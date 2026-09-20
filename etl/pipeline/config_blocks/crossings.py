"""`crossings:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`), imported through
`pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    LayerSpec,
    SourceLayer,
    _require,
    _source_layer,
    _spec_header,
)


@dataclass(frozen=True)
class ZebraEvidence:
    """What says a striped crossing is a ZEBRA rather than a light-signal one.

    🔴 **The colour of a crossing is not published on the crossing.**
    `DTAD_CROSSING_LINE`'s `LINETYPE` has no domain in the data dictionary, and
    it does not separate them: every value carries the same 0.6 m stripe,
    `RM1076` included, whose sheet width is 250-350. What the regulations leave
    is two striped kinds — a zebra (`RM1070`, white) and a light-signal crossing
    (`RM1076`, yellow) — and a zebra is never painted without its zigzags
    (`RM1072`-`RM1074`), which TD surveys in another layer.

    `within_m` sits on a plateau and that is its licence: over Wan Chai and
    Causeway Bay's 140 crossings the nearest zigzag is **0.3 m** from one and
    **197 m** from the next, so every value from 1 to 100 m names the same
    crossing.
    """

    layer: SourceLayer
    codes: frozenset[str]
    within_m: float
    # A `LINETYPE` that says zebra outright. Mong Kok publishes `ZEBRA4`.
    line_types: frozenset[str]


@dataclass(frozen=True)
class Crossings(LayerSpec):
    """Published pedestrian-crossing stripes, drawn by `pipeline/crossings.py`
    (`P3-35g2`).

    **Read, not invented**: `DTAD_CROSSING_LINE` surveys each stripe as its own
    rectangle — a closed ring, or four loose edges that close into one — so the
    stage draws the faces the publisher's lines enclose and nothing else. No
    dimension is declared here because none is used: width, length and spacing
    are the survey's (p50 0.600 x 3.500 m at 0.6 m gaps, against the sheet's
    500-700).

    ⚠️ **`line_types` is a whitelist and is matched case-folded**: the layer
    carries `SOLID` and `Solid` for one thing. What it leaves out is refused and
    counted per code — `CROSS_BOUNDARY` is the outline of the whole crossing and
    would paint it solid; `CROSS_ANNO` is a label; `RM1077` is slow-down bars.

    ⚠️ **No material here**, as `BoxJunctions` says of itself: the two paints are
    authored in `game/tuning/` and dispatched on the glTF material names in
    `pipeline/crossings.py`.
    """

    line_types: frozenset[str]
    zebra: ZebraEvidence
    lift_m: float
    max_offset_m: float
    max_stripe_width_m: float


# Both layers are read for the same two things.
_CROSSING_ROLES = ("line_type", "level")


def _codes(body: dict[str, Any], key: str, where: str, *, empty_ok: bool = False) -> frozenset[str]:
    raw = _require(body, key, where)
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise ValueError(f"{where}:{key} must be a list, got {raw!r}")
    codes = frozenset(str(value).strip().upper() for value in raw)
    if not codes and not empty_ok:
        raise ValueError(f"{where}:{key} is empty; a block that draws nothing is a mistake")
    return codes


def _positive(body: dict[str, Any], key: str, where: str, why: str) -> float:
    value = float(_require(body, key, where))
    if value <= 0.0:
        raise ValueError(f"{where}:{key} is {value}; {why}")
    return value


def _crossings(body: Any, where: str) -> Crossings | None:
    """The optional published-crossing block (`P3-35g2`).

    Absent, the region ships no `crossings.glb` and the manifest names none.
    What is not offered is a crossing at every signalised junction: nothing here
    knows which junctions are signalised (`Q77`), and a derived crossing renders
    perfectly.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    line_types = _codes(body, "line_types", where)
    zebra_body = _require(body, "zebra", where)
    zebra_where = f"{where}:zebra"
    if not isinstance(zebra_body, dict):
        raise ValueError(f"{zebra_where} must be a mapping, got {zebra_body!r}")
    zebra = ZebraEvidence(
        layer=_source_layer(zebra_body, zebra_where, _CROSSING_ROLES),
        codes=_codes(zebra_body, "codes", zebra_where),
        within_m=_positive(zebra_body, "within_m", zebra_where, "nothing would ever be a zebra"),
        line_types=_codes(zebra_body, "line_types", zebra_where, empty_ok=True),
    )
    stray = zebra.line_types - line_types
    if stray:
        raise ValueError(
            f"{zebra_where}:line_types names {sorted(stray)}, which {where}:line_types does not "
            f"draw; a zebra that is refused before it is coloured is never painted"
        )

    return Crossings(
        **_spec_header(body, where, _CROSSING_ROLES),
        line_types=line_types,
        zebra=zebra,
        lift_m=_positive(
            body, "lift_m", where, "paint coplanar with the road it is painted on z-fights"
        ),
        max_offset_m=_positive(body, "max_offset_m", where, "every crossing would be too far"),
        max_stripe_width_m=_positive(
            body, "max_stripe_width_m", where, "every stripe would be refused"
        ),
    )
