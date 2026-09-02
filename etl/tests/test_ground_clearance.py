"""The `P3-10` ground probe (`tools/ground_clearance.py`).

Same standard as `test_deck_error.py` and `test_overhang.py`: only the parts
whose failure mode is **silent**. The headline shares check themselves against
the recorded table — 0.363% of sampled points and 3.289% of area at
`ground_sink_m: 0.20` — and a sink that stopped being applied reads 47%, which
nobody could miss. What would not announce itself is the arithmetic underneath.

Four rules carry this tool and all are tested here:

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
- 🔴 **The structure reader is not the ground reader, and both wrong versions of
  it delete the finding rather than corrupting it.** Terrain is single-valued
  wherever a car can be, so the ground takes the *nearest* height; structure is
  a volume in a stack, so it takes the **lowest face strictly above the road**.
  Read as nearest, a ledge is reported as the deck beneath the ribbon; read as
  highest, a ledge under a flyover is refused as overhead. Either way the table
  is clean and the wall is still there. `TestStructureReading` fixes both.

⚠️ What has **no unit test and would most want one**: the rule that a sampled
point is the first station of each segment. It lives inside `survey`, which
wants a whole shipped bundle, and splitting it out would move it away from the
loop that has the polyline in hand. `test_the_first_station_of_a_segment_is_its_vertex`
below pins the property of `walk_width` that the rule rests on, which is the
half that could change underneath it.

⚠️ **The section share's DENOMINATOR is in the same position.** `add_section`
divides the two numbers it is handed, and `TestStructureSections` pins that;
what decides them is `survey`'s loop, where `section_cells` counts a cell only
after the road lookup succeeds. Counted over the cells that found *structure*
instead, the region reads p50 0.83 against `Q19`'s 0.10 — so this is the rule
worth knowing is unreached, not the arithmetic that is.

⚠️ **The two classes never share an assertion here either.** `Q57` is what
pooling them would cost, and a test that accepted either population would be
the first place the separation stopped being real.
"""

from __future__ import annotations

import numpy as np
import pytest
from deck_error import Faces
from ground_clearance import (
    SUSPENSION_TRAVEL_M,
    Step,
    Structure,
    Survey,
    ground_above,
    structure_above,
)
from overhang import walk_width

from pipeline.clearance import BUMPER_LOW_M


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


class _Slabs:
    """Synthetic upward-wound geometry, so the readers are testable without a bundle.

    🔴 **The winding is asserted rather than trusted.** `Faces.of(signed=True)`
    keeps only faces wound upward, which is the filter that makes a deck's top a
    candidate and its soffit not one — so a helper that quietly built downward
    quads would hand every test below an empty index and every one of them would
    pass by finding nothing.
    """

    HALF_M = 5.0

    @classmethod
    def at(cls, *heights: float) -> Faces:
        corners = []
        for height in heights:
            low, high = -cls.HALF_M, cls.HALF_M
            corners.append([[low, height, low], [low, height, high], [high, height, high]])
            corners.append([[low, height, low], [high, height, high], [high, height, low]])
        # Reshaped rather than passed bare, so the no-structure case — which is
        # 92.8% of the region and has to be testable — arrives as an empty
        # `(0, 3, 3)` rather than as an empty 1-D array.
        faces = Faces.of(np.asarray(corners, dtype=np.float64).reshape(-1, 3, 3), signed=True)
        assert len(faces.corners) == 2 * len(heights), "a slab was wound downward"
        return faces


class TestStructureReading:
    """`structure_above`, the one rule that could NOT be borrowed from the ground.

    Terrain is single-valued wherever a car can be, so `ground_above` takes the
    *nearest* height within a symmetric window and is right to. Structure is a
    volume in a stack: `Faces.from_tiles` keeps upward-wound faces, so a
    flyover's **deck top** is a candidate for the street running underneath it.
    Read the terrain way, this region's interchange reports structure standing
    **+13.27 m proud** of GLOUCESTER ROAD, across 210 of 737 edges.

    Every test here fixes one half of "the lowest face strictly above the road,
    or nothing". Both wrong rules — nearest, and highest — are reachable by a
    one-word edit and neither announces itself: nearest reports a ledge as the
    deck beneath the road, highest reports it as a flyover overhead. Both delete
    the finding rather than corrupting it, which is why they need a test each.
    """

    def test_a_step_inside_the_window_is_measured(self) -> None:
        step = structure_above(_Slabs.at(0.25), 0.0, 0.0, 0.0, 2.0)
        assert step.rise_m == pytest.approx(0.25)
        assert step.overhead_m is None
        assert step.has_structure

    def test_a_deck_overhead_is_refused_and_published_rather_than_dropped(self) -> None:
        """`Probe.above_window_m` at a second layer, and for its reason.

        A flyover 6 m over a street is not a step in it. Refusing it silently
        would be honest about the band and dishonest about the tool: every
        `worst_m` in the report is a lower bound, and the refused population is
        what says by how much.
        """
        step = structure_above(_Slabs.at(6.0), 0.0, 0.0, 0.0, 2.0)
        assert step.rise_m is None
        assert step.overhead_m == pytest.approx(6.0)
        assert step.has_structure

    def test_the_lowest_face_above_the_road_is_the_step_not_the_nearest_one(self) -> None:
        """The terrain rule, applied here, reports the deck the road rests on.

        A ribbon sitting 0.05 m proud of its own deck with a 0.25 m ledge beside
        it: nearest picks the deck 0.05 m *below* the road, which is not a step
        at all, and the ledge — the thing that stops the car — is never seen.
        """
        step = structure_above(_Slabs.at(-0.05, 0.25), 0.0, 0.0, 0.0, 2.0)
        assert step.rise_m == pytest.approx(0.25)

    def test_a_ledge_under_a_flyover_is_not_hidden_by_the_deck_over_it(self) -> None:
        """The other wrong rule, and the one that would be found last.

        Taking the highest face reads the deck 6 m up, refuses it as overhead,
        and books the cell as a refusal — so a ledge in the carriageway
        disappears *because* there is a flyover above it. This region's band is
        dominated by WAN CHAI INTERCHANGE, which is exactly where that happens.
        """
        step = structure_above(_Slabs.at(0.25, 6.0), 0.0, 0.0, 0.0, 2.0)
        assert step.rise_m == pytest.approx(0.25)
        assert step.overhead_m is None

    def test_structure_at_or_below_the_road_is_resting_and_not_a_step(self) -> None:
        """The deck the ribbon sits on. Geometry working, and deliberately not a
        miss — counting it as one would make the coverage of a correctly built
        flyover approach look like a hole in the tiles."""
        step = structure_above(_Slabs.at(-0.40, 0.0), 0.0, 0.0, 0.0, 2.0)
        assert step.rise_m is None
        assert step.overhead_m is None
        assert step.has_structure

    def test_no_structure_at_all_is_absent_and_is_the_normal_answer(self) -> None:
        """92.8% of this region's level-0 carriageway. A coverage gate over this
        population would fail the tool on a fact, which is why there is none."""
        step = structure_above(_Slabs.at(), 0.0, 0.0, 0.0, 2.0)
        assert step == Step(None, None, False)

    def test_a_face_exactly_at_the_window_is_a_step_rather_than_overhead(self) -> None:
        """Inclusive at the bound, as every other threshold in this file is."""
        assert structure_above(_Slabs.at(2.0), 0.0, 0.0, 0.0, 2.0).rise_m == pytest.approx(2.0)
        assert structure_above(_Slabs.at(2.0), 0.0, 0.0, 0.0, 1.99).rise_m is None

    def test_the_rise_is_measured_from_the_road_and_not_from_zero(self) -> None:
        """The road height arrives as a value because two readers want it, and
        an argument that is ignored is the failure this pins: a slab 4.25 m up
        over a road 4.00 m up is a 0.25 m step, not a 4.25 m one."""
        assert structure_above(_Slabs.at(4.25), 0.0, 0.0, 4.0, 2.0).rise_m == pytest.approx(0.25)


class TestGroundReading:
    """`ground_above`, unchanged in rule and newly reachable without a bundle.

    It was a closure inside `survey` and so could only be exercised by building
    a whole region — the same complaint this file's header makes about the
    sampled-point rule. Lifting it out to give the structure reader the road
    height once is what made these testable.
    """

    def test_the_nearest_terrain_is_taken_and_not_the_highest(self) -> None:
        """`deck_error.nearest`'s rule. Highest would attribute the top of a sea
        wall or a cutting face to the road running below it, and report several
        metres of proud where the geometry is right."""
        probe = ground_above(_Slabs.at(-0.20, 2.60), 0.0, 0.0, 0.0, 3.0)
        assert probe.proud_m == pytest.approx(-0.20)

    def test_terrain_past_the_window_is_published_rather_than_counted_as_missing(self) -> None:
        """`Q24`'s amendment, pinned: 121 cells with terrain 3.07-7.65 m above
        the carriageway were reported as coverage misses — the region's deepest
        burials leaving the numerator, which is `deck_error`'s fourth defect
        inverted."""
        probe = ground_above(_Slabs.at(5.00), 0.0, 0.0, 0.0, 3.0)
        assert probe.proud_m is None
        assert probe.above_window_m == pytest.approx(5.00)
        assert probe.has_terrain

    def test_no_terrain_is_told_apart_from_terrain_out_of_the_window(self) -> None:
        """The two rejections `Survey.no_ground` sums, and they are opposite
        findings: a hole in the tiles against a burial this declines to
        attribute."""
        probe = ground_above(_Slabs.at(), 0.0, 0.0, 0.0, 3.0)
        assert probe.above_window_m is None
        assert not probe.has_terrain


class TestStructureBands:
    """Where a rise lands, which is the whole claim this half publishes."""

    def _standing(self) -> Structure:
        """A `Structure` with one edge begun — named for what it returns."""
        standing = Structure()
        standing.begin(4, "TEST ROAD")
        return standing

    def test_the_band_is_bounded_by_the_car_below_and_the_other_instrument_above(self) -> None:
        """🔴 Both bounds are imported, not chosen. `SUSPENSION_TRAVEL_M` is what
        throws the car; `BUMPER_LOW_M` is where `clearance.py` starts looking.
        The gap between them is the entire finding, so an off-by-one at either
        end publishes a band that is not the blind one."""
        standing = self._standing()
        for rise in (SUSPENSION_TRAVEL_M, 0.19, BUMPER_LOW_M, 0.31):
            standing.add(4, rise, 1.0)

        edge = standing.edges[4]
        # 0.18 exactly is not over the car's travel — exclusive, as
        # `area_share_above` and `EdgeCells` are, and for the same reason.
        assert edge.band_m2 == pytest.approx(2.0)
        assert edge.over_bumper_m2 == pytest.approx(1.0)

    def test_the_band_and_the_bumper_bucket_never_hold_the_same_cell(self) -> None:
        """They are reported side by side and must never be summed — anything
        past `BUMPER_LOW_M` is already `carriageway_occupancy`'s population, so
        a cell in both would republish `Q19`'s own count as this tool's find.

        🔴 **Asserted against the area that went IN, never against a derived
        total.** This test used to read `stepped_m2 == band_m2 + over_bumper_m2`
        against a property defined as that sum — `Q72`'s tautology, in the file
        that cites `Q72` twice, and it passed for an `add` that booked every
        cell into both buckets. Six square metres entered; six must come out,
        split one way.
        """
        standing = self._standing()
        for rise in (0.25, 0.90, 1.90):
            standing.add(4, rise, 2.0)
        edge = standing.edges[4]
        assert edge.band_m2 + edge.over_bumper_m2 == pytest.approx(6.0)
        assert edge.band_m2 == pytest.approx(2.0)
        assert edge.over_bumper_m2 == pytest.approx(4.0)

    def test_the_edge_share_is_over_the_ribbon_and_not_over_the_cells_with_structure(self) -> None:
        """🔴 The tautology this denominator exists to refuse.

        Structure is absent under 92.8% of the region's carriageway. Divided by
        the cells that *found* some, an edge carrying one ledge and 400 m² of
        clean road reads **100%** — a table of maximal shares that says nothing
        about how much of any street is obstructed.
        """
        standing = self._standing()
        standing.edges[4].ribbon_m2 = 100.0
        standing.add(4, 0.25, 5.0)
        assert standing.edges[4].band_share == pytest.approx(0.05)

    def test_the_worst_rise_per_edge_is_the_highest_not_the_last(self) -> None:
        standing = self._standing()
        for rise in (1.40, 0.20, 0.30):
            standing.add(4, rise, 1.0)
        assert standing.edges[4].worst_m == pytest.approx(1.40)

    def test_the_band_counts_come_from_the_same_pass_as_the_cells(self) -> None:
        """`cells_in` reports cells, area and edges together, so the three
        cannot describe different populations of the same band."""
        standing = Structure()
        for edge_id in (4, 5):
            standing.begin(edge_id, "TEST ROAD")
            standing.add(edge_id, 0.25, 3.0)
        standing.add(5, 1.00, 3.0)

        assert standing.cells_in(SUSPENSION_TRAVEL_M, BUMPER_LOW_M) == (2, pytest.approx(6.0), 2)
        assert standing.cells_in(BUMPER_LOW_M, 2.0) == (1, pytest.approx(3.0), 1)


class TestStructurePartition:
    """`Structure.observe` and the `check` that grades it.

    🔴 **The decode is exercised here, not hand-set fields.** These tests set
    `on_road` through `saw_road_cell` and the buckets through `observe`, so
    `check` compares two things the class counted — which is the whole
    difference between an invariant and a caller graded against itself. Written
    the other way first, the identity held while two per-edge counters were
    write-only and no test could reach the branch that wrote them.
    """

    def _one_cell(self, standing: Structure, step: Step) -> bool:
        standing.saw_road_cell(6, 1.0)
        return standing.observe(6, step, 1.0)

    def test_every_outcome_books_exactly_one_bucket(self) -> None:
        """All four `Step` shapes through the real decode, then the identity."""
        standing = Structure()
        standing.begin(6, "TEST ROAD")
        for step in (
            Step(0.25, None, True),
            Step(1.50, None, True),
            Step(None, 4.0, True),
            Step(None, None, True),
            Step(None, None, False),
        ):
            self._one_cell(standing, step)

        assert standing.on_road == 5
        assert (standing.measured, standing.overhead, standing.resting, standing.absent) == (
            2,
            1,
            1,
            1,
        )
        standing.check()

    def test_only_a_step_past_the_cars_travel_counts_toward_a_section(self) -> None:
        """`observe`'s return is the section numerator, so the threshold stays
        in the class with the other two rather than being applied again at the
        call site — where a drifting copy would change the discriminator
        without changing any band."""
        standing = Structure()
        standing.begin(6, "TEST ROAD")
        assert self._one_cell(standing, Step(0.25, None, True)) is True
        assert self._one_cell(standing, Step(SUSPENSION_TRAVEL_M, None, True)) is False
        assert self._one_cell(standing, Step(None, 4.0, True)) is False
        assert self._one_cell(standing, Step(None, None, False)) is False

    def test_a_refused_overhead_is_recorded_on_its_edge_and_not_only_pooled(self) -> None:
        """The per-edge pair the report prints as `over window`, which is what
        makes that edge's `worst` an honest bound. Both were written and never
        read until review; a counter nobody prints is the refusal this class's
        docstring says it must not be."""
        standing = Structure()
        standing.begin(6, "TEST ROAD")
        # ⚠️ **Nearest LAST, deliberately.** Ordered the other way this passes
        # for `overhead_min_m = step.overhead_m`, which keeps whichever face
        # came last rather than the closest one — and the closest is the whole
        # point, being the nearest thing to a step that was refused.
        self._one_cell(standing, Step(None, 4.0, True))
        self._one_cell(standing, Step(None, 9.0, True))

        assert standing.overhead_m == [4.0, 9.0]
        assert standing.edges[6].overhead == 2
        assert standing.edges[6].overhead_min_m == pytest.approx(4.0)

    def test_an_outcome_that_stopped_being_counted_is_refused(self) -> None:
        """⚠️ Mutation-checked rather than read, which is `Q72`'s rule for a
        counter: the test of one is not that it reads clean but that a reachable
        state makes it fire. A fifth outcome added without a bucket would
        otherwise leave every share divided by a total that no longer describes
        its own parts."""
        standing = Structure()
        standing.on_road = 3
        standing.absent = 2
        with pytest.raises(AssertionError, match="do not partition"):
            standing.check()


class TestStructureSections:
    """`Q19`'s discriminator: a ledge takes a strip of a cross-section, a ribbon
    disagreeing with the deck it rests on takes most of one. It is what tells
    the two failure modes apart, and they do not share a fix."""

    def test_the_share_is_over_the_cells_with_a_road_not_the_cells_with_structure(self) -> None:
        """🔴 The denominator that a scratch run of this got wrong.

        Counted over the cells that found structure, the region read p50 **0.83**
        where `Q19` reads 0.10 — because a thin ledge is most of the structure in
        its own section and almost none of the road. The shipped reading is p50
        14%, which is `Q19`'s shape.
        """
        standing = Structure()
        standing.begin(8, "TEST ROAD")
        standing.add_section(8, stepped=2, cells=20)
        assert standing.section_share == [pytest.approx(0.10)]

    def test_a_clean_section_records_no_share_but_still_counts_as_a_station(self) -> None:
        """`Q19`'s conditioning, kept so the two distributions are comparable:
        the question is what shape a defect takes, and a clean section has no
        shape. Including them would drive any percentile to zero and make the
        two modes indistinguishable.

        ⚠️ **It must still reach `stations`**, which is the denominator of the
        table's `stepped/measured` column — dropped there, an edge stepped at
        every one of its five sections would read `5/5` whether it has five
        sections or five hundred.
        """
        standing = Structure()
        standing.begin(8, "TEST ROAD")
        standing.add_section(8, stepped=0, cells=20)
        assert standing.section_share == []
        assert standing.edges[8].stepped_stations == 0
        assert standing.edges[8].stations == 1

    def test_the_worst_section_on_an_edge_is_kept_not_the_last(self) -> None:
        """The per-edge half of `Q19`'s discriminator: it says which failure
        mode an edge has, and a milder later section must not overwrite it."""
        standing = Structure()
        standing.begin(8, "TEST ROAD")
        standing.add_section(8, stepped=16, cells=20)
        standing.add_section(8, stepped=2, cells=20)
        assert standing.edges[8].worst_section_share == pytest.approx(0.80)
        assert standing.edges[8].stepped_stations == 2
        assert standing.edges[8].stations == 2

    def test_a_section_with_no_measurable_cell_is_not_a_division(self) -> None:
        standing = Structure()
        standing.begin(8, "TEST ROAD")
        standing.add_section(8, stepped=0, cells=0)
        assert standing.section_share == []
        assert standing.edges[8].stations == 0
