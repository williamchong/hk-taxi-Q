"""Derive the moving traffic's hourly fleet and mix from TD's census (`Q186`).

The third hand-run tool that *produces* tuning rather than grading a build
(after `ring_weights.py` and the sound scripts). It reads TD's *Annual Traffic
Census* through the census's own interactive site (https://atc.td.gov.hk/), the
same `POST /api/analysis` the site's AADT Analysis page makes, for the counting
stations inside Wan Chai and Causeway Bay, and prints `traffic.tres`' two
hourly tables:

- **`fleet_by_hour`** — each station's weekday (`M-F`) hourly share of its day,
  averaged over the stations with each station counted once, then divided by the
  busiest hour: the share of `cars` alive at each clock hour. A mean of shapes,
  not of flows, so Gloucester Road's 120,000 a day does not drown Tung Lo Wan
  Road's 16,000 — the taxi drives the side streets too.
- **`kinds`** — the vehicle classification surveys (VCO) at the stations that
  have one, POOLED BY VEHICLE COUNT per hour (the `Veh` row): a station that
  counted 20 vehicles in an hour does not move the mix as far as one that counted
  1,500. Only the classes the traffic draws are kept — private car, taxi, public
  light bus, light goods — and renormalised to 100; private cars are split
  between the library's two saloons at `CAR_SPLIT`, which is authored. The VCO
  covers 07:00-23:00 only; outside it each kind holds its nearest surveyed hour.

The census is build-time data like every other source: this runs by hand, and
the game reads only the numbers it prints into `traffic.tres` (hard rule 2).
Responses are cached under `build/census/`, which is gitignored.

Run:  .venv/bin/python tools/traffic_census.py [--refresh]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.config import load_config  # noqa: E402
from pipeline.fetch import _USER_AGENT  # noqa: E402

CACHE = ROOT / "build" / "census"
API = "https://atc.td.gov.hk/api/analysis"
# The counting stations are a Hong Kong fact, so they live in `hong_kong.yaml`'s
# `traffic_census:` block (hard rule 3), read through `load_config`.

# The VCO's ten classes, in the API's order (`VCO.ylabels`).
VCO_CLASSES: tuple[str, ...] = (
    "M/C",
    "P/C",
    "Taxi",
    "Priv.LB",
    "PLB",
    "L/G",
    "H/G",
    "Coach",
    "B/SD",
    "B/DD",
)
# What each kind the traffic draws is, as a VCO class. Motorcycles have no mesh;
# heavy goods and coaches are too long for the turn curve a wandering car takes;
# buses run on their routes (`P3-78`); a private light bus is not a red minibus.
KIND_CLASS: dict[str, str] = {
    "car_a": "P/C",
    "car_b": "P/C",
    "taxi": "Taxi",
    "minibus": "PLB",
    "van": "L/G",
}
# How the private cars split between the library's two saloons: the 4 : 3 the
# shipped `kinds` drew them at. Authored — the census has one class for both.
CAR_SPLIT: dict[str, float] = {"car_a": 4.0 / 7.0, "car_b": 3.0 / 7.0}
# The VCO's hours: `req_vco_time` t is the hour from t - 1 to t.
VCO_HOURS: range = range(7, 23)
HOURS = 24


def fetch(station: str, vco_hour: int, refresh: bool) -> dict:
    """One station's analysis with the VCO of the hour from `vco_hour`, cached."""
    path = CACHE / f"{station}_{vco_hour:02d}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    body = json.dumps(
        {
            "req_station": station,
            "req_month": "0",
            "req_direction": 0,
            "req_vco_date": "Wed",
            "req_vco_time": str(vco_hour + 1),
        }
    ).encode()
    request = Request(
        API,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT},
    )
    with urlopen(request, timeout=60) as response:
        data = json.load(response)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def weekday_shape(analysis: dict) -> list[float]:
    """A station's weekday share of its day, in percent, by clock hour."""
    var = analysis["Hourly_Var"]
    row = var["data"][var["linelabels"].index("M-F")]
    if len(row) != HOURS:
        raise ValueError(f"{analysis['Info']['station']}: {len(row)} hours, not {HOURS}")
    return [float(v) for v in row]


def vco_counts(analysis: dict) -> dict[str, float] | None:
    """Vehicles counted by class in the analysis's VCO hour; None where unsurveyed."""
    vco = analysis["VCO"]
    if list(vco["ylabels"]) != list(VCO_CLASSES):
        raise ValueError(f"VCO classes moved: {vco['ylabels']}")
    row = vco["data"][vco["linelabels"].index("Veh")]
    if any(v == "-" for v in row):
        return None
    return {name: float(v) for name, v in zip(VCO_CLASSES, row, strict=True)}


def fleet_by_hour(shapes: Sequence[Sequence[float]]) -> list[float]:
    """The mean of the stations' shapes, over its busiest hour."""
    if not shapes:
        raise ValueError("no station shapes")
    mean = [sum(s[h] for s in shapes) / len(shapes) for h in range(HOURS)]
    peak = max(mean)
    return [m / peak for m in mean]


def mix_by_hour(counts: dict[int, Sequence[dict[str, float]]]) -> dict[str, list[float]]:
    """Each kind's percent of the drawn vehicles by clock hour.

    `counts` maps a surveyed hour to the stations' class counts in it; they are
    pooled, kept to the drawn classes, renormalised, and the saloons split.
    Hours with no survey hold the nearest surveyed one.
    """
    if not counts:
        raise ValueError("no VCO hours")
    surveyed: dict[int, dict[str, float]] = {}
    drawn = sorted(set(KIND_CLASS.values()))
    for hour, stations in counts.items():
        pooled = {name: sum(s[name] for s in stations) for name in drawn}
        total = sum(pooled.values())
        if total <= 0.0:
            raise ValueError(f"{hour:02d}:00 counted no drawn vehicle")
        surveyed[hour] = {name: 100.0 * v / total for name, v in pooled.items()}
    mix: dict[str, list[float]] = {kind: [] for kind in KIND_CLASS}
    for hour in range(HOURS):
        nearest = min(surveyed, key=lambda h: (abs(h - hour), h))
        for kind, name in KIND_CLASS.items():
            mix[kind].append(surveyed[nearest][name] * CAR_SPLIT.get(kind, 1.0))
    return mix


def _packed(values: Sequence[float], digits: int) -> str:
    return "PackedFloat32Array(" + ", ".join(f"{v:.{digits}f}" for v in values) + ")"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="refetch, ignoring the cache")
    args = parser.parse_args(argv)

    shapes: list[list[float]] = []
    counts: dict[int, list[dict[str, float]]] = {}
    vehicles: dict[int, float] = {}
    stations = load_config().census_stations
    if not stations:
        parser.error("hong_kong.yaml's traffic_census block names no station")
    for station in stations:
        first = fetch(station, VCO_HOURS[0], args.refresh)
        info = first["Info"]
        shapes.append(weekday_shape(first))
        surveyed = vco_counts(first) is not None
        print(
            f"# {station} {info['link']} ({info['type']}), AADT {info['aadt_annual']}"
            f"{', VCO' if surveyed else ''}"
        )
        if not surveyed:
            continue
        for hour in VCO_HOURS:
            analysis = first if hour == VCO_HOURS[0] else fetch(station, hour, args.refresh)
            row = vco_counts(analysis)
            if row is None:
                raise ValueError(f"{station} has no VCO at {hour:02d}:00")
            counts.setdefault(hour, []).append(row)
            vehicles[hour] = vehicles.get(hour, 0.0) + sum(row.values())

    fleet = fleet_by_hour(shapes)
    mix = mix_by_hour(counts)
    print(f"# vehicles classified per hour, all classes: {[int(vehicles[h]) for h in VCO_HOURS]}")
    print()
    print("| hour | fleet | " + " | ".join(KIND_CLASS) + " |")
    print("|---|---|" + "---|" * len(KIND_CLASS))
    for hour in range(HOURS):
        cells = " | ".join(f"{mix[kind][hour]:.1f}" for kind in KIND_CLASS)
        print(f"| {hour:02d} | {fleet[hour]:.2f} | {cells} |")
    print()
    print("fleet_by_hour = " + _packed(fleet, 3))
    print("kinds = Dictionary[String, PackedFloat32Array]({")
    lines = [f'"{kind}": {_packed(mix[kind], 2)}' for kind in sorted(KIND_CLASS)]
    print(",\n".join(lines))
    print("})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
