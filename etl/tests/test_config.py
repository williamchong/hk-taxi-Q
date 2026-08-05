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
        # Finest first. Not "the first is 0.0" — an exact-weld tier is a
        # shipping decision, and Wan Chai stopped shipping one when `P2-1`'s
        # review found LOD1 indistinguishable at closest range.
        assert style.lod_cell_sizes_m[0] == min(style.lod_cell_sizes_m)

    def test_the_ground_is_tiled_without_jitter_and_with_a_sink(self, hong_kong) -> None:
        """`P3-10` put the terrain class in `classes`, which `P1-2` had kept it
        out of because the LandsD terrain ships a 45-megapixel JPEG per sheet.
        The rule it was protecting is unchanged and lives in `verify_tiles.gd` —
        the tile output carries no textures — and `buildings._ground` is what
        keeps it true. What this asserts is the two settings the ground cannot
        be tiled *correctly* without: no jitter, because it arrives as a handful
        of sheet-sized meshes rather than one mesh per object, and a sink,
        because `roads.py` lays the level-0 carriageway coplanar with it."""
        style = hong_kong.buildings
        assert style.terrain_class in style.classes
        assert style.jitter_for(style.terrain_class) == 0.0
        assert style.jitter_for("BUILDING") > 0.0
        assert style.ground_sink_m > 0.0

    def test_structure_is_a_building_class(self, hong_kong) -> None:
        """The mirror of the rule above, and for the opposite reason. `P2-7`
        lays the off-grade carriageway on this class and is accepted against the
        *shipped* tiles, so structure the ETL alone can see would put the road
        in the right place relative to nothing the player ever meets."""
        assert hong_kong.buildings.structure_class in hong_kong.buildings.classes

    def test_a_structure_class_that_is_never_tiled_is_rejected(self, rewrite) -> None:
        # A name that is not in `classes` rather than the terrain class, which
        # used to stand in for one and has been tiled since `P3-10`.
        def use_untiled(doc: dict[str, Any]) -> None:
            doc["buildings"]["structure_class"] = "VEGETATION"

        with pytest.raises(ValueError, match="which is not in classes"):
            load_city("hong_kong", cities_root=rewrite(use_untiled))

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

    def test_a_class_may_override_the_lod_cell_sizes(self, hong_kong) -> None:
        """Infrastructure is thinner than the cell that decimates a building, so
        one cell size for both folds a flyover deck into a sliver (`P2-1`)."""
        style = hong_kong.buildings
        assert style.cell_size_m("INFRASTRUCTURE", 1) < style.cell_size_m("BUILDING", 1)
        assert style.cell_size_m("BUILDING", 1) == style.lod_cell_sizes_m[1]

    def test_an_unoverridden_class_takes_the_default_table(self, hong_kong) -> None:
        style = hong_kong.buildings
        for level in range(len(style.lod_cell_sizes_m)):
            assert style.cell_size_m("BUILDING", level) == style.lod_cell_sizes_m[level]

    def test_class_lod_override_must_name_a_real_class(self, rewrite) -> None:
        """The same trap as `class_colours`: a misspelling parses, loads, and
        silently overrides nothing."""

        def misspell(doc: dict[str, Any]) -> None:
            doc["buildings"]["class_lod_cell_sizes_m"] = {"INFRASTRUCTUR": [0.0, 0.5, 1.0]}

        with pytest.raises(ValueError, match="not in classes"):
            load_city("hong_kong", cities_root=rewrite(misspell))

    def test_class_lod_override_must_match_the_tier_count(self, rewrite) -> None:
        """A short table index-errors partway through a build, after the
        expensive read; a long one describes tiers that never exist."""

        def truncate(doc: dict[str, Any]) -> None:
            # One short of whatever the city declares, so the test cannot go
            # vacuous the next time the tier count changes.
            short = doc["buildings"]["lod_cell_sizes_m"][:-1]
            doc["buildings"]["class_lod_cell_sizes_m"] = {"INFRASTRUCTURE": short}

        with pytest.raises(ValueError, match="tiers"):
            load_city("hong_kong", cities_root=rewrite(truncate))

    def test_class_lod_override_must_coarsen(self, rewrite) -> None:
        def invert(doc: dict[str, Any]) -> None:
            doc["buildings"]["class_lod_cell_sizes_m"] = {"INFRASTRUCTURE": [1.0, 0.5, 0.0]}

        with pytest.raises(ValueError, match="coarsest last"):
            load_city("hong_kong", cities_root=rewrite(invert))

    def test_jitter_outside_zero_to_one_is_rejected(self, rewrite) -> None:
        def overdo_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["colour_jitter"] = 1.5

        with pytest.raises(ValueError, match="colour_jitter"):
            load_city("hong_kong", cities_root=rewrite(overdo_it))

    def test_a_class_jitter_wins_over_the_default(self, hong_kong) -> None:
        style = hong_kong.buildings
        assert style.jitter_for(style.terrain_class) == 0.0
        assert style.jitter_for("BUILDING") == style.colour_jitter

    def test_class_jitter_override_must_name_a_real_class(self, rewrite) -> None:
        """The same trap as `class_colours` and `class_lod_cell_sizes_m`: a
        misspelling parses, loads, and silently overrides nothing — and the
        symptom here is the ground rendering in six shades, which reads as a
        source defect rather than as a typo."""

        def misspell(doc: dict[str, Any]) -> None:
            doc["buildings"]["class_colour_jitter"] = {"TERRAIN(TP)": 0.0}

        with pytest.raises(ValueError, match="not in classes"):
            load_city("hong_kong", cities_root=rewrite(misspell))

    @pytest.mark.parametrize("value", [1.5, -0.1, float("nan"), float("inf")])
    def test_class_jitter_outside_zero_to_one_is_rejected(self, rewrite, value) -> None:
        """The same range as the default, through the same helper.

        `.nan` and `.inf` are in here for `P2-7`'s reason rather than for
        completeness: YAML 1.1 resolves both, and a NaN passes every sign test
        then makes every comparison it feeds silently false. `0.0 <= value`
        happens to reject it, which is the property worth pinning down."""

        def overdo_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["class_colour_jitter"] = {"BUILDING": value}

        with pytest.raises(ValueError, match=r"class_colour_jitter\.BUILDING"):
            load_city("hong_kong", cities_root=rewrite(overdo_it))

    @pytest.mark.parametrize("spoil", ["drop", "zero"])
    def test_tiling_the_ground_without_a_sink_is_rejected(self, rewrite, spoil) -> None:
        """The silent failure this check exists for: `roads.py` lays the level-0
        carriageway at `terrain + 0.0`, so a tiled ground with no sink is
        coplanar with the road by construction and z-fights the length of the
        network. That reads as a rendering bug, not as a missing key.

        ⚠️ **An explicit `0.0` is the case worth parametrising for.** The first
        version of this check tested whether the *key* was present, which reads
        as equivalent and is not: `_measures` admits zero, so `ground_sink_m:
        0.0` loaded happily into exactly the coplanar state the message
        describes. Missing and zero have to arrive at the same error."""

        def spoil_it(doc: dict[str, Any]) -> None:
            if spoil == "drop":
                del doc["buildings"]["ground_sink_m"]
            else:
                doc["buildings"]["ground_sink_m"] = 0.0

        with pytest.raises(ValueError, match="ground_sink_m"):
            load_city("hong_kong", cities_root=rewrite(spoil_it))

    def test_a_sink_without_a_tiled_ground_is_allowed(self, rewrite) -> None:
        """One direction only, on `structure_class`'s precedent. A city that
        samples the ground for road heights without drawing it has correct
        output, and refusing its unused key would reject it for nothing."""

        def stop_tiling_it(doc: dict[str, Any]) -> None:
            terrain = doc["buildings"]["terrain_class"]
            doc["buildings"]["classes"] = [
                name for name in doc["buildings"]["classes"] if name != terrain
            ]
            for table in ("class_colours", "class_colour_jitter", "class_lod_cell_sizes_m"):
                doc["buildings"][table].pop(terrain, None)

        city = load_city("hong_kong", cities_root=rewrite(stop_tiling_it))
        assert city.buildings.terrain_class not in city.buildings.classes

    @pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf")])
    def test_an_unusable_ground_sink_is_rejected(self, rewrite, value) -> None:
        def spoil_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["ground_sink_m"] = value

        with pytest.raises(ValueError, match="ground_sink_m"):
            load_city("hong_kong", cities_root=rewrite(spoil_it))

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


class TestRoadNetwork:
    """The `roads:` block is mostly the publisher's schema rather than tuning,
    and a wrong column name there produces an attribute that is uniformly null
    rather than an error — so it is checked at load."""

    def test_the_shipped_mapping_matches_the_published_data_specification(self, hong_kong) -> None:
        roads = hong_kong.roads
        assert roads.centrelines.layer == "CENTERLINE"
        assert roads.centrelines.field("travel_direction") == "TRAVEL_DIRECTION"
        assert roads.turns.field("first_end") == "EDGE1END"
        # 1 = both ways, 3 = the digitised direction only, per the spec.
        assert roads.travel_directions == {1: "both", 3: "forward"}
        assert roads.source in hong_kong.sources

    def test_columns_are_deduplicated(self, hong_kong) -> None:
        """Two roles may name one column; reading it twice is an OGR error."""
        columns = hong_kong.roads.speed_limits.columns
        assert len(columns) == len(set(columns))

    def test_a_layer_missing_a_role_is_rejected(self, rewrite) -> None:
        def drop_direction(doc: dict[str, Any]) -> None:
            doc["roads"]["centrelines"]["fields"].pop("travel_direction")

        with pytest.raises(ValueError, match="travel_direction"):
            load_city("hong_kong", cities_root=rewrite(drop_direction))

    def test_an_unknown_direction_word_is_rejected(self, rewrite) -> None:
        """`roadgraph.json` has a closed vocabulary. A typo here would ship a
        direction the game has no branch for."""

        def misspell(doc: dict[str, Any]) -> None:
            doc["roads"]["travel_directions"][3] = "one-way"

        with pytest.raises(ValueError, match="expected one of"):
            load_city("hong_kong", cities_root=rewrite(misspell))

    def test_boolean_travel_direction_keys_are_rejected(self, rewrite) -> None:
        """The YAML 1.1 trap again: a bare `on:` key resolves to True, and
        True == 1 as a dict key, so it would silently redefine two-way."""

        def add_bool_key(doc: dict[str, Any]) -> None:
            codes = {k: v for k, v in doc["roads"]["travel_directions"].items() if k != 1}
            codes[True] = "forward"
            doc["roads"]["travel_directions"] = codes

        with pytest.raises(ValueError, match="not an integer"):
            load_city("hong_kong", cities_root=rewrite(add_bool_key))

    def test_a_source_the_city_does_not_publish_is_rejected(self, rewrite) -> None:
        def rename(doc: dict[str, Any]) -> None:
            doc["roads"]["source"] = "not_fetched"

        with pytest.raises(ValueError, match="not in sources"):
            load_city("hong_kong", cities_root=rewrite(rename))

    def test_a_negative_simplify_tolerance_is_rejected(self, rewrite) -> None:
        def invert(doc: dict[str, Any]) -> None:
            doc["roads"]["simplify_tolerance_m"] = -1.0

        with pytest.raises(ValueError, match="simplify_tolerance_m"):
            load_city("hong_kong", cities_root=rewrite(invert))

    def test_an_unknown_ground_source_is_rejected(self, rewrite) -> None:
        def mistype(doc: dict[str, Any]) -> None:
            doc["roads"]["ground"] = "sea level"

        with pytest.raises(ValueError, match="expected one of terrain, datum"):
            load_city("hong_kong", cities_root=rewrite(mistype))

    def test_a_missing_roads_block_is_rejected(self, rewrite) -> None:
        with pytest.raises(ValueError, match="'roads'"):
            load_city("hong_kong", cities_root=rewrite(lambda doc: doc.pop("roads")))

    def test_a_negative_kerb_is_rejected(self, rewrite) -> None:
        """A negative kerb turns the lip inside out, inverting its winding so it
        renders as a hole — plausible-looking output, which is why the loader
        refuses it rather than leaving it to be noticed in the engine."""

        def invert(doc: dict[str, Any]) -> None:
            doc["roads"]["surface"]["kerb_height_m"] = -0.15

        with pytest.raises(ValueError, match="kerb_height_m must not be negative"):
            load_city("hong_kong", cities_root=rewrite(invert))


class TestWidening:
    """Which factor an edge takes, and which rule wins when two of them match.

    The precedence is the part worth pinning. Nothing downstream would fail
    loudly if the tables were consulted in the other order — an expressway
    flyover would simply be drawn 1.3x and hang over its parapet, which is the
    defect `widen_by_elevation_level` exists to remove and which reads as
    ordinary road until someone drives it.
    """

    def test_an_at_grade_road_takes_the_speed_rule(self, hong_kong) -> None:
        surface = hong_kong.roads.surface
        assert surface.widen_for(50, elevation_level=0) == 1.6
        assert surface.widen_for(70, elevation_level=0) == 1.3

    def test_structure_is_drawn_at_its_authored_width(self, hong_kong) -> None:
        """1.0 is the narrowest the loader permits, and it means "as authored" —
        the ribbon has to stay on the deck `P2-7` put it on."""
        assert hong_kong.roads.surface.widen_for(50, elevation_level=1) == 1.0

    def test_the_level_rule_beats_a_speed_rule_that_also_matches(self, hong_kong) -> None:
        """The Wan Chai Interchange is both: signed at 70 and up on structure.
        A combined or speed-first reading would draw it 1.3x wide."""
        assert hong_kong.roads.surface.widen_for(70, elevation_level=1) == 1.0

    def test_a_level_with_no_rule_falls_through_to_the_speed_rule(self, hong_kong) -> None:
        """Level -1 is deliberately unconfigured. A tunnel has no deck to
        overhang, so there is no measured defect to fix, and `Q21` asks whether
        it should be drawn at all — this pins that the fix left it alone."""
        surface = hong_kong.roads.surface
        assert -1 not in surface.widen_by_elevation_level
        assert surface.widen_for(70, elevation_level=-1) == 1.3

    def test_a_level_zero_station_on_structure_takes_the_authored_width(self, hong_kong) -> None:
        """`Q23`. The edge is level 0 and signed at 50, so both at-grade rules
        match — and the station is still standing on a ramp deck."""
        surface = hong_kong.roads.surface
        assert surface.widen_for(50, elevation_level=0, on_structure=True) == 1.0
        assert surface.widen_for(50, elevation_level=0, on_structure=False) == 1.6

    def test_the_level_rule_still_beats_the_station(self, hong_kong) -> None:
        """Ordering, and it is load bearing. `ISLAND EASTERN CORRIDOR`'s stub is
        level 1 with no structure found anywhere under it, so it takes the flat
        offset and reports every station as *off* structure. If the station won,
        that edge would go back to 1.3x and hang over a deck that is not there.
        """
        surface = hong_kong.roads.surface
        assert surface.widen_for(70, elevation_level=1, on_structure=False) == 1.0

    def test_a_station_off_structure_is_the_default(self, hong_kong) -> None:
        """A city with no deck sampling publishes `on_structure` false
        everywhere, and must be drawn exactly as it was before `Q23`."""
        surface = hong_kong.roads.surface
        assert surface.widen_for(50, elevation_level=0) == surface.widen_for(
            50, elevation_level=0, on_structure=False
        )

    @pytest.mark.parametrize("table", ["widen_by_min_speed_limit_kph", "widen_by_elevation_level"])
    def test_a_factor_below_one_is_rejected_in_either_table(self, rewrite, table: str) -> None:
        """Narrowing below the authored width is a typo, not a tuning choice:
        the graph's width already comes from a lane count, so a sub-1 factor
        draws a carriageway narrower than its own lanes."""

        def narrow(doc: dict[str, Any]) -> None:
            doc["roads"]["surface"][table] = {1: 0.9}

        with pytest.raises(ValueError, match=r"widening factor 0\.9 is below 1\.0"):
            load_city("hong_kong", cities_root=rewrite(narrow))

    @pytest.mark.parametrize("key", [True, False, "1"])
    def test_a_key_that_is_not_a_plain_integer_is_rejected(self, rewrite, key) -> None:
        """PyYAML is YAML 1.1, where bare `on`/`off`/`yes`/`no` are booleans, and
        `bool` subclasses `int` — so `off: 1.0` becomes level **0** and drops
        every at-grade road in the region to its authored width. The output
        loads and renders; only the road is wrong. `elevation_levels` refuses
        the same spellings, and these two tables are keyed on the same domain."""

        def odd_key(doc: dict[str, Any]) -> None:
            doc["roads"]["surface"]["widen_by_elevation_level"] = {key: 1.0}

        with pytest.raises(ValueError, match="is not an integer"):
            load_city("hong_kong", cities_root=rewrite(odd_key))

    def test_a_rule_for_a_level_the_city_never_maps_is_rejected(self, rewrite) -> None:
        """Inert rather than wrong, which is why it needs saying: the rule can
        never fire, so the ribbon keeps its at-grade width and the output looks
        like a city that never asked for the rule at all."""

        def unmapped(doc: dict[str, Any]) -> None:
            doc["roads"]["surface"]["widen_by_elevation_level"] = {7: 1.0}

        with pytest.raises(ValueError, match="elevation_levels does not map"):
            load_city("hong_kong", cities_root=rewrite(unmapped))

    def test_a_city_that_declares_no_level_table_widens_everything_alike(self, rewrite) -> None:
        """The pre-fix behaviour stays reachable, and the table stays optional
        for the second city, which may not have structure at all."""

        def drop(doc: dict[str, Any]) -> None:
            doc["roads"]["surface"].pop("widen_by_elevation_level")

        city = load_city("hong_kong", cities_root=rewrite(drop))
        assert city.roads.surface.widen_by_elevation_level == {}
        assert city.roads.surface.widen_for(70, elevation_level=1) == 1.3

    def test_widen_on_structure_below_one_is_rejected_like_the_tables(self, rewrite) -> None:
        """It is a widening factor and shares their floor. Checked separately
        because it is a scalar rather than a table, so the loop that guards the
        tables would not have reached it."""

        def narrow(doc: dict[str, Any]) -> None:
            doc["roads"]["surface"]["widen_on_structure"] = 0.9

        with pytest.raises(ValueError, match=r"widening factor 0\.9 is below 1\.0"):
            load_city("hong_kong", cities_root=rewrite(narrow))

    def test_a_negative_taper_is_rejected(self, rewrite) -> None:
        """It would run the blend backwards and widen the road onto the deck —
        the defect being fixed, arriving through its own fix."""

        def backwards(doc: dict[str, Any]) -> None:
            doc["roads"]["surface"]["structure_taper_m"] = -5.0

        with pytest.raises(ValueError, match="structure_taper_m"):
            load_city("hong_kong", cities_root=rewrite(backwards))


class TestDeckSampling:
    """`roads.deck` is optional, and every way it can be present but unusable is
    refused at load rather than ignored.

    The failure it guards against is not a crash: a block that parses and is
    never read leaves the carriageway on the flat `elevation_levels` offset, so
    the output looks exactly like a city that never asked for deck sampling at
    all. That is the shape of config error that survives review."""

    def test_the_shipped_thresholds_stay_inside_their_measured_margins(self, hong_kong) -> None:
        """Bounds rather than the shipped literals, because these are tuning
        values and `P2-7` may well retune them.

        Each bound is the margin the city file's own comment argues from, so
        this fails when a retune breaks the reasoning and stays quiet when it
        does not — which a pinned literal has backwards."""
        deck = hong_kong.roads.deck
        assert deck is not None

        # Between the widest gap measured across one deck and the narrowest
        # between two stacked ones. Outside it, the query either splits a single
        # deck in two or merges a flyover into the road beneath it.
        assert 2.57 < deck.slab_gap_m < 3.36
        # Between the lowest genuine ramp touchdown and the ISLAND EASTERN
        # CORRIDOR samples the gate exists to reject.
        assert 0.543 < deck.max_below_terrain_m < 8.181
        # Above the sampling wobble that makes the lift profiles non-monotone,
        # and well inside the 0.5 m acceptance it is the residual step for.
        assert 0.2 <= deck.at_grade_m < 0.5
        # No margin to state: this one is set by the single 71.5 m vertex gap it
        # exists to break up, so all that can be said is that it does.
        assert 0.0 < deck.resample_m < 71.5

    def test_a_city_that_declares_no_block_samples_no_deck(self, rewrite) -> None:
        """The pre-`P2-7` behaviour has to stay reachable: a city whose sources
        carry no structure can only use the flat offset."""

        def drop(doc: dict[str, Any]) -> None:
            doc["roads"].pop("deck")

        city = load_city("hong_kong", cities_root=rewrite(drop))
        assert city.roads.deck is None

    @pytest.mark.parametrize("key", ["resample_m", "slab_gap_m"])
    def test_a_non_positive_span_is_rejected(self, rewrite, key: str) -> None:
        """Zero is degenerate for both: a spacing of zero asks for infinitely
        many stations, and a slab gap of zero makes every distinct height its
        own slab, which defeats the clustering the query is built on."""

        def zero(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"][key] = 0.0

        with pytest.raises(ValueError, match=f"{key} must be positive"):
            load_city("hong_kong", cities_root=rewrite(zero))

    @pytest.mark.parametrize("key", ["max_below_terrain_m", "at_grade_m"])
    def test_a_negative_tolerance_is_rejected(self, rewrite, key: str) -> None:
        """Zero is a coherent if strict choice for these two, so only the sign
        is checked — a negative one inverts the comparison it feeds."""

        def invert(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"][key] = -1.0

        with pytest.raises(ValueError, match=f"{key} must not be negative"):
            load_city("hong_kong", cities_root=rewrite(invert))

    def test_deck_sampling_without_terrain_ground_is_rejected(self, rewrite) -> None:
        """Both the gate and the fallback are measured against the ground mesh,
        so under `datum` the block could never run."""

        def to_datum(doc: dict[str, Any]) -> None:
            doc["roads"]["ground"] = "datum"

        with pytest.raises(ValueError, match="deck needs ground 'terrain'"):
            load_city("hong_kong", cities_root=rewrite(to_datum))

    def test_deck_sampling_without_a_structure_class_is_rejected(self, rewrite) -> None:
        """The thresholds live under `roads:` and the geometry they apply to is
        named under `buildings:`, each following its own precedent. Nothing but
        this check stops a city declaring one half and not the other."""

        def drop_class(doc: dict[str, Any]) -> None:
            doc["buildings"].pop("structure_class")

        with pytest.raises(ValueError, match="structure_class names none"):
            load_city("hong_kong", cities_root=rewrite(drop_class))

    def test_an_empty_block_is_rejected_rather_than_read_as_absent(self, rewrite) -> None:
        """`deck:` with nothing under it parses as None, and would otherwise be
        indistinguishable from a city that never asked for deck sampling — the
        precise failure this class exists to refuse. Omitting the key is already
        how a city says that, so the empty spelling can only be a mistake."""

        def empty(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"] = None

        with pytest.raises(ValueError, match="deck is empty"):
            load_city("hong_kong", cities_root=rewrite(empty))

    def test_a_block_that_is_not_a_mapping_is_rejected(self, rewrite) -> None:
        def scalar(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"] = 5

        with pytest.raises(ValueError, match="must be a mapping"):
            load_city("hong_kong", cities_root=rewrite(scalar))

    @pytest.mark.parametrize("key", ["resample_m", "slab_gap_m", "max_below_terrain_m"])
    def test_a_non_finite_threshold_is_rejected(self, rewrite, key: str) -> None:
        """The one bad value that never announces itself. YAML 1.1 resolves
        `.nan`, it passes every sign check, and downstream it makes each
        comparison it feeds false without ever raising — so the edge falls back
        silently and the output looks like a city with no deck sampling."""

        def not_a_number(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"][key] = float("nan")

        with pytest.raises(ValueError, match=f"{key} must be a finite number"):
            load_city("hong_kong", cities_root=rewrite(not_a_number))

    def test_an_unbounded_slab_gap_is_rejected(self, rewrite) -> None:
        """`.inf` merges every stacked structure into one slab, and the measured
        margin here is only 0.79 m wide to begin with."""

        def unbounded(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"]["slab_gap_m"] = float("inf")

        with pytest.raises(ValueError, match="slab_gap_m must be a finite number"):
            load_city("hong_kong", cities_root=rewrite(unbounded))

    def test_a_threshold_that_is_not_a_number_names_where_it_came_from(self, rewrite) -> None:
        """`float()` on its own reports the bad value and not its key, which in a
        config of forty-odd numbers is most of the answer."""

        def text(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"]["resample_m"] = "ten"

        with pytest.raises(ValueError, match="deck:resample_m is 'ten'"):
            load_city("hong_kong", cities_root=rewrite(text))

    def test_a_key_the_block_does_not_use_is_rejected(self, rewrite) -> None:
        """Misspelling one of the four is already caught by its absence, but
        adding a fifth on top of them is not — it would parse, load, and tune
        nothing. Same trap `class_colours` refuses, on a closed key set."""

        def extra(doc: dict[str, Any]) -> None:
            doc["roads"]["deck"]["max_above_terrain_m"] = 99.0

        with pytest.raises(ValueError, match="does not use max_above_terrain_m"):
            load_city("hong_kong", cities_root=rewrite(extra))


class TestGroundProfile:
    """`Q24`'s config: how closely an at-grade road follows the ground.

    The guards are `deck:`'s, through the same helper, and that sharing is
    exactly what these pin down. A copied set of checks is a set that drifts,
    and the one that drifts is the one that quietly stops catching anything.
    """

    def test_it_loads(self, hong_kong) -> None:
        profile = hong_kong.roads.ground_profile
        assert profile is not None
        assert profile.resample_m > 0.0
        # Half the sink, so a station kept at this tolerance cannot poke through
        # the carriageway on its own.
        assert 0.0 < profile.tolerance_m <= hong_kong.buildings.ground_sink_m / 2.0

    def test_a_city_that_omits_it_samples_only_its_plan_vertices(self, rewrite) -> None:
        """Optional, like `deck:`. Omitting it is how a city asks for what
        shipped before there was drawn ground to disagree with."""

        def drop(doc: dict[str, Any]) -> None:
            del doc["roads"]["ground_profile"]

        assert load_city("hong_kong", cities_root=rewrite(drop)).roads.ground_profile is None

    def test_following_the_ground_without_terrain_ground_is_rejected(self, rewrite) -> None:
        """There is nothing to follow under `datum`, so the block could never
        run — and a silently inert block is the kind that survives review."""

        def to_datum(doc: dict[str, Any]) -> None:
            doc["roads"]["ground"] = "datum"
            del doc["roads"]["deck"]

        with pytest.raises(ValueError, match="ground_profile needs ground 'terrain'"):
            load_city("hong_kong", cities_root=rewrite(to_datum))

    def test_an_empty_block_is_rejected_rather_than_read_as_absent(self, rewrite) -> None:
        def empty(doc: dict[str, Any]) -> None:
            doc["roads"]["ground_profile"] = None

        with pytest.raises(ValueError, match="ground_profile is empty"):
            load_city("hong_kong", cities_root=rewrite(empty))

    def test_a_block_that_is_not_a_mapping_is_rejected(self, rewrite) -> None:
        def scalar(doc: dict[str, Any]) -> None:
            doc["roads"]["ground_profile"] = 10.0

        with pytest.raises(ValueError, match="ground_profile must be a mapping"):
            load_city("hong_kong", cities_root=rewrite(scalar))

    def test_a_key_the_block_does_not_use_is_rejected(self, rewrite) -> None:
        def extra(doc: dict[str, Any]) -> None:
            doc["roads"]["ground_profile"]["tolerance_mm"] = 100.0

        with pytest.raises(ValueError, match="does not use tolerance_mm"):
            load_city("hong_kong", cities_root=rewrite(extra))

    @pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
    def test_an_unusable_spacing_is_rejected(self, rewrite, value: float) -> None:
        """Zero asks `resample` for infinitely many stations, and `.nan` makes
        every comparison it feeds false without ever raising."""

        def spoil(doc: dict[str, Any]) -> None:
            doc["roads"]["ground_profile"]["resample_m"] = value

        with pytest.raises(ValueError, match="resample_m"):
            load_city("hong_kong", cities_root=rewrite(spoil))

    @pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
    def test_an_unusable_tolerance_is_rejected(self, rewrite, value: float) -> None:
        """Zero is allowed here and nowhere in this list: it keeps every station
        the resample inserted, which is the un-thinned behaviour the measured
        table compares against."""

        def spoil(doc: dict[str, Any]) -> None:
            doc["roads"]["ground_profile"]["tolerance_m"] = value

        with pytest.raises(ValueError, match="tolerance_m"):
            load_city("hong_kong", cities_root=rewrite(spoil))


class TestFares:
    """`P1-5`'s config, and the two ways its category table can be wrong."""

    def test_the_shipped_groups_cover_both_published_datasets(self, hong_kong) -> None:
        groups = {group.kind: group for group in hong_kong.fares.groups}

        assert set(groups) == {"taxi_stand", "pudo"}
        assert groups["taxi_stand"].source == "taxi_stands"
        assert groups["pudo"].source == "taxi_pudo"
        # The property names are the Transport Department's, and this is the
        # test that notices if a republish renames one.
        assert groups["taxi_stand"].field("name_zh") == "Location_TC"

    def test_every_published_category_spelling_is_matched(self, hong_kong) -> None:
        """The sixteen distinct `Status_EN` values in the territory, surveyed
        in docs/DATA_SOURCES.md. The region only ever exercises two of them, so
        without this the other fourteen are untested until a build fails."""
        stands = next(g for g in hong_kong.fares.groups if g.kind == "taxi_stand")
        expected = {
            "Urban Taxi Stand": "urban",
            "Both of Urban and NT Taxi Stand": "urban_and_nt",
            "NT Taxi Stand": "nt",
            "Cross Harbour Taxi Stand": "cross_harbour",
            "Lantau Taxi Stand": "lantau",
            "Cross Harbour Taxi Stand\n(2200-0700 daily)": "cross_harbour",
            "Cross Harbour Taxi Stand\n(0000-0500 on Sat & Sun)": "cross_harbour",
            "Urban Taxi Stand\n(0000-0500 on Sat & Sun)": "urban",
            "Urban Taxi Stand\n(0700-1000 daily)": "urban",
            "Urban Taxi Stand\n(0700-1900 daily)": "urban",
            "Cross Harbour Taxi Stand\n(1200-0600 daily)": "cross_harbour",
            "Urban Taxi Stand (0700-1000; 1600-1900 daily)": "urban",
            "Urban and Cross Harbour Taxi Stands": "cross_harbour",
            "Urban and NT Taxi Stand": "urban_and_nt",
            "NT Taxi Stand\n(2300-0630 daily)": "nt",
            "Urban Taxi Stand\n(2300-0630 daily)": "urban",
        }
        assert {text: stands.categorise(text).id for text in expected} == expected

    def test_a_drop_off_point_is_not_a_pick_up_point(self, hong_kong) -> None:
        points = next(g for g in hong_kong.fares.groups if g.kind == "pudo")

        assert (points.categorise("Taxi DF").pickup, points.categorise("Taxi DF").dropoff) == (
            False,
            True,
        )
        assert points.categorise("Taxi PU/DF").pickup

    def test_a_rule_an_earlier_one_shadows_is_rejected(self, rewrite) -> None:
        """Ordering is load-bearing and silent when wrong: `DF` before `PU/DF`
        files every pick-up point as drop-off only, and the output still looks
        complete."""

        def reverse(doc: dict[str, Any]) -> None:
            group = next(g for g in doc["fares"]["groups"] if g["kind"] == "pudo")
            group["categories"] = list(reversed(group["categories"]))

        with pytest.raises(ValueError, match="can therefore never be reached"):
            load_city("hong_kong", cities_root=rewrite(reverse))

    def test_an_unmatched_category_names_the_rules_it_tried(self, hong_kong) -> None:
        stands = next(g for g in hong_kong.fares.groups if g.kind == "taxi_stand")

        with pytest.raises(KeyError, match="Cross Harbour"):
            stands.categorise("Hovercraft Stand")

    def test_an_unknown_kind_is_rejected(self, rewrite) -> None:
        def mistype(doc: dict[str, Any]) -> None:
            doc["fares"]["groups"][0]["kind"] = "bus_stop"

        with pytest.raises(ValueError, match="expected one of taxi_stand, pudo, poi"):
            load_city("hong_kong", cities_root=rewrite(mistype))

    def test_a_source_the_city_does_not_publish_is_rejected(self, rewrite) -> None:
        def rename(doc: dict[str, Any]) -> None:
            doc["fares"]["groups"][0]["source"] = "not_fetched"

        with pytest.raises(ValueError, match="not in sources"):
            load_city("hong_kong", cities_root=rewrite(rename))

    def test_a_non_positive_snap_limit_is_rejected(self, rewrite) -> None:
        def zero(doc: dict[str, Any]) -> None:
            doc["fares"]["max_snap_m"] = 0.0

        with pytest.raises(ValueError, match="max_snap_m"):
            load_city("hong_kong", cities_root=rewrite(zero))

    def test_a_missing_fares_block_is_rejected(self, rewrite) -> None:
        with pytest.raises(ValueError, match="'fares'"):
            load_city("hong_kong", cities_root=rewrite(lambda doc: doc.pop("fares")))
