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
from pathlib import Path, PurePosixPath

import numpy as np
from pyogrio.raw import read as _ogr_read

# WKB geometry type codes (OGC 06-103r4 §8.2.3). Only the ones this pipeline
# reads are named; anything else raises rather than being guessed at. Point
# layers are deliberately absent until a stage needs one — `P1-5` will.
_LINESTRING = 2
_POLYGON = 3
_MULTILINESTRING = 5
_MULTIPOLYGON = 6

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
    zip_member: str | None = None,
    expect_crs: str | None = None,
) -> Layer:
    """Read one layer, optionally clipped to a bounding box.

    `bbox` is `(min_x, min_y, max_x, max_y)` **in the layer's own CRS** — OGR
    does no reprojection here, and this project has already been bitten once by
    comparing coordinates across datums. `expect_crs` makes that check the
    read's own job rather than one every caller hand-rolls: a datum mismatch
    shifts coordinates by hundreds of metres and still looks plausible, so a
    caller that passes a `bbox` should say which CRS it built it in.

    `columns` is required rather than defaulted to all: the road centreline
    layer carries fourteen fields, half of them audit timestamps, and reading
    them is the difference between a numpy array and a list of Python objects.

    `zip_member` names the geodatabase inside the zip, for publishers that nest
    it under a directory (`sheet/sheet.gdb`) instead of zipping the `.gdb` at
    the archive root. The caller gets it from city config, never spells it.
    """
    meta, fids, geometry, fields = _ogr_read(
        _vsi_path(path, zip_member),
        layer=layer,
        columns=columns,
        bbox=bbox,
        return_fids=True,
    )
    if expect_crs is not None and meta["crs"] and meta["crs"] != expect_crs:
        raise ValueError(
            f"layer '{layer}' is in {meta['crs']}, but the caller expects {expect_crs}. "
            f"Reprojection is not done here — fix the config."
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


def _vsi_path(path: Path | str, member: str | None = None) -> str:
    """Route a zipped geodatabase through OGR's virtual filesystem.

    `member` is a path inside the archive. It arrives from config formatted
    with a tile id that originated in a publisher's remote index, so a member
    that tries to escape the archive is refused rather than trusted.
    """
    text = str(path)
    if member is None:
        return f"/vsizip/{text}" if text.endswith(".zip") else text
    parts = PurePosixPath(member)
    if parts.is_absolute() or ".." in parts.parts:
        raise ValueError(f"zip member {member!r} escapes its archive")
    return f"/vsizip/{text}/{member}"


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
    order, kind, has_z = _header(wkb, 0)
    if kind not in (_LINESTRING, _MULTILINESTRING):
        raise GeometryError(f"layer '{where}' holds geometry type {kind}, expected a linestring")
    if has_z:
        raise GeometryError(f"layer '{where}' holds Z linestrings; the line path reads 2D only")
    if kind == _LINESTRING:
        return [_coordinates(wkb, 5, order)[0]]

    (count,) = struct.unpack_from(_uint(order), wkb, 5)
    parts: list[np.ndarray] = []
    offset = 9
    for _ in range(count):
        # Each part carries its own byte-order flag and type; a mixed-endian
        # WKB is legal and the outer header does not speak for the parts.
        part_order, part_kind, part_z = _header(wkb, offset)
        if part_kind != _LINESTRING:
            raise GeometryError(f"layer '{where}' has a {part_kind} inside a multilinestring")
        if part_z:
            raise GeometryError(f"layer '{where}' holds Z linestrings; the line path reads 2D only")
        piece, offset = _coordinates(wkb, offset + 5, part_order)
        parts.append(piece)
    return parts


def polygons(layer: Layer) -> tuple[np.ndarray, list[list[np.ndarray]]]:
    """Every polygon part in the layer as its rings, and the row each came from.

    Owners mirror `polylines`: a multipolygon's polygons are separate footprints
    that happen to share a database row, so each is its own part tagged with the
    row index. A part is a list of `(n, 2)` rings with the outer ring first —
    WKB fixes that ordering — so a caller doing containment can tell a boundary
    from a hole.

    Coordinates are plan-only: a Z geometry is decoded at its true stride and
    the Z column then dropped, because the sources this reads carry vertical
    extent in attribute columns, not in ring geometry. A consumer that ever
    needs ring Z extends the decode here — it does not mask flags off.
    """
    owners: list[int] = []
    parts: list[list[np.ndarray]] = []
    for row, wkb in enumerate(layer.geometry):
        for rings in _polygon_parts(wkb, layer.name):
            owners.append(row)
            parts.append(rings)
    return np.asarray(owners, dtype=np.int64), parts


def _polygon_parts(wkb: bytes, where: str) -> list[list[np.ndarray]]:
    order, kind, has_z = _header(wkb, 0)
    if kind == _POLYGON:
        rings, _ = _rings(wkb, 5, order, has_z)
        return [rings] if rings else []
    if kind != _MULTIPOLYGON:
        raise GeometryError(f"layer '{where}' holds geometry type {kind}, expected a polygon")

    (count,) = struct.unpack_from(_uint(order), wkb, 5)
    parts: list[list[np.ndarray]] = []
    offset = 9
    for _ in range(count):
        # Each part carries its own byte-order flag, type and dimensionality;
        # the outer header does not speak for the parts.
        part_order, part_kind, part_z = _header(wkb, offset)
        if part_kind != _POLYGON:
            raise GeometryError(f"layer '{where}' has a {part_kind} inside a multipolygon")
        rings, offset = _rings(wkb, offset + 5, part_order, part_z)
        if rings:
            parts.append(rings)
    return parts


def _rings(wkb: bytes, offset: int, order: int, has_z: bool) -> tuple[list[np.ndarray], int]:
    """A polygon body's rings starting at `offset`, and the offset just past.

    Rings share the polygon's byte order and dimensionality: WKB gives nested
    *geometries* their own header, but a ring is a bare coordinate block.
    """
    (count,) = struct.unpack_from(_uint(order), wkb, offset)
    offset += 4
    rings: list[np.ndarray] = []
    for _ in range(count):
        ring, offset = _coordinates(wkb, offset, order, has_z=has_z)
        rings.append(ring)
    return rings, offset


def _coordinates(
    wkb: bytes, offset: int, order: int, *, has_z: bool = False
) -> tuple[np.ndarray, int]:
    """The plan `(n, 2)` coordinate block at `offset`, and the offset just past it.

    A Z block is strided at three ordinates per point and its Z column dropped
    after the decode: the callers that accept Z take vertical extent from
    attribute columns, and a mixed `(n, 2)` / `(n, 3)` return would push that
    slice into every one of them.
    """
    (count,) = struct.unpack_from(_uint(order), wkb, offset)
    offset += 4
    width = 3 if has_z else 2
    # A view onto the buffer, copied because `wkb` is a bytes object the caller
    # is about to drop and a read-only view would keep all of it alive.
    block = np.frombuffer(wkb, _real(order), count=count * width, offset=offset)
    plan = np.array(block.reshape(count, width)[:, :2], dtype=np.float64)
    return plan, offset + count * width * 8


def _header(wkb: bytes, offset: int) -> tuple[int, int, bool]:
    """The byte-order flag, base geometry type, and Z flag at `offset`.

    Dimensionality is marked in the type word, in two dialects: ISO WKB offsets
    the code (`1002` for a LineString Z) and the older OGC form sets the
    `0x80000000` high bit — which is the one GDAL's export writes, so it is what
    pyogrio hands back. Both are decoded, never masked off, because the only
    thing dimensionality changes is the coordinate stride: masking would leave a
    reader striding 16 bytes through 24-byte points and returning coordinates
    that are wrong without being obviously wrong. Z is reported for the caller
    to accept or refuse; M is refused here outright — nothing in this pipeline
    reads measures, and GDAL already drops them from the one source that carries
    them. The EWKB SRID flag is refused too: it changes the header's own size,
    and no plain WKB writer emits it.
    """
    order = wkb[offset]
    (raw,) = struct.unpack_from(_uint(order), wkb, offset + 1)
    if raw & 0x2000_0000:
        raise GeometryError(f"WKB geometry type {raw:#010x} embeds an SRID; only plain WKB is read")
    dims, base = divmod(raw & 0x1FFF_FFFF, 1000)
    if dims > 3:
        raise GeometryError(f"WKB geometry type {raw} is not a recognised type code")
    has_z = bool(raw & 0x8000_0000) or dims in (1, 3)
    has_m = bool(raw & 0x4000_0000) or dims in (2, 3)
    if has_m:
        raise GeometryError(f"WKB geometry type {raw} carries M ordinates; nothing here reads them")
    return order, base, has_z


def _uint(order: int) -> str:
    return ">I" if order == _BIG_ENDIAN else "<I"


def _real(order: int) -> str:
    return ">f8" if order == _BIG_ENDIAN else "<f8"
