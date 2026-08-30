"""Fixtures shared across the test suite.

Only fixtures live here — pytest injects them, so nothing imports this module
and the double-import trap above does not apply. Plain helpers go in
`tests/helpers.py`.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.config import load_config
from tests.helpers import CITY_YAML, NULL_SENTINELS, line_wkb, write_layer


@pytest.fixture
def hong_kong():
    """The real city config.

    The real one rather than a stub on purpose: a stub would drift out of step
    with the schema and keep passing while the shipped config broke.
    """
    return load_config()


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
    path = tmp_path / "testville.yaml"
    path.write_text(CITY_YAML, encoding="utf-8")
    return load_config(path)


@pytest.fixture
def testville(tmp_path, testville_config):
    """A whole city — config, geodatabase and all — under `tmp_path`.

    Here rather than in `test_roads.py`, where it was written, because
    `test_kerbside.py` builds the same city to check the join it publishes and a
    second copy of a four-layer geodatabase is four places for the two to drift.
    """
    city = testville_config

    transform = city.game_transform("middle")

    def at(x: float, z: float) -> tuple[float, float]:
        """Region-local game metres to source easting/northing.

        Through the transform rather than off the projected bounds: the origin
        is rounded outward to whole metres, so the two differ by up to a metre
        and the expected coordinates below are stated exactly.
        """
        easting, northing, _ = transform.to_source(x, 0.0, z)
        return (easting, northing)

    gpkg = tmp_path / "sources" / "roads" / "roads.gpkg"
    gpkg.parent.mkdir(parents=True)

    write_layer(
        gpkg,
        "CENTERLINE",
        [
            # A two-way street, west to east, meeting the next at (300, 100).
            line_wkb([at(100.0, 100.0), at(200.0, 100.0), at(300.0, 100.0)]),
            # One-way continuing east, on a flyover deck.
            line_wkb([at(300.0, 100.0), at(500.0, 100.0)]),
            # A side street joining the same node, unnamed, with a tram.
            line_wkb([at(300.0, 100.0), at(300.0, 400.0)]),
            # Runs off the eastern edge of the region and must be cut.
            line_wkb([at(500.0, 100.0), at(5000.0, 100.0)]),
        ],
        {
            "ELEVATION": np.array([0, 1, 0, 0]),
            "TRAVEL_DIRECTION": np.array([1, 3, 3, 3]),
            "ROUTE_ID": np.array([11, 12, 13, 14]),
            "STREET_ENAME": np.array(
                ["MAIN STREET", "MAIN STREET", "TRAM STREET", "-99"], dtype=object
            ),
            "STREET_CNAME": np.array(["大街", "大街", "電車街", NULL_SENTINELS[1]], dtype=object),
        },
    )
    write_layer(
        gpkg,
        "SPEED_LIMIT",
        [line_wkb([at(300.0, 100.0), at(500.0, 100.0)])],
        {"ROAD_ROUTE_ID": np.array([12]), "SPEED_LIMIT": np.array(["70 km/h"], dtype=object)},
    )
    write_layer(
        gpkg,
        "BUS_ONLY_LANE",
        [line_wkb([at(100.0, 100.0), at(300.0, 100.0)])],
        {"ROAD_ROUTE_ID": np.array([11])},
    )
    write_layer(
        gpkg,
        "NSR",
        [
            # The north kerb of the two-way main street, which runs west to east
            # — so the nearside — restricted around the clock.
            line_wkb([at(110.0, 94.0), at(290.0, 94.0)]),
            # The same kerb again, overlapping, as the source does.
            line_wkb([at(150.0, 94.0), at(250.0, 94.0)]),
            # The south kerb, posted hours only, so a single line.
            line_wkb([at(110.0, 106.0), at(200.0, 106.0)]),
            # A goods-vehicle restriction, which is a sign rather than a line.
            line_wkb([at(210.0, 106.0), at(290.0, 106.0)]),
        ],
        {"VEHICLE_TYPE": np.array([1, 1, 1, 4]), "TIME_ZONE": np.array([1, 1, 3, 1])},
    )
    write_layer(
        gpkg,
        "TURN",
        [line_wkb([at(250.0, 100.0), at(300.0, 250.0)])],
        {
            "EDGE1FID": np.array([1]),
            "EDGE1END": np.array(["Y"], dtype=object),
            "EDGE2FID": np.array([3]),
        },
    )
    return city, tmp_path
