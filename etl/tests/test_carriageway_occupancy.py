"""The `Q19` occupancy probe (`tools/carriageway_occupancy.py`).

Same standard as `test_deck_error.py`, `test_overhang.py` and
`test_ground_clearance.py`: only the parts whose failure mode is **silent**. The
headline shares check themselves against `Q19`'s recorded table, and an index
that stopped finding walls at all would read 0.000% and nobody could miss it.
What would not announce itself is everything below.

This tool shipped with three defects, each of which produced a plausible table
rather than an obviously wrong one. **Only the first is pinned here**, and the
other two are named so nobody reads this file as covering them:

- ✅ **The share was divided by the wrong area.** `Q19` publishes its three
  figures as shares of *all* drawn carriageway — they sum to its 5.17% headline —
  so gating the level-0 pair against the level-0 area alone read them about a
  tenth looser than they were written. A bar moved by a choice of divisor.
  `TestShareDenominator` holds it.
- ⚠️ **A trimmed cross-section was judged anyway** — one clear cell out of twenty
  at a junction read as a 0.49 m corridor, condemning **18 edges that are not
  blocked** (44 failures where there are 26). **Untested.** The guard lives
  inside `survey`, which wants a whole `Lattice` built from a shipped bundle.
- ⚠️ **The landmark bearing was applied unnegated.** `rot_y_deg` is a compass
  bearing and `generated_landmarks.gd` places a hero with the *negative*
  rotation; HKCEC's is 0.0, so it was invisible until a landmark with a real
  bearing went through it. **Untested**, and it wants a `.glb` to exercise. Its
  only guard is that `generated_landmarks.gd` states the convention it must match.

⚠️ What else has **no unit test and would most want one**: the pruning in
`index_corners`, which drops any triangle whose plan box misses the carriageway
or whose height range misses the band. It is a superset test, so a bug there
*removes* occupied cells and the tool reads cleaner — the one direction this
must not flatter. `walk_carriageway` now feeds both the prune and the survey from
one lattice, which makes the superset property structural rather than a
convention, but nothing here asserts it. It wants a whole shipped bundle, and the
region run is the only thing that provides one.
"""

from __future__ import annotations

import numpy as np
import pytest
from carriageway_occupancy import (
    BUMPER_HIGH_M,
    BUMPER_LOW_M,
    INDEX_CELL_M,
    Occupied,
    Survey,
    _barycentric,
    _clear_run,
)


class TestShareDenominator:
    """`Q19`'s three figures share one whole, and the gates ride on that."""

    def _survey(self) -> Survey:
        found = Survey()
        # 900 m2 at grade with 90 of it occupied, 100 m2 off-grade with 50.
        found.add(0, "BUILDING", 90.0)
        found.add(0, None, 810.0)
        found.add(1, "INFRASTRUCTURE", 50.0)
        found.add(1, None, 50.0)
        return found

    def test_the_gated_share_is_of_all_drawn_carriageway(self) -> None:
        """90 of 1000 m2, not 90 of 900. `Q19`'s `BUILDING` 1.72%,
        `INFRASTRUCTURE` 1.60% and off-grade 1.87% add up to its 5.17% headline,
        which is only true if all three are shares of the same whole."""
        assert self._survey().drawn_share(0, "BUILDING") == pytest.approx(0.09)

    def test_the_per_level_share_is_of_that_level_only(self) -> None:
        """The informative column, and the one that must *not* reach the gate.
        Off-grade reads 50% of its own ribbon and 5% of the region, and the
        difference is a factor of ten in how bad level +1 looks."""
        found = self._survey()
        assert found.share(1, "INFRASTRUCTURE") == pytest.approx(0.5)
        assert found.drawn_share(1, "INFRASTRUCTURE") == pytest.approx(0.05)

    def test_an_unoccupied_class_is_zero_rather_than_absent(self) -> None:
        """A class that never occupied anything has to score 0.0, not raise.
        The gate sums over class names it was handed, and a missing key there
        would fail the build for the class being clean."""
        assert self._survey().drawn_share(0, "LANDMARK") == 0.0


class TestClearRun:
    """The corridor arithmetic. Every mistake here reads as a plausible width."""

    def test_the_run_must_be_contiguous(self) -> None:
        """Three clear cells split by a wall are not a three-cell corridor. A
        car needs them side by side, and counting clear cells instead of the
        longest run is the whole difference between weaving past an obstruction
        and being stopped by it."""
        assert _clear_run([False, True, False, False], 1.0) == pytest.approx(2.0)

    def test_a_fully_blocked_station_has_no_corridor(self) -> None:
        assert _clear_run([True, True, True], 1.0) == pytest.approx(0.0)

    def test_a_clear_station_is_its_whole_width(self) -> None:
        assert _clear_run([False] * 4, 0.5) == pytest.approx(2.0)

    def test_the_run_is_measured_in_metres_not_cells(self) -> None:
        """`--across-m` changes the cell width, and the criterion is a lane in
        metres. A run counted in cells would pass or fail the same road
        depending on the sampling lattice."""
        assert _clear_run([False, False], 0.25) == pytest.approx(0.5)


def _occupied(heights: list[float], cell_m: float = INDEX_CELL_M) -> Occupied:
    """One plan cell holding these surface heights, binned at `cell_m`."""
    return Occupied(
        cells={(0, 0): np.sort(np.asarray(heights, dtype=np.float64))},
        triangles_kept=1,
        triangles_seen=1,
        samples=len(heights),
        cell_m=cell_m,
    )


class TestInBand:
    """The band test, at its two edges."""

    def test_surface_inside_the_band_is_occupation(self) -> None:
        assert _occupied([1.0]).in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_surface_below_the_bumper_is_not(self) -> None:
        """Kerbs, road markings and the ribbon's own thickness live here. The
        floor of the band is what keeps them out of a wall count."""
        assert not _occupied([0.1]).in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_surface_above_the_band_is_not(self) -> None:
        """A podium overhanging the street 6 m up is Hong Kong working as
        intended, and counting it would make the city its own defect."""
        assert not _occupied([6.0]).in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_the_band_is_inclusive_at_both_ends(self) -> None:
        """A surface exactly at bumper height is a surface the bumper meets."""
        assert _occupied([BUMPER_LOW_M]).in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)
        assert _occupied([BUMPER_HIGH_M]).in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_it_finds_the_band_among_many_heights(self) -> None:
        """The lookup is a binary search over a sorted column, so a wall whose
        samples run from the pavement to the roof must still be found by the
        slice of it that crosses the band — not just by its lowest point."""
        wall = _occupied([0.0, 0.1, 0.2, 1.2, 8.0, 30.0])
        assert wall.in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_an_empty_cell_is_clear_rather_than_an_error(self) -> None:
        assert not _occupied([1.0]).in_band(99.5, 99.5, BUMPER_LOW_M, BUMPER_HIGH_M)


class TestPlanBin:
    """The plan cell — **the dominant error term in every corridor width**.

    `Q51`'s starved-edges headline is very nearly a function of this constant —
    `INDEX_CELL_M` carries the swept figures. What is silent is a *mismatch*:
    bin the heights at one size and query them at another and cells stop lining
    up, so walls are looked for where they were never filed — and every one of
    those lookups reads **clear**, the one direction this tool must not flatter.
    """

    def test_the_query_uses_the_cell_the_heights_were_binned_at(self) -> None:
        # Cell (0, 0) at 1.0 m spans 0-1 m; at 0.25 m it spans 0-0.25 m. A point
        # at 0.5 m is inside the first and outside the second, so an index that
        # ignored its own `cell_m` would answer the same for both.
        assert _occupied([1.0], 1.0).in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)
        assert not _occupied([1.0], 0.25).in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_a_coarser_bin_reaches_further(self) -> None:
        """Which is the smear itself: one sample blocks its whole cell, so the
        coarser the cell the more carriageway one wall condemns."""
        assert _occupied([1.0], 4.0).in_band(3.5, 3.5, BUMPER_LOW_M, BUMPER_HIGH_M)
        assert not _occupied([1.0], 1.0).in_band(3.5, 3.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_the_default_is_the_shipped_constant(self) -> None:
        # So a sweep cannot become the default by accident. The coarseness is
        # deliberate: it is what makes this tool immune to the along-edge
        # aliasing `clearance.py` is exposed to (`Q51`).
        assert Occupied(cells={}, triangles_kept=0, triangles_seen=0, samples=0).cell_m == (
            INDEX_CELL_M
        )


class TestLattice:
    """Surface sampling. Too sparse and walls go missing, which reads as clear."""

    @pytest.mark.parametrize("steps", [1, 2, 5])
    def test_every_weight_is_a_barycentric_coordinate(self, steps: int) -> None:
        weights = _barycentric(steps)
        assert np.allclose(weights.sum(axis=1), 1.0)
        assert (weights >= -1e-12).all()

    def test_the_corners_are_always_sampled(self) -> None:
        """A triangle's corners are where it meets its neighbours, so a lattice
        that missed them would leave seams unsampled along every wall."""
        weights = _barycentric(3)
        for corner in np.eye(3):
            assert np.isclose(weights, corner).all(axis=1).any()

    def test_the_lattice_refines_with_the_step_count(self) -> None:
        assert len(_barycentric(1)) == 3
        assert len(_barycentric(2)) == 6


class TestMissesStayCounted:
    """`deck_error`'s fourth defect, refused by construction."""

    def test_coverage_falls_when_cells_cannot_be_measured(self) -> None:
        """A cell with no road drawn is counted, never skipped. A tool whose
        denominator shrinks when the thing it measures breaks reports a pass for
        having stopped looking — which is how that defect exited 0 with a third
        of the carriageway broken."""
        found = Survey()
        found.asked = 10
        found.measured = 6
        found.no_road = 4
        assert found.coverage == pytest.approx(0.6)

    def test_coverage_of_nothing_is_zero_not_one(self) -> None:
        """An empty survey has measured nothing, and must not read as complete
        coverage — that is the shape a missing road mesh would take."""
        assert Survey().coverage == 0.0
