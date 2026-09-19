"""Road surface mesh construction (`P1-4`).

The unit tests cover the three things that decide whether the ribbon is
drivable: the mitre that closes a joint on a bend, the boundary that refuses to
cross itself on a corner tighter than the road is wide, and the hull that fills
a junction. The integration test then builds a whole region from a hand-written
road graph and checks the acceptance criterion directly — that every arm's mouth
is covered by the cap at its junction.

The graph is the input, so unlike `P1-3` there is no geodatabase to synthesise:
the fixture below is the contract in `docs/ARCHITECTURE.md`, written out.
"""

from __future__ import annotations

import json
import struct
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pipeline import roads
from pipeline.buildings import Grid
from pipeline.config import load_config
from pipeline.drawnsurface import DrawnSurface, _fans_thin
from pipeline.gltf import read_glb, read_render
from pipeline.polyline import plan_lengths
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA
from pipeline.surface import (
    MARKING_CLASS_CAP,
    MARKING_CLASS_CARRIAGEWAY,
    MARKING_CLASS_KERB,
    MARKING_CODE_MAX,
    MARKING_KERB_ABSENT,
    MARKING_KERB_DOUBLE,
    MARKING_KERB_NONE,
    MARKING_KERB_SINGLE,
    SURFACE_COLLIDER_NAME,
    SURFACE_DIR,
    SURFACE_MANIFEST_NAME,
    SURFACE_MATERIAL,
    SURFACE_MESH_NAME,
    SurfaceReport,
    _assign_trims,
    _Builder,
    _clamped_rails,
    _deck_rims,
    _ends_by_node_and_level,
    _half_widths,
    _insert_stations,
    _kerbside,
    _Marking,
    _on_structure_length_m,
    _prepare,
    _rail_stations,
    _stub_clusters,
    boundary,
    build_region,
    dedupe,
    downward_facing,
    hull,
    mitres,
    read_surface,
    trim,
)
from tests.helpers import ribbon_of


def _line(*points: tuple[float, float, float]) -> np.ndarray:
    return np.array(points, dtype=np.float64)


class TestPolyline:
    def test_plan_length_ignores_height(self) -> None:
        """A ramp is offset by its footprint, not by its travel: a 3-4-5 climb
        is three metres of road to lay kerbs along."""
        line = _line((0.0, 0.0, 0.0), (3.0, 4.0, 0.0))
        assert plan_lengths(line)[-1] == pytest.approx(3.0)

    def test_repeated_vertices_are_dropped(self) -> None:
        line = _line((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (10.0, 0.0, 0.0))
        assert len(dedupe(line)) == 2

    def test_trimming_cuts_from_both_ends(self) -> None:
        line = _line((0.0, 0.0, 0.0), (100.0, 0.0, 0.0))
        cut = trim(line, 10.0, 25.0)

        assert cut[0][0] == pytest.approx(10.0)
        assert cut[-1][0] == pytest.approx(75.0)

    def test_a_trimmed_ramp_keeps_its_gradient(self) -> None:
        """The cut point is interpolated in Y as well as in plan, so trimming a
        junction off a slope does not flatten what is left."""
        line = _line((0.0, 0.0, 0.0), (100.0, 10.0, 0.0))
        assert trim(line, 20.0, 0.0)[0][1] == pytest.approx(2.0)

    def test_trims_that_meet_leave_nothing(self) -> None:
        line = _line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0))
        assert len(trim(line, 6.0, 6.0)) == 0


class TestMitres:
    def test_a_straight_line_offsets_by_one(self) -> None:
        offsets = mitres(_line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (20.0, 0.0, 0.0)))
        np.testing.assert_allclose(np.hypot(*offsets.T), 1.0)

    def test_the_offset_points_left_of_travel(self) -> None:
        """Not a free convention. `TEXCOORD_0` is a lane coordinate measured
        from the nearside kerb and Hong Kong drives on the left, so a flipped
        sign here mirrors every asymmetric marking the shader will draw.

        Left of travel in a Y-up right-handed frame is `up x forward`.
        """
        forward = np.array([1.0, 0.0, 0.0])
        expected = np.cross([0.0, 1.0, 0.0], forward)[[0, 2]]

        offsets = mitres(_line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0)))
        np.testing.assert_allclose(offsets[0], expected)

    def test_a_right_angle_lengthens_the_corner(self) -> None:
        """The mitre is longer than the half-width by `1 / cos(half the turn)`,
        which for a square corner is the diagonal of a unit square."""
        offsets = mitres(_line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 0.0, 10.0)))
        assert np.hypot(*offsets[1]) == pytest.approx(np.sqrt(2.0))

    def test_the_joint_closes(self) -> None:
        """The property the whole mitre exists for: the two quads meeting at a
        bend share their edge exactly, so the ribbon has no notch outside it."""
        line = _line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (20.0, 0.0, 10.0))
        offsets = mitres(line)
        corner = line[1][[0, 2]] + offsets[1] * 4.0

        for start, end in ((line[0], line[1]), (line[1], line[2])):
            span = (end - start)[[0, 2]]
            side = np.array([span[1], -span[0]]) / np.hypot(*span)
            # The corner sits on both segments' offset lines at once.
            assert np.dot(corner - start[[0, 2]], side) == pytest.approx(4.0)

    def test_a_hairpin_is_clamped_rather_than_sent_to_infinity(self) -> None:
        line = _line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 0.0, 0.01))
        assert np.hypot(*mitres(line)[1]) < 5.0


class TestBoundary:
    def test_a_straight_road_offsets_exactly(self) -> None:
        """A positive offset is the nearside boundary, so travel along +X puts
        it at -Z."""
        line = _line((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (20.0, 0.0, 0.0))
        edge = boundary(line, mitres(line), 3.0)

        np.testing.assert_allclose(edge[:, 1], -3.0)
        np.testing.assert_allclose(edge[:, 0], [0.0, 10.0, 20.0])

    def test_a_corner_tighter_than_the_road_never_runs_backwards(self) -> None:
        """A slip road off Hung Hing Road loops at a 5 m radius while the
        widened carriageway is 10.2 m across. The naive inner offset crosses
        itself there, which renders as an inverted sliver and leaves a notch in
        the collider."""
        angles = np.linspace(0.0, np.pi, 24)
        line = np.column_stack([5.0 * np.cos(angles), np.zeros(24), 5.0 * np.sin(angles)])
        step = np.diff(line[:, [0, 2]], axis=0)

        for across in (5.12, -5.12):
            edge = boundary(line, mitres(line), across)
            assert ((np.diff(edge, axis=0) * step).sum(axis=1) >= 0.0).all()

    def test_the_outer_side_of_that_corner_is_untouched(self) -> None:
        """Only the inside of a tight bend has no offset curve. Clamping both
        sides would narrow a road that has done nothing wrong."""
        angles = np.linspace(0.0, np.pi, 24)
        line = np.column_stack([5.0 * np.cos(angles), np.zeros(24), 5.0 * np.sin(angles)])

        outer = boundary(line, mitres(line), -4.0)
        # Every vertex keeps its full offset from the centreline — the mitre
        # pushes the corners slightly beyond it, and nothing is held back.
        assert (np.linalg.norm(outer - line[:, [0, 2]], axis=1) >= 4.0 - 1e-9).all()
        assert (np.linalg.norm(np.diff(outer, axis=0), axis=1) > 0.0).all()


class TestHull:
    def test_a_square_keeps_its_four_corners(self) -> None:
        points = np.array([[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 0.0, 4.0], [0.0, 0.0, 4.0]])
        assert len(hull(points)) == 4

    def test_an_interior_point_is_dropped(self) -> None:
        points = np.array(
            [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 0.0, 4.0], [0.0, 0.0, 4.0], [2.0, 0.0, 2.0]]
        )
        assert len(hull(points)) == 4

    def test_collinear_points_make_no_polygon(self) -> None:
        points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
        assert len(hull(points)) < 3

    def test_height_comes_along(self) -> None:
        """A cap on a slope follows it rather than flattening the junction."""
        points = np.array([[0.0, 1.0, 0.0], [4.0, 2.0, 0.0], [4.0, 3.0, 4.0], [0.0, 4.0, 4.0]])
        assert set(np.round(hull(points)[:, 1], 3)) == {1.0, 2.0, 3.0, 4.0}


def _plan_area(ring: np.ndarray) -> float:
    """Half the shoelace, unsigned, over `(n, 2)` plan corners."""
    return 0.5 * abs(
        float(
            np.dot(ring[:, 0], np.roll(ring[:, 1], -1))
            - np.dot(np.roll(ring[:, 0], -1), ring[:, 1])
        )
    )


class TestDrawnSurface:
    """`Q92`: the height of the road this stage drew, asked for at a point.

    🔴 **The tests that matter here are the two that would let the defect back
    in.** A query that disagrees with `_Builder.fan` puts markings under the
    asphalt again — that is what 23.2% of `boxjunctions.glb` was — and a query
    that steps where the builder is continuous rebuilds the near-vertical shards
    the old blend was written to prevent.
    """

    @staticmethod
    def _fan_of(ring: np.ndarray) -> np.ndarray:
        """The triangles `_Builder.fan` emits for this ring, as `(n, 3, 3)`."""
        builder = _Builder()
        builder.fan(
            ring,
            colour=(200, 200, 200),
            marking=_Marking(float(MARKING_CLASS_CAP), 0.0),
        )
        mesh = builder.build("cap")
        return mesh.positions[mesh.triangles]

    def test_the_query_reproduces_the_fan_the_builder_emits(self) -> None:
        """🔴 The one property that stops the reader drifting from the writer.

        `DrawnSurface` rebuilds `_Builder.fan`'s triangulation from the published
        ring rather than reading the mesh, so nothing but a test says the two
        agree. A tilted, irregular ring, because a flat one agrees under any
        interpolation at all and would pass while saying nothing.
        """
        ring = np.array(
            [
                [0.0, 1.0, 0.0],
                [10.0, 1.4, 1.0],
                [12.0, 2.2, 9.0],
                [3.0, 0.6, 11.0],
                [-2.0, 1.9, 5.0],
            ]
        )
        triangles = self._fan_of(ring)
        drawn = DrawnSurface.of(
            {"caps": [{"level": 0, "ring": [list(corner) for corner in ring]}]},
        )
        rng = np.random.default_rng(11)
        checked = 0
        for triangle in triangles:
            for _ in range(20):
                first, second = rng.random(2)
                if first + second > 1.0:
                    first, second = 1.0 - first, 1.0 - second
                point = (
                    triangle[0]
                    + first * (triangle[1] - triangle[0])
                    + second * (triangle[2] - triangle[0])
                )
                assert drawn.height_at(float(point[0]), float(point[2])) == pytest.approx(
                    float(point[1]), abs=1e-9
                )
                checked += 1
        assert checked == 20 * len(triangles)

    def test_the_cap_meets_the_ribbon_without_a_step(self) -> None:
        """⚠️ Why this needs no blend, where the model it replaced did.

        The old height model blended centrelines because a hard nearest-edge
        switch stepped by a measured 0.43 m at a junction seam and built **172
        near-vertical triangles**. Nothing here switches between arms: the cap
        ring passes through each arriving ribbon's own end corners and the
        carriageway is flat across, so the two cases carry the same height where
        they meet. Walked across the boundary rather than argued.
        """
        arm = {
            "id": 0,
            "polyline": [[0.0, 0.0, -20.0], [0.0, 0.0, -4.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        # A cap whose near edge sits on that arm's end height and whose far edge
        # is 0.4 m up — the disagreement the old blend existed to smooth.
        cap = {
            "level": 0,
            "ring": [[-5.0, 0.0, -4.0], [5.0, 0.0, -4.0], [5.0, 0.4, 4.0], [-5.0, 0.4, 4.0]],
        }
        drawn = DrawnSurface.of({"caps": [cap], "ribbons": [ribbon_of(arm)]})
        transect = [drawn.height_at(0.0, float(z)) for z in np.arange(-10.0, 4.01, 0.1)]
        assert transect[0] == pytest.approx(0.0)
        assert transect[-1] == pytest.approx(0.4)
        assert np.abs(np.diff(np.asarray(transect))).max() < 0.05

    def test_the_higher_of_a_cap_and_the_ribbon_it_covers_wins(self) -> None:
        """A cap and the arm it overlaps are both drawn; the renderer shows the
        upper one, so a marking has to clear that one."""
        arm = {
            "id": 0,
            "polyline": [[-10.0, 3.0, 0.0], [10.0, 3.0, 0.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        sunken = {
            "level": 0,
            "ring": [[-5.0, 1.0, -4.0], [5.0, 1.0, -4.0], [5.0, 1.0, 4.0], [-5.0, 1.0, 4.0]],
        }
        drawn = DrawnSurface.of({"caps": [sunken], "ribbons": [ribbon_of(arm)]})
        assert drawn.cap_height_at(0.0, 0.0) == pytest.approx(1.0)
        assert drawn.height_at(0.0, 0.0) == pytest.approx(3.0)

    def test_a_manifest_without_caps_reads_from_the_strips(self) -> None:
        """⚠️ The silent revert, pinned at the reader. A manifest that stops
        publishing caps must leave the query on the ribbon rather than raise —
        it is the *consumers'* counters that have to notice, and they can only do
        that if this returns."""
        arm = {
            "id": 0,
            "polyline": [[-10.0, 2.0, 0.0], [10.0, 2.0, 0.0]],
            "lanes": 2,
            "direction": "both",
            "elevation_level": 0,
        }
        drawn = DrawnSurface.of({"ribbons": [ribbon_of(arm)]})
        assert drawn.cap_height_at(0.0, 0.0) is None
        assert drawn.height_at(0.0, 0.0) == pytest.approx(2.0)

    def test_a_manifest_that_draws_nothing_is_refused(self) -> None:
        """No caps and no ribbons is not a surface with no height — it is
        `blended_height` again, and the schema bump exists so no reader sees it."""
        with pytest.raises(ValueError, match="draws nothing"):
            DrawnSurface.of({"caps": [], "ribbons": []})

    def test_the_query_reproduces_the_strip_the_builder_emits(self) -> None:
        """🔴 The rail half of the reader-drifts-from-writer property.

        `_strip_corners` rebuilds `_Builder.strip`'s quads from the published
        rails rather than reading the mesh. A bent, graded, unevenly stationed
        pair of rails whose two rails are *not* parallel and *not* level with
        each other, because on a straight flat strip either diagonal agrees and
        the test would pass while saying nothing about the diagonal.
        """
        first = np.array([[0.0, 0.0, 0.0], [10.0, 0.3, 1.0], [14.0, 0.9, 6.0], [15.0, 1.4, 12.0]])
        second = np.array([[0.0, 0.2, 8.0], [9.0, 0.7, 9.5], [12.0, 1.1, 13.0], [11.0, 1.3, 17.0]])
        builder = _Builder()
        builder.strip(
            first,
            second,
            colour=(200, 200, 200),
            along=plan_lengths(first),
            across=(2.0, 0.0),
            marking=_Marking(float(MARKING_CLASS_CARRIAGEWAY), 10.0),
        )
        mesh = builder.build("strip")
        triangles = mesh.positions[mesh.triangles]
        drawn = DrawnSurface.of(
            {"ribbons": [{"edge": 0, "level": 0, "rails": [first.tolist(), second.tolist()]}]}
        )
        rng = np.random.default_rng(7)
        checked = 0
        for triangle in triangles:
            for _ in range(20):
                a, b = rng.random(2)
                if a + b > 1.0:
                    a, b = 1.0 - a, 1.0 - b
                point = (
                    triangle[0] + a * (triangle[1] - triangle[0]) + b * (triangle[2] - triangle[0])
                )
                assert drawn.height_at(float(point[0]), float(point[2])) == pytest.approx(
                    float(point[1]), abs=1e-9
                )
                checked += 1
        assert checked == 20 * len(triangles)
        # ⚠️ And the other diagonal is a different surface: swapping the rails
        # flips every quad's diagonal, and a point off the diagonal reads a
        # different plane. Without this the test above cannot tell a
        # `_strip_corners` written to the wrong triple from the right one.
        swapped = DrawnSurface.of(
            {"ribbons": [{"edge": 0, "level": 0, "rails": [second.tolist(), first.tolist()]}]}
        )
        assert swapped.height_at(11.5, 5.0) != pytest.approx(drawn.height_at(11.5, 5.0), abs=1e-6)

    def test_the_ribbon_that_covers_the_point_answers_not_the_nearer_centreline(self) -> None:
        """🔴 HKCEC's six buried triangles (`P3-32`'s residue).

        Two parallel ribbons: a narrow one whose centreline is nearer the point
        but whose rails stop short of it, and a wide one 0.3 m higher that
        actually covers it. The old reader took the nearest centreline and put
        the paint 2.6 cm under the wide ribbon.
        """
        narrow = {"id": 0, "polyline": [[-50.0, 0.0, 0.0], [50.0, 0.0, 0.0]], "elevation_level": 0}
        wide = {"id": 1, "polyline": [[-50.0, 0.3, 13.0], [50.0, 0.3, 13.0]], "elevation_level": 0}
        drawn = DrawnSurface.of(
            {"ribbons": [ribbon_of(narrow, half_width_m=5.0), ribbon_of(wide, half_width_m=7.5)]}
        )
        # z = 6.0: 6 m from the narrow centreline (rails stop at 5), 7 m from
        # the wide one (rails reach 5.5).
        here = drawn.sample(0.0, 6.0)
        assert here.ribbon_m == pytest.approx(0.3)
        assert here.height_m == pytest.approx(0.3)
        assert here.reach_m == 0.0

    def test_a_point_over_nothing_drawn_takes_the_nearest_drawn_edge(self) -> None:
        """🔴 HUNG HING ROAD's four (`P3-32`'s residue).

        A vertex in the gap beside a flank: 0.17 m from the flank's edge and
        7.8 m from another carriageway's centreline. The old reader took that
        centreline's height, 8.8 cm under the flank. Now the nearest drawn
        edge answers — the flank's — and the reach says how far it was.
        """
        far = {"id": 0, "polyline": [[-50.0, 4.30, 0.0], [50.0, 4.30, 0.0]], "elevation_level": 0}
        flank = {
            "level": 0,
            "ring": [[-1.0, 4.384, 8.0], [1.0, 4.384, 8.0], [1.0, 4.384, 9.0], [-1.0, 4.384, 9.0]],
        }
        drawn = DrawnSurface.of({"caps": [flank], "ribbons": [ribbon_of(far, half_width_m=5.0)]})
        here = drawn.sample(0.0, 7.83)
        assert here.over_void
        assert here.height_m == pytest.approx(4.384)
        assert here.reach_m == pytest.approx(0.17)
        # A point nearer the ribbon's rail than the flank takes the rail.
        assert drawn.sample(0.0, 5.2).height_m == pytest.approx(4.30)
        # And a point beyond a ribbon's END snaps to its end line, not to a
        # rail extended to infinity.
        beyond = drawn.sample(60.0, 0.0)
        assert beyond.over_void
        assert beyond.height_m == pytest.approx(4.30)
        assert beyond.reach_m == pytest.approx(10.0)

    def test_the_nearest_edge_search_widens_until_nothing_unseen_can_be_nearer(self) -> None:
        """The ring search stops on an exact bound, so a far edge is found
        across many empty cells and the answer is the true nearest edge."""
        arm = {"id": 0, "polyline": [[0.0, 1.0, 0.0], [10.0, 1.0, 0.0]], "elevation_level": 0}
        drawn = DrawnSurface.of({"ribbons": [ribbon_of(arm, half_width_m=2.0)]})
        here = drawn.sample(300.0, 200.0)
        assert here.over_void
        assert here.height_m == pytest.approx(1.0)
        assert here.reach_m == pytest.approx(np.hypot(290.0, 198.0))

    # `Q92`'s chord residue: BULLOCK LANE's cap ring as `roadsurface.json`
    # published it (box 1, Wan Chai), whose corners alternate 4.324 / 4.404 m
    # about an apex at 4.323 — so every spoke to a 4.404 corner is a ridge, and
    # a flat piece across two of them chords under the fan.
    _CREASED_RING = np.array(
        [
            [386.544, 4.242, 792.174],
            [396.698, 4.324, 791.248],
            [397.745, 4.404, 801.352],
            [397.672, 4.324, 801.442],
            [387.568, 4.404, 802.489],
            [387.43, 4.242, 802.376],
        ]
    )
    # A 0.1 m hatch stripe across that fan at the heading that chords deepest —
    # 4.3 cm — found by scanning headings through the apex.
    _CHORDING_STRIPE = np.array(
        [[388.278, 797.803], [395.796, 800.539], [395.761, 800.633], [388.244, 797.897]]
    )

    @staticmethod
    def _interior_points(polygon: np.ndarray, count: int, seed: int) -> np.ndarray:
        """Random points inside a convex plan polygon, by its fan."""
        rng = np.random.default_rng(seed)
        fan = np.stack(
            [np.broadcast_to(polygon[0], polygon[1:-1].shape), polygon[1:-1], polygon[2:]], axis=1
        )
        picks = rng.integers(0, len(fan), count)
        first, second = rng.random(count), rng.random(count)
        flip = first + second > 1.0
        first[flip], second[flip] = 1.0 - first[flip], 1.0 - second[flip]
        base = fan[picks]
        return (
            base[:, 0]
            + first[:, None] * (base[:, 1] - base[:, 0])
            + second[:, None] * (base[:, 2] - base[:, 0])
        )

    @staticmethod
    def _chord_gap(drawn: DrawnSurface, piece: np.ndarray, points: np.ndarray) -> np.ndarray:
        """Flat paint with its corners on the drawn road, minus the road, at
        each plan point of the piece: negative is paint under the asphalt."""
        heights = np.array([drawn.height_at(float(x), float(z)) for x, z in piece])
        # The plane through the fan's first triangle, which is the piece's plane
        # only if the piece is planar — every piece a split returns is judged
        # on the fan `FlatBuilder.polygon` will actually emit.
        gaps = []
        for x, z in points:
            fan = np.stack(
                [np.broadcast_to(piece[0], piece[1:-1].shape), piece[1:-1], piece[2:]], axis=1
            )
            fan_heights = np.stack(
                [np.broadcast_to(heights[0], heights[1:-1].shape), heights[1:-1], heights[2:]],
                axis=1,
            )
            for corners, tops in zip(fan, fan_heights, strict=True):
                a, b, c = corners
                det = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                if abs(det) < 1e-12:
                    continue
                beta = ((x - a[0]) * (c[1] - a[1]) - (z - a[1]) * (c[0] - a[0])) / det
                gamma = ((b[0] - a[0]) * (z - a[1]) - (b[1] - a[1]) * (x - a[0])) / det
                if beta >= -1e-9 and gamma >= -1e-9 and beta + gamma <= 1.0 + 1e-9:
                    paint = tops[0] + beta * (tops[1] - tops[0]) + gamma * (tops[2] - tops[0])
                    gaps.append(paint - drawn.height_at(float(x), float(z)))
                    break
        return np.asarray(gaps)

    def test_a_split_piece_never_chords_under_the_fan_it_lies_on(self) -> None:
        """🔴 `Q92`'s chord residue, closed by construction rather than by a
        height.

        A hatch piece across BULLOCK LANE's creased cap read 10-12 mm under the
        road with every corner on it. Cut along the spokes it crosses, every
        piece lies within one fan triangle and is coplanar with it. The
        mutation is in the same test: the *uncut* piece must read under the
        fan somewhere, or the fixture proves nothing.
        """
        drawn = DrawnSurface.of(
            {"caps": [{"level": 0, "ring": [list(corner) for corner in self._CREASED_RING]}]}
        )
        stripe = self._CHORDING_STRIPE
        whole = self._chord_gap(drawn, stripe, self._interior_points(stripe, 400, 3))
        assert whole.min() < -0.01, "the fixture has no fold to chord under"

        pieces = drawn.split(stripe)
        assert len(pieces) > 1
        assert sum(_plan_area(piece) for piece in pieces) == pytest.approx(_plan_area(stripe))
        for piece in pieces:
            gaps = self._chord_gap(drawn, piece, self._interior_points(piece, 60, 5))
            assert gaps.min() > -1e-9

    def test_a_split_piece_never_chords_under_a_strip_diagonal(self) -> None:
        """The other fold: a strip quad on a bend and a grade is not planar, so
        `_Builder.strip`'s diagonal is a crease too, and a band quad astride it
        chords under one of the two triangles."""
        bend = {
            "id": 0,
            "polyline": [[0.0, 0.0, 0.0], [10.0, 0.6, 0.0], [16.0, 0.6, 6.0]],
            "elevation_level": 0,
        }
        drawn = DrawnSurface.of({"ribbons": [ribbon_of(bend, half_width_m=4.0)]})
        quad = np.array([[9.0, -3.0], [11.5, -3.0], [11.5, 3.0], [9.0, 3.0]])
        whole = self._chord_gap(drawn, quad, self._interior_points(quad, 400, 7))
        assert whole.min() < -1e-4, "the fixture has no fold to chord under"
        for piece in drawn.split(quad):
            gaps = self._chord_gap(drawn, piece, self._interior_points(piece, 60, 9))
            assert gaps.min() > -1e-9

    def test_a_polygon_no_crease_crosses_comes_back_as_itself(self) -> None:
        """The common case, and the one the counters read as 'not split'."""
        flat = {"id": 0, "polyline": [[0.0, 1.0, 0.0], [10.0, 1.0, 0.0]], "elevation_level": 0}
        drawn = DrawnSurface.of({"ribbons": [ribbon_of(flat, half_width_m=4.0)]})
        # Inside one strip triangle: the diagonal runs corner to corner and
        # this sits in the half below it.
        small = np.array([[1.0, -3.5], [3.0, -3.5], [3.0, -3.0]])
        pieces = drawn.split(small)
        assert len(pieces) == 1
        assert pieces[0] is small

    def test_a_cut_that_would_leave_a_sliver_is_not_made(self) -> None:
        """⚠️ Measured: cutting regardless lost 1.96% of the box paint's plan
        area, because a fold within the builder's sliver bar of a stripe's edge
        cut off a strip the builder then dropped. With the bar handed in, that
        cut is refused and the stripe is placed whole."""
        drawn = DrawnSurface.of(
            {"caps": [{"level": 0, "ring": [list(corner) for corner in self._CREASED_RING]}]}
        )
        # A stripe whose long edge runs 2 cm from one spoke and across the
        # others: the cut along that spoke would leave a 2 cm strip.
        apex = self._CREASED_RING[:, [0, 2]].mean(axis=0)
        spoke = self._CREASED_RING[2, [0, 2]] - apex
        along = spoke / np.hypot(*spoke)
        across = np.array([-along[1], along[0]])
        near = apex + 0.02 * across
        stripe = np.array(
            [
                near - along,
                near + 5.0 * along,
                near + 5.0 * along + 0.3 * across,
                near - along + 0.3 * across,
            ]
        )
        cut_regardless = drawn.split(stripe)
        assert any(_fans_thin(piece, 0.05) for piece in cut_regardless)
        guarded = drawn.split(stripe, thin_m=0.05)
        assert len(guarded) < len(cut_regardless)
        assert not any(_fans_thin(piece, 0.05) for piece in guarded)
        assert sum(_plan_area(piece) for piece in guarded) == pytest.approx(_plan_area(stripe))


class TestHalfWidths:
    """`Q23`: the width a station is drawn at, and the taper between two of them.

    Unit-level because the interesting cases are shapes the region has once
    each — a taper that runs off the end of an edge, a hard-step city, an edge
    the flag never fires on — and building a mesh to see them would test the
    mesh instead.
    """

    def _published(self, station_m: float, flags: list[bool], **overrides) -> dict:
        polyline = [[station_m * step, 0.0, 0.0] for step in range(len(flags))]
        return _edge(0, 0, 1, polyline, on_structure=flags, **overrides)

    def test_a_station_on_structure_takes_the_authored_half_width(self, testville_config) -> None:
        style = testville_config.roads.surface
        published = self._published(10.0, [True, True, False, False, False])

        widths = _half_widths(published, style)

        assert widths[0] == pytest.approx(6.4 / 2.0)
        assert widths[1] == pytest.approx(6.4 / 2.0)

    def test_the_taper_finishes_before_the_structure_rather_than_across_it(
        self, testville_config
    ) -> None:
        """The decision the user made. Every flagged station is already at the
        authored width, so the first metre of deck is never over-wide — the
        blend is spent entirely on the approach."""
        style = testville_config.roads.surface
        published = self._published(5.0, [True] + [False] * 6)

        widths = _half_widths(published, style)
        at_grade, on_deck = 6.4 * 1.5 / 2.0, 6.4 / 2.0

        assert widths[0] == pytest.approx(on_deck)
        assert on_deck < widths[1] < at_grade, "5 m into a 15 m taper"
        assert widths[-1] == pytest.approx(at_grade), "30 m out, well past it"
        assert list(widths) == sorted(widths)

    def test_a_zero_taper_steps_at_the_boundary(self, testville_config) -> None:
        """The literal reading stays reachable for a city that wants it, and it
        must not divide by zero on the way."""
        style = replace(testville_config.roads.surface, structure_taper_m=0.0)
        published = self._published(5.0, [True, False, False])

        widths = _half_widths(published, style)

        assert widths[0] == pytest.approx(6.4 / 2.0)
        assert widths[1] == pytest.approx(6.4 * 1.5 / 2.0), "no blend at all"

    def test_an_edge_with_no_flag_set_is_the_constant_it_always_was(self, testville_config) -> None:
        """769 of the region's 797 edges. The taper has to be arithmetically
        inert here or `Q23` becomes a change to the whole city."""
        style = testville_config.roads.surface
        published = self._published(10.0, [False] * 5)

        widths = _half_widths(published, style)
        assert list(widths) == pytest.approx([6.4 * 1.5 / 2.0] * 5)

    def test_an_off_grade_edge_is_untouched_by_the_station_rule(self, testville_config) -> None:
        """Levels 1 and -1 are decided by their own table, which is checked
        first. `P2-7` measured them and this must not move them."""
        style = testville_config.roads.surface
        published = self._published(10.0, [True, True, False], elevation_level=1)

        widths = _half_widths(published, style)
        assert list(widths) == pytest.approx([6.4 / 2.0] * 3), "authored width along all of it"


class TestOnStructureLength:
    def test_it_measures_only_level_zero(self, testville_config) -> None:
        """An off-grade edge is on structure along its whole length by
        definition; counting it would bury the number `Q23` reports."""
        polyline = [[10.0 * step, 0.0, 0.0] for step in range(4)]
        flags = [True, True, True, True]

        edge = _edge(0, 0, 1, polyline, on_structure=flags)
        assert _on_structure_length_m(edge, "on_structure") == 30.0
        lifted = _edge(0, 0, 1, polyline, on_structure=flags, elevation_level=1)
        assert _on_structure_length_m(lifted, "on_structure") == 0.0

    def test_a_run_ending_mid_edge_counts_half_its_last_segment(self) -> None:
        """The trapezoid rule, stated so a change to it is visible rather than
        arithmetic drift in a reported figure."""
        polyline = [[10.0 * step, 0.0, 0.0] for step in range(4)]
        published = _edge(0, 0, 1, polyline, on_structure=[True, True, False, False])

        assert _on_structure_length_m(published, "on_structure") == pytest.approx(15.0)

    def test_an_edge_never_on_structure_measures_nothing(self) -> None:
        polyline = [[10.0 * step, 0.0, 0.0] for step in range(4)]
        assert _on_structure_length_m(_edge(0, 0, 1, polyline), "on_structure") == 0.0

    def test_the_same_rule_measures_Q19s_flag_and_the_two_are_independent(self) -> None:
        """One function, two flags (`Q19`). The point of the shared reduction is
        that the two lengths stay comparable; the point of this case is that
        they are read off *different* keys, so an edge walled along its whole
        length while resting on structure nowhere reports 30 m under one and
        0 m under the other. That pairing is the whole finding — `Q23`'s flag
        cannot see a ramp sampled off the terrain."""
        polyline = [[10.0 * step, 0.0, 0.0] for step in range(4)]
        walled = _edge(0, 0, 1, polyline, structure_bounded=[True] * 4)

        assert _on_structure_length_m(walled, "structure_bounded") == 30.0
        assert _on_structure_length_m(walled, "on_structure") == 0.0

    def test_a_flag_absent_from_an_older_bundle_measures_nothing(self) -> None:
        """Schema 7 and earlier published no `structure_bounded`, and the
        reduction is asked for it unconditionally. Absent must read as "nothing
        known" rather than raising, because the alternative is a stage that
        cannot open a bundle one version old."""
        polyline = [[10.0 * step, 0.0, 0.0] for step in range(4)]
        older = _edge(0, 0, 1, polyline)
        del older["structure_bounded"]

        assert _on_structure_length_m(older, "structure_bounded") == 0.0


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------


def _edge(edge_id: int, from_node: int, to_node: int, polyline, **overrides) -> dict:
    edge = {
        "id": edge_id,
        "from": from_node,
        "to": to_node,
        "polyline": polyline,
        # Off structure unless a case says otherwise, which is what a city that
        # samples no decks publishes and what every edge here means.
        "on_structure": [False] * len(polyline),
        # `Q19`'s second flag, schema 8. Published on every edge and read by
        # nothing that draws — `_half_widths` records why the narrowing it would
        # license was measured and refused — so it is here for the length
        # measurement and for the fixtures that override it.
        "structure_bounded": [False] * len(polyline),
        "direction": "both",
        "lanes": 2,
        # Schema 13 (`Q126`). `None` is the split nobody stated; `_prepare`
        # reads it without a default for the reason `offset_m` gives below.
        "lanes_forward": None,
        "width_m": 6.4,
        # Schema 9. Zero is a ribbon centred on its own centreline, which is
        # every level-0 edge and so every fixture here that does not say
        # otherwise. ⚠️ Present rather than absent: `_prepare` reads it with
        # `[]` on purpose, because `read_graph` pins the schema and a `.get`
        # default could only ever fire on a document that had stopped
        # publishing it — silently drawing every off-grade ribbon unshifted.
        "offset_m": 0.0,
        # Schema 10. The deck's two edges per vertex, and **empty is the
        # ordinary case** — every level-0 edge, and every off-grade edge the
        # deck walk could not measure. `_deck_rims` turns an empty or
        # length-mismatched list into an infinite reach, which is no constraint,
        # so a fixture that says nothing here draws the ribbon it always drew.
        "deck_rim_m": [],
        "speed_limit_kph": 50,
        "bus_lane": False,
        "tram_tracks": False,
        "elevation_level": 0,
        "road_name": {"en": "MAIN STREET", "zh": "大街"},
        # Schema 4 publishes the key on every edge; empty is a region whose
        # source restricts nothing here, which is what most of these fixtures
        # want to say. `kerbville` is the one that overrides it.
        "kerbside": [],
    }
    return {**edge, **overrides}


def _write_graph(tmp_path: Path, nodes: list[dict], edges: list[dict]) -> None:
    """One region's `roadgraph.json`, which is all the fixtures below differ in.

    Same reasoning as `_edge` above: the envelope is the contract in
    `docs/ARCHITECTURE.md` and repeating it three times invites the copies to
    drift, leaving the graph — the only interesting part — buried in it.
    """
    out_dir = tmp_path / "out" / "middle"
    out_dir.mkdir(parents=True)
    (out_dir / ROADGRAPH_NAME).write_text(
        json.dumps(
            {
                "schema_version": ROADGRAPH_SCHEMA,
                "city_id": "hong_kong",
                "region_id": "middle",
                "nodes": nodes,
                "edges": edges,
                "turn_restrictions": [],
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def pairville(tmp_path, testville_config):
    """An opposed carriageway pair, centrelines 3 m apart and nothing else.

    Each is 6.4 m of graph drawn at the 1.5x default, so the two ribbons overlap
    by 6.6 m and read on screen as one 12.6 m road. Neither shares a node with
    the other, so there is no junction, no trim and no cap here — whatever
    happens to the kerbs is the overlap pass and nothing else.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 2, "pos": [100.0, 0.0, 303.0], "kind": "endpoint"},
            {"id": 3, "pos": [500.0, 0.0, 303.0], "kind": "endpoint"},
        ],
        [
            _edge(0, 0, 1, [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]]),
            _edge(1, 3, 2, [[500.0, 0.0, 303.0], [100.0, 0.0, 303.0]]),
        ],
    )
    return testville_config, tmp_path


@pytest.fixture
def bendville(tmp_path, testville_config):
    """One street, split into two edges at a 60-degree bend.

    Two arms and nothing else, so the corner between them is carriageway rather
    than the pavement a third street would put there — and every square metre at
    the node is the cap's doing. This is the shape the junction pinch was
    reported on: BULLOCK LANE into CROSS LANE turns 62 degrees.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [300.0, 0.0, 300.0], "kind": "junction"},
            {"id": 1, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 2, "pos": [400.0, 0.0, 473.205], "kind": "endpoint"},
        ],
        [
            _edge(0, 1, 0, [[100.0, 0.0, 300.0], [300.0, 0.0, 300.0]]),
            _edge(1, 0, 2, [[300.0, 0.0, 300.0], [400.0, 0.0, 473.205]]),
        ],
    )
    return testville_config, tmp_path


@pytest.fixture
def stubville(tmp_path, testville_config):
    """Two dual-carriageway nodes 14 m apart, joined by the link Road Network v2
    draws between them, each with a north and a south arm (`P3-31`).

    The link is the stub: 12 m arms give a 6 m trim radius at both nodes, and
    35% of 14 m is 4.9 m, so both its trims are clamped. Each per-node cap then
    reaches 6 m from its node and the two stop 2 m short of each other, with
    the stub's own 9.6 m ribbon covering only the middle of that gap — so the
    ground at (307, 305.7), between the two south arms, is the median void.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [300.0, 0.0, 300.0], "kind": "junction"},
            {"id": 1, "pos": [314.0, 0.0, 300.0], "kind": "junction"},
            {"id": 2, "pos": [300.0, 0.0, 100.0], "kind": "endpoint"},
            {"id": 3, "pos": [300.0, 0.0, 500.0], "kind": "endpoint"},
            {"id": 4, "pos": [314.0, 0.0, 100.0], "kind": "endpoint"},
            {"id": 5, "pos": [314.0, 0.0, 500.0], "kind": "endpoint"},
        ],
        [
            _edge(0, 0, 1, [[300.0, 0.0, 300.0], [314.0, 0.0, 300.0]]),
            _edge(1, 2, 0, [[300.0, 0.0, 100.0], [300.0, 0.0, 300.0]], width_m=12.0),
            _edge(2, 0, 3, [[300.0, 0.0, 300.0], [300.0, 0.0, 500.0]], width_m=12.0),
            _edge(3, 4, 1, [[314.0, 0.0, 100.0], [314.0, 0.0, 300.0]], width_m=12.0),
            _edge(4, 1, 5, [[314.0, 0.0, 300.0], [314.0, 0.0, 500.0]], width_m=12.0),
        ],
    )
    return testville_config, tmp_path


@pytest.fixture
def splayville(tmp_path, testville_config):
    """One straight street crossing a junction whose two nodes it is attached
    to on the skew, the way Road Network v2 draws a dual carriageway (`P3-31`).

    The street is 12 m wide along z = 304. Its west arm reaches node 0 at
    (300, 300) by an 8 m splay from (292, 304), and its east arm reaches node 1
    at (314, 300) from (322, 304); the two nodes are joined by a 14 m stub,
    clamped at both ends by the 6 m radius, so the cluster is the two nodes.
    The notch between the splayed ribbon and the straight kerb at (296, 309.5)
    is road on the street and pavement in a cap built from the mouths alone.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [300.0, 0.0, 300.0], "kind": "junction"},
            {"id": 1, "pos": [314.0, 0.0, 300.0], "kind": "junction"},
            {"id": 2, "pos": [200.0, 0.0, 304.0], "kind": "endpoint"},
            {"id": 3, "pos": [414.0, 0.0, 304.0], "kind": "endpoint"},
        ],
        [
            _edge(0, 0, 1, [[300.0, 0.0, 300.0], [314.0, 0.0, 300.0]]),
            _edge(
                1,
                2,
                0,
                [[200.0, 0.0, 304.0], [292.0, 0.0, 304.0], [300.0, 0.0, 300.0]],
                width_m=12.0,
            ),
            _edge(
                2,
                1,
                3,
                [[314.0, 0.0, 300.0], [322.0, 0.0, 304.0], [414.0, 0.0, 304.0]],
                width_m=12.0,
            ),
        ],
    )
    return testville_config, tmp_path


@pytest.fixture
def testville(tmp_path, testville_config):
    """A crossroads, a flyover touching down on it, and a dead end.

    Four arms meet at node 0 so the junction cap has something to fill; the
    flyover arrives at the same node six metres up, which is the case that must
    *not* be capped across.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [300.0, 0.0, 300.0], "kind": "junction"},
            {"id": 1, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 2, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 3, "pos": [300.0, 0.0, 100.0], "kind": "endpoint"},
            {"id": 4, "pos": [300.0, 0.0, 500.0], "kind": "endpoint"},
            {"id": 5, "pos": [300.0, 6.0, 700.0], "kind": "endpoint"},
        ],
        [
            _edge(0, 1, 0, [[100.0, 0.0, 300.0], [300.0, 0.0, 300.0]]),
            _edge(1, 0, 2, [[300.0, 0.0, 300.0], [500.0, 0.0, 300.0]]),
            _edge(2, 3, 0, [[300.0, 0.0, 100.0], [300.0, 0.0, 300.0]]),
            _edge(3, 0, 4, [[300.0, 0.0, 300.0], [300.0, 0.0, 500.0]]),
            # Signed above the urban default, so it is the edge that proves the
            # widening table is read rather than a constant.
            _edge(
                4,
                1,
                3,
                [[100.0, 0.0, 300.0], [300.0, 0.0, 100.0]],
                lanes=3,
                width_m=9.6,
                speed_limit_kph=70,
            ),
            # A flyover deck arriving at the crossroads six metres up.
            _edge(5, 0, 5, [[300.0, 6.0, 300.0], [300.0, 6.0, 700.0]], elevation_level=1),
        ],
    )
    return testville_config, tmp_path


@pytest.fixture
def markedville(tmp_path, testville_config):
    """One straight one-way bus lane, and nothing for it to meet.

    The three fields `TEXCOORD_1` carries beyond the geometry are all published
    per edge and all off their defaults here, so a packing that dropped any of
    them would still pass on `testville` — every edge there is a two-way
    non-bus street. No node is shared, so there is no trim and no cap either,
    which is what makes the distance-to-end arithmetic checkable against the
    edge's own length rather than against whatever a junction held back.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
        ],
        [
            _edge(
                0,
                0,
                1,
                [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]],
                direction="forward",
                bus_lane=True,
                tram_tracks=True,
            )
        ],
    )
    return testville_config, tmp_path


@pytest.fixture
def kerbville(tmp_path, testville_config):
    """One straight street with a no-stopping restriction over part of it.

    400 m, no node shared with anything, so there is no trim and no cap and V is
    the edge's own metres. The nearside run is a double yellow over the middle
    half; the offside carries a shorter single, so the two sides differ in both
    kind and extent — a payload that wrote one side's answer to both would pass
    on a fixture where they agreed.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
        ],
        [
            _edge(
                0,
                0,
                1,
                [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]],
                kerbside=[
                    {"side": "near", "from_m": 100.0, "to_m": 300.0, "kind": "double"},
                    {"side": "off", "from_m": 150.0, "to_m": 200.0, "kind": "single"},
                ],
            )
        ],
    )
    return testville_config, tmp_path


@pytest.fixture
def dualville(tmp_path, testville_config):
    """One street as an opposed one-way pair, 4 m between the centrelines.

    The shape `P1-4` measured six of in Wan Chai and deliberately does not
    merge: at the 1.5x default each ribbon is 9.6 m wide, so the two overlap and
    read on screen as a single road with nothing separating the two flows.
    Nothing else is here, so whatever the offside pass decides is about this pair
    and not about a neighbour.

    ⚠️ **Both polylines start and end on the shared nodes**, which is what makes
    them a pair at all — and is the geometry the first version of this fixture
    got wrong. Given endpoints 4 m apart instead, the two centrelines never touch
    and a gap measured over the whole polyline never sees the zeros that a real
    pair contributes at both ends. The bug that hid behind that is in
    `_centreline_gap_m`'s docstring.
    """
    _write_graph(
        tmp_path,
        [
            {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
            {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
        ],
        [
            _edge(
                0,
                0,
                1,
                [
                    [100.0, 0.0, 300.0],
                    [200.0, 0.0, 298.0],
                    [400.0, 0.0, 298.0],
                    [500.0, 0.0, 300.0],
                ],
                direction="forward",
            ),
            _edge(
                1,
                1,
                0,
                [
                    [500.0, 0.0, 300.0],
                    [400.0, 0.0, 302.0],
                    [200.0, 0.0, 302.0],
                    [100.0, 0.0, 300.0],
                ],
                direction="forward",
            ),
        ],
    )
    return testville_config, tmp_path


def _abreast(tmp_path: Path, *offsets_m: float) -> None:
    """Straight one-way ribbons side by side, each running back the way the last came.

    `_write_graph`'s own argument one level up: the envelope is the same in
    every opposed-pair case and the only thing they differ in is the spacing, so
    written out per test the one interesting number is buried in forty lines of
    nodes. Anti-parallel because that is what makes two ribbons a pair at all —
    the search asks their chords.
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    for index, offset in enumerate(offsets_m):
        low = [100.0, 0.0, 300.0 + offset]
        high = [500.0, 0.0, 300.0 + offset]
        first, second = 2 * index, 2 * index + 1
        nodes.append({"id": first, "pos": low, "kind": "endpoint"})
        nodes.append({"id": second, "pos": high, "kind": "endpoint"})
        forwards = index % 2 == 0
        edges.append(
            _edge(
                index,
                first if forwards else second,
                second if forwards else first,
                [low, high] if forwards else [high, low],
                direction="forward",
            )
        )
    _write_graph(tmp_path, nodes, edges)


def _manifest(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "out" / "middle" / SURFACE_MANIFEST_NAME).read_text())


def _mesh(tmp_path: Path):
    """The drawn road as one mesh — merged back from its chunks (`P5-6`).

    Every geometry test below asks a region-wide question, and the merge is the
    reader every grader uses, so these tests exercise it on the way.
    """
    return read_surface(tmp_path / "out" / "middle", _manifest(tmp_path)["chunks"])


def _decode(code: float) -> dict[str, int]:
    """`TEXCOORD_1.x` back into its fields, the way a consumer has to do it.

    Spelled out here rather than imported from the pipeline, so these tests fail
    when the packing drifts from the layout `docs/ARCHITECTURE.md` publishes
    instead of agreeing with whatever the pipeline happens to write. `floor(x +
    0.5)` first is the contract's own instruction — every legal code is exact in
    float32, and this is what makes that worth asserting.
    """
    packed = int(np.floor(code + 0.5))
    return {
        "surface_class": packed % 4,
        "lanes": packed // 4 % 16,
        "direction": packed // 64 % 4,
        "bus_lane": packed // 256 % 2,
        "tram_tracks": packed // 512 % 2,
        "offside_kerb": packed // 1024 % 2,
        "centre": packed // 2048 % 64,
        "kerb_near": packed // 131072 % 4,
        "kerb_off": packed // 524288 % 4,
        "lanes_forward": packed // 2097152 % 4,
    }


def _of_class(mesh, surface_class: int) -> np.ndarray:
    """Mask of the vertices belonging to one surface class.

    By the payload's own class field, not by colour: a cap is painted the same
    asphalt as the carriageway it fills, so a colour mask quietly includes one.
    """
    return np.array([_decode(code)["surface_class"] == surface_class for code in mesh.uv2[:, 0]])


def _carriageway(mesh) -> np.ndarray:
    return _of_class(mesh, MARKING_CLASS_CARRIAGEWAY)


def _kerb(mesh) -> np.ndarray:
    return _of_class(mesh, MARKING_CLASS_KERB)


def _painted(mesh, colour: tuple[int, int, int]) -> np.ndarray:
    """Mask of the vertices carrying exactly this colour.

    Exact equality is safe here and nowhere else in the project: the road
    surface takes its two colours flat from the config, with none of the
    per-building jitter that makes a class a *ray* through its base colour on
    the tiles (`tools/deck_error.py` matched 428 of 434,149 triangles before
    that was understood).
    """
    return np.all(mesh.colours[:, :3] == np.array(colour, dtype=np.uint8), axis=1)


class TestBuildRegion:
    def test_it_writes_one_render_mesh_and_one_collider_per_tile(self, testville, tmp_path) -> None:
        """One GLB per tile the road touches, and in each the drawn ribbon plus
        its `-colonly` collider (`P5-12`) — Godot's importer reads the suffix to
        build the static trimesh at import time, so each chunk stands on its
        own (`P5-6`). The collider is the ribbon's own triangles, bare: no
        colour, no lane coordinate, no marking code."""
        report = build_region(testville[0], "middle", out_root=tmp_path / "out")

        chunks = _manifest(tmp_path)["chunks"]
        # Testville runs 100-700 m on a 150 m grid, so the road cannot fit one tile.
        assert len(chunks) > 1
        assert [chunk["id"] for chunk in chunks] == sorted(chunk["id"] for chunk in chunks)
        for chunk in chunks:
            assert chunk["file"] == f"{SURFACE_DIR}/{chunk['id']}.glb"
            meshes = read_glb(tmp_path / "out" / "middle" / chunk["file"])
            assert [mesh.name for mesh in meshes] == [SURFACE_MESH_NAME, SURFACE_COLLIDER_NAME]
            drawn, collider = meshes
            assert drawn.triangle_count == chunk["triangles"]
            assert len(drawn.positions) == chunk["vertices"]
            assert collider.triangle_count == chunk["collision_triangles"]
            assert np.array_equal(collider.positions, drawn.positions)
            assert np.array_equal(collider.triangles, drawn.triangles)
            assert collider.colours is None and collider.uvs is None and collider.uv2 is None
            assert [
                mesh.name for mesh in read_render(tmp_path / "out" / "middle" / chunk["file"])
            ] == [SURFACE_MESH_NAME]
        assert report.triangles == sum(chunk["triangles"] for chunk in chunks)

    def test_the_chunks_are_a_partition_of_the_built_mesh(self, testville, tmp_path) -> None:
        """Nothing is cut and nothing moves: every chunk triangle is a built
        triangle with the same three corners and the same attributes, and the
        only cost is the station vertices the cut duplicated — published as
        `cut_vertices` and equal to the difference by construction."""
        report = build_region(testville[0], "middle", out_root=tmp_path / "out")
        manifest = _manifest(tmp_path)

        merged = _mesh(tmp_path)
        assert merged.triangle_count == report.triangles
        # Zero here, and rightly: Testville's edges are one quad each, so no strip
        # has a station on a tile line. `TestTheCutFallsAtStations` is where a
        # cut is forced and the duplicate counted.
        assert manifest["cut_vertices"] == len(merged.positions) - report.vertices
        assert manifest["cut_vertices"] >= 0
        assert manifest["vertices"] == report.vertices

        # The same triangles, corner for corner, whatever order they came out in.
        merged_corners = {tuple(row) for row in merged.positions[merged.triangles].reshape(-1, 9)}
        for chunk in manifest["chunks"]:
            piece = read_render(tmp_path / "out" / "middle" / chunk["file"])[0]
            piece_corners = {tuple(row) for row in piece.positions[piece.triangles].reshape(-1, 9)}
            assert piece_corners <= merged_corners

    def test_a_junction_cap_goes_whole_to_one_chunk(self, testville, tmp_path) -> None:
        """A cap is a fan from its centroid, so a cap split across two tiles
        would pop in halves as the streamer loads one and not the other. The
        centroid vertex belongs to the fan alone, so exactly one chunk carries
        it — and that chunk carries every corner of the ring too."""
        build_region(testville[0], "middle", out_root=tmp_path / "out")
        manifest = _manifest(tmp_path)
        positions_of = {
            chunk["id"]: {
                tuple(np.round(row, 3))
                for row in read_render(tmp_path / "out" / "middle" / chunk["file"])[0].positions
            }
            for chunk in manifest["chunks"]
        }
        assert manifest["caps"]
        for cap in manifest["caps"]:
            ring = np.asarray(cap["ring"], dtype=np.float64)
            centroid = tuple(np.round(ring.mean(axis=0), 3))
            homes = [tile for tile, positions in positions_of.items() if centroid in positions]
            assert len(homes) == 1, f"cap at level {cap['level']} is in {len(homes)} chunks"
            corners = {tuple(np.round(corner, 3)) for corner in ring}
            assert corners <= positions_of[homes[0]]

    def test_the_carriageway_is_the_configured_multiple_of_its_lanes(
        self, testville, tmp_path
    ) -> None:
        """`widen_factor` is data, which is half of `P1-4`'s acceptance. The
        eastern arm is 6.4 m of graph at the 1.5x default; the diagonal is
        signed at 70 km/h and takes the 1.2x rule instead."""
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        # The eastern arm alone: past the junction, and nothing else runs here.
        arm = mesh.positions[mesh.positions[:, 0] > 320.0]
        kerb_to_kerb = arm[:, 2].max() - arm[:, 2].min()
        assert kerb_to_kerb - 2 * city.roads.surface.kerb_width_m == pytest.approx(
            6.4 * 1.5, abs=0.01
        )
        assert city.roads.surface.floor_for(70, elevation_level=0) == 11.52

    def test_the_flyover_is_drawn_at_its_authored_width(self, testville, tmp_path) -> None:
        """The off-grade half of the same acceptance, measured in the mesh.

        The unit tests in `test_config.py` pin the factor, and the manifest test
        pins what was published — but only geometry proves the ribbon was
        actually *extruded* narrower. Before the rule this read 9.6 m across.
        """
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        # The deck alone: six metres up, and north of the junction it lands on.
        deck = mesh.positions[(mesh.positions[:, 1] > 5.0) & (mesh.positions[:, 2] > 320.0)]
        kerb_to_kerb = deck[:, 0].max() - deck[:, 0].min()
        assert kerb_to_kerb - 2 * city.roads.surface.kerb_width_m == pytest.approx(6.4, abs=0.01)

    def test_every_arm_meets_its_junction_with_no_gap(self, testville, tmp_path) -> None:
        """`P1-4`'s acceptance criterion, checked directly rather than argued.

        Each ribbon stops short of the node, so the mouth it leaves — the
        segment between its two end corners — has to be inside the cap. It is,
        because the cap is the convex hull of those very corners.
        """
        build_region(testville[0], "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        # Street level only. The flyover deck runs across the same junction six
        # metres up, and letting it count would hide a hole in the road below.
        corners = mesh.positions[mesh.triangles]
        triangles = corners[(corners[:, :, 1] < 1.0).all(axis=1)][:, :, [0, 2]]
        grid = np.array(
            [(x, z) for x in np.arange(295.0, 305.5, 0.5) for z in np.arange(295.0, 305.5, 0.5)]
        )
        assert _covered(grid, triangles).all()

    def test_a_kerb_inside_a_neighbours_carriageway_is_not_drawn(self, pairville, tmp_path) -> None:
        """The white line down the middle of Hennessy Road, reported by a driver.

        Every edge is extruded on its own account, so an opposed pair gets four
        kerbs — and the widening that merges their tarmac into one surface buries
        the inner two in it. They are not decoration: the mesh ships as one
        trimesh collider and 0.15 m is 83% of the car's bump travel.
        """
        city, _ = pairville
        report = build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        raised = mesh.positions[mesh.positions[:, 1] > city.roads.surface.kerb_height_m / 2.0]
        assert len(raised) > 0
        # The union runs from z 295.2 to z 307.8, and only its two outer edges
        # are a kerb anyone can see. Both inner ones are 3.6 m inside it.
        assert ((raised[:, 2] < 295.3) | (raised[:, 2] > 307.7)).all()
        # Both edges are 400 m long and untrimmed, and each loses one side.
        assert report.buried_kerb_m == pytest.approx(800.0, abs=1.0)

    def test_a_bend_keeps_its_full_width_through_the_cap(self, bendville, tmp_path) -> None:
        """The junction pinch, reported from the driver's seat and measured after.

        A hull of the arm mouths alone is a chord across the turn, so the road
        used to narrow to `cos(half the turn)` of its width at the node — 30% of
        a 10.2 m street gone at Wan Chai's sharpest two-arm bend, in the one
        place a car is already committed. The mitre apexes go into the same hull
        to stop it, so the cross-section here is the mitred one.
        """
        city, _ = bendville
        report = build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        half = city.roads.surface.drawn_width_m(6.4, 50, elevation_level=0) / 2.0
        # Travel turns from +X to 60 degrees right of it, so the joint bisects
        # at 30 degrees and the mitre reaches `1 / cos(30)` half-widths out.
        normal = np.array([np.sin(np.radians(30.0)), -np.cos(np.radians(30.0))])
        reach = half / np.cos(np.radians(30.0))
        node = np.array([300.0, 300.0])
        across = np.linspace(-0.95, 0.95, 21)[:, None] * reach * normal

        corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
        assert _covered(node + across, corners).all()
        assert report.through_movements == 1

    def test_a_flyover_is_not_capped_down_to_the_street(self, testville, tmp_path) -> None:
        """The 36 places in Wan Chai where two levels share a node all step by a
        whole deck height. Capping across one would weld a street to the deck
        above it with a wall no car could climb."""
        build_region(testville[0], "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        at_junction = mesh.positions[
            (np.abs(mesh.positions[:, 0] - 300.0) < 12.0)
            & (np.abs(mesh.positions[:, 2] - 300.0) < 12.0)
        ]
        heights = np.unique(np.round(at_junction[:, 1], 2))
        # Street, street kerb, deck, deck kerb — and nothing bridging the two.
        assert heights.min() == pytest.approx(0.0)
        assert heights.max() == pytest.approx(6.15)
        assert not ((heights > 0.2) & (heights < 5.9)).any()

    def test_the_report_counts_the_level_change(self, testville, tmp_path) -> None:
        report = build_region(testville[0], "middle", out_root=tmp_path / "out")

        assert report.level_changes == 1
        assert report.max_level_step_m == pytest.approx(6.0)

    def test_kerbs_stand_at_their_configured_height(self, testville, tmp_path) -> None:
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        street = mesh.positions[mesh.positions[:, 1] < 3.0]
        assert street[:, 1].max() == pytest.approx(city.roads.surface.kerb_height_m)

    def test_lane_zero_is_the_nearside_kerb(self, testville, tmp_path) -> None:
        """Hong Kong drives on the left, so U must count lanes from the left of
        travel. Nothing renders wrong if this flips — the winding is
        self-consistent either way — but every asymmetric marking the shader
        draws off U would end up on the wrong side of the road.
        """
        build_region(testville[0], "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        # Edge 1 runs east (+X) from the crossroads, so its nearside is -Z.
        arm = mesh.positions[:, 0] > 320.0
        at_kerb_line = arm & (np.abs(mesh.uvs[:, 0]) < 1e-6)
        assert at_kerb_line.any()
        assert mesh.positions[at_kerb_line][:, 2].max() < 300.0

    def test_the_kerb_carries_its_u_ramp_on_the_lip(self, testville, tmp_path) -> None:
        """The riser has no plan width, so both its rails stand at the kerb line
        and must share its U. Put the ramp there instead and an integer U stops
        meaning a lane boundary, which is the one promise the contract makes.
        """
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        style = city.roads.surface
        outside = style.kerb_width_m / city.roads.lane_width_m
        arm = mesh.positions[:, 0] > 320.0
        # The eastern arm travels +X, so its nearside lip is the smallest Z on
        # it and the carriageway edge sits one kerb width inside that.
        lip_outer_z = mesh.positions[arm][:, 2].min()
        kerb_line_z = lip_outer_z + style.kerb_width_m

        at_kerb_line = arm & (np.abs(mesh.positions[:, 2] - kerb_line_z) < 1e-4)
        # Both ends of the riser stand here — road level and kerb height alike.
        assert set(np.round(mesh.positions[at_kerb_line][:, 1], 3)) == {0.0, style.kerb_height_m}
        np.testing.assert_allclose(mesh.uvs[at_kerb_line][:, 0], 0.0, atol=1e-6)

        # U reaches its outer value only across the lip, which has plan width.
        at_lip_outer = arm & (np.abs(mesh.positions[:, 2] - lip_outer_z) < 1e-4)
        np.testing.assert_allclose(mesh.uvs[at_lip_outer][:, 0], -outside, atol=1e-6)

    def test_no_triangle_faces_downward(self, testville, tmp_path) -> None:
        """A fold renders as a hole under back-face culling and is invisible to
        a one-sided collider."""
        build_region(testville[0], "middle", out_root=tmp_path / "out")

        count, area = downward_facing(_mesh(tmp_path))
        assert (count, area) == (0, 0.0)

    def test_it_writes_a_manifest_for_the_export_stage(self, testville, tmp_path) -> None:
        report = build_region(testville[0], "middle", out_root=tmp_path / "out")

        manifest = _manifest(tmp_path)
        assert "mesh" not in manifest
        assert manifest["mesh_name"] == SURFACE_MESH_NAME
        assert manifest["triangles"] == report.triangles
        assert manifest["bytes"] == sum(chunk["bytes"] for chunk in manifest["chunks"])
        assert len(manifest["aabb"]) == 2
        for chunk in manifest["chunks"]:
            assert set(chunk) == {
                "id",
                "file",
                "triangles",
                "vertices",
                "collision_triangles",
                "bytes",
                "aabb",
            }

    def test_the_manifest_carries_the_drawn_half_width_of_every_edge(
        self, testville, tmp_path
    ) -> None:
        """The game cannot derive it. `roadgraph.json` publishes the authored
        street width and the widening lives on the surface style, so this is the
        only route by which the drawn width reaches a runtime — `P2-2` puts a car
        in the nearside lane with it."""
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")

        out = tmp_path / "out" / "middle"
        manifest = json.loads((out / SURFACE_MANIFEST_NAME).read_text())
        graph = json.loads((out / ROADGRAPH_NAME).read_text())
        published = {entry["edge"]: entry["half_width_m"] for entry in manifest["carriageway"]}

        assert set(published) == {edge["id"] for edge in graph["edges"]}
        style = city.roads.surface
        off_grade = 0
        for edge in graph["edges"]:
            widened = (
                style.drawn_width_m(
                    edge["width_m"],
                    edge["speed_limit_kph"],
                    elevation_level=edge["elevation_level"],
                )
                / 2.0
            )
            # One value per station since `Q23`, and the game indexes it by the
            # graph's own vertex numbering — so a length that drifts from the
            # polyline reads the wrong station's width rather than failing.
            assert len(published[edge["id"]]) == len(edge["polyline"])
            assert published[edge["id"]] == pytest.approx(
                [widened] * len(edge["polyline"]), abs=0.001
            )
            # Stated against the authored width rather than against
            # `drawn_width_m`, which the line above already uses: an expectation
            # computed by the function under test survives that function being
            # reverted.
            #
            # At grade the drawn ribbon is wider than the authored street, so a
            # lane centre taken from the graph alone would sit short. Off-grade
            # it is *equal* — which is why the game reads this table instead of
            # deriving a width from the graph and a factor.
            if edge["elevation_level"] == 1:
                off_grade += 1
                assert published[edge["id"]] == pytest.approx(
                    [edge["width_m"] / 2.0] * len(edge["polyline"]), abs=0.001
                )
            else:
                # Level -1 has no rule and takes the speed factor, so it belongs
                # here rather than with the structure.
                assert min(published[edge["id"]]) > edge["width_m"] / 2.0
        # The fixture's one flyover. Without this the off-grade branch could stop
        # being reached and every assertion above would still pass.
        assert off_grade == 1

    def test_a_level_zero_edge_narrows_where_it_stands_on_structure(
        self, testville, tmp_path
    ) -> None:
        """`Q23`, measured in the mesh rather than in the manifest.

        The fixture's western arm is rewritten to arrive on a ramp deck: its
        first three stations are flagged, which is the shape `P2-7` leaves at
        every touchdown — a level-0 edge whose start is on structure and whose
        far end is on the street. Before this, the whole edge was drawn 1.5x.
        """
        city, _ = testville
        graph_path = tmp_path / "out" / "middle" / ROADGRAPH_NAME
        document = json.loads(graph_path.read_text())
        # 60 m of straight running west from the junction, on structure for its
        # first 20 m — far enough that the taper has finished before the street.
        document["edges"][0] = _edge(
            0,
            1,
            0,
            [[240.0 + 10.0 * step, 0.0, 300.0] for step in range(7)],
            on_structure=[True, True, True, False, False, False, False],
        )
        graph_path.write_text(json.dumps(document), encoding="utf-8")

        build_region(city, "middle", out_root=tmp_path / "out")
        manifest = json.loads((tmp_path / "out" / "middle" / SURFACE_MANIFEST_NAME).read_text())
        widths = next(
            entry["half_width_m"] for entry in manifest["carriageway"] if entry["edge"] == 0
        )

        assert widths[0] == pytest.approx(6.4 / 2.0, abs=0.001), "on the deck, authored width"
        assert widths[-1] == pytest.approx(6.4 * 1.5 / 2.0, abs=0.001), "on the street, widened"
        assert widths == sorted(widths), "and it only ever widens away from the structure"

    def test_the_report_counts_the_metres_it_narrowed(self, testville, tmp_path) -> None:
        """`Q23`'s acceptance number, off the stage that acted on it."""
        city, _ = testville
        graph_path = tmp_path / "out" / "middle" / ROADGRAPH_NAME
        document = json.loads(graph_path.read_text())
        document["edges"][0] = _edge(
            0,
            1,
            0,
            [[240.0 + 10.0 * step, 0.0, 300.0] for step in range(7)],
            on_structure=[True, True, True, False, False, False, False],
        )
        graph_path.write_text(json.dumps(document), encoding="utf-8")

        report = build_region(city, "middle", out_root=tmp_path / "out")
        # Two whole 10 m segments between the three flagged stations, plus half
        # of the segment that leaves the last one — the trapezoid rule.
        assert report.on_structure_m == pytest.approx(25.0, abs=0.01)

    def test_a_graph_from_another_schema_is_refused(self, testville, tmp_path) -> None:
        """The contract is versioned, so a mismatch is a stale copy rather than
        something to parse optimistically."""
        city, _ = testville
        graph = tmp_path / "out" / "middle" / ROADGRAPH_NAME
        document = json.loads(graph.read_text())
        document["schema_version"] = ROADGRAPH_SCHEMA + 1
        graph.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(ValueError, match="schema_version"):
            build_region(city, "middle", out_root=tmp_path / "out")


class TestTheCutFallsAtStations:
    """`_Builder` decides a quad's chunk by the plan centre of its two stations
    and a cap's by its centroid — the rule `P5-6` is accepted on, pinned on a
    synthetic grid so it fails on the rule and not on Testville's layout."""

    @staticmethod
    def _grid() -> Grid:
        return Grid(tile_size_m=150.0, max_x=300.0, max_z=150.0)

    def test_a_quad_belongs_to_the_tile_its_centre_is_in(self) -> None:
        builder = _Builder(self._grid())
        # Stations at x = 10, 140, 160, 290: quad centres 75, 150, 225 -> tiles 0, 1, 1.
        left = np.array([[10.0, 0.0, 2.0], [140.0, 0.0, 2.0], [160.0, 0.0, 2.0], [290.0, 0.0, 2.0]])
        right = left + np.array([0.0, 0.0, -4.0])
        builder.strip(
            right,
            left,
            colour=(1, 2, 3),
            along=np.array([0.0, 130.0, 150.0, 280.0]),
            across=(2.0, 0.0),
            marking=_Marking(0.0, 280.0),
        )
        builder.build("cut")
        chunks = dict(builder.chunk())

        assert set(chunks) == {"t_00_00", "t_01_00"}
        assert chunks["t_00_00"].triangle_count == 2
        assert chunks["t_01_00"].triangle_count == 4
        # The station at x = 140 is on both sides of the cut, at the same place.
        shared = {tuple(p) for p in chunks["t_00_00"].positions} & {
            tuple(p) for p in chunks["t_01_00"].positions
        }
        assert {p[0] for p in shared} == {140.0}
        assert len(shared) == 2

    def test_a_cap_belongs_whole_to_the_tile_its_centroid_is_in(self) -> None:
        builder = _Builder(self._grid())
        # A ring straddling x = 150 whose centroid is at x = 160: tile 1, all of it.
        ring = np.array(
            [[140.0, 0.0, 0.0], [180.0, 0.0, 0.0], [180.0, 0.0, 10.0], [140.0, 0.0, 10.0]]
        )
        builder.fan(ring, colour=(1, 2, 3), marking=_Marking(2.0, 0.0))
        builder.build("cap")
        chunks = dict(builder.chunk())

        assert set(chunks) == {"t_01_00"}
        assert chunks["t_01_00"].triangle_count == 4

    def test_a_ribbon_past_the_west_edge_is_clamped_into_the_first_tile(self) -> None:
        """A widened ribbon along the region edge runs a few metres negative;
        `//` alone would hand those quads to a tile that does not exist."""
        builder = _Builder(self._grid())
        left = np.array([[-6.0, 0.0, 2.0], [-2.0, 0.0, 2.0]])
        right = left + np.array([0.0, 0.0, -4.0])
        builder.strip(
            right,
            left,
            colour=(1, 2, 3),
            along=np.array([0.0, 4.0]),
            across=(2.0, 0.0),
            marking=_Marking(0.0, 4.0),
        )
        builder.build("edge")
        assert set(dict(builder.chunk())) == {"t_00_00"}

    def test_chunk_before_build_is_refused(self) -> None:
        with pytest.raises(ValueError, match="before build"):
            _Builder(self._grid()).chunk()

    def test_a_builder_is_used_once(self) -> None:
        """A second `build` would append onto the first's keys and hand `chunk`
        a key per triangle of a mesh that no longer exists."""
        builder = _Builder(self._grid())
        ring = np.array([[0.0, 0.0, 0.0], [40.0, 0.0, 0.0], [40.0, 0.0, 10.0]])
        builder.fan(ring, colour=(1, 2, 3), marking=_Marking(2.0, 0.0))
        builder.build("once")
        with pytest.raises(ValueError, match="already built"):
            builder.build("twice")

    def test_without_a_grid_everything_is_one_chunk(self) -> None:
        builder = _Builder()
        ring = np.array([[0.0, 0.0, 0.0], [400.0, 0.0, 0.0], [400.0, 0.0, 10.0]])
        builder.fan(ring, colour=(1, 2, 3), marking=_Marking(2.0, 0.0))
        builder.build("one")
        assert [tile for tile, _ in builder.chunk()] == ["t_00_00"]


class TestMarkingPayload:
    """`TEXCOORD_1`, which is what makes `TEXCOORD_0` readable (`P3-12`).

    Every test here is about a question the shader has to be able to answer
    before it paints anything, and that `TEXCOORD_0` alone cannot — the codec
    block in `pipeline/surface.py` says why.
    """

    def test_the_carriageway_says_its_class_lanes_and_direction(self, testville, tmp_path) -> None:
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        # The eastern arm alone, and its road rather than its kerb: past the
        # junction, so nothing else in the region reaches here.
        arm = mesh.positions[:, 0] > 320.0
        road = arm & _painted(mesh, city.roads.surface.surface_material.colour)
        assert road.any()

        codes = np.unique(mesh.uv2[road, 0])
        assert len(codes) == 1
        assert _decode(codes[0]) == {
            "surface_class": 0,
            "lanes": 2,
            "direction": 1,
            "bus_lane": 0,
            "tram_tracks": 0,
            "offside_kerb": 1,
            "centre": 0,
            # Schema 4 publishes the key and this fixture leaves it empty, which
            # is "the source was consulted and restricts nothing here" — not the
            # same as a city with no such layer, which reports 0.
            "kerb_near": MARKING_KERB_NONE,
            "kerb_off": MARKING_KERB_NONE,
            # Schema 13: the fixture publishes no split (`null`), which packs
            # as 0 — "draw the middle" — and is what a one-way edge packs too.
            "lanes_forward": 0,
        }

    def test_a_kerb_says_it_is_a_kerb(self, testville, tmp_path) -> None:
        """The one field the shader cannot do without. `fract(U)` on the offside
        lip lands in [0, 0.156], so without this a lane line is painted down
        every kerb in the region.
        """
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        arm = mesh.positions[:, 0] > 320.0
        kerb = arm & _painted(mesh, city.roads.surface.kerb_material.colour)
        assert kerb.any()

        classes = {_decode(code)["surface_class"] for code in mesh.uv2[kerb, 0]}
        assert classes == {1}

    def test_a_junction_cap_says_so_and_stands_at_zero(self, testville, tmp_path) -> None:
        """A cap carries `TEXCOORD_0 = (0, 0)`, and U = 0 *is* the nearside kerb
        line — so a kerbside marking keyed on U alone would flood every junction
        in the city. The class says what the lane coordinate cannot, and the
        distance is what actually keeps the shader off it.
        """
        city, _ = testville
        report = build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        cap = np.array([_decode(code)["surface_class"] == 2 for code in mesh.uv2[:, 0]])
        assert report.junctions > 0
        assert cap.any()

        # Every capped vertex stands at a node — testville caps two of them, the
        # crossroads and the two ends of the diagonal, each a street bending
        # through a degree-2 node — and within reach of the widest arm meeting
        # it, the 3-lane diagonal at half-width 5.76 m.
        nodes = np.array([[300.0, 300.0], [100.0, 300.0], [300.0, 100.0]])
        plan = mesh.positions[cap][:, [0, 2]]
        to_nodes = np.hypot(*(plan[:, None, :] - nodes).transpose(2, 1, 0))
        assert to_nodes.min(axis=0).max() < 12.0
        # Zero length is what the shader reads as "not a length of lane".
        np.testing.assert_array_equal(mesh.uv2[cap, 1], 0.0)

    def test_the_ribbon_carries_the_length_it_was_drawn_at(self, markedville, tmp_path) -> None:
        """`markedville` shares no node, so nothing is trimmed and the ribbon is
        the whole 400 m of graph.

        ⚠️ The length, not a per-vertex distance to the nearer end — the codec
        block in `pipeline/surface.py` has the argument. **This fixture is the
        two-station edge that argument is about**, and it read 0.0 end to end
        before the payload became a length, which is what this test exists to
        keep true.
        """
        city, _ = markedville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        np.testing.assert_allclose(mesh.uv2[:, 1], 400.0, atol=1e-3)
        # And V is the other half of the pair the shader takes the distance
        # from, so it has to span that same length.
        assert mesh.uvs[:, 1].min() == pytest.approx(0.0, abs=1e-4)
        assert mesh.uvs[:, 1].max() == pytest.approx(400.0, abs=1e-3)

    def test_the_length_is_the_drawn_one_not_the_published_one(self, testville, tmp_path) -> None:
        """Every arm of the crossroads is held back for its cap, and the fade
        has to reach zero where the ribbon stops rather than where the
        centreline did — or a stub of lane line stands under every junction.
        """
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        # The eastern arm: 200 m of centreline from the crossroads to node 2,
        # trimmed at the junction end only.
        arm = (mesh.positions[:, 0] > 320.0) & _painted(
            mesh, city.roads.surface.surface_material.colour
        )
        lengths = np.unique(mesh.uv2[arm, 1])
        assert len(lengths) == 1
        assert 0.0 < lengths[0] < 200.0
        # V still runs to that length, which is what makes the two comparable.
        assert mesh.uvs[arm, 1].max() == pytest.approx(lengths[0], abs=1e-3)

    def test_a_one_way_bus_lane_sets_every_bit_it_owns(self, markedville, tmp_path) -> None:
        """Three published fields nothing read until now. A centre line on a
        one-way street is the loud half of getting this wrong; a bus lane drawn
        on 737 edges instead of 14 is the quiet one.
        """
        city, _ = markedville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        road = _painted(mesh, city.roads.surface.surface_material.colour)
        codes = np.unique(mesh.uv2[road, 0])
        assert len(codes) == 1
        assert _decode(codes[0]) == {
            "surface_class": 0,
            "lanes": 2,
            "direction": 2,
            "bus_lane": 1,
            "tram_tracks": 1,
            "offside_kerb": 1,
            "centre": 0,
            # Schema 4 publishes the key and this fixture leaves it empty, which
            # is "the source was consulted and restricts nothing here" — not the
            # same as a city with no such layer, which reports 0.
            "kerb_near": MARKING_KERB_NONE,
            "kerb_off": MARKING_KERB_NONE,
            "lanes_forward": 0,
        }

    def test_every_code_is_a_small_exact_integer(self, testville, tmp_path) -> None:
        """The property the codec is built on, and the one a later field would
        break silently: float32 carries 24 exact bits, the layout tops out at
        1023, and a consumer decodes with `floor(x + 0.5)` on that promise.
        """
        build_region(testville[0], "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        codes = mesh.uv2[:, 0]
        np.testing.assert_array_equal(codes, np.floor(codes))
        assert codes.min() >= 0.0
        assert codes.max() <= MARKING_CODE_MAX
        # A negative length would run the fade backwards.
        assert mesh.uv2[:, 1].min() >= 0.0

    def test_a_lane_count_the_codec_cannot_say_is_refused(self, tmp_path, testville_config) -> None:
        """⚠️ The guard has to be **per field**, and the total cannot stand in
        for it. `lanes` is the only unbounded input — city config authors it per
        road class with no ceiling — and 16 packs to 64, carries straight into
        the direction field, and still leaves a total inside `MARKING_CODE_MAX`.
        A check on the sum passes it, and the shader then reads no lanes
        travelling in a direction the vocabulary does not have.
        """
        _write_graph(
            tmp_path,
            [
                {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
            ],
            [_edge(0, 0, 1, [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]], lanes=16)],
        )

        with pytest.raises(ValueError, match="16 lanes"):
            build_region(testville_config, "middle", out_root=tmp_path / "out")

    def test_the_split_is_packed_where_the_graph_states_one(self, testville_config, tmp_path):
        """`Q126`: WAN CHAI ROAD's shape — three lanes, two of them forward — so
        the shader draws the centre line at `U = 2` and not down the middle of
        the right-turn lane. A one-way edge packs 0 whatever the graph says its
        `lanes_forward` is, because 0 is the codec's "draw the middle" and a
        one-way edge has no middle to draw."""
        _write_graph(
            tmp_path,
            [
                {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 2, "pos": [100.0, 0.0, 600.0], "kind": "endpoint"},
                {"id": 3, "pos": [500.0, 0.0, 600.0], "kind": "endpoint"},
            ],
            [
                _edge(
                    0, 0, 1, [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]], lanes=3, lanes_forward=2
                ),
                _edge(
                    1,
                    2,
                    3,
                    [[100.0, 0.0, 600.0], [500.0, 0.0, 600.0]],
                    lanes=3,
                    lanes_forward=3,
                    direction="forward",
                ),
            ],
        )
        build_region(testville_config, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)
        road = _painted(mesh, testville_config.roads.surface.surface_material.colour)
        south = road & (mesh.positions[:, 2] < 450.0)
        north = road & (mesh.positions[:, 2] > 450.0)
        assert {_decode(c)["lanes_forward"] for c in np.unique(mesh.uv2[south, 0])} == {2}
        assert {_decode(c)["lanes_forward"] for c in np.unique(mesh.uv2[north, 0])} == {0}

    def test_a_split_the_two_bits_cannot_hold_is_counted_and_drawn_at_the_middle(
        self, testville_config, tmp_path
    ):
        """Four forward lanes on a two-way single carriageway is past anything
        TPDM lets one be, and past the channel — so the road still draws, at
        its old middle, and `lanes_forward_unsaid` says so."""
        _write_graph(
            tmp_path,
            [
                {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
            ],
            [_edge(0, 0, 1, [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]], lanes=6, lanes_forward=4)],
        )
        report = build_region(testville_config, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)
        assert report.lanes_forward_unsaid == 1
        assert {_decode(c)["lanes_forward"] for c in np.unique(mesh.uv2[:, 0])} == {0}

    def test_a_split_on_a_one_way_edge_or_past_its_lanes_is_refused_by_the_codec(self):
        """`marking_code`'s own guard, below `_prepare`'s translation: the two
        states the shader would draw a centre line across a one-way road or on a
        kerb for. Reachable only by a caller that bypasses `_prepare`."""
        from dataclasses import replace

        from pipeline.surface import _Edge

        edge = _Edge(
            points=np.zeros((2, 5)),
            published_half_widths=np.zeros(2),
            published_offsets=np.zeros(2),
            lanes=3,
            direction="both",
            bus_lane=False,
            tram_tracks=False,
            level=0,
            length_m=10.0,
        )
        assert _decode(replace(edge, lanes_forward=2).marking_code(0))["lanes_forward"] == 2
        with pytest.raises(ValueError, match="strictly inside"):
            replace(edge, lanes_forward=3).marking_code(0)
        with pytest.raises(ValueError, match="strictly inside"):
            replace(edge, direction="forward", lanes_forward=2).marking_code(0)
        with pytest.raises(ValueError, match="past what"):
            replace(edge, lanes=6, lanes_forward=4).marking_code(0)

    def test_an_opposed_pair_publishes_where_its_flows_meet(self, dualville, tmp_path) -> None:
        """Two one-way carriageways widened until they read as one road have a
        centre neither of them marks: the ribbons overlap, so `U = lanes` on
        either lands inside the other's carriageway rather than at the join.

        ⚠️ The offset is in **lane-coordinate units, and one of those is not
        `lane_width_m`** — U is normalised to the ribbon as drawn, so a U-lane is
        `2 * half_width / lanes` on the ground. Dividing by the authored lane
        width puts the join past `U = lanes` and off the carriageway, which is
        exactly where it first landed.
        """
        city, _ = dualville
        report = build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        assert report.opposed_pair_ends == 2
        assert report.opposed_pairs_unpublishable == 0

        road = _carriageway(mesh)
        fields = [_decode(c) for c in mesh.uv2[road, 0]]
        centres = {f["centre"] for f in fields}
        assert centres and 0 not in centres

        # 🔴 **The property the whole field exists for, and the one it shipped
        # without.** Each half publishes its own offset and the two are meant to
        # name the *same* line. Measured against the region, a gap taken over the
        # whole centreline read half the truth on a four-station edge — the two
        # shared nodes contribute an exact 0.0 each — so the halves disagreed and
        # drew two lines up to 3.9 m apart on Fleming Road.
        assert len(centres) == 1, "both halves of a pair must publish the same join"

        lanes = next(iter({f["lanes"] for f in fields}))
        k = next(iter(centres))
        join = lanes / 2.0 + (k - 1) / 16.0
        assert 0.0 < join < lanes, "the join must land on the carriageway"
        # The centrelines are 4 m apart at mid-street and meet at both nodes, so
        # the join sits between the centreline and half of 4 m. Bounded rather
        # than pinned: what the median of a tapering gap comes to is not a
        # number worth freezing, and the two assertions above are the contract.
        assert 0.0 < (k - 1) / 16.0 * (2 * 4.8 / lanes) <= 2.0

    def test_a_pair_does_not_claim_its_offside_is_a_kerb(self, dualville, tmp_path) -> None:
        """The other half of the same fact, and the one that keeps a no-stopping
        line off the middle of a road."""
        city, _ = dualville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        road = _carriageway(mesh)
        assert all(not _decode(c)["offside_kerb"] for c in mesh.uv2[road, 0])

    def test_an_ordinary_street_says_its_offside_is_a_kerb(self, testville, tmp_path) -> None:
        city, _ = testville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        arm = mesh.positions[:, 0] > 320.0
        road = arm & _painted(mesh, city.roads.surface.surface_material.colour)
        fields = [_decode(c) for c in mesh.uv2[road, 0]]
        assert all(f["offside_kerb"] for f in fields)
        assert all(f["centre"] == 0 for f in fields)

    def test_a_street_is_not_its_own_opposed_carriageway(self, tmp_path, testville_config) -> None:
        """A loop edge publishes a centre line down the middle of its own lane if
        anything lets it match itself.

        ⚠️ **The reason it cannot changed with the pairing and the test did not.**
        Under the endpoint rule a loop matched its own reversed key; under the
        geometric one it is refused twice over — a candidate is never itself, and
        a loop's chord has no length, so `normalise` leaves `_Ribbon`'s unit at
        zero and the anti-parallel test is handed a zero vector, which fails it
        rather than passing it.
        """
        _write_graph(
            tmp_path,
            [{"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"}],
            [
                _edge(
                    0,
                    0,
                    0,
                    [[100.0, 0.0, 300.0], [200.0, 0.0, 360.0], [100.0, 0.0, 300.0]],
                    direction="forward",
                )
            ],
        )
        report = build_region(testville_config, "middle", out_root=tmp_path / "out")
        assert report.opposed_pair_ends == 0

    def test_a_co_directional_neighbour_is_not_an_opposed_half(
        self, tmp_path, testville_config
    ) -> None:
        """Two one-way ribbons running the SAME way, overlapping exactly as an
        opposed pair does.

        🔴 **This is the test the endpoint rule never needed and the geometric one
        cannot ship without.** Two carriageways of one road share both nodes only
        by accident, so what replaced that rule is proximity — and proximity alone
        cannot tell a dual carriageway from a service road beside a main one, or
        from a bus lane drawn as its own edge. A centre line between two flows
        that go the same way instructs a player to stay left of traffic
        overtaking on their left.
        """
        _write_graph(
            tmp_path,
            [
                {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 2, "pos": [100.0, 0.0, 304.0], "kind": "endpoint"},
                {"id": 3, "pos": [500.0, 0.0, 304.0], "kind": "endpoint"},
            ],
            [
                _edge(
                    0,
                    0,
                    1,
                    [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]],
                    direction="forward",
                ),
                _edge(
                    1,
                    2,
                    3,
                    [[100.0, 0.0, 304.0], [500.0, 0.0, 304.0]],
                    direction="forward",
                ),
            ],
        )
        report = build_region(testville_config, "middle", out_root=tmp_path / "out")

        assert report.opposed_pair_ends == 0
        assert report.opposed_pairs_one_sided == 0
        mesh = _mesh(tmp_path)
        road = _carriageway(mesh)
        assert all(_decode(c)["centre"] == 0 for c in mesh.uv2[road, 0])

    def test_a_one_sided_vote_publishes_nothing(self, tmp_path, testville_config) -> None:
        """Three anti-parallel ribbons abreast, so the middle one is the nearest
        partner of both its neighbours and can only vote back to one of them.

        🔴 **`opposed_pairs_one_sided` is reachable and this is what reaches it.**
        Each half computes the join in its own lane coordinate, so an unreturned
        vote is a line the other half does not draw — the 3.9 m double line
        `P3-12` shipped on FLEMING ROAD. The outer ribbon here votes for the
        middle one, the middle one votes back to the *nearer* outer one, and the
        loser publishes nothing rather than half a pair.
        """
        _write_graph(
            tmp_path,
            [
                {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 2, "pos": [100.0, 0.0, 302.0], "kind": "endpoint"},
                {"id": 3, "pos": [500.0, 0.0, 302.0], "kind": "endpoint"},
                {"id": 4, "pos": [100.0, 0.0, 306.0], "kind": "endpoint"},
                {"id": 5, "pos": [500.0, 0.0, 306.0], "kind": "endpoint"},
            ],
            [
                _edge(
                    0,
                    0,
                    1,
                    [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]],
                    direction="forward",
                ),
                _edge(
                    1,
                    3,
                    2,
                    [[500.0, 0.0, 302.0], [100.0, 0.0, 302.0]],
                    direction="forward",
                ),
                _edge(
                    2,
                    4,
                    5,
                    [[100.0, 0.0, 306.0], [500.0, 0.0, 306.0]],
                    direction="forward",
                ),
            ],
        )
        report = build_region(testville_config, "middle", out_root=tmp_path / "out")

        # Two ends of one pair published; the third ribbon voted and was refused.
        assert report.opposed_pair_ends == 2
        assert report.opposed_pairs_one_sided == 1
        assert report.opposed_pairs_unpublishable == 0
        # 🔴 **And the one-sided vote reaches the manifest as nothing** — the
        # pairing the join is drawn from is the mutual one, so a half that
        # nobody chose back cannot hand `roadmarks.py` a line to draw down the
        # middle of a single carriageway (`Q125`).
        assert _manifest(tmp_path)["opposed_pairs"] == [[0, 1, pytest.approx(2.0, abs=0.5)]]

    def test_two_ribbons_a_seam_apart_are_one_road(self, tmp_path, testville_config) -> None:
        """🔴 **`Q125`: a seam thinner than a kerb is not a median.** The drawn
        ribbons here are 9.6 m wide and their centrelines 9.8 m apart, so they
        miss touching by 0.2 m — EXPO DRIVE EAST's own geometry, where the two
        carriageways read as one road with opposing traffic on it and the pair
        was refused by 0.245 m. The reach is the drawn width plus one kerb, the
        same 0.5 m `_paint_flanks` used, until `P3-35e` deleted it, to decide a flank
        is too thin to draw.

        ⚠️ **Mutation-check it rather than reading the count**: drop the kerb
        term from `_opposed_gaps`' `reach` and this fails, which is the whole of
        what says the term is doing something.
        """
        # 9.6 m ribbons 9.8 m apart: a 0.2 m seam, under the 0.5 m kerb.
        _abreast(tmp_path, 0.0, 9.8)
        report = build_region(testville_config, "middle", out_root=tmp_path / "out")

        [(here, there, gap)] = [tuple(row) for row in _manifest(tmp_path)["opposed_pairs"]]
        assert (here, there) == (0, 1)
        assert gap == pytest.approx(9.8, abs=0.1)
        # 🔴 **And the codec is not widened with it.** The join sits past what a
        # lane coordinate can reach, so `centre_step` refuses it and the pair
        # travels for the geometry alone — which is why `roads.glb` does not move.
        assert report.opposed_pairs_unpublishable == 2
        mesh = _mesh(tmp_path)
        road = _carriageway(mesh)
        assert all(_decode(code)["centre"] == 0 for code in mesh.uv2[road, 0])

    def test_two_ribbons_a_median_apart_are_two_roads(self, tmp_path, testville_config) -> None:
        """The other side of it: a gap a kerb could not close is a median, and
        the pair is refused rather than painted over."""
        # 2.4 m of clear ground between the two ribbons: a median, not a seam.
        _abreast(tmp_path, 0.0, 12.0)
        report = build_region(testville_config, "middle", out_root=tmp_path / "out")

        assert report.opposed_pair_ends == 0
        assert _manifest(tmp_path)["opposed_pairs"] == []

    def test_a_pair_is_published_once_for_the_stage_that_draws_its_join(
        self, dualville, tmp_path
    ) -> None:
        """`Q125`: `roadmarks.py` draws the join between two opposed flows, and
        a join is one line rather than one per half.

        ⚠️ **The counter above counts ENDS and this counts PAIRS**, which is the
        whole reason the manifest carries the pair rather than a flag per edge:
        published per half, the line would be drawn twice, coincident, and every
        counter would still close.
        """
        city, _ = dualville
        report = build_region(city, "middle", out_root=tmp_path / "out")

        assert report.opposed_pair_ends == 2
        pairs = _manifest(tmp_path)["opposed_pairs"]
        # ⚠️ The gap is the pair's own measurement, not the 4 m the fixture's
        # middles are apart: both halves run into the shared nodes at either
        # end, so the separation the pairing agrees on is smaller than the
        # widest part of it. What this pins is the shape — one row, both ids,
        # a real separation — because the measurement is `_pair_gap_m`'s and
        # has tests of its own.
        [(here, there, gap)] = [tuple(row) for row in pairs]
        assert (here, there) == (0, 1)
        assert 0.0 < gap < 4.0

    def test_the_surface_asks_the_engine_for_its_shader(self, testville, tmp_path) -> None:
        """glTF cannot say "use this shader", so the material name is the whole
        channel — and it fails silently in the engine, which is why
        `verify_road_surface.gd` checks the other end of it.
        """
        build_region(testville[0], "middle", out_root=tmp_path / "out")

        # Read off the document rather than through `read_glb`, which restores
        # geometry and drops the material name — the same reason
        # `test_gltf.py` reads the JSON to pin `city_facade`.
        for chunk in _manifest(tmp_path)["chunks"]:
            raw = (tmp_path / "out" / "middle" / chunk["file"]).read_bytes()
            length, _ = struct.unpack_from("<II", raw, 12)
            document = json.loads(raw[20 : 20 + length])
            # The collider's material is named after its mesh and never read:
            # the importer removes the mesh with it (`P5-12`).
            assert [material["name"] for material in document["materials"]] == [
                SURFACE_MATERIAL,
                f"{SURFACE_COLLIDER_NAME}_material",
            ]


class TestKerbside:
    """`P3-13`: where the kerbside yellow applies, and what kind it is (`Q54`).

    ⚠️ **The rail these land on is the whole thing.** `COLOR_0.a` is written per
    rail, so the nearside extent and the offside extent are the same channel on
    opposite sides of one strip — and swapping them mirrors every yellow line in
    the city while rendering as a perfectly ordinary road. `kerbville` is built
    with the two sides deliberately unequal so that a payload writing one
    answer to both cannot pass.
    """

    def test_the_extent_lands_on_the_rail_of_its_own_side(self, kerbville) -> None:
        city, root = kerbville
        build_region(city, "middle", out_root=root / "out")
        mesh = _mesh(root)

        road = _carriageway(mesh)
        near = road & (mesh.uvs[:, 0] == 0.0)
        off = road & (mesh.uvs[:, 0] == 2.0)
        along = mesh.uvs[:, 1]
        alpha = mesh.colours[:, 3]

        def at(rail: np.ndarray, distance: float) -> set[int]:
            """The alpha carried by that rail's station a given V along.

            Asked station by station rather than over a V window, because the
            stations *are* the answer: this edge has two of its own and eight
            inserted, and between two boundaries there is nothing in between to
            sample. That is the whole design — the value is exact where it is
            written and linear over the half metre between a boundary's pair.
            """
            return set(alpha[rail & np.isclose(along, distance)].tolist())

        # The edge shares no node, so nothing is trimmed and V is the published
        # distance along it exactly. Each boundary is asked from both sides.
        assert at(near, 99.75) == {0} and at(near, 100.25) == {255}
        assert at(near, 299.75) == {255} and at(near, 300.25) == {0}
        assert at(off, 149.75) == {0} and at(off, 150.25) == {255}
        assert at(off, 199.75) == {255} and at(off, 200.25) == {0}
        # And the ends of the edge, where neither side is restricted.
        assert at(near, 0.0) == at(off, 0.0) == {0}

    def test_the_codec_says_the_kind_each_side_carries(self, kerbville) -> None:
        city, root = kerbville
        build_region(city, "middle", out_root=root / "out")
        mesh = _mesh(root)

        codes = {
            (fields["kerb_near"], fields["kerb_off"])
            for fields in (_decode(code) for code in mesh.uv2[:, 0])
            if fields["surface_class"] == 0
        }
        assert codes == {(MARKING_KERB_DOUBLE, MARKING_KERB_SINGLE)}

    def test_a_kerb_the_source_does_not_restrict_says_none_not_absent(self, markedville) -> None:
        """The distinction the shader ignores and a later consumer will not.
        `ABSENT` is a city with no such layer; `NONE` is a kerb the source was
        consulted about and leaves alone, which is where a car may pull over."""
        city, root = markedville
        build_region(city, "middle", out_root=root / "out")
        mesh = _mesh(root)

        for code in mesh.uv2[:, 0]:
            fields = _decode(code)
            if fields["surface_class"] != 0:
                continue
            assert fields["kerb_near"] == MARKING_KERB_NONE
            assert fields["kerb_off"] == MARKING_KERB_NONE

    def test_a_graph_that_publishes_no_runs_at_all_says_absent(
        self, tmp_path, testville_config
    ) -> None:
        """A city whose sources carry no no-stopping layer draws no kerbside
        line rather than the invented one `P3-12` shipped."""
        edge = _edge(0, 0, 1, [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]])
        del edge["kerbside"]
        _write_graph(
            tmp_path,
            [
                {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
                {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
            ],
            [edge],
        )
        build_region(testville_config, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        for code in mesh.uv2[:, 0]:
            fields = _decode(code)
            if fields["surface_class"] == 0:
                assert fields["kerb_near"] == fields["kerb_off"] == MARKING_KERB_ABSENT

    def test_a_boundary_gets_a_station_either_side_of_it(self, kerbville) -> None:
        """What the exact V-range costs, and why. Without the pair the alpha
        would ramp from one graph vertex to the next — 400 m here."""
        city, root = kerbville
        report = build_region(city, "middle", out_root=root / "out")
        mesh = _mesh(root)

        along = sorted(set(np.round(mesh.uvs[_carriageway(mesh), 1], 3).tolist()))
        # Four boundaries fall inside the drawn ribbon — both ends of both runs
        # — and each takes a pair.
        assert report.kerb_stations == 8
        for ends_at in (100.0, 150.0, 200.0, 300.0):
            assert pytest.approx(ends_at - 0.25, abs=1e-3) in along
            assert pytest.approx(ends_at + 0.25, abs=1e-3) in along

    def test_the_longer_kind_wins_a_side_and_the_shorter_is_reported(self) -> None:
        """The codec says one kind per side and the source does not promise one.
        Reported rather than designed around — 183 m of Wan Chai's 26,065."""
        published = {
            "kerbside": [
                {"side": "near", "from_m": 0.0, "to_m": 90.0, "kind": "double"},
                {"side": "near", "from_m": 90.0, "to_m": 100.0, "kind": "single"},
            ]
        }
        extents, kinds, minority_m = _kerbside(published)

        assert kinds["near"] == MARKING_KERB_DOUBLE
        assert kinds["off"] == MARKING_KERB_NONE
        assert minority_m == pytest.approx(10.0)
        assert extents["near"] == [(0.0, 90.0), (90.0, 100.0)]

    def test_an_inserted_station_carries_the_interpolated_half_width(self) -> None:
        """`_at` interpolates every column, so a station inserted where the
        carriageway is tapering arrives at the width it should be. Asserted
        because nothing about the geometry would look wrong if it did not."""
        points = np.array([[0.0, 0.0, 0.0, 2.0], [100.0, 0.0, 0.0, 4.0]])
        merged, inserted = _insert_stations(points, [50.0])

        # The indices are where the new rows landed *after* the merge sort, not
        # how many there were — `_add_kerb_stations` marks `_INSERTED` by them.
        assert inserted.tolist() == [1, 2]
        assert merged[1][0] == pytest.approx(49.75)
        assert merged[1][3] == pytest.approx(2.995)
        assert merged[2][3] == pytest.approx(3.005)

    def test_a_boundary_on_an_existing_station_inserts_nothing(self) -> None:
        """The alternative is a quad thin enough to collapse in `build`, for an
        extent that is already right to within a tenth of a metre."""
        points = np.array([[0.0, 0.0, 0.0, 2.0], [50.0, 0.0, 0.0, 2.0], [100.0, 0.0, 0.0, 2.0]])
        # The boundary's leading station would land 0.05 m from the vertex at
        # 50 m, so only the trailing one is inserted — between the 50 m station
        # it was too close to and the 100 m one.
        _, inserted = _insert_stations(points, [50.2])
        assert inserted.tolist() == [2]

    def test_the_widest_legal_code_survives_the_shaders_decode(self) -> None:
        """The codec's own promise, and what `floor(x + 0.5)` in the shader
        rests on: not that the code is exact in float32 — every integer to 2^24
        is — but that the code PLUS A HALF is, which stops at 2^23. `Q126`'s
        field fills the channel to 8,388,607, one under it, and the odd
        neighbour just past it is what the next field would silently corrupt.
        """
        assert MARKING_CODE_MAX == 8_388_607 == 2**23 - 1
        half = np.float32(0.5)
        assert np.floor(np.float32(MARKING_CODE_MAX) + half) == MARKING_CODE_MAX
        past = 2**23 + 1
        assert np.floor(np.float32(past) + half) != past, "the channel is full, and this is why"


# One bend, twice: level and then climbing 6 m over the second segment. 210 m to
# 250 m puts all four restriction boundaries on that segment and clear of both
# ends, so each takes its pair and none is lost to a trim.
_BEND = [[100.0, 0.0, 300.0], [300.0, 0.0, 300.0], [400.0, 6.0, 400.0]]
_FLAT = [[x, 0.0, z] for x, _, z in _BEND]
_BEND_RUNS = [{"side": "near", "from_m": 210.0, "to_m": 250.0, "kind": "double"}]


class TestKerbRailStations:
    """Which of `P3-13`'s stations the kerb rails are drawn from.

    The stations exist so `COLOR_0.a` can turn on in half a metre. Only the
    carriageway reads that channel, so the kerbs should not be paying for them
    — and mostly they do not. **The exception is the point of these tests.** A
    mitred vertex is displaced along its segment as well as across it, so a kerb
    rail's chord spans a different stretch of road than the centreline does, and
    height is interpolated along the centreline. Where the road climbs through a
    bend the two disagree, and the station is carrying the difference.
    """

    def _street(self, root, config, polyline, kerbside):
        """One street on its own, built into its own directory."""
        _write_graph(
            root,
            [
                {"id": 0, "pos": polyline[0], "kind": "endpoint"},
                {"id": 1, "pos": polyline[-1], "kind": "endpoint"},
            ],
            [_edge(0, 0, 1, polyline, kerbside=kerbside)],
        )
        return build_region(config, "middle", out_root=root / "out"), _mesh(root)

    def test_a_straight_street_pays_no_kerb_vertex_for_its_restrictions(
        self, tmp_path, testville_config
    ) -> None:
        """The whole point of the thinning: a flat straight ribbon draws exactly
        the kerb it drew before `P3-13`, while the carriageway gains the
        stations that carry the extent."""
        line = [[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]]
        plain, plain_mesh = self._street(tmp_path / "plain", testville_config, line, [])
        painted, painted_mesh = self._street(
            tmp_path / "painted",
            testville_config,
            line,
            [{"side": "near", "from_m": 100.0, "to_m": 300.0, "kind": "double"}],
        )

        assert plain.kerb_stations == 0
        assert painted.kerb_stations == 4
        assert painted.kerb_rail_stations == 0
        assert _kerb(painted_mesh).sum() == _kerb(plain_mesh).sum()
        # And the carriageway is where the cost went, which is the trade.
        assert _carriageway(painted_mesh).sum() > _carriageway(plain_mesh).sum()

    def test_a_station_the_kerb_needs_for_its_height_is_kept(
        self, tmp_path, testville_config
    ) -> None:
        """One variable changed — the same bend, level and then climbing.

        Level, the mitre displaces the rail along the segment and nothing
        depends on where along it a station is, so every station is free. Put
        6 m of climb on the same plan and the station beside the bend is
        carrying a kerb height its own chord does not have. Dropping it would
        step the kerb away from the carriageway it is welded to.
        """
        flat, _ = self._street(tmp_path / "flat", testville_config, _FLAT, _BEND_RUNS)
        bend, _ = self._street(tmp_path / "bend", testville_config, _BEND, _BEND_RUNS)

        assert flat.kerb_stations == bend.kerb_stations == 4
        assert flat.kerb_rail_stations == 0
        assert flat.kerb_rail_offset_m == pytest.approx(0.0, abs=1e-9)
        # Only the station next to the bend: the other three have neighbours on
        # the same segment, or an unmitred ribbon end.
        assert bend.kerb_rail_stations == 1

    def test_a_trim_cut_is_not_counted_as_a_station_P3_13_asked_for(self) -> None:
        """`_at` lerps every column, so a trim cut landing between an original
        station and an inserted one arrives carrying a *fraction* of `_INSERTED`.

        It is a ribbon end, not a boundary marker — and it is pinned either way,
        so no geometry depends on the distinction. What depends on it is the
        published residue: 316 of this region's ribbons start or end on such a
        station, and reading the column as truthy rather than as `== 1.0` counts
        every one of them as `P3-13` cost it does not have. Nothing else would
        fail, which is why this is pinned here.
        """
        # x, y, z, half-width, `_INSERTED` — the two ends part-way between an
        # original station and an inserted one, as `trim` leaves them.
        points = np.array(
            [
                [0.0, 0.0, 0.0, 2.0, 0.4],
                [10.0, 0.0, 0.0, 2.0, 1.0],
                [20.0, 0.0, 0.0, 2.0, 0.0],
                [30.0, 0.0, 0.0, 2.0, 1.0],
                [40.0, 0.0, 0.0, 2.0, 0.6],
            ]
        )
        rail = points[:, :3]
        report = SurfaceReport()
        stations = _rail_stations(points, [(0, len(points))], (rail,) * 4, report)

        # Both ends stay because they are ends; the two inserted stations go
        # because the rail runs straight through them.
        assert stations.tolist() == [0, 2, 4]
        assert report.kerb_rail_stations == 0

    def test_a_buried_kerb_run_keeps_its_ends(self, dualville, tmp_path) -> None:
        """`_hide_buried_kerbs` decides coverage per quad, so a run end is a
        station where the answer changes. Thinning one away would merge two
        quads that disagree and move the region's largest kerb number, with
        nothing failing. Asserted as an invariant: restrictions are paint, and
        paint cannot change how much kerb another carriageway covers.
        """
        city, root = dualville
        plain = build_region(city, "middle", out_root=root / "out")

        graph = json.loads((root / "out" / "middle" / ROADGRAPH_NAME).read_text(encoding="utf-8"))
        for edge in graph["edges"]:
            edge["kerbside"] = [{"side": "near", "from_m": 40.0, "to_m": 260.0, "kind": "double"}]
        painted_root = tmp_path / "painted"
        _write_graph(painted_root, graph["nodes"], graph["edges"])
        painted = build_region(city, "middle", out_root=painted_root / "out")

        assert painted.kerb_stations > 0
        assert painted.buried_kerb_m == pytest.approx(plain.buried_kerb_m)


def _covered(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Whether each plan point falls inside some triangle, by edge sign.

    The 2D cross product is written out because `np.cross` dropped support for
    2-vectors in numpy 2.0 — the same trap `roads.py` documents.
    """

    def side(start: np.ndarray, end: np.ndarray, point: np.ndarray) -> np.ndarray:
        span = end - start
        offset = point - start
        return span[:, 0] * offset[:, 1] - span[:, 1] * offset[:, 0]

    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    covered = np.zeros(len(points), dtype=bool)
    for index, point in enumerate(points):
        first, second, third = side(a, b, point), side(b, c, point), side(c, a, point)
        covered[index] = (
            ((first >= 0) & (second >= 0) & (third >= 0))
            | ((first <= 0) & (second <= 0) & (third <= 0))
        ).any()
    return covered


class TestTheRibbonIsClampedToItsDeck:
    """🔴 The paint stops at the structure, per station and per side (`Q107`).

    Every way this breaks draws a perfectly good carriageway. A clamp applied
    with the two rims swapped puts the ribbon on the wrong side of its own deck;
    one applied where no deck was measured collapses the whole at-grade network;
    one that extends rather than cuts invents carriageway, which is `Q54`. None
    of the three is visible in a counter, and the first two are not visible in a
    frame either unless you already know where the deck is.
    """

    HALF = np.array([2.0, 2.0, 2.0])
    WIDE = np.full(3, np.inf)

    def test_no_deck_leaves_the_ribbon_exactly_where_it_was(self) -> None:
        """The inertness the whole at-grade network rests on.

        ⚠️ Asserted first and against an **`inf`** rim, because that is what
        `_deck_rims` returns for every level-0 edge — the ordinary case, not the
        exceptional one. A 0.0 default here would collapse 737 edges to nothing.
        """
        upper, lower, refused = _clamped_rails(self.HALF, self.WIDE, self.WIDE, 0.0)
        assert upper == pytest.approx(self.HALF)
        assert lower == pytest.approx(-self.HALF)
        assert refused == 0

    def test_a_shift_carries_the_ribbon_without_changing_its_width(self) -> None:
        upper, lower, _ = _clamped_rails(self.HALF, self.WIDE, self.WIDE, 1.5)
        assert upper == pytest.approx(self.HALF + 1.5)
        assert lower == pytest.approx(-self.HALF + 1.5)

    def test_a_deck_wider_than_the_paint_changes_nothing(self) -> None:
        """🔴 It cuts and never extends — `Q54`'s rule, and why this is licensed.

        A clamp that took the rim whenever it differed would widen the ribbon
        onto structure no publisher called carriageway, which is precisely the
        move `Q54` refuses and `Q105` was careful not to make.
        """
        upper, lower, _ = _clamped_rails(self.HALF, np.full(3, 9.0), np.full(3, 9.0), 0.0)
        assert upper == pytest.approx(self.HALF)
        assert lower == pytest.approx(-self.HALF)

    def test_each_side_is_cut_independently(self) -> None:
        """The whole point: one number per edge cannot fit a varying deck."""
        upper, lower, _ = _clamped_rails(self.HALF, np.array([0.5, 2.0, 9.0]), np.full(3, 9.0), 0.0)
        assert upper == pytest.approx([0.5, 2.0, 2.0])
        assert lower == pytest.approx([-2.0, -2.0, -2.0]), "the right rail must not move"

    def test_the_two_rims_are_not_interchangeable(self) -> None:
        """A swap draws the carriageway on the wrong side and renders fine."""
        left, right = np.full(3, 0.5), np.full(3, 9.0)
        upper, lower, _ = _clamped_rails(self.HALF, left, right, 0.0)
        swapped_upper, swapped_lower, _ = _clamped_rails(self.HALF, right, left, 0.0)
        assert upper != pytest.approx(swapped_upper)
        assert lower != pytest.approx(swapped_lower)

    def test_crossing_rails_keep_the_unclamped_ribbon_and_are_counted(self) -> None:
        """🔴 `Q105`'s fallback: no answer is not the same as a zero-width road.

        The ribbon lies wholly off its own deck here, so the clamp has none —
        and collapsing to zero would put a hole in the collider rather than a
        narrow road.
        """
        # Deck entirely to the left of a ribbon shifted hard right.
        upper, lower, refused = _clamped_rails(self.HALF, np.full(3, -5.0), np.full(3, 9.0), 0.0)
        assert refused == 3
        assert upper == pytest.approx(self.HALF)
        assert lower == pytest.approx(-self.HALF)

    def test_rails_that_merely_touch_are_refused_too(self) -> None:
        """A zero-width quad collapses in `_Builder.build` and reads as a gap."""
        _, _, refused = _clamped_rails(np.array([2.0]), np.array([-2.0]), np.array([2.0]), 0.0)
        assert refused == 1


class TestDeckRimsFallBackToNoConstraint:
    """A missing, empty or mis-aligned rim list must not cut anything."""

    def test_an_edge_without_rims_is_unconstrained(self) -> None:
        left, right, _ = _deck_rims({"deck_rim_m": []}, 3)
        assert np.isinf(left).all() and np.isinf(right).all()
        assert len(left) == len(right) == 3

    def test_a_missing_key_is_unconstrained(self) -> None:
        left, _, _ = _deck_rims({}, 2)
        assert np.isinf(left).all()

    def test_a_length_mismatch_is_unconstrained_rather_than_raising(self) -> None:
        """🔴 The graph and this stage disagreeing about the polyline.

        Deliberately not an exception: the rims are per published vertex and so
        are the half-widths, so a mismatch means the two documents disagree —
        and the ribbon it always drew is a better answer than a clamped one
        built on a mis-aligned array.
        """
        left, right, _ = _deck_rims({"deck_rim_m": [[1.0, 2.0]]}, 3)
        assert np.isinf(left).all() and np.isinf(right).all()

    def test_a_matching_list_is_read_in_order(self) -> None:
        left, right, _ = _deck_rims({"deck_rim_m": [[1.0, 2.0], [3.0, 4.0]]}, 2)
        assert left == pytest.approx([1.0, 3.0])
        assert right == pytest.approx([2.0, 4.0])


class TestDeckRimsOffStructure:
    """`Q113`'s branch, as a unit — the stage test below is end to end."""

    def test_a_rim_is_discarded_where_the_vertex_is_not_on_structure(self) -> None:
        left, right, discarded = _deck_rims(
            {"deck_rim_m": [[1.0, 2.0], [3.0, 4.0]], "on_structure": [True, False]}, 2
        )
        assert left[0] == 1.0
        assert right[0] == 2.0
        assert left[1] == np.inf
        assert right[1] == np.inf
        assert discarded == 1

    def test_a_mismatched_on_structure_discards_nothing_and_counts_nothing(self) -> None:
        """🔴 One rule behind one guard.

        The count used to be taken in `_prepare` under `deck_rim_m`'s length
        rather than `on_structure`'s, so a graph where the two disagreed booked
        discards this function had deliberately not made.
        """
        left, _, discarded = _deck_rims(
            {"deck_rim_m": [[1.0, 2.0], [3.0, 4.0]], "on_structure": [False]}, 2
        )
        assert left[1] == 3.0
        assert discarded == 0

    def test_a_vertex_that_carried_no_rim_is_not_counted_as_a_discard(self) -> None:
        # `inf` is already no constraint, so dropping it drops nothing.
        _, _, discarded = _deck_rims(
            {"deck_rim_m": [[float("inf"), float("inf")]], "on_structure": [False]}, 1
        )
        assert discarded == 0


class TestTheClampReachesTheBuiltRibbon:
    """The clamp end to end, through `build_region` and out to the manifest.

    ⚠️ **The unit tests above exercise `_clamped_rails` and `_deck_rims`
    directly; nothing else in this file publishes a rim**, so without this the
    stage could stop threading them and every one of those would still pass.
    """

    def _built(self, testville_config, tmp_path: Path, **overrides) -> dict:
        # 🔴 **A rim implies `on_structure` (`Q113`).** `_edge` defaults every
        # vertex to off structure, which is right for the at-grade fixtures and
        # is a contradiction for a decked one — and since `Q113` the stage reads
        # it that way and refuses the clamp. Set here rather than in each case
        # so the coupling is stated once; `TestDeckRimsOffStructure` above and
        # the end-to-end case below are what pin the refusal itself.
        if "deck_rim_m" in overrides and "on_structure" not in overrides:
            overrides["on_structure"] = [True] * len(overrides["deck_rim_m"])
        _write_graph(
            tmp_path,
            [{"id": 0, "pos": [0.0, 0.0, 0.0]}, {"id": 1, "pos": [40.0, 0.0, 0.0]}],
            [_edge(1, 0, 1, [[0.0, 0.0, 0.0], [40.0, 0.0, 0.0]], **overrides)],
        )
        build_region(testville_config, "middle", out_root=tmp_path / "out")
        manifest = json.loads((tmp_path / "out" / "middle" / SURFACE_MANIFEST_NAME).read_text())
        return manifest["carriageway"][0]

    def test_an_edge_without_rims_publishes_a_centred_ribbon(
        self, testville_config, tmp_path: Path
    ) -> None:
        """The at-grade case, and what every other fixture in this file relies on."""
        entry = self._built(testville_config, tmp_path)
        assert entry["offset_m"] == pytest.approx([0.0] * len(entry["offset_m"]))
        assert min(entry["half_width_m"]) > 0.0

    def test_a_narrow_deck_cuts_the_ribbon_and_moves_its_centre(
        self, testville_config, tmp_path: Path
    ) -> None:
        """🔴 The whole point, asserted on what SHIPS rather than on a local.

        A deck reaching 1.0 m left and 3.0 m right of the centreline, under a
        ribbon the config draws wider: the published half-width falls to 2.0 and
        the centre moves to -1.0. That asymmetry is what `Q107` exists for and
        what no symmetric width could produce.
        """
        entry = self._built(testville_config, tmp_path, deck_rim_m=[[1.0, 3.0], [1.0, 3.0]])
        assert entry["half_width_m"] == pytest.approx([2.0] * len(entry["half_width_m"]))
        assert entry["offset_m"] == pytest.approx([-1.0] * len(entry["offset_m"]))

    def test_a_rim_on_a_vertex_that_is_not_on_structure_is_ignored(
        self, testville_config, tmp_path: Path
    ) -> None:
        """🔴 `Q113`, end to end: a ramp on the ground has no deck to be cut to.

        `carriageway._deck_reach` walks outward from the centreline and reports
        whatever contiguous slab it finds, and where a ramp descends to grade it
        finds the structure petering out — `e208` FLEMING ROAD published a left
        rim of **0.100 m**, `DECK_ACROSS_M` exactly, and the clamp cut the drawn
        ribbon 5.60 -> 3.15 m on the strength of it. The graph already says
        which vertices stand on structure, so the rim is discarded where they do
        not.

        The same rim as the case above, which cuts to 2.0; off structure it must
        publish the ribbon the config draws.
        """
        entry = self._built(
            testville_config,
            tmp_path,
            deck_rim_m=[[1.0, 3.0], [1.0, 3.0]],
            on_structure=[False, False],
        )
        assert min(entry["half_width_m"]) > 2.0
        assert entry["offset_m"] == pytest.approx([0.0] * len(entry["offset_m"]))

    def test_one_vertex_off_structure_keeps_the_other_clamped(
        self, testville_config, tmp_path: Path
    ) -> None:
        """⚠️ Per vertex, not per edge — a ramp goes off structure partway down.

        `np.interp` carries `inf` across the segment between them, so the
        clamped end keeps its cut exactly at its own vertex and the ribbon
        flares back to full width toward the deckless one. On `e208` that flare
        runs over an 8 m segment, which is the landing opening out.
        """
        entry = self._built(
            testville_config,
            tmp_path,
            deck_rim_m=[[1.0, 3.0], [1.0, 3.0]],
            on_structure=[True, False],
        )
        assert min(entry["half_width_m"]) == pytest.approx(2.0)
        assert max(entry["half_width_m"]) > 2.0

    def test_a_deck_wider_than_the_ribbon_publishes_it_unchanged(
        self, testville_config, tmp_path: Path
    ) -> None:
        """It cuts and never extends (`Q54`) — through the stage, not just the
        function."""
        # ⚠️ **Both sides declare the same `on_structure`.** It is not only the
        # clamp's gate since `Q113` — `Q23` draws an on-structure edge at its
        # authored width instead of the playability floor — so a baseline that
        # left it at the fixture's default would differ from the rimmed build
        # for a reason that has nothing to do with the rim.
        on = {"on_structure": [True, True]}
        wide = self._built(testville_config, tmp_path / "a", **on)
        entry = self._built(
            testville_config, tmp_path / "b", deck_rim_m=[[40.0, 40.0], [40.0, 40.0]], **on
        )
        assert entry["half_width_m"] == pytest.approx(wide["half_width_m"])
        assert entry["offset_m"] == pytest.approx(wide["offset_m"])


class TestJoinCaps:
    """`Q116`'s one exception to "the non-owner draws nothing" (`P5-7f`): a
    junction cap admits the mouth of a neighbour-owned run, and a cap goes
    whole to the region containing its node.

    Built through the roads stage on `testville_pair`, because the question is
    about two regions' documents agreeing: `middle` holds the junction at
    (700, 620) where its SPOKE leaves east's LONG, and `east` holds the one at
    (1100, 100) where middle's MAIN meets east's BACK. Each region has one
    owned arm and one foreign arm at *both* nodes, so which region caps which
    is decided by the node alone.
    """

    @staticmethod
    def _build(city, tmp_path: Path) -> dict[str, tuple[SurfaceReport, dict]]:
        out = {}
        for region in ("middle", "east"):
            roads.build_region(
                city, region, sources_root=tmp_path / "sources", out_root=tmp_path / "out"
            )
            report = build_region(city, region, out_root=tmp_path / "out")
            manifest = json.loads((tmp_path / "out" / region / SURFACE_MANIFEST_NAME).read_text())
            out[region] = (report, manifest)
        return out

    def test_each_seam_junction_is_capped_by_the_region_holding_its_node(
        self, testville_pair, tmp_path
    ) -> None:
        city, sources = testville_pair
        built = self._build(city, sources)

        for region in ("middle", "east"):
            report, manifest = built[region]
            assert report.caps_with_foreign_mouth == 1
            assert report.caps_in_neighbour == 1
            assert manifest["join"] == {
                "foreign_ends": report.foreign_ends,
                "caps_with_foreign_mouth": 1,
                "caps_in_neighbour": 1,
            }
            # Drawn, trimmed and measured: the owned edges and nothing else.
            graph = json.loads((sources / "out" / region / ROADGRAPH_NAME).read_text())
            owned = {int(edge["id"]) for edge in graph["edges"]}
            assert {int(row["edge"]) for row in manifest["carriageway"]} == owned
            assert report.edges == len(owned)

    def test_without_the_foreign_list_the_seam_junction_has_no_cap(
        self, testville_pair, tmp_path
    ) -> None:
        """The mutation: strip `foreign_edges` from east's graph and its cap at
        (1100, 100) is a lone arm with nothing to join — one cap fewer, and the
        counters at 0. That is what says the cap came from the foreign mouth."""
        city, sources = testville_pair
        built = self._build(city, sources)
        with_foreign, _ = built["east"]

        path = sources / "out" / "east" / ROADGRAPH_NAME
        graph = json.loads(path.read_text(encoding="utf-8"))
        graph["foreign_edges"] = []
        path.write_text(json.dumps(graph), encoding="utf-8")
        without = build_region(city, "east", out_root=sources / "out")

        assert without.junctions == with_foreign.junctions - 1
        assert without.caps_with_foreign_mouth == 0
        assert without.caps_in_neighbour == 0
        assert without.foreign_ends == 0


class TestStubClusters:
    """`P3-31`: nodes joined by a link clamped at both ends are one junction and
    get one cap, so the ground between their per-node caps is road.

    Wan Chai's HKCEC and Lockhart / Fleming junctions are the sites; `Q104`'s
    box-junction grader is what measured them, and the per-node cap left the
    taxi parked on grey in both. Two of `stubville`'s three tests are the
    mutation: with the ceiling loosened the same graph has no stub, no cluster
    and the void back, which is what makes `clusters` a counter (`Q72`).
    """

    VOID = np.array([[307.0, 305.7], [307.0, 294.3]])

    def test_a_stub_cluster_is_capped_once_and_the_void_is_road(self, stubville, tmp_path) -> None:
        city, _ = stubville
        report = build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        assert report.stub_edges == 1
        assert report.clusters == 1
        assert report.cluster_nodes == 2
        assert report.junctions == 1
        corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
        assert _covered(self.VOID, corners).all()
        assert _manifest(tmp_path)["clusters"] == {
            "stub_edges": 1,
            "count": 1,
            "nodes": 2,
            "corridors": 0,
        }

    def test_a_looser_ceiling_dissolves_the_cluster(self, stubville, tmp_path) -> None:
        """At 49% of 14 m the ceiling is 6.86 m, past the 6 m radius, so neither
        trim is clamped: no stub, two per-node caps, and the void is back."""
        yaml = (tmp_path / "testville.yaml").read_text(encoding="utf-8")
        assert yaml.count("junction_trim_max_fraction: 0.35") == 1
        (tmp_path / "loose.yaml").write_text(
            yaml.replace("junction_trim_max_fraction: 0.35", "junction_trim_max_fraction: 0.49"),
            encoding="utf-8",
        )
        loose = load_config(tmp_path / "loose.yaml")

        report = build_region(loose, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        assert report.clamped_trims == 0
        assert report.stub_edges == 0
        assert report.clusters == 0
        assert report.junctions == 2
        corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
        assert not _covered(self.VOID, corners).any()

    def test_the_stub_lends_no_corner_to_the_cluster_cap(self, stubville, tmp_path) -> None:
        """The cap is the hull of the four arm mouths: 12 m wide, from the north
        mouths at z 294 to the south mouths at z 306, and 300 - 6 to 314 + 6
        along. A stub corner in the hull could only shrink nothing — it lies
        inside — so the check is the ring itself, corner for corner."""
        city, _ = stubville
        report = build_region(city, "middle", out_root=tmp_path / "out")

        ((level, ring),) = report.cap_rings
        assert level == 0
        plan = {(round(float(x), 3), round(float(z), 3)) for x, _, z in ring}
        assert plan == {(294.0, 294.0), (320.0, 294.0), (320.0, 306.0), (294.0, 306.0)}

    def test_a_stub_across_the_seam_joins_nothing(self, stubville, tmp_path) -> None:
        """`P5-7f`'s seam: the neighbour never sees this region's stub, so it caps
        the far node alone. Clustering it here would draw that junction twice or
        not at all, so a stub is refused unless both its nodes are owned."""
        city, _ = stubville
        graph = json.loads((tmp_path / "out" / "middle" / ROADGRAPH_NAME).read_text())
        style = city.roads.surface
        report = SurfaceReport()
        edges = [_prepare(edge, style, report) for edge in graph["edges"]]
        ends = _ends_by_node_and_level(graph["edges"], edges)
        _assign_trims(ends, edges, style, report)
        assert edges[0].is_stub

        both = _stub_clusters(ends, edges, SurfaceReport(), owned=lambda node: True)
        assert [keys for keys in both if len(keys) >= 2] == [[(0, 0), (1, 0)]]

        refused = SurfaceReport()
        one = _stub_clusters(ends, edges, refused, owned=lambda node: node != 1)
        assert all(len(keys) == 1 for keys in one)
        assert (refused.stub_edges, refused.clusters, refused.cluster_nodes) == (0, 0, 0)

    def test_a_city_without_stubs_is_capped_as_it_always_was(self, testville, tmp_path) -> None:
        """Every other fixture's assertions are the byte-identity check; this
        one just says the counters agree that nothing clustered."""
        report = build_region(testville[0], "middle", out_root=tmp_path / "out")
        assert (report.stub_edges, report.clusters, report.cluster_nodes) == (0, 0, 0)
        assert _manifest(tmp_path)["clusters"] == {
            "stub_edges": 0,
            "count": 0,
            "nodes": 0,
            "corridors": 0,
        }


class TestThroughCorridors:
    """`P3-31`'s second finding: a street attached to a cluster's nodes on the
    skew is drawn straight across it, by a corridor quad between the two arms'
    cross-sections beyond their splay."""

    NOTCH = np.array([[296.0, 309.5], [318.0, 309.5]])

    def test_the_corridor_makes_the_skewed_street_straight(self, splayville, tmp_path) -> None:
        city, _ = splayville
        report = build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        assert report.clusters == 1
        assert report.corridors == 1
        assert report.junctions == 2  # the cluster cap and its corridor
        corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
        assert _covered(self.NOTCH, corners).all()
        # The corridor is the straight street between the two splay vertices:
        # x 292..322 at the 6 m half-width about z = 304.
        rings = [np.asarray(cap["ring"]) for cap in _manifest(tmp_path)["caps"]]
        corridor = next(ring for ring in rings if len(ring) == 4)
        plan = {(round(float(x), 3), round(float(z), 3)) for x, _, z in corridor}
        assert plan == {(292.0, 298.0), (292.0, 310.0), (322.0, 298.0), (322.0, 310.0)}
        assert _manifest(tmp_path)["clusters"]["corridors"] == 1

    def test_a_splay_longer_than_the_cluster_is_not_a_splay(self, splayville, tmp_path) -> None:
        """The mutation: move the west arm's first vertex 40 m out — past the
        two nodes' span plus both half-widths — and the arm has no far
        section, so no corridor and the notch is pavement again."""
        city, _ = splayville
        path = tmp_path / "out" / "middle" / ROADGRAPH_NAME
        graph = json.loads(path.read_text(encoding="utf-8"))
        graph["edges"][1]["polyline"] = [
            [200.0, 0.0, 304.0],
            [260.0, 0.0, 304.0],
            [300.0, 0.0, 300.0],
        ]
        graph["edges"][1]["on_structure"] = [False] * 3
        graph["edges"][1]["structure_bounded"] = [False] * 3
        path.write_text(json.dumps(graph), encoding="utf-8")

        report = build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)

        assert report.clusters == 1
        assert report.corridors == 0
        corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
        assert not _covered(self.NOTCH[1:], corners).any()

    def test_straight_arms_draw_no_corridor(self, stubville, tmp_path) -> None:
        """Two-vertex arms have no vertex beyond the mouth, so nothing to run a
        corridor between; the cluster cap alone is byte for byte what it was."""
        city, _ = stubville
        report = build_region(city, "middle", out_root=tmp_path / "out")
        assert report.corridors == 0
        assert report.junctions == 1
