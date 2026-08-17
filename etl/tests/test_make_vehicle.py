"""The `P3-11` vehicle generator (`tools/make_vehicle.py`).

Four kinds of test, and the first is the reason this file exists.

**The chassis desync guard.** The physics never reads the mesh — `P0-5a` chose a
custom raycast controller so the wheel hardpoints are authored in the scene, and
`P0-5` tuned handling against those points. A model built to a different
wheelbase therefore looks correct, drives to the old tuning, and shows nothing
wrong in a drive. Nothing else in the project can catch that, so these tests
read the shipped `.tscn` and `.tres` and hold the generator to them.

**The committed-asset guard.** The `.glb`s are build output that is *committed*,
and `tools/check.sh` does not know this tool exists. Regenerating and comparing
bytes is what catches "edited the generator, forgot to re-run".

**Winding and degeneracy.** Both had real bugs on the first run: the wheel was
wound inside-out (backface culling renders that as a wheel-shaped hole), and the
caps were faked as quads with two coincident corners, which makes the face
normal come out of a zero-length edge. Neither is visible in a triangle count.

**Seating.** The bumper was a flat bar, and everything low on the car was bolted
to it with one hand-copied z. It is bodywork now, and the panel those fixtures
fell back onto slopes — so whether a plate is visible along its whole height, or
hangs off the paint, or sinks into it, is arithmetic no render reliably shows and
no other check reaches. `TestFixturesSeatedInTheBodywork` is that arithmetic.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest
from make_vehicle import (
    AMBER,
    BADGE_GREEN,
    BODY_MATERIAL,
    CIRCUIT_BRAKE,
    CIRCUIT_HEADLAMP,
    CIRCUIT_INDICATOR_L,
    CIRCUIT_INDICATOR_R,
    CIRCUIT_NONE,
    CIRCUIT_REVERSE,
    CIRCUIT_SIDELAMP,
    DARK,
    DEEP_RED,
    FIXTURE_PROUD_M,
    GLASS,
    LAMP,
    LAMP_CIRCUITS,
    MARKER_GLASS,
    MARKER_LAMP,
    MARKER_PAINT,
    MARKER_TRIM,
    RED,
    SILVER,
    Chassis,
    Proportions,
    _badge,
    _check_wiring,
    _flush_fixture,
    _high_brake_lamp,
    _plates,
    _rear_door_z_m,
    _wheel,
    build_taxi,
    opening_radius_m,
    taxi_body,
    write_taxi,
)
from primitives import Colour, box, polygon

from pipeline.gltf import MeshData, triangle_cross
from pipeline.mesh import select_triangles

ROOT = Path(__file__).resolve().parents[2]
TAXI_SCENE = ROOT / "game" / "scenes" / "vehicle" / "taxi.tscn"
HANDLING = ROOT / "game" / "tuning" / "handling.tres"
SHIPPED = ROOT / "game" / "assets" / "authored" / "vehicles"

# `ART_DESIGN.md`'s ceiling for one vehicle.
TRIANGLE_CEILING = 2000
PALETTE = (RED, SILVER, DARK, GLASS, LAMP, AMBER, BADGE_GREEN, DEEP_RED)


def _rgbs(mesh: MeshData, where: np.ndarray | None = None) -> set[Colour]:
    """Every distinct colour on a mesh, or on the vertices `where` selects.

    `np.unique` returns rows of `np.uint8`, which compare unequal to the plain
    tuples in `PALETTE` unless converted — and indexing `[0]` to dodge that is
    what let a two-coloured plate pass an equality check.
    """
    assert mesh.colours is not None, f"{mesh.name} carries no colours"
    rgb = mesh.colours[:, :3] if where is None else mesh.colours[where, :3]
    return {tuple(int(channel) for channel in row) for row in np.unique(rgb, axis=0)}


def _tres_float(text: str, field: str) -> float:
    match = re.search(rf"^{field} = ([\d.]+)$", text, flags=re.MULTILINE)
    assert match is not None, f"{field} is gone from handling.tres"
    return float(match.group(1))


def _marker_origins(scene: str) -> dict[str, tuple[float, float, float]]:
    """Every wheel hardpoint in the scene, by node name, as its xyz origin.

    A `Transform3D` is nine basis floats then three origin floats; the wheels
    are unrotated, so only the last three carry chassis information.

    Selected by node *type* since `Q50`, where the hardpoints stopped being
    `Marker3D`s running `wheel_mount.gd` and became `VehicleWheel3D`s. That is
    also more robust than what it replaces: matching on the script's ExtResource
    id meant resolving that id from the script path first, because Godot
    renumbers the ids on an editor save and a stale literal would quietly select
    no nodes at all — leaving this guard passing over nothing.
    """
    origins: dict[str, tuple[float, float, float]] = {}
    for block in re.split(r"^\[node ", scene, flags=re.MULTILINE)[1:]:
        name = re.match(r'name="([^"]+)"', block)
        transform = re.search(r"transform = Transform3D\(([^)]*)\)", block)
        if name is None or transform is None:
            continue
        if 'type="VehicleWheel3D"' not in block:
            continue
        values = [float(part) for part in transform.group(1).split(",")]
        origins[name.group(1)] = (values[-3], values[-2], values[-1])
    return origins


@pytest.fixture(scope="module")
def scene_chassis() -> Chassis:
    """The chassis as the *shipped scene and profile* describe it."""
    origins = _marker_origins(TAXI_SCENE.read_text())
    assert len(origins) == 4, f"expected four VehicleWheel3Ds, found {sorted(origins)}"

    xs = sorted({round(origin[0], 4) for origin in origins.values()})
    zs = sorted({round(origin[2], 4) for origin in origins.values()})
    assert len(xs) == 2 and len(zs) == 2, f"wheels are not a rectangle: {origins}"

    profile = HANDLING.read_text()
    return Chassis(
        wheelbase_m=zs[1] - zs[0],
        track_m=xs[1] - xs[0],
        wheel_radius_m=_tres_float(profile, "wheel_radius_m"),
        suspension_rest_m=_tres_float(profile, "suspension_rest_length_m"),
    )


@pytest.fixture(scope="module")
def meshes() -> list[MeshData]:
    return build_taxi(Chassis(), Proportions())


@pytest.fixture(scope="module")
def bare_flank() -> MeshData:
    """The body with the rocker switched off, for the tests that need both.

    Module-scoped for the same reason `meshes` is: `taxi_body` is 12 ms, the new
    tests wanted it nine times, and none of them mutates what it gets back.
    """
    return taxi_body(Chassis(), replace(Proportions(), rocker_top_y_m=Proportions().sill_y_m))


class TestChassisMatchesTheScene:
    """If these fail, the model and the tuned physics have drifted apart.

    Fix by changing `Chassis`' defaults to follow the scene — never by moving
    the scene to suit the model, which silently retunes a car `P0-5` signed off.
    """

    def test_every_hardpoint_agrees(self, scene_chassis: Chassis) -> None:
        assert Chassis() == scene_chassis

    def test_the_wheel_mesh_fills_the_radius_the_profile_tunes(
        self, scene_chassis: Chassis
    ) -> None:
        """A visual wheel smaller than its raycast hovers; larger, it sinks."""
        wheel = _wheel(scene_chassis.wheel_radius_m, 0.2, 12, name="w")
        radial = np.linalg.norm(wheel.positions[:, 1:], axis=1)
        assert radial.max() == pytest.approx(scene_chassis.wheel_radius_m, abs=1e-6)

    def test_the_body_is_exactly_as_wide_as_the_track(self, scene_chassis: Chassis) -> None:
        """`half_width_m` is a hand-copied literal of track/2 + tyre width/2,
        and both failure modes have been shipped: narrower and the tyres stand
        outside the flank like pre-war fenders, wider and they vanish inside it.
        Neither raises anything, so the equality is asserted here instead."""
        shape = Proportions()
        flush = scene_chassis.track_m / 2.0 + shape.wheel_width_m / 2.0
        assert shape.half_width_m == pytest.approx(flush, abs=1e-9)

    def test_the_wheels_rest_on_the_ground_plane(self, scene_chassis: Chassis) -> None:
        """Stated as the relationship, not as the two numbers it produces —
        pinning the literals would only detect that they changed together."""
        assert scene_chassis.hub_y_m == pytest.approx(-scene_chassis.suspension_rest_m)
        assert scene_chassis.ground_y_m == pytest.approx(
            scene_chassis.hub_y_m - scene_chassis.wheel_radius_m
        )

    def test_the_scene_does_not_re_author_the_rest_length(self) -> None:
        """A `VehicleWheel3D` positions its own child mesh from
        `wheel_rest_length`, which the controller writes from the profile — so no
        wheel mesh may carry a transform of its own. A scene copy would hover or
        sink the moment the spring is retuned, with the physics unchanged. Held
        by `wheel_visual.gd` reading the profile before `Q50` deleted it."""
        scene = TAXI_SCENE.read_text()
        visuals = [
            block
            for block in re.split(r"^\[node ", scene, flags=re.MULTILINE)[1:]
            if block.startswith('name="Visual"')
        ]
        assert len(visuals) == 4, "expected four wheel Visual nodes"
        for block in visuals:
            assert "transform = " not in block, "a wheel Visual re-authors its own offset"


class TestShippedAssets:
    """The `.glb`s are committed, and nothing else in the build checks them."""

    def test_the_committed_files_match_the_generator(self, tmp_path: Path) -> None:
        written = write_taxi(tmp_path, Chassis(), Proportions())
        for path, _, _ in written:
            shipped = SHIPPED / path.name
            assert shipped.exists(), f"{shipped.name} is not committed"
            assert shipped.read_bytes() == path.read_bytes(), (
                f"{shipped.name} is stale — re-run tools/make_vehicle.py"
            )


class Seated(NamedTuple):
    """One fixture `_seated_depth` placed, and what is expected of it."""

    mesh: MeshData
    rear: bool
    on_bumper: bool


class TestFixturesSeatedInTheBodywork:
    """Lamps and plates sit *in* the nose and tail, not on a bumper bar.

    The bumpers used to be two boxes standing 6 cm proud of each end, and the
    plate and the fog lamps were mounted on them. With the bar folded back into
    the bodywork there is nothing flat left to bolt to: the lower body is lofted
    through rings that draw in towards the sill, so the panel these sit on is at
    a different z at every height. A hand-copied z floats at one edge and sinks
    at the other, and neither raises anything.
    """

    @staticmethod
    def _face_z(shape: Proportions, y: float, *, rear: bool) -> float:
        inset = shape.face_inset_m(y)
        return shape.rear_z_m - inset if rear else shape.front_z_m + inset

    @staticmethod
    def _fixtures(shape: Proportions) -> list[Seated]:
        """Every fixture `_seated_depth` places, with what is expected of it.

        The tail lamps are absent because they cannot pass the last assertion by
        design — they sit on the boot, above the bumper band — and the fog lamps
        are present because the class docstring names them and they were the
        other thing bolted to the deleted bar.
        """
        front_plate, rear_plate = _plates(shape)
        fog = [
            _flush_fixture(
                shape,
                centre=(side * 0.66, -0.04),
                half=(0.105, 0.03),
                colour=LAMP,
                rear=False,
                name=f"foglamp_{tag}",
            )
            for tag, side in (("l", -1.0), ("r", 1.0))
        ]
        return [
            Seated(front_plate, rear=False, on_bumper=True),
            # ⚠️ The one exemption, and it is an expectation rather than a skip.
            # The rear plate is on the boot, as the real car's is; asserting that
            # here is what keeps it from silently drifting onto the band.
            Seated(rear_plate, rear=True, on_bumper=False),
            Seated(_badge(shape, rear=False), rear=False, on_bumper=True),
            Seated(_badge(shape, rear=True), rear=True, on_bumper=True),
            *(Seated(lamp, rear=False, on_bumper=True) for lamp in fog),
        ]

    def test_each_one_is_proud_of_the_panel_along_its_whole_height(self) -> None:
        """Visible at the top edge and at the bottom edge, not just the middle.

        ⚠️ And at every profile knot between them. `face_inset_m` is not
        monotonic — the body is furthest out at `belt_y_m - bevel_m * 1.4`, in
        the middle of the range — so sampling only the edges passed a top
        tail-lamp lens that stood 8.5 mm proud where 15 mm was promised."""
        shape = Proportions()
        for seat in self._fixtures(shape):
            low, high = seat.mesh.aabb()
            outer = high[2] if seat.rear else low[2]
            knots = [y for _, y, _ in shape.lower_profile if low[1] < y < high[1]]
            for y in (low[1], high[1], *knots):
                face = self._face_z(shape, y, rear=seat.rear)
                clear = (outer - face) if seat.rear else (face - outer)
                assert clear >= FIXTURE_PROUD_M - 1e-9, (
                    f"{seat.mesh.name} stands only {clear * 1000:.1f} mm proud at y={y:+.3f}"
                )

    def test_none_of_them_leaves_a_gap_behind_it(self) -> None:
        """The other failure: a fixture bridging a slope hangs off the paint."""
        shape = Proportions()
        for seat in self._fixtures(shape):
            low, high = seat.mesh.aabb()
            inner = low[2] if seat.rear else high[2]
            for y in (low[1], high[1]):
                face = self._face_z(shape, y, rear=seat.rear)
                buried = (face - inner) if seat.rear else (inner - face)
                # Flush is the intended answer at the deepest edge, so the bound
                # has to tolerate the rounding that reaches it, not just floats.
                assert buried >= -1e-9, f"{seat.mesh.name} floats clear at y={y:+.3f}"

    def test_none_of_them_reaches_below_the_valance(self) -> None:
        """⚠️ Where the body folds in hard, `_seated_depth` answers correctly
        and the answer looks wrong: a fixture spanning the fold is made deep
        enough to bridge it, so it stands 4 cm off the paint at its bottom edge
        and hangs below the car's own outline. The badge did exactly that. The
        fix is placement, not depth, and this is what holds the placement.

        Stated against `bumper_bottom_y_m` rather than against `sill_y_m +
        bevel_m`, which is the same number and was what this asserted before.
        The sum was arithmetic about a fold; the property is the line the bumper
        band stops at, and every fixture here is *on* that band — so a plate
        crossing it now fails for the reason that matters, which is that it
        would be a light shape half on the dark bumper and half on the red
        valance below it."""
        shape = Proportions()
        for seat in self._fixtures(shape):
            low, _ = seat.mesh.aabb()
            assert low[1] >= shape.bumper_bottom_y_m, (
                f"{seat.mesh.name} reaches below the bumper band onto the valance"
            )

    def test_each_one_sits_where_its_backing_colour_is(self) -> None:
        """A fixture on the bumper is a light shape on DARK; one on the boot is a
        light shape on RED. Crossing `bumper_top_y_m` puts half of it on each."""
        shape = Proportions()
        for seat in self._fixtures(shape):
            low, high = seat.mesh.aabb()
            edge = high[1] if seat.on_bumper else low[1]
            below = edge <= shape.bumper_top_y_m
            assert below is seat.on_bumper, (
                f"{seat.mesh.name} straddles the bumper line at y={edge:+.3f}"
            )


def _faces_of(mesh: MeshData, colour: Colour) -> np.ndarray:
    """Every triangle painted `colour`, as an (n, 3) index array.

    Flat shading means one colour per face, so the first corner's colour is the
    face's colour — the same shortcut `TestWinding` takes for normals.
    """
    assert mesh.colours is not None
    wanted = np.array(colour, dtype=np.uint8)
    return mesh.triangles[np.all(mesh.colours[:, :3][mesh.triangles[:, 0]] == wanted, axis=1)]


class TestTheScreensAreRaked:
    """The windscreen and the backlight, measured off the mesh that ships.

    Both slope because two *other* numbers happened to make them: the roof
    tapers positioned the roof edge and the top of the glass was a bare `* 0.8`
    of them. That produced 32.3° at the front, near enough by accident, and
    **18.6° at the rear**, which reads as a vertical wall from the chase camera
    — the one angle `ART_DESIGN.md` says most players ever see. Nothing here
    caught it, because nothing here knew the greenhouse had an angle at all.
    """

    @staticmethod
    def _screen_rakes(shape: Proportions, body: MeshData) -> dict[str, np.ndarray]:
        """Rake of each glazed face that spans the car, in degrees off vertical.

        The screens are the glass faces whose normal has no `x` component; the
        side windows and the corner chamfers all do. A face raked `a` off
        vertical carries a normal `a` off horizontal, so the angle is read
        between the normal's y and z — not between z and y, which is the
        complement and looked plausible enough to be believed once.
        """
        glass = _faces_of(body, GLASS)
        normals = body.normals[glass[:, 0]]
        spanning = np.abs(normals[:, 0]) < 1e-6
        faces, normals = glass[spanning], normals[spanning]
        # The loft caps its bottom ring in GLASS too, and a horizontal face is
        # not a screen. It reads 90° here, so it is excluded by what it is
        # rather than by where it is.
        upright = np.abs(normals[:, 2]) > 1e-6
        faces, normals = faces[upright], normals[upright]
        rake = np.degrees(np.arctan2(np.abs(normals[:, 1]), np.abs(normals[:, 2])))
        z = body.positions[faces].mean(axis=1)[:, 2]
        return {
            "windscreen": rake[z < shape.cabin_mid_z_m],
            "backlight": rake[z > shape.cabin_mid_z_m],
        }

    def test_each_screen_has_the_rake_it_was_given(self, meshes: list[MeshData]) -> None:
        shape = Proportions()
        rakes = self._screen_rakes(shape, meshes[0])
        for name, authored in (
            ("windscreen", shape.windscreen_rake_deg),
            ("backlight", shape.backlight_rake_deg),
        ):
            measured = rakes[name]
            assert len(measured), f"no {name} faces found"
            # Normals ship as float32, so the tolerance is the format's, not the
            # geometry's — the angles themselves are exact.
            assert measured == pytest.approx(authored, abs=1e-4), (
                f"{name} is raked {measured.mean():.1f}°, not {authored}°"
            )

    def test_the_cant_rail_continues_the_screen_it_caps(self) -> None:
        """One plane, not two. The silver band above the glass is where the
        paint changes, not where the bodywork turns — so deriving the roof taper
        from the same angle is the whole reason `roof_front_taper_m` stopped
        being a field."""
        shape = Proportions()
        belt, glass_top, roof = shape.greenhouse_profile
        for label, (glass_span, rail_span, sign) in {
            "front": ((belt.z_front, glass_top.z_front), (glass_top.z_front, roof.z_front), 1.0),
            "rear": ((belt.z_rear, glass_top.z_rear), (glass_top.z_rear, roof.z_rear), -1.0),
        }.items():
            glass_rake = np.degrees(
                np.arctan2(sign * (glass_span[1] - glass_span[0]), shape.glass_band_m)
            )
            cant_rake = np.degrees(
                np.arctan2(sign * (rail_span[1] - rail_span[0]), shape.cant_rail_m)
            )
            assert glass_rake == pytest.approx(cant_rake, abs=1e-9), (
                f"{label} glass rakes {glass_rake:.2f}° but its cant rail rakes {cant_rake:.2f}°"
            )

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("windscreen_rake_deg", -10.0),
            ("windscreen_rake_deg", 75.0),
            ("backlight_rake_deg", -10.0),
            ("backlight_rake_deg", 80.0),
        ],
        ids=["front inverted", "front leaves no roof", "rear inverted", "rear leaves no roof"],
    )
    def test_a_rake_the_cabin_cannot_carry_is_refused(self, field: str, value: float) -> None:
        """⚠️ The failure this replaces is silent. `loft` joins ring *i* to ring
        *i+1* whatever their coordinates are, and `polygon_facing` faithfully
        turns each face outward from a profile that is itself inside out — so an
        over-raked greenhouse builds without an error, without a degenerate
        triangle, and passes the winding check. Only the render would say."""
        with pytest.raises(ValueError):
            _ = replace(Proportions(), **{field: value}).greenhouse_profile

    @pytest.mark.parametrize("field", ["windscreen_rake_deg", "backlight_rake_deg"])
    def test_a_square_greenhouse_is_allowed(self, field: str) -> None:
        """⚠️ Zero rake is the boundary the guard above must not swallow. A
        vertical screen lofts perfectly well — it is the cheap car `B3`'s traffic
        wants, the same offer `corner_cut_m = 0` and `rocker_top_y_m = sill_y_m`
        make — and a strict `<` on the ring ordering refuses it. The refusal
        cases are all on the far side of the boundary, so only this reaches it."""
        shape = replace(Proportions(), **{field: 0.0})
        body = taxi_body(Chassis(), shape)
        assert body.triangle_count > 0
        areas = np.linalg.norm(body.triangle_cross(), axis=1)
        assert (areas > 1e-9).all()

    def test_the_roof_sign_sits_on_the_roof(self) -> None:
        """It never had a reason to before: the roof was long and the sign was
        near the middle of it. Rake shortens the roof from both ends at once,
        and a sign hanging off the front edge is the kind of thing that renders
        without complaint."""
        shape = Proportions()
        roof = shape.greenhouse_profile[-1]
        assert roof.z_front + roof.cut_m < shape.sign_z_m - shape.sign_half_length_m
        assert shape.sign_z_m + shape.sign_half_length_m < roof.z_rear - roof.cut_m


class TestTheBumperBandAndTheRocker:
    """Where the paint changes on the lower body, all the way round the car.

    ⚠️ The rocker is the **third** dark strip down this flank. A box standing
    proud read as a stick; the bumper band continued at `bumper_top_y_m` covered
    38% of the flank and read as a stripe painted on a toy. This one is paint at
    the sill, and it is on trial — these tests hold its *shape*, not the verdict
    on whether it should be there, which only a render answers.
    """

    @staticmethod
    def _flank_faces(mesh: MeshData, shape: Proportions, colour: Colour) -> np.ndarray:
        """Faces lying in the flank plane and looking out of it, as indices.

        Both halves of that matter. The wheel-well rims start at `x_out` too, so
        selecting on position alone catches dark faces that turn inward — which
        is what first read as a rocker reaching 24 cm above its own ceiling.

        Indices rather than corner coordinates, to match `_faces_of` and so the
        area check can hand them straight to `triangle_cross`.
        """
        faces = _faces_of(mesh, colour)
        corners = mesh.positions[faces]
        on_plane = np.all(np.abs(np.abs(corners[:, :, 0]) - shape.half_width_m) < 1e-9, axis=1)
        outward = np.abs(mesh.normals[faces[:, 0]][:, 0]) > 0.999
        return faces[on_plane & outward]

    def test_one_line_runs_all_the_way_round(self) -> None:
        """⚠️ `rocker_top_y_m` is a hand-copied literal of `bumper_bottom_y_m`,
        exactly as `half_width_m` is one of track/2 + tyre/2. Sharing the line is
        the design: a single break runs unbroken around the car and only what
        sits below it changes — red across the nose and tail, dark along the
        flank. Let the two drift and the corner chamfers grow a visible jog."""
        shape = Proportions()
        assert shape.rocker_top_y_m == pytest.approx(shape.bumper_bottom_y_m, abs=1e-9)

    def test_the_nose_carries_a_red_valance_under_a_dark_bumper(
        self, meshes: list[MeshData]
    ) -> None:
        """The bumper used to run to the bottom of the car. Every reference
        photograph shows the dark band stopping and red bodywork carrying on
        below it, which is the lowest 27% of what used to be solid black.

        Read off the lofted panel rather than off the bounding box: the plate,
        the fog lamps and the badge all face the same way and stand proud of it,
        so `z` has to land on the panel itself to be sampling paint. The panel's
        z is interpolated straight from `lower_profile` rather than through
        `face_inset_m` per corner — that wrapper is one `np.interp`, so calling
        it elementwise rebuilds the profile once per vertex to answer a question
        `np.interp` answers for the whole array at once.
        """
        shape, body = Proportions(), meshes[0]
        ys = [y for _, y, _ in shape.lower_profile]
        insets = [inset for inset, _, _ in shape.lower_profile]
        corners = body.positions[body.triangles]
        panel_z = shape.front_z_m + np.interp(corners[:, :, 1], ys, insets)
        on_panel = np.all(np.abs(corners[:, :, 2] - panel_z) < 1e-9, axis=1)

        bands = {
            "valance": (shape.sill_y_m, shape.bumper_bottom_y_m, RED),
            "bumper": (shape.bumper_bottom_y_m, shape.bumper_top_y_m, DARK),
            "body": (shape.bumper_top_y_m, shape.belt_y_m, RED),
        }
        for label, (low, high, expected) in bands.items():
            inside = np.all(
                (corners[:, :, 1] >= low - 1e-9) & (corners[:, :, 1] <= high + 1e-9), axis=1
            )
            band = select_triangles(body, on_panel & inside)
            assert band is not None, f"the {label} band on the nose has no faces at all"
            assert _rgbs(band) == {expected}, (
                f"the {label} band on the nose is {sorted(_rgbs(band))}"
            )

    def test_the_flank_is_dark_below_the_rocker_and_red_above(self, meshes: list[MeshData]) -> None:
        shape, body = Proportions(), meshes[0]
        dark = body.positions[self._flank_faces(body, shape, DARK)]
        red = body.positions[self._flank_faces(body, shape, RED)]
        # ⚠️ Both selections asserted non-empty before anything is read off them.
        # `_flank_faces` is a strict filter on an exact plane and a normal, and
        # its own docstring records a version that selected the wrong faces —
        # every comparison below is vacuously true against an empty array, and
        # `min`/`max` on one raises numpy's error rather than this file's.
        assert len(dark), "the flank carries no rocker at all"
        assert len(red), "the flank carries no bodywork at all"
        assert dark[:, :, 1].max() == pytest.approx(shape.rocker_top_y_m, abs=1e-9)
        assert dark[:, :, 1].min() == pytest.approx(shape.sill_y_m, abs=1e-9)
        assert red[:, :, 1].min() >= shape.rocker_top_y_m - 1e-9

    def test_the_rocker_stops_at_the_wheel_openings(self, meshes: list[MeshData]) -> None:
        """A sill panel runs between the arches and no further. The arc rises
        above the rocker line for 89% of each opening, so this is mostly a check
        that the columns which *do* dip below it are clipped to the arc rather
        than filled in square."""
        shape, chassis, body = Proportions(), Chassis(), meshes[0]
        dark = body.positions[self._flank_faces(body, shape, DARK)]
        assert len(dark), "the flank carries no rocker at all"
        opening_r = opening_radius_m(chassis, shape)
        for wheel_z in chassis.axle_z_m:
            radial = np.hypot(dark[:, :, 2] - wheel_z, dark[:, :, 1] - chassis.hub_y_m)
            assert radial.min() >= opening_r - 1e-9, (
                f"the rocker intrudes {(opening_r - radial.min()) * 1000:.1f} mm "
                f"into the opening at z={wheel_z:+.2f}"
            )

    def test_the_rocker_is_paint_and_not_a_part(
        self, meshes: list[MeshData], bare_flank: MeshData
    ) -> None:
        """⚠️ The first attempt at a strip down this flank was a box standing
        2-3 cm proud, and it read as a stick. This one may not change the
        silhouette by so much as a sliver — it is the same flank, cut in two
        colours — so the flank with the rocker has to cover exactly the area the
        flank without it does.

        ⚠️ **Area on its own would not have caught the bug this was written for.**
        Clamping the dark band to the rocker line instead of cutting the stretch
        at it pushed one triangle into the wheel opening and pulled an identical
        one out of the bodywork: two triangles on the same base, so the total
        came out to the millimetre and the outline was wrong. What found it is
        `test_the_rocker_stops_at_the_wheel_openings`, and the two are only
        worth anything together.
        """
        shape = Proportions()

        def flank_area(mesh: MeshData) -> float:
            faces = np.concatenate(
                [self._flank_faces(mesh, shape, colour) for colour in (RED, DARK)]
            )
            return float(np.linalg.norm(triangle_cross(mesh.positions, faces), axis=1).sum() / 2.0)

        painted = flank_area(meshes[0])
        # ⚠️ The positive control, and it is not decoration. `flank_area` sums
        # over a strict selector, so a selector that matches nothing returns 0.0
        # for both meshes and the comparison below becomes `0.0 == 0.0`. This is
        # the one new test whose whole assertion collapses that way.
        assert painted > 0.0, "no flank faces were selected, so the areas are both zero"
        assert painted == pytest.approx(flank_area(bare_flank), abs=1e-9)

    def test_setting_the_rocker_to_the_sill_removes_it_entirely(
        self, meshes: list[MeshData], bare_flank: MeshData
    ) -> None:
        """The escape hatch, and `B3`'s traffic cars want it — the same offer
        `corner_cut_m = 0` makes. It has to leave *no* dark faces rather than
        zero-height ones, which would be degenerate triangles paid for in full."""
        shape = replace(Proportions(), rocker_top_y_m=Proportions().sill_y_m)
        assert len(self._flank_faces(bare_flank, shape, DARK)) == 0
        # Same positive control as above: without it, a broken selector reports
        # the rocker successfully removed from a car it never found.
        assert len(self._flank_faces(bare_flank, shape, RED)), "the flank itself went missing"
        assert bare_flank.triangle_count < meshes[0].triangle_count


class TestTheDoorHandles:
    """Placed from the doors' trailing edges, which is what the cabin moved.

    They were `cabin_mid_z_m` +/- a flat 0.42, and that held only while the cabin
    stayed the length it was first written at. Raking the backlight was paid for
    by carrying `cabin_rear_z_m` back to the rear axle, and the rear handle went
    with it — 130 mm out over the wheel opening, floating above a tyre.
    """

    @staticmethod
    def _handle_spans(mesh: MeshData, shape: Proportions) -> list[tuple[float, float]]:
        """(min z, max z) of each handle on the right flank, front to back.

        Read off the mesh rather than recomputed. The cant rail is SILVER too, so
        the belt line separates trim from handles; one side is enough, and taking
        one keeps the two boxes apart instead of pooling four.
        """
        corners = mesh.positions[_faces_of(mesh, SILVER)]
        keep = np.all(corners[:, :, 1] < shape.belt_y_m, axis=1) & np.all(
            corners[:, :, 0] > 0.0, axis=1
        )
        corners = corners[keep]
        if not len(corners):
            return []
        # Split at the widest gap between faces, so the count comes out of the
        # geometry rather than being assumed to be two. The extents are then the
        # corners themselves — a box's face centres already reach its ends, so
        # padding them by a half-length measures it half again as long.
        centres = corners[:, :, 2].mean(axis=1)
        gaps = np.diff(np.sort(centres))
        cut = (
            np.sort(centres)[int(np.argmax(gaps)) + 1]
            if len(gaps) and gaps.max() > 2.0 * shape.handle_half_length_m
            else None
        )
        groups = [corners] if cut is None else [corners[centres < cut], corners[centres >= cut]]
        return [(float(g[:, :, 2].min()), float(g[:, :, 2].max())) for g in groups if len(g)]

    def test_the_car_carries_two_handles_a_side(self, meshes: list[MeshData]) -> None:
        """⚠️ The count is the test. Pooling every SILVER face and taking one
        global `min` — which is what the clearance check below used to do — is
        satisfied by the *front* handle alone, because it clears both axles by
        over a metre. Deleting the rear handle outright left that green, and the
        rear handle is the one this whole change exists for."""
        assert len(self._handle_spans(meshes[0], Proportions())) == 2

    def test_both_handles_clear_both_wheel_openings(self, meshes: list[MeshData]) -> None:
        shape, chassis = Proportions(), Chassis()
        spans = self._handle_spans(meshes[0], shape)
        assert len(spans) == 2, "expected a front and a rear handle"
        opening_r = opening_radius_m(chassis, shape)
        for i, (low, high) in enumerate(spans):
            for wheel_z in chassis.axle_z_m:
                clear = min(abs(low - wheel_z), abs(high - wheel_z))
                assert clear >= opening_r, (
                    f"handle {i} spans {low:+.3f}..{high:+.3f} and overhangs "
                    f"the opening at z={wheel_z:+.2f}"
                )

    def test_each_handle_sits_wholly_on_the_door_it_belongs_to(
        self, meshes: list[MeshData]
    ) -> None:
        """⚠️ Read off the mesh, and read as *extents*. This asserted an
        inequality over numbers it had derived itself — it recomputed both
        `_rear_door_z_m`'s expression and the handle's own placement, then
        checked one against the other, so changing `- handle_inset_m` to `+` in
        the generator left it green. It also checked the box's centre, which a
        handle deeper than `handle_inset_m` overhangs its door edge while
        passing."""
        shape, chassis = Proportions(), Chassis()
        doors = {
            "front": (shape.cabin_front_z_m, shape.cabin_mid_z_m),
            "rear": (shape.cabin_mid_z_m, _rear_door_z_m(chassis, shape)),
        }
        spans = self._handle_spans(meshes[0], shape)
        assert len(spans) == len(doors)
        for (door, (leading, trailing)), (low, high) in zip(doors.items(), spans, strict=True):
            assert leading < low and high < trailing, (
                f"the {door} handle spans {low:+.3f}..{high:+.3f}, "
                f"outside its door at {leading:+.3f}..{trailing:+.3f}"
            )

    @pytest.mark.parametrize(
        "shape",
        [
            replace(Proportions(), well_clearance_m=0.65),
            replace(Proportions(), cabin_front_z_m=-0.20, cabin_rear_z_m=2.00),
        ],
        ids=["a wide opening", "a cabin pushed back"],
    )
    def test_a_rear_door_ahead_of_the_front_one_is_refused(self, shape: Proportions) -> None:
        """⚠️ A wide enough opening drags the arch ahead of `cabin_mid_z_m` and
        the "rear" handle lands on the front door — two SILVER boxes overlapping
        by 135 mm and z-fighting, measured at `well_clearance_m = 0.65`.
        Reachable rather than theoretical: `cabin_rear_z_m` moved 1.00 -> 1.25 to
        buy the backlight its rake, and rake is paid for out of cabin length.

        Refused rather than clamped, because clamping the door back far enough to
        separate the boxes carries the rear handle onto the arch instead — one
        defect for another, with nothing reported either way."""
        with pytest.raises(ValueError, match="no room for a handle"):
            _rear_door_z_m(Chassis(), shape)


class TestWinding:
    """Every face points out of the solid it belongs to."""

    @staticmethod
    def _outward_fraction(mesh: MeshData) -> float:
        centre = mesh.positions.mean(axis=0)
        face_normals = mesh.normals[mesh.triangles[:, 0]]
        return float((((mesh.triangle_centroids() - centre) * face_normals).sum(axis=1) > 0).mean())

    def test_a_box_faces_outward(self) -> None:
        assert self._outward_fraction(box((-1, -1, -1), (1, 1, 1), RED, name="b")) == 1.0

    def test_the_wheel_faces_outward(self) -> None:
        """The bug this caught: wound the other way, every normal points at the
        axle and the wheel renders as a hole."""
        assert self._outward_fraction(_wheel(0.35, 0.2, 12, name="w")) == 1.0

    def test_no_triangle_is_degenerate(self, meshes: list[MeshData]) -> None:
        """Zero-area triangles cost index bytes and carry no normal."""
        for mesh in meshes:
            areas = np.linalg.norm(mesh.triangle_cross(), axis=1)
            assert (areas > 1e-9).all(), f"{mesh.name} has {(areas <= 1e-9).sum()} degenerate"

    def test_a_face_with_no_area_is_refused_rather_than_written(self) -> None:
        with pytest.raises(ValueError, match="collinear or coincident"):
            polygon([(0, 0, 0), (1, 0, 0), (2, 0, 0)], RED, name="flat")


class TestTaxiContract:
    """What `ART_DESIGN.md` asks of a vehicle, and `write_glb` of a mesh."""

    def test_the_two_meshes_are_body_and_wheel(self, meshes: list[MeshData]) -> None:
        """One material each, which is what `ART_DESIGN.md` budgets. There used
        to be a third — a decal sheet carrying the roof lettering, the plate
        characters and the 4 SEATS badge — and its own docstring called it a
        deliberate exception. Nothing on the car is text now, so the exception
        is closed rather than merely unused."""
        assert [mesh.name for mesh in meshes] == ["taxi_body", "taxi_tyre"]

    def test_nothing_on_the_taxi_is_textured(self, meshes: list[MeshData]) -> None:
        """The city is flat-shaded vertex colour throughout, and a textured car
        driving through it is the one surface that would not belong.

        ⚠️ **This used to assert `uvs is None` as well, and that was the same
        conflation `P3-7` untangled on the tiles**: UVs without a texture are a
        different question, because a coordinate meant for a *shader* is not a
        coordinate meant for an image. The body carries a surface marker in
        `UV.y` now — see `TestSurfaceMarkers`. The texture half of the guard is
        unchanged and still catches the case it was written for, and the wheel,
        which asks for no shader, still carries no UVs at all."""
        for mesh in meshes:
            assert mesh.texture is None, f"{mesh.name} carries a texture"
        assert meshes[1].uvs is None, "the wheel needs no shader payload"

    def test_within_the_triangle_ceiling(self, meshes: list[MeshData]) -> None:
        """Counted as the scene instances it: one body, four wheels."""
        body, wheel = meshes
        assert body.triangle_count + 4 * wheel.triangle_count <= TRIANGLE_CEILING

    def test_every_vertex_is_coloured(self, meshes: list[MeshData]) -> None:
        """An uncoloured vertex renders at whatever the attribute defaults to."""
        for mesh in meshes:
            assert mesh.colours is not None
            assert len(mesh.colours) == len(mesh.positions)

    def test_the_palette_is_the_declared_colours(self, meshes: list[MeshData]) -> None:
        """`ART_DESIGN.md` asks for 3-5; this is eight. All three extras are
        deliberate: AMBER because the tail cluster stacks three lenses and two
        colours cannot express three, BADGE_GREEN because the 4 SEATS badge
        stopped being a texture and a green dome is the whole of what is left
        of it, and DEEP_RED because the high-level brake lamp has to vanish
        against the glazing it sits on and RED cannot. The assertion is that
        nothing *else* creeps in."""
        used = set().union(*(_rgbs(mesh) for mesh in meshes))
        assert used <= set(PALETTE), f"unexpected colour: {sorted(used - set(PALETTE))}"

    def test_the_body_clears_the_ground(self, meshes: list[MeshData]) -> None:
        """A sill below the contact patch would drag through the road surface."""
        low, _ = meshes[0].aabb()
        assert low[1] > Chassis().ground_y_m

    def test_the_taxi_faces_negative_z(self) -> None:
        """Godot's forward is -Z, and the plates are what prove the car is not
        mirrored: Hong Kong follows the UK and runs a white plate at the front
        and a yellow one at the rear, so colour and z together tell the two ends
        apart. The earlier version of this test asserted the body's bounds were
        roughly *symmetric*, which is true of any centred box facing either way
        and caught nothing.

        Read off `_plates` rather than off the merged body, because once the
        plates are flat-coloured boxes their colours are shared with the lamps
        at both ends and nothing in the merged mesh can pick them out again."""
        front, rear = _plates(Proportions())
        for plate, colour, expected_sign in ((front, LAMP, -1.0), (rear, AMBER, 1.0)):
            # The whole set, not its first row: a plate that picked up a second
            # colour would still pass if the smaller row happened to match.
            assert _rgbs(plate) == {colour}, plate.name
            assert np.sign(plate.positions[:, 2]).mean() == expected_sign, (
                f"{plate.name} is on the wrong end"
            )


class TestSurfaceMarkers:
    """The `TEXCOORD_0` payload `vehicle_body.gdshader` reads (`P3-11c`).

    Every failure this class covers is silent in the engine. A missing material
    name leaves the body on its imported `BaseMaterial3D` and the car simply
    renders as it did before; a marker that is not an exact integer sends
    `floor()` to the wrong surface and shades a door like a windscreen. Godot
    reports neither, and no verify tool covers vehicles.
    """

    @staticmethod
    def _markers(body: MeshData) -> np.ndarray:
        assert body.uvs is not None, "the body carries no shader payload"
        return body.uvs[:, 1]

    def test_the_body_asks_for_its_shader_by_name(self, meshes: list[MeshData]) -> None:
        """The only channel glTF offers. Without it `generated_scene_import.gd`
        matches nothing, the body keeps its `BaseMaterial3D`, and the car looks
        exactly like the one that shipped before the shader existed — which is
        why this is asserted rather than left to a render."""
        body, wheel = meshes
        assert body.material == BODY_MATERIAL
        assert wheel.material is None, "the wheel asks for no shader"

    def test_every_marker_is_an_exact_integer(self, meshes: list[MeshData]) -> None:
        """`floor(UV.y)` is the surface marker, so a value of 0.999 reads as
        paint and 1.0001 reads as glass. Nothing interpolates here — each part
        is stamped whole before the merge — and this is what proves it."""
        markers = self._markers(meshes[0])
        assert np.array_equal(markers, np.floor(markers))
        assert set(markers.tolist()) <= {MARKER_PAINT, MARKER_GLASS, MARKER_LAMP, MARKER_TRIM}

    def test_the_glazing_is_exactly_the_glass_coloured_vertices(
        self, meshes: list[MeshData]
    ) -> None:
        """`GLASS` names one material and nothing else wears it, so here the
        colour rule is exact — and it has to be per-vertex, because the
        greenhouse is one lofted part carrying both `GLASS` and `SILVER`."""
        body = meshes[0]
        assert body.colours is not None
        glass = np.all(body.colours[:, :3] == np.array(GLASS, dtype=np.uint8), axis=1)
        assert glass.any(), "no glazing on the car"
        assert np.array_equal(self._markers(body) == MARKER_GLASS, glass)

    def test_the_tail_lens_is_a_lamp_although_it_is_painted_red(
        self, meshes: list[MeshData]
    ) -> None:
        """The reason the name rule exists at all. The bottom lens of the tail
        cluster is `RED` on `RED` bodywork with no bezel behind it — which is
        exactly why `ART_DESIGN.md` records the cluster reading as
        "amber-over-white with a bump where the red should be" — so no colour
        rule can pick it out of the panel it sits in."""
        body = meshes[0]
        assert body.colours is not None
        red = np.all(body.colours[:, :3] == np.array(RED, dtype=np.uint8), axis=1)
        assert (red & (self._markers(body) == MARKER_LAMP)).any(), (
            "the red tail lens is being marked as bodywork"
        )

    def test_the_plates_and_the_roof_sign_are_not_lenses(self, meshes: list[MeshData]) -> None:
        """⚠️ **The regression this design was corrected for.** The first pass
        marked by colour alone, and `LAMP` and `AMBER` are also the front and
        rear registration plates and the roof sign — so a matte plate was being
        handed a lens's gloss. Colour is not materiality, which is the same
        collision `Q43` records on the facades under two predicates wearing one
        name."""
        body = meshes[0]
        assert body.colours is not None
        markers = self._markers(body)
        for colour, name in ((LAMP, "LAMP"), (AMBER, "AMBER")):
            worn = np.all(body.colours[:, :3] == np.array(colour, dtype=np.uint8), axis=1)
            assert (markers[worn] == MARKER_PAINT).any(), (
                f"every {name} vertex is marked as a lens — the plates are being over-marked"
            )


class TestLampCircuits:
    """Which lamps switch, and on what (`P3-11d`).

    `UV.x` carries the circuit; `vehicle_lamps.gd` decides which circuits are
    live and `vehicle_body.gdshader` lights them. Every failure here is silent
    in exactly the way `TestSurfaceMarkers` describes, with one addition that is
    worse: `CIRCUIT_NONE` is a *valid* value meaning "never lights", so a lens
    that loses its wiring ships a well-formed file, imports clean, renders, and
    is simply dark. Nothing but a graded frame would notice.
    """

    @staticmethod
    def _circuits(body: MeshData) -> np.ndarray:
        assert body.uvs is not None, "the body carries no shader payload"
        return body.uvs[:, 0]

    @classmethod
    def _assert_cluster(
        cls, body: MeshData, circuit: float, colours: set[Colour], *, front: bool
    ) -> None:
        """Assert a circuit's lenses sit on one end of the car, wear exactly
        `colours`, and span the centreline.

        Shared because the two ends ask the identical three questions, and the
        one that matters is the *end*: the front and rear both carry a white
        `LAMP` lens, so a circuit wired to the wrong cluster still renders a car
        whose lamps light. Only the sign on `z` separates them.
        """
        assert body.colours is not None
        on = cls._circuits(body) == circuit
        z = body.positions[on, 2]
        at_end = np.all(z < 0.0) if front else np.all(z > 0.0)
        assert at_end, f"circuit {circuit} is not at the {'front' if front else 'rear'}"
        worn = _rgbs(body, on)
        assert worn == colours, f"circuit {circuit} wears {sorted(worn)}"
        assert body.positions[on, 0].min() < 0.0 < body.positions[on, 0].max(), (
            f"circuit {circuit} is only on one side of the car"
        )

    def test_every_circuit_is_an_exact_integer(self, meshes: list[MeshData]) -> None:
        """The shader indexes a `vec4` with `int(UV.x) - 1`, so 2.9999 selects
        the brake channel for a reverse lens and no interpolation error is
        recoverable downstream. Each part is stamped whole before the merge."""
        circuits = self._circuits(meshes[0])
        assert np.array_equal(circuits, np.floor(circuits))
        assert set(circuits.tolist()) <= {
            CIRCUIT_NONE,
            CIRCUIT_BRAKE,
            CIRCUIT_REVERSE,
            CIRCUIT_INDICATOR_L,
            CIRCUIT_INDICATOR_R,
            CIRCUIT_SIDELAMP,
            CIRCUIT_HEADLAMP,
        }

    def test_no_circuit_outruns_the_shader_payload(self, meshes: list[MeshData]) -> None:
        """⚠️ **The bound the shader cannot hold on its own.** `vehicle_body`
        carries the circuits in two `vec4`s and refuses to index past the
        eighth — so a ninth added here does not fail, or warn, or render wrong:
        it takes the `CIRCUIT_NONE` branch and the lens is simply dark for ever,
        which is the silent failure `TestLampCircuits` exists for. Widening the
        payload means adding a third `instance uniform` and raising this."""
        assert self._circuits(meshes[0]).max() <= 8.0

    def test_every_circuit_reaches_the_car(self, meshes: list[MeshData]) -> None:
        """A circuit the shader can switch and no vertex answers to is a lamp
        that never lights, and `vehicle_lamps.gd` cannot tell the difference —
        it writes the same four floats either way."""
        present = set(self._circuits(meshes[0]).tolist())
        for circuit in set(LAMP_CIRCUITS.values()):
            assert circuit in present, f"circuit {circuit} is wired to no geometry"

    def test_only_a_lens_is_ever_switched(self, meshes: list[MeshData]) -> None:
        """⚠️ The shader only reads `UV.x` inside its `MARKER_LAMP` branch, so a
        circuit stamped on bodywork is invisible until someone moves that read —
        at which point a door panel starts flashing amber. Held here instead."""
        body = meshes[0]
        assert body.uvs is not None
        switched = self._circuits(body) != CIRCUIT_NONE
        assert np.all(body.uvs[switched, 1] == MARKER_LAMP)

    def test_the_indicators_are_split_left_from_right(self, meshes: list[MeshData]) -> None:
        """⚠️ **The one failure that still looks like a working feature.** One
        amber circuit lights both flanks, which is a hazard warning rather than a
        turn — and a swapped pair signals the opposite of where the car is going.
        Neither reads as a bug in a screenshot, so it is arithmetic here: `-Z` is
        forward, so the car's right is `+X`."""
        body = meshes[0]
        circuits = self._circuits(body)
        x = body.positions[:, 0]
        assert np.all(x[circuits == CIRCUIT_INDICATOR_L] < 0.0)
        assert np.all(x[circuits == CIRCUIT_INDICATOR_R] > 0.0)

    def test_the_front_circuits_are_all_at_the_front(self, meshes: list[MeshData]) -> None:
        """The mirror of the rear test below, and it catches the one mistake the
        naming invites: `foglamp_*` is switched as the *position* lamp, so a
        reader tidying `LAMP_CIRCUITS` by moving it to the tail cluster — where
        the other white lens lives — would light the back of the car when the
        light drops. Both circuits span the centreline, because neither is split
        left from right: a one-sided white lamp is a blown bulb, not a signal."""
        for circuit in (CIRCUIT_SIDELAMP, CIRCUIT_HEADLAMP):
            self._assert_cluster(meshes[0], circuit, {LAMP}, front=True)

    def test_the_side_lamps_sit_below_the_main_beams(self, meshes: list[MeshData]) -> None:
        """⚠️ **The two front circuits are two different lamps, and this is what
        says so.** They are the same colour on the same face of the same car, so
        wiring both to one pair of lenses would render as a working feature —
        the nose lights up either way — and the whole point of the pair is that
        "shade" and "no sky" are visibly different states. Height separates them:
        `taxi_body` puts the main beam in the cluster and the side lamp low in
        the bumper band, so nothing overlaps."""
        body = meshes[0]
        circuits = self._circuits(body)
        side = body.positions[circuits == CIRCUIT_SIDELAMP, 1]
        head = body.positions[circuits == CIRCUIT_HEADLAMP, 1]
        assert side.max() < head.min(), "the side lamps and the main beams overlap in height"

    def test_the_brake_and_reverse_lenses_are_all_at_the_rear(self, meshes: list[MeshData]) -> None:
        """Every lens on either circuit is behind the car's middle and spans both
        sides of its centreline. The colour half is the interesting one: the
        outer brake lens is `RED`, which is why it needed a circuit at all — it
        is `RED` on `RED` bodywork and `P3-11c` measured shading alone as not
        enough to separate it. Lighting the authored colour is the fix that
        recolours nothing. `DEEP_RED` is the high-level strip, which is the
        opposite problem: it has to vanish when the circuit is out."""
        wanted = {CIRCUIT_BRAKE: {RED, DEEP_RED}, CIRCUIT_REVERSE: {LAMP}}
        for circuit, colours in wanted.items():
            self._assert_cluster(meshes[0], circuit, colours, front=False)

    def test_the_high_level_lamp_sits_in_the_backlight(self, meshes: list[MeshData]) -> None:
        """⚠️ **Seated against a raked surface, and both failures are silent.**
        Too far back and it floats off the glass on a stalk; too far forward and
        it sinks into it, which at this rake happens to the top edge alone — so
        the lamp is still visible, just half as tall as it was authored, and no
        count or bound reports it.

        Held against the backlight plane the greenhouse actually builds, so a
        change to `backlight_rake_deg` or `cabin_rear_z_m` moves both sides of
        this together instead of stranding the lamp behind the window."""
        shape = Proportions()
        lamp = _high_brake_lamp(shape)
        low, high = lamp.aabb()

        band = (shape.belt_y_m, shape.glass_top_y_m)
        assert band[0] < low[1] and high[1] < band[1], "the lamp is not inside the glazed band"

        # The plane at each edge of the lamp, from the same rake the loft uses.
        plane_at_top = shape.cabin_ends_m(high[1] - shape.belt_y_m)[1]
        plane_at_bottom = shape.cabin_ends_m(low[1] - shape.belt_y_m)[1]
        assert low[2] == pytest.approx(plane_at_top), "the lamp's back does not reach the glass"
        assert high[2] == pytest.approx(plane_at_bottom + FIXTURE_PROUD_M), (
            "the lamp does not stand clear of the glass along its whole height"
        )

    def test_a_renamed_lamp_is_refused_rather_than_shipped_dark(self) -> None:
        """`_check_wiring` is the guard, and it runs in the generator rather than
        only here: the person who renames a part is the person regenerating the
        `.glb`, and `pytest` is a separate step a regenerate does not require."""
        parts = [box((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), RED, name=n) for n in LAMP_CIRCUITS]
        _check_wiring(parts)
        with pytest.raises(ValueError, match="wired to nothing"):
            _check_wiring(parts[1:])
