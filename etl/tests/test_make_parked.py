"""`tools/make_parked.py` — the parked roster's library (`P3-72`, `Q161`).

What is pinned: the committed bytes against the generator, so an edit to a
proportion is a rebuild; every kind's footprint against the one
`hong_kong.yaml` places by, because the ETL stands a vehicle by those two
numbers and the engine draws the mesh, and a kind whose two disagree is a car
drawn through the kerb; the frame (nose north, ground at zero, centred);
the material door every part goes through; and the winding, for the reason
`test_make_vehicle.py` gives — wound inward, a wheel renders as a hole.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from pipeline.config import load_config
from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from make_parked import (  # noqa: E402
    LIBRARY_FILE,
    SHAPES,
    _glasshouse,
    _lower,
    build_roster,
    write_roster,
)
from make_vehicle import LAMP, MATERIAL_OF_PAYLOAD, material_parts  # noqa: E402

SHIPPED = ROOT / "game" / "assets" / "authored" / "vehicles"
# `ART_DESIGN.md`'s upper bar per vehicle.
TRIANGLE_CEILING = 2000
# The library's footprint may differ from the config's by this much: a wheel
# of ten segments does not reach its own radius exactly.
FOOTPRINT_SLACK_M = 0.05


@pytest.fixture(scope="module")
def meshes() -> list[MeshData]:
    return build_roster()


@pytest.fixture(scope="module")
def by_name(meshes: list[MeshData]) -> dict[str, MeshData]:
    return {mesh.name: mesh for mesh in meshes}


class TestShippedAssets:
    def test_the_committed_library_matches_the_generator(self, tmp_path: Path) -> None:
        path, _, _ = write_roster(tmp_path)
        shipped = SHIPPED / LIBRARY_FILE
        assert shipped.exists(), f"{shipped.name} is not committed"
        assert shipped.read_bytes() == path.read_bytes(), (
            f"{shipped.name} is stale — re-run tools/make_parked.py"
        )


class TestTheFootprintIsTheConfigs:
    """🔴 The ETL places by `parked.vehicles:`; the engine draws this."""

    def test_every_config_kind_has_a_library_mesh(self, by_name: dict[str, MeshData]) -> None:
        city = load_config()
        assert city.parked is not None
        for vehicle in city.parked.vehicles.values():
            for mesh_name in vehicle.library_meshes:
                assert mesh_name in by_name, f"{vehicle.kind} names {mesh_name}, not in the library"

    def test_every_library_mesh_is_a_config_kind(self, by_name: dict[str, MeshData]) -> None:
        city = load_config()
        assert city.parked is not None
        named = {m for v in city.parked.vehicles.values() for m in v.library_meshes}
        assert set(by_name) == named

    def test_length_and_width_match_the_config(self, by_name: dict[str, MeshData]) -> None:
        city = load_config()
        assert city.parked is not None
        for vehicle in city.parked.vehicles.values():
            for mesh_name in vehicle.library_meshes:
                low, high = by_name[mesh_name].aabb()
                assert abs((high[0] - low[0]) - vehicle.width_m) <= FOOTPRINT_SLACK_M, mesh_name
                assert abs((high[2] - low[2]) - vehicle.length_m) <= FOOTPRINT_SLACK_M, mesh_name


class TestTheFrame:
    def test_the_ground_is_zero_and_the_body_is_centred(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            low, high = mesh.aabb()
            assert abs(low[1]) < 1e-6, f"{mesh.name} floats {low[1]:.3f} m"
            assert low[0] < 0.0 < high[0] and low[2] < 0.0 < high[2], mesh.name

    def test_the_nose_is_north(self, meshes: list[MeshData]) -> None:
        """The head lamps — the one `LAMP`-coloured part on every kind — sit
        at negative z, where `placed_positions` stands a bearing's nose."""
        for mesh in meshes:
            lamp = np.all(mesh.colours[:, :3] == np.array(LAMP, dtype=np.uint8), axis=1)
            assert lamp.any(), f"{mesh.name} has no head lamp"
            assert mesh.positions[lamp, 2].max() < 0.0, f"{mesh.name}'s lamps are not at the nose"


class TestTheBudget:
    def test_each_kind_is_under_the_ceiling(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            assert mesh.triangle_count <= TRIANGLE_CEILING, mesh.name

    def test_each_kind_is_within_a_few_flat_colours(self, meshes: list[MeshData]) -> None:
        """`ART_DESIGN.md`'s 3 to 5, plus the three lens colours every vehicle
        carries, is the standing exception the taxi already holds."""
        for mesh in meshes:
            colours = {tuple(int(v) for v in row[:3]) for row in mesh.colours}
            assert 3 <= len(colours) <= 8, f"{mesh.name} carries {len(colours)} colours"

    def test_every_part_goes_through_the_material_door(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            group = material_parts(mesh)
            names = {part.material for part in group.parts}
            assert names <= set(MATERIAL_OF_PAYLOAD.values()), mesh.name
            assert "vehicle_paint" in names, mesh.name
            assert any(name.startswith("vehicle_lamp") for name in names), mesh.name


class TestWinding:
    @staticmethod
    def _outward_fraction(mesh: MeshData) -> float:
        centre = mesh.positions.mean(axis=0)
        face_normals = mesh.normals[mesh.triangles[:, 0]]
        return float((((mesh.triangle_centroids() - centre) * face_normals).sum(axis=1) > 0).mean())

    def test_no_triangle_is_degenerate(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            areas = np.linalg.norm(mesh.triangle_cross(), axis=1)
            assert (areas > 1e-9).all(), f"{mesh.name} has {(areas <= 1e-9).sum()} degenerate"

    def test_every_loft_faces_outward(self) -> None:
        """The two lofts every body is built from are convex solids, so every
        face points away from their centre — wound the other way, `cull_back`
        renders the car as its own inside."""
        for shape in SHAPES:
            if shape.single_track:
                continue
            assert self._outward_fraction(_lower(shape)) == 1.0, shape.kind
            assert (
                self._outward_fraction(
                    _glasshouse(
                        shape, shape.belt_y_m, shape.roof_y_m, shape.roof, name="g", cap=True
                    )
                )
                == 1.0
            ), shape.kind

    def test_every_body_encloses_a_positive_volume(self, meshes: list[MeshData]) -> None:
        """The signed volume of the whole mesh: inward-wound parts subtract."""
        for mesh in meshes:
            tri = mesh.positions[mesh.triangles]
            volume = (
                float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()) / 6.0
            )
            low, high = mesh.aabb()
            box = float(np.prod(np.asarray(high) - np.asarray(low)))
            # A tenth: a motorcycle is mostly air and reads 0.12 of its box.
            assert volume > 0.1 * box, f"{mesh.name} encloses {volume:.2f} of a {box:.2f} m³ box"


class TestTheRoster:
    def test_the_kinds_are_distinct_and_named_after_their_shape(self) -> None:
        names = [shape.kind for shape in SHAPES]
        assert len(names) == len(set(names))
        for shape, mesh in zip(SHAPES, build_roster(), strict=True):
            assert mesh.name == shape.kind
