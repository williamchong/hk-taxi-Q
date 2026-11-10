"""`tools/traffic_census.py` — the traffic's hourly fleet and mix (`Q186`).

What is pinned: the fleet is a mean of the stations' SHAPES over its busiest hour,
not of their flows; the mix pools the stations' COUNTS, so a station that counted
twenty vehicles cannot outvote one that counted fifteen hundred; only the drawn
classes are kept and renormalised; the saloons split at `CAR_SPLIT`; an hour the
VCO never surveyed holds the nearest one; and an unsurveyed station reads as
None, never as zeros. And (`Q198`) the fleet is flow over SPEED: a hour that
crawls at half the fastest hour's speed holds twice its flow's cars; the speed is
a space mean, weighted by volume, skipping a lane that counted no car; and the
archive's minutes are picked a slot at a time, nearest the slot's middle first.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from traffic_census import (  # noqa: E402
    CAR_SPLIT,
    HOURS,
    KIND_CLASS,
    VCO_CLASSES,
    density_by_hour,
    fleet_by_hour,
    mix_by_hour,
    occupancy_by_hour,
    parse_detectors,
    pick_minutes,
    speed_by_hour,
    vco_counts,
    weekday_shape,
)


def _counts(**by_class: float) -> dict[str, float]:
    return {name: by_class.get(name.replace("/", "").replace(".", ""), 0.0) for name in VCO_CLASSES}


def test_fleet_is_a_mean_of_shapes_over_the_busiest_hour() -> None:
    flat = [100.0 / HOURS] * HOURS
    peaked = [0.0] * HOURS
    peaked[12] = 100.0
    fleet = fleet_by_hour([flat, peaked])
    assert fleet[12] == pytest.approx(1.0)
    assert max(fleet) == pytest.approx(1.0)
    # Each station counts once whatever its flow: the flat road's hours are
    # half its share over the peak hour's mean.
    assert fleet[3] == pytest.approx((100.0 / HOURS / 2) / ((100.0 / HOURS + 100.0) / 2))


def test_mix_pools_counts_keeps_drawn_classes_and_splits_saloons() -> None:
    big = _counts(PC=600.0, Taxi=300.0, LG=100.0, BDD=500.0, MC=50.0)
    small = _counts(Taxi=20.0)
    mix = mix_by_hour({8: [big, small]})
    # Buses and motorcycles drop out; the small station adds twenty taxis.
    total = 600.0 + 320.0 + 100.0
    assert mix["taxi"][8] == pytest.approx(100.0 * 320.0 / total)
    assert mix["van"][8] == pytest.approx(100.0 * 100.0 / total)
    assert mix["car_a"][8] == pytest.approx(100.0 * 600.0 / total * CAR_SPLIT["car_a"])
    assert mix["car_b"][8] == pytest.approx(100.0 * 600.0 / total * CAR_SPLIT["car_b"])
    assert sum(mix[kind][8] for kind in KIND_CLASS) == pytest.approx(100.0)


def test_unsurveyed_hours_hold_the_nearest() -> None:
    mix = mix_by_hour({7: [_counts(Taxi=1.0)], 22: [_counts(PC=1.0)]})
    assert mix["taxi"][0] == pytest.approx(100.0)
    assert mix["taxi"][14] == pytest.approx(100.0)  # seven hours from 07, eight from 22
    assert mix["car_a"][23] == pytest.approx(100.0 * CAR_SPLIT["car_a"])
    assert all(len(v) == HOURS for v in mix.values())


def test_an_hour_with_no_drawn_vehicle_is_refused() -> None:
    with pytest.raises(ValueError, match="no drawn vehicle"):
        mix_by_hour({9: [_counts(BDD=40.0)]})


def _analysis(vco_row: list[str]) -> dict:
    return {
        "Info": {"station": "Core Station 9999"},
        "Hourly_Var": {
            "linelabels": ["Sat", "Sun", "M-F", "All"],
            "data": [["0"] * HOURS, ["0"] * HOURS, [str(h) for h in range(HOURS)], ["0"] * HOURS],
        },
        "VCO": {
            "ylabels": list(VCO_CLASSES),
            "linelabels": ["Pro", "Ocp", "Veh", "Pass."],
            "data": [["0"] * 10, ["0"] * 10, vco_row, ["0"] * 10],
        },
    }


def test_reads_the_weekday_row_and_the_vehicle_counts() -> None:
    analysis = _analysis(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
    assert weekday_shape(analysis) == [float(h) for h in range(HOURS)]
    assert vco_counts(analysis) == {name: float(i + 1) for i, name in enumerate(VCO_CLASSES)}


def test_an_unsurveyed_station_reads_none() -> None:
    assert vco_counts(_analysis(["-"] * 10)) is None


def test_the_stations_are_the_citys_not_the_tools() -> None:
    # Hard rule 3: TD's station numbers are a Hong Kong fact, read off
    # `hong_kong.yaml`'s `traffic_census:` block, never a second copy here.
    from pipeline.config import load_config

    stations = load_config().census_stations
    assert stations == ("1002", "1020", "1024", "1028", "1029", "1107", "2214")
    assert all(isinstance(station, str) for station in stations)


@pytest.mark.parametrize("body", [{"stations": "1002"}, {"stations": ["1002", "1002"]}, ["1002"]])
def test_a_station_list_that_is_not_one_is_refused(body) -> None:
    from pipeline.config import _census_stations

    with pytest.raises(ValueError):
        _census_stations(body, "traffic_census")


def test_the_fleet_is_flow_over_speed() -> None:
    flow = [1.0] * HOURS
    flow[3] = 0.25
    speed = [60.0] * HOURS
    speed[8] = 30.0  # rush hour: the same flow, at half the speed
    fleet = density_by_hour(flow, speed)
    assert fleet[8] == pytest.approx(1.0)
    assert fleet[12] == pytest.approx(0.5)
    assert fleet[3] == pytest.approx(0.125)


def test_speed_is_the_space_mean_and_skips_an_empty_lane() -> None:
    # Ten cars at 60 and ten at 20: the space mean is 20 / (10/60 + 10/20) = 30,
    # not the arithmetic 40. A lane that counted none reads speed 0 and is skipped.
    readings = {h: [[60.0, 5.0, 1.0]] for h in range(HOURS)}
    readings[8] = [[60.0, 5.0, 10.0], [20.0, 30.0, 10.0], [0.0, 0.0, 0.0]]
    speed = speed_by_hour(readings)
    assert speed[8] == pytest.approx(30.0)
    assert speed[0] == pytest.approx(60.0)


def test_an_hour_no_detector_counted_is_refused() -> None:
    readings = {h: [[60.0, 5.0, 1.0]] for h in range(HOURS)}
    readings[4] = [[0.0, 0.0, 0.0]]
    with pytest.raises(ValueError, match="04:00"):
        speed_by_hour(readings)


def test_occupancy_is_over_its_busiest_hour() -> None:
    readings = {h: [[60.0, 5.0, 1.0]] for h in range(HOURS)}
    readings[18] = [[30.0, 20.0, 1.0], [30.0, 10.0, 1.0]]
    occupancy = occupancy_by_hour(readings)
    assert occupancy[18] == pytest.approx(1.0)
    assert occupancy[0] == pytest.approx(5.0 / 15.0)


def test_minutes_are_picked_by_slot_nearest_its_middle_first() -> None:
    stamps = ["20261020-0800", "20261020-0804", "20261020-0806", "20261020-0831", "20261020-0959"]
    slots = pick_minutes(stamps, 2)
    # 08:00-08:30's middle is 08:15: 0806 first, then 0804, 0800.
    assert slots == [
        ["20261020-0806", "20261020-0804", "20261020-0800"],
        ["20261020-0831"],
        ["20261020-0959"],
    ]


def test_only_the_named_detectors_valid_lanes_are_read() -> None:
    xml = (
        b"<raw_speed_volume_list><periods><period><detectors>"
        b"<detector><detector_id>A</detector_id><lanes>"
        b"<lane><speed>40</speed><occupancy>12</occupancy><volume>7</volume><valid>Y</valid></lane>"
        b"<lane><speed>99</speed><occupancy>1</occupancy><volume>1</volume><valid>N</valid></lane>"
        b"</lanes></detector>"
        b"<detector><detector_id>B</detector_id><lanes>"
        b"<lane><speed>50</speed><occupancy>3</occupancy><volume>2</volume><valid>Y</valid></lane>"
        b"</lanes></detector>"
        b"</detectors></period></periods></raw_speed_volume_list>"
    )
    assert parse_detectors(xml, ["A"]) == [[40.0, 12.0, 7.0]]


def test_the_detectors_and_days_are_the_citys() -> None:
    from pipeline.config import load_config

    config = load_config()
    assert len(config.census_detectors) == 8
    assert config.census_detector_days and "20261019" not in config.census_detector_days


@pytest.mark.parametrize(
    "days", [["20261018"], ["2026-10-20"], ["2026111"], ["20261020", "20261020"], "20261020"]
)
def test_a_detector_day_that_is_not_a_weekday_is_refused(days) -> None:
    from pipeline.config import _census_days

    with pytest.raises(ValueError):
        _census_days({"detector_days": days}, "traffic_census")


def test_a_missing_hour_is_refused_by_name() -> None:
    readings = {h: [[60.0, 5.0, 1.0]] for h in range(HOURS)}
    readings[5] = []
    with pytest.raises(ValueError, match="05:00"):
        occupancy_by_hour(readings)


def test_a_slot_reads_its_cache_first_and_skips_a_404(tmp_path, monkeypatch) -> None:
    import json

    import traffic_census

    asked: list[str] = []
    xml = (
        b"<r><detector><detector_id>A</detector_id><lanes><lane><speed>40</speed>"
        b"<occupancy>9</occupancy><volume>3</volume><valid>Y</valid></lane></lanes></detector></r>"
    )

    def fake_get(url: str, timeout_s: float) -> bytes | None:
        asked.append(url[-13:])
        return None if url.endswith("0805") else xml

    monkeypatch.setattr(traffic_census, "DETECTOR_CACHE", tmp_path)
    monkeypatch.setattr(traffic_census, "_get", fake_get)
    # The nearest minute 404s; the next one is served and cached.
    assert traffic_census.fetch_minute(["20261020-0805", "20261020-0806"], ["A"], False) == (
        "20261020-0806",
        [[40.0, 9.0, 3.0]],
    )
    assert asked == ["20261020-0805", "20261020-0806"]
    # A second run reads the cache across the slot and asks nothing.
    asked.clear()
    assert traffic_census.fetch_minute(["20261020-0805", "20261020-0806"], ["A"], False)[0] == (
        "20261020-0806"
    )
    assert asked == []
    # The cache is keyed by the detectors as a set, not by their order.
    cached = json.loads((tmp_path / "20261020-0806.json").read_text())
    assert cached["detectors"] == ["A"]
    # --refresh goes to the network.
    traffic_census.fetch_minute(["20261020-0806"], ["A"], True)
    assert asked == ["20261020-0806"]
