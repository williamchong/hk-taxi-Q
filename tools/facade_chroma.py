"""Measure the shipped façade chroma against the authored palette (`Q30`).

The seventh hand-run tool. `ART_DESIGN.md` carries a palette table and a red
block saying the city no longer matches it; this is the measurement that block
quotes, and it existed only as a number in a document until now. Every figure in
`Q30` moves whenever `facade_hue.strength` moves or the survey is re-run, and
`Q37` re-ran the survey — so the number needed a mechanism for the same reason
`ring_weights.py` did.

**What it measures is chroma the config asks for, and that is legitimate *here*
and nowhere near lightness.** `with_hue` assigns `a*` and `b*` outright rather
than scaling what the material had, so a building's shipped `C*` is its measured
`C*` times `strength` — the drawn material and the colour jitter reach it only by
moving `L*`, which moves where the gamut boundary falls. Measured both ways over
Wan Chai the two agree to **0.04 `C*`**, and `--shipped` is here so that stays
checkable rather than becoming a claim in a comment. ⚠️ Do not carry the
shortcut across to lightness: `frame_stats.py` records asking for 18.0 `L*` and
getting 16.93, because jitter and clamping *do* land on that axis.

Run:  .venv/bin/python tools/facade_chroma.py
      .venv/bin/python tools/facade_chroma.py --shipped   # the full pipeline path
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.buildings import Placement, colour_for, facade_hue, read_sheet, stem  # noqa: E402
from pipeline.colour import (  # noqa: E402
    chroma,
    in_gamut,
    lab_to_srgb,
    lab_with_hue,
    srgb_to_lab,
)
from pipeline.config import BuildingStyle, CityConfig, load_city  # noqa: E402
from ring_weights import heights, ramp_class  # noqa: E402

log = logging.getLogger(__name__)

# The strengths the `ART_DESIGN.md` table has always carried: the faithful one,
# the one that ships, and the midpoint that says whether the tail grows linearly.
# Re-measuring on a different set would answer a different question — keeping
# these is what makes a new row comparable with the old one.
STRENGTHS = (1.0, 1.5, 2.0)

# The line `ART_DESIGN.md` draws for "more saturated than anything the direction
# sanctions". It is the doc's number rather than a derived one, and it is held
# here so the share stays comparable across re-measurements; `band_chroma` prints
# what the authored bands actually reach, which is the check that 20 is still a
# sane place to put it.
SANCTIONED_MAX = 20.0


@dataclass(frozen=True)
class Spread:
    """One strength's chroma distribution over a population of buildings."""

    count: int
    mean: float
    median: float
    p90: float
    p99: float
    highest: float
    over: float
    lightness: float

    @classmethod
    def of(cls, lab: np.ndarray) -> Spread:
        found = chroma(lab)
        return cls(
            count=len(found),
            mean=float(found.mean()),
            median=float(np.median(found)),
            p90=float(np.percentile(found, 90)),
            p99=float(np.percentile(found, 99)),
            highest=float(found.max()),
            over=100.0 * float((found > SANCTIONED_MAX).mean()),
            lightness=float(lab[:, 0].mean()),
        )


@dataclass(frozen=True)
class Population:
    """The surveyed buildings, as the two arrays every figure here comes from.

    Held apart because only one of them depends on `strength`: the band a
    building takes is fixed, and the sweep varies what is written over its
    `(a*, b*)`. Joining them once also removes the question of whether two
    dictionaries keyed by stem are still in step.
    """

    band: np.ndarray
    hue: np.ndarray

    @classmethod
    def of(cls, city: CityConfig, *, root: Path | None = None) -> Population:
        """Which rows the pipeline trusts is `facade_hue`'s rule, called rather
        than restated; the height column is `ring_weights.heights`' for the same
        reason. Neither is this tool's to decide."""
        style = city.buildings
        hues = facade_hue(style, city.id, root=root)
        if not hues:
            return cls(np.empty((0, 3)), np.empty((0, 2)))
        height = heights(city, root=root)
        answered_by_ramp = ramp_class(style)
        return cls(
            band=srgb_to_lab(
                np.array(
                    [style.colour_for(answered_by_ramp, height[key]) for key in hues],
                    dtype=np.float64,
                )
            ),
            hue=np.array(list(hues.values()), dtype=np.float64),
        )

    def __len__(self) -> int:
        return len(self.hue)

    def requested(self, strength: float) -> np.ndarray:
        """`(n, 3)` CIELAB the config asks each surveyed building to be.

        `colour.lab_with_hue` and not an assignment written here, so the colour
        this measures cannot come apart from the one `with_hue` ships. Held in
        Lab because the gamut question is about the colour that was *asked* for,
        and converting first is what destroys the evidence.
        """
        return lab_with_hue(self.band, self.hue, strength)


def achieved(lab: np.ndarray) -> np.ndarray:
    """What sRGB gives back — the round trip every shipped colour makes."""
    return srgb_to_lab(lab_to_srgb(lab).astype(np.float64))


def clipping(lab: np.ndarray) -> tuple[float, float]:
    """Share of a population sRGB cannot show, and the worst `dE` it costs.

    `dE` is CIE76, the plain Euclidean distance in Lab. Named because it is the
    least defensible of the `dE` family and the one most likely to be assumed:
    an unnamed `dE` is a number the next re-measurement cannot reproduce, which
    is the state this figure was in before.
    """
    outside = ~in_gamut(lab)
    if not outside.any():
        return 0.0, 0.0
    delta = np.linalg.norm(achieved(lab) - lab, axis=1)
    return 100.0 * float(outside.mean()), float(delta[outside].max())


def band_chroma(style: BuildingStyle) -> tuple[float, float]:
    """The chroma range the authored height bands themselves occupy.

    The palette table is authorised in words — "warm off-white, beige, pale
    grey-green" — and this is the number that says whether the bands still honour
    it. It is the baseline the `strength` rows are departing from.
    """
    ramp = [band.material.colour for band in style.height_bands]
    found = chroma(srgb_to_lab(np.array(ramp, dtype=np.float64)))
    return float(found.min()), float(found.max())


def shipped(
    city: CityConfig, region_id: str, *, root: Path | None = None
) -> dict[float, np.ndarray]:
    """`(n, 3)` CIELAB every surveyed building actually receives, per strength.

    The whole pipeline path — material draw, `with_hue`, jitter and clamping —
    walked over the region's real meshes, so that this module's claim that the
    material and the jitter do not reach chroma is a thing anyone can re-check
    rather than a thing anyone has to believe.

    Every strength answered from one pass over the sheets, because the sheets are
    the expensive part and the strength is a scalar the colour depends on.

    ⚠️ **The mesh is placed before it is coloured even though nothing in the
    colour reads its position today.** That is the call `build_region` makes, and
    the fidelity is the point — `Q35`'s leading candidate for the salt-and-pepper
    skyline is a spatial hash, which would make position matter without touching
    a line of this file.
    """
    style = city.buildings
    place = Placement.resolve(city, region_id, root, None)
    hues = facade_hue(style, city.id, root=root)
    styles = {strength: replace(style, facade_hue_strength=strength) for strength in STRENGTHS}
    found: dict[float, list[np.ndarray]] = {strength: [] for strength in STRENGTHS}
    for _, sheet_path in place.sheets:
        for class_id, mesh in read_sheet(sheet_path, style.classes):
            if style.is_ground(class_id) or stem(mesh.name) not in hues:
                continue
            placed = mesh.translated(place.offset)
            # Measured once and handed to all three, which is what the argument
            # is for: `colour_for` would otherwise sweep every vertex twice per
            # strength to rediscover the same height.
            bounds = placed.aabb()
            for strength, styled in styles.items():
                colour = colour_for(styled, class_id, placed, bounds=bounds, hue=hues)
                found[strength].append(colour[0][:3])
    return {
        strength: srgb_to_lab(np.array(colours, dtype=np.float64))
        for strength, colours in found.items()
    }


def _row(strength: float, found: Spread, suffix: str = "") -> None:
    """One line of the sweep. Shared because both tables print under the single
    header above them, so a format that drifted would misalign in silence — and
    reading the two against each other is the whole reason `--shipped` exists."""
    log.info(
        "      %.1f   | %6.2f  %6.2f  %6.2f  %6.2f  %6.2f |     %5.1f%% | %5.1f%s",
        strength,
        found.mean,
        found.median,
        found.p90,
        found.p99,
        found.highest,
        found.over,
        found.lightness,
        suffix,
    )


def report(city: CityConfig, region_id: str | None, *, root: Path | None = None) -> int:
    style = city.buildings
    people = Population.of(city, root=root)
    if not len(people):
        log.error("no facade survey for %s — there is no shipped chroma to measure", city.id)
        return 1
    asked = {strength: people.requested(strength) for strength in STRENGTHS}

    low, high = band_chroma(style)
    log.info("")
    log.info("  %d surveyed buildings after the vegetation filter", len(people))
    log.info("  authored height bands sit at C* %.2f to %.2f", low, high)
    log.info("  ships at facade_hue.strength %.1f", style.facade_hue_strength)
    log.info("")
    log.info(
        "  strength |   mean  median     p90     p99     max | over C* %.0f |    L*", SANCTIONED_MAX
    )
    for strength, lab in asked.items():
        # The colour that survives the round trip, not the one asked for: above
        # `strength` 1.0 the two part company at the top of the range, and the
        # tail is the whole question. Asked-for peaks at C* 154 where sRGB can
        # deliver 102.
        _row(strength, Spread.of(achieved(lab)))
    log.info("")
    for strength, lab in asked.items():
        outside, worst = clipping(lab)
        log.info(
            "  strength %.1f: %.1f%% outside the sRGB gamut, worst dE76 %.1f",
            strength,
            outside,
            worst,
        )

    if region_id is not None:
        log.info("")
        log.info("  the full pipeline path over %s, for comparison:", region_id)
        for strength, lab in shipped(city, region_id, root=root).items():
            found = Spread.of(lab)
            _row(strength, found, f"  ({found.count} meshes)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", default="hong_kong", help="city id under etl/config/cities")
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument(
        "--shipped",
        nargs="?",
        # Empty rather than a region id: naming one here would be the only
        # hardcoded Hong Kong region in the tree, and hard rule 3 keeps city
        # geography in the config. Bare `--shipped` takes the city's first.
        const="",
        metavar="REGION",
        help="also walk the region's real meshes through the whole pipeline path",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(arguments.city)
    region = arguments.shipped or next(iter(city.regions), None)
    return report(city, None if arguments.shipped is None else region, root=arguments.sources_root)


if __name__ == "__main__":
    raise SystemExit(main())
