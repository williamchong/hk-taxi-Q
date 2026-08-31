"""Where a barrier stands so the player can see the refusal (`P3-29`, `Q19`).

    python -m pipeline.fence --region wan_chai

`clearance.py` publishes how much of each station a car can get through and
`RoadGraph.fits_car` refuses the edges that keep less than the car's own width.
🔴 **A refusal the player cannot see is the defect it was meant to fix.** Round
0 of `P3-9a` ended with three HK drivers stopping at geometry they could not
read, and an invisible predicate repeats that with different plumbing. So this
stage places `game/assets/authored/barriers/barrier.glb` at the mouths of the
fenced set, and the game instances it.

**The set is computed, never hand-kept.** `PLAN.md` requires that, and the
reason is `Q19`'s own history: the population moved when the carve ran and it
will move again. What is read is `clearance.json` against `clearance.car_width_m`
— the same two numbers `fits_car` reads, so the barrier cannot end up standing
somewhere the predicate lets the player drive.

**A mouth is a node, not an edge end.** ⚠️ Barriers go where the *open* network
meets the fenced set, which is not the same as both ends of every fenced edge:
`Q19` names `e222` and `e256` as edges reachable only by way of another blocked
edge, so a barrier on them would stand behind a barrier. Fenced edges are
therefore grouped into connected components and each component is closed at its
**boundary** nodes. That is why this stage builds an adjacency the rest of the
pipeline does not need, and why it cannot be done in the engine: `RoadGraph` is
a spatial index and an attribute table with no adjacency at all.

⚠️ **The facing is published as a direction vector and not as a compass
bearing.** `landmarks.json` carries `rot_y_deg` and one place in the engine
converts it; a second producer of that convention is a sign-error waiting to
happen on a layer where a wrong facing renders as a perfectly good barrier
turned the wrong way (`Q62`, `Q72`). A vector is applied with `Basis.looking_at`
and has no convention to get wrong.

⚠️ **A row of standard units, never one barrier stretched.** `make_barrier.py`
records why: scaling a 2 m prop across a 10 m mouth stretches its posts with it.
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline.clearance import (
    CLEARANCE_NAME,
    CLEARANCE_SCHEMA,
    ClearanceReport,
)
from pipeline.config import Config, load_config
from pipeline.documents import read_document, round_position, write_document
from pipeline.polyline import plan_lengths
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

FENCE_NAME = "fence.json"
FENCE_SCHEMA = 1

# The committed prop this stage places. ⚠️ Under `authored/`, which is the
# licence boundary: this is the project's own CC BY-SA work and never
# government-derived geometry (`LICENSING.md`, hard rule 7).
BARRIER_ASSET = "res://assets/authored/barriers/barrier.glb"


@dataclass
class FenceReport:
    """What one region's fence came to."""

    # Every drivable level-0 edge whose tightest measured station is under the
    # car's own width — the set `RoadGraph.fenced_edge_ids` re-derives.
    fenced: list[int] = field(default_factory=list)
    # Fenced edges grouped by shared node. A component is closed at its
    # boundary, so this is what makes a pocket one closure rather than three.
    components: int = 0
    # ⚠️ **Counted per fenced-edge END, not per node** — two fenced edges meeting
    # at one open junction score two. Every counter in this class is in that
    # frame, and `test_an_end_reachable_only_through_another_fence_is_a_pocket`
    # pins it, because "mouths" reads as nodes and the arithmetic is not.
    #
    # Derived rather than counted: it is the sum of the two outcomes below, and a
    # third field holding the same number is a third thing to forget to update.
    # ⚠️ **The counter that says the pocket rule fired.** A fenced edge end whose
    # node carries other drivable arms and every one of them is fenced too: the
    # street is reachable only through another closure, which is `Q19`'s
    # `e222`/`e256` case, so a barrier here would stand behind a barrier. Zero is
    # legitimate — it means every fenced edge is entered directly — so this is a
    # finding to read, never a bar.
    ends_behind_another_fence: int = 0
    # 🔴 **Not the same thing, and conflating them makes both meaningless.** A
    # node with no other drivable arm at all is a dead end — a cul-de-sac, or a
    # street clipped by the region boundary — and nobody can arrive from there,
    # so there is nothing to close. Counted separately because the first read of
    # this stage reported 13 pockets over 14 *disjoint* components, which is
    # arithmetically impossible and was this distinction missing.
    ends_with_no_way_in: int = 0
    # Barrier units written. A dressed mouth takes a whole row of them.
    barriers: int = 0
    # Ends this stage actually closed, as opposed to units placed at them.
    mouths_dressed: int = 0
    # The span each dressed mouth was measured across — one entry per
    # `mouths_dressed`, and never a placeholder. ⚠️ **A refusal is counted in
    # `mouths_no_width` rather than appended here as a zero**, which is
    # `touchdown_error.py`'s `ends_no_target` shape: an end with no width has no
    # span to record, and a padded zero would be filtered back out before every
    # percentile anyway — as `build_region` had to do while it was padded.
    span_m: list[float] = field(default_factory=list)
    # An end with no published ribbon to span, so nothing could be placed.
    mouths_no_width: int = 0

    @property
    def mouths(self) -> int:
        """Fenced-edge ends the open network arrives at, dressed or not."""
        return self.mouths_dressed + self.mouths_no_width

    def closes(self, unit_width_m: float) -> bool:
        """Every dressed mouth carries a span, and every span carries its row.

        🔴 **The second half is the load-bearing one and the first half alone was
        a tautology.** `place` appends a span and increments `mouths_dressed` in
        the same breath, so `len(span_m) == mouths_dressed` holds by construction
        and no reachable input could fail it — `Q72`'s rule about counters,
        applied to an identity. Recomputing the row width from the published
        spans is falsifiable: an off-by-one in the row loop, a unit width that
        stopped matching the prop, or a span rounded after the row was sized all
        break it, and those are the bugs worth catching.
        """
        if len(self.span_m) != self.mouths_dressed:
            return False
        expected = sum(max(1, math.ceil(span / unit_width_m)) for span in self.span_m)
        return self.barriers == expected


def fenced_edges(graph: dict, clearance: dict, bar_m: float) -> list[int]:
    """Drivable level-0 edges that keep less than `bar_m` clear.

    ⚠️ **The same rule `RoadGraph.fits_car` applies, deliberately duplicated.**
    There is no import to share — the predicate is GDScript — so the two are
    expected to agree and `verify_road_graph.gd` re-derives it a third time from
    `city.json`'s own arrays. A divergence is a finding, never a bar to retune.
    """
    levels = {int(edge["id"]): int(edge.get("elevation_level", 0)) for edge in graph["edges"]}
    # `clearance.json`'s array *is* `ClearanceReport.corridor_m` serialised, so the
    # report is reconstructed rather than its `min` restated here. That keeps one
    # definition of "the narrowest measured station" — refusals filtered before
    # the `min`, never clamped after, because `-1.0` is the smallest number in any
    # row it appears in. `tools/narrowing.py` reuses it the same way.
    corridor = {int(row["edge"]): list(row["clear_width_m"]) for row in clearance["clearance"]}
    report = ClearanceReport(corridor_m=corridor)
    return sorted(edge_id for edge_id, _ in report.starved(bar_m) if levels.get(edge_id, 1) == 0)


def _adjacency(graph: dict) -> tuple[dict[int, list[int]], dict[int, tuple[int, int]]]:
    """Node to drivable level-0 edge ids, and edge id to its two nodes."""
    at_node: dict[int, list[int]] = {}
    ends: dict[int, tuple[int, int]] = {}
    for edge in graph["edges"]:
        if int(edge.get("elevation_level", 0)) != 0:
            continue
        edge_id = int(edge["id"])
        nodes = (int(edge["from"]), int(edge["to"]))
        ends[edge_id] = nodes
        for node in nodes:
            at_node.setdefault(node, []).append(edge_id)
    return at_node, ends


def _components(fenced: list[int], ends: dict[int, tuple[int, int]]) -> list[list[int]]:
    """Fenced edges grouped by shared node, so a pocket is closed once.

    A plain flood fill over the fenced subgraph. Not a union-find: the fenced
    set is tens of edges, and the fill is what makes the boundary rule below
    readable.
    """
    remaining = set(fenced)
    groups = []
    while remaining:
        seed = remaining.pop()
        group = [seed]
        frontier = [seed]
        while frontier:
            for node in ends[frontier.pop()]:
                for edge_id in list(remaining):
                    if node in ends[edge_id]:
                        remaining.discard(edge_id)
                        group.append(edge_id)
                        frontier.append(edge_id)
        groups.append(sorted(group))
    return sorted(groups)


@dataclass(frozen=True)
class Placement:
    """One barrier unit, in game-space metres."""

    edge: int
    node: int
    # A `list` rather than a tuple because it comes from
    # `documents.round_position`, which is the shared millimetre-and-no-negative-
    # zero treatment every position in the data contract gets.
    position: list[float]
    # 🔴 A direction, not a bearing. See the module docstring: a second producer
    # of `landmarks.json`'s compass convention is a sign error waiting to happen
    # on a layer where the wrong facing renders perfectly.
    facing: tuple[float, float, float]


def _half_width_at_end(drawn: dict, edge_id: int, at_start: bool) -> float | None:
    """The drawn half-width at one END of an edge, or `None` where none was published.

    Takes the end rather than a station index on purpose: the only two stations a
    mouth can sit at are the first and the last, and an integer parameter needed a
    clamp — which would have silently absorbed any disagreement between
    `half_width_m`'s length and the polyline's, the "confined by construction"
    masking this repo refuses elsewhere (`Q58`).
    """
    halves = (drawn.get(edge_id) or {}).get("half_width_m") or []
    if not halves:
        return None
    return float(halves[0] if at_start else halves[-1])


def _mouth_frame(
    points: np.ndarray, node_is_start: bool, inset_m: float
) -> tuple[np.ndarray, np.ndarray]:
    """Where across the edge a barrier stands, and which way it faces.

    `inset_m` along the edge from the node, so the barrier stands *in* the
    closed street rather than in the junction it is entered from — a barrier on
    the node itself blocks every other arm of that junction too.
    """
    ordered = points if node_is_start else points[::-1]
    along = plan_lengths(ordered)
    # Clamped to the edge's own length: a street shorter than the inset is
    # closed at its far end rather than beyond it.
    reach = min(inset_m, float(along[-1]))
    at = np.array(
        [np.interp(reach, along, ordered[:, axis]) for axis in range(3)], dtype=np.float64
    )
    # The tangent taken over the segment the barrier landed on, pointing away
    # from the node — so the barrier faces back along it, at the car.
    ahead = np.searchsorted(along, reach, side="right")
    ahead = int(min(max(ahead, 1), len(ordered) - 1))
    tangent = ordered[ahead] - ordered[ahead - 1]
    tangent[1] = 0.0
    length = float(np.linalg.norm(tangent))
    if length <= 0.0:
        # A zero-length segment cannot say which way anything faces. Refused
        # rather than defaulted, because a defaulted facing is the defect this
        # layer cannot see in a frame.
        raise ValueError("an edge segment has no plan length, so a mouth has no facing")
    return at, tangent / length


def place(
    graph: dict, drawn: dict, fenced: list[int], *, inset_m: float, unit_width_m: float
) -> tuple[list[Placement], FenceReport]:
    """Every barrier unit the fenced set needs, and what it came to."""
    report = FenceReport(fenced=list(fenced))
    at_node, ends = _adjacency(graph)
    points = {
        int(edge["id"]): np.asarray(edge["polyline"], dtype=np.float64) for edge in graph["edges"]
    }
    blocked = set(fenced)
    # ⚠️ Grouping is for the published counter and nothing else. The boundary rule
    # below is decided entirely by `blocked` and `at_node`, so iterating the
    # components would be exactly iterating `fenced` with two extra levels of
    # nesting. The **adjacency** is what is load-bearing here, not the grouping.
    report.components = len(_components(fenced, ends))

    placements: list[Placement] = []
    for edge_id in fenced:
        for node in ends[edge_id]:
            # An end is a mouth when there is a way in from outside the fenced
            # set. ⚠️ Read over *drivable* edges only: an off-grade ramp meeting
            # this node is not a way in, because `Q13` refuses to hand a car an
            # off-grade edge at all.
            arms = [other for other in at_node[node] if other != edge_id]
            if not arms:
                # Nobody can arrive here at all — see `ends_with_no_way_in`.
                report.ends_with_no_way_in += 1
                continue
            if all(other in blocked for other in arms):
                report.ends_behind_another_fence += 1
                continue
            at_start = ends[edge_id][0] == node
            half = _half_width_at_end(drawn, edge_id, at_start)
            if half is None or half <= 0.0:
                report.mouths_no_width += 1
                continue
            span = round(2.0 * half, 3)
            report.span_m.append(span)
            at, tangent = _mouth_frame(points[edge_id], at_start, inset_m)
            # Across the carriageway rather than along it. ⚠️ **This is
            # `carriageway._stations`' frame — RIGHT of travel — and not
            # `surface.mitres`' left one.** The two are opposite on purpose and
            # must not be "made consistent" (`Q78`); this may hold either because
            # the offsets below are symmetric about zero, so the row is sign-free
            # exactly as `carriageway.py`'s own licence says.
            across = np.array([-tangent[2], 0.0, tangent[0]], dtype=np.float64)
            units = max(1, math.ceil(span / unit_width_m))
            report.mouths_dressed += 1
            for index in range(units):
                offset = (index + 0.5) * unit_width_m - 0.5 * units * unit_width_m
                centre = at + across * offset
                placements.append(
                    Placement(
                        edge=edge_id,
                        node=node,
                        position=round_position(tuple(float(v) for v in centre)),
                        # Back along the edge, at the car coming in.
                        facing=tuple(round(float(-value), 4) for value in tangent),
                    )
                )
    report.barriers = len(placements)
    return placements, report


def _document(
    city: Config, region_id: str, placements: list[Placement], report: FenceReport
) -> dict:
    """Written unconditionally, `carve.json`'s precedent: a missing file means
    the stage never ran, not that there was nothing to fence."""
    return {
        "schema_version": FENCE_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "asset": BARRIER_ASSET,
        "fenced_edges": report.fenced,
        "components": report.components,
        "mouths": report.mouths,
        "ends_behind_another_fence": report.ends_behind_another_fence,
        "ends_with_no_way_in": report.ends_with_no_way_in,
        "mouths_no_width": report.mouths_no_width,
        "span_m": report.span_m,
        "barriers": [
            {
                "edge": item.edge,
                "node": item.node,
                "position": list(item.position),
                "facing": list(item.facing),
            }
            for item in placements
        ],
    }


def build_region(city: Config, region_id: str, *, out_root: Path | None = None) -> int:
    """Place the fence over the region already built in its out dir."""
    out_dir = city.out_dir(region_id, out_root)
    rebuild = f"python -m pipeline --region {region_id}"
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    surface = read_document(out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, rebuild)
    drawn = {int(entry["edge"]): entry for entry in surface.get("carriageway", [])}

    if city.clearance is None:
        # Nothing to fence against. The document is still written, so a build
        # without a `clearance:` block is distinguishable from one where this
        # stage never ran.
        log.info("  no clearance block, so nothing is fenced")
        return write_document(out_dir / FENCE_NAME, _document(city, region_id, [], FenceReport()))

    clearance = read_document(out_dir / CLEARANCE_NAME, CLEARANCE_SCHEMA, rebuild)
    bar_m = float(city.clearance.car_width_m)
    fenced = fenced_edges(graph, clearance, bar_m)
    if city.fence is None:
        # 🔴 **The bar without the dressing, and it is a real state rather than a
        # half-configured one.** `clearance:` decides which edges the *predicate*
        # refuses and `fence:` decides where a barrier stands, so a city can
        # publish the fenced set and dress none of it — `RoadGraph.fits_car`
        # still works and the player still meets an undressed wall. `Q19` forbids
        # *shipping* that, which is a review question rather than a build one, so
        # this is logged loudly and published rather than refused.
        log.warning(
            "  %d edges fenced at the car's %.2f m and NO fence block to dress them"
            " — Q19 forbids shipping an undressed refusal",
            len(fenced),
            bar_m,
        )
        return write_document(
            out_dir / FENCE_NAME, _document(city, region_id, [], FenceReport(fenced=fenced))
        )

    placements, report = place(
        graph,
        drawn,
        fenced,
        inset_m=city.fence.inset_m,
        unit_width_m=city.fence.unit_width_m,
    )
    if not report.closes(city.fence.unit_width_m):
        # The identity that says every mouth is accounted for. Raised rather
        # than logged: a stage whose own partition does not close is publishing
        # a number nobody can read.
        raise ValueError(
            f"{report.barriers} barrier units against {len(report.span_m)} spans over "
            f"{report.mouths_dressed} dressed mouths — the row width and the published "
            f"spans disagree"
        )

    log.info(
        "  %d edges fenced at the car's %.2f m, in %d component(s); %d mouths,"
        " %d behind another fence, %d with no way in",
        len(fenced),
        bar_m,
        report.components,
        report.mouths,
        report.ends_behind_another_fence,
        report.ends_with_no_way_in,
    )
    if report.mouths_no_width:
        log.warning("  %d mouths had no published ribbon to span", report.mouths_no_width)
    spans = [span for span in report.span_m if span > 0.0]
    if spans:
        log.info(
            "  %d barrier units across spans p50 %.2f m, max %.2f m",
            report.barriers,
            float(np.percentile(spans, 50)),
            max(spans),
        )
    return write_document(out_dir / FENCE_NAME, _document(city, region_id, placements, report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)
    build_region(city, args.region)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
