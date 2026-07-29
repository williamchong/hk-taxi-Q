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
