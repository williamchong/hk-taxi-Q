"""The signalled junctions and their authored stages (`P3-3a`, `Q173`).

The plan a car stops at and, from `P3-3e`, the plan the heads are lit by. Two
halves, and only the first is read:

- 🔴 **Which junctions are signalled is the publisher's.** A junction is
  signalled when a signal stop line (`signals.stop_line_codes`, `RM1011`) is
  hosted at it. The host is `roadmarks.transverse_host`, so the bar a car stops
  at is the bar the paint stage drew; the junction is the host edge's nearer
  node, read as `surface.py`'s stub cluster (`P3-31`) or alone. Grouping nodes
  by distance would be a free radius (`Q72`): 15 / 25 / 35 m give 297 / 240 /
  202 junctions on Wan Chai and nothing plateaus.
- 🔴 **Which approaches share a green is ours.** TD publishes no stage plan.
  Approaches whose travel axes lie within `axis_tolerance_deg` share a stage;
  a one-axis junction gets an all-red stage for the crossing it serves.

⚠️ **The host fixes the junction, never the approach.** 68 of Wan Chai's 120
`RM1011` cross no level-0 centreline — the graph and the paint part at the mouth
— and the transverse host is often the edge LEAVING the junction. So the
approaches are every level-0 edge entering the junction from outside it, each
stopping at its drawn mouth: `roadsurface.json`'s `trim_m` at that end, where
the ribbon gives way to the junction's surface.

⚠️ **A junction a neighbour's edge reaches is refused (`at_seam`)**: its
approaches are split across two bundles and neither could stage it whole.
"""

from __future__ import annotations

import argparse
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.config import Config, load_config
from pipeline.documents import read_document, write_document
from pipeline.polyline import Segments, bearing_deg, plan_lengths_2d
from pipeline.roadmarks import (
    Network,
    RoadMarkReport,
    _drawn_widths,
    read_markings,
    transverse_host,
)
from pipeline.roads import ROADGRAPH_NAME, Ownership, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

SIGNALS_MANIFEST_NAME = "signals.json"
# 2 since `Q173`: the plan, where 1 was `P3-17`'s heads (`Q77`). A v1 reader
# would look for a mesh and find a junction table.
SIGNALS_MANIFEST_SCHEMA = 2
SIGNALS_PLAN_NAME = "signals_plan.json"
SIGNALS_PLAN_SCHEMA = 1


@dataclass
class SignalReport:
    """What the stage read, refused and staged.

    The partitions:

        stop_lines == no_host + off_axis + dead_end + hosted
        junctions  == staged + at_seam + not_owned + no_approach
    """

    stop_lines: int = 0
    no_host: int = 0
    off_axis: int = 0
    # Hosted at a node only one edge reaches: the map's edge or a cul-de-sac.
    dead_end: int = 0
    hosted: int = 0
    junctions: int = 0
    staged: int = 0
    at_seam: int = 0
    not_owned: int = 0
    no_approach: int = 0
    # Of the staged: junctions that are a stub cluster rather than one node.
    clusters: int = 0
    approaches: int = 0
    # Approaches whose own edge hosts a stop line: the rest stop at a mouth the
    # publisher painted no bar across (the host is often the edge leaving).
    approaches_with_stop_line: int = 0
    approaches_by_junction: dict[str, int] = field(default_factory=dict)
    stages_by_junction: dict[str, int] = field(default_factory=dict)
    # One-axis junctions, given an all-red stage for their crossing.
    crossing_stages: int = 0


@dataclass(frozen=True)
class Approach:
    """One way into a junction, stopping at its drawn mouth."""

    edge: int
    # True when travel runs along the edge's own direction (it enters at `to`).
    along: bool
    # Distance from the edge's START to the stop point, in plan metres.
    stop_m: float
    # Game heading of travel at the mouth, degrees in [0, 360): 0 is -z.
    heading_deg: float


def stages_of(headings: list[float], tolerance_deg: float) -> list[int]:
    """The stage each approach takes: one per run of travel axes `tolerance_deg` wide.

    An axis is a heading mod 180, so opposed approaches share one. The axes are
    walked round the half-circle from the widest gap — the one place a run cannot
    straddle — and a stage opens wherever an axis lies more than the tolerance
    past its stage's first. Stages are numbered in that walk's order.
    """
    if not headings:
        return []
    axes = [heading % 180.0 for heading in headings]
    order = sorted(range(len(axes)), key=lambda index: axes[index])
    ring = [axes[index] for index in order]
    # The last gap wraps the fold; unmodded, so equal axes leave it 180 wide.
    gaps = [ring[k + 1] - ring[k] for k in range(len(ring) - 1)] + [ring[0] + 180.0 - ring[-1]]
    start = (int(np.argmax(gaps)) + 1) % len(ring)
    stage_of = [0] * len(axes)
    stage, first = -1, math.nan
    for step in range(len(ring)):
        k = (start + step) % len(ring)
        unwrapped = ring[k] + (180.0 if k < start else 0.0)
        if stage < 0 or unwrapped - first > tolerance_deg:
            stage += 1
            first = unwrapped
        stage_of[order[k]] = stage
    return stage_of


def _junction_of(surface: dict) -> dict[int, int]:
    """Node id -> the lowest node of its level-0 stub cluster; a node in none is its own."""
    junction: dict[int, int] = {}
    for cluster in surface.get("junctions", []):
        if int(cluster["level"]) == 0:
            nodes = [int(node) for node in cluster["nodes"]]
            for node in nodes:
                junction[node] = min(nodes)
    return junction


def approaches_into(
    members: set[int], edges: list[dict[str, Any]], trims: dict[int, list[float]]
) -> list[Approach]:
    """Every level-0 edge entering `members` from outside, stopped at its mouth."""
    found: list[Approach] = []
    for edge in edges:
        starts, ends = int(edge["from"]) in members, int(edge["to"]) in members
        if starts == ends:
            # Wholly outside, or a stub inside the junction.
            continue
        plan = np.asarray(edge["polyline"], dtype=np.float64)[:, [0, 2]]
        length = float(plan_lengths_2d(plan)[-1])
        trim_start, trim_end = trims.get(int(edge["id"]), [0.0, 0.0])
        if ends:
            found.append(
                Approach(int(edge["id"]), True, length - trim_end, bearing_deg(plan[-1] - plan[-2]))
            )
        elif edge["direction"] == "both":
            found.append(
                Approach(int(edge["id"]), False, trim_start, bearing_deg(plan[0] - plan[1]))
            )
    return found


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> SignalReport:
    """Stage the region's signalled junctions and write `signals_plan.json`."""
    spec = city.signals
    report = SignalReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None or city.road_marks is None:
        log.info("city '%s' declares no signals (or no road_marks) block; no plan", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    marks = city.road_marks
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    edges = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    network = Network.of(Segments.of(edges), _drawn_widths(surface))
    by_id = {int(edge["id"]): edge for edge in edges}
    ends: dict[int, int] = defaultdict(int)
    for edge in edges:
        ends[int(edge["from"])] += 1
        ends[int(edge["to"])] += 1
    junction = _junction_of(surface)

    markings = read_markings(
        city,
        marks,
        region_id,
        city.game_transform(region_id),
        city.region_high(region_id),
        RoadMarkReport(),
        sources_root=sources_root,
    )
    stop_lines: dict[int, int] = defaultdict(int)
    hosts: set[int] = set()
    for marking in markings:
        if marking.code not in spec.stop_line_codes:
            continue
        report.stop_lines += 1
        host = transverse_host(network, marking, marks)
        if host is None:
            report.no_host += 1
            continue
        if host.residual_deg > marks.bearing_tolerance_deg:
            report.off_axis += 1
            continue
        edge = by_id[host.edge_id]
        plan = np.asarray(edge["polyline"], dtype=np.float64)[:, [0, 2]]
        midpoint = marking.midpoint
        near_start = np.linalg.norm(plan[0] - midpoint) <= np.linalg.norm(plan[-1] - midpoint)
        node = int(edge["from"] if near_start else edge["to"])
        if ends[node] < 2:
            report.dead_end += 1
            continue
        report.hosted += 1
        stop_lines[junction.get(node, node)] += 1
        hosts.add(host.edge_id)

    members: dict[int, set[int]] = defaultdict(set)
    for node, root in junction.items():
        members[root].add(node)
    foreign = {
        int(node) for edge in graph.get("foreign_edges", []) for node in (edge["from"], edge["to"])
    }
    positions = {int(node["id"]): node["pos"] for node in graph["nodes"]}
    owner_of = Ownership(city, region_id, city.game_transform(region_id))
    trims = {int(row["edge"]): row["trim_m"] for row in surface["carriageway"]}

    junctions: list[dict[str, Any]] = []
    for root in sorted(stop_lines):
        report.junctions += 1
        nodes = members.get(root) or {root}
        if nodes & foreign:
            report.at_seam += 1
            continue
        pos = positions[root]
        if owner_of(np.array([pos[0], pos[2]])) != region_id:
            report.not_owned += 1
            continue
        approaches = approaches_into(nodes, edges, trims)
        if not approaches:
            report.no_approach += 1
            continue
        stage_of = stages_of([one.heading_deg for one in approaches], spec.axis_tolerance_deg)
        stages = max(stage_of) + 1
        crossing = stages == 1
        report.staged += 1
        report.clusters += len(nodes) > 1
        report.approaches += len(approaches)
        report.approaches_with_stop_line += sum(one.edge in hosts for one in approaches)
        key = str(len(approaches))
        report.approaches_by_junction[key] = report.approaches_by_junction.get(key, 0) + 1
        key = str(stages)
        report.stages_by_junction[key] = report.stages_by_junction.get(key, 0) + 1
        report.crossing_stages += crossing
        centre = np.mean([positions[node] for node in nodes], axis=0)
        junctions.append(
            {
                "id": root,
                "nodes": sorted(nodes),
                "pos": [round(float(value), 3) for value in centre],
                "stop_lines": stop_lines[root],
                # Vehicle stages; a crossing adds one all-red stage after them.
                "stages": stages,
                "crossing": crossing,
                "approaches": [
                    {
                        "edge": one.edge,
                        "along": one.along,
                        "stop_m": round(one.stop_m, 3),
                        "heading_deg": round(one.heading_deg, 2),
                        "stage": stage,
                    }
                    for one, stage in zip(approaches, stage_of, strict=True)
                ],
            }
        )

    if junctions:
        write_document(
            out_dir / SIGNALS_PLAN_NAME,
            {
                "schema_version": SIGNALS_PLAN_SCHEMA,
                "city_id": city.id,
                "region_id": region_id,
                "junctions": junctions,
            },
        )
    _write_manifest(out_dir, city, region_id, report)
    return report


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: SignalReport) -> int:
    document: dict[str, Any] = {
        "schema_version": SIGNALS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "plan_document": SIGNALS_PLAN_NAME if report.staged else None,
    }
    document.update(vars(report))
    return write_document(out_dir / SIGNALS_MANIFEST_NAME, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "signals: %d stop lines (%d no host, %d off axis, %d at a dead end) -> %d junctions, "
        "%d staged (%d clusters; %d at the seam, %d not owned, %d no approach), "
        "%d approaches (%d with their own stop line) %s, stages %s, %d crossing stages",
        report.stop_lines,
        report.no_host,
        report.off_axis,
        report.dead_end,
        report.junctions,
        report.staged,
        report.clusters,
        report.at_seam,
        report.not_owned,
        report.no_approach,
        report.approaches,
        report.approaches_with_stop_line,
        report.approaches_by_junction,
        report.stages_by_junction,
        report.crossing_stages,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
