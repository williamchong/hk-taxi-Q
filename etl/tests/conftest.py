"""Fixtures shared across the test suite.

Only fixtures live here — pytest injects them, so nothing imports this module
and the double-import trap above does not apply. Plain helpers go in
`tests/helpers.py`.
"""

from __future__ import annotations

import pytest

from pipeline.config import load_city
from tests.helpers import CITY_YAML


@pytest.fixture
def hong_kong():
    """The real city config.

    The real one rather than a stub on purpose: a stub would drift out of step
    with the schema and keep passing while the shipped config broke.
    """
    return load_city("hong_kong")


@pytest.fixture
def sources(tmp_path, hong_kong):
    """A sources tree holding one synthetic sheet and an index that selects it.

    The builder lives in `test_buildings.py` beside the fixtures it writes;
    this is only the pytest registration, here because both that module and
    `test_landmarks.py` request it and conftest is where shared fixtures
    resolve. Imported inside the body so collecting this module never imports
    a test module.
    """
    from tests.test_buildings import _write_sources

    return _write_sources(tmp_path, hong_kong)


@pytest.fixture
def testville_config(tmp_path):
    """The synthetic city, loaded through the real loader.

    The road-graph and road-surface stages both build on it, and they are a
    pipeline: a fixture city that drifted between them would let the second
    stage pass against a city the first never built.
    """
    cities = tmp_path / "cities"
    cities.mkdir()
    (cities / "testville.yaml").write_text(CITY_YAML, encoding="utf-8")
    return load_city("testville", cities_root=cities)
