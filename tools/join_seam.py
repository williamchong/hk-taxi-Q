"""Do two neighbouring regions meet at the same nodes, and does each crossing road have one owner?

`Q116` measured the seam by hand off two `roadgraph.json`s: nine features cross the
line Wan Chai shares with Causeway Bay, the paired nodes miss by 0.62 m in x and
0.3-0.7 m in z because the two rectangles clip at different eastings, and
`width_m` disagrees on 7 of 9 pairs because each region measured half a
carriageway. This is that reading as a tool, so `P5-7e`'s cut has a before side
and an after side that were taken the same way.

Two tables, and they answer different questions:

- **nodes** — every node one region publishes within `--pair-within-m` of a node
  the other publishes, in the shared city frame (`Q10`: region-local position plus
  `city_offset`). The separation is what the cut has to close: today it is the
  distance between two clip points on two lines, after `P5-7e` both regions
  publish the node from the same source vertex and it must read 0.000.
- **crossings** — the road that runs through each paired node. Once the graph
  publishes `source_id` and `run`, a crossing is paired by that identity and the
  question is whether exactly ONE side owns it; until then it is the one edge each
  side hangs on its boundary node, and the question is whether the two halves
  agree on `width_m` and `lanes`, which they cannot, because each is half a road.

The near-line candidates are read off the config: which side of `--region-a`
`--region-b` lies on is derived from the two `bounds`, so a node counts as a
boundary candidate only on that side. A candidate with no partner is printed —
a road that reaches the line in one region and not the other is a clip
disagreement, and it is the finding the mutual-nearest pairing exists to expose.

Grades rather than checks and exits 0 whatever it finds: the bar is `P5-7`'s
accept, and it is quoted in the summary rather than enforced here.

Run:  .venv/bin/python tools/join_seam.py --region-a wan_chai --region-b causeway_bay
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(ROOT / "tools"))

from carriageway_occupancy import road_names  # noqa: E402
from pipeline.config import Config, load_config  # noqa: E402
from pipeline.documents import read_document  # noqa: E402
from pipeline.export import CITY_SCHEMA  # noqa: E402
from pipeline.roads import read_graph  # noqa: E402

log = logging.getLogger(__name__)

# Which edge of region A region B shares, as the sign of the axis it lies along
# in game space: +x is east, -x is west, +z is south, -z is north.
Side = tuple[str, int]
SIDE_OF = {"east": ("x", 1), "west": ("x", -1), "south": ("z", 1), "north": ("z", -1)}
COMPASS = {side: name for name, side in SIDE_OF.items()}


@dataclass(frozen=True)
class Graph:
    """One region's road graph, already moved into the city frame."""

    region: str
    nodes: dict[int, np.ndarray]
    edges: list[dict[str, Any]]
    high: tuple[float, float]
    offset: np.ndarray
    names: dict[int, str]
    # The neighbour-owned runs this region publishes for the join (`P5-7e`),
    # under their own list so no reader of `edges` sees a road nobody owns.
    foreign_edges: list[dict[str, Any]] = field(default_factory=list)

    @cached_property
    def incident(self) -> dict[int, list[dict[str, Any]]]:
        by_node: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for edge in self.edges:
            by_node[edge["from"]].append(edge)
            by_node[edge["to"]].append(edge)
        return by_node

    @cached_property
    def identities(self) -> dict[tuple[int, int], dict[str, Any]]:
        """Every edge, owned or foreign, keyed by `(source_id, run)` — empty on
        a schema that publishes neither."""
        return {
            (edge["source_id"], edge["run"]): edge
            for edge in (*self.edges, *self.foreign_edges)
            if "source_id" in edge and "run" in edge
        }

    def describe(self, edge: dict[str, Any]) -> str:
        if "source_id" not in edge:
            flag = ""
        elif edge.get("foreign"):
            flag = f"foreign→{edge['foreign']}"
        else:
            flag = "owned"
        return f"e{edge['id']:<4} {edge['width_m']:6.2f} m {edge['lanes']}L {flag}"


@dataclass(frozen=True)
class NodePair:
    a: int
    b: int
    separation: np.ndarray  # (dx, dy, dz) in metres, b minus a

    @property
    def plan_m(self) -> float:
        return float(np.hypot(self.separation[0], self.separation[2]))


def shared_side(city: Config, region_a: str, region_b: str) -> Side:
    """The side of `region_a` on which `region_b` lies, as the config derives it.

    `Config.neighbours` is the one place the whole-edge rule lives (`P5-7c`);
    a pair it does not name is not a seam this tool can read.
    """
    for name, other in city.neighbours(region_a).items():
        if other == region_b:
            return SIDE_OF[name]
    raise SystemExit(f"{region_a} and {region_b} share no whole edge in their declared bounds")


def load_graph(city: Config, region: str, out_root: Path | None) -> Graph:
    out_dir = city.out_dir(region, out_root)
    manifest = read_document(
        out_dir / "city.json", CITY_SCHEMA, f"cd etl && python -m pipeline --region {region}"
    )
    graph = read_graph(out_dir / manifest["road_graph"], city.id, region)
    offset = np.asarray(manifest["city_offset"], dtype=float)
    log.info(
        "  %s: %d nodes, %d edges, built %s",
        region,
        len(graph["nodes"]),
        len(graph["edges"]),
        manifest.get("generated_utc", "unknown"),
    )
    return Graph(
        region=region,
        nodes={
            node["id"]: np.asarray(node["pos"], dtype=float) + offset for node in graph["nodes"]
        },
        edges=graph["edges"],
        high=city.region_high(region),
        offset=offset,
        names=road_names({"edges": [*graph["edges"], *graph.get("foreign_edges", [])]}),
        foreign_edges=graph.get("foreign_edges", []),
    )


def near_line(graph: Graph, side: Side, within_m: float) -> list[int]:
    """Nodes within `within_m` of the region's edge on `side`, in its own frame."""
    axis, sign = side
    index = 0 if axis == "x" else 2
    limit = (graph.high[0] if axis == "x" else graph.high[1]) if sign > 0 else 0.0
    origin = float(graph.offset[index])
    return sorted(
        node
        for node, pos in graph.nodes.items()
        if abs(float(pos[index]) - origin - limit) <= within_m
    )


def pair_nodes(
    a: Graph, b: Graph, candidates_a: list[int], candidates_b: list[int], within_m: float
) -> tuple[list[NodePair], list[int], list[int]]:
    """Mutual nearest neighbours in plan across the two candidate sets, plus the unpaired.

    Mutual rather than one-way: two roads reaching the line 1 m apart in one
    region must not both claim the single node the other region has there.
    """
    if not candidates_a or not candidates_b:
        return [], candidates_a, candidates_b
    pos_a = np.array([a.nodes[n] for n in candidates_a])
    pos_b = np.array([b.nodes[n] for n in candidates_b])
    delta = pos_b[None, :, :] - pos_a[:, None, :]
    plan = np.hypot(delta[:, :, 0], delta[:, :, 2])
    nearest_b = plan.argmin(axis=1)
    nearest_a = plan.argmin(axis=0)
    pairs: list[NodePair] = []
    for i, j in enumerate(nearest_b):
        if nearest_a[j] == i and plan[i, j] <= within_m:
            pairs.append(NodePair(candidates_a[i], candidates_b[j], delta[i, j]))
    paired_a = {pair.a for pair in pairs}
    paired_b = {pair.b for pair in pairs}
    return (
        pairs,
        [n for n in candidates_a if n not in paired_a],
        [n for n in candidates_b if n not in paired_b],
    )


def _log_crossing_header(a: Graph, b: Graph, label: str) -> None:
    log.info("")
    log.info("  %-32s %3s  %-30s  %-30s", label, "lvl", a.region, b.region)


def _log_crossing(
    a: Graph, b: Graph, xa: dict[str, Any], xb: dict[str, Any], suffix: str = ""
) -> None:
    log.info(
        "  %-32s %3d  %-30s  %-30s%s",
        a.names.get(xa["id"], "unnamed")[:32],
        xa["elevation_level"],
        a.describe(xa),
        b.describe(xb),
        suffix,
    )


def report_crossings_by_node(a: Graph, b: Graph, pairs: list[NodePair]) -> tuple[int, int]:
    """Today's reading: the one edge each side hangs on its boundary node.

    Returns how many pairs disagree on `width_m` and on `lanes`.
    """
    width_off = lanes_off = 0
    _log_crossing_header(a, b, "crossing")
    for pair in pairs:
        ea, eb = a.incident[pair.a], b.incident[pair.b]
        if len(ea) != 1 or len(eb) != 1:
            log.info(
                "  node %d/%d: %d and %d incident edges — not a clip end, skipped",
                pair.a,
                pair.b,
                len(ea),
                len(eb),
            )
            continue
        (xa,), (xb,) = ea, eb
        width_off += xa["width_m"] != xb["width_m"]
        lanes_off += xa["lanes"] != xb["lanes"]
        _log_crossing(a, b, xa, xb)
    return width_off, lanes_off


def report_crossings_by_identity(a: Graph, b: Graph) -> tuple[int, int, int, int]:
    """After the cut: every edge both regions publish, by `(source_id, run)`.

    Returns the shared count, how many have exactly one owner, how many
    disagree on `lanes` between the owner's copy and the foreign one, and how
    many foreign copies name a run the region opposite does not publish at all
    — the counter that reads non-zero if the two builds ever number a
    feature's runs differently, which nothing else here can see.
    """
    shared = sorted(a.identities.keys() & b.identities.keys())
    one_owner = lanes_off = 0
    _log_crossing_header(a, b, "shared edge")
    for key in shared:
        xa, xb = a.identities[key], b.identities[key]
        owners = (xa.get("foreign") is None) + (xb.get("foreign") is None)
        one_owner += owners == 1
        lanes_off += xa["lanes"] != xb["lanes"]
        _log_crossing(a, b, xa, xb, "" if owners == 1 else f"  ⚠ {owners} owners")
    unmatched = 0
    for mine, theirs in ((a, b), (b, a)):
        for edge in mine.foreign_edges:
            if (edge["source_id"], edge["run"]) not in theirs.identities:
                unmatched += 1
                log.info(
                    "  %-32s %3d  %s has no run (%d, %d) opposite",
                    mine.names.get(edge["id"], "unnamed")[:32],
                    edge["elevation_level"],
                    mine.describe(edge),
                    edge["source_id"],
                    edge["run"],
                )
    return len(shared), one_owner, lanes_off, unmatched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region-a", required=True)
    parser.add_argument("--region-b", required=True)
    parser.add_argument(
        "--out", type=Path, default=None, help="the ETL out tree (default: etl/out)"
    )
    parser.add_argument(
        "--pair-within-m",
        type=float,
        default=2.0,
        help="how far apart two nodes may be and still be the same node (default 2.0)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    side = shared_side(city, args.region_a, args.region_b)
    side_name = COMPASS[side]
    a = load_graph(city, args.region_a, args.out)
    b = load_graph(city, args.region_b, args.out)
    log.info("  %s lies %s of %s", args.region_b, side_name, args.region_a)

    # Before the cut every candidate stands on the internal line; after it
    # nothing should, and the shared nodes are the crossing runs' two ends,
    # found through the edges both regions publish.
    on_line_a = near_line(a, side, args.pair_within_m)
    on_line_b = near_line(b, (side[0], -side[1]), args.pair_within_m)
    shared = a.identities.keys() & b.identities.keys()
    if shared:
        cand_a = sorted(
            {n for k in shared for n in (a.identities[k]["from"], a.identities[k]["to"])}
        )
        cand_b = sorted(
            {n for k in shared for n in (b.identities[k]["from"], b.identities[k]["to"])}
        )
    else:
        cand_a, cand_b = on_line_a, on_line_b

    pairs, lone_a, lone_b = pair_nodes(a, b, cand_a, cand_b, args.pair_within_m)
    log.info("")
    log.info(
        "  %-6s %-6s %8s %8s %8s %8s", a.region[:6], b.region[:6], "dx m", "dy m", "dz m", "plan m"
    )
    for pair in sorted(pairs, key=lambda p: a.nodes[p.a][2]):
        dx, dy, dz = pair.separation
        log.info("  n%-5d n%-5d %8.3f %8.3f %8.3f %8.3f", pair.a, pair.b, dx, dy, dz, pair.plan_m)
    for node in lone_a:
        log.info("  n%-5d —      no partner within %.1f m", node, args.pair_within_m)
    for node in lone_b:
        log.info("  —      n%-5d no partner within %.1f m", node, args.pair_within_m)
    plan_min = min((p.plan_m for p in pairs), default=0.0)
    plan_max = max((p.plan_m for p in pairs), default=0.0)

    if shared:
        count, one_owner, lanes_off, unmatched = report_crossings_by_identity(a, b)
        crossings = (
            f"{count} shared edges, {one_owner} with exactly one owner, "
            f"{lanes_off} disagreeing on lanes, {unmatched} foreign copies with no run "
            f"opposite; {len(on_line_a)} + {len(on_line_b)} nodes still on the internal line"
        )
    else:
        width_off, lanes_off = report_crossings_by_node(a, b, pairs)
        crossings = (
            f"width_m disagrees on {width_off}, lanes on {lanes_off} — "
            f"no source_id published, so no owner to read"
        )
    log.info("")
    log.info(
        "  %d nodes paired (plan separation min %.3f / max %.3f m), %d unpaired; %s",
        len(pairs),
        plan_min,
        plan_max,
        len(lone_a) + len(lone_b),
        crossings,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
