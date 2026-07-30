"""Source massing to per-tile, vertex-coloured GLB (`P1-2`).

Reads the LandsD non-textured glTF sheets a previous fetch cached, moves them
into the region's game frame, colours each building by height band and class,
buckets them into tiles, and writes one merged mesh per tile per LOD tier.

Merging is the whole point. Untextured, vertex-coloured buildings share a single
material, so a tile's 300-odd buildings collapse into one primitive and one draw
call — which is why the untextured dataset was chosen over the photogrammetry
one (`docs/DATA_SOURCES.md`).

Sheets are read straight out of their zips. Unpacking six of them costs ~400 MB
on disk to produce input that is read once.

Nothing here knows anything about any particular city: sheet layout, palette and
LOD cell sizes all arrive from `config/cities/*.yaml`.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from zlib import crc32

import numpy as np
from numpy.typing import ArrayLike

from pipeline.config import BuildingStyle, CityConfig, RegionConfig, load_city
from pipeline.crs import GameTransform
from pipeline.fetch import artefact_path, cached_tiles
from pipeline.gltf import Bounds, MeshData, read_scene, write_glb
from pipeline.mesh import EmptyMeshError, collapse, merge, select_triangles

log = logging.getLogger(__name__)

OUT_ROOT = Path(__file__).resolve().parent.parent / "out"

# The config key for the tiled source that carries massing. A stage name rather
# than a city fact — `fetch.py --only buildings` names the same thing.
SOURCE_ID = "buildings"

# Named for what it holds, not for `fetch.py`'s `manifest.json`, which is a
# different file with a different job.
BUILDINGS_MANIFEST_NAME = "buildings.json"
BUILDINGS_MANIFEST_SCHEMA = 2


@dataclass(frozen=True)
class LodOutput:
    """One tier of one tile. Its position in `TileOutput.lods` is its level.

    A tile can have fewer tiers than there are configured cell sizes: once
    everything in it is smaller than the cell, no coarser tier has anything to
    draw. Consumers must read the list, not index it.
    """

    path: str
    triangles: int
    vertices: int
    bytes: int


@dataclass(frozen=True)
class TileOutput:
    id: str
    ix: int
    iz: int
    meshes: int
    aabb: Bounds
    lods: list[LodOutput]


@dataclass
class BuildReport:
    tiles: list[TileOutput] = field(default_factory=list)
    # Source meshes seen, and how many landed nowhere. Sheets overlap the region
    # rather than matching it, so a large `clipped` is expected — but a `read`
    # of zero, or a `clipped` equal to it, is the wrong-bounds failure.
    read: int = 0
    clipped: int = 0


# --------------------------------------------------------------------------
# Reading sheets
# --------------------------------------------------------------------------


def read_sheet(path: Path, classes: tuple[str, ...]) -> Iterator[tuple[str, MeshData]]:
    """Every `(class, mesh)` in the given sub-directories of one sheet zip.

    Coordinates come back in the source CRS, on Godot's axes — see
    `game_offset`. A generator because a sheet unpacks to ~65 MB and only one
    mesh at a time is needed.
    """
    prefixes = tuple(f"{name}/" for name in classes)
    with zipfile.ZipFile(path) as archive:
        # Sorted so a rerun writes byte-identical tiles: merge order decides
        # vertex order, and an unstable order makes every output look changed.
        members = sorted(
            name
            for name in archive.namelist()
            if name.startswith(prefixes) and name.lower().endswith(".gltf")
        )
        for member in members:
            class_id = member.split("/", 1)[0]
            directory = str(PurePosixPath(member).parent)
            for mesh in read_scene(archive.read(member), _resolver(archive, directory)):
                yield class_id, mesh


def _resolver(archive: zipfile.ZipFile, directory: str) -> Callable[[str], bytes]:
    """Resolve a glTF's relative URIs against its own directory in the zip."""
    return lambda uri: archive.read(f"{directory}/{unquote(uri)}")


# --------------------------------------------------------------------------
# Placement and colour
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Grid:
    """The region's tile grid, in game-space metres."""

    tile_size_m: float
    max_x: float
    max_z: float

    @classmethod
    def for_region(cls, city: CityConfig, region: RegionConfig) -> Grid:
        bounds = city.projected_bounds(region.id)
        # Through `GameTransform` rather than subtracting the origin here. The
        # origin is at the NW corner and the Z flip is forced by handedness, so
        # writing the far corner out by hand means restating a sign convention
        # `crs.py` documents as not a free choice — in a second place, where it
        # can drift.
        max_x, _, max_z = city.game_transform(region.id).to_game(
            bounds.max_easting, bounds.min_northing
        )
        return cls(tile_size_m=region.tile_size_m, max_x=max_x, max_z=max_z)

    @property
    def columns(self) -> int:
        return max(1, math.ceil(self.max_x / self.tile_size_m))

    @property
    def rows(self) -> int:
        return max(1, math.ceil(self.max_z / self.tile_size_m))

    def contains(self, x: ArrayLike, z: ArrayLike) -> np.ndarray:
        """Whether each game-space point lies in the region. Scalars welcome."""
        x, z = np.asarray(x), np.asarray(z)
        return (x >= 0.0) & (x <= self.max_x) & (z >= 0.0) & (z <= self.max_z)

    def index(self, x: ArrayLike, z: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
        """Tile column and row for points already known to be inside.

        Clamped because a point exactly on the far edge divides to one past the
        last tile — the same off-by-one that puts the easternmost buildings in a
        column that does not exist.
        """
        return (
            np.minimum(np.asarray(x) // self.tile_size_m, self.columns - 1).astype(int),
            np.minimum(np.asarray(z) // self.tile_size_m, self.rows - 1).astype(int),
        )


def assign(
    mesh: MeshData, grid: Grid, bounds: Bounds | None = None
) -> Iterator[tuple[tuple[int, int], MeshData]]:
    """Place a mesh into the tiles it belongs to, dropping what falls outside.

    `bounds` is the mesh's AABB when the caller already has it, purely to avoid
    a second full pass over the positions.

    Buildings are assigned **whole**, by their centre, and so may overhang their
    tile by half a footprint. That is deliberate: split at the boundary they
    become open shells, and half a building would pop in and out as the streamer
    loads one tile and not its neighbour.

    A mesh too large to fit a tile at all cannot be assigned that way, and the
    source has plenty — an elevated road structure here runs to **two
    kilometres** in a single mesh. Whole-mesh assignment either drops one whose
    centre happens to lie outside the region, taking a viaduct that crosses the
    whole map with it, or keeps it and gives one 150 m tile a 2 km bounding box
    that defeats distance-based streaming. So those are partitioned by triangle
    instead. Nothing is cut, so the pieces abut exactly.
    """
    low, high = bounds if bounds is not None else mesh.aabb()
    if high[0] - low[0] <= grid.tile_size_m and high[2] - low[2] <= grid.tile_size_m:
        centre_x, centre_z = (low[0] + high[0]) / 2, (low[2] + high[2]) / 2
        if grid.contains(centre_x, centre_z):
            ix, iz = grid.index(centre_x, centre_z)
            yield (int(ix), int(iz)), mesh
        return

    centroids = mesh.triangle_centroids()
    inside = grid.contains(centroids[:, 0], centroids[:, 2])
    columns, rows = grid.index(centroids[:, 0], centroids[:, 2])
    for ix, iz in {(int(c), int(r)) for c, r in zip(columns[inside], rows[inside], strict=True)}:
        piece = select_triangles(mesh, inside & (columns == ix) & (rows == iz))
        if piece is not None:
            yield (ix, iz), piece


def game_offset(transform: GameTransform) -> np.ndarray:
    """Translation from LandsD sheet coordinates into the region's game frame.

    The sheets are already on Godot's axes — each node translates to
    `(easting, elevation, -northing)`, exactly the convention in
    `docs/ARCHITECTURE.md` — so this leg is a translation with no axis work.
    Taken from `GameTransform` rather than written out, so it cannot drift from
    the definition the rest of the pipeline and `city.json` share.
    """
    return np.asarray(transform.to_game(0.0, 0.0, 0.0), dtype=np.float64)


def colour_for(
    style: BuildingStyle, class_id: str, mesh: MeshData, bounds: Bounds | None = None
) -> np.ndarray:
    """One RGBA row per vertex: the class or height-band colour, jittered.

    Jitter is seeded from the mesh name — the LandsD building id — via `crc32`
    rather than `hash`, which is salted per process and would repaint the city
    on every run.
    """
    low, high = bounds if bounds is not None else mesh.aabb()
    red, green, blue = style.colour_for(class_id, high[1] - low[1])

    if style.colour_jitter > 0.0:
        unit = crc32(mesh.name.encode("utf-8")) / 0x1_0000_0000
        factor = 1.0 + style.colour_jitter * (2.0 * unit - 1.0)
        red, green, blue = (
            min(255, max(0, round(channel * factor))) for channel in (red, green, blue)
        )

    # A read-only broadcast view, not 4 bytes repeated a million times. `merge`
    # and `select_triangles` materialise it where it is actually needed.
    return np.broadcast_to(
        np.array([red, green, blue, 255], dtype=np.uint8), (len(mesh.positions), 4)
    )


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Placement:
    """Everything both stages need to put a sheet's geometry in the region.

    Both `build_region` and `build_terrain` start by resolving the same
    things from the same two arguments; sharing that is what stops the two
    stages disagreeing about where the region is.
    """

    region: RegionConfig
    grid: Grid
    offset: np.ndarray
    out_dir: Path
    sheets: list[tuple[str, Path]]

    @classmethod
    def resolve(
        cls, city: CityConfig, region_id: str, sources_root: Path | None, out_root: Path | None
    ) -> Placement:
        region = city.region(region_id)
        tiles = cached_tiles(city, region, city.tiled_sources[SOURCE_ID], root=sources_root)
        return cls(
            region=region,
            grid=Grid.for_region(city, region),
            offset=game_offset(city.game_transform(region_id)),
            out_dir=(out_root or OUT_ROOT) / city.id / region_id,
            sheets=[
                (sheet.tile_id, artefact_path(city.id, sheet, root=sources_root)) for sheet in tiles
            ],
        )


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> BuildReport:
    """Write every tile of the region, at every LOD tier, and report on them."""
    style = city.buildings
    place = Placement.resolve(city, region_id, sources_root, out_root)

    report = BuildReport()
    buckets: dict[tuple[int, int], list[MeshData]] = {}

    for sheet_id, sheet_path in place.sheets:
        kept = 0
        for class_id, mesh in read_sheet(sheet_path, style.classes):
            report.read += 1
            placed = mesh.translated(place.offset)
            bounds = placed.aabb()
            # Colour comes from the whole mesh's height, before any splitting,
            # so a viaduct partitioned across four tiles stays one colour.
            coloured = replace(placed, colours=colour_for(style, class_id, placed, bounds))
            placements = list(assign(coloured, place.grid, bounds))
            for tile, piece in placements:
                buckets.setdefault(tile, []).append(piece)
            if placements:
                kept += 1
            else:
                report.clipped += 1
        log.info("  %-12s %4d kept", sheet_id, kept)

    if not buckets:
        raise ValueError(
            f"region '{region_id}' produced no tiles. Every source mesh fell outside the "
            f"region bounds — check that the sheets on disk are the ones the bounds select."
        )

    # Popped as they are written so the bucket payload — 133 MB for Wan Chai —
    # decays across the write stage instead of all staying live to the end.
    for tile in sorted(buckets):
        report.tiles.append(_write_tile(place.out_dir, tile, buckets.pop(tile), style))

    _write_manifest(place.out_dir, city, place.region, place.grid, report)
    return report


def _write_tile(
    out_dir: Path, tile: tuple[int, int], meshes: list[MeshData], style: BuildingStyle
) -> TileOutput:
    ix, iz = tile
    tile_id = f"t_{ix:02d}_{iz:02d}"
    merged = merge(meshes, name=tile_id)

    lods: list[LodOutput] = []
    for level, cell_m in enumerate(style.lod_cell_sizes_m):
        try:
            tier = collapse(merged, cell_m=cell_m)
        except EmptyMeshError:
            # Everything in this tile is smaller than the cell. Correct at LOD2
            # for a tile holding one sign gantry — but the tiers coarsen, so
            # every later one vanishes too, and a tile with nothing left to draw
            # at 400 m must not take the whole region's build down with it.
            log.info("  %s: nothing survives LOD%d (%.1f m cells)", tile_id, level, cell_m)
            break

        relative = Path("tiles") / f"{tile_id}_lod{level}.glb"
        size = write_glb(out_dir / relative, [tier])
        lods.append(
            LodOutput(
                path=relative.as_posix(),
                triangles=tier.triangle_count,
                vertices=len(tier.positions),
                bytes=size,
            )
        )

    return TileOutput(
        id=tile_id,
        ix=ix,
        iz=iz,
        meshes=len(meshes),
        aabb=merged.aabb(),
        lods=lods,
    )


def _write_manifest(
    out_dir: Path, city: CityConfig, region: RegionConfig, grid: Grid, report: BuildReport
) -> None:
    """An intermediate for `P1-6`, not the game-facing contract.

    `city.json` is `export.py`'s to write and has to reconcile roads and fares
    too. This file records only what the building stage knows, so the two stages
    stay independently runnable.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / BUILDINGS_MANIFEST_NAME).write_text(
        json.dumps(
            {
                "schema_version": BUILDINGS_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": region.id,
                "tile_size_m": grid.tile_size_m,
                "grid": {"columns": grid.columns, "rows": grid.rows},
                "lod_cell_sizes_m": list(city.buildings.lod_cell_sizes_m),
                "tiles": [asdict(tile) for tile in report.tiles],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# Terrain — evaluation output only
# --------------------------------------------------------------------------


def build_terrain(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> list[tuple[str, int, int]]:
    """Emit each sheet's textured ground mesh, clipped to the region.

    Not part of the tile output, and deliberately not merged into it: the ground
    ships with a 45-megapixel JPEG per sheet, and the building tiles are
    specified to contain no textures at all. This exists so the terrain can be
    judged in Godot beside the massing — z-fighting against the `P1-4` road
    ribbon, and whether photographic ground reads wrong next to flat-shaded
    volumes — with the texture cost measured rather than guessed.

    Returns `(sheet, triangles, bytes)` per sheet.
    """
    place = Placement.resolve(city, region_id, sources_root, out_root)
    out_dir = place.out_dir / "terrain"

    results: list[tuple[str, int, int]] = []
    for sheet_id, sheet_path in place.sheets:
        meshes = [
            clipped
            for _, mesh in read_sheet(sheet_path, (city.buildings.terrain_class,))
            if (clipped := _clip_triangles(mesh.translated(place.offset), place.grid)) is not None
        ]
        if not meshes:
            log.info("  %-12s no terrain inside the region", sheet_id)
            continue
        size = write_glb(out_dir / f"{sheet_id}.glb", meshes)
        triangles = sum(mesh.triangle_count for mesh in meshes)
        results.append((sheet_id, triangles, size))
        log.info("  %-12s %7d triangles, %6.1f MB", sheet_id, triangles, size / 1e6)
    return results


def _clip_triangles(mesh: MeshData, grid: Grid) -> MeshData | None:
    """Drop triangles whose centroid falls outside the region.

    Per triangle rather than per mesh, because a sheet's terrain is one mesh
    spanning 750 m and the region takes a bite out of it. Vertices are left
    alone, so UVs stay valid against the sheet's own texture and the cut edge
    can overhang the region by up to a triangle.
    """
    centroids = mesh.triangle_centroids()
    return select_triangles(mesh, grid.contains(centroids[:, 0], centroids[:, 2]))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--terrain",
        action="store_true",
        help="also emit each sheet's textured ground mesh, for evaluation (see build_terrain)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    report = build_region(city, args.region)
    log.info(
        "%d meshes read, %d clipped away, %d tiles written",
        report.read,
        report.clipped,
        len(report.tiles),
    )
    for level, cell_m in enumerate(city.buildings.lod_cell_sizes_m):
        # Not every tile reaches every tier — see `LodOutput`.
        tiers = [tile.lods[level] for tile in report.tiles if level < len(tile.lods)]
        log.info(
            "  LOD%d (%.1f m cells): %8d triangles, %6.1f MB, %d tiles",
            level,
            cell_m,
            sum(tier.triangles for tier in tiers),
            sum(tier.bytes for tier in tiers) / 1e6,
            len(tiers),
        )

    if args.terrain:
        log.info("terrain (evaluation output, not part of the tile set):")
        results = build_terrain(city, args.region)
        log.info(
            "  %d sheets: %d triangles, %.1f MB",
            len(results),
            sum(triangles for _, triangles, _ in results),
            sum(size for _, _, size in results) / 1e6,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
