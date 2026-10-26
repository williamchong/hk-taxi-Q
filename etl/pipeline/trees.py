"""Published trees, stood as a library of kinds (`P3-77`, `Q171`).

Two inventories publish a tree as a point and an identity — HyD's Tree layer
(with a trunk diameter) and LCSD's venue trees (with a species) — and this stage
stands each on the ground the bundle draws, as one of four library meshes
scaled to its height. 🔴 **Only where one is surveyed**: nothing fills the
parks LCSD's layer leaves out (Victoria Park) or the streets nobody inventories.

Three refusals, each counted, none of them a push — a published tree moved is a
tree that is not where it was surveyed:

- **in the carriageway**: the trunk stands inside the level-0 carriageway region
  (`carriageway_region.json`'s R) or within `kerb_clear_m` of its rail. A kerbed
  island is a hole in R, so a tree on one stands.
- **no ground**: no ground face the tiles draw lies under the point.
- **under structure**: a face the bundle draws — a block, a podium, a deck —
  stands over the foot between `overhead_clear_m` and the tree's own top.

⚠️ **The height is the SHIPPED ground's, not the source terrain's**: the tiles
decimate the ground, and a tree stood on the sheets' finer surface floats or
sinks against the one drawn under it — `tramway.py`'s reason for reading the
meshes. A park's ground is painted (`buildings.paint_parks`), so the ground is
read by both colours.

⚠️ **Every size is authored** (`Trees`' docstring). The trunk is what the engine
collides with: `trees_placements.json` carries each kind's trunk radius and the
crown's base height in the library's frame, and every tree's stand scales them.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely

from pipeline import gdb
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA
from pipeline.clearance import ground_colour, tile_meshes, wears
from pipeline.config import Config, GameTransform, TreeKind, Trees, load_config
from pipeline.documents import read_document, write_document
from pipeline.fetch import cached_source
from pipeline.gltf import MeshData, read_render
from pipeline.meshbuild import ColouredBuilder
from pipeline.placements import Placement, placement, stand_library
from pipeline.railings import facing_away
from pipeline.report import tail_of
from pipeline.roads import clean_text
from pipeline.signs import disc
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, read_surface
from pipeline.surface_region import read as read_carriageway_region
from pipeline.terrain import hits

log = logging.getLogger(__name__)

TREES_NAME = "trees.glb"
TREES_MANIFEST_NAME = "trees.json"
TREES_MANIFEST_SCHEMA = 1
TREES_PLACEMENTS_NAME = "trees_placements.json"
# The glTF material name `tools/generated_scene_import.gd` dispatches on.
TREES_MATERIAL = "trees"

# Plan bin for the ground and structure faces. `tramway._Faces`' size, for its
# reason: a decimated ground triangle is metres across, a roof tens.
_CELL_M = 8.0
# A face this close to vertical carries no height worth asking: a wall's plan
# projection is a sliver, and the roof above it answers the overhead question.
_MIN_UP = 0.1


@dataclass(frozen=True)
class Tree:
    """One published tree, in region game space."""

    publisher: str
    ident: str
    x: float
    z: float
    species: str | None
    dbh_mm: float | None


@dataclass
class TreeReport:
    """What the stage read, refused and stood.

    The partitions:

        features   == empty_geometry + outside + read
        read       == merged + candidates
        candidates == drawn + in_carriageway + no_ground + under_structure
    """

    features: int = 0
    features_by_publisher: dict[str, int] = field(default_factory=dict)
    empty_geometry: int = 0
    outside: int = 0
    read: int = 0
    # Two publishers' records within `merge_m`: one tree, the first publisher's.
    merged: int = 0
    candidates: int = 0
    in_carriageway: int = 0
    no_ground: int = 0
    under_structure: int = 0
    drawn: int = 0
    drawn_by_publisher: dict[str, int] = field(default_factory=dict)
    drawn_by_kind: dict[str, int] = field(default_factory=dict)
    # How each drawn tree's height was got: off its trunk, or its kind's.
    sized_by_dbh: int = 0
    sized_by_kind: int = 0
    heights_m: list[float] = field(default_factory=list)
    # 🔴 **The invariant: no trunk stands in the carriageway**, measured from
    # the placed point to R's boundary rather than read back off the refusal.
    # At least `kerb_clear_m` while the refusal runs; delete it and this goes
    # negative.
    min_kerb_clearance_m: float = math.inf
    facing_away: int = 0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)
    placements: int = 0
    placements_refused: int = 0
    library_meshes: int = 0
    library_triangles: int = 0
    library_vertices: int = 0


class _Faces:
    """Triangles binned by plan cell, asked for every height over a point."""

    def __init__(self, corners: np.ndarray) -> None:
        self.corners = corners
        plan = corners[:, :, [0, 2]]
        low = np.floor_divide(plan.min(axis=1), _CELL_M).astype(np.intp)
        high = np.floor_divide(plan.max(axis=1), _CELL_M).astype(np.intp)
        cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        for row in range(len(corners)):
            for cx in range(low[row, 0], high[row, 0] + 1):
                for cz in range(low[row, 1], high[row, 1] + 1):
                    cells[(cx, cz)].append(row)
        self.cells = {cell: np.asarray(rows, dtype=np.intp) for cell, rows in cells.items()}

    def heights(self, x: float, z: float) -> np.ndarray:
        rows = self.cells.get((int(x // _CELL_M), int(z // _CELL_M)))
        if rows is None:
            return np.zeros(0)
        return hits(self.corners[rows], x, z)


def read_trees(
    city: Config,
    spec: Trees,
    region_id: str,
    transform: GameTransform,
    report: TreeReport,
    *,
    sources_root: Path | None = None,
) -> list[Tree]:
    """Every publisher's trees inside the region's rectangle, in precedence order."""
    bbox = city.projected_bounds(region_id).bbox
    far_x, far_z = city.region_high(region_id)
    trees: list[Tree] = []
    for publisher in spec.publishers:
        layer = gdb.read_layer(
            cached_source(city, publisher.source, root=sources_root),
            publisher.layer.layer,
            columns=publisher.layer.columns,
            bbox=bbox,
            expect_crs=city.projected_crs,
        )
        report.features += len(layer)
        report.features_by_publisher[publisher.id] = len(layer)
        owners, plan = gdb.points(layer)
        report.empty_geometry += len(layer) - len(owners)
        idents = layer.column(publisher.layer.field("id"))
        species = layer.column(publisher.layer.field("species")) if publisher.has_species else None
        dbh = layer.column(publisher.layer.field("dbh_mm")) if publisher.has_dbh else None
        for owner, (easting, northing) in zip(owners, plan, strict=True):
            if not (math.isfinite(easting) and math.isfinite(northing)):
                report.empty_geometry += 1
                continue
            x, _, z = transform.to_game(float(easting), float(northing))
            if not (0.0 <= x <= far_x and 0.0 <= z <= far_z):
                report.outside += 1
                continue
            trees.append(
                Tree(
                    publisher=publisher.id,
                    ident=str(idents[owner]),
                    x=float(x),
                    z=float(z),
                    species=None if species is None else clean_text(species[owner], ()),
                    dbh_mm=None if dbh is None else _number(dbh[owner]),
                )
            )
    report.read = len(trees)
    return trees


def _number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0.0 else None


def merge(trees: list[Tree], merge_m: float) -> tuple[list[Tree], int]:
    """`trees` with every one within `merge_m` of a kept one dropped, and how many.

    First wins, so the list's order is the publishers' precedence. Within one
    publisher the order is the read's, and a publisher repeating a point keeps
    its first record.
    """
    kept: list[Tree] = []
    cells: dict[tuple[int, int], list[Tree]] = defaultdict(list)
    for tree in trees:
        cx, cz = int(tree.x // merge_m), int(tree.z // merge_m)
        near = (
            other
            for dx in (-1, 0, 1)
            for dz in (-1, 0, 1)
            for other in cells.get((cx + dx, cz + dz), ())
        )
        if any(math.hypot(other.x - tree.x, other.z - tree.z) < merge_m for other in near):
            continue
        kept.append(tree)
        cells[(cx, cz)].append(tree)
    return kept, len(trees) - len(kept)


def _rng(tree: Tree) -> np.random.Generator:
    """A generator seeded on the tree's identity — the same tree, every build."""
    digest = hashlib.sha256(f"{tree.publisher}:{tree.ident}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def height_of(spec: Trees, tree: Tree, kind: TreeKind, jitter: float) -> tuple[float, bool]:
    """The tree's height and whether its trunk gave it.

    `jitter` is a draw in [-1, 1]; it moves a height got from the kind's and
    leaves one got from a measured trunk alone.
    """
    if tree.dbh_mm is not None:
        sized = tree.dbh_mm * spec.height_per_dbh_m
        return float(np.clip(sized, spec.min_height_m, spec.max_height_m)), True
    return kind.height_m * (1.0 + spec.height_jitter * jitter), False


# --------------------------------------------------------------------------
# The library
# --------------------------------------------------------------------------

# A crown's silhouette, bottom to top: (share of the crown's span, share of
# `crown_radius_m`). A broadleaf is a lumpy ellipsoid; a fan palm a flattened
# round head. Drawing, not tuning: the sizes they scale are in the config.
_CROWN_PROFILE = ((0.0, 0.55), (0.35, 1.0), (0.7, 0.85), (1.0, 0.3))
_FAN_PROFILE = ((0.0, 0.4), (0.3, 1.0), (0.75, 0.8), (1.0, 0.2))
# A feather palm's frond, from the head: (share of the radius out, metres up)
# at its ridge's middle and its tip, and the half-width at the middle.
_FROND_MID = (0.5, 0.35)
_FROND_TIP = (1.0, -1.1)
_FROND_HALF_WIDTH_M = 0.3
# A conifer is two cones: (base as a share of height, top as one, base radius
# as a share of `crown_radius_m`).
_CONES = ((0.0, 0.75, 1.0), (0.45, 1.0, 0.7))


def _face(
    builder: ColouredBuilder, points: np.ndarray, colour: tuple[int, int, int], outward: np.ndarray
) -> None:
    """A convex polygon, wound so its front faces `outward`."""
    normal = np.cross(points[1] - points[0], points[2] - points[0])
    if float(normal @ outward) < 0.0:
        points, normal = points[::-1], -normal
    length = float(np.linalg.norm(normal))
    if length <= 0.0:
        return
    builder.polygon(points, normal / length, colour)


def _ring(radius: float, y: float, sides: int) -> np.ndarray:
    # `signs.disc`, for its phase convention, lifted into the plan at `y`.
    plan = disc(radius, sides)
    return np.column_stack([plan[:, 0], np.full(sides, y), plan[:, 1]])


def _radial(points: np.ndarray) -> np.ndarray:
    centre = points.mean(axis=0)
    return np.array([centre[0], 0.0, centre[2]])


def _band(
    builder: ColouredBuilder, lower: np.ndarray, upper: np.ndarray, colour: tuple[int, int, int]
) -> None:
    """The sides between two rings of the same phase — each a planar trapezoid."""
    sides = len(lower)
    for i in range(sides):
        j = (i + 1) % sides
        quad = np.array([lower[i], lower[j], upper[j], upper[i]])
        _face(builder, quad, colour, _radial(quad))


def _cone(
    builder: ColouredBuilder, base: np.ndarray, apex: np.ndarray, colour: tuple[int, int, int]
) -> None:
    sides = len(base)
    for i in range(sides):
        triangle = np.array([base[i], base[(i + 1) % sides], apex])
        _face(builder, triangle, colour, _radial(triangle[:2]))
    _face(builder, base, colour, np.array([0.0, -1.0, 0.0]))


def _profiled(
    builder: ColouredBuilder,
    profile: tuple[tuple[float, float], ...],
    low_m: float,
    high_m: float,
    radius_m: float,
    sides: int,
    colour: tuple[int, int, int],
) -> None:
    rings = [_ring(share * radius_m, low_m + t * (high_m - low_m), sides) for t, share in profile]
    for lower, upper in itertools.pairwise(rings):
        _band(builder, lower, upper, colour)
    _face(builder, rings[0], colour, np.array([0.0, -1.0, 0.0]))
    _face(builder, rings[-1], colour, np.array([0.0, 1.0, 0.0]))


def _fronds(
    builder: ColouredBuilder, head: np.ndarray, radius_m: float, count: int, colour: tuple
) -> None:
    """A feather palm's head: `count` drooping fronds, each a closed thin tent."""
    for k in range(count):
        angle = 2.0 * math.pi * k / count
        out = np.array([math.cos(angle), 0.0, math.sin(angle)])
        across = np.array([-out[2], 0.0, out[0]])
        mid = head + out * _FROND_MID[0] * radius_m + np.array([0.0, _FROND_MID[1], 0.0])
        tip = head + out * _FROND_TIP[0] * radius_m + np.array([0.0, _FROND_TIP[1], 0.0])
        left = mid - across * _FROND_HALF_WIDTH_M
        right = mid + across * _FROND_HALF_WIDTH_M
        ridge = mid + np.array([0.0, 0.08, 0.0])
        up, down = np.array([0.0, 1.0, 0.0]), np.array([0.0, -1.0, 0.0])
        for triangle in ((head, left, ridge), (head, ridge, right), (left, tip, ridge)):
            _face(builder, np.array(triangle), colour, up)
        _face(builder, np.array((ridge, tip, right)), colour, up)
        _face(builder, np.array((head, right, left)), colour, down)
        _face(builder, np.array((left, right, tip)), colour, down)


def draw_kind(spec: Trees, name: str, kind: TreeKind) -> MeshData | None:
    """One library mesh, at the origin, `kind.height_m` tall, foot at y = 0."""
    builder = ColouredBuilder(TREES_MATERIAL)
    bark = spec.bark_material.colour
    leaves = kind.crown_material.colour
    height, sides = kind.height_m, spec.sides
    crown_low = kind.crown_base * height
    if kind.form == "palm":
        # A palm's trunk runs to its head; the fronds spring from the top.
        top = _ring(0.8 * kind.trunk_radius_m, height, sides)
        _band(builder, _ring(kind.trunk_radius_m, 0.0, sides), top, bark)
        _face(builder, top, bark, np.array([0.0, 1.0, 0.0]))
        _fronds(builder, np.array([0.0, height, 0.0]), kind.crown_radius_m, sides, leaves)
    else:
        # The trunk runs into the crown so no gap shows under it.
        trunk_top = crown_low + 0.25 * (height - crown_low)
        _band(
            builder,
            _ring(kind.trunk_radius_m, 0.0, sides),
            _ring(kind.trunk_radius_m, trunk_top, sides),
            bark,
        )
        if kind.form == "cone":
            for base, apex, share in _CONES:
                low = crown_low + base * (height - crown_low)
                high = crown_low + apex * (height - crown_low)
                _cone(
                    builder,
                    _ring(share * kind.crown_radius_m, low, sides),
                    np.array([0.0, high, 0.0]),
                    leaves,
                )
        else:
            profile = _FAN_PROFILE if kind.form == "fan" else _CROWN_PROFILE
            _profiled(builder, profile, crown_low, height, kind.crown_radius_m, sides, leaves)
    return builder.build(name)


def trunks(spec: Trees) -> dict[str, dict[str, float]]:
    """Each kind's trunk collider in the library's frame: radius and height."""
    return {
        name: {
            "radius_m": kind.trunk_radius_m,
            "height_m": round(kind.crown_base * kind.height_m, 4),
        }
        for name, kind in sorted(spec.kinds.items())
    }


# --------------------------------------------------------------------------
# The region
# --------------------------------------------------------------------------


def _shipped_faces(city: Config, region_id: str, out_dir: Path) -> tuple[_Faces, _Faces]:
    """The ground the tiles draw, and everything else the bundle draws over it."""
    rebuild = f"python -m pipeline --region {region_id}"
    buildings = read_document(out_dir / BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA, rebuild)
    surface = read_document(out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, rebuild)
    paving, jitter = ground_colour(city)
    park = None if city.basemap is None else city.basemap.park_material.colour
    ground: list[np.ndarray] = []
    road = read_surface(out_dir, surface["chunks"])
    structure: list[np.ndarray] = [road.positions[road.triangles].astype(np.float64)]
    for path in tile_meshes(out_dir, buildings):
        for mesh in read_render(path):
            if mesh.colours is None or not len(mesh.triangles):
                continue
            on_ground = wears(mesh.colours, paving, jitter)
            if park is not None:
                on_ground |= wears(mesh.colours, park, 0.0)
            is_ground = on_ground[mesh.triangles].all(axis=1)
            corners = mesh.positions[mesh.triangles].astype(np.float64)
            ground.append(corners[is_ground])
            structure.append(corners[~is_ground])
    return _Faces(np.concatenate(ground)), _Faces(_upward(np.concatenate(structure)))


def _upward(corners: np.ndarray) -> np.ndarray:
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    length = np.linalg.norm(normal, axis=1)
    return corners[np.abs(normal[:, 1]) > _MIN_UP * np.where(length > 0.0, length, 1.0)]


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> TreeReport:
    """Read the region's published trees and write `trees.glb` and its stands."""
    spec = city.trees
    report = TreeReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no trees block; nothing to stand", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    read = read_trees(city, spec, region_id, transform, report, sources_root=sources_root)
    candidates, report.merged = merge(read, spec.merge_m)
    report.candidates = len(candidates)

    carriageway = read_carriageway_region(out_dir, region_id).whole
    kept_clear = carriageway.buffer(spec.kerb_clear_m)
    shapely.prepare(kept_clear)
    ground, structure = _shipped_faces(city, region_id, out_dir)

    stands: list[Placement] = []
    for tree in candidates:
        if kept_clear.contains(shapely.Point(tree.x, tree.z)):
            report.in_carriageway += 1
            continue
        under = ground.heights(tree.x, tree.z)
        if not len(under):
            report.no_ground += 1
            continue
        foot = float(under.max())
        rng = _rng(tree)
        yaw, jitter = float(rng.uniform(0.0, 360.0)), float(rng.uniform(-1.0, 1.0))
        name = spec.kind_of(tree.species)
        kind = spec.kinds[name]
        height, by_dbh = height_of(spec, tree, kind, jitter)
        over = structure.heights(tree.x, tree.z)
        if ((over > foot + spec.overhead_clear_m) & (over < foot + height)).any():
            report.under_structure += 1
            continue
        scale = round(height / kind.height_m, 4)
        stands.append(placement(name, (tree.x, foot, tree.z), yaw, scale=(scale, scale, scale)))
        report.drawn += 1
        report.drawn_by_publisher[tree.publisher] = (
            report.drawn_by_publisher.get(tree.publisher, 0) + 1
        )
        report.drawn_by_kind[name] = report.drawn_by_kind.get(name, 0) + 1
        report.sized_by_dbh += int(by_dbh)
        report.sized_by_kind += int(not by_dbh)
        report.heights_m.append(height)
        report.min_kerb_clearance_m = min(
            report.min_kerb_clearance_m, float(carriageway.distance(shapely.Point(tree.x, tree.z)))
        )
    for name in spec.kinds:
        report.drawn_by_kind.setdefault(name, 0)
    report.drawn_by_kind = dict(sorted(report.drawn_by_kind.items()))

    stood = sorted({entry["mesh"] for entry in stands})
    meshes = [mesh for name in stood if (mesh := draw_kind(spec, name, spec.kinds[name]))]
    library = stand_library(meshes, stands)
    if meshes:
        report.facing_away = sum(facing_away(mesh) for mesh in meshes)
        library.publish(report)
        library.require_every_stand(report.drawn, f"{report.drawn} trees")
        report.bytes = library.write(
            out_dir,
            TREES_NAME,
            TREES_PLACEMENTS_NAME,
            city.id,
            region_id,
            extra={"trunks": {n: t for n, t in trunks(spec).items() if n in stood}},
        )
    _write_manifest(out_dir, city, region_id, report)
    return report


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: TreeReport) -> int:
    drawn = bool(report.triangles)
    clearance = report.min_kerb_clearance_m
    document = {
        "schema_version": TREES_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "asset": TREES_NAME if drawn else None,
        "placements_document": TREES_PLACEMENTS_NAME if drawn else None,
        "features": report.features,
        "features_by_publisher": report.features_by_publisher,
        "empty_geometry": report.empty_geometry,
        "outside": report.outside,
        "read": report.read,
        "merged": report.merged,
        "candidates": report.candidates,
        # The refusals, as disjoint parts of `candidates` with `drawn`.
        "in_carriageway": report.in_carriageway,
        "no_ground": report.no_ground,
        "under_structure": report.under_structure,
        "drawn": report.drawn,
        "drawn_by_publisher": dict(sorted(report.drawn_by_publisher.items())),
        "drawn_by_kind": report.drawn_by_kind,
        # ⚠️ Every height is an estimate the publishers do not give; these say
        # which way each was got.
        "sized_by_dbh": report.sized_by_dbh,
        "sized_by_kind": report.sized_by_kind,
        "height_m": tail_of(report.heights_m),
        # 🔴 The invariant: at least `kerb_clear_m`, measured, not assumed.
        "min_kerb_clearance_m": round(clearance, 4) if math.isfinite(clearance) else None,
        "facing_away": report.facing_away,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
        "placements": report.placements,
        "placements_refused": report.placements_refused,
        "library_meshes": report.library_meshes,
        "library_triangles": report.library_triangles,
        "library_vertices": report.library_vertices,
    }
    return write_document(out_dir / TREES_MANIFEST_NAME, document)


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
        "trees: %d read -> %d stood (%d merged, %d in carriageway, %d no ground, "
        "%d under structure), %.2f m least kerb clearance, %d triangles, %d facing away",
        report.read,
        report.drawn,
        report.merged,
        report.in_carriageway,
        report.no_ground,
        report.under_structure,
        report.min_kerb_clearance_m,
        report.triangles,
        report.facing_away,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
