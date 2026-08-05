"""sRGB ↔ CIELAB, for the one thing the pipeline needs a perceptual space for.

Buildings take their **lightness** from the height bands and their **hue** from
photographs, and that split is only expressible in a space where the two are
separate axes. In sRGB they are not: darkening a colour scales all three
channels, so there is no way to say "keep this building's cream, but let the
config decide how light it is".

⚠️ **The split is not stylistic — it is what the measurement supports.** A
building's `a*`/`b*` in an aerial photograph survive the illumination it was
shot under; its `L*` does not. `docs/PROGRESS.md` (2026-08-06) records the
sheet-wide numbers, and the per-orientation record found the same building's
north and south walls differing by up to 39 `L*` — larger than the whole
between-building spread. So hue is evidence and lightness is not, and this
module exists to let the pipeline use one without the other.

D65, the sRGB standard illuminant. Written out rather than taking a dependency:
`colormath` is unmaintained and `colour-science` is a large import for two
functions that are twenty lines and fully specified by the sRGB and CIE
standards.
"""

from __future__ import annotations

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


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """CIELAB back to `(n, 3)` sRGB, rounded and clipped to 0-255 `uint8`.

    ⚠️ **Clipping is silent and it is a real loss.** Lab describes colours sRGB
    cannot show, and a hue pushed hard enough at a light or dark value lands
    outside the gamut — where clipping each channel independently shifts the hue
    it was asked to preserve. Callers that amplify chroma should keep the
    amplification modest for that reason, not only for taste.
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
    return np.clip(np.round(v * 255.0), 0, 255).astype(np.uint8)


def with_hue(
    rgb: tuple[int, int, int], hue: tuple[float, float], strength: float
) -> tuple[int, int, int]:
    """`rgb`'s lightness carrying `hue`'s `(a*, b*)`, scaled by `strength`.

    `strength` is a stylisation knob and is documented as one: 1.0 reproduces
    the measured chroma, which is muted enough (`C*` ~6 on seven buildings in
    ten) that a city built from it reads as almost neutral. Above 1.0 keeps
    *which* building is warmer and only exaggerates by how much — so the
    ordering stays evidence and the magnitude becomes art direction.
    """
    lab = srgb_to_lab(np.array([rgb], dtype=np.float64))
    lab[0, 1] = hue[0] * strength
    lab[0, 2] = hue[1] * strength
    out = lab_to_srgb(lab)[0]
    return int(out[0]), int(out[1]), int(out[2])
