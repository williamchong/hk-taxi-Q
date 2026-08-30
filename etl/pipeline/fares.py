"""Published taxi points to fare nodes (`P1-5`).

Reads the taxi-stand and pick-up/drop-off datasets a previous fetch cached,
keeps the ones inside the region, attaches each to the road edge it belongs to,
and writes `fares.json` per the contract in `docs/ARCHITECTURE.md`.

Four measurements off the two sources decide the shape of this — see
`docs/DATA_SOURCES.md`:

- **Snapping is never ambiguous — for the two taxi datasets it was measured
  on.** Every one of the region's 29 points sits 1.18-8.37 m from a road
  centreline, and the runner-up edge is at least 4.28 m further away. These are
  kerbside positions against a centreline graph, so the distance is about half a
  carriageway and the nearest edge is the road the point is on. No tie-breaking
  rule was needed, and inventing one would be guessing.
  ⚠️ **That margin is a fact about those two sources, not about this stage.**
  `P3-14` added 19 tram stops, and one of them — `f_032`, on Hennessy Road under
  the Canal Road Flyover — was won by the deck overhead by 0.80 m and took its
  height, 12.562 m against 3.947 m for the road it is on. Candidates are
  restricted to `elevation_level == 0` in `build_region` for that reason, the
  same restriction `kerbside.py`, `tramway.py` and `arrows.py` make, and
  `FareReport.off_grade_nearer` counts the points it changes the answer for.
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
spellings and the snap limit all arrive from `config/hong_kong.yaml`.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.config import TAXI_STAND, Config, FareCategory, FareGroup, load_config
from pipeline.crs import transformer
from pipeline.documents import round_position, write_document
from pipeline.fetch import cached_source, read_feature_collection
from pipeline.polyline import Segments, Snap
from pipeline.roads import ROADGRAPH_NAME, clean_text, read_graph

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
    # Points with an off-grade edge nearer than the level-0 one they were
    # measured against — the population the restriction in `build_region`
    # changed the answer for. One in Wan Chai (`f_032`, under the Canal Road
    # Flyover), and it is the only number here that can see `Q15`:
    # `worst_snap_m` reads 10.04 m with the restriction and 10.04 m without it,
    # so nothing else this stage publishes moves when the snap is wrong. A city
    # where this is large is the signal to give a group its own rule rather than
    # adding a per-group config boolean speculatively.
    #
    # ⚠️ **Off-grade, not elevated.** The restriction excludes every non-zero
    # level, so this counts a point over a *tunnel* as well as one under a deck —
    # 15 of this region's 797 edges are level -1 — and it should, because a
    # kerbside point taking a tunnel's height is the same defect upside down.
    # ⚠️ **It counts points the snap limit then refuses**, which is why it is
    # incremented above that guard; those points reach no node and no `pos`.
    off_grade_nearer: int = 0
    worst_off_grade_margin_m: float = 0.0
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


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> FareReport:
    """Read the region's taxi points and write its `fares.json`."""
    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, the same restriction `kerbside.py`, `tramway.py` and
    # `arrows.py` all make: the nearest edge of *any* level to a point under a
    # flyover is the flyover. Measured on this region it moves exactly one of 48
    # nodes — `f_032` off the Canal Road Flyover deck and back onto Hennessy
    # Road, 8.6 m down — and leaves the other 47 on the edge they already had,
    # the largest margin difference among them being 0.80 m. `Q15`.
    segments = Segments.of([edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0])
    # Every level the restriction above excludes, which is tunnels as well as
    # decks. This index is never snapped to — it exists so that restriction can
    # be counted, because without it a region where the rule never fires and one
    # where it fires on every node write the same `fares.json`.
    #
    # ⚠️ **The polyline test is `Segments.of`'s refusal, restated because this
    # caller has to survive it.** `of` skips edges under two points and *then*
    # raises if nothing usable is left, so filtering on emptiness alone would
    # pass a list of one-point polylines straight into that raise — out of a
    # stage that has decided it does not need this index at all. Same predicate
    # `roads.py` folds into the list it hands `kerbside.py`.
    off_grade_edges = [
        edge
        for edge in graph["edges"]
        if int(edge["elevation_level"]) != 0 and len(edge["polyline"]) > 1
    ]
    off_grade = Segments.of(off_grade_edges) if off_grade_edges else None

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
            if off_grade is not None:
                margin = snap.distance_m - off_grade.nearest(x, z).distance_m
                if margin > 0.0:
                    # ⚠️ **Recorded before the refusal below, not after** —
                    # `Q58`'s `drawn_gauge_m` trap. Measured under the guard,
                    # this margin would be bounded by `max_snap_m` by
                    # construction and could never report the point the limit
                    # threw away. Pinned by the `max_snap_m` test, whose adrift
                    # point reads a 2 m margin and is then refused.
                    report.off_grade_nearer += 1
                    report.worst_off_grade_margin_m = max(report.worst_off_grade_margin_m, margin)
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
            # ⚠️ Optional roles: a publisher may give positions and no names.
            # TD's tram stops do exactly that — 117 features carrying an
            # `OBJECTID`, a `STOP_ID` and a date — and a null name is what the
            # contract should then carry. `FareReport.unnamed` counts them.
            name={
                "en": _text(properties, group.optional_field("name_en"), null_values),
                "zh": _text(properties, group.optional_field("name_zh"), null_values),
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


def _text(properties: dict[str, Any], name: str | None, null_values: Sequence[str]) -> str | None:
    """One text field, or None where the publisher has no such column at all.

    The two cases collapse on purpose: a column that is absent and a column
    whose value is the source's null sentinel both mean "this node has no name",
    and the contract spells both as `null`.
    """
    if name is None:
        return None
    return clean_text(properties.get(name), null_values)


def _write(out_dir: Path, city: Config, region_id: str, report: FareReport) -> int:
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
    return write_document(out_dir / FARES_NAME, document)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
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
    if report.off_grade_nearer:
        log.warning(
            "  %d points had an off-grade edge nearer than the level-0 one they were measured"
            " against, by up to %.2f m — snap limit refusals included (`Q15`)",
            report.off_grade_nearer,
            report.worst_off_grade_margin_m,
        )
    if report.unnamed:
        log.warning("  %d fare nodes are missing a name in at least one language", report.unnamed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
