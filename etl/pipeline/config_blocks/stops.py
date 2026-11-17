"""`stops:`.

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import _require
from pipeline.config_blocks.crossings import _positive

# The kinds of stop a pole marks, and the shelter a tram stop takes.
BUS, MINIBUS, TAXI = "bus_stop", "minibus_stop", "taxi_point"
POLE_KINDS = (BUS, MINIBUS, TAXI)

# A colour is a NAME in `signs.colours`, the one livery table outside
# `materials:` (`test_no_colour_escapes_the_materials_table`); `stops.py`
# resolves it and refuses a name the table does not carry.
Colour = str


@dataclass(frozen=True)
class StopFlag:
    """One kind's flag: a plate across the footway on top of a pole, with a band
    across its head. Every number is authored — nothing publishes a bus stop
    flag's size or livery."""

    width_m: float
    height_m: float
    mount_m: float
    colour: Colour
    band: Colour


@dataclass(frozen=True)
class TramShelter:
    """A tram stop's shelter: a roof on two posts beside the track.

    `offset_m` is from the track's centreline to the shelter's, on the left of
    travel — the side a tram's doors open on. It must clear `trams.tres`'
    body. The two posts are solid and the roof is not (`Q242`, the user's
    call): the game draws no island, so a post can stand in a lane.
    """

    offset_m: float
    length_m: float
    width_m: float
    height_m: float
    roof_m: float
    colour: Colour
    roof: Colour


@dataclass(frozen=True)
class Stops:
    """Authored furniture at published stops, stood by `pipeline/stops.py`
    (`P3-93` to `P3-95`).

    **Where is read, what is authored.** A pole stands where `bus_routes.json`
    and `fares.json` already place a stop — the operators' own stop points and
    TD's taxi points — and a shelter where `tram_lines.json` binds a tram stop.
    The furniture itself is ours: nothing publishes it (0 of iB1000's
    open-sided blocks lie within 6 m of a stop).
    """

    outset_m: float
    max_shift_m: float
    merge_m: float
    pole_radius_m: float
    plate_thickness_m: float
    pole: Colour
    flags: dict[str, StopFlag]
    tram: TramShelter | None


def _colour(body: dict[str, Any], key: str, where: str) -> Colour:
    return str(_require(body, key, where))


def _stops(body: Any, where: str) -> Stops | None:
    """The optional stop furniture block. Absent, the region ships no
    `stops.glb` and the manifest names none."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw = _require(body, "flags", where)
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{where}:flags must be a non-empty mapping of kind to flag")
    flags: dict[str, StopFlag] = {}
    for kind, entry in raw.items():
        spot = f"{where}:flags:{kind}"
        if kind not in POLE_KINDS:
            raise ValueError(f"{spot} is not one of {', '.join(POLE_KINDS)}")
        if not isinstance(entry, dict):
            raise ValueError(f"{spot} must be a mapping, got {entry!r}")
        flags[kind] = StopFlag(
            width_m=_positive(entry, "width_m", spot, "a flag of no width"),
            height_m=_positive(entry, "height_m", spot, "a flag of no height"),
            mount_m=_positive(entry, "mount_m", spot, "a flag on the ground"),
            colour=_colour(entry, "colour", spot),
            band=_colour(entry, "band", spot),
        )
        if flags[kind].mount_m < 0.5 * flags[kind].height_m:
            raise ValueError(
                f"{spot}: mount_m is the flag's middle; this one hangs into the ground"
            )

    tram = body.get("tram")
    if tram is not None and not isinstance(tram, dict):
        raise ValueError(f"{where}:tram must be a mapping, got {tram!r}")
    spot = f"{where}:tram"
    if tram is not None and float(tram.get("roof_m", 0.0)) >= float(tram.get("height_m", 0.0)):
        raise ValueError(f"{spot}: roof_m is the roof's own depth and must be under height_m")
    return Stops(
        outset_m=_positive(body, "outset_m", where, "a pole on the kerb line"),
        max_shift_m=_positive(body, "max_shift_m", where, "every pole would be refused"),
        merge_m=_positive(body, "merge_m", where, "no two stops would share a pole"),
        pole_radius_m=_positive(body, "pole_radius_m", where, "a pole of no width"),
        plate_thickness_m=_positive(body, "plate_thickness_m", where, "a flag of no depth"),
        pole=_colour(body, "pole_colour", where),
        flags=flags,
        tram=None
        if tram is None
        else TramShelter(
            offset_m=_positive(tram, "offset_m", spot, "a shelter on the track"),
            length_m=_positive(tram, "length_m", spot, "a shelter of no length"),
            width_m=_positive(tram, "width_m", spot, "a shelter of no width"),
            height_m=_positive(tram, "height_m", spot, "a shelter of no height"),
            roof_m=_positive(tram, "roof_m", spot, "a roof of no depth"),
            colour=_colour(tram, "colour", spot),
            roof=_colour(tram, "roof", spot),
        ),
    )
