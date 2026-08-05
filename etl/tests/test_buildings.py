"""Building stage tests: placement, colour, and one end-to-end run.

The end-to-end test builds a synthetic sheet zip rather than reading the real
280 MB of LandsD data, but it builds it in the *shape* the real data has —
Z-up local geometry under a column-major node matrix, one file per building,
inside `BUILDING/<id>/`. A fixture that got that shape wrong would pass while
the pipeline was broken.
"""

from __future__ import annotations

import json
import math
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest

from pipeline.buildings import (
    BUILDINGS_MANIFEST_NAME,
    COLLISION_TIER,
    SOURCE_ID,
    Grid,
    _tile_ground,
    assign,
    build_region,
    colour_for,
    facade_uv,
    game_offset,
)
from pipeline.config import BuildingStyle, SurfaceClass
from pipeline.gltf import MeshData, read_glb
from pipeline.mesh import collapse
from tests.helpers import BOX_FACES, box_corners, box_soup, covered, flat_mesh, soup, style

# --------------------------------------------------------------------------
# Fixture construction — a sheet zip shaped like the real ones
# --------------------------------------------------------------------------


def landsd_box(
    name: str,
    easting: float,
    northing: float,
    *,
    width: float,
    depth: float,
    height: float,
    textured: bool = False,
) -> tuple[bytes, bytes, bytes | None]:
    """One building in the exact shape LandsD ships: Z-up local, Y-up node.

    `textured` gives it UVs and a `baseColorTexture`, which is the shape the
    *terrain* class ships in — a 45-megapixel JPEG per sheet. Since `P3-10`
    tiles the ground alongside the massing, a fixture that only ever produced
    untextured geometry could not reach the path that strips it.
    """
    half_x, half_y = width / 2, depth / 2
    positions, normals = box_soup(box_corners((-half_x, -half_y, 0.0), (half_x, half_y, height)))

    position_bytes = np.array(positions, dtype="<f4").tobytes()
    normal_bytes = np.array(normals, dtype="<f4").tobytes()
    index_bytes = np.arange(36, dtype="<u2").tobytes()
    binary = position_bytes + normal_bytes + index_bytes

    attributes = {"POSITION": 0, "NORMAL": 1}
    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": 36, "type": "VEC3"},
        {"bufferView": 1, "componentType": 5126, "count": 36, "type": "VEC3"},
        {"bufferView": 2, "componentType": 5123, "count": 36, "type": "SCALAR"},
    ]
    views = [
        {"buffer": 0, "byteOffset": 0, "byteLength": len(position_bytes)},
        {"buffer": 0, "byteOffset": len(position_bytes), "byteLength": len(normal_bytes)},
        {
            "buffer": 0,
            "byteOffset": len(position_bytes) + len(normal_bytes),
            "byteLength": len(index_bytes),
        },
    ]
    primitive: dict[str, object] = {"attributes": attributes, "indices": 2, "mode": 4}
    document: dict[str, object] = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {
                "name": name,
                # Column-major, Z-up to Y-up, position in the last column.
                "matrix": [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, easting, 0.0, -northing, 1],
                "children": [1],
            },
            {"mesh": 0},
        ],
        "meshes": [{"primitives": [primitive]}],
        "accessors": accessors,
        "bufferViews": views,
    }

    image: bytes | None = None
    if textured:
        uv_bytes = np.tile(np.array([0.0, 0.0], dtype="<f4"), 36).tobytes()
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(uv_bytes)})
        accessors.append({"bufferView": 3, "componentType": 5126, "count": 36, "type": "VEC2"})
        binary += uv_bytes
        attributes["TEXCOORD_0"] = 3
        primitive["material"] = 0

        # Not a real JPEG. Nothing in the pipeline decodes it — `_ground` drops
        # it and `write_glb` would only re-embed the bytes — so a decodable
        # image would test the fixture rather than the stage.
        image = b"\xff\xd8\xff\xe0 not really a jpeg"
        document["images"] = [{"uri": f"{name}.jpg", "mimeType": "image/jpeg"}]
        document["textures"] = [{"source": 0}]
        document["materials"] = [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}]

    document["buffers"] = [{"uri": f"{name}.bin", "byteLength": len(binary)}]
    return json.dumps(document).encode(), binary, image


class Fixture(NamedTuple):
    """One synthetic building, placed in game space rather than source metres.

    `footprint` defaults to something comfortably larger than the coarsest LOD
    cell; it only matters for objects small enough to vanish into one.
    """

    name: str
    class_id: str
    x: float
    z: float
    height: float
    footprint: float = 20.0
    # The terrain class ships textured; the massing classes do not.
    textured: bool = False


@pytest.fixture
def sources(tmp_path: Path, hong_kong):
    """A sources tree holding one synthetic sheet and an index that selects it."""
    root = tmp_path / "sources"
    directory = root / hong_kong.id / SOURCE_ID
    directory.mkdir(parents=True)

    region = hong_kong.region("wan_chai")
    (directory / "index.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "SHEETNO": "TEST-1",
                            "Format_glTF": "https://example.test/models/TEST-1.zip?key=secret",
                            "REVISIONDATE": "20260101",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [region.bounds.west, region.bounds.south],
                                    [region.bounds.east, region.bounds.south],
                                    [region.bounds.east, region.bounds.north],
                                    [region.bounds.west, region.bounds.north],
                                    [region.bounds.west, region.bounds.south],
                                ]
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def _write(buildings: list[Fixture]) -> Path:
        with zipfile.ZipFile(directory / "TEST-1.zip", "w") as archive:
            for spec in buildings:
                easting, northing, _ = _to_source(hong_kong, spec.x, spec.z)
                document, binary, image = landsd_box(
                    spec.name,
                    easting,
                    northing,
                    width=spec.footprint,
                    depth=spec.footprint,
                    height=spec.height,
                    textured=spec.textured,
                )
                member = f"{spec.class_id}/{spec.name}/{spec.name}"
                archive.writestr(f"{member}.gltf", document)
                archive.writestr(f"{member}.bin", binary)
                if image is not None:
                    archive.writestr(f"{member}.jpg", image)
        return root

    return _write


def _to_source(city, x: float, z: float) -> tuple[float, float, float]:
    """Game-space (x, z) back to source easting/northing, for placing fixtures."""
    return city.game_transform("wan_chai").to_source(x, 0.0, z)


# --------------------------------------------------------------------------
# Placement
# --------------------------------------------------------------------------


def test_game_offset_matches_the_shared_transform(hong_kong) -> None:
    """The sheets are already on Godot's axes, so moving them into the region
    frame is a translation — but it must be *the* translation `city.json`
    publishes, not an equivalent one derived separately."""
    transform = hong_kong.game_transform("wan_chai")
    assert game_offset(transform) == pytest.approx(transform.to_game(0.0, 0.0, 0.0))


def test_a_source_point_lands_where_the_transform_says(hong_kong) -> None:
    transform = hong_kong.game_transform("wan_chai")
    easting, northing = transform.origin_easting + 500.0, transform.origin_northing - 300.0
    source_space = np.array([easting, 12.5, -northing])

    assert source_space + game_offset(transform) == pytest.approx([500.0, 12.5, 300.0])


class TestGrid:
    def grid(self) -> Grid:
        return Grid(tile_size_m=150.0, max_x=1650.0, max_z=900.0)

    def test_it_covers_the_region_exactly(self) -> None:
        assert (self.grid().columns, self.grid().rows) == (11, 6)

    def test_a_point_on_the_far_edge_stays_in_the_last_tile(self) -> None:
        """1650 / 150 is 11, one past the last column. Off by one here puts the
        easternmost buildings in a tile that does not exist."""
        ix, iz = self.grid().index(1650.0, 900.0)
        assert (int(ix), int(iz)) == (10, 5)

    def test_the_north_west_corner_is_tile_zero(self) -> None:
        """Q7: the origin is the NW corner, so row 0 is the *northern* row."""
        ix, iz = self.grid().index(0.0, 0.0)
        assert (int(ix), int(iz)) == (0, 0)

    @pytest.mark.parametrize(
        ("x", "z", "inside"),
        [(0.0, 0.0, True), (1650.0, 900.0, True), (-0.1, 10.0, False), (10.0, 900.1, False)],
    )
    def test_containment(self, x: float, z: float, inside: bool) -> None:
        assert bool(self.grid().contains(x, z)) is inside


class TestAssign:
    def grid(self) -> Grid:
        return Grid(tile_size_m=150.0, max_x=1650.0, max_z=900.0)

    def mesh(self, low: tuple[float, float, float], high: tuple[float, float, float]) -> MeshData:
        corners = box_corners(low, high)
        positions, normals, triangles = [], [], []
        for (a, b, c, d), normal in BOX_FACES:
            base = len(positions)
            positions.extend(corners[index] for index in (a, b, c, d))
            normals.extend([normal] * 4)
            triangles.extend([[base, base + 1, base + 2], [base, base + 2, base + 3]])
        return MeshData(
            name="m",
            positions=np.array(positions),
            normals=np.array(normals, dtype=np.float32),
            triangles=np.array(triangles, dtype=np.uint32),
        )

    def test_a_building_goes_whole_into_one_tile(self) -> None:
        placed = list(assign(self.mesh((10, 0, 10), (40, 30, 40)), self.grid()))
        assert len(placed) == 1
        assert placed[0][0] == (0, 0)
        assert placed[0][1].triangle_count == 12

    def test_a_building_straddling_a_boundary_still_goes_whole(self) -> None:
        """Split at the boundary it would be an open shell, and half of it would
        pop as the streamer loads one tile and not its neighbour."""
        [(tile, piece)] = list(assign(self.mesh((140, 0, 10), (170, 30, 40)), self.grid()))
        assert tile == (1, 0)
        assert piece.triangle_count == 12
        assert piece.positions.min(axis=0)[0] < 150.0  # overhangs west into tile 0

    def test_a_mesh_outside_the_region_is_dropped(self) -> None:
        assert list(assign(self.mesh((-500, 0, 10), (-400, 30, 40)), self.grid())) == []

    def test_a_mesh_too_large_for_a_tile_is_partitioned(self) -> None:
        """A two-kilometre viaduct is one mesh in this source. Assigned whole it
        either vanishes — its centre outside the region — or gives one 150 m
        tile a two-kilometre bounding box."""
        pieces = list(assign(self.mesh((10, 0, 10), (900, 30, 40)), self.grid()))

        assert len(pieces) > 1
        assert {iz for (_, iz), _ in pieces} == {0}  # one row, several columns
        assert sum(piece.triangle_count for _, piece in pieces) == 12

    def test_partitioning_drops_only_what_is_outside(self) -> None:
        pieces = list(assign(self.mesh((-500, 0, 10), (400, 30, 40)), self.grid()))
        assert pieces
        for _, piece in pieces:
            assert piece.positions.min(axis=0)[0] >= -500.0
        kept = sum(piece.triangle_count for _, piece in pieces)
        assert 0 < kept < 12


# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------


class TestColour:
    def test_height_selects_the_band(self) -> None:
        low = colour_for(style(), "BUILDING", flat_mesh("a", 8.0))
        high = colour_for(style(), "BUILDING", flat_mesh("b", 80.0))
        assert tuple(low[0]) == (200, 180, 150, 255)
        assert tuple(high[0]) == (190, 200, 200, 255)

    def test_a_band_is_inclusive_of_its_own_limit(self) -> None:
        assert tuple(colour_for(style(), "BUILDING", flat_mesh("a", 12.0))[0])[:3] == (
            200,
            180,
            150,
        )

    def test_class_colour_overrides_the_band(self) -> None:
        """A flyover deck is concrete whatever height it happens to sit at."""
        deck = colour_for(style(), "INFRASTRUCTURE", flat_mesh("i", 80.0))
        assert tuple(deck[0]) == (100, 100, 100, 255)

    def test_every_vertex_gets_the_colour(self) -> None:
        colours = colour_for(style(), "BUILDING", flat_mesh("a", 8.0))
        assert colours.shape == (3, 4)
        assert colours.dtype == np.uint8

    def test_jitter_is_stable_across_runs(self) -> None:
        """Seeded from the building id via crc32, not `hash` — which is salted
        per process and would repaint the city on every run."""
        first = colour_for(style(0.1), "BUILDING", flat_mesh("B12345", 8.0))
        second = colour_for(style(0.1), "BUILDING", flat_mesh("B12345", 8.0))
        assert (first == second).all()


class TestFacadeUv:
    """`P3-7`'s vertex payload: what the window-band shader cannot derive."""

    def test_u_is_measured_from_the_mesh_s_own_base(self) -> None:
        """The whole reason this ships. A vertex knows its world Y, and Wan Chai's
        ground moves 40 m across the region — so world Y says nothing about which
        floor a wall vertex is on."""
        on_a_hill = flat_mesh("B1", 30.0).translated((0.0, 120.0, 0.0))

        uvs = facade_uv(style(), "BUILDING", on_a_hill)

        assert uvs[:, 0].min() == pytest.approx(0.0)
        assert uvs[:, 0].max() == pytest.approx(30.0)

    def test_u_is_metres_rather_than_a_fraction_of_the_building(self) -> None:
        """The correction to `ART_DESIGN.md`'s original `(0-1)`. Normalised, a
        shophouse and a tower get the same number of window rows, and the floor
        *count* is the density signature the effect exists to carry."""
        shophouse = facade_uv(style(), "BUILDING", flat_mesh("B1", 9.0))
        tower = facade_uv(style(), "BUILDING", flat_mesh("B2", 120.0))

        assert shophouse[:, 0].max() == pytest.approx(9.0)
        assert tower[:, 0].max() == pytest.approx(120.0)

    def test_the_marker_separates_the_three_kinds_of_surface(self) -> None:
        """A tile is one merged primitive, so nothing else tells a façade from a
        viaduct soffit from the pavement."""
        markers = {
            class_id: np.floor(facade_uv(style(), class_id, flat_mesh("m", 8.0))[:, 1])[0]
            for class_id in ("BUILDING", "INFRASTRUCTURE", "TERRAIN")
        }

        assert markers == {
            "BUILDING": float(SurfaceClass.FACADE),
            "INFRASTRUCTURE": float(SurfaceClass.STRUCTURE),
            "TERRAIN": float(SurfaceClass.GROUND),
        }

    def test_the_phase_shares_the_colour_jitter_s_seed(self) -> None:
        """One seed for both, so a rebuild cannot move a building's window rows
        while leaving its brightness alone."""
        first = facade_uv(style(), "BUILDING", flat_mesh("B12345", 8.0))
        second = facade_uv(style(), "BUILDING", flat_mesh("B12345", 8.0))

        assert (first == second).all()
        assert facade_uv(style(), "BUILDING", flat_mesh("B99999", 8.0))[0, 1] != first[0, 1]

    def test_a_high_phase_never_rounds_into_the_next_marker(self) -> None:
        """⚠️ The defect this was written against, and it was a real one. The raw
        seed reaches 1 - 2^-32; float32 spacing near 2.0 is ~2.4e-7, so
        `STRUCTURE + 0.9999999998` rounds up to *exactly* 3.0 — an unknown marker
        and a lost phase, silently, on whichever viaduct drew a high seed.

        Brute-forced over every phase at every marker rather than sampled: the
        failure was one value at one end of one class, which is exactly what a
        spot check walks past."""
        for marker in SurfaceClass:
            for phase in range(256):
                packed = np.float32(float(marker) + phase / 256)
                assert math.floor(packed) == marker
                assert packed - math.floor(packed) == pytest.approx(phase / 256)

    def test_a_split_mesh_keeps_one_base(self) -> None:
        """Computed before `assign` cuts a two-kilometre viaduct into tiles, for
        the same reason the colour is: four pieces measuring from four different
        lowest corners would band at four different heights."""
        # Two faces 300 m apart, each spanning the full 40 m height, so the mesh
        # is far too wide for one tile and `assign` partitions it by triangle.
        viaduct = soup(
            [
                [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 40.0, 0.0)],
                [(300.0, 0.0, 0.0), (310.0, 0.0, 0.0), (300.0, 40.0, 0.0)],
            ],
            name="v1",
        )
        whole = replace(viaduct, uvs=facade_uv(style(), "INFRASTRUCTURE", viaduct))

        pieces = [
            piece for _, piece in assign(whole, Grid(tile_size_m=150.0, max_x=400.0, max_z=400.0))
        ]

        assert len(pieces) > 1
        for piece in pieces:
            assert piece.uvs[:, 0].min() == pytest.approx(0.0)
            assert piece.uvs[:, 0].max() == pytest.approx(40.0)

    def test_jitter_distinguishes_neighbours(self) -> None:
        """Without it a height band renders as one flat mass and the block reads
        as a single object."""
        a = colour_for(style(0.1), "BUILDING", flat_mesh("B00001", 8.0))
        b = colour_for(style(0.1), "BUILDING", flat_mesh("B00002", 8.0))
        assert not (a == b).all()

    def test_jitter_stays_within_its_bound(self) -> None:
        for index in range(200):
            colour = colour_for(style(0.06), "BUILDING", flat_mesh(f"B{index:05d}", 8.0))
            assert abs(int(colour[0][0]) - 200) <= round(200 * 0.06) + 1
            assert colour[0][3] == 255


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------


class TestBuildRegion:
    def buildings(self) -> list[Fixture]:
        return [
            Fixture("B0001", "BUILDING", 75.0, 75.0, 10.0),  # tile 0,0 — low band
            Fixture("B0002", "BUILDING", 90.0, 90.0, 90.0),  # tile 0,0 — tall band
            Fixture("B0003", "BUILDING", 400.0, 300.0, 40.0),  # tile 2,2
            Fixture("I0001", "INFRASTRUCTURE", 410.0, 310.0, 8.0),  # tile 2,2
            Fixture("B0009", "BUILDING", -900.0, 300.0, 40.0),  # outside the region
        ]

    def build(
        self,
        hong_kong,
        sources,
        tmp_path: Path,
        fixtures: list[Fixture] | None = None,
        out: str = "out",
    ):
        """One end-to-end run. `fixtures` overrides the default set, `hong_kong`
        takes any city so a test can vary the config, and `out` separates two
        runs in one test — without it the second silently overwrites the first's
        GLBs under the same tmp_path."""
        return build_region(
            hong_kong,
            "wan_chai",
            sources_root=sources(self.buildings() if fixtures is None else fixtures),
            out_root=tmp_path / out,
        )

    def tile(self, report, tile_id: str):
        """One tile of a report, by id."""
        return {output.id: output for output in report.tiles}[tile_id]

    def test_it_writes_a_tile_per_occupied_cell(self, hong_kong, sources, tmp_path) -> None:
        report = self.build(hong_kong, sources, tmp_path)
        assert [tile.id for tile in report.tiles] == ["t_00_00", "t_02_02"]
        assert report.read == 5
        assert report.clipped == 1

    def test_every_lod_tier_is_written(self, hong_kong, sources, tmp_path) -> None:
        report = self.build(hong_kong, sources, tmp_path)
        out = tmp_path / "out" / "hong_kong" / "wan_chai"
        for tile in report.tiles:
            assert [Path(lod.path).name for lod in tile.lods] == [
                f"{tile.id}_lod{level}.glb"
                for level in range(len(hong_kong.buildings.lod_cell_sizes_m))
            ]
            for lod in tile.lods:
                assert (out / lod.path).exists()

    def test_only_the_finest_tier_is_named_for_collision(
        self, hong_kong, sources, tmp_path
    ) -> None:
        """The `-col` suffix is what Godot's importer turns into a static
        trimesh, so the name *is* the collision contract.

        Asserted here as well as in `game/tools/verify_tiles.gd` because the two
        run in different places: `Q17` records that CI runs `tools/check.sh`
        without the generated-asset verifiers, so on a pull request this test is
        the only thing standing between a rename and a city the car drives
        through. Both directions, because a suffix that spread to every tier
        would still pass a present-on-tier-0 check while paying for a collider
        in the bundle for geometry 300 m away.
        """
        self.build(hong_kong, sources, tmp_path)
        tiles = tmp_path / "out" / "hong_kong" / "wan_chai" / "tiles"
        levels = range(len(hong_kong.buildings.lod_cell_sizes_m))

        for level in levels:
            meshes = read_glb(tiles / f"t_00_00_lod{level}.glb")
            expected = "t_00_00-col" if level == COLLISION_TIER else "t_00_00"
            assert [mesh.name for mesh in meshes] == [expected]

    def test_a_tile_is_one_mesh_and_so_one_draw_call(self, hong_kong, sources, tmp_path) -> None:
        """`P1-2` accepts under three draw calls per tile. Merging every
        building into one primitive is how the untextured dataset pays off."""
        self.build(hong_kong, sources, tmp_path)
        path = tmp_path / "out" / "hong_kong" / "wan_chai" / "tiles" / "t_00_00_lod0.glb"
        assert len(read_glb(path)) == 1

    def test_tiles_carry_vertex_colours_and_no_texture(self, hong_kong, sources, tmp_path) -> None:
        self.build(hong_kong, sources, tmp_path)
        [tile] = read_glb(
            tmp_path / "out" / "hong_kong" / "wan_chai" / "tiles" / "t_00_00_lod0.glb"
        )
        assert tile.colours is not None
        assert tile.texture is None

    def test_both_height_bands_survive_the_merge(self, hong_kong, sources, tmp_path) -> None:
        """Two boxes in one tile, 10 m and 90 m, so two different bands. Merging
        into one primitive is what makes the tile one draw call — and the thing
        it must not cost is per-building colour."""
        self.build(hong_kong, sources, tmp_path)
        [tile] = read_glb(
            tmp_path / "out" / "hong_kong" / "wan_chai" / "tiles" / "t_00_00_lod0.glb"
        )
        assert len(set(map(tuple, tile.colours))) == 2

    def test_geometry_lands_in_the_region(self, hong_kong, sources, tmp_path) -> None:
        report = self.build(hong_kong, sources, tmp_path)
        (low, high) = report.tiles[0].aabb
        # B0001 is a 20 m box centred on game (75, 75).
        assert low[0] == pytest.approx(65.0, abs=1.0)
        assert high[2] == pytest.approx(100.0, abs=1.0)

    def test_coarser_tiers_hold_less_geometry(self, hong_kong, sources, tmp_path) -> None:
        report = self.build(hong_kong, sources, tmp_path)
        for tile in report.tiles:
            counts = [lod.triangles for lod in tile.lods]
            assert counts == sorted(counts, reverse=True)

    def test_a_tile_of_only_tiny_objects_does_not_kill_the_run(
        self, hong_kong, sources, tmp_path
    ) -> None:
        """A 1.5 m cube alone in a tile vanishes at 4 m cells. Correct for a sign
        gantry seen from 400 m; taking the whole region's build down with it,
        after 100 GLBs are already on disk, is not.

        Placed to sit *wholly inside* one 4 m cell, because that is the condition
        — a sub-cell object straddling a boundary keeps two clusters per axis and
        survives. Which makes this a latent failure that depends on absolute
        position, and so can appear the next time the region bounds move.
        """
        gantry = Fixture("B0100", "BUILDING", 1402.0, 802.0, height=1.5, footprint=1.5)
        report = self.build(hong_kong, sources, tmp_path, [*self.buildings(), gantry])

        tiers = len(hong_kong.buildings.lod_cell_sizes_m)
        assert len(self.tile(report, "t_09_05").lods) < tiers
        assert len(self.tile(report, "t_00_00").lods) == tiers

    def thin_deck(self) -> list[Fixture]:
        """A building next to an elevated deck, in one tile.

        The deck is 0.8 m thick and 30 m across — thinner than the 1.5 m cell
        that decimates a building, and that is the whole failure `P2-1` saw on
        screen: cluster a deck at a cell thicker than itself and its top surface
        merges into its bottom one, leaving a flat sliver where a flyover was.
        """
        return [
            Fixture("B0100", "BUILDING", 75.0, 75.0, 60.0),
            Fixture("I0100", "INFRASTRUCTURE", 100.0, 100.0, 0.8, footprint=30.0),
        ]

    def test_the_override_keeps_a_thin_structure_the_building_cell_would_flatten(
        self, hong_kong, sources, tmp_path
    ) -> None:
        """The deck is thinner than the cell that decimates a building, so
        without a per-class cell its top surface clusters into its bottom one
        and it collapses to a flat sliver.

        Asserted as a comparison between two builds of the same geometry rather
        than between two tiers of one build, and **across all tiers rather than
        at one index**: which tier shows the difference depends on the table,
        since a tier whose building cell already matches its override loses
        nothing either way. The claim is that the override never costs geometry
        and somewhere gains it, and that holds whatever the table says.
        """
        kept = self.build(hong_kong, sources, tmp_path, self.thin_deck(), out="kept")
        lost = self.build(
            replace(hong_kong, buildings=replace(hong_kong.buildings, class_lod_cell_sizes_m={})),
            sources,
            tmp_path,
            self.thin_deck(),
            out="lost",
        )

        with_override = [lod.triangles for lod in self.tile(kept, "t_00_00").lods]
        without = [lod.triangles for lod in self.tile(lost, "t_00_00").lods]
        assert all(a >= b for a, b in zip(with_override, without, strict=True))
        assert any(a > b for a, b in zip(with_override, without, strict=True))

    def ground(self) -> list[Fixture]:
        """A building and a patch of the textured ground beneath it, in one tile.

        Flat, wide and textured, which is the shape the LandsD terrain ships in
        and the shape `P3-10` has to get through a pipeline specified to emit no
        textures at all.
        """
        return [
            Fixture("B0100", "BUILDING", 75.0, 75.0, 60.0),
            Fixture(
                "G0100",
                "TERRAIN(TB)",
                75.0,
                75.0,
                height=0.5,
                footprint=100.0,
                textured=True,
            ),
        ]

    def test_the_textured_ground_ships_untextured(self, hong_kong, sources, tmp_path) -> None:
        """The invariant `P1-2` kept the terrain out of `classes` to protect, now
        that `P3-10` has put it in.

        Not a formality: `merge` refuses a textured mesh outright, so a
        regression here fails the build rather than shipping a JPEG — which is
        why this asserts the *tile* is clean rather than asserting `_ground` was
        called.

        ⚠️ **The absent texture is what is asserted, not absent UVs.** This read
        `uvs is None` until `P3-7`, where the two stopped being the same
        question: a tile now ships `TEXCOORD_0` deliberately, as a shader payload
        with no image behind it. Keeping the old assertion would have made the
        source orthophoto's own UVs indistinguishable from ours — which is the
        regression this test exists to catch."""
        report = self.build(hong_kong, sources, tmp_path, self.ground())

        out = tmp_path / "out" / "hong_kong" / "wan_chai"
        for lod in self.tile(report, "t_00_00").lods:
            meshes = read_glb(out / lod.path)
            assert len(meshes) == 1
            assert meshes[0].texture is None
            assert meshes[0].colours is not None
            # The source's UVs index an orthophoto and run 0-1 across a sheet.
            # Ours are metres above a base and a surface marker, so the ground's
            # `v` is exactly `GROUND` — a value the source could not produce.
            assert meshes[0].uvs is not None
            markers = set(np.unique(np.floor(meshes[0].uvs[:, 1])).tolist())
            assert float(SurfaceClass.GROUND) in markers
            assert markers <= {float(member) for member in SurfaceClass}

    def test_a_tile_holding_only_ground_is_still_written(
        self, hong_kong, sources, tmp_path
    ) -> None:
        """The ground no longer travels in `buckets`, so the write loop iterates
        the union of two dicts. Taking `buckets` alone would drop exactly this
        square — and the region has one: it gained its 66th tile when `P3-10`
        put ground in corners no building reaches."""
        report = self.build(
            hong_kong,
            sources,
            tmp_path,
            [
                Fixture("B0300", "BUILDING", 75.0, 75.0, 40.0),
                Fixture("G0300", "TERRAIN(TB)", 400.0, 300.0, 0.5, footprint=60.0, textured=True),
            ],
        )
        assert [tile.id for tile in report.tiles] == ["t_00_00", "t_02_02"]

    def test_ground_meshes_are_still_counted_as_read(self, hong_kong, sources, tmp_path) -> None:
        """`read` and `clipped` are the wrong-bounds diagnostic — a `read` of
        zero, or a `clipped` equal to it, is the failure they exist for. Routing
        the ground past the buckets must not route it past the tally."""
        report = self.build(hong_kong, sources, tmp_path, self.ground())
        assert report.read == len(self.ground())

    def test_the_ground_is_sunk_and_the_buildings_are_not(
        self, hong_kong, sources, tmp_path
    ) -> None:
        """`roads.py` lays the level-0 carriageway at `terrain + 0.0`, so ground
        drawn where it was sampled is coplanar with the road by construction.

        Measured as a difference between two builds of the same fixtures rather
        than against an absolute height: the fixture's own elevation, the game
        transform and the LOD cell all move the number, and none of them is what
        this is about. Only the ground moves, and it moves by the sink.
        """
        sunk = self.build(hong_kong, sources, tmp_path, self.ground(), out="sunk")
        flat = self.build(
            replace(hong_kong, buildings=replace(hong_kong.buildings, ground_sink_m=0.0)),
            sources,
            tmp_path,
            self.ground(),
            out="flat",
        )

        sink = hong_kong.buildings.ground_sink_m
        assert sink > 0.0
        # The ground is the lowest thing in the tile and the building the
        # tallest, so the box's floor tracks the ground and its ceiling the
        # building — which is what makes "only the ground moved" visible in an
        # AABB without reading the meshes apart.
        (low_sunk, high_sunk), (low_flat, high_flat) = (
            self.tile(report, "t_00_00").aabb for report in (sunk, flat)
        )
        assert low_sunk[1] == pytest.approx(low_flat[1] - sink)
        assert high_sunk[1] == pytest.approx(high_flat[1])

    def test_the_ground_takes_no_jitter(self, hong_kong, sources, tmp_path) -> None:
        """Jitter is seeded per source mesh, and the ground arrives as a handful
        of sheet-sized meshes rather than one per object — so the setting that
        stops a height band reading as a single mass would instead paint the
        region in as many shades as there are sheets, seams included.

        ⚠️ Asserted as **one shade across every ground vertex**, not as "the base
        colour appears somewhere". The jitter factor is a crc32 seed scaled into
        `[1 - j, 1 + j]`, so for some mesh names it rounds back to the base
        colour anyway — a test looking for the base colour can pass against the
        bug. Two ground meshes wearing two shades is the property that fails.
        """
        two_sheets = [
            Fixture("G0100", "TERRAIN(TB)", 40.0, 40.0, height=0.5, footprint=60.0, textured=True),
            Fixture(
                "G0101", "TERRAIN(TB)", 110.0, 110.0, height=0.5, footprint=60.0, textured=True
            ),
        ]

        def shades(city) -> int:
            report = self.build(city, sources, tmp_path, two_sheets, out=str(id(city)))
            path = tmp_path / str(id(city)) / "hong_kong" / "wan_chai"
            colours = read_glb(path / self.tile(report, "t_00_00").lods[0].path)[0].colours
            return len(np.unique(colours[:, :3], axis=0))

        jittered = replace(
            hong_kong, buildings=replace(hong_kong.buildings, class_colour_jitter={})
        )
        assert shades(hong_kong) == 1
        assert shades(jittered) == 2

    def test_a_mixed_class_tile_is_one_mesh_at_every_tier(
        self, hong_kong, sources, tmp_path
    ) -> None:
        """Collapsing per class and merging afterwards must not cost the tile its
        single primitive — `game/tools/verify_tiles.gd` enforces the same thing
        from the engine side."""
        report = self.build(hong_kong, sources, tmp_path, self.thin_deck())

        out = tmp_path / "out" / "hong_kong" / "wan_chai"
        for lod in self.tile(report, "t_00_00").lods:
            assert len(read_glb(out / lod.path)) == 1

    def test_the_manifest_describes_the_grid(self, hong_kong, sources, tmp_path) -> None:
        self.build(hong_kong, sources, tmp_path)
        manifest = json.loads(
            (tmp_path / "out" / "hong_kong" / "wan_chai" / BUILDINGS_MANIFEST_NAME).read_text()
        )
        assert manifest["grid"] == {"columns": 11, "rows": 6}
        assert manifest["tile_size_m"] == 150.0
        assert [tile["id"] for tile in manifest["tiles"]] == ["t_00_00", "t_02_02"]

    def test_a_rerun_is_byte_identical(self, hong_kong, sources, tmp_path) -> None:
        """Merge order decides vertex order, so an unstable sheet listing would
        make every tile look changed on every run."""
        root = sources(self.buildings())
        first = tmp_path / "a"
        second = tmp_path / "b"
        build_region(hong_kong, "wan_chai", sources_root=root, out_root=first)
        build_region(hong_kong, "wan_chai", sources_root=root, out_root=second)

        for path in sorted((first / "hong_kong" / "wan_chai" / "tiles").glob("*.glb")):
            twin = second / "hong_kong" / "wan_chai" / "tiles" / path.name
            assert path.read_bytes() == twin.read_bytes()

    def test_a_region_with_nothing_in_it_is_an_error(self, hong_kong, sources, tmp_path) -> None:
        """Exiting 0 with no buildings is the failure this pipeline is most
        exposed to — wrong bounds and a wrong datum both land here."""
        root = sources([Fixture("B0009", "BUILDING", -900.0, 300.0, 40.0)])
        with pytest.raises(ValueError, match="no tiles"):
            build_region(hong_kong, "wan_chai", sources_root=root, out_root=tmp_path / "out")

    def test_a_missing_index_says_how_to_fix_it(self, hong_kong, tmp_path) -> None:
        with pytest.raises(FileNotFoundError, match=r"pipeline\.fetch"):
            build_region(
                hong_kong,
                "wan_chai",
                sources_root=tmp_path / "empty",
                out_root=tmp_path / "out",
            )


class TestTileGround:
    """`Q25`: the ground is decimated once and cut afterwards.

    `collapse` bins world-anchored but ships `_cluster_mean` over *the members
    present in that mesh*. Cut the ground into tiles first and a cluster
    straddling a boundary averages over a different subset either side, lands on
    two different positions, and the sheet pulls apart — a crack straight to the
    sky, since a height field has no inside. Measured on the region: **15.65%**
    of probes within 2 m of a tile boundary had no ground over them against
    0.61% beyond 10 m. After this: 0.42% against 0.54%, which is to say the
    boundary stopped being special.

    Tested here rather than through `build_region` because the synthetic sheet
    zip builds boxes, and a box is far coarser than the 4 m cluster cell — the
    tear needs source vertices *finer* than the cell, which is what real terrain
    has and `landsd_box` cannot express.
    """

    GRID = Grid(tile_size_m=150.0, max_x=1650.0, max_z=900.0)

    def _style(self, cells: tuple[float, ...]) -> BuildingStyle:
        """`style()` at one cell size per tier.

        `style()` already names `TERRAIN` as its `terrain_class`, and
        `_tile_ground` reads only that and the cell table — never `classes`.
        """
        return replace(style(), lod_cell_sizes_m=cells)

    def _sheet(self, step: float) -> MeshData:
        """A ramp spanning x=60-240, so `assign` must cut it at x=150.

        `step` is the source vertex spacing. Below the 4 m cluster cell it puts
        two rows of vertices in the cell that straddles the boundary, which is
        what makes the two sides' subsets differ — and is the condition real
        terrain meets everywhere.
        """
        xs, zs = np.arange(60.0, 241.0, step), np.arange(40.0, 111.0, step)
        height = lambda x: 2.0 + 0.35 * (x - 60.0)  # noqa: E731
        corners: list[list[tuple[float, float, float]]] = []
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                a = (xs[i], height(xs[i]), zs[j])
                b = (xs[i + 1], height(xs[i + 1]), zs[j])
                c = (xs[i + 1], height(xs[i + 1]), zs[j + 1])
                d = (xs[i], height(xs[i]), zs[j + 1])
                corners.append([a, b, d])
                corners.append([b, c, d])
        # Flat +Y normals: `height_field=True` replaces the facing term with a
        # zero column, so what the normals say cannot reach the clustering under
        # test — see `mesh.collapse`.
        return soup(corners, name="ground", colour=(176, 169, 154, 255))

    def _holes(self, pieces: list[MeshData]) -> int:
        """Plan positions across the x=150 boundary with no surface over them."""
        return int(
            (~covered(pieces, np.arange(142.0, 159.0, 0.25), np.arange(50.0, 101.0, 0.5))).sum()
        )

    def test_the_seam_a_tile_boundary_used_to_open_is_closed(self) -> None:
        """The defect and the fix in one comparison, against the order this
        replaced. 714 holes to none on this fixture; 8.12% to 0.00% on the band
        of the region the driver photographed."""
        sheet = self._sheet(step=1.5)
        cells = self._style((4.0,))

        torn = [
            collapse(piece, cell_m=4.0, height_field=True) for _, piece in assign(sheet, self.GRID)
        ]
        whole = [tiers[0] for tiers in _tile_ground([sheet], self.GRID, cells).values()]

        assert self._holes(torn) > 0
        assert self._holes(whole) == 0

    def test_every_tier_reaches_every_tile_the_ground_covers(self) -> None:
        sheet = self._sheet(step=1.5)
        cells = self._style((4.0, 8.0))

        tiers = _tile_ground([sheet], self.GRID, cells)
        assert len(tiers) == 2  # x=60-240 straddles the boundary at 150
        for tile in tiers.values():
            assert sorted(tile) == [0, 1]

    def test_a_region_with_no_ground_produces_no_tiers(self) -> None:
        """A city that does not tile its ground reaches this with nothing, and
        `merge` refuses an empty list rather than returning an empty mesh."""
        assert _tile_ground([], self.GRID, self._style((4.0,))) == {}
