"""Measuring along, and snapping to, the road graph's polylines.

A leaf: numpy only. That is the whole reason this module exists rather than the
pieces living where they grew up.

`plan_lengths` and its neighbours were in `roads.py`, and `Snap`/`Segments` were
in `fares.py` — which imports `roads`. `roads` imports `carriageway`, so
`carriageway.py` could not reach a nearest-edge snap without closing a hard
import cycle, and `Q94`'s lane row needs one at the roads stage. Hoisting is
what breaks it.

⚠️ **This is a primitive, and the repo's duplicate-deliberately rule does not
reach it.** `carriageway.py` is a second implementation of
`carriageway_margin.py`'s *measurement* and must stay one; a vectorised
point-to-polyline snap grades nothing, so a second copy would be cost with no
check bought. The precedent is `arrows.axis_residual_deg` and
`railings.AT_GRADE`, both "imported rather than restated".

⚠️ **Not `geometry.py`.** That module's contract is plan polygons, shape
`(n, 2)`; everything here takes a 3-D polyline `(n, 3)` and drops the height
column deliberately. Two different frames in one module is how a road ends up
measured against its own height — the split `_steps` already documents.

⚠️ **`kerbside._plan_lengths` is a third copy of `plan_lengths_2d`** and says it
cannot import because `roads` imports `kerbside`. That constraint is gone now
this is a leaf, but retiring it is not part of `Q94` and is left alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np


def plan_lengths(points: np.ndarray) -> np.ndarray:
    """Cumulative plan distance along a polyline, starting at zero.

    Plan rather than 3D: road widths, kerbs, junction radii and positions along
    an edge are all measured on the ground, and a 6 m ramp would otherwise be
    treated as longer than its own footprint.

    Here rather than in either consumer because both `P1-4` and `P1-5` measure
    along an edge, and two copies of this convention is two places for it to
    drift.
    """
    return plan_lengths_2d(points[:, [0, 2]])


def plan_steps(points: np.ndarray) -> np.ndarray:
    """Length of each segment of a polyline, in plan."""
    return plan_steps_2d(points[:, [0, 2]])


def plan_steps_2d(plan: np.ndarray) -> np.ndarray:
    """`plan_steps` for an array that is already two columns of `(x, z)`.

    A separate name rather than a mode of the 3-D one: a run in `roads.py` is
    plan-only from `clip` until its heights are decided, and column indices that
    mean different things in different halves of a file are how a road ends up
    measured against its own height. The 3-D pair drops its height column and
    calls through, so the arithmetic is written once.

    ⚠️ **Was `roads._steps` and is public because the hoist made it so** — the
    privacy was a statement about being inside `roads.py`, and `roads.py` is now
    a caller like any other. The naming follows `plan_lengths_2d`.
    """
    return np.hypot(*np.diff(plan, axis=0).T)


def plan_lengths_2d(plan: np.ndarray) -> np.ndarray:
    """`plan_lengths` for two columns of `(x, z)`. See `_steps` for the split.

    Public where `_steps` is private, because a caller outside this module can
    already hold a plan-only line: `railings._run_uvs` measures along a *fence*
    line, which never had a height column to drop. Exported rather than copied —
    `kerbside._plan_lengths` is the third copy of this arithmetic and documents
    why it cannot import (this module imports `kerbside`), which is a constraint
    `railings` does not have.
    """
    return np.concatenate([[0.0], np.cumsum(plan_steps_2d(plan))])


@dataclass(frozen=True)
class Snap:
    """Where a point attaches to the road graph."""

    # The graph's own edge id, not a position in any list.
    edge: int
    distance_m: float
    # Fraction along the edge's plan length, 0 at `from` and 1 at `to`.
    t: float
    # Height of the attachment point, which is where the fare node's own
    # height comes from.
    y: float
    # Signed perpendicular offset: `|offset_m| == distance_m`, and the sign says
    # which side of travel the point fell on — **positive is the nearside**, the
    # rail at `TEXCOORD_0`'s `U = 0`.
    #
    # ⚠️ **The expression is `kerbside.SideIndex.nearest`'s, and it is deliberately
    # not restated there or here in prose.** Left of travel is
    # `dot(point - start, (step_z, -step_x))`, which is `surface.mitres`'s normal.
    # A sign flip mirrors every side-keyed feature in the city and still renders
    # as a city, so `tests/test_fares.py` asserts it against `mitres` itself
    # rather than against this comment.
    #
    # Added for `P3-15`, which needs a side and a heading to put a turn arrow in
    # a lane. Folded into the one join rather than written a second time: `Q56`
    # records why two implementations of a join grade nothing —
    # "two implementations disagreeing tells you one is wrong and never which".
    offset_m: float
    # Game-space heading of the segment the point landed on, degrees clockwise
    # from north (`-Z`), in `[0, 360)`. What an arrow's own bearing is graded
    # against.
    heading_deg: float


@dataclass(frozen=True)
class Segments:
    """Every edge's segments flattened into one set of arrays.

    Flattened rather than walked per edge so snapping a point is a single
    vectorised pass over the region rather than a Python loop over 797
    polylines. The bookkeeping arrays are what let a hit be traced back to
    which edge it was on and how far along.

    Public because it is the one piece of geometry this stage owns, and so the
    one worth testing on its own.
    """

    start: np.ndarray
    delta: np.ndarray
    # Plan length of each segment, of the run before it along its own edge, and
    # of that whole edge. Plan rather than 3D, via the same helpers `P1-4`
    # measures with: a ramp's footprint is what a position along it means.
    length_m: np.ndarray
    before_m: np.ndarray
    total_m: np.ndarray
    # The graph's edge id for each segment. Read from the edge rather than
    # taken from its position in the list: it is published as `nearest_edge`,
    # which the data contract defines as an id, and the two agree today only
    # because `P1-3` happens to number edges by their order.
    edge: np.ndarray

    @classmethod
    def of(cls, edges: Sequence[dict[str, Any]]) -> Segments:
        starts, deltas, lengths, befores, totals, owners = [], [], [], [], [], []
        for edge in edges:
            points = np.asarray(edge["polyline"], dtype=np.float64)
            if len(points) < 2:
                continue
            along = plan_lengths(points)
            starts.append(points[:-1])
            deltas.append(np.diff(points, axis=0))
            lengths.append(plan_steps(points))
            befores.append(along[:-1])
            totals.append(np.full(len(points) - 1, along[-1]))
            owners.append(np.full(len(points) - 1, int(edge["id"])))

        if not starts:
            raise ValueError("the road graph has no edge with a usable polyline")
        return cls(
            start=np.concatenate(starts),
            delta=np.concatenate(deltas),
            length_m=np.concatenate(lengths),
            before_m=np.concatenate(befores),
            total_m=np.concatenate(totals),
            edge=np.concatenate(owners),
        )

    def nearest(self, x: float, z: float) -> Snap:
        """The closest point on the graph to `(x, z)`, measured in plan.

        Plan distance is the only defensible measure here, because the sources
        are 2D: a taxi stand carries no height, so a stand under a flyover has
        nothing in it to prefer the street over the deck above.

        ⚠️ **Which edges are candidates is the caller's decision, and every
        caller passes level 0 only** — `fares.build_region`, `tramway.py` and
        `arrows.py`, for the same stated reason. That measured nothing until
        `P3-14` added 19 tram stops: `f_032`, on Hennessy Road under the Canal
        Road Flyover, was won by the deck by a plan margin of 0.80 m and took
        its height — 12.562 m against 3.947 m for the road it is actually on.
        The claim that stood here, that the one level-1 runner-up in the region
        lost by 7 m, was measured on `P1-5`'s taxi points and never covered a
        point beneath a deck.

        A point that belongs to an elevated road still cannot be placed on one:
        narrowing the candidates fixes the direction the sources are wrong in
        here, not the other. That half of `Q15` is open, and
        `FareReport.off_grade_nearer` is what would say so.
        """
        distance, along = self._plan_distances(x, z)
        hit = int(distance.argmin())

        total = self.total_m[hit]
        reached = self.before_m[hit] + along[hit] * self.length_m[hit]
        # Sign only: the magnitude comes from `distance`, which is measured to
        # the *clamped* projection. Past a segment's end the two differ, and the
        # distance is the honest one — a point beyond the end is that far from
        # the road, not that far from its infinite extension.
        offset_x, offset_z = x - self.start[hit, 0], z - self.start[hit, 2]
        step_x, step_z = float(self.delta[hit, 0]), float(self.delta[hit, 2])
        side = offset_x * step_z - offset_z * step_x
        return Snap(
            edge=int(self.edge[hit]),
            distance_m=float(distance[hit]),
            t=float(reached / total) if total > 0.0 else 0.0,
            y=float(self.start[hit, 1] + along[hit] * self.delta[hit, 1]),
            offset_m=float(distance[hit]) if side > 0.0 else -float(distance[hit]),
            heading_deg=float(np.degrees(np.arctan2(step_x, -step_z)) % 360.0),
        )

    def _plan_distances(self, x: float, z: float) -> tuple[np.ndarray, np.ndarray]:
        """Plan distance from `(x, z)` to every segment, and the clamped `along`.

        Extracted so `nearest` and `rivals_within` sweep the graph the **one**
        way. A second copy of this arithmetic is a second implementation of the
        join, and `Q56`'s rule is that two implementations disagreeing tells you
        one is wrong and never which.
        """
        offset_x, offset_z = x - self.start[:, 0], z - self.start[:, 2]
        step_x, step_z = self.delta[:, 0], self.delta[:, 2]

        # Projection of the point onto each segment, clamped to it. A zero
        # length segment cannot survive `P1-3`'s simplification, but the graph
        # is an input rather than something this stage built, so guard the
        # divide. No second guard on the result is needed: a zero-length
        # segment has a zero numerator too, so the clamped quotient is 0.
        squared = step_x * step_x + step_z * step_z
        projected = offset_x * step_x + offset_z * step_z
        along = (projected / np.where(squared > 0.0, squared, 1.0)).clip(0.0, 1.0)

        return np.hypot(offset_x - along * step_x, offset_z - along * step_z), along

    def rivals_within(self, x: float, z: float, radius_m: float, exclude: int) -> int:
        """How many **other** edges come within `radius_m` of `(x, z)`.

        🔴 **The counter that can see a nearest-edge host go wrong, for a feature
        that stands where nearest-edge is weakest.** `nearest` returns one
        winner and says nothing about how close the runner-up was — and a signal
        head, like a stop line, sits at a junction *mouth* where several edges
        are near. `roadmarks.py` measured that geometry picking the wrong road on
        **43%** of its layer (`Q69`) and answered it with a transverse pick; a
        head is not drawn *across* anything, so it has no such second rule and
        this is the instrument instead.

        ⚠️ **Report-only wherever it is used, and never a bar.** A crowded
        junction is a fact about the city, not a defect in the join — which is
        why this counts rather than refuses.

        Distinct **edges**, not segments: every polyline of the host's own edge
        is near by construction, and so are the several segments a single
        neighbouring road contributes.
        """
        distance, _ = self._plan_distances(x, z)
        near = self.edge[distance <= radius_m]
        return int(np.count_nonzero(np.unique(near) != exclude))
