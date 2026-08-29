"""Measure each level-0 edge's carriageway width from what the publishers drew (`Q95`).

`roadgraph.json`'s `width_m` was `lanes x lane_width_m` on every edge — 6.4 m on
720 of the region's 737 — which `Q95` established is not merely underived but
**outside** TD's published range: Table 3.4.2.1 puts a two-lane single
carriageway at 7.3 m minimum and allows 6.75 m only *per direction* of a dual.
This stage replaces that number with a measurement wherever two publishers
license one, and leaves it authored where they do not.

🔴 **This is a second implementation of a survey `tools/carriageway_margin.py`
already performs, and the duplication is deliberate.** `CLAUDE.md` records that
the tool "shares no code with what it grades" — that independence is the only
reason its verdict on the shipped ribbon means anything, and importing this
module into it, or it into this one, would retire the grader to save six hundred
lines. The two are expected to *agree*; where they do not, that is a finding
about one of them, which is exactly what a grader is for. `Q95`.

⚠️ **Nothing here may be a bound of its own.** Every figure this stage refuses
on comes from `carriageway_survey.width_bounds` in the city file, transcribed
from TD's Transport Planning & Design Manual under hard rule 3 — the second city
has its own manual. The classification rule is `Q95`'s: `beyond = span - own` is
the room an opposed carriageway would need, and under one through lane there is
none, so the ray stopped at the far kerb of the road it was walking.

⚠️ **It runs where `_kerbside` runs and for `_kerbside`'s reason** — after every
edge exists, because the join is geometric rather than by key. A station needs
to know which graph nodes are near it and which centreline lies across its far
ray, and neither question can be asked while the edge list is still being built.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from pipeline import gdb
from pipeline.config import (
    BOTH,
    CARRIAGEWAY_AREA,
    FORWARD,
    CarriagewayEdge,
    CityConfig,
    WidthBounds,
)
from pipeline.crs import GameTransform
from pipeline.fetch import source_reads
from pipeline.geometry import orient

log = logging.getLogger(__name__)

# Station spacing along an edge, and how far from a graph node a station is
# discarded. Both match the instrument's defaults, because two surveys that
# walk differently cannot be compared and comparison is the whole point of
# keeping the second one.
STATION_M = 4.0
JUNCTION_M = 12.0
# How far a perpendicular may travel before the station is unmeasurable. A cap
# rather than unbounded, because an uncapped ray finds *something* eventually
# and calls it a kerb.
MAX_RAY_M = 15.0
# Stations an edge needs before its median is read. Three is the instrument's,
# and it is what stops a 6 m stub publishing a width off one lucky ray.
MIN_STATIONS = 3

# Cell size of the segment index. ⚠️ **A lookup accelerator and nothing else** —
# it changes runtime and no published number, unlike the resolution constants in
# `clearance.py` that `Q51` found were deciding a count. The assertion that keeps
# it that way is that a cell is only ever used to *gather* candidates, which are
# then tested exactly.
_INDEX_CELL_M = 20.0


@dataclass
class CarriagewayReport:
    """What the survey measured, and what it refused.

    🔴 **The counters are derived from one unfiltered population**, never
    accumulated beside the guard that refuses. `Q95` built the instrument that
    way after `Q58`'s `drawn_gauge_m` trap had shipped in four stages, and the
    same rule holds here: `widths` carries every edge that got a median, and the
    bounds are applied where the number is read.
    """

    # Every level-0 edge that got a median, measured before anything is refused.
    spans_m: dict[int, float] = field(default_factory=dict)
    own_m: dict[int, float] = field(default_factory=dict)
    # The width finally assigned, per edge. A subset of `spans_m`'s keys.
    assigned_m: dict[int, float] = field(default_factory=dict)
    # Why each assigned edge was licensed, so a reader can tell a two-way span
    # from a one-way one that never crossed a median. They are different
    # measurements and pooling them is `Q57`'s generalisation.
    basis: dict[int, str] = field(default_factory=dict)
    # 🔴 **Which publishers supplied the stations behind each median, and it is a
    # SET rather than a winner** (`Q94`). The three do not measure the same
    # quantity: HyD carves traffic islands, run-ins and car parks out of its
    # carriageway, so it reads the *trafficable* surface where the two line
    # publishers run on to the kerb — worth p10 **-3.39 m** across this region.
    # Pooling those into one `width_m` without saying which is `Q57`'s
    # generalisation, a property established on one population and quoted for
    # another.
    #
    # ⚠️ **A set joined on `+`, never a dominant publisher**, because the loop
    # picks per *station* and the mixture is the common case: 201 edges here are
    # iB1000 alone, 21 are HyD alone, and **66 are mixed**. A "winner" would put
    # a 51% edge and a 49% edge in different populations over one station.
    publishers: dict[int, str] = field(default_factory=dict)

    stations_walked: int = 0
    stations_spanned: int = 0
    edges_walked: int = 0
    # Edges with a median that no rule licensed a width from.
    unattributed: int = 0
    # Assigned widths that fall under the manual's own two-lane minimum. TD's
    # table is headed *Minimum* and 3.4.2.2 lets a width fall below it, so this
    # is reported and never refused — refusing would delete Wan Chai's real
    # back streets and publish a region that agrees with the standard by
    # construction.
    under_minimum: int = 0

    # ── The lane count, bracketed off the width above (`Q94`) ──────────────
    #
    # 🔴 **The bracket for every assigned width, recorded before anything is
    # read from it**, which is what lets every counter below be a property. The
    # class docstring's rule is not decoration here: a `lanes_ambiguous`
    # incremented beside the guard that refuses would count only the edges the
    # rule declined, and could never say how much of the population that was.
    lanes_bracket: dict[int, tuple[int, int]] = field(default_factory=dict)
    # The count finally published, and why. A subset of `lanes_bracket`'s keys.
    lanes: dict[int, int] = field(default_factory=dict)
    lanes_basis: dict[int, str] = field(default_factory=dict)
    # ⚠️ **A finding, not a counter.** TPDM 3.4.2.7 forbids dividing a two-way
    # single carriageway into three lanes other than as a climbing lane, so an
    # unambiguously odd bracket of three or more on a two-way edge is a
    # statement about the measurement or the `direction` field — reported, and
    # never corrected into agreement.
    lanes_odd_two_way: list[int] = field(default_factory=list)

    @property
    def measured(self) -> int:
        return len(self.assigned_m)

    @property
    def lanes_resolved(self) -> int:
        """Brackets that named one count, before the floor is applied."""
        return sum(1 for low, high in self.lanes_bracket.values() if low == high)

    @property
    def lanes_ambiguous(self) -> int:
        """Brackets TD's own range does not resolve. These keep the authored count."""
        return sum(1 for low, high in self.lanes_bracket.values() if high > low)

    @property
    def lanes_floored(self) -> int:
        """Resolved brackets under the floor, published as `LANES_FLOOR`. See `_lanes`.

        ⚠️ **The predicate is `_lanes`'s own, not a restatement of it.** Writing
        `low == high == 1` here would agree with the assignment only through
        `config.py`'s guard that `lane_m[0] <= hard_min_m` — which is what makes
        a zero-lane bracket unreachable — and would silently stop agreeing if
        that guard ever moved.
        """
        return sum(
            1 for low, high in self.lanes_bracket.values() if low == high and low < LANES_FLOOR
        )


@dataclass(frozen=True)
class _Segments:
    """A segment soup with a uniform grid over it, in the frame it was read in.

    Built rather than borrowed: `geometry.py` offers the exact predicates
    (`orient`) and no index, and an index is what turns 13,500 stations against
    29,000 segments from a minute into a second.
    """

    starts: np.ndarray
    ends: np.ndarray
    buckets: dict[tuple[int, int], list[int]]

    @staticmethod
    def build(starts: np.ndarray, ends: np.ndarray) -> _Segments:
        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for row, (a, b) in enumerate(zip(starts, ends, strict=True)):
            lo = np.minimum(a, b) / _INDEX_CELL_M
            hi = np.maximum(a, b) / _INDEX_CELL_M
            for cx in range(int(np.floor(lo[0])), int(np.floor(hi[0])) + 1):
                for cy in range(int(np.floor(lo[1])), int(np.floor(hi[1])) + 1):
                    buckets[(cx, cy)].append(row)
        return _Segments(starts, ends, buckets)

    def near(self, origin: np.ndarray, direction: np.ndarray, reach: float) -> np.ndarray:
        """Candidate rows whose cell the probe passes through.

        Gathers over the probe's bounding cells rather than walking the ray in
        order. Order would let an early exit skip the exact test, and the exact
        test is what makes the cell size inert.
        """
        far = origin + direction * reach
        lo = np.minimum(origin, far) / _INDEX_CELL_M
        hi = np.maximum(origin, far) / _INDEX_CELL_M
        rows: list[int] = []
        for cx in range(int(np.floor(lo[0])), int(np.floor(hi[0])) + 1):
            for cy in range(int(np.floor(lo[1])), int(np.floor(hi[1])) + 1):
                rows.extend(self.buckets.get((cx, cy), ()))
        return np.unique(np.asarray(rows, dtype=np.int64)) if rows else np.empty(0, np.int64)

    def first_hit(self, origin: np.ndarray, direction: np.ndarray, reach: float) -> float | None:
        """Distance to the NEAREST crossing within `reach`, or None.

        🔴 **The nearest, not the first found.** A bucket holds its segments in
        insertion order, so taking the first hit inside one makes the answer
        depend on which sheet was read first — `tools/carriageway_margin.py`'s
        own test file opens by naming that as the quiet failure its tests exist
        for, and the same trap is reachable here.

        Crossing is decided by `geometry.orient`, the pipeline's own predicate,
        and only the surviving segments have a distance computed. That split is
        what keeps a degenerate segment — a repeated vertex, whose direction is
        undefined — out of the arithmetic rather than inside it producing a
        silent zero.
        """
        rows = self.near(origin, direction, reach)
        if not len(rows):
            return None
        far = origin + direction * reach
        a, b = self.starts[rows], self.ends[rows]

        # Proper crossing, both ways round, via the pipeline's own orientation
        # test. Collinear touches fall out: `orient` returns 0 and the strict
        # sign comparison rejects it, which is the right answer for a kerb the
        # ray runs along rather than through.
        d1, d2 = orient(a, b, origin), orient(a, b, far)
        d3, d4 = orient(origin, far, a), orient(origin, far, b)
        crosses = (d1 * d2 < 0.0) & (d3 * d4 < 0.0)
        if not crosses.any():
            return None

        a, b = a[crosses], b[crosses]
        # Distance along the probe to each crossing. The denominator cannot
        # vanish here: a segment parallel to the probe cannot have produced
        # opposite signs above.
        seg = b - a
        denominator = direction[0] * seg[:, 1] - direction[1] * seg[:, 0]
        offset = a - origin
        distance = (offset[:, 0] * seg[:, 1] - offset[:, 1] * seg[:, 0]) / denominator
        ahead = distance[distance > 0.0]
        return float(ahead.min()) if len(ahead) else None


def _read_publisher(
    city: CityConfig,
    spec: CarriagewayEdge,
    region_id: str,
    transform: GameTransform,
) -> _Segments:
    """One publisher's carriageway edge, in the frame the graph is already in.

    ⚠️ **Both grade filters are EXCLUSIONS, and that is the opposite of the
    obvious reading.** At grade is the *unmarked* case in both files — a null
    relative level in TD's drawings, a code absent from iB1000's list — so an
    inclusion filter keeps 57% of the layer, all of it flyover, and still
    reports a plausible number. `Q57` measured that the drawings' commonest
    relative level is the elevated one.
    """
    wanted, off_grade = set(spec.codes), set(spec.off_grade_codes)
    elevation_field = spec.elevation_field
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    for path, member in source_reads(city, spec, region_id, root=None):
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("edge_type"))
        levels = layer.column(elevation_field) if elevation_field else None
        area = spec.geometry == CARRIAGEWAY_AREA
        if area:
            owners, rings = gdb.polygons(layer)
            runs = [
                (owner, ring) for owner, part in zip(owners, rings, strict=True) for ring in part
            ]
        else:
            owners, parts = gdb.polylines(layer)
            runs = list(zip(owners, parts, strict=True))
        run_starts: list[np.ndarray] = []
        run_ends: list[np.ndarray] = []
        for owner, points in runs:
            if str(codes[owner]) not in wanted:
                continue
            if levels is not None and str(levels[owner]) in off_grade:
                continue
            projected = np.asarray(points, dtype=np.float64)
            game_x, _, game_z = transform.to_game(projected[:, 0], projected[:, 1])
            plan = np.column_stack([game_x, game_z])
            keep = np.any(np.diff(plan, axis=0) != 0.0, axis=1)
            if not keep.any():
                continue
            run_starts.append(plan[:-1][keep])
            run_ends.append(plan[1:][keep])
        if area:
            run_starts, run_ends = _union_boundary(run_starts, run_ends)
        starts.extend(run_starts)
        ends.extend(run_ends)
    if not starts:
        return _Segments.build(np.empty((0, 2)), np.empty((0, 2)))
    return _Segments.build(np.vstack(starts), np.vstack(ends))


def _union_boundary(
    starts: list[np.ndarray], ends: list[np.ndarray]
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """The outline of a set of abutting polygons, with the seams between them gone.

    🔴 **Without this an area publisher measures the wrong thing, and plausibly.**
    HyD tiles Wan Chai's carriageway into **552** polygons; the boundary between
    two of them is a maintenance division, not a kerb, and a ray stops at the
    first one it crosses. The result is a width that is short by however far the
    nearest seam happens to lie — a number in the right range, on the right road,
    and wrong.

    A seam is a segment two polygons both draw, so it appears **twice** and the
    union's own edge appears once. Dropping every repeat leaves the outline.

    ✅ **Measured against the method that needs no such rule**: walking outward
    until the point leaves every polygon steps through seams by construction.
    Over 126 stations the two agree to a **max of 0.037 m**, all of it the walk's
    own 0.02 m step, so this is the same measurement at a fraction of the cost.

    ⚠️ **It assumes abutting polygons share vertices exactly**, which is a
    property of the publisher rather than of geometry. Where they do not, a seam
    survives as two near-coincident single segments and the ray stops on it —
    which is why the agreement above is checked rather than assumed. In this
    region 2,418 segments are shared and 51 appear three times or more; those
    are dropped as well, on the same rule.
    """
    if not starts:
        return [], []
    first, second = np.vstack(starts), np.vstack(ends)
    # Rounded so float noise cannot part two vertices the publisher drew as one,
    # and canonically ordered so a seam drawn in opposite directions by its two
    # owners — which is the usual case — still matches itself.
    a, b = np.round(first, 3), np.round(second, 3)
    swap = (a[:, 0] > b[:, 0]) | ((a[:, 0] == b[:, 0]) & (a[:, 1] > b[:, 1]))
    key = np.hstack([np.where(swap[:, None], b, a), np.where(swap[:, None], a, b)])
    _, inverse, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    once = counts[inverse.ravel()] == 1
    return [first[once]], [second[once]]


def _stations(plan: np.ndarray, spacing_m: float) -> list[tuple[np.ndarray, np.ndarray]]:
    """Evenly spaced points along a polyline with the unit normal at each.

    The normal is taken from the *segment* the station sits on rather than from
    a smoothed tangent, because a ray cast off a smoothed direction can leave
    the carriageway at a bend and find the wrong kerb.
    """
    steps = np.diff(plan, axis=0)
    lengths = np.hypot(steps[:, 0], steps[:, 1])
    total = float(lengths.sum())
    if total <= 0.0:
        return []
    edges_at = np.concatenate([[0.0], np.cumsum(lengths)])
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for along in np.arange(spacing_m * 0.5, total, spacing_m):
        index = int(np.searchsorted(edges_at, along, side="right") - 1)
        index = min(max(index, 0), len(steps) - 1)
        if lengths[index] <= 0.0:
            continue
        unit = steps[index] / lengths[index]
        point = plan[index] + unit * (along - edges_at[index])
        out.append((point, np.array([-unit[1], unit[0]])))
    return out


def _median_or_none(values: list[float]) -> float | None:
    return float(np.median(values)) if len(values) >= MIN_STATIONS else None


def measure(
    city: CityConfig,
    region_id: str,
    transform: GameTransform,
    edges: list,
    nodes: np.ndarray,
) -> CarriagewayReport:
    """Per-edge carriageway width, or nothing where the publishers do not license one.

    The rule, and every figure in it is TD's rather than this project's:

    - **span** — both kerbs at one station, from a single publisher. A publisher
      that answers only one side is not used, because a span assembled from two
      sources is two different registrations of the same street.
    - **own** — twice the *near* ray, the carriageway the centreline is drawn in.
    - **beyond** = span - own, the room an opposed carriageway would need. Under
      `hard_min_m` there is not one through lane of it, so the ray never crossed
      a median and the span **is** this edge's width.

    🔴 **A two-way edge is its span and a one-way edge usually is not.** 621 of
    the region's 737 level-0 edges are one-way and Hong Kong runs those as
    opposed pairs, so the centreline sits inside one carriageway and the ray may
    legitimately span both. That is the whole reason `beyond` exists; without it
    this stage would draw both halves of Hennessy Road on each half of it.
    """
    survey = city.carriageway_survey
    if survey is None or survey.width_bounds is None:
        return CarriagewayReport()
    bounds = survey.width_bounds

    publishers = [
        (spec.name, _read_publisher(city, spec, region_id, transform)) for spec in survey.edges
    ]
    report = CarriagewayReport()
    level_0 = [edge for edge in edges if edge.elevation_level == 0 and len(edge.polyline) > 1]
    report.edges_walked = len(level_0)

    for edge in level_0:
        plan = np.asarray(edge.polyline, dtype=np.float64)[:, [0, 2]]
        spans: list[float] = []
        nears: list[float] = []
        answered: set[str] = set()
        for point, normal in _stations(plan, STATION_M):
            report.stations_walked += 1
            if len(nodes) and float(np.hypot(*(nodes - point).T).min()) < JUNCTION_M:
                # A station in a junction mouth has no far kerb to find and
                # reads as a wide road. Dropped here rather than reported,
                # because this stage assigns rather than grades.
                continue
            for name, segments in publishers:
                ahead = segments.first_hit(point, normal, MAX_RAY_M)
                behind = segments.first_hit(point, -normal, MAX_RAY_M)
                if ahead is None or behind is None:
                    continue
                spans.append(ahead + behind)
                nears.append(min(ahead, behind))
                answered.add(name)
                report.stations_spanned += 1
                break

        span = _median_or_none(spans)
        if span is None:
            continue
        own = 2.0 * float(np.median(nears))
        report.spans_m[edge.id] = span
        report.own_m[edge.id] = own
        report.publishers[edge.id] = "+".join(sorted(answered))

        width, basis = _license(edge, span, own, bounds)
        if width is None:
            report.unattributed += 1
            continue
        report.assigned_m[edge.id] = width
        report.basis[edge.id] = basis
        if width < bounds.min_m:
            report.under_minimum += 1

        bracket = _lane_bracket(width, bounds, two_way=edge.direction == BOTH)
        report.lanes_bracket[edge.id] = bracket
        low, high = bracket
        if low == high and low >= 3 and low % 2 and edge.direction == BOTH:
            report.lanes_odd_two_way.append(edge.id)
        count, lanes_basis = _lanes(bracket)
        if count is not None:
            report.lanes[edge.id] = count
            report.lanes_basis[edge.id] = lanes_basis
    return report


def _license(edge, span: float, own: float, bounds: WidthBounds) -> tuple[float | None, str]:
    """Whether this edge's measurement may be read as a carriageway width.

    ⚠️ **The span ceiling refuses before anything else is asked.** Above
    `max_m` — a four-lane single carriageway plus a parking strip — the ray has
    crossed a median, a tram reserve or a junction mouth, and `beyond` cannot
    tell which. Below `hard_min_m` it landed on a hatched island or a bay line
    and is not a carriageway at all.
    """
    if not bounds.hard_min_m <= span <= bounds.max_m:
        return None, ""
    if edge.direction == BOTH:
        # Already a whole carriageway: there is no opposed half to have crossed
        # into, so the span is the width with nothing to classify.
        return span, "two_way_span"
    if edge.direction != FORWARD:
        # Unreachable while `roads.py` normalises `BACKWARD` away by reversing
        # the polyline, and refused rather than assumed: `carriageway_margin.py`
        # asks the same question as `!= BOTH`, so a third value would have the
        # two surveys disagree about which edges are one-way — and their
        # agreement is the only check on this stage. Pinned by
        # `test_a_backward_centreline_is_normalised_to_forward`.
        return None, ""
    if span - own < bounds.hard_min_m:
        return span, "one_way_uncrossed"
    return None, ""


def _lane_bracket(width_m: float, bounds: WidthBounds, *, two_way: bool) -> tuple[int, int]:
    """How many through lanes a measured carriageway could hold, as a range.

    🔴 **Never `width / lane_width_m`.** 3.2 m is the authored constant this
    whole question is about, and dividing by it would make the answer agree with
    the value under test by construction — `Q72`'s tautology. The divisor is
    TPDM 4.3.9.8's published through-lane range, so the answer is a bracket and
    its ambiguity is published rather than resolved by fiat.

    ⚠️ **A second implementation of `carriageway_margin.py`'s `lane_bracket`,
    and deliberately not an import.** The rule `Q95` set for this module holds:
    the tool "shares no code with what it grades". The arithmetic here is three
    lines and the duplication looks gratuitous — but the two run over
    independently *measured* widths, and it is that agreement which means
    something. Importing either into the other retires the only check there is.

    ✅ **Validated against the manual it is read from, which costs nothing to
    check** — the six shared-endpoint pairs' precedent. Over the nine carriageway
    figures in Table 3.4.2.1 this bracket contains TD's own stated lane count on
    **9 of 9**. A tighter reading requiring the width to partition exactly into
    lanes (`3.0 <= w/n <= 3.65`) excludes it on two: it calls TD's 10.3 m
    *two-lane* single carriageway three lanes, and returns nothing at all for
    the 11 m dual three-lane. So the permissive reading is the correct one and
    must not be "sharpened".

    ⚠️ **There is no empty state.** `lane_m` is ascending, so `w // 3.0` is never
    below `w // 3.65`, and `config.py` refuses a `lane_m` floor above
    `hard_min_m` so that a kept width always brackets to at least one lane.

    On a two-way edge 3.4.2.7 removes the odd counts — a two-way single
    carriageway may not be divided into three lanes other than as a climbing
    lane on a gradient. ⚠️ That narrows an *ambiguous* bracket only. An
    unambiguously odd one is left standing and reported as
    `lanes_odd_two_way`, because it is then a finding about the measurement or
    the `direction` field rather than a reading to correct into agreement.
    """
    low = int(width_m // bounds.lane_m[1])
    high = int(width_m // bounds.lane_m[0])
    if two_way and high > low:
        allowed = [n for n in range(low, high + 1) if not (n >= 3 and n % 2)]
        if allowed:
            return min(allowed), max(allowed)
    return low, high


# 🔴 **The floor on a published lane count, and it is `surface.floor_default_m`'s
# argument at a second dimension.** The bracket reads a 5-7 m one-way street as
# one lane, which is true of the street and false of what this project draws on
# it: the ribbon is floored at 10.24 m so a car can use it, and a one-lane road
# puts `RoadGraph.lane_offset` at **0** — the lane centre on the centreline,
# which `road_graph.gd` calls the one place on the network a wheel must not go
# and where `P0-5`'s car crept at 0.8 m/s on three of four wheels.
#
# ⚠️ **So the count is floored rather than the reading being suppressed**, and
# `lanes_source` says `floored` where it bit. The measurement is not edited to
# agree with the drawing; it is published alongside what the drawing needed.
LANES_FLOOR = 2


def _lanes(bracket: tuple[int, int]) -> tuple[int | None, str]:
    """The lane count a bracket may be read as, and why (`Q94`).

    Three states, the middle one publishing nothing — `_license`'s shape, for
    `_license`'s reason. An ambiguous bracket is the honest answer for a width
    TD's own range does not resolve, and resolving it by fiat would author a
    count with better provenance, which is the move `Q95` was opened about.
    """
    low, high = bracket
    if high > low:
        return None, ""
    if low < LANES_FLOOR:
        return LANES_FLOOR, "floored"
    return low, "measured"
