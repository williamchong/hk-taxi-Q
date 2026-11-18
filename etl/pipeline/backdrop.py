"""The far shore (`P3-100`, `Q249`): the skyline across the harbour, the ground
it stands on and the sea that reaches it, as `backdrop.glb`.

Seen from a kilometre and more and never driven, so it is none of the things a
region is: no roads, no tiles, no collider, no shadow. Three parts, two meshes:

- **The skyline**: each block of the topographic map's `Building` layer over
  the strip (`backdrop.bounds`), extruded from the shore's ground to its
  published roof level. Only blocks at least `min_height_m` tall, and no more
  than `triangle_cap` triangles of them: over the cap the shortest go first,
  and the manifest says what height was drawn down to.
- **The shore**: one flat slab at `ground_level_m` under everything published
  — every footprint and every sea wall, closed over gaps up to twice
  `ground_close_m` and filled.
- **The far sea**: the water from the basemap's frame out to the strip and
  under it, in the water's own material, so the harbour does not end at the
  map's reach — and the basemap's own sea a second time, because the far plane
  cuts that off 400 m from the camera, which on a diagonal is short of the
  frame's edge. Nearer than that the basemap's water is in front of its copy.

⚠️ **The shore is not the basemap's cut** (`basemap.sea_of`), which needs a
shoreline that separates land from sea. Over Kowloon the published one does
not: West Kowloon's waterfront and east Tsim Sha Tsui's are gaps of several
hundred metres, and the cut finds one piece. So the shore is where things
stand, and an unbuilt waterfront wider than the closing is sea.

⚠️ **The far sea is a rectangle, not a survey.** Between the frame and the
strip no sheet is read, so it runs over whatever stands there past the frame's
north edge: undrawn land beside the region reads as water from across the map.

    python -m pipeline.backdrop --region wan_chai
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry

from pipeline import basemap, gdb
from pipeline.config import Backdrop, Config, SourceLayer, load_config
from pipeline.crs import GameTransform, project_bounds
from pipeline.documents import write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.meshbuild import ColouredBuilder
from pipeline.planters import prism

log = logging.getLogger(__name__)

BACKDROP_NAME = "backdrop.glb"
BACKDROP_MANIFEST_NAME = "backdrop.json"
BACKDROP_MANIFEST_SCHEMA = 1
BACKDROP_MESH_NAME = "backdrop"
BACKDROP_SEA_MESH_NAME = "backdrop_sea"
# The glTF material the engine's importer dispatches on — `SHADERS` in
# `game/tools/generated_scene_import.gd` holds the other end. The sea's is
# `basemap.WATER_MATERIAL`: one harbour, one water.
BACKDROP_MATERIAL = "backdrop"

# `COLOR_0`'s fourth byte on the far sea: the marker `water.gdshader` reads to
# draw a vertex past the camera's far plane. The water's shader is opaque, so
# the byte is free (`meshbuild.ColouredBuilder.polygon`).
FAR_SEA_ALPHA = 0

# How far the shore's slab reaches under the water plane, so its wall has no
# lower edge to see.
_SKIRT_M = 1.0


@dataclass(frozen=True)
class Block:
    """One published building block: its footprint in projected metres, its
    roof level and how tall it stands over its own base."""

    footprint: Polygon
    roof_m: float
    height_m: float

    @property
    def triangles(self) -> int:
        """What `prism` draws of it: two a wall segment, and a roof."""
        rings = (self.footprint.exterior, *self.footprint.interiors)
        corners = sum(len(ring.coords) - 1 for ring in rings)
        return 3 * corners - 2 + 2 * len(self.footprint.interiors)


@dataclass
class BackdropReport:
    # Building parts in the strip, and those with no usable level.
    blocks_read: int = 0
    blocks_no_level: int = 0
    # At least `min_height_m` tall, and the ones the cap kept.
    blocks_tall: int = 0
    blocks_drawn: int = 0
    # The height of the shortest block drawn: how far down the cap let the
    # skyline reach, never under `min_height_m`.
    min_height_drawn_m: float = 0.0
    tallest_m: float = 0.0
    skyline_triangles: int = 0
    shore_triangles: int = 0
    sea_triangles: int = 0
    shore_m2: float = 0.0
    sea_m2: float = 0.0
    # The strip's distance from the region's own frame, in metres: what
    # keeps the skyline out of anywhere a car can be.
    gap_m: float = 0.0
    asset: str = ""
    bytes: int = 0


def strip_of(city: Config, spec: Backdrop) -> Polygon:
    """`backdrop.bounds` in projected metres."""
    projected = project_bounds(
        spec.bounds, geodetic_crs=city.geodetic_crs, projected_crs=city.projected_crs
    )
    return box(*projected.bbox)


def _layers(
    city: Config,
    spec: Backdrop,
    region_id: str,
    layer: SourceLayer,
    strip: Polygon,
    sources_root: Path | None,
) -> list[gdb.Layer]:
    """`layer` from every sheet under the strip."""
    reads = source_reads(city, spec, region_id, root=sources_root, bounds=spec.bounds)
    return [
        gdb.read_layer(
            path,
            layer.layer,
            columns=layer.columns,
            bbox=strip.bounds,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        for path, member in reads
    ]


def read_blocks(
    layers: list[gdb.Layer], spec: Backdrop, strip: Polygon, report: BackdropReport
) -> list[Block]:
    """Every building part whose centre is inside the strip and whose levels
    are published, thinned to `simplify_m`.

    ⚠️ **Kept by its centre, never clipped**: a sheet's read box hands back the
    blocks that straddle it, and the same block from two sheets is one block.
    """
    seen: set[tuple[float, float, float]] = set()
    shapely.prepare(strip)
    blocks: list[Block] = []
    for layer in layers:
        base = layer.column(spec.buildings.field("base")).astype(np.float64)
        roof = layer.column(spec.buildings.field("roof")).astype(np.float64)
        owners, parts = gdb.polygons(layer)
        for owner, rings in zip(owners, parts, strict=True):
            footprint = shapely.make_valid(Polygon(rings[0], rings[1:]))
            if footprint.is_empty:
                continue
            centre = footprint.representative_point()
            key = (round(centre.x, 1), round(centre.y, 1), round(float(roof[owner]), 1))
            if key in seen or not strip.contains(centre):
                continue
            seen.add(key)
            report.blocks_read += 1
            height = float(roof[owner] - base[owner])
            if not np.isfinite(height) or height <= 0.0:
                report.blocks_no_level += 1
                continue
            simple = footprint.simplify(spec.simplify_m, preserve_topology=True)
            for part in shapely.get_parts(shapely.make_valid(simple)):
                if isinstance(part, Polygon) and part.area > 0.0:
                    blocks.append(Block(part, float(roof[owner]), height))
    return blocks


def skyline_of(blocks: list[Block], spec: Backdrop, report: BackdropReport) -> list[Block]:
    """The blocks at least `min_height_m` tall, tallest first, as many as fit
    under `triangle_cap`.

    Tallest first because a skyline is read off its tops: the block the cap
    refuses is always the shortest one left.
    """
    tall = sorted(
        (block for block in blocks if block.height_m >= spec.min_height_m),
        key=lambda block: (-block.height_m, block.footprint.centroid.x, block.footprint.centroid.y),
    )
    report.blocks_tall = len(tall)
    drawn: list[Block] = []
    spent = 0
    for block in tall:
        if spent + block.triangles > spec.triangle_cap:
            break
        spent += block.triangles
        drawn.append(block)
    report.blocks_drawn = len(drawn)
    report.min_height_drawn_m = drawn[-1].height_m if drawn else 0.0
    report.tallest_m = drawn[0].height_m if drawn else 0.0
    return drawn


def shore_of(
    strip: Polygon, blocks: list[Block], shoreline: list[LineString], spec: Backdrop
) -> BaseGeometry:
    """The ground everything published stands on: the footprints and the sea
    walls, closed by `ground_close_m` and filled, inside the strip.

    Filled, because a park inland is a hole in what is built and not a lake.
    """
    stood = shapely.union_all([block.footprint for block in blocks] + shoreline)
    closed = stood.buffer(spec.ground_close_m).buffer(-spec.ground_close_m)
    filled = [
        Polygon(part.exterior)
        for part in shapely.get_parts(closed)
        if isinstance(part, Polygon) and not part.is_empty
    ]
    if not filled:
        return Polygon()
    shore = shapely.union_all(filled).intersection(strip)
    return shapely.make_valid(shore.simplify(spec.simplify_m, preserve_topology=True))


def far_sea_of(strip: Polygon, frames: list[Polygon], seas: list[BaseGeometry]) -> BaseGeometry:
    """The water from the first of `frames` — the region's, whose north edge
    it starts at — out to the strip and under it, and inside each frame the
    sea the basemap found there.

    Spans the strip and the frames both, east to west. ⚠️ Inside a frame it is
    the basemap's sea and nothing more: run under the land, it would floor the
    far end of every street the far plane cuts short.
    """
    own = frames[0]
    west = min(strip.bounds[0], *(frame.bounds[0] for frame in frames))
    east = max(strip.bounds[2], *(frame.bounds[2] for frame in frames))
    reach = box(west, own.bounds[3], east, strip.bounds[3])
    return shapely.union_all([reach.difference(shapely.union_all(frames)), *seas])


def _to_game(geometry: BaseGeometry, transform: GameTransform) -> BaseGeometry:
    """`geometry` in the region's game plan: `(x, z)` where it held `(E, N)`."""

    def plan(points: np.ndarray) -> np.ndarray:
        x, _, z = transform.to_game(points[:, 0], points[:, 1])
        return np.column_stack([x, z])

    return shapely.transform(geometry, plan)


def build_meshes(
    skyline: list[Block],
    shore: BaseGeometry,
    far_sea: BaseGeometry,
    city: Config,
    transform: GameTransform,
    report: BackdropReport,
) -> list[MeshData]:
    """The skyline and its shore as one mesh, the far sea as another."""
    spec, harbour = city.backdrop, city.basemap
    assert spec is not None and harbour is not None
    builder = ColouredBuilder(BACKDROP_MATERIAL)
    ground = spec.ground_level_m

    def level(height: float) -> Callable[[np.ndarray], np.ndarray]:
        return lambda plan: np.full(len(plan), height)

    for block in skyline:
        colour = spec.material_for(block.height_m).colour
        prism(
            builder,
            _to_game(block.footprint, transform),
            level(ground),
            0.0,
            block.roof_m - ground,
            colour,
            colour,
        )
    skyline_mesh = builder.build(BACKDROP_MESH_NAME)
    report.skyline_triangles = 0 if skyline_mesh is None else len(skyline_mesh.triangles)

    colour = spec.ground_material.colour
    for part in shapely.get_parts(shore):
        if isinstance(part, Polygon) and part.area > 0.0:
            prism(
                builder,
                _to_game(part, transform),
                level(harbour.water_level_m - _SKIRT_M),
                0.0,
                ground - harbour.water_level_m + _SKIRT_M,
                colour,
                colour,
            )
    meshes: list[MeshData] = []
    land = builder.build(BACKDROP_MESH_NAME)
    if land is not None:
        report.shore_triangles = len(land.triangles) - report.skyline_triangles
        meshes.append(land)

    sea = basemap.water_mesh(
        # The basemap's tolerance, not this block's: inside a frame this is the
        # basemap's water over again and must lie under the same outline.
        basemap.triangles_of(far_sea, harbour.simplify_m, transform),
        harbour.water_level_m,
        harbour.water_material.colour,
    )
    if sea is not None and sea.colours is not None:
        report.sea_triangles = len(sea.triangles)
        # `FAR_SEA_ALPHA` on every vertex: `water.gdshader` draws these past
        # the far plane and the basemap's own water, at 255, where it stands.
        colours = sea.colours.copy()
        colours[:, 3] = FAR_SEA_ALPHA
        meshes.append(replace(sea, name=BACKDROP_SEA_MESH_NAME, colours=colours))
    return meshes


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> BackdropReport:
    """Write `backdrop.glb` for a region that ships the far shore, and the
    manifest for every region."""
    report = BackdropReport()
    out_dir = city.out_dir(region_id, out_root)
    spec, harbour = city.backdrop, city.basemap
    meshes: list[MeshData] = []
    if spec is not None and harbour is not None and region_id in spec.regions:
        strip = strip_of(city, spec)
        frame = basemap.frame_of(city, region_id, harbour.reach_m)
        report.gap_m = float(strip.distance(frame))
        if report.gap_m <= 0.0:
            raise ValueError(
                f"backdrop.bounds reaches into {region_id}'s own frame — "
                "the far shore is the one a region does not hold"
            )
        if strip.bounds[1] < frame.bounds[3]:
            raise ValueError(
                f"backdrop.bounds is not north of {region_id}: the far sea is run "
                "from the frame's north edge and has no other shape yet"
            )
        frames, seas = [], []
        for resident in (region_id, *city.neighbours(region_id).values()):
            framed, sea = basemap.read_sea(
                city, resident, basemap.BasemapReport(), sources_root=sources_root
            )
            frames.append(framed)
            seas.append(sea)
        blocks = read_blocks(
            _layers(city, spec, region_id, spec.buildings, strip, sources_root), spec, strip, report
        )
        shoreline = basemap.read_shoreline(
            _layers(city, spec, region_id, harbour.shoreline, strip, sources_root), harbour
        )
        shore = shore_of(strip, blocks, shoreline, spec)
        far_sea = far_sea_of(strip, frames, seas)
        report.shore_m2 = float(shore.area)
        report.sea_m2 = float(far_sea.area)
        transform = city.game_transform(region_id)
        meshes = build_meshes(
            skyline_of(blocks, spec, report), shore, far_sea, city, transform, report
        )
    if meshes:
        report.bytes = write_glb(out_dir / BACKDROP_NAME, meshes)
        report.asset = BACKDROP_NAME
    else:
        # Named from what was drawn, on `basemap`'s terms.
        (out_dir / BACKDROP_NAME).unlink(missing_ok=True)
    _write_manifest(out_dir, city, region_id, report)
    return report


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: BackdropReport) -> None:
    spec = city.backdrop
    document = {
        "schema_version": BACKDROP_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # `backdrop.glb`, or null where the city declares no `backdrop:` block
        # or this region is not one that ships it.
        "asset": report.asset or None,
        "triangle_cap": None if spec is None else spec.triangle_cap,
        "min_height_m": None if spec is None else spec.min_height_m,
        "blocks_read": report.blocks_read,
        "blocks_no_level": report.blocks_no_level,
        "blocks_tall": report.blocks_tall,
        "blocks_drawn": report.blocks_drawn,
        # The shortest block drawn: above `min_height_m` where the cap, not
        # the dial, drew the line.
        "min_height_drawn_m": round(report.min_height_drawn_m, 1),
        "tallest_m": round(report.tallest_m, 1),
        "skyline_triangles": report.skyline_triangles,
        "shore_triangles": report.shore_triangles,
        "sea_triangles": report.sea_triangles,
        "shore_m2": round(report.shore_m2, 1),
        "sea_m2": round(report.sea_m2, 1),
        "gap_m": round(report.gap_m, 1),
        "bytes": report.bytes,
    }
    write_document(out_dir / BACKDROP_MANIFEST_NAME, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the far shore (backdrop.glb) for a region.")
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    if not report.asset:
        log.info("backdrop: none — %s ships no far shore", args.region)
        return 0
    log.info(
        "backdrop: %d blocks read (%d with no level), %d tall -> %d drawn down to %.1f m "
        "(tallest %.1f m), %d skyline + %d shore + %d sea triangles, %d m off the frame",
        report.blocks_read,
        report.blocks_no_level,
        report.blocks_tall,
        report.blocks_drawn,
        report.min_height_drawn_m,
        report.tallest_m,
        report.skyline_triangles,
        report.shore_triangles,
        report.sea_triangles,
        report.gap_m,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
