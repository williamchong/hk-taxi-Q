"""The `Q34′` weight derivation (`tools/ring_weights.py`).

Only the parts whose failure is **silent**, which is the whole tool: it emits
numbers a human pastes into `hong_kong.yaml`, so a proposal that is subtly wrong
looks exactly like one that is right, and the city ships it. Two of these are
guarding against a plausible-looking answer rather than against a crash.

The population it derives against needs the 4.9 GB survey and is therefore not
here. What is here is everything downstream of the population: the binning, the
weights coming back out of a draw, and the solve.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from ring_weights import bins, expected, ramp_class, rederive, weights_of

from pipeline.config import Material, WeightedDraw

# Three materials spanning the shipped facade palette's range, and the shipped
# neutral ring's weights over them. Real numbers so the assertions below are
# about a solve that has to work on this city, not on a convenient one.
DARK = Material(name="panel_grey", colour=(142, 147, 147), reflectance=55.2, source="test")
MID = Material(name="render_cool", colour=(148, 153, 149), reflectance=60.1, source="test")
LIGHT = Material(name="tile_neutral", colour=(154, 154, 144), reflectance=61.5, source="test")
REFLECTANCE = {material.name: material.reflectance for material in (DARK, MID, LIGHT)}
SHIPPED = {DARK.name: 0.50, MID.name: 0.30, LIGHT.name: 0.20}


class TestBins:
    """Enumerating what `draw_for` can return, which is how rows are counted."""

    def test_every_reachable_draw_is_enumerated(self, hong_kong) -> None:
        """The silent failure this guards is a row landing in no bin at all, or
        — worse — in the wrong one because two bins compared equal. The tool bins
        by identity for that reason, so the enumeration has to be complete by
        identity too."""
        assignment = hong_kong.buildings.material_assignment
        known = [found.draw for found in bins(assignment)]
        for chroma in (0.0, 2.5, 5.0, 5.01, 12.0, 40.0):
            for hue_deg in range(0, 360, 5):
                drawn = assignment.draw_for(chroma, float(hue_deg))
                assert drawn is not None, "the last ring is .inf and answers everything"
                assert any(drawn is candidate for candidate in known)

    def test_bins_are_distinctly_labelled(self, hong_kong) -> None:
        """The labels key the population counts. Two bins sharing one would
        merge their populations and average their targets."""
        labels = [found.label for found in bins(hong_kong.buildings.material_assignment)]
        assert len(set(labels)) == len(labels)


class TestWeightsOf:
    """Recovering authored weights from the cumulative table a draw keeps."""

    def test_it_round_trips_the_authored_weights(self) -> None:
        drawn = WeightedDraw.of({DARK: 0.50, MID: 0.30, LIGHT: 0.20}, "test")
        assert weights_of(drawn) == pytest.approx(SHIPPED)

    def test_a_weight_follows_its_material_and_not_its_position(self) -> None:
        """`WeightedDraw` sorts by material name, so authored order and stored
        order differ. Reading the differences off positionally would return a
        valid-looking distribution with the weights on the wrong materials."""
        drawn = WeightedDraw.of({LIGHT: 0.7, DARK: 0.2, MID: 0.1}, "test")
        assert weights_of(drawn) == pytest.approx({LIGHT.name: 0.7, DARK.name: 0.2, MID.name: 0.1})


class TestRederive:
    """The solve, and the two properties the config loader will reject without."""

    def test_it_lands_on_the_target(self) -> None:
        moved = rederive(SHIPPED, REFLECTANCE, 57.58)
        assert expected(moved, REFLECTANCE) == pytest.approx(57.58, abs=0.1)

    def test_the_proposal_sums_to_one(self) -> None:
        """Rounding three weights to two places breaks the sum, and
        `WeightedDraw.build` refuses a table that does not sum to 1.0 — it does
        not normalise. A proposal that misses is one nobody can paste."""
        for target in (55.5, 56.4, 57.58, 58.0, 60.9):
            moved = rederive(SHIPPED, REFLECTANCE, target)
            assert sum(moved.values()) == pytest.approx(1.0, abs=1e-9)

    def test_it_moves_as_little_as_it_can(self) -> None:
        """The rule that fixes the free degree of freedom. Two constraints over
        three materials leave a line of solutions, and any point on it hits the
        target — so the target alone cannot catch a solve that threw the authored
        distribution away and re-derived it from nothing."""
        moved = rederive(SHIPPED, REFLECTANCE, 57.58)
        assert max(moved, key=moved.get) == max(SHIPPED, key=SHIPPED.get)
        assert sum(abs(moved[name] - SHIPPED[name]) for name in SHIPPED) < 0.2

    def test_a_target_already_met_moves_nothing(self) -> None:
        moved = rederive(SHIPPED, REFLECTANCE, expected(SHIPPED, REFLECTANCE))
        assert moved == pytest.approx(SHIPPED)

    def test_an_unreachable_target_is_refused_rather_than_approximated(self) -> None:
        """Below the darkest material in the set there is no distribution at all,
        and the honest output is one the caller can see is impossible. The solve
        returns a negative weight, which `report` fails on and the config loader
        would refuse — an approximation would silently ship the nearest legal
        answer as though it were the derived one."""
        moved = rederive(SHIPPED, REFLECTANCE, 40.0)
        assert min(moved.values()) <= 0.0

    def test_a_single_material_bin_is_left_alone(self) -> None:
        """Its expected reflectance is whatever the palette gives it and no
        weighting can move it. The degenerate solve must not raise on the way to
        saying so — the tool reports every bin, including the ones it cannot
        help."""
        assert rederive({DARK.name: 1.0}, REFLECTANCE, 57.58) == {DARK.name: 1.0}


class TestRampClass:
    """Which class's ramp answer a surveyed building is compared against."""

    def test_it_is_the_class_with_no_override(self, hong_kong) -> None:
        style = hong_kong.buildings
        found = ramp_class(style)
        assert found in style.classes
        assert found not in style.class_materials

    def test_an_ambiguous_config_is_refused(self, hong_kong) -> None:
        """Dropping the overrides leaves three classes the ramp answers for, and
        picking one of them silently would compare the survey against a mean
        drawn from ground and viaducts."""
        with pytest.raises(ValueError, match="exactly one class"):
            ramp_class(replace(hong_kong.buildings, class_materials={}))
