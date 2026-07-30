"""Mesh- and vector-shaped test helpers.

A plain module, not `conftest.py`, because these are imported by name. pytest
imports `conftest.py` as top-level `conftest` while an `import tests.conftest`
creates a *second* module object — so anything living in both places exists
twice, and only pytest's copy of a fixture is a working fixture.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import numpy as np
from pyogrio.raw import write as _ogr_write

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


# --------------------------------------------------------------------------
# Vector geometry, for `gdb.py` and `roads.py`
# --------------------------------------------------------------------------


# Every spelling of Road Network v2's null sentinel for a text field. Written
# as escapes rather than literally: the difference between an en-dash and a
# hyphen, or a full-width digit and an ASCII one, is exactly what these test
# and exactly what is invisible in a source file.
NULL_SENTINELS = (
    "-99",
    "\u2013\uff19\uff19",  # en-dash, full-width nines
    "\uff0d\uff19\uff19",  # full-width hyphen and nines
    "-\uff19\uff19",  # ASCII hyphen, full-width nines
)


def line_wkb(*parts: object, big_endian: bool = False) -> bytes:
    """A 2D LineString or MultiLineString as WKB.

    One part gives a plain LineString, several give a MultiLineString, so a test
    can exercise either shape without a second helper.
    """
    order, prefix = (0, ">") if big_endian else (1, "<")
    blocks = [_line_block(np.asarray(part, dtype=np.float64), order, prefix) for part in parts]
    if len(blocks) == 1:
        return blocks[0]
    return struct.pack(f"{prefix}BII", order, 5, len(blocks)) + b"".join(blocks)


def _line_block(points: np.ndarray, order: int, prefix: str) -> bytes:
    body = points.astype(f"{prefix}f8", copy=False).tobytes()
    return struct.pack(f"{prefix}BII", order, 2, len(points)) + body


def write_layer(
    path: Path,
    layer: str,
    geometry: list[bytes],
    columns: dict[str, Any],
    *,
    geometry_type: str = "LineString",
    crs: str = "EPSG:2326",
) -> None:
    """Append one layer of WKB features to a GeoPackage.

    Built through pyogrio's raw writer rather than a checked-in fixture file, so
    the tests read their input back through the same GDAL that reads the real
    geodatabase — a fixture would only prove that the parser agrees with itself.
    """
    fields = np.array(list(columns), dtype=object)
    field_data = [np.asarray(values) for values in columns.values()]
    _ogr_write(
        str(path),
        geometry=np.array(geometry, dtype=object),
        field_data=field_data,
        fields=fields,
        layer=layer,
        driver="GPKG",
        geometry_type=geometry_type,
        crs=crs,
        append=path.exists(),
    )
