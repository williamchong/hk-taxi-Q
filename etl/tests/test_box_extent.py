"""The box-junction extent grader (`tools/box_extent.py`, `P3-30`).

Only the parts whose failure mode is **silent**. The headline share checks
itself — the tool reproduced the shipped bundle's 38.75 m2 of off-road paint on
a reading arrived at independently — but nothing below it does.

Two things here are worth more than the rest:

🔴 **The three-way classification decides which of two opposite fixes owns a
defect.** `P3-31` closes a median void by making two ribbons meet; `P3-32` necks
or widens a ribbon that is genuinely narrower than the paint. A classifier that
quietly calls everything a void produces a plausible table and sends both tasks
to the wrong half of the problem. So the classes are checked over *every*
reachable ray pattern rather than on a happy path.

🔴 **The distance must not be confined to the classification radius.** That is
`Q58`'s `drawn_gauge_m` trap: a distribution bounded by the bar it is compared
against reports a clean sweep whatever the data does. The tool keeps two
separate values for exactly this reason, and a test is what stops them being
"simplified" back into one.

⚠️ **The mutation check here is a *ribbon* mutation, not a proof of
disjointness.** Disjointness is structural — the opposed-pair predicate is a
boolean over a set that is either empty or not — and
`test_the_three_classes_are_exhaustive_and_disjoint` is what establishes it. A
widened ribbon closes voids and kerb overhangs alike, so no config mutation can
separate the two axes; asserting otherwise would be a check whose passing state
is unreachable (`Q72`).
"""

from __future__ import annotations

import numpy as np
import pytest
from box_extent import (
    _RAYS,
    ISOLATED,
    ON_ROAD,
    PAST_KERB,
    VOID,
    SourceBox,
    attribute,
    classify,
    main,
    march,
    march_paint,
    outer_ring,
    survey,
)
from deck_error import Faces
from paint_clearance import twice_plan_area

# The tool's own defaults, so a failure says something about the shipped bars
# rather than about a fixture nobody reads.
RAY_M = 4.0
REACH_M = 10.0
STEP_M = 0.05


def road(*rectangles: tuple[float, float, float, float]) -> Faces:
    """A drawn carriageway made of axis-aligned slabs at y = 0."""
    corners: list[list[list[float]]] = []
    for x0, x1, z0, z1 in rectangles:
        corners.append([[x0, 0.0, z0], [x1, 0.0, z0], [x1, 0.0, z1]])
        corners.append([[x0, 0.0, z0], [x1, 0.0, z1], [x0, 0.0, z1]])
    return Faces.of(np.asarray(corners, dtype=np.float64), signed=False)


def paint(*centres: tuple[float, float], size: float = 0.2) -> np.ndarray:
    """Paint triangles whose centroids are exactly the given points.

    Exact because the tool judges a triangle at its centroid, so a fixture that
    only approximately centres one would make every boundary test fuzzy.
    """
    corners = [
        [[x - size, 0.02, z - size], [x + size, 0.02, z - size], [x, 0.02, z + 2.0 * size]]
        for x, z in centres
    ]
    return np.asarray(corners, dtype=np.float64)


def class_at(surface: Faces, x: float, z: float, *, ray_m: float = RAY_M) -> str:
    """March from a point and classify what surrounds it, at the shipped bars."""
    return classify(march(surface, x, z, reach_m=REACH_M, step_m=STEP_M), ray_m=ray_m)


def ring(half: float) -> np.ndarray:
    """A square published ring centred on the origin."""
    return np.asarray(
        [[-half, -half], [half, -half], [half, half], [-half, half]], dtype=np.float64
    )


def test_the_paint_fixture_centres_where_it_says_it_does():
    # The rest of this module reads centroids as positions, so the fixture that
    # produces them is checked before anything trusts it.
    corners = paint((3.0, -7.0))
    centroid = corners.mean(axis=1)[0]
    assert centroid[0] == pytest.approx(3.0)
    assert centroid[2] == pytest.approx(-7.0)


def test_the_three_classes_are_exhaustive_and_disjoint():
    """Every reachable ray pattern lands in exactly one class, by the stated rule.

    🔴 This is what disjointness rests on — not on a config mutation. Over all
    `2 ** _RAYS` patterns the class is `void` if and only if some opposed
    pair both hit, `isolated` if and only if nothing hit, and `past kerb`
    otherwise. There is no pattern that is two of those and none that is none.
    """
    half = _RAYS // 2
    for mask in range(1 << _RAYS):
        hits = [1.0 if mask >> ray & 1 else float("inf") for ray in range(_RAYS)]
        got = classify(hits, ray_m=RAY_M)
        assert got in (VOID, PAST_KERB, ISOLATED)
        opposed = any((mask >> ray & 1) and (mask >> (ray + half) & 1) for ray in range(half))
        if mask == 0:
            assert got == ISOLATED
        elif opposed:
            assert got == VOID
        else:
            assert got == PAST_KERB


def test_the_classification_reads_the_radius_and_not_the_reach():
    # A ray that found road at 6 m is not a neighbour at a 4 m bar, and is at 8.
    hits = [6.0] + [float("inf")] * 7
    assert classify(hits, ray_m=4.0) == ISOLATED
    assert classify(hits, ray_m=8.0) == PAST_KERB


def test_the_distance_is_measured_past_the_classification_radius():
    """🔴 `Q58`'s trap: the distance may not be confined to the bar it classifies at."""
    surface = road((10.0, 20.0, -5.0, 5.0))
    hits = march(surface, 4.0, 0.0, reach_m=REACH_M, step_m=STEP_M)
    assert classify(hits, ray_m=RAY_M) == ISOLATED
    # 6 m of clear ground, recorded despite classifying outside the 4 m radius.
    assert min(hits) == pytest.approx(6.0, abs=STEP_M)


def test_a_median_gap_reads_as_a_void():
    twin = road((-20.0, -1.0, -20.0, 20.0), (1.0, 20.0, -20.0, 20.0))
    assert class_at(twin, 0.0, 0.0) == VOID


def test_paint_past_a_single_kerb_does_not_read_as_a_void():
    one = road((1.0, 20.0, -20.0, 20.0))
    assert class_at(one, 0.0, 0.0) == PAST_KERB


def survey_of(corners: np.ndarray, surface: Faces, boxes: list[SourceBox], *, ray_m: float = RAY_M):
    marched = march_paint(corners, surface, boxes, reach_m=REACH_M, step_m=STEP_M)
    return survey(marched, boxes, [f"box {box.index}" for box in boxes], ray_m=ray_m)


def test_widening_the_ribbon_takes_paint_off_the_off_road_set():
    """A ribbon mutation moves paint onto the road — the fix `P3-32` is shaped like."""
    boxes = [SourceBox(index=0, ring=ring(5.0))]
    corners = paint((0.0, 0.0))
    narrow = survey_of(corners, road((2.0, 20.0, -20.0, 20.0)), boxes)
    wide = survey_of(corners, road((-2.0, 20.0, -20.0, 20.0)), boxes)
    assert narrow.rows[0].triangles[PAST_KERB] == 1
    assert narrow.off_m2 > 0.0
    assert wide.rows[0].triangles[ON_ROAD] == 1
    assert wide.off_m2 == 0.0


def test_the_radius_moves_the_split_but_never_the_off_road_total():
    """`--ray-m` is the rule's one free value: it may reclassify, never reclaim.

    The sweep would be meaningless if the radius could move the denominator —
    a row that fell could then be either the classification or the population,
    which is the ambiguity `Q72` rejected a divider test for.
    """
    boxes = [SourceBox(index=0, ring=ring(8.0))]
    corners = paint((0.0, 0.0))
    surface = road((-20.0, -6.0, -20.0, 20.0), (6.0, 20.0, -20.0, 20.0))
    tight = survey_of(corners, surface, boxes, ray_m=4.0)
    loose = survey_of(corners, surface, boxes, ray_m=8.0)
    assert tight.rows[0].triangles[ISOLATED] == 1
    assert loose.rows[0].triangles[VOID] == 1
    assert tight.off_m2 == pytest.approx(loose.off_m2)


def test_every_triangle_lands_in_exactly_one_class():
    """The partition the tool asserts, on geometry that reaches all four classes.

    ⚠️ The counts are asserted per class, not only as a sum. Summed alone the
    assertion passes whatever the classifier does, and the fixture this replaced
    put its third triangle *on* a slab — so it claimed to exercise four classes
    while producing two.
    """
    boxes = [SourceBox(index=0, ring=ring(30.0))]
    # On the left slab; between the two; past the right kerb; far from both.
    corners = paint((-10.0, 0.0), (0.0, 0.0), (22.0, 0.0), (0.0, 25.0))
    surface = road((-20.0, -1.0, -8.0, 8.0), (1.0, 20.0, -8.0, 8.0))
    report = survey_of(corners, surface, boxes)
    row = report.rows[0]
    assert row.triangles == {ON_ROAD: 1, VOID: 1, PAST_KERB: 1, ISOLATED: 1}
    assert report.placed + report.unattributed == len(corners)
    assert report.paint_m2 + report.unattributed_area_m2 == pytest.approx(
        0.5 * float(twice_plan_area(corners).sum())
    )


def test_a_triangle_outside_every_ring_is_unattributed_rather_than_pooled():
    """🔴 The counter that holds the attribution that replaced clustering.

    Placing a stray triangle in its nearest box would hide exactly the failure
    the source-polygon attribution exists to make visible.
    """
    boxes = [SourceBox(index=0, ring=ring(5.0))]
    corners = paint((0.0, 0.0), (100.0, 100.0))
    report = survey_of(corners, road((-20.0, 20.0, -20.0, 20.0)), boxes)
    assert report.unattributed == 1
    assert report.unattributed_area_m2 > 0.0
    assert sum(sum(row.triangles.values()) for row in report.rows) == 1


def test_a_point_two_rings_both_claim_is_placed_once():
    """The first-ring-wins tie-break, on rings that genuinely overlap.

    ⚠️ **Abutting axis-aligned rings do not test this.** `inside_polygon` is
    half-open, so a point on that kind of seam already falls in exactly one ring
    and the assertion passes with the tie-break deleted. Overlap is what makes
    the rule observable: placed twice it breaks the partition, and which box
    wins must depend on the order rather than on float luck.
    """
    first = SourceBox(index=0, ring=np.asarray([[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]]))
    second = SourceBox(index=1, ring=np.asarray([[2.0, 0.0], [9.0, 0.0], [9.0, 5.0], [2.0, 5.0]]))
    claimed_by_both = np.asarray([[3.0, 2.5]], dtype=np.float64)
    assert attribute(claimed_by_both, [first, second]).tolist() == [0]
    assert attribute(claimed_by_both, [second, first]).tolist() == [1]


def test_the_march_never_looks_past_its_own_reach():
    """🔴 A step that does not divide the reach must not extend it.

    Rounding rather than flooring marched to 10.2 m on a 10 m reach, and a
    one-step floor under it made the overshoot unbounded — a distance column
    that can exceed its stated reach is what the two separate bars exist to
    prevent.
    """
    # 🔴 The slab sits at 10.1 m — past a 10 m reach, and inside the 10.2 m that
    # rounding 10.0/0.6 up to 17 steps would reach. A fixture further out than
    # the overshoot passes under the bug as well as under the fix, and says
    # nothing.
    just_past = road((10.1, 30.0, -5.0, 5.0))
    hits = march(just_past, 0.0, 0.0, reach_m=10.0, step_m=0.6)
    assert all(not np.isfinite(hit) for hit in hits)


def test_a_step_that_cannot_march_is_refused():
    with pytest.raises(SystemExit, match="--step-m"):
        main(["--step-m", "0"])
    with pytest.raises(SystemExit, match="--step-m"):
        main(["--reach-m", "10", "--step-m", "11"])


def test_the_ring_drops_a_repeated_closing_vertex():
    closed = np.asarray([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]], dtype=np.float64)
    assert len(outer_ring(closed)) == 3


def test_a_ring_with_nothing_to_place_is_refused():
    assert outer_ring(np.asarray([[0.0, 0.0], [1.0, 0.0]], dtype=np.float64)) is None
    broken = np.asarray([[0.0, 0.0], [1.0, np.nan], [1.0, 1.0]], dtype=np.float64)
    assert outer_ring(broken) is None


def test_a_reach_under_the_classification_radius_is_refused():
    """The one configuration that makes the tool quietly wrong is refused loudly."""
    with pytest.raises(SystemExit, match="under --ray-m"):
        main(["--ray-m", "4.0", "--reach-m", "2.0"])
