"""The `Q51` clearance stage (`pipeline/clearance.py`).

The same standard as `test_carriageway_occupancy.py`, which grades what this
publishes: pin only the parts whose failure mode is **silent**. A sweep that
stopped finding occupiers at all would report the whole region clear and be
caught by the first drive, let alone by the grader. What would not announce
itself is everything below.

Two of these are defects this stage actually shipped and had to be fixed, and
both produced a full, plausible table:

- ✅ **Measuring at the polyline's own vertices.** `roads.py` simplifies to
  0.2 m, so a straight street is *two* stations — its ends — and those are
  exactly the stretch the junction trims remove. The first draft measured
  nothing whatever on every two-vertex edge and published a complete-looking
  table of refusals. `TestWalk` holds both halves: that the trims are honoured
  and that a two-vertex edge is still measured.
- ✅ **A clearance wider than the road it was measured across.** `ACROSS_M` does
  not divide every carriageway, so an unobstructed 10.24 m street measured as
  41 clear samples and published 10.25 m. `TestMeasure` holds the clamp.

⚠️ What has **no unit test here and would most want one**: `occupy`'s prune,
which drops any triangle whose height range misses every band or whose plan box
covers no carriageway. It is a superset test, so a bug in it removes occupiers
silently and every sample behind them reads clear. Its only guard today is that
the prune is built from the very samples the survey consumes — and that removing
it changed no published number, which is evidence rather than a test.
"""

from __future__ import annotations

import argparse
from typing import Any, cast

import numpy as np
import pytest

from pipeline.clearance import (
    ACROSS_M,
    ALONG_M,
    LEVELS,
    MAX_SUBDIVISIONS,
    NOT_MEASURED,
    PIECE_BUDGET,
    SUBDIVIDE_M,
    ClearanceReport,
    _across,
    _batches,
    _levels_argument,
    _longest_clear,
    _plan_steps,
    _spread,
    _subdivide,
    _write,
    measure,
    walk,
    wears,
)
from pipeline.config import load_config
from pipeline.surface import mitres


def _split(corners: np.ndarray) -> np.ndarray:
    return _subdivide(corners, _plan_steps(corners).steps)


def _edge(edge_id: int, points: list[list[float]], *, level: int = 0) -> dict:
    return {"id": edge_id, "polyline": points, "elevation_level": level}


def _drawn(
    edge_id: int,
    halves: list[float],
    trim: tuple[float, float],
    offsets: list[float] | None = None,
) -> dict:
    """One edge of the carriageway table `roadsurface.json` publishes.

    ⚠️ **`offset_m` defaults to zeros here and is REQUIRED by `walk`**, which is
    not a contradiction: the manifest is schema-pinned, so the pipeline always
    carries one, and defaulting in the helper keeps the tests that are about
    something else from restating a zero. The tests that are about the offset
    pass one.
    """
    return {
        edge_id: {
            "half_width_m": halves,
            "offset_m": [0.0] * len(halves) if offsets is None else offsets,
            "trim_m": list(trim),
        }
    }


class TestLongestClear:
    """The widest continuous run, which is the whole criterion."""

    def test_all_clear_is_the_whole_section(self) -> None:
        assert _longest_clear(np.zeros(8, dtype=bool)) == 8

    def test_all_blocked_is_nothing(self) -> None:
        assert _longest_clear(np.ones(8, dtype=bool)) == 0

    def test_takes_the_widest_run_not_the_total(self) -> None:
        # Four clear samples in two gaps of two, and one gap of three. A car
        # needs one gap it fits through, not the sum of the gaps beside it.
        flags = np.array([0, 0, 1, 0, 0, 0, 1, 0, 0], dtype=bool)
        assert _longest_clear(flags) == 3

    def test_a_run_against_the_end_counts(self) -> None:
        assert _longest_clear(np.array([0, 0, 0, 1], dtype=bool)) == 3
        assert _longest_clear(np.array([1, 0, 0, 0], dtype=bool)) == 3


class TestSpread:
    def test_expands_counts_into_group_and_position(self) -> None:
        group, within = _spread(np.array([2, 0, 3]))
        assert group.tolist() == [0, 0, 2, 2, 2]
        assert within.tolist() == [0, 1, 0, 1, 2]


class TestSubdivide:
    """Split by *plan* extent, which is the point of the whole routine."""

    def test_a_small_triangle_is_left_whole(self) -> None:
        corners = np.array([[[0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.0, 0.0, 0.2]]])
        assert len(_split(corners)) == 1

    def test_a_tall_thin_wall_is_left_whole(self) -> None:
        # A hundred metres tall and centimetres across in plan: splitting it by
        # edge length would shatter it into thousands of pieces for nothing,
        # because its height range is already exact over its own footprint.
        corners = np.array([[[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.0, 100.0, 0.0]]])
        assert len(_split(corners)) == 1

    def test_a_wide_face_is_split(self) -> None:
        corners = np.array([[[0.0, 0.0, 0.0], [8.0, 0.0, 0.0], [0.0, 0.0, 8.0]]])
        pieces = _split(corners)
        assert len(pieces) > 1
        plan = pieces[:, :, [0, 2]]
        span = (plan.max(axis=1) - plan.min(axis=1)).max()
        assert span <= SUBDIVIDE_M + 1e-9

    def test_the_pieces_cover_the_original_area(self) -> None:
        corners = np.array([[[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [0.0, 0.0, 4.0]]])
        pieces = _split(corners)
        plan = pieces[:, :, [0, 2]]
        edges = plan[:, 1:] - plan[:, :1]
        area = 0.5 * np.abs(edges[:, 0, 0] * edges[:, 1, 1] - edges[:, 0, 1] * edges[:, 1, 0])
        assert area.sum() == pytest.approx(8.0)


class TestBatches:
    """The piece budget that keeps one hero mesh off the pipeline's memory peak."""

    def test_every_triangle_lands_in_exactly_one_batch(self) -> None:
        steps = np.random.default_rng(0).integers(1, MAX_SUBDIVISIONS + 1, size=5000)
        covered = [index for start, end in _batches(steps) for index in range(start, end)]
        assert covered == list(range(len(steps)))

    def test_a_small_mesh_is_one_batch(self) -> None:
        assert _batches(np.ones(10, dtype=np.int64)) == [(0, 10)]

    def test_no_batch_runs_far_past_the_budget(self) -> None:
        steps = np.full(5000, MAX_SUBDIVISIONS, dtype=np.int64)
        # One triangle's worth of overshoot is allowed and unavoidable — the cut
        # lands after the piece that crossed the line. Anything more means the
        # budget is not bounding the batch it names.
        largest = MAX_SUBDIVISIONS**2
        assert all(
            int((steps[a:b] ** 2).sum()) <= PIECE_BUDGET + largest for a, b in _batches(steps)
        )


class TestWears:
    """The inverse of `colour_for`'s jitter, used here only to find the ground."""

    def test_an_exact_colour_matches_without_jitter(self) -> None:
        colours = np.array([[95, 90, 81, 255]], dtype=np.uint8)
        assert wears(colours, (95, 90, 81), 0.0).tolist() == [True]

    def test_another_class_does_not(self) -> None:
        colours = np.array([[120, 120, 120, 255]], dtype=np.uint8)
        assert wears(colours, (95, 90, 81), 0.0).tolist() == [False]

    def test_a_darker_shade_of_the_same_ray_matches_under_jitter(self) -> None:
        # `colour_for` scales all three channels by one factor, so a jittered
        # class occupies a ray from black through its base colour rather than a
        # single value. 0.94 of the base is inside a 0.06 jitter.
        base = (100, 100, 100)
        colours = np.array([[94, 94, 94, 255]], dtype=np.uint8)
        assert wears(colours, base, 0.06).tolist() == [True]
        assert wears(colours, base, 0.0).tolist() == [False]


class TestWalk:
    """Where the cross-sections are — the half this stage got wrong first."""

    def test_a_two_vertex_edge_is_still_measured(self) -> None:
        # The defect that made this stage's first draft useless: both stations
        # of a straight street are its ends, and both ends are trimmed.
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])]}
        corridor, report = walk(graph, _drawn(1, [3.2, 3.2], (5.0, 5.0)))
        assert report.edges == 1
        assert len(corridor.section_count) > 0
        assert set(corridor.section_station.tolist()) <= {0, 1}

    def test_the_trimmed_ends_are_never_judged(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])]}
        corridor, _ = walk(graph, _drawn(1, [3.2, 3.2], (5.0, 4.0)))
        # Reconstructed from the samples themselves rather than from the
        # arithmetic above, so this fails if the skip stops being applied.
        along = np.unique(np.round(corridor.z, 3))
        assert along.min() >= 5.0 - ALONG_M
        assert along.max() <= 16.0 + ALONG_M

    def test_an_edge_shorter_than_its_own_caps_is_refused_not_crashed(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 4.0]])]}
        with pytest.raises(SystemExit):
            # The only edge in the graph is wholly inside its junction caps, so
            # nothing is measurable and the stage says so rather than writing an
            # empty table that reads as a clear region.
            walk(graph, _drawn(1, [3.2, 3.2], (3.0, 3.0)))

    def _three_levels(self) -> tuple[dict, dict]:
        """One edge at each of the levels `elevation_levels` maps in this region."""
        graph = {
            "edges": [
                _edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]]),
                _edge(2, [[9.0, 6.0, 0.0], [9.0, 6.0, 20.0]], level=1),
                _edge(3, [[18.0, -8.0, 0.0], [18.0, -8.0, 20.0]], level=-1),
            ]
        }
        drawn = {
            **_drawn(1, [3.2, 3.2], (2.0, 2.0)),
            **_drawn(2, [3.2, 3.2], (2.0, 2.0)),
            **_drawn(3, [3.2, 3.2], (2.0, 2.0)),
        }
        return graph, drawn

    def test_an_unwalked_level_is_published_but_not_measured(self) -> None:
        """A level outside `LEVELS` still gets a full-length row of refusals.

        ⚠️ **The population changed on 2026-09-04 and the property did not.**
        This was level 1 until it shipped; the tunnels are what is left, and the
        row has to be present either way so the table covers the graph rather
        than a subset of it — a consumer indexing by edge id must not find a
        hole where a level it does not care about used to be.
        """
        graph, drawn = self._three_levels()
        _, report = walk(graph, drawn)
        assert report.edges == 2
        assert report.corridor_m[3] == [NOT_MEASURED, NOT_MEASURED]

    def test_the_level_gate_is_a_knob_a_tool_can_widen(self) -> None:
        # A measurement outside the shipped set has to stay reachable without
        # the bundle changing — that is how level 1's numbers were read before
        # they were published, and it is how level -1's would be. Asserted as a
        # *pair* with the default: what is pinned is that the shipped default
        # holds while a tool can ask for more, and a single test of either half
        # would pass with the two silently merged.
        graph, drawn = self._three_levels()
        corridor, report = walk(graph, drawn, levels=(0, 1, -1))
        assert report.edges == 3
        # Read off the sections themselves, not off `corridor_m`: `walk` leaves
        # that at `NOT_MEASURED` for every edge until `measure` fills it, so an
        # assertion there would pass for the level-0 edge too and prove nothing.
        assert {2, 3} <= set(corridor.section_edge.tolist())

    def test_a_graph_out_of_step_with_the_manifest_is_refused(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 10.0], [0.0, 0.0, 20.0]])]}
        with pytest.raises(SystemExit, match="different runs"):
            walk(graph, _drawn(1, [3.2, 3.2], (0.0, 0.0)))

    def test_a_manifest_with_no_offsets_is_refused_rather_than_read_as_zero(self) -> None:
        """🔴 The whole of `Q106` arrives as a zero nobody wrote.

        A missing `offset_m` read as 0.0 is a cross-section about the published
        centreline — the defect below — and it publishes a full, plausible
        table. `tools/overhang.py` can afford the fallback because it grades;
        this writes the bundle.
        """
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])]}
        drawn = {1: {"half_width_m": [3.2, 3.2], "trim_m": [0.0, 0.0]}}
        with pytest.raises(SystemExit, match="offsets"):
            walk(graph, drawn)


class TestTheDrawnFrame:
    """Where the cross-section is taken, which `Q106` got wrong in four tools.

    🔴 **Both halves are silent failures and they are different failures.** A
    section centred on the published centreline measures a strip of ground the
    ribbon has left — up to 4.95 m away on `e337` — and a section shifted the
    *wrong way* measures the mirror image of the right one. Neither shortens the
    table, changes a count, or trips a partition; both publish widths.

    ⚠️ **Nothing here can be seen at level 0**, where every offset is 0.0. That
    is the point: this stage shipped the defect for as long as it published
    level 0 alone, and the guard has to be a test rather than a drive.
    """

    def _walked(self, offsets: list[float]) -> np.ndarray:
        """The plan Z of every sample on one straight edge running along +X."""
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [20.0, 0.0, 0.0]], level=1)]}
        drawn = _drawn(1, [1.0, 1.0], (0.0, 0.0), offsets=offsets)
        corridor, _ = walk(graph, drawn, levels=(1,))
        return corridor.z

    def test_the_walk_normal_is_the_negation_of_mitres(self) -> None:
        """The two conventions in this repo are opposite, and must stay opposite.

        `walk` builds `[-forward.z, forward.x]`, the **right** of travel that
        `pipeline/carriageway.py::_stations` also emits; `offset_m` is published
        in `surface.mitres`' frame, the **left**. Pinned against `mitres` rather
        than a literal, because that is where the convention is decided —
        `test_centreline_error.py` pins the same pair for the same reason. If
        anyone "restores consistency", this fails loudly rather than mirroring
        every off-grade cross-section onto the far side of its own deck.

        🔴 **Read off `_across` and never retyped.** The first version of this
        test rebuilt the expression by hand and compared that to `mitres`, so it
        passed whatever `walk` did — `Q72`'s tautology inside the guard against
        `Q78`'s defect, which is why the normal has a name.
        """
        points = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
        assert _across(np.array([[1.0, 0.0]]))[0] == pytest.approx(-mitres(points)[0])

    def test_the_section_is_centred_on_the_ribbon_and_not_on_the_centreline(self) -> None:
        # Travel along +X, so `mitres`' left is -Z: a +5.0 m offset draws the
        # ribbon over z in [-6, -4] and the centreline is not under it at all.
        z = self._walked([5.0, 5.0])
        assert z.max() <= -4.0 + 1e-9
        assert z.min() >= -6.0 - 1e-9
        # 🔴 Not merely "off the centreline" — the sign. Read the other way this
        # spans [+4, +6], which is the same distance away and the wrong side.
        assert z.mean() == pytest.approx(-5.0, abs=ACROSS_M)

    def test_a_zero_offset_is_the_section_this_stage_always_took(self) -> None:
        """The inertness proof, as a test: level 0 publishes 0.0 everywhere.

        All 737 of them, which is why the **frame fix alone** reproduced the
        shipped `clearance.json` byte-for-byte. ⚠️ **That is not a claim about
        the whole change** — publishing level 1 moved 45 rows — and the two have
        to be stated apart, because only the first can be byte-for-byte and the
        second is "every row that moved is one the old default never walked".
        """
        z = self._walked([0.0, 0.0])
        assert z.max() <= 1.0 + 1e-9
        assert z.min() >= -1.0 - 1e-9


class TestAlongSpacing:
    """`along_m` is the one dimension this stage could *miss* in rather than smear.

    ⚠️ Measured on the shipped bundle, dropping it to `CELL_M` cost three edges —
    `ALONG_M` carries the sweep — so it stays a parameter in order to stay
    measurable. What is silent is the knob quietly stopping working: a sweep that
    returned the same cross-sections at every spacing would read as "the aliasing
    was already priced" when nothing had been swept at all.
    """

    def test_finer_spacing_judges_strictly_more_cross_sections(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 40.0]])]}
        drawn = _drawn(1, [3.2, 3.2], (2.0, 2.0))
        # The coarse side is `ALONG_M` rather than a literal, so this keeps
        # exercising what ships rather than a spacing the stage has left behind.
        coarse, _ = walk(graph, drawn, along_m=ALONG_M)
        fine, _ = walk(graph, drawn, along_m=ALONG_M / 2.0)
        assert len(fine.section_count) > len(coarse.section_count)

    def test_the_default_is_the_shipped_constant(self) -> None:
        # So a sweep cannot become the default by accident: `city.json` is
        # published from this, and `RoadGraph.is_routable` reads it.
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 40.0]])]}
        drawn = _drawn(1, [3.2, 3.2], (2.0, 2.0))
        assert len(walk(graph, drawn)[0].section_count) == len(
            walk(graph, drawn, along_m=ALONG_M)[0].section_count
        )

    def test_the_trims_are_still_honoured_at_any_spacing(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])]}
        corridor, _ = walk(graph, _drawn(1, [3.2, 3.2], (5.0, 4.0)), along_m=0.25)
        along = np.unique(np.round(corridor.z, 3))
        assert along.min() >= 5.0 - 0.25
        assert along.max() <= 16.0 + 0.25


class TestPublishingASweep:
    """`_write` is the one place a measurement becomes the bundle.

    ⚠️ **`along_m` had a guard here and `levels` did not, and that asymmetry was
    the hole.** `build_region` is public and takes both, so a caller could walk
    the off-grade network *at the shipped spacing* and publish 60 edges of
    `clear_width_m` that every pre-`P4-1` consumer hides behind `is_drivable` —
    a bundle change nobody decided, arriving as a silently different document.
    `Q103` records that flipping the level is the user's call.
    """

    def test_the_shipped_levels_are_the_two_with_a_deck(self) -> None:
        # Pinned by value because of what it encodes rather than for tidiness.
        # 🔴 **`-1` is the assertion that matters and `1` is the one that
        # changed.** The tunnels are excluded because a bore has no deck for
        # this walk to find and `e489`'s defect is 0.22 m of *headroom* — a
        # horizontal corridor cannot express it, so a published width there
        # would mean something different from every other row in the document.
        assert LEVELS == (0, 1)
        assert -1 not in LEVELS

    def test_the_shipped_levels_match_the_width_surveys(self) -> None:
        """🔴 Two keys naming one population, pinned against each other.

        `carriageway_survey.levels` decides which levels take a measured width
        and this decides which take a measured corridor. They are the same
        argument about the same decks — a bore has none — and a bundle where
        they disagree publishes a corridor across a width nothing surveyed, or
        the reverse. Read off the shipped config rather than restated, so the
        two cannot drift while both look right in isolation.
        """
        city = load_config()
        assert tuple(city.carriageway_survey.levels) == LEVELS

    def test_the_open_levels_are_the_measured_levels(self) -> None:
        """🔴 **`P4-1`'s invariant: the network is open exactly where it is measured.**

        `fence.touchdown_levels` decides which levels a player cannot reach and
        this decides which levels carry a corridor. A level that is open and
        unmeasured hands the player road nothing has looked at — which is the
        state `Q108` refused in as many words — and a level that is measured and
        shut publishes a number nobody can drive to.

        ⚠️ **Level 2 is why this is stated over `elevation_levels` and not over
        the edges that exist.** No edge in Wan Chai carries it, so a check
        written against the built bundle would pass with level 2 open by
        omission, and the first region that draws one would open it ungraded —
        which is the one thing a bundle-shaped check could not catch.
        """
        city = load_config()
        mapped = {int(level) for level in city.elevation_levels}
        shut = {int(level) for level in city.fence.touchdown_levels}
        assert mapped - shut == set(LEVELS)

    def test_the_report_says_what_it_was_actually_walked_over(self) -> None:
        # 🔴 The guard above is only worth having if the field is true. `walk` is
        # public — `tools/narrowing.py` calls it directly — so a report built
        # with the defaults and corrected by `build_region` two frames later
        # would hand every other caller a level-0 claim over an off-grade walk,
        # and `_write` would publish it without complaint.
        graph = {
            "edges": [
                _edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]]),
                _edge(2, [[9.0, 6.0, 0.0], [9.0, 6.0, 20.0]], level=1),
            ]
        }
        drawn = {**_drawn(1, [3.2, 3.2], (2.0, 2.0)), **_drawn(2, [3.2, 3.2], (2.0, 2.0))}
        assert walk(graph, drawn, levels=(0, 1))[1].levels == (0, 1)
        assert walk(graph, drawn, along_m=ALONG_M / 2.0)[1].along_m == ALONG_M / 2.0
        # And a list is coerced, because the annotation does not stop one and the
        # guard compares with `!=` against a tuple.
        assert walk(graph, drawn, levels=[0, 1])[1].levels == (0, 1)

    def test_a_widened_walk_cannot_publish(self) -> None:
        with pytest.raises(SystemExit, match="level"):
            # ⚠️ `city` is never reached, and that is pinned as much as the
            # refusal: a guard standing *after* `out_dir` would already have
            # resolved where to write the document it is refusing.
            _write(None, cast(Any, None), "wan_chai", ClearanceReport(levels=(0, 1, -1)))

    def test_a_swept_spacing_still_cannot_publish(self) -> None:
        # The older guard, kept under test beside the new one: they share a
        # message and a reason, and a refactor that reached one would reach both.
        with pytest.raises(SystemExit, match="sweep reports"):
            _write(None, cast(Any, None), "wan_chai", ClearanceReport(along_m=ALONG_M / 2.0))

    def test_the_shipped_measurement_still_gets_through(self) -> None:
        # 🔴 **Mutation-checked rather than read** (`Q72`). Two refusals that
        # always fired would pass both tests above while publishing nothing ever,
        # and every counter in this stage would go on closing. What says the
        # guards are reachable at zero is that a default report gets past them —
        # here, into the `city` dereference they stand in front of.
        # ⚠️ **`match` is load-bearing.** A bare `AttributeError` is also what a
        # renamed `report.along_m` raises *before* either guard runs, so this
        # would go on passing with both of them dead — certifying the wrong
        # state, which is the failure this class is written against.
        with pytest.raises(AttributeError, match="out_dir"):
            _write(None, cast(Any, None), "wan_chai", ClearanceReport())


class TestLevelsArgument:
    """`--levels` is how `P4-1` reads the off-grade network before it exists.

    Only the refusals are worth a test: a parse that returned the wrong levels
    would show up in the very next log line, which names them.
    """

    def test_a_list_becomes_a_sorted_tuple(self) -> None:
        # Sorted rather than as typed, so one level set has one label —
        # `config._survey_levels`' rule at the CLI. `_write` quotes that label.
        assert _levels_argument("0,1,-1") == (-1, 0, 1)
        assert _levels_argument("1,-1,0") == (-1, 0, 1)

    def test_spacing_is_tolerated(self) -> None:
        assert _levels_argument(" 0 , 1 ") == (0, 1)

    def test_a_repeat_is_refused(self) -> None:
        # `walk` tests membership, so `0,0` walks what `0` walks and prints
        # differently — and the printed form is what `_write`'s refusal quotes.
        with pytest.raises(argparse.ArgumentTypeError, match="twice"):
            _levels_argument("0,1,0")

    def test_an_empty_token_is_refused(self) -> None:
        # Which is also how `--levels ""` is caught: it splits to one empty
        # token, so the walk cannot be handed a level set that measures nothing.
        with pytest.raises(argparse.ArgumentTypeError, match="empty"):
            _levels_argument("0,,1")

    def test_a_non_integer_is_refused(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="not an elevation level"):
            _levels_argument("0,ground")


class TestSubdivisionCap:
    """How many triangles the cap held back — this stage's own smear, now counted.

    ⚠️ Silent in exactly the way that matters. A piece the cap left wider than
    `CELL_M` blocks by its plan box carrying its *whole* height range, so it
    invents blockage beside anything large and sloped, and the constant's own
    comment claimed the only such geometry was ground. `MAX_SUBDIVISIONS` carries
    how many a run actually holds back.
    """

    def test_a_triangle_inside_the_cap_is_not_counted(self) -> None:
        small = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]])
        split = _plan_steps(small)
        assert split.clipped == 0
        assert split.steps.max() <= MAX_SUBDIVISIONS

    def test_a_triangle_over_the_cap_is_counted_and_still_clipped(self) -> None:
        # Wider in plan than `MAX_SUBDIVISIONS * SUBDIVIDE_M`, so it cannot be
        # split to `SUBDIVIDE_M` and the count is the only thing that says so.
        span = MAX_SUBDIVISIONS * SUBDIVIDE_M * 4.0
        huge = np.array([[[0.0, 0.0, 0.0], [span, 0.0, 0.0], [0.0, 0.0, span]]])
        split = _plan_steps(huge)
        assert split.clipped == 1
        assert split.steps.tolist() == [MAX_SUBDIVISIONS]

    def test_the_count_is_per_triangle_not_per_mesh(self) -> None:
        span = MAX_SUBDIVISIONS * SUBDIVIDE_M * 4.0
        mixed = np.array(
            [
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
                [[0.0, 0.0, 0.0], [span, 0.0, 0.0], [0.0, 0.0, span]],
                [[0.0, 0.0, 0.0], [span, 0.0, 0.0], [0.0, 0.0, span]],
            ]
        )
        assert _plan_steps(mixed).clipped == 2


class TestMeasure:
    """Folding samples into one width per station."""

    def _corridor(self, graph: dict, drawn: dict):
        return walk(graph, drawn)

    def test_an_open_street_reports_the_width_it_was_drawn(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])]}
        corridor, report = self._corridor(graph, _drawn(1, [5.12, 5.12], (2.0, 2.0)))
        measure(corridor, np.zeros(len(corridor), dtype=bool), report)
        # 10.24 m is not a multiple of 0.25, so an unclamped run would publish
        # 10.25 m — a corridor wider than the road it was measured across.
        assert max(report.corridor_m[1]) == pytest.approx(10.24)

    def test_a_station_takes_its_tightest_cross_section(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])]}
        corridor, report = self._corridor(graph, _drawn(1, [5.12, 5.12], (2.0, 2.0)))
        blocked = np.zeros(len(corridor), dtype=bool)
        # Block one whole cross-section. Averaging, or taking the last one, would
        # let a wall across a station hide behind the clear road beside it.
        first = int(corridor.section_count[0])
        blocked[:first] = True
        measure(corridor, blocked, report)
        assert min(width for width in report.corridor_m[1] if width != NOT_MEASURED) == 0.0

    def test_the_widest_gap_survives_a_pillar_in_the_middle(self) -> None:
        graph = {"edges": [_edge(1, [[0.0, 0.0, 0.0], [0.0, 0.0, 20.0]])]}
        corridor, report = self._corridor(graph, _drawn(1, [5.12, 5.12], (2.0, 2.0)))
        blocked = np.zeros(len(corridor), dtype=bool)
        count = int(corridor.section_count[0])
        blocked[count // 2] = True
        measure(corridor, blocked, report)
        widths = [width for width in report.corridor_m[1] if width != NOT_MEASURED]
        # Not 10.24 minus one sample: the run is the wider of the two sides.
        assert min(widths) == pytest.approx((count - count // 2 - 1) * ACROSS_M)


class TestStarved:
    def test_refusals_never_count_as_a_blockage(self) -> None:
        report = ClearanceReport(corridor_m={1: [NOT_MEASURED, NOT_MEASURED], 2: [0.5, 9.0]})
        # Edge 1 was never measured, so it is not starved — reading its `-1.0`
        # as a width would condemn every edge the junction caps swallowed.
        assert report.starved(3.2) == [(2, 0.5)]
