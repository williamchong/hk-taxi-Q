"""The clearance reconciliation ratchet (`tools/clearance_reconcile.py`).

The same standard as the other tool tests: pin only what fails silently. The
ratchet's own headline is loud — it names both counts and the expected ones in
its `FAIL` line — and the grading it does is `carriageway_occupancy`'s, tested
there. What would not announce itself is the fold below.

⚠️ **`published` is the third implementation of "the narrowest measured station of
each edge", and the first two both got it wrong the same way.** `NOT_MEASURED` is
`-1.0`, so it is the smallest number in any row it appears in: fold it into the
`min` and every part-trimmed edge becomes the most blocked in the region, the
starved count balloons, and the ratchet fails with a diagnosis that is entirely
fictional. `ClearanceReport.tightest` carries the same warning in the pipeline.

⚠️ What is **not** tested here and would want a shipped bundle: that the hoisted
lattice is the one every sweep pass grades. `grade` takes it as a parameter now
rather than rebuilding it, which makes that structural, but nothing asserts it.
"""

from __future__ import annotations

import pytest
from clearance_reconcile import _VERDICT, published, starved

from pipeline.clearance import NOT_MEASURED


def _manifest(rows: dict[int, list[float]]) -> dict:
    return {"carriageway": [{"edge": edge, "clear_width_m": w} for edge, w in rows.items()]}


def _published(
    rows: dict[int, list[float]],
    levels: dict[int, int] | None = None,
    walked: tuple[int, ...] = (0,),
) -> dict[int, float]:
    """`published` with every edge at grade unless a test says otherwise.

    The level filter is one test's subject and noise in every other, so it is
    defaulted here rather than restated eight times.
    """
    # ⚠️ `is None` and not `or`: an explicitly EMPTY map is a real case here —
    # it is what the refusal test passes — and `levels or ...` silently replaced
    # it with the at-grade default, which is the branch that test exists to
    # prove is gone. It did, and the test caught it.
    at_grade = dict.fromkeys(rows, 0) if levels is None else levels
    return published(_manifest(rows), level_of=at_grade, walked=walked)


class TestPublished:
    """The fold that turns a station table into one width per edge."""

    def test_it_takes_the_narrowest_station(self) -> None:
        assert _published({7: [9.0, 2.5, 4.0]}) == {7: 2.5}

    def test_refusals_are_filtered_before_the_min_not_clamped_after(self) -> None:
        # The defect this repo has re-learnt twice. `-1.0` is smaller than any
        # real clearance, so folding it in reports a clear street as blocked
        # solid — and on precisely the edges the ribbon never reached.
        assert _published({7: [NOT_MEASURED, 9.0, 4.0]}) == {7: 4.0}

    def test_an_edge_with_no_measured_station_is_absent_not_zero(self) -> None:
        """Absent means "this instrument never judged it", which the report calls
        out separately. Zero would read as a wall straight across the road."""
        assert _published({7: [NOT_MEASURED, NOT_MEASURED]}) == {}

    def test_an_edge_with_no_row_at_all_is_absent(self) -> None:
        assert _published({7: []}) == {}

    def test_a_bundle_naming_no_carriageway_is_empty_rather_than_an_error(self) -> None:
        assert published({}, level_of={}, walked=(0,)) == {}


class TestTheLevelFilter:
    """🔴 Both halves of a reconciliation have to judge one population.

    This fold read every row in `city.json` until 2026-09-04, which was the same
    population as the grader's while the pipeline published level 0 alone. The
    moment it published level 1, an unfiltered fold put three off-grade starved
    edges into `pipeline_set` with no grader row opposite them — three
    `judged by only one instrument` lines, and `EXPECT_PIPELINE` moved by
    something that is not a disagreement. A ratchet over two populations is not
    a ratchet, and it fails in the direction of looking like a finding.
    """

    def test_a_level_outside_the_walk_is_dropped(self) -> None:
        rows = {1: [3.0], 2: [1.25]}
        assert _published(rows, {1: 0, 2: 1}, (0,)) == {1: 3.0}

    def test_a_level_inside_the_walk_is_kept(self) -> None:
        rows = {1: [3.0], 2: [1.25]}
        assert _published(rows, {1: 0, 2: 1}, (0, 1)) == {1: 3.0, 2: 1.25}

    def test_an_edge_the_graph_does_not_name_is_refused_rather_than_defaulted(self) -> None:
        """🔴 Indexed, so an unknown edge raises rather than filing itself.

        The document and the graph come from one run, so this is unreachable —
        and *both* defaults are wrong on invalid input: read as off-grade it
        silently drops a street from the gated count, read as at-grade it files
        an unknown edge into the population the ratchet is measured over.
        `split_by_level` refuses a default for this reason and `surface.py`
        refuses one over `offset_m`. An inconsistency here is a thing to hear
        about, not to resolve by a choice of default.
        """
        with pytest.raises(KeyError):
            _published({9: [3.0]}, {}, (0,))


class TestStarved:
    """The bar, which is strict — a corridor exactly one lane wide is passable."""

    def test_under_the_bar_is_starved(self) -> None:
        assert starved({1: 3.19}, 3.2) == {1}

    def test_exactly_the_bar_is_not(self) -> None:
        assert starved({1: 3.2}, 3.2) == set()


class TestVerdict:
    """One spelling per side, so a reader can grep the log for one word."""

    def test_both_and_neither_read_as_agreement(self) -> None:
        assert _VERDICT[True, True] == "agree"
        assert _VERDICT[False, False] == "agree"

    def test_each_disagreement_names_the_instrument_that_condemns(self) -> None:
        assert _VERDICT[True, False] == "grader-only"
        assert _VERDICT[False, True] == "pipeline-only"
