"""The turn-arrow stage (`P3-15`, `Q53`).

Weighted towards the *conventions* rather than the drawing, because that is
where this stage can be confidently wrong and where nothing downstream would
notice. An arrow read with the wrong bearing convention is a perfectly drawn
arrow pointing across the road. An arrow wound the wrong way is nothing at all.
A glyph table off by one code paints turn-left across the region and renders
beautifully. `Q56` is the precedent — every consumer took double-versus-single
on trust from one field — and there is no second publisher of marking symbols to
cross-check against, so these tests are the whole of it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.arrows import (
    ARROWS_MATERIAL,
    ArrowReport,
    Symbol,
    _Builder,
    _draw,
    _place,
    axis_residual_deg,
    directed_residual_deg,
    glyph_polygons,
)
from pipeline.config import load_city
from pipeline.fares import Segments
from pipeline.surface import downward_facing, mitres
from tests.helpers import CITY_YAML

# The block as `hong_kong.yaml` declares it, trimmed to the codes the tests use.
# Held here rather than in `helpers.py`'s `CITY_YAML` because the block is
# optional by contract, and the fixture city's job is to prove that a city
# without one still builds — see `test_the_block_is_optional`.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "DTAD_RD_MARK_SYM_PT",
    "fields": {
        "code": "REFNAME",
        "bearing": "ANGLE",
        "level": "ELEVATION",
        "size": "SYMBOL_SIZE",
    },
    "glyphs": {
        "1017": {"movements": ["ahead"], "length_m": 4.0},
        "1018": {"movements": ["ahead"], "length_m": 6.0},
        "1019": {"movements": ["left"], "length_m": 4.0},
        "1021": {"movements": ["right"], "length_m": 4.0},
        "1027": {"movements": ["ahead", "left"], "length_m": 4.0},
    },
    "stem_width_frac": 0.085,
    "head_length_frac": 0.325,
    "head_width_frac": 0.235,
    "branch_reach_frac": 0.28,
    "lift_m": 0.015,
    "max_offset_m": 12.0,
    "bearing_tolerance_deg": 30.0,
}


def city_with(tmp_path, block: dict[str, Any] | None):
    """`testville` carrying the given arrows block, loaded through the real
    loader — the same argument `test_tramway.py`'s namesake makes."""
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["arrows"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_city("testville", cities_root=cities)


@pytest.fixture
def spec(tmp_path):
    """`testville` with an arrows block bolted on, parsed by the real loader."""
    return city_with(tmp_path, BLOCK).arrows


def edge(edge_id: int, points: list[list[float]], *, lanes: int = 2, direction: str = "forward"):
    return {
        "id": edge_id,
        "polyline": points,
        "lanes": lanes,
        "direction": direction,
        "elevation_level": 0,
    }


class TestTheBearingConvention:
    """`ANGLE` is a mathematical angle, and the game heading is `90 - ANGLE`.

    ⚠️ **Asserted against `surface.mitres` rather than against a comment**, the
    same way `test_kerbside.py` holds the side convention. The two conventions
    have the same failure mode: a systematic sign or offset error agrees with
    itself everywhere and renders as a city.
    """

    @pytest.mark.parametrize(
        ("angle_deg", "expected_heading_deg"),
        [
            # ANGLE 0 is east, which is heading 90 clockwise from north.
            (0.0, 90.0),
            # ANGLE 90 is north, which is heading 0.
            (90.0, 0.0),
            (180.0, 270.0),
            (270.0, 180.0),
        ],
    )
    def test_a_published_angle_reads_as_a_game_heading(self, angle_deg, expected_heading_deg):
        assert (90.0 - angle_deg) % 360.0 == pytest.approx(expected_heading_deg)

    def test_the_heading_agrees_with_the_frame_mitres_offsets_in(self):
        """A heading of 0 points the way an edge running north points.

        `Segments.heading_deg` is what an arrow's bearing is graded against, and
        `mitres` is what decides which side of that edge is the nearside. Both
        are derived here from the same polyline, so a change to either that
        broke the other fails on the same day.
        """
        northward = [[0.0, 0.0, 10.0], [0.0, 0.0, 0.0]]
        snap = Segments.of([edge(0, northward)]).nearest(1.0, 5.0)
        assert snap.heading_deg == pytest.approx(0.0)

        # `mitres` offsets to the left of travel, which is the nearside — `U = 0`.
        # Travelling north (-Z), left is west (-X), so the nearside offset is
        # negative in X and a point at +X is on the offside.
        normals = mitres(np.asarray(northward, dtype=np.float64))
        assert normals[0][0] < 0.0
        assert snap.offset_m < 0.0

    def test_a_symbol_pointing_across_its_edge_is_off_axis(self):
        eastward = 90.0
        northward = 0.0
        assert axis_residual_deg(eastward, northward) == pytest.approx(90.0)

    def test_the_directed_residual_does_not_fold(self):
        """The signed question, which only a one-way host may ask.

        Kept apart from the axis residual because the two answer different
        questions from the same two numbers, and the first draft wrote the same
        expression out twice.
        """
        assert directed_residual_deg(0.0, 180.0) == pytest.approx(180.0)
        assert directed_residual_deg(10.0, 350.0) == pytest.approx(20.0)

    def test_the_axis_residual_folds_at_180_so_an_opposing_arrow_is_aligned(self):
        """A two-way street carries arrows pointing both ways down one axis.

        Refusing on the directed residual would throw away every arrow on the
        far side of every two-way street — the region's two-way hosts split
        roughly evenly when this was measured.
        """
        assert axis_residual_deg(0.0, 180.0) == pytest.approx(0.0)
        assert axis_residual_deg(10.0, 185.0) == pytest.approx(5.0)


class TestTheGlyph:
    """What each published code draws."""

    def test_every_polygon_is_wound_counter_clockwise(self, spec):
        """⚠️ The failure this catches renders as *nothing*.

        A turn head is the mirror of its opposite, so half of them come out of
        the same expression reversed, and `cull_back` draws neither.
        """
        for code, glyph in spec.glyphs.items():
            for polygon in glyph_polygons(spec, glyph.movements, glyph.length_m):
                shifted = np.roll(polygon, -1, axis=0)
                twice_area = float(
                    np.sum(polygon[:, 0] * shifted[:, 1] - shifted[:, 0] * polygon[:, 1])
                )
                assert twice_area > 0.0, f"RM{code} has a reversed polygon"

    def test_a_placed_glyph_faces_up(self, spec):
        """The winding survives the mapping into world space.

        `_place` maps the glyph frame with a **negative determinant**, so this
        is what says counter-clockwise there is up-facing here. Checked at
        several headings because a sign error in one axis of the rotation
        survives a single-heading test.
        """
        glyph = spec.glyphs["1027"]
        for heading_deg in (0.0, 37.0, 90.0, 180.0, 271.0):
            builder = _Builder()
            for polygon in glyph_polygons(spec, glyph.movements, glyph.length_m):
                plan = _place(polygon, 0.0, 0.0, heading_deg)
                builder.polygon(plan, np.zeros(len(plan)))
            mesh = builder.build("arrows")
            assert mesh is not None
            assert downward_facing(mesh) == (0, 0.0)

    def test_an_ahead_arrow_points_the_way_its_heading_says(self, spec):
        """The nose is north of the tail when the heading is north.

        The one assertion here that a reader can check against the world: an
        arrow at heading 0 must have its furthest vertex towards `-Z`.
        """
        glyph = spec.glyphs["1017"]
        placed = np.vstack(
            [
                _place(polygon, 0.0, 0.0, 0.0)
                for polygon in glyph_polygons(spec, glyph.movements, glyph.length_m)
            ]
        )
        assert placed[:, 1].min() == pytest.approx(-0.5 * glyph.length_m)

    def test_a_turn_head_sits_on_the_side_its_movement_names(self, spec):
        """Left is `-u`, which at heading 0 is `-X`. A mirrored glyph table
        would draw every turn arrow pointing the wrong way, which is exactly
        the debit `GAME_DESIGN.md` prices against a missing one."""
        left = np.vstack([_place(p, 0.0, 0.0, 0.0) for p in glyph_polygons(spec, ("left",), 4.0)])
        right = np.vstack([_place(p, 0.0, 0.0, 0.0) for p in glyph_polygons(spec, ("right",), 4.0)])
        assert left[:, 0].min() < -0.5
        assert right[:, 0].max() > 0.5
        assert left[:, 0].max() == pytest.approx(-right[:, 0].min(), abs=1e-9)

    def test_the_two_published_lengths_of_one_marking_scale_together(self, spec):
        """`RM1017` and `RM1018` are the same arrow at 4 m and 6 m.

        A single authored length would draw one of the pair wrong by half its
        own size, on a marking whose whole defence is that it is read.
        """
        short = np.vstack(glyph_polygons(spec, ("ahead",), 4.0))
        long = np.vstack(glyph_polygons(spec, ("ahead",), 6.0))
        assert long[:, 1].max() / short[:, 1].max() == pytest.approx(1.5)
        assert long[:, 0].max() / short[:, 0].max() == pytest.approx(1.5)


class TestDrawing:
    def test_an_arrow_takes_the_grade_of_the_road_under_it(self, spec):
        """A 4 m glyph on a slope is not laid flat.

        `lift_m` is 15 mm, so a flat glyph on any real gradient has one end
        under the road — which reads as half an arrow rather than as an error.
        """
        builder = _Builder()
        symbol = Symbol(code="1017", x=0.0, z=5.0, heading_deg=0.0)
        _draw(builder, spec, symbol, spec.glyphs["1017"], np.array([0.0, 5.0]), 0.0, 1.0)
        mesh = builder.build("arrows")
        assert mesh is not None
        # The nose is uphill of the tail, and every vertex is clear of the deck.
        heights = mesh.positions[:, 1]
        assert heights.max() > heights.min()
        assert heights.min() >= spec.lift_m - 1e-9

    def test_the_mesh_names_the_material_the_engine_dispatches_on(self, spec):
        assert _built(spec).material == ARROWS_MATERIAL

    def test_the_mesh_ships_position_and_normal_and_nothing_else(self, spec):
        """⚠️ Three absences with reasons, asserted rather than assumed.

        `COLOR_0`: `Q33`'s palette rule makes `materials:` the one place a city
        colour is written and `Q53` deliberately put road paint outside it, so
        an arrow's white lives in `arrows.tres`. One appearing here would mean a
        third road colour had been authored in the ETL.

        `TEXCOORD_0` / `TEXCOORD_1`: nothing reads them. The first draft shipped
        a UV of glyph-local metres that `marking_paint.gdshader` never sampled, which is
        what `Q54` found `COLOR_0.a` had been doing, and it cost 59 KB.
        """
        mesh = _built(spec)
        assert mesh.colours is None
        assert mesh.uvs is None
        assert mesh.uv2 is None


def _built(spec, movements=("ahead",), length_m=4.0):
    builder = _Builder()
    for polygon in glyph_polygons(spec, movements, length_m):
        plan = _place(polygon, 0.0, 0.0, 0.0)
        builder.polygon(plan, np.zeros(len(plan)))
    mesh = builder.build("arrows")
    assert mesh is not None
    return mesh


class TestTheReport:
    def test_a_distribution_publishes_its_tail(self):
        """p90/p99/max rather than p10/p50/p90.

        Every distribution this stage publishes is a residual whose tail is the
        finding: a median near zero is also what a wholly broken join looks
        like, if most of its symbols sit on straight streets.
        """
        measured = ArrowReport.measured([0.0] * 99 + [90.0])
        assert measured["p50"] == pytest.approx(0.0)
        assert measured["max"] == pytest.approx(90.0)
        assert measured["n"] == 100

    def test_an_empty_distribution_publishes_nothing_rather_than_a_zero(self):
        """A zero would read as "measured, and it was fine"."""
        assert ArrowReport.measured([]) == {}


class TestTheBlockIsOptional:
    def test_a_city_without_arrows_still_loads(self, tmp_path):
        assert city_with(tmp_path, None).arrows is None


class TestConfigRefusals:
    """What the loader refuses, and why each would otherwise ship."""

    def test_a_movement_the_pipeline_cannot_draw_is_refused(self, tmp_path):
        block = {**BLOCK, "glyphs": {"1017": {"movements": ["u_turn"], "length_m": 4.0}}}
        with pytest.raises(ValueError, match="u_turn"):
            city_with(tmp_path, block)

    def test_a_glyph_with_no_movements_is_refused(self, tmp_path):
        block = {**BLOCK, "glyphs": {"1017": {"movements": [], "length_m": 4.0}}}
        with pytest.raises(ValueError, match="pointing nowhere"):
            city_with(tmp_path, block)

    def test_a_repeated_movement_is_refused_rather_than_deduped(self, tmp_path):
        """A duplicate draws the same head twice in the same place — invisible,
        and the mesh silently heavier. It means the table was transcribed
        wrong, and the rest of that row is then suspect."""
        block = {**BLOCK, "glyphs": {"1017": {"movements": ["left", "left"], "length_m": 4.0}}}
        with pytest.raises(ValueError, match="repeats a movement"):
            city_with(tmp_path, block)

    def test_a_head_longer_than_its_arrow_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="head_length_frac"):
            city_with(tmp_path, {**BLOCK, "head_length_frac": 1.5})

    def test_a_stem_wider_than_its_head_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="not a head"):
            city_with(tmp_path, {**BLOCK, "stem_width_frac": 0.9})

    def test_a_bearing_tolerance_past_a_right_angle_is_refused(self, tmp_path):
        """Past 90 degrees a symbol lying square across its edge passes, which
        is the exact signature of a match to the wrong road. The check would
        still run and would refuse nothing."""
        with pytest.raises(ValueError, match="square across"):
            city_with(tmp_path, {**BLOCK, "bearing_tolerance_deg": 120.0})

    def test_paint_coplanar_with_its_road_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="z-fights"):
            city_with(tmp_path, {**BLOCK, "lift_m": 0.0})
