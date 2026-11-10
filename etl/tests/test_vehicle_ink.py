"""`tools/vehicle_ink.py`: which edges of a body take a detail line.

The line is drawn by `vehicle_body.gdshader` off `uv2`, so what is pinned here
is the mesh data alone: where a channel reads 1 (on an inked edge) and where it
stays 0 (no line).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

from pipeline.gltf import MeshData
from pipeline.mesh import merge

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from primitives import polygon  # noqa: E402
from vehicle_ink import INK_SPAN_M, inked  # noqa: E402

RED = (200, 0, 0)
GLASS = (40, 50, 60)


def _body(*parts: MeshData) -> MeshData:
    body = merge(list(parts), name="body")
    assert body.colours is not None
    return replace(body, uvs=np.zeros((len(body.colours), 2), dtype=np.float32))


def _square(x0: float, x1: float, colour: tuple[int, int, int], z: float = 0.0) -> MeshData:
    return polygon([(x0, 0, z), (x1, 0, z), (x1, 1, z), (x0, 1, z)], colour, name="q")


def _on_line(mesh: MeshData) -> np.ndarray:
    """Per vertex: whether either channel puts it on an inked edge."""
    assert mesh.uv2 is not None
    return np.isclose(mesh.uv2, 1.0).any(axis=1)


def test_a_quad_inks_its_rim_and_not_its_diagonal() -> None:
    mesh = inked(_body(_square(0.0, 1.0, RED)))
    assert mesh.uv2 is not None
    # Every corner is on the rim, and no channel is constant 1 across a
    # triangle — which is what an inked diagonal would look like from inside.
    assert _on_line(mesh).all()
    per_triangle = mesh.uv2[np.asarray(mesh.triangles).reshape(-1, 3)]
    assert np.all(np.isclose(per_triangle, 1.0).sum(axis=1) <= 2)
    assert np.isclose(per_triangle.min(), 1.0 - 1.0 / INK_SPAN_M)


def test_the_same_colour_carrying_on_takes_no_line() -> None:
    mesh = inked(_body(_square(0.0, 1.0, RED), _square(1.0, 2.0, RED)))
    assert mesh.uv2 is not None
    triangles = np.asarray(mesh.triangles).reshape(-1, 3)
    inked_edges = 0
    for triangle in triangles:
        for channel in range(2):
            on_edge = triangle[np.isclose(mesh.uv2[triangle, channel], 1.0)]
            if len(on_edge) == 2:
                inked_edges += 1
                # The seam between the two squares, at x = 1, is not one of them.
                assert not np.allclose(mesh.positions[on_edge, 0], 1.0)
    assert inked_edges == 6


def test_a_pane_laid_on_a_panel_is_inked_all_round() -> None:
    panel = _square(0.0, 3.0, RED)
    pane = polygon(
        [(1, 0.2, 0.001), (2, 0.2, 0.001), (2, 0.8, 0.001), (1, 0.8, 0.001)], GLASS, name="pane"
    )
    mesh = inked(_body(panel, pane))
    assert mesh.colours is not None
    glass = np.all(mesh.colours[:, :3] == np.array(GLASS, dtype=np.uint8), axis=1)
    assert glass.any() and _on_line(mesh)[glass].all()


def test_a_lone_triangle_is_split_so_two_channels_carry_three_edges() -> None:
    mesh = inked(_body(polygon([(0, 0, 0), (1, 0, 0), (0, 1, 0)], RED, name="t")))
    assert mesh.uv2 is not None
    assert len(np.asarray(mesh.triangles).reshape(-1, 3)) == 3
    assert np.all(mesh.uv2[:, 1] == 0.0)
    # The incentre is the same distance from all three edges.
    centre = ~np.isclose(mesh.uv2[:, 0], 1.0)
    assert len(np.unique(np.round(mesh.uv2[centre, 0], 6))) == 1
