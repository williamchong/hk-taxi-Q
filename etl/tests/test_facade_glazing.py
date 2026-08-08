"""The glazing bimodality check (`tools/facade_glazing.py`).

The sheet walk needs the source archives; what is testable offline is the
statistic itself — a dip that misreads a clean two-mode population, or reads a
valley into a single blob, would grade the contamination check with the wrong
instrument and the printed table would look exactly as authoritative.
"""

from __future__ import annotations

from dataclasses import replace

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

from pipeline.gltf import Texture
from tests.helpers import soup


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
    lstar = np.random.default_rng(7).normal(50, 8, 40_000)
    # Otsu happily splits this blob (`Q40`: eta never goes low) — the dip is
    # what must refuse to see two modes where there is one.
    assert dip_statistic(lstar) > UNIMODAL_ABOVE
    assert verdict(lstar).kind == "unimodal"


def test_verdict_boundaries_are_the_recorded_ones() -> None:
    assert BIMODAL_BELOW == 0.25
    assert UNIMODAL_ABOVE == 0.60


def test_wall_area_counts_textured_walls_only() -> None:
    # A 3 m² wall triangle facing south (+z normal) and a 3 m² roof triangle
    # facing up. Only the wall may count — and only when the mesh carries
    # texture, because this area is the denominator of a texel density and an
    # untextured wall contributes nothing to its numerator.
    bare = soup(
        [
            [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 3.0, 0.0)],
            [(0.0, 10.0, 0.0), (2.0, 10.0, 0.0), (0.0, 10.0, 3.0)],
        ],
        name="wall-and-roof",
        normals=np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float32),
    )
    textured = replace(
        bare,
        uvs=np.zeros((len(bare.positions), 2), dtype=np.float32),
        texture=Texture(data=b"", mime_type="image/png"),
    )
    assert wall_area_m2([textured]) == 3.0
    assert wall_area_m2([bare]) == 0.0
