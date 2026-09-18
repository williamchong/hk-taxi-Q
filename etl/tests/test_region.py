"""`pipeline/region.py` — the level-0 carriageway as a region (`Q129`, `P3-33b`).

Only the parts whose failure mode is **silent**. A region that failed to build
would raise; what would not announce itself is a side named wrongly, an extent
indexed against a deduplicated polyline, a neighbour's asphalt dropped at the
seam, and a run cut at the rectangle reading its own clip as HyD's silence.
"""

from __future__ import annotations

import numpy as np
import pytest
import shapely
from shapely.geometry import LineString, Polygon

from pipeline.config import CarriagewayRegion
from pipeline.region import (
    KERB,
    NONE,
    SHARE,
    Centreline,
    RegionReport,
    build,
    centrelines,
)

SPEC = CarriagewayRegion(sample_m=1.0, rail_m=2.0, station_m=10.0, rail_tolerance_m=0.1)
CLIP = shapely.box(-100.0, -100.0, 200.0, 100.0)


def _line(edge_id: int, plan, **fields) -> Centreline:
    values = {"foreign": False, "width_m": 6.4, "width_source": "authored"}
    return Centreline(id=edge_id, plan=np.asarray(plan, dtype=float), **(values | fields))


def _build(polygons, kerbs, lines, clip=CLIP):
    report = RegionReport()
    hyd, strip, territories = build(
        polygons, kerbs, lines, clip=clip, spec=SPEC, max_m=16.5, min_span_m=3.0, report=report
    )
    return hyd, strip, {t.edge.id: t for t in territories}, report


def test_left_is_left_of_travel() -> None:
    # Heading +x (east) in a frame whose z is SOUTH: left of travel is north, -z.
    road = Polygon([(0, -6), (100, -6), (100, 2), (0, 2)])
    _, _, owned, _ = _build([road], [], [_line(1, [(0, 0), (50, 0), (100, 0)])])
    assert owned[1].along_m == pytest.approx(np.arange(0.0, 101.0, 10.0))
    assert owned[1].left_m == pytest.approx([6.0] * 11)
    assert owned[1].right_m == pytest.approx([2.0] * 11)
    assert owned[1].left_end == owned[1].right_end == [KERB] * 11


def test_two_centrelines_in_one_carriageway_split_it() -> None:
    road = Polygon([(0, 0), (100, 0), (100, 12), (0, 12)])
    lines = [_line(1, [(0, 3), (100, 3)]), _line(2, [(0, 9), (100, 9)])]
    hyd, strip, owned, report = _build([road], [], lines)
    assert owned[1].shape.area == pytest.approx(600.0, rel=1e-3)
    assert owned[1].shape.intersection(owned[2].shape).area == pytest.approx(0.0, abs=1e-6)
    assert report.owned_m2 == pytest.approx(hyd.area + strip.area)
    # Heading east with the other centreline to the south: the RIGHT side is shared.
    assert (owned[1].left_end[0], owned[1].right_end[0]) == (KERB, SHARE)
    assert owned[1].left_m[0] + owned[1].right_m[0] == pytest.approx(6.0, abs=1e-6)
    assert report.ends["authored"]["kerb|share"] == 22


def test_a_neighbours_run_keeps_its_territory_inside_this_rectangle() -> None:
    # The seam rule: asphalt goes by rectangle, so the foreign half is PUBLISHED —
    # dropped, it is a hole neither build draws.
    road = Polygon([(0, 0), (100, 0), (100, 12), (0, 12)])
    lines = [_line(1, [(0, 3), (100, 3)]), _line(2, [(0, 9), (100, 9)], foreign=True)]
    _, _, owned, report = _build([road], [], lines)
    assert owned[2].shape.area == pytest.approx(600.0, rel=1e-3)
    assert report.foreign_m2 == pytest.approx(600.0, rel=1e-3)
    assert report.owned_m2 == pytest.approx(600.0, rel=1e-3)
    assert set(report.ends) == {"authored"}


def test_a_neighbours_run_casts_rails_where_hyd_is_silent() -> None:
    kerbs = [LineString([(-5, -3), (45, -3)]), LineString([(-5, 3), (45, 3)])]
    _, strip, owned, report = _build([], kerbs, [_line(7, [(0, 0), (40, 0)], foreign=True)])
    assert strip.area == pytest.approx(240.0)
    assert owned[7].shape.area == pytest.approx(240.0)
    assert sum(report.silent_m.values()) == 0.0  # counted over owned runs only


def test_a_run_cut_at_the_rectangle_does_not_read_the_clip_as_silence() -> None:
    # `|stage - tool|` found this one: the cut end stands ON the clipped boundary,
    # where `contains` is false, and cast a 2 m rail out to a kerb line HyD's own
    # polygon stops short of.
    road = Polygon([(-50, -4), (100, -4), (100, 4), (-50, 4)])
    kerbs = [LineString([(-50, -7), (100, -7)]), LineString([(-50, 7), (100, 7)])]
    clip = shapely.box(0.0, -50.0, 100.0, 50.0)
    hyd, strip, _, report = _build([road], kerbs, [_line(1, [(0, 0), (100, 0)])], clip=clip)
    assert strip.is_empty
    assert hyd.area == pytest.approx(800.0)
    assert sum(report.silent_m.values()) == 0.0


def test_a_span_under_the_hard_minimum_is_not_a_kerb() -> None:
    kerbs = [LineString([(-5, -1), (45, -1)]), LineString([(-5, 1), (45, 1)])]
    _, strip, _, report = _build([], kerbs, [_line(1, [(0, 0), (40, 0)], width_m=7.0)])
    assert report.rail_stations_refused == 21
    assert report.silent_m[0] == pytest.approx(40.0)
    assert strip.bounds == pytest.approx((0.0, -3.5, 40.0, 3.5))


def test_a_straight_street_is_stationed_between_its_two_vertices() -> None:
    # Schema 1's defect: a straight street is two vertices, both at nodes, so
    # extents at the vertices alone are a sliver the length of the block. The
    # bulge below is 40 m from either vertex and only a station can see it.
    road = Polygon([(0, -3), (30, -3), (30, -9), (70, -9), (70, -3), (100, -3), (100, 3), (0, 3)])
    _, _, owned, _ = _build([road], [], [_line(1, [(0, 0), (100, 0)])])
    territory = owned[1]
    assert territory.vertex_station == [0, 10]
    assert territory.left_m[0] == territory.left_m[10] == pytest.approx(3.0)
    assert territory.left_m[5] == pytest.approx(9.0)
    assert territory.right_m == pytest.approx([3.0] * 11)


def test_vertices_are_indexed_into_the_stations_repeats_included() -> None:
    # `carriageway[]` is indexed by `roadgraph.json`'s own vertex numbering, and a
    # published polyline can repeat a vertex. A deduplicated plan shifts every
    # index after the repeat, and every consumer reads a plausible number.
    graph = {
        "edges": [
            {
                "id": 3,
                "elevation_level": 0,
                "width_m": 6.4,
                "polyline": [[0, 0, 0], [50, 0, 0], [50, 0, 0], [100, 0, 0]],
            },
            {"id": 4, "elevation_level": 1, "width_m": 6.4, "polyline": [[0, 0, 9], [9, 0, 9]]},
        ]
    }
    lines = centrelines(graph)
    assert [line.id for line in lines] == [3]  # level 0 only
    road = Polygon([(0, -6), (100, -6), (100, 2), (0, 2)])
    _, _, owned, _ = _build([road], [], lines)
    territory = owned[3]
    assert [territory.along_m[index] for index in territory.vertex_station] == [0, 50, 50, 100]
    assert len(set(territory.vertex_station)) == 4  # the repeat keeps a station of its own
    assert territory.left_m == pytest.approx([6.0] * len(territory.along_m))


def test_an_end_vertex_is_measured_inside_its_territory_not_on_the_node() -> None:
    # Two edges meeting at a node: the node is on both territories' boundary, so a
    # cross-section AT it has no inside and would read zero on a good road.
    road = Polygon([(0, -4), (100, -4), (100, 4), (0, 4)])
    lines = [_line(1, [(0, 0), (50, 0)]), _line(2, [(50, 0), (100, 0)])]
    _, _, owned, _ = _build([road], [], lines)
    assert owned[1].left_m[-1] == pytest.approx(4.0)
    assert owned[2].right_m[0] == pytest.approx(4.0)


def test_a_run_past_the_rectangle_owns_only_an_orphan_and_is_counted() -> None:
    # Its sites still compete, so it takes the in-rectangle asphalt nearest it —
    # which never touches its own centreline. That is what `orphan_m2` prices, and
    # its vertices stand on no territory at all.
    road = Polygon([(0, -4), (300, -4), (300, 4), (0, 4)])
    lines = [_line(1, [(0, 0), (100, 0)]), _line(2, [(210, 0), (290, 0)])]
    _, _, owned, report = _build([road], [], lines)
    assert owned[2].shape.bounds == pytest.approx((155.0, -4.0, 200.0, 4.0))
    assert set(owned[2].left_end) == set(owned[2].right_end) == {NONE}
    assert set(owned[2].left_m) == set(owned[2].right_m) == {0.0}
    assert report.orphan_m2 == pytest.approx(45.0 * 8.0)
    assert report.orphan_pieces == 1
    assert report.owned_past_rectangle_m == pytest.approx(80.0)
