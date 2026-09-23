"""`basemap:`.

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    SourceLayer,
    _require,
    _source_layer,
    _tile_member,
)


@dataclass(frozen=True)
class Basemap:
    """The minimap's ground: the harbour and the parks under its roads
    (`pipeline/basemap.py`, 2026-09-24, the user's call).

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


def _basemap(body: Any, where: str) -> Basemap | None:
    """The optional minimap-basemap block. Absent, the map draws roads alone."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    shoreline = _require(body, "shoreline", where)
    parks = _require(body, "parks", where)
    cover = float(_require(body, "land_cover", where))
    if not 0.0 < cover < 1.0:
        raise ValueError(f"{where}:land_cover must be a share in (0, 1), got {cover}")
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
    )
