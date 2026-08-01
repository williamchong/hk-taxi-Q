"""Published road centrelines to a drivable graph (`P1-3`).

Reads the road network geodatabase a previous fetch cached, clips it to the
region, snaps shared endpoints into nodes, and writes `roadgraph.json` per the
contract in `docs/ARCHITECTURE.md`.

Three properties of the source shape everything here, all of them measured
rather than assumed — see `docs/DATA_SOURCES.md`:

- **Endpoints coincide exactly.** Centrelines that meet share a vertex to full
  float precision, and the nearest *distinct* pair of endpoints in the region is
  2.26 m apart. So nodes are found by exact coordinate identity, and there is no
  snapping tolerance to tune or to get wrong.
- **Grade separation must not split nodes.** Every endpoint in the region where
  two `ELEVATION` levels meet is a ramp touching down. Keying nodes on the level
  as well as the position severs the elevated network from the ground one.
- **The geometry is wildly over-densified in places.** One 51.7 m centreline
  ships 54,330 vertices. Simplification is a correctness measure for `P1-4`, not
  a size optimisation.

Nothing here knows a Hong Kong fact: layer names, column names, direction codes
and lane policy all arrive from `config/cities/*.yaml`.
"""

from __future__ import annotations

import argparse
import itertools
import logging
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.buildings import Placement, read_sheet
from pipeline.config import (
    BACKWARD,
    FORWARD,
    CityConfig,
    DeckSampling,
    RoadNetwork,
    SourceLayer,
    load_city,
)
from pipeline.documents import read_document, round_position, write_document
from pipeline.fetch import cached_source
from pipeline.terrain import HeightField

log = logging.getLogger(__name__)

ROADGRAPH_NAME = "roadgraph.json"
ROADGRAPH_SCHEMA = 1

# `Node.kind` in the data contract. Degree three or more is somewhere a
# driver can choose; anything else is a road continuing or stopping.
JUNCTION = "junction"
ENDPOINT = "endpoint"

# Endpoints are rounded to this many decimal places before being compared —
# millimetres. Anything from roughly a millimetre to a metre gives the identical
# graph, because the nearest *distinct* pair of endpoints in the region is
# 2.26 m apart, so this is not a tolerance that needs tuning.
#
# It does have to be at least this coarse. Two of the region's endpoint clusters
# differ in the last few bits and agree only once rounded: at a tenth of a
# millimetre they split into separate nodes, which silently disconnects
# Johnston Road at Fenwick Street and drops the turn restriction there.
_SNAP_DECIMALS = 3

# Leading integer of a speed-limit string. The source writes "70 km/h", and the
# units are not guaranteed to be spelled the same way twice. Anchored, so a
# label like "Route 4, 70 km/h" is rejected rather than read as 4 km/h.
_LEADING_INTEGER = re.compile(r"\s*(\d+)")

# Two clipped points closer than this in both axes are the same point. Written
# as an absolute metre tolerance rather than through `np.allclose`, whose
# default `rtol=1e-5` would silently widen it to 15 mm at the far edge of a
# 1.5 km region — and which measured 25% of this stage's runtime, called once
# per segment of every centreline that crosses the boundary.
_JOIN_EPSILON_M = 1e-9


@dataclass(frozen=True)
class Node:
    id: int
    pos: tuple[float, float, float]
    kind: str


@dataclass(frozen=True)
class Edge:
    id: int
    source_id: int
    from_node: int
    to_node: int
    polyline: list[tuple[float, float, float]]
    direction: str
    lanes: int
    width_m: float
    speed_limit_kph: int
    bus_lane: bool
    tram_tracks: bool
    elevation_level: int
    road_name: dict[str, str | None]


@dataclass(frozen=True)
class TurnRestriction:
    from_edge: int
    via_node: int
    to_edge: int


@dataclass
class RoadReport:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    turn_restrictions: list[TurnRestriction] = field(default_factory=list)
    # Centreline parts read, and how many the region boundary left nothing of.
    # The geodatabase's spatial filter selects on bounding box, so a long
    # feature can be selected without ever entering the region.
    read: int = 0
    clipped: int = 0
    # Turns whose two edges both survived clipping but share no endpoint.
    turns_unresolved: int = 0
    # Vertices before and after simplification, and how many fell outside the
    # terrain. All three are the numbers a silent regression would show up in.
    vertices_read: int = 0
    vertices_kept: int = 0
    vertices_off_terrain: int = 0
    # `P2-7`'s half of that. The failure this stage can now have is a *quiet*
    # one — a deck sample that never happens leaves the ribbon on the old flat
    # offset and produces a graph that is entirely well-formed, so these are the
    # only place it shows. Stations resampling inserted; stations whose height
    # came from the structure rather than the level's offset; structure samples
    # thrown out for sitting under the terrain; edges with at least one sample;
    # and level-0 edge ends the walk raised onto a ramp.
    vertices_added: int = 0
    vertices_on_structure: int = 0
    vertices_gated: int = 0
    edges_sampled: int = 0
    ends_lifted: int = 0
    components: list[int] = field(default_factory=list)

    @property
    def connectivity(self) -> float:
        """Share of nodes in the largest connected component."""
        return max(self.components) / sum(self.components) if self.components else 0.0


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def simplify(points: np.ndarray, tolerance_m: float) -> np.ndarray:
    """Douglas-Peucker: drop vertices no further than `tolerance_m` off the line.

    Endpoints are always kept, which is what makes this safe to run before node
    snapping — the coordinates two edges meet at are exactly the ones this
    cannot move.

    Iterative rather than recursive: an over-densified centreline here runs to
    54,330 vertices, and the recursion depth that produces is a stack overflow
    on nearly-collinear input, which is precisely the input that produces it.
    """
    if tolerance_m <= 0.0 or len(points) < 3:
        return points

    keep = np.zeros(len(points), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        offsets = _perpendicular_distance(points[start + 1 : end], points[start], points[end])
        worst = int(offsets.argmax())
        if offsets[worst] > tolerance_m:
            split = start + 1 + worst
            keep[split] = True
            stack.append((start, split))
            stack.append((split, end))
    return points[keep]


def plan_lengths(points: np.ndarray) -> np.ndarray:
    """Cumulative plan distance along a polyline, starting at zero.

    Plan rather than 3D: road widths, kerbs, junction radii and positions along
    an edge are all measured on the ground, and a 6 m ramp would otherwise be
    treated as longer than its own footprint.

    Here rather than in either consumer because both `P1-4` and `P1-5` measure
    along an edge, and two copies of this convention is two places for it to
    drift.
    """
    return np.concatenate([[0.0], np.cumsum(plan_steps(points))])


def plan_steps(points: np.ndarray) -> np.ndarray:
    """Length of each segment of a polyline, in plan."""
    return np.hypot(*np.diff(points[:, [0, 2]], axis=0).T)


def _steps(plan: np.ndarray) -> np.ndarray:
    """`plan_steps` for an array that is already two columns of `(x, z)`.

    Separate rather than a mode of the public one: inside this module a run is
    plan-only from `clip` until its heights are decided, and column indices that
    mean different things in different halves of a file are how a road ends up
    measured against its own height.
    """
    return np.hypot(*np.diff(plan, axis=0).T)


def resample(plan: np.ndarray, spacing_m: float) -> np.ndarray:
    """A plan polyline with stations inserted until no two are `spacing_m` apart.

    Every existing vertex is kept to the bit and only interior stations are
    added, so the line's shape in plan is untouched: this exists to ask the
    height field more questions along the same road, not to redraw it. Restating
    the line at evenly spaced stations instead — the obvious way to write this —
    would discard exactly the vertices `simplify` has just finished deciding are
    load-bearing, and cut every corner it left in.

    Justified by the worst vertex gap rather than the typical one. `P2-7`
    measured off-grade spacing at median 10.8 m, and sampling at today's
    vertices alone already clears the ±0.5 m criterion at p90. What it does not
    clear is the maximum: a 71.5 m gap on `FLEMING ROAD` spans structure
    climbing 4.25 to 5.05 m, a chord across it is 4.84 m out, and that is the
    defect the `P2-5` drive found. p90 hides it; the maximum is the acceptance.
    """
    if spacing_m <= 0.0 or len(plan) < 2:
        return plan

    steps = _steps(plan)
    # At least one piece per segment, so a repeated vertex survives rather than
    # dividing by zero on its way to being dropped.
    pieces = np.maximum(np.ceil(steps / spacing_m).astype(np.int64), 1)
    if not (pieces > 1).any():
        return plan

    # Each new station's position within its own segment, as a fraction. The
    # subtracted term is the exclusive prefix sum of `pieces` — the same idiom
    # `terrain.py` spreads triangles across cells with, and for the same reason:
    # a Python loop over segments is what this stage cannot afford per edge.
    starts = np.repeat(np.arange(len(steps)), pieces)
    within = np.arange(int(pieces.sum())) - np.repeat(np.cumsum(pieces) - pieces, pieces)
    fraction = (within / np.repeat(pieces, pieces))[:, None]
    # Fraction zero reproduces the original vertex exactly, which is what makes
    # "every vertex is kept" true rather than approximately true.
    stations = plan[starts] + fraction * (plan[starts + 1] - plan[starts])
    return np.vstack([stations, plan[-1]])


def clip(points: np.ndarray, high: tuple[float, float], *, min_length_m: float) -> list[np.ndarray]:
    """The runs of a polyline that lie inside `(0, 0)`-`high`, in game plan metres.

    Roads are cut at the region boundary rather than kept whole the way
    buildings are. A building overhanging its tile is half a footprint; a road
    feature overhanging the region is the Central-Wan Chai Bypass, which enters
    the geodatabase's spatial filter because its bounding box grazes the region
    and then runs 570 m out into the harbour. Left whole, 14.2% of the region's
    road length would be geometry no one can drive on — and `P1-4` would build
    a ribbon mesh for all of it.

    Cutting is safe here in a way it is not for a mesh: a polyline cut in two is
    two polylines, with no open shell and nothing to seam. The cut point becomes
    an ordinary endpoint node, which is what the map edge should be anyway.

    Runs shorter than `min_length_m` are dropped — a feature clipping a corner
    of the region contributes a stub no vehicle can occupy.
    """
    if len(points) < 2:
        # A NULL or single-vertex geometry is legal in a geodatabase and is not
        # a road. Returned as nothing here rather than allowed through, because
        # the caller indexes `[0]` and `[-1]` to find the edge's end nodes.
        return []

    runs: list[np.ndarray] = []

    # The overwhelming majority of centrelines are wholly inside, and the walk
    # below is a Python loop over every vertex — 175,610 of them in this region,
    # three quarters belonging to five over-densified features that never leave
    # it. Testing the whole array first keeps that off the slow path. It still
    # goes through `_close`, so the minimum length is one rule rather than two.
    if points.min() >= 0.0 and points[:, 0].max() <= high[0] and points[:, 1].max() <= high[1]:
        _close(runs, points, min_length_m)
        return runs

    current: list[np.ndarray] = []
    for start, end in itertools.pairwise(points):
        span = _segment_inside(start, end, high)
        if span is None:
            _close(runs, current, min_length_m)
            current = []
            continue

        enter, leave = start + span[0] * (end - start), start + span[1] * (end - start)
        if not current:
            current = [enter]
        elif abs(current[-1][0] - enter[0]) > _JOIN_EPSILON_M or (
            abs(current[-1][1] - enter[1]) > _JOIN_EPSILON_M
        ):
            # The line left the region and came back within one segment.
            _close(runs, current, min_length_m)
            current = [enter]
        current.append(leave)

    _close(runs, current, min_length_m)
    return runs


def _close(
    runs: list[np.ndarray], current: Sequence[np.ndarray] | np.ndarray, min_length_m: float
) -> None:
    if len(current) < 2:
        return
    run = np.asarray(current)
    if float(_steps(run).sum()) >= min_length_m:
        runs.append(run)


def _segment_inside(
    start: np.ndarray, end: np.ndarray, high: tuple[float, float]
) -> tuple[float, float] | None:
    """Liang-Barsky: the parameter interval of a segment inside the rectangle."""
    delta = end - start
    lower, upper = 0.0, 1.0
    for axis in (0, 1):
        for gradient, offset in (
            (-delta[axis], start[axis]),
            (delta[axis], high[axis] - start[axis]),
        ):
            if gradient == 0.0:
                # Parallel to this edge: either wholly on the right side or not
                # in the rectangle at all, and no interval to narrow.
                if offset < 0.0:
                    return None
                continue
            crossing = offset / gradient
            if gradient < 0.0:
                if crossing > upper:
                    return None
                lower = max(lower, crossing)
            else:
                if crossing < lower:
                    return None
                upper = min(upper, crossing)
    return (lower, upper) if lower < upper else None


def _perpendicular_distance(points: np.ndarray, start: np.ndarray, end: np.ndarray) -> np.ndarray:
    line = end - start
    length = float(np.hypot(*line))
    if length == 0.0:
        # A closed segment has no line to measure against, so fall back to
        # distance from the shared endpoint. Without this a loop road — a
        # roundabout drawn as one feature — collapses to nothing.
        return np.hypot(*(points - start).T)
    # The 2D cross product, written out: `np.cross` dropped support for
    # 2-vectors in numpy 2.0.
    offset = points - start
    return np.abs(line[0] * offset[:, 1] - line[1] * offset[:, 0]) / length


# --------------------------------------------------------------------------
# Attributes
# --------------------------------------------------------------------------


def clean_text(value: object, null_values: Sequence[str]) -> str | None:
    """A source text field as a string, or None where it means "no value".

    The null sentinel arrives in four spellings in this data — `-99`, and three
    variants using full-width digits and an en-dash. NFKC folds the full-width
    forms; the dash has to be folded by hand, because Unicode quite reasonably
    does not consider an en-dash a hyphen.

    The value returned is NFC, and only the *comparison* is NFKC. NFKC is a
    compatibility fold, so it also rewrites the full-width brackets Chinese
    text sets its parentheticals in as their narrow ASCII equivalents. That is
    wrong typography in 98 of the fare-node names `P1-5` reads, and those names
    go on a bilingual HUD; `test_fares.py` pins the case. No road name in the
    region is affected — all 198 are already NFC.

    Internal whitespace runs collapse to a single space. Not cosmetic either:
    the taxi datasets wrap long place names across lines, so `Location_EN`
    arrives with newlines inside it in 31 of the territory's 793 points.
    """
    if value is None:
        return None
    text = " ".join(unicodedata.normalize("NFC", str(value)).split())
    if not text:
        return None
    compatible = unicodedata.normalize("NFKC", text)
    folded = "".join("-" if unicodedata.category(ch) == "Pd" else ch for ch in compatible)
    return None if folded in null_values else text


def parse_speed_limit(value: object, default_kph: int) -> int:
    """Kilometres per hour from a text field like "70 km/h".

    Matched from the start of the string, not searched for anywhere in it: the
    field is free text, and a label like "Route 4, 70 km/h" would otherwise read
    as a 4 km/h speed limit rather than falling back to the city default.
    """
    if value is None:
        return default_kph
    match = _LEADING_INTEGER.match(str(value))
    return int(match.group(1)) if match else default_kph


# --------------------------------------------------------------------------
# Building the graph
# --------------------------------------------------------------------------


class _Nodes:
    """Endpoints to node ids, by exact coordinate identity.

    Deliberately not keyed on `ELEVATION`. Every one of the 36 endpoints in Wan
    Chai where two levels meet is a ramp touching down — `HUNG HING ROAD
    FLYOVER` at level 1 meeting itself at level 0, and so on. Adding the level
    to the key takes the region from 6 connected components to 24 and cuts a
    163-node elevated island adrift. `docs/DATA_SOURCES.md` says two edges may
    only form a junction if their levels match; that is right about *crossings*,
    which this never creates, and wrong about junctions.

    Identity is plan-only, and deliberately carries no height. That is what lets
    `build_region` name every node before it knows how high any of them are,
    which `P2-7` needs: a level-0 edge is lifted onto its ramp only where it
    meets a node another level also reaches, and which nodes those are is not
    known until every centreline has been read. `_node_heights` fills the gap
    afterwards.
    """

    def __init__(self) -> None:
        self._ids: dict[tuple[float, float], int] = {}

    def id_for(self, x: float, z: float) -> int:
        key = (round(x, _SNAP_DECIMALS), round(z, _SNAP_DECIMALS))
        if key not in self._ids:
            self._ids[key] = len(self._ids)
        return self._ids[key]

    def positions(self, heights: Sequence[float]) -> list[tuple[float, float, float]]:
        """Node positions in id order, given a height for each id."""
        return [(x, heights[index], z) for (x, z), index in self._ids.items()]

    def __len__(self) -> int:
        return len(self._ids)


@dataclass(frozen=True)
class _Pending:
    """One clipped, simplified run, held until the graph's levels are known.

    ⚠️ `edge.polyline` is empty until the second pass fills it, and it is the
    only field that is not already final. Empty rather than provisional on
    purpose: a placeholder height is a plausible number that would survive a
    missed assignment, and an empty list cannot be mistaken for geometry.
    """

    edge: Edge
    plan: np.ndarray


@dataclass(frozen=True)
class _Surfaces:
    """What the road stage samples heights from.

    Bundled because the three travel together through every height decision and
    are meaningless apart: `structure` is unreadable without `deck`'s thresholds,
    and both are gated against `ground`. Passing them separately would put the
    same three-way None check at each call site.
    """

    ground: HeightField | None
    structure: HeightField | None
    deck: DeckSampling | None

    @property
    def samples_structure(self) -> bool:
        return self.ground is not None and self.structure is not None and self.deck is not None

    def sampling(self) -> tuple[HeightField, DeckSampling]:
        """The structure field and its thresholds, for callers past the check above.

        A method rather than three `is not None` tests repeated in each sampler:
        the condition is one thing, `samples_structure` names it, and this is
        how a caller that has already asked says so.
        """
        if self.structure is None or self.deck is None:
            raise AssertionError("structure sampling asked for without a field or thresholds")
        return self.structure, self.deck

    def terrain(self, x: np.ndarray, z: np.ndarray) -> np.ndarray:
        if self.ground is None:
            raise AssertionError("terrain asked for from a city that samples none")
        return self.ground.sample(x, z)


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> RoadReport:
    """Read the region's roads and write its `roadgraph.json`."""
    style = city.roads
    bounds = city.projected_bounds(region_id)
    transform = city.game_transform(region_id)

    source = _Source(
        path=cached_source(city, style.source, root=sources_root),
        city=city,
        bbox=(bounds.min_easting, bounds.min_northing, bounds.max_easting, bounds.max_northing),
    )
    centrelines = source.read(style.centrelines)
    owners, parts = gdb.polylines(centrelines)

    region_high = city.region_high(region_id)

    surfaces = _surfaces(city, region_id, sources_root, region_high)
    report = RoadReport(read=len(parts))
    nodes = _Nodes()

    speed_limits, bus_lanes = _route_overlays(source, style)
    route = centrelines.column(style.centrelines.field("route"))
    elevation = centrelines.column(style.centrelines.field("elevation"))
    direction_code = centrelines.column(style.centrelines.field("travel_direction"))
    name_en = centrelines.column(style.centrelines.field("name_en"))
    name_zh = centrelines.column(style.centrelines.field("name_zh"))

    # Read, clipped and named in one pass; measured in a second. The seam is
    # forced by `P2-7`: whether a level-0 edge sits on a ramp depends on whether
    # its node is also reached by another level, and no edge can know that until
    # every edge has been placed. `_Nodes` keys on plan position alone, so node
    # *identity* survives the split intact and only heights wait.
    pending: list[_Pending] = []
    edges_of_source: dict[int, list[int]] = {}
    for owner, points in zip(owners, parts, strict=True):
        report.vertices_read += len(points)

        level = int(elevation[owner])
        direction = _direction(style, int(direction_code[owner]), centrelines.name)
        if direction == BACKWARD:
            # Normalised away here so `roadgraph.json` only ever says `forward`.
            points, direction = points[::-1], FORWARD

        english = clean_text(name_en[owner], style.null_values)
        limit = parse_speed_limit(
            speed_limits.get(int(route[owner])), style.default_speed_limit_kph
        )
        lanes = style.lanes_for(limit)
        source_id = int(centrelines.fids[owner])

        game_x, _, game_z = transform.to_game(points[:, 0], points[:, 1])
        plan = np.column_stack([game_x, game_z])
        runs = clip(plan, region_high, min_length_m=style.min_edge_length_m)
        if not runs:
            report.clipped += 1
        for run in runs:
            # Simplified after clipping, so the vertices the cut introduced are
            # endpoints and therefore cannot be moved.
            run = simplify(run, style.simplify_tolerance_m)
            report.vertices_kept += len(run)

            edge_id = len(pending)
            edges_of_source.setdefault(source_id, []).append(edge_id)
            pending.append(
                _Pending(
                    edge=Edge(
                        id=edge_id,
                        source_id=source_id,
                        from_node=nodes.id_for(run[0, 0], run[0, 1]),
                        to_node=nodes.id_for(run[-1, 0], run[-1, 1]),
                        polyline=[],
                        direction=direction,
                        lanes=lanes,
                        width_m=round(lanes * style.lane_width_m, 3),
                        speed_limit_kph=limit,
                        bus_lane=int(route[owner]) in bus_lanes,
                        tram_tracks=english in style.tram_streets,
                        elevation_level=level,
                        road_name={
                            "en": english,
                            "zh": clean_text(name_zh[owner], style.null_values),
                        },
                    ),
                    plan=run,
                )
            )

    mixed = _mixed_level_nodes(pending)
    report.edges = [
        _measured(item, surfaces, city.deck_height_m(item.edge.elevation_level), mixed, report)
        for item in pending
    ]

    heights = _node_heights(len(nodes), report.edges)
    report.nodes = _nodes_with_kind(nodes.positions(heights), report.edges)
    report.turn_restrictions, report.turns_unresolved = _turn_restrictions(
        source, style, report.edges, edges_of_source
    )
    report.components = _components(len(nodes), report.edges)

    _write(out_root, city, region_id, report)
    return report


@dataclass(frozen=True)
class _Source:
    """The region's road geodatabase, and the frame every read is checked against.

    Bundled rather than passed around as three arguments because every read has
    to be checked, and a check that is the caller's job to remember is a check
    that gets forgotten on the fourth layer.
    """

    path: Path
    city: CityConfig
    bbox: gdb.Bbox

    def read(self, layer: SourceLayer) -> gdb.Layer:
        """One configured layer, clipped to the region and known to be in its CRS.

        The bounding box handed to OGR is in the city's projected CRS and OGR
        does not reproject it. Reading Hong Kong coordinates on the wrong datum
        moves them ~304 m — a fifth of the width of this region — and the result
        is a plausible-looking road network somewhere it is not.
        """
        read = gdb.read_layer(self.path, layer.layer, columns=layer.columns, bbox=self.bbox)
        if read.crs and read.crs != self.city.projected_crs:
            raise ValueError(
                f"layer '{layer.layer}' is in {read.crs}, but city '{self.city.id}' declares "
                f"{self.city.projected_crs}. Reprojection is not done here — fix the config."
            )
        return read


def _direction(style: RoadNetwork, code: int, layer: str) -> str:
    if code not in style.travel_directions:
        known = ", ".join(str(k) for k in sorted(style.travel_directions))
        raise KeyError(
            f"layer '{layer}' has travel direction {code}, which the city maps no "
            f"direction for. Mapped: {known}"
        )
    return style.travel_directions[code]


def _mixed_level_nodes(pending: Iterable[_Pending]) -> set[int]:
    """Nodes more than one elevation level reaches.

    `Q13`'s 36, and every one of them measured as a ramp — 17 where the
    structure already reaches grade at the node, 13 where the publisher's
    `ELEVATION` attribute flips partway up, 5 tunnel portals and one stub. The
    13 are why the level-0 side needs anything done to it at all: there the
    at-grade edge is itself 2.1 to 4.0 m up the ramp, drawn at ground level.
    """
    levels: dict[int, set[int]] = defaultdict(set)
    for item in pending:
        levels[item.edge.from_node].add(item.edge.elevation_level)
        levels[item.edge.to_node].add(item.edge.elevation_level)
    return {node for node, found in levels.items() if len(found) > 1}


def _measured(
    item: _Pending,
    surfaces: _Surfaces,
    deck_m: float,
    mixed: set[int],
    report: RoadReport,
) -> Edge:
    """One pending run with its heights, and the report told where they came from.

    The three sources are chosen here rather than inside one branching height
    function, so what decides between them stays visible: the level, and whether
    the edge meets a node another level also reaches.
    """
    level = item.edge.elevation_level
    # Level 0 only. Level -1 is a tunnel, which is a void — its portals are
    # mixed nodes and there is no structure under them to find. `Q21` asks
    # whether they should be drawn at all; nothing here can improve their height.
    ends = (
        (item.edge.from_node in mixed, item.edge.to_node in mixed)
        if surfaces.samples_structure and level == 0
        else (False, False)
    )
    lifting = any(ends)

    plan = item.plan
    if surfaces.samples_structure and (level > 0 or lifting):
        _, deck = surfaces.sampling()
        stationed = resample(plan, deck.resample_m)
        report.vertices_added += len(stationed) - len(plan)
        plan = stationed

    x, z = plan[:, 0], plan[:, 1]
    if not surfaces.samples_structure or (level <= 0 and not lifting):
        y, missing = _heights(surfaces.ground, x, z, deck_m)
    elif level > 0:
        y, missing = _deck_heights(surfaces, x, z, deck_m, report)
    else:
        y, missing = _lifted_heights(surfaces, x, z, deck_m, ends, report)
    report.vertices_off_terrain += missing

    return replace(
        item.edge,
        polyline=[(float(a), float(b), float(c)) for a, b, c in zip(x, y, z, strict=True)],
    )


def _heights(
    ground: HeightField | None, x: np.ndarray, z: np.ndarray, deck_m: float
) -> tuple[np.ndarray, int]:
    """Deck height per vertex, and how many had no terrain under them.

    Resolves `Q11`. `elevation_levels` was always an offset per grade-separation
    level; what was missing was what it is an offset *from*. Taking it from the
    vertical datum puts every at-grade road four metres below the doorways on
    it, because Wan Chai's ground is not at the datum.
    """
    if ground is None:
        return np.full(len(x), deck_m), 0
    return _from_terrain(ground.sample(x, z), deck_m)


def _from_terrain(terrain: np.ndarray, deck_m: float) -> tuple[np.ndarray, int]:
    """The level's flat offset above sampled ground, with the holes filled.

    Split from `_heights` so the two structure samplers can reuse it as their
    fallback without sampling the terrain a second time — they need the raw
    terrain anyway, to gate their own answer against.
    """
    missing = ~np.isfinite(terrain)
    if not missing.any():
        return terrain + deck_m, 0

    # The median of what *was* sampled on this edge, or the region's ground
    # floor if the whole edge missed. Better than zero, and the count is
    # returned so a terrain that stops covering the region is visible.
    fill = np.nanmedian(terrain) if np.isfinite(terrain).any() else 0.0
    return np.where(missing, fill, terrain) + deck_m, int(missing.sum())


def _deck_heights(
    surfaces: _Surfaces, x: np.ndarray, z: np.ndarray, deck_m: float, report: RoadReport
) -> tuple[np.ndarray, int]:
    """An off-grade carriageway's height, taken from the structure it is built on.

    Answers `Q20`. `elevation_levels` gives level 1 a flat +6.0 m, and real
    flyover decks do not oblige: measured against the shipped tiles the ribbon
    is |error| p90 **4.19 m** out, and sits *below* the deck — inside the
    structure — in 66% of samples.

    ⚠️ A station the structure does not cover falls back to the deck either
    side of it, **not** to the flat offset, and the difference is the whole
    quality of the result at the one place it matters most. `INFRASTRUCTURE`
    stops being modelled where a ramp reaches grade, so the last stretch of
    every touchdown is uncovered — and at 9 of `Q13`'s nodes that is precisely
    the node itself. Measured just inside the hole, the structure sits **-0.6 to
    +1.1 m** of the terrain: the ramp has arrived, and what is missing is a
    volume nobody modelled rather than a deck. Dropping those stations back to
    +6.0 m rebuilds the cliff this function exists to remove, exactly where it
    is most visible. Interpolating holds the deck across the hole instead, which
    closed four of the nine outright and took the worst of the rest from a
    6.00 m step to 1.63 m.

    Only an edge the structure does not cover **anywhere** falls back to the
    flat offset. That is `ISLAND EASTERN CORRIDOR`'s stub, whose every sample
    the terrain gate refuses, and it is the case the offset is still right for.
    """
    structure, deck = surfaces.sampling()
    terrain = surfaces.terrain(x, z)
    fallback, missing = _from_terrain(terrain, deck_m)
    sampled = structure.sample_along(x, z, slab_gap_m=deck.slab_gap_m)

    # A deck cannot sit below the ground under it. The structure class is not
    # only elevated carriageway — `ISLAND EASTERN CORRIDOR`'s 25 m stub samples
    # 8.2 m *under* the terrain, and the next lowest anywhere in the region is
    # 0.54 m under, so the threshold sits in a 7.6 m gap rather than on a guess.
    #
    # A NaN terrain makes this comparison False and keeps the sample, which is
    # right: with no ground to measure against there is nothing to reject it on.
    under = sampled < terrain - deck.max_below_terrain_m
    usable = np.isfinite(sampled) & ~under
    report.vertices_gated += int(under.sum())
    report.vertices_on_structure += int(usable.sum())
    report.edges_sampled += int(usable.any())
    if not usable.any():
        return fallback, missing

    # Along the edge rather than by station index: `resample` inserts stations
    # but never removes the source's own, so the spacing is not uniform and
    # counting stations would weight a densely drawn curve as if it were long.
    along = np.concatenate([[0.0], np.cumsum(_steps(np.column_stack([x, z])))])
    return np.interp(along, along[usable], sampled[usable]), missing


def _lifted_heights(
    surfaces: _Surfaces,
    x: np.ndarray,
    z: np.ndarray,
    deck_m: float,
    ends: tuple[bool, bool],
    report: RoadReport,
) -> tuple[np.ndarray, int]:
    """A level-0 edge raised onto the ramp it starts on, where it starts on one.

    At 13 of `Q13`'s 36 nodes the source's `ELEVATION` flips partway up a ramp,
    which leaves the at-grade side of the flip drawn 2.1 to 4.0 m below the
    structure it is on. Sampling only the off-grade side would move that cliff
    to mid-ramp rather than close it.

    The rule is topological, not a height threshold: an edge is on this ramp
    because it connects to the edge that is on it. `P2-7` measured the
    alternative — lowest slab top within a cap above terrain — and the ramp and
    flyover-deck populations separate at 4.95 m against 5.33 m, which is 0.38 m
    to place a threshold in, and it lifts about five times what is broken. The
    walk touches 16 edge ends, and `P2-7` measured every one of them descending
    to grade inside its own edge.

    The walk stops at the first station whose structure is within `at_grade_m`
    of the ground, so a profile that wobbles by the 0.1-0.2 m the sampler is
    noisy at cannot restart it. That leaves a residual step of at most
    `at_grade_m`, which is what bounds the value.
    """
    structure, deck = surfaces.sampling()
    terrain = surfaces.terrain(x, z)
    fallback, missing = _from_terrain(terrain, deck_m)
    tops = structure.sample_lowest_above(
        x, z, terrain - deck.max_below_terrain_m, slab_gap_m=deck.slab_gap_m
    )
    lift = np.where(np.isfinite(tops), tops - terrain, 0.0)

    raised = np.zeros(len(x))
    for lifted, start, step in ((ends[0], 0, 1), (ends[1], len(x) - 1, -1)):
        if not lifted or lift[start] <= deck.at_grade_m:
            continue
        report.ends_lifted += 1
        index = start
        while 0 <= index < len(x) and lift[index] > deck.at_grade_m:
            # Maximum, not assignment: a short edge mixed at both ends is walked
            # twice, and the two runs may overlap in the middle.
            raised[index] = max(raised[index], lift[index])
            index += step

    # `terrain + lift` is the slab top itself. The level's flat offset is what
    # level 0 means where there is no ramp, and it is not an offset to add on
    # top of one — a city that puts level 0 anywhere but zero would otherwise
    # find its ramps that far above the structure they are supposed to lie on.
    return np.where(raised > 0.0, terrain + raised, fallback), missing


def _node_heights(count: int, edges: Iterable[Edge]) -> list[float]:
    """One height per node, from the edge ends that meet there.

    A node has one plan position and, at `Q13`'s 36, two genuine heights. There
    is no correct single answer, so the rule picks the one that misleads least:
    **the level nearest grade, and the highest edge end on it.**

    Nearest grade because everything that reads a node position reads it for an
    at-grade purpose — `nearest_edge` refuses off-grade edges, and the fare
    stands snap in plan. Putting a junction on the flyover overhead, or 8 m down
    a tunnel portal, is the answer that is wrong for every current consumer.

    Highest on it for the reason `HeightField.sample` takes the maximum: where
    a road surface is multi-valued at one point, the drivable face is the top,
    and a node below a ribbon end is a node inside the road.

    Until `P2-7` this was whichever edge the source happened to list first. That
    was invisible while every edge at a level shared one flat offset, and stops
    being invisible the moment the ends are sampled independently.
    """
    tops: dict[int, dict[int, float]] = defaultdict(dict)
    for edge in edges:
        for node, point in ((edge.from_node, edge.polyline[0]), (edge.to_node, edge.polyline[-1])):
            by_level = tops[node]
            level, y = edge.elevation_level, point[1]
            by_level[level] = max(by_level.get(level, y), y)

    heights = [0.0] * count
    for node, by_level in tops.items():
        # Ties — a node reached only by level -1 and level 1 — break downwards.
        # No such node exists in Wan Chai; the tie-break exists so that if one
        # ever does, it is decided here rather than by dictionary order.
        heights[node] = by_level[min(by_level, key=lambda level: (abs(level), level))]
    return heights


def _nodes_with_kind(
    positions: Sequence[tuple[float, float, float]], edges: Sequence[Edge]
) -> list[Node]:
    """Label each node `junction` or `endpoint` by how many edge ends meet there.

    Degree, not the source's intersection layer. Two centrelines meeting end to
    end is one road continuing through a geometry break rather than a junction a
    driver could turn at — and the source records those as intersections too.
    """
    degrees = [0] * len(positions)
    for edge in edges:
        degrees[edge.from_node] += 1
        degrees[edge.to_node] += 1
    return [
        Node(id=index, pos=pos, kind=JUNCTION if degrees[index] >= 3 else ENDPOINT)
        for index, pos in enumerate(positions)
    ]


def _route_overlays(source: _Source, style: RoadNetwork) -> tuple[dict[int, str], set[int]]:
    """Speed limits and bus lanes, keyed by the route id they annotate.

    Both layers are linear-referenced events against a route rather than
    attributes of a centreline. That would normally mean measuring where along
    the route each event applies — but in this dataset `ROUTE_ID` is unique per
    centreline (796 distinct values across 796 features in the region), so the
    reference collapses to a key join.
    """
    speeds = source.read(style.speed_limits)
    buses = source.read(style.bus_lanes)
    return (
        dict(
            zip(
                _routes(speeds, style.speed_limits),
                speeds.column(style.speed_limits.field("speed_limit")),
                strict=True,
            )
        ),
        set(_routes(buses, style.bus_lanes)),
    )


def _routes(layer: gdb.Layer, spec: SourceLayer) -> list[int]:
    return [int(route) for route in layer.column(spec.field("route"))]


def _turn_restrictions(
    source: _Source,
    style: RoadNetwork,
    edges: Sequence[Edge],
    edges_of_source: dict[int, list[int]],
) -> tuple[list[TurnRestriction], int]:
    """Banned movements, as `(from_edge, via_node, to_edge)`.

    Every feature in the turn layer *is* a restriction — the data specification
    defines its impedance field as negative-means-restricted and the publisher
    assigns -1 throughout — so there is nothing to filter on.

    The layer names the end of the first edge the turn passes through, and in
    213 of the region's 217 turns that end is shared with the second edge. In
    the other four it is not, while the *opposite* end coincides exactly, so the
    shared node is taken as the truth and the field only as the hint.

    A turn names source features, and clipping can split one of those into
    several edges, so every combination is tried and the pair that actually
    meets wins.

    Returns the restrictions and the count that could not be resolved.
    """
    turns = source.read(style.turns)
    first = turns.column(style.turns.field("first_edge"))
    second = turns.column(style.turns.field("second_edge"))
    at_end = turns.column(style.turns.field("first_end"))

    restrictions: list[TurnRestriction] = []
    unresolved = 0
    for row in range(len(turns)):
        from_source, to_source = int(first[row]), int(second[row])
        prefer_end = str(at_end[row]) == style.turn_at_end_value
        via = next(
            (
                (from_edge, to_edge, node)
                for from_edge in edges_of_source.get(from_source, ())
                for to_edge in edges_of_source.get(to_source, ())
                if (node := _shared_node(edges[from_edge], edges[to_edge], prefer_end=prefer_end))
                is not None
            ),
            None,
        )
        if via is not None:
            restrictions.append(TurnRestriction(from_edge=via[0], via_node=via[2], to_edge=via[1]))
        elif from_source in edges_of_source and to_source in edges_of_source:
            # Both sides survived clipping but share no node. One side merely
            # clipped away with the region is not an error: the turn layer is
            # territory-wide, exactly like the centrelines.
            unresolved += 1
    return restrictions, unresolved


def _shared_node(first: Edge, second: Edge, *, prefer_end: bool) -> int | None:
    """The node a turn passes through, preferring the end the source nominates.

    ⚠️ `prefer_end` is stated against the *source feature's* digitisation, and
    two things here can break that correspondence: reversing a `backward` edge
    swaps its ends, and clipping splits a feature so that only the last run ends
    where the feature did. The fallback below covers both, so the answer is
    right today — but it would stop being right if a turn's two edges ever met
    at *both* ends, which is a loop road or a carriageway pair closing on
    itself. Neither occurs in Wan Chai, and `backward` is unreachable for a
    source that codes direction absolutely. Recorded rather than solved: the fix
    is to carry each edge end's source provenance, which is machinery for a case
    no data has yet produced.
    """
    nominated = first.to_node if prefer_end else first.from_node
    other = first.from_node if prefer_end else first.to_node
    ends = (second.from_node, second.to_node)
    if nominated in ends:
        return nominated
    return other if other in ends else None


def _components(node_count: int, edges: Iterable[Edge]) -> list[int]:
    """Sizes of the graph's connected components, largest first."""
    parent = list(range(node_count))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for edge in edges:
        a, b = find(edge.from_node), find(edge.to_node)
        if a != b:
            parent[a] = b

    sizes: dict[int, int] = {}
    for node in range(node_count):
        root = find(node)
        sizes[root] = sizes.get(root, 0) + 1
    return sorted(sizes.values(), reverse=True)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def read_graph(path: Path, city_id: str, region_id: str) -> dict:
    """The road graph, at the version this build understands.

    Lives beside the writer below rather than in either consumer: `P1-4` draws
    the graph and `P1-5` snaps to it, and a second copy of this check is a
    second place for the version to be read wrongly.

    Takes the city and region only to name them in the rebuild command. A hint
    that does not run is worse than no hint — `python -m pipeline.roads` on its
    own exits on a missing argument, which is a second puzzle to solve while
    already stuck on the first.
    """
    rebuild = f"python -m pipeline.roads --city {city_id} --region {region_id}"
    return read_document(path, ROADGRAPH_SCHEMA, rebuild)


def _write(out_root: Path | None, city: CityConfig, region_id: str, report: RoadReport) -> int:
    out_dir = city.out_dir(region_id, out_root)
    document = {
        "schema_version": ROADGRAPH_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "nodes": [
            {"id": node.id, "pos": round_position(node.pos), "kind": node.kind}
            for node in report.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "from": edge.from_node,
                "to": edge.to_node,
                "polyline": [round_position(point) for point in edge.polyline],
                "direction": edge.direction,
                "lanes": edge.lanes,
                "width_m": edge.width_m,
                "speed_limit_kph": edge.speed_limit_kph,
                "bus_lane": edge.bus_lane,
                "tram_tracks": edge.tram_tracks,
                "elevation_level": edge.elevation_level,
                "road_name": edge.road_name,
            }
            for edge in report.edges
        ],
        "turn_restrictions": [
            {"from_edge": turn.from_edge, "via_node": turn.via_node, "to_edge": turn.to_edge}
            for turn in report.turn_restrictions
        ],
    }
    return write_document(out_dir / ROADGRAPH_NAME, document)


def _surfaces(
    city: CityConfig,
    region_id: str,
    sources_root: Path | None,
    region_high: tuple[float, float],
) -> _Surfaces:
    """The height fields this region's roads are measured against.

    The terrain resolves `Q11`; the structure resolves `Q20`, and is read only
    when the city asks for deck sampling. `load_city` refuses `roads.deck`
    without a `buildings.structure_class`, so the second half of the test below
    is a type narrowing rather than a case that can occur.

    Two passes over the sheet zips rather than one, which costs almost nothing:
    the two classes live in disjoint members, so each pass decompresses only its
    own and the duplicated work is opening the archive. Reading them together
    would mean holding both classes' geometry live to split the stream, and the
    memory note on `_field` is the reason not to.
    """
    if not city.roads.ground_from_terrain:
        return _Surfaces(ground=None, structure=None, deck=None)

    place = Placement.resolve(city, region_id, sources_root, None)
    ground = _field(place, region_high, city.buildings.terrain_class, city.id, region_id)

    deck, structure_class = city.roads.deck, city.buildings.structure_class
    if deck is None or structure_class is None:
        return _Surfaces(ground=ground, structure=None, deck=None)
    return _Surfaces(
        ground=ground,
        structure=_field(place, region_high, structure_class, city.id, region_id),
        deck=deck,
    )


def _field(
    place: Placement,
    region_high: tuple[float, float],
    class_name: str,
    city_id: str,
    region_id: str,
) -> HeightField:
    """One sheet class, as a height field.

    Read through the building stage's sheet reader because it is the same
    sheets, the same zips and the same game-space offset. Any drift between
    where roads think the ground is and where buildings sit would show up as
    kerbs at the wrong height along every street in the region — and, since
    `P2-7`, as a flyover deck that misses the tiles the player drives on.

    A generator, not a list, and stripped of everything but geometry on the way
    through. The terrain ships a 40 MB JPEG per sheet — 224 MB across the six —
    which a height field never looks at, and materialising all six meshes first
    holds every one of those textures live at once. Measured: 962 MB peak RSS
    down to 661 MB.
    """
    meshes = (
        replace(mesh.translated(place.offset), texture=None, uvs=None)
        for _, path in place.sheets
        for _, mesh in read_sheet(path, (class_name,))
    )
    try:
        return HeightField.from_meshes(meshes, region_high=region_high)
    except ValueError as error:
        raise ValueError(
            f"city '{city_id}' asks roads to sample '{class_name}', but region '{region_id}' has "
            f"no '{class_name}' geometry inside it in the cached sheets"
        ) from error


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
        "%d centreline parts read, %d clipped away, %d edges over %d nodes, %d turn restrictions",
        report.read,
        report.clipped,
        len(report.edges),
        len(report.nodes),
        len(report.turn_restrictions),
    )
    log.info(
        "  %d vertices simplified to %d (%.1f%%)",
        report.vertices_read,
        report.vertices_kept,
        100.0 * report.vertices_kept / max(1, report.vertices_read),
    )
    log.info(
        "  largest component holds %d of %d nodes (%.1f%%), %d components in all",
        max(report.components, default=0),
        len(report.nodes),
        100.0 * report.connectivity,
        len(report.components),
    )
    if report.edges_sampled or report.ends_lifted:
        log.info(
            "  %d edges took their height from the structure over %d added stations, "
            "%d vertices sampled, %d level-0 ends lifted onto a ramp",
            report.edges_sampled,
            report.vertices_added,
            report.vertices_on_structure,
            report.ends_lifted,
        )
    if report.turns_unresolved:
        log.warning("  %d turn restrictions had no shared node", report.turns_unresolved)
    if report.vertices_off_terrain:
        log.warning("  %d vertices fell outside the terrain", report.vertices_off_terrain)
    if report.vertices_gated:
        log.warning(
            "  %d structure samples sat under the terrain and were refused", report.vertices_gated
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
