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
from facade_chroma import SANCTIONED_MAX, Spread, achieved, band_chroma, clipping, requested

from pipeline.colour import chroma_and_hue, srgb_to_lab


class TestRequested:
    """The colour the config asks a surveyed building to be."""

    def test_chroma_is_the_measurement_times_strength(self, hong_kong) -> None:
        """The claim the whole tool rests on, and the one that would be silently
        wrong if `with_hue` ever scaled the material's own chroma instead of
        replacing it: a building's asked-for `C*` is its survey `C*` times
        `strength`, and the material it draws does not enter."""
        hues = {"a": (3.0, 4.0), "b": (-6.0, 8.0)}
        lab = requested(hong_kong.buildings, hues, {"a": 12.0, "b": 90.0}, 2.0)
        assert np.hypot(lab[:, 1], lab[:, 2]) == pytest.approx([10.0, 20.0])

    def test_lightness_comes_from_the_band_not_the_survey(self, hong_kong) -> None:
        """The other half of `Q34`'s split. A tall building and a short one carry
        the same hue here, so any difference in `L*` is the ramp doing its job —
        and no difference at all would mean the ramp was not being consulted."""
        style = hong_kong.buildings
        lab = requested(style, {"a": (3.0, 4.0), "b": (3.0, 4.0)}, {"a": 6.0, "b": 200.0}, 1.0)
        assert lab[0, 0] != lab[1, 0]
        assert lab[1, 0] == pytest.approx(
            srgb_to_lab(np.array([style.material_for("BUILDING", 200.0).colour]))[0, 0]
        )

    def test_hue_angle_survives_the_amplification(self, hong_kong) -> None:
        """`strength` is documented as keeping *which* building is warmer and
        changing only by how much. Scaling `a*` and `b*` together is what makes
        that true, and scaling chroma in any other space would not."""
        hues = {"a": (-6.0, 8.0)}
        style = hong_kong.buildings
        angles = [
            chroma_and_hue(tuple(requested(style, hues, {"a": 30.0}, strength)[0, 1:]))
            for strength in (1.0, 2.0)
        ]
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
        """One light violet among nine greys: 10% outside, and a `dE` large
        enough that it could not be rounding."""
        lab = np.stack([np.full(10, 61.5), np.zeros(10), np.zeros(10)], axis=1)
        lab[0] = [95.0, 120.0, -120.0]
        outside, worst = clipping(lab)
        assert outside == pytest.approx(10.0)
        assert worst > 1.0

    def test_the_worst_is_measured_on_a_clipped_colour(self) -> None:
        """The trap in reporting a maximum over the whole population: it would be
        the worst `dE` of *anything*, which is a number about rounding whenever
        nothing clipped, and it would still look like a gamut figure."""
        lab = np.stack([np.full(10, 61.5), np.zeros(10), np.zeros(10)], axis=1)
        lab[0] = [95.0, 120.0, -120.0]
        _, worst = clipping(lab)
        one = np.linalg.norm(achieved(lab[:1]) - lab[:1], axis=1)[0]
        assert worst == pytest.approx(one)


class TestBandChroma:
    def test_is_the_authored_ramp_and_not_the_survey(self, hong_kong) -> None:
        """The baseline the `strength` rows depart from. `ART_DESIGN.md` quotes
        it as 1.92-13.84 and calls it "warm off-white, beige, pale grey-green" —
        if the ramp is re-authored, this is the number that has to move with it."""
        low, high = band_chroma(hong_kong.buildings)
        assert 0.0 < low < high < SANCTIONED_MAX
