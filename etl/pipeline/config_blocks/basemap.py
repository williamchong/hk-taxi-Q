"""`basemap:`.

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    Material,
    SourceLayer,
    _MaterialTable,
    _require,
    _source_layer,
    _tile_member,
)


@dataclass(frozen=True)
class Basemap:
    """The harbour and the parks: the minimap's ground under its roads
    (`pipeline/basemap.py`, 2026-09-24, the user's call), and since 2026-09-25
    the water plane the world draws where the sea is (`water.glb`), on the
    user's call as well.

    ✅ **Every class is PUBLISHED.** The sea is cut from the topographic map's
    own shoreline — sea walls, high-water marks and breakwaters, a coded domain
    in every sheet — and the parks are its `Site` polygons whose published code
    is a park, a garden, a playground, a sitting-out area, a sports ground or a
    promenade. Nothing here draws a coastline by hand.

    ⚠️ **The sheets carry no sea POLYGON**: the harbour is the absence of land
    north of a line. So the stage cuts the frame along the shoreline and keeps
    the pieces with no building on them — see `pipeline/basemap.py`.
    """

    source: str
    member: str | None
    # Metres past the region's read box the basemap covers: the minimap's span,
    # so the map shows the water the car can see. The fetch selects its sheets
    # this far out (`tiled_sources.<source>.fetch_margin_m`), and the two must
    # agree — `config.py` refuses a reach the fetch does not cover.
    reach_m: float
    shoreline: SourceLayer
    # `shoreline`'s type codes that bound the sea.
    shoreline_types: frozenset[str]
    parks: SourceLayer
    # `parks`' codes that are open space.
    park_codes: frozenset[str]
    buildings: SourceLayer
    # How wide a gap in the shoreline is closed before the frame is cut along
    # it, in metres. The lines are surveyed per sheet and meet with gaps.
    seal_m: float
    # A piece is land where buildings cover more than this share of it.
    land_cover: float
    # Douglas-Peucker tolerance for the published outlines, in metres: under
    # what a 320 m map shows at 240 px.
    simplify_m: float
    # The height the world's water plane is drawn at, in game metres — the
    # source vertical datum, since `GameTransform.origin_elevation` is 0.0. A
    # fact about the city, not a look: mean sea level on Hong Kong Principal
    # Datum, cited in the city file.
    water_level_m: float
    # The height the tile stage sinks the ground to under the sea, in game
    # metres. 🔴 **The sheets' terrain over the harbour is NOT flat** — measured
    # 1.1-4.2 m over Wan Chai's sea at a 4 m grid, against 2.7-4.9 m on the land
    # within 12 m of the shore — so a plane laid over the shipped ground either
    # shows grey through the blue or floods the promenade, at every level tried.
    # `buildings._tile_ground` drops every ground vertex inside the sea polygon
    # to this instead, so the water meets the published shoreline and nothing
    # else. Must lie under `water_level_m`.
    seabed_m: float
    # The water's colour, from `materials:` like every other colour the city
    # ships (`Q33`). Its diffuse albedo; the blue is the sky reflected off
    # `tuning/water.tres`'s roughness.
    water_material: Material

    @property
    def tiled(self) -> bool:
        return self.member is not None


_SHORELINE_ROLES = ("type",)
_PARK_ROLES = ("code",)


def _codes(body: dict[str, Any], key: str, where: str) -> frozenset[str]:
    raw = _require(body, key, where)
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError(f"{where}:{key} must be a non-empty list of codes, got {raw!r}")
    return frozenset(str(code) for code in raw)


def _positive(body: dict[str, Any], key: str, where: str) -> float:
    value = float(_require(body, key, where))
    if value <= 0.0:
        raise ValueError(f"{where}:{key} must be positive, got {value}")
    return value


def _basemap(body: Any, where: str, table: _MaterialTable) -> Basemap | None:
    """The optional basemap block. Absent, the map draws roads alone and the
    world draws no water."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    shoreline = _require(body, "shoreline", where)
    parks = _require(body, "parks", where)
    cover = float(_require(body, "land_cover", where))
    if not 0.0 < cover < 1.0:
        raise ValueError(f"{where}:land_cover must be a share in (0, 1), got {cover}")
    water_level_m = float(_require(body, "water_level_m", where))
    seabed_m = float(_require(body, "seabed_m", where))
    if seabed_m >= water_level_m:
        raise ValueError(
            f"{where}:seabed_m is {seabed_m} m, not under water_level_m {water_level_m} m — "
            "the ground sunk under the sea would stand above the water drawn over it"
        )
    return Basemap(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        reach_m=_positive(body, "reach_m", where),
        shoreline=_source_layer(shoreline, f"{where}:shoreline", _SHORELINE_ROLES),
        shoreline_types=_codes(shoreline, "types", f"{where}:shoreline"),
        parks=_source_layer(parks, f"{where}:parks", _PARK_ROLES),
        park_codes=_codes(parks, "codes", f"{where}:parks"),
        buildings=_source_layer(_require(body, "buildings", where), f"{where}:buildings", ()),
        seal_m=_positive(body, "seal_m", where),
        land_cover=cover,
        simplify_m=_positive(body, "simplify_m", where),
        water_level_m=water_level_m,
        seabed_m=seabed_m,
        water_material=table.get(
            str(_require(body, "water_material", where)), f"{where}:water_material"
        ),
    )
