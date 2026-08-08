"""glTF read/write tests.

The reader's job is to be *strict*: this format has many ways to say the same
thing, the LandsD files use one of them, and quietly mis-reading any of the
others puts a building somewhere plausible and wrong. So most of these check
that unsupported input raises rather than that supported input works.
"""

from __future__ import annotations

import json
import struct
from dataclasses import replace

import numpy as np
import pytest

from pipeline.gltf import MeshData, Texture, read_glb, read_scene, write_glb

# The rotation LandsD ships on every node: local Z-up to Godot's Y-up, with the
# grid position in the translation column. Column-major, as glTF requires.
LANDSD_MATRIX = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 836567.5, 3.61, -815718.25, 1]


def triangle_document(matrix: list[float] | None = None, **overrides) -> tuple[bytes, bytes]:
    """One triangle in a two-node scene, shaped like the LandsD files."""
    positions = np.array([[0, 0, 0], [10, 0, 0], [0, 20, 5]], dtype="<f4")
    normals = np.array([[0, 0, 1]] * 3, dtype="<f4")
    indices = np.array([0, 1, 2], dtype="<u2")
    binary = positions.tobytes() + normals.tobytes() + indices.tobytes()

    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {"name": "B0001", "matrix": matrix or LANDSD_MATRIX, "children": [1]},
            {"mesh": 0},
        ],
        "meshes": [
            {"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "mode": 4}]}
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": 2, "componentType": 5123, "count": 3, "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 36},
            {"buffer": 0, "byteOffset": 36, "byteLength": 36},
            {"buffer": 0, "byteOffset": 72, "byteLength": 6},
        ],
        "buffers": [{"uri": "b.bin", "byteLength": len(binary)}],
    }
    document.update(overrides)
    return json.dumps(document).encode(), binary


def read_one(document: bytes, binary: bytes) -> MeshData:
    return read_scene(document, lambda _uri: binary)[0]


class TestNodeTransforms:
    def test_matrix_is_read_column_major(self) -> None:
        """The single most expensive thing to get wrong in this module.

        Read row-major, the LandsD rotation comes back as its inverse: every
        building lies on its side, and the mistake is only visible in 3D.
        """
        mesh = read_one(*triangle_document())

        # Local (10, 0, 0) is 10 m east; local (0, 20, 5) is 20 m *north* and
        # 5 m up, so it must land at -20 on z and +5 on y.
        assert mesh.positions[0] == pytest.approx([836567.5, 3.61, -815718.25])
        assert mesh.positions[1] == pytest.approx([836577.5, 3.61, -815718.25])
        assert mesh.positions[2] == pytest.approx([836567.5, 8.61, -815738.25])

    def test_normals_are_rotated_but_not_translated(self) -> None:
        mesh = read_one(*triangle_document())
        # Local +Z (up) becomes Godot +Y, and stays a unit vector.
        assert mesh.normals[0] == pytest.approx([0.0, 1.0, 0.0])

    def test_positions_are_float64(self) -> None:
        """float32 spacing at 836,000 m is 6 cm — coarser than a kerb."""
        mesh = read_one(*triangle_document())
        assert mesh.positions.dtype == np.float64

    def test_trs_nodes_are_supported(self) -> None:
        document, binary = triangle_document(matrix=None)
        parsed = json.loads(document)
        parsed["nodes"][0] = {"name": "B0001", "translation": [1.0, 2.0, 3.0], "children": [1]}
        mesh = read_one(json.dumps(parsed).encode(), binary)
        assert mesh.positions[0] == pytest.approx([1.0, 2.0, 3.0])

    def test_mesh_takes_the_name_of_its_named_parent(self) -> None:
        """LandsD puts the building id on the parent and leaves the child
        anonymous. The id seeds the colour jitter, so losing it repaints the
        city with one shared value."""
        assert read_one(*triangle_document()).name == "B0001"


class TestUnsupportedInput:
    @pytest.mark.parametrize(
        ("mutate", "message"),
        [
            (lambda d: d["meshes"][0]["primitives"][0].update(mode=1), "triangle"),
            (lambda d: d["accessors"][0].update(sparse={}), "sparse"),
            (lambda d: d["accessors"][0].update(type="VEC5"), "accessor type"),
            (lambda d: d["accessors"][0].update(componentType=9999), "componentType"),
            (lambda d: d["bufferViews"][0].update(byteStride=64), "interleaved"),
            (lambda d: d["buffers"][0].pop("uri"), "GLB-embedded"),
        ],
    )
    def test_it_raises_rather_than_guessing(self, mutate, message: str) -> None:
        document, binary = triangle_document()
        parsed = json.loads(document)
        mutate(parsed)
        with pytest.raises(ValueError, match=message):
            read_one(json.dumps(parsed).encode(), binary)

    def test_a_missing_index_buffer_means_one_triangle_per_three_vertices(self) -> None:
        document, binary = triangle_document()
        parsed = json.loads(document)
        parsed["meshes"][0]["primitives"][0].pop("indices")
        mesh = read_one(json.dumps(parsed).encode(), binary)
        assert mesh.triangles.tolist() == [[0, 1, 2]]


class TestWriting:
    def box(self, colour: int = 200) -> MeshData:
        positions = np.array(
            [[0, 0, 0], [10, 0, 0], [0, 0, 10], [10, 0, 0], [10, 0, 10], [0, 0, 10]],
            dtype=np.float64,
        )
        return MeshData(
            name="tile",
            positions=positions,
            normals=np.tile(np.array([0, 1, 0], dtype=np.float32), (6, 1)),
            triangles=np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
            colours=np.tile(np.array([colour, colour, colour, 255], np.uint8), (6, 1)),
        )

    def document_of(self, path) -> dict:
        raw = path.read_bytes()
        length, _ = struct.unpack_from("<II", raw, 12)
        return json.loads(raw[20 : 20 + length])

    def test_round_trip_preserves_geometry(self, tmp_path) -> None:
        original = self.box()
        write_glb(tmp_path / "t.glb", [original])
        [restored] = read_glb(tmp_path / "t.glb")

        assert restored.positions == pytest.approx(original.positions)
        assert restored.triangles.tolist() == original.triangles.tolist()

    def test_declared_length_matches_the_file(self, tmp_path) -> None:
        size = write_glb(tmp_path / "t.glb", [self.box()])
        raw = (tmp_path / "t.glb").read_bytes()
        assert struct.unpack_from("<III", raw, 0)[2] == len(raw) == size

    def test_buffer_views_are_four_byte_aligned(self, tmp_path) -> None:
        """glTF requires it, and a misaligned view is the kind of thing one
        reader tolerates and the next rejects."""
        write_glb(tmp_path / "t.glb", [self.box()])
        for view in self.document_of(tmp_path / "t.glb")["bufferViews"]:
            assert view["byteOffset"] % 4 == 0

    def test_colours_are_marked_normalized(self, tmp_path) -> None:
        """Measured against Godot 4.7: drop `normalized` and every byte colour
        reads as 1.0, so the whole city renders white with no error anywhere."""
        write_glb(tmp_path / "t.glb", [self.box()])
        document = self.document_of(tmp_path / "t.glb")
        colour = document["accessors"][
            document["meshes"][0]["primitives"][0]["attributes"]["COLOR_0"]
        ]
        assert colour["normalized"] is True
        assert colour["type"] == "VEC4"
        assert colour["componentType"] == 5121

    def test_a_material_name_is_shipped_when_the_engine_has_to_recognise_it(self, tmp_path) -> None:
        """`P3-7`: a tile asks for the window-band shader by naming its material,
        because glTF offers no other channel and the payload that distinguishes a
        tile — `TEXCOORD_0` — is what the road surface uses for lane coordinates.

        Asserted from the file rather than from `MeshData`, because it is the
        bytes Godot's importer reads."""
        write_glb(tmp_path / "t.glb", [replace(self.box(), material="city_facade")])
        document = self.document_of(tmp_path / "t.glb")

        assert document["materials"][0]["name"] == "city_facade"

    def test_a_mesh_that_names_no_material_is_labelled_after_itself(self, tmp_path) -> None:
        """Unchanged for every other asset. Roads and vehicles keep a material
        named for the mesh, which is a label rather than a contract — and keeps
        them on the default `BaseMaterial3D` at import."""
        write_glb(tmp_path / "t.glb", [self.box()])

        assert self.document_of(tmp_path / "t.glb")["materials"][0]["name"] == "tile_material"

    def test_untextured_meshes_carry_no_image(self, tmp_path) -> None:
        """`P1-2` accepts no textures in the tile output at all."""
        write_glb(tmp_path / "t.glb", [self.box()])
        document = self.document_of(tmp_path / "t.glb")
        assert "images" not in document
        assert "textures" not in document

    def test_one_primitive_per_mesh(self, tmp_path) -> None:
        """Draw calls are counted in primitives, and the tile budget is three."""
        write_glb(tmp_path / "t.glb", [self.box()])
        for mesh in self.document_of(tmp_path / "t.glb")["meshes"]:
            assert len(mesh["primitives"]) == 1

    def test_small_meshes_use_uint16_indices(self, tmp_path) -> None:
        write_glb(tmp_path / "t.glb", [self.box()])
        document = self.document_of(tmp_path / "t.glb")
        indices = document["accessors"][document["meshes"][0]["primitives"][0]["indices"]]
        assert indices["componentType"] == 5123

    def test_large_meshes_fall_back_to_uint32_indices(self, tmp_path) -> None:
        count = 70_002  # a multiple of 3, and over the uint16 ceiling
        mesh = MeshData(
            name="big",
            positions=np.zeros((count, 3)),
            normals=np.zeros((count, 3), dtype=np.float32),
            triangles=np.arange(count, dtype=np.uint32).reshape(-1, 3),
        )
        write_glb(tmp_path / "t.glb", [mesh])
        document = self.document_of(tmp_path / "t.glb")
        indices = document["accessors"][document["meshes"][0]["primitives"][0]["indices"]]
        assert indices["componentType"] == 5125

    def test_positions_carry_min_and_max(self, tmp_path) -> None:
        write_glb(tmp_path / "t.glb", [self.box()])
        document = self.document_of(tmp_path / "t.glb")
        position = document["accessors"][
            document["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
        ]
        assert position["min"] == [0.0, 0.0, 0.0]
        assert position["max"] == [10.0, 0.0, 10.0]

    def test_textures_round_trip(self, tmp_path) -> None:
        textured = MeshData(
            name="ground",
            positions=self.box().positions,
            normals=self.box().normals,
            triangles=self.box().triangles,
            uvs=np.zeros((6, 2), dtype=np.float32),
            texture=Texture(data=b"\xff\xd8\xff not really a jpeg", mime_type="image/jpeg"),
        )
        write_glb(tmp_path / "t.glb", [textured])
        [restored] = read_glb(tmp_path / "t.glb")
        assert restored.texture is not None
        assert restored.texture.data == textured.texture.data

    def test_uv2_round_trips_exactly_and_sits_beside_texcoord_0(self, tmp_path) -> None:
        """Schema 6: the survey payload is integer state codes, so the file
        must hand back the exact floats it was given — approx would hide the
        one corruption that matters."""
        surveyed = replace(
            self.box(),
            uvs=np.zeros((6, 2), dtype=np.float32),
            uv2=np.tile(np.array([6082.0, 0.0], dtype=np.float32), (6, 1)),
        )
        write_glb(tmp_path / "t.glb", [surveyed])

        document = self.document_of(tmp_path / "t.glb")
        attributes = document["meshes"][0]["primitives"][0]["attributes"]
        assert {"TEXCOORD_0", "TEXCOORD_1"} <= set(attributes)
        accessor = document["accessors"][attributes["TEXCOORD_1"]]
        assert accessor["type"] == "VEC2"
        assert accessor["componentType"] == 5126

        [restored] = read_glb(tmp_path / "t.glb")
        assert restored.uv2 is not None
        assert (restored.uv2 == surveyed.uv2).all()

    def test_writing_nothing_is_an_error(self, tmp_path) -> None:
        """An empty tile is a bug upstream, and an empty GLB hides it."""
        with pytest.raises(ValueError, match="no meshes"):
            write_glb(tmp_path / "t.glb", [])


def test_attribute_length_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="colours"):
        MeshData(
            name="bad",
            positions=np.zeros((3, 3)),
            normals=np.zeros((3, 3), dtype=np.float32),
            triangles=np.array([[0, 1, 2]]),
            colours=np.zeros((2, 4), dtype=np.uint8),
        )
    with pytest.raises(ValueError, match="uv2"):
        MeshData(
            name="bad",
            positions=np.zeros((3, 3)),
            normals=np.zeros((3, 3), dtype=np.float32),
            triangles=np.array([[0, 1, 2]]),
            uv2=np.zeros((2, 2), dtype=np.float32),
        )
