"""`planters:`.

One of `pipeline.config`'s blocks (`P3-98`, `Q247`), imported through
`pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    Material,
    SourceLayer,
    _MaterialTable,
    _measures,
    _require,
)

_SIZES = (
    "wall_height_m",
    "wall_width_m",
    "clump_m",
    "shrub_min_m",
    "shrub_max_m",
    "min_bed_m2",
    "min_wall_m2",
)
_MARGINS = ("shrub_inset_m", "kerb_clear_m", "sink_m", "cell_m")
_SHARES = ("side_darken", "tint_darken", "max_on_road")


@dataclass(frozen=True)
class Planters:
    """The published planter walls, built by `pipeline/planters.py` (`P3-98`, `Q247`).

    🔴 **Only where a wall is surveyed.** A bed is a ring of published walls
    that closes; nothing is filled between two that do not.

    ⚠️ **Every height and the planting are authored.** The publisher draws a
    line and names it, and that is all.
    """

    source: str
    layer: SourceLayer
    wall_material: Material
    shrub_material: Material
    wall_height_m: float
    wall_width_m: float
    shrub_inset_m: float
    clump_m: float
    shrub_min_m: float
    shrub_max_m: float
    side_darken: float
    tint_darken: float
    kerb_clear_m: float
    max_on_road: float
    min_bed_m2: float
    min_wall_m2: float
    sink_m: float
    # The plan cell a region's planters are cut into, so the engine can cull
    # them; zero is one mesh.
    cell_m: float


def _planters(body: Any, where: str, table: _MaterialTable) -> Planters | None:
    """The optional `planters:` block. Absent, the region ships no `planters.glb`."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    sizes = _measures(body, where, _SIZES, positive=True)
    if sizes["shrub_min_m"] > sizes["shrub_max_m"]:
        raise ValueError(f"{where}:shrub_min_m is over shrub_max_m")
    shares = {name: float(_require(body, name, where)) for name in _SHARES}
    for name, share in shares.items():
        if not 0.0 <= share < 1.0:
            raise ValueError(f"{where}:{name} {share} must be in [0, 1)")
    return Planters(
        source=str(_require(body, "source", where)),
        layer=SourceLayer(layer=str(_require(body, "layer", where)), fields={}),
        wall_material=table.get(
            str(_require(body, "wall_material", where)), f"{where}:wall_material"
        ),
        shrub_material=table.get(
            str(_require(body, "shrub_material", where)), f"{where}:shrub_material"
        ),
        **sizes,
        **_measures(body, where, _MARGINS),
        **shares,
    )
