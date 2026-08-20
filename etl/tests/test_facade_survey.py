"""The `Q37` survey tool (`tools/facade_survey.py`).

Only the parts whose failure mode is **silent**, which is most of this tool: the
defect it exists to fix produced a complete, well-formed, plausible-looking table
for two years. A guard that quietly matches nothing looks exactly like a guard
that had nothing to match.
"""

from __future__ import annotations

import numpy as np
import pytest
from facade_survey import (
    CLIP_LEVEL,
    FACES,
    MODAL_SHARE,
    PERCENTILE,
    VEGETATION_A,
    _atlas_filler,
    _pack,
    _repeats,
    coverage,
    estimate,
    face_of,
    filler_colours,
    is_filler,
    photographic,
)

from pipeline.colour import srgb_to_lab


def measure(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """`estimate` with the conversion its callers hoist out of it."""
    return estimate(rgb, srgb_to_lab(rgb))


# A filler grey the shipped table actually landed on, and the two the guard it
# replaces missed. `Q37`: 23 distinct greys across 222 rows, which is why this is
# a structural test and not a list.
FILLER = [(0, 0, 0), (60, 60, 60), (128, 128, 128), (193, 193, 193), (231, 231, 231)]


class TestFillerGuard:
    """Rejecting padding by structure rather than by enumeration."""

    @pytest.mark.parametrize("grey", FILLER)
    def test_every_exact_grey_is_filler(self, grey: tuple[int, int, int]) -> None:
        assert is_filler(np.array([grey])).all()

    @pytest.mark.parametrize("texel", [(128, 128, 129), (127, 128, 128), (60, 61, 60)])
    def test_one_channel_off_is_photography(self, texel: tuple[int, int, int]) -> None:
        """The guard has to be exact. Padding is written, not measured, so a tie
        to within a count is a real pixel and rejecting it would throw away the
        neutral end of every genuinely grey building."""
        assert not is_filler(np.array([texel])).any()


# `Q55`'s four damaging placeholders. None is a channel tie, so `Q37`'s guard
# passes every one; `(68, 65, 65)` is the one that also defeats any percentile,
# at `L*` 27.8 across 44-96% of a building's walls.
PANELS = [(68, 65, 65), (41, 37, 25), (136, 138, 137), (177, 178, 175)]


def atlas(colour: tuple[int, int, int], share: float, size: int = 64) -> np.ndarray:
    """A photographic atlas with one flat panel covering `share` of it.

    ⚠️ `share` is quantised by `MODAL_STRIDE` — the guard counts on a lattice, so
    at `size=64` only every fourth row is sampled and a nominal 0.10 reads 0.125.
    Use a larger `size` where the margin to `MODAL_SHARE` is the point.
    """
    rng = np.random.default_rng(11)
    image = rng.integers(0, 256, size=(size, size, 3), dtype=np.uint8)
    rows = round(size * share)
    image[:rows] = colour
    return image


class TestColourFiller:
    """`Q55`: the structural rule was right and its axis was wrong."""

    @pytest.mark.parametrize("panel", PANELS)
    def test_a_repeated_coloured_panel_is_found(self, panel: tuple[int, int, int]) -> None:
        """Each of these ships on a real building today and `is_filler`'s channel
        tie passes all four — which is the whole of `Q55`."""
        assert not is_filler(np.array([panel])).any()
        assert filler_colours({0: atlas(panel, 0.30)}) == frozenset({_pack(np.array([panel]))[0]})

    def test_a_photograph_repeats_nothing(self) -> None:
        """The guard must find nothing on real photography, or it eats the city.
        No natural colour survives a 20% bar."""
        rng = np.random.default_rng(3)
        assert (
            filler_colours({0: rng.integers(0, 256, size=(256, 256, 3), dtype=np.uint8)})
            == frozenset()
        )

    @pytest.mark.parametrize("grey", [(60, 60, 60), (0, 0, 0), (255, 255, 255)])
    def test_a_repeated_grey_is_not_reported_as_a_colour(self, grey: tuple[int, int, int]) -> None:
        """⚠️ **The two axes stay disjoint, and the sweep is why.** These three
        repeat past the bar on most atlases in the region, and `Q37`'s tie already
        rejects every one — so returning them changes no texel, but it would put a
        row in `--filler-report` for nearly every building, each with a zero delta,
        and bury `Q55`'s 93 in 2,213 rows of nothing.
        """
        assert is_filler(np.array([grey])).all(), "the tie already has it"
        assert filler_colours({0: atlas(grey, 0.30)}) == frozenset()

    def test_a_panel_under_the_bar_is_left_alone(self) -> None:
        """A deliberate blind spot, and the reason `Q55` calls every figure a
        lower bound: a small panel beside a multi-megapixel photograph is inert
        (median 0.5% of walls, worst 0.82 `L*`), so the bar buys safety cheaply."""
        assert filler_colours({0: atlas((68, 65, 65), MODAL_SHARE / 2, size=256)}) == frozenset()

    def test_the_rejection_is_per_texel_not_per_atlas(self) -> None:
        """⚠️ **The constraint `Q55` states outright.** Four of the atlases it
        found are 4096-square photographs of real buildings carrying an embedded
        panel, 33,981 to 82,565 distinct colours apiece. Dropping the atlas would
        discard the building; dropping the panel's texels is correct.
        """
        image = atlas((68, 65, 65), 0.30, size=256)
        colours, distinct = _atlas_filler(image)
        assert distinct > 1000, "this atlas is a photograph, not a panel"

        # ⚠️ Asserted through `_repeats`, not `is_filler`. `is_filler` also
        # applies `Q37`'s tie, and a random background texel that happens to be
        # an exact grey is *correctly* rejected by that axis — which made the
        # obvious spelling of this test seed-dependent (it failed 8 seeds in 30).
        texels = image.reshape(-1, 3)
        rejected = _repeats(texels, colours)
        assert rejected.any() and not rejected.all()
        assert (texels[rejected] == (68, 65, 65)).all()
        assert (texels[~rejected] != (68, 65, 65)).any(axis=1).all()

    def test_dark_filler_defeats_the_percentile_and_the_guard_still_takes_it(self) -> None:
        """⚠️ **The mechanism `Q37`'s brightness argument does not reach.**
        `Q37` reasoned that filler is *bright*, so a top-percentile median selects
        it. `(68,65,65)` is `L*` 27.8 — far below any plausible cut — and wins
        anyway by sheer mass: at 90% of the sample the cut lands *inside* the
        filler, so the order statistic cannot escape it wherever it falls.
        """
        panel = np.tile([68.0, 65.0, 65.0], (900, 1))
        bright = np.tile([200.0, 150.0, 120.0], (50, 1))
        dark = np.tile([30.0, 25.0, 20.0], (50, 1))
        texels = np.vstack([dark, panel, bright])
        lab = srgb_to_lab(texels)

        unguarded = estimate(texels, lab)
        assert unguarded is not None
        assert unguarded[1].tolist() == [68.0, 65.0, 65.0], "filler wins the cut"

        colours = filler_colours({0: texels.astype(np.uint8).reshape(1, -1, 3)})
        guarded = estimate(texels, lab, colours)
        assert guarded is not None
        assert guarded[1].tolist() == [200.0, 150.0, 120.0], "the facade comes back"

    def test_an_all_panel_building_is_refused_not_recoloured(self) -> None:
        """`estimate`'s refusal has to survive the new axis: a building whose
        walls are entirely placeholder must emit no row, exactly as an all-grey
        one does, so `facade_hue` falls back to the height band."""
        texels = np.tile([68.0, 65.0, 65.0], (5000, 1))
        colours = filler_colours({0: texels.astype(np.uint8).reshape(1, -1, 3)})
        assert estimate(texels, srgb_to_lab(texels), colours) is None

    def test_no_colours_is_exactly_the_shipped_guard(self) -> None:
        """⚠️ **The property `facade_glazing.py` rides on.** It calls
        `photographic` with two arguments and is deliberately left on `Q37`'s axis
        alone, so the default must be the old function and not merely close to it
        — including the exact black its untextured-canvas rejection depends on.
        """
        rng = np.random.default_rng(7)
        texels = rng.integers(0, 256, size=(4000, 3), dtype=np.uint8)
        texels[:100] = texels[:100, :1]
        tie = (texels[:, 0] == texels[:, 1]) & (texels[:, 1] == texels[:, 2])

        assert np.array_equal(is_filler(texels), tie)
        assert np.array_equal(is_filler(texels, frozenset()), tie)
        assert is_filler(np.array([(0, 0, 0)])).all()
        lab = srgb_to_lab(texels.astype(float))
        assert np.array_equal(photographic(texels, lab), ~tie & (lab[:, 1] >= VEGETATION_A))


class TestEstimator:
    """The order statistic, and what it refuses to answer."""

    def test_bright_filler_does_not_reach_the_estimate(self) -> None:
        """`Q37`'s mechanism in one assertion: filler at `L*` 91.6 outranks a
        darker real facade, so an unguarded top-percentile median lands on the
        padding. Half the sample is filler here — past the point where the shipped
        survey went achromatic."""
        facade = np.tile([118.0, 111.0, 105.0], (500, 1))
        padding = np.tile([231.0, 231.0, 231.0], (500, 1))
        lab, lit = measure(np.vstack([facade, padding]))
        assert lit.tolist() == [118.0, 111.0, 105.0]
        assert abs(lab[1]) > 1.0, "a real facade is not achromatic"

    def test_an_all_filler_building_is_refused_not_neutralised(self) -> None:
        """The whole defect. A sample with no photography in it must produce no
        row, so `facade_hue` falls back to the height band — never a grey one."""
        assert measure(np.tile([128.0, 128.0, 128.0], (5000, 1))) is None

    def test_canopy_is_excluded(self) -> None:
        """A row measured off a tree sits 4.45 `a*` to the green side of the
        rest, and `strength: 2.0` doubles that onto the wall."""
        facade = np.tile([150.0, 145.0, 140.0], (500, 1))
        leaves = np.tile([70.0, 140.0, 60.0], (500, 1))
        assert srgb_to_lab(leaves[:1])[0, 1] < VEGETATION_A
        _, lit = measure(np.vstack([facade, leaves]))
        assert lit.tolist() == [150.0, 145.0, 140.0]

    def test_the_cut_is_the_recorded_percentile(self) -> None:
        """A dark majority and a bright minority: the estimate must come from the
        bright tail, which is the property that makes it a lit-facade estimate
        rather than a whole-building average.

        The split has to straddle the cut. A block of *identical* texels wider
        than the cut is admitted whole, because every one of them compares equal
        to the percentile — harmless on photography, which does not tie at that
        scale, and the one thing that does tie is filler, already excluded above.
        """
        dark = np.tile([40.0, 42.0, 44.0], (600, 1))
        bright = np.tile([200.0, 190.0, 180.0], (400, 1))
        assert PERCENTILE >= 60.0, "the cut has to land above the dark block"
        _, lit = measure(np.vstack([dark, bright]))
        assert lit.tolist() == [200.0, 190.0, 180.0]


class TestFaceAssignment:
    def test_each_axis_lands_on_its_compass_name(self) -> None:
        names = list(FACES)
        normals = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
        assigned = face_of(normals)
        # Before the name lookup: `names[-1]` is "S", so a face_of that failed to
        # recognise the south wall at all would still spell out the right list.
        assert (assigned >= 0).all(), "every one of these is a wall"
        assert [names[index] for index in assigned] == ["E", "W", "N", "S"]

    def test_a_roof_is_not_a_wall(self) -> None:
        assert (face_of(np.array([[0.0, 1.0, 0.0], [0.0, -1.0, 0.0]])) == -1).all()

    def test_a_corner_takes_one_face_and_the_tie_break_is_pinned(self) -> None:
        """A 45-degree corner is equidistant from two faces, and `argmax` settles
        it by taking the lower column — east here, not south. Counting it on both
        would weight the corner above the walls either side of it."""
        assigned = face_of(np.array([[0.7071, 0.0, 0.7071]]))
        assert assigned[0] == list(FACES).index("E")


class TestCoverage:
    def test_a_full_quad_covers_every_texel(self) -> None:
        uvs = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        triangles = np.array([[0, 1, 2], [0, 2, 3]])
        assert coverage(uvs, triangles, 16, 16).all()

    def test_an_overlapping_triangle_counts_a_texel_once(self) -> None:
        """A mask, not a tally: tessellation is a property of the mesh, and
        counting per triangle would let it weight the colour."""
        uvs = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        doubled = np.array([[0, 1, 2], [0, 2, 3], [0, 1, 2], [0, 2, 3]])
        assert coverage(uvs, doubled, 16, 16).sum() == 256

    def test_an_untouched_atlas_region_is_not_sampled(self) -> None:
        uvs = np.array([[0.0, 0.0], [0.5, 0.0], [0.5, 0.5]])
        mask = coverage(uvs, np.array([[0, 1, 2]]), 32, 32)
        assert mask.any() and not mask.all()
        assert not mask[24:, 24:].any()


class TestRowColumns:
    """The two columns that are not the estimate, one of which the pipeline
    filters on."""

    def test_a_partly_clipped_texel_counts_as_clipped(self) -> None:
        """`clipped` names blown highlights. Testing every channel instead of any
        would match only white — which `is_filler` already rejects — so the column
        would quietly report a slice of the padding and never a burnt-out wall."""
        blown = np.array([[255, 180, 90]])
        assert (blown >= CLIP_LEVEL).any(axis=1).all()
        assert not (blown >= CLIP_LEVEL).all(axis=1).any()
        assert not is_filler(blown).any()

    def test_the_canopy_share_is_measured_before_exclusion(self) -> None:
        """`vegetation` is the pipeline's own filter key (`vegetation_max`), so it
        has to describe the sample that was gathered, not the one left after the
        canopy was dropped — otherwise every row reports zero."""
        facade = np.tile([150.0, 145.0, 140.0], (750, 1))
        leaves = np.tile([70.0, 140.0, 60.0], (250, 1))
        pooled = np.vstack([facade, leaves])
        assert (srgb_to_lab(pooled)[:, 1] < VEGETATION_A).mean() == pytest.approx(0.25)
