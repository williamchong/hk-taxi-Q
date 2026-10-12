"""Generate the parked roster's library (`P3-72`, `Q161`).

    python tools/make_parked.py
    python tools/make_parked.py --out-dir /tmp/vehicles --report

One `.glb`, `parked.glb`, holding one node per roster kind — `car_a`, `car_b`,
`taxi`, `minibus`, `bus`, `coach`, `van`, `tram`, `motorcycle` — which
`pipeline/parked.py` stands by a placements document, the shape every prop
library takes (`P5-2`). Each node is a MeshGroup of `vehicle_*` material parts
(`make_vehicle.material_parts`), so `generated_scene_import.gd` merges it into
one `vehicle_body` surface on `vehicle_body.tres`: the glass, the lamps and the
paint shade as the player's taxi does, and every lens stays dark because no
`vehicle_lamps.gd` drives a parked car.

**Real footprints, not toy proportions.** A parked car sits beside the
player's Crown Comfort, which has run on its real wheelbase since `Q153`, and
a toy beside it reads as a toy. The lengths and widths here are the ones
`hong_kong.yaml`'s `parked.vehicles:` places by, and `tests/test_make_parked.py`
pins the two tables to each other.

**Detailed inside the footprint** (`P3-75`). The engine sizes each parked
vehicle's collider from this mesh's own box (`parked_layer.gd`), so nothing
may stand proud of it: the body is drawn `SKIN_M` inside the flanks and a
bumper's depth inside the ends, and the mirrors, handles, plates and bumpers
stand in that margin. A parked car's mirrors are folded, as they are on the
street, which is what lets them fit.

**Frame.** Nose at `-Z` (north, the library convention `placed_positions`
stands at a bearing), `+Y` up, the ground at `y = 0` — a placement's `pos` is
the road's own height. Wheels are baked in: a parked car's wheels never turn.

Output goes to `game/assets/authored/vehicles/`, which is **committed** — these
are hand-authored assets under CC BY-SA 4.0, not build output. See LICENSING.md.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_vehicle import (  # noqa: E402
    AMBER,
    BADGE_GREEN,
    BODY_MATERIAL,
    DARK,
    GLASS,
    LAMP,
    RED,
    SILVER,
    _marked,
    _rake_run_m,
    _wheel,
    material_parts,
)
from pipeline.gltf import MeshData, MeshGroup, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import (  # noqa: E402
    Colour,
    box,
    box_at,
    flank_edges,
    hexahedron,
    loft,
    polygon_facing,
    ring,
)

LOG = logging.getLogger("make_parked")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "vehicles"
LIBRARY_FILE = "parked.glb"

# Liveries. Flat, three to five a vehicle (`ART_DESIGN.md`), each one a
# vehicle a Hong Kong street actually carries.
WHITE = (236, 236, 232)
NAVY = (38, 56, 104)
CREAM = (240, 232, 200)
MINIBUS_GREEN = (24, 122, 72)
CITYBUS_YELLOW = (238, 194, 44)
# Citybus's lower skirt, under the yellow.
CITYBUS_BLUE = (30, 70, 150)
TRAM_GREEN = (22, 108, 60)
TRAM_CREAM = (232, 226, 196)
STEEL = (120, 122, 126)

# Fewer segments than the taxi's 18: a parked wheel is looked at from a car
# going past, and four of them a vehicle over nine kinds is where the triangles
# go. Twelve since the arches opened the wheel to view (`P3-75`).
WHEEL_SEGMENTS = 12

# How far inside the footprint the body's flanks are drawn, so a fixture on
# them — a folded mirror, a handle, a pillar, a seam — stands in the margin
# and the mesh's box stays the footprint the collider is sized from.
SKIN_M = 0.012
# How far a lamp, plate or board stands off the face it is seated on.
FIXTURE_PROUD_M = 0.012
# The arch's radius over the tyre's, and the facets in its curve.
ARCH_CLEARANCE_M = 0.05
ARCH_SEGMENTS = 8
# How deep a wheel well runs in, past the tyre's inner face.
WELL_SPARE_M = 0.06
# Space left above an arch's crown before the waist ring.
WAIST_OVER_ARCH_M = 0.06


@dataclass(frozen=True)
class Shape:
    """One roster kind as proportions, in metres."""

    kind: str
    length_m: float
    width_m: float
    paint: Colour
    roof: Colour
    # The underside's clearance and the body's rings.
    sill_y_m: float
    belt_y_m: float
    roof_y_m: float
    # Where the glasshouse starts and ends along the body, from the nose.
    cabin_front_m: float
    cabin_rear_m: float
    windscreen_rake_deg: float
    backlight_rake_deg: float
    # Chamfer at the vertical corners, and how far the roof draws in.
    corner_cut_m: float
    roof_inset_m: float
    wheel_radius_m: float
    wheel_width_m: float
    # The axles, from the nose.
    axles_m: tuple[float, ...]
    # A second glasshouse over the first (a double-decker, a tram).
    upper_deck: bool = False
    # Wheels along the centreline (a motorcycle), not at the flanks.
    single_track: bool = False
    # A bar at the belt in a second colour (a tram's cream band).
    band: Colour | None = None
    # The band from the sill to the arches' crown, when it is not the paint
    # (Citybus's blue skirt).
    skirt: Colour | None = None
    # The window pillars, when they are not the roof's colour.
    pillar: Colour | None = None
    # Side windows a deck, split by `window_bays - 1` pillars.
    window_bays: int = 2
    bumper: Colour = DARK
    bumper_m: float = 0.06
    bumper_height_m: float = 0.22
    grille: Colour | None = DARK
    plates: bool = True
    # Folded against the glass; a bus's on their stalks would leave the box.
    mirrors: bool = True
    # A handle at the belt behind each side window — on a car, each door's.
    handles: bool = False
    # Wheels in arches. Off, the skirt runs whole to the sill and hides them,
    # and a dark underframe stands in for the trucks (a tram's).
    arches: bool = True
    # Of each deck's height, belt to top: the solid panel under the side
    # glass, and the glass. A tram's windows are a band over a tall panel.
    panel_share: float = 0.0
    glass_share: float = 0.72
    # One lamp centred on the dash (a tram's), or a pair.
    head_lamps: int = 2

    def __post_init__(self) -> None:
        if self.panel_share + self.glass_share >= 1.0:
            raise ValueError(f"{self.kind}: the panel and the glass leave no roof rail")
        if self.head_lamps not in (1, 2):
            raise ValueError(f"{self.kind}: head_lamps is 1 or 2, not {self.head_lamps}")

    @property
    def half_width_m(self) -> float:
        return self.width_m / 2.0

    @property
    def front_z_m(self) -> float:
        return -self.length_m / 2.0

    @property
    def rear_z_m(self) -> float:
        return self.length_m / 2.0

    @property
    def body_half_width_m(self) -> float:
        return self.half_width_m - SKIN_M

    @property
    def body_front_z_m(self) -> float:
        return self.front_z_m + self.bumper_m

    @property
    def body_rear_z_m(self) -> float:
        return self.rear_z_m - self.bumper_m

    @property
    def arch_radius_m(self) -> float:
        return self.wheel_radius_m + ARCH_CLEARANCE_M

    @property
    def waist_y_m(self) -> float:
        """The ring the arches are cut below: over the crown, under the belt."""
        return min(
            self.belt_y_m - 0.03, self.wheel_radius_m + self.arch_radius_m + WAIST_OVER_ARCH_M
        )

    @property
    def skirt_colour(self) -> Colour:
        return self.skirt or self.paint

    @property
    def deck_y_m(self) -> float:
        """Where a double-decker's lower glasshouse ends and the upper starts."""
        return self.belt_y_m + (self.roof_y_m - self.belt_y_m) * 0.5


@dataclass(frozen=True)
class _Glazing:
    """One deck's glasshouse as `_glasshouse` lofts it: belt, the panel's top
    where the glass starts (the belt itself unless `panel_share`), the glass's
    top, and the roof."""

    belt_y: float
    panel_y: float
    glass_y: float
    top_y: float
    # Half-widths at the belt and at the top of the glass.
    belt_half_w: float
    glass_half_w: float
    # The cabin's ends at the belt, and how far each rakes in over the glass.
    front_z: float
    rear_z: float
    front_run: float
    rear_run: float
    cut: float
    inset: float

    def end_z(self, y: float, *, rear: bool) -> float:
        """The raked windscreen's (or backlight's) z at height `y`."""
        t = (y - self.panel_y) / (self.glass_y - self.panel_y)
        return self.rear_z - self.rear_run * t if rear else self.front_z + self.front_run * t

    def glass_top_z(self) -> tuple[float, float]:
        """The side glass's top edge, the shorter of its two — where a pillar,
        a handle or a rack must stand to be on the glass at both ends."""
        return self.front_z + self.front_run + self.cut, self.rear_z - self.rear_run - self.cut

    def roof_end_z(self, *, rear: bool) -> float:
        """Where the roof's flat ends, at the top of the cant rail."""
        if rear:
            return self.rear_z - self.rear_run - self.inset * 0.5
        return self.front_z + self.front_run + self.inset * 0.5

    def side_x(self, y: float) -> float:
        """The side glass's half-width at height `y` — it leans in as it rises."""
        t = (y - self.panel_y) / (self.glass_y - self.panel_y)
        return self.belt_half_w + (self.glass_half_w - self.belt_half_w) * t


def _glazing(shape: Shape, belt_y: float, top_y: float) -> _Glazing:
    panel_y = belt_y + (top_y - belt_y) * shape.panel_share
    glass_rise = (top_y - belt_y) * shape.glass_share
    hw = shape.body_half_width_m
    return _Glazing(
        belt_y=belt_y,
        panel_y=panel_y,
        glass_y=panel_y + glass_rise,
        top_y=top_y,
        belt_half_w=hw,
        glass_half_w=hw - shape.roof_inset_m * 0.6,
        front_z=shape.front_z_m + shape.cabin_front_m,
        rear_z=shape.front_z_m + shape.cabin_rear_m,
        front_run=_rake_run_m(shape.windscreen_rake_deg, glass_rise),
        rear_run=_rake_run_m(shape.backlight_rake_deg, glass_rise),
        cut=shape.corner_cut_m,
        inset=shape.roof_inset_m,
    )


# --------------------------------------------------------------------------
# The body
# --------------------------------------------------------------------------


def _lower(shape: Shape) -> MeshData:
    """Sill to belt: a skirt with the wheel arches cut through its flanks, and
    the body over it, capped — the cap is the bonnet and the boot lid.

    ⚠️ The cap is what the earlier body left out (`top=None`): the glasshouse
    covers only the cabin, so a car showed the road through its bonnet.
    """
    hw = shape.body_half_width_m
    rings = [
        ring(y, hw, shape.body_front_z_m, shape.body_rear_z_m, shape.corner_cut_m)
        for y in (shape.sill_y_m, shape.waist_y_m, shape.belt_y_m)
    ]
    skirt = loft(
        rings[:2],
        [shape.skirt_colour],
        bottom=DARK,
        top=None,
        skip_edges=flank_edges(len(rings[0])) if shape.arches else (),
        name="skirt",
    )
    body = loft(rings[1:], [shape.paint], bottom=None, top=shape.paint, name="lower")
    flanks = [_flank(shape, rings[0], side) for side in (-1.0, 1.0)] if shape.arches else []
    return merge([skirt, body, *flanks], name="lower")


def _arch(shape: Shape, axle_z: float) -> list[tuple[float, float]]:
    """The arch over one wheel as (z, y) knots, sill to sill over the crown."""
    hub = shape.wheel_radius_m
    radius = shape.arch_radius_m
    start = math.asin(max(-1.0, min(1.0, (shape.sill_y_m - hub) / radius)))
    knots = [
        (axle_z - radius * math.cos(a), hub + radius * math.sin(a))
        for a in np.linspace(start, math.pi - start, ARCH_SEGMENTS + 1)
    ]
    # Exactly on the sill, so the run beside it meets it without a sliver.
    knots[0] = (knots[0][0], shape.sill_y_m)
    knots[-1] = (knots[-1][0], shape.sill_y_m)
    return knots


def _axle_zs(shape: Shape) -> list[float]:
    return sorted(shape.front_z_m + axle for axle in shape.axles_m)


def _flank(shape: Shape, sill_ring: Sequence[Sequence[float]], side: float) -> MeshData:
    """One flank of the skirt, a column per knot so the arches are open.

    Spans the ring's own flank edge, so it meets the chamfers the loft drew.
    """
    # Either flank edge: the ring is symmetric, so both span the same z.
    edge = flank_edges(len(sill_ring))[0]
    z_ends = sorted((sill_ring[edge][2], sill_ring[(edge + 1) % len(sill_ring)][2]))
    x = side * shape.body_half_width_m
    sill, waist = shape.sill_y_m, shape.waist_y_m
    bottom: list[tuple[float, float]] = [(z_ends[0], sill)]
    for axle_z in _axle_zs(shape):
        arch = _arch(shape, axle_z)
        if arch[0][0] <= bottom[-1][0] or arch[-1][0] >= z_ends[1]:
            raise ValueError(f"{shape.kind}: the arch at z {axle_z:+.2f} leaves its flank")
        if max(y for _, y in arch) >= waist:
            raise ValueError(f"{shape.kind}: the arch at z {axle_z:+.2f} rises past the waist")
        bottom.extend(arch)
    bottom.append((z_ends[1], sill))
    tag = "l" if side < 0 else "r"
    return merge(
        [
            polygon_facing(
                [(x, y0, z0), (x, y1, z1), (x, waist, z1), (x, waist, z0)],
                shape.skirt_colour,
                (side, 0.0, 0.0),
                name=f"flank_{tag}_{i}",
            )
            for i, ((z0, y0), (z1, y1)) in enumerate(pairwise(bottom))
        ],
        name=f"flank_{tag}",
    )


def _wells(shape: Shape) -> list[MeshData]:
    """What the arches open onto: a dark liner round the tyre and a wall
    inboard of it, so an arch shows a wheel in a well and not the body's
    inside, which back-face culling would show as a hole through the car."""
    hub = shape.wheel_radius_m
    hw = shape.body_half_width_m
    depth = shape.wheel_width_m + WELL_SPARE_M
    parts: list[MeshData] = []
    for side in (-1.0, 1.0):
        x_out, x_in = side * hw, side * (hw - depth)
        for index, axle_z in enumerate(_axle_zs(shape)):
            arch = _arch(shape, axle_z)
            name = f"well_{index}_{'l' if side < 0 else 'r'}"
            for i, ((z0, y0), (z1, y1)) in enumerate(pairwise(arch)):
                mid_y, mid_z = (y0 + y1) / 2.0, (z0 + z1) / 2.0
                parts.append(
                    polygon_facing(
                        [(x_out, y0, z0), (x_out, y1, z1), (x_in, y1, z1), (x_in, y0, z0)],
                        DARK,
                        (0.0, hub - mid_y, axle_z - mid_z),
                        name=f"{name}_liner_{i}",
                    )
                )
            parts.append(
                polygon_facing(
                    [(x_in, y, z) for z, y in arch], DARK, (side, 0.0, 0.0), name=f"{name}_wall"
                )
            )
    return parts


def _glasshouse(
    shape: Shape,
    belt_y: float,
    top_y: float,
    roof: Colour,
    *,
    name: str,
    cap: bool,
    floor: Colour | None = None,
) -> MeshData:
    """Belt to roof: a glass band under a painted cant rail, raked at both ends.

    `floor` closes the underside — the upper deck's, which overhangs the
    lower deck's drawn-in top by `roof_inset_m`.
    """
    g = _glazing(shape, belt_y, top_y)
    panel = (
        []
        if shape.panel_share <= 0.0
        else [ring(belt_y, g.belt_half_w, g.front_z, g.rear_z, g.cut)]
    )
    rings = [
        *panel,
        ring(g.panel_y, g.belt_half_w, g.front_z, g.rear_z, g.cut),
        ring(
            g.glass_y,
            g.glass_half_w,
            g.front_z + g.front_run,
            g.rear_z - g.rear_run,
            g.cut,
        ),
        ring(
            top_y,
            g.belt_half_w - g.inset,
            g.roof_end_z(rear=False),
            g.roof_end_z(rear=True),
            g.cut,
        ),
    ]
    bands = [shape.paint] * len(panel) + [GLASS, roof]
    return loft(rings, bands, bottom=floor, top=roof if cap else None, name=name)


def _pillars(shape: Shape, belt_y: float, top_y: float, *, name: str) -> list[MeshData]:
    """The pillars between the side windows, laid on the leaning glass."""
    if shape.window_bays < 2:
        return []
    g = _glazing(shape, belt_y, top_y)
    z0, z1 = g.glass_top_z()
    half = 0.045
    colour = shape.pillar or shape.roof
    parts: list[MeshData] = []
    for side in (-1.0, 1.0):
        x_low = side * (g.side_x(g.panel_y) + 0.004)
        x_high = side * (g.side_x(g.glass_y) + 0.004)
        for k in range(1, shape.window_bays):
            z = z0 + (z1 - z0) * k / shape.window_bays
            parts.append(
                polygon_facing(
                    [
                        (x_low, g.panel_y, z - half),
                        (x_low, g.panel_y, z + half),
                        (x_high, g.glass_y, z + half),
                        (x_high, g.glass_y, z - half),
                    ],
                    colour,
                    (side, 0.0, 0.0),
                    name=f"{name}_pillar_{k}_{'l' if side < 0 else 'r'}",
                )
            )
    return parts


def _board(
    g: _Glazing, *, rear: bool, y0: float, y1: float, half_w: float, name: str
) -> list[MeshData]:
    """A destination blind on the end glass: a dark housing, its amber line."""
    out = 1.0 if rear else -1.0

    def pane(lo: float, hi: float, hw: float, proud: float, colour: Colour, tag: str) -> MeshData:
        corners = [
            (x, y, g.end_z(y, rear=rear) + out * proud)
            for x, y in ((-hw, lo), (hw, lo), (hw, hi), (-hw, hi))
        ]
        return polygon_facing(corners, colour, (0.0, 0.0, out), name=f"{name}_{tag}")

    inner = (y1 - y0) * 0.22
    return [
        pane(y0, y1, half_w, 0.006, DARK, "housing"),
        pane(y0 + inner, y1 - inner, half_w - inner, 0.010, AMBER, "line"),
    ]


def _roof_box(
    shape: Shape, top_y: float, z_face: float, *, rear: bool, half: tuple[float, float, float]
) -> list[MeshData]:
    """A destination box standing on the roof's end, its face lettered amber."""
    out = 1.0 if rear else -1.0
    hx, hy, hz = half
    centre_z = z_face - out * hz
    face_z = z_face + out * 0.004
    tag = "rear" if rear else "front"
    lo, hi = top_y + hy * 0.6, top_y + hy * 1.4
    line = [
        (-hx * 0.8, lo, face_z),
        (hx * 0.8, lo, face_z),
        (hx * 0.8, hi, face_z),
        (-hx * 0.8, hi, face_z),
    ]
    return [
        box_at((0.0, top_y + hy, centre_z), half, DARK, name=f"roof_box_{tag}"),
        polygon_facing(line, AMBER, (0.0, 0.0, out), name=f"roof_box_{tag}_line"),
    ]


def _ends(shape: Shape) -> list[MeshData]:
    """Bumpers, lamps, indicators, the grille and the plates.

    The bumpers are the footprint's ends; the body stands `bumper_m` behind
    them, and every lens on its end face stands in that margin.
    """
    hw = shape.body_half_width_m
    lamp_y = shape.sill_y_m + (shape.belt_y_m - shape.sill_y_m) * 0.65
    bumper_top = shape.sill_y_m + shape.bumper_height_m
    parts: list[MeshData] = []
    for rear in (False, True):
        out = 1.0 if rear else -1.0
        end = shape.rear_z_m if rear else shape.front_z_m
        face = shape.body_rear_z_m if rear else shape.body_front_z_m
        tag = "rear" if rear else "front"
        # The bumper reaches the footprint's end bar the plate's own depth.
        z_bumper = sorted((end - out * FIXTURE_PROUD_M, face - out * 0.02))
        parts.append(
            box(
                (-(hw - shape.corner_cut_m * 0.5), shape.sill_y_m, z_bumper[0]),
                (hw - shape.corner_cut_m * 0.5, bumper_top, z_bumper[1]),
                shape.bumper,
                name=f"bumper_{tag}",
            )
        )
        if shape.plates:
            z_plate = sorted((end, end - out * (FIXTURE_PROUD_M + 0.01)))
            y_plate = (shape.sill_y_m + bumper_top) / 2.0
            parts.append(
                box(
                    (-0.26, y_plate - 0.06, z_plate[0]),
                    (0.26, y_plate + 0.06, z_plate[1]),
                    AMBER if rear else LAMP,
                    name=f"plate_{tag}",
                )
            )
        z_lens = sorted((face - 0.01 * out, face + FIXTURE_PROUD_M * out))
        for side, side_tag in ((-1.0, "l"), (1.0, "r")):
            x = side * (hw - 0.22)
            lens_half = (0.08, 0.05) if rear else (0.11, 0.05)
            if rear or shape.head_lamps == 2:
                parts.append(
                    box(
                        (x - lens_half[0], lamp_y - lens_half[1], z_lens[0]),
                        (x + lens_half[0], lamp_y + lens_half[1], z_lens[1]),
                        RED if rear else LAMP,
                        name=f"{'taillamp' if rear else 'headlamp'}_{side_tag}",
                    )
                )
            # Not `indicator_l` / `indicator_r`: those are the taxi's switched
            # circuits, and a parked car's indicators are wired to nothing.
            parts.append(
                box(
                    (x - 0.06, lamp_y - 0.105, z_lens[0]),
                    (x + 0.06, lamp_y - 0.06, z_lens[1]),
                    AMBER,
                    name=f"indicator_{tag}_{side_tag}",
                )
            )
        if shape.head_lamps == 1 and not rear:
            parts.append(
                box(
                    (-0.09, lamp_y - 0.09, z_lens[0]),
                    (0.09, lamp_y + 0.09, z_lens[1]),
                    LAMP,
                    name="headlamp_c",
                )
            )
        if shape.grille is not None and not rear:
            grille_hw = hw - 0.37
            parts.append(
                box(
                    (-grille_hw, lamp_y - 0.055, z_lens[0]),
                    (grille_hw, lamp_y + 0.055, z_lens[1]),
                    shape.grille,
                    name="grille",
                )
            )
    return parts


def _side_fixtures(shape: Shape) -> list[MeshData]:
    """Folded mirrors and door handles, in the flanks' skin."""
    if not (shape.mirrors or shape.handles):
        return []
    g = _glazing(shape, shape.belt_y_m, shape.roof_y_m)
    hw = shape.half_width_m
    parts: list[MeshData] = []
    for side, tag in ((-1.0, "l"), (1.0, "r")):
        if shape.mirrors:
            # Folded back along the glass at the windscreen's foot.
            z = g.front_z + g.front_run * 0.6 + 0.12
            x = sorted((side * (hw - 0.065), side * hw))
            parts.append(
                box(
                    (x[0], g.belt_y + 0.05, z - 0.11),
                    (x[1], g.belt_y + 0.17, z + 0.11),
                    DARK,
                    name=f"mirror_{tag}",
                )
            )
        if shape.handles:
            z0, z1 = g.glass_top_z()
            doors = [z0 + (z1 - z0) * k / shape.window_bays for k in range(1, shape.window_bays)]
            x = sorted((side * (shape.body_half_width_m - 0.004), side * (hw - 0.002)))
            for k, z in enumerate([*doors, z1]):
                parts.append(
                    box(
                        (x[0], shape.belt_y_m - 0.12, z - 0.23),
                        (x[1], shape.belt_y_m - 0.08, z - 0.08),
                        DARK,
                        name=f"handle_{k}_{tag}",
                    )
                )
    return parts


def _seams(shape: Shape, zs: Sequence[float], y0: float, y1: float) -> list[MeshData]:
    """Dark lines on both flanks at `zs` — a sliding door's, a luggage bay's."""
    parts: list[MeshData] = []
    x = shape.body_half_width_m + 0.004
    for side in (-1.0, 1.0):
        for i, z in enumerate(zs):
            parts.append(
                polygon_facing(
                    [
                        (side * x, y0, z - 0.012),
                        (side * x, y0, z + 0.012),
                        (side * x, y1, z + 0.012),
                        (side * x, y1, z - 0.012),
                    ],
                    DARK,
                    (side, 0.0, 0.0),
                    name=f"seam_{i}_{'l' if side < 0 else 'r'}",
                )
            )
    return parts


def _wheels(shape: Shape) -> list[MeshData]:
    """The wheels, baked in. A flank wheel has its outer face only: the inner
    one looks at its well's wall (`_wells`), so a car is 144 triangles lighter."""

    def wheel(faces: Sequence[float]) -> MeshData:
        return _wheel(
            shape.wheel_radius_m,
            shape.wheel_width_m,
            WHEEL_SEGMENTS,
            rim_fraction=0.5,
            faces=faces,
            name="wheel",
        )

    outer = {-1.0: wheel((-1.0,)), 1.0: wheel((1.0,)), 0.0: wheel((1.0, -1.0))}
    parts: list[MeshData] = []
    xs = (
        (0.0,)
        if shape.single_track
        else (
            -(shape.half_width_m - shape.wheel_width_m / 2.0 - 0.02),
            shape.half_width_m - shape.wheel_width_m / 2.0 - 0.02,
        )
    )
    for index, axle in enumerate(shape.axles_m):
        z = shape.front_z_m + axle
        for x in xs:
            parts.append(
                replace(
                    outer[float(np.sign(x))],
                    name=f"wheel_{index}_{'l' if x < 0 else 'r' if x > 0 else 'c'}",
                ).translated((x, shape.wheel_radius_m, z))
            )
    return parts


def _underframe(shape: Shape) -> MeshData:
    """The trucks under a whole skirt, as one dark block from the ground to
    the sill: in shadow from any street, what reads is the gap, not wheels."""
    axles = _axle_zs(shape)
    # A truck's half-length either side of its axle.
    reach = shape.wheel_radius_m * 2.5
    hw = shape.body_half_width_m - 0.2
    return box(
        (-hw, 0.0, axles[0] - reach), (hw, shape.sill_y_m, axles[-1] + reach), DARK, name="trucks"
    )


# --------------------------------------------------------------------------
# What makes each kind itself (`P3-75`), read off photographs of the real ones
# --------------------------------------------------------------------------


def _taxi(shape: Shape) -> list[MeshData]:
    """The roof's TAXI sign over the front seats, and the 4 SEATS badge."""
    hw = shape.body_half_width_m
    face = shape.body_front_z_m
    sign_z = _glazing(shape, shape.belt_y_m, shape.roof_y_m).roof_end_z(rear=False) + 0.15
    return [
        # Named `sign_…`, so `_marked` takes it for a lens. Not the player's
        # `sign` circuit: nothing lights a parked taxi's.
        box_at((0.0, shape.roof_y_m + 0.08, sign_z), (0.24, 0.08, 0.09), LAMP, name="sign_roof"),
        box(
            (hw - 0.34, shape.sill_y_m + shape.bumper_height_m + 0.01, face - FIXTURE_PROUD_M),
            (hw - 0.18, shape.sill_y_m + shape.bumper_height_m + 0.09, face + 0.01),
            BADGE_GREEN,
            name="badge_front",
        ),
    ]


def _minibus(shape: Shape) -> list[MeshData]:
    """The route board standing on the roof's front edge."""
    g = _glazing(shape, shape.belt_y_m, shape.roof_y_m)
    roof_front = g.roof_end_z(rear=False)
    return _roof_box(shape, shape.roof_y_m, roof_front + 0.02, rear=False, half=(0.6, 0.14, 0.18))


def _bus(shape: Shape) -> list[MeshData]:
    """The blind over the lower windscreen, between the decks."""
    g = _glazing(shape, shape.belt_y_m, shape.deck_y_m)
    return _board(
        g, rear=False, y0=g.glass_y - 0.34, y1=g.glass_y - 0.04, half_w=0.95, name="blind"
    )


def _tram(shape: Shape) -> list[MeshData]:
    """A route board on the roof at each end, and the trolley pole lying back."""
    g = _glazing(shape, shape.deck_y_m, shape.roof_y_m)
    ends = (g.roof_end_z(rear=False), g.roof_end_z(rear=True))
    pole_len = shape.length_m * 0.36
    return [
        *_roof_box(shape, shape.roof_y_m, ends[0] + 0.02, rear=False, half=(0.55, 0.12, 0.1)),
        *_roof_box(shape, shape.roof_y_m, ends[1] - 0.02, rear=True, half=(0.55, 0.12, 0.1)),
        box_at((0.0, shape.roof_y_m + 0.06, 0.0), (0.16, 0.06, 0.22), DARK, name="pole_base"),
        box_at(
            (0.0, shape.roof_y_m + 0.15, pole_len / 2.0),
            (0.025, 0.025, pole_len / 2.0),
            DARK,
            name="pole",
        ),
    ]


def _van(shape: Shape) -> list[MeshData]:
    """The sliding door's seam and a roof rack."""
    g = _glazing(shape, shape.belt_y_m, shape.roof_y_m)
    rail_x = shape.body_half_width_m - g.inset - 0.12
    z0 = g.front_z + g.front_run + 0.5
    z1 = g.rear_z - g.rear_run - 0.2
    rack: list[MeshData] = [
        box_at(
            (side * rail_x, shape.roof_y_m + 0.03, (z0 + z1) / 2.0),
            (0.02, 0.03, (z1 - z0) / 2.0),
            SILVER,
            name=f"rail_{'l' if side < 0 else 'r'}",
        )
        for side in (-1.0, 1.0)
    ]
    rack.extend(
        box_at((0.0, shape.roof_y_m + 0.07, z), (rail_x, 0.012, 0.02), SILVER, name=f"bar_{i}")
        for i, z in enumerate(np.linspace(z0 + 0.1, z1 - 0.1, 3))
    )
    door = shape.front_z_m + 1.55
    return [*rack, *_seams(shape, (door, door + 0.95), shape.sill_y_m + 0.04, shape.belt_y_m)]


def _coach(shape: Shape) -> list[MeshData]:
    """The luggage bays' doors between the axles."""
    axles = _axle_zs(shape)
    front, rear = axles[0], axles[-1]
    reach = shape.arch_radius_m + 0.15
    zs = np.linspace(front + reach, rear - reach, 4)
    return _seams(shape, [float(z) for z in zs], shape.sill_y_m + 0.08, shape.waist_y_m)


DETAILS: dict[str, Callable[[Shape], list[MeshData]]] = {
    "taxi": _taxi,
    "minibus": _minibus,
    "bus": _bus,
    "tram": _tram,
    "van": _van,
    "coach": _coach,
}


def vehicle(shape: Shape) -> MeshData:
    """One kind as one marked mesh, ready for `material_parts`."""
    parts: list[MeshData] = [_lower(shape)]
    if shape.arches:
        parts.extend(_wells(shape))
    if shape.upper_deck:
        deck = shape.deck_y_m
        parts.append(
            _glasshouse(shape, shape.belt_y_m, deck, shape.paint, name="lower_deck", cap=True)
        )
        parts.append(
            _glasshouse(
                shape,
                deck,
                shape.roof_y_m,
                shape.roof,
                name="upper_deck",
                cap=True,
                floor=shape.paint,
            )
        )
        parts.extend(_pillars(shape, shape.belt_y_m, deck, name="lower_deck"))
        parts.extend(_pillars(shape, deck, shape.roof_y_m, name="upper_deck"))
    else:
        parts.append(
            _glasshouse(
                shape, shape.belt_y_m, shape.roof_y_m, shape.roof, name="glasshouse", cap=True
            )
        )
        parts.extend(_pillars(shape, shape.belt_y_m, shape.roof_y_m, name="glasshouse"))
    if shape.band is not None:
        parts.append(
            box_at(
                (0.0, shape.belt_y_m, 0.0),
                (
                    # In the skin's margin, proud of the flank: drawn inside
                    # the body, as it first was, it never showed.
                    shape.half_width_m - 0.002,
                    0.06,
                    (shape.body_rear_z_m - shape.body_front_z_m) / 2.0 - shape.corner_cut_m,
                ),
                shape.band,
                name="band",
            )
        )
    parts.extend(_ends(shape))
    parts.extend(_side_fixtures(shape))
    parts.extend(DETAILS.get(shape.kind, lambda _: [])(shape))
    parts.extend(_wheels(shape) if shape.arches else [_underframe(shape)])
    body = merge([_marked(part) for part in parts], name=shape.kind)
    return replace(body, material=BODY_MATERIAL)


def motorcycle(shape: Shape) -> MeshData:
    """A delivery bike: two wheels in line under a fairing, a tank, a saddle
    and the top box Hong Kong's couriers ride with — the one kind that is not
    a lofted body."""
    front, rear = shape.front_z_m, shape.rear_z_m
    r = shape.wheel_radius_m
    z_front, z_rear = front + shape.axles_m[0], front + shape.axles_m[1]
    fairing_low = r + 0.28
    fairing_high = r + 0.68
    parts: list[MeshData] = [
        # The frame, from the headstock down to the rear axle.
        box_at((0.0, r + 0.18, 0.0), (0.07, 0.12, shape.length_m * 0.3), DARK, name="frame"),
        box_at((0.0, r + 0.02, 0.05), (0.13, 0.14, 0.22), STEEL, name="engine"),
        # Tank and the side cover under the saddle, in the livery.
        box_at((0.0, r + 0.42, front + 0.75), (0.17, 0.12, 0.28), shape.paint, name="tank"),
        box_at((0.0, r + 0.3, z_rear - 0.5), (0.14, 0.1, 0.24), shape.paint, name="side_cover"),
        # Saddle.
        box_at((0.0, r + 0.44, rear - 0.6), (0.16, 0.05, 0.34), DARK, name="saddle"),
        # The fairing round the headstock, narrowing to the screen.
        hexahedron(
            [
                (-0.18, fairing_low, z_front + 0.08),
                (0.18, fairing_low, z_front + 0.08),
                (0.18, fairing_low, z_front + 0.42),
                (-0.18, fairing_low, z_front + 0.42),
            ],
            [
                (-0.12, fairing_high, z_front + 0.2),
                (0.12, fairing_high, z_front + 0.2),
                (0.12, fairing_high, z_front + 0.4),
                (-0.12, fairing_high, z_front + 0.4),
            ],
            shape.paint,
            name="fairing",
        ),
        box_at((0.0, fairing_high + 0.1, z_front + 0.27), (0.1, 0.1, 0.01), GLASS, name="screen"),
        # Handlebar, across the headstock.
        box_at((0.0, r + 0.62, front + 0.42), (0.4, 0.02, 0.02), SILVER, name="bar"),
        box_at((0.0, r + 0.3, front + 0.4), (0.03, 0.3, 0.03), SILVER, name="fork"),
        box_at((0.0, 2.0 * r + 0.03, z_front), (0.06, 0.02, 0.2), shape.paint, name="fender"),
        # Named with the taxi's lamp prefixes, so `_marked` reads them as lenses.
        box_at((0.0, r + 0.47, z_front + 0.1), (0.06, 0.04, 0.03), LAMP, name="headlamp_c"),
        box_at((0.0, r + 0.42, rear - 0.12), (0.05, 0.03, 0.02), RED, name="taillamp_c"),
        # The top box on its rack behind the saddle, and the plate under it.
        box_at((0.0, r + 0.66, rear - 0.3), (0.19, 0.15, 0.2), DARK, name="top_box"),
        box_at((0.0, r + 0.3, rear - 0.1), (0.1, 0.06, 0.006), AMBER, name="plate_rear"),
        # Exhaust, low on the right.
        box_at((0.14, r - 0.05, rear - 0.55), (0.04, 0.04, 0.3), STEEL, name="exhaust"),
    ]
    parts.extend(_wheels(shape))
    body = merge([_marked(part) for part in parts], name=shape.kind)
    return replace(body, material=BODY_MATERIAL)


def _car(kind: str, paint: Colour, roof: Colour) -> Shape:
    """A saloon: three boxes, a boot behind the cabin."""
    return Shape(
        kind=kind,
        length_m=4.5,
        width_m=1.8,
        paint=paint,
        roof=roof,
        sill_y_m=0.22,
        belt_y_m=0.78,
        roof_y_m=1.42,
        cabin_front_m=1.25,
        cabin_rear_m=3.65,
        windscreen_rake_deg=32.0,
        backlight_rake_deg=30.0,
        corner_cut_m=0.16,
        roof_inset_m=0.14,
        wheel_radius_m=0.32,
        wheel_width_m=0.2,
        axles_m=(0.85, 3.55),
        handles=True,
    )


SHAPES: tuple[Shape, ...] = (
    _car("car_a", WHITE, WHITE),
    # A people-carrier on the saloon's footprint — an Alphard, the private
    # car a Hong Kong street carries most after the saloon: tall, the cabin
    # running to the tail, three windows a side and a chrome face.
    Shape(
        kind="car_b",
        length_m=4.5,
        width_m=1.8,
        paint=NAVY,
        roof=NAVY,
        sill_y_m=0.22,
        belt_y_m=0.92,
        roof_y_m=1.86,
        cabin_front_m=0.95,
        cabin_rear_m=4.38,
        windscreen_rake_deg=40.0,
        backlight_rake_deg=8.0,
        corner_cut_m=0.18,
        roof_inset_m=0.1,
        wheel_radius_m=0.33,
        wheel_width_m=0.21,
        axles_m=(0.85, 3.65),
        window_bays=3,
        grille=SILVER,
        handles=True,
    ),
    # The red urban taxi, parked: a Crown Comfort's footprint (`Q153`), the
    # silver above the belt and the chrome grille of the photographs.
    Shape(
        kind="taxi",
        length_m=4.7,
        width_m=1.7,
        paint=RED,
        roof=SILVER,
        sill_y_m=0.22,
        belt_y_m=0.8,
        roof_y_m=1.46,
        cabin_front_m=1.45,
        cabin_rear_m=3.9,
        windscreen_rake_deg=35.0,
        backlight_rake_deg=30.0,
        corner_cut_m=0.16,
        roof_inset_m=0.13,
        wheel_radius_m=0.31,
        wheel_width_m=0.2,
        axles_m=(0.95, 3.75),
        grille=SILVER,
        handles=True,
    ),
    # The green minibus: a Toyota Coaster, cream with the green roof.
    Shape(
        kind="minibus",
        length_m=7.0,
        width_m=2.1,
        paint=CREAM,
        roof=MINIBUS_GREEN,
        sill_y_m=0.35,
        belt_y_m=1.25,
        roof_y_m=2.6,
        cabin_front_m=0.35,
        cabin_rear_m=6.9,
        windscreen_rake_deg=14.0,
        backlight_rake_deg=6.0,
        corner_cut_m=0.14,
        roof_inset_m=0.12,
        wheel_radius_m=0.38,
        wheel_width_m=0.22,
        axles_m=(1.6, 5.3),
        pillar=CREAM,
        window_bays=5,
        mirrors=False,
    ),
    # The double-decker, in Citybus yellow over its blue skirt.
    Shape(
        kind="bus",
        length_m=12.0,
        width_m=2.5,
        paint=CITYBUS_YELLOW,
        roof=CITYBUS_YELLOW,
        sill_y_m=0.35,
        belt_y_m=1.3,
        roof_y_m=4.4,
        cabin_front_m=0.2,
        cabin_rear_m=11.9,
        windscreen_rake_deg=6.0,
        backlight_rake_deg=3.0,
        corner_cut_m=0.16,
        roof_inset_m=0.1,
        wheel_radius_m=0.5,
        wheel_width_m=0.3,
        axles_m=(2.6, 8.2, 9.8),
        upper_deck=True,
        skirt=CITYBUS_BLUE,
        window_bays=6,
        mirrors=False,
    ),
    # A tour coach: single deck, high floor, white.
    Shape(
        kind="coach",
        length_m=12.0,
        width_m=2.5,
        paint=WHITE,
        roof=WHITE,
        sill_y_m=0.4,
        belt_y_m=1.7,
        roof_y_m=3.6,
        cabin_front_m=0.3,
        cabin_rear_m=11.6,
        windscreen_rake_deg=10.0,
        backlight_rake_deg=4.0,
        corner_cut_m=0.18,
        roof_inset_m=0.14,
        wheel_radius_m=0.5,
        wheel_width_m=0.3,
        axles_m=(2.6, 8.6),
        band=NAVY,
        window_bays=7,
        mirrors=False,
    ),
    # The Hiace: a van's box, tall, short-nosed.
    Shape(
        kind="van",
        length_m=4.7,
        width_m=1.8,
        paint=WHITE,
        roof=WHITE,
        sill_y_m=0.25,
        belt_y_m=1.0,
        roof_y_m=1.95,
        cabin_front_m=0.45,
        cabin_rear_m=4.6,
        windscreen_rake_deg=22.0,
        backlight_rake_deg=4.0,
        corner_cut_m=0.12,
        roof_inset_m=0.1,
        wheel_radius_m=0.32,
        wheel_width_m=0.2,
        axles_m=(0.95, 3.55),
        window_bays=3,
    ),
    # The tram: a tall, narrow double-decker with a cream band at the belt,
    # boxy — square ends, flat sides, the roof barely drawn in — and its
    # skirt down to the rails, the trucks hidden under it (the user's call);
    # each deck a band of nine windows over a tall panel, one lamp on the
    # dash — checked against Commons photographs of the fleet.
    Shape(
        kind="tram",
        length_m=8.89,
        width_m=2.0,
        paint=TRAM_GREEN,
        roof=TRAM_GREEN,
        sill_y_m=0.12,
        belt_y_m=1.3,
        roof_y_m=4.7,
        cabin_front_m=0.25,
        cabin_rear_m=8.64,
        windscreen_rake_deg=1.0,
        backlight_rake_deg=1.0,
        corner_cut_m=0.06,
        roof_inset_m=0.04,
        wheel_radius_m=0.3,
        wheel_width_m=0.12,
        axles_m=(1.75, 7.14),
        upper_deck=True,
        band=TRAM_CREAM,
        window_bays=9,
        bumper_m=0.04,
        grille=None,
        plates=False,
        arches=False,
        panel_share=0.35,
        glass_share=0.52,
        head_lamps=1,
        mirrors=False,
    ),
    Shape(
        kind="motorcycle",
        length_m=2.1,
        width_m=0.8,
        paint=RED,
        roof=DARK,
        sill_y_m=0.0,
        belt_y_m=0.0,
        roof_y_m=0.0,
        cabin_front_m=0.0,
        cabin_rear_m=0.0,
        windscreen_rake_deg=0.0,
        backlight_rake_deg=0.0,
        corner_cut_m=0.0,
        roof_inset_m=0.0,
        wheel_radius_m=0.3,
        wheel_width_m=0.12,
        axles_m=(0.3, 1.8),
        single_track=True,
    ),
)


def build_roster(shapes: Sequence[Shape] = SHAPES) -> list[MeshData]:
    """Every kind as one marked mesh, in roster order."""
    return [motorcycle(shape) if shape.single_track else vehicle(shape) for shape in shapes]


def write_roster(
    out_dir: Path, shapes: Sequence[Shape] = SHAPES
) -> tuple[Path, int, list[MeshData]]:
    """The library, one node per kind; returns where it went and its bytes."""
    meshes = build_roster(shapes)
    path = out_dir / LIBRARY_FILE
    groups: list[MeshGroup] = [material_parts(mesh) for mesh in meshes]
    return path, write_glb(path, groups), meshes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output directory")
    parser.add_argument("--report", action="store_true", help="print the geometry it produced")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    path, written, meshes = write_roster(args.out_dir)
    LOG.info("wrote %s (%d bytes, %d kinds)", path, written, len(meshes))
    if args.report:
        for mesh in meshes:
            low, high = mesh.aabb()
            colours = len({tuple(int(v) for v in row[:3]) for row in mesh.colours})
            LOG.info(
                "  %-10s %5d triangles  %.2f x %.2f x %.2f m  %d colours",
                mesh.name,
                mesh.triangle_count,
                high[0] - low[0],
                high[1] - low[1],
                high[2] - low[2],
                colours,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
