"""`pipeline/roadtext.py` — TD's road lettering (`P3-21`, `Q262`)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import shapely
import yaml
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from pipeline.config import load_config
from pipeline.drawnsurface import DrawnSurface
from pipeline.mesh import merge
from pipeline.polyline import frame
from pipeline.roadtext import (
    Face,
    Legend,
    RoadTextReport,
    _host,
    cell_meshes,
    draw,
    facing,
    laid,
    legend_lines,
)
from pipeline.surface import downward_facing
from tests.helpers import CITY_YAML, ribbon_of

# The block as `hong_kong.yaml` declares it, held here because the block is
# optional by contract (`test_stopmarks.py`'s reason).
BLOCK: dict[str, Any] = {
    "source": "drawings",
    "layer": "DTAD_RD_MARK_ANNO",
    "fields": {"text": "TextString", "bearing": "Angle", "level": "ELEVATION"},
    "deck_codes": ["A01"],
    "font_source": "face",
    "font_weight": 700,
    "flatten_em": 0.02,
    "line_gap_em": 0.0,
    "refused": ["COLOURED DRESSING IN\nREDDISH BROWN"],
    "sliver_m": 0.01,
    "lift_m": 0.013,
    "max_offset_m": 12.0,
    "bearing_tolerance_deg": 20.0,
    "cell_m": 300.0,
}

# Along +X, so its heading is 90; drawn 5.12 m either side by `ribbon_of`. Its
# nearside (left of travel) is -Z, where the traffic runs the edge's own way.
ROAD = {
    "id": 0,
    "polyline": [[0.0, 0.0, 0.0], [60.0, 0.0, 0.0]],
    "lanes": 2,
    "direction": "both",
    "elevation_level": 0,
}

EM = 1000


def city_with(tmp_path, block: dict[str, Any] | None):
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["road_text"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_config(cities / "testville.yaml")


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).road_text


def _square(pen: TTGlyphPen, x0: float, y0: float, x1: float, y1: float, *, clockwise: bool):
    corners = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    if not clockwise:
        corners.reverse()
    pen.moveTo(corners[0])
    for corner in corners[1:]:
        pen.lineTo(corner)
    pen.closePath()


@pytest.fixture(scope="module")
def face(tmp_path_factory) -> Face:
    """A three-glyph TrueType face: `O` a 500 x 700 box with a 200 x 300 hole,
    `X` two boxes overlapping wound the same way — a variable font's strokes —
    and a space. TrueType winds an outer contour clockwise."""
    glyphs = {}
    pen = TTGlyphPen(None)
    glyphs[".notdef"] = pen.glyph()
    pen = TTGlyphPen(None)
    _square(pen, 0, 0, 500, 700, clockwise=True)
    _square(pen, 150, 200, 350, 500, clockwise=False)
    glyphs["O"] = pen.glyph()
    pen = TTGlyphPen(None)
    _square(pen, 0, 0, 400, 700, clockwise=True)
    _square(pen, 200, 0, 600, 700, clockwise=True)
    glyphs["X"] = pen.glyph()
    glyphs["space"] = TTGlyphPen(None).glyph()

    builder = FontBuilder(EM, isTTF=True)
    builder.setupGlyphOrder(list(glyphs))
    builder.setupCharacterMap({ord("O"): "O", ord("X"): "X", ord(" "): "space"})
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(
        {".notdef": (500, 0), "O": (600, 0), "X": (700, 0), "space": (250, 0)}
    )
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    path = tmp_path_factory.mktemp("face") / "test.ttf"
    builder.save(str(path))
    return Face(path, 700.0, 0.02)


def area(triangles: np.ndarray) -> float:
    edges_a = triangles[:, 1] - triangles[:, 0]
    edges_b = triangles[:, 2] - triangles[:, 0]
    return float(0.5 * np.abs(edges_a[:, 0] * edges_b[:, 1] - edges_a[:, 1] * edges_b[:, 0]).sum())


def legend_at(
    x: float,
    z: float,
    *,
    up_deg: float = 90.0,
    width: float = 1.0,
    height: float = 2.5,
    text: tuple[str, ...] = ("OX",),
    baseline_deg: float | None = None,
    deck: bool = False,
) -> Legend:
    """A legend whose rectangle is `width` across and `height` along `up_deg`,
    filed reading a quarter turn right of it unless told otherwise."""
    along, across = frame(up_deg)
    centre = np.array([x, z])
    ring = np.array(
        [
            centre + sx * 0.5 * width * across + sy * 0.5 * height * along
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
    )
    baseline = (up_deg + 90.0) % 360.0 if baseline_deg is None else baseline_deg
    return Legend(text, ring, baseline, deck)


def street():
    return _host([ROAD], {0: DrawnSurface.of({"caps": [], "ribbons": [ribbon_of(ROAD)]})})


class TestTheText:
    def test_the_drawings_markup_is_not_paint(self):
        raw = '<BOL><FNT name="ENGINEERING" size="4.00">BUS LANE</FNT></BOL>'
        assert legend_lines(raw) == ["BUS LANE"]

    def test_a_stacked_legend_is_its_lines_and_a_trailing_break_is_nothing(self):
        assert legend_lines("FLEET\r\nTAXI") == ["FLEET", "TAXI"]
        assert legend_lines("灣仔\r\n") == ["灣仔"]

    def test_no_string_is_no_lines(self):
        assert legend_lines(None) == []
        assert legend_lines("  ") == []


class TestTheFace:
    def test_a_counter_is_left_open(self, face):
        assert area(face.glyph("O").triangles) == pytest.approx(500 * 700 - 200 * 300)

    def test_overlapping_strokes_fill_by_winding_not_even_odd(self, face):
        """Even-odd would punch the 200-unit overlap out of the middle."""
        assert area(face.glyph("X").triangles) == pytest.approx(600 * 700)

    def test_a_character_the_face_lacks_is_named_and_a_space_never_is(self, face):
        assert face.lacks("OX Q區") == {"Q", "區"}

    def test_the_frame_is_the_advances_by_the_line_box_not_the_ink(self, face):
        """🔴 TD's rectangle is this frame: `東` and `及` file identical ones."""
        triangles, frame_box = face.block(["OX"], 0.0)
        # Advances 600 + 700, centred; the line box is ascent 800 to descent -200.
        assert frame_box == pytest.approx([-650.0, -200.0, 650.0, 800.0])
        flat = triangles.reshape(-1, 2)
        assert flat.min(axis=0) == pytest.approx([-650.0, 0.0])
        assert flat.max(axis=0) == pytest.approx([550.0, 700.0])

    def test_a_space_advances_the_pen(self, face):
        _, frame_box = face.block(["O X"], 0.0)
        assert frame_box[2] - frame_box[0] == pytest.approx(600 + 250 + 700)

    def test_line_one_is_on_top_and_the_gap_is_in_em(self, face):
        triangles, frame_box = face.block(["O", "X"], 0.25)
        # One line box (1000) and a quarter em (250) between baselines.
        assert frame_box[1] == pytest.approx(-1250.0 - 200.0)
        o_ink, x_ink = (
            triangles[: len(face.glyph("O").triangles)],
            triangles[len(face.glyph("O").triangles) :],
        )
        assert o_ink[..., 1].min() == pytest.approx(0.0)
        assert x_ink[..., 1].max() == pytest.approx(-1250.0 + 700.0)


class TestTheFacing:
    def test_the_letters_head_with_the_nearside_flow(self):
        up, residual = facing(legend_at(10.0, -3.0), 90.0)
        assert up == pytest.approx(90.0) and residual == pytest.approx(0.0)

    def test_a_legend_the_drawing_reads_upside_down_is_turned_to_the_traffic(self):
        """`FlipAngle` turns the plan's text upright: TD's angle is right
        modulo 180 only."""
        up, _ = facing(legend_at(10.0, -3.0, baseline_deg=0.0), 90.0)
        assert up == pytest.approx(90.0)

    def test_the_far_kerbs_letters_face_the_other_way(self):
        up, _ = facing(legend_at(10.0, 3.0), 270.0)
        assert up == pytest.approx(270.0)

    def test_the_residual_is_tds_axis_against_the_flow(self):
        _, residual = facing(legend_at(10.0, -3.0, up_deg=100.0), 90.0)
        assert residual == pytest.approx(10.0)


class TestTheLay:
    def test_the_frame_fills_the_rectangle_and_the_ink_sits_in_it(self, face):
        legend = legend_at(10.0, -3.0, width=1.3, height=2.5)
        plan, height = laid(legend, 90.0, *face.block(["OX"], 0.0))
        flat = plan.reshape(-1, 2)
        # Heading 90 is +X: the letters' height runs along X, their width along
        # Z. 1 frame unit is 1.3 / 1300 m across and 2.5 / 1000 m along; the
        # frame's middle is (0, 300), so the ink's 0..700 lands at -0.75..1.0.
        assert flat.min(axis=0) == pytest.approx([9.25, -3.65])
        assert flat.max(axis=0) == pytest.approx([11.0, -2.45])
        assert height == pytest.approx(1.75)

    def test_the_letters_read_left_to_right_for_the_driver(self, face):
        """🔴 Not mirrored: what is right of the glyph lands on the driver's
        right. Heading 90 (+X) has its right at +Z."""
        legend = legend_at(10.0, -3.0, width=1.2, height=2.5)
        plan, _ = laid(legend, 90.0, *face.block(["OX"], 0.0))
        o_ink, x_ink = (
            plan[: len(face.glyph("O").triangles)],
            plan[len(face.glyph("O").triangles) :],
        )
        assert o_ink[..., 1].mean() < x_ink[..., 1].mean()


class TestWhatIsDrawn:
    def drawn(self, spec, face, legends, decks=None):
        report = RoadTextReport()
        builder, thin = draw(spec, legends, face, street(), decks, report)
        return report, cell_meshes(builder, thin, report)

    def test_a_legend_on_the_road_is_drawn_facing_up_and_lifted(self, spec, face):
        report, meshes = self.drawn(spec, face, [legend_at(10.0, -3.0)])
        assert report.drawn == 1 and report.characters_drawn == 2
        mesh = merge(meshes, name="all")
        assert downward_facing(mesh) == (0, 0.0)
        assert mesh.positions[:, 1] == pytest.approx(spec.lift_m)
        assert report.drawn_by_text == {"OX": 1}

    def test_the_drawn_area_is_the_ink_scaled_by_the_frame(self, face, spec):
        _, meshes = self.drawn(spec, face, [legend_at(10.0, -3.0, width=1.2, height=2.5)])
        mesh = merge(meshes, name="all")
        triangles = mesh.positions[mesh.triangles][..., [0, 2]]
        ink = (500 * 700 - 200 * 300) + 600 * 700
        assert area(triangles) == pytest.approx(ink * (1.2 / 1300) * (2.5 / 1000), rel=1e-6)

    def test_a_legend_off_every_road_is_too_far(self, spec, face):
        report, _ = self.drawn(spec, face, [legend_at(10.0, -20.0)])
        assert report.too_far == 1 and report.drawn == 0

    def test_a_legend_across_the_road_is_off_axis(self, spec, face):
        report, _ = self.drawn(spec, face, [legend_at(10.0, -3.0, up_deg=0.0)])
        assert report.off_axis == 1 and report.axis_residual_deg == pytest.approx([90.0])

    def test_a_legend_past_the_drawn_kerb_is_off_the_road(self, spec, face):
        report, _ = self.drawn(spec, face, [legend_at(10.0, -8.0)])
        assert report.off_road == 1 and report.off_road_m2 > 0.0

    def test_a_deck_legend_with_no_deck_drawn_is_off_the_road(self, spec, face):
        report, _ = self.drawn(spec, face, [legend_at(10.0, -3.0, deck=True)])
        assert report.no_deck_drawn == 1 and report.off_road == 1

    def test_the_partition_closes(self, spec, face):
        legends = [
            legend_at(10.0, -3.0),
            legend_at(20.0, 3.0, up_deg=270.0),
            legend_at(30.0, -20.0),
            legend_at(40.0, -3.0, up_deg=0.0),
            legend_at(50.0, -8.0),
        ]
        report, _ = self.drawn(spec, face, legends)
        assert (report.drawn, report.too_far, report.off_axis, report.off_road) == (2, 1, 1, 1)


class TestTheBlock:
    def test_a_city_without_road_text_still_loads(self, tmp_path):
        assert city_with(tmp_path, None).road_text is None

    def test_the_block_reads_as_declared(self, spec):
        assert spec.deck_codes == ("A01",)
        assert spec.refused == frozenset({"COLOURED DRESSING IN\nREDDISH BROWN"})

    def test_a_tolerance_that_refuses_nothing_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="bearing_tolerance_deg"):
            city_with(tmp_path, {**BLOCK, "bearing_tolerance_deg": 90.0})

    def test_a_refused_string_alone_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="refused"):
            city_with(tmp_path, {**BLOCK, "refused": "NOTE"})

    def test_overlapping_lines_are_refused(self, tmp_path):
        with pytest.raises(ValueError, match="line_gap_em"):
            city_with(tmp_path, {**BLOCK, "line_gap_em": -0.1})

    def test_paint_coplanar_with_its_road_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="lift_m"):
            city_with(tmp_path, {**BLOCK, "lift_m": 0.0})


def test_the_block_shapes_survive_a_round_trip_through_shapely(face):
    """The cached triangles tile the glyph: their union is the filled outline."""
    triangles = face.glyph("O").triangles
    union = shapely.union_all([shapely.Polygon(t) for t in triangles])
    assert union.area == pytest.approx(500 * 700 - 200 * 300)
