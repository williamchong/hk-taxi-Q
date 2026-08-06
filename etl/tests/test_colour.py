"""CIELAB conversion, and the hue-without-lightness split that depends on it."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pipeline.buildings import colour_for, facade_hue
from pipeline.colour import lab_to_srgb, reflectance, srgb_to_lab, with_hue
from pipeline.config import BuildingStyle, HeightBand, Material, MaterialAssignment
from tests.helpers import flat_mesh, style

CITY = "testville"


class TestConversion:
    def test_round_trip_is_exact_for_every_representable_colour(self) -> None:
        """Not "close enough": a lossy round trip would silently shift the hue
        of every building that keeps its measured colour."""
        rng = np.random.default_rng(0)
        rgb = rng.integers(0, 256, (20_000, 3))
        assert np.array_equal(lab_to_srgb(srgb_to_lab(rgb)), rgb.astype(np.uint8))

    @pytest.mark.parametrize(
        ("rgb", "lightness"),
        [((255, 255, 255), 100.0), ((0, 0, 0), 0.0), ((128, 128, 128), 53.59)],
    )
    def test_known_lightness(self, rgb: tuple[int, int, int], lightness: float) -> None:
        assert srgb_to_lab(np.array([rgb]))[0, 0] == pytest.approx(lightness, abs=0.01)

    def test_neutral_greys_have_no_hue(self) -> None:
        """Within 1e-4, not exactly: the published D65 white point is rounded and
        does not quite match the row sums of the published sRGB matrix, leaving
        ~2e-5 of residual chroma on a true grey. Four orders of magnitude below
        a just-noticeable difference, and the round trip above is still exact."""
        lab = srgb_to_lab(np.array([[v, v, v] for v in range(0, 256, 17)]))
        assert np.allclose(lab[:, 1:], 0.0, atol=1e-4)

    def test_out_of_gamut_is_clipped_rather_than_wrapped(self) -> None:
        """A wrapped channel would turn an over-saturated pale colour dark, and
        `uint8` alone cannot say which happened — 0-255 is true either way. The
        assertion is therefore about *direction*: a light violet asks for more
        red and blue than sRGB has, so both must saturate high rather than roll
        over, and green must stay below them."""
        red, green, blue = lab_to_srgb(np.array([[95.0, 120.0, -120.0]]))[0]
        assert (red, blue) == (255, 255)
        assert green < 255


class TestWithHue:
    def test_lightness_survives_and_hue_is_replaced(self) -> None:
        """The whole point of the split: the band still decides how light a
        building is, the photograph only decides what colour it is."""
        before = srgb_to_lab(np.array([[191, 198, 198]]))[0]
        after = srgb_to_lab(np.array([with_hue((191, 198, 198), (1.5, 8.0), 1.0)]))[0]
        assert after[0] == pytest.approx(before[0], abs=1.0)
        assert after[1] == pytest.approx(1.5, abs=0.6)
        assert after[2] == pytest.approx(8.0, abs=0.6)

    def test_strength_multiplies_the_measured_chroma(self) -> None:
        """What `strength: 2.0` in `hong_kong.yaml` claims to mean: in gamut it
        is a plain multiplier on `C*`, so the result is defensible as art
        direction rather than as a second measurement.

        Against the *requested* chroma rather than against each other, because
        the return is `uint8` and quantisation costs up to 0.6 `C*` either way —
        at a measured `C*` of 6 that is 10%, and a ratio of two round trips
        carries it twice. Which is itself the argument for amplifying: at
        `strength` 1.0 the whole signal is a couple of quantisation steps."""
        hue = (1.0, 6.0)
        for strength in (1.0, 2.0):
            lab = srgb_to_lab(np.array([with_hue((191, 198, 198), hue, strength)]))[0]
            assert np.hypot(*lab[1:]) == pytest.approx(np.hypot(*hue) * strength, abs=0.6)

    def test_strength_scales_chroma_without_reordering_it(self) -> None:
        """Above 1.0 is stylisation, and it must stay *monotonic* — exaggerating
        by how much a building is warm is defensible, changing which building is
        warmer is not."""
        warm = with_hue((191, 198, 198), (1.0, 9.0), 2.0)
        cool = with_hue((191, 198, 198), (-1.0, -6.0), 2.0)
        assert srgb_to_lab(np.array([warm]))[0, 2] > srgb_to_lab(np.array([cool]))[0, 2]

    def test_zero_strength_is_neutral(self) -> None:
        assert with_hue((190, 190, 190), (12.0, -9.0), 0.0) == (190, 190, 190)


def _style_with_hue(
    tmp_path: Path, table: dict, *, strength: float = 1.0, vegetation_max: float | None = None
) -> BuildingStyle:
    """A style whose survey is `table`, written where `facade_hue` will look.

    The survey lands under `source_dir`'s layout rather than beside `tmp_path`,
    because the layout is half of what these tests are pinning.
    """
    path = tmp_path / CITY / "facade_colour" / "hue.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(table))
    return replace(
        style(),
        material_assignment=MaterialAssignment(
            by_height=(
                HeightBand(
                    up_to_m=float("inf"),
                    material=Material(
                        name="high", colour=(190, 200, 200), reflectance=55.0, source="test"
                    ),
                ),
            ),
            rings=(),
        ),
        facade_hue_source="hue.json",
        facade_hue_strength=strength,
        facade_hue_vegetation_max=vegetation_max,
    )


class TestFacadeHue:
    """The survey's hue reaching the shipped colour, and the fallback when it
    does not.

    ⚠️ **Since `Q34` these are also the regression tests for the fallback path,
    and that is why `_style_with_hue` declares no `rings`.** With no surveyed
    rule a building takes the height ramp whether or not it was measured, which
    is the state a fresh clone is permanently in — the survey is a 4.9 GB
    gitignored read, so CI and every new checkout build the city these tests
    describe. A change that only worked when the draw was configured would pass
    a suite that never configures it.
    """

    def test_a_city_without_a_survey_gets_an_empty_table(self) -> None:
        assert facade_hue(style(), CITY) == {}

    def test_a_missing_file_is_not_an_error(self, tmp_path: Path) -> None:
        """⚠️ The load-bearing case. The survey is gitignored build cache, so
        every fresh clone hits this path and must still build a city."""
        loaded = _style_with_hue(tmp_path, {})
        (tmp_path / CITY / "facade_colour" / "hue.json").unlink()
        assert facade_hue(loaded, CITY, root=tmp_path) == {}

    def test_only_the_two_hue_axes_are_read(self, tmp_path: Path) -> None:
        """Pins the parse itself, not what `colour_for` later does with it:
        `a*` and `b*` are taken and `L*` is dropped before anything else runs."""
        loaded = _style_with_hue(tmp_path, {"B1234": {"lab": [60.0, 4.0, 12.0]}})
        assert facade_hue(loaded, CITY, root=tmp_path) == {"B1234": (4.0, 12.0)}

    def test_a_malformed_survey_names_the_file(self, tmp_path: Path) -> None:
        """A partial write is the likely failure of a cache this expensive, and
        colouring the city from half a survey is what must not happen quietly."""
        loaded = _style_with_hue(tmp_path, {})
        (tmp_path / CITY / "facade_colour" / "hue.json").write_text('{"B1234": {"lab": [60.0]}}')
        with pytest.raises(ValueError, match="malformed"):
            facade_hue(loaded, CITY, root=tmp_path)

    def test_the_variant_suffix_is_stripped_to_reach_the_key(self, tmp_path: Path) -> None:
        """The survey reads `…A0` models and the pipeline reads `…C0` ones; the
        stem is what joins them."""
        loaded = _style_with_hue(tmp_path, {"B1234": {"lab": [60.0, 4.0, 12.0]}})
        table = facade_hue(loaded, CITY, root=tmp_path)
        rgba = colour_for(loaded, "BUILDING", flat_mesh("B1234C0", 40.0), hue=table)
        assert rgba[0].tolist() == [*with_hue((190, 200, 200), (4.0, 12.0), 1.0), 255]

    def test_an_unsurveyed_building_keeps_its_band(self, tmp_path: Path) -> None:
        loaded = _style_with_hue(tmp_path, {"B1234": {"lab": [60.0, 4.0, 12.0]}})
        table = facade_hue(loaded, CITY, root=tmp_path)
        mesh = flat_mesh("B9999C0", 40.0)
        assert colour_for(loaded, "BUILDING", mesh, hue=table)[0].tolist() == [190, 200, 200, 255]

    def test_strength_reaches_the_shipped_colour(self, tmp_path: Path) -> None:
        """`hong_kong.yaml` ships `strength: 2.0`, so the knob has to survive the
        trip from config to vertex — not only work inside `with_hue`."""
        loaded = _style_with_hue(tmp_path, {"B1234": {"lab": [60.0, 4.0, 12.0]}}, strength=2.0)
        table = facade_hue(loaded, CITY, root=tmp_path)
        rgba = colour_for(loaded, "BUILDING", flat_mesh("B1234C0", 40.0), hue=table)
        assert rgba[0].tolist() == [*with_hue((190, 200, 200), (4.0, 12.0), 2.0), 255]

    def test_an_overgrown_row_is_dropped(self, tmp_path: Path) -> None:
        """43 of Wan Chai's 2,214 rows are over half canopy. What they measured
        is the tree, so the building falls back to its band."""
        table = {
            "B1234": {"lab": [60.0, 4.0, 12.0], "vegetation": 0.78},
            "B5678": {"lab": [60.0, 4.0, 12.0], "vegetation": 0.02},
        }
        loaded = _style_with_hue(tmp_path, table, vegetation_max=0.5)
        assert facade_hue(loaded, CITY, root=tmp_path) == {"B5678": (4.0, 12.0)}

    def test_a_row_exactly_at_the_threshold_is_kept(self, tmp_path: Path) -> None:
        """The comparison is `<=`, so the threshold names the worst sample still
        trusted rather than the best one rejected."""
        table = {"B1234": {"lab": [60.0, 4.0, 12.0], "vegetation": 0.5}}
        loaded = _style_with_hue(tmp_path, table, vegetation_max=0.5)
        assert facade_hue(loaded, CITY, root=tmp_path) == {"B1234": (4.0, 12.0)}

    def test_no_threshold_ignores_the_vegetation_column(self, tmp_path: Path) -> None:
        """The contract that keeps the filter optional. The mixed table is the
        point: with no threshold no row is read for vegetation, so one that
        records none and one that is *entirely* canopy both survive."""
        table = {
            "B1234": {"lab": [60.0, 4.0, 12.0]},
            "B5678": {"lab": [60.0, 4.0, 12.0], "vegetation": 1.0},
        }
        loaded = _style_with_hue(tmp_path, table)
        assert facade_hue(loaded, CITY, root=tmp_path) == {
            "B1234": (4.0, 12.0),
            "B5678": (4.0, 12.0),
        }

    def test_a_threshold_of_one_still_requires_the_column(self, tmp_path: Path) -> None:
        """Why the disabled state is `None` rather than 1.0: a city may want
        every row *and* the guarantee that the column was there to be checked."""
        loaded = _style_with_hue(
            tmp_path, {"B1234": {"lab": [60.0, 4.0, 12.0]}}, vegetation_max=1.0
        )
        with pytest.raises(ValueError, match="no `vegetation` column"):
            facade_hue(loaded, CITY, root=tmp_path)

    def test_a_threshold_without_the_column_names_the_config_key(self, tmp_path: Path) -> None:
        """⚠️ The failure worth being loud about, and worth being *specific*
        about: such a survey is intact and merely predates the column, so the
        message must not send the reader hunting for the partial write that
        `malformed` means everywhere else in this function."""
        loaded = _style_with_hue(
            tmp_path, {"B1234": {"lab": [60.0, 4.0, 12.0]}}, vegetation_max=0.5
        )
        with pytest.raises(ValueError, match=r"facade_hue\.vegetation_max"):
            facade_hue(loaded, CITY, root=tmp_path)

    def test_a_truncated_row_is_still_malformed(self, tmp_path: Path) -> None:
        """The other side of that split: a real partial write keeps the original
        message even while a threshold is set."""
        loaded = _style_with_hue(tmp_path, {}, vegetation_max=0.5)
        path = tmp_path / CITY / "facade_colour" / "hue.json"
        path.write_text('{"B1234": {"lab": [60.0], "vegetation": 0.1}}')
        with pytest.raises(ValueError, match="malformed"):
            facade_hue(loaded, CITY, root=tmp_path)

    def test_the_surveyed_lightness_is_not_used(self, tmp_path: Path) -> None:
        """⚠️ The rule the whole design rests on. The survey's L* is 20 here
        against the band's ~79; if it ever leaks through, this fails."""
        loaded = _style_with_hue(tmp_path, {"B1234": {"lab": [20.0, 3.0, 9.0]}})
        table = facade_hue(loaded, CITY, root=tmp_path)
        rgba = colour_for(loaded, "BUILDING", flat_mesh("B1234C0", 40.0), hue=table)
        lightness = srgb_to_lab(np.array([rgba[0, :3]]))[0, 0]
        band = srgb_to_lab(np.array([[190, 200, 200]]))[0, 0]
        assert lightness == pytest.approx(band, abs=1.5)


class TestReflectance:
    """The measurable half of the palette rule (`Q33`)."""

    def test_white_is_a_perfect_diffuser_and_black_reflects_nothing(self) -> None:
        assert reflectance((255, 255, 255)) == pytest.approx(100.0)
        assert reflectance((0, 0, 0)) == pytest.approx(0.0)

    def test_it_is_luminance_rather_than_perceptual_lightness(self) -> None:
        """Mid-grey is the case that tells the two apart, and getting it wrong
        would put every declared material out by a factor of two.

        `#808080` is `L*` 53.6 — near the middle perceptually — but reflects only
        21.6% of the light. The rule is a statement about light, so ratios
        between surfaces survive a change of exposure anchor; on `L*` they would
        not.
        """
        assert reflectance((128, 128, 128)) == pytest.approx(21.6, abs=0.1)

    def test_the_channels_are_weighted_by_the_srgb_primaries(self) -> None:
        """Green carries ~72% of luminance and blue ~7%, so a palette checked on
        a channel average would let a blue surface claim far more light than it
        reflects."""
        assert reflectance((0, 255, 0)) == pytest.approx(71.5, abs=0.1)
        assert reflectance((0, 0, 255)) == pytest.approx(7.2, abs=0.1)
