"""Generate the authored hero landmark buildings (`P3-6`).

    python tools/make_landmark.py
    python tools/make_landmark.py --out-dir /tmp/landmarks --report

`ART_DESIGN.md` names ~5 buildings whose identity the generated tiles cannot
carry; the authored ones ship as committed `.glb`s placed via `landmarks.json`,
and the ETL excludes the source meshes they replace. Generated rather than
modelled — **not** on `P3-11`'s argument, which was a proportion family with a
roster behind it and does not transfer to bespoke silhouettes. The argument
here is the one the byte-comparison test enforces: a committed generator makes
the model reproducible from a fresh clone, reviewable in a diff, and
parameterised by the surveyed dimensions it was authored against (footprints,
base and roof levels read from the iB1000 blocks and the 3D-BIT meshes — the
numbers on each `Proportions`-style dataclass below cite their sheet). See
`docs/DECISIONS.md`, `P3-6`.

⚠️ **HKCEC is not here any more, and it must not come back here.** Its hero is
the building's own source mesh, extracted and repainted by
`etl/pipeline/landmarks.py` — a `source_paint` landmark in the city config —
after the review rounds converged this generator's massing onto the source by
measurement. That model is government-derived generated output and can never
be a committed asset (LICENSING.md); the ribbon constants it kept live on in
the config's `source_paint` block.

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

from pipeline.buildings import COLLISION_SUFFIX  # noqa: E402
from pipeline.config import Material, check_material_exposure, load_city  # noqa: E402
from pipeline.gltf import MeshData, write_glb  # noqa: E402

# The one name the engine dispatches materials on — owned by the pipeline
# stage since the HKCEC repaint, imported so the two hero emitters cannot
# drift on it. See `pipeline/landmarks.py` for why it is ≠ `city_facade`.
from pipeline.landmarks import LANDMARK_MATERIAL as MATERIAL  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import Point, box, loft, ring  # noqa: E402

LOG = logging.getLogger("make_landmark")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "landmarks"

CENTRAL_PLAZA_FILE = "central_plaza.glb"


# `hong_kong.yaml:materials` in miniature, on the config's own `Material`
# dataclass — these colours cannot live in that table, because the table
# colours what the ETL draws and a committed `.glb` never passes through the
# ETL. The same rule still binds (`Q33`): every colour is `reflectance x
# exposure_anchor`, held by `check_palette` on the same shared check the
# loader applies to the YAML. The anchor is read from the city config at
# generate time (`Q38`) — change the anchor and this generator stops until
# the palette is re-derived, loudly. Colours are sRGB, what `COLOR_0`
# carries (`Q27`: consumers linearise).
ALUMINIUM = Material(
    "aluminium_roof",
    (144, 146, 148),
    55.0,
    "mill-finish standing-seam aluminium, 50-60%",
)
# HKCEC's `panel_pale` and `roof_grey` moved to `hong_kong.yaml:materials`
# with its repaint — a colour a pipeline stage ships belongs where
# `_check_exposure` can see it. These two stay: Central Plaza's podium.
GLASS = Material(
    "curtain_glass",
    (61, 72, 83),
    12.0,
    "curtain-wall glass, 8-15% diffuse — the trap Q34 records: never lighter",
)
CONCRETE = Material(
    "concrete_pale",
    (114, 110, 102),
    30.0,
    "clean concrete and granite podium cladding, 20-35%",
)
GOLD = Material(
    "gold_glass",
    (87, 75, 54),
    14.0,
    "gold reflective coated glass, 10-20% diffuse",
)
GOLD_BAND = Material(
    "gold_band",
    (101, 89, 70),
    20.0,
    "the lighter mechanical-floor band on the same glass family",
)

PALETTE = (ALUMINIUM, GLASS, CONCRETE, GOLD, GOLD_BAND)


def check_palette(anchor: float) -> None:
    """`_check_exposure` for the colours the ETL never sees — same shared body."""
    for surface in PALETTE:
        check_material_exposure(surface, anchor, surface.name)


# How far the plinth continues below y = 0, absorbing terrain disagreement,
# and how far it stands proud of the footprint in plan — pavement, not wall.
PLINTH_DEPTH_M = 1.0
PLINTH_FLARE_M = 2.0


@dataclass(frozen=True)
class CentralPlaza:
    """Stem `B359321570101063` — iB1000 block 1103126797, base 3.9 / roof
    380.7 mPD; 3D-BIT mesh footprint 78.6 x 82.9 m, top 378.5 mPD.

    Local frame before the runtime bearing: the tower triangle's apex points
    -z. Heights are metres above the base level the authored position carries.
    """

    podium_half_x_m: float = 39.0
    podium_half_z_m: float = 41.0
    podium_base_m: float = 12.0  # granite arcade under the atrium glass
    podium_m: float = 30.5
    tower_radius_m: float = 33.0  # triangle centroid to apex
    corner_cut_m: float = 7.5
    # The lighter mechanical band two-thirds up — with the crown, the feature
    # that separates this tower from every flat-topped shaft around it.
    band_low_m: float = 160.0
    band_high_m: float = 166.0
    shaft_top_m: float = 288.0
    pyramid_top_m: float = 335.0  # the glass pyramid's apex
    mast_step_m: float = 352.0  # the mast thins here
    mast_top_m: float = 374.5  # mesh top 378.53 mPD less base 4.0
    mast_half_m: float = 2.2
    mast_tip_half_m: float = 1.0


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


def build_central_plaza(p: CentralPlaza | None = None) -> MeshData:
    """Granite-and-glass podium, banded triangular shaft, glass pyramid, mast."""
    p = p or CentralPlaza()
    podium = loft(
        [
            ring(
                -PLINTH_DEPTH_M,
                p.podium_half_x_m + PLINTH_FLARE_M,
                -p.podium_half_z_m - PLINTH_FLARE_M,
                p.podium_half_z_m + PLINTH_FLARE_M,
                6.0,
            ),
            ring(p.podium_base_m, p.podium_half_x_m, -p.podium_half_z_m, p.podium_half_z_m, 6.0),
            ring(p.podium_m, p.podium_half_x_m, -p.podium_half_z_m, p.podium_half_z_m, 6.0),
        ],
        # Arcade below, the atrium's glass above — the podium is where the
        # driver actually is, so it gets the one band the tower can spare.
        [CONCRETE.colour, GLASS.colour],
        bottom=CONCRETE.colour,
        top=CONCRETE.colour,
        name="central_plaza_podium",
    )
    # The arcade's piers, spaced along both street faces — the relief a driver
    # actually passes. Boxes rather than cylinders (`P3-11`: chamfer, never
    # smooth), stood just proud of the podium wall.
    piers: list[MeshData] = []
    for index in range(-3, 4):
        x = index * (p.podium_half_x_m / 3.5)
        for side in (-1.0, 1.0):
            piers.append(
                box(
                    (x - 1.2, -PLINTH_DEPTH_M, side * p.podium_half_z_m - 1.2),
                    (x + 1.2, p.podium_base_m, side * p.podium_half_z_m + 1.2),
                    CONCRETE.colour,
                    name=f"central_plaza_pier_{index}_{side}",
                )
            )
    shaft = loft(
        [
            tri_ring(p.podium_m, p.tower_radius_m, p.corner_cut_m),
            tri_ring(p.band_low_m, p.tower_radius_m, p.corner_cut_m),
            tri_ring(p.band_high_m, p.tower_radius_m, p.corner_cut_m),
            tri_ring(p.shaft_top_m, p.tower_radius_m, p.corner_cut_m),
        ],
        [GOLD.colour, GOLD_BAND.colour, GOLD.colour],
        bottom=GOLD.colour,
        top=GOLD_BAND.colour,
        name="central_plaza_shaft",
    )
    pyramid = loft(
        [
            tri_ring(p.shaft_top_m, p.tower_radius_m, p.corner_cut_m),
            tri_ring(p.pyramid_top_m, 3.0, 1.0),
        ],
        [ALUMINIUM.colour],
        bottom=GOLD_BAND.colour,
        top=ALUMINIUM.colour,
        name="central_plaza_pyramid",
    )
    mast = [
        box(
            (-half, low, -half),
            (half, high, half),
            ALUMINIUM.colour,
            name=f"central_plaza_mast_{index}",
        )
        for index, (low, high, half) in enumerate(
            (
                (p.pyramid_top_m, p.mast_step_m, p.mast_half_m),
                (p.mast_step_m, p.mast_top_m, p.mast_tip_half_m),
            )
        )
    ]
    return replace(
        merge([podium, *piers, shaft, pyramid, *mast], name=f"central_plaza{COLLISION_SUFFIX}"),
        material=MATERIAL,
    )


def build_landmarks() -> list[tuple[str, MeshData]]:
    return [(CENTRAL_PLAZA_FILE, build_central_plaza())]


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
