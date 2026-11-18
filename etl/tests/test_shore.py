"""`pipeline/shore.py` — the sea's edge cut into the ground (`P3-101`, `Q250`).

A 20 m square of flat ground at 4 m, the sea over its east half. What is
asserted is what a frame cannot show: that the cut loses no ground and opens no
crack, that a built shore is a face and a natural one is not, and that the
ground on both sides is still ground.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from shapely.geometry import LineString, Polygon, box

from pipeline.basemap import BASEMAP_NAME, BASEMAP_SCHEMA
from pipeline.gltf import MeshData
from pipeline.mesh import weld
from pipeline.shore import Shore, cut_sea, shoreline_of_bundle
from tests.helpers import soup

GROUND_M = 4.0
SEABED_M = -3.0
PAVING = (129, 123, 111, 255)
QUAY = (132, 129, 123)
# The sea east of x = 10, past the ground on three sides.
SEA = box(10.0, -5.0, 30.0, 25.0)
LINE = LineString([(10.0, -5.0), (10.0, 25.0)])


def _ground(step: float = 5.0, height=lambda x, z: GROUND_M) -> MeshData:
    """A 20 m square in `step` cells, two triangles each, vertices shared."""
    faces = []
    for x in np.arange(0.0, 20.0, step):
        for z in np.arange(0.0, 20.0, step):
            a, b, c, d = (x, z), (x + step, z), (x + step, z + step), (x, z + step)
            for ring in ((a, c, b), (a, d, c)):
                faces.append([(px, height(px, pz), pz) for px, pz in ring])
    return weld(soup(faces, name="ground", colour=PAVING))


def _shore(hard=(LINE,), soft=()) -> Shore:
    return Shore(SEA, list(hard), list(soft), SEABED_M, QUAY)


def _plan_area(mesh: MeshData, keep: np.ndarray | None = None) -> float:
    corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
    if keep is not None:
        corners = corners[keep]
    ab, ac = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    return float(np.abs(ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]).sum() * 0.5)


def _cross(mesh: MeshData) -> np.ndarray:
    corners = mesh.positions[mesh.triangles]
    return np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])


def _is_wall(mesh: MeshData) -> np.ndarray:
    cross = _cross(mesh)
    return np.abs(cross[:, 1]) < 1e-9


def test_no_sea_is_the_same_mesh() -> None:
    mesh = _ground()
    same, report = cut_sea(mesh, Shore(Polygon(), [], [], SEABED_M, QUAY))
    assert same is mesh and report.cut == 0


@pytest.mark.parametrize("step", [5.0, 4.0, 20.0])
def test_a_built_shore_is_a_face_from_the_ground_to_the_seabed(step: float) -> None:
    """At 5 m the line runs along the grid's own edges, at 4 m through its
    cells, and at 20 m through the one cell: the cut is the same line."""
    mesh = _ground(step)
    cut, report = cut_sea(mesh, _shore())
    wall = _is_wall(cut)
    flat = ~wall

    # No ground lost, none doubled.
    assert _plan_area(cut, flat) == pytest.approx(400.0)
    centre = cut.positions[cut.triangles][:, :, [0, 2]].mean(axis=1)
    heights = cut.positions[cut.triangles][:, :, 1]
    land, sea = flat & (centre[:, 0] < 10.0), flat & (centre[:, 0] > 10.0)
    assert (heights[land] == GROUND_M).all()
    assert (heights[sea] == SEABED_M).all()

    # The face: on the line, its full height, as long as the ground is wide.
    faces = cut.positions[cut.triangles][wall]
    assert faces[:, :, 0] == pytest.approx(10.0)
    assert faces[:, :, 1].min() == SEABED_M and faces[:, :, 1].max() == GROUND_M
    assert report.quay_m == pytest.approx(20.0) == pytest.approx(report.edge_m)
    twice = np.linalg.norm(_cross(cut)[wall], axis=1).sum()
    assert twice * 0.5 == pytest.approx(20.0 * (GROUND_M - SEABED_M))
    assert report.wall_triangles == int(wall.sum())
    assert report.sunk == int((cut.positions[:, 1] == SEABED_M).sum()) > 0


def test_a_face_looks_out_to_sea_and_is_wound_as_the_ground_is() -> None:
    cut, _ = cut_sea(_ground(4.0), _shore())
    wall = _is_wall(cut)
    cross = _cross(cut)
    # The ground faces up; its right-handed normal says which way that is wound.
    wound = np.sign(cross[~wall][:, 1])
    assert (wound == wound[0]).all()
    # The sea is east: every face is wound the same way about +x.
    assert (np.sign(cross[wall][:, 0]) == wound[0]).all()
    normals = cut.normals[cut.triangles][wall]
    assert normals.reshape(-1, 3) == pytest.approx(
        np.tile([1.0, 0.0, 0.0], (int(wall.sum()) * 3, 1))
    )


def test_the_face_wears_the_quay_and_the_ground_stays_ground() -> None:
    """`trees.tile_corners` knows the ground by its colour: a cut point that
    blended two would stop being ground under every layer that stands on it."""
    cut, _ = cut_sea(_ground(4.0), _shore())
    wall = _is_wall(cut)
    colours = cut.colours[cut.triangles]
    assert (colours[wall][:, :, :3] == QUAY).all()
    assert (colours[~wall] == PAVING).all()


def test_a_natural_shore_slopes_from_the_line_and_has_no_face() -> None:
    cut, report = cut_sea(_ground(4.0), _shore(hard=(), soft=(LINE,)))
    assert not _is_wall(cut).any()
    assert (report.wall_triangles, report.quay_m) == (0, 0.0)
    assert report.edge_m == pytest.approx(20.0)
    assert _plan_area(cut) == pytest.approx(400.0)
    x, y = cut.positions[:, 0], cut.positions[:, 1]
    # The land and the line itself keep the terrain; the sea past it is sunk.
    assert (y[x <= 10.0 + 1e-9] == GROUND_M).all()
    assert (y[x > 10.0 + 1e-9] == SEABED_M).all()


def test_built_and_natural_meet_without_a_crack() -> None:
    """The nearer line decides each point, by position: south of z = 10 the
    shore is built, north of it natural, and where they meet every triangle
    that shares a point on the sea's edge agrees on its height."""
    hard = LineString([(10.0, -5.0), (10.0, 10.0)])
    soft = LineString([(10.0, 10.0), (10.0, 25.0)])
    cut, report = cut_sea(_ground(4.0), _shore(hard=(hard,), soft=(soft,)))
    assert report.quay_m == pytest.approx(10.0, abs=2.0)
    assert _plan_area(cut, ~_is_wall(cut)) == pytest.approx(400.0)

    # Every edge of the cut mesh that lies on the sea's edge is shared: by a
    # land piece and a sea piece where the shore is natural, by each of them
    # and a face where it is built.
    corners = cut.positions[cut.triangles]
    edges: dict[tuple, int] = {}
    for triangle in corners:
        for first, second in ((0, 1), (1, 2), (2, 0)):
            pair = (triangle[first], triangle[second])
            # ...but for the two at the ground's own rim, z = 0 and z = 20.
            if pair[0][2] == pair[1][2] and pair[0][2] in (0.0, 20.0):
                continue
            if all(abs(point[0] - 10.0) < 1e-9 for point in pair):
                key = tuple(sorted(tuple(np.round(point, 6)) for point in pair))
                edges[key] = edges.get(key, 0) + 1
    assert edges and all(count == 2 for count in edges.values())


def test_the_cut_follows_sloping_ground() -> None:
    """A face's top is the terrain at the line, wherever the line crosses a
    triangle: 4 m at the south end, 6 m at the north."""
    cut, _ = cut_sea(_ground(4.0, lambda x, z: GROUND_M + 0.1 * z), _shore())
    faces = cut.positions[cut.triangles][_is_wall(cut)].reshape(-1, 3)
    tops = faces[faces[:, 1] > SEABED_M]
    assert tops[:, 1] == pytest.approx(GROUND_M + 0.1 * tops[:, 2])


def test_the_bundles_shoreline_is_read_back_as_lines(tmp_path) -> None:
    (tmp_path / BASEMAP_NAME).write_text(
        json.dumps(
            {
                "schema_version": BASEMAP_SCHEMA,
                "shoreline": {
                    "hard": [[0.0, 1.0, 5.0, 1.0, 5.0, 9.0]],
                    "soft": [[5.0, 9.0, 0.0, 9.0]],
                },
            }
        )
    )
    hard, soft = shoreline_of_bundle(tmp_path, "wan_chai")
    assert [line.length for line in hard] == [pytest.approx(13.0)]
    assert [list(line.coords) for line in soft] == [[(5.0, 9.0), (0.0, 9.0)]]
