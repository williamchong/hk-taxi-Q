"""The centreline registration (`tools/centreline_error.py`).

The same standard as the other tool tests: pin only what fails silently.

🔴 **The sign is what this file mostly exists for.** `carriageway._stations`
emits its normal *right* of travel and `surface.mitres` emits *left*; nothing
noticed for as long as the survey kept only `ahead + behind` and
`min(ahead, behind)`, both of which are sign-free. The moment a tool keeps the
difference, a dropped negation stops being invisible and starts publishing "the
sourced correction makes it worse" — a table that is plausible, publishable and
false. `Q78` is the same failure one layer down, where `signs.py`'s absolute
`shift_m` could not report the direction of the move it measured and 95 of 654
posts went the wrong way through three published distributions.

⚠️ **The tool's own control checks are NOT here.** They are `check_baseline`
against `clearance.json`, the assertion that the control world's edges are the
graph's own object, and the re-measurement of Part A on the shifted graph
(|off-centre| p50 0.373 m -> 0.043 m on the region). All three want a built
region and fetched sources, so they run at the command line rather than
asserting in pytest — `test_narrowing.py` says the same of its baseline column.

⚠️ **No metre measured on the real region is pinned here.** 143.2 m, 0.88 m,
50.60 m and the rest are findings, and pinning a finding turns a grader into a
ratchet, which is what this family of tools is deliberately not.
"""

from __future__ import annotations

import numpy as np
import pytest
from centreline_error import (
    Offset,
    Priced,
    clears_at,
    percentiles,
    priced,
    ramp,
    runs_backwards,
    shift_graph,
    sides,
    signed_percentiles,
    station_weights,
    surveyed_table,
)

from pipeline.carriageway import _stations
from pipeline.clearance import NOT_MEASURED, ClearanceReport
from pipeline.surface import mitres


def _points(*xz: tuple[float, float]) -> np.ndarray:
    """A polyline at a constant height, in the game's Y-up frame."""
    return np.array([[x, 4.0, z] for x, z in xz], dtype=np.float64)


def _edge(edge_id: int, points: np.ndarray, direction: str = "forward") -> dict:
    return {
        "id": edge_id,
        "from": edge_id,
        "to": edge_id + 1,
        "polyline": points.tolist(),
        "direction": direction,
        "elevation_level": 0,
        "width_source": "one_way_uncrossed",
    }


def _offset(edge_id: int, shift_m: float, *, basis: str = "one_way_uncrossed") -> Offset:
    return Offset(
        edge=edge_id,
        walked=10,
        n=10,
        junction=0,
        off_centre_m=-shift_m,
        spread_m=0.0,
        sign_mixed=0,
        span_m=6.0,
        own_m=5.8,
        publishers="ib1000",
        direction="forward",
        basis=basis,
    )


class TestSignFrame:
    """🔴 The negation, pinned from both ends."""

    def test_the_station_normal_is_the_negation_of_mitres(self):
        """The two conventions in this repo are opposite, and must stay opposite.

        If anyone "restores consistency" in `pipeline/carriageway.py`, this fails
        loudly. Without it, `_LEFT` silently reverses every shift the tool
        measures and the tool goes on printing a full table.
        """
        points = _points((0.0, 0.0), (10.0, 0.0), (20.0, 0.0))
        _, normal = _stations(points[:, [0, 2]], 4.0)[0]
        assert normal == pytest.approx(-mitres(points)[0])

    def test_left_of_travel_is_negative_z_for_travel_along_x(self):
        """`mitres`' own documented frame, restated where the tool depends on it."""
        points = _points((0.0, 0.0), (10.0, 0.0))
        assert mitres(points)[0] == pytest.approx([0.0, -1.0])


class TestRamp:
    def test_the_shift_is_zero_at_both_ends(self):
        along = np.linspace(0.0, 100.0, 11)
        weights = ramp(along, 15.0)
        assert weights[0] == 0.0
        assert weights[-1] == 0.0

    def test_the_shift_is_full_in_the_middle_of_a_long_run(self):
        along = np.linspace(0.0, 100.0, 11)
        assert ramp(along, 15.0)[5] == pytest.approx(1.0)

    def test_no_taper_delivers_the_full_shift_at_the_ends(self):
        """The upper-bound mode has to be reachable, or the endpoint cost is
        never measured and the taper's price is taken on trust."""
        along = np.linspace(0.0, 100.0, 11)
        assert ramp(along, 0.0).tolist() == [1.0] * 11

    def test_a_run_shorter_than_two_tapers_never_reaches_the_full_shift(self):
        """`e781` has 5 vertices and `e207` has 4. A table reporting the nominal
        shift on those would be reporting a move it did not make."""
        along = np.linspace(0.0, 10.0, 5)
        assert ramp(along, 15.0).max() < 1.0


class TestStationWeights:
    def test_the_weights_sum_to_the_edges_own_length(self):
        """This is what makes a per-vertex corridor into a length at all."""
        points = _points((0.0, 0.0), (10.0, 0.0), (10.0, 20.0))
        assert station_weights(points).sum() == pytest.approx(30.0)

    def test_an_interior_vertex_carries_half_of_each_neighbour(self):
        points = _points((0.0, 0.0), (10.0, 0.0), (10.0, 20.0))
        assert station_weights(points).tolist() == pytest.approx([5.0, 15.0, 10.0])

    def test_the_weights_are_not_the_sample_pitch(self):
        """🔴 The defect this function replaced. `stations * ALONG_M` published
        3.50 m where the edge carries 50.60 m, and it read like a length."""
        points = _points((0.0, 0.0), (100.0, 0.0))
        assert station_weights(points).sum() == pytest.approx(100.0)


class TestShiftGraph:
    def test_the_control_moves_nothing(self):
        """`Q72`'s control row. A control that differs makes every other row
        unreadable, because the worlds then differ for a reason that is not the
        shift."""
        graph = {"nodes": [], "edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        world = shift_graph(graph, {0: _offset(0, 2.0)}, scale=0.0, taper_m=0.0)
        assert world.graph["edges"] == graph["edges"]

    def test_a_positive_shift_moves_left_of_travel(self):
        """Travel along +x, so left is -z, and a positive shift lands there."""
        graph = {"nodes": [], "edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        world = shift_graph(graph, {0: _offset(0, 2.0)}, scale=1.0, taper_m=0.0)
        moved = np.asarray(world.graph["edges"][0]["polyline"])
        assert moved[:, 2].tolist() == pytest.approx([-2.0, -2.0])

    def test_reversing_the_shift_reverses_the_move(self):
        """The mutation check for the sign, at unit size. A tool reporting the
        same answer at +1 and -1 is not applying the sign it measured."""
        graph = {"nodes": [], "edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        forward = shift_graph(graph, {0: _offset(0, 2.0)}, scale=1.0, taper_m=0.0)
        backward = shift_graph(graph, {0: _offset(0, 2.0)}, scale=-1.0, taper_m=0.0)
        assert np.asarray(forward.graph["edges"][0]["polyline"])[0][2] == pytest.approx(-2.0)
        assert np.asarray(backward.graph["edges"][0]["polyline"])[0][2] == pytest.approx(2.0)

    def test_an_unlicensed_edge_is_left_alone(self):
        """An edge the publishers licensed nothing for has no sourced correction,
        so there is nothing to move it by — and moving it anyway would be the
        invented geometry `Q54` refuses."""
        graph = {"nodes": [], "edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        world = shift_graph(graph, {0: _offset(0, 2.0, basis="")}, scale=1.0, taper_m=0.0)
        assert world.graph["edges"] == graph["edges"]

    def test_the_height_and_the_vertex_count_survive(self):
        """`walk` refuses an edge whose station count and half-width count
        disagree, naming both documents — so a joint that dropped a vertex would
        take the whole region out with a message about a mismatched build."""
        points = _points((0.0, 0.0), (25.0, 0.0), (50.0, 0.0))
        graph = {"nodes": [], "edges": [_edge(0, points)]}
        world = shift_graph(graph, {0: _offset(0, 2.0)}, scale=1.0, taper_m=0.0)
        moved = np.asarray(world.graph["edges"][0]["polyline"])
        assert len(moved) == 3
        assert moved[:, 1].tolist() == pytest.approx([4.0, 4.0, 4.0])

    def test_an_untapered_shift_opens_the_shared_node_by_the_shift(self):
        """The node break as a measurement rather than an argument. Plan node
        coincidence is exact in the shipped region, so there is no slack."""
        graph = {"nodes": [], "edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        world = shift_graph(graph, {0: _offset(0, 2.0)}, scale=1.0, taper_m=0.0)
        assert world.node_gap_m == pytest.approx(2.0)

    def test_a_tapered_shift_opens_nothing(self):
        graph = {"nodes": [], "edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        world = shift_graph(graph, {0: _offset(0, 2.0)}, scale=1.0, taper_m=15.0)
        assert world.node_gap_m == pytest.approx(0.0)

    def test_a_shift_that_runs_backwards_is_refused_rather_than_repaired(self):
        """`surface.boundary` repairs this case by holding the inner rail still,
        which is right for a rail and wrong for a centreline: it would change the
        edge's length and move every station on it."""
        points = _points((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (8.0, 4.0))
        graph = {"nodes": [], "edges": [_edge(0, points)]}
        world = shift_graph(graph, {0: _offset(0, 10.0)}, scale=1.0, taper_m=0.0)
        assert world.refused == (0,)
        assert world.graph["edges"] == graph["edges"]


class TestRunsBackwards:
    def test_a_straight_offset_does_not(self):
        points = _points((0.0, 0.0), (10.0, 0.0), (20.0, 0.0))
        assert not runs_backwards(points, points)

    def test_a_reversed_segment_does(self):
        points = _points((0.0, 0.0), (10.0, 0.0))
        moved = _points((0.0, 0.0), (-10.0, 0.0))
        assert runs_backwards(points, moved)


class TestSurveyedTable:
    def test_a_licensed_edge_is_narrowed_to_half_its_surveyed_span(self):
        drawn = {0: {"edge": 0, "half_width_m": [5.12, 5.12], "trim_start_m": 1.0}}
        graph = {"edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        table, refused = surveyed_table(drawn, {0: _offset(0, 0.0)}, graph)
        assert table[0]["half_width_m"] == pytest.approx([3.0, 3.0])
        assert refused == []

    def test_the_rest_of_the_entry_survives(self):
        """The trims ride through untouched — `narrowing.scaled`'s own shape."""
        drawn = {0: {"edge": 0, "half_width_m": [5.12], "trim_start_m": 1.25}}
        graph = {"edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        table, _ = surveyed_table(drawn, {0: _offset(0, 0.0)}, graph)
        assert table[0]["trim_start_m"] == 1.25

    def test_a_narrower_drawn_station_is_not_widened(self):
        drawn = {0: {"edge": 0, "half_width_m": [1.0]}}
        graph = {"edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        table, _ = surveyed_table(drawn, {0: _offset(0, 0.0)}, graph)
        assert table[0]["half_width_m"] == pytest.approx([1.0])

    def test_an_authored_width_is_refused_and_kept_at_its_drawn_width(self):
        """🔴 Both halves matter. Refused, so nothing is priced against an
        invented carriageway; kept, so `walk` still has a row for the edge and
        does not take the region out with a mismatched-build message."""
        drawn = {0: {"edge": 0, "half_width_m": [5.12]}}
        published = _edge(0, _points((0.0, 0.0), (50.0, 0.0)))
        published["width_source"] = "authored"
        table, refused = surveyed_table(drawn, {0: _offset(0, 0.0)}, {"edges": [published]})
        assert refused == [0]
        assert table[0]["half_width_m"] == pytest.approx([5.12])

    def test_an_unlicensed_edge_is_refused_the_same_way(self):
        drawn = {0: {"edge": 0, "half_width_m": [5.12]}}
        graph = {"edges": [_edge(0, _points((0.0, 0.0), (50.0, 0.0)))]}
        table, refused = surveyed_table(drawn, {0: _offset(0, 0.0, basis="")}, graph)
        assert refused == [0]
        assert table[0]["half_width_m"] == pytest.approx([5.12])


class TestPriced:
    def _report(self, widths: list[float]) -> ClearanceReport:
        report = ClearanceReport()
        report.corridor_m[0] = widths
        return report

    def test_the_blocked_length_is_weighted_not_counted(self):
        """🔴 The defect. Two of four stations under the bar on a 90 m edge is
        not `2 * ALONG_M`; it is however much of the run those two stand for."""
        points = _points((0.0, 0.0), (30.0, 0.0), (60.0, 0.0), (90.0, 0.0))
        graph = {"edges": [_edge(0, points)]}
        found = priced(self._report([0.5, 0.5, 9.0, 9.0]), {0: _offset(0, 0.0)}, graph, set(), 1.8)
        # Weights are [15, 30, 30, 15], so the two blocked end-and-interior
        # stations stand for 45 m of the 90 — not `2 * ALONG_M`, and not half of
        # the station count either.
        assert found[0].along_m == pytest.approx(45.0)
        assert found[0].length_m == pytest.approx(90.0)
        assert found[0].share == pytest.approx(0.5)

    def test_an_unmeasured_station_is_neither_blocked_nor_length(self):
        """`NOT_MEASURED` is a station the ribbon never reached, not a clear one
        and not a blocked one."""
        points = _points((0.0, 0.0), (30.0, 0.0), (60.0, 0.0))
        graph = {"edges": [_edge(0, points)]}
        found = priced(
            self._report([NOT_MEASURED, 0.5, 9.0]), {0: _offset(0, 0.0)}, graph, set(), 1.8
        )
        assert found[0].stations == 2
        assert found[0].length_m == pytest.approx(45.0)

    def test_a_refused_edge_is_absent_rather_than_priced_at_its_drawn_width(self):
        points = _points((0.0, 0.0), (30.0, 0.0))
        graph = {"edges": [_edge(0, points)]}
        assert priced(self._report([0.5, 0.5]), {0: _offset(0, 0.0)}, graph, {0}, 1.8) == {}

    def test_an_unblocked_edge_prices_zero_rather_than_disappearing(self):
        """An edge that drops out of the table is an edge nobody can see was
        asked about."""
        points = _points((0.0, 0.0), (30.0, 0.0))
        graph = {"edges": [_edge(0, points)]}
        found = priced(self._report([9.0, 9.0]), {0: _offset(0, 0.0)}, graph, set(), 1.8)
        assert found[0].along_m == 0.0
        assert found[0].share == 0.0


class TestClearsAt:
    def test_the_first_clearing_rung_is_reported(self):
        results = {0.0: {7: 1.0}, 1.0: {7: 4.0}, 2.0: {7: 5.0}}
        assert clears_at((0.0, 1.0, 2.0), results, 7, 3.2) == 1.0

    def test_an_edge_that_clears_and_re_blocks_reports_the_first(self):
        """⚠️ Moving sideways can clear one blocker and run into the next, which
        is why the whole row is printed beside this number."""
        results = {0.0: {7: 1.0}, 1.0: {7: 4.0}, 2.0: {7: 1.0}}
        assert clears_at((0.0, 1.0, 2.0), results, 7, 3.2) == 1.0

    def test_an_edge_that_never_clears_is_nan_not_the_end_of_the_ladder(self):
        results = {0.0: {7: 1.0}, 1.0: {7: 1.0}}
        assert np.isnan(clears_at((0.0, 1.0), results, 7, 3.2))

    def test_an_unmeasured_edge_does_not_count_as_clear(self):
        """`NOT_MEASURED` is -1.0, so a naive comparison would read it as narrow
        rather than as absent; the failure worth pinning is the other one, an
        unmeasured edge reported as having cleared."""
        results = {0.0: {7: NOT_MEASURED}}
        assert np.isnan(clears_at((0.0,), results, 7, 3.2))


class TestPercentiles:
    def test_the_tail_is_what_is_published(self):
        values = [float(value) for value in range(101)]
        assert percentiles(values) == pytest.approx((50.0, 90.0, 99.0, 100.0))

    def test_an_empty_distribution_is_zero_rather_than_an_error(self):
        assert percentiles([]) == (0.0, 0.0, 0.0, 0.0)


class TestSignedPercentiles:
    def test_a_two_sided_population_reports_both_tails(self):
        """🔴 The reading the house convention cannot give. A population half at
        +2 and half at -2 has a magnitude median of 2 and a signed median of 0;
        publishing only the first says "off by 2 m" and only the second says
        "centred", and both are wrong on their own."""
        values = [-2.0] * 50 + [2.0] * 50
        p1, _, p50, _, p99 = signed_percentiles(values)
        assert p1 < 0.0 < p99
        assert p50 == pytest.approx(0.0)

    def test_an_empty_distribution_is_zero_rather_than_an_error(self):
        assert signed_percentiles([]) == (0.0, 0.0, 0.0, 0.0, 0.0)


class TestSides:
    def test_a_left_and_a_right_are_not_averaged_away(self):
        assert sides([-2.0, -1.0, 3.0]) == (1, 2, 0)

    def test_a_centreline_exactly_on_the_middle_is_its_own_column(self):
        """`Q19`'s own 2026-08-21 precedent: a tie is reported as a tie, because
        breaking one by index leans every symmetric cross-section the same way
        and makes the row read less mixed than it is."""
        assert sides([0.0, 0.0, 1.0]) == (1, 0, 2)


class TestPricedShare:
    def test_a_zero_length_edge_shares_zero_rather_than_dividing(self):
        row = Priced(
            edge=0, carriageway_m=6.0, stations=0, stations_under=0, length_m=0.0, along_m=0.0
        )
        assert row.share == 0.0
