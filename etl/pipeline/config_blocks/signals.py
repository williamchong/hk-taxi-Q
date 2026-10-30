"""`signals:` — the signalled junctions and their authored stages (`P3-3a`, `Q173`).

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.

Nothing in this file knows a Hong Kong fact: which marking code is the signal
stop line arrives from `config/hong_kong.yaml` (hard rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    LayerSpec,
    _measures,
    _parse_hex,
    _require,
    _spec_header,
)

# The roles `heads:` maps onto the publisher's columns.
_HEAD_ROLES = ("code", "level")
# The head's four colours: the housing, and each lens's dark glass. The lit
# colour is the shader's (`signal_heads.tres`); the vertex carries the unlit.
HEAD_COLOURS = ("body", "red", "amber", "green")
# The lens order down the face, top to bottom, which is also each lens's
# circuit: `UV.x` is `index + 1` (`tools/make_signal_heads.py`).
HEAD_LENSES = ("red", "amber", "green")


def is_signal_head(code: str, prefixes: tuple[str, ...], refused: tuple[str, ...]) -> bool:
    """Whether a published head code names a signal head: a declared letter, digits, an
    optional `L`/`R`, and not in `refused` (`Q76`).

    🔴 **A rule about SPELLING, and nothing published says the spelling means
    anything** (`Q76`: the column has no domain). It admits; it never describes —
    `P` is not primary nor `S` secondary (`Q173`: `P` binds 131 / 33, `S` 20 / 14).
    `PTR01` leaves digits behind a letter and is refused, the near miss.
    """
    if code in refused:
        return False
    for prefix in prefixes:
        if not code.startswith(prefix):
            continue
        rest = code[len(prefix) :]
        if rest.endswith(("L", "R")):
            rest = rest[:-1]
        if rest.isdigit():
            return True
    return False


@dataclass(frozen=True)
class HeadDrawing:
    """The one head the library draws (`tools/make_signal_heads.py`, `P3-3e`).

    🔴 **One head for every admitted code** (`Q76`): nothing published says a
    `P` from an `S`, or how many aspects a head carries, so the drawing is
    authored and every post stands the same one. Values are `P3-17`'s.
    """

    mount_height_m: float
    post_radius_m: float
    post_headroom_m: float
    head_width_m: float
    head_height_m: float
    head_depth_m: float
    lens_diameter_m: float
    lens_lift_m: float
    post_sides: int
    lens_segments: int
    # sRGB, `HEAD_COLOURS` exactly. A printed specification, exempt from `Q33`'s
    # palette as `signs.colours` is: a red lens is TD's, not a reflectance.
    colours: dict[str, tuple[int, int, int]]


def _drawing(body: Any, where: str) -> HeadDrawing:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    counts: dict[str, int] = {}
    for name in ("post_sides", "lens_segments"):
        counts[name] = int(_require(body, name, where))
        if counts[name] < 3:
            raise ValueError(f"{where}:{name} must be at least 3, got {counts[name]}")
    raw = _require(body, "colours", where)
    if not isinstance(raw, dict) or set(raw) != set(HEAD_COLOURS):
        raise ValueError(f"{where}:colours must name exactly {list(HEAD_COLOURS)}")
    measures = _measures(
        body,
        where,
        (
            "mount_height_m",
            "post_radius_m",
            "post_headroom_m",
            "head_width_m",
            "head_height_m",
            "head_depth_m",
            "lens_diameter_m",
            "lens_lift_m",
        ),
        positive=True,
    )
    pitch = measures["head_height_m"] / len(HEAD_LENSES)
    if measures["lens_diameter_m"] > min(pitch, measures["head_width_m"]):
        # A lens wider than its share of the face overlaps its neighbour or
        # hangs off the housing.
        raise ValueError(f"{where}:lens_diameter_m does not fit the head's face")
    return HeadDrawing(
        **measures,
        **counts,
        colours={
            name: _parse_hex(str(raw[name]), f"{where}:colours.{name}") for name in HEAD_COLOURS
        },
    )


@dataclass(frozen=True)
class SignalHeads(LayerSpec):
    """The published signal heads (`P3-3a`, `P3-3e`, `Q173`): where a lamp
    stands, and a second witness to which junctions are signalled.

    🔴 **Read because the stop-line survey is half the estate** (`Q173`, the
    gate, 2026-10-30): of Wan Chai's 63 junctions carrying heads, 29 had an
    `RM1011` hosted and 34 had none, while the 198 junctions with no head had 4.
    """

    head_prefixes: tuple[str, ...]
    refuse_codes: tuple[str, ...]
    # How far a head may stand from its nearest level-0 edge and still be hosted.
    max_offset_m: float
    # Two points closer than this are one post: 470 of Wan Chai's 913 sit within
    # 0.05 m of another, the stack of aspects one surveyed post carries (`Q76`).
    assembly_merge_m: float
    # The registration (`Q60`, `Q78`): a post surveyed inside the drawn road is
    # moved out to `outset_m` past the kerb, never pulled in, and refused past
    # `max_shift_m`.
    outset_m: float
    max_shift_m: float
    # The AUTHORED head library the placements stand (`tools/make_signal_heads.py`,
    # committed): a `res://` path, as `parked.library` is.
    library: str
    drawing: HeadDrawing

    def is_head(self, code: str) -> bool:
        return is_signal_head(code, self.head_prefixes, self.refuse_codes)


def _heads(body: Any, where: str) -> SignalHeads | None:
    """The optional `heads:` sub-block. Absent, the stop lines alone signal."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    prefixes = _require(body, "head_prefixes", where)
    if not isinstance(prefixes, list) or not prefixes:
        raise ValueError(f"{where}:head_prefixes must be a non-empty list")
    prefixes = tuple(str(prefix) for prefix in prefixes)
    bad = [prefix for prefix in prefixes if not (prefix.isascii() and prefix.isupper())]
    if bad:
        # The gate does no case folding: a `p` would load clean and admit nothing.
        raise ValueError(f"{where}:head_prefixes must be upper-case letters; got {bad}")
    refused = body.get("refuse_codes") or []
    if not isinstance(refused, list):
        raise ValueError(f"{where}:refuse_codes must be a list")
    refused = tuple(str(code) for code in refused)
    dead = [code for code in refused if not is_signal_head(code, prefixes, ())]
    if dead:
        # The spelling already refuses it; listing it is dead config.
        raise ValueError(f"{where}:refuse_codes {dead} are already refused by head_prefixes")
    return SignalHeads(
        **_spec_header(body, where, _HEAD_ROLES),
        head_prefixes=prefixes,
        refuse_codes=refused,
        library=str(_require(body, "library", where)),
        drawing=_drawing(_require(body, "drawing", where), f"{where}:drawing"),
        **_measures(
            body,
            where,
            ("max_offset_m", "assembly_merge_m", "outset_m", "max_shift_m"),
            positive=True,
        ),
    )


@dataclass(frozen=True)
class Signals:
    """Where the published estate says a junction is signalled, and how its
    approaches are staged (`pipeline/signals.py`, `Q173`).

    🔴 **The junction is READ and the stages are AUTHORED.** A junction is
    signalled because a signal stop line is hosted at it; nothing published
    says which approaches share a green, so the stage rule is ours and
    `axis_tolerance_deg` is its one free value, swept in `Q173`.
    """

    # The `road_marks:` codes that are a signal's stop line. Read through that
    # block's own layers and host rule, so the stop line the cars stop at is the
    # one the paint stage drew.
    stop_line_codes: tuple[str, ...]
    # How far apart two approaches' travel axes (heading mod 180) may lie and
    # still share a green: same way or opposed.
    axis_tolerance_deg: float
    # The heads, read where a lamp stands and as a second witness to which
    # junctions are signalled. `None`: the stop lines alone.
    heads: SignalHeads | None = None


def _signals(body: Any, where: str) -> Signals | None:
    """The optional `signals:` block. Absent, the region ships no signal plan."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    codes = _require(body, "stop_line_codes", where)
    if not isinstance(codes, list) or not codes:
        raise ValueError(f"{where}:stop_line_codes must be a non-empty list")
    tolerance = _measures(body, where, ("axis_tolerance_deg",), positive=True)["axis_tolerance_deg"]
    if tolerance >= 90.0:
        # At 90 every axis is within reach of every other: one stage, every
        # approach green at once.
        raise ValueError(f"{where}:axis_tolerance_deg {tolerance} must be under 90")
    return Signals(
        stop_line_codes=tuple(str(code) for code in codes),
        axis_tolerance_deg=tolerance,
        heads=_heads(body.get("heads"), f"{where}:heads"),
    )
