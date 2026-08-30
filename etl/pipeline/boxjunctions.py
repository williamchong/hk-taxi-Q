"""Published yellow box junctions, drawn as their own mesh (`P3-18`).

`Q53` held box junctions with "what it needs is a list of which junctions have
one, and nothing publishes that". `Q56` found the list on 2026-08-20 —
`DTAD_YL_BOX_POLY` publishes each box as a surveyed polygon — and `Q59` recorded
this stage as the obvious follow-on once `P3-15` existed. This is that work.

The shape of the stage is `arrows.py`'s, and so is the argument for a separate
mesh: the junction cap is a convex hull that overlaps its arms by 6,051 m², and
"anything drawn *on* a cap re-exposes it immediately" (`Q53`). Separate
geometry lifted above both cap and arm is immune, because it does not care what
is underneath.

Three decisions differ from arrows, and each is recorded where it bites:

- **The polygon is drawn at its surveyed position, never registered to the
  ribbon.** Arrows read their position as a fraction across the carriageway
  because a point feature has no extent of its own; a box *is* an extent, and
  scaling it to the 1.6x-widened ribbon would be invented geometry in `Q54`'s
  sense. The honest cost is underfill at the arm mouths, where the drawn
  carriageway is wider than the real one the box was surveyed on.
- **Heights come from a per-vertex query of the drawn road, not a host edge's
  polyline.** The second snap arrows refused was a second opinion about one
  host; a box spans several arms and has no host, so the query *is* the primary
  join. 🔴 **`surface.DrawnSurface` since `Q92`, where this took a
  distance-weighted blend of centreline heights.** The blend was a *model* of
  the junction and the junction is a published convex-hull cap fanned from its
  own centroid; off the centreline the two diverge by up to 0.218 m against a
  `lift_m` of 0.012, and **23.2% of this mesh shipped underneath the road it is
  painted on**. `height_spread_m` publishes what the join moved and
  `vertices_over_cap` publishes that the caps are being read at all.
- **The hatch direction is derived where the publisher is silent.** `ANGLE1` /
  `ANGLE2` are published on 4 of the region's 20 boxes and used where present;
  elsewhere the direction is the box's own min-area-rectangle long axis
  + 45 deg. `hatch_angle_residual_deg` grades the derivation against every
  published pair on every run — the one number that can see it drift.

⚠️ **Nothing here invents a box.** A region publishes 20 boxes against 393
junction nodes; a fallback keyed on topology would be wrong nineteen times in
twenty, and it would render perfectly.
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.arrows import ArrowReport
from pipeline.config import BoxJunctions, CityConfig, GameTransform, load_config
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.mesh import select_triangles
from pipeline.polyline import Segments, game_heading_deg
from pipeline.roads import JUNCTION, ROADGRAPH_NAME, read_graph
from pipeline.surface import (
    SURFACE_MANIFEST_NAME,
    SURFACE_MANIFEST_SCHEMA,
    DrawnSurface,
    downward_facing,
)

log = logging.getLogger(__name__)

BOXJUNCTIONS_NAME = "boxjunctions.glb"
BOXJUNCTIONS_MANIFEST_NAME = "boxjunctions.json"
BOXJUNCTIONS_MANIFEST_SCHEMA = 1

# ⚠️ **No `-col` suffix.** Paint is not a collider — `ARROWS_MESH_NAME`'s
# reasoning, unchanged: a 12 mm step of paint modelled as collision geometry is
# a kerb across every junction in the city.
BOXJUNCTIONS_MESH_NAME = "boxjunctions"

# glTF material name, the contract channel `ARROWS_MATERIAL` uses:
# `tools/generated_scene_import.gd` maps this string onto
# `tuning/boxjunctions.tres` and nothing else.
BOXJUNCTIONS_MATERIAL = "boxjunctions"

# Below this, twice a triangle's area means it has collapsed. The bar
# `surface.py`, `tramway.py` and `arrows.py` all set, for the same reason.
_MIN_TWICE_AREA_M2 = 1e-6

# What `ELEVATION` says when a feature is at grade — the same column, on the
# same geodatabase, that `arrows.py` reads, and the same reading: the column is
# a structure identifier (`A01`, `A03`) and null is the ground. 19 of the
# region's 20 boxes are null and one is the empty string.
#
# ⚠️ Not config, for `arrows._AT_GRADE`'s stated reason: it is the source's own
# encoding of "no structure", not a threshold anyone may tune.
_AT_GRADE = ("", "none", "null", "<na>")

# Past this ratio of offset length to border width, a mitre at a sharp vertex
# is clamped rather than allowed to spike. The join is between two 300 mm
# bands, so the clamp changes nothing a frame shows; what it prevents is a
# single reflex vertex throwing a metre of paint outside the surveyed ring.
_MITRE_LIMIT = 4.0


@dataclass
class BoxJunctionReport:
    """What the stage read, matched and drew.

    ⚠️ **The counters are what can see this stage fail** — `Q58`'s lesson,
    inherited via `arrows.py`: a box on the wrong junction is a perfectly drawn
    box, a hatch rotated by a wrong convention is a perfectly drawn hatch, and
    an inverted mesh renders as *nothing*.

    The partitions:

        boxes == not_a_yellow_box + on_structure + empty_geometry + candidates
        candidates == drawn + too_far
    """

    boxes: int = 0
    not_a_yellow_box: int = 0
    on_structure: int = 0
    empty_geometry: int = 0
    candidates: int = 0

    drawn: int = 0
    too_far: int = 0

    # Of the drawn boxes, how many took their hatch direction from the
    # publisher's own `ANGLE1` and how many from the derivation.
    hatch_angle_published: int = 0
    hatch_angle_derived: int = 0
    # Derived direction against the published one, folded modulo 90 — an
    # orthogonal two-direction hatch field is invariant under 90 deg, and every
    # published pair is 90 deg apart. Recorded for every candidate that
    # publishes a pair, whatever is then drawn: this is the only grader the
    # derivation has, and `config.BoxJunctions` quotes its numbers.
    hatch_angle_residual_deg: list[float] = field(default_factory=list)

    # Centroid distance to the nearest level-0 centreline, recorded **before**
    # the `too_far` refusal — `n` exceeding `drawn` is how a reader tells the
    # distribution can still see past its own filter (`Q58`).
    nearest_edge_m: list[float] = field(default_factory=list)
    # Centroid distance to the nearest junction *node*. The registration
    # finding: a box junction far from every junction the graph knows has
    # matched a crossing this build does not drive, and no frame shows that.
    nearest_node_m: list[float] = field(default_factory=list)
    # Per drawn box, max minus min of its vertices' snapped road heights. What
    # the per-vertex join actually moved, and the number that would say if two
    # arms ever disagreed under one box.
    height_spread_m: list[float] = field(default_factory=list)

    # 🔴 **The tripwire on the cap join (`Q92`).** `vertices_over_cap` must be a
    # large share of `vertices_drawn` — a box junction is at a junction, so most
    # of its paint is on cap tarmac — and it goes to **zero** the moment
    # `roadsurface.json` stops publishing `caps` or publishes them at the wrong
    # level, which is the one way this fix reverts with every partition still
    # closing. `over_cap_rise_m` is how far the cap stands above the centreline
    # the old model would have used, so it also says whether the caps matter
    # here rather than merely being read.
    vertices_drawn: int = 0
    vertices_over_cap: int = 0
    over_cap_rise_m: list[float] = field(default_factory=list)

    ring_vertices: list[float] = field(default_factory=list)
    area_m2: list[float] = field(default_factory=list)
    total_area_m2: float = 0.0

    # Border segments whose inward offset crossed itself at a tight reflex
    # vertex and were dropped rather than guessed at. Each leaves a small gap
    # in the boundary line; the count is the only sign of it.
    degenerate_border_segments: int = 0
    # Triangles dropped for being thinner than the engine's import lattice,
    # and the lattice pitch they were judged against. See `_import_quantum_m`:
    # Godot quantises this mesh's positions to `span / 65535` on import —
    # ~17 mm here — and a sliver under that pitch can come back with its
    # winding flipped, which `cull_back` then culls. Measured: 217 of the
    # first build's triangles did exactly that, caught by
    # `verify_boxjunctions.gd` while this stage's own `inverted` read 0.
    slivers_dropped: int = 0
    import_quantum_m: float = 0.0
    # Inner rings encountered. The region publishes none, so a hole appearing
    # is a schema change to go and look at — the outer ring still draws, and
    # the hatch then covers ground the publisher cut out.
    holes_refused: int = 0

    # Triangles wound so they face the ground. ⚠️ Must be 0 — `cull_back` drew
    # none of the first tramway, 5,111 triangles of 5,112.
    inverted: int = 0
    inverted_area_m2: float = 0.0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)

    # One distribution as the manifest publishes it: p90/p99/max, the tail
    # rather than the middle, for `ArrowReport.measured`'s stated reason —
    # every distribution here is a residual, and the tail is the finding.
    measured = staticmethod(ArrowReport.measured)


@dataclass(frozen=True)
class Box:
    """One published box junction, in game plan space."""

    # The outer ring, `(n, 2)` as `(x, z)`, open (no repeated closing vertex).
    ring: np.ndarray
    # The published hatch direction as a game heading, or None where the
    # publisher left `ANGLE1` null — 16 of the region's 20.
    hatch_deg: float | None


def read_boxes(
    city: CityConfig,
    spec: BoxJunctions,
    region_id: str,
    transform: GameTransform,
    report: BoxJunctionReport,
    *,
    sources_root: Path | None,
) -> list[Box]:
    """Every published box junction in the region, in game plan space.

    Everything refused here is refused on what the *publisher* says — a type
    outside `box_types`, a feature on a structure, an empty ring — and each
    refusal is counted rather than logged (`Q58`).
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    boxes: list[Box] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = layer.column(spec.layer.field("type"))
        levels = layer.column(spec.layer.field("level"))
        hatch_a = layer.column(spec.layer.field("hatch_a"))
        owners, parts = gdb.polygons(layer)

        for owner, rings in zip(owners, parts, strict=True):
            report.boxes += 1
            if str(types[owner]) not in spec.box_types:
                report.not_a_yellow_box += 1
                continue
            if str(levels[owner]).strip().lower() not in _AT_GRADE:
                # On a flyover deck. `Q13` keeps the elevated network closed to
                # driving, and the nearest level-0 edge to a box on a deck is
                # the street underneath it.
                report.on_structure += 1
                continue
            # Inner rings are holes. Counted, not drawn around: the region
            # publishes none, so a repair for them would be untestable code
            # guarding a shape the source does not contain.
            report.holes_refused += len(rings) - 1
            ring = _open_ring(rings[0])
            if ring is None:
                report.empty_geometry += 1
                continue
            game_x, _, game_z = transform.to_game(ring[:, 0], ring[:, 1])
            report.candidates += 1

            angle = hatch_a[owner]
            hatch_deg: float | None = None
            if angle is not None and math.isfinite(float(angle)):
                # `ANGLE1` is a mathematical angle, converted exactly as
                # `arrows.Symbol.heading_deg` converts `ANGLE` — same
                # geodatabase, same convention, and `hatch_angle_residual_deg`
                # is what holds it: a wrong reading here shows up as a large
                # residual against the derived axis on every published pair.
                hatch_deg = game_heading_deg(float(angle))
            boxes.append(Box(ring=np.column_stack([game_x, game_z]), hatch_deg=hatch_deg))
    return boxes


def _open_ring(ring: np.ndarray) -> np.ndarray | None:
    """The ring without its closing vertex, or None if nothing is left to draw."""
    points = np.asarray(ring, dtype=np.float64)
    if len(points) and np.array_equal(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3 or not np.isfinite(points).all():
        return None
    return points


# --------------------------------------------------------------------------
# Plan geometry
# --------------------------------------------------------------------------
#
# Everything below works in the game's `(x, z)` plan. ⚠️ **Winding: a triangle
# wound counter-clockwise in `(x, z)` faces the ground.** The frame the maths
# is done in is `(x, -z)` wherever orientation matters, so that the classic
# positive-area convention comes out facing `+Y` — and `downward_facing` plus
# `BoxJunctionReport.inverted` are what actually hold that end, as they do for
# arrows.


def _twice_area(ring: np.ndarray) -> float:
    """Shoelace sum in `(x, -z)` — positive when the ring faces `+Y`."""
    shifted = np.roll(ring, -1, axis=0)
    return float(np.sum(shifted[:, 0] * ring[:, 1] - ring[:, 0] * shifted[:, 1]))


def _wound_up(ring: np.ndarray) -> np.ndarray:
    """The ring, wound so its fan and ears face `+Y`.

    Corrected rather than trusted per feature, for `arrows.ccw`'s reason: WKB
    fixes outer-ring orientation only per its own convention, and a reversed
    ring renders as **nothing** under `cull_back` rather than as anything a
    frame would show.
    """
    return ring if _twice_area(ring) > 0.0 else ring[::-1]


def _cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Cross of `o->a` and `o->b` in the `(x, -z)` frame."""
    return float((a[0] - o[0]) * (o[1] - b[1]) - (o[1] - a[1]) * (b[0] - o[0]))


def _ear_clip(ring: np.ndarray) -> list[np.ndarray]:
    """A simple, possibly concave ring as triangles, each wound to face `+Y`.

    O(n²) ear clipping over index lists — the largest ring in the region has
    106 vertices, so nothing faster earns its complexity. The fallback when no
    ear passes the containment test (collinear runs, survey slivers) clips the
    most convex candidate anyway rather than looping forever: the collapsed
    triangle it may emit is exactly what `select_triangles` removes.
    """
    wound = _wound_up(ring)
    active = list(range(len(wound)))
    triangles: list[np.ndarray] = []
    while len(active) > 3:
        clipped = False
        for spot in range(len(active)):
            previous, here, following = (
                active[spot - 1],
                active[spot],
                active[(spot + 1) % len(active)],
            )
            if _cross(wound[previous], wound[here], wound[following]) <= 0.0:
                continue
            if _any_inside(wound, active, previous, here, following):
                continue
            triangles.append(np.array([wound[previous], wound[here], wound[following]]))
            del active[spot]
            clipped = True
            break
        if not clipped:
            spot = max(
                range(len(active)),
                key=lambda i: _cross(
                    wound[active[i - 1]], wound[active[i]], wound[active[(i + 1) % len(active)]]
                ),
            )
            previous, here, following = (
                active[spot - 1],
                active[spot],
                active[(spot + 1) % len(active)],
            )
            triangles.append(np.array([wound[previous], wound[here], wound[following]]))
            del active[spot]
    triangles.append(np.array([wound[active[0]], wound[active[1]], wound[active[2]]]))
    return triangles


def _any_inside(ring: np.ndarray, active: list[int], a: int, b: int, c: int) -> bool:
    corners = (ring[a], ring[b], ring[c])
    for index in active:
        if index in (a, b, c):
            continue
        point = ring[index]
        if all(_cross(corners[side], corners[(side + 1) % 3], point) >= 0.0 for side in range(3)):
            return True
    return False


def _hull(points: np.ndarray) -> np.ndarray:
    """Andrew's monotone chain, as `surface.hull` builds junction caps."""
    unique = np.unique(points, axis=0)
    ordered = unique[np.lexsort((unique[:, 1], unique[:, 0]))]
    if len(ordered) <= 2:
        return ordered

    def sweep(sequence: np.ndarray) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        for point in sequence:
            while len(out) >= 2 and _cross(out[-2], out[-1], point) <= 0.0:
                out.pop()
            out.append(point)
        return out

    lower = sweep(ordered)
    upper = sweep(ordered[::-1])
    return np.asarray(lower[:-1] + upper[:-1])


def long_axis_deg(ring: np.ndarray) -> float:
    """Game heading of the ring's minimum-area rectangle's long axis, in [0, 180).

    Rotating calipers over the convex hull: the minimum-area rectangle shares a
    side with some hull edge, so trying each edge direction is exact rather
    than a sampling of headings.
    """
    hull = _hull(ring)
    edges = np.diff(np.vstack([hull, hull[:1]]), axis=0)
    best: tuple[float, float, float] | None = None
    for edge_x, edge_z in edges:
        length = math.hypot(edge_x, edge_z)
        if length < 1e-9:
            continue
        unit_x, unit_z = edge_x / length, edge_z / length
        along = ring[:, 0] * unit_x + ring[:, 1] * unit_z
        across = -ring[:, 0] * unit_z + ring[:, 1] * unit_x
        width = float(along.max() - along.min())
        height = float(across.max() - across.min())
        area = width * height
        if best is None or area < best[0]:
            if width >= height:
                axis_x, axis_z = unit_x, unit_z
            else:
                axis_x, axis_z = -unit_z, unit_x
            best = (area, axis_x, axis_z)
    _, axis_x, axis_z = best  # type: ignore[misc]  # a valid ring always sets it
    return math.degrees(math.atan2(axis_x, -axis_z)) % 180.0


def _clip_half_plane(polygon: np.ndarray, normal: np.ndarray, bound: float) -> np.ndarray:
    """Sutherland-Hodgman against `dot(p, normal) <= bound`, convex in, convex out."""
    if len(polygon) == 0:
        return polygon
    distances = polygon @ normal - bound
    kept: list[np.ndarray] = []
    for index in range(len(polygon)):
        following = (index + 1) % len(polygon)
        here_in, next_in = distances[index] <= 0.0, distances[following] <= 0.0
        if here_in:
            kept.append(polygon[index])
        if here_in != next_in:
            span = distances[index] - distances[following]
            t = distances[index] / span if span != 0.0 else 0.0
            kept.append(polygon[index] + t * (polygon[following] - polygon[index]))
    return np.asarray(kept) if len(kept) >= 3 else np.empty((0, 2))


def _import_quantum_m(boxes: list[Box]) -> float:
    """The plan pitch Godot's importer will quantise this mesh to.

    ⚠️ **The engine USED TO re-quantise what this stage ships, and the first
    build measured it.** The scene importer compressed vertex positions to a
    16-bit lattice over the mesh's own AABB, which for a region-spanning mesh is
    `span / 65535` — about **17 mm** for Wan Chai.

    ✅ **`Q82` turned `meshes/force_disable_compression` on project-wide
    (2026-08-27), so that lattice no longer exists at import**, and this whole
    paragraph describes a hazard that is switched off. The machinery below is
    kept anyway and deliberately: it is one `.import` setting between here and
    the lattice returning, `check.sh`'s `settings` step is the only thing holding
    it, and a stage that stops refusing sub-quantum slivers cannot be made to
    start again by a config edit. ⚠️ **What it costs is a second city**: the
    build-stopping `ValueError` in `roadmarks.py` is sized against this region's
    17 mm, and at a 6.2 km extent it fires for a hazard that is now off. Read it
    as a bound on drawn thinness rather than as an import constraint.

    A clip fragment thinner than that pitch could come back from the import with
    its winding flipped: 217 of the first build's 12,181 triangles
    did, read as up-facing by this stage's own `inverted` counter and refused
    by `verify_boxjunctions.gd`'s engine-side check — the two counters exist
    separately for exactly this (`Q59`).

    `roads.glb`, `tram.glb` and `arrows.glb` survived the same lattice not by
    disabling it but by never shipping a sub-quantum feature — a rail is 3.5
    quanta wide — so this stage holds itself to the same bar. ⚠️ **`Q82` did
    then ask the importer for the exception**, for a different reason: a lamp
    post's 0.06 m bracket arm and a sign pole's 0.032 m are *below* the quantum,
    and unlike a box junction they cannot be thickened to clear it.

    Derived from the rings' own extent rather than authored, because the pitch
    is a property of the region's size, not a number anyone should tune.
    """
    if not boxes:
        return 0.0
    points = np.vstack([box.ring for box in boxes])
    spans = points.max(axis=0) - points.min(axis=0)
    return float(spans.max()) / 65535.0


def _frame(heading_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Along and across in game plan space for a heading clockwise from north.

    `arrows._frame`'s expression, restated here rather than imported because
    arrows' is private and one line — along is `(sin h, -cos h)`, across is
    `(cos h, sin h)`.
    """
    heading = math.radians(heading_deg)
    return (
        np.array([math.sin(heading), -math.cos(heading)]),
        np.array([math.cos(heading), math.sin(heading)]),
    )


def hatch_polygons(ring: np.ndarray, axis_deg: float, spec: BoxJunctions) -> list[np.ndarray]:
    """The cross-hatch clipped to the ring, as convex polygons facing `+Y`.

    Two stripe fields 90 deg apart, each anchored on the ring's own centroid so
    the pattern is stable under a re-survey that only re-orders vertices. Each
    ear triangle is clipped against each stripe's two half-planes — convex
    against convex, so every output is convex — and the pieces are then split
    at `station_m` along the stripe so their vertices are dense enough to take
    the road's height under them.

    ⚠️ The stripes deliberately run to the ring's own edge rather than stopping
    at the boundary line's inner rim; the border is lifted `border_lift_m`
    clear, which is what makes that overlap invisible — see `config.py`.
    """
    ears = _ear_clip(ring)
    centroid = ring.mean(axis=0)
    half = 0.5 * spec.hatch_width_m
    pieces: list[np.ndarray] = []
    for direction in (axis_deg, axis_deg + 90.0):
        along, across = _frame(direction)
        anchor = float(centroid @ across)
        for ear in ears:
            offsets = ear @ across - anchor
            first = math.ceil((float(offsets.min()) - half) / spec.hatch_spacing_m)
            last = math.floor((float(offsets.max()) + half) / spec.hatch_spacing_m)
            for stripe in range(first, last + 1):
                centre = anchor + stripe * spec.hatch_spacing_m
                piece = _clip_half_plane(ear, across, centre + half)
                piece = _clip_half_plane(piece, -across, -(centre - half))
                if len(piece):
                    pieces.extend(_stations(piece, along, spec.station_m))
    return pieces


def _stations(polygon: np.ndarray, along: np.ndarray, station_m: float) -> list[np.ndarray]:
    """The convex polygon cut at `station_m` intervals along `along`."""
    reach = polygon @ along
    first = math.floor(float(reach.min()) / station_m) + 1
    last = math.ceil(float(reach.max()) / station_m) - 1
    if first > last:
        return [polygon]
    pieces: list[np.ndarray] = []
    rest = polygon
    for cut in range(first, last + 1):
        piece = _clip_half_plane(rest, along, cut * station_m)
        if len(piece):
            pieces.append(piece)
        rest = _clip_half_plane(rest, -along, -cut * station_m)
        if not len(rest):
            break
    if len(rest):
        pieces.append(rest)
    return pieces


def border_polygons(
    ring: np.ndarray, spec: BoxJunctions, report: BoxJunctionReport
) -> list[np.ndarray]:
    """The boundary line as inward quads along each ring edge, facing `+Y`.

    Mitred at each vertex, with the mitre length clamped at `_MITRE_LIMIT`
    times the border width. A segment whose inner edge comes out running
    against its outer edge has been crossed by the offset at a tight reflex
    vertex; it is dropped and counted, never repaired — the repair would be
    invented geometry on a ring the publisher drew.
    """
    wound = _wound_up(ring)
    count = len(wound)
    edges = np.roll(wound, -1, axis=0) - wound
    lengths = np.hypot(edges[:, 0], edges[:, 1])
    lengths = np.where(lengths > 0.0, lengths, 1.0)
    units = edges / lengths[:, None]
    # Inward normal of each edge for a `+Y`-wound ring: rotate the edge
    # direction by 90 deg as `(z, -x)` — asserted against a square in tests
    # rather than trusted from this comment.
    normals = np.column_stack([units[:, 1], -units[:, 0]])

    inner = np.empty_like(wound)
    for index in range(count):
        before = normals[index - 1]
        after = normals[index]
        bisector = before + after
        norm = math.hypot(bisector[0], bisector[1])
        if norm < 1e-9:
            # A hairpin: the two edges double back. Fall back to the following
            # edge's own normal; the segment test below decides what survives.
            offset = after * spec.border_width_m
        else:
            bisector = bisector / norm
            cos_half = max(float(bisector @ after), 1.0 / _MITRE_LIMIT)
            offset = bisector * (spec.border_width_m / cos_half)
        inner[index] = wound[index] + offset

    quads: list[np.ndarray] = []
    for index in range(count):
        following = (index + 1) % count
        inner_edge = inner[following] - inner[index]
        if float(inner_edge @ units[index]) <= 0.0:
            report.degenerate_border_segments += 1
            continue
        quad = np.array([wound[index], wound[following], inner[following], inner[index]])
        along = units[index]
        quads.extend(_stations(quad, along, spec.station_m))
    return quads


class _Builder:
    """Accumulates flat convex polygons into one mesh — `arrows._Builder`,
    with the material this stage dispatches on.

    ⚠️ **Position and normal only — no `COLOR_0`, no `TEXCOORD_0`, no
    `TEXCOORD_1`** — for the reason arrows records: the colour is authored in
    `game/tuning/boxjunctions.tres` (`Q53` kept paint out of `materials:`),
    and a channel earns its place when something reads it.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def polygon(self, plan: np.ndarray, height: np.ndarray) -> None:
        span = len(plan)
        if span < 3:
            return
        base = self._count
        fan = np.arange(1, span - 1)
        self._triangles.append(
            np.column_stack([np.zeros(len(fan), dtype=np.int64), fan, fan + 1]) + base
        )
        self._positions.append(np.column_stack([plan[:, 0], height, plan[:, 1]]))
        self._count += span

    def build(
        self,
        name: str,
        thin_bar_m: float = 0.0,
        report: BoxJunctionReport | None = None,
    ) -> MeshData | None:
        """The mesh, minus collapsed triangles and sub-lattice slivers.

        ⚠️ The sliver bar is judged **per triangle, not per polygon** — a
        convex quad wider than the bar can still fan into one sound triangle
        and one needle along its long diagonal, and the needle is what the
        import lattice flips. Judged per polygon first, 37 of them survived to
        fail the engine-side check; per triangle, none do.
        """
        if not self._triangles:
            return None
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.tile(np.array([0.0, 1.0, 0.0], dtype=np.float32), (self._count, 1)),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            material=BOXJUNCTIONS_MATERIAL,
        )
        cross = mesh.triangle_cross()
        twice_area = np.linalg.norm(cross, axis=1)
        corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
        sides = np.roll(corners, -1, axis=1) - corners
        longest = np.linalg.norm(sides, axis=2).max(axis=1)
        # Plan twice-area over the longest plan edge — twice the width, for a
        # rectangle — against the lattice bar `_import_quantum_m` explains.
        thin = np.abs(cross[:, 1]) < thin_bar_m * np.where(longest > 0.0, longest, 1.0)
        if report is not None:
            report.slivers_dropped = int(thin.sum())
        return select_triangles(mesh, (twice_area > _MIN_TWICE_AREA_M2) & ~thin)


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> BoxJunctionReport:
    """Read the region's published box junctions and write its `boxjunctions.glb`."""
    spec = city.boxjunctions
    report = BoxJunctionReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the same shape `tramway` and `arrows` take: a city
        # whose estate publishes no box polygons ships none rather than
        # inferring them.
        log.info("city '%s' declares no boxjunctions block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    boxes = read_boxes(city, spec, region_id, transform, report, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, the restriction every snap in the pipeline makes (`Q15`):
    # a box under a flyover must take its heights from the street it is painted
    # on, not the deck above it.
    segments = Segments.of([edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0])
    # The road as `surface.py` actually drew it — the ribbon heights above plus
    # the junction caps it publishes (`Q92`). Same level restriction, applied to
    # the caps as well: a cap on the deck overhead is not what a street marking
    # is painted on.
    drawn = DrawnSurface.of(
        segments,
        read_document(
            out_dir / SURFACE_MANIFEST_NAME,
            SURFACE_MANIFEST_SCHEMA,
            f"python -m pipeline.surface --region {region_id}",
        ),
        level=0,
    )
    junctions = np.asarray(
        [node["pos"] for node in graph["nodes"] if node["kind"] == JUNCTION],
        dtype=np.float64,
    )

    builder = _Builder()
    # The pitch the engine will re-quantise this mesh to, and the thinness bar
    # that keeps every shipped fragment at least two lattice cells wide — see
    # `_import_quantum_m` for the 217 flipped triangles that priced it.
    report.import_quantum_m = round(_import_quantum_m(boxes), 6)
    thinness_bar_m = 2.0 * report.import_quantum_m
    for box in boxes:
        centroid = box.ring.mean(axis=0)
        x, z = float(centroid[0]), float(centroid[1])
        snap = segments.nearest(x, z)
        # Recorded before the refusal — `n` past `drawn` is the proof the
        # distribution can read outside its own filter (`Q58`).
        report.nearest_edge_m.append(snap.distance_m)
        if len(junctions):
            report.nearest_node_m.append(
                float(np.min(np.hypot(junctions[:, 0] - x, junctions[:, 2] - z)))
            )
        derived_deg = (long_axis_deg(box.ring) + 45.0) % 180.0
        if box.hatch_deg is not None:
            gap = abs(derived_deg - box.hatch_deg) % 90.0
            report.hatch_angle_residual_deg.append(min(gap, 90.0 - gap))
        if snap.distance_m > spec.max_offset_m:
            report.too_far += 1
            continue

        if box.hatch_deg is not None:
            report.hatch_angle_published += 1
            axis_deg = box.hatch_deg
        else:
            report.hatch_angle_derived += 1
            axis_deg = derived_deg

        heights: list[float] = []
        for piece in hatch_polygons(box.ring, axis_deg, spec):
            heights.extend(_place(builder, drawn, piece, spec.lift_m, report))
        for quad in border_polygons(box.ring, spec, report):
            heights.extend(_place(builder, drawn, quad, spec.lift_m + spec.border_lift_m, report))

        report.drawn += 1
        report.ring_vertices.append(float(len(box.ring)))
        area = 0.5 * abs(_twice_area(box.ring))
        report.area_m2.append(area)
        report.total_area_m2 += area
        if heights:
            report.height_spread_m.append(max(heights) - min(heights))

    mesh = builder.build(BOXJUNCTIONS_MESH_NAME, thinness_bar_m, report)
    if mesh is not None:
        report.inverted, report.inverted_area_m2 = downward_facing(mesh)
        report.triangles = mesh.triangle_count
        report.vertices = len(mesh.positions)
        low, high = mesh.aabb()
        report.aabb = [list(low), list(high)]
        report.bytes = write_glb(out_dir / BOXJUNCTIONS_NAME, [mesh])

    _write_manifest(out_dir, city, region_id, report)
    return report


def _place(
    builder: _Builder,
    drawn: DrawnSurface,
    polygon: np.ndarray,
    lift_m: float,
    report: BoxJunctionReport,
) -> list[float]:
    """One polygon onto the road under it, each vertex at its own drawn height.

    Returns the road heights so the caller can publish their spread.
    ⚠️ The join is per vertex on purpose — the opposite of `arrows._draw`'s
    host-edge interpolation, for the reason the module docstring gives: a box
    spans several arms and has no host, so the query *is* the primary join
    rather than a second opinion about one.

    🔴 **`DrawnSurface.height_at` since `Q92`, where this took
    `blended_height`.** The blend was a model of the road; this is the road.
    Measured on the shipped bundle before the change, **2,161 of 9,315 box
    triangles (23.2%) stood below the surface they were painted on**, p90 0.126 m
    against a `lift_m` of 0.012 — the blend follows the arms' centrelines down
    while the junction cap stays on its own fan, and the paint sinks into the
    difference. Nothing in this stage could see it: the mesh is complete in plan
    and wrong in Y, which is the projection `Q91` closed on.

    🔴 **The counters recorded here are the ones that can see the caps stop being
    read** — see `BoxJunctionReport`. There is deliberately **no** counter for
    "placed height minus drawn height": that is `lift_m` by construction, no
    reachable configuration makes it anything else, and it is `Q72`'s tautology
    exactly.
    """
    heights: list[float] = []
    for px, pz in polygon:
        drawn_here = drawn.sample(float(px), float(pz))
        heights.append(drawn_here.height_m)
        report.vertices_drawn += 1
        if drawn_here.cap_m is not None:
            report.vertices_over_cap += 1
            report.over_cap_rise_m.append(drawn_here.cap_m - drawn_here.ribbon_m)
    builder.polygon(polygon, np.asarray(heights) + lift_m)
    return heights


def _write_manifest(
    out_dir: Path, city: CityConfig, region_id: str, report: BoxJunctionReport
) -> int:
    document = {
        "schema_version": BOXJUNCTIONS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what
        # `CITY_SCHEMA` 11 was bumped over.
        "asset": BOXJUNCTIONS_NAME if report.drawn else None,
        # The read, as four disjoint parts of `boxes`.
        "boxes": report.boxes,
        "not_a_yellow_box": report.not_a_yellow_box,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "candidates": report.candidates,
        # The join, as two disjoint parts of `candidates`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        # Where the drawn hatch directions came from, and the only grader the
        # derivation has: derived-versus-published, folded mod 90, over every
        # candidate that publishes a pair — including any the join then
        # refused. `config.py` quotes these numbers; this is what keeps them
        # describing the survey that ships.
        "hatch_angle_published": report.hatch_angle_published,
        "hatch_angle_derived": report.hatch_angle_derived,
        "hatch_angle_residual_deg": report.measured(report.hatch_angle_residual_deg),
        # Recorded before the `too_far` guard, so `n` exceeding `drawn` is the
        # proof it can see past its own filter (`Q58`). What `max_offset_m` is
        # set against.
        "nearest_edge_m": report.measured(report.nearest_edge_m),
        # ⚠️ **The registration finding.** A box junction far from every
        # junction node the graph knows has matched a crossing this build does
        # not drive — a carpark mouth, a private road — and rendering cannot
        # show that. To be gone and looked at, never tuned against.
        "nearest_node_m": report.measured(report.nearest_node_m),
        "height_spread_m": report.measured(report.height_spread_m),
        # 🔴 The tripwire on the cap join (`Q92`) — see `BoxJunctionReport`.
        # Neither is a tautology: both are reachable at zero, and zero is what a
        # stage that has gone back to guessing the road's height reads.
        "vertices_drawn": report.vertices_drawn,
        "vertices_over_cap": report.vertices_over_cap,
        "over_cap_rise_m": report.measured(report.over_cap_rise_m),
        "ring_vertices": report.measured(report.ring_vertices),
        "area_m2": report.measured(report.area_m2),
        "total_area_m2": round(report.total_area_m2, 4),
        "degenerate_border_segments": report.degenerate_border_segments,
        # Fragments thinner than two cells of the engine's import lattice,
        # dropped before they could come back winding-flipped — see
        # `_import_quantum_m` for the measured mechanism. The pitch is
        # published beside the count so the bar is checkable from a shipped
        # artefact rather than a scratch script (`Q37`).
        "slivers_dropped": report.slivers_dropped,
        "import_quantum_m": report.import_quantum_m,
        "holes_refused": report.holes_refused,
        # ⚠️ **Must be 0.** `marking_paint.gdshader` is `cull_back`, so winding
        # decides visibility and the normal attribute does not (`Q58`).
        "inverted": report.inverted,
        "inverted_area_m2": round(report.inverted_area_m2, 4),
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
    }
    return write_document(out_dir / BOXJUNCTIONS_MANIFEST_NAME, document)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


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
        "boxjunctions: %d boxes -> %d drawn (%d too far), %d triangles",
        report.boxes,
        report.drawn,
        report.too_far,
        report.triangles,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
