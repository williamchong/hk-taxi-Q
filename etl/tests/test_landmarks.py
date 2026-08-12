"""The mesh-sourced hero stage (`P3-6` amendment): slice, repaint, emit.

Three layers, mirroring the module. The slicer and the paint are pure
geometry, tested on hand-built meshes where every triangle's fate is
checkable by eye. `build_assets` is tested end-to-end on a synthetic sheet
zip — the `test_buildings.py` fixture pattern — because its work is exactly
the plumbing (stem match, local frame, budget gate, document shape) that a
unit test of the parts cannot see fail.
"""

from __future__ import annotations

import json
import struct
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pipeline.buildings import COLLISION_SUFFIX
from pipeline.config import Landmark, Material, SourcePaint
from pipeline.gltf import MeshData, read_glb
from pipeline.landmarks import (
    ASSETS_SCHEMA,
    LANDMARK_MATERIAL,
    Reference,
    _band_planes,
    _tag_parents,
    build_assets,
    paint,
)
from pipeline.mesh import merge, slice_horizontal, weld
from tests.test_buildings import Fixture, _to_source

WALL = Material("wall", (134, 128, 119), 42.0, "test")
RIBBON = Material("ribbon", (61, 72, 83), 12.0, "test")
ROOF = Material("roof", (90, 96, 99), 22.0, "test")
BASE = Material("base", (114, 110, 102), 30.0, "test")

PAINT = SourcePaint(
    wall=WALL,
    ribbon=RIBBON,
    roof=ROOF,
    base=BASE,
    ribbon_first_m=15.0,
    ribbon_pitch_m=4.8,
    ribbon_thickness_m=1.5,
    ribbon_count=10,
    base_below_m=8.0,
)


def tri(
    corners: list[list[float]], *, normal: list[float] | None = None, colour=(200, 200, 200, 255)
) -> MeshData:
    """One unshared triangle, with a face-constant normal."""
    positions = np.asarray(corners, dtype=np.float64)
    if normal is None:
        edge = np.cross(positions[1] - positions[0], positions[2] - positions[0])
        normal = (edge / np.linalg.norm(edge)).tolist()
    return MeshData(
        name="t",
        positions=positions,
        normals=np.asarray([normal] * 3, dtype=np.float32),
        triangles=np.asarray([[0, 1, 2]], dtype=np.uint32),
        colours=np.asarray([colour] * 3, dtype=np.uint8),
    )


def area(mesh: MeshData) -> float:
    return float(np.linalg.norm(mesh.triangle_cross(), axis=1).sum() / 2.0)


def material_names(path: Path) -> list[str]:
    """The glTF material names, straight from the binary's JSON chunk."""
    raw = path.read_bytes()
    length, _ = struct.unpack_from("<II", raw, 12)
    document = json.loads(raw[20 : 20 + length])
    return [material["name"] for material in document.get("materials", [])]


def spans(mesh: MeshData, height: float) -> bool:
    y = mesh.positions[mesh.triangles][:, :, 1]
    return bool(((y.min(axis=1) < height - 1e-9) & (y.max(axis=1) > height + 1e-9)).any())


class TestSliceHorizontal:
    def test_a_crossing_triangle_splits_and_keeps_its_area(self) -> None:
        wall = tri([[0.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0]])
        out = slice_horizontal(wall, [4.0])

        assert out.triangle_count == 3
        assert area(out) == pytest.approx(area(wall))
        assert not spans(out, 4.0)

    def test_a_plane_through_a_vertex_splits_into_two(self) -> None:
        """One on-plane corner means one cut edge — 2 triangles, not 3, and
        never a zero-area sliver shaved off the corner."""
        wall = tri([[0.0, 5.0, 0.0], [3.0, 0.0, 0.0], [3.0, 10.0, 0.0]])
        out = slice_horizontal(wall, [5.0])

        assert out.triangle_count == 2
        assert area(out) == pytest.approx(area(wall))

    def test_a_plane_outside_the_mesh_is_a_no_op(self) -> None:
        wall = tri([[0.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0]])
        assert slice_horizontal(wall, [99.0]).triangle_count == 1

    def test_neighbours_cut_the_shared_edge_bit_identically(self) -> None:
        """Two triangles walk their shared diagonal in opposite winding; the
        lower-endpoint-first interpolation makes both cuts the same bits, so
        the sliced surface stays closed."""
        quad = MeshData(
            name="q",
            positions=np.asarray(
                [
                    [0.0, 0.0, 0.0],
                    [5.0, 10.0, 0.0],
                    [0.0, 10.0, 0.0],
                    [0.0, 0.0, 0.0],
                    [5.0, 0.0, 0.0],
                    [5.0, 10.0, 0.0],
                ],
                dtype=np.float64,
            ),
            normals=np.asarray([[0.0, 0.0, 1.0]] * 6, dtype=np.float32),
            triangles=np.asarray([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
        )
        out = slice_horizontal(quad, [3.7])

        cut = out.positions[np.isclose(out.positions[:, 1], 3.7)]
        diagonal = cut[np.isclose(cut[:, 0], 5.0 * 3.7 / 10.0)]
        assert len(diagonal) >= 2
        assert len(np.unique(diagonal, axis=0)) == 1

    def test_normals_and_colours_survive_the_cut(self) -> None:
        wall = tri([[0.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0]], colour=(10, 20, 30, 255))
        out = slice_horizontal(wall, [4.0, 6.0])

        assert np.allclose(out.normals, [0.0, 0.0, 1.0])
        assert (out.colours == (10, 20, 30, 255)).all()

    def test_the_output_is_unshared(self) -> None:
        """Three vertices per triangle — the invariant `paint` colours by."""
        wall = tri([[0.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0]])
        out = slice_horizontal(wall, [4.0])
        assert len(out.positions) == 3 * out.triangle_count


class TestWeld:
    def test_agreeing_duplicates_collapse_and_triangles_survive(self) -> None:
        quad = MeshData(
            name="q",
            positions=np.asarray(
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]] * 2, dtype=np.float64
            ),
            normals=np.asarray([[0.0, 0.0, 1.0]] * 6, dtype=np.float32),
            triangles=np.asarray([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
            colours=np.asarray([[9, 9, 9, 255]] * 6, dtype=np.uint8),
        )
        out = weld(quad)

        assert len(out.positions) == 3
        assert out.triangle_count == 2

    def test_a_colour_boundary_is_never_welded_across(self) -> None:
        """The reason this is not `collapse(cell_m=0)`: coincident vertices on
        opposite sides of a band edge agree on position and normal, and
        welding them would bleed one band into the other."""
        pair = MeshData(
            name="p",
            positions=np.asarray(
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]] * 2, dtype=np.float64
            ),
            normals=np.asarray([[0.0, 0.0, 1.0]] * 6, dtype=np.float32),
            triangles=np.asarray([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
            colours=np.asarray([[1, 1, 1, 255]] * 3 + [[2, 2, 2, 255]] * 3, dtype=np.uint8),
        )
        out = weld(pair)

        assert len(out.positions) == 6
        assert out.triangle_count == 2


class TestPaint:
    """One triangle per rule, so a misclassification names itself."""

    def paint_one(self, mesh: MeshData) -> tuple[int, int, int]:
        out = paint(mesh, PAINT)
        colours = np.unique(out.colours[:, :3], axis=0)
        assert len(colours) == 1, "one triangle must paint one colour"
        return tuple(int(v) for v in colours[0])

    def wall_at(self, y: float) -> MeshData:
        return tri([[0.0, y, 0.0], [1.0, y, 0.0], [0.0, y + 0.5, 0.0]], normal=[0.0, 0.0, 1.0])

    def test_a_wall_between_bands_is_wall(self) -> None:
        assert self.paint_one(self.wall_at(17.0)) == WALL.colour

    def test_a_wall_inside_a_band_is_ribbon(self) -> None:
        # Band 2 spans 24.6..26.1; a triangle whose centroid is inside it.
        assert self.paint_one(self.wall_at(24.8)) == RIBBON.colour

    def test_the_band_grid_ends_at_ribbon_count(self) -> None:
        beyond = PAINT.ribbon_first_m + PAINT.ribbon_count * PAINT.ribbon_pitch_m
        assert self.paint_one(self.wall_at(beyond + 0.1)) == WALL.colour

    def test_an_up_facing_triangle_is_roof(self) -> None:
        roof = tri([[0.0, 30.0, 0.0], [1.0, 30.0, 0.0], [0.0, 30.0, 1.0]], normal=[0.0, 1.0, 0.0])
        assert self.paint_one(roof) == ROOF.colour

    def test_a_down_facing_triangle_is_base(self) -> None:
        """Soffits take the base concrete even inside a ribbon band."""
        soffit = tri(
            [[0.0, 24.8, 0.0], [1.0, 24.8, 0.0], [0.0, 24.8, 1.0]], normal=[0.0, -1.0, 0.0]
        )
        assert self.paint_one(soffit) == BASE.colour

    def test_everything_below_the_base_line_is_base(self) -> None:
        assert self.paint_one(self.wall_at(3.0)) == BASE.colour

    def test_the_paint_is_srgb_with_full_alpha(self) -> None:
        out = paint(self.wall_at(17.0), PAINT)
        assert (out.colours[:, 3] == 255).all()
        assert (out.colours[:, :3] == WALL.colour).all()


def strip_mesh() -> MeshData:
    """A vertical wall, 12 m wide and 30 m tall, as three side-by-side quads.

    Tall enough to hold ribbon levels 0-3, wide enough that each sliced band
    carries more than the five decided triangles a strip verdict requires.
    """
    quads = []
    for column in range(3):
        x0, x1 = column * 4.0, column * 4.0 + 4.0
        quads.append(
            MeshData(
                name=f"q{column}",
                positions=np.asarray(
                    [
                        [x0, 0.0, 0.0],
                        [x1, 0.0, 0.0],
                        [x1, 30.0, 0.0],
                        [x0, 0.0, 0.0],
                        [x1, 30.0, 0.0],
                        [x0, 30.0, 0.0],
                    ],
                    dtype=np.float64,
                ),
                normals=np.asarray([[0.0, 0.0, 1.0]] * 6, dtype=np.float32),
                triangles=np.asarray([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
            )
        )
    return merge(quads, name="wall")


def wall_reference(atlas: np.ndarray, mesh: MeshData) -> Reference:
    """A Reference mapping the strip mesh onto `atlas` by elevation.

    v runs 0 at the top of the wall to 1 at its base — the glTF image
    convention — so atlas row `r` shows at height `30 * (1 - r/(h-1))`.
    """
    corners = mesh.positions[mesh.triangles]
    uvs = np.zeros((len(corners), 3, 2), dtype=np.float32)
    uvs[:, :, 0] = (corners[:, :, 0] / 12.0).astype(np.float32)
    uvs[:, :, 1] = (1.0 - corners[:, :, 1] / 30.0).astype(np.float32)
    return Reference(
        corners=corners,
        uvs=uvs,
        image=np.zeros(len(corners), dtype=np.int32),
        luminance=(atlas,),
    )


class TestPhotoReference:
    """The strip verdict: whole ribbons kept or dropped by their photo."""

    def painted_strip_levels(self, atlas: np.ndarray) -> set[int]:
        mesh, _ = _tag_parents(strip_mesh(), 0)
        reference = wall_reference(atlas, mesh)
        sliced = slice_horizontal(mesh, _band_planes(PAINT))
        out = paint(sliced, PAINT, reference)
        centroids = out.positions[out.triangles].mean(axis=1)[:, 1]
        ribboned = (out.colours[out.triangles[:, 0], :3] == RIBBON.colour).all(axis=1)
        levels = np.floor((centroids - PAINT.ribbon_first_m) / PAINT.ribbon_pitch_m)
        return {int(level) for level in levels[ribboned]}

    def test_a_uniform_photo_vetoes_every_strip(self) -> None:
        """The sweep case: no glazing in the photo, no bands in the paint."""
        assert self.painted_strip_levels(np.full((300, 8), 0.5, dtype=np.float32)) == set()

    def test_dark_photo_rows_keep_their_strips(self) -> None:
        """Bands survive exactly where the photo carries dark glazing rows —
        here levels 0 and 2, under lighting three times brighter at the top
        of the wall than the bottom, which an absolute cut would misread."""
        rows = np.linspace(0.0, 30.0, 300)[::-1]  # row elevation, v convention
        lighting = 0.2 + 0.4 * (rows / 30.0)
        atlas = np.tile(lighting[:, None], (1, 8)).astype(np.float32)
        for level in (0, 2):
            low = PAINT.ribbon_first_m + level * PAINT.ribbon_pitch_m
            in_band = (rows >= low) & (rows < low + PAINT.ribbon_thickness_m)
            atlas[in_band] *= 0.4
        assert self.painted_strip_levels(atlas) == {0, 2}

    def test_the_scratch_channel_never_ships(self) -> None:
        mesh, _ = _tag_parents(strip_mesh(), 0)
        out = paint(
            slice_horizontal(mesh, [15.0]),
            PAINT,
            wall_reference(np.full((16, 8), 0.5, dtype=np.float32), mesh),
        )
        assert out.uvs is None


class TestGrownSurfaces:
    """Roof-ness follows the surface, not the angle (`P3-6` amendment)."""

    def rolled_sweep(self) -> MeshData:
        """A roof strip rolling from flat to vertical in 15-degree steps,
        every facet above the ribbon grid's first line so a misclassified
        facet would take bands."""
        angles = np.radians(np.arange(0, 105, 15, dtype=np.float64))
        spine = np.zeros((len(angles), 3))
        spine[:, 1] = 40.0
        for index in range(1, len(angles)):
            step = np.asarray([0.0, -np.sin(angles[index - 1]), np.cos(angles[index - 1])])
            spine[index] = spine[index - 1] + step * 3.0
        pieces = []
        for index in range(len(angles) - 1):
            a, b = spine[index], spine[index + 1]
            normal = np.asarray(
                [0.0, np.cos(angles[index]), np.sin(angles[index])], dtype=np.float32
            )
            pieces.append(
                MeshData(
                    name=f"facet{index}",
                    positions=np.asarray(
                        [
                            [0.0, a[1], a[2]],
                            [4.0, a[1], a[2]],
                            [4.0, b[1], b[2]],
                            [0.0, a[1], a[2]],
                            [4.0, b[1], b[2]],
                            [0.0, b[1], b[2]],
                        ],
                        dtype=np.float64,
                    ),
                    normals=np.asarray([normal] * 6, dtype=np.float32),
                    triangles=np.asarray([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
                )
            )
        return merge(pieces, name="sweep")

    def test_a_rolling_sweep_stays_roof_to_the_vertical(self) -> None:
        out = paint(self.rolled_sweep(), PAINT)
        colours = {tuple(int(v) for v in c) for c in np.unique(out.colours[:, :3], axis=0)}
        assert colours == {ROOF.colour}

    def test_a_crease_stops_the_roof(self) -> None:
        """A flat roof meeting a wall at a right angle: the wall keeps its
        bands, however close to the roof it stands."""
        roof = MeshData(
            name="flat",
            positions=np.asarray(
                [
                    [0.0, 26.5, 0.0],
                    [4.0, 26.5, 0.0],
                    [4.0, 26.5, 4.0],
                    [0.0, 26.5, 0.0],
                    [4.0, 26.5, 4.0],
                    [0.0, 26.5, 4.0],
                ],
                dtype=np.float64,
            ),
            normals=np.asarray([[0.0, 1.0, 0.0]] * 6, dtype=np.float32),
            triangles=np.asarray([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
        )
        # The wall's top edge is the roof's front edge — a shared, creased edge.
        wall = MeshData(
            name="drop",
            positions=np.asarray(
                [
                    [0.0, 26.5, 0.0],
                    [0.0, 24.7, 0.0],
                    [4.0, 24.7, 0.0],
                    [0.0, 26.5, 0.0],
                    [4.0, 24.7, 0.0],
                    [4.0, 26.5, 0.0],
                ],
                dtype=np.float64,
            ),
            normals=np.asarray([[0.0, 0.0, -1.0]] * 6, dtype=np.float32),
            triangles=np.asarray([[0, 1, 2], [3, 4, 5]], dtype=np.uint32),
        )
        out = paint(merge([roof, wall], name="corner"), PAINT)
        shown = {tuple(int(v) for v in c) for c in np.unique(out.colours[:, :3], axis=0)}
        # Both wall centroids (25.3 m, 25.9 m) sit inside ribbon level 2
        # (24.6-26.1 m): a leak across the crease would show as roof grey.
        assert shown == {ROOF.colour, RIBBON.colour}


class TestBuildAssets:
    """End-to-end on a synthetic sheet: the plumbing a unit test cannot see."""

    def landmark(self, hong_kong, *, budget: int = 120_000) -> Landmark:
        easting, northing, _ = _to_source(hong_kong, 50.0, 50.0)
        return Landmark(
            id="hero",
            asset="res://assets/generated/landmarks/hero.glb",
            easting=easting,
            northing=northing,
            elevation=0.0,
            rot_y_deg=0.0,
            name_en="Hero",
            name_zh="主角",
            replaces_source_ids=("hero",),
            triangle_budget=budget,
            source_paint=PAINT,
        )

    def build(self, hong_kong, sources, tmp_path, **kwargs):
        city = replace(hong_kong, landmarks=(self.landmark(hong_kong, **kwargs),))
        root = sources([Fixture("hero01", "BUILDING", 50.0, 50.0, height=40.0)])
        out_root = tmp_path / "out"
        return city, build_assets(city, "wan_chai", sources_root=root, out_root=out_root), out_root

    def test_the_model_ships_with_the_import_contract(self, hong_kong, sources, tmp_path) -> None:
        city, document, out_root = self.build(hong_kong, sources, tmp_path)

        assert document["schema_version"] == ASSETS_SCHEMA
        [asset] = document["assets"]
        assert asset["id"] == "hero"
        assert asset["path"] == "landmarks/hero.glb"
        assert asset["stems"] == ["hero"]

        path = city.out_dir("wan_chai", out_root) / "landmarks" / "hero.glb"
        [mesh] = read_glb(path)
        assert mesh.name == f"hero{COLLISION_SUFFIX}"
        # `read_glb` does not carry the material name back, so the contract
        # `generated_scene_import.gd` dispatches on is read from the file.
        assert material_names(path) == [LANDMARK_MATERIAL]
        assert mesh.colours is not None
        assert mesh.uvs is None and mesh.uv2 is None and mesh.texture is None
        assert mesh.triangle_count == asset["triangles"]

    def test_the_model_is_in_the_landmark_local_frame(self, hong_kong, sources, tmp_path) -> None:
        """Translated so `landmarks.json`'s position puts it back exactly —
        the fixture box stands at game (50, 50), the landmark is authored
        there, so locally it must be centred on the origin."""
        city, _, out_root = self.build(hong_kong, sources, tmp_path)
        [mesh] = read_glb(city.out_dir("wan_chai", out_root) / "landmarks" / "hero.glb")
        low, high = mesh.aabb()

        assert (low[0] + high[0]) / 2.0 == pytest.approx(0.0, abs=1e-6)
        assert (low[2] + high[2]) / 2.0 == pytest.approx(0.0, abs=1e-6)
        assert low[1] == pytest.approx(0.0, abs=1e-6)
        assert high[1] == pytest.approx(40.0, abs=1e-6)

    def test_the_walls_carry_crisp_ribbon_bands(self, hong_kong, sources, tmp_path) -> None:
        """The observable the slicing exists for: ribbon and wall colours both
        present, and no triangle straddles a band edge with one colour."""
        city, _, out_root = self.build(hong_kong, sources, tmp_path)
        [mesh] = read_glb(city.out_dir("wan_chai", out_root) / "landmarks" / "hero.glb")

        shown = {tuple(int(v) for v in colour) for colour in np.unique(mesh.colours, axis=0)}
        assert (*WALL.colour, 255) in shown
        assert (*RIBBON.colour, 255) in shown
        assert not spans(mesh, PAINT.ribbon_first_m)

    def test_a_budget_breach_refuses_the_build(self, hong_kong, sources, tmp_path) -> None:
        with pytest.raises(ValueError, match="triangle_budget"):
            self.build(hong_kong, sources, tmp_path, budget=3)

    def test_a_stem_matching_nothing_refuses_the_build(self, hong_kong, sources, tmp_path) -> None:
        city = replace(
            hong_kong,
            landmarks=(replace(self.landmark(hong_kong), replaces_source_ids=("nothing",)),),
        )
        root = sources([Fixture("hero01", "BUILDING", 50.0, 50.0, height=40.0)])
        with pytest.raises(ValueError, match="no source mesh matched"):
            build_assets(city, "wan_chai", sources_root=root, out_root=tmp_path / "out")

    def test_no_mesh_sourced_landmark_still_writes_the_document(
        self, hong_kong, sources, tmp_path
    ) -> None:
        """Written even when empty, so export's input read is unconditional —
        a missing file means the stage never ran."""
        city = replace(hong_kong, landmarks=())
        root = sources([Fixture("hero01", "BUILDING", 50.0, 50.0, height=40.0)])
        document = build_assets(city, "wan_chai", sources_root=root, out_root=tmp_path / "out")

        assert document["assets"] == []
        assert (city.out_dir("wan_chai", tmp_path / "out") / "landmark_assets.json").exists()
