"""Is an off-grade edge still held level in the air where its structure stops (`Q90`)?

`INFRASTRUCTURE` stops being modelled where a ramp reaches grade, so the last
stretch of every touchdown is uncovered. `roads.py` ramps the ribbon down to the
node across that gap; before `Q90` it clamped, and 24 m of `FLEMING ROAD` stood
1.83 m above the street it lands on.

Why this is a separate tool rather than a number the road stage prints — the
reason `deck_error.py` gives, at the one place that tool cannot reach. **Where
the structure is absent there is nothing to measure against**, so a clamped end
is *uncovered* to `deck_error` rather than wrong, and its `--accept-measured`
share is the only place it registers at all. Nothing here is shared with the code
it grades:

| | the pipeline | this tool |
|---|---|---|
| Structure geometry | source sheets, full density | **shipped tiles**, decimated and welded |
| Which class is structure | sub-directory in the sheet zip | **vertex colour** |
| Where the hole is | `sample_along`'s slab clustering | **any upward face** over the station |
| That a ribbon was clamped | — | **bit-identical `y`** in the published polyline |

The last row is the point. A run of equal heights at an edge end is the only
thing `np.interp` can leave outside its range, so the clamp is readable from
`roadgraph.json` with no reference to the structure at all — and the hole is
readable from the tiles with no reference to the ribbon. The two agreeing to the
metre is what made `Q90` a mechanism rather than a reading, and it is what this
tool re-checks on every build.

⚠️ **The two reads are allowed to disagree by about a station.** `P2-1`
decimates `INFRASTRUCTURE` on a 0.5 m cell, so the tiles lose the deck's own
edge where the sheets still carry it; four of the region's ends show a one-station
tile gap the pipeline never saw. That is why a disagreement is reported rather
than failed on, and why the bar below is one-sided.

Run:  .venv/bin/python tools/touchdown_error.py --city hong_kong
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
sys.path.insert(0, str(ROOT / "tools"))

from deck_error import bundle_arguments, load_bundle, log_bundle, structure_faces  # noqa: E402
from pipeline.config import load_city  # noqa: E402

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class End:
    """One off-grade edge end whose structure stops before the node."""

    edge: int
    end: str
    node: int
    road: str
    clamped_m: float
    hole_m: float
    step_m: float
    grade_pct: float

    @property
    def has_step(self) -> bool:
        """Whether there is an at-grade edge here to measure a step against."""
        return bool(np.isfinite(self.step_m))

    def should_descend(self, cap_pct: float) -> bool:
        """Whether the published ribbon should have been ramped to the node.

        `grade_pct` is measured off the *drawn* ribbon rather than read back
        from the pipeline, so this is the tool's own verdict on the config's
        bar and not a restatement of it.

        One method rather than a predicate written twice, once negated: the
        refusals are its complement, and two comprehensions can drift apart.
        `_grade` returns infinity for every end with no street to land on and no
        run to climb, so those fail this test without needing a term of their
        own.
        """
        return bool(self.grade_pct <= cap_pct)


def covered(deck: Any, points: np.ndarray) -> np.ndarray:
    """Which stations have any upward structure face over them."""
    return np.array(
        [bool(np.isfinite(deck.heights_at(float(p[0]), float(p[2]))).any()) for p in points]
    )


def clamped_run(heights: np.ndarray) -> int:
    """Stations at an end sharing the first one's exact height.

    Exact rather than within a tolerance, deliberately: a clamp writes one float
    into every station of the run, and a *near*-equal run is a real gradient that
    happens to be shallow. Widening this would report a flat deck as a defect.
    """
    run = 1
    while run < len(heights) and heights[run] == heights[0]:
        run += 1
    return run


def ends_of(graph: dict[str, Any], deck: Any) -> list[End]:
    """Every off-grade edge end the structure stops short of."""
    at_node: dict[int, list[tuple[int, float]]] = {}
    for edge in graph["edges"]:
        for node, height in (
            (edge["from"], edge["polyline"][0][1]),
            (edge["to"], edge["polyline"][-1][1]),
        ):
            at_node.setdefault(node, []).append((edge["elevation_level"], height))

    found: list[End] = []
    for edge in graph["edges"]:
        if edge["elevation_level"] <= 0:
            continue
        points = np.array(edge["polyline"], float)
        cover = covered(deck, points)
        steps = np.hypot(np.diff(points[:, 0]), np.diff(points[:, 2]))
        for name, node, order in (("from", edge["from"], 1), ("to", edge["to"], -1)):
            heights, seen = points[::order, 1], cover[::order]
            spans = steps[::order]
            if seen[0]:
                continue
            gap = int(np.argmax(seen)) if seen.any() else len(seen)
            # The at-grade side of the node, which is what a touchdown lands on.
            # A node no other level reaches is a clipped region boundary and
            # there is no street there to descend to.
            grade = [y for level, y in at_node[node] if level == 0]
            hole_m = float(spans[:gap].sum())
            run = clamped_run(heights)
            found.append(
                End(
                    edge=edge["id"],
                    end=name,
                    node=node,
                    road=edge["road_name"]["en"] or "(unnamed)",
                    clamped_m=float(spans[: run - 1].sum()),
                    hole_m=hole_m,
                    step_m=float(heights[0]) - min(grade) if grade else float("nan"),
                    grade_pct=_grade(heights, gap, hole_m, grade),
                )
            )
    return found


def _grade(heights: np.ndarray, gap: int, hole_m: float, grade: list[float]) -> float:
    """The grade a ramp to the node would have to climb, or infinity.

    Infinity where there is no street to land on, no covered station to climb
    to, or no run to climb over — three different reasons a descent cannot be
    reconstructed, all of which make the same claim about this end: not that it
    is steep, but that this tool cannot say it is shallow.
    """
    if not grade or gap >= len(heights) or hole_m <= 0.0:
        return float("inf")
    return abs(float(heights[gap]) - min(grade)) / hole_m * 100.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    if city.roads.deck is None:
        raise SystemExit(f"city '{args.city}' samples no decks — nothing to grade")
    cap = city.roads.deck.touchdown_max_grade_pct

    manifest, tiles = load_bundle(args.generated, args.lod, args.city)
    log_bundle(manifest, args.lod)
    deck, structure_class = structure_faces(city, tiles)
    graph = json.loads((args.generated / manifest["road_graph"]).read_text(encoding="utf-8"))

    found = ends_of(graph, deck)
    off_grade = sum(2 for edge in graph["edges"] if edge["elevation_level"] > 0)
    log.info(
        "  %d upward faces of '%s'; %d of %d off-grade edge ends have no structure at the node",
        len(deck.corners),
        structure_class,
        len(found),
        off_grade,
    )
    if not found:
        raise SystemExit("no off-grade end lacks structure — the tiles cannot be right")

    log.info("")
    log.info(
        "  %-5s %-4s %-5s %8s %8s %8s %8s  %s",
        "edge",
        "end",
        "node",
        "clamp m",
        "hole m",
        "step m",
        "grade %",
        "road",
    )
    for end in sorted(found, key=lambda e: -abs(e.step_m) if e.has_step else 0.0):
        log.info(
            "  e%-4d %-4s %-5d %8.1f %8.1f %8s %8s  %s",
            end.edge,
            end.end,
            end.node,
            end.clamped_m,
            end.hole_m,
            f"{end.step_m:+.2f}" if end.has_step else "—",
            f"{end.grade_pct:.1f}" if np.isfinite(end.grade_pct) else "—",
            end.road,
        )

    # The bar, and it is one-sided on purpose. A ribbon still clamped over a hole
    # it could have been ramped across is `Q90`'s defect returning, and it
    # renders as a flyover afloat over the street. A ribbon left clamped where
    # the grade is over the cap is the refusal working.
    log.info("")
    clamped = [e for e in found if e.clamped_m > 0.0]
    missed = [e for e in clamped if e.should_descend(cap)]
    refused = [e for e in clamped if not e.should_descend(cap)]
    log.info(
        "  %d ends still clamped: %d refused over the %.1f%% cap or with no street to land on, "
        "%d that should have descended",
        len(clamped),
        len(refused),
        cap,
        len(missed),
    )
    for end in refused:
        log.info(
            "    refused: e%d at node %d, %s — %s",
            end.edge,
            end.node,
            end.road,
            f"{end.grade_pct:.1f}% over {end.hole_m:.1f} m"
            if np.isfinite(end.grade_pct)
            else "no at-grade edge at the node",
        )
    if missed:
        for end in missed:
            log.error(
                "  e%d %s at node %d is clamped %.1f m at %.1f%%, inside the %.1f%% cap",
                end.edge,
                end.end,
                end.node,
                end.clamped_m,
                end.grade_pct,
                cap,
            )
        return 1
    log.info("  PASS: every reconstructable touchdown reaches its node")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
