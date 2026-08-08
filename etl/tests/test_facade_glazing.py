"""The glazing bimodality check (`tools/facade_glazing.py`).

The sheet walk needs the source archives; what is testable offline is the
statistic itself — a dip that misreads a clean two-mode population, or reads a
valley into a single blob, would grade the contamination check with the wrong
instrument and the printed table would look exactly as authoritative.
"""

from __future__ import annotations

import numpy as np
from facade_glazing import (
    BIMODAL_BELOW,
    UNIMODAL_ABOVE,
    Verdict,
    dip_statistic,
    otsu_bin,
    verdict,
    wall_area_m2,
)

from pipeline.gltf import MeshData


def test_otsu_splits_two_separated_modes() -> None:
    hist = np.zeros(50)
    hist[10] = 100.0
    hist[40] = 100.0
    assert 10 <= otsu_bin(hist) < 40


def test_two_clean_modes_read_bimodal() -> None:
    rng = np.random.default_rng(7)
    lstar = np.concatenate([rng.normal(20, 3, 20_000), rng.normal(70, 3, 20_000)])
    assert verdict(lstar) == Verdict(dip=0.0, kind="bimodal")


def test_one_blob_reads_unimodal() -> None:
    rng = np.random.default_rng(7)
    dip = dip_statistic(rng.normal(50, 8, 40_000))
    assert dip > UNIMODAL_ABOVE
    # Otsu happily splits this blob (`Q40`: eta never goes low) — the dip is
    # what must refuse to see two modes where there is one.
    assert verdict(rng.normal(50, 8, 40_000)).kind == "unimodal"


def test_verdict_boundaries_are_the_recorded_ones() -> None:
    assert BIMODAL_BELOW == 0.25
    assert UNIMODAL_ABOVE == 0.60


def test_wall_area_counts_walls_and_ignores_roofs() -> None:
    # One 2x3 m wall facing south (+z normal), one 2x3 m roof facing up: the
    # roof triangle must not contribute — it is not a wall the survey reads.
    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 3.0, 0.0],
            [0.0, 10.0, 0.0],
            [2.0, 10.0, 0.0],
            [0.0, 10.0, 3.0],
        ],
        dtype=np.float32,
    )
    normals = np.array(
        [[0.0, 0.0, 1.0]] * 3 + [[0.0, 1.0, 0.0]] * 3,
        dtype=np.float32,
    )
    mesh = MeshData(
        name="wall-and-roof",
        positions=positions.astype(np.float64),
        normals=normals,
        triangles=np.array([[0, 1, 2], [3, 4, 5]]),
    )
    assert wall_area_m2([mesh]) == 3.0
