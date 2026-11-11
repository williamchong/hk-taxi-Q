"""Generate the parked roster's library (`P3-72`, `Q161`).

    python tools/make_parked.py
    python tools/make_parked.py --out-dir /tmp/vehicles --report

One `.glb`, `parked.glb`, holding one node per roster kind — `car_a`, `car_b`,
`taxi` and its two other licences, `minibus`, `bus`, `coach`, `van`, `tram`,
`lorry`, `motorcycle` — which
`pipeline/parked.py` stands by a placements document, the shape every prop
library takes (`P5-2`). Each node is a MeshGroup of `vehicle_*` material parts
(`make_vehicle.material_parts`), so `generated_scene_import.gd` merges it into
one `vehicle_body` surface on `vehicle_body.tres`: the glass, the lamps and the
paint shade as the player's taxi does, and every lens stays dark because no
`vehicle_lamps.gd` drives a parked car.

**Real footprints, but the taxi's.** A parked car sits beside the player's
Crown Comfort, and a toy beside it reads as a toy: the lofted kinds' lengths
and widths are the real vehicles'. The taxis are the exception since `P3-85`
— they ARE the player's die-cast body (`Taxi`, `Q190`), so the taxi in the
next lane is the car being driven. Every footprint here is the one
`hong_kong.yaml`'s `parked.vehicles:` places by, and
`tests/test_make_parked.py` pins the two tables to each other.

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
    BODY_MATERIAL,
    DARK,
    GLASS,
    GLINT,
    GLINT_FOOT,
    GLINT_LEAN,
    KERB_SIDE,
    LAMP,
    MARKER_CABIN,
    MARKER_CABIN_DIM,
    MARKER_GLASS,
    MARKER_LIVERY,
    MARKER_PAINT,
    RED,
    SILVER,
    Chassis,
    Proportions,
    _marked,
    _rake_run_m,
    _wheel,
    door_hinge,
    material_parts,
    taxi_door,
    taxi_parts,
)
from pipeline.gltf import MeshData, MeshGroup, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import (  # noqa: E402
    Colour,
    Point,
    box,
    box_at,
    flank_edges,
    hexahedron,
    loft,
    polygon_facing,
    ring,
)
from vehicle_ink import inked  # noqa: E402

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
# The licence colours of the two non-urban taxis (`Q183`), read off
# photographs: the New Territories' leaf green, Lantau's sky blue.
NT_TAXI_GREEN = (46, 150, 66)
LANTAU_TAXI_BLUE = (78, 160, 218)
# Citybus's lower skirt, under the yellow.
CITYBUS_BLUE = (30, 70, 150)
TRAM_GREEN = (22, 108, 60)
# A tram's roof, the model's near-black with the body's green in it.
TRAM_ROOF = (34, 46, 42)
STEEL = (120, 122, 126)

# Fewer segments than the player's 18: a roster wheel is looked at from a car
# going past, and four of them a vehicle over nine kinds is where the triangles
# go. Twelve since the arches opened the wheel to view (`P3-75`); the roster's
# taxis wear the player's hubcap on it.
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
# A head lamp's chrome bezel: how far it shows round the lens and the
# indicator under it, and how far it stands off the face (the lens stands
# `FIXTURE_PROUD_M`, so the bezel is behind it).
BEZEL_M = 0.02
BEZEL_PROUD_M = 0.004
# How far a line or a strip drawn on a flank stands off it, inside `SKIN_M`.
FLANK_PROUD_M = 0.004
# The bar between a window and the top light over it.
TOP_LIGHT_BAR_M = 0.05
# How much of a corner chamfer a wrap-round pane covers, as shares across it.
CORNER_WRAP = (0.15, 0.85)
# How far a run of windows' surround shows round it.
SURROUND_M = 0.04
# Proud of the glass it lies on (twice `FLANK_PROUD_M` over a surround), and
# still inside `SKIN_M`.
GLINT_PROUD_M = 0.010
# A tram's side lamp: its half-size, and how far a rear one stands inboard of
# the tail lens, on the row of the indicator under it.
SIDE_LAMP_HALF_M = (0.06, 0.05)
SIDE_LAMP_INBOARD_M = 0.2
# Space left above an arch's crown before the waist ring.
WAIST_OVER_ARCH_M = 0.06


@dataclass(frozen=True)
class Glass:
    """A run of side windows on a flat-sided body (`Shape.slab_sided`)."""

    # The glass's foot and head.
    y0_m: float
    y1_m: float
    # The run along the body, from the nose, and the windows in it.
    start_m: float
    end_m: float
    bays: int
    # Which flanks carry it: both, or one where a door or a staircase stands
    # on the other.
    sides: tuple[float, ...] = (-1.0, 1.0)
    pillar_m: float = 0.07
    # A top light this tall split off each window's head by a bar (a tram's).
    top_light_m: float = 0.0
    # A surround in this colour behind the whole run, so thin pillars read as
    # one dark band of glass (a modern bus's bonded glazing); None leaves the
    # body's own paint between the windows.
    surround: Colour | None = None

    def __post_init__(self) -> None:
        if self.bays < 1 or self.end_m - self.start_m <= self.pillar_m * (self.bays - 1):
            raise ValueError(f"a glass run of {self.bays} bays leaves its windows no width")
        light = self.top_light_m + TOP_LIGHT_BAR_M if self.top_light_m else 0.0
        if not 0.0 <= light < self.y1_m - self.y0_m:
            raise ValueError("a glass run's top light leaves no window under it")


@dataclass(frozen=True)
class EndPane:
    """A window, or a dark panel, on a flat-sided body's end face."""

    y0_m: float
    y1_m: float
    rear: bool = False
    # How far inside the end face's own edges it stands.
    inset_m: float = 0.08
    # Carried round onto the two corner chamfers: a wrap-round screen.
    corners: bool = False
    colour: Colour = GLASS

    def __post_init__(self) -> None:
        if not self.y0_m < self.y1_m:
            raise ValueError("an end pane's head is under its foot")


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
    # Where the glasshouse starts and ends along the body, from the nose
    # (unread on a flat-sided body, whose glass is `side_glass`).
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
    # Wheels along the centreline (a motorcycle), not at the flanks.
    single_track: bool = False
    # A bar at the belt in a second colour (a coach's stripe).
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
    # glass, and the glass. A lorry's cab has its doors under its windows.
    panel_share: float = 0.0
    glass_share: float = 0.72
    # One lamp centred on the dash (a tram's), or a pair.
    head_lamps: int = 2
    # The authored colour a parked vehicle may wear another of (`Q167`): its
    # paint-marked vertices in this colour take `MARKER_LIVERY`, and
    # `parked.tres`'s `liveries` says what each one wears. None where the
    # colour IS the vehicle — the red taxi, Citybus's yellow, the green tram.
    livery: Colour | None = None
    # The small lamps a tram runs with lit, on the side-lamp circuit: white
    # beside the head lamp, red inboard of each tail lens.
    side_lamps: bool = False
    # A saloon lit behind every window at night: the marker its glass takes.
    cabin: float | None = None
    # The roof of a box body standing behind the cab (`_lorry`).
    cargo_top_m: float | None = None
    # --- A flat-sided body (`P3-85`): one wall from the belt to a crowned
    # roof, its windows applied to it run by run — a double-decker's and a
    # tram's, whose sides do not step in at each deck as stacked glasshouses do.
    slab_sided: bool = False
    # How far under the roof the wall turns in to it.
    crown_m: float = 0.0
    side_glass: tuple[Glass, ...] = ()
    end_panes: tuple[EndPane, ...] = ()
    # A door's head on a flat side.
    door_head_m: float | None = None
    # The rear share of each flank's glass panelled over in the body's paint:
    # a panel van's blind quarter, a minibus's rear corner.
    blind_rear_share: float = 0.0
    # A pale streak across each side window, the sky caught in the glass (the
    # user's pick of five treatments, 2026-11-11): its colour, or None.
    glint: Colour | None = None
    # How far inboard of the flank the corner lamps sit, and how far the
    # bumper stops short of it; a body with deep corner cuts needs more.
    lamp_inset_m: float = 0.22
    bumper_inset_m: float | None = None
    # --- The die-cast pass (`P3-85`): what a 1:64 model of the kind carries
    # that the loft alone does not. Each is off unless the kind sets it.
    # How far the bonnet falls from the scuttle to the nose, and the boot from
    # the backlight's foot to the tail: the three-box profile a flat deck at
    # the belt cannot make.
    nose_drop_m: float = 0.0
    tail_drop_m: float = 0.0
    # Slots round each hubcap (`make_vehicle._wheel`); 0 is the plain disc.
    hub_slots: int = 0
    # A chrome bezel behind each head lamp.
    bezels: bool = False
    # A shut line at each door's edge, where `handles` puts the doors.
    shut_lines: bool = False
    # A strip along each flank between the arches, in this colour.
    rub_strip: Colour | None = None
    # Wiper arms lying at the windscreen's foot.
    wipers: bool = False
    # Passenger doors on the kerb side, each (start, end) from the nose: a
    # dark frame from the step up, two glazed leaves, posts across the glass.
    doors_m: tuple[tuple[float, float], ...] = ()
    # Glazed leaves in those doors; off, the doorway stands open and dark (a
    # tram's, behind its turnstile).
    door_glass: bool = True
    # A bar across each deck's side glass: (how far up the glass its centre
    # sits, its height in metres). A minibus's slider rails.
    window_bar: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.panel_share + self.glass_share >= 1.0:
            raise ValueError(f"{self.kind}: the panel and the glass leave no roof rail")
        if self.head_lamps not in (1, 2):
            raise ValueError(f"{self.kind}: head_lamps is 1 or 2, not {self.head_lamps}")
        if self.shut_lines and not self.handles:
            raise ValueError(f"{self.kind}: shut lines stand at the doors `handles` places")
        if self.slab_sided and not 0.0 < self.crown_m < self.roof_y_m - self.belt_y_m:
            raise ValueError(f"{self.kind}: a flat-sided body needs a crown under its roof")
        if self.doors_m and self.slab_sided and self.door_head_m is None:
            raise ValueError(f"{self.kind}: a door on a flat side needs `door_head_m`")
        flat_only = self.side_glass or self.end_panes or self.glint or self.crown_m
        if flat_only and not self.slab_sided:
            raise ValueError(f"{self.kind}: applied glass and a crown are a flat-sided body's")
        if self.slab_sided and (self.blind_rear_share or self.window_bar):
            raise ValueError(f"{self.kind}: a blind quarter and a window bar lie on lofted glass")

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
    falling = bool(shape.nose_drop_m or shape.tail_drop_m)
    if falling:
        if not shape.arches:
            raise ValueError(f"{shape.kind}: a falling deck needs the flanks its arches draw")
        rings[1] = tuple((x, waist_y_at(shape, z), z) for x, _, z in rings[1])
    skirt = loft(
        rings[:2],
        [shape.skirt_colour],
        bottom=DARK,
        top=None,
        skip_edges=flank_edges(len(rings[0])) if shape.arches else (),
        name="skirt",
    )
    if falling:
        body = _falling_deck(shape, rings[1], rings[2])
    else:
        # A flat-sided body's wall stands on this ring: its cap would be sealed in.
        cap = None if shape.slab_sided else shape.paint
        body = loft(rings[1:], [shape.paint], bottom=None, top=cap, name="lower")
    flanks = [_flank(shape, rings[0], side) for side in (-1.0, 1.0)] if shape.arches else []
    return merge([skirt, body, *flanks], name="lower")


def deck_y_at(shape: Shape, z: float) -> float:
    """The lower body's top at `z`: the belt under the cabin, falling
    `nose_drop_m` to the nose and `tail_drop_m` to the tail."""
    scuttle = shape.front_z_m + shape.cabin_front_m
    deck = shape.front_z_m + shape.cabin_rear_m
    front, rear = shape.body_front_z_m, shape.body_rear_z_m
    y = shape.belt_y_m
    if z < scuttle:
        y -= shape.nose_drop_m * (scuttle - z) / (scuttle - front)
    elif z > deck:
        y -= shape.tail_drop_m * (z - deck) / (rear - deck)
    return y


def waist_y_at(shape: Shape, z: float) -> float:
    """The skirt's top at `z`: the waist, falling with the deck over it so the
    band between them keeps its height to the nose and the tail."""
    if not (shape.nose_drop_m or shape.tail_drop_m):
        return shape.waist_y_m
    return deck_y_at(shape, z) - (shape.belt_y_m - shape.waist_y_m)


def _deck_stations(shape: Shape) -> list[float]:
    """Where a falling deck creases: the scuttle, and the backlight's foot."""
    stations: list[float] = []
    if shape.nose_drop_m:
        stations.append(shape.front_z_m + shape.cabin_front_m)
    if shape.tail_drop_m:
        stations.append(shape.front_z_m + shape.cabin_rear_m)
    return stations


def _falling_deck(
    shape: Shape, waist: Sequence[Sequence[float]], belt: Sequence[Sequence[float]]
) -> MeshData:
    """Waist to belt with the bonnet and the boot falling away from the cabin.

    Both rings gain a station each side at the scuttle and at the backlight's
    foot, so the fall creases there, and the waist falls with the deck
    (`waist_y_at`) so the nose keeps a band of body over its skirt; the cap
    is then one strip a station, each a plane because the height depends on
    `z` alone.
    """
    if len(belt) != 8:
        raise ValueError(f"{shape.kind}: a falling deck needs chamfered corners")
    flank_front, flank_rear = belt[2][2], belt[3][2]
    stations = _deck_stations(shape)
    if not all(flank_front < z < flank_rear for z in stations):
        raise ValueError(f"{shape.kind}: the cabin's end leaves the flank; no deck can fall")

    def stationed(
        ring_: Sequence[Sequence[float]], y_at: Callable[[Shape, float], float]
    ) -> list[Point]:
        hw = ring_[2][0]
        points: list[Point] = [
            *ring_[:3],
            *((hw, 0.0, z) for z in stations),
            *ring_[3:7],
            *((-hw, 0.0, z) for z in reversed(stations)),
            ring_[7],
        ]
        return [(x, y_at(shape, z), z) for x, _, z in points]

    low, high = stationed(waist, waist_y_at), stationed(belt, deck_y_at)
    sides = loft([low, high], [shape.paint], bottom=None, top=None, name="lower")
    # The cap, a strip between each pair of sections nose to tail: the right
    # flank runs up the ring's indices from 1, the left down them from 0.
    count = len(high)
    right = list(range(1, count // 2 + 1))
    left = [0, *range(count - 1, count // 2, -1)]
    caps = [
        polygon_facing(
            [high[left[i]], high[right[i]], high[right[i + 1]], high[left[i + 1]]],
            shape.paint,
            (0.0, 1.0, 0.0),
            name=f"lower_cap_{i}",
        )
        for i in range(len(right) - 1)
    ]
    return merge([sides, *caps], name="lower")


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
    sill = shape.sill_y_m
    bottom: list[tuple[float, float]] = [(z_ends[0], sill)]
    for axle_z in _axle_zs(shape):
        arch = _arch(shape, axle_z)
        if arch[0][0] <= bottom[-1][0] or arch[-1][0] >= z_ends[1]:
            raise ValueError(f"{shape.kind}: the arch at z {axle_z:+.2f} leaves its flank")
        if any(y >= waist_y_at(shape, z) for z, y in arch):
            raise ValueError(f"{shape.kind}: the arch at z {axle_z:+.2f} rises past the waist")
        bottom.extend(arch)
    bottom.append((z_ends[1], sill))
    # A falling deck's creases, so no column's top cuts one.
    for station in _deck_stations(shape):
        for i, ((z0, y0), (z1, y1)) in enumerate(pairwise(bottom)):
            if z0 < station < z1:
                bottom.insert(i + 1, (station, y0 + (y1 - y0) * (station - z0) / (z1 - z0)))
                break
    tag = "l" if side < 0 else "r"
    return merge(
        [
            polygon_facing(
                [
                    (x, y0, z0),
                    (x, y1, z1),
                    (x, waist_y_at(shape, z1), z1),
                    (x, waist_y_at(shape, z0), z0),
                ],
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


@dataclass(frozen=True)
class _Slab:
    """A flat-sided body's wall and roof as `_slab_upper` lofts them."""

    belt_y: float
    shoulder_y: float
    roof_y: float
    half_w: float
    front_z: float
    rear_z: float
    front_run: float
    rear_run: float
    cut: float
    inset: float

    def end_z(self, y: float, *, rear: bool) -> float:
        """The end face's z at height `y`: upright to the belt, raked above."""
        t = min(1.0, max(0.0, (y - self.belt_y) / (self.shoulder_y - self.belt_y)))
        return self.rear_z - self.rear_run * t if rear else self.front_z + self.front_run * t

    def roof_end_z(self, *, rear: bool) -> float:
        """Where the roof's flat ends."""
        z = self.end_z(self.shoulder_y, rear=rear)
        return z - self.inset if rear else z + self.inset

    def flank_z(self, y: float) -> tuple[float, float]:
        """The flat flank's ends at height `y`, inside the corner cuts."""
        return self.end_z(y, rear=False) + self.cut, self.end_z(y, rear=True) - self.cut


def _slab(shape: Shape) -> _Slab:
    shoulder = shape.roof_y_m - shape.crown_m
    rise = shoulder - shape.belt_y_m
    return _Slab(
        belt_y=shape.belt_y_m,
        shoulder_y=shoulder,
        roof_y=shape.roof_y_m,
        half_w=shape.body_half_width_m,
        front_z=shape.body_front_z_m,
        rear_z=shape.body_rear_z_m,
        front_run=_rake_run_m(shape.windscreen_rake_deg, rise),
        rear_run=_rake_run_m(shape.backlight_rake_deg, rise),
        cut=shape.corner_cut_m,
        inset=shape.roof_inset_m,
    )


def _slab_upper(shape: Shape) -> MeshData:
    """Belt to roof as one wall: flat flanks, raked ends, and a crown that
    turns in to the roof — the roof's colour from the shoulder up."""
    b = _slab(shape)
    front, rear = b.end_z(b.shoulder_y, rear=False), b.end_z(b.shoulder_y, rear=True)
    rings = [
        ring(b.belt_y, b.half_w, b.front_z, b.rear_z, b.cut),
        ring(b.shoulder_y, b.half_w, front, rear, b.cut),
        ring(b.roof_y, b.half_w - b.inset, front + b.inset, rear - b.inset, b.cut),
    ]
    return loft(rings, [shape.paint, shape.roof], bottom=None, top=shape.roof, name="wall")


def _slab_glass(shape: Shape) -> list[MeshData]:
    """Every run of side windows, a pane a bay, proud of the flat flank."""
    b = _slab(shape)
    parts: list[MeshData] = []
    for index, run in enumerate(shape.side_glass):
        z0, z1 = shape.front_z_m + run.start_m, shape.front_z_m + run.end_m
        flank0, flank1 = b.flank_z(run.y1_m)
        if not (b.belt_y <= run.y0_m < run.y1_m < b.shoulder_y):
            raise ValueError(f"{shape.kind}: glass run {index} leaves the wall")
        if z0 < flank0 or z1 > flank1:
            raise ValueError(f"{shape.kind}: glass run {index} runs off the flank")
        bay = (z1 - z0 - run.pillar_m * (run.bays - 1)) / run.bays
        head = run.y1_m - run.top_light_m - TOP_LIGHT_BAR_M if run.top_light_m else run.y1_m
        # Over its surround where it has one, still inside the skin.
        proud = FLANK_PROUD_M * 2.0 if run.surround is not None else FLANK_PROUD_M
        for side in run.sides:
            if run.surround is not None:
                parts.append(
                    _flank_quad(
                        shape,
                        side,
                        run.y0_m - SURROUND_M,
                        run.y1_m + SURROUND_M,
                        z0 - SURROUND_M,
                        z1 + SURROUND_M,
                        run.surround,
                        f"surround_{index}",
                    )
                )
            for k in range(run.bays):
                za = z0 + k * (bay + run.pillar_m)
                name = f"glass_{index}_{k}"
                parts.append(
                    _flank_quad(shape, side, run.y0_m, head, za, za + bay, GLASS, name, proud=proud)
                )
                if shape.glint is not None:
                    lean = min(bay * GLINT_LEAN, (head - run.y0_m) * 0.5)
                    x = side * (shape.body_half_width_m + GLINT_PROUD_M)
                    foot0, foot1 = (za + bay * share for share in GLINT_FOOT)
                    parts.append(
                        polygon_facing(
                            [
                                (x, run.y0_m, foot0),
                                (x, run.y0_m, foot1),
                                (x, head, foot1 - lean),
                                (x, head, foot0 - lean),
                            ],
                            shape.glint,
                            (side, 0.0, 0.0),
                            name=f"glint_{index}_{k}_{'l' if side < 0 else 'r'}",
                        )
                    )
                if run.top_light_m:
                    light_y = run.y1_m - run.top_light_m
                    parts.append(
                        _flank_quad(
                            shape,
                            side,
                            light_y,
                            run.y1_m,
                            za,
                            za + bay,
                            GLASS,
                            f"{name}_top",
                            proud=proud,
                        )
                    )
    return parts


def _end_quad(
    b: _Slab,
    y0: float,
    y1: float,
    half_w: float,
    *,
    rear: bool,
    proud: float,
    colour: Colour,
    name: str,
) -> MeshData:
    """A quad on a flat-sided body's end face, following its rake."""
    out = 1.0 if rear else -1.0
    corners = [
        (x, y, b.end_z(y, rear=rear) + out * proud)
        for x, y in ((-half_w, y0), (half_w, y0), (half_w, y1), (-half_w, y1))
    ]
    return polygon_facing(corners, colour, (0.0, 0.0, out), name=name)


def _end_panes(shape: Shape) -> list[MeshData]:
    """The end faces' windows and panels, and their wraps round the corners."""
    b = _slab(shape)
    face_hw = b.half_w - b.cut
    parts: list[MeshData] = []
    for index, pane in enumerate(shape.end_panes):
        if pane.y1_m >= b.shoulder_y or pane.inset_m >= face_hw:
            raise ValueError(f"{shape.kind}: end pane {index} leaves its end face")
        tag = f"pane_{index}_{'rear' if pane.rear else 'front'}"
        parts.append(
            _end_quad(
                b,
                pane.y0_m,
                pane.y1_m,
                face_hw - pane.inset_m,
                rear=pane.rear,
                proud=FLANK_PROUD_M,
                colour=pane.colour,
                name=tag,
            )
        )
        if not pane.corners:
            continue
        out = 1.0 if pane.rear else -1.0
        # Across a chamfer, from the end face's edge to the flank's.
        lean = FLANK_PROUD_M / math.sqrt(2.0)
        near, far = CORNER_WRAP
        for side, side_tag in ((-1.0, "l"), (1.0, "r")):
            corners = []
            for share, y in (
                (near, pane.y0_m),
                (far, pane.y0_m),
                (far, pane.y1_m),
                (near, pane.y1_m),
            ):
                face_z = b.end_z(y, rear=pane.rear)
                corners.append(
                    (
                        side * (face_hw + b.cut * share + lean),
                        y,
                        face_z - out * b.cut * share + out * lean,
                    )
                )
            parts.append(
                polygon_facing(corners, pane.colour, (side, 0.0, out), name=f"{tag}_{side_tag}")
            )
    return parts


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
        for k in range(1, shape.window_bays):
            z = z0 + (z1 - z0) * k / shape.window_bays
            tag = f"{name}_pillar_{k}_{'l' if side < 0 else 'r'}"
            parts.append(_leaning_strip(g, side, z, half, colour, tag))
    return parts


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
    if lamp_y + 0.06 > shape.belt_y_m - max(shape.nose_drop_m, shape.tail_drop_m):
        raise ValueError(f"{shape.kind}: the deck falls below its own lamps")
    bumper_inset = shape.bumper_inset_m
    bumper_hw = hw - (shape.corner_cut_m * 0.5 if bumper_inset is None else bumper_inset)
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
                (-bumper_hw, shape.sill_y_m, z_bumper[0]),
                (bumper_hw, bumper_top, z_bumper[1]),
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
            x = side * (hw - shape.lamp_inset_m)
            lens_half = (0.08, 0.05) if rear else (0.11, 0.05)
            if shape.bezels and not rear and shape.head_lamps == 2:
                z_bezel = face + out * BEZEL_PROUD_M
                parts.append(
                    polygon_facing(
                        [
                            (x - lens_half[0] - BEZEL_M, lamp_y - 0.105 - BEZEL_M, z_bezel),
                            (x + lens_half[0] + BEZEL_M, lamp_y - 0.105 - BEZEL_M, z_bezel),
                            (x + lens_half[0] + BEZEL_M, lamp_y + lens_half[1] + BEZEL_M, z_bezel),
                            (x - lens_half[0] - BEZEL_M, lamp_y + lens_half[1] + BEZEL_M, z_bezel),
                        ],
                        SILVER,
                        (0.0, 0.0, out),
                        name=f"bezel_{side_tag}",
                    )
                )
            if rear or shape.head_lamps == 2:
                parts.append(
                    box(
                        (x - lens_half[0], lamp_y - lens_half[1], z_lens[0]),
                        (x + lens_half[0], lamp_y + lens_half[1], z_lens[1]),
                        RED if rear else LAMP,
                        # The tail lens on the taxi's BRAKE circuit, the head
                        # lens on its head lamps: lit only where a moving car
                        # writes them (`TrafficSystem`, `P3-3c`) — a parked
                        # car's instance data leaves every circuit dark.
                        name=f"taillamp_{side_tag}_brake" if rear else f"headlamp_{side_tag}",
                    )
                )
            # On the taxi's indicator circuits, a side each: lit only where a
            # moving car winks or a stopping one flashes its hazards (`P3-3f`) —
            # a switched-off car's instance data leaves them dark.
            parts.append(
                box(
                    (x - 0.06, lamp_y - 0.105, z_lens[0]),
                    (x + 0.06, lamp_y - 0.06, z_lens[1]),
                    AMBER,
                    name=f"taillamp_{side_tag}_indicator" if rear else f"indicator_{side_tag}",
                )
            )
            if shape.side_lamps:
                x_lamp, y_lamp = x, lamp_y
                if rear:
                    x_lamp -= side * SIDE_LAMP_INBOARD_M
                    y_lamp -= 0.0825
                half_x, half_y = SIDE_LAMP_HALF_M
                parts.append(
                    box(
                        (x_lamp - half_x, y_lamp - half_y, z_lens[0]),
                        (x_lamp + half_x, y_lamp + half_y, z_lens[1]),
                        RED if rear else LAMP,
                        name=f"foglamp_{side_tag}",
                    )
                )
        if shape.head_lamps == 1 and not rear:
            parts.append(
                box(
                    (-0.09, lamp_y - 0.09, z_lens[0]),
                    (0.09, lamp_y + 0.09, z_lens[1]),
                    LAMP,
                    # The head-lamp circuit's name, so a running tram lights it;
                    # the motorcycle's `headlamp_c` is on no circuit.
                    name="headlamp_l",
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
    if not (shape.mirrors or shape.handles or shape.rub_strip is not None):
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
    if shape.shut_lines:
        z0, z1 = g.glass_top_z()
        edges = [
            g.front_z + 0.04,
            *(z0 + (z1 - z0) * k / shape.window_bays for k in range(1, shape.window_bays)),
            z1,
        ]
        for k, z in enumerate(edges):
            foot = _over_arch(shape, z, shape.sill_y_m + 0.04)
            for part in _seams(shape, (z,), foot, shape.belt_y_m):
                parts.append(replace(part, name=f"shut_{k}_{part.name[-1]}"))
    if shape.rub_strip is not None:
        parts.extend(_rub_strips(shape, shape.rub_strip))
    return parts


def _flank_quad(
    shape: Shape,
    side: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    colour: Colour,
    name: str,
    *,
    proud: float = FLANK_PROUD_M,
) -> MeshData:
    """A quad on one flank's plane, `proud` off it, named by its side."""
    x = side * (shape.body_half_width_m + proud)
    return polygon_facing(
        [(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)],
        colour,
        (side, 0.0, 0.0),
        name=f"{name}_{'l' if side < 0 else 'r'}",
    )


def _leaning_strip(
    g: _Glazing, side: float, z: float, half: float, colour: Colour, name: str
) -> MeshData:
    """An upright strip on one side's glass at `z`, leaning in with it."""
    x_low = side * (g.side_x(g.panel_y) + FLANK_PROUD_M)
    x_high = side * (g.side_x(g.glass_y) + FLANK_PROUD_M)
    return polygon_facing(
        [
            (x_low, g.panel_y, z - half),
            (x_low, g.panel_y, z + half),
            (x_high, g.glass_y, z + half),
            (x_high, g.glass_y, z - half),
        ],
        colour,
        (side, 0.0, 0.0),
        name=name,
    )


def _rub_strips(shape: Shape, colour: Colour) -> list[MeshData]:
    """A strip along each flank between the arches, at the bumper's height."""
    axles = _axle_zs(shape)
    reach = shape.arch_radius_m + 0.04
    y0 = shape.sill_y_m + shape.bumper_height_m - 0.05
    return [
        _flank_quad(shape, side, y0, y0 + 0.05, axles[0] + reach, axles[-1] - reach, colour, "rub")
        for side in (-1.0, 1.0)
    ]


def _wipers(shape: Shape) -> list[MeshData]:
    """Two wiper arms lying along the windscreen's foot: on the raked glass of
    a lofted body, over the applied screen of a flat-sided one."""
    if shape.slab_sided:
        slab = _slab(shape)
        screens = [pane for pane in shape.end_panes if not pane.rear and pane.colour == GLASS]
        if not screens:
            raise ValueError(f"{shape.kind}: wipers need a windscreen among `end_panes`")
        screen = min(screens, key=lambda pane: pane.y0_m)
        foot, reach, end_z = screen.y0_m, slab.half_w - slab.cut - screen.inset_m - 0.12, slab.end_z
    else:
        g = _glazing(shape, shape.belt_y_m, shape.roof_y_m)
        foot, reach, end_z = g.panel_y, g.belt_half_w - g.cut - 0.12, g.end_z
    y0, y1 = foot + 0.03, foot + 0.06
    # Over a flat side's applied screen as over a lofted one.
    proud = 0.006 + (FLANK_PROUD_M if shape.slab_sided else 0.0)
    parts: list[MeshData] = []
    for k, (xa, xb) in enumerate(((-reach, -0.06), (0.04, reach - 0.1))):
        corners = [
            (x, y, end_z(y, rear=False) - proud)
            for x, y in ((xa, y0), (xb, y0), (xb, y1), (xa, y1))
        ]
        parts.append(polygon_facing(corners, DARK, (0.0, 0.0, -1.0), name=f"wiper_{k}"))
    return parts


def _doors(shape: Shape) -> list[MeshData]:
    """The kerb-side passenger doors: a dark frame from the step with two
    glazed leaves in it — to the door's head on a flat side; on a lofted body
    to the glass's foot, its posts carried up the leaning glass."""
    if not shape.doors_m:
        return []
    side = KERB_SIDE
    # A flat side takes the whole door to its head; a lofted one the door to
    # the glass's foot, and its posts up the leaning glass.
    g = None if shape.slab_sided else _glazing(shape, shape.belt_y_m, shape.roof_y_m)
    head = shape.door_head_m if g is None else g.panel_y
    assert head is not None
    x = side * (shape.body_half_width_m + FLANK_PROUD_M)
    step_y = shape.sill_y_m + 0.05
    parts: list[MeshData] = []

    def pane(
        z0: float, z1: float, y0: float, y1: float, proud: float, colour: Colour, name: str
    ) -> MeshData:
        xp = x + side * proud
        return polygon_facing(
            [(xp, y0, z0), (xp, y0, z1), (xp, y1, z1), (xp, y1, z0)],
            colour,
            (side, 0.0, 0.0),
            name=name,
        )

    for k, (start, end) in enumerate(shape.doors_m):
        z0, z1 = shape.front_z_m + start, shape.front_z_m + end
        if shape.arches and any(
            abs(z - axle) < shape.arch_radius_m for axle in _axle_zs(shape) for z in (z0, z1)
        ):
            raise ValueError(f"{shape.kind}: door {k} stands in a wheel arch")
        parts.append(pane(z0, z1, step_y, head, 0.0, DARK, f"door_{k}_frame"))
        if shape.door_glass:
            mid, post = (z0 + z1) / 2.0, 0.035
            for leaf, (za, zb) in enumerate(
                ((z0 + post, mid - post / 2.0), (mid + post / 2.0, z1 - post))
            ):
                parts.append(
                    pane(
                        za,
                        zb,
                        step_y + 0.25,
                        head - 0.02,
                        0.003,
                        GLASS,
                        f"door_{k}_leaf_{leaf}",
                    )
                )
        if g is None:
            continue
        # The posts over the side glass, leaning with it.
        posts = (z0, (z0 + z1) / 2.0, z1) if shape.door_glass else (z0, z1)
        parts.extend(
            _leaning_strip(g, side, z, 0.03, DARK, f"door_{k}_post_{j}")
            for j, z in enumerate(posts)
        )
    return parts


def _blind_rear(shape: Shape, belt_y: float, top_y: float, *, name: str) -> list[MeshData]:
    """The panel over the rear of each flank's glass, leaning with it."""
    if shape.blind_rear_share <= 0.0:
        return []
    g = _glazing(shape, belt_y, top_y)
    z0, z1 = g.glass_top_z()
    half = (z1 - z0) * shape.blind_rear_share / 2.0
    return [
        _leaning_strip(g, side, z1 - half, half, shape.paint, f"{name}_blind_{tag}")
        for side, tag in ((-1.0, "l"), (1.0, "r"))
    ]


def _window_bars(shape: Shape, belt_y: float, top_y: float, *, name: str) -> list[MeshData]:
    """The bar across one deck's side glass, on both sides."""
    if shape.window_bar is None:
        return []
    share, height = shape.window_bar
    g = _glazing(shape, belt_y, top_y)
    z0, z1 = g.glass_top_z()
    centre = g.panel_y + (g.glass_y - g.panel_y) * share
    y0, y1 = centre - height / 2.0, centre + height / 2.0
    colour = shape.pillar or shape.roof
    return [
        polygon_facing(
            [
                (side * (g.side_x(y0) + FLANK_PROUD_M), y0, z0),
                (side * (g.side_x(y0) + FLANK_PROUD_M), y0, z1),
                (side * (g.side_x(y1) + FLANK_PROUD_M), y1, z1),
                (side * (g.side_x(y1) + FLANK_PROUD_M), y1, z0),
            ],
            colour,
            (side, 0.0, 0.0),
            name=f"{name}_bar_{'l' if side < 0 else 'r'}",
        )
        for side in (-1.0, 1.0)
    ]


def _over_arch(shape: Shape, z: float, y: float, reach: float = 0.03) -> float:
    """`y`, or the waist there where `z` stands over a wheel arch: a line down a
    flank stops at the arch's crown instead of crossing the opening."""
    if not shape.arches:
        return y
    span = shape.arch_radius_m + reach
    over = any(abs(z - axle) <= span for axle in _axle_zs(shape))
    return max(y, waist_y_at(shape, z)) if over else y


def _seams(shape: Shape, zs: Sequence[float], y0: float, y1: float) -> list[MeshData]:
    """Dark lines on both flanks at `zs` — a sliding door's, a luggage bay's."""
    return [
        _flank_quad(shape, side, y0, y1, z - 0.012, z + 0.012, DARK, f"seam_{i}")
        for side in (-1.0, 1.0)
        for i, z in enumerate(zs)
    ]


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
            hub_slots=shape.hub_slots,
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


def _minibus(shape: Shape) -> list[MeshData]:
    """The route board standing on the roof's front edge."""
    g = _glazing(shape, shape.belt_y_m, shape.roof_y_m)
    roof_front = g.roof_end_z(rear=False)
    return _roof_box(shape, shape.roof_y_m, roof_front + 0.02, rear=False, half=(0.6, 0.14, 0.18))


def _bus(shape: Shape) -> list[MeshData]:
    """The blind's amber line, on the dark panel between the two screens."""
    b = _slab(shape)
    blind = next((pane for pane in shape.end_panes if not pane.rear and pane.colour == DARK), None)
    if blind is None:
        raise ValueError(f"{shape.kind}: the blind needs a dark front pane among `end_panes`")
    margin = (blind.y1_m - blind.y0_m) * 0.22
    return [
        _end_quad(
            b,
            blind.y0_m + margin,
            blind.y1_m - margin,
            b.half_w - b.cut - blind.inset_m - margin,
            rear=False,
            proud=FLANK_PROUD_M + 0.004,
            colour=AMBER,
            name="blind_line",
        )
    ]


def _tram(shape: Shape) -> list[MeshData]:
    """A route board on the roof at each end, and the trolley pole raised
    from its base amidships to the wire behind."""
    b = _slab(shape)
    ends = (b.roof_end_z(rear=False), b.roof_end_z(rear=True))
    top = shape.roof_y_m
    # Raised, but not far: the mesh's box is the tram's collider.
    pole_len, rise, half = shape.length_m * 0.36, 0.3, 0.025
    return [
        *_roof_box(shape, top, ends[0] + 0.02, rear=False, half=(0.5, 0.12, 0.1)),
        *_roof_box(shape, top, ends[1] - 0.02, rear=True, half=(0.5, 0.12, 0.1)),
        box_at((0.0, top + 0.06, 0.0), (0.16, 0.06, 0.22), DARK, name="pole_base"),
        hexahedron(
            [
                (-half, top + 0.12, 0.0),
                (half, top + 0.12, 0.0),
                (half, top + 0.12 + rise, pole_len),
                (-half, top + 0.12 + rise, pole_len),
            ],
            [
                (-half, top + 0.17, 0.0),
                (half, top + 0.17, 0.0),
                (half, top + 0.17 + rise, pole_len),
                (-half, top + 0.17 + rise, pole_len),
            ],
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


# How far a box lorry's body stands behind its cab.
CARGO_GAP_M = 0.08


def _lorry(shape: Shape) -> list[MeshData]:
    """The box body behind the cab, on the chassis the lower body draws: its
    two rear doors' seam and hinge posts, and a rail along each lower edge.

    Lofted on the chassis's own chamfered ring: a square box overhung the cut
    corners under it by their whole depth.
    """
    if shape.cargo_top_m is None:
        raise ValueError(f"{shape.kind}: a box body needs `cargo_top_m`")
    hw, cut = shape.body_half_width_m, shape.corner_cut_m
    z0 = shape.front_z_m + shape.cabin_rear_m + CARGO_GAP_M
    z1 = shape.body_rear_z_m
    floor, top = shape.belt_y_m, shape.cargo_top_m
    tail = z1 + FLANK_PROUD_M
    low, high = floor + 0.05, top - 0.05
    # The rear face, inside the chamfers, and a hinge post's width and inset.
    face_hw, post, inset = hw - cut, 0.03, 0.04

    def on_tail(x0: float, x1: float, name: str) -> MeshData:
        return polygon_facing(
            [(x0, low, tail), (x1, low, tail), (x1, high, tail), (x0, high, tail)],
            DARK,
            (0.0, 0.0, 1.0),
            name=name,
        )

    return [
        loft(
            [ring(floor, hw, z0, z1, cut), ring(top, hw, z0, z1, cut)],
            [shape.paint],
            bottom=shape.paint,
            top=shape.paint,
            name="cargo",
        ),
        on_tail(-0.012, 0.012, "cargo_door_seam"),
        on_tail(-face_hw + inset, -face_hw + inset + post, "cargo_hinge_l"),
        on_tail(face_hw - inset - post, face_hw - inset, "cargo_hinge_r"),
        *(
            _flank_quad(shape, side, floor, floor + 0.07, z0 + cut, z1 - cut, SILVER, "cargo_rail")
            for side in (-1.0, 1.0)
        ),
    ]


DETAILS: dict[str, Callable[[Shape], list[MeshData]]] = {
    "lorry": _lorry,
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
    if shape.slab_sided:
        parts.append(_slab_upper(shape))
        parts.extend(_slab_glass(shape))
        parts.extend(_end_panes(shape))
    else:
        parts.append(
            _glasshouse(
                shape, shape.belt_y_m, shape.roof_y_m, shape.roof, name="glasshouse", cap=True
            )
        )
        parts.extend(_pillars(shape, shape.belt_y_m, shape.roof_y_m, name="glasshouse"))
        parts.extend(_window_bars(shape, shape.belt_y_m, shape.roof_y_m, name="glasshouse"))
        parts.extend(_blind_rear(shape, shape.belt_y_m, shape.roof_y_m, name="glasshouse"))
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
    parts.extend(_doors(shape))
    if shape.wipers:
        parts.extend(_wipers(shape))
    parts.extend(DETAILS.get(shape.kind, lambda _: [])(shape))
    parts.extend(_wheels(shape) if shape.arches else [_underframe(shape)])
    body = _liveried(merge([_marked(part) for part in parts], name=shape.kind), shape)
    return replace(_cabin_lit(body, shape), material=BODY_MATERIAL)


def _liveried(body: MeshData, shape: Shape) -> MeshData:
    """Restamp the paint in the kind's livery colour as `MARKER_LIVERY`.

    Only paint-marked vertices: a lens wearing the same swatch (the bike's red
    tail lamp) keeps its lamp marker. A livery that marks nothing is refused,
    since the palette would then repaint nothing without a word.
    """
    if shape.livery is None:
        return body
    assert body.colours is not None and body.uvs is not None
    hit = np.all(body.colours[:, :3] == np.array(shape.livery, dtype=np.uint8), axis=1)
    hit &= body.uvs[:, 1] == MARKER_PAINT
    if not hit.any():
        raise ValueError(f"{shape.kind}: livery {shape.livery} is on no painted vertex")
    uvs = body.uvs.copy()
    uvs[hit, 1] = MARKER_LIVERY
    return replace(body, uvs=uvs)


def _cabin_lit(body: MeshData, shape: Shape) -> MeshData:
    """Restamp a lit saloon's glass as its cabin marker, the whole of it."""
    if shape.cabin is None:
        return body
    assert body.uvs is not None
    uvs = body.uvs.copy()
    uvs[uvs[:, 1] == MARKER_GLASS, 1] = shape.cabin
    return replace(body, uvs=uvs)


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
    body = _liveried(merge([_marked(part) for part in parts], name=shape.kind), shape)
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
        nose_drop_m=0.1,
        tail_drop_m=0.06,
        hub_slots=6,
        bezels=True,
        shut_lines=True,
        rub_strip=DARK,
        wipers=True,
    )


@dataclass(frozen=True)
class Taxi:
    """One licence's taxi: the player's die-cast body (`make_vehicle`, `Q190`)
    in the licence's paint, its door shut and its wheels baked in (`P3-85`).

    Not a `Shape`: nothing here is a proportion. The body is the one the
    player drives, so the taxi in the next lane is the same car.
    """

    kind: str
    paint: Colour
    # The cant rail, roof and pillars: silver on the urban taxi, white on the
    # other two licences.
    roof: Colour


# How far a taxi's door mirror stands off the flank. The player's stand
# `Proportions.mirror_reach_m` out on their stalks; a roster vehicle's box is
# its collider, so these are tucked to the door handles' depth.
TAXI_MIRROR_REACH_M = -0.04
# The greenhouse parts whose silver is the roof's paint, not chrome.
_TAXI_ROOF_PARTS = ("glass_", "greenhouse")


def taxi(licence: Taxi) -> MeshData:
    """A licence's taxi as one marked mesh, in the roster's frame."""
    chassis = Chassis()
    shape = replace(Proportions(), mirror_reach_m=TAXI_MIRROR_REACH_M)
    parts = []
    roofed = 0
    for part in taxi_parts(chassis, shape):
        if part.name.startswith(_TAXI_ROOF_PARTS):
            part, hit = _repainted(part, SILVER, licence.roof)
            roofed += hit
        parts.append(_marked(part))
    # The names are `make_vehicle`'s: renamed there, the roof would stay silver
    # on a green taxi without a word.
    if not roofed:
        raise ValueError(f"{licence.kind}: no part in {_TAXI_ROOF_PARTS} wears the roof's silver")
    hinge = np.asarray(door_hinge(chassis, shape), dtype=np.float64)
    parts.append(taxi_door(chassis, shape).translated(hinge))
    half_track = chassis.track_m / 2.0
    for index, axle_z in enumerate(chassis.axle_z_m):
        for side, tag in ((-1.0, "l"), (1.0, "r")):
            wheel = _wheel(
                chassis.wheel_radius_m,
                shape.wheel_width_m,
                WHEEL_SEGMENTS,
                faces=(side,),
                hub_slots=shape.hub_slots,
                name=f"wheel_{index}_{tag}",
            )
            parts.append(_marked(wheel).translated((side * half_track, chassis.hub_y_m, axle_z)))
    body = merge(parts, name=licence.kind)
    assert body.colours is not None and body.uvs is not None
    # The licence's paint on every painted red vertex; a red lens keeps its red.
    painted = np.all(body.colours[:, :3] == np.array(RED, dtype=np.uint8), axis=1)
    painted &= body.uvs[:, 1] == MARKER_PAINT
    colours = body.colours.copy()
    colours[painted, :3] = licence.paint
    low, high = body.aabb()
    centred = replace(body, colours=colours).translated(
        (0.0, -chassis.ground_y_m, -(low[2] + high[2]) / 2.0)
    )
    return replace(centred, material=BODY_MATERIAL)


def _repainted(part: MeshData, old: Colour, new: Colour) -> tuple[MeshData, int]:
    """`part` with every vertex wearing `old` in `new`, and how many did."""
    assert part.colours is not None
    hit = np.all(part.colours[:, :3] == np.array(old, dtype=np.uint8), axis=1)
    colours = part.colours.copy()
    colours[hit, :3] = new
    return replace(part, colours=colours), int(hit.sum())


RosterEntry = Shape | Taxi

ROSTER: tuple[RosterEntry, ...] = (
    replace(_car("car_a", WHITE, WHITE), livery=WHITE),
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
        livery=NAVY,
        nose_drop_m=0.14,
        hub_slots=4,
        bezels=True,
        shut_lines=True,
        wipers=True,
    ),
    # The urban licence's red under silver, and the New Territories' and
    # Lantau's (`Q183`): the same Crown Comfort, green or blue under white.
    Taxi("taxi", RED, SILVER),
    Taxi("taxi_nt", NT_TAXI_GREEN, WHITE),
    Taxi("taxi_lantau", LANTAU_TAXI_BLUE, WHITE),
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
        # The Coaster's four big windows a side and its solid rear corner.
        window_bays=4,
        blind_rear_share=0.07,
        mirrors=False,
        livery=MINIBUS_GREEN,
        cabin=MARKER_CABIN_DIM,
        hub_slots=6,
        bezels=True,
        wipers=True,
        # The Coaster's folding door, behind the front wheel.
        doors_m=((2.15, 2.95),),
        # The sliding lights' rail across each window.
        window_bar=(0.5, 0.03),
    ),
    # The double-decker, in Citybus yellow over its blue skirt: an Enviro500
    # MMC's flat sides, read off Tiny's model of one — the lower deck's
    # windows in groups between the doors, a blank offside where the stairs
    # climb, one long band upstairs, the blind dark between two raked screens.
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
        backlight_rake_deg=2.0,
        corner_cut_m=0.16,
        roof_inset_m=0.12,
        wheel_radius_m=0.5,
        wheel_width_m=0.3,
        axles_m=(2.6, 8.2, 9.8),
        skirt=CITYBUS_BLUE,
        mirrors=False,
        cabin=MARKER_CABIN,
        wipers=True,
        # The entrance ahead of the front axle and the exit amidships.
        doors_m=((0.55, 1.75), (5.3, 6.5)),
        door_head_m=2.34,
        # Inside the end face: at the default the lenses hung past its corners.
        lamp_inset_m=0.3,
        slab_sided=True,
        crown_m=0.2,
        glint=GLINT,
        side_glass=(
            Glass(1.34, 2.3, 1.9, 5.2, 2, sides=(KERB_SIDE,), pillar_m=0.04, surround=DARK),
            Glass(1.34, 2.3, 6.6, 10.6, 3, sides=(KERB_SIDE,), pillar_m=0.04, surround=DARK),
            # The driver's window, then the staircase's blank panel.
            Glass(1.34, 2.3, 0.55, 1.75, 1, sides=(-KERB_SIDE,), surround=DARK),
            Glass(1.34, 2.3, 3.3, 10.6, 5, sides=(-KERB_SIDE,), pillar_m=0.04, surround=DARK),
            Glass(2.85, 3.85, 0.7, 11.4, 8, pillar_m=0.04, surround=DARK),
        ),
        end_panes=(
            EndPane(1.35, 2.3, corners=True),
            EndPane(2.34, 2.81, colour=DARK),
            EndPane(2.85, 3.85, corners=True),
            EndPane(2.85, 3.85, rear=True),
            # The engine's cover under the rear window.
            EndPane(1.15, 2.1, rear=True, inset_m=0.25, colour=DARK),
        ),
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
        livery=NAVY,
        wipers=True,
        doors_m=((0.6, 1.5),),
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
        cabin_front_m=0.8,
        cabin_rear_m=4.6,
        windscreen_rake_deg=36.0,
        backlight_rake_deg=4.0,
        corner_cut_m=0.12,
        roof_inset_m=0.1,
        wheel_radius_m=0.32,
        wheel_width_m=0.2,
        axles_m=(0.95, 3.55),
        window_bays=3,
        livery=WHITE,
        # The H300's short bonnet under a steep screen, and a panel van's
        # blind rear quarter, off Tiny's model of one.
        nose_drop_m=0.18,
        blind_rear_share=0.36,
        hub_slots=6,
        bezels=True,
        wipers=True,
    ),
    # The tram, read off Tiny's model of one: flat sides from the skirt to a
    # dark crowned roof, rounded ends with the screens wrapping them, a top
    # light over each upstairs window, five windows between two open doorways
    # downstairs, one lamp on the dash. Plain green — the model wears no band.
    # Its skirt still runs down to the rails, the trucks hidden under it (the
    # user's call, `Q166`), where the model shows its truck.
    Shape(
        kind="tram",
        length_m=8.89,
        width_m=2.0,
        paint=TRAM_GREEN,
        roof=TRAM_ROOF,
        sill_y_m=0.12,
        belt_y_m=1.3,
        roof_y_m=4.7,
        cabin_front_m=0.25,
        cabin_rear_m=8.64,
        windscreen_rake_deg=1.0,
        backlight_rake_deg=1.0,
        corner_cut_m=0.3,
        roof_inset_m=0.1,
        wheel_radius_m=0.3,
        wheel_width_m=0.12,
        axles_m=(1.75, 7.14),
        bumper_m=0.04,
        grille=None,
        plates=False,
        arches=False,
        head_lamps=1,
        mirrors=False,
        side_lamps=True,
        cabin=MARKER_CABIN,
        # The exit beside the driver and the entrance at the tail, open
        # doorways behind their gates.
        doors_m=((0.45, 1.25), (7.64, 8.44)),
        door_glass=False,
        door_head_m=2.45,
        slab_sided=True,
        crown_m=0.22,
        glint=GLINT,
        lamp_inset_m=0.42,
        bumper_inset_m=0.3,
        side_glass=(
            Glass(3.0, 4.05, 0.5, 8.39, 8, top_light_m=0.16),
            Glass(1.45, 2.4, 2.0, 6.3, 5, sides=(KERB_SIDE,)),
            Glass(1.45, 2.4, 1.3, 7.6, 7, sides=(-KERB_SIDE,)),
        ),
        end_panes=(
            EndPane(1.45, 2.4, corners=True),
            EndPane(3.0, 4.05, corners=True),
            EndPane(1.45, 2.4, rear=True, corners=True),
            EndPane(3.0, 4.05, rear=True, corners=True),
        ),
    ),
    # The 5.5-tonne box lorry, an Isuzu N: a cab over the front axle, a box
    # body on a dark chassis behind it (`_lorry`). The cab is the glasshouse;
    # the lower body's top behind it is the chassis deck the box stands on.
    Shape(
        kind="lorry",
        length_m=6.0,
        width_m=2.1,
        paint=WHITE,
        roof=WHITE,
        sill_y_m=0.45,
        belt_y_m=1.2,
        roof_y_m=2.3,
        cabin_front_m=0.1,
        cabin_rear_m=1.7,
        windscreen_rake_deg=8.0,
        backlight_rake_deg=1.0,
        corner_cut_m=0.1,
        roof_inset_m=0.08,
        wheel_radius_m=0.38,
        wheel_width_m=0.24,
        axles_m=(1.05, 4.35),
        skirt=DARK,
        window_bays=1,
        mirrors=False,
        livery=WHITE,
        # The cab's doors under its windows: the glass starts a third up.
        panel_share=0.32,
        glass_share=0.5,
        cargo_top_m=3.0,
        hub_slots=6,
        bezels=True,
        wipers=True,
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
        livery=RED,
    ),
)


# The lofted kinds, every one but the taxis.
SHAPES: tuple[Shape, ...] = tuple(entry for entry in ROSTER if isinstance(entry, Shape))


def build_roster(roster: Sequence[RosterEntry] = ROSTER) -> list[MeshData]:
    """Every kind as one marked mesh, in roster order."""
    meshes: list[MeshData] = []
    for entry in roster:
        if isinstance(entry, Taxi):
            meshes.append(taxi(entry))
        else:
            meshes.append(motorcycle(entry) if entry.single_track else vehicle(entry))
    return meshes


def write_roster(
    out_dir: Path, roster: Sequence[RosterEntry] = ROSTER
) -> tuple[Path, int, list[MeshData]]:
    """The library, one node per kind; returns where it went and its bytes."""
    meshes = build_roster(roster)
    path = out_dir / LIBRARY_FILE
    groups: list[MeshGroup] = [material_parts(inked(mesh)) for mesh in meshes]
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
