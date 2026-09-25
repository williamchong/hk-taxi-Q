"""The `P3-49` emote generator (`tools/make_emote.py`).

Three kinds of test, on `test_make_vehicle.py`'s pattern.

**The committed-asset guard.** The `.glb`s are build output that is *committed*,
and `tools/check.sh` does not know this tool exists. Regenerating and comparing
bytes is what catches "edited the generator, forgot to re-run".

**The facing.** `PassengerEmote` turns an emote with `look_at`, which points -Z
at the camera, so every feature must stand proud of the **-Z** face of the disc
and nothing may stand proud of +Z. A face built the other way round renders as
a blank coin from every angle, and a frame check would report a coin and not
say why.

**Winding and degeneracy.** The wheel's lessons: an inside-out disc is a hole
under backface culling, and a zero-area quad has no normal.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from make_emote import (
    ANGRY_FILE,
    DARK,
    GRIN_FILE,
    HURT_FILE,
    MATERIAL,
    PROUD_M,
    WHITE,
    Proportions,
    build_angry,
    build_grin,
    build_hurt,
    plate,
    write_emotes,
)

from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
SHIPPED = ROOT / "game" / "assets" / "authored" / "vehicles"

# A glyph over a toy car, seen for a second and a half. The budget is what keeps
# "a face" from becoming "a head".
TRIANGLE_BUDGET = 400

# `make_vehicle.py` records why: Godot's importer converts node names ending in
# these into physics nodes, silently.
FORBIDDEN_SUFFIXES = ("_wheel", "_col", "_convcol", "_navmesh", "_occ", "_rigid", "_vehicle")


@pytest.fixture(scope="module")
def faces() -> list[MeshData]:
    return [build_grin(), build_angry(), build_hurt()]


def _outward_fraction(mesh: MeshData) -> float:
    """The share of triangles whose stored normal agrees with their winding."""
    cross = mesh.triangle_cross()
    stored = mesh.normals[mesh.triangles[:, 0]]
    return float((np.einsum("ij,ij->i", cross, stored) > 0.0).mean())


class TestShippedAssets:
    def test_the_committed_files_match_the_generator(self, tmp_path: Path) -> None:
        for path, _, _ in write_emotes(tmp_path):
            shipped = SHIPPED / path.name
            assert shipped.exists(), f"{shipped.name} is not committed"
            assert shipped.read_bytes() == path.read_bytes(), (
                f"{shipped.name} is stale — re-run tools/make_emote.py"
            )

    def test_two_files_and_no_importer_suffix(self) -> None:
        for name in (GRIN_FILE, ANGRY_FILE, HURT_FILE):
            stem = name.removesuffix(".glb")
            assert not any(stem.endswith(s) for s in FORBIDDEN_SUFFIXES), stem

    def test_the_material_is_not_one_the_import_hook_dispatches(self, faces) -> None:
        # The rig overrides the surface with an unshaded material; a name the
        # hook recognises would hand it a lit shader first.
        assert MATERIAL == "emote"
        assert all(face.material == MATERIAL for face in faces)


class TestTheFaceIsOnTheSideTheCameraGets:
    def test_every_feature_stands_proud_of_minus_z(self, faces) -> None:
        shape = Proportions()
        front = -shape.thickness_m / 2.0
        for face in faces:
            z = face.positions[:, 2]
            assert np.isclose(z.max(), shape.thickness_m / 2.0), f"{face.name} grows behind +Z"
            assert z.min() < front - PROUD_M / 2.0, f"{face.name} has nothing proud of the front"

    def test_the_features_are_the_dark_and_white_parts(self, faces) -> None:
        shape = Proportions()
        front = -shape.thickness_m / 2.0
        for face in faces:
            rgb = face.colours[:, :3]
            feature = np.all(rgb == np.array(DARK), axis=1) | np.all(rgb == np.array(WHITE), axis=1)
            assert feature.any(), f"{face.name} has no features"
            assert (face.positions[feature, 2] <= front + 1e-9).all(), (
                f"{face.name}: a feature reaches behind the front face"
            )
            assert (face.positions[~feature, 2] >= front - 1e-9).all(), (
                f"{face.name}: the disc stands in front of its own features"
            )

    def test_every_feature_lies_inside_the_disc(self, faces) -> None:
        shape = Proportions()
        for face in faces:
            radial = np.hypot(face.positions[:, 0], face.positions[:, 1])
            assert radial.max() <= shape.radius_m + 1e-9, f"{face.name} spills past its disc"

    def test_the_faces_are_the_same_size(self, faces) -> None:
        grin = faces[0]
        for other in faces[1:]:
            assert np.allclose(grin.aabb()[0][:2], other.aabb()[0][:2])
            assert np.allclose(grin.aabb()[1][:2], other.aabb()[1][:2])

    def test_the_hurt_eyes_are_crossed(self) -> None:
        # A daze, not a stare: over each eye's place the dark vertices spread
        # along both diagonals, which a disc's ring or a bar's line does not.
        shape = Proportions()
        hurt = build_hurt()
        rgb = hurt.colours[:, :3]
        dark = np.all(rgb == np.array(DARK), axis=1)
        for side in (-1.0, 1.0):
            near = hurt.positions[
                dark
                & (np.sign(hurt.positions[:, 0]) == side)
                & (hurt.positions[:, 1] > shape.eye_y_m - shape.cross_half_length_m - 1e-6)
            ]
            assert len(near) >= 16, f"side {side:+.0f} has no crossed eye"
            local = near[:, :2] - np.array([side * shape.eye_x_m, shape.eye_y_m])
            diag_a = local @ np.array([1.0, 1.0]) / np.sqrt(2.0)
            diag_b = local @ np.array([1.0, -1.0]) / np.sqrt(2.0)
            assert diag_a.max() > shape.cross_half_length_m * 0.9
            assert diag_b.max() > shape.cross_half_length_m * 0.9

    def test_the_angry_brows_slope_down_towards_the_nose(self) -> None:
        # Anger, not worry: each brow's inner end is the lower one. Read off the
        # dark vertices above the eyes, split by side.
        shape = Proportions()
        angry = build_angry()
        rgb = angry.colours[:, :3]
        dark = np.all(rgb == np.array(DARK), axis=1)
        brows = angry.positions[dark & (angry.positions[:, 1] > shape.eye_y_m + shape.eye_radius_m)]
        assert len(brows) > 0
        for side in (-1.0, 1.0):
            bar = brows[np.sign(brows[:, 0]) == side]
            inner = bar[np.argmin(np.abs(bar[:, 0]))]
            outer = bar[np.argmax(np.abs(bar[:, 0]))]
            assert inner[1] < outer[1], f"brow on side {side:+.0f} slopes up towards the nose"


class TestWinding:
    def test_every_triangle_faces_outward(self, faces) -> None:
        for face in faces:
            assert _outward_fraction(face) == 1.0, face.name

    def test_no_triangle_is_degenerate(self, faces) -> None:
        for face in faces:
            area = np.linalg.norm(face.triangle_cross(), axis=1)
            assert (area > 1e-9).all(), f"{face.name} has a zero-area triangle"

    def test_within_the_triangle_budget(self, faces) -> None:
        for face in faces:
            assert face.triangle_count <= TRIANGLE_BUDGET, (
                f"{face.name}: {face.triangle_count} > {TRIANGLE_BUDGET}"
            )

    def test_nothing_is_textured(self, faces) -> None:
        for face in faces:
            assert face.texture is None and face.uvs is None
            assert face.colours is not None


class TestPlate:
    def test_a_plate_built_backwards_is_refused(self) -> None:
        with pytest.raises(ValueError, match="in front of"):
            plate([(0, 0), (1, 0), (1, 1)], DARK, z_front=0.0, z_back=-0.1, name="back")

    def test_a_plate_needs_three_corners(self) -> None:
        with pytest.raises(ValueError, match="three corners"):
            plate([(0, 0), (1, 0)], DARK, z_front=-0.1, z_back=0.0, name="line")
