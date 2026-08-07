"""The band shares `Q31` is stated in (`tools/frame_stats.py`).

The first tests this tool has had. They cover the band arithmetic only — the
rest of the grader is a pair of renders and a ratio, and its failures are loud
and already guarded by the `FAIL` paths it prints. The bands are different:
they emit a percentage a human pastes into `DECISIONS.md` as the argument that
a look shipped or did not, so a share that is subtly wrong reads exactly like
one that is right.

⚠️ **These build `Frame` from `L*` directly rather than from pixels.** The sRGB
decode has its own tests in `test_colour.py`, and going through it would make
the edge cases below unreachable: no 8-bit grey lands on `L*` 10.0 exactly, so
the boundary the bands are defined by could not be tested at all. `rgb` and
`luminance` are left as zeros because `band_shares` reads neither — the
inconsistency is deliberate and confined to this module.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from frame_stats import MIDTONE_L, SHADOW_L, Frame, band_shares


def frame_of(*lightness: float) -> Frame:
    """A synthetic frame with the given `L*` per pixel, one pixel per row."""
    lab = np.zeros((len(lightness), 3), dtype=float)
    lab[:, 0] = np.asarray(lightness, dtype=float)
    zeros = np.zeros((len(lightness), 3), dtype=np.uint8)
    return Frame(
        path=Path("synthetic.png"),
        size=(len(lightness), 1),
        rgb=zeros,
        lab=lab,
        luminance=np.zeros(len(lightness), dtype=float),
    )


class TestBounds:
    """The half-open edges, which are what stop the two bands disagreeing."""

    def test_a_pixel_on_the_shadow_edge_is_a_midtone(self) -> None:
        """`SHADOW_L` belongs to the band it opens, not the one it closes. The
        silent failure is the other convention: it would move a pixel from the
        band the claim says is empty into the band the claim says is full, in
        the direction that makes the finding look worse."""
        shadow, midtone = band_shares(frame_of(SHADOW_L))
        assert shadow == 0.0
        assert midtone == 1.0

    def test_a_pixel_on_the_midtone_edge_is_in_neither(self) -> None:
        """`MIDTONE_L` is the exclusive top. A pixel there is lit, and counting
        it as a midtone would credit the fill with reaching a band it did
        not."""
        shadow, midtone = band_shares(frame_of(MIDTONE_L))
        assert shadow == 0.0
        assert midtone == 0.0

    def test_the_bands_never_double_count(self) -> None:
        """Spanning both edges and well outside them: the two shares plus the
        lit remainder have to be the whole frame exactly once.

        ⚠️ `approx` because three sixths do not sum to 1.0 in binary — this
        fixture happens to, but 1/4/1, 2/3/1 and 3/2/1 all land on
        0.9999999999999999. An exact comparison here would make a one-pixel
        edit to the fixture look like a binning defect.
        """
        frame = frame_of(0.0, 5.0, SHADOW_L, 20.0, MIDTONE_L, 90.0)
        shadow, midtone = band_shares(frame)
        lit = float(np.mean(frame.lab[:, 0] >= MIDTONE_L))
        assert shadow + midtone + lit == pytest.approx(1.0)


class TestEmptyMiddle:
    """The one thing the statistic exists to do that percentiles cannot."""

    def test_a_bimodal_frame_reports_an_empty_middle_percentiles_hide(self) -> None:
        """This is the whole argument for the tool, as an assertion.

        51 pixels in deep shadow against 49 in daylight — the shape `Q31`
        describes, at the shipped `kerb` frame's own split. The band share sees
        the middle is empty; p50 and p90 straddle it and report nothing, because
        with the middle empty the percentiles bounding it move *apart*.
        Sharpening the percentile grid does not help, which is why this is a
        different statistic and not a finer one.
        """
        frame = frame_of(*([2.0] * 51), *([70.0] * 49))

        shadow, midtone = band_shares(frame)
        assert shadow == 0.51
        assert midtone == 0.0

        p50, p90 = np.percentile(frame.lab[:, 0], [50, 90])
        assert p50 < SHADOW_L < MIDTONE_L < p90

    def test_a_percentile_can_report_a_value_no_pixel_has(self) -> None:
        """The sharper form of the same fault, and a live trap when reading
        these frames.

        Move the split to exactly half and `np.percentile` interpolates *across*
        the gap: p50 comes back 36.0, a confident mid-grey for a frame whose
        pixels are all at 2 or 70. The shipped `kerb` frame escapes this only by
        being 51/49 rather than 50/50 — a frame one percent darker would report
        a midtone p50 while having no midtones at all.
        """
        frame = frame_of(*([2.0] * 50), *([70.0] * 50))

        assert float(np.percentile(frame.lab[:, 0], 50)) == 36.0
        assert not np.any(np.isclose(frame.lab[:, 0], 36.0))

        _, midtone = band_shares(frame)
        assert midtone == 0.0

    def test_a_populated_middle_is_distinguished_from_an_empty_one(self) -> None:
        """The control, so the two tests above cannot pass by always returning
        zero: same 50% shadow share, but a quarter of the frame really is in the
        middle and the share says so.

        ⚠️ Its p50 is 11.0 — *inside* the band, and honestly reported here
        because the interpolation above lands at 36.0 on a frame with nothing
        there. A percentile is not reliably wrong, which is worse than being
        reliably wrong: it cannot be corrected for, only replaced.
        """
        frame = frame_of(*([2.0] * 50), *([20.0] * 25), *([70.0] * 25))
        shadow, midtone = band_shares(frame)
        assert shadow == 0.5
        assert midtone == 0.25
