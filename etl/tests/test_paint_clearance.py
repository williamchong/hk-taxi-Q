"""The paint-height grader (`tools/paint_clearance.py`, `Q92`).

Only the parts whose failure mode is **silent**. The headline shares check
themselves — the tool reproduced the shipped bundle's 23.2% before the fix and
12.8% after it, on numbers arrived at independently — but the classifier that
splits a burial into "on a kerb" and "in the carriageway" does not. It decides
which population the exit code rides on, and a classifier that quietly calls
everything a kerb produces a passing table with the defect still in it.

`deck_error.py`'s test makes the same argument about its colour filter, and for
the same reason: a plausible-looking table is the failure to guard against.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from deck_error import Faces
from paint_clearance import Bars, LayerVerdict, on_raised_edge, survey, twice_plan_area

# The kerb the classifier has to recognise: `hong_kong.yaml`'s `kerb_height_m`.
# ⚠️ **Copied rather than read through the city fixture, deliberately.** These
# test the *arithmetic*, and the tool itself refuses to read the pipeline's
# number — taking it here would undo that in the one place it is checked.
KERB_RISE_M = 0.15

# The tool's own defaults, so a test that fails says something about the shipped
# bars rather than about a fixture nobody reads.
BARS = Bars(road_within_m=1.5, kerb_probe_m=1.0, kerb_step_m=0.10, accept_depth_m=0.010)


def quad(x0: float, z0: float, x1: float, z1: float, y: float) -> np.ndarray:
    """Two triangles covering a plan rectangle at one height, as `(2, 3, 3)`."""
    corners = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    return np.array([[corners[0], corners[1], corners[2]], [corners[0], corners[2], corners[3]]])


def street(lip_m: float = 0.6) -> Faces:
    """A carriageway at y=0 with a kerb top standing `KERB_RISE_M` above it.

    ⚠️ **The kerb is a narrow strip and nothing lies beyond it**, which is what
    `roads.glb` actually holds: the lip is 0.5 m over a 0.15 m riser and the
    pavement is not road. A fixture with metres of kerb would make the
    classifier look broken when it is the probe radius that is the point.
    """
    return Faces.of(
        np.concatenate(
            [
                quad(-10.0, -10.0, 3.0, 10.0, 0.0),
                quad(3.0, -10.0, 3.0 + lip_m, 10.0, KERB_RISE_M),
            ]
        ),
        signed=False,
    )


class TestTheRaisedEdgeClassifier:
    """🔴 The split the exit code rides on.

    A marking under a **kerb top** reached past the drawn ribbon — registration,
    which `Q54` refuses to fix by scaling a surveyed extent. A marking under the
    **carriageway** is at the wrong height on the road it is drawn on, which is
    a defect with a fix. Pooling them leaves nothing to do but raise the bar.
    """

    def test_a_kerb_top_is_a_raised_edge(self) -> None:
        road = street()
        assert on_raised_edge(road, 3.3, 0.0, KERB_RISE_M, BARS)

    def test_the_open_carriageway_is_not(self) -> None:
        """The mirror, and the half that matters: called an edge, a burial in
        the middle of the road stops being counted at all."""
        road = street()
        assert not on_raised_edge(road, -5.0, 0.0, 0.0, BARS)

    def test_a_step_shallower_than_the_bar_is_not_an_edge(self) -> None:
        """⚠️ A ribbon's own mitre and trim interpolation move it centimetres
        within a metre, and that must not read as a kerb."""
        road = Faces.of(
            np.concatenate(
                [quad(-10.0, -10.0, 0.0, 10.0, 0.0), quad(0.0, -10.0, 10.0, 10.0, 0.02)]
            ),
            signed=False,
        )
        assert not on_raised_edge(road, 3.0, 0.0, 0.02, BARS)

    def test_the_probe_radius_is_what_the_classifier_can_see(self) -> None:
        """⚠️ **The limitation, pinned rather than assumed away.** The classifier
        asks the neighbourhood, so a raised strip wider than its radius has no
        carriageway within reach and reads as carriageway itself — which is the
        safe direction, because it charges the burial to the gated population
        rather than excusing it. A real kerb is 0.5 m of lip and the default
        radius is a metre, so this is a bound on a second region, not on this
        one.
        """
        broad = street(lip_m=3.0)
        assert not on_raised_edge(broad, 4.5, 0.0, KERB_RISE_M, BARS)
        assert on_raised_edge(broad, 4.5, 0.0, KERB_RISE_M, replace(BARS, kerb_probe_m=2.0))


class TestTheSurvey:
    """What the per-layer verdict counts, and what it refuses to drop."""

    def test_paint_above_the_road_is_not_buried(self) -> None:
        road = street()
        verdict = survey(
            quad(-5.0, -1.0, -1.0, 1.0, 0.012),
            road,
            key="boxjunctions",
            name="test",
            bars=BARS,
        )
        assert verdict.judged == 2
        assert verdict.under_highest == 0
        assert verdict.under_lowest == 0
        assert verdict.deep_in_carriageway == 0

    def test_paint_under_the_carriageway_is_counted_and_classified(self) -> None:
        road = street()
        verdict = survey(
            quad(-5.0, -1.0, -1.0, 1.0, -0.05),
            road,
            key="boxjunctions",
            name="test",
            bars=BARS,
        )
        assert verdict.under_lowest == 2
        assert verdict.on_raised_edge == 0
        assert verdict.in_carriageway == 2
        assert verdict.deep_in_carriageway == 2
        assert verdict.depth_in_carriageway_m == pytest.approx([0.05, 0.05])

    def test_paint_under_a_kerb_top_is_not_charged_to_the_carriageway(self) -> None:
        """The 193 box triangles this separates out on the shipped region: the
        box's surveyed extent reaches past the drawn ribbon onto the kerb, which
        is not a height defect and has no height fix."""
        road = street()
        verdict = survey(
            quad(3.1, -1.0, 3.5, 1.0, 0.012),
            road,
            key="boxjunctions",
            name="test",
            bars=BARS,
        )
        assert verdict.under_lowest == 2
        assert verdict.on_raised_edge == 2
        assert verdict.in_carriageway == 0

    def test_a_shallow_burial_is_the_chord_residue_and_not_gated(self) -> None:
        """⚠️ Paint is a flat triangle over a road that creases, so its chord
        dips below the crown it spans by millimetres however right its vertices
        are. Counted, and kept out of the gated population."""
        road = street()
        verdict = survey(
            quad(-5.0, -1.0, -1.0, 1.0, -0.004),
            road,
            key="boxjunctions",
            name="test",
            bars=BARS,
        )
        assert verdict.in_carriageway == 2
        assert verdict.deep_in_carriageway == 0

    def test_paint_over_no_road_is_counted_rather_than_dropped(self) -> None:
        """🔴 The denominator trap `ground_clearance.Survey` was split up to
        end. Dropped silently, paint drawn off the road flatters every share
        here — and a layer that had come adrift entirely would score perfectly.
        """
        road = street()
        verdict = survey(
            quad(40.0, 40.0, 44.0, 44.0, 0.0),
            road,
            key="boxjunctions",
            name="test",
            bars=BARS,
        )
        assert verdict.triangles == 2
        assert verdict.judged == 0
        assert verdict.no_road == 2
        assert verdict.coverage == 0.0

    def test_a_deck_overhead_is_not_the_road_this_paint_is_on(self) -> None:
        """⚠️ `ground_clearance.py`'s 'level 0 only', in the one form available
        on a layer that publishes no level. Without the window every marking
        under a flyover reports the height of the bridge as a burial."""
        road = Faces.of(
            np.concatenate(
                [quad(-10.0, -10.0, 10.0, 10.0, 0.0), quad(-10.0, -10.0, 10.0, 10.0, 9.0)]
            ),
            signed=False,
        )
        verdict = survey(
            quad(-5.0, -1.0, -1.0, 1.0, 0.012),
            road,
            key="boxjunctions",
            name="test",
            bars=BARS,
        )
        assert verdict.judged == 2
        assert verdict.under_highest == 0

    def test_the_two_burial_counts_partition(self) -> None:
        """`under_lowest == on_raised_edge + in_carriageway`, on a layer holding
        one of each. Asserted rather than assumed, because the report prints all
        three and a reader is entitled to add them up."""
        road = street()
        corners = np.concatenate(
            [
                quad(-5.0, -1.0, -1.0, 1.0, -0.05),  # under the carriageway
                quad(3.1, -1.0, 3.5, 1.0, 0.012),  # under the kerb top
                quad(-5.0, 4.0, -1.0, 6.0, 0.5),  # clear of both
            ]
        )
        verdict = survey(
            corners,
            road,
            key="boxjunctions",
            name="test",
            bars=BARS,
        )
        assert verdict.under_lowest == verdict.on_raised_edge + verdict.in_carriageway
        assert (verdict.on_raised_edge, verdict.in_carriageway) == (2, 2)


class TestPlanArea:
    """Area is reported beside the counts because the two can disagree, and
    neither is derived from the other."""

    def test_a_unit_square_is_two_half_squares(self) -> None:
        assert twice_plan_area(quad(0.0, 0.0, 1.0, 1.0, 0.0)) == pytest.approx([1.0, 1.0])

    def test_a_marking_on_a_grade_covers_its_plan_area_and_no_more(self) -> None:
        """Plan rather than true area: a bar on a 5% grade is not 0.1% more
        paint on the street."""
        flat = quad(0.0, 0.0, 2.0, 1.0, 0.0)
        sloped = flat.copy()
        sloped[:, :, 1] = sloped[:, :, 0] * 0.05
        assert twice_plan_area(sloped) == pytest.approx(twice_plan_area(flat))


class TestTheVerdictShares:
    def test_an_empty_layer_divides_by_nothing(self) -> None:
        """A layer a region publishes none of must report zero rather than
        raise — `signals` is `null` today and a second region will have more."""
        verdict = LayerVerdict(key="roadmarks", name="test")
        assert verdict.share(verdict.under_highest) == 0.0
        assert verdict.share(verdict.in_carriageway) == 0.0
        assert verdict.area_share(verdict.under_highest_area_m2) == 0.0
        assert verdict.coverage == 0.0
