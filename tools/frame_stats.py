"""How much of a building's albedo reaches the screen (`Q27`).

The fourth hand-run grader, and the only one that measures a **render** rather
than a mesh. `deck_error.py`, `overhang.py` and `ground_clearance.py` all ask
where geometry ended up; this asks how much of the colour the ETL paid to measure
survives to the frame — and, when it does not, whether the loss is the kind a
lighting change could ever fix.

It takes a **pair** of renders of the same camera from two builds that differ
only in albedo. Because `drive.sh` is deterministic to the centimetre, the pair
is pixel-aligned and can simply be subtracted: a pixel that did not move is a
pixel the change could not reach — sky, glass, road, an unlit face — and it
identifies itself with no mask, depth buffer or segmentation pass.

That matters because `Q27` was originally asked with a whole-frame mean, and a
third of the frame is sky, fog and glazing. Re-reading its own evidence through
the responding-pixel filter moved the answer from 0.19 to 0.28 before anything
was changed.

Three numbers come out, and the **third is the one that closed `Q27`**:

- **responding share** — how much of the frame was in the experiment at all.
- **gain** — rendered `ΔL*` per unit of albedo `ΔL*`. Intuitive, and *confounded*:
  `ΔL*` for a fixed reflectance ratio scales with how bright the pixel already
  is, so a dark frame scores a low gain with nothing wrong. Read it as a trend
  across variants of one scene, never as an absolute.
- **additive share** — of a responding pixel's luminance, the fraction that does
  **not** come from albedo. This is the unconfounded one. It compares the pixel's
  *linear* ratio against the albedo's own: a surface lit only by light it
  reflects moves in exact proportion, so anything left over is light the albedo
  did not ask for and cannot modulate.

⚠️ **A high additive share is not a lighting problem, and assuming it was cost a
full sweep of the rig.** Ambient, exposure, glow, fog, the tonemap curve and
specular were each ablated against this tool and **none moved gain by more than
0.05**. The cause was `COLOR_0` being authored in sRGB and consumed as linear —
an encoding error upstream of the light, which no light could undo. That
invariance is diagnostic: fog and glow are additive and the tonemap compressive,
so if changing them does nothing, the loss is not happening in the rig.

⚠️ **A pair must differ in exactly one thing.** Two renders that differ in both
albedo and exposure produce numbers that mean nothing, because the denominator is
only the albedo half. It bites harder here than in most A/Bs: both frames look
entirely plausible.

⚠️ **`--albedo-l` wants the albedo that *shipped*, not the one the config asked
for.** Jitter, clamping and the classes that ignore the height bands all move it.
Measure it off the built tiles' `COLOR_0`; asking for 18.0 `L*` delivered 16.93.

Clipping is reported on the definition `tonemap_white` was fixed against on
2026-08-06 — any channel at or above 250 — so those numbers stay comparable.

Run:  .venv/bin/python tools/frame_stats.py build/driver/street/t00.80.png
      .venv/bin/python tools/frame_stats.py --albedo-l 81.36 64.43 before.png after.png
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.colour import luminance, srgb_to_lab  # noqa: E402

log = logging.getLogger(__name__)

# A channel at or above this is treated as clipped. `HEAD~1` measured 20.6% of
# the aerial preview this way before `tonemap_white` went back to 3.0, and 0.1%
# after; keeping the threshold identical is what makes those numbers and these
# ones the same measurement.
CLIP_LEVEL = 250

# The `ΔL*` a pixel must move before it counts as having responded. Renders are
# deterministic, so the floor is not sampling noise — it is the sliver of pixels
# that catch a polygon edge differently once colour changes what the antialiaser
# blends. 0.5 `L*` is well under a just-noticeable difference and well over that.
RESPONSE_L = 0.5

# Below this linear luminance a ratio is dominated by quantisation, so those
# pixels are dropped from the ratio statistics only. At 8 bits the darkest code
# is 1/255 and the step between codes is the whole value.
MIN_LUMINANCE = 0.01


@dataclass(frozen=True)
class Frame:
    """One decoded render, in the three spaces the report needs it in."""

    path: Path
    size: tuple[int, int]
    rgb: np.ndarray
    lab: np.ndarray
    luminance: np.ndarray

    @property
    def chroma(self) -> np.ndarray:
        """`C*ab` per pixel — how colourful, independent of how light."""
        return np.hypot(self.lab[:, 1], self.lab[:, 2])


def load_frame(path: Path) -> Frame:
    """Decode a PNG, dropping any alpha channel."""
    with Image.open(path) as handle:
        image = handle.convert("RGB")
        size = image.size
        rgb = np.asarray(image, dtype=np.uint8).reshape(-1, 3)
    return Frame(
        path=path,
        size=size,
        rgb=rgb,
        lab=srgb_to_lab(rgb),
        luminance=luminance(rgb),
    )


def clipped_fraction(frame: Frame) -> float:
    """Share of pixels with any channel at or above `CLIP_LEVEL`.

    Clipping is a colour defect before it is a brightness one: a clipped texel is
    `a* = b* = 0` by construction, so every per-building difference inside the
    clipped region is flattened to the same white.
    """
    return float(np.mean(np.any(frame.rgb >= CLIP_LEVEL, axis=1)))


def relative_luminance(lightness: float) -> float:
    """The linear `Y` an `L*` corresponds to — the inverse of the CIELAB curve."""
    return float(((lightness + 16.0) / 116.0) ** 3)


def report_absolute(frame: Frame) -> None:
    """Print one frame's own distribution — no comparison, no gain."""
    lightness, chroma = frame.lab[:, 0], frame.chroma
    log.info("  %s  %d x %d", frame.path, *frame.size)
    log.info(
        "    L*      mean %5.1f   p10 %5.1f   p50 %5.1f   p90 %5.1f",
        float(np.mean(lightness)),
        *(float(v) for v in np.percentile(lightness, [10, 50, 90])),
    )
    log.info(
        "    C*      mean %5.1f   p50 %5.1f   p90 %5.1f",
        float(np.mean(chroma)),
        *(float(v) for v in np.percentile(chroma, [50, 90])),
    )
    log.info(
        "    clipped %5.1f%%  (any channel >= %d)", 100.0 * clipped_fraction(frame), CLIP_LEVEL
    )


def report_paired(before: Frame, after: Frame, albedo: tuple[float, float] | None) -> int:
    """Print what changed between two aligned renders. Returns a process status."""
    if before.size != after.size:
        log.error("FAIL frames differ in size: %dx%d against %dx%d", *before.size, *after.size)
        return 1

    delta = after.lab[:, 0] - before.lab[:, 0]
    responded = np.abs(delta) >= RESPONSE_L

    log.info("  before  %s", before.path)
    log.info("  after   %s", after.path)
    log.info("")
    log.info("  Whole frame — the statistic Q27 was originally asked with:")
    log.info(
        "    L*      %5.1f -> %5.1f   (delta %+5.1f)",
        float(np.mean(before.lab[:, 0])),
        float(np.mean(after.lab[:, 0])),
        float(np.mean(delta)),
    )
    log.info(
        "    C* p90  %5.1f -> %5.1f",
        float(np.percentile(before.chroma, 90)),
        float(np.percentile(after.chroma, 90)),
    )
    log.info(
        "    clipped %5.1f%% -> %5.1f%%",
        100.0 * clipped_fraction(before),
        100.0 * clipped_fraction(after),
    )

    log.info("")
    log.info("  Responding pixels — the ones the change could actually reach:")
    log.info("    share   %5.1f%%  (moved >= %.1f L*)", 100.0 * np.mean(responded), RESPONSE_L)

    if not responded.any():
        log.info("")
        log.info("  ⚠️  Nothing moved. Either the pair is identical, or the render")
        log.info("      did not pick up the change — check the reimport, not the rig.")
        return 0

    moved = np.abs(delta[responded])
    log.info(
        "    |dL*|   mean %5.2f   p50 %5.2f   p90 %5.2f",
        float(np.mean(moved)),
        *(float(v) for v in np.percentile(moved, [50, 90])),
    )
    log.info(
        "    C* p90  %5.1f -> %5.1f",
        float(np.percentile(before.chroma[responded], 90)),
        float(np.percentile(after.chroma[responded], 90)),
    )

    if albedo is None:
        return 0

    light, dark = albedo
    if light <= dark:
        log.error("FAIL --albedo-l wants the lighter build first, got %.2f then %.2f", light, dark)
        return 1

    albedo_ratio = relative_luminance(dark) / relative_luminance(light)
    usable = responded & (before.luminance > MIN_LUMINANCE)
    if not usable.any():
        log.info("")
        log.info("  ⚠️  Every responding pixel is too dark to take a ratio from.")
        return 0

    rendered_ratio = float(np.median(after.luminance[usable] / before.luminance[usable]))
    additive = (rendered_ratio - albedo_ratio) / (1.0 - albedo_ratio)

    log.info("")
    log.info(
        "  Against an albedo of L* %.2f -> %.2f (linear ratio %.3f):", light, dark, albedo_ratio
    )
    log.info(
        "    gain            %5.2f   rendered dL* per unit of albedo dL*",
        float(np.median(moved)) / (light - dark),
    )
    log.info("    linear ratio    %5.3f   what the pixel actually did", rendered_ratio)
    log.info(
        "    additive share  %5.0f%%  of a responding pixel is NOT from albedo", 100.0 * additive
    )
    if additive > 0.30:
        log.info("")
        log.info("    ⚠️  Above ~30%, suspect a colour-space or encoding fault before")
        log.info("        the lights — see this file's header and Q27. Ablate one rig")
        log.info("        setting: if the share does not move, the rig is not the cause.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "frames",
        type=Path,
        nargs="+",
        metavar="PNG",
        help="one frame for its own distribution, or two aligned frames to compare",
    )
    parser.add_argument(
        "--albedo-l",
        type=float,
        nargs=2,
        default=None,
        metavar=("LIGHT", "DARK"),
        help="mean CIELAB L* of the shipped COLOR_0 in each build, lighter first. "
        "Turns the rendered difference into a gain and an additive share",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(args.frames) > 2:
        log.error("FAIL wants one frame or two, got %d", len(args.frames))
        return 1
    for path in args.frames:
        if not path.is_file():
            log.error("FAIL no such frame at %s", path)
            return 1

    frames = [load_frame(path) for path in args.frames]
    log.info("")
    if len(frames) == 1:
        if args.albedo_l is not None:
            log.error("FAIL --albedo-l needs a pair of frames to compare")
            return 1
        report_absolute(frames[0])
        log.info("")
        return 0

    albedo = tuple(args.albedo_l) if args.albedo_l else None
    status = report_paired(frames[0], frames[1], albedo)
    log.info("")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
