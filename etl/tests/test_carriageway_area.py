"""The strip reading off HyD's pavement area (`pipeline/carriageway_area.py`, `Q128`).

Pin only what fails silently, and on this layer nearly everything does: the
reading is a median over a raster, so a rule that took the wrong cells publishes
a plausible width on every edge and nothing in a frame can show it. A street
drawn 2 m too wide looks like a street.

⚠️ **The three that would each publish a clean table while being wrong:**

- **The run taken as the widest in the row rather than the one through the
  centreline.** A service road or a lay-by beyond a kerb island is HyD
  carriageway too, and the widest run on many rows is the *opposed* carriageway.
- **A cell handed to the wrong edge.** Ownership is the whole of the junction
  rule here — there is no radius and no station count — so a cross street's
  asphalt counted as this one's widens every edge at every junction it meets.
- **A continuation read as a side street.** The graph inserts a node wherever a
  speed limit changes, so an edge running straight on through one opens no
  mouth; treating it as one drops the stations either side of every such node
  and reads the edge on whatever is left.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.carriageway_area import Openings, _Rings, _stations, contiguous_run


class _Edge:
    """The fields `Openings.of` and the raster read off a graph edge."""

    def __init__(
        self,
        edge_id: int,
        polyline: list[tuple[float, float, float]],
        *,
        from_node: int = 0,
        to_node: int = 1,
        width_m: float = 6.4,
        level: int = 0,
    ) -> None:
        self.id = edge_id
        self.polyline = polyline
        self.from_node = from_node
        self.to_node = to_node
        self.width_m = width_m
        self.elevation_level = level
        self.foreign = None


class TestContiguousRun:
    def test_the_run_stops_at_the_first_gap_either_side(self) -> None:
        """🔴 The reading's whole difference from an area. A lay-by beyond a kerb
        island is carriageway HyD draws and not this road's, and counting every
        owned cell in the row reads it in."""
        grid = np.array([[True, False, True, True, True, False, True]])

        assert contiguous_run(grid, centre=3).tolist() == [3]

    def test_a_centreline_off_the_carriageway_reads_nothing(self) -> None:
        """Zero rather than the nearest run: a centreline standing on no paint
        has no strip, and borrowing the nearest one reads a neighbouring road."""
        grid = np.array([[True, True, False, True, True]])

        assert contiguous_run(grid, centre=2).tolist() == [0]

    def test_a_run_reaching_both_edges_of_the_corridor_is_the_whole_row(self) -> None:
        assert contiguous_run(np.array([[True] * 5]), centre=2).tolist() == [5]


class TestRings:
    def _square(self, low: float, high: float) -> np.ndarray:
        return np.array([(low, low), (high, low), (high, high), (low, high), (low, low)])

    def test_a_point_inside_a_ring_is_carriageway(self) -> None:
        index = _Rings([self._square(0.0, 10.0)])

        assert index.inside(np.array([[5.0, 5.0]])).tolist() == [True]

    def test_a_point_outside_every_ring_is_not(self) -> None:
        index = _Rings([self._square(0.0, 10.0)])

        assert index.inside(np.array([[50.0, 5.0]])).tolist() == [False]

    def test_a_ring_far_outside_the_query_box_is_not_tested(self) -> None:
        """The bucket walk is an accelerator and must change no answer, so a
        distant ring has to be absent from the result rather than from the
        search only."""
        index = _Rings([self._square(0.0, 10.0), self._square(1000.0, 1010.0)])

        assert index.inside(np.array([[5.0, 5.0], [1005.0, 1005.0]])).tolist() == [True, True]

    def test_no_rings_reads_nothing_rather_than_raising(self) -> None:
        assert _Rings([]).inside(np.array([[5.0, 5.0]])).tolist() == [False]


class TestStations:
    def test_the_normal_is_perpendicular_to_travel(self) -> None:
        points, normals = _stations(np.array([(0.0, 0.0), (100.0, 0.0)]), 10.0)

        assert len(points) == 10
        assert np.allclose(np.einsum("ij,ij->i", normals, np.array([[1.0, 0.0]] * 10)), 0.0)

    def test_a_polyline_of_no_length_walks_nothing(self) -> None:
        points, _ = _stations(np.array([(0.0, 0.0), (0.0, 0.0)]), 10.0)

        assert len(points) == 0


class TestOpenings:
    def _cross(self) -> list[_Edge]:
        """A north-south street crossing an east-west one at node 1."""
        return [
            _Edge(1, [(0.0, 0.0, 0.0), (50.0, 0.0, 0.0)], from_node=0, to_node=1),
            _Edge(2, [(50.0, 0.0, 0.0), (50.0, 0.0, 40.0)], from_node=1, to_node=2, width_m=12.0),
        ]

    def test_a_side_street_opens_a_mouth_half_its_own_width_wide(self) -> None:
        mouths = Openings.of(self._cross()).mouths(1, 30.0)

        assert len(mouths) == 1
        node, reach = mouths[0]
        assert node.tolist() == [50.0, 0.0]
        assert reach == pytest.approx(6.0)

    def test_a_continuation_is_not_a_side_street(self) -> None:
        """🔴 The graph inserts a node wherever a speed limit changes or a region
        is cut. Read as a mouth, every such node fences off its own street and
        the edge is measured on whatever stations are left."""
        straight = [
            _Edge(1, [(0.0, 0.0, 0.0), (50.0, 0.0, 0.0)], from_node=0, to_node=1),
            _Edge(2, [(50.0, 0.0, 0.0), (100.0, 0.0, 0.0)], from_node=1, to_node=2, width_m=12.0),
        ]

        assert Openings.of(straight).mouths(1, 30.0) == []

    def test_a_straight_back_arm_is_a_continuation_too(self) -> None:
        """Direction is not the question — the same road digitised the other way
        round leaves the node on the same bearing, and `abs` is what says so."""
        doubled = [
            _Edge(1, [(0.0, 0.0, 0.0), (50.0, 0.0, 0.0)], from_node=0, to_node=1),
            _Edge(2, [(100.0, 0.0, 0.0), (50.0, 0.0, 0.0)], from_node=2, to_node=1, width_m=12.0),
        ]

        assert Openings.of(doubled).mouths(1, 30.0) == []

    def test_the_widest_arm_sets_the_mouth(self) -> None:
        crossing = self._cross()
        crossing.append(
            _Edge(3, [(50.0, 0.0, 0.0), (50.0, 0.0, -40.0)], from_node=1, to_node=3, width_m=20.0)
        )

        _, reach = Openings.of(crossing).mouths(1, 30.0)[0]

        assert reach == pytest.approx(10.0)

    def test_an_off_grade_edge_opens_no_mouth_and_gets_none(self) -> None:
        """The reading is level 0 only, and a flyover crossing overhead is not a
        junction at all."""
        overhead = self._cross()
        overhead[1].elevation_level = 1

        assert Openings.of(overhead).mouths(1, 30.0) == []

    def test_an_edge_off_the_graph_has_no_mouths(self) -> None:
        assert Openings.of(self._cross()).mouths(99, 30.0) == []
