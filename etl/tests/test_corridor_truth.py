"""The probe on `tools/corridor_truth.py` (`Q110`).

Same standard as `test_deck_margin.py`: only the parts whose failure mode is
**silent**. A walk that stopped walking reads nothing and nobody could miss it.

🔴 **What would not announce itself is a clip that lets geometry through.** The
whole claim of this tool is that its reading is exact where the two shipped
instruments are lower bounds, and it is quoted to decide whether `fence.py`
stands a barrier in front of the player. A clipper that drops a triangle, or
that keeps one but reports the extent of the *unclipped* corners, prints a
perfectly plausible table and moves the answer the reassuring way — wider, not
narrower. So the clip is pinned against walls whose exact answer is known by
hand, arithmetic rather than approximation, and the tests fail on the mutations
that matter: a dropped half-space, an extent taken before the clip, and the
across-extent taken over the wrong axis.

⚠️ **`widest_clear` is the other silent one.** `pipeline/clearance.py` and this
both promise the widest single run rather than the unblocked total, because a
car needs one gap it fits through. Summing instead reads *wider* on exactly the
cross-sections this tool exists to judge — a ribbon blocked in the middle is the
shape of every one of them.
"""

from __future__ import annotations

import argparse

import numpy as np
import pytest
from corridor_truth import (
    Walk,
    _at,
    _clip,
    _station_frame,
    blocked_extent,
    deck_rims,
    merged,
    section_argument,
    spacing_argument,
    survey_edge,
    unclamped_ribbon,
    widest_clear,
    windows_argument,
)


def wall(
    s_low: float, s_high: float, t_low: float, t_high: float, y_low: float, y_high: float
) -> list[np.ndarray]:
    """Two triangles spanning a box in `(s, y, t)`, as the clip sees them.

    Arguments are grouped by axis in the order `(s, s, t, t, y, y)`, which is
    NOT the `(s, y, t)` order the corners themselves are built in — read the
    body before adding a call.
    """
    corners = [
        np.array([[s_low, y_low, t_low], [s_high, y_low, t_high], [s_high, y_high, t_high]]),
        np.array([[s_low, y_low, t_low], [s_high, y_high, t_high], [s_low, y_high, t_low]]),
    ]
    return corners


class TestBlockedExtent:
    """The exact across-extent of one triangle inside a slab and a band."""

    def test_a_face_inside_both_bounds_reports_its_own_extent(self) -> None:
        # Wholly within the slab and within the band, so neither clip bites and
        # the answer is the face's own across-extent, 1.0 to 1.5 by hand.
        corners = np.array([[-0.25, 1.0, 1.0], [0.25, 1.0, 1.5], [0.25, 1.5, 1.5]])
        extent = blocked_extent(corners, (-0.25, 0.25), (0.30, 2.00))
        assert extent is not None
        assert extent == pytest.approx((1.0, 1.5))

    def test_the_band_cuts_a_face_that_rises_into_it(self) -> None:
        # A face standing on the deck: its two feet are below `BUMPER_LOW_M`, so
        # only the part inside the band counts. The band edge crosses at
        # t = 1.05 by hand, where a reading that ignored the band reports 1.00.
        corners = np.array([[-0.25, 0.0, 1.0], [0.25, 0.0, 1.5], [0.25, 3.0, 1.5]])
        extent = blocked_extent(corners, (-0.25, 0.25), (0.30, 2.00))
        assert extent is not None
        assert extent == pytest.approx((1.05, 1.5))

    def test_the_slab_cuts_the_extent_down_and_does_not_report_the_whole_face(self) -> None:
        # 🔴 The mutation this catches is an extent taken over the *unclipped*
        # corners: that reads (0.0, 4.0) here, four times the truth, and a
        # blocked interval four times too wide is a corridor read too narrow —
        # the direction that condemns an edge that is fine.
        corners = np.array([[-2.0, 1.0, 0.0], [2.0, 1.0, 4.0], [2.0, 1.5, 4.0]])
        extent = blocked_extent(corners, (-0.25, 0.25), (0.30, 2.00))
        assert extent is not None
        assert extent == pytest.approx((1.75, 2.25))

    def test_geometry_wholly_above_the_band_does_not_block(self) -> None:
        # A soffit six metres up is Hong Kong working as intended (`Q19`).
        corners = np.array([[-1.0, 6.0, 0.0], [1.0, 6.0, 1.0], [1.0, 6.5, 1.0]])
        assert blocked_extent(corners, (-0.25, 0.25), (0.30, 2.00)) is None

    def test_geometry_wholly_below_the_band_does_not_block(self) -> None:
        corners = np.array([[-1.0, -3.0, 0.0], [1.0, -3.0, 1.0], [1.0, 0.2, 1.0]])
        assert blocked_extent(corners, (-0.25, 0.25), (0.30, 2.00)) is None

    def test_geometry_outside_the_slab_does_not_block(self) -> None:
        corners = np.array([[4.0, 0.5, 0.0], [5.0, 0.5, 1.0], [5.0, 1.5, 1.0]])
        assert blocked_extent(corners, (-0.25, 0.25), (0.30, 2.00)) is None

    def test_a_vertical_wall_in_a_zero_window_reports_zero_thickness(self) -> None:
        """🔴 The reading a zero window gives, pinned so the claim stays honest.

        A vertical parapet meets a zero-thickness cross-section in a line, so
        the exact blockage is zero metres wide. That was expected to be the
        reason `--window-m` exists and it is **not**: a zero-width block still
        partitions the run — `TestWidestClear` shows the partition — so the
        corridor is unmoved and `Q110`'s sweep is flat from 0 to 2.0 m. What
        the window actually guards is an obstruction standing *between* two
        stations.
        """
        corners = np.array([[-1.0, 0.5, 1.0], [1.0, 0.5, 1.0], [1.0, 1.5, 1.0]])
        extent = blocked_extent(corners, (0.0, 0.0), (0.30, 2.00))
        assert extent is not None
        assert extent[1] - extent[0] == pytest.approx(0.0)

    def test_the_same_wall_in_a_real_window_blocks_a_real_width(self) -> None:
        """And the same wall, run at an angle to the road, blocks properly."""
        corners = np.array([[-1.0, 0.5, 1.0], [1.0, 0.5, 1.4], [1.0, 1.5, 1.4]])
        extent = blocked_extent(corners, (-0.25, 0.25), (0.30, 2.00))
        assert extent is not None
        assert extent == pytest.approx((1.15, 1.25))


class TestWidestClear:
    """One gap a car fits through, never two halves of one."""

    def test_an_unblocked_ribbon_is_clear_end_to_end(self) -> None:
        assert widest_clear([], -2.8, 2.8)[0] == pytest.approx(5.6)

    def test_a_block_in_the_middle_reports_the_wider_half(self) -> None:
        # 🔴 The mutation: summing the unblocked total reads 5.1 m here, on a
        # cross-section a car cannot cross at all.
        width, centre = widest_clear([(-0.3, 0.2)], -2.8, 2.8)
        assert width == pytest.approx(2.6)
        assert centre == pytest.approx(1.5)

    def test_overlapping_blocks_do_not_double_count(self) -> None:
        width, _ = widest_clear([(-1.0, 0.0), (-0.5, 0.5)], -2.8, 2.8)
        assert width == pytest.approx(2.3)

    def test_a_block_outside_the_ribbon_is_ignored(self) -> None:
        assert widest_clear([(4.0, 5.0)], -2.8, 2.8)[0] == pytest.approx(5.6)

    def test_a_block_straddling_a_rim_is_clipped_to_the_ribbon(self) -> None:
        width, _ = widest_clear([(-4.0, -2.0)], -2.8, 2.8)
        assert width == pytest.approx(4.8)

    def test_a_fully_blocked_ribbon_is_zero(self) -> None:
        assert widest_clear([(-3.0, 3.0)], -2.8, 2.8)[0] == pytest.approx(0.0)


class TestClip:
    """The half-space clip itself, since every extent above rests on it."""

    def test_a_polygon_wholly_inside_is_returned_unchanged(self) -> None:
        polygon = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]
        assert _clip(polygon, 0, -5.0, True) == polygon

    def test_a_polygon_wholly_outside_is_emptied(self) -> None:
        polygon = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]
        assert _clip(polygon, 0, 5.0, True) == []

    def test_a_straddling_polygon_keeps_the_cut_edge_on_the_bound(self) -> None:
        polygon = [(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]
        clipped = _clip(polygon, 0, 0.0, True)
        # One corner outside a half-space cuts a triangle into a quad.
        assert len(clipped) == 4
        assert min(point[0] for point in clipped) == pytest.approx(0.0)
        assert max(point[0] for point in clipped) == pytest.approx(1.0)


class TestStationFrame:
    """The across unit, whose sign no reading of this tool can report."""

    def test_the_across_unit_is_left_of_travel(self) -> None:
        # `overhang.left_of`'s frame is `surface.mitres`', which is the frame
        # `offset_m` is published in. Travelling +x, left is -z in this
        # right-handed, y-up frame; a flip here mirrors every reading and the
        # table still prints.
        along, across, length = _station_frame(
            np.array([0.0, 0.0, 0.0]), np.array([10.0, 0.0, 0.0])
        )
        assert length == pytest.approx(10.0)
        assert along == pytest.approx(np.array([1.0, 0.0]))
        assert across == pytest.approx(np.array([0.0, -1.0]))

    def test_a_zero_length_segment_reports_zero_rather_than_dividing(self) -> None:
        _, _, length = _station_frame(np.zeros(3), np.zeros(3))
        assert length == 0.0


class TestInterpolatedRibbon:
    """The published half-width between two vertices."""

    def test_a_value_is_blended_along_its_segment(self) -> None:
        # 🔴 `overhang.at_vertex` returns 2.198 across this whole segment. On
        # `e208` that is half a metre of ribbon in the wrong place, at the two
        # segments that carry the pinch this tool was written to read.
        assert _at([2.198, 1.709], 0, 0.0) == pytest.approx(2.198)
        assert _at([2.198, 1.709], 0, 0.5) == pytest.approx(1.9535)
        assert _at([2.198, 1.709], 0, 1.0) == pytest.approx(1.709)

    def test_the_last_vertex_holds_rather_than_running_off_the_end(self) -> None:
        assert _at([2.198, 1.709], 1, 0.5) == pytest.approx(1.709)


def test_the_two_triangles_of_a_box_report_one_extent_between_them() -> None:
    """A wall is meshed as quads, so the union is what the caller accumulates."""
    extents = [
        blocked_extent(c, (-0.25, 0.25), (0.30, 2.00)) for c in wall(-1, 1, 1.0, 1.4, 0.0, 3.0)
    ]
    assert all(extent is not None for extent in extents)
    width, _ = widest_clear([e for e in extents if e is not None], -2.8, 2.8)
    # The wall runs t = 1.0 -> 1.4 over s = -1 -> 1, so inside the slab it
    # spans 1.15 to 1.25 and the wider side of the ribbon is the one below it.
    assert width == pytest.approx(1.15 + 2.8)


class TestMerged:
    """Blocked intervals folded, since the cross-section printer reads them."""

    def test_touching_runs_join(self) -> None:
        assert merged([(0.0, 1.0), (1.0, 2.0)]) == [(0.0, 2.0)]

    def test_disjoint_runs_stay_apart_and_are_ordered(self) -> None:
        assert merged([(3.0, 4.0), (0.0, 1.0)]) == [(0.0, 1.0), (3.0, 4.0)]

    def test_a_run_swallowed_by_another_does_not_shorten_it(self) -> None:
        # 🔴 `runs[-1][1] = high` rather than `max(...)` reads 1.0 here, which
        # prints a wall as ending where a sliver inside it does.
        assert merged([(0.0, 5.0), (0.5, 1.0)]) == [(0.0, 5.0)]


class TestDeckRims:
    """`Q107`'s rims, per station."""

    def test_an_edge_with_no_deck_reads_inf_rather_than_zero(self) -> None:
        # 🔴 `surface._clamped_rails`' own rule. A 0.0 default collapses the
        # whole at-grade network to nothing, which is why absence is `inf`.
        left, right = deck_rims({}, 3)
        assert left == [float("inf")] * 3
        assert right == [float("inf")] * 3

    def test_the_pairs_are_split_in_order(self) -> None:
        left, right = deck_rims({"deck_rim_m": [[0.1, 8.0], [0.3, 7.9]]}, 2)
        assert left == [0.1, 0.3]
        assert right == [8.0, 7.9]


class TestUnclampedRibbon:
    """The pre-`Q107` frame, for the counterfactual."""

    def test_it_is_the_graph_width_and_offset_held_constant(self) -> None:
        halves, shifts = unclamped_ribbon({"width_m": 5.6, "offset_m": -0.25}, 3)
        assert halves == [2.8, 2.8, 2.8]
        assert shifts == [-0.25, -0.25, -0.25]

    def test_an_edge_with_no_offset_is_centred(self) -> None:
        _, shifts = unclamped_ribbon({"width_m": 6.4}, 2)
        assert shifts == [0.0, 0.0]


class TestSectionArgument:
    """`EDGE@METRES`, so a station can be named on the command line."""

    def test_a_pair_parses(self) -> None:
        assert section_argument("e208@180.6") == [(208, 180.6)]

    def test_several_parse_in_order(self) -> None:
        assert section_argument("e208@180.6, e306@186.7") == [(208, 180.6), (306, 186.7)]

    def test_a_missing_distance_is_refused(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError):
            section_argument("e208")

    def test_a_distance_that_is_not_a_number_is_refused(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError):
            section_argument("e208@middle")


class TestArgumentTypes:
    """Parsed by argparse, so a bad value is a usage error and not a traceback."""

    def test_windows_parse_in_order(self) -> None:
        assert windows_argument("0,0.5,2") == [0.0, 0.5, 2.0]

    def test_an_empty_window_list_is_refused(self) -> None:
        # 🔴 Hand-parsed after `parse_args`, this yielded an empty sweep that
        # printed nothing and then raised `IndexError` two functions later.
        with pytest.raises(argparse.ArgumentTypeError):
            windows_argument(",")

    def test_a_negative_window_is_refused(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError):
            windows_argument("0.5,-1")

    def test_a_zero_pitch_is_refused_because_it_divides(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError):
            spacing_argument("0")

    def test_a_negative_pitch_is_refused(self) -> None:
        # `max(1, ceil(L / spacing))` swallows it into one station a segment,
        # which is a silent resolution change rather than an error.
        with pytest.raises(argparse.ArgumentTypeError):
            spacing_argument("-0.25")


def empty_walk(window_m: float = 0.5, spacing_m: float = 1.0) -> Walk:
    """A walk over no geometry, so only the traversal is under test."""
    triangles = np.zeros((0, 3, 3))
    return Walk(triangles, np.zeros((0, 2)), np.zeros((0, 2)), (0.30, 2.00), window_m, spacing_m)


def straight_edge(length_m: float = 10.0, vertices: int = 3) -> dict[str, object]:
    """An edge running down +x in 3-D game coordinates, `vertices` long."""
    step = length_m / (vertices - 1)
    return {
        "id": 1,
        "polyline": [[step * index, 0.0, 0.0] for index in range(vertices)],
        "width_m": 5.6,
        "offset_m": 0.0,
    }


class TestSurveyEdge:
    """The traversal, whose three failure modes all print a plausible table."""

    def test_the_along_distance_is_cumulative_over_the_whole_edge(self) -> None:
        """🔴 The defect this replaced read `2.2 m along` for a station 190 m down a ramp.

        A per-segment distance prints a table that looks entirely right and
        names a place nobody can go and look at — and it is the one number a
        reader takes out of this tool into the world.
        """
        readings = survey_edge(straight_edge(10.0, 3), empty_walk(), [2.8] * 3, [0.0] * 3)
        assert readings[0].along_m == pytest.approx(0.0)
        assert readings[-1].along_m == pytest.approx(10.0)
        distances = [station.along_m for station in readings]
        assert distances == sorted(distances)

    def test_the_shared_vertex_is_walked_once(self) -> None:
        # `overhang.walk_width`'s guard restated: run per segment without it,
        # each interior vertex is emitted twice.
        readings = survey_edge(straight_edge(10.0, 3), empty_walk(), [2.8] * 3, [0.0] * 3)
        distances = [round(station.along_m, 6) for station in readings]
        assert len(distances) == len(set(distances))

    def test_an_unobstructed_ribbon_is_clear_end_to_end(self) -> None:
        readings = survey_edge(straight_edge(10.0, 2), empty_walk(), [2.8] * 2, [0.0] * 2)
        assert readings
        assert all(station.clear_m == pytest.approx(5.6) for station in readings)

    def test_a_published_offset_moves_the_ribbon_and_not_its_width(self) -> None:
        readings = survey_edge(straight_edge(10.0, 2), empty_walk(), [2.8] * 2, [-1.5] * 2)
        assert readings[0].near == pytest.approx(-4.3)
        assert readings[0].far == pytest.approx(1.3)
        assert readings[0].ribbon_m == pytest.approx(5.6)

    def test_an_edge_published_before_the_offset_existed_does_not_crash(self) -> None:
        # 🔴 `overhang.drawn_offsets` returns `[]` for a pre-schema-7 bundle, and
        # `_at` without its empty guard raises `IndexError` on exactly those.
        readings = survey_edge(straight_edge(10.0, 2), empty_walk(), [2.8] * 2, [])
        assert readings[0].near == pytest.approx(-2.8)

    def test_a_zero_length_segment_is_skipped_rather_than_dividing(self) -> None:
        edge = {"id": 1, "polyline": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [10.0, 0.0, 0.0]]}
        readings = survey_edge(edge, empty_walk(), [2.8] * 3, [0.0] * 3)
        assert readings
        assert readings[-1].along_m == pytest.approx(10.0)
