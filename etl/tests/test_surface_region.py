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
from shapely.geometry import Point as shapely_point
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
        triangles, _ = surface_region.areas(
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
        triangles, _ = surface_region.areas(
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
        triangles, _ = surface_region.areas(
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


class TestTheRailIsTheRunningKerbLine:
    """`opened`: an outward bump shorter than the window is a bay, not the road."""

    ALONG = np.arange(0.0, 101.0, 2.0)

    def _bay(self, start: float, stop: float, depth: float) -> np.ndarray:
        return np.where((start <= self.ALONG) & (stop >= self.ALONG), 3.0 + depth, 3.0)

    def _opened(self, left, window_m=20.0, bump_m=0.5):
        count = len(self.ALONG)
        stations = _stations(self.ALONG, left, np.full(count, 3.0), vertices=[0, count - 1])
        return surface_region.opened(stations, window_m, bump_m)

    def test_a_bay_shorter_than_the_window_is_let_go_of(self) -> None:
        opened = self._opened(self._bay(40, 52, 2.5))
        assert opened.left_m == pytest.approx(3.0)
        assert opened.right_m == pytest.approx(3.0)

    def test_and_its_kerb_stops_following_the_rail(self) -> None:
        # The kerb strip is drawn ALONG THE RAIL: left set, a riser would stand
        # across the mouth of the bay the rail now runs straight past.
        opened = self._opened(self._bay(40, 52, 2.5))
        in_bay = (self.ALONG >= 40) & (self.ALONG <= 52)
        assert not opened.kerb_left[in_bay].any()
        assert opened.kerb_left[~in_bay].all()
        assert opened.kerb_right.all()

    def test_a_widening_longer_than_the_window_is_a_carriageway(self) -> None:
        wide = self._bay(30, 70, 2.5)
        assert self._opened(wide).left_m == pytest.approx(wide)

    def test_it_never_widens_so_an_island_is_never_drawn_over(self) -> None:
        pinch = self._bay(40, 52, -2.0)
        opened = self._opened(pinch)
        assert (opened.left_m <= pinch + 1e-9).all()
        assert opened.left_m[(self.ALONG >= 40) & (self.ALONG <= 52)] == pytest.approx(1.0)

    def test_a_taper_is_left_exactly_alone(self) -> None:
        taper = 3.0 + 0.05 * self.ALONG
        assert self._opened(taper).left_m == pytest.approx(taper)

    def test_kerb_jitter_under_the_bump_bar_stays_on_the_rail(self) -> None:
        # Applied whole, the opening moved 33,400 m2 of Wan Chai to area and
        # cleared a quarter of the kerb flags, for bumps that total a tenth of it.
        jitter = 3.0 + 0.2 * (np.arange(len(self.ALONG)) % 2)
        opened = self._opened(jitter)
        assert opened.left_m == pytest.approx(jitter)
        assert opened.kerb_left.all()


class TestAreasCarryTheirOwnKerb:
    ROAD = Polygon([(0, -5), (100, -5), (100, 5), (0, 5)])
    CENTRE = np.array([(0.0, 7.0, 0.0), (100.0, 7.0, 0.0)])

    def _lines(self, **kwargs):
        region = surface_region.Region(whole=self.ROAD, shapes={(False, 1): self.ROAD}, stations={})
        ribbon = np.array([(20.0, -5.0), (100.0, -5.0), (100.0, 5.0), (20.0, 5.0)])
        return surface_region.areas(region, [ribbon], {(False, 1): self.CENTRE}, [], **kwargs)[1]

    def test_the_kerb_is_the_boundary_an_area_shares_with_R(self) -> None:
        lines = self._lines()
        # The 20 m end west of the ribbon: two sides and the end, not the seam
        # with the ribbon at x = 20, which is interior to R.
        assert sum(np.hypot(*np.diff(line[:, [0, 2]], axis=0).T).sum() for line in lines) == (
            pytest.approx(50.0)
        )
        assert all(line[:, 1] == pytest.approx(7.0) for line in lines)

    def test_it_is_walked_with_the_road_on_its_right(self) -> None:
        for line in self._lines():
            plan = line[:, [0, 2]]
            step = plan[1] - plan[0]
            right = np.array([-step[1], step[0]]) / np.hypot(*step)
            probe = 0.5 * (plan[0] + plan[1]) + 0.05 * right
            assert self.ROAD.contains(shapely_point(probe))

    def test_the_regions_own_rectangle_is_a_cut_and_not_a_kerb(self) -> None:
        length = sum(
            np.hypot(*np.diff(line[:, [0, 2]], axis=0).T).sum()
            for line in self._lines(high=(100.0, 5.0))
        )
        # z = 5 lies on the rectangle and so does x = 0 from z = 0 up; what is left
        # is z = -5 (20 m) and the 5 m of x = 0 below it.
        assert length == pytest.approx(25.0, abs=0.05)

    def test_a_stretch_a_ribbon_already_kerbs_is_not_kerbed_twice(self) -> None:
        kerbed = [np.array([(0.0, -5.0), (20.0, -5.0)])]
        length = sum(
            np.hypot(*np.diff(line[:, [0, 2]], axis=0).T).sum()
            for line in self._lines(kerbed=kerbed, kerb_width_m=0.5)
        )
        assert length == pytest.approx(30.0 - 0.5, abs=0.05)


def test_a_short_edge_is_not_one_bump_between_its_two_wedges() -> None:
    # A territory pinches to a wedge at each node, so an edge shorter than the
    # window is, end to end, one bump. The first build collapsed HENNESSY ROAD
    # `e0`, 11 m long, to its wedge width and put its lane centre on the centreline.
    along = np.arange(0.0, 13.0, 2.0)
    hill = np.array([0.5, 2.0, 3.0, 3.0, 3.0, 2.0, 0.5])
    stations = _stations(along, hill, hill, vertices=[0, 6])
    opened = surface_region.opened(stations, 20.0, 0.5)
    assert opened.left_m == pytest.approx(hill)
    assert opened.kerb_left.all()


class TestTheTrimIsReadOffTheFlare:
    """`flare_m`: a ribbon starts where its carriageway has settled."""

    ALONG = np.arange(0.0, 81.0, 2.0)

    def test_a_bell_mouth_is_junction_until_it_settles(self) -> None:
        # 8 m wide at the node, down to 3 m by 12 m in; settled from there.
        left = np.maximum(3.0, 8.0 - self.ALONG * (5.0 / 12.0))
        count = len(self.ALONG)
        stations = _stations(self.ALONG, left, np.full(count, 3.0), vertices=[0, count - 1])
        start, end = surface_region.flare_m(stations, 20.0, 0.5)
        assert 8.0 <= start <= 12.0
        assert end == 0.0

    def test_it_reads_each_end_for_itself(self) -> None:
        count = len(self.ALONG)
        right = np.where(self.ALONG > 70.0, 7.0, 3.0)  # a pocket at the far end only
        stations = _stations(self.ALONG, np.full(count, 3.0), right, vertices=[0, count - 1])
        start, end = surface_region.flare_m(stations, 20.0, 0.5)
        assert start == 0.0
        assert end == pytest.approx(10.0)

    def test_a_settled_road_has_no_flare(self) -> None:
        count = len(self.ALONG)
        stations = _stations(
            self.ALONG, np.full(count, 3.0), np.full(count, 3.2), vertices=[0, count - 1]
        )
        assert surface_region.flare_m(stations, 20.0, 0.5) == (0.0, 0.0)
