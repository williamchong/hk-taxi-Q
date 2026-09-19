"""`surface.build_region` down the path that SHIPS — with a carriageway region.

Every test in `test_surface.py` builds with no `carriageway_region:` block, which
since `P3-33c` is a path no shipped region takes; the territory path was tested
through its helpers alone (`test_surface_region.py`). `Q133`'s review found that,
and these are the end-to-end half (`P3-35c`).

The fixture runs the **real** `region.build` over a graph and a handful of
polygons standing in for HyD's, writes `carriageway_region.json` through the
stage's own `_document`, and hands the pair to `surface`. So what is pinned is
the hand-off between the two stages and not either stage's idea of the other.

⚠️ Truth here is the polygon the test drew, read back off the shipped MESH —
never `carriageway[]` alone, which is what the stage says it drew.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import shapely

from pipeline import region as region_stage
from pipeline.config import CarriagewayRegion, Config
from pipeline.documents import write_document
from pipeline.surface import (
    MARKING_CLASS_CAP,
    MARKING_CLASS_CARRIAGEWAY,
    MARKING_CLASS_KERB,
    build_region,
)
from tests.test_surface import _decode, _edge, _manifest, _mesh, _write_graph

SPEC = CarriagewayRegion(
    sample_m=1.0,
    rail_m=2.0,
    station_m=10.0,
    rail_tolerance_m=0.1,
    rail_opening_m=20.0,
    seam_m=0.1,
)

# The carriageway as a publisher would draw it. The east-west road is 16 m wide
# and its centreline is NOT in the middle of it — 9 m of road to the north
# (`z` 291) and 7 m to the south (`z` 307) — which is `P3-33c`'s whole point: 288
# of Wan Chai's 734 level-0 ribbons sit more than 1 m off their centreline. The
# north-south road is 8 m and centred.
EAST_WEST = shapely.box(100.0, 291.0, 500.0, 307.0)
NORTH_SOUTH = shapely.box(296.0, 100.0, 304.0, 500.0)
CARRIAGEWAY = (EAST_WEST, NORTH_SOUTH)

NODES = [
    {"id": 0, "pos": [300.0, 0.0, 300.0], "kind": "junction"},
    {"id": 1, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
    {"id": 2, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
    {"id": 3, "pos": [300.0, 0.0, 100.0], "kind": "endpoint"},
    {"id": 4, "pos": [300.0, 0.0, 500.0], "kind": "endpoint"},
    {"id": 5, "pos": [300.0, 6.0, 700.0], "kind": "endpoint"},
]
EDGES = [
    _edge(0, 1, 0, [[100.0, 0.0, 300.0], [300.0, 0.0, 300.0]]),
    _edge(1, 0, 2, [[300.0, 0.0, 300.0], [500.0, 0.0, 300.0]]),
    _edge(2, 3, 0, [[300.0, 0.0, 100.0], [300.0, 0.0, 300.0]]),
    _edge(3, 0, 4, [[300.0, 0.0, 300.0], [300.0, 0.0, 500.0]]),
    # The flyover `test_surface.testville` carries, six metres up: levels ±1 keep
    # their ribbons and their caps whatever the region says (`Q103`, `Q107`).
    _edge(5, 0, 5, [[300.0, 6.0, 300.0], [300.0, 6.0, 700.0]], elevation_level=1),
]


def _write_region(city: Config, out: Path, polygons=CARRIAGEWAY) -> None:
    out_dir = out / "middle"
    graph = json.loads((out_dir / "roadgraph.json").read_text(encoding="utf-8"))
    high_x, high_z = city.region_high("middle")
    report = region_stage.RegionReport()
    hyd, strip, territories, islands = region_stage.build(
        list(polygons),
        [],
        region_stage.centrelines(graph),
        clip=shapely.box(0.0, 0.0, high_x, high_z),
        spec=SPEC,
        max_m=16.5,
        min_span_m=3.0,
        report=report,
        lane_width_m=city.roads.lane_width_m,
    )
    write_document(
        out_dir / region_stage.REGION_NAME,
        region_stage._document(city, "middle", hyd, strip, territories, report, islands),
    )


@pytest.fixture
def regionville(tmp_path, testville_config) -> tuple[Config, Path]:
    """A crossroads whose carriageway is published, and a flyover over it."""
    _write_graph(tmp_path, NODES, EDGES)
    city = replace(testville_config, carriageway_region=SPEC)
    _write_region(city, tmp_path / "out")
    return city, tmp_path


def _classes(mesh) -> np.ndarray:
    return np.array([_decode(code)["surface_class"] for code in mesh.uv2[:, 0]])


def _plan_area(mesh, keep: np.ndarray) -> float:
    """Plan area of the triangles whose three corners all pass `keep`."""
    corners = mesh.positions[mesh.triangles]
    chosen = keep[mesh.triangles].all(axis=1)
    first, second = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    twice = np.abs(first[:, 0] * second[:, 2] - first[:, 2] * second[:, 0])
    return float(twice[chosen].sum() / 2.0)


def _row(tmp_path: Path, edge: int) -> dict:
    return next(row for row in _manifest(tmp_path)["carriageway"] if row["edge"] == edge)


class TestTheRailsAreTheTerritory:
    def test_the_ribbon_is_as_wide_as_the_published_road_and_not_the_floor(
        self, regionville
    ) -> None:
        city, tmp_path = regionville
        build_region(city, "middle", out_root=tmp_path / "out")
        assert _row(tmp_path, 0)["half_width_m"] == pytest.approx([8.0, 8.0], abs=0.05)
        assert _row(tmp_path, 2)["half_width_m"] == pytest.approx([4.0, 4.0], abs=0.05)

    def test_the_same_graph_without_a_region_draws_the_invented_width(self, regionville) -> None:
        """The control, and the reason the test above means anything: region
        off, both roads draw at the floor and the 16 m road is indistinguishable
        from the 8 m one."""
        city, tmp_path = regionville
        build_region(replace(city, carriageway_region=None), "middle", out_root=tmp_path / "out")
        assert _row(tmp_path, 0)["half_width_m"] == _row(tmp_path, 2)["half_width_m"]

    def test_the_drawn_carriageway_stands_where_the_road_is_not_about_the_centreline(
        self, regionville
    ) -> None:
        """🔴 Read off the MESH. The centreline runs at `z` 300 and the road lies
        291 to 307; a ribbon drawn `±half` about the centreline (`Q106`'s defect,
        four tools wide) covers 292 to 308 with the same half-width published."""
        city, tmp_path = regionville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)
        west_arm = (
            (_classes(mesh) == MARKING_CLASS_CARRIAGEWAY)
            # West of the junction's flare. A straight ribbon has vertices at
            # its two ends only — the stations between are pruned at
            # `rail_tolerance_m` — so the arm is selected whole.
            & (mesh.positions[:, 0] < 280.0)
            & (mesh.positions[:, 1] < 1.0)
        )
        across = mesh.positions[west_arm, 2]
        assert across.min() == pytest.approx(291.0, abs=0.05)
        assert across.max() == pytest.approx(307.0, abs=0.05)
        assert np.abs(_row(tmp_path, 0)["offset_m"]) == pytest.approx([1.0, 1.0], abs=0.05)


class TestEverythingElseOfRIsArea:
    def test_no_cap_is_drawn_at_level_0_and_the_flyover_keeps_its_own(self, regionville) -> None:
        city, tmp_path = regionville
        build_region(city, "middle", out_root=tmp_path / "out")
        levels = {cap["elevation_level"] for cap in _manifest(tmp_path)["caps"]}
        assert 0 not in levels

    def test_the_asphalt_drawn_is_the_asphalt_published(self, regionville) -> None:
        """Ribbons plus areas tile R: no hole at the junction, nothing drawn past
        a kerb. Level 0 only — the flyover is asphalt no publisher here drew."""
        city, tmp_path = regionville
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)
        classes = _classes(mesh)
        asphalt = (classes != MARKING_CLASS_KERB) & (mesh.positions[:, 1] < 1.0)
        published = shapely.union_all(CARRIAGEWAY).area
        assert _plan_area(mesh, asphalt) == pytest.approx(published, rel=0.01)
        assert _plan_area(mesh, asphalt & (classes == MARKING_CLASS_CAP)) > 0.0

    def test_with_the_areas_dropped_the_junction_is_a_hole(
        self, regionville, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The mutation the test above must fail under, kept as a test so the
        area comparison is known to be able to."""
        from pipeline import surface_region

        city, tmp_path = regionville
        monkeypatch.setattr(
            surface_region, "areas", lambda *_, **__: (np.zeros((0, 3, 3)), np.zeros((0, 2, 3)))
        )
        build_region(city, "middle", out_root=tmp_path / "out")
        mesh = _mesh(tmp_path)
        asphalt = (_classes(mesh) != MARKING_CLASS_KERB) & (mesh.positions[:, 1] < 1.0)
        assert _plan_area(mesh, asphalt) < shapely.union_all(CARRIAGEWAY).area * 0.99


class TestWhatFallsBackIsCounted:
    def test_an_edge_with_no_territory_keeps_the_plain_ribbon_and_is_counted(
        self, tmp_path, testville_config
    ) -> None:
        """🔴 Silent until `P3-35c`: `territory_fallback_stations` counts stations
        INSIDE a territory edge, so an edge with no row at all drew the invented
        width and moved no counter. A run wholly past the rectangle is the
        ordinary way to get here (`Q116`)."""
        _write_graph(tmp_path, NODES, EDGES)
        city = replace(testville_config, carriageway_region=SPEC)
        _write_region(city, tmp_path / "out")
        path = tmp_path / "out" / "middle" / region_stage.REGION_NAME
        document = json.loads(path.read_text(encoding="utf-8"))
        document["territories"] = [row for row in document["territories"] if row["edge"] != 2]
        path.write_text(json.dumps(document), encoding="utf-8")

        report = build_region(city, "middle", out_root=tmp_path / "out")
        assert report.territory_edges == 3
        assert report.territory_missing_edges == 1
        assert report.territory_mismatched_edges == 0
        assert _row(tmp_path, 2)["half_width_m"] != pytest.approx([4.0, 4.0], abs=0.05)

    def test_a_territory_that_does_not_index_its_polyline_is_counted(
        self, tmp_path, testville_config
    ) -> None:
        """🔴 `carriageway_region.json` built off another graph than the one drawn.
        The edge falls back to the plain ribbon WHOLE — the invented width, and it
        renders as a road — and until `P3-35c` nothing said so."""
        _write_graph(tmp_path, NODES, EDGES)
        city = replace(testville_config, carriageway_region=SPEC)
        _write_region(city, tmp_path / "out")
        # The graph gains a vertex the region file never saw.
        bent = [dict(edge) for edge in EDGES]
        bent[0] = _edge(0, 1, 0, [[100.0, 0.0, 300.0], [200.0, 0.0, 300.0], [300.0, 0.0, 300.0]])
        _rewrite_graph(tmp_path, bent)

        report = build_region(city, "middle", out_root=tmp_path / "out")
        assert report.territory_mismatched_edges == 1
        assert report.territory_edges == 3


def _rewrite_graph(tmp_path: Path, edges: list[dict]) -> None:
    path = tmp_path / "out" / "middle" / "roadgraph.json"
    scratch = tmp_path / "scratch"
    _write_graph(scratch, NODES, edges)
    path.write_text(
        (scratch / "out" / "middle" / "roadgraph.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
