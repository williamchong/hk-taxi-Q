"""Mesh-shaped test helpers.

A plain module, not `conftest.py`, because these are imported by name. pytest
imports `conftest.py` as top-level `conftest` while an `import tests.conftest`
creates a *second* module object — so anything living in both places exists
twice, and only pytest's copy of a fixture is a working fixture.
"""

from __future__ import annotations

import numpy as np

from pipeline.gltf import MeshData

# The six faces of an axis-aligned box, over corners ordered x-outer, y-middle,
# z-inner. Each face is a quad; callers decide how to triangulate it.
BOX_FACES = [
    ((0, 1, 3, 2), (-1, 0, 0)),
    ((4, 6, 7, 5), (1, 0, 0)),
    ((0, 4, 5, 1), (0, -1, 0)),
    ((2, 3, 7, 6), (0, 1, 0)),
    ((0, 2, 6, 4), (0, 0, -1)),
    ((1, 5, 7, 3), (0, 0, 1)),
]


def box_corners(low: tuple[float, float, float], high: tuple[float, float, float]) -> np.ndarray:
    """The eight corners of a box, in the order `BOX_FACES` indexes."""
    return np.array(
        [
            [x, y, z]
            for x in (low[0], high[0])
            for y in (low[1], high[1])
            for z in (low[2], high[2])
        ],
        dtype=np.float64,
    )


def box_soup(corners: np.ndarray) -> tuple[list, list]:
    """A box's 36 positions and matching face normals, vertices unshared.

    Unshared on purpose: every vertex repeated per face so each carries its own
    face normal. That repetition is exactly what LOD0's exact weld exists to
    remove, so a test must not start from a welded box.
    """
    positions, normals = [], []
    for (a, b, c, d), normal in BOX_FACES:
        for index in (a, b, c, a, c, d):
            positions.append(corners[index])
            normals.append(normal)
    return positions, normals


def box(
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
    size: float = 10.0,
    *,
    colour: tuple[int, int, int, int] = (200, 190, 180, 255),
) -> MeshData:
    """An axis-aligned box in game space, unwelded and flat-shaded."""
    corners = box_corners(origin, tuple(value + size for value in origin))
    positions, normals = box_soup(corners)

    return MeshData(
        name="box",
        positions=np.array(positions, dtype=np.float64),
        normals=np.array(normals, dtype=np.float32),
        triangles=np.arange(36, dtype=np.uint32).reshape(-1, 3),
        colours=np.tile(np.array(colour, np.uint8), (36, 1)),
    )
