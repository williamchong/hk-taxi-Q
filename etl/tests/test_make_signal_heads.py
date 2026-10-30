"""`tools/make_signal_heads.py` — the signal-head library (`P3-3e`, `Q173`).

What is pinned: the committed bytes against the generator, so an edit to the
drawing is a rebuild; the head IN FRONT of its post (`P3-17`'s defect was the
reverse); the frame (facing north, foot at the origin); the lens circuits on
`UV.x`, which `signal_head.gdshader` decodes; and the winding.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from pipeline.config import load_config
from pipeline.config_blocks.signals import HEAD_LENSES, HeadDrawing
from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from make_signal_heads import (  # noqa: E402
    BODY_CIRCUIT,
    LIBRARY_FILE,
    MATERIAL,
    head_mesh,
    lens_circuit,
    write_library,
)

SHIPPED = ROOT / "game" / "assets" / "authored" / "signals"


@pytest.fixture(scope="module")
def drawing() -> HeadDrawing:
    signals = load_config().signals
    assert signals is not None and signals.heads is not None
    return signals.heads.drawing


@pytest.fixture(scope="module")
def mesh(drawing: HeadDrawing) -> MeshData:
    return head_mesh(drawing)


def test_the_committed_library_matches_the_generator(tmp_path: Path) -> None:
    path, _, _ = write_library(tmp_path)
    shipped = SHIPPED / LIBRARY_FILE
    assert shipped.exists(), f"{shipped.name} is not committed"
    assert shipped.read_bytes() == path.read_bytes(), (
        f"{shipped.name} is stale — re-run tools/make_signal_heads.py"
    )


def test_the_material_is_the_import_scripts_row(mesh: MeshData) -> None:
    assert mesh.material == MATERIAL
    importer = (ROOT / "game" / "tools" / "generated_scene_import.gd").read_text()
    assert f'"{MATERIAL}": "res://tuning/signal_heads.tres"' in importer


def test_the_foot_is_at_the_origin(mesh: MeshData, drawing: HeadDrawing) -> None:
    low, high = mesh.aabb()
    assert low[1] == pytest.approx(0.0)
    assert high[1] == pytest.approx(
        drawing.mount_height_m + drawing.head_height_m + drawing.post_headroom_m
    )


def test_the_head_stands_in_front_of_its_post(mesh: MeshData, drawing: HeadDrawing) -> None:
    """North is -Z: every head vertex is at or north of the post's own face."""
    above = mesh.positions[:, 1] >= drawing.mount_height_m - 1e-9
    housing = above & (np.abs(mesh.positions[:, 0]) > drawing.post_radius_m + 1e-6)
    assert housing.any()
    assert mesh.positions[housing, 2].max() <= -drawing.post_radius_m + 1e-6
    low, _ = mesh.aabb()
    assert low[2] == pytest.approx(
        -(drawing.post_radius_m + drawing.head_depth_m + drawing.lens_lift_m)
    )


def test_each_lens_carries_its_circuit_top_to_bottom(mesh: MeshData) -> None:
    assert mesh.uvs is not None
    circuit = mesh.uvs[:, 0]
    assert set(np.unique(circuit)) == {BODY_CIRCUIT, *(lens_circuit(k) for k in range(3))}
    heights = [
        mesh.positions[circuit == lens_circuit(k), 1].mean() for k in range(len(HEAD_LENSES))
    ]
    assert heights == sorted(heights, reverse=True), "red at the top, green at the bottom"


def test_vertex_alpha_says_nothing(mesh: MeshData) -> None:
    """The Compatibility renderer reads alpha 0 here: no marker may ride it."""
    assert (mesh.colours[:, 3] == 255).all()


def test_every_lens_faces_north(mesh: MeshData) -> None:
    assert mesh.uvs is not None
    lens = mesh.uvs[:, 0] != BODY_CIRCUIT
    assert np.allclose(mesh.normals[lens], [0.0, 0.0, -1.0])


def test_every_face_is_wound_to_its_normal(mesh: MeshData) -> None:
    """`cull_back`: a face wound against its normal renders as a hole."""
    cross = mesh.triangle_cross()
    normals = mesh.normals[mesh.triangles[:, 0]]
    assert (np.einsum("ij,ij->i", cross, normals) > 0.0).all()
