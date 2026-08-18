"""The narrowing sweep (`tools/narrowing.py`).

The same standard as the other tool tests: pin only what fails silently. The
sweep's headline is a count per factor, and a count that collapsed to zero would
be noticed. What would not announce itself is the factor simulation — it decides
every column, and a wrong one produces a full, plausible, entirely fictional
table.

⚠️ **The sweep's own baseline column is the real check, and it is not here** —
it is in `narrowing.check_baseline`, which the tool runs on itself. At `1.60x`
the sweep must reproduce `clearance.json` edge for edge, because that is the
width the bundle was actually drawn at; anything else means the factor
simulation is wrong and no other column means anything. It wants a built region,
so it refuses at run time rather than asserting in pytest.
"""

from __future__ import annotations

import numpy as np
import pytest
from narrowing import BUILDING, LANDMARK, UNOBSTRUCTED, class_meshes, moved, owner, scaled

from pipeline.gltf import MeshData


def _table(halves: list[float]) -> dict[int, dict]:
    return {7: {"edge": 7, "half_width_m": halves, "trim_m": [0.0, 0.0]}}


class TestScaled:
    """Simulating a lower `widen_default` without rebuilding the region."""

    def test_a_widened_station_narrows_to_the_factor(self) -> None:
        # 3.20 m authored half, drawn at 1.6x. At 1.3x it must be 3.2 x 1.3.
        table = scaled(_table([5.12, 5.12]), {7: 3.2}, 1.3)
        assert table[7]["half_width_m"] == [4.16, 4.16]

    def test_a_station_already_narrower_is_left_alone(self) -> None:
        # On structure, `widen_on_structure` draws at 1.0x whatever the default
        # is, so lowering the default must not touch it — and must never *widen*
        # it, which is what a bare multiply would do.
        table = scaled(_table([3.2, 5.12]), {7: 3.2}, 1.45)
        assert table[7]["half_width_m"] == [3.2, 4.64]

    def test_the_baseline_factor_changes_nothing(self) -> None:
        # The sweep's first column is the shipped city, and every later one is a
        # proposal against it — so this is what makes the comparison a comparison.
        halves = [5.12, 4.32, 3.2]
        assert scaled(_table(halves), {7: 3.2}, 1.6)[7]["half_width_m"] == halves

    def test_the_rest_of_the_entry_survives(self) -> None:
        # `walk` reads `trim_m` off the same entry, and a station the ribbon
        # never reached must stay unjudged at every factor.
        assert scaled(_table([5.12, 5.12]), {7: 3.2}, 1.3)[7]["trim_m"] == [0.0, 0.0]


class TestMoved:
    """Both directions, because narrowing can make an edge worse."""

    def test_an_edge_that_crosses_up_is_cleared(self) -> None:
        assert moved({1: 2.0}, {1: 3.5}, 3.2) == ([1], [])

    def test_an_edge_that_crosses_down_is_lost(self) -> None:
        # The finding the sweep exists to be able to see: clipping the corridor
        # trims a clear run that lay against one kerb.
        assert moved({1: 3.5}, {1: 2.0}, 3.2) == ([], [1])

    def test_an_edge_that_stays_put_is_neither(self) -> None:
        assert moved({1: 1.0, 2: 9.0}, {1: 1.5, 2: 8.0}, 3.2) == ([], [])

    def test_exactly_the_bar_counts_as_clear(self) -> None:
        # `>=` on the after side and `<=` on the before side, so an edge sitting
        # exactly on one lane is clear and has not moved.
        assert moved({1: 3.2}, {1: 3.2}, 3.2) == ([], [])
        assert moved({1: 3.19}, {1: 3.2}, 3.2) == ([1], [])

    def test_an_edge_in_only_one_side_is_neither(self) -> None:
        # It left or joined the population rather than crossing the bar, and
        # `main` refuses a sweep whose edge set moved — so this is the shape of
        # the guard rather than a case the report should invent a verdict for.
        assert moved({1: 1.0}, {}, 3.2) == ([], [])
        assert moved({}, {1: 1.0}, 3.2) == ([], [])


class TestOwner:
    """Which class is credited with blocking an edge."""

    def test_the_tightest_class_owns_it(self) -> None:
        assert owner({"A": 4.0, "B": 1.0, "C": 9.0}, clear=10.0) == "B"

    def test_an_edge_nothing_blocks_is_not_credited_to_a_class(self) -> None:
        # The bug this exists to stop: an unblocked edge returns the drawn width
        # from every class sweep, and a plain `min` over the three ties and falls
        # through to whichever key came first — 427 of the region's 737 edges.
        assert owner({"A": 8.0, "B": 8.0, "C": 8.0}, clear=8.0) == UNOBSTRUCTED

    def test_a_class_that_only_ties_is_not_blocking(self) -> None:
        assert owner({"A": 8.0, "B": 6.0}, clear=8.0) == "B"


class TestClassMeshes:
    """Pulling one class out of a tile that merged every class into one."""

    @staticmethod
    def _tile(colours: list[tuple[int, int, int]]) -> MeshData:
        # One triangle per colour, each with its three corners the same colour.
        count = len(colours)
        return MeshData(
            name="t",
            positions=np.zeros((count * 3, 3), dtype=np.float64),
            normals=np.zeros((count * 3, 3), dtype=np.float32),
            triangles=np.arange(count * 3, dtype=np.int32).reshape(count, 3),
            colours=np.array(
                [[*colour, 255] for colour in colours for _ in range(3)], dtype=np.uint8
            ),
        )

    def test_a_named_class_is_selected_by_its_colour(self, hong_kong) -> None:
        structure = hong_kong.buildings.structure_class
        other = hong_kong.buildings.class_materials[structure].colour
        tile = self._tile([other, (200, 30, 30)])
        assert len(class_meshes([tile], hong_kong, structure)[0].triangles) == 1

    def test_buildings_are_every_class_the_config_does_not_name(self, hong_kong) -> None:
        # ⚠️ *Every* entry. Subtracting only structure and ground left a third
        # flat-material class counted as a building — a bug the sibling grader
        # shipped once and records having shipped.
        flats = [material.colour for material in hong_kong.buildings.class_materials.values()]
        tile = self._tile([*flats, (200, 30, 30)])
        picked = class_meshes([tile], hong_kong, BUILDING)
        assert len(picked[0].triangles) == 1

    def test_a_triangle_whose_corners_disagree_belongs_to_neither(self, hong_kong) -> None:
        structure = hong_kong.buildings.structure_class
        seam = hong_kong.buildings.class_materials[structure].colour
        tile = self._tile([seam])
        # Repaint one corner: a triangle spanning two classes is a weld artefact
        # rather than a surface, so it must fall out of both.
        tile.colours[2] = [200, 30, 30, 255]
        assert class_meshes([tile], hong_kong, structure) == []
        assert class_meshes([tile], hong_kong, BUILDING) == []

    def test_an_unknown_class_is_refused_by_name(self, hong_kong) -> None:
        with pytest.raises(SystemExit, match="no colour to select it by"):
            class_meshes([self._tile([(1, 2, 3)])], hong_kong, LANDMARK)
