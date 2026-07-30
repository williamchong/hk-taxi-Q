"""Published taxi points to fare nodes (`P1-5`).

Reads the taxi-stand and pick-up/drop-off datasets a previous fetch cached,
keeps the ones inside the region, attaches each to the road edge it belongs to,
and writes `fares.json` per the contract in `docs/ARCHITECTURE.md`.

Four measurements off the two sources decide the shape of this — see
`docs/DATA_SOURCES.md`:

- **Snapping is never ambiguous.** Every one of the region's 29 points sits
  1.18-8.37 m from a road centreline, and the runner-up edge is at least 4.28 m
  further away. These are kerbside positions against a centreline graph, so the
  distance is about half a carriageway and the nearest edge is the road the
  point is on. No tie-breaking rule was needed, and inventing one would be
  guessing.
- **The source positions are quantised to whole metres.** Published as lon/lat
  to ten decimal places, but every one round-trips to an exact metre on the
  HK1980 grid. So a fare node's position carries about half a metre of its own
  uncertainty, which is why nothing here tries to be more precise than that —
  and why the 4.28 m margin above is comfortable rather than marginal.
- **The source's own prose confirms it.** 28 of the 29 snap to an edge with an
  English name, and in 28 of those 28 that street name appears in the point's
  free-text `Location_EN`. The geometry pipeline never reads that text, so the
  agreement is independent evidence rather than a tautology.
- **The category field is free text, not an enum.** Sixteen distinct spellings
  territory-wide, several carrying an operating-time note after a newline. The
  city file collapses them with ordered substring rules; `Q14` records what is
  lost.
- **A quarter of the pick-up/drop-off points are drop-off only.** 66 of 275,
  and 4 of the region's 15. Carried as `pickup`/`dropoff` rather than flattened.

Nothing here knows a Hong Kong fact: dataset URLs, property names, category
spellings and the snap limit all arrive from `config/cities/*.yaml`.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.config import TAXI_STAND, CityConfig, FareCategory, FareGroup, load_city
from pipeline.crs import transformer
from pipeline.fetch import cached_source, read_feature_collection
from pipeline.roads import (
    ROADGRAPH_NAME,
    clean_text,
    plan_lengths,
    plan_steps,
    read_graph,
    round_position,
)

log = logging.getLogger(__name__)

FARES_NAME = "fares.json"
FARES_SCHEMA = 1

# Node ids in the data contract are `f_001`. Zero-padded to three so a listing
# sorts in the order the nodes were written; wider ids simply grow past it.
_ID_FORMAT = "f_{:03d}"


@dataclass(frozen=True)
class FareNode:
    id: str
    # The *source* position — the kerbside, not the carriageway. Deliberate:
    # 11 of the region's 29 points lie outside even the widened road surface,
    # and this is where the passenger stands. Where the taxi stops is
    # `nearest_edge` at `edge_t`, which is recoverable; this is not.
    pos: tuple[float, float, float]
    kind: str
    stand_category: str | None
    name: dict[str, str | None]
    nearest_edge: int
    # How far along that edge, as a fraction of its plan length. Without it
    # `nearest_edge` names a road that can be 200 m long and leaves the game to
    # redo the projection this stage just did.
    edge_t: float
    pickup: bool
    dropoff: bool


@dataclass
class FareReport:
    nodes: list[FareNode] = field(default_factory=list)
    # Features in the fetched datasets, before any filtering. These are
    # whole-territory files, so most of this is other districts.
    read: int = 0
    outside: int = 0
    # Dropped for having no road edge within the configured limit. The one
    # count that should stay at zero: a fare node whose `nearest_edge` did not
    # resolve is the acceptance criterion for this task.
    unsnapped: int = 0
    worst_snap_m: float = 0.0
    # Counted rather than derived from `nodes`, because a `pudo` node does not
    # carry its category into the contract — only what it permits.
    by_category: dict[str, int] = field(default_factory=dict)

    @property
    def unnamed(self) -> int:
        """Nodes kept but missing a name in at least one language."""
        return sum(1 for node in self.nodes if not all(node.name.values()))

    def add(self, node: FareNode, category: FareCategory, snap_m: float) -> None:
        self.nodes.append(node)
        self.by_category[category.id] = self.by_category.get(category.id, 0) + 1
        self.worst_snap_m = max(self.worst_snap_m, snap_m)

    def next_id(self) -> str:
        return _ID_FORMAT.format(len(self.nodes) + 1)


@dataclass(frozen=True)
class Snap:
    """Where a point attaches to the road graph."""

    # The graph's own edge id, not a position in any list.
    edge: int
    distance_m: float
    # Fraction along the edge's plan length, 0 at `from` and 1 at `to`.
    t: float
    # Height of the attachment point, which is where the fare node's own
    # height comes from.
    y: float


@dataclass(frozen=True)
class Segments:
    """Every edge's segments flattened into one set of arrays.

    Flattened rather than walked per edge so snapping a point is a single
    vectorised pass over the region rather than a Python loop over 797
    polylines. The bookkeeping arrays are what let a hit be traced back to
    which edge it was on and how far along.

    Public because it is the one piece of geometry this stage owns, and so the
    one worth testing on its own.
    """

    start: np.ndarray
    delta: np.ndarray
    # Plan length of each segment, of the run before it along its own edge, and
    # of that whole edge. Plan rather than 3D, via the same helpers `P1-4`
    # measures with: a ramp's footprint is what a position along it means.
    length_m: np.ndarray
    before_m: np.ndarray
    total_m: np.ndarray
    # The graph's edge id for each segment. Read from the edge rather than
    # taken from its position in the list: it is published as `nearest_edge`,
    # which the data contract defines as an id, and the two agree today only
    # because `P1-3` happens to number edges by their order.
    edge: np.ndarray

    @classmethod
    def of(cls, edges: Sequence[dict[str, Any]]) -> Segments:
        starts, deltas, lengths, befores, totals, owners = [], [], [], [], [], []
        for edge in edges:
            points = np.asarray(edge["polyline"], dtype=np.float64)
            if len(points) < 2:
                continue
            along = plan_lengths(points)
            starts.append(points[:-1])
            deltas.append(np.diff(points, axis=0))
            lengths.append(plan_steps(points))
            befores.append(along[:-1])
            totals.append(np.full(len(points) - 1, along[-1]))
            owners.append(np.full(len(points) - 1, int(edge["id"])))

        if not starts:
            raise ValueError("the road graph has no edge with a usable polyline")
        return cls(
            start=np.concatenate(starts),
            delta=np.concatenate(deltas),
            length_m=np.concatenate(lengths),
            before_m=np.concatenate(befores),
            total_m=np.concatenate(totals),
            edge=np.concatenate(owners),
        )

    def nearest(self, x: float, z: float) -> Snap:
        """The closest point on the graph to `(x, z)`, measured in plan.

        Plan distance is the only defensible measure here, because the sources
        are 2D: a taxi stand carries no height, so a stand under a flyover has
        nothing in it to prefer the street over the deck above. No point in
        this region is affected — every winner is at level 0, and the one
        level-1 runner-up loses by 7 m — but a city with stands under an
        elevated road would need height in the source to do better. See `Q15`.
        """
        offset_x, offset_z = x - self.start[:, 0], z - self.start[:, 2]
        step_x, step_z = self.delta[:, 0], self.delta[:, 2]

        # Projection of the point onto each segment, clamped to it. A zero
        # length segment cannot survive `P1-3`'s simplification, but the graph
        # is an input rather than something this stage built, so guard the
        # divide. No second guard on the result is needed: a zero-length
        # segment has a zero numerator too, so the clamped quotient is 0.
        squared = step_x * step_x + step_z * step_z
        projected = offset_x * step_x + offset_z * step_z
        along = (projected / np.where(squared > 0.0, squared, 1.0)).clip(0.0, 1.0)

        distance = np.hypot(offset_x - along * step_x, offset_z - along * step_z)
        hit = int(distance.argmin())

        total = self.total_m[hit]
        reached = self.before_m[hit] + along[hit] * self.length_m[hit]
        return Snap(
            edge=int(self.edge[hit]),
            distance_m=float(distance[hit]),
            t=float(reached / total) if total > 0.0 else 0.0,
            y=float(self.start[hit, 1] + along[hit] * self.delta[hit, 1]),
        )


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> FareReport:
    """Read the region's taxi points and write its `fares.json`."""
    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME)
    segments = Segments.of(graph["edges"])

    style = city.fares
    transform = city.game_transform(region_id)
    far_x, far_z = city.region_high(region_id)

    report = FareReport()
    for group in style.groups:
        features = read_feature_collection(
            cached_source(city, group.source, root=sources_root),
            f"fare group '{group.kind}'",
        )["features"]
        report.read += len(features)

        to_projected = transformer(group.crs, city.projected_crs)
        for feature in features:
            position = _point(feature.get("geometry"))
            if position is None:
                continue
            easting, northing = to_projected.transform(*position)
            x, _, z = transform.to_game(easting, northing)
            if not (0.0 <= x <= far_x and 0.0 <= z <= far_z):
                report.outside += 1
                continue

            snap = segments.nearest(x, z)
            if snap.distance_m > style.max_snap_m:
                # Reported rather than raised: a point in a car park is the
                # publisher's business, and one bad row should not cost the
                # region its other fare nodes.
                report.unsnapped += 1
                continue

            node, category = _node(feature, group, style.null_values, (x, snap.y, z), snap, report)
            report.add(node, category, snap.distance_m)

    _write(out_dir, city, region_id, report)
    return report


def _node(
    feature: dict[str, Any],
    group: FareGroup,
    null_values: Sequence[str],
    pos: tuple[float, float, float],
    snap: Snap,
    report: FareReport,
) -> tuple[FareNode, FareCategory]:
    """One fare node, and the category rule it matched.

    The category comes back rather than being counted here: what a node is
    filed under is the report's bookkeeping, not this function's, and `pudo`
    nodes drop theirs before it reaches the contract.
    """
    properties = feature.get("properties") or {}
    category = group.categorise(_text(properties, group.field("category"), null_values) or "")
    return (
        FareNode(
            id=report.next_id(),
            # `pos.y` is the road's height, not the terrain's: the fare node
            # belongs to its edge, and sampling the ground eight metres away
            # could land on a podium. It also keeps this stage free of the
            # height field, which costs six 46 MB sheet reads.
            pos=pos,
            kind=group.kind,
            # Null unless the node is a stand, per the data contract. A pick-up
            # point's category says what may happen there, and that is carried
            # by `pickup`/`dropoff` instead.
            stand_category=category.id if group.kind == TAXI_STAND else None,
            name={
                "en": _text(properties, group.field("name_en"), null_values),
                "zh": _text(properties, group.field("name_zh"), null_values),
            },
            nearest_edge=snap.edge,
            edge_t=round(snap.t, 6),
            pickup=category.pickup,
            dropoff=category.dropoff,
        ),
        category,
    )


def _point(geometry: Any) -> tuple[float, float] | None:
    """The lon/lat of a GeoJSON Point, or None for anything else.

    Both datasets are points throughout. Anything else is skipped rather than
    rejected: a publisher adding a stand drawn as a footprint should not fail
    the build, and `read` minus what was kept makes it visible.
    """
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    return float(coordinates[0]), float(coordinates[1])


def _text(properties: dict[str, Any], name: str, null_values: Sequence[str]) -> str | None:
    return clean_text(properties.get(name), null_values)


def _write(out_dir: Path, city: CityConfig, region_id: str, report: FareReport) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": FARES_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "nodes": [
            {
                "id": node.id,
                "pos": round_position(node.pos),
                "kind": node.kind,
                "stand_category": node.stand_category,
                "name": node.name,
                "nearest_edge": node.nearest_edge,
                "edge_t": node.edge_t,
                "pickup": node.pickup,
                "dropoff": node.dropoff,
            }
            for node in report.nodes
        ],
    }
    path = out_dir / FARES_NAME
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path.stat().st_size


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    report = build_region(city, args.region)
    log.info(
        "%d points read, %d outside the region, %d fare nodes kept",
        report.read,
        report.outside,
        len(report.nodes),
    )
    log.info(
        "  furthest from its road: %.2f m (limit %.1f m)",
        report.worst_snap_m,
        city.fares.max_snap_m,
    )
    for category, count in sorted(report.by_category.items()):
        log.info("  %-16s %d", category, count)
    if report.unsnapped:
        log.warning("  %d points had no road edge within the snap limit", report.unsnapped)
    if report.unnamed:
        log.warning("  %d fare nodes are missing a name in at least one language", report.unnamed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
