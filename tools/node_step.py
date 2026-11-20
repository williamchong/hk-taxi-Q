"""How high a step a wheel meets crossing from the street onto a deck (`P4-3`).

`P4-3`'s acceptance: no step over `STEP_BAR_M` at any node joining level 0 to
an open off-grade edge. `touchdown_error.py` grades one mechanism behind such a
step, a deck end clamped over a hole, and reads it off the published
centrelines. This tool grades the *result*, on the road the car drives:

| | the pipeline | this tool |
|---|---|---|
| A station's height | `roads.py`'s samplers | **the shipped road mesh** |
| Which surface is the road | the edge the station is on | **the one the walk is already on** |
| Which edges are open | `clearance.py`'s levels | **`city.json`'s `clear_width_m`** |
| Where the step is | the two edge ends at the node | **anywhere on the walk** |

The last row is the point. A step need not sit exactly at the node — a junction
cap, a trimmed ribbon end or a lifted run can put it a metre either side — so
the walk runs `WALK_M` in from both sides and reports the largest rise or drop
between neighbouring stations, wherever it falls.

⚠️ **The polyline chooses where to stand, never what height is read.** Its `y`
is used once, to pick which drawn surface the walk starts on, `WALK_M` up the
deck; every height after that is the drawn surface. Each station takes the
face nearest the last one's height, within `HEADROOM_M` — the way a wheel stays
on the tarmac it is rolling on — so a step is read only where that surface
ends. Taking the *highest* face instead was tried first and read a neighbouring
carriageway's overlapping ribbon, 0.3-2.7 m off, as a step at eleven nodes
where the drawn road runs on unbroken.

Run:  .venv/bin/python tools/node_step.py [--generated <bundle dir>]
"""

from __future__ import annotations

import argparse
import itertools
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

from _lib.bundle import (  # noqa: E402
    Faces,
    bundle_arguments,
    drawn_surface,
    load_bundle,
    log_bundle,
    nearest,
    stations,
)
from pipeline.polyline import plan_lengths  # noqa: E402

log = logging.getLogger(__name__)

# `P4-3`'s bar, as `PLAN.md` states it: a low kerb, which is what a step at a
# ramp's foot reads as from the driver's seat.
STEP_BAR_M = 0.15

# Distance walked in from the node on each side. Long enough that the start is
# clear of the junction cap and of any lifted or descended run (the longest
# touchdown in Wan Chai is 6.6 m); a walk that runs out of edge stops there.
WALK_M = 15.0

# Station pitch. A 10% grade rises 0.025 m a station, so a ramp never reads as
# a step at the bar, and a step at the bar never hides between two stations.
PITCH_M = 0.25

# A change between two stations under this is the road's own grade, not a step,
# and is reported as no step at all. Twice what the steepest ramp the stage
# keeps (`touchdown_max_grade_pct` 10%) rises in one `PITCH_M`, and a third of
# the bar.
GRADE_FLOOR_M = 0.05

# Where the surface ends, how far the next one may be and still be the road a
# wheel lands on. A deck crossing overhead clears the street below by more than
# 4 m everywhere in the region, so it is never stepped onto.
HEADROOM_M = 1.0

# The value `clear_width_m` carries where no width was judged: the edge is
# closed to the game. Restated from `CityManifest.NOT_MEASURED` rather than
# imported from the stage, so the two cannot agree by sharing a typo.
NOT_MEASURED = -1.0


@dataclass(frozen=True)
class Crossing:
    """One walk across a node, from a deck edge onto a street edge."""

    node: int
    deck_edge: int
    street_edge: int
    road: str
    step_m: float
    at_m: float
    lost: int

    @property
    def over_bar(self) -> bool:
        return bool(self.step_m > STEP_BAR_M)


def open_edges(manifest: dict[str, Any], graph: dict[str, Any]) -> set[int]:
    """The edges the game lets a car onto: level 0, or any judged width.

    `RoadGraph._drivable`'s rule, read off the bundle that rule reads.
    """
    judged = {
        int(entry["edge"])
        for entry in manifest.get("carriageway", [])
        if any(width != NOT_MEASURED for width in entry.get("clear_width_m", []))
    }
    return {
        int(edge["id"])
        for edge in graph["edges"]
        if int(edge["elevation_level"]) == 0 or int(edge["id"]) in judged
    }


def leaving(edge: dict[str, Any], node: int, length_m: float) -> np.ndarray:
    """The first `length_m` of an edge from `node` outward, as `(n, 3)` points."""
    points = np.asarray(edge["polyline"], dtype=np.float64)
    if int(edge["from"]) != node:
        points = points[::-1]
    run = plan_lengths(points)
    end = min(length_m, float(run[-1]))
    tail = np.array([np.interp(end, run, points[:, axis]) for axis in range(3)])
    return np.vstack([points[run < end], tail])


def path_across(deck: np.ndarray, street: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Stations at most `PITCH_M` apart from the deck's far end to the street's,
    and each one's signed distance from the node (negative on the deck)."""
    path = np.array(list(stations(np.vstack([deck[::-1], street[1:]]), PITCH_M)))
    return path, plan_lengths(path) - float(plan_lengths(deck)[-1])


def walk(faces: Faces, path: np.ndarray, seed_within_m: float) -> tuple[float, int | None, int]:
    """The largest height change between neighbouring stations, where, and misses.

    Returns `(step_m, station, lost)`; `step_m` is NaN when the walk could not
    start, 0.0 and `station` None when nothing changed by `GRADE_FLOOR_M`.
    `lost` counts stations with no drawn face in reach — a hole in the road,
    reported beside the step rather than read as one.
    """
    start = faces.heights_at(float(path[0, 0]), float(path[0, 2]))
    height = nearest(start, float(path[0, 1]), within=seed_within_m)
    if height is None:
        return float("nan"), None, len(path)
    worst, where, lost = 0.0, None, 0
    for index in range(1, len(path)):
        faces_here = faces.heights_at(float(path[index, 0]), float(path[index, 2]))
        landed = nearest(faces_here, height, within=HEADROOM_M)
        if landed is None:
            lost += 1
            continue
        if abs(landed - height) > max(worst, GRADE_FLOOR_M):
            worst, where = abs(landed - height), index
        height = landed
    return worst, where, lost


def crossings(
    faces: Faces, graph: dict[str, Any], opened: set[int], seed_within_m: float
) -> tuple[list[Crossing], int]:
    """Every walk across a node joining level 0 to an open off-grade edge, and
    how many such nodes join only closed ones (the portals, a shut stub)."""
    edges = {int(edge["id"]): edge for edge in graph["edges"]}
    at_node: dict[int, list[int]] = {}
    for edge in graph["edges"]:
        for node in (int(edge["from"]), int(edge["to"])):
            at_node.setdefault(node, []).append(int(edge["id"]))

    found: list[Crossing] = []
    closed = 0
    for node, ids in sorted(at_node.items()):
        streets = [i for i in ids if int(edges[i]["elevation_level"]) == 0]
        decks = [i for i in ids if int(edges[i]["elevation_level"]) != 0]
        if not streets or not decks:
            continue
        decks = [i for i in decks if i in opened]
        if not decks:
            closed += 1
            continue
        for deck_id, street_id in itertools.product(decks, streets):
            path, along = path_across(
                leaving(edges[deck_id], node, WALK_M), leaving(edges[street_id], node, WALK_M)
            )
            step, station, lost = walk(faces, path, seed_within_m)
            found.append(
                Crossing(
                    node=node,
                    deck_edge=deck_id,
                    street_edge=street_id,
                    road=edges[deck_id]["road_name"]["en"] or "(unnamed)",
                    step_m=step,
                    at_m=float("nan") if station is None else float(along[station]),
                    lost=lost,
                )
            )
    return found, closed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manifest, _ = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)
    graph = json.loads((args.generated / manifest["road_graph"]).read_text(encoding="utf-8"))
    faces = drawn_surface(args.generated, manifest)

    found, closed = crossings(faces, graph, open_edges(manifest, graph), args.attribute_within_m)
    nodes = {crossing.node for crossing in found}
    log.info(
        "  %d nodes join level 0 to an open off-grade edge (%d walks); %d join only closed ones",
        len(nodes),
        len(found),
        closed,
    )
    if not found:
        raise SystemExit("no node joins level 0 to an open deck — nothing to grade")

    log.info("")
    log.info(
        "  %-5s %-6s %-6s %8s %7s %5s  %s",
        "node",
        "deck",
        "street",
        "step m",
        "at m",
        "lost",
        "road",
    )
    for crossing in sorted(found, key=lambda c: -np.nan_to_num(c.step_m, nan=np.inf)):
        log.info(
            "  %-5d e%-5d e%-5d %8s %7s %5d  %s",
            crossing.node,
            crossing.deck_edge,
            crossing.street_edge,
            f"{crossing.step_m:.3f}" if np.isfinite(crossing.step_m) else "unseeded",
            f"{crossing.at_m:+.2f}" if np.isfinite(crossing.at_m) else "—",
            crossing.lost,
            crossing.road,
        )

    over = sorted({c.node for c in found if c.over_bar})
    unseeded = sorted({c.node for c in found if not np.isfinite(c.step_m)})
    holed = sorted({c.node for c in found if c.lost})
    log.info("")
    log.info(
        "  %d of %d nodes step over %.2f m; %d unseeded; %d with a hole in the drawn road on the "
        "walk (reported, not graded: a hole is not P4-3's bar)",
        len(over),
        len(nodes),
        STEP_BAR_M,
        len(unseeded),
        len(holed),
    )
    if over or unseeded:
        for node in over:
            log.error("  node %d steps over the bar", node)
        for node in unseeded:
            log.error("  node %d: no drawn surface where the deck walk starts", node)
        return 1
    log.info("  PASS: every open level change is crossed without a step over the bar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
