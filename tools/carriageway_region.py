"""The level-0 carriageway as a REGION, partitioned among centrelines (`Q129`).

`Q95`'s survey asks each centreline how far it is to a kerb on either side, and
`Q128` took that to 53.5% of Wan Chai's level-0 edges. `Q129` records why it
stops there: on the edges still authored, most cross-sections are bounded by
ANOTHER CENTRELINE'S share of the same asphalt and not by a kerb, so the number
the survey asks for does not exist. Road Network v2 draws several centrelines
per carriageway — slip lanes, junction links, the lanes of GLOUCESTER ROAD — and
a width is a property of the carriageway, not of any one of them.

This tool reads the carriageway the other way round. It builds

* **R** — the at-grade carriageway as one plan region: the union of HyD's
  Pavement Polygons; and where HyD is silent, rails cast per station to the two
  line publishers' kerbs (TD `RM1108`/`RM1109`, iB1000 `RM`), with the graph's
  own `width_m` only on a side no kerb answers on;
* **T_e** — each level-0 edge's *territory*: R cut by the Voronoi cell of that
  edge's centreline, so every square metre of R has exactly one owner;

and prints what a build on that model would inherit: R's composition by
centreline length, each territory's left/right extent per station against the
ray survey's widths, how each cross-section ENDS (a kerb, another territory, or
open), and the territory that is owned but not reachable.

🔴 **It is read-only and it grades nothing in the bundle yet** — no stage builds
R today. When one does, this stays on as its second implementation, on
`carriageway_margin.py`'s precedent: it takes its I/O from `pipeline.gdb` and
no method from `pipeline.carriageway` or `pipeline.carriageway_area`.

⚠️ **The agreement with the ray survey is partly BUILT IN and must not be read
as a second source**: where R comes from HyD, the ray survey's third publisher
is that same polygon's boundary. What the agreement shows is that the
instrument is sound on the population where a width exists. The finding is the
END-PAIR table on the population where it does not.

⚠️ **The partition is Euclidean, the flood `Q129` was first measured with was
geodesic.** Asphalt nearer a centreline *through* a median than along the road
is handed across it. `orphan` — territory in pieces that never touch their own
centreline — is the counter that prices that, and it is quoted with every run.

⚠️ **Holes are kept.** `carriageway_area.read_rings` drops them because a strip
read *through* an island should not be cut by it; a region that is going to be
DRAWN must not pave the island. The centreline length standing in a hole is
printed, because that is where keeping them could be wrong.

⚠️ It grades rather than checks and exits 0 whatever it finds.

    python tools/carriageway_region.py --region wan_chai --svg /tmp/region.svg
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import gdb  # noqa: E402
from pipeline.config import CARRIAGEWAY_AREA, CarriagewayEdge, Config, load_config  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402

log = logging.getLogger("carriageway_region")

# The ray survey's own walk, restated: two readings stationed differently cannot
# be compared (`STATION_M`/`JUNCTION_M`'s own rule in `pipeline/carriageway.py`).
STATION_M = 4.0
JUNCTION_M = 12.0
# The width sources a ray measured. `hyd_strip` is deliberately absent, as it is
# from `width_evidence.MEASURED`: where R is HyD's, a strip graded against a
# territory is HyD graded against HyD.
RAY_SOURCES = ("two_way_span", "one_way_uncrossed")
# How far past a cross-section's end the far side is sampled to name what ended
# it. Small against any kerb and large against the snap.
_PROBE_M = 0.10


# --------------------------------------------------------------------------
# Reading the publishers
# --------------------------------------------------------------------------


def _layers(city: Config, spec: CarriagewayEdge, region_id: str, sources_root: Path | None):
    bbox = city.read_box(region_id).bbox
    reads = source_reads(
        city, spec, region_id, root=sources_root, bounds=city.read_bounds(region_id)
    )
    for path, member in reads:
        yield gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )


def _kept(spec: CarriagewayEdge, layer) -> np.ndarray:
    """Which features are this publisher's at-grade carriageway edge.

    Both grade filters are EXCLUSIONS (`Q57`): at grade is the unmarked case, so
    an inclusion filter keeps the flyovers and reports a plausible number.
    """
    wanted, off_grade = set(spec.codes), set(spec.off_grade_codes)
    codes = layer.column(spec.layer.field("edge_type"))
    levels = layer.column(spec.elevation_field) if spec.elevation_field else None
    keep = np.array([str(code) in wanted for code in codes], dtype=bool)
    if levels is not None:
        keep &= np.array([str(level) not in off_grade for level in levels], dtype=bool)
    return keep


def _plan(transform, points) -> np.ndarray:
    projected = np.asarray(points, dtype=np.float64)
    game_x, _, game_z = transform.to_game(projected[:, 0], projected[:, 1])
    return np.column_stack([game_x, game_z])


def read_publishers(
    city: Config, region_id: str, sources_root: Path | None
) -> tuple[list[Polygon], list[LineString]]:
    """HyD's carriageway polygons WITH their holes, and the line publishers' kerbs."""
    survey = city.carriageway_survey
    if survey is None:
        raise SystemExit(f"city '{city.id}' declares no carriageway_survey block")
    transform = city.game_transform(region_id)
    polygons: list[Polygon] = []
    kerbs: list[LineString] = []
    for spec in survey.edges:
        for layer in _layers(city, spec, region_id, sources_root):
            keep = _kept(spec, layer)
            if spec.geometry == CARRIAGEWAY_AREA:
                owners, parts = gdb.polygons(layer)
                for owner, part in zip(owners, parts, strict=True):
                    rings = [_plan(transform, ring) for ring in part if len(ring) >= 4]
                    if keep[owner] and rings:
                        polygons.append(Polygon(rings[0], rings[1:]))
            else:
                owners, parts = gdb.polylines(layer)
                for owner, part in zip(owners, parts, strict=True):
                    if keep[owner] and len(part) >= 2:
                        kerbs.append(LineString(_plan(transform, part)))
    return polygons, kerbs


# --------------------------------------------------------------------------
# The graph
# --------------------------------------------------------------------------


@dataclass
class Centreline:
    id: int
    foreign: bool
    width_m: float
    width_source: str
    name: str
    plan: np.ndarray
    line: LineString = field(init=False)

    def __post_init__(self) -> None:
        self.line = LineString(self.plan)

    @property
    def length(self) -> float:
        return float(self.line.length)


def centrelines(graph: dict, level: int) -> list[Centreline]:
    """The level's edges, and the neighbour's runs beside them.

    Foreign edges take part in the partition and own nothing reported: past the
    shared line the nearest road is the neighbour's (`Q116`), and without them
    this region would claim the neighbour's asphalt.
    """
    out: list[Centreline] = []
    for foreign, key in ((False, "edges"), (True, "foreign_edges")):
        for edge in graph.get(key, ()):
            if edge["elevation_level"] != level:
                continue
            plan = np.asarray(edge["polyline"], dtype=np.float64)[:, [0, 2]]
            plan = plan[np.r_[True, np.any(np.diff(plan, axis=0) != 0.0, axis=1)]]
            if len(plan) < 2:
                continue
            out.append(
                Centreline(
                    id=int(edge["id"]),
                    foreign=foreign,
                    width_m=float(edge["width_m"]),
                    width_source=str(edge.get("width_source", "authored")),
                    name=str((edge.get("road_name") or {}).get("en") or ""),
                    plan=plan,
                )
            )
    return out


# --------------------------------------------------------------------------
# R
# --------------------------------------------------------------------------


@dataclass
class Region:
    hyd: BaseGeometry
    strip: BaseGeometry
    whole: BaseGeometry
    # Metres of centreline off HyD's paint, by how many sides a kerb answered on.
    silent_m: dict[int, float] = field(default_factory=lambda: {2: 0.0, 1: 0.0, 0: 0.0})
    stations_refused: int = 0


def _valid_union(shapes: list) -> BaseGeometry:
    return unary_union([shapely.make_valid(shape) for shape in shapes]) if shapes else Polygon()


def _rail_stations(plan: np.ndarray, spacing_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Points and unit right normals along a centreline, BOTH ENDS INCLUDED.

    Unlike `stations`, which keeps clear of the nodes to compare with the survey:
    a strip that stops short of its node leaves the junction undrawn.
    """
    step = np.diff(plan, axis=0)
    length = np.hypot(step[:, 0], step[:, 1])
    along = np.r_[0.0, np.cumsum(length)]
    count = max(1, int(np.ceil(along[-1] / spacing_m)))
    at = np.linspace(0.0, along[-1], count + 1)
    seg = np.clip(np.searchsorted(along, at, side="right") - 1, 0, len(length) - 1)
    unit = step[seg] / length[seg][:, None]
    points = plan[seg] + unit * (at - along[seg])[:, None]
    return points, np.column_stack([-unit[:, 1], unit[:, 0]])


def _box_sides(ring: Polygon) -> tuple[float, float]:
    """(short, long) side of the tightest rectangle around a ring.

    Swept by ANGLE at a tenth of a degree, where the stage walks the hull's own
    edges: two routes to one rectangle, so neither can carry the other's slip.
    """
    xy = np.asarray(ring.exterior.coords) - np.asarray(ring.centroid.coords[0])
    turn = np.deg2rad(np.arange(0.0, 90.0, 0.1))
    along = xy @ np.vstack([np.cos(turn), np.sin(turn)])
    across = xy @ np.vstack([-np.sin(turn), np.cos(turn)])
    spans = np.column_stack([np.ptp(along, axis=0), np.ptp(across, axis=0)])
    best = spans[np.argmin(spans.prod(axis=1))]
    return float(best.min()), float(best.max())


def free_islands(
    published: BaseGeometry, kerbs: list[LineString], max_length_m: float, max_width_m: float
) -> tuple[list[Polygon], set[int]]:
    """Kerbed islands standing in the carriageway (`pipeline/region.islands_of`):
    HyD's holes and the line publishers' free-standing closed rings, shorter than
    a rail follows and no wider than a lane. The second value is which kerb lines
    a ray passes through when there is a kerb behind them."""

    def small(ring: Polygon) -> bool:
        if not ring.is_valid or ring.is_empty:
            return False
        short, long = _box_sides(ring)
        return long < max_length_m and short <= max_width_m

    holes = [
        Polygon(ring)
        for part in shapely.get_parts(published)
        if part.geom_type == "Polygon"
        for ring in part.interiors
    ]
    found = [hole for hole in holes if small(hole)]
    through: set[int] = set()
    for key, kerb in enumerate(kerbs):
        if not kerb.is_ring or len(kerb.coords) < 4 or not small(Polygon(kerb)):
            continue
        # Free-standing: no other kerb line so much as touches it.
        if any(other is not kerb and other.intersects(kerb) for other in kerbs):
            continue
        through.add(key)
        found.append(Polygon(kerb))
    return found, through


def kerb_strip(
    kerbs: list[LineString],
    hyd: BaseGeometry,
    lines: list[Centreline],
    *,
    spacing_m: float,
    max_m: float,
    min_span_m: float,
    through: set[int] | None = None,
) -> tuple[BaseGeometry, dict[int, float], int]:
    """The carriageway where HyD is silent: rails cast to the line publishers' kerbs.

    🔴 **Not the closed faces of the linework, and that is measured.** The two
    line publishers' kerbs do not close: polygonised at a 5 cm snap they offer 24
    faces a silent Wan Chai centreline runs through, 0.3% of the level-0 length,
    while HyD is silent under 13.5% of it — GLOUCESTER ROAD's main carriageway
    and the whole of HKCEC included. A ray does not need a closed face.

    Each station off HyD's paint casts to the nearest kerb line on either side,
    out to `max_m`. A side nothing answers on takes the edge's own median for
    that side, and an edge with none its graph `width_m` halved — the only
    place R is not read from a publisher, and `silent_m[0]` is its length.
    ⚠️ A span under `min_span_m` is refused as the survey refuses it: the ray
    landed on a bay line or a hatched island, not a kerb.

    ⚠️ A FOREIGN run casts too and is counted nowhere: inside this rectangle its
    asphalt is this region's to draw (`pipeline/region.py`'s seam rule), so leaving
    it out would leave a hole where the neighbour's road reaches in.

    The rays pass THROUGH a neighbouring centreline to the kerb beyond it, on
    purpose. Where three centrelines share one carriageway the strips overlap,
    the union is that carriageway, and the partition — not the ray — says whose
    it is.
    """
    shapely.prepare(hyd)
    tree = STRtree(kerbs) if kerbs else None
    quads: list[Polygon] = []
    silent = {2: 0.0, 1: 0.0, 0: 0.0}
    refused = 0
    through = through or set()
    axis_of = {line.id: LineString(line.plan) for line in lines}
    for line in lines:
        points, right = _rail_stations(line.plan, spacing_m)
        axis = axis_of[line.id]
        # `intersects`, not `contains`: a station ON the publisher's own edge is
        # covered, and read as silent it casts a rail from a road HyD drew.
        bare = ~shapely.intersects_xy(hyd, points[:, 0], points[:, 1])
        if not bare.any():
            continue
        reach = np.full((len(points), 2), np.nan)
        for row in np.flatnonzero(bare | np.r_[bare[1:], False] | np.r_[False, bare[:-1]]):
            for side, sign in enumerate((-1.0, 1.0)):
                ray = LineString([points[row], points[row] + sign * right[row] * max_m])
                if tree is None:
                    continue
                # 🔴 A line that CROSSES this road is not its kerb: refused where it
                # reaches the centreline nearer, along the road, than the hit
                # stands off it. And a ray passes through an island to the kerb
                # behind it — where there is one.
                here = axis.project(Point(points[row]))
                kept: dict[int, float] = {}
                for key in tree.query(ray, predicate="intersects"):
                    off = ray.intersection(kerbs[key]).distance(Point(points[row]))
                    meets = axis.intersection(kerbs[key])
                    nearest = min(
                        (
                            abs(axis.project(Point(xy)) - here)
                            for xy in shapely.get_coordinates(meets)
                        ),
                        default=np.inf,
                    )
                    if nearest > off:
                        kept[int(key)] = off
                behind = [off for key, off in kept.items() if key not in through]
                if kept:
                    reach[row, side] = min(behind or kept.values())
            if np.nansum(reach[row]) < min_span_m and not np.isnan(reach[row]).any():
                reach[row] = np.nan
                refused += 1
        pitch = np.hypot(*np.diff(points, axis=0).T)
        answered = (~np.isnan(reach)).sum(axis=1)
        for first in range(len(points) - 1):
            # Half an interval per bare end, so the three lines sum to the length
            # off HyD's paint and not to every interval touching it.
            for end in (first, first + 1):
                if bare[end] and not line.foreign:
                    silent[int(answered[end])] += 0.5 * float(pitch[first])
        typical = np.array(
            [
                np.median(side[~np.isnan(side)]) if (~np.isnan(side)).any() else line.width_m / 2.0
                for side in reach.T
            ]
        )
        reach = np.where(np.isnan(reach), typical, reach)
        left = points - right * reach[:, :1]
        rght = points + right * reach[:, 1:]
        for first in range(len(points) - 1):
            if bare[first] or bare[first + 1]:
                quads.append(Polygon([left[first], left[first + 1], rght[first + 1], rght[first]]))
    return _valid_union(quads), silent, refused


def build_region(
    polygons: list[Polygon],
    kerbs: list[LineString],
    lines: list[Centreline],
    *,
    clip: BaseGeometry,
    spacing_m: float,
    max_m: float,
    min_span_m: float,
    seam_m: float = 0.0,
    island_m: tuple[float, float] | None = None,
) -> Region:
    """R, cut to the region's own rectangle.

    The publishers are read `join.reach_m` past the rectangle and further, and
    the graph is not: asphalt out there has no centreline of this region's to
    own it, so unclipped it is handed to whichever edge is nearest — 6.8% of
    Wan Chai's territory, one piece 228 m from its owner. ⚠️ An owned run's far
    half past a shared line (`Q116`) is cut with it, and `main` prints how many
    metres that is, because a build has to decide it and this tool does not.
    """
    # Silence is the publisher's, not the clip's: see `pipeline/region.build`.
    published = _valid_union(polygons)
    if seam_m > 0.0:
        # HyD's tiles do not always meet, and a sliver between two of them reads
        # as a kerb on the centreline (`pipeline/region._closed`). Filled here as
        # the gaps themselves — what a dilation reaches and an erosion leaves —
        # so the stage's closing and this one are two routes to one region.
        grown = published.buffer(seam_m, join_style="mitre")
        gaps = grown.buffer(-seam_m, join_style="mitre").difference(published)
        # Polygons only: the difference leaves the odd line where the two touch.
        slivers = [part for part in shapely.get_parts(gaps) if part.geom_type == "Polygon"]
        # ⚠️ A pairwise `union`, never `unary_union` over the list: cascaded over
        # 414 slivers GEOS filled HyD's holes (+9,010 m2 on Wan Chai) and said
        # nothing; `|stage - tool|` found it at 4,145 m2 on one territory.
        published = shapely.union(published, shapely.union_all(slivers))
        published = shapely.multipolygons(
            [part for part in shapely.get_parts(published) if part.geom_type == "Polygon"]
        )
    hyd = published.intersection(clip)
    islands, through = free_islands(published, kerbs, *island_m) if island_m else ([], set())
    strip, silent, refused = kerb_strip(
        kerbs,
        published,
        lines,
        spacing_m=spacing_m,
        max_m=max_m,
        min_span_m=min_span_m,
        through=through,
    )
    strip = strip.intersection(clip)
    if islands:
        strip = strip.difference(unary_union(islands))
    whole = unary_union([hyd, strip])
    return Region(
        hyd=hyd,
        strip=strip.difference(hyd),
        whole=whole,
        silent_m=silent,
        stations_refused=refused,
    )


# --------------------------------------------------------------------------
# T_e
# --------------------------------------------------------------------------


def territories(
    region: Region, lines: list[Centreline], sample_m: float
) -> dict[int, BaseGeometry]:
    """R cut by each centreline's Voronoi cell — one owner per square metre.

    Samples sit at `sample_m / 2 + k * sample_m` along each centreline, so no
    sample stands on a node: two edges meeting there would otherwise publish the
    same point twice, and GEOS keeps one cell for it.
    """
    points: list[np.ndarray] = []
    owner: list[int] = []
    for key, line in enumerate(lines):
        count = max(1, int(line.length // sample_m))
        along = (np.arange(count) + 0.5) * (line.length / count)
        xy = shapely.get_coordinates(shapely.line_interpolate_point(line.line, along))
        points.append(xy)
        owner.extend([key] * len(xy))
    cloud = MultiPoint(np.vstack(points))
    cells = shapely.voronoi_polygons(cloud, extend_to=region.whole.envelope, ordered=True)
    parts = np.asarray(shapely.get_parts(cells))
    # GEOS can hand back a self-touching cell on the hull, tens of metres from any
    # sample (1 of Wan Chai's 45,086), and the union then fails on it with "unable
    # to assign free hole to a shell". Repaired rather than dropped: a dropped cell
    # is asphalt with no owner.
    broken = ~shapely.is_valid(parts)
    parts[broken] = shapely.make_valid(parts[broken])
    owners = np.asarray(owner)
    if len(parts) != len(owners):
        raise SystemExit(
            f"{len(owners)} samples gave {len(parts)} Voronoi cells — two centrelines share a "
            "sample point, so one of them would own nothing there"
        )
    out: dict[int, BaseGeometry] = {}
    prepared = region.whole
    for key, line in enumerate(lines):
        cell = shapely.union_all(parts[owners == key])
        if not line.foreign:
            out[line.id] = cell.intersection(prepared)
    return out


# --------------------------------------------------------------------------
# The cross-sections
# --------------------------------------------------------------------------


def stations(plan: np.ndarray, spacing_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Points, unit RIGHT normals and distance-to-nearer-end along one centreline.

    The normal is RIGHT of travel — `[-u_z, u_x]` in a frame whose x is east and
    whose z is SOUTH — as `carriageway._stations` emits it. 🔴 Load-bearing here
    where it is not there: that stage keeps only sign-free sums, this tool keeps
    the two sides apart, and the first build had them swapped with every table
    unmoved. `test_left_is_left_of_travel` is what fails.
    """
    step = np.diff(plan, axis=0)
    length = np.hypot(step[:, 0], step[:, 1])
    along = np.r_[0.0, np.cumsum(length)]
    total = along[-1]
    at = np.arange(spacing_m / 2.0, total, spacing_m)
    seg = np.minimum(len(length) - 1, np.searchsorted(along, at, side="right") - 1)
    unit = step[seg] / length[seg][:, None]
    points = plan[seg] + unit * (at - along[seg])[:, None]
    right = np.column_stack([-unit[:, 1], unit[:, 0]])
    return points, right, np.minimum(at, total - at)


def _reach(start: np.ndarray, direction: np.ndarray, shape: BaseGeometry, max_m: float) -> float:
    """How far the ray runs inside `shape` before it first leaves it."""
    ray = LineString([start, start + direction * max_m])
    hit = ray.intersection(shape)
    if hit.is_empty:
        return 0.0
    # Merged first: a territory can come back from GEOS as two parts that touch,
    # and the ray across their seam is then two pieces end to end. Read piecewise
    # it stopped at the seam — `e451` read 3.99 m or 6.545 m depending on which
    # overlay built the shape, from rings identical on disk.
    hit = shapely.line_merge(hit) if hit.geom_type == "MultiLineString" else hit
    origin = Point(start)
    for piece in shapely.get_parts(hit):
        if piece.geom_type == "LineString" and piece.distance(origin) < 1e-6:
            ends = np.asarray(piece.coords)
            return float(np.max(np.hypot(*(ends - start).T)))
    return 0.0


@dataclass
class Section:
    edge: int
    near_m: float
    left_m: float
    right_m: float
    left_end: str
    right_end: str

    @property
    def span_m(self) -> float:
        return self.left_m + self.right_m


def cross_sections(
    region: Region,
    owned: dict[int, BaseGeometry],
    lines: list[Centreline],
    *,
    max_m: float,
) -> list[Section]:
    shapely.prepare(region.whole)
    out: list[Section] = []
    for line in lines:
        shape = owned.get(line.id)
        if shape is None or shape.is_empty:
            continue
        points, right, near = stations(line.plan, STATION_M)
        for point, normal, distance in zip(points, right, near, strict=True):
            ends = []
            for direction in (-normal, normal):
                reach = _reach(point, direction, shape, max_m)
                if reach >= max_m - 1e-6:
                    ends.append((reach, "open"))
                    continue
                beyond = Point(point + direction * (reach + _PROBE_M))
                ends.append((reach, "share" if region.whole.contains(beyond) else "kerb"))
            out.append(
                Section(line.id, float(distance), ends[0][0], ends[1][0], ends[0][1], ends[1][1])
            )
    return out


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _length_in(lines: list[Centreline], shape: BaseGeometry) -> float:
    if shape.is_empty:
        return 0.0
    shapely.prepare(shape)
    return float(sum(line.line.intersection(shape).length for line in lines if not line.foreign))


def _percentiles(values: np.ndarray) -> str:
    if not len(values):
        return "n=0"
    magnitude = np.abs(values)
    return (
        f"n={len(values):4d}  p50 {np.median(values):+.2f}"
        f"  |p50| {np.percentile(magnitude, 50):.2f}"
        f"  |p90| {np.percentile(magnitude, 90):.2f}  max {magnitude.max():.2f}"
    )


def report(
    region: Region,
    owned: dict[int, BaseGeometry],
    lines: list[Centreline],
    sections: list[Section],
) -> None:
    own = [line for line in lines if not line.foreign]
    total = sum(line.length for line in own)
    log.info("")
    log.info("  R, by level-0 centreline length (%.1f km over %d edges):", total / 1000.0, len(own))
    on_hyd = _length_in(own, region.hyd)
    log.info(
        "    %-34s %7.0f m  %5.1f%%   %8.0f m2",
        "HyD pavement polygons",
        on_hyd,
        100.0 * on_hyd / total,
        region.hyd.area,
    )
    log.info(
        "    %-34s %7.0f m  %5.1f%%   %8.0f m2",
        "HyD silent: rails cast to kerb lines",
        sum(region.silent_m.values()),
        100.0 * sum(region.silent_m.values()) / total,
        region.strip.area,
    )
    for sides, label in (
        (2, "a kerb on both sides"),
        (1, "on one side"),
        (0, "on neither (width_m)"),
    ):
        log.info(
            "      %-32s %7.0f m  %5.1f%%",
            label,
            region.silent_m[sides],
            100.0 * region.silent_m[sides] / total,
        )
    log.info("    stations refused under the hard minimum span: %d", region.stations_refused)
    holes = unary_union(
        [Polygon(ring) for part in shapely.get_parts(region.hyd) for ring in part.interiors]
    )
    log.info(
        "    HyD holes kept: %.0f m2, with %.0f m of centreline standing in one",
        holes.area if not holes.is_empty else 0.0,
        _length_in(own, holes),
    )

    # Owned, and owned-but-unreachable.
    by_id = {line.id: line for line in own}
    owned_area = orphan_area = 0.0
    orphan_edges = 0
    for edge_id, shape in owned.items():
        owned_area += shape.area
        loose = [
            part
            for part in shapely.get_parts(shape)
            if part.geom_type == "Polygon" and not part.intersects(by_id[edge_id].line)
        ]
        orphan_area += sum(part.area for part in loose)
        orphan_edges += bool(loose)
    log.info("")
    log.info(
        "  territories: %.0f m2 owned of R's %.0f m2 (the rest is the neighbour's); "
        "orphan %.0f m2 (%.1f%%) on %d edges",
        owned_area,
        region.whole.area,
        orphan_area,
        100.0 * orphan_area / owned_area if owned_area else 0.0,
        orphan_edges,
    )

    # Against the ray survey, where a width exists.
    span: dict[int, list[Section]] = {}
    for section in sections:
        span.setdefault(section.edge, []).append(section)
    log.info("")
    log.info("  territory span against the RAY survey's width, mid-block kerb|kerb stations:")
    for label, keep in (("all", lambda line: True), ("<60 m", lambda line: line.length < 60.0)):
        errors = []
        for line in own:
            if line.width_source not in RAY_SOURCES or not keep(line):
                continue
            spans = [
                s.span_m
                for s in span.get(line.id, ())
                if s.near_m >= JUNCTION_M and s.left_end == s.right_end == "kerb"
            ]
            if len(spans) >= 2:
                errors.append(float(np.median(spans)) - line.width_m)
        log.info("    %-6s %s", label, _percentiles(np.asarray(errors)))

    # How a cross-section ends — `Q129`'s table. Twice, because a station inside
    # the junction guard ends in a share by geometry: the side street's territory
    # is what it faces. The mid-block table is the one a width survey could use,
    # and its `stations` column against the first's is the population it cannot.
    groups = {"ray": RAY_SOURCES, "hyd_strip": ("hyd_strip",), "authored": ("authored",)}
    columns = ("kerb|kerb", "kerb|share", "share|share", "open")
    for title, keep in (
        ("every station", lambda s: True),
        (f"mid-block only (>= {JUNCTION_M:.0f} m from a node)", lambda s: s.near_m >= JUNCTION_M),
    ):
        log.info("")
        log.info("  how a cross-section ENDS, %s, by width_source:", title)
        log.info("    %-10s %8s  %9s  %10s  %11s  %6s", "", "stations", *columns)
        for label, sources in groups.items():
            pairs: Counter[str] = Counter()
            for line in own:
                if line.width_source not in sources:
                    continue
                for s in span.get(line.id, ()):
                    if keep(s):
                        ends = sorted((s.left_end, s.right_end))
                        pairs["open" if "open" in ends else "|".join(ends)] += 1
            count = sum(pairs.values())
            if count:
                log.info(
                    "    %-10s %8d  %8.1f%%  %9.1f%%  %10.1f%%  %5.1f%%",
                    label,
                    count,
                    *(100.0 * pairs[k] / count for k in columns),
                )


def against_stage(path: Path, owned: dict[int, BaseGeometry]) -> None:
    """`|stage - tool|`, per owned edge, on the one quantity both publish: area.

    The stage measures at published vertices and this tool at 4 m stations, so
    the extents are not comparable row for row; a territory's area is, and a
    partition that handed asphalt to a different owner moves it on both edges.
    Read as plain JSON and not through `pipeline.region`: a grader that imports
    the stage's reader is graded by it.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    areas = {}
    for row in document["territories"]:
        if not row["foreign"]:
            areas[int(row["edge"])] = sum(
                Polygon(ring["outer"], ring["holes"]).area for ring in row["rings"]
            )
    both = sorted(set(areas) & set(owned))
    delta = np.abs(np.array([areas[key] - owned[key].area for key in both]))
    log.info("")
    log.info(
        "  |stage - tool| territory area, %d edges both publish (%d stage-only, %d tool-only): "
        "p50 %.3f  p90 %.3f  max %.3f m2; total %.1f against %.1f m2",
        len(both),
        len(set(areas) - set(owned)),
        len(set(owned) - set(areas)),
        *np.percentile(delta, (50, 90)),
        delta.max(),
        sum(areas.values()),
        sum(shape.area for shape in owned.values()),
    )


def write_svg(
    path: Path,
    region: Region,
    owned: dict[int, BaseGeometry],
    lines: list[Centreline],
    kerbs: list[LineString],
    window,
) -> None:
    """A plan of R coloured by source, with territory boundaries and centrelines."""
    low_x, low_z, high_x, high_z = window or region.whole.bounds
    scale = 2.0

    def ring_path(shape: BaseGeometry) -> str:
        out = []
        for part in shapely.get_parts(shape):
            if part.geom_type != "Polygon":
                continue
            for ring in (part.exterior, *part.interiors):
                xy = (np.asarray(ring.coords) - (low_x, low_z)) * scale
                out.append("M" + " L".join(f"{x:.1f},{z:.1f}" for x, z in xy) + "Z")
        return " ".join(out)

    box = shapely.box(low_x, low_z, high_x, high_z)
    body = []
    for shape, colour in ((region.hyd, "#555"), (region.strip, "#2a7")):
        body.append(
            f'<path d="{ring_path(shape.intersection(box))}" fill="{colour}" fill-rule="evenodd"/>'
        )
    for shape in owned.values():
        clipped = shape.intersection(box)
        if not clipped.is_empty:
            body.append(
                f'<path d="{ring_path(clipped)}" fill="none" stroke="#fd0" stroke-width="0.4"/>'
            )
    for kerb in kerbs:
        if kerb.intersects(box):
            xy = (np.asarray(kerb.coords) - (low_x, low_z)) * scale
            points = " ".join(f"{x:.1f},{z:.1f}" for x, z in xy)
            body.append(
                f'<polyline points="{points}" fill="none" stroke="#f5a" stroke-width="0.5"/>'
            )
    for line in lines:
        if line.line.intersects(box):
            xy = (line.plan - (low_x, low_z)) * scale
            points = " ".join(f"{x:.1f},{z:.1f}" for x, z in xy)
            colour = "#09f" if line.foreign else "#fff"
            body.append(
                f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="0.6"/>'
            )
    width, height = (high_x - low_x) * scale, (high_z - low_z) * scale
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}"><rect width="100%" height="100%" fill="#111"/>'
        + "".join(body)
        + "</svg>",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument("--level", type=int, default=0, help="elevation level; the plan is level 0")
    parser.add_argument("--sample-m", type=float, default=1.0, help="Voronoi sample pitch")
    parser.add_argument(
        "--max-ray-m",
        type=float,
        default=16.5,
        # `width_bounds.max_m`: a side further than a whole TPDM carriageway
        # from its centreline is `open`, as the flood's reach had it.
        help="how far a cross-section runs before its side is called open",
    )
    parser.add_argument(
        "--rail-m", type=float, default=2.0, help="station pitch of the rails where HyD is silent"
    )
    parser.add_argument(
        "--seam-m",
        type=float,
        help="close gaps between HyD polygons under twice this; default carriageway_region.seam_m",
    )
    parser.add_argument("--svg", type=Path, help="write a plan here")
    parser.add_argument(
        "--window", type=float, nargs=4, metavar=("X0", "Z0", "X1", "Z1"), help="clip the plan"
    )
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    out_dir = city.out_dir(args.region, args.out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, args.region)
    lines = centrelines(graph, args.level)
    high_x, high_z = city.region_high(args.region)
    clip = shapely.box(0.0, 0.0, high_x, high_z)
    clock = time.perf_counter()
    polygons, kerbs = read_publishers(city, args.region, args.sources_root)
    read_s = time.perf_counter() - clock
    region = build_region(
        polygons,
        kerbs,
        lines,
        clip=clip,
        spacing_m=args.rail_m,
        max_m=args.max_ray_m,
        min_span_m=city.carriageway_survey.width_bounds.hard_min_m,
        seam_m=(
            args.seam_m
            if args.seam_m is not None
            else (city.carriageway_region.seam_m if city.carriageway_region else 0.0)
        ),
        island_m=(
            (city.carriageway_region.rail_opening_m, city.roads.lane_width_m)
            if city.carriageway_region
            else None
        ),
    )
    region_s = time.perf_counter() - clock - read_s
    owned = territories(region, lines, args.sample_m)
    owned_s = time.perf_counter() - clock - read_s - region_s
    sections = cross_sections(region, owned, lines, max_m=args.max_ray_m)
    log.info(
        "%s / %s level %d: %d HyD polygons, %d kerb lines, %d centrelines (%d foreign); "
        "sample %.2f m, open past %.1f m  [read %.1f s, R %.1f s, territories %.1f s, "
        "sections %.1f s]",
        city.id,
        args.region,
        args.level,
        len(polygons),
        len(kerbs),
        len(lines),
        sum(line.foreign for line in lines),
        args.sample_m,
        args.max_ray_m,
        read_s,
        region_s,
        owned_s,
        time.perf_counter() - clock - read_s - region_s - owned_s,
    )
    report(region, owned, lines, sections)
    past = sum(line.line.difference(clip).length for line in lines if not line.foreign)
    log.info("")
    log.info("  owned centreline past the region's own rectangle, which R is cut to: %.0f m", past)
    stage = out_dir / "carriageway_region.json"
    if stage.exists():
        against_stage(stage, owned)
    if args.svg:
        write_svg(args.svg, region, owned, lines, kerbs, args.window)
        log.info("")
        log.info("  plan written to %s", args.svg)
    log.info("")
    log.info(
        "  This grades and does not gate. The span agreement is partly built in — the ray "
        "survey's third publisher is R's own boundary — so the finding is the end-pair table."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
