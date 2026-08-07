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
import json
import logging
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.buildings import (  # noqa: E402
    HUE_SOURCE_ID,
    Placement,
    colour_for,
    facade_hue,
    read_sheet,
    stem,
)
from pipeline.colour import in_gamut, lab_to_srgb, srgb_to_lab  # noqa: E402
from pipeline.config import BuildingStyle, CityConfig, load_city  # noqa: E402
from pipeline.fetch import source_dir  # noqa: E402
from ring_weights import ramp_class  # noqa: E402

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
        chroma = np.hypot(lab[:, 1], lab[:, 2])
        return cls(
            count=len(chroma),
            mean=float(chroma.mean()),
            median=float(np.median(chroma)),
            p90=float(np.percentile(chroma, 90)),
            p99=float(np.percentile(chroma, 99)),
            highest=float(chroma.max()),
            over=100.0 * float((chroma > SANCTIONED_MAX).mean()),
            lightness=float(lab[:, 0].mean()),
        )


def survey(city: CityConfig, *, root: Path | None = None) -> dict[str, tuple[float, float]]:
    """The survey rows the pipeline trusts, keyed by stem — `facade_hue`'s own
    filter, called rather than restated."""
    return facade_hue(city.buildings, city.id, root=root)


def heights(city: CityConfig, *, root: Path | None = None) -> dict[str, float]:
    """Each surveyed building's height, from the survey's own column.

    The same column `ring_weights.py` reads and for the same reason: the ramp is
    a step function and the survey's height matched the placed mesh's on 59 of 59
    when `Q37` checked, so only a building within centimetres of a band edge
    could take a different band.
    """
    style = city.buildings
    assert style.facade_hue_source is not None
    path = source_dir(city.id, HUE_SOURCE_ID, root=root) / style.facade_hue_source
    table = json.loads(path.read_text())
    return {key: float(row["height_m"]) for key, row in table.items()}


def requested(
    style: BuildingStyle,
    hues: dict[str, tuple[float, float]],
    height: dict[str, float],
    strength: float,
) -> np.ndarray:
    """`(n, 3)` CIELAB the config asks each surveyed building to be.

    The band's lightness carrying the survey's hue at `strength`, which is
    `with_hue`'s arithmetic before it converts — held in Lab because the gamut
    question is about the colour that was asked for, and converting first is what
    destroys the evidence.
    """
    answered_by_ramp = ramp_class(style)
    ramp = [style.material_for(answered_by_ramp, height[key]).colour for key in hues]
    lab = srgb_to_lab(np.array(ramp, dtype=np.float64))
    lab[:, 1] = [hue[0] * strength for hue in hues.values()]
    lab[:, 2] = [hue[1] * strength for hue in hues.values()]
    return lab


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
    lab = srgb_to_lab(np.array(ramp, dtype=np.float64))
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    return float(chroma.min()), float(chroma.max())


def shipped(
    city: CityConfig,
    region_id: str,
    hues: dict[str, tuple[float, float]],
    *,
    root: Path | None = None,
) -> dict[float, np.ndarray]:
    """`(n, 3)` CIELAB every surveyed building actually receives, per strength.

    The whole pipeline path — material draw, `with_hue`, jitter and clamping —
    walked over the region's real meshes, so that this module's claim that the
    material and the jitter do not reach chroma is a thing anyone can re-check
    rather than a thing anyone has to believe.

    Every strength answered from one pass over the sheets, because the sheets are
    the expensive part and the strength is a scalar the colour depends on.
    """
    style = city.buildings
    place = Placement.resolve(city, region_id, root, None)
    styles = {strength: replace(style, facade_hue_strength=strength) for strength in STRENGTHS}
    found: dict[float, list[np.ndarray]] = {strength: [] for strength in STRENGTHS}
    for _, sheet_path in place.sheets:
        for class_id, mesh in read_sheet(sheet_path, style.classes):
            if style.is_ground(class_id) or stem(mesh.name) not in hues:
                continue
            placed = mesh.translated(place.offset)
            for strength, styled in styles.items():
                found[strength].append(colour_for(styled, class_id, placed, hue=hues)[0][:3])
    return {
        strength: srgb_to_lab(np.array(colours, dtype=np.float64))
        for strength, colours in found.items()
    }


def report(city: CityConfig, region_id: str | None, *, root: Path | None = None) -> int:
    style = city.buildings
    hues = survey(city, root=root)
    if not hues:
        log.error("no facade survey for %s — there is no shipped chroma to measure", city.id)
        return 1
    height = heights(city, root=root)

    low, high = band_chroma(style)
    log.info("")
    log.info("  %d surveyed buildings after the vegetation filter", len(hues))
    log.info("  authored height bands sit at C* %.2f to %.2f", low, high)
    log.info("  ships at facade_hue.strength %.1f", style.facade_hue_strength)
    log.info("")
    log.info(
        "  strength |   mean  median     p90     p99     max | over C* %.0f |    L*", SANCTIONED_MAX
    )
    for strength in STRENGTHS:
        # The colour that survives the round trip, not the one asked for: above
        # `strength` 1.0 the two part company at the top of the range, and the
        # tail is the whole question. Asked-for peaks at C* 154 where sRGB can
        # deliver 102.
        found = Spread.of(achieved(requested(style, hues, height, strength)))
        log.info(
            "      %.1f   | %6.2f  %6.2f  %6.2f  %6.2f  %6.2f |     %5.1f%% | %5.1f",
            strength,
            found.mean,
            found.median,
            found.p90,
            found.p99,
            found.highest,
            found.over,
            found.lightness,
        )
    log.info("")
    for strength in STRENGTHS:
        outside, worst = clipping(requested(style, hues, height, strength))
        log.info(
            "  strength %.1f: %.1f%% outside the sRGB gamut, worst dE76 %.1f",
            strength,
            outside,
            worst,
        )

    if region_id is not None:
        log.info("")
        log.info("  the full pipeline path over %s, for comparison:", region_id)
        for strength, lab in shipped(city, region_id, hues, root=root).items():
            found = Spread.of(lab)
            log.info(
                "      %.1f   | %6.2f  %6.2f  %6.2f  %6.2f  %6.2f |"
                "     %5.1f%% | %5.1f  (%d meshes)",
                strength,
                found.mean,
                found.median,
                found.p90,
                found.p99,
                found.highest,
                found.over,
                found.lightness,
                found.count,
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", default="hong_kong", help="city id under etl/config/cities")
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument(
        "--shipped",
        nargs="?",
        const="wan_chai",
        metavar="REGION",
        help="also walk the region's real meshes through the whole pipeline path",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    return report(load_city(arguments.city), arguments.shipped, root=arguments.sources_root)


if __name__ == "__main__":
    raise SystemExit(main())
