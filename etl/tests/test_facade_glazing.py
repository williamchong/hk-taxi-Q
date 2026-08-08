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
    mode_tint,
    otsu_bin,
    survey_rows,
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


def test_mode_tint_splits_where_the_dip_does_and_reads_each_mode() -> None:
    # A cool dark mode against a warm light one — the split the dip measures is
    # the split the tint reads, so each median lands inside its own mode.
    rng = np.random.default_rng(7)
    dark = np.stack(
        [rng.normal(20, 3, 30_000), np.zeros(30_000), rng.normal(-8, 1, 30_000)], axis=1
    )
    light = np.stack(
        [rng.normal(70, 3, 10_000), np.zeros(10_000), rng.normal(5, 1, 10_000)], axis=1
    )
    tint = mode_tint(np.concatenate([dark, light]))
    assert abs(tint["dark_share"] - 0.75) < 0.01
    assert abs(tint["dark_L"] - 20.0) < 1.0
    assert abs(tint["dark_b"] - (-8.0)) < 0.5
    assert abs(tint["light_L"] - 70.0) < 1.0
    assert abs(tint["light_b"] - 5.0) < 0.5


def test_survey_rows_key_by_stem_and_keep_no_atlas_column() -> None:
    row = {
        "building": "B352631575201063A0",
        "tex_per_m": 12.5,
        "atlas_dip": 0.241,
        "atlas_kind": "bimodal",
        "unwrap_dip": 0.972,
        "unwrap_kind": "unimodal",
        "dark_share": 0.4,
        "dark_L": 22.1,
        "dark_b": -6.3,
        "light_L": 68.0,
        "light_b": 2.2,
    }
    table = survey_rows([row], "11-SW-9D")
    assert set(table) == {"B352631575201063"}
    entry = table["B352631575201063"]
    assert entry["dip"] == 0.972
    assert entry["sheet"] == "11-SW-9D"
    assert not any("atlas" in key or "kind" in key for key in entry)


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
