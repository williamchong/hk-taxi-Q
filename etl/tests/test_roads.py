"""Road graph construction (`P1-3`).

The unit tests cover the four source quirks that shaped the stage — endpoints
that agree only once rounded, features that leave the region, geometry densified
to a fraction of a millimetre, and a null sentinel written four different ways.
The integration test then builds a whole graph from a synthetic geodatabase, so
the wiring between them is exercised rather than assumed.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import numpy as np
import pytest

from pipeline.config import load_city
from pipeline.roads import (
    Edge,
    build_region,
    clean_text,
    clip,
    parse_speed_limit,
    simplify,
)
from tests.helpers import NULL_SENTINELS, line_wkb, write_layer


class TestSimplify:
    def test_collinear_vertices_are_dropped(self) -> None:
        line = np.array([(x, 0.0) for x in range(20)], dtype=np.float64)
        np.testing.assert_array_equal(simplify(line, 0.2), np.array([(0.0, 0.0), (19.0, 0.0)]))

    def test_no_vertex_moves_further_than_the_tolerance(self) -> None:
        """Douglas-Peucker's guarantee, and the reason the tolerance can be
        stated in metres in city config rather than tuned by eye."""
        rng = np.random.default_rng(7)
        line = np.column_stack([np.arange(400.0), rng.normal(0.0, 1.5, 400)])
        kept = simplify(line, 0.25)

        assert len(kept) < len(line)
        for point in line:
            starts, ends = kept[:-1], kept[1:]
            spans = ends - starts
            travel = np.clip(((point - starts) * spans).sum(axis=1) / (spans**2).sum(axis=1), 0, 1)
            closest = np.linalg.norm(point - (starts + travel[:, None] * spans), axis=1).min()
            assert closest <= 0.25 + 1e-9

    def test_endpoints_are_never_moved(self) -> None:
        """What makes it safe to simplify before snapping: the coordinates two
        edges meet at are exactly the ones this cannot touch."""
        line = np.array([(0.0, 0.0), (5.0, 0.001), (10.0, 0.0)])
        kept = simplify(line, 1.0)

        np.testing.assert_array_equal(kept[0], line[0])
        np.testing.assert_array_equal(kept[-1], line[-1])

    def test_a_closed_loop_keeps_its_shape(self) -> None:
        """A roundabout drawn as one feature starts and ends at the same point,
        so there is no chord to measure against and the naive implementation
        collapses it to nothing."""
        angles = np.linspace(0.0, 2.0 * np.pi, 33)
        loop = np.column_stack([20.0 * np.cos(angles), 20.0 * np.sin(angles)])

        kept = simplify(loop, 0.5)
        assert len(kept) > 8
        assert np.linalg.norm(kept, axis=1).min() > 15.0

    def test_a_heavily_densified_line_does_not_exhaust_the_stack(self) -> None:
        """One centreline in Wan Chai carries 54,330 vertices over 51.7 m. A
        recursive implementation is a stack overflow on exactly that input."""
        line = np.column_stack([np.linspace(0.0, 50.0, 60_000), np.zeros(60_000)])
        assert len(simplify(line, 0.2)) == 2

    def test_a_zero_tolerance_changes_nothing(self) -> None:
        line = np.array([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
        np.testing.assert_array_equal(simplify(line, 0.0), line)


class TestClip:
    HIGH = (100.0, 100.0)

    def test_a_line_wholly_inside_is_returned_unchanged(self) -> None:
        line = np.array([(10.0, 10.0), (20.0, 30.0)])
        runs = clip(line, self.HIGH, min_length_m=2.0)

        assert len(runs) == 1
        np.testing.assert_array_equal(runs[0], line)

    def test_a_line_leaving_the_region_is_cut_at_the_boundary(self) -> None:
        runs = clip(np.array([(50.0, 50.0), (150.0, 50.0)]), self.HIGH, min_length_m=2.0)

        assert len(runs) == 1
        np.testing.assert_allclose(runs[0], [(50.0, 50.0), (100.0, 50.0)])

    def test_a_line_that_leaves_and_returns_becomes_two_runs(self) -> None:
        """One source feature, two drivable stretches, and no edge joining them
        through ground the player cannot reach."""
        line = np.array([(50.0, 50.0), (150.0, 50.0), (150.0, 20.0), (50.0, 20.0)])
        runs = clip(line, self.HIGH, min_length_m=2.0)

        assert len(runs) == 2
        np.testing.assert_allclose(runs[0][-1], (100.0, 50.0))
        np.testing.assert_allclose(runs[1][0], (100.0, 20.0))

    def test_a_line_wholly_outside_produces_nothing(self) -> None:
        """The geodatabase filters on bounding box, so a long feature can be
        selected without ever entering the region."""
        assert clip(np.array([(200.0, 200.0), (300.0, 300.0)]), self.HIGH, min_length_m=2.0) == []

    def test_a_stub_shorter_than_the_minimum_is_dropped(self) -> None:
        line = np.array([(99.0, 150.0), (99.0, 99.5), (150.0, 99.5)])
        assert clip(line, self.HIGH, min_length_m=2.0) == []

    def test_a_line_along_the_boundary_is_kept(self) -> None:
        """Parallel to an edge is the case Liang-Barsky divides by zero on."""
        line = np.array([(0.0, 10.0), (0.0, 90.0)])
        runs = clip(line, self.HIGH, min_length_m=2.0)

        assert len(runs) == 1
        np.testing.assert_allclose(runs[0], line)


class TestAttributes:
    @pytest.mark.parametrize("value", [*NULL_SENTINELS, None, "", "   "])
    def test_every_spelling_of_the_null_sentinel_reads_as_none(self, value) -> None:
        """The Chinese name field writes it with full-width digits and an
        en-dash. Comparing the raw string catches one of the four."""
        assert clean_text(value, ("-99",)) is None

    def test_a_real_name_survives_normalisation(self) -> None:
        assert clean_text("HENNESSY ROAD", ("-99",)) == "HENNESSY ROAD"
        assert clean_text("軒尼詩道", ("-99",)) == "軒尼詩道"

    def test_a_name_that_merely_contains_the_sentinel_is_kept(self) -> None:
        assert clean_text("ROUTE -99A", ("-99",)) == "ROUTE -99A"

    @pytest.mark.parametrize(
        ("value", "expected"), [("70 km/h", 70), ("80km/h", 80), ("50", 50), (None, 50), ("", 50)]
    )
    def test_speed_limits_parse_out_of_their_units(self, value, expected) -> None:
        assert parse_speed_limit(value, 50) == expected


class TestLanes:
    def test_the_fastest_matching_rule_wins(self, hong_kong) -> None:
        roads = hong_kong.roads
        assert roads.lanes_for(50) == roads.lanes_default
        assert roads.lanes_for(70) == 3
        assert roads.lanes_for(80) == 3


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------

# A 1 km square of made-up city, far enough east to be inside the declared
# bounds and metric throughout, so expected coordinates can be worked out by
# hand rather than read back off the output.
_CITY = textwrap.dedent(
    """
    schema_version: 1
    id: testville
    name: Testville
    crs:
      projected: EPSG:2326
      geodetic: EPSG:4326
    elevation_levels:
      -1: -8.0
      0: 0.0
      1: 6.0
    bounds: {west: 114.00, east: 114.30, south: 22.20, north: 22.40}
    regions:
      middle:
        name: Middle
        bounds: {west: 114.170, east: 114.180, south: 22.276, north: 22.282}
        tile_size_m: 150.0
    sources:
      roads: https://example.test/roads.gpkg
    buildings:
      classes: [BUILDING]
      terrain_class: TERRAIN
      class_colours: {}
      height_bands:
        - {up_to_m: .inf, colour: "#808080"}
      colour_jitter: 0.0
      lod_cell_sizes_m: [0.0]
    roads:
      source: roads
      centrelines:
        layer: CENTERLINE
        fields:
          elevation: ELEVATION
          travel_direction: TRAVEL_DIRECTION
          route: ROUTE_ID
          name_en: STREET_ENAME
          name_zh: STREET_CNAME
      turns:
        layer: TURN
        fields:
          first_edge: EDGE1FID
          first_end: EDGE1END
          second_edge: EDGE2FID
      speed_limits:
        layer: SPEED_LIMIT
        fields: {route: ROAD_ROUTE_ID, speed_limit: SPEED_LIMIT}
      bus_lanes:
        layer: BUS_ONLY_LANE
        fields: {route: ROAD_ROUTE_ID}
      travel_directions:
        1: both
        3: forward
      turn_at_end_value: "Y"
      null_values: ["-99"]
      default_speed_limit_kph: 50
      simplify_tolerance_m: 0.2
      min_edge_length_m: 2.0
      lanes_default: 2
      lanes_by_min_speed_limit_kph: {70: 3}
      lane_width_m: 3.2
      tram_streets: [TRAM STREET]
      ground: datum
    """
)


@pytest.fixture
def testville(tmp_path):
    """A whole city — config, geodatabase and all — under `tmp_path`."""
    cities = tmp_path / "cities"
    cities.mkdir()
    (cities / "testville.yaml").write_text(_CITY, encoding="utf-8")
    city = load_city("testville", cities_root=cities)

    transform = city.game_transform("middle")

    def at(x: float, z: float) -> tuple[float, float]:
        """Region-local game metres to source easting/northing.

        Through the transform rather than off the projected bounds: the origin
        is rounded outward to whole metres, so the two differ by up to a metre
        and the expected coordinates below are stated exactly.
        """
        easting, northing, _ = transform.to_source(x, 0.0, z)
        return (easting, northing)

    gpkg = tmp_path / "sources" / "testville" / "roads" / "roads.gpkg"
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
        "TURN",
        [line_wkb([at(250.0, 100.0), at(300.0, 250.0)])],
        {
            "EDGE1FID": np.array([1]),
            "EDGE1END": np.array(["Y"], dtype=object),
            "EDGE2FID": np.array([3]),
        },
    )
    return city, tmp_path


def _graph(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "out" / "testville" / "middle" / "roadgraph.json").read_text())


class TestBuildRegion:
    def test_it_writes_a_graph_matching_the_contract(self, testville) -> None:
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )
        document = _graph(tmp_path)

        assert document["schema_version"] == 1
        assert len(document["edges"]) == len(report.edges) == 4
        assert {key for edge in document["edges"] for key in edge} == {
            "id",
            "from",
            "to",
            "polyline",
            "direction",
            "lanes",
            "width_m",
            "speed_limit_kph",
            "bus_lane",
            "tram_tracks",
            "elevation_level",
            "road_name",
        }

    def test_shared_endpoints_become_one_node(self, testville) -> None:
        """Three centrelines meet at (300, 100). If they did not collapse onto
        one node, the junction would not exist and nothing could turn there."""
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )

        junctions = [node for node in report.nodes if node.kind == "junction"]
        assert len(junctions) == 1
        assert junctions[0].pos[0] == pytest.approx(300.0, abs=0.01)
        assert junctions[0].pos[2] == pytest.approx(100.0, abs=0.01)

    def test_a_flyover_still_joins_the_road_it_ramps_off(self, testville) -> None:
        """The level-1 edge shares its start with two level-0 edges. Keying
        nodes on the level as well as the position would sever it — which is
        what happens to Wan Chai's whole elevated network if you try."""
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )

        elevated = next(edge for edge in report.edges if edge.elevation_level == 1)
        ground = [edge for edge in report.edges if edge.elevation_level == 0]
        assert any(elevated.from_node in (edge.from_node, edge.to_node) for edge in ground)
        assert report.connectivity == 1.0

    def test_deck_height_comes_from_the_elevation_level(self, testville) -> None:
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )

        heights = {edge.elevation_level: edge.polyline[0][1] for edge in report.edges}
        assert heights[0] == pytest.approx(0.0)
        assert heights[1] == pytest.approx(6.0)

    def test_an_edge_leaving_the_region_is_cut_at_the_boundary(self, testville) -> None:
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )

        max_x = max(point[0] for edge in report.edges for point in edge.polyline)
        assert max_x < 1100.0
        assert max_x == pytest.approx(city.projected_bounds("middle").width_m, abs=1.0)

    def test_attributes_are_joined_from_their_own_layers(self, testville) -> None:
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )
        flyover = next(edge for edge in report.edges if edge.elevation_level == 1)
        street = next(
            edge
            for edge in report.edges
            if edge.road_name["en"] == "MAIN STREET" and edge.elevation_level == 0
        )

        assert flyover.speed_limit_kph == 70
        assert flyover.lanes == 3
        assert flyover.width_m == pytest.approx(9.6)
        assert flyover.bus_lane is False
        assert street.speed_limit_kph == 50
        assert street.lanes == 2
        assert street.bus_lane is True

    def test_names_are_bilingual_and_sentinels_become_null(self, testville) -> None:
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )
        names = [edge.road_name for edge in report.edges]

        assert {"en": "MAIN STREET", "zh": "大街"} in names
        assert {"en": None, "zh": None} in names

    def test_tram_streets_are_flagged_from_the_authored_list(self, testville) -> None:
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )

        assert [edge.road_name["en"] for edge in report.edges if edge.tram_tracks] == [
            "TRAM STREET"
        ]

    def test_a_turn_restriction_resolves_to_edges_and_the_node_between_them(
        self, testville
    ) -> None:
        city, tmp_path = testville
        report = build_region(
            city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out"
        )

        assert len(report.turn_restrictions) == 1
        turn = report.turn_restrictions[0]
        first, second = report.edges[turn.from_edge], report.edges[turn.to_edge]
        assert turn.via_node in (first.from_node, first.to_node)
        assert turn.via_node in (second.from_node, second.to_node)
        assert report.turns_unresolved == 0

    def test_a_one_way_direction_survives_into_the_output(self, testville) -> None:
        city, tmp_path = testville
        build_region(city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out")
        document = _graph(tmp_path)

        directions = sorted(edge["direction"] for edge in document["edges"])
        assert directions == ["both", "forward", "forward", "forward"]

    def test_positions_carry_no_negative_zero(self, testville) -> None:
        """A vertex clipped to the western edge lands on -0.0, which is legal
        JSON and a confusing thing to find in a file whose premise is that the
        region starts at zero."""
        city, tmp_path = testville
        build_region(city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out")

        raw = (tmp_path / "out" / "testville" / "middle" / "roadgraph.json").read_text()
        assert "-0.0" not in raw

    def test_an_unmapped_travel_direction_is_an_error(self, testville, tmp_path) -> None:
        """A defaulted direction makes a one-way street two-way, which reads as
        plausible output and is a head-on collision in play."""
        city, sources = testville
        broken = {**city.roads.travel_directions}
        broken.pop(3)
        city = _with_directions(city, broken)

        with pytest.raises(KeyError, match="travel direction 3"):
            build_region(city, "middle", sources_root=sources / "sources", out_root=sources / "out")

    def test_a_missing_geodatabase_names_the_fetch_command(self, testville) -> None:
        city, tmp_path = testville
        with pytest.raises(FileNotFoundError, match=r"pipeline\.fetch"):
            build_region(city, "middle", sources_root=tmp_path / "empty", out_root=tmp_path / "out")


def _with_directions(city, directions):
    from dataclasses import replace

    return replace(city, roads=replace(city.roads, travel_directions=directions))


class TestEdgeIdentity:
    def test_edge_ids_are_dense_and_index_their_own_list(self) -> None:
        """`turn_restrictions` addresses edges by id, so the game can index the
        array directly only if the two agree."""
        edges = [
            Edge(
                id=index,
                source_id=index,
                from_node=index,
                to_node=index + 1,
                polyline=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
                direction="both",
                lanes=2,
                width_m=6.4,
                speed_limit_kph=50,
                bus_lane=False,
                tram_tracks=False,
                elevation_level=0,
                road_name={"en": None, "zh": None},
            )
            for index in range(5)
        ]
        assert [edge.id for edge in edges] == list(range(len(edges)))


class TestClipGuards:
    """Cases the fast path used to answer differently from the slow one."""

    HIGH = (100.0, 100.0)

    def test_a_short_line_inside_the_region_is_dropped_like_a_short_stub(self) -> None:
        """The whole-array fast path applies the same minimum length as the
        walk. Two paths through one function must not carry two policies."""
        inside = np.array([(50.0, 50.0), (50.5, 50.0)])
        crossing = np.array([(99.5, 50.0), (150.0, 50.0)])

        assert clip(inside, self.HIGH, min_length_m=2.0) == []
        assert clip(crossing, self.HIGH, min_length_m=2.0) == []

    @pytest.mark.parametrize("points", [np.zeros((0, 2)), np.array([(10.0, 10.0)])])
    def test_geometry_too_short_to_be_a_road_yields_nothing(self, points) -> None:
        """A NULL or single-vertex geometry is legal in a geodatabase. Passed
        through, it reaches `polyline[0]` and `polyline[-1]` on the same vertex
        and builds a zero-length edge — or, when empty, an IndexError with no
        indication of which feature caused it."""
        assert clip(points, self.HIGH, min_length_m=2.0) == []

    def test_a_re_entry_within_one_segment_is_not_merged_by_a_loose_tolerance(self) -> None:
        """The join test is absolute metres. Through `np.allclose` the default
        `rtol=1e-5` widens it to ~15 mm at the far edge of a 1.5 km region, and
        two runs 10 mm apart merge into one segment crossing outside."""
        far = (1500.0, 1500.0)
        line = np.array([(1499.99, 700.0), (1600.0, 700.0), (1600.0, 700.01), (1499.99, 700.01)])
        runs = clip(line, far, min_length_m=0.0)

        assert len(runs) == 2


class TestSpeedLimitParsing:
    @pytest.mark.parametrize("value", ["Route 4, 70 km/h", "-70", "km/h"])
    def test_a_value_that_does_not_start_with_a_number_falls_back(self, value) -> None:
        """Unanchored, `Route 4, 70 km/h` reads as a 4 km/h speed limit."""
        assert parse_speed_limit(value, 50) == 50
