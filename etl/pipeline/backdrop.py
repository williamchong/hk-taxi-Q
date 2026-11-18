"""A region's far version (`P3-100`, `Q249`): what another region sees of it
past the camera's 400 m far plane, where its tiles are never loaded, as
`backdrop.glb` in the region's own frame.

The far plane stays 400 m (measured: raising it brought the streamed city into
the frustum, +70% primitives), so the far version is drawn past it by
`far_shore.gdshaderinc` and skipped nearer than it, where the region's own
tiles stand. Every declared region ships one; a `far_only` region (Tsim Sha
Tsui) ships nothing else. No roads, no collider, no shadow. Three parts, two
meshes:

- **The skyline**: each block of the topographic map's `Building` layer whose
  centre is in the region's `bounds`, extruded from the far version's ground
  to its published roof level. Only blocks at least `min_height_m` tall, and
  no more than `triangle_cap` triangles of them: over the cap the shortest go
  first, and the manifest says what height was drawn down to.
- **The shore**: one flat slab at `ground_level_m` under everything published
  in the box — every footprint and every sea wall, closed over gaps up to
  twice `ground_close_m` and filled.
- **The far sea**: for a driven region, the basemap's own sea in its frame a
  second time, because the far plane cuts the basemap's water off 400 m from
  the camera, which on a diagonal is short of the frame's edge; and for every
  region the open water round it, out to `sea_reach_m`: what is not land
  there, in no driven region's frame, and joined to a frame's sea. Nearer than
  the far plane the basemap's water is in front of its copy.

⚠️ **The shore is not the basemap's cut** (`basemap.sea_of`), which needs a
shoreline that separates land from sea. Over Kowloon the published one does
not: West Kowloon's waterfront and east Tsim Sha Tsui's are gaps of several
hundred metres, and the cut finds one piece. So the shore is where things
stand, and an unbuilt waterfront wider than the closing is sea.

⚠️ **The open water is not a survey.** Outside every frame it is the reach less
what stands there, so an unbuilt place wider than the closing that touches the
harbour reads as water from across the map.

    python -m pipeline.backdrop --region wan_chai
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry

from pipeline import basemap, gdb
from pipeline.config import Backdrop, Config, SourceLayer, load_config
from pipeline.crs import GameTransform
from pipeline.documents import write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.meshbuild import ColouredBuilder, prism

log = logging.getLogger(__name__)

BACKDROP_NAME = "backdrop.glb"
BACKDROP_MANIFEST_NAME = "backdrop.json"
# 2 since every region ships its own far version (`Q249` amended): the asset is
# the region's, not the far shore across from it, and the manifest carries the
# region's `city_offset` and `far_only`, which place a far-only one in the game.
BACKDROP_MANIFEST_SCHEMA = 2
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

# How near a piece of open water must come to a frame's sea to be joined to it:
# the two meet on the frame's edge, and the difference leaves a float's width.
_JOIN_M = 1.0


@dataclass(frozen=True)
class Block:
    """One published building block: its footprint in projected metres, its
    roof level and how tall it stands over its own base."""

    footprint: Polygon
    roof_m: float
    height_m: float
    # Whether the building it is part of is centred in the region's own box:
    # the region's skyline is its own, the rest only closes its shore.
    mine: bool = True

    @property
    def triangles(self) -> int:
        """What `prism` draws of it: two a wall segment, and a roof."""
        rings = (self.footprint.exterior, *self.footprint.interiors)
        corners = sum(len(ring.coords) - 1 for ring in rings)
        return 3 * corners - 2 + 2 * len(self.footprint.interiors)


@dataclass
class BackdropReport:
    # Building parts in the region's box, and those with no usable level.
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
    # Of `sea_m2`, the water outside every driven region's frame.
    open_sea_m2: float = 0.0
    # The driven regions whose frame's sea the open water was joined to.
    seas_read: list[str] = field(default_factory=list)
    asset: str = ""
    bytes: int = 0


def _layers(
    city: Config,
    spec: Backdrop,
    region_id: str,
    layer: SourceLayer,
    reach: Polygon,
    sources_root: Path | None,
) -> list[gdb.Layer]:
    """`layer` from every sheet under the region and its sea reach."""
    bounds = city.bounds_past(region_id, spec.sea_reach_m)
    reads = source_reads(city, spec, region_id, root=sources_root, bounds=bounds)
    return [
        gdb.read_layer(
            path,
            layer.layer,
            columns=layer.columns,
            bbox=reach.bounds,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        for path, member in reads
    ]


def read_blocks(
    layers: list[gdb.Layer],
    spec: Backdrop,
    reach: Polygon,
    own: Polygon,
    report: BackdropReport,
) -> list[Block]:
    """Every building part whose centre is inside `reach` and whose levels are
    published, thinned to `simplify_m`. Each is marked `mine` where its
    building is centred in `own`, the region's box, and the report counts those.

    ⚠️ **Kept by its centre, never clipped**: a sheet's read box hands back the
    blocks that straddle it, and the same block from two sheets is one block.
    """
    seen: set[tuple[float, float, float]] = set()
    shapely.prepare(reach)
    shapely.prepare(own)
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
            if key in seen or not reach.contains(centre):
                continue
            seen.add(key)
            mine = own.contains(centre)
            report.blocks_read += mine
            height = float(roof[owner] - base[owner])
            if not np.isfinite(height) or height <= 0.0:
                report.blocks_no_level += mine
                continue
            simple = footprint.simplify(spec.simplify_m, preserve_topology=True)
            for part in shapely.get_parts(shapely.make_valid(simple)):
                if isinstance(part, Polygon) and part.area > 0.0:
                    blocks.append(Block(part, float(roof[owner]), height, mine))
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


def ground_of(blocks: list[Block], shoreline: list[LineString], spec: Backdrop) -> BaseGeometry:
    """The ground everything published stands on: the footprints and the sea
    walls, closed by `ground_close_m` and filled.

    Filled, because a park inland is a hole in what is built and not a lake.
    """
    stood = shapely.union_all([block.footprint for block in blocks] + shoreline)
    closed = stood.buffer(spec.ground_close_m).buffer(-spec.ground_close_m)
    filled = [
        Polygon(part.exterior)
        for part in shapely.get_parts(closed)
        if isinstance(part, Polygon) and not part.is_empty
    ]
    return shapely.union_all(filled) if filled else Polygon()


def shore_of(area: Polygon, ground: BaseGeometry, spec: Backdrop) -> BaseGeometry:
    """`ground` inside `area`, thinned to `simplify_m`: the slab drawn there."""
    shore = ground.intersection(area)
    return shapely.make_valid(shore.simplify(spec.simplify_m, preserve_topology=True))


def open_sea_of(
    reach: Polygon, land: BaseGeometry, frames: list[Polygon], seas: list[BaseGeometry]
) -> BaseGeometry:
    """The water in `reach` outside every one of `frames`: what is not `land`
    there, kept where it joins one of `seas`.

    Joined, so an unbuilt square inland is not water: only what runs on from a
    frame's published sea is. ⚠️ Inside a frame it is nothing — the frame's own
    region ships that sea — and run under the land there it would floor the far
    end of every street the far plane cuts short.
    """
    known = shapely.union_all(seas) if seas else Polygon()
    if known.is_empty:
        return Polygon()
    outside = reach.difference(land).difference(shapely.union_all(frames))
    touching = known.buffer(_JOIN_M)
    shapely.prepare(touching)
    return shapely.union_all(
        [part for part in shapely.get_parts(outside) if touching.intersects(part)]
    )


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
    """Write the region's far version, `backdrop.glb`, and its manifest."""
    report = BackdropReport()
    out_dir = city.out_dir(region_id, out_root)
    spec, harbour = city.backdrop, city.basemap
    meshes: list[MeshData] = []
    if spec is not None and harbour is not None:
        own = box(*city.projected_bounds(region_id).bbox)
        reach = basemap.frame_of(city, region_id, spec.sea_reach_m)
        # The sea of every driven region whose frame the reach meets, this
        # region's own among them: the open water is joined to these, and the
        # frames are where it is not drawn.
        frames, seas = [], []
        own_sea: BaseGeometry = Polygon()
        for other_id in city.drivable_regions:
            if not basemap.frame_of(city, other_id, harbour.reach_m).intersects(reach):
                continue
            framed, sea = basemap.read_sea(
                city, other_id, basemap.BasemapReport(), sources_root=sources_root
            )
            frames.append(framed)
            seas.append(sea)
            report.seas_read.append(other_id)
            if other_id == region_id:
                own_sea = sea
        blocks = read_blocks(
            _layers(city, spec, region_id, spec.buildings, reach, sources_root),
            spec,
            reach,
            own,
            report,
        )
        shoreline = basemap.read_shoreline(
            _layers(city, spec, region_id, harbour.shoreline, reach, sources_root), harbour
        )
        # Closed once over the whole reach, so the region's own slab meets the
        # land beside it where the closing runs across its box's edge.
        ground = ground_of(blocks, shoreline, spec)
        shore = shore_of(own, ground, spec)
        open_sea = open_sea_of(reach, shore_of(reach, ground, spec), frames, seas)
        far_sea = shapely.union_all([own_sea, open_sea])
        report.shore_m2 = float(shore.area)
        report.sea_m2 = float(far_sea.area)
        report.open_sea_m2 = float(open_sea.area)
        transform = city.game_transform(region_id)
        meshes = build_meshes(
            skyline_of([block for block in blocks if block.mine], spec, report),
            shore,
            far_sea,
            city,
            transform,
            report,
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
        # Seen and never driven: the game places this region by the offset
        # below, since it has no `city.json` to read it from.
        "far_only": city.region(region_id).far_only,
        "city_offset": [round(value, 3) for value in city.city_offset(region_id)],
        # `backdrop.glb`, or null where the city declares no `backdrop:` block.
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
        "open_sea_m2": round(report.open_sea_m2, 1),
        "seas_read": report.seas_read,
        "bytes": report.bytes,
    }
    write_document(out_dir / BACKDROP_MANIFEST_NAME, document)


def built(city: Config, out_root: Path | None = None) -> list[str]:
    """The declared regions whose far version this stage has written at this
    schema, in declaration order: what the game can draw of a region it does
    not hold, a far-only one or a driven one not synced."""
    found = []
    for region_id in city.regions:
        manifest = city.out_dir(region_id, out_root) / BACKDROP_MANIFEST_NAME
        if not manifest.is_file():
            continue
        document = json.loads(manifest.read_text(encoding="utf-8"))
        if document.get("schema_version") == BACKDROP_MANIFEST_SCHEMA and document.get("asset"):
            found.append(region_id)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a region's far version (backdrop.glb).")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--region")
    target.add_argument(
        "--built",
        action="store_true",
        help="print the regions whose far version is built at this schema, one a line, and stop",
    )
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    if args.built:
        # For `tools/sync_generated.sh`, which ships these beside the regions
        # it is asked for: stdout is the list, so nothing else is printed there.
        for region_id in built(city, args.out_root):
            print(region_id)
        return 0
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    if not report.asset:
        log.info("backdrop: none — the city declares no backdrop: block")
        return 0
    log.info(
        "backdrop: %d blocks read (%d with no level), %d tall -> %d drawn down to %.1f m "
        "(tallest %.1f m), %d skyline + %d shore + %d sea triangles, %.2f km² of open sea",
        report.blocks_read,
        report.blocks_no_level,
        report.blocks_tall,
        report.blocks_drawn,
        report.min_height_drawn_m,
        report.tallest_m,
        report.skyline_triangles,
        report.shore_triangles,
        report.sea_triangles,
        report.open_sea_m2 / 1e6,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
