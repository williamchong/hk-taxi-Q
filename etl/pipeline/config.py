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
    regions: dict[str, RegionConfig]
    sources: dict[str, str]

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
        return GameTransform.from_bounds(self.projected_bounds(region_id))

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

    return CityConfig(
        id=city_id,
        name=str(_require(document, "name", path)),
        projected_crs=str(_require(crs, "projected", f"{path}:crs")),
        geodetic_crs=str(_require(crs, "geodetic", f"{path}:crs")),
        elevation_levels=_elevation_levels(_require(document, "elevation_levels", path), path),
        regions={region_id: _region(region_id, body, path) for region_id, body in regions.items()},
        sources={str(k): str(v) for k, v in (document.get("sources") or {}).items()},
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


def _region(region_id: str, body: dict[str, Any], path: Path) -> RegionConfig:
    where = f"{path}:regions.{region_id}"
    bounds = _require(body, "bounds", where)
    return RegionConfig(
        id=region_id,
        name=str(_require(body, "name", where)),
        bounds=GeodeticBounds(
            west=float(_require(bounds, "west", f"{where}.bounds")),
            east=float(_require(bounds, "east", f"{where}.bounds")),
            south=float(_require(bounds, "south", f"{where}.bounds")),
            north=float(_require(bounds, "north", f"{where}.bounds")),
        ),
        tile_size_m=float(_require(body, "tile_size_m", where)),
    )
