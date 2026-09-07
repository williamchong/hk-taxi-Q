#!/usr/bin/env python3
"""Resident triangles at the worst camera, the way `CityStreamer` would hold them.

    tools/resident_budget.py --region wan_chai [--region mong_kok ...]
    tools/resident_budget.py --region mong_kok --sweep
    tools/resident_budget.py --region mong_kok --lod0-m 200 --unload-m 400

`Q120` measured that the shipped `streaming.tres` pair holds **108%** of the
300k triangle budget resident at the worst camera in `mong_kok`, and did it
with a scratch script that is gone. This is that measurement as a tool
(`P5-18`, `Q122`): every building tile's grid centre is tried as the camera,
each tile and road chunk is banded by the **plan distance from the camera to
its published `aabb`** exactly as `TileStreaming.band_of` does — LOD0 within
`--lod0-m`, the coarsest tier within `--unload-m`, nothing beyond, road chunks
always at their one tier — and the tier triangle counts `buildings.json` and
`roadsurface.json` publish are summed. The worst camera is the statistic;
`Q120` records why the region average is not.

⚠️ **What it reads is what the engine draws, since `P5-13`.** With the
importer's own LODs off the manifest count of a resident tier is the count
submitted for it; before `P5-13` it was an upper bound on the drawn set.
Occlusion and frustum culling still remove from it at draw time, so this is a
*resident* figure — an upper bound on the *visible* triangles the budget in
`docs/ARCHITECTURE.md` is stated against.

🔴 **`Q120`'s table was banded by distance to the tile CENTRE, and the engine
bands by distance to the box — `--band-by centre` reproduces the old figures
to the triangle (181,349 / 301,647 / 143,895 for `wan_chai` / `mong_kok` /
`causeway_bay`; `sha_tin` reads 70,808 against 72,463 because its bundle was
rebuilt for `P5-15`), and the default, `aabb`, is what `CityStreamer` does.**
A 150 m tile's centre is up to 75 m further off than its near face on every
side, so the centre rule loads a tile at LOD1 that the engine loads at LOD0
and unloads one the engine still holds; on the same bundles the shipped pair
reads 105% in `wan_chai` and 184% in `mong_kok` under the engine's rule,
against `Q120`'s 71% and 108%. The old rule is kept as an option so the
correction can be reproduced, never as a reading of the engine.

⚠️ **Two road figures, and `Q120` quoted the first.** `whole road` is every
chunk — `roads.glb` before `P5-6` chunked it, and what `Q120`'s table added to
the building figure; `resident road` is the chunks within the unload radius,
which is what streams today. Both are printed so the old table can be
reproduced and the new one read.

There is no LOD-cell flag, deliberately: the tool reads whatever bundle is
under `--out-root`, so `P5-18`'s cell sweep is one build and one run per cell,
and the L1/L0 ratio printed is the bundle's own rather than a label.

Grades rather than checks: exits 0 whatever it finds.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.documents import read_document  # noqa: E402
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA  # noqa: E402

# The shipped `streaming.tres` pair. Restated rather than parsed out of the
# resource: the `.tres` is Godot's own written form and omits any value equal
# to the script default, so a parse would have to know the defaults too.
LOD0_M = 250.0
UNLOAD_M = 400.0
BUDGET = 300_000
# `Q120`'s own sweep, so its table reproduces row for row.
SWEEP = ((250.0, 400.0), (200.0, 400.0), (150.0, 400.0), (200.0, 300.0), (120.0, 250.0))
# One edge in the profile, so two bands: LOD0 and the coarsest tier. `band_of`
# and the per-tier tallies are sized by this together.
BANDS = 2

Box = tuple[tuple[float, float, float], tuple[float, float, float]]
DistanceRule = Callable[[Box, float, float], float]


@dataclass(frozen=True)
class Unit:
    """One streamable thing: a building tile with its tiers, or a road chunk."""

    id: str
    aabb: Box
    # Triangles per tier, nearest first; a road chunk has one.
    tiers: tuple[int, ...]
    is_road: bool


@dataclass(frozen=True)
class Bundle:
    """A region's stage outputs, read once and shared by the report and the sweep."""

    units: list[Unit]
    # Every building tile's grid centre, `Q120`'s camera set.
    cameras: list[tuple[float, float]]
    whole_road: int
    lod1_cell_m: float | None


@dataclass(frozen=True)
class Profile:
    """The streaming bands and the distance rule that assigns a unit to one."""

    lod0_m: float
    unload_m: float
    distance: DistanceRule


@dataclass(frozen=True)
class Camera:
    x: float
    z: float
    buildings: int
    resident_road: int
    tiles_by_tier: tuple[int, ...]
    # Building triangles resident per tier — the split that says which tier's
    # cell is the lever at this camera, and which is not.
    triangles_by_tier: tuple[int, ...]


def plan_distance_to(box: Box, x: float, z: float) -> float:
    """`TileStreaming.plan_distance_to`: plan distance from a point to a box, 0 inside."""
    (x0, _, z0), (x1, _, z1) = box
    dx = max(x0 - x, x - x1, 0.0)
    dz = max(z0 - z, z - z1, 0.0)
    return math.hypot(dx, dz)


def centre_distance_to(box: Box, x: float, z: float) -> float:
    """`Q120`'s rule: plan distance from a point to the box's centre. Not the engine's."""
    (x0, _, z0), (x1, _, z1) = box
    return math.hypot((x0 + x1) * 0.5 - x, (z0 + z1) * 0.5 - z)


ENGINE_RULE = "aabb"
DISTANCE_RULES: dict[str, DistanceRule] = {
    ENGINE_RULE: plan_distance_to,
    "centre": centre_distance_to,
}


def band_of(distance_m: float, lod0_m: float, unload_m: float) -> int | None:
    """`TileStreaming.band_of` for a one-edge profile: 0, 1, or `None` for unloaded."""
    if distance_m > unload_m:
        return None
    return 0 if distance_m <= lod0_m else 1


def _aabb(entry: dict) -> Box:
    low, high = entry["aabb"]
    return (tuple(low), tuple(high))


def load_bundle(out_dir: Path, region: str) -> Bundle:
    """The region's tiles and road chunks, its cameras, and the whole road's triangles."""
    rebuild = f"cd etl && python -m pipeline --region {region}"
    buildings = read_document(out_dir / BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA, rebuild)
    surface = read_document(out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, rebuild)
    tiles = [
        Unit(
            id=tile["id"],
            aabb=_aabb(tile),
            tiers=tuple(int(lod["triangles"]) for lod in tile["lods"]),
            is_road=False,
        )
        for tile in buildings["tiles"]
    ]
    chunks = [
        Unit(id=chunk["id"], aabb=_aabb(chunk), tiers=(int(chunk["triangles"]),), is_road=True)
        for chunk in surface["chunks"]
    ]
    size = float(buildings["tile_size_m"])
    cells = buildings.get("lod_cell_sizes_m") or []
    return Bundle(
        units=tiles + chunks,
        cameras=[((t["ix"] + 0.5) * size, (t["iz"] + 0.5) * size) for t in buildings["tiles"]],
        whole_road=int(surface["triangles"]),
        lod1_cell_m=float(cells[-1]) if cells else None,
    )


def resident_at(units: list[Unit], x: float, z: float, profile: Profile) -> Camera:
    """What the streamer would hold with the camera at `(x, z)`, ignoring hysteresis."""
    buildings = 0
    road = 0
    tiles = [0] * BANDS
    triangles = [0] * BANDS
    for unit in units:
        band = band_of(profile.distance(unit.aabb, x, z), profile.lod0_m, profile.unload_m)
        if band is None:
            continue
        if unit.is_road:
            road += unit.tiers[0]
            continue
        # `CityManifest.Tile.lod` clamps to what the tile carries.
        tier = min(band, len(unit.tiers) - 1)
        buildings += unit.tiers[tier]
        tiles[tier] += 1
        triangles[tier] += unit.tiers[tier]
    return Camera(x, z, buildings, road, tuple(tiles), tuple(triangles))


def worst_camera(bundle: Bundle, profile: Profile) -> Camera:
    """The camera holding the most building triangles resident."""
    return max(
        (resident_at(bundle.units, x, z, profile) for x, z in bundle.cameras),
        key=lambda camera: camera.buildings,
    )


def lod_ratio(units: list[Unit]) -> float | None:
    """Coarsest-tier over finest-tier triangles, summed over tiles carrying both."""
    tiered = [unit for unit in units if not unit.is_road and len(unit.tiers) > 1]
    finest = sum(unit.tiers[0] for unit in tiered)
    return sum(unit.tiers[-1] for unit in tiered) / finest if finest else None


def budget_share(triangles: int, budget: int) -> str:
    return f"{100.0 * triangles / budget:.0f}%"


def report(region: str, bundle: Bundle, profile: Profile, budget: int, band_by: str) -> Camera:
    camera = worst_camera(bundle, profile)
    rule = (
        "the engine's aabb rule"
        if band_by == ENGINE_RULE
        else "Q120's centre rule (NOT the engine's)"
    )
    print(
        f"{region}: LOD0 <{profile.lod0_m:.0f} m, unload {profile.unload_m:.0f} m,"
        f" budget {budget:,}, {rule}"
    )
    print(
        f"  worst camera ({camera.x:.0f}, {camera.z:.0f}): {camera.buildings:,} building"
        f" triangles resident over {camera.tiles_by_tier[0]} LOD0 + {camera.tiles_by_tier[1]}"
        f" LOD1 tiles"
    )
    lod0_share = 100.0 * camera.triangles_by_tier[0] / camera.buildings if camera.buildings else 0.0
    print(
        f"  of which LOD0 tiles {camera.triangles_by_tier[0]:,} ({lod0_share:.0f}%) and LOD1"
        f" tiles {camera.triangles_by_tier[1]:,} — a LOD1 cell can move only the second"
    )
    with_whole = camera.buildings + bundle.whole_road
    with_resident = camera.buildings + camera.resident_road
    print(
        f"  + whole road {bundle.whole_road:,} = {with_whole:,}"
        f" ({budget_share(with_whole, budget)} of budget) — Q120's model"
    )
    print(
        f"  + resident road {camera.resident_road:,} = {with_resident:,}"
        f" ({budget_share(with_resident, budget)} of budget) — P5-6's chunks"
    )
    ratio = lod_ratio(bundle.units)
    if ratio is not None:
        cell = f" at a {bundle.lod1_cell_m:.1f} m LOD1 cell" if bundle.lod1_cell_m else ""
        print(f"  L1/L0 triangle ratio {ratio:.2f}{cell}")
    return camera


def sweep(bundles: dict[str, Bundle], budget: int, band_by: str) -> None:
    print(f"worst camera, buildings + whole road, share of budget, banded by {band_by}:")
    print("| LOD0 / unload | " + " | ".join(f"`{region}`" for region in bundles) + " |")
    print("|---|" + "---:|" * len(bundles))
    for lod0_m, unload_m in SWEEP:
        profile = Profile(lod0_m, unload_m, DISTANCE_RULES[band_by])
        cells = [
            budget_share(worst_camera(bundle, profile).buildings + bundle.whole_road, budget)
            for bundle in bundles.values()
        ]
        print(f"| {lod0_m:.0f} / {unload_m:.0f} m | " + " | ".join(cells) + " |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--region", action="append", required=True)
    parser.add_argument("--out-root", type=Path, default=None, help="defaults to etl/out")
    parser.add_argument("--lod0-m", type=float, default=LOD0_M)
    parser.add_argument("--unload-m", type=float, default=UNLOAD_M)
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--sweep", action="store_true", help="Q120's distance table")
    parser.add_argument(
        "--band-by",
        choices=sorted(DISTANCE_RULES),
        default=ENGINE_RULE,
        help="aabb is the engine's rule; centre reproduces Q120's table and is not",
    )
    args = parser.parse_args(argv)
    if args.lod0_m > args.unload_m:
        parser.error("--lod0-m must not exceed --unload-m")
    city = load_config()
    bundles = {
        region: load_bundle(city.out_dir(region, args.out_root), region) for region in args.region
    }
    profile = Profile(args.lod0_m, args.unload_m, DISTANCE_RULES[args.band_by])
    for region, bundle in bundles.items():
        report(region, bundle, profile, args.budget, args.band_by)
    if args.sweep:
        sweep(bundles, args.budget, args.band_by)
    return 0


if __name__ == "__main__":
    sys.exit(main())
