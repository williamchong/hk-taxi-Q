"""The level-0 carriageway as a region, one territory per centreline (`Q129`, `P3-33b`).

`Q95`'s survey asks each centreline for a kerb-to-kerb width, and `Q129` measured
why that stops at about half the network: on the edges still `authored`, four
mid-block cross-sections in five end in ANOTHER CENTRELINE'S share of the same
asphalt. Road Network v2 draws several centrelines per carriageway, and a width
is the carriageway's.

So this stage reads the carriageway itself:

* **R** — one plan region: the union of HyD's Pavement Polygons with their holes
  kept, and where HyD is silent, rails cast per station to the two line
  publishers' kerbs. Cut to the region's own rectangle.
* **T_e** — R cut by the Voronoi cell of edge *e*'s centreline. Every square
  metre of R has exactly one owner, so two territories can neither overlap nor
  fail to meet.

and writes `carriageway_region.json`: R's rings, each territory's rings, and at a
station every `station_m` along each edge — every published vertex among them —
how far the territory reaches to the left and to the right and what ended it.

🔴 **INERT at `P3-33b`.** Nothing reads the document yet — `export`'s inputs are
an explicit list and this is not on it — so every published file must come out
byte-identical with this stage in the chain. `P3-33c` is the first reader.

🔴 **The seam is a cut in R, not in runs, and that is a decision** (`Q116`).
A crossing run has one owner, and its far half lies in the neighbour's rectangle
where this build knows none of the centrelines it would compete with. So
ownership of ASPHALT goes by rectangle: each region draws all of R inside its
own rectangle — including the territory of a neighbour's run reaching in, which
is why `foreign` territories are published here rather than dropped — and
nothing outside it. Two rectangles share a line and nothing else, so there is no
hole and no double-draw by construction, and the two builds never have to agree
on a Voronoi. ⚠️ The price is an owned run whose far half has no territory in
this document; `owned_past_rectangle_m` counts it.

⚠️ **A second implementation of `tools/carriageway_region.py`, deliberately**, on
`Q95`'s precedent: the tool grades the stage without being the stage, and its
`|stage - tool|` line is the check. They share I/O (`gdb`, `source_reads`) and no
method. Do not "fix" a divergence by importing one into the other.

🚫 **A territory's span is a SHARE and never a `width_m`** (`Q57`): nothing here
moves the graph's width, and lanes, the arrow snap and `e99`'s carve prism keep
`Q128`'s five sources.
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.geometry.base import BaseGeometry

from pipeline import gdb
from pipeline.config import (
    CARRIAGEWAY_AREA,
    CarriagewayEdge,
    CarriagewayRegion,
    Config,
    load_config,
)
from pipeline.crs import GameTransform
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.roads import ROADGRAPH_NAME, read_graph

log = logging.getLogger(__name__)

REGION_NAME = "carriageway_region.json"
# 2: extents at dense STATIONS with the published vertices indexed into them,
# where 1 published the vertices alone — a straight street's two vertices are
# both at nodes, so 1 described a sliver the length of the block.
REGION_SCHEMA = 2
# The one level this model covers. Every publisher here is a 2D plan that reads
# the street underneath a deck (`Q103`), and `Q107`'s rim clamp already cuts the
# off-grade ribbons to their structure.
LEVEL = 0

# What ended a cross-section. `kerb` is R's own boundary, `share` another
# territory, `open` a side still inside this territory at the ray's cap, and
# `none` a vertex standing on no carriageway at all.
KERB, SHARE, OPEN, NONE = "kerb", "share", "open", "none"
# How far past a cross-section's end the far side is probed to name it.
_PROBE_M = 0.10


@dataclass
class RegionReport:
    """What the stage built, and the counters that can see it go wrong."""

    hyd_polygons: int = 0
    kerb_lines: int = 0
    hyd_m2: float = 0.0
    rails_m2: float = 0.0
    # Metres of centreline off HyD's paint, by how many sides a kerb answered
    # on. 🔴 `[0]` is the only place R is not read from a publisher — the
    # graph's `width_m` — so a rise there is the invented width coming back.
    silent_m: dict[int, float] = field(default_factory=lambda: {2: 0.0, 1: 0.0, 0: 0.0})
    rail_stations_refused: int = 0
    # Voronoi cells GEOS handed back invalid, repaired rather than dropped: a
    # dropped cell is asphalt with no owner.
    cells_repaired: int = 0
    owned_m2: float = 0.0
    foreign_m2: float = 0.0
    # Territory in pieces that never touch their own centreline. The partition
    # is Euclidean, so asphalt nearer a centreline THROUGH a median than along
    # the road is handed across it; this is that, priced.
    orphan_m2: float = 0.0
    orphan_pieces: int = 0
    edges_without_territory: int = 0
    owned_past_rectangle_m: float = 0.0
    # `Q129`'s finding, in the bundle's own words: how each published vertex's
    # cross-section ended, by the edge's `width_source`.
    ends: dict[str, Counter] = field(default_factory=dict)


@dataclass
class Centreline:
    id: int
    foreign: bool
    width_m: float
    width_source: str
    plan: np.ndarray
    line: LineString = field(init=False)

    def __post_init__(self) -> None:
        self.line = LineString(self.plan)


@dataclass
class Territory:
    edge: Centreline
    shape: BaseGeometry
    # Stations along the PUBLISHED polyline, in metres from its first vertex, and
    # at each how far the territory reaches either side and what ended it.
    along_m: list[float] = field(default_factory=list)
    left_m: list[float] = field(default_factory=list)
    right_m: list[float] = field(default_factory=list)
    left_end: list[str] = field(default_factory=list)
    right_end: list[str] = field(default_factory=list)
    # Which station each published vertex IS, in `roadgraph.json`'s own vertex
    # numbering, repeats included — the index `carriageway[]` is read under.
    vertex_station: list[int] = field(default_factory=list)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def centrelines(graph: dict) -> list[Centreline]:
    """The level's edges in published order, then the neighbour's runs.

    🔴 The published polyline is kept WHOLE, repeats included: the extents below
    are indexed by `roadgraph.json`'s own vertex numbering, as `carriageway[]`
    is, and a deduplicated plan would shift every index after the repeat.
    """
    out: list[Centreline] = []
    for foreign, key in ((False, "edges"), (True, "foreign_edges")):
        for edge in graph.get(key, ()):
            if int(edge["elevation_level"]) != LEVEL:
                continue
            plan = np.asarray(edge["polyline"], dtype=np.float64)[:, [0, 2]]
            if len(plan) < 2 or not np.any(np.diff(plan, axis=0)):
                continue
            out.append(
                Centreline(
                    id=int(edge["id"]),
                    foreign=foreign,
                    width_m=float(edge["width_m"]),
                    width_source=str(edge.get("width_source", "authored")),
                    plan=plan,
                )
            )
    return out


def _to_plan(transform: GameTransform, points) -> np.ndarray:
    projected = np.asarray(points, dtype=np.float64)
    game_x, _, game_z = transform.to_game(projected[:, 0], projected[:, 1])
    return np.column_stack([game_x, game_z])


def read_publishers(
    city: Config,
    specs: tuple[CarriagewayEdge, ...],
    region_id: str,
    transform: GameTransform,
    *,
    sources_root: Path | None = None,
) -> tuple[list[Polygon], list[LineString]]:
    """The survey's own three publishers: HyD's areas with holes, and the kerb lines.

    ⚠️ **Both grade filters are EXCLUSIONS** (`Q57`) — at grade is the unmarked
    case, so an inclusion filter keeps the flyovers and reports a plausible
    number. ⚠️ **Holes are KEPT**, which `carriageway_area.read_rings` does not
    do: a strip read *through* an island should not be cut by it, and a region
    that is going to be drawn must not pave it.
    """
    polygons: list[Polygon] = []
    kerbs: list[LineString] = []
    bbox = city.read_box(region_id).bbox
    for spec in specs:
        wanted, off_grade = set(spec.codes), set(spec.off_grade_codes)
        for path, member in source_reads(
            city, spec, region_id, root=sources_root, bounds=city.read_bounds(region_id)
        ):
            layer = gdb.read_layer(
                path,
                spec.layer.layer,
                columns=spec.layer.columns,
                bbox=bbox,
                zip_member=member,
                expect_crs=city.projected_crs,
            )
            codes = layer.column(spec.layer.field("edge_type"))
            levels = layer.column(spec.elevation_field) if spec.elevation_field else None

            def kept(owner: int, codes=codes, levels=levels, wanted=wanted, off=off_grade) -> bool:
                if str(codes[owner]) not in wanted:
                    return False
                return levels is None or str(levels[owner]) not in off

            if spec.geometry == CARRIAGEWAY_AREA:
                owners, parts = gdb.polygons(layer)
                for owner, part in zip(owners, parts, strict=True):
                    rings = [_to_plan(transform, ring) for ring in part if len(ring) >= 4]
                    if kept(owner) and rings:
                        polygons.append(Polygon(rings[0], rings[1:]))
            else:
                owners, parts = gdb.polylines(layer)
                for owner, part in zip(owners, parts, strict=True):
                    if kept(owner) and len(part) >= 2:
                        kerbs.append(LineString(_to_plan(transform, part)))
    return polygons, kerbs


# --------------------------------------------------------------------------
# R
# --------------------------------------------------------------------------


def _union(shapes: list[BaseGeometry]) -> BaseGeometry:
    if not shapes:
        return Polygon()
    return shapely.union_all(shapely.make_valid(np.asarray(shapes, dtype=object)))


def _walk(plan: np.ndarray, pitch_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Evenly pitched points along a plan, both ends included, with LEFT normals.

    Left of travel is `[u_z, -u_x]` in a frame whose x is east and whose z is
    SOUTH — `surface.mitres`' side, and the opposite of `carriageway._stations`
    (`CLAUDE.md` names the pair). This stage publishes the two sides apart, so
    the sign is load-bearing and `test_left_is_left_of_travel` pins it.
    """
    step = np.diff(plan, axis=0)
    length = np.hypot(step[:, 0], step[:, 1])
    live = length > 0.0
    step, length = step[live], length[live]
    start = plan[:-1][live]
    along = np.r_[0.0, np.cumsum(length)]
    count = max(1, int(np.ceil(along[-1] / pitch_m)))
    at = np.linspace(0.0, along[-1], count + 1)
    seg = np.clip(np.searchsorted(along, at, side="right") - 1, 0, len(length) - 1)
    unit = step[seg] / length[seg][:, None]
    points = start[seg] + unit * (at - along[seg])[:, None]
    return points, np.column_stack([unit[:, 1], -unit[:, 0]])


def rails(
    kerbs: list[LineString],
    hyd: BaseGeometry,
    lines: list[Centreline],
    *,
    pitch_m: float,
    max_m: float,
    min_span_m: float,
    report: RegionReport,
) -> BaseGeometry:
    """The carriageway where HyD is silent: rails cast to the line publishers' kerbs.

    🔴 **Rails and not the closed faces of the linework** — `Q129` measured the
    kerb lines not closing: 24 faces, 0.3% of Wan Chai's level-0 length, against
    13.5% silent. A ray does not need a closed face.

    Each station off HyD's paint casts to the nearest kerb line on either side,
    out to `max_m`. A side nothing answers on takes the edge's own median for
    that side, and an edge with none its graph `width_m` halved. A span under
    `min_span_m` is refused as the survey refuses it: a bay line or a hatched
    island, not a kerb. The rays pass THROUGH a neighbouring centreline to the
    kerb beyond, on purpose — the union is the carriageway and the partition
    says whose it is.

    ⚠️ Foreign runs cast too: inside this rectangle their asphalt is this
    region's to draw (the module docstring's seam rule).
    """
    if not hyd.is_empty:
        shapely.prepare(hyd)
    tree = STRtree(kerbs) if kerbs else None
    quads: list[BaseGeometry] = []
    for line in lines:
        points, left = _walk(line.plan, pitch_m)
        # `intersects`, not `contains`: a station ON the publisher's own edge is
        # covered, and read as silent it casts a rail from a road HyD drew.
        bare = ~shapely.intersects_xy(hyd, points[:, 0], points[:, 1])
        if not bare.any():
            continue
        wanted = bare | np.r_[bare[1:], False] | np.r_[False, bare[:-1]]
        reach = np.full((len(points), 2), np.nan)
        for row in np.flatnonzero(wanted):
            origin = Point(points[row])
            for side, sign in enumerate((1.0, -1.0)):
                if tree is None:
                    continue
                ray = LineString([points[row], points[row] + sign * left[row] * max_m])
                hits = tree.query(ray, predicate="intersects")
                if len(hits):
                    reach[row, side] = min(
                        ray.intersection(kerbs[key]).distance(origin) for key in hits
                    )
            if not np.isnan(reach[row]).any() and reach[row].sum() < min_span_m:
                reach[row] = np.nan
                report.rail_stations_refused += 1
        answered = (~np.isnan(reach)).sum(axis=1)
        pitch = np.hypot(*np.diff(points, axis=0).T)
        if not line.foreign:
            for first in range(len(points) - 1):
                for end in (first, first + 1):
                    if bare[end]:
                        report.silent_m[int(answered[end])] += 0.5 * float(pitch[first])
        typical = [
            float(np.median(side[~np.isnan(side)]))
            if (~np.isnan(side)).any()
            else line.width_m / 2.0
            for side in reach.T
        ]
        reach = np.where(np.isnan(reach), typical, reach)
        upper = points + left * reach[:, :1]
        lower = points - left * reach[:, 1:]
        for first in range(len(points) - 1):
            if bare[first] or bare[first + 1]:
                quads.append(
                    Polygon([upper[first], upper[first + 1], lower[first + 1], lower[first]])
                )
    return _union(quads)


# --------------------------------------------------------------------------
# T_e
# --------------------------------------------------------------------------


def _samples(line: Centreline, pitch_m: float) -> np.ndarray:
    """Voronoi sites along one centreline, none of them on a node.

    At `(k + 1/2) * L / n`: two edges meeting at a node would otherwise publish
    the same point, and GEOS keeps one cell for it.
    """
    length = float(line.line.length)
    count = max(1, int(length // pitch_m))
    along = (np.arange(count) + 0.5) * (length / count)
    return shapely.get_coordinates(shapely.line_interpolate_point(line.line, along))


def partition(
    whole: BaseGeometry, lines: list[Centreline], pitch_m: float, report: RegionReport
) -> list[Territory]:
    sites = [_samples(line, pitch_m) for line in lines]
    owner = np.repeat(np.arange(len(lines)), [len(site) for site in sites])
    cells = np.asarray(
        shapely.get_parts(
            shapely.voronoi_polygons(
                MultiPoint(np.vstack(sites)), extend_to=whole.envelope, ordered=True
            )
        )
    )
    if len(cells) != len(owner):
        raise ValueError(
            f"{len(owner)} centreline samples gave {len(cells)} Voronoi cells: two centrelines "
            "share a sample point, so one of them would own nothing there"
        )
    broken = ~shapely.is_valid(cells)
    report.cells_repaired = int(broken.sum())
    cells[broken] = shapely.make_valid(cells[broken])
    out: list[Territory] = []
    for key, line in enumerate(lines):
        shape = shapely.union_all(cells[owner == key]).intersection(whole)
        # Overlay leaves the odd line or point where a cell only grazes R.
        shape = _union([part for part in shapely.get_parts(shape) if part.geom_type == "Polygon"])
        out.append(Territory(line, shape))
    return out


# --------------------------------------------------------------------------
# The extents
# --------------------------------------------------------------------------


def _station_frames(
    line: Centreline, station_m: float, inset_m: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int]]:
    """Where a territory is measured: distance along, point, LEFT normal, and
    which station each published vertex is.

    🔴 **Every published vertex is a station AND there is one every `station_m`
    between them**, and the second half is not resolution for its own sake. A
    straight street is two vertices, both at nodes, where a territory pinches to
    a wedge between its neighbours — so extents at the vertices alone describe a
    sliver the length of the block. `P3-33b`'s first document did exactly that.

    A vertex is measured across the bisector of its two segments; a station
    between two across its own segment. 🔴 **An END station is measured
    `inset_m` in from its node**: the node is on the boundary of every territory
    meeting there, so a cross-section *at* it has no inside to run through and
    reads zero on a perfectly good road.
    """
    plan = line.plan
    step = np.diff(plan, axis=0)
    length = np.hypot(step[:, 0], step[:, 1])
    vertex_along = np.r_[0.0, np.cumsum(length)]
    total = float(vertex_along[-1])
    unit = np.divide(step, length[:, None], out=np.zeros_like(step), where=length[:, None] > 0.0)
    # A repeated vertex has a zero segment; it takes its neighbour's heading.
    for index in range(len(unit)):
        if length[index] == 0.0:
            unit[index] = unit[index - 1] if index else unit[np.argmax(length > 0.0)]
    bisector = np.vstack([unit[:1], unit[:-1] + unit[1:], unit[-1:]])
    flat = np.hypot(bisector[:, 0], bisector[:, 1]) < 1e-9  # a hairpin: keep the way in
    bisector[flat] = np.vstack([unit[:1], unit[:-1], unit[-1:]])[flat]
    bisector /= np.hypot(bisector[:, 0], bisector[:, 1])[:, None]

    # Regular stations, dropped where a vertex already stands within half a pitch
    # of a quarter — a quad that thin collapses in `surface._Builder.build`.
    count = max(1, int(np.ceil(total / station_m)))
    regular = np.linspace(0.0, total, count + 1)[1:-1]
    regular = regular[
        np.abs(regular[:, None] - vertex_along[None, :]).min(axis=1) > station_m / 4.0
    ]
    along = np.concatenate([vertex_along, regular])
    heading = np.vstack(
        [
            bisector,
            unit[
                np.clip(np.searchsorted(vertex_along, regular, side="right") - 1, 0, len(unit) - 1)
            ]
            if len(regular)
            else np.zeros((0, 2)),
        ]
    )
    # Stable, so a repeated vertex keeps its published order.
    order = np.argsort(along, kind="stable")
    rank = np.empty(len(order), dtype=int)
    rank[order] = np.arange(len(order))
    along, heading = along[order], heading[order]
    inset = min(inset_m, total / 2.0)
    measured = np.clip(along, inset, total - inset)
    points = shapely.get_coordinates(shapely.line_interpolate_point(line.line, measured))
    left = np.column_stack([heading[:, 1], -heading[:, 0]])
    return along, points, left, [int(index) for index in rank[: len(vertex_along)]]


def _reach(start: np.ndarray, direction: np.ndarray, shape: BaseGeometry, max_m: float) -> float:
    hit = LineString([start, start + direction * max_m]).intersection(shape)
    if hit.is_empty:
        return 0.0
    origin = Point(start)
    for piece in shapely.get_parts(hit):
        if piece.geom_type == "LineString" and piece.distance(origin) < 1e-6:
            return float(np.max(np.hypot(*(np.asarray(piece.coords) - start).T)))
    return 0.0


def measure(
    territory: Territory,
    whole: BaseGeometry,
    *,
    station_m: float,
    inset_m: float,
    max_m: float,
) -> None:
    """Fill one territory's per-station extents and what ended each."""
    along, points, left, vertex_station = _station_frames(territory.edge, station_m, inset_m)
    territory.along_m = [float(value) for value in along]
    territory.vertex_station = vertex_station
    for point, normal in zip(points, left, strict=True):
        for sign, reach_out, end_out in (
            (1.0, territory.left_m, territory.left_end),
            (-1.0, territory.right_m, territory.right_end),
        ):
            if territory.shape.is_empty:
                reach_out.append(0.0)
                end_out.append(NONE)
                continue
            reach = _reach(point, sign * normal, territory.shape, max_m)
            if reach >= max_m - 1e-6:
                kind = OPEN
            elif reach == 0.0 and not territory.shape.intersects(Point(point).buffer(_PROBE_M)):
                kind = NONE
            else:
                beyond = point + sign * normal * (reach + _PROBE_M)
                kind = SHARE if shapely.contains_xy(whole, *beyond) else KERB
            reach_out.append(reach)
            end_out.append(kind)


# --------------------------------------------------------------------------
# The stage
# --------------------------------------------------------------------------


def build(
    polygons: list[Polygon],
    kerbs: list[LineString],
    lines: list[Centreline],
    *,
    clip: BaseGeometry,
    spec: CarriagewayRegion,
    max_m: float,
    min_span_m: float,
    report: RegionReport,
) -> tuple[BaseGeometry, BaseGeometry, list[Territory]]:
    """R's two halves and every territory, measured. Pure: no file is touched."""
    report.hyd_polygons, report.kerb_lines = len(polygons), len(kerbs)
    # 🔴 Silence is asked of the publisher and not of the clip: a run cut at the
    # rectangle ends ON the clipped boundary, where `contains` is false, and read
    # against the clipped union every such end cast a 2 m rail past HyD's own
    # kerb. The tool skipped those lines by accident and `|stage - tool|` found it
    # (9.4 m2 on Causeway Bay's `e79`).
    published = _union(list(polygons))
    hyd = published.intersection(clip)
    strip = rails(
        kerbs,
        published,
        lines,
        pitch_m=spec.rail_m,
        max_m=max_m,
        min_span_m=min_span_m,
        report=report,
    )
    strip = strip.intersection(clip).difference(hyd)
    whole = shapely.union_all([hyd, strip])
    report.hyd_m2, report.rails_m2 = float(hyd.area), float(strip.area)
    if whole.is_empty:
        return hyd, strip, []
    shapely.prepare(whole)
    territories = partition(whole, lines, spec.sample_m, report)
    for territory in territories:
        edge = territory.edge
        measure(
            territory,
            whole,
            station_m=spec.station_m,
            inset_m=spec.sample_m / 2.0,
            max_m=max_m,
        )
        area = float(territory.shape.area)
        if edge.foreign:
            report.foreign_m2 += area
            continue
        report.owned_m2 += area
        report.owned_past_rectangle_m += float(edge.line.difference(clip).length)
        if territory.shape.is_empty:
            report.edges_without_territory += 1
        for part in shapely.get_parts(territory.shape):
            if not part.intersects(edge.line):
                report.orphan_m2 += float(part.area)
                report.orphan_pieces += 1
        tally = report.ends.setdefault(edge.width_source, Counter())
        for pair in zip(territory.left_end, territory.right_end, strict=True):
            tally["|".join(sorted(pair))] += 1
    return hyd, strip, territories


def _rings(shape: BaseGeometry) -> list[dict]:
    """A geometry as `{outer, holes}` plan rings at millimetre precision."""
    out = []
    for part in shapely.get_parts(shape):
        if part.geom_type != "Polygon" or part.is_empty:
            continue
        out.append(
            {
                "outer": np.round(np.asarray(part.exterior.coords), 3).tolist(),
                "holes": [np.round(np.asarray(hole.coords), 3).tolist() for hole in part.interiors],
            }
        )
    return out


def _document(
    city: Config,
    region_id: str,
    hyd: BaseGeometry,
    strip: BaseGeometry,
    territories: list[Territory],
    report: RegionReport,
) -> dict:
    return {
        "schema_version": REGION_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "level": LEVEL,
        "region": {"hyd": _rings(hyd), "rails": _rings(strip)},
        "territories": [
            {
                "edge": territory.edge.id,
                "foreign": territory.edge.foreign,
                "rings": _rings(territory.shape),
                "vertex_station": territory.vertex_station,
                "along_m": [round(value, 3) for value in territory.along_m],
                "left_m": [round(value, 3) for value in territory.left_m],
                "right_m": [round(value, 3) for value in territory.right_m],
                "left_end": territory.left_end,
                "right_end": territory.right_end,
            }
            for territory in territories
        ],
        "report": {
            "hyd_polygons": report.hyd_polygons,
            "kerb_lines": report.kerb_lines,
            "hyd_m2": round(report.hyd_m2, 1),
            "rails_m2": round(report.rails_m2, 1),
            "silent_m": {
                "kerb_both_sides": round(report.silent_m[2], 1),
                "kerb_one_side": round(report.silent_m[1], 1),
                "width_m_only": round(report.silent_m[0], 1),
            },
            "rail_stations_refused": report.rail_stations_refused,
            "cells_repaired": report.cells_repaired,
            "owned_m2": round(report.owned_m2, 1),
            "foreign_m2": round(report.foreign_m2, 1),
            "orphan_m2": round(report.orphan_m2, 1),
            "orphan_pieces": report.orphan_pieces,
            "edges_without_territory": report.edges_without_territory,
            "owned_past_rectangle_m": round(report.owned_past_rectangle_m, 1),
            "ends": {
                source: dict(sorted(tally.items())) for source, tally in sorted(report.ends.items())
            },
        },
    }


def read_region(path: Path, city_id: str, region_id: str) -> dict:
    return read_document(path, REGION_SCHEMA, f"python -m pipeline.region --region {region_id}")


def build_region(
    city: Config,
    region_id: str,
    *,
    out_root: Path | None = None,
    sources_root: Path | None = None,
) -> RegionReport | None:
    spec = city.carriageway_region
    if spec is None:
        log.info("  no carriageway_region block: the level-0 road stays a ribbon, nothing written")
        return None
    survey = city.carriageway_survey
    if survey is None:
        raise ValueError(
            "carriageway_region needs carriageway_survey: its three publishers are R's sources "
            "and its width_bounds are the rails' cap and refusal"
        )
    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    lines = centrelines(graph)
    transform = city.game_transform(region_id)
    polygons, kerbs = read_publishers(
        city, survey.edges, region_id, transform, sources_root=sources_root
    )
    high_x, high_z = city.region_high(region_id)
    report = RegionReport()
    hyd, strip, territories = build(
        polygons,
        kerbs,
        lines,
        clip=shapely.box(0.0, 0.0, high_x, high_z),
        spec=spec,
        max_m=survey.width_bounds.max_m,
        min_span_m=survey.width_bounds.hard_min_m,
        report=report,
    )
    size = write_document(
        out_dir / REGION_NAME, _document(city, region_id, hyd, strip, territories, report)
    )
    silent = sum(report.silent_m.values())
    log.info(
        "  R: %.0f m2 on %d HyD polygons + %.0f m2 of rails; HyD silent under %.0f m of "
        "centreline (kerb both sides %.0f, one side %.0f, width_m only %.0f), %d rail stations "
        "refused",
        report.hyd_m2,
        report.hyd_polygons,
        report.rails_m2,
        silent,
        report.silent_m[2],
        report.silent_m[1],
        report.silent_m[0],
        report.rail_stations_refused,
    )
    log.info(
        "  territories: %d, %.0f m2 owned + %.0f m2 foreign; orphan %.0f m2 in %d pieces; "
        "%d edges with none; %.0f m of owned run past the rectangle; %d Voronoi cells repaired",
        len(territories),
        report.owned_m2,
        report.foreign_m2,
        report.orphan_m2,
        report.orphan_pieces,
        report.edges_without_territory,
        report.owned_past_rectangle_m,
        report.cells_repaired,
    )
    # ⚠️ Over EVERY station, the ones inside the junction guard included — and a
    # station near a node ends in a share by geometry. `Q129`'s finding is the
    # tool's MID-BLOCK table; this is the same walk weighted differently, and the
    # two must not be quoted for each other (`Q57`).
    for source, tally in sorted(report.ends.items()):
        count = sum(tally.values())
        log.info(
            "  ends at every station, %-18s %5d: kerb|kerb %5.1f%%  kerb|share %5.1f%%  "
            "share|share %5.1f%%  other %5.1f%%",
            source,
            count,
            *(100.0 * tally[key] / count for key in ("kerb|kerb", "kerb|share", "share|share")),
            100.0
            * (count - tally["kerb|kerb"] - tally["kerb|share"] - tally["share|share"])
            / count,
        )
    log.info("  wrote %s (%d bytes)", REGION_NAME, size)
    return report


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
