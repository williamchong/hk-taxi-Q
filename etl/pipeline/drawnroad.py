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
from pathlib import Path

import numpy as np

from pipeline.config import Config
from pipeline.polyline import Snap, frame, plan_lengths
from pipeline.region import KERB, REGION_NAME, read_region


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
    # 🔴 **The ROAD this edge lies in, kerb to kerb** — `carriageway_region.json`'s
    # running kerb lines (`_kerbs`), at the region's own DENSE stations
    # (`kerb_at_t`, normalised like `at`). `None` where no region is built or the
    # edge has no territory; `kerb_at` then answers with the ribbon.
    # ⚠️ **Not the ribbon**: its rail is its territory's edge, a SHARE (`Q57`), and
    # on Wan Chai that stands more than 0.5 m from the kerb on 800 of 1,468
    # edge-sides. 🔴 **And not `roadsurface.json`'s `corridor_*` either — built
    # first, measured, and withdrawn.** That table is per GRAPH VERTEX, and a
    # straight street's two vertices are both at junctions, where a kerb-to-kerb
    # ray runs off down the side street. Graded against where iB1000's surveyed
    # lamp posts stand, it reads 24.2% of Wan Chai's as in the road against 21.8%
    # for the `±half` it replaced, and these stations 14.9% (`Q133`).
    kerb_at_t: np.ndarray | None = None
    kerb_left_m: np.ndarray | None = None
    kerb_right_m: np.ndarray | None = None

    def half_width_at(self, t: float) -> float:
        """The drawn half-width at a normalised position along the edge."""
        return float(np.interp(t, self.at, self.half_width_m))

    def offset_at(self, t: float) -> float:
        """The drawn ribbon's middle at a normalised position, nearside positive."""
        return float(np.interp(t, self.at, self.offset_m))

    def kerb_at(self, t: float) -> tuple[float, float]:
        """`(middle, half)` of the road at `t`: the kerbs stand at `middle ± half`,
        nearside positive, measured from this edge's centreline."""
        if self.kerb_at_t is None or self.kerb_left_m is None or self.kerb_right_m is None:
            return self.offset_at(t), self.half_width_at(t)
        # Left is the nearside (`region.py`'s `test_left_is_left_of_travel`), so
        # the kerbs stand at `+left` and `-right`.
        left = float(np.interp(t, self.kerb_at_t, self.kerb_left_m))
        right = float(np.interp(t, self.kerb_at_t, self.kerb_right_m))
        return (left - right) / 2.0, (left + right) / 2.0

    def past_kerb_m(self, snap: Snap) -> float:
        """How far `snap` stands past the nearer kerb; negative is in the road.

        🔴 **About the road's middle, never the centreline.** `abs(snap.offset_m)
        - half` is this about a road symmetric on its centreline, which was every
        level-0 edge until `P3-33c` and is `Q106`'s defect since: signs and lamps
        both asked it that way, and the road they cleared was not the one drawn.
        """
        middle_m, half_m = self.kerb_at(snap.t)
        return abs(snap.offset_m - middle_m) - half_m

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
        nearside — a point exactly on the road's middle has no side to keep, and
        the nearside is the one a left-driving city's traffic passes closest
        to), the road's half-width at the snap, the signed across-edge target
        FROM THE CENTRELINE, and the placed point.

        🔴 **The kerb is the ROAD's (`kerb_at`), and the side is the nearer one.**
        Until `P3-35d` this read `side * (half + outset)` about the centreline
        with `side = sign(snap.offset_m)`: on a road lying 9 m one side of its
        centreline and 7 m the other it aimed both kerbs a metre wrong, and a
        post surveyed between the centreline and the middle of the road was sent
        to the far kerb. `target_m` stays in the centreline's frame, so a
        caller's `abs(target_m - snap.offset_m)` is still the move it made.

        ⚠️ **The point comes off the polyline (`foot_at`), never from
        `point - offset_m * nearside`** — `Snap.offset_m` is `±distance_m` to
        the *clamped* projection, so a post past an edge's end has an along-edge
        component in that vector and the subtraction lands off the centreline;
        `foot_at` carries the measurement. Only the arithmetic is shared
        (`Q100`): whether to move at all, `Q78`'s outward-only clamp and every
        counter stay with each stage.
        """
        middle_m, half_width_m = self.kerb_at(snap.t)
        # `>=`, so `-0.0` — which `Segments.nearest` really returns for a point on
        # the line — reads as the nearside, the convention every caller pins.
        side = 1.0 if snap.offset_m - middle_m >= 0.0 else -1.0
        target_m = middle_m + side * (half_width_m + outset_m)
        point = self.foot_at(snap.t) + target_m * nearside(snap.heading_deg)
        return side, half_width_m, target_m, point


def kerbed_ribbons(
    city: Config, out_dir: Path, region_id: str, graph: dict, surface: dict
) -> dict[int, Ribbon]:
    """`ribbons`, with the region's kerbs where the city builds a region.

    For a stage that stands something AT a kerb. Paint in a lane wants `ribbons`
    alone: `arrows` reads the ribbon and never the road.
    """
    if city.carriageway_region is None:
        return ribbons(graph, surface)
    return ribbons(graph, surface, read_region(out_dir / REGION_NAME, region_id))


def ribbons(graph: dict, surface: dict, region: dict | None = None) -> dict[int, Ribbon]:
    """The drawn ribbon, keyed by edge id.

    ⚠️ **Read from `roadsurface.json` rather than recomputed.** The drawn
    half-width is `surface.py`'s answer after the widening and after `Q23`'s
    per-station adjustment, and a second implementation of it here would be a
    second join in `Q56`'s sense — disagreeing would tell us one was wrong and
    never which.
    """
    widths = {int(entry["edge"]): entry for entry in surface["carriageway"]}
    # This region's own runs only: a neighbour's run is published under
    # `foreign` and is drawn, and furnished, by its owner (`Q116`).
    territories = {
        int(row["edge"]): row for row in (region or {}).get("territories", ()) if not row["foreign"]
    }
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
            **_kerbs(territories.get(int(edge["id"])), total),
        )
    return drawn_ribbons


def _kerbs(territory: dict | None, length_m: float) -> dict[str, np.ndarray | None]:
    """A territory's running kerb lines as `Ribbon`'s three kerb fields.

    🔴 **A side is read only at the stations where it ENDED AT A KERB, and is the
    straight line between them** — `surface_region.bridged`'s own reading, and no
    knob. At a side-street mouth the ray runs off down the side street, so the
    station there reads a kerb 16 m away and a post on the corner reads as deep
    in the road: taken raw, 74 of Wan Chai's 1,125 hosted lamp posts stood more
    than 2 m inside it (worst -16.5 m) and 43 of them were within 15 m of an end
    of their edge; read this way it is 47, worst -5.9 m (`Q133`).
    ⚠️ A side with NO kerbed station — an inner share of a road several
    centrelines divide — has no kerb line of its own and takes the corridor's.

    Refused WHOLE where the lists disagree in length or the stations do not run
    forward — a half-read kerb is a post registered against one side of a road —
    and the edge falls back to its ribbon.
    """
    if territory is None:
        return {}
    along = np.asarray(territory["along_m"], dtype=np.float64)
    sides: list[np.ndarray] = []
    for side in ("left", "right"):
        extent = np.asarray(territory[f"{side}_m"], dtype=np.float64)
        corridor = np.asarray(territory[f"{side}_kerb_m"], dtype=np.float64)
        ends = territory[f"{side}_end"]
        if not len(along) == len(extent) == len(corridor) == len(ends) >= 2:
            return {}
        kerbed = np.flatnonzero([end == KERB for end in ends])
        if len(kerbed) == 0:
            sides.append(corridor)
        else:
            sides.append(np.interp(along, along[kerbed], extent[kerbed]))
    if np.any(np.diff(along) < 0.0):
        return {}
    return {"kerb_at_t": along / length_m, "kerb_left_m": sides[0], "kerb_right_m": sides[1]}
