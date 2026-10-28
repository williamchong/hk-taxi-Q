"""The signalled junctions and their authored stages (`P3-3a`, `Q173`)."""

from __future__ import annotations

from typing import ClassVar

import pytest

from pipeline.config_blocks.signals import _signals
from pipeline.signals import approaches_into, stages_of


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
