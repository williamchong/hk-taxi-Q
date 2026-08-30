"""Re-derive the surveyed material ring weights against the survey (`Q34′`).

The sixth hand-run tool, and the second that *produces* config rather than
grading a build. `facade_survey.py` measures the source imagery; this reads what
that wrote and answers the question `hong_kong.yaml` asks in a comment and had no
mechanism for: **re-derive these if the ramp moves.**

The property it derives to is `Q34`'s mitigation, and that mitigation is what
makes any change to the draw gradeable: **every bin's weights are authored so its
expected reflectance matches what the height ramp already handed that same
population.** Anything visible in a before/after frame is then hue structure
rather than a level change. `etl/tests/test_config.py` asserts a deliberately
loose version of this against the ramp's *unweighted* band mean, because that
suite must run without the 4.9 GB survey. This is the real one.

⚠️ **The weights are underdetermined, and the free degree of freedom is fixed by
a stated rule rather than by whoever runs this.** Three materials against two
constraints — sum to 1, and hit the target — leave a line of solutions, and
different points on it repaint different buildings for no reason anyone could
name later. The rule is the **smallest move from the shipped weights**, which
keeps whichever material the author made dominant dominant. It is a choice, so it
is written down and not left to the solver.

⚠️ **A large change in a bin's *share* does not imply a large change in its
weights.** The bins partition on hue and every target is a mean over *height*, so
stock moving between bins barely moves either bin's target — `Q34′` re-derived
across an 11-point swing in the near-neutral ring and no target moved by more
than 0.35 reflectance points. Height and hue are near-independent, which is
`Q34`'s finding; expect this tool to confirm it rather than to overturn it.

Run:  .venv/bin/python tools/ring_weights.py
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.buildings import HUE_SOURCE_ID, facade_hue  # noqa: E402
from pipeline.colour import chroma_and_hue  # noqa: E402
from pipeline.config import (  # noqa: E402
    BuildingStyle,
    Config,
    MaterialAssignment,
    WeightedDraw,
    load_config,
)
from pipeline.fetch import source_dir  # noqa: E402

log = logging.getLogger(__name__)

# Authored weights are two decimal places, and the derivation rounds to that
# rather than emitting a number nobody would type into a config by hand.
WEIGHT_PLACES = 2

# What the rounding may cost, in reflectance points. Not a tuning knob: one
# hundredth of a weight is worth 0.01 of the bin's reflectance spread — 0.049 on
# the two-material cool sector and 0.128 on the widest — so a bin that misses by
# more than this is missing for a reason rounding cannot explain, and the likely
# cause is a target outside what its material set can express at all.
RESIDUAL_MAX = 0.10


@dataclass(frozen=True)
class Bin:
    """One distribution the surveyed branch can select, under the thresholds
    that select it."""

    label: str
    draw: WeightedDraw


def bins(assignment: MaterialAssignment) -> list[Bin]:
    """Every distribution `MaterialAssignment.draw_for` can return.

    Built from the config's own rings and sectors so that adding a ring is not
    also an edit here, and labelled from the thresholds rather than from names
    this tool would have to invent — a bin has no identity beyond the chroma and
    hue that reach it.
    """
    found: list[Bin] = []
    for ring in assignment.rings:
        edge = "inf" if math.isinf(ring.up_to_chroma) else f"{ring.up_to_chroma:g}"
        if ring.draw is not None:
            found.append(Bin(f"C* <= {edge}", ring.draw))
            continue
        for index, sector in enumerate(ring.sectors):
            # The last sector wraps through 360 to the first, which is the
            # loader's rule and is why this indexes modulo the length.
            upper = ring.sectors[(index + 1) % len(ring.sectors)].from_deg
            found.append(Bin(f"C* <= {edge}, {sector.from_deg:g}-{upper:g} deg", sector.draw))
    return found


def weights_of(draw: WeightedDraw) -> dict[str, float]:
    """The authored weights back out of a built draw.

    `WeightedDraw` keeps the cumulative table and not the weights, because the
    cumulative table is what a draw needs. Differencing it is exact — the bounds
    are partial sums of the authored numbers, and the last is 1.0 by assignment.
    """
    lower = 0.0
    weights: dict[str, float] = {}
    for material, bound in zip(draw.materials, draw.bounds, strict=True):
        weights[material.name] = bound - lower
        lower = bound
    return weights


def expected(weights: dict[str, float], reflectance: dict[str, float]) -> float:
    """Mean reflectance a building drawing from these weights gets."""
    return math.fsum(weight * reflectance[name] for name, weight in weights.items())


def rederive(
    current: dict[str, float], reflectance: dict[str, float], target: float
) -> dict[str, float]:
    """`current`, moved as little as it can be to expect `target`.

    The minimum-norm correction onto the two constraints, which is the smallest
    repaint that satisfies both — see this module's header for why the rule is
    stated rather than left to whichever solution a solver happens to reach.
    """
    names = list(current)
    weights = np.array([current[name] for name in names])
    albedo = np.array([reflectance[name] for name in names])
    constraints = np.vstack([np.ones_like(albedo), albedo])
    goal = np.array([1.0, target])
    try:
        correction = np.linalg.solve(constraints @ constraints.T, goal - constraints @ weights)
    except np.linalg.LinAlgError:
        # One material, or several at one reflectance: the bin's expected value
        # is whatever the palette gives it and no weighting can move it.
        return dict(current)
    moved = np.round(weights + constraints.T @ correction, WEIGHT_PLACES)
    # Rounding breaks the sum, and the deficit goes to the largest weight: it is
    # where a hundredth is proportionally smallest, and it is the weight the
    # smallest-move rule is trying hardest to leave alone.
    moved[np.argmax(moved)] += round(1.0 - moved.sum(), WEIGHT_PLACES)
    return {
        name: round(float(value), WEIGHT_PLACES) for name, value in zip(names, moved, strict=True)
    }


def ramp_class(style: BuildingStyle) -> str:
    """The class the height ramp answers for, derived rather than named here.

    `buildings.material_for` reaches the rings only for a class with no
    `class_materials` override, so the ramp mean a surveyed building is being
    compared against is the one *that* class gets. Reading the name out of the
    config keeps this city-agnostic (hard rule 3), and the count check is what
    stops it silently picking one of two.
    """
    plain = [name for name in style.classes if name not in style.class_materials]
    if len(plain) != 1:
        raise ValueError(
            f"expected exactly one class the height ramp answers for, found {plain or '(none)'}"
        )
    return plain[0]


def heights(city: Config, *, root: Path | None = None) -> dict[str, float]:
    """Every surveyed building's height, keyed by stem.

    ⚠️ **The height is the survey's own column, not the placed mesh's.** They are
    the same measurement taken off two versions of the same building — `Q37`
    matched them exactly on 59 of 59 on `11-SW-9D` — and the ramp is a step
    function, so only a row within centimetres of a band edge could differ.

    Read here rather than in each tool that wants it, so that where the survey
    lives and what its height column is called are written down once —
    `facade_hue` already owns the same question for the hue column.
    """
    style = city.buildings
    if style.facade_hue_source is None:
        return {}
    path = source_dir(HUE_SOURCE_ID, root=root) / style.facade_hue_source
    table = json.loads(path.read_text())
    return {stem: float(row["height_m"]) for stem, row in table.items()}


def population(city: Config, *, root: Path | None = None) -> list[tuple[float, float, float]]:
    """`(chroma, hue angle, ramp reflectance)` for every row the pipeline uses.

    The vegetation filter is `facade_hue`'s, called rather than copied: which
    rows the pipeline trusts is one rule and it is already written down. Only the
    height is read separately, because that function returns hue and nothing else.
    """
    style = city.buildings
    hues = facade_hue(style, root=root)
    if not hues:
        return []
    height = heights(city, root=root)
    answered_by_ramp = ramp_class(style)
    return [
        (
            *chroma_and_hue(hue),
            style.material_for(answered_by_ramp, height[stem]).reflectance,
        )
        for stem, hue in hues.items()
    ]


def report(city: Config, rows: list[tuple[float, float, float]]) -> int:
    """Every bin's target, its shipped weights and the re-derived ones."""
    assignment = city.buildings.material_assignment
    found = bins(assignment)
    ramp: dict[str, list[float]] = {found_bin.label: [] for found_bin in found}
    for chroma, hue_deg, reflectance in rows:
        drawn = assignment.draw_for(chroma, hue_deg)
        # Identity, not equality: two bins may legitimately carry the same
        # weights, and it is the one `draw_for` returned that this row is in.
        label = next(item.label for item in found if item.draw is drawn)
        ramp[label].append(reflectance)

    failed = 0
    for item in found:
        reached = ramp[item.label]
        current = weights_of(item.draw)
        reflectance = {material.name: material.reflectance for material in item.draw.materials}
        log.info("")
        log.info("  %s", item.label)
        if not reached:
            log.error("    FAIL  no surveyed building falls here — nothing to derive against")
            failed = 1
            continue
        target = math.fsum(reached) / len(reached)
        proposed = rederive(current, reflectance, target)
        log.info(
            "    %d buildings, %.1f%% of the surveyed stock, ramp mean %.2f%%",
            len(reached),
            100.0 * len(reached) / len(rows),
            target,
        )
        log.info(
            "    expects %.3f%% now, %.3f%% re-derived (%+.3f off target)",
            expected(current, reflectance),
            expected(proposed, reflectance),
            expected(proposed, reflectance) - target,
        )
        for name in sorted(proposed):
            log.info(
                "      %-14s %.2f -> %.2f  (%+.2f)",
                name,
                current[name],
                proposed[name],
                proposed[name] - current[name],
            )
        log.info(
            "    weights: {%s}",
            ", ".join(f"{name}: {proposed[name]:.2f}" for name in sorted(proposed)),
        )
        residual = abs(expected(proposed, reflectance) - target)
        if residual > RESIDUAL_MAX:
            log.error(
                "    FAIL  %.3f points off target, past the %.2f rounding can account for — "
                "this bin's materials cannot express it",
                residual,
                RESIDUAL_MAX,
            )
            failed = 1
        if min(proposed.values()) <= 0.0:
            log.error("    FAIL  a weight reached zero — the target is outside this material set")
            failed = 1
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    rows = population(city, root=arguments.sources_root)
    if not rows:
        log.error("no facade survey — there is nothing to derive against")
        return 1
    log.info("")
    log.info("  %d surveyed buildings after the vegetation filter", len(rows))
    return report(city, rows)


if __name__ == "__main__":
    raise SystemExit(main())
