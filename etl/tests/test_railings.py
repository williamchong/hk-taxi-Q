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

from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import RailingClass, Railings, SourceLayer, load_config
from pipeline.kerbside import NEARSIDE, OFFSIDE
from pipeline.polyline import plan_lengths
from pipeline.railings import (
    ClassReport,
    RailingReport,
    Ribbon,
    _assign,
    _Builder,
    _draw_run,
    _sides,
    _visible,
    facing_away,
)
from pipeline.surface import mitres
from tests.helpers import CITY_YAML

# Far enough from the origin that nothing here clips on the region bounds, and
# far enough from them that a kerb is never outside the region.
WHOLE_WORLD = (10_000.0, 10_000.0)


# The class every fixture here draws. `Q61` splits the layer into three, and
# these tests are about the join and the geometry, which are the same code for
# all three — so one class is exercised and its `id` is the fence's, because
# that is the one whose published figures the docstrings quote.
CLASS_ID = "railings"


def klass(**overrides) -> RailingClass:
    """The Hong Kong fence class, which is what every published figure was measured at."""
    values = {
        "id": CLASS_ID,
        "line_types": ("CRAIL1",),
        "bridge_gap_m": 4.0,
        "min_run_m": 4.0,
        "station_m": 2.0,
        "height_m": 1.1,
        "base_sink_m": 0.25,
        "outset_m": 0.6,
    }
    return RailingClass(**{**values, **overrides})


def spec(**overrides) -> Railings:
    """The Hong Kong tuning, with one class.

    Overrides naming a `RailingClass` field are routed to the class, so a test
    written before `Q61` split the block reads the same as it always did.
    """
    on_class = {
        name: overrides.pop(name)
        for name in list(overrides)
        if name in RailingClass.__dataclass_fields__
    }
    values = {
        "source": "traffic_aids",
        "member": None,
        "layer": SourceLayer(
            layer="DTAD_RAILING_LINE", fields={"line_type": "LINETYPE", "level": "ELEVATION"}
        ),
        "sample_m": 1.0,
        "max_offset_m": 12.0,
        "max_shift_m": 3.0,
        "classes": (klass(**on_class),),
    }
    return Railings(**{**values, **overrides})


def drew(report: RailingReport) -> ClassReport:
    """The counters for the one class these fixtures draw."""
    return report.klass(CLASS_ID)


class _City:
    """The one thing `_assign` asks a `CityConfig` for."""

    def region_high(self, region_id: str) -> tuple[float, float]:
        del region_id
        return WHOLE_WORLD


def straight(x0: float, x1: float, z: float = 100.0, half: float = 5.0) -> np.ndarray:
    """An edge polyline in game space, as `roads.py` publishes one: x, y, z."""
    return np.array([[x0, 0.0, z], [x1, 0.0, z]], dtype=np.float64)


def ribbon(edge: np.ndarray, classes=(), half: float = 5.0, **overrides) -> Ribbon:
    """One edge's drawn ribbon, built the way `railings.ribbons` builds it.

    Through `mitres` and the stage's own `_sides` rather than by writing the
    offset out here: those are what `surface.py` draws the carriageway edge with,
    and a fixture that computed its own would agree with a wrong stage.

    `classes` defaults to the one fence class; pass several and each gets its own
    standing line at its own `outset_m`, which is what `ribbons` does.
    """
    shaped = np.column_stack([edge, np.full(len(edge), half)])
    offsets = mitres(shaped)
    values = {
        "points": shaped,
        "fence": {
            entry.id: _sides(shaped, offsets, entry.outset_m) for entry in (classes or (klass(),))
        },
        # `plan_lengths`, because that is what `railings.ribbons` uses — the
        # hand-written two-point version this fixture used to carry only
        # described a straight edge, and `TestFenceCoordinate` needs a bend.
        "along": plan_lengths(shaped),
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
        assert {side for _, _, side in cells} == {NEARSIDE}

    def test_a_railing_on_the_other_kerb_is_the_offside(self) -> None:
        edge = straight(0.0, 100.0)
        rail = edge[:, [0, 2]] - mitres(edge) * 5.0
        kerb_z = 100.0 + (float(rail[0, 1]) - 100.0) * 1.1

        cells, _ = assign(
            [(beside(10.0, 90.0, kerb_z), "CRAIL1")],
            [(7, edge)],
            {7: ribbon(edge)},
        )
        assert {side for _, _, side in cells} == {OFFSIDE}


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
        assert drew(report).samples_over_shift == 0
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
        assert drew(report).samples_over_shift == 80
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
        assert len(drew(report).shift_m) == 80
        assert max(drew(report).shift_m) > spec().max_shift_m


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
        _draw_run(_Builder(), drawn, klass(), NEARSIDE, 10, 89, "CRAIL1", spec().sample_m, report)
        assert drew(report).metres_on_buried_kerb == pytest.approx(20.0)
        assert drew(report).drawn_m == pytest.approx(60.0)


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
        _draw_run(
            builder, ribbon(edge), klass(), side, 10, 89, "CRAIL1", spec().sample_m, RailingReport()
        )
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
        _draw_run(
            builder, ribbon(edge), klass(), side, 10, 89, "CRAIL1", spec().sample_m, RailingReport()
        )
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
        _draw_run(
            builder,
            ribbon(edge),
            klass(),
            NEARSIDE,
            10,
            89,
            "CRAIL1",
            spec().sample_m,
            RailingReport(),
        )
        mesh = builder.build("railings")
        assert mesh is not None
        across = np.abs(mesh.positions[:, 2] - 100.0)
        assert np.allclose(across, 5.6, atol=1e-6)

    def test_the_fence_is_as_tall_as_it_was_authored_and_sinks_below_the_road(self) -> None:
        edge = straight(0.0, 100.0)
        builder = _Builder()
        _draw_run(
            builder,
            ribbon(edge),
            klass(),
            NEARSIDE,
            10,
            89,
            "CRAIL1",
            spec().sample_m,
            RailingReport(),
        )
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
        _draw_run(
            _Builder(), ribbon(edge), klass(), NEARSIDE, 80, 139, "CRAIL1", spec().sample_m, report
        )
        assert drew(report).metres_outside_ribbon == pytest.approx(40.0)
        assert drew(report).drawn_m == pytest.approx(20.0)

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
        _draw_run(
            _Builder(),
            ribbon(edge),
            klass(),
            NEARSIDE,
            10,
            39,
            "CRAIL1",
            spec().sample_m,
            report,
            occupied,
        )
        # Cells 20, 21 and 22 carried no sample and were bridged.
        assert drew(report).metres_bridged == pytest.approx(3.0)
        assert drew(report).drawn_m == pytest.approx(30.0)

    def test_nothing_is_bridged_when_every_cell_carried_a_sample(self) -> None:
        edge = straight(0.0, 100.0)
        occupied = {cell: {"CRAIL1": 1} for cell in range(10, 40)}
        report = RailingReport()
        _draw_run(
            _Builder(),
            ribbon(edge),
            klass(),
            NEARSIDE,
            10,
            39,
            "CRAIL1",
            spec().sample_m,
            report,
            occupied,
        )
        assert drew(report).metres_bridged == 0.0

    def test_a_run_shorter_than_a_car_is_a_post_and_is_dropped(self) -> None:
        edge = straight(0.0, 100.0)
        report = RailingReport()
        _draw_run(
            _Builder(), ribbon(edge), klass(), NEARSIDE, 10, 11, "CRAIL1", spec().sample_m, report
        )
        assert drew(report).runs_dropped == 1
        assert drew(report).metres_dropped_short == pytest.approx(2.0)
        assert drew(report).drawn_m == 0.0


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
        _draw_run(_Builder(), drawn, klass(), NEARSIDE, 20, 39, "CRAIL1", spec().sample_m, report)
        # Cells 20..39 are 20-40 m along the published polyline, so 10-30 m
        # along a ribbon trimmed by 10.
        assert drew(report).drawn_m == pytest.approx(20.0)
        assert drew(report).metres_outside_ribbon == pytest.approx(0.0)


class TestFenceCoordinate:
    """`TEXCOORD_0` is `(metres along the fence, metres above the deck)` (`Q61`).

    ⚠️ **Nothing downstream can check this and everything downstream depends on
    it.** `railings.gdshader` cuts every baluster, post and rail out of these two
    numbers, so a `v` measured from the wrong datum puts the top rail underground
    and a `u` measured along the wrong line gives the fence a limp around every
    corner — and both render as a fence.
    """

    def test_v_is_the_authored_height_and_sink_measured_from_the_deck(self) -> None:
        """Exactly two planes, and they are the authored figures rather than a fraction."""
        builder = _Builder()
        _draw_run(
            builder,
            ribbon(straight(0.0, 100.0)),
            klass(),
            NEARSIDE,
            10,
            89,
            "CRAIL1",
            spec().sample_m,
            RailingReport(),
        )
        mesh = builder.build(CLASS_ID)
        assert mesh is not None
        assert sorted(set(np.round(mesh.uvs[:, 1], 6))) == [-0.25, 1.1]

    def test_v_follows_the_class_rather_than_the_fence(self) -> None:
        """A shorter class is shorter in the coordinate too, not just in the mesh."""
        builder = _Builder()
        low = klass(height_m=0.85, base_sink_m=0.1)
        _draw_run(
            builder,
            ribbon(straight(0.0, 100.0)),
            low,
            NEARSIDE,
            10,
            89,
            "CRAIL1",
            spec().sample_m,
            RailingReport(),
        )
        mesh = builder.build(CLASS_ID)
        assert mesh is not None
        assert sorted(set(np.round(mesh.uvs[:, 1], 6))) == [-0.1, 0.85]

    def test_u_measures_the_fence_line_and_not_the_centreline(self) -> None:
        """The assertion that catches the limp.

        On a bend the fence line and the centreline differ by the ratio of their
        radii, so a `u` taken from the station's ribbon distance would not match
        the kerb it is drawn on and the balusters would stretch round the corner.
        Checked against the drawn positions themselves, which is the only ground
        truth that cannot agree with a wrong stage.
        """
        edge = np.array(
            [[0.0, 0.0, 100.0], [100.0, 0.0, 100.0], [100.0, 0.0, 200.0]], dtype=np.float64
        )
        builder = _Builder()
        _draw_run(
            builder,
            ribbon(edge),
            klass(),
            NEARSIDE,
            0,
            199,
            "CRAIL1",
            spec().sample_m,
            RailingReport(),
        )
        mesh = builder.build(CLASS_ID)
        assert mesh is not None

        foot = mesh.uvs[:, 1] < 0.0
        plan = mesh.positions[foot][:, [0, 2]]
        walked = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(plan, axis=0).T))])
        # A millimetre, because `TEXCOORD_0` ships as float32 and the run is
        # 200 m long — the float32 step up there is already 15 microns.
        assert np.allclose(mesh.uvs[foot][:, 0], walked, atol=1e-3)
        # And it is genuinely not the centreline: this bend makes the two differ
        # by more than a baluster pitch, which is what the test is worth.
        assert abs(float(walked[-1]) - 200.0) > 1.0


class TestClasses:
    """The layer draws more than one kind of thing, and they must not merge (`Q61`)."""

    def test_two_classes_on_one_kerb_stay_two_runs(self) -> None:
        """⚠️ Pooled into one cell they would be drawn once, at one height.

        A bollard row and a railing are published along the same kerb often
        enough that this is the ordinary case, not a corner. Keyed apart they
        stay two runs; keyed together the second silently becomes the first.
        """
        edge = straight(0.0, 100.0)
        fence = klass()
        posts = klass(id="bollards", line_types=("bollard0",), min_run_m=1.0, height_m=0.85)
        report = RailingReport()
        cells = _assign(
            [(beside(10.0, 90.0, 104.0), "CRAIL1"), (beside(10.0, 90.0, 104.0), "bollard0")],
            {"edges": [{"id": 7, "polyline": edge, "elevation_level": 0}]},
            {7: ribbon(edge, classes=(fence, posts))},
            spec(classes=(fence, posts)),
            _City(),
            "middle",
            report,
        )

        assert {class_id for _, class_id, _ in cells} == {"railings", "bollards"}
        assert report.klass("railings").metres_deduped == pytest.approx(80.0)
        assert report.klass("bollards").metres_deduped == pytest.approx(80.0)

    def test_each_class_is_priced_against_its_own_outset(self) -> None:
        """The shift is per class, because the classes stand in different places."""
        edge = straight(0.0, 100.0)
        fence = klass()
        far = klass(id="bollards", line_types=("bollard0",), outset_m=2.6)
        report = RailingReport()
        _assign(
            [(beside(10.0, 90.0, 104.0), "CRAIL1"), (beside(10.0, 90.0, 104.0), "bollard0")],
            {"edges": [{"id": 7, "polyline": edge, "elevation_level": 0}]},
            {7: ribbon(edge, classes=(fence, far))},
            spec(classes=(fence, far)),
            _City(),
            "middle",
            report,
        )
        # The railing stands at 5.6 m and the bollard at 7.6 m, so a line at
        # 4.0 m moves 1.6 m for one and 3.6 m for the other.
        assert max(report.klass("railings").shift_m) == pytest.approx(1.6)
        assert max(report.klass("bollards").shift_m) == pytest.approx(3.6)


class TestClassTable:
    """What the loader refuses, and why each refusal is not tidiness (`Q61`).

    Through the **real loader** on a mutated shipped document, which is
    `test_tramway.city_with`'s argument and `test_config.py`'s `rewrite`'s before
    it: *"a stub would drift out of step with the schema and keep passing while
    the real config broke."* A hand-written block dict is that stub.
    """

    @staticmethod
    def _class(**overrides) -> dict[str, Any]:
        return {
            "id": "railings",
            "line_types": ["CRAIL1"],
            "bridge_gap_m": 4.0,
            "min_run_m": 4.0,
            "station_m": 2.0,
            "height_m": 1.1,
            "base_sink_m": 0.25,
            "outset_m": 0.6,
            **overrides,
        }

    @staticmethod
    def _city(tmp_path, classes: list[dict[str, Any]]):
        document = yaml.safe_load(CITY_YAML)
        document["railings"] = {
            "source": "stands",
            "layer": "DTAD_RAILING_LINE",
            "fields": {"line_type": "LINETYPE", "level": "ELEVATION"},
            "sample_m": 1.0,
            "max_offset_m": 12.0,
            "max_shift_m": 3.0,
            "classes": classes,
        }
        cities = tmp_path / "cities"
        cities.mkdir(exist_ok=True)
        (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
        return load_config(cities / "testville.yaml")

    def test_a_code_in_two_classes_is_refused(self, tmp_path) -> None:
        """⚠️ Not tidiness: it would be drawn twice, and both would look right."""
        with pytest.raises(ValueError, match="drawn twice"):
            self._city(
                tmp_path,
                [self._class(), self._class(id="bollards", line_types=["bollard0", "CRAIL1"])],
            )

    def test_two_classes_may_not_share_an_id(self, tmp_path) -> None:
        """An id is a mesh name and a material name; two would collide in one file."""
        with pytest.raises(ValueError, match="repeats an id"):
            self._city(tmp_path, [self._class(), self._class(line_types=["bollard0"])])

    def test_an_id_that_would_build_a_collider_is_refused(self, tmp_path) -> None:
        """The guard that used to be one string in `pipeline/railings.py`.

        Godot's importer turns a `-col` suffix into a static body, and
        `GAME_DESIGN.md` puts this whole layer under "omit or make breakable" —
        so a city config must not be able to hand the region 9 km of wall.
        """
        with pytest.raises(ValueError, match="-col"):
            self._city(tmp_path, [self._class(id="railings-col")])

    def test_a_min_run_under_the_sample_pitch_is_refused(self, tmp_path) -> None:
        """It could refuse nothing: the shortest run the sampler makes is one cell."""
        with pytest.raises(ValueError, match="would refuse nothing"):
            self._city(tmp_path, [self._class(min_run_m=0.5)])

    def test_a_dimension_that_is_not_finite_is_refused(self, tmp_path) -> None:
        """⚠️ The value that never announces itself.

        YAML 1.1 resolves `.nan`, and a NaN passes every sign test — then makes
        false every comparison downstream and ships a mesh of NaN vertices.
        `config._measures` is what catches it, and this stage reached for it only
        after hand-rolling the sign check without the finiteness one.
        """
        with pytest.raises(ValueError, match="finite"):
            self._city(tmp_path, [self._class(height_m=float("nan"))])

    def test_the_drawn_line_types_are_the_union_of_the_classes(self, tmp_path) -> None:
        """Derived, so a code cannot be admitted and then belong to no class."""
        spec_ = self._city(
            tmp_path, [self._class(), self._class(id="bollards", line_types=["bollard0"])]
        ).railings
        assert spec_ is not None
        assert spec_.drawn_line_types == ("CRAIL1", "bollard0")
        assert spec_.class_of("CRAIL1").id == "railings"
        assert spec_.class_of("bollard0").id == "bollards"
        assert spec_.class_of("SOLID") is None
