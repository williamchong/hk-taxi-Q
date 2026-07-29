"""City configuration loading.

Every city specific — CRS codes, region bounds, deck heights, source URLs —
lives in `config/cities/*.yaml` and reaches the pipeline only through this
module (CLAUDE.md hard rule 3). Pipeline logic that needs a Hong Kong fact asks
the config for it; it never spells the fact out.

Loading is strict and fails on the first problem rather than defaulting. A
silently-defaulted CRS or bound produces output that looks plausible and is
wrong by hundreds of metres, which is far more expensive than a stack trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeline.crs import (
    GameTransform,
    GeodeticBounds,
    ProjectedBounds,
    project_bounds,
)

SUPPORTED_SCHEMA = 1
CITIES_ROOT = Path(__file__).resolve().parent.parent / "config" / "cities"


@dataclass(frozen=True)
class RegionConfig:
    id: str
    name: str
    bounds: GeodeticBounds
    tile_size_m: float


@dataclass(frozen=True)
class TiledSource:
    """A dataset published per map sheet, reachable only through an index.

    The index is a vector layer whose features carry both a footprint and the
    download URL for that footprint's models, so which sheets a region needs is
    derived rather than listed. The property names below are what keeps this
    city-agnostic: the pipeline knows "some property holds the URL", never that
    Hong Kong happens to call it `Format_glTF`.

    Those URLs may embed a publisher's API key, which is why they are read from
    the fetched index at run time and never written into config or the manifest.
    """

    id: str
    index_url: str
    # Datum of the index geometry, which need not match the region's.
    index_crs: str
    id_property: str
    url_property: str
    # Per-tile version stamp used as the cache key. Optional: a publisher that
    # offers none simply gets fetch-once semantics.
    revision_property: str | None = None


@dataclass(frozen=True)
class CityConfig:
    id: str
    name: str
    # CRS the source datasets are published in; all pipeline geometry lives here.
    projected_crs: str
    # Datum the region bounds above are expressed in. Stated rather than assumed
    # because reading Hong Kong bounds on the wrong datum moves them ~304 m.
    geodetic_crs: str
    # Ordinal grade-separation level to authored deck height in metres. Road
    # Network v2 carries no Z; ELEVATION is a layer index, not a measurement.
    elevation_levels: dict[int, float]
    # Whole-city extent. Only ever used to anchor the city-space frame that
    # regions are positioned in, so it must be *declared and stable* rather
    # than derived from the regions that happen to exist — see `city_transform`.
    bounds: GeodeticBounds
    regions: dict[str, RegionConfig]
    # Datasets available at a single fixed URL.
    sources: dict[str, str]
    # Datasets that must be selected per region via an index.
    tiled_sources: dict[str, TiledSource]

    @property
    def source_ids(self) -> set[str]:
        """Every fetchable source name, of either kind."""
        return set(self.sources) | set(self.tiled_sources)

    def region(self, region_id: str) -> RegionConfig:
        if region_id not in self.regions:
            known = ", ".join(sorted(self.regions)) or "none"
            raise KeyError(f"City '{self.id}' has no region '{region_id}'. Known: {known}")
        return self.regions[region_id]

    def projected_bounds(self, region_id: str) -> ProjectedBounds:
        return project_bounds(
            self.region(region_id).bounds,
            geodetic_crs=self.geodetic_crs,
            projected_crs=self.projected_crs,
        )

    def game_transform(self, region_id: str) -> GameTransform:
        """The region's own frame — what its geometry is authored in.

        Region-local rather than city-wide on purpose. Everything the player
        drives through sits within ~2 km of this origin, where float32 resolves
        to a fraction of a millimetre. A city-wide frame would put Wan Chai
        35 km out, quantising every position — the car's included — to ~4 mm.
        See `city_offset` for how regions are then placed relative to each other.
        """
        return GameTransform.from_bounds(self.projected_bounds(region_id))

    def city_transform(self) -> GameTransform:
        """The shared frame all regions are positioned in (`Q10`).

        Anchored on the city's *declared* bounds, never on the union of the
        regions defined so far. Deriving it would make the frame move every time
        a region is added, silently invalidating every offset already written
        into a published `city.json`. Declared bounds are allowed to be generous;
        they are not allowed to change.
        """
        return GameTransform.from_bounds(
            project_bounds(
                self.bounds,
                geodetic_crs=self.geodetic_crs,
                projected_crs=self.projected_crs,
            )
        )

    def city_offset(self, region_id: str) -> tuple[float, float, float]:
        """Add this to a region-local position to get a city-space one.

        The number that lets two regions abut without either giving up its local
        precision. A region loaded alone can ignore it entirely; a build that
        streams neighbours applies it as a translation.

        Non-negative in X and Z whenever the city bounds actually contain the
        region, which `load_city` checks.
        """
        region = self.game_transform(region_id)
        city = self.city_transform()
        return (
            region.origin_easting - city.origin_easting,
            region.origin_elevation - city.origin_elevation,
            city.origin_northing - region.origin_northing,
        )

    def deck_height_m(self, elevation_level: int) -> float:
        """Authored height for a road-graph ELEVATION value.

        Tunnels are plausible in the source and were not seen in the sample, so
        an unmapped level is an error rather than a silent 0.0 that would drag a
        tunnel up to street level and invent a junction.
        """
        if elevation_level not in self.elevation_levels:
            known = ", ".join(str(k) for k in sorted(self.elevation_levels))
            raise KeyError(
                f"City '{self.id}' maps no deck height for ELEVATION {elevation_level}. "
                f"Known levels: {known}"
            )
        return self.elevation_levels[elevation_level]


def load_city(city_id: str, *, cities_root: Path | None = None) -> CityConfig:
    """Read and validate `<cities_root>/<city_id>.yaml`."""
    path = (cities_root or CITIES_ROOT) / f"{city_id}.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} is not a YAML mapping")

    version = document.get("schema_version")
    if version != SUPPORTED_SCHEMA:
        raise ValueError(f"{path} declares schema_version {version!r}, expected {SUPPORTED_SCHEMA}")
    if document.get("id") != city_id:
        raise ValueError(f"{path} declares id {document.get('id')!r}, expected {city_id!r}")

    crs = _require(document, "crs", path)
    regions = _require(document, "regions", path)
    if not regions:
        raise ValueError(f"{path} defines no regions")

    city = CityConfig(
        id=city_id,
        name=str(_require(document, "name", path)),
        projected_crs=str(_require(crs, "projected", f"{path}:crs")),
        geodetic_crs=str(_require(crs, "geodetic", f"{path}:crs")),
        elevation_levels=_elevation_levels(_require(document, "elevation_levels", path), path),
        bounds=_bounds(_require(document, "bounds", path), f"{path}:bounds"),
        regions={region_id: _region(region_id, body, path) for region_id, body in regions.items()},
        sources={str(k): str(v) for k, v in (document.get("sources") or {}).items()},
        tiled_sources={
            str(source_id): _tiled_source(str(source_id), body, path)
            for source_id, body in (document.get("tiled_sources") or {}).items()
        },
    )
    _check_regions_lie_within_the_city(city, path)
    return city


def _check_regions_lie_within_the_city(city: CityConfig, path: Path) -> None:
    """A region outside the declared city bounds is a config error, not a shift.

    It would still produce coordinates, just with a negative `city_offset` —
    i.e. a region placed north or west of the frame everything else is measured
    from. Caught here because the symptom otherwise appears in `P1-6` output as
    a region that loads fine alone and lands in the wrong place beside another.
    """
    city_bounds = city.bounds
    for region in city.regions.values():
        r = region.bounds
        if (
            r.west < city_bounds.west
            or r.east > city_bounds.east
            or r.south < city_bounds.south
            or r.north > city_bounds.north
        ):
            raise ValueError(
                f"{path}:regions.{region.id} lies outside the city bounds. "
                f"Region ({r.west}, {r.south})-({r.east}, {r.north}) is not inside "
                f"({city_bounds.west}, {city_bounds.south})-"
                f"({city_bounds.east}, {city_bounds.north})."
            )


def _tiled_source(source_id: str, body: dict[str, Any], path: Path) -> TiledSource:
    where = f"{path}:tiled_sources.{source_id}"
    revision = body.get("revision_property")
    return TiledSource(
        id=source_id,
        index_url=str(_require(body, "index_url", where)),
        index_crs=str(_require(body, "index_crs", where)),
        id_property=str(_require(body, "id_property", where)),
        url_property=str(_require(body, "url_property", where)),
        revision_property=None if revision is None else str(revision),
    )


def _require(mapping: dict[str, Any], key: str, where: Path | str) -> Any:
    if key not in mapping:
        raise ValueError(f"{where} is missing required key '{key}'")
    return mapping[key]


def _elevation_levels(raw: dict[Any, Any], path: Path) -> dict[int, float]:
    levels: dict[int, float] = {}
    for key, value in raw.items():
        # Two YAML traps here, both silent, both producing a map that loads
        # cleanly and answers wrongly.
        #
        # Quoted "-1" stays a str, giving a level no ELEVATION lookup can hit.
        #
        # Worse: PyYAML implements YAML 1.1, where bare `on`/`off`/`yes`/`no`
        # resolve to booleans. Since bool subclasses int, `off: 3.0` satisfies a
        # plain isinstance(key, int) check — and then lands on level 0, because
        # False == 0 as a dict key. A typo would silently redefine ground level.
        #
        # A collision PyYAML resolves before we see it (both `1:` and `on:` in
        # one mapping) is beyond this layer; it needs both spellings at once.
        if isinstance(key, bool) or not isinstance(key, int):
            raise ValueError(f"{path}:elevation_levels key {key!r} is not an integer")
        levels[key] = float(value)
    if 0 not in levels:
        raise ValueError(f"{path}:elevation_levels has no level 0 — ground must be mapped")
    return levels


def _bounds(body: dict[str, Any], where: str) -> GeodeticBounds:
    return GeodeticBounds(
        west=float(_require(body, "west", where)),
        east=float(_require(body, "east", where)),
        south=float(_require(body, "south", where)),
        north=float(_require(body, "north", where)),
    )


def _region(region_id: str, body: dict[str, Any], path: Path) -> RegionConfig:
    where = f"{path}:regions.{region_id}"
    return RegionConfig(
        id=region_id,
        name=str(_require(body, "name", where)),
        bounds=_bounds(_require(body, "bounds", where), f"{where}.bounds"),
        tile_size_m=float(_require(body, "tile_size_m", where)),
    )
