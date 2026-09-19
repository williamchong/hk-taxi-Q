"""How far the drawn carriageway is from the structure it is meant to lie on (`P2-7`).

`P2-7`'s acceptance, and the reason it is a separate tool rather than a number
the road stage prints: **the stage cannot mark its own work.** `roads.py` chose
every off-grade height by asking `HeightField.sample_along` about the source map
sheets. Asking the same query about the same geometry afterwards measures only
whether the answer was written down correctly — it reads |error| p90 0.02 m,
which is the sampler agreeing with itself.

So nothing here is shared with the code it grades:

| | the pipeline | this tool |
|---|---|---|
| Structure geometry | source sheets, full density | **shipped tiles**, decimated and welded |
| Which surface is a deck | slab clustering, continuity walk | **upward faces**, by winding |
| Which class is structure | sub-directory in the sheet zip | **vertex colour** |
| Which height wins | continuity from the last station | **nearest to the drawn road** |
| Spatial index | `HeightField`'s fitted grid | its own, keyed from the origin |

⚠️ Two things here are *not* independent, and saying so is the point of a table
like this. The barycentric test in `Faces.heights_at` is `terrain._hits` with
different names — a sign or inclusivity error in it would be present in both and
invisible here. And `stations` is `plan_steps` plus the body of
`roads.resample`, kept as a copy rather than imported because
`from pipeline.roads import ...` drags in `pipeline.terrain` and GDAL, and
losing "`HeightField` is unreachable from this module" costs more than three
lines of duplication are worth. Neither is where the value is: the rows above
are, and station placement decides only *where* a height is compared, never what
the comparison means.

The tile decimation is the part that matters. `P2-1` collapses `INFRASTRUCTURE`
on a 0.5 m cell, and a deck is thinner than a building — so the geometry the
player's wheels actually touch is *not* the geometry the ETL sampled, and the
difference is exactly what an internal check cannot see.

The carriageway is read from the shipped `roads.glb`. `roadgraph.json` supplies
plan positions — which edges are off-grade and where their centrelines run — and
one height, its own `y`, used *only* to decide which of several overlapping
drawn surfaces belongs to an edge. It never scores one. `elevated_samples`
argues that in full, because it is the seam where a defect could hide.

Run:  .venv/bin/python tools/deck_error.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from _lib.bundle import (  # noqa: E402
    Faces,
    bundle_arguments,
    drawn_surface,
    load_bundle,
    log_bundle,
    nearest,
    stations,
    structure_faces,
)
from pipeline.config import load_config  # noqa: E402

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Reading the shipped bundle — shared with `overhang.py` and `ground_clearance.py`
#
# All three grade the same bundle and must resolve it the same way, down to the
# message a missing `city.json` prints. Kept here rather than in a fourth module
# because this one is the oldest and the one `P2-7` cites; the split that
# matters is tool-versus-pipeline, and that is unaffected.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Samples:
    """Stations on the drawn carriageway, and everything that did not become one.

    ⚠️ `asked` and `unmatched` exist because a station that fails attribution
    used to leave no trace. Injecting a 30 m error into a third of the elevated
    carriageway then produced |error| p90 0.09 m, coverage 97.6% and a pass: the
    broken stations simply stopped being stations, and every ratio was computed
    over the survivors. A measurement tool must count what it *failed* to
    measure, or its denominator is chosen by the defect.
    """

    points: np.ndarray
    edges: int
    asked: int
    unmatched: list[int]


def elevated_samples(
    generated: Path, manifest: dict[str, Any], spacing_m: float, near_m: float
) -> _Samples:
    """Where the shipped road mesh draws the *middle* of each elevated carriageway.

    Heights come from `roads.glb` — the mesh that ships and collides. The graph
    supplies plan positions and nothing else; take a height from it and this
    would grade the ETL's arithmetic rather than its result.

    ⚠️ **Sampled down the centreline, not at the mesh's own vertices**, and the
    difference is most of this tool's answer. `roads.glb` carries vertices only
    at `TEXCOORD_0.x` of 0 and `lanes` — the two *edges* of the carriageway —
    and `width_m` is hand-tuned wider than the real road for playability. So the
    drawn edges deliberately overhang the deck they sit on, and scoring them
    finds the structure 7 m below rather than the deck they belong to. Measured
    that way `CANAL ROAD FLYOVER` reads 8.4 m of "error" at a place where the
    source sheets and the shipped tiles agree exactly and the ETL is right. That
    is overhang, which is `Q19`'s question, and this is `Q20`'s.

    Where several carriageways overlap in plan — an opposed pair, or a flyover
    over a street — the drawn height nearest the edge's own polyline is taken.
    That reads the graph's `y`, which needs stating: it identifies *which*
    surface, never scores it. A ribbon is extruded from its own polyline, so it
    sits within a kerb height of it wherever the ETL put it, including somewhere
    wrong — attribution cannot hide an error, only stop two different roads
    being compared.

    Level -1 is excluded outright. A tunnel is a void with no structure to lie
    on, so every sample would score against whatever passes overhead. `Q21` asks
    whether it should be drawn at all; it is not what `Q20` measures.
    """
    # Both filenames come from the manifest, which is the thing that knows them.
    graph = json.loads((generated / manifest["road_graph"]).read_text())

    edges = [edge for edge in graph["edges"] if edge["elevation_level"] > 0]
    if not edges:
        raise SystemExit("the graph has no elevated edges to measure")

    drawn = drawn_surface(generated, manifest)

    samples: list[tuple[float, float, float]] = []
    asked = 0
    unmatched: list[int] = []
    for edge in edges:
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        matched = 0
        for x, expected, z in stations(polyline, spacing_m):
            asked += 1
            drawn_here = nearest(drawn.heights_at(x, z), expected, near_m)
            if drawn_here is not None:
                matched += 1
                samples.append((x, drawn_here, z))
        if not matched:
            unmatched.append(int(edge["id"]))

    return _Samples(
        points=np.asarray(samples, dtype=np.float64),
        edges=len(edges),
        asked=asked,
        unmatched=unmatched,
    )


def measure(samples: np.ndarray, deck: Faces, clearance_m: float = 0.0) -> tuple[np.ndarray, int]:
    """Signed height of each sample above the nearest deck face, and the misses.

    `clearance_m` is subtracted because the carriageway is *meant* to sit that
    far above the deck — it is the wearing course, and the layer that stops the
    two surfaces interleaving once they agree to within the tile decimation.
    Scoring against the bare deck would read a deliberate 0.20 m as 0.20 m of
    error and grow with any future change to it.

    Nearest rather than highest or lowest: the question is how far the drawn
    road is from *a* deck, and a flyover stacked over another would otherwise be
    scored against whichever happened to be on top. It flatters only where two
    decks are within the error being measured, which is the case `slab_gap_m`
    already says does not occur — the closest stacked pair in this region is
    3.36 m apart.
    """
    errors: list[float] = []
    uncovered = 0
    for x, y, z in samples:
        below = nearest(deck.heights_at(float(x), float(z)), y)
        if below is None:
            uncovered += 1
            continue
        errors.append(float(y - below - clearance_m))
    return np.asarray(errors), uncovered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    parser.add_argument(
        "--accept-p90-m",
        type=float,
        default=0.5,
        help="fail above this |error| p90 (default: P2-7's criterion)",
    )
    parser.add_argument("--spacing-m", type=float, default=2.0, help="centreline station spacing")
    parser.add_argument(
        "--clearance-m",
        type=float,
        default=None,
        # Defaults to what the city declares, which is right for any bundle
        # built from that config. The override exists for the one comparison
        # that is not: grading a bundle built *before* `deck.clearance_m` — the
        # pre-`P2-7` baseline — where subtracting a layer its geometry never had
        # shifts every figure by exactly that much.
        help="override the city's deck clearance; use 0 to grade a bundle built without one",
    )
    parser.add_argument(
        "--accept-measured",
        type=float,
        default=0.90,
        help="fail if less than this share of the asked-for stations could be measured",
    )
    parser.add_argument(
        "--accept-below-m",
        type=float,
        default=0.5,
        # `P2-7` first wrote this as "no sample more than 0.1 m below", which was
        # set against the internal check where the geometry is exact. The
        # shipped tiles are not: `P2-1` collapses `INFRASTRUCTURE` on a 0.5 m
        # cell, which alone moves the deck's top face -0.04 m median and widens
        # |error| p90 from 0.030 to 0.095 with the carriageway held still. A
        # 0.1 m gate therefore sits under the resolution of the surface it is
        # measuring. Kept at the same 0.5 m as the p90 criterion, and applied to
        # the *worst* intrusion rather than to a share of samples — "how far
        # does the road ever sink into the flyover" is `Q20`'s actual question.
        help="the deepest a sample may sit below the deck before it is inside the structure",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    manifest, tiles = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)

    deck, structure_class = structure_faces(city, tiles)
    taken = elevated_samples(args.generated, manifest, args.spacing_m, args.attribute_within_m)
    declared = city.roads.deck.clearance_m if city.roads.deck is not None else 0.0
    clearance = declared if args.clearance_m is None else args.clearance_m
    errors, uncovered = measure(taken.points, deck, clearance)
    log.info(
        "  %d upward faces of '%s' across %d tiles; %d elevated edges",
        len(deck.corners),
        structure_class,
        len(tiles),
        taken.edges,
    )
    # Two ways a station leaves the measurement, and both are reported against
    # the same denominator — everything the centrelines asked for. A station is
    # lost here when the drawn road has nothing within `--attribute-within-m` of
    # it, and lost below when no deck lies under it.
    log.info(
        "  %d stations asked: %d unmatched by the drawn road, %d with no deck under them",
        taken.asked,
        taken.asked - len(taken.points),
        uncovered,
    )
    if not len(errors):
        raise SystemExit("no carriageway point had structure under it — nothing to measure")

    absolute = np.abs(errors)
    p90 = float(np.percentile(absolute, 90))
    deepest = float(-errors.min())
    log.info("")
    log.info(
        "  drawn carriageway minus the deck beneath it, less its %.2f m clearance, in metres:",
        clearance,
    )
    log.info("    median   %+.3f", float(np.median(errors)))
    log.info("    p10/p90  %+.2f / %+.2f", *np.percentile(errors, [10, 90]))
    log.info("    |err|p90 %.3f   (accepts %.2f)", p90, args.accept_p90_m)
    log.info("    deepest below the deck  %.2f   (accepts %.2f)", deepest, args.accept_below_m)
    log.info("    furthest above the deck %.2f", float(errors.max()))
    # Informational, not gates. Both are the figures `Q20` opened on — it
    # recorded the ribbon below the deck in 66% of samples — so a reader can
    # line this run up against that without re-deriving it.
    #
    # ⚠️ Reported at 0.10 m rather than "below at all", which reads 84.9% on a
    # passing run and means nothing: the tiles' own decimation puts the median
    # 0.04 m under the deck, so most of a correct carriageway is *slightly*
    # below it. `Q20`'s complaint was a road inside a flyover, not under it by a
    # tile's rounding.
    log.info("    within +-0.10 m: %.1f%%", 100.0 * float((absolute <= 0.10).mean()))
    log.info("    below the deck by over 0.10 m: %.1f%%", 100.0 * float((errors < -0.10).mean()))
    measured = len(errors) / taken.asked
    log.info(
        "    measured %.1f%% of what was asked   (accepts %.2f)",
        100.0 * measured,
        args.accept_measured,
    )

    problems = []
    if p90 > args.accept_p90_m:
        problems.append(f"|error| p90 is {p90:.2f} m")
    if deepest > args.accept_below_m:
        problems.append(f"the carriageway sinks {deepest:.2f} m into the structure")
    # ⚠️ Gating the denominator, not just the ratios above it. Every ratio here
    # is computed over the stations that survived, so a defect that stops a
    # station being measurable improves every other number on this page. An edge
    # contributing nothing is the sharpest form of that and fails outright.
    if measured < args.accept_measured:
        problems.append(f"only {100.0 * measured:.1f}% of the carriageway could be measured")
    if taken.unmatched:
        problems.append(
            f"{len(taken.unmatched)} elevated edges matched no drawn road at all: "
            f"{taken.unmatched[:5]}"
        )
    if problems:
        log.error("")
        for problem in problems:
            log.error("  FAIL  %s", problem)
        return 1

    log.info("")
    log.info("  P2-7 acceptance met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
