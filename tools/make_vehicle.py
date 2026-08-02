"""Generate the roster's low-poly toy vehicles (`P3-11`).

    python tools/make_vehicle.py
    python tools/make_vehicle.py --out-dir /tmp/vehicles --report

`ART_DESIGN.md` specifies the vehicles as *proportions* — "shortened wheelbase,
tall greenhouse, exaggerated wheel arches" — rather than as detail. Proportions
are three numbers, so they are worth tuning in a diff instead of guessing in a
mesh, and the roster is six vehicles that differ mostly by those numbers. Hence
a generator rather than a modelled asset.

⚠️ **The chassis is an input, not an output.** `P0-5` tuned handling against the
`WheelMount` markers in `game/scenes/vehicle/taxi.tscn`, and `P0-5a` chose a
custom raycast controller precisely so those points are authored rather than
inferred from a mesh. The physics never reads this file's output, so a model
built to a different wheelbase would look correct and silently drive to the old
tuning. `Chassis` below therefore mirrors the scene, and
`etl/tests/test_make_vehicle.py` fails if the two ever disagree.

Output goes to `game/assets/authored/vehicles/`, which is **committed** — these
are hand-authored assets under CC BY-SA 4.0, not build output. See LICENSING.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.gltf import MeshData, Texture, normalise, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from vehicle_decals import MIME, Patch, build_sheet  # noqa: E402

LOG = logging.getLogger("make_vehicle")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "vehicles"

# Body, tyre and decals ship as separate files rather than as meshes in one.
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
DECAL_FILE = "taxi_decal.glb"

# How far a decal stands off the face it is stuck to. Small enough not to
# read as floating, large enough that no view resolves it as z-fighting.
DECAL_CLEARANCE_M = 0.004

# RGB, 0-255. `ART_DESIGN.md` asks for 3-5 flat colours per vehicle; these are
# the five. Red body with a silver roof is called non-negotiable there — it is
# the HK Island urban taxi, and a green or blue one is a different territory.
RED = (198, 32, 40)
SILVER = (226, 228, 230)
DARK = (30, 32, 36)
GLASS = (18, 19, 22)
LAMP = (242, 236, 205)
# ⚠️ A sixth colour, where `ART_DESIGN.md` says 3-5 per vehicle. It buys the
# indicator in the tail-lamp cluster, which is three lenses stacked — amber
# over white over red — and that stack is a specific identifying feature of the
# car's rear. Two colours cannot express three lenses. Flagged rather than
# quietly taken: see docs/PROGRESS.md, P3-11.
AMBER = (226, 138, 32)

Colour = tuple[int, int, int]
Point = Sequence[float]


@dataclass(frozen=True)
class Chassis:
    """The hardpoints, mirrored from `taxi.tscn` and `handling.tres`.

    Nothing here may be changed to suit the model. If the car should sit
    differently, the scene and the handling profile move first and this follows
    — in that order, with the drive re-reviewed.
    """

    wheelbase_m: float = 2.60  # markers at z = +/-1.30
    track_m: float = 1.60  # markers at x = +/-0.80
    wheel_radius_m: float = 0.35  # handling.tres, wheel_radius_m
    suspension_rest_m: float = 0.35  # handling.tres, hub sits this far below the marker

    @property
    def hub_y_m(self) -> float:
        """Wheel centre at rest. Markers are the top of the spring, not the hub."""
        return -self.suspension_rest_m

    @property
    def ground_y_m(self) -> float:
        return self.hub_y_m - self.wheel_radius_m


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
    cabin_rear_z_m: float = 1.00
    roof_inset_m: float = 0.13
    roof_front_taper_m: float = 0.30
    roof_rear_taper_m: float = 0.16
    # The roof sign is most of what says "taxi" at a distance. Wider across
    # the car than along it, because the lettering faces fore and aft — which is
    # where the real sign carries it, confirmed against reference art. It also
    # happens to be the only face the chase camera ever sees, so accuracy and
    # readability want the same thing here.
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
    # bevel is one more ring, not a curve — see `_loft`.
    bevel_m: float = 0.06
    # The silver band between the glass and the roof. The reference art shows
    # roof paint coming down over the pillars; without this the roof reads as a
    # pale lid laid on a red box, which is the note the first review returned.
    cant_rail_m: float = 0.10
    # Dark rub strip along the doors, at the height a real one sits.
    rub_strip_y_m: float = 0.08
    rub_strip_half_m: float = 0.035

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
    def sign_z_m(self) -> float:
        """Centre of the roof sign, set back slightly from the cabin's middle.

        A property because the sign's geometry and the TAXI decal stuck to it
        both need it, and they were deriving it separately — including the same
        magic setback. Nothing would have failed if they drifted; the lettering
        would simply have slid off the side of the sign.
        """
        return self.cabin_mid_z_m - 0.06


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------


def _polygon(corners: Sequence[Point], colour: Colour, *, name: str) -> MeshData:
    """One flat convex face, wound counter-clockwise seen from outside.

    Vertices are never shared between faces. That is what makes the whole model
    flat-shaded without smoothing groups: every triangle carries its own face
    normal, so an edge stays an edge and a vertex colour stays crisp across it.

    Triangles and quads go through the same call because a wheel needs both, and
    the earlier version faked the triangles as quads with two coincident
    corners. That is not a harmless trick: the face normal comes from
    `corners[1] - corners[0]` crossed with `corners[-1] - corners[0]`, and
    duplicating `corners[0]` makes the second of those zero — so every cap on
    the first wheel got a zero normal and a degenerate triangle to go with it.
    """
    positions = np.asarray(corners, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[0] < 3 or positions.shape[1] != 3:
        raise ValueError(f"'{name}': need at least three xyz corners, got {positions.shape}")

    face = normalise(np.cross(positions[1] - positions[0], positions[-1] - positions[0])[None, :])
    if not np.isfinite(face).all() or np.allclose(face, 0.0):
        raise ValueError(f"'{name}': corners are collinear or coincident, so it has no normal")

    fan = [(0, i, i + 1) for i in range(1, len(positions) - 1)]
    return MeshData(
        name=name,
        positions=positions,
        normals=np.repeat(face, len(positions), axis=0).astype(np.float32),
        triangles=np.array(fan, dtype=np.uint32),
        colours=np.repeat(np.array([[*colour, 255]], dtype=np.uint8), len(positions), axis=0),
    )


def _polygon_facing(
    corners: Sequence[Point], colour: Colour, outward: Sequence[float], *, name: str
) -> MeshData:
    """A face wound so its normal points along `outward`.

    Curved runs — the arch band and its rim — are generated from angles rather
    than written out corner by corner, and which way round that comes out flips
    with the side of the car and with the direction of travel around the arc.
    Stating the direction the face should look and letting the code reverse
    itself is the difference between one rule and four hand-checked cases; the
    wheel proved the alternative by rendering itself inside-out.
    """
    ring = list(corners)
    normal = np.cross(
        np.subtract(ring[1], ring[0], dtype=np.float64),
        np.subtract(ring[-1], ring[0], dtype=np.float64),
    )
    if float(np.dot(normal, np.asarray(outward, dtype=np.float64))) < 0.0:
        ring.reverse()
    return _polygon(ring, colour, name=name)


def _hexahedron(
    bottom: Sequence[Point],
    top: Sequence[Point],
    colour: Colour,
    *,
    name: str,
) -> MeshData:
    """Six quads over eight corners, so a taper costs no more than a box.

    Corners run anticlockwise seen from above: (-x,-z), (+x,-z), (+x,+z),
    (-x,+z). Taking bottom and top as separate rings is what lets a fixture
    narrow towards its top without becoming two parts.

    One colour for the whole solid. It used to take a colour per named face,
    which is what painted the old boxed body — a dark glasshouse under a silver
    roof. `_loft` does that job now, band by band, and every caller left here is
    a lamp or a bumper that wants one flat colour.
    """
    b0, b1, b2, b3 = bottom
    t0, t1, t2, t3 = top
    quads = [
        _polygon(corners, colour, name=f"{name}_{i}")
        for i, corners in enumerate(
            (
                (b0, b1, b2, b3),
                (t0, t3, t2, t1),
                (b1, b0, t0, t1),
                (b3, b2, t2, t3),
                (b0, b3, t3, t0),
                (b2, b1, t1, t2),
            )
        )
    ]
    return merge(quads, name=name)


def _ring(
    y: float, half_w: float, z_front: float, z_back: float, cut: float = 0.0
) -> tuple[Point, ...]:
    """One horizontal section, in order around the body.

    With `cut` the four square corners become eight, turning each vertical edge
    into three short facets instead of one 90° turn. That is what "rounded"
    means here: the faces stay flat and every edge stays crisp, so the car still
    belongs in a flat-shaded city — there are simply more of them. Smooth
    shading would be the thing that broke the art direction; a chamfer is not.
    """
    if cut <= 0.0:
        return (
            (-half_w, y, z_front),
            (half_w, y, z_front),
            (half_w, y, z_back),
            (-half_w, y, z_back),
        )
    cut = min(cut, half_w * 0.9, abs(z_back - z_front) * 0.45)
    return (
        (-half_w + cut, y, z_front),
        (half_w - cut, y, z_front),
        (half_w, y, z_front + cut),
        (half_w, y, z_back - cut),
        (half_w - cut, y, z_back),
        (-half_w + cut, y, z_back),
        (-half_w, y, z_back - cut),
        (-half_w, y, z_front + cut),
    )


def _flank_edges(corners: int) -> tuple[int, int]:
    """Which two edges of a ring are the long flanks.

    Derived rather than pinned. They were hardcoded as `(2, 6)`, correct only
    for the eight-corner ring — and `corner_cut_m = 0` is an offered setting
    that returns four corners, where edge 2 is the *boot face*. Skipping it left
    a hole through the back of the car and drew both flanks twice, silently, for
    fifty fewer triangles and no error.
    """
    return (corners // 4, 3 * corners // 4)


def _loft(
    rings: Sequence[Sequence[Point]],
    band_colours: Sequence[Colour],
    *,
    bottom: Colour,
    top: Colour,
    skip_edges: Sequence[int] = (),
    name: str,
) -> MeshData:
    """A profile lofted through stacked rings — the shape a car body is.

    Bevels at this scale are not rounded edges, they are *one more ring* a few
    centimetres in and up. Stacking three or four rings gives a chamfered sill,
    a tucked roof and a raked pillar for four quads apiece, and it keeps every
    face flat — which is the whole point, since the city it drives through is
    flat-shaded and a smooth-shaded car would sit outside its own art direction.
    """
    if len(rings) < 2:
        raise ValueError(f"'{name}': a loft needs at least two rings")
    if len(band_colours) != len(rings) - 1:
        raise ValueError(
            f"'{name}': {len(rings)} rings need {len(rings) - 1} band colours, "
            f"got {len(band_colours)}"
        )

    corners = len(rings[0])
    if any(len(ring) != corners for ring in rings):
        raise ValueError(f"'{name}': every ring needs the same number of corners")
    out_of_range = [edge for edge in skip_edges if not 0 <= edge < corners]
    if out_of_range:
        raise ValueError(f"'{name}': no edge {out_of_range} on a {corners}-corner ring")

    parts: list[MeshData] = []
    centre = np.mean(np.asarray(rings[0], dtype=np.float64), axis=0)
    for i, colour in enumerate(band_colours):
        lower, upper = rings[i], rings[i + 1]
        for edge in range(corners):
            if edge in skip_edges:
                continue
            nxt = (edge + 1) % corners
            outward = np.mean(
                [lower[edge], lower[nxt], upper[edge], upper[nxt]], axis=0
            ) - np.asarray([centre[0], 0.0, centre[2]])
            parts.append(
                _polygon_facing(
                    [lower[nxt], lower[edge], upper[edge], upper[nxt]],
                    colour,
                    (outward[0], 0.0, outward[2]),
                    name=f"{name}_edge{edge}_{i}",
                )
            )

    parts.append(_polygon_facing(rings[0], bottom, (0.0, -1.0, 0.0), name=f"{name}_bottom"))
    parts.append(_polygon_facing(rings[-1], top, (0.0, 1.0, 0.0), name=f"{name}_top"))
    return merge(parts, name=name)


def _box(low: Point, high: Point, colour: Colour, *, name: str) -> MeshData:
    """An axis-aligned box — the untapered case of `_hexahedron`."""
    (lx, ly, lz), (hx, hy, hz) = low, high

    def ring(y: float) -> tuple[Point, ...]:
        return ((lx, y, lz), (hx, y, lz), (hx, y, hz), (lx, y, hz))

    return _hexahedron(ring(ly), ring(hy), colour, name=name)


def _box_at(centre: Point, half: Point, colour: Colour, *, name: str) -> MeshData:
    """A box from its centre and half-extents.

    Fixtures that come in mirrored pairs — lamps, mirrors, arches — are placed
    by centre, because writing them as opposing corners means every one of them
    needs its own `min`/`max` reasoning and the left of the pair reads
    differently from the right.
    """
    low = tuple(c - h for c, h in zip(centre, half, strict=True))
    high = tuple(c + h for c, h in zip(centre, half, strict=True))
    return _box(low, high, colour, name=name)


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
            _polygon(
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
            parts.append(_polygon_facing(wall, DARK, (face_x, 0.0, 0.0), name=f"{name}_wall_{i}"))
            parts.append(_polygon_facing(hub, SILVER, (face_x, 0.0, 0.0), name=f"{name}_hub_{i}"))
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
    tuck = shape.bevel_m
    cut = shape.corner_cut_m
    # (z inset from each end, y, corner cut) for the four rings of the lower body.
    profile = (
        (tuck * 2.4, shape.sill_y_m, cut * 0.6),
        (tuck, shape.sill_y_m + tuck, cut * 0.85),
        (0.0, shape.belt_y_m - tuck * 1.4, cut),
        (tuck * 0.8, shape.belt_y_m, cut * 0.85),
    )
    lower_rings = [
        _ring(y, hw, front_z + inset_z, rear_z - inset_z, ring_cut)
        for inset_z, y, ring_cut in profile
    ]
    parts.append(
        _loft(
            lower_rings,
            [DARK, RED, RED],
            bottom=DARK,
            top=RED,
            # The two long flanks are `_flank`'s, because a loft band cannot
            # carry the wheel opening cut through it.
            skip_edges=_flank_edges(len(lower_rings[0])),
            name="lower",
        )
    )

    # Greenhouse: belt to roof through a glass band and a silver cant rail, so
    # the roof colour comes down over the pillars the way the real paint does
    # rather than sitting on top like a lid.
    inset = shape.roof_inset_m
    glass_top = shape.roof_y_m - shape.cant_rail_m
    cabin_hw = hw - tuck
    parts.append(
        _loft(
            [
                _ring(
                    shape.belt_y_m,
                    cabin_hw,
                    shape.cabin_front_z_m,
                    shape.cabin_rear_z_m,
                    cut * 0.8,
                ),
                _ring(
                    glass_top,
                    cabin_hw - inset * 0.7,
                    shape.cabin_front_z_m + shape.roof_front_taper_m * 0.8,
                    shape.cabin_rear_z_m - shape.roof_rear_taper_m * 0.8,
                    cut * 0.7,
                ),
                _ring(
                    shape.roof_y_m,
                    cabin_hw - inset,
                    shape.cabin_front_z_m + shape.roof_front_taper_m,
                    shape.cabin_rear_z_m - shape.roof_rear_taper_m,
                    cut * 0.55,
                ),
            ],
            [GLASS, SILVER],
            bottom=GLASS,
            top=SILVER,
            name="greenhouse",
        )
    )

    # Roof sign, raked rather than a plain cuboid: narrower and shorter at the
    # top, which is the profile the real fitting has and what stops it reading
    # as a white brick. Its two long faces carry the TAXI decal.
    sign_z = shape.sign_z_m
    parts.append(
        _loft(
            [
                _ring(
                    shape.roof_y_m,
                    shape.sign_half_width_m,
                    sign_z - shape.sign_half_length_m,
                    sign_z + shape.sign_half_length_m,
                ),
                # ⚠️ Raked across its width only, never its depth. The decals
                # sit on the fore and aft faces, and those stay vertical planes
                # at constant z only while the rake is in x. Taper the depth and
                # the faces slope, no flat quad can lie on them, and the
                # lettering ends up buried inside the solid — which is exactly
                # what happened when it was on the sides.
                _ring(
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

    # Bumpers, standing proud of the body at each end.
    parts.append(
        _box_at((0.0, -0.03, front_z + 0.02), (hw - 0.008, 0.09, 0.08), DARK, name="front_bumper")
    )
    parts.append(
        _box_at((0.0, -0.03, rear_z - 0.02), (hw - 0.008, 0.09, 0.08), DARK, name="rear_bumper")
    )
    parts.append(_box_at((0.0, 0.11, front_z + 0.01), (0.42, 0.09, 0.03), DARK, name="grille"))

    for tag, side in (("l", -1.0), ("r", 1.0)):
        # The front cluster is three lamps, not one pale block: the main beam
        # inboard, an amber indicator outboard of it, and a small white lamp low
        # in the bumper. The amber is what stops the nose reading as two blank
        # rectangles, and it pairs with the amber at the top of the tail cluster.
        parts.append(
            _box_at(
                (side * 0.58, 0.19, front_z + 0.015),
                (0.15, 0.085, 0.035),
                LAMP,
                name=f"headlamp_{tag}",
            )
        )
        parts.append(
            _box_at(
                (side * 0.80, 0.19, front_z + 0.02),
                (0.065, 0.085, 0.035),
                AMBER,
                name=f"indicator_{tag}",
            )
        )
        parts.append(
            _box_at(
                (side * 0.66, -0.04, front_z - 0.05),
                (0.105, 0.03, 0.03),
                LAMP,
                name=f"foglamp_{tag}",
            )
        )
        # Tail lamps upright, the way the Crown Comfort's cluster stands at the
        # corner of the boot — its proportion is most of what identifies the
        # rear at a glance.
        #
        # ⚠️ The lens is RED, and the dark bezel is what makes that possible. A
        # red lens straight onto red bodywork disappears, which is why an
        # earlier pass made the lens cream — and a white tail lamp is simply
        # wrong. Bezel first, then the correct colour on top of it.
        parts.append(
            _box_at(
                (side * (hw - 0.13), 0.19, rear_z - 0.03),
                (0.105, 0.165, 0.035),
                DARK,
                name=f"taillamp_bezel_{tag}",
            )
        )
        # Three lenses stacked in the cluster, top to bottom: amber indicator,
        # white reverse, red tail and brake. Ordering is not decorative — it is
        # what the car actually carries, and getting it upside down would be as
        # wrong to a local eye as the wrong badge.
        for lens, (offset, colour) in enumerate(
            ((0.073, AMBER), (0.0, LAMP), (-0.073, RED)),
        ):
            parts.append(
                _box_at(
                    (side * (hw - 0.13), 0.21 + offset, rear_z - 0.01),
                    (0.085, 0.034, 0.035),
                    colour,
                    name=f"taillamp_{tag}_{lens}",
                )
            )
        # Wing mirrors: wider than they are deep. The earlier proportions were
        # 0.12 x 0.09 x 0.15, longer front-to-back than across, which is a stalk
        # rather than a mirror — part of what the review read as strange.
        parts.append(
            _box_at(
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
    return merge(parts, name="taxi_body")


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
    """
    x_out = side * shape.half_width_m
    x_in = side * (shape.half_width_m - shape.well_depth_m)
    opening_r = chassis.wheel_radius_m + shape.well_clearance_m
    hub_y = chassis.hub_y_m
    wheels_z = (-chassis.wheelbase_m / 2.0, chassis.wheelbase_m / 2.0)
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

    parts: list[MeshData] = []
    # Solid stretches: nose to front arch, between the arches, rear arch to tail.
    spans = (
        (front_z, wheels_z[0] - opening_r),
        (wheels_z[0] + opening_r, wheels_z[1] - opening_r),
        (wheels_z[1] + opening_r, rear_z),
    )
    for i, (z0, z1) in enumerate(spans):
        parts.append(
            _polygon_facing(
                [
                    (x_out, shape.sill_y_m, z0),
                    (x_out, shape.belt_y_m, z0),
                    (x_out, shape.belt_y_m, z1),
                    (x_out, shape.sill_y_m, z1),
                ],
                RED,
                (side, 0.0, 0.0),
                name=f"{name}_span_{i}",
            )
        )

    for w, wheel_z in enumerate(wheels_z):
        columns = np.linspace(wheel_z - opening_r, wheel_z + opening_r, shape.arch_segments + 1)
        for c in range(shape.arch_segments):
            z0, z1 = float(columns[c]), float(columns[c + 1])
            y0, y1 = arc_y(z0, wheel_z), arc_y(z1, wheel_z)
            # Bodywork above the arc.
            parts.append(
                _polygon_facing(
                    [
                        (x_out, y0, z0),
                        (x_out, shape.belt_y_m, z0),
                        (x_out, shape.belt_y_m, z1),
                        (x_out, y1, z1),
                    ],
                    RED,
                    (side, 0.0, 0.0),
                    name=f"{name}_arch_{w}_{c}",
                )
            )
            # The rim, turning inward into the well.
            parts.append(
                _polygon_facing(
                    [(x_out, y0, z0), (x_out, y1, z1), (x_in, y1, z1), (x_in, y0, z0)],
                    DARK,
                    (0.0, float(np.sin((c + 0.5) / shape.arch_segments * np.pi)), 0.0),
                    name=f"{name}_rim_{w}_{c}",
                )
            )
        # Inner wall, so the well has a back to it.
        parts.append(
            _polygon_facing(
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


def _flank_detail(chassis: Chassis, shape: Proportions) -> list[MeshData]:
    """Handles, rub strips and grille slats.

    All of it is proud of the surface rather than cut into it. Flat shading
    reads a raised edge and a recessed one identically, and a raised strip costs
    one box where a recess costs a re-tiled flank.
    """
    parts: list[MeshData] = []
    hw = shape.half_width_m
    front_z = shape.front_z_m
    cabin_mid_z = shape.cabin_mid_z_m

    for tag, side in (("l", -1.0), ("r", 1.0)):
        # ⚠️ No modelled A/B/C pillars. They were straight boxes against a
        # greenhouse that tapers inward as it rises, so each one stood 0.14 m
        # proud of the glass at the roofline and read as a black stick growing
        # out of the roof. A box cannot sit flush on a tapering face at more
        # than one height, so this is structural rather than a number to tune:
        # the silver-over-glass reading comes from `_loft`'s cant rail instead,
        # and painting the pillars belongs in the decal pass, not in geometry.
        #
        # Rub strip along the doors. Thin, but it is the one horizontal line
        # breaking a very tall red flank, and the review called the flank flat.
        parts.append(
            _box_at(
                (side * (hw + 0.01), shape.rub_strip_y_m, cabin_mid_z - 0.05),
                (0.022, shape.rub_strip_half_m, shape.length_m * 0.30),
                DARK,
                name=f"rub_strip_{tag}",
            )
        )
        # ⚠️ No modelled door shut lines. They were 1 cm wide, 52 cm tall and
        # stood 1 cm PROUD of the flank — so instead of the recessed shadow a
        # real door gap is, they were four raised black ribs on a red body, and
        # the review read them as sticks. Flat shading cannot express a groove:
        # a recess and a rib light identically, and only the silhouette differs.
        # A panel line is a texture, and that is where this one goes.
        for door, z in (("front", cabin_mid_z - 0.42), ("rear", cabin_mid_z + 0.42)):
            parts.append(
                _box_at(
                    (side * (hw + 0.02), 0.30, z + 0.16),
                    (0.02, 0.025, 0.075),
                    SILVER,
                    name=f"handle_{door}_{tag}",
                )
            )
        # Sill skirt between the arches, which grounds the body visually.
        parts.append(
            _box_at(
                (side * (hw - 0.01), shape.sill_y_m + 0.05, 0.0),
                (0.03, 0.05, chassis.wheelbase_m / 2.0 - chassis.wheel_radius_m - 0.06),
                DARK,
                name=f"sill_{tag}",
            )
        )

    for i, offset in enumerate((-0.13, 0.0, 0.13)):
        parts.append(
            _box_at(
                (offset, 0.11, front_z + 0.005),
                (0.05, 0.055, 0.03),
                SILVER,
                name=f"grille_slat_{i}",
            )
        )
    return parts


def _decal(
    centre: Point,
    right: Point,
    up: Point,
    half_w: float,
    half_h: float,
    patch: Patch,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One textured quad as (positions, normal, uvs).

    Taken as centre plus a right and an up vector rather than four corners,
    because a decal is a rectangle stuck to a surface and its *orientation* is
    the thing that goes wrong — text upside down or mirrored reads as a bug
    instantly, and corner lists hide which way is up.
    """
    c = np.asarray(centre, dtype=np.float64)
    r = np.asarray(right, dtype=np.float64) * half_w
    u = np.asarray(up, dtype=np.float64) * half_h
    positions = np.array([c - r - u, c + r - u, c + r + u, c - r + u])
    normal = normalise(np.cross(r, u)[None, :])[0]
    u0, v0, u1, v1 = patch.uv()
    uvs = np.array([[u0, v1], [u1, v1], [u1, v0], [u0, v0]], dtype=np.float32)
    return positions, normal, uvs


def taxi_decals(chassis: Chassis, shape: Proportions) -> MeshData:
    """Plates, roof lettering and the 4 SEATS badge, on one textured sheet.

    A third mesh, so a third material — `ART_DESIGN.md` budgets 1-2 per vehicle
    and this is the exception, taken deliberately. It also sidesteps
    `pipeline/mesh.py`'s refusal to merge textured meshes: nothing here merges
    with the body, so the body stays untextured and flat-shaded exactly as the
    city around it is.
    """
    png, patches = build_sheet(sign_face=LAMP, bumper_face=DARK)
    front_z, rear_z = shape.front_z_m, shape.rear_z_m
    sign_z = shape.sign_z_m
    sign_mid_y = shape.roof_y_m + shape.sign_height_m / 2.0
    sign_face_z = shape.sign_half_length_m + DECAL_CLEARANCE_M
    # On the car's right. A photographer facing the rear sees that on their
    # left; the chase camera faces the way the car does, so it sees it right.
    badge_x = 0.34

    faces = [
        # Roof sign, fore and aft — where the real one carries its lettering,
        # and the only face the chase camera sees. The long sides are plain.
        (
            (0.0, sign_mid_y, sign_z - sign_face_z),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            0.21,
            0.048,
            "taxi_sign",
        ),
        (
            (0.0, sign_mid_y, sign_z + sign_face_z),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            0.21,
            0.048,
            "taxi_sign",
        ),
        # Plates: white at the front, yellow at the rear, per the HK standard.
        (
            (0.0, -0.03, front_z - 0.07),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            0.17,
            0.055,
            "plate_front",
        ),
        ((0.0, 0.16, rear_z + 0.015), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 0.17, 0.055, "plate_rear"),
        # 4 SEATS on both bumpers.
        (
            (badge_x, -0.03, front_z - 0.07),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            0.125,
            0.072,
            "seats4",
        ),
        (
            (badge_x, -0.03, rear_z + 0.075),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            0.125,
            0.072,
            "seats4",
        ),
    ]

    positions, normals, uvs, triangles = [], [], [], []
    for i, (centre, right, up, hw, hh, key) in enumerate(faces):
        quad, normal, quad_uvs = _decal(centre, right, up, hw, hh, patches[key])
        positions.append(quad)
        normals.append(np.repeat(normal[None, :], 4, axis=0))
        uvs.append(quad_uvs)
        base = i * 4
        triangles.append(np.array([[base, base + 1, base + 2], [base, base + 2, base + 3]]))

    return MeshData(
        name="taxi_decal",
        positions=np.concatenate(positions),
        normals=np.concatenate(normals).astype(np.float32),
        triangles=np.concatenate(triangles).astype(np.uint32),
        uvs=np.concatenate(uvs),
        texture=Texture(data=png, mime_type=MIME),
    )


def build_taxi(chassis: Chassis, shape: Proportions) -> list[MeshData]:
    """Body, tyre and decal sheet, in that order — one material each."""
    wheel = _wheel(
        chassis.wheel_radius_m, shape.wheel_width_m, shape.wheel_segments, name="taxi_tyre"
    )
    return [taxi_body(chassis, shape), wheel, taxi_decals(chassis, shape)]


def write_taxi(
    out_dir: Path, chassis: Chassis, shape: Proportions
) -> list[tuple[Path, int, MeshData]]:
    """Write one `.glb` per mesh and return what went where."""
    body, wheel, decal = build_taxi(chassis, shape)
    written = []
    for filename, mesh in ((BODY_FILE, body), (WHEEL_FILE, wheel), (DECAL_FILE, decal)):
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
        body, wheel, decal = (mesh for _, _, mesh in written)
        LOG.info(
            "  as the scene builds it: %d body + 4 x %d tyre + %d decal = %d triangles",
            body.triangle_count,
            wheel.triangle_count,
            decal.triangle_count,
            body.triangle_count + 4 * wheel.triangle_count + decal.triangle_count,
        )
        LOG.info("  ground plane at y %+.2f, hub at y %+.2f", chassis.ground_y_m, chassis.hub_y_m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
