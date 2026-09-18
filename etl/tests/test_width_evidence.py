"""The width-evidence grader (`tools/width_evidence.py`, `Q127`).

Pins what fails silently. Every reading here is graded against the survey's
own widths, so a reading that broke in a plausible direction — a lane counted
twice, a cross street's asphalt counted as this one's, a reading agreeing with
the answer it is graded against — prints a clean table rather than an error.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from width_evidence import (
    _VOTERS,
    LOWER,
    UPPER,
    Edge,
    _side_sum,
    agreeing,
    chain_at_centre,
    consensus,
    contiguous_run,
    dividers,
    grade,
    main,
    outside,
    runs,
    street_borrow,
    voter_suffix,
)

from pipeline.polyline import Segments


def _edge(
    edge_id: int, width: float, source: str, *, street: str = "A", two_way: bool = False
) -> Edge:
    return Edge(
        id=edge_id,
        polyline=np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]),
        length_m=100.0,
        width_m=width,
        width_source=source,
        two_way=two_way,
        lanes=2,
        lanes_source="authored",
        speed_limit_kph=50,
        name=street,
        street=(street, two_way),
    )


class TestDividers:
    def test_a_double_line_is_one_divider(self) -> None:
        """`RM1001` is two lines 0.1 m apart. Counted as two it is a 0.25 m lane,
        and every pitch and lane count across that street is wrong."""
        assert dividers([-0.05, 0.05, 3.2], merge_m=1.5) == pytest.approx([0.0, 3.2])

    def test_lines_a_lane_apart_stay_apart(self) -> None:
        assert dividers([0.0, 3.0, 6.1], merge_m=1.5) == pytest.approx([0.0, 3.0, 6.1])


class TestChain:
    def test_the_chain_through_the_centreline_is_kept(self) -> None:
        """The opposed carriageway's lane lines lie beyond a median, and a pitch
        taken across that median is not a lane."""
        # The far chain is the LONGER one, so a rule that took the widest row
        # instead of the one through the centreline reads the other carriageway.
        chain, broken = chain_at_centre([-1.6, 1.6, 12.0, 15.2, 18.4, 21.6], gap_m=7.3)

        assert chain == [-1.6, 1.6]
        assert broken is True

    def test_an_unbroken_row_is_not_reported_as_cut(self) -> None:
        chain, broken = chain_at_centre([-1.6, 1.6], gap_m=7.3)

        assert chain == [-1.6, 1.6]
        assert broken is False


class TestContiguousRun:
    def test_the_run_stops_at_the_first_gap_either_side(self) -> None:
        """A lay-by beyond a kerb island is carriageway HyD draws, and not this
        road's. Counting every owned cell reads it in."""
        grid = np.array([[True, False, True, True, True, False, True]])

        assert contiguous_run(grid, centre=3).tolist() == [3]

    def test_a_centre_off_the_carriageway_reads_nothing(self) -> None:
        grid = np.array([[True, True, False, True, True]])

        assert contiguous_run(grid, centre=2).tolist() == [0]


class TestRuns:
    def test_half_a_glyph_splits_two_rows(self) -> None:
        half = lambda a, b: 0.5 * min(a, b)  # noqa: E731
        split = runs([(0.0, 4.0), (1.9, 4.0), (4.0, 4.0)], half)

        assert [len(run) for run in split] == [2, 1]


class TestGrade:
    def test_measured_edges_are_graded_and_authored_ones_are_reach(self) -> None:
        edges = {1: _edge(1, 8.0, "one_way_uncrossed"), 2: _edge(2, 6.4, "authored")}

        one_way, two_way = grade("x", {1: 9.0, 2: 7.0}, edges)

        assert one_way.errors == pytest.approx([1.0])
        assert one_way.reached == [2]
        assert two_way.errors == [] and two_way.reached == []

    def test_a_deck_width_is_neither(self) -> None:
        """Level 1 is not what any reading here walks; a deck width graded as a
        reference would grade a street reading against a flyover."""
        edges = {1: _edge(1, 8.0, "deck")}

        one_way, _ = grade("x", {1: 9.0}, edges)

        assert one_way.errors == [] and one_way.reached == []


class TestStreetBorrow:
    def test_a_measured_edge_never_lends_to_itself(self) -> None:
        """🔴 Leave-one-out. With the edge in its own donor pool the borrow's
        reference error shrinks toward zero by construction — `Q58`'s trap in the
        one row the whole synthesis compares against."""
        edges = {
            1: _edge(1, 8.0, "one_way_uncrossed"),
            2: _edge(2, 12.0, "one_way_uncrossed"),
            3: _edge(3, 6.4, "authored"),
        }

        graded = street_borrow(edges, leave_out=True)

        assert graded[1] == pytest.approx(12.0)
        assert graded[2] == pytest.approx(8.0)
        assert graded[3] == pytest.approx(10.0)

    def test_direction_is_part_of_the_street(self) -> None:
        edges = {
            1: _edge(1, 8.0, "two_way_span", two_way=True),
            2: _edge(2, 6.4, "authored", two_way=False),
        }

        assert street_borrow(edges, leave_out=False) == {}


class TestCombinations:
    def test_agreement_needs_an_independent_reading_in_tolerance(self) -> None:
        assert agreeing({1: 8.0, 2: 8.0}, [{1: 8.9, 2: 10.0}], 1.0) == {1: 8.0}

    def test_consensus_needs_two_within_tolerance_of_the_median(self) -> None:
        # Edge 2's median is 9.8 and only that reading lies within a metre of it:
        # one reading agreeing with the median it set is not two readings agreeing.
        readings = [{1: 8.0, 2: 8.0}, {1: 8.4, 2: 9.8}, {1: 20.0, 2: 20.0}]

        agreed = consensus(readings, 1.0)

        assert agreed[1] == pytest.approx(8.2)
        assert 2 not in agreed


class TestVoters:
    """Which readings may CONFIRM a strip (`Q128` stage 0a).

    🔴 **The roster is a ratchet, not a preference.** `Q127` measured the
    combinations at 0.63 m by construction when the ray survey was let vote — on
    a reference edge it IS the reference — so what has to be pinned is that it
    cannot come back by accident, and that a misspelt voter cannot quietly
    narrow the roster a pasted table names.
    """

    def test_the_ray_survey_is_never_a_voter(self) -> None:
        assert not [name for name in _VOTERS.values() if "ray survey" in name]

    def test_an_unknown_voter_is_refused_before_a_source_is_read(self) -> None:
        # Refused at parse time deliberately: the readings take minutes to build,
        # and the region is not even resolved yet — so this exits on the voter
        # rather than on the bogus region below it.
        with pytest.raises(SystemExit, match="pick from"):
            main(["--region", "nowhere", "--voters", "ray_survey"])

    def test_an_empty_roster_is_refused_rather_than_confirming_nothing(self) -> None:
        # Not the same as "no combinations": an empty list makes `agreeing`
        # return {} and the cascade would print a clean table reaching nothing.
        with pytest.raises(SystemExit, match="pick from"):
            main(["--region", "nowhere", "--voters", ""])

    def test_the_full_roster_prints_the_label_Q127_published(self) -> None:
        assert voter_suffix(list(_VOTERS)) == ""

    def test_a_narrowed_roster_names_itself(self) -> None:
        assert voter_suffix(["borrow", "arrows"]) == " [borrow+arrows]"


class TestOutside:
    """The one predicate both the bound table and the conflict count read.

    ⚠️ An upper bound and a lower bound are opposite tests; a predicate that
    forgot the kind would report every lower bound as never violated, which is
    what a *valid* bound looks like."""

    def test_the_two_kinds_are_opposite(self) -> None:
        assert outside(9.0, 8.0, UPPER) and not outside(7.0, 8.0, UPPER)
        assert outside(7.0, 8.0, LOWER) and not outside(9.0, 8.0, LOWER)


class TestSideSum:
    def test_only_an_edge_bounded_on_both_sides_gets_a_limit(self) -> None:
        """A kerb lies between the centreline and a post on EITHER side; one side
        alone bounds half a road and says nothing about its width."""
        segments = Segments.of([{"id": 1, "polyline": [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]}])

        right_only = _side_sum([(50.0, 5.0)], segments, 30.0)
        left_only = _side_sum([(50.0, -5.0)], segments, 30.0)
        both = _side_sum([(50.0, 5.0), (60.0, -4.0), (70.0, -9.0)], segments, 30.0)

        assert right_only == {}
        assert left_only == {}
        assert both[1] == pytest.approx(9.0)

    def test_a_point_past_the_end_bounds_nothing(self) -> None:
        segments = Segments.of([{"id": 1, "polyline": [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]}])

        assert _side_sum([(110.0, 5.0), (110.0, -5.0)], segments, 30.0) == {}


def test_nan_readings_are_not_graded() -> None:
    edges = {1: _edge(1, 8.0, "one_way_uncrossed")}

    one_way, _ = grade("x", {1: math.nan}, edges)

    assert one_way.errors == []
