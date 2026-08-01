"""Surface sampling for `Q11` and `P2-7`.

`P1-2` measured Wan Chai's ground at a median 4.29 m above the vertical datum,
so taking level 0 as y=0 would bury every road. These check that the height
field answers what the terrain actually says, and — just as important — that it
says nothing rather than zero where the terrain does not reach.

`TestSlabs` and `TestSamplingAlongAPath` cover the second query. Its whole
reason to exist is that a flyover is a closed volume rather than a surface, so
the tests are built from slabs with two faces, and every one of them checks a
case where taking the highest hit gives the wrong deck.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.gltf import MeshData
from pipeline.terrain import HeightField, slab_tops

# Wide enough apart that the two faces of one slab never read as two structures.
GAP_M = 3.0


def _surface(triangles: list[list[tuple[float, float, float]]]) -> MeshData:
    positions = np.array(
        [corner for triangle in triangles for corner in triangle], dtype=np.float64
    )
    return MeshData(
        name="terrain",
        positions=positions,
        normals=np.tile(np.array([0.0, 1.0, 0.0], np.float32), (len(positions), 1)),
        triangles=np.arange(len(positions), dtype=np.uint32).reshape(-1, 3),
    )


def _quad(y00: float, y10: float, y01: float, y11: float, size: float = 10.0) -> MeshData:
    """A square patch spanning `(0, 0)`-`(size, size)` with the given corner heights."""
    a, b = (0.0, y00, 0.0), (size, y10, 0.0)
    c, d = (0.0, y01, size), (size, y11, size)
    return _surface([[a, b, c], [b, d, c]])


def _slab(
    x0: float, x1: float, top: float, rise: float = 0.0, depth: float = 1.5
) -> list[MeshData]:
    """A closed deck spanning `x0`-`x1` across the test corridor, as two faces.

    `top` is its height at `x0` and `rise` the climb to `x1`, so a ramp is one
    call. The underside is the same surface moved down by `depth`, which is what
    a real extruded deck is and why one query returns both.

    `depth` stays under the clustering gap on purpose: a fixture of single
    surfaces would pass these tests while testing nothing, because the whole
    reason the query exists is that a deck answers twice.
    """
    deck = _surface(
        [
            [(x0, top, 0.0), (x1, top + rise, 0.0), (x0, top, 30.0)],
            [(x1, top + rise, 0.0), (x1, top + rise, 30.0), (x0, top, 30.0)],
        ]
    )
    return [deck, deck.translated((0.0, -depth, 0.0))]


def _along(field: HeightField, xs: list[float]) -> np.ndarray:
    """Walk a straight path down the middle of the corridor, choosing by continuity."""
    return field.sample_along(xs, [15.0] * len(xs), slab_gap_m=GAP_M)


def _highest(field: HeightField, xs: list[float]) -> np.ndarray:
    """The same points, answered per-point. Paired with `_along` to show the contrast."""
    return field.sample(xs, [15.0] * len(xs))


class TestSampling:
    def test_a_flat_patch_returns_its_own_height(self) -> None:
        field = HeightField.from_meshes([_quad(4.0, 4.0, 4.0, 4.0)])
        np.testing.assert_allclose(field.sample([2.0, 8.0], [3.0, 9.0]), [4.0, 4.0])

    def test_a_slope_is_interpolated_across_the_triangle(self) -> None:
        """Barycentric, not nearest-vertex. Hong Kong's north shore climbs 50 m
        inside this region, so a road sampled per vertex would step rather than
        ramp if this snapped."""
        field = HeightField.from_meshes([_quad(0.0, 10.0, 0.0, 10.0)])
        np.testing.assert_allclose(
            field.sample([0.0, 2.5, 5.0, 10.0], [5.0] * 4), [0.0, 2.5, 5.0, 10.0]
        )

    def test_a_point_outside_the_terrain_is_nan_not_zero(self) -> None:
        """Substituting a height here would put the road back on the datum in
        exactly the places nobody looks — which is the bug this module exists
        to fix."""
        field = HeightField.from_meshes([_quad(4.0, 4.0, 4.0, 4.0)])
        assert np.isnan(field.sample([-50.0, 500.0], [0.0, 0.0])).all()

    def test_a_point_in_a_covered_cell_but_outside_every_triangle_is_nan(self) -> None:
        """The grid indexes bounding boxes, so a cell can hold a triangle that
        does not cover the query point. Returning that triangle's height anyway
        would be a plausible answer from the wrong surface."""
        field = HeightField.from_meshes(
            [_surface([[(0.0, 7.0, 0.0), (10.0, 7.0, 0.0), (0.0, 7.0, 10.0)]])]
        )

        assert field.sample([1.0], [1.0])[0] == pytest.approx(7.0)
        assert np.isnan(field.sample([9.0], [9.0])[0])

    def test_overlapping_surfaces_report_the_upper_one(self) -> None:
        """A sea wall projects both its faces onto the same plan position. The
        one a vehicle can be on is the top."""
        lower = _quad(0.0, 0.0, 0.0, 0.0)
        upper = _quad(6.0, 6.0, 6.0, 6.0)
        field = HeightField.from_meshes([lower, upper])

        assert field.sample([5.0], [5.0])[0] == pytest.approx(6.0)

    def test_near_vertical_triangles_are_dropped(self) -> None:
        """A wall has no plan area, so its barycentric coordinates divide by
        roughly zero. Dropped at build time rather than guarded per query."""
        wall = _surface([[(0.0, 0.0, 5.0), (10.0, 0.0, 5.0), (0.0, 9.0, 5.0)]])
        field = HeightField.from_meshes([_quad(2.0, 2.0, 2.0, 2.0), wall])

        assert field.triangle_count == 2
        assert field.sample([5.0], [5.0])[0] == pytest.approx(2.0)


class TestConstruction:
    def test_a_triangle_spanning_many_cells_is_found_from_all_of_them(self) -> None:
        """One terrain triangle here can span a whole flat block. Registering it
        only in the cell holding its first corner would leave holes."""
        field = HeightField.from_meshes([_quad(3.0, 3.0, 3.0, 3.0, size=100.0)], cell_m=8.0)

        heights = field.sample(np.arange(1.0, 100.0, 7.0), np.full(15, 50.0))
        np.testing.assert_allclose(heights, 3.0)

    def test_meshes_with_no_triangles_are_an_error(self) -> None:
        empty = MeshData(
            name="empty",
            positions=np.zeros((0, 3)),
            normals=np.zeros((0, 3), np.float32),
            triangles=np.zeros((0, 3), np.uint32),
        )
        with pytest.raises(ValueError, match="no triangles"):
            HeightField.from_meshes([empty])


class TestSlabs:
    def test_the_two_faces_of_one_deck_are_a_single_candidate(self) -> None:
        """The query that matters is which deck, and a deck answers twice."""
        np.testing.assert_allclose(slab_tops(np.array([4.5, 6.0]), GAP_M), [6.0])

    def test_stacked_structures_stay_separate_and_report_their_tops(self) -> None:
        hits = np.array([18.5, 4.5, 20.0, 6.0])
        np.testing.assert_allclose(slab_tops(hits, GAP_M), [6.0, 20.0])

    def test_a_gap_of_exactly_the_threshold_is_still_one_structure(self) -> None:
        """The tie goes to merging — splitting invents a deck that is not there.

        Wan Chai leaves less room here than it looks: gaps within a deck reach
        2.57 m and gaps between stacked structures start at 3.36 m, so the
        threshold has 0.79 m to sit in and both sides of it get a case."""
        np.testing.assert_allclose(slab_tops(np.array([3.0, 6.0]), GAP_M), [6.0])  # gap 3.0
        np.testing.assert_allclose(slab_tops(np.array([2.8, 6.0]), GAP_M), [2.8, 6.0])  # gap 3.2

    def test_nothing_underfoot_stays_nothing(self) -> None:
        assert not len(slab_tops(np.zeros(0), GAP_M))

    def test_a_nan_hit_is_dropped_rather_than_becoming_a_slab(self) -> None:
        """`np.sort` puts NaN last and no comparison against one is true, so an
        unfiltered NaN would end up the top of the highest slab — and from there
        the walk would carry it down the rest of the path."""
        hits = np.array([5.0, 6.0, 20.0, np.nan])
        np.testing.assert_allclose(slab_tops(hits, GAP_M), [6.0, 20.0])


class TestSamplingAlongAPath:
    def test_a_deck_under_a_flyover_keeps_its_own_deck(self) -> None:
        """The motivating case. Taking the highest hit hands the carriageway the
        flyover passing above it, which is how the ribbon ended up off by
        metres in the first place."""
        field = HeightField.from_meshes(
            [*_slab(0.0, 30.0, 6.0), *_slab(10.0, 20.0, 20.0)],
        )

        np.testing.assert_allclose(_highest(field, [5.0, 15.0, 25.0]), [6.0, 20.0, 6.0])
        np.testing.assert_allclose(_along(field, [5.0, 15.0, 25.0]), [6.0, 6.0, 6.0])

    def test_the_chosen_slab_is_neither_the_highest_nor_the_lowest(self) -> None:
        """Three structures over the middle station, and the right answer is the
        one in between. No height preference can produce it — only continuity."""
        field = HeightField.from_meshes(
            [*_slab(0.0, 30.0, 20.0), *_slab(10.0, 20.0, 6.0), *_slab(10.0, 20.0, 30.0)],
        )

        np.testing.assert_allclose(_highest(field, [15.0]), [30.0])
        np.testing.assert_allclose(_along(field, [5.0, 15.0, 25.0]), [20.0, 20.0, 20.0])

    def test_a_climbing_ramp_is_tracked_through_the_structure_above_it(self) -> None:
        """Wan Chai's actual geometry: `P2-7` found all 36 mixed-level nodes are
        ramps, and several climb under something else."""
        field = HeightField.from_meshes(
            [*_slab(0.0, 30.0, 0.0, rise=6.0), *_slab(10.0, 20.0, 20.0)],
        )

        np.testing.assert_allclose(_along(field, [0.0, 10.0, 15.0, 20.0, 30.0]), [0, 2, 3, 4, 6])

    def test_the_walk_runs_backwards_from_the_first_certain_station(self) -> None:
        """A ramp is ambiguous where it starts, under the deck it climbs to, and
        certain only once it emerges. The anchor is wherever it turns up."""
        field = HeightField.from_meshes(
            [*_slab(0.0, 30.0, 20.0), *_slab(0.0, 20.0, 30.0)],
        )

        np.testing.assert_allclose(_highest(field, [5.0, 15.0, 25.0]), [30.0, 30.0, 20.0])
        np.testing.assert_allclose(_along(field, [5.0, 15.0, 25.0]), [20.0, 20.0, 20.0])

    def test_a_path_that_is_ambiguous_everywhere_degrades_to_the_highest(self) -> None:
        """With no unambiguous station there is nothing to grow continuity from.
        Guessing a deck would be worse than answering what `sample` answers, and
        the caller's terrain gate still has to pass on it."""
        field = HeightField.from_meshes([*_slab(0.0, 30.0, 6.0), *_slab(0.0, 30.0, 20.0)])
        stations = [5.0, 15.0, 25.0]

        np.testing.assert_allclose(_along(field, stations), _highest(field, stations))

    def test_stations_off_the_structure_are_nan_and_do_not_break_the_walk(self) -> None:
        """A level-1 edge runs past the end of its own deck at both ends. Those
        stations have no answer, and the ones between them still do."""
        field = HeightField.from_meshes(
            [*_slab(0.0, 30.0, 6.0), *_slab(10.0, 20.0, 20.0)],
        )

        heights = _along(field, [-5.0, 5.0, 15.0, 25.0, 40.0])
        np.testing.assert_allclose(heights[1:4], [6.0, 6.0, 6.0])
        assert np.isnan(heights[[0, 4]]).all()

    def test_every_anchor_seeds_the_walk_not_merely_the_first(self) -> None:
        """A station with nothing under it settles nothing, and continuity
        cannot cross it, so a path can hold several independently anchored runs.
        Growing outward from only the first anchor would strand the far side on
        the highest hit — which is the deck this query exists to reject.

        No Wan Chai edge does this today: `P2-7` measured zero gaps strictly
        inside an edge's covered span. It is guarded because the sampler will
        meet other regions."""
        field = HeightField.from_meshes(
            [
                *_slab(0.0, 20.0, 6.0),
                *_slab(10.0, 20.0, 20.0),
                *_slab(30.0, 50.0, 6.0),
                *_slab(30.0, 40.0, 20.0),
            ],
        )
        # Deck, deck-under-flyover, nothing at all, deck-under-flyover, deck.
        stations = [5.0, 15.0, 25.0, 35.0, 45.0]

        np.testing.assert_allclose(_highest(field, stations), [6.0, 20.0, np.nan, 20.0, 6.0])
        np.testing.assert_allclose(_along(field, stations), [6.0, 6.0, np.nan, 6.0, 6.0])


class TestSamplingTheLowestStructureAbove:
    """The third query, and the one whose answer is the *opposite* of `sample`'s.

    It asks what a road is resting on, so anything higher is something the road
    passes under. Every fixture here therefore stacks a second structure over
    the first, because a single-slab fixture would agree with `sample` and prove
    nothing about which of the two rules is running.
    """

    def _lowest(self, field: HeightField, xs: list[float], floor: list[float]) -> np.ndarray:
        return field.sample_lowest_above(xs, [15.0] * len(xs), floor, slab_gap_m=GAP_M)

    def test_a_flyover_overhead_is_not_what_the_road_rests_on(self) -> None:
        """Gloucester Road under Canal Road Flyover, which is the case that
        decides this. `sample` reads the upper deck; a street is on the lower."""
        field = HeightField.from_meshes([*_slab(0.0, 20.0, 1.0), *_slab(0.0, 20.0, 12.0)])

        np.testing.assert_allclose(_highest(field, [10.0]), [12.0])
        np.testing.assert_allclose(self._lowest(field, [10.0], [0.0]), [1.0])

    def test_the_floor_is_read_per_point_because_the_ground_is_not_level(self) -> None:
        field = HeightField.from_meshes([*_slab(0.0, 40.0, 2.0), *_slab(0.0, 40.0, 9.0)])
        # The same two slabs, asked with a floor that rises past the lower one.
        np.testing.assert_allclose(self._lowest(field, [10.0, 30.0], [0.0, 5.0]), [2.0, 9.0])

    def test_a_floor_above_every_slab_finds_nothing(self) -> None:
        field = HeightField.from_meshes(_slab(0.0, 20.0, 4.0))
        assert np.isnan(self._lowest(field, [10.0], [20.0])).all()

    def test_a_nan_floor_admits_nothing_rather_than_everything(self) -> None:
        """With no ground to measure against there is no way to tell a ramp from
        a flyover overhead, so the lowest slab is as likely to be the wrong one.
        NaN also makes every comparison False, so this is the behaviour that
        falls out — pinned because the opposite would be silent and plausible."""
        field = HeightField.from_meshes([*_slab(0.0, 20.0, 1.0), *_slab(0.0, 20.0, 12.0)])
        assert np.isnan(self._lowest(field, [10.0], [np.nan])).all()

    def test_a_point_off_the_structure_is_nan_not_the_floor(self) -> None:
        field = HeightField.from_meshes(_slab(0.0, 20.0, 4.0))
        assert np.isnan(self._lowest(field, [500.0], [0.0])).all()

    def test_the_two_faces_of_one_deck_do_not_make_the_underside_the_answer(self) -> None:
        """The point of clustering, restated for this query: taking the lowest
        *hit* rather than the lowest *slab top* would return the underside, and
        put the road inside the deck it is driving on."""
        field = HeightField.from_meshes(_slab(0.0, 20.0, 6.0, depth=1.5))
        np.testing.assert_allclose(self._lowest(field, [10.0], [0.0]), [6.0])

    def test_a_floor_of_the_wrong_length_is_refused(self) -> None:
        field = HeightField.from_meshes(_slab(0.0, 20.0, 4.0))
        with pytest.raises(ValueError, match="floor has 1 values for 2 points"):
            field.sample_lowest_above([5.0, 10.0], [15.0, 15.0], [0.0], slab_gap_m=GAP_M)
