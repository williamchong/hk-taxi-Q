"""`backdrop:`.

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
from pipeline.config_blocks.basemap import _positive
from pipeline.crs import GeodeticBounds


@dataclass(frozen=True)
class BackdropBand:
    """The colour of every backdrop block standing at least `above_m` tall."""

    above_m: float
    material: Material


@dataclass(frozen=True)
class Backdrop:
    """The far shore (`P3-100`, `Q249`): the skyline across the harbour as one
    silhouette mesh, the ground it stands on and the sea that reaches it
    (`pipeline/backdrop.py`). Seen from a kilometre and more, never driven.

    ✅ **Every block is PUBLISHED**: a footprint of the topographic map's
    `Building` layer, extruded to the layer's own roof level. The water is the
    basemap's — its level, its colour and the frame it stops at — and so are
    the sea walls, so the block needs `basemap:` beside it.

    ⚠️ **Not a region.** It has no roads, no tiles and no collider, and it is
    drawn in the frame of each region in `regions`.
    """

    source: str
    member: str | None
    # The strip of the far shore that is built, on the city's geodetic datum.
    # The fetch downloads `source`'s sheets over it for every region in
    # `regions` (`Config.fetch_extents`).
    bounds: GeodeticBounds
    # The regions whose bundle ships the backdrop. A region joined to one of
    # these is drawn beside it and needs no copy of its own.
    regions: frozenset[str]
    buildings: SourceLayer
    # A block shorter than this, roof over base, is not drawn: at a kilometre
    # it is under the haze and behind the front row.
    min_height_m: float
    # Douglas-Peucker tolerance for a footprint, in metres.
    simplify_m: float
    # The most triangles the skyline may ship. Over it the shortest blocks go
    # first, and the report says the height of the shortest one drawn.
    triangle_cap: int
    # The height of the far shore's ground, in game metres: one flat slab.
    ground_level_m: float
    # The slab lies under everything published, closed over a gap up to twice
    # this wide: the shoreline over the strip does not close on its own.
    ground_close_m: float
    ground_material: Material
    # Ascending by `above_m`, the first at 0.
    bands: tuple[BackdropBand, ...]

    @property
    def tiled(self) -> bool:
        return self.member is not None

    def material_for(self, height_m: float) -> Material:
        """The tallest band `height_m` reaches."""
        chosen = self.bands[0]
        for band in self.bands:
            if height_m >= band.above_m:
                chosen = band
        return chosen.material


_BUILDING_ROLES = ("base", "roof")


def _bands(body: dict[str, Any], where: str, table: _MaterialTable) -> tuple[BackdropBand, ...]:
    raw = _require(body, "bands", where)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{where}:bands must be a non-empty list, got {raw!r}")
    bands: list[BackdropBand] = []
    for index, entry in enumerate(raw):
        at = f"{where}:bands[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{at} must be a mapping, got {entry!r}")
        above_m = float(_require(entry, "above_m", at))
        if bands and above_m <= bands[-1].above_m:
            raise ValueError(f"{at}:above_m is {above_m}, not above the band before it")
        bands.append(
            BackdropBand(
                above_m=above_m,
                material=table.get(str(_require(entry, "material", at)), f"{at}:material"),
            )
        )
    if bands[0].above_m != 0.0:
        raise ValueError(f"{where}:bands[0]:above_m is {bands[0].above_m}, and the first is 0")
    return tuple(bands)


def _backdrop(body: Any, where: str, table: _MaterialTable) -> Backdrop | None:
    """The optional backdrop block. Absent, the sea ends at the basemap's reach
    and nothing stands beyond it."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    bounds = _require(body, "bounds", where)
    if not isinstance(bounds, dict):
        raise ValueError(f"{where}:bounds must be a mapping, got {bounds!r}")
    regions = _require(body, "regions", where)
    if isinstance(regions, str) or not isinstance(regions, list) or not regions:
        raise ValueError(f"{where}:regions must be a non-empty list of region ids, got {regions!r}")
    cap = int(_require(body, "triangle_cap", where))
    if cap < 1:
        raise ValueError(f"{where}:triangle_cap is {cap}, which draws nothing")
    return Backdrop(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        bounds=GeodeticBounds(
            west=float(_require(bounds, "west", f"{where}:bounds")),
            east=float(_require(bounds, "east", f"{where}:bounds")),
            south=float(_require(bounds, "south", f"{where}:bounds")),
            north=float(_require(bounds, "north", f"{where}:bounds")),
        ),
        regions=frozenset(str(region) for region in regions),
        buildings=_source_layer(
            _require(body, "buildings", where), f"{where}:buildings", _BUILDING_ROLES
        ),
        min_height_m=_positive(body, "min_height_m", where),
        simplify_m=_positive(body, "simplify_m", where),
        triangle_cap=cap,
        ground_level_m=float(_require(body, "ground_level_m", where)),
        ground_close_m=_positive(body, "ground_close_m", where),
        ground_material=table.get(
            str(_require(body, "ground_material", where)), f"{where}:ground_material"
        ),
        bands=_bands(body, where, table),
    )
