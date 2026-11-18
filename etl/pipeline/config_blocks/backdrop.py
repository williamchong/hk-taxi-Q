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


@dataclass(frozen=True)
class BackdropBand:
    """The colour of every backdrop block standing at least `above_m` tall."""

    above_m: float
    material: Material


@dataclass(frozen=True)
class Backdrop:
    """A region's far version (`P3-100`, `Q249`): its skyline as one silhouette
    mesh, the ground it stands on and the water round it
    (`pipeline/backdrop.py`). What another region sees of it past the camera's
    far plane, where its own tiles are never loaded.

    ✅ **Every block is PUBLISHED**: a footprint of the topographic map's
    `Building` layer, extruded to the layer's own roof level. The water is the
    basemap's — its level, its colour and the frame it stops at — and so are
    the sea walls, so the block needs `basemap:` beside it.

    Every declared region ships one, built over its own `bounds`; a region
    declared `far_only` ships nothing else.
    """

    source: str
    member: str | None
    # How far past a region's read box its far version runs the water: far
    # enough that the open harbour between two regions' frames is somebody's.
    # The fetch downloads `source`'s sheets over it (`Config.fetch_extents`).
    sea_reach_m: float
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
    cap = int(_require(body, "triangle_cap", where))
    if cap < 1:
        raise ValueError(f"{where}:triangle_cap is {cap}, which draws nothing")
    return Backdrop(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        sea_reach_m=_positive(body, "sea_reach_m", where),
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
