"""The signalled junctions and their authored stages (`P3-3a`, `Q173`)."""

from __future__ import annotations

import copy
import math
from typing import ClassVar

import numpy as np
import pytest

from pipeline.config_blocks.base import SourceLayer
from pipeline.config_blocks.signals import SignalHeads, _drawing, _signals, is_signal_head
from pipeline.drawnroad import Ribbon
from pipeline.polyline import Segments
from pipeline.signals import (
    Approach,
    Head,
    Line,
    Post,
    SignalReport,
    _stopped,
    approaches_into,
    assemble,
    bind_heads,
    host_heads,
    own_stop,
    stages_of,
)

# `hong_kong.yaml`'s `signals.heads.drawing:`, the values `P3-17` drew.
DRAWING: dict = {
    "mount_height_m": 2.40,
    "post_radius_m": 0.06,
    "post_sides": 8,
    "post_headroom_m": 0.15,
    "head_width_m": 0.42,
    "head_height_m": 1.10,
    "head_depth_m": 0.30,
    "lens_diameter_m": 0.30,
    "lens_segments": 12,
    "lens_lift_m": 0.012,
    "colours": {"body": "#2b2f33", "red": "#4a1416", "amber": "#4d3510", "green": "#0f3a24"},
}


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
        "outset_m": 0.45,
        "max_shift_m": 6.0,
        "library": "res://heads.glb",
        "drawing": copy.deepcopy(DRAWING),
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

    def test_the_drawing_reads_its_colours_as_rgb(self) -> None:
        spec = _signals(self._block(), "x")
        assert spec is not None and spec.heads is not None
        assert spec.heads.drawing.colours["red"] == (0x4A, 0x14, 0x16)
        assert spec.heads.drawing.lens_segments == 12

    def test_a_drawing_missing_a_lens_colour_is_refused(self) -> None:
        drawing = copy.deepcopy(DRAWING)
        del drawing["colours"]["amber"]
        with pytest.raises(ValueError, match="colours"):
            _signals(self._block(drawing=drawing), "x")

    def test_a_lens_wider_than_its_share_of_the_face_is_refused(self) -> None:
        # 1.10 m over three lenses is 0.367 m each.
        with pytest.raises(ValueError, match="lens_diameter_m"):
            _signals(self._block(drawing={**DRAWING, "lens_diameter_m": 0.40}), "x")


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


class TestOwnStop:
    """`own_stop`: back to the approach's own painted line, never forward past its mouth."""

    # Travel runs +x from 0 to 100; the mouth is at 90. Left of travel (the
    # nearside, `Snap.offset_m`'s sign) is -z under `(step_z, -step_x)`.
    PLAN: ClassVar[np.ndarray] = np.array([[0.0, 0.0], [100.0, 0.0]])

    @staticmethod
    def _bar(x: float, z0: float, z1: float) -> Line:
        return Line(np.array([[x, z0], [x, z1]]), True)

    def _stop(self, lines: list[Line], *, two_way: bool = False) -> tuple[float, str]:
        return own_stop(self.PLAN, 90.0, 5.0, two_way, lines, 30.0)

    def test_no_line_keeps_the_mouth(self) -> None:
        assert self._stop([]) == (90.0, "mouth")

    def test_a_square_bar_before_the_mouth_moves_the_stop_back(self) -> None:
        assert self._stop([self._bar(83.0, -4.0, 4.0)]) == (pytest.approx(83.0), "bar")

    def test_a_bar_past_the_mouth_moves_nothing(self) -> None:
        assert self._stop([self._bar(95.0, -4.0, 4.0)]) == (90.0, "mouth")

    def test_a_bar_on_the_far_half_is_the_other_ends(self) -> None:
        assert self._stop([self._bar(30.0, -4.0, 4.0)]) == (90.0, "mouth")

    def test_a_bar_along_the_road_is_not_a_stop_line(self) -> None:
        assert self._stop([Line(np.array([[80.0, -2.0], [86.0, -2.0]]), True)])[1] == "mouth"

    def test_a_bar_outside_the_corridor_is_another_roads(self) -> None:
        assert self._stop([self._bar(83.0, -9.0, -7.0)])[1] == "mouth"

    def test_on_a_two_way_road_only_the_nearside_bar_is_this_flows(self) -> None:
        assert self._stop([self._bar(83.0, 0.5, 4.0)], two_way=True)[1] == "mouth"
        assert self._stop([self._bar(83.0, -4.0, -0.5)], two_way=True) == (
            pytest.approx(83.0),
            "bar",
        )

    def test_a_crossing_stops_at_its_near_edge(self) -> None:
        stripes = Line(np.array([[84.0, -3.0], [88.0, -3.0], [84.0, 3.0], [88.0, 3.0]]), False)
        assert self._stop([stripes]) == (pytest.approx(84.0), "crossing")

    def test_a_bar_wins_over_a_crossing(self) -> None:
        stripes = Line(np.array([[85.0, -3.0], [89.0, -3.0]]), False)
        assert self._stop([stripes, self._bar(83.0, -4.0, 4.0)])[1] == "bar"

    def test_the_bar_nearest_the_mouth_wins(self) -> None:
        bars = [self._bar(70.0, -4.0, 4.0), self._bar(86.0, -4.0, 4.0)]
        assert self._stop(bars) == (pytest.approx(86.0), "bar")

    def test_a_crossing_outside_the_corridor_is_another_roads(self) -> None:
        stripes = Line(np.array([[84.0, 7.0], [88.0, 9.0]]), False)
        assert self._stop([stripes])[1] == "mouth"

    def test_a_crossing_past_the_mouth_moves_nothing(self) -> None:
        stripes = Line(np.array([[92.0, -3.0], [96.0, 3.0]]), False)
        assert self._stop([stripes])[1] == "mouth"

    def test_a_bar_just_inside_the_tolerance_counts(self) -> None:
        # 25 degrees off square, inside the 30 the stage takes.
        tilt = 4.0 * math.tan(math.radians(25.0))
        assert (
            self._stop([Line(np.array([[83.0 - tilt, -4.0], [83.0 + tilt, 4.0]]), True)])[1]
            == "bar"
        )


class TestStopped:
    """`_stopped`: the travel-direction flip, and its counters."""

    EDGE: ClassVar[dict] = _edge(7, 1, 2, [(0.0, 0.0), (100.0, 0.0)], "both")

    def test_against_travel_converts_back_to_the_edges_start(self) -> None:
        # Entering at `from` (x 0) against the edge: mouth 10 m from the start,
        # a nearside bar (travel -x, so nearside is +z) at x 17.
        approach = Approach(7, False, 10.0, 270.0)
        bar = Line(np.array([[17.0, 0.5], [17.0, 4.0]]), True)
        report = SignalReport()
        moved = _stopped(approach, self.EDGE, {7: 10.0}, [bar], 30.0, report)
        assert moved.stop_m == pytest.approx(17.0)
        assert report.stops_by_source == {"bar": 1}
        assert report.stop_moved_m == [pytest.approx(7.0)]

    def test_no_drawn_width_is_counted_not_hidden(self) -> None:
        approach = Approach(7, True, 90.0, 90.0)
        report = SignalReport()
        assert _stopped(approach, self.EDGE, {}, [], 30.0, report) is approach
        assert report.stops_by_source == {"no_width": 1}


def _ribbon(plan: list[tuple[float, float]], one_way: bool) -> Ribbon:
    return Ribbon(
        lanes=2,
        carriageway_m=10.0,
        one_way=one_way,
        at=np.array([0.0, 1.0]),
        half_width_m=np.array([5.0, 5.0]),
        offset_m=np.zeros(2),
        plan=np.array(plan),
        height_m=np.zeros(2),
        trim_start_m=0.0,
        trim_end_m=0.0,
        length_m=100.0,
    )


class TestBindHeads:
    """`bind_heads`: the approach a head shows, from where it stands (`P3-3e`)."""

    # Junction 1 at the origin. 20 runs east into it from node 9 (two-way); 21
    # runs east out of it to node 8 (two-way); 22 runs south into it from node 7
    # (one-way); 23 runs north-east out of it to node 6 (one-way). Headings: east
    # 90, west 270, south 180, north-east 45 (+z is south: heading 0 is -z).
    # The east-west axis is stage 0, south stage 1.
    EDGES: ClassVar[list[dict]] = [
        _edge(20, 9, 1, [(-100.0, 0.0), (0.0, 0.0)], "both"),
        _edge(21, 1, 8, [(0.0, 0.0), (100.0, 0.0)], "both"),
        _edge(22, 7, 1, [(0.0, -100.0), (0.0, 0.0)], "forward"),
        _edge(23, 1, 6, [(0.0, 0.0), (70.0, -70.0)], "forward"),
    ]
    JUNCTIONS: ClassVar[list[dict]] = [
        {
            "id": 1,
            "stages": 2,
            "approaches": [
                {"edge": 20, "along": True, "heading_deg": 90.0, "stage": 0},
                {"edge": 21, "along": False, "heading_deg": 270.0, "stage": 0},
                {"edge": 22, "along": True, "heading_deg": 180.0, "stage": 1},
            ],
        }
    ]

    def _bind(
        self,
        posts: list[Post],
        *,
        junction_of: dict[int, int] | None = None,
        junctions: list[dict] | None = None,
        max_shift_m: float = 6.0,
    ) -> tuple[list, SignalReport]:
        spec = SignalHeads(
            source="s",
            member=None,
            layer=SourceLayer("L", {"code": "C", "level": "E"}),
            head_prefixes=("P", "S"),
            refuse_codes=(),
            max_offset_m=25.0,
            assembly_merge_m=1.0,
            outset_m=0.45,
            max_shift_m=max_shift_m,
            library="res://heads.glb",
            drawing=_drawing(DRAWING, "x"),
        )
        drawn = {
            int(edge["id"]): _ribbon(
                [(p[0], p[2]) for p in edge["polyline"]], edge["direction"] != "both"
            )
            for edge in self.EDGES
        }
        report = SignalReport()
        bound = bind_heads(
            posts,
            Segments.of(self.EDGES),
            {int(edge["id"]): edge for edge in self.EDGES},
            drawn,
            junction_of or {},
            junctions if junctions is not None else self.JUNCTIONS,
            spec,
            30.0,
            report,
        )
        return bound, report

    def test_a_nearside_head_before_the_junction_is_its_approachs_primary(self) -> None:
        # Eastbound on 20: the nearside (left of travel) is -z.
        (head,), report = self._bind([Post(-10.0, -7.0, ("P01",))])
        assert (head.edge, head.along, head.primary) == (20, True, True)
        # It looks back west, at the traffic coming.
        assert head.facing_deg == pytest.approx(270.0)
        assert report.bound_by_code == {"P_primary": 1}

    def test_an_offside_head_on_a_two_way_road_shows_the_other_flow(self) -> None:
        # Offside of 20 is the westbound flow, which LEAVES junction 1 here:
        # the far-side head for the traffic coming west along 21.
        (head,), _ = self._bind([Post(-10.0, 7.0, ("S01",))])
        assert (head.edge, head.along, head.stage, head.primary) == (21, False, 0, False)
        assert head.facing_deg == pytest.approx(90.0)

    def test_a_one_way_head_shows_its_own_flow_from_either_kerb(self) -> None:
        (near,), _ = self._bind([Post(-7.0, -40.0, ("P01",))])
        (far,), _ = self._bind([Post(7.0, -40.0, ("P01",))])
        assert (near.edge, near.stage) == (far.edge, far.stage) == (22, 1)

    def test_a_head_out_of_a_junction_with_no_approach_straight_on_is_refused(self) -> None:
        # North-east out along 23, 6 m off it: nothing enters heading north-east.
        bound, report = self._bind([Post(9.8, -18.2, ("P01",))])
        assert bound == []
        assert report.bind_no_straight == 1

    def test_two_stages_straight_on_is_ambiguous(self) -> None:
        junctions = [
            {
                **self.JUNCTIONS[0],
                "approaches": [
                    *self.JUNCTIONS[0]["approaches"],
                    {"edge": 99, "along": True, "heading_deg": 100.0, "stage": 1},
                ],
            }
        ]
        bound, report = self._bind([Post(40.0, -7.0, ("P01",))], junctions=junctions)
        assert bound == []
        assert report.bind_ambiguous == 1

    def test_the_far_end_of_an_edge_is_another_junctions(self) -> None:
        bound, report = self._bind([Post(-90.0, -7.0, ("P01",))])
        assert bound == []
        assert report.bind_unstaged == 1

    def test_a_stub_inside_one_junction_shows_nothing(self) -> None:
        bound, report = self._bind([Post(-10.0, -7.0, ("P01",))], junction_of={9: 1, 1: 1})
        assert bound == []
        assert report.bind_on_stub == 1

    def test_a_post_in_the_road_is_moved_out_past_the_kerb(self) -> None:
        (head,), report = self._bind([Post(-10.0, -2.0, ("P01",))])
        assert head.z == pytest.approx(-5.45)
        assert report.head_shift_m == [pytest.approx(3.45)]

    def test_a_post_clear_of_the_kerb_keeps_its_surveyed_point(self) -> None:
        (head,), report = self._bind([Post(-10.0, -7.0, ("P01",))])
        assert head.z == pytest.approx(-7.0)
        assert report.head_shift_m == [0.0]

    def test_a_move_past_max_shift_is_refused(self) -> None:
        bound, report = self._bind([Post(-10.0, -2.0, ("P01",))], max_shift_m=1.0)
        assert bound == []
        assert report.bind_over_shift == 1

    def test_every_stage_shown_counts_the_junction(self) -> None:
        _, one = self._bind([Post(-10.0, -7.0, ("P01",))])
        _, both = self._bind([Post(-10.0, -7.0, ("P01",)), Post(-7.0, -40.0, ("P02",))])
        assert (one.stages_shown, both.stages_shown) == (0, 1)
