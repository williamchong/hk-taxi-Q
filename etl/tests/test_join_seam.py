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
    near_line,
    pair_nodes,
    report_crossings_by_identity,
    report_crossings_by_node,
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
    def _city(a: dict, b: dict):
        regions = {
            "a": SimpleNamespace(bounds=SimpleNamespace(**a)),
            "b": SimpleNamespace(bounds=SimpleNamespace(**b)),
        }
        return SimpleNamespace(region=lambda r: regions[r])

    def test_each_of_the_four_sides_is_read_from_the_bounds(self) -> None:
        base = {"west": 0.0, "east": 1.0, "south": 0.0, "north": 1.0}
        east = {**base, "west": 1.0, "east": 2.0}
        west = {**base, "west": -1.0, "east": 0.0}
        south = {**base, "south": -1.0, "north": 0.0}
        north = {**base, "south": 1.0, "north": 2.0}
        assert shared_side(self._city(base, east), "a", "b") == ("x", +1)
        assert shared_side(self._city(base, west), "a", "b") == ("x", -1)
        assert shared_side(self._city(base, south), "a", "b") == ("z", +1)
        assert shared_side(self._city(base, north), "a", "b") == ("z", -1)

    def test_a_pair_sharing_no_edge_is_refused(self) -> None:
        base = {"west": 0.0, "east": 1.0, "south": 0.0, "north": 1.0}
        apart = {**base, "west": 5.0, "east": 6.0}
        with pytest.raises(SystemExit):
            shared_side(self._city(base, apart), "a", "b")


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
        shared, one_owner, lanes_off = report_crossings_by_identity(a, b)
        assert shared == 3
        assert one_owner == 1  # source 6 has two owners, source 7 none
        assert lanes_off == 1

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
