"""`pipeline/signboards.py` — the Buildings Department's signboards (`P3-103`, `Q260`).

What is asserted is what a frame cannot show: that a board lands on the wall
nearest its point and turns to the street it is published as facing, that
boards sharing a wall stack rather than overlap, that a blade over the road
clears it, that every face is wound the way it is lit, and that a board's
colour is the survey's only where the survey is confident.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest
import shapely
import yaml

from pipeline.config import CONFIG_PATH, Mount
from pipeline.config_blocks.signboards import _signboards
from pipeline.railings import facing_away
from pipeline.signboards import (
    LIT_ALPHA,
    Board,
    SignboardReport,
    Walls,
    build_meshes,
    colour_of,
    facing_streets,
    palette_colour,
    photo_url,
    sized,
    snap,
    stack,
)
from pipeline.trees import Faces

NOWHERE = shapely.Polygon()
GROUND_Y = 4.0


@pytest.fixture
def spec(hong_kong):
    assert hong_kong.signboards is not None
    return hong_kong.signboards


def _wall(a: tuple[float, float], b: tuple[float, float], normal: tuple[float, float]):
    """One upright 20 m wall from `a` to `b` in plan, as two triangles."""
    (ax, az), (bx, bz) = a, b
    low, high = GROUND_Y, GROUND_Y + 20.0
    quad = np.array([[ax, low, az], [bx, low, bz], [bx, high, bz], [ax, high, az]])
    corners = np.array([quad[[0, 1, 2]], quad[[0, 2, 3]]])
    normals = np.tile(np.array([normal[0], 0.0, normal[1]]), (2, 1))
    return corners, normals


def _building() -> Walls:
    """A block whose south face runs x 0..20 at z = 10, facing +z, and whose
    east face runs z 0..10 at x = 20, facing +x."""
    south = _wall((0.0, 10.0), (20.0, 10.0), (0.0, 1.0))
    east = _wall((20.0, 0.0), (20.0, 10.0), (1.0, 0.0))
    return Walls(np.concatenate([south[0], east[0]]), np.concatenate([south[1], east[1]]))


def _ground() -> Faces:
    points = np.array(
        [[-50, GROUND_Y, -50], [150, GROUND_Y, -50], [150, GROUND_Y, 150], [-50, GROUND_Y, 150]],
        float,
    )
    return Faces(np.array([points[[0, 1, 2]], points[[0, 2, 3]]]))


def _board(
    spec, x: float, z: float, *, kind: str = "WALL SIGNBOARD", ident: str = "1", **sizes
) -> Board:
    return Board(
        ident=ident,
        kind=kind,
        mount=spec.mounts[kind],
        x=x,
        z=z,
        length_m=sizes.get("length", 4.0),
        height_m=sizes.get("height", 1.0),
        thickness_m=sizes.get("thickness", 0.2),
        facing=sizes.get("facing", ()),
        photo=None,
    )


def _place(spec, board, *, streets=None, report=None):
    return snap(spec, board, _building(), _ground(), streets or {}, report or SignboardReport())


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def test_facing_names_every_street_and_nothing_else() -> None:
    assert facing_streets("FACING RUSSELL STREET / CANAL ROAD EAST") == (
        "RUSSELL STREET",
        "CANAL ROAD EAST",
    )
    assert facing_streets("Facing Hennessy Road") == ("HENNESSY ROAD",)
    assert facing_streets("N.A.") == ()
    assert facing_streets(None) == ()


def test_the_photo_link_is_read_out_of_its_span() -> None:
    cell = (
        '<span style="text-decoration: underline;">'
        "https://storage.googleapis.com/legal-signboard-image-hosting-prod/SCU/2025/04/MW1.pdf</span>"
    )
    assert photo_url(cell).endswith("/MW1.pdf")
    assert photo_url("") is None


def test_a_missing_size_takes_its_types_median_and_a_typo_is_refused(spec) -> None:
    report = SignboardReport()
    boards = [
        _board(spec, 0, 0, ident="1", length=2.0, height=1.0),
        _board(spec, 0, 0, ident="2", length=4.0, height=3.0),
        _board(spec, 0, 0, ident="3", length=None, height=None),
        _board(spec, 0, 0, ident="4", length=spec.max_dimension_m + 1.0),
    ]
    boards[2].length_m = boards[2].height_m = boards[2].thickness_m = None
    kept = sized(spec, boards, report)
    assert [board.ident for board in kept] == ["1", "2", "3"]
    assert (kept[2].length_m, kept[2].height_m) == (3.0, 2.0)
    assert kept[2].thickness_m == spec.default_thickness_m
    assert (report.implausible, report.sized_by_median) == (1, 1)


def test_a_type_with_no_published_size_is_refused(spec) -> None:
    report = SignboardReport()
    board = _board(spec, 0, 0, kind="SIGNBOARD ON ROOF")
    board.length_m = None
    assert sized(spec, [board], report) == []
    assert report.no_size == 1


# --------------------------------------------------------------------------
# Snapping
# --------------------------------------------------------------------------


def test_a_board_lands_on_the_nearest_wall_facing_out(spec) -> None:
    item = _place(spec, _board(spec, 5.0, 9.6))
    assert item is not None
    np.testing.assert_allclose(item.foot, [5.0, 10.0])
    np.testing.assert_allclose(item.normal, [0.0, 1.0])
    assert item.ground_y == pytest.approx(GROUND_Y)


def test_a_point_with_no_wall_in_reach_is_refused(spec) -> None:
    report = SignboardReport()
    assert _place(spec, _board(spec, 60.0, 60.0), report=report) is None
    assert report.no_wall == 1


def test_a_board_turns_to_the_street_it_faces(spec) -> None:
    """At the corner the south face is nearer; the published street is east."""
    streets = {"EAST ROAD": shapely.MultiLineString([[(40.0, -20.0), (40.0, 30.0)]])}
    board = _board(spec, 19.7, 9.9, facing=("EAST ROAD",))
    report = SignboardReport()
    item = _place(spec, board, streets=streets, report=report)
    np.testing.assert_allclose(item.normal, [1.0, 0.0])
    assert (report.facing_named, report.facing_moved) == (1, 1)

    unnamed = SignboardReport()
    item = _place(spec, _board(spec, 19.7, 9.9, facing=("NOWHERE LANE",)), report=unnamed)
    np.testing.assert_allclose(item.normal, [0.0, 1.0])
    assert (unnamed.facing_unmatched, unnamed.facing_moved) == (1, 0)


# --------------------------------------------------------------------------
# Stacking and the road
# --------------------------------------------------------------------------


def test_boards_sharing_a_wall_stack_and_boards_apart_do_not(spec) -> None:
    placed = [
        _place(spec, _board(spec, 5.0, 9.8, ident="1")),
        _place(spec, _board(spec, 6.0, 9.8, ident="2")),
        _place(spec, _board(spec, 15.0, 9.8, ident="3")),
    ]
    report = SignboardReport()
    stack(spec, placed, NOWHERE, report)
    base = GROUND_Y + spec.mounts["WALL SIGNBOARD"].base_m
    assert placed[0].base_y == pytest.approx(base)
    assert placed[1].base_y == pytest.approx(placed[0].top_y + spec.stack_gap_m)
    assert placed[2].base_y == pytest.approx(base)
    assert report.stacked == 1


def test_a_blade_over_the_road_clears_it(spec) -> None:
    road = shapely.box(0.0, 11.0, 20.0, 20.0)
    over = _place(spec, _board(spec, 5.0, 9.8, kind="PROJECTING SIGNBOARD", length=2.0))
    clear = _place(
        spec, _board(spec, 15.0, 9.8, kind="PROJECTING SIGNBOARD", length=0.5, ident="2")
    )
    report = SignboardReport()
    stack(spec, [over, clear], road, report)
    assert over.base_y == pytest.approx(GROUND_Y + spec.road_base_m)
    assert clear.base_y == pytest.approx(GROUND_Y + spec.mounts["PROJECTING SIGNBOARD"].base_m)
    assert report.over_road == 1


def test_a_roof_board_stands_on_its_walls_top(spec) -> None:
    item = _place(spec, _board(spec, 5.0, 9.8, kind="SIGNBOARD ON ROOF"))
    stack(spec, [item], NOWHERE, SignboardReport())
    assert item.base_y == pytest.approx(GROUND_Y + 20.0 + spec.mounts["SIGNBOARD ON ROOF"].base_m)


# --------------------------------------------------------------------------
# Drawing and colour
# --------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["WALL SIGNBOARD", "PROJECTING SIGNBOARD", "SIGNBOARD ON ROOF"])
def test_every_face_is_wound_the_way_it_is_lit_and_only_the_faces_glow(spec, kind) -> None:
    for normal_wall in (
        _board(spec, 5.0, 9.8, kind=kind),
        _board(spec, 19.8, 5.0, kind=kind, ident="2"),
    ):
        item = _place(spec, normal_wall)
        stack(spec, [item], NOWHERE, SignboardReport())
        item.colour = (200, 16, 46)
        (mesh,) = build_meshes(spec, [item])
        assert facing_away(mesh) == 0
        assert len(mesh.triangles) == 12
        lit = mesh.colours[mesh.triangles[:, 0], 3] == LIT_ALPHA
        assert lit.sum() == 4
        # The lit faces are the board's two widest.
        areas = np.linalg.norm(mesh.triangle_cross(), axis=1)
        assert areas[lit].min() >= areas[~lit].max() - 1e-9


def test_the_palette_is_picked_by_id_and_holds(spec) -> None:
    assert palette_colour(spec, "123") == palette_colour(spec, "123")
    picks = {palette_colour(spec, str(ident)) for ident in range(200)}
    assert picks <= set(spec.palette)
    assert len(picks) == len(spec.palette)


def test_a_surveyed_colour_is_used_only_where_the_survey_is_confident(spec) -> None:
    survey = {
        "boards": {
            "1": {"rgb": "#e86a10", "share": spec.survey_min_share},
            "2": {"rgb": "#e86a10", "share": spec.survey_min_share / 2.0},
        }
    }
    report = SignboardReport()
    surveyed = colour_of(spec, "1", survey, report)
    assert surveyed != palette_colour(spec, "1")
    assert colour_of(spec, "2", survey, report) == palette_colour(spec, "2")
    assert colour_of(spec, "3", survey, report) == palette_colour(spec, "3")
    assert colour_of(spec, "4", None, report) == palette_colour(spec, "4")
    assert (report.colour_surveyed, report.colour_weak, report.colour_unread) == (1, 1, 1)
    assert report.colour_palette == 3


def test_a_blown_out_photo_is_clamped_into_the_lightness_bounds(spec) -> None:
    from pipeline.colour import srgb_to_lab

    report = SignboardReport()
    white = colour_of(spec, "1", {"boards": {"1": {"rgb": "#ffffff", "share": 1.0}}}, report)
    black = colour_of(spec, "2", {"boards": {"2": {"rgb": "#000000", "share": 1.0}}}, report)
    low, high = spec.survey_lightness
    assert srgb_to_lab(np.array([white], float))[0, 0] == pytest.approx(high, abs=0.5)
    assert srgb_to_lab(np.array([black], float))[0, 0] == pytest.approx(low, abs=0.5)


# --------------------------------------------------------------------------
# The block
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b.update(mounts={}), "mounts"),
        (lambda b: b["mounts"].update({"X": {"mount": "floating", "base_m": 1.0}}), "floating"),
        (lambda b: b["mounts"].update({"X": {"mount": "wall", "base_m": -1.0}}), "base_m"),
        (lambda b: b.update(palette=[]), "palette"),
        (lambda b: b.update(palette=["red"]), "palette"),
        (lambda b: b.update(survey_lightness=[90.0, 12.0]), "survey_lightness"),
        (lambda b: b.update(frame_darken=1.5), "frame_darken"),
        (lambda b: b.update(max_snap_m=0.0), "max_snap_m"),
        (lambda b: b["fields"].pop("facing"), "facing"),
    ],
)
def test_block_refuses(mutate, message: str) -> None:
    document = yaml.safe_load(CONFIG_PATH.read_text())
    body = copy.deepcopy(document["signboards"])
    mutate(body)
    with pytest.raises((ValueError, KeyError), match=message):
        _signboards(body, "signboards")


def test_every_published_type_in_the_region_has_a_mount(spec) -> None:
    for kind in (
        "WALL SIGNBOARD",
        "PROJECTING SIGNBOARD",
        "SIGNBOARD ON ROOF",
        "OUTDOOR SIGNBOARD FIXED ON-GRADE",
        "OUTDOOR SIGNBOARD WITH A SPREAD FOOTING",
        "SIGNBOARD ON OR HUNG UNDERNEATH BALCONY OR CANOPY",
    ):
        assert isinstance(spec.mounts[kind], Mount)
