"""The two-region merge (`P5-7g`).

What would fail silently: a seam node kept twice, so a route across the join
does not exist; a foreign copy merged beside the owner's, so a road is drawn
and routed twice; a turn whose foreign arm resolves to nothing; and the
second region's geometry landing in the wrong frame by a whole origin.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from pipeline.join import JOIN_NAME, join_regions, merge
from pipeline.roads import ROADGRAPH_NAME
from tests.helpers import build_pair_graphs


def _pair(city, tmp_path: Path) -> tuple[dict, dict, np.ndarray]:
    _, docs = build_pair_graphs(city, tmp_path)
    own, other = city.game_transform("middle"), city.game_transform("east")
    delta = np.asarray(
        own.to_game(other.origin_easting, other.origin_northing, other.origin_elevation)
    )
    return docs["middle"], docs["east"], delta


class TestMerge:
    def test_every_run_appears_once_and_the_seam_nodes_are_shared(self, testville_pair) -> None:
        city, tmp_path = testville_pair
        a, b, delta = _pair(city, tmp_path)
        graph, _, report = merge(a, b, delta, regions=("middle", "east"))

        identities = [(e["source_id"], e["run"]) for e in graph["edges"]]
        assert len(identities) == len(set(identities)) == len(a["edges"]) + len(b["edges"])
        assert graph["foreign_edges"] == []
        assert report.foreign_matched == len(a["foreign_edges"]) + len(b["foreign_edges"])
        assert report.foreign_unmatched == 0
        # Every foreign copy names two seam nodes; a node shared by two copies
        # counts once, which is why this is `<=` and not `==`.
        assert 0 < report.nodes_unified <= 2 * report.foreign_matched
        assert report.nodes == len(a["nodes"]) + len(b["nodes"]) - report.nodes_unified
        ids = {n["id"] for n in graph["nodes"]}
        assert ids == set(range(report.nodes))
        assert all(e["from"] in ids and e["to"] in ids for e in graph["edges"])

    def test_the_second_region_is_moved_into_the_first_frame(self, testville_pair) -> None:
        """MAIN (middle's) ends where BACK (east's) begins; after the merge the
        two say so with one node and the same coordinates."""
        city, tmp_path = testville_pair
        a, b, delta = _pair(city, tmp_path)
        graph, _, _ = merge(a, b, delta, regions=("middle", "east"))
        by_source = {e["source_id"]: e for e in graph["edges"]}
        nodes = {n["id"]: np.asarray(n["pos"]) for n in graph["nodes"]}

        main, back = by_source[1], by_source[2]
        assert main["to"] == back["from"]
        np.testing.assert_allclose(main["polyline"][-1], back["polyline"][0], atol=1e-3)
        # BACK's copy in middle was at the same place, so nothing moved by an origin.
        copy = next(e for e in a["foreign_edges"] if e["source_id"] == 2)
        np.testing.assert_allclose(back["polyline"], copy["polyline"], atol=1e-3)
        assert nodes[main["to"]][0] == pytest.approx(main["polyline"][-1][0], abs=1e-3)

    def test_a_turn_across_the_seam_names_the_owner_copies(self, testville_pair) -> None:
        city, tmp_path = testville_pair
        a, b, delta = _pair(city, tmp_path)
        graph, _, report = merge(a, b, delta, regions=("middle", "east"))
        by_source = {e["source_id"]: e for e in graph["edges"]}

        assert report.turns == len(a["turn_restrictions"]) + len(b["turn_restrictions"]) == 1
        assert report.turns_dropped == 0
        (turn,) = graph["turn_restrictions"]
        assert turn["from_edge"] == by_source[1]["id"]
        assert turn["to_edge"] == by_source[2]["id"]
        assert turn["via_node"] == by_source[1]["to"]

    def test_a_run_owned_by_both_is_refused(self, testville_pair) -> None:
        city, tmp_path = testville_pair
        a, b, delta = _pair(city, tmp_path)
        b["edges"].append({**a["edges"][0], "id": 99})
        with pytest.raises(ValueError, match="owned by both"):
            merge(a, b, delta, regions=("middle", "east"))

    def test_without_the_foreign_lists_nothing_unifies_and_the_seam_is_two_nodes(
        self, testville_pair
    ) -> None:
        """The mutation: the identities are what name the seam. Strip them and
        the merge is two graphs side by side — every node kept, no node shared."""
        city, tmp_path = testville_pair
        a, b, delta = _pair(city, tmp_path)
        a["foreign_edges"], b["foreign_edges"] = [], []
        _, _, report = merge(a, b, delta, regions=("middle", "east"))

        assert report.nodes_unified == 0
        assert report.nodes == len(a["nodes"]) + len(b["nodes"])
        assert report.foreign_matched == 0

    def test_clearance_rows_follow_the_renumbered_ids(self, testville_pair) -> None:
        city, tmp_path = testville_pair
        a, b, delta = _pair(city, tmp_path)
        clearance = tuple(
            {
                "schema_version": 1,
                "region_id": r,
                "clearance": [{"edge": e["id"], "clear_width_m": [5.0]} for e in doc["edges"]],
            }
            for r, doc in (("middle", a), ("east", b))
        )
        graph, merged, report = merge(a, b, delta, regions=("middle", "east"), clearance=clearance)

        assert merged is not None
        assert {row["edge"] for row in merged["clearance"]} == {e["id"] for e in graph["edges"]}
        assert report.clearance_rows == len(graph["edges"])


class TestJoinRegions:
    def test_it_writes_the_pair_under_its_own_directory(self, testville_pair) -> None:
        city, tmp_path = testville_pair
        _pair(city, tmp_path)
        report = join_regions(city, "middle", "east", out_root=tmp_path / "out")

        out = tmp_path / "out" / "middle+east"
        graph = json.loads((out / ROADGRAPH_NAME).read_text())
        assert graph["region_id"] == "middle+east" and graph["frame"] == "middle"
        assert len(graph["edges"]) == report.edges
        assert (
            json.loads((out / JOIN_NAME).read_text())["foreign_matched"] == report.foreign_matched
        )

    def test_two_regions_that_share_no_edge_are_refused(self, testville_pair) -> None:
        city, tmp_path = testville_pair
        with pytest.raises(SystemExit, match="share no whole edge"):
            join_regions(city, "middle", "middle", out_root=tmp_path / "out")
