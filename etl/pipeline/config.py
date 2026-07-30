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
class HeightBand:
    """A colour for buildings up to a given height above their own base."""

    up_to_m: float
    colour: tuple[int, int, int]


@dataclass(frozen=True)
class BuildingStyle:
    """How `P1-2` turns source massing into vertex-coloured tiles.

    All of it is tuning data rather than constants in code (CLAUDE.md hard
    rule 4), and all of it is city-shaped: the sub-directory names come from the
    publisher's zip layout, and the palette is Hong Kong's, not a generic city's.
    """

    # Sheet sub-directories holding massing to tile.
    classes: tuple[str, ...]
    # Sheet sub-directory holding the textured ground, which is read only by the
    # evaluation path and never tiled. Named here rather than in the pipeline
    # because "TERRAIN(TB)" is a LandsD spelling, not a fact about terrain.
    terrain_class: str
    # Flat colour for a class, overriding the height bands.
    class_colours: dict[str, tuple[int, int, int]]
    height_bands: tuple[HeightBand, ...]
    # Fraction of brightness a building's colour may be varied by, seeded from
    # its own id so the result is stable across runs.
    colour_jitter: float
    # One clustering cell size per LOD tier, in metres, coarsest last. The first
    # is normally 0.0 — an exact weld, losing nothing.
    lod_cell_sizes_m: tuple[float, ...]

    def colour_for(self, class_id: str, height_m: float) -> tuple[int, int, int]:
        if class_id in self.class_colours:
            return self.class_colours[class_id]
        return next(band.colour for band in self.height_bands if height_m <= band.up_to_m)


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
    buildings: BuildingStyle

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
        buildings=_building_style(_require(document, "buildings", path), f"{path}:buildings"),
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


def _building_style(body: dict[str, Any], where: str) -> BuildingStyle:
    bands = tuple(
        HeightBand(
            up_to_m=float(_require(band, "up_to_m", where)),
            colour=_parse_hex(str(_require(band, "colour", where)), f"{where}:height_bands"),
        )
        for band in _require(body, "height_bands", where)
    )
    if not bands:
        raise ValueError(f"{where}:height_bands is empty")
    heights = [band.up_to_m for band in bands]
    if heights != sorted(heights):
        raise ValueError(f"{where}:height_bands must be ordered by ascending up_to_m")
    if heights[-1] != float("inf"):
        # Without an open-ended last band, `colour_for` has nothing to return for
        # a building taller than the table — and the tallest buildings are the
        # ones a Hong Kong skyline is read by.
        raise ValueError(f"{where}:height_bands must end with `up_to_m: .inf`")

    cells = tuple(float(size) for size in _require(body, "lod_cell_sizes_m", where))
    if not cells:
        raise ValueError(f"{where}:lod_cell_sizes_m is empty")
    if list(cells) != sorted(cells):
        raise ValueError(f"{where}:lod_cell_sizes_m must be ordered coarsest last")

    classes = tuple(str(name) for name in _require(body, "classes", where))
    if not classes:
        raise ValueError(f"{where}:classes is empty")

    class_colours = {
        str(name): _parse_hex(str(value), f"{where}:class_colours.{name}")
        for name, value in (body.get("class_colours") or {}).items()
    }
    unknown = set(class_colours) - set(classes)
    if unknown:
        # A misspelled key parses, loads, and silently colours nothing — the one
        # way this table can be wrong without saying so.
        raise ValueError(
            f"{where}:class_colours names {', '.join(sorted(unknown))}, "
            f"which is not in classes ({', '.join(classes)})"
        )

    jitter = float(_require(body, "colour_jitter", where))
    if not 0.0 <= jitter < 1.0:
        raise ValueError(f"{where}:colour_jitter must be in [0, 1), got {jitter}")

    return BuildingStyle(
        classes=classes,
        terrain_class=str(_require(body, "terrain_class", where)),
        class_colours=class_colours,
        height_bands=bands,
        colour_jitter=jitter,
        lod_cell_sizes_m=cells,
    )


def _parse_hex(value: str, where: str) -> tuple[int, int, int]:
    text = value.lstrip("#")
    if len(text) != 6:
        raise ValueError(f"{where} is not a #rrggbb colour: {value!r}")
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError as error:
        raise ValueError(f"{where} is not a #rrggbb colour: {value!r}") from error


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
