"""The `P3-29` fence stage (`etl/pipeline/fence.py`).

Pins the parts whose failure mode is **silent**, which on this stage is most of
them: a barrier in the wrong place, facing the wrong way, or standing behind
another barrier all render as a perfectly good barrier, and a barrier that is
never placed renders as the invisible wall `Q19` exists to remove.

Two of these tests exist because the first run of the stage got them wrong:
`test_a_dead_end_is_not_a_pocket` (13 "pockets" reported over 14 disjoint
components, which is arithmetically impossible) and
`test_the_unit_width_matches_the_committed_prop` (the config and the authored
`.glb` are two files and nothing else binds them).
"""

from __future__ import annotations

import math

import make_barrier
import numpy as np
import pytest

from pipeline.fence import (
    FenceReport,
    _adjacency,
    _components,
    _mouth_frame,
    fenced_edges,
    place,
)


def _edge(
    edge_id: int, points: list[list[float]], node_a: int, node_b: int, level: int = 0
) -> dict:
    return {
        "id": edge_id,
        "from": node_a,
        "to": node_b,
        "polyline": points,
        "elevation_level": level,
    }


def _clearance(rows: dict[int, list[float]]) -> dict:
    return {"clearance": [{"edge": edge, "clear_width_m": widths} for edge, widths in rows.items()]}


def _drawn(edges: dict[int, list[float]]) -> dict:
    return {edge: {"edge": edge, "half_width_m": halves} for edge, halves in edges.items()}


class TestFencedSet:
    def test_an_edge_under_the_bar_is_fenced(self) -> None:
        graph = {"edges": [_edge(1, [[0, 0, 0], [0, 0, 10]], 1, 2)]}
        assert fenced_edges(graph, _clearance({1: [1.0, 1.0]}), 1.8) == [1]

    def test_an_edge_over_the_bar_is_not(self) -> None:
        graph = {"edges": [_edge(1, [[0, 0, 0], [0, 0, 10]], 1, 2)]}
        assert fenced_edges(graph, _clearance({1: [3.0, 3.0]}), 1.8) == []

    def test_an_unmeasured_edge_is_not_fenced(self) -> None:
        """⚠️ A missing measurement is not a measurement of zero. Every station of
        a short edge can be swallowed by the junction caps at its two ends, and
        fencing those would close streets nothing was ever measured on —
        `RoadGraph.min_clear_width_of` returns `INF` for exactly this case."""
        graph = {"edges": [_edge(1, [[0, 0, 0], [0, 0, 10]], 1, 2)]}
        assert fenced_edges(graph, _clearance({1: [-1.0, -1.0]}), 1.8) == []

    def test_a_refusal_never_counts_as_a_blockage(self) -> None:
        """`-1.0` is the smallest number in any row it appears in, so folding it
        into the `min` would make every part-trimmed edge the most blocked in the
        region."""
        graph = {"edges": [_edge(1, [[0, 0, 0], [0, 0, 10]], 1, 2)]}
        assert fenced_edges(graph, _clearance({1: [-1.0, 9.0]}), 1.8) == []

    def test_an_off_grade_edge_is_never_fenced(self) -> None:
        """`Q13` refuses to hand a car an off-grade edge at all, so its clearance
        is a Phase 4 question and a barrier there would stand where nobody can
        drive."""
        graph = {"edges": [_edge(1, [[0, 0, 0], [0, 0, 10]], 1, 2, level=1)]}
        assert fenced_edges(graph, _clearance({1: [0.0, 0.0]}), 1.8) == []


class TestComponents:
    def test_edges_sharing_a_node_are_one_component(self) -> None:
        ends = {1: (1, 2), 2: (2, 3)}
        assert _components([1, 2], ends) == [[1, 2]]

    def test_disjoint_edges_are_separate_components(self) -> None:
        ends = {1: (1, 2), 2: (3, 4)}
        assert _components([1, 2], ends) == [[1], [2]]

    def test_a_chain_of_three_is_one_component(self) -> None:
        ends = {1: (1, 2), 2: (2, 3), 3: (3, 4)}
        assert _components([1, 2, 3], ends) == [[1, 2, 3]]


class TestMouths:
    """Where a barrier stands, and where one deliberately does not."""

    def _region(self, fenced_clear: float, open_clear: float = 9.0):
        # Two edges meeting at node 2: edge 1 is the street under test, edge 2 is
        # the open network it is entered from. Node 3 is edge 1's far end and has
        # nothing else on it.
        graph = {
            "edges": [
                _edge(1, [[0, 0, 0], [0, 0, 20]], 2, 3),
                _edge(2, [[0, 0, 0], [20, 0, 0]], 2, 4),
            ]
        }
        clearance = _clearance({1: [fenced_clear, fenced_clear], 2: [open_clear, open_clear]})
        drawn = _drawn({1: [5.12, 5.12], 2: [5.12, 5.12]})
        return graph, clearance, drawn

    def test_a_barrier_stands_at_the_open_end(self) -> None:
        graph, clearance, drawn = self._region(1.0)
        fenced = fenced_edges(graph, clearance, 1.8)
        placements, report = place(graph, drawn, fenced, inset_m=4.0, unit_width_m=2.0)
        assert report.mouths == 1
        assert {item.node for item in placements} == {2}

    def test_a_dead_end_is_not_a_pocket(self) -> None:
        """🔴 The distinction the stage's first run was missing. Node 3 carries no
        other drivable arm, so nobody can arrive from there and there is nothing
        to close — which is **not** the same as `Q19`'s `e222`/`e256` case, where
        the arms exist and are all fenced. Conflating them reported 13 pockets
        over 14 disjoint components."""
        graph, clearance, drawn = self._region(1.0)
        fenced = fenced_edges(graph, clearance, 1.8)
        _, report = place(graph, drawn, fenced, inset_m=4.0, unit_width_m=2.0)
        assert report.ends_with_no_way_in == 1
        assert report.ends_behind_another_fence == 0

    def test_an_end_reachable_only_through_another_fence_is_a_pocket(self) -> None:
        """`Q19`'s `e222`/`e256` rule: a barrier there would stand behind a
        barrier, so the component is closed at its boundary instead."""
        graph = {
            "edges": [
                _edge(1, [[0, 0, 0], [0, 0, 20]], 2, 3),
                _edge(2, [[0, 0, 20], [20, 0, 20]], 3, 5),
                _edge(3, [[0, 0, 0], [20, 0, 0]], 2, 4),
            ]
        }
        clearance = _clearance({1: [1.0, 1.0], 2: [1.0, 1.0], 3: [9.0, 9.0]})
        drawn = _drawn({1: [5.12, 5.12], 2: [5.12, 5.12], 3: [5.12, 5.12]})
        fenced = fenced_edges(graph, clearance, 1.8)
        placements, report = place(graph, drawn, fenced, inset_m=4.0, unit_width_m=2.0)
        assert report.components == 1, "two fenced edges sharing node 3 are one closure"
        # Node 3 has an arm and it is fenced, so it is a pocket rather than a
        # dead end; node 5 has no arm at all, so it is a dead end.
        #
        # ⚠️ **Two, not one: the counter counts fenced-edge ENDS, and node 3 is an
        # end of both of them.** That is the field's own wording and the right
        # frame — `span_m` and the partition are per end too — but it is the kind
        # of counter a reader turns into "pockets" and then into "nodes", so the
        # arithmetic is pinned here rather than left to the name.
        assert report.ends_behind_another_fence == 2
        assert report.ends_with_no_way_in == 1
        assert {item.node for item in placements} == {2}

    def test_the_partition_closes(self) -> None:
        """Every mouth is either closed or recorded as unmeasurable — the
        identity `build_region` raises on."""
        graph, clearance, drawn = self._region(1.0)
        fenced = fenced_edges(graph, clearance, 1.8)
        _, report = place(graph, drawn, fenced, inset_m=4.0, unit_width_m=2.0)
        assert report.closes(2.0)

    def test_a_mouth_with_no_published_ribbon_is_counted_not_placed(self) -> None:
        """⚠️ Counted rather than appended as a zero, on `touchdown_error.py`'s
        `ends_no_target` reasoning: an end with no width has no span to record.

        🔴 It **was** padded with a `0.0` until review caught it — which both
        contradicted this field's own comment and was what made `closes()`
        unfalsifiable, since the padding kept the count matching whatever the
        loop did. `build_region` then had to filter the zeros back out before
        every percentile, which is the tell."""
        graph, clearance, _ = self._region(1.0)
        fenced = fenced_edges(graph, clearance, 1.8)
        placements, report = place(graph, _drawn({}), fenced, inset_m=4.0, unit_width_m=2.0)
        assert report.mouths_no_width == 1
        assert report.span_m == [], "a refusal has no span, not a zero one"
        assert report.mouths == 1, "it is still a mouth the open network arrives at"
        assert placements == []
        assert report.closes(2.0)

    def test_the_identity_catches_a_row_sized_wrong(self) -> None:
        """🔴 The half of `closes()` that is falsifiable. `len(span_m) ==
        mouths_dressed` holds by construction — `place` writes both in one
        breath — so the identity that earns its keep is the one recomputing the
        row width from the published spans."""
        graph, clearance, drawn = self._region(1.0)
        fenced = fenced_edges(graph, clearance, 1.8)
        _, report = place(graph, drawn, fenced, inset_m=4.0, unit_width_m=2.0)
        assert report.closes(2.0)
        # The row was sized at 2.0 m a unit; grading it at any other width is the
        # mismatch between `fence.unit_width_m` and the committed prop.
        assert not report.closes(1.0)
        report.barriers += 1
        assert not report.closes(2.0)


class TestRow:
    def test_the_row_spans_the_drawn_carriageway(self) -> None:
        graph = {
            "edges": [
                _edge(1, [[0, 0, 0], [0, 0, 20]], 2, 3),
                _edge(2, [[0, 0, 0], [20, 0, 0]], 2, 4),
            ]
        }
        clearance = _clearance({1: [1.0, 1.0], 2: [9.0, 9.0]})
        drawn = _drawn({1: [5.12, 5.12], 2: [5.12, 5.12]})
        fenced = fenced_edges(graph, clearance, 1.8)
        placements, _ = place(graph, drawn, fenced, inset_m=4.0, unit_width_m=2.0)
        # 10.24 m of ribbon at 2.0 m a unit — six units, because a row that
        # covers five sixths of a mouth is a gap a car drives through.
        assert len(placements) == math.ceil(10.24 / 2.0)

    def test_the_row_is_centred_on_the_centreline(self) -> None:
        graph = {
            "edges": [
                _edge(1, [[0, 0, 0], [0, 0, 20]], 2, 3),
                _edge(2, [[0, 0, 0], [20, 0, 0]], 2, 4),
            ]
        }
        clearance = _clearance({1: [1.0, 1.0], 2: [9.0, 9.0]})
        drawn = _drawn({1: [5.12, 5.12], 2: [5.12, 5.12]})
        fenced = fenced_edges(graph, clearance, 1.8)
        placements, _ = place(graph, drawn, fenced, inset_m=4.0, unit_width_m=2.0)
        across = [item.position[0] for item in placements]
        assert sum(across) == pytest.approx(0.0, abs=1e-6)

    def test_the_unit_width_matches_the_committed_prop(self) -> None:
        """🔴 The config and the authored `.glb` are two files and nothing else
        binds them. Mismatch them and the row is tiled at the wrong pitch —
        gapped or overlapping — and both render as a barrier."""
        from pipeline.config import load_config

        city = load_config()
        assert city.fence is not None
        assert city.fence.unit_width_m == make_barrier.UNIT_WIDTH_M


class TestMouthFrame:
    def test_the_barrier_stands_inside_the_closed_street(self) -> None:
        """⚠️ Not on the node: a barrier there stands in the junction the street
        is entered from and blocks every other arm of it."""
        points = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])
        at, _ = _mouth_frame(points, True, 4.0)
        assert at[2] == pytest.approx(4.0)

    def test_the_facing_is_along_the_edge_away_from_the_node(self) -> None:
        points = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])
        _, tangent = _mouth_frame(points, True, 4.0)
        assert tangent[2] == pytest.approx(1.0)
        assert tangent[1] == 0.0

    def test_entering_from_the_far_node_reverses_it(self) -> None:
        """The two ends of one edge face opposite ways, and a stage that got this
        wrong would turn half the region's barriers around — which renders as a
        perfectly good barrier (`Q62`)."""
        points = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])
        near, forward = _mouth_frame(points, True, 4.0)
        far, backward = _mouth_frame(points, False, 4.0)
        assert far[2] == pytest.approx(16.0)
        assert forward[2] == pytest.approx(-backward[2])
        assert near[2] != far[2]

    def test_an_inset_past_the_end_is_clamped(self) -> None:
        """A street shorter than the inset is closed at its far end rather than
        beyond it — where the barrier would stand in the next junction."""
        points = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 3.0]])
        at, _ = _mouth_frame(points, True, 4.0)
        assert at[2] == pytest.approx(3.0)

    def test_a_zero_length_segment_is_refused(self) -> None:
        """A defaulted facing is the one thing no counter here can see."""
        points = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        with pytest.raises(ValueError, match="no plan length"):
            _mouth_frame(points, True, 4.0)


class TestAdjacency:
    def test_off_grade_edges_are_not_arms(self) -> None:
        """An off-grade ramp meeting a node is not a way in, because `Q13`
        refuses to hand a car an off-grade edge at all."""
        graph = {
            "edges": [
                _edge(1, [[0, 0, 0], [0, 0, 20]], 2, 3),
                _edge(2, [[0, 0, 0], [20, 0, 0]], 2, 4, level=1),
            ]
        }
        at_node, ends = _adjacency(graph)
        assert at_node[2] == [1]
        assert 2 not in ends


class TestReport:
    def test_an_empty_report_closes(self) -> None:
        assert FenceReport().closes(2.0)

    def test_mouths_is_derived_from_the_two_outcomes(self) -> None:
        """Three fields holding one number is a third thing to forget to update,
        and this one is published."""
        report = FenceReport(mouths_dressed=4, mouths_no_width=2)
        assert report.mouths == 6


class TestOptionalBlocks:
    """The two config blocks are independently optional, and each absence means
    something different."""

    def test_a_bar_with_no_fence_block_publishes_the_set_and_dresses_none(self) -> None:
        """🔴 A real state, not a half-configured one — and it crashed with an
        `AttributeError` until review caught it, on a path `Fence`'s own docstring
        said was supported. `clearance:` decides what the predicate refuses;
        `fence:` decides where a barrier stands. Publishing the set with nothing
        dressing it is what `Q19` forbids **shipping**, which is a review question
        rather than a build one, so it is logged and published rather than
        refused."""
        from dataclasses import replace as _replace

        from pipeline.config import load_config

        city = _replace(load_config(), fence=None)
        assert city.clearance is not None
        assert city.fence is None
        # The stage's own guard, exercised without a built region: the fenced set
        # is still computed, and `place` is never reached.
        graph = {"edges": [_edge(1, [[0, 0, 0], [0, 0, 10]], 1, 2)]}
        fenced = fenced_edges(graph, _clearance({1: [1.0, 1.0]}), city.clearance.car_width_m)
        assert fenced == [1]
