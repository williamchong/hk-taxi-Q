"""Merge, select and LOD-collapse tests.

The LOD tiers are the part of `P1-2` carrying real risk: the six Wan Chai sheets
are ~1M triangles against a <300k visible budget, so `collapse` is load-bearing
rather than cosmetic. These check both that it removes enough and that it does
not remove the things the art direction depends on.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from pipeline.gltf import MeshData, Texture, normalise, triangle_cross
from pipeline.mesh import collapse, merge, select_triangles, slice_horizontal, slice_plane
from tests.helpers import area, box, covered, soup


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

    def test_textured_meshes_are_rejected(self) -> None:
        """Two textures cannot share one primitive without a UV atlas. Keeping
        one and dropping the other would render the second mesh in a single
        wrong colour with no error — the terrain trap waiting for P1-2t."""
        plain = box()
        textured = MeshData(
            "ground",
            plain.positions,
            plain.normals,
            plain.triangles,
            uvs=np.zeros((36, 2), dtype=np.float32),
            texture=Texture(data=b"jpeg", mime_type="image/jpeg"),
        )
        with pytest.raises(ValueError, match="UV atlas"):
            merge([textured], name="tile")

    def test_uvs_without_a_texture_are_merged(self) -> None:
        """`P3-7`'s payload is a shader coordinate with no image behind it, so
        the atlas objection does not reach it — and merging is not optional:
        every tile goes through here twice, per class and then per tier."""
        first, second = box(), box(origin=(100, 0, 0))
        merged = merge(
            [
                replace(first, uvs=np.zeros((len(first.positions), 2), dtype=np.float32)),
                replace(second, uvs=np.ones((len(second.positions), 2), dtype=np.float32)),
            ],
            name="tile",
        )

        assert merged.uvs is not None
        assert len(merged.uvs) == len(merged.positions)
        # Concatenated in order, like every other attribute — a UV that stayed
        # with the wrong vertex is the failure a length check cannot see.
        assert (merged.uvs[: len(first.positions)] == 0.0).all()
        assert (merged.uvs[len(first.positions) :] == 1.0).all()

    def test_merging_mapped_with_unmapped_is_rejected(self) -> None:
        """The same rule colours have, for the same reason: one primitive has one
        attribute set, and the half without would render at whatever the missing
        attribute defaults to — for `P3-7` that is height zero, so a whole class
        would band as though it were at ground level."""
        plain = box()
        with pytest.raises(ValueError, match="with and without UVs"):
            merge(
                [plain, replace(plain, uvs=np.zeros((len(plain.positions), 2), dtype=np.float32))],
                name="tile",
            )

    def test_uv2_merges_and_a_half_carrying_half_is_rejected(self) -> None:
        """A UV2 payload obeys the same all-or-none rule as colours and UVs: a
        primitive half without the channel decodes the missing half as code 0,
        and every codec that ships one gives 0 a meaning — so nothing
        downstream could tell the defect from that meaning. Only this guard
        can. `roads.glb` and `tram.glb` are the layers this protects today."""
        first, second = box(), box(origin=(100, 0, 0))
        merged = merge(
            [
                replace(first, uv2=np.zeros((len(first.positions), 2), dtype=np.float32)),
                replace(
                    second,
                    uv2=np.tile(
                        np.array([6082.0, 0.0], dtype=np.float32), (len(second.positions), 1)
                    ),
                ),
            ],
            name="tile",
        )
        assert merged.uv2 is not None
        assert (merged.uv2[: len(first.positions), 0] == 0.0).all()
        assert (merged.uv2[len(first.positions) :, 0] == 6082.0).all()

        with pytest.raises(ValueError, match="with and without UV2"):
            merge(
                [
                    box(),
                    replace(box(), uv2=np.zeros((len(box().positions), 2), dtype=np.float32)),
                ],
                name="tile",
            )

    def test_material_is_not_inherited_from_an_input(self) -> None:
        """A merged primitive has exactly one material, so taking whichever mesh
        came first would be a coin toss with no error. The caller names the
        result — `buildings._write_tile` does."""
        merged = merge([replace(box(), material="city_facade"), box()], name="tile")

        assert merged.material is None

    def test_indices_do_not_widen_to_int64(self) -> None:
        """A Python-list cumsum offsets in int64, which would silently promote
        every merged tile's index array and double the index buffer."""
        assert merge([box(), box(origin=(50, 0, 0))], name="tile").triangles.dtype == np.uint32


class TestCollapseExact:
    def test_lod0_welds_without_losing_a_triangle(self) -> None:
        """An exact weld is lossless by construction, and worth doing: the
        source repeats every vertex per triangle."""
        welded = collapse(box(), cell_m=0.0)

        assert welded.triangle_count == 12
        assert len(welded.positions) == 24  # 4 per face, not 8 — normals differ
        assert welded.positions.min() == 0.0
        assert welded.positions.max() == 10.0

    def test_the_weld_reproduces_source_positions_bit_for_bit(self) -> None:
        """ "Lossless" is a claim this tier makes, so it is checked exactly.

        Averaging a cluster of identical doubles is not guaranteed to reproduce
        them once k >= 3, so the exact tier takes a representative instead.
        """
        source = box()
        welded = collapse(source, cell_m=0.0)
        assert set(map(tuple, welded.positions)) <= set(map(tuple, source.positions))

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

    def test_uv2_takes_a_representative_and_invents_no_state(self) -> None:
        """Two objects, two distinct constant codes, clustered coarsely enough
        that cells span both: every surviving value must be one of the two
        inputs. A mean would mint a third code that decodes as something
        neither object carried — the failure the representative pick exists to
        prevent, and the reason a UV2 payload must be constant across whatever
        this clusters."""
        first, second = box(), box(origin=(2.0, 0, 0))
        pair = merge(
            [
                replace(
                    first,
                    uv2=np.tile(
                        np.array([1026.0, 0.0], dtype=np.float32), (len(first.positions), 1)
                    ),
                ),
                replace(
                    second,
                    uv2=np.tile(
                        np.array([2050.0, 0.0], dtype=np.float32), (len(second.positions), 1)
                    ),
                ),
            ],
            name="tile",
        )
        decimated = collapse(pair, cell_m=8.0)
        assert decimated.uv2 is not None
        assert set(decimated.uv2[:, 0].tolist()) <= {1026.0, 2050.0}
        assert (decimated.uv2[:, 1] == 0.0).all()


class TestCollapseHeightField:
    """`height_field` drops the facing term, and a single-sided sheet needs it
    dropped.

    Keying on facing exists so a building's wall never averages into its roof.
    Ground has no such distinction, and where a slope crosses one of the six
    buckets the shared vertices land in different clusters, move to different
    means, and the sheet tears open — a hole through to the sky, which is why
    the gaps appear exactly where the ground is sloped.
    """

    def _slope(self, rise: float, run: float = 40.0, step: float = 2.0) -> MeshData:
        """A strip climbing `rise` over `run`, as a continuous triangulated sheet.

        Steep enough and the dominant normal axis flips from +Y to +X partway
        up, which is the boundary the facing key tears along.
        """
        xs = np.arange(0.0, run + step / 2, step)
        ys = rise * (xs / run) ** 3  # shallow at the foot, near-vertical at the top
        corners: list[list[tuple[float, float, float]]] = []
        for index in range(len(xs) - 1):
            a, b = (xs[index], ys[index]), (xs[index + 1], ys[index + 1])
            corners.append([(a[0], a[1], 0.0), (b[0], b[1], 0.0), (a[0], a[1], 20.0)])
            corners.append([(b[0], b[1], 0.0), (b[0], b[1], 20.0), (a[0], a[1], 20.0)])
        # Real normals, unlike most soup fixtures: which facing bucket one lands
        # in is the whole subject here, so they are derived through the pipeline's
        # own `triangle_cross` and `normalise` rather than through a lookalike.
        positions = np.array([c for face in corners for c in face], dtype=np.float64)
        triangles = np.arange(len(positions), dtype=np.uint32).reshape(-1, 3)
        return soup(corners, name="slope", normals=normalise(triangle_cross(positions, triangles)))

    def _covered(self, mesh: MeshData) -> float:
        """Share of this fixture's plan extent that still has surface over it.

        Coverage rather than triangle count, for the reason `helpers.covered`
        gives — and this fixture is where that reason was measured: both
        settings return 24 triangles, so a count reports the tear as absent.
        """
        return float(covered([mesh], np.arange(0.5, 40.0, 0.5), np.arange(0.5, 20.0, 0.5)).mean())

    def test_a_slope_that_tears_with_the_facing_key_survives_without_it(self) -> None:
        """The defect and the fix in one comparison. Measured on Wan Chai the
        same way round: region coverage 99.61% with the key, 99.84% without."""
        slope = self._slope(rise=25.0)
        torn = collapse(slope, cell_m=4.0)
        whole = collapse(slope, cell_m=4.0, height_field=True)

        assert self._covered(whole) > self._covered(torn)

    def test_it_does_not_grow_the_mesh(self) -> None:
        """The whole reason this is affordable: it is a different key, not a
        finer one, so it buys coverage without buying triangles."""
        slope = self._slope(rise=25.0)
        torn = collapse(slope, cell_m=4.0)
        whole = collapse(slope, cell_m=4.0, height_field=True)

        assert whole.triangle_count <= torn.triangle_count
        assert len(whole.positions) <= len(torn.positions)

    def test_a_wall_and_a_roof_still_refuse_to_merge_by_default(self) -> None:
        """The rule this is an exception to, pinned so the exception cannot
        become the rule. A box's faces meet at hard edges the style depends on,
        and off is what every class but the ground gets."""
        kept = collapse(box(size=20.0), cell_m=4.0)
        assert kept.triangle_count == 12
        assert kept.positions.min() == 0.0 and kept.positions.max() == 20.0

    def test_a_solid_is_the_wrong_thing_to_pass_it(self) -> None:
        """Stated as a test because it is the trade rather than a bug: with the
        facing key gone, the three faces meeting at a box's corner become one
        cluster and share a vertex. Harmless on a sheet, which has no corners
        like that; wrong for anything with an inside."""
        rounded = collapse(box(size=20.0), cell_m=16.0, height_field=True)
        square = collapse(box(size=16.0 * 1.25), cell_m=16.0)
        assert len(rounded.positions) < len(square.positions)


class TestSelectTriangles:
    def test_a_partition_loses_no_triangles_and_shares_no_vertex(self) -> None:
        """This is what lets an oversized mesh be split across tiles without a
        seam: triangles are moved, never cut."""
        source = merge([box(), box(origin=(100, 0, 0))], name="pair")
        left = source.triangle_centroids()[:, 0] < 50.0

        west = select_triangles(source, left)
        east = select_triangles(source, ~left)
        assert west.triangle_count + east.triangle_count == source.triangle_count
        assert west.positions.max(axis=0)[0] < east.positions.min(axis=0)[0]

    def test_unused_vertices_are_dropped(self) -> None:
        source = merge([box(), box(origin=(100, 0, 0))], name="pair")
        left = source.triangle_centroids()[:, 0] < 50.0
        assert len(select_triangles(source, left).positions) == 36

    def test_selecting_nothing_returns_nothing(self) -> None:
        assert select_triangles(box(), np.zeros(12, dtype=bool)) is None

    def test_one_mesh_in_one_out_keeps_its_material(self) -> None:
        """Both of these rebuild a `MeshData` field by field, so a field they
        forget is dropped silently — and a tile that lost its material name
        imports with the default `BaseMaterial3D` and renders as flat colour,
        which is what it looked like before `P3-7` anyway."""
        named = replace(box(), material="city_facade")

        assert select_triangles(named, np.ones(12, dtype=bool)).material == "city_facade"
        assert collapse(named, cell_m=0.5).material == "city_facade"


def _edge_counts(mesh: MeshData) -> dict[tuple, int]:
    """How many triangles walk each undirected edge, keyed on exact positions.

    Exact rather than rounded, deliberately: `slice_plane` claims neighbouring
    triangles compute bit-identical cut points, and a tolerance here would
    accept the crack that claim exists to rule out.
    """
    counts: dict[tuple, int] = {}
    for triangle in mesh.triangles:
        points = [tuple(mesh.positions[index]) for index in triangle]
        for first, second in ((0, 1), (1, 2), (2, 0)):
            key = tuple(sorted((points[first], points[second])))
            counts[key] = counts.get(key, 0) + 1
    return counts


class TestSlicePlane:
    """`slice_horizontal` off the Y axis, for `carve.py`'s prism walls.

    The invariant that matters is not the triangle count — it is that the
    surface stays *closed*. `carve.py` removes the inside of a cut volume, so a
    crack left here becomes an open shell whose backfaces cull to nothing, which
    is the invisible wall `Q19` exists to remove, returning as a hole.
    """

    def test_a_slanted_cut_leaves_the_surface_closed(self) -> None:
        """Every edge walked by exactly two triangles, on exact positions."""
        cut = slice_plane(box(size=10.0), (1.0, 1.0, 0.0), 7.0)

        assert set(_edge_counts(cut).values()) == {2}

    def test_it_conservesarea(self) -> None:
        """Subdividing is not clipping: nothing is discarded here."""
        source = box(size=10.0)
        cut = slice_plane(source, (1.0, 0.4, -0.3), 4.0)

        assert area(cut) == pytest.approx(area(source))
        assert cut.triangle_count > source.triangle_count

    def test_no_triangle_spans_the_plane_afterwards(self) -> None:
        """What makes a whole-triangle selection afterwards abut the cut
        exactly, with no seam to close between the two halves."""
        normal = normalise(np.array([[1.0, 1.0, 0.0]]))[0]
        cut = slice_plane(box(size=10.0), normal, 7.0)
        distance = (cut.positions @ normal - 7.0)[cut.triangles]

        assert not ((distance > 1e-6).any(axis=1) & (distance < -1e-6).any(axis=1)).any()

    def test_the_two_halves_partition_the_originalarea(self) -> None:
        """The pairing `carve.py` actually uses: slice, then select by side."""
        source = box(size=10.0)
        normal = normalise(np.array([[1.0, 1.0, 0.0]]))[0]
        cut = slice_plane(source, normal, 7.0)
        outside = cut.triangle_centroids() @ normal > 7.0

        kept = select_triangles(cut, outside)
        dropped = select_triangles(cut, ~outside)
        assert area(kept) + area(dropped) == pytest.approx(area(source))

    def test_winding_survives_the_cut(self) -> None:
        """A reversed piece renders as a hole under `cull_back` and as nothing
        else — the same class `arrows.py` and `tramway.py` count `inverted` for."""
        source = box(size=10.0)
        cut = slice_plane(source, (1.0, 1.0, 0.0), 7.0)
        outward = cut.triangle_centroids() - np.array([5.0, 5.0, 5.0])

        assert (np.sum(triangle_cross(cut.positions, cut.triangles) * outward, axis=1) > 0).all()

    def test_a_plane_that_misses_returns_the_mesh_unchanged(self) -> None:
        source = box(size=10.0)

        assert slice_plane(source, (1.0, 0.0, 0.0), 99.0).triangle_count == source.triangle_count

    def test_colour_interpolates_across_a_cut(self) -> None:
        """A channel left behind is a cut vertex wearing its neighbour's colour,
        which renders as a plausible smudge rather than as an error."""
        source = box(size=10.0)
        cut = slice_plane(source, (1.0, 0.0, 0.0), 5.0)

        assert cut.colours is not None
        assert set(map(tuple, cut.colours)) == set(map(tuple, source.colours))

    def test_a_zero_normal_is_refused(self) -> None:
        """It would divide by its own length and return NaN geometry, which
        writes a glTF full of NaN and imports as an empty tile."""
        with pytest.raises(ValueError, match="non-zero normal"):
            slice_plane(box(), (0.0, 0.0, 0.0), 1.0)

    def test_a_horizontal_plane_agrees_with_slice_horizontal(self) -> None:
        """The two share their topology and keep their own arithmetic, so this
        pins that the split itself did not drift between them."""
        source = box(size=10.0)
        general = slice_plane(source, (0.0, 1.0, 0.0), 4.0)
        special = slice_horizontal(source, [4.0])

        assert general.triangle_count == special.triangle_count
        assert general.positions == pytest.approx(special.positions)
