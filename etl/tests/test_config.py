"""City config loading tests.

These also serve as the check that `hong_kong.yaml` stays consistent with
docs/DATA_SOURCES.md — a config that parses but describes the wrong place is
the expensive failure here, not a syntax error.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from pipeline.config import CITIES_ROOT, SUPPORTED_SCHEMA, SurfaceClass, load_city


@pytest.fixture
def rewrite(tmp_path: Path):
    """Load the real config, mutate it, and write it somewhere disposable.

    Mutating the real file beats a hand-written fixture: a stub would drift out
    of step with the schema and keep passing while the real config broke.

    The certs directory is mirrored beside the relocated yaml because the real
    config spans both: `extra_cas` paths resolve against the yaml's own
    directory, and a relocation that dropped them would fail the load for
    every test here, whatever it was actually testing.
    """

    def _rewrite(mutate) -> Path:
        document = yaml.safe_load((CITIES_ROOT / "hong_kong.yaml").read_text(encoding="utf-8"))
        mutate(document)
        cities = tmp_path / "cities"
        cities.mkdir(exist_ok=True)
        (cities / "hong_kong.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
        certs = CITIES_ROOT.parent / "certs"
        if certs.is_dir():
            shutil.copytree(certs, tmp_path / "certs", dirs_exist_ok=True)
        return cities

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

    def test_surface_class_reads_the_palette_rather_than_a_new_key(self, hong_kong) -> None:
        """`P3-7`'s per-vertex marker is derived, not configured — hard rule 3.
        The distinction the shader needs is one the palette has always drawn: a
        class with a flat `class_materials` entry is a thing whose colour does not
        depend on how tall it is, which is exactly the set with no floors to
        band. A second city gets the right answer from its own palette."""
        style = hong_kong.buildings

        assert style.surface_class("BUILDING") == SurfaceClass.FACADE
        assert style.surface_class(style.terrain_class) == SurfaceClass.GROUND
        assert style.surface_class(style.structure_class) == SurfaceClass.STRUCTURE

    def test_an_unknown_class_bands_like_a_building(self, hong_kong) -> None:
        """`FACADE` is the fallback rather than a listed case, and that is the
        safe direction: a new massing class reads as a building until someone
        gives it a flat colour, and one that must not be banded announces itself
        by needing a colour that height cannot supply."""
        assert hong_kong.buildings.surface_class("VEGETATION") == SurfaceClass.FACADE

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
            doc["buildings"]["material_assignment"]["unsurveyed"]["by_height"].reverse()

        with pytest.raises(ValueError, match="ascending"):
            load_city("hong_kong", cities_root=rewrite(shuffle))

    def test_a_closed_last_band_is_rejected(self, rewrite) -> None:
        """Without an open-ended band there is no colour for a building taller
        than the table — and those are what a Hong Kong skyline is read by."""

        def close_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["material_assignment"]["unsurveyed"]["by_height"][-1]["up_to_m"] = (
                500.0
            )

        with pytest.raises(ValueError, match=r"\.inf"):
            load_city("hong_kong", cities_root=rewrite(close_it))

    def test_a_malformed_colour_is_rejected(self, rewrite) -> None:
        def break_colour(doc: dict[str, Any]) -> None:
            doc["materials"]["render_warm"]["colour"] = "beige"

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
        """The same trap as `class_materials`: a misspelling parses, loads, and
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
        """The same trap as `class_materials` and `class_lod_cell_sizes_m`: a
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

    @pytest.mark.parametrize("value", [-0.1, 99.0, float("nan"), float("inf")])
    def test_facade_hue_strength_outside_its_bound_is_rejected(self, rewrite, value) -> None:
        """⚠️ The ceiling exists to make this test two-sided, and that is the
        whole point of it. A one-sided `< 0.0` guard admits `.nan` and `.inf`,
        and a NaN strength reaches `np.clip(np.round(nan)).astype(np.uint8)`,
        which miscolours every surveyed building without raising anything."""

        def overdo_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["facade_hue"]["strength"] = value

        with pytest.raises(ValueError, match=r"facade_hue\.strength"):
            load_city("hong_kong", cities_root=rewrite(overdo_it))

    @pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
    def test_facade_hue_vegetation_max_outside_its_bound_is_rejected(self, rewrite, value) -> None:
        """A fraction, so the ceiling is 1.0 rather than a taste limit — and it
        is two-sided for the same NaN reason as `strength` above."""

        def overdo_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["facade_hue"]["vegetation_max"] = value

        with pytest.raises(ValueError, match=r"facade_hue\.vegetation_max"):
            load_city("hong_kong", cities_root=rewrite(overdo_it))

    def test_facade_hue_needs_a_source(self, rewrite) -> None:
        """`strength` alone colours nothing, so the pair is refused rather than
        silently ignored."""

        def drop_source(doc: dict[str, Any]) -> None:
            del doc["buildings"]["facade_hue"]["source"]

        with pytest.raises(ValueError, match="source"):
            load_city("hong_kong", cities_root=rewrite(drop_source))

    def test_facade_survey_block_is_optional_and_each_key_stands_alone(self, rewrite) -> None:
        """Same defaulted-is-the-contract rule as `facade_hue`: both tables are
        gitignored derived data, so a clone without the block — or with half of
        it — must still build, on the refusal sentinel."""
        surveyed = load_city("hong_kong").buildings
        assert surveyed.facade_glazing_source == "facade_glazing.json"
        assert surveyed.facade_grammar_source == "facade_grammar.json"

        def drop_block(doc: dict[str, Any]) -> None:
            del doc["buildings"]["facade_survey"]

        stripped = load_city("hong_kong", cities_root=rewrite(drop_block)).buildings
        assert stripped.facade_glazing_source is None
        assert stripped.facade_grammar_source is None

        def drop_grammar(doc: dict[str, Any]) -> None:
            del doc["buildings"]["facade_survey"]["grammar"]

        partial = load_city("hong_kong", cities_root=rewrite(drop_grammar)).buildings
        assert partial.facade_glazing_source == "facade_glazing.json"
        assert partial.facade_grammar_source is None

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
            for table in ("class_materials", "class_colour_jitter", "class_lod_cell_sizes_m"):
                doc["buildings"][table].pop(terrain, None)
            # ⚠️ The extra line *is* `_check_every_material_is_used` working. The
            # ground was the only thing referencing `concrete_paving`, so dropping
            # class strands the material — and a stranded material is a colour
            # still being exposure-checked as though it ships.
            doc["materials"].pop("concrete_paving")

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
        assert style.colour_for("BUILDING", 5.0) == style.height_bands[0].material.colour
        assert style.colour_for("BUILDING", 1_000.0) == style.height_bands[-1].material.colour

    def test_a_class_material_wins_over_the_bands(self, hong_kong) -> None:
        style = hong_kong.buildings
        flat = style.class_materials["INFRASTRUCTURE"]
        assert style.material_for("INFRASTRUCTURE", 5.0) is flat
        assert style.material_for("INFRASTRUCTURE", 200.0) is flat
        assert style.colour_for("INFRASTRUCTURE", 200.0) == flat.colour


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
        nothing. Same trap `class_materials` refuses, on a closed key set."""

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


class TestMaterialAssignment:
    """`Q34`'s `surveyed:` block — the rings and sectors, and their totality.

    The shape is chosen so it cannot fail to cover a building: rings reuse the
    height ramp's ascending-and-`.inf` rule, sectors partition the circle. These
    are the tests that the loader actually refuses the ways it could stop being
    total, because a gap would show as a crash mid-build, after the expensive
    source read.
    """

    def test_it_loads(self, hong_kong) -> None:
        rings = hong_kong.buildings.material_assignment.rings
        assert rings
        assert rings[-1].up_to_chroma == float("inf")

    def test_the_surveyed_block_is_optional(self, rewrite) -> None:
        """⚠️ The contract. A clone without the 4.9 GB survey must still build,
        and it builds the city the height ramp describes."""

        def drop(doc: dict[str, Any]) -> None:
            del doc["buildings"]["material_assignment"]["surveyed"]

        city = load_city("hong_kong", cities_root=rewrite(drop))
        assert city.buildings.material_assignment.rings == ()
        # Nothing else had to move, and that is worth asserting rather than
        # assuming: every material the draw names is also named by the ramp, so
        # deleting the draw strands none of them. An earlier version of this test
        # appended two junk bands to keep them referenced, on a guess that was
        # simply wrong — and the junk bands silently repainted every tower.
        assert set(city.materials) == set(load_city("hong_kong").materials)

    def test_unordered_rings_are_rejected(self, rewrite) -> None:
        def invert(doc: dict[str, Any]) -> None:
            doc["buildings"]["material_assignment"]["surveyed"]["rings"].reverse()

        with pytest.raises(ValueError, match="ascending up_to_chroma"):
            load_city("hong_kong", cities_root=rewrite(invert))

    def test_a_closed_last_ring_is_rejected(self, rewrite) -> None:
        """Chroma has no ceiling, so a bounded last ring leaves the most
        colourful buildings in the region with no rule at all."""

        def close_it(doc: dict[str, Any]) -> None:
            doc["buildings"]["material_assignment"]["surveyed"]["rings"][-1]["up_to_chroma"] = 40.0

        with pytest.raises(ValueError, match=r"\.inf"):
            load_city("hong_kong", cities_root=rewrite(close_it))

    def test_a_ring_with_both_weights_and_sectors_is_rejected(self, rewrite) -> None:
        """Either would be silently dead. Refused rather than resolved by
        precedence, which would make which one wins a thing to remember."""

        def both(doc: dict[str, Any]) -> None:
            ring = doc["buildings"]["material_assignment"]["surveyed"]["rings"][-1]
            ring["weights"] = {"panel_grey": 1.0}

        with pytest.raises(ValueError, match="exactly one of"):
            load_city("hong_kong", cities_root=rewrite(both))

    def test_a_ring_with_neither_is_rejected(self, rewrite) -> None:
        def neither(doc: dict[str, Any]) -> None:
            del doc["buildings"]["material_assignment"]["surveyed"]["rings"][0]["weights"]

        with pytest.raises(ValueError, match="exactly one of"):
            load_city("hong_kong", cities_root=rewrite(neither))

    def test_unordered_sectors_are_rejected(self, rewrite) -> None:
        """The wrap only covers the circle if the boundaries ascend."""

        def invert(doc: dict[str, Any]) -> None:
            doc["buildings"]["material_assignment"]["surveyed"]["rings"][-1]["sectors"].reverse()

        with pytest.raises(ValueError, match="ascending from_deg"):
            load_city("hong_kong", cities_root=rewrite(invert))

    @pytest.mark.parametrize(("index", "angle"), [(0, -10.0), (-1, 360.0), (-1, 400.0)])
    def test_a_sector_boundary_off_the_circle_is_rejected(self, rewrite, index, angle) -> None:
        """Moved at the end that keeps the list ascending, so this reaches the
        range check rather than tripping the ordering one on the way."""

        def move(doc: dict[str, Any]) -> None:
            doc["buildings"]["material_assignment"]["surveyed"]["rings"][-1]["sectors"][index][
                "from_deg"
            ] = angle

        with pytest.raises(ValueError, match=r"\[0, 360\)"):
            load_city("hong_kong", cities_root=rewrite(move))

    def test_every_bin_expects_the_reflectance_the_ramp_already_gave_it(self, hong_kong) -> None:
        """⚠️ **The mitigation that makes this change gradeable**, asserted so it
        cannot quietly stop being true.

        The draw is meant to change *which* material a building gets, not how
        light the city is — otherwise a before/after frame shows a level change
        and the hue structure it was built for is unreadable underneath. Every
        bin's weights are authored so its expected reflectance matches what the
        height ramp handed that same population, which is possible only because
        height and hue are near-independent — the finding behind `Q34`.

        ⚠️ **What this actually compares is the bin against the ramp's *unweighted*
        band mean, not against the population it was authored from.** The real
        property — each bin matching the mean reflectance the ramp handed the
        buildings that fall in it — needs the 2,171-row survey, which is a 4.9 GB
        gitignored read this suite must run without. So the bound is loose on
        purpose and means less than the paragraph above: it catches a bin
        re-weighted toward one end of the palette, and nothing finer. **Do not
        tighten it expecting it to mean more** — re-derive against the survey
        instead, the way the shipped weights were.
        """
        ramp = hong_kong.buildings.material_assignment.by_height
        ramp_mean = sum(band.material.reflectance for band in ramp) / len(ramp)

        for ring in hong_kong.buildings.material_assignment.rings:
            draws = [ring.draw] if ring.draw is not None else [s.draw for s in ring.sectors]
            for draw in draws:
                lower = 0.0
                expected = 0.0
                for material, bound in zip(draw.materials, draw.bounds, strict=True):
                    expected += material.reflectance * (bound - lower)
                    lower = bound
                assert expected == pytest.approx(ramp_mean, abs=3.0)


class TestPaletteExposure:
    """`Q33` — every colour is `reflectance x exposure_anchor`, checked at load.

    ⚠️ **What guarantees the rule changed with `Q34`, and these tests changed
    with it.** The rule used to earn its keep by being *cross-section*: the
    colours lived in two unrelated dataclasses and `235aa4f` re-exposed one and
    not the other, so the tests that mattered reproduced that — a change applied
    to `buildings:` while `roads:` was not in the diff.

    There is now one section. `_check_exposure` is total because the **table**
    is, which is stronger, and which moves the load-bearing test to
    `test_no_colour_escapes_the_materials_table` below: that is what now holds
    the property this class used to hold.
    """

    def test_the_pre_rule_kerb_is_now_rejected(self, rewrite) -> None:
        """The exact colour that drifted, against the material it claims.

        `#9a968d` is weathered concrete asserting 58.9% albedo. Before the rule
        this loaded, built and shipped.
        """

        def restore(doc: dict[str, Any]) -> None:
            doc["materials"]["concrete_kerb"]["colour"] = "#9a968d"

        with pytest.raises(ValueError, match=r"materials\.concrete_kerb"):
            load_city("hong_kong", cities_root=rewrite(restore))

    def test_re_exposing_only_some_materials_is_rejected(self, rewrite) -> None:
        """`235aa4f` in the only miniature still available, which is the point.

        Re-exposing the city means moving the anchor and moving every colour with
        it. That commit did the first half and only part of the second, because
        `roads:` was not in the diff. The *sections* it could be split between
        are gone, so this splits the table instead — anchor moved, facades
        rescaled, the two road materials left behind — and it is still caught.

        ⚠️ The salvage is imperfect and worth naming: a partial edit to one table
        is a more obviously wrong thing to write than an edit that simply stops
        at a section boundary. The structural defence is that there is now one
        place to change, not that this test is hard to pass.
        """

        def re_expose(doc: dict[str, Any]) -> None:
            doc["exposure_anchor"] = 0.40
            for name, entry in doc["materials"].items():
                if name not in ("asphalt_aged", "concrete_kerb"):
                    entry["reflectance"] = entry["reflectance"] * 0.520 / 0.40

        with pytest.raises(ValueError, match=r"materials\.(asphalt_aged|concrete_kerb)"):
            load_city("hong_kong", cities_root=rewrite(re_expose))

    def test_a_reference_to_an_undeclared_material_is_rejected(self, rewrite) -> None:
        """The forward direction of the join. A name with no entry would
        otherwise be a colour that does not exist, discovered at use."""

        def dangle(doc: dict[str, Any]) -> None:
            doc["buildings"]["material_assignment"]["unsurveyed"]["by_height"][0]["material"] = (
                "renderr_warm"
            )

        with pytest.raises(ValueError, match="which materials: does not declare"):
            load_city("hong_kong", cities_root=rewrite(dangle))

    def test_a_material_nothing_references_is_rejected(self, rewrite) -> None:
        """The reverse direction, inherited from the `class_reflectance` stray
        check this replaces.

        An entry that colours nothing parses, loads and is silently inert — and
        worse than merely inert, because `_check_exposure` reads the whole table:
        it would be a colour validated as though it ships.
        """

        def stray(doc: dict[str, Any]) -> None:
            doc["materials"]["roof_felt"] = {
                "colour": "#3a3a38",
                "reflectance": 8.0,
                "source": "test",
            }

        with pytest.raises(ValueError, match="roof_felt, which nothing references"):
            load_city("hong_kong", cities_root=rewrite(stray))

    def test_a_material_without_a_source_is_rejected(self, rewrite) -> None:
        """Unvalidated but required. The point is that somebody had to type an
        answer — an unsourced albedo is how the palette drifted before `Q33`."""

        def drop(doc: dict[str, Any]) -> None:
            del doc["materials"]["concrete_paving"]["source"]

        with pytest.raises(ValueError, match="source"):
            load_city("hong_kong", cities_root=rewrite(drop))

    def test_a_zero_anchor_is_rejected(self, rewrite) -> None:
        """Zero would make every colour black and pass the check for any material.

        The trap worth a test: it turns the rule into a no-op that still reads as
        enforced, which is worse than not having it.
        """

        def zero(doc: dict[str, Any]) -> None:
            doc["exposure_anchor"] = 0.0

        with pytest.raises(ValueError, match=r"must be in \(0, 2\.0\]"):
            load_city("hong_kong", cities_root=rewrite(zero))

    @pytest.mark.parametrize("value", [0.0, -1.0, 101.0])
    def test_an_impossible_reflectance_is_rejected(self, rewrite, value) -> None:
        def spoil(doc: dict[str, Any]) -> None:
            doc["materials"]["asphalt_aged"]["reflectance"] = value

        with pytest.raises(ValueError, match="reflectance"):
            load_city("hong_kong", cities_root=rewrite(spoil))

    def test_no_colour_escapes_the_materials_table(self) -> None:
        """⚠️ **The check `_check_exposure` now depends on and cannot make.**

        This is what carries `235aa4f`'s lesson. That commit re-exposed the
        colours in `buildings:` and missed the two in `roads:` — not by argument,
        but because `roads:` was not in the diff. `Q33` answered it with a
        cross-section loop; `Q34` answered it structurally, by leaving exactly one
        place a colour may be written. The loop is now total *because the table
        is*, which is a stronger guarantee resting on a weaker foundation: it
        holds only while nothing authors a colour anywhere else.

        Nothing in `config.py` can enforce that — a second `_parse_hex` call on a
        new key would be perfectly well-formed. So it is asserted here, against
        the shipped document, on the shape of the value rather than on any list of
        known keys. A new palette key added outside `materials:` fails this test
        the day it is written.
        """
        document = yaml.safe_load((CITIES_ROOT / "hong_kong.yaml").read_text(encoding="utf-8"))
        declared = {entry["colour"] for entry in document["materials"].values()}

        def hex_colours(node: Any, path: str):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield from hex_colours(value, f"{path}.{key}")
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    yield from hex_colours(value, f"{path}[{index}]")
            elif isinstance(node, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", node):
                yield path, node

        outside = {
            path: value
            for path, value in hex_colours(document, "")
            if not path.startswith(".materials.")
        }
        assert not outside, (
            f"colour(s) authored outside materials: {outside}. Every colour the city "
            "ships is declared in materials: — see _check_exposure."
        )
        # And the table is not merely where they are written, but where they all
        # are: nine distinct colours, none of them repeated under two names.
        assert len(declared) == len(document["materials"])


class TestPodiums:
    """The `podiums:` block — Q47's building-block layer, and its `tile_suffix`."""

    def test_the_real_config_declares_the_block_layer(self, hong_kong) -> None:
        assert hong_kong.podiums is not None
        assert hong_kong.podiums.source in hong_kong.tiled_sources
        blocks = hong_kong.podiums.blocks
        assert blocks.field("base_level") in blocks.columns

    def test_the_block_is_optional(self, rewrite) -> None:
        """A city without a topographic source builds as before — the same
        defaulted-is-the-contract rule as the survey tables."""
        city = load_city("hong_kong", cities_root=rewrite(lambda doc: doc.pop("podiums")))
        assert city.podiums is None

    def test_a_source_that_is_not_tiled_is_rejected(self, rewrite) -> None:
        """The block reads per-sheet zips, so a fixed-URL source cannot serve
        it — naming one is a config error, caught at load."""

        def rename(doc: dict[str, Any]) -> None:
            doc["podiums"]["source"] = "road_network_gdb"

        with pytest.raises(ValueError, match="not in tiled_sources"):
            load_city("hong_kong", cities_root=rewrite(rename))

    @pytest.mark.parametrize("member", ["{sheet}/{sheet}.gdb", "{tile/{tile}.gdb"])
    def test_a_member_with_a_bad_placeholder_is_rejected(self, rewrite, member: str) -> None:
        """A `{sheet}` typo or an unclosed brace would otherwise fail at first
        read, per sheet, rather than once at load."""

        def mistype(doc: dict[str, Any]) -> None:
            doc["podiums"]["member"] = member

        with pytest.raises(ValueError, match="placeholder"):
            load_city("hong_kong", cities_root=rewrite(mistype))

    def test_a_missing_role_is_rejected(self, rewrite) -> None:
        def drop(doc: dict[str, Any]) -> None:
            del doc["podiums"]["blocks"]["fields"]["roof_level"]

        with pytest.raises(ValueError, match="roof_level"):
            load_city("hong_kong", cities_root=rewrite(drop))

    def test_a_missing_code_role_is_rejected(self, rewrite) -> None:
        """The join asks for the tower and podium domain values by role, so a
        config that names only one fails at load, not at first join."""

        def drop(doc: dict[str, Any]) -> None:
            del doc["podiums"]["codes"]["podium"]

        with pytest.raises(ValueError, match="codes is missing podium"):
            load_city("hong_kong", cities_root=rewrite(drop))

    def test_the_real_config_maps_both_code_roles(self, hong_kong) -> None:
        assert hong_kong.podiums.code("tower") != hong_kong.podiums.code("podium")


class TestLandmarks:
    """The `landmarks:` block — P3-6's hero placements.

    Stem *format* is deliberately not validated (an id's shape is a publisher's
    spelling, hard rule 3); a typo'd stem is `export.validate`'s catch. What
    load does refuse is everything that is wrong before any data is read.
    """

    def test_the_real_config_places_the_first_two_heroes(self, hong_kong) -> None:
        by_id = {landmark.id: landmark for landmark in hong_kong.landmarks}
        assert set(by_id) >= {"hkcec", "central_plaza"}
        for landmark in by_id.values():
            assert landmark.replaces_source_ids, landmark.id

        # Central Plaza stays an authored, committed model.
        assert by_id["central_plaza"].asset.startswith("res://assets/authored/landmarks/")
        assert by_id["central_plaza"].source_paint is None

        # HKCEC is mesh-sourced (`P3-6` amendment): its model is generated
        # output, keeps the source orientation, and carries its own budget.
        hkcec = by_id["hkcec"]
        assert hkcec.asset == "res://assets/generated/landmarks/hkcec.glb"
        assert hkcec.rot_y_deg == 0.0
        assert hkcec.triangle_budget > 8000
        paint = hkcec.source_paint
        assert paint is not None
        assert {m.name for m in (paint.wall, paint.ribbon, paint.roof, paint.base)} == {
            "panel_pale",
            "curtain_glass",
            "roof_grey",
            "concrete_pale",
        }
        assert paint.ribbon_count == 10

    def test_the_block_is_optional(self, rewrite) -> None:
        def drop(doc: dict[str, Any]) -> None:
            doc.pop("landmarks")
            # The paint surfaces' only referent is the block being dropped, and
            # a material nothing references is refused — that refusal has its
            # own test; this one is about the landmarks block.
            for name in ("panel_pale", "roof_grey", "curtain_glass", "concrete_pale"):
                del doc["materials"][name]

        city = load_city("hong_kong", cities_root=rewrite(drop))
        assert city.landmarks == ()

    def test_a_reused_id_is_rejected(self, rewrite) -> None:
        def duplicate(doc: dict[str, Any]) -> None:
            doc["landmarks"].append(dict(doc["landmarks"][0]))

        with pytest.raises(ValueError, match="reuses id"):
            load_city("hong_kong", cities_root=rewrite(duplicate))

    def test_a_stem_claimed_twice_is_rejected(self, rewrite) -> None:
        """Two heroes over one building would fail export's set-equality check
        with a report pointing regions away from the config mistake."""

        def share(doc: dict[str, Any]) -> None:
            doc["landmarks"][1]["replaces_source_ids"] = list(
                doc["landmarks"][0]["replaces_source_ids"]
            )

        with pytest.raises(ValueError, match="already claimed"):
            load_city("hong_kong", cities_root=rewrite(share))

    def test_an_empty_replacement_list_is_rejected(self, rewrite) -> None:
        """A hero replacing nothing lands inside the source building it was
        meant to replace — the z-fighting the field exists to prevent."""

        def strip(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["replaces_source_ids"] = []

        with pytest.raises(ValueError, match="non-empty"):
            load_city("hong_kong", cities_root=rewrite(strip))

    def test_an_authored_asset_outside_the_authored_directory_is_rejected(self, rewrite) -> None:
        def relocate(doc: dict[str, Any]) -> None:
            # [1] is Central Plaza — the authored mode; [0] is mesh-sourced.
            doc["landmarks"][1]["asset"] = "res://assets/generated/central_plaza.glb"

        with pytest.raises(ValueError, match="authored/landmarks"):
            load_city("hong_kong", cities_root=rewrite(relocate))

    def test_a_mesh_sourced_asset_must_be_its_derived_path(self, rewrite) -> None:
        """The stage writes `landmarks/<id>.glb`; any other asset spelling
        would ship a model the manifest points past."""

        def relocate(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["asset"] = "res://assets/authored/landmarks/hkcec.glb"

        with pytest.raises(ValueError, match="repainted source mesh"):
            load_city("hong_kong", cities_root=rewrite(relocate))

    def test_a_mesh_sourced_bearing_is_rejected(self, rewrite) -> None:
        """The extracted mesh keeps its source orientation — a bearing on top
        would rotate it twice."""

        def rotate(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["rot_y_deg"] = 6.4

        with pytest.raises(ValueError, match="source orientation"):
            load_city("hong_kong", cities_root=rewrite(rotate))

    def test_a_paint_material_missing_from_the_table_is_rejected(self, rewrite) -> None:
        """Paint surfaces resolve through the materials table — the invariant
        that no colour is authored anywhere else in the file."""

        def mistype(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["source_paint"]["materials"]["roof"] = "roof_gray"

        with pytest.raises(ValueError, match="materials: does not declare"):
            load_city("hong_kong", cities_root=rewrite(mistype))

    def test_a_non_positive_triangle_budget_is_rejected(self, rewrite) -> None:
        def zero(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["triangle_budget"] = 0

        with pytest.raises(ValueError, match="positive integer"):
            load_city("hong_kong", cities_root=rewrite(zero))

    def test_an_out_of_range_normal_threshold_is_rejected(self, rewrite) -> None:
        """Above 1 nothing ever matches and the whole mesh silently paints as
        wall — the quiet failure, refused loudly at load."""

        def overshoot(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["source_paint"]["roof_normal_y"] = 1.5

        with pytest.raises(ValueError, match="within"):
            load_city("hong_kong", cities_root=rewrite(overshoot))

    def test_an_out_of_range_crease_is_rejected(self, rewrite) -> None:
        """At 180 growth crosses every edge and the first seed's surface
        floods the whole mesh."""

        def flood(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["source_paint"]["crease_deg"] = 180.0

        with pytest.raises(ValueError, match="crease_deg"):
            load_city("hong_kong", cities_root=rewrite(flood))

    def test_a_non_boolean_reference_flag_is_rejected(self, rewrite) -> None:
        def mistype(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["source_paint"]["reference_texture"] = "yes"

        with pytest.raises(ValueError, match="reference_texture"):
            load_city("hong_kong", cities_root=rewrite(mistype))

    def test_the_real_config_references_the_photo(self, hong_kong) -> None:
        paint = {landmark.id: landmark for landmark in hong_kong.landmarks}["hkcec"].source_paint
        assert paint.reference_texture is True
        assert 0.0 < paint.veto_ratio <= 1.0
        assert 0.0 < paint.crease_deg < 180.0

    def test_a_position_inside_no_region_is_rejected(self, rewrite) -> None:
        """Excluded wherever its sheets are read, shipped nowhere — a hole with
        no hero over it, refused at load rather than found in a build."""

        def strand(doc: dict[str, Any]) -> None:
            doc["landmarks"][0]["pos"]["easting"] = 800000.0

        with pytest.raises(ValueError, match="inside no declared region"):
            load_city("hong_kong", cities_root=rewrite(strand))

    def test_a_missing_display_name_is_rejected(self, rewrite) -> None:
        def drop(doc: dict[str, Any]) -> None:
            del doc["landmarks"][0]["name"]["zh"]

        with pytest.raises(ValueError, match="zh"):
            load_city("hong_kong", cities_root=rewrite(drop))

    def test_the_tile_suffix_is_parsed_onto_the_source(self, hong_kong) -> None:
        assert hong_kong.tiled_sources["topography"].tile_suffix == ".zip"
        assert hong_kong.tiled_sources["buildings"].tile_suffix is None

    def test_a_tile_suffix_without_a_dot_is_rejected(self, rewrite) -> None:
        def mistype(doc: dict[str, Any]) -> None:
            doc["tiled_sources"]["topography"]["tile_suffix"] = "zip"

        with pytest.raises(ValueError, match="tile_suffix"):
            load_city("hong_kong", cities_root=rewrite(mistype))


class TestExtraCas:
    """`extra_cas:` — committed intermediates that complete a publisher's chain."""

    def test_paths_resolve_against_the_config_directory_and_exist(self, hong_kong) -> None:
        assert hong_kong.extra_cas
        for certificate in hong_kong.extra_cas:
            assert certificate.is_absolute()
            assert certificate.is_file()

    def test_the_key_is_optional(self, rewrite) -> None:
        city = load_city("hong_kong", cities_root=rewrite(lambda doc: doc.pop("extra_cas")))
        assert city.extra_cas == ()

    def test_a_missing_certificate_is_rejected_at_load(self, rewrite) -> None:
        """Silently falling back to the default store would re-surface the
        publisher's broken chain as a mid-run download failure instead."""

        def mistype(doc: dict[str, Any]) -> None:
            doc["extra_cas"] = ["../certs/nonexistent.pem"]

        with pytest.raises(ValueError, match="does not exist"):
            load_city("hong_kong", cities_root=rewrite(mistype))


class TestKerbsideRestrictions:
    """The `NSR` block (`P3-13`). Every guard here refuses a config that loads —
    a block that paints nothing, or a kind the surface stage has no case for,
    would otherwise surface as a quiet absence of yellow lines."""

    def test_hong_kong_declares_one(self, hong_kong) -> None:
        kerbside = hong_kong.roads.kerbside
        assert kerbside is not None
        # "All motor vehicles" and "Others" are painted lines (`Q56` measured
        # 93.9% of the latter carrying one in the drawings). The class-specific
        # codes stay out — not because they are signs, which the drawings
        # disproved, but because this codec cannot say *which* class.
        assert kerbside.painted_vehicle_types == frozenset({1, 5})
        assert not kerbside.painted_vehicle_types & {2, 3, 4}
        # 24 hours is a double yellow; every posted-hours code is a single.
        assert kerbside.kind_for(1) == "double"
        assert {kerbside.kind_for(code) for code in (2, 3, 4, 5)} == {"single"}

    def test_the_block_is_optional(self, rewrite) -> None:
        """A city whose sources carry no such layer draws no kerbside line,
        which is the honest answer rather than the invented one."""
        city = load_city(
            "hong_kong", cities_root=rewrite(lambda doc: doc["roads"].pop("kerbside_restrictions"))
        )
        assert city.roads.kerbside is None

    def test_an_unmapped_time_zone_raises_rather_than_defaulting(self, hong_kong) -> None:
        """These datasets are republished twice a year. A new code filed under a
        fallback would paint the wrong line everywhere it appeared."""
        with pytest.raises(KeyError, match="does not map to a kind"):
            hong_kong.roads.kerbside.kind_for(9)

    def test_an_empty_vehicle_type_list_is_rejected(self, rewrite) -> None:
        def empty(doc: dict[str, Any]) -> None:
            doc["roads"]["kerbside_restrictions"]["painted_vehicle_types"] = []

        with pytest.raises(ValueError, match="would paint nothing"):
            load_city("hong_kong", cities_root=rewrite(empty))

    def test_a_kind_outside_the_vocabulary_is_rejected(self, rewrite) -> None:
        def invent(doc: dict[str, Any]) -> None:
            doc["roads"]["kerbside_restrictions"]["kinds"][1] = "triple"

        with pytest.raises(ValueError, match="expected one of"):
            load_city("hong_kong", cities_root=rewrite(invent))

    def test_a_minimum_run_below_the_sampling_pitch_is_rejected(self, rewrite) -> None:
        """It could reject nothing: the shortest run the sampler can produce is
        one cell, so a minimum under that is a dial connected to nothing."""

        def blunt(doc: dict[str, Any]) -> None:
            doc["roads"]["kerbside_restrictions"]["min_run_m"] = 0.5

        with pytest.raises(ValueError, match="would reject nothing"):
            load_city("hong_kong", cities_root=rewrite(blunt))


class TestKerbsideAudit:
    """The second-source block (`Q56`). Nothing in `pipeline/` reads it, and it
    is checked at load anyway — the alternative is a grader that dies on a typo
    after reading a 218 MB geodatabase."""

    def test_hong_kong_declares_one(self, hong_kong) -> None:
        audit = hong_kong.roads.kerbside.audit
        assert audit is not None
        assert audit.layer.layer == "DTAD_RST_ZONE_LINE"
        assert audit.layer.field("line_type") == "LINETYPE"
        # The Transport Department's own marking codes, from the index plan in
        # the drawings' dataspec: RM1040 is "no stopping at any time" drawn as
        # two continuous lines, RM1041 "no stopping part time" as one.
        assert audit.kinds == {"RM1040": "double", "RM1041": "single"}

    def test_it_names_a_source_that_exists(self, hong_kong) -> None:
        """A typo here would surface as a missing file after a build's work."""
        assert hong_kong.roads.kerbside.audit.source in hong_kong.sources

    def test_an_unfetchable_source_is_rejected(self, rewrite) -> None:
        def rename(doc: dict[str, Any]) -> None:
            doc["roads"]["kerbside_restrictions"]["audit"]["source"] = "no_such_source"

        with pytest.raises(ValueError, match="which is not in sources"):
            load_city("hong_kong", cities_root=rewrite(rename))

    def test_the_block_is_optional(self, rewrite) -> None:
        """A city with one source and no way to check it says so by leaving the
        block out, rather than by an audit that grades a source against itself."""
        city = load_city(
            "hong_kong",
            cities_root=rewrite(lambda doc: doc["roads"]["kerbside_restrictions"].pop("audit")),
        )
        assert city.roads.kerbside is not None
        assert city.roads.kerbside.audit is None

    def test_a_kind_outside_the_vocabulary_is_rejected(self, rewrite) -> None:
        """The audit reaches a kind by its own route, so its vocabulary has to be
        checked on its own rather than inherited from the block it grades."""

        def invent(doc: dict[str, Any]) -> None:
            doc["roads"]["kerbside_restrictions"]["audit"]["kinds"]["RM1040"] = "triple"

        with pytest.raises(ValueError, match="expected one of"):
            load_city("hong_kong", cities_root=rewrite(invent))

    def test_an_empty_kind_table_is_rejected(self, rewrite) -> None:
        """It would map every marking code to nothing, grade the whole region as
        unmapped, and report the two sources in perfect disagreement."""

        def empty(doc: dict[str, Any]) -> None:
            doc["roads"]["kerbside_restrictions"]["audit"]["kinds"] = {}

        with pytest.raises(ValueError, match="grade every metre unknown"):
            load_city("hong_kong", cities_root=rewrite(empty))


class TestCarriagewaySurvey:
    """The published-carriageway-edge block (`Q57`). Nothing in `pipeline/` reads it, and it is
    validated at load anyway — the alternative is an instrument that dies on a
    typo after reading a 218 MB geodatabase and six map sheets."""

    def test_hong_kong_declares_both_publishers(self, hong_kong) -> None:
        survey = hong_kong.carriageway_survey
        assert survey is not None
        assert [edge.name for edge in survey.edges] == ["traffic_aids", "ib1000"]

    def test_the_drawings_lead_because_they_draw_the_carriageway(self, hong_kong) -> None:
        """Order is preference. TD paints the edge of the carriageway; iB1000's
        margin is a topographic line that may follow a kerb, a wall or a lot
        boundary, and is the fallback for its density rather than its meaning."""
        first = hong_kong.carriageway_survey.edges[0]

        assert first.layer.layer == "DTAD_RD_MARK_LINE"
        assert first.codes == ("RM1108", "RM1109")
        assert not first.tiled

    def test_the_topographic_source_is_read_per_sheet(self, hong_kong) -> None:
        second = hong_kong.carriageway_survey.edges[1]

        assert second.tiled
        assert second.member == "{tile}/{tile}.gdb"
        assert second.codes == ("RM",)

    def test_off_grade_is_stated_as_an_exclusion(self, hong_kong) -> None:
        """⚠️ The regression this pins. At-grade is the *unmarked* case in both
        files — a null relative level in the drawings, the plain `RM` code in
        iB1000 — so it cannot be spelt as a list of included values. `Q57`
        measured that `A01`, the drawings' commonest relative level, sits within
        8 m of a level-1 edge 93% of the time: it is the elevated network, and
        an inclusion filter built on "commonest must mean normal" would have
        kept exactly the wrong 57% of the layer."""
        drawings, topographic = hong_kong.carriageway_survey.edges

        assert drawings.off_grade_codes == ("A01", "A03")
        assert drawings.elevation_field == "ELEVATION"
        # iB1000 has no level column at all, so its under-deck margin is
        # excluded by carrying a code (`RMU`) that `codes` does not list —
        # the omission is the filter, and there is nothing to declare.
        assert topographic.elevation_field is None
        assert topographic.off_grade_codes == ()
        assert "RMU" not in topographic.codes

    def test_every_named_source_can_be_fetched(self, hong_kong) -> None:
        """A typo would surface as a missing file after a build's worth of work."""
        for edge in hong_kong.carriageway_survey.edges:
            known = hong_kong.tiled_sources if edge.tiled else hong_kong.sources
            assert edge.source in known

    def test_the_block_is_optional(self, rewrite) -> None:
        """A city with no published carriageway edge says so by leaving the
        block out, and is then honestly unmeasurable rather than measured
        against an invented width."""
        cities = rewrite(lambda doc: doc.pop("carriageway_survey"))
        city = load_city("hong_kong", cities_root=cities)

        assert city.carriageway_survey is None

    def test_an_empty_edge_list_is_rejected(self, rewrite) -> None:
        """It would report total coverage of nothing, which reads as agreement."""

        def empty(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"] = []

        with pytest.raises(ValueError, match="is empty"):
            load_city("hong_kong", cities_root=rewrite(empty))

    def test_repeated_names_are_rejected(self, rewrite) -> None:
        """The report is keyed by name, so a duplicate merges two publishers into
        one column and hides the disagreement that is the reason for reading
        more than one of them."""

        def collide(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"][1]["name"] = doc["carriageway_survey"]["edges"][0][
                "name"
            ]

        with pytest.raises(ValueError, match="repeated names"):
            load_city("hong_kong", cities_root=rewrite(collide))

    def test_an_empty_code_list_is_rejected(self, rewrite) -> None:
        """It would match no feature and report the source as carrying nothing,
        which is indistinguishable from a publisher having dropped the layer."""

        def empty(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"][0]["codes"] = []

        with pytest.raises(ValueError, match="codes is empty"):
            load_city("hong_kong", cities_root=rewrite(empty))

    def test_an_unfetchable_plain_source_is_rejected(self, rewrite) -> None:
        def rename(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"][0]["source"] = "no_such_source"

        with pytest.raises(ValueError, match="which is not in sources"):
            load_city("hong_kong", cities_root=rewrite(rename))

    def test_an_unfetchable_tiled_source_is_rejected(self, rewrite) -> None:
        """The per-sheet entry is checked against `tiled_sources`, not `sources`
        — naming a plain source there would fetch one file and read it as six."""

        def rename(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"][1]["source"] = "road_network_gdb"

        with pytest.raises(ValueError, match="which is not in tiled_sources"):
            load_city("hong_kong", cities_root=rewrite(rename))

    def test_a_malformed_member_placeholder_is_rejected(self, rewrite) -> None:
        """Otherwise it surfaces at first read, once per sheet, rather than at
        load — the same reason `podiums.member` is checked here."""

        def broken(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"][1]["member"] = "{sheet}/{sheet}.gdb"

        with pytest.raises(ValueError, match="placeholder"):
            load_city("hong_kong", cities_root=rewrite(broken))

    def test_off_grade_codes_without_a_column_to_read_them_from_is_rejected(self, rewrite) -> None:
        """⚠️ It would load, filter nothing, and publish a level-0 figure computed
        over the flyovers too — inert config that still prints a plausible
        number, which is the failure `_sampling_block` refuses for."""

        def orphan(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"][1]["off_grade_codes"] = ["RMU"]

        with pytest.raises(ValueError, match="no 'elevation' role"):
            load_city("hong_kong", cities_root=rewrite(orphan))

    def test_a_missing_edge_type_role_is_rejected(self, rewrite) -> None:
        def drop(doc: dict[str, Any]) -> None:
            doc["carriageway_survey"]["edges"][0]["fields"].pop("edge_type")

        with pytest.raises(ValueError, match="missing edge_type"):
            load_city("hong_kong", cities_root=rewrite(drop))
