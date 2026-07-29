"""Merge, select and LOD-collapse tests.

The LOD tiers are the part of `P1-2` carrying real risk: the six Wan Chai sheets
are ~1M triangles against a <300k visible budget, so `collapse` is load-bearing
rather than cosmetic. These check both that it removes enough and that it does
not remove the things the art direction depends on.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.gltf import MeshData
from pipeline.mesh import collapse, merge, select_triangles


def box(origin: tuple[float, float, float] = (0, 0, 0), size: float = 10.0) -> MeshData:
    """An axis-aligned box, unwelded and flat-shaded, as LandsD ships them.

    36 vertices for 12 triangles: every vertex is repeated per face so each
    carries its own face normal. That repetition is what LOD0's exact weld is
    there to remove.
    """
    low = np.asarray(origin, dtype=np.float64)
    high = low + size
    corners = np.array(
        [[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    )
    quads = [
        ((0, 1, 3, 2), (-1, 0, 0)),
        ((4, 6, 7, 5), (1, 0, 0)),
        ((0, 4, 5, 1), (0, -1, 0)),
        ((2, 3, 7, 6), (0, 1, 0)),
        ((0, 2, 6, 4), (0, 0, -1)),
        ((1, 5, 7, 3), (0, 0, 1)),
    ]

    positions, normals = [], []
    for (a, b, c, d), normal in quads:
        for index in (a, b, c, a, c, d):
            positions.append(corners[index])
            normals.append(normal)

    return MeshData(
        name="box",
        positions=np.array(positions, dtype=np.float64),
        normals=np.array(normals, dtype=np.float32),
        triangles=np.arange(36, dtype=np.uint32).reshape(-1, 3),
        colours=np.tile(np.array([200, 190, 180, 255], np.uint8), (36, 1)),
    )


class TestMerge:
    def test_triangles_are_renumbered_into_the_merged_buffer(self) -> None:
        """The one way merging can go wrong silently: leave the second mesh's
        indices pointing at the first mesh's vertices and the tile fills with
        triangles stretched between unrelated buildings."""
        merged = merge([box(), box(origin=(100, 0, 0))], name="tile")

        assert len(merged.positions) == 72
        assert merged.triangle_count == 24
        assert merged.triangles.max() == 71
        # Every triangle of the second box must reference its own vertices.
        second = merged.positions[merged.triangles[12:]]
        assert second[..., 0].min() >= 100.0

    def test_merging_coloured_with_uncoloured_is_rejected(self) -> None:
        """One primitive has one attribute set. Half a tile without colours
        would render at whatever the missing attribute defaults to."""
        plain = box()
        with pytest.raises(ValueError, match="coloured and uncoloured"):
            merge([box(), MeshData("p", plain.positions, plain.normals, plain.triangles)], name="t")

    def test_merging_nothing_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="zero meshes"):
            merge([], name="tile")


class TestCollapseExact:
    def test_lod0_welds_without_losing_a_triangle(self) -> None:
        """An exact weld is lossless by construction, and worth doing: the
        source repeats every vertex per triangle."""
        welded = collapse(box(), cell_m=0.0)

        assert welded.triangle_count == 12
        assert len(welded.positions) == 24  # 4 per face, not 8 — normals differ
        assert welded.positions.min() == 0.0
        assert welded.positions.max() == 10.0

    def test_the_weld_keeps_hard_normals(self) -> None:
        """Welding on position alone would average a wall normal with the roof
        normal above it and round off the faceting the whole style rests on."""
        welded = collapse(box(), cell_m=0.0)
        for normal in welded.normals:
            assert sorted(abs(component) for component in normal) == pytest.approx([0.0, 0.0, 1.0])


class TestCollapseDecimation:
    def test_a_building_sized_box_keeps_its_silhouette(self) -> None:
        """The property that makes clustering the right decimator here: an
        extruded volume larger than the cell keeps every face, so a tower stays
        a tower rather than becoming a wedge."""
        tower = collapse(box(size=20.0), cell_m=4.0)
        assert tower.triangle_count == 12
        assert tower.positions.min() == 0.0
        assert tower.positions.max() == 20.0

    def test_anything_smaller_than_a_cell_disappears(self) -> None:
        """Every face of a sub-cell box folds onto a single vertex. Intended at
        LOD2 — a 1 m object 400 m away is not worth a draw — but it is why
        `collapse` raises when a whole *tile* vanishes rather than shipping a
        hole in the city."""
        with pytest.raises(ValueError, match="no triangles"):
            collapse(box(size=1.0), cell_m=4.0)

    def test_it_cuts_a_real_tile_hard(self) -> None:
        """The budget question, in miniature: many small boxes in one tile."""
        cluster = merge(
            [box(origin=(x * 3.0, 0, z * 3.0), size=2.0) for x in range(6) for z in range(6)],
            name="tile",
        )
        assert collapse(cluster, cell_m=4.0).triangle_count < cluster.triangle_count / 3

    def test_coarser_cells_never_produce_more_geometry(self) -> None:
        cluster = merge([box(origin=(x * 4.0, 0, 0)) for x in range(8)], name="tile")
        counts = [collapse(cluster, cell_m=cell).triangle_count for cell in (0.0, 1.5, 4.0, 8.0)]
        assert counts == sorted(counts, reverse=True)

    def test_it_stays_inside_the_original_bounds(self) -> None:
        """Cluster representatives are means of their members, so decimation
        can shrink a silhouette but must never inflate one — a building growing
        into the road is a collision bug, not an art one."""
        original = box()
        decimated = collapse(original, cell_m=4.0)
        assert decimated.positions.min() >= original.positions.min() - 1e-9
        assert decimated.positions.max() <= original.positions.max() + 1e-9

    def test_colour_survives_decimation(self) -> None:
        decimated = collapse(box(), cell_m=4.0)
        assert decimated.colours is not None
        assert set(map(tuple, decimated.colours)) == {(200, 190, 180, 255)}


class TestSelectTriangles:
    def test_a_partition_loses_no_triangles_and_shares_no_vertex(self) -> None:
        """This is what lets an oversized mesh be split across tiles without a
        seam: triangles are moved, never cut."""
        source = merge([box(), box(origin=(100, 0, 0))], name="pair")
        left = source.positions[source.triangles].mean(axis=1)[:, 0] < 50.0

        west = select_triangles(source, left)
        east = select_triangles(source, ~left)
        assert west.triangle_count + east.triangle_count == source.triangle_count
        assert west.positions.max(axis=0)[0] < east.positions.min(axis=0)[0]

    def test_unused_vertices_are_dropped(self) -> None:
        source = merge([box(), box(origin=(100, 0, 0))], name="pair")
        left = source.positions[source.triangles].mean(axis=1)[:, 0] < 50.0
        assert len(select_triangles(source, left).positions) == 36

    def test_selecting_nothing_returns_nothing(self) -> None:
        assert select_triangles(box(), np.zeros(12, dtype=bool)) is None
