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

from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
TAXI_SCENE = ROOT / "game" / "scenes" / "vehicle" / "taxi.tscn"
HANDLING = ROOT / "game" / "tuning" / "handling.tres"
SHIPPED = ROOT / "game" / "assets" / "authored" / "vehicles"

# `ART_DESIGN.md`'s ceiling for one vehicle.
TRIANGLE_CEILING = 2000
PALETTE = (RED, SILVER, DARK, GLASS, LAMP)


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

    def test_two_meshes_so_two_materials(self, meshes: list[MeshData]) -> None:
        """`write_glb` writes one material per mesh, and the spec allows 1-2."""
        assert [mesh.name for mesh in meshes] == ["taxi_body", "taxi_wheel"]

    def test_within_the_triangle_ceiling(self, meshes: list[MeshData]) -> None:
        """Counted as the scene instances it: one body and four wheels."""
        body, wheel = meshes
        assert body.triangle_count + 4 * wheel.triangle_count <= TRIANGLE_CEILING

    def test_every_vertex_is_coloured(self, meshes: list[MeshData]) -> None:
        """An uncoloured vertex renders at whatever the attribute defaults to."""
        for mesh in meshes:
            assert mesh.colours is not None
            assert len(mesh.colours) == len(mesh.positions)

    def test_the_palette_is_the_five_declared_colours(self, meshes: list[MeshData]) -> None:
        """`ART_DESIGN.md` asks for 3-5 flat colours per vehicle."""
        used = {tuple(rgb) for mesh in meshes for rgb in np.unique(mesh.colours[:, :3], axis=0)}
        assert used <= set(PALETTE)
        assert len(used) <= 5

    def test_the_body_clears_the_ground(self, meshes: list[MeshData]) -> None:
        """A sill below the contact patch would drag through the road surface."""
        low, _ = meshes[0].aabb()
        assert low[1] > Chassis().ground_y_m

    def test_the_taxi_faces_negative_z(self, meshes: list[MeshData]) -> None:
        """Godot's forward. The roof sign sits ahead of the cabin's midpoint,
        so an asymmetric bound is the cheap check that nothing got mirrored."""
        low, high = meshes[0].aabb()
        assert low[2] < 0 < high[2]
        assert abs(low[2]) == pytest.approx(abs(high[2]), abs=0.15)
