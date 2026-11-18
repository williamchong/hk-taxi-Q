"""`paths:`.

One of `pipeline.config`'s blocks (`P3-101`, `Q250`), imported through
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
    _source_layer,
    _tile_member,
)

_ROLES = ("type",)
_SIZES = ("step_m", "min_length_m", "max_grade_pct")
_MARGINS = ("lift_m", "kerb_clear_m", "sag_m", "cell_m")


@dataclass(frozen=True)
class Paths:
    """The pedestrian lines the topographic map draws, laid on the ground by
    `pipeline/paths.py` (`P3-101`, `Q250`).

    🔴 **Only where a line is surveyed.** Nothing is drawn between two lines,
    and no area is filled: the publisher draws margins and centrelines, not
    faces.

    ⚠️ **A width is authored.** A line has none; `widths_m` gives each
    published code the ribbon it is drawn as.
    """

    source: str
    member: str | None
    layer: SourceLayer
    # Each published code that is drawn, and the ribbon's width in metres.
    widths_m: dict[str, float]
    material: Material
    # How far over the ground the ribbon is laid.
    lift_m: float
    # How far outside the level-0 carriageway a line is cut back to.
    kerb_clear_m: float
    # How often the ground is read along a line.
    step_m: float
    # How far the ground may leave the straight ribbon between two kept
    # stations before a station is kept between them.
    sag_m: float
    # A piece shorter than this is not drawn.
    min_length_m: float
    # The steepest ground a ribbon is laid on, along it or across it, as a
    # percentage: past it the line is broken.
    max_grade_pct: float
    # The plan cell a region's ribbons are cut into, so the engine can cull
    # them; zero is one mesh.
    cell_m: float

    @property
    def tiled(self) -> bool:
        return self.member is not None


def _paths(body: Any, where: str, table: _MaterialTable) -> Paths | None:
    """The optional `paths:` block. Absent, the region ships no `paths.glb`."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw = _require(body, "widths_m", where)
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{where}:widths_m must map a published code to a width, got {raw!r}")
    widths = _measures(raw, f"{where}:widths_m", tuple(str(code) for code in raw), positive=True)
    margins = _measures(body, where, _MARGINS)
    if margins["sag_m"] >= margins["lift_m"]:
        raise ValueError(
            f"{where}:sag_m {margins['sag_m']} is not under lift_m {margins['lift_m']}: "
            "the ground could rise through the ribbon between two stations"
        )
    return Paths(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        layer=_source_layer(body, where, _ROLES),
        widths_m=widths,
        material=table.get(str(_require(body, "material", where)), f"{where}:material"),
        **_measures(body, where, _SIZES, positive=True),
        **margins,
    )
