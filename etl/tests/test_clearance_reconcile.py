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

from clearance_reconcile import _VERDICT, published, starved

from pipeline.clearance import NOT_MEASURED


def _manifest(rows: dict[int, list[float]]) -> dict:
    return {"carriageway": [{"edge": edge, "clear_width_m": w} for edge, w in rows.items()]}


class TestPublished:
    """The fold that turns a station table into one width per edge."""

    def test_it_takes_the_narrowest_station(self) -> None:
        assert published(_manifest({7: [9.0, 2.5, 4.0]})) == {7: 2.5}

    def test_refusals_are_filtered_before_the_min_not_clamped_after(self) -> None:
        # The defect this repo has re-learnt twice. `-1.0` is smaller than any
        # real clearance, so folding it in reports a clear street as blocked
        # solid — and on precisely the edges the ribbon never reached.
        assert published(_manifest({7: [NOT_MEASURED, 9.0, 4.0]})) == {7: 4.0}

    def test_an_edge_with_no_measured_station_is_absent_not_zero(self) -> None:
        """Absent means "this instrument never judged it", which the report calls
        out separately. Zero would read as a wall straight across the road."""
        assert published(_manifest({7: [NOT_MEASURED, NOT_MEASURED]})) == {}

    def test_an_edge_with_no_row_at_all_is_absent(self) -> None:
        assert published(_manifest({7: []})) == {}

    def test_a_bundle_naming_no_carriageway_is_empty_rather_than_an_error(self) -> None:
        assert published({}) == {}


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
