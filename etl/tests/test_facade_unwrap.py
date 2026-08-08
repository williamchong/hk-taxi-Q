"""The `Q41` unwrap (`tools/facade_unwrap.py`).

Only the parts whose failure is **silent**. A mirrored elevation, or one where
a rear surface overwrote the façade, is still a plausible-looking picture — the
reader classifies it happily and nobody sees that the survey read the wrong
wall. So the tests pin the two properties the module docstring calls
load-bearing: viewer-outside orientation, and outermost-surface-wins.
"""

from __future__ import annotations

import io

import numpy as np
from facade_unwrap import TEXELS_PER_M, unwrap_building, unwrap_face
from PIL import Image

from pipeline.gltf import MeshData, Texture


def png_texture(pixels: list[list[list[int]]]) -> Texture:
    buffer = io.BytesIO()
    Image.fromarray(np.array(pixels, dtype=np.uint8)).save(buffer, format="PNG")
    return Texture(data=buffer.getvalue(), mime_type="image/png")


# A 2x2 texture whose quadrants are distinct: row 0 (v≈0) red|green,
# row 1 (v≈1) blue|yellow.
QUADRANTS = png_texture(
    [
        [[255, 0, 0], [0, 255, 0]],
        [[0, 0, 255], [255, 255, 0]],
    ]
)


def wall(z: float, normal_z: float, texture: Texture, width: float = 10.0) -> MeshData:
    """A textured quad from x=0..width, y=0..5, at depth `z`, facing ±z.

    UVs put v=0 at the wall's top, so texture row 0 is the top of the wall —
    the convention the assertions below rely on.
    """
    positions = np.array([[0, 0, z], [width, 0, z], [width, 5, z], [0, 5, z]], dtype=np.float64)
    normals = np.tile(np.array([0, 0, normal_z], dtype=np.float32), (4, 1))
    uvs = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], dtype=np.float32)
    return MeshData(
        name="wall",
        positions=positions,
        normals=normals,
        triangles=np.array([[0, 1, 2], [0, 2, 3]]),
        uvs=uvs,
        texture=texture,
    )


def test_south_face_is_viewer_oriented_and_metred() -> None:
    elevation = unwrap_face([wall(0.0, 1.0, QUADRANTS)], "S")
    assert elevation is not None
    assert elevation.width_m == 10.0 and elevation.height_m == 5.0
    assert elevation.canvas.shape[1] == int(np.ceil(10 * TEXELS_PER_M)) + 1
    assert elevation.coverage > 0.95
    # Viewer south of a south-facing wall: world x=0 is on the LEFT, wall top
    # is row 0. Top-left texel is texture (u=0, v=0) — red.
    height, width = elevation.canvas.shape[:2]
    assert tuple(elevation.canvas[1, 1]) == (255, 0, 0)
    assert tuple(elevation.canvas[1, width - 2]) == (0, 255, 0)
    assert tuple(elevation.canvas[height - 2, 1]) == (0, 0, 255)
    assert tuple(elevation.canvas[height - 2, width - 2]) == (255, 255, 0)


def test_north_face_mirrors_so_the_viewer_stands_outside() -> None:
    elevation = unwrap_face([wall(0.0, -1.0, QUADRANTS)], "N")
    assert elevation is not None
    # Viewer north of a north-facing wall looks back at it: world x=0 is now on
    # the RIGHT, so the top-right texel is texture (u=0, v=0) — red.
    width = elevation.canvas.shape[1]
    assert tuple(elevation.canvas[1, width - 2]) == (255, 0, 0)
    assert tuple(elevation.canvas[1, 1]) == (0, 255, 0)


def test_outermost_surface_wins_the_depth_buffer() -> None:
    grey = png_texture([[[128, 128, 128]]])
    front = wall(1.0, 1.0, QUADRANTS)  # south-facing, 1 m further out
    behind = wall(0.0, 1.0, grey)
    elevation = unwrap_face([behind, front], "S")
    assert elevation is not None
    # The rear grey wall must not overwrite the façade, whatever the mesh order.
    assert tuple(elevation.canvas[1, 1]) == (255, 0, 0)
    reversed_order = unwrap_face([front, behind], "S")
    assert reversed_order is not None
    assert tuple(reversed_order.canvas[1, 1]) == (255, 0, 0)


def test_slivers_and_bare_faces_refuse() -> None:
    assert unwrap_face([wall(0.0, 1.0, QUADRANTS, width=1.0)], "S") is None
    assert unwrap_face([wall(0.0, 1.0, QUADRANTS)], "E") is None
    faces = unwrap_building([wall(0.0, 1.0, QUADRANTS)])
    assert list(faces) == ["S"]
    # Narrowing to the faces a caller needs skips the rest, refusals included.
    assert unwrap_building([wall(0.0, 1.0, QUADRANTS)], faces=["N", "E"]) == {}
