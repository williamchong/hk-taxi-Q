"""The signalled junctions and their authored stages (`P3-3a`, `Q173`)."""

from __future__ import annotations

from typing import ClassVar

import pytest

from pipeline.config_blocks.signals import _signals, is_signal_head
from pipeline.polyline import Segments
from pipeline.signals import (
    Head,
    Post,
    SignalReport,
    approaches_into,
    assemble,
    host_heads,
    stages_of,
)


class TestStages:
    """`stages_of`: one stage per run of travel axes, opposed approaches sharing."""

    def test_opposed_approaches_share_a_stage(self) -> None:
        # North and south bound, east and west bound: two axes, two stages.
        stages = stages_of([0.0, 180.0, 90.0, 270.0], 30.0)
        assert stages[0] == stages[1]
        assert stages[2] == stages[3]
        assert stages[0] != stages[2]
        assert sorted(set(stages)) == [0, 1]

    def test_a_run_straddling_the_fold_is_one_stage(self) -> None:
        # 175 and 5 deg are 10 deg apart as axes; the walk starts at the widest
        # gap, so they are never split across the fold.
        stages = stages_of([175.0, 5.0, 85.0], 30.0)
        assert stages[0] == stages[1]
        assert stages[2] != stages[0]

    def test_the_tolerance_splits_what_it_does_not_reach(self) -> None:
        assert len(set(stages_of([0.0, 40.0], 30.0))) == 2
        assert len(set(stages_of([0.0, 20.0], 30.0))) == 1

    def test_a_three_way_junction_takes_three_stages(self) -> None:
        assert len(set(stages_of([0.0, 60.0, 120.0], 30.0))) == 3

    def test_approaches_on_one_exact_axis_are_one_stage(self) -> None:
        # Equal axes leave no gap but the fold's; a plain two-way road at a
        # crossing is one stage, not two.
        assert stages_of([0.0, 180.0], 30.0) == [0, 0]
        assert stages_of([90.0, 90.0, 270.0], 30.0) == [0, 0, 0]

    def test_one_approach_is_one_stage(self) -> None:
        assert stages_of([123.0], 30.0) == [0]
        assert stages_of([], 30.0) == []


def _edge(
    ident: int, start: int, end: int, plan: list[tuple[float, float]], direction: str
) -> dict:
    return {
        "id": ident,
        "from": start,
        "to": end,
        "direction": direction,
        "polyline": [[x, 0.0, z] for x, z in plan],
    }


class TestApproaches:
    """`approaches_into`: every edge entering the junction, stopped at its mouth."""

    # Junction {1, 2} joined by stub 10. Edge 11 one-way INTO node 1 from the
    # north; 12 one-way OUT of node 2; 13 two-way from the east into node 2.
    EDGES: ClassVar[list[dict]] = [
        _edge(10, 1, 2, [(0.0, 0.0), (10.0, 0.0)], "forward"),
        _edge(11, 3, 1, [(0.0, -50.0), (0.0, 0.0)], "forward"),
        _edge(12, 2, 4, [(10.0, 0.0), (10.0, 50.0)], "forward"),
        _edge(13, 2, 5, [(10.0, 0.0), (60.0, 0.0)], "both"),
    ]
    TRIMS: ClassVar[dict[int, list[float]]] = {11: [1.0, 4.0], 12: [3.0, 0.0], 13: [6.0, 2.0]}

    def test_entering_edges_only_and_the_stub_is_inside(self) -> None:
        found = approaches_into({1, 2}, self.EDGES, self.TRIMS)
        assert sorted((one.edge, one.along) for one in found) == [(11, True), (13, False)]

    def test_a_one_way_entering_at_its_end_stops_short_of_it(self) -> None:
        (one,) = [a for a in approaches_into({1, 2}, self.EDGES, self.TRIMS) if a.edge == 11]
        assert one.stop_m == pytest.approx(50.0 - 4.0)
        # Southbound: towards +z, which is 180 in this frame.
        assert one.heading_deg == pytest.approx(180.0)

    def test_a_two_way_entered_against_stops_at_its_start_trim(self) -> None:
        (one,) = [a for a in approaches_into({1, 2}, self.EDGES, self.TRIMS) if a.edge == 13]
        assert one.stop_m == pytest.approx(6.0)
        # Westbound, from x 60 towards x 10.
        assert one.heading_deg == pytest.approx(270.0)

    def test_a_one_way_leaving_is_no_approach(self) -> None:
        assert all(one.edge != 12 for one in approaches_into({1, 2}, self.EDGES, self.TRIMS))


class TestBlock:
    def test_absent_is_none(self) -> None:
        assert _signals(None, "x") is None

    def test_reads_codes_and_tolerance(self) -> None:
        spec = _signals({"stop_line_codes": ["RM1011"], "axis_tolerance_deg": 30.0}, "x")
        assert spec is not None
        assert spec.stop_line_codes == ("RM1011",)
        assert spec.axis_tolerance_deg == 30.0

    @pytest.mark.parametrize("tolerance", [0.0, 90.0, -5.0])
    def test_a_tolerance_that_stages_nothing_apart_is_refused(self, tolerance: float) -> None:
        with pytest.raises(ValueError):
            _signals({"stop_line_codes": ["RM1011"], "axis_tolerance_deg": tolerance}, "x")

    def test_no_codes_is_refused(self) -> None:
        with pytest.raises(ValueError):
            _signals({"stop_line_codes": [], "axis_tolerance_deg": 30.0}, "x")


class TestHeadGate:
    """`is_signal_head`: a gate on spelling, never a look (`Q76`)."""

    @pytest.mark.parametrize("code", ["P01", "S1", "P24L", "S02R"])
    def test_admits_a_prefix_digits_and_an_optional_side(self, code: str) -> None:
        assert is_signal_head(code, ("P", "S"), ())

    @pytest.mark.parametrize(
        "code", ["PBUTT", "PTR01", "STR02", "KLBOLL", "WIGWAG", "M3", "P", "p01"]
    )
    def test_refuses_the_rest(self, code: str) -> None:
        assert not is_signal_head(code, ("P", "S"), ())

    def test_refuse_codes_win(self) -> None:
        assert not is_signal_head("P90", ("P", "S"), ("P90",))


class TestHeadsBlock:
    BODY: ClassVar[dict] = {
        "source": "s",
        "layer": "L",
        "fields": {"code": "REFNAME", "level": "ELEVATION"},
        "head_prefixes": ["P", "S"],
        "max_offset_m": 25.0,
        "assembly_merge_m": 1.0,
    }

    def _block(self, **heads: object) -> dict:
        return {
            "stop_line_codes": ["RM1011"],
            "axis_tolerance_deg": 30.0,
            "heads": {**self.BODY, **heads},
        }

    def test_absent_heads_is_none(self) -> None:
        spec = _signals({"stop_line_codes": ["RM1011"], "axis_tolerance_deg": 30.0}, "x")
        assert spec is not None
        assert spec.heads is None

    def test_reads_the_gate(self) -> None:
        spec = _signals(self._block(), "x")
        assert spec is not None
        assert spec.heads is not None
        assert spec.heads.is_head("P01")
        assert not spec.heads.is_head("PBUTT")

    def test_a_lower_case_prefix_is_refused(self) -> None:
        # It would load clean and admit nothing.
        with pytest.raises(ValueError):
            _signals(self._block(head_prefixes=["p"]), "x")

    def test_a_refuse_code_the_spelling_already_refuses_is_dead_config(self) -> None:
        with pytest.raises(ValueError):
            _signals(self._block(refuse_codes=["PBUTT"]), "x")


class TestAssemble:
    def test_coincident_heads_are_one_post_at_their_centroid(self) -> None:
        posts = assemble([Head("S01", 0.0, 0.0), Head("P01", 0.4, 0.0), Head("P02", 0.8, 0.0)], 0.5)
        # Single linkage: 0 and 0.8 join through 0.4.
        assert len(posts) == 1
        assert posts[0].codes == ("P01", "P02", "S01")
        assert posts[0].x == pytest.approx(0.4)

    def test_opposite_kerbs_stay_apart(self) -> None:
        assert len(assemble([Head("P01", 0.0, 0.0), Head("P02", 12.0, 0.0)], 1.0)) == 2

    def test_the_order_is_the_sources_not_the_reads(self) -> None:
        heads = [Head("P01", 5.0, 0.0), Head("P02", 0.0, 0.0)]
        assert assemble(heads, 1.0) == assemble(heads[::-1], 1.0)


class TestHostHeads:
    """`host_heads`: the stop line's rule — the nearest edge's nearer node, as its cluster."""

    # Node 1 (a junction: 11, 12 and 13 meet) at the origin; 11 runs west to
    # node 2, a dead end; 12 north to node 3, 13 east to node 4.
    EDGES: ClassVar[list[dict]] = [
        _edge(11, 2, 1, [(-100.0, 0.0), (0.0, 0.0)], "both"),
        _edge(12, 1, 3, [(0.0, 0.0), (0.0, -100.0)], "both"),
        _edge(13, 1, 4, [(0.0, 0.0), (100.0, 0.0)], "both"),
        _edge(14, 3, 5, [(0.0, -100.0), (0.0, -200.0)], "both"),
    ]
    ENDS: ClassVar[dict[int, int]] = {1: 3, 2: 1, 3: 2, 4: 1, 5: 1}

    def _host(self, posts: list[Post], junction: dict[int, int] | None = None) -> tuple:
        report = SignalReport()
        found = host_heads(
            posts,
            Segments.of(self.EDGES),
            {int(edge["id"]): edge for edge in self.EDGES},
            self.ENDS,
            junction or {},
            25.0,
            report,
        )
        return found, report

    def test_a_head_near_a_junction_is_hosted_at_it(self) -> None:
        found, report = self._host([Post(8.0, 3.0, ("P01",)), Post(-3.0, -9.0, ("S01",))])
        assert found == {1: 2}
        assert report.head_hosted == 2

    def test_the_nearer_node_decides_not_the_junction(self) -> None:
        # 70 m north of node 1 on edge 12: nearer node 3, two edges meet there.
        found, _ = self._host([Post(2.0, -70.0, ("P01",))])
        assert found == {3: 1}

    def test_a_dead_end_hosts_nothing(self) -> None:
        found, report = self._host([Post(-90.0, 2.0, ("P01",))])
        assert found == {}
        assert report.head_dead_end == 1

    def test_too_far_from_any_edge_is_no_host(self) -> None:
        found, report = self._host([Post(50.0, 60.0, ("P01",))])
        assert found == {}
        assert report.head_no_host == 1

    def test_a_cluster_is_counted_at_its_root(self) -> None:
        found, _ = self._host([Post(8.0, 3.0, ("P01",))], junction={1: 0, 0: 0})
        assert found == {0: 1}

    def test_the_post_partition_closes(self) -> None:
        posts = [
            Post(8.0, 3.0, ("P01", "S01")),
            Post(-90.0, 2.0, ("P02",)),
            Post(50.0, 60.0, ("P03",)),
        ]
        _, report = self._host(posts)
        assert report.head_posts == report.head_no_host + report.head_dead_end + report.head_hosted
        assert report.head_assembly_size == {"1": 2, "2": 1}
