"""`pipeline/stopmarks.py` — TD's surveyed stop and stand paint (`P3-89`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import load_config
from pipeline.drawnsurface import DrawnSurface
from pipeline.mesh import merge
from pipeline.polyline import Segments
from pipeline.stopmarks import (
    KINDS,
    Marking,
    StopMarkReport,
    Symbol,
    band_quads,
    cell_meshes,
    draw,
    glyph_of,
    painted_runs,
    stand_symbols,
)
from pipeline.surface import downward_facing
from tests.helpers import CITY_YAML, polygon_area, ribbon_of

WHITE, YELLOW = KINDS["white"], KINDS["yellow"]

LINE = {"layer": "DTAD_RD_MARK_LINE_C", "fields": {"code": "LINETYPE", "level": "ELEVATION"}}
SYMBOL = {"layer": "DTAD_RD_MARK_SYM_LINE", "fields": {"code": "REFNAME", "level": "ELEVATION"}}

# The block as `hong_kong.yaml` declares it, held here for the reason
# `test_boxjunctions.py` gives: the block is optional by contract.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "legend_stroke_m": 0.12,
    "lift_m": 0.013,
    "max_offset_m": 12.0,
    "cell_m": 300.0,
    "marks": [
        {
            **LINE,
            "id": "bus_stop_box",
            "codes": ["RM1048"],
            "line_width_m": 0.1,
            "module": [["white", 1.0], ["none", 1.0]],
        },
        {
            **LINE,
            "id": "stand_box",
            "codes": ["RM1049"],
            "line_width_m": 0.1,
            "module": [["yellow", 1.0], ["white", 1.0]],
        },
        {
            **LINE,
            "id": "tram_stop_line",
            "codes": ["RM1045"],
            "line_width_m": 0.3,
            "paint": "yellow",
        },
        {
            **SYMBOL,
            "id": "legend",
            "codes": ["1047"],
            "legend": True,
            "paint": "white",
            "symbols": {
                "layer": "DTAD_RD_MARK_SYM_PT",
                "fields": {"code": "REFNAME", "bearing": "ANGLE", "level": "ELEVATION"},
                "turn_deg": 0.0,
            },
        },
    ],
}

# Drawn 5.12 m either side of its centreline by `ribbon_of`.
ROAD = {
    "id": 0,
    "polyline": [[0.0, 0.0, 0.0], [60.0, 0.0, 0.0]],
    "lanes": 2,
    "direction": "both",
    "elevation_level": 0,
}


def city_with(tmp_path, block: dict[str, Any] | None):
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["stop_marks"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_config(cities / "testville.yaml")


def with_mark(index: int, **changes: Any) -> dict[str, Any]:
    marks = [dict(mark) for mark in BLOCK["marks"]]
    marks[index] = {**marks[index], **changes}
    return {**BLOCK, "marks": marks}


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).stop_marks


def mark_of(spec, mark_id: str):
    return next(mark for mark in spec.marks if mark.id == mark_id)


def along(start: float, stop: float, z: float = 3.0) -> np.ndarray:
    """A line along `ROAD`, `z` metres off its centreline."""
    return np.array([[start, z], [stop, z]])


def drawn_with(spec, markings):
    report = StopMarkReport()
    builders, thin_m = draw(
        spec,
        list(markings),
        Segments.of([ROAD]),
        DrawnSurface.of({"caps": [], "ribbons": [ribbon_of(ROAD)]}),
        report,
    )
    meshes = {}
    for kind, builder in builders.items():
        cells = builder.build(kind, thin_m)
        meshes[kind] = (
            replace(merge(list(cells.values()), name=kind), material=kind) if cells else None
        )
    return meshes, report


def area_of(mesh) -> float:
    return sum(polygon_area(mesh.positions[triangle][:, [0, 2]]) for triangle in mesh.triangles)


class TestTheModule:
    def test_a_continuous_line_is_one_run(self, spec):
        assert painted_runs(mark_of(spec, "tram_stop_line"), 4.8) == [("yellow", 0.0, 4.8)]

    def test_a_broken_line_paints_its_marks_and_leaves_its_gaps(self, spec):
        runs = painted_runs(mark_of(spec, "bus_stop_box"), 4.5)
        assert runs == [("white", 0.0, 1.0), ("white", 2.0, 3.0), ("white", 4.0, 4.5)]

    def test_an_alternating_line_is_painted_end_to_end_in_two_paints(self, spec):
        runs = painted_runs(mark_of(spec, "stand_box"), 3.0)
        assert runs == [("yellow", 0.0, 1.0), ("white", 1.0, 2.0), ("yellow", 2.0, 3.0)]

    def test_the_module_runs_through_a_corner(self, spec):
        """A box is one line round three sides: the dash does not restart at a bend."""
        bent = np.array([[0.0, 0.0], [1.5, 0.0], [1.5, 2.0]])
        quads = band_quads(mark_of(spec, "bus_stop_box"), bent)
        lengths = sorted(round(float(np.linalg.norm(quad[1] - quad[0])), 6) for _, quad in quads)
        # 0-1 on the first leg, 2-3 on the second; 1.5-2 is the gap across the corner.
        assert lengths == [1.0, 1.0]


class TestWhatIsDrawn:
    def test_a_line_is_drawn_at_its_surveyed_extent_and_width_and_lifted(self, spec):
        marking = Marking(mark_of(spec, "tram_stop_line"), (along(10.0, 14.8),))
        meshes, report = drawn_with(spec, [marking])
        mesh = meshes[YELLOW]
        assert meshes[WHITE] is None
        assert (mesh.positions[:, 0].min(), mesh.positions[:, 0].max()) == pytest.approx(
            (10.0, 14.8)
        )
        assert (mesh.positions[:, 2].min(), mesh.positions[:, 2].max()) == pytest.approx(
            (2.85, 3.15)
        )
        assert mesh.positions[:, 1] == pytest.approx(spec.lift_m)
        assert area_of(mesh) == pytest.approx(4.8 * 0.3)
        assert report.drawn_by_id == {"tram_stop_line": 1}
        assert report.paint_m_by_kind[YELLOW] == pytest.approx(4.8)

    def test_a_stand_box_is_half_yellow_and_half_white(self, spec):
        meshes, report = drawn_with(spec, [Marking(mark_of(spec, "stand_box"), (along(10, 20),))])
        assert area_of(meshes[YELLOW]) == pytest.approx(5.0 * 0.1)
        assert area_of(meshes[WHITE]) == pytest.approx(5.0 * 0.1)
        assert report.drawn_m_by_id == {"stand_box": pytest.approx(10.0)}

    def test_a_legend_stroke_is_squared_off_past_its_ends(self, spec):
        """So the strokes of a character meet at their corners."""
        meshes, _ = drawn_with(spec, [Marking(mark_of(spec, "legend"), (along(10.0, 11.0),))])
        mesh = meshes[WHITE]
        assert (mesh.positions[:, 0].min(), mesh.positions[:, 0].max()) == pytest.approx(
            (9.94, 11.06)
        )
        assert np.ptp(mesh.positions[:, 2]) == pytest.approx(spec.legend_stroke_m)

    def test_every_triangle_faces_up(self, spec):
        """Whichever way the line was digitised."""
        markings = [
            Marking(mark_of(spec, "stand_box"), (along(10.0, 20.0), along(20.0, 10.0, z=-3.0))),
            Marking(mark_of(spec, "legend"), (np.array([[30.0, 1.0], [30.5, -1.0], [31.0, 1.0]]),)),
        ]
        meshes, _ = drawn_with(spec, markings)
        for mesh in meshes.values():
            assert downward_facing(mesh)[0] == 0


class TestWhatIsRefused:
    def test_a_marking_off_every_road_is_too_far(self, spec):
        _, report = drawn_with(spec, [Marking(mark_of(spec, "stand_box"), (along(10, 20, 40.0),))])
        assert (report.too_far, report.drawn) == (1, 0)
        # Recorded before the refusal, so the distribution sees past its filter.
        assert len(report.nearest_edge_m) == 1

    def test_a_marking_past_the_drawn_kerb_is_off_the_road(self, spec):
        """Within reach of the centreline and over nothing drawn: the footway."""
        meshes, report = drawn_with(
            spec, [Marking(mark_of(spec, "tram_stop_line"), (along(10.0, 14.8, z=6.0),))]
        )
        assert meshes[YELLOW] is None
        assert (report.off_road, report.drawn) == (1, 0)
        assert report.off_road_m_by_id == {"tram_stop_line": pytest.approx(4.8)}

    def test_only_the_pieces_past_the_kerb_are_refused(self, spec):
        """A box's return to the kerb runs off the ribbon; the box is still drawn."""
        box = np.array([[10.0, 9.0], [10.0, 6.0], [10.0, 3.0], [20.0, 3.0]])
        _, report = drawn_with(spec, [Marking(mark_of(spec, "tram_stop_line"), (box,))])
        assert (report.drawn, report.off_road) == (1, 0)
        assert report.off_road_m == pytest.approx(3.0)
        assert report.paint_m_by_kind[YELLOW] == pytest.approx(13.0)

    def test_the_partition_closes(self, spec):
        mark = mark_of(spec, "stand_box")
        markings = [
            Marking(mark, (along(10.0, 20.0),)),
            Marking(mark, (along(10.0, 20.0, z=40.0),)),
            Marking(mark, (along(10.0, 20.0, z=6.0),)),
        ]
        _, report = drawn_with(spec, markings)
        assert (report.drawn, report.too_far, report.off_road) == (1, 1, 1)
        assert sum(report.drawn_by_id.values()) == report.drawn


# An "L" read by traffic heading +X on `ROAD`'s nearside (its left, -Z): the
# upright runs with the flow and the foot points to the offside.
def legend_at(x: float, z: float = -3.0, turn_deg: float = 0.0) -> tuple[np.ndarray, ...]:
    turn = np.radians(turn_deg)
    spin = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
    strokes = (np.array([[-1.0, -0.4], [1.0, -0.4]]), np.array([[-1.0, -0.4], [-1.0, 0.4]]))
    return tuple(stroke @ spin.T + np.array([x, z]) for stroke in strokes)


ONE_WAY = {0: False}


class TestALegendFiledAsAPoint:
    def glyph(self, spec, legends):
        report = StopMarkReport()
        mark = mark_of(spec, "legend")
        markings = [Marking(mark, legend) for legend in legends]
        return glyph_of(mark, markings, Segments.of([ROAD]), ONE_WAY, report), report

    def test_the_glyph_is_the_surveyed_legend_in_its_traffics_frame(self, spec):
        glyph, report = self.glyph(spec, [legend_at(10.0)])
        # `(along, across)` about the legend's middle: +X is along, +Z across.
        assert glyph[0] == pytest.approx(np.array([[-1.0, -0.4], [1.0, -0.4]]))
        assert glyph[1] == pytest.approx(np.array([[-1.0, -0.4], [-1.0, 0.4]]))
        assert report.glyph_from == {"legend": 1}

    def test_the_far_kerbs_legend_is_read_against_the_edge(self, spec):
        """A two-way street's offside traffic runs the other way, so the same
        legend turned round over there is the same glyph."""
        near, _ = self.glyph(spec, [legend_at(10.0)])
        far, _ = self.glyph(spec, [legend_at(10.0, z=3.0, turn_deg=180.0)])
        for ours, theirs in zip(near, far, strict=True):
            assert theirs == pytest.approx(ours)

    def test_a_legend_a_few_degrees_off_the_road_does_not_blur_the_glyph(self, spec):
        legends = [legend_at(10.0), legend_at(20.0, turn_deg=3.0), legend_at(30.0, turn_deg=-3.0)]
        glyph, report = self.glyph(spec, legends)
        # To the millimetre: a turned legend's middle is not quite its own.
        assert glyph[0] == pytest.approx(np.array([[-1.0, -0.4], [1.0, -0.4]]), abs=2e-3)
        assert max(report.glyph_fit_m) == pytest.approx(0.0, abs=1e-6)
        assert sorted(report.glyph_turn_deg) == pytest.approx([0.0, 3.0, 3.0], abs=1e-6)

    def test_the_commonest_layout_is_the_glyph(self, spec):
        other = (np.array([[40.0, -3.0], [41.0, -3.0], [42.0, -3.5]]),)
        _, report = self.glyph(spec, [legend_at(10.0), legend_at(20.0), other])
        assert report.glyph_from == {"legend": 2}

    def test_a_point_is_stood_as_the_glyph_at_its_own_heading(self, spec):
        mark = mark_of(spec, "legend")
        markings = [Marking(mark, legend_at(10.0))]
        report = StopMarkReport()
        # Heading 270 is -X: the legend turned round, as the far kerb's is.
        stood = stand_symbols(
            spec, markings, [Symbol(mark, 30.0, 3.0, 270.0)], Segments.of([ROAD]), ONE_WAY, report
        )
        assert report.symbols_stood == 1 and stood[0].stood
        for ours, theirs in zip(
            stood[0].lines, legend_at(30.0, z=3.0, turn_deg=180.0), strict=True
        ):
            assert ours == pytest.approx(theirs)

    def test_a_point_with_no_stroke_legend_in_the_region_is_not_stood(self, spec):
        report = StopMarkReport()
        mark = mark_of(spec, "legend")
        stood = stand_symbols(
            spec, [], [Symbol(mark, 30.0, 3.0, 90.0)], Segments.of([ROAD]), ONE_WAY, report
        )
        assert stood == [] and report.symbols_no_glyph == 1

    def test_a_stood_legend_is_drawn_and_counted_apart(self, spec):
        mark = mark_of(spec, "legend")
        markings = [Marking(mark, legend_at(10.0)), Marking(mark, legend_at(30.0), stood=True)]
        _, report = drawn_with(spec, markings)
        assert report.drawn_by_id == {"legend": 2}
        assert report.drawn_from_symbols_by_id == {"legend": 1}


class TestTheCells:
    def test_a_cell_holds_a_mesh_a_paint_each_under_its_own_material(self, spec):
        report = StopMarkReport()
        builders, thin_m = draw(
            spec,
            [Marking(mark_of(spec, "stand_box"), (along(10.0, 20.0),))],
            Segments.of([ROAD]),
            DrawnSurface.of({"caps": [], "ribbons": [ribbon_of(ROAD)]}),
            report,
        )
        meshes = cell_meshes(builders, thin_m, report)
        assert sorted(mesh.material for mesh in meshes) == sorted(KINDS.values())
        assert all(mesh.name.startswith(mesh.material + "_c") for mesh in meshes)
        assert report.cells == 2
        assert report.triangles == sum(mesh.triangle_count for mesh in meshes)
        assert report.inverted == 0


class TestTheBlock:
    def test_a_city_without_stop_marks_still_loads(self, tmp_path):
        assert city_with(tmp_path, None).stop_marks is None

    def test_a_legend_takes_the_authored_stroke(self, spec):
        assert mark_of(spec, "legend").width_m == spec.legend_stroke_m
        assert mark_of(spec, "legend").legend

    def test_symbols_on_a_line_are_refused(self, tmp_path):
        with pytest.raises(ValueError, match="a line has no glyph"):
            city_with(tmp_path, with_mark(0, symbols=BLOCK["marks"][3]["symbols"]))

    def test_a_point_code_claimed_by_two_legends_is_refused(self, tmp_path):
        # Its strokes are another layer's, so only the point layer is shared.
        twin = {**BLOCK["marks"][3], "id": "twin", "layer": "DTAD_OTHER"}
        body = {**BLOCK, "marks": [*BLOCK["marks"], twin]}
        with pytest.raises(ValueError, match="drawn twice"):
            city_with(tmp_path, body)

    def test_a_legend_with_a_line_width_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="exactly one applies"):
            city_with(tmp_path, with_mark(3, line_width_m=0.1))

    def test_a_line_without_a_width_is_refused(self, tmp_path):
        marks = [dict(mark) for mark in BLOCK["marks"]]
        del marks[0]["line_width_m"]
        with pytest.raises(ValueError, match="exactly one applies"):
            city_with(tmp_path, {**BLOCK, "marks": marks})

    def test_a_paint_and_a_module_together_are_refused(self, tmp_path):
        with pytest.raises(ValueError, match="exactly one of"):
            city_with(tmp_path, with_mark(0, paint="white"))

    def test_a_module_that_paints_nothing_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="paints nothing"):
            city_with(tmp_path, with_mark(0, module=[["none", 1.0], ["none", 1.0]]))

    def test_an_unknown_paint_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="one of"):
            city_with(tmp_path, with_mark(2, paint="red"))

    def test_a_code_claimed_twice_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="drawn twice"):
            city_with(tmp_path, with_mark(1, codes=["RM1048"]))

    def test_paint_coplanar_with_its_road_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="z-fights"):
            city_with(tmp_path, {**BLOCK, "lift_m": 0.0})

    def test_a_key_nothing_reads_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="nothing reads"):
            city_with(tmp_path, {**BLOCK, "letter_height_m": 1.6})
