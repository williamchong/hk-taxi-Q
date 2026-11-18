"""`pipeline/paths.py` — the topographic map's pedestrian lines (`P3-101`, `Q250`).

What is asserted is what a frame cannot show: that no ribbon lies on the drawn
road, in the sea or over bare air, that it follows the ground it is laid on,
and that it faces up.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest
import shapely
import yaml

from pipeline.config import CONFIG_PATH, _materials, _MaterialTable
from pipeline.config_blocks.paths import _paths
from pipeline.gltf import is_collider
from pipeline.paths import PATHS_MATERIAL, PathReport, build_paths
from pipeline.trees import Faces

NOWHERE = shapely.Polygon()
GROUND_M = 4.0


def _slab(height_at=lambda x, z: GROUND_M, x1: float = 100.0) -> Faces:
    """A 100 m deep strip of ground out to `x1`, at a height read per corner."""
    corners = [(0.0, 0.0), (x1, 0.0), (x1, 100.0), (0.0, 100.0)]
    points = np.array([[x, height_at(x, z), z] for x, z in corners])
    return Faces(np.array([points[[0, 1, 2]], points[[0, 2, 3]]]))


def _ridge() -> Faces:
    """Flat to x = 50, then climbing 1 m in 10: a crease across a line along x."""
    flat = _slab(x1=50.0).corners
    climb = flat + np.array([50.0, 0.0, 0.0])
    climb[..., 1] = GROUND_M + (climb[..., 0] - 50.0) * 0.1
    return Faces(np.concatenate([flat, climb]))


def _line(*points: tuple[float, float], code: str = "PA"):
    return (code, shapely.LineString(points))


def _build(spec, lines, *, road=NOWHERE, sea=NOWHERE, ground=None):
    report = PathReport()
    return build_paths(spec, lines, road, sea, ground or _slab(), report), report


def _positions(meshes) -> np.ndarray:
    return np.concatenate([mesh.positions for mesh in meshes])


@pytest.fixture
def spec(hong_kong):
    assert hong_kong.paths is not None
    return hong_kong.paths


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b.update(widths_m={}), "widths_m"),
        (lambda b: b.update(widths_m={"PA": 0.0}), "PA"),
        (lambda b: b.update(lift_m=-0.1), "lift_m"),
        (lambda b: b.update(sag_m=b["lift_m"]), "sag_m"),
        (lambda b: b.update(step_m=0.0), "step_m"),
        (lambda b: b.update(max_grade_pct=0.0), "max_grade_pct"),
        (lambda b: b.update(material="chalk"), "material"),
        (lambda b: b.pop("layer"), "layer"),
        (lambda b: b["fields"].pop("type"), "type"),
    ],
)
def test_block_refuses(mutate, message: str) -> None:
    document = yaml.safe_load(CONFIG_PATH.read_text())
    table = _MaterialTable(_materials(document["materials"], "materials"))
    body = copy.deepcopy(document["paths"])
    mutate(body)
    with pytest.raises((ValueError, KeyError), match=message):
        _paths(body, "paths", table)


def test_a_line_is_a_ribbon_of_its_codes_width_lifted_off_the_ground(spec) -> None:
    meshes, report = _build(spec, [_line((10.0, 10.0), (40.0, 10.0))])
    assert (report.ribbons, report.drawn_m) == (1, pytest.approx(30.0))
    assert report.drawn_m_by_code == {"PA": pytest.approx(30.0)}
    (mesh,) = meshes
    assert mesh.material == PATHS_MATERIAL and not is_collider(mesh)
    assert (mesh.colours[:, :3] == np.array(spec.material.colour)).all()
    across = mesh.positions[:, 2]
    assert across.max() - across.min() == pytest.approx(spec.widths_m["PA"])
    assert mesh.positions[:, 1] == pytest.approx(GROUND_M + spec.lift_m)
    # Flat ground asks for no station between the ends: one quad.
    assert len(mesh.triangles) == 2 and report.stations_kept == 2 < report.stations


def test_a_footpath_is_drawn_at_its_own_width(spec) -> None:
    meshes, _ = _build(spec, [_line((10.0, 10.0), (40.0, 10.0), code="FP")])
    across = _positions(meshes)[:, 2]
    assert across.max() - across.min() == pytest.approx(spec.widths_m["FP"])
    assert spec.widths_m["FP"] > spec.widths_m["PA"]


def test_every_ribbon_faces_up(spec) -> None:
    """A bend tighter than the ribbon is wide folds its inner edge, and the
    quad there is a bow-tie: both halves still face up."""
    hairpin = _line((40.0, 50.0), (41.0, 50.2), (41.2, 50.4), (41.0, 50.6), (40.0, 50.8), code="FP")
    lines = [
        _line((10.0, 10.0), (40.0, 10.0)),
        _line((40.0, 30.0), (10.0, 30.0), (10.0, 60.0)),
        hairpin,
    ]
    meshes, _ = _build(spec, lines)
    for mesh in meshes:
        corners = mesh.positions[mesh.triangles]
        normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        assert (normal[:, 1] > 0.0).all()


def test_a_ribbon_follows_a_crease_in_the_ground(spec) -> None:
    meshes, report = _build(spec, [_line((10.0, 10.0), (90.0, 10.0))], ground=_ridge())
    positions = _positions(meshes)
    # A station is kept at the crease, and nowhere on the two flat runs.
    assert report.stations_kept == 3
    at_crease = np.isclose(positions[:, 0], 50.0)
    assert at_crease.any()
    assert positions[at_crease, 1] == pytest.approx(GROUND_M + spec.lift_m)
    far = np.isclose(positions[:, 0], 90.0)
    assert positions[far, 1] == pytest.approx(GROUND_M + 4.0 + spec.lift_m)


def test_a_line_is_broken_where_the_ground_is_too_steep_to_lie_on(spec) -> None:
    """A retaining wall the terrain smears into a slope: flat, a 10 m bank
    steeper than the bar, flat again. The bank is not drawn, along a line that
    climbs it or under one that runs across it."""
    grade = 2.0 * spec.max_grade_pct / 100.0

    def banked(x: float, z: float) -> float:
        return GROUND_M + grade * float(np.clip(x - 40.0, 0.0, 10.0))

    strips = [(0.0, 40.0), (40.0, 50.0), (50.0, 100.0)]
    corners = []
    for x0, x1 in strips:
        ring = [(x0, 0.0), (x1, 0.0), (x1, 100.0), (x0, 100.0)]
        points = np.array([[x, banked(x, z), z] for x, z in ring])
        corners += [points[[0, 1, 2]], points[[0, 2, 3]]]
    ground = Faces(np.array(corners))

    meshes, report = _build(spec, [_line((10.0, 10.0), (90.0, 10.0))], ground=ground)
    assert report.ribbons == 2
    assert report.too_steep_m == pytest.approx(10.0, abs=2.0 * spec.step_m)
    along = _positions(meshes)[:, 0]
    assert not ((along > 41.0) & (along < 49.0)).any()

    # Across the fall: the ribbon's two edges stand at different heights.
    meshes, report = _build(spec, [_line((45.0, 10.0), (45.0, 90.0), code="FP")], ground=ground)
    assert meshes == [] and report.too_steep_m == pytest.approx(80.0)


def test_a_line_is_cut_back_off_the_road(spec) -> None:
    road = shapely.box(20.0, 0.0, 30.0, 100.0)
    meshes, report = _build(spec, [_line((10.0, 10.0), (40.0, 10.0))], road=road)
    cut = 10.0 + 2.0 * spec.kerb_clear_m
    assert report.on_road_m == pytest.approx(cut)
    assert (report.ribbons, report.drawn_m) == (2, pytest.approx(30.0 - cut))
    along = _positions(meshes)[:, 0]
    assert not (
        (along > 20.0 - spec.kerb_clear_m + 1e-6) & (along < 30.0 + spec.kerb_clear_m - 1e-6)
    ).any()


def test_a_line_is_cut_out_of_the_sea(spec) -> None:
    sea = shapely.box(30.0, 0.0, 100.0, 100.0)
    meshes, report = _build(spec, [_line((10.0, 10.0), (40.0, 10.0))], sea=sea)
    assert report.in_sea_m == pytest.approx(10.0)
    assert _positions(meshes)[:, 0].max() == pytest.approx(30.0)


def test_a_line_stops_where_the_tiles_draw_no_ground(spec) -> None:
    meshes, report = _build(spec, [_line((10.0, 10.0), (80.0, 10.0))], ground=_slab(x1=50.0))
    assert report.ribbons == 1
    assert report.no_ground_m == pytest.approx(30.0, abs=spec.step_m)
    assert _positions(meshes)[:, 0].max() <= 50.0 + 1e-6


def test_a_stub_under_the_bar_is_not_drawn(spec) -> None:
    short = 0.5 * spec.min_length_m
    meshes, report = _build(spec, [_line((10.0, 10.0), (10.0 + short, 10.0))])
    assert meshes == [] and report.triangles == 0
    assert report.too_short_m == pytest.approx(short)


def test_ribbons_are_cut_into_plan_cells(spec) -> None:
    assert spec.cell_m > 0.0
    wide = _slab(x1=2.0 * spec.cell_m + 100.0)
    lines = [
        _line((10.0, 10.0), (40.0, 10.0)),
        _line((spec.cell_m + 10.0, 10.0), (spec.cell_m + 40.0, 10.0)),
    ]
    meshes, report = _build(spec, lines, ground=wide)
    assert report.cells == len(meshes) == 2
    assert len({mesh.name for mesh in meshes}) == 2
    assert report.triangles == sum(len(mesh.triangles) for mesh in meshes)
