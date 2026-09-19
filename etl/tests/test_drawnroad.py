"""`pipeline/drawnroad.py` — the one reader of the drawn road (`P3-35d`, `Q133`).

What is pinned here is the question `Q57` says every reader owes — *the share or
the road?* — for the consumers that stand something at a kerb.
"""

from __future__ import annotations

from types import MappingProxyType

import numpy as np
import pytest

from pipeline.drawnroad import Ribbon, nearside, ribbons
from pipeline.polyline import Segments
from tests.test_surface import _edge


def _graph(**overrides) -> dict:
    return {"edges": [_edge(7, 0, 1, [[0.0, 0.0, 0.0], [0.0, 0.0, -100.0]], **overrides)]}


def _surface(**row) -> dict:
    return {"carriageway": [{"edge": 7, "half_width_m": [3.0, 3.0], "offset_m": [0.0, 0.0]} | row]}


MID_EDGE = np.array([0.0, -50.0])


def _surveyed(across_m: float) -> np.ndarray:
    """A plan point `across_m` to the nearside of the edge, half way along it —
    clear of both ends, where a snap clamps and `offset_m` stops being across."""
    return MID_EDGE + across_m * nearside(0.0)


def _snap(graph: dict, across_m: float):
    return Segments.of(graph["edges"]).nearest(*_surveyed(across_m))


def _across(point: np.ndarray, heading_deg: float) -> float:
    """A plan point's signed distance to the NEARSIDE of the edge."""
    return float((point - MID_EDGE) @ nearside(heading_deg))


class TestTheKerbIsTheRoads:
    """A share 3 m either side of its centreline, in a road whose kerbs stand
    4 m to the nearside and 12 m to the offside — two more carriageways lie
    between this centreline and the far kerb."""

    # `carriageway_region.json`'s own shape: dense stations along the run, the
    # kerb 4 m to the left (nearside) and 12 m to the right at each.
    ROAD = MappingProxyType(
        {
            "edge": 7,
            "foreign": False,
            "along_m": [0.0, 25.0, 50.0, 75.0, 100.0],
            # This centreline's share: 4 m to its own kerb on the left, and 3 m
            # to the next carriageway on the right — asphalt, not a kerb.
            "left_m": [4.0] * 5,
            "right_m": [3.0] * 5,
            "left_end": ["kerb"] * 5,
            "right_end": ["share"] * 5,
            "left_kerb_m": [4.0] * 5,
            "right_kerb_m": [12.0] * 5,
        }
    )

    def _ribbon(self, road=None, **row) -> tuple[dict, Ribbon]:
        graph = _graph()
        region = {"territories": [dict(road)]} if road is not None else None
        return graph, ribbons(graph, _surface(**row), region)[7]

    def test_kerb_at_is_the_regions_kerbs_where_the_edge_has_a_territory(self) -> None:
        _, ribbon = self._ribbon(self.ROAD)
        assert ribbon.kerb_at(0.5) == pytest.approx((-4.0, 8.0))

    def test_kerb_at_is_the_ribbon_where_it_does_not(self) -> None:
        _, ribbon = self._ribbon(offset_m=[1.0, 1.0])
        assert ribbon.kerb_at(0.5) == pytest.approx((1.0, 3.0))

    def test_a_post_on_the_shares_rail_is_still_in_the_road(self) -> None:
        """🔴 The defect this file exists for. 3.5 m to the offside is past this
        share's rail and 7.5 m short of the nearer kerb: a test about the ribbon
        calls it clear, and the post stays standing between two carriageways."""
        graph, ribbon = self._ribbon(self.ROAD)
        offside = _snap(graph, -3.5)
        assert offside.offset_m == pytest.approx(-3.5)
        assert ribbon.past_kerb_m(offside) == pytest.approx(-7.5)

    def test_a_post_past_the_roads_kerb_is_clear_by_what_it_stands_past(self) -> None:
        graph, ribbon = self._ribbon(self.ROAD)
        assert ribbon.past_kerb_m(_snap(graph, 5.0)) == pytest.approx(1.0)

    def test_the_target_is_the_nearer_kerb_of_the_road(self) -> None:
        """2 m to the offside of the centreline is 6 m from the nearside kerb and
        10 m from the offside one. The sign of `offset_m` — the old rule — sends
        it across two carriageways."""
        graph, ribbon = self._ribbon(self.ROAD)
        snap = _snap(graph, -2.0)
        side, half_m, target_m, point = ribbon.kerb_target(snap, 0.6)
        assert (side, half_m, target_m) == pytest.approx((1.0, 8.0, 4.6))
        assert _across(point, snap.heading_deg) == pytest.approx(4.6)

    def test_the_offside_target_is_the_offside_kerb(self) -> None:
        graph, ribbon = self._ribbon(self.ROAD)
        snap = _snap(graph, -9.0)
        side, _, target_m, point = ribbon.kerb_target(snap, 0.6)
        assert (side, target_m) == pytest.approx((-1.0, -12.6))
        assert _across(point, snap.heading_deg) == pytest.approx(-12.6)

    def test_the_move_is_still_target_minus_offset(self) -> None:
        """`target_m` stays in the centreline's frame, so every caller's
        `abs(target_m - snap.offset_m)` is still the distance it moved the post."""
        graph, ribbon = self._ribbon(self.ROAD)
        snap = _snap(graph, -2.0)
        _, _, target_m, point = ribbon.kerb_target(snap, 0.6)
        moved_m = float(np.linalg.norm(point - _surveyed(-2.0)))
        assert abs(target_m - snap.offset_m) == pytest.approx(moved_m)

    def test_a_point_on_the_roads_middle_takes_the_nearside(self) -> None:
        graph, ribbon = self._ribbon(self.ROAD)
        side, *_ = ribbon.kerb_target(_snap(graph, -4.0), 0.6)
        assert side == 1.0

    def test_on_a_symmetric_road_nothing_moved(self) -> None:
        """The inertness the region-less path and every off-grade edge rest on."""
        graph, ribbon = self._ribbon()
        snap = _snap(graph, 2.0)
        assert ribbon.kerb_target(snap, 0.6)[:3] == pytest.approx((1.0, 3.0, 3.6))
        assert ribbon.past_kerb_m(snap) == pytest.approx(-1.0)

    def test_kerbs_that_disagree_in_length_are_refused_whole(self) -> None:
        """A half-read kerb is a post registered against one side of a road."""
        _, ribbon = self._ribbon(self.ROAD | {"right_kerb_m": [12.0] * 4})
        assert ribbon.kerb_at_t is None
        assert ribbon.kerb_at(0.5) == pytest.approx((0.0, 3.0))

    def test_a_neighbours_run_lends_no_kerb(self) -> None:
        """`foreign` territories are published for the AREAS (`Q116`); the run is
        its owner's to furnish, and an edge id may collide across the seam."""
        _, ribbon = self._ribbon(self.ROAD | {"foreign": True})
        assert ribbon.kerb_at_t is None

    def test_the_kerb_is_read_where_the_post_stands_and_not_at_the_nodes(self) -> None:
        """🔴 Why the manifest's per-vertex `corridor_*` was withdrawn. This street
        is two graph vertices, both at junctions, where the kerb ray runs off down
        the side street (16 m); mid-block the kerb is 4 m away."""
        mouths = self.ROAD | {"left_kerb_m": [16.0, 4.0, 4.0, 4.0, 16.0]}
        graph, ribbon = self._ribbon(mouths)
        assert ribbon.past_kerb_m(_snap(graph, 5.0)) == pytest.approx(1.0)

    def test_a_mouth_is_bridged_along_the_kerb_line_either_side_of_it(self) -> None:
        """🔴 The middle station stands in a side-street mouth: its ray ran 16 m
        down the side street and ended in that street's share. A post on the
        corner, 5 m out, is ONE metre past the kerb line — read raw it is 11 m
        deep in the road, and is pushed across the footway or refused."""
        mouth = self.ROAD | {
            "left_m": [4.0, 4.0, 16.0, 4.0, 4.0],
            "left_kerb_m": [4.0, 4.0, 16.0, 4.0, 4.0],
            "left_end": ["kerb", "kerb", "share", "kerb", "kerb"],
        }
        graph, ribbon = self._ribbon(mouth)
        assert ribbon.past_kerb_m(_snap(graph, 5.0)) == pytest.approx(1.0)

    def test_a_side_with_no_kerb_of_its_own_takes_the_corridors(self) -> None:
        _, ribbon = self._ribbon(self.ROAD)
        assert ribbon.kerb_right_m == pytest.approx([12.0] * 5)
