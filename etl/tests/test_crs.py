"""Coordinate conversion tests.

The reference values below are external facts about the HK1980 Grid System, not
values read back out of this code, so these tests can actually fail if the
conversion is wrong. Everything Hong Kong specific lives in this file rather
than in the pipeline.
"""

from __future__ import annotations

import math

import pytest

from pipeline.crs import (
    GameTransform,
    GeodeticBounds,
    ProjectedBounds,
    project_bounds,
    transformer,
)

# The HK1980 Grid System's published definition (EPSG:2326). Its natural origin
# is expressed on the HK1980 geodetic datum, EPSG:4611 — which is the whole
# point of the datum test below.
HK1980_GRID = "EPSG:2326"
HK1980_GEODETIC = "EPSG:4611"
WGS84 = "EPSG:4326"

GRID_ORIGIN_LON = 114 + 10 / 60 + 42.80 / 3600
GRID_ORIGIN_LAT = 22 + 18 / 60 + 43.68 / 3600
FALSE_EASTING = 836694.05
FALSE_NORTHING = 819069.80

# docs/DATA_SOURCES.md, "Region of interest". Hardcoded rather than read from
# hong_kong.yaml on purpose: these tests check the CRS maths, and taking their
# inputs from the config under test would make them agree with it by
# construction. Holding the YAML to these numbers is test_config.py's job.
WAN_CHAI = GeodeticBounds(west=114.172, east=114.188, south=22.276, north=22.284)


def test_grid_origin_projects_to_the_published_false_origin() -> None:
    """The one reference point whose answer is published rather than computed.

    By definition the projection's natural origin maps to the false easting and
    northing. Anything wrong with axis order, datum selection or unit handling
    breaks this.
    """
    easting, northing = transformer(HK1980_GEODETIC, HK1980_GRID).transform(
        GRID_ORIGIN_LON, GRID_ORIGIN_LAT
    )
    assert easting == pytest.approx(FALSE_EASTING, abs=1e-3)
    assert northing == pytest.approx(FALSE_NORTHING, abs=1e-3)


def test_reading_wgs84_coordinates_as_hk1980_moves_the_region_hundreds_of_metres() -> None:
    """Why city config must declare the datum of its bounds.

    This is not a hypothetical. Bounds read off any consumer web map are WGS84;
    interpreting the same digits as HK1980 puts the region a fifth of its own
    width from the road data, with no error and entirely plausible-looking
    output. Config states `crs.geodetic` so this cannot happen silently.
    """
    as_hk1980 = transformer(HK1980_GEODETIC, HK1980_GRID).transform(
        GRID_ORIGIN_LON, GRID_ORIGIN_LAT
    )
    as_wgs84 = transformer(WGS84, HK1980_GRID).transform(GRID_ORIGIN_LON, GRID_ORIGIN_LAT)
    separation = math.dist(as_hk1980, as_wgs84)
    assert separation > 250.0, (
        "Expected the two datums to disagree by hundreds of metres. If this "
        "shrank, PROJ may have fallen back to a ballpark transformation."
    )


def test_geodetic_round_trip_returns_the_original_degrees() -> None:
    to_grid = transformer(WGS84, HK1980_GRID)
    from_grid = transformer(HK1980_GRID, WGS84)
    for lon, lat in ((WAN_CHAI.west, WAN_CHAI.south), (WAN_CHAI.east, WAN_CHAI.north)):
        back_lon, back_lat = from_grid.transform(*to_grid.transform(lon, lat))
        # 1e-7 degrees is roughly a centimetre at this latitude.
        assert back_lon == pytest.approx(lon, abs=1e-7)
        assert back_lat == pytest.approx(lat, abs=1e-7)


def test_transformers_are_cached_per_crs_pair() -> None:
    """Construction hits the PROJ database; the pipeline converts millions of
    vertices through a handful of pairs."""
    assert transformer(WGS84, HK1980_GRID) is transformer(WGS84, HK1980_GRID)


def test_wan_chai_projects_to_its_documented_size() -> None:
    bounds = project_bounds(WAN_CHAI, geodetic_crs=WGS84, projected_crs=HK1980_GRID)
    assert bounds.width_m == pytest.approx(1650.0, abs=50.0)
    assert bounds.height_m == pytest.approx(900.0, abs=50.0)


class TestGameTransform:
    """The projected-to-Godot leg. Pure arithmetic, so these are exact."""

    transform = GameTransform(origin_easting=835765.0, origin_northing=815238.0)

    def test_round_trip_is_exact(self) -> None:
        source = (836000.0, 815900.0, 12.5)
        assert self.transform.to_source(*self.transform.to_game(*source)) == pytest.approx(
            source, abs=1e-9
        )

    def test_axes_follow_the_godot_convention(self) -> None:
        origin = self.transform.to_game(836000.0, 815900.0, 10.0)
        east = self.transform.to_game(836100.0, 815900.0, 10.0)
        north = self.transform.to_game(836000.0, 816000.0, 10.0)
        up = self.transform.to_game(836000.0, 815900.0, 20.0)

        assert east[0] - origin[0] == pytest.approx(100.0)
        assert up[1] - origin[1] == pytest.approx(10.0)
        # Godot is right-handed and Y-up. Without the negation the city would be
        # mirrored, which reads as a plausible map that no local recognises.
        assert north[2] - origin[2] == pytest.approx(-100.0)

    def test_origin_lands_on_whole_metres(self) -> None:
        """Tile boundaries are measured from the origin, so it must not inherit
        the last decimal place of whatever PROJ release generated it."""
        bounds = project_bounds(WAN_CHAI, geodetic_crs=WGS84, projected_crs=HK1980_GRID)
        transform = GameTransform.from_bounds(bounds)
        assert transform.origin_easting == math.floor(transform.origin_easting)
        assert transform.origin_northing == math.floor(transform.origin_northing)

    def test_region_sits_north_west_of_the_origin(self) -> None:
        """Origin at the south-west corner plus a negated northing means the
        region runs +X east and -Z north. Documented here because the sign of Z
        is the thing every consumer of city.json gets wrong once."""
        bounds = project_bounds(WAN_CHAI, geodetic_crs=WGS84, projected_crs=HK1980_GRID)
        transform = GameTransform.from_bounds(bounds)

        south_west = transform.to_game(bounds.min_easting, bounds.min_northing)
        north_east = transform.to_game(bounds.max_easting, bounds.max_northing)

        assert 0.0 <= south_west[0] < 1.0
        assert -1.0 < south_west[2] <= 0.0
        assert north_east[0] > south_west[0]
        assert north_east[2] < south_west[2]


class TestGeodeticBounds:
    def test_rejects_inverted_longitude(self) -> None:
        with pytest.raises(ValueError, match="west"):
            GeodeticBounds(west=114.188, east=114.172, south=22.276, north=22.284)

    def test_rejects_degenerate_latitude(self) -> None:
        with pytest.raises(ValueError, match="south"):
            GeodeticBounds(west=114.172, east=114.188, south=22.276, north=22.276)


def test_projected_bounds_report_their_extent() -> None:
    bounds = ProjectedBounds(
        min_easting=100.0, min_northing=200.0, max_easting=350.0, max_northing=800.0
    )
    assert bounds.width_m == pytest.approx(250.0)
    assert bounds.height_m == pytest.approx(600.0)
