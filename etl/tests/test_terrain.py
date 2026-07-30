"""Ground sampling for `Q11`.

`P1-2` measured Wan Chai's ground at a median 4.29 m above the vertical datum,
so taking level 0 as y=0 would bury every road. These check that the height
field answers what the terrain actually says, and — just as important — that it
says nothing rather than zero where the terrain does not reach.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.gltf import MeshData
from pipeline.terrain import HeightField


def _surface(triangles: list[list[tuple[float, float, float]]]) -> MeshData:
    positions = np.array(
        [corner for triangle in triangles for corner in triangle], dtype=np.float64
    )
    return MeshData(
        name="terrain",
        positions=positions,
        normals=np.tile(np.array([0.0, 1.0, 0.0], np.float32), (len(positions), 1)),
        triangles=np.arange(len(positions), dtype=np.uint32).reshape(-1, 3),
    )


def _quad(y00: float, y10: float, y01: float, y11: float, size: float = 10.0) -> MeshData:
    """A square patch spanning `(0, 0)`-`(size, size)` with the given corner heights."""
    a, b = (0.0, y00, 0.0), (size, y10, 0.0)
    c, d = (0.0, y01, size), (size, y11, size)
    return _surface([[a, b, c], [b, d, c]])


class TestSampling:
    def test_a_flat_patch_returns_its_own_height(self) -> None:
        field = HeightField.from_meshes([_quad(4.0, 4.0, 4.0, 4.0)])
        np.testing.assert_allclose(field.sample([2.0, 8.0], [3.0, 9.0]), [4.0, 4.0])

    def test_a_slope_is_interpolated_across_the_triangle(self) -> None:
        """Barycentric, not nearest-vertex. Hong Kong's north shore climbs 50 m
        inside this region, so a road sampled per vertex would step rather than
        ramp if this snapped."""
        field = HeightField.from_meshes([_quad(0.0, 10.0, 0.0, 10.0)])
        np.testing.assert_allclose(
            field.sample([0.0, 2.5, 5.0, 10.0], [5.0] * 4), [0.0, 2.5, 5.0, 10.0]
        )

    def test_a_point_outside_the_terrain_is_nan_not_zero(self) -> None:
        """Substituting a height here would put the road back on the datum in
        exactly the places nobody looks — which is the bug this module exists
        to fix."""
        field = HeightField.from_meshes([_quad(4.0, 4.0, 4.0, 4.0)])
        assert np.isnan(field.sample([-50.0, 500.0], [0.0, 0.0])).all()

    def test_a_point_in_a_covered_cell_but_outside_every_triangle_is_nan(self) -> None:
        """The grid indexes bounding boxes, so a cell can hold a triangle that
        does not cover the query point. Returning that triangle's height anyway
        would be a plausible answer from the wrong surface."""
        field = HeightField.from_meshes(
            [_surface([[(0.0, 7.0, 0.0), (10.0, 7.0, 0.0), (0.0, 7.0, 10.0)]])]
        )

        assert field.sample([1.0], [1.0])[0] == pytest.approx(7.0)
        assert np.isnan(field.sample([9.0], [9.0])[0])

    def test_overlapping_surfaces_report_the_upper_one(self) -> None:
        """A sea wall projects both its faces onto the same plan position. The
        one a vehicle can be on is the top."""
        lower = _quad(0.0, 0.0, 0.0, 0.0)
        upper = _quad(6.0, 6.0, 6.0, 6.0)
        field = HeightField.from_meshes([lower, upper])

        assert field.sample([5.0], [5.0])[0] == pytest.approx(6.0)

    def test_near_vertical_triangles_are_dropped(self) -> None:
        """A wall has no plan area, so its barycentric coordinates divide by
        roughly zero. Dropped at build time rather than guarded per query."""
        wall = _surface([[(0.0, 0.0, 5.0), (10.0, 0.0, 5.0), (0.0, 9.0, 5.0)]])
        field = HeightField.from_meshes([_quad(2.0, 2.0, 2.0, 2.0), wall])

        assert field.triangle_count == 2
        assert field.sample([5.0], [5.0])[0] == pytest.approx(2.0)


class TestConstruction:
    def test_a_triangle_spanning_many_cells_is_found_from_all_of_them(self) -> None:
        """One terrain triangle here can span a whole flat block. Registering it
        only in the cell holding its first corner would leave holes."""
        field = HeightField.from_meshes([_quad(3.0, 3.0, 3.0, 3.0, size=100.0)], cell_m=8.0)

        heights = field.sample(np.arange(1.0, 100.0, 7.0), np.full(15, 50.0))
        np.testing.assert_allclose(heights, 3.0)

    def test_meshes_with_no_triangles_are_an_error(self) -> None:
        empty = MeshData(
            name="empty",
            positions=np.zeros((0, 3)),
            normals=np.zeros((0, 3), np.float32),
            triangles=np.zeros((0, 3), np.uint32),
        )
        with pytest.raises(ValueError, match="no triangles"):
            HeightField.from_meshes([empty])
