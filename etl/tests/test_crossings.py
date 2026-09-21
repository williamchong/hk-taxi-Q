"""`pipeline/crossings.py` — TD's surveyed crossing stripes (`P3-35g2`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import load_config
from pipeline.crossings import (
    SIGNAL,
    ZEBRA,
    Crossing,
    CrossingReport,
    _is_convex,
    cell_meshes,
    draw,
    faces_of,
)
from pipeline.drawnsurface import DrawnSurface
from pipeline.mesh import merge
from pipeline.meshbuild import CellBuilder
from pipeline.polyline import Segments
from pipeline.surface import downward_facing
from tests.helpers import CITY_YAML, polygon_area, ribbon_of

# The block as `hong_kong.yaml` declares it, held here for the reason
# `test_boxjunctions.py` gives: the block is optional by contract.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "DTAD_CROSSING_LINE",
    "fields": {"line_type": "LINETYPE", "level": "ELEVATION"},
    "line_types": ["SOLID", "NONE", "RM1076", "ZEBRA4"],
    "zebra": {
        "layer": "DTAD_RD_MARK_LINE_C",
        "fields": {"line_type": "LINETYPE", "level": "ELEVATION"},
        "codes": ["ZIGZAGL", "ZIGZAGR"],
        "within_m": 10.0,
        "line_types": ["ZEBRA4"],
    },
    "lift_m": 0.010,
    "max_offset_m": 12.0,
    "max_stripe_width_m": 1.4,
    "cell_m": 300.0,
}

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
        document["crossings"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_config(cities / "testville.yaml")


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).crossings


def stripe(x: float, width: float = 0.6, half_length: float = 1.75) -> np.ndarray:
    """One stripe across `ROAD` as a CLOSED ring, the way TD surveys most."""
    return np.array(
        [
            [x, -half_length],
            [x + width, -half_length],
            [x + width, half_length],
            [x, half_length],
            [x, -half_length],
        ]
    )


def loose(ring: np.ndarray) -> tuple[np.ndarray, ...]:
    """The same stripe as four two-vertex edges, the way TD surveys the rest."""
    return tuple(ring[index : index + 2] for index in range(len(ring) - 1))


def drawn_with(spec, crossings, zigzags=()):
    report = CrossingReport()
    builders, thin_m = draw(
        spec,
        list(crossings),
        list(zigzags),
        Segments.of([ROAD]),
        DrawnSurface.of({"caps": [], "ribbons": [ribbon_of(ROAD)]}),
        report,
    )
    meshes = {kind: pooled(kind, builder, thin_m) for kind, builder in builders.items()}
    return meshes, report


def pooled(kind, builder, thin_m):
    """A kind's cells as the one mesh they were before `P3-42`, or `None`.

    No report: `build` ASSIGNS `slivers_dropped`, so one report handed to both
    kinds keeps the last's — `cell_meshes` is what sums them.
    """
    cells = builder.build(kind, thin_m)
    if not cells:
        return None
    return replace(merge(list(cells.values()), name=kind), material=kind)


class TestAStripeIsAFaceOfItsLines:
    def test_a_closed_ring_is_one_face(self):
        rings, unclosed_m, touching = faces_of((stripe(10.0),))
        assert len(rings) == 1
        assert polygon_area(rings[0]) == pytest.approx(0.6 * 3.5)
        assert (unclosed_m, touching) == (pytest.approx(0.0, abs=1e-6), 0)

    def test_four_loose_edges_close_into_the_same_face(self):
        """367 of Wan Chai's parts are loose edges and 777 m of them are stripes."""
        rings, unclosed_m, _ = faces_of(loose(stripe(10.0)))
        assert len(rings) == 1
        assert polygon_area(rings[0]) == pytest.approx(0.6 * 3.5)
        assert unclosed_m == pytest.approx(0.0, abs=1e-6)

    def test_corners_a_millimetre_apart_still_close(self):
        edges = [edge.copy() for edge in loose(stripe(10.0))]
        edges[1][0] += 0.0004
        assert len(faces_of(tuple(edges))[0]) == 1

    def test_a_line_that_encloses_nothing_is_counted_and_not_drawn(self):
        bar = np.array([[20.0, -2.0], [20.0, 2.0]])
        rings, unclosed_m, _ = faces_of((stripe(10.0), bar))
        assert len(rings) == 1
        assert unclosed_m == pytest.approx(4.0)

    def test_a_ladder_is_seen(self):
        """🔴 Two rails and their rungs polygonise the GAPS too, which would
        paint the crossing solid. The survey never draws one; this is what
        says so if it starts."""
        rails = (np.array([[0.0, -1.0], [3.0, -1.0]]), np.array([[0.0, 1.0], [3.0, 1.0]]))
        rungs = tuple(np.array([[x, -1.0], [x, 1.0]]) for x in (0.0, 1.0, 2.0, 3.0))
        stub = (np.array([[5.0, 0.0], [7.0, 0.0]]),)
        rings, unclosed_m, touching = faces_of(rails + rungs + stub)
        assert len(rings) == 3
        assert touching > 0
        # A rung borders two faces; counted twice it would hide the stub.
        assert unclosed_m == pytest.approx(2.0)

    def test_every_face_is_wound_to_face_up(self, spec):
        reversed_ring = stripe(10.0)[::-1]
        meshes, report = drawn_with(spec, [Crossing("SOLID", (reversed_ring,))])
        assert downward_facing(meshes[SIGNAL]) == (0, 0.0)
        assert report.inverted == 0


class TestWhatIsDrawn:
    def test_the_stripe_is_drawn_at_its_surveyed_extent_and_lifted(self, spec):
        meshes, report = drawn_with(spec, [Crossing("SOLID", (stripe(10.0), stripe(11.2)))])
        mesh = meshes[SIGNAL]
        assert mesh.positions[:, 0].min() == pytest.approx(10.0)
        assert mesh.positions[:, 0].max() == pytest.approx(11.8)
        assert mesh.positions[:, 1] == pytest.approx(spec.lift_m)
        assert (report.drawn, report.stripes) == (1, 2)
        assert report.area_m2_by_kind[SIGNAL] == pytest.approx(2 * 0.6 * 3.5)

    def test_a_face_too_wide_to_be_a_stripe_is_refused(self, spec):
        """A crossing's own outline filed under a drawn line type."""
        outline = stripe(10.0, width=4.0)
        meshes, report = drawn_with(spec, [Crossing("SOLID", (outline,))])
        assert meshes[SIGNAL] is None
        assert (report.too_wide, report.no_face, report.drawn) == (1, 1, 0)

    def test_a_face_that_is_not_convex_is_refused(self, spec):
        """`FlatBuilder` fans from vertex 0 and does not test its precondition."""
        notched = np.array(
            [[10.0, -1.75], [10.6, -1.75], [10.6, 1.75], [10.3, 0.0], [10.0, 1.75], [10.0, -1.75]]
        )
        assert not _is_convex(notched[:-1])
        _, report = drawn_with(spec, [Crossing("SOLID", (notched,))])
        assert (report.not_convex, report.drawn) == (1, 0)

    def test_a_crossing_off_every_road_is_too_far(self, spec):
        away = stripe(10.0) + np.array([0.0, 40.0])
        _, report = drawn_with(spec, [Crossing("SOLID", (away,))])
        assert (report.too_far, report.drawn) == (1, 0)
        # Recorded before the refusal, so the distribution sees past its filter.
        assert len(report.nearest_edge_m) == 1

    def test_the_partitions_close(self, spec):
        crossings = [
            Crossing("SOLID", (stripe(10.0),)),
            Crossing("SOLID", (stripe(20.0, width=4.0),)),
            Crossing("SOLID", (stripe(30.0) + np.array([0.0, 40.0]),)),
        ]
        _, report = drawn_with(spec, crossings)
        assert report.drawn + report.too_far + report.no_face == len(crossings)
        assert report.faces == report.stripes + report.too_wide + report.not_convex
        assert sum(report.drawn_by_kind.values()) == report.drawn


class TestTheColourIsTheZigzags:
    ZIGZAG = np.array([[14.0, -1.0], [16.0, -0.7], [18.0, -1.0]])

    def test_a_crossing_the_zigzags_reach_is_a_zebra(self, spec):
        meshes, report = drawn_with(
            spec, [Crossing("SOLID", (stripe(10.0),))], zigzags=[self.ZIGZAG]
        )
        assert meshes[ZEBRA] is not None and meshes[SIGNAL] is None
        assert (report.zebra_by_zigzag, report.zebra_by_line_type) == (1, 0)

    def test_every_other_striped_crossing_is_a_light_signal_one(self, spec):
        meshes, report = drawn_with(
            spec, [Crossing("SOLID", (stripe(40.0),))], zigzags=[self.ZIGZAG]
        )
        assert meshes[SIGNAL] is not None and meshes[ZEBRA] is None
        assert report.drawn_by_kind == {SIGNAL: 1, ZEBRA: 0}

    def test_a_line_type_that_says_zebra_needs_no_zigzag(self, spec):
        meshes, report = drawn_with(spec, [Crossing("ZEBRA4", (stripe(10.0),))])
        assert meshes[ZEBRA] is not None
        assert (report.zebra_by_zigzag, report.zebra_by_line_type) == (0, 1)

    def test_both_sides_of_the_plateau_are_published(self, spec):
        """The furthest zebra and the nearest crossing that was not one."""
        crossings = [Crossing("SOLID", (stripe(10.0),)), Crossing("SOLID", (stripe(40.0),))]
        _, report = drawn_with(spec, crossings, zigzags=[self.ZIGZAG])
        assert report.zebra_reach_m == pytest.approx(3.4, abs=0.1)
        assert report.signal_reach_m == pytest.approx(22.0, abs=0.1)


# `ROAD`, long enough to cross a cell line and laid off the z = 0 row line.
LONG_ROAD = {**ROAD, "polyline": [[0.0, 0.0, 50.0], [600.0, 0.0, 50.0]]}


class TestTheCells:
    """`P3-42` (`Q135`): `crossings.glb` is a mesh a kind a plan cell, so the
    engine can cull it. The routing is `CellBuilder`'s (`test_roadmarks.py`);
    what is this stage's own is two kinds sharing the cells and one report."""

    ZIGZAG = np.array([[312.0, 48.25], [330.0, 48.25]])
    # `ROAD` runs along z = 0, which is a row line: a stripe across it is cut at
    # the crown and its two pieces go to two rows.
    OFF_THE_ROW_LINE = np.array([0.0, 50.0])

    def built(self, spec):
        report = CrossingReport()
        crossings = [
            Crossing("SOLID", (stripe(10.0) + self.OFF_THE_ROW_LINE,)),
            Crossing("SOLID", (stripe(450.0) + self.OFF_THE_ROW_LINE,)),
            Crossing("SOLID", (stripe(310.0) + self.OFF_THE_ROW_LINE,)),
        ]
        builders, thin_m = draw(
            spec,
            crossings,
            [self.ZIGZAG],
            Segments.of([LONG_ROAD]),
            DrawnSurface.of({"caps": [], "ribbons": [ribbon_of(LONG_ROAD)]}),
            report,
        )
        return cell_meshes(builders, thin_m, report), report

    def test_a_cell_holds_a_mesh_a_kind_each_under_its_own_material(self, spec):
        """🔴 The name carries the kind and the cell; the MATERIAL stays the
        bare kind, which is what the importer dispatches on — a cell name
        there is a stripe with no paint. `verify_crossings.gd` reads the kind
        back off the name."""
        meshes, report = self.built(spec)
        assert [(mesh.name, mesh.material) for mesh in meshes] == [
            ("crossings_signal_c0_r0", SIGNAL),
            ("crossings_signal_c1_r0", SIGNAL),
            ("crossings_zebra_c1_r0", ZEBRA),
        ]
        assert report.cells == 3
        assert report.triangles == sum(mesh.triangle_count for mesh in meshes)
        assert report.cell_triangles_max == max(mesh.triangle_count for mesh in meshes)
        assert report.cell_triangles_max < report.triangles

    def test_the_cells_union_is_the_uncut_layer(self, spec):
        cut, _ = self.built(spec)
        whole, report = self.built(replace(spec, cell_m=0.0))
        assert [mesh.name for mesh in whole] == ["crossings_signal_c0_r0", "crossings_zebra_c0_r0"]
        assert report.cells == 2

        def corners(meshes, kind):
            rows = [
                mesh.positions[mesh.triangles].reshape(-1, 9)
                for mesh in meshes
                if mesh.material == kind
            ]
            return sorted(map(tuple, np.vstack(rows)))

        for kind in (SIGNAL, ZEBRA):
            assert corners(cut, kind) == corners(whole, kind)

    def test_each_kinds_slivers_are_counted(self):
        """🔴 `build` ASSIGNS the count, so with the stage's report handed to
        both kinds the LAST kind's was what shipped — the first's needles read
        0. Mutation-check it by handing `report` to `build`."""
        needle = np.array([[0.0, 0.0], [0.0, 0.001], [20.0, 0.001], [20.0, 0.0]])
        quad = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])
        builders = {kind: CellBuilder(kind, 300.0) for kind in (SIGNAL, ZEBRA)}
        builders[SIGNAL].polygon(needle, np.zeros(4))
        builders[SIGNAL].polygon(needle + np.array([600.0, 0.0]), np.zeros(4))
        builders[ZEBRA].polygon(quad, np.zeros(4))
        report = CrossingReport()
        meshes = cell_meshes(builders, 0.05, report)
        assert report.slivers_dropped == 4
        assert [mesh.material for mesh in meshes] == [ZEBRA]

    def test_a_cell_of_no_size_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="cell_m"):
            city_with(tmp_path, {**BLOCK, "cell_m": 0.0})


class TestTheBlockIsOptional:
    def test_a_city_without_crossings_still_loads(self, tmp_path):
        assert city_with(tmp_path, None).crossings is None


class TestConfigRefusals:
    def test_line_types_are_matched_case_folded(self, spec):
        """The layer carries `SOLID` and `Solid` for one thing."""
        assert "SOLID" in spec.line_types
        assert "zigzagl".upper() in spec.zebra.codes

    def test_an_empty_line_type_list_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="draws nothing"):
            city_with(tmp_path, {**BLOCK, "line_types": []})

    def test_a_zebra_line_type_that_is_not_drawn_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="never painted"):
            city_with(tmp_path, {**BLOCK, "line_types": ["SOLID"]})

    def test_paint_coplanar_with_its_road_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="z-fights"):
            city_with(tmp_path, {**BLOCK, "lift_m": 0.0})

    def test_a_zero_zebra_reach_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="within_m"):
            city_with(tmp_path, {**BLOCK, "zebra": {**BLOCK["zebra"], "within_m": 0.0}})

    def test_a_key_nothing_reads_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="nothing reads"):
            city_with(tmp_path, {**BLOCK, "stripe_width_m": 0.6})
