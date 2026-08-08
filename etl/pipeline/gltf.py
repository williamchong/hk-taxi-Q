"""glTF 2.0 reading and writing, narrowed to the shapes this pipeline handles.

Reading: the subset FME emits for the LandsD models — a two-node scene, one
mesh, one primitive, non-interleaved attributes. Writing: merged tile meshes,
one primitive each, vertex colours, optionally one texture.

Hand-rolled rather than taken from a library because both ends are this narrow.
trimesh and pygltflib solve the general problem, and the general problem is not
the one here: the read side would use a few percent of either, and the write
side still has to lay out accessors and buffer views by hand under both, since
neither merges a vertex-coloured tile mesh for you. A dependency that saves no
work still has to install on every machine that runs the build.

Everything unsupported raises rather than being ignored. A silently dropped
attribute here becomes a building with no colour or a tile in the wrong place,
which is far more expensive to notice than an exception at parse time.
"""

from __future__ import annotations

import json
import struct
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

_GLB_MAGIC = 0x46546C67
_GLB_VERSION = 2
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942
_GLB_HEADER_BYTES = 12
_CHUNK_HEADER_BYTES = 8

_ARRAY_BUFFER = 34962
_ELEMENT_ARRAY_BUFFER = 34963
_MODE_TRIANGLES = 4

_UNSIGNED_BYTE = 5121
_UNSIGNED_SHORT = 5123
_UNSIGNED_INT = 5125
_FLOAT = 5126

_COMPONENT_DTYPE = {
    5120: np.dtype("<i1"),
    _UNSIGNED_BYTE: np.dtype("<u1"),
    5122: np.dtype("<i2"),
    _UNSIGNED_SHORT: np.dtype("<u2"),
    _UNSIGNED_INT: np.dtype("<u4"),
    _FLOAT: np.dtype("<f4"),
}
_COMPONENTS_PER_ELEMENT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

# uint16 indices halve the index buffer, and a 150 m tile of Wan Chai is well
# inside the range. Falling back rather than always using uint32 matters because
# the index buffer is a third of a non-indexed mesh's size.
_UINT16_LIMIT = 65_535


# A mesh's axis-aligned bounds: (low xyz, high xyz).
Bounds = tuple[tuple[float, float, float], tuple[float, float, float]]


@dataclass(frozen=True)
class Texture:
    data: bytes
    mime_type: str


@dataclass(frozen=True)
class MeshData:
    """One triangle mesh: one primitive, and so one draw call.

    Positions are float64 on purpose. Source coordinates are HK1980 grid
    metres — around 836,000 — where float32 spacing is 6 cm, so anything that
    holds a position before the region origin is subtracted must be wider than
    the float32 the file stores. `write_glb` narrows back to float32 once the
    numbers are region-local and small again.
    """

    name: str
    positions: np.ndarray  # (n, 3) float64
    normals: np.ndarray  # (n, 3) float32
    triangles: np.ndarray  # (m, 3) integer
    colours: np.ndarray | None = None  # (n, 4) uint8 RGBA
    uvs: np.ndarray | None = None  # (n, 2) float32
    uv2: np.ndarray | None = None  # (n, 2) float32
    texture: Texture | None = None
    # glTF material name, when the *engine* has to recognise it. Left unset the
    # material is named after the mesh, which is a label; set, it is a contract.
    #
    # `P3-7` needs one: `TEXCOORD_0` on a tile is a shader payload rather than a
    # texture coordinate, so a tile must import with a `ShaderMaterial` where
    # every other asset keeps its `BaseMaterial3D`. The engine sees a name and
    # nothing else — this is the only channel glTF offers for that, and it is the
    # same shape as the `-col` node-name suffix already carrying collision.
    material: str | None = None

    def __post_init__(self) -> None:
        count = len(self.positions)
        for attribute in ("normals", "colours", "uvs", "uv2"):
            values = getattr(self, attribute)
            if values is not None and len(values) != count:
                raise ValueError(
                    f"mesh '{self.name}': {attribute} has {len(values)} entries "
                    f"for {count} vertices"
                )

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    def translated(self, offset: Sequence[float]) -> MeshData:
        return replace(self, positions=self.positions + np.asarray(offset, dtype=np.float64))

    def aabb(self) -> Bounds:
        low = self.positions.min(axis=0)
        high = self.positions.max(axis=0)
        return (tuple(low.tolist()), tuple(high.tolist()))

    def triangle_centroids(self) -> np.ndarray:
        """(m, 3) centre of each triangle — how a mesh is bucketed spatially."""
        return self.positions[self.triangles].mean(axis=1)

    def triangle_cross(self) -> np.ndarray:
        """(m, 3) cross product of each triangle's two edge vectors.

        One product answers three questions: its direction is the face normal,
        its sign says which way the winding faces, and its length is twice the
        face area. Callers that want only one of those still want this.
        """
        return triangle_cross(self.positions, self.triangles)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def read_scene(document: bytes | str, resolve: Callable[[str], bytes]) -> list[MeshData]:
    """Decode a `.gltf` into meshes, with node transforms already applied.

    `resolve` maps a relative URI — a `.bin` buffer or a texture — to its bytes,
    so a caller can serve them straight out of a zip without unpacking 65 MB per
    sheet to disk.

    Node transforms are baked in rather than returned alongside, because every
    caller here wants source-CRS coordinates and none wants a scene graph.
    """
    gltf = json.loads(document)
    buffers = _BufferCache(gltf, resolve)

    meshes: list[MeshData] = []
    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    for root in scene.get("nodes", []):
        _walk(gltf, root, np.eye(4), buffers, meshes)
    return meshes


class _BufferCache:
    """Decoded buffers and images for one document.

    A document's accessors all read the same `.bin`, so resolving once per URI
    rather than per accessor saves three or four zip reads per building — the
    one measured saving here.

    Images go through the same cache, and `texture` hands out one object per
    image, so two primitives sharing a 39 MB terrain JPEG neither decompress it
    twice nor embed it twice. No LandsD document is shaped that way, so that
    part is a guard against a document shape this data does not have, not a
    saving on it.
    """

    def __init__(self, gltf: dict[str, Any], resolve: Callable[[str], bytes]) -> None:
        self._gltf = gltf
        self._resolve = resolve
        self._resolved: dict[str, bytes] = {}
        self._textures: dict[int, Texture] = {}

    def resolve(self, uri: str) -> bytes:
        if uri not in self._resolved:
            self._resolved[uri] = self._resolve(uri)
        return self._resolved[uri]

    def buffer(self, index: int) -> bytes:
        uri = self._gltf["buffers"][index].get("uri")
        if uri is None:
            raise ValueError("GLB-embedded buffers are not supported by this reader")
        return self.resolve(uri)

    def texture(self, image: int) -> Texture:
        """The image as a `Texture`, one object per image per document.

        One *object*, not merely one copy of the bytes: `write_glb` decides
        whether two primitives share an image by identity, so handing out a
        fresh wrapper per primitive would silently defeat it and embed a 39 MB
        JPEG twice.
        """
        if image not in self._textures:
            entry = self._gltf["images"][image]
            if "bufferView" in entry:
                self._textures[image] = Texture(
                    data=self.view_bytes(entry["bufferView"]), mime_type=entry["mimeType"]
                )
            else:
                uri = str(entry["uri"])
                self._textures[image] = Texture(data=self.resolve(uri), mime_type=_mime_type(uri))
        return self._textures[image]

    def view_bytes(self, index: int) -> bytes:
        view = self._gltf["bufferViews"][index]
        start = view.get("byteOffset", 0)
        return self.buffer(view["buffer"])[start : start + view["byteLength"]]

    def accessor(self, index: int) -> np.ndarray:
        accessor = self._gltf["accessors"][index]
        if "sparse" in accessor:
            raise ValueError("sparse accessors are not supported by this reader")

        element_type = accessor["type"]
        if element_type not in _COMPONENTS_PER_ELEMENT:
            raise ValueError(f"unsupported accessor type {element_type!r}")
        component_type = accessor["componentType"]
        if component_type not in _COMPONENT_DTYPE:
            raise ValueError(f"unsupported componentType {component_type}")

        width = _COMPONENTS_PER_ELEMENT[element_type]
        dtype = _COMPONENT_DTYPE[component_type]
        count = accessor["count"]

        view = self._gltf["bufferViews"][accessor["bufferView"]]
        if view.get("byteStride") not in (None, width * dtype.itemsize):
            raise ValueError("interleaved buffer views are not supported by this reader")

        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        raw = self.buffer(view["buffer"])
        values = np.frombuffer(raw, dtype=dtype, count=count * width, offset=start)
        return values.reshape(count, width) if width > 1 else values


def _walk(
    gltf: dict[str, Any],
    index: int,
    parent: np.ndarray,
    buffers: _BufferCache,
    out: list[MeshData],
) -> None:
    node = gltf["nodes"][index]
    transform = parent @ _node_matrix(node)

    if "mesh" in node:
        for primitive in gltf["meshes"][node["mesh"]].get("primitives", []):
            out.append(_primitive(gltf, primitive, transform, buffers, _name(gltf, index, node)))

    for child in node.get("children", []):
        _walk(gltf, child, transform, buffers, out)


def _name(gltf: dict[str, Any], index: int, node: dict[str, Any]) -> str:
    """The node's own name, or the nearest named ancestor's.

    LandsD puts the building id on the parent node and leaves the mesh-bearing
    child anonymous, and the id is what the colour jitter is seeded from.
    """
    if node.get("name"):
        return str(node["name"])
    for candidate in gltf["nodes"]:
        if index in candidate.get("children", []) and candidate.get("name"):
            return str(candidate["name"])
    return f"node_{index}"


def _node_matrix(node: dict[str, Any]) -> np.ndarray:
    """A node's local transform as a row-major 4x4.

    glTF stores `matrix` in **column-major** order, so the transpose is not
    cosmetic: without it the LandsD Z-up-to-Y-up rotation comes back as its
    inverse and every building lies on its side.
    """
    if "matrix" in node:
        return np.asarray(node["matrix"], dtype=np.float64).reshape(4, 4).T

    matrix = np.eye(4)
    if "rotation" in node:
        matrix[:3, :3] = _quaternion_to_matrix(node["rotation"])
    if "scale" in node:
        matrix[:3, :3] *= np.asarray(node["scale"], dtype=np.float64)
    if "translation" in node:
        matrix[:3, 3] = node["translation"]
    return matrix


def _quaternion_to_matrix(quaternion: Sequence[float]) -> np.ndarray:
    x, y, z, w = (float(v) for v in quaternion)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def _primitive(
    gltf: dict[str, Any],
    primitive: dict[str, Any],
    transform: np.ndarray,
    buffers: _BufferCache,
    name: str,
) -> MeshData:
    mode = primitive.get("mode", _MODE_TRIANGLES)
    if mode != _MODE_TRIANGLES:
        raise ValueError(f"mesh '{name}': only triangle primitives are supported, got mode {mode}")

    attributes = primitive["attributes"]
    positions = buffers.accessor(attributes["POSITION"]).astype(np.float64)
    positions = positions @ transform[:3, :3].T + transform[:3, 3]
    triangles = _triangles(primitive, buffers, len(positions))

    if "NORMAL" in attributes:
        # Rotation only: the LandsD node matrices are orthonormal, so the
        # inverse transpose reduces to the rotation itself.
        normals = buffers.accessor(attributes["NORMAL"]).astype(np.float64)
        normals = normalise(normals @ transform[:3, :3].T).astype(np.float32)
    else:
        normals = _face_normals(positions, triangles)

    uvs = None
    if "TEXCOORD_0" in attributes:
        uvs = buffers.accessor(attributes["TEXCOORD_0"]).astype(np.float32)

    uv2 = None
    if "TEXCOORD_1" in attributes:
        uv2 = buffers.accessor(attributes["TEXCOORD_1"]).astype(np.float32)

    colours = None
    if "COLOR_0" in attributes:
        colours = _as_rgba8(buffers.accessor(attributes["COLOR_0"]))

    return MeshData(
        name=name,
        positions=positions,
        normals=normals,
        triangles=triangles,
        colours=colours,
        uvs=uvs,
        uv2=uv2,
        texture=_texture(gltf, primitive, buffers),
    )


def _as_rgba8(values: np.ndarray) -> np.ndarray:
    """COLOR_0 in any encoding glTF permits, as RGBA bytes.

    Normalising on read means one representation reaches the rest of the
    pipeline. The alpha default is opaque, since RGB is a legal COLOR_0 and a
    zeroed alpha would render the mesh invisible.

    (The LandsD source is a uniform 0.8 grey on every vertex of every building,
    so `buildings.py` replaces it outright. This exists so that what this module
    writes, it can also read.)
    """
    if values.dtype == np.float32:
        channels = np.clip(values, 0.0, 1.0) * 255.0
    elif values.dtype == np.uint16:
        channels = values / 257.0
    else:
        channels = values.astype(np.float64)

    rgba = np.full((len(values), 4), 255, dtype=np.uint8)
    rgba[:, : channels.shape[1]] = np.rint(channels).astype(np.uint8)
    return rgba


def _triangles(primitive: dict[str, Any], buffers: _BufferCache, vertices: int) -> np.ndarray:
    if "indices" not in primitive:
        return np.arange(vertices, dtype=np.uint32).reshape(-1, 3)
    return buffers.accessor(primitive["indices"]).astype(np.uint32).reshape(-1, 3)


def _texture(
    gltf: dict[str, Any], primitive: dict[str, Any], buffers: _BufferCache
) -> Texture | None:
    if "material" not in primitive:
        return None
    pbr = gltf["materials"][primitive["material"]].get("pbrMetallicRoughness", {})
    if "baseColorTexture" not in pbr:
        return None

    return buffers.texture(gltf["textures"][pbr["baseColorTexture"]["index"]]["source"])


def _mime_type(uri: str) -> str:
    suffix = Path(uri).suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    raise ValueError(f"unsupported texture format {suffix!r} for {uri}")


def normalise(vectors: np.ndarray) -> np.ndarray:
    """Scale rows to unit length, leaving zero-length rows at zero."""
    lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
    return np.divide(vectors, lengths, out=np.zeros_like(vectors), where=lengths > 0)


def triangle_cross(positions: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """(m, 3) cross product of each triangle's two edge vectors.

    A free function as well as a `MeshData` method because the read path needs
    it before there is a mesh to ask.
    """
    corners = positions[triangles]
    return np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])


def _face_normals(positions: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Per-vertex normals from face winding, for sources that ship none.

    Requires unshared vertices, and checks rather than assuming: the assignment
    below is last-write-wins, so on an indexed mesh a shared vertex would
    silently take whichever face happened to be written last. That is a wrong
    normal with no error attached — the failure mode this module exists to
    avoid.
    """
    if len(np.unique(triangles)) != triangles.size:
        raise ValueError(
            "cannot derive flat normals for a mesh with shared vertices; "
            "the source must supply NORMAL"
        )
    face = triangle_cross(positions, triangles)
    per_vertex = np.zeros_like(positions)
    per_vertex[triangles.reshape(-1)] = np.repeat(normalise(face), 3, axis=0)
    return per_vertex.astype(np.float32)


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------


def write_glb(path: Path, meshes: Sequence[MeshData]) -> int:
    """Write a binary glTF and return its size in bytes.

    One node, mesh, primitive and material per entry, so the entry count is the
    tile's draw-call count — which is the thing `P1-2`'s acceptance criteria
    are stated in.
    """
    if not meshes:
        raise ValueError(f"refusing to write {path} with no meshes")

    gltf: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "hk-taxi-Q etl"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(meshes)))}],
        "nodes": [],
        "meshes": [],
        "materials": [],
        "accessors": [],
        "bufferViews": [],
    }
    binary = bytearray()
    textures: dict[int, int] = {}

    for mesh in meshes:
        attributes = {
            "POSITION": _accessor(
                gltf, binary, mesh.positions.astype(np.float32), "VEC3", _FLOAT, _ARRAY_BUFFER
            ),
            "NORMAL": _accessor(
                gltf, binary, mesh.normals.astype(np.float32), "VEC3", _FLOAT, _ARRAY_BUFFER
            ),
        }
        if mesh.colours is not None:
            # VEC4 rather than VEC3 because glTF requires each vertex attribute
            # element to start on a 4-byte boundary, and a 3-byte RGB does not.
            attributes["COLOR_0"] = _accessor(
                gltf,
                binary,
                np.asarray(mesh.colours, dtype=np.uint8),
                "VEC4",
                _UNSIGNED_BYTE,
                _ARRAY_BUFFER,
                normalized=True,
            )
        if mesh.uvs is not None:
            attributes["TEXCOORD_0"] = _accessor(
                gltf, binary, mesh.uvs.astype(np.float32), "VEC2", _FLOAT, _ARRAY_BUFFER
            )
        if mesh.uv2 is not None:
            attributes["TEXCOORD_1"] = _accessor(
                gltf, binary, mesh.uv2.astype(np.float32), "VEC2", _FLOAT, _ARRAY_BUFFER
            )

        index_dtype = np.uint16 if len(mesh.positions) <= _UINT16_LIMIT else np.uint32
        indices = _accessor(
            gltf,
            binary,
            mesh.triangles.astype(index_dtype).reshape(-1),
            "SCALAR",
            _UNSIGNED_SHORT if index_dtype is np.uint16 else _UNSIGNED_INT,
            _ELEMENT_ARRAY_BUFFER,
        )

        gltf["meshes"].append(
            {
                "name": mesh.name,
                "primitives": [
                    {
                        "attributes": attributes,
                        "indices": indices,
                        "material": _material(gltf, binary, mesh, textures),
                        "mode": _MODE_TRIANGLES,
                    }
                ],
            }
        )
        gltf["nodes"].append({"name": mesh.name, "mesh": len(gltf["meshes"]) - 1})

    gltf["buffers"] = [{"byteLength": len(binary)}]
    return _write_container(path, gltf, binary)


def _material(
    gltf: dict[str, Any], binary: bytearray, mesh: MeshData, textures: dict[int, int]
) -> int:
    material: dict[str, Any] = {
        "name": mesh.material or f"{mesh.name}_material",
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            # Flat-shaded massing under a low sun. Any metallic response reads
            # as wet plastic on an untextured volume.
            "metallicFactor": 0.0,
            "roughnessFactor": 0.9,
        },
    }
    if mesh.texture is not None:
        material["pbrMetallicRoughness"]["baseColorTexture"] = {
            "index": _texture_index(gltf, binary, mesh.texture, textures)
        }

    gltf["materials"].append(material)
    return len(gltf["materials"]) - 1


def _texture_index(
    gltf: dict[str, Any], binary: bytearray, texture: Texture, seen: dict[int, int]
) -> int:
    """Embed an image once however many meshes share it.

    Keyed on identity rather than content: hashing a 39 MB terrain JPEG to
    discover it equals itself costs more than the duplicate would. Identity is
    meaningful because `_BufferCache.texture` hands out one `Texture` per image
    per document — sharing the bytes alone would not be enough.
    """
    key = id(texture)
    if key in seen:
        return seen[key]

    gltf.setdefault("samplers", [{"wrapS": 33071, "wrapT": 33071}])
    gltf.setdefault("images", []).append(
        {
            "bufferView": _buffer_view(gltf, binary, texture.data, target=None),
            "mimeType": texture.mime_type,
        }
    )
    gltf.setdefault("textures", []).append({"source": len(gltf["images"]) - 1, "sampler": 0})
    seen[key] = len(gltf["textures"]) - 1
    return seen[key]


def _buffer_view(
    gltf: dict[str, Any], binary: bytearray, payload: bytes, *, target: int | None
) -> int:
    _pad(binary)
    view: dict[str, Any] = {
        "buffer": 0,
        "byteOffset": len(binary),
        "byteLength": len(payload),
    }
    if target is not None:
        view["target"] = target
    binary.extend(payload)
    gltf["bufferViews"].append(view)
    return len(gltf["bufferViews"]) - 1


def _accessor(
    gltf: dict[str, Any],
    binary: bytearray,
    values: np.ndarray,
    element_type: str,
    component_type: int,
    target: int,
    *,
    normalized: bool = False,
) -> int:
    accessor: dict[str, Any] = {
        "bufferView": _buffer_view(gltf, binary, values.tobytes(), target=target),
        "componentType": component_type,
        "count": len(values),
        "type": element_type,
    }
    if normalized:
        accessor["normalized"] = True
    if element_type == "VEC3" and component_type == _FLOAT:
        # The spec requires min/max on POSITION. Cheap enough to record on every
        # float VEC3, and viewers use it to frame the scene.
        accessor["min"] = values.min(axis=0).tolist()
        accessor["max"] = values.max(axis=0).tolist()
    gltf["accessors"].append(accessor)
    return len(gltf["accessors"]) - 1


def _pad(buffer: bytearray, fill: int = 0) -> None:
    buffer.extend(bytes([fill]) * (-len(buffer) % 4))


def _write_container(path: Path, gltf: dict[str, Any], binary: bytes) -> int:
    json_chunk = bytearray(json.dumps(gltf, separators=(",", ":")).encode("utf-8"))
    # Trailing space, not NUL: the spec requires the JSON chunk be padded with
    # 0x20 so it stays parseable text, and 0x00 makes strict readers reject it.
    _pad(json_chunk, fill=0x20)

    # Padded on the way out rather than into a copy. A terrain sheet's buffer
    # holds a 39 MB JPEG, and copying it to append at most three zero bytes put
    # three of them in memory at once.
    bin_padding = -len(binary) % 4
    bin_length = len(binary) + bin_padding

    total = _GLB_HEADER_BYTES + 2 * _CHUNK_HEADER_BYTES + len(json_chunk) + bin_length
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(struct.pack("<III", _GLB_MAGIC, _GLB_VERSION, total))
        handle.write(struct.pack("<II", len(json_chunk), _CHUNK_JSON))
        handle.write(json_chunk)
        handle.write(struct.pack("<II", bin_length, _CHUNK_BIN))
        handle.write(binary)
        handle.write(bytes(bin_padding))
    return total


def read_glb(path: Path) -> list[MeshData]:
    """Read back a GLB this module wrote. Exists for tests and inspection."""
    raw = path.read_bytes()
    magic, version, _ = struct.unpack_from("<III", raw, 0)
    if magic != _GLB_MAGIC or version != _GLB_VERSION:
        raise ValueError(f"{path} is not a glTF 2.0 binary container")

    chunks: dict[int, bytes] = {}
    offset = _GLB_HEADER_BYTES
    while offset < len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += _CHUNK_HEADER_BYTES
        chunks[kind] = raw[offset : offset + length]
        offset += length

    binary = chunks[_CHUNK_BIN]
    document = json.loads(chunks[_CHUNK_JSON])
    # `read_scene` resolves buffers by URI; a GLB has none, so hand it the one
    # embedded chunk under the empty URI its buffer entry lacks.
    for buffer in document["buffers"]:
        buffer["uri"] = ""
    return read_scene(json.dumps(document), lambda _uri: binary)
