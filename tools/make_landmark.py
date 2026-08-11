"""Generate the hero landmark buildings (`P3-6`).

    python tools/make_landmark.py
    python tools/make_landmark.py --out-dir /tmp/landmarks --report

`ART_DESIGN.md` names ~5 buildings whose identity the generated tiles cannot
carry; each ships as an authored `.glb` placed via `landmarks.json`, and the
ETL excludes the source meshes it replaces. Generated rather than modelled —
**not** on `P3-11`'s argument, which was a proportion family with a roster
behind it and does not transfer to five bespoke silhouettes. The argument here
is the one the byte-comparison test enforces: a committed generator makes the
model reproducible from a fresh clone, reviewable in a diff, and parameterised
by the surveyed dimensions it was authored against (footprints, base and roof
levels read from the iB1000 blocks and the 3D-BIT meshes — the numbers on each
`Proportions`-style dataclass below cite their sheet). See `docs/DECISIONS.md`,
`P3-6`.

Every model is authored at the origin: footprint centred on x/z, `y = 0` at
the building's base level — `landmarks.json` carries the position (game-space
metres, `y` = base elevation) and a compass bearing, and the runtime applies
them. A one-metre plinth continues every model below `y = 0` so ±0.5 m of
disagreement with the terrain reads as pavement, not as a floating slab.

Output goes to `game/assets/authored/landmarks/`, which is **committed** —
hand-authored assets under CC BY-SA 4.0, not build output. See LICENSING.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.colour import reflectance  # noqa: E402
from pipeline.config import EXPOSURE_TOLERANCE_PCT, load_city  # noqa: E402
from pipeline.gltf import MeshData, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import Colour, Point, box_at, loft, ring  # noqa: E402

LOG = logging.getLogger("make_landmark")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "landmarks"

# ≠ `city_facade`, deliberately: `generated_scene_import.gd` swaps that name for
# the tile shader, whose `TEXCOORD_0`/`TEXCOORD_1` payloads these models do not
# author. Any other name gets the vertex-colour `BaseMaterial3D` path instead.
MATERIAL = "landmark_vertex"

# The `-col` suffix is the tile precedent (`buildings.py`, `COLLISION_SUFFIX`):
# the visible mesh doubles as its own static trimesh collider, which matters
# here because excluding the source building also removes the tile collision
# that used to stand on its footprint. Same importer-suffix caution as
# `make_vehicle.py`: nothing else may end in _wheel/_convcol/_navmesh/etc.
HKCEC_FILE = "hkcec.glb"
CENTRAL_PLAZA_FILE = "central_plaza.glb"


@dataclass(frozen=True)
class Surface:
    """A real material and the colour it ships as — `hong_kong.yaml:materials`
    in miniature, because these colours cannot live there: the table colours
    what the ETL draws, and a committed `.glb` never passes through the ETL.

    The same rule still binds (`Q33`): every colour is `reflectance x
    exposure_anchor`, and `check_palette` refuses to generate on the same
    tolerance `_check_exposure` refuses to load. The anchor is read from the
    city config at generate time (`Q38`) — change the anchor and this generator
    stops until the palette is re-derived, loudly.
    """

    name: str
    colour: Colour  # sRGB, what COLOR_0 carries (`Q27`: consumers linearise)
    reflectance: float  # real-world diffuse albedo, %
    source: str


ALUMINIUM = Surface(
    "aluminium_roof",
    (144, 146, 148),
    55.0,
    "mill-finish standing-seam aluminium, 50-60%",
)
GLASS = Surface(
    "curtain_glass",
    (61, 72, 83),
    12.0,
    "curtain-wall glass, 8-15% diffuse — the trap Q34 records: never lighter",
)
CONCRETE = Surface(
    "concrete_pale",
    (114, 110, 102),
    30.0,
    "clean concrete and granite podium cladding, 20-35%",
)
GOLD = Surface(
    "gold_glass",
    (87, 75, 54),
    14.0,
    "gold reflective coated glass, 10-20% diffuse",
)
GOLD_BAND = Surface(
    "gold_band",
    (101, 89, 70),
    20.0,
    "the lighter mechanical-floor band on the same glass family",
)

PALETTE = (ALUMINIUM, GLASS, CONCRETE, GOLD, GOLD_BAND)


def check_palette(anchor: float) -> None:
    """`_check_exposure` for the colours the ETL never sees."""
    for surface in PALETTE:
        expected = surface.reflectance * anchor
        actual = reflectance(surface.colour)
        if abs(actual - expected) > EXPOSURE_TOLERANCE_PCT:
            red, green, blue = surface.colour
            raise ValueError(
                f"{surface.name} is #{red:02x}{green:02x}{blue:02x}, whose luminance "
                f"is {actual:.2f}% — but it declares reflectance {surface.reflectance}% "
                f"at exposure_anchor {anchor}, which is {expected:.2f}%. "
                "Re-derive the palette, or change the material it claims to be."
            )


# How far the plinth continues below y = 0, absorbing terrain disagreement.
PLINTH_DEPTH_M = 1.0


@dataclass(frozen=True)
class Hkcec:
    """Phase 2 — the island wing and its atrium link, stem `B358761603301063`.

    Dimensions read from sheet `11-SW-9D`: iB1000 block 1103124251 ("Hong Kong
    Convention and Exhibition Centre", base 3.6 / roof 70.3 mPD) and the 3D-BIT
    mesh (footprint 201 x 349 m including the link, top 71.9 mPD). Local frame:
    -z is the model's north — the harbour side the roof sweeps toward.

    ⚠️ This is the **massing pass**: right footprint, right heights, the wing
    stated as an asymmetric swoop. The curved roof is the art commit's job.
    """

    island_half_x_m: float = 95.0  # 3D-BIT E span 201.3 m
    island_north_z_m: float = -157.0  # N 816198.6, about the authored centroid
    island_south_z_m: float = 43.0  # where the hall ends and the link begins
    link_south_z_m: float = 191.0  # N 815849.6 — the link's landward end
    link_half_x_m: float = 22.0
    link_roof_m: float = 18.0
    podium_m: float = 8.0  # concrete base band
    hall_roof_m: float = 30.0  # glass hall shoulder
    ridge_m: float = 66.0  # roof crest; mesh top 71.9 mPD less base 4.0, eased
    corner_cut_m: float = 10.0


@dataclass(frozen=True)
class CentralPlaza:
    """Stem `B359321570101063` — iB1000 block 1103126797, base 3.9 / roof
    380.7 mPD; 3D-BIT mesh footprint 78.6 x 82.9 m, top 378.5 mPD.

    Local frame before the runtime bearing: the tower triangle's apex points
    -z. Heights are metres above the base level the authored position carries.
    """

    podium_half_x_m: float = 39.0
    podium_half_z_m: float = 41.0
    podium_m: float = 30.5
    tower_radius_m: float = 33.0  # triangle centroid to apex
    corner_cut_m: float = 7.5
    shaft_top_m: float = 288.0
    crown_top_m: float = 330.0  # pyramid
    mast_top_m: float = 374.5  # mesh top 378.53 mPD less base 4.0
    mast_half_m: float = 1.2


def tri_ring(y: float, radius: float, cut: float) -> tuple[Point, ...]:
    """A triangle in plan, apex to -z, corners cut — Central Plaza's section.

    A simple six-point cycle: each vertex is trimmed `cut` metres toward both
    neighbours, turning three corners into six short facets — the same
    chamfer-not-smoothing rule as everything else (`P3-11`). Winding does not
    need stating: `loft` orients every face itself via `polygon_facing`.
    """
    corners = [
        np.array([radius * np.sin(np.radians(a)), -radius * np.cos(np.radians(a))])
        for a in (0.0, 120.0, 240.0)
    ]
    points: list[Point] = []
    for i, corner in enumerate(corners):
        for other in (corners[i - 1], corners[(i + 1) % 3]):
            toward = other - corner
            trimmed = corner + toward / float(np.linalg.norm(toward)) * cut
            points.append((float(trimmed[0]), y, float(trimmed[1])))
    return tuple(points)


def build_hkcec(p: Hkcec | None = None) -> MeshData:
    """Island hall with the roof swept toward the harbour, plus the link."""
    p = p or Hkcec()
    hall = loft(
        [
            ring(
                -PLINTH_DEPTH_M,
                p.island_half_x_m + 2.0,
                p.island_north_z_m - 2.0,
                p.island_south_z_m + 2.0,
                p.corner_cut_m,
            ),
            ring(
                p.podium_m,
                p.island_half_x_m,
                p.island_north_z_m,
                p.island_south_z_m,
                p.corner_cut_m,
            ),
            ring(
                p.hall_roof_m,
                p.island_half_x_m - 3.0,
                p.island_north_z_m + 3.0,
                p.island_south_z_m - 3.0,
                p.corner_cut_m,
            ),
            # The swoop: the crest sits on the harbour half, so the south face
            # rakes long and shallow while the north face stays steep.
            ring(
                p.ridge_m,
                p.island_half_x_m - 55.0,
                p.island_north_z_m + 35.0,
                p.island_south_z_m - 120.0,
                p.corner_cut_m,
            ),
        ],
        [CONCRETE.colour, GLASS.colour, ALUMINIUM.colour],
        bottom=CONCRETE.colour,
        top=ALUMINIUM.colour,
        name="hkcec_hall",
    )
    link = loft(
        [
            ring(
                -PLINTH_DEPTH_M, p.link_half_x_m + 2.0, p.island_south_z_m, p.link_south_z_m + 2.0
            ),
            ring(p.podium_m, p.link_half_x_m, p.island_south_z_m, p.link_south_z_m),
            ring(p.link_roof_m, p.link_half_x_m - 2.0, p.island_south_z_m, p.link_south_z_m - 2.0),
        ],
        [CONCRETE.colour, GLASS.colour],
        bottom=CONCRETE.colour,
        top=ALUMINIUM.colour,
        name="hkcec_link",
    )
    return replace(merge([hall, link], name="hkcec-col"), material=MATERIAL)


def build_central_plaza(p: CentralPlaza | None = None) -> MeshData:
    """Podium, triangular shaft, pyramid crown, mast."""
    p = p or CentralPlaza()
    podium = loft(
        [
            ring(
                -PLINTH_DEPTH_M,
                p.podium_half_x_m + 2.0,
                -p.podium_half_z_m - 2.0,
                p.podium_half_z_m + 2.0,
                6.0,
            ),
            ring(p.podium_m, p.podium_half_x_m, -p.podium_half_z_m, p.podium_half_z_m, 6.0),
        ],
        [CONCRETE.colour],
        bottom=CONCRETE.colour,
        top=CONCRETE.colour,
        name="central_plaza_podium",
    )
    shaft = loft(
        [
            tri_ring(p.podium_m, p.tower_radius_m, p.corner_cut_m),
            tri_ring(p.shaft_top_m, p.tower_radius_m, p.corner_cut_m),
        ],
        [GOLD.colour],
        bottom=GOLD.colour,
        top=GOLD_BAND.colour,
        name="central_plaza_shaft",
    )
    crown = loft(
        [
            tri_ring(p.shaft_top_m, p.tower_radius_m, p.corner_cut_m),
            tri_ring(p.crown_top_m, 3.0, 1.0),
        ],
        [ALUMINIUM.colour],
        bottom=GOLD_BAND.colour,
        top=ALUMINIUM.colour,
        name="central_plaza_crown",
    )
    mast = box_at(
        (0.0, (p.crown_top_m + p.mast_top_m) / 2.0, 0.0),
        (p.mast_half_m, (p.mast_top_m - p.crown_top_m) / 2.0, p.mast_half_m),
        ALUMINIUM.colour,
        name="central_plaza_mast",
    )
    return replace(merge([podium, shaft, crown, mast], name="central_plaza-col"), material=MATERIAL)


def build_landmarks() -> list[tuple[str, MeshData]]:
    return [(HKCEC_FILE, build_hkcec()), (CENTRAL_PLAZA_FILE, build_central_plaza())]


def write_landmarks(out_dir: Path) -> list[tuple[Path, int, MeshData]]:
    """Check the palette against the live anchor, then write one `.glb` each."""
    check_palette(load_city("hong_kong").exposure_anchor)
    written = []
    for filename, mesh in build_landmarks():
        path = out_dir / filename
        written.append((path, write_glb(path, [mesh]), mesh))
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output directory")
    parser.add_argument("--report", action="store_true", help="print the geometry it produced")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    written = write_landmarks(args.out_dir)
    for path, size, mesh in written:
        LOG.info("%s — %d bytes, %d triangles", path, size, mesh.triangle_count)
    if args.report:
        for _, _, mesh in written:
            (low, high) = mesh.aabb()
            LOG.info(
                "  %-20s x %+.1f..%+.1f  y %+.1f..%+.1f  z %+.1f..%+.1f",
                mesh.name,
                low[0],
                high[0],
                low[1],
                high[1],
                low[2],
                high[2],
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
