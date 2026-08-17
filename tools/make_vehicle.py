"""Generate the roster's low-poly toy vehicles (`P3-11`).

    python tools/make_vehicle.py
    python tools/make_vehicle.py --out-dir /tmp/vehicles --report

`ART_DESIGN.md` specifies the vehicles as *proportions* — "shortened wheelbase,
tall greenhouse, exaggerated wheel arches" — rather than as detail. Proportions
are three numbers, so they are worth tuning in a diff instead of guessing in a
mesh, and the roster is six vehicles that differ mostly by those numbers. Hence
a generator rather than a modelled asset.

⚠️ **The chassis is an input, not an output.** `P0-5` tuned handling against the
wheel hardpoints in `game/scenes/vehicle/taxi.tscn` — `WheelMount` markers then,
`VehicleWheel3D` nodes since `Q50`, at the same positions. Either way those
points are authored rather than inferred from a mesh, and the physics never reads
this file's output, so a model built to a different wheelbase would look correct
and silently drive to the old tuning. `Chassis` below therefore mirrors the scene, and
`etl/tests/test_make_vehicle.py` fails if the two ever disagree.

Output goes to `game/assets/authored/vehicles/`, which is **committed** — these
are hand-authored assets under CC BY-SA 4.0, not build output. See LICENSING.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.gltf import MeshData, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import (  # noqa: E402
    Colour,
    box,
    box_at,
    flank_edges,
    loft,
    polygon,
    polygon_facing,
    ring,
)

LOG = logging.getLogger("make_vehicle")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "vehicles"

# Body and tyre ship as separate files rather than as meshes in one.
# Godot imports a `.glb` as a PackedScene, so a single file would have to be
# instanced whole — and the wheel inside it would arrive at the body's origin,
# once, when the scene needs four of them at hardpoints it already owns.
# Referencing the sub-resource instead (`taxi.glb::ArrayMesh_xxxx`) means
# hand-writing IDs the importer generates, which no longer resolve the first
# time anything upstream changes. Two files keeps the scene the authority on
# *where* a wheel is and the mesh the authority on what it looks like.
BODY_FILE = "taxi_body.glb"
# ⚠️ NOT "taxi_wheel". Godot's glTF importer converts any node whose name ends
# in `_wheel` into a VehicleWheel3D by naming convention, silently — and P0-5a
# measured VehicleWheel3D and rejected it, because its friction is isotropic and
# cannot express a drift. The importer reintroduced it through a filename, wrapped
# the mesh in a physics node with no VehicleBody3D above it, and the wheels
# stopped drawing. Nothing reported an error. Suffixes to avoid: _wheel, _col,
# _convcol, _navmesh, _occ, _rigid, _vehicle.
WHEEL_FILE = "taxi_tyre.glb"

# How far a lamp or a plate stands out of the bodywork it is seated in. Small
# enough to read as part of the panel, large enough that no view resolves the
# join as z-fighting. See `_flush_fixture`.
FIXTURE_PROUD_M = 0.015

# RGB, 0-255. `ART_DESIGN.md` asks for 3-5 flat colours per vehicle; these are
# the five. Red body with a silver roof is called non-negotiable there — it is
# the HK Island urban taxi, and a green or blue one is a different territory.
RED = (198, 32, 40)
# ⚠️ A grey, not a near-white. This was (226, 228, 230), and under the scene's
# directional light plus tonemap it came back off the roof at ~250 — the car had
# a white lid, not a silver one. The albedo has to leave headroom for the
# exposure the city is lit at, so it is chosen against a *screenshot* of the
# roof rather than against the swatch. It is also the cant rail, the wheel hubs
# and the door handles, all of which want the same correction.
#
# ⚠️ **Warmed on the hue axis only, and `L*` is the axis that must not move.**
# `ART_DESIGN.md` records this roof rendering ice-blue and diagnoses it as a
# near-neutral taking its hue from ambient. It does — but measured, the value
# above was itself authored blue at `b* -3.56`, so half the fault was in the
# swatch and no lighting change would have reached it. Now `L* 70.21 -> 70.17`,
# `b* -3.56 -> +3.07`: the headroom the paragraph above was written to protect
# is untouched, and the trim carries a hue of its own to resist the sky's.
SILVER = (175, 171, 166)
DARK = (30, 32, 36)
GLASS = (18, 19, 22)
LAMP = (242, 236, 205)
# ⚠️ A sixth colour, where `ART_DESIGN.md` says 3-5 per vehicle. It buys the
# indicator in the tail-lamp cluster, which is three lenses stacked — amber
# over white over red — and that stack is a specific identifying feature of the
# car's rear. Two colours cannot express three lenses. Flagged rather than
# quietly taken: see docs/DECISIONS.md, P3-11.
AMBER = (226, 138, 32)
# ⚠️ A seventh, on the same terms. It is the 4 SEATS badge and nothing else —
# the one green thing on a red car, which is exactly why the badge is legible
# as a shape now that its lettering is gone. Nothing may borrow it for anything
# that is not that badge, or the count stops being defensible.
BADGE_GREEN = (12, 116, 82)
# ⚠️ An eighth, and the one whose *darkness* is the whole feature. It is the lens
# of the high-level brake lamp in the backlight and nothing else. That lamp is
# asked to be invisible until it lights, and it sits on near-black glazing —
# `RED` at the authored value is a bright bar across a black window every time
# the car coasts, which is the opposite of what a third brake lamp is for. Dark
# enough to disappear against `GLASS`; saturated enough that the shader's
# hue-normalised emission burns it red rather than pink. See `_high_brake_lamp`.
DEEP_RED = (58, 10, 12)

# The glTF material name `generated_scene_import.gd` matches to hand the body a
# `ShaderMaterial`. A name is the only channel glTF offers — the same contract
# the tiles use for `city_facade`, and it fails the same way: silently, in the
# engine, where nothing but a render can see it.
BODY_MATERIAL = "vehicle_body"

# Surface markers, shipped in `UV.y` and read by `vehicle_body.gdshader`. Same
# shape as the tiles' payload, where `floor(UV.y)` is the surface marker — the
# body is one merged primitive, so nothing else tells a windscreen from the
# bodywork it is set into.
#
# ⚠️ **Not `COLOR_0.a`**, which is the cheaper-looking place for a mask and is
# the one `ARCHITECTURE.md` rules out: `vertex_color_use_as_albedo` is set
# project-wide, and an opaque `BaseMaterial3D` ignores albedo alpha only until
# somebody enables transparency, after which the car renders see-through with
# no error.
MARKER_PAINT = 0.0
MARKER_GLASS = 1.0
MARKER_LAMP = 2.0
MARKER_TRIM = 3.0

# Which marker each authored colour earns — per *vertex*, because the greenhouse
# is one lofted part carrying both `GLASS` and `SILVER` and no per-part rule
# could split it.
#
# ⚠️ **Only the two unambiguous swatches are here, and the omissions are the
# point.** `LAMP` and `AMBER` are *also* the registration plates and the roof
# sign, so a colour rule marks a matte plate as a lamp lens — colour is not
# materiality, the same collision `Q43` records on the facades under two
# predicates wearing one name. Those parts are marked by name below.
COLOUR_MARKERS: dict[Colour, float] = {
    GLASS: MARKER_GLASS,
    SILVER: MARKER_TRIM,
}

# Parts whose every vertex is a lamp lens, whatever colour it is wearing. Name
# is the authority here: the tail cluster's bottom lens is `RED` on `RED`
# bodywork, and the plates share their swatches with the lenses.
LAMP_PARTS = ("headlamp_", "indicator_", "foglamp_", "taillamp_")

# Which switched circuit a lens is wired to, shipped in `UV.x` and read by
# `vehicle_body.gdshader`. `MARKER_LAMP` says a surface is a lens; this says
# whether anything ever turns it *on*, and which switch does it.
#
# ⚠️ **A second channel rather than four more markers**, because the two
# questions are independent: a lit lens still wants the lens roughness and the
# lens reflection, and folding "which circuit" into `UV.y` would make the
# shading branch enumerate the wiring. `UV.x` was reserved and zero — a tile
# spends it on metres above base, which nothing on a 4 m car needs.
#
# ⚠️ **Ordering, not a set, and 4 is a seam rather than a limit.** The shader
# indexes `int(UV.x) - 1` into `lamp_lit`, which is a `vec4`, so circuits 5 and
# up land in the second vector `lamp_front`. Renumbering these moves lenses
# between the two and is not a rename.
CIRCUIT_NONE = 0.0
CIRCUIT_BRAKE = 1.0
CIRCUIT_REVERSE = 2.0
CIRCUIT_INDICATOR_L = 3.0
CIRCUIT_INDICATOR_R = 4.0
CIRCUIT_SIDELAMP = 5.0
CIRCUIT_HEADLAMP = 6.0

# ⚠️ **Left and right are separate circuits, and that is the whole point of
# indicators** — one amber circuit would flash both flanks, which is a hazard
# warning and not a turn. The side tags come from `taxi_body`'s own
# `(("l", -1.0), ("r", 1.0))`, where `-Z` is forward, so `r` is the car's right.
#
# Keyed on the full part name rather than a prefix: the tail cluster is three
# lenses on one lamp and they are three different circuits. `taxi_body` raises if
# any key here names no part, so a rename cannot quietly unwire a lamp.
#
# ⚠️ **The two front circuits are deliberately *not* split left from right**,
# which is the opposite call to the indicators directly above and for the same
# reason. Sides are separate there because a one-sided amber is the whole
# meaning of the lamp; a one-sided white lamp has no meaning at all except a
# blown bulb, so a second circuit could only ever express a fault nothing
# simulates. One switch, both flanks.
#
# ⚠️ **`foglamp_*` is switched as the position lamp, and the name is about where
# it sits rather than what it does.** `taxi_body` builds it as "a small white
# lamp low in the bumper", which is where a fog lamp lives and also what the
# small lamp *reads* as from a chase camera — a second, smaller pair of points
# clear of the main beam. Dimming `headlamp_*` instead was the alternative and
# is worse twice over: `lamp_emission` is 1.6 against `clean_daylight.tres`'s
# 1.0 glow threshold, so a lens at a fraction of that carries no bloom and is
# "merely a brighter swatch" by the shader's own note, and a dim main beam reads
# as a weak headlamp rather than as a different lamp.
LAMP_CIRCUITS: dict[str, float] = {
    "headlamp_l": CIRCUIT_HEADLAMP,
    "headlamp_r": CIRCUIT_HEADLAMP,
    "foglamp_l": CIRCUIT_SIDELAMP,
    "foglamp_r": CIRCUIT_SIDELAMP,
    "indicator_l": CIRCUIT_INDICATOR_L,
    "indicator_r": CIRCUIT_INDICATOR_R,
    "taillamp_l_indicator": CIRCUIT_INDICATOR_L,
    "taillamp_r_indicator": CIRCUIT_INDICATOR_R,
    "taillamp_l_reverse": CIRCUIT_REVERSE,
    "taillamp_r_reverse": CIRCUIT_REVERSE,
    "taillamp_l_brake": CIRCUIT_BRAKE,
    "taillamp_r_brake": CIRCUIT_BRAKE,
    "taillamp_high_brake": CIRCUIT_BRAKE,
}


class CabinRing(NamedTuple):
    """One horizontal section of the greenhouse, in absolute coordinates.

    Named rather than a bare 5-tuple because `greenhouse_profile`'s own guard
    reads three of these fields, and a guard that indexes positionally is the
    thing it exists to prevent: reorder the tuple and the ordering check starts
    comparing half-widths to z, silently and in the direction of "passes".
    """

    y_m: float
    half_width_m: float
    z_front: float
    z_rear: float
    cut_m: float


def _rake_run_m(rake_deg: float, rise_m: float) -> float:
    """How far a face raked `rake_deg` off vertical travels over `rise_m`."""
    return rise_m * float(np.tan(np.radians(rake_deg)))


def opening_radius_m(chassis: Chassis, shape: Proportions) -> float:
    """Half-width of a wheel opening — the tyre, plus the clearance round it.

    A function rather than a hand-copied sum, because it had reached five copies
    across the generator and its tests and one of them was a test re-deriving
    what it was meant to be checking. Takes both because the tyre is the
    chassis' and the clearance is the caricature's.
    """
    return chassis.wheel_radius_m + shape.well_clearance_m


@dataclass(frozen=True)
class Chassis:
    """The hardpoints, mirrored from `taxi.tscn` and `handling.tres`.

    Nothing here may be changed to suit the model. If the car should sit
    differently, the scene and the handling profile move first and this follows
    — in that order, with the drive re-reviewed.
    """

    wheelbase_m: float = 2.60  # wheel nodes at z = +/-1.30
    track_m: float = 1.60  # wheel nodes at x = +/-0.80
    wheel_radius_m: float = 0.35  # handling.tres, wheel_radius_m
    suspension_rest_m: float = 0.35  # handling.tres, hub sits this far below the node

    @property
    def hub_y_m(self) -> float:
        """Wheel centre at rest. Markers are the top of the spring, not the hub."""
        return -self.suspension_rest_m

    @property
    def ground_y_m(self) -> float:
        return self.hub_y_m - self.wheel_radius_m

    @property
    def axle_z_m(self) -> tuple[float, float]:
        """Front and rear axle centrelines. The wheelbase straddles the origin."""
        return (-self.wheelbase_m / 2.0, self.wheelbase_m / 2.0)


@dataclass(frozen=True)
class Proportions:
    """The toy caricature, in metres. These are the numbers worth tuning.

    Defaults caricature a Toyota Crown Comfort — the Hong Kong urban taxi — by
    cutting its overhangs
    length and raising its greenhouse — see `length_m` for the figures.
    """

    # Lengthened from 4.00 with the cabin pulled back, which is what buys the
    # long bonnet and boot of a three-box saloon. The real car is 4.69 m on a
    # 2.68 m wheelbase; the toy keeps the scene's 2.60 m and shortens around it.
    length_m: float = 4.30
    # ⚠️ Flush with the tyres, which reach x 0.90 exactly. Three values were
    # tried and the two failures are worth keeping: at 0.86 the wheels were
    # sealed inside the bodywork and the car rendered with none at all; at 0.76
    # they were visible but stood *outside* the flank on a perched lip, which
    # reads as separate standing fenders — a pre-war car, not a 1990s saloon.
    # Flush bodywork with the wheel in a hole cut through it is the only
    # arrangement that is neither, and it is why `_flank` exists.
    half_width_m: float = 0.90
    # The wheel well: how far the rim turns inward, and how much bigger the
    # opening is than the tyre. The clearance has to be generous — a tight
    # opening on a flush tyre shows nothing from any angle but dead abeam.
    well_depth_m: float = 0.14
    well_clearance_m: float = 0.11
    # ⚠️ Corner chamfer. Zero gives square corners and the cheapest possible
    # car, which is what `B3`'s traffic wants; the player's is rounded because
    # the reference art is, and because a 90° vertical edge is what reads as
    # blocky rather than as a Crown Comfort.
    corner_cut_m: float = 0.16
    sill_y_m: float = -0.20
    belt_y_m: float = 0.38
    roof_y_m: float = 0.86
    # Greenhouse, as fractions of the body: where the cabin starts and ends
    # along z, and how far the roof pulls in from the belt line.
    cabin_front_z_m: float = -0.62
    # ⚠️ The C-pillar base, and it was 1.00 — 0.30 m *ahead* of the rear axle,
    # where every reference photograph puts it at or behind. A short cabin is
    # what made the backlight unaffordable, because rake is paid for out of roof
    # length: at 1.00 a 30° screen left a 1.01 m roof, shorter than the upright
    # version started with. At 1.25 the same rake leaves 1.26 m. The two numbers
    # are one decision, not two, which is why they moved together.
    cabin_rear_z_m: float = 1.25
    roof_inset_m: float = 0.13
    # ⚠️ Screen rake, in degrees from vertical, and these are the **authored**
    # numbers — the roof taper is derived from them rather than the reverse.
    # It used to be the other way: two taper distances placed the roof edge, and
    # the top of the glass was a bare `* 0.8` of them. That literal is very
    # nearly the fraction of the greenhouse the glass occupies (0.38 of 0.48 =
    # 0.792), so the old code was already treating the screen and the cant rail
    # above it as one continuous raked plane — it simply had no word for the
    # angle of that plane, and no way to set one without moving the roof.
    # Measured off the reference: the front came out at 32.3°, near enough, and
    # the rear at 18.6°, which reads as a vertical wall from the chase camera —
    # the one angle `ART_DESIGN.md` says most players ever see.
    windscreen_rake_deg: float = 35.0
    backlight_rake_deg: float = 30.0
    # The roof sign is most of what says "taxi" at a distance — as a shape now
    # rather than as a word. Wider across the car than along it, which is the
    # proportion the real fitting has and the one the chase camera sees.
    sign_half_length_m: float = 0.11
    sign_half_width_m: float = 0.26
    sign_height_m: float = 0.13
    wheel_width_m: float = 0.20
    # Detail dials. `ART_DESIGN.md` budgets 800-2,000 triangles per vehicle and
    # the first pass came in at 384, so these are what spend the rest: rounder
    # wheels, a curved arch over each one, and the panel lines and pillars a
    # single extruded box cannot suggest. They are dials rather than constants
    # because `B3`'s traffic wants the same shapes an order of magnitude cheaper
    # — a roster car is 20 m away and never looked at.
    wheel_segments: int = 18
    arch_segments: int = 7
    # How far a chamfer ring pulls in from the face it softens. At this scale a
    # bevel is one more ring, not a curve — see `loft`.
    bevel_m: float = 0.06
    # The silver band between the glass and the roof. The reference art shows
    # roof paint coming down over the pillars; without this the roof reads as a
    # pale lid laid on a red box, which is the note the first review returned.
    cant_rail_m: float = 0.10
    # The high-level brake lamp, sitting in the bottom centre of the backlight.
    # `rise_m` is measured from the belt line, so it follows the glass rather
    # than the body — rake the backlight and the lamp rakes with it.
    #
    # ⚠️ Sized against the glass it sits in, not against the tail cluster. At
    # 0.36 m across it is a little under half the cabin's width, which is the
    # proportion a real high-level strip has; matching the outer lenses' 0.17 m
    # would read as a third small lamp floating in the window rather than as the
    # bar that it is.
    high_brake_half_width_m: float = 0.18
    high_brake_half_height_m: float = 0.022
    high_brake_rise_m: float = 0.055
    # Registration plates. Blank rectangles, not lettering: the characters were
    # a texture, and a pixel font is the one thing on the car that does not
    # belong in a flat-shaded city. Colour still carries the information a plate
    # carries here — Hong Kong follows the UK, white at the front and yellow at
    # the rear — so the two ends stay told apart without a glyph.
    plate_half_width_m: float = 0.17
    plate_half_height_m: float = 0.055
    # ⚠️ Both plate heights, and the badge below, are chosen to sit *above* the
    # sill tuck at `sill_y_m + bevel_m`. That is where the body stops sloping
    # gently and folds in hard, and `_seated_depth` answers a fixture spanning
    # the fold by making it deep enough to bridge it — so it stands 4 cm off
    # the paint at its bottom edge and hangs below the car's own outline.
    plate_front_y_m: float = -0.08
    plate_rear_y_m: float = 0.16
    # ⚠️ Top of the bumper, and the bumper is *paint*, not a part. Everything
    # below this line on the lower body is DARK — the nose and tail through
    # `loft`, the flanks through `_flank` — so the car keeps a bumper band all
    # the way round without one face leaving the silhouette. Raise it and the
    # dark hem climbs the doors; the *front* plate, both badges and the fog
    # lamps sit on the band and have to stay under it. The rear plate does not —
    # it is on the boot, as the real car's is, which is why it alone is exempt
    # from the "stays on the bumper" test.
    bumper_top_y_m: float = 0.02
    # ⚠️ Top of the dark rocker, and the **third** attempt at a strip down the
    # flank. The first was a box standing 2-3 cm proud, which read as a stick;
    # the second continued the bumper band at `bumper_top_y_m`, which is 38% of
    # a 0.58 m flank and read as a stripe painted on a toy. Both are written up
    # in `_flank_detail`. This one is paint, at the *sill* rather than at bumper
    # height — 10% of the flank, which is what the reference photographs show.
    #
    # ⚠️ A hand-copied literal of `bumper_bottom_y_m`, on purpose, and
    # `test_one_line_runs_all_the_way_round` holds the two together. Sharing the
    # line is the whole idea: one break runs unbroken around the car and only
    # what sits *below* it changes — red across the nose and tail, dark along
    # the flank, which is a bumper with a valance under it meeting a sill panel.
    # Set it to `sill_y_m` to switch the rocker off; `_flank` then emits no dark
    # faces at all, which is the setting `B3`'s traffic wants.
    rocker_top_y_m: float = -0.14
    # How far forward of a door's trailing edge its handle sits. The handles
    # used to be placed from `cabin_mid_z_m` +/- a fixed 0.42, which is not
    # where a handle is on a car and does not survive the cabin changing length:
    # at `cabin_rear_z_m = 1.25` that put the rear one 130 mm out over the wheel
    # opening. Anchored to the door edges it follows the cabin instead.
    handle_inset_m: float = 0.10
    # Half the handle's length along the car. Promoted out of `_flank_detail`'s
    # box literals because `_rear_door_z_m` needs it: "is there room for a second
    # handle behind the first" is a question about the handle's own size.
    handle_half_length_m: float = 0.075
    # The 4 SEATS badge, as a shape. It was a green dome with lettering on it,
    # drawn as pixels; the words are gone and the dome is geometry now, faceted
    # at the segment count the wheel arch uses because nothing else in this city
    # is smooth either.
    badge_x_m: float = 0.34
    badge_y_m: float = -0.125
    badge_radius_m: float = 0.085
    badge_segments: int = 7

    @property
    def front_z_m(self) -> float:
        return -self.length_m / 2.0

    @property
    def rear_z_m(self) -> float:
        return self.length_m / 2.0

    @property
    def cabin_mid_z_m(self) -> float:
        return (self.cabin_front_z_m + self.cabin_rear_z_m) / 2.0

    @property
    def cabin_half_width_m(self) -> float:
        """The greenhouse stands one bevel inboard of the flank at the belt line."""
        return self.half_width_m - self.bevel_m

    @property
    def glass_band_m(self) -> float:
        """Height of the glazed band — belt line to the bottom of the cant rail."""
        return self.roof_y_m - self.cant_rail_m - self.belt_y_m

    @property
    def glass_top_y_m(self) -> float:
        """Top of the glazed band, where the cant rail starts.

        Named for the same reason `bumper_bottom_y_m` is: `belt_y_m +
        glass_band_m` had reached three call sites and a test, and a fixture
        seated in the window is exactly the caller that must not carry its own
        copy of where the window ends.
        """
        return self.belt_y_m + self.glass_band_m

    @property
    def bumper_bottom_y_m(self) -> float:
        """Where the dark bumper band stops and the red valance below it starts.

        Not a ring of its own: this *is* the sill tuck, the body's own fold, and
        `lower_profile` has always emitted a ring there. Naming it is what turns
        an accident into a statement — the fixtures that sit on the bumper all
        clear this line already, and `test_none_of_them_reaches_below_the_valance`
        now says so against this property rather than recomputing the sum.
        """
        return self.sill_y_m + self.bevel_m

    def cabin_ends_m(self, rise_m: float) -> tuple[float, float]:
        """(front z, rear z) of the cabin `rise_m` above the belt line.

        The one place the sign flip lives. Rake carries the front of the cabin
        *backwards* and the rear of it *forwards*, and writing that out per ring
        is two chances to get a minus sign right — which the glass ring and the
        roof ring above it each needed.
        """
        return (
            self.cabin_front_z_m + _rake_run_m(self.windscreen_rake_deg, rise_m),
            self.cabin_rear_z_m - _rake_run_m(self.backlight_rake_deg, rise_m),
        )

    @property
    def roof_front_taper_m(self) -> float:
        """How far the roof's leading edge sits behind the windscreen's base.

        Derived, where it used to be authored. The windscreen and the cant rail
        that caps it are one plane, so one angle places both — and the roof edge
        is wherever that plane has got to by the time it reaches `roof_y_m`.
        """
        return _rake_run_m(self.windscreen_rake_deg, self.glass_band_m + self.cant_rail_m)

    @property
    def roof_rear_taper_m(self) -> float:
        """The backlight's counterpart. See `roof_front_taper_m`."""
        return _rake_run_m(self.backlight_rake_deg, self.glass_band_m + self.cant_rail_m)

    @property
    def greenhouse_profile(self) -> tuple[CabinRing, ...]:
        """The cabin's rings: the belt line, the top of the glass, and the roof.

        The two ends of each come from the rake angles through `cabin_ends_m`,
        so raking a screen moves the glass and the roof edge above it together
        and by construction.

        ⚠️ **The stack has to stay ordered, and nothing downstream would say so.**
        `loft` joins ring *i* to ring *i+1* whatever their coordinates are: give
        it a front edge that moves backwards, or two rings that cross, and it
        builds an inverted greenhouse out of quads that are individually valid —
        no error, no degenerate triangle, and a normal check that still passes
        because `polygon_facing` faithfully turns each face outward from a
        profile that is itself inside out. Rake past about 55° at this cabin
        length and that is what comes out, so the guard lives here rather than in
        a test — a `Proportions` this wrong refuses to yield a profile at all.

        ⚠️ **The ordering test is `<=`, not `<`.** Zero rake is a *square*
        greenhouse, which lofts perfectly well and is the cheap car `B3`'s
        traffic wants — the same offer `corner_cut_m = 0` and
        `rocker_top_y_m = sill_y_m` already make. Only genuine inversion is
        refused; collapse is the roof-length guard below, which is independent.
        """
        cut, hw = self.corner_cut_m, self.cabin_half_width_m
        glass_front, glass_rear = self.cabin_ends_m(self.glass_band_m)
        roof_front, roof_rear = self.cabin_ends_m(self.glass_band_m + self.cant_rail_m)
        rings = (
            CabinRing(self.belt_y_m, hw, self.cabin_front_z_m, self.cabin_rear_z_m, cut * 0.8),
            CabinRing(
                self.glass_top_y_m,
                hw - self.roof_inset_m * 0.7,
                glass_front,
                glass_rear,
                cut * 0.7,
            ),
            CabinRing(self.roof_y_m, hw - self.roof_inset_m, roof_front, roof_rear, cut * 0.55),
        )
        for lower, upper in pairwise(rings):
            if upper.z_front < lower.z_front or lower.z_rear < upper.z_rear:
                raise ValueError(
                    f"greenhouse rings are out of order between y {lower.y_m:+.3f} and "
                    f"{upper.y_m:+.3f}: front {lower.z_front:+.3f} -> {upper.z_front:+.3f}, "
                    f"rear {lower.z_rear:+.3f} -> {upper.z_rear:+.3f}"
                )
        roof = rings[-1]
        if roof.z_rear - roof.z_front <= 2.0 * roof.cut_m:
            raise ValueError(
                f"windscreen_rake_deg={self.windscreen_rake_deg} and "
                f"backlight_rake_deg={self.backlight_rake_deg} leave no roof between "
                f"{roof.z_front:+.3f} and {roof.z_rear:+.3f} on a "
                f"{self.cabin_rear_z_m - self.cabin_front_z_m:.2f} m cabin"
            )
        return rings

    @property
    def sign_z_m(self) -> float:
        """Centre of the roof sign, set back slightly from the cabin's middle."""
        return self.cabin_mid_z_m - 0.06

    @property
    def lower_profile(self) -> tuple[tuple[float, float, float], ...]:
        """(z inset from each end, y, corner cut) for the rings of the lower body.

        Five rings, not the four the shape needs: the extra one is the top of
        the bumper band, and it exists only so `loft` has an edge to change
        colour at. Its inset and cut are *interpolated* from its neighbours
        rather than chosen, which is what makes it a colour change and nothing
        else — the silhouette is identical with the ring and without it, and
        `face_inset_m` returns the same answer either way.
        """
        tuck = self.bevel_m
        cut = self.corner_cut_m
        base = (
            (tuck * 2.4, self.sill_y_m, cut * 0.6),
            (tuck, self.sill_y_m + tuck, cut * 0.85),
            (0.0, self.belt_y_m - tuck * 1.4, cut),
            (tuck * 0.8, self.belt_y_m, cut * 0.85),
        )
        # ⚠️ Spliced at a fixed index, so the band top has to fall between the
        # two rings it is spliced between. `bumper_top_y_m`'s own comment invites
        # raising it, and past the shoulder the ring stack comes out unsorted —
        # at which point `np.interp` returns nonsense without raising and `loft`
        # builds an inverted band, both silently.
        if not base[1][1] < self.bumper_top_y_m < base[2][1]:
            raise ValueError(
                f"bumper_top_y_m must sit between {base[1][1]:+.3f} and {base[2][1]:+.3f}, "
                f"got {self.bumper_top_y_m:+.3f}"
            )
        ys = [entry[1] for entry in base]
        bumper = (
            float(np.interp(self.bumper_top_y_m, ys, [entry[0] for entry in base])),
            self.bumper_top_y_m,
            float(np.interp(self.bumper_top_y_m, ys, [entry[2] for entry in base])),
        )
        return (*base[:2], bumper, *base[2:])

    def face_inset_m(self, y: float) -> float:
        """How far the nose and tail draw in at height `y`.

        The lower body is lofted through rings that step inward towards the
        sill, so "flush with the nose" is a different z at every height. That
        did not matter while the plate and the fog lamps were bolted to a
        bumper bar, which was flat; with the bar folded back into the bodywork
        it is the only thing that decides whether a fixture floats or sinks.
        """
        profile = self.lower_profile
        return float(np.interp(y, [entry[1] for entry in profile], [entry[0] for entry in profile]))


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------


def _seated_depth(
    shape: Proportions, y_low: float, y_high: float, *, rear: bool
) -> tuple[float, float]:
    """(inner z, outer z) for a fixture covering this band of the nose or tail.

    The panel a lamp or a plate sits on is not vertical — `face_inset_m` draws
    the body in by up to 14 cm between the belt line and the sill — so seating
    one takes two numbers, not a thickness. The back goes to where the panel is
    furthest *in*, so nothing hangs off the paint at one edge; the face stands
    `FIXTURE_PROUD_M` clear of where the panel is furthest *out*, so it is
    visible along its whole height rather than only in the middle.

    That distinction did not exist while the bumper was a bar: it was flat, and
    everything low on the car was bolted to it with one hand-copied z.

    ⚠️ **Every profile knot inside the band is sampled, not just its edges.**
    `face_inset_m` is not monotonic — the body is furthest out at
    `belt_y_m - bevel_m * 1.4`, in the *middle* of the range — so two endpoints
    do not bracket it. Measured on the top tail-lamp lens, which straddles that
    knot, the two-sample version delivered 8.5 mm of the 15 mm it promises.
    Nothing showed, because the shortfall was smaller than the margin; shrink
    `FIXTURE_PROUD_M` and the lens sinks into the paint at mid-height only.

    ⚠️ **It compensates in y alone, and the corner chamfer is a function of x.**
    A fixture placed outboard of `half_width_m - corner_cut_m` overhangs the
    chamfer, and its back cap then floats clear of the paint: 10 cm on the tail
    lamps, 9 cm on the indicators, measured. Invisible at the angles the car is
    drawn at and pre-existing — the bezel this replaced overhung further — so it
    is recorded rather than fixed. Do not read the promise above as covering x.
    """
    knots = [y for _, y, _ in shape.lower_profile if y_low < y < y_high]
    insets = [shape.face_inset_m(y) for y in (y_low, y_high, *knots)]
    end = shape.rear_z_m if rear else shape.front_z_m
    inward = -1.0 if rear else 1.0
    return (
        end + inward * max(insets),
        end + inward * (min(insets) - FIXTURE_PROUD_M),
    )


def _flush_fixture(
    shape: Proportions,
    *,
    centre: tuple[float, float],
    half: tuple[float, float],
    colour: Colour,
    rear: bool,
    name: str,
) -> MeshData:
    """A rectangular lamp or plate seated in the nose or the tail. See `_seated_depth`."""
    half_x, half_y = half
    x, y = centre
    z0, z1 = sorted(_seated_depth(shape, y - half_y, y + half_y, rear=rear))
    return box((x - half_x, y - half_y, z0), (x + half_x, y + half_y, z1), colour, name=name)


def _high_brake_lamp(shape: Proportions) -> MeshData:
    """The high-level brake lamp, in the bottom centre of the backlight.

    The third brake lamp every car built since the nineties carries, and the one
    the driver behind actually reads — it is at eye height and in the middle of
    the car, where the outer cluster is neither. On the chase camera, which
    `ART_DESIGN.md` calls the only angle most players ever see, it is the most
    visible lamp on the vehicle.

    ⚠️ **"Inside the window" is a look, not a coordinate.** The glazing is an
    opaque flat colour — there is no transparency on this car and
    `ART_DESIGN.md`'s anti-goals keep it that way — so a lamp *behind* the
    backlight is a lamp that is never drawn. It is seated on the glass the same
    way the tail lamps are seated on the paint: `FIXTURE_PROUD_M` clear of the
    surface, which at 15 mm on a 4 m car reads as sitting in the window rather
    than as bolted to the outside of it.

    ⚠️ **Seated against the backlight's rake, which is why this is not a
    `box_at`.** The screen leans 30° off vertical, so its z moves 12 mm across
    the lamp's own 44 mm of height. Ignoring that sinks the top edge into the
    glass and floats the bottom one off it — the same arithmetic `_seated_depth`
    does for the nose and the tail, against a different surface, which is why it
    is done here rather than by calling that.
    """
    y_low = shape.belt_y_m + shape.high_brake_rise_m - shape.high_brake_half_height_m
    y_high = shape.belt_y_m + shape.high_brake_rise_m + shape.high_brake_half_height_m
    if y_low <= shape.belt_y_m or y_high >= shape.glass_top_y_m:
        raise ValueError(
            f"the high-level brake lamp spans y {y_low:+.3f}..{y_high:+.3f}, which leaves the "
            f"glazed band {shape.belt_y_m:+.3f}..{shape.glass_top_y_m:+.3f} — "
            "it would be seated on the boot lid or the cant rail, not in the window"
        )

    # Rake carries the backlight forward as it rises, so the low edge is the one
    # furthest back. The box runs from the high edge's plane — the innermost
    # point, so nothing hangs off the glass — to the low edge's, plus the stand-off.
    z_high = shape.cabin_ends_m(y_high - shape.belt_y_m)[1]
    z_low = shape.cabin_ends_m(y_low - shape.belt_y_m)[1]
    return box(
        (-shape.high_brake_half_width_m, y_low, z_high),
        (shape.high_brake_half_width_m, y_high, z_low + FIXTURE_PROUD_M),
        DEEP_RED,
        name="taillamp_high_brake",
    )


def _wheel(
    radius: float, width: float, segments: int, *, rim_fraction: float = 0.58, name: str
) -> MeshData:
    """One wheel, centred on the origin and rolling about X.

    Emitted once and instanced four times in the scene rather than baked in
    four places: the scene already owns where the wheels are, and a wheel that
    has to follow suspension travel has to be its own node anyway.
    """
    if segments < 3:
        raise ValueError(f"'{name}': a wheel needs at least three segments, got {segments}")

    half = width / 2.0
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    rim = [(float(radius * np.cos(a)), float(radius * np.sin(a))) for a in angles]

    parts: list[MeshData] = []
    for i, (y0, z0) in enumerate(rim):
        y1, z1 = rim[(i + 1) % segments]
        # Wound from +x to -x, not the other way. The mirrored order sends every
        # tread normal into the axle instead of out of it, which backface
        # culling renders as a wheel-shaped hole — and the whole-mesh normal
        # check reads 0% outward rather than something ambiguous.
        parts.append(
            polygon(
                [(half, y0, z0), (-half, y0, z0), (-half, y1, z1), (half, y1, z1)],
                DARK,
                name=f"{name}_tread_{i}",
            )
        )
        # Each face is a dark sidewall ring around a silver rim rather than one
        # silver disc. A disc reads as a flat grey blob at any distance; the
        # ring is what makes the wheel look like a wheel, and the review asked
        # for exactly that.
        wy0, wz0 = y0 * rim_fraction, z0 * rim_fraction
        wy1, wz1 = y1 * rim_fraction, z1 * rim_fraction
        for face_x in (half, -half):
            wall = [
                (face_x, y0, z0),
                (face_x, y1, z1),
                (face_x, wy1, wz1),
                (face_x, wy0, wz0),
            ]
            hub = [(face_x, 0.0, 0.0), (face_x, wy0, wz0), (face_x, wy1, wz1)]
            parts.append(polygon_facing(wall, DARK, (face_x, 0.0, 0.0), name=f"{name}_wall_{i}"))
            parts.append(polygon_facing(hub, SILVER, (face_x, 0.0, 0.0), name=f"{name}_hub_{i}"))
    return merge(parts, name=name)


# --------------------------------------------------------------------------
# The taxi
# --------------------------------------------------------------------------


def taxi_body(chassis: Chassis, shape: Proportions) -> MeshData:
    """The body as one mesh, and so one draw call and one material."""
    front_z, rear_z = shape.front_z_m, shape.rear_z_m
    hw = shape.half_width_m
    parts: list[MeshData] = []

    # Lower body, lofted rather than boxed. The extra rings are the bevel: a
    # tucked sill at the bottom and a drawn-in shoulder at the belt, which is
    # what stops the flank reading as a slab without curving a single face.
    profile = shape.lower_profile
    lower_rings = [
        ring(y, hw, front_z + inset_z, rear_z - inset_z, ring_cut)
        for inset_z, y, ring_cut in profile
    ]
    parts.append(
        loft(
            lower_rings,
            # Red, dark, then two red: the bumper, painted on, with the body's
            # own valance below it. It used to be a box standing 6 cm proud of
            # each end, and at the size the car is actually played at that bar
            # was the widest thing on it. Bodywork keeps the bumper visible and
            # takes it out of the silhouette.
            #
            # ⚠️ The first band is RED, and it was DARK — so the bumper ran to
            # the bottom of the car and there was nothing under it. Every
            # reference photograph shows the opposite: the dark band stops, and
            # red bodywork carries on below it to the bottom edge. That valance
            # is the lowest 27% of what used to be solid black. The ring it
            # starts at is `bumper_bottom_y_m`, which the flank shares.
            [RED, DARK, RED, RED],
            bottom=DARK,
            top=RED,
            # The two long flanks are `_flank`'s, because a loft band cannot
            # carry the wheel opening cut through it.
            skip_edges=flank_edges(len(lower_rings[0])),
            name="lower",
        )
    )

    # Greenhouse: belt to roof through a glass band and a silver cant rail, so
    # the roof colour comes down over the pillars the way the real paint does
    # rather than sitting on top like a lid.
    #
    # The three rings and their ordering guard are `greenhouse_profile`'s. They
    # used to be written out here, with the top of the glass placed at a bare
    # `* 0.8` of the roof taper — which is how the car ended up with a backlight
    # raked 18.6° that nobody had chosen and nobody could change on its own.
    parts.append(
        loft(
            [ring(*section) for section in shape.greenhouse_profile],
            [GLASS, SILVER],
            bottom=GLASS,
            top=SILVER,
            name="greenhouse",
        )
    )

    # Roof sign, raked rather than a plain cuboid: narrower and shorter at the
    # top, which is the profile the real fitting has and what stops it reading
    # as a white brick. Blank — see `_plates` for why no lettering survives.
    sign_z = shape.sign_z_m
    parts.append(
        loft(
            [
                ring(
                    shape.roof_y_m,
                    shape.sign_half_width_m,
                    sign_z - shape.sign_half_length_m,
                    sign_z + shape.sign_half_length_m,
                ),
                # Raked across its width only, never its depth, so the fore and
                # aft faces stay vertical planes at constant z. Nothing is stuck
                # to them any more, but the silhouette a raked box gives from
                # the side is the whole reason the rake is here.
                ring(
                    shape.roof_y_m + shape.sign_height_m,
                    shape.sign_half_width_m * 0.86,
                    sign_z - shape.sign_half_length_m,
                    sign_z + shape.sign_half_length_m,
                ),
            ],
            [LAMP],
            bottom=DARK,
            top=SILVER,
            name="sign",
        )
    )

    # ⚠️ No bumper *parts*. There are no boxes here any more and there should
    # not be: the bumper is the dark band `loft` and `_flank` paint below
    # `bumper_top_y_m`, so it is visible from every angle and adds nothing to
    # the silhouette. Adding a box back is how it went wrong the first time.
    parts.append(box_at((0.0, 0.11, front_z + 0.01), (0.42, 0.09, 0.03), DARK, name="grille"))
    parts.extend(_plates(shape))
    parts.extend(_badge(shape, rear=rear) for rear in (False, True))
    # Centred, so it is outside the per-side loop below — the only lamp on the
    # car that is not one of a pair.
    parts.append(_high_brake_lamp(shape))

    for tag, side in (("l", -1.0), ("r", 1.0)):
        # The front cluster is three lamps, not one pale block: the main beam
        # inboard, an amber indicator outboard of it, and a small white lamp low
        # in the bumper. The amber is what stops the nose reading as two blank
        # rectangles, and it pairs with the amber at the top of the tail cluster.
        # ⚠️ **`0.58` is also authored in `game/scenes/vehicle/taxi.tscn`**, which
        # seats `HeadlampL`/`HeadlampR` — the cones the lamps throw (`P3-11e`) —
        # at the same offset. Nothing carries a part coordinate across the
        # Python/Godot seam, so moving this lens leaves the light where it was
        # and the beam simply stops coming out of the lamp. Visible only in a
        # frame, and only if someone looks at the nose.
        parts.append(
            box_at(
                (side * 0.58, 0.19, front_z + 0.015),
                (0.15, 0.085, 0.035),
                LAMP,
                name=f"headlamp_{tag}",
            )
        )
        parts.append(
            box_at(
                (side * 0.80, 0.19, front_z + 0.02),
                (0.065, 0.085, 0.035),
                AMBER,
                name=f"indicator_{tag}",
            )
        )
        # Seated in the bumper band rather than bolted to a bumper bar, so its
        # depth follows the panel it sits in instead of being copied by hand.
        parts.append(
            _flush_fixture(
                shape,
                centre=(side * 0.66, -0.04),
                half=(0.105, 0.03),
                colour=LAMP,
                rear=False,
                name=f"foglamp_{tag}",
            )
        )
        # Three lenses stacked in the cluster, top to bottom: amber indicator,
        # white reverse, red tail and brake. Ordering is not decorative — it is
        # what the car actually carries, and getting it upside down would be as
        # wrong to a local eye as the wrong badge.
        #
        # ⚠️ They sit straight on the paint, with no dark bezel behind them, and
        # that costs the bottom lens: RED on RED bodywork has only the lens's
        # own edges to separate it, so the cluster reads as two lamps and a
        # bump at anything past a few metres. The bezel existed to buy that
        # contrast. Removing it was asked for with the trade understood — do not
        # "fix" it by making the lens cream, which is the earlier bug and a
        # white tail lamp besides. What the lens has instead is a *circuit*: it
        # is the brake lamp, and a brake lamp that lights separates itself.
        #
        # ⚠️ **Named for the circuit, not numbered `0/1/2` as they were.** The
        # names are what `LAMP_CIRCUITS` wires, so the stacking order and the
        # wiring are one list rather than two that can disagree.
        for offset, colour, circuit in (
            (0.073, AMBER, "indicator"),
            (0.0, LAMP, "reverse"),
            (-0.073, RED, "brake"),
        ):
            parts.append(
                _flush_fixture(
                    shape,
                    centre=(side * (hw - 0.13), 0.21 + offset),
                    half=(0.085, 0.034),
                    colour=colour,
                    rear=True,
                    name=f"taillamp_{tag}_{circuit}",
                )
            )
        # Wing mirrors: wider than they are deep. The earlier proportions were
        # 0.12 x 0.09 x 0.15, longer front-to-back than across, which is a stalk
        # rather than a mirror — part of what the review read as strange.
        parts.append(
            box_at(
                (side * (hw + 0.025), 0.34, shape.cabin_front_z_m + 0.06),
                (0.032, 0.04, 0.035),
                DARK,
                name=f"mirror_{tag}",
            )
        )

    # The two flanks, each with its wheel openings cut through.
    # The flank may not run past the point where the chamfer takes over, or it
    # stands proud of it as a flat fin and cancels the rounding — 0.24 m of it
    # at each lower corner, before this was clamped.
    flank_z0 = max(front_z + inset_z + ring_cut for inset_z, _, ring_cut in profile)
    flank_z1 = min(rear_z - inset_z - ring_cut for inset_z, _, ring_cut in profile)
    for side_tag, side in (("l", -1.0), ("r", 1.0)):
        parts.extend(
            _flank(chassis, shape, side=side, ends=(flank_z0, flank_z1), name=f"flank_{side_tag}")
        )

    parts.extend(_flank_detail(chassis, shape))
    _check_wiring(parts)
    body = merge([_marked(part) for part in parts], name="taxi_body")
    # `merge` deliberately does not carry `material` — many meshes in, one out,
    # and inheriting whichever was first would be a coin toss. The caller names
    # the result, exactly as `buildings._write_tile` does for a tile.
    return replace(body, material=BODY_MATERIAL)


def _check_wiring(parts: Sequence[MeshData]) -> None:
    """Fail if `LAMP_CIRCUITS` names a part that will not carry its circuit.

    ⚠️ **The failure this catches is silent everywhere else.** A lens whose name
    no longer matches its key ships `CIRCUIT_NONE`, which is a perfectly valid
    value meaning "never lights" — the glTF is well-formed, the import is clean,
    the car renders, and the only symptom is a brake lamp that stays dark in a
    frame nobody is grading. Names are the wiring here, so a rename is a
    rewiring, and it has to be loud.

    Both directions, because there are two ways to lose a lamp and they look
    identical from the outside: a key naming no part at all, and a key naming a
    part that is not a lens. The shader reads `UV.x` only inside its
    `MARKER_LAMP` branch, so a circuit stamped on bodywork is never switched.

    Run over the parts rather than asserted in a test because the person who
    renames a part is the person running this, and `pytest` is a separate step
    that a regenerate does not require.
    """
    named = {part.name for part in parts}
    unwired = sorted(LAMP_CIRCUITS.keys() - named)
    if unwired:
        raise ValueError(
            f"LAMP_CIRCUITS names parts the body does not build: {unwired}. "
            "A lamp was renamed and is now wired to nothing."
        )
    unlit = sorted(name for name in LAMP_CIRCUITS if not name.startswith(LAMP_PARTS))
    if unlit:
        raise ValueError(
            f"LAMP_CIRCUITS wires parts that are not lenses: {unlit}. "
            f"The shader only switches {MARKER_LAMP} surfaces, so these would ship dark."
        )


def _marked(part: MeshData) -> MeshData:
    """Stamp a part's vertices with the shader payload its shading needs.

    `UV.y` carries the surface marker and `UV.x` the switched circuit — which of
    the car's lamps, if any, turns this surface on. A tile spends `UV.x` on
    height above base; nothing on a 4 m car needs that.

    Two rules for the marker, and which one applies is decided by whether the
    swatch is ambiguous. `GLASS` and `SILVER` name exactly one material each, so
    a colour lookup is exact and splits the greenhouse's lofted band correctly.
    Every other lens shares its colour with something matte, so `LAMP_PARTS`
    marks by name and overrides.

    The name rule is not tidiness. **The tail cluster's bottom lens is `RED` on
    `RED` bodywork**, which is exactly why `ART_DESIGN.md` records the cluster
    reading as "amber-over-white with a bump where the red should be" — no
    colour rule can see it. Marking it by name lets the shader separate it by
    *shading*, which leaves the authored colours alone: the bezel behind the
    cluster was removed on request with the trade understood, and making the
    lens cream is the earlier bug and a white tail lamp besides.

    ⚠️ **The circuit is looked up on the whole name, where the marker matches a
    prefix, and the difference is load-bearing.** `taillamp_` is one prefix and
    three circuits — indicator, reverse, brake — stacked on one lamp.
    """
    if part.colours is None:
        raise ValueError(f"part '{part.name}': cannot mark a part with no vertex colours")

    markers = np.full(len(part.colours), MARKER_PAINT, dtype=np.float32)
    rgb = part.colours[:, :3]
    for colour, marker in COLOUR_MARKERS.items():
        markers[np.all(rgb == np.array(colour, dtype=np.uint8), axis=1)] = marker
    if part.name.startswith(LAMP_PARTS):
        markers[:] = MARKER_LAMP

    uvs = np.zeros((len(part.colours), 2), dtype=np.float32)
    uvs[:, 0] = LAMP_CIRCUITS.get(part.name, CIRCUIT_NONE)
    uvs[:, 1] = markers
    return replace(part, uvs=uvs)


def _plates(shape: Proportions) -> list[MeshData]:
    """Front and rear registration plates, in that order.

    Blank. The characters were pixels on a texture sheet, and a bitmap font is
    the one thing on this car that no amount of triangles reaches and nothing
    else in the city has. What survives is the part that is colour rather than
    text: Hong Kong follows the UK, so the plate is **white at the front and
    yellow at the rear**, and that alone still says which end of the car you
    are looking at. Kept as its own function because it is also the only
    asymmetry the tests can use to prove the model is not mirrored.
    """
    return [
        _flush_fixture(
            shape,
            centre=(0.0, shape.plate_front_y_m),
            half=(shape.plate_half_width_m, shape.plate_half_height_m),
            colour=LAMP,
            rear=False,
            name="plate_front",
        ),
        _flush_fixture(
            shape,
            centre=(0.0, shape.plate_rear_y_m),
            half=(shape.plate_half_width_m, shape.plate_half_height_m),
            colour=AMBER,
            rear=True,
            name="plate_rear",
        ),
    ]


def _badge(shape: Proportions, *, rear: bool) -> MeshData:
    """The 4 SEATS badge — a green half-disc standing on its flat edge.

    Geometry, where it used to be a drawing. The badge was a dome with 「TAXI /
    4 / SEATS」 lettered across it on the decal sheet; the words are gone, and
    what is left is a shape no texture is needed to say. Faceted at
    `badge_segments`, because a smooth-shaded curve on a flat-shaded car is the
    one thing that would look imported from a different game.

    A prism rather than a flat cut-out for the same reason the plate is a box:
    the bumper band it sits on slopes, and only a solid with depth can be proud
    of that panel at the top of the badge and buried at the bottom. `loft`
    builds it, extruding along Z — see `axis` there for why that is not a
    second implementation.
    """
    x, y0, radius = shape.badge_x_m, shape.badge_y_m, shape.badge_radius_m
    angles = np.linspace(np.pi, 0.0, shape.badge_segments + 1)
    outline = [(x + radius * float(np.cos(a)), y0 + radius * float(np.sin(a))) for a in angles]
    # Sorted, so `rings[0]` is always the end `loft` caps facing -Z. The nose
    # seats its face at the *lower* z and the tail at the higher one, and
    # passing them in call order would turn one of the two badges inside out.
    return loft(
        [
            [(px, py, z) for px, py in outline]
            for z in sorted(_seated_depth(shape, y0, y0 + radius, rear=rear))
        ],
        [BADGE_GREEN],
        bottom=BADGE_GREEN,
        top=BADGE_GREEN,
        axis=2,
        name="badge_rear" if rear else "badge_front",
    )


def _flank(
    chassis: Chassis,
    shape: Proportions,
    *,
    side: float,
    ends: tuple[float, float],
    name: str,
) -> list[MeshData]:
    """One side of the lower body, with an arch cut out over each wheel.

    ⚠️ This replaced a body narrower than its own track with a lip perched on
    top. That arrangement put the tyres and their arches *outside* the flank,
    which reads as separate standing fenders — a pre-war car, not the 1990s
    saloon this is meant to be. A Crown Comfort's flank is flush and the wheel
    sits in a hole in it, so the flank has to be built around the hole.

    Everything above the arc is bodywork; everything below is the opening. The
    rim then turns inward to an inner wall, so an eye at the kerb sees a dark
    wheel well rather than straight through the car.

    The flank is red from the rocker to the belt line and dark below it — see
    `panels` for what that band is and, just as importantly, what it is not.
    `_flank_detail` keeps the running list of what else does *not* go here.
    """
    x_out = side * shape.half_width_m
    x_in = side * (shape.half_width_m - shape.well_depth_m)
    opening_r = opening_radius_m(chassis, shape)
    hub_y = chassis.hub_y_m
    wheels_z = chassis.axle_z_m
    front_z, rear_z = ends

    def arc_y(z: float, wheel_z: float) -> float:
        """Top of the opening at this z — the circle over the wheel."""
        offset = abs(z - wheel_z)
        if offset >= opening_r:
            return shape.sill_y_m
        # Clamped, not just guarded: the circle dips below the sill for the
        # last 2.5 cm of the opening, which no column samples at seven
        # segments but would hang bodywork under the floor from 37 up.
        return max(shape.sill_y_m, hub_y + float(np.sqrt(opening_r**2 - offset**2)))

    def panels(z0: float, z1: float, y0: float, y1: float, *, tag: str) -> list[MeshData]:
        """One stretch of flank, from the arc (or the sill) up to the belt line.

        The two z and the two y are positional and interchangeable by mistake —
        transposing the pairs compiles and builds a silently wrong quad — so
        `tag` is keyword-only to keep the four coordinates adjacent and ordered.

        Two bands, split at `rocker_top_y_m`: dark below, red above. ⚠️ **This
        is the third dark strip tried down this flank and the first two were
        both rejected**, so the form matters more than the fact of it. It is
        *paint*, so it adds nothing to the silhouette — the first attempt was a
        box standing 2-3 cm proud, and it read as a stick. And it is at the
        **sill**, 10% of a 0.58 m flank — the second attempt continued the
        bumper band down from `bumper_top_y_m`, which is 38% of it, and read as
        a stripe painted on a toy. The line it starts at is the one the nose and
        tail already break at, so the two meet at the corner chamfers with no
        jog; what differs is only which side of it is dark.

        ⚠️ **The stretch is cut where the arc crosses the rocker line, and
        clamping to the line instead is wrong in a way that preserves area.**
        Clamped, the dark band's outer corner is dragged up to the line while
        its inner corner stays on the arc, which fills a sliver of the wheel
        opening and leaves an identical sliver of bodywork uncovered — two
        triangles on the same base, so the flank measures the same size and the
        silhouette is quietly a different shape. Cutting at the crossing makes
        the dark band sit exactly between the arc and the line, everywhere.
        """
        rocker = shape.rocker_top_y_m
        # ⚠️ Snapped to the line before the sign test below, because that test
        # has no tolerance and `rocker_top_y_m` is a dial. Land it within a
        # rounding error of an arch sample and the straddle reads as genuine,
        # the cut lands at `across ~ 0`, and the stretch either side is a sliver
        # — measured down to **1.4e-30 m²**, and nothing catches it: `polygon`
        # refuses only an *exactly* zero cross product, so a 1e-30 normal
        # normalises to unit length and passes every winding and degeneracy
        # check the suite has.
        y0 = rocker if abs(y0 - rocker) < 1e-9 else y0
        y1 = rocker if abs(y1 - rocker) < 1e-9 else y1

        def band(
            za: float, zb: float, ya: float, yb: float, *, top: float, colour: Colour, suffix: str
        ) -> MeshData | None:
            """One quad of flank, floor `ya`->`yb` to a flat ceiling at `top`.

            Keyword-only past the coordinates for the reason `panels` is: four
            interchangeable floats in a row transpose silently into a valid,
            wrong quad, and a bare fifth one immediately after them is the same
            hazard again.
            """
            ring = [
                (x_out, ya, za),
                (x_out, top, za),
                (x_out, top, zb),
                (x_out, yb, zb),
            ]
            # Where the arc meets the band's own ceiling an edge collapses, and a
            # quad with two coincident corners has no normal — `polygon` says so
            # rather than emitting one, so the duplicates go before it sees them.
            # Below three corners there is no face left to draw at all.
            ring = [corner for i, corner in enumerate(ring) if corner != ring[i - 1]]
            if len(ring) < 3:
                return None
            return polygon_facing(ring, colour, (side, 0.0, 0.0), name=f"{name}_{tag}{suffix}")

        stretches = [(z0, z1, y0, y1)]
        if (y0 - rocker) * (y1 - rocker) < 0.0:
            across = (rocker - y0) / (y1 - y0)
            stretches = [
                (z0, z0 + across * (z1 - z0), y0, rocker),
                (z0 + across * (z1 - z0), z1, rocker, y1),
            ]

        faces: list[MeshData] = []
        for i, (za, zb, ya, yb) in enumerate(stretches):
            suffix = f"_{i}" if len(stretches) > 1 else ""
            # Each stretch now lies wholly on one side of the line, so the dark
            # band is present or absent rather than clipped.
            wanted = [(max(ya, rocker), max(yb, rocker), shape.belt_y_m, RED, suffix)]
            if min(ya, yb) < rocker:
                wanted.insert(0, (ya, yb, rocker, DARK, f"_rocker{suffix}"))
            for floor_a, floor_b, ceiling, colour, label in wanted:
                face = band(za, zb, floor_a, floor_b, top=ceiling, colour=colour, suffix=label)
                if face is not None:
                    faces.append(face)
        return faces

    parts: list[MeshData] = []
    # Solid stretches: nose to front arch, between the arches, rear arch to tail.
    spans = (
        (front_z, wheels_z[0] - opening_r),
        (wheels_z[0] + opening_r, wheels_z[1] - opening_r),
        (wheels_z[1] + opening_r, rear_z),
    )
    for i, (z0, z1) in enumerate(spans):
        parts.extend(panels(z0, z1, shape.sill_y_m, shape.sill_y_m, tag=f"span_{i}"))

    for w, wheel_z in enumerate(wheels_z):
        columns = np.linspace(wheel_z - opening_r, wheel_z + opening_r, shape.arch_segments + 1)
        for c in range(shape.arch_segments):
            z0, z1 = float(columns[c]), float(columns[c + 1])
            y0, y1 = arc_y(z0, wheel_z), arc_y(z1, wheel_z)
            # Bodywork above the arc.
            parts.extend(panels(z0, z1, y0, y1, tag=f"arch_{w}_{c}"))
            # The rim, turning inward into the well.
            parts.append(
                polygon_facing(
                    [(x_out, y0, z0), (x_out, y1, z1), (x_in, y1, z1), (x_in, y0, z0)],
                    DARK,
                    (0.0, float(np.sin((c + 0.5) / shape.arch_segments * np.pi)), 0.0),
                    name=f"{name}_rim_{w}_{c}",
                )
            )
        # Inner wall, so the well has a back to it.
        parts.append(
            polygon_facing(
                [
                    (x_in, shape.sill_y_m, wheel_z - opening_r),
                    (x_in, hub_y + opening_r, wheel_z - opening_r),
                    (x_in, hub_y + opening_r, wheel_z + opening_r),
                    (x_in, shape.sill_y_m, wheel_z + opening_r),
                ],
                DARK,
                (side, 0.0, 0.0),
                name=f"{name}_well_{w}",
            )
        )
    return parts


def _rear_door_z_m(chassis: Chassis, shape: Proportions) -> float:
    """Trailing edge of the rear door — the cabin's back, or the arch before it.

    ⚠️ **Refused rather than clamped when it lands ahead of the front door.** A
    wide enough opening, or a cabin pushed far enough back, drags the arch ahead
    of `cabin_mid_z_m` and puts the "rear" handle on the *front* door — measured
    at `well_clearance_m = 0.65`, the two boxes overlap by 135 mm and z-fight.
    Reachable rather than theoretical: `cabin_rear_z_m` moved 1.00 -> 1.25 to buy
    the backlight its rake, and rake is paid for out of cabin length, so it will
    move again. Clamping was tried and is worse — pushing the edge back far
    enough to separate the boxes carries the rear handle *onto the arch*, which
    trades a defect for a different one and reports neither. This is the same
    answer `greenhouse_profile` gives: a `Proportions` that cannot be built
    refuses, rather than building something quietly wrong.

    A function rather than a line inside `_flank_detail` because the test that
    checks handle placement was re-deriving this expression verbatim, which made
    it assert the formula against itself.
    """
    behind_the_arch = chassis.axle_z_m[1] - opening_radius_m(chassis, shape)
    rear_door_z = min(shape.cabin_rear_z_m, behind_the_arch)
    if rear_door_z - shape.cabin_mid_z_m <= 2.0 * shape.handle_half_length_m:
        raise ValueError(
            f"the rear door ends at {rear_door_z:+.3f}, which leaves no room for a handle "
            f"behind the front door's at {shape.cabin_mid_z_m:+.3f} — the wheel opening "
            f"({opening_radius_m(chassis, shape):.3f} m) has reached the middle of the cabin"
        )
    return rear_door_z


def _flank_detail(chassis: Chassis, shape: Proportions) -> list[MeshData]:
    """Door handles, and the running list of what the flank does *not* carry.

    They are proud of the surface rather than cut into it. Flat shading reads a
    raised edge and a recessed one identically, and a raised handle costs one box
    where a recess costs a re-tiled flank.

    ⚠️ Placed from the doors' **trailing edges**, which is why this needs the
    chassis. It used to be `cabin_mid_z_m` +/- a flat 0.42, and that survived
    only as long as the cabin did not change length: lengthening it to reach the
    rear axle carried the rear handle 130 mm out over the wheel opening, where a
    handle floating above a tyre is not a handle. The front door's trailing edge
    is the cabin's middle; the rear door's is its back — or the arch, whichever
    comes first, because the arch is where a real rear door stops.
    """
    parts: list[MeshData] = []
    hw = shape.half_width_m
    rear_door_z = _rear_door_z_m(chassis, shape)

    for tag, side in (("l", -1.0), ("r", 1.0)):
        # ⚠️ No modelled A/B/C pillars. They were straight boxes against a
        # greenhouse that tapers inward as it rises, so each one stood 0.14 m
        # proud of the glass at the roofline and read as a black stick growing
        # out of the roof. A box cannot sit flush on a tapering face at more
        # than one height, so this is structural rather than a number to tune:
        # the silver-over-glass reading comes from `loft`'s cant rail instead,
        # and painting the pillars is not something this model does at all.
        #
        # ⚠️ No rub strip. It was a dark bar running most of the flank's length
        # and standing 2-3 cm proud of it, put there because a review called the
        # flank flat — and at any distance the car is actually played at it read
        # as a black stripe painted down the side of a toy, not as trim.
        #
        # ⚠️ The sill skirt came back, on the user's call, and it is **not** that
        # bar. It is paint at the sill rather than a box at the belt, and it is
        # `panels`' business, not this function's — see the ⚠️ there for the two
        # forms that failed and why this one is neither. It is still on trial:
        # 60 mm at review distance is inside the band this file keeps calling
        # sub-pixel, and the argument for it — that a long high-contrast line
        # survives where an isolated small shape does not — is an argument and
        # not a measurement. `rocker_top_y_m = sill_y_m` switches it off.
        #
        # ⚠️ No modelled door shut lines. They were 1 cm wide, 52 cm tall and
        # stood 1 cm PROUD of the flank — so instead of the recessed shadow a
        # real door gap is, they were four raised black ribs on a red body, and
        # the review read them as sticks. Flat shading cannot express a groove:
        # a recess and a rib light identically, and only the silhouette differs.
        # A panel line is a texture, and that is where this one goes.
        for door, trailing_z in (("front", shape.cabin_mid_z_m), ("rear", rear_door_z)):
            parts.append(
                box_at(
                    (side * (hw + 0.02), 0.30, trailing_z - shape.handle_inset_m),
                    (0.02, 0.025, shape.handle_half_length_m),
                    SILVER,
                    name=f"handle_{door}_{tag}",
                )
            )

    # ⚠️ No grille slats. Three silver blocks sat in the middle of the dark
    # grille, and at the size the nose is ever drawn they read as three white
    # squares floating on the front of the car rather than as chrome. The grille
    # is one flat dark rectangle now, which is what every other flat-shaded
    # surface in the city is.
    return parts


def build_taxi(chassis: Chassis, shape: Proportions) -> list[MeshData]:
    """Body and tyre, in that order — one material each.

    Two meshes, where there were three. The third was a textured decal sheet
    carrying the roof lettering, the plate characters and the 4 SEATS badge,
    and its own docstring called it "the exception, taken deliberately" against
    `ART_DESIGN.md`'s 1-2 materials per vehicle. With the characters gone there
    is nothing on it a flat-coloured quad cannot say, so the exception is
    closed and the car is untextured all the way through — like the city.
    """
    wheel = _wheel(
        chassis.wheel_radius_m, shape.wheel_width_m, shape.wheel_segments, name="taxi_tyre"
    )
    return [taxi_body(chassis, shape), wheel]


def write_taxi(
    out_dir: Path, chassis: Chassis, shape: Proportions
) -> list[tuple[Path, int, MeshData]]:
    """Write one `.glb` per mesh and return what went where."""
    body, wheel = build_taxi(chassis, shape)
    written = []
    for filename, mesh in ((BODY_FILE, body), (WHEEL_FILE, wheel)):
        path = out_dir / filename
        written.append((path, write_glb(path, [mesh]), mesh))
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output directory")
    parser.add_argument("--report", action="store_true", help="print the geometry it produced")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    chassis = Chassis()
    shape = Proportions()

    written = write_taxi(args.out_dir, chassis, shape)
    for path, size, mesh in written:
        LOG.info("%s — %d bytes, %d triangles", path, size, mesh.triangle_count)
    if args.report:
        for _, _, mesh in written:
            (low, high) = mesh.aabb()
            LOG.info(
                "  %-12s x %+.2f..%+.2f  y %+.2f..%+.2f  z %+.2f..%+.2f",
                mesh.name,
                low[0],
                high[0],
                low[1],
                high[1],
                low[2],
                high[2],
            )
        body, wheel = (mesh for _, _, mesh in written)
        LOG.info(
            "  as the scene builds it: %d body + 4 x %d tyre = %d triangles",
            body.triangle_count,
            wheel.triangle_count,
            body.triangle_count + 4 * wheel.triangle_count,
        )
        LOG.info("  ground plane at y %+.2f, hub at y %+.2f", chassis.ground_y_m, chassis.hub_y_m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
