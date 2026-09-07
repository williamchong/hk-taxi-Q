"""How far the tile collider stands off the facade it stands in for (`P5-12`).

Since `P5-12` a tile's finest tier ships two primitives: the render mesh the
player sees and a `-colonly` collider the car hits, each decimated at its own
stated cell (`buildings.lod_cell_sizes_m[0]` and `buildings.collision_cell_m`,
per class). A collider coarser than the facade is a wall the car drives into
before it reaches the wall it can see, or through the wall it can — and no
in-engine check can see that, because a collider is invisible by construction.
This measures the offset between the two, on the shipped bundle.

**What is measured.** For every collider vertex, the distance to the nearest
render-mesh vertex of the same tile, and the same the other way round. Vertex
to vertex, not vertex to surface: a collider vertex `d` metres from the nearest
drawn vertex is *at most* `d` from the drawn surface, so each direction is an
**upper bound** on the offset at that vertex. Reported per `SurfaceClass` at
the house p50 / p90 / p99 / max (`tools/centreline_error.py` says why one
distribution, not two),
because the ground has extent and no silhouette while a facade is nothing but
one, and the two classes are decimated at different cells by design.

**At the shipped cells the answer is 0.00 m, and that is by value rather than
by construction.** The config states the collision cells equal to the finest
tier's, so the collider is that tier's own triangles; `--sweep` builds the
colliders again at coarser cells — into a scratch directory, the shipped bundle
untouched — and prices what a smaller trimesh costs in offset. The sweep moves
the *default* cell only and keeps the class overrides, because a deck thinner
than its cell folds and that is `P2-1`'s finding, not this tool's question.

⚠️ **The sweep grades the buildings stage's output, before the carve.** The
carve re-emits nine tiles with walls in both primitives, and its counters are
the render mesh's alone; the offset it introduces is measured on the shipped
row, not the sweep rows.

The road is graded too: each chunk's collider is the ribbon's own triangles
(`surface._road_collider`), so the tool counts the chunks where the two are
identical and reports any that are not.

Grades rather than checks: exits 0 whatever it finds. The bar is `--bar-m`, the
0.25 m `PLAN.md` proposed, and the count over it is a number to read, not a gate.

Run:  .venv/bin/python tools/collider_offset.py
      .venv/bin/python tools/collider_offset.py --sweep 2.0,3.0,4.0
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(ROOT / "tools"))

from deck_error import bundle_arguments, load_bundle, log_bundle  # noqa: E402
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, build_region  # noqa: E402
from pipeline.config import SurfaceClass, load_config  # noqa: E402
from pipeline.gltf import MeshData, read_glb, split_colliders  # noqa: E402

log = logging.getLogger(__name__)

# Past this the nearest-vertex search stops looking and the sample is reported
# as censored. Sized well past any bar anyone would set: a 4 m collider cell
# moves a vertex at most half a cell, and the search reads three cells across.
SEARCH_RADIUS_M = 8.0


@dataclass(frozen=True)
class TileOffset:
    """One tile's two primitives, and the offsets between them per class."""

    tile: str
    render_triangles: int
    collider_triangles: int
    # collider vertex → nearest render vertex, keyed by `SurfaceClass` name.
    to_render: dict[str, np.ndarray]
    # render vertex → nearest collider vertex, keyed the same way.
    to_collider: dict[str, np.ndarray]


def _grouped(keys: np.ndarray) -> dict[tuple[int, int, int], np.ndarray]:
    """Row indices by integer cell key — one `np.unique`, no per-row Python."""
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    order = np.argsort(inverse, kind="stable")
    starts = np.searchsorted(inverse[order], np.arange(len(unique)))
    ends = np.append(starts[1:], len(order))
    return {tuple(unique[i]): order[starts[i] : ends[i]] for i in range(len(unique))}


def nearest_distance(points: np.ndarray, targets: np.ndarray, radius_m: float) -> np.ndarray:
    """Distance from each point to the nearest target, `inf` past `radius_m`.

    Bucketed on a grid of `radius_m` cells so a tile of ten thousand vertices
    a side is a few hundred small blocks rather than one hundred-million-entry
    distance matrix. Exact within the radius: a target nearer than `radius_m`
    lies in one of the 27 cells around the point's own. ⚠️ The cell IS the
    radius on purpose — a finer cell with a wider gather was measured slower
    (13 s and 53 s against 8 s at half and a quarter of it), because the gather
    is Python and the candidate volume it saves is not.

    Each block is a centred matrix product, `|b|^2 - 2 b.n + |n|^2`, rather than
    a `(m, n, 3)` broadcast: 2.2x faster and a third of the temporary, within
    2e-7 m of the broadcast on a table printed to the millimetre. Centred on the
    block's mean so the cancellation runs over metres and not over a 1.5 km
    easting.
    """
    out = np.full(len(points), np.inf)
    if not len(points) or not len(targets):
        return out
    cell = float(radius_m)
    buckets = _grouped(np.floor(targets / cell).astype(np.int64))
    groups = _grouped(np.floor(points / cell).astype(np.int64))
    offsets = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    for key, members in groups.items():
        parts = [
            buckets[neighbour]
            for neighbour in ((key[0] + dx, key[1] + dy, key[2] + dz) for dx, dy, dz in offsets)
            if neighbour in buckets
        ]
        if not parts:
            continue
        block = points[members]
        near = targets[np.concatenate(parts)]
        centre = block.mean(axis=0)
        b = block - centre
        n = near - centre
        squared = (b * b).sum(axis=1)[:, None] - 2.0 * (b @ n.T) + (n * n).sum(axis=1)[None, :]
        best = np.sqrt(np.maximum(squared.min(axis=1), 0.0))
        best[best > radius_m] = np.inf
        out[members] = best
    return out


def _classes(mesh: MeshData) -> np.ndarray:
    """Each vertex's `SurfaceClass` name, off `TEXCOORD_1.x`'s integer part."""
    if mesh.uv2 is None:
        return np.full(len(mesh.positions), "unclassed")
    markers = np.floor(mesh.uv2[:, 0]).astype(int)
    names = {int(member): member.name for member in SurfaceClass}
    return np.array([names.get(int(marker), "unclassed") for marker in markers])


def _by_class(distances: np.ndarray, classes: np.ndarray) -> dict[str, np.ndarray]:
    return {name: distances[classes == name] for name in sorted(set(classes.tolist()))}


def grade_tile(path: Path) -> TileOffset | None:
    """One tile's offsets, or `None` where the file carries no collider."""
    drawn, colliders = split_colliders(read_glb(path))
    if len(drawn) != 1 or len(colliders) != 1:
        return None
    render, collider = drawn[0], colliders[0]
    return TileOffset(
        tile=path.stem,
        render_triangles=render.triangle_count,
        collider_triangles=collider.triangle_count,
        to_render=_by_class(
            nearest_distance(collider.positions, render.positions, SEARCH_RADIUS_M),
            _classes(collider),
        ),
        to_collider=_by_class(
            nearest_distance(render.positions, collider.positions, SEARCH_RADIUS_M),
            _classes(render),
        ),
    )


def _quantiles(values: np.ndarray) -> str:
    finite = values[np.isfinite(values)]
    if not len(finite):
        return "        —        —        —        —"
    p50, p90, p99, top = np.percentile(finite, (50, 90, 99, 100))
    return f"  {p50:7.3f}  {p90:7.3f}  {p99:7.3f}  {top:7.3f}"


def report(tiles: list[TileOffset], bar_m: float, label: str) -> None:
    """The per-tile table and the per-class summary for one set of colliders."""
    render = sum(tile.render_triangles for tile in tiles)
    collider = sum(tile.collider_triangles for tile in tiles)
    log.info("")
    log.info(
        "%s: %d tiles, render %s triangles, collider %s (%.1f%% of the render mesh)",
        label,
        len(tiles),
        f"{render:,}",
        f"{collider:,}",
        100.0 * collider / max(render, 1),
    )
    log.info(
        "  %-12s %9s %9s %7s  %34s", "tile", "render", "collider", "ratio", "collider→render m"
    )
    log.info(
        "  %-12s %9s %9s %7s  %8s %8s %8s %8s", "", "tris", "tris", "", "p50", "p90", "p99", "max"
    )
    worst = sorted(
        tiles,
        key=lambda tile: (
            -max(
                (float(np.nanmax(v)) if len(v) and np.isfinite(v).any() else 0.0)
                for v in tile.to_render.values()
            )
        ),
    )
    for tile in worst[:10]:
        pooled = np.concatenate(list(tile.to_render.values()))
        log.info(
            "  %-12s %9d %9d %7.3f%s",
            tile.tile,
            tile.render_triangles,
            tile.collider_triangles,
            tile.collider_triangles / max(tile.render_triangles, 1),
            _quantiles(pooled),
        )
    if len(worst) > 10:
        log.info("  … %d more tiles, all with a smaller worst offset", len(worst) - 10)

    log.info("")
    log.info("  per class, vertex to nearest vertex (an upper bound on the surface offset):")
    log.info(
        "  %-14s %-18s %8s %8s %8s %8s %9s %9s",
        "class",
        "direction",
        "p50",
        "p90",
        "p99",
        "max",
        "over bar",
        "censored",
    )
    for direction, attribute in (
        ("collider→render", "to_render"),
        ("render→collider", "to_collider"),
    ):
        pooled: dict[str, list[np.ndarray]] = defaultdict(list)
        for tile in tiles:
            for name, values in getattr(tile, attribute).items():
                pooled[name].append(values)
        for name in sorted(pooled):
            values = np.concatenate(pooled[name])
            finite = values[np.isfinite(values)]
            log.info(
                "  %-14s %-18s%s %9d %9d",
                name,
                direction,
                _quantiles(values),
                int((finite > bar_m).sum()),
                int((~np.isfinite(values)).sum()),
            )
    log.info(
        "  bar %.2f m; a vertex is 'censored' when nothing lies within %.1f m",
        bar_m,
        SEARCH_RADIUS_M,
    )


def grade_road(generated: Path, manifest: dict[str, Any]) -> None:
    """Every chunk's collider against its ribbon: identical, or by how much not."""
    identical = 0
    differing: list[tuple[str, float]] = []
    chunks = manifest.get("road_surface", [])
    for chunk in chunks:
        drawn, colliders = split_colliders(read_glb(generated / str(chunk["file"])))
        if len(drawn) != 1 or len(colliders) != 1:
            differing.append((str(chunk["id"]), float("nan")))
            continue
        if np.array_equal(drawn[0].positions, colliders[0].positions) and np.array_equal(
            drawn[0].triangles, colliders[0].triangles
        ):
            identical += 1
            continue
        offset = nearest_distance(colliders[0].positions, drawn[0].positions, SEARCH_RADIUS_M)
        differing.append((str(chunk["id"]), float(np.nanmax(offset))))
    log.info("")
    log.info(
        "road: %d of %d chunks carry a collider identical to the ribbon, kerb riser included",
        identical,
        len(chunks),
    )
    for chunk_id, offset in differing:
        log.info("  %s: collider differs, worst offset %.3f m", chunk_id, offset)


def sweep(city_id: str, region_id: str, cells: list[float], bar_m: float) -> None:
    """The colliders rebuilt at each cell, graded — the shipped bundle untouched."""
    city = load_config()
    if city.id != city_id:
        raise SystemExit(f"the bundle is {city_id}'s and the config is {city.id}'s")
    for cell in cells:
        style = replace(city.buildings, collision_cell_m=cell)
        with tempfile.TemporaryDirectory(prefix="collider_offset_") as scratch:
            out_root = Path(scratch)
            build_region(replace(city, buildings=style), region_id, out_root=out_root)
            manifest = json.loads((out_root / region_id / BUILDINGS_MANIFEST_NAME).read_text())
            tiles = [
                graded
                for tile in manifest["tiles"]
                if (graded := grade_tile(out_root / region_id / tile["lods"][0]["path"]))
                is not None
            ]
        overrides = ", ".join(
            f"{name} {value:.1f} m" for name, value in sorted(style.class_collision_cell_m.items())
        )
        report(tiles, bar_m, f"sweep collision_cell_m={cell:.1f} m ({overrides} kept)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0], parents=[bundle_arguments()]
    )
    parser.add_argument(
        "--bar-m",
        type=float,
        default=0.25,
        help="the offset a collider vertex may stand off the facade (default: 0.25, PLAN.md's)",
    )
    parser.add_argument(
        "--sweep",
        type=lambda text: [float(value) for value in text.split(",")],
        default=None,
        help="collision cells to rebuild the colliders at and grade, e.g. 2.0,3.0,4.0",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manifest, paths = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)
    tiles = [graded for path in paths if (graded := grade_tile(path)) is not None]
    if not tiles:
        raise SystemExit("no tile carries a `-colonly` collider; is this a pre-P5-12 bundle?")
    report(tiles, args.bar_m, "shipped")
    grade_road(args.generated, manifest)
    if args.sweep:
        sweep(str(manifest["city_id"]), str(manifest["region_id"]), args.sweep, args.bar_m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
