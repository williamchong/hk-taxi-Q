"""Published no-stopping restrictions to `(edge, side, V-range)` runs (`P3-13`).

Closes `Q54`. `P3-12` paints a kerbside double yellow on **every** kerb the
region draws, and `Q53` recorded that as unsourceable. It is not: `NSR` — No
Stopping Restriction — is a layer of the same geodatabase the road graph is
built from, and this stage joins it to the graph the graph can be drawn from.

**Why this is a linear-referencing join and not a key join.** `SPEED_LIMIT` and
`BUS_ONLY_LANE` carry `ROAD_ROUTE_ID`, which is unique per centreline, so
`roads.py` joins them with a dictionary. `NSR` carries `ST_CODE_1..6` — the
*street* codes the restriction runs along — and a street is many centrelines.
There is no key to join on, so the geometry is the join: the layer's own lines
are drawn at the real kerb, roughly a carriageway's half-width off the
centreline (median 2.76 m in this region), and which centreline they belong to
has to be *measured*.

**What is measured.** Each restriction line is sampled every `sample_m` and
each sample assigned to the nearest drivable segment, which gives the edge, the
distance along it, and — from the sign of the offset — which of the ribbon's two
sides the restriction is on. Samples are accumulated into cells `sample_m` long,
so two `NSR` features covering the same kerb collapse into one run rather than
counting twice: 1,736 m of this region's 27,854 do exactly that, and `Q54`'s
harm figures were measured before the dedupe existed.

⚠️ **Only level-0 edges are candidates, and that is the answer rather than an
approximation of it.** For 7% of this region's samples the *nearest* edge of any
level is elevated — Canal Road flyover and Morrison Hill Road run directly over
the streets they shadow. Those restrictions belong to the street underneath: its
centreline is a median 4.0 m away, which is exactly the offset a kerb sits at.
Letting an elevated edge win would move 385 m of kerb onto a flyover, where no
kerb is drawn at all.

⚠️ **The side convention is the trap here, and it renders plausibly when
wrong.** `surface.py:mitres` offsets one half-width to the **left of travel**,
and `TEXCOORD_0`'s `U = 0` is that side, because Hong Kong drives on the left.
So a restriction is on the nearside where its offset from the segment is left of
travel *in game space* — which is what `_sides` computes, in the same expression
`mitres` uses and no other. Getting it backwards mirrors every yellow line in
the city and still looks like a road; `tests/test_kerbside.py` asserts it on a
fixture with a known side rather than trusting this paragraph.

Nothing here knows a Hong Kong fact: the layer, its columns, which vehicle-type
codes are a painted line and which time-zone codes are a double one all arrive
from `config/cities/*.yaml`.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from pipeline import gdb
from pipeline.config import KerbsideRestrictions
from pipeline.crs import GameTransform

log = logging.getLogger(__name__)

# Which of the ribbon's two sides a restriction sits on, in `TEXCOORD_0`'s own
# terms rather than in traffic's: `NEARSIDE` is the rail at `U = 0` and
# `OFFSIDE` the one at `U = lanes`. Those *are* the near and off sides of travel
# — that is what `mitres` guarantees — but naming them after the lane coordinate
# is what keeps a consumer from having to reason about which way a two-way edge
# was digitised.
NEARSIDE = "near"
OFFSIDE = "off"
SIDES = (NEARSIDE, OFFSIDE)


@dataclass(frozen=True)
class Restriction:
    """One contiguous restricted run of one side of one edge.

    `start_m` and `end_m` are measured along the **published** polyline, which
    is the only frame the graph has. `surface.py` draws a shorter ribbon than
    the graph publishes — the junction trims come off both ends — so the
    consumer subtracts its own `trim_start_m` to reach the V it draws at.
    """

    edge: int
    side: str
    start_m: float
    end_m: float
    kind: str


@dataclass
class KerbsideReport:
    """What the join found, and every population a silent regression shows up in."""

    restrictions: list[Restriction] = field(default_factory=list)
    # Features read from the layer, and how many carried a vehicle type this
    # city paints a line for. The gap is the refusal, not a failure.
    #
    # ⚠️ Both count **features**, not parts. `gdb.polylines` explodes a
    # multipart feature into one array per part, and counting those against a
    # feature total reported "725 of 579" — a ratio over one, which is the shape
    # a mismatched denominator takes when nothing is checking.
    features_read: int = 0
    features_painted: int = 0
    # Metres of restriction refused, by source vehicle-type code. `P3-13` refuses
    # `VEHICLE_TYPE = 5` "Others" deliberately — the class it restricts is not
    # named in the data, and asserting a restriction on an unnamed class is the
    # same invention this stage exists to remove — so the metres are reported
    # rather than silently dropped.
    metres_refused: dict[int, float] = field(default_factory=dict)
    # Samples taken, and the two ways one fails to land on an edge. A sample
    # outside the region is ordinary: the geodatabase's spatial filter selects on
    # bounding box, so a feature reaching well past the region comes back whole.
    # A sample *inside* the region with no edge within `max_offset_m` is not
    # ordinary, and is the number to look at when a region goes quiet.
    samples: int = 0
    samples_outside_region: int = 0
    samples_unassigned: int = 0
    # Metres the samples cover before and after the cell dedupe. The difference
    # is overlapping `NSR` features, and it is the double-count `Q54` measured
    # its harm figures through.
    metres_sampled: float = 0.0
    metres_deduped: float = 0.0
    # Metres left after gaps are bridged and short runs dropped — the length
    # this stage actually publishes.
    metres_published: float = 0.0
    # Runs dropped for being shorter than `min_run_m`, and the metres with them.
    runs_dropped: int = 0
    metres_dropped: float = 0.0

    @property
    def sides_covered(self) -> int:
        return len({(item.edge, item.side) for item in self.restrictions})

    @property
    def metres_by_kind(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for item in self.restrictions:
            totals[item.kind] = totals.get(item.kind, 0.0) + item.end_m - item.start_m
        return totals


def build(
    layer: gdb.Layer,
    spec: KerbsideRestrictions,
    transform: GameTransform,
    region_high: tuple[float, float],
    tracks: list[tuple[int, np.ndarray]],
) -> KerbsideReport:
    """Every restriction the region's drivable edges carry.

    `tracks` is `(edge id, published polyline)` for the edges that may take a
    restriction — level 0 only, for the reason in the module docstring. Passed
    in rather than read back off the graph because this runs inside the build,
    before anything is written.
    """
    report = KerbsideReport()
    lines = _lines(layer, spec, transform, report)
    if not lines or not tracks:
        return report
    _assign(lines, tracks, spec, region_high, report)
    return report


def _plan_lengths(plan: np.ndarray) -> np.ndarray:
    """Cumulative distance along two columns of `(x, z)`, starting at zero.

    `roads.plan_lengths` is the same measurement and would be the import, but
    `roads` imports this module to publish its runs, so the dependency only
    runs one way. Written once here rather than left open in the sampler, the
    segment index and the refusal tally: those three are what a restriction's
    extent is measured against, and a drift between them is a run reported
    against a length the edge does not have.
    """
    return np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(plan, axis=0).T))])


def _lines(
    layer: gdb.Layer,
    spec: KerbsideRestrictions,
    transform: GameTransform,
    report: KerbsideReport,
) -> list[tuple[np.ndarray, str]]:
    """The layer's painted-line features, in game plan coordinates, with kinds.

    A feature whose vehicle type this city does not paint is counted into
    `metres_refused` and dropped. A feature whose *time zone* is not in the
    city's table raises instead: the vehicle types are a filter the city
    chooses, but an unrecognised time zone means the publisher has changed a
    closed domain, and guessing a kind for it would paint a single yellow line
    where the source says something this stage has never seen.
    """
    vehicle_type = layer.column(spec.layer.field("vehicle_type"))
    time_zone = layer.column(spec.layer.field("time_zone"))
    owners, parts = gdb.polylines(layer)
    report.features_read = len(layer.fids)

    lines: list[tuple[np.ndarray, str]] = []
    painted: set[int] = set()
    for owner, points in zip(owners, parts, strict=True):
        source = np.asarray(points, dtype=np.float64)
        code = int(vehicle_type[owner])
        if code not in spec.painted_vehicle_types:
            length = float(_plan_lengths(source[:, :2])[-1])
            report.metres_refused[code] = report.metres_refused.get(code, 0.0) + length
            continue
        painted.add(int(owner))
        game_x, _, game_z = transform.to_game(source[:, 0], source[:, 1])
        lines.append((np.column_stack([game_x, game_z]), spec.kind_for(int(time_zone[owner]))))
    report.features_painted = len(painted)
    return lines


def _assign(
    lines: list[tuple[np.ndarray, str]],
    tracks: list[tuple[int, np.ndarray]],
    spec: KerbsideRestrictions,
    region_high: tuple[float, float],
    report: KerbsideReport,
) -> None:
    """Sample every line, put each sample on an edge and a side, and merge runs."""
    index = _Segments(tracks, spec.max_offset_m)
    # `(edge, side) -> cell -> kind -> samples`. A dict of counters rather than a
    # set because the cell is where two overlapping features are deduped, and
    # where they disagree about the kind the majority has to be visible.
    cells: dict[tuple[int, str], dict[int, dict[str, int]]] = defaultdict(dict)

    points, kinds = _samples(lines, spec.sample_m)
    report.samples = len(points)
    report.metres_sampled = len(points) * spec.sample_m
    inside = (
        (points[:, 0] >= 0.0)
        & (points[:, 1] >= 0.0)
        & (points[:, 0] <= region_high[0])
        & (points[:, 1] <= region_high[1])
    )
    report.samples_outside_region = int((~inside).sum())

    for edge, side, along, kind in index.nearest(points[inside], kinds[inside], report):
        cell = cells[(edge, side)].setdefault(int(along // spec.sample_m), {})
        cell[kind] = cell.get(kind, 0) + 1

    report.metres_deduped = sum(len(found) for found in cells.values()) * spec.sample_m
    for (edge, side), found in sorted(cells.items()):
        for start, stop, kind in _runs(found, spec):
            length = (stop - start + 1) * spec.sample_m
            if length < spec.min_run_m:
                report.runs_dropped += 1
                report.metres_dropped += length
                continue
            report.metres_published += length
            report.restrictions.append(
                Restriction(
                    edge=edge,
                    side=side,
                    start_m=round(start * spec.sample_m, 3),
                    end_m=round((stop + 1) * spec.sample_m, 3),
                    kind=kind,
                )
            )


def _samples(lines: list[tuple[np.ndarray, str]], step_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Every line resampled at a fixed pitch, as one array of points and kinds.

    Sampled at the *midpoint* of each step — `step/2`, `3*step/2`, … — so a
    cell's sample sits in the middle of the metre it stands for rather than on
    its boundary, where a rounding difference decides which cell it lands in.
    """
    points: list[np.ndarray] = []
    kinds: list[np.ndarray] = []
    for plan, kind in lines:
        if len(plan) < 2:
            continue
        along = _plan_lengths(plan)
        if along[-1] < step_m:
            continue
        at = np.arange(step_m / 2.0, along[-1], step_m)
        points.append(
            np.column_stack([np.interp(at, along, plan[:, 0]), np.interp(at, along, plan[:, 1])])
        )
        kinds.append(np.full(len(at), kind, dtype=object))
    if not points:
        return np.empty((0, 2)), np.empty(0, dtype=object)
    return np.vstack(points), np.concatenate(kinds)


def _runs(
    found: dict[int, dict[str, int]], spec: KerbsideRestrictions
) -> list[tuple[int, int, str]]:
    """Occupied cells merged into runs, each with the kind most of it carries.

    Gaps up to `bridge_gap_m` are bridged. A restriction is interrupted wherever
    the source drew two features with a hair between them, wherever a vehicle
    crossing was digitised as a break, and wherever the sampling landed either
    side of a bend — and a break shorter than a car is not a place a car can
    stop. The bridged cells take the kind of the run they join, which is what
    makes a bridged gap invisible in the published length.
    """
    occupied = sorted(found)
    if not occupied:
        return []

    groups: list[tuple[int, int]] = []
    start = previous = occupied[0]
    for cell in occupied[1:]:
        if (cell - previous) * spec.sample_m > spec.bridge_gap_m:
            groups.append((start, previous))
            start = cell
        previous = cell
    groups.append((start, previous))

    runs: list[tuple[int, int, str]] = []
    for start, stop in groups:
        votes: dict[str, int] = {}
        for cell in range(start, stop + 1):
            for kind, count in found.get(cell, {}).items():
                votes[kind] = votes.get(kind, 0) + count
        # Ties broken by the kind's own name rather than by dict order, so a
        # rebuild of the same region publishes the same file.
        runs.append((start, stop, max(sorted(votes), key=lambda kind: votes[kind])))
    return runs


class _Segments:
    """Every candidate edge's segments, on a grid that makes "nearest" cheap.

    The grid cell is exactly `max_offset_m` across, which is what makes a 3x3
    lookup *complete* rather than merely likely: a sample lies somewhere in its
    own cell, so everything within `max_offset_m` of it lies inside that cell
    grown by one in each direction. Tying the two together is the point — a
    smaller cell would need a wider search and a larger one would put the whole
    region in one bucket — so there is one number, not two that must agree.
    """

    def __init__(self, tracks: list[tuple[int, np.ndarray]], max_offset_m: float) -> None:
        self.max_offset_m = max_offset_m
        starts, ends, edges, offsets = [], [], [], []
        for edge, polyline in tracks:
            plan = np.asarray(polyline, dtype=np.float64)[:, [0, 2]]
            if len(plan) < 2:
                continue
            along = _plan_lengths(plan)
            starts.append(plan[:-1])
            ends.append(plan[1:])
            edges.append(np.full(len(plan) - 1, edge))
            offsets.append(along[:-1])
        if not starts:
            self.start = np.empty((0, 2))
            self.buckets: dict[tuple[int, int], np.ndarray] = {}
            return

        self.start = np.vstack(starts)
        self.step = np.vstack(ends) - self.start
        self.length = np.hypot(*self.step.T)
        # A zero-length segment cannot happen in a published graph — `dedupe`'s
        # counterpart in `roads.py` runs before the polyline is written — but the
        # division below has to be total, and clamping is cheaper than a filter
        # that changes every index downstream.
        self.length_squared = np.where(self.length > 0.0, self.length**2, 1.0)
        self.edge = np.concatenate(edges)
        self.offset = np.concatenate(offsets)

        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        low = np.minimum(self.start, self.start + self.step)
        high = np.maximum(self.start, self.start + self.step)
        for index, (lo, hi) in enumerate(zip(low, high, strict=True)):
            for x in range(int(lo[0] // self.max_offset_m), int(hi[0] // self.max_offset_m) + 1):
                for z in range(
                    int(lo[1] // self.max_offset_m), int(hi[1] // self.max_offset_m) + 1
                ):
                    buckets[(x, z)].append(index)
        self.buckets = {key: np.array(value) for key, value in buckets.items()}

    def nearest(
        self, points: np.ndarray, kinds: np.ndarray, report: KerbsideReport
    ) -> list[tuple[int, str, float, str]]:
        """Each sample's edge, side, distance along it, and the kind it carried.

        Batched by grid cell rather than run per point: the candidate list is a
        property of the cell, so gathering it once per cell turns a Python loop
        over 28,000 samples into one over a few hundred.
        """
        found: list[tuple[int, str, float, str]] = []
        if not len(points):
            return found

        by_cell: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index, (x, z) in enumerate(points // self.max_offset_m):
            by_cell[(int(x), int(z))].append(index)

        for (x, z), rows in by_cell.items():
            near = [
                self.buckets[(x + dx, z + dz)]
                for dx in (-1, 0, 1)
                for dz in (-1, 0, 1)
                if (x + dx, z + dz) in self.buckets
            ]
            if not near:
                report.samples_unassigned += len(rows)
                continue
            candidates = np.unique(np.concatenate(near))

            batch = points[rows]
            start = self.start[candidates]
            step = self.step[candidates]
            # (samples, candidates) — the projection of every sample onto every
            # candidate segment, clamped to the segment so an endpoint answers
            # for anything past it.
            offset = batch[:, None, :] - start[None, :, :]
            travel = np.clip(
                (offset * step[None, :, :]).sum(axis=2) / self.length_squared[candidates], 0.0, 1.0
            )
            gap = np.hypot(
                *(
                    (start[None, :, :] + travel[:, :, None] * step[None, :, :]) - batch[:, None, :]
                ).transpose(2, 0, 1)
            )
            best = np.argmin(gap, axis=1)
            rows_index = np.arange(len(rows))
            distance = gap[rows_index, best]
            chosen = candidates[best]
            # Left of travel is `dot(sample - start, (step_z, -step_x))`, which
            # is `mitres`'s normal and the reason `U = 0` is the nearside. Never
            # restate it: a sign flip here mirrors every kerbside line in the
            # city and still renders as a road.
            side_of = (
                offset[rows_index, best, 0] * step[best, 1]
                - offset[rows_index, best, 1] * step[best, 0]
            )
            along = self.offset[chosen] + travel[rows_index, best] * self.length[chosen]

            for row, keep in enumerate(distance <= self.max_offset_m):
                if not keep:
                    report.samples_unassigned += 1
                    continue
                found.append(
                    (
                        int(self.edge[chosen[row]]),
                        NEARSIDE if side_of[row] > 0.0 else OFFSIDE,
                        float(along[row]),
                        str(kinds[rows[row]]),
                    )
                )
        return found
