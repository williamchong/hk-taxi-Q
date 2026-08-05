"""The `P3-10` ground probe (`tools/ground_clearance.py`).

Same standard as `test_deck_error.py` and `test_overhang.py`: only the parts
whose failure mode is **silent**. The headline shares check themselves against
the recorded table — 0.363% of sampled points and 3.289% of area at
`ground_sink_m: 0.20` — and a sink that stopped being applied reads 47%, which
nobody could miss. What would not announce itself is the arithmetic underneath.

Two rules carry this tool and both are tested here:

- **The two populations are counted differently on purpose.** Area for the
  width sweep, count for the sampled points. Getting that backwards produces a
  plausible table off by the width of whichever streets happen to be steep.
- **A cell that could not be measured must stay in the denominator.** This is
  `deck_error`'s fourth defect, the one that read "acceptance met, exit 0" while
  a third of the carriageway was broken, and the only reason it is catchable
  here is that `Survey` counts the misses rather than skipping them.

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
        for proud_m, area_m2 in cells:
            found.add(1, proud_m, area_m2)
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
        found.no_ground = 5
        found.add(1, -0.2, 1.0)
        found.add(1, -0.2, 1.0)

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
        for proud_m in (+1.4, -0.2, +0.3):
            found.add(7, proud_m, 1.0)
        assert found.worst[7] == pytest.approx(1.4)


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
