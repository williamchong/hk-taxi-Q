"""The `P3-10` ground probe (`tools/ground_clearance.py`).

Same standard as `test_deck_error.py` and `test_overhang.py`: only the parts
whose failure mode is **silent**. The headline shares check themselves against
the recorded table — 0.363% of sampled points and 3.289% of area at
`ground_sink_m: 0.20` — and a sink that stopped being applied reads 47%, which
nobody could miss. What would not announce itself is the arithmetic underneath.

Three rules carry this tool and all are tested here:

- **The two populations are counted differently on purpose.** Area for the
  width sweep, count for the sampled points. Getting that backwards produces a
  plausible table off by the width of whichever streets happen to be steep.
- **A cell that could not be measured must stay in the denominator.** This is
  `deck_error`'s fourth defect, the one that read "acceptance met, exit 0" while
  a third of the carriageway was broken, and the only reason it is catchable
  here is that `Survey` counts the misses rather than skipping them.
- **The per-edge split is inside-authored against in-the-rim, and it decides
  which fix is even a candidate.** A defect confined to the rim is the 1.6x
  widening (`Q19`); one reaching the authored carriageway is not, and no
  narrowing clears it. Swap the two and the table still looks plausible while
  pointing at the wrong repair — which is the whole use anybody has for it.

⚠️ What has **no unit test and would most want one**: the rule that a sampled
point is the first station of each segment. It lives inside `survey`, which
wants a whole shipped bundle, and splitting it out would move it away from the
loop that has the polyline in hand. `test_the_first_station_of_a_segment_is_its_vertex`
below pins the property of `walk_width` that the rule rests on, which is the
half that could change underneath it.
"""

from __future__ import annotations

import numpy as np
import pytest
from ground_clearance import Survey
from overhang import walk_width


class TestSurveyShares:
    def _survey(self, cells: list[tuple[float, float]], sampled: list[float]) -> Survey:
        found = Survey()
        found.begin(1, "TEST ROAD", 6.4)
        for proud_m, area_m2 in cells:
            found.add(1, proud_m, area_m2, offset_m=0.0)
        for proud_m in sampled:
            found.add_sampled(proud_m)
        return found

    def test_the_area_share_weights_wide_streets_over_narrow_ones(self) -> None:
        """One cell of a six-lane arterial is more road than one cell of an
        alley, and the player is on the arterial. Counting cells would say the
        two contribute equally."""
        found = self._survey([(+0.3, 90.0), (-0.3, 10.0)], [])
        assert found.area_share_above(0.0) == pytest.approx(0.9)

    def test_the_sampled_share_does_not_weight_by_width(self) -> None:
        """The mirror of the rule above, and it has to go the other way. A
        sampled point is one question asked of the terrain, not a piece of
        surface — weighting it by the road it happens to sit on would measure
        the streets rather than the sampling."""
        found = self._survey([], [+0.3, -0.3, -0.3, -0.3])
        assert found.sampled_share_above(0.0) == pytest.approx(0.25)

    def test_the_threshold_is_exclusive_so_a_flush_surface_is_not_proud(self) -> None:
        """Ground exactly level with the road is the boundary case, and it is
        not standing in the carriageway."""
        found = self._survey([(0.0, 1.0)], [0.0])
        assert found.area_share_above(0.0) == 0.0
        assert found.sampled_share_above(0.0) == 0.0

    def test_nothing_measured_is_zero_rather_than_a_division(self) -> None:
        found = Survey()
        assert found.area_share_above(0.0) == 0.0
        assert found.sampled_share_above(0.0) == 0.0
        assert found.coverage == 0.0
        assert found.sampled_coverage == 0.0


class TestSurveyCoverage:
    def test_a_cell_that_could_not_be_measured_stays_in_the_denominator(self) -> None:
        """`deck_error`'s fourth defect, refused here.

        Its coverage was computed over the stations that survived, so breaking a
        third of the carriageway made the broken third stop being counted and
        every ratio improved. Coverage has to be measured against what was
        *asked*, or the denominator is chosen by the defect.
        """
        found = Survey()
        found.asked = 10
        found.no_road = 3
        # `no_ground` is derived from the two window rejections now, so the miss
        # is set through one of them rather than assigned.
        found.below_window = 5
        found.begin(1, "TEST ROAD", 6.4)
        found.add(1, -0.2, 1.0, offset_m=0.0)
        found.add(1, -0.2, 1.0, offset_m=0.0)

        assert found.measured == 2
        assert found.coverage == pytest.approx(0.2)

    def test_a_sampled_point_that_could_not_be_measured_stays_in_its_denominator(self) -> None:
        """The same rule as above, applied to the population that carries the
        gate on the sink — which is where a shrinking denominator would do the
        most damage, because a build that stopped shipping ground under half the
        region would drop those points and *improve* the share they gate."""
        found = Survey()
        found.add_sampled(+0.3)
        found.add_sampled(None)
        found.add_sampled(-0.3)
        found.add_sampled(None)

        assert found.sampled_asked == 4
        assert found.sampled_coverage == pytest.approx(0.5)
        # Over what was measured, not over what was asked: the missing points
        # are not evidence either way, and the coverage gate is what notices
        # there are too many of them.
        assert found.sampled_share_above(0.0) == pytest.approx(0.5)

    def test_the_worst_cell_per_edge_is_the_highest_not_the_last(self) -> None:
        """It names where to go and look, so a later, milder cell on the same
        edge must not overwrite the one worth looking at."""
        found = Survey()
        found.begin(7, "TEST ROAD", 6.4)
        for proud_m in (+1.4, -0.2, +0.3):
            found.add(7, proud_m, 1.0, offset_m=0.0)
        assert found.edges[7].worst_m == pytest.approx(1.4)


class TestSampledPoints:
    def test_the_first_station_of_a_segment_is_its_vertex(self) -> None:
        """What `survey` identifies a sampled point by.

        `roads.py` asks the terrain for a height at the polyline's own vertices;
        everywhere else on the ribbon is interpolated from those, along the road
        or across it. So the first station of each segment is the only cell that
        grades the sink rather than the road's shape — and that identification is
        only sound while `walk_width` keeps starting each segment at its vertex.
        """
        polyline = np.array([[0.0, 5.0, 0.0], [30.0, 7.0, 0.0], [60.0, 6.0, 0.0]])

        firsts = {}
        for vertex, station in walk_width(polyline, 2.0):
            firsts.setdefault(vertex, station)

        assert set(firsts) == {0, 1}
        for vertex, station in firsts.items():
            assert station == pytest.approx(polyline[vertex])


class TestPerEdgeSplit:
    """`EdgeCells`, which exists because the region share cannot see a fix.

    Correcting the region's most cross-sloped edge moves its own proud share
    12.2% -> 3.5% and the region headline by 0.06pp, so a grader reporting only
    the second number scores that fix as noise.

    ⚠️ **These hand `add` an OFFSET, never a decided `inside` flag**, because the
    classification is the thing worth testing. Handed the flag ready-made — as
    the first draft of these tests did — the assertion below calls itself
    load-bearing while testing nothing but arithmetic, and the swap it warns
    about happens in a caller no unit test reaches.
    """

    def _edge(self, authored_width_m: float = 6.4) -> Survey:
        found = Survey()
        found.begin(3, "TEST ROAD", authored_width_m)
        return found

    def test_the_authored_width_decides_which_bucket_a_cell_lands_in(self) -> None:
        """`abs(offset) <= width_m / 2`, the convention `carriageway_occupancy`
        reaches independently. A 6.4 m carriageway drawn at 1.6x is 10.24 m, so a
        cell 4 m out is on the ribbon and off the authored road."""
        found = self._edge()
        found.add(3, +0.5, 1.0, offset_m=+4.0)
        found.add(3, +0.5, 1.0, offset_m=-4.0)
        found.add(3, -0.5, 1.0, offset_m=+1.0)
        found.add(3, -0.5, 1.0, offset_m=-1.0)

        edge = found.edges[3]
        assert edge.over_share == pytest.approx(0.5)
        assert edge.rim_over_share == pytest.approx(1.0)
        # 🔴 The load-bearing assertion: a rim-only defect must read **zero**
        # inside the authored width. `e153 KAI CHIU ROAD` is the shipped
        # instance — 0.0% authored against 27.1% rim. Swap the two buckets and
        # this fails, which the flag-passing version could not.
        assert edge.inside_over_share == pytest.approx(0.0)

    def test_a_cell_exactly_on_the_authored_kerb_is_inside_it(self) -> None:
        """Inclusive at the boundary, so the two buckets partition the ribbon and
        an edge's area is never lost between them."""
        found = self._edge()
        found.add(3, -0.1, 1.0, offset_m=+3.2)
        assert found.edges[3].inside_m2 == pytest.approx(1.0)
        assert found.edges[3].rim_m2 == pytest.approx(0.0)

    def test_the_buckets_partition_the_ribbon(self) -> None:
        """`area_m2` and `over_m2` are derived from the two buckets rather than
        counted alongside them, so a total cannot disagree with its parts."""
        found = self._edge()
        found.add(3, +0.9, 2.0, offset_m=+1.0)
        found.add(3, -0.9, 3.0, offset_m=+5.0)
        edge = found.edges[3]
        assert edge.area_m2 == pytest.approx(edge.inside_m2 + edge.rim_m2)
        assert edge.over_m2 == pytest.approx(edge.inside_over_m2 + edge.rim_over_m2)
        assert edge.area_m2 == pytest.approx(5.0)

    def test_a_cell_exactly_at_suspension_travel_is_not_over_it(self) -> None:
        """Exclusive, as `area_share_above` is, and for the same reason: the bar
        is `handling.tres`'s travel, and a wheel that exactly reaches it has not
        been thrown."""
        found = self._edge()
        found.add(3, 0.18, 1.0, offset_m=0.0)
        assert found.edges[3].over_share == pytest.approx(0.0)

    def test_the_bar_is_the_cars_travel_and_not_the_regions_accept_threshold(self) -> None:
        """The region gates ask whether the ground is above the road at all
        (`--accept-proud-m`, 0.0 by default). This asks whether it would throw
        the car. A cell 0.1 m proud is in the first population and not this
        one — reading them as one number is what the tool's own report warns
        about two populations for."""
        found = self._edge()
        found.add(3, +0.10, 1.0, offset_m=0.0)
        assert found.area_share_above(0.0) == pytest.approx(1.0)
        assert found.edges[3].over_share == pytest.approx(0.0)

    def test_an_edge_records_area_even_where_nothing_stands_proud(self) -> None:
        """The denominator rule again, one level down: an edge whose ribbon was
        measured and found clean has to carry its area, or the share of a later
        build's single bad cell is divided by that cell alone."""
        found = self._edge()
        found.add(3, -0.4, 7.0, offset_m=0.0)
        assert found.edges[3].area_m2 == pytest.approx(7.0)
        assert found.edges[3].over_share == pytest.approx(0.0)


class TestWindowRejections:
    """The two ways a cell can have no attributable ground, which used to be one
    counter — `deck_error`'s fourth defect inverted, with the region's deepest
    burials leaving the numerator instead of the denominator shrinking."""

    def test_no_ground_is_the_two_rejections_summed(self) -> None:
        found = Survey()
        found.below_window = 2276
        found.above_window_m.extend([3.07, 5.00, 7.65])

        assert found.above_window == 3
        assert found.no_ground == 2279
