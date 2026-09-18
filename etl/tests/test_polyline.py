"""`pipeline.polyline`'s primitives that no stage's own tests pin directly."""

from __future__ import annotations

import numpy as np

from pipeline.polyline import true_runs


class TestTrueRuns:
    def test_each_run_is_half_open(self) -> None:
        flags = np.array([False, True, True, False, True])
        assert true_runs(flags) == [(1, 3), (4, 5)]

    def test_a_run_touching_both_ends_is_one_run(self) -> None:
        assert true_runs(np.array([True, True, True])) == [(0, 3)]

    def test_no_true_is_no_run(self) -> None:
        assert true_runs(np.array([False, False])) == []
        assert true_runs(np.zeros(0, dtype=bool)) == []
