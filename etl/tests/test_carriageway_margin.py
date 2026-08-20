"""The published-carriageway-edge instrument (`tools/carriageway_margin.py`, `Q57`).

The same standard as the other tool tests: pin only what fails silently. The
report is loud, the distributions are printed in full, and a source that read
nothing shows up as a zero segment count in the first line of output.

⚠️ **The failures this file exists for are all quiet ones.**

- **The ray finds the wrong hit.** `_Index.cast` walks buckets in ray order, but
  a bucket holds its segments in insertion order — take the first hit inside one
  and the answer depends on which sheet was read first. It has to be the nearest.
- **A grade filter that excludes the wrong half.** Both publishers mark the
  *off*-grade case and leave at-grade unmarked, so an inclusion filter reads as
  a city with almost no kerbs — and `Q57` measured that the drawings' commonest
  relative level, `A01`, is the elevated one. Getting this backwards keeps 57%
  of the layer, all of it flyover, and still reports a plausible number.
- **A degenerate segment.** A repeated vertex makes the ray/segment determinant
  vanish rather than miss, so it must be dropped before the cast, not inside it.
"""

from __future__ import annotations

import numpy as np
import pytest
from carriageway_margin import _BANDS, _Index, _segments, nearest_published


def _index(*lines: list[tuple[float, float]]) -> _Index:
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    for line in lines:
        start, end = _segments(np.asarray(line, dtype=np.float64))
        starts.append(start)
        ends.append(end)
    return _Index(np.vstack(starts), np.vstack(ends))


class TestCast:
    def test_a_ray_measures_the_distance_to_a_crossing_segment(self) -> None:
        index = _index([(-50.0, 4.0), (50.0, 4.0)])
        hit = index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert hit == pytest.approx(4.0)

    def test_the_nearest_hit_wins_regardless_of_insertion_order(self) -> None:
        """The bucket holds segments in the order the sheets were read. Taking
        the first hit found inside one would make the published overhang depend
        on which of six map sheets happened to load first."""
        far = [(-50.0, 9.0), (50.0, 9.0)]
        near = [(-50.0, 2.0), (50.0, 2.0)]

        for order in ((far, near), (near, far)):
            hit = _index(*order).cast(np.zeros(2), np.array([0.0, 1.0]), 15.0)
            assert hit == pytest.approx(2.0)

    def test_a_segment_behind_the_ray_is_not_a_hit(self) -> None:
        """Both directions are cast separately and the nearer taken, so a ray
        that reached backwards would report the opposite kerb as its own."""
        index = _index([(-50.0, -3.0), (50.0, -3.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_segment_beyond_the_cap_is_not_a_hit(self) -> None:
        """An uncapped perpendicular finds something eventually and calls it a
        kerb; the cap is what makes an unmeasurable station say so."""
        index = _index([(-50.0, 30.0), (50.0, 30.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_ray_passing_beyond_a_segments_end_misses_it(self) -> None:
        """The segment is bounded. A reader that solved the infinite line would
        find a kerb across the mouth of every junction it is nowhere near."""
        index = _index([(20.0, 4.0), (60.0, 4.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_ray_parallel_to_a_segment_misses_rather_than_divides(self) -> None:
        index = _index([(0.0, -50.0), (0.0, 50.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) is None

    def test_a_hit_beyond_the_first_index_cell_is_still_found(self) -> None:
        """The candidate walk steps at half a cell; a segment further out than
        one cell must still be reached, or every wide street reads unmeasurable."""
        index = _index([(-50.0, 14.0), (50.0, 14.0)])

        assert index.cast(np.zeros(2), np.array([0.0, 1.0]), 15.0) == pytest.approx(14.0)


class TestSegments:
    def test_a_repeated_vertex_is_dropped(self) -> None:
        """A zero-length segment makes the determinant vanish rather than miss,
        so it is a silent wrong answer rather than a skipped one."""
        starts, _ = _segments(np.array([(0.0, 0.0), (0.0, 0.0), (1.0, 0.0)]))

        assert len(starts) == 1

    def test_a_single_vertex_yields_nothing(self) -> None:
        starts, ends = _segments(np.array([(0.0, 0.0)]))

        assert len(starts) == 0
        assert len(ends) == 0


class TestBands:
    def test_the_bands_split_on_the_graphs_own_median(self) -> None:
        """`Q19`'s finding is that 12 of its 14 building failures are under 20 m
        against a graph median of 47.3 m. The bands are that record's split, so
        a reader can line the two tables up; inventing a third boundary here
        would make the comparison unfalsifiable."""
        bounds = [low for low, _, _ in _BANDS]

        assert bounds == [0.0, 20.0, 47.3]


class TestNearestPublished:
    """The preference-order rule the whole two-publisher design rests on."""

    def _pair(self, first_at: float | None, second_at: float | None):
        def side(distance: float | None) -> list[tuple[float, float]]:
            return [(-50.0, distance), (50.0, distance)] if distance is not None else []

        return [
            (
                name,
                _index(side(at)) if at is not None else _index([(999.0, 999.0), (1000.0, 999.0)]),
            )
            for name, at in (("first", first_at), ("second", second_at))
        ]

    def test_the_first_publisher_that_answers_wins(self) -> None:
        """Order is preference, not a tie-break: the drawings are the semantic
        carriageway edge and iB1000 is the fallback for density. Sorting by
        distance instead would silently prefer whichever kerb happened to be
        nearer and make the config's ordering decorative."""
        indexes = self._pair(9.0, 2.0)

        chosen, nearest, _ = nearest_published(np.zeros(2), np.array([0.0, 1.0]), indexes, 15.0)

        assert chosen == "first"
        assert nearest == pytest.approx(9.0)

    def test_the_second_answers_when_the_first_cannot(self) -> None:
        indexes = self._pair(None, 2.0)

        chosen, nearest, _ = nearest_published(np.zeros(2), np.array([0.0, 1.0]), indexes, 15.0)

        assert chosen == "second"
        assert nearest == pytest.approx(2.0)

    def test_nobody_answering_is_reported_as_no_name(self) -> None:
        indexes = self._pair(None, None)

        chosen, _, spread = nearest_published(np.zeros(2), np.array([0.0, 1.0]), indexes, 15.0)

        assert chosen == ""
        assert spread == []

    def test_every_publisher_is_still_asked_so_the_spread_is_real(self) -> None:
        """⚠️ The losing publishers do not decide the measurement, and short-
        circuiting once one answers would be the obvious optimisation — it would
        also delete the cross-check that is `Q57`'s whole argument for reading
        more than one source."""
        indexes = self._pair(9.0, 2.0)

        _, _, spread = nearest_published(np.zeros(2), np.array([0.0, 1.0]), indexes, 15.0)

        assert sorted(spread) == [pytest.approx(2.0), pytest.approx(9.0)]

    def test_the_nearer_side_wins_within_one_publisher(self) -> None:
        """Both rays come from one `cast_both`; the metric takes the nearer kerb
        because the far one is what a junction mouth and a dual carriageway
        corrupt."""
        index = _index([(-50.0, 6.0), (50.0, 6.0)], [(-50.0, -2.0), (50.0, -2.0)])

        _, nearest, _ = nearest_published(
            np.zeros(2), np.array([0.0, 1.0]), [("only", index)], 15.0
        )

        assert nearest == pytest.approx(2.0)


class TestCastBoth:
    def test_one_solve_answers_both_directions(self) -> None:
        index = _index([(-50.0, 4.0), (50.0, 4.0)], [(-50.0, -7.0), (50.0, -7.0)])

        forward, backward = index.cast_both(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert forward == pytest.approx(4.0)
        assert backward == pytest.approx(7.0)

    def test_a_direction_with_nothing_in_it_is_None(self) -> None:
        index = _index([(-50.0, 4.0), (50.0, 4.0)])

        forward, backward = index.cast_both(np.zeros(2), np.array([0.0, 1.0]), 15.0)

        assert forward == pytest.approx(4.0)
        assert backward is None

    def test_reversing_the_direction_swaps_the_pair(self) -> None:
        """The backward hit is the same arithmetic read at negative `along`, so
        the two must agree exactly rather than nearly."""
        index = _index([(-50.0, 4.0), (50.0, 4.0)], [(-50.0, -7.0), (50.0, -7.0)])

        forward, backward = index.cast_both(np.zeros(2), np.array([0.0, 1.0]), 15.0)
        reversed_pair = index.cast_both(np.zeros(2), np.array([0.0, -1.0]), 15.0)

        assert reversed_pair == (backward, forward)
