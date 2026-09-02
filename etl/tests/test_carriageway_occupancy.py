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

import argparse
from typing import ClassVar

import numpy as np
import pytest
from carriageway_occupancy import (
    BUMPER_HIGH_M,
    BUMPER_LOW_M,
    CORRIDOR_LEVELS,
    INDEX_CELL_M,
    Lattice,
    Occupied,
    Standing,
    Survey,
    _barycentric,
    _centreline_verdict,
    _clear_run,
    _closest_approach,
    _covers_centreline,
    _edges_argument,
    _levels_argument,
    _profile_runs,
    _standing_runs,
    _starved_shape,
    split_by_level,
    survey,
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


class TestStarvedShape:
    """How much of an edge is starved, and in how many pieces.

    `Q19`'s two fix families wear one symptom — an edge under one lane — and
    the corridor figure cannot tell them apart, because it is a minimum and a
    minimum has no extent. These two numbers are what separates them, so a
    mistake here files a wall under frontage or the reverse.
    """

    def test_a_wall_across_the_street_is_one_station(self) -> None:
        """The building half's signature: clear, blocked for a metre, clear
        again. That is a road passing under a volume the source extruded shut,
        and its fix is an opening rather than a moved footprint."""
        assert _starved_shape([5.0, 5.0, 0.0, 5.0, 5.0], 3.2, 1.0) == pytest.approx((1.0, 1.0))

    def test_a_frontage_standing_in_the_road_is_one_long_run(self) -> None:
        assert _starved_shape([0.5] * 40 + [5.0], 3.2, 1.0) == pytest.approx((40.0, 40.0))

    def test_the_total_and_the_run_are_reported_separately(self) -> None:
        """The discriminator, and the reason one number would not do: a pier
        field starves as much of the edge as a wall of the same total length
        and is a different defect. Six metres in three pieces, not one six."""
        assert _starved_shape([0.0, 0.0, 5.0, 0.0, 0.0, 5.0, 0.0, 0.0], 3.2, 1.0) == pytest.approx(
            (6.0, 2.0)
        )

    def test_the_bar_is_the_bar_the_gate_uses(self) -> None:
        """A station exactly at one lane is not starved. `is_passable` reads
        `>=` on the same figure, and an off-by-one here would report edges the
        gate does not fail."""
        assert _starved_shape([3.2, 3.19], 3.2, 1.0) == pytest.approx((1.0, 1.0))

    def test_the_shape_is_measured_in_metres_not_stations(self) -> None:
        """`--spacing-m` moves the station pitch, and both figures scale with
        it — a run counted in stations would describe the same blockage
        differently at a different sampling. ⚠️ This pins the *nominal* pitch,
        which is the only one this function is given; the walk's real pitch is
        a little shorter and the docstring says by how much."""
        assert _starved_shape([0.0, 0.0], 3.2, 0.5) == pytest.approx((1.0, 1.0))

    def test_an_edge_that_never_starves_has_no_shape(self) -> None:
        assert _starved_shape([5.0, 5.0], 3.2, 1.0) == pytest.approx((0.0, 0.0))


class TestProfileRuns:
    """The profile's run-length encoding — `Q19`'s shape argument, printed.

    `_starved_shape` reduces the same list to a total and a run, and those two
    numbers let `Q19` read a spot blockage as a frontage for two corrections
    running. This is the encoding that made the difference visible, so an error
    here re-hides it.
    """

    def test_a_repeated_width_is_one_run(self) -> None:
        assert _profile_runs([10.2, 10.2, 10.2]) == [(10.2, 3)]

    def test_the_building_half_signature_survives_the_encoding(self) -> None:
        """`e627` as published: full drawn width, a two-station collapse, full
        width again. A frontage cannot make this shape — it would leave about
        half the ribbon for its whole length."""
        assert _profile_runs([10.2] * 7 + [1.0, 1.5] + [10.2] * 3) == [
            (10.2, 7),
            (1.0, 1),
            (1.5, 1),
            (10.2, 3),
        ]

    def test_rounding_happens_before_grouping(self) -> None:
        """⚠️ The trap this function exists around. Every clear run is an
        integer multiple of a ~0.4876 m across-span, so two stations that both
        read "full width" differ in the last bits. Grouping the raw floats
        prints 21 runs of one where the reader needs one run of 21."""
        assert _profile_runs([10.2400, 10.2401, 10.2399]) == [(10.2, 3)]

    def test_walk_order_is_preserved(self) -> None:
        """The same widths in a different order are a different edge. Sorting
        or tallying would turn 'clear, then a wall' into a histogram, which is
        exactly the reduction that lost the finding the first time."""
        assert _profile_runs([1.0, 10.2, 1.0]) == [(1.0, 1), (10.2, 1), (1.0, 1)]

    def test_an_edge_with_no_judged_station_encodes_to_nothing(self) -> None:
        assert _profile_runs([]) == []


class TestCentrelineVerdict:
    """What stands on the centreline, and the two ways to get that wrong.

    `Q19` refused every remaining width candidate on this one query: `lanes`,
    `width_m` and `widen_default` all move the ribbon's *edges*, so an occupier
    on the centreline is out of reach of all three. It had never been asked
    from the shipped tool.
    """

    def _offsets(self, count: int, span_m: float) -> list[float]:
        """`walk_carriageway`'s own convention — left rim inward, in even steps,
        so the centre cell of an odd-length section sits at exactly 0.0."""
        half = count * span_m / 2.0
        return [-half + span_m * (i + 0.5) for i in range(count)]

    def test_the_centreline_cell_is_the_one_nearest_zero(self) -> None:
        offsets = self._offsets(5, 1.0)
        standing = [None, None, "BUILDING", None, None]
        verdict = _centreline_verdict(standing, offsets, 1.0)
        assert verdict is not None
        assert verdict.occupier == "BUILDING"
        assert verdict.centre_offset_m == pytest.approx(0.0)

    def test_a_clear_centreline_reports_how_narrowly_it_escaped(self) -> None:
        """`Q19`'s two exceptions, `e627` and `e315`, are clear at the centre and
        0.5 m from the occupier. Reporting only "clear" would file them as
        counter-examples when they are the same defect one cell over."""
        offsets = self._offsets(5, 1.0)
        verdict = _centreline_verdict([None, "BUILDING", None, None, None], offsets, 1.0)
        assert verdict is not None
        assert verdict.occupier is None
        assert verdict.to_occupier_m == pytest.approx(1.0)
        assert verdict.to_clear_m == pytest.approx(0.0)

    def test_a_symmetric_cross_section_is_given_no_side(self) -> None:
        """⚠️ The bias this function is written against. `Q19` reads the *sign*
        to tell a whole-layer registration shift from fifteen unrelated sites,
        and the walk starts at the left rim — so breaking a tie by index would
        lean every symmetric section negative and make the signs read less mixed
        than they are."""
        offsets = self._offsets(5, 1.0)
        verdict = _centreline_verdict(
            [None, "BUILDING", "BUILDING", "BUILDING", None], offsets, 1.0
        )
        assert verdict is not None
        assert verdict.to_clear_m == pytest.approx(2.0)
        assert np.isnan(verdict.clear_offset_m)

    def test_an_asymmetric_cross_section_keeps_its_side(self) -> None:
        offsets = self._offsets(5, 1.0)
        verdict = _centreline_verdict(
            [None, "BUILDING", "BUILDING", "BUILDING", "BUILDING"], offsets, 1.0
        )
        assert verdict is not None
        assert verdict.clear_offset_m == pytest.approx(-2.0)

    def test_a_fully_blocked_section_has_no_way_out(self) -> None:
        """⚠️ `inf`, never 0.0. A blocked cross-section's distance-to-clear is
        undefined, and 0.0 is the value that means "the centreline is clear" —
        the two readings are opposite and would print the same."""
        offsets = self._offsets(3, 1.0)
        verdict = _centreline_verdict(["BUILDING"] * 3, offsets, 1.0)
        assert verdict is not None
        assert verdict.to_clear_m == float("inf")
        assert verdict.to_occupier_m == pytest.approx(0.0)

    def test_a_trimmed_section_centres_on_what_was_judged(self) -> None:
        """⚠️ The index trap. Cells with no road drawn never reach `standing_at`,
        so at a junction trim the judged cells can all sit to one side. The
        centreline is the nearest survivor to zero — several metres off the true
        centre, and still the only centreline this station has. Indexing the
        walk's own min-offset cell instead would index a list it is not aligned
        with; index 0 would report the left rim."""
        offsets = [2.5, 3.5, 4.5]
        verdict = _centreline_verdict(["BUILDING", None, None], offsets, 1.0)
        assert verdict is not None
        assert verdict.centre_offset_m == pytest.approx(2.5)
        assert verdict.occupier == "BUILDING"

    def test_a_station_with_nothing_judged_has_no_verdict(self) -> None:
        assert _centreline_verdict([], [], 1.0) is None


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


class TestCorridorLevels:
    """`--levels` is `P4-1`'s knob, and every way it could flatter the gate.

    The corridor gate reads the level-0 rows alone, because an off-grade edge is
    graded and never gated (`Q57`). That split is what makes the *shape* of this
    flag load-bearing: widening the corridor is a measurement, and narrowing it
    below the population the bars were written against is a way to get a green
    run out of a red bundle.
    """

    def test_the_default_is_level_zero_alone(self) -> None:
        """🔴 Moving this moves `clearance_reconcile.py`'s `EXPECT_GRADER`, and
        `Q51`'s ratchet is what keeps the pipeline's count and this tool's count
        describing one bundle."""
        assert CORRIDOR_LEVELS == (0,)

    def test_a_set_without_level_zero_is_refused(self) -> None:
        """🔴 **The defect this flag shipped with, for one run.** `--levels 1`
        leaves the gate an empty population and it passes for having stopped
        looking: it printed "Within the accepted bounds." on a bundle with 21
        starved level-0 edges. The unmapped-level guard cannot catch it, because
        level 1 *is* mapped."""
        with pytest.raises(argparse.ArgumentTypeError, match="must include 0"):
            _levels_argument("1")

    def test_a_level_below_the_terrain_is_refused(self) -> None:
        """`walk_carriageway` skips them, and folding them in would add their
        area to `drawn_share`'s denominator — which sums every level — so the two
        gated bars would read looser for no reason but a choice of divisor."""
        with pytest.raises(argparse.ArgumentTypeError, match="below the terrain"):
            _levels_argument("0,-1")

    def test_an_empty_set_is_refused(self) -> None:
        """The empty set reading as agreement, which `pipeline/clearance.py`
        refuses at the sibling flag.

        ⚠️ **Pinned by message, because the branch that catches this is not the
        obvious one.** `"".split(",")` is `[""]`, so an empty argument is caught
        by the empty-*piece* guard inside the loop and never by a check for an
        empty set afterwards — one was written and was unreachable. A bare
        `pytest.raises` passed while covering nothing."""
        with pytest.raises(argparse.ArgumentTypeError, match="comma-separated integers"):
            _levels_argument("")
        with pytest.raises(argparse.ArgumentTypeError, match="comma-separated integers"):
            _levels_argument(",")

    def test_levels_are_deduplicated_and_sorted(self) -> None:
        """So a run's log line and its refusals spell the same set, however it
        was typed."""
        assert _levels_argument("1,0,1") == (0, 1)

    def test_widening_is_permitted(self) -> None:
        """The measurement `Q103` deferred and `P4-1` needs."""
        assert _levels_argument("0,1") == (0, 1)

    @staticmethod
    def _lattice(levels: list[int]) -> Lattice:
        """One two-cell cross-section per level, all road drawn, nothing standing.

        Small enough to write out, which is the point: the gate's population is
        decided by `survey`, and nothing else in this file can reach it without
        a shipped bundle.
        """
        n = len(levels) * 2
        return Lattice(
            edge=np.repeat(np.arange(len(levels), dtype=np.int32), 2),
            level=np.repeat(np.asarray(levels, dtype=np.int8), 2),
            station=np.repeat(np.arange(len(levels), dtype=np.int32), 2),
            x=np.zeros(n),
            z=np.zeros(n),
            span=np.full(n, 0.5),
            offset=np.tile([-0.25, 0.25], len(levels)),
            authored_half=np.full(n, 1.0),
            surface_y=np.zeros(n),
            spacing_m=1.0,
        )

    def test_an_off_grade_edge_gets_no_corridor_at_the_default(self) -> None:
        """The level-0 population the acceptance bars were written against."""
        found = survey(self._lattice([0, 1]), {})
        assert set(found.corridor_m) == {0}

    def test_the_level_is_recorded_where_the_population_is_decided(self) -> None:
        """🔴 `main` splits the gated rows from the reported ones off this, and
        it must not re-derive them from `graph["edges"]`: a second derivation of
        the same fact is free to drift from the one that chose the population,
        and it spells `elevation_level` in a second place."""
        found = survey(self._lattice([0, 1]), {}, corridor_levels=(0, 1))
        assert found.corridor_level == {0: 0, 1: 1}
        assert set(found.corridor_level) == set(found.corridor_m)

    def test_the_gated_population_is_invariant_under_widening(self) -> None:
        """🔴 **`Q19`'s report and the gate must read the same rows however wide
        the walk is.** Both select on level 0 out of `corridor_level`, so asking
        for more levels adds reported rows and moves no gated one. This is what
        `--levels 0,1 --corridor-report` printing `n 782` under a label reading
        "all judged level-0" looked like before it was filtered."""
        narrow = survey(self._lattice([0, 1]), {})
        wide = survey(self._lattice([0, 1]), {}, corridor_levels=(0, 1))
        gated = {
            edge: clear for edge, clear in wide.corridor_m.items() if wide.corridor_level[edge] == 0
        }
        assert gated == narrow.corridor_m

    def test_widening_admits_the_off_grade_edge(self) -> None:
        """🔴 **The mutation this exists for.** Reverting the gate to a bare
        `!= 0` leaves every counter closing and every other test passing, and
        the flag silently measures nothing — which is the shape `P4-1` would
        then plan against."""
        found = survey(self._lattice([0, 1]), {}, corridor_levels=(0, 1))
        assert set(found.corridor_m) == {0, 1}


class TestSplitByLevel:
    """🔴 **The one place a widened walk could reach the gate.**

    `--levels` is additive, so every level named beyond 0 adds rows to the
    listing — and exactly one line decides which of those rows the acceptance
    bars are then applied to. It lived inside `main` until the off-grade report
    was written, where nothing could reach it without a shipped bundle; the
    reason it is a function is that the mutations below all leave every counter
    closing and every other test in this file passing.

    ⚠️ These are about the **partition**, not about the widths. `survey` decides
    which edges get a corridor at all and `TestCorridorLevels` holds that; this
    decides which of the failures are `Q19`'s and which are `P4-1`'s.
    """

    # Sorted by clear width, the way `main` builds it.
    ROWS: ClassVar[list[tuple[int, float]]] = [
        (405, 1.46),
        (208, 2.33),
        (306, 2.42),
        (315, 2.44),
        (450, 2.98),
    ]
    LEVELS: ClassVar[dict[int, int]] = {405: 0, 208: 1, 306: 1, 315: 0, 450: 1}

    def test_the_split_is_disjoint_and_exhaustive(self) -> None:
        """Every failing row is judged exactly once. A row in both halves is
        counted against the gate *and* reported as exempt from it; a row in
        neither leaves the listing silently."""
        starved, off_grade = split_by_level(self.ROWS, self.LEVELS)
        assert not set(starved) & set(off_grade)
        assert sorted(starved + off_grade) == sorted(self.ROWS)

    def test_every_level_zero_row_is_gated(self) -> None:
        """🔴 **The direction that must never fail.** An off-grade row escaping
        into `starved` reads as a defect on a street that has none; a level-0
        row escaping into `off_grade` is a starved street the gate stops seeing,
        and that one ships."""
        starved, off_grade = split_by_level(self.ROWS, self.LEVELS)
        assert [edge for edge, _ in starved] == [405, 315]
        assert all(self.LEVELS[edge] != 0 for edge, _ in off_grade)

    def test_nothing_is_off_grade_at_the_default(self) -> None:
        """Which is what keeps the default run's output byte-identical: the
        report below returns immediately on an empty population, so the section
        cannot appear unless `--levels` asked for it."""
        rows = [row for row in self.ROWS if self.LEVELS[row[0]] == 0]
        starved, off_grade = split_by_level(rows, self.LEVELS)
        assert starved == rows
        assert off_grade == []

    def test_walk_order_is_preserved_in_both_halves(self) -> None:
        """Both listings are printed in the order `main` sorted them — tightest
        first — so a stable partition is what makes two dated runs diffable.
        `Q19`'s history is a record of readers diffing exactly that table."""
        starved, off_grade = split_by_level(self.ROWS, self.LEVELS)
        assert [clear for _, clear in starved] == sorted(clear for _, clear in starved)
        assert [edge for edge, _ in off_grade] == [208, 306, 450]

    def test_an_unknown_edge_raises_rather_than_being_gated(self) -> None:
        """⚠️ **The mutation this exists for**, and it is `.get(edge, 0)`.

        Written that way the lookup is total, so an edge whose level was never
        recorded defaults into the *gated* population and is scored against a
        bar it was never measured for — while the run reports one more starved
        edge and looks like a finding. Every key here was put in `corridor_m` by
        the same `close_station` that set the level, so a miss is an
        inconsistency to hear about.
        """
        with pytest.raises(KeyError):
            split_by_level([(999, 1.0)], self.LEVELS)

    def test_an_empty_listing_splits_into_two_empty_halves(self) -> None:
        """A region with nothing below the bar, which is the state the gate is
        trying to reach."""
        assert split_by_level([], self.LEVELS) == ([], [])


def _standing(
    bands: list[tuple[float, float]],
    *,
    cells: int = 10,
    judged: int = 10,
    occupier: str | None = "INFRASTRUCTURE",
    base_m: float = -0.2,
    top_m: float = 0.7,
) -> Standing:
    """One station's occupier reading, written out."""
    return Standing(
        cells=cells,
        judged=judged,
        occupier=occupier if bands else None,
        bands=tuple(bands),
        base_m=base_m if bands else float("nan"),
        top_m=top_m if bands else float("nan"),
    )


class TestBandExtent:
    """The heights behind `in_band`, and the two ways they could be over-read.

    `Q103` stopped at "the mechanism is not measured and is not guessed", having
    only plan columns to read; this is what added the vertical one. Its failure
    modes are silent in the way that matters — a probe that disagreed with the
    corridor half about *whether* a cell is occupied would diagnose a different
    city, and a bound read in the wrong direction would refute or confirm
    headroom on evidence that cannot carry it.
    """

    def test_band_extent_agrees_with_in_band(self) -> None:
        """🔴 **The one property that must hold, and the reason it is a test
        rather than a comment.** They are deliberately two queries — `in_band`
        is on the 1.1 M-call path and returns the moment it can — so nothing
        structural keeps them together. A probe naming an occupier the corridor
        half never saw is a diagnosis of a different bundle.
        """
        columns = [
            [],
            [0.0],
            [0.1, 0.2],
            [BUMPER_LOW_M],
            [BUMPER_HIGH_M],
            [1.0],
            [6.0, 30.0],
            [0.0, 0.1, 1.2, 8.0],
            [0.29, 2.01],
        ]
        for heights in columns:
            index = _occupied(heights) if heights else Occupied({}, 0, 0, 0)
            extent = index.band_extent(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)
            assert (extent is not None) == index.in_band(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)

    def test_it_returns_the_column_and_not_the_part_inside_the_band(self) -> None:
        """The two bounds that carry the reading, and only those.

        ⚠️ Where the surface sits *within* the band is clipped to the band by
        construction — `Q58`'s `drawn_gauge_m` trap in miniature — so it could
        never be a finding, and it is deliberately not returned. A wall running
        from the pavement to the roof would report the band's own edges, and
        reading that as the object's extent is the mistake. `base` at -1.6 m and
        `top` at 8.0 m are what say this is a wall standing on the deck rather
        than something hanging over it.
        """
        wall = _occupied([-1.6, 0.5, 1.0, 8.0])
        base, top = wall.band_extent(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)
        assert base == pytest.approx(-1.6)
        assert top == pytest.approx(8.0)

    def test_geometry_wholly_outside_the_band_reports_nothing_at_all(self) -> None:
        """🔴 **The mutation this exists for: returning the column anyway.**

        Written that way — `heights is None` as the only refusal — a cell holding
        nothing but a soffit 6 m up would hand back a base and a top, and the
        report would print a height range for a station with nothing standing in
        it. Read as headroom that is exactly backwards: the pruning in
        `index_corners` drops any triangle that misses the band, so what is
        returned here is never a survey of what is overhead. `None` is the only
        honest answer, and it is what keeps `top_m` a lower bound.
        """
        assert _occupied([6.0, 30.0]).band_extent(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M) is None
        assert _occupied([0.0, 0.1]).band_extent(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M) is None

    def test_an_empty_cell_is_clear_rather_than_an_error(self) -> None:
        assert _occupied([1.0]).band_extent(99.5, 99.5, BUMPER_LOW_M, BUMPER_HIGH_M) is None

    def test_it_uses_the_cell_the_heights_were_binned_at(self) -> None:
        """`TestPlanBin`'s property at the second query. A mismatch looks for
        walls where they were never filed, and every such lookup reads clear."""
        assert _occupied([1.0], 1.0).band_extent(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M)
        assert _occupied([1.0], 0.25).band_extent(0.5, 0.5, BUMPER_LOW_M, BUMPER_HIGH_M) is None


class TestCentrelineCoverage:
    """Whether an occupier reaches the middle — over the walk, not at one station.

    🔴 **This is what separates `Q103`'s 2-2 split into a measurement.** A
    parapet standing at the rims for a whole edge and a parapet the ribbon
    *crosses* need opposite fixes, and the binding station alone cannot tell
    them apart: `Centreline` reads one cross-section, and the crossing happens
    somewhere else along the edge.
    """

    def test_the_hull_of_two_rims_does_not_cover_the_centreline(self) -> None:
        """🔴 **The mutation this exists for, and it is the obvious way to write
        it.** Summarised as `min(offsets) .. max(offsets)`, a cross-section
        blocked at both rims and wide open down the middle spans the centreline
        and reads as standing on it — so `e257` and `e450` would report their
        every occupied station as a crossing, the 0 of 266 that makes them
        different from `e208` would vanish, and the population would stop being
        split at all.
        """
        assert not _covers_centreline(_standing([(-2.8, -1.9), (1.9, 2.8)]))

    def test_a_stretch_containing_the_centreline_covers_it(self) -> None:
        assert _covers_centreline(_standing([(-0.47, 0.47)]))

    def test_a_stretch_touching_the_centreline_covers_it(self) -> None:
        """Inclusive at both ends, on `TestInBand`'s rule: a surface exactly at
        the centreline is a surface the centreline meets."""
        assert _covers_centreline(_standing([(-0.93, 0.0)]))
        assert _covers_centreline(_standing([(0.0, 0.93)]))

    def test_a_clear_station_covers_nothing(self) -> None:
        assert not _covers_centreline(_standing([]))

    def test_the_approach_is_the_nearest_edge_of_the_nearest_stretch(self) -> None:
        walk = [_standing([(1.9, 2.8)]), _standing([(0.93, 1.87)]), _standing([(2.33, 2.8)])]
        assert _closest_approach(walk) == pytest.approx(0.93)

    def test_a_covered_centreline_approaches_to_zero(self) -> None:
        assert _closest_approach([_standing([(-0.47, 0.47)])]) == 0.0

    def test_an_edge_with_nothing_standing_on_it_has_no_distance(self) -> None:
        """⚠️ `inf`, never 0.0 — `Centreline.nearest`'s rule. The reading that
        matters most is the one at 0.00 m, so an absence must not manufacture
        it. The report prints a sentence there rather than a number."""
        assert _closest_approach([_standing([]), _standing([])]) == float("inf")
        assert _closest_approach([]) == float("inf")


class TestStandingRuns:
    """The run-length encoding, and the station accounting under it."""

    def test_stations_reading_alike_group(self) -> None:
        runs = _standing_runs([_standing([(1.9, 2.8)])] * 3)
        assert [count for _, count in runs] == [3]

    def test_a_moved_occupier_starts_a_new_run(self) -> None:
        """Which is the whole finding on `e208`: the stretch marches from one
        rim across the centreline, and a grouping that folded that away would
        print a single run and say nothing."""
        runs = _standing_runs([_standing([(1.9, 2.8)]), _standing([(0.93, 1.87)])])
        assert [count for _, count in runs] == [1, 1]

    def test_the_height_columns_do_not_split_runs(self) -> None:
        """⚠️ They drift by centimetres between neighbouring stations — the deck
        is not flat — so folding them into the key prints one line per station
        and buries the reading. Reduced over the run instead, worst either
        way."""
        runs = _standing_runs(
            [
                _standing([(1.9, 2.8)], base_m=-0.2, top_m=0.7),
                _standing([(1.9, 2.8)], base_m=-1.6, top_m=0.9),
            ]
        )
        assert len(runs) == 1
        assert runs[0][0].base_m == pytest.approx(-1.6)
        assert runs[0][0].top_m == pytest.approx(0.9)

    def test_a_clear_station_never_groups_with_an_occupied_one(self) -> None:
        """Which is what makes the plain `min`/`max` reduction safe: an
        unoccupied station carries NaN, `min(nan, x)` is whichever argument came
        first, and the two never meet because an empty `bands` cannot share a
        key with a non-empty one.

        ⚠️ **A guard on the reduction was written and removed.** `np.fmin`/`fmax`
        there could not be made to fail a test, because the mixed case is
        unreachable — and an unreachable guard reads as a hazard someone has
        handled. This is the property that actually holds it.
        """
        runs = _standing_runs([_standing([(1.9, 2.8)]), _standing([]), _standing([(1.9, 2.8)])])
        assert [station.occupier for station, _ in runs] == [
            "INFRASTRUCTURE",
            None,
            "INFRASTRUCTURE",
        ]
        assert np.isnan(runs[1][0].base_m)
        assert runs[0][0].base_m == pytest.approx(-0.2)

    def test_two_classes_at_the_same_offsets_are_two_runs(self) -> None:
        """🔴 **The mutation this exists for: dropping `occupier` from the key.**

        The offsets alone do not identify what is standing there. A station where
        a building takes over from a parapet at the same distance off the
        centreline would fold into the run above it and be reported as that run's
        class — a silent misattribution, on the one column that says which of
        `Q19`'s fix families an edge belongs to.

        ⚠️ It is the *bands* that keep a clear station out of an occupied run, so
        a test built from those two cannot see this: they differ whatever the key
        does.
        """
        runs = _standing_runs(
            [_standing([(1.9, 2.8)]), _standing([(1.9, 2.8)], occupier="BUILDING")]
        )
        assert [station.occupier for station, _ in runs] == ["INFRASTRUCTURE", "BUILDING"]

    def test_a_trimmed_station_is_not_a_clear_one(self) -> None:
        """🔴 **The rule is `_trimmed`, the corridor half's own guard.**

        The reader lines these rows up against the `profile` printed directly
        above them, and that list omits exactly the stations `survey` refused to
        judge. A weaker test here — "no road drawn at all" — calls a station
        judged that the profile skipped, and the two lists then differ in length
        with no row saying why: measured before they were shared, `e257` walked
        266 stations against the profile's 265. A trimmed station reading as
        clear is also the direction this tool must never flatter.
        """
        assert _standing([(1.9, 2.8)], cells=20, judged=1).trimmed
        assert not _standing([(1.9, 2.8)], cells=20, judged=20).trimmed
        runs = _standing_runs(
            [_standing([], cells=20, judged=20), _standing([], cells=20, judged=1)]
        )
        assert [station.trimmed for station, _ in runs] == [False, True]

    def test_a_station_exactly_at_the_bar_is_judged(self) -> None:
        """🔴 **The mutation this exists for: `<` becoming `<=` in `_trimmed`.**

        That rule is now called from both `survey.close_station` and
        `Standing.trimmed`, and the point of sharing it was that a flipped
        operator would otherwise drift between the profile and the probe. Only a
        station *at* the bar can see the flip — `18` of `20` cells at
        `_CORRIDOR_MEASURED` 0.90 is exactly 18.0 in floating point, so it is a
        reachable boundary and not an artefact. `_starved_shape`'s
        `test_the_bar_is_the_bar_the_gate_uses` is the same test one bar over.
        """
        assert not _standing([(1.9, 2.8)], cells=20, judged=18).trimmed
        assert _standing([(1.9, 2.8)], cells=20, judged=17).trimmed

    def test_a_run_keeps_the_trimmed_verdict_its_key_grouped_on(self) -> None:
        """🔴 **The mutation this exists for: reducing `cells` and `judged`
        across the run** — `max(cells)` beside `min(judged)`, which reads as the
        conservative choice and is not one.

        `trimmed` is a *ratio* over those two and it is in the key, so every
        member of a run already shares its verdict. Reducing them independently
        invents a third ratio belonging to no station: stations of 19/20 and
        24/25 — neither trimmed — merge to 19/25, which is, and the run then
        prints "not judged" over cross-sections that were judged. It also splits
        the run, because the next station no longer matches the head.
        """
        walk = [
            _standing([(1.9, 2.8)], cells=20, judged=19),
            _standing([(1.9, 2.8)], cells=25, judged=24),
            _standing([(1.9, 2.8)], cells=25, judged=24),
        ]
        assert [station.trimmed for station in walk] == [False, False, False]
        runs = _standing_runs(walk)
        assert [count for _, count in runs] == [3]
        assert not runs[0][0].trimmed


class TestEdgesArgument:
    """`--probe-edges`, whose failure would be a report that says nothing."""

    def test_both_spellings_are_accepted(self) -> None:
        """Half the listings here print `e208` and the graph's own field is
        `208`; a reader retyping one from the other should not have to know."""
        assert _edges_argument("e208,306") == (208, 306)

    def test_the_order_the_reader_chose_is_kept(self) -> None:
        """⚠️ Unlike `--levels`, which is a set. This is a listing, and sorting
        it would rearrange a comparison someone lined up deliberately."""
        assert _edges_argument("e450,e208,e306") == (450, 208, 306)

    def test_duplicates_collapse(self) -> None:
        assert _edges_argument("e208,e208") == (208,)

    def test_an_empty_argument_is_refused(self) -> None:
        """`_levels_argument`'s note applies: `"".split(",")` is `[""]`, so this
        is caught by the empty-piece guard inside the loop, and a post-loop
        check for an empty set would be unreachable. Pinned by message so the
        test cannot pass on the wrong branch."""
        with pytest.raises(argparse.ArgumentTypeError, match="comma-separated edge ids"):
            _edges_argument("")

    def test_something_that_is_not_an_edge_id_is_refused(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="write e208 or 208"):
            _edges_argument("FLEMING ROAD")
