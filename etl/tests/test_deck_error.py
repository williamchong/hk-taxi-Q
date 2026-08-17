"""The `P2-7` acceptance tool (`tools/deck_error.py`).

Only the parts whose failure mode is **silent**. The tool's headline numbers
check themselves — run it on a bundle built without deck sampling and it must
reproduce the recorded 4.19 m baseline, which it does at 4.13 m — but a
classifier that quietly matches a tenth of what it should still produces a
plausible-looking table, and did: an exact colour test found 428 structure
triangles of 434,149 and read as a working filter.
"""

from __future__ import annotations

import numpy as np
import pytest
from deck_error import Faces, measure, nearest, stations, wears

# `INFRASTRUCTURE`'s `class_materials` entry and `colour_jitter` from
# `config/cities/hong_kong.yaml`. Copied rather than read through the `hong_kong`
# fixture on purpose: these test the *arithmetic* of the classifier, and they
# should not start failing because someone repainted a deck. `test_config.py`
# is where the shipped values are held to account.
GREY = (157, 154, 147)
JITTER = 0.06


class TestClassColour:
    """`colour_for` jitters every class by one factor across all three channels,
    so a class occupies a *ray* through its base colour rather than a value."""

    def test_the_unjittered_colour_is_its_own_class(self) -> None:
        assert wears(np.array([GREY]), GREY, JITTER).all()

    @pytest.mark.parametrize("factor", [0.95, 0.98, 1.0, 1.02, 1.05])
    def test_a_colour_anywhere_along_the_jitter_range_is_matched(self, factor: float) -> None:
        """The failure that started this: matching the base value alone finds
        only the meshes whose seed happened to land near a factor of one."""
        shade = np.array([[round(channel * factor) for channel in GREY]])
        assert wears(shade, GREY, JITTER).all(), shade

    def test_a_colour_past_the_configured_jitter_is_refused(self) -> None:
        far = np.array([[round(channel * 1.30) for channel in GREY]])
        assert not wears(far, GREY, JITTER).any()

    def test_a_building_band_colour_is_not_mistaken_for_structure(self) -> None:
        """Warm and grey are different directions, not different brightnesses,
        which is what makes one factor across three channels a discriminator."""
        bands = np.array([[194, 177, 149], [200, 189, 170], [204, 186, 157]])
        assert not wears(bands, GREY, JITTER).any()

    @pytest.mark.parametrize("base", [(255, 250, 240), (245, 240, 238)])
    def test_a_base_that_jitters_past_a_channel_is_refused(self, base) -> None:
        """`colour_for` clamps to 0-255, which truncates the ray and would make
        the interval test quietly wrong instead of loudly unavailable.

        `(245, 240, 238)` is the case that matters: no channel is at 255, so a
        guard testing the base alone lets it through — and then 13.5% of its
        jitter range rounds to colours this function rejects. Clamping bites at
        `base * (1 + jitter)`, not at 255."""
        with pytest.raises(SystemExit, match="channel limit"):
            wears(np.array([[250, 250, 250]]), base, JITTER)


class TestFaces:
    def _quad(self, y: float, *, upward: bool) -> np.ndarray:
        """A flat patch, wound so its face normal points up or down.

        The order that reads as "anticlockwise seen from above" is the one that
        gives a *downward* normal here, because game space is y-up and z runs
        into the screen: `(10,0,0) x (0,0,10)` is `(0,-100,0)`.
        """
        a, b, c, d = (0.0, y, 0.0), (10.0, y, 0.0), (0.0, y, 10.0), (10.0, y, 10.0)
        wound = [[a, c, b], [b, c, d]] if upward else [[a, b, c], [b, d, c]]
        return np.array(wound, dtype=np.float64)

    def test_an_upward_face_answers_its_own_height(self) -> None:
        faces = Faces.of(self._quad(6.0, upward=True), signed=True)
        np.testing.assert_allclose(faces.heights_at(5.0, 5.0), [6.0, 6.0])

    def test_a_downward_face_is_dropped_when_winding_is_read(self) -> None:
        """A deck's underside is as horizontal as its top. Keeping it would let
        a carriageway sunk into the deck score against the face below it."""
        faces = Faces.of(self._quad(6.0, upward=False), signed=True)
        assert not len(faces.heights_at(5.0, 5.0))

    def test_a_downward_face_is_kept_when_winding_is_ignored(self) -> None:
        faces = Faces.of(self._quad(6.0, upward=False), signed=False)
        np.testing.assert_allclose(faces.heights_at(5.0, 5.0), [6.0, 6.0])

    def test_a_point_off_the_geometry_finds_nothing(self) -> None:
        faces = Faces.of(self._quad(6.0, upward=True), signed=True)
        assert not len(faces.heights_at(500.0, 500.0))

    def test_a_vertical_face_carries_no_height_and_is_dropped(self) -> None:
        wall = np.array([[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 8.0, 0.0)]], dtype=np.float64)
        assert not len(Faces.of(wall, signed=False).corners)


class TestStations:
    def test_a_long_segment_is_broken_up_and_keeps_its_ends(self) -> None:
        line = np.array([[0.0, 5.0, 0.0], [30.0, 5.0, 0.0]])
        points = list(stations(line, 10.0))

        assert points[0] == (0.0, 5.0, 0.0)
        assert points[-1] == (30.0, 5.0, 0.0)
        assert max(np.diff([p[0] for p in points])) <= 10.0 + 1e-9

    def test_height_is_carried_along_so_a_ramp_is_followed(self) -> None:
        line = np.array([[0.0, 0.0, 0.0], [20.0, 4.0, 0.0]])
        heights = [y for _, y, _ in stations(line, 10.0)]
        np.testing.assert_allclose(heights, [0.0, 2.0, 4.0])

    def test_a_segment_shorter_than_the_spacing_is_left_whole(self) -> None:
        line = np.array([[0.0, 1.0, 0.0], [3.0, 1.0, 0.0]])
        assert len(list(stations(line, 10.0))) == 2


class TestNearest:
    def test_the_window_refuses_rather_than_falling_back_to_a_far_candidate(self) -> None:
        """The attribution rule. Returning the 5.0 here would score a flyover
        against the street beneath it and call the difference an error."""
        assert nearest(np.array([5.0, 12.0]), 8.5, 1.0) is None
        assert nearest(np.array([5.0, 12.0]), 12.1, 1.0) == pytest.approx(12.0)

    def test_without_a_window_the_nearest_always_wins(self) -> None:
        assert nearest(np.array([5.0, 12.0]), 8.5) == pytest.approx(5.0)

    def test_nothing_to_choose_from_is_none_not_zero(self) -> None:
        assert nearest(np.zeros(0), 3.0) is None


class TestMeasure:
    """The sign convention, which nothing else pins.

    If `drawn - deck` ever flipped, `deepest below the deck` would measure the
    wrong tail, the gate would never fire, and every bundle would pass forever.
    """

    def _deck(self, y: float) -> Faces:
        a, b, c, d = (0.0, y, 0.0), (20.0, y, 0.0), (0.0, y, 20.0), (20.0, y, 20.0)
        return Faces.of(np.array([[a, c, b], [b, c, d]], dtype=np.float64), signed=True)

    def test_a_carriageway_above_its_deck_reads_positive(self) -> None:
        errors, uncovered = measure(np.array([[10.0, 6.5, 10.0]]), self._deck(6.0))
        assert uncovered == 0
        np.testing.assert_allclose(errors, [0.5])

    def test_a_carriageway_sunk_into_its_deck_reads_negative(self) -> None:
        errors, _ = measure(np.array([[10.0, 5.6, 10.0]]), self._deck(6.0))
        np.testing.assert_allclose(errors, [-0.4])

    def test_a_station_with_no_deck_is_counted_rather_than_scored(self) -> None:
        errors, uncovered = measure(np.array([[900.0, 6.0, 900.0]]), self._deck(6.0))
        assert uncovered == 1
        assert not len(errors)

    def test_the_nearest_of_two_stacked_decks_wins(self) -> None:
        stacked = Faces.of(
            np.concatenate([self._deck(2.0).corners, self._deck(10.0).corners]), signed=True
        )
        errors, _ = measure(np.array([[10.0, 9.8, 10.0]]), stacked)
        np.testing.assert_allclose(errors, [-0.2])
