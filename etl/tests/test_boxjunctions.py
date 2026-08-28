"""The box-junction stage (`P3-18`).

Weighted towards the *conventions* rather than the drawing, for
`test_arrows.py`'s stated reason: this is where the stage can be confidently
wrong and where nothing downstream would notice. A hatch read with the wrong
angle convention is a perfectly drawn hatch rotated inside its own border. A
ring wound the wrong way is nothing at all. A border offset outward instead of
inward paints the footway yellow and renders beautifully.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.boxjunctions import (
    BOXJUNCTIONS_MATERIAL,
    BoxJunctionReport,
    _Builder,
    _place,
    border_polygons,
    hatch_polygons,
    long_axis_deg,
)
from pipeline.config import load_city
from pipeline.fares import Segments
from pipeline.surface import DrawnSurface, downward_facing
from tests.helpers import CITY_YAML, polygon_area

# The block as `hong_kong.yaml` declares it. Held here rather than in
# `helpers.py`'s `CITY_YAML` because the block is optional by contract, and the
# fixture city's job is to prove that a city without one still builds.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "DTAD_YL_BOX_POLY",
    "fields": {
        "type": "YELLOWBOX_TYPE",
        "level": "ELEVATION",
        "hatch_a": "ANGLE1",
        "hatch_b": "ANGLE2",
    },
    "box_types": ["Yellow Box"],
    "border_width_m": 0.3,
    "hatch_width_m": 0.1,
    "hatch_spacing_m": 2.0,
    "station_m": 2.0,
    "lift_m": 0.012,
    "border_lift_m": 0.002,
    "max_offset_m": 12.0,
}


def city_with(tmp_path, block: dict[str, Any] | None):
    """`testville` carrying the given boxjunctions block, loaded through the
    real loader — the same argument `test_arrows.py`'s namesake makes."""
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["boxjunctions"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_city("testville", cities_root=cities)


@pytest.fixture
def spec(tmp_path):
    """`testville` with a boxjunctions block bolted on, parsed by the real loader."""
    return city_with(tmp_path, BLOCK).boxjunctions


def rotated(ring: np.ndarray, heading_deg: float) -> np.ndarray:
    """The ring turned by a game heading, for convention tests at odd angles."""
    heading = math.radians(heading_deg)
    forward = np.array([math.sin(heading), -math.cos(heading)])
    right = np.array([math.cos(heading), math.sin(heading)])
    return ring[:, :1] * right + ring[:, 1:2] * forward


# An L: the smallest ring that exercises the concave paths. Four of the
# region's twenty boxes are concave, at up to 106 vertices.
L_SHAPE = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 4.0], [4.0, 4.0], [4.0, 10.0], [0.0, 10.0]])


def contains(ring: np.ndarray, point: np.ndarray) -> bool:
    """Ray-cast containment, used to check pieces stay inside their ring."""
    inside = False
    for index in range(len(ring)):
        a, b = ring[index], ring[(index + 1) % len(ring)]
        if (a[1] > point[1]) != (b[1] > point[1]):
            crossing = a[0] + (point[1] - a[1]) / (b[1] - a[1]) * (b[0] - a[0])
            if point[0] < crossing:
                inside = not inside
    return inside


class TestTheHatchConvention:
    """`ANGLE1` is a mathematical angle, and the derivation is graded mod 90."""

    @pytest.mark.parametrize(
        ("angle_deg", "expected_heading_deg"),
        [
            # ANGLE 0 is east, which is heading 90 clockwise from north — the
            # same table `test_arrows.py` pins, because it is the same column
            # convention on the same geodatabase.
            (0.0, 90.0),
            (90.0, 0.0),
            (180.0, 270.0),
            (270.0, 180.0),
        ],
    )
    def test_a_published_angle_reads_as_a_game_heading(self, angle_deg, expected_heading_deg):
        assert (90.0 - angle_deg) % 360.0 == pytest.approx(expected_heading_deg)

    def test_the_long_axis_is_the_long_axis(self):
        """An east-west rectangle's long axis is heading 90, whatever the
        vertex order — the derivation the 16 silent boxes ship with."""
        rectangle = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 4.0], [0.0, 4.0]])
        assert long_axis_deg(rectangle) == pytest.approx(90.0)
        assert long_axis_deg(rectangle[::-1]) == pytest.approx(90.0)

    def test_the_long_axis_survives_rotation(self):
        """Checked at an odd angle because a sign error in one axis of the
        frame survives an axis-aligned test."""
        rectangle = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 4.0], [0.0, 4.0]])
        turned = rotated(rectangle, 37.0)
        # Heading 90 turned by 37 is 127, modulo the axis fold at 180.
        assert long_axis_deg(turned) == pytest.approx(127.0, abs=1e-6)

    def test_the_residual_folds_at_90_so_the_two_hatch_directions_coincide(self):
        """An orthogonal two-direction hatch field is invariant under 90 deg —
        every published `ANGLE2` is its `ANGLE1` + 90, so a residual that did
        not fold would call half the published pairs wrong by exactly 90."""
        for derived, published in ((45.0, 135.0), (10.0, 100.0), (170.0, 80.0)):
            gap = abs(derived - published) % 90.0
            assert min(gap, 90.0 - gap) == pytest.approx(0.0)


class TestTheGeometry:
    def test_a_concave_ring_hatches_up_facing_at_any_heading(self, spec):
        """⚠️ The failure this catches renders as *nothing*.

        `cull_back` decides visibility by winding, and the ear clip walks a
        ring whose published orientation is not trusted — so the whole chain is
        checked, at several headings, through the same `downward_facing` the
        manifest's `inverted` counter uses.
        """
        for heading_deg in (0.0, 37.0, 90.0, 180.0, 271.0):
            ring = rotated(L_SHAPE, heading_deg)
            builder = _Builder()
            for piece in hatch_polygons(ring, heading_deg + 45.0, spec):
                builder.polygon(piece, np.zeros(len(piece)))
            mesh = builder.build("boxjunctions")
            assert mesh is not None
            assert downward_facing(mesh) == (0, 0.0)

    def test_the_hatch_stays_inside_its_ring(self, spec):
        """Concavity is the trap: a hatch clipped to the convex hull instead of
        the ring would stripe the notch of the L, which on a real junction is
        the footway."""
        for piece in hatch_polygons(L_SHAPE, 45.0, spec):
            centre = piece.mean(axis=0)
            assert contains(L_SHAPE, centre), f"hatch piece at {centre} is outside the ring"

    def test_the_hatch_covers_the_fraction_the_dimensions_say(self, spec):
        """Two stripe fields at width/spacing cover ~2 x 0.1 / 2.0 of the box.

        Coarse on purpose — crossings double-count and edges clip — but a
        mirrored clip or a dropped stripe field misses it by far more than the
        tolerance.
        """
        square = np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]])
        pieces = hatch_polygons(square, 45.0, spec)
        area = sum(polygon_area(piece) for piece in pieces)
        expected = 400.0 * 2.0 * spec.hatch_width_m / spec.hatch_spacing_m
        assert area == pytest.approx(expected, rel=0.15)

    def test_a_long_stripe_is_cut_at_stations(self, spec):
        """A stripe longer than `station_m` gets intermediate vertices — the
        subdivision that lets it follow the crown instead of chording it."""
        square = np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]])
        for piece in hatch_polygons(square, 45.0, spec):
            span = piece.max(axis=0) - piece.min(axis=0)
            reach = float(np.hypot(span[0], span[1]))
            assert reach <= spec.station_m * math.sqrt(2.0) + 1e-6

    def test_the_border_lies_between_the_ring_and_its_inset(self, spec):
        """The boundary line is inward of the ring, never outward — outward
        would paint the footway, and it would render perfectly."""
        square = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
        report = BoxJunctionReport()
        quads = border_polygons(square, spec, report)
        assert report.degenerate_border_segments == 0
        assert quads
        for quad in quads:
            assert quad[:, 0].min() >= -1e-9 and quad[:, 0].max() <= 10.0 + 1e-9
            assert quad[:, 1].min() >= -1e-9 and quad[:, 1].max() <= 10.0 + 1e-9
            builder = _Builder()
            builder.polygon(quad, np.zeros(len(quad)))
            mesh = builder.build("boxjunctions")
            assert mesh is not None
            assert downward_facing(mesh) == (0, 0.0)

    def test_a_tab_tighter_than_the_border_is_dropped_and_counted(self, spec):
        """A protrusion narrower than twice the border width has no room for
        the offset — its tip's inner edge crosses itself. The crossed segment
        is refused rather than repaired, and the count is the only sign of it.
        The region's curved rings hit this seven times."""
        tabbed = np.array(
            [
                [0.0, 0.0],
                [10.0, 0.0],
                [10.0, 10.0],
                [5.2, 10.0],
                [5.2, 12.0],
                [4.8, 12.0],
                [4.8, 10.0],
                [0.0, 10.0],
            ]
        )
        report = BoxJunctionReport()
        border_polygons(tabbed, spec, report)
        assert report.degenerate_border_segments > 0

    def test_a_polygon_takes_the_grade_of_the_road_under_it(self, spec):
        """Per-vertex heights off the snap, plus the lift — a box across a
        crown must bend with it, because `lift_m` is 12 mm and a chorded end
        would sit under the road."""
        sloped = {
            "id": 0,
            "polyline": [[0.0, 0.0, 0.0], [20.0, 2.0, 0.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        segments = Segments.of([sloped])
        builder = _Builder()
        polygon = np.array([[2.0, -1.0], [18.0, -1.0], [18.0, 1.0], [2.0, 1.0]])
        # No caps: the ribbon alone, which is the case this test is about.
        drawn = DrawnSurface.of(segments, {"caps": []})
        _place(builder, drawn, polygon, spec.lift_m, BoxJunctionReport())
        mesh = builder.build("boxjunctions")
        assert mesh is not None
        heights = mesh.positions[:, 1]
        assert heights.max() > heights.min() + 1.0
        assert heights.min() >= spec.lift_m - 1e-9

    def test_the_paint_follows_the_cap_and_not_the_centrelines(self, spec):
        """🔴 The defect `Q92` fixed, at the level this stage owns it.

        Two arms of one junction extrapolate their own grade into the cap and
        disagree where they meet — a measured 0.43 m in region. What is *drawn*
        between them is `surface.py`'s cap, fanned from its ring's centroid, and
        that fan stands above the centrelines it spans. Placing paint on the
        blend of those centrelines put **23.2% of this mesh under the asphalt**,
        so the vertices must take the cap's height and not the arms'.
        """
        low = {
            "id": 0,
            "polyline": [[-10.0, 0.0, -4.0], [10.0, 0.0, -4.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        high = {
            "id": 1,
            "polyline": [[-10.0, 0.4, 4.0], [10.0, 0.4, 4.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        segments = Segments.of([low, high])
        # A cap standing 0.5 m over both arms — higher than any blend of them
        # could ever reach, so the two models cannot be confused here.
        cap = {
            "level": 0,
            "ring": [
                [-5.0, 0.5, -4.0],
                [5.0, 0.5, -4.0],
                [5.0, 0.5, 4.0],
                [-5.0, 0.5, 4.0],
            ],
        }
        drawn = DrawnSurface.of(segments, {"caps": [cap]})
        builder = _Builder()
        report = BoxJunctionReport()
        polygon = np.array([[-2.0, -2.0], [2.0, -2.0], [2.0, 2.0], [-2.0, 2.0]])
        _place(builder, drawn, polygon, spec.lift_m, report)
        mesh = builder.build("boxjunctions")
        assert mesh is not None
        assert mesh.positions[:, 1] == pytest.approx(0.5 + spec.lift_m)
        # And the tripwire says the cap was what answered.
        assert report.vertices_drawn == 4
        assert report.vertices_over_cap == 4

    def test_a_stage_with_no_caps_falls_back_to_the_ribbon_and_says_so(self, spec):
        """⚠️ The way this fix reverts silently, pinned.

        A `roadsurface.json` that stops publishing `caps` leaves every vertex on
        the nearest centreline — which is what shipped before `Q92` — with both
        partitions still closing and `inverted` still 0. `vertices_over_cap` is
        the only thing that says so, which is why it must reach zero here rather
        than being a count that cannot.
        """
        arm = {
            "id": 0,
            "polyline": [[-10.0, 1.0, 0.0], [10.0, 1.0, 0.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        drawn = DrawnSurface.of(Segments.of([arm]), {"caps": []})
        builder = _Builder()
        report = BoxJunctionReport()
        _place(builder, drawn, np.array([[-2.0, -1.0], [2.0, -1.0], [0.0, 1.0]]), 0.012, report)
        assert report.vertices_drawn == 3
        assert report.vertices_over_cap == 0

    def test_a_cap_on_another_level_is_not_the_road_under_this_paint(self, spec):
        """⚠️ Level 0 only, the restriction every snap in the pipeline makes.

        A flyover's cap sits directly over a street's junction in plan. Reading
        it would put the box junction on the deck overhead.
        """
        arm = {
            "id": 0,
            "polyline": [[-10.0, 0.0, 0.0], [10.0, 0.0, 0.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        overhead = {
            "level": 1,
            "ring": [[-5.0, 9.0, -4.0], [5.0, 9.0, -4.0], [5.0, 9.0, 4.0], [-5.0, 9.0, 4.0]],
        }
        drawn = DrawnSurface.of(Segments.of([arm]), {"caps": [overhead]}, level=0)
        assert drawn.cap_height_at(0.0, 0.0) is None
        assert drawn.height_at(0.0, 0.0) == pytest.approx(0.0)


class TestTheMeshContract:
    def test_the_mesh_names_the_material_the_engine_dispatches_on(self, spec):
        assert _built(spec).material == BOXJUNCTIONS_MATERIAL

    def test_the_mesh_ships_position_and_normal_and_nothing_else(self, spec):
        """⚠️ The same three absences `test_arrows.py` asserts, with the same
        reasons: the yellow lives in `boxjunctions.tres` (`Q53` kept paint out
        of `materials:`), and a channel earns its place when something reads
        it."""
        mesh = _built(spec)
        assert mesh.colours is None
        assert mesh.uvs is None
        assert mesh.uv2 is None


def _built(spec):
    builder = _Builder()
    for piece in hatch_polygons(L_SHAPE, 45.0, spec):
        builder.polygon(piece, np.zeros(len(piece)))
    mesh = builder.build("boxjunctions")
    assert mesh is not None
    return mesh


class TestTheReport:
    def test_a_distribution_publishes_its_tail(self):
        """`ArrowReport.measured`, reused rather than restated — every
        distribution here is a residual whose tail is the finding."""
        measured = BoxJunctionReport.measured([0.0] * 99 + [90.0])
        assert measured["p50"] == pytest.approx(0.0)
        assert measured["max"] == pytest.approx(90.0)
        assert measured["n"] == 100

    def test_an_empty_distribution_publishes_nothing_rather_than_a_zero(self):
        assert BoxJunctionReport.measured([]) == {}


class TestTheBlockIsOptional:
    def test_a_city_without_boxjunctions_still_loads(self, tmp_path):
        assert city_with(tmp_path, None).boxjunctions is None


class TestConfigRefusals:
    """What the loader refuses, and why each would otherwise ship."""

    def test_an_empty_type_list_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="draws nothing"):
            city_with(tmp_path, {**BLOCK, "box_types": []})

    def test_a_hatch_wider_than_its_spacing_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="fill"):
            city_with(tmp_path, {**BLOCK, "hatch_width_m": 2.5})

    def test_a_negative_width_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="border_width_m"):
            city_with(tmp_path, {**BLOCK, "border_width_m": -0.3})

    def test_paint_coplanar_with_its_road_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="z-fights"):
            city_with(tmp_path, {**BLOCK, "lift_m": 0.0})

    def test_a_border_coplanar_with_its_hatch_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="border_lift_m"):
            city_with(tmp_path, {**BLOCK, "border_lift_m": 0.0})

    def test_a_zero_snap_bar_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="max_offset_m"):
            city_with(tmp_path, {**BLOCK, "max_offset_m": 0.0})
