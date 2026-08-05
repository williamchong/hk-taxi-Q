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

from pipeline.gltf import MeshData, normalise, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402

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
SILVER = (168, 172, 178)
DARK = (30, 32, 36)
GLASS = (18, 19, 22)
LAMP = (242, 236, 205)
# ⚠️ A sixth colour, where `ART_DESIGN.md` says 3-5 per vehicle. It buys the
# indicator in the tail-lamp cluster, which is three lenses stacked — amber
# over white over red — and that stack is a specific identifying feature of the
# car's rear. Two colours cannot express three lenses. Flagged rather than
# quietly taken: see docs/PROGRESS.md, P3-11.
AMBER = (226, 138, 32)
# ⚠️ A seventh, on the same terms. It is the 4 SEATS badge and nothing else —
# the one green thing on a red car, which is exactly why the badge is legible
# as a shape now that its lettering is gone. Nothing may borrow it for anything
# that is not that badge, or the count stops being defensible.
BADGE_GREEN = (12, 116, 82)

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
    # bevel is one more ring, not a curve — see `_loft`.
    bevel_m: float = 0.06
    # The silver band between the glass and the roof. The reference art shows
    # roof paint coming down over the pillars; without this the roof reads as a
    # pale lid laid on a red box, which is the note the first review returned.
    cant_rail_m: float = 0.10
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
    # `_loft`, the flanks through `_flank` — so the car keeps a bumper band all
    # the way round without one face leaving the silhouette. Raise it and the
    # dark hem climbs the doors; the *front* plate, both badges and the fog
    # lamps sit on the band and have to stay under it. The rear plate does not —
    # it is on the boot, as the real car's is, which is why it alone is exempt
    # from the "stays on the bumper" test.
    bumper_top_y_m: float = 0.02
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
    def sign_z_m(self) -> float:
        """Centre of the roof sign, set back slightly from the cabin's middle."""
        return self.cabin_mid_z_m - 0.06

    @property
    def lower_profile(self) -> tuple[tuple[float, float, float], ...]:
        """(z inset from each end, y, corner cut) for the rings of the lower body.

        Five rings, not the four the shape needs: the extra one is the top of
        the bumper band, and it exists only so `_loft` has an edge to change
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
        # at which point `np.interp` returns nonsense without raising and `_loft`
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
    axis: int = 1,
    name: str,
) -> MeshData:
    """A profile lofted through stacked rings — the shape a car body is.

    Bevels at this scale are not rounded edges, they are *one more ring* a few
    centimetres in and up. Stacking three or four rings gives a chamfered sill,
    a tucked roof and a raked pillar for four quads apiece, and it keeps every
    face flat — which is the whole point, since the city it drives through is
    flat-shaded and a smooth-shaded car would sit outside its own art direction.

    `axis` is which way the rings are stacked, and it is a parameter because the
    4 SEATS badge is the same operation lying on its side — a profile extruded
    along Z rather than Y. That was written out by hand first, centroid, outward
    masking and both caps, and it produced the *identical* solid: same 28
    triangles, same vertices, same area. Two copies of this loop is one more
    place for the outward-facing rule to be got wrong.
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
    # Flattened along the stacking axis, both here and on every band below. A
    # side face looks *outward from the profile*, and leaving the axis component
    # in tilts that vector by however much the rings taper — which is enough to
    # flip a face on a steeply raked band.
    centre = np.mean(np.asarray(rings[0], dtype=np.float64), axis=0)
    centre[axis] = 0.0
    for i, colour in enumerate(band_colours):
        lower, upper = rings[i], rings[i + 1]
        for edge in range(corners):
            if edge in skip_edges:
                continue
            nxt = (edge + 1) % corners
            outward = np.mean([lower[edge], lower[nxt], upper[edge], upper[nxt]], axis=0) - centre
            outward[axis] = 0.0
            parts.append(
                _polygon_facing(
                    [lower[nxt], lower[edge], upper[edge], upper[nxt]],
                    colour,
                    outward,
                    name=f"{name}_edge{edge}_{i}",
                )
            )

    end = np.zeros(3)
    end[axis] = 1.0
    parts.append(_polygon_facing(rings[0], bottom, -end, name=f"{name}_bottom"))
    parts.append(_polygon_facing(rings[-1], top, end, name=f"{name}_top"))
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
    return _box((x - half_x, y - half_y, z0), (x + half_x, y + half_y, z1), colour, name=name)


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
    profile = shape.lower_profile
    lower_rings = [
        _ring(y, hw, front_z + inset_z, rear_z - inset_z, ring_cut)
        for inset_z, y, ring_cut in profile
    ]
    parts.append(
        _loft(
            lower_rings,
            # Two dark bands then two red: the bumper, painted on. It used to be
            # a box standing 6 cm proud of each end, and at the size the car is
            # actually played at that bar was the widest thing on it. Bodywork
            # keeps the bumper visible and takes it out of the silhouette.
            [DARK, DARK, RED, RED],
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
    # as a white brick. Blank — see `_plates` for why no lettering survives.
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
                # Raked across its width only, never its depth, so the fore and
                # aft faces stay vertical planes at constant z. Nothing is stuck
                # to them any more, but the silhouette a raked box gives from
                # the side is the whole reason the rake is here.
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

    # ⚠️ No bumper *parts*. There are no boxes here any more and there should
    # not be: the bumper is the dark band `_loft` and `_flank` paint below
    # `bumper_top_y_m`, so it is visible from every angle and adds nothing to
    # the silhouette. Adding a box back is how it went wrong the first time.
    parts.append(_box_at((0.0, 0.11, front_z + 0.01), (0.42, 0.09, 0.03), DARK, name="grille"))
    parts.extend(_plates(shape))
    parts.extend(_badge(shape, rear=rear) for rear in (False, True))

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
        # white tail lamp besides.
        for lens, (offset, colour) in enumerate(
            ((0.073, AMBER), (0.0, LAMP), (-0.073, RED)),
        ):
            parts.append(
                _flush_fixture(
                    shape,
                    centre=(side * (hw - 0.13), 0.21 + offset),
                    half=(0.085, 0.034),
                    colour=colour,
                    rear=True,
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

    parts.extend(_flank_detail(shape))
    return merge(parts, name="taxi_body")


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
    of that panel at the top of the badge and buried at the bottom. `_loft`
    builds it, extruding along Z — see `axis` there for why that is not a
    second implementation.
    """
    x, y0, radius = shape.badge_x_m, shape.badge_y_m, shape.badge_radius_m
    angles = np.linspace(np.pi, 0.0, shape.badge_segments + 1)
    outline = [(x + radius * float(np.cos(a)), y0 + radius * float(np.sin(a))) for a in angles]
    # Sorted, so `rings[0]` is always the end `_loft` caps facing -Z. The nose
    # seats its face at the *lower* z and the tail at the higher one, and
    # passing them in call order would turn one of the two badges inside out.
    return _loft(
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

    The flank is red from the sill to the belt line and carries no trim at all —
    see `panel` for why the bumper band stops at the corners rather than running
    through here, and `_flank_detail` for the two strips that used to run along
    it.
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

    def panel(z0: float, z1: float, y0: float, y1: float, *, tag: str) -> MeshData:
        """One stretch of flank, from the arc (or the sill) up to the belt line.

        The two z and the two y are positional and interchangeable by mistake —
        transposing the pairs compiles and builds a silently wrong quad — so
        `tag` is keyword-only to keep the four coordinates adjacent and ordered.

        ⚠️ Red top to bottom, deliberately. The bumper band the nose and tail
        carry below `bumper_top_y_m` was continued along here for one round, and
        it was wrong: a dark line down the side reads as a stripe painted on a
        toy, not as trim. The band stops where `_loft` stops it — wrapped round
        each end and through the corner chamfers — which is where a real bumper
        stops too.
        """
        return _polygon_facing(
            [
                (x_out, y0, z0),
                (x_out, shape.belt_y_m, z0),
                (x_out, shape.belt_y_m, z1),
                (x_out, y1, z1),
            ],
            RED,
            (side, 0.0, 0.0),
            name=f"{name}_{tag}",
        )

    parts: list[MeshData] = []
    # Solid stretches: nose to front arch, between the arches, rear arch to tail.
    spans = (
        (front_z, wheels_z[0] - opening_r),
        (wheels_z[0] + opening_r, wheels_z[1] - opening_r),
        (wheels_z[1] + opening_r, rear_z),
    )
    for i, (z0, z1) in enumerate(spans):
        parts.append(panel(z0, z1, shape.sill_y_m, shape.sill_y_m, tag=f"span_{i}"))

    for w, wheel_z in enumerate(wheels_z):
        columns = np.linspace(wheel_z - opening_r, wheel_z + opening_r, shape.arch_segments + 1)
        for c in range(shape.arch_segments):
            z0, z1 = float(columns[c]), float(columns[c + 1])
            y0, y1 = arc_y(z0, wheel_z), arc_y(z1, wheel_z)
            # Bodywork above the arc.
            parts.append(panel(z0, z1, y0, y1, tag=f"arch_{w}_{c}"))
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


def _flank_detail(shape: Proportions) -> list[MeshData]:
    """Door handles, and the running list of what the flank does *not* carry.

    They are proud of the surface rather than cut into it. Flat shading reads a
    raised edge and a recessed one identically, and a raised handle costs one box
    where a recess costs a re-tiled flank.
    """
    parts: list[MeshData] = []
    hw = shape.half_width_m
    cabin_mid_z = shape.cabin_mid_z_m

    for tag, side in (("l", -1.0), ("r", 1.0)):
        # ⚠️ No modelled A/B/C pillars. They were straight boxes against a
        # greenhouse that tapers inward as it rises, so each one stood 0.14 m
        # proud of the glass at the roofline and read as a black stick growing
        # out of the roof. A box cannot sit flush on a tapering face at more
        # than one height, so this is structural rather than a number to tune:
        # the silver-over-glass reading comes from `_loft`'s cant rail instead,
        # and painting the pillars is not something this model does at all.
        #
        # ⚠️ No rub strip and no sill skirt. Both were dark bars running most of
        # the flank's length and standing 2-3 cm proud of it, put there because a
        # review called the flank flat — and at any distance the car is actually
        # played at they read as black stripes painted down the side of a toy,
        # not as trim. **The flank is red from the sill to the belt line and
        # nothing else goes on it.** Its horizontal break comes from the wheel
        # arches; the bumper band stops at the corner chamfers, deliberately.
        #
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
