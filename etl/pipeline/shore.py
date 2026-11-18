"""The sea's edge, cut into the ground (`P3-101`, `Q250`).

Until this the tile stage dropped every ground vertex under the sea to the
seabed and let each triangle that straddled the shoreline slope over its own
width: a beach as long as the terrain's cell, on a harbour the publisher draws
as a wall. Measured on Wan Chai's LOD0 tiles, 17.8% of the land within 12 m of
the sea lay under the water.

Here the decimated ground is **cut along the sea polygon's own edge**, the one
`water.glb` is drawn to, so the land stops exactly where the water starts:

- land keeps the published terrain to the line;
- sea drops to `seabed_m`;
- where the line is built — the nearer published shoreline is a sea wall or a
  breakwater (`basemap.shoreline.hard_types`) — the two are joined by a
  vertical face in `quay_material`, part of the tile and of its collider;
- where it is natural, the sea's side of the cut keeps the terrain's height at
  the line and slopes from there, so a high-water mark stays a shore.

🔴 **After `collapse`, never before** (`Q25`): the ground is decimated once as
one surface and cut afterwards, so every cell size is cut along the same line
and a tier change does not move the quay.

⚠️ **Hard or soft is read per point, by position**, never per triangle: two
triangles that share a cut point agree on its height, so the cut opens no
crack between them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry

from pipeline.basemap import BASEMAP_NAME, BASEMAP_SCHEMA
from pipeline.documents import read_document
from pipeline.geometry import orient
from pipeline.gltf import MeshData
from pipeline.mesh import _rebuild, _unpack, weld
from pipeline.meshbuild import MIN_TWICE_AREA_M2

# The plan cell the sea is clipped to before a triangle is cut against it, and
# how far past the cell the clip reaches. A speed measure alone: a triangle
# that does not fit takes the whole sea.
_LOCAL_CELL_M = 64.0
_LOCAL_MARGIN_M = 32.0
# A point this close to the sea polygon's boundary lies on it. The cut's own
# points are GEOS intersections, exact to ~1e-12 at region magnitudes.
_ON_EDGE_M = 1e-7


@dataclass(frozen=True)
class Shore:
    """What the ground is cut by: the sea's plan polygon, the published lines
    that say which of its edge is built, and what the cut is made to."""

    sea: BaseGeometry
    hard: list[LineString]
    soft: list[LineString]
    seabed_m: float
    colour: tuple[int, int, int]

    def is_hard(self, x: np.ndarray, z: np.ndarray) -> np.ndarray:
        """Whether the nearer published shoreline at each point is a built one."""
        if not self.hard:
            return np.zeros(len(x), dtype=bool)
        if not self.soft:
            return np.ones(len(x), dtype=bool)
        points = shapely.points(x, z)
        return _nearest_m(self.hard, points) <= _nearest_m(self.soft, points)


def _nearest_m(lines: list[LineString], points: np.ndarray) -> np.ndarray:
    tree = shapely.STRtree(lines)
    rows, distance = tree.query_nearest(points, return_distance=True, all_matches=False)
    found = np.full(len(points), np.inf)
    found[rows[0]] = distance
    return found


@dataclass
class ShoreReport:
    # Ground triangles the sea's edge crossed.
    cut: int = 0
    # Vertices at the seabed.
    sunk: int = 0
    # The sea's edge over the ground, and how much of it is a wall.
    edge_m: float = 0.0
    quay_m: float = 0.0
    wall_triangles: int = 0


def shoreline_of_bundle(out_dir: Path, region_id: str) -> tuple[list[LineString], list[LineString]]:
    """The built and the natural shoreline from the document `basemap.py`
    wrote, in the region's game plan metres."""
    document = read_document(
        out_dir / BASEMAP_NAME, BASEMAP_SCHEMA, f"python -m pipeline.basemap --region {region_id}"
    )
    published = document.get("shoreline") or {}

    def lines(kind: str) -> list[LineString]:
        return [
            LineString(np.asarray(flat, dtype=np.float64).reshape(-1, 2))
            for flat in published.get(kind, [])
            if len(flat) >= 4
        ]

    return lines("hard"), lines("soft")


class _LocalSea:
    """The sea near a triangle, and its edge: `sea` clipped to the plan cell
    that holds the triangle."""

    def __init__(self, sea: BaseGeometry) -> None:
        self._whole = (sea, sea.boundary)
        self._cells: dict[tuple[int, int], tuple[BaseGeometry, BaseGeometry]] = {}

    def near(self, plan: np.ndarray) -> tuple[BaseGeometry, BaseGeometry]:
        low, high = plan.min(axis=0), plan.max(axis=0)
        cell = (int(low[0] // _LOCAL_CELL_M), int(low[1] // _LOCAL_CELL_M))
        x0, z0 = cell[0] * _LOCAL_CELL_M, cell[1] * _LOCAL_CELL_M
        reach = _LOCAL_CELL_M + _LOCAL_MARGIN_M
        if high[0] > x0 + reach or high[1] > z0 + reach:
            return self._whole
        if cell not in self._cells:
            around = box(x0 - _LOCAL_MARGIN_M, z0 - _LOCAL_MARGIN_M, x0 + reach, z0 + reach)
            self._cells[cell] = (
                self._whole[0].intersection(around),
                self._whole[1].intersection(around),
            )
        return self._cells[cell]


def _on(edge: BaseGeometry, points: np.ndarray) -> np.ndarray:
    """Which plan points lie on the sea's edge."""
    return shapely.distance(shapely.points(points), edge) < _ON_EDGE_M


def _weights(points: np.ndarray, plan: np.ndarray) -> np.ndarray:
    """Each point's barycentric weights in the plan triangle `plan`."""
    a, b, c = plan
    twice = orient(a, b, c)
    wb = orient(a, points, c) / twice
    wc = orient(a, b, points) / twice
    weights = np.clip(np.column_stack([1.0 - wb - wc, wb, wc]), 0.0, 1.0)
    return weights / weights.sum(axis=1, keepdims=True)


def _interpolated(weights: np.ndarray, source: np.ndarray) -> np.ndarray:
    """A corner row for each cut point: the position and the normal blended
    across the triangle, every other channel taken whole from the nearest
    corner. The colour, so every shipped vertex is still paving or grass and
    nothing between — `paint_parks`' rule, and what `trees.tile_corners` knows
    the ground by — and the UV sets, which are payloads (`facade_uv`,
    `identity_uv2`) and not surfaces to sample."""
    rows = weights @ source
    rows[:, 6:] = source[weights.argmax(axis=1), 6:]
    return rows


def _polygons(geometry: BaseGeometry) -> list[Polygon]:
    return [
        shapely.geometry.polygon.orient(part, 1.0)
        for part in shapely.get_parts(geometry)
        if isinstance(part, Polygon) and part.area > MIN_TWICE_AREA_M2
    ]


def cut_sea(mesh: MeshData, shore: Shore) -> tuple[MeshData, ShoreReport]:
    """`mesh`, a height field, cut along `shore.sea`'s edge: the sea sunk to
    the seabed, the built shore walled, the natural shore sloped."""
    report = ShoreReport()
    if shore.sea.is_empty or mesh.triangle_count == 0:
        return mesh, report

    corners, widths = _unpack(mesh)
    plan = corners[:, :, [0, 2]]
    signed = orient(plan[:, 0], plan[:, 1], plan[:, 2])
    faces = shapely.polygons(np.concatenate([plan, plan[:, :1]], axis=1))
    crossing = np.zeros(len(corners), dtype=bool)
    crossing[shapely.STRtree(faces).query(shore.sea.boundary, predicate="intersects")] = True
    crossing &= np.abs(signed) > MIN_TWICE_AREA_M2

    # Whole triangles: under the sea or not, by where they lie.
    centre = plan.mean(axis=1)
    under = ~crossing & shapely.contains_xy(shore.sea, centre[:, 0], centre[:, 1])
    whole = corners[~crossing].copy()
    whole[under[~crossing], :, 1] = shore.seabed_m

    # Cut triangles — every one the sea's edge touches, one it merely runs
    # along included: each row a corner, and whether it is a point on that
    # edge, whose height the nearer shoreline decides.
    pieces: list[np.ndarray] = []
    on_shore: list[np.ndarray] = []
    walls: list[np.ndarray] = []
    facings: list[np.ndarray] = []
    local = _LocalSea(shore.sea)
    for row in np.flatnonzero(crossing):
        source, face = corners[row], faces[row]
        sea, sea_edge = local.near(plan[row])
        for part, wet in ((face.intersection(sea), True), (face.difference(sea), False)):
            for polygon in _polygons(part):
                for triangle in shapely.get_parts(shapely.constrained_delaunay_triangles(polygon)):
                    points = np.asarray(triangle.exterior.coords)[:3]
                    if (orient(*points) > 0.0) != (signed[row] > 0.0):
                        points = points[::-1]
                    weights = _weights(points, plan[row])
                    piece = _interpolated(weights, source)
                    at_line = _on(sea_edge, points) if wet else np.zeros(3, dtype=bool)
                    if wet:
                        piece[~at_line, 1] = shore.seabed_m
                    pieces.append(piece)
                    on_shore.append(at_line)
                if wet:
                    _wall(polygon, sea_edge, plan[row], source, walls, facings, report)
        report.cut += 1

    cut = np.array(pieces).reshape(-1, 3, corners.shape[2])
    edge = np.array(on_shore, dtype=bool).reshape(-1, 3)
    wall = np.array(walls).reshape(-1, 3, corners.shape[2] + 1)
    # A point on the sea's edge drops where the shore is built and keeps the
    # terrain where it is natural. `_wall` marks a face's bottom rows with a
    # NaN height and carries the top's in a last column: on a natural shore
    # the bottom stands at its top and the face has no area.
    low = np.isnan(wall[:, :, 1])
    for rows, mask, kept in ((cut, edge, cut[:, :, 1]), (wall, low, wall[:, :, -1])):
        if mask.any():
            hard = shore.is_hard(rows[mask][:, 0], rows[mask][:, 2])
            rows[mask, 1] = np.where(hard, shore.seabed_m, kept[mask])
    wall = _faced(
        wall[:, :, :-1],
        np.array(facings).reshape(-1, 3),
        signed,
        mesh.colours is not None,
        shore,
        report,
    )

    rebuilt = weld(_rebuild(mesh, np.concatenate([whole, cut, wall]), widths))
    report.sunk = int((rebuilt.positions[:, 1] == shore.seabed_m).sum())
    return rebuilt, report


def _wall(
    polygon: Polygon,
    sea_edge: BaseGeometry,
    plan: np.ndarray,
    source: np.ndarray,
    walls: list[np.ndarray],
    facings: list[np.ndarray],
    report: ShoreReport,
) -> None:
    """The vertical faces under the edges of `polygon`, a piece of sea, that
    lie on the sea's edge. Each row carries one more column, its top's height,
    and a bottom row a NaN height for `cut_sea` to settle."""
    for ring in (polygon.exterior, *polygon.interiors):
        points = np.asarray(ring.coords)
        weights = _weights(points, plan)
        for at in np.flatnonzero(_on(sea_edge, 0.5 * (points[:-1] + points[1:]))):
            step = points[at + 1] - points[at]
            length = float(np.hypot(*step))
            if length <= 0.0:
                continue
            report.edge_m += length
            top = _interpolated(weights[[at, at + 1]], source)
            top = np.column_stack([top, top[:, 1]])
            bottom = top.copy()
            bottom[:, 1] = np.nan
            walls.extend(
                [np.array([top[0], top[1], bottom[1]]), np.array([top[0], bottom[1], bottom[0]])]
            )
            # The ring is wound anticlockwise, so the sea is on its left.
            facing = np.array([-step[1], 0.0, step[0]]) / length
            facings.extend([facing, facing])


def _faced(
    wall: np.ndarray,
    facings: np.ndarray,
    signed: np.ndarray,
    coloured: bool,
    shore: Shore,
    report: ShoreReport,
) -> np.ndarray:
    """The walls that stand, wound to face the sea the way the ground faces up,
    with the sea's facing for a normal and the quay's colour."""
    if len(wall) == 0:
        return wall
    cross = np.cross(wall[:, 1, :3] - wall[:, 0, :3], wall[:, 2, :3] - wall[:, 0, :3])
    stands = np.linalg.norm(cross, axis=1) > MIN_TWICE_AREA_M2
    wall, facings, cross = wall[stands], facings[stands], cross[stands]
    # The ground's own rule: a plan triangle wound with a negative signed area
    # has its right-handed normal up. Whichever way the ground is wound, a wall
    # is wound the same way about the direction it faces.
    ground_up = -1.0 if np.median(signed) > 0.0 else 1.0
    flip = np.sign((cross * facings).sum(axis=1)) != ground_up
    wall[flip] = wall[flip][:, ::-1]
    wall[:, :, 3:6] = facings[:, None, :]
    if coloured:
        wall[:, :, 6:9] = shore.colour
        wall[:, :, 9] = 255.0
    report.wall_triangles = len(wall)
    # Half a face a triangle: its top edge, or its bottom, is the line.
    height = np.ptp(wall[:, :, 1], axis=1)
    report.quay_m = float(
        np.divide(
            np.linalg.norm(cross, axis=1), height, out=np.zeros(len(wall)), where=height > 0
        ).sum()
        * 0.5
    )
    return wall
