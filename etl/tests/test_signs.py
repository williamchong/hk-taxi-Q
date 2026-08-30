"""The traffic-sign stage (`P3-16`).

Weighted almost entirely towards the *conventions*, because this stage has no
failure that a frame would show. A sign turned 180 degrees is a perfectly drawn
sign giving the opposite instruction. A plate mirrored about its own axis is a
perfectly drawn TURN RIGHT where the publisher said TURN LEFT. A face table off
by one code paints NO ENTRY across the region and renders beautifully. `Q56` is
the precedent — every consumer took double-versus-single on trust from one field.

⚠️ **And this stage has less to lean on than `arrows.py` did.** An arrow's
bearing convention could be graded against its own host edge, because a published
arrow really does point along its road. Nothing here does: `ANGLE` is the
MicroStation label rotation, so the facing is *derived*. These tests are
therefore the only thing holding the derivation, and they assert it against
`surface.mitres` itself rather than against a comment — the same move
`test_kerbside.py` and `test_arrows.py` both make, for the same reason: a
systematic sign error agrees with itself everywhere and renders as a city.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline import arrows
from pipeline.arrows import axis_residual_deg, nearside
from pipeline.config import (
    SIGN_DRAWINGS,
    SIGN_OCTAGON,
    SIGN_PLATES,
    SIGN_TEXT,
    SignFace,
    SignLayer,
    Signs,
    load_config,
)
from pipeline.polyline import Segments
from pipeline.railings import facing_away
from pipeline.sign_text import _bake, _bounds, _coverage, _livery, _plate_mask
from pipeline.signs import (
    SIGNS_MATERIAL,
    Sign,
    SignReport,
    _Builder,
    _downstream_node,
    _draw_plate,
    _draw_pole,
    _merge_placements,
    _merge_posts,
    _Placed,
    _plate_facing_deg,
    _record_semantics,
    _register,
    _turn_classes,
    facing_from_side,
    layer_polygons,
    orphaned_supplementary,
    plate_extent_m,
    plate_frame,
)
from pipeline.surface import mitres
from tests.helpers import CITY_YAML

# The block as `hong_kong.yaml` declares it, trimmed to the codes the tests use.
# Held here rather than in `helpers.py`'s `CITY_YAML` because the block is
# optional by contract, and the fixture city's job is to prove that a city
# without one still builds — see `test_the_block_is_optional`.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "DTAD_TS_ABV_PT",
    "fields": {
        "code": "SIGNID",
        "bearing": "ANGLE",
        "level": "ELEVATION",
        "group": "GG_NAME",
    },
    "poles": {
        "layer": "DTAD_TS_POLE_PT",
        "fields": {"group": "GG_NAME", "level": "ELEVATION"},
    },
    "faces": {
        "TS115": {
            # `Q72`: mirrors `hong_kong.yaml`. Without it the fixture would
            # disagree with the shipped config about which way a NO ENTRY looks.
            "faces_against_traffic": True,
            "plate": "disc",
            "layers": [
                {"draw": "disc", "colour": "red", "size": 1.0},
                {"draw": "bar", "colour": "white", "size": 0.66},
            ],
        },
        "TS107": {
            "plate": "disc",
            "layers": [
                {"draw": "disc", "colour": "blue", "size": 1.0},
                {"draw": "arrow_left", "colour": "white", "size": 0.7},
            ],
        },
        "TS102": {
            "plate": "triangle_down",
            "layers": [{"draw": "triangle_down", "colour": "red", "size": 1.0}],
        },
        # The turn prohibitions `TestTheTurnRestrictionDiff` drives. Declared so
        # `diff` can look a face up the way `build_region` does — a hard lookup —
        # instead of branching around a fixture gap.
        "TS131": {
            "plate": "disc",
            "layers": [{"draw": "disc", "colour": "red", "size": 1.0}],
        },
        "TS132": {
            "plate": "disc",
            "layers": [{"draw": "disc", "colour": "red", "size": 1.0}],
        },
        "TS133": {
            "plate": "disc",
            "layers": [{"draw": "disc", "colour": "red", "size": 1.0}],
        },
        "TS734": {
            "plate": "rect_wide",
            "rank": "supplementary",
            "layers": [{"draw": "arrow_left", "colour": "black", "size": 0.72}],
        },
        "TS414": {
            "plate": "board_wide",
            # `warning`, because CT174/51-2(1) is TRAFFIC SIGNS (WARNING) and the
            # rank IS the sheet class. It defaulted to `regulatory` until `Q67`
            # noticed the three `P3-22` faces were all silently claiming to be
            # regulatory signs — which is a stack order, so a deviation board
            # could sit above a NO ENTRY on a post they share.
            "rank": "warning",
            "mirror": True,
            "layers": [
                {"draw": "board_wide", "colour": "white", "size": 1.0},
                {"draw": "chevrons", "colour": "black", "size": 0.86},
            ],
        },
    },
    "colours": {
        "red": "#c21a26",
        "blue": "#0d4794",
        "white": "#f0f0ea",
        "black": "#1c1c1f",
        # ⚠️ Mirrors `hong_kong.yaml` — and `yellow` is here because it *ties*
        # with `white` on the brightest channel, which is what the polarity test
        # pins. Dropping it would make that test silently untestable.
        "yellow": "#f0c020",
        "grey": "#70737a",
    },
    "disc_diameter_m": 0.60,
    "triangle_height_m": 0.68,
    "octagon_height_m": 0.60,
    "rect_width_m": 0.45,
    "rect_height_m": 0.60,
    "rect_wide_width_m": 0.60,
    "rect_wide_height_m": 0.25,
    "rect_info_width_m": 0.60,
    "rect_info_height_m": 0.55,
    "board_wide_width_m": 1.20,
    "board_wide_height_m": 0.40,
    "board_tall_width_m": 0.45,
    "board_tall_height_m": 0.58,
    "mount_height_m": 2.10,
    "stack_gap_m": 0.06,
    "pole_radius_m": 0.032,
    "pole_sides": 6,
    "pole_headroom_m": 0.05,
    "disc_segments": 12,
    "layer_lift_m": 0.004,
    "max_offset_m": 12.0,
    "max_pole_span_m": 15.0,
    "outset_m": 0.6,
    "max_shift_m": 6.0,
    "pole_merge_m": 0.75,
    "turn_straight_deg": 30.0,
    "turn_u_deg": 135.0,
}


def city_with(tmp_path, block: dict[str, Any] | None):
    """`testville` carrying the given signs block, loaded through the real
    loader — the same argument `test_arrows.py`'s namesake makes."""
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["signs"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_config(cities / "testville.yaml")


@pytest.fixture
def spec(tmp_path):
    """`testville` with a signs block bolted on, parsed by the real loader."""
    return city_with(tmp_path, BLOCK).signs


def sign(group: str, x: float, z: float, code: str = "TS115") -> Sign:
    """One `Sign` for the merge tests, where only group and position vary.

    A factory rather than six near-identical constructions — `test_arrows.py`'s
    `_built` is the house precedent. The published point is irrelevant to
    merging, which keys on the pole.
    """
    return Sign(code=code, group=group, x=x, z=z, published_x=x, published_z=z, axis_deg=0.0)


def edge(
    edge_id: int,
    points: list[list[float]],
    *,
    lanes: int = 2,
    width_m: float = 5.5,
    direction: str = "both",
    from_node: int | None = None,
    to_node: int | None = None,
):
    """One `roadgraph.json` edge dict, enough of one for `Segments.of`.

    ⚠️ **`from`/`to` default to a pair derived from the id** rather than to a
    constant, so two edges built without them cannot silently share a node and
    make a junction the test never meant to draw. The turn-restriction diff is
    the only caller that reads them.
    """
    return {
        "id": edge_id,
        "from": 2 * edge_id if from_node is None else from_node,
        "to": 2 * edge_id + 1 if to_node is None else to_node,
        "polyline": points,
        "lanes": lanes,
        # ⚠️ The surveyed carriageway `arrows.ribbons` reads (`Q96`), and
        # deliberately **not** `lanes x lane_width_m` — a fixture that encoded
        # the identity `Q95` severed would teach it back to the next reader.
        # ⚠️ Under the drawn `half_width_m` these tests supply (3.2, so a 6.4 m
        # ribbon), it also has to be a width `drawn = max(width_m, floor)` could
        # produce: 10.24 stood here and described a carriageway wider than the
        # road drawn over it, which is not a road.
        "width_m": width_m,
        "direction": direction,
        "elevation_level": 0,
    }


class TestTheFacingIsDerived:
    """The rule that replaces the facing nothing publishes.

    ⚠️ **Asserted against `surface.mitres` rather than against a comment.** The
    derivation reads the *sign* of `Snap.offset_m`, so a flip in that convention
    mirrors every sign in the city and still renders as a city — exactly the
    failure `test_kerbside.py` was written about.
    """

    def test_the_nearside_is_the_side_mitres_offsets_in(self):
        """A pole on the **offside** is at negative `offset_m` for a northward edge.

        ⚠️ **Which is to say the nearside is *positive*** — what `Snap.offset_m`
        documents and what `facing_from_side`'s `offset_m > 0.0` reads. The first
        version of this summary said "nearside is negative", the exact inversion
        the class docstring above is written against, while the body proved the
        opposite. A test whose title contradicts its assertions is worse than no
        test, because it is what a reader checks the convention against.

        Both facts are derived here from the same polyline, so a change to either
        that broke the other fails on the same day.
        """
        northward = [[0.0, 0.0, 10.0], [0.0, 0.0, 0.0]]
        snap = Segments.of([edge(0, northward)]).nearest(1.0, 5.0)
        assert snap.heading_deg == pytest.approx(0.0)

        # `mitres` offsets to the left of travel, which is the nearside. Heading
        # north (-Z), left is west (-X), so a point at +X is on the offside.
        normals = mitres(np.asarray(northward, dtype=np.float64))
        assert normals[0][0] < 0.0
        assert snap.offset_m < 0.0

    def test_a_nearside_sign_faces_back_along_its_edge(self):
        """Traffic running along the edge meets a nearside sign head-on."""
        assert facing_from_side(0.0, 1.0, False) == pytest.approx(180.0)
        assert facing_from_side(90.0, 1.0, False) == pytest.approx(270.0)

    def test_an_offside_sign_faces_along_its_edge(self):
        """On a two-way street the offside kerb serves the other direction."""
        assert facing_from_side(0.0, -1.0, False) == pytest.approx(0.0)
        assert facing_from_side(90.0, -1.0, False) == pytest.approx(90.0)

    def test_both_kerbs_of_a_one_way_face_its_only_traffic(self):
        """⚠️ **The branch whose absence was measurable.**

        A one-way edge has traffic in one direction, so both its kerbs address
        it. Without this the offside signs came out reversed and `signs.json`
        read the counter now called `no_entry_against_flow` at **117 of 253** — the
        coin-toss a broken rule
        produces, and the reason that counter exists.
        """
        assert facing_from_side(0.0, 1.0, True) == pytest.approx(180.0)
        assert facing_from_side(0.0, -1.0, True) == pytest.approx(180.0)


class TestAPlateMayFaceTheOtherWayFromItsPost:
    """`Q72` — the facing is a property of the FACE, not only of the pole.

    🔴 **The defect this closes rendered perfectly and was reported from the
    driving seat**: a NO ENTRY staring back down a one-way the car was legally
    on. Almost every face addresses the traffic already proceeding and so agrees
    with its post; a NO ENTRY addresses the driver who would come in the wrong
    way and is turned 180 degrees from it. 82 of Wan Chai's 499 posts carry both
    kinds, and before this they were drawn on one face.

    ⚠️ **Asserted through real `SignFace`s off the real loader**, not against
    hand-written booleans — the flag is config, and a test that stubbed it could
    not see the config and the code stop agreeing.
    """

    def test_a_face_that_addresses_oncoming_traffic_is_turned_from_its_post(self, spec):
        assert _plate_facing_deg(90.0, spec.faces["TS115"]) == pytest.approx(270.0)
        assert _plate_facing_deg(270.0, spec.faces["TS115"]) == pytest.approx(90.0)

    def test_every_other_face_agrees_with_its_post(self, spec):
        for code in ("TS102", "TS107", "TS734", "TS414"):
            assert _plate_facing_deg(90.0, spec.faces[code]) == pytest.approx(90.0)

    def test_the_turn_is_what_puts_a_no_entry_with_its_one_way_flow(self, spec):
        """The whole point, stated as geometry rather than as the flag.

        A one-way's traffic runs along `heading`; `facing_from_side` turns the
        post to face back at it, and the NO ENTRY must end up pointing the other
        way — along the flow, at whoever would enter against it.
        """
        heading = 252.0
        post = facing_from_side(heading, 1.0, True)
        assert post == pytest.approx((heading + 180.0) % 360.0)
        assert _plate_facing_deg(post, spec.faces["TS115"]) == pytest.approx(heading)

    def test_the_counter_fires_when_the_turn_is_taken_away(self, spec):
        """🔴 **The only assertion that makes `no_entry_against_flow` more than
        decoration**, and it is deliberately a *mutation* test.

        The counter cannot be moved by data — on a one-way host the post faces
        `heading + 180` and the turn adds another 180, so a flagged plate's
        residual is identically 0. What it guards is the flag and the turn
        themselves, so the only honest test is to remove one and watch it fire.
        Without this, re-inverting the comparison leaves a green suite.
        """
        graph = {"edges": [edge(0, APPROACH, direction="forward")], "turn_restrictions": []}
        assert (
            diff(spec, graph, [("TS115", NEARSIDE_POST)], one_way=True).no_entry_against_flow == 0
        )

        blunted = replace(spec.faces["TS115"], faces_against_traffic=False)
        mutated = replace(spec, faces={**spec.faces, "TS115": blunted})
        assert (
            diff(mutated, graph, [("TS115", NEARSIDE_POST)], one_way=True).no_entry_against_flow
            == 1
        )

    def test_a_turned_face_on_a_two_way_host_is_not_graded_for_flow(self, spec):
        """`TS116` is turned but makes no one-way claim, so a two-way host is not
        a disagreement — it must reach neither flow counter."""
        graph = {"edges": [edge(0, APPROACH, direction="both")], "turn_restrictions": []}
        report = diff(spec, graph, [("TS115", NEARSIDE_POST)])
        assert report.no_entry_against_flow == 0
        assert report.no_entry_on_two_way == 1

    def test_the_shipped_config_marks_the_no_entry_family_and_nothing_else(self, hong_kong):
        """⚠️ Against `hong_kong.yaml` itself, because the flag is data.

        A second face quietly gaining it would turn a whole code 180 degrees
        across the region and render perfectly — `Q64`'s failure class, on the
        one field that decides which way an instruction points.
        """
        faces = hong_kong.signs.faces
        turned = {code for code, face in faces.items() if face.faces_against_traffic}
        assert turned == {"TS115", "TS116"}


class TestThePlateFrame:
    """Which way is right, seen by somebody reading the sign.

    ⚠️ **This is the mirror test, and it is the one with no other net.** A plate
    built in a left-handed frame draws TURN RIGHT where the publisher said TURN
    LEFT: same position, same colours, same triangle count, and every other check
    in the repo passes.
    """

    def test_u_cross_up_is_the_outward_normal(self):
        """What makes counter-clockwise in `(u, v)` come out facing forward.

        The winding of every polygon this stage draws rests on it, and
        `facing_away` only catches a violation once something is built.
        """
        for facing_deg in (0.0, 37.0, 90.0, 180.0, 271.5):
            normal, right = plate_frame(facing_deg)
            assert np.allclose(np.cross(right, [0.0, 1.0, 0.0]), normal, atol=1e-12)

    def test_a_sign_facing_south_is_read_with_east_on_the_right(self):
        """Concrete enough to catch a mirror, which the identity above is not.

        A sign facing south (heading 180) is read by somebody standing south of
        it and looking **north**. Their right hand points east, `+X`.

        ⚠️ Worth working through rather than pattern-matching: the first draft of
        this test asserted west, on the reflex that a south-facing thing has west
        on its right. It does — on *its* right. The frame is the reader's.
        """
        _, right = plate_frame(180.0)
        assert right[0] == pytest.approx(1.0)
        assert right[2] == pytest.approx(0.0, abs=1e-12)

    def test_a_sign_facing_east_is_read_with_north_on_the_right(self):
        """The second case, because one axis cannot distinguish a transpose."""
        _, right = plate_frame(90.0)
        assert right[2] == pytest.approx(-1.0)
        assert right[0] == pytest.approx(0.0, abs=1e-12)

    def test_the_normal_points_the_way_the_sign_faces(self):
        """Heading 90 is east, so an east-facing plate's normal is `+X`."""
        normal, _ = plate_frame(90.0)
        assert normal[0] == pytest.approx(1.0)
        assert normal[2] == pytest.approx(0.0, abs=1e-12)


class TestWhatIsBuiltIsWoundRight:
    """Nothing this stage draws may disagree with the normal it was given.

    ⚠️ `signs.gdshader` is `cull_back`, so a violation renders as **nothing**.
    The first build shipped 3,200 such triangles — every pole in the region —
    because the prism ring was wound the way a plate wants.
    """

    def test_a_plate_and_its_back_agree_with_their_normals(self, spec):
        builder = _Builder()
        for facing_deg in (0.0, 45.0, 180.0, 300.0):
            _draw_plate(
                builder, spec, spec.faces["TS115"], np.array([0.0, 3.0, 0.0]), facing_deg, 1.0
            )
        mesh = builder.build("signs")
        assert mesh is not None
        assert facing_away(mesh) == 0

    def test_a_pole_agrees_with_its_normals(self, spec):
        """The regression this test exists for, held explicitly."""
        builder = _Builder()
        _draw_pole(builder, spec, 4.0, -7.0, 0.0, 3.0)
        mesh = builder.build("signs")
        assert mesh is not None
        assert facing_away(mesh) == 0

    def test_a_pole_faces_outward_rather_than_inward(self, spec):
        """`facing_away` alone would pass a pole wound inward *and* labelled so.

        It asks whether winding and normal agree, not whether either is right —
        so this asserts the normals actually point away from the post's axis.
        """
        builder = _Builder()
        _draw_pole(builder, spec, 0.0, 0.0, 0.0, 3.0)
        mesh = builder.build("signs")
        assert mesh is not None
        sides = np.abs(mesh.normals[:, 1]) < 0.5
        outward = (mesh.normals[sides, 0] * mesh.positions[sides, 0]) + (
            mesh.normals[sides, 2] * mesh.positions[sides, 2]
        )
        assert (outward > 0.0).all()

    def test_the_material_is_the_contract_name(self, spec):
        """The string `generated_scene_import.gd` dispatches the shader on."""
        builder = _Builder()
        _draw_pole(builder, spec, 0.0, 0.0, 0.0, 3.0)
        mesh = builder.build("signs")
        assert mesh is not None
        assert mesh.material == SIGNS_MATERIAL

    def test_every_plate_carries_vertex_colour(self, spec):
        """⚠️ The channel that makes one draw call carry four colours.

        `arrows.glb` ships none on purpose; this one must, and
        `verify_signs.gd` passes `true` to `check_surface` to match.
        """
        builder = _Builder()
        _draw_plate(builder, spec, spec.faces["TS107"], np.array([0.0, 3.0, 0.0]), 0.0, 1.0)
        mesh = builder.build("signs")
        assert mesh is not None
        assert mesh.colours is not None
        assert len(mesh.colours) == len(mesh.positions)
        # Blue field and a white arrow, so more than one colour is present.
        assert len({tuple(row) for row in mesh.colours.tolist()}) >= 2


# 🔴 **Every drawing except `text`, and the exclusion is the point of naming it.**
# The two sweeps below cover the whole vocabulary deliberately, so that the next
# glyph anyone adds is tested without anyone remembering to add it. `text` is the
# one word that has no polygons at all — it is a textured quad placed from the
# atlas by `_draw_plate` — so it is excluded HERE, once, rather than by softening
# either sweep into "whatever `layer_polygons` happens to answer".
# `test_text_has_no_polygons_and_says_so` is what holds the exclusion honest.
_POLYGON_DRAWINGS = tuple(draw for draw in SIGN_DRAWINGS if draw != SIGN_TEXT)


class TestTheFaceGeometry:
    def test_a_disc_plate_is_as_wide_as_it_is_tall(self, spec):
        half_w, half_h = plate_extent_m(spec, "disc")
        assert half_w == pytest.approx(half_h)
        assert 2.0 * half_w == pytest.approx(spec.disc_diameter_m)

    def test_a_layer_scales_with_its_size_fraction(self, spec):
        """`size` is a fraction of the plate, so a 900 mm disc scales with it."""
        full = layer_polygons(spec, "disc", 1.0, 0.3, 0.3)[0]
        half = layer_polygons(spec, "disc", 0.5, 0.3, 0.3)[0]
        assert np.abs(half).max() == pytest.approx(0.5 * np.abs(full).max())

    def test_every_layer_polygon_is_wound_counter_clockwise(self, spec):
        """What `plate_frame` then turns into an outward-facing triangle.

        Checked over every drawing the vocabulary has, because the turn glyphs
        are built as mirrors of one another and half of them come out reversed
        from the same expression — `arrows.py`'s recorded reason for `_ccw`.
        """
        for draw in _POLYGON_DRAWINGS:
            for polygon in layer_polygons(spec, draw, 1.0, 0.3, 0.3):
                shifted = np.roll(polygon, -1, axis=0)
                twice_area = float(
                    np.sum(polygon[:, 0] * shifted[:, 1] - shifted[:, 0] * polygon[:, 1])
                )
                assert twice_area > 0.0, f"{draw} is wound clockwise"

    def test_a_left_arrow_points_left_of_the_reader(self, spec):
        """⚠️ The other half of the mirror problem, in the glyph rather than the frame.

        `arrow_left` must extend further to `-u` than to `+u`. A mirrored glyph
        in a correct frame is as wrong as a correct glyph in a mirrored frame,
        and neither shows up in a triangle count.
        """
        points = np.vstack(layer_polygons(spec, "arrow_left", 1.0, 0.3, 0.3))
        assert points[:, 0].min() < -0.9 * points[:, 0].max()

    def test_a_right_arrow_is_the_mirror_of_a_left_one(self, spec):
        left = np.vstack(layer_polygons(spec, "arrow_left", 1.0, 0.3, 0.3))
        right = np.vstack(layer_polygons(spec, "arrow_right", 1.0, 0.3, 0.3))
        assert left[:, 0].min() == pytest.approx(-right[:, 0].max())

    def test_a_mirrored_board_flips_its_glyphs_and_keeps_its_winding(self, spec):
        """🔴 **The one face orientation this layer derives rather than reads.**

        TD publishes no left/right code pair for a deviation board, so which way
        the chevrons point is an assumption (`Q66`): away from the kerb the post
        stands on. Two things have to hold and only one of them is visible.

        ⚠️ **The invisible one is winding.** Negating `u` turns a
        counter-clockwise polygon clockwise, and `signs.gdshader` is `cull_back`
        — so a mirrored board would go *missing* rather than draw backwards,
        with `facing_away` still reading 0 because the normal is untouched.
        """
        face = spec.faces["TS414"]
        assert face.mirror_by_side

        def drawn(side: float):
            builder = _Builder()
            _draw_plate(builder, spec, face, np.zeros(3), 0.0, side)
            return builder.build("probe")

        nearside, offside = drawn(1.0), drawn(-1.0)

        # 🔴 **Which way it points, not merely that it moved.** The first version
        # of this test asserted `not allclose` plus `facing_away == 0`, and both
        # are symmetric under a side swap — so flipping `side > 0.0` to
        # `side < 0.0`, which mirrors every board onto the wrong kerb, passed the
        # whole suite. Found in review. `+u` is the viewer's right and the plate
        # faces `-Z` at `facing_deg` 0, so `plate_frame` maps `+u` onto `-X`.
        # ⚠️ Measured on the CHEVRONS, not the mesh — the plate outline and its
        # back are symmetric about `u`, so a whole-mesh extent is the same on
        # both kerbs and asserts nothing. The barb tips lie on the axis, and the
        # glyph points whichever way its tips are extreme.
        def tip_side(mesh) -> float:
            black = np.array([28, 28, 31])
            keep = np.abs(mesh.colours[:, :3].astype(int) - black).sum(1) < 8
            points = mesh.positions[keep]
            axis_u = -points[:, 0]
            tips = axis_u[np.isclose(points[:, 1], 0.0, atol=1e-6)]
            return 1.0 if tips.max() == pytest.approx(axis_u.max()) else -1.0

        assert tip_side(nearside) > 0.0, "a nearside board must point into the carriageway"
        assert tip_side(offside) < 0.0, "an offside board must point the other way"

        # The two really are reflections of one another, which `not allclose`
        # only hinted at.
        assert np.allclose(
            np.sort(nearside.positions * np.array([-1.0, 1.0, 1.0]), axis=0),
            np.sort(offside.positions, axis=0),
        )
        # And every triangle still faces the way its normal claims, on both.
        assert facing_away(nearside) == 0
        assert facing_away(offside) == 0

    def test_a_chevron_points_minus_u_before_any_mirror(self, spec):
        """🔴 **The other half of `Q66`, and it was unpinned too.**

        `_draw_plate` mirrors for the nearside, so the glyph itself has to be
        authored for the *offside* — pointing `-u`. Authoring it the other way
        round and flipping the side test cancel out, and the suite stayed green
        through exactly that pair of mutations. This is `test_a_left_arrow_
        points_left_of_the_reader`'s argument at the one face whose direction
        the publisher does not give.
        """
        points = np.vstack(layer_polygons(spec, "chevrons", 1.0, 0.3, 0.3))
        # The barb tips lie on the axis, and they are the leftmost thing drawn.
        on_axis = points[np.isclose(points[:, 1], 0.0)]
        assert on_axis[:, 0].min() == pytest.approx(points[:, 0].min())

    def test_a_chevron_row_is_centred_on_its_board(self, spec):
        """The row is narrower than the plate, and the slack was all on one side
        — 8% of `TS589`'s board width, small enough to look like nothing and
        entirely invisible to every counter the stage publishes."""
        for half_w, half_h in ((0.6, 0.2), (0.225, 0.29), (0.3, 0.3)):
            points = np.vstack(layer_polygons(spec, "chevrons", 1.0, half_w, half_h))
            assert points[:, 0].min() == pytest.approx(-points[:, 0].max(), abs=1e-9)

    def test_the_two_arrows_of_a_double_do_not_touch(self, spec):
        """⚠️ `_arrow_double`'s docstring claimed a shared gap it did not have:
        both stem tails sat at exactly `u = 0`, so `TS735` drew as one bar with
        two heads. Measured off the shipped layer in review, never seen."""
        polygons = layer_polygons(spec, "arrow_double", 1.0, 0.3, 0.125)
        right = [p for p in polygons if p[:, 0].mean() > 0.0]
        left = [p for p in polygons if p[:, 0].mean() < 0.0]
        assert right and left
        assert min(p[:, 0].min() for p in right) > max(p[:, 0].max() for p in left)

    def test_an_unmirrored_face_ignores_the_side_it_stands_on(self, spec):
        """The flag is opt-in, so every face that does not set it is unmoved —
        otherwise `Q66`'s assumption would leak onto plates TD *does* orient."""
        face = spec.faces["TS115"]
        assert not face.mirror_by_side

        meshes = []
        for side in (1.0, -1.0):
            builder = _Builder()
            _draw_plate(builder, spec, face, np.zeros(3), 0.0, side)
            meshes.append(builder.build("probe").positions)
        assert np.allclose(meshes[0], meshes[1])

    def test_every_plate_outline_can_be_measured_and_drawn(self, spec):
        """⚠️ **The drift `_PLATE_RECTS` exists to stop.** A plate is named in
        three places — `SIGN_PLATES` (what a face may be cut to), the extent
        lookup, and the outline branch in `layer_polygons` — and `P3-22` added
        three at once. A plate in the vocabulary that either site does not know
        raises at build time, on a city that loaded cleanly.
        """
        for plate in SIGN_PLATES:
            half_w, half_h = plate_extent_m(spec, plate)
            assert half_w > 0.0 and half_h > 0.0, plate
            assert layer_polygons(spec, plate, 1.0, half_w, half_h), plate

    def test_a_chevron_count_comes_from_the_plate_aspect(self, spec):
        """⚠️ TD draws three solid chevrons and two outlined — "repeat as
        required" — so a count is a property of the board's width, not a number
        to transcribe. A wide board gets three and a portrait one gets one, and
        both are what the extracted cells show.
        """
        wide = layer_polygons(spec, "chevrons", 1.0, 0.60, 0.20)
        tall = layer_polygons(spec, "chevrons", 1.0, 0.225, 0.29)
        # Two convex quads per chevron, because a chevron is concave.
        assert len(wide) == 3 * 2
        assert len(tall) == 1 * 2

    def test_a_concave_glyph_is_split_into_convex_pieces(self, spec):
        """⚠️ **`_Builder.polygon` fans from vertex 0 and takes a CONVEX polygon.**

        A chevron and a T are both concave as outlines, and fanning one emits
        triangles outside the shape with half of them wound backwards — it read
        `facing_away` **21** on the first build. Asserted as convexity rather
        than as a piece count so it holds however the glyphs are re-cut, and
        swept over **every** drawing rather than the four `P3-22` added, so the
        next concave glyph fails here without anyone remembering to add it —
        the same sweep `test_every_layer_polygon_is_wound_counter_clockwise`
        makes one class up.
        """
        for draw in _POLYGON_DRAWINGS:
            for polygon in layer_polygons(spec, draw, 1.0, 0.60, 0.20):
                edges = np.diff(np.vstack([polygon, polygon[:2]]), axis=0)
                cross = edges[:-1, 0] * edges[1:, 1] - edges[:-1, 1] * edges[1:, 0]
                assert np.all(cross > -1e-12), f"{draw} is concave: {polygon.tolist()}"

    def test_a_backslash_crosses_the_slash_it_mirrors(self, spec):
        """⚠️ The mirror problem again, on the pair that makes `TS183` a saltire.

        A `backslash` that drew a second `slash` would render as a **doubled
        bar**, which is a plausible-looking plate rather than an obviously broken
        one — `Q64`'s failure mode, where a wrong sign renders perfectly. So this
        asserts the two are mirrored in `u` *and* that their axes actually
        oppose, which a duplicated expression cannot satisfy.
        """
        slash = layer_polygons(spec, "slash", 1.0, 0.3, 0.3)[0]
        backslash = layer_polygons(spec, "backslash", 1.0, 0.3, 0.3)[0]

        mirrored = np.column_stack([-backslash[:, 0], backslash[:, 1]])
        assert sorted(map(tuple, np.round(slash, 9))) == sorted(map(tuple, np.round(mirrored, 9)))

        def axis(polygon: np.ndarray) -> np.ndarray:
            edges = np.diff(np.vstack([polygon, polygon[:1]]), axis=0)
            return edges[int(np.argmax(np.linalg.norm(edges, axis=1)))]

        assert float(axis(slash) @ axis(backslash)) == pytest.approx(0.0, abs=1e-9)


class TestThePublishedAngleIsNotConsumed:
    """`ANGLE` is the MicroStation label rotation, and nothing reads it.

    The residual is still computed and published so the claim stays checkable
    against a shipped artefact rather than a scratch script (`Q37`).
    """

    def test_the_axis_residual_folds_modulo_180(self):
        """A plate has an axis, not a head and a tail.

        The helper is `arrows.axis_residual_deg`, shared rather than restated;
        pinned here as well because this stage relies on the fold and would not
        notice `arrows.py` changing it.
        """
        assert axis_residual_deg(0.0, 180.0) == pytest.approx(0.0)
        assert axis_residual_deg(90.0, 0.0) == pytest.approx(90.0)
        assert axis_residual_deg(10.0, 350.0) == pytest.approx(20.0)

    def test_no_facing_depends_on_it(self):
        """`facing_from_side` takes no angle argument at all.

        Held as a test rather than as a comment because re-introducing `ANGLE`
        into the facing is the single most plausible future regression here —
        it is the field that *looks* like it should decide this.
        """
        import inspect

        parameters = inspect.signature(facing_from_side).parameters
        assert set(parameters) == {"snap_heading_deg", "side", "one_way"}


class TestTheBlockIsOptional:
    def test_a_city_without_a_signs_block_loads(self, tmp_path):
        """A city whose estate publishes no sign layer ships none.

        The shape `tramway`, `arrows`, `boxjunctions` and `railings` all take.
        """
        assert city_with(tmp_path, None).signs is None

    def test_an_unknown_drawing_fails_the_load(self, tmp_path):
        """⚠️ Refused at load rather than at draw time.

        A face naming geometry the pipeline does not have would otherwise draw a
        plate with a hole in it — a perfectly rendered blank sign.
        """
        block = {**BLOCK, "faces": dict(BLOCK["faces"])}
        block["faces"]["TS999"] = {
            "plate": "disc",
            "layers": [{"draw": "pentagram", "colour": "red", "size": 1.0}],
        }
        with pytest.raises(ValueError, match="pentagram"):
            city_with(tmp_path, block)

    def test_an_unknown_colour_fails_the_load(self, tmp_path):
        """A livery name with no entry would render a plausible sign, miscoloured."""
        block = {**BLOCK, "faces": dict(BLOCK["faces"])}
        block["faces"]["TS999"] = {
            "plate": "disc",
            "layers": [{"draw": "disc", "colour": "puce", "size": 1.0}],
        }
        with pytest.raises(ValueError, match="puce"):
            city_with(tmp_path, block)

    def test_a_plate_with_no_layers_fails_the_load(self, tmp_path):
        """A blank plate instructs nothing and renders perfectly."""
        block = {**BLOCK, "faces": dict(BLOCK["faces"])}
        block["faces"]["TS999"] = {"plate": "disc", "layers": []}
        with pytest.raises(ValueError, match="not a sign"):
            city_with(tmp_path, block)

    def test_a_layer_shape_may_not_be_a_plate(self, tmp_path):
        """A plate needs a closed outline with a back; `slash` has neither."""
        block = {**BLOCK, "faces": dict(BLOCK["faces"])}
        block["faces"]["TS999"] = {
            "plate": "slash",
            "layers": [{"draw": "disc", "colour": "red", "size": 1.0}],
        }
        with pytest.raises(ValueError, match="plate"):
            city_with(tmp_path, block)


class TestTheStackOrder:
    """A main sign on top, its supplementary plate hanging below.

    ⚠️ **Sorting by `SIGNID` alone gets this backwards**, and it shipped that way
    for one build: `TS733` sorts after `TS115`, so the NO ENTRY hung off the
    bottom of its own arrow plate. It renders as a perfectly built signpost
    assembled upside down, which is why it needs a test rather than an eye.
    """

    def test_a_supplementary_plate_ranks_below_a_regulatory_sign(self, spec):
        assert spec.faces["TS734"].rank > spec.faces["TS115"].rank

    def test_a_face_that_says_nothing_is_regulatory(self, spec):
        """The default is the common case, so most rows stay silent."""
        assert spec.faces["TS115"].rank == 0

    def test_an_unknown_rank_fails_the_load(self, tmp_path):
        block = {**BLOCK, "faces": {**BLOCK["faces"]}}
        block["faces"]["TS999"] = {
            "plate": "disc",
            "rank": "urgent",
            "layers": [{"draw": "disc", "colour": "red", "size": 1.0}],
        }
        with pytest.raises(ValueError, match="urgent"):
            city_with(tmp_path, block)

    def test_a_non_boolean_mirror_fails_the_load(self, tmp_path):
        """⚠️ **The one face key whose absence is invisible in a frame.**

        A face that should mirror and does not draws a plausible board pointing
        the wrong way (`Q66`), so a `mirror: "yes"` quietly read as truthy — or
        a misspelled `mirrored:` silently ignored — is the failure this layer
        cannot see. The type check is refused loudly; the misspelling is not,
        and that is recorded rather than fixed, because nothing here rejects
        unknown face keys and making it do so is a wider change than `P3-22`.
        """
        block = {**BLOCK, "faces": {**BLOCK["faces"]}}
        block["faces"]["TS999"] = {
            "plate": "disc",
            "mirror": "yes",
            "layers": [{"draw": "disc", "colour": "red", "size": 1.0}],
        }
        with pytest.raises(ValueError, match="mirror"):
            city_with(tmp_path, block)

    def test_a_colours_table_without_the_back_colour_fails_the_load(self, tmp_path):
        """⚠️ The one livery key no `faces:` row names.

        Every plate's back and every post is drawn in it, so a city whose
        `colours:` omits it would load, pass every other config check, and die
        partway through the build on a bare `KeyError`.
        """
        block = {**BLOCK, "colours": {k: v for k, v in BLOCK["colours"].items() if k != "grey"}}
        with pytest.raises(ValueError, match="grey"):
            city_with(tmp_path, block)

    def test_a_signs_source_that_is_not_declared_fails_the_load(self, tmp_path):
        """`signs:` was the only block whose `source` nothing checked.

        Without it a typo surfaces regions away, inside `fetch.source_reads` —
        the failure `_check_declared_source` exists to prevent.
        """
        with pytest.raises(ValueError, match=r"signs\.source"):
            city_with(tmp_path, {**BLOCK, "source": "no_such_source"})


class TestPostsAreRegisteredAndMerged:
    """The two things a screenshot caught that no counter could.

    ⚠️ Both are `Q60`'s territory: a published position is moved, and the price
    of moving it is published rather than asserted to be small.
    """

    def test_coincident_poles_become_one_post(self, spec):
        """🔴 The layer publishes poles at the *same point*.

        Nearest-other-pole reads 0.00 m at p10 and p25 across the region, because
        several `GG_NAME` groups hang off one real post. Drawn apart, their plates
        interpenetrate and neither is readable.
        """
        report = SignReport()
        here = sign("a", 10.0, 20.0, code="TS115")
        alongside = sign("b", 10.2, 20.1, code="TS102")
        posts = _merge_posts(
            {("a", 10.0, 20.0): [here], ("b", 10.2, 20.1): [alongside]}, spec.pole_merge_m, report
        )
        assert len(posts) == 1
        assert report.poles_merged == 1
        assert len(posts[0][2]) == 2

    def test_a_pole_beyond_the_merge_radius_stays_its_own_post(self, spec):
        report = SignReport()
        a = sign("a", 0.0, 0.0, code="TS115")
        b = sign("b", 5.0, 0.0, code="TS115")
        posts = _merge_posts(
            {("a", 0.0, 0.0): [a], ("b", 5.0, 0.0): [b]}, spec.pole_merge_m, report
        )
        assert len(posts) == 2
        assert report.poles_merged == 0

    def test_merging_is_deterministic_in_the_input_order(self, spec):
        """Two builds of the same data must merge the same way.

        The pass is greedy, so the order it walks decides which post absorbs
        which — and a mesh that changes shape between builds is not reproducible.
        """
        signs = {
            ("b", 0.3, 0.0): [
                Sign(
                    code="TS115",
                    group="b",
                    x=0.3,
                    z=0.0,
                    published_x=0.0,
                    published_z=0.0,
                    axis_deg=0.0,
                )
            ],
            ("a", 0.0, 0.0): [
                Sign(
                    code="TS102",
                    group="a",
                    x=0.0,
                    z=0.0,
                    published_x=0.0,
                    published_z=0.0,
                    axis_deg=0.0,
                )
            ],
        }
        first = _merge_posts(signs, spec.pole_merge_m, SignReport())
        second = _merge_posts(dict(reversed(list(signs.items()))), spec.pole_merge_m, SignReport())
        assert [(x, z) for x, z, _ in first] == [(x, z) for x, z, _ in second]

    def test_the_nearside_is_the_frame_mitres_offsets_in(self):
        """⚠️ The registration moves along this vector, so its sign is load-bearing.

        A flip mirrors every post in the city onto the far kerb and still renders
        as a city — held against `mitres` itself rather than against a comment.
        """
        northward = [[0.0, 0.0, 10.0], [0.0, 0.0, 0.0]]
        normals = mitres(np.asarray(northward, dtype=np.float64))
        assert nearside(0.0)[0] == pytest.approx(-1.0)
        assert normals[0][0] < 0.0


class TestTheRegistrationArithmetic:
    """The three ways registration moved a post silently and wrongly.

    ⚠️ All three were found in review, all three were invisible to every
    counter, and all three render as a perfectly built signpost.
    """

    def test_the_foot_comes_off_the_polyline_not_from_the_offset(self):
        """🔴 `Snap.offset_m` is the distance to the **clamped** projection.

        For a point past an edge's end the displacement has an along-edge
        component, so `point - offset_m * nearside` is not on the centreline.
        Here the point is dead on the road's axis 5 m past its end: the
        reconstruction puts it 5 m off a road it is standing in the middle of,
        while `Ribbon.foot_at` puts it back on the axis.
        """
        eastward = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]
        ribbons = arrows.ribbons(
            {"edges": [edge(0, eastward, lanes=2)]},
            {"carriageway": [{"edge": 0, "half_width_m": [3.2, 3.2], "trim_m": [0.0, 0.0]}]},
        )
        snap = Segments.of([edge(0, eastward)]).nearest(105.0, 0.0)
        assert snap.t == pytest.approx(1.0)

        reconstructed = np.array([105.0, 0.0]) - snap.offset_m * nearside(snap.heading_deg)
        foot = ribbons[0].foot_at(snap.t)
        assert foot[0] == pytest.approx(100.0)
        assert foot[1] == pytest.approx(0.0)
        # The reconstruction is 5 m off the axis; the foot is on it.
        assert abs(reconstructed[1]) == pytest.approx(5.0)

    def test_a_post_on_the_centreline_faces_the_side_it_was_placed_on(self):
        """🔴 `Segments.nearest` returns **-0.0** for a point on the centreline.

        `-0.0 >= 0.0` is true and `-0.0 > 0.0` is false, so placing on
        `offset_m >= 0` and facing on `offset_m > 0` put the post one side and
        turned it to face the other — a NO ENTRY drawn perfectly, backwards.
        `facing_from_side` takes the side actually used for exactly this.
        """
        eastward = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]
        snap = Segments.of([edge(0, eastward)]).nearest(50.0, 0.0)
        assert math.copysign(1.0, snap.offset_m) == -1.0
        side = 1.0 if snap.offset_m >= 0.0 else -1.0
        assert side == 1.0
        assert facing_from_side(snap.heading_deg, side, False) == pytest.approx(
            (snap.heading_deg + 180.0) % 360.0
        )

    def test_a_post_already_clear_of_the_kerb_keeps_the_point_td_surveyed(self, spec):
        """🔴 `Q78`: the correction runs outward, and it used to move both ways.

        `widen_default` draws the ribbon 1.6x the real carriageway, so a pole
        standing on the real kerb lands in the drawn lane — an argument for
        pushing a post **out**. Assigning the target unconditionally also dragged
        the posts already standing clear back *toward* the road, and `shift_m` is
        an absolute value, so no counter could tell the two apart.
        """
        eastward = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]
        ribbon = arrows.ribbons(
            {"edges": [edge(0, eastward, lanes=2)]},
            {"carriageway": [{"edge": 0, "half_width_m": [3.2, 3.2], "trim_m": [0.0, 0.0]}]},
        )[0]
        # 6 m out, against a 3.2 m drawn half-width and a 0.6 m outset.
        published = np.array([50.0, 6.0])
        snap = Segments.of([edge(0, eastward)]).nearest(50.0, 6.0)
        assert abs(snap.offset_m) > 3.2 + spec.outset_m

        report = SignReport()
        placed, side = _register(spec, snap, ribbon, published, report)

        assert placed[0] == pytest.approx(published[0])
        assert placed[1] == pytest.approx(published[1])
        assert report.posts_kept_as_surveyed == 1
        # A real 0.0 rather than a skipped append, so the partition still closes.
        assert report.shift_m == [0.0]
        # ⚠️ The side still comes off `snap.offset_m`, so the facing derivation
        # is untouched — this branch moves a position and nothing else.
        assert side == (1.0 if snap.offset_m >= 0.0 else -1.0)

    def test_a_post_inside_the_ribbon_is_still_pushed_out_to_the_kerb(self, spec):
        """The guard against `Q78`'s branch inverting.

        ⚠️ **An inverted rule renders as a perfectly built signpost** — standing
        in the road, which is the state the registration exists to prevent. The
        push is the case that must keep happening, so it is asserted rather than
        assumed by the test above passing.
        """
        eastward = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]
        ribbon = arrows.ribbons(
            {"edges": [edge(0, eastward, lanes=2)]},
            {"carriageway": [{"edge": 0, "half_width_m": [3.2, 3.2], "trim_m": [0.0, 0.0]}]},
        )[0]
        segments = Segments.of([edge(0, eastward)])
        published = np.array([50.0, 1.0])
        snap = segments.nearest(50.0, 1.0)
        assert abs(snap.offset_m) < 3.2 + spec.outset_m

        report = SignReport()
        placed, _ = _register(spec, snap, ribbon, published, report)

        settled = segments.nearest(float(placed[0]), float(placed[1]))
        assert abs(settled.offset_m) == pytest.approx(3.2 + spec.outset_m)
        assert report.posts_kept_as_surveyed == 0
        assert report.shift_m[0] == pytest.approx(3.2 + spec.outset_m - 1.0)

    def test_registration_can_re_collapse_posts_and_is_merged_again(self, spec):
        """Two posts on one edge, side and `t` are pushed to the same offset.

        The first merge works on surveyed positions and cannot see it, so the
        placements are deduped too — otherwise each restarts its stack at
        `mount_height_m` in the same place.
        """
        report = SignReport()
        snap = Segments.of([edge(0, [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]])]).nearest(50.0, 2.0)
        a = _Placed(
            x=50.0,
            z=-5.6,
            y=0.0,
            facing_deg=0.0,
            side=1.0,
            one_way=False,
            snap=snap,
            plates=[sign("a", 50.0, 2.0)],
        )
        b = _Placed(
            x=50.0,
            z=-5.6,
            y=0.0,
            facing_deg=0.0,
            side=1.0,
            one_way=False,
            snap=snap,
            plates=[sign("b", 50.0, 3.0, code="TS102")],
        )
        merged = _merge_placements([a, b], spec.pole_merge_m, report)
        assert len(merged) == 1
        assert len(merged[0].plates) == 2
        assert report.posts_merged_after_shift == 1


class TestTheReportPartitions:
    """The counters must account for every sign read.

    ⚠️ **The whole of what can see this stage fail** — `Q58`'s lesson. A
    partition that stops closing means a refusal path was added without a
    counter, and the missing signs are invisible in every other way.
    """

    def test_the_measured_distribution_reports_its_own_count(self):
        """`n` exceeding `drawn` is how a reader tells the residual was recorded
        over refusals too — the `drawn_gauge_m` trap `Q58` records."""
        assert SignReport.measured([]) == {}
        measured = SignReport.measured([0.0, 1.0, 2.0, 3.0])
        assert measured["n"] == 4
        assert measured["max"] == pytest.approx(3.0)

    def test_the_shift_distribution_still_decomposes_with_kept_posts_in_it(self, spec):
        """`Q78`'s kept posts append a real 0.0, so the documented identity holds.

        `len(shift_m) == poles_drawn + posts_over_shift + posts_in_carriageway
        + posts_merged_after_shift` is what lets a reader tell whether `n`'s
        excess over the drawn posts came from the bar or from somewhere else.
        Skipping the append for a post that did not move would have been the
        tidier branch and would have quietly stopped that partition closing.

        ⚠️ **A wide ribbon, because `max_shift_m` can now only refuse a post
        surveyed INSIDE the carriageway** — one surveyed clear of it is kept, and
        a kept post makes no move for the bar to refuse. At the region's real
        widths nothing reaches the bar at all, which is why this is built rather
        than sampled.
        """
        eastward = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]
        ribbon = arrows.ribbons(
            {"edges": [edge(0, eastward, lanes=2)]},
            {"carriageway": [{"edge": 0, "half_width_m": [8.0, 8.0], "trim_m": [0.0, 0.0]}]},
        )[0]
        segments = Segments.of([edge(0, eastward)])
        report = SignReport()

        placed = 0
        for z in (0.5, 4.0, 10.0, -12.0):
            snap = segments.nearest(50.0, z)
            if _register(spec, snap, ribbon, np.array([50.0, z]), report) is not None:
                placed += 1

        # 0.5 m in is an 8.1 m push against a 6.0 m bar, so it is refused; 4.0 m
        # in is pushed; 10.0 and -12.0 are already clear of 8.6 and are kept.
        assert report.posts_over_shift == 1
        assert report.posts_kept_as_surveyed == 2
        assert placed == 3
        assert len(report.shift_m) == placed + report.posts_over_shift
        # ⚠️ **Containment, not equality, and the strict `>` is why.** A post
        # surveyed exactly on `half_width + outset` takes the *push* branch and
        # its move is 0.0 too, so counting zeros would merge two populations.
        # Asserting equality here would hold on this fixture and mislead about
        # the rule — `Q78`'s own confusion between a number and what it counts.
        assert report.shift_m.count(0.0) >= report.posts_kept_as_surveyed
        boundary = segments.nearest(50.0, 8.6)
        assert _register(spec, boundary, ribbon, np.array([50.0, 8.6]), report) is not None
        assert report.posts_kept_as_surveyed == 2
        assert report.shift_m[-1] == pytest.approx(0.0)

    def test_a_stack_climbs_the_post(self, spec):
        """Two plates on one pole occupy different heights.

        Held because the stack offset is accumulated in a loop, and a stack that
        failed to advance would draw every plate of an assembly inside the one
        below it — invisible, and heavier.
        """
        builder = _Builder()
        centre_low = np.array([0.0, 2.4, 0.0])
        centre_high = np.array([0.0, 3.1, 0.0])
        _draw_plate(builder, spec, spec.faces["TS115"], centre_low, 0.0, 1.0)
        _draw_plate(builder, spec, spec.faces["TS102"], centre_high, 0.0, 1.0)
        mesh = builder.build("signs")
        assert mesh is not None
        low, high = mesh.aabb()
        assert high[1] - low[1] > 0.7

    def test_a_triangle_plate_is_equilateral(self, spec):
        """GIVE WAY is an equilateral triangle standing on its point.

        ⚠️ **So it is *wider* than it is tall** — 0.785 m across at Hong Kong's
        0.68 m height — and the first version of this test asserted the reverse
        in its name while checking only `half_w > 0.0`, which cannot fail. The
        assertion below is the formula itself, which is what would catch the
        `*2` / `/2` slip the expression invites.
        """
        half_w, half_h = plate_extent_m(spec, "triangle_down")
        assert math.isclose(2.0 * half_h, spec.triangle_height_m)
        assert half_w == pytest.approx(half_h / math.sqrt(3.0) * 2.0)
        assert half_w > half_h


# --------------------------------------------------------------------------
# The turn-restriction diff (`Q62`)
# --------------------------------------------------------------------------
#
# A T junction at node 10, drive-on-left, in the frame `Snap.heading_deg` uses:
# north is `-Z`, so an edge running north has heading 0.
#
#                 |  APPROACH (edge 0), heading 0, node 1 -> node 10
#     WEST -------+------- EAST
#     (edge 1)   10       (edge 2)
#
# Leaving node 10 westward is a left turn, eastward a right turn.
APPROACH = [[0.0, 0.0, 100.0], [0.0, 0.0, 0.0]]
WEST_ARM = [[0.0, 0.0, 0.0], [-100.0, 0.0, 0.0]]
EAST_ARM = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]
# ⚠️ **Leaning, not exactly straight, and leaning both ways.** A movement at
# exactly 0 deg is classified the same by every broken version of the sign test
# below it, so it cannot tell them apart — the `Q66` trap in miniature. These two
# sit inside `turn_straight_deg` and fall on opposite sides of zero.
NORTH_ARM_EAST = [[0.0, 0.0, 0.0], [10.0, 0.0, -100.0]]
NORTH_ARM_WEST = [[0.0, 0.0, 0.0], [-10.0, 0.0, -100.0]]

# ⚠️ Nearside is *left of travel*, and travel here runs north, so the nearside
# kerb is at negative x. Both posts sit halfway along, at `t` 0.5.
NEARSIDE_POST = (-3.0, 50.0)
OFFSIDE_POST = (3.0, 50.0)
# ⚠️ **Off-centre on purpose.** At `t` 0.5 the distance to either end of the
# edge is the same number, so a post halfway along cannot tell the two apart —
# and the test that measures the distance is precisely the one that must.
NEARSIDE_POST_QUARTER = (-3.0, 75.0)
OFFSIDE_POST_QUARTER = (3.0, 75.0)


def junction(*arms: tuple[int, list[list[float]]]) -> dict[str, Any]:
    """The T above as a graph, with `edge 0` arriving at node 10."""
    edges = [edge(0, APPROACH, from_node=1, to_node=10)]
    edges += [edge(edge_id, points, from_node=10, to_node=10 + edge_id) for edge_id, points in arms]
    return {"edges": edges, "turn_restrictions": []}


def banned(graph: dict[str, Any], to_edge: int) -> dict[str, Any]:
    """The movement out of `edge 0` through node 10 onto `to_edge`, banned."""
    graph["turn_restrictions"].append({"from_edge": 0, "via_node": 10, "to_edge": to_edge})
    return graph


def t_junction(to_edge: int) -> dict[str, Any]:
    """The T with both arms, and the movement onto `to_edge` banned."""
    return banned(junction((1, WEST_ARM), (2, EAST_ARM)), to_edge=to_edge)


def posted(code: str, at: tuple[float, float], one_way: bool = False) -> tuple[Sign, _Placed]:
    """One plate of `code` on the approach, as `build_region` would have placed it.

    Returns the real `_Placed` rather than loose fields, so the facing is
    `facing_from_side`'s own answer and never hand-written — the coupling
    between the facing and the junction is the property under test.
    """
    segments = Segments.of([edge(0, APPROACH, from_node=1, to_node=10)])
    snap = segments.nearest(at[0], at[1])
    # ⚠️ **A restatement of `build_region`, not a rule of its own** — the `>=` is
    # load-bearing, because `-0.0` belongs to the nearside, and it is pinned by
    # `test_a_post_on_the_centreline_faces_the_side_it_was_placed_on`. If the
    # production line moves, this must move with it.
    side = 1.0 if snap.offset_m >= 0.0 else -1.0
    plate = sign("g", at[0], at[1], code=code)
    return plate, _Placed(
        x=at[0],
        z=at[1],
        y=0.0,
        facing_deg=facing_from_side(snap.heading_deg, side, one_way),
        side=side,
        one_way=one_way,
        snap=snap,
        plates=[plate],
    )


def diff(
    spec: Signs,
    graph: dict[str, Any],
    plates: Sequence[tuple[str, tuple[float, float]]],
    *,
    one_way: bool = False,
) -> SignReport:
    """Run `_record_semantics` over `plates`, the way `build_region` does."""
    by_edge = {int(item["id"]): item for item in graph["edges"]}
    turns = _turn_classes(graph["turn_restrictions"], by_edge, spec)
    report = SignReport()
    for code, at in plates:
        plate, post = posted(code, at, one_way)
        # ⚠️ **Through `_plate_facing_deg`, exactly as `build_region` does**
        # (`Q72`). Passing `post.facing_deg` straight through would make every
        # test here grade a NO ENTRY at its post's facing, which is the facing
        # the defect drew and not the one that ships.
        #
        _record_semantics(report, plate, post, spec.faces[code], turns, by_edge[post.snap.edge])
    return report


class TestTheTurnRestrictionDiff:
    """The instrument `Q62` named, and the only grader the derived facing has.

    ⚠️ **Every test here must fail under a stated mutation**, because `Q66` is
    what happens when one does not: that claim shipped with two mutations passing
    the whole suite, since the property asserted was symmetric under the very
    swap it was meant to catch. The mutation each test kills is named in its
    docstring.

    ⚠️ **The facing is never hand-written** — `posted` takes it from
    `facing_from_side` — so a test that passes here is testing the expression
    the stage actually uses.
    """

    def test_a_sign_is_matched_to_the_junction_its_own_traffic_reaches(self):
        """🔴 **The whole coupling, and the reason this diff grades the facing.**

        A sign faces the traffic it addresses, so that traffic is heading *away*
        from the plate — and the junction it governs is the one ahead of it. On a
        two-way the two kerbs address opposite streams, so they govern opposite
        ends of the same edge.

        ⚠️ Mutation killed: flipping `side > 0.0` in `facing_from_side`. That
        mirrors every post onto the wrong kerb, which sends every plate to the
        far end of its edge — and nothing else in this file would notice,
        because a mirrored city renders as a city.

        🔴 **This holds per plate and still does not grade the region**, which is
        the finding `Q62` keeps: the host here is two-way, and in Wan Chai 62 of
        68 prohibition plates stand on a *one-way*, where `facing_from_side`
        returns the same facing for both kerbs and the mutation changes nothing.
        Mirroring the whole region moves `turn_sign_agreed` from 29 to 30. The
        test below pins the branch that makes that so.
        """
        host = edge(0, APPROACH, from_node=1, to_node=10)
        near = posted("TS131", NEARSIDE_POST)[1]
        far = posted("TS131", OFFSIDE_POST)[1]

        assert _downstream_node(host, near)[0] == 10
        assert _downstream_node(host, far)[0] == 1

    def test_a_one_way_host_matches_the_same_junction_from_either_kerb(self, spec):
        """🔴 **The reason this diff cannot grade the kerb side**, pinned.

        `facing_from_side` turns both kerbs of a one-way to face its only
        traffic, so both address the same junction and a mirrored city produces
        an identical match. That is not a defect — it is the correct rule — but
        it bounds what `turn_sign_agreed` can be read to mean, and
        `turn_sign_on_one_way` publishes how much of the population it applies
        to: **62 of 68** in Wan Chai.

        ⚠️ Mutation killed: dropping `one_way or` from `facing_from_side`, which
        would make the two kerbs of a one-way disagree — and would also send
        `no_entry_against_flow` back to the 117 of 253 that found it the first time.
        """
        host = edge(0, APPROACH, from_node=1, to_node=10, direction="forward")
        near = posted("TS131", NEARSIDE_POST, one_way=True)[1]
        far = posted("TS131", OFFSIDE_POST, one_way=True)[1]

        assert _downstream_node(host, near)[0] == _downstream_node(host, far)[0] == 10

        graph = t_junction(to_edge=1)
        counted = [
            (report.turn_sign_agreed, report.turn_sign_on_one_way)
            for report in (
                diff(spec, graph, [("TS131", at)], one_way=True)
                for at in (NEARSIDE_POST, OFFSIDE_POST)
            )
        ]
        assert counted == [(1, 1), (1, 1)]

    def test_the_distance_is_measured_to_the_junction_the_sign_governs(self):
        """Not to the nearer end, and not to the edge's midpoint.

        `Snap.t` is normalised over the whole edge, so the two kerbs of a post
        halfway along a 100 m edge are each 50 m from *different* junctions.
        Published because there is deliberately no bar on it (`Q58`).

        ⚠️ Mutation killed: measuring from the wrong end — `t * length` where the
        junction is at `t` 1. ⚠️ **Which needs a post that is not halfway
        along**: at `t` 0.5 both ends are 50 m away and the swap is invisible,
        which is how the first version of this test passed under it.
        """
        host = edge(0, APPROACH, from_node=1, to_node=10)
        near = posted("TS131", NEARSIDE_POST_QUARTER)[1]
        far = posted("TS131", OFFSIDE_POST_QUARTER)[1]

        assert near.snap.t == pytest.approx(0.25)
        # The nearside post governs the far junction, so it is 75 m off it; the
        # offside post governs the near one, 25 m back the other way.
        assert _downstream_node(host, near) == (10, pytest.approx(75.0))
        assert _downstream_node(host, far) == (1, pytest.approx(25.0))

    def test_a_no_left_turn_agrees_with_a_banned_left_and_not_with_a_banned_right(self, spec):
        """The classification, read off the movement's own geometry.

        🔴 **The graph publishes no restriction *type*** — `P1-3` reads
        `OTHER_REST_TYPE` and never emits it — so a banned movement is a left or
        a right only by its bearings. Two sources naming different banned
        movements at one junction is the finding this whole counter exists for.

        ⚠️ Mutation killed: swapping the sign test in `_turn_class`. Asserted in
        both directions, because a swap leaves a one-sided test passing.
        """
        left, right = t_junction(to_edge=1), t_junction(to_edge=2)

        assert diff(spec, left, [("TS131", NEARSIDE_POST)]).turn_sign_agreed == 1
        assert diff(spec, left, [("TS132", NEARSIDE_POST)]).turn_sign_disagreed == 1
        assert diff(spec, right, [("TS132", NEARSIDE_POST)]).turn_sign_agreed == 1
        assert diff(spec, right, [("TS131", NEARSIDE_POST)]).turn_sign_disagreed == 1

    def test_a_u_turn_is_the_edge_returned_and_falls_out_of_the_180_deg_change(self, spec):
        """⚠️ **The one class no threshold can get wrong**, which is why `TS133`
        is in the table although `Q62` named only the two turns.

        A movement that leaves by the edge it arrived on reads its two bearings
        off one polyline in *opposite* orders, so the change is exactly 180 deg
        and `turn_u_deg` is refused at or above 180. 60 of the region's 217
        restrictions are this shape, and none needs a special case — a branch for
        them was written and removed as dead.

        ⚠️ Mutation killed: flipping either `leaving=` argument in
        `_turn_classes`, after which both bearings come off the polyline the same
        way, the change is 0, and a U-turn reads as a straight-through movement.
        """
        graph = banned(junction((1, WEST_ARM)), to_edge=0)
        assert diff(spec, graph, [("TS133", NEARSIDE_POST)]).turn_sign_agreed == 1
        assert diff(spec, graph, [("TS131", NEARSIDE_POST)]).turn_sign_disagreed == 1

    def test_a_junction_the_graph_bans_nothing_at_is_unmatched_and_not_agreed(self, spec):
        """The weak bucket, and it must not be the default the others fall into.

        The graph does not publish every signed prohibition — 34 banned lefts
        against 38 drawn `TS131` — so silence is a coverage fact about the graph
        and never a passing grade for the sign.

        ⚠️ Mutation killed: treating a missing key as agreement, which would read
        as a perfect score on a region whose graph carried no restrictions at all.
        """
        quiet = junction((1, WEST_ARM), (2, EAST_ARM))
        report = diff(spec, quiet, [("TS131", NEARSIDE_POST)])
        assert (report.turn_sign_unmatched, report.turn_sign_agreed) == (1, 0)

    def test_a_movement_straight_through_is_neither_a_left_nor_a_right(self, spec):
        """A restriction the sign cannot be claiming, so the plate disagrees.

        The region publishes 4 of these. They are a real banned movement, so the
        approach is *matched* — what is refused is the claim that they are the
        turn the plate names.

        ⚠️ Mutation killed: letting the straight band fall through to left/right,
        which turns 4 published restrictions into whichever turn their noise
        happens to lean. ⚠️ **Both leans and both codes**, because one of each
        pair still disagrees under that mutation — an earlier version of this
        test asserted a single lean against a single code and the mutation
        walked straight through it.
        """
        for arm in (NORTH_ARM_EAST, NORTH_ARM_WEST):
            graph = banned(junction((1, arm)), to_edge=1)
            for code in ("TS131", "TS132"):
                report = diff(spec, graph, [(code, NEARSIDE_POST)])
                assert (report.turn_sign_disagreed, report.turn_sign_unmatched) == (1, 0)

    def test_the_three_outcomes_partition_the_prohibition_plates(self, spec):
        """The identity `SignReport`'s docstring states, and `signs.json` publishes.

        ⚠️ Mutation killed: any `return` that skips a plate without counting it —
        the partition is what makes the three numbers readable as shares rather
        than as three unrelated tallies.
        """
        graph = t_junction(to_edge=1)
        plates = [
            ("TS131", NEARSIDE_POST),
            ("TS132", NEARSIDE_POST),
            ("TS133", NEARSIDE_POST),
            ("TS131", OFFSIDE_POST),
            ("TS115", NEARSIDE_POST),
        ]
        report = diff(spec, graph, plates)
        counted = report.turn_sign_agreed + report.turn_sign_disagreed + report.turn_sign_unmatched
        # Four prohibition plates; the NO ENTRY is counted by the other diff.
        assert counted == 4
        assert len(report.turn_sign_to_junction_m) == 4
        assert report.no_entry_on_two_way == 1


class TestASupplementaryPlateNeedsSomethingToQualify:
    """🔴 **A post carrying only arrows says nothing, and it looks like it does.**

    `TS733`/`TS734` are captioned ARROW (RIGHT) / ARROW (LEFT) on TD's own
    supplementary sheet, and the Road Users' Code gives them their meaning:
    *"Direction in which the prohibition or restriction applies"*. They qualify
    the plate above them. `Q65` put most of those plates out of scope, so the
    whitelist started leaving arrows standing on their own — a black arrow
    pointing along a kerb at nothing, which reads as a driving instruction and
    is not one. The user found it in a frame; nothing in the bundle could.

    ⚠️ **Tested on `orphaned_supplementary` rather than on a built region**,
    because the rule is one predicate and a region test would grade the join.
    """

    def test_an_arrow_on_its_own_is_orphaned(self, spec):
        assert orphaned_supplementary(spec, ["TS734"])

    def test_two_arrows_on_one_post_are_still_orphaned(self, spec):
        """The count is not what makes an assembly; the ranks are."""
        assert orphaned_supplementary(spec, ["TS734", "TS734"])

    def test_an_arrow_under_a_sign_is_kept(self, spec):
        assert not orphaned_supplementary(spec, ["TS115", "TS734"])

    def test_an_arrow_under_a_WARNING_sign_is_kept(self, spec):
        """⚠️ **The test is "nothing outranks supplementary", not "a regulatory
        sign is present".** A deviation board is `warning` and a NO THROUGH ROAD
        is `informatory`; an arrow under either is a real assembly, and a rule
        written against `regulatory` would have deleted both.
        """
        assert spec.faces["TS414"].rank != 0
        assert not orphaned_supplementary(spec, ["TS414", "TS734"])

    def test_an_empty_post_is_not_orphaned(self, spec):
        """Nothing was refused, so nothing is counted — the counter has to stay
        a count of *this* decision or its partition stops meaning anything."""
        assert not orphaned_supplementary(spec, [])


class TestTheLetteringLayer:
    """`P3-20`: the one face with words on it, and the bundle's one texture."""

    def test_text_has_no_polygons_and_says_so(self, spec):
        """🔴 **The refusal `_POLYGON_DRAWINGS` leans on.**

        A `text` layer that quietly returned the plate outline would paint a
        blank rectangle over the face and render as the wordless plate `P3-20`
        exists to replace — so the fallback has to be an exception, not a shape.
        """
        with pytest.raises(ValueError, match="atlas"):
            layer_polygons(spec, SIGN_TEXT, 1.0, 0.3, 0.3)

    def test_a_mirrored_face_may_not_carry_text(self, tmp_path):
        """🔴 **Mirroring writes the words backwards.**

        `Q66`'s mirror negates `u` to turn a chevron round, which is right for a
        chevron and catastrophic for lettering — on a plate whose whole job is
        to be read, and it would render perfectly. Refused at load rather than
        trusted to a comment.
        """
        block = {**BLOCK, "text_cell_px": 64, "text_source": "stands"}
        block["faces"] = {**BLOCK["faces"]}
        block["faces"]["TS999"] = {
            "plate": "triangle_down",
            "mirror": True,
            "layers": [
                {"draw": "triangle_down", "colour": "red", "size": 1.0},
                {"draw": "text", "colour": "black", "size": 1.0},
            ],
        }
        with pytest.raises(ValueError, match="backwards"):
            city_with(tmp_path, block)

    def test_a_text_layer_without_a_cell_size_fails_the_load(self, tmp_path):
        """A cell of 0 px bakes nothing, and a plate with nothing baked on it is
        the blank plate again. Caught on the way in."""
        block = {**BLOCK, "text_source": "stands"}
        block["faces"] = {**BLOCK["faces"]}
        block["faces"]["TS999"] = {
            "plate": "triangle_down",
            "layers": [
                {"draw": "triangle_down", "colour": "red", "size": 1.0},
                {"draw": "text", "colour": "black", "size": 1.0},
            ],
        }
        with pytest.raises(ValueError, match="text_cell_px"):
            city_with(tmp_path, block)

    def test_a_text_layer_without_a_source_fails_the_load(self, tmp_path):
        """⚠️ **The sheets are in a DIFFERENT archive from the signs**, so this
        is not derivable from `source:` and a city that forgets it would build
        every plate and silently letter none."""
        block = {**BLOCK, "text_cell_px": 64}
        block["faces"] = {**BLOCK["faces"]}
        block["faces"]["TS999"] = {
            "plate": "triangle_down",
            "layers": [
                {"draw": "triangle_down", "colour": "red", "size": 1.0},
                {"draw": "text", "colour": "black", "size": 1.0},
            ],
        }
        with pytest.raises(ValueError, match="text_source"):
            city_with(tmp_path, block)

    def test_a_city_with_no_lettering_needs_neither_key(self, tmp_path):
        """✅ **Zero textures stays the default** (`Q63`). A city whose faces
        carry no words declares no budget and ships no image."""
        city = city_with(tmp_path, BLOCK)
        assert city.signs is not None
        assert city.signs.text_cell_px == 0
        assert city.signs.text_source is None


def _cell(*, hole: bool) -> np.ndarray:
    """A synthetic index-plan cell: a red plate, and TD's dimension either side.

    The plate is a red square from (10, 10) to (29, 29); with `hole`, it carries
    a white field from (15, 15) to (24, 24). The two 1 px red columns at x=2 and
    x=37 stand in for the extension lines of the dimension TD draws across every
    cell — red, thin, detached, and **not** part of the plate.
    """
    cell = np.full((40, 40, 3), 255, dtype=np.uint8)
    red = (200, 30, 30)
    cell[10:30, 10:30] = red
    if hole:
        cell[15:25, 15:25] = 255
    cell[15:26, 2] = red
    cell[15:26, 37] = red
    return cell


class TestWhereThePlateStops:
    """🔴 `Q68`: the plate every lettering fraction is measured against.

    An error here is invisible by construction — `plate_rect` is a *fraction* of
    this, so a plate read 13% wide prints the words 13% small on a face that
    otherwise renders perfectly. `TS101` is the case that found it: TD's two red
    dimension extension lines took the octagon from 269 px to 308.

    ⚠️ Against `_plate_mask` and `_bounds` rather than a wrapper, because those
    two are what `build_atlas` calls — a test that pins a convenience nobody
    ships is free to agree with itself while the shipped path drifts.
    """

    def test_the_dimension_lines_are_not_the_plate(self):
        """The plate is the ink enclosing the field, not every red pixel."""
        assert _bounds(_plate_mask(_cell(hole=True))) == (10, 10, 29, 29)

    def test_ink_enclosing_nothing_falls_back_to_all_of_it(self):
        """⚠️ **A solid blob is a face with nothing on it, and refusing it here
        would report as missing lettering** — `build_atlas` raises on a missing
        plate, and that message would name the wrong defect. No face in scope
        reaches this, and the old reading is the honest answer when one does."""
        assert _bounds(_plate_mask(_cell(hole=False))) == (2, 10, 37, 29)

    def test_a_cell_with_no_ink_at_all_is_still_no_plate(self):
        """The one case that really is nothing to crop."""
        assert _plate_mask(np.full((40, 40, 3), 255, dtype=np.uint8)) is None


class TestTheOctagon:
    """`P3-20`: the STOP plate, and the half-step that decides what it reads as."""

    def test_it_is_as_wide_as_it_is_tall(self, spec):
        """One authored number, `octagon_height_m`, sizes both extents.

        ✅ **And that squareness is checkable against the publisher**: `Q68`'s
        corrected plate box reads TD's own `TS101` cell at 269 x 269 px.
        """
        half_w, half_h = plate_extent_m(spec, SIGN_OCTAGON)
        assert math.isclose(half_w, half_h)
        assert math.isclose(2.0 * half_w, spec.octagon_height_m)

    def test_the_top_is_flat_and_not_a_corner(self, spec):
        """🔴 **The whole difference between a STOP plate and a rotated square.**

        Vertices at `k * 45` degrees put a point at the top; a STOP has a flat
        top, flat bottom and flat sides. Half a step out renders perfectly as
        the wrong shape, which is the only kind of failure this stage has.
        """
        (polygon,) = layer_polygons(spec, SIGN_OCTAGON, 1.0, 0.3, 0.3)
        assert len(polygon) == 8
        on_top = np.isclose(polygon[:, 1], polygon[:, 1].max())
        assert int(on_top.sum()) == 2, "a flat top is two vertices, a corner is one"

    def test_the_flats_are_what_the_authored_number_measures(self, spec):
        """Across the flats, not corner to corner — how a plate is specified.

        ⚠️ Sized from `plate_extent_m` rather than from literals, so
        `octagon_height_m` is actually in the call. Passing `0.3, 0.3` by hand
        and asserting 0.6 would hold even if the extent read the wrong field.
        """
        half_w, half_h = plate_extent_m(spec, SIGN_OCTAGON)
        (polygon,) = layer_polygons(spec, SIGN_OCTAGON, 1.0, half_w, half_h)
        for axis in (0, 1):
            span = polygon[:, axis].max() - polygon[:, axis].min()
            assert math.isclose(span, spec.octagon_height_m)

    # ⚠️ **No winding test here on purpose.** `SIGN_OCTAGON` is in
    # `SIGN_DRAWINGS`, so `test_every_layer_polygon_is_wound_counter_clockwise`
    # and the convexity sweep already cover it — which is what those sweeps are
    # for, and a hand-written copy could only ever agree with them.


def _knockout_cell(*, hole: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """A red plate with paper knocked out of it, and the plate's own mask.

    `hole=False` keeps the field solid, which is what the crop-bounding test
    needs: the only paper left is outside the plate.
    """
    cell = np.full((20, 20, 3), 255, dtype=np.uint8)
    cell[5:15, 5:15] = (200, 30, 30)
    if hole:
        cell[8:12, 8:12] = 255
    plate = np.zeros((20, 20), dtype=bool)
    plate[5:15, 5:15] = True
    return cell, plate


def _face(glyph: str, field: str = "red") -> SignFace:
    return SignFace(
        plate=SIGN_OCTAGON,
        layers=(
            SignLayer(draw=SIGN_OCTAGON, colour=field, size=1.0),
            SignLayer(draw=SIGN_TEXT, colour=glyph, size=1.0),
        ),
        rank=0,
        mirror_by_side=False,
        faces_against_traffic=False,
    )


class TestWhichWayTheLetteringIsCutOut:
    """🔴 `Q68`: TD draws lettering both ways, and one of them read as zero.

    `TS102` is black ink on a white field; `TS101` is white knocked out of a
    solid red octagon. The crop that finds the first returns 0.0000 everywhere
    on the second — `black` ink covers **0.0000** of `TS101`'s cell — so
    `_ink_box` handed back `None` and `build_atlas` refused a face that is
    entirely lettering. `Q67` found `TS414` shipped in negative for the same
    reason: the pipeline assumed one polarity and TD uses two.
    """

    def test_the_livery_comes_off_the_face_and_not_off_a_default(self, spec):
        """🔴 **Both colours were hardcoded to black-on-white.** The `text`
        layer's own `colour` went unread, and the field is the layer beneath."""
        livery = _livery(spec, _face("white", field="red"))
        assert tuple(int(v) for v in livery.glyph_rgb) == spec.colours["white"]
        assert tuple(int(v) for v in livery.field_rgb) == spec.colours["red"]

    def test_lighter_than_its_field_is_a_knockout(self, spec):
        """⚠️ **Derived from the livery, never from a colour's NAME.** A second
        city's STOP is its own publisher's, so `"white"` is not a string this
        may test for — hard rule 3. Both shipped pairs, so the assertion guards
        the polarities that actually render: `TS101` white-on-red and `TS102`
        black-on-white."""
        assert _livery(spec, _face("white", field="red")).knockout
        assert not _livery(spec, _face("black", field="white")).knockout

    def test_the_brightest_channel_is_not_the_test(self, spec):
        """🔴 **The regression guard for a tie that ships.** The first version
        compared `max()`, and in this palette `white` `#f0f0ea` and `yellow`
        `#f0c020` are **both 240** — so a white glyph on a yellow field read as
        ink, took the wrong crop and would have baked a blank cell. `yellow` is
        real livery (`TS589`'s border), so the face is reachable config, and
        `colour.luminance` separates them 0.87 to 0.56."""
        white = np.asarray(spec.colours["white"], dtype=float)
        yellow = np.asarray(spec.colours["yellow"], dtype=float)
        assert white.max() == yellow.max(), "the tie is the point; pick another pair if it moves"
        assert _livery(spec, _face("white", field="yellow")).knockout

    def test_a_knockout_reads_the_paper_and_the_other_reads_the_ink(self):
        """The two polarities on one cell, which is the clearest statement of
        why this cannot be a single rule: each returns zero where the other
        returns the glyph."""
        cell, plate = _knockout_cell()
        knocked = _coverage(cell, plate, knockout=True)
        assert knocked[9, 9] > 0.9, "the knocked-out paper is the glyph"
        assert knocked[6, 6] < 0.2, "the red field is not"

        inked = _coverage(cell, plate, knockout=False)
        assert inked.max() == 0.0, "read the other way, a red plate carries no ink at all"

    def test_the_plate_body_bounds_the_crop(self):
        """⚠️ **An octagon's bounding box has paper in its corners**, and on a
        knockout paper is what the glyph is made of — so a crop crossing the
        plate edge reads the corners as lettering and returns the whole plate."""
        cell, plate = _knockout_cell(hole=False)
        assert _coverage(cell, plate, knockout=True)[0, 0] == 0.0

    def test_the_bake_lays_the_face_own_colours_down(self, spec):
        """🔴 **The one place `TS101`'s livery actually lands**, and the failure
        it guards is a colour swap — which `_livery` returning two same-shaped
        arrays used to make a one-character mistake."""
        livery = _livery(spec, _face("white", field="red"))
        covered = _bake(np.ones((4, 4)), livery, 2)
        bare = _bake(np.zeros((4, 4)), livery, 2)
        assert tuple(int(v) for v in covered[0, 0]) == spec.colours["white"]
        assert tuple(int(v) for v in bare[0, 0]) == spec.colours["red"]

    def test_a_face_whose_words_have_no_field_fails_the_load(self, tmp_path):
        """🔴 **The field is the layer beneath the words**, so a leading `text`
        layer has nothing to bake over. `sign_text.py` would have to invent a
        colour, and the one it invented before `TS101` was white — which on a
        red plate is a white box with the words in it, rendering as a sticker
        stuck to the sign."""
        block = {**BLOCK, "text_cell_px": 64, "text_source": "stands"}
        block["faces"] = {**BLOCK["faces"]}
        block["faces"]["TS999"] = {
            "plate": "triangle_down",
            "layers": [{"draw": "text", "colour": "white", "size": 1.0}],
        }
        with pytest.raises(ValueError, match="beneath"):
            city_with(tmp_path, block)

    def test_a_face_may_not_carry_two_text_layers(self, tmp_path):
        """⚠️ **One cell is baked per face and `_draw_plate` gives it to every
        `text` layer**, so a second would repeat the first's words and ignore
        its own `colour` — the same phrase twice on one plate, rendering
        perfectly. `_livery` reads the first layer and would never see it."""
        block = {**BLOCK, "text_cell_px": 64, "text_source": "stands"}
        block["faces"] = {**BLOCK["faces"]}
        block["faces"]["TS999"] = {
            "plate": "triangle_down",
            "layers": [
                {"draw": "triangle_down", "colour": "white", "size": 1.0},
                {"draw": "text", "colour": "black", "size": 1.0},
                {"draw": "text", "colour": "red", "size": 1.0},
            ],
        }
        with pytest.raises(ValueError, match="more than one text layer"):
            city_with(tmp_path, block)
