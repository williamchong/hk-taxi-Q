"""Whether the two carriageway-clearance instruments still describe one bundle (`Q51`).

`etl/pipeline/clearance.py` publishes a clear corridor width per station into
`city.json`, and `RoadGraph.is_routable` routes `P3-3`'s traffic on it.
`tools/carriageway_occupancy.py` grades the same bundle independently and reads a
different answer — **24 starved level-0 edges against 26**. `Q51` recorded that
gap rather than tuning it away, on the grounds that tuning one instrument toward
the other destroys the only thing a second one is for.

A recorded gap goes stale. Both figures are only evidence while they describe the
same bundle, and nothing could see one of them move: `check.sh` does not require a
built region, the pipeline reports its own number without failing, and the grader
fails for its own reasons. This is the missing half — one run, one bundle, both
numbers, and the per-edge table that says where they part.

**What it does not do.** It does not decide which instrument is right, and it has
no tolerance to argue about — because the two are wrong in *different dimensions*
and no single number reconciles those.

**In plan, both over-block, and the plan cell sets how much.** A cell blocks in
full as soon as one surface sample lands in it, so a wall smears by up to a cell
either side and a corridor bounded by two obstructions loses twice that again.
Brute-forcing `e132`'s own geometry — 109 M surface samples at 5 cm, independent
of both instruments — reproduces each tool's published width from nothing but its
own cell size; `carriageway_occupancy.INDEX_CELL_M` carries the figures. `--sweep`
reproduces it here by grading at each of the pipeline's own cells.

⚠️ **Along the edge the pipeline misses rather than over-blocks, and a miss is not
a bound at all.** ✅ **This tool found that, and it is fixed**: `ALONG_M` is `CELL_M`,
so an axis-aligned walk cannot stride over a cell it never samples. `e636` HARBOUR
ROAD — which the grader condemned and the pipeline cleared, because a wall stood
between two of its cross-sections — reads **0.00 m** and the two agree about it.
⚠️ **The bound holds at `CELL_M` and no finer**: a diagonal edge advances 0.35 m in
each axis per 0.50 m step and can corner-cross a cell without landing in it, which
is the one edge (`e520` TONNOCHY ROAD, 4.50 m against 2.50 m) a 0.25 m walk finds
and the shipped one does not. `pipeline.clearance.ALONG_M` carries the sweep.

So this is a **ratchet**, on `Q47`'s precedent: the counts are fixed outside the
instrument, from `Q51`, and any movement in either is a finding to go and look at
rather than a threshold to retune.

⚠️ **It reads the shipped bundle for the pipeline's side, never re-runs the
stage.** `city.json` is what the game loads and what `is_routable` answers from,
so a bundle whose `clear_width_m` no longer matches what the pipeline would
publish today is exactly the drift worth catching — re-running the stage here
would hide it.

Run:  .venv/bin/python tools/clearance_reconcile.py
      .venv/bin/python tools/clearance_reconcile.py --sweep
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import (  # noqa: E402
    ACROSS_M,
    INDEX_CELL_M,
    SAMPLE_M,
    SPACING_M,
    Lattice,
    band_map,
    index_classes,
    road_names,
    survey,
    walk_carriageway,
)
from deck_error import bundle_arguments, drawn_surface, load_bundle, log_bundle  # noqa: E402
from pipeline.clearance import ACROSS_M as PIPELINE_ACROSS_M  # noqa: E402
from pipeline.clearance import CELL_M, NOT_MEASURED  # noqa: E402
from pipeline.config import Config, load_config  # noqa: E402

log = logging.getLogger(__name__)

# `Q51`'s two figures, fixed there and not derived here. The whole point of a
# ratchet is that the instrument cannot move its own bar.
#
# ✅ **Moved by `P3-28`.** The carve cleared four of `Q19`'s seven licensed edges
# outright and narrowed the rest, so both counts fell by exactly the edges it
# cut — the ratchet reporting the work, rather than a bar retuned to fit it,
# which is the distinction the comment above exists to protect.
EXPECT_PIPELINE = 19
EXPECT_GRADER = 22
# Edges the two disagree about: 4 the grader condemns and the pipeline clears
# (`e99`, `e207`, `e485`, `e781`), plus `e702` the other way. ⚠️ **A single number
# here hides a swap** — `Q51` first said "five" where the split was 6 + 1, so read
# the per-side lists in the report rather than this total.
# ⚠️ `e485` joined the grader-only side at `P3-28`: the carve took its corridor to
# 2.90 m, which the pipeline reads as clear at its 0.5 m plan cell and the grader
# still condemns at its 1.0 m one. That is `Q51`'s gap doing exactly what `Q51`
# says it does, on one more edge.
EXPECT_DISAGREEMENT = 5

# Plan cells the sweep bins the grader's occupiers at: the grader's own shipped
# cell first, then the pipeline's plan cell and its across resolution — so the
# table reads as "the grader at each of the other instrument's resolutions".
#
# ⚠️ Element 0 is `INDEX_CELL_M` rather than a literal 1.0 for the same reason the
# grader's other knobs are imported: typed out, it would keep grading at 1.0 after
# the grader moved, the `(shipped)` label would be a lie, and `EXPECT_GRADER`
# would ratchet against settings nothing ships.
SWEEP_CELLS_M = (INDEX_CELL_M, CELL_M, PIPELINE_ACROSS_M)


def published(manifest: dict[str, Any]) -> dict[int, float]:
    """The pipeline's narrowest measured station per edge, as the bundle carries it.

    `manifest` *is* `city.json` — `load_bundle` parses it — so this reads what the
    game loads and what `is_routable` answers from, with no second opinion about
    where the numbers came from.

    `NOT_MEASURED` stations are filtered before the `min`, never clamped after:
    `-1.0` is the smallest number in any row it appears in, so folding it would
    make every part-trimmed edge the most blocked in the region. Deliberately a
    second implementation of `ClearanceReport.tightest` rather than a call to it —
    this grades what shipped, so sharing the fold would hide a bundle that
    disagrees with the code that wrote it. The *sentinel* is imported, because
    that is the document's contract rather than a measurement.
    """
    tightest: dict[int, float] = {}
    for entry in manifest.get("carriageway", []):
        widths = [
            float(width) for width in entry.get("clear_width_m", []) if float(width) != NOT_MEASURED
        ]
        if widths:
            tightest[int(entry["edge"])] = min(widths)
    return tightest


def grade(
    city: Config,
    generated: Path,
    manifest: dict[str, Any],
    tiles: list[Path],
    lattice: Lattice,
    bands: dict[tuple[int, int], tuple[float, float]],
    *,
    sample_m: float,
    cell_m: float,
) -> dict[int, float]:
    """One grader pass at one plan cell — its narrowest corridor per level-0 edge.

    ⚠️ **The lattice and the bands are passed in, not rebuilt.** Neither depends on
    `cell_m` — it reaches exactly one line, the plan bin in `index_corners` — and
    `walk_carriageway` is **20.0 s of a 26.6 s pass**, so rebuilding it per cell
    made `--sweep` 79.9 s where it is now 38.7 s. The grader's own `main` carries
    the same note about the same walk. It is also what makes it *structurally*
    true that every pass grades the same carriageway, which is the tool's claim.
    """
    return survey(
        lattice,
        index_classes(city, generated, manifest, tiles, bands, sample_m=sample_m, cell_m=cell_m),
    ).corridor_m


# How an edge reads, by which instruments condemn it. A lookup rather than nested
# ternaries, and one spelling per side — the table, the summary and the FAIL text
# all name them the same way, so a reader can grep the log for one word.
_VERDICT = {
    (True, True): "agree",
    (False, False): "agree",
    (True, False): "grader-only",
    (False, True): "pipeline-only",
}


def starved(widths: dict[int, float], bar_m: float) -> set[int]:
    return {edge_id for edge_id, width in widths.items() if width < bar_m}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        parents=[bundle_arguments()],
        description="Whether the two clearance instruments still describe one bundle (Q51).",
    )
    # Defaults imported from the grader, never re-typed: this tool ratchets `Q51`'s
    # counts, and grading at settings the grader no longer ships would move them
    # for a reason no reader of the failure could see.
    parser.add_argument(
        "--spacing-m", type=float, default=SPACING_M, help="station spacing along an edge"
    )
    parser.add_argument(
        "--across-m", type=float, default=ACROSS_M, help="cell width across the ribbon"
    )
    parser.add_argument(
        "--sample-m", type=float, default=SAMPLE_M, help="how densely each triangle is sampled"
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        # Off by default because it is three grader passes rather than one, and
        # the ratchet above is what a routine run is for. On, it reproduces the
        # measurement in the module docstring.
        help="also grade at the pipeline's plan cells, to price the gap",
    )
    parser.add_argument(
        "--expect-pipeline",
        type=int,
        default=EXPECT_PIPELINE,
        help="Q51's starved count for the bundle",
    )
    parser.add_argument(
        "--expect-grader",
        type=int,
        default=EXPECT_GRADER,
        help="Q51's starved count for the grader",
    )
    parser.add_argument(
        "--expect-disagreement",
        type=int,
        default=EXPECT_DISAGREEMENT,
        help="Q51's count of edges the two disagree about, in either direction",
    )
    args = parser.parse_args(argv)

    city = load_config()
    bar_m = float(city.roads.lane_width_m)
    manifest, tiles = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)
    log.info("clearance reconciliation, lod %d", args.lod)
    log.info("  one lane is %.2f m. In plan both instruments over-block, and the plan", bar_m)
    log.info("  cell sets how much; along the edge the pipeline samples at its own cell")
    log.info("  pitch, so it no longer misses on axis — see the module docstring. A diagonal")
    log.info("  edge can still corner-cross a cell, so its bound holds at CELL_M and no finer.")

    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    drawn = drawn_surface(args.generated, manifest)
    names = road_names(graph)

    pipeline = published(manifest)

    # Walked once and shared by every pass — see `grade`. The refusal is the
    # grader's own, and it has to be here rather than left to an empty result: a
    # lattice with no drawn carriageway yields no starved edges at all, which this
    # tool would otherwise report as "the grader's count has moved to 0".
    lattice = walk_carriageway(
        graph,
        manifest,
        drawn,
        spacing_m=args.spacing_m,
        across_m=args.across_m,
        attribute_within_m=args.attribute_within_m,
    )
    if not lattice.drawn.any():
        raise SystemExit(
            "no drawn carriageway could be found — is the road mesh present, and does "
            "city.json still name it?"
        )
    bands = band_map(lattice)

    passes = {
        cell_m: grade(
            city,
            args.generated,
            manifest,
            tiles,
            lattice,
            bands,
            sample_m=args.sample_m,
            cell_m=cell_m,
        )
        for cell_m in (SWEEP_CELLS_M if args.sweep else SWEEP_CELLS_M[:1])
    }
    grader = passes[SWEEP_CELLS_M[0]]

    pipeline_set = starved(pipeline, bar_m)
    grader_set = starved(grader, bar_m)
    grader_only = sorted(grader_set - pipeline_set)
    pipeline_only = sorted(pipeline_set - grader_set)

    log.info("")
    log.info("  narrowest corridor on every edge either instrument condemns:")
    log.info("    'delta' is pipeline minus grader; positive means the pipeline sees more room")
    log.info(
        "    %-7s %8s %8s %8s  %-13s %s", "edge", "grader", "pipeline", "delta", "verdict", "name"
    )
    for edge_id in sorted(grader_set | pipeline_set, key=lambda key: grader.get(key, float("inf"))):
        grader_m = grader.get(edge_id)
        pipeline_m = pipeline.get(edge_id)
        if grader_m is None or pipeline_m is None:
            # One instrument never judged this edge at all, which is a different
            # defect from disagreeing about it and must not read as a delta.
            log.warning("    e%-6d %s", edge_id, "judged by only one instrument")
            continue
        log.info(
            "    e%-6d %8.2f %8.2f %+8.2f  %-13s %s",
            edge_id,
            grader_m,
            pipeline_m,
            pipeline_m - grader_m,
            _VERDICT[edge_id in grader_set, edge_id in pipeline_set],
            names.get(edge_id, "unnamed"),
        )

    log.info("")
    log.info(
        "  %d starved by the pipeline, %d by the grader; %d disagreements "
        "(%d grader-only, %d pipeline-only)",
        len(pipeline_set),
        len(grader_set),
        len(grader_only) + len(pipeline_only),
        len(grader_only),
        len(pipeline_only),
    )
    log.info("    grader-only   %s", ", ".join(f"e{edge_id}" for edge_id in grader_only) or "none")
    log.info(
        "    pipeline-only %s", ", ".join(f"e{edge_id}" for edge_id in pipeline_only) or "none"
    )

    if args.sweep:
        log.info("")
        log.info("  the grader at each plan cell — this is the gap, priced:")
        for cell_m, widths in passes.items():
            log.info(
                "    %.2f m cells  %3d starved%s",
                cell_m,
                len(starved(widths, bar_m)),
                "   (shipped)" if cell_m == SWEEP_CELLS_M[0] else "",
            )
        log.info(
            "    the pipeline publishes %d, measured in %.2f m cells", len(pipeline_set), CELL_M
        )

    problems = []
    for label, found, expected in (
        ("the pipeline's", len(pipeline_set), args.expect_pipeline),
        ("the grader's", len(grader_set), args.expect_grader),
        ("their", len(grader_only) + len(pipeline_only), args.expect_disagreement),
    ):
        if found != expected:
            problems.append(
                f"{label} starved count is {found}, where Q51 records {expected} — "
                "one of the two has moved, and the recorded gap no longer describes this bundle"
            )

    if problems:
        log.error("")
        for problem in problems:
            log.error("  FAIL  %s", problem)
        return 1

    log.info("")
    log.info("  Both instruments still read what Q51 recorded over this bundle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
