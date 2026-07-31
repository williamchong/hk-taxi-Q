"""Road graph to a drivable ribbon mesh (`P1-4`).

Reads the `roadgraph.json` that `P1-3` wrote and extrudes every edge into a
carriageway with kerbs, filling each junction with a cap so the surface is
continuous through it. Output is one vertex-coloured GLB for the whole region.

Three measurements off the emitted graph decide the shape of this:

- **Opposed carriageway pairs need no special handling.** Six pairs in Wan Chai
  sit 1.49-6.82 m apart, and at their authored widths five of the six already
  overlap. Applying the playability widening closes the sixth. The gap the
  `P1-3` hand-over worried about does not exist, so there is no pair detection
  here and no merging.
- **A node may not be capped across elevation levels.** All 36 nodes in the
  region where two levels meet step by exactly a deck height — 6 m at a flyover,
  8 m at a tunnel mouth — because `elevation_levels` is a constant offset per
  level and no edge ramps between them. Capping across that would weld a street
  to a tunnel roof with a 60-degree wall. Caps are therefore built per level.
  See `Q13`: the network is topologically connected and geometrically is not.
- **Mitred joints are safe.** The sharpest interior turn in the region is 91.8
  degrees, a mitre scale of 1.44. The limit below is a guard for another city,
  not something this data reaches.

Nothing here reads the road network source. The graph is the input, which is
what lets this stage run in a second without touching the geodatabase.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline.config import CityConfig, RoadSurface, load_city
from pipeline.documents import write_document
from pipeline.gltf import Bounds, MeshData, normalise, write_glb
from pipeline.mesh import select_triangles
from pipeline.roads import ROADGRAPH_NAME, plan_lengths, plan_steps, read_graph

log = logging.getLogger(__name__)

SURFACE_NAME = "roads.glb"
SURFACE_MANIFEST_NAME = "roadsurface.json"
SURFACE_MANIFEST_SCHEMA = 2

# Godot's glTF importer reads node-name suffixes: `-col` gives the mesh a static
# trimesh collider at import time and leaves it visible. Naming it here rather
# than building the shape in GDScript at load makes the collision part of the
# asset, which is what `P1-4` is asked to deliver.
SURFACE_MESH_NAME = "road_surface-col"

# Ceiling on how far a mitred outside corner may be pushed from the centreline,
# as a multiple of the half-width. A degeneracy guard, not a tuning value: it
# only binds past a 151-degree turn, and the sharpest in this region is 92.
_MITRE_LIMIT = 4.0

# Below this, two consecutive polyline vertices are the same point and the
# segment between them has no direction to offset along.
_MIN_SEGMENT_M = 1e-6

# Below this, a triangle has collapsed and is dropped. Compared against *twice*
# the area, which is what the cross product's length gives — a square millimetre
# of road is not road, and a collision shape built from degenerate triangles is
# a collision shape with holes in it.
_MIN_TWICE_AREA_M2 = 1e-6


@dataclass
class SurfaceReport:
    edges: int = 0
    # Drawn half-width per graph edge id, in metres. Recorded rather than
    # recomputed downstream: `_prepare` is the one place the widening is
    # applied, and a second evaluation of `widen_for` is a second thing to keep
    # in step with the config.
    carriageway: dict[int, float] = field(default_factory=dict)
    junctions: int = 0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: Bounds | None = None
    # Ends held back from a node so a cap can fill the middle, and how many of
    # those hit the length ceiling instead of the junction radius. A high clamp
    # count means the trim factor is wide for the region's block size.
    trimmed_ends: int = 0
    clamped_trims: int = 0
    # Nodes where the graph changes elevation level, and the largest vertical
    # step at one. Reported every run because it is the one thing about this
    # output that is not drivable, and it is inherited rather than introduced.
    level_changes: int = 0
    max_level_step_m: float = 0.0
    # Triangles left facing downward, and the area they cover. Tracked rather
    # than assumed away: `boundary` removes all but a handful at the region's
    # sharpest hairpin, and a jump in either number means a ribbon has started
    # folding somewhere new.
    inverted: int = 0
    inverted_area_m2: float = 0.0


# --------------------------------------------------------------------------
# Ribbon geometry
# --------------------------------------------------------------------------


def dedupe(points: np.ndarray) -> np.ndarray:
    """Drop vertices that repeat the previous one in plan.

    A repeated vertex has no direction, so it produces a zero normal and takes
    the whole ribbon with it. Legal in the graph — clipping can land a cut
    exactly on an existing vertex.
    """
    if len(points) < 2:
        return points
    return points[np.concatenate([[True], plan_steps(points) > _MIN_SEGMENT_M])]


def trim(points: np.ndarray, start_m: float, end_m: float) -> np.ndarray:
    """The polyline with `start_m` cut off the front and `end_m` off the back.

    Cut points are interpolated, including in Y, so a trimmed ramp keeps its
    gradient. Returns fewer than two vertices if the trims meet, which the
    caller treats as an edge too short to draw.
    """
    along = plan_lengths(points)
    low, high = start_m, along[-1] - end_m
    if high - low <= _MIN_SEGMENT_M:
        return points[:0]

    inner = points[(along > low) & (along < high)]
    return np.vstack([_at(points, along, low), inner, _at(points, along, high)])


def _at(points: np.ndarray, along: np.ndarray, distance: float) -> np.ndarray:
    """The point a given distance along the polyline, as a (1, 3) row."""
    return np.array([[np.interp(distance, along, points[:, axis]) for axis in range(3)]])


def mitres(points: np.ndarray) -> np.ndarray:
    """Per-vertex offset vector in plan, one half-width to the **left** of travel.

    Interior vertices get the mitre — the intersection of the two neighbouring
    offset lines — so consecutive quads share an edge exactly and the ribbon has
    no notch on the outside of a bend. Its length exceeds one where the road
    turns, by `1 / cos(half the turn)`, which is what makes the joint close.
    """
    direction = normalise(np.diff(points[:, [0, 2]], axis=0))
    # Left of travel, which in a Y-up right-handed frame is `up x forward`: for
    # travel along +X that is -Z. Not a free convention — `TEXCOORD_0` is a lane
    # coordinate measured from the nearside kerb, and Hong Kong drives on the
    # left, so getting this backwards mirrors every asymmetric road marking.
    normal = np.column_stack([direction[:, 1], -direction[:, 0]])

    offsets = np.empty((len(points), 2))
    offsets[0], offsets[-1] = normal[0], normal[-1]
    if len(points) > 2:
        bisector = normal[:-1] + normal[1:]
        length = np.hypot(*bisector.T)
        # A zero bisector is a 180-degree reversal, which has no mitre. Keeping
        # the incoming normal folds the ribbon back on itself rather than
        # sending the corner to infinity.
        reversal = length <= _MIN_SEGMENT_M
        unit = bisector / np.where(reversal, 1.0, length)[:, None]
        bisector = np.where(reversal[:, None], normal[:-1], unit)
        cosine = (bisector * normal[:-1]).sum(axis=1)
        offsets[1:-1] = bisector * (1.0 / np.clip(cosine, 1.0 / _MITRE_LIMIT, 1.0))[:, None]
    return offsets


def boundary(points: np.ndarray, offsets: np.ndarray, across_m: float) -> np.ndarray:
    """One side of the ribbon in plan, stopped where it would run backwards.

    A corner tighter than the road is wide has no offset curve on its inside:
    the naive one crosses over itself, which renders as an inverted sliver and
    leaves a notch in the collider. The region has such corners — a slip road
    off Hung Hing Road loops at a 5 m radius, and the widened carriageway is
    10.2 m across.

    Holding the inner boundary still while the outer sweeps past is what the
    offset of a too-tight corner actually is, and it is the only repair here
    that touches neither the centreline nor the width: capping the width
    instead pinches the carriageway to nothing at 24 places in the region, and
    dropping the offending vertices cuts up to 17 m off that same loop.
    """
    rail = points[:, [0, 2]] + offsets * across_m
    step = np.diff(points[:, [0, 2]], axis=0)
    # Vectorised first because it is almost always clean: 74 of 797 edges have
    # a corner tight enough to need the walk below.
    if not ((np.diff(rail, axis=0) * step).sum(axis=1) <= 0.0).any():
        return rail

    rail = rail.copy()
    for index in range(len(rail) - 1):
        if np.dot(rail[index + 1] - rail[index], step[index]) <= 0.0:
            rail[index + 1] = rail[index]
    return rail


def _lift(plan: np.ndarray, points: np.ndarray, lift_m: float) -> np.ndarray:
    """A plan boundary put back on the ribbon's own heights."""
    return np.column_stack([plan[:, 0], points[:, 1] + lift_m, plan[:, 1]])


# --------------------------------------------------------------------------
# Mesh assembly
# --------------------------------------------------------------------------


class _Builder:
    """Accumulates triangle strips and fans into one vertex-coloured mesh.

    Vertices are shared along a strip and never between strips. That is what
    keeps the road smooth along its length and hard-edged where the carriageway
    meets the kerb riser — the same flat-shaded treatment the buildings get,
    applied where it means something.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._colours: list[np.ndarray] = []
        self._uvs: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def strip(
        self,
        left: np.ndarray,
        right: np.ndarray,
        *,
        colour: tuple[int, int, int],
        along: np.ndarray,
        across: tuple[float, float],
    ) -> None:
        """A quad strip between two rails, wound so its face points out of it.

        `across` is the pair of U coordinates for the two rails, in lane widths;
        `along` is V, in metres. `docs/ART_DESIGN.md` puts lane markings in a
        shader driven by these rather than in a texture atlas, so U is a lane
        coordinate — an integer U is a lane boundary whatever the widening did
        to the metres.
        """
        span = len(left)
        if span < 2:
            return

        base = self._count
        index = np.arange(span - 1)
        self._triangles.append(
            np.concatenate(
                [
                    np.column_stack([index, index + 1, index + span]),
                    np.column_stack([index + 1, index + span + 1, index + span]),
                ]
            )
            + base
        )
        # One facing for the whole strip width: the two rails differ only by the
        # mitre, and a strip is a flat piece of road, kerb face or lip.
        facing = _rail_normals(left, right)
        self._positions.append(np.vstack([left, right]))
        self._normals.append(np.vstack([facing, facing]))
        self._colours.append(_rgba(colour, 2 * span))
        self._uvs.append(
            np.column_stack([np.repeat(across, span), np.concatenate([along, along])]).astype(
                np.float32
            )
        )
        self._count += 2 * span

    def fan(self, ring: np.ndarray, *, colour: tuple[int, int, int]) -> None:
        """A convex polygon as a fan from its centroid, facing up."""
        if len(ring) < 3:
            return
        if _shoelace(ring) > 0.0:
            ring = ring[::-1]

        base = self._count
        index = np.arange(len(ring))
        self._triangles.append(
            np.column_stack(
                [
                    np.full(len(ring), base + len(ring)),
                    index + base,
                    (index + 1) % len(ring) + base,
                ]
            )
        )
        self._positions.append(np.vstack([ring, ring.mean(axis=0)]))
        self._normals.append(np.tile([0.0, 1.0, 0.0], (len(ring) + 1, 1)))
        self._colours.append(_rgba(colour, len(ring) + 1))
        # A junction is not a length of lane, so it carries no marking
        # coordinate. Box junctions come from a mask keyed on the node, not
        # from these — see `docs/ART_DESIGN.md`.
        self._uvs.append(np.zeros((len(ring) + 1, 2), dtype=np.float32))
        self._count += len(ring) + 1

    def build(self, name: str) -> MeshData:
        """The accumulated geometry, minus the triangles that collapsed.

        A boundary held still at a tight corner leaves a quad with two corners
        in the same place. It draws as nothing and it has no normal, so it is
        dropped here rather than shipped into a collision shape.
        """
        if not self._triangles:
            raise ValueError(f"'{name}': nothing to write — the graph produced no ribbon")
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.vstack(self._normals).astype(np.float32),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            colours=np.vstack(self._colours),
            uvs=np.vstack(self._uvs),
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        kept = select_triangles(mesh, twice_area > _MIN_TWICE_AREA_M2)
        if kept is None:
            raise ValueError(f"'{name}': every triangle collapsed")
        return kept


def downward_facing(mesh: MeshData) -> tuple[int, float]:
    """How many triangles face downward, and how much ground they cover.

    A road triangle that points at the sky's opposite is a fold: it renders as a
    hole under back-face culling and it is invisible to a one-sided collider. A
    kerb riser is vertical and legitimately faces sideways, which is why the
    test is well below horizontal rather than at it.
    """
    cross = mesh.triangle_cross()
    twice_area = np.linalg.norm(cross, axis=1)
    facing = cross[:, 1] / np.where(twice_area > 0.0, twice_area, 1.0)
    inverted = facing < -0.1
    return int(inverted.sum()), float(0.5 * twice_area[inverted].sum())


def _rail_normals(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Per-vertex normal of a strip, from its own along and across directions.

    Derived rather than assumed, so one routine serves the flat carriageway, the
    vertical kerb riser and the lip between them.
    """
    along = np.empty_like(left)
    along[:-1] = left[1:] - left[:-1]
    along[-1] = along[-2]
    normals = np.cross(along, right - left)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    # A rail pair that meets — a zero-width strip — has no facing to compute,
    # and `normalise` leaves those rows at zero rather than at a direction.
    return np.where(length > _MIN_SEGMENT_M, normalise(normals), [0.0, 1.0, 0.0])


def _rgba(colour: tuple[int, int, int], count: int) -> np.ndarray:
    """One RGBA row per vertex, as a read-only view rather than a copy.

    `_Builder.build` materialises it in the one `vstack` that needs it — the
    same reasoning as `buildings.colour_for`.
    """
    return np.broadcast_to(np.array([*colour, 255], dtype=np.uint8), (count, 4))


def _shoelace(ring: np.ndarray) -> float:
    """Twice the signed plan area. Negative is a face pointing up (+Y)."""
    x, z = ring[:, 0], ring[:, 2]
    return float(np.dot(x, np.roll(z, -1)) - np.dot(np.roll(x, -1), z))


def hull(points: np.ndarray) -> np.ndarray:
    """Convex hull of a junction's ribbon ends, in plan, as (k, 3) in order.

    Andrew's monotone chain. The hull is the right shape for a junction cap
    because its boundary passes through every incoming ribbon's two end corners:
    the cap therefore meets each carriageway along its full width, with no gap,
    and stops at the kerb line rather than spilling into the corner between two
    streets — which is pavement, not road.

    Y comes along for the ride, so a cap on sloping ground follows it.
    """
    order = np.lexsort((points[:, 2], points[:, 0]))
    ordered = points[order]
    if len(ordered) < 3:
        return ordered

    def chain(rows: np.ndarray) -> list[np.ndarray]:
        built: list[np.ndarray] = []
        for point in rows:
            while len(built) >= 2 and _turn(built[-2], built[-1], point) <= 0.0:
                built.pop()
            built.append(point)
        return built

    lower, upper = chain(ordered), chain(ordered[::-1])
    return np.array(lower[:-1] + upper[:-1])


def _turn(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]))


# --------------------------------------------------------------------------
# Building the region
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _End:
    """One end of one edge, arriving at a node on one elevation level."""

    edge: int
    at_start: bool


@dataclass
class _Edge:
    """One graph edge, and the ribbon geometry derived from it."""

    points: np.ndarray
    half_width_m: float
    lanes: int
    level: int
    length_m: float
    trim_start_m: float = 0.0
    trim_end_m: float = 0.0
    # Filled by `_shape`, once the trims are known. The two carriageway
    # boundaries are stored rather than recomputed so the junction cap is built
    # from the same numbers the ribbon was — a cap derived from an unclamped
    # boundary would miss the arm it is supposed to meet.
    ribbon: np.ndarray | None = None
    offsets: np.ndarray | None = None
    left: np.ndarray | None = None
    right: np.ndarray | None = None

    def corner(self, at_start: bool, *, on_left: bool) -> np.ndarray | None:
        """One of the two corners this ribbon presents to a junction."""
        plan = self.left if on_left else self.right
        if plan is None or self.ribbon is None:
            return None
        row = 0 if at_start else -1
        return np.array([plan[row][0], self.ribbon[row][1], plan[row][1]])


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    out_root: Path | None = None,
) -> SurfaceReport:
    """Read the region's road graph and write its `roads.glb`."""
    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    style = city.roads.surface

    edges = [_prepare(edge, style) for edge in graph["edges"]]
    report = SurfaceReport()
    # Zipped rather than looked up: `_prepare` maps the published edges one for
    # one and in order, so the pairing is the list's own construction.
    report.carriageway = {
        int(published["id"]): round(prepared.half_width_m, 3)
        for published, prepared in zip(graph["edges"], edges, strict=True)
    }
    ends = _ends_by_node_and_level(graph["edges"], edges)
    _assign_trims(ends, edges, style, report)
    _count_level_changes(ends, edges, report)
    for edge in edges:
        _shape(edge)

    builder = _Builder()
    for edge in edges:
        if _draw_edge(builder, edge, style, city.roads.lane_width_m):
            report.edges += 1

    # Capped after every ribbon exists, because a cap is defined by where the
    # ribbons it joins actually ended — including where a trim was clamped.
    for group in ends.values():
        ring = _cap_ring(group, edges)
        if ring is not None:
            builder.fan(ring, colour=style.surface_colour)
            report.junctions += 1

    mesh = builder.build(SURFACE_MESH_NAME)
    report.inverted, report.inverted_area_m2 = downward_facing(mesh)
    report.triangles = mesh.triangle_count
    report.vertices = len(mesh.positions)
    report.aabb = mesh.aabb()
    report.bytes = write_glb(out_dir / SURFACE_NAME, [mesh])
    _write_manifest(out_dir, city, region_id, report)
    return report


def _prepare(published: dict, style: RoadSurface) -> _Edge:
    points = dedupe(np.asarray(published["polyline"], dtype=np.float64))
    return _Edge(
        points=points,
        half_width_m=published["width_m"] * style.widen_for(published["speed_limit_kph"]) / 2.0,
        lanes=published["lanes"],
        level=published["elevation_level"],
        length_m=float(plan_lengths(points)[-1]) if len(points) > 1 else 0.0,
    )


def _shape(edge: _Edge) -> None:
    """Trim the edge back from its junctions and offset what is left."""
    points = dedupe(trim(edge.points, edge.trim_start_m, edge.trim_end_m))
    if len(points) < 2:
        return
    edge.ribbon = points
    edge.offsets = mitres(points)
    edge.left = boundary(points, edge.offsets, edge.half_width_m)
    edge.right = boundary(points, edge.offsets, -edge.half_width_m)


def _ends_by_node_and_level(
    published: list[dict], edges: list[_Edge]
) -> dict[tuple[int, int], list[_End]]:
    """Edge ends grouped by the node *and the level* they arrive on.

    The level is part of the key, which is the opposite of how `P1-3` keys
    nodes and is right for the opposite reason. A node exists so a flyover and
    the ramp under it stay one network; a junction cap is a piece of tarmac, and
    there is no tarmac between a street and the tunnel roof 8 m below it.
    """
    groups: dict[tuple[int, int], list[_End]] = defaultdict(list)
    for index, edge in enumerate(published):
        geometry = edges[index]
        if len(geometry.points) < 2:
            continue
        for node, at_start in ((edge["from"], True), (edge["to"], False)):
            groups[(node, geometry.level)].append(_End(edge=index, at_start=at_start))
    return groups


def _assign_trims(
    ends: dict[tuple[int, int], list[_End]],
    edges: list[_Edge],
    style: RoadSurface,
    report: SurfaceReport,
) -> None:
    """Hold each ribbon back from the nodes where it meets another at its level.

    An end alone at its node and level is left long: there is nothing to join
    to, and trimming would leave the carriageway stopping short of the map edge
    or of the ramp it dead-ends against.
    """
    for group in ends.values():
        if len(group) < 2:
            continue
        radius = style.junction_trim_factor * max(edges[end.edge].half_width_m for end in group)
        for end in group:
            edge = edges[end.edge]
            ceiling = edge.length_m * style.junction_trim_max_fraction
            if end.at_start:
                edge.trim_start_m = min(radius, ceiling)
            else:
                edge.trim_end_m = min(radius, ceiling)
            report.trimmed_ends += 1
            if ceiling < radius:
                report.clamped_trims += 1


def _count_level_changes(
    ends: dict[tuple[int, int], list[_End]], edges: list[_Edge], report: SurfaceReport
) -> None:
    """Measure the vertical steps the graph leaves at grade transitions (`Q13`).

    Read off the level groups rather than off the heights, so this counts the
    nodes where the *network* changes level. Two edges meeting at one level
    differ in height only by the millimetre their coordinates were rounded to.
    """
    by_node: dict[int, list[float]] = defaultdict(list)
    for (node, _), group in ends.items():
        for end in group:
            points = edges[end.edge].points
            by_node[node].append(float(points[0 if end.at_start else -1][1]))

    for node, levels in _levels_by_node(ends).items():
        if len(levels) > 1:
            report.level_changes += 1
            report.max_level_step_m = max(
                report.max_level_step_m, max(by_node[node]) - min(by_node[node])
            )


def _levels_by_node(ends: dict[tuple[int, int], list[_End]]) -> dict[int, set[int]]:
    levels: dict[int, set[int]] = defaultdict(set)
    for node, level in ends:
        levels[node].add(level)
    return levels


def _draw_edge(builder: _Builder, edge: _Edge, style: RoadSurface, lane_width_m: float) -> bool:
    """The carriageway and both kerbs, between this edge's two trims."""
    points, offsets = edge.ribbon, edge.offsets
    if points is None or offsets is None or edge.left is None or edge.right is None:
        return False

    along = plan_lengths(points)
    kerb, rise = style.kerb_width_m, style.kerb_height_m
    # U is a lane coordinate: 0 at the nearside kerb line, `lanes` at the
    # offside one. The kerb runs off the ends of that range in the same units.
    outside = kerb / lane_width_m
    lanes = float(edge.lanes)

    # Each boundary is stopped on its own account. The kerb stays welded to the
    # carriageway because the two share vertex indices, not positions — so a
    # corner that holds the road edge still and the kerb line moving simply
    # makes the lip wider there, which is what a real kerb does on a tight bend.
    left = _lift(edge.left, points, 0.0)
    right = _lift(edge.right, points, 0.0)
    left_top = _lift(edge.left, points, rise)
    right_top = _lift(edge.right, points, rise)
    left_out = _lift(boundary(points, offsets, edge.half_width_m + kerb), points, rise)
    right_out = _lift(boundary(points, offsets, -(edge.half_width_m + kerb)), points, rise)

    # Rail order is the winding: `strip` faces out of the cross product of its
    # own along and across directions, so the two kerbs — being mirror images —
    # take their pairs in opposite orders. The carriageway is right-then-left
    # for the same reason. `test_surface.py` pins every one of these facings.
    builder.strip(right, left, colour=style.surface_colour, along=along, across=(lanes, 0.0))

    # The riser has no plan width, so both its rails sit at the kerb line and
    # share its U. The lip is where U crosses the kerb — putting the ramp on the
    # riser instead would make an integer U stop meaning a lane boundary.
    builder.strip(left, left_top, colour=style.kerb_colour, along=along, across=(0.0, 0.0))
    builder.strip(left_top, left_out, colour=style.kerb_colour, along=along, across=(0.0, -outside))
    builder.strip(right_top, right, colour=style.kerb_colour, along=along, across=(lanes, lanes))
    builder.strip(
        right_out, right_top, colour=style.kerb_colour, along=along, across=(lanes + outside, lanes)
    )
    return True


def _cap_ring(group: list[_End], edges: list[_Edge]) -> np.ndarray | None:
    """The junction polygon closing one node at one level, or None if there is none.

    Built from the two carriageway corners each ribbon presents to the node, so
    the cap meets every arm along that arm's full width.

    ⚠️ It **overlaps** those arms rather than abutting them, wherever they stop
    at different distances from the node — which they do whenever
    `junction_trim_max_fraction` holds a short edge back, 210 of the region's
    1,398 trimmed ends. An arm's mouth is then inside the hull and the cap
    re-covers ribbon that already exists: measured at 6,051 m2 of 52,985 m2 of
    cap area. Harmless today, because cap and carriageway are the same colour at
    the same height in the same material, so the coplanar pair cannot be told
    apart. It stops being harmless when `docs/ART_DESIGN.md`'s markings shader
    lands, since a cap carries no lane coordinate and the ribbon under it does.
    Fixing it properly means a non-convex cap — the union boundary rather than
    the hull — which is polygon clipping, and is not worth building blind.

    A group of one is a
    ribbon with nothing to join to — a map edge, or a ramp dead-ending against a
    deck it cannot reach — and gets no cap and no trim.
    """
    if len(group) < 2:
        return None
    corners = [
        corner
        for end in group
        for on_left in (True, False)
        if (corner := edges[end.edge].corner(end.at_start, on_left=on_left)) is not None
    ]
    if len(corners) < 3:
        return None
    ring = hull(np.vstack(corners))
    return ring if len(ring) >= 3 else None


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _write_manifest(out_dir: Path, city: CityConfig, region_id: str, report: SurfaceReport) -> None:
    """An intermediate for `P1-6`, not the game-facing contract.

    Same reasoning as `buildings.json`: `city.json` is `export.py`'s to write,
    and this records only what the surface stage knows so the two stages stay
    independently runnable.

    `carriageway` is the exception worth naming: it is the only thing here the
    *game* needs rather than the next stage. `roadgraph.json` publishes the
    authored street width, `lanes x lane_width_m`, while the ribbon is drawn at
    `width_m x widen_for(speed_limit_kph)` — so a runtime asking "where is the
    nearside lane?" from the graph alone lands short of the lane by a quarter of
    the widening. The factor stays on the surface style, where `config.py` says
    it belongs; the *result* travels, through `export.py`, into `city.json`.
    """
    write_document(
        out_dir / SURFACE_MANIFEST_NAME,
        {
            "schema_version": SURFACE_MANIFEST_SCHEMA,
            "city_id": city.id,
            "region_id": region_id,
            "mesh": SURFACE_NAME,
            "mesh_name": SURFACE_MESH_NAME,
            "triangles": report.triangles,
            "vertices": report.vertices,
            "bytes": report.bytes,
            "aabb": report.aabb,
            "carriageway": [
                {"edge": edge_id, "half_width_m": half}
                for edge_id, half in sorted(report.carriageway.items())
            ],
        },
    )


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
        "%d edges and %d junction caps: %d triangles, %d vertices, %.1f MB",
        report.edges,
        report.junctions,
        report.triangles,
        report.vertices,
        report.bytes / 1e6,
    )
    log.info(
        "  %d ends trimmed back from a junction, %d of them clamped by edge length",
        report.trimmed_ends,
        report.clamped_trims,
    )
    if report.inverted:
        log.info(
            "  %d triangles still fold inward at a hairpin, covering %.2f m2",
            report.inverted,
            report.inverted_area_m2,
        )
    if report.level_changes:
        log.warning(
            "  %d nodes step between elevation levels, by up to %.1f m — see Q13",
            report.level_changes,
            report.max_level_step_m,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
