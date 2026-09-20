"""The probe on `tools/join_seam.py` (`P5-7b`).

Only the parts whose failure mode is silent. A loader that read nothing prints
0 nodes, which nobody could miss; what would not announce itself is a pairing
that hands one node two partners, a candidate taken from the wrong side of the
region, or an owner count that reads 1 whatever the flags say.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from join_seam import (
    Graph,
    NodePair,
    carriageway_of,
    near_line,
    pair_nodes,
    report_crossings_by_identity,
    report_crossings_by_node,
    section,
    section_lines,
    shared_side,
)


def _graph(
    region: str,
    nodes: dict[int, tuple[float, float, float]],
    edges=(),
    *,
    high=(100.0, 50.0),
    offset=(0.0, 0.0, 0.0),
) -> Graph:
    off = np.asarray(offset, dtype=float)
    return Graph(
        region=region,
        nodes={n: np.asarray(p, dtype=float) + off for n, p in nodes.items()},
        edges=list(edges),
        high=high,
        offset=off,
        names={edge["id"]: "X" for edge in edges},
    )


def _edge(id_: int, source: int, run: int, *, foreign: str | None = None, lanes: int = 2) -> dict:
    edge = {
        "id": id_,
        "from": 0,
        "to": 1,
        "source_id": source,
        "run": run,
        "lanes": lanes,
        "width_m": 6.4,
        "elevation_level": 0,
        "road_name": {"en": "X"},
    }
    if foreign:
        edge["foreign"] = foreign
    return edge


class TestSharedSide:
    @staticmethod
    def _city(neighbours: dict[str, str]):
        return SimpleNamespace(neighbours=lambda region: neighbours if region == "a" else {})

    def test_each_of_the_four_sides_maps_to_its_game_axis(self) -> None:
        assert shared_side(self._city({"east": "b"}), "a", "b") == ("x", +1)
        assert shared_side(self._city({"west": "b"}), "a", "b") == ("x", -1)
        assert shared_side(self._city({"south": "b"}), "a", "b") == ("z", +1)
        assert shared_side(self._city({"north": "b"}), "a", "b") == ("z", -1)

    def test_a_pair_the_config_does_not_name_is_refused(self) -> None:
        with pytest.raises(SystemExit):
            shared_side(self._city({"east": "c"}), "a", "b")


class TestNearLine:
    def test_candidates_are_read_in_the_region_frame_on_the_shared_side_only(self) -> None:
        # Offset so a node's city position is far from its local one: a tool
        # testing city coordinates against a local `high` would find nothing.
        graph = _graph(
            "a",
            {0: (99.5, 0.0, 10.0), 1: (0.3, 0.0, 10.0), 2: (50.0, 0.0, 49.8)},
            offset=(1000.0, 0.0, 2000.0),
        )
        assert near_line(graph, ("x", +1), 1.0) == [0]
        assert near_line(graph, ("x", -1), 1.0) == [1]
        assert near_line(graph, ("z", +1), 1.0) == [2]
        assert near_line(graph, ("z", -1), 1.0) == []


class TestPairNodes:
    def test_pairing_is_mutual_so_two_nodes_cannot_share_one_partner(self) -> None:
        a = _graph("a", {0: (100.0, 0.0, 10.0), 1: (100.0, 0.0, 11.0)})
        b = _graph("b", {7: (100.4, 0.0, 10.1)})
        pairs, lone_a, lone_b = pair_nodes(a, b, [0, 1], [7], 2.0)
        assert [(p.a, p.b) for p in pairs] == [(0, 7)]
        assert lone_a == [1] and lone_b == []

    def test_separation_is_b_minus_a_in_the_city_frame(self) -> None:
        a = _graph("a", {0: (100.0, 1.0, 10.0)}, offset=(0.0, 0.0, 0.0))
        b = _graph("b", {0: (0.0, 1.5, 10.2)}, offset=(99.4, 0.0, 0.0))
        (pair,), _, _ = pair_nodes(a, b, [0], [0], 2.0)
        assert pair.separation == pytest.approx([-0.6, 0.5, 0.2])
        assert pair.plan_m == pytest.approx(np.hypot(0.6, 0.2))

    def test_beyond_the_radius_nothing_pairs(self) -> None:
        a = _graph("a", {0: (100.0, 0.0, 10.0)})
        b = _graph("b", {0: (103.0, 0.0, 10.0)})
        pairs, lone_a, lone_b = pair_nodes(a, b, [0], [0], 2.0)
        assert pairs == [] and lone_a == [0] and lone_b == [0]


class TestCrossingsByNode:
    """The pre-cut reading: one edge per side at a boundary node, or nothing."""

    @staticmethod
    def _plain(id_: int, from_: int, to: int, width: float, lanes: int) -> dict:
        return {
            "id": id_,
            "from": from_,
            "to": to,
            "lanes": lanes,
            "width_m": width,
            "elevation_level": 0,
            "road_name": {"en": "X"},
        }

    def test_width_and_lanes_are_counted_separately(self) -> None:
        a = _graph(
            "a",
            {0: (0, 0, 0), 1: (1, 0, 0), 2: (2, 0, 0)},
            [self._plain(0, 0, 1, 6.4, 2), self._plain(1, 0, 2, 4.0, 1)],
        )
        b = _graph(
            "b",
            {5: (0, 0, 0), 6: (1, 0, 0), 7: (2, 0, 0)},
            [self._plain(0, 5, 6, 6.4, 2), self._plain(1, 5, 7, 6.4, 1)],
        )
        pairs = [NodePair(1, 6, np.zeros(3)), NodePair(2, 7, np.zeros(3))]
        assert report_crossings_by_node(a, b, pairs) == (1, 0)

    def test_a_node_with_two_incident_edges_is_not_a_clip_end_and_is_skipped(self) -> None:
        a = _graph(
            "a",
            {0: (0, 0, 0), 1: (1, 0, 0), 2: (2, 0, 0)},
            [self._plain(0, 0, 1, 6.4, 2), self._plain(1, 1, 2, 4.0, 1)],
        )
        b = _graph("b", {5: (0, 0, 0), 6: (1, 0, 0)}, [self._plain(0, 5, 6, 3.0, 3)])
        assert report_crossings_by_node(a, b, [NodePair(1, 6, np.zeros(3))]) == (0, 0)


class TestOwners:
    """`one_owner` must be reachable at 0 in both directions, or it is `Q72`'s tautology."""

    def test_exactly_one_owner_is_counted_and_two_or_none_are_not(self) -> None:
        a = _graph(
            "a",
            {0: (0, 0, 0), 1: (1, 0, 0)},
            [_edge(0, 5, 0), _edge(1, 6, 0), _edge(2, 7, 0, foreign="b")],
        )
        b = _graph(
            "b",
            {0: (0, 0, 0), 1: (1, 0, 0)},
            [_edge(0, 5, 0, foreign="a"), _edge(1, 6, 0), _edge(2, 7, 0, foreign="a", lanes=3)],
        )
        shared, one_owner, lanes_off, unmatched = report_crossings_by_identity(a, b)
        assert shared == 3
        assert one_owner == 1  # source 6 has two owners, source 7 none
        assert lanes_off == 1
        assert unmatched == 0

    def test_a_foreign_copy_with_no_run_opposite_is_counted(self) -> None:
        """The two builds numbering a feature's runs differently is invisible
        to every other counter: the owner's copy is simply an owned edge and
        the foreign one pairs with nothing."""
        a = _graph("a", {0: (0, 0, 0), 1: (1, 0, 0)}, [_edge(0, 5, 0)])
        b = _graph("b", {0: (0, 0, 0), 1: (1, 0, 0)}, [_edge(0, 5, 1, foreign="a")])
        b = Graph(**{**b.__dict__, "edges": [], "foreign_edges": b.edges})

        shared, _, _, unmatched = report_crossings_by_identity(a, b)
        assert shared == 0
        assert unmatched == 1

    def test_no_identity_means_no_shared_edges(self) -> None:
        plain = {
            "id": 0,
            "from": 0,
            "to": 1,
            "lanes": 2,
            "width_m": 6.4,
            "elevation_level": 0,
            "road_name": {"en": "X"},
        }
        a = _graph("a", {0: (0, 0, 0), 1: (1, 0, 0)}, [plain])
        b = _graph("b", {0: (0, 0, 0), 1: (1, 0, 0)}, [dict(plain)])
        assert a.identities == {} and b.identities == {}


def _road(z_low: float, z_high: float, *, x_low: float = 0.0, x_high: float = 100.0) -> dict:
    """A `carriageway_region.json` holding one straight road across the rectangle."""
    outer = [[x_low, z_low], [x_high, z_low], [x_high, z_high], [x_low, z_high], [x_low, z_low]]
    return {"territories": [{"rings": [{"outer": outer, "holes": []}]}]}


class TestCarriagewaySection:
    """`P3-33e`: R is cut by rectangle (`Q116`), so nothing but this makes the
    two builds agree on where a road meets the line they share."""

    WEST = _graph("west", {})
    # `city_offset` is whole metres and a rectangle is not, so the pair overlap
    # as Wan Chai and Causeway Bay do — by 0.6 m here.
    EAST = _graph("east", {}, offset=(99.4, 0.0, 0.0))

    def test_an_overlapping_pair_is_sectioned_on_one_line(self) -> None:
        """🔴 An inset inside each instead reads a road crossing at 45 degrees
        0.5 m apart along the line, and all eight of the shipped seam's roads
        reported a disagreement that was the offset's rounding."""
        ours, theirs = section_lines(self.WEST, self.EAST, ("x", 1), 0.05)
        assert ours == theirs == pytest.approx(99.7)

    def test_a_pair_sharing_an_exact_line_is_sectioned_inside_each(self) -> None:
        flush = _graph("east", {}, offset=(100.0, 0.0, 0.0))
        assert section_lines(self.WEST, flush, ("x", 1), 0.05) == pytest.approx((99.95, 100.05))

    def test_the_section_is_along_the_line_in_the_city_frame(self) -> None:
        south = _graph("south", {}, offset=(0.0, 0.0, 200.0))
        found = section(carriageway_of(_road(10.0, 17.0)), south, "x", 50.0)
        assert [part.bounds for part in found.geoms] == [(210.0, 0.0, 217.0, 0.0)]

    def test_a_road_one_build_draws_wider_is_a_disagreement(self) -> None:
        """🔴 **The mutation this exists for.** The shipped pair reads 0.00 m,
        and a counter that reads zero is only evidence if something reachable
        moves it (`Q72`): a kerb stepping 1.5 m sideways at the seam does."""
        line = 99.7
        ours = section(carriageway_of(_road(10.0, 17.0)), self.WEST, "x", line)
        theirs = section(carriageway_of(_road(10.0, 18.5, x_high=50.0)), self.EAST, "x", line)
        assert ours.difference(theirs).length == 0.0
        assert theirs.difference(ours).length == pytest.approx(1.5)

    def test_a_road_that_stops_short_of_the_line_is_not_on_it(self) -> None:
        short = carriageway_of(_road(10.0, 17.0, x_high=99.0))
        assert section(short, self.WEST, "x", 99.7).is_empty
