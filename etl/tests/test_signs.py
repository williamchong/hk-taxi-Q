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
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline import arrows
from pipeline.arrows import axis_residual_deg, nearside
from pipeline.config import SIGN_DRAWINGS, SIGN_PLATES, load_city
from pipeline.fares import Segments
from pipeline.railings import facing_away
from pipeline.signs import (
    SIGNS_MATERIAL,
    Sign,
    SignReport,
    _Builder,
    _draw_plate,
    _draw_pole,
    _facing_from_side,
    _merge_placements,
    _merge_posts,
    _Placed,
    _plate_frame,
    layer_polygons,
    plate_extent_m,
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
        "TS734": {
            "plate": "rect_wide",
            "rank": "supplementary",
            "layers": [{"draw": "arrow_left", "colour": "black", "size": 0.72}],
        },
        "TS414": {
            "plate": "board_wide",
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
        "grey": "#70737a",
    },
    "disc_diameter_m": 0.60,
    "triangle_height_m": 0.68,
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
    return load_city("testville", cities_root=cities)


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


def edge(edge_id: int, points: list[list[float]], *, lanes: int = 2, direction: str = "both"):
    return {
        "id": edge_id,
        "polyline": points,
        "lanes": lanes,
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
        documents and what `_facing_from_side`'s `offset_m > 0.0` reads. The first
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
        assert _facing_from_side(0.0, 1.0, False) == pytest.approx(180.0)
        assert _facing_from_side(90.0, 1.0, False) == pytest.approx(270.0)

    def test_an_offside_sign_faces_along_its_edge(self):
        """On a two-way street the offside kerb serves the other direction."""
        assert _facing_from_side(0.0, -1.0, False) == pytest.approx(0.0)
        assert _facing_from_side(90.0, -1.0, False) == pytest.approx(90.0)

    def test_both_kerbs_of_a_one_way_face_its_only_traffic(self):
        """⚠️ **The branch whose absence was measurable.**

        A one-way edge has traffic in one direction, so both its kerbs address
        it. Without this the offside signs came out reversed and `signs.json`
        read `no_entry_with_flow` at **117 of 253** — the coin-toss a broken rule
        produces, and the reason that counter exists.
        """
        assert _facing_from_side(0.0, 1.0, True) == pytest.approx(180.0)
        assert _facing_from_side(0.0, -1.0, True) == pytest.approx(180.0)


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
            normal, right = _plate_frame(facing_deg)
            assert np.allclose(np.cross(right, [0.0, 1.0, 0.0]), normal, atol=1e-12)

    def test_a_sign_facing_south_is_read_with_east_on_the_right(self):
        """Concrete enough to catch a mirror, which the identity above is not.

        A sign facing south (heading 180) is read by somebody standing south of
        it and looking **north**. Their right hand points east, `+X`.

        ⚠️ Worth working through rather than pattern-matching: the first draft of
        this test asserted west, on the reflex that a south-facing thing has west
        on its right. It does — on *its* right. The frame is the reader's.
        """
        _, right = _plate_frame(180.0)
        assert right[0] == pytest.approx(1.0)
        assert right[2] == pytest.approx(0.0, abs=1e-12)

    def test_a_sign_facing_east_is_read_with_north_on_the_right(self):
        """The second case, because one axis cannot distinguish a transpose."""
        _, right = _plate_frame(90.0)
        assert right[2] == pytest.approx(-1.0)
        assert right[0] == pytest.approx(0.0, abs=1e-12)

    def test_the_normal_points_the_way_the_sign_faces(self):
        """Heading 90 is east, so an east-facing plate's normal is `+X`."""
        normal, _ = _plate_frame(90.0)
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
            _draw_plate(builder, spec, spec.faces["TS115"], np.array([0.0, 3.0, 0.0]), facing_deg)
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
        _draw_plate(builder, spec, spec.faces["TS107"], np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signs")
        assert mesh is not None
        assert mesh.colours is not None
        assert len(mesh.colours) == len(mesh.positions)
        # Blue field and a white arrow, so more than one colour is present.
        assert len({tuple(row) for row in mesh.colours.tolist()}) >= 2


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
        """What `_plate_frame` then turns into an outward-facing triangle.

        Checked over every drawing the vocabulary has, because the turn glyphs
        are built as mirrors of one another and half of them come out reversed
        from the same expression — `arrows.py`'s recorded reason for `_ccw`.
        """
        for draw in SIGN_DRAWINGS:
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

        # The glyphs really did move: the same board on the two kerbs is not the
        # same mesh. Without this the test passes on a mirror that does nothing.
        assert not np.allclose(
            np.sort(nearside.positions, axis=0), np.sort(offside.positions, axis=0)
        )
        # And every triangle still faces the way its normal claims, on both.
        assert facing_away(nearside) == 0
        assert facing_away(offside) == 0

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
        for draw in SIGN_DRAWINGS:
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
        """`_facing_from_side` takes no angle argument at all.

        Held as a test rather than as a comment because re-introducing `ANGLE`
        into the facing is the single most plausible future regression here —
        it is the field that *looks* like it should decide this.
        """
        import inspect

        parameters = inspect.signature(_facing_from_side).parameters
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
            "layers": [{"draw": "octagon", "colour": "red", "size": 1.0}],
        }
        with pytest.raises(ValueError, match="octagon"):
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
    """The two ways registration moved a post silently and wrongly.

    ⚠️ Both were found in review, both were invisible to every counter, and both
    render as a perfectly built signpost.
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
        `_facing_from_side` takes the side actually used for exactly this.
        """
        eastward = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]
        snap = Segments.of([edge(0, eastward)]).nearest(50.0, 0.0)
        assert math.copysign(1.0, snap.offset_m) == -1.0
        side = 1.0 if snap.offset_m >= 0.0 else -1.0
        assert side == 1.0
        assert _facing_from_side(snap.heading_deg, side, False) == pytest.approx(
            (snap.heading_deg + 180.0) % 360.0
        )

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

    def test_a_stack_climbs_the_post(self, spec):
        """Two plates on one pole occupy different heights.

        Held because the stack offset is accumulated in a loop, and a stack that
        failed to advance would draw every plate of an assembly inside the one
        below it — invisible, and heavier.
        """
        builder = _Builder()
        centre_low = np.array([0.0, 2.4, 0.0])
        centre_high = np.array([0.0, 3.1, 0.0])
        _draw_plate(builder, spec, spec.faces["TS115"], centre_low, 0.0)
        _draw_plate(builder, spec, spec.faces["TS102"], centre_high, 0.0)
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
