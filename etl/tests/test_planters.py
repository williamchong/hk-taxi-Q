"""`pipeline/planters.py` — HyD's roadside planters (`P3-98`, `Q247`).

What is asserted is what a frame cannot show: that no planter stands on the
drawn road or through a building, that the collider is the walls and nothing
of the planting, and that a wall follows the ground under it.
"""

from __future__ import annotations

import copy
from dataclasses import replace

import numpy as np
import pytest
import shapely
import yaml

from pipeline.config import CONFIG_PATH, _materials, _MaterialTable
from pipeline.config_blocks.planters import _planters
from pipeline.gltf import is_collider
from pipeline.planters import PLANTERS_MATERIAL, PlanterReport, Walls, build_planters
from pipeline.trees import Faces

FRAME = shapely.box(0.0, 0.0, 100.0, 100.0)
NO_ROAD = shapely.Polygon()
GROUND_M = 4.0


def _slab(height_at=lambda x, z: GROUND_M) -> Faces:
    """The frame as two ground triangles, at a height read per corner."""
    corners = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    points = np.array([[x, height_at(x, z), z] for x, z in corners])
    return Faces(np.array([points[[0, 1, 2]], points[[0, 2, 3]]]))


def _no_walls() -> Walls:
    return Walls(np.zeros((0, 3, 3)))


def _box_walls(x0: float, z0: float, x1: float, z1: float, low: float, high: float) -> Walls:
    """A building's four walls as upright triangles."""
    plan = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    triangles = []
    for (ax, az), (bx, bz) in zip(plan, plan[1:] + plan[:1], strict=True):
        a, b = [ax, low, az], [bx, low, bz]
        c, d = [bx, high, bz], [ax, high, az]
        triangles += [[a, b, c], [a, c, d]]
    return Walls(np.array(triangles, dtype=np.float64))


def _ring(x0: float, z0: float, x1: float, z1: float) -> shapely.MultiLineString:
    return shapely.MultiLineString([[(x0, z0), (x1, z0), (x1, z1)], [(x1, z1), (x0, z1), (x0, z0)]])


def _build(spec, features, *, road=NO_ROAD, ground=None, standing=None):
    report = PlanterReport()
    meshes = build_planters(
        spec, features, FRAME, road, ground or _slab(), standing or _no_walls(), report
    )
    return meshes, report


def _greens(mesh, spec) -> np.ndarray:
    """Which vertices wear the planting rather than the wall."""
    return ~(mesh.colours[:, :3] == np.array(spec.wall_material.colour)).all(axis=1)


@pytest.fixture
def spec(hong_kong):
    assert hong_kong.planters is not None
    return hong_kong.planters


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b.update(wall_height_m=0.0), "wall_height_m"),
        (lambda b: b.update(shrub_min_m=2.0), "shrub_min_m"),
        (lambda b: b.update(max_on_road=1.0), "max_on_road"),
        (lambda b: b.update(side_darken=-0.1), "side_darken"),
        (lambda b: b.update(kerb_clear_m=-1.0), "kerb_clear_m"),
        (lambda b: b.update(shrub_material="moss"), "shrub_material"),
        (lambda b: b.pop("layer"), "layer"),
    ],
)
def test_block_refuses(mutate, message: str) -> None:
    document = yaml.safe_load(CONFIG_PATH.read_text())
    table = _MaterialTable(_materials(document["materials"], "materials"))
    body = copy.deepcopy(document["planters"])
    mutate(body)
    with pytest.raises((ValueError, KeyError), match=message):
        _planters(body, "planters", table)


def test_a_closed_ring_is_a_planted_bed_and_its_collider_is_the_wall(spec) -> None:
    meshes, report = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0)])
    mesh, collider = meshes
    assert (report.closed, report.rings, report.beds, report.walls) == (1, 1, 1, 0)
    assert report.bed_area_m2 == pytest.approx(40.0)
    assert report.clumps > 0 and report.facing_away == 0
    assert mesh.material == PLANTERS_MATERIAL and not is_collider(mesh)

    wall_top = GROUND_M + spec.wall_height_m
    assert mesh.positions[:, 1].min() == pytest.approx(GROUND_M - spec.sink_m)
    planted = _greens(mesh, spec)
    assert planted.any()
    # Every clump tops out inside the authored band, and stands inside the wall.
    top = mesh.positions[planted][:, 1].max()
    assert wall_top + spec.shrub_min_m <= top <= wall_top + spec.shrub_max_m
    inside = mesh.positions[planted][:, [0, 2]]
    assert inside.min() >= 10.0 + spec.shrub_inset_m - 1e-6
    assert mesh.positions[~planted][:, 1].max() == pytest.approx(wall_top)

    # The collider is the walls alone: a car hits the planter, never the hedge.
    assert is_collider(collider) and collider.colours is None
    assert collider.positions[:, 1].max() == pytest.approx(wall_top)


def test_an_open_wall_stands_bare(spec) -> None:
    line = shapely.MultiLineString([[(10.0, 10.0), (30.0, 10.0)]])
    meshes, report = _build(spec, [line])
    assert (report.open, report.walls, report.beds, report.clumps) == (1, 1, 0, 0)
    mesh = meshes[0]
    assert not _greens(mesh, spec).any()
    across = mesh.positions[:, 2]
    assert across.max() - across.min() == pytest.approx(spec.wall_width_m)


def test_a_bed_is_cut_back_off_the_road(spec) -> None:
    road = shapely.box(0.0, 0.0, 100.0, 11.0)
    meshes, report = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0)], road=road)
    assert report.beds == 1 and report.in_carriageway == 0
    assert report.road_cut_m2 == pytest.approx(10.0 * (1.0 + spec.kerb_clear_m))
    for mesh in meshes:
        assert mesh.positions[:, 2].min() >= 11.0 + spec.kerb_clear_m - 1e-6


def test_a_ring_that_is_mostly_road_is_refused_whole(spec) -> None:
    road = shapely.box(0.0, 0.0, 100.0, 13.0)
    meshes, report = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0)], road=road)
    assert meshes == []
    assert (report.rings, report.in_carriageway, report.beds) == (1, 1, 0)


def test_a_bed_does_not_plant_the_building_inside_it(spec) -> None:
    tower = _box_walls(14.0, 11.0, 16.0, 13.0, GROUND_M, GROUND_M + 20.0)
    meshes, report = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0)], standing=tower)
    assert report.building_cut_m2 >= 4.0
    footprint = shapely.box(14.0, 11.0, 16.0, 13.0).buffer(-0.01)
    for mesh in meshes:
        centres = mesh.positions[mesh.triangles][:, :, [0, 2]].mean(axis=1)
        assert not any(footprint.contains(shapely.Point(centre)) for centre in centres)


def test_a_wall_overhead_cuts_nothing(spec) -> None:
    # A footbridge's parapet: upright, but it never comes down to the planter.
    parapet = _box_walls(14.0, 11.0, 16.0, 13.0, GROUND_M + 5.0, GROUND_M + 6.0)
    _, report = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0)], standing=parapet)
    assert report.building_cut_m2 == 0.0


def test_a_ring_over_no_ground_is_refused(spec) -> None:
    meshes, report = _build(spec, [_ring(150.0, 10.0, 160.0, 14.0)], ground=_slab())
    assert meshes == []
    assert (report.no_ground, report.beds) == (1, 0)


def test_a_wall_follows_the_ground_under_it(spec) -> None:
    ground = _slab(lambda x, z: GROUND_M + 0.05 * x)
    meshes, report = _build(spec, [_ring(10.0, 10.0, 50.0, 14.0)], ground=ground)
    collider = meshes[1]
    # Level, the wall would stand 2.45 m at its low end; following, 0.45 m everywhere.
    over = collider.positions[:, 1] - (GROUND_M + 0.05 * collider.positions[:, 0])
    assert over.max() == pytest.approx(spec.wall_height_m, abs=0.02)
    assert report.max_ground_fall_m == pytest.approx(2.0, abs=0.01)


def test_a_bed_is_drawn_the_same_every_build(spec) -> None:
    first, _ = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0)])
    again, _ = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0)])
    assert np.array_equal(first[0].positions, again[0].positions)
    assert np.array_equal(first[0].colours, again[0].colours)


def test_a_wall_round_a_hole_stands_on_its_own_ground(spec) -> None:
    # A wide bed on a slope with a tower in its middle: the wall round the
    # tower is 20 m from any outer corner and must not take that corner's height.
    ground = _slab(lambda x, z: GROUND_M + 0.05 * x)
    tower = _box_walls(48.0, 48.0, 52.0, 52.0, GROUND_M, GROUND_M + 30.0)
    meshes, report = _build(spec, [_ring(10.0, 30.0, 90.0, 70.0)], ground=ground, standing=tower)
    assert report.building_cut_m2 >= 16.0
    collider = meshes[1]
    near = (np.abs(collider.positions[:, 0] - 50.0) < 3.0) & (
        np.abs(collider.positions[:, 2] - 50.0) < 3.0
    )
    assert near.any()
    over = collider.positions[near][:, 1] - (GROUND_M + 0.05 * collider.positions[near][:, 0])
    assert over.max() == pytest.approx(spec.wall_height_m, abs=0.02)
    assert over.min() == pytest.approx(-spec.sink_m, abs=0.02)


def test_a_refused_rings_cuts_are_not_counted(spec) -> None:
    road = shapely.box(0.0, 0.0, 100.0, 11.0)
    _, report = _build(spec, [_ring(150.0, 10.0, 160.0, 14.0)], road=road)
    assert report.no_ground == 1 and report.road_cut_m2 == 0.0


def test_beds_in_two_cells_are_two_meshes_and_one_collider(spec) -> None:
    spec = replace(spec, cell_m=50.0)
    meshes, report = _build(spec, [_ring(10.0, 10.0, 20.0, 14.0), _ring(70.0, 10.0, 80.0, 14.0)])
    *drawn, collider = meshes
    assert [mesh.name for mesh in drawn] == ["planters_c0_r0", "planters_c1_r0"]
    assert is_collider(collider) and not any(is_collider(mesh) for mesh in drawn)
    assert report.beds == 2
    assert report.triangles == sum(len(mesh.triangles) for mesh in drawn)
