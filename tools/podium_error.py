"""How far the survey's floors→metres conversion lands from the data boundary (`R4`, `Q47`).

`Q47`'s call made the iB1000 tower↔block join `R4`'s validation set: where the
survey will supply a podium boundary, its floors→metres conversion is graded
against the 310 stems whose boundary came from data, **before anything packs**.
The bar — pools, thresholds, the executable pitch spec — was fixed in
`docs/DECISIONS.md` under `Q47` before this tool existed, and the `--accept-*`
defaults below are that record's numbers, not this module's opinion.

This is not a `deck_error.py`-style re-measurement — the join has its own
pinned acceptance test (`test_podiums.py`), and re-deriving `boundary_m` here
would only measure whether it was written down correctly. What this tool does
is compare **two instruments that share nothing but the stem key and a
government survey lineage**:

| | the data side | the survey side |
|---|---|---|
| Instrument | iB1000 `P`-block levels, joined by geometry | vision reader over the unwraps |
| Boundary | `boundary_m` as written, never recomputed | floors x reconciled pitch, computed here |
| Certainty | iB1000 `CERTAINTY`, unanimous over a stitch | readable faces, strict-majority vote |
| Height | `ROOFLEVEL` minus the mesh's own base | the survey's `height_m` over visible storeys |

It reads an ETL intermediate rather than the shipped bundle, unlike the three
graders `ARCHITECTURE.md` registers: `podiums.json` never ships and its
provenance is ETL-side by `Q47`'s contract point (iii), so there is no shipped
artefact to grade yet — "a stage cannot mark its own work" is satisfied here by
instrument independence, not bundle reading. The shipped boundary owes its own
grade after the pack.

⚠️ Four things are *not* independent, and saying so is the point. The document
is read through `pipeline.documents.read_document` with the stage's own name
and schema constants (`deck_error`'s `CITY_SCHEMA` precedent) — a version gate,
not a measurement. `_majority` is imported from the reader tool — the vote *is*
the conversion's spec, and the reader tool is not the stage under grade.
`heights()` comes from `ring_weights` — the survey's own height column. And the
conversion computed here is shared with `R4`'s future pack **by design**: it is
the object under test, and this module's definition is normative for the pack.
The confessed deviation: per-face heights exist only at unwrap time, so each
face's pitch divides the *building* height by that face's `storey_count` — the
median over faces keeps the face-disagreement signal, the numerator does not.

Run:  .venv/bin/python tools/podium_error.py --region wan_chai
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(ROOT / "tools"))

from facade_grammar import SURVEY_SOURCE_ID, _majority  # noqa: E402
from facade_survey import claim_stems  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.documents import read_document  # noqa: E402
from pipeline.fetch import source_dir  # noqa: E402
from pipeline.podiums import PODIUMS_NAME, PODIUMS_SCHEMA  # noqa: E402
from ring_weights import heights  # noqa: E402

log = logging.getLogger(__name__)

# The reconciled-pitch window and grid, from the vertex contract: bits 0-6
# carry `2.5 + (k-1)/32` m over `Q42`'s 2.5-4.5 m sanity window
# (`ARCHITECTURE.md` "Tile output"). A committed pitch is quantised to that
# grid so the graded conversion is byte-for-byte the future packed one; the
# fallback is *not* quantised, because refusal packs no pitch — the shader
# uniform is the fallback, and 2.8 is not even on the grid (k-1 = 9.6).
_PITCH_MIN_M = 2.5
_PITCH_MAX_M = 4.5
_PITCH_STEPS_PER_M = 32


@dataclass(frozen=True)
class Graded:
    """One boundary stem's grade — every asked stem gets one.

    ⚠️ A stem the survey never covered still lands here, with a `None` verdict:
    the coverage pool divides by every certain row, so a missing survey row
    counts against coverage instead of silently shrinking the denominator —
    `deck_error._Samples`' lesson, kept without the numpy.
    """

    stem: str
    certain: bool
    boundary_m: float
    verdict: int | None
    pitch_m: float
    committed: bool
    error_m: float | None


def survey_rows(root: Path | None = None) -> dict[str, dict]:
    """Per-building face rows, merged from the per-sheet grammar tables.

    The per-sheet tables, not `facade_grammar.json`: the merged table reduces
    to the voted `glazed`/`grammar` verdicts and carries no podium fields.
    `claim_stems` keeps the merge honest the same way the survey writers do.
    """
    directory = source_dir(SURVEY_SOURCE_ID, root=root)
    merged: dict[str, dict] = {}
    for path in sorted(directory.glob("facade_grammar.*.json")):
        rows = json.loads(path.read_text(encoding="utf-8"))
        claim_stems(merged, rows, path.name)
        merged.update(rows)
    return merged


def reconciled_pitch(
    faces: dict[str, dict], height_m: float | None, fallback_m: float
) -> tuple[float, bool]:
    """`(pitch_m, committed)` — the bar's executable spec, normative for the pack.

    Median over readable faces of building height ÷ that face's visible
    `storey_count`; committed iff the median lands in the window, quantised to
    the grid; everything else refuses to the fallback, unquantised.
    """
    counts = [
        face["storey_count"]
        for face in faces.values()
        if face["readable"] and (face["storey_count"] or 0) >= 1
    ]
    if height_m is None or not counts:
        return fallback_m, False
    median = statistics.median(height_m / count for count in counts)
    if not _PITCH_MIN_M <= median <= _PITCH_MAX_M:
        return fallback_m, False
    steps = round((median - _PITCH_MIN_M) * _PITCH_STEPS_PER_M)
    return _PITCH_MIN_M + steps / _PITCH_STEPS_PER_M, True


def podium_verdict(faces: dict[str, dict]) -> int | None:
    """Strict-majority podium floors over readable faces; `None` is refusal.

    Null votes an explicit 0 — "no podium", the commitment the prompt's "null
    if none" makes and the codec's `k = 1` encodes. The mapping is load-bearing:
    fed raw, `_majority` would return `None` for a no-podium majority and for a
    tie alike, and Pool B would be indistinguishable from refusal.
    """
    votes: list[int] = [face["podium_floors"] or 0 for face in faces.values() if face["readable"]]
    if any(vote < 0 for vote in votes):
        # A negative winning verdict would land in neither pool while still
        # counting against coverage — a row that quietly disappears from the
        # decided count. A survey-writer defect raises, per `claim_stems`.
        raise ValueError(f"negative podium_floors among votes {votes}")
    verdict = _majority(votes)
    return None if verdict is None else int(verdict)


def grade(
    rows: dict[str, dict],
    survey: dict[str, dict],
    height_by_stem: dict[str, float],
    fallback_m: float,
) -> tuple[list[Graded], list[str]]:
    """Every asked stem graded, plus the stems the survey never covered."""
    graded: list[Graded] = []
    unmatched: list[str] = []
    for key, row in sorted(rows.items()):
        entry = survey.get(key)
        if entry is None:
            unmatched.append(key)
            graded.append(
                Graded(key, row["certain"], row["boundary_m"], None, fallback_m, False, None)
            )
            continue
        faces = entry["faces"]
        pitch, committed = reconciled_pitch(faces, height_by_stem.get(key), fallback_m)
        verdict = podium_verdict(faces)
        error = verdict * pitch - row["boundary_m"] if verdict else None
        graded.append(
            Graded(key, row["certain"], row["boundary_m"], verdict, pitch, committed, error)
        )
    return graded, unmatched


def pools(graded: list[Graded]) -> tuple[list[Graded], list[Graded], list[Graded]]:
    """`(certain, pool_a, pool_b)` — disjoint, over certain rows only.

    The 19-in-today's-region uncertain rows are reported beside the pools and
    never inside them: `certain` survives stitching only unanimously, so they
    are exactly the rows whose polygon the source doubts.
    """
    certain = [row for row in graded if row.certain]
    pool_a = [row for row in certain if row.verdict is not None and row.verdict >= 1]
    pool_b = [row for row in certain if row.verdict == 0]
    return certain, pool_a, pool_b


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True, help="region id under etl/out")
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    parser.add_argument(
        "--fallback-pitch-m",
        type=float,
        default=2.8,
        help="pitch where the survey refuses: P3-7's measured 2.77 m as shipped "
        "in the shader's floor_height_m uniform (default 2.8)",
    )
    parser.add_argument(
        "--accept-p50-m",
        type=float,
        default=2.8,
        help="Pool A |error| median ceiling: one reader floor is one pitch, so "
        "beating one pitch is being within ±1 floor (default 2.8)",
    )
    parser.add_argument(
        "--accept-p90-m",
        type=float,
        default=7.0,
        help="Pool A |error| p90 ceiling: two miscounted floors plus the "
        "half-pitch quantisation floor, 2 x 2.8 + 1.4 (default 7.0)",
    )
    parser.add_argument(
        "--min-pool",
        type=int,
        default=100,
        help="Pool A minimum n — the gate that keeps the headline from passing "
        "vacuously (default 100)",
    )
    parser.add_argument(
        "--accept-null-rate",
        type=float,
        default=1.0 / 3.0,
        help="Pool B ceiling: share of decided certain rows where the survey "
        "says no podium against a data boundary (default 1/3)",
    )
    parser.add_argument(
        "--accept-verdict-rate",
        type=float,
        default=0.60,
        help="Pool C floor: share of certain rows yielding any majority verdict (default 0.60)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    rebuild = f"cd etl && python -m pipeline --region {args.region}"
    try:
        document = read_document(
            city.out_dir(args.region, args.out_root) / PODIUMS_NAME, PODIUMS_SCHEMA, rebuild
        )
    except (FileNotFoundError, ValueError) as broken:
        raise SystemExit(str(broken)) from None

    survey = survey_rows(root=args.sources_root)
    graded, unmatched = grade(
        document["buildings"], survey, heights(city, root=args.sources_root), args.fallback_pitch_m
    )
    certain, pool_a, pool_b = pools(graded)

    join, stitch = document["join"], document["stitch"]
    log.info(
        "%s / %s, %s schema %d",
        document["city_id"],
        document["region_id"],
        PODIUMS_NAME,
        document["schema_version"],
    )
    log.info(
        "  stitch: %d pieces, %d groups across a cut; join: %d pairs, %d exact level meets "
        "(aggregate; a row does not identify its meet)",
        stitch["pieces"],
        stitch["cross_sheet_groups"],
        join["pairs"],
        join["exact_level_meets"],
    )
    log.info(
        "  %d stems asked, %d certain, %d without a survey row",
        len(graded),
        len(certain),
        len(unmatched),
    )

    committed = [row.pitch_m for row in graded if row.committed]
    log.info("")
    log.info(
        "  reconciled pitch (window %.1f-%.1f m, 1/%d m grid, fallback %.2f):",
        _PITCH_MIN_M,
        _PITCH_MAX_M,
        _PITCH_STEPS_PER_M,
        args.fallback_pitch_m,
    )
    if committed:
        log.info(
            "    committed %d of %d, p10/p50/p90  %.2f / %.2f / %.2f",
            len(committed),
            len(graded),
            *np.percentile(committed, [10, 50, 90]),
        )
    else:
        log.info("    committed 0 of %d — every building graded on the fallback", len(graded))

    errors = np.array([row.error_m for row in pool_a], dtype=np.float64)
    absolute = np.abs(errors)
    log.info("")
    log.info(
        "  Pool A — metres (certain, majority >= 1 floor): n=%d (gate %d)",
        len(pool_a),
        args.min_pool,
    )
    if len(pool_a):
        p50 = float(np.percentile(absolute, 50))
        p90 = float(np.percentile(absolute, 90))
        log.info("    floors x pitch minus boundary_m, signed:")
        log.info("    median   %+.2f", float(np.median(errors)))
        log.info("    p10/p90  %+.2f / %+.2f", *np.percentile(errors, [10, 90]))
        log.info("    |err|p50 %.2f   (accepts %.2f)", p50, args.accept_p50_m)
        log.info("    |err|p90 %.2f   (accepts %.2f)", p90, args.accept_p90_m)
        half_pitch = args.fallback_pitch_m / 2.0
        log.info(
            "    within half a pitch (%.2f m): %.1f%%",
            half_pitch,
            100.0 * float((absolute <= half_pitch).mean()),
        )
    else:
        # No sentinel: an empty pool is the gate's failure to report, and
        # "p50 is inf m" would be the sentinel talking, not the data.
        p50 = p90 = None

    decided = len(pool_a) + len(pool_b)
    null_rate = len(pool_b) / decided if decided else 0.0
    verdict_rate = decided / len(certain) if certain else 0.0
    log.info("")
    log.info(
        "  Pool B — semantic (certain, majority says no podium): n=%d, %.1f%% of %d decided "
        "  (accepts <= %.1f%%)",
        len(pool_b),
        100.0 * null_rate,
        decided,
        100.0 * args.accept_null_rate,
    )
    log.info(
        "  Pool C — coverage: %d/%d certain rows decided, %.1f%%   (accepts >= %.1f%%)",
        decided,
        len(certain),
        100.0 * verdict_rate,
        100.0 * args.accept_verdict_rate,
    )

    uncertain = [row for row in graded if not row.certain]
    doubted = [row.error_m for row in uncertain if row.error_m is not None]
    log.info("")
    log.info(
        "  uncertain rows, reported never pooled: %d, %d with a floors verdict, |err| p50 %s",
        len(uncertain),
        len(doubted),
        f"{float(np.percentile(np.abs(doubted), 50)):.2f}" if doubted else "-",
    )

    worst = sorted(pool_a, key=lambda row: -abs(row.error_m))[:5]
    if worst:
        log.info("")
        log.info("  worst misses, for adjudication:")
        for row in worst:
            log.info(
                "    %s  %d floors x %.2f = %5.2f against %5.2f  (%+.2f, %s pitch)",
                row.stem,
                row.verdict,
                row.pitch_m,
                row.verdict * row.pitch_m,
                row.boundary_m,
                row.error_m,
                "committed" if row.committed else "fallback",
            )

    problems = []
    if len(pool_a) < args.min_pool:
        problems.append(f"Pool A holds {len(pool_a)} stems against the {args.min_pool} gate")
    if p50 is not None and p50 > args.accept_p50_m:
        problems.append(f"Pool A |error| p50 is {p50:.2f} m against {args.accept_p50_m:.2f}")
    if p90 is not None and p90 > args.accept_p90_m:
        problems.append(f"Pool A |error| p90 is {p90:.2f} m against {args.accept_p90_m:.2f}")
    if null_rate > args.accept_null_rate:
        problems.append(
            f"Pool B: the survey sees no podium on {100.0 * null_rate:.1f}% of decided "
            f"certain rows, against {100.0 * args.accept_null_rate:.1f}%"
        )
    if verdict_rate < args.accept_verdict_rate:
        problems.append(
            f"Pool C: only {100.0 * verdict_rate:.1f}% of certain rows decided, "
            f"against {100.0 * args.accept_verdict_rate:.1f}%"
        )
    if problems:
        log.error("")
        for problem in problems:
            log.error("  FAIL  %s", problem)
        return 1

    log.info("")
    log.info("  R4 grading bar met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
