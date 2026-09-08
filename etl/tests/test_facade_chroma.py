"""The `Q30` chroma measurement (`tools/facade_chroma.py`).

Only the parts whose failure is **silent**. This tool reports numbers that go
straight into `ART_DESIGN.md` and a decision record, and a distribution that is
subtly the wrong distribution reads exactly like the right one — nobody looks at
a mean of 15.4 and knows it should have been 12.6.

The population needs the 4.9 GB survey and is not here. What is here is the
arithmetic between a survey row and a published figure.
"""

from __future__ import annotations

import numpy as np
import pytest
from facade_chroma import SANCTIONED_MAX, Population, Spread, achieved, band_chroma, clipping
from lighting_rig import DEFAULT_RIG, rig_exposure
from ring_weights import ramp_class

from pipeline.colour import chroma_and_hue, srgb_to_lab


def violet_among_greys() -> np.ndarray:
    """Nine neutral buildings and one colour sRGB has no way to show."""
    lab = np.stack([np.full(10, 61.5), np.zeros(10), np.zeros(10)], axis=1)
    lab[0] = [95.0, 120.0, -120.0]
    return lab


def band_of(style, heights: dict[str, float]) -> np.ndarray:
    """The ramp lightness `Population` would derive, without the 4.9 GB survey."""
    return srgb_to_lab(
        np.array([style.colour_for(ramp_class(style), h) for h in heights.values()], np.float64)
    )


class TestRequested:
    """The colour the config asks a surveyed building to be."""

    def test_chroma_is_the_measurement_times_strength(self, hong_kong) -> None:
        """The claim the whole tool rests on, and the one that would be silently
        wrong if `with_hue` ever scaled the material's own chroma instead of
        replacing it: a building's asked-for `C*` is its survey `C*` times
        `strength`, and the material it draws does not enter."""
        style = hong_kong.buildings
        people = Population(
            band=band_of(style, {"a": 12.0, "b": 90.0}), hue=np.array([[3.0, 4.0], [-6.0, 8.0]])
        )
        lab = people.requested(2.0)
        assert np.hypot(lab[:, 1], lab[:, 2]) == pytest.approx([10.0, 20.0])

    def test_lightness_comes_from_the_band_not_the_survey(self, hong_kong) -> None:
        """The other half of `Q34`'s split. A tall building and a short one carry
        the same hue here, so any difference in `L*` is the ramp doing its job —
        and no difference at all would mean the ramp was not being consulted."""
        style = hong_kong.buildings
        people = Population(
            band=band_of(style, {"a": 6.0, "b": 200.0}), hue=np.array([[3.0, 4.0], [3.0, 4.0]])
        )
        lab = people.requested(1.0)
        assert lab[0, 0] != lab[1, 0]
        assert lab[1, 0] == pytest.approx(
            srgb_to_lab(np.array([style.colour_for(ramp_class(style), 200.0)]))[0, 0]
        )

    def test_hue_angle_survives_the_amplification(self, hong_kong) -> None:
        """`strength` is documented as keeping *which* building is warmer and
        changing only by how much. Scaling `a*` and `b*` together is what makes
        that true, and scaling chroma in any other space would not."""
        people = Population(
            band=band_of(hong_kong.buildings, {"a": 30.0}), hue=np.array([[-6.0, 8.0]])
        )
        angles = [chroma_and_hue(tuple(people.requested(s)[0, 1:])) for s in (1.0, 2.0)]
        assert angles[0][1] == pytest.approx(angles[1][1])
        assert angles[1][0] == pytest.approx(2.0 * angles[0][0])


class TestSpread:
    def test_share_over_the_sanctioned_maximum(self) -> None:
        """The headline figure. `>` and not `>=`, matching the "more saturated
        than the direction sanctions" the number is quoted as."""
        chroma = np.array([0.0, SANCTIONED_MAX, SANCTIONED_MAX + 0.1, 90.0])
        lab = np.stack([np.full(4, 61.5), chroma, np.zeros(4)], axis=1)
        assert Spread.of(lab).over == pytest.approx(50.0)

    def test_reports_the_tail_and_not_only_the_middle(self) -> None:
        """`Q30`'s finding is that the mean and the tail disagree — a summary
        that carried the mean alone could not have found it."""
        lab = np.stack([np.full(100, 61.5), np.arange(100.0), np.zeros(100)], axis=1)
        found = Spread.of(lab)
        assert found.median == pytest.approx(49.5)
        assert found.p99 == pytest.approx(99.0, abs=1.0)
        assert found.highest == pytest.approx(99.0)


class TestClipping:
    def test_representable_colours_cost_nothing(self) -> None:
        """Rounding is not clipping. At `strength` 1.0 almost the whole city is
        inside the gamut, so a tool that counted the byte grid would report a
        loss on a city that has none."""
        rng = np.random.default_rng(0)
        outside, worst = clipping(srgb_to_lab(rng.integers(0, 256, (2_000, 3))))
        assert (outside, worst) == (0.0, 0.0)

    def test_finds_the_colours_srgb_cannot_show(self) -> None:
        """10% outside, and a `dE` large enough that it could not be rounding."""
        outside, worst = clipping(violet_among_greys())
        assert outside == pytest.approx(10.0)
        assert worst > 1.0

    def test_the_worst_is_measured_on_a_clipped_colour(self) -> None:
        """The trap in reporting a maximum over the whole population: it would be
        the worst `dE` of *anything*, which is a number about rounding whenever
        nothing clipped, and it would still look like a gamut figure."""
        lab = violet_among_greys()
        _, worst = clipping(lab)
        one = np.linalg.norm(achieved(lab[:1]) - lab[:1], axis=1)[0]
        assert worst == pytest.approx(one)


class TestBandChroma:
    def test_is_the_authored_ramp_and_not_the_survey(self, hong_kong) -> None:
        """The baseline the `strength` rows depart from. `ART_DESIGN.md` quotes
        it as 1.76-13.83 and calls it "warm off-white, beige, pale grey-green" —
        if the ramp is re-authored, this is the number that has to move with it.

        ⚠️ **Taken at the rig's exposure since `P5-28c`**, like every other figure
        the tool prints, so that the baseline and the rows sit on one axis.
        """
        low, high = band_chroma(hong_kong.buildings, rig_exposure())
        assert 0.0 < low < high < SANCTIONED_MAX

    def test_the_exposure_lowers_chroma_and_does_not_leave_it_alone(self, hong_kong) -> None:
        """🔴 **The assumption `P5-28c` had to disprove to write this tool.**
        Exposure reads as a lightness control, so the obvious expectation is that
        it moves `L*` and leaves `a*`/`b*` where they were. It does not: a scale
        toward black in linear light pulls chroma down with it, which is why
        `facade_chroma` exposes every row it prints and why `Q30`'s table moved on
        a commit that changed no look."""
        unexposed = band_chroma(hong_kong.buildings, 1.0)
        at_rig = band_chroma(hong_kong.buildings, rig_exposure())
        assert at_rig[1] < unexposed[1]

    def test_a_rig_that_sets_no_exposure_is_refused(self, tmp_path) -> None:
        """⚠️ **Absent is an error and never a default.** A silent fallback would
        grade the palette the game does not draw, and read as a clean run."""
        rig = tmp_path / "no_anchor.tscn"
        rig.write_text('[node name="X" type="Node3D"]\n', encoding="utf-8")
        with pytest.raises(ValueError, match="0 times"):
            rig_exposure(rig)

    def test_a_rig_that_sets_it_twice_is_refused(self, tmp_path) -> None:
        """🔴 **The case where this reader and the engine disagree.**
        `lighting_rig.gd` warns that two rigs alive at once fight over the
        process-wide global and the *last* one readied wins; a `search` here
        would take the first. Both answers are silent, so neither is allowed."""
        rig = tmp_path / "two.tscn"
        rig.write_text("exposure_anchor = 0.52\nexposure_anchor = 0.9\n", encoding="utf-8")
        with pytest.raises(ValueError, match="2 times"):
            rig_exposure(rig)

    def test_a_zero_exposure_is_refused(self, tmp_path) -> None:
        """🔴 **The trap `P5-28c` moved out of the ETL and had to move the guard
        with.** `_exposure_anchor` refused `0.0` by name, because zero makes every
        shipped colour black and then satisfies the palette rule for any declared
        reflectance. The bar is `lighting_rig.gd`'s `@export_range` now, and a
        `.tscn` is plain text a hand edit reaches."""
        rig = tmp_path / "zero.tscn"
        rig.write_text("exposure_anchor = 0.0\n", encoding="utf-8")
        with pytest.raises(ValueError, match="outside the"):
            rig_exposure(rig)

    def test_the_shipped_rigs_agree(self) -> None:
        """⚠️ **Two rigs, one number, and nothing else enforces it.** They are
        different times of day and *may* diverge — but while they do not, a
        grader reading one is describing both, which is what lets
        `facade_chroma` default to `clean_daylight` without saying so."""
        golden = DEFAULT_RIG.parent / "golden_hour.tscn"
        assert rig_exposure(DEFAULT_RIG) == rig_exposure(golden)
