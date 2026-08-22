"""The railing join and the fence it draws (`P3-19`, opens `Q60`).

⚠️ **Every failure mode this stage has renders as a perfectly good fence**, so
none of these tests can be replaced by looking at the city. A railing moved to
the other kerb is a fence. A railing drawn across merged tarmac is a fence, and
it is the one the player crashes into. A railing whose registration quietly
doubled is a fence 3 m further out than the street it belongs to.

Four of them carry the weight:

- **the side**, asserted against `surface.mitres` itself rather than against a
  comment, for `test_kerbside.py`'s stated reason — the convention decides which
  kerb *every* fence in the city stands on, and mirrored it still renders;
- **the shift bar**, which is the whole price of `Q60`'s registration and the
  only thing standing between a plaza balustrade and a carriageway edge;
- **the buried kerb**, which is the guard that keeps a fence out of the middle
  of a merged dual carriageway;
- **the winding**, because under `cull_disabled` a flipped quad still draws.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.config import Railings, SourceLayer
from pipeline.kerbside import NEARSIDE, OFFSIDE
from pipeline.railings import (
    RailingReport,
    Ribbon,
    _assign,
    _Builder,
    _draw_run,
    _visible,
    facing_away,
)
from pipeline.surface import boundary, mitres

# Far enough from the origin that nothing here clips on the region bounds, and
# far enough from them that a kerb is never outside the region.
WHOLE_WORLD = (10_000.0, 10_000.0)


def spec(**overrides) -> Railings:
    """The Hong Kong tuning, which is what every published figure was measured at."""
    values = {
        "source": "traffic_aids",
        "member": None,
        "layer": SourceLayer(
            layer="DTAD_RAILING_LINE", fields={"line_type": "LINETYPE", "level": "ELEVATION"}
        ),
        "drawn_line_types": ("CRAIL1",),
        "sample_m": 1.0,
        "max_offset_m": 12.0,
        "max_shift_m": 3.0,
        "bridge_gap_m": 4.0,
        "min_run_m": 4.0,
        "station_m": 2.0,
        "height_m": 1.1,
        "base_sink_m": 0.25,
        "outset_m": 0.6,
    }
    return Railings(**{**values, **overrides})


class _City:
    """The one thing `_assign` asks a `CityConfig` for."""

    def region_high(self, region_id: str) -> tuple[float, float]:
        del region_id
        return WHOLE_WORLD


def straight(x0: float, x1: float, z: float = 100.0, half: float = 5.0) -> np.ndarray:
    """An edge polyline in game space, as `roads.py` publishes one: x, y, z."""
    return np.array([[x0, 0.0, z], [x1, 0.0, z]], dtype=np.float64)


def ribbon(edge: np.ndarray, half: float = 5.0, outset: float = 0.6, **overrides) -> Ribbon:
    """One edge's drawn ribbon, built the way `railings.ribbons` builds it.

    Through `mitres` and `boundary` rather than by writing the offset out here:
    those two are what `surface.py` draws the carriageway edge with, and a
    fixture that computed its own would agree with a wrong stage.
    """
    shaped = np.column_stack([edge, np.full(len(edge), half)])
    offsets = mitres(shaped)
    across = shaped[:, 3] + outset
    values = {
        "points": shaped,
        "fence": {
            NEARSIDE: boundary(shaped, offsets, across),
            OFFSIDE: boundary(shaped, offsets, -across),
        },
        "along": np.array([0.0, float(np.hypot(*(edge[-1, [0, 2]] - edge[0, [0, 2]])))]),
        "hidden": {},
        "trim_start_m": 0.0,
    }
    return Ribbon(**{**values, **overrides})


def beside(x0: float, x1: float, z: float) -> np.ndarray:
    """A railing line in game plan coordinates: x, z."""
    return np.array([[x0, z], [x1, z]], dtype=np.float64)


def assign(lines, edges, drawn, **overrides) -> tuple[dict, RailingReport]:
    report = RailingReport()
    graph = {
        "edges": [
            {"id": edge_id, "polyline": polyline, "elevation_level": 0}
            for edge_id, polyline in edges
        ]
    }
    cells = _assign(lines, graph, drawn, spec(**overrides), _City(), "middle", report)
    return cells, report


class TestSide:
    def test_the_nearside_is_the_side_mitres_puts_u_zero_on(self) -> None:
        """The assertion that cannot drift.

        `surface.mitres` offsets one half-width to the left of travel and
        `_draw_edge` gives that rail `U = 0`. A railing beyond that rail must
        come back as the nearside — checked against that *code*, so a flipped
        offset fails here on the same day rather than mirroring every fence in
        the city.
        """
        edge = straight(0.0, 100.0)
        rail = edge[:, [0, 2]] + mitres(edge) * 5.0
        kerb_z = 100.0 + (float(rail[0, 1]) - 100.0) * 1.1

        cells, _ = assign(
            [(beside(10.0, 90.0, kerb_z), "CRAIL1")],
            [(7, edge)],
            {7: ribbon(edge)},
        )
        assert {side for _, side in cells} == {NEARSIDE}

    def test_a_railing_on_the_other_kerb_is_the_offside(self) -> None:
        edge = straight(0.0, 100.0)
        rail = edge[:, [0, 2]] - mitres(edge) * 5.0
        kerb_z = 100.0 + (float(rail[0, 1]) - 100.0) * 1.1

        cells, _ = assign(
            [(beside(10.0, 90.0, kerb_z), "CRAIL1")],
            [(7, edge)],
            {7: ribbon(edge)},
        )
        assert {side for _, side in cells} == {OFFSIDE}


class TestShiftBar:
    """`Q60`'s price, and the guard on it.

    The published railing sits at the *real* kerb; the drawn one sits at the
    widened one. The difference is what `max_shift_m` bounds, and a railing far
    enough out to be a plaza balustrade is refused rather than dragged onto a
    carriageway edge it was never near.
    """

    def test_a_railing_near_the_drawn_kerb_is_kept(self) -> None:
        edge = straight(0.0, 100.0)
        # The fence line stands at half-width plus outset — 5.6 m. A railing at
        # 4.0 m moves 1.6 m, inside the 3.0 m bar.
        cells, report = assign(
            [(beside(10.0, 90.0, 104.0), "CRAIL1")],
            [(7, edge)],
            {7: ribbon(edge)},
        )
        assert report.samples_over_shift == 0
        assert cells

    def test_a_railing_too_far_from_the_drawn_kerb_is_refused(self) -> None:
        edge = straight(0.0, 100.0)
        # 11.0 m off the centreline is inside `max_offset_m` and 5.4 m from the
        # fence line — a railing this stage must not claim is a kerb railing.
        cells, report = assign(
            [(beside(10.0, 90.0, 111.0), "CRAIL1")],
            [(7, edge)],
            {7: ribbon(edge)},
        )
        assert report.samples_over_shift == 80
        assert cells == {}

    def test_the_shift_is_recorded_over_the_samples_it_then_refuses(self) -> None:
        """`Q58`'s tell: a distribution confined to its own filter says nothing.

        `shift_m` is appended before `max_shift_m` is applied, so its `n`
        exceeds what was drawn. Move that append below the guard and every
        percentile is bounded by the bar by construction — which is exactly the
        defect review caught in `arrows.py`'s `axis_residual_deg`.
        """
        edge = straight(0.0, 100.0)
        _, report = assign(
            [(beside(10.0, 90.0, 111.0), "CRAIL1")],
            [(7, edge)],
            {7: ribbon(edge)},
        )
        assert len(report.shift_m) == 80
        assert max(report.shift_m) > spec().max_shift_m


class TestBuriedKerb:
    """The guard that keeps a fence off the middle of the road.

    A 1.6x-widened opposed pair merges into one surface and `surface.py` stops
    drawing the swallowed kerbs. A railing joined to one of those is a fence
    standing in traffic, and it is 11.1% of the region's railing metres.
    """

    def test_a_range_clear_of_every_buried_stretch_survives_whole(self) -> None:
        edge = straight(0.0, 100.0)
        drawn = ribbon(edge, hidden={NEARSIDE: [[60.0, 80.0]]})
        assert _visible(drawn, NEARSIDE, 10.0, 50.0) == [(10.0, 50.0)]

    def test_a_range_across_a_buried_stretch_is_cut_in_two(self) -> None:
        edge = straight(0.0, 100.0)
        drawn = ribbon(edge, hidden={NEARSIDE: [[40.0, 60.0]]})
        assert _visible(drawn, NEARSIDE, 10.0, 90.0) == [(10.0, 40.0), (60.0, 90.0)]

    def test_a_range_wholly_inside_a_buried_stretch_draws_nothing(self) -> None:
        edge = straight(0.0, 100.0)
        drawn = ribbon(edge, hidden={NEARSIDE: [[0.0, 100.0]]})
        assert _visible(drawn, NEARSIDE, 10.0, 90.0) == []

    def test_the_other_side_of_the_same_edge_is_untouched(self) -> None:
        """The mask is per side, and reading it per edge would bury both kerbs.

        An opposed pair buries the kerbs that face each other and leaves the two
        outer ones standing — which is exactly where the railings a driver sees
        actually are.
        """
        edge = straight(0.0, 100.0)
        drawn = ribbon(edge, hidden={NEARSIDE: [[0.0, 100.0]]})
        assert _visible(drawn, OFFSIDE, 10.0, 90.0) == [(10.0, 90.0)]

    def test_a_buried_stretch_is_reported_in_metres_not_silently_dropped(self) -> None:
        edge = straight(0.0, 100.0)
        drawn = ribbon(edge, hidden={NEARSIDE: [[40.0, 60.0]]})
        report = RailingReport()
        _draw_run(_Builder(), drawn, NEARSIDE, 10, 89, "CRAIL1", spec(), report)
        assert report.metres_on_buried_kerb == pytest.approx(20.0)
        assert report.drawn_m == pytest.approx(60.0)


class TestWinding:
    """Under `cull_disabled` a flipped quad still draws — lit from behind.

    So the winding is checked against the normal each vertex was given, which is
    the direction that looks at the carriageway. `railings.json` publishes this
    as `facing_away` and it must be 0 (`Q58`).
    """

    @pytest.mark.parametrize("side", [NEARSIDE, OFFSIDE])
    def test_every_quad_is_wound_toward_the_road(self, side: str) -> None:
        edge = straight(0.0, 100.0)
        builder = _Builder()
        _draw_run(builder, ribbon(edge), side, 10, 89, "CRAIL1", spec(), RailingReport())
        mesh = builder.build("railings")
        assert mesh is not None
        assert facing_away(mesh) == 0

    @pytest.mark.parametrize("side", [NEARSIDE, OFFSIDE])
    def test_the_normal_points_across_the_fence_at_the_centreline(self, side: str) -> None:
        """Not merely consistent — pointing the right way.

        `facing_away` compares winding against the normal, so a mesh built with
        *both* reversed would pass it. This is the second half: the normal is
        the direction from the fence back to the road, and on a street running
        east that is `+Z` for the nearside fence and `-Z` for the offside one.
        """
        edge = straight(0.0, 100.0)
        builder = _Builder()
        _draw_run(builder, ribbon(edge), side, 10, 89, "CRAIL1", spec(), RailingReport())
        mesh = builder.build("railings")
        assert mesh is not None
        expected = 1.0 if side == NEARSIDE else -1.0
        assert np.allclose(mesh.normals[:, 2], expected, atol=1e-6)
        assert np.allclose(mesh.normals[:, 1], 0.0, atol=1e-6)


class TestFence:
    def test_the_fence_stands_outside_the_drawn_carriageway_edge(self) -> None:
        """`outset_m` puts it behind the kerb strip, not on the lane.

        A fence *on* the carriageway edge is one the player's wheel clips while
        driving in lane, and the kerb `surface.py` draws is 0.5 m wide.
        """
        edge = straight(0.0, 100.0)
        builder = _Builder()
        _draw_run(builder, ribbon(edge), NEARSIDE, 10, 89, "CRAIL1", spec(), RailingReport())
        mesh = builder.build("railings")
        assert mesh is not None
        across = np.abs(mesh.positions[:, 2] - 100.0)
        assert np.allclose(across, 5.6, atol=1e-6)

    def test_the_fence_is_as_tall_as_it_was_authored_and_sinks_below_the_road(self) -> None:
        edge = straight(0.0, 100.0)
        builder = _Builder()
        _draw_run(builder, ribbon(edge), NEARSIDE, 10, 89, "CRAIL1", spec(), RailingReport())
        mesh = builder.build("railings")
        assert mesh is not None
        assert mesh.positions[:, 1].min() == pytest.approx(-0.25)
        assert mesh.positions[:, 1].max() == pytest.approx(1.1)

    def test_a_run_past_the_ribbons_end_is_clipped_rather_than_drawn(self) -> None:
        """The ribbon stops short of the junction; the cap fills the middle.

        A fence drawn past that point crosses the junction mouth, standing on
        tarmac that has no kerb at all.
        """
        edge = straight(0.0, 100.0)
        report = RailingReport()
        _draw_run(_Builder(), ribbon(edge), NEARSIDE, 80, 139, "CRAIL1", spec(), report)
        assert report.metres_outside_ribbon == pytest.approx(40.0)
        assert report.drawn_m == pytest.approx(20.0)

    def test_metres_bridged_counts_the_fence_the_source_never_published(self) -> None:
        """The one part of `drawn_m` this stage invents.

        `merge_runs` bridges gaps up to `bridge_gap_m`, so a fence crosses them
        with nothing underneath it in the source. Right — a break shorter than a
        car is a digitising artefact — but it is invention, and until it was
        counted the region's numbers were out by 400 m with nothing saying why.
        """
        edge = straight(0.0, 100.0)
        occupied = {cell: {"CRAIL1": 1} for cell in list(range(10, 20)) + list(range(23, 40))}
        report = RailingReport()
        _draw_run(_Builder(), ribbon(edge), NEARSIDE, 10, 39, "CRAIL1", spec(), report, occupied)
        # Cells 20, 21 and 22 carried no sample and were bridged.
        assert report.metres_bridged == pytest.approx(3.0)
        assert report.drawn_m == pytest.approx(30.0)

    def test_nothing_is_bridged_when_every_cell_carried_a_sample(self) -> None:
        edge = straight(0.0, 100.0)
        occupied = {cell: {"CRAIL1": 1} for cell in range(10, 40)}
        report = RailingReport()
        _draw_run(_Builder(), ribbon(edge), NEARSIDE, 10, 39, "CRAIL1", spec(), report, occupied)
        assert report.metres_bridged == 0.0

    def test_a_run_shorter_than_a_car_is_a_post_and_is_dropped(self) -> None:
        edge = straight(0.0, 100.0)
        report = RailingReport()
        _draw_run(_Builder(), ribbon(edge), NEARSIDE, 10, 11, "CRAIL1", spec(), report)
        assert report.runs_dropped == 1
        assert report.metres_dropped_short == pytest.approx(2.0)
        assert report.drawn_m == 0.0


class TestTrims:
    def test_a_run_is_measured_along_the_published_polyline_and_drawn_along_the_ribbon(
        self,
    ) -> None:
        """The frame shift that would be silent.

        `SideIndex` measures `along_m` in `roadgraph.json`'s frame; the ribbon
        starts `trim_m[0]` further on. Forget the conversion and every fence in
        the city slides by a junction trim — a median 3.3 m in this region — and
        still looks like a fence.
        """
        edge = straight(0.0, 100.0)
        drawn = ribbon(edge, trim_start_m=10.0)
        report = RailingReport()
        _draw_run(_Builder(), drawn, NEARSIDE, 20, 39, "CRAIL1", spec(), report)
        # Cells 20..39 are 20-40 m along the published polyline, so 10-30 m
        # along a ribbon trimmed by 10.
        assert report.drawn_m == pytest.approx(20.0)
        assert report.metres_outside_ribbon == pytest.approx(0.0)
