"""`tools/node_step.py`, `P4-3`'s grader.

Only the parts whose failure is silent. A walk that read the wrong surface would
still print a full table of plausible steps, and a closed edge counted as open
would grade a 6 m drop nobody can drive, so each is pinned on a surface whose
right answer is known.
"""

from __future__ import annotations

import numpy as np
from _lib.bundle import Faces
from node_step import (
    GRADE_FLOOR_M,
    NOT_MEASURED,
    PITCH_M,
    STEP_BAR_M,
    open_edges,
    path_across,
    walk,
)


def _slab(x0: float, x1: float, y0: float, y1: float, half_m: float = 4.0) -> np.ndarray:
    """A road quad from `x0` to `x1` along +x, rising `y0` to `y1`, as two triangles."""
    a, b = [x0, y0, -half_m], [x1, y1, -half_m]
    c, d = [x1, y1, half_m], [x0, y0, half_m]
    return np.array([[a, b, c], [a, c, d]], dtype=np.float64)


def _faces(*slabs: np.ndarray) -> Faces:
    return Faces.of(np.concatenate(slabs), signed=False)


def _path(x0: float, x1: float, y: float) -> np.ndarray:
    xs = np.arange(x0, x1 + PITCH_M / 2, PITCH_M)
    return np.column_stack([xs, np.full(len(xs), y), np.zeros(len(xs))])


class TestWalk:
    def test_a_step_is_read_at_its_height(self) -> None:
        faces = _faces(_slab(0.0, 10.0, 4.10, 4.10), _slab(10.0, 20.0, 3.44, 3.44))
        step, station, lost = walk(faces, _path(0.5, 19.5, 4.10), 0.4)
        assert abs(step - 0.66) < 1e-9
        assert abs(_path(0.5, 19.5, 4.10)[station, 0] - 10.0) <= PITCH_M
        assert lost == 0

    def test_a_ramp_at_the_cap_is_no_step(self) -> None:
        """10% rises 0.025 m a station: continuity, never a step."""
        faces = _faces(_slab(0.0, 20.0, 4.0, 6.0))
        step, _, _ = walk(faces, _path(0.5, 19.5, 4.05), 0.4)
        assert step == 0.0
        assert 0.10 * PITCH_M < GRADE_FLOOR_M < STEP_BAR_M

    def test_an_overlapping_ribbon_is_not_stepped_onto(self) -> None:
        """A neighbouring carriageway 0.5 m higher, over the middle of the walk:
        the wheel stays on its own road. Taking the highest face read this."""
        faces = _faces(_slab(0.0, 20.0, 3.0, 3.0), _slab(6.0, 12.0, 3.5, 3.5))
        step, _, _ = walk(faces, _path(0.5, 19.5, 3.0), 0.4)
        assert step == 0.0

    def test_a_deck_overhead_is_invisible(self) -> None:
        faces = _faces(_slab(0.0, 20.0, 3.0, 3.0), _slab(-5.0, 25.0, 9.0, 9.0))
        step, _, lost = walk(faces, _path(0.5, 19.5, 3.0), 0.4)
        assert (step, lost) == (0.0, 0)

    def test_a_hole_is_counted_not_stepped(self) -> None:
        faces = _faces(_slab(0.0, 9.0, 3.0, 3.0), _slab(11.0, 20.0, 3.0, 3.0))
        step, _, lost = walk(faces, _path(0.5, 19.5, 3.0), 0.4)
        assert step == 0.0
        assert lost == 7

    def test_a_walk_with_no_road_at_its_start_is_unseeded(self) -> None:
        faces = _faces(_slab(0.0, 20.0, 3.0, 3.0))
        step, _, lost = walk(faces, _path(0.5, 19.5, 8.0), 0.4)
        assert np.isnan(step)
        assert lost > 0


class TestPathAcross:
    def test_the_node_is_at_zero_and_the_deck_negative(self) -> None:
        deck = np.array([[0.0, 4.0, 0.0], [-15.0, 5.0, 0.0]])
        street = np.array([[0.0, 3.0, 0.0], [15.0, 3.0, 0.0]])
        path, along = path_across(deck, street)
        assert along[0] == -15.0
        assert abs(along[-1] - 15.0) < 1e-9
        node = int(np.argmin(np.abs(along)))
        assert np.allclose(path[node], [0.0, 4.0, 0.0])
        assert np.diff(along).max() <= PITCH_M + 1e-9


class TestOpenEdges:
    def test_the_game_rule(self) -> None:
        """Level 0 always; off-grade on any judged width; never an unmeasured one."""
        graph = {
            "edges": [
                {"id": 1, "elevation_level": 0},
                {"id": 2, "elevation_level": 1},
                {"id": 3, "elevation_level": 1},
                {"id": 4, "elevation_level": -1},
            ]
        }
        manifest = {
            "carriageway": [
                {"edge": 2, "clear_width_m": [NOT_MEASURED, 6.4]},
                {"edge": 3, "clear_width_m": [NOT_MEASURED, NOT_MEASURED]},
                {"edge": 4, "clear_width_m": [NOT_MEASURED]},
            ]
        }
        assert open_edges(manifest, graph) == {1, 2}
