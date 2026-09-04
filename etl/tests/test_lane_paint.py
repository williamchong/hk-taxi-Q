"""The probe on `tools/lane_paint.py` (`Q113`).

The same standard the other tool tests keep: only the parts whose failure mode is
**silent**. The per-edge table grades itself — a walk that stopped walking would
print no rows and a divisor that vanished would raise — and what would not
announce itself is everything here.

🔴 **The divisor is the one that has already gone wrong once in this repo, on a
neighbouring layer.** `roadmarks.underfill_m` was measured against the graph's
authored `width_m` instead of the drawn half-width and read p50 0.22 m against a
true 4.04 — an 18x error that printed a full, plausible distribution. This tool
asks the same question of the same two frames, so `TestTheStripIsTheDrawnRibbon`
pins it against a fixture where the two disagree, and by a factor rather than by
an epsilon.

🔴 **And the second is the per-station read.** `Q113`'s whole defect is a ribbon
that narrows at four vertices out of twenty-five; a tool that took one
half-width for the edge would report `e208` at its published width and find
nothing at all, with a table nobody could tell from a clean bill.

⚠️ **`narrow_points` is pinned by ORIENTATION, not by its numbers.** The house
convention in this repo is p50/p90/p99/max, and every other grader here uses it —
so the standing risk is somebody "restoring consistency" and turning a
narrow-tail reading into a wide-tail one, which prints four plausible metres and
reports the widest roads in the region.
"""

from __future__ import annotations

import numpy as np
import pytest
from lane_paint import (
    Edge,
    narrow_points,
    render,
    render_by_class,
    survey,
)


def _graph(edges: list[dict]) -> dict:
    """A road graph carrying exactly the fields this tool reads."""
    return {"edges": edges}


def _edge(
    edge_id: int,
    *,
    polyline: list[list[float]],
    lanes: int = 2,
    lanes_source: str = "authored",
    width_m: float = 6.4,
    width_source: str = "authored",
    direction: str = "forward",
    level: int = 0,
) -> dict:
    return {
        "id": edge_id,
        "polyline": polyline,
        "lanes": lanes,
        "lanes_source": lanes_source,
        "width_m": width_m,
        "width_source": width_source,
        "direction": direction,
        "elevation_level": level,
        "road_name": {"en": f"STREET {edge_id}"},
    }


def _manifest(carriageway: list[dict]) -> dict:
    return {"carriageway": carriageway}


def _bounds(hong_kong):
    return hong_kong.carriageway_survey.width_bounds


# A straight run with a vertex in the middle: three stations, two 10 m segments.
STRAIGHT = [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [20.0, 0.0, 0.0]]


class TestTheStripIsTheDrawnRibbon:
    """The strip comes from `city.json`'s half-width, never the graph's `width_m`."""

    def test_the_drawn_ribbon_and_not_the_published_width(self, hong_kong):
        """A widened edge paints the widened lane, not the surveyed one.

        The two differ by the playability floor on most of the region — 10.24 m
        drawn over a 6.40 m authored width — so a tool reading `width_m` reports
        a 3.20 m lane where the shader paints 5.12 m. That is the same frame
        error `roadmarks.underfill_m` shipped, at a 1.6x rather than an 18x.
        """
        rows = survey(
            _graph([_edge(1, polyline=STRAIGHT, lanes=2, width_m=6.4)]),
            _manifest([{"edge": 1, "half_width_m": [5.12, 5.12, 5.12]}]),
            _bounds(hong_kong),
        )
        assert rows[0].narrowest_m == pytest.approx(5.12)
        assert rows[0].narrowest_m != pytest.approx(6.4 / 2)

    def test_the_half_width_is_read_at_every_vertex(self, hong_kong):
        """A ribbon that narrows at one station is read at that station.

        `Q113`'s defect is four vertices of twenty-five. Reading one half-width
        for the whole edge — which is what a pre-`Q23` bundle publishes and what
        `half_width_at` degrades to — finds nothing and prints a clean table.
        """
        rows = survey(
            _graph([_edge(1, polyline=STRAIGHT, lanes=2)]),
            _manifest([{"edge": 1, "half_width_m": [5.12, 5.12, 1.60]}]),
            _bounds(hong_kong),
        )
        assert rows[0].narrowest_m == pytest.approx(1.60)
        assert int(rows[0].thin(2.5).sum()) == 1

    def test_the_divisor_is_the_lane_count(self, hong_kong):
        """Doubling the count halves the strip, on an unmoved ribbon.

        The shader's own arithmetic — `surface._u_metres` — restated as the
        claim under test rather than as a comment.
        """
        ribbon = _manifest([{"edge": 1, "half_width_m": [5.12, 5.12, 5.12]}])
        two = survey(_graph([_edge(1, polyline=STRAIGHT, lanes=2)]), ribbon, _bounds(hong_kong))
        four = survey(_graph([_edge(1, polyline=STRAIGHT, lanes=4)]), ribbon, _bounds(hong_kong))
        assert two[0].narrowest_m == pytest.approx(2.0 * four[0].narrowest_m)


class TestNarrowPoints:
    """The distribution reports the narrow tail, and would be silent reversed."""

    def test_the_points_are_the_narrow_end(self):
        """min, p1, p10, p50 — in that order and no others."""
        values = np.arange(1.0, 101.0)
        assert narrow_points(values) == pytest.approx(
            (
                1.0,
                float(np.percentile(values, 1)),
                float(np.percentile(values, 10)),
                float(np.percentile(values, 50)),
            )
        )

    def test_the_house_wide_tail_table_would_miss_the_defect(self):
        """One thin strip among wide ones moves the narrow points and not p90.

        🔴 The mutation this file exists for. A population of 5.12 m lanes with
        a single 1.15 m among them is exactly the region, and the house
        p50/p90/p99/max table reports **5.12 on all four points** — a clean bill
        over the defect.
        """
        values = np.concatenate([np.full(99, 5.12), [1.15]])
        low, _, _, median = narrow_points(values)
        assert low == pytest.approx(1.15)
        assert median == pytest.approx(5.12)
        assert float(np.percentile(values, 90)) == pytest.approx(5.12)

    def test_an_empty_population_is_zeroes(self):
        assert narrow_points(np.array([])) == (0.0, 0.0, 0.0, 0.0)


class TestVerdict:
    """The width-versus-count verdict, and the state that must not read as agreement."""

    def test_it_is_reachable_both_ways(self, hong_kong):
        """A flag that cannot be raised is `Q72`'s tautology.

        Two edges, one ribbon, differing only in the count they publish over the
        same measured width.
        """
        ribbon = _manifest(
            [
                {"edge": 1, "half_width_m": [2.9, 2.9, 2.9]},
                {"edge": 2, "half_width_m": [2.9, 2.9, 2.9]},
            ]
        )
        rows = survey(
            _graph(
                [
                    _edge(1, polyline=STRAIGHT, lanes=1, width_m=5.8, width_source="deck"),
                    _edge(2, polyline=STRAIGHT, lanes=3, width_m=5.8, width_source="deck"),
                ]
            ),
            ribbon,
            _bounds(hong_kong),
        )
        by_id = {row.id: row for row in rows}
        assert by_id[1].verdict == "within"
        assert by_id[2].verdict == "over"

    def test_an_AUTHORED_width_grades_nothing(self, hong_kong):
        """🔴 It is `lanes x lane_width_m` exactly, so bracketing it is circular.

        Every one of this region's 469 authored edges divides to 3.2 to six
        places, so the bracket would be fed the quantity under test and `over`
        is unreachable by construction — `carriageway_margin.lane_bracket`'s own
        refusal, applying to this caller as much as to that tool. The
        three-state verdict already has the right answer for it.

        ⚠️ **The second half is the point**: the same count over a width a
        publisher licensed still reads `over`, so this is a refusal to grade a
        circular reading and not a bar that hides a finding.
        """
        ribbon = _manifest([{"edge": 1, "half_width_m": [2.9, 2.9, 2.9]}])
        authored = survey(
            _graph([_edge(1, polyline=STRAIGHT, lanes=3, width_m=9.6)]),
            ribbon,
            _bounds(hong_kong),
        )
        assert authored[0].verdict == "ungraded"
        assert authored[0].bracket is None

        measured = survey(
            _graph([_edge(1, polyline=STRAIGHT, lanes=3, width_m=5.8, width_source="deck")]),
            ribbon,
            _bounds(hong_kong),
        )
        assert measured[0].verdict == "over"

    def test_no_bracket_is_its_own_state_and_not_agreement(self):
        """A city with no through-lane range grades nothing, and says so.

        🔴 The mutation this class exists for. Collapsed to a boolean, a missing
        bracket returns `False` and is counted among the rows the width endorses
        — so the split line prints `0 over the bracket` on a population nothing
        graded, which is `Q58`'s trap reachable from a config file. The three
        states are what keep `within` and `ungraded` apart.
        """
        row = Edge(
            id=1,
            name="STREET 1",
            level=0,
            lanes=9,
            lanes_source="authored",
            width_m=3.0,
            width_source="authored",
            two_way=False,
            bracket=None,
            strip_m=np.array([1.0]),
            station_m=np.array([1.0]),
        )
        assert row.verdict == "ungraded"
        assert row.verdict != "within"

    def test_the_ungraded_state_reaches_the_table_and_the_split(self):
        """It is printed rather than merely modelled.

        A state the reports cannot show is a state that does not exist for a
        reader, which is the whole complaint against the boolean.
        """
        row = Edge(
            id=1,
            name="STREET 1",
            level=0,
            lanes=9,
            lanes_source="authored",
            width_m=3.0,
            width_source="authored",
            two_way=False,
            bracket=None,
            strip_m=np.array([1.0]),
            station_m=np.array([1.0]),
        )
        assert "?" in "\n".join(render([row], bar_m=2.5, undrawn=0))
        assert "1 have no bracket" in "\n".join(render_by_class([row], 2.5))


class TestTheTwoCountsAreDifferentQuestions:
    """Edges, vertices and metres are three readings and not one.

    `Q113`'s own correction at `_deck_rims`: the record first published the
    edges a rim was discarded on and not the ribbons that moved, and they are
    different numbers. Here an edge thin at one station of three must not be
    counted as a thin edge's worth of road.
    """

    def test_one_thin_station_is_one_station(self, hong_kong):
        rows = survey(
            _graph([_edge(1, polyline=STRAIGHT, lanes=2)]),
            _manifest([{"edge": 1, "half_width_m": [5.12, 5.12, 1.00]}]),
            _bounds(hong_kong),
        )
        row = rows[0]
        assert row.narrowest_m == pytest.approx(1.0)
        assert int(row.thin(2.5).sum()) == 1
        assert row.thin_m(2.5) == pytest.approx(5.0)
        assert row.length_m == pytest.approx(20.0)


class TestSurveyRefusals:
    """What is left out, and why leaving it out is not a silent hole."""

    def test_an_undrawn_edge_carries_no_reading(self, hong_kong):
        """No ribbon, no strip — and never a zero, which would sort first.

        A published edge the surface stage drew nothing for has no lane to
        measure. Giving it 0.0 would put it at the head of the table as the
        worst row in the region.
        """
        rows = survey(
            _graph([_edge(1, polyline=STRAIGHT), _edge(2, polyline=STRAIGHT)]),
            _manifest([{"edge": 1, "half_width_m": [5.12, 5.12, 5.12]}]),
            _bounds(hong_kong),
        )
        assert [row.id for row in rows] == [1]

    def test_a_zero_lane_edge_is_refused_loudly(self, hong_kong):
        """`surface.MarkingCode` refuses it, so a bundle carrying it is malformed.

        Louder than a divide by zero, which would print `inf` into the widest
        column of a table that reads small-is-bad.
        """
        with pytest.raises(SystemExit):
            survey(
                _graph([_edge(1, polyline=STRAIGHT, lanes=0)]),
                _manifest([{"edge": 1, "half_width_m": [5.12, 5.12, 5.12]}]),
                _bounds(hong_kong),
            )


class TestRender:
    """The table says which rows the width disagrees with the count on."""

    def test_the_disagreement_is_marked(self, hong_kong):
        rows = survey(
            _graph([_edge(1, polyline=STRAIGHT, lanes=3, width_m=5.8, width_source="deck")]),
            _manifest([{"edge": 1, "half_width_m": [2.9, 2.9, 2.9]}]),
            _bounds(hong_kong),
        )
        table = "\n".join(render(rows, bar_m=2.5, undrawn=0))
        assert "e1" in table
        assert "1-1!" in table

    def test_a_clean_region_says_so(self, hong_kong):
        rows = survey(
            _graph([_edge(1, polyline=STRAIGHT, lanes=2)]),
            _manifest([{"edge": 1, "half_width_m": [5.12, 5.12, 5.12]}]),
            _bounds(hong_kong),
        )
        assert "nothing under the bar." in "\n".join(render(rows, bar_m=2.5, undrawn=0))
