"""`tools/traffic_census.py` — the traffic's hourly fleet and mix (`Q186`).

What is pinned: the fleet is a mean of the stations' SHAPES over its busiest hour,
not of their flows; the mix pools the stations' COUNTS, so a station that counted
twenty vehicles cannot outvote one that counted fifteen hundred; only the drawn
classes are kept and renormalised; the saloons split at `CAR_SPLIT`; an hour the
VCO never surveyed holds the nearest one; and an unsurveyed station reads as
None, never as zeros.
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
    fleet_by_hour,
    mix_by_hour,
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
