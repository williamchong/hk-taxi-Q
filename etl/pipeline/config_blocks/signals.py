"""`signals:` — the signalled junctions and their authored stages (`P3-3a`, `Q173`).

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.

Nothing in this file knows a Hong Kong fact: which marking code is the signal
stop line arrives from `config/hong_kong.yaml` (hard rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import _measures, _require


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
    return Signals(stop_line_codes=tuple(str(code) for code in codes), axis_tolerance_deg=tolerance)
