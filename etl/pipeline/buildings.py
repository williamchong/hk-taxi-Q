"""Source massing to per-tile, vertex-coloured GLB (`P1-2`, `P3-10`).

Reads the LandsD glTF sheets a previous fetch cached, moves them into the
region's game frame, colours each mesh by height band and class, buckets them
into tiles, and writes one merged mesh per tile per LOD tier.

Merging is the whole point. Untextured, vertex-coloured buildings share a single
material, so a tile's 300-odd buildings collapse into one primitive and one draw
call — which is why the untextured dataset was chosen over the photogrammetry
one (`docs/DATA_SOURCES.md`).

**The ground lands in the same tile primitive since `P3-10`, and that is the
design rather than a convenience.** Being one more class in `classes` is what
gets it the tile's single material for free: it costs no draw call, and it
cannot end up somewhere the buildings are not. It arrives textured and is
stripped on the way in (`_ground`) — the *source* is textured even though the
massing dataset is not, and the tile output carries no textures either way. It
reaches that primitive by a different route, though; see `_tile_ground`.

⚠️ **A consequence with no line of code behind it: the ground collides.** The
finest tier is merged and then named `<tile_id>-col`, so everything in it gets
a trimesh collider, ground included. That was decided rather than inherited —
drawing ground the car falls through is worse than drawing none, because the
player can see it. What it costs is that `collapse` moves vertices to cluster
means, so a lump can end up standing proud of the carriageway and a 0.15 m step
is most of the car's suspension travel. `buildings.ground_sink_m` is what holds
it down, and `tools/ground_clearance.py` is what sizes that.

Within a tier the merge happens **after** the collapse, once per class, because
one cell size does not suit two kinds of geometry: a building is a big box that
loses half its triangles and keeps its silhouette, while an elevated road deck is
thinner than the cell that decimates a building and folds into a sliver. The
merge still runs, so a tile is still one mesh and one draw call.

⚠️ **The ground is the exception, and it runs the other way round** (`Q25`): it
is decimated once for the whole region and cut into tiles afterwards, because it
is the only class that is both cut across tiles and a continuous surface, so a
seam in it is a hole. `_tile_ground` carries the argument.

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
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from zlib import crc32

import numpy as np
from numpy.typing import ArrayLike

from pipeline.colour import with_hue
from pipeline.config import BuildingStyle, CityConfig, RegionConfig, load_city
from pipeline.crs import GameTransform
from pipeline.documents import write_document
from pipeline.fetch import artefact_path, cached_tiles, source_dir
from pipeline.gltf import Bounds, MeshData, read_scene, write_glb
from pipeline.mesh import EmptyMeshError, collapse, merge, select_triangles

log = logging.getLogger(__name__)

# A building's measured `(a*, b*)` — hue without lightness. See `colour.py`.
Hue = tuple[float, float]

# The config key for the tiled source that carries massing. A stage name rather
# than a city fact — `fetch.py --only buildings` names the same thing.
SOURCE_ID = "buildings"

# Where the photo survey lands under the sources tree. A stage name for the same
# reason `SOURCE_ID` is, which keeps the city id out of the city's own config —
# `source_dir` puts it there, and it is the only thing that should.
HUE_SOURCE_ID = "facade_colour"

# How many characters of a source id are the variant suffix. `docs/DATA_SOURCES.md`
# establishes the remaining **stem** as the cross-dataset key: the survey reads
# the individualised set's `…A0` models and this pipeline reads the non-textured
# `…C0` ones, and the stem is what joins them.
_VARIANT_SUFFIX = 2

# Named for what it holds, not for `fetch.py`'s `manifest.json`, which is a
# different file with a different job.
BUILDINGS_MANIFEST_NAME = "buildings.json"
BUILDINGS_MANIFEST_SCHEMA = 2

# Godot's glTF importer reads node-name suffixes: `-col` gives the mesh a static
# trimesh collider at import time and leaves it visible. `write_glb` writes the
# mesh name as the node name, which is where the importer looks. The same
# mechanism `surface.py` uses for the carriageway.
COLLISION_SUFFIX = "-col"

# Only the finest tier, and that is policy rather than oversight. A tier is
# chosen by distance to the camera, so the coarser one is resident only *beyond*
# the near band, where nothing can touch a building — suffixing it would pay for
# a `ConcavePolygonShape3D` in the bundle to be looked at from 300 m away.
# Measured at 5.17 MB of PCK for the one tier that ships it; see docs/PROGRESS.md.
#
# The suffix goes on the *merged* tier, so it covers every class in it. Since
# `P3-10` that includes the ground, which is the whole reason the ground can be
# driven on. Anything added to `classes` from here on inherits collision on this
# tier whether or not it was asked for — worth knowing before adding one.
COLLISION_TIER = 0

# The glTF material name a tile ships so the engine knows to give it the
# window-band shader (`P3-7`). `game/tools/generated_scene_import.gd` dispatches
# on it; everything else in the bundle keeps the default `BaseMaterial3D`.
#
# A name rather than anything structural because glTF offers nothing else: the
# format has no "use this shader" concept, and the payload that distinguishes a
# tile — `TEXCOORD_0` — is also what the road surface uses for lane coordinates,
# so its presence cannot be the signal. The same shape as `COLLISION_SUFFIX`
# above, and it fails the same way: silently, in the engine, where only
# `verify_tiles.gd` can see it.
FACADE_MATERIAL = "city_facade"


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
        max_x, max_z = city.region_high(region.id)
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


def _seed(mesh: MeshData) -> float:
    """A stable number in [0, 1) for one source mesh.

    `crc32` of the name — the LandsD object id — rather than `hash`, which is
    salted per process and would repaint the city on every run.

    Shared by the colour jitter and `P3-7`'s window phase so the two agree: a
    building whose brightness came out at the top of its band has its window rows
    in the same place every rebuild, and neither can drift from the other.
    """
    return crc32(mesh.name.encode("utf-8")) / 0x1_0000_0000


def _stem(name: str) -> str:
    """A source id without its variant suffix — see `_VARIANT_SUFFIX`.

    It was re-verified on sheet `11-SW-10C`: 151 buildings, 151 stems, and every
    one matched between the non-textured set this pipeline reads and the
    individualised set the survey read, with no orphan on either side.
    """
    return name[:-_VARIANT_SUFFIX]


def facade_hue(style: BuildingStyle, city_id: str, *, root: Path | None = None) -> dict[str, Hue]:
    """Per-building `(a*, b*)` from the photo survey, or empty if there is none.

    Keyed by `_stem`, which is what joins the survey's models to this
    pipeline's.

    ⚠️ **Missing is normal, not an error.** The survey is a 4.9 GB read that
    `etl/sources/` caches and `.gitignore` excludes, so a fresh clone has none
    and must still build the same city it built before. Absent, every building
    falls back to its height band, which is what `colour_for` already did.
    Malformed is a different matter and is refused loudly — a partial write of a
    cache this expensive is likelier than a corrupt one, and silently colouring
    the city from half a survey is the outcome worth preventing.

    Rows whose sample is mostly canopy are dropped, and the reason is on the axis
    this function returns rather than the one it discards. At `vegetation_max:
    0.5` that is 43 of Wan Chai's 2,214, and they sit **6.08 `a*` to the green
    side** of the rest at **more than double the chroma** (`C*` 13.72 against
    6.35) — because what they measured is a tree. `strength: 2.0` then doubles
    it, so an unfiltered canopy row reaches the facade about 12 `a*` green.
    """
    if style.facade_hue_source is None:
        return {}
    path = source_dir(city_id, HUE_SOURCE_ID, root=root) / style.facade_hue_source
    try:
        text = path.read_text()
    except FileNotFoundError:
        log.info("no facade hue survey at %s — colouring from height bands", path)
        return {}
    limit = style.facade_hue_vegetation_max
    try:
        table = json.loads(text)
        # `limit is None` short-circuits before `row["vegetation"]`, which is what
        # keeps the column optional for a survey that never recorded one.
        hues = {
            stem: (float(row["lab"][1]), float(row["lab"][2]))
            for stem, row in table.items()
            if limit is None or float(row["vegetation"]) <= limit
        }
    except KeyError as exc:
        if exc.args[0] == "vegetation":
            # Distinguished from a corrupt cache because the fix is the opposite
            # one: this survey is intact and simply predates the column, so the
            # reader should re-run it or drop the threshold, not hunt for a
            # partial write.
            raise ValueError(
                f"{path}: facade_hue.vegetation_max is set, but this survey has no "
                "`vegetation` column — re-run the survey, or unset the threshold"
            ) from exc
        raise ValueError(f"{path}: facade hue survey is malformed ({exc})") from exc
    except (AttributeError, TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"{path}: facade hue survey is malformed ({exc})") from exc
    if limit is None:
        log.info("facade hue: %d buildings from %s", len(hues), path.name)
    else:
        log.info(
            "facade hue: %d buildings from %s, %d dropped over %.0f%% vegetation",
            len(hues),
            path.name,
            len(table) - len(hues),
            limit * 100.0,
        )
    return hues


def colour_for(
    style: BuildingStyle,
    class_id: str,
    mesh: MeshData,
    *,
    bounds: Bounds | None = None,
    hue: dict[str, Hue] | None = None,
) -> np.ndarray:
    """One RGBA row per vertex: the class or height-band colour, jittered.

    How much jitter is the class's to say, not the city's alone. Seeding per
    source mesh only means "per object" where the source ships one mesh per
    object, which is true of buildings and false of the ground.

    Where the survey has a colour for this building, its **hue** replaces the
    band's and its **lightness does not** — the band keeps that, and so does the
    jitter below. The survey's `L*` is repeatable but confounded: log pixel count
    alone explains 26% of it, so it is not albedo. ⚠️ Not because a building's
    walls disagree by compass direction — that is 1.4% of the variance, and
    `colour.py`'s header has the rest of the arithmetic.
    """
    low, high = bounds if bounds is not None else mesh.aabb()
    red, green, blue = style.colour_for(class_id, high[1] - low[1])

    measured = None if hue is None else hue.get(_stem(mesh.name))
    if measured is not None:
        red, green, blue = with_hue((red, green, blue), measured, style.facade_hue_strength)

    jitter = style.jitter_for(class_id)
    if jitter > 0.0:
        factor = 1.0 + jitter * (2.0 * _seed(mesh) - 1.0)
        red, green, blue = (
            min(255, max(0, round(channel * factor))) for channel in (red, green, blue)
        )

    # A read-only broadcast view, not 4 bytes repeated a million times. `merge`
    # and `select_triangles` materialise it where it is actually needed.
    return np.broadcast_to(
        np.array([red, green, blue, 255], dtype=np.uint8), (len(mesh.positions), 4)
    )


def facade_uv(
    style: BuildingStyle, class_id: str, mesh: MeshData, bounds: Bounds | None = None
) -> np.ndarray:
    """One `TEXCOORD_0` row per vertex, for the window-band shader (`P3-7`).

    Two things the shader cannot derive and the ETL therefore must ship:

    - **`u` is metres above this mesh's own base.** A vertex knows its world Y,
      not where its building starts, so a podium vertex and a 30th-floor vertex
      are indistinguishable to a shader — and Wan Chai's ground moves 40 m across
      the region, so world Y is not even a proxy. **Metres rather than the 0-1
      `ART_DESIGN.md` first specified**: normalised, a 3-storey shophouse and a
      40-storey tower each get the same number of window rows, and the floor
      *count* is the density signature the whole effect exists to carry.
    - **`v` is `surface_class + seed`.** The integer part says what this vertex
      belongs to, because a tile is one merged primitive and nothing else
      distinguishes a façade from a viaduct. The fraction is a per-object phase,
      so neighbouring towers do not line their window rows up.

    Packed into one VEC2 rather than taking a second attribute: `TEXCOORD_1`
    would cost another accessor and another vertex stream for one number that
    never varies within a mesh.

    ⚠️ **The horizontal window coordinate is deliberately *not* here.** It is
    derivable in the shader from world position and the wall normal, and a
    payload that ships what the geometry already knows is bytes on every vertex
    of every tile forever.

    ⚠️ **Computed on the whole source mesh, before `assign` splits it**, for the
    same reason the colour is: a viaduct partitioned across four tiles must keep
    one base, or the four pieces disagree about where the ground was.

    ⚠️ Unlike `colour_for`, this cannot be a broadcast view — `u` varies per
    vertex — so it is 8 bytes a vertex through the bucket phase.

    ⚠️ **"Its own base" means the source mesh's, which is an object only where
    the source ships one mesh per object.** True of buildings, false of the
    ground, whose sheet-sized meshes each measure from their own lowest corner —
    so `u` on ground is not comparable across a sheet boundary. Harmless while
    `GROUND` is reserved and unread, and the same caveat `jitter_for` already
    records for colour. A ground treatment that wants a height must say which
    height, and that is a schema question rather than a shader one.
    """
    low, _ = bounds if bounds is not None else mesh.aabb()
    uvs = np.empty((len(mesh.positions), 2), dtype=np.float32)
    uvs[:, 0] = mesh.positions[:, 1] - low[1]
    uvs[:, 1] = float(style.surface_class(class_id)) + _phase(mesh)
    return uvs


# Distinct window phases. A power of two so `_phase` lands on values float32
# holds exactly, and 256 because the eye cannot count more offsets than that
# across a street.
_PHASES = 256


def _phase(mesh: MeshData) -> float:
    """The seed as a fraction that survives being added to a surface marker.

    ⚠️ **Not `_seed` directly, and the difference is a real defect rather than
    tidiness.** `_seed` reaches 1 - 2^-32, and float32 has 24 bits of mantissa:
    near 2.0 its spacing is ~2.4e-7, so `STRUCTURE + 0.9999999998` rounds *up to
    exactly 3.0*. The shader would read a marker of 3, which is nothing, and a
    phase of 0. It would have been rare, silent, and confined to whichever
    viaduct happened to draw a high seed.

    Quantising to 1/256 removes the case by construction rather than by margin:
    every value is exactly representable at every marker, so `floor` and `fract`
    round-trip in the shader instead of nearly doing so.
    """
    return math.floor(_seed(mesh) * _PHASES) / _PHASES


def _ground(mesh: MeshData, offset: np.ndarray, style: BuildingStyle) -> MeshData:
    """One ground mesh, placed in the region and ready to tile (`P3-10`).

    Two things separate it from every other class, and it takes the region
    offset rather than being translated by the caller so that both happen in
    one pass — terrain sheets are the largest meshes in the region, and
    `translated` copies the whole position array each time.

    **The texture goes, here rather than at write time.** `merge` refuses a
    textured mesh whenever it is reached, so this is not what makes the tile
    untextured — it is *when*. `Texture.data` is raw bytes, and `build_region`
    holds its buckets live until the write stage, so leaving the strip to
    `merge` would pin all six sheets' orthophotos — 224 MB — through the whole
    bucket phase. Measured: peak RSS 716 MB with the strip removed against
    605 MB with it. `roads._field` strips at the same seam for the same reason.

    ⚠️ It does **not** save the *read*. `_BufferCache.texture` resolves the
    image while `read_scene` is still building the mesh, so the bytes are
    resident before this is reached — one sheet at a time. Making `read_scene`
    skip images a caller does not want is worth ~185 MB more off the peak and
    belongs to `gltf.py`.

    Dropping the UVs with it is not tidiness. They index a texture that no
    longer exists, `collapse` moves them to cluster representatives, and a
    later stage finding UVs on a tile would be right to assume they mean
    something. Worth 20.5 MB of bucket payload on its own.

    **And it sinks.** `roads.py` lays the level-0 carriageway at `terrain +
    0.0`, so the two surfaces are coplanar by construction; the ground drops
    under the kerb's riser and lip, which is what hides the seam.
    """
    sunk = offset - np.array([0.0, style.ground_sink_m, 0.0])
    return replace(mesh.translated(sunk), texture=None, uvs=None)


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
            out_dir=city.out_dir(region_id, out_root),
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
    hue = facade_hue(style, city.id, root=sources_root)

    report = BuildReport()
    # Bucketed by tile *and class*, because the two decimate at different cell
    # sizes — see `BuildingStyle.cell_size_m`. Merging still happens per tile;
    # it just happens after the collapse instead of before it.
    buckets: dict[tuple[int, int], dict[str, list[MeshData]]] = {}
    # The ground does not go in there — see `_tile_ground` for why it is held
    # whole until every sheet has been read.
    ground: list[MeshData] = []

    for sheet_id, sheet_path in place.sheets:
        kept = 0
        for class_id, mesh in read_sheet(sheet_path, style.classes):
            report.read += 1
            if style.is_ground(class_id):
                # Clipped here rather than inside `_tile_ground` so it is counted
                # like every other class — and so `ground` accumulates only what
                # the region can use. The sheets are 750 m squares against a
                # 1.65 x 0.9 km region, so **54% of the source terrain is
                # outside it**: carrying that to the merge cost a measured
                # 924 MB of peak RSS against 690 MB, to decimate geometry that
                # `assign` then threw away.
                placed = _ground(mesh, place.offset, style)
                inside = _within_region(placed, place.grid)
                if inside is None:
                    report.clipped += 1
                    continue
                ground.append(
                    replace(
                        inside,
                        colours=colour_for(style, class_id, inside),
                        uvs=facade_uv(style, class_id, inside),
                    )
                )
                kept += 1
                continue
            placed = mesh.translated(place.offset)
            bounds = placed.aabb()
            # Colour and shader payload both come from the whole mesh, before any
            # splitting, so a viaduct partitioned across four tiles stays one
            # colour and keeps one base to measure its height above.
            coloured = replace(
                placed,
                colours=colour_for(style, class_id, placed, bounds=bounds, hue=hue),
                uvs=facade_uv(style, class_id, placed, bounds),
            )
            placements = list(assign(coloured, place.grid, bounds))
            for tile, piece in placements:
                buckets.setdefault(tile, {}).setdefault(class_id, []).append(piece)
            if placements:
                kept += 1
            else:
                report.clipped += 1
        log.info("  %-12s %4d kept", sheet_id, kept)

    # `_tile_ground` empties the list as it merges, so nothing here holds the
    # region's ground twice.
    tiers = _tile_ground(ground, place.grid, style)

    if not buckets and not tiers:
        raise ValueError(
            f"region '{region_id}' produced no tiles. Every source mesh fell outside the "
            f"region bounds — check that the sheets on disk are the ones the bounds select."
        )

    # The union, not `buckets` alone: a square holding ground and no buildings is
    # real — the region gained its 66th tile that way when `P3-10` landed — and
    # iterating one dict would drop it without saying anything.
    #
    # Popped as they are written so the bucket payload — ~121 MB for Wan Chai,
    # 173 MB before `Q25` moved the ground out of it — decays across the write
    # stage instead of all staying live to the end. The ground arrives already
    # decimated and comes to 4.0 MB, against the 52.5 MB it occupied here as
    # source geometry.
    for tile in sorted(set(buckets) | set(tiers)):
        written = _write_tile(
            place.out_dir, tile, buckets.pop(tile, {}), tiers.pop(tile, {}), style
        )
        if written is not None:
            report.tiles.append(written)

    _write_manifest(place.out_dir, city, place.region, place.grid, report)
    return report


def _tile_ground(
    meshes: list[MeshData], grid: Grid, style: BuildingStyle
) -> dict[tuple[int, int], dict[int, MeshData]]:
    """The region's ground, decimated **once per tier** and then cut into tiles.

    ⚠️ **The order is the whole point, and it is the reverse of every other
    class** (`Q25`). `collapse` bins on `floor(position / cell_m)`, which is
    world-anchored, but the vertex it ships is `_cluster_mean` over *the members
    present in that mesh*. Cut the ground into tiles first and the two sides of
    a boundary average over different members, land on different positions, and
    the sheet pulls apart — a crack straight through to the sky, since a height
    field has no inside. Measured: **15.65%** of probes within 2 m of a tile
    boundary had no ground over them, against **0.61%** beyond 10 m.

    Collapsing whole and cutting afterwards closes them by construction: every
    tile is a piece of one surface that was decimated as one surface. Region-wide
    holes **1.76% → 0.76%**, the band the driver photographed 8.12% → **0.00%**,
    and the triangle count does not move (87,534 → 87,544).

    Buildings must **not** be treated this way and are not: one is assigned to a
    tile whole, so it is never cut and has no seam to open, and collapsing the
    region's massing as one mesh would merge neighbours across the streets
    between them. The ground is the only class that is both cut and continuous.

    ⚠️ `INFRASTRUCTURE` is cut too — `assign` partitions a two-kilometre viaduct
    by triangle — and tears by the same mechanism. Left alone deliberately: a
    viaduct is a closed volume, so its tears are slivers inside solid geometry
    rather than holes, and moving it would move the geometry `tools/deck_error.py`
    grades `P2-7` against.

    ⚠️ **The caller's list is emptied here rather than after the call**, because
    `merge` copies it and the peak is inside this function, not around it:
    measured at 102.7 MB of source and 113.0 MB of merge live at once. The
    caller has already clipped each mesh to the region — see `build_region`, and
    `_within_region` for why that is a memory measure rather than tidiness.
    """
    if not meshes:
        return {}

    whole = merge(meshes, name=style.terrain_class)
    meshes.clear()

    tiers: dict[tuple[int, int], dict[int, MeshData]] = {}
    for level in range(len(style.lod_cell_sizes_m)):
        try:
            decimated = collapse(
                whole, cell_m=style.cell_size_m(style.terrain_class, level), height_field=True
            )
        except EmptyMeshError:
            # The whole region's ground is smaller than one cell. Not reachable
            # on any real region, and `config.py` refuses a cell table that is
            # not ascending, so no coarser tier can survive what this one did not.
            break
        for tile, piece in assign(decimated, grid):
            tiers.setdefault(tile, {})[level] = piece
    return tiers


def _within_region(mesh: MeshData, grid: Grid) -> MeshData | None:
    """The mesh's triangles inside the region, plus one tile of margin.

    Only the ground needs this, and it needs it because it is the one class
    decimated whole (`_tile_ground`). A sheet is a 750 m square against a
    1.65 x 0.9 km region, so **54% of the source terrain lies outside it** —
    geometry every other class discards in `assign` *before* `collapse` sees it.
    Carrying it into a region-wide decimation costs a measured **924 MB of peak
    RSS against 690 MB**, and 2.70 s against 2.40 s, to produce byte-identical
    interior tiles.

    ⚠️ **The margin is load-bearing.** A triangle just outside the region still
    shares vertices with one inside, and cutting it away before the collapse
    would change which cluster its neighbours average into — trading the tile
    seam `Q25` closes for a region-boundary one. It only has to exceed the
    coarsest cell; one tile is far more than that and needs no tuning.

    `_clip_triangles` asks the same question without the margin, for the
    textured evaluation output, where the region edge is the answer rather than
    a working boundary.
    """
    centroids = mesh.triangle_centroids()
    margin = grid.tile_size_m
    inside = (
        (centroids[:, 0] >= -margin)
        & (centroids[:, 0] <= grid.max_x + margin)
        & (centroids[:, 2] >= -margin)
        & (centroids[:, 2] <= grid.max_z + margin)
    )
    return select_triangles(mesh, inside)


def _write_tile(
    out_dir: Path,
    tile: tuple[int, int],
    by_class: dict[str, list[MeshData]],
    ground: dict[int, MeshData],
    style: BuildingStyle,
) -> TileOutput | None:
    """One tile at every tier it has, or `None` when it has none.

    A tile with no tier ships nothing, so publishing it would put a square in
    the manifest that names no file — which `export.py` and `verify_city.gd`
    both reject, and whose AABB would still widen `bounds_game` with geometry
    no build contains. Dropping it is the only honest option and it only became
    reachable when the finest tier stopped being an exact weld: anything that
    fits inside one 1.5 m cell now empties at level 0.
    """
    ix, iz = tile
    tile_id = f"t_{ix:02d}_{iz:02d}"
    # Sorted so a rerun writes byte-identical tiles: merge order decides vertex
    # order, and a dict's insertion order follows whichever sheet happened to be
    # read first.
    per_class = {name: merge(by_class[name], name=tile_id) for name in sorted(by_class)}

    lods: list[LodOutput] = []
    boxes: list[Bounds] = []
    for level in range(len(style.lod_cell_sizes_m)):
        # Collapsed per class, then merged — for every class that arrives here.
        # Merging first would put a thin bridge deck and a building wall in the
        # same cluster grid and force one cell size on both, which is the thing
        # this exists to stop. Merging after keeps the tile **one mesh and one
        # draw call**, the contract `game/tools/verify_tiles.gd` enforces.
        #
        # ⚠️ The ground does not arrive here, and runs the other way round for
        # a reason that does not apply to any of these — see `_tile_ground`.
        pieces: list[MeshData] = []
        for class_id, mesh in per_class.items():
            try:
                pieces.append(collapse(mesh, cell_m=style.cell_size_m(class_id, level)))
            except EmptyMeshError:
                # This class has nothing left at this cell size; another may.
                continue
        # The ground arrives already decimated, by `_tile_ground`, because it is
        # the one class that must be collapsed *before* it is cut. Appended after
        # the sorted classes rather than merged into them: `TERRAIN(TB)` already
        # sorted last, so this is the order the tiles have always had, and merge
        # order is vertex order.
        if level in ground:
            pieces.append(ground[level])
        if not pieces:
            # Everything left in this tile is smaller than the cell. Expected at
            # the coarsest tier for a square holding one sign gantry — the tiers
            # coarsen, so every later one vanishes too, and that must not take
            # the whole region's build down with it.
            log.info("  %s: nothing survives LOD%d", tile_id, level)
            break
        suffix = COLLISION_SUFFIX if level == COLLISION_TIER else ""
        # Named after the merge rather than carried through it: a merged
        # primitive has one material and `merge` refuses to guess which. This is
        # the tile's request for the window-band shader, and the only channel
        # glTF gives for it — see `FACADE_MATERIAL`.
        tier = replace(merge(pieces, name=f"{tile_id}{suffix}"), material=FACADE_MATERIAL)
        boxes.append(tier.aabb())

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

    if not lods:
        # Nothing survived even the finest tier. Warned rather than logged at
        # info: a square of the city vanishing is worth noticing, and the cell
        # size is the thing to look at.
        log.warning("  %s: nothing survives any tier; the tile is dropped", tile_id)
        return None

    return TileOutput(
        id=tile_id,
        ix=ix,
        iz=iz,
        # Source meshes bucketed here. Since `Q25` that excludes the ground,
        # which no longer *has* a per-tile source count — it is decimated as one
        # surface for the whole region before anything is cut, so a ground-only
        # tile reports zero. A diagnostic in `buildings.json`; `export.py` does
        # not forward it and nothing in `game/` reads it.
        meshes=sum(len(group) for group in by_class.values()),
        # The union of the **shipped tiers**, not of the source geometry.
        #
        # This is what the runtime culls with and what `bounds_game` is summed
        # from, so it has to describe what a build actually contains. Measuring
        # it from the uncollapsed source was right only while tier 0 was an exact
        # weld: decimation pulls vertices to cluster centroids and drops anything
        # thinner than a cell, so a source box can exceed every mesh that ships.
        # Measured when the finest tier became 1.5 m — one tile's declared height
        # ran **19 m** past its own LOD0, a mast too thin to survive the cell.
        # `verify_city.gd` compares the two in-engine and caught it.
        #
        # A union rather than tier 0's box alone, because nothing guarantees a
        # coarser tier sits inside a finer one — a cluster mean can move a vertex
        # outward — and a box that fails to contain a tier would cull geometry
        # that is about to be drawn.
        aabb=_union(boxes),
        lods=lods,
    )


def _union(boxes: Iterable[Bounds]) -> Bounds:
    lows, highs = zip(*boxes, strict=True)
    return (
        (min(c[0] for c in lows), min(c[1] for c in lows), min(c[2] for c in lows)),
        (max(c[0] for c in highs), max(c[1] for c in highs), max(c[2] for c in highs)),
    )


def _write_manifest(
    out_dir: Path, city: CityConfig, region: RegionConfig, grid: Grid, report: BuildReport
) -> None:
    """An intermediate for `P1-6`, not the game-facing contract.

    `city.json` is `export.py`'s to write and has to reconcile roads and fares
    too. This file records only what the building stage knows, so the two stages
    stay independently runnable.
    """
    write_document(
        out_dir / BUILDINGS_MANIFEST_NAME,
        {
            "schema_version": BUILDINGS_MANIFEST_SCHEMA,
            "city_id": city.id,
            "region_id": region.id,
            "tile_size_m": grid.tile_size_m,
            "grid": {"columns": grid.columns, "rows": grid.rows},
            "lod_cell_sizes_m": list(city.buildings.lod_cell_sizes_m),
            # Recorded beside the default table because on its own that table no
            # longer describes the build: a tier is not one cell size once a
            # class is held back from it, and this file exists to diagnose what
            # was actually produced.
            "class_lod_cell_sizes_m": {
                name: list(sizes)
                for name, sizes in sorted(city.buildings.class_lod_cell_sizes_m.items())
            },
            "tiles": [asdict(tile) for tile in report.tiles],
        },
    )


# --------------------------------------------------------------------------
# Textured terrain — evaluation output only
# --------------------------------------------------------------------------


def build_terrain(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> list[tuple[str, int, int]]:
    """Emit each sheet's **textured** ground mesh, clipped to the region.

    Not what ships. `P3-10` tiles the ground through `build_region` with the
    texture stripped, which is the version the game gets; this keeps the
    orthophoto reachable so the choice not to ship it can be re-examined
    instead of only re-read. `docs/ART_DESIGN.md` records the argument: it would
    cost a draw call per tile, and it has the *real* roads baked into it at
    their real width, under a generated ribbon drawn 1.6x wider.

    Not merged into the tile output, and now for one reason rather than two.
    The remaining one is the texture — 224 MB of JPEG across the region's six
    sheets, against tiles specified to carry none.

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
    style = city.buildings
    for level, cell_m in enumerate(style.lod_cell_sizes_m):
        # Named per class where they differ, because "LOD1 (1.5 m cells)" is a
        # false summary the moment one class is held back from that cell — and
        # the whole point of the override is that the tier is not uniform.
        overrides = ", ".join(
            f"{name} {sizes[level]:.1f} m"
            for name, sizes in sorted(style.class_lod_cell_sizes_m.items())
            if sizes[level] != cell_m
        )
        cells = f"{cell_m:.1f} m cells" + (f"; {overrides}" if overrides else "")
        # Not every tile reaches every tier — see `LodOutput`.
        tiers = [tile.lods[level] for tile in report.tiles if level < len(tile.lods)]
        log.info(
            "  LOD%d (%s): %8d triangles, %6.1f MB, %d tiles",
            level,
            cells,
            sum(tier.triangles for tier in tiers),
            sum(tier.bytes for tier in tiers) / 1e6,
            len(tiers),
        )

    if args.terrain:
        log.info("textured terrain (evaluation output; the tiles above ship it untextured):")
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
