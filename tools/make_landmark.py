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
# HKCEC's own pair, read off the Expo Drive East street views (2024): the
# elevation is *pale* panels carrying thin dark ribbon glazing, under a roof
# *darker* than the wall — the first shipped treatment had both inverted.
PANEL = Material(
    "panel_pale",
    (134, 128, 119),
    42.0,
    "pale precast and granite curtain panels, 35-45%",
)
ROOF_GREY = Material(
    "roof_grey",
    (90, 96, 99),
    22.0,
    "pearl-grey coated aluminium re-roof, 18-28%",
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

PALETTE = (ALUMINIUM, PANEL, ROOF_GREY, GLASS, CONCRETE, GOLD, GOLD_BAND)


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
    """One cross-section of the island, at `z_m` — roof *and* hull.

    The wing is a sequence of these rather than a curve, on the chamfer rule
    (`P3-11`): faces stay flat and every station edge stays crisp, so the
    swoop reads as low-poly rather than as failed smoothing.

    Asymmetric on purpose: the island's plan is a curved, eastward-leaning
    banana (`mid_m` drifts ~-22 → +13 south), the east flank's roof rolls far
    lower than the west's, and the hull edges are their own measurement — at
    the prow the wall stands 15-20 m inside the fold, mid-south it meets the
    roof edge nearly flush. A symmetric model had fattened the 14 m nose to
    40 m, which is most of why the source mesh read closer to the street
    photos than the first hero did.
    """

    z_m: float
    mid_m: float  # plan centre of the roof at this station
    half_m: float  # eave tip each side of `mid_m`
    ridge_m: float  # roof height on the centreline
    eave_w_m: float  # roof height at the west edge
    eave_e_m: float  # east edge — the flank that sweeps lowest
    hull_w_m: float  # the wall's own west edge in plan
    hull_e_m: float


@dataclass(frozen=True)
class Hkcec:
    """Phase 2 — the island wing and its atrium block, stem `B358761603301063`.

    Dimensions read from sheet `11-SW-9D`: iB1000 block 1103124251 ("Hong Kong
    Convention and Exhibition Centre", base 3.6 / roof 70.3 mPD) and the 3D-BIT
    mesh (footprint 201 x 349 m, top 71.9 mPD). Local frame: -z is the model's
    north — the harbour side the prow points at.

    ⚠️ **The stations are measured, not styled** — 8 m z-band slices of the
    source mesh (2026-08-12, re-sliced at double density after the user judged
    the source closer to the street photos than the first hero), because the
    eyeballed pass got the shape backwards and the symmetric pass got it fat:
    the roof is a ~63-67 m *plateau* whose **edges** roll down (that roll is
    the wing — deepest on the *east* flank, where edges reach ~20 m), the plan
    is a curved eastward-leaning banana (station `mid_m` drifts -22 → +13)
    that is widest at the *south* (~97 m half-width) and tapers to a **14 m**
    prow folding over the nose. The cross-section between ridge and eaves is
    an arc sampled at `arc_points` — chamfered facets, never smoothed
    (`P3-11`), but enough of them that the shell reads doubly curved the way
    the source's 41k triangles did.
    """

    podium_m: float = 8.0  # concrete base band
    fascia_m: float = 1.8  # roof edge thickness — the line the eye reads
    arc_points: int = 17  # cross-section samples, eave to eave
    # The ribbon strips: the street views (Expo Drive East, 2024) read the
    # elevation as pale panels carrying thin *dark* glazing ribbons — the
    # first treatment had the values inverted (dark glass hull, light bands).
    # The ribbons are storey lines at **constant absolute heights**, not
    # fractions of the wall: fractions squished every strip into a zebra fan
    # where the east roll pinches the wall (user review, 2026-08-12). Placed
    # by elevation, the descending roofline cuts the strips off one by one
    # instead — `_wall_ring` clamps each line into [floor, soffit], so a strip
    # the roof has passed degrades to an invisible hairline.
    # Pitch and thickness measured off the street views by pixel profile
    # (2026-08-12): the strips hold ~30% of the pitch (dark share 0.27-0.37
    # across six sampled columns) and the hull carries 9-10 bands over ~45 m
    # of wall — ~4.8 m pitch, ~1.5 m strip.
    ribbon_first_m: float = 15.0  # first strip's underside
    ribbon_pitch_m: float = 4.8
    ribbon_m: float = 1.5  # strip thickness
    ribbon_count: int = 10
    # Re-sliced 2026-08-12 after the source-vs-hero comparison: 8 m z-bands of
    # the source mesh (p1/p99 extents; eaves the p90 of the outer 12% each
    # side, 3-band rolling median; hull edges the p1/p99 of points 18-40 m up,
    # one-flank bands interpolated from their neighbours; prow hull falls back
    # to the roof edge less 10 m where the hall hides under the fold), then
    # every column faired with a sigma = 1-band Gaussian along z: the SOM roof
    # is a fair curve, and 1-3 m of slice noise reads as creases once flat
    # facets amplify it (user call, same day: one smooth sweep, kept faceted).
    stations: tuple[WingStation, ...] = (
        WingStation(-156.0, -22.4, 18.3, 66.2, 62.8, 59.8, -31.7, -9.9),
        WingStation(-148.0, -22.1, 22.9, 66.3, 61.6, 57.7, -32.1, -9.3),
        WingStation(-140.0, -21.2, 28.5, 66.4, 59.6, 54.1, -34.3, -5.8),
        WingStation(-132.0, -19.7, 33.9, 66.6, 57.0, 50.3, -38.9, 3.1),
        WingStation(-124.0, -16.4, 39.9, 66.7, 53.8, 46.2, -44.8, 16.4),
        WingStation(-116.0, -11.0, 47.7, 66.9, 50.0, 41.7, -51.6, 32.6),
        WingStation(-108.0, -4.4, 57.0, 66.9, 46.6, 37.9, -58.0, 50.9),
        WingStation(-100.0, 1.3, 65.1, 66.8, 45.2, 36.1, -63.1, 66.0),
        WingStation(-92.0, 3.9, 70.5, 66.8, 45.4, 35.4, -66.6, 74.5),
        WingStation(-84.0, 4.0, 74.5, 66.7, 45.5, 34.5, -70.5, 78.4),
        WingStation(-76.0, 2.9, 78.2, 66.2, 42.9, 33.1, -75.3, 81.0),
        WingStation(-68.0, 2.0, 81.3, 65.4, 36.8, 30.9, -79.3, 83.3),
        WingStation(-60.0, 1.7, 83.6, 64.8, 32.1, 28.4, -81.7, 85.3),
        WingStation(-52.0, 2.2, 85.2, 64.5, 30.6, 26.9, -82.8, 87.4),
        WingStation(-44.0, 3.4, 86.9, 64.7, 30.6, 25.9, -83.0, 89.6),
        WingStation(-36.0, 5.4, 88.7, 64.6, 31.3, 23.8, -83.1, 91.9),
        WingStation(-28.0, 7.7, 90.8, 64.2, 32.6, 21.2, -83.1, 94.1),
        WingStation(-20.0, 9.7, 92.6, 63.9, 34.0, 19.8, -82.9, 95.8),
        WingStation(-12.0, 11.3, 93.8, 63.9, 35.3, 19.6, -82.5, 97.2),
        WingStation(-4.0, 12.4, 94.5, 64.0, 36.0, 19.7, -82.0, 98.4),
        WingStation(4.0, 12.8, 95.3, 64.1, 36.4, 19.7, -82.5, 99.5),
        WingStation(12.0, 12.2, 96.3, 64.2, 36.6, 20.2, -84.1, 100.4),
        WingStation(20.0, 10.5, 96.2, 64.3, 36.5, 22.3, -85.7, 100.9),
        WingStation(28.0, 8.2, 95.4, 64.4, 35.0, 26.2, -87.2, 101.0),
        WingStation(36.0, 7.2, 94.7, 64.5, 32.6, 29.3, -87.5, 100.8),
        WingStation(44.0, 7.6, 93.9, 64.5, 31.0, 30.7, -86.4, 100.7),
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
    # South-zone deck plan `(z, mid, half)` — the measured slices from z 54
    # to the link's landward end, from the same 2026-08-12 re-slice as the
    # stations. The island run (z -76..44) is *derived* from the stations in
    # `build_hkcec`, so a future re-slice cannot leave the deck behind.
    deck_south: tuple[tuple[float, float, float], ...] = (
        (54.0, 9.5, 81.7),
        (66.0, 11.7, 78.8),
        (78.0, 13.8, 75.3),
        (90.0, 14.9, 72.1),
        (102.0, 15.6, 68.4),
        (114.0, 16.3, 64.5),
        (126.0, 16.5, 61.9),
        (138.0, 17.2, 61.0),
        (150.0, 19.7, 60.4),
        (162.0, 21.4, 58.1),
        (174.0, 18.2, 50.4),
        (186.0, 11.1, 38.7),
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
    # The link keeps the sweep going: measured south-zone tops run 61-67 m,
    # so the striped hull rises to `atrium_wall_m` and the grey roof crests
    # above it — the first pass stopped 10 m short at 53.
    atrium_wall_m: float = 57.0
    atrium_roof_m: float = 64.0


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
    """One station's roof profile, west eave to east eave: `(x, y)` arc samples.

    `y(t) = ridge - (ridge - eave_side) * t^2` over `t` in [-1, 1], taking
    each side's own eave — the east flank rolls lower than the west, and one
    quadratic per side keeps the crest at the ridge while the two falls
    disagree. A barrel of flat facets; the count is the chamfer budget
    (`P3-11`).
    """
    ts = np.linspace(-1.0, 1.0, arc_points)
    return [
        (
            station.mid_m + float(t) * station.half_m,
            station.ridge_m
            - (station.ridge_m - (station.eave_w_m if t < 0 else station.eave_e_m)) * float(t * t),
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
            # The y term is ~the roof's rise: big enough that a plateau facet
            # near the centreline reads "up" however its x-offset rounds,
            # small enough that a steep flank facet's sign still comes from
            # the x term.
            outward = ((x0 + x1) / 2.0 - a.mid_m, 40.0, 0.0)
            parts.append(
                polygon_facing(
                    [(x0, y0, a.z_m), (x1, y1, a.z_m), (x3, y3, b.z_m), (x2, y2, b.z_m)],
                    colour,
                    outward,
                    name=f"wing_{i}_{j}",
                )
            )
        # The fascia hangs from the sections' own end samples (t = ±1 is the
        # eave tip), so shell and fascia share bit-identical corners and no
        # hairline can open between them.
        for side, k in ((-1.0, 0), (1.0, -1)):
            (ax, ay), (bx, by) = near[k], far[k]
            parts.append(
                polygon_facing(
                    [
                        (ax, ay, a.z_m),
                        (bx, by, b.z_m),
                        (bx, by - p.fascia_m, b.z_m),
                        (ax, ay - p.fascia_m, a.z_m),
                    ],
                    colour,
                    (side, 0.0, 0.0),
                    name=f"wing_fascia_{i}_{side}",
                )
            )
        (awx, awy), (aex, aey) = near[0], near[-1]
        (bwx, bwy), (bex, bey) = far[0], far[-1]
        parts.append(
            polygon_facing(
                [
                    (awx, awy - p.fascia_m, a.z_m),
                    (aex, aey - p.fascia_m, a.z_m),
                    (bex, bey - p.fascia_m, b.z_m),
                    (bwx, bwy - p.fascia_m, b.z_m),
                ],
                colour,
                (0.0, -1.0, 0.0),
                name=f"wing_soffit_{i}",
            )
        )

    for index, forward in ((0, -1.0), (len(p.stations) - 1, 1.0)):
        station = p.stations[index]
        section = sections[index]
        cap = [(x, y, station.z_m) for x, y in section]
        cap.append((section[-1][0], section[-1][1] - p.fascia_m, station.z_m))
        cap.append((section[0][0], section[0][1] - p.fascia_m, station.z_m))
        parts.append(polygon_facing(cap, colour, (0.0, 0.0, forward), name=f"wing_cap_{forward}"))
    return merge(parts, name="wing")


def _profile_ring(
    profile: Sequence[tuple[float, float, float]], y: float, inset: float = 0.0
) -> tuple[Point, ...]:
    """A closed plan ring from a `(z, mid, half)` profile, at height `y`.

    Walking the profile down one side and back up the other, the same shape
    `_wall_ring` walks the stations.
    """
    left = [(mid - (half - inset), y, z) for z, mid, half in profile]
    right = [(mid + (half - inset), y, z) for z, mid, half in reversed(profile)]
    return tuple(left + right)


def _hull_ring(stations: Sequence[WingStation], y: float, flare: float = 0.0) -> tuple[Point, ...]:
    """The measured hull edges as a closed plan ring at height `y`."""
    left = [(s.hull_w_m - flare, y, s.z_m) for s in stations]
    right = [(s.hull_e_m + flare, y, s.z_m) for s in reversed(stations)]
    return tuple(left + right)


def _ribbon_lines(p: Hkcec) -> list[float]:
    """The strips' absolute elevations, flattened: lo, hi, lo, hi, ..."""
    lines: list[float] = []
    for index in range(p.ribbon_count):
        lo = p.ribbon_first_m + index * p.ribbon_pitch_m
        lines.extend((lo, lo + p.ribbon_m))
    return lines


def _level_height(lines: Sequence[float], level: int, floor: float, soffit: float) -> float:
    """One banding ring's height: level 0 is the floor, the last is the
    soffit, and the ones between are the ribbon lines clamped into the wall.

    A line the roof has descended past clamps onto the soffit exactly —
    coincident rings make a dead band degenerate, and `loft` drops it.
    """
    if level == 0:
        return floor
    if level > len(lines):
        return soffit
    return min(max(lines[level - 1], floor), soffit)


def _wall_ring(p: Hkcec, lines: Sequence[float], level: int) -> tuple[Point, ...]:
    """The hall's hull as a ring, at one banding level.

    Walking the stations north-to-south down the west edges and back up the
    east gives a closed ring on the measured hull plan. The ribbon strips sit
    at constant absolute elevations — storey lines, as on the real elevation —
    and each is clamped into the wall between that station's floor (podium
    where grounded, deck top where bridging) and that side's soffit, so the
    descending roofline cuts the strips off one by one instead of squeezing
    them together.
    """
    left: list[Point] = []
    right: list[Point] = []
    for station in p.stations:
        floor = p.podium_m if station.z_m <= p.deck_north_z_m else p.deck_top_m
        # Where the roof rolls all the way down to the deck (the east flank
        # around z -20..-4 lands within a fascia of deck level), the wall
        # pinches to half a metre rather than to zero.
        soffit_w = max(station.eave_w_m - p.fascia_m, floor + 0.5)
        soffit_e = max(station.eave_e_m - p.fascia_m, floor + 0.5)
        left.append((station.hull_w_m, _level_height(lines, level, floor, soffit_w), station.z_m))
        right.append((station.hull_e_m, _level_height(lines, level, floor, soffit_e), station.z_m))
    return tuple(left + list(reversed(right)))


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
    # The grounded base follows the measured hull — a rectangle here left the
    # podium jutting ~60 m east of the real prow, the other half of why the
    # source mesh read closer to the photos than the first hero.
    grounded = [s for s in p.stations if s.z_m <= p.deck_north_z_m]
    base = loft(
        [
            _hull_ring(grounded, -PLINTH_DEPTH_M, PLINTH_FLARE_M),
            _hull_ring(grounded, p.podium_m),
        ],
        [CONCRETE.colour],
        bottom=CONCRETE.colour,
        top=CONCRETE.colour,
        name="hkcec_base",
    )
    # The deck's island run is the stations' own plan, starting one station
    # north of `deck_north_z_m` so the slab tucks under the grounded hall's
    # south face.
    deck_profile = [
        (s.z_m, s.mid_m, s.half_m) for s in p.stations if s.z_m >= p.deck_north_z_m - 1.0
    ] + list(p.deck_south)
    deck = loft(
        [
            _profile_ring(deck_profile, p.deck_bottom_m),
            _profile_ring(deck_profile, p.deck_top_m),
        ],
        [CONCRETE.colour],
        bottom=CONCRETE.colour,
        top=CONCRETE.colour,
        name="hkcec_deck",
    )
    # Tops reach 5 cm past the soffit plane so the hidden face sits inside the
    # slab instead of exactly coplanar with it — coplanar faces z-fight.
    infill = [
        box(
            (x0, -PLINTH_DEPTH_M, z0),
            (x1, p.deck_bottom_m + 0.05, z1),
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
            (x + p.pier_half_m, p.deck_bottom_m + 0.05, z + p.pier_half_m),
            CONCRETE.colour,
            name=f"hkcec_pier_{index}",
        )
        for index, (x, z) in enumerate(p.piers)
        if not any(x0 <= x <= x1 and z0 <= z <= z1 for x0, z0, x1, z1 in p.infill)
    ]
    # The hall's hull follows the measured plan and rises to meet the soffit
    # everywhere. The intermediate rings are the ribbon lines — storey lines
    # at constant elevations, so the strips stay level around the whole curve
    # and terminate into the roofline where it descends. No caps: the floor
    # ring is buried in the podium and deck, and the soffit ring lies exactly
    # on the wing's underside.
    lines = _ribbon_lines(p)
    levels = len(lines) + 2
    band_colours: list[Colour] = []
    for index in range(levels - 1):
        band_colours.append(GLASS.colour if index % 2 == 1 else PANEL.colour)
    walls = loft(
        [_wall_ring(p, lines, level) for level in range(levels)],
        band_colours,
        bottom=None,
        top=None,
        name="hkcec_walls",
    )
    wing = _wing(p, ROOF_GREY.colour)
    # The link continues the striped hull south — the street views show the
    # same pale panels and ribbons on the south zone, not a glass block —
    # with the grey roof cresting over it. Same absolute ribbon lines, so the
    # strips run level across the island-to-link joint. No bottom cap: that
    # ring lies on the deck top.
    south = [row for row in deck_profile if row[0] >= p.stations[-1].z_m]
    atrium_rings = [
        _profile_ring(south, _level_height(lines, level, p.deck_top_m, p.atrium_wall_m), 4.0)
        for level in range(levels)
    ]
    atrium_rings.append(_profile_ring(south, p.atrium_roof_m, 12.0))
    atrium = loft(
        atrium_rings,
        [*band_colours, ROOF_GREY.colour],
        bottom=None,
        top=ROOF_GREY.colour,
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
