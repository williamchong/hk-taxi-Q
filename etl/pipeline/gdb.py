"""Vector layers out of a File Geodatabase, as numpy arrays.

The counterpart to `gltf.py`: this module knows the container and nothing about
what is stored in it. `roads.py` supplies the meaning of a layer or a field;
here they are just names passed through to OGR.

Reading goes through **pyogrio**, which ships GDAL/OGR in its wheels. That
matters more than it sounds: the alternative bindings need a system GDAL, which
is the dependency this project spent `P0-4` deliberately deferring.

The geodatabase is read **inside its zip**, via OGR's `/vsizip/` virtual
filesystem. `RdNet_IRNP.gdb.zip` is 17 MB and expands to a directory of a few
hundred files; unpacking it would cost disk and a cleanup path to produce input
that is read once.

Geometry comes back as WKB and is decoded here rather than through Shapely, for
the same reason `gltf.py` writes glTF by hand: the pipeline needs coordinate
arrays, and going via geometry objects would allocate one Python object per
feature on the way to `np.ndarray` anyway.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pyogrio.raw import read as _ogr_read

# WKB geometry type codes (OGC 06-103r4 §8.2.3). Only the ones this pipeline
# reads are named; anything else raises rather than being guessed at. Point
# layers are deliberately absent until a stage needs one — `P1-5` will.
_LINESTRING = 2
_MULTILINESTRING = 5

# WKB byte-order flag, per geometry and per nested part.
_BIG_ENDIAN = 0

Bbox = tuple[float, float, float, float]


class GeometryError(ValueError):
    """A geometry was not the shape the caller asked for."""


@dataclass(frozen=True)
class Layer:
    """One layer's features: their ids, their geometry, and chosen columns.

    `fids` are the geodatabase's own `OBJECTID` values, not row numbers. They
    are the identity the source's own cross-references use — Road Network v2's
    turn restrictions point at centrelines by FID — so they must survive the
    read, and they must survive a *filtered* read unchanged.
    """

    name: str
    crs: str | None
    fids: np.ndarray
    geometry: list[bytes]
    columns: dict[str, np.ndarray]

    def __len__(self) -> int:
        return len(self.geometry)

    def column(self, name: str) -> np.ndarray:
        if name not in self.columns:
            known = ", ".join(sorted(self.columns)) or "none"
            raise KeyError(f"layer '{self.name}' has no column '{name}'. Read: {known}")
        return self.columns[name]


def read_layer(
    path: Path | str,
    layer: str,
    *,
    columns: list[str],
    bbox: Bbox | None = None,
) -> Layer:
    """Read one layer, optionally clipped to a bounding box.

    `bbox` is `(min_x, min_y, max_x, max_y)` **in the layer's own CRS** — OGR
    does no reprojection here, and this project has already been bitten once by
    comparing coordinates across datums. Check `Layer.crs` before trusting it.

    `columns` is required rather than defaulted to all: the road centreline
    layer carries fourteen fields, half of them audit timestamps, and reading
    them is the difference between a numpy array and a list of Python objects.
    """
    meta, fids, geometry, fields = _ogr_read(
        _vsi_path(path),
        layer=layer,
        columns=columns,
        bbox=bbox,
        return_fids=True,
    )
    read = {str(name): values for name, values in zip(meta["fields"], fields, strict=True)}
    missing = [name for name in columns if name not in read]
    if missing:
        # OGR drops an unknown column silently, so a renamed field in a new
        # release of the source would otherwise surface far downstream as an
        # attribute that is uniformly null.
        raise KeyError(f"layer '{layer}' has no column(s): {', '.join(missing)}")

    return Layer(
        name=layer,
        crs=meta["crs"],
        fids=np.asarray(fids, dtype=np.int64),
        geometry=list(geometry),
        columns=read,
    )


def _vsi_path(path: Path | str) -> str:
    """Route a zipped geodatabase through OGR's virtual filesystem."""
    text = str(path)
    return f"/vsizip/{text}" if text.endswith(".zip") else text


def polylines(layer: Layer) -> tuple[np.ndarray, list[np.ndarray]]:
    """Every linestring part in the layer, and the row each came from.

    Parts rather than features because a multi-part linestring is two separate
    runs of road that happen to share a database row. Concatenating them would
    invent a straight segment across the gap between them; returning the row
    index instead lets the caller give each part the feature's attributes and
    treat them as the separate edges they are.
    """
    owners: list[int] = []
    parts: list[np.ndarray] = []
    for row, wkb in enumerate(layer.geometry):
        for points in _line_parts(wkb, layer.name):
            owners.append(row)
            parts.append(points)
    return np.asarray(owners, dtype=np.int64), parts


def _line_parts(wkb: bytes, where: str) -> list[np.ndarray]:
    order, kind = _header(wkb, 0)
    if kind == _LINESTRING:
        return [_coordinates(wkb, 5, order)[0]]
    if kind != _MULTILINESTRING:
        raise GeometryError(f"layer '{where}' holds geometry type {kind}, expected a linestring")

    (count,) = struct.unpack_from(_uint(order), wkb, 5)
    parts: list[np.ndarray] = []
    offset = 9
    for _ in range(count):
        # Each part carries its own byte-order flag and type; a mixed-endian
        # WKB is legal and the outer header does not speak for the parts.
        part_order, part_kind = _header(wkb, offset)
        if part_kind != _LINESTRING:
            raise GeometryError(f"layer '{where}' has a {part_kind} inside a multilinestring")
        piece, offset = _coordinates(wkb, offset + 5, part_order)
        parts.append(piece)
    return parts


def _coordinates(wkb: bytes, offset: int, order: int) -> tuple[np.ndarray, int]:
    """The `(n, 2)` coordinate block at `offset`, and the offset just past it."""
    (count,) = struct.unpack_from(_uint(order), wkb, offset)
    offset += 4
    # A view onto the buffer, copied because `wkb` is a bytes object the caller
    # is about to drop and a read-only view would keep all of it alive.
    block = np.frombuffer(wkb, _real(order), count=count * 2, offset=offset).reshape(count, 2)
    return np.array(block, dtype=np.float64), offset + count * 16


def _header(wkb: bytes, offset: int) -> tuple[int, int]:
    """The byte-order flag and geometry type at `offset`, rejecting 3D.

    Z and M ordinates are marked in the type word — `1002` for a LineString Z in
    ISO WKB, a high bit set in the PostGIS dialect. Both are refused rather than
    masked off, because the only thing they change is the coordinate stride:
    masking would leave this reader striding 16 bytes through 24-byte points and
    returning coordinates that are wrong without being obviously wrong.
    """
    order = wkb[offset]
    (kind,) = struct.unpack_from(_uint(order), wkb, offset + 1)
    if kind > 1000 or kind & 0xF000_0000:
        raise GeometryError(
            f"WKB geometry type {kind} carries Z or M ordinates; this reader is 2D only"
        )
    return order, kind


def _uint(order: int) -> str:
    return ">I" if order == _BIG_ENDIAN else "<I"


def _real(order: int) -> str:
    return ">f8" if order == _BIG_ENDIAN else "<f8"
