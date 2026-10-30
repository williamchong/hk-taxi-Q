"""`signals:` — the signalled junctions and their authored stages (`P3-3a`, `Q173`).

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.

Nothing in this file knows a Hong Kong fact: which marking code is the signal
stop line arrives from `config/hong_kong.yaml` (hard rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import LayerSpec, _measures, _require, _spec_header

# The roles `heads:` maps onto the publisher's columns.
_HEAD_ROLES = ("code", "level")


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
        **_measures(body, where, ("max_offset_m", "assembly_merge_m"), positive=True),
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
