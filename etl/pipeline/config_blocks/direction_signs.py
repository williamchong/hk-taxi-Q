"""`direction_signs:`.

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.
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
from pipeline.config_blocks.crossings import _positive

_PLATE_ROLES = ("code",)
_LEADER_ROLES = ("kind",)
_BEAM_ROLES = ("kind",)
_COLOUR_ROLES = ("field", "ink", "steel")


@dataclass(frozen=True)
class DirectionSigns(LayerSpec):
    """TD's overhead direction signs on their gantries (`P3-105`, `Q265`), drawn
    by `pipeline/direction_signs.py`.

    `layer` is the plate drawings (`DTAD_DS_PLATE_LINE`): each board's whole
    face as line-work, a callout set beside the road at `drawing_units_per_m`.
    `leaders` ties a callout to the road (`leader_kind`), and `beams` is the
    gantry's span across it (`beam_kind`). A board whose `code` carries
    `gantry_code` is a gantry's; nothing else is drawn.

    **The face, its size, its place and the beam are TD's**; the steel is not.
    TD draws no leg, so a leg stands at each beam end pushed off the drawn
    asphalt by `leg_clear_m`, at most `leg_max_push_m`; an end that cannot get
    off within it carries no leg (a cantilever). `colours` names three
    `signs.colours` entries: the board's field, its ink, and the steel. A
    gantry whose board would stand in a deck (a deck's walking surface over the
    beam, under the board's top plus `deck_depth_m`) moves along its normal to
    the nearest clear line, at most `clear_max_push_m`.

    The fill (`Q265`): Chinese is closed outlines (drawn twice; deduplicated),
    filled and thickened by `bold_m`; English is single centre-line strokes,
    drawn `stroke_m` wide; a closed face of open line-work under
    `counter_max_m2` is a letter's counter and only stroked.
    """

    leaders: SourceLayer
    beams: SourceLayer
    gantry_code: str
    leader_kind: str
    beam_kind: str
    drawing_units_per_m: float
    reach_m: float
    leader_touch_m: float
    beam_reach_m: float
    host_max_m: float
    panel_min_m2: float
    counter_max_m2: float
    stroke_m: float
    bold_m: float
    px_per_m: int
    supersample: int
    pad_px: int
    clearance_m: float
    board_thickness_m: float
    face_lift_m: float
    beam_depth_m: float
    beam_width_m: float
    leg_width_m: float
    leg_clear_m: float
    leg_max_push_m: float
    deck_depth_m: float
    clear_max_push_m: float
    colours: dict[str, str]


def _whole(body: dict[str, Any], key: str, where: str, low: int) -> int:
    value = _require(body, key, where)
    if not isinstance(value, int) or isinstance(value, bool) or value < low:
        raise ValueError(f"{where}:{key} must be a whole number of at least {low}, got {value!r}")
    return value


def _direction_signs(body: Any, where: str) -> DirectionSigns | None:
    """The optional overhead-direction-sign block. Absent, the region ships no
    `direction_signs.glb` and the manifest names none."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    header = _spec_header(body, where, _PLATE_ROLES)
    colours = _require(body, "colours", where)
    if not isinstance(colours, dict):
        raise ValueError(f"{where}:colours must be a mapping, got {colours!r}")
    missing = [role for role in _COLOUR_ROLES if role not in colours]
    if missing:
        raise ValueError(f"{where}:colours is missing {', '.join(missing)}")
    bold = float(_require(body, "bold_m", where))
    if bold < 0.0:
        raise ValueError(f"{where}:bold_m is {bold}; a stroke cannot be thinned below its outline")
    return DirectionSigns(
        **header,
        leaders=_source_layer(_require(body, "leaders", where), f"{where}:leaders", _LEADER_ROLES),
        beams=_source_layer(_require(body, "beams", where), f"{where}:beams", _BEAM_ROLES),
        gantry_code=str(_require(body, "gantry_code", where)),
        leader_kind=str(_require(body, "leader_kind", where)),
        beam_kind=str(_require(body, "beam_kind", where)),
        drawing_units_per_m=_positive(
            body, "drawing_units_per_m", where, "a drawing at no scale has no size"
        ),
        reach_m=_positive(body, "reach_m", where, "a callout beside the road would not be read"),
        leader_touch_m=_positive(body, "leader_touch_m", where, "no leader would touch a board"),
        beam_reach_m=_positive(body, "beam_reach_m", where, "no leader would reach a beam"),
        host_max_m=_positive(body, "host_max_m", where, "no beam would be over a road"),
        panel_min_m2=_positive(body, "panel_min_m2", where, "every letter would be a panel"),
        counter_max_m2=_positive(
            body, "counter_max_m2", where, "every counter would fill its letter"
        ),
        stroke_m=_positive(body, "stroke_m", where, "the English would not be drawn"),
        bold_m=bold,
        px_per_m=_whole(body, "px_per_m", where, 8),
        supersample=_whole(body, "supersample", where, 1),
        pad_px=_whole(body, "pad_px", where, 1),
        clearance_m=_positive(body, "clearance_m", where, "a board on the road is a wall"),
        board_thickness_m=_positive(body, "board_thickness_m", where, "a board has a back"),
        face_lift_m=_positive(
            body, "face_lift_m", where, "a face coplanar with its board z-fights"
        ),
        beam_depth_m=_positive(body, "beam_depth_m", where, "a beam has a section"),
        beam_width_m=_positive(body, "beam_width_m", where, "a beam has a section"),
        leg_width_m=_positive(body, "leg_width_m", where, "a leg has a section"),
        leg_clear_m=_positive(body, "leg_clear_m", where, "a leg on the kerb line is in the road"),
        leg_max_push_m=_positive(body, "leg_max_push_m", where, "no leg would leave the road"),
        deck_depth_m=_positive(body, "deck_depth_m", where, "a deck has an underside"),
        clear_max_push_m=_positive(
            body, "clear_max_push_m", where, "no gantry under a deck would move clear"
        ),
        colours={role: str(colours[role]) for role in _COLOUR_ROLES},
    )
