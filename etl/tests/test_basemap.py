"""The minimap's ground (`pipeline/basemap.py`): the sea cut from the frame by
the shoreline, and triangles that keep a park's holes."""

from __future__ import annotations

import pytest
import shapely
from shapely.geometry import LineString, Polygon, box

from pipeline.basemap import BasemapReport, sea_of, triangles_of
from pipeline.config import Basemap, SourceLayer
from pipeline.crs import GameTransform


def _spec(seal_m: float = 8.0) -> Basemap:
    layer = SourceLayer(layer="x", fields={})
    return Basemap(
        source="topography",
        member="{tile}/{tile}.gdb",
        reach_m=320.0,
        shoreline=layer,
        shoreline_types=frozenset({"SWA"}),
        parks=layer,
        park_codes=frozenset({"PAR"}),
        buildings=layer,
        seal_m=seal_m,
        land_cover=0.01,
        simplify_m=1.0,
    )


FRAME = box(0.0, 0.0, 100.0, 100.0)
# A shore across the frame at y = 60, land (with a building) below it.
SHORE = [LineString([(-1.0, 60.0), (101.0, 60.0)])]
BUILDING = [box(40.0, 10.0, 60.0, 30.0)]


class TestSea:
    def test_the_piece_with_no_building_is_the_sea(self) -> None:
        report = BasemapReport()
        sea = sea_of(FRAME, SHORE, BUILDING, _spec(), report)
        assert report.pieces == 2 and report.sea_pieces == 1
        # Grown back to the line: the sea meets the shore at y = 60.
        assert sea.area == pytest.approx(40.0 * 100.0, rel=0.01)
        assert sea.contains(shapely.Point(50.0, 90.0))
        assert not sea.contains(shapely.Point(50.0, 20.0))

    def test_a_gap_narrower_than_the_seal_closes(self) -> None:
        """Surveyed shorelines stop short at pier ends; a gap under `seal_m`
        must not join the harbour to the city."""
        broken = [
            LineString([(-1.0, 60.0), (48.0, 60.0)]),
            LineString([(52.0, 60.0), (101.0, 60.0)]),
        ]
        assert sea_of(FRAME, broken, BUILDING, _spec(8.0), BasemapReport()).area > 3000.0
        # Wider than the seal, the frame is one piece and it has a building on it.
        assert sea_of(FRAME, broken, BUILDING, _spec(2.0), BasemapReport()).is_empty

    def test_no_shoreline_is_no_sea(self) -> None:
        assert sea_of(FRAME, [], BUILDING, _spec(), BasemapReport()).is_empty


class TestTriangles:
    def test_a_hole_stays_out_of_the_triangles(self) -> None:
        park = Polygon(
            [(0.0, 0.0), (30.0, 0.0), (30.0, 30.0), (0.0, 30.0)],
            [[(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]],
        )
        transform = GameTransform(origin_easting=0.0, origin_northing=0.0, origin_elevation=0.0)
        triangles = triangles_of(park, 0.1, transform)
        area = sum(
            abs((t[2] - t[0]) * (t[5] - t[1]) - (t[4] - t[0]) * (t[3] - t[1])) * 0.5
            for t in triangles
        )
        assert area == pytest.approx(900.0 - 100.0)
        assert all(len(t) == 6 for t in triangles)
