"""The pipeline's own carriageway survey (`pipeline/carriageway.py`, `Q95`).

⚠️ **This is a second implementation of a survey `tools/carriageway_margin.py`
also performs, and these tests do not exist to prove the two identical.** They
are deliberately independent — `CLAUDE.md` records that the tool "shares no code
with what it grades" — so what is pinned here is that this one is *correct*, and
the agreement between them is measured on the region instead, where it currently
runs to a 5 mm median over 259 shared edges.

The failures worth pinning are the quiet ones:

- **The ray takes the wrong hit.** Candidates come out of a grid bucket in
  insertion order, so returning the first crossing found makes the measured
  width depend on which sheet was read first. It has to be the nearest.
- **A degenerate segment.** A repeated vertex has no direction, and dividing by
  its vanishing determinant yields a silent zero-distance "hit" rather than a
  miss — a kerb apparently on top of the centreline.
- **A span that crossed a median read as a width.** This is the one that draws
  both halves of Hennessy Road on each half of Hennessy Road, and it renders as
  an ordinary, slightly generous street.
"""

from __future__ import annotations

import math
from typing import ClassVar

import numpy as np
import pytest

from pipeline.carriageway import (
    LANES_FLOOR,
    MIN_STATIONS,
    _lane_bracket,
    _lanes,
    _license,
    _Segments,
    _stations,
    _union_boundary,
)
from pipeline.config import BOTH, FORWARD, WidthBounds


def _bounds(**overrides: object) -> WidthBounds:
    """TD's transcribed figures, as `hong_kong.yaml` carries them."""
    defaults = {
        "max_m": 16.5,
        "min_m": 7.3,
        "hard_min_m": 3.0,
        "lane_m": (3.0, 3.65),
        "dual_max_m": 14.6,
        "dual_min_m": 6.75,
        "median_max_m": 5.5,
        "pair_bearing_tolerance_deg": 30.0,
    }
    return WidthBounds(**{**defaults, **overrides})  # type: ignore[arg-type]


def _kerbs(*lines: list[tuple[float, float]]) -> _Segments:
    starts, ends = [], []
    for line in lines:
        points = np.asarray(line, dtype=np.float64)
        starts.append(points[:-1])
        ends.append(points[1:])
    return _Segments.build(np.vstack(starts), np.vstack(ends))


class _Edge:
    """The three fields `_license` reads off a graph edge."""

    def __init__(self, direction: str) -> None:
        self.direction = direction


class TestRay:
    def test_a_ray_measures_the_distance_to_a_crossing_kerb(self) -> None:
        kerbs = _kerbs([(-50.0, 4.0), (50.0, 4.0)])

        hit = kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert hit == pytest.approx(4.0)

    def test_it_takes_the_NEAREST_kerb_and_not_the_first_one_indexed(self) -> None:
        """🔴 The quiet one. Both kerbs land in the same 20 m bucket and the
        bucket holds them in insertion order, so a reader that stops at its
        first crossing measures 9 m of carriageway where there are 4 — and the
        answer would depend on which sheet was read first."""
        far_first = _kerbs([(-50.0, 9.0), (50.0, 9.0)], [(-50.0, 4.0), (50.0, 4.0)])

        hit = far_first.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert hit == pytest.approx(4.0)

    def test_a_kerb_past_the_cap_is_not_found(self) -> None:
        """An uncapped perpendicular finds *something* eventually and calls it a
        kerb. Beyond the cap the station is unmeasurable, which is a different
        answer from a narrow road."""
        kerbs = _kerbs([(-50.0, 40.0), (50.0, 40.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_kerb_behind_the_station_is_not_a_hit_ahead_of_it(self) -> None:
        """The two rays are cast separately and summed, so a backward hit
        counted forwards would double one side and halve the other."""
        kerbs = _kerbs([(-50.0, -4.0), (50.0, -4.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None
        assert kerbs.first_hit(np.zeros(2), np.array([0.0, -1.0]), 15.0) == pytest.approx(4.0)

    def test_a_degenerate_segment_is_a_miss_rather_than_a_zero(self) -> None:
        """A repeated vertex has no direction. Its determinant vanishes rather
        than the ray missing, so it must be excluded by the crossing test before
        any division — otherwise it reads as a kerb on the centreline."""
        kerbs = _kerbs([(1.0, 1.0), (1.0, 1.0)], [(-50.0, 4.0), (50.0, 4.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) == pytest.approx(4.0)

    def test_a_kerb_the_ray_runs_along_is_not_a_crossing(self) -> None:
        """Collinear touching is not a crossing — `geometry.edges_cross` refuses
        it for the same reason, and a ray parallel to a kerb has not reached the
        far side of anything."""
        kerbs = _kerbs([(0.0, 2.0), (0.0, 12.0)])

        assert kerbs.first_hit(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None


class TestStations:
    def test_stations_are_evenly_spaced_along_the_line(self) -> None:
        out = _stations(np.array([[0.0, 0.0], [20.0, 0.0]]), 4.0)

        assert [round(float(p[0]), 3) for p, _ in out] == [2.0, 6.0, 10.0, 14.0, 18.0]

    def test_the_normal_is_perpendicular_to_the_segment_it_sits_on(self) -> None:
        (_, normal), *_ = _stations(np.array([[0.0, 0.0], [20.0, 0.0]]), 4.0)

        assert normal == pytest.approx([0.0, 1.0])

    def test_a_line_shorter_than_one_step_still_yields_a_station(self) -> None:
        """The walk starts half a step in, so a 3 m stub is measured once rather
        than dropped silently."""
        assert len(_stations(np.array([[0.0, 0.0], [3.0, 0.0]]), 4.0)) == 1

    def test_a_zero_length_line_yields_nothing_rather_than_dividing(self) -> None:
        assert _stations(np.array([[5.0, 5.0], [5.0, 5.0]]), 4.0) == []


class TestLicence:
    """Which measurements may become a `width_m`, and which may not."""

    def test_a_two_way_edge_is_its_span(self) -> None:
        """There is no opposed half to have crossed into, so the span is the
        carriageway with nothing to classify."""
        width, basis = _license(_Edge(BOTH), 9.0, 8.0, _bounds())

        assert (width, basis) == (9.0, "two_way_span")

    def test_a_one_way_span_with_no_room_beside_it_is_that_edges_width(self) -> None:
        """`Q95`'s finding: 96 of 110 mutual pairs refuse their own split because
        the ray stopped at the far kerb and never crossed. A 7 m span over a 7 m
        carriageway leaves 0 m — nowhere for an opposed carriageway to be."""
        width, basis = _license(_Edge(FORWARD), 7.0, 7.0, _bounds())

        assert (width, basis) == (7.0, "one_way_uncrossed")

    def test_a_one_way_span_with_a_carriageway_beside_it_licenses_nothing(self) -> None:
        """🔴 The one that draws both halves of Hennessy Road on each half of
        it. 16 m of span over a 6 m carriageway leaves 10 m — room for an opposed
        one — so the number is a kerb-to-kerb span and not this edge's width."""
        assert _license(_Edge(FORWARD), 16.0, 6.0, _bounds()) == (None, "")

    def test_the_undecided_band_licenses_nothing_either(self) -> None:
        """Room for a lane but not a carriageway. `Q95` records TONNOCHY ROAD
        `e142` here — a 16.7 m span over an 11.78 m half — and a rule with only
        one threshold has to call that either a width or a span."""
        bounds = _bounds()
        beyond = 12.0 - 7.0
        assert bounds.hard_min_m < beyond < bounds.dual_min_m
        assert _license(_Edge(FORWARD), 12.0, 7.0, bounds) == (None, "")

    def test_a_span_past_the_manuals_ceiling_is_refused_before_anything_else(self) -> None:
        """Above a four-lane carriageway plus a parking strip the ray has crossed
        a median, a tram reserve or a junction mouth, and `beyond` cannot tell
        which — so the refusal comes first and applies to two-way edges too."""
        assert _license(_Edge(FORWARD), 20.0, 20.0, _bounds()) == (None, "")
        assert _license(_Edge(BOTH), 20.0, 20.0, _bounds()) == (None, "")

    def test_a_span_under_one_through_lane_is_not_a_carriageway(self) -> None:
        """It landed on a hatched island or a bay line rather than the far kerb."""
        assert _license(_Edge(BOTH), 2.0, 2.0, _bounds()) == (None, "")

    def test_the_bounds_come_from_the_city_and_move_the_answer(self) -> None:
        """⚠️ Hard rule 3: every figure here is the city file's, and none is a
        constant in this module. Driving them is how that is shown rather than
        asserted — the second city has its own design manual."""
        assert _license(_Edge(FORWARD), 12.0, 7.0, _bounds(dual_min_m=4.0)) == (None, "")
        assert _license(_Edge(FORWARD), 12.0, 7.0, _bounds(hard_min_m=6.0))[1] == (
            "one_way_uncrossed"
        )


class TestStationFloor:
    def test_the_minimum_station_count_is_what_stops_a_stub_publishing(self) -> None:
        """Documented rather than asserted elsewhere: three stations is what
        keeps a 6 m stub from carrying a width off one lucky ray."""
        assert MIN_STATIONS == 3


class TestLaneBracket:
    """`Q94`: how many through lanes a measured carriageway may be read as.

    🔴 **The instrument must not agree with the value under test.** The divisor
    is TPDM 4.3.9.8's published range and never `roads.lane_width_m`, so what
    these pin first is that the answer is a *bracket* and that its ambiguity
    survives rather than being resolved by fiat.
    """

    # Table 3.4.2.1's own rows: (carriageway width, the lane count TD gives it).
    # ⚠️ **The truth side of the only validation this rule can have.** There is
    # no published per-edge lane count anywhere to check against, so the manual
    # the divisor came from is what is left — and it costs nothing to check,
    # which is the six shared-endpoint pairs' argument at a second layer.
    TABLE_3_4_2_1: ClassVar[list[tuple[float, int]]] = [
        (7.3, 2),
        (10.3, 2),
        (13.5, 4),
        (6.75, 2),
        (11.0, 3),
        (10.0, 3),
        (14.6, 4),
    ]

    def test_the_bracket_contains_TDs_own_count_on_every_row_of_its_own_table(self) -> None:
        for width_m, published in self.TABLE_3_4_2_1:
            low, high = _lane_bracket(width_m, _bounds(), two_way=False)
            assert low <= published <= high, (
                f"{width_m} m brackets ({low}, {high}), TD says {published}"
            )

    def test_and_a_tighter_reading_would_exclude_it_which_is_why_this_one_is_permissive(
        self,
    ) -> None:
        """🔴 The argument for the loose bracket, as a measurement rather than a preference.

        Requiring the width to partition exactly into legal lanes —
        `3.0 <= w / n <= 3.65` — is the obvious sharpening and it is wrong: it
        calls TD's 10.3 m *two-lane* single carriageway three lanes, and finds
        no legal reading at all for the 11 m dual three-lane. A rule that
        contradicts the document it is derived from is not a sharper rule.
        """
        excluded = [
            (width_m, published)
            for width_m, published in self.TABLE_3_4_2_1
            if not math.ceil(width_m / 3.65) <= published <= int(width_m // 3.0)
        ]
        assert [width_m for width_m, _ in excluded] == [10.3, 11.0]

    def test_a_resolved_bracket_publishes_its_count(self) -> None:
        assert _lanes(_lane_bracket(7.3, _bounds(), two_way=False)) == (2, "measured")

    def test_a_width_TDs_range_does_not_resolve_publishes_nothing(self) -> None:
        """The middle state, and it is most of the region — `_license`'s own shape."""
        assert _lane_bracket(7.29, _bounds(), two_way=False) == (1, 2)
        assert _lanes((1, 2)) == (None, "")

    def test_one_lane_is_floored_because_the_ribbon_over_it_is_not(self) -> None:
        """A 5 m one-way street holds one lane; what is drawn on it is 10.24 m wide."""
        assert _lane_bracket(3.65, _bounds(), two_way=False) == (1, 1)
        assert _lanes((1, 1)) == (LANES_FLOOR, "floored")

    def test_no_licensed_width_can_bracket_to_no_lanes_at_all(self) -> None:
        """🔴 The invariant `config.py` enforces, pinned where it is relied upon.

        `_lanes` floors anything under `LANES_FLOOR`, so an unambiguous bracket
        of **zero** would publish two lanes for a width that measured none. It
        is unreachable because a licensed width is at least `hard_min_m` and
        `config.py` refuses a `lane_m` floor above that — but the refusal lives
        in another module, and this is the line that would break if it moved.
        """
        bounds = _bounds()
        assert bounds.lane_m[0] <= bounds.hard_min_m
        for step in range(300, 1651):
            low, high = _lane_bracket(step / 100.0, bounds, two_way=False)
            assert high >= 1
            assert not (low == high == 0)

    def test_3_4_2_7_removes_the_odd_counts_from_an_AMBIGUOUS_two_way_bracket(self) -> None:
        """A two-way single carriageway may not be split into three lanes."""
        assert _lane_bracket(11.5, _bounds(), two_way=False) == (3, 3)
        assert _lane_bracket(12.5, _bounds(), two_way=True) == (4, 4)

    def test_but_an_unambiguously_odd_one_stands_and_is_reported_instead(self) -> None:
        """⚠️ Narrowing that would be correcting a reading into agreement (`Q54`).

        Three lanes on a two-way edge is a finding about the measurement or the
        `direction` field, and `measure` records it in `lanes_odd_two_way`. The
        bracket is not edited to make the finding go away.
        """
        assert _lane_bracket(11.5, _bounds(), two_way=True) == (3, 3)

    def test_the_divisor_is_the_manuals_and_never_the_authored_lane_width(self) -> None:
        """🔴 `Q72`'s tautology, one dimension over.

        `roads.lane_width_m` is 3.2 m and is the constant this whole question is
        about. Dividing by it makes the instrument agree with the graph by
        construction — and it gives a different answer, which is what says the
        two are not interchangeable.
        """
        assert _lane_bracket(14.67, _bounds(), two_way=False) == (4, 4)
        assert int(14.67 // 3.2) == 4
        assert _lane_bracket(10.3, _bounds(), two_way=False) == (2, 3)
        assert int(10.3 // 3.2) == 3


class TestUnionBoundary:
    """`Q94`: an area publisher's outline, with the seams between its parts gone.

    🔴 **The failure this prevents is a plausible number, not an error.** HyD
    tiles Wan Chai's carriageway into 552 polygons; a ray that stops at the
    boundary between two of them reports a width short by however far the
    nearest maintenance division happens to lie.
    """

    @staticmethod
    def _square(x: float, y: float, size: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        """One closed square as (starts, ends), wound counter-clockwise."""
        ring = np.array(
            [[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]], dtype=float
        )
        return ring[:-1], ring[1:]

    def test_a_lone_polygon_keeps_every_edge(self) -> None:
        starts, ends = self._square(0.0, 0.0)
        kept_starts, kept_ends = _union_boundary([starts], [ends])
        assert len(kept_starts[0]) == 4
        assert len(kept_ends[0]) == 4

    def test_the_seam_between_two_abutting_polygons_is_dropped(self) -> None:
        """Two unit squares side by side: 8 edges drawn, 6 on the outline."""
        left, right = self._square(0.0, 0.0), self._square(1.0, 0.0)
        kept_starts, kept_ends = _union_boundary([left[0], right[0]], [left[1], right[1]])
        assert len(kept_starts[0]) == 6
        # The shared edge runs x = 1 from y = 0 to y = 1, and neither copy survives.
        survivors = np.hstack([kept_starts[0], kept_ends[0]])
        on_seam = np.all(np.isclose(survivors[:, [0, 2]], 1.0), axis=1)
        assert not on_seam.any()

    def test_a_seam_drawn_in_OPPOSITE_directions_still_matches_itself(self) -> None:
        """🔴 The usual case, and the reason the key is canonically ordered.

        Two polygons wound the same way traverse their shared edge in opposite
        directions, so a key built from `(start, end)` as drawn never matches
        and every seam survives — leaving the seams in place while every
        counter reads correctly.
        """
        starts = [np.array([[1.0, 0.0]]), np.array([[1.0, 1.0]])]
        ends = [np.array([[1.0, 1.0]]), np.array([[1.0, 0.0]])]
        kept_starts, _ = _union_boundary(starts, ends)
        assert len(kept_starts[0]) == 0

    def test_a_vertex_a_hair_apart_is_NOT_treated_as_shared(self) -> None:
        """The assumption this rests on is the publisher's, so it is pinned.

        Abutting polygons must share vertices *exactly* for a seam to cancel.
        Where they do not, the seam survives and a ray stops on it — which is
        why the agreement with point-in-union walking is measured rather than
        assumed.
        """
        starts = [np.array([[1.0, 0.0]]), np.array([[1.0, 1.0]])]
        ends = [np.array([[1.0, 1.0]]), np.array([[1.004, 0.0]])]
        kept_starts, _ = _union_boundary(starts, ends)
        assert len(kept_starts[0]) == 2

    def test_nothing_drawn_is_nothing_kept(self) -> None:
        assert _union_boundary([], []) == ([], [])
