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
class ExitSign:
    """A station exit's portal (`P3-107`), drawn on the wall the 3D map
    already stands there: a doorway `door_width_m` x `door_height_m` dark as
    the stairwell, a jamb of the station's colour each side, a `fascia` band
    over the lintel lettered with the station's Chinese and English names,
    and the exit's letter on a square plate beside the door.

    It hangs on the shipped wall nearest the exit within `wall_reach_m` — the
    stair head the 3D map draws, or the building the exit opens from — the
    wall facing the exit's road preferred by `facing_weight_m` a unit of
    `1 - cos`. Where no wall is in reach the fascia tops a post, both faces
    lettered. Every number is authored: nothing publishes the portal.
    """

    font_source: str
    font_weight: float
    flatten_em: float
    wall_reach_m: float
    facing_weight_m: float
    door_width_m: float
    door_height_m: float
    jamb_m: float
    fascia_m: float
    depth_m: float
    letter_m: float
    letter_mount_m: float
    off_wall_m: float
    lift_m: float
    # The fascia's two lines, `{station}` the table's name: `{station}站`.
    fascia_zh: str
    fascia_en: str
    fascia: Colour
    opening: Colour
    trim: Colour
    ink: Colour
    letter_ground: Colour
    letter_ink: Colour

    @property
    def width_m(self) -> float:
        """The portal across its two jambs."""
        return self.door_width_m + 2.0 * self.jamb_m


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
    station_exit: ExitSign | None = None


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

    station_exit = _exit_sign(body.get("station_exit"), f"{where}:station_exit")
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
        station_exit=station_exit,
    )


def _exit_sign(body: Any, where: str) -> ExitSign | None:
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    sign = ExitSign(
        font_source=str(_require(body, "font_source", where)),
        font_weight=_positive(body, "font_weight", where, "a weight of nothing"),
        flatten_em=_positive(body, "flatten_em", where, "a curve never flattened"),
        wall_reach_m=_positive(body, "wall_reach_m", where, "every portal on a post"),
        facing_weight_m=float(_require(body, "facing_weight_m", where)),
        door_width_m=_positive(body, "door_width_m", where, "a door of no width"),
        door_height_m=_positive(body, "door_height_m", where, "a door of no height"),
        jamb_m=_positive(body, "jamb_m", where, "a jamb of no width"),
        fascia_m=_positive(body, "fascia_m", where, "a fascia of no height"),
        depth_m=_positive(body, "depth_m", where, "a frame of no depth"),
        letter_m=_positive(body, "letter_m", where, "a letter plate of no size"),
        letter_mount_m=_positive(body, "letter_mount_m", where, "a letter plate on the ground"),
        off_wall_m=float(_require(body, "off_wall_m", where)),
        lift_m=_positive(body, "lift_m", where, "lettering inside the fascia"),
        fascia_zh=str(_require(body, "fascia_zh", where)),
        fascia_en=str(_require(body, "fascia_en", where)),
        fascia=_colour(body, "fascia", where),
        opening=_colour(body, "opening", where),
        trim=_colour(body, "trim", where),
        ink=_colour(body, "ink", where),
        letter_ground=_colour(body, "letter_ground", where),
        letter_ink=_colour(body, "letter_ink", where),
    )
    for key in ("fascia_zh", "fascia_en"):
        if "{station}" not in getattr(sign, key):
            raise ValueError(f"{where}:{key} must name the {{station}}")
    if sign.off_wall_m < 0.0:
        raise ValueError(f"{where}: off_wall_m is a gap; a negative one buries the portal")
    if sign.letter_mount_m + 0.5 * sign.letter_m > sign.door_height_m:
        raise ValueError(f"{where}: the letter plate rises past the lintel")
    return sign
