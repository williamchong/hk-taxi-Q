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

import itertools
import logging
import math
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import numpy as np

from pipeline import gdb
from pipeline.config import (
    BOTH,
    CARRIAGEWAY_AREA,
    FORWARD,
    CarriagewayEdge,
    Config,
    WidthBounds,
)
from pipeline.crs import GameTransform
from pipeline.fetch import source_reads
from pipeline.geometry import orient
from pipeline.polyline import (
    Segments,
    axis_residual_deg,
    directed_residual_deg,
    game_heading_deg,
    plan_lengths,
)
from pipeline.terrain import HeightField

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

    # ── The lane row, and what it was allowed to resolve (`Q94`) ───────────
    #
    # Every arrow-carrying edge's stated count, whether or not this stage has a
    # bracket for it — so what `roads.py` logs is the whole population this stage
    # read, not the subset it could act on.
    # ⚠️ **This is NOT what grades the two implementations against each other.**
    # That is `arrows._grade_against_the_graph`, which reads `lanes_source` back
    # out of `roadgraph.json` and so covers only the edges a row was published
    # on. Nothing serialises this dict, so widening it buys no coverage until
    # something does.
    lane_rows: dict[int, int] = field(default_factory=dict)
    # 🔴 **A row BELOW its bracket is an unpainted lane, not a narrower road.**
    # A lane carrying no turn arrow is invisible to the row, which makes the row
    # a lower bound — so this is reported and never used. **7** edges today.
    lanes_row_below_bracket: list[int] = field(default_factory=list)
    # 🔴 **A row ABOVE its bracket is a finding about one of the two readings.**
    # `e403` reads 7.70 m with four arrows abreast — 1.9 m a lane — so either the
    # width under-reads (HyD carves islands and run-ins out and publishes the
    # *trafficable* surface, p10 -3.39 m below iB1000's kerb-to-kerb) or the row
    # over-counts. **6** edges today. Reported; go and look; never retuned.
    # ⚠️ **A row agreeing with the published count is filed as agreement, not
    # here**, even where it sits outside its bracket — see `_resolve_with_rows`.
    lanes_row_over_bracket: list[int] = field(default_factory=list)
    # Rows of a single arrow, which state a marking rather than a lane count.
    # See `_resolve_with_rows` for why they are refused rather than floored.
    lanes_row_single: list[int] = field(default_factory=list)
    # Rows agreeing with a bracket the width already resolved on its own — two
    # readings sharing no input, landing on the same integer. Nothing to
    # publish; counted because it is the only free cross-check either has.
    lanes_row_agreeing: list[int] = field(default_factory=list)

    # ── The deck a ribbon is drawn on (`Q103`) ─────────────────────────────
    #
    # 🔴 **A different truth side from everything above, and the reason is
    # measured.** Every field above reads what a *publisher* drew. Off-grade
    # those lines are a 2D plan projection, so a ray from a deck centreline
    # finds the kerb of the street underneath — they license 5 of 45 level-1
    # edges and 2 of the 5 would publish a width wider than the deck. The only
    # source that knows where a viaduct deck is, is the model, and `roads.py`
    # already reads it as a `HeightField` for the polyline's own height.
    #
    # ⚠️ **Recorded and published NOWHERE yet.** Nothing downstream reads these,
    # which is what lets the walk be added and graded before the bundle moves.
    deck_span_m: dict[int, float] = field(default_factory=dict)
    # 🔴 **SIGNED, in `_stations`' RIGHT-of-travel frame, and that is not the
    # frame `surface.mitres` draws in.** The two normals in this repo are
    # opposite on purpose (`CLAUDE.md`), so whatever finally consumes this owes
    # a *named* negation and a mutation check — `Q78`'s defect is precisely an
    # unsigned magnitude that could not report the direction of its own move.
    # Positive means the deck's centre lies right of the published centreline.
    deck_offset_m: dict[int, float] = field(default_factory=dict)
    # Stations whose centreline stood on no deck at all — the ribbon is off its
    # own structure there, which is the defect this exists to size.
    deck_stations_off: int = 0
    # Stations where the walk found a deck and measured it.
    deck_stations_on: int = 0
    # Edges walked at a non-zero level with no deck field to walk against.
    deck_edges_unsampled: int = 0

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
    def lanes_unresolved(self) -> int:
        """Ambiguous brackets the arrow row did not resolve either.

        ⚠️ **Not `lanes_ambiguous`, and the two stopped being the same number in
        `Q94`.** An ambiguous bracket used to mean "keeps the authored count",
        and the log line said so; since the row can resolve one, the population
        that falls back to the authored count is this narrower one. Kept as two
        properties rather than one corrected in place, because the *bracket*
        being ambiguous is still the thing `_lane_bracket` is graded on.
        """
        return sum(
            1
            for edge_id, (low, high) in self.lanes_bracket.items()
            if high > low and edge_id not in self.lanes
        )

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
    city: Config,
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


# Which percentile of an edge's deck spans becomes its published width.
#
# 🔴 **Not the median, and the asymmetry is the whole reason** (`Q103`). Every
# other width in this stage is a median, because at grade a ribbon drawn too
# wide lands on **tarmac** — the error is invisible and costs nothing. Off-grade
# the same error lands on **air**, and a deck's span varies along its own edge
# (a ramp tapers), so one number per edge cannot fit all of it. A median splits
# the difference and hangs at every station below it: measured, it took
# `deck_margin.py`'s stations-with-some-hang from 53.4% to **85.5%** even as it
# took the hanging *area* down. A low percentile buys the incidence back by
# giving up drawn width where the deck narrows, which is the side of the trade
# a player can survive.
#
# ⚠️ **Swept, and there is no plateau — this is a position on a trade curve
# rather than an optimum**, so it is a judgement and the numbers are the whole
# argument. `overhang.py`'s hanging fraction and `deck_margin.py`'s
# stations-with-some-hang, over the shipped bundle:
#
#     percentile   drawn m2   hanging   hang m2   stations hanging
#     authored        52661     10.3%      5449         53.4%
#     p0  (min)       56574      5.3%      3007         66.0%
#     p10             59286      5.6%      3326         75.0%
#     p25             60885      6.2%      3796         80.7%
#     p50 (median)    62808      7.0%      4380         85.5%
#
# 🔴 **p0 is 0.3 points better and is rejected: it is an extremum, not a
# statistic.** The minimum span is whatever the single worst station on the edge
# read, so one unbridged hole or one station at a taper shrinks the whole
# ribbon — the failure mode `_median_or_none` exists to avoid everywhere else in
# this stage. p10 buys robustness for 0.3 points.
# ⚠️ **Stations-with-some-hang is worse than authored at every percentile, and
# that is not a regression being hidden**: the authored 6.40 m ribbon fits
# inside most decks *because it is too narrow to be the road*, which is the
# defect. The area is the metric that moved — 5449 to 3326 m2, down 39%.
DECK_WIDTH_PERCENTILE = 10.0


def _deck_width_or_none(values: list[float]) -> float | None:
    """One edge's published deck width, or None below `MIN_STATIONS`.

    ⚠️ **`MIN_STATIONS` is shared with the publishers' own reduction above**, so
    the two licences stay comparable — an edge measured on two stations is not
    measured, whichever source answered.
    """
    if len(values) < MIN_STATIONS:
        return None
    return float(np.percentile(values, DECK_WIDTH_PERCENTILE))


# How far either side of a centreline the deck walk looks, and how finely. The
# reach clears the widest authored off-grade ribbon (9.60 m, so 4.80 m a side)
# with room for a deck wider than the paint, which is the common case; the step
# is the resolution every number below is quantised to.
DECK_MAX_LATERAL_M = 12.0
DECK_ACROSS_M = 0.10
# How far a lateral sample may sit from the station's own slab height and still
# be the same deck. A deck is not level across its width — it is cambered, and
# it is drawn as a decimated mesh — so this cannot be zero; and it must stay
# well under a storey or the walk steps onto the deck above at an interchange.
#
# 🔴 **0.40 m because that is `tools/deck_margin.py`'s `--attribute-within-m`,
# and the two are REQUIRED to agree.** They are two implementations of one
# measurement (`CLAUDE.md`), so a tolerance chosen independently here would make
# every divergence between them unreadable — is it the reading, or is it the
# bar? Measured: at 0.75 m this walk read p50 **+2.38 m** wider than that tool
# over the 8 edges both license, against the width survey's own p50 0.005 m.
DECK_TOLERANCE_M = 0.40

# How wide an interior hole may be before it stops being a hole in the model and
# starts being a real void between two decks. 🔴 **Sourced, not chosen, and
# shared with `tools/deck_margin.py` for `DECK_TOLERANCE_M`'s reason** — that
# tool measured the gap distribution as bimodal (p50 0.40 m, then a separate
# tail at p90 3.37 m), and 1.0 sits between the two clusters.
DECK_BRIDGE_M = 1.0

# 🔴 **The comparison is SLAB to SLAB, and the ribbon is not the slab.**
# `roads._deck_heights` publishes `polyline.y` as the sampled structure *plus*
# `deck.clearance_m`, so the road surface floats above the deck it rests on by
# design. Comparing a lateral structure sample against that height spends the
# whole tolerance on a constant offset before the camber is even reached —
# which is half of the divergence above, and it is subtracted rather than
# absorbed into a wider bar.


def _deck_reach(
    field: HeightField,
    slab_gap_m: float,
    point: np.ndarray,
    normal: np.ndarray,
    sign: float,
    deck_y: float,
) -> float | None:
    """How far the deck under a station continues in one direction, or None.

    ⚠️ **A walk outward from the centreline, not a hit test.** The question is
    which deck *this station stands on*, so the run has to be contiguous from
    the centre out: a hit test would find the deck on the far side of a gap and
    report a span across thin air. `sample_along` is handed the walk in order
    for the same reason it is handed the polyline in `roads._deck_heights` —
    consecutive samples resolve a stack by continuity rather than by a seed.
    """
    offsets = np.arange(0.0, DECK_MAX_LATERAL_M + DECK_ACROSS_M, DECK_ACROSS_M)
    heights = field.sample_along(
        point[0] + sign * normal[0] * offsets,
        point[1] + sign * normal[1] * offsets,
        slab_gap_m=slab_gap_m,
    )
    on = np.isfinite(heights) & (np.abs(heights - deck_y) <= DECK_TOLERANCE_M)
    if not on[0]:
        # The centreline itself is not on this deck, so there is no run to walk.
        return None

    # 🔴 **Interior gaps up to `DECK_BRIDGE_M` are closed first, and without this
    # the walk is a hole detector rather than a deck measurement.** `Q19`
    # measured this estate as *not watertight*, so a contiguous run of structure
    # at slab height terminates at the first hole. Measured here: unbridged, this
    # walk read p50 **-3.65 m** against `tools/deck_margin.py` over the edges
    # both license — systematically narrow, which is the signature that tool
    # documents for its own unbridged form.
    hits = np.flatnonzero(on)
    max_gap = round(DECK_BRIDGE_M / DECK_ACROSS_M)
    for low, high in itertools.pairwise(hits):
        if 1 <= high - low - 1 <= max_gap:
            on[low + 1 : high] = True

    ends = np.flatnonzero(~on)
    return float(offsets[ends[0] - 1] if len(ends) else offsets[-1])


def _walk_the_deck(
    report: CarriagewayReport,
    deck: tuple[HeightField, float, float],
    point: np.ndarray,
    normal: np.ndarray,
    plan: np.ndarray,
    along_edge: np.ndarray,
    heights: np.ndarray,
    spans: list[float],
    offsets: list[float],
) -> None:
    """One station's deck span and the centreline's signed offset from it.

    ⚠️ **The reference height is the ribbon's own `y`, interpolated along the
    edge** — not the deck's, which is the quantity being looked for. `roads.py`
    has already sampled the structure to build that `y` and added
    `deck.clearance_m` on top of it, so the road surface sits just above the
    slab it rests on and `DECK_TOLERANCE_M` has to cover that lift as well as
    the camber.

    ⚠️ **A station is dropped, never defaulted, where the centreline stands on
    no deck.** That is the defect being sized, so scoring it as a zero-width
    deck would fold the thing being measured into the measurement.
    """
    field, slab_gap_m, clearance_m = deck
    deck_y = float(np.interp(_along_at(plan, along_edge, point), along_edge, heights)) - clearance_m
    right = _deck_reach(field, slab_gap_m, point, normal, +1.0, deck_y)
    left = _deck_reach(field, slab_gap_m, point, normal, -1.0, deck_y)
    if right is None or left is None:
        report.deck_stations_off += 1
        return
    report.deck_stations_on += 1
    spans.append(right + left)
    # 🔴 **Positive is RIGHT of travel**, because `_stations` emits the right
    # normal. `surface.mitres` is the left one and the two are opposite on
    # purpose, so a consumer owes a named negation (`CLAUDE.md`, `Q78`).
    offsets.append(0.5 * (right - left))


def _along_at(plan: np.ndarray, along_edge: np.ndarray, point: np.ndarray) -> float:
    """Arc length of a station that lies on this polyline.

    ⚠️ **Projected onto the segment, never snapped to the nearest vertex.**
    `_stations` places points *between* vertices by construction, so a nearest-
    vertex reading would quantise every height to the source's own drawing
    density — coarse on a long straight, which is exactly where a ramp's height
    is changing fastest.
    """
    starts, ends = plan[:-1], plan[1:]
    steps = ends - starts
    lengths_sq = (steps * steps).sum(axis=1)
    safe = np.where(lengths_sq > 0.0, lengths_sq, 1.0)
    t = np.clip(((point - starts) * steps).sum(axis=1) / safe, 0.0, 1.0)
    feet = starts + steps * t[:, None]
    index = int(np.hypot(*(feet - point).T).argmin())
    return float(along_edge[index] + t[index] * np.sqrt(lengths_sq[index]))


def measure(
    city: Config,
    region_id: str,
    transform: GameTransform,
    edges: list,
    nodes: np.ndarray,
    deck: tuple[HeightField, float, float] | None = None,
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
    # 🔴 **Config, not a constant, and it defaults to level 0 alone (`Q103`).**
    # `clearance.walk(levels=...)`'s rule at a second key: the knob exists so an
    # off-grade measurement is *reachable* without the bundle changing, and
    # moving the default re-publishes `roadgraph.json` for 60 edges. See
    # `CarriagewaySurvey.levels` for why these publishers fail unsafely up there.
    walked = [
        edge for edge in edges if edge.elevation_level in survey.levels and len(edge.polyline) > 1
    ]
    report.edges_walked = len(walked)

    for edge in walked:
        plan = np.asarray(edge.polyline, dtype=np.float64)[:, [0, 2]]
        heights = np.asarray(edge.polyline, dtype=np.float64)[:, 1]
        along_edge = plan_lengths(np.asarray(edge.polyline, dtype=np.float64))
        deck_spans: list[float] = []
        deck_offsets: list[float] = []
        spans: list[float] = []
        nears: list[float] = []
        answered: set[str] = set()
        for point, normal in _stations(plan, STATION_M):
            report.stations_walked += 1
            if len(nodes) and float(np.hypot(*(nodes - point).T).min()) < JUNCTION_M:
                # A station in a junction mouth has no far kerb to find and
                # reads as a wide road. Dropped here rather than reported,
                # because this stage assigns rather than grades.
                #
                # ⚠️ **The deck walk is refused here too, and must stay below
                # this line.** At a junction mouth a deck runs into the ramp it
                # joins, so the contiguous run is the whole interchange rather
                # than this edge's deck — `tools/deck_margin.py` refuses for the
                # same reason and the two populations have to match to be
                # comparable. Walked above this guard, CANAL ROAD FLYOVER's
                # `e337` reads a 14.05 m deck against that tool's 11.95.
                continue
            if deck is not None and edge.elevation_level != 0:
                _walk_the_deck(
                    report, deck, point, normal, plan, along_edge, heights, deck_spans, deck_offsets
                )
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

        # ⚠️ Recorded before the publishers' `continue` below, because the deck
        # and the published lines are different truth sides — an edge no
        # publisher licensed can still have been measured against its own deck,
        # and that is most of the off-grade network.
        deck_span = _deck_width_or_none(deck_spans)
        if deck_span is not None:
            report.deck_span_m[edge.id] = deck_span
            report.deck_offset_m[edge.id] = float(np.median(deck_offsets))
        elif deck is not None and edge.elevation_level != 0:
            report.deck_edges_unsampled += 1

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

    # ⚠️ **A second pass, after every bracket exists rather than inside the
    # station loop.** The width survey does not change and cannot be made to
    # depend on the arrows: keeping the two apart is what lets the row be tested
    # on its own, and what keeps a failure to read the arrows from moving a
    # width.
    # 🔴 **Level 0 only, and NOT the walked set (`Q103`).** The row's hosting
    # rule is written for the street — `_read_lane_rows` says the nearest
    # level-0 edge to a symbol on a deck *is* the street — so offering it
    # off-grade edges lets an arrow host to the flyover above the road it is
    # painted on. Measured: handed `walked`, it moved `e263`'s count 3 -> 2 and
    # `tools/ground_clearance.py` went 87 -> 89 level-0 edges, a level-0
    # regression out of an off-grade change.
    # ⚠️ Off-grade needs nothing from it: the deck licenses a *width*, and
    # `lanes` stays authored up there.
    rows = _read_lane_rows(
        city, region_id, transform, [edge for edge in walked if edge.elevation_level == 0]
    )
    _resolve_with_rows(report, rows)
    return report


def _resolve_with_rows(report: CarriagewayReport, rows: dict[int, int]) -> None:
    """Let the arrow row resolve the brackets TD's own range leaves ambiguous.

    🔴 **A row of ONE arrow is not a row, and refusing it is the whole
    correctness of this function.** The row counts *painted* lanes, so it is a
    lower bound on the real count — a lane carrying no turn arrow is invisible
    to it. At two abreast that bound is a statement; at one it is a single
    marking, and a junction approach on an ordinary two-lane street carries one
    arrow far more often than not. Measured on the region: **81** edges state a
    row of one, and **26** of them sit on a bracket of `(1, 1)` and **22** on
    `(2, 2)` — reading those as "one lane" would publish a one-lane road from a
    marking that says nothing about width.
    ⚠️ **The first build of this rule floored them to `LANES_FLOOR` instead**,
    which published 28 edges whose basis said `arrows` and whose count the
    arrows had not chosen. The floor is not reachable from here now, and the
    assertion below is what says so rather than a comment.

    🔴 **Ambiguous brackets ONLY, and the restriction is the design.** The row is
    a tie-breaker between two readings of a *measured* width, never a standalone
    publisher — so a count is published here only where this stage already
    licensed a width and the bracket named more than one integer. That keeps
    `verify_road_graph.gd`'s invariant true by construction: a measured
    `lanes_source` implies a measured `width_source`, on every edge, without the
    engine having to be relaxed. `test_carriageway.py` pins it rather than
    trusting this paragraph.

    ⚠️ **So this does NOT reach STEWART ROAD `e505`**, the edge `Q94` was opened
    from. It carries arrows stating three lanes and an *authored* 6.4 m width, so
    there is no bracket to resolve and it keeps the authored count. Widening the
    rule to cover it is a separate question about provenance, not a tidy-up.

    ⚠️ **The two disagreement counters range over resolved brackets as well as
    ambiguous ones**, which is deliberate: a row contradicting a bracket the
    width already resolved is the stronger finding of the two, and confining
    them to the ambiguous population would hide it.
    """
    report.lane_rows.update(rows)
    for edge_id, (low, high) in report.lanes_bracket.items():
        stated = rows.get(edge_id)
        if stated is None:
            continue
        if stated < _ROW_MIN:
            report.lanes_row_single.append(edge_id)
            continue
        if stated == report.lanes.get(edge_id):
            # The width already published this count and the row lands on it —
            # two readings sharing no input agreeing on one integer, which is the
            # only free cross-check either has. Nothing to publish.
            #
            # 🔴 **Tested against the PUBLISHED count, not against the bracket,
            # and the difference is 3 edges.** A `(1, 1)` bracket publishes
            # `LANES_FLOOR`, so a row of two on one of those sits *above* its
            # bracket while agreeing exactly with what shipped: the floor doing
            # its job, confirmed. Filed by bracket instead, those read as the two
            # instruments contradicting each other, and `lanes_row_over_bracket`
            # would be two populations wearing one name.
            report.lanes_row_agreeing.append(edge_id)
            continue
        if stated < low:
            report.lanes_row_below_bracket.append(edge_id)
            continue
        if stated > high:
            report.lanes_row_over_bracket.append(edge_id)
            continue
        if high == low:
            # Inside a bracket the width resolved, but not on the count it
            # published — unreachable while `_lanes` publishes `low` for every
            # resolved bracket at or above the floor, and kept so that a change
            # there cannot silently start overwriting a resolved count.
            continue
        report.lanes[edge_id] = stated
        report.lanes_basis[edge_id] = "arrows"


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


# --------------------------------------------------------------------------
# The lane row (`Q94`)
# --------------------------------------------------------------------------
# 🔴 **A row of turn arrows ACROSS a carriageway is a lane count written down**,
# and it is the one lane reading in the bundle owing nothing to a width. That is
# what makes it able to resolve a bracket TD's own range leaves ambiguous: the
# bracket divides a measured width by 3.0-3.65 m, the row counts painted
# symbols, and the two share no input.
#
# 🔴 **This is a second implementation of `arrows._count_rows` and the
# duplication is FORCED, not chosen.** `arrows.py` imports `roads`, `roads`
# imports this module — so there is no import that could be written. It lands on
# the right side of the house rule anyway: `carriageway.py` is already a second
# implementation of `carriageway_margin.py`'s survey, kept because "they are
# expected to agree and a divergence is a finding".
#
# ⚠️ **The two are NOT expected to agree exactly, and the reason is structural.**
# `arrows.py` counts symbols that survived *registration* — after `max_offset_m`,
# `bearing_tolerance_deg`, the one-way test **and** the drawn ribbon. At this
# stage no ribbon exists yet, so the ribbon-dependent refusals cannot be applied
# here. Everything else is applied, which is why the residual is small and
# enumerable rather than a shrug. `CarriagewayReport.lane_rows` publishes this
# side of it so the gap can be read rather than assumed.

# ⚠️ **A private copy, and it cannot be the shared `railings.AT_GRADE`**:
# `railings` imports `roads`, and `roads` imports this module — the same wall as
# the clustering above, and the one `kerbside._plan_lengths` documents. Named so
# the next reader does not delete it as an oversight.
_AT_GRADE = ("", "none", "null", "<na>")


@dataclass(frozen=True)
class _Symbol:
    """One published turn arrow, reduced to what a lane row is counted from.

    Deliberately not `arrows.Symbol`: that carries a code and a heading because
    the arrows stage draws a glyph, and this stage only ever asks *how many
    abreast*. Along and across the host edge, plus the glyph's own length,
    because the run bar is a fraction of it.
    """

    along_m: float
    offset_m: float
    length_m: float


def _runs(symbols: list[_Symbol], key: Callable[[_Symbol], float]) -> Iterator[list[_Symbol]]:
    """Split symbols into runs, breaking wherever `key` jumps by half a glyph.

    ⚠️ **`arrows._runs`'s bar, restated rather than tuned.** `Q94` swept it
    28 / 30 / 30 / 30 / 24 / 0 over 1.0-4.0 m and found it flat across 1.50-2.50
    with the shipped 2.00 in the middle of that plateau — 2.00 being what
    `0.5 x min(length)` gives for the 4 m glyphs Wan Chai publishes. The plateau
    ends where the bar passes TPDM's 3.0 m through lane, because past that it
    merges two real lanes into one, so this is a published dimension rather than
    a tuning cliff. Derived from the glyph rather than authored as a constant,
    so the 4 m and 6 m variants scale together — the same reason `ArrowGlyph`
    carries a length per code.
    """
    ordered = sorted(symbols, key=key)
    if not ordered:
        return
    run = [ordered[0]]
    for previous, symbol in itertools.pairwise(ordered):
        if key(symbol) - key(previous) >= 0.5 * min(previous.length_m, symbol.length_m):
            yield run
            run = []
        run.append(symbol)
    yield run


def _read_lane_rows(
    city: Config,
    region_id: str,
    transform: GameTransform,
    edges: list,
) -> dict[int, int]:
    """The lane count each edge's own turn arrows state, keyed by edge id.

    ⚠️ **An edge's count is the widest row it carries, not its rows averaged** —
    `arrows._count_rows`'s rule. A carriageway holding three arrows abreast has
    three lanes at that station whatever the rest of it is painted with, and a
    mean lets a long edge with one marked junction read as two.

    🔴 **The count is a LOWER BOUND on lanes, never an equality**, because a lane
    carrying no turn arrow is invisible to it. That is the whole reason
    `_resolve_with_rows` may only read a row *inside* a bracket and never below
    one: **7** edges in the region state fewer lanes than their own width
    brackets.
    """
    spec = city.arrows
    if spec is None:
        return {}

    hosts = Segments.of([{"id": edge.id, "polyline": edge.polyline} for edge in edges])
    one_way = {edge.id: edge.direction != BOTH for edge in edges}
    # ⚠️ **`Snap.t` is a fraction and the row bar is in metres**, so the length
    # has to come back in. Taken off the polyline with the same `plan_lengths`
    # every other stage measures along an edge with, rather than from the
    # ribbon: there is no ribbon at this stage, which is the whole reason this
    # reader exists separately from `arrows.py`.
    length_m = {
        edge.id: float(plan_lengths(np.asarray(edge.polyline, dtype=np.float64))[-1])
        for edge in edges
    }

    rows: dict[int, list[_Symbol]] = defaultdict(list)
    for path, member in source_reads(city, spec, region_id, root=None):
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("code"))
        bearings = layer.column(spec.layer.field("bearing"))
        levels = layer.column(spec.layer.field("level"))
        owners, plan = gdb.points(layer)
        if len(owners) == 0:
            continue
        game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])

        for row, owner in enumerate(owners):
            code = str(codes[owner])
            glyph = spec.glyphs.get(code)
            if glyph is None:
                continue
            # On a flyover: `Q13` keeps the elevated network closed to driving,
            # and the nearest level-0 edge to a symbol on a deck is the street
            # underneath it. `arrows.read_symbols`' refusal, for its reason.
            if str(levels[owner]).strip().lower() not in _AT_GRADE:
                continue
            x, z, bearing = float(game_x[row]), float(game_z[row]), float(bearings[owner])
            if not (math.isfinite(x) and math.isfinite(z) and math.isfinite(bearing)):
                continue
            heading = game_heading_deg(bearing)

            snap = hosts.nearest(x, z)
            if snap.distance_m > spec.max_offset_m:
                continue
            if axis_residual_deg(heading, snap.heading_deg) > spec.bearing_tolerance_deg:
                # Matched a road it is not on. Refused, never rotated onto it.
                continue
            if one_way[snap.edge] and directed_residual_deg(heading, snap.heading_deg) > 90.0:
                # An arrow pointing against a one-way street has either matched
                # the wrong edge or found a one-way the graph has backwards.
                # Either way it is not evidence about this edge's lane count.
                continue
            rows[snap.edge].append(
                _Symbol(
                    along_m=snap.t * length_m[snap.edge],
                    offset_m=snap.offset_m,
                    length_m=glyph.length_m,
                )
            )

    return _widest_rows(rows)


def _widest_rows(rows: dict[int, list[_Symbol]]) -> dict[int, int]:
    """Each edge's widest row of arrows: along the edge first, then across it.

    ⚠️ **An edge's count is the widest row it carries, not its rows averaged** —
    `arrows._count_rows`' rule. A carriageway holding three arrows abreast has
    three lanes at that station whatever the rest of it is painted with, and a
    mean lets a long edge with one marked junction read as two.

    Lifted out of `_read_lane_rows` so it can be tested without a build: it and
    `_runs` are the half this module duplicates, so they are the half most able
    to drift from `arrows.py`, and they were the only part with no test of their
    own.
    """
    return {
        edge_id: max(len(list(_runs(row, _across))) for row in _runs(symbols, _along))
        for edge_id, symbols in rows.items()
    }


def _along(symbol: _Symbol) -> float:
    return symbol.along_m


def _across(symbol: _Symbol) -> float:
    return symbol.offset_m


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

# 🔴 **The narrowest row that is evidence, and it is `LANES_FLOOR` on purpose.**
# Two abreast is the narrowest painted row that states a lane count; one arrow
# states a marking. Tied to the floor rather than authored separately because
# the two answer the same question from opposite sides — the floor is the
# narrowest count this project will publish, and a row under it could only ever
# be published by being floored, which is the defect `_resolve_with_rows`
# records. If one moves the other has to, and a second constant is how that
# stops happening.
_ROW_MIN = LANES_FLOOR


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
