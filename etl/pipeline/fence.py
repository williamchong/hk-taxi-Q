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

🔴 **This stage closes TWO populations and they are published apart (`Q103`).**
The first is the one above: `clearance.py`'s starved set, edges too narrow for
the car. The second is the off-grade touchdowns — ramps and portals that are
wide enough and simply are not *graded*. `Q13` refuses to hand a car an
off-grade edge, but that is a **graph** refusal: `surface.py` still draws the
ribbon and `roads.glb` still carries its collider, so once `Q90` ramped the
touchdowns the network became reachable by driving at it while `clearance.py`,
`centreline_error.py`, `carriageway_occupancy.py`, `street_tracker.gd` and the
wrong-way monitor all went on gating at level 0. A user drove `e208` FLEMING
ROAD into the flyover's own parapet, standing 1.08 m from a centreline inside a
ribbon spanning ±3.20 m, with every counter in the bundle reading correctly.

⚠️ **`fenced_edges` does not gain those edges and must not.** It is the set
`RoadGraph.fenced_edge_ids` re-derives from the same two numbers `fits_car`
reads, and `verify_fence.gd` joins the two; a ramp swept into it would assert
that a 6.40 m deck is too narrow for a 1.80 m car. They travel as
`touchdown_edges` instead, and the barrier rows are identical because a mouth
is a mouth.

⚠️ **This is a closure, not a fix.** It restores *reachable ⟺ graded* and buys
the time to open the network properly; `PLAN.md` `P4-1` owns the other ending.

**The third population is the region's own edge (`Q143`).** A street the clip
cut ends on the rectangle with nothing past it: no tile, no ground, no
neighbour. `GAME_DESIGN.md` calls the map edges diegetic, and they are — for
the harbour and the escarpment. The streets that simply stop on the line (67
in Wan Chai and 19 in Causeway Bay, 2026-09-25) are not, and a car driven down
one leaves the world. So every open dead end
within `fence.clipped_within_m` of the rectangle is closed with the same row,
stood `inset_m` inside the map and **facing the interior**, at the car coming
out. ⚠️ **A node any `foreign_edges` run touches is never closed**: past that
node the road is the neighbour's, and that is what "not yet connected to
another region" means, read off the graph rather than declared. They travel
as `clipped_edges`, a third list, on the two-populations reasoning above — a
clipped end is neither narrow nor ungraded, and `verify_fence.gd` re-derives
the set from the graph's own nodes, the way it re-derives `fenced_edges`.

⚠️ **The prop is 192 triangles and the row is the layer's whole cost**, so the
unit count is the number to watch: 90 → 253 units is 17,280 → **48,576**
triangles. That is 4.9% of the desktop `< 1M` budget and **16.2% of the mobile
`< 300k`** one (`ARCHITECTURE.md`). Mobile is unbuilt and blocked on `P0-3b`, so
nothing ships against that row today — but a static barrier layer taking a sixth
of it is the figure to have on hand when it is. Draw calls are unaffected: the
whole row is one `MultiMesh` (`fence.gd`), measured 87 → 89 for the layer.
"""

from __future__ import annotations

import argparse
import logging
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline.clearance import (
    CLEARANCE_NAME,
    CLEARANCE_SCHEMA,
    ClearanceReport,
)
from pipeline.config import Config, load_config
from pipeline.crs import inside_plan
from pipeline.documents import read_document, round_position, write_document
from pipeline.polyline import plan_lengths
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

FENCE_NAME = "fence.json"
FENCE_SCHEMA = 3

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

    # ---- the touchdown population (`Q103`), counted apart from the one above --
    #
    # 🔴 **Separate counters because they are separate populations** — the module
    # docstring says why the two sets are separate at all. The counting rule is
    # the part that belongs here: a single `mouths` total would move when either
    # population moved and say which neither, which is exactly the mistake
    # `ends_behind_another_fence` and `ends_with_no_way_in` were split to avoid.
    #
    # The levels asked for, published so the document says what it closed rather
    # than leaving a reader to infer it from the edges that happen to appear.
    touchdown_levels: list[int] = field(default_factory=list)
    # Off-grade edge ends closed, one per dressed touchdown.
    touchdowns_dressed: int = 0
    # The off-grade edges those ends belong to, de-duplicated: one ramp closed
    # at both its ends is one edge here and two in `touchdowns_dressed`.
    # ⚠️ **Recorded where it is decided rather than differenced out of
    # `barriers` against `fenced` afterwards.** The two sets are disjoint by
    # construction — `fenced_edges` filters to level 0 and this filters away
    # from it — and a set difference would keep working, silently, on the day
    # that stopped being true.
    touchdown_edges: list[int] = field(default_factory=list)
    # A touchdown whose off-grade edge published no ribbon to span. ⚠️ Counted,
    # never appended to `span_m` as a zero — `mouths_no_width`'s own rule, and
    # `touchdown_error.py`'s `ends_no_target` shape.
    touchdowns_no_width: int = 0

    # ---- the clipped population (`Q143`), counted apart from both above -----
    #
    # The reach asked for, published so the document says what rule closed
    # these ends; `None` is the pre-`Q143` build and every counter below is 0.
    clipped_within_m: float | None = None
    # The rectangle those ends were measured against (`Config.region_high`),
    # published so `verify_fence.gd` can re-derive the set — `city.json`'s
    # `bounds_game` is the content's union, not this. Recorded where it is
    # decided, beside the reach, rather than threaded past the report.
    region_high: tuple[float, float] | None = None
    # Open edge ends the region's clip cut, closed — one per row placed.
    clipped_dressed: int = 0
    # The edges those ends belong to, de-duplicated on `touchdown_edges`' terms:
    # a street clipped at both ends (across a corner) is one edge here and two
    # in `clipped_dressed`. Disjoint from both other lists by construction — a
    # fenced edge's clipped end is already behind that edge's own barrier.
    clipped_edges: list[int] = field(default_factory=list)
    # A clipped end whose edge published no ribbon to span. Counted, never a
    # zero in `span_m` — `mouths_no_width`'s own rule.
    clipped_no_width: int = 0

    @property
    def clipped(self) -> int:
        """Clipped edge ends found at the region's rectangle, dressed or not."""
        return self.clipped_dressed + self.clipped_no_width

    @property
    def mouths(self) -> int:
        """Fenced-edge ends the open network arrives at, dressed or not."""
        return self.mouths_dressed + self.mouths_no_width

    @property
    def touchdowns(self) -> int:
        """Off-grade edge ends meeting the open network, dressed or not."""
        return self.touchdowns_dressed + self.touchdowns_no_width

    def closes(self, unit_width_m: float) -> bool:
        """Every dressed mouth carries a span, and every span carries its row.

        🔴 **The second half is the load-bearing one and the first half alone was
        a tautology.** `place` appends a span and increments its dressed counter
        in the same breath, so the first equality holds by construction and no
        reachable input could fail it — `Q72`'s rule about counters, applied to
        an identity. Recomputing the row width from the published spans is
        falsifiable: an off-by-one in the row loop, a unit width that stopped
        matching the prop, or a span rounded after the row was sized all break
        it, and those are the bugs worth catching.

        ⚠️ **All three populations are covered by one identity on purpose.**
        They are counted apart because they mean different things, but every
        span in `span_m` owes its row whichever list it came from, and a second
        identity over a second span list would be a second thing to forget.
        """
        dressed = self.mouths_dressed + self.touchdowns_dressed + self.clipped_dressed
        if len(self.span_m) != dressed:
            return False
        expected = sum(max(1, math.ceil(span / unit_width_m)) for span in self.span_m)
        return self.barriers == expected


def fenced_edges(
    graph: dict, clearance: dict, bar_m: float, closed_levels: Iterable[int] = ()
) -> list[int]:
    """Drivable edges that keep less than `bar_m` clear, on every open level.

    ⚠️ **The same rule `RoadGraph.fits_car` applies, deliberately duplicated.**
    There is no import to share — the predicate is GDScript — so the two are
    expected to agree and `verify_road_graph.gd` re-derives it a third time from
    `city.json`'s own arrays. A divergence is a finding, never a bar to retune.

    🔴 **The level filter is `closed_levels` since `P4-1` opened the network,
    and it is no longer the literal `0`.** It was a hardcoded level-0 test whose
    stated reason was that *"the off-grade network is closed ALREADY, at its
    touchdowns"* — true while `fence.touchdown_levels` closed level 1, and false
    the moment it stopped. The rule it always meant is the one written here: a
    barrier belongs on an edge the player can reach, so **fence every level the
    touchdown closure leaves open**, and skip the levels already shut at their
    mouths, where a second barrier would stand behind the first
    (`ends_behind_another_fence`'s case, split across two populations that do
    not share the counter).

    ⚠️ **It is at 0 of 45 open off-grade edges on this bundle and it is
    reachable** — `e208` FLEMING ROAD reads 2.00 m, under the lane bar and over
    the car's own 1.80 m — so read the tests rather than the count, which is
    `Q72`'s rule about a counter that cannot go non-zero.

    ⚠️ An unmeasured edge cannot be starved: `starved` filters `-1.0` before its
    `min`, so a level nothing has measured contributes nothing here whatever
    this filter says. The filter is about *reachability*, not about coverage.
    """
    shut = set(closed_levels)
    levels = {int(edge["id"]): int(edge.get("elevation_level", 0)) for edge in graph["edges"]}
    # `clearance.json`'s array *is* `ClearanceReport.corridor_m` serialised, so the
    # report is reconstructed rather than its `min` restated here. That keeps one
    # definition of "the narrowest measured station" — refusals filtered before
    # the `min`, never clamped after, because `-1.0` is the smallest number in any
    # row it appears in. `tools/narrowing.py` reuses it the same way.
    corridor = {int(row["edge"]): list(row["clear_width_m"]) for row in clearance["clearance"]}
    report = ClearanceReport(corridor_m=corridor)
    # 🔴 **Membership, not a sentinel level.** This read
    # `levels.get(edge_id, next(iter(shut), 1)) not in shut`, meaning to default
    # an unknown id to something closed — and with `shut` empty, which is what a
    # city with no `fence:` block passes, the default became `1`, `1 not in
    # set()` was true, and an id the graph does not carry was fenced. Asking
    # whether the graph carries it says the thing directly and cannot depend on
    # an arbitrary pick from an unordered set.
    return sorted(
        edge_id
        for edge_id, _ in report.starved(bar_m)
        if edge_id in levels and levels[edge_id] not in shut
    )


def _adjacency(
    graph: dict, closed_levels: Iterable[int]
) -> tuple[dict[int, list[int]], dict[int, tuple[int, int]]]:
    """Node to open edge ids, and edge id to its two nodes.

    🔴 **The same level policy `fenced_edges` applies, and it must be the same
    or `place` raises.** This filtered to the literal level 0 while that one
    took `closed_levels`, so an open off-grade edge could reach `fenced` and
    then have no entry in `ends` — `KeyError` on the first barrier row across a
    live ramp. It could not fire while `touchdown_levels` closed level 1, and
    `P4-1` opened it; the 45 tests stayed green because none of them ran
    `place` over an off-grade edge.

    ⚠️ **`at_node` is the "way in" test, so widening it is not incidental.** An
    open ramp meeting a fenced end *is* a way in now, where `Q13` used to say it
    could never be one — which is what makes `ends_with_no_way_in` still mean a
    dead end rather than "the only arm is a ramp".
    """
    shut = set(closed_levels)
    at_node: dict[int, list[int]] = {}
    ends: dict[int, tuple[int, int]] = {}
    for edge in graph["edges"]:
        if int(edge.get("elevation_level", 0)) in shut:
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


def touchdown_mouths(graph: dict, levels: tuple[int, ...]) -> list[tuple[int, int, bool]]:
    """`(edge, node, at_start)` for every off-grade end meeting the open network (`Q103`).

    🔴 **The population is topological, and that is the claim worth stating.**
    An off-grade edge is reachable because its ramp touches down onto a street,
    and a touchdown is a node the two share — `roads._descend` gates on exactly
    that, "a level-0 edge at the node", which is why the count here is the same
    36 nodes `P4-3` measures its ramp steps at. Closing all of them closes the
    whole off-grade subgraph, because an interior ramp can only be entered
    through one of them.

    ⚠️ **What it does NOT cover is a car leaving the road.** A deck that dips
    near a street it shares no node with is reachable by driving at it, and no
    node-based rule can see that. The same hole `Q19`'s fence has, named here
    rather than left implicit.

    ⚠️ Levels are asked for rather than assumed: `elevation_levels` maps 1 and
    -1 in this region and a tunnel portal is as ungraded as a flyover ramp, but
    which of them the slice closes is a config decision (`fence.touchdown_levels`).
    """
    wanted = set(levels)
    if not wanted:
        return []

    open_network: set[int] = set()
    off_grade: list[tuple[int, int, bool]] = []
    for edge in graph["edges"]:
        level = int(edge.get("elevation_level", 0))
        nodes = (int(edge["from"]), int(edge["to"]))
        if level == 0:
            open_network.update(nodes)
        elif level in wanted:
            # ⚠️ **Which end is carried out rather than recovered.** The caller
            # needs it to read the ribbon's half-width at the right end, and
            # rebuilding an edge-to-nodes map over the whole graph to recover
            # what this loop already has in `nodes` is the redundant half of a
            # fact, which drifts the day either side changes.
            off_grade.extend(
                (int(edge["id"]), node, index == 0) for index, node in enumerate(nodes)
            )
    return sorted(row for row in off_grade if row[1] in open_network)


def clipped_ends(
    graph: dict,
    closed_levels: Iterable[int],
    region_high: tuple[float, float],
    within_m: float,
) -> list[tuple[int, int, bool]]:
    """`(edge, node, at_start)` for every open dead end on the region's rectangle (`Q143`).

    Three tests, and each one is a population deliberately left out:

    - **One open arm at the node**, over the same level policy `fenced_edges`
      and `_adjacency` apply. A junction on the line is entered from its other
      arms and is not a dead end; a closed-level edge meeting the node is shut
      at its own touchdown and is not a way in.
    - **On no `foreign_edges` run.** Since `P5-7e` a road that crosses into a
      declared neighbour is kept whole and the far half published under that
      list, so a boundary node the neighbour continues is the one kind of edge
      end that must stay open — it is the join. Read off the graph, never off
      `Config.neighbours`: a neighbour declared and not built would otherwise
      leave the line open on the promise of a bundle that is not there.
    - **Within `within_m` of the rectangle's line, from the inside**, tested on
      the edge's own polyline end rather than `nodes[]`, so the barrier and the
      test share one point. A cul-de-sac inside the region is a dead end the
      player can turn round in and gets nothing. ⚠️ **An end OUTSIDE the
      rectangle gets nothing either, and the first build closed five of them**:
      an owned run that crosses into the neighbour is kept whole (`P5-7`), so
      its far end stands on the neighbour's ground with degree 1 in *this*
      graph — COTTON PATH `e691` ends at a Causeway Bay junction 51 m past the
      line. A signed distance read those as "on the line"; the test is the
      unsigned distance to the nearest side, and the point within the
      rectangle grown by `within_m`.

    ⚠️ `region_high` is the region's own rectangle (`Config.region_high`), never
    `city.json`'s `bounds_game`, which is the union of the content and reaches
    past the line wherever a building overhangs its tile (`export.py`).
    """
    at_node, ends = _adjacency(graph, closed_levels)
    foreign_nodes: set[int] = set()
    for edge in graph.get("foreign_edges", []):
        foreign_nodes.update((int(edge["from"]), int(edge["to"])))
    points = {int(edge["id"]): edge["polyline"] for edge in graph["edges"]}
    grown_low = (-within_m, -within_m)
    grown_high = (region_high[0] + within_m, region_high[1] + within_m)
    found: list[tuple[int, int, bool]] = []
    for node, arms in at_node.items():
        if len(arms) != 1 or node in foreign_nodes:
            continue
        edge_id = arms[0]
        at_start = ends[edge_id][0] == node
        x, _, z = points[edge_id][0 if at_start else -1]
        line_m = min(abs(x), abs(z), abs(region_high[0] - x), abs(region_high[1] - z))
        if line_m > within_m or not inside_plan(x, z, grown_low, grown_high):
            continue
        found.append((edge_id, node, at_start))
    return sorted(found)


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


def _ribbon_at_end(drawn: dict, edge_id: int, at_start: bool) -> tuple[float, float] | None:
    """The drawn ribbon at one END of an edge as `(half width, offset)`, or `None`
    where none was published.

    🔴 **Both, because the ribbon is `[offset - half, offset + half]` and never
    `±half` about the centreline (`Q106`, `Q107`, `P3-33c`).** This read the
    half-width alone until `P3-35d` and laid every row about the centreline: at
    KA NING PATH `e45` the ribbon's mouth is 2.41 m to one side, so a 8.5 m row
    stood with 2.4 m of open road past one end and 2.4 m of barrier on the footway
    past the other. `offset_m` is read with `[]`, never a `.get` default: the
    manifest's schema is pinned, and a default could only fire on a document that
    had stopped publishing it — silently re-centring every row.

    Takes the end rather than a station index on purpose: the only two stations a
    mouth can sit at are the first and the last, and an integer parameter needed a
    clamp — which would have silently absorbed any disagreement between
    `half_width_m`'s length and the polyline's, the "confined by construction"
    masking this repo refuses elsewhere (`Q58`).
    """
    row = drawn.get(edge_id) or {}
    halves = row.get("half_width_m") or []
    if not halves:
        return None
    end = 0 if at_start else -1
    return float(halves[end]), float(row["offset_m"][end])


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


def _dress(
    edge_id: int,
    node: int,
    *,
    points: np.ndarray,
    at_start: bool,
    half: float,
    offset: float,
    inset_m: float,
    unit_width_m: float,
    faces_node: bool = True,
) -> tuple[list[Placement], float]:
    """One mouth's row of units, and the span it was laid across.

    Shared by all three populations rather than written thrice. ⚠️ They differ
    in *which* ends they close and in nothing else — a row across a ramp mouth
    is a row across a street mouth — so a second copy here would be two places
    for the pitch, the centring and the facing to drift apart, on a layer where
    all three render perfectly when wrong (`Q62`).

    `faces_node` is the one thing a clipped end reverses: at a mouth the car
    arrives *from* the node, at the region's edge it arrives from the interior
    and the node is the void, so the row faces back down the street instead.
    ⚠️ The prop has no front (`tools/make_barrier.py`), so this cannot be seen
    in a frame; it is kept right so the day it grows one it stands right.
    """
    span = round(2.0 * half, 3)
    at, tangent = _mouth_frame(points, at_start, inset_m)
    # Across the carriageway rather than along it: RIGHT of `tangent`, which
    # runs from the node INTO the street.
    across = np.array([-tangent[2], 0.0, tangent[0]], dtype=np.float64)
    # 🔴 **The row is centred on the RIBBON, and that makes the sign load-bearing.**
    # While the row was symmetric about the centreline `across` could be either
    # hand (`carriageway.py`'s own licence). `offset` is positive to the NEARSIDE
    # — left of the PUBLISHED direction (`surface.mitres`, `drawnroad.nearside`) —
    # and `tangent` is the published direction only at the start mouth. So the
    # nearside is `-across` there and `+across` at the end mouth. A flip here
    # doubles the error it exists to remove and renders as a row of barriers;
    # `test_the_row_stands_across_the_ribbon_at_both_mouths` is the ratchet.
    middle = at + across * (-offset if at_start else offset)
    units = max(1, math.ceil(span / unit_width_m))
    placements = []
    for index in range(units):
        along_row = (index + 0.5) * unit_width_m - 0.5 * units * unit_width_m
        centre = middle + across * along_row
        placements.append(
            Placement(
                edge=edge_id,
                node=node,
                position=round_position(tuple(float(v) for v in centre)),
                # At the car coming in: back along the edge toward the node,
                # or down the street when the node is the region's edge.
                facing=tuple(round(float(-value if faces_node else value), 4) for value in tangent),
            )
        )
    return placements, span


def _dress_open_end(
    edge_id: int,
    node: int,
    at_start: bool,
    *,
    points: dict[int, np.ndarray],
    drawn: dict,
    inset_m: float,
    unit_width_m: float,
    faces_node: bool = True,
) -> tuple[list[Placement], float] | None:
    """One end the open network arrives at, dressed, or `None` where its edge
    published no ribbon to span.

    The plumbing the touchdown and clipped loops share — ribbon lookup, the
    no-width refusal, the row. ⚠️ **The bookkeeping stays at the call site**:
    which counter a refusal lands in and which list the edge joins is what
    keeps the populations apart, so this returns and never counts.
    """
    ribbon = _ribbon_at_end(drawn, edge_id, at_start)
    if ribbon is None or ribbon[0] <= 0.0:
        return None
    half, offset = ribbon
    return _dress(
        edge_id,
        node,
        points=points[edge_id],
        at_start=at_start,
        half=half,
        offset=offset,
        inset_m=inset_m,
        unit_width_m=unit_width_m,
        faces_node=faces_node,
    )


def place(
    graph: dict,
    drawn: dict,
    fenced: list[int],
    *,
    inset_m: float,
    unit_width_m: float,
    touchdown_levels: tuple[int, ...] = (),
    region_high: tuple[float, float] | None = None,
    clipped_within_m: float | None = None,
) -> tuple[list[Placement], FenceReport]:
    """Every barrier unit the three closed populations need, and what they came to.

    ⚠️ **The levels rather than the mouths, so the report cannot be half-filled.**
    Handed a mouth list, this function could publish `touchdown_edges` while its
    caller forgot to set `touchdown_levels` beside it — a document saying which
    ramps it closed and refusing to say under what rule. Owning the call makes
    that state unreachable rather than merely unlikely.
    """
    if clipped_within_m is not None and region_high is None:
        # Refused rather than defaulted: the rectangle is what the closure is
        # measured against, and no default rectangle is the region's.
        raise ValueError("clipped_within_m needs the region's own rectangle (region_high)")
    report = FenceReport(
        fenced=list(fenced),
        touchdown_levels=list(touchdown_levels),
        clipped_within_m=clipped_within_m,
        region_high=region_high,
    )
    at_node, ends = _adjacency(graph, touchdown_levels)
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
            # set. ⚠️ Read over the **open** edges — every level the touchdown
            # closure leaves reachable. It was level 0 alone while `Q13` refused
            # to hand a car an off-grade edge at all; since `P4-1` an open ramp
            # meeting this node is a way in like any other arm.
            arms = [other for other in at_node[node] if other != edge_id]
            if not arms:
                # Nobody can arrive here at all — see `ends_with_no_way_in`.
                report.ends_with_no_way_in += 1
                continue
            if all(other in blocked for other in arms):
                report.ends_behind_another_fence += 1
                continue
            at_start = ends[edge_id][0] == node
            ribbon = _ribbon_at_end(drawn, edge_id, at_start)
            if ribbon is None or ribbon[0] <= 0.0:
                report.mouths_no_width += 1
                continue
            half, offset = ribbon
            row, span = _dress(
                edge_id,
                node,
                points=points[edge_id],
                at_start=at_start,
                half=half,
                offset=offset,
                inset_m=inset_m,
                unit_width_m=unit_width_m,
            )
            report.span_m.append(span)
            report.mouths_dressed += 1
            placements.extend(row)

    # ---- the touchdown population (`Q103`) ---------------------------------
    #
    # ⚠️ **No boundary rule, and that is a difference rather than an omission.**
    # The starved set needs one because a fenced street can be entered only
    # through another fenced street (`Q19`'s `e222`/`e256`), so a barrier there
    # would stand behind a barrier. A touchdown is by construction a node where
    # the *open* network arrives, so every one of them is a way in.
    for edge_id, node, at_start in touchdown_mouths(graph, touchdown_levels):
        dressed = _dress_open_end(
            edge_id,
            node,
            at_start,
            points=points,
            drawn=drawn,
            inset_m=inset_m,
            unit_width_m=unit_width_m,
        )
        if dressed is None:
            report.touchdowns_no_width += 1
            continue
        row, span = dressed
        report.span_m.append(span)
        report.touchdowns_dressed += 1
        if edge_id not in report.touchdown_edges:
            report.touchdown_edges.append(edge_id)
        placements.extend(row)

    # ---- the clipped population (`Q143`) ------------------------------------
    #
    # ⚠️ **A fenced edge's clipped end is skipped, not counted.** That end is
    # `ends_with_no_way_in`'s already — counted there as the dead end it is —
    # and its street is closed at its mouth, so a row here would stand behind a
    # barrier (`Q19`'s pocket, at the third population). A touchdown edge cannot
    # reach here at all: it sits on a closed level and `clipped_ends` reads the
    # open ones.
    if clipped_within_m is not None:
        assert region_high is not None  # the ValueError above guards; narrows the type
        for edge_id, node, at_start in clipped_ends(
            graph, touchdown_levels, region_high, clipped_within_m
        ):
            if edge_id in blocked:
                continue
            dressed = _dress_open_end(
                edge_id,
                node,
                at_start,
                points=points,
                drawn=drawn,
                inset_m=inset_m,
                unit_width_m=unit_width_m,
                faces_node=False,
            )
            if dressed is None:
                report.clipped_no_width += 1
                continue
            row, span = dressed
            report.span_m.append(span)
            report.clipped_dressed += 1
            if edge_id not in report.clipped_edges:
                report.clipped_edges.append(edge_id)
            placements.extend(row)

    report.barriers = len(placements)
    return placements, report


def _document(
    city: Config, region_id: str, placements: list[Placement], report: FenceReport
) -> dict:
    """Written unconditionally, `carve.json`'s precedent: a missing file means
    the stage never ran, not that there was nothing to fence.

    Schema 3 (`Q143`): `clipped_*` and `region_extent_m`. A v2 reader would
    report every clipped barrier as standing on an edge nothing closes.
    """
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
        # Published apart from `fenced_edges` — the module docstring carries why
        # that separation is the contract rather than a layout choice.
        "touchdown_levels": report.touchdown_levels,
        "touchdown_edges": sorted(report.touchdown_edges),
        "touchdowns": report.touchdowns,
        "touchdowns_no_width": report.touchdowns_no_width,
        # The third population, with the rectangle it was measured against so
        # `verify_fence.gd` can re-derive it — `bounds_game` is not that rectangle.
        "clipped_within_m": report.clipped_within_m,
        "region_extent_m": (
            None if report.region_high is None else [round(v, 3) for v in report.region_high]
        ),
        "clipped_edges": sorted(report.clipped_edges),
        "clipped_ends": report.clipped,
        "clipped_no_width": report.clipped_no_width,
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

    # 🔴 **The starved set needs `clearance:` and the touchdown closure does NOT,
    # so this is a branch rather than an early return (`Q103`).** It was written
    # as a return, and that silently skipped a declared `touchdown_levels` on any
    # city without a clearance block — publishing an empty closure, and not even
    # reaching the loud warning below, which is precisely the open-and-ungraded
    # state the key exists to end. The closure is topological: it reads the
    # graph's levels and nodes and no measurement at all.
    fenced: list[int] = []
    # ⚠️ **Read before the `city.fence is None` branch below, so it must not go
    # through `city.fence`.** A city with no `fence:` block closes nothing, which
    # means every level is open and every starved edge is fenced — the state that
    # branch exists to describe, and the safe reading: the bar still refuses the
    # edge, there is simply no barrier dressing it.
    closed_levels = city.fence.touchdown_levels if city.fence is not None else ()
    bar_m = float(city.clearance.car_width_m) if city.clearance is not None else None
    if bar_m is None:
        log.info("  no clearance block, so no starved edge is fenced")
    else:
        clearance = read_document(out_dir / CLEARANCE_NAME, CLEARANCE_SCHEMA, rebuild)
        fenced = fenced_edges(graph, clearance, bar_m, closed_levels)

    if city.fence is None:
        # 🔴 **The bar without the dressing, and it is a real state rather than a
        # half-configured one.** `clearance:` decides which edges the *predicate*
        # refuses and `fence:` decides where a barrier stands, so a city can
        # publish the fenced set and dress none of it — `RoadGraph.fits_car`
        # still works and the player still meets an undressed wall. `Q19` forbids
        # *shipping* that, which is a review question rather than a build one, so
        # this is logged loudly and published rather than refused.
        if fenced:
            log.warning(
                "  %d edges fenced at the car's %.2f m and NO fence block to dress them"
                " — Q19 forbids shipping an undressed refusal",
                len(fenced),
                bar_m,
            )
        return write_document(
            out_dir / FENCE_NAME, _document(city, region_id, [], FenceReport(fenced=fenced))
        )

    region_high = city.region_high(region_id)
    placements, report = place(
        graph,
        drawn,
        fenced,
        inset_m=city.fence.inset_m,
        unit_width_m=city.fence.unit_width_m,
        touchdown_levels=closed_levels,
        region_high=region_high,
        clipped_within_m=city.fence.clipped_within_m,
    )
    if not report.closes(city.fence.unit_width_m):
        # The identity that says every mouth is accounted for. Raised rather
        # than logged: a stage whose own partition does not close is publishing
        # a number nobody can read.
        raise ValueError(
            f"{report.barriers} barrier units against {len(report.span_m)} spans over "
            f"{report.mouths_dressed} dressed mouths, {report.touchdowns_dressed} dressed "
            f"touchdowns and {report.clipped_dressed} dressed clipped ends — the row width "
            "and the published spans disagree"
        )

    log.info(
        "  %d edges fenced at the car's %s, in %d component(s); %d mouths,"
        " %d behind another fence, %d with no way in",
        len(fenced),
        "no bar" if bar_m is None else f"{bar_m:.2f} m",
        report.components,
        report.mouths,
        report.ends_behind_another_fence,
        report.ends_with_no_way_in,
    )
    if report.mouths_no_width:
        log.warning("  %d mouths had no published ribbon to span", report.mouths_no_width)
    if city.fence.touchdown_levels:
        log.info(
            "  touchdowns closed at level(s) %s: %d ends dressed, %d with no width",
            ", ".join(str(level) for level in city.fence.touchdown_levels),
            report.touchdowns_dressed,
            report.touchdowns_no_width,
        )
    else:
        # ⚠️ Loud rather than silent: `Q103` measured the off-grade network
        # reachable and ungraded, so leaving it open is a choice the build log
        # should say out loud rather than a default nobody sees.
        log.warning(
            "  no fence.touchdown_levels — the off-grade network stays open and ungraded (Q103)"
        )
    if city.fence.clipped_within_m is not None:
        log.info(
            "  clipped ends within %.2f m of the rectangle: %d dressed over %d edges, %d with no"
            " width",
            city.fence.clipped_within_m,
            report.clipped_dressed,
            len(report.clipped_edges),
            report.clipped_no_width,
        )
    else:
        # Loud on `touchdown_levels`' terms: an open line is a way out of the
        # world, and a build that leaves it open should say so.
        log.warning("  no fence.clipped_within_m — streets cut by the region stay open (Q143)")
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
