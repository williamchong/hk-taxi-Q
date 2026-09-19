"""`boxjunctions:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import LayerSpec, _require, _spec_header


@dataclass(frozen=True)
class BoxJunctions(LayerSpec):
    """Published yellow box junctions, drawn by `pipeline/boxjunctions.py` (`P3-18`).

    The content is **read, not invented**, on `Q53`'s terms: `DTAD_YL_BOX_POLY`
    publishes each box as a surveyed polygon, so the extent that `Q53` said
    "nothing publishes" is exactly what this block reads (`Q56` found it). The
    dimensions below are marking *convention*, transcribed from TD's index plan
    CT174/51-5(1)F — where the box goes is read from the source.

    ⚠️ **The hatch direction is the one derived thing here.** The publisher's
    `ANGLE1`/`ANGLE2` pair carries it on a fraction of the layer (4 of the
    region's 20), and is used wherever present; elsewhere the direction is the
    box's own min-area-rectangle long axis + 45 deg. That derivation was graded
    against the published pairs before it shipped — `boxjunctions.json`
    publishes `hatch_angle_residual_deg` so it stays graded — and it was chosen
    over the nearest-edge heading + 45 on those numbers: per published pair it
    wins 3 of 4, and the edge alternative picks an arbitrary arm at exactly the
    geometry a box occupies. A wrong direction rotates a cross-hatch inside its
    own border and misleads no one; a box on the wrong junction would, which is
    why position is never derived.

    ⚠️ **There is no material here, and its absence is the decision** — the same
    paragraph `Arrows` carries. The yellow is authored in
    `game/tuning/boxjunctions.tres`, deliberately outside `Q33`'s exposure rule,
    and the glTF material *name* the engine dispatches on is
    `BOXJUNCTIONS_MATERIAL` in `pipeline/boxjunctions.py`.
    """

    # Which published `YELLOWBOX_TYPE` values are box junctions. The region's
    # layer is single-valued ("Yellow Box"), so today this filters nothing —
    # it exists so a second city whose publisher adds a type this stage has no
    # business drawing refuses it loudly rather than painting it yellow.
    box_types: tuple[str, ...]
    # Marking convention, from the index plan: RM1038 draws a 300 mm boundary
    # line and 100 mm hatched lines.
    border_width_m: float
    hatch_width_m: float
    # Centre-to-centre spacing of the hatched lines. The index plan gives
    # "SPACING = 2000 (2500)"; the parenthetical is the wider variant.
    hatch_spacing_m: float
    # Sampling pitch along stripes and border runs. Each vertex takes its height
    # from the road under it, so this is what lets a long stripe follow the
    # crown of the junction instead of chording across it.
    station_m: float
    # How far above the carriageway the hatch sits. ⚠️ Deliberately below
    # `arrows.lift_m`: 51 of the region's turn arrows sit over junction caps,
    # and an arrow inside a box junction at equal lift would z-fight the
    # hatching. Arrows paint over boxes, which is also what the street does.
    lift_m: float
    # How far the boundary line sits above the *hatch*. The two are the same
    # paint at the same nominal height, and the hatch is deliberately not
    # clipped back to the boundary's inner edge — an inward offset of a concave
    # 106-vertex ring can self-intersect, and a guessed repair of that is
    # invented geometry. Lifting the border clear instead makes the overlap
    # invisible by construction.
    border_lift_m: float
    # Furthest a box's centroid may sit from a level-0 centreline and still be
    # drawn. Beyond it the box is dropped rather than guessed at — its vertices
    # would take their heights from a road it is not on.
    max_offset_m: float


_BOXJUNCTION_ROLES = ("type", "level", "hatch_a", "hatch_b")


def _boxjunctions(body: Any, where: str) -> BoxJunctions | None:
    """The optional published-box-junction block (`P3-18`).

    Absent, the region ships no `boxjunctions.glb` and the manifest names none —
    the shape `tramway` and `arrows` both use. What is *not* offered is a
    fallback that puts a box on every junction node: the region publishes 20
    boxes against 393 junctions, so a derived placement would be wrong nineteen
    times in twenty, and `Q53` refused exactly that.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw_types = _require(body, "box_types", where)
    if isinstance(raw_types, str) or not isinstance(raw_types, (list, tuple)):
        raise ValueError(f"{where}:box_types must be a list, got {raw_types!r}")
    box_types = tuple(str(value) for value in raw_types)
    if not box_types:
        # An empty list admits nothing, which is the same outcome as omitting
        # the block — refused so the difference is a decision, not a typo.
        raise ValueError(f"{where}:box_types is empty; a block that draws nothing is a mistake")

    widths = {
        name: float(_require(body, name, where))
        for name in ("border_width_m", "hatch_width_m", "hatch_spacing_m", "station_m")
    }
    negative = {name: value for name, value in widths.items() if value <= 0.0}
    if negative:
        raise ValueError(f"{where}: {', '.join(sorted(negative))} must be positive; got {negative}")
    if widths["hatch_width_m"] >= widths["hatch_spacing_m"]:
        raise ValueError(
            f"{where}: hatch_width_m {widths['hatch_width_m']} must be narrower than "
            f"hatch_spacing_m {widths['hatch_spacing_m']}, or the hatch is a fill"
        )

    max_offset_m = float(_require(body, "max_offset_m", where))
    if max_offset_m <= 0.0:
        raise ValueError(f"{where}:max_offset_m must be positive, got {max_offset_m}")
    lift_m = float(_require(body, "lift_m", where))
    if lift_m <= 0.0:
        raise ValueError(
            f"{where}:lift_m is {lift_m}; paint coplanar with the road it is painted on z-fights"
        )
    border_lift_m = float(_require(body, "border_lift_m", where))
    if border_lift_m <= 0.0:
        raise ValueError(
            f"{where}:border_lift_m is {border_lift_m}; the boundary line coplanar with the "
            f"hatch it crosses z-fights it"
        )

    return BoxJunctions(
        **_spec_header(body, where, _BOXJUNCTION_ROLES),
        box_types=box_types,
        border_width_m=widths["border_width_m"],
        hatch_width_m=widths["hatch_width_m"],
        hatch_spacing_m=widths["hatch_spacing_m"],
        station_m=widths["station_m"],
        lift_m=lift_m,
        border_lift_m=border_lift_m,
        max_offset_m=max_offset_m,
    )
