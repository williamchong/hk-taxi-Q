"""The lines a tram runs (`P3-4`, `Q176`).

Weighted to the three ways this reads plausibly and is wrong: a bed running the
wrong way renders the same, a join across to the other track is a smooth tram in
the wrong place, and a stop line the tram misses is a tram through a red.
"""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
import pytest

from pipeline.config import TramLines
from pipeline.tramlines import (
    WITNESS_ROAD,
    WITNESS_TOUCH,
    WITNESS_TRACK,
    TramLinesReport,
    _Flow,
    _Track,
    bind_signals,
    bind_stops,
    build_lines,
    count_in_path,
    direct_beds,
    join_tracks,
    prune_stubs,
)

SPEC = TramLines(
    separation_min_m=1.8,
    separation_max_m=3.6,
    flow_reach_m=12.0,
    min_flow_m=30.0,
    touch_m=6.0,
    join_m=25.0,
    join_heading_deg=40.0,
    open_end_m=25.0,
    stop_max_track_m=12.0,
    signal_reach_m=15.0,
    signal_heading_deg=30.0,
    tram_path_m=1.3,
)
HIGH = (1000.0, 1000.0)


def line(*plan: tuple[float, float]) -> np.ndarray:
    return np.array([[x, 4.0, z] for x, z in plan], dtype=np.float64)


def straight(x0: float, z0: float, x1: float, z1: float, step_m: float = 4.0) -> np.ndarray:
    count = max(2, math.ceil(math.hypot(x1 - x0, z1 - z0) / step_m) + 1)
    return line(*zip(np.linspace(x0, x1, count), np.linspace(z0, z1, count), strict=True))


def road(edge: int, a: tuple[float, float], b: tuple[float, float], direction: str) -> dict:
    return {
        "id": edge,
        "polyline": [[a[0], 4.0, a[1]], [b[0], 4.0, b[1]]],
        "direction": direction,
        "elevation_level": 0,
    }


NO_ROADS = _Flow([])


class TestWhichWayABedRuns:
    def test_the_other_track_on_the_right_of_travel(self) -> None:
        """Left-hand running, x east and z south: of two parallel east-west
        tracks, the northern one (lower z) runs east whichever way it was stored."""
        north = straight(0.0, 100.0, 100.0, 100.0)
        south = straight(0.0, 102.6, 100.0, 102.6)
        report = TramLinesReport()
        tracks = direct_beds([north, south], NO_ROADS, SPEC, report)
        assert tracks[0].points[0, 0] < tracks[0].points[-1, 0]
        assert tracks[1].points[0, 0] > tracks[1].points[-1, 0]
        assert report.by_witness == {WITNESS_TRACK: 2}

    def test_the_stored_order_says_nothing(self) -> None:
        north = straight(100.0, 100.0, 0.0, 100.0)
        south = straight(100.0, 102.6, 0.0, 102.6)
        tracks = direct_beds([north, south], NO_ROADS, SPEC, TramLinesReport())
        assert tracks[0].points[0, 0] < tracks[0].points[-1, 0]
        assert tracks[1].points[0, 0] > tracks[1].points[-1, 0]

    def test_a_single_line_takes_the_flow_of_its_one_way_street(self) -> None:
        bed = straight(0.0, 0.0, 0.0, 100.0)
        flow = _Flow([road(1, (5.0, 100.0), (5.0, 0.0), "forward")])
        report = TramLinesReport()
        tracks = direct_beds([bed], flow, SPEC, report)
        assert tracks[0].points[0, 1 + 1] > tracks[0].points[-1, 1 + 1]
        assert report.by_witness == {WITNESS_ROAD: 1}

    def test_a_two_way_street_speaks_for_nothing(self) -> None:
        bed = straight(0.0, 0.0, 0.0, 100.0)
        flow = _Flow([road(1, (5.0, 100.0), (5.0, 0.0), "both")])
        report = TramLinesReport()
        assert direct_beds([bed], flow, SPEC, report) == []
        assert report.refused_no_direction == 1
        assert report.refused_m == pytest.approx(100.0)

    def test_a_foot_is_on_the_segment_not_its_line(self) -> None:
        """A collinear road past its end would otherwise read as distance zero."""
        bed = straight(0.0, 0.0, 0.0, 100.0)
        far = _Flow([road(1, (0.0, 900.0), (0.0, 800.0), "forward")])
        assert direct_beds([bed], far, SPEC, TramLinesReport()) == []

    def test_a_fragment_takes_the_way_of_the_bed_it_continues(self) -> None:
        bed = straight(0.0, 0.0, 0.0, 100.0)
        fragment = straight(0.0, 118.0, 0.0, 102.0)
        flow = _Flow([road(1, (5.0, 0.0), (5.0, 100.0), "forward")])
        report = TramLinesReport()
        tracks = direct_beds([bed, fragment], flow, SPEC, report)
        assert report.by_witness == {WITNESS_ROAD: 1, WITNESS_TOUCH: 1}
        assert tracks[1].points[0, 2] < tracks[1].points[-1, 2]

    def test_a_fragment_beside_the_other_track_is_not_its_neighbour(self) -> None:
        """🔴 The other track's end stands 2.6 m abeam, parallel and under
        `touch_m`: the chord's own heading is what keeps it out. Without that a
        fragment took the wrong way and the whole main line pruned."""
        north = straight(0.0, 100.0, 100.0, 100.0)
        south = straight(0.0, 102.6, 100.0, 102.6)
        fragment = straight(103.0, 100.0, 118.0, 100.0)
        tracks = direct_beds([north, south, fragment], NO_ROADS, SPEC, TramLinesReport())
        assert tracks[2].points[0, 0] < tracks[2].points[-1, 0]

    def test_a_turnout_beside_the_main_line_does_not_read_as_double_track(self) -> None:
        """🔴 A fragment is not asked: it has the main line on one side for its
        whole length and would run into its own junction."""
        main = straight(0.0, 100.0, 100.0, 100.0)
        other = straight(0.0, 102.6, 100.0, 102.6)
        turnout = straight(100.0, 97.4, 115.0, 97.4)
        report = TramLinesReport()
        direct_beds([main, other, turnout], NO_ROADS, SPEC, report)
        assert report.by_witness.get(WITNESS_TRACK) == 2


def tracked(*beds: np.ndarray) -> list[_Track]:
    return [_Track(bed, row, WITNESS_TRACK) for row, bed in enumerate(beds)]


class TestJoins:
    def test_a_gap_ahead_joins(self) -> None:
        tracks = tracked(straight(0.0, 0.0, 50.0, 0.0), straight(60.0, 0.0, 100.0, 0.0))
        join_tracks(tracks, SPEC, TramLinesReport())
        assert tracks[0].next == [1]
        assert tracks[1].previous == [0]

    def test_the_other_track_abeam_does_not_join(self) -> None:
        tracks = tracked(straight(0.0, 0.0, 50.0, 0.0), straight(50.5, 2.6, 100.0, 2.6))
        join_tracks(tracks, SPEC, TramLinesReport())
        assert tracks[0].next == []

    def test_a_bed_behind_does_not_join(self) -> None:
        tracks = tracked(straight(0.0, 0.0, 50.0, 0.0), straight(40.0, 0.0, 80.0, 0.0))
        join_tracks(tracks, SPEC, TramLinesReport())
        assert tracks[0].next == []

    def test_a_right_angle_does_not_join(self) -> None:
        tracks = tracked(straight(0.0, 0.0, 50.0, 0.0), straight(50.0, 0.0, 50.0, 50.0))
        join_tracks(tracks, SPEC, TramLinesReport())
        assert tracks[0].next == []

    def test_a_jump_over_a_nearer_bed_is_reduced(self) -> None:
        """A bed's end sees the next bed and the one past it; a tram taking the
        second would skip the first."""
        tracks = tracked(
            straight(0.0, 0.0, 50.0, 0.0),
            straight(51.0, 0.0, 60.0, 0.0),
            straight(61.0, 0.0, 100.0, 0.0),
        )
        report = TramLinesReport()
        join_tracks(tracks, SPEC, report)
        assert tracks[0].next == [1]
        assert tracks[1].next == [2]
        assert report.joins_reduced == 1

    def test_a_turnout_is_a_fork(self) -> None:
        tracks = tracked(
            straight(0.0, 0.0, 50.0, 0.0),
            straight(50.5, 0.0, 100.0, 0.0),
            straight(50.2, 0.2, 90.0, 20.0),
        )
        join_tracks(tracks, SPEC, TramLinesReport())
        assert sorted(tracks[0].next) == [1, 2]


class TestPrune:
    def test_a_stub_in_the_street_is_pruned_and_so_is_what_only_feeds_it(self) -> None:
        tracks = tracked(
            straight(0.0, 500.0, 400.0, 500.0),
            straight(401.0, 500.0, 500.0, 500.0),
        )
        join_tracks(tracks, SPEC, TramLinesReport())
        report = TramLinesReport()
        assert prune_stubs(tracks, HIGH, SPEC, report) == []
        assert report.pruned == 2
        assert report.pruned_m == pytest.approx(499.0)

    def test_a_line_through_the_region_is_kept_and_open_at_both_ends(self) -> None:
        tracks = tracked(straight(0.0, 500.0, 500.0, 500.0), straight(501.0, 500.0, 1000.0, 500.0))
        join_tracks(tracks, SPEC, TramLinesReport())
        kept = prune_stubs(tracks, HIGH, SPEC, TramLinesReport())
        assert len(kept) == 2
        assert (kept[0].open_start, kept[0].open_end) == (True, False)
        assert (kept[1].open_start, kept[1].open_end) == (False, True)

    def test_a_bed_near_the_line_that_joins_on_is_not_open(self) -> None:
        """🔴 Within `open_end_m` of the rectangle and running on: read as leaving,
        a tram would vanish 10 m in."""
        tracks = tracked(straight(0.0, 500.0, 10.0, 500.0), straight(11.0, 500.0, 1000.0, 500.0))
        join_tracks(tracks, SPEC, TramLinesReport())
        kept = prune_stubs(tracks, HIGH, SPEC, TramLinesReport())
        assert kept[0].open_end is False


class TestStops:
    def test_a_stop_binds_to_its_nearest_track_at_its_foot(self) -> None:
        tracks = tracked(straight(0.0, 100.0, 100.0, 100.0), straight(100.0, 102.6, 0.0, 102.6))
        report = TramLinesReport()
        bind_stops(tracks, [{"id": "s", "pos": [40.0, 4.0, 97.0]}], SPEC, report)
        assert tracks[0].stops == [{"id": "s", "s_m": pytest.approx(40.0)}]
        assert tracks[1].stops == []
        assert report.stops_bound == 1
        assert report.stops_offside == 0

    def test_a_stop_on_the_right_of_travel_is_counted(self) -> None:
        tracks = tracked(straight(0.0, 100.0, 100.0, 100.0))
        report = TramLinesReport()
        bind_stops(tracks, [{"id": "s", "pos": [40.0, 4.0, 103.0]}], SPEC, report)
        assert report.stops_offside == 1

    def test_a_stop_past_the_bar_binds_to_nothing(self) -> None:
        tracks = tracked(straight(0.0, 100.0, 100.0, 100.0))
        report = TramLinesReport()
        bind_stops(tracks, [{"id": "s", "pos": [40.0, 4.0, 120.0]}], SPEC, report)
        assert tracks[0].stops == []
        assert report.stops_no_track == 1


def plan_with(stop_at: tuple[float, float], heading_deg: float, along: bool = True) -> tuple:
    """A junction with one approach: an edge whose stop point is at `stop_at`."""
    x, z = stop_at
    edge = road(7, (x, z), (x + 200.0, z), "forward") | {"polyline": [[x, 4.0, z], [x, 4.0, z]]}
    edge["polyline"] = [[x, 4.0, z], [x + 1.0, 4.0, z]]
    document: dict[str, Any] = {
        "junctions": [
            {
                "pos": [x + 15.0, 4.0, z],
                "approaches": [
                    {"edge": 7, "along": along, "stop_m": 0.0, "heading_deg": heading_deg}
                ],
            }
        ]
    }
    return document, {7: edge}


class TestSignals:
    def test_a_track_obeys_a_line_it_crosses_off_the_carriageway(self) -> None:
        """🔴 8 m off the road the line belongs to: the car's own line would miss."""
        tracks = tracked(straight(0.0, 108.0, 100.0, 108.0))
        document, edges = plan_with((50.0, 100.0), 90.0)
        report = TramLinesReport()
        bind_signals(tracks, document, edges, SPEC, report)
        assert tracks[0].signals == [{"edge": 7, "along": True, "s_m": pytest.approx(50.0)}]
        assert report.signals_bound == 1

    def test_the_other_way_does_not_bind(self) -> None:
        tracks = tracked(straight(100.0, 108.0, 0.0, 108.0))
        document, edges = plan_with((50.0, 100.0), 90.0)
        report = TramLinesReport()
        bind_signals(tracks, document, edges, SPEC, report)
        assert tracks[0].signals == []
        assert report.junctions_unbound == 1

    def test_past_the_reach_does_not_bind(self) -> None:
        tracks = tracked(straight(0.0, 130.0, 100.0, 130.0))
        document, edges = plan_with((50.0, 100.0), 90.0)
        bind_signals(tracks, document, edges, SPEC, TramLinesReport())
        assert tracks[0].signals == []

    def test_a_line_in_the_gap_between_two_beds_binds_to_the_first(self) -> None:
        """A diamond leaves a gap between beds, and a stop line can stand in it."""
        tracks = tracked(straight(0.0, 108.0, 45.0, 108.0), straight(55.0, 108.0, 100.0, 108.0))
        tracks[0].next = [1]
        document, edges = plan_with((50.0, 100.0), 90.0)
        bind_signals(tracks, document, edges, SPEC, TramLinesReport())
        assert tracks[0].signals[0]["s_m"] == pytest.approx(50.0)
        assert tracks[1].signals == []


class TestTheWhole:
    def test_the_partition_closes(self) -> None:
        beds = [
            straight(0.0, 500.0, 1000.0, 500.0),
            straight(1000.0, 502.6, 0.0, 502.6),
            straight(400.0, 700.0, 500.0, 700.0),
        ]
        report = TramLinesReport()
        edges = [road(1, (0.0, 480.0), (1000.0, 480.0), "both")]
        build_lines(beds, edges, [], {}, HIGH, SPEC, report)
        assert report.beds == report.kept + report.refused_no_direction + report.pruned
        assert report.kept == 2
        assert report.refused_no_direction == 1

    def test_what_stands_in_the_path_is_counted(self, tmp_path) -> None:
        tracks = tracked(straight(0.0, 100.0, 100.0, 100.0))
        (tmp_path / "lamps_placements.json").write_text(
            json.dumps(
                {
                    "placements": [
                        {"transform": {"pos": [50.0, 4.0, 101.0]}},
                        {"transform": {"pos": [50.0, 4.0, 102.0]}},
                    ]
                }
            )
        )
        report = TramLinesReport()
        count_in_path(tracks, 1.3, tmp_path, report)
        assert report.in_tram_path == {"lamps": 1}
