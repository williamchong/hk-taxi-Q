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
    CORRIDOR_LEVELS,
    INDEX_CELL_M,
    SAMPLE_M,
    SPACING_M,
    Lattice,
    _levels_argument,
    _levels_label,
    band_map,
    edge_levels,
    index_classes,
    road_names,
    survey,
    walk_carriageway,
)
from deck_error import bundle_arguments, drawn_surface, load_bundle, log_bundle  # noqa: E402
from pipeline.clearance import ACROSS_M as PIPELINE_ACROSS_M  # noqa: E402
from pipeline.clearance import CELL_M, LEVELS, NOT_MEASURED  # noqa: E402
from pipeline.config import Config, load_config  # noqa: E402

log = logging.getLogger(__name__)

# `Q51`'s two figures, fixed there and not derived here. The whole point of a
# ratchet is that the instrument cannot move its own bar.
#
# ✅ **Moved by `P3-28`.** The carve cleared four of `Q19`'s seven licensed edges
# outright and narrowed the rest, so both counts fell by exactly the edges it
# cut — the ratchet reporting the work, rather than a bar retuned to fit it,
# which is the distinction the comment above exists to protect.
#
# ✅ **Moved again by `Q19`'s `e99` carve (2026-09-01), and only on the grader's
# side.** `EXPECT_PIPELINE` does **not** move: `e99` read 4.50 m at the
# pipeline's 0.5 m plan cell before the cut, so it was never in that count —
# which is the whole reason a width bar could not reach the defect that stranded
# the car there. The grader condemned it at 2.93 m on its 1.0 m cell and now
# does not, so `EXPECT_GRADER` falls 22 → 21 and the disagreement 5 → 4 by
# exactly that one edge. Both halves are `Q51`'s gap being read, not closed.
# ✅ **Moved again on 2026-09-04, by the LEVEL and not by the city.** Both
# instruments now judge level 1 as well as level 0, so both counts grew by the
# off-grade edges they condemn: the grader by 4 (`e208`, `e257`, `e306`,
# `e450`) and the pipeline by 2 (`e208`, `e306`). 🔴 **The at-grade halves are
# unchanged — 21 and 19, exactly what stood here before** — which is what makes
# this the population arriving rather than a bar retuned to fit it. If a future
# move cannot say that, it is not this kind of move.
EXPECT_PIPELINE = 21
EXPECT_GRADER = 25
# Edges the two disagree about: 3 the grader condemns and the pipeline clears
# (`e207`, `e485`, `e781`), plus `e702` the other way. ⚠️ `e99` left this list at
# its own carve — it was the largest of the grader-only gaps at 1.57 m. ⚠️ **A single number
# here hides a swap** — `Q51` first said "five" where the split was 6 + 1, so read
# the per-side lists in the report rather than this total.
# ⚠️ `e485` joined the grader-only side at `P3-28`: the carve took its corridor to
# 2.90 m, which the pipeline reads as clear at its 0.5 m plan cell and the grader
# still condemns at its 1.0 m one. That is `Q51`'s gap doing exactly what `Q51`
# says it does, on one more edge.
# ✅ **4 -> 6 on 2026-09-04**, and the two new ones are both grader-only and
# both off-grade: `e257` and `e450`, CANAL ROAD FLYOVER. The at-grade four are
# untouched. ⚠️ The gap widens off-grade for the reason it widens anywhere — the
# grader's 1.0 m plan cell against the pipeline's 0.5 m — and a viaduct's
# parapet is thin in plan, so it is the shape of edge that gap is largest on.
EXPECT_DISAGREEMENT = 6

# Plan cells the sweep bins the grader's occupiers at: the grader's own shipped
# cell first, then the pipeline's plan cell and its across resolution — so the
# table reads as "the grader at each of the other instrument's resolutions".
#
# ⚠️ Element 0 is `INDEX_CELL_M` rather than a literal 1.0 for the same reason the
# grader's other knobs are imported: typed out, it would keep grading at 1.0 after
# the grader moved, the `(shipped)` label would be a lie, and `EXPECT_GRADER`
# would ratchet against settings nothing ships.
SWEEP_CELLS_M = (INDEX_CELL_M, CELL_M, PIPELINE_ACROSS_M)


def published(
    manifest: dict[str, Any], *, level_of: dict[int, int], walked: tuple[int, ...]
) -> dict[int, float]:
    """The pipeline's narrowest measured station per edge, as the bundle carries it.

    `manifest` *is* `city.json` — `load_bundle` parses it — so this reads what the
    game loads and what `is_routable` answers from, with no second opinion about
    where the numbers came from.

    🔴 **Filtered to `walked`, because the grader's half is.** This read every
    row in the document until 2026-09-04, which was the same population while
    the pipeline published level 0 alone and stopped being one the moment it
    published level 1: the three off-grade starved edges would have landed in
    `pipeline_set` with no grader row opposite them, printing three
    `judged by only one instrument` lines and moving `EXPECT_PIPELINE` for
    something that is not a disagreement. A ratchet on two populations is not a
    ratchet. ⚠️ **The filter is the graph's `elevation_level` and not the
    document's** — `city.json`'s `carriageway[]` does not carry one. The two
    filter arguments are keyword-only: they are both about levels and neither
    reads as the other's position.

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
        edge_id = int(entry["edge"])
        if level_of[edge_id] not in walked:
            continue
        widths = [
            float(width) for width in entry.get("clear_width_m", []) if float(width) != NOT_MEASURED
        ]
        if widths:
            tightest[edge_id] = min(widths)
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
    levels: tuple[int, ...],
) -> dict[int, float]:
    """One grader pass at one plan cell — its narrowest corridor per edge walked.

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
        # 🔴 **Passed, never left to the grader's own default.** The two halves
        # of this tool have to walk one population or the comparison below is
        # between two different questions — which is the whole claim the tool
        # makes, and it survived only by accident while both defaults were
        # level 0.
        corridor_levels=levels,
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
        "--levels",
        type=_levels_argument,
        default=CORRIDOR_LEVELS,
        # 🔴 **One flag reaching BOTH halves**, which is the only shape that
        # keeps this a reconciliation. Defaulted from the grader's constant and
        # asserted below against the pipeline's, so the routine run grades the
        # population the bundle publishes and a reader cannot silently compare
        # a level-0 grader against an all-levels document.
        help=(
            "comma-separated elevation levels both instruments judge "
            "(default: the levels the bundle publishes)"
        ),
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
    if tuple(args.levels) != LEVELS:
        # ⚠️ **A warning and not a refusal.** Grading a level the bundle does
        # not publish is a real thing to want — it is how level 1 was read
        # before it shipped — but the counts it produces are not `Q51`'s, and
        # the ratchet below would fail for a reason that is the reader's own.
        log.warning(
            "  --levels %s, but the bundle is published over %s — the counts below are not "
            "Q51's and the expectations will not hold",
            _levels_label(args.levels),
            _levels_label(LEVELS),
        )
    # The grader's labeller and not a join of this file's own: `pipeline/clearance.py`
    # spells a level set `0/1` and the grader spells it `+0,+1`, and a tool whose
    # whole job is showing that two instruments judge one population is the last
    # place to print a third spelling of which population that is.
    log.info("  both instruments judge level(s) %s", _levels_label(args.levels))
    log.info("  one lane is %.2f m. In plan both instruments over-block, and the plan", bar_m)
    log.info("  cell sets how much; along the edge the pipeline samples at its own cell")
    log.info("  pitch, so it no longer misses on axis — see the module docstring. A diagonal")
    log.info("  edge can still corner-cross a cell, so its bound holds at CELL_M and no finer.")

    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    drawn = drawn_surface(args.generated, manifest)
    names = road_names(graph)

    pipeline = published(manifest, level_of=edge_levels(graph), walked=args.levels)

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
            levels=args.levels,
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
