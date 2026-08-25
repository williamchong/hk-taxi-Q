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
spellings and the snap limit all arrive from `config/cities/*.yaml`.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.config import TAXI_STAND, CityConfig, FareCategory, FareGroup, load_city
from pipeline.crs import transformer
from pipeline.documents import round_position, write_document
from pipeline.fetch import cached_source, read_feature_collection
from pipeline.roads import (
    ROADGRAPH_NAME,
    clean_text,
    plan_lengths,
    plan_steps,
    read_graph,
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
    # Signed perpendicular offset: `|offset_m| == distance_m`, and the sign says
    # which side of travel the point fell on — **positive is the nearside**, the
    # rail at `TEXCOORD_0`'s `U = 0`.
    #
    # ⚠️ **The expression is `kerbside.SideIndex.nearest`'s, and it is deliberately
    # not restated there or here in prose.** Left of travel is
    # `dot(point - start, (step_z, -step_x))`, which is `surface.mitres`'s normal.
    # A sign flip mirrors every side-keyed feature in the city and still renders
    # as a city, so `tests/test_fares.py` asserts it against `mitres` itself
    # rather than against this comment.
    #
    # Added for `P3-15`, which needs a side and a heading to put a turn arrow in
    # a lane. Folded into the one join rather than written a second time: `Q56`
    # records why two implementations of a join grade nothing —
    # "two implementations disagreeing tells you one is wrong and never which".
    offset_m: float
    # Game-space heading of the segment the point landed on, degrees clockwise
    # from north (`-Z`), in `[0, 360)`. What an arrow's own bearing is graded
    # against.
    heading_deg: float


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
        nothing in it to prefer the street over the deck above.

        ⚠️ **Which edges are candidates is the caller's decision, and every
        caller passes level 0 only** — `fares.build_region`, `tramway.py` and
        `arrows.py`, for the same stated reason. That measured nothing until
        `P3-14` added 19 tram stops: `f_032`, on Hennessy Road under the Canal
        Road Flyover, was won by the deck by a plan margin of 0.80 m and took
        its height — 12.562 m against 3.947 m for the road it is actually on.
        The claim that stood here, that the one level-1 runner-up in the region
        lost by 7 m, was measured on `P1-5`'s taxi points and never covered a
        point beneath a deck.

        A point that belongs to an elevated road still cannot be placed on one:
        narrowing the candidates fixes the direction the sources are wrong in
        here, not the other. That half of `Q15` is open, and
        `FareReport.off_grade_nearer` is what would say so.
        """
        distance, along = self._plan_distances(x, z)
        hit = int(distance.argmin())

        total = self.total_m[hit]
        reached = self.before_m[hit] + along[hit] * self.length_m[hit]
        # Sign only: the magnitude comes from `distance`, which is measured to
        # the *clamped* projection. Past a segment's end the two differ, and the
        # distance is the honest one — a point beyond the end is that far from
        # the road, not that far from its infinite extension.
        offset_x, offset_z = x - self.start[hit, 0], z - self.start[hit, 2]
        step_x, step_z = float(self.delta[hit, 0]), float(self.delta[hit, 2])
        side = offset_x * step_z - offset_z * step_x
        return Snap(
            edge=int(self.edge[hit]),
            distance_m=float(distance[hit]),
            t=float(reached / total) if total > 0.0 else 0.0,
            y=float(self.start[hit, 1] + along[hit] * self.delta[hit, 1]),
            offset_m=float(distance[hit]) if side > 0.0 else -float(distance[hit]),
            heading_deg=float(np.degrees(np.arctan2(step_x, -step_z)) % 360.0),
        )

    def _plan_distances(self, x: float, z: float) -> tuple[np.ndarray, np.ndarray]:
        """Plan distance from `(x, z)` to every segment, and the clamped `along`.

        Extracted so `nearest` and `rivals_within` sweep the graph the **one**
        way. A second copy of this arithmetic is a second implementation of the
        join, and `Q56`'s rule is that two implementations disagreeing tells you
        one is wrong and never which.
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

        return np.hypot(offset_x - along * step_x, offset_z - along * step_z), along

    def rivals_within(self, x: float, z: float, radius_m: float, exclude: int) -> int:
        """How many **other** edges come within `radius_m` of `(x, z)`.

        🔴 **The counter that can see a nearest-edge host go wrong, for a feature
        that stands where nearest-edge is weakest.** `nearest` returns one
        winner and says nothing about how close the runner-up was — and a signal
        head, like a stop line, sits at a junction *mouth* where several edges
        are near. `roadmarks.py` measured that geometry picking the wrong road on
        **43%** of its layer (`Q69`) and answered it with a transverse pick; a
        head is not drawn *across* anything, so it has no such second rule and
        this is the instrument instead.

        ⚠️ **Report-only wherever it is used, and never a bar.** A crowded
        junction is a fact about the city, not a defect in the join — which is
        why this counts rather than refuses.

        Distinct **edges**, not segments: every polyline of the host's own edge
        is near by construction, and so are the several segments a single
        neighbouring road contributes.
        """
        distance, _ = self._plan_distances(x, z)
        near = self.edge[distance <= radius_m]
        return int(np.count_nonzero(np.unique(near) != exclude))


def build_region(
    city: CityConfig,
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


def _write(out_dir: Path, city: CityConfig, region_id: str, report: FareReport) -> int:
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
