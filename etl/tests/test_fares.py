"""Fare node construction (`P1-5`).

The unit tests cover the one piece of geometry this stage owns — attaching a
point to the road graph, and saying where along the edge it landed. The
integration tests then build a region from a hand-written graph and a
hand-written pair of point datasets, and check the acceptance criteria for the
task directly: every node's `nearest_edge` resolves, `cross_harbour` survives,
and every name is populated in both languages.

The source points are authored in *game* coordinates and converted back to
lon/lat by the fixture, so a test can say "a stand five metres north of the
crossroads" instead of carrying a magic pair of degrees.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from pipeline.config import load_city
from pipeline.crs import transformer
from pipeline.fares import FARES_NAME, FARES_SCHEMA, Segments, build_region
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA
from tests.helpers import CITY_YAML

REGION = "middle"


# Edge ids deliberately do not match their position in the list. `nearest_edge`
# is published as an id, and `P1-3` happens to number edges in order — so a
# fixture that used 0, 1, 2 would agree with a snapper that returned positions.
_FIRST_EDGE_ID = 40


def _edges(*polylines: list[list[float]]) -> list[dict]:
    return [
        {"id": _FIRST_EDGE_ID + index, "polyline": polyline}
        for index, polyline in enumerate(polylines)
    ]


class TestSnapping:
    def test_a_point_beside_a_straight_road_lands_on_it(self) -> None:
        segments = Segments.of(_edges([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]))
        snap = segments.nearest(25.0, 4.0)

        assert snap.edge == _FIRST_EDGE_ID
        assert snap.distance_m == pytest.approx(4.0)
        assert snap.t == pytest.approx(0.25)

    def test_a_point_past_the_end_clamps_to_the_end(self) -> None:
        """Off the end of a cul-de-sac is still on that road, at t=1 — not at
        some extrapolated position beyond it."""
        segments = Segments.of(_edges([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]))
        snap = segments.nearest(140.0, 0.0)

        assert snap.t == pytest.approx(1.0)
        assert snap.distance_m == pytest.approx(40.0)

    def test_position_along_the_edge_is_by_length_not_by_vertex(self) -> None:
        """An L with a short leg and a long one. Halfway along the *geometry* is
        well inside the long leg, which is not halfway along the vertex list."""
        segments = Segments.of(_edges([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 0.0, 90.0]]))
        snap = segments.nearest(10.0, 40.0)

        # 10 m of first leg plus 40 m into the second, over 100 m in all.
        assert snap.t == pytest.approx(0.5)
        assert snap.distance_m == pytest.approx(0.0)

    def test_the_nearer_of_two_parallel_roads_wins(self) -> None:
        segments = Segments.of(
            _edges(
                [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]],
                [[0.0, 0.0, 20.0], [100.0, 0.0, 20.0]],
            )
        )
        assert segments.nearest(50.0, 12.0).edge == _FIRST_EDGE_ID + 1
        assert segments.nearest(50.0, 8.0).edge == _FIRST_EDGE_ID

    def test_height_comes_from_the_road_not_from_the_point(self) -> None:
        """The sources are 2D, so a fare node's height can only come from the
        edge it attaches to — interpolated along it, not taken from an end."""
        segments = Segments.of(_edges([[0.0, 10.0, 0.0], [100.0, 20.0, 0.0]]))

        assert segments.nearest(50.0, 3.0).y == pytest.approx(15.0)

    def test_distance_is_measured_in_plan(self) -> None:
        """A stand at the foot of a ramp is not 6 m from it because the deck
        climbs — widths and offsets are all ground measurements."""
        segments = Segments.of(_edges([[0.0, 0.0, 0.0], [0.0, 60.0, 100.0]]))

        assert segments.nearest(0.0, 50.0).distance_m == pytest.approx(0.0)

    def test_a_graph_with_no_usable_edge_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no edge with a usable polyline"):
            Segments.of(_edges([[0.0, 0.0, 0.0]]))


# --------------------------------------------------------------------------
# Region fixture
# --------------------------------------------------------------------------


def _road(polyline: list[list[float]]) -> dict:
    return {
        "id": 0,
        "from": 0,
        "to": 1,
        "polyline": polyline,
        "direction": "both",
        "lanes": 2,
        "width_m": 6.4,
        "speed_limit_kph": 50,
        "bus_lane": False,
        "tram_tracks": False,
        "elevation_level": 0,
        "road_name": {"en": "MAIN STREET", "zh": "大街"},
    }


class _Testville:
    """A city, a two-road graph, and a writer for its point datasets.

    Everything a test needs to author source features in game coordinates and
    run the stage over them. Calling it runs the stage.
    """

    def __init__(self, city, out_root: Path, sources: Path, at) -> None:
        self.city = city
        self.out_root = out_root
        self.out_dir = city.out_dir(REGION, out_root)
        self.sources = sources
        self._at = at

    def feature(self, x: float, z: float, status: str, name_en: str, name_zh: str) -> dict:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": self._at(x, z)},
            "properties": {"STATUS": status, "NAME_EN": name_en, "NAME_ZH": name_zh},
        }

    def elsewhere(self) -> dict:
        """One feature far outside the region.

        A group a test does not care about still has to be a legal, *non-empty*
        FeatureCollection, because `read_feature_collection` refuses an empty
        one — that is how a portal serving an error body with a 200 status is
        caught. Putting the filler outside the region keeps it out of the
        results instead of quietly adding a node to every test.
        """
        return self.feature(-5000.0, 305.0, "Urban", "Elsewhere", "他處")

    def write(self, source_id: str, features: list[dict]) -> None:
        self.write_raw(source_id, json.dumps({"type": "FeatureCollection", "features": features}))

    def write_raw(self, source_id: str, body: str) -> None:
        """Put arbitrary bytes where a fetch would have left the dataset.

        The path has to match `fetch.source_artefact`'s layout, so it is built
        once here rather than at each call site.
        """
        directory = self.sources / self.city.id / source_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{source_id}.geojson").write_text(body, encoding="utf-8")

    def run(self):
        return build_region(
            self.city,
            REGION,
            sources_root=self.sources,
            out_root=self.out_root,
        )

    def __call__(self, stands: list[dict] | None = None, points: list[dict] | None = None):
        self.write("stands", stands if stands is not None else [self.elsewhere()])
        self.write("points", points if points is not None else [self.elsewhere()])
        return self.run()


@pytest.fixture
def testville(tmp_path):
    cities = tmp_path / "cities"
    cities.mkdir()
    (cities / "testville.yaml").write_text(CITY_YAML, encoding="utf-8")
    city = load_city("testville", cities_root=cities)

    out_root = tmp_path / "out"
    out_dir = city.out_dir(REGION, out_root)
    out_dir.mkdir(parents=True)
    (out_dir / ROADGRAPH_NAME).write_text(
        json.dumps(
            {
                "schema_version": ROADGRAPH_SCHEMA,
                "city_id": "testville",
                "region_id": REGION,
                "nodes": [
                    {"id": 0, "pos": [100.0, 0.0, 300.0], "kind": "endpoint"},
                    {"id": 1, "pos": [500.0, 0.0, 300.0], "kind": "endpoint"},
                ],
                # The first runs east-west through the middle; the second is a
                # spur far enough away that nothing in these tests reaches it.
                # Ids again chosen not to match their list positions.
                "edges": [
                    {
                        **_road([[100.0, 0.0, 300.0], [500.0, 0.0, 300.0]]),
                        "id": _FIRST_EDGE_ID,
                    },
                    {
                        **_road([[100.0, 0.0, 50.0], [500.0, 0.0, 50.0]]),
                        "id": _FIRST_EDGE_ID + 1,
                    },
                ],
                "turn_restrictions": [],
            }
        ),
        encoding="utf-8",
    )

    transform = city.game_transform(REGION)
    back = transformer(city.projected_crs, "EPSG:4326")

    def at(x: float, z: float) -> list[float]:
        """A game position as the lon/lat a source dataset would publish."""
        easting, northing, _ = transform.to_source(x, 0.0, z)
        return list(back.transform(easting, northing))

    return _Testville(city, out_root, tmp_path / "sources", at)


def _written(out_dir: Path) -> dict:
    return json.loads((out_dir / FARES_NAME).read_text(encoding="utf-8"))


class TestTheSideAndHeadingASnapPublishes:
    """`offset_m` and `heading_deg`, added for `P3-15`.

    ⚠️ **Asserted against `surface.mitres` itself rather than against the
    comment beside them**, the same discipline `test_kerbside.py` applies to the
    side convention it shares. A sign flip here mirrors every side-keyed feature
    that reads this — today the turn arrows — and still renders as a city.
    """

    def _northward(self):
        """An edge running north: `-Z` is north, so it runs from +Z to 0."""
        return [
            {
                "id": 0,
                "polyline": [[0.0, 0.0, 10.0], [0.0, 0.0, 0.0]],
                "lanes": 2,
                "direction": "forward",
                "elevation_level": 0,
            }
        ]

    def test_the_nearside_is_the_side_mitres_offsets_towards(self):
        import numpy as np

        from pipeline.surface import mitres

        points = np.asarray(self._northward()[0]["polyline"], dtype=np.float64)
        # `mitres` offsets to the left of travel, which is what makes `U = 0`
        # the nearside. Travelling north, left is west, so its X is negative.
        assert mitres(points)[0][0] < 0.0

        segments = Segments.of(self._northward())
        west = segments.nearest(-3.0, 5.0)
        east = segments.nearest(3.0, 5.0)
        assert west.offset_m > 0.0, "west of a northbound edge is its nearside"
        assert east.offset_m < 0.0

    def test_the_offset_magnitude_is_the_distance(self):
        segments = Segments.of(self._northward())
        snap = segments.nearest(-3.0, 5.0)
        assert abs(snap.offset_m) == pytest.approx(snap.distance_m)

    def test_a_point_past_the_end_measures_to_the_end_not_to_the_extension(self):
        """⚠️ The magnitude comes from the clamped projection on purpose.

        A point beyond a segment's end is that far from the *road*, not that far
        from its infinite extension, and the two differ by metres exactly where
        an arrow near a junction sits.
        """
        segments = Segments.of(self._northward())
        snap = segments.nearest(0.0, -4.0)
        assert snap.distance_m == pytest.approx(4.0)

    def test_the_heading_is_clockwise_from_north(self):
        segments = Segments.of(self._northward())
        assert segments.nearest(0.0, 5.0).heading_deg == pytest.approx(0.0)

        eastward = [
            {
                "id": 0,
                "polyline": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]],
                "lanes": 2,
                "direction": "forward",
                "elevation_level": 0,
            }
        ]
        assert Segments.of(eastward).nearest(5.0, 0.0).heading_deg == pytest.approx(90.0)


class TestBuildRegion:
    def test_it_writes_a_schema_stamped_document(self, testville) -> None:
        testville()
        document = _written(testville.out_dir)

        assert document["schema_version"] == FARES_SCHEMA
        assert document["city_id"] == "testville"
        assert document["region_id"] == REGION

    def test_every_node_resolves_to_an_edge(self, testville) -> None:
        """The task's acceptance criterion, checked against the graph itself."""
        feature = testville.feature
        report = testville(
            [
                feature(150.0, 304.0, "Urban Taxi Stand", "West stand", "西站"),
                feature(450.0, 296.0, "Cross Harbour Taxi Stand", "East stand", "東站"),
            ],
            [feature(300.0, 303.0, "Taxi PU/DF", "Middle point", "中點")],
        )
        published = json.loads((testville.out_dir / ROADGRAPH_NAME).read_text())
        edges = {edge["id"] for edge in published["edges"]}

        assert report.unsnapped == 0
        assert len(report.nodes) == 3
        for node in report.nodes:
            assert node.nearest_edge in edges

    def test_the_cross_harbour_category_survives(self, testville) -> None:
        feature = testville.feature
        report = testville(
            [feature(450.0, 296.0, "Cross Harbour Taxi Stand", "East stand", "東站")]
        )
        stand = next(node for node in report.nodes if node.name["en"] == "East stand")

        assert stand.stand_category == "cross_harbour"

    def test_an_operating_time_note_does_not_hide_the_category(self, testville) -> None:
        """The spelling that makes matching a substring rather than an equality:
        the publisher glues a time restriction on after a newline."""
        feature = testville.feature
        report = testville(
            [
                feature(
                    450.0,
                    296.0,
                    "Cross Harbour Taxi Stand\n(1200-0600 daily)",
                    "Russell Street",
                    "羅素街",
                )
            ],
        )
        assert report.nodes[0].stand_category == "cross_harbour"

    def test_an_unknown_category_stops_the_build(self, testville) -> None:
        """Rather than filing it under a default. These datasets are
        republished twice a year, and a silently mis-filed premium stand is a
        fare type quietly missing from the game."""
        feature = testville.feature
        with pytest.raises(KeyError, match="matches no rule"):
            testville([feature(200.0, 305.0, "Hovercraft Stand", "Odd", "怪")])

    def test_names_are_populated_in_both_languages(self, testville) -> None:
        feature = testville.feature
        report = testville(
            [feature(200.0, 305.0, "Urban", "Yun Ping Road", "恩平道")],
            [feature(300.0, 305.0, "Taxi PU/DF", "Johnston Road", "莊士敦道")],
        )
        assert report.unnamed == 0
        for node in report.nodes:
            assert node.name["en"] and node.name["zh"]

    def test_a_name_wrapped_across_lines_is_joined(self, testville) -> None:
        """`Location_EN` carries newlines in 31 of the territory's points, and
        a fare node's name goes on the HUD."""
        feature = testville.feature
        report = testville(
            [feature(200.0, 305.0, "Urban", "Hennessy Road (W/B) outside \nYing King", "軒尼詩道")],
        )
        assert report.nodes[0].name["en"] == "Hennessy Road (W/B) outside Ying King"

    def test_full_width_brackets_survive_in_chinese_names(self, testville) -> None:
        """NFKC would flatten these to ASCII, which is wrong typography in the
        98 territory-wide names that use them."""
        feature = testville.feature
        # The full-width brackets below are the point of the test, so ruff's
        # ambiguous-character rule is silenced rather than obeyed here.
        stand = feature(200.0, 305.0, "Urban", "Admiralty (1)", "金鐘港鐵站（1）")  # noqa: RUF001
        report = testville([stand])

        assert report.nodes[0].name["zh"] == "金鐘港鐵站（1）"  # noqa: RUF001

    def test_a_drop_off_only_point_may_not_be_hailed_at(self, testville) -> None:
        """A quarter of the published points are drop-off only, and the rule
        order in the city file is what keeps `Taxi DF` from matching PU/DF."""
        feature = testville.feature
        report = testville(
            points=[
                feature(250.0, 303.0, "Taxi DF", "Drop only", "落客"),
                feature(350.0, 303.0, "Taxi PU/DF", "Both", "上落客"),
            ],
        )
        by_name = {node.name["en"]: node for node in report.nodes}

        assert (by_name["Drop only"].pickup, by_name["Drop only"].dropoff) == (False, True)
        assert (by_name["Both"].pickup, by_name["Both"].dropoff) == (True, True)

    def test_a_stand_category_is_not_written_for_a_pick_up_point(self, testville) -> None:
        """`stand_category` is null unless the kind is `taxi_stand`, per the
        data contract."""
        feature = testville.feature
        testville(points=[feature(300.0, 305.0, "Taxi PU/DF", "Point", "點")])
        node = _written(testville.out_dir)["nodes"][0]

        assert node["kind"] == "pudo"
        assert node["stand_category"] is None

    def test_points_outside_the_region_are_dropped(self, testville) -> None:
        """These are whole-territory datasets — 764 of Hong Kong's 793 points
        are somewhere else."""
        feature = testville.feature
        report = testville(
            [
                feature(200.0, 305.0, "Urban", "Inside", "內"),
                feature(-500.0, 305.0, "Urban", "Far west", "遠西"),
            ],
            # Supplied so the fixture adds no out-of-region filler of its own,
            # and the count below is exactly the one feature this test placed.
            points=[feature(300.0, 305.0, "Taxi PU/DF", "Also inside", "亦內")],
        )
        assert report.outside == 1
        assert [node.name["en"] for node in report.nodes] == ["Inside", "Also inside"]

    def test_a_point_too_far_from_any_road_is_dropped_and_counted(self, testville) -> None:
        """`max_snap_m` is 30 in the fixture; this one is 150 m from the
        nearest edge, which is a car park rather than a kerbside."""
        feature = testville.feature
        report = testville([feature(300.0, 175.0, "Urban", "Adrift", "漂")])

        assert report.unsnapped == 1
        assert report.nodes == []

    def test_the_position_kept_is_the_source_one(self, testville) -> None:
        """Not the snapped one. The kerbside is where the passenger stands, and
        11 of the region's 29 points are outside even the widened carriageway —
        the on-road position is recoverable from `nearest_edge` and `edge_t`,
        this is not."""
        feature = testville.feature
        testville([feature(200.0, 308.0, "Urban", "North side", "北")])
        node = _written(testville.out_dir)["nodes"][0]

        assert node["pos"][0] == pytest.approx(200.0, abs=0.01)
        assert node["pos"][2] == pytest.approx(308.0, abs=0.01)
        # Height, though, comes off the road it attached to.
        assert node["pos"][1] == pytest.approx(0.0)

    def test_ids_are_sequential_across_every_group(self, testville) -> None:
        feature = testville.feature
        testville(
            [feature(150.0, 305.0, "Urban", "A", "甲"), feature(250.0, 305.0, "Urban", "B", "乙")],
            [feature(350.0, 305.0, "Taxi PU/DF", "C", "丙")],
        )
        assert [node["id"] for node in _written(testville.out_dir)["nodes"]] == [
            "f_001",
            "f_002",
            "f_003",
        ]

    def test_a_non_point_feature_is_skipped_rather_than_failing_the_build(self, testville) -> None:
        feature = testville.feature
        drawn_as_an_area = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0]]]},
            "properties": {"STATUS": "Urban", "NAME_EN": "Area", "NAME_ZH": "區"},
        }
        report = testville([drawn_as_an_area, feature(200.0, 305.0, "Urban", "Ok", "好")])

        assert [node.name["en"] for node in report.nodes] == ["Ok"]

    def test_a_stale_road_graph_is_refused(self, testville) -> None:
        graph = testville.out_dir / ROADGRAPH_NAME
        document = json.loads(graph.read_text())
        document["schema_version"] = ROADGRAPH_SCHEMA + 1
        graph.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(ValueError, match="schema_version"):
            testville([])

    def test_an_error_page_served_with_a_200_is_refused(self, testville) -> None:
        """The portal these come from answers an outage with JSON, and a cached
        error body would look like a region with no fare nodes for ever."""
        testville.write_raw("stands", json.dumps({"error": "rate limited"}))

        with pytest.raises(ValueError, match="FeatureCollection"):
            testville.run()


class TestEdgePositions:
    def test_the_fraction_matches_where_the_point_actually_is(self, testville) -> None:
        """A stand a quarter of the way along a 400 m road reports t=0.25, so
        the game can place the pickup without redoing the projection."""
        feature = testville.feature
        report = testville([feature(200.0, 304.0, "Urban", "Quarter", "四分一")])

        assert report.nodes[0].edge_t == pytest.approx(0.25, abs=1e-4)
        assert report.nodes[0].nearest_edge == _FIRST_EDGE_ID

    def test_interpolating_the_edge_at_the_fraction_returns_the_snap(self, testville) -> None:
        """The property that makes `edge_t` usable: walk the polyline that far
        and you arrive beside the node."""
        feature = testville.feature
        report = testville([feature(370.0, 296.0, "Urban", "Somewhere", "某處")])
        node = report.nodes[0]

        published = json.loads((testville.out_dir / ROADGRAPH_NAME).read_text())["edges"]
        # Looked up by id rather than indexed by it — `nearest_edge` is an id,
        # and this test would pass either way if the fixture numbered edges by
        # their position.
        edge = next(edge for edge in published if edge["id"] == node.nearest_edge)
        polyline = np.asarray(edge["polyline"], dtype=float)
        steps = np.hypot(*np.diff(polyline[:, [0, 2]], axis=0).T)
        walked = np.interp(
            node.edge_t * steps.sum(),
            np.concatenate([[0.0], np.cumsum(steps)]),
            polyline[:, 0],
        )
        assert walked == pytest.approx(node.pos[0], abs=0.01)
