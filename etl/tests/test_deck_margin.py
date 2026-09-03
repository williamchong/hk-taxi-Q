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
    clamp_station,
    occupancy_indices,
    priced_widths,
    refuse_unprobeable,
    survey,
)
from overhang import walk_width

# A deck at this height, and a road drawn on it. The value is arbitrary and only
# has to be off zero, so a station whose height was dropped somewhere reads as a
# miss rather than coincidentally landing on the deck.
DECK_Y = 10.0

# One straight run with a vertex in the middle, shared by every class that walks
# a whole edge. Hoisted rather than copied: two classes reached across into
# `TestTheTraceIsAPartition` for it and a third had a byte-identical copy, so
# the constant was already being treated as common.
POLYLINE = [[0.0, DECK_Y, 0.0], [10.0, DECK_Y, 0.0], [20.0, DECK_Y, 0.0]]


def _deck_band(x_from: float, x_to: float, z_from: float, z_to: float) -> Faces:
    """A flat quad of upward-wound triangles, indexed as `survey` expects.

    Wound `(a, +z, +x)` because `Faces.of(..., signed=True)` keeps only faces
    whose normal points up, and the opposite winding indexes **nothing** — which
    would make every assertion below pass by there being no deck at all.

    ⚠️ **The band is asymmetric on purpose.** A deck that does not straddle
    `z = 0` is the only way to reach a station whose centreline is off its own
    deck, which is the state `TestClampStation` exists for and which the
    symmetric `_deck` below cannot produce at any width.
    """
    corners = np.array(
        [
            [[x_from, DECK_Y, z_from], [x_from, DECK_Y, z_to], [x_to, DECK_Y, z_from]],
            [[x_to, DECK_Y, z_from], [x_from, DECK_Y, z_to], [x_to, DECK_Y, z_to]],
        ],
        dtype=np.float64,
    )
    faces = Faces.of(corners, signed=True)
    assert len(faces.corners) == 2, "both triangles must survive the upward filter"
    return faces


def _deck(x_from: float, x_to: float, z_half: float = 3.0) -> Faces:
    """The band centred on the centreline — every test here that predates it."""
    return _deck_band(x_from, x_to, -z_half, z_half)


def _graph(polyline: list[list[float]], nodes: list[list[float]]) -> dict:
    """One off-grade edge.

    ⚠️ **The ribbon's offset is NOT here.** It rides on the surface manifest
    beside the half-width, per station, because the clamp cuts the two rails
    independently and a per-edge number cannot say where the ribbon is even on
    one edge (`Q107`). See `_manifest`.
    """
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


def _manifest(*edges: int, offset_m: float = 0.0) -> dict:
    """The surface manifest. `offset_m` is where `surface.py` centres the ribbon.

    Per station in the real thing (`Q107`); constant here, which the readers
    handle by index — one value is read for every vertex past the first.
    """
    return {
        "carriageway": [
            {"edge": edge, "half_width_m": [2.0, 2.0, 2.0], "offset_m": [offset_m] * 3}
            for edge in edges
        ]
    }


def _survey(
    graph: dict,
    structure: Faces,
    *,
    trace: dict[int, list[Station]] | None = None,
    offset_m: float = 0.0,
) -> dict:
    """`survey` with the walk constants fixed, so four tests state them once.

    A change to `survey`'s signature lands in one place here rather than four,
    which is the only thing standing between this file and the drift the tool it
    grades keeps a whole docstring about.
    """
    return survey(
        graph,
        _manifest(*(int(edge["id"]) for edge in graph["edges"]), offset_m=offset_m),
        structure,
        spacing_m=2.0,
        across_m=0.1,
        max_lateral_m=12.0,
        junction_m=3.0,
        attribute_within_m=1.0,
        bridge_m=1.0,
        trace=trace,
    )


def _walk(graph: dict, structure: Faces, offset_m: float = 0.0) -> tuple[dict, list[Station]]:
    trace: dict[int, list[Station]] = {1: []}
    return _survey(graph, structure, trace=trace, offset_m=offset_m), trace[1]


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
    NODES: ClassVar[list[list[float]]] = [[0.0, DECK_Y, 0.0], [20.0, DECK_Y, 0.0]]

    def _run(self) -> tuple[dict, list[Station]]:
        return _walk(_graph(POLYLINE, self.NODES), _deck(0.0, 12.0))

    def test_it_records_one_row_per_walked_station(self) -> None:
        _, series = self._run()
        walked = len(list(walk_width(np.asarray(POLYLINE, dtype=np.float64), 2.0)))
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
        graph = _graph(POLYLINE, TestTheTraceIsAPartition.NODES)
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
        graph = _graph(POLYLINE, TestTheTraceIsAPartition.NODES)
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
        graph = _graph(POLYLINE, TestTheTraceIsAPartition.NODES)
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


class TestClampStation:
    """The counterfactual half-widths (`Q105`), whose failure modes are all silent.

    🔴 **Every one of these renders as a perfectly drawn ribbon.** A clamp with
    an inverted sign narrows the wrong side and draws a road; a clamp that reads
    a negative half as a narrow one prints a plausible width in a table nobody
    can check against a frame. There is no picture to catch either.
    """

    # Ribbon half-width 2.0 throughout, from `_manifest`.
    HALF: ClassVar[float] = 2.0

    def test_it_reproduces_the_overhang_the_walk_ALREADY_recorded(self) -> None:
        """The anti-drift assertion, and the reason this is not a second walk.

        `survey` records `max(0, low + half) + max(0, half - high)` — the sum of
        the two sides the clamp separates — and the paint the clamp gives up is
        that column **exactly and unconditionally**, negative halves included:
        `half - min(half, high) == max(0, half - high)` for every input. A clamp
        that re-derived the rims some other way would agree here at first and
        drift as one of the two changed.
        """
        rows, series = _walk(
            _graph(
                POLYLINE,
                TestTheTraceIsAPartition.NODES,
            ),
            # 🔴 **One rim inside the ribbon and one outside, and neither
            # half of that is decoration.** Where the clamp cuts on BOTH sides
            # the paint given up is `drawn - span` and the offset cancels out
            # of it entirely — so over a centred deck, and over any deck
            # narrower than the ribbon, this test passes unchanged with the
            # offset term deleted outright. That is the covering-nothing state
            # `Q103` caught two of its own tests in. Only a station cut on one
            # side can see it, and the guard below is what says one was reached.
            _deck_band(0.0, 20.0, -4.0, 0.5),
        )
        kept = [station for station in series if not station.refused]
        assert kept, "a walk that kept nothing satisfies every equality below"
        clamps = [
            clamp_station(station.span_m, station.off_centre_m, station.drawn_m) for station in kept
        ]
        assert any(clamp.left_m != pytest.approx(clamp.right_m) for clamp in clamps), (
            "a deck cut on both sides cannot see an offset defect — see the band above"
        )
        for clamp, station in zip(clamps, kept, strict=True):
            assert not clamp.undrawable
            assert clamp.given_up_m == pytest.approx(station.overhang_m)
        assert rows[1].overhang_m

    def test_a_positive_off_centre_narrows_the_LEFT_half(self) -> None:
        """The direction, which an absolute value could not report (`Q78`).

        `off_centre_m` is the centreline in the deck's frame, positive left of
        travel — so a positive reading means the deck lies to the RIGHT and the
        left half is the short one. Inverting the sign inside `clamp_station`
        swaps which side of every ribbon in the region gets cut, and the region
        still renders.
        """
        left_short = clamp_station(span_m=6.0, off_centre_m=+2.0, drawn_m=2.0 * self.HALF)
        assert left_short.left_m < left_short.right_m
        right_short = clamp_station(span_m=6.0, off_centre_m=-2.0, drawn_m=2.0 * self.HALF)
        assert right_short.right_m < right_short.left_m
        centred = clamp_station(span_m=6.0, off_centre_m=0.0, drawn_m=2.0 * self.HALF)
        assert centred.left_m == pytest.approx(centred.right_m)

    def test_a_negative_half_hides_under_a_POSITIVE_sum(self) -> None:
        """🔴 The load-bearing one: the sum is not the detector.

        A deck at `+1 .. +3` under a ribbon at `-2 .. +2` leaves the right half
        at **-1.0** and the left at **+2.0**, so `width_m` is a perfectly
        ordinary **+1.0 m** while the station has no rim on one side at all.
        The pricing run that opened `Q105` counted "0 undrawable" over eight
        such stations for exactly this reason, so `undrawable` reads the two
        halves and never their sum.
        """
        clamp = clamp_station(span_m=2.0, off_centre_m=-2.0, drawn_m=2.0 * self.HALF)
        assert clamp.right_m == pytest.approx(-1.0)
        assert clamp.left_m == pytest.approx(2.0)
        assert clamp.width_m > 0.0
        assert clamp.undrawable

    def test_the_clamp_leaves_no_overhang_at_all(self) -> None:
        """Why `clamp_report` prints no "on deck after the clamp" counter.

        ⚠️ **This pins a claim, not a result.** The property is algebra — a half
        cut to its own rim cannot pass it — and the counter it justifies
        omitting would report that algebra as a finding, which is `Q58`'s trap.
        The test earns its place by failing if `clamp_station` ever stops having
        the property, at which point the omission would need re-arguing.
        """
        for span_m, off_centre_m in ((6.0, 0.0), (2.0, +1.5), (9.0, -3.0), (1.0, 0.0)):
            clamp = clamp_station(span_m, off_centre_m, 2.0 * self.HALF)
            high = 0.5 * span_m - off_centre_m
            low = -0.5 * span_m - off_centre_m
            assert max(0.0, low + clamp.right_m) == pytest.approx(0.0)
            assert max(0.0, clamp.left_m - high) == pytest.approx(0.0)

    def test_a_deck_wider_than_the_ribbon_gives_the_ribbon_back_unchanged(self) -> None:
        """The control row. A clamp that always cuts would fail nothing above."""
        clamp = clamp_station(span_m=40.0, off_centre_m=+1.0, drawn_m=2.0 * self.HALF)
        assert clamp.left_m == pytest.approx(self.HALF)
        assert clamp.right_m == pytest.approx(self.HALF)
        assert clamp.given_up_m == pytest.approx(0.0)
        assert not clamp.undrawable


class TestTheClampAgreesWithTheWalkAboutTheSameStations:
    """`clamp_report`'s ratchet: a negative half IS a centreline off the deck.

    The two are the same geometry read from two sides, so `clamp_report` refuses
    to print when the counts differ. Pinned here against a walk that actually
    reaches the state, because the identity holds trivially over a population
    where neither ever fires.
    """

    def test_the_two_counters_find_the_same_stations(self) -> None:
        rows, series = _walk(
            _graph(POLYLINE, []),
            # Off to one side, so the centreline misses the deck entirely.
            _deck_band(0.0, 20.0, 1.0, 3.0),
        )
        kept = [station for station in series if not station.refused]
        assert kept
        negative = [
            station
            for station in kept
            if clamp_station(station.span_m, station.off_centre_m, station.drawn_m).undrawable
        ]
        assert negative, "the walk never reached the state this test is about"
        assert len(negative) == rows[1].centre_off_deck


class TestPricedWidths:
    """🔴 An undrawable station may not be priced as a narrow road (`Q105`).

    The defect this pins **shipped in the first build of the table it grades**:
    every median, every minimum, the sort key and both bar counts were computed
    over a population that still contained the negative halves, so `e208` was
    published at 0.70 m — a station with a -0.10 m half read as a carriageway.
    Nothing about that output looks wrong; it is a plausible number in a
    plausible column, which is why it is a test and not a comment.
    """

    def test_an_undrawable_station_contributes_no_width(self) -> None:
        drawn, span = 4.0, 2.0
        # `off_centre_m` -2.0 puts the deck at +1 .. +3 under a ribbon at ±2, so
        # the right half is -1.0 while `left + right` is a respectable +1.0.
        bad = clamp_station(span_m=span, off_centre_m=-2.0, drawn_m=drawn)
        good = clamp_station(span_m=6.0, off_centre_m=0.0, drawn_m=drawn)
        assert bad.undrawable and bad.width_m > 0.0, "the fixture must reach the state"
        assert priced_widths({1: [good, bad]}) == {1: [pytest.approx(good.width_m)]}

    def test_an_edge_that_prices_nothing_is_dropped_rather_than_left_to_raise(self) -> None:
        bad = clamp_station(span_m=2.0, off_centre_m=-2.0, drawn_m=4.0)
        assert priced_widths({1: [bad]}) == {}

    def test_it_keeps_every_station_where_both_halves_exist(self) -> None:
        """The control. A filter that dropped everything would pass the two above."""
        series = [
            clamp_station(span_m=6.0, off_centre_m=off, drawn_m=4.0) for off in (-1.0, 0.0, +1.0)
        ]
        assert not any(clamp.undrawable for clamp in series)
        assert len(priced_widths({1: series})[1]) == 3


class TestTheWalkMeasuresTheRibbonThatIsDRAWN:
    """🔴 `surface.py` offsets both rails by `offset_m`, so the walk must too.

    `Q106`. `surface._shape` builds the ribbon at `+half + shift` and
    `-half + shift`, and `Q103` moved 36 off-grade edges onto the middle of
    their own decks — up to 4.95 m. A walk about the published centreline
    therefore measured a ribbon that is not drawn, and it did so **silently**:
    every counter closed, the partition held, and the region read 10.7% hanging
    where the drawn road is 4.3%.

    ⚠️ **`shift` is 0.0 on every level-0 edge**, so the whole level-0 half of
    this repo's instruments is untouched — which is the property that makes the
    change safe, and the one asserted first below.
    """

    # Ribbon half-width 2.0 (`_manifest`), deck 3.0 either side of the
    # centreline (`_deck`), so unshifted the ribbon is comfortably on the deck.
    def _spans(self, offset_m: float) -> tuple[list[float], list[float], list[float]]:
        rows, _ = _walk(_graph(POLYLINE, []), _deck(0.0, 20.0), offset_m)
        return rows[1].span_m, rows[1].off_centre_m, rows[1].overhang_m

    def test_a_zero_offset_reproduces_the_walk_it_replaced(self) -> None:
        """The inertness proof: level 0 publishes no offset and must not move."""
        spans, offs, overs = self._spans(0.0)
        assert spans, "the walk kept nothing"
        assert offs == pytest.approx([0.0] * len(offs))
        assert overs == pytest.approx([0.0] * len(overs))

    def test_the_offset_moves_the_ribbon_and_not_the_deck(self) -> None:
        """A 2.0 m shift puts the 2.0 m half-width ribbon's rail on the deck rim.

        The deck is unmoved, so its span is unchanged; what moves is where the
        ribbon sits inside it, which is exactly the distinction `off_centre_m`
        exists to report.
        """
        base_spans, _, base_overs = self._spans(0.0)
        spans, offs, overs = self._spans(1.0)
        assert spans == pytest.approx(base_spans), "the deck must not move"
        assert offs == pytest.approx([1.0] * len(offs))
        # Still inside: rims are 3.0 - 1.0 = 2.0 left and 3.0 + 1.0 = 4.0 right,
        # against a 2.0 m half-width, so nothing hangs — as at zero.
        assert overs == pytest.approx(base_overs)

    def test_a_shift_past_the_rim_hangs_where_the_unshifted_ribbon_did_not(self) -> None:
        _, _, base_overs = self._spans(0.0)
        _, offs, overs = self._spans(2.0)
        assert max(base_overs) == pytest.approx(0.0)
        # Left rim 3.0 - 2.0 = 1.0 against a 2.0 m half: 1.0 m of ribbon in air.
        assert overs == pytest.approx([1.0] * len(overs))
        assert offs == pytest.approx([2.0] * len(offs))

    def test_a_shift_off_the_deck_entirely_is_counted_as_such(self) -> None:
        rows, _ = _walk(_graph(POLYLINE, []), _deck(0.0, 20.0), 4.0)
        assert rows[1].span_m, "the walk kept nothing"
        assert rows[1].centre_off_deck == len(rows[1].span_m)
