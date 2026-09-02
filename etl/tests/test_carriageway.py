"""The pipeline's own carriageway survey (`pipeline/carriageway.py`, `Q95`).

⚠️ **This is a second implementation of a survey `tools/carriageway_margin.py`
also performs, and these tests do not exist to prove the two identical.** They
are deliberately independent — `CLAUDE.md` records that the tool "shares no code
with what it grades" — so what is pinned here is that this one is *correct*, and
the agreement between them is measured on the region instead, where it currently
runs to a 5 mm median over 259 shared edges.

The failures worth pinning are the quiet ones:

- **The ray takes the wrong hit.** Candidates come out of a grid bucket in
  insertion order, so returning the first crossing found makes the measured
  width depend on which sheet was read first. It has to be the nearest.
- **A degenerate segment.** A repeated vertex has no direction, and dividing by
  its vanishing determinant yields a silent zero-distance "hit" rather than a
  miss — a kerb apparently on top of the centreline.
- **A span that crossed a median read as a width.** This is the one that draws
  both halves of Hennessy Road on each half of Hennessy Road, and it renders as
  an ordinary, slightly generous street.
"""

from __future__ import annotations

import math
from typing import ClassVar

import numpy as np
import pytest

from pipeline.carriageway import (
    _ROW_MIN,
    DECK_ACROSS_M,
    DECK_BRIDGE_M,
    DECK_MAX_LATERAL_M,
    DECK_TOLERANCE_M,
    LANES_FLOOR,
    MIN_STATIONS,
    CarriagewayReport,
    _along_at,
    _deck_reach,
    _lane_bracket,
    _lanes,
    _license,
    _resolve_with_rows,
    _Segments,
    _stations,
    _Symbol,
    _union_boundary,
    _widest_rows,
)
from pipeline.config import BOTH, FORWARD, WidthBounds


def _bounds(**overrides: object) -> WidthBounds:
    """TD's transcribed figures, as `hong_kong.yaml` carries them."""
    defaults = {
        "max_m": 16.5,
        "min_m": 7.3,
        "hard_min_m": 3.0,
        "lane_m": (3.0, 3.65),
        "dual_max_m": 14.6,
        "dual_min_m": 6.75,
        "median_max_m": 5.5,
        "pair_bearing_tolerance_deg": 30.0,
    }
    return WidthBounds(**{**defaults, **overrides})  # type: ignore[arg-type]


def _kerbs(*lines: list[tuple[float, float]]) -> _Segments:
    starts, ends = [], []
    for line in lines:
        points = np.asarray(line, dtype=np.float64)
        starts.append(points[:-1])
        ends.append(points[1:])
    return _Segments.build(np.vstack(starts), np.vstack(ends))


class _Edge:
    """The three fields `_license` reads off a graph edge."""

    def __init__(self, direction: str) -> None:
        self.direction = direction


class TestRay:
    def test_a_ray_measures_the_distance_to_a_crossing_kerb(self) -> None:
        kerbs = _kerbs([(-50.0, 4.0), (50.0, 4.0)])

        hit = kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert hit == pytest.approx(4.0)

    def test_it_takes_the_NEAREST_kerb_and_not_the_first_one_indexed(self) -> None:
        """🔴 The quiet one. Both kerbs land in the same 20 m bucket and the
        bucket holds them in insertion order, so a reader that stops at its
        first crossing measures 9 m of carriageway where there are 4 — and the
        answer would depend on which sheet was read first."""
        far_first = _kerbs([(-50.0, 9.0), (50.0, 9.0)], [(-50.0, 4.0), (50.0, 4.0)])

        hit = far_first.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert hit == pytest.approx(4.0)

    def test_a_kerb_past_the_cap_is_not_found(self) -> None:
        """An uncapped perpendicular finds *something* eventually and calls it a
        kerb. Beyond the cap the station is unmeasurable, which is a different
        answer from a narrow road."""
        kerbs = _kerbs([(-50.0, 40.0), (50.0, 40.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_kerb_behind_the_station_is_not_a_hit_ahead_of_it(self) -> None:
        """The two rays are cast separately and summed, so a backward hit
        counted forwards would double one side and halve the other."""
        kerbs = _kerbs([(-50.0, -4.0), (50.0, -4.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None
        assert kerbs.first_hit(np.zeros(2), np.array([0.0, -1.0]), 15.0) == pytest.approx(4.0)

    def test_a_degenerate_segment_is_a_miss_rather_than_a_zero(self) -> None:
        """A repeated vertex has no direction. Its determinant vanishes rather
        than the ray missing, so it must be excluded by the crossing test before
        any division — otherwise it reads as a kerb on the centreline."""
        kerbs = _kerbs([(1.0, 1.0), (1.0, 1.0)], [(-50.0, 4.0), (50.0, 4.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) == pytest.approx(4.0)

    def test_a_kerb_the_ray_runs_along_is_not_a_crossing(self) -> None:
        """Collinear touching is not a crossing — `geometry.edges_cross` refuses
        it for the same reason, and a ray parallel to a kerb has not reached the
        far side of anything."""
        kerbs = _kerbs([(0.0, 2.0), (0.0, 12.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None


class TestStations:
    def test_stations_are_evenly_spaced_along_the_line(self) -> None:
        out = _stations(np.array([[0.0, 0.0], [20.0, 0.0]]), 4.0)

        assert [round(float(p[0]), 3) for p, _ in out] == [2.0, 6.0, 10.0, 14.0, 18.0]

    def test_the_normal_is_perpendicular_to_the_segment_it_sits_on(self) -> None:
        (_, normal), *_ = _stations(np.array([[0.0, 0.0], [20.0, 0.0]]), 4.0)

        assert normal == pytest.approx([0.0, 1.0])

    def test_a_line_shorter_than_one_step_still_yields_a_station(self) -> None:
        """The walk starts half a step in, so a 3 m stub is measured once rather
        than dropped silently."""
        assert len(_stations(np.array([[0.0, 0.0], [3.0, 0.0]]), 4.0)) == 1

    def test_a_zero_length_line_yields_nothing_rather_than_dividing(self) -> None:
        assert _stations(np.array([[5.0, 5.0], [5.0, 5.0]]), 4.0) == []


class TestLicence:
    """Which measurements may become a `width_m`, and which may not."""

    def test_a_two_way_edge_is_its_span(self) -> None:
        """There is no opposed half to have crossed into, so the span is the
        carriageway with nothing to classify."""
        width, basis = _license(_Edge(BOTH), 9.0, 8.0, _bounds())

        assert (width, basis) == (9.0, "two_way_span")

    def test_a_one_way_span_with_no_room_beside_it_is_that_edges_width(self) -> None:
        """`Q95`'s finding: 96 of 110 mutual pairs refuse their own split because
        the ray stopped at the far kerb and never crossed. A 7 m span over a 7 m
        carriageway leaves 0 m — nowhere for an opposed carriageway to be."""
        width, basis = _license(_Edge(FORWARD), 7.0, 7.0, _bounds())

        assert (width, basis) == (7.0, "one_way_uncrossed")

    def test_a_one_way_span_with_a_carriageway_beside_it_licenses_nothing(self) -> None:
        """🔴 The one that draws both halves of Hennessy Road on each half of
        it. 16 m of span over a 6 m carriageway leaves 10 m — room for an opposed
        one — so the number is a kerb-to-kerb span and not this edge's width."""
        assert _license(_Edge(FORWARD), 16.0, 6.0, _bounds()) == (None, "")

    def test_the_undecided_band_licenses_nothing_either(self) -> None:
        """Room for a lane but not a carriageway. `Q95` records TONNOCHY ROAD
        `e142` here — a 16.7 m span over an 11.78 m half — and a rule with only
        one threshold has to call that either a width or a span."""
        bounds = _bounds()
        beyond = 12.0 - 7.0
        assert bounds.hard_min_m < beyond < bounds.dual_min_m
        assert _license(_Edge(FORWARD), 12.0, 7.0, bounds) == (None, "")

    def test_a_span_past_the_manuals_ceiling_is_refused_before_anything_else(self) -> None:
        """Above a four-lane carriageway plus a parking strip the ray has crossed
        a median, a tram reserve or a junction mouth, and `beyond` cannot tell
        which — so the refusal comes first and applies to two-way edges too."""
        assert _license(_Edge(FORWARD), 20.0, 20.0, _bounds()) == (None, "")
        assert _license(_Edge(BOTH), 20.0, 20.0, _bounds()) == (None, "")

    def test_a_span_under_one_through_lane_is_not_a_carriageway(self) -> None:
        """It landed on a hatched island or a bay line rather than the far kerb."""
        assert _license(_Edge(BOTH), 2.0, 2.0, _bounds()) == (None, "")

    def test_the_bounds_come_from_the_city_and_move_the_answer(self) -> None:
        """⚠️ Hard rule 3: every figure here is the city file's, and none is a
        constant in this module. Driving them is how that is shown rather than
        asserted — the second city has its own design manual."""
        assert _license(_Edge(FORWARD), 12.0, 7.0, _bounds(dual_min_m=4.0)) == (None, "")
        assert _license(_Edge(FORWARD), 12.0, 7.0, _bounds(hard_min_m=6.0))[1] == (
            "one_way_uncrossed"
        )


class TestStationFloor:
    def test_the_minimum_station_count_is_what_stops_a_stub_publishing(self) -> None:
        """Documented rather than asserted elsewhere: three stations is what
        keeps a 6 m stub from carrying a width off one lucky ray."""
        assert MIN_STATIONS == 3


class TestLaneBracket:
    """`Q94`: how many through lanes a measured carriageway may be read as.

    🔴 **The instrument must not agree with the value under test.** The divisor
    is TPDM 4.3.9.8's published range and never `roads.lane_width_m`, so what
    these pin first is that the answer is a *bracket* and that its ambiguity
    survives rather than being resolved by fiat.
    """

    # Table 3.4.2.1's own rows: (carriageway width, the lane count TD gives it).
    # ⚠️ **The truth side of the only validation this rule can have.** There is
    # no published per-edge lane count anywhere to check against, so the manual
    # the divisor came from is what is left — and it costs nothing to check,
    # which is the six shared-endpoint pairs' argument at a second layer.
    TABLE_3_4_2_1: ClassVar[list[tuple[float, int]]] = [
        (7.3, 2),
        (10.3, 2),
        (13.5, 4),
        (6.75, 2),
        (11.0, 3),
        (10.0, 3),
        (14.6, 4),
    ]

    def test_the_bracket_contains_TDs_own_count_on_every_row_of_its_own_table(self) -> None:
        for width_m, published in self.TABLE_3_4_2_1:
            low, high = _lane_bracket(width_m, _bounds(), two_way=False)
            assert low <= published <= high, (
                f"{width_m} m brackets ({low}, {high}), TD says {published}"
            )

    def test_and_a_tighter_reading_would_exclude_it_which_is_why_this_one_is_permissive(
        self,
    ) -> None:
        """🔴 The argument for the loose bracket, as a measurement rather than a preference.

        Requiring the width to partition exactly into legal lanes —
        `3.0 <= w / n <= 3.65` — is the obvious sharpening and it is wrong: it
        calls TD's 10.3 m *two-lane* single carriageway three lanes, and finds
        no legal reading at all for the 11 m dual three-lane. A rule that
        contradicts the document it is derived from is not a sharper rule.
        """
        excluded = [
            (width_m, published)
            for width_m, published in self.TABLE_3_4_2_1
            if not math.ceil(width_m / 3.65) <= published <= int(width_m // 3.0)
        ]
        assert [width_m for width_m, _ in excluded] == [10.3, 11.0]

    def test_a_resolved_bracket_publishes_its_count(self) -> None:
        assert _lanes(_lane_bracket(7.3, _bounds(), two_way=False)) == (2, "measured")

    def test_a_width_TDs_range_does_not_resolve_publishes_nothing(self) -> None:
        """The middle state, and it is most of the region — `_license`'s own shape."""
        assert _lane_bracket(7.29, _bounds(), two_way=False) == (1, 2)
        assert _lanes((1, 2)) == (None, "")

    def test_one_lane_is_floored_because_the_ribbon_over_it_is_not(self) -> None:
        """A 5 m one-way street holds one lane; what is drawn on it is 10.24 m wide."""
        assert _lane_bracket(3.65, _bounds(), two_way=False) == (1, 1)
        assert _lanes((1, 1)) == (LANES_FLOOR, "floored")

    def test_no_licensed_width_can_bracket_to_no_lanes_at_all(self) -> None:
        """🔴 The invariant `config.py` enforces, pinned where it is relied upon.

        `_lanes` floors anything under `LANES_FLOOR`, so an unambiguous bracket
        of **zero** would publish two lanes for a width that measured none. It
        is unreachable because a licensed width is at least `hard_min_m` and
        `config.py` refuses a `lane_m` floor above that — but the refusal lives
        in another module, and this is the line that would break if it moved.
        """
        bounds = _bounds()
        assert bounds.lane_m[0] <= bounds.hard_min_m
        for step in range(300, 1651):
            low, high = _lane_bracket(step / 100.0, bounds, two_way=False)
            assert high >= 1
            assert not (low == high == 0)

    def test_3_4_2_7_removes_the_odd_counts_from_an_AMBIGUOUS_two_way_bracket(self) -> None:
        """A two-way single carriageway may not be split into three lanes."""
        assert _lane_bracket(11.5, _bounds(), two_way=False) == (3, 3)
        assert _lane_bracket(12.5, _bounds(), two_way=True) == (4, 4)

    def test_but_an_unambiguously_odd_one_stands_and_is_reported_instead(self) -> None:
        """⚠️ Narrowing that would be correcting a reading into agreement (`Q54`).

        Three lanes on a two-way edge is a finding about the measurement or the
        `direction` field, and `measure` records it in `lanes_odd_two_way`. The
        bracket is not edited to make the finding go away.
        """
        assert _lane_bracket(11.5, _bounds(), two_way=True) == (3, 3)

    def test_the_divisor_is_the_manuals_and_never_the_authored_lane_width(self) -> None:
        """🔴 `Q72`'s tautology, one dimension over.

        `roads.lane_width_m` is 3.2 m and is the constant this whole question is
        about. Dividing by it makes the instrument agree with the graph by
        construction — and it gives a different answer, which is what says the
        two are not interchangeable.
        """
        assert _lane_bracket(14.67, _bounds(), two_way=False) == (4, 4)
        assert int(14.67 // 3.2) == 4
        assert _lane_bracket(10.3, _bounds(), two_way=False) == (2, 3)
        assert int(10.3 // 3.2) == 3


class TestUnionBoundary:
    """`Q94`: an area publisher's outline, with the seams between its parts gone.

    🔴 **The failure this prevents is a plausible number, not an error.** HyD
    tiles Wan Chai's carriageway into 552 polygons; a ray that stops at the
    boundary between two of them reports a width short by however far the
    nearest maintenance division happens to lie.
    """

    @staticmethod
    def _square(x: float, y: float, size: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        """One closed square as (starts, ends), wound counter-clockwise."""
        ring = np.array(
            [[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]], dtype=float
        )
        return ring[:-1], ring[1:]

    def test_a_lone_polygon_keeps_every_edge(self) -> None:
        starts, ends = self._square(0.0, 0.0)
        kept_starts, kept_ends = _union_boundary([starts], [ends])
        assert len(kept_starts[0]) == 4
        assert len(kept_ends[0]) == 4

    def test_the_seam_between_two_abutting_polygons_is_dropped(self) -> None:
        """Two unit squares side by side: 8 edges drawn, 6 on the outline."""
        left, right = self._square(0.0, 0.0), self._square(1.0, 0.0)
        kept_starts, kept_ends = _union_boundary([left[0], right[0]], [left[1], right[1]])
        assert len(kept_starts[0]) == 6
        # The shared edge runs x = 1 from y = 0 to y = 1, and neither copy survives.
        survivors = np.hstack([kept_starts[0], kept_ends[0]])
        on_seam = np.all(np.isclose(survivors[:, [0, 2]], 1.0), axis=1)
        assert not on_seam.any()

    def test_a_seam_drawn_in_OPPOSITE_directions_still_matches_itself(self) -> None:
        """🔴 The usual case, and the reason the key is canonically ordered.

        Two polygons wound the same way traverse their shared edge in opposite
        directions, so a key built from `(start, end)` as drawn never matches
        and every seam survives — leaving the seams in place while every
        counter reads correctly.
        """
        starts = [np.array([[1.0, 0.0]]), np.array([[1.0, 1.0]])]
        ends = [np.array([[1.0, 1.0]]), np.array([[1.0, 0.0]])]
        kept_starts, _ = _union_boundary(starts, ends)
        assert len(kept_starts[0]) == 0

    def test_a_vertex_a_hair_apart_is_NOT_treated_as_shared(self) -> None:
        """The assumption this rests on is the publisher's, so it is pinned.

        Abutting polygons must share vertices *exactly* for a seam to cancel.
        Where they do not, the seam survives and a ray stops on it — which is
        why the agreement with point-in-union walking is measured rather than
        assumed.
        """
        starts = [np.array([[1.0, 0.0]]), np.array([[1.0, 1.0]])]
        ends = [np.array([[1.0, 1.0]]), np.array([[1.004, 0.0]])]
        kept_starts, _ = _union_boundary(starts, ends)
        assert len(kept_starts[0]) == 2

    def test_nothing_drawn_is_nothing_kept(self) -> None:
        assert _union_boundary([], []) == ([], [])


def _report(
    published: dict[int, int] | None = None, **brackets: tuple[int, int]
) -> CarriagewayReport:
    """A report carrying the brackets, and optionally what the width published.

    ⚠️ **`published` matters**: `_resolve_with_rows` calls a row that lands on the
    already-published count agreement, so a fixture that leaves `lanes` empty is
    testing a state `measure` never hands it.
    """
    report = CarriagewayReport()
    for name, bracket in brackets.items():
        report.lanes_bracket[int(name.lstrip("e"))] = bracket
    report.lanes.update(published or {})
    return report


class TestLaneRow:
    """`Q94`: what a row of turn arrows across a carriageway is allowed to say.

    🔴 **The row is a LOWER BOUND on lanes, never an equality**, because a lane
    carrying no turn arrow is invisible to it. Every rule here follows from
    that one fact, and the tests are written to fail if it is forgotten.
    """

    def test_a_row_of_one_arrow_is_refused_rather_than_floored(self) -> None:
        """🔴 **The correctness of the whole rule.** A single arrow is a marking,
        not a lane count — an ordinary two-lane approach carries one far more
        often than not. The first build floored these to `LANES_FLOOR`, which
        published 28 edges whose basis said `arrows` and whose count the arrows
        had not chosen.
        """
        report = _report(e1=(1, 2))
        _resolve_with_rows(report, {1: 1})
        assert report.lanes == {}, "a row of one published a lane count"
        assert report.lanes_row_single == [1]

    def test_the_row_bar_is_tied_to_the_lane_floor(self) -> None:
        """They answer the same question from opposite sides, so they may not
        drift apart: a row under the floor could only ever be published by being
        floored, which is what this refuses."""
        assert _ROW_MIN == LANES_FLOOR

    def test_a_row_inside_an_ambiguous_bracket_resolves_it(self) -> None:
        report = _report(e119=(4, 5))
        _resolve_with_rows(report, {119: 4})
        assert report.lanes == {119: 4}
        assert report.lanes_basis == {119: "arrows"}

    def test_a_row_below_its_bracket_is_reported_and_never_used(self) -> None:
        """An unpainted lane, not a narrower road. Publishing it would let a
        marking crew's omission overrule a measured width."""
        report = _report(e1=(4, 5))
        _resolve_with_rows(report, {1: 2})
        assert report.lanes == {}
        assert report.lanes_row_below_bracket == [1]

    def test_a_row_above_its_bracket_is_reported_and_never_used(self) -> None:
        """A finding about one of the two readings — the width may under-read
        where HyD carves islands out — and never a licence to overrule TPDM."""
        report = _report({403: 2}, e403=(2, 2))
        _resolve_with_rows(report, {403: 4})
        assert report.lanes == {403: 2}, "the width's count stands"
        assert report.lanes_basis == {}
        assert report.lanes_row_over_bracket == [403]

    def test_a_row_agreeing_with_a_resolved_bracket_publishes_nothing(self) -> None:
        """Two readings sharing no input landing on one integer. Counted,
        because it is the only free cross-check either has; not published,
        because the width already said it."""
        report = _report({1: 3}, e1=(3, 3))
        _resolve_with_rows(report, {1: 3})
        assert report.lanes_basis == {}, "the width had already published it"
        assert report.lanes_row_agreeing == [1]

    def test_a_row_agreeing_with_a_FLOORED_count_is_agreement_not_a_finding(self) -> None:
        """🔴 **Filed against the published count, not the bracket, and that is
        3 edges.** A `(1, 1)` bracket publishes `LANES_FLOOR`, so a row of two on
        one sits *above* its bracket while agreeing exactly with what shipped —
        the floor doing its job, confirmed by an independent reading. Filed by
        bracket it would read as the two instruments contradicting each other."""
        report = _report({1: LANES_FLOOR}, e1=(1, 1))
        _resolve_with_rows(report, {1: LANES_FLOOR})
        assert report.lanes_row_agreeing == [1]
        assert report.lanes_row_over_bracket == []

    def test_an_edge_with_no_bracket_is_never_given_a_count(self) -> None:
        """🔴 **`verify_road_graph.gd`'s invariant, pinned here rather than
        trusted.** A measured `lanes_source` must imply a measured
        `width_source`, so a row may only ever resolve a bracket this stage
        already licensed a width for. STEWART ROAD `e505` is the edge this
        keeps out: it states three lanes over an *authored* 6.4 m width.
        """
        report = _report()
        _resolve_with_rows(report, {505: 3})
        assert report.lanes == {}
        assert report.lane_rows == {505: 3}, "the row is still recorded, only not used"

    def test_the_row_is_recorded_for_edges_it_cannot_resolve(self) -> None:
        """⚠️ `Q58`'s trap in its dict form. `lane_rows` confined to bracketed
        edges could not see the two implementations diverge on the rest, and
        that diff is the only check either of them has."""
        report = _report(e1=(2, 3))
        _resolve_with_rows(report, {1: 3, 2: 2, 505: 3})
        assert set(report.lane_rows) == {1, 2, 505}


class TestWidestRow:
    """The clustering half — the part duplicated from `arrows._count_rows`.

    ⚠️ **Tested here because it is the half most able to drift.** The snap is a
    shared primitive in `polyline.py`; this rule is written out twice on purpose,
    and until now only `arrows.py`'s copy had tests.
    """

    @staticmethod
    def _at(along: float, across: float) -> _Symbol:
        return _Symbol(along_m=along, offset_m=across, length_m=4.0)

    def test_three_arrows_abreast_are_one_row_of_three(self) -> None:
        row = [self._at(10.0, -3.2), self._at(10.0, 0.0), self._at(10.0, 3.2)]
        assert _widest_rows({1: row}) == {1: 3}

    def test_arrows_strung_along_the_edge_are_separate_rows_of_one(self) -> None:
        """The failure this guards is a whole street reading as one wide row."""
        strung = [self._at(0.0, 0.0), self._at(40.0, 0.0), self._at(80.0, 0.0)]
        assert _widest_rows({1: strung}) == {1: 1}

    def test_an_edge_takes_its_widest_row_and_not_its_mean(self) -> None:
        """A long edge with one marked junction must not average down to two."""
        symbols = [
            self._at(0.0, -3.2),
            self._at(0.0, 0.0),
            self._at(0.0, 3.2),
            self._at(60.0, 0.0),
        ]
        assert _widest_rows({1: symbols}) == {1: 3}

    def test_the_bar_is_half_a_glyph_so_the_two_variants_scale_together(self) -> None:
        """`ArrowGlyph` carries a length per code — 4 m and 6 m variants of the
        same marking — so the bar is derived from the glyph rather than authored.
        1.9 m apart is one row at 4 m; the same pair is still one row at 6 m."""
        near = [self._at(0.0, 0.0), self._at(0.0, 1.9)]
        assert _widest_rows({1: near}) == {1: 1}
        wide = [_Symbol(0.0, 0.0, 6.0), _Symbol(0.0, 2.9, 6.0)]
        assert _widest_rows({1: wide}) == {1: 1}


class _FlatDeck:
    """A `HeightField` stand-in: one slab height over a plan window.

    A fake rather than a built field, because what these tests pin is the walk's
    *rules* — where a run stops, what bridges, which way positive points — and a
    real mesh would make each of those depend on geometry nobody reads here.
    """

    def __init__(self, spans: list[tuple[float, float, float]]) -> None:
        # (low_x, high_x, height); anything outside every span is NaN.
        self.spans = spans

    def sample_along(self, x: np.ndarray, z: np.ndarray, *, slab_gap_m: float) -> np.ndarray:
        out = np.full(len(np.asarray(x)), np.nan)
        for index, value in enumerate(np.asarray(x)):
            for low, high, height in self.spans:
                if low <= value <= high:
                    out[index] = height
                    break
        return out


def _reach(deck, point, normal, sign, deck_y: float = 10.0) -> float | None:
    """`_deck_reach`'s distance alone, dropping the saturation flag.

    The flag has its own test; unwrapping it at every call site would bury the
    rule each of these is actually pinning.
    """
    out = _deck_reach(deck, 0.5, point, normal, sign, deck_y)
    return None if out is None else out[0]


class TestDeckReach:
    """The lateral deck walk (`Q103`).

    ⚠️ **Every rule here fails silently in a frame.** A run that stops early
    reports a narrow deck and a run that leaks reports a wide one, and both
    render as a perfectly ordinary flyover.
    """

    # A station at the origin, walking along +x, so the normal is +x.
    POINT: ClassVar[np.ndarray] = np.array([0.0, 0.0])
    NORMAL: ClassVar[np.ndarray] = np.array([1.0, 0.0])

    def test_the_run_stops_at_the_deck_edge(self) -> None:
        deck = _FlatDeck([(-3.0, 4.0, 10.0)])
        assert _reach(deck, self.POINT, self.NORMAL, +1.0) == pytest.approx(4.0, abs=DECK_ACROSS_M)
        assert _reach(deck, self.POINT, self.NORMAL, -1.0) == pytest.approx(3.0, abs=DECK_ACROSS_M)

    def test_a_centreline_off_the_deck_measures_nothing(self) -> None:
        """🔴 Refused, never scored as a zero-width deck. That station is the
        defect being sized, so folding it in would measure it away."""
        deck = _FlatDeck([(2.0, 6.0, 10.0)])
        assert _reach(deck, self.POINT, self.NORMAL, +1.0) is None

    def test_a_slab_at_another_height_is_not_this_deck(self) -> None:
        """The interchange case: a deck overhead must not extend this one."""
        deck = _FlatDeck([(-3.0, 2.0, 10.0), (2.0, 9.0, 10.0 + 5.0)])
        assert _reach(deck, self.POINT, self.NORMAL, +1.0) == pytest.approx(2.0, abs=DECK_ACROSS_M)

    def test_camber_inside_the_tolerance_stays_one_deck(self) -> None:
        deck = _FlatDeck([(-3.0, 2.0, 10.0), (2.0, 6.0, 10.0 + DECK_TOLERANCE_M * 0.5)])
        assert _reach(deck, self.POINT, self.NORMAL, +1.0) == pytest.approx(6.0, abs=DECK_ACROSS_M)

    def test_a_hole_narrower_than_the_bridge_is_closed(self) -> None:
        """🔴 Without this the walk is a hole detector, not a deck measurement —
        `Q19`'s estate is not watertight. Measured: unbridged, this walk read
        p50 -3.65 m against `tools/deck_margin.py`."""
        gap = DECK_BRIDGE_M * 0.5
        deck = _FlatDeck([(-3.0, 2.0, 10.0), (2.0 + gap, 7.0, 10.0)])
        assert _reach(deck, self.POINT, self.NORMAL, +1.0) == pytest.approx(7.0, abs=DECK_ACROSS_M)

    def test_a_void_wider_than_the_bridge_is_not_closed(self) -> None:
        """The other half of the same rule, and the one that keeps two decks two
        decks. Without it the bridge would span a real void and report a single
        carriageway across an interchange."""
        gap = DECK_BRIDGE_M * 2.0
        deck = _FlatDeck([(-3.0, 2.0, 10.0), (2.0 + gap, 7.0, 10.0)])
        assert _reach(deck, self.POINT, self.NORMAL, +1.0) == pytest.approx(2.0, abs=DECK_ACROSS_M)


class TestDeckReachSaturation:
    """A deck wider than the walk is a LOWER BOUND, and it says so.

    ⚠️ Reported rather than refused: about a tenth of directions reach the cap
    on this region's widest interchanges, so refusing them would throw away the
    decks the walk exists to find. But a clamp that never says it clamped is a
    measurement reporting a constant, which is `Q58`'s trap.
    """

    def test_a_deck_wider_than_the_walk_is_flagged(self) -> None:
        deck = _FlatDeck([(-100.0, 100.0, 10.0)])
        reach, capped = _deck_reach(
            deck, 0.5, np.array([0.0, 0.0]), np.array([1.0, 0.0]), +1.0, 10.0
        )
        assert capped is True
        assert reach == pytest.approx(DECK_MAX_LATERAL_M, abs=DECK_ACROSS_M)

    def test_a_deck_inside_the_walk_is_not_flagged(self) -> None:
        deck = _FlatDeck([(-3.0, 4.0, 10.0)])
        _, capped = _deck_reach(deck, 0.5, np.array([0.0, 0.0]), np.array([1.0, 0.0]), +1.0, 10.0)
        assert capped is False


class TestTheDeckOffsetSign:
    """🔴 The one thing here that renders perfectly when it is backwards.

    `_stations` emits the **right** normal and `surface.mitres` the **left**
    one, and `CLAUDE.md` says the two are opposite on purpose. So the offset
    this stage records is right-of-travel, and whatever finally draws with it
    owes a *named* negation — pinned here rather than described in a comment,
    which is what `Q78` says a sign needs.
    """

    def test_positive_means_the_deck_lies_right_of_the_centreline(self) -> None:
        # Travel along +x in plan, so `_stations`' normal is (-0, 1) — +z, the
        # right hand. A deck hanging further to +z must read positive.
        (_, normal), *_ = _stations(np.array([[0.0, 0.0], [20.0, 0.0]]), 4.0)
        assert normal == pytest.approx([0.0, 1.0])

        deck = _FlatDeck([(-2.0, 8.0, 10.0)])
        # `_FlatDeck` keys on the first coordinate, so walk it in that frame:
        # +1.0 reaches 8 m and -1.0 reaches 2 m, a deck centred 3 m to the right.
        right = _reach(deck, np.array([0.0, 0.0]), np.array([1.0, 0.0]), +1.0)
        left = _reach(deck, np.array([0.0, 0.0]), np.array([1.0, 0.0]), -1.0)
        assert right is not None and left is not None
        assert 0.5 * (right - left) == pytest.approx(3.0, abs=DECK_ACROSS_M)


class TestAlongAt:
    def test_a_station_between_vertices_is_projected_not_snapped(self) -> None:
        """⚠️ Snapping would quantise every deck height to the source's own
        drawing density — coarsest on a long straight, which is exactly where a
        ramp's height changes fastest."""
        plan = np.array([[0.0, 0.0], [100.0, 0.0]])
        along = np.array([0.0, 100.0])
        assert _along_at(plan, along, np.array([37.0, 0.0])) == pytest.approx(37.0)

    def test_it_walks_the_second_segment_too(self) -> None:
        plan = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])
        along = np.array([0.0, 10.0, 20.0])
        assert _along_at(plan, along, np.array([10.0, 4.0])) == pytest.approx(14.0)


def _road_edge(edge_id: int):
    """A minimal `roads.Edge` for the reassignment tests."""
    from pipeline.roads import Edge

    return Edge(
        id=edge_id,
        source_id=edge_id,
        from_node=0,
        to_node=1,
        polyline=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)],
        on_structure=[False, False],
        structure_bounded=[False, False],
        direction=FORWARD,
        lanes=2,
        width_m=6.4,
        speed_limit_kph=50,
        bus_lane=False,
        tram_tracks=False,
        elevation_level=1,
        road_name={"en": "TEST", "zh": ""},
    )


class TestThePublishedOffsetIsTheNegationOfTheSurvey:
    """🔴 The one place the two station normals in this repo have to be paid.

    `carriageway._stations` emits the **right** normal; `surface.mitres` emits
    the **left** one, and `CLAUDE.md` says they are opposite on purpose. So the
    survey measures the deck offset in one frame and `roads.Edge.offset_m`
    publishes it in the other, with `_reassign` negating once by name.

    ⚠️ **Asserted rather than commented, because a sign renders perfectly when
    it is backwards** — a ribbon shifted the wrong way is a ribbon, just further
    off its deck. This is `Q78`'s rule: a negation gets a test, not a paragraph.
    """

    def test_reassign_flips_the_sign_the_survey_measured(self) -> None:
        from pipeline.roads import _reassign

        found = CarriagewayReport()
        found.deck_span_m[7] = 8.0
        found.deck_offset_m[7] = 1.25  # right of travel, the survey's frame

        out = _reassign(_road_edge(7), found)

        assert out.offset_m == -1.25, "published offset must be mitres' left-of-travel frame"
        assert out.offset_source == "deck"
        assert out.width_m == 8.0
        assert out.width_source == "deck"

    def test_an_edge_the_deck_never_answered_keeps_a_zero_offset(self) -> None:
        """`none` rather than a deck offset of 0.0 — the two are different
        claims, and every level-0 edge makes the first."""
        from pipeline.roads import _reassign

        out = _reassign(_road_edge(9), CarriagewayReport())
        assert out.offset_m == 0.0
        assert out.offset_source == "none"


class TestTheDeckTolerancesAreBoundToTheirGrader:
    """🔴 `DECK_TOLERANCE_M`'s own comment says it is REQUIRED to agree with
    `tools/deck_margin.py`'s attribution, and nothing enforced it.

    `test_fence.py`'s precedent: `fence.unit_width_m` is bound to
    `make_barrier.UNIT_WIDTH_M` by a test, because two files holding one number
    drift silently. Here the cost of drift is worse than a drawing error — the
    two are separate implementations of one measurement, so a tolerance that
    stops matching makes every divergence between them unreadable: is it the
    reading, or is it the bar?

    ⚠️ The three walk constants need no test — `deck_margin.py` *imports* them,
    which is stronger. This one cannot be imported: it is an argparse default in
    a third tool.
    """

    def test_the_attribution_matches_deck_errors_default(self) -> None:
        import deck_error

        parser = deck_error.bundle_arguments()
        default = parser.get_default("attribute_within_m")
        assert default == DECK_TOLERANCE_M, (
            f"deck_error --attribute-within-m defaults to {default} and the deck walk "
            f"uses {DECK_TOLERANCE_M}; they grade the same question and must agree"
        )


class TestThePublishersAreKeptOffGrade:
    """🔴 `hong_kong.yaml` says level 1 reads its width from the deck and never
    from the publishers; this is what makes that true of the code.

    ⚠️ **A latent hole, not a defect that shipped.** `roads._reassign` applies
    the deck after the publishers, so a publisher's off-grade width was
    overridden wherever the deck measured that edge — all five of them, in this
    region. What nothing kept empty is the intersection: an off-grade edge a
    publisher licenses and the deck cannot measure. Pinned here because that
    intersection being empty is data, and data moves.
    """

    def test_no_off_grade_edge_is_licensed_by_a_publisher(self) -> None:
        import json
        from pathlib import Path

        out = Path(__file__).resolve().parents[1] / "out" / "wan_chai" / "roadgraph.json"
        if not out.exists():
            pytest.skip("region not built")
        graph = json.loads(out.read_text())
        leaked = [
            edge["id"]
            for edge in graph["edges"]
            if edge["elevation_level"] != 0 and edge["width_source"] not in ("authored", "deck")
        ]
        assert leaked == [], (
            f"edges {leaked} are off-grade and carry a line-publisher width; their 2D lines "
            "find the street under the deck"
        )
