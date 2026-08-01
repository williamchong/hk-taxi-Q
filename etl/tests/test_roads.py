"""Road graph construction (`P1-3`).

The unit tests cover the four source quirks that shaped the stage — endpoints
that agree only once rounded, features that leave the region, geometry densified
to a fraction of a millimetre, and a null sentinel written four different ways.
The integration test then builds a whole graph from a synthetic geodatabase, so
the wiring between them is exercised rather than assumed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from pipeline.config import DeckSampling
from pipeline.gltf import MeshData
from pipeline.roads import (
    ROADGRAPH_SCHEMA,
    Edge,
    _Counts,
    _Deck,
    _deck_heights,
    _lifted_heights,
    _mixed_level_nodes,
    _node_heights,
    build_region,
    clean_text,
    clip,
    parse_speed_limit,
    resample,
    simplify,
)
from pipeline.terrain import HeightField
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

    def test_full_width_brackets_are_not_flattened_to_ascii(self) -> None:
        """NFKC folds the sentinel's full-width digits, and would fold these
        too — but they are correct typography in Chinese, and `P1-5`'s fare
        node names go on a bilingual HUD. So the value is NFC and only the
        sentinel comparison is NFKC."""
        assert clean_text("金鐘港鐵站（1）", ("-99",)) == "金鐘港鐵站（1）"  # noqa: RUF001

    def test_a_name_wrapped_across_lines_becomes_one_line(self) -> None:
        """The taxi datasets wrap long place names; 31 of the territory's 793
        points carry a newline inside the name."""
        assert clean_text("Hennessy Road \noutside  Ying King", ()) == (
            "Hennessy Road outside Ying King"
        )

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


@pytest.fixture
def testville(tmp_path, testville_config):
    """A whole city — config, geodatabase and all — under `tmp_path`."""
    city = testville_config

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

        assert document["schema_version"] == ROADGRAPH_SCHEMA
        assert len(document["edges"]) == len(report.edges) == 4
        assert {key for edge in document["edges"] for key in edge} == {
            "id",
            "from",
            "to",
            "polyline",
            "on_structure",
            "direction",
            "lanes",
            "width_m",
            "speed_limit_kph",
            "bus_lane",
            "tram_tracks",
            "elevation_level",
            "road_name",
        }

    def test_on_structure_is_parallel_to_the_polyline(self, testville) -> None:
        """`surface.py` indexes one against the other to pick a per-station
        width (`Q23`), so a length that drifts is a silently wrong carriageway
        rather than an error. Nothing else in the document has this property,
        which is why it is asserted rather than assumed."""
        city, tmp_path = testville
        build_region(city, "middle", sources_root=tmp_path / "sources", out_root=tmp_path / "out")

        for edge in _graph(tmp_path)["edges"]:
            assert len(edge["on_structure"]) == len(edge["polyline"]), edge["id"]
            assert all(isinstance(flag, bool) for flag in edge["on_structure"])

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
                on_structure=[False, False],
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


class TestResample:
    """Stations added for `P2-7`'s deck sampling, without redrawing the road.

    The property that matters is not the spacing — it is that the line's plan
    shape is untouched. Restating a polyline at evenly spaced stations is the
    obvious implementation and it silently cuts every corner `simplify` just
    decided to keep, which no height measurement would ever reveal.
    """

    def test_every_original_vertex_survives_exactly(self) -> None:
        plan = np.array([[0.0, 0.0], [30.0, 0.0], [30.0, 7.0], [61.5, 7.0]])
        stationed = resample(plan, 10.0)

        for vertex in plan:
            assert any(np.array_equal(vertex, station) for station in stationed), vertex

    def test_no_station_gap_exceeds_the_spacing(self) -> None:
        plan = np.array([[0.0, 0.0], [71.5, 0.0], [71.5, 3.0]])
        steps = np.hypot(*np.diff(resample(plan, 10.0), axis=0).T)

        assert steps.max() <= 10.0 + 1e-9

    def test_a_corner_is_not_cut(self) -> None:
        """A right angle whose sides are shorter than the spacing. Resampling by
        arc length alone would return the two endpoints and a straight line
        between them, moving the road 7 m sideways."""
        plan = np.array([[0.0, 0.0], [7.0, 0.0], [7.0, 7.0]])
        np.testing.assert_array_equal(resample(plan, 10.0), plan)

    def test_a_line_already_dense_enough_is_returned_unchanged(self) -> None:
        plan = np.array([[0.0, 0.0], [4.0, 0.0], [8.0, 0.0]])
        assert resample(plan, 10.0) is plan

    @pytest.mark.parametrize("spacing", [0.0, -1.0])
    def test_a_spacing_that_asks_for_nothing_changes_nothing(self, spacing: float) -> None:
        """Zero would otherwise ask for infinitely many stations. `config.py`
        refuses it, so this is the second line of that defence rather than the
        first — but the caller is a loop over every edge in the region."""
        plan = np.array([[0.0, 0.0], [100.0, 0.0]])
        assert resample(plan, spacing) is plan

    def test_a_repeated_vertex_does_not_divide_by_zero(self) -> None:
        plan = np.array([[0.0, 0.0], [0.0, 0.0], [40.0, 0.0]])
        stationed = resample(plan, 10.0)

        assert np.isfinite(stationed).all()
        assert len(stationed) == 6

    def test_a_line_too_short_to_have_a_segment_is_left_alone(self) -> None:
        plan = np.array([[3.0, 4.0]])
        assert resample(plan, 10.0) is plan


class TestNodeHeights:
    """One height per node, chosen rather than inherited from iteration order.

    Before `P2-7` a node took the height of whichever edge the source listed
    first. That was invisible while every edge at a level shared one flat
    offset; it stops being invisible the moment two ends are sampled
    independently, which is exactly what this task made happen.
    """

    def _edge(self, edge_id: int, level: int, nodes: tuple[int, int], y: float) -> Edge:
        return Edge(
            id=edge_id,
            source_id=edge_id,
            from_node=nodes[0],
            to_node=nodes[1],
            polyline=[(0.0, y, 0.0), (10.0, y, 0.0)],
            on_structure=[False, False],
            direction="forward",
            lanes=2,
            width_m=6.0,
            speed_limit_kph=50,
            bus_lane=False,
            tram_tracks=False,
            elevation_level=level,
            road_name={"en": None, "zh": None},
        )

    def test_a_flyover_node_takes_the_at_grade_height(self) -> None:
        """`Q13`'s shape: a ramp touching down, level 1 meeting level 0. The
        junction belongs on the street, not six metres above it."""
        edges = [self._edge(0, 1, (0, 1), 10.5), self._edge(1, 0, (1, 2), 4.2)]
        assert _node_heights(3, edges)[1] == pytest.approx(4.2)

    def test_a_tunnel_portal_takes_the_at_grade_height_too(self) -> None:
        """The other direction, which a plain minimum would get wrong: level -1
        is further from grade than level 0, so the portal stays on the street."""
        edges = [self._edge(0, -1, (0, 1), -3.8), self._edge(1, 0, (1, 2), 4.2)]
        assert _node_heights(3, edges)[1] == pytest.approx(4.2)

    def test_the_highest_end_at_the_chosen_level_wins(self) -> None:
        """`HeightField.sample`'s rule, for its reason: where a surface is
        multi-valued at a point the drivable face is the top, and a node below a
        ribbon end is a node inside the road."""
        edges = [self._edge(0, 0, (0, 1), 4.20), self._edge(1, 0, (1, 2), 4.26)]
        assert _node_heights(3, edges)[1] == pytest.approx(4.26)

    def test_the_answer_does_not_depend_on_the_order_the_edges_arrive_in(self) -> None:
        edges = [
            self._edge(0, 1, (0, 1), 10.5),
            self._edge(1, 0, (1, 2), 4.2),
            self._edge(2, 0, (1, 3), 4.1),
        ]
        assert _node_heights(4, edges) == _node_heights(4, list(reversed(edges)))

    def test_a_node_reached_only_off_grade_keeps_its_own_level(self) -> None:
        """Nearest to grade among the levels *present*, not a preference for
        zero — an elevated node with no at-grade edge belongs on the deck."""
        edges = [self._edge(0, 1, (0, 1), 10.5), self._edge(1, 1, (1, 2), 10.6)]
        assert _node_heights(3, edges)[1] == pytest.approx(10.6)


# --------------------------------------------------------------------------
# Deck sampling
# --------------------------------------------------------------------------

THRESHOLDS = DeckSampling(
    resample_m=10.0, slab_gap_m=3.0, max_below_terrain_m=1.0, at_grade_m=0.30, clearance_m=0.0
)


def _mesh(triangles: list[list[tuple[float, float, float]]]) -> MeshData:
    positions = np.array([c for triangle in triangles for c in triangle], dtype=np.float64)
    return MeshData(
        name="fixture",
        positions=positions,
        normals=np.tile(np.array([0.0, 1.0, 0.0], np.float32), (len(positions), 1)),
        triangles=np.arange(len(positions), dtype=np.uint32).reshape(-1, 3),
    )


def _sheet(x0: float, x1: float, y0: float, y1: float) -> list[MeshData]:
    """A slab spanning `x0`-`x1` across the corridor, climbing `y0` to `y1`.

    Returned as two faces, because a real deck is a closed volume and answering
    twice is the whole reason `slab_gap_m` exists — a single-surface fixture
    would pass while testing none of the clustering.
    """
    top = _mesh(
        [
            [(x0, y0, -20.0), (x1, y1, -20.0), (x0, y0, 20.0)],
            [(x1, y1, -20.0), (x1, y1, 20.0), (x0, y0, 20.0)],
        ]
    )
    return [top, top.translated((0.0, -1.5, 0.0))]


def _deck(*meshes: MeshData) -> _Deck:
    return _Deck(field=HeightField.from_meshes(list(meshes)), thresholds=THRESHOLDS)


def _straight(x_end: float, step: float = 10.0) -> np.ndarray:
    stations = np.arange(0.0, x_end + step / 2, step)
    return np.column_stack([stations, np.zeros(len(stations))])


class TestDeckHeights:
    """The off-grade sampler, which carries the task's central decision.

    Callable in isolation only since it stopped writing into a `RoadReport`,
    which is why it had no direct test until it had one.
    """

    def test_the_deck_wins_over_the_level_offset(self) -> None:
        plan = _straight(40.0)
        terrain = np.zeros(len(plan))
        deck = _deck(*_sheet(-5.0, 45.0, 5.0, 5.0))

        y, on_structure = _deck_heights(deck, plan, terrain, terrain + 6.0, _Counts())
        np.testing.assert_allclose(y, 5.0)
        assert on_structure.all(), "and every station says so, for `Q23`"

    def test_a_hole_in_the_structure_is_bridged_from_either_side(self) -> None:
        """The defect that made the first run look right and measure wrong.
        `INFRASTRUCTURE` stops being modelled where a ramp reaches grade, so at
        9 of `Q13`'s nodes the query returns nothing *at the node*. Dropping
        those stations to the flat offset rebuilds the cliff being removed."""
        plan = _straight(40.0)
        terrain = np.zeros(len(plan))
        # Structure over 0-10 and 30-40; nothing at all across the middle.
        deck = _deck(*_sheet(-1.0, 10.0, 4.0, 4.0), *_sheet(30.0, 41.0, 4.0, 4.0))

        counts = _Counts()
        y, on_structure = _deck_heights(deck, plan, terrain, terrain + 6.0, counts)

        assert counts.sampled == 4, "the four covered stations"
        np.testing.assert_allclose(y, 4.0), "and the gap holds the deck, not +6"
        assert on_structure.all(), (
            "a bridged station is on the deck — that is what the bridging claims, "
            "and `Q23` must not narrow it back to bare ground"
        )

    def test_an_edge_the_structure_never_covers_keeps_the_flat_offset(self) -> None:
        """`ISLAND EASTERN CORRIDOR`'s stub — the case the offset is right for,
        and the reason the fallback is not simply deleted."""
        plan = _straight(40.0)
        terrain = np.zeros(len(plan))
        deck = _deck(*_sheet(500.0, 520.0, 4.0, 4.0))

        counts = _Counts()
        y, on_structure = _deck_heights(deck, plan, terrain, terrain + 6.0, counts)

        assert counts.sampled == 0
        np.testing.assert_allclose(y, 6.0)
        assert not on_structure.any(), "the flat offset is not a deck"

    def test_structure_under_the_terrain_is_refused(self) -> None:
        """A deck cannot sit below the ground under it. `e425` samples 8.2 m
        under; the next lowest in the region is 0.54 m under, so the threshold
        sits in a 7.6 m gap rather than on a guess."""
        plan = _straight(20.0)
        terrain = np.zeros(len(plan))
        deck = _deck(*_sheet(-5.0, 25.0, -8.0, -8.0))

        counts = _Counts()
        y, on_structure = _deck_heights(deck, plan, terrain, terrain + 6.0, counts)

        assert counts.gated == len(plan)
        assert counts.sampled == 0
        np.testing.assert_allclose(y, 6.0)
        assert not on_structure.any()

    def test_a_sample_grazing_grade_from_below_is_kept(self) -> None:
        """The other side of that threshold: real ramp ends sample fractionally
        under the terrain, and 0.54 m of that is genuine rather than an error."""
        plan = _straight(20.0)
        terrain = np.zeros(len(plan))
        deck = _deck(*_sheet(-5.0, 25.0, -0.54, -0.54))

        counts = _Counts()
        _deck_heights(deck, plan, terrain, terrain + 6.0, counts)
        assert counts.gated == 0


class TestLiftedHeights:
    """The level-0 half, which nobody had seen until the nodes were classified."""

    def _lift(self, deck: _Deck, plan: np.ndarray, ends: tuple[bool, bool]) -> tuple:
        terrain = np.zeros(len(plan))
        counts = _Counts()
        y, on_structure = _lifted_heights(deck, plan, terrain, terrain.copy(), ends, counts)
        return y, on_structure, counts

    def test_an_edge_leaving_a_mixed_node_climbs_onto_its_ramp(self) -> None:
        plan = _straight(40.0)
        # A ramp descending 3 m over the first 30 m, then flat at grade.
        deck = _deck(*_sheet(0.0, 30.0, 3.0, 0.0), *_sheet(30.0, 41.0, 0.0, 0.0))

        y, on_structure, counts = self._lift(deck, plan, (True, False))

        assert counts.ends_lifted == 1
        assert y[0] == pytest.approx(3.0)
        assert y[-1] == pytest.approx(0.0)
        assert (np.diff(y) <= 1e-9).all(), "the lift descends to grade and stays there"
        assert on_structure[0] and not on_structure[-1], (
            "`Q23`: the lifted end is on the ramp and the far end is not, "
            "which is the whole reason width cannot be an edge attribute"
        )

    def test_the_walk_stops_where_the_structure_reaches_the_ground(self) -> None:
        """`at_grade_m` is a tolerance, not a boundary — the residual step it
        leaves behind is what bounds the value."""
        plan = _straight(40.0)
        deck = _deck(*_sheet(0.0, 10.0, 2.0, 0.0), *_sheet(10.0, 41.0, 0.0, 0.0))

        y, on_structure, _ = self._lift(deck, plan, (True, False))
        assert y[0] == pytest.approx(2.0)
        np.testing.assert_allclose(y[1:], 0.0)
        assert list(on_structure) == [True] + [False] * (len(y) - 1), (
            "the flag stops exactly where the walk does"
        )

    def test_an_edge_meeting_no_mixed_node_is_left_alone(self) -> None:
        """The rule is topological. Structure overhead is not this edge's ramp,
        and a height threshold was measured and rejected for saying otherwise."""
        plan = _straight(40.0)
        deck = _deck(*_sheet(-1.0, 41.0, 3.0, 3.0))

        y, on_structure, counts = self._lift(deck, plan, (False, False))

        assert counts.ends_lifted == 0
        np.testing.assert_allclose(y, 0.0)
        assert not on_structure.any(), "structure overhead is not structure underfoot"

    def test_an_end_already_at_grade_is_not_counted_as_lifted(self) -> None:
        plan = _straight(40.0)
        deck = _deck(*_sheet(-1.0, 41.0, 0.1, 0.1))

        _, _, counts = self._lift(deck, plan, (True, True))
        assert counts.ends_lifted == 0

    def test_an_edge_mixed_at_both_ends_is_walked_from_both(self) -> None:
        plan = _straight(40.0)
        # High at both ends, at grade across the middle. The joins sit between
        # stations rather than on one: where two slabs meet, their four faces
        # cluster into a single slab and the fixture would test nothing.
        deck = _deck(
            *_sheet(0.0, 5.0, 2.0, 2.0),
            *_sheet(5.0, 35.0, 0.0, 0.0),
            *_sheet(35.0, 41.0, 2.0, 2.0),
        )

        y, on_structure, counts = self._lift(deck, plan, (True, True))

        assert counts.ends_lifted == 2
        assert y[0] == pytest.approx(2.0)
        assert y[-1] == pytest.approx(2.0)
        assert on_structure[0] and on_structure[-1] and not on_structure[len(y) // 2]


class TestMixedLevelNodes:
    def test_a_node_two_levels_reach_is_found(self) -> None:
        edges = [
            Edge(
                id=0,
                source_id=0,
                from_node=0,
                to_node=1,
                polyline=[],
                on_structure=[],
                direction="forward",
                lanes=2,
                width_m=6.0,
                speed_limit_kph=50,
                bus_lane=False,
                tram_tracks=False,
                elevation_level=1,
                road_name={"en": None, "zh": None},
            ),
            Edge(
                id=1,
                source_id=1,
                from_node=1,
                to_node=2,
                polyline=[],
                on_structure=[],
                direction="forward",
                lanes=2,
                width_m=6.0,
                speed_limit_kph=50,
                bus_lane=False,
                tram_tracks=False,
                elevation_level=0,
                road_name={"en": None, "zh": None},
            ),
        ]
        assert _mixed_level_nodes(edges) == {1}
