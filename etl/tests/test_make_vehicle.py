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
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest
from make_vehicle import (
    AMBER,
    BADGE_GREEN,
    DARK,
    FIXTURE_PROUD_M,
    GLASS,
    LAMP,
    RED,
    SILVER,
    Chassis,
    Colour,
    Proportions,
    _badge,
    _box,
    _flush_fixture,
    _plates,
    _polygon,
    _wheel,
    build_taxi,
    write_taxi,
)

from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
TAXI_SCENE = ROOT / "game" / "scenes" / "vehicle" / "taxi.tscn"
HANDLING = ROOT / "game" / "tuning" / "handling.tres"
SHIPPED = ROOT / "game" / "assets" / "authored" / "vehicles"

# `ART_DESIGN.md`'s ceiling for one vehicle.
TRIANGLE_CEILING = 2000
PALETTE = (RED, SILVER, DARK, GLASS, LAMP, AMBER, BADGE_GREEN)


def _rgbs(mesh: MeshData) -> set[Colour]:
    """Every distinct colour on a mesh, as plain int tuples.

    `np.unique` returns rows of `np.uint8`, which compare unequal to the plain
    tuples in `PALETTE` unless converted — and indexing `[0]` to dodge that is
    what let a two-coloured plate pass an equality check.
    """
    assert mesh.colours is not None, f"{mesh.name} carries no colours"
    return {
        tuple(int(channel) for channel in rgb) for rgb in np.unique(mesh.colours[:, :3], axis=0)
    }


def _tres_float(text: str, field: str) -> float:
    match = re.search(rf"^{field} = ([\d.]+)$", text, flags=re.MULTILINE)
    assert match is not None, f"{field} is gone from handling.tres"
    return float(match.group(1))


def _mount_resource_id(scene: str) -> str:
    """The ExtResource id the scene gave `wheel_mount.gd`.

    Resolved from the script path rather than hardcoded, because Godot
    renumbers these ids on an editor save and a stale literal would quietly
    select no nodes at all — leaving the desync guard passing over nothing.
    """
    match = re.search(r'\[ext_resource [^\]]*wheel_mount\.gd" id="([^"]+)"\]', scene)
    assert match is not None, "no ext_resource for wheel_mount.gd in taxi.tscn"
    return match.group(1)


def _marker_origins(scene: str) -> dict[str, tuple[float, float, float]]:
    """Every `WheelMount` in the scene, by node name, as its xyz origin.

    A `Transform3D` is nine basis floats then three origin floats; the mounts
    are unrotated, so only the last three carry chassis information.
    """
    wanted = _mount_resource_id(scene)
    origins: dict[str, tuple[float, float, float]] = {}
    for block in re.split(r"^\[node ", scene, flags=re.MULTILINE)[1:]:
        name = re.match(r'name="([^"]+)"', block)
        transform = re.search(r"transform = Transform3D\(([^)]*)\)", block)
        if name is None or transform is None:
            continue
        if not re.search(rf'script = ExtResource\("{re.escape(wanted)}"\)', block):
            continue
        values = [float(part) for part in transform.group(1).split(",")]
        origins[name.group(1)] = (values[-3], values[-2], values[-1])
    return origins


@pytest.fixture(scope="module")
def scene_chassis() -> Chassis:
    """The chassis as the *shipped scene and profile* describe it."""
    origins = _marker_origins(TAXI_SCENE.read_text())
    assert len(origins) == 4, f"expected four WheelMounts, found {sorted(origins)}"

    xs = sorted({round(origin[0], 4) for origin in origins.values()})
    zs = sorted({round(origin[2], 4) for origin in origins.values()})
    assert len(xs) == 2 and len(zs) == 2, f"mounts are not a rectangle: {origins}"

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
        """`wheel_visual.gd` takes its rest offset from the profile, so no wheel
        mesh may carry one of its own. A scene copy would hover or sink the
        moment the spring is retuned, with the physics unchanged."""
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

    def test_none_of_them_reaches_below_the_sill_tuck(self) -> None:
        """⚠️ Where the body folds in hard, `_seated_depth` answers correctly
        and the answer looks wrong: a fixture spanning the fold is made deep
        enough to bridge it, so it stands 4 cm off the paint at its bottom edge
        and hangs below the car's own outline. The badge did exactly that. The
        fix is placement, not depth, and this is what holds the placement."""
        shape = Proportions()
        fold = shape.sill_y_m + shape.bevel_m
        for seat in self._fixtures(shape):
            low, _ = seat.mesh.aabb()
            assert low[1] >= fold, f"{seat.mesh.name} reaches into the sill tuck"

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


class TestWinding:
    """Every face points out of the solid it belongs to."""

    @staticmethod
    def _outward_fraction(mesh: MeshData) -> float:
        centre = mesh.positions.mean(axis=0)
        face_normals = mesh.normals[mesh.triangles[:, 0]]
        return float((((mesh.triangle_centroids() - centre) * face_normals).sum(axis=1) > 0).mean())

    def test_a_box_faces_outward(self) -> None:
        assert self._outward_fraction(_box((-1, -1, -1), (1, 1, 1), RED, name="b")) == 1.0

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
            _polygon([(0, 0, 0), (1, 0, 0), (2, 0, 0)], RED, name="flat")


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
        driving through it is the one surface that would not belong."""
        for mesh in meshes:
            assert mesh.texture is None, f"{mesh.name} carries a texture"
            assert mesh.uvs is None, f"{mesh.name} carries UVs"

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
        """`ART_DESIGN.md` asks for 3-5; this is seven. Both extras are
        deliberate: AMBER because the tail cluster stacks three lenses and two
        colours cannot express three, BADGE_GREEN because the 4 SEATS badge
        stopped being a texture and a green dome is the whole of what is left
        of it. The assertion is that nothing *else* creeps in."""
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
