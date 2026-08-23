"""The stop and give-way line stage (`P3-23`).

Weighted towards the *join* and the *conventions* rather than the drawing, for
`test_boxjunctions.py`'s stated reason: this is where the stage can be
confidently wrong and where nothing downstream would notice. A bar hosted by
the road it lies beside rather than the road it crosses is drawn in exactly the
right place at the wrong height. A double line read as centre-to-centre is one
line of twice the width. A quad wound the wrong way is nothing at all.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.boxjunctions import blended_height
from pipeline.config import RoadMark, load_city
from pipeline.fares import Segments
from pipeline.roadmarks import (
    ROADMARKS_MATERIAL,
    Marking,
    Network,
    RoadMarkReport,
    _Builder,
    _cuts,
    _host,
    _runs,
    band_quads,
)
from pipeline.surface import downward_facing
from tests.helpers import CITY_YAML

# The block as `hong_kong.yaml` declares it. Held here rather than in
# `helpers.py`'s `CITY_YAML` because the block is optional by contract, and the
# fixture city's job is to prove that a city without one still builds.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "DTAD_RD_MARK_LINE",
    "fields": {"mark_type": "LINETYPE", "level": "ELEVATION"},
    "host_radius_m": 20.0,
    "bearing_tolerance_deg": 30.0,
    "proximity_weight_deg_per_m": 0.05,
    "station_m": 2.0,
    "lift_m": 0.016,
    "height_blend_m": 4.0,
    "marks": [
        {
            "id": "stop_line",
            "codes": ["RM1011"],
            "line_width_m": 0.2,
            "lines": 1,
            "lines_spacing_m": 0.0,
        },
        {
            "id": "stop_lines",
            "codes": ["RM1012"],
            "line_width_m": 0.2,
            "lines": 2,
            "lines_spacing_m": 0.3,
        },
        {
            "id": "give_way_lines",
            "codes": ["RM1013"],
            "line_width_m": 0.2,
            "lines": 2,
            "lines_spacing_m": 0.2,
            "mark_m": 0.6,
            "gap_m": 0.3,
        },
    ],
}


def city_with(tmp_path, block: dict[str, Any] | None):
    """`testville` carrying the given road_marks block, loaded through the real
    loader — the same argument `test_boxjunctions.py`'s namesake makes."""
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["road_marks"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_city("testville", cities_root=cities)


@pytest.fixture
def spec(tmp_path):
    """`testville` with a road_marks block bolted on, parsed by the real loader."""
    return city_with(tmp_path, BLOCK).road_marks


def edge(edge_id: int, points: list[list[float]], width_m: float = 6.4) -> dict:
    """One level-0 road-graph edge, in the shape `roadgraph.json` publishes."""
    return {"id": edge_id, "polyline": points, "width_m": width_m}


def network(edges: list[dict], drawn_width_m: float = 10.24) -> Network:
    """`Network` over those edges, with a drawn width for each.

    ⚠️ The default is the **drawn** ribbon — `edge`'s 6.4 m authored width times
    the region's 1.6x widening — because that is the frame `underfill_m` is
    measured in and reading the authored width instead was an 18x error in a
    published number.
    """
    return Network.of(Segments.of(edges), {int(one["id"]): drawn_width_m for one in edges})


def band_width_m(mark: RoadMark) -> float:
    """Across-marking extent, edge to edge, from the sheet's own two numbers.

    Here rather than on `RoadMark` because nothing the stage draws needs it —
    `band_offsets_m` is the production path — so over there it was a property
    with no caller outside this file.
    """
    return mark.lines * mark.line_width_m + (mark.lines - 1) * mark.lines_spacing_m


def marking(spec, code: str, points: list[list[float]]) -> Marking:
    return Marking(code=code, mark=spec.mark_of(code), line=np.asarray(points, dtype=np.float64))


class TestTheDoubleLineReading:
    """`LINES SPACING` is the clear gap, not a centre-to-centre pitch.

    ⚠️ The sheet settles this two rows above the ones this stage reads: `RM1001`
    DOUBLE LINES publishes `LINE WIDTH = 150` with `LINES SPACING = 100`, and
    two 150 mm lines whose centres are 100 mm apart is one 250 mm line. Only the
    gap reading draws a shape, and getting it wrong renders as a perfectly good
    marking of the wrong weight.
    """

    def test_a_single_line_sits_on_the_published_line(self, spec):
        assert spec.mark_of("RM1011").band_offsets_m == (0.0,)

    def test_a_double_line_is_symmetric_about_the_published_line(self, spec):
        offsets = spec.mark_of("RM1013").band_offsets_m
        assert offsets == pytest.approx((-0.2, 0.2))
        assert sum(offsets) == pytest.approx(0.0)

    def test_the_gap_between_the_two_lines_is_what_the_sheet_says(self, spec):
        mark = spec.mark_of("RM1013")
        low, high = mark.band_offsets_m
        inner_gap = (high - 0.5 * mark.line_width_m) - (low + 0.5 * mark.line_width_m)
        assert inner_gap == pytest.approx(mark.lines_spacing_m)

    def test_stop_lines_carry_the_wider_gap(self, spec):
        # `RM1012` publishes 300 where `RM1013` publishes 200, so the two bands
        # must not come out the same width.
        assert band_width_m(spec.mark_of("RM1012")) == pytest.approx(0.7)
        assert band_width_m(spec.mark_of("RM1013")) == pytest.approx(0.6)

    def test_the_band_spans_every_line_and_every_gap(self, spec):
        for code in ("RM1011", "RM1012", "RM1013"):
            mark = spec.mark_of(code)
            offsets = mark.band_offsets_m
            span = (max(offsets) + 0.5 * mark.line_width_m) - (
                min(offsets) - 0.5 * mark.line_width_m
            )
            assert span == pytest.approx(band_width_m(mark))


class TestTheModule:
    """A continuous line is one run; a dashed one is `mark`/`gap` from the start."""

    def test_a_continuous_line_is_a_single_run(self, spec):
        assert _runs(spec.mark_of("RM1011"), 12.0) == [(0.0, 12.0)]

    def test_a_dashed_line_repeats_at_the_published_period(self, spec):
        runs = _runs(spec.mark_of("RM1013"), 2.7)
        # 600 mark, 300 gap: marks start at 0.0, 0.9, 1.8 and each is 0.6 long.
        assert [value for run in runs for value in run] == pytest.approx(
            [0.0, 0.6, 0.9, 1.5, 1.8, 2.4]
        )

    def test_the_last_mark_is_clipped_and_never_overruns(self, spec):
        runs = _runs(spec.mark_of("RM1013"), 2.0)
        assert runs[-1] == pytest.approx((1.8, 2.0))
        assert all(stop <= 2.0 for _, stop in runs)

    def test_painted_length_is_two_thirds_of_a_long_give_way_line(self, spec):
        runs = _runs(spec.mark_of("RM1013"), 90.0)
        painted = sum(stop - start for start, stop in runs)
        # 600 of every 900 mm — the ratio the sheet publishes, not a tuned one.
        assert painted / 90.0 == pytest.approx(2.0 / 3.0, abs=0.01)


class TestTheCuts:
    """Every quad stays inside one source segment, so its ends share a normal."""

    def test_a_run_is_split_at_station_boundaries(self):
        cuts = _cuts(0.0, 5.0, np.array([0.0, 5.0]), 2.0)
        assert cuts == pytest.approx([0.0, 2.0, 4.0, 5.0])

    def test_a_run_is_split_at_every_source_vertex(self):
        # ⚠️ The vertex cut is what keeps a quad inside one segment. Without it
        # a quad spanning a bend takes two different perpendiculars and comes
        # out skewed — which draws, and draws wrong.
        cuts = _cuts(0.0, 5.0, np.array([0.0, 1.3, 5.0]), 100.0)
        assert cuts == pytest.approx([0.0, 1.3, 5.0])

    def test_a_short_mark_inside_one_station_is_not_split(self):
        assert _cuts(0.9, 1.5, np.array([0.0, 10.0]), 2.0) == pytest.approx([0.9, 1.5])


class TestTheHostIsPickedByTransversality:
    """🔴 The one place this stage departs from `arrows.py` and `boxjunctions.py`.

    Both of those take the nearest level-0 edge. A stop line sits at a junction
    **mouth** — drawn across the minor road while lying a metre off the major
    road's kerb — so proximity hands it the wrong host by construction, on a
    measured 44% of the region's stop lines and 43% of its give-way lines.
    """

    @pytest.fixture
    def junction(self):
        """A T: a major road running east-west, a minor one joining from the south.

        Distances are what make this the real case. The major road's centreline
        is 1.0 m from the bar; the minor road's is 6.0 m away along its own
        axis. Proximity picks the major road and is wrong.
        """
        return network(
            [
                edge(1, [[-50.0, 0.0, 0.0], [50.0, 0.0, 0.0]]),
                edge(2, [[0.0, 0.0, 7.0], [0.0, 0.0, 60.0]]),
            ]
        )

    @pytest.fixture
    def bar(self, spec):
        """A stop line across the minor road's mouth, 1 m south of the major road."""
        return marking(spec, "RM1011", [[-3.2, 1.0], [3.2, 1.0]])

    def test_the_nearest_edge_is_the_one_the_bar_lies_along(self, junction, bar):
        # The premise of the whole rule, asserted rather than assumed: if the
        # nearest edge were already the right one there would be nothing here
        # to fix.
        distances = junction.distances(bar.midpoint)
        assert junction.edge_id[int(np.argmin(distances))] == 1

    def test_the_host_is_the_edge_the_bar_is_drawn_across(self, junction, bar, spec):
        host = _host(junction, bar, spec)
        assert junction.edge_id[host.segment] == 2
        assert host.residual_deg == pytest.approx(0.0, abs=1e-9)

    def test_the_disagreement_is_reported(self, junction, bar, spec):
        # `host_disagreement` is the counter that can see this rule regress —
        # `axis_residual_deg` cannot, because it grades a rule that optimises
        # the very thing it reports (`Q58`'s `drawn_gauge_m` trap).
        assert _host(junction, bar, spec).disagrees is True

    def test_no_disagreement_where_proximity_already_agrees(self, junction, spec):
        across = marking(spec, "RM1011", [[10.0, -3.2], [10.0, 3.2]])
        host = _host(junction, across, spec)
        assert junction.edge_id[host.segment] == 1
        assert host.disagrees is False

    def test_a_marking_lying_along_every_candidate_is_refused(self, spec):
        # The 18 of the region's 209 candidates that no host makes transverse —
        # a 56.9 m `RM1013` at 78.8 deg off square is the extreme. Returned with
        # its residual so the caller can record it *before* refusing it, which
        # is what keeps `axis_residual_deg`'s `n` above `drawn` (`Q58`).
        #
        # ⚠️ One road, not the T above: with a cross street in range a bar lying
        # along the major road is square across the minor one, and *is* hosted.
        # That is the correct answer and it is why this needs its own fixture.
        straight = network([edge(1, [[-50.0, 0.0, 0.0], [50.0, 0.0, 0.0]])])
        along = marking(spec, "RM1011", [[-16.0, 1.0], [16.0, 1.0]])
        host = _host(straight, along, spec)
        assert host is not None
        assert host.residual_deg == pytest.approx(90.0)
        assert host.residual_deg > spec.bearing_tolerance_deg

    def test_nothing_in_range_is_a_different_answer_from_nothing_transverse(self, junction, spec):
        # `no_edge_in_range` and `no_transverse_host` are separate partitions on
        # purpose: one says the marking is off the network, the other says it is
        # on it and is not a transverse bar.
        far = marking(spec, "RM1011", [[500.0, 500.0], [503.2, 500.0]])
        assert _host(junction, far, spec) is None

    def test_proximity_breaks_ties_and_never_decides(self, spec):
        # Two edges equally square across the bar, 2 m and 12 m away. The tie
        # goes to the near one — but at 0.05 deg per metre it takes 20 m of
        # extra distance to overturn a single degree, so distance can never
        # outvote a real angular difference.
        two = network(
            [
                edge(1, [[0.0, 0.0, -30.0], [0.0, 0.0, 30.0]]),
                edge(2, [[10.0, 0.0, -30.0], [10.0, 0.0, 30.0]]),
            ]
        )
        bar = marking(spec, "RM1011", [[-3.2, 0.0], [3.2, 0.0]])
        assert two.edge_id[_host(two, bar, spec).segment] == 1


class TestTheGeometry:
    """What is drawn, and which way up."""

    @pytest.fixture
    def bar(self, spec):
        return marking(spec, "RM1011", [[-3.0, 0.0], [3.0, 0.0]])

    def test_a_continuous_bar_covers_its_whole_published_length(self, bar, spec):
        quads = band_quads(bar, spec)
        along = np.vstack(quads)[:, 0]
        assert along.min() == pytest.approx(-3.0)
        assert along.max() == pytest.approx(3.0)

    def test_the_bar_is_drawn_at_the_published_width(self, bar, spec):
        across = np.vstack(band_quads(bar, spec))[:, 1]
        assert across.max() - across.min() == pytest.approx(0.2)

    def test_the_extent_is_never_stretched_to_the_ribbon(self, bar, spec):
        # ⚠️ `Q54`: the length is the publisher's and the width is convention.
        # The host here is 6.4 m wide against a 6.0 m bar, and the underfill is
        # published rather than closed.
        quads = np.vstack(band_quads(bar, spec))
        assert quads[:, 0].max() - quads[:, 0].min() == pytest.approx(6.0)

    def test_a_double_line_draws_two_separated_bands(self, spec):
        marks = marking(spec, "RM1012", [[-3.0, 0.0], [3.0, 0.0]])
        across = np.unique(np.round(np.vstack(band_quads(marks, spec))[:, 1], 6))
        # Four distinct across-coordinates: each band's two edges, and no
        # coordinate between them.
        assert across.tolist() == pytest.approx([-0.35, -0.15, 0.15, 0.35])

    def test_a_dashed_line_leaves_gaps(self, spec):
        give_way = marking(spec, "RM1013", [[0.0, 0.0], [9.0, 0.0]])
        quads = band_quads(give_way, spec)
        # Ten marks per band over 9 m at a 0.9 m period, two bands.
        painted = sum(
            (quad[:, 0].max() - quad[:, 0].min()) * (quad[:, 1].max() - quad[:, 1].min())
            for quad in quads
        )
        # Two bands, 0.2 m wide, two-thirds painted over 9 m.
        assert painted == pytest.approx(2 * 0.2 * 9.0 * 2.0 / 3.0, rel=0.02)

    @pytest.mark.parametrize("heading_deg", [0.0, 37.0, 90.0, 143.0, 216.0, 305.0])
    def test_every_quad_faces_up_at_every_heading(self, spec, heading_deg):
        # ⚠️ **The failure that fails to nothing.** `marking_paint.gdshader` is
        # `cull_back`, so a quad wound the other way is correct geometry in the
        # correct place that simply is not in the city — the tramway shipped
        # 5,111 of 5,112 like that.
        heading = math.radians(heading_deg)
        forward = np.array([math.sin(heading), -math.cos(heading)])
        line = np.array([-4.0 * forward, 4.0 * forward])
        quads = band_quads(Marking("RM1013", spec.mark_of("RM1013"), line), spec)
        builder = _Builder()
        for quad in quads:
            builder.polygon(quad, np.zeros(len(quad)))
        mesh = builder.build("roadmarks")
        inverted, area = downward_facing(mesh)
        assert inverted == 0
        assert area == pytest.approx(0.0)

    def test_a_bent_line_keeps_every_quad_inside_one_segment(self, spec):
        # Nineteen of the region's 211 parts bend. Each quad must be a true
        # rectangle, which is what the vertex cut in `_cuts` buys.
        bent = marking(spec, "RM1011", [[0.0, 0.0], [3.0, 0.0], [6.0, 3.0]])
        for quad in band_quads(bent, spec):
            first, second = quad[1] - quad[0], quad[2] - quad[1]
            assert float(first @ second) == pytest.approx(0.0, abs=1e-9)

    def test_the_mesh_names_the_material_the_engine_dispatches_on(self, spec):
        bar = marking(spec, "RM1011", [[-3.0, 0.0], [3.0, 0.0]])
        builder = _Builder()
        for quad in band_quads(bar, spec):
            builder.polygon(quad, np.zeros(len(quad)))
        # `tools/generated_scene_import.gd` maps this string and nothing else;
        # a mesh that names something else keeps its imported `BaseMaterial3D`
        # and draws the right bars in the importer's grey.
        assert builder.build("roadmarks").material == ROADMARKS_MATERIAL


class TestTheHeightJoin:
    """Each vertex takes a blended height, because a junction mouth is a seam."""

    def test_a_bar_across_a_graded_street_follows_it(self, spec):
        segments = Segments.of(
            [
                {
                    "id": 1,
                    "polyline": [[0.0, 0.0, -20.0], [0.0, 2.0, 20.0]],
                    "width_m": 6.4,
                    "elevation_level": 0,
                }
            ]
        )
        # Stationing exists so a long bar samples the grade rather than chording
        # across it; on a bar drawn *across* the grade the heights agree, which
        # is what makes `height_spread_m` p50 0.021 m in region.
        heights = [blended_height(segments, 0.0, z, spec.height_blend_m) for z in (-10.0, 10.0)]
        assert heights[0] < heights[1]


class TestTheBlockIsOptional:
    """A city that publishes no transverse markings ships none."""

    def test_a_city_without_the_block_loads(self, tmp_path):
        assert city_with(tmp_path, None).road_marks is None

    def test_an_empty_marks_table_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="draws nothing"):
            city_with(tmp_path, {**BLOCK, "marks": []})

    def test_a_code_in_two_entries_is_refused(self, tmp_path):
        # ⚠️ It would be drawn twice, in one place, at two widths — and the
        # wider looks exactly like a correctly drawn marking.
        doubled = [*BLOCK["marks"], {**BLOCK["marks"][0], "id": "again"}]
        with pytest.raises(ValueError, match="drawn twice"):
            city_with(tmp_path, {**BLOCK, "marks": doubled})

    def test_a_double_line_with_no_gap_is_refused(self, tmp_path):
        marks = [{**BLOCK["marks"][2], "lines_spacing_m": 0.0}]
        with pytest.raises(ValueError, match="twice the width"):
            city_with(tmp_path, {**BLOCK, "marks": marks})

    def test_half_a_module_is_refused(self, tmp_path):
        # A mark with no gap is a continuous line spelt at length; a gap with no
        # mark draws nothing. Both are silent, so neither is guessed at.
        marks = [{**BLOCK["marks"][2], "gap_m": None}]
        with pytest.raises(ValueError, match="together or not at all"):
            city_with(tmp_path, {**BLOCK, "marks": marks})

    def test_a_tolerance_that_refuses_nothing_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="lying along its host"):
            city_with(tmp_path, {**BLOCK, "bearing_tolerance_deg": 90.0})


class TestTheReportPartitions:
    """The counters are what can see this stage fail (`Q58`)."""

    def test_the_partitions_close_on_the_shipped_figures(self):
        # The region's own numbers, so this fails if a leg is ever incremented
        # without its total. A default-constructed report asserts 0 == 0 and
        # proves nothing about the invariant it names.
        report = RoadMarkReport(
            features=1679,
            parts=4162,
            not_a_road_mark=3951,
            on_structure=2,
            empty_geometry=0,
            candidates=209,
            drawn=191,
            no_transverse_host=18,
            no_edge_in_range=0,
        )
        assert (
            report.not_a_road_mark + report.on_structure + report.empty_geometry + report.candidates
            == report.parts
        )
        assert (
            report.drawn + report.no_transverse_host + report.no_edge_in_range == report.candidates
        )

    def test_the_residual_distribution_publishes_its_tail(self):
        # p90/p99/max rather than a median alone: the tail is where a match to
        # the wrong road goes, and a median near zero is also what a wholly
        # broken join looks like.
        measured = RoadMarkReport.measured([0.0, 1.0, 2.0, 89.0])
        assert set(measured) == {"p50", "p90", "p99", "max", "n"}
        assert measured["max"] == pytest.approx(89.0)
        assert measured["n"] == 4
