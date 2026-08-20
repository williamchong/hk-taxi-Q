"""The tramway stage (`P3-14`, `Q58`).

Weighted towards the join rather than the drawing, because the join is where
this stage can be confidently wrong: a bed drawn between two rails that are not
a track renders perfectly and is a lane wide in the wrong place. Two of the
tests below are regressions on defects that shipped into a built region during
`P3-14` and were caught by `drawn_gauge_m` rather than by a frame.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import load_city
from pipeline.surface import downward_facing
from pipeline.tramway import (
    TRAMWAY_CLASS_BED,
    TRAMWAY_CLASS_RAIL,
    TRAMWAY_MATERIAL,
    TramwayReport,
    _Builder,
    _draw,
    _pair_rails,
    _project,
    _snap_heights,
    _track_centres,
)
from tests.helpers import CITY_YAML

GAUGE_M = 1.067
TOLERANCE_M = 0.35

# The block as `hong_kong.yaml` declares it, with `testville`'s own materials.
# Held here rather than in `helpers.py`'s `CITY_YAML` because the tramway is
# optional by contract, and the fixture city's job is to prove that a city
# without one still builds — see `test_the_block_is_optional`.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "CartoTransLine",
    "fields": {"line_type": "TYPE"},
    "codes": ["TW"],
    "gauge_m": GAUGE_M,
    "pair_tolerance_m": TOLERANCE_M,
    "rail_width_m": 0.14,
    "bed_width_m": 2.2,
    "bed_lift_m": 0.02,
    "rail_lift_m": 0.01,
    "max_snap_m": 25.0,
    "rail_material": "kerb",
    "bed_material": "asphalt",
}


def city_with(tmp_path, block: dict[str, Any] | None):
    """`testville` carrying the given tramway block, loaded through the real
    loader — the same argument `test_config.py`'s `rewrite` makes for mutating
    the shipped document rather than hand-writing a stub."""
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["tramway"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_city("testville", cities_root=cities)


def rail(x0: float, x1: float, z: float, *, step: float = 5.0) -> np.ndarray:
    """A straight rail along +X at offset `z`, in game space with y = 0."""
    xs = np.arange(x0, x1 + step * 0.5, step)
    return np.column_stack([xs, np.zeros(len(xs)), np.full(len(xs), z)])


@pytest.fixture
def spec(tmp_path):
    """`testville` with a tramway block bolted on.

    Built by rewriting the fixture document rather than by constructing a
    `Tramway` directly, so the block's own parsing and its material lookup are
    exercised by every geometry test rather than only by the config tests.
    """
    return city_with(tmp_path, BLOCK).tramway


class TestPairing:
    """Which rails are the two sides of one track."""

    def test_two_rails_a_gauge_apart_are_one_track(self, spec) -> None:
        parts = [rail(0.0, 100.0, 0.0), rail(0.0, 100.0, GAUGE_M)]
        report = TramwayReport()

        pairs = _pair_rails(parts, spec, report)

        assert pairs == [(0, 1)]
        assert report.paired == 2
        assert report.unpaired == 0

    def test_a_mutual_pair_is_one_track_and_not_two(self, spec) -> None:
        """Both rails vote for each other; the bed must still be drawn once.

        Drawn twice it is two coplanar strips in the same place, which z-fights
        rather than failing.
        """
        parts = [rail(0.0, 100.0, 0.0), rail(0.0, 100.0, GAUGE_M)]

        assert len(_pair_rails(parts, spec, TramwayReport())) == 1

    def test_rails_a_track_apart_do_not_pair(self, spec) -> None:
        """2.6 m is the measured separation between two *tracks* (`Q58`), which
        is well outside the tolerance and must not read as a gauge."""
        parts = [rail(0.0, 100.0, 0.0), rail(0.0, 100.0, 2.6)]
        report = TramwayReport()

        assert _pair_rails(parts, spec, report) == []
        assert report.unpaired == 2

    def test_a_rail_split_across_sheets_still_pairs(self, spec) -> None:
        """⚠️ **The regression that cost a fifth of the region's tramway.**

        iB1000 is published per sheet, so a rail crossing a boundary arrives as
        two parts while the rail beside it arrives as one. The long rail's
        stations then split their ballot between the two halves and clear no
        threshold; requiring the vote to be *mutual* dropped all three, 38 of
        132 parts. Both halves must be drawn against their own stretch.
        """
        parts = [
            rail(0.0, 100.0, 0.0),  # one long rail
            rail(0.0, 48.0, GAUGE_M),  # its opposite number, sheet-split
            rail(52.0, 100.0, GAUGE_M),
        ]
        report = TramwayReport()

        pairs = _pair_rails(parts, spec, report)

        assert {partner for _, partner in pairs} | {v for v, _ in pairs} == {0, 1, 2}
        assert report.unpaired == 0

    def test_a_rail_alone_is_reported_rather_than_raised(self, spec) -> None:
        parts = [rail(0.0, 100.0, 0.0)]
        report = TramwayReport()

        assert _pair_rails(parts, spec, report) == []
        assert report.unpaired == 1


class TestTrackCentres:
    """Where the bed goes, and how far along it is drawn."""

    def test_the_centreline_sits_half_a_gauge_from_each_rail(self, spec) -> None:
        left, right = rail(0.0, 100.0, 0.0), rail(0.0, 100.0, GAUGE_M)

        runs, rejected, tested = _track_centres(left, right, spec)

        assert len(runs) == 1
        assert rejected == 0
        assert tested == len(left)
        spine, gauges = runs[0]
        assert np.allclose(spine[:, 2], GAUGE_M * 0.5)
        # The gauge comes back per station, from the half-offset the trim
        # already computed rather than measured again afterwards.
        assert np.allclose(gauges, GAUGE_M)

    def test_a_track_is_trimmed_to_where_both_rails_run(self, spec) -> None:
        """⚠️ **The defect `drawn_gauge_m` caught, and a frame would not.**

        `_project` clamps to the partner's nearest end, so a rail running on
        past its partner keeps generating a "centre" that walks steadily out
        towards it. The bed then flares out of the four-foot at every sheet
        boundary. Untrimmed this read p90 **1.92 m** against a 1.067 m gauge.
        """
        left, right = rail(0.0, 100.0, 0.0), rail(0.0, 40.0, GAUGE_M)

        runs, rejected, _ = _track_centres(left, right, spec)

        assert len(runs) == 1
        spine, _ = runs[0]
        assert spine[:, 0].max() <= 45.0
        assert np.allclose(spine[:, 2], GAUGE_M * 0.5)
        # ⚠️ The rejected count is what the manifest publishes as the join's
        # detector — `drawn_gauge_m` cannot see this, because every station it
        # reports is one the trim already accepted.
        assert rejected > 0

    def test_a_pair_that_parts_and_rejoins_is_two_runs(self, spec) -> None:
        """A crossover swings away from the gauge and comes back.

        Modelled as a rail that *diverges* rather than as two disjoint parts,
        because a single published part is one polyline and cannot have a hole
        in it. Bridging it would draw a bed straight across the junction.
        """
        left = rail(0.0, 100.0, 0.0, step=2.0)
        right = rail(0.0, 100.0, GAUGE_M, step=2.0)
        swung = (right[:, 0] >= 40.0) & (right[:, 0] <= 60.0)
        right[swung, 2] = 4.0

        runs, rejected, _ = _track_centres(left, right, spec)

        assert len(runs) == 2
        assert rejected > 0

    def test_rails_with_different_station_counts_still_join(self, spec) -> None:
        """The two rails of a track are digitised independently — 28 stations
        against 26 on the first pair this region draws — so anything zipping
        them vertex-for-vertex shears across the four-foot."""
        left, right = rail(0.0, 100.0, 0.0, step=4.0), rail(0.0, 100.0, GAUGE_M, step=7.0)

        runs, _, _ = _track_centres(left, right, spec)

        assert len(runs) == 1
        spine, gauges = runs[0]
        # Sampled on `left`, so the two agree by construction. One station short
        # of the whole rail: `right`'s coarser step ends at 98, so `left`'s
        # station at 100 has no partner abreast of it and is correctly trimmed.
        assert len(spine) == len(gauges) == len(left) - 1
        assert np.allclose(spine[:, 2], GAUGE_M * 0.5, atol=1e-6)


class TestGaugeMetric:
    """⚠️ **What `drawn_gauge_m` can and cannot see**, pinned because the record
    got this wrong once: the metric was published as the detector for a
    mis-paired join, and the trim had already made that impossible."""

    def test_a_cross_track_pairing_yields_no_run_rather_than_a_wide_gauge(self, spec) -> None:
        """2.597 m is the measured separation between two *tracks* (`Q58`). Every
        station is outside the tolerance, so the trim rejects all of them —
        which surfaces as zero runs and as `off_gauge_stations`, never as a
        gauge reading 2.6 m, because a rejected station never reaches the gauge.
        """
        left, right = rail(0.0, 100.0, 0.0), rail(0.0, 100.0, 2.597)

        runs, rejected, tested = _track_centres(left, right, spec)

        assert runs == []
        assert rejected == tested > 0

    def test_every_reported_gauge_is_inside_the_tolerance_by_construction(self, spec) -> None:
        """Not a quality bar — an identity. It is here so the next person to
        read a healthy `drawn_gauge_m` knows it could not have read otherwise."""
        left, right = rail(0.0, 100.0, 0.0), rail(0.0, 100.0, GAUGE_M + 0.2)

        runs, _, _ = _track_centres(left, right, spec)

        for _, gauges in runs:
            assert np.all(np.abs(gauges - GAUGE_M) <= TOLERANCE_M)


class TestProjection:
    def test_a_point_past_the_end_clamps_to_it(self) -> None:
        """Clamping is what makes the trim above necessary, so it is pinned
        here rather than left as an implementation detail."""
        onto = rail(0.0, 10.0, 0.0)

        feet = _project(np.array([[20.0, 0.0, 0.0]]), onto)

        assert feet is not None
        assert feet[0][0] == pytest.approx(10.0)

    def test_a_degenerate_polyline_has_no_projection(self) -> None:
        onto = np.zeros((3, 3))

        assert _project(np.array([[1.0, 0.0, 1.0]]), onto) is None


class TestHeights:
    """Rails take the deck height of the road beside them, or are not drawn."""

    class _Segments:
        """The narrowest stand-in for `fares.Segments` this stage uses."""

        def __init__(self, y: float, distance_m: float) -> None:
            self._y, self._distance_m = y, distance_m

        def nearest(self, x: float, z: float):
            return type("Snap", (), {"y": self._y, "distance_m": self._distance_m})()

    def test_stations_land_on_the_deck_plus_the_lift(self) -> None:
        points = rail(0.0, 20.0, 0.0)

        lifted = _snap_heights(points, self._Segments(4.5, 3.0), 25.0, 0.02)

        assert lifted is not None
        assert np.allclose(lifted[:, 1], 4.52)
        assert np.allclose(lifted[:, [0, 2]], points[:, [0, 2]])

    def test_a_rail_with_no_road_near_it_is_dropped_whole(self) -> None:
        """Not partially: a tramway taking its height from a road at one end and
        guessing at the other is drawn on a slope the city does not have."""
        points = rail(0.0, 20.0, 0.0)

        assert _snap_heights(points, self._Segments(4.5, 99.0), 25.0, 0.02) is None


class TestBuilder:
    def test_a_strip_carries_the_contract_material(self) -> None:
        builder = _Builder()
        left, right = rail(0.0, 10.0, 0.0), rail(0.0, 10.0, 1.0)

        builder.strip(
            left,
            right,
            colour=(1, 2, 3),
            along_m=np.arange(len(left), dtype=float),
            surface_class=TRAMWAY_CLASS_RAIL,
        )
        mesh = builder.build("tramway")

        assert mesh is not None
        assert mesh.material == TRAMWAY_MATERIAL
        assert mesh.triangle_count == 2 * (len(left) - 1)
        # U is a fraction across rather than the lane coordinate the carriageway
        # uses — a rail has no lanes.
        assert set(np.unique(mesh.uvs[:, 0])) == {0.0, 1.0}

    def test_every_triangle_faces_up(self) -> None:
        """⚠️ **The defect that made a correct tramway invisible.**

        `tramway.gdshader` is `cull_back`, so winding — not the normal
        attribute — decides whether anything is drawn. `mitres` offsets to the
        *left* of travel, and feeding the strip left-then-right winds every
        triangle to face the ground: the first build of this module put
        **5,111 of 5,112** triangles face-down. The geometry was right, the
        position was right, the material was right, and the city simply had no
        tramway in it. No check saw it and no frame said why.
        """
        builder = _Builder()
        spine = rail(0.0, 20.0, 0.0)
        _draw(builder, spine, 2.2, (1, 2, 3), TRAMWAY_CLASS_BED)
        mesh = builder.build("tramway")

        assert mesh is not None
        inverted, area = downward_facing(mesh)
        assert inverted == 0, f"{inverted} of {mesh.triangle_count} triangles face the ground"
        assert area == 0.0

    def test_the_class_channel_rides_in_uv2(self) -> None:
        """The shader cannot tell a rail from a bed any other way, and getting
        it from strip width would invert the day the two widths converged."""
        builder = _Builder()
        spine = rail(0.0, 20.0, 0.0)
        _draw(builder, spine, 2.2, (1, 2, 3), TRAMWAY_CLASS_BED)
        _draw(builder, spine, 0.14, (4, 5, 6), TRAMWAY_CLASS_RAIL)
        mesh = builder.build("tramway")

        assert mesh is not None
        assert set(np.unique(mesh.uv2[:, 0])) == {TRAMWAY_CLASS_BED, TRAMWAY_CLASS_RAIL}
        # ⚠️ Metres along ride in `TEXCOORD_1.y`, **not** `TEXCOORD_0.y`: Godot
        # compresses UV0 and leaves UV2 alone, and a contract read off the
        # compressed copy reported this tramway starting at -0.009 m.
        assert mesh.uv2[:, 1].max() == pytest.approx(20.0)

    def test_nothing_drawn_is_no_mesh_rather_than_an_empty_one(self) -> None:
        """A city whose estate publishes no tramway ships none, and `export.py`
        writes a null asset. An empty mesh would ship a file and a draw call."""
        assert _Builder().build("tramway") is None


class TestConfig:
    """The block's own refusals, which are measurements rather than taste."""

    def test_a_tolerance_as_wide_as_the_gauge_is_refused(self, tmp_path) -> None:
        # At this width a rail pairs with the other *track's* near rail as
        # readily as with its own, and the bed is drawn across the four-foot of
        # neither.
        with pytest.raises(ValueError, match="pair_tolerance_m"):
            city_with(tmp_path, {**BLOCK, "pair_tolerance_m": GAUGE_M})

    def test_a_rail_wider_than_its_bed_is_refused(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="rail_width_m"):
            city_with(tmp_path, {**BLOCK, "rail_width_m": 3.0})

    def test_both_materials_are_resolved_through_the_table(self, tmp_path) -> None:
        """Names, not colours — hard rule 4, and the route by which
        `_check_every_material_is_used` counts them as referenced."""
        spec = city_with(tmp_path, BLOCK).tramway

        assert spec.rail_material.name == "kerb"
        assert spec.bed_material.name == "asphalt"

    def test_the_block_is_optional(self, tmp_path) -> None:
        """A city with no tramway in its estate declares none and builds as
        before — the same defaulted-is-the-contract rule as `podiums`."""
        assert city_with(tmp_path, None).tramway is None
