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
from pipeline.config import Material, check_material_reflectance  # noqa: E402
from pipeline.gltf import MeshData, write_glb  # noqa: E402

# The one name the engine dispatches materials on — owned by the pipeline
# stage since the HKCEC repaint, imported so the two hero emitters cannot
# drift on it. See `pipeline/landmarks.py` for why it is ≠ `city_facade`.
from pipeline.landmarks import LANDMARK_MATERIAL as MATERIAL  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import Colour, Point, box, loft, ring  # noqa: E402

LOG = logging.getLogger("make_landmark")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "landmarks"

CENTRAL_PLAZA_FILE = "central_plaza.glb"
STAR_FERRY_FILE = "star_ferry.glb"


# `hong_kong.yaml:materials` in miniature, on the config's own `Material`
# dataclass — these colours cannot live in that table, because the table
# colours what the ETL draws and a committed `.glb` never passes through the
# ETL. The same rule still binds (`Q33`): every colour **is** a real material's
# diffuse albedo and lies inside the range its own source names, held by
# `check_palette` on the same shared check the loader applies to the YAML.
#
# 🔴 **Un-baked by `P5-28c`, and that is why every value here moved.** Until then
# each colour was `reflectance x exposure_anchor` and this generator read the
# anchor out of the city config at build time. The exposure is a Godot global now
# (`Q38`), so these are reflectance-level colours and the rig scales them —
# `aluminium_roof` ships `#c1c4c7` and reaches the screen at the `#909294` it used
# to carry. ⚠️ **So the committed `.glb` and the shipped `project.godot` are one
# artefact in two files**, which is what `city.json`'s `schema_version` 5 says.
# Colours are sRGB, what `COLOR_0` carries (`Q27`: consumers linearise).
ALUMINIUM = Material(
    "aluminium_roof",
    (193, 196, 199),
    55.0,
    "mill-finish standing-seam aluminium, 50-60%",
    (50.0, 60.0),
)
# HKCEC's `panel_pale` and `roof_grey` moved to `hong_kong.yaml:materials`
# with its repaint — a colour a pipeline stage ships belongs where
# `_check_reflectance` can see it. These two stay: Central Plaza's podium.
GLASS = Material(
    "curtain_glass",
    (84, 99, 113),
    12.0,
    "curtain-wall glass, 8-15% diffuse — the trap Q34 records: never lighter",
    (8.0, 15.0),
)
CONCRETE = Material(
    "concrete_pale",
    (154, 149, 138),
    30.0,
    "clean concrete and granite podium cladding, 20-35%",
    (20.0, 35.0),
)
GOLD = Material(
    "gold_glass",
    (119, 103, 75),
    14.0,
    "gold reflective coated glass, 10-20% diffuse",
    (10.0, 20.0),
)
# ⚠️ **The one entry whose `source` named no range**, so `P5-28c` had to widen the
# sentence rather than transcribe it. Stated as 15-25%: a mechanical-floor band on
# the same coated-glass family, lighter than the 10-20% glass beside it. That is
# an argument rather than a citation, which is exactly what `bounds` is for —
# a soft number stated is arguable and a soft number implied is not.
GOLD_BAND = Material(
    "gold_band",
    (137, 121, 96),
    20.0,
    "the lighter mechanical-floor band on the same glass family, 15-25%",
    (15.0, 25.0),
)

# The moored ferry's (`P3-102`, `Q254`): the fleet's two-colour livery, green
# below and white above, and the black rubber of its fenders. Paint colours,
# not a brand: the hull carries no name, lettering or emblem (`Q42`).
FERRY_GREEN = Material(
    "ferry_green",
    (40, 104, 64),
    10.7,
    "gloss marine enamel, mid-dark green, 8-15%",
    (8.0, 15.0),
)
FERRY_WHITE = Material(
    "ferry_white",
    (222, 224, 220),
    74.0,
    "white marine enamel, weathered, 70-85%",
    (70.0, 85.0),
)
FENDER = Material(
    "fender_rubber",
    (38, 38, 40),
    2.0,
    "carbon-black rubber fendering, 1-5%",
    (1.0, 5.0),
)

PALETTE = (ALUMINIUM, GLASS, CONCRETE, GOLD, GOLD_BAND, FERRY_GREEN, FERRY_WHITE, FENDER)


def check_palette() -> None:
    """`_check_reflectance` for the colours the ETL never sees — same shared body.

    ⚠️ **Takes no anchor since `P5-28c`.** It read one out of `load_config()`
    until the exposure left the ETL (`Q38`); the check is now colour against its
    own declared reflectance and reflectance against its own bounds, neither of
    which the city config knows anything about.
    """
    for surface in PALETTE:
        check_material_reflectance(surface, surface.name)


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


@dataclass(frozen=True)
class StarFerry:
    """A double-ended harbour ferry moored at Wan Chai Ferry Pier (`P3-102`).

    Length and beam are Electric Star's (1933): 116 ft overall, 28 ft beam,
    35.4 x 8.5 m — the fleet's common size; World Star (46 m) and Golden Star
    (47 m) are the long exceptions. The decks are proportions read off
    photographs, not a survey: no publisher draws a vessel.

    Local frame: the waterline's centre is the origin, `y = 0` the water
    plane, and the long axis is z. Both ends are the same, as on the real
    boats, so the bearing names the hull's line and not a bow. The hull runs
    `hull_below_m` under the water so the rocking (`tuning/moored.tres`)
    never lifts a gap into view.
    """

    length_m: float = 35.4
    beam_m: float = 8.5
    hull_below_m: float = 1.0
    # The double-ended plan: each end's corners cut this far, so the hull
    # tapers from the full beam to a blunt 2.5 m end.
    end_cut_m: float = 3.0
    fender_low_m: float = 0.9
    fender_high_m: float = 1.3
    fender_proud_m: float = 0.2
    deck_m: float = 1.5
    # The lower saloon, set in from the hull and short of its ends, where the
    # gangways land on open deck.
    lower_inset_m: float = 0.35
    lower_end_m: float = 2.5
    lower_glass_m: tuple[float, float] = (2.4, 3.3)
    upper_deck_m: float = 3.9
    upper_inset_m: float = 0.5
    upper_end_m: float = 3.5
    upper_glass_m: tuple[float, float] = (4.5, 5.5)
    roof_band_m: float = 6.0
    roof_m: float = 6.2
    # A wheelhouse over each end, and a mast on each.
    wheelhouse_from_end_m: float = 6.0
    wheelhouse_half_x_m: float = 1.4
    wheelhouse_half_z_m: float = 1.0
    wheelhouse_glass_m: tuple[float, float] = (6.7, 7.3)
    wheelhouse_roof_m: float = 7.6
    mast_top_m: float = 9.6
    mast_half_m: float = 0.15


def build_star_ferry(p: StarFerry | None = None) -> MeshData:
    """Green hull with a black fender belt, two white saloons with their window
    bands, a green roof, and a wheelhouse and mast over each end."""
    p = p or StarFerry()
    half_x, half_z = p.beam_m / 2.0, p.length_m / 2.0

    def section(y: float, inset: float, end: float, cut: float) -> tuple[Point, ...]:
        return ring(y, half_x - inset, -half_z + end, half_z - end, cut)

    proud = -p.fender_proud_m
    hull = loft(
        [
            section(-p.hull_below_m, 0.5, 0.8, p.end_cut_m - 0.5),
            section(p.fender_low_m, 0.0, 0.0, p.end_cut_m),
            section(p.fender_low_m, proud, proud, p.end_cut_m),
            section(p.fender_high_m, proud, proud, p.end_cut_m),
            section(p.fender_high_m, 0.0, 0.0, p.end_cut_m),
            section(p.deck_m, 0.0, 0.0, p.end_cut_m),
        ],
        [FERRY_GREEN.colour, FENDER.colour, FENDER.colour, FENDER.colour, FERRY_GREEN.colour],
        bottom=FERRY_GREEN.colour,
        top=FERRY_GREEN.colour,
        name="star_ferry_hull",
    )

    window_bands = [FERRY_WHITE.colour, GLASS.colour, FERRY_WHITE.colour]

    def saloon(
        heights: Sequence[float], bands: list[Colour], inset: float, end: float, name: str
    ) -> MeshData:
        cut = p.end_cut_m - end * 0.4
        return loft(
            [section(y, inset, end, cut) for y in heights],
            bands,
            bottom=None,
            top=bands[-1],
            name=name,
        )

    lower = saloon(
        (p.deck_m, *p.lower_glass_m, p.upper_deck_m),
        window_bands,
        p.lower_inset_m,
        p.lower_end_m,
        "star_ferry_lower_saloon",
    )
    upper = saloon(
        (p.upper_deck_m, *p.upper_glass_m, p.roof_band_m, p.roof_m),
        [*window_bands, FERRY_GREEN.colour],
        p.upper_inset_m,
        p.upper_end_m,
        "star_ferry_upper_saloon",
    )
    ends: list[MeshData] = []
    for side in (-1.0, 1.0):
        z = side * (half_z - p.wheelhouse_from_end_m)
        ends.append(
            loft(
                [
                    ring(
                        y,
                        p.wheelhouse_half_x_m,
                        z - p.wheelhouse_half_z_m,
                        z + p.wheelhouse_half_z_m,
                        0.3,
                    )
                    for y in (p.roof_m, *p.wheelhouse_glass_m, p.wheelhouse_roof_m)
                ],
                [FERRY_WHITE.colour, GLASS.colour, FERRY_WHITE.colour],
                bottom=None,
                top=FERRY_GREEN.colour,
                name=f"star_ferry_wheelhouse_{side:+.0f}",
            )
        )
        ends.append(
            box(
                (-p.mast_half_m, p.wheelhouse_roof_m, z - p.mast_half_m),
                (p.mast_half_m, p.mast_top_m, z + p.mast_half_m),
                FERRY_WHITE.colour,
                name=f"star_ferry_mast_{side:+.0f}",
            )
        )
    return replace(
        merge([hull, lower, upper, *ends], name=f"star_ferry{COLLISION_SUFFIX}"),
        material=MATERIAL,
    )


def build_landmarks() -> list[tuple[str, MeshData]]:
    return [
        (CENTRAL_PLAZA_FILE, build_central_plaza()),
        (STAR_FERRY_FILE, build_star_ferry()),
    ]


def write_landmarks(out_dir: Path) -> list[tuple[Path, int, MeshData]]:
    """Check the palette, then write one `.glb` each."""
    check_palette()
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
