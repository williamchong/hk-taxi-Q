"""Merge two neighbouring regions' road graphs into one (`P5-7g`, `Q116`).

Each region publishes the runs it owns under `edges` and the neighbour's runs
that reach into it under `foreign_edges` (`P5-7e`), so a pair of built regions
carries every crossing road twice — once measured, once as a placeholder. The
merge keeps the owner's copy, drops the foreign one, and uses the pair to name
the nodes the two graphs share: a foreign copy's `from` and `to` are the very
nodes the owner's copy ends at, so the seam nodes are identified by
`(source_id, run)` and never by a distance tolerance.

The merged graph is in the FIRST region's frame — the second region's
positions are shifted by the difference of the two `city_offset`s, which is
exact in float because both origins are whole metres (`Q7`) — and its edge
ids are the first region's own followed by the second's renumbered, so a
consumer that already reads one region reads the pair unchanged.

🔴 **This is the reference `P5-9`'s GDScript merge is tested against, and what
`tools/reachability.py --graph-dir` runs across the pair.** It measures nothing
itself; the counters it publishes are about the identities — a foreign copy
whose run the owner does not publish, or a run both regions claim — because
those are the two ways two builds can disagree about one road, and neither is
visible from inside either build.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.clearance import CLEARANCE_NAME
from pipeline.config import Config, load_config
from pipeline.documents import round_position, write_document
from pipeline.roads import ENDPOINT, JUNCTION, ROADGRAPH_NAME, ROADGRAPH_SCHEMA, read_graph

log = logging.getLogger(__name__)

JOIN_NAME = "join.json"

Identity = tuple[int, int]


@dataclass
class JoinReport:
    """What the merge did, and the two ways the pair can disagree."""

    frame: str
    regions: tuple[str, str]
    owned_a: int
    owned_b: int
    # Foreign copies whose run the other region publishes as its own — every
    # one is a seam node named by identity — and those it does not, which is
    # the two builds numbering a feature's runs differently (`join_seam.py`
    # reads the same counter off the shipped pair).
    foreign_matched: int = 0
    foreign_unmatched: int = 0
    nodes: int = 0
    nodes_unified: int = 0
    edges: int = 0
    turns: int = 0
    # A turn naming an arm the merged graph has no edge for: a foreign copy
    # left unmatched, or a turn on a run only one build read.
    turns_dropped: int = 0
    clearance_rows: int = 0


def identity(edge: dict[str, Any]) -> Identity:
    return (int(edge["source_id"]), int(edge["run"]))


def merge(
    a: dict[str, Any],
    b: dict[str, Any],
    delta: np.ndarray,
    *,
    regions: tuple[str, str],
    clearance: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, JoinReport]:
    """`a` and `b` as one graph in `a`'s frame; `delta` moves `b` into it."""
    a_owned = {identity(edge): edge for edge in a["edges"]}
    b_owned = {identity(edge): edge for edge in b["edges"]}
    a_foreign = {identity(edge): edge for edge in a.get("foreign_edges", [])}
    b_foreign = {identity(edge): edge for edge in b.get("foreign_edges", [])}
    # A run both regions claim is the ownership rule disagreeing with itself,
    # and is refused rather than counted, because a merge cannot pick.
    both = a_owned.keys() & b_owned.keys()
    if both:
        raise ValueError(
            f"{len(both)} runs are owned by both {regions[0]} and {regions[1]}: {sorted(both)[:5]}"
        )
    report = JoinReport(
        frame=regions[0], regions=regions, owned_a=len(a_owned), owned_b=len(b_owned)
    )

    # Which merged node each node of `b` is: seeded here with the seam nodes,
    # wherever a run's two copies say so, and completed below with a new id
    # for every other node of `b` — so by the edge loop it is a total map.
    node_of_b: dict[int, int] = {}

    def unify(b_node: int, a_node: int) -> None:
        if node_of_b.setdefault(b_node, a_node) != a_node:
            raise ValueError(
                f"node {b_node} of {regions[1]} is named as two nodes of {regions[0]}: "
                f"{node_of_b[b_node]} and {a_node}"
            )

    # Edge ids `a`'s foreign copies carry, to the merged id of the owner's copy —
    # and the same the other way — so a turn naming a foreign arm resolves.
    alias_a: dict[int, int] = {}
    alias_b: dict[int, int] = {}
    edge_of_a = {int(edge["id"]): int(edge["id"]) for edge in a["edges"]}
    edge_of_b: dict[int, int] = {}
    next_id = max(edge_of_a, default=-1) + 1
    for edge in b["edges"]:
        edge_of_b[int(edge["id"])] = next_id
        next_id += 1

    for key, copy in a_foreign.items():
        owner = b_owned.get(key)
        if owner is None:
            report.foreign_unmatched += 1
            continue
        report.foreign_matched += 1
        unify(int(owner["from"]), int(copy["from"]))
        unify(int(owner["to"]), int(copy["to"]))
        alias_a[int(copy["id"])] = edge_of_b[int(owner["id"])]
    for key, copy in b_foreign.items():
        owner = a_owned.get(key)
        if owner is None:
            report.foreign_unmatched += 1
            continue
        report.foreign_matched += 1
        unify(int(copy["from"]), int(owner["from"]))
        unify(int(copy["to"]), int(owner["to"]))
        alias_b[int(copy["id"])] = int(owner["id"])
    report.nodes_unified = len(node_of_b)

    nodes = [dict(node) for node in a["nodes"]]
    for node in b["nodes"]:
        b_id = int(node["id"])
        if b_id in node_of_b:
            continue
        node_of_b[b_id] = len(nodes)
        nodes.append(
            {
                "id": len(nodes),
                "pos": round_position(np.asarray(node["pos"], dtype=float) + delta),
                "kind": node["kind"],
            }
        )

    edges = [dict(edge) for edge in a["edges"]]
    for edge in b["edges"]:
        moved = dict(edge)
        moved["id"] = edge_of_b[int(edge["id"])]
        moved["from"] = node_of_b[int(edge["from"])]
        moved["to"] = node_of_b[int(edge["to"])]
        moved["polyline"] = [
            round_position(np.asarray(point, dtype=float) + delta) for point in edge["polyline"]
        ]
        edges.append(moved)
    _rekind(nodes, edges)

    turns = _remap_turns(a["turn_restrictions"], edge_of_a, alias_a, {}, report)
    turns += _remap_turns(b["turn_restrictions"], edge_of_b, alias_b, node_of_b, report)

    graph = {
        "schema_version": ROADGRAPH_SCHEMA,
        "city_id": a["city_id"],
        "region_id": "+".join(regions),
        "frame": regions[0],
        "nodes": nodes,
        "edges": edges,
        "foreign_edges": [],
        "turn_restrictions": turns,
    }
    report.nodes, report.edges, report.turns = len(nodes), len(edges), len(turns)

    merged_clearance = None
    if clearance is not None:
        rows = list(clearance[0]["clearance"])
        for row in clearance[1]["clearance"]:
            if int(row["edge"]) in edge_of_b:
                rows.append({**row, "edge": edge_of_b[int(row["edge"])]})
        merged_clearance = {**clearance[0], "region_id": graph["region_id"], "clearance": rows}
        report.clearance_rows = len(rows)
    return graph, merged_clearance, report


def _remap_turns(
    turns: list[dict[str, Any]],
    renumbered: dict[int, int],
    alias: dict[int, int],
    node_of: dict[int, int],
    report: JoinReport,
) -> list[dict[str, int]]:
    """One region's turns in merged ids: an owned arm through `renumbered`, a
    foreign arm through `alias`, the pivot through `node_of` (empty for the
    region whose nodes are the merged nodes). An arm in neither map is a foreign
    copy the other region never published as its own, and the turn is dropped
    and counted rather than published against nothing."""
    kept: list[dict[str, int]] = []
    for turn in turns:
        arms = [
            renumbered.get(int(turn[k]), alias.get(int(turn[k]))) for k in ("from_edge", "to_edge")
        ]
        if None in arms:
            report.turns_dropped += 1
            continue
        via = int(turn["via_node"])
        kept.append({"from_edge": arms[0], "via_node": node_of.get(via, via), "to_edge": arms[1]})
    return kept


def _rekind(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    """`junction` at three or more edge ends, `endpoint` otherwise — `roads.py`'s
    rule, re-applied because a seam node has arms from both regions now."""
    degree = [0] * len(nodes)
    for edge in edges:
        degree[int(edge["from"])] += 1
        degree[int(edge["to"])] += 1
    for node in nodes:
        node["kind"] = JUNCTION if degree[int(node["id"])] >= 3 else ENDPOINT


def join_regions(
    city: Config, region_a: str, region_b: str, out_root: Path | None = None
) -> JoinReport:
    """Merge two built regions and write the pair under `<out>/<a>+<b>/`."""
    if region_b not in city.neighbours(region_a).values():
        raise SystemExit(f"{region_a} and {region_b} share no whole edge in their declared bounds")
    docs = {}
    for region in (region_a, region_b):
        out_dir = city.out_dir(region, out_root)
        graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region)
        clearance_path = out_dir / CLEARANCE_NAME
        clearance = (
            json.loads(clearance_path.read_text(encoding="utf-8"))
            if clearance_path.exists()
            else None
        )
        docs[region] = (graph, clearance)
    (ga, ca), (gb, cb) = docs[region_a], docs[region_b]
    # `b`'s origin in `a`'s frame, through the one translation the codebase
    # keeps (`GameTransform.to_game`), so the sign on z cannot be restated.
    own, other = city.game_transform(region_a), city.game_transform(region_b)
    delta = np.asarray(
        own.to_game(other.origin_easting, other.origin_northing, other.origin_elevation),
        dtype=float,
    )
    pair = (ca, cb) if ca is not None and cb is not None else None
    graph, clearance, report = merge(ga, gb, delta, regions=(region_a, region_b), clearance=pair)

    out_dir = city.out_dir(graph["region_id"], out_root)
    write_document(out_dir / ROADGRAPH_NAME, graph)
    if clearance is not None:
        write_document(out_dir / CLEARANCE_NAME, clearance)
    write_document(out_dir / JOIN_NAME, {"schema_version": 1, **asdict(report)})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region-a", required=True)
    parser.add_argument("--region-b", required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = join_regions(load_config(), args.region_a, args.region_b, args.out)
    log.info(
        "%s + %s in %s's frame: %d + %d owned edges → %d edges over %d nodes (%d unified), "
        "%d turns (%d dropped); foreign copies %d matched, %d unmatched; %d clearance rows",
        *report.regions,
        report.frame,
        report.owned_a,
        report.owned_b,
        report.edges,
        report.nodes,
        report.nodes_unified,
        report.turns,
        report.turns_dropped,
        report.foreign_matched,
        report.foreign_unmatched,
        report.clearance_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
