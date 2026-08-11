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

from pipeline.buildings import COLLISION_SUFFIX  # noqa: E402
from pipeline.config import Material, check_material_exposure, load_city  # noqa: E402
from pipeline.gltf import MeshData, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import Colour, Point, box, loft, polygon_facing, ring  # noqa: E402

LOG = logging.getLogger("make_landmark")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "landmarks"

# ≠ `city_facade`, deliberately: `generated_scene_import.gd` swaps that name for
# the tile shader, whose `TEXCOORD_0`/`TEXCOORD_1` payloads these models do not
# author. Any other name gets the vertex-colour `BaseMaterial3D` path instead.
MATERIAL = "landmark_vertex"

HKCEC_FILE = "hkcec.glb"
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
class WingStation:
    """One cross-section of the roof shell, at `z_m` along the island.

    The wing is a sequence of these rather than a curve, on the chamfer rule
    (`P3-11`): faces stay flat and every station edge stays crisp, so the
    swoop reads as low-poly rather than as failed smoothing.
    """

    z_m: float
    ridge_m: float  # roof height on the centreline
    eave_m: float  # roof height where it meets the outer edge
    half_w_m: float  # eave tip from the centreline


@dataclass(frozen=True)
class Hkcec:
    """Phase 2 — the island wing and its atrium block, stem `B358761603301063`.

    Dimensions read from sheet `11-SW-9D`: iB1000 block 1103124251 ("Hong Kong
    Convention and Exhibition Centre", base 3.6 / roof 70.3 mPD) and the 3D-BIT
    mesh (footprint 201 x 349 m, top 71.9 mPD). Local frame: -z is the model's
    north — the harbour side the prow points at.

    ⚠️ **The stations are measured, not styled** — z-band slices of the source
    mesh (p99 extents, 2026-08-12), because the first eyeballed pass got the
    building's shape backwards: the roof is a ~63-67 m *plateau* along the
    whole island whose **edges** roll down (that roll is the wing — strongest
    mid-south, where edges reach ~27 m), the plan is widest at the *south*
    (~109 m half-width) and tapers to a ~45 m prow at the north, where the
    section folds over the nose. The cross-section between ridge and eave is
    an arc sampled at `arc_points` — chamfered facets, never smoothed
    (`P3-11`), but enough of them that the shell reads doubly curved the way
    the source's 41k triangles did.
    """

    podium_m: float = 8.0  # concrete base band
    wall_inset_m: float = 10.0  # curtain stands this far inside the eave tips
    fascia_m: float = 1.8  # roof edge thickness — the line the eye reads
    corner_cut_m: float = 10.0
    arc_points: int = 9  # cross-section samples, eave to eave
    # The louvre bands: the real curtain carries horizontal white walkway
    # bands, and they are placed as fractions of each station's own wall
    # height so a band can never climb through the roof where the eaves dip.
    band_fractions: tuple[tuple[float, float], ...] = ((0.38, 0.44), (0.72, 0.78))
    stations: tuple[WingStation, ...] = (
        WingStation(-158.0, 63.0, 58.0, 40.0),  # prow: the roof folds over the nose
        WingStation(-133.0, 64.0, 55.0, 54.0),
        WingStation(-116.0, 66.0, 50.0, 60.0),
        WingStation(-99.0, 67.0, 42.0, 74.0),  # plateau, edges starting to roll
        WingStation(-82.0, 67.0, 38.0, 80.0),
        WingStation(-65.0, 66.0, 38.0, 85.0),
        WingStation(-48.0, 65.0, 34.0, 90.0),
        WingStation(-31.0, 65.0, 31.0, 98.0),
        WingStation(-14.0, 64.0, 28.0, 105.0),  # deepest roll of the wing
        WingStation(4.0, 64.0, 34.0, 108.0),
        WingStation(21.0, 64.0, 33.0, 109.0),  # widest — the south, not the prow
        WingStation(38.0, 65.0, 35.0, 102.0),
        WingStation(46.0, 65.0, 38.0, 96.0),  # hand-off to the atrium block
    )
    # ⚠️ **The building bridges the streets, and the model must too.** Expo
    # Drive passes under the halls (the spawn line is literally "underneath
    # HKCEC Phase II") and the Convention Avenue network runs under the south
    # zone — the source mesh is measurably elevated there (bottom 25-50 m over
    # local z 94..144). A solid base would dead-end real roads into concrete,
    # so everything south of `deck_north_z_m` stands on a deck over street
    # level — but a deck on bare piers reads as a building on stilts from the
    # kerb (review, 2026-08-12), so the under-deck is `infill`: solid to the
    # soffit everywhere a carriageway does not need daylight, leaving the
    # streets real portals.
    deck_north_z_m: float = -75.0  # north of this the hall is grounded
    deck_bottom_m: float = 12.0  # ~10 m of headroom over the carriageways
    deck_top_m: float = 18.0
    # Deck plan half-widths by z: the island stations to z 46, then the
    # measured south-zone slices tapering to the link's landward end.
    deck_profile: tuple[tuple[float, float], ...] = (
        (-75.0, 80.0),
        (-48.0, 90.0),
        (-31.0, 98.0),
        (-14.0, 105.0),
        (4.0, 108.0),
        (21.0, 109.0),
        (38.0, 102.0),
        (46.0, 96.0),
        (64.0, 84.0),
        (84.0, 80.0),
        (104.0, 72.0),
        (124.0, 66.0),
        (144.0, 62.0),
        (164.0, 58.0),
        (184.0, 40.0),
        (191.0, 30.0),
    )
    # Pier plan positions, authored against the shipped road graph: every
    # candidate on a 26 m grid was tested against densely sampled carriageway
    # polylines in the model's local frame and kept only at >= 8 m clearance
    # (2026-08-12). Rows over the densest crossing (local z 105..130) are
    # empty on purpose — that is the span the real building bridges.
    piers: tuple[tuple[float, float], ...] = (
        (-52.0, -70.0),
        (-26.0, -70.0),
        (26.0, -70.0),
        (52.0, -70.0),
        (78.0, -45.0),
        (-52.0, -20.0),
        (0.0, -20.0),
        (26.0, -20.0),
        (52.0, -20.0),
        (78.0, -20.0),
        (-78.0, 5.0),
        (-52.0, 5.0),
        (-26.0, 5.0),
        (0.0, 5.0),
        (26.0, 5.0),
        (52.0, 5.0),
        (78.0, 5.0),
        (-78.0, 30.0),
        (-52.0, 30.0),
        (-26.0, 30.0),
        (0.0, 30.0),
        (26.0, 30.0),
        (52.0, 30.0),
        (78.0, 30.0),
        (-52.0, 55.0),
        (-26.0, 55.0),
        (0.0, 55.0),
        (0.0, 80.0),
        (26.0, 80.0),
        (-26.0, 155.0),
        (0.0, 155.0),
        (26.0, 155.0),
        (-26.0, 178.0),
        (26.0, 189.0),
    )
    pier_half_m: float = 1.4
    # Solid under-deck mass, `(x0, z0, x1, z1)` in plan, plinth to soffit —
    # derived from the shipped road graph the way the piers were (2026-08-12):
    # carriageway polylines densified to 2 m in the local frame, every 4 m
    # grid cell of the deck plan kept solid at >= `width/2 + 4.8 m` from every
    # surface sample (the pier rule's 8 m on a 6.4 m carriageway), cells
    # merged greedily into rectangles, none thinner than 8 m. The rim stays
    # 6 m inboard of the deck edge so the slab still reads as a deck. Bypass-
    # tunnel samples (local y < -2.5) are buried and carve nothing; the Lung
    # Wo interchange (z 93..130) stays fully bridged — the real link bridges
    # it too.
    infill: tuple[tuple[float, float, float, float], ...] = (
        (-72.0, -75.0, -36.0, -55.0),
        (36.0, -39.0, 88.0, -3.0),
        (-16.0, -27.0, 16.0, -19.0),
        (-16.0, -19.0, 36.0, -3.0),
        (88.0, -19.0, 96.0, -3.0),
        (-64.0, -15.0, -36.0, -3.0),
        (-76.0, -3.0, 72.0, 45.0),
        (72.0, -3.0, 100.0, 25.0),
        (-68.0, 45.0, 12.0, 57.0),
        (-64.0, 57.0, -28.0, 65.0),
        (60.0, 65.0, 72.0, 89.0),
        (40.0, 69.0, 60.0, 77.0),
        (4.0, 133.0, 40.0, 169.0),
        (-32.0, 153.0, 0.0, 177.0),
    )
    atrium_glass_m: float = 48.0  # measured south-zone tops 56-67, eased under the roof
    atrium_roof_m: float = 53.0


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


def _shell_section(station: WingStation, arc_points: int) -> list[tuple[float, float]]:
    """One station's roof profile, eave to eave: `(x, y)` samples of an arc.

    `y(t) = eave + (ridge - eave) * (1 - t^2)` over `t` in [-1, 1] — a barrel
    of flat facets. The count is the chamfer budget: enough that the shell
    reads doubly curved at review distance, few enough that every facet is
    still a face (`P3-11`).
    """
    ts = np.linspace(-1.0, 1.0, arc_points)
    return [
        (
            float(t) * station.half_w_m,
            station.eave_m + (station.ridge_m - station.eave_m) * float(1.0 - t * t),
        )
        for t in ts
    ]


def _wing(p: Hkcec, colour: Colour) -> MeshData:
    """The roof shell: arced top, fascia edges, flat soffit, two caps.

    Hand-assembled from `polygon_facing` rather than lofted, because a loft's
    band takes one colour per band and one centroid per profile — and this
    shape's soffit faces down while its crown faces up in the *same* band.
    Outward hints are stated per face; the winding corrects itself.
    """
    parts: list[MeshData] = []
    sections = [_shell_section(station, p.arc_points) for station in p.stations]
    for i in range(len(p.stations) - 1):
        a, b = p.stations[i], p.stations[i + 1]
        near, far = sections[i], sections[i + 1]
        for j in range(p.arc_points - 1):
            (x0, y0), (x1, y1) = near[j], near[j + 1]
            (x2, y2), (x3, y3) = far[j], far[j + 1]
            outward = ((x0 + x1) / p.arc_points, 1.0, 0.0)
            parts.append(
                polygon_facing(
                    [(x0, y0, a.z_m), (x1, y1, a.z_m), (x3, y3, b.z_m), (x2, y2, b.z_m)],
                    colour,
                    outward,
                    name=f"wing_{i}_{j}",
                )
            )
        for side in (-1.0, 1.0):
            parts.append(
                polygon_facing(
                    [
                        (side * a.half_w_m, a.eave_m, a.z_m),
                        (side * b.half_w_m, b.eave_m, b.z_m),
                        (side * b.half_w_m, b.eave_m - p.fascia_m, b.z_m),
                        (side * a.half_w_m, a.eave_m - p.fascia_m, a.z_m),
                    ],
                    colour,
                    (side, 0.0, 0.0),
                    name=f"wing_fascia_{i}_{side}",
                )
            )
        parts.append(
            polygon_facing(
                [
                    (-a.half_w_m, a.eave_m - p.fascia_m, a.z_m),
                    (a.half_w_m, a.eave_m - p.fascia_m, a.z_m),
                    (b.half_w_m, b.eave_m - p.fascia_m, b.z_m),
                    (-b.half_w_m, b.eave_m - p.fascia_m, b.z_m),
                ],
                colour,
                (0.0, -1.0, 0.0),
                name=f"wing_soffit_{i}",
            )
        )

    for index, forward in ((0, -1.0), (len(p.stations) - 1, 1.0)):
        station = p.stations[index]
        cap = [(x, y, station.z_m) for x, y in sections[index]]
        cap.append((station.half_w_m, station.eave_m - p.fascia_m, station.z_m))
        cap.append((-station.half_w_m, station.eave_m - p.fascia_m, station.z_m))
        parts.append(polygon_facing(cap, colour, (0.0, 0.0, forward), name=f"wing_cap_{forward}"))
    return merge(parts, name="wing")


def _profile_ring(
    profile: Sequence[tuple[float, float]], y: float, inset: float = 0.0
) -> tuple[Point, ...]:
    """A closed plan ring from a `(z, half_width)` profile, at height `y`.

    Walking the profile down one side and back up the other, the same shape
    `_wall_ring` walks the stations.
    """
    left = [(-(half_w - inset), y, z) for z, half_w in profile]
    right = [(half_w - inset, y, z) for z, half_w in reversed(profile)]
    return tuple(left + right)


def _wall_ring(p: Hkcec, fraction: float) -> tuple[Point, ...]:
    """The hall's plan as a ring: the wing's stations, brought inboard.

    Walking the stations north-to-south down one side and back up the other
    gives a closed ring that tapers wherever the roof does. `fraction` places
    the ring between each station's own floor and soffit — the floor is the
    podium where the hall is grounded and the deck top where it bridges the
    streets — so a louvre band follows the roofline and can never climb
    through it where the eaves dip.
    """
    points: list[tuple[float, float, float]] = []
    for station in p.stations:
        half_w = max(station.half_w_m - p.wall_inset_m, 8.0)
        floor = p.podium_m if station.z_m <= p.deck_north_z_m else p.deck_top_m
        soffit = station.eave_m - p.fascia_m
        points.append((half_w, floor + fraction * (soffit - floor), station.z_m))
    left = [(-half_w, y, z) for half_w, y, z in points]
    right = [(half_w, y, z) for half_w, y, z in reversed(points)]
    return tuple(left + right)


# Every hero's merged node name ends in `buildings.py`'s COLLISION_SUFFIX: the
# visible mesh doubles as its own static trimesh collider, the tile precedent —
# and it matters here because excluding the source building also removed the
# tile collision that used to stand on its footprint. Same importer-suffix
# caution as `make_vehicle.py`: nothing else may end in _wheel/_convcol/etc.
def build_hkcec(p: Hkcec | None = None) -> MeshData:
    """Grounded north hall, street-bridging deck over solid infill and portal
    piers, banded glass under the wing, and the atrium run to the landward
    end."""
    p = p or Hkcec()
    north = p.stations[0].z_m
    grounded = max(station.half_w_m for station in p.stations if station.z_m <= p.deck_north_z_m)
    base = loft(
        [
            ring(
                -PLINTH_DEPTH_M,
                grounded + PLINTH_FLARE_M,
                north - PLINTH_FLARE_M,
                p.deck_north_z_m,
                p.corner_cut_m,
            ),
            ring(p.podium_m, grounded, north, p.deck_north_z_m, p.corner_cut_m),
        ],
        [CONCRETE.colour],
        bottom=CONCRETE.colour,
        top=CONCRETE.colour,
        name="hkcec_base",
    )
    deck = loft(
        [
            _profile_ring(p.deck_profile, p.deck_bottom_m),
            _profile_ring(p.deck_profile, p.deck_top_m),
        ],
        [CONCRETE.colour],
        bottom=CONCRETE.colour,
        top=CONCRETE.colour,
        name="hkcec_deck",
    )
    infill = [
        box(
            (x0, -PLINTH_DEPTH_M, z0),
            (x1, p.deck_bottom_m, z1),
            CONCRETE.colour,
            name=f"hkcec_infill_{index}",
        )
        for index, (x0, z0, x1, z1) in enumerate(p.infill)
    ]
    # Piers the infill swallowed would render as buried boxes; only the ones
    # still standing in a street portal survive.
    piers = [
        box(
            (x - p.pier_half_m, -PLINTH_DEPTH_M, z - p.pier_half_m),
            (x + p.pier_half_m, p.deck_bottom_m, z + p.pier_half_m),
            CONCRETE.colour,
            name=f"hkcec_pier_{index}",
        )
        for index, (x, z) in enumerate(p.piers)
        if not any(x0 <= x <= x1 and z0 <= z <= z1 for x0, z0, x1, z1 in p.infill)
    ]
    # The glass hall follows the roof plan inboard of the eaves — so no wall
    # pokes out past the overhang, and the curtain rises to meet the soffit
    # everywhere. The intermediate rings are the louvre bands.
    fractions = [0.0]
    for band_low, band_high in p.band_fractions:
        fractions.extend((band_low, band_high))
    fractions.append(1.0)
    band_colours: list[Colour] = []
    for index in range(len(fractions) - 1):
        band_colours.append(ALUMINIUM.colour if index % 2 == 1 else GLASS.colour)
    walls = loft(
        [_wall_ring(p, fraction) for fraction in fractions],
        band_colours,
        bottom=GLASS.colour,
        top=GLASS.colour,
        name="hkcec_walls",
    )
    wing = _wing(p, ALUMINIUM.colour)
    south = [(z, half_w) for z, half_w in p.deck_profile if z >= p.stations[-1].z_m]
    atrium = loft(
        [
            _profile_ring(south, p.deck_top_m, 4.0),
            _profile_ring(south, p.atrium_glass_m, 6.0),
            _profile_ring(south, p.atrium_roof_m, 12.0),
        ],
        [GLASS.colour, ALUMINIUM.colour],
        bottom=GLASS.colour,
        top=ALUMINIUM.colour,
        name="hkcec_atrium",
    )
    return replace(
        merge([base, deck, *infill, *piers, walls, wing, atrium], name=f"hkcec{COLLISION_SUFFIX}"),
        material=MATERIAL,
    )


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
