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
from pipeline.signboard_text import build_atlas, characters, ink, pick_name
from pipeline.signboards import (
    LIT_ALPHA,
    Board,
    SignboardReport,
    Walls,
    build_meshes,
    colour_of,
    facing_streets,
    name_boards,
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
        (mesh,), lettering, screens = build_meshes(spec, [item])
        assert lettering == [] and screens == []
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
        (lambda b: b["text"]["trades"]["bar"].update(mounts=["floating"]), "floating"),
        (lambda b: b["text"]["streets"].update({"X ROAD": {"bakery": 2.0}}), "bakery"),
        (lambda b: b["text"].update(name_chars=0), "name_chars"),
        (lambda b: b["text"].update(fill=1.5), "fill"),
        (lambda b: b.update(screens="2297"), "screens"),
        (lambda b: b["text"].update(lettered="false"), "lettered"),
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


# --------------------------------------------------------------------------
# The lettering (step 2)
# --------------------------------------------------------------------------


def test_every_character_the_block_can_letter_is_in_its_font(spec) -> None:
    import sys

    from pipeline.config import CONFIG_PATH as config_path

    root = config_path.parents[2]
    sys.path.insert(0, str(root / "tools"))
    from font_coverage import read_cmap

    cmap = read_cmap(root / spec.text.font)
    missing = [c for c in characters(spec.text) if ord(c) not in cmap]
    assert not missing, f"{spec.text.font} lacks {''.join(missing)}: re-run tools/make_fonts.py"


def test_a_name_is_generic_seeded_by_id_and_never_empty(spec) -> None:
    text = spec.text
    names = {pick_name(text, str(ident), "wall", (), False)[0] for ident in range(300)}
    assert "" not in names and len(names) > 250
    assert pick_name(text, "77", "wall", (), False) == pick_name(text, "77", "wall", (), False)
    for name in names:
        suffix_ok = any(name.endswith(s) for t in text.trades.values() for s in t.suffixes)
        assert suffix_ok and all(c in text.prefixes for c in name[: text.name_chars])


def test_a_licence_nearby_makes_a_restaurant_and_a_trade_keeps_to_its_mount(spec) -> None:
    text = spec.text

    def food_share(near: bool) -> float:
        trades = [pick_name(text, str(i), "wall", (), near)[1] for i in range(600)]
        return sum(text.trades[t].food for t in trades) / len(trades)

    assert food_share(True) > 0.8 > 0.3 > food_share(False)
    roof = {pick_name(text, str(i), "roof", (), False)[1] for i in range(300)}
    wall = {pick_name(text, str(i), "wall", (), False)[1] for i in range(600)}
    assert "pawn" not in roof | wall and "group" not in wall and "group" in roof


def test_a_street_weights_its_own_trade(spec) -> None:
    text = spec.text
    street = next(iter(text.streets))
    trade = next(iter(text.streets[street]))
    on = [pick_name(text, str(i), "wall", (street,), True)[1] for i in range(400)]
    off = [pick_name(text, str(i), "wall", (), True)[1] for i in range(400)]
    assert on.count(trade) > 3 * max(1, off.count(trade))


def test_the_ink_stands_out_from_its_board(spec) -> None:
    assert ink(spec.text, (20, 20, 20)) != (26, 26, 26)
    assert ink(spec.text, (244, 241, 232)) == (26, 26, 26)


@pytest.mark.parametrize(
    ("kind", "sizes", "faces"),
    [
        ("WALL SIGNBOARD", {"length": 6.0, "height": 1.0}, 1),
        ("PROJECTING SIGNBOARD", {"length": 1.0, "height": 4.0}, 2),
        ("SIGNBOARD ON ROOF", {"length": 8.0, "height": 2.0}, 1),
    ],
)
def test_the_lettering_faces_out_of_its_board_and_stays_on_it(spec, kind, sizes, faces) -> None:
    item = _place(spec, _board(spec, 5.0, 9.8, kind=kind, **sizes))
    stack(spec, [item], NOWHERE, SignboardReport())
    item.colour = (200, 16, 46)
    item.name = "金興茶餐廳"
    atlas = build_atlas(spec.text, CONFIG_PATH.parents[2])
    (board,), (lettering,), _ = build_meshes(spec, [item], atlas)
    assert facing_away(lettering) == 0
    assert len(lettering.triangles) == 2 * len(item.name) * faces
    assert (lettering.colours[:, 3] == LIT_ALPHA).all()
    # Every glyph inside the board's outline, off its face.
    low, high = board.positions.min(axis=0), board.positions.max(axis=0)
    margin = spec.text.lift_m + 1e-4
    assert (lettering.positions >= low - margin).all()
    assert (lettering.positions <= high + margin).all()
    # A blade is lettered top to bottom; the wall and roof boards across.
    spread = np.ptp(lettering.positions, axis=0)
    assert (spread[1] > max(spread[0], spread[2])) == (kind == "PROJECTING SIGNBOARD")
    assert lettering.texture is not None and lettering.texture.uri == "signboards_text.png"


# --------------------------------------------------------------------------
# The screens (step 3)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("kind", "faces"), [("WALL SIGNBOARD", 1), ("PROJECTING SIGNBOARD", 2)])
def test_an_authored_screen_is_drawn_as_a_screen_and_not_lettered(spec, kind, faces) -> None:
    from dataclasses import replace

    screened = replace(spec, screens=("9",))
    item = _place(screened, _board(screened, 5.0, 9.8, kind=kind, ident="9", length=6.0))
    stack(screened, [item], NOWHERE, SignboardReport())
    item.name = "金興茶餐廳"
    atlas = build_atlas(spec.text, CONFIG_PATH.parents[2])
    _, lettering, (screen,) = build_meshes(screened, [item], atlas)
    assert lettering == []
    assert facing_away(screen) == 0 and len(screen.triangles) == 2 * faces
    assert (screen.colours[:, 3] == LIT_ALPHA).all()
    # UVs in metres: the face's own width and height.
    assert np.ptp(screen.uvs, axis=0) == pytest.approx([6.0, 1.0])
    assert screen.texture is None and screen.material == "signboards_screen"

    report = SignboardReport()
    name_boards(screened.text, screened.screens, [item], None, report)
    assert report.lettered == 0


def test_the_screens_are_the_two_named_boards(spec) -> None:
    assert set(spec.screens) == {"2297", "1934"}


def test_the_shipped_boards_are_colour_only(spec) -> None:
    # The user's call (2026-11-20): `text.lettered` is off, and the block
    # stays whole so it switches back on.
    assert spec.text is not None and not spec.text.lettered
