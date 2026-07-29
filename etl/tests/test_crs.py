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
    reproject_bounds,
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


@pytest.fixture
def wan_chai_bounds() -> ProjectedBounds:
    return project_bounds(WAN_CHAI, geodetic_crs=WGS84, projected_crs=HK1980_GRID)


class TestGameTransform:
    """The projected-to-Godot leg. Pure arithmetic, so these are exact."""

    # The origin `from_bounds` produces for Wan Chai: floor(min easting), and
    # ceil(max northing) because the origin sits at the *north*-west corner.
    transform = GameTransform(origin_easting=835765.0, origin_northing=816125.0)

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
        # Godot is right-handed and Y-up, so rotating +X by 90 degrees
        # counter-clockwise about +Y lands on -Z: if east is +X then north must
        # be -Z, or the city is mirrored — a plausible map no local recognises.
        # This sign is forced, and moving the origin (Q7) must not change it:
        # the assertion is a difference, so it holds for any origin.
        assert north[2] - origin[2] == pytest.approx(-100.0)

    def test_origin_lands_on_whole_metres(self, wan_chai_bounds) -> None:
        """Tile boundaries are measured from the origin, so it must not inherit
        the last decimal place of whatever PROJ release generated it.

        Asserts integrality rather than a rounding direction — the directions
        differ per axis and are `from_bounds`'s business, not this test's.
        """
        transform = GameTransform.from_bounds(wan_chai_bounds)
        assert float(transform.origin_easting).is_integer()
        assert float(transform.origin_northing).is_integer()

    def test_whole_region_sits_in_the_positive_quadrant(self, wan_chai_bounds) -> None:
        """Q7, resolved: origin at the north-west corner.

        The Z flip is forced by handedness, so anchoring *north* is what keeps Z
        non-negative — which is what makes tile indices natural numbers instead
        of running 0, -1, -2 southward. Pinned because the sign of Z is the thing
        every consumer of city.json gets wrong once.
        """
        transform = GameTransform.from_bounds(wan_chai_bounds)

        # X depends only on easting and Z only on northing, so the four corners
        # cover every extreme the region can produce.
        for easting in (wan_chai_bounds.min_easting, wan_chai_bounds.max_easting):
            for northing in (wan_chai_bounds.min_northing, wan_chai_bounds.max_northing):
                x, _, z = transform.to_game(easting, northing)
                assert x >= 0.0
                assert z >= 0.0

        # And the origin is the NW corner specifically, not merely somewhere
        # north-west of the region — up to the sub-metre outward rounding.
        north_west = transform.to_game(wan_chai_bounds.min_easting, wan_chai_bounds.max_northing)
        assert 0.0 <= north_west[0] < 1.0
        assert 0.0 <= north_west[2] < 1.0


class TestGeodeticBounds:
    def test_rejects_inverted_longitude(self) -> None:
        with pytest.raises(ValueError, match="west"):
            GeodeticBounds(west=114.188, east=114.172, south=22.276, north=22.284)

    def test_rejects_degenerate_latitude(self) -> None:
        with pytest.raises(ValueError, match="south"):
            GeodeticBounds(west=114.172, east=114.188, south=22.276, north=22.276)

    def test_around_takes_the_envelope_of_scattered_points(self) -> None:
        bounds = GeodeticBounds.around([114.18, 114.172, 114.176], [22.28, 22.276, 22.284])
        assert (bounds.west, bounds.east) == (114.172, 114.18)
        assert (bounds.south, bounds.north) == (22.276, 22.284)

    def test_around_rejects_no_points(self) -> None:
        with pytest.raises(ValueError, match="no points"):
            GeodeticBounds.around([], [])

    def test_overlapping_rectangles_intersect(self) -> None:
        assert WAN_CHAI.intersects(
            GeodeticBounds(west=114.180, east=114.200, south=22.280, north=22.300)
        )

    def test_disjoint_rectangles_do_not(self) -> None:
        assert not WAN_CHAI.intersects(
            GeodeticBounds(west=114.200, east=114.220, south=22.276, north=22.284)
        )

    def test_shared_edge_counts_as_intersecting(self) -> None:
        """Map sheets tile edge to edge; a boundary on a shared edge must select
        both neighbours rather than fall down the crack between them."""
        assert WAN_CHAI.intersects(
            GeodeticBounds(west=WAN_CHAI.east, east=114.200, south=22.276, north=22.284)
        )

    def test_separation_in_only_one_axis_is_enough_to_miss(self) -> None:
        """Guards the classic overlap-test bug of testing X and Y with `or`."""
        assert not WAN_CHAI.intersects(
            GeodeticBounds(west=114.176, east=114.180, south=22.300, north=22.310)
        )


class TestReprojectBounds:
    def test_same_crs_returns_the_input_untouched(self) -> None:
        """An identity round-trip through PROJ would still perturb the last
        decimal place, which would be a needless source of drift."""
        assert reproject_bounds(WAN_CHAI, from_crs=WGS84, to_crs=WGS84) is WAN_CHAI

    def test_hk1980_to_wgs84_moves_the_region_hundreds_of_metres(self) -> None:
        """The same shift `test_reading_wgs84_coordinates_as_hk1980...` measures,
        seen from the other side — this is the conversion that stops a published
        index and a region definition being compared across datums."""
        moved = reproject_bounds(WAN_CHAI, from_crs=HK1980_GEODETIC, to_crs=WGS84)
        as_metres = math.dist(
            transformer(WGS84, HK1980_GRID).transform(WAN_CHAI.west, WAN_CHAI.south),
            transformer(WGS84, HK1980_GRID).transform(moved.west, moved.south),
        )
        assert as_metres > 250.0

    def test_result_is_a_superset_not_a_crop(self) -> None:
        """Densified, so a filter built on it over-selects at worst — a spare
        download rather than a hole in the map."""
        there = reproject_bounds(WAN_CHAI, from_crs=WGS84, to_crs=HK1980_GEODETIC)
        back = reproject_bounds(there, from_crs=HK1980_GEODETIC, to_crs=WGS84)
        assert back.west <= WAN_CHAI.west + 1e-9
        assert back.east >= WAN_CHAI.east - 1e-9
        assert back.south <= WAN_CHAI.south + 1e-9
        assert back.north >= WAN_CHAI.north - 1e-9


def test_projected_bounds_report_their_extent() -> None:
    bounds = ProjectedBounds(
        min_easting=100.0, min_northing=200.0, max_easting=350.0, max_northing=800.0
    )
    assert bounds.width_m == pytest.approx(250.0)
    assert bounds.height_m == pytest.approx(600.0)
