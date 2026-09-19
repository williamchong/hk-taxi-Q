"""The drawn road, as every stage that stands something on it reads it.

`roadsurface.json`'s `carriageway[]` table joined to `roadgraph.json`'s polylines:
per level-0 edge, the ribbon `surface.py` drew and — where a region is built — the
kerb-to-kerb corridor it lies in. One reader (`P3-35d`, `Q133`), because there were
four: this one (then in `arrows.py`, imported sideways by `signs` and `lamps`),
`railings.ribbons`, `roadmarks._drawn_widths` and `fence._half_width_at_end`, and
each met `P3-33c` on its own — `Q106`, `Q130`, and the registration defect
`Ribbon.kerb_target` was left with.

🔴 **Two extents, and a reader owes the question which one it means (`Q57`).** A
level-0 ribbon's rails are its TERRITORY, a share of the carriageway: on a road
several centrelines share, a rail is a line down the middle of the asphalt. The
CORRIDOR is kerb to kerb through every share. Paint in a lane wants the ribbon;
anything that stands at a kerb wants the corridor.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pipeline.polyline import Snap, frame, plan_lengths


def nearside(heading_deg: float) -> np.ndarray:
    """The unit vector to the **nearside** of an edge, in game plan space.

    Nearside is *left* of travel — the rail `surface.mitres` offsets to, and the
    side `Snap.offset_m` is positive on.

    ⚠️ **Public, and spelled exactly once, because a flip here mirrors every
    side-keyed feature in the city and still renders as a city.** `_frame`'s own
    docstring records that this vector was written out three times in the first
    draft of this module and that "a sign fix lands in two of three places"; it
    was then written a fourth time in `pipeline/signs.py`, which is what made it
    public. `tests/test_signs.py` pins it against `surface.mitres` itself rather
    than against this comment.
    """
    return -frame(heading_deg)[1]


@dataclass(frozen=True)
class Ribbon:
    """What `surface.py` drew for one edge, as a consumer needs to read it.

    ⚠️ **Public because `pipeline/signs.py` reads it too**, and reads it for the
    same reason: the drawn half-width is `surface.py`'s answer after the widening
    and after `Q23`'s per-station adjustment, so a second implementation of it
    would be a second join in `Q56`'s sense — disagreeing would tell us one was
    wrong and never which.

    ⚠️ **`carriageway_m` is the exception to that first sentence**: it comes off
    `roadgraph.json`, not off anything `surface.py` drew, and only the lane snap
    reads it. `signs` and `lamps` import this class and inherit a
    field they never touch.
    """

    lanes: int
    # ⚠️ **The SURVEYED carriageway (`roadgraph.json`'s `width_m`), not the drawn
    # ribbon.** `half_width_m` below is what `surface.py` drew after
    # `surface.floor_default_m`; this is what TD, iB1000 and HyD measured. The
    # two frames meet in `_lane_of` and nowhere else, and conflating them is what
    # `Q96` was — see that function for what it cost and on how many edges.
    carriageway_m: float
    one_way: bool
    # Normalised distance along the published polyline at each station, and the
    # drawn half-width there. Per station rather than per edge because `Q23`
    # widens the ribbon station by station.
    at: np.ndarray
    half_width_m: np.ndarray
    # 🔴 **Where the drawn ribbon's middle sits, per station, positive to the
    # nearside** — `roadsurface.json`'s `offset_m`, so the ribbon is
    # `[offset - half, offset + half]` and never `±half` about the centreline
    # (`Q106`). It was 0.0 on every level-0 edge when this class was written;
    # since `P3-33c` a level-0 ribbon's rails are its territory, and 288 of 734
    # level-0 edges are drawn more than 1 m off their centreline. `EXPO DRIVE
    # EAST` `e657`'s arrows sat 2.2 m out of the painted lanes for want of it.
    offset_m: np.ndarray
    # The centreline itself, `(n, 2)` as `(x, z)` per station. ⚠️ **Carried so a
    # consumer can take the foot of a snap from the polyline rather than
    # reconstruct it** — see `foot_at`.
    plan: np.ndarray
    # Deck height at each of those stations, straight off the published
    # polyline. ⚠️ **This is what an arrow's height comes from, rather than a
    # fresh snap at its nose and tail.** A second snap is a second join with no
    # memory of the host edge: measured, **43 of 747** arrows took at least one
    # endpoint from a *different* edge, disagreeing with the ribbon they are
    # drawn on by up to **0.515 m** against a `lift_m` of 0.015. Interpolating
    # here reproduces `Snap.y` to 1.8e-15 m, because it is the same linear
    # interpolation — it is a faithful substitute, not an approximation.
    height_m: np.ndarray
    trim_start_m: float
    trim_end_m: float
    length_m: float

    def half_width_at(self, t: float) -> float:
        """The drawn half-width at a normalised position along the edge."""
        return float(np.interp(t, self.at, self.half_width_m))

    def offset_at(self, t: float) -> float:
        """The drawn ribbon's middle at a normalised position, nearside positive."""
        return float(np.interp(t, self.at, self.offset_m))

    def foot_at(self, t: float) -> np.ndarray:
        """The point on the centreline at `t`, in game plan space.

        ⚠️ **Read from the polyline, never reconstructed as
        `point - offset_m * nearside`.** `Snap.offset_m` is `±distance_m` to the
        **clamped** projection, so for anything past an edge's end the
        displacement has an along-edge component and that subtraction lands off
        the centreline. Measured on an edge from (0,0) to (100,0) with a point at
        (105, 0) — dead on the axis, 5 m past the end — the reconstruction gives
        (105, -5), five metres off a road the point is standing in the middle of.
        Where the snap did not clamp the two agree to the bit.
        """
        return np.array(
            [
                float(np.interp(t, self.at, self.plan[:, 0])),
                float(np.interp(t, self.at, self.plan[:, 1])),
            ]
        )

    def kerb_target(self, snap: Snap, outset_m: float) -> tuple[float, float, float, np.ndarray]:
        """The registration target `outset_m` past the drawn kerb, and its frame.

        Returns `(side, half_width_m, target_m, point)`: the kerb side (`+1`
        nearside — a point exactly on the centreline has no side to keep, and
        the nearside is the one a left-driving city's traffic passes closest
        to), the drawn half-width at the snap, the signed across-edge target,
        and the placed point.

        ⚠️ **The point comes off the polyline (`foot_at`), never from
        `point - offset_m * nearside`** — `Snap.offset_m` is `±distance_m` to
        the *clamped* projection, so a post past an edge's end has an along-edge
        component in that vector and the subtraction lands off the centreline;
        `foot_at` carries the measurement. Only the arithmetic is shared
        (`Q100`): whether to move at all, `Q78`'s outward-only clamp and every
        counter stay with each stage.
        """
        half_width_m = self.half_width_at(snap.t)
        side = 1.0 if snap.offset_m >= 0.0 else -1.0
        target_m = side * (half_width_m + outset_m)
        point = self.foot_at(snap.t) + target_m * nearside(snap.heading_deg)
        return side, half_width_m, target_m, point


def ribbons(graph: dict, surface: dict) -> dict[int, Ribbon]:
    """The drawn ribbon, keyed by edge id.

    ⚠️ **Read from `roadsurface.json` rather than recomputed.** The drawn
    half-width is `surface.py`'s answer after the widening and after `Q23`'s
    per-station adjustment, and a second implementation of it here would be a
    second join in `Q56`'s sense — disagreeing would tell us one was wrong and
    never which.
    """
    widths = {int(entry["edge"]): entry for entry in surface["carriageway"]}
    drawn_ribbons: dict[int, Ribbon] = {}
    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        drawn = widths.get(int(edge["id"]))
        if drawn is None:
            continue
        points = np.asarray(edge["polyline"], dtype=np.float64)
        along = plan_lengths(points)
        total = float(along[-1])
        half = np.asarray(drawn["half_width_m"], dtype=np.float64)
        offset = np.asarray(drawn["offset_m"], dtype=np.float64)
        carriageway_m = float(edge["width_m"])
        if (
            total <= 0.0
            or len(half) != len(along)
            or len(offset) != len(along)
            or not carriageway_m > 0.0
        ):
            # A width list that does not match the polyline it was measured on
            # is a contract break, not a rounding problem. Skipped rather than
            # interpolated across, and visible as a symbol that found no lane.
            #
            # ⚠️ **A missing surveyed width is refused HERE and not in
            # `_lane_of`**, so it lands in `no_lane` rather than in
            # `outside_carriageway`. An absent width and an arrow past a kerb are
            # two populations, and `Q90`'s `ends_no_target` is the precedent for
            # keeping the second out of the first's count. This is also the only
            # place with the edge id to name.
            # ⚠️ **`not x > 0.0`, never `x <= 0.0`** — the second is False for
            # NaN, which would divide through to a silent lane 0.
            continue
        trim = drawn.get("trim_m") or [0.0, 0.0]
        drawn_ribbons[int(edge["id"])] = Ribbon(
            lanes=int(edge["lanes"]),
            carriageway_m=carriageway_m,
            one_way=str(edge["direction"]) != "both",
            at=along / total,
            half_width_m=half,
            offset_m=offset,
            plan=np.column_stack([points[:, 0], points[:, 2]]),
            height_m=points[:, 1],
            trim_start_m=float(trim[0]),
            trim_end_m=float(trim[1]),
            length_m=total,
        )
    return drawn_ribbons
