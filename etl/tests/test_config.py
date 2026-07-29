"""City config loading tests.

These also serve as the check that `hong_kong.yaml` stays consistent with
docs/DATA_SOURCES.md — a config that parses but describes the wrong place is
the expensive failure here, not a syntax error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from pipeline.config import CITIES_ROOT, SUPPORTED_SCHEMA, load_city


@pytest.fixture
def hong_kong():
    return load_city("hong_kong")


@pytest.fixture
def rewrite(tmp_path: Path):
    """Load the real config, mutate it, and write it somewhere disposable.

    Mutating the real file beats a hand-written fixture: a stub would drift out
    of step with the schema and keep passing while the real config broke.
    """

    def _rewrite(mutate) -> Path:
        document = yaml.safe_load((CITIES_ROOT / "hong_kong.yaml").read_text(encoding="utf-8"))
        mutate(document)
        (tmp_path / "hong_kong.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
        return tmp_path

    return _rewrite


def test_hong_kong_loads(hong_kong) -> None:
    assert hong_kong.id == "hong_kong"
    assert hong_kong.projected_crs == "EPSG:2326"
    assert hong_kong.geodetic_crs == "EPSG:4326"
    assert hong_kong.sources


def test_wan_chai_region_matches_the_documented_corridor(hong_kong) -> None:
    bounds = hong_kong.projected_bounds("wan_chai")
    assert bounds.width_m == pytest.approx(1650.0, abs=50.0)
    assert bounds.height_m == pytest.approx(900.0, abs=50.0)


def test_game_transform_puts_the_region_next_to_the_origin(hong_kong) -> None:
    """Large absolute coordinates cost float precision in the engine, which is
    the reason for a local origin at all.

    Checks the corner furthest from the origin — the south-east one, since the
    origin sits north-west (Q7) — because that is where any drift shows up.
    """
    transform = hong_kong.game_transform("wan_chai")
    bounds = hong_kong.projected_bounds("wan_chai")
    x, _, z = transform.to_game(bounds.max_easting, bounds.min_northing)
    assert 0.0 < x < 2000.0
    assert 0.0 < z < 1000.0


class TestCityOffset:
    """Q10: regions keep local origins, and carry their offset in a shared frame."""

    def test_offset_reconciles_the_region_and_city_frames_exactly(self, hong_kong) -> None:
        """The property the whole scheme rests on: a region-local position plus
        its offset is the city-space position, for every point.

        Exact rather than approximate — both legs are pure translation, so any
        drift here would mean an arithmetic error, not float noise.
        """
        region = hong_kong.game_transform("wan_chai")
        city = hong_kong.city_transform()
        offset = hong_kong.city_offset("wan_chai")
        bounds = hong_kong.projected_bounds("wan_chai")

        corners = [
            (bounds.min_easting, bounds.max_northing),
            (bounds.max_easting, bounds.min_northing),
            (836000.0, 815900.0),
        ]
        for easting, northing in corners:
            local = region.to_game(easting, northing, 12.5)
            in_city = city.to_game(easting, northing, 12.5)
            assert tuple(local[i] + offset[i] for i in range(3)) == pytest.approx(in_city)

    def test_offset_is_non_negative(self, hong_kong) -> None:
        """City origin is the city's NW corner, so every region lies east and
        south of it. A negative component means a region outside the city."""
        x, _, z = hong_kong.city_offset("wan_chai")
        assert x >= 0.0
        assert z >= 0.0

    def test_region_frame_stays_local(self, hong_kong) -> None:
        """The reason for keeping a per-region origin at all: the geometry the
        player drives through must stay near zero, where float32 is precise.

        Wan Chai sits ~38 km out in city space, where float32 resolves to ~4 mm.
        """
        bounds = hong_kong.projected_bounds("wan_chai")
        region = hong_kong.game_transform("wan_chai")
        far_corner = region.to_game(bounds.max_easting, bounds.min_northing)
        assert max(abs(v) for v in far_corner) < 2000.0

        city = hong_kong.city_transform()
        assert city.to_game(bounds.max_easting, bounds.min_northing)[0] > 30_000.0

    def test_city_origin_does_not_move_when_a_region_is_added(self, rewrite) -> None:
        """The stability requirement, stated as a test.

        A frame derived from the regions defined so far would shift each time one
        was added, silently relocating every region already published against the
        old value. Anchoring on declared city bounds is what prevents that.
        """
        before = load_city("hong_kong").city_transform()

        def add_region(doc: dict[str, Any]) -> None:
            doc["regions"]["kowloon_tsim_sha_tsui"] = {
                "name": "Tsim Sha Tsui",
                "bounds": {"west": 114.168, "east": 114.180, "south": 22.294, "north": 22.302},
                "tile_size_m": 150.0,
            }

        after = load_city("hong_kong", cities_root=rewrite(add_region)).city_transform()
        assert after == before

    def test_region_outside_the_city_bounds_is_rejected(self, rewrite) -> None:
        """It would still produce coordinates — just with a negative offset,
        placing the region north or west of the frame everything else uses."""

        def move_region_out(doc: dict[str, Any]) -> None:
            doc["regions"]["wan_chai"]["bounds"]["east"] = 120.0

        with pytest.raises(ValueError, match="outside the city bounds"):
            load_city("hong_kong", cities_root=rewrite(move_region_out))


def test_missing_city_bounds_is_rejected(rewrite) -> None:
    root = rewrite(lambda doc: doc.pop("bounds"))
    with pytest.raises(ValueError, match="bounds"):
        load_city("hong_kong", cities_root=root)


class TestBuildingStyle:
    """P1-2's palette and LOD tiers are tuning data, so they are validated here
    rather than trusted at the point of use."""

    def test_it_loads(self, hong_kong) -> None:
        style = hong_kong.buildings
        assert "BUILDING" in style.classes
        assert style.height_bands[-1].up_to_m == float("inf")
        assert style.lod_cell_sizes_m[0] == 0.0

    def test_terrain_is_not_a_building_class(self, hong_kong) -> None:
        """The tile output is specified to contain no textures, and the LandsD
        terrain ships a 45-megapixel JPEG per sheet."""
        assert not any("TERRAIN" in name for name in hong_kong.buildings.classes)

    def test_unordered_height_bands_are_rejected(self, rewrite) -> None:
        """`colour_for` returns the first band a height fits, so an out-of-order
        table silently paints towers with the shophouse colour."""

        def shuffle(doc: dict[str, Any]) -> None:
            doc["buildings"]["height_bands"].reverse()

        with pytest.raises(ValueError, match="ascending"):
            load_city("hong_kong", cities_root=rewrite(shuffle))

    def test_a_closed_last_band_is_rejected(self, rewrite) -> None:
        """Without an open-ended band there is no colour for a building taller
        than the table — and those are what a Hong Kong skyline is read by."""

        def close_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["height_bands"][-1]["up_to_m"] = 500.0

        with pytest.raises(ValueError, match=r"\.inf"):
            load_city("hong_kong", cities_root=rewrite(close_it))

    def test_a_malformed_colour_is_rejected(self, rewrite) -> None:
        def break_colour(doc: dict[str, Any]) -> None:
            doc["buildings"]["height_bands"][0]["colour"] = "beige"

        with pytest.raises(ValueError, match="#rrggbb"):
            load_city("hong_kong", cities_root=rewrite(break_colour))

    def test_lod_cell_sizes_must_coarsen(self, rewrite) -> None:
        def invert(doc: dict[str, Any]) -> None:
            doc["buildings"]["lod_cell_sizes_m"] = [4.0, 1.5, 0.0]

        with pytest.raises(ValueError, match="coarsest last"):
            load_city("hong_kong", cities_root=rewrite(invert))

    def test_jitter_outside_zero_to_one_is_rejected(self, rewrite) -> None:
        def overdo_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["colour_jitter"] = 1.5

        with pytest.raises(ValueError, match="colour_jitter"):
            load_city("hong_kong", cities_root=rewrite(overdo_it))

    def test_missing_buildings_block_is_rejected(self, rewrite) -> None:
        with pytest.raises(ValueError, match="buildings"):
            load_city("hong_kong", cities_root=rewrite(lambda doc: doc.pop("buildings")))

    def test_colour_comes_from_the_band_a_height_falls_in(self, hong_kong) -> None:
        style = hong_kong.buildings
        assert style.colour_for("BUILDING", 5.0) == style.height_bands[0].colour
        assert style.colour_for("BUILDING", 1_000.0) == style.height_bands[-1].colour

    def test_a_class_colour_wins_over_the_bands(self, hong_kong) -> None:
        style = hong_kong.buildings
        assert style.colour_for("INFRASTRUCTURE", 5.0) == style.class_colours["INFRASTRUCTURE"]
        assert style.colour_for("INFRASTRUCTURE", 200.0) == style.class_colours["INFRASTRUCTURE"]


def test_elevation_levels_map_grade_separation_to_deck_heights(hong_kong) -> None:
    assert hong_kong.deck_height_m(0) == 0.0
    assert hong_kong.deck_height_m(2) > hong_kong.deck_height_m(1) > hong_kong.deck_height_m(0)
    assert hong_kong.deck_height_m(-1) < 0.0


def test_unmapped_elevation_level_raises(hong_kong) -> None:
    """A tunnel dragged to 0.0 by a default would invent a junction with the
    road above it — silently, and only visible when traffic drives through a
    wall."""
    with pytest.raises(KeyError, match="ELEVATION 7"):
        hong_kong.deck_height_m(7)


def test_unknown_region_names_the_known_ones(hong_kong) -> None:
    with pytest.raises(KeyError, match="wan_chai"):
        hong_kong.region("central")


def test_schema_version_mismatch_is_rejected(rewrite) -> None:
    root = rewrite(lambda doc: doc.__setitem__("schema_version", SUPPORTED_SCHEMA + 1))
    with pytest.raises(ValueError, match="schema_version"):
        load_city("hong_kong", cities_root=root)


def test_missing_geodetic_crs_is_rejected(rewrite) -> None:
    """The datum of the bounds is exactly the thing that must never default."""
    root = rewrite(lambda doc: doc["crs"].pop("geodetic"))
    with pytest.raises(ValueError, match="geodetic"):
        load_city("hong_kong", cities_root=root)


def test_string_keyed_elevation_levels_are_rejected(rewrite) -> None:
    """YAML resolves bare -1 to an int and quoted "-1" to a str. The quoted form
    parses fine and produces a map no ELEVATION lookup can ever hit."""

    def quote_keys(doc: dict[str, Any]) -> None:
        doc["elevation_levels"] = {str(k): v for k, v in doc["elevation_levels"].items()}

    with pytest.raises(ValueError, match="not an integer"):
        load_city("hong_kong", cities_root=rewrite(quote_keys))


def test_boolean_elevation_level_keys_are_rejected(rewrite) -> None:
    """PyYAML implements YAML 1.1, where a bare `on`/`off`/`yes`/`no` key
    resolves to a bool — and bool subclasses int, so a plain integer check waves
    it through. `off:` would then land on level 0, silently redefining the ground
    every road in the region sits on.

    Level 1 is removed first only because True == 1 as a dict key, so the two
    would collapse in the fixture before the loader ever saw them.
    """

    def add_bool_key(doc: dict[str, Any]) -> None:
        levels = {k: v for k, v in doc["elevation_levels"].items() if k != 1}
        levels[True] = 6.0
        doc["elevation_levels"] = levels

    with pytest.raises(ValueError, match="not an integer"):
        load_city("hong_kong", cities_root=rewrite(add_bool_key))


def test_missing_ground_level_is_rejected(rewrite) -> None:
    root = rewrite(lambda doc: doc["elevation_levels"].pop(0))
    with pytest.raises(ValueError, match="level 0"):
        load_city("hong_kong", cities_root=root)
