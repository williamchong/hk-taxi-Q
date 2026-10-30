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
- 🔴 **Or when a published HEAD is hosted at it** (`signals.heads`, `Q173`'s
  `P3-3e` gate): the stop-line survey is about half the light estate — 34 of
  Wan Chai's 63 head-carrying junctions have no `RM1011` — and the two agree
  where there is no signal (4 of 198 head-less junctions have a bar). A head's
  host is its nearest level-0 edge and its junction that edge's nearer node:
  the stop line's rule, with the nearest edge for the transverse host, since a
  head is not drawn across anything.
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
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

from pipeline import gdb
from pipeline.config import Config, SignalHeads, load_config
from pipeline.crossings import CrossingReport, read_crossings
from pipeline.documents import read_document, write_document
from pipeline.drawnroad import Ribbon, kerbed_ribbons
from pipeline.fetch import source_reads
from pipeline.placements import placement, write_placements
from pipeline.polyline import (
    Segments,
    axis_residual_deg,
    bearing_deg,
    directed_residual_deg,
    plan_lengths_2d,
    plan_projections,
    plan_steps_2d,
)
from pipeline.railings import AT_GRADE
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
# would look for a mesh and find a junction table. 3 since `P3-3e`: the manifest
# names `heads_document`, which a v2 reader would never ship.
SIGNALS_MANIFEST_SCHEMA = 3
SIGNALS_PLAN_NAME = "signals_plan.json"
SIGNALS_PLAN_SCHEMA = 1
# Where each bound head stands (`P3-3e`), beside the authored library it stands.
SIGNAL_HEADS_PLACEMENTS_NAME = "signal_heads_placements.json"
# The one mesh in the library: every admitted code draws the same head (`Q76`).
SIGNAL_HEAD_MESH = "head"


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

    # The heads (`signals.heads`). Features over the gate:
    #     head_features == head_refused + head_on_structure + head_empty + head_admitted
    # and posts (one per assembly) over the host:
    #     head_posts == head_no_host + head_dead_end + head_hosted
    head_features: int = 0
    head_refused: int = 0
    head_on_structure: int = 0
    head_empty: int = 0
    head_admitted: int = 0
    head_posts: int = 0
    head_no_host: int = 0
    head_dead_end: int = 0
    head_hosted: int = 0
    head_refused_by_code: dict[str, int] = field(default_factory=dict)
    # How many features each post stands for; the collapse made visible (`Q76`).
    head_assembly_size: dict[str, int] = field(default_factory=dict)
    # Which witness signalled each junction counted in `junctions`.
    junctions_by_stop_line: int = 0
    junctions_by_heads: int = 0
    junctions_by_both: int = 0
    # Junctions the heads alone signal, by how many posts stand at them.
    heads_only_by_posts: dict[str, int] = field(default_factory=dict)

    # Where the approaches stop (`own_stop`): `approaches == sum(stops_by_source)`,
    # and how far back from its mouth each moved stop came, in metres.
    stops_by_source: dict[str, int] = field(default_factory=dict)
    stop_moved_m: list[float] = field(default_factory=list)

    # Each post bound to the approach it shows (`bind_heads`, `P3-3e`):
    #     head_posts == bound_primary + bound_secondary + every bind_* refusal
    bound_primary: int = 0
    bound_secondary: int = 0
    bind_no_host: int = 0
    bind_no_ribbon: int = 0
    bind_over_shift: int = 0
    bind_in_carriageway: int = 0
    bind_on_stub: int = 0
    bind_unstaged: int = 0
    bind_no_straight: int = 0
    bind_ambiguous: int = 0
    # Posts carrying a `P` code / only `S` codes, by role: `P` and `S` describe
    # nothing (`Q76`), and this is where that stays checkable.
    bound_by_code: dict[str, int] = field(default_factory=dict)
    # How far each BOUND head moved out to the kerb; 0.0 where it was kept.
    head_shift_m: list[float] = field(default_factory=list)
    # Staged junctions with a head for every one of their stages.
    stages_shown: int = 0


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


@dataclass(frozen=True)
class Head:
    """One published signal head feature, at its surveyed point in game plan space."""

    code: str
    x: float
    z: float


@dataclass(frozen=True)
class Post:
    """One assembly: the coincident heads one surveyed post carries (`Q76`)."""

    x: float
    z: float
    codes: tuple[str, ...]


def read_heads(
    city: Config,
    spec: SignalHeads,
    region_id: str,
    report: SignalReport,
    *,
    sources_root: Path | None,
) -> list[Head]:
    """Every head the gate admits, at grade, at its published position."""
    transform = city.game_transform(region_id)
    heads: list[Head] = []
    for path, member in source_reads(city, spec, region_id, root=sources_root):
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("code"))
        levels = layer.column(spec.layer.field("level"))
        owners, plan = gdb.points(layer)
        if len(owners) == 0:
            continue
        game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])
        for row, owner in enumerate(owners):
            report.head_features += 1
            code = str(codes[owner])
            if not spec.is_head(code):
                report.head_refused += 1
                report.head_refused_by_code[code] = report.head_refused_by_code.get(code, 0) + 1
                continue
            if str(levels[owner]).strip().lower() not in AT_GRADE:
                # On a structure: the level-0 edge nearest it is the street below.
                report.head_on_structure += 1
                continue
            x, z = float(game_x[row]), float(game_z[row])
            if not (math.isfinite(x) and math.isfinite(z)):
                # `POINT EMPTY` reads as NaN through `gdb.points`.
                report.head_empty += 1
                continue
            report.head_admitted += 1
            heads.append(Head(code, x, z))
    report.head_refused_by_code = dict(sorted(report.head_refused_by_code.items()))
    return heads


def assemble(heads: list[Head], merge_m: float) -> list[Post]:
    """Coincident heads grouped, single-linkage at `merge_m`, into the posts they stand on.

    🔴 **Derived, not read**: the layer carries no `GG_NAME`, only coincidence.
    One post per assembly — `P3-17` stacked them and drew 8.53 m masts (`Q76`).
    The post stands at its members' centroid, and the posts are sorted, so two
    builds of one input agree. O(n²) over a region's ~850 heads; a cell hash is
    the exact fix if a region ever grows past a few thousand.
    """
    if not heads:
        return []
    points = np.array([[head.x, head.z] for head in heads])
    close = (
        np.hypot(points[:, None, 0] - points[None, :, 0], points[:, None, 1] - points[None, :, 1])
        <= merge_m
    )
    seen: set[int] = set()
    posts: list[Post] = []
    for index in range(len(heads)):
        if index in seen:
            continue
        stack, members = [index], []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            members.append(current)
            stack.extend(int(other) for other in np.nonzero(close[current])[0])
        centre = points[members].mean(axis=0)
        codes = tuple(sorted(heads[member].code for member in members))
        posts.append(Post(float(centre[0]), float(centre[1]), codes))
    posts.sort(key=lambda post: (post.x, post.z))
    return posts


def host_heads(
    posts: list[Post],
    segments: Segments,
    by_id: dict[int, dict[str, Any]],
    ends: dict[int, int],
    junction: dict[int, int],
    max_offset_m: float,
    report: SignalReport,
) -> dict[int, int]:
    """Junction root -> how many posts are hosted at it.

    The stop line's rule, with the nearest level-0 edge for the transverse host
    (a head is drawn across nothing): the host edge's nearer node — by arc length
    along it, where the bar's is by straight distance to each end, since a point
    has a foot on the edge and a line need not — read as its stub cluster. A node
    only one edge reaches is the map's edge or a cul-de-sac.
    """
    found: dict[int, int] = defaultdict(int)
    sizes: dict[str, int] = defaultdict(int)
    for post in posts:
        report.head_posts += 1
        sizes[str(len(post.codes))] += 1
        snap = segments.nearest(post.x, post.z)
        if snap.distance_m > max_offset_m:
            report.head_no_host += 1
            continue
        edge = by_id[snap.edge]
        node = int(edge["from"] if snap.t <= 0.5 else edge["to"])
        if ends.get(node, 0) < 2:
            report.head_dead_end += 1
            continue
        report.head_hosted += 1
        found[junction.get(node, node)] += 1
    report.head_assembly_size = dict(sorted(sizes.items(), key=lambda item: int(item[0])))
    return dict(found)


@dataclass(frozen=True)
class Line:
    """A painted line an approach may stop at: a stop bar or a crossing, in game plan."""

    # `(n, 2)` vertices: the bar's run, or every vertex of a crossing's stripes.
    points: np.ndarray
    # A bar must lie square across its approach; a crossing's stripes run along it.
    bar: bool


def own_stop(
    plan: np.ndarray,
    mouth_m: float,
    half_width_m: float,
    two_way: bool,
    lines: list[Line],
    tolerance_deg: float,
) -> tuple[float, str]:
    """Where an approach stops: its own painted line where one is in reach, else its mouth.

    `plan` runs in the direction of travel, `mouth_m` along it. Returns the stop in
    the same terms and which source set it (`bar`, `crossing`, `mouth`).

    🔴 **Back from the mouth only, never forward** (`Q173`, 2026-10-30, the user's
    call): the mouth is where the ribbon meets the junction's cap, and the cap
    starts past the crossing the bar stands before — 53 of Wan Chai's 80 approaches
    with a line within 15 m stopped past it, a car held at red standing on the
    crossing. A line past the mouth is in the junction; the mouth already holds.

    The reach is the approach's own, with no new bar: inside the drawn corridor
    (`half_width_m`) and on the mouth's half of the edge — the far half is the
    other end's. A bar must also lie square to travel within
    `road_marks.bearing_tolerance_deg` (the axis test `transverse_host` scores)
    and, on a two-way road, on the nearside half: the other half's is the other
    flow's. A crossing spans both halves, so only its near edge is read. A bar
    wins over a crossing; nearest the mouth wins among each.
    """
    starts, steps = plan[:-1], np.diff(plan, axis=0)
    lengths = plan_steps_2d(plan)
    before = plan_lengths_2d(plan)
    floor_m = 0.5 * float(before[-1])

    def project(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Each point's along, signed nearside offset (`Snap.offset_m`'s sign), and segment."""
        fraction, distance = plan_projections(points[:, None, :], starts[None], steps)
        nearest = np.argmin(distance, axis=1)
        index = np.arange(len(points))
        along = before[nearest] + np.clip(fraction[index, nearest], 0.0, 1.0) * lengths[nearest]
        step = steps[nearest]
        left = np.column_stack([step[:, 1], -step[:, 0]]) / np.maximum(
            lengths[nearest, None], 1e-12
        )
        lateral = np.einsum("nk,nk->n", points - starts[nearest], left)
        return along, lateral, nearest

    found: dict[str, float] = {}
    for line in lines:
        if line.bar:
            (along,), (lateral,), (segment,) = project(line.points.mean(axis=0)[None])
            if abs(lateral) > half_width_m or (two_way and lateral <= 0.0):
                continue
            run = line.points[-1] - line.points[0]
            square = 90.0 - axis_residual_deg(bearing_deg(run), bearing_deg(steps[segment]))
            if square > tolerance_deg:
                continue
            stop = float(along)
        else:
            along, lateral, _ = project(line.points)
            band = np.abs(lateral) <= half_width_m
            if not band.any():
                continue
            stop = float(along[band].min())
        if floor_m <= stop <= mouth_m:
            source = "bar" if line.bar else "crossing"
            found[source] = max(found.get(source, -math.inf), stop)
    for source in ("bar", "crossing"):
        if source in found:
            return found[source], source
    return mouth_m, "mouth"


def _stopped(
    approach: Approach,
    edge: dict[str, Any],
    widths: dict[int, float],
    lines: list[Line],
    tolerance_deg: float,
    report: SignalReport,
) -> Approach:
    """`approach` with its stop moved back to its own painted line, where `own_stop` finds one."""
    plan = np.asarray(edge["polyline"], dtype=np.float64)[:, [0, 2]]
    length = float(plan_lengths_2d(plan)[-1])
    if not approach.along:
        plan = plan[::-1]
    mouth = approach.stop_m if approach.along else length - approach.stop_m
    if approach.edge not in widths:
        # No drawn corridor to read a line inside; counted, not hidden in `mouth`.
        report.stops_by_source["no_width"] = report.stops_by_source.get("no_width", 0) + 1
        return approach
    stop, source = own_stop(
        plan,
        mouth,
        0.5 * widths[approach.edge],
        edge["direction"] == "both",
        lines,
        tolerance_deg,
    )
    report.stops_by_source[source] = report.stops_by_source.get(source, 0) + 1
    if source == "mouth":
        return approach
    report.stop_moved_m.append(round(mouth - stop, 3))
    return replace(approach, stop_m=stop if approach.along else length - stop)


@dataclass(frozen=True)
class Bound:
    """A post bound to the approach it shows, standing where it is drawn."""

    x: float
    y: float
    z: float
    # The compass way the head looks: back at its approach's traffic.
    facing_deg: float
    junction: int
    # The approach, in the plan's own terms.
    edge: int
    along: bool
    stage: int
    primary: bool


def bind_heads(
    posts: list[Post],
    segments: Segments,
    by_id: dict[int, dict[str, Any]],
    drawn: dict[int, Ribbon],
    junction_of: dict[int, int],
    junctions: list[dict[str, Any]],
    spec: SignalHeads,
    tolerance_deg: float,
    report: SignalReport,
) -> list[Bound]:
    """Each post bound to the approach whose light it shows, or refused and counted.

    🔴 **Nothing publishes a head's facing or its approach** (`Q76`), so both
    come from where it stands, by the signs' rule (`signs.facing_from_side`):
    a post addresses the traffic on its kerb's side — the edge's own on a one-way
    road; on a two-way road, the flow along the edge from the nearside and
    against it from the offside (drive on the left).

    - **Primary**: the post stands on the half of its edge that traffic ends
      at, and that travel is a staged approach.
    - **Secondary** (across the junction): it stands on the half traffic
      starts from, out of a staged junction, and that junction's approaches
      running straight on to it — within `axis_tolerance_deg`, same way — are
      ONE stage. `light_at` reads only the stage, so the nearest-heading one
      stands for them.

    Never a dark head (`Q77`): everything else is refused and counted. The
    head looks back along its approach, so a lamp and its facing cannot
    disagree. The post is registered to the kerb as the signs are (`Q60`,
    outward only since `Q78`), and refused where that leaves it in a road.
    """
    approach_of: dict[tuple[int, bool], tuple[dict[str, Any], dict[str, Any]]] = {}
    staged: dict[int, dict[str, Any]] = {}
    for junction in junctions:
        staged[int(junction["id"])] = junction
        for approach in junction["approaches"]:
            approach_of[(int(approach["edge"]), bool(approach["along"]))] = (junction, approach)

    bound: list[Bound] = []
    shown: dict[int, set[int]] = defaultdict(set)
    for post in posts:
        snap = segments.nearest(post.x, post.z)
        if snap.distance_m > spec.max_offset_m:
            report.bind_no_host += 1
            continue
        ribbon = drawn.get(snap.edge)
        if ribbon is None:
            report.bind_no_ribbon += 1
            continue
        side, _, target_m, placed = ribbon.kerb_target(snap, spec.outset_m)
        shift_m = 0.0
        if ribbon.past_kerb_m(snap) > spec.outset_m:
            # Already clear of the kerb: TD's point stands (`Q78`).
            placed = np.array([post.x, post.z])
        else:
            shift_m = abs(target_m - snap.offset_m)
            if shift_m > spec.max_shift_m:
                report.bind_over_shift += 1
                continue
        settled = segments.nearest(float(placed[0]), float(placed[1]))
        settled_ribbon = drawn.get(settled.edge)
        if settled_ribbon is not None and settled_ribbon.past_kerb_m(settled) < 0.0:
            # Moved onto its own kerb and standing in another road: a junction
            # mouth where ribbons overlap. Refused, never pushed again (`P3-17`).
            report.bind_in_carriageway += 1
            continue

        edge_id = snap.edge
        start, end = int(by_id[edge_id]["from"]), int(by_id[edge_id]["to"])
        if junction_of.get(start, start) == junction_of.get(end, end):
            report.bind_on_stub += 1
            continue
        # `signs.facing_from_side`'s rule as a direction rather than a heading.
        along = ribbon.one_way or side > 0.0
        towards_end = (snap.t if along else 1.0 - snap.t) >= 0.5
        if towards_end:
            hit = approach_of.get((edge_id, along))
            if hit is None:
                report.bind_unstaged += 1
                continue
            junction, approach = hit
            primary = True
        else:
            origin = start if along else end
            junction = staged.get(junction_of.get(origin, origin))
            if junction is None:
                report.bind_unstaged += 1
                continue
            travel = (snap.heading_deg if along else snap.heading_deg + 180.0) % 360.0
            ahead = [
                one
                for one in junction["approaches"]
                if directed_residual_deg(float(one["heading_deg"]), travel) <= tolerance_deg
            ]
            if not ahead:
                report.bind_no_straight += 1
                continue
            if len({int(one["stage"]) for one in ahead}) > 1:
                report.bind_ambiguous += 1
                continue
            approach = min(
                ahead, key=lambda one: directed_residual_deg(float(one["heading_deg"]), travel)
            )
            primary = False

        role = "primary" if primary else "secondary"
        if primary:
            report.bound_primary += 1
        else:
            report.bound_secondary += 1
        letter = "P" if any(code.startswith("P") for code in post.codes) else "S"
        key = f"{letter}_{role}"
        report.bound_by_code[key] = report.bound_by_code.get(key, 0) + 1
        shown[int(junction["id"])].add(int(approach["stage"]))
        report.head_shift_m.append(round(shift_m, 3))
        bound.append(
            Bound(
                x=float(placed[0]),
                y=snap.y,
                z=float(placed[1]),
                facing_deg=(float(approach["heading_deg"]) + 180.0) % 360.0,
                junction=int(junction["id"]),
                edge=int(approach["edge"]),
                along=bool(approach["along"]),
                stage=int(approach["stage"]),
                primary=primary,
            )
        )
    report.bound_by_code = dict(sorted(report.bound_by_code.items()))
    report.stages_shown = sum(
        1 for one in junctions if shown.get(int(one["id"]), set()) >= set(range(one["stages"]))
    )
    return bound


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
    segments = Segments.of(edges)
    widths = _drawn_widths(surface)
    network = Network.of(segments, widths)
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
    lines = [
        Line(points=marking.line, bar=True)
        for marking in markings
        if marking.code in spec.stop_line_codes
    ]
    if city.crossings is not None:
        lines += [
            Line(points=np.vstack(crossing.lines), bar=False)
            for crossing in read_crossings(
                city,
                city.crossings,
                region_id,
                city.game_transform(region_id),
                CrossingReport(),
                sources_root=sources_root,
            )
        ]
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

    heads_at: dict[int, int] = {}
    posts: list[Post] = []
    if spec.heads is not None:
        heads = read_heads(city, spec.heads, region_id, report, sources_root=sources_root)
        posts = assemble(heads, spec.heads.assembly_merge_m)
        heads_at = host_heads(
            posts, segments, by_id, ends, junction, spec.heads.max_offset_m, report
        )

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
    for root in sorted(set(stop_lines) | set(heads_at)):
        report.junctions += 1
        if root in stop_lines and root in heads_at:
            report.junctions_by_both += 1
        elif root in stop_lines:
            report.junctions_by_stop_line += 1
        else:
            report.junctions_by_heads += 1
            key = str(heads_at[root])
            report.heads_only_by_posts[key] = report.heads_only_by_posts.get(key, 0) + 1
        nodes = members.get(root) or {root}
        if nodes & foreign:
            report.at_seam += 1
            continue
        pos = positions[root]
        if owner_of(np.array([pos[0], pos[2]])) != region_id:
            report.not_owned += 1
            continue
        approaches = [
            _stopped(one, by_id[one.edge], widths, lines, marks.bearing_tolerance_deg, report)
            for one in approaches_into(nodes, edges, trims)
        ]
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
                "stop_lines": stop_lines.get(root, 0),
                "heads": heads_at.get(root, 0),
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

    report.heads_only_by_posts = dict(
        sorted(report.heads_only_by_posts.items(), key=lambda item: int(item[0]))
    )
    bound: list[Bound] = []
    if spec.heads is not None and posts:
        bound = bind_heads(
            posts,
            segments,
            by_id,
            kerbed_ribbons(city, out_dir, region_id, graph, surface),
            junction,
            junctions,
            spec.heads,
            spec.axis_tolerance_deg,
            report,
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
    if bound:
        assert spec.heads is not None
        write_placements(
            out_dir / SIGNAL_HEADS_PLACEMENTS_NAME,
            city.id,
            region_id,
            spec.heads.library,
            [_stand(head) for head in bound],
        )
    else:
        (out_dir / SIGNAL_HEADS_PLACEMENTS_NAME).unlink(missing_ok=True)
    _write_manifest(out_dir, city, region_id, report)
    return report


def _stand(head: Bound) -> dict[str, Any]:
    """One placements entry: the head, and the approach whose light it shows.

    The approach is the plan's own key (`edge` in region numbering, `along`), so
    the engine resolves it through `SignalPlan.approach_on` as the cars do; the
    junction and stage ride beside it for a reader to check against the plan.
    """
    entry = placement(SIGNAL_HEAD_MESH, (head.x, head.y, head.z), head.facing_deg)
    entry.update(
        junction=head.junction,
        edge=head.edge,
        along=head.along,
        stage=head.stage,
        primary=head.primary,
    )
    return entry


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: SignalReport) -> int:
    document: dict[str, Any] = {
        "schema_version": SIGNALS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "plan_document": SIGNALS_PLAN_NAME if report.staged else None,
        "heads_document": SIGNAL_HEADS_PLACEMENTS_NAME
        if report.bound_primary + report.bound_secondary
        else None,
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
        "%d approaches (%d with their own stop line) %s, stages %s, %d crossing stages; "
        "heads %d features (%d refused, %d on structure, %d empty) -> %d posts "
        "(%d no host, %d at a dead end, %d hosted); junctions by stop line %d, heads %d, "
        "both %d; heads-only by posts %s; stops by source %s, moved back p50 %.1f max %.1f m; "
        "bound %d primary + %d secondary (%d no host, %d no ribbon, %d over shift, "
        "%d in a carriageway, %d on a stub, %d unstaged, %d no straight, %d ambiguous) %s, "
        "shift p90 %.2f max %.2f m, every stage shown at %d of %d",
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
        report.head_features,
        report.head_refused,
        report.head_on_structure,
        report.head_empty,
        report.head_posts,
        report.head_no_host,
        report.head_dead_end,
        report.head_hosted,
        report.junctions_by_stop_line,
        report.junctions_by_heads,
        report.junctions_by_both,
        report.heads_only_by_posts,
        dict(sorted(report.stops_by_source.items())),
        float(np.median(report.stop_moved_m)) if report.stop_moved_m else 0.0,
        max(report.stop_moved_m, default=0.0),
        report.bound_primary,
        report.bound_secondary,
        report.bind_no_host,
        report.bind_no_ribbon,
        report.bind_over_shift,
        report.bind_in_carriageway,
        report.bind_on_stub,
        report.bind_unstaged,
        report.bind_no_straight,
        report.bind_ambiguous,
        report.bound_by_code,
        float(np.percentile(report.head_shift_m, 90)) if report.head_shift_m else 0.0,
        max(report.head_shift_m, default=0.0),
        report.stages_shown,
        report.staged,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
