"""Whether `Q19`'s walls are a centreline error or a wall in the published road.

    .venv/bin/python tools/centreline_error.py --city hong_kong --region wan_chai

`Q19` leaves three candidates and a price on one of them. `tools/reachability.py`
measured **candidate 2** — fencing the blocked edges costs 1 ordered pair of
187,946 and no pairs at all at the player's own 1.80 m bar. **Candidate 1**
(correct the graph) and **candidate 3** (author the interchange, as `P3-6`
authored HKCEC) have never had a number, so the user's call between fencing and
fixing is being asked with one side blank.

This measures both.

**Part A — the correction that is SOURCED.** Per level-0 station, the *signed*
lateral offset of the published centreline from the middle of the carriageway
TD, iB1000 and HyD actually drew. `carriageway.measure` already casts both rays
and keeps only their sum and their minimum; the difference is what a centreline
correction is made of, and it is thrown away there because nothing needed it.

**Part B — whether moving there clears anything.** The same clearance
measurement, on a graph whose polylines have been shifted by that offset, swept
over a signed ladder.

**Part C — what candidate 3 would cost.** How many centreline metres of the
*surveyed* carriageway have `INFRASTRUCTURE` standing in them. If the sourced
correction does not reach, that is the geometry a fix has to author away, and it
is the first number that candidate has ever had.

⚠️ **This grades rather than checks and exits 0 whatever it finds.** There is no
bar, deliberately. `clearance_reconcile.py` is a ratchet because it holds two
published figures against each other; there is no prior figure here to hold.

⚠️ **It is NOT a fifth grader and must not be quoted as an independent check of
`Q19`.** It imports `pipeline.carriageway` and `pipeline.clearance` whole, which
puts it on `narrowing.py`'s side of the independence line rather than
`carriageway_occupancy.py`'s — and for `narrowing.py`'s reason, restated: the
question is not whether the measurement is right but what the *same* measurement
says at a moved centreline, and answering that with a second implementation
would confound the two.

🔴 **THE TWO NORMALS ARE OPPOSITE, AND THIS IS THE FILE WHERE THAT STARTS TO
MATTER.** `carriageway._stations` emits `[-unit[1], unit[0]]` — right of travel.
`surface.mitres` emits `[direction[1], -direction[0]]` — left, and says so in a
comment that calls the convention load-bearing, because `TEXCOORD_0` is a lane
coordinate measured from the nearside kerb and Hong Kong drives on the left.
`tools/overhang.py::left_of` agrees with `mitres`, and so do the offsets
`carriageway_occupancy.py` publishes in its centreline verdict.

`carriageway.py` has never had to care, because it keeps `ahead + behind` and
`min(ahead, behind)` and **both are sign-free**. The convention starts deciding
an answer at the exact moment this tool keeps the difference. So there is one
named negation, `_LEFT`, and the frame is closed three ways because no one of
them is enough:

1. `_LEFT` named at the point of use, with this paragraph behind it.
2. `test_the_station_normal_is_the_negation_of_mitres`, so that anyone later
   "restoring consistency" in `pipeline/carriageway.py` fails loudly rather than
   silently reversing every shift measured here.
3. A **signed** ladder, and a re-measurement of Part A on the shifted graph: a
   flipped sign doubles the residual offset where a right one cancels it. That
   closes the question by measurement rather than by comment.

A dropped negation publishes "the sourced correction makes it worse" — plausible,
publishable and false. It is the largest risk in this file.

⚠️ **`off_centre_m` here is not `off_centre` in `carriageway_width.json`.** This
is signed metres; that is an unsigned 0-1 ratio, and they are one letter apart.
The conversion is `|off_centre_m| == off_centre * span_m / 2`.

✅ **Nothing here reads `carriageway_width.json`**, which is gitignored generated
city data — so hard rules 2 and 7 are untouched and a clone that has never run
`carriageway_margin.py --json` reproduces every finding in this file. What it
reads instead is `roadgraph.json`, and the agreement is exact: this licenses the
same **292** edges the pipeline marks measured, same set both ways, with spans
agreeing to p50 0.0003 m.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from narrowing import check_baseline, classes, moved, sweep, sweep_report  # noqa: E402
from pipeline import gltf  # noqa: E402
from pipeline.carriageway import (  # noqa: E402
    JUNCTION_M,
    MAX_RAY_M,
    MIN_STATIONS,
    STATION_M,
    _license,
    _read_publisher,
    _Segments,
    _stations,
)
from pipeline.clearance import (  # noqa: E402
    ALONG_M,
    NOT_MEASURED,
    ClearanceReport,
    landmark_meshes,
    open_region,
    tile_meshes,
)
from pipeline.config import CityConfig, WidthBounds, load_city  # noqa: E402
from pipeline.polyline import plan_lengths  # noqa: E402
from pipeline.surface import mitres  # noqa: E402

log = logging.getLogger(__name__)

# 🔴 `_stations` emits the normal RIGHT of travel; `surface.mitres`,
# `overhang.left_of` and `carriageway_occupancy`'s centreline offsets are all
# LEFT. One negation, named, so that every number this file publishes and every
# number `Q19` already records are in one frame. See the module docstring for
# why this is the largest risk here, and the test file for the pin that holds it.
_LEFT = -1.0

# The player's own width, from `taxi.tscn`. Same value and same reason as
# `narrowing.py` and `reachability.py`; the wheels are raycasts with no collider
# of their own since `Q50`, so 1.8 m is the whole car.
CAR_WIDTH_M = 1.8


def percentiles(values: list[float]) -> tuple[float, float, float, float]:
    """p50, p90, p99 and max, of a MAGNITUDE.

    The same four points and the same `np.percentile` as `arrows.py:282` and
    `reachability.py:316`. Restated by hand rather than imported, which is this
    repo's convention: two percentile definitions in one repo would be two ways
    to publish one distribution, and the answer to that is one convention, not
    one shared function.
    """
    if not values:
        return (0.0, 0.0, 0.0, 0.0)
    points = np.percentile(np.asarray(values, dtype=np.float64), (50, 90, 99, 100))
    return (float(points[0]), float(points[1]), float(points[2]), float(points[3]))


def signed_percentiles(values: list[float]) -> tuple[float, float, float, float, float]:
    """p1, p10, p50, p90 and p99 of a SIGNED distribution.

    🔴 **A second convention, deliberately, and beside the first rather than
    instead of it.** The house four points are a magnitude convention and cannot
    see a two-sided population: a set of offsets half of them +2 m and half -2 m
    has a median near zero and a maximum of 2, which reads as a centred
    centreline with one outlier. That is `Q78`'s failure at population scale —
    an absolute value cannot report the direction of the move it measures — so
    both readings are published and neither replaces the other.
    """
    if not values:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    points = np.percentile(np.asarray(values, dtype=np.float64), (1, 10, 50, 90, 99))
    return tuple(float(value) for value in points)  # type: ignore[return-value]


def sides(values: list[float]) -> tuple[int, int, int]:
    """How many offsets fall left, right, and exactly on the centreline.

    The counts are what say a population has two sides. A median cannot: see
    `signed_percentiles`. Zero is reported as its own column rather than folded
    into either side, on `Q19`'s own precedent — its 2026-08-21 table reports a
    tie as a tie, because breaking one by index leans every symmetric
    cross-section the same way and makes the row read less mixed than it is.
    """
    left = sum(1 for value in values if value > 0.0)
    right = sum(1 for value in values if value < 0.0)
    return (left, right, len(values) - left - right)


@dataclass(frozen=True)
class Offset:
    """One level-0 edge's signed lateral offset from the surveyed middle.

    🔴 **The population is UNFILTERED and the bounds are applied where the table
    is printed.** `CarriagewayReport` was built that way after `Q58`'s
    `drawn_gauge_m` trap had shipped in four stages, and the rule holds here: a
    row exists for every edge walked, with `n == 0` and a NaN offset where
    nothing answered, so `n` can exceed the edges kept and a reader can see by
    how much.
    """

    edge: int
    walked: int
    """Stations walked, junction stations included."""
    n: int
    """Stations a single publisher spanned. Zero is a legal value."""
    junction: int
    """Stations dropped for sitting in a junction mouth, where there is no far
    kerb to find and the road reads wide."""
    publishers: str
    direction: str
    off_centre_m: float = float("nan")
    """SIGNED, positive LEFT of travel, the median over signed stations.

    🔴 **The median of the signed stations, never `(median far - median near)/2`.**
    On an edge whose near side swaps the two differ, and the second discards
    exactly the direction this file exists to publish. `sign_mixed` is what makes
    a swap visible instead of averaged away.
    """
    spread_m: float = float("nan")
    """p90 of |per-station offset - median|. The run-versus-point column: a
    centreline that is off by a constant is a registration, one whose offset
    wanders is a different animal and must not be reported as the first."""
    sign_mixed: int = 0
    """Stations whose offset falls on the other side from the median."""
    span_m: float = float("nan")
    own_m: float = float("nan")
    basis: str = ""
    """`_license`'s own answer: `two_way_span`, `one_way_uncrossed`, or empty
    where the publishers licensed nothing."""

    @property
    def beyond_m(self) -> float:
        return self.span_m - self.own_m

    @property
    def shift_m(self) -> float:
        """The move that would put the centreline in the surveyed middle."""
        return -self.off_centre_m

    @property
    def licensed(self) -> bool:
        return bool(self.basis)


def _station_offsets(
    plan: np.ndarray,
    publishers: list[tuple[str, _Segments]],
    nodes: np.ndarray,
    *,
    spacing_m: float,
    max_ray_m: float,
    junction_m: float,
) -> tuple[list[float], list[float], list[float], set[str], int, int]:
    """Signed offsets, spans and near rays per station, plus what was refused.

    ⚠️ **The first publisher that answers BOTH sides wins and the loop breaks**,
    which is `carriageway.measure`'s own rule rather than a new one. It matters
    more here than it does there: the offset and the width then come from one
    registration, where a span assembled from two sources would be two different
    surveys of the same street differenced against each other.
    """
    offsets: list[float] = []
    spans: list[float] = []
    nears: list[float] = []
    answered: set[str] = set()
    walked = 0
    junction = 0
    for point, normal in _stations(plan, spacing_m):
        walked += 1
        if len(nodes) and float(np.hypot(*(nodes - point).T).min()) < junction_m:
            junction += 1
            continue
        for name, segments in publishers:
            ahead = segments.first_hit(point, normal, max_ray_m)
            behind = segments.first_hit(point, -normal, max_ray_m)
            if ahead is None or behind is None:
                continue
            # The middle of the span sits at `(ahead - behind) / 2` from the
            # centreline along `+normal`; the centreline therefore sits at the
            # negation of that from the middle. `_LEFT` carries it into the
            # frame `mitres` and `Q19`'s own table are written in.
            offsets.append(_LEFT * (behind - ahead) / 2.0)
            spans.append(ahead + behind)
            nears.append(min(ahead, behind))
            answered.add(name)
            break
    return offsets, spans, nears, answered, walked, junction


def read_publishers(city: CityConfig, region_id: str) -> list[tuple[str, _Segments]]:
    """Every carriageway-edge publisher, read once.

    ⚠️ **Hoisted out of `offsets` because `main` measures twice** — once on the
    published graph and once on the shifted one, to settle the sign — and the
    publishers are identical geometry both times. Re-reading them costs 2.9 s of
    a 33 s run, almost all of it HyD's 552 pavement polygons, and moves no
    published number.
    """
    survey = city.carriageway_survey
    assert survey is not None  # guarded in `main` before anything is walked
    transform = city.game_transform(region_id)
    return [(spec.name, _read_publisher(city, spec, region_id, transform)) for spec in survey.edges]


def offsets(
    city: CityConfig,
    region_id: str,
    graph: dict,
    bounds: WidthBounds,
    *,
    spacing_m: float = STATION_M,
    max_ray_m: float = MAX_RAY_M,
    junction_m: float = JUNCTION_M,
    min_stations: int = MIN_STATIONS,
    publishers: list[tuple[str, _Segments]] | None = None,
) -> dict[int, Offset]:
    """Every level-0 edge's signed offset from the middle the publishers drew."""
    publishers = read_publishers(city, region_id) if publishers is None else publishers
    nodes = np.array([node["pos"] for node in graph["nodes"]], dtype=np.float64)
    nodes = nodes[:, [0, 2]] if len(nodes) else np.empty((0, 2))

    rows: dict[int, Offset] = {}
    for published in graph["edges"]:
        if int(published["elevation_level"]) != 0 or len(published["polyline"]) < 2:
            continue
        plan = np.asarray(published["polyline"], dtype=np.float64)[:, [0, 2]]
        found, spans, nears, answered, walked, junction = _station_offsets(
            plan,
            publishers,
            nodes,
            spacing_m=spacing_m,
            max_ray_m=max_ray_m,
            junction_m=junction_m,
        )
        edge_id = int(published["id"])
        walked_row = Offset(
            edge=edge_id,
            walked=walked,
            n=len(found),
            junction=junction,
            publishers="+".join(sorted(answered)),
            direction=str(published["direction"]),
        )
        if len(found) < min_stations:
            # Every field but the six above stays at its NaN default: an edge no
            # publisher spanned has no measurement, and a row still exists for it
            # so that `n` can exceed what is kept (`Q58`).
            rows[edge_id] = walked_row
            continue
        median = float(np.median(found))
        span = float(np.median(spans))
        own = 2.0 * float(np.median(nears))
        measured = replace(
            walked_row,
            off_centre_m=median,
            spread_m=float(np.percentile(np.abs(np.asarray(found) - median), 90)),
            sign_mixed=sum(1 for value in found if value * median < 0.0),
            span_m=span,
            own_m=own,
        )
        # `_license` reads `edge.direction` and nothing else, so the row is its
        # own argument — no stand-in object, and `direction` stops being a field
        # nothing reads.
        _, basis = _license(measured, span, own, bounds)
        rows[edge_id] = replace(measured, basis=basis)
    return rows


# --------------------------------------------------------------------------
# Part B — does moving there clear anything?
# --------------------------------------------------------------------------
# Signed multiples of each edge's OWN sourced correction. 🔴 **The negative arm
# is the mutation check, not padding** (`Q72`): a tool reporting the same answer
# at +1 and -1 is not applying the sign it measured, and the sign is this file's
# largest risk. Past 1.0 the move is no longer sourced and the table says so.
FRACTIONS: tuple[float, ...] = (-2.0, -1.0, 0.0, 1.0, 2.0, 3.0)

# How far the residual offset may sit from zero after a +1.0x shift before the
# sign or the joint is wrong. A warning rather than a refusal: the tool grades.
_RESIDUAL_M = 0.10


@dataclass(frozen=True)
class World:
    """The graph at one signed multiple of each licensed edge's own shift."""

    scale: float
    taper_m: float
    graph: dict
    delivered_m: dict[int, float]
    """The shift actually applied at each edge's own tightest station, which the
    taper can make much smaller than nominal."""
    node_gap_m: float
    """The worst plan distance between two edges' endpoints at a shared node.

    🔴 **Measured per NODE, not per edge, and the difference is a factor of two
    in both directions.** The obvious reading — the largest endpoint shift over
    all edges — is neither an upper nor a lower bound on the gap it claims to
    report: two edges meeting head-to-tail and shifted the same way in world
    space open *nothing*, while two meeting head-to-head have opposed travel
    directions, so `mitres`' left-of-travel points to opposite world sides and
    the joint opens *twice* the shift. `--no-taper` exists to read an upper
    bound, and this is the number that prices it."""
    refused: tuple[int, ...]
    """Edges whose offset polyline runs backwards on some segment."""

    @property
    def label(self) -> str:
        return f"{self.scale:+.2f}x sourced" if self.scale else "0.00 (control)"


def ramp(along_m: np.ndarray, taper_m: float) -> np.ndarray:
    """Zero at each end of the run, one beyond `taper_m` from either.

    🔴 **This is what keeps the graph connected, and there is no slack to do
    without it.** Measured over all 797 edges, the plan deviation from a
    polyline endpoint to its node is *exactly* 0.000000 m, so an untapered shift
    of `d` opens a gap of exactly `d` against every neighbour, and every edge in
    `Q19`'s population meets nodes of degree two or more.

    ⚠️ **A centreline is a run, not a point.** `railings.py` shifts a run and
    `signs.py` shifts a point, and `CLAUDE.md` says not to align them; the same
    distinction arrives here one layer up, because a per-station push with no
    ramp would zigzag a straight street.
    """
    if taper_m <= 0.0:
        return np.ones(len(along_m))
    total = float(along_m[-1])
    from_end = np.minimum(along_m, total - along_m)
    return np.clip(from_end / taper_m, 0.0, 1.0)


def runs_backwards(points: np.ndarray, moved: np.ndarray) -> bool:
    """Whether the offset polyline reverses on any segment.

    `surface.boundary`'s own test, used here as a **refusal**. `boundary` repairs
    this case by holding the inner rail still, which is right for a rail and
    wrong for a centreline: it would change the edge's length and move every
    station on it. Refused and counted instead.
    """
    before = np.diff(points[:, [0, 2]], axis=0)
    after = np.diff(moved[:, [0, 2]], axis=0)
    return bool((np.einsum("ij,ij->i", before, after) <= 0.0).any())


def shift_graph(graph: dict, rows: dict[int, Offset], *, scale: float, taper_m: float) -> World:
    """The graph with every licensed centreline moved toward its surveyed middle.

    ⚠️ **Built with `surface.mitres`, never with a local normal.** The expression
    below is `surface.boundary`'s own — `plan + offsets * across` — with a
    per-vertex signed shift where the half-width goes. So a shifted centreline
    and the ribbon `surface.py` would draw on it cannot disagree about which way
    they moved, which is the one thing `_LEFT` could still get wrong on its own.

    ⚠️ **`y` is untouched**, so `walk` reads the published deck height and
    `narrowing.py`'s no-rebuild argument mostly transfers. **Mostly**: narrowing
    may hold height fixed because buildings do not move when a ribbon narrows,
    while a ribbon moved *sideways* stands over different ground at its old
    height. On this population that is bounded — these ramps run at 1.0-5.6%
    grade and the `INFRASTRUCTURE` beside them tops out metres above the
    0.30-2.00 m bumper band — and in general it is not.
    """
    edges = []
    delivered: dict[int, float] = {}
    refused: list[int] = []
    landing: dict[int, list[np.ndarray]] = {}
    for published in graph["edges"]:
        edge_id = int(published["id"])
        row = rows.get(edge_id)
        kept = published
        if row is not None and row.licensed and scale != 0.0:
            points = np.asarray(published["polyline"], dtype=np.float64)
            profile = row.shift_m * scale * ramp(plan_lengths(points), taper_m)
            moved = points.copy()
            moved[:, [0, 2]] = points[:, [0, 2]] + mitres(points) * profile[:, None]
            if runs_backwards(points, moved):
                refused.append(edge_id)
            else:
                delivered[edge_id] = float(np.abs(profile).max())
                kept = {**published, "polyline": moved.tolist()}
        edges.append(kept)
        # Every edge lands at its two nodes, moved or not — an unmoved neighbour
        # is exactly what a moved edge tears away from.
        ends = np.asarray(kept["polyline"], dtype=np.float64)[:, [0, 2]]
        landing.setdefault(int(published["from"]), []).append(ends[0])
        landing.setdefault(int(published["to"]), []).append(ends[-1])
    return World(
        scale=scale,
        taper_m=taper_m,
        graph={**graph, "edges": edges},
        delivered_m=delivered,
        node_gap_m=_worst_node_gap(landing),
        refused=tuple(sorted(refused)),
    )


def _worst_node_gap(landing: dict[int, list[np.ndarray]]) -> float:
    """The widest a shared node has been pulled apart, over every node."""
    worst = 0.0
    for points in landing.values():
        if len(points) < 2:
            continue
        stack = np.asarray(points)
        spread = np.hypot(*(stack[:, None, :] - stack[None, :, :]).T)
        worst = max(worst, float(spread.max()))
    return worst


def _cell(width_m: float) -> str:
    """One clear-width cell, or a dash where the ribbon never reached the station.

    `NOT_MEASURED` is -1.0, so printing it raw would read as a road narrower than
    nothing rather than as one that was not asked about.
    """
    return f"{'--':>9}" if width_m == NOT_MEASURED else f"{width_m:>9.2f}"


def _report_sweep(
    ladder: tuple[float, ...],
    results: dict[float, dict[int, float]],
    watched: list[int],
    names: dict[int, str],
    rows: dict[int, Offset],
) -> None:
    log.info("")
    log.info("  clear width per watched edge, at signed multiples of its own sourced shift:")
    header = "".join(f"{rung:>+8.2f}x" for rung in ladder)
    log.info("    %-6s %9s %s  %s", "edge", "shift m", header, "road")
    for edge in watched:
        row = rows.get(edge)
        shift = row.shift_m if row and row.licensed else float("nan")
        cells = "".join(_cell(results[rung].get(edge, NOT_MEASURED)) for rung in ladder)
        log.info("    e%-5d %+9.2f %s  %s", edge, shift, cells, names.get(edge, "unnamed"))
    log.info(
        "    columns past +1.00x are NOT sourced: no publisher puts the carriageway there, and a "
        "move to them would be invented geometry (`Q54`)"
    )


def _report_bar(
    bar_m: float,
    label: str,
    ladder: tuple[float, ...],
    results: dict[float, dict[int, float]],
    names: dict[int, str],
) -> None:
    """Edges under the bar at each rung, and both directions of movement.

    ⚠️ **Moving cuts both ways, exactly as narrowing does.** A lateral shift can
    clear one edge and starve another, so the losses are named rather than
    netted off against the wins.
    """
    log.info("")
    log.info("  edges under %.2f m (%s), per rung:", bar_m, label)
    log.info("    %10s %8s %9s %7s  %s", "shift", "below", "cleared", "lost", "worse")
    for rung in ladder:
        below = {edge for edge, width in results[rung].items() if width < bar_m}
        # ⚠️ **`narrowing.moved`, not a set difference.** It intersects the two
        # rungs' edge sets first, so an edge measured at the control and absent
        # at this rung is neither cleared nor lost. A plain difference reports it
        # as **cleared**, which is a win invented out of a missing measurement.
        cleared, lost = moved(results[0.0], results[rung], bar_m)
        log.info(
            "    %+10.2fx %8d %9d %7d  %s",
            rung,
            len(below),
            len(cleared),
            len(lost),
            ", ".join(f"e{edge}" for edge in sorted(lost)[:8]) or "-",
        )


def _report_endpoints(
    world: World, rows: dict[int, Offset], names: dict[int, str], watched: list[int]
) -> None:
    log.info("")
    log.info(
        "  the endpoint cost, at %s (taper %.1f m): worst node gap %.4f m, %d edges refused for "
        "running backwards",
        world.label,
        world.taper_m,
        world.node_gap_m,
        len(world.refused),
    )
    if world.taper_m > 0.0:
        log.info(
            "    a tapered shift opens nothing at a shared node by construction; what it costs "
            "instead is delivered-versus-nominal, below"
        )
    log.info("    %-6s %10s %11s %7s  %s", "edge", "nominal m", "delivered m", "ramp", "road")
    for edge in watched:
        if edge not in world.delivered_m:
            continue
        row = rows[edge]
        nominal = abs(row.shift_m * world.scale)
        delivered = world.delivered_m[edge]
        log.info(
            "    e%-5d %10.2f %11.2f %7.2f  %s",
            edge,
            nominal,
            delivered,
            delivered / nominal if nominal > 0.0 else 1.0,
            names.get(edge, "unnamed"),
        )


def _report_offsets(
    rows: dict[int, Offset], names: dict[int, str], watched: list[int], bounds: WidthBounds
) -> None:
    log.info("")
    log.info("  the sourced centreline correction, per watched edge:")
    log.info(
        "    %-6s %4s %4s %8s %8s %8s %-18s %10s %8s %6s %10s  %s",
        "edge",
        "n",
        "junc",
        "span m",
        "own m",
        "beyond m",
        "basis",
        "off-cent m",
        "spread m",
        "mixed",
        "shift m",
        "road",
    )
    for edge in watched:
        row = rows.get(edge)
        if row is None:
            log.info("    e%-5d  not a level-0 edge in this graph", edge)
            continue
        log.info(
            "    e%-5d %4d %4d %8.2f %8.2f %8.2f %-18s %+10.2f %8.2f %6d %+10.2f  %s",
            row.edge,
            row.n,
            row.junction,
            row.span_m,
            row.own_m,
            row.beyond_m,
            row.basis or "refused",
            row.off_centre_m,
            row.spread_m,
            row.sign_mixed,
            row.shift_m,
            names.get(edge, "unnamed"),
        )
    log.info(
        "    positive is LEFT of travel (`surface.mitres`' frame); `shift m` is the move that "
        "centres it"
    )
    log.info(
        "    bounds: hard_min %.2f m, max %.2f m, min_stations %d",
        bounds.hard_min_m,
        bounds.max_m,
        MIN_STATIONS,
    )


def _report_distribution(rows: dict[int, Offset], populations: dict[str, set[int]]) -> None:
    """Per population, never pooled — `Q57`'s generalisation is the failure here."""
    log.info("")
    log.info("  how far off the surveyed middle the published centreline sits:")
    log.info(
        "    %-22s %6s %8s %8s %8s %8s %8s | %8s %8s %8s %8s | %5s %5s %5s",
        "population",
        "edges",
        "stations",
        "|off| p50",
        "p90",
        "p99",
        "max",
        "p1",
        "p10",
        "p50",
        "p99",
        "left",
        "right",
        "zero",
    )
    for label, members in populations.items():
        group = [rows[edge] for edge in sorted(members) if edge in rows and rows[edge].licensed]
        values = [row.off_centre_m for row in group]
        p50, p90, p99, worst = percentiles([abs(value) for value in values])
        s1, s10, s50, _, s99 = signed_percentiles(values)
        left, right, zero = sides(values)
        log.info(
            "    %-22s %6d %8d %8.2f %8.2f %8.2f %8.2f | %+8.2f %+8.2f %+8.2f %+8.2f | %5d %5d %5d",
            label,
            len(group),
            sum(row.n for row in group),
            p50,
            p90,
            p99,
            worst,
            s1,
            s10,
            s50,
            s99,
            left,
            right,
            zero,
        )
    licensed = [row for row in rows.values() if row.licensed]
    log.info(
        "    %d level-0 edges walked, %d licensed a width, so %d rows carry a measurement the "
        "bounds refused",
        len(rows),
        len(licensed),
        len(rows) - len(licensed),
    )


# --------------------------------------------------------------------------
# Part C — what candidate 3 would have to author away
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Priced:
    """How much structure stands inside one edge's SURVEYED carriageway.

    ⚠️ **This prices geometry, not identity.** `Q19` was corrected the same day
    for exactly that over-reading: nothing here says *which* structure stands in
    the road, or whether an author could remove it. The column is `to author
    away`, never `cost`.
    """

    edge: int
    carriageway_m: float
    stations: int
    stations_under: int
    length_m: float
    """Centreline metres the measured stations stand for."""
    along_m: float
    """Centreline metres standing under the bar.

    🔴 **Not `stations_under * ALONG_M`, and the difference is not small.**
    `ClearanceReport.corridor_m` is indexed per *polyline vertex*, never per
    cross-section: `walk` samples at `ALONG_M` and folds each sample into the
    nearest vertex, so one station stands for however much of the run is nearer
    to it than to its neighbours. `e55` is 239 m of centreline over 36 vertices.
    Multiplying stations by the sample pitch published 1.50 m where the edge
    carries 3.5 m, and it read like a length.
    """

    @property
    def share(self) -> float:
        return self.along_m / self.length_m if self.length_m else 0.0


# `roads.py` writes `width_source` as bare literals and exports no constant, so
# these are restated rather than imported. 🔴 **Matched POSITIVELY on purpose.**
# The obvious test is `!= "authored"`, and that vocabulary is open at the other
# end: a fourth source meaning "not measured" would slip through it silently and
# price every such edge against a width nobody measured, which is the exact
# failure this function's own refusal exists to prevent.
_MEASURED_SOURCES = frozenset({"one_way_uncrossed", "two_way_span"})


def surveyed_table(
    drawn: dict[int, dict], rows: dict[int, Offset], graph: dict
) -> tuple[dict[int, dict], list[int]]:
    """`roadsurface.json`'s carriageway table restated at each SURVEYED width.

    `narrowing.scaled`'s move: the entry is copied and only `half_width_m` is
    replaced, so the trims and every other field ride through untouched.

    🔴 **An edge the publishers licensed nothing for is REFUSED, never defaulted
    to its authored width.** Pricing a fix against an invented width is `Q54`
    inverted — and `narrowing.scaled` raises on the same class of hole rather
    than filling it, because a silently defaulted edge is a hole in a published
    sweep with no word said.
    """
    published = {int(edge["id"]): edge for edge in graph["edges"]}
    table: dict[int, dict] = {}
    refused: list[int] = []
    for edge_id, entry in drawn.items():
        row = rows.get(edge_id)
        source = str(published.get(edge_id, {}).get("width_source", ""))
        if row is None or not row.licensed or source not in _MEASURED_SOURCES:
            # ⚠️ **Kept in the table at its DRAWN width, and refused from the
            # pricing instead.** `walk` requires a half-width row for every edge
            # it walks and raises naming both documents if one is missing, so
            # dropping the entry here would take the whole region out with a
            # message about a mismatched build. What must not happen is the
            # opposite one — an edge *priced* against a width nothing measured —
            # and `refused` is what stops that, at the point the number is read.
            table[edge_id] = entry
            refused.append(edge_id)
            continue
        half = row.span_m / 2.0
        table[edge_id] = {
            **entry,
            # Narrow only: the surveyed carriageway is never wider than the
            # drawn one here, and a `min` keeps a floor-widened station from
            # being *widened* by this substitution on the few where it would be.
            "half_width_m": [min(value, half) for value in entry["half_width_m"]],
        }
    return table, sorted(refused)


def station_weights(points: np.ndarray) -> np.ndarray:
    """Centreline metres each polyline vertex stands for.

    Half the segment either side of it, so the weights sum to the edge's own
    plan length. This is what turns a per-vertex corridor into a length; see
    `Priced.along_m` for the reading it replaces.
    """
    segments = np.diff(plan_lengths(points))
    weights = np.zeros(len(points))
    weights[:-1] += segments / 2.0
    weights[1:] += segments / 2.0
    return weights


def priced(
    report: ClearanceReport,
    rows: dict[int, Offset],
    graph: dict,
    refused: set[int],
    bar_m: float,
) -> dict[int, Priced]:
    """Per edge, how much of its surveyed carriageway keeps less than `bar_m`."""
    polylines = {
        int(edge["id"]): np.asarray(edge["polyline"], dtype=np.float64) for edge in graph["edges"]
    }
    out: dict[int, Priced] = {}
    for edge_id, stations in report.corridor_m.items():
        row = rows.get(edge_id)
        # Only the edges a publisher licensed a width for. The rest were walked
        # at their drawn width so that `walk` had a row, and pricing them off
        # that would be pricing a fix against an invented carriageway.
        if row is None or edge_id in refused or not row.licensed:
            continue
        widths = np.asarray(stations, dtype=np.float64)
        weights = station_weights(polylines[edge_id])
        seen = widths != NOT_MEASURED
        if not seen.any():
            continue
        under = seen & (widths < bar_m)
        out[edge_id] = Priced(
            edge=edge_id,
            carriageway_m=row.span_m,
            stations=int(seen.sum()),
            stations_under=int(under.sum()),
            length_m=float(weights[seen].sum()),
            along_m=float(weights[under].sum()),
        )
    return out


def price_surveyed(
    city: CityConfig,
    graph: dict,
    drawn: dict[int, dict],
    rows: dict[int, Offset],
    tiles: list[Path],
    heroes: list[gltf.MeshData],
    bar_m: float,
) -> tuple[dict[int, Priced], list[int]]:
    """Part C, whole, so its three steps cannot be handed each other's inputs.

    ⚠️ **The binding is the point.** `priced` needs a report measured at the
    *surveyed* widths and a refusal list from the *same* `surveyed_table` call;
    given a report built at the drawn widths it prices every edge against the
    shipped ribbon instead and prints a complete, plausible table saying so.
    Nothing in the types can catch that, so the three are not separately callable
    from `main`.
    """
    table, refused = surveyed_table(drawn, rows, graph)
    report = sweep_report(city, graph, table, tiles, heroes, only=classes(city)[0])
    return priced(report, rows, graph, set(refused), bar_m), refused


def _report_authoring(
    found: dict[int, Priced],
    refused: list[int],
    graph: dict,
    names: dict[int, str],
    watched: list[int],
    bar_m: float,
) -> None:
    log.info("")
    log.info(
        "  candidate 3, priced: how much of the SURVEYED carriageway keeps under %.2f m,",
        bar_m,
    )
    log.info("  which is the geometry a fix has to author away:")
    log.info(
        "    %-6s %13s %9s %9s %10s %10s %7s  %s",
        "edge",
        "surveyed m",
        "stations",
        "under",
        "length m",
        "under m",
        "share",
        "road",
    )
    for edge in watched:
        row = found.get(edge)
        if row is None:
            log.info(
                "    e%-5d %13s  no surveyed width — unpriceable, and named rather than dropped",
                edge,
                "--",
            )
            continue
        log.info(
            "    e%-5d %13.2f %9d %9d %10.2f %10.2f %7.1f%%  %s",
            row.edge,
            row.carriageway_m,
            row.stations,
            row.stations_under,
            row.length_m,
            row.along_m,
            100.0 * row.share,
            names.get(edge, "unnamed"),
        )
    total = sum(row.along_m for row in found.values())
    starved = [row for row in found.values() if row.stations_under]
    log.info(
        "    region-wide: %.1f m of surveyed carriageway under the bar over %d of %d priced edges",
        total,
        len(starved),
        len(found),
    )
    # ⚠️ **Two refusals, split, because they are not the same refusal.** The
    # off-grade rows were never in scope — this question is about level 0 — while
    # a level-0 edge with no licensed width is a real hole in the pricing and
    # `Q19`'s own `e99`, `e125`, `e207` and `e781` are in it. One number would
    # hide the second inside the first. ⚠️ **Read off `elevation_level`, never
    # off membership of the offsets table**: an edge with a one-vertex polyline
    # is absent from that table and is level 0 all the same.
    levels = {int(edge["id"]): int(edge["elevation_level"]) for edge in graph["edges"]}
    at_grade = [edge for edge in refused if levels.get(edge) == 0]
    log.info(
        "    refused: %d level-0 edges the publishers licensed no width for, and %d rows that are "
        "not level 0 and never were in scope",
        len(at_grade),
        len(refused) - len(at_grade),
    )
    log.info(
        "    lengths are centreline metres, weighted per station — NOT a station count times the "
        "%.2f m sample pitch, which is not a length (`Priced.along_m`)",
        ALONG_M,
    )


def _ids(text: str) -> set[int]:
    return {int(part.lstrip("e")) for part in text.replace(",", " ").split()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--watch",
        default="",
        help="extra edge ids to report per-edge, e.g. carriageway_occupancy.py's grader-only three",
    )
    parser.add_argument("--spacing-m", type=float, default=STATION_M)
    parser.add_argument("--max-ray-m", type=float, default=MAX_RAY_M)
    parser.add_argument("--junction-m", type=float, default=JUNCTION_M)
    parser.add_argument("--min-stations", type=int, default=MIN_STATIONS)
    parser.add_argument(
        "--car-width-m",
        type=float,
        default=CAR_WIDTH_M,
        help="the player's own width, from taxi.tscn (default: %(default)s)",
    )
    parser.add_argument(
        "--taper-m",
        type=float,
        help="taper the shift to zero over this many metres at each end "
        "(default: surface.structure_taper_m)",
    )
    parser.add_argument(
        "--no-taper",
        action="store_true",
        help="shift rigidly and break the shared nodes, to read the upper bound",
    )
    parser.add_argument(
        "--offsets-only",
        action="store_true",
        help="stop after Part A; skips every occupier pass",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)
    survey = city.carriageway_survey
    if survey is None or survey.width_bounds is None:
        raise SystemExit(
            f"{city.id} declares no carriageway_survey.width_bounds; there is no surveyed "
            "middle to measure a centreline against"
        )
    bounds = survey.width_bounds
    # 🔴 `Q58`'s `drawn_gauge_m` trap, reachable from the command line. A ray cap
    # that cannot reach the ceiling makes every span pass the bounds by
    # construction and manufactures a clean sweep. `carriageway_margin.py`
    # refuses the same way for the same reason.
    if 2.0 * args.max_ray_m <= bounds.max_m:
        raise SystemExit(
            f"--max-ray-m {args.max_ray_m:.2f} cannot reach the {bounds.max_m:.2f} m ceiling: "
            "the cap would refuse every wide span before the bounds could"
        )

    log.info("%s / %s", city.name, region.name)
    out_dir, graph, drawn, buildings = open_region(city, args.region)
    names = road_names(graph)
    # 🔴 **One binding for both measurements.** The sign check below compares a
    # before and an after, and that comparison only means anything if the two
    # were measured at identical settings — so there is one call shape rather
    # than two that have to be kept in step by eye. The publishers are read once
    # for the same reason and because it is 2.9 s of a 33 s run.
    publishers = read_publishers(city, args.region)

    def survey(of: dict) -> dict[int, Offset]:
        return offsets(
            city,
            args.region,
            of,
            bounds,
            spacing_m=args.spacing_m,
            max_ray_m=args.max_ray_m,
            junction_m=args.junction_m,
            min_stations=args.min_stations,
            publishers=publishers,
        )

    rows = survey(graph)

    watched = sorted(_ids(args.watch))
    _report_offsets(rows, names, watched, bounds)
    by_basis: dict[str, set[int]] = {}
    for edge, row in rows.items():
        if row.licensed:
            by_basis.setdefault(row.basis, set()).add(edge)
    # 🔴 Split, never pooled. A two-way edge's offset is from the whole
    # carriageway's middle and a one-way uncrossed edge's is from its own half's;
    # one row over both is `Q57`'s generalisation, which `CLAUDE.md` names for
    # the sibling table in the same words.
    _report_distribution(rows, {"all licensed": set(rows), **by_basis})
    if args.offsets_only:
        return 0

    lane_m = float(city.roads.lane_width_m)
    taper_m = 0.0 if args.no_taper else (args.taper_m or city.roads.surface.structure_taper_m)
    tiles = tile_meshes(out_dir, buildings)
    heroes = landmark_meshes(city, args.region, out_dir)
    log.info("")
    log.info(
        "  sweeping %d rungs over %d tiles and %d hero meshes, taper %.1f m; bars %.2f m (one "
        "lane) and %.2f m (the car)",
        len(FRACTIONS),
        len(tiles),
        len(heroes),
        taper_m,
        lane_m,
        args.car_width_m,
    )

    worlds = {scale: shift_graph(graph, rows, scale=scale, taper_m=taper_m) for scale in FRACTIONS}
    # 🔴 The control must have moved nothing (`Q72`, `reachability.py`'s control
    # row). ⚠️ Comparing its edge list against the graph's would be a tautology —
    # `shift_graph` appends the original objects at scale 0 — so this asserts the
    # world's own claims about itself instead, and refuses rather than
    # `assert`ing, which `python -O` would strip.
    if worlds[0.0].delivered_m or worlds[0.0].refused or worlds[0.0].node_gap_m:
        raise SystemExit("the control world moved something; every other rung is unreadable")
    results = {
        scale: sweep(city, world.graph, drawn, tiles, heroes) for scale, world in worlds.items()
    }
    check_baseline(out_dir, city.id, args.region, results[0.0])

    _report_sweep(FRACTIONS, results, watched, names, rows)
    for bar, label in ((lane_m, "one lane"), (args.car_width_m, "the car")):
        _report_bar(bar, label, FRACTIONS, results, names)
    _report_endpoints(worlds[1.0], rows, names, watched)

    # 🔴 The sign, closed by measurement rather than by comment. A `_LEFT` the
    # wrong way round doubles the residual offset where a right one cancels it.
    moved = survey(worlds[1.0].graph)
    # ⚠️ **Paired, over the edges licensed in BOTH worlds.** `licensed` is
    # `_license`'s verdict on the re-cast span, so a shift can license an edge or
    # de-license one; comparing the two full populations would publish an
    # unpaired before/after as though it were a matched one.
    licensed_before = [edge for edge, row in rows.items() if row.licensed]
    common = [edge for edge in licensed_before if moved[edge].licensed]
    before = percentiles([abs(rows[edge].off_centre_m) for edge in common])
    after = percentiles([abs(moved[edge].off_centre_m) for edge in common])
    log.info("")
    log.info(
        "  the sign, re-measured on the shifted graph over the %d edges licensed in both "
        "(%d de-licensed by the shift): |off-centre| p50 %.3f m -> %.3f m, max %.3f m -> %.3f m",
        len(common),
        len(licensed_before) - len(common),
        before[0],
        after[0],
        before[3],
        after[3],
    )
    if after[0] > before[0] + _RESIDUAL_M:
        log.info(
            "    ⚠ the residual GREW. A shift that moves the centreline away from the middle it "
            "was measured against is a flipped sign, not a finding"
        )

    found, refused = price_surveyed(city, graph, drawn, rows, tiles, heroes, args.car_width_m)
    _report_authoring(found, refused, graph, names, watched, args.car_width_m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
