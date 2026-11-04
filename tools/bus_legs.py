"""How far a bus drives between two of its stops, against the straight line.

    .venv/bin/python tools/bus_legs.py --region wan_chai

`P3-78` (`Q182`). TD publishes each route's stops in order and nothing between
them, so the game's legal router finds the path from one stop to the next. A leg
whose legal path is many times its straight gap is where an inferred path can
pick the wrong street — a bus seen turning off the road its route runs down.
This lists those legs, worst first, and the legs no legal path joins at all.

🔴 **The search is `reachability.py`'s, not the game's.** `build()` is the
second implementation `RoadRouter` is diffed against (`router.md`), so this
grades the legs with the population and the cost convention that rule pins:
level 0, the lane bar, the published turn bans, no U-turn. ⚠️ The game's
`Profile.legal()` also admits the measured level-1 edges this walk never routes
(`DRIVABLE_LEVEL`'s note), so a leg over a flyover reads longer or unreachable
here and may not be in the game.

A leg is two consecutive stops of one route direction, both snapped, both in
this region, `seq` one apart. The path starts at the first stop's point on its
edge, driving the way that stop's kerb flows, and ends at the second's.

⚠️ **This grades rather than checks and exits 0 whatever it finds.**
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.busroutes import (  # noqa: E402
    BUS_ROUTES_NAME,
    BUS_ROUTES_SCHEMA,
    BUSROUTES_MANIFEST_NAME,
    BUSROUTES_MANIFEST_SCHEMA,
)
from pipeline.clearance import CLEARANCE_NAME, CLEARANCE_SCHEMA  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.documents import read_document  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402
from reachability import (  # noqa: E402
    DRIVABLE_LEVEL,
    Network,
    build,
    check_documents,
    percentiles,
    plan_length,
    starved,
)

log = logging.getLogger(__name__)

# A leg past this many times its straight gap is listed.
DETOUR_RATIO = 2.0
# How many legs to name.
NAMED_LIMIT = 15


@dataclass(frozen=True)
class Leg:
    route: str
    name: str
    from_seq: int
    to_seq: int
    straight_m: float
    # `math.inf` where no legal path joins the two.
    path_m: float

    @property
    def ratio(self) -> float:
        return self.path_m / max(self.straight_m, 1.0)


def _state(net: Network, graph_edges: dict[int, dict], edge: int, along: bool) -> int | None:
    """The network state driving `edge` its `along` way, or None off the network."""
    entry = int(graph_edges[edge]["from" if along else "to"])
    for state in net.by_edge.get(edge, ()):
        if net.states[state][1] == entry:
            return state
    return None


def leg_m(
    net: Network,
    graph_edges: dict[int, dict],
    lengths: dict[int, float],
    start: dict,
    end: dict,
) -> float:
    """The legal driving distance from stop `start` to stop `end`, `math.inf` for none.

    `reachability.distances`' convention: entering a state costs its whole edge,
    so the end edge's whole length is taken off and the part up to the stop put
    back, and the start edge's remainder past its stop is added.
    """
    first = _state(net, graph_edges, int(start["edge"]), bool(start["along"]))
    last = _state(net, graph_edges, int(end["edge"]), bool(end["along"]))
    if first is None or last is None:
        return math.inf
    start_t, end_t = float(start["t"]), float(end["t"])
    start_len = lengths[int(start["edge"])]
    end_len = lengths[int(end["edge"])]
    if first == last:
        ahead = (end_t - start_t) if start["along"] else (start_t - end_t)
        if ahead >= 0.0:
            return ahead * start_len
    remainder = ((1.0 - start_t) if start["along"] else start_t) * start_len
    into_end = (end_t if end["along"] else 1.0 - end_t) * end_len
    best = [math.inf] * len(net.states)
    heap: list[tuple[float, int]] = []
    for other in net.adjacency[first]:
        best[other] = net.lengths[other]
        heap.append((best[other], other))
    heapq.heapify(heap)
    while heap:
        cost, state = heapq.heappop(heap)
        if cost > best[state]:
            continue
        if state == last:
            return remainder + cost - end_len + into_end
        for other in net.adjacency[state]:
            step = cost + net.lengths[other]
            if step < best[other]:
                best[other] = step
                heapq.heappush(heap, (step, other))
    return math.inf


def legs_of(routes: list[dict]) -> list[tuple[dict, dict, dict]]:
    """Every `(route, start, end)` of consecutive snapped stops, `seq` one apart."""
    found = []
    for route in routes:
        stops = route["stops"]
        for start, end in itertools.pairwise(stops):
            if int(end["seq"]) != int(start["seq"]) + 1:
                continue
            if int(start["edge"]) < 0 or int(end["edge"]) < 0:
                continue
            found.append((route, start, end))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument("--ratio", type=float, default=DETOUR_RATIO)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    out_dir = city.out_dir(args.region, args.out_root)
    rebuild = f"python -m pipeline --region {args.region}"
    manifest = read_document(
        out_dir / BUSROUTES_MANIFEST_NAME, BUSROUTES_MANIFEST_SCHEMA, "python -m pipeline.busroutes"
    )
    if manifest.get("document") is None:
        log.info("bus legs: %s publishes no route", args.region)
        return 0
    routes = read_document(
        out_dir / BUS_ROUTES_NAME, BUS_ROUTES_SCHEMA, "python -m pipeline.busroutes"
    )["routes"]
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, args.region)
    clearance = read_document(out_dir / CLEARANCE_NAME, CLEARANCE_SCHEMA, rebuild)
    check_documents(graph, clearance)
    levels = {int(edge["id"]): int(edge["elevation_level"]) for edge in graph["edges"]}
    keep = {edge for edge, level in levels.items() if level == DRIVABLE_LEVEL}
    keep -= starved(clearance, levels, float(city.roads.lane_width_m))
    net = build(graph, keep)
    graph_edges = {int(edge["id"]): edge for edge in graph["edges"]}
    lengths = {edge: plan_length(graph_edges[edge]["polyline"]) for edge in graph_edges}

    legs: list[Leg] = []
    for route, start, end in legs_of(routes):
        straight = math.dist(start["plan"], end["plan"])
        legs.append(
            Leg(
                str(route["key"]),
                str(route["name"]),
                int(start["seq"]),
                int(end["seq"]),
                straight,
                leg_m(net, graph_edges, lengths, start, end),
            )
        )
    unreachable = [leg for leg in legs if math.isinf(leg.path_m)]
    reached = [leg for leg in legs if not math.isinf(leg.path_m)]
    ratios = [leg.ratio for leg in reached]
    over = sorted((leg for leg in reached if leg.ratio > args.ratio), key=lambda leg: -leg.ratio)
    p50, p90, p99, worst = percentiles(ratios)
    log.info(
        "bus legs %s: %d routes, %d legs -> %d reached, %d unreachable; path / straight "
        "p50 %.2f p90 %.2f p99 %.2f max %.2f; %d over %.1fx",
        args.region,
        len(routes),
        len(legs),
        len(reached),
        len(unreachable),
        p50,
        p90,
        p99,
        worst,
        len(over),
        args.ratio,
    )
    for leg in over[:NAMED_LIMIT]:
        log.info(
            "  %-10s %-6s stop %d -> %d: %.0f m by road for %.0f m straight (%.1fx)",
            leg.route,
            leg.name,
            leg.from_seq,
            leg.to_seq,
            leg.path_m,
            leg.straight_m,
            leg.ratio,
        )
    for leg in unreachable[:NAMED_LIMIT]:
        log.info(
            "  %-10s %-6s stop %d -> %d: unreachable (%.0f m straight)",
            leg.route,
            leg.name,
            leg.from_seq,
            leg.to_seq,
            leg.straight_m,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
