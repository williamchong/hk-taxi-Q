"""What the blocked carriageway costs a driver who has to go round it.

    .venv/bin/python tools/reachability.py --region wan_chai

`P3-9a` ended with three HK drivers stopping because the bridges are blocked,
and `Q19` records the walls they hit. What no record contains is whether those
walls **disconnect** anything: `P3-9a′` says so in its own words — *"no route
analysis here shows the region is disconnected by these edges, and `RoadGraph`
would be the thing to ask"*. This asks it.

⚠️ **`RoadGraph` could not in fact be asked.** `game/scripts/city/road_graph.gd`
is a spatial index and an attribute table — `is_routable`, `is_passable`,
`impassable_edge_ids` — with no adjacency, no traversal and no router;
`turn_restrictions` is only counted. So the traversal is built here, over the
documents the ETL already publishes, and `is_routable` is reimplemented rather
than called.

🔴 **A second implementation of a shipped predicate, deliberately** — the same
arrangement `pipeline/carriageway.py` has with `tools/carriageway_margin.py`.
They are expected to agree and a divergence is a finding, never a bar to retune.

⚠️ **This grades rather than checks and exits 0 whatever it finds.** There is no
bar, deliberately: a region that loses routes is a fact about Wan Chai's
interchange, not a regression to hold a build against.

🔴 **The obvious instrument is wrong, and it was tried first.** Strongly connected
components over the level-0 network are dominated by the *region clip*, not by
the walls: the largest is 331 edges of 737, the second 103, and the rest are
singletons — a street that leaves a 1.5 km² clip has no way back into it.
Refusing every starved edge leaves those sizes **unchanged**, so an SCC headline
would report "no effect" on a question it never asked. The headline here is
pairwise reachability instead.

🔴 **The counted population is held fixed across the two worlds.** Refusing 24
edges and then counting pairs over all 737 makes the count fall by construction —
`Q58`'s `drawn_gauge_m` trap again — named rather than numbered, because the
repo's own running count of it disagrees with itself. Every figure below is
counted over the edges that survive in **both** worlds, which is why the tables
say *among the survivors*.

⚠️ **Two bars, because they are two questions**, as `tools/narrowing.py` has it.
One lane (`lane_width_m`) is whether traffic should be *routed* down an edge,
which is what `Q51` gates on. The car's own width is whether the **player** is
stuck, and the player is who round 0 was run on.

⚠️ **The starved population depends on which instrument names it**, and that is
`Q51`'s reconciled gap arriving here. `clearance.json` measures at `CELL_M` and
`tools/carriageway_occupancy.py` grades the shipped mesh at its own plan
resolution; the two name 24 and 26 edges. This computes the first and takes the
second on `--refuse`, so both can be published side by side and neither wears the
other's name.

⚠️ **The detour ignores the source edge's own length**, because it is the same
length in both worlds and cancels out of every delta. What it measures is the
distance travelled *after leaving* the source edge, so a figure here is a
difference in route length and not a trip length.
"""

from __future__ import annotations

import argparse
import heapq
import logging
import math
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from pipeline.clearance import CLEARANCE_NAME, CLEARANCE_SCHEMA, NOT_MEASURED  # noqa: E402
from pipeline.config import FORWARD, Config, load_config  # noqa: E402
from pipeline.documents import read_document  # noqa: E402
from pipeline.polyline import plan_lengths  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402

log = logging.getLogger(__name__)

# The taxi's body collider, in metres — `game/scenes/vehicle/taxi.tscn`. A
# default rather than a hard-coded bar, so a wider car is a flag rather than an
# edit. Same value and same reason as `tools/narrowing.py`.
CAR_WIDTH_M = 1.8

# A detour past this is called out by name rather than only folded into the
# percentiles. Not a bar — nothing fails on it — but a distance a driver in an
# arcade taxi would experience as being sent the wrong way rather than nudged.
DETOUR_REPORT_M = 200.0

# The level a car is handed. `RoadGraph.is_drivable` is the same test, and `Q13`
# is why the elevated network is not in it.
DRIVABLE_LEVEL = 0

# How many named losses to print. The list is evidence to go and drive, so it
# has to fit on a screen; the count above it is the complete figure.
NAMED_LIMIT = 12


@dataclass(frozen=True)
class Network:
    """The directed traversals a car can be in, and what each leads to.

    A **state** is `(edge, entry node, exit node)` — one per `forward` edge and
    two per `both`, because a two-way street is two different positions to be in
    and only one of them can reach what lies beyond its far end.

    ⚠️ **`roads.py::_components` must not be reused for this.** It is undirected
    union-find, and this region is 93.5% one-way by drivable length, so it would
    overstate connectivity by construction. Its question is the graph's
    integrity; this one is driving.
    """

    states: tuple[tuple[int, int, int], ...]
    # `adjacency[i]` is every state reachable from state `i` in one junction.
    adjacency: tuple[tuple[int, ...], ...]
    # The plan length of each state's own edge, in metres, in state order.
    lengths: tuple[float, ...]
    # Edge id to the states that traverse it.
    by_edge: dict[int, tuple[int, ...]]


def plan_length(polyline: list[list[float]]) -> float:
    """A polyline's length in the ground plane, in metres.

    Plan rather than 3D, matching `RoadGraph.plan_distance`: the graph's `y` is a
    deck height the driver does not travel through, and a ramp's slope would
    otherwise make it fractionally more expensive than the flat street beside it
    for a reason that has nothing to do with routing.

    ⚠️ **`pipeline.polyline` owns the arithmetic, and this only unpacks the
    document.** That module is a numpy leaf whose docstring says in terms that
    the repo's duplicate-deliberately rule does not reach it — a snap grades
    nothing, so a second copy buys no check — and it already carries
    `kerbside._plan_lengths` as an unretired third copy. Restating it here would
    have been the fourth. Every other grader that wants one edge's length calls
    it exactly this way (`carriageway_margin.py`, `kerbside_error.py`).
    """
    return float(plan_lengths(np.asarray(polyline, dtype=np.float64))[-1])


def build(graph: dict, keep: set[int]) -> Network:
    """The traversal network over `keep`, with every other edge refused.

    Refusing an edge removes its states, so nothing routes *through* it either —
    which is the whole point. An edge a car cannot fit down is not a corner it
    can cut.
    """
    states: list[tuple[int, int, int]] = []
    lengths: list[float] = []
    by_edge: dict[int, list[int]] = {}
    for edge in graph["edges"]:
        edge_id = int(edge["id"])
        if edge_id not in keep:
            continue
        length = plan_length(edge["polyline"])
        ends = [(int(edge["from"]), int(edge["to"]))]
        if edge["direction"] != FORWARD:
            ends.append((int(edge["to"]), int(edge["from"])))
        for entry, exit_node in ends:
            by_edge.setdefault(edge_id, []).append(len(states))
            states.append((edge_id, entry, exit_node))
            lengths.append(length)

    # Which states *leave* each node, so a transition is a lookup rather than a
    # scan of the whole region per junction.
    leaving: dict[int, list[int]] = {}
    for index, (_, entry, _) in enumerate(states):
        leaving.setdefault(entry, []).append(index)

    banned = {
        (int(rule["from_edge"]), int(rule["via_node"]), int(rule["to_edge"]))
        for rule in graph.get("turn_restrictions", [])
    }

    adjacency: list[tuple[int, ...]] = []
    for edge_id, _, exit_node in states:
        onward = []
        for other in leaving.get(exit_node, ()):
            next_edge = states[other][0]
            # ⚠️ **A U-turn is not a movement the source publishes.** Allowing
            # one would let a car turn round on a blocked edge's own carriageway
            # and quietly restore a route the wall removed.
            if next_edge == edge_id:
                continue
            if (edge_id, exit_node, next_edge) in banned:
                continue
            onward.append(other)
        adjacency.append(tuple(onward))

    return Network(
        states=tuple(states),
        adjacency=tuple(adjacency),
        lengths=tuple(lengths),
        by_edge={edge: tuple(indices) for edge, indices in by_edge.items()},
    )


def reachable(net: Network) -> dict[int, set[int]]:
    """Every edge each source edge can reach, by any legal route.

    From **any** state of the source, because a driver standing on a two-way
    street may set off either way. The source itself is excluded: whether a car
    can come back round to where it started is a different question and it would
    swamp a count of the pairs this exists to compare.
    """
    onward: dict[int, set[int]] = {}
    for edge_id, starts in net.by_edge.items():
        seen = bytearray(len(net.states))
        queue = deque(starts)
        for start in starts:
            seen[start] = 1
        found: set[int] = set()
        while queue:
            state = queue.popleft()
            for other in net.adjacency[state]:
                if seen[other]:
                    continue
                seen[other] = 1
                found.add(net.states[other][0])
                queue.append(other)
        found.discard(edge_id)
        onward[edge_id] = found
    return onward


def distances(net: Network) -> dict[int, dict[int, float]]:
    """The shortest driving distance from each edge to every edge it reaches.

    Multi-source Dijkstra from the source's own states at cost zero, so the
    source edge's own length is not in the answer — see the module docstring for
    why that is the right frame for a *difference* in route length.
    """
    out: dict[int, dict[int, float]] = {}
    for edge_id, starts in net.by_edge.items():
        best = [math.inf] * len(net.states)
        heap: list[tuple[float, int]] = []
        for start in starts:
            best[start] = 0.0
            heap.append((0.0, start))
        heapq.heapify(heap)
        while heap:
            cost, state = heapq.heappop(heap)
            if cost > best[state]:
                continue
            for other in net.adjacency[state]:
                # Entering a state costs that state's own edge, which is the
                # tarmac actually driven to get from this junction to the next.
                step = cost + net.lengths[other]
                if step < best[other]:
                    best[other] = step
                    heapq.heappush(heap, (step, other))
        per_edge: dict[int, float] = {}
        for index, cost in enumerate(best):
            if cost == math.inf:
                continue
            target = net.states[index][0]
            if target == edge_id:
                continue
            if cost < per_edge.get(target, math.inf):
                per_edge[target] = cost
        out[edge_id] = per_edge
    return out


def pairs(onward: dict[int, set[int]], counted: set[int]) -> int:
    """Ordered edge pairs with a route, over one fixed population.

    🔴 **`counted` is the population, not `onward`'s own keys.** The two worlds
    being compared have different edge sets by construction, and counting each
    over its own would make the refusal look expensive however little it cost.
    """
    return sum(len(onward.get(source, set()) & counted) for source in counted)


def starved(clearance: dict, levels: dict[int, int], bar: float) -> set[int]:
    """Drivable edges keeping less than `bar` clear at some measured station.

    `RoadGraph.is_passable` restated (`road_graph.gd:319`). ⚠️ **A missing
    measurement is not a measurement of zero** — every station of a short edge
    can be swallowed by the junction caps at its two ends — so an edge with
    nothing measured is unjudged and stays in the network.
    """
    blocked = set()
    for entry in clearance["clearance"]:
        edge_id = int(entry["edge"])
        if levels.get(edge_id) != DRIVABLE_LEVEL:
            continue
        widths = [width for width in entry["clear_width_m"] if width != NOT_MEASURED]
        if widths and min(widths) < bar:
            blocked.add(edge_id)
    return blocked


def check_documents(graph: dict, clearance: dict) -> None:
    """Refuse two documents from different runs.

    `narrowing.scaled`'s precondition, restated for this pair: an edge in one and
    not the other is a silent hole in every count below, and defaulting it would
    drop it from the population without a word.
    """
    graphed = {int(edge["id"]) for edge in graph["edges"]}
    measured = {int(entry["edge"]) for entry in clearance["clearance"]}
    missing = measured - graphed
    if missing:
        raise SystemExit(
            f"{CLEARANCE_NAME} measures {len(missing)} edges the graph does not carry "
            f"(first: e{sorted(missing)[0]}); the two documents are from different runs"
        )


def percentiles(values: list[float]) -> tuple[float, float, float, float]:
    """p50 / p90 / p99 / max, as the marking stages publish them.

    ⚠️ **The tail is the finding and the median is not.** `arrows.py` records
    why: a median near zero is also what a wholly broken join looks like.

    The same four points and the same `np.percentile` as `arrows.py:282`, rather
    than a rank convention of this tool's own — two percentile definitions in one
    repo is two ways for the same distribution to be published.
    """
    if not values:
        return (0.0, 0.0, 0.0, 0.0)
    points = np.percentile(np.asarray(values), (50, 90, 99, 100))
    return (float(points[0]), float(points[1]), float(points[2]), float(points[3]))


@dataclass(frozen=True)
class Verdict:
    """One refusal, measured against the world that keeps everything."""

    refused: tuple[int, ...]
    counted: int
    before: int
    after: int
    detours_m: tuple[float, ...]
    lost: tuple[tuple[int, int], ...]

    @property
    def cut(self) -> int:
        return self.before - self.after

    @property
    def share(self) -> float:
        return 100.0 * self.cut / self.before if self.before else 0.0


def moved_m(verdict: Verdict) -> list[float]:
    """The detours that are a detour.

    A pair whose shortest route ran through a refused edge but had an
    equal-length alternative comes back as a floating-point zero, and counting it
    would report the whole network as diverted. One definition, because the
    detour table and the per-edge table both need it and two would drift.
    """
    return [metres for metres in verdict.detours_m if metres > 1e-6]


@dataclass(frozen=True)
class Open:
    """The world with nothing refused — searched once, read many times.

    Every row of every table is a comparison against this same world, and
    `measure` is called once per population **and** once per blocked edge — 28
    times on Wan Chai. Recomputing the open side of each of those was ~40% of the
    tool's runtime, measured. It is a pure cache over `(graph, level0)`, neither
    of which moves inside a run, so it cannot change a published figure.
    """

    net: Network
    reach: dict[int, set[int]]
    cost: dict[int, dict[int, float]]

    @classmethod
    def of(cls, graph: dict, level0: set[int]) -> Open:
        net = build(graph, level0)
        return cls(net=net, reach=reachable(net), cost=distances(net))


def measure(graph: dict, level0: set[int], refuse: set[int], world: Open | None = None) -> Verdict:
    """Reachability and detour cost with `refuse` taken out of the network.

    `world` is the open side, so a caller making many comparisons can search it
    once. Left optional rather than required because a test wants one call and no
    scaffolding, and building it here is the same computation either way.
    """
    counted = level0 - refuse
    world = world or Open.of(graph, level0)

    # Refusing nothing is the control row, and its two worlds are the same world.
    # Searching the second one produces a byte-identical answer at full price.
    if refuse:
        cut_net = build(graph, counted)
        cut_reach = reachable(cut_net)
    else:
        cut_net, cut_reach = world.net, world.reach

    lost = tuple(
        (source, target)
        for source in sorted(counted)
        for target in sorted(
            (world.reach.get(source, set()) & counted) - cut_reach.get(source, set())
        )
    )

    detours: list[float] = []
    if refuse:
        cut_cost = distances(cut_net)
        for source in counted:
            for target, after in cut_cost[source].items():
                if target not in counted:
                    continue
                before = world.cost[source].get(target)
                if before is not None:
                    detours.append(after - before)

    verdict = Verdict(
        refused=tuple(sorted(refuse)),
        counted=len(counted),
        before=pairs(world.reach, counted),
        after=pairs(cut_reach, counted),
        detours_m=tuple(detours),
        lost=lost,
    )
    # The named list and the count are two routes to one fact, and they are
    # computed separately — one by differencing the reachable sets, the other by
    # counting each world. Refusing an edge can only ever remove a route, so they
    # must agree; if they do not, one of the two worlds is not the world the
    # other table describes and every figure in the report is suspect.
    assert len(verdict.lost) == verdict.cut, (
        f"{len(verdict.lost)} pairs named lost against a count of {verdict.cut}"
    )
    return verdict


def _report_populations(
    graph: dict,
    level0: set[int],
    populations: list[tuple[str, set[int]]],
    world: Open,
) -> dict[str, Verdict]:
    log.info("")
    log.info("  routes lost, per population — counted over the survivors of each refusal:")
    log.info(
        "    %-28s %7s %9s %11s %8s %9s",
        "refused",
        "edges",
        "pairs",
        "with a route",
        "lost",
        "share",
    )
    verdicts: dict[str, Verdict] = {}
    for label, refuse in populations:
        verdict = measure(graph, level0, refuse & level0, world)
        verdicts[label] = verdict
        log.info(
            "    %-28s %7d %9d %11d %8d %8.2f%%",
            label,
            len(verdict.refused),
            verdict.counted * (verdict.counted - 1),
            verdict.before,
            verdict.cut,
            verdict.share,
        )
    return verdicts


def _report_detours(verdicts: dict[str, Verdict], report_m: float) -> None:
    log.info("")
    log.info("  detour on the routes that SURVIVE, in metres — the tail, not the median:")
    log.info(
        "    %-28s %9s %8s %8s %8s %8s %10s",
        "refused",
        "pairs",
        "p50",
        "p90",
        "p99",
        "max",
        f"over {report_m:.0f} m",
    )
    for label, verdict in verdicts.items():
        if not verdict.refused:
            continue
        moved = moved_m(verdict)
        p50, p90, p99, worst = percentiles(moved)
        log.info(
            "    %-28s %9d %8.1f %8.1f %8.1f %8.1f %10d",
            label,
            len(moved),
            p50,
            p90,
            p99,
            worst,
            sum(1 for metres in moved if metres > report_m),
        )


def _report_per_edge(
    graph: dict,
    level0: set[int],
    watched: list[int],
    names: dict[int, str],
    world: Open,
) -> None:
    """Each blocked edge refused alone.

    🔴 **This is what tells one bridge carrying the only crossing from four
    parallel ones**, which is the whole question behind closing the structure
    edges to the player.
    """
    log.info("")
    log.info("  each blocked edge refused ALONE — pairs lost among the survivors:")
    log.info("    %-7s %8s %9s %8s  %s", "edge", "lost", "detour p90", "max", "street")
    rows = []
    for edge_id in watched:
        verdict = measure(graph, level0, {edge_id}, world)
        moved = moved_m(verdict)
        _, p90, _, worst = percentiles(moved)
        rows.append((verdict.cut, edge_id, p90, worst))
    for cut, edge_id, p90, worst in sorted(rows, reverse=True):
        log.info(
            "    e%-6d %8d %9.1f %8.1f  %s",
            edge_id,
            cut,
            p90,
            worst,
            names.get(edge_id, "unnamed"),
        )


def _report_standing(
    watched: list[int],
    names: dict[int, str],
    world: Open,
) -> None:
    """Where each blocked edge stands in the network it is part of.

    🔴 **The table above cannot answer the question this one does.** "No route is
    lost" is counted over the *survivors*, so an edge that carries no through
    traffic reads as free to refuse — and that is true of a dead-end stub and of
    a street the player drives onto and cannot leave, which are not the same
    thing at all. `reached by` is how many surviving edges can get a car onto
    this one, which is how often a player arrives at the wall; `reaches` is what
    the edge leads to, which is what closing it would take away.
    """
    onward = world.reach
    arrivals: dict[int, int] = dict.fromkeys(watched, 0)
    for source, targets in onward.items():
        for target in targets:
            if target in arrivals and source not in arrivals:
                arrivals[target] += 1
    log.info("")
    log.info("  where each blocked edge stands, in the OPEN network — survivors only:")
    log.info("    %-7s %10s %9s  %s", "edge", "reached by", "reaches", "street")
    blocked = set(watched)
    for edge_id in sorted(watched, key=lambda e: -arrivals[e]):
        log.info(
            "    e%-6d %10d %9d  %s",
            edge_id,
            arrivals[edge_id],
            len(onward.get(edge_id, set()) - blocked),
            names.get(edge_id, "unnamed"),
        )


def _report_named(verdict: Verdict, names: dict[int, str], label: str) -> None:
    """The pairs that lose every route, named rather than merely counted.

    `narrowing._report_bar`'s rule: the thing a change makes worse is the finding
    the sweep exists to be able to see, so it is printed with a street on it.
    """
    log.info("")
    if not verdict.lost:
        log.info("  no ordered pair loses every route when %s is refused", label)
        return
    log.info(
        "  pairs losing every route when %s is refused — first %d of %d:",
        label,
        min(NAMED_LIMIT, len(verdict.lost)),
        len(verdict.lost),
    )
    for source, target in verdict.lost[:NAMED_LIMIT]:
        log.info(
            "    e%-6d %-28s -> e%-6d %s",
            source,
            names.get(source, "unnamed"),
            target,
            names.get(target, "unnamed"),
        )


def _ids(text: str) -> set[int]:
    return {int(part) for part in text.replace(",", " ").split()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--car-width-m",
        type=float,
        default=CAR_WIDTH_M,
        help="the player's own width, from taxi.tscn (default: %(default)s)",
    )
    parser.add_argument(
        "--refuse",
        default="",
        help=(
            "extra edge ids to refuse as their own population, e.g. "
            "carriageway_occupancy.py's 26 — comma or space separated"
        ),
    )
    parser.add_argument(
        "--refuse-label",
        default="--refuse",
        help="what to call the --refuse population in the tables",
    )
    parser.add_argument(
        "--detour-report-m",
        type=float,
        default=DETOUR_REPORT_M,
        help="call out detours past this many metres (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city: Config = load_config()
    region = city.region(args.region)
    out_dir = city.out_dir(args.region)
    rebuild = f"python -m pipeline --region {args.region}"
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, args.region)
    clearance = read_document(out_dir / CLEARANCE_NAME, CLEARANCE_SCHEMA, rebuild)
    check_documents(graph, clearance)

    levels = {int(edge["id"]): int(edge["elevation_level"]) for edge in graph["edges"]}
    level0 = {edge for edge, level in levels.items() if level == DRIVABLE_LEVEL}
    names = road_names(graph)
    lane_m = float(city.roads.lane_width_m)

    lane_blocked = starved(clearance, levels, lane_m)
    car_blocked = starved(clearance, levels, args.car_width_m)
    on_structure = {
        int(edge["id"]) for edge in graph["edges"] if any(edge.get("on_structure") or ())
    }
    extra = _ids(args.refuse) if args.refuse.strip() else set()

    log.info("%s / %s", city.name, region.name)
    log.info(
        "  %d level-0 edges, %d nodes, %d turn restrictions; bars %.2f m (one lane) and %.2f m"
        " (the car)",
        len(level0),
        len(graph["nodes"]),
        len(graph.get("turn_restrictions", [])),
        lane_m,
        args.car_width_m,
    )
    log.info(
        "  starved at one lane %d, at the car %d; %d level-0 edges touch structure, %d of them"
        " starved",
        len(lane_blocked),
        len(car_blocked),
        len(level0 & on_structure),
        len(lane_blocked & on_structure),
    )

    # Named rather than reached by position. The named-losses table below wants
    # this one row, and `populations[1]` would have gone on resolving — to the
    # wrong population — the moment anyone inserted a row above it.
    lane_label = f"starved at one lane ({len(lane_blocked)})"
    populations: list[tuple[str, set[int]]] = [
        # ⚠️ **Reachable at zero, and that is why it is first.** A refusal of
        # nothing must lose nothing; a non-zero row here would mean the two
        # worlds differ for a reason that is not the refusal (`Q72`).
        ("nothing (control)", set()),
        (lane_label, lane_blocked),
        (f"starved at the car ({len(car_blocked)})", car_blocked),
        (
            f"starved AND on structure ({len(lane_blocked & on_structure)})",
            lane_blocked & on_structure,
        ),
    ]
    if extra:
        populations.append((f"{args.refuse_label} ({len(extra & level0)})", extra))

    world = Open.of(graph, level0)
    verdicts = _report_populations(graph, level0, populations, world)
    _report_detours(verdicts, args.detour_report_m)
    watched = sorted(lane_blocked | (extra & level0))
    _report_per_edge(graph, level0, watched, names, world)
    _report_standing(watched, names, world)
    _report_named(verdicts[lane_label], names, lane_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
