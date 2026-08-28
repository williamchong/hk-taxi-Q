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

import numpy as np
import pytest

from pipeline.carriageway import MIN_STATIONS, _license, _Segments, _stations
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
