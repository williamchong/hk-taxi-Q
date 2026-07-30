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
import json
import logging
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.buildings import Placement, read_sheet
from pipeline.config import (
    BACKWARD,
    FORWARD,
    OUT_ROOT,
    CityConfig,
    RoadNetwork,
    SourceLayer,
    load_city,
)
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
    if float(np.hypot(*np.diff(run, axis=0).T).sum()) >= min_length_m:
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
    variants using full-width digits and an en-dash. Normalising to NFKC folds
    the full-width forms; the dash has to be folded by hand, because Unicode
    quite reasonably does not consider an en-dash a hyphen.
    """
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return None
    folded = "".join("-" if unicodedata.category(ch) == "Pd" else ch for ch in text)
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
    """

    def __init__(self) -> None:
        self._ids: dict[tuple[float, float], int] = {}
        self.heights: list[float] = []

    def id_for(self, x: float, z: float, y: float) -> int:
        key = (round(x, _SNAP_DECIMALS), round(z, _SNAP_DECIMALS))
        if key not in self._ids:
            self._ids[key] = len(self._ids)
            self.heights.append(y)
        return self._ids[key]

    def positions(self) -> list[tuple[float, float, float]]:
        return [(x, self.heights[i], z) for (x, z), i in self._ids.items()]

    def __len__(self) -> int:
        return len(self._ids)


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

    far_x, _, far_z = transform.to_game(bounds.max_easting, bounds.min_northing)
    region_high = (far_x, far_z)

    ground = (
        _ground(city, region_id, sources_root, region_high) if style.ground_from_terrain else None
    )
    report = RoadReport(read=len(parts))
    nodes = _Nodes()

    speed_limits, bus_lanes = _route_overlays(source, style)
    route = centrelines.column(style.centrelines.field("route"))
    elevation = centrelines.column(style.centrelines.field("elevation"))
    direction_code = centrelines.column(style.centrelines.field("travel_direction"))
    name_en = centrelines.column(style.centrelines.field("name_en"))
    name_zh = centrelines.column(style.centrelines.field("name_zh"))

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
            x, z = run[:, 0], run[:, 1]
            y, off_terrain = _heights(ground, x, z, city.deck_height_m(level))
            report.vertices_off_terrain += off_terrain

            edge_id = len(report.edges)
            edges_of_source.setdefault(source_id, []).append(edge_id)
            report.edges.append(
                Edge(
                    id=edge_id,
                    source_id=source_id,
                    from_node=nodes.id_for(x[0], z[0], y[0]),
                    to_node=nodes.id_for(x[-1], z[-1], y[-1]),
                    polyline=[
                        (float(a), float(b), float(c)) for a, b, c in zip(x, y, z, strict=True)
                    ],
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
                )
            )

    report.nodes = _nodes_with_kind(nodes.positions(), report.edges)
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
    sampled = ground.sample(x, z)
    missing = ~np.isfinite(sampled)
    if not missing.any():
        return sampled + deck_m, 0

    # The median of what *was* sampled on this edge, or the region's ground
    # floor if the whole edge missed. Better than zero, and the count is
    # returned so a terrain that stops covering the region is visible.
    fill = np.nanmedian(sampled) if np.isfinite(sampled).any() else 0.0
    return np.where(missing, fill, sampled) + deck_m, int(missing.sum())


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


def _rounded(point: tuple[float, float, float]) -> list[float]:
    """A position at millimetre precision, without a negative zero.

    A vertex clipped to the region's western edge lands on -0.0, which is a
    legal JSON number and a confusing thing to read in a file whose whole point
    is that the region starts at zero. Adding 0.0 collapses it: IEEE 754 makes
    -0.0 + 0.0 exactly +0.0, and leaves every other value alone.
    """
    return [round(value, 3) + 0.0 for value in point]


def _write(out_root: Path | None, city: CityConfig, region_id: str, report: RoadReport) -> int:
    out_dir = (out_root or OUT_ROOT) / city.id / region_id
    out_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": ROADGRAPH_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "nodes": [
            {"id": node.id, "pos": _rounded(node.pos), "kind": node.kind} for node in report.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "from": edge.from_node,
                "to": edge.to_node,
                "polyline": [_rounded(point) for point in edge.polyline],
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
    path = out_dir / ROADGRAPH_NAME
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path.stat().st_size


def _ground(
    city: CityConfig,
    region_id: str,
    sources_root: Path | None,
    region_high: tuple[float, float],
) -> HeightField:
    """The region's terrain, as a height field (`Q11`).

    Read through the building stage's sheet reader because it is the same
    sheets, the same zips and the same game-space offset. Any drift between
    where roads think the ground is and where buildings sit would show up as
    kerbs at the wrong height along every street in the region.

    A generator, not a list, and stripped of everything but geometry on the way
    through. The terrain ships a 40 MB JPEG per sheet — 224 MB across the six —
    which a height field never looks at, and materialising all six meshes first
    holds every one of those textures live at once. Measured: 962 MB peak RSS
    down to 661 MB.
    """
    place = Placement.resolve(city, region_id, sources_root, None)
    meshes = (
        replace(mesh.translated(place.offset), texture=None, uvs=None)
        for _, path in place.sheets
        for _, mesh in read_sheet(path, (city.buildings.terrain_class,))
    )
    try:
        return HeightField.from_meshes(meshes, region_high=region_high)
    except ValueError as error:
        raise ValueError(
            f"city '{city.id}' sets roads.ground to 'terrain', but region '{region_id}' has no "
            f"'{city.buildings.terrain_class}' geometry inside it in the cached sheets"
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
    if report.turns_unresolved:
        log.warning("  %d turn restrictions had no shared node", report.turns_unresolved)
    if report.vertices_off_terrain:
        log.warning("  %d vertices fell outside the terrain", report.vertices_off_terrain)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
