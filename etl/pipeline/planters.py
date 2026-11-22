"""HyD's roadside planter walls to `planters.glb` (`P3-98`, `Q247`).

**Where is read, what is authored.** `INV_RPW` draws the wall of every planter
HyD keeps beside and between carriageways as a line, and that line is the whole
of what is published: no height, no level and nothing about what grows inside.
So the plan is the publisher's and everything vertical is ours — a wall at
`wall_height_m` over the ground the tiles draw, and, where a feature's walls
close into a ring, a bed of clumped shrub inside it (the user's pick of three
renders, 2026-11-18).

🔴 **A planter never stands on the drawn road.** A bed is cut back to
`kerb_clear_m` outside the level-0 carriageway, and refused whole where more
than `max_on_road` of it lay inside. It is also cut by every wall the tiles
stand through its height, so a ring drawn round a pier or a lift tower does not
plant the building.

One merged mesh and one `-colonly` collider beside it: the walls alone, since a
planter is something a car hits.

    python -m pipeline.planters --region wan_chai
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import shapely
import shapely.ops

from pipeline import gdb
from pipeline.config import Config, GameTransform, Planters, load_config
from pipeline.documents import write_document
from pipeline.fetch import cached_source
from pipeline.gltf import COLLISION_ONLY_SUFFIX, MeshData, write_glb
from pipeline.mesh import weld
from pipeline.meshbuild import Cell, ColouredBuilder, cell_name, cell_of, polygons_of, prism
from pipeline.railings import facing_away
from pipeline.surface_region import read as read_carriageway_region
from pipeline.trees import Faces, tile_corners

log = logging.getLogger(__name__)

PLANTERS_NAME = "planters.glb"
PLANTERS_MANIFEST_NAME = "planters.json"
PLANTERS_MANIFEST_SCHEMA = 1
PLANTERS_MESH_NAME = "planters"
PLANTERS_COLLIDER_NAME = f"planters_collision{COLLISION_ONLY_SUFFIX}"
# The glTF material the engine's importer dispatches on — `SHADERS` in
# `game/tools/generated_scene_import.gd` holds the other end.
PLANTERS_MATERIAL = "planters"

# A ring edge longer than this is cut, so a wall follows the ground under it.
_STEP_M = 4.0
# A published wall is thinned to this before it is drawn: the source's curves
# are a vertex every half metre, and a 5 cm chord is under the outline.
_SIMPLIFY_M = 0.05
# A tile face this close to upright is a wall.
_UPRIGHT = 0.1
# A tile wall cuts a bed when it starts no higher than this over the ground.
_WALL_FOOT_M = 0.3
# How far a wall cut is widened: the tiles' walls have no thickness.
_WALL_CUT_M = 0.05
# A clump piece smaller than this is not drawn.
_MIN_CLUMP_M2 = 0.15
_UP = np.array([0.0, 1.0, 0.0])
# What tells a clump's two draws apart.
_RISE_SALT, _TINT_SALT = 1, 2


@dataclass
class PlanterReport:
    features: int = 0
    empty_geometry: int = 0
    outside: int = 0
    read: int = 0
    closed: int = 0
    open: int = 0
    rings: int = 0
    # The refusals, as disjoint parts of `rings` with `beds`.
    in_carriageway: int = 0
    cut_away: int = 0
    no_ground: int = 0
    beds: int = 0
    walls: int = 0
    walls_too_small: int = 0
    walls_no_ground: int = 0
    bed_area_m2: float = 0.0
    road_cut_m2: float = 0.0
    building_cut_m2: float = 0.0
    clumps: int = 0
    max_ground_fall_m: float = 0.0
    facing_away: int = 0
    triangles: int = 0
    vertices: int = 0
    collider_triangles: int = 0
    bytes: int = 0


class Walls:
    """The tiles' upright faces, asked for the plan lines standing through a height."""

    def __init__(self, corners: np.ndarray) -> None:
        normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        length = np.linalg.norm(normal, axis=1)
        upright = np.abs(normal[:, 1]) <= _UPRIGHT * np.where(length > 0.0, length, 1.0)
        self.corners = corners[upright & (length > 0.0)]
        self.low = self.corners.min(axis=1)
        self.high = self.corners.max(axis=1)

    def through(
        self, bounds: tuple[float, float, float, float], foot: float, top: float
    ) -> shapely.Geometry | None:
        """The union of the walls in `bounds` that rise from `foot` past `top`, or None."""
        x0, z0, x1, z1 = bounds
        rows = (
            (self.high[:, 0] >= x0)
            & (self.low[:, 0] <= x1)
            & (self.high[:, 2] >= z0)
            & (self.low[:, 2] <= z1)
            & (self.low[:, 1] <= foot)
            & (self.high[:, 1] >= top)
        )
        if not rows.any():
            return None
        lines = []
        for triangle in self.corners[rows]:
            plan = triangle[:, [0, 2]]
            spans = [np.linalg.norm(plan[i] - plan[(i + 1) % 3]) for i in range(3)]
            longest = int(np.argmax(spans))
            lines.append(shapely.LineString([plan[longest], plan[(longest + 1) % 3]]))
        return shapely.unary_union(lines)


def read_walls(
    city: Config,
    spec: Planters,
    region_id: str,
    transform: GameTransform,
    report: PlanterReport,
    *,
    sources_root: Path | None = None,
) -> list[shapely.MultiLineString]:
    """Each published feature's walls in game plan, where they reach the region."""
    layer = gdb.read_layer(
        cached_source(city, spec.source, root=sources_root),
        spec.layer.layer,
        columns=spec.layer.columns,
        bbox=city.projected_bounds(region_id).bbox,
        expect_crs=city.projected_crs,
    )
    report.features = len(layer)
    far_x, far_z = city.region_high(region_id)
    frame = shapely.box(0.0, 0.0, far_x, far_z)
    owners, parts = gdb.polylines(layer)
    by_feature: dict[int, list[shapely.LineString]] = {}
    for owner, points in zip(owners, parts, strict=True):
        if len(points) < 2 or not np.isfinite(points).all():
            continue
        x, _, z = transform.to_game(points[:, 0], points[:, 1])
        by_feature.setdefault(int(owner), []).append(shapely.LineString(np.column_stack([x, z])))
    report.empty_geometry = len(layer) - len(by_feature)
    walls = []
    for owner in sorted(by_feature):
        lines = shapely.MultiLineString(by_feature[owner])
        if lines.intersects(frame):
            walls.append(lines)
        else:
            report.outside += 1
    report.read = len(walls)
    return walls


def _heights(ground: Faces, ring: np.ndarray) -> np.ndarray | None:
    """The ground under each ring point; a point over none takes the nearest that has."""
    found = np.full(len(ring), np.nan)
    for row, (x, z) in enumerate(ring):
        under = ground.heights(float(x), float(z))
        if len(under):
            found[row] = float(under.max())
    known = np.isfinite(found)
    if not known.any():
        return None
    for row in np.flatnonzero(~known):
        gaps = np.linalg.norm(ring[known] - ring[row], axis=1)
        found[row] = found[known][int(np.argmin(gaps))]
    return found


def _shade(colour: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(round(channel * factor) for channel in colour)  # type: ignore[return-value]


def _draw(salt: int, column: int, row: int) -> float:
    """A repeatable draw in [0, 1) for a clump cell: the same bed every build."""
    mixed = (column * 73856093) ^ (row * 19349663) ^ (salt * 83492791)
    return ((mixed * 2654435761) & 0xFFFFFFFF) / 2**32


def _clumps(
    builder: ColouredBuilder,
    spec: Planters,
    bed: shapely.Polygon,
    floor_of: Callable[[np.ndarray], np.ndarray],
    report: PlanterReport,
) -> None:
    """The planting: the bed inside its wall, cut into cells of their own height and green."""
    colour = spec.shrub_material.colour
    for inner in polygons_of(bed.buffer(-spec.shrub_inset_m)):
        x0, z0, x1, z1 = inner.bounds
        for column in range(int(x0 // spec.clump_m), int(x1 // spec.clump_m) + 1):
            for row in range(int(z0 // spec.clump_m), int(z1 // spec.clump_m) + 1):
                cell = shapely.box(
                    column * spec.clump_m,
                    row * spec.clump_m,
                    (column + 1) * spec.clump_m,
                    (row + 1) * spec.clump_m,
                )
                for piece in polygons_of(inner.intersection(cell)):
                    if piece.area < _MIN_CLUMP_M2:
                        continue
                    rise = spec.shrub_min_m + (spec.shrub_max_m - spec.shrub_min_m) * _draw(
                        _RISE_SALT, column, row
                    )
                    green = _shade(colour, 1.0 - spec.tint_darken * _draw(_TINT_SALT, column, row))
                    centre = piece.representative_point()
                    # Level, off the wall's top at its middle, and sunk to the
                    # ground so no clump floats where the wall falls away.
                    wall_top = float(floor_of(np.array([[centre.x, centre.y]]))[0])
                    wall_top += spec.wall_height_m
                    prism(
                        builder,
                        piece,
                        lambda plan, level=wall_top: np.full(len(plan), level),
                        spec.wall_height_m,
                        rise,
                        _shade(green, 1.0 - spec.side_darken),
                        green,
                    )
                    report.clumps += 1


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> PlanterReport:
    """Read the region's published planter walls and write `planters.glb`."""
    spec = city.planters
    report = PlanterReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no planters block; nothing to build", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    features = read_walls(city, spec, region_id, transform, report, sources_root=sources_root)
    far_x, far_z = city.region_high(region_id)
    ground, built = tile_corners(city, region_id, out_dir)
    meshes = build_planters(
        spec,
        features,
        shapely.box(0.0, 0.0, far_x, far_z),
        read_carriageway_region(out_dir, region_id).whole,
        Faces(ground),
        Walls(built),
        report,
    )
    if meshes:
        report.bytes = write_glb(out_dir / PLANTERS_NAME, meshes)
    _write_manifest(out_dir, city, region_id, report)
    return report


def build_planters(
    spec: Planters,
    features: list[shapely.MultiLineString],
    frame: shapely.Polygon,
    carriageway,
    ground: Faces,
    standing: Walls,
    report: PlanterReport,
) -> list[MeshData]:
    """A drawn mesh a plan cell and one collider, or nothing where no wall stood."""
    kept_clear = carriageway.buffer(spec.kerb_clear_m)
    drawn: dict[Cell, ColouredBuilder] = {}
    solid = ColouredBuilder(PLANTERS_MATERIAL)
    wall_colour = spec.wall_material.colour

    def stand(shape: shapely.Polygon, planted: bool) -> bool:
        """One wall or bed onto the ground under it; False where the tiles draw none."""
        shape = shape.simplify(_SIMPLIFY_M).segmentize(_STEP_M)
        if shape.is_empty:
            return False
        # Every ring, so the wall round a hole stands on its own ground.
        corners = np.vstack(
            [np.asarray(ring.coords)[:, :2] for ring in (shape.exterior, *shape.interiors)]
        )
        heights = _heights(ground, corners)
        if heights is None:
            return False
        tree = shapely.STRtree(shapely.points(corners))

        def floor(plan: np.ndarray) -> np.ndarray:
            return heights[tree.nearest(shapely.points(plan))]

        middle = shape.centroid
        cell = cell_of(middle.x, middle.y, spec.cell_m)
        if cell not in drawn:
            drawn[cell] = ColouredBuilder(PLANTERS_MATERIAL)
        builder = drawn[cell]
        for into in (builder, solid):
            prism(into, shape, floor, spec.sink_m, spec.wall_height_m, wall_colour, wall_colour)
        if planted:
            _clumps(builder, spec, shape, floor, report)
        report.max_ground_fall_m = max(
            report.max_ground_fall_m, float(heights.max() - heights.min())
        )
        return True

    for lines in features:
        rings = list(shapely.ops.polygonize(shapely.unary_union(lines)))
        if not rings:
            report.open += 1
            strip = lines.buffer(0.5 * spec.wall_width_m, cap_style="flat")
            for piece in polygons_of(strip.difference(kept_clear).intersection(frame)):
                if piece.area < spec.min_wall_m2:
                    report.walls_too_small += 1
                elif stand(piece, False):
                    report.walls += 1
                else:
                    report.walls_no_ground += 1
            continue
        report.closed += 1
        for ring in rings:
            report.rings += 1
            on_road = ring.intersection(carriageway).area
            if on_road > spec.max_on_road * ring.area:
                report.in_carriageway += 1
                continue
            bed = ring.difference(kept_clear)
            road_cut = ring.area - bed.area
            ring_ground = _heights(ground, np.asarray(ring.exterior.coords)[:, :2])
            if ring_ground is None:
                report.no_ground += 1
                continue
            # From the ring's highest ground: on a slope that asks more of a
            # wall than the low end would, and cuts by fewer.
            high = float(ring_ground.max())
            through = standing.through(ring.bounds, high + _WALL_FOOT_M, high + spec.wall_height_m)
            building_cut = 0.0
            if through is not None:
                blocks = shapely.unary_union(
                    [*shapely.ops.polygonize(through), through.buffer(_WALL_CUT_M)]
                )
                cut = bed.difference(blocks)
                building_cut = bed.area - cut.area
                bed = cut
            pieces = [
                piece
                for piece in polygons_of(bed.intersection(frame))
                if piece.area >= spec.min_bed_m2
            ]
            if not pieces:
                report.cut_away += 1
                continue
            stood = [piece for piece in pieces if stand(piece, True)]
            if not stood:
                report.no_ground += 1
                continue
            report.beds += 1
            report.bed_area_m2 += sum(piece.area for piece in stood)
            # Of the beds that stand; a refused ring's cuts are not a planter's.
            report.road_cut_m2 += road_cut
            report.building_cut_m2 += building_cut

    # Welded: a builder lays each face with its own corners. Lossless.
    meshes = [
        weld(mesh)
        for cell in sorted(drawn)
        if (mesh := drawn[cell].build(cell_name(PLANTERS_MESH_NAME, cell))) is not None
    ]
    walls = solid.build(PLANTERS_COLLIDER_NAME)
    if not meshes or walls is None:
        return []
    collider = replace(walls, colours=None, material=None)
    report.facing_away = sum(facing_away(mesh) for mesh in meshes)
    report.triangles = sum(len(mesh.triangles) for mesh in meshes)
    report.vertices = sum(len(mesh.positions) for mesh in meshes)
    report.collider_triangles = len(collider.triangles)
    return [*meshes, collider]


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: PlanterReport) -> int:
    document = {
        "schema_version": PLANTERS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "asset": PLANTERS_NAME if report.triangles else None,
        "features": report.features,
        "empty_geometry": report.empty_geometry,
        "outside": report.outside,
        "read": report.read,
        # `read` in two: a feature whose walls close at least one ring, and one
        # whose walls close none and stand as walls alone. ⚠️ A closed
        # feature's walls that are part of no ring are not drawn.
        "closed": report.closed,
        "open": report.open,
        "rings": report.rings,
        # The refusals, as disjoint parts of `rings` with `beds`.
        "in_carriageway": report.in_carriageway,
        "cut_away": report.cut_away,
        "no_ground": report.no_ground,
        "beds": report.beds,
        "walls": report.walls,
        "walls_too_small": report.walls_too_small,
        "walls_no_ground": report.walls_no_ground,
        "bed_area_m2": round(report.bed_area_m2, 1),
        "road_cut_m2": round(report.road_cut_m2, 1),
        "building_cut_m2": round(report.building_cut_m2, 1),
        "clumps": report.clumps,
        # The most the ground falls under one wall — what a level top would hide.
        "max_ground_fall_m": round(report.max_ground_fall_m, 2),
        "facing_away": report.facing_away,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "collider_triangles": report.collider_triangles,
        "bytes": report.bytes,
    }
    return write_document(out_dir / PLANTERS_MANIFEST_NAME, document)


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
        "planters: %d read -> %d beds of %d rings (%d on the road, %d cut away, %d no ground), "
        "%d walls, %.0f m2 planted in %d clumps, %d triangles, %d facing away",
        report.read,
        report.beds,
        report.rings,
        report.in_carriageway,
        report.cut_away,
        report.no_ground,
        report.walls,
        report.bed_area_m2,
        report.clumps,
        report.triangles,
        report.facing_away,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
