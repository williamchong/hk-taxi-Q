"""`pipeline/parked.py` — the parked roster (`P3-71`, `Q161`).

⚠️ **Every failure this stage has renders as a perfectly parked car.** A car
facing against its kerb's flow, a van standing in the lane, a fill that
ignores a double yellow, a bay refused for a bar meant for the fill — each is
a plausible street. So what is asserted is the arithmetic nothing downstream
can see: the side and the flow, the lateral stand, the windows from both
sides, the refusals in their order and the partition they close, and the
fill's determinism — the same inputs place the same cars, so a battery diff
moves only on a real change.
"""

from __future__ import annotations

import copy
import math
from types import MappingProxyType
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import ALWAYS, SOURCE_BAY, SOURCE_FILL, SOURCE_STAND, load_config
from pipeline.drawnroad import ribbons
from pipeline.parked import (
    Candidate,
    ParkedReport,
    _complement,
    _fill_candidates,
    _flow_heading,
    _footprint,
    _layby_candidates,
    _on_track,
    _stand,
    _Street,
    in_window,
)
from tests.helpers import CITY_YAML
from tests.test_surface import _edge

BLOCK: dict[str, Any] = {
    "library": "res://assets/authored/vehicles/parked.glb",
    "vehicles": {
        "car": {"length_m": 4.5, "width_m": 1.8, "meshes": ["car_a", "car_b"]},
        "van": {"length_m": 4.7, "width_m": 1.8},
        "bus": {"length_m": 12.0, "width_m": 2.5},
        "taxi": {"length_m": 4.7, "width_m": 1.7},
        "tram": {"length_m": 8.6, "width_m": 2.0},
        "motorcycle": {"length_m": 2.1, "width_m": 0.8, "gap_m": 0.2, "across": True},
    },
    "stops": [
        {
            "source": "bus_stops",
            "crs": "EPSG:4326",
            "kind": "bus",
            "chance": 0.35,
            "max_snap_m": 12.0,
        }
    ],
    "stands": {"taxi_stand": {"kind": "taxi", "queue": 2, "pitch_m": 6.5}, "poi": {"kind": "tram"}},
    "frontage": {
        "classes": {
            "hotel": {"match": ["Hotel"], "kinds": ["taxi"]},
            "office": {"match": ["Centre", "Tower"], "kinds": ["van"], "hours": [8, 19]},
        },
        "max_distance_m": 15.0,
        "pitch_m": 14.0,
    },
    "fill": {
        "share": 0.5,
        "pitch_m": 7.0,
        "kinds": {"car": 0.8, "van": 0.2},
        "single_yellow_hours": [7, 19],
        "hours_by_kind": {"van": [8, 19]},
    },
    "laybys": {
        "min_bulge_m": 1.8,
        "max_bulge_m": 4.0,
        "min_run_m": 8.0,
        "max_run_m": 90.0,
        "pitch_m": 7.0,
        "kinds": {"car": 0.7, "taxi": 0.3},
        "chance": 0.6,
    },
    "tram_max_track_m": 12.0,
    "slow_streets": {
        "street_classes": ["minor"],
        "max_speed_kph": 50,
        "bus_lane": False,
        "min_lanes": 2,
        "on_structure": False,
    },
    "clearances": {
        "kerb_gap_m": 0.25,
        "junction_m": 10.0,
        "fare_m": 25.0,
        "crossing_m": 5.0,
        "gap_m": 0.4,
        "lane_width_m": 3.0,
        "row_lanes": 1,
    },
}


def city_with(tmp_path, block: dict[str, Any] | None):
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["parked"] = block
    path = tmp_path / "testville.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return load_config(path)


def mutated(tmp_path, mutate):
    block = copy.deepcopy(BLOCK)
    mutate(block)
    return city_with(tmp_path, block)


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).parked


# A straight 200 m two-way street running north, 12 m kerb to kerb (two
# lanes and room to park both sides), and a one-way one beside it.
def _graph(direction: str = "both", width_m: float = 12.0, lanes: int = 2, **more) -> dict:
    return {
        "edges": [
            _edge(
                7,
                0,
                1,
                [[0.0, 0.0, 0.0], [0.0, 0.0, -200.0]],
                direction=direction,
                width_m=width_m,
                lanes=lanes,
                kerbside=[],
                **({"street_class": "minor", "speed_limit_kph": 50, "bus_lane": False} | more),
            )
        ]
    }


def _surface(half_width_m: float = 6.0, **row) -> dict:
    return {
        "carriageway": [
            {
                "edge": 7,
                "half_width_m": [half_width_m, half_width_m],
                "offset_m": [0.0, 0.0],
                "trim_m": [0.0, 0.0],
            }
            | row
        ]
    }


def _street(graph: dict, surface: dict) -> _Street:
    return _Street(graph, surface, ribbons(graph, surface))


def _candidate(kind: str, t: float, side: float, source: str = SOURCE_BAY, **more) -> Candidate:
    return Candidate(kind, source, 7, t, side, ALWAYS, 1.0, **more)


class TestTheWindow:
    """`in_window` is restated in `parked_roster.gd`; both sides of every bar."""

    def test_no_window_is_always(self) -> None:
        assert in_window(3.0, ALWAYS)

    def test_a_day_window_includes_its_start_and_excludes_its_end(self) -> None:
        assert in_window(8.0, (8.0, 19.0))
        assert in_window(18.99, (8.0, 19.0))
        assert not in_window(19.0, (8.0, 19.0))
        assert not in_window(7.99, (8.0, 19.0))

    def test_a_night_window_wraps_midnight(self) -> None:
        night = _complement((7.0, 19.0))
        assert night == (19.0, 7.0)
        assert in_window(23.0, night) and in_window(0.0, night) and in_window(3.0, night)
        assert not in_window(12.0, night)


class TestTheSideAndTheFlow:
    """🔴 The trap: a car facing against its kerb's flow is a perfectly drawn car."""

    def test_the_nearside_faces_with_the_edge(self) -> None:
        street = _street(_graph(), _surface())
        assert _flow_heading(street, 7, 0.5, 1.0) == pytest.approx(0.0)

    def test_the_offside_of_a_two_way_edge_faces_against_it(self) -> None:
        street = _street(_graph(), _surface())
        assert _flow_heading(street, 7, 0.5, -1.0) == pytest.approx(180.0)

    def test_both_kerbs_of_a_one_way_street_face_the_way_it_runs(self) -> None:
        street = _street(_graph(direction="forward"), _surface())
        assert _flow_heading(street, 7, 0.5, -1.0) == pytest.approx(0.0)

    def test_a_motorcycle_stands_nose_to_its_kerb(self, spec) -> None:
        street = _street(_graph(), _surface())
        near = _stand(street, spec, _candidate("motorcycle", 0.5, 1.0))
        off = _stand(street, spec, _candidate("motorcycle", 0.5, -1.0))
        assert not isinstance(near, str) and not isinstance(off, str)
        # The nearside is west of a northbound edge: nose west (270), and the
        # offside nose east (90).
        assert near.rot_y_deg == pytest.approx(270.0)
        assert off.rot_y_deg == pytest.approx(90.0)


class TestWhereItStands:
    def test_a_car_stands_kerb_gap_off_the_kerb_on_its_side(self, spec) -> None:
        street = _street(_graph(), _surface(half_width_m=6.0))
        stood = _stand(street, spec, _candidate("car", 0.5, 1.0))
        assert not isinstance(stood, str)
        # Nearside of a northbound edge is -x; the kerb at 6 m, the gap 0.25,
        # half a car 0.9: the centre is 4.85 m out.
        assert stood.x == pytest.approx(-(6.0 - 0.25 - 0.9))
        assert stood.z == pytest.approx(-100.0)
        low, high = stood.footprint.bounds[0], stood.footprint.bounds[2]
        assert low == pytest.approx(-5.75) and high == pytest.approx(-3.95)

    def test_a_motorcycle_takes_its_length_off_the_road(self, spec) -> None:
        street = _street(_graph(), _surface(half_width_m=6.0))
        stood = _stand(street, spec, _candidate("motorcycle", 0.5, 1.0))
        assert not isinstance(stood, str)
        assert stood.x == pytest.approx(-(6.0 - 0.25 - 1.05))

    def test_the_footprint_is_the_vehicle_turned_to_its_bearing(self) -> None:
        box = _footprint(10.0, 20.0, 90.0, 4.0, 2.0)
        minx, minz, maxx, maxz = box.bounds
        # Nose east: four metres along x, two across z.
        assert (maxx - minx, maxz - minz) == pytest.approx((4.0, 2.0))
        assert box.centroid.x == pytest.approx(10.0) and box.centroid.y == pytest.approx(20.0)


class TestTheRefusals:
    def test_a_fill_slot_inside_the_junction_setback_is_refused(self, spec) -> None:
        street = _street(_graph(), _surface())
        # 5 m from the start: inside junction_m (10) plus half a car.
        assert _stand(street, spec, _candidate("car", 0.025, 1.0, SOURCE_FILL)) == "at_junction"
        assert not isinstance(_stand(street, spec, _candidate("car", 0.1, 1.0, SOURCE_FILL)), str)

    def test_a_published_bay_stands_where_the_fill_may_not(self, spec) -> None:
        """A bay is where the publisher put it: only the trim refuses it."""
        street = _street(_graph(), _surface())
        assert not isinstance(_stand(street, spec, _candidate("car", 0.025, 1.0)), str)

    def test_the_trim_refuses_a_bay_too(self, spec) -> None:
        street = _street(_graph(), _surface(trim_m=[20.0, 0.0]))
        assert _stand(street, spec, _candidate("car", 0.05, 1.0)) == "at_junction"

    def test_a_narrow_road_refuses_the_fill_and_counts_the_bay(self, spec) -> None:
        # 4.5 m kerb to kerb, two lanes: a row keeps one 3.0 m lane, and a
        # car plus its gap leaves 2.45 — less.
        street = _street(_graph(width_m=4.5), _surface(half_width_m=2.25))
        assert _stand(street, spec, _candidate("car", 0.5, 1.0, SOURCE_FILL)) == "too_narrow"
        bay = _stand(street, spec, _candidate("car", 0.5, 1.0))
        assert not isinstance(bay, str) and bay.lane_room_m < 0.0

    def test_a_row_keeps_one_lane_fewer_than_authored(self, spec) -> None:
        """Hong Kong's 6.4 m two-way back street: two lanes authored, one row
        parked, one lane left to pass in."""
        street = _street(_graph(width_m=6.4), _surface(half_width_m=3.2))
        one = _stand(street, spec, _candidate("car", 0.5, 1.0, SOURCE_FILL, rows=1))
        assert not isinstance(one, str) and one.lane_room_m == pytest.approx(6.4 - 2.05 - 3.0)
        # A second row prices the first's width too: 6.4 - 4.1 - 3.0 < 0.
        two = _stand(street, spec, _candidate("car", 0.5, 1.0, SOURCE_FILL, rows=2))
        assert two == "too_narrow"

    def test_a_hidden_kerb_stands_nothing(self, spec) -> None:
        street = _street(_graph(), _surface(kerb_hidden_m={"near": [[90.0, 110.0]], "off": []}))
        assert _stand(street, spec, _candidate("car", 0.5, 1.0)) == "kerb_hidden"
        assert not isinstance(_stand(street, spec, _candidate("car", 0.5, -1.0)), str)

    def test_a_tram_stands_on_its_bed_and_skips_the_kerb_rules(self, spec) -> None:
        street = _street(_graph(width_m=7.0), _surface(half_width_m=3.5))
        on_bed = _candidate(
            "tram", 0.5, 1.0, SOURCE_STAND, heading_deg=0.0, plan=(0.0, -100.0), height_m=3.0
        )
        stood = _stand(street, spec, on_bed)
        assert not isinstance(stood, str)
        assert (stood.x, stood.y, stood.z) == (0.0, 3.0, -100.0)


class TestTheFill:
    def _spec_with_runs(self, spec, runs: list[dict]) -> tuple[_Street, Any]:
        graph = _graph()
        graph["edges"][0]["kerbside"] = runs
        return _street(graph, _surface()), spec

    def test_the_fill_is_deterministic(self, spec) -> None:
        street = _street(_graph(), _surface())
        first = _fill_candidates(street, spec, ParkedReport())
        second = _fill_candidates(street, spec, ParkedReport())
        assert first == second
        assert first, "the fixture street fills"

    def test_the_fill_keeps_its_share_evenly(self, spec) -> None:
        street = _street(_graph(), _surface())
        report = ParkedReport()
        kept = _fill_candidates(street, spec, report)
        assert report.fill_slots == 2 * int(200.0 // 7.0)
        assert abs(len(kept) - 0.5 * report.fill_slots) <= 2
        # Evenly: every other slot on each kerb, never two in a row.
        near = sorted(candidate.t for candidate in kept if candidate.side > 0.0)
        gaps = {round((b - a) * 200.0 / 7.0) for a, b in zip(near, near[1:], strict=False)}
        assert gaps == {2}

    def test_a_narrow_two_way_street_fills_its_nearside_only(self, spec) -> None:
        """6.4 m, two lanes: one row keeps a lane, two would not."""
        street = _street(_graph(width_m=6.4), _surface(half_width_m=3.2))
        kept = _fill_candidates(street, spec, ParkedReport())
        assert kept and all(candidate.side > 0.0 and candidate.rows == 1 for candidate in kept)
        wide = _fill_candidates(_street(_graph(), _surface()), spec, ParkedReport())
        assert any(candidate.side < 0.0 for candidate in wide)
        assert all(candidate.rows == 2 for candidate in wide)

    def test_a_double_yellow_takes_its_kerb_out_of_the_fill(self, spec) -> None:
        street, _ = self._spec_with_runs(
            spec, [{"side": "near", "from_m": 0.0, "to_m": 200.0, "kind": "double"}]
        )
        kept = _fill_candidates(street, spec, ParkedReport())
        assert kept and all(candidate.side < 0.0 for candidate in kept)

    def test_a_single_yellow_fills_outside_the_posted_hours_only(self, spec) -> None:
        street, _ = self._spec_with_runs(
            spec, [{"side": "near", "from_m": 0.0, "to_m": 200.0, "kind": "single"}]
        )
        report = ParkedReport()
        kept = _fill_candidates(street, spec, report)
        near = [candidate for candidate in kept if candidate.side > 0.0]
        assert near and report.fill_night_only == len(near)
        assert all(candidate.hours == (19.0, 7.0) for candidate in near)
        # And never a van: a kind with hours of its own does not take the night.
        assert all(candidate.kind == "car" for candidate in near)

    @pytest.mark.parametrize(
        "fast",
        [
            {"street_class": "main"},
            {"speed_limit_kph": 70},
            {"bus_lane": True},
            {"street_class": None},
            {"lanes": 1},
            {"on_structure": [False, True]},
        ],
    )
    def test_the_fill_never_draws_a_slot_on_a_fast_street(self, spec, fast) -> None:
        """The user's drive: cars do not park in fast lanes, on a bridge, or on
        a one-lane road. A main road, a 70 km/h limit, a bus lane, an
        unclassified edge, one lane and a structure each stand no fill."""
        street = _street(_graph(**fast), _surface())
        report = ParkedReport()
        assert _fill_candidates(street, spec, report) == []
        assert report.fill_slots == 0

    def test_a_one_way_street_fills_its_nearside_only(self, spec) -> None:
        """The offside of a one-way street is the fast lane (the user's drive)."""
        street = _street(_graph(direction="forward"), _surface())
        kept = _fill_candidates(street, spec, ParkedReport())
        assert kept and all(candidate.side > 0.0 for candidate in kept)
        both = _fill_candidates(_street(_graph(), _surface()), spec, ParkedReport())
        assert any(candidate.side < 0.0 for candidate in both)

    def test_a_van_keeps_its_own_hours_on_a_free_kerb(self, spec) -> None:
        street = _street(_graph(), _surface())
        kept = _fill_candidates(street, spec, ParkedReport())
        vans = [candidate for candidate in kept if candidate.kind == "van"]
        assert vans and all(candidate.hours == (8.0, 19.0) for candidate in vans)


class TestTheLayby:
    """A run of kerb a parking lane proud of the street's own kerb."""

    def _region(self, bulge_m: float, run: tuple[float, float]) -> dict:
        at = np.linspace(0.0, 1.0, 41)
        left = np.full(41, 6.0)
        along = at * 200.0
        left[(along >= run[0]) & (along <= run[1])] += bulge_m
        # `carriageway_region.json`'s own shape (`test_drawnroad.py`'s `ROAD`):
        # dense stations, every one ending at a kerb on both sides.
        return {
            "territories": [
                {
                    "edge": 7,
                    "foreign": False,
                    "along_m": along.tolist(),
                    "left_m": left.tolist(),
                    "right_m": [6.0] * 41,
                    "left_end": ["kerb"] * 41,
                    "right_end": ["kerb"] * 41,
                    "left_kerb_m": left.tolist(),
                    "right_kerb_m": [6.0] * 41,
                }
            ]
        }

    def _street_with(self, bulge_m: float, run: tuple[float, float], **edge) -> _Street:
        graph = _graph(**edge)
        surface = _surface()
        return _Street(graph, surface, ribbons(graph, surface, self._region(bulge_m, run)))

    def test_a_widening_stands_cars_whatever_the_street(self, spec) -> None:
        street = self._street_with(2.5, (80.0, 120.0), street_class="main", speed_limit_kph=70)
        report = ParkedReport()
        kept = _layby_candidates(street, spec, report)
        assert report.layby_runs == 1 and 35.0 <= report.layby_m <= 45.0
        assert len(kept) == 5 and all(c.side > 0.0 and c.source == "layby" for c in kept)
        assert all(80.0 < c.t * 200.0 < 120.0 for c in kept)
        stood = _stand(street, spec, kept[0])
        assert not isinstance(stood, str)
        # In the bulge: 2.5 m further out than the street's own kerb.
        assert stood.x == pytest.approx(-(8.5 - 0.25 - 0.9))

    def test_a_flare_or_a_short_notch_is_not_a_layby(self, spec) -> None:
        assert _layby_candidates(self._street_with(6.0, (80.0, 120.0)), spec, ParkedReport()) == []
        assert _layby_candidates(self._street_with(2.5, (80.0, 85.0)), spec, ParkedReport()) == []
        assert _layby_candidates(self._street_with(1.0, (80.0, 120.0)), spec, ParkedReport()) == []

    def test_a_widening_that_reaches_the_edge_end_is_a_flare(self, spec) -> None:
        """A run touching the trim is the junction opening, not a lay-by."""
        assert _layby_candidates(self._street_with(2.5, (160.0, 200.0)), spec, ParkedReport()) == []
        assert _layby_candidates(self._street_with(2.5, (0.0, 40.0)), spec, ParkedReport()) == []

    def test_a_missing_speed_limit_is_a_fast_street(self, spec) -> None:
        edge = _graph()["edges"][0]
        del edge["speed_limit_kph"]
        assert not spec.slow_streets.allows(edge)


class TestOnTheTrack:
    def test_a_fraction_along_a_bed_gives_its_point_and_bearing(self) -> None:
        bed = np.array([[0.0, 3.0, 0.0], [0.0, 3.0, -100.0], [50.0, 3.0, -100.0]])
        x, y, z, bearing = _on_track(bed, 0.25)
        assert (x, y, z) == pytest.approx((0.0, 3.0, -37.5))
        assert bearing == pytest.approx(0.0)
        x, y, z, bearing = _on_track(bed, 0.8)
        assert (x, z) == pytest.approx((20.0, -100.0))
        assert bearing == pytest.approx(90.0)


class TestTheBlock:
    """The loader refuses what the stage could not place honestly."""

    def test_the_real_city_loads(self) -> None:
        city = load_config()
        assert city.parked is not None
        assert city.parked.frontage is not None
        assert city.parked.frontage.class_of("Grand Hyatt Hotel").id == "hotel"
        assert city.parked.frontage.class_of("Caine House") is None

    def test_absent_is_none(self, tmp_path) -> None:
        assert city_with(tmp_path, None).parked is None

    def test_a_kind_outside_the_roster_is_refused(self, tmp_path) -> None:
        def mutate(block):
            block["vehicles"]["lorry"] = {"length_m": 9.0, "width_m": 2.5}

        with pytest.raises(ValueError, match="not in the roster"):
            mutated(tmp_path, mutate)

    def test_a_placed_kind_the_vehicles_do_not_size_is_refused(self, tmp_path) -> None:
        def mutate(block):
            block["stops"][0]["kind"] = "coach"

        with pytest.raises(ValueError, match="does not size"):
            mutated(tmp_path, mutate)

    def test_a_shadowed_frontage_token_is_refused(self, tmp_path) -> None:
        def mutate(block):
            block["frontage"]["classes"]["grand"] = {"match": ["Grand Hotel"], "kinds": ["taxi"]}

        with pytest.raises(ValueError, match="shadowed"):
            mutated(tmp_path, mutate)

    def test_a_share_over_one_is_refused(self, tmp_path) -> None:
        def mutate(block):
            block["fill"]["share"] = 1.5

        with pytest.raises(ValueError, match="share"):
            mutated(tmp_path, mutate)

    def test_an_empty_window_is_refused(self, tmp_path) -> None:
        def mutate(block):
            block["fill"]["single_yellow_hours"] = [7, 7]

        with pytest.raises(ValueError, match="empty window"):
            mutated(tmp_path, mutate)

    def test_a_queue_needs_a_pitch(self, tmp_path) -> None:
        def mutate(block):
            block["stands"]["taxi_stand"]["pitch_m"] = 0.0

        with pytest.raises(ValueError, match="pitch_m"):
            mutated(tmp_path, mutate)

    def test_a_kind_defaults_to_its_own_mesh(self, spec) -> None:
        assert spec.vehicle("van").library_meshes == ("van",)
        assert spec.vehicle("car").library_meshes == ("car_a", "car_b")

    def test_the_read_only_view_of_kinds(self, spec) -> None:
        assert MappingProxyType(spec.fill.kinds)["car"] == 0.8
        assert math.isclose(sum(spec.fill.kinds.values()), 1.0)
