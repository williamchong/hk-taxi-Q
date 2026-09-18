"""The probe on `tools/carriageway_region.py` (`Q129`).

The same standard the other tool tests keep: only the parts whose failure mode is
**silent**. A region that failed to build would raise; what would not announce
itself is a side named wrongly, an owner that owns the neighbour's asphalt, and a
rail that reads a bay line as a kerb.

🔴 **The side is the one that has already gone wrong, in this tool's first
build.** Every table it prints is a sum of the two sides or a sorted pair of
them, so left and right were swapped through two regions' worth of output with
nothing moved. `R1` publishes the two extents apart, which is where it lands.
"""

from __future__ import annotations

import numpy as np
import pytest
import shapely
from carriageway_region import (
    Centreline,
    build_region,
    cross_sections,
    kerb_strip,
    territories,
)
from shapely.geometry import LineString, Polygon

CLIP = shapely.box(-100.0, -100.0, 200.0, 100.0)
RAILS = {"spacing_m": 2.0, "max_m": 16.5, "min_span_m": 3.0}
LINE = [(0.0, 0.0), (40.0, 0.0)]


def _line(edge_id: int, plan: list[tuple[float, float]], **fields) -> Centreline:
    values = {"foreign": False, "width_m": 6.4, "width_source": "authored", "name": ""}
    return Centreline(id=edge_id, plan=np.asarray(plan, dtype=float), **(values | fields))


def _region(polygons, kerbs, lines, clip=CLIP):
    return build_region(
        polygons, kerbs, lines, clip=clip, spacing_m=2.0, max_m=16.5, min_span_m=3.0
    )


def test_left_is_left_of_travel() -> None:
    # Heading +x (east) in a frame whose z is SOUTH: left of travel is north, -z.
    # The carriageway runs 6 m to the north of the centreline and 2 m to the south.
    road = Polygon([(0, -6), (100, -6), (100, 2), (0, 2)])
    line = _line(1, [(0, 0), (100, 0)])
    region = _region([road], [], [line])
    owned = territories(region, [line], 1.0)
    sections = cross_sections(region, owned, [line], max_m=16.5)
    assert sections
    assert all(s.left_m == pytest.approx(6.0, abs=1e-6) for s in sections)
    assert all(s.right_m == pytest.approx(2.0, abs=1e-6) for s in sections)


def test_two_centrelines_in_one_carriageway_split_it_and_share_the_join() -> None:
    # GLOUCESTER ROAD in miniature: one 12 m carriageway, two centrelines, no kerb
    # between them. Each owns its half, and the side facing the other is a SHARE.
    road = Polygon([(0, 0), (100, 0), (100, 12), (0, 12)])
    north, south = _line(1, [(0, 3), (100, 3)]), _line(2, [(0, 9), (100, 9)])
    region = _region([road], [], [north, south])
    owned = territories(region, [north, south], 1.0)
    assert owned[1].area == pytest.approx(600.0, rel=1e-3)
    assert owned[1].area + owned[2].area == pytest.approx(region.whole.area)
    assert owned[1].intersection(owned[2]).area == pytest.approx(0.0, abs=1e-6)
    for section in cross_sections(region, owned, [north, south], max_m=16.5):
        if section.edge == 1:  # heading east, the other centreline is to the south: RIGHT
            assert (section.left_end, section.right_end) == ("kerb", "share")
            assert section.span_m == pytest.approx(6.0, abs=1e-6)


def test_a_foreign_centreline_takes_its_asphalt_and_reports_none() -> None:
    road = Polygon([(0, 0), (100, 0), (100, 12), (0, 12)])
    own, other = _line(1, [(0, 3), (100, 3)]), _line(2, [(0, 9), (100, 9)], foreign=True)
    region = _region([road], [], [own, other])
    owned = territories(region, [own, other], 1.0)
    assert set(owned) == {1}
    assert owned[1].area == pytest.approx(600.0, rel=1e-3)


def test_the_region_is_cut_to_its_own_rectangle() -> None:
    road = Polygon([(-50, 0), (100, 0), (100, 8), (-50, 8)])
    line = _line(1, [(0, 4), (100, 4)])
    region = _region([road], [], [line], clip=shapely.box(0, -10, 100, 10))
    assert region.whole.area == pytest.approx(800.0)


class TestWhereHydIsSilent:
    def _strip(self, kerbs, **fields):
        return kerb_strip(
            kerbs,
            Polygon(),
            [_line(1, LINE, **fields)],
            spacing_m=2.0,
            max_m=16.5,
            min_span_m=3.0,
        )

    def test_rails_follow_the_kerbs_either_side(self) -> None:
        kerbs = [LineString([(-5, -3), (45, -3)]), LineString([(-5, 5), (45, 5)])]
        strip, silent, refused = self._strip(kerbs)
        assert strip.area == pytest.approx(40.0 * 8.0)
        assert strip.bounds == pytest.approx((0.0, -3.0, 40.0, 5.0))
        assert silent == {2: pytest.approx(40.0), 1: 0.0, 0: 0.0}
        assert refused == 0

    def test_open_linework_still_reads(self) -> None:
        # The reason this is rays and not faces: two kerbs that never close.
        kerbs = [
            LineString([(-5, -3), (18, -3)]),
            LineString([(22, -3), (45, -3)]),
            LineString([(-5, 5), (45, 5)]),
        ]
        strip, silent, _ = self._strip(kerbs)
        # The one station in the gap takes the edge's own median on that side.
        assert strip.area == pytest.approx(40.0 * 8.0)
        assert silent[1] == pytest.approx(2.0)

    def test_a_side_nothing_answers_on_takes_half_the_graph_width(self) -> None:
        strip, silent, _ = self._strip([LineString([(-5, -3), (45, -3)])], width_m=10.0)
        assert strip.bounds == pytest.approx((0.0, -3.0, 40.0, 5.0))
        assert silent[1] == pytest.approx(40.0)

    def test_a_span_under_the_hard_minimum_is_a_bay_line_not_a_kerb(self) -> None:
        kerbs = [LineString([(-5, -1), (45, -1)]), LineString([(-5, 1), (45, 1)])]
        strip, silent, refused = self._strip(kerbs, width_m=7.0)
        assert refused == 21
        assert silent[0] == pytest.approx(40.0)
        assert strip.bounds == pytest.approx((0.0, -3.5, 40.0, 3.5))

    def test_a_centreline_on_hyd_paint_casts_nothing(self) -> None:
        hyd = Polygon([(-1, -4), (41, -4), (41, 4), (-1, 4)])
        strip, silent, _ = kerb_strip(
            [LineString([(-5, -9), (45, -9)])],
            hyd,
            [_line(1, LINE)],
            spacing_m=2.0,
            max_m=16.5,
            min_span_m=3.0,
        )
        assert strip.is_empty
        assert sum(silent.values()) == 0.0
