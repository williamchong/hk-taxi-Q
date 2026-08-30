"""The published-carriageway-edge instrument (`tools/carriageway_margin.py`, `Q57`).

The same standard as the other tool tests: pin only what fails silently. The
report is loud, the distributions are printed in full, and a source that read
nothing shows up as a zero segment count in the first line of output.

⚠️ **The failures this file exists for are all quiet ones.**

- **The ray finds the wrong hit.** `_Index.cast` walks buckets in ray order, but
  a bucket holds its segments in insertion order — take the first hit inside one
  and the answer depends on which sheet was read first. It has to be the nearest.
- **A grade filter that excludes the wrong half.** Both publishers mark the
  *off*-grade case and leave at-grade unmarked, so an inclusion filter reads as
  a city with almost no kerbs — and `Q57` measured that the drawings' commonest
  relative level, `A01`, is the elevated one. Getting this backwards keeps 57%
  of the layer, all of it flyover, and still reports a plausible number.
- **A degenerate segment.** A repeated vertex makes the ray/segment determinant
  vanish rather than miss, so it must be dropped before the cast, not inside it.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
from carriageway_margin import (
    _BANDS,
    BASIS_DECOMPOSED,
    BASIS_TWO_WAY,
    BASIS_UNCROSSED,
    CROSSED,
    UNCROSSED,
    UNRESOLVED,
    EdgeWidth,
    Report,
    Station,
    _Index,
    _segments,
    _sides,
    edge_widths,
    graph_edges,
    lane_bracket,
    lane_verdict,
    main,
    nearest_published,
    opposed_offset_deg,
    width_published,
)

from pipeline.config import BOTH, FORWARD, WidthBounds


def _ask(indexes: list[tuple[str, _Index]]) -> list[tuple[str, float | None, float | None]]:
    """One station's rays, cast north from the origin — the readers' shared input."""
    return _sides(np.zeros(2), np.array([0.0, 1.0]), indexes, 15.0)


def _bounds(**overrides: object) -> WidthBounds:
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


def _index(*lines: list[tuple[float, float]]) -> _Index:
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    for line in lines:
        start, end = _segments(np.asarray(line, dtype=np.float64))
        starts.append(start)
        ends.append(end)
    return _Index(np.vstack(starts), np.vstack(ends))


class TestCast:
    def test_a_ray_measures_the_distance_to_a_crossing_segment(self) -> None:
        index = _index([(-50.0, 4.0), (50.0, 4.0)])
        hit = index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert hit == pytest.approx(4.0)

    def test_the_nearest_hit_wins_regardless_of_insertion_order(self) -> None:
        """The bucket holds segments in the order the sheets were read. Taking
        the first hit found inside one would make the published overhang depend
        on which of six map sheets happened to load first."""
        far = [(-50.0, 9.0), (50.0, 9.0)]
        near = [(-50.0, 2.0), (50.0, 2.0)]

        for order in ((far, near), (near, far)):
            hit = _index(*order).cast(np.zeros(2), np.array([0.0, 1.0]), 15.0)
            assert hit == pytest.approx(2.0)

    def test_a_segment_behind_the_ray_is_not_a_hit(self) -> None:
        """Both directions are cast separately and the nearer taken, so a ray
        that reached backwards would report the opposite kerb as its own."""
        index = _index([(-50.0, -3.0), (50.0, -3.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_segment_beyond_the_cap_is_not_a_hit(self) -> None:
        """An uncapped perpendicular finds something eventually and calls it a
        kerb; the cap is what makes an unmeasurable station say so."""
        index = _index([(-50.0, 30.0), (50.0, 30.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_ray_passing_beyond_a_segments_end_misses_it(self) -> None:
        """The segment is bounded. A reader that solved the infinite line would
        find a kerb across the mouth of every junction it is nowhere near."""
        index = _index([(20.0, 4.0), (60.0, 4.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_ray_parallel_to_a_segment_misses_rather_than_divides(self) -> None:
        index = _index([(0.0, -50.0), (0.0, 50.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_hit_beyond_the_first_index_cell_is_still_found(self) -> None:
        """The candidate walk steps at half a cell; a segment further out than
        one cell must still be reached, or every wide street reads unmeasurable."""
        index = _index([(-50.0, 14.0), (50.0, 14.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) == pytest.approx(14.0)


class TestSegments:
    def test_a_repeated_vertex_is_dropped(self) -> None:
        """A zero-length segment makes the determinant vanish rather than miss,
        so it is a silent wrong answer rather than a skipped one."""
        starts, _ = _segments(np.array([(0.0, 0.0), (0.0, 0.0), (1.0, 0.0)]))

        assert len(starts) == 1

    def test_a_single_vertex_yields_nothing(self) -> None:
        starts, ends = _segments(np.array([(0.0, 0.0)]))

        assert len(starts) == 0
        assert len(ends) == 0


class TestBands:
    def test_the_bands_split_on_the_graphs_own_median(self) -> None:
        """`Q19`'s finding is that 12 of its 14 building failures are under 20 m
        against a graph median of 47.3 m. The bands are that record's split, so
        a reader can line the two tables up; inventing a third boundary here
        would make the comparison unfalsifiable."""
        bounds = [low for low, _, _ in _BANDS]

        assert bounds == [0.0, 20.0, 47.3]


class TestNearestPublished:
    """The preference-order rule the whole two-publisher design rests on."""

    def _pair(self, first_at: float | None, second_at: float | None):
        def side(distance: float | None) -> list[tuple[float, float]]:
            return [(-50.0, distance), (50.0, distance)] if distance is not None else []

        return [
            (
                name,
                _index(side(at)) if at is not None else _index([(999.0, 999.0), (1000.0, 999.0)]),
            )
            for name, at in (("first", first_at), ("second", second_at))
        ]

    def test_the_first_publisher_that_answers_wins(self) -> None:
        """Order is preference, not a tie-break: the drawings are the semantic
        carriageway edge and iB1000 is the fallback for density. Sorting by
        distance instead would silently prefer whichever kerb happened to be
        nearer and make the config's ordering decorative."""
        indexes = self._pair(9.0, 2.0)

        chosen, nearest, _ = nearest_published(_ask(indexes))

        assert chosen == "first"
        assert nearest == pytest.approx(9.0)

    def test_the_second_answers_when_the_first_cannot(self) -> None:
        indexes = self._pair(None, 2.0)

        chosen, nearest, _ = nearest_published(_ask(indexes))

        assert chosen == "second"
        assert nearest == pytest.approx(2.0)

    def test_nobody_answering_is_reported_as_no_name(self) -> None:
        indexes = self._pair(None, None)

        chosen, _, spread = nearest_published(_ask(indexes))

        assert chosen == ""
        assert spread == []

    def test_every_publisher_is_still_asked_so_the_spread_is_real(self) -> None:
        """⚠️ The losing publishers do not decide the measurement, and short-
        circuiting once one answers would be the obvious optimisation — it would
        also delete the cross-check that is `Q57`'s whole argument for reading
        more than one source."""
        indexes = self._pair(9.0, 2.0)

        _, _, spread = nearest_published(_ask(indexes))

        assert sorted(spread) == [pytest.approx(2.0), pytest.approx(9.0)]

    def test_the_nearer_side_wins_within_one_publisher(self) -> None:
        """Both rays come from one `cast_both`; the metric takes the nearer kerb
        because the far one is what a junction mouth and a dual carriageway
        corrupt."""
        index = _index([(-50.0, 6.0), (50.0, 6.0)], [(-50.0, -2.0), (50.0, -2.0)])

        _, nearest, _ = nearest_published(_ask([("only", index)]))

        assert nearest == pytest.approx(2.0)


class TestCastBoth:
    def test_one_solve_answers_both_directions(self) -> None:
        index = _index([(-50.0, 4.0), (50.0, 4.0)], [(-50.0, -7.0), (50.0, -7.0)])

        forward, backward = index.cast_both(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert forward == pytest.approx(4.0)
        assert backward == pytest.approx(7.0)

    def test_a_direction_with_nothing_in_it_is_None(self) -> None:
        index = _index([(-50.0, 4.0), (50.0, 4.0)])

        forward, backward = index.cast_both(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert forward == pytest.approx(4.0)
        assert backward is None

    def test_reversing_the_direction_swaps_the_pair(self) -> None:
        """The backward hit is the same arithmetic read at negative `along`, so
        the two must agree exactly rather than nearly."""
        index = _index([(-50.0, 4.0), (50.0, 4.0)], [(-50.0, -7.0), (50.0, -7.0)])

        forward, backward = index.cast_both(np.zeros(2), np.array([0.0, 1.0]), 15.0)
        reversed_pair = index.cast_both(np.zeros(2), np.array([0.0, -1.0]), 15.0)

        assert reversed_pair == (backward, forward)


class TestSides:
    """The one place a station's rays are cast, which is why it is named."""

    def test_every_publisher_is_asked_even_after_one_spans_the_road(self) -> None:
        """A row per configured publisher, including ones that hit nothing.
        Short-circuiting once someone answers is the obvious optimisation, and
        it would delete both `nearest_published`'s spread and the width's own
        preference order in a single move."""
        spans = _index([(-50.0, 4.0), (50.0, 4.0)], [(-50.0, -4.0), (50.0, -4.0)])
        empty = _index([(999.0, 999.0), (1000.0, 999.0)])

        sides = _ask([("first", spans), ("second", empty)])

        assert [name for name, _, _ in sides] == ["first", "second"]
        assert sides[1] == ("second", None, None)

    def test_both_readers_consume_the_same_list(self) -> None:
        """⚠️ If `_sides` ever becomes a generator, the second consumer sees an
        exhausted iterator: width coverage drops to zero with no error, no
        exception and a report that still prints."""
        index = _index([(-50.0, 5.0), (50.0, 5.0)], [(-50.0, -6.0), (50.0, -6.0)])
        sides = _ask([("only", index)])

        chosen, nearest, _ = nearest_published(sides)
        spanner, near, far, _ = width_published(sides)

        assert (chosen, nearest) == ("only", pytest.approx(5.0))
        assert (spanner, near, far) == ("only", pytest.approx(5.0), pytest.approx(6.0))


class TestWidthPublished:
    def test_a_publisher_reaching_one_side_only_supplies_no_width(self) -> None:
        """Treating a missing far side as zero publishes half-widths as widths,
        and a half-width lands squarely inside the plausible range."""
        spanner, near, far, spread = width_published(
            _ask([("only", _index([(-50.0, 4.0), (50.0, 4.0)]))])
        )

        assert spanner == ""
        assert np.isnan(near) and np.isnan(far)
        assert spread == []

    def test_the_two_sides_come_from_one_publisher(self) -> None:
        """🔴 The drawings are TD's painted edge and iB1000's `RM` is LandsD's
        surveyed margin. Summing one on the near side and the other on the far
        adds a cartographic truth to a topographic one, and the result still
        looks like a road."""
        near_only = _index([(-50.0, 3.0), (50.0, 3.0)])
        spanning = _index([(-50.0, 5.0), (50.0, 5.0)], [(-50.0, -9.0), (50.0, -9.0)])

        spanner, near, far, _ = width_published(
            _ask([("near_only", near_only), ("spanning", spanning)])
        )

        assert spanner == "spanning"
        assert near + far == pytest.approx(14.0)

    def test_the_first_publisher_that_spans_wins_even_when_it_is_wider(self) -> None:
        """Preference, not smallest — the same rule `nearest_published` follows,
        so that config order stays the thing that decides."""
        wide = _index([(-50.0, 8.0), (50.0, 8.0)], [(-50.0, -8.0), (50.0, -8.0)])
        narrow = _index([(-50.0, 4.0), (50.0, 4.0)], [(-50.0, -4.0), (50.0, -4.0)])

        spanner, near, far, spread = width_published(_ask([("wide", wide), ("narrow", narrow)]))

        assert spanner == "wide"
        assert near + far == pytest.approx(16.0)
        assert sorted(spread) == [pytest.approx(8.0), pytest.approx(16.0)]

    def test_the_rays_come_back_signed_rather_than_sorted(self) -> None:
        """⚠️ **The sort moved to `Station` and the sign is now load-bearing.**
        A sum needs no side convention, which is why this returned `(near, far)`
        and threw the sign away. Splitting a span does need one: the partner
        carriageway lies across the *far* ray specifically, so a search has to
        know which way that is. Reading the pair back the other way round is
        `TestSignedRays`."""
        index = _index([(-50.0, 2.0), (50.0, 2.0)], [(-50.0, -11.0), (50.0, -11.0)])

        _, ahead, behind, _ = width_published(_ask([("only", index)]))
        flipped = width_published(
            _sides(np.zeros(2), np.array([0.0, -1.0]), [("only", index)], 15.0)
        )

        assert (ahead, behind) == (pytest.approx(2.0), pytest.approx(11.0))
        assert flipped[1:3] == (pytest.approx(11.0), pytest.approx(2.0))


class TestSignedRays:
    """The near/far ordering is derived, so it survives `left_of`'s sign."""

    def test_a_station_reads_the_same_whichever_way_the_normal_points(self) -> None:
        """`off_centre` and `width_m` are what the rest of the report is built
        from, and neither may depend on which way the polyline happens to run."""
        one = Station(1, 0.0, 0.0, "only", False, "only", 2.0, 11.0)
        other = Station(1, 0.0, 0.0, "only", False, "only", 11.0, 2.0)

        for station in (one, other):
            assert station.width_near_m == pytest.approx(2.0)
            assert station.width_far_m == pytest.approx(11.0)
            assert station.width_m == pytest.approx(13.0)
            assert station.off_centre == pytest.approx(9.0 / 13.0)


class TestLaneBracket:
    """`Q95`'s lane count, which must not be a division by the value under test."""

    def test_the_bracket_comes_from_the_standard_not_from_lane_width_m(self) -> None:
        """🔴 Dividing by `roads.lane_width_m` (3.2) would make the instrument
        agree with the authored constant by construction — `Q72`'s tautology one
        dimension over. 11.9 m holds three 3.65 m lanes and three 3.0 m ones;
        at 3.2 it would read a single unambiguous 3 for the wrong reason."""
        assert lane_bracket(11.9, _bounds(), two_way=False) == (3, 3)
        assert lane_bracket(7.0, _bounds(), two_way=False) == (1, 2)
        assert lane_bracket(14.14, _bounds(), two_way=False) == (3, 4)

    def test_3_4_2_7_collapses_an_ambiguous_bracket_on_a_two_way_edge(self) -> None:
        """A two-way single carriageway may not be divided into three lanes, so
        an ambiguous (3, 4) is a four — which is how STEWART ROAD reads as
        TPDM's 13.5 m four-lane rather than as an odd count."""
        assert lane_bracket(14.14, _bounds(), two_way=True) == (4, 4)
        assert lane_bracket(7.0, _bounds(), two_way=True) == (1, 2)

    def test_an_unambiguously_odd_two_way_count_is_left_standing(self) -> None:
        """⚠️ The collapse narrows an *ambiguous* bracket only. An unambiguous
        three is a finding about the measurement or the direction field, and
        correcting it into agreement would delete the finding."""
        assert lane_bracket(11.9, _bounds(), two_way=True) == (3, 3)


def _station(
    edge: int,
    near: float,
    far: float,
    *,
    junction: bool = False,
    spanned: bool = True,
    partner: int = -1,
    offset_deg: float = 0.0,
) -> Station:
    """One station. `spanned=False` is the near side answering and no far ray.

    `near` and `far` go in on `left_of`'s own sign — forward and backward — and
    `Station` sorts them. Passing them the other way round must produce the same
    row, which `TestSignedRays` is the test of.
    """
    return Station(
        edge=edge,
        nearest_m=near,
        overhang_m=0.0,
        source="only",
        near_junction=junction,
        width_source="only" if spanned else "",
        width_forward_m=near if spanned else float("nan"),
        width_backward_m=far if spanned else float("nan"),
        partner_edge=partner,
        partner_offset_deg=offset_deg,
    )


class TestWidthPartition:
    """The counters, and the trap CLAUDE.md records firing in four other stages.

    ⚠️ **These drive the population, never the counters.** An earlier version of
    this class set `report.widths` and `report.width_over_ceiling` by hand and
    then asserted arithmetic on the values it had just chosen — it would have
    passed unchanged had `survey` appended *below* the guard, which is the whole
    defect the section stakes itself on. Everything here is now derived from
    `stations`, so the assertions can only be satisfied by the derivation.
    """

    def _report(self, spans: list[Station], *, bare: int = 0, unmeasured: int = 0) -> Report:
        """A report holding real stations: `spans` reached across, `bare` did not."""
        report = Report()
        report.stations = [*spans, *[_station(1, 3.0, 4.0, spanned=False) for _ in range(bare)]]
        report.unmeasured = unmeasured
        return report

    def test_a_refused_span_still_reaches_the_population(self) -> None:
        """The `drawn_gauge_m` trap. A width over the ceiling has to be visible
        in `n` and in `max`, or the distribution is confined to the bar by
        construction and reports a clean sweep whatever the region does. Both
        are asserted: either alone is satisfied by a population that never saw
        a refusal."""
        report = self._report([_station(1, 4.0, 4.0), _station(1, 14.0, 15.0)])

        widths = [s.width_m for s in report.spans]

        assert len(widths) == 2
        assert max(widths) == pytest.approx(29.0)
        assert max(widths) > _bounds().max_m

    def test_the_bounds_are_applied_where_the_table_is_printed(self) -> None:
        """`survey` does not take `bounds` at all, so there is no guard for the
        measurement to be stored on the wrong side of. This pins that: the same
        report yields different keeps under different bounds, without being
        re-surveyed."""
        report = self._report([_station(1, 4.0, 4.0), _station(1, 14.0, 15.0)])
        widths = [s.width_m for s in report.spans]

        assert sum(1 for w in widths if w <= 16.5) == 1
        assert sum(1 for w in widths if w <= 29.5) == 2

    def test_a_station_nobody_spanned_is_outside_the_distribution(self) -> None:
        """A station with one ray has no width, so it is reported beside the
        distribution rather than inside it with a placeholder — which is what
        review found `touchdown_error.py`'s `ends_no_target` doing."""
        report = self._report([_station(1, 4.0, 4.0)], bare=6, unmeasured=3)

        assert len(report.spans) == 1
        assert report.stations_walked == 10
        assert report.width_no_span == 9

    def test_width_coverage_is_not_the_near_side_coverage(self) -> None:
        """`coverage` is "one hit *either* side" and reads far higher. Reporting
        one as the other states a number for a measurement that was not made."""
        report = self._report([_station(1, 3.0, 4.0) for _ in range(50)], bare=42, unmeasured=8)

        assert report.coverage == pytest.approx(0.92)
        assert report.width_coverage == pytest.approx(0.50)


class TestLaneVerdict:
    """The aggregate over published edges, which had no test of its own."""

    def _rows(self, *widths: float) -> list[EdgeWidth]:
        return [
            EdgeWidth(
                edge=i,
                median_m=width,
                n=5,
                refused_share=0.0,
                off_centre=0.1,
                source="only",
                refused=False,
            )
            for i, width in enumerate(widths)
        ]

    def _report(self, rows: list[EdgeWidth], direction: str, lanes: int) -> Report:
        report = Report()
        report.directions = {row.edge: direction for row in rows}
        report.lanes = {row.edge: lanes for row in rows}
        return report

    def test_the_authored_count_below_the_bracket_is_too_few(self) -> None:
        rows = self._rows(14.14)

        verdict = lane_verdict(rows, self._report(rows, FORWARD, 2), _bounds())

        assert (verdict.too_few, verdict.too_many, verdict.outside) == (1, 0, 1)

    def test_the_authored_count_above_the_bracket_is_too_many(self) -> None:
        rows = self._rows(7.0)

        verdict = lane_verdict(rows, self._report(rows, FORWARD, 5), _bounds())

        assert (verdict.too_few, verdict.too_many, verdict.outside) == (0, 1, 1)

    def test_a_count_inside_an_ambiguous_bracket_is_neither(self) -> None:
        """(3, 4) holds an authored 3 and an authored 4, so neither is a finding
        about the graph — the ambiguity is, and it is counted separately."""
        rows = self._rows(14.14)

        verdict = lane_verdict(rows, self._report(rows, FORWARD, 3), _bounds())

        assert (verdict.outside, verdict.ambiguous) == (0, 1)

    def test_an_unambiguous_odd_two_way_count_is_a_3_4_2_7_finding(self) -> None:
        rows = self._rows(11.9)

        verdict = lane_verdict(rows, self._report(rows, BOTH, 3), _bounds())

        assert [edge for edge, _ in verdict.findings] == [0]

    def test_the_same_span_one_way_is_not_a_finding(self) -> None:
        """3.4.2.7 is a rule about two-way single carriageways. A one-way edge
        may carry three lanes, so the same 11.9 m must not be reported."""
        rows = self._rows(11.9)

        verdict = lane_verdict(rows, self._report(rows, FORWARD, 3), _bounds())

        assert verdict.findings == []


class TestEdgeWidths:
    def test_an_edge_is_refused_on_its_median_not_by_trimming_its_stations(self) -> None:
        """Gating stations at the ceiling and *then* taking a median
        manufactures a median just under the ceiling for an edge most of whose
        stations escape through a junction mouth — a number that reads as a
        careful measurement of a wide street and is an average of the crossings
        beside it. Here four of five stations escape, so the edge goes."""
        report = Report()
        report.stations = [
            _station(1, 4.0, 4.0),
            *[_station(1, 10.0, 15.0) for _ in range(4)],
        ]

        (row,) = edge_widths(report, _bounds())

        assert row.refused is True
        assert row.median_m == pytest.approx(25.0)
        assert row.refused_share == pytest.approx(0.8)

    def test_an_edge_below_one_through_lane_is_refused_too(self) -> None:
        """Below `hard_min_m` the ray landed on a hatched island or a bay line
        rather than the far kerb, and the reading is not a carriageway at all."""
        report = Report()
        report.stations = [_station(1, 0.5, 0.6) for _ in range(3)]

        (row,) = edge_widths(report, _bounds())

        assert row.refused is True

    def test_an_edge_below_the_published_minimum_is_kept_not_refused(self) -> None:
        """The asymmetry is the point. 3.4.2.2 lets widths fall below the
        table's minimum "on economic or other grounds", and Wan Chai is full of
        genuinely sub-standard back streets. Refusing at `min_m` would delete
        them and publish a region that agrees with TD by construction — the
        ceiling's own trap, inverted."""
        report = Report()
        report.stations = [_station(1, 2.5, 3.0) for _ in range(3)]

        (row,) = edge_widths(report, _bounds())

        assert row.median_m == pytest.approx(5.5)
        assert row.refused is False

    def test_junction_stations_do_not_reach_a_median(self) -> None:
        """A station in a junction mouth has no far kerb to find, so its ray
        crosses the mouth and the edge reads as a wide road."""
        report = Report()
        report.stations = [
            *[_station(1, 4.0, 4.0) for _ in range(3)],
            *[_station(1, 12.0, 14.0, junction=True) for _ in range(20)],
        ]

        (row,) = edge_widths(report, _bounds())

        assert row.n == 3
        assert row.median_m == pytest.approx(8.0)


def _graph(*edges: tuple[int, list[tuple[float, float]], int]) -> dict[str, Any]:
    """A graph of level-0 centrelines, as `graph_edges` reads one."""
    return {
        "edges": [
            {
                "id": edge_id,
                "elevation_level": level,
                "polyline": [[x, 0.0, z] for x, z in points],
            }
            for edge_id, points, level in edges
        ]
    }


class TestCastHit:
    """The directional cast that names an edge, not just a distance."""

    def test_the_owner_comes_back_with_the_distance(self) -> None:
        index = graph_edges(_graph((7, [(-50.0, 6.0), (50.0, 6.0)], 0)))

        ahead, behind = index.cast_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0, exclude=1)

        assert behind is None
        assert ahead is not None
        distance, row = ahead
        assert distance == pytest.approx(6.0)
        assert int(index.owners[row]) == 7

    def test_both_directions_come_from_one_solve(self) -> None:
        """🔴 `cast_both`'s argument one level down: negating the direction
        negates `along` and leaves the cell set and `across` untouched, so
        casting twice re-pays the whole gather to reuse half of it — and makes
        `_solve`'s "one arithmetic, every caller" claim false. Both sides must
        come back positive, and reading them from the flipped normal must agree."""
        index = graph_edges(
            _graph((4, [(-50.0, 5.0), (50.0, 5.0)], 0), (9, [(-50.0, -11.0), (50.0, -11.0)], 0))
        )

        ahead, behind = index.cast_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0, exclude=1)
        flipped = index.cast_hit(np.zeros(2), np.array([0.0, -1.0]), 15.0, exclude=1)

        assert ahead is not None and behind is not None
        assert (ahead[0], int(index.owners[ahead[1]])) == (pytest.approx(5.0), 4)
        assert (behind[0], int(index.owners[behind[1]])) == (pytest.approx(11.0), 9)
        assert (flipped[0][0], flipped[1][0]) == (pytest.approx(11.0), pytest.approx(5.0))

    def test_the_caller_s_own_polyline_is_excluded(self) -> None:
        """⚠️ Not an optimisation. The station sits *on* its own centreline, so
        without this every cast returns that edge at zero distance and no
        partner is ever found — a pairing rule that silently pairs nothing."""
        index = graph_edges(
            _graph((1, [(-50.0, 0.0), (50.0, 0.0)], 0), (2, [(-50.0, 6.0), (50.0, 6.0)], 0))
        )

        ahead, _ = index.cast_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0, exclude=1)

        assert ahead is not None
        assert int(index.owners[ahead[1]]) == 2

    def test_the_nearest_wins_rather_than_the_first_read(self) -> None:
        """A bucket holds its segments in the order they were read, so a
        first-hit rule would make the partner depend on graph ordering."""
        index = graph_edges(
            _graph((9, [(-50.0, 11.0), (50.0, 11.0)], 0), (4, [(-50.0, 5.0), (50.0, 5.0)], 0))
        )

        ahead, _ = index.cast_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0, exclude=1)

        assert ahead is not None
        assert int(index.owners[ahead[1]]) == 4

    def test_a_ramp_overhead_is_not_indexed(self) -> None:
        """A flyover shares plan position with the street beneath it and is
        nobody's opposed carriageway."""
        index = graph_edges(_graph((3, [(-50.0, 6.0), (50.0, 6.0)], 2)))

        assert index.cast_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0, exclude=1) == (None, None)


class TestOpposedOffset:
    """Anti-parallel, not merely parallel — `roads.py` normalises one-ways to
    `forward`, so a pair's two polylines are drawn 180 deg apart and a service
    road running alongside its neighbour is drawn 0 deg apart."""

    def test_an_opposed_centreline_reads_zero(self) -> None:
        assert opposed_offset_deg(np.array([1.0, 0.0]), np.array([-1.0, 0.0])) == pytest.approx(0.0)

    def test_a_centreline_running_alongside_reads_one_eighty(self) -> None:
        assert opposed_offset_deg(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == pytest.approx(
            180.0
        )

    def test_a_perpendicular_centreline_reads_ninety(self) -> None:
        """Which is why the config refuses a tolerance at 90: at that bar a side
        street meeting a main road is its own carriageway's partner."""
        assert opposed_offset_deg(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(90.0)


def _pair_report(
    near_a: float, far_a: float, near_b: float, far_b: float, **station: Any
) -> Report:
    """Two one-way edges, each voting for the other at every station."""
    report = Report()
    report.stations = [
        *[_station(1, near_a, far_a, partner=2, **station) for _ in range(3)],
        *[_station(2, near_b, far_b, partner=1, **station) for _ in range(3)],
    ]
    report.directions = {1: FORWARD, 2: FORWARD}
    return report


class TestPairing:
    """The mutual, anti-parallel pairing that splits a span."""

    def test_a_mutual_pair_decomposes(self) -> None:
        rows = {row.edge: row for row in edge_widths(_pair_report(3.0, 10.0, 3.0, 10.0), _bounds())}

        assert rows[1].partner == 2 and rows[2].partner == 1
        assert rows[1].own_m == pytest.approx(6.0)
        # 13.0 span, two 6.0 m carriageways, 1.0 m left for the median.
        assert rows[1].median_gap_m == pytest.approx(1.0)
        assert rows[1].decomposed is True

    def test_a_one_sided_vote_does_not_pair(self) -> None:
        """🔴 `surface.py` measures its pair gap from both directions because a
        one-sided measure lets the two halves disagree, and the region's pairs
        did disagree, by up to 3.9 m. The same holds for the pairing itself: an
        edge that finds a neighbour has found *something*, and only the
        neighbour finding it back says the two are halves of one road."""
        report = _pair_report(3.0, 10.0, 3.0, 10.0)
        for station in report.stations:
            if station.edge == 2:
                station.partner_edge = 99

        rows = {row.edge: row for row in edge_widths(report, _bounds())}

        assert rows[1].candidate == 2
        assert rows[1].partner is None
        assert rows[1].decomposed is False

    def test_a_partner_past_the_bearing_bar_casts_no_vote(self) -> None:
        """The angle is measured in `survey` and judged here, so the bar can be
        swept without re-walking the region."""
        report = _pair_report(3.0, 10.0, 3.0, 10.0, offset_deg=45.0)

        rows = {row.edge: row for row in edge_widths(report, _bounds())}

        assert rows[1].candidate is None
        assert rows[1].partner is None
        # …and the same survey pairs once the bar admits 45 deg. This is what
        # makes the sweep a re-read rather than a re-measurement.
        loose = edge_widths(report, _bounds(pair_bearing_tolerance_deg=60.0))
        assert {row.edge: row for row in loose}[1].partner == 2

    def test_a_two_way_edge_is_not_paired(self) -> None:
        """It is already a whole carriageway; pairing it would decompose a
        street into itself."""
        report = _pair_report(3.0, 10.0, 3.0, 10.0)
        report.directions = {1: BOTH, 2: FORWARD}

        rows = {row.edge: row for row in edge_widths(report, _bounds())}

        assert rows[1].partner is None and rows[2].partner is None


class TestDecomposition:
    """`own = 2 x near` is an assumption, and the residual is what can refuse it."""

    def test_a_negative_residual_refuses_the_split_and_is_reachable(self) -> None:
        """🔴 The parts cannot exceed the whole. Two 8 m carriageways inside a
        13 m span is `own = 2 x near` failing on that pair, not a finding about
        the city — and the counter is proven reachable here rather than read at
        0, which is `Q72`'s test of a counter."""
        rows = {row.edge: row for row in edge_widths(_pair_report(4.0, 9.0, 4.0, 9.0), _bounds())}

        assert rows[1].median_gap_m == pytest.approx(-3.0)
        assert rows[1].decomposed is False
        assert sum(1 for row in rows.values() if row.median_gap_m < 0.0) == 2

    def test_own_m_is_recorded_over_the_refusals_too(self) -> None:
        """⚠️ `Q58`'s `drawn_gauge_m` trap. A half recorded only where it survives
        is confined to the bar by construction, and the table would report a
        clean split whatever the region did. `n` exceeding the rows read is the
        tell, so an unpaired edge still carries its measured half."""
        report = Report()
        report.stations = [_station(1, 3.0, 10.0) for _ in range(3)]
        report.directions = {1: FORWARD}

        (row,) = edge_widths(report, _bounds())

        assert row.partner is None
        assert row.own_m == pytest.approx(6.0)

    def test_a_half_outside_the_dual_column_is_refused_separately(self) -> None:
        """A row may have a perfectly readable span and an unreadable half, so
        the two flags do not pool. 16.0 m of span passes `max_m`; a 15.0 m half
        of a pair is above Table 3.4.2.1's dual four-lane 14.6."""
        rows = {row.edge: row for row in edge_widths(_pair_report(7.5, 8.5, 0.4, 0.5), _bounds())}

        assert rows[1].refused is False
        assert rows[1].own_refused is True
        assert rows[1].decomposed is False


class TestRayCapRefusal:
    def test_a_cap_that_cannot_reach_the_ceiling_is_refused(self) -> None:
        """The `drawn_gauge_m` trap, reachable from the command line. Two rays
        capped at 8 m cannot sum past 16, so a 16.5 m ceiling can never bind and
        the report announces a clean sweep the cap manufactured."""
        with pytest.raises(SystemExit, match="cannot reach"):
            main(["--region", "wan_chai", "--max-ray-m", "8.0"])


class TestCrossing:
    """Did the two-sided ray reach past the carriageway its centreline sits in?

    🔴 **The counters are driven through the population, never set by hand.**
    `TestWidthPartition` records why: an earlier version of that class assigned
    the report's own counters directly and so tested nothing but its own
    arithmetic. Every row below comes out of `edge_widths`.
    """

    def test_a_span_with_no_room_beyond_it_is_the_edges_own_carriageway(self) -> None:
        """🔴 The finding this rule generalises. `Q95` measured that 96 of 110
        mutual pairs refuse their own split because the ray stopped at the far
        kerb and never crossed the median — LOCKHART ROAD's three shared-endpoint
        pairs among them. A centred 7 m span leaves 0 m beyond a 7 m carriageway,
        which is nowhere for an opposed one to be."""
        report = Report()
        report.stations = [_station(1, 3.5, 3.5) for _ in range(3)]
        report.directions = {1: FORWARD}
        bounds = _bounds()

        (row,) = edge_widths(report, bounds)

        assert row.beyond_m == pytest.approx(0.0)
        assert row.crossing(bounds) == UNCROSSED
        assert row.basis(bounds) == BASIS_UNCROSSED
        # The SPAN is the width here, not half of it — the two one-way bases
        # publish different measurements, which is why the basis travels with it.
        assert row.carriageway_m(bounds) == pytest.approx(7.0)

    def test_a_span_with_a_whole_carriageway_beyond_it_stays_a_span(self) -> None:
        """A short near ray and a long far one: 6 m of carriageway and 10 m
        beyond it, which is room for the narrowest dual carriageway TD
        publishes. Nothing may be read off it."""
        report = Report()
        report.stations = [_station(1, 3.0, 13.0) for _ in range(3)]
        report.directions = {1: FORWARD}
        bounds = _bounds()

        (row,) = edge_widths(report, bounds)

        assert row.beyond_m == pytest.approx(10.0)
        assert row.crossing(bounds) == CROSSED
        assert row.basis(bounds) == ""
        assert math.isnan(row.carriageway_m(bounds))

    def test_the_middle_band_publishes_nothing_and_is_why_there_are_three_states(
        self,
    ) -> None:
        """🔴 `Q95`'s own counter-example, in the shape it has on the region:
        TONNOCHY ROAD `e142`, a 16.7 m span over an 11.78 m half — "not a ray
        that stayed put". 4.96 m beyond is room for a lane and not for a
        carriageway, and a single threshold anywhere in that gap would publish
        16.7 m as somebody's width."""
        report = Report()
        report.stations = [_station(1, 5.89, 10.85) for _ in range(3)]
        report.directions = {1: FORWARD}
        bounds = _bounds()

        (row,) = edge_widths(report, bounds)

        assert bounds.hard_min_m < row.beyond_m < bounds.dual_min_m
        assert row.crossing(bounds) == UNRESOLVED
        assert row.basis(bounds) == ""
        assert math.isnan(row.carriageway_m(bounds))

    def test_every_state_is_reachable_at_zero_and_at_all_rows(self) -> None:
        """⚠️ `Q72`'s test of a counter, applied to all three states: the
        question is never whether one reads 0 but whether any reachable
        configuration moves it. Driving the bounds together rather than reading
        the region's own numbers is what makes that a test.

        🔴 The floor is what licenses a width, and the ceiling never does — at
        `dual_min_m == hard_min_m` nothing is unresolved, and at
        `dual_min_m == dual_max_m` nothing is crossed, but neither moves what is
        published. That is measured on the region too, and it is the reason the
        sweep of this bound leaves the licensed count flat.
        """
        report = Report()
        report.stations = [_station(1, 3.0, 13.0) for _ in range(3)]
        report.directions = {1: FORWARD}

        (crossed,) = edge_widths(report, _bounds())
        assert crossed.crossing(_bounds()) == CROSSED
        # The band collapses upward: with the narrowest dual carriageway as wide
        # as the widest, nothing has room to have crossed.
        assert crossed.crossing(_bounds(dual_min_m=14.6)) == UNRESOLVED
        # …and downward, where every reading that is not uncrossed is crossed.
        assert crossed.crossing(_bounds(dual_min_m=3.0)) == CROSSED
        # The uncrossed boundary answers to `hard_min_m` and to nothing else,
        # which is why sweeping `dual_min_m` cannot move it.
        assert crossed.crossing(_bounds(hard_min_m=12.0)) == UNCROSSED

    def test_the_verdict_is_recorded_over_the_refusals_too(self) -> None:
        """⚠️ `Q58`'s `drawn_gauge_m` trap, at a fourth counter. `beyond_m` is a
        property of two numbers the row already carries, so a row whose span the
        ceiling refuses still has one — and `basis` is what declines to read it,
        separately and visibly."""
        report = Report()
        report.stations = [_station(1, 10.0, 10.0) for _ in range(3)]
        report.directions = {1: FORWARD}
        bounds = _bounds()

        (row,) = edge_widths(report, bounds)

        assert row.refused is True
        assert row.beyond_m == pytest.approx(0.0)
        assert row.crossing(bounds) == UNCROSSED
        # Uncrossed, and still publishing nothing: the span is past `max_m`, so
        # the ray crossed *something* even though there is no room beside it.
        assert row.basis(bounds) == ""

    def test_a_two_way_edge_is_a_width_without_being_classified(self) -> None:
        """It is already a whole carriageway — `_pair_up` refuses to split one on
        the ground that decomposing a street into itself is not a split, and the
        span table has published these as widths since `Q95`."""
        report = Report()
        report.stations = [_station(1, 3.0, 13.0) for _ in range(3)]
        report.directions = {1: BOTH}
        bounds = _bounds()

        (row,) = edge_widths(report, bounds)

        assert row.crossing(bounds) == CROSSED
        assert row.basis(bounds) == BASIS_TWO_WAY
        assert row.carriageway_m(bounds) == pytest.approx(16.0)

    def test_a_decomposed_pair_outranks_uncrossed_and_the_two_disagree(self) -> None:
        """🔴 Both bases can fire on one row, and they name different numbers.
        A partner whose own half measures under a through lane inflates this
        row's residual into the non-negative, so `decomposed` fires while the
        span itself has no room beside it. `basis` resolves toward the partner
        that voted back; the report counts how often that mattered rather than
        assuming it never does — it is 2 rows on the region, both MARSH ROAD."""
        # MARSH ROAD `e36`/`e149`'s own shape, rounded: a 4.4 m span against a
        # partner reading 12.5 m of the same pair. The residual only clears zero
        # because the partner's half is small, and the two halves disagree about
        # the span by 8 m — which is what makes these rows worth counting.
        rows = {
            row.edge: row for row in edge_widths(_pair_report(1.75, 2.65, 1.85, 10.65), _bounds())
        }
        bounds = _bounds()

        assert rows[1].crossing(bounds) == UNCROSSED
        assert rows[1].decomposed is True
        assert rows[1].basis(bounds) == BASIS_DECOMPOSED
        # …and the two really do disagree: half a span, not the whole of it.
        assert rows[1].carriageway_m(bounds) == pytest.approx(3.5)
        assert rows[1].median_m == pytest.approx(4.4)


class TestDualMinBound:
    def test_a_bound_outside_the_dual_column_is_refused(self) -> None:
        """The config guard, which `replace` in `main` goes round. Below the
        floor no span could ever be read as crossing; above the dual ceiling the
        narrowest carriageway of a pair would be wider than the widest."""
        with pytest.raises(SystemExit, match="must lie within"):
            main(
                [
                    "--region",
                    "wan_chai",
                    "--dual-min-m",
                    "20.0",
                ]
            )
