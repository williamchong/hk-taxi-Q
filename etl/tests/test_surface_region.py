"""What `surface.py` takes from the carriageway region (`Q129`, `P3-33c`).

Only the parts whose failure mode is **silent** — and two of them already
happened. The first build took `min(lerped rim, measured)` for an inserted
station and drew BOWRINGTON ROAD 1.2 m wide down the middle of its own 6.5 m
territory, with every counter closing; and `clearance` read a territory SHARE as
a corridor and fenced GLOUCESTER ROAD `e390` off a 25 m carriageway.
"""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon

from pipeline import surface_region
from pipeline.surface import (
    _KERB_LEFT,
    _RIM_LEFT,
    _RIM_RIGHT,
    DrawnSurface,
    _clamped_rails,
    _shoelace,
    _stations_kept,
    _with_territory_stations,
)


def _stations(along, left, right, *, vertices, kerb_left=None, kerb_right=None):
    count = len(along)
    return surface_region.Stations(
        along_m=np.asarray(along, dtype=float),
        left_m=np.asarray(left, dtype=float),
        right_m=np.asarray(right, dtype=float),
        kerb_left=np.ones(count) if kerb_left is None else np.asarray(kerb_left, dtype=float),
        kerb_right=np.ones(count) if kerb_right is None else np.asarray(kerb_right, dtype=float),
        left_kerb_m=np.asarray(left, dtype=float),
        right_kerb_m=np.asarray(right, dtype=float),
        vertex_station=np.asarray(vertices, dtype=int),
    )


def _points(rows: int) -> np.ndarray:
    """A straight 100 m edge of `rows` published vertices, no deck: rims `inf`."""
    x = np.linspace(0.0, 100.0, rows)
    matrix = np.zeros((rows, 9))
    matrix[:, 0], matrix[:, 3] = x, 3.2
    matrix[:, _RIM_LEFT] = matrix[:, _RIM_RIGHT] = np.inf
    matrix[:, 7:] = 1.0
    return matrix


class TestExactRails:
    def test_the_territory_extends_past_the_graph_width_as_readily_as_it_cuts(self) -> None:
        half = np.array([3.2, 3.2])
        upper, lower, refused = _clamped_rails(
            half, np.array([6.0, 1.0]), np.array([2.0, 5.0]), 0.0, exact=True
        )
        assert upper == pytest.approx([6.0, 1.0])
        assert lower == pytest.approx([-2.0, -5.0])
        assert refused == 0

    def test_without_exact_a_rim_still_only_cuts(self) -> None:
        upper, lower, _ = _clamped_rails(
            np.array([3.2]), np.array([6.0]), np.array([2.0]), 0.0, exact=False
        )
        assert (upper[0], lower[0]) == pytest.approx((3.2, -2.0))

    def test_a_station_with_no_territory_keeps_the_plain_ribbon_and_is_counted(self) -> None:
        # A run past its region's rectangle (`Q116`): extents of zero.
        upper, lower, refused = _clamped_rails(
            np.array([3.2]), np.array([0.0]), np.array([0.0]), 0.0, exact=True
        )
        assert (upper[0], lower[0], refused) == pytest.approx((3.2, -3.2, 1))


class TestTerritoryStations:
    def test_an_added_station_carries_its_MEASURED_extent_not_the_lerp(self) -> None:
        # Both end vertices are wedges; the street between them is 3 m a side. The
        # lerp between the wedges is 0.5 everywhere, and `min(lerp, measured)` —
        # the first build — drew the whole block half a metre wide.
        along = [0, 25, 50, 75, 100]
        stations = _stations(along, [0.5, 3, 3, 3, 0.5], [0.5, 3, 3, 3, 0.5], vertices=[0, 4])
        merged = _with_territory_stations(_points(2), stations, 0.05)
        assert merged[:, 0] == pytest.approx([0, 25, 75, 100])  # 50 is collinear, pruned
        assert merged[:, _RIM_LEFT] == pytest.approx([0.5, 3.0, 3.0, 0.5])
        assert merged[:, _RIM_RIGHT] == pytest.approx([0.5, 3.0, 3.0, 0.5])

    def test_a_deck_rim_still_cuts_a_territory(self) -> None:
        points = _points(2)
        points[:, _RIM_LEFT] = 2.0
        stations = _stations([0, 100], [5, 5], [4, 4], vertices=[0, 1])
        merged = _with_territory_stations(points, stations, 0.05)
        assert merged[:, _RIM_LEFT] == pytest.approx([2.0, 2.0])
        assert merged[:, _RIM_RIGHT] == pytest.approx([4.0, 4.0])

    def test_pruning_keeps_breakpoints_vertices_and_kerb_changes(self) -> None:
        along = np.arange(0.0, 101.0, 10.0)
        left = np.where(along < 50, 3.0, 3.0 + (along - 50) * 0.1)  # a breakpoint at 50
        kerb = np.ones(11)
        kerb[8:] = 0.0  # the kerb gives way to a share between 70 and 80
        stations = _stations(along, left, np.full(11, 3.0), vertices=[0, 3, 10], kerb_left=kerb)
        kept = _stations_kept(stations, 0.05)
        assert kept.tolist() == [0, 3, 5, 7, 8, 10]

    def test_a_loose_tolerance_prunes_to_the_vertices_alone(self) -> None:
        along = np.arange(0.0, 101.0, 10.0)
        wobble = 3.0 + 0.04 * np.sin(along)
        stations = _stations(along, wobble, wobble, vertices=[0, 10])
        assert _stations_kept(stations, 0.10).tolist() == [0, 10]
        assert len(_stations_kept(stations, 0.001)) > 2

    def test_the_kerb_flag_travels_with_the_station(self) -> None:
        stations = _stations(
            [0, 50, 100], [3, 3, 3], [3, 3, 3], vertices=[0, 2], kerb_left=[1, 0, 0]
        )
        merged = _with_territory_stations(_points(2), stations, 0.05)
        assert merged[:, _KERB_LEFT].tolist() == [1.0, 0.0, 0.0]


class TestAreas:
    ROAD = Polygon([(0, -5), (100, -5), (100, 5), (0, 5)])

    def _region(self, shapes):
        return surface_region.Region(whole=self.ROAD, shapes=shapes, stations={})

    def test_it_is_R_less_every_ribbon_and_faces_up(self) -> None:
        ribbon = np.array([(20.0, -5.0), (80.0, -5.0), (80.0, 5.0), (20.0, 5.0)])
        centre = np.array([(0.0, 7.0, 0.0), (100.0, 7.0, 0.0)])
        triangles = surface_region.areas(
            self._region({(False, 1): self.ROAD}), [ribbon], {(False, 1): centre}, []
        )
        area = sum(abs(_shoelace(tri)) / 2.0 for tri in triangles)
        assert area == pytest.approx(400.0)  # the two 20 m ends, not the ribbon
        assert all(_shoelace(tri) < 0.0 for tri in triangles)
        assert triangles[:, :, 1] == pytest.approx(7.0)

    def test_two_owners_meet_in_a_shared_vertex_not_along_a_crack(self) -> None:
        west = Polygon([(0, -5), (50, -5), (50, 5), (0, 5)])
        east = Polygon([(50, -5), (100, -5), (100, 5), (50, 5)])
        centres = {
            (False, 1): np.array([(0.0, 10.0, 0.0), (50.0, 10.0, 0.0)]),
            (False, 2): np.array([(50.0, 12.0, 0.0), (100.0, 12.0, 0.0)]),
        }
        triangles = surface_region.areas(
            self._region({(False, 1): west, (False, 2): east}), [], centres, []
        )
        by_x = {round(x): set() for x in (0, 100)}
        for x, y, _ in triangles.reshape(-1, 3):
            by_x.setdefault(round(x), set()).add(round(y, 6))
        assert by_x[0] == {10.0} and by_x[100] == {12.0}
        # One height per plan position: a vertex is never at two.
        seen: dict[tuple[float, float], float] = {}
        for x, y, z in triangles.reshape(-1, 3):
            assert seen.setdefault((round(x, 3), round(z, 3)), y) == pytest.approx(y)

    def test_a_vertex_on_a_drawn_rail_takes_the_rails_height(self) -> None:
        ribbon = np.array([(20.0, -5.0), (100.0, -5.0), (100.0, 5.0), (20.0, 5.0)])
        rail = np.array([(20.0, 9.5, -5.0), (20.0, 9.5, 5.0)])
        centre = np.array([(0.0, 7.0, 0.0), (100.0, 7.0, 0.0)])
        triangles = surface_region.areas(
            self._region({(False, 1): self.ROAD}), [ribbon], {(False, 1): centre}, [rail]
        )
        flat = triangles.reshape(-1, 3)
        assert flat[np.isclose(flat[:, 0], 20.0), 1] == pytest.approx(9.5)
        assert flat[np.isclose(flat[:, 0], 0.0), 1] == pytest.approx(7.0)


def test_drawn_surface_reads_the_areas_as_cap_class() -> None:
    triangle = [[0.0, 3.0, 0.0], [0.0, 3.0, 10.0], [10.0, 3.0, 0.0]]
    surface = DrawnSurface.of({"caps": [], "ribbons": [], "areas": [triangle]})
    assert DrawnSurface.levels_drawn({"caps": [], "ribbons": [], "areas": [triangle]}) == [0]
    assert surface.covers(2.0, 2.0)
    assert surface.height_at(2.0, 2.0) == pytest.approx(3.0)
    assert surface.cap_height_at(2.0, 2.0) == pytest.approx(3.0)
    assert not surface.covers(9.0, 9.0)


class TestOpeningsAreBridged:
    """A straight road must not broaden and shrink at every side street."""

    def test_a_mouth_between_two_kerbs_is_held_to_the_kerb_line(self) -> None:
        along = np.arange(0.0, 61.0, 10.0)
        stations = _stations(
            along,
            [3, 3, 9, 11, 9, 3, 3],  # the territory bulges into a side street
            [3] * 7,
            vertices=[0, 6],
            kerb_left=[1, 1, 0, 0, 0, 1, 1],
        )
        bridged = surface_region.bridged(stations)
        assert bridged.left_m == pytest.approx([3.0] * 7)
        assert bridged.right_m == pytest.approx([3.0] * 7)
        assert stations.left_m[3] == 11.0  # the measurement is not rewritten

    def test_it_only_ever_narrows(self) -> None:
        stations = _stations(
            [0, 10, 20], [4, 2, 4], [3, 3, 3], vertices=[0, 2], kerb_left=[1, 0, 1]
        )
        assert surface_region.bridged(stations).left_m == pytest.approx([4.0, 2.0, 4.0])

    def test_the_line_follows_a_road_that_really_widens(self) -> None:
        stations = _stations(
            [0, 10, 20], [3, 12, 5], [3, 3, 3], vertices=[0, 2], kerb_left=[1, 0, 1]
        )
        assert surface_region.bridged(stations).left_m == pytest.approx([3.0, 4.0, 5.0])

    def test_a_share_that_reaches_the_end_of_the_edge_is_left_alone(self) -> None:
        # A carriageway shared with another centreline: no second kerb to bridge to.
        stations = _stations(
            [0, 10, 20], [3, 8, 8], [3, 3, 3], vertices=[0, 2], kerb_left=[1, 0, 0]
        )
        assert surface_region.bridged(stations).left_m == pytest.approx([3.0, 8.0, 8.0])
