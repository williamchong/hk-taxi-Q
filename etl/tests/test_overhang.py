"""The `Q22`/`Q23` probe (`tools/overhang.py`).

Same standard as `test_deck_error.py`: only the parts whose failure mode is
**silent**. The headline shares check themselves against the recorded 10.2% and
1,070 m, but the cell arithmetic underneath them would produce a plausible table
while measuring the wrong thing.

⚠️ One rule has **no test here and needs one most**: `Q23` counts a station as
on structure from its centreline only. The first version asked whether *any*
cell across the ribbon had structure under it, read 1,490 m against a recorded
1,070 m, and — worse than inaccurate — made the measurement depend on the drawn
width, so narrowing the road shrank the number that measures whether narrowing
worked. It is untested because the rule lives inside `survey`, which wants a
whole shipped bundle. Splitting it out for a unit was considered and would move
the rule away from the loop that has the cell results in hand, which is where a
reader has to see it. The comment at that line carries the reasoning instead.
"""

from __future__ import annotations

import numpy as np
import pytest
from overhang import Tally, _cross_section, _half_width_at, _left_of, _walk


class TestCrossSection:
    """Cells across the ribbon, and the area each stands for.

    Area rather than a count, because a ribbon whose width varies along its
    length is exactly what `Q23` created: counting cells would weight a 3.2 m
    ramp and a 5.12 m arterial as equals and report a share of nothing in
    particular.
    """

    def _cells(self, half: float, across: float = 0.5):
        return _cross_section(np.zeros(2), np.array([0.0, 1.0]), half, across)

    def test_the_cells_span_the_full_drawn_width(self) -> None:
        cells = self._cells(5.0)
        assert sum(span for _, _, span in cells) == pytest.approx(10.0)

    def test_they_stay_inside_the_carriageway(self) -> None:
        """A cell centre outside the ribbon would ask whether a piece of road
        that is not drawn is supported, and count the answer."""
        for _, offset, _ in self._cells(5.0):
            assert abs(offset) < 5.0

    def test_a_width_that_is_not_a_multiple_of_the_cell_still_spans_it(self) -> None:
        """3.2 m of authored ramp against a 0.5 m cell. Truncating instead would
        leave the outermost strip — the one that overhangs — unmeasured."""
        cells = self._cells(1.6)
        assert sum(span for _, _, span in cells) == pytest.approx(3.2)

    def test_a_zero_width_edge_contributes_nothing(self) -> None:
        assert self._cells(0.0) == []


class TestHalfWidthAt:
    def test_a_per_station_table_is_indexed_by_vertex(self) -> None:
        assert _half_width_at([5.12, 4.3, 3.2], 1) == pytest.approx(4.3)

    def test_a_vertex_past_the_end_takes_the_last(self) -> None:
        """The published table is parallel to the graph polyline, so this cannot
        happen on a matched pair — it is the guard for a stale bundle, which is
        the case the tool most wants to survive rather than crash in."""
        assert _half_width_at([5.12, 3.2], 9) == pytest.approx(3.2)

    def test_a_pre_q23_bundle_reads_as_a_constant(self) -> None:
        """One number per edge is what schema 3 published. Grading an older
        build is the reason the reader is forgiving here."""
        assert _half_width_at([5.12], 4) == pytest.approx(5.12)

    def test_an_edge_with_no_entry_is_zero_rather_than_a_guess(self) -> None:
        assert _half_width_at([], 0) == 0.0


class TestLeftOf:
    def test_it_is_perpendicular_to_travel(self) -> None:
        normal = _left_of(np.array([3.0, 4.0]))
        assert np.dot(normal, [3.0, 4.0]) == pytest.approx(0.0)
        assert np.hypot(*normal) == pytest.approx(1.0)

    def test_a_zero_length_segment_has_no_normal(self) -> None:
        """A repeated vertex is legal in the graph. Normalising it would divide
        by zero and put NaN into every cell position downstream, where it reads
        as 'no structure here' rather than as an error."""
        assert np.hypot(*_left_of(np.zeros(2))) == 0.0


class TestWalk:
    def _polyline(self, *xs: float) -> np.ndarray:
        return np.array([[x, 0.0, 0.0] for x in xs], dtype=np.float64)

    def test_every_station_knows_which_segment_it_came_from(self) -> None:
        """The width is per vertex, so a station attributed to the wrong segment
        is measured against a neighbour's width — which on a tapered approach is
        the whole defect being measured."""
        vertices = [vertex for vertex, _ in _walk(self._polyline(0.0, 10.0, 20.0), 5.0)]
        assert set(vertices) == {0, 1}
        assert vertices == sorted(vertices)

    def test_a_segment_is_broken_at_most_the_spacing_apart(self) -> None:
        points = [station for _, station in _walk(self._polyline(0.0, 10.0), 2.0)]
        gaps = np.hypot(*np.diff(np.asarray(points)[:, [0, 2]], axis=0).T)
        assert (gaps <= 2.0 + 1e-9).all()

    def test_a_segment_shorter_than_the_spacing_still_yields(self) -> None:
        assert len(list(_walk(self._polyline(0.0, 1.0), 10.0))) >= 1


class TestTally:
    def test_the_share_is_by_area_not_by_cell_count(self) -> None:
        """One wide supported cell against two narrow unsupported ones: by count
        that is 67% hanging in air, by area 20%."""
        tally = Tally()
        tally.add(supported=True, area_m2=8.0)
        tally.add(supported=False, area_m2=1.0)
        tally.add(supported=False, area_m2=1.0)

        assert tally.share == pytest.approx(0.2)

    def test_nothing_measured_is_zero_rather_than_a_division(self) -> None:
        assert Tally().share == 0.0
