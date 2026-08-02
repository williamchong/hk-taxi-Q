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

from pipeline.gltf import MeshData, normalise, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402

LOG = logging.getLogger("make_vehicle")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "vehicles"

# Body and wheel ship as separate files rather than as two meshes in one.
# Godot imports a `.glb` as a PackedScene, so a single file would have to be
# instanced whole — and the wheel inside it would arrive at the body's origin,
# once, when the scene needs four of them at hardpoints it already owns.
# Referencing the sub-resource instead (`taxi.glb::ArrayMesh_xxxx`) means
# hand-writing IDs the importer generates, which no longer resolve the first
# time anything upstream changes. Two files keeps the scene the authority on
# *where* a wheel is and the mesh the authority on what it looks like.
BODY_FILE = "taxi_body.glb"
WHEEL_FILE = "taxi_wheel.glb"

# RGB, 0-255. `ART_DESIGN.md` asks for 3-5 flat colours per vehicle; these are
# the five. Red body with a silver roof is called non-negotiable there — it is
# the HK Island urban taxi, and a green or blue one is a different territory.
RED = (196, 30, 38)
SILVER = (198, 201, 205)
DARK = (34, 36, 40)
GLASS = (48, 58, 68)
LAMP = (240, 232, 198)

Colour = tuple[int, int, int]
Point = Sequence[float]

# The six faces of a box or a tapered box, in the order `_hexahedron` builds them.
_FACES = ("bottom", "top", "front", "back", "left", "right")


def _faces(default: Colour, **overrides: Colour) -> dict[str, Colour]:
    """One colour on every face, then the exceptions.

    Written out longhand, a six-key dict hides the one entry that differs among
    five that do not — and the exception is the whole reason the call exists.
    """
    unknown = set(overrides) - set(_FACES)
    if unknown:
        raise ValueError(f"no such face: {sorted(unknown)}")
    return dict.fromkeys(_FACES, default) | overrides


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
    cutting its overhangs and raising its greenhouse. The real car is 4.69 m
    long on a 2.68 m wheelbase; this is 4.00 m on the 2.60 m the scene already
    has, which is most of the toy proportion for free.
    """

    length_m: float = 4.00
    # ⚠️ Narrower than half the track, so the wheels stand proud of the body.
    # At 0.86 they did not: the wheels reach x 0.90 and the arch lip 0.91, so
    # every one of them was sealed inside the bodywork and the first render came
    # back as a car with no wheels at all. A real Crown Comfort hides its wheels
    # in wells cut into a wider body; cutting wells costs a segmented flank,
    # and proud wheels are the toy read this art direction asks for anyway.
    half_width_m: float = 0.76
    sill_y_m: float = -0.20
    belt_y_m: float = 0.38
    roof_y_m: float = 0.86
    # Greenhouse, as fractions of the body: where the cabin starts and ends
    # along z, and how far the roof pulls in from the belt line.
    cabin_front_z_m: float = -0.78
    cabin_rear_z_m: float = 1.02
    roof_inset_m: float = 0.13
    roof_front_taper_m: float = 0.30
    roof_rear_taper_m: float = 0.16
    # The roof sign is most of what says "taxi" at a distance.
    sign_half_length_m: float = 0.21
    sign_half_width_m: float = 0.15
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
    arch_flare_m: float = 0.05


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
    colours: dict[str, Colour],
    *,
    name: str,
) -> MeshData:
    """Six quads over eight corners, so a taper costs no more than a box.

    Corners run anticlockwise seen from above: (-x,-z), (+x,-z), (+x,+z),
    (-x,+z). Taking bottom and top as separate rings is what lets the roof pull
    in from the belt line, which is the whole shape of a car's greenhouse.

    `colours` keys the six faces by name, so one call paints a dark glasshouse
    with a silver roof without splitting the solid into parts.
    """
    b0, b1, b2, b3 = bottom
    t0, t1, t2, t3 = top
    corners_by_face = dict(
        zip(
            _FACES,
            (
                (b0, b1, b2, b3),
                (t0, t3, t2, t1),
                (b1, b0, t0, t1),
                (b3, b2, t2, t3),
                (b0, b3, t3, t0),
                (b2, b1, t1, t2),
            ),
            strict=True,
        )
    )
    missing = set(_FACES) - set(colours)
    if missing:
        raise ValueError(f"'{name}': no colour for {sorted(missing)}")
    quads = [
        _polygon(corners, colours[face], name=f"{name}_{face}")
        for face, corners in corners_by_face.items()
    ]
    return merge(quads, name=name)


def _box(low: Point, high: Point, colour: Colour | dict[str, Colour], *, name: str) -> MeshData:
    """An axis-aligned box — the untapered case of `_hexahedron`."""
    (lx, ly, lz), (hx, hy, hz) = low, high

    def ring(y: float) -> tuple[Point, ...]:
        return ((lx, y, lz), (hx, y, lz), (hx, y, hz), (lx, y, hz))

    faces = colour if isinstance(colour, dict) else dict.fromkeys(_FACES, colour)
    return _hexahedron(ring(ly), ring(hy), faces, name=name)


def _box_at(
    centre: Point, half: Point, colour: Colour | dict[str, Colour], *, name: str
) -> MeshData:
    """A box from its centre and half-extents.

    Fixtures that come in mirrored pairs — lamps, mirrors, arches — are placed
    by centre, because writing them as opposing corners means every one of them
    needs its own `min`/`max` reasoning and the left of the pair reads
    differently from the right.
    """
    low = tuple(c - h for c, h in zip(centre, half, strict=True))
    high = tuple(c + h for c, h in zip(centre, half, strict=True))
    return _box(low, high, colour, name=name)


def _wheel(radius: float, width: float, segments: int, *, name: str) -> MeshData:
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
        parts.append(
            _polygon(
                [(half, 0.0, 0.0), (half, y0, z0), (half, y1, z1)],
                SILVER,
                name=f"{name}_hub_r_{i}",
            )
        )
        parts.append(
            _polygon(
                [(-half, 0.0, 0.0), (-half, y1, z1), (-half, y0, z0)],
                SILVER,
                name=f"{name}_hub_l_{i}",
            )
        )
    return merge(parts, name=name)


# --------------------------------------------------------------------------
# The taxi
# --------------------------------------------------------------------------


def taxi_body(chassis: Chassis, shape: Proportions) -> MeshData:
    """The body as one mesh, and so one draw call and one material."""
    front_z = -shape.length_m / 2.0
    rear_z = shape.length_m / 2.0
    hw = shape.half_width_m
    parts: list[MeshData] = []

    # Lower body: the full three-box mass from bumper to bumper.
    parts.append(
        _box(
            (-hw, shape.sill_y_m, front_z),
            (hw, shape.belt_y_m, rear_z),
            _faces(RED, bottom=DARK),
            name="lower",
        )
    )

    # Greenhouse: belt line to roof, pulled in on all four sides so the pillars
    # rake. Glass on the sides, silver on top — the taxi's own two-tone.
    inset = shape.roof_inset_m
    cabin = (
        (-hw, shape.belt_y_m, shape.cabin_front_z_m),
        (hw, shape.belt_y_m, shape.cabin_front_z_m),
        (hw, shape.belt_y_m, shape.cabin_rear_z_m),
        (-hw, shape.belt_y_m, shape.cabin_rear_z_m),
    )
    roof = (
        (-hw + inset, shape.roof_y_m, shape.cabin_front_z_m + shape.roof_front_taper_m),
        (hw - inset, shape.roof_y_m, shape.cabin_front_z_m + shape.roof_front_taper_m),
        (hw - inset, shape.roof_y_m, shape.cabin_rear_z_m - shape.roof_rear_taper_m),
        (-hw + inset, shape.roof_y_m, shape.cabin_rear_z_m - shape.roof_rear_taper_m),
    )
    parts.append(
        _hexahedron(
            cabin,
            roof,
            _faces(GLASS, top=SILVER),
            name="greenhouse",
        )
    )

    # Roof sign.
    sign_z = (shape.cabin_front_z_m + shape.cabin_rear_z_m) / 2.0 - 0.10
    parts.append(
        _box(
            (-shape.sign_half_width_m, shape.roof_y_m, sign_z - shape.sign_half_length_m),
            (
                shape.sign_half_width_m,
                shape.roof_y_m + shape.sign_height_m,
                sign_z + shape.sign_half_length_m,
            ),
            _faces(LAMP, bottom=DARK, top=SILVER),
            name="sign",
        )
    )

    # Bumpers, standing proud of the body at each end.
    parts.append(_box_at((0.0, -0.03, front_z + 0.02), (hw, 0.09, 0.08), DARK, name="front_bumper"))
    parts.append(_box_at((0.0, -0.03, rear_z - 0.02), (hw, 0.09, 0.08), DARK, name="rear_bumper"))
    parts.append(_box_at((0.0, 0.11, front_z + 0.01), (0.42, 0.09, 0.03), DARK, name="grille"))

    lamp_x = 0.68
    for tag, side in (("l", -1.0), ("r", 1.0)):
        parts.append(
            _box_at(
                (side * lamp_x, 0.19, front_z + 0.015),
                (0.10, 0.09, 0.035),
                LAMP,
                name=f"headlamp_{tag}",
            )
        )
        parts.append(
            _box_at(
                (side * lamp_x, 0.21, rear_z - 0.015),
                (0.10, 0.09, 0.035),
                RED,
                name=f"taillamp_{tag}",
            )
        )
        # Wing mirrors: tiny, but they break the greenhouse silhouette.
        parts.append(
            _box_at(
                (side * (hw + 0.045), 0.35, shape.cabin_front_z_m + 0.09),
                (0.045, 0.05, 0.07),
                DARK,
                name=f"mirror_{tag}",
            )
        )

    # Wheel arches: a curved lip reaching from the flank out over each tyre.
    # Spanned from the wheel outward rather than from the body outward, so it
    # stays a lip over the wheel when either width is retuned — the version
    # measured off `half_width_m` silently stopped covering anything the moment
    # the body narrowed.
    for tag, z in (("front", -chassis.wheelbase_m / 2.0), ("rear", chassis.wheelbase_m / 2.0)):
        for side_tag, side in (("l", -1.0), ("r", 1.0)):
            parts.extend(_arch(chassis, shape, z=z, side=side, name=f"arch_{tag}_{side_tag}"))

    parts.extend(_flank_detail(chassis, shape))
    return merge(parts, name="taxi_body")


def _arch(
    chassis: Chassis, shape: Proportions, *, z: float, side: float, name: str
) -> list[MeshData]:
    """One wheel arch, as a band swept over the top of the tyre plus its rim.

    Swept from the hub rather than boxed around it because a box lip reads as a
    shelf: the eye finds the corner before it finds the wheel. Only the top half
    is drawn — below the hub the lip would be inside the tyre.
    """
    inner_x = side * (shape.half_width_m - 0.02)
    outer_x = side * (chassis.track_m / 2.0 + shape.wheel_width_m / 2.0 + shape.arch_flare_m)
    outer_r = chassis.wheel_radius_m + 0.07
    inner_r = chassis.wheel_radius_m + 0.01
    hub_y = chassis.hub_y_m

    def at(angle: float, radius: float) -> tuple[float, float]:
        return (hub_y + radius * np.sin(angle), z + radius * np.cos(angle))

    parts: list[MeshData] = []
    angles = np.linspace(0.0, np.pi, shape.arch_segments + 1)
    for i in range(shape.arch_segments):
        a0, a1 = float(angles[i]), float(angles[i + 1])
        (y0, z0), (y1, z1) = at(a0, outer_r), at(a1, outer_r)
        # The band the wheel sits under, facing away from the hub.
        mid = (a0 + a1) / 2.0
        parts.append(
            _polygon_facing(
                [(inner_x, y0, z0), (outer_x, y0, z0), (outer_x, y1, z1), (inner_x, y1, z1)],
                RED,
                (0.0, float(np.sin(mid)), float(np.cos(mid))),
                name=f"{name}_band_{i}",
            )
        )
        (yr0, zr0), (yr1, zr1) = at(a0, inner_r), at(a1, inner_r)
        parts.append(
            _polygon_facing(
                [(outer_x, y0, z0), (outer_x, yr0, zr0), (outer_x, yr1, zr1), (outer_x, y1, z1)],
                RED,
                (side, 0.0, 0.0),
                name=f"{name}_rim_{i}",
            )
        )
    return parts


def _flank_detail(chassis: Chassis, shape: Proportions) -> list[MeshData]:
    """Pillars, door shuts, handles and grille slats.

    All of it is proud of the surface rather than cut into it. Flat shading
    reads a raised edge and a recessed one identically, and a raised strip costs
    one box where a recess costs a re-tiled flank.
    """
    parts: list[MeshData] = []
    hw = shape.half_width_m
    front_z = -shape.length_m / 2.0
    cabin_mid_z = (shape.cabin_front_z_m + shape.cabin_rear_z_m) / 2.0
    pillar_y = (shape.belt_y_m + shape.roof_y_m) / 2.0
    pillar_half_y = (shape.roof_y_m - shape.belt_y_m) / 2.0

    for tag, side in (("l", -1.0), ("r", 1.0)):
        # A, B and C pillars. The B pillar is what makes it read as a saloon
        # rather than a coupe, and the taxi is always a saloon.
        for pillar, z, half_z, colour in (
            ("a", shape.cabin_front_z_m + 0.22, 0.05, DARK),
            ("b", cabin_mid_z, 0.045, SILVER),
            ("c", shape.cabin_rear_z_m - 0.16, 0.05, DARK),
        ):
            parts.append(
                _box_at(
                    (side * (hw - 0.055), pillar_y, z),
                    (0.02, pillar_half_y, half_z),
                    colour,
                    name=f"pillar_{pillar}_{tag}",
                )
            )
        # Door shut lines and handles, on the two doors either side.
        for door, z in (("front", cabin_mid_z - 0.42), ("rear", cabin_mid_z + 0.42)):
            parts.append(
                _box_at(
                    (side * (hw + 0.005), 0.10, z),
                    (0.008, 0.26, 0.012),
                    DARK,
                    name=f"shut_{door}_{tag}",
                )
            )
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


def build_taxi(chassis: Chassis, shape: Proportions) -> list[MeshData]:
    """Body and wheel, in that order — two meshes, so two draw calls."""
    wheel = _wheel(
        chassis.wheel_radius_m, shape.wheel_width_m, shape.wheel_segments, name="taxi_wheel"
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
        body, wheel = written[0][2], written[1][2]
        LOG.info(
            "  as the scene builds it: %d body + 4 x %d wheel = %d triangles",
            body.triangle_count,
            wheel.triangle_count,
            body.triangle_count + 4 * wheel.triangle_count,
        )
        LOG.info("  ground plane at y %+.2f, hub at y %+.2f", chassis.ground_y_m, chassis.hub_y_m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
