"""sRGB ↔ CIELAB, for the one thing the pipeline needs a perceptual space for.

Buildings take their **lightness** from the height bands and their **hue** from
photographs, and that split is only expressible in a space where the two are
separate axes. In sRGB they are not: darkening a colour scales all three
channels, so there is no way to say "keep this building's cream, but let the
config decide how light it is".

⚠️ **The split is not stylistic — it is what the measurement supports, and only
just.** A building's surveyed `L*` is *repeatable*: the mean of its four walls
has an ICC of 0.822 across 2,026 buildings. But repeatability is not validity,
and the confounds that are constant across all four walls are exactly the ones
that stability cannot expose — **log pixel count explains 26% of `L*`** and
height 10%, both building-level, both indistinguishable from paint. At most 54%
of the variance is plausibly reflectance. `a*`/`b*` carry no such passenger, so
hue is evidence and lightness is a stable number of uncertain meaning.

⚠️ **It is *not* that walls facing the sun differ from walls facing away.** That
reading is intuitive, was argued here once, and is wrong by measurement: fitting
`L* = building + orientation` puts **1.4%** of the variance on compass
direction, and removing it entirely shrinks the spread within a building by
0.9%. Anyone re-opening this should attack the pixel-count confound, not the
shadows. `docs/DECISIONS.md`, `Q34`, has the full arithmetic.

D65, the sRGB standard illuminant. Written out rather than taking a dependency:
`colormath` is unmaintained and `colour-science` is a large import for two
functions that are twenty lines and fully specified by the sRGB and CIE
standards.
"""

from __future__ import annotations

import math

import numpy as np

# CIE standard illuminant D65, the sRGB white point, normalised to Y = 1.
_WHITE = np.array([0.95047, 1.0, 1.08883])

# sRGB primaries to CIE XYZ (IEC 61966-2-1).
_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_FROM_XYZ = np.linalg.inv(_TO_XYZ)

# CIE 1931 luminance from linear sRGB — the Y row of the matrix above, so the
# two cannot disagree about the primaries.
LUMA = _TO_XYZ[1]

# The CIE L*a*b* companding threshold, (6/29)^3, and its linear-segment slope.
_EPSILON = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """`(n, 3)` sRGB in 0-255 to linear 0-1, the exact IEC 61966-2-1 curve.

    Written once and exported because every consumer of a colour has to undo
    this encoding, and the copies disagreeing is what `Q27` *was* — the shaders
    carry their own only because GLSL cannot import this one.
    """
    v = np.asarray(rgb, dtype=np.float64) / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """`(n, 3)` sRGB in 0-255 to CIELAB. Returns float `(n, 3)` as `L*, a*, b*`."""
    xyz = srgb_to_linear(rgb) @ _TO_XYZ.T / _WHITE
    f = np.where(xyz > _EPSILON, np.cbrt(xyz), (_KAPPA * xyz + 16.0) / 116.0)
    return np.stack(
        [116.0 * f[:, 1] - 16.0, 500.0 * (f[:, 0] - f[:, 1]), 200.0 * (f[:, 1] - f[:, 2])],
        axis=1,
    )


def _lab_to_encoded(lab: np.ndarray) -> np.ndarray:
    """CIELAB to sRGB in 0-255, **unclipped** — everything `lab_to_srgb` does
    except discard the evidence of leaving the gamut.

    Split out so `lab_to_srgb` and `in_gamut` cannot come to disagree about where
    the boundary is: one clips this and the other measures it.
    """
    lightness, a_star, b_star = lab[:, 0], lab[:, 1], lab[:, 2]
    fy = (lightness + 16.0) / 116.0
    fx = fy + a_star / 500.0
    fz = fy - b_star / 200.0
    f = np.stack([fx, fy, fz], axis=1)
    cubed = f**3
    xyz = np.where(cubed > _EPSILON, cubed, (116.0 * f - 16.0) / _KAPPA) * _WHITE
    linear = xyz @ _FROM_XYZ.T
    v = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.abs(linear) ** (1.0 / 2.4) - 0.055)
    return v * 255.0


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """CIELAB back to `(n, 3)` sRGB, rounded and clipped to 0-255 `uint8`.

    ⚠️ **Clipping is silent and it is a real loss.** Lab describes colours sRGB
    cannot show, and a hue pushed hard enough at a light or dark value lands
    outside the gamut — where clipping each channel independently shifts the hue
    it was asked to preserve. Callers that amplify chroma should keep the
    amplification modest for that reason, not only for taste. `in_gamut` is how
    to find out how much of a population that is costing.
    """
    return np.clip(np.round(_lab_to_encoded(lab)), 0, 255).astype(np.uint8)


def in_gamut(lab: np.ndarray) -> np.ndarray:
    """Which of `(n, 3)` CIELAB colours sRGB can actually show.

    The boundary is **whether `lab_to_srgb`'s clip changed the byte it returns**,
    which is the loss that reaches a screen and is the only version of the
    question with no tolerance to argue about. A mathematical `0 <= linear <= 1`
    is the tempting definition and it does not survive contact with floating
    point: a colour converted *from* sRGB comes back a few parts in 10^16 outside
    the cube, so that test reports real colours as unshowable.

    ⚠️ **A `dE` threshold cannot answer this at all.** Every colour loses up to
    about 0.7 `dE` to the `uint8` grid whether or not sRGB can show it, so no
    threshold separates the two populations: below 0.7 it counts rounding as
    clipping, above it misses colours clipped by less than rounding costs. That
    is why this is a predicate and why `Q30` counts with it rather than with a
    distance.
    """
    encoded = np.round(_lab_to_encoded(lab))
    return ((encoded >= 0.0) & (encoded <= 255.0)).all(axis=1)


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Linear CIE `Y` for `(n, 3)` sRGB in 0-255.

    ⚠️ **Linear rather than `L*`, and both callers depend on that for the same
    reason.** A diffuse surface's luminance is `albedo * illumination`, so in
    linear light a *ratio* between two surfaces is meaningful and survives any
    change of exposure. `L*` is perceptually uniform and deliberately non-linear
    in exactly the way that breaks it — the same reflectance change produces
    different numbers at different brightnesses. `L*` is the right axis to read a
    palette on and the wrong one to define it on.

    `tools/frame_stats.py` needs this for its additive-share model and
    `reflectance` below for the palette rule; it lives here so the two cannot
    end up disagreeing about what luminance is.
    """
    return srgb_to_linear(rgb) @ LUMA


def reflectance(rgb: tuple[int, int, int]) -> float:
    """One colour's luminance as a percentage — the albedo it claims to be.

    The measurable half of the palette rule (`Q33`): every authored colour is
    `material reflectance x exposure_anchor`, so dividing this by the anchor
    recovers the real-world material the colour is asserting. That assertion is
    checkable against published albedos, which is the whole point — it gives a
    palette an external referent instead of only internal consistency.

    A percentage rather than `luminance`'s 0-1 because that is the unit
    published albedo tables are quoted in, and the config is authored against
    them directly.
    """
    return float(luminance(np.array([rgb], dtype=np.float64))[0]) * 100.0


def chroma_and_hue(hue: tuple[float, float]) -> tuple[float, float]:
    """`(a*, b*)` as CIELCh chroma and hue angle in degrees, wrapped to [0, 360).

    Named and exported rather than written inline at its one caller, because it
    is the definition of the units **`hong_kong.yaml` authors thresholds in** —
    `up_to_chroma` and `from_deg` mean nothing without it, and a config value has
    to be checkable against something. The polar convention is the arguable part:
    `atan2(b*, a*)`, so 0° is `+a*` (red), 90° is `+b*` (yellow), 180° is green
    and 270° blue. Anything binning buildings by hue has to agree with that or it
    is binning something else.
    """
    a_star, b_star = hue
    return math.hypot(a_star, b_star), math.degrees(math.atan2(b_star, a_star)) % 360.0


def with_hue(
    rgb: tuple[int, int, int], hue: tuple[float, float], strength: float
) -> tuple[int, int, int]:
    """`rgb`'s lightness carrying `hue`'s `(a*, b*)`, scaled by `strength`.

    `strength` is a stylisation knob and is documented as one: 1.0 reproduces
    the measured chroma, which is muted enough (six buildings in ten under `C*`
    8) that a city built from it reads as almost neutral. Above 1.0 keeps
    *which* building is warmer and only exaggerates by how much — so the
    ordering stays evidence and the magnitude becomes art direction.

    ⚠️ **It assigns `a*` and `b*` rather than scaling them**, so the shipped
    chroma is the measured chroma times `strength` and the material's own chroma
    never reaches a screen — `buildings.material_for` has what that costs. The
    consequence worth knowing here is that the drawn material and the jitter
    reach chroma only by moving `L*` and so moving where the gamut boundary
    falls, which `tools/facade_chroma.py` measures at 0.04 `C*` over Wan Chai.
    """
    lab = srgb_to_lab(np.array([rgb], dtype=np.float64))
    lab[0, 1] = hue[0] * strength
    lab[0, 2] = hue[1] * strength
    out = lab_to_srgb(lab)[0]
    return int(out[0]), int(out[1]), int(out[2])
