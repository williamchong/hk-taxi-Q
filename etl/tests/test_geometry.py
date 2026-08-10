"""The shared plan-polygon predicates (`P3-7a`).

The overlap cases are chosen for the ways two polygons can meet without either
holding the other's vertices — the plus-sign crossing, the flush edge — because
those are exactly the configurations the tower↔block join (`Q47`) sees in the
iB1000 data and the configurations a vertex-containment-only test passes on
silently.
"""

from __future__ import annotations

import numpy as np

from pipeline.geometry import (
    edges_cross,
    gap_between,
    inside_polygon,
    inside_rings,
    points_in_triangles,
    rings_overlap,
)


def _ring(*points: tuple[float, float]) -> np.ndarray:
    return np.array(points, dtype=np.float64)


def _square(low: float, high: float) -> np.ndarray:
    return _ring((low, low), (high, low), (high, high), (low, high))


class TestInsidePolygon:
    def test_interior_and_exterior_points_separate(self) -> None:
        points = np.array([(5.0, 5.0), (15.0, 5.0)])
        assert inside_polygon(points, _square(0.0, 10.0)).tolist() == [True, False]

    def test_a_concave_notch_is_outside(self) -> None:
        # A U-shape: the notch between the arms is outside the polygon even
        # though it is inside the bounding box.
        u_shape = _ring(
            (0.0, 0.0),
            (30.0, 0.0),
            (30.0, 20.0),
            (20.0, 20.0),
            (20.0, 5.0),
            (10.0, 5.0),
            (10.0, 20.0),
            (0.0, 20.0),
        )
        points = np.array([(15.0, 15.0), (5.0, 15.0)])
        assert inside_polygon(points, u_shape).tolist() == [False, True]


class TestInsideRings:
    def test_a_point_in_the_hole_is_outside(self) -> None:
        donut = [_square(0.0, 30.0), _square(10.0, 20.0)]
        points = np.array([(15.0, 15.0), (5.0, 5.0), (35.0, 5.0)])
        assert inside_rings(points, donut).tolist() == [False, True, False]


class TestEdgesCross:
    def test_a_plus_sign_crossing_is_seen(self) -> None:
        # Two rectangles crossing like a plus sign: real interior overlap, yet
        # neither holds a vertex of the other.
        horizontal = _ring((0.0, 4.0), (10.0, 4.0), (10.0, 6.0), (0.0, 6.0))
        vertical = _ring((4.0, 0.0), (6.0, 0.0), (6.0, 10.0), (4.0, 10.0))
        assert edges_cross(horizontal, vertical)

    def test_disjoint_rings_do_not_cross(self) -> None:
        assert not edges_cross(_square(0.0, 10.0), _square(20.0, 30.0))

    def test_a_shared_edge_is_not_a_proper_crossing(self) -> None:
        # Two squares flush along x=10 — the sheet-cut abutment. Collinear
        # contact must not read as a crossing, or every stitched pair would
        # also count as overlapping.
        assert not edges_cross(_square(0.0, 10.0), _square(10.0, 20.0))


class TestGapBetween:
    def test_the_gap_is_the_closest_approach(self) -> None:
        assert gap_between(np.array([(15.0, 5.0)]), _square(0.0, 10.0)) == 5.0

    def test_a_point_on_the_boundary_has_zero_gap(self) -> None:
        assert gap_between(np.array([(10.0, 5.0)]), _square(0.0, 10.0)) == 0.0


class TestRingsOverlap:
    def test_containment_overlaps(self) -> None:
        assert rings_overlap([_square(0.0, 30.0)], [_square(10.0, 20.0)], touch_m=0.0)

    def test_the_plus_sign_overlaps_without_any_contained_vertex(self) -> None:
        horizontal = [_ring((0.0, 4.0), (10.0, 4.0), (10.0, 6.0), (0.0, 6.0))]
        vertical = [_ring((4.0, 0.0), (6.0, 0.0), (6.0, 10.0), (4.0, 10.0))]
        assert rings_overlap(horizontal, vertical, touch_m=0.0)

    def test_a_flush_edge_overlaps_at_a_positive_tolerance(self) -> None:
        # Exact contact at touch_m=0.0 is unspecified (a boundary vertex
        # classifies arbitrarily under the crossing number), so only the
        # positive-tolerance verdict is promised — and it is the one the
        # join relies on.
        assert rings_overlap([_square(0.0, 10.0)], [_square(10.0, 20.0)], touch_m=0.01)

    def test_a_near_miss_stays_outside_the_tolerance(self) -> None:
        left, right = [_square(0.0, 10.0)], [_square(10.5, 20.0)]
        assert not rings_overlap(left, right, touch_m=0.01)

    def test_a_tower_in_the_courtyard_does_not_overlap(self) -> None:
        # The hole case the join must refuse: a block ring with a courtyard
        # hole, and a tower standing wholly inside the hole.
        donut = [_square(0.0, 30.0), _square(10.0, 20.0)]
        tower = [_square(12.0, 18.0)]
        assert not rings_overlap(donut, tower, touch_m=0.0)


class TestPointsInTriangles:
    def test_interior_points_hit_either_winding(self) -> None:
        counter = np.array([[(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]])
        clockwise = counter[:, ::-1, :]
        point = np.array([(2.0, 2.0)])
        assert points_in_triangles(point, counter).tolist() == [True]
        assert points_in_triangles(point, clockwise).tolist() == [True]

    def test_exterior_points_miss(self) -> None:
        triangles = np.array([[(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]])
        assert points_in_triangles(np.array([(9.0, 9.0)]), triangles).tolist() == [False]

    def test_a_degenerate_sliver_accepts_nothing(self) -> None:
        collinear = np.array([[(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]])
        points = np.array([(5.0, 0.0), (5.0, 1.0)])
        assert points_in_triangles(points, collinear).tolist() == [False, False]

    def test_any_triangle_of_many_counts(self) -> None:
        triangles = np.array(
            [
                [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
                [(20.0, 20.0), (30.0, 20.0), (20.0, 30.0)],
            ]
        )
        assert points_in_triangles(np.array([(22.0, 22.0)]), triangles).tolist() == [True]
