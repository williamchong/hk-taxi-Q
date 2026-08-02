"""The `P3-11` vehicle generator (`tools/make_vehicle.py`).

Three kinds of test, and the first is the reason this file exists.

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
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest
from make_vehicle import (
    AMBER,
    DARK,
    GLASS,
    LAMP,
    RED,
    SILVER,
    Chassis,
    Proportions,
    _box,
    _polygon,
    _wheel,
    build_taxi,
    write_taxi,
)
from vehicle_decals import build_sheet

from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
TAXI_SCENE = ROOT / "game" / "scenes" / "vehicle" / "taxi.tscn"
HANDLING = ROOT / "game" / "tuning" / "handling.tres"
SHIPPED = ROOT / "game" / "assets" / "authored" / "vehicles"

# `ART_DESIGN.md`'s ceiling for one vehicle.
TRIANGLE_CEILING = 2000
PALETTE = (RED, SILVER, DARK, GLASS, LAMP, AMBER)


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


class TestDecals:
    """The sheet and the quads that carry it."""

    def test_the_sheet_is_a_valid_png(self) -> None:
        png, _ = build_sheet(sign_face=LAMP, bumper_face=DARK)
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert png.endswith(b"IEND\xaeB`\x82")

    def test_every_patch_is_inside_the_sheet(self) -> None:
        """An out-of-range rect samples a neighbouring decal, not empty space."""
        _, patches = build_sheet(sign_face=LAMP, bumper_face=DARK)
        for key, patch in patches.items():
            u0, v0, u1, v1 = patch.uv()
            assert 0.0 <= u0 < u1 <= 1.0, key
            assert 0.0 <= v0 < v1 <= 1.0, key

    def test_no_two_patches_overlap(self) -> None:
        """Overlapping rects put one decal's ink inside another's texture."""
        _, patches = build_sheet(sign_face=LAMP, bumper_face=DARK)
        items = list(patches.values())
        for i, a in enumerate(items):
            for b in items[i + 1 :]:
                apart = a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y
                assert apart, f"{a} overlaps {b}"

    def test_text_too_wide_for_its_patch_is_refused(self) -> None:
        """`_text` writes straight into the sheet array. Without a bound it
        would silently scribble across whatever patch sits alongside."""
        with pytest.raises(ValueError, match="does not fit"):
            build_sheet(sign_face=LAMP, bumper_face=DARK, plate="HK 0521 0521 0521")

    def test_the_roof_sign_decal_stands_proud_of_the_sign(self, meshes: list[MeshData]) -> None:
        """⚠️ Both roof-sign quads once sat at x = 0 — inside the sign solid and
        coincident with each other — so the TAXI lettering was invisible. It
        rendered, imported and passed every check in that state.

        Asserted as "outside the solid" rather than "clear along x", so it still
        holds whichever face the lettering is moved to. The first version of
        this test pinned the axis and failed the moment the sign turned to face
        fore and aft, which is a test describing an implementation rather than
        the property that matters.
        """
        shape = Proportions()
        decal = meshes[2]
        on_sign = decal.positions[decal.positions[:, 1] > shape.roof_y_m]
        assert len(on_sign) > 0, "no decal sits on the roof sign"

        within_x = np.abs(on_sign[:, 0]) <= shape.sign_half_width_m
        within_z = np.abs(on_sign[:, 2] - shape.sign_z_m) <= shape.sign_half_length_m
        assert not (within_x & within_z).any(), "a roof-sign decal is buried in the sign"


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

    def test_the_three_meshes_are_body_wheel_and_decal(self, meshes: list[MeshData]) -> None:
        """One material each. Two would meet `ART_DESIGN.md`; the third is the
        decal sheet, taken deliberately because plates and the 4 SEATS badge are
        text and no triangle count reaches them."""
        assert [mesh.name for mesh in meshes] == ["taxi_body", "taxi_tyre", "taxi_decal"]

    def test_within_the_triangle_ceiling(self, meshes: list[MeshData]) -> None:
        """Counted as the scene instances it: one body, four wheels, one decal."""
        body, wheel, decal = meshes
        in_scene = body.triangle_count + 4 * wheel.triangle_count + decal.triangle_count
        assert in_scene <= TRIANGLE_CEILING

    def test_every_untextured_vertex_is_coloured(self, meshes: list[MeshData]) -> None:
        """An uncoloured vertex renders at whatever the attribute defaults to.
        The decal sheet is the exception: it carries UVs and a texture instead."""
        for mesh in meshes:
            if mesh.texture is not None:
                assert mesh.uvs is not None and len(mesh.uvs) == len(mesh.positions)
                continue
            assert mesh.colours is not None
            assert len(mesh.colours) == len(mesh.positions)

    def test_the_palette_is_the_declared_colours(self, meshes: list[MeshData]) -> None:
        """`ART_DESIGN.md` asks for 3-5; this is six. AMBER is the deliberate
        extra — the tail cluster stacks three lenses and two colours cannot
        express three. The assertion is that nothing *else* creeps in."""
        used = {
            tuple(rgb)
            for mesh in meshes
            if mesh.colours is not None
            for rgb in np.unique(mesh.colours[:, :3], axis=0)
        }
        assert used <= set(PALETTE), f"unexpected colour: {sorted(used - set(PALETTE))}"

    def test_the_body_clears_the_ground(self, meshes: list[MeshData]) -> None:
        """A sill below the contact patch would drag through the road surface."""
        low, _ = meshes[0].aabb()
        assert low[1] > Chassis().ground_y_m

    def test_the_taxi_faces_negative_z(self, meshes: list[MeshData]) -> None:
        """Godot's forward is -Z, and the plates are what prove the car is not
        mirrored: Hong Kong runs a white plate at the front and a yellow one at
        the rear, so their z tells the two ends apart. The earlier version of
        this test asserted the body's bounds were roughly *symmetric*, which is
        true of any centred box facing either way and caught nothing."""
        decal = meshes[2]
        _, patches = build_sheet(sign_face=LAMP, bumper_face=DARK)
        sheet_v = {key: patch.uv()[1] for key, patch in patches.items()}
        for key, expected_sign in (("plate_front", -1.0), ("plate_rear", 1.0)):
            rows = np.isclose(decal.uvs[:, 1], sheet_v[key]) | np.isclose(
                decal.uvs[:, 1], patches[key].uv()[3]
            )
            zs = decal.positions[rows][:, 2]
            assert len(zs) > 0, f"no {key} decal found"
            assert np.sign(zs).mean() == expected_sign, f"{key} is on the wrong end"
