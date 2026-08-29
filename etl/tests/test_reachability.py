"""The route analysis (`tools/reachability.py`).

The same standard as the other tool tests: pin only what fails silently. A count
that collapsed to zero would be noticed — and in fact the headline this tool
published on its first run **is** near zero, which is exactly why the traversal
underneath it has to be pinned. A network that quietly forgets one-way, or lets
a car turn round on the edge it was refused, produces a full, plausible,
entirely fictional table saying the walls cost nothing.

⚠️ **The tool's own mutation check is not here** — it is the `nothing (control)`
row it prints on every run, and the operator refusing a main road by hand
(`--refuse` with HENNESSY ROAD's ids loses 14.87% of pairs against the blocked
population's 0.00%). Those want a built region, so they run at the command line
rather than asserting in pytest.
"""

from __future__ import annotations

import pytest
from reachability import (
    NOT_MEASURED,
    build,
    check_documents,
    distances,
    measure,
    pairs,
    percentiles,
    plan_length,
    reachable,
    starved,
)


def _edge(edge_id: int, a: int, b: int, points: list[list[float]], direction="forward") -> dict:
    return {
        "id": edge_id,
        "from": a,
        "to": b,
        "polyline": points,
        "direction": direction,
        "elevation_level": 0,
    }


@pytest.fixture
def diamond() -> dict:
    """One short way and one long way between the same two junctions.

    `e0` runs into the fork; `e1` is the 10 m way across and `e2`+`e3` the 50 m
    way round; `e4` is what both of them lead to. Refusing `e1` therefore costs a
    measurable 40 m and disconnects nothing, which is the shape the region turned
    out to have and the one worth being able to tell from a broken traversal.
    """
    return {
        "nodes": [{"id": node} for node in range(5)],
        "edges": [
            _edge(0, 0, 1, [[0, 0, 0], [10, 0, 0]]),
            _edge(1, 1, 2, [[10, 0, 0], [20, 0, 0]]),
            _edge(2, 1, 3, [[10, 0, 0], [10, 0, 20]]),
            _edge(3, 3, 2, [[10, 0, 20], [20, 0, 20], [20, 0, 0]]),
            _edge(4, 2, 4, [[20, 0, 0], [25, 0, 0]]),
        ],
        "turn_restrictions": [],
    }


class TestPlanLength:
    def test_height_is_not_distance(self) -> None:
        # A ramp must not cost more than the flat street beside it for a reason
        # that has nothing to do with routing — `RoadGraph.plan_distance` again.
        assert plan_length([[0, 0, 0], [3, 100, 4]]) == pytest.approx(5.0)

    def test_a_polyline_is_summed_along_its_stations(self) -> None:
        assert plan_length([[0, 0, 0], [3, 0, 0], [3, 0, 4]]) == pytest.approx(7.0)


class TestBuild:
    def test_a_one_way_edge_is_one_state_and_a_two_way_edge_is_two(self, diamond) -> None:
        # The whole model rests on this: a two-way street is two positions to be
        # in, and only one of them can reach what lies beyond its far end.
        diamond["edges"][1]["direction"] = "both"
        net = build(diamond, {0, 1, 2, 3, 4})
        assert len(net.by_edge[0]) == 1
        assert len(net.by_edge[1]) == 2

    def test_a_refused_edge_is_not_a_corner_to_cut(self, diamond) -> None:
        # Refusing must remove the edge from the network, not merely from the
        # count — otherwise a car routes *through* the wall it cannot fit past.
        net = build(diamond, {0, 2, 3, 4})
        assert 1 not in net.by_edge
        assert all(state[0] != 1 for state in net.states)

    def test_a_u_turn_is_not_a_movement(self, diamond) -> None:
        # A `both` edge shares a node with itself. Without the guard a car turns
        # round on its own carriageway and every dead end stops being one.
        diamond["edges"][0]["direction"] = "both"
        net = build(diamond, {0, 1, 2, 3, 4})
        for index, (edge_id, _, _) in enumerate(net.states):
            assert all(net.states[other][0] != edge_id for other in net.adjacency[index])

    def test_a_turn_restriction_bans_exactly_its_movement(self, diamond) -> None:
        diamond["turn_restrictions"] = [{"from_edge": 0, "via_node": 1, "to_edge": 1}]
        net = build(diamond, {0, 1, 2, 3, 4})
        onward = {net.states[other][0] for other in net.adjacency[net.by_edge[0][0]]}
        # `e1` is banned from `e0` and `e2` is not, at the same junction.
        assert onward == {2}


class TestReachable:
    def test_direction_is_obeyed(self, diamond) -> None:
        # `e4` leaves the far end, so nothing upstream is reachable from it.
        onward = reachable(build(diamond, {0, 1, 2, 3, 4}))
        assert onward[0] == {1, 2, 3, 4}
        assert onward[4] == set()

    def test_the_source_is_not_its_own_destination(self, diamond) -> None:
        diamond["edges"][0]["direction"] = "both"
        onward = reachable(build(diamond, {0, 1, 2, 3, 4}))
        assert 0 not in onward[0]


class TestDistances:
    def test_the_source_edge_pays_for_itself_nowhere(self, diamond) -> None:
        # `e0` is 10 m long and `e1` is 10 m; the answer must be `e1`'s alone, so
        # that a *difference* between two worlds is a difference in route length.
        assert distances(build(diamond, {0, 1, 2, 3, 4}))[0][1] == pytest.approx(10.0)

    def test_the_short_way_is_taken_when_it_exists(self, diamond) -> None:
        cost = distances(build(diamond, {0, 1, 2, 3, 4}))[0]
        assert cost[4] == pytest.approx(15.0)

    def test_refusing_the_short_way_costs_the_difference(self, diamond) -> None:
        # 10 + 5 becomes 20 + 30 + 5. The detour is 40 m and the pair survives —
        # which is the case a reachability-only instrument cannot see at all.
        cost = distances(build(diamond, {0, 2, 3, 4}))[0]
        assert cost[4] == pytest.approx(55.0)


class TestPairs:
    def test_the_population_is_counted_and_not_the_keys(self) -> None:
        # 🔴 `Q58`'s trap. Counting each world over its own keys makes a refusal
        # look expensive however little it cost, because the refused edges leave
        # the numerator by construction.
        onward = {1: {2, 3}, 2: {3}, 3: set()}
        assert pairs(onward, {1, 2, 3}) == 3
        assert pairs(onward, {1, 3}) == 1


class TestMeasure:
    def test_refusing_nothing_loses_nothing(self, diamond) -> None:
        # The control row the tool prints first. A non-zero here would mean the
        # two worlds differ for a reason that is not the refusal (`Q72`).
        verdict = measure(diamond, {0, 1, 2, 3, 4}, set())
        assert verdict.cut == 0
        assert verdict.detours_m == ()

    def test_a_detour_is_reported_where_no_route_is_lost(self, diamond) -> None:
        verdict = measure(diamond, {0, 1, 2, 3, 4}, {1})
        assert verdict.cut == 0
        assert verdict.lost == ()
        assert max(verdict.detours_m) == pytest.approx(40.0)

    def test_a_severed_pair_is_named(self, diamond) -> None:
        # With both ways round refused there is no route from `e0` to `e4`, and
        # the pair has to arrive with its two edge ids on it rather than as a
        # count of one.
        verdict = measure(diamond, {0, 1, 2, 3, 4}, {1, 3})
        assert (0, 4) in verdict.lost


class TestStarved:
    def _entry(self, edge_id: int, widths: list[float]) -> dict:
        return {"edge": edge_id, "clear_width_m": widths}

    def test_an_unmeasured_station_is_not_a_measurement_of_zero(self) -> None:
        # Every station of a short edge can be swallowed by the junction caps at
        # its two ends. Reading the sentinel as a width blocks the whole region.
        clearance = {"clearance": [self._entry(7, [NOT_MEASURED, NOT_MEASURED])]}
        assert starved(clearance, {7: 0}, 3.2) == set()

    def test_the_tightest_station_decides(self) -> None:
        clearance = {"clearance": [self._entry(7, [9.0, 2.0, NOT_MEASURED])]}
        assert starved(clearance, {7: 0}, 3.2) == {7}

    def test_an_off_grade_edge_is_not_in_the_population(self) -> None:
        # `Q13`: the elevated network is refused to the player already, so its
        # clearance is not this tool's to spend.
        clearance = {"clearance": [self._entry(7, [0.0])]}
        assert starved(clearance, {7: 1}, 3.2) == set()


class TestCheckDocuments:
    def test_two_runs_are_refused(self, diamond) -> None:
        clearance = {"clearance": [{"edge": 99, "clear_width_m": [5.0]}]}
        with pytest.raises(SystemExit, match="different runs"):
            check_documents(diamond, clearance)


class TestPercentiles:
    def test_the_tail_is_what_is_published(self) -> None:
        p50, p90, p99, worst = percentiles([float(value) for value in range(1, 101)])
        assert (p50, p90, p99, worst) == pytest.approx((50.5, 90.1, 99.01, 100.0))

    def test_an_empty_distribution_is_zero_rather_than_an_error(self) -> None:
        assert percentiles([]) == (0.0, 0.0, 0.0, 0.0)
