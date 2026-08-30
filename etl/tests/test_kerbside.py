"""The `NSR` join (`P3-13`, closes `Q54`).

The unit tests cover the four things that decide whether a published run means
anything — which side of the ribbon it lands on, that two source features
covering one kerb count once, that a hairline break is not two restrictions, and
that a restriction belonging to no road here is refused rather than dragged onto
the nearest one. The integration test then builds a whole graph with a
no-stopping layer in it, so the wiring is exercised rather than assumed.

⚠️ **The side tests are the point of this file.** A mirrored side convention
renders as a road: every yellow line in the city moves to the other kerb and
nothing looks broken. So the convention is asserted twice — once against
`surface.mitres`, which is the code that decides where `U = 0` goes, and once in
plain terms against a street whose kerbs can be named.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pipeline.config import KERB_DOUBLE, KERB_SINGLE, KerbsideRestrictions, SourceLayer
from pipeline.kerbside import (
    NEARSIDE,
    OFFSIDE,
    KerbsideReport,
    _assign,
)
from pipeline.roads import build_region
from pipeline.surface import mitres

# Far enough away that nothing in a unit test clips on it.
WHOLE_WORLD = (10_000.0, 10_000.0)


def spec(**overrides) -> KerbsideRestrictions:
    """The Hong Kong tuning, which is what every published figure was measured at."""
    values = {
        "layer": SourceLayer(layer="NSR", fields={"vehicle_type": "V", "time_zone": "T"}),
        "painted_vehicle_types": frozenset({1}),
        "kinds": {1: KERB_DOUBLE, 2: KERB_SINGLE},
        "sample_m": 1.0,
        "bridge_gap_m": 3.0,
        "min_run_m": 5.0,
        "max_offset_m": 20.0,
    }
    return KerbsideRestrictions(**{**values, **overrides})


def run(lines, tracks, **overrides) -> KerbsideReport:
    report = KerbsideReport()
    _assign(lines, tracks, spec(**overrides), WHOLE_WORLD, report)
    return report


def straight(x0: float, x1: float, z: float = 100.0) -> np.ndarray:
    """An edge polyline in game space, as `roads.py` publishes one: x, y, z.

    Held off the origin because game coordinates start there: a street on `z =
    0` has its northern kerb outside the region, and `_assign` would drop every
    sample of it as out of bounds rather than assigning it a side.
    """
    return np.array([[x0, 0.0, z], [x1, 0.0, z]], dtype=np.float64)


def beside(x0: float, x1: float, z: float) -> np.ndarray:
    """A restriction line in game plan coordinates: x, z."""
    return np.array([[x0, z], [x1, z]], dtype=np.float64)


class TestSide:
    def test_the_nearside_is_the_side_mitres_puts_u_zero_on(self) -> None:
        """The assertion that cannot drift.

        `surface.mitres` offsets one half-width to the left of travel and
        `_draw_edge` gives that rail `U = 0`. This checks the join agrees with
        that *code* rather than with a comment about it — so if the offset ever
        flips, this fails on the same day rather than shipping a mirrored city.
        """
        edge = straight(0.0, 100.0)
        rail = edge[:, [0, 2]] + mitres(edge) * 5.0
        # The rail is one half-width off the centreline; put the restriction a
        # little beyond it, where a real kerb would be.
        kerb_z = 100.0 + (float(rail[0, 1]) - 100.0) * 1.2

        report = run([(beside(10.0, 90.0, kerb_z), KERB_DOUBLE)], [(7, edge)])
        assert [item.side for item in report.restrictions] == [NEARSIDE]

    def test_an_eastbound_street_takes_its_restriction_on_its_north_kerb(self) -> None:
        """The same fact in terms someone can check against a map.

        Game X is east and game Z is *south* — the transform flips north to -Z.
        Hong Kong drives on the left, so traffic heading east keeps to the north
        half of the road and its nearside kerb is the northern one.
        """
        edge = straight(0.0, 100.0)
        north = run([(beside(10.0, 90.0, 94.0), KERB_DOUBLE)], [(1, edge)])
        south = run([(beside(10.0, 90.0, 106.0), KERB_DOUBLE)], [(1, edge)])

        assert [item.side for item in north.restrictions] == [NEARSIDE]
        assert [item.side for item in south.restrictions] == [OFFSIDE]

    def test_reversing_the_edge_moves_the_restriction_to_the_other_side(self) -> None:
        """Side is a property of travel, not of the map.

        `roads.py` normalises a backward centreline by reversing its points, so
        the same kerb changes side when it does — and that is correct, because
        the ribbon's `U = 0` moves with it.
        """
        forward = run([(beside(10.0, 90.0, 94.0), KERB_DOUBLE)], [(1, straight(0.0, 100.0))])
        backward = run([(beside(10.0, 90.0, 94.0), KERB_DOUBLE)], [(1, straight(100.0, 0.0))])

        assert [item.side for item in forward.restrictions] == [NEARSIDE]
        assert [item.side for item in backward.restrictions] == [OFFSIDE]


class TestRuns:
    def test_two_features_covering_one_kerb_are_counted_once(self) -> None:
        """The dedupe `Q54`'s harm figures were measured without.

        The source overlaps its own features — 1,736 m of Wan Chai's 27,854 —
        and a run built by adding lengths would report a kerb as more restricted
        than it is long.
        """
        line = beside(10.0, 90.0, 94.0)
        report = run([(line, KERB_DOUBLE), (line, KERB_DOUBLE)], [(1, straight(0.0, 100.0))])

        assert len(report.restrictions) == 1
        assert report.metres_sampled == pytest.approx(160.0)
        assert report.metres_deduped == pytest.approx(80.0)
        assert report.metres_published == pytest.approx(80.0)

    def test_a_break_shorter_than_a_car_is_bridged(self) -> None:
        report = run(
            [
                (beside(10.0, 40.0, 94.0), KERB_DOUBLE),
                (beside(42.0, 90.0, 94.0), KERB_DOUBLE),
            ],
            [(1, straight(0.0, 100.0))],
        )
        assert len(report.restrictions) == 1

    def test_a_break_longer_than_a_car_is_two_runs(self) -> None:
        report = run(
            [
                (beside(10.0, 40.0, 94.0), KERB_DOUBLE),
                (beside(60.0, 90.0, 94.0), KERB_DOUBLE),
            ],
            [(1, straight(0.0, 100.0))],
        )
        assert len(report.restrictions) == 2
        assert [item.side for item in report.restrictions] == [NEARSIDE, NEARSIDE]

    def test_a_run_under_the_minimum_is_dropped_and_reported(self) -> None:
        report = run([(beside(10.0, 13.0, 94.0), KERB_DOUBLE)], [(1, straight(0.0, 100.0))])
        assert report.restrictions == []
        assert report.runs_dropped == 1
        assert report.metres_dropped == pytest.approx(3.0)

    def test_a_run_takes_the_kind_most_of_it_carries(self) -> None:
        """One kind per run, decided by length rather than by feature count.

        `TIME_ZONE` is the double-versus-single distinction, and the source
        draws a short posted-hours feature over the end of a 24-hour one often
        enough that the first feature read would otherwise decide the whole run.
        """
        report = run(
            [
                (beside(10.0, 90.0, 94.0), KERB_DOUBLE),
                (beside(10.0, 20.0, 94.0), KERB_SINGLE),
            ],
            [(1, straight(0.0, 100.0))],
        )
        assert [item.kind for item in report.restrictions] == [KERB_DOUBLE]


class TestAssignment:
    def test_a_restriction_belonging_to_no_road_here_is_refused(self) -> None:
        report = run(
            [(beside(10.0, 90.0, 160.0), KERB_DOUBLE)],
            [(1, straight(0.0, 100.0))],
            max_offset_m=20.0,
        )
        assert report.restrictions == []
        assert report.samples_unassigned == 80

    def test_a_sample_outside_the_region_is_counted_rather_than_assigned(self) -> None:
        """The geodatabase filters on bounding box, so a feature reaching well
        past the region comes back whole. Those samples are ordinary, and
        keeping them apart from the unassigned ones is what makes the second
        number worth reading."""
        report = KerbsideReport()
        _assign(
            [(beside(-100.0, 90.0, 94.0), KERB_DOUBLE)],
            [(1, straight(0.0, 100.0))],
            spec(),
            (200.0, 200.0),
            report,
        )
        assert report.samples_outside_region == 100
        assert report.samples_unassigned == 0

    def test_the_nearer_of_two_parallel_streets_wins(self) -> None:
        report = run(
            [(beside(10.0, 90.0, 94.0), KERB_DOUBLE)],
            [(1, straight(0.0, 100.0)), (2, straight(0.0, 100.0, 60.0))],
        )
        assert {item.edge for item in report.restrictions} == {1}

    def test_the_run_is_measured_along_the_edge_it_landed_on(self) -> None:
        report = run([(beside(30.0, 70.0, 94.0), KERB_DOUBLE)], [(1, straight(0.0, 100.0))])
        (found,) = report.restrictions
        assert found.start_m == pytest.approx(30.0, abs=1.0)
        assert found.end_m == pytest.approx(70.0, abs=1.0)


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------


class TestBuildRegion:
    def test_the_graph_carries_the_runs_it_joined(self, testville) -> None:
        city, root = testville
        report = build_region(city, "middle", sources_root=root / "sources", out_root=root / "out")
        document = json.loads((root / "out" / "middle" / "roadgraph.json").read_text())

        assert report.kerbside is not None
        assert report.kerbside.features_read == 4
        assert report.kerbside.features_painted == 3
        # The refusal, reported rather than dropped in silence.
        assert report.kerbside.metres_refused[4] == pytest.approx(80.0, abs=1.0)

        runs = [
            (run["side"], run["kind"]) for edge in document["edges"] for run in edge["kerbside"]
        ]
        assert sorted(runs) == [(NEARSIDE, KERB_DOUBLE), (OFFSIDE, KERB_SINGLE)]
