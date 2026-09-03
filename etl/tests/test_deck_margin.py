"""The probe on `tools/deck_margin.py` (`Q103`).

Same standard as `test_carriageway_occupancy.py`: only the parts whose failure
mode is **silent**. The per-edge and pooled tables above the probe grade
themselves against `Q22`'s recorded figures and a walk that stopped walking
would read 0 stations, which nobody could miss. What would not announce itself
is everything here.

🔴 **The probe exists to be read as a SERIES, so a hole in it that does not
print is the defect this file is about.** `Row`'s lists are dense and carry no
positional marker for a refusal, and refusals outnumber keeps on this tool —
1,637 junction against 1,334 kept as it runs today. A trace that recorded only
the stations `survey` kept would draw a smooth drift straight through the
stations it could not read, and it would look exactly like a finding. So the
partition is asserted, and asserted with **both** halves non-empty: a trace that
recorded nothing at all satisfies every equality in a partition.

⚠️ **The join key is the other silent one.** `along_metres` and
`occupancy_indices` line this walk up against `carriageway_occupancy.py`'s at a
different pitch, and both pitches are variable — `deck_error.stations` cuts each
segment into `ceil(L / spacing)` equal pieces. An index computed by division
instead of by re-walking is wrong by a fraction of a station everywhere and by
whole stations after a short segment, and it prints a full and plausible table
either way. `TestOccupancyIndices` pins it against a polyline where the two
answers differ.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

import numpy as np
import pytest
from deck_error import Faces
from deck_margin import (
    Refusals,
    Station,
    along_metres,
    occupancy_indices,
    refuse_unprobeable,
    survey,
)
from overhang import walk_width

# A deck at this height, and a road drawn on it. The value is arbitrary and only
# has to be off zero, so a station whose height was dropped somewhere reads as a
# miss rather than coincidentally landing on the deck.
DECK_Y = 10.0


def _deck(x_from: float, x_to: float, z_half: float = 3.0) -> Faces:
    """A flat quad of upward-wound triangles, indexed as `survey` expects.

    Wound `(a, +z, +x)` because `Faces.of(..., signed=True)` keeps only faces
    whose normal points up, and the opposite winding indexes **nothing** — which
    would make every assertion below pass by there being no deck at all.
    """
    corners = np.array(
        [
            [[x_from, DECK_Y, -z_half], [x_from, DECK_Y, z_half], [x_to, DECK_Y, -z_half]],
            [[x_to, DECK_Y, -z_half], [x_from, DECK_Y, z_half], [x_to, DECK_Y, z_half]],
        ],
        dtype=np.float64,
    )
    faces = Faces.of(corners, signed=True)
    assert len(faces.corners) == 2, "both triangles must survive the upward filter"
    return faces


def _graph(polyline: list[list[float]], nodes: list[list[float]]) -> dict:
    return {
        "nodes": [{"pos": pos} for pos in nodes],
        "edges": [
            {
                "id": 1,
                "elevation_level": 1,
                "polyline": polyline,
                "width_m": 4.0,
                "lanes": 2,
                "lanes_source": "authored",
            }
        ],
    }


def _manifest(*edges: int) -> dict:
    return {"carriageway": [{"edge": edge, "half_width_m": [2.0, 2.0, 2.0]} for edge in edges]}


def _survey(
    graph: dict, structure: Faces, *, trace: dict[int, list[Station]] | None = None
) -> dict:
    """`survey` with the walk constants fixed, so four tests state them once.

    A change to `survey`'s signature lands in one place here rather than four,
    which is the only thing standing between this file and the drift the tool it
    grades keeps a whole docstring about.
    """
    return survey(
        graph,
        _manifest(*(int(edge["id"]) for edge in graph["edges"])),
        structure,
        spacing_m=2.0,
        across_m=0.1,
        max_lateral_m=12.0,
        junction_m=3.0,
        attribute_within_m=1.0,
        bridge_m=1.0,
        trace=trace,
    )


def _walk(graph: dict, structure: Faces) -> tuple[dict, list[Station]]:
    trace: dict[int, list[Station]] = {1: []}
    return _survey(graph, structure, trace=trace), trace[1]


class TestAlongMetres:
    """The join key, which is a distance and not an index."""

    def test_the_first_station_is_at_zero(self) -> None:
        polyline = np.array([[0.0, DECK_Y, 0.0], [10.0, DECK_Y, 0.0]])
        assert along_metres(polyline, 0, polyline[0]) == pytest.approx(0.0)

    def test_it_accumulates_the_segments_behind_the_station(self) -> None:
        polyline = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 0.0, 7.0]])
        # Three metres up the second segment: ten behind it, thirteen in all.
        assert along_metres(polyline, 1, np.array([10.0, 0.0, 3.0])) == pytest.approx(13.0)

    def test_it_is_a_PLAN_distance_and_ignores_the_climb(self) -> None:
        """A ramp's length is its plan length here, as it is in both tools.

        Measuring the slope instead would put this walk's metres and the
        occupier walk's on different rulers wherever a deck climbs — which is
        every deck worth probing.
        """
        flat = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
        climbing = np.array([[0.0, 0.0, 0.0], [10.0, 40.0, 0.0]])
        assert along_metres(climbing, 0, climbing[1]) == pytest.approx(
            along_metres(flat, 0, flat[1])
        )


class TestOccupancyIndices:
    """The counterpart index, derived by re-walking rather than by division."""

    # 7 m in one segment at a nominal 1 m walks `ceil(7 / 1) = 7` pieces of
    # exactly 1.0, and at a nominal 2 m walks `ceil(7 / 2) = 4` pieces of
    # **1.75**. So this tool's station 3 is at 5.25 m and the occupier's station
    # nearest it is 5, where `round(along / spacing)` also says 5 — but station
    # 2 is at 3.50 m, where the nearest is 3 or 4 and the arithmetic answer is a
    # tie the tools would break differently.
    POLYLINE: ClassVar[np.ndarray] = np.array([[0.0, 0.0, 0.0], [7.0, 0.0, 0.0]])

    def test_every_station_maps_to_a_real_occupancy_station(self) -> None:
        alongs = [
            along_metres(self.POLYLINE, vertex, station)
            for vertex, station in walk_width(self.POLYLINE, 2.0)
        ]
        indices = occupancy_indices(self.POLYLINE, alongs, 1.0)
        walked = len(list(walk_width(self.POLYLINE, 1.0)))
        assert len(indices) == len(alongs)
        assert all(0 <= index < walked for index in indices)

    def test_it_never_runs_backwards(self) -> None:
        alongs = [
            along_metres(self.POLYLINE, vertex, station)
            for vertex, station in walk_width(self.POLYLINE, 2.0)
        ]
        indices = occupancy_indices(self.POLYLINE, alongs, 1.0)
        assert indices == sorted(indices)

    def test_a_short_final_segment_moves_the_index_off_the_arithmetic_answer(self) -> None:
        """The property that makes this a re-walk rather than a division.

        A 1.2 m tail segment is cut into `ceil(1.2 / 1) = 2` pieces of **0.6 m**,
        so past 7 m the occupier's stations are 0.6 m apart and its index stops
        counting metres. The occupier walks 10 stations over this 8.2 m
        polyline and its last is at 8.2 m, where `round(along / spacing)` says
        8 — a whole station short. Off by one is the error worth catching: off
        by a fraction is invisible, and off by one lays a drift against the
        wrong cross-section.
        """
        polyline = np.array([[0.0, 0.0, 0.0], [7.0, 0.0, 0.0], [8.2, 0.0, 0.0]])
        alongs = [
            along_metres(polyline, vertex, station) for vertex, station in walk_width(polyline, 2.0)
        ]
        indices = occupancy_indices(polyline, alongs, 1.0)
        walked = len(list(walk_width(polyline, 1.0)))
        assert walked == 10
        assert max(indices) < walked
        # The last station is the polyline's end, so it maps to the occupier's
        # last station — which the arithmetic answer misses by one.
        assert alongs[-1] == pytest.approx(8.2)
        assert indices[-1] == walked - 1
        assert round(alongs[-1] / 1.0) == walked - 2


class TestTheTraceIsAPartition:
    """Every walked station is recorded exactly once, kept or refused."""

    # A node at each end, so the junction refusal fires; a deck under the middle
    # only, so `no_deck` fires too. Both halves non-empty is the point.
    POLYLINE: ClassVar[list[list[float]]] = [
        [0.0, DECK_Y, 0.0],
        [10.0, DECK_Y, 0.0],
        [20.0, DECK_Y, 0.0],
    ]
    NODES: ClassVar[list[list[float]]] = [[0.0, DECK_Y, 0.0], [20.0, DECK_Y, 0.0]]

    def _run(self) -> tuple[dict, list[Station]]:
        return _walk(_graph(self.POLYLINE, self.NODES), _deck(0.0, 12.0))

    def test_it_records_one_row_per_walked_station(self) -> None:
        _, series = self._run()
        walked = len(list(walk_width(np.asarray(self.POLYLINE, dtype=np.float64), 2.0)))
        assert len(series) == walked

    def test_the_kept_and_refused_halves_are_both_reached(self) -> None:
        """Asserted before the equalities, because a partition of nothing holds.

        A trace that never appended satisfies every count below, and that is the
        state this whole file exists to catch.
        """
        rows, series = self._run()
        assert sum(1 for station in series if not station.refused) > 0
        assert sum(1 for station in series if station.refused) > 0
        assert rows[1].refused.junction > 0
        assert rows[1].refused.no_deck > 0

    def test_the_counts_agree_with_the_row_the_tables_are_built_from(self) -> None:
        rows, series = self._run()
        row = rows[1]
        kept = [station for station in series if not station.refused]
        assert len(kept) == len(row.span_m)
        # Derived, not restated: a fifth reason added to `Refusals` and
        # `survey` would otherwise be covered only by the looser total below.
        for reason in (field.name for field in dataclasses.fields(Refusals)):
            assert sum(1 for station in series if station.refused == reason) == getattr(
                row.refused, reason
            )
        assert len(series) == len(kept) + row.refused.total

    def test_the_kept_rows_carry_the_same_numbers_the_tables_do(self) -> None:
        rows, series = self._run()
        kept = [station for station in series if not station.refused]
        assert [station.span_m for station in kept] == pytest.approx(rows[1].span_m)
        assert [station.off_centre_m for station in kept] == pytest.approx(rows[1].off_centre_m)
        assert [station.overhang_m for station in kept] == pytest.approx(rows[1].overhang_m)
        assert sum(station.centre_off_deck for station in kept) == rows[1].centre_off_deck

    def test_a_refusal_carries_NaN_and_never_a_zero(self) -> None:
        """A zero span reads as a measured absence of deck; there is none."""
        _, series = self._run()
        refused = [station for station in series if station.refused]
        assert refused
        for station in refused:
            assert np.isnan(station.span_m)
            assert np.isnan(station.off_centre_m)
            assert np.isnan(station.overhang_m)


class TestTheTraceDoesNotDisturbTheWalk:
    """The default path is the shipped one, and a second edge is its own edge."""

    def test_the_row_is_identical_with_and_without_a_trace(self) -> None:
        graph = _graph(TestTheTraceIsAPartition.POLYLINE, TestTheTraceIsAPartition.NODES)
        structure = _deck(0.0, 12.0)
        untraced = _survey(graph, structure)[1]
        traced = _survey(graph, structure, trace={1: []})[1]
        assert untraced.span_m == pytest.approx(traced.span_m)
        assert untraced.off_centre_m == pytest.approx(traced.off_centre_m)
        assert untraced.refused == traced.refused

    def test_an_untraced_edge_records_nothing(self) -> None:
        """`survey` fills the keys it is handed and never invents one.

        `main` keys the trace from `--probe-edges` before the walk for exactly
        this reason: an edge the walk never reaches must reach `probe`'s own
        refusal, rather than printing an empty series as though it had been
        walked and found bare.
        """
        graph = _graph(TestTheTraceIsAPartition.POLYLINE, TestTheTraceIsAPartition.NODES)
        trace: dict[int, list[Station]] = {}
        _survey(graph, _deck(0.0, 12.0), trace=trace)
        assert trace == {}

    def test_each_edge_measures_along_its_OWN_polyline(self) -> None:
        """Each edge's trace is keyed to its own edge and measured on its own line.

        ⚠️ **This does NOT pin `record`'s default-argument binding**, which an
        earlier docstring here claimed. Every call is inside the iteration that
        defines `record`, so a plain closure reads the current edge too — checked
        by removing the binding, whereupon this test still passes and only
        `B023` complains. A test that passes with the thing it names removed is
        covering nothing (`Q72`), so what it is named for is the keying.
        """
        graph = _graph(TestTheTraceIsAPartition.POLYLINE, TestTheTraceIsAPartition.NODES)
        # A second edge, half as long and elsewhere, walked in the same pass.
        graph["edges"].append(
            {
                "id": 2,
                "elevation_level": 1,
                "polyline": [[0.0, DECK_Y, 50.0], [10.0, DECK_Y, 50.0]],
                "width_m": 4.0,
                "lanes": 2,
                "lanes_source": "authored",
            }
        )
        trace: dict[int, list[Station]] = {1: [], 2: []}
        _survey(graph, _deck(0.0, 12.0), trace=trace)
        assert max(station.along_m for station in trace[1]) == pytest.approx(20.0)
        assert max(station.along_m for station in trace[2]) == pytest.approx(10.0)


class TestRefuseUnprobeable:
    """A named edge that could print no row is refused, and refused EARLY.

    🔴 **Silence is the failure mode.** An edge the walk never reaches leaves
    the report saying nothing about it, and nothing reads as "the deck is fine
    there" — the empty set as agreement. `carriageway_occupancy`'s own
    `refuse_unprobeable` carries the same paragraph.

    ⚠️ **Each branch is exercised separately**, because a single check that
    happened to catch all three would pass a test that only ever asked for one.
    """

    GRAPH: ClassVar[dict] = {
        "nodes": [],
        "edges": [
            {"id": 1, "elevation_level": 1, "polyline": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]]},
            {"id": 2, "elevation_level": 0, "polyline": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]]},
            {"id": 3, "elevation_level": 1, "polyline": [[0.0, 0.0, 0.0]]},
        ],
    }

    def test_an_off_grade_edge_with_a_real_polyline_is_accepted(self) -> None:
        """Asserted first: a refusal that fires on everything refuses nothing."""
        refuse_unprobeable(self.GRAPH, (1,))

    def test_an_edge_the_graph_does_not_carry_is_refused(self) -> None:
        with pytest.raises(SystemExit, match="road graph does not carry"):
            refuse_unprobeable(self.GRAPH, (99,))

    def test_an_at_grade_edge_is_refused(self) -> None:
        with pytest.raises(SystemExit, match="at or below grade"):
            refuse_unprobeable(self.GRAPH, (2,))

    def test_a_single_point_polyline_is_refused(self) -> None:
        with pytest.raises(SystemExit, match=r"single\s+point"):
            refuse_unprobeable(self.GRAPH, (3,))

    def test_the_refusal_names_the_edge_in_the_spelling_the_listings_print(self) -> None:
        """`edges_label` is imported, not restated — the flag's parser inverse.

        Two spellings of one set costs the reader the match, which is the
        reason that helper carries in the tool it came from.

        ⚠️ Both ids are refused by the **same** branch on purpose — a pair that
        straddled two branches would only ever print the first, and the test
        would pass on a label that never joined anything. The reversed pair
        pins that the reader's order is kept, which is `edges_argument`'s rule.
        """
        with pytest.raises(SystemExit, match="e99,e98"):
            refuse_unprobeable(self.GRAPH, (99, 98))
        with pytest.raises(SystemExit, match="e98,e99"):
            refuse_unprobeable(self.GRAPH, (98, 99))

    def test_naming_nothing_refuses_nothing(self) -> None:
        refuse_unprobeable(self.GRAPH, ())
