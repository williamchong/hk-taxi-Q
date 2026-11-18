"""The harbour and the parks (2026-09-24, the user's call): the minimap's ground,
and since 2026-09-25 the water the world draws where the sea is.

What an ordinary GPS shows and this map did not — the water, first of all: in
Wan Chai the waterfront is the strongest landmark there is. Both classes are
read off the topographic map's sheets (`basemap:` in the city file), and
published as triangles in game plan metres for the minimap, which draws them
under its roads in one mesh. The sea is published a second time as `water.glb`
(the user's call, 2026-09-25): the same triangles, flat at `water_level_m`, one
mesh in `water_material`'s colour, drawn in the world by `region.tscn`'s
`Water` node. ⚠️ **The ground under it is the tile stage's business**: the
sheets' terrain over the harbour is not flat (1.1-4.2 m over Wan Chai's sea),
so `buildings._tile_ground` sinks every ground vertex inside this stage's sea
to `seabed_m` — which is why this stage runs BEFORE `buildings` (`__main__`),
reading only the sheets.

⚠️ **The sheets publish no sea polygon.** `HydroPolygon` is culverts, ponds and
streams; the harbour is the absence of land north of the shoreline. So the
frame — the region's read box and the map's reach around it — is cut along the
published shoreline (sea walls, high-water marks, breakwaters), and a piece is
sea where the published buildings cover none of it. The shoreline is surveyed
feature by feature and does not close — pier and shelter outlines are chains
whose vertices miss each other by fractions of a metre, and pier ends stop
~35 m short — so it is thickened by `seal_m` before the cut and the sea grown
back by the same half afterwards. ⚠️ Bridging each loose end instead was built
and refused: the chains dangle at dozens of sub-metre joins no nearest-line
rule closes. The price is an inlet narrower than `seal_m`, drawn as land.

⚠️ **A reach the fetch did not download is refused at load**
(`_check_basemap_reach_is_fetched`): past the last sheet there is no shoreline
and no building, and the missing sheet would read as open water.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry

from pipeline import gdb
from pipeline.config import Basemap, Config, SourceLayer, load_config
from pipeline.crs import GameTransform
from pipeline.documents import write_document
from pipeline.fetch import source_reads
from pipeline.geometry import wound_up
from pipeline.gltf import MeshData, write_glb
from pipeline.mesh import merge, select_triangles
from pipeline.meshbuild import MIN_TWICE_AREA_M2

log = logging.getLogger(__name__)


BASEMAP_NAME = "basemap.json"
# 2 since the world's water (2026-09-25): the document names `asset` — the
# water plane, or null where the frame holds no sea — and `water_level_m`, the
# height it is drawn at, which `verify_water.gd` holds the mesh to. A v1 reader
# ships a region without the plane.
#
# 3 since `P3-101` (`Q250`): `shoreline`, the published lines the sea was cut
# from, split into the built (`hard`) and the natural (`soft`). The tile stage
# cuts the ground along the sea's edge and reads from these which stretch is a
# wall; a v2 reader would slope every shore.
BASEMAP_SCHEMA = 3

# The water plane, in the region's bundle. ⚠️ **No `-col` suffix**: water is not
# a floor. The car that leaves the quay lands on the sunk ground under it.
WATER_NAME = "water.glb"
# glTF material name, the contract channel every drawn layer uses:
# `tools/generated_scene_import.gd` maps this string onto `tuning/water.tres`,
# and `verify_water.gd` checks that it did.
WATER_MATERIAL = "sea_water"
# The land no region's tiles draw (`P3-101`), a second mesh in `WATER_NAME`:
# `tuning/harbour_land.tres` by the same channel.
LAND_MESH_NAME = "harbour_land"
LAND_MATERIAL = "harbour_land"
# An edge of the land whose middle is this close to the sea is the sea's edge.
# The two are cut from one outline, so the distance is rounding.
_ON_SEA_M = 1e-3


@dataclass
class BasemapReport:
    # Pieces the shoreline cut the frame into, and how many were sea.
    pieces: int = 0
    sea_pieces: int = 0
    sea_m2: float = 0.0
    park_m2: float = 0.0
    shoreline_lines: int = 0
    park_polygons: int = 0
    water_triangles: int = 0
    park_triangles: int = 0
    # `WATER_NAME` where the frame held sea, else "".
    water_asset: str = ""
    # The plane's height, `basemap.water_level_m`; None with no block.
    water_level_m: float | None = None
    # The published shoreline as plan polylines, built (`hard`) and natural
    # (`soft`).
    shoreline: dict[str, list[list[float]]] = field(
        default_factory=lambda: {"hard": [], "soft": []}
    )
    # The land no region's tiles draw, and the length of the face under its
    # sea edge.
    land_m2: float = 0.0
    land_quay_m: float = 0.0
    land_triangles: int = 0


def frame_of(city: Config, region_id: str, reach_m: float) -> Polygon:
    """The region's read box and `reach_m` around it, in projected metres."""
    read = city.read_box(region_id)
    return box(
        read.min_easting - reach_m,
        read.min_northing - reach_m,
        read.max_easting + reach_m,
        read.max_northing + reach_m,
    )


def _layers(
    city: Config,
    spec: Basemap,
    region_id: str,
    layer: SourceLayer,
    frame: Polygon,
    sources_root: Path | None,
) -> list[gdb.Layer]:
    """`layer` from every sheet under the frame."""
    reads = source_reads(
        city,
        spec,
        region_id,
        root=sources_root,
        bounds=city.bounds_past(region_id, spec.reach_m),
    )
    return [
        gdb.read_layer(
            path,
            layer.layer,
            columns=layer.columns,
            bbox=frame.bounds,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        for path, member in reads
    ]


def read_shoreline(
    layers: list[gdb.Layer], spec: Basemap, types: frozenset[str] | None = None
) -> list[LineString]:
    """The shoreline lines whose published type bounds the sea, or only those
    of `types`."""
    wanted = spec.shoreline_types if types is None else types
    lines: list[LineString] = []
    for layer in layers:
        published = layer.column(spec.shoreline.field("type"))
        owners, parts = gdb.polylines(layer)
        for owner, points in zip(owners, parts, strict=True):
            if str(published[owner]) in wanted and len(points) > 1:
                lines.append(LineString(points))
    return lines


def polylines_of(
    lines: list[LineString], frame: Polygon, simplify_m: float, transform: GameTransform
) -> list[list[float]]:
    """`lines` inside `frame`, simplified, each `[x0, z0, x1, z1, ...]` in game
    plan metres: `triangles_of`'s terms, for a line."""
    if not lines:
        return []
    kept = shapely.union_all(lines).intersection(frame).simplify(simplify_m)
    found: list[list[float]] = []
    for part in shapely.get_parts(kept):
        if not isinstance(part, LineString) or part.length <= 0.0:
            continue
        points = np.asarray(part.coords)
        game_x, _, game_z = transform.to_game(points[:, 0], points[:, 1])
        flat: list[float] = []
        for x, z in zip(game_x, game_z, strict=True):
            flat.extend([round(float(x), 2), round(float(z), 2)])
        found.append(flat)
    return found


def read_polygons(
    layers: list[gdb.Layer], keep: frozenset[str] | None = None, column: str = ""
) -> list[Polygon]:
    """Every polygon part, or only those whose `column` value is in `keep`."""
    found: list[Polygon] = []
    for layer in layers:
        codes = None if keep is None else layer.column(column)
        owners, parts = gdb.polygons(layer)
        for owner, rings in zip(owners, parts, strict=True):
            if codes is not None and str(codes[owner]) not in keep:
                continue
            polygon = shapely.make_valid(Polygon(rings[0], rings[1:]))
            if not polygon.is_empty:
                found.append(polygon)
    return found


def sea_of(
    frame: Polygon,
    shoreline: list[LineString],
    buildings: list[Polygon],
    spec: Basemap,
    report: BasemapReport,
) -> BaseGeometry:
    """The pieces of `frame` the shoreline cuts off with no building on them.

    The shoreline is thickened by half of `seal_m` each side before the cut, so
    a gap narrower than `seal_m` closes; the sea is then grown back by the same
    half so it meets the line rather than stopping `seal_m / 2` short of it.
    """
    report.shoreline_lines = len(shoreline)
    if not shoreline:
        return Polygon()
    seam = shapely.union_all(shoreline).buffer(spec.seal_m * 0.5)
    built = shapely.union_all(buildings) if buildings else Polygon()
    pieces = shapely.get_parts(frame.difference(seam))
    report.pieces = len(pieces)
    sea = [
        piece for piece in pieces if piece.intersection(built).area <= spec.land_cover * piece.area
    ]
    report.sea_pieces = len(sea)
    if not sea:
        return Polygon()
    grown = shapely.union_all(sea).buffer(spec.seal_m * 0.5).intersection(frame)
    report.sea_m2 = float(grown.area)
    return grown


def read_sea(
    city: Config,
    region_id: str,
    report: BasemapReport,
    *,
    sources_root: Path | None = None,
) -> tuple[Polygon, BaseGeometry]:
    """A region's frame and the sea in it, in projected metres.

    The one reading of a region's harbour: `build_region` draws it, and
    `pipeline/backdrop.py` runs the far sea on from it — for the region and
    for each neighbour drawn beside it.
    """
    spec = city.basemap
    assert spec is not None
    frame = frame_of(city, region_id, spec.reach_m)
    shoreline = read_shoreline(
        _layers(city, spec, region_id, spec.shoreline, frame, sources_root), spec
    )
    buildings = read_polygons(_layers(city, spec, region_id, spec.buildings, frame, sources_root))
    return frame, sea_of(frame, shoreline, buildings, spec, report)


def simplified(geometry: BaseGeometry, simplify_m: float) -> BaseGeometry:
    """`geometry` as `triangles_of` cuts it: the outline the document
    publishes, and so the one anything drawn against it must be cut from."""
    return shapely.make_valid(geometry.simplify(simplify_m, preserve_topology=True))


def triangles_of(
    geometry: BaseGeometry, simplify_m: float, transform: GameTransform
) -> list[list[float]]:
    """`geometry` simplified and cut into triangles, each `[x0, z0, x1, z1, x2,
    z2]` in game plan metres. Holes survive: a constrained triangulation keeps
    Victoria Park's pond out of the park."""
    if geometry.is_empty:
        return []
    simple = simplified(geometry, simplify_m)
    triangles: list[list[float]] = []
    for part in shapely.get_parts(simple):
        if not isinstance(part, Polygon) or part.area <= 0.0:
            continue
        for triangle in shapely.get_parts(shapely.constrained_delaunay_triangles(part)):
            corners = np.asarray(triangle.exterior.coords)[:3]
            game_x, _, game_z = transform.to_game(corners[:, 0], corners[:, 1])
            flat: list[float] = []
            for x, z in zip(game_x, game_z, strict=True):
                flat.extend([round(float(x), 2), round(float(z), 2)])
            triangles.append(flat)
    return triangles


def water_mesh(
    triangles: list[list[float]], level_m: float, colour: tuple[int, int, int]
) -> MeshData | None:
    """The sea as one flat mesh at `level_m`, every triangle wound to face `+Y`
    and coloured `colour` on the vertex, or None with no sea.

    Vertices are not shared: the triangulation is the minimap's, in plan, and
    a flat plane has no shading seam to close. ⚠️ **Wound here, not trusted**:
    `triangles_of` publishes no winding — the map draws them flat — and a
    reversed triangle renders as *nothing* under `cull_back`.
    """
    if not triangles:
        return None
    rings = [wound_up(np.asarray(flat, dtype=np.float64).reshape(3, 2)) for flat in triangles]
    plan = np.vstack(rings)
    positions = np.column_stack([plan[:, 0], np.full(len(plan), level_m), plan[:, 1]])
    count = len(positions)
    mesh = MeshData(
        name="water",
        positions=positions,
        normals=np.tile(np.array([0.0, 1.0, 0.0], dtype=np.float32), (count, 1)),
        triangles=np.arange(count, dtype=np.uint32).reshape(-1, 3),
        colours=np.tile(np.array([*colour, 255], dtype=np.uint8), (count, 1)),
        material=WATER_MATERIAL,
    )
    # A simplified sliver can collapse to nothing at the glb's float32; drop it
    # rather than ship a triangle `check_faces_up` cannot judge. The bar is
    # shared: see `meshbuild.MIN_TWICE_AREA_M2`.
    twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
    return select_triangles(mesh, twice_area > MIN_TWICE_AREA_M2)


def land_of(frame: Polygon, sea: BaseGeometry, drawn: list[Polygon], spec: Basemap) -> BaseGeometry:
    """The land in `frame` within `land_within_m` of `sea` that lies in none of
    `drawn`, the regions' own boxes. `sea` is the published outline
    (`simplified`), so the land's edge is the water's edge and not a second
    simplification of it."""
    if sea.is_empty:
        return Polygon()
    near = sea.buffer(spec.land_within_m, quad_segs=4)
    return frame.intersection(near).difference(shapely.union_all([sea, *drawn]))


def land_mesh(
    land: BaseGeometry,
    sea: BaseGeometry,
    transform: GameTransform,
    spec: Basemap,
    report: BasemapReport,
) -> MeshData | None:
    """`land` as one mesh: flat at `land_level_m` in `land_material`, and under
    every edge it shares with `sea` a face down to `seabed_m` in
    `quay_material`, looking out to sea. None with no land.

    ⚠️ **Every sea edge is a face**, a high-water mark's too: the tiles slope a
    natural shore on the sheets' terrain (`pipeline/shore.py`), and out here no
    terrain is read."""
    top = water_mesh(
        triangles_of(land, 0.0, transform), spec.land_level_m, spec.land_material.colour
    )
    if top is None:
        return None
    report.land_m2 = float(land.area)
    # The way `water_mesh` wound the top about `+Y`: a face is wound the same
    # way about the direction it looks.
    wound = np.sign(top.triangle_cross()[0, 1])
    corners: list[np.ndarray] = []
    facings: list[np.ndarray] = []
    for polygon in shapely.get_parts(land):
        if not isinstance(polygon, Polygon):
            continue
        for ring in (polygon.exterior, *polygon.interiors):
            points = np.asarray(ring.coords)[:, :2]
            middles = 0.5 * (points[:-1] + points[1:])
            on_sea = shapely.distance(shapely.points(middles), sea) < _ON_SEA_M
            for at in np.flatnonzero(on_sea):
                step = points[at + 1] - points[at]
                length = float(np.hypot(*step))
                if length <= 0.0:
                    continue
                # Out of the land, in the sheet's plan; game z runs south.
                out = np.array([step[1], -step[0]]) / length
                if polygon.contains(shapely.Point(*(middles[at] + _ON_SEA_M * 10.0 * out))):
                    out = -out
                facing = np.array([out[0], 0.0, -out[1]])
                x, _, z = transform.to_game(points[at : at + 2, 0], points[at : at + 2, 1])
                x, z = np.round(x, 2), np.round(z, 2)
                high = [[x[0], spec.land_level_m, z[0]], [x[1], spec.land_level_m, z[1]]]
                low = [[x[1], spec.seabed_m, z[1]], [x[0], spec.seabed_m, z[0]]]
                for face in (
                    np.array([high[0], high[1], low[0]]),
                    np.array([high[0], low[0], low[1]]),
                ):
                    cross = np.cross(face[1] - face[0], face[2] - face[0])
                    corners.append(face if np.sign(cross @ facing) == wound else face[::-1])
                    facings.append(facing)
                report.land_quay_m += length
    if not corners:
        return replace(top, name=LAND_MESH_NAME, material=LAND_MATERIAL)
    positions = np.concatenate(corners)
    count = len(positions)
    walls = MeshData(
        name=LAND_MESH_NAME,
        positions=positions,
        normals=np.repeat(np.array(facings), 3, axis=0).astype(np.float32),
        triangles=np.arange(count, dtype=np.uint32).reshape(-1, 3),
        colours=np.tile(np.array([*spec.quay_material.colour, 255], dtype=np.uint8), (count, 1)),
    )
    return replace(merge([top, walls], name=LAND_MESH_NAME), material=LAND_MATERIAL)


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> BasemapReport:
    """Read the region's shoreline, buildings and parks; write `basemap.json`
    and, where the frame held sea, `water.glb`."""
    report = BasemapReport()
    out_dir = city.out_dir(region_id, out_root)
    spec = city.basemap
    if spec is None:
        # Written anyway, empty, so the manifest can name it unconditionally and
        # a missing file still means the stage never ran.
        write_document(out_dir / BASEMAP_NAME, _document(city.id, region_id, [], [], report))
        return report
    transform = city.game_transform(region_id)
    frame, sea = read_sea(city, region_id, report, sources_root=sources_root)

    parks = read_polygons(
        _layers(city, spec, region_id, spec.parks, frame, sources_root),
        spec.park_codes,
        spec.parks.field("code"),
    )
    report.park_polygons = len(parks)
    green = shapely.union_all(parks).intersection(frame).difference(sea) if parks else Polygon()
    report.park_m2 = float(green.area)

    water = triangles_of(sea, spec.simplify_m, transform)
    park = triangles_of(green, spec.simplify_m, transform)
    shores = _layers(city, spec, region_id, spec.shoreline, frame, sources_root)
    soft_types = spec.shoreline_types - spec.hard_shoreline_types
    report.shoreline = {
        kind: polylines_of(read_shoreline(shores, spec, types), frame, spec.simplify_m, transform)
        for kind, types in (("hard", spec.hard_shoreline_types), ("soft", soft_types))
    }
    report.water_triangles = len(water)
    report.park_triangles = len(park)

    report.water_level_m = spec.water_level_m
    plane = water_mesh(water, spec.water_level_m, spec.water_material.colour)
    if plane is not None:
        outline = simplified(sea, spec.simplify_m)
        tiled = [box(*city.projected_bounds(other).bbox) for other in city.drivable_regions]
        land = land_mesh(land_of(frame, outline, tiled, spec), outline, transform, spec, report)
        if land is not None:
            report.land_triangles = land.triangle_count
        write_glb(out_dir / WATER_NAME, [plane] if land is None else [plane, land])
        report.water_asset = WATER_NAME
    else:
        # Named from what was drawn, never from the constant: a stale plane
        # beside a document that says "no sea" is the state `sync_generated.sh`
        # sweeps, and one this stage must not leave behind.
        (out_dir / WATER_NAME).unlink(missing_ok=True)
    write_document(out_dir / BASEMAP_NAME, _document(city.id, region_id, water, park, report))
    return report


def _document(
    city_id: str,
    region_id: str,
    water: list[list[float]],
    parks: list[list[float]],
    report: BasemapReport,
) -> dict:
    return {
        "schema_version": BASEMAP_SCHEMA,
        "city_id": city_id,
        "region_id": region_id,
        # Triangles `[x0, z0, x1, z1, x2, z2]` in this region's game plan metres,
        # in no particular winding — the minimap draws them flat, uncelled.
        "water": water,
        "parks": parks,
        # The world's water plane: `water.glb`, or null where the frame held no
        # sea (`tramway`'s terms — named from what was drawn). Flat at
        # `water_level_m`, which the engine-side check holds it to.
        "asset": report.water_asset or None,
        "water_level_m": report.water_level_m,
        # The lines the sea was cut from, each `[x0, z0, x1, z1, ...]` in game
        # plan metres: `hard` a sea wall or a breakwater, `soft` a high-water
        # mark. `pipeline/shore.py` reads which stretch of the sea's edge is a
        # wall from the nearer of the two.
        "shoreline": report.shoreline,
        "report": {
            "pieces": report.pieces,
            "sea_pieces": report.sea_pieces,
            "sea_m2": round(report.sea_m2, 1),
            "park_m2": round(report.park_m2, 1),
            "shoreline_lines": report.shoreline_lines,
            "park_polygons": report.park_polygons,
            # The land no region's tiles draw, a second mesh in the asset.
            "land_m2": round(report.land_m2, 1),
            "land_quay_m": round(report.land_quay_m, 1),
            "land_triangles": report.land_triangles,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)
    report = build_region(city, args.region)
    log.info(
        "  sea: %d of %d pieces, %.0f m² off %d shoreline lines -> %d triangles",
        report.sea_pieces,
        report.pieces,
        report.sea_m2,
        report.shoreline_lines,
        report.water_triangles,
    )
    log.info(
        "  parks: %d polygons, %.0f m² -> %d triangles",
        report.park_polygons,
        report.park_m2,
        report.park_triangles,
    )
    log.info(
        "  water plane: %s",
        f"{report.water_asset}, {report.water_triangles} triangles"
        if report.water_asset
        else "none — no sea in the frame",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
