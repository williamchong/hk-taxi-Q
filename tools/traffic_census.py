"""Derive the moving traffic's hourly fleet and mix from TD's census (`Q186`).

The third hand-run tool that *produces* tuning rather than grading a build
(after `ring_weights.py` and the sound scripts). It reads TD's *Annual Traffic
Census* through the census's own interactive site (https://atc.td.gov.hk/), the
same `POST /api/analysis` the site's AADT Analysis page makes, for the counting
stations inside Wan Chai and Causeway Bay, and prints `traffic.tres`' two
hourly tables:

- **`fleet_by_hour`** — the cars on the street at once, which is FLOW OVER SPEED
  (`Q198`). The flow is each station's weekday (`M-F`) hourly share of its day,
  averaged over the stations with each station counted once: a mean of shapes,
  not of flows, so Gloucester Road's 120,000 a day does not drown Tung Lo Wan
  Road's 16,000 — the taxi drives the side streets too. The speed is TD's traffic
  detectors inside the regions, read off DATA.GOV.HK's historical archive of
  `rawSpeedVol-all.xml` on the configured weekdays, `MINUTES_PER_HOUR` minutes an
  hour: the space-mean speed of each hour over the fastest hour's. Flow over that,
  divided by the busiest hour, is the share of `cars` alive at each clock hour.
  A flow saturates in a jam while the street fills, so the flow alone (`Q186`)
  read rush hour as noon. The detectors' mean occupancy is printed beside it, an
  independent reading of the same density.
- **`kinds`** — the vehicle classification surveys (VCO) at the stations that
  have one, POOLED BY VEHICLE COUNT per hour (the `Veh` row): a station that
  counted 20 vehicles in an hour does not move the mix as far as one that counted
  1,500. Only the classes the traffic draws are kept — private car, taxi, public
  light bus, light goods — and renormalised to 100; private cars are split
  between the library's two saloons at `CAR_SPLIT`, which is authored. The VCO
  covers 07:00-23:00 only; outside it each kind holds its nearest surveyed hour.

The census is build-time data like every other source: this runs by hand, and
the game reads only the numbers it prints into `traffic.tres` (hard rule 2).
Responses are cached under `build/census/` and the detectors' readings, kept to
the configured detectors, under `build/detectors/`; both are gitignored.

Run:  .venv/bin/python tools/traffic_census.py [--refresh]
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.config import load_config  # noqa: E402
from pipeline.fetch import _USER_AGENT, _with_retries  # noqa: E402

CACHE = ROOT / "build" / "census"
API = "https://atc.td.gov.hk/api/analysis"
DETECTOR_CACHE = ROOT / "build" / "detectors"
# TD's raw detector feed, one file a minute, and DATA.GOV.HK's archive of it.
DETECTOR_FEED = "https://resource.data.one.gov.hk/td/traffic-detectors/rawSpeedVol-all.xml"
ARCHIVE = "https://api.data.gov.hk/v1/historical-archive"
# The archived minutes read in each clock hour, spread evenly through it.
MINUTES_PER_HOUR = 6
# Parallel archive requests: a courtesy bound, not a tuning value.
FETCH_WORKERS = 4
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


def _hour(stamp: str) -> int:
    """The clock hour of an archive version, `YYYYMMDD-HHMM`."""
    return int(stamp[9:11])


def _write_atomic(path: Path, text: str) -> None:
    """Write `text` whole or not at all, so a run cut off mid-write leaves no
    truncated cache entry for the next run to choke on."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    partial.write_text(text)
    partial.replace(path)


def _get(url: str, timeout_s: float) -> bytes | None:
    """`url`'s body, retried on a transient failure; None when the archive
    answers 404 — a version it lists but cannot serve, which no retry fixes."""

    def once() -> bytes | None:
        try:
            with urlopen(Request(url, headers={"User-Agent": _USER_AGENT}), timeout=timeout_s) as r:
                return r.read()
        except HTTPError as error:
            if error.code == 404:
                return None
            raise

    return _with_retries(once, f"read {url}")


def list_minutes(day: str, refresh: bool) -> list[str]:
    """The archive's file versions for `day`, as `YYYYMMDD-HHMM`, cached: the
    configured days are past, so their listing does not move."""
    path = DETECTOR_CACHE / f"{day}-versions.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    url = f"{ARCHIVE}/list-file-versions?url={quote(DETECTOR_FEED, safe='')}&start={day}&end={day}"
    body = _get(url, 60.0)
    if body is None:
        raise ValueError(f"the archive has no listing for {day}")
    stamps = list(json.loads(body)["timestamps"])
    _write_atomic(path, json.dumps(stamps))
    return stamps


def pick_minutes(stamps: Iterable[str], per_hour: int) -> list[list[str]]:
    """For each slot of each hour, the archived minutes nearest its middle first.

    An hour is cut into `per_hour` equal slots; each slot keeps its versions in
    order of distance from the slot's middle, so a version the archive lists but
    cannot serve falls back to the next nearest one in the same slot."""
    slots: dict[tuple[int, int], list[tuple[float, str]]] = {}
    width = 60.0 / per_hour
    for stamp in stamps:
        minute = int(stamp[11:13])
        slot = int(minute // width)
        middle = (slot + 0.5) * width
        slots.setdefault((_hour(stamp), slot), []).append((abs(minute - middle), stamp))
    return [[stamp for _, stamp in sorted(slots[key])] for key in sorted(slots)]


# A lane-period's reading: `[speed kph, occupancy %, volume]`.
SPEED, OCCUPANCY, VOLUME = 0, 1, 2


def parse_detectors(xml: bytes, detectors: Sequence[str]) -> list[list[float]]:
    """`[speed, occupancy, volume]` for each valid lane-period of `detectors`."""
    wanted = set(detectors)
    rows: list[list[float]] = []
    for detector in ET.fromstring(xml).iter("detector"):
        if detector.findtext("detector_id") not in wanted:
            continue
        for lane in detector.iter("lane"):
            if lane.findtext("valid") != "Y":
                continue
            rows.append(
                [
                    float(lane.findtext("speed") or 0),
                    float(lane.findtext("occupancy") or 0),
                    float(lane.findtext("volume") or 0),
                ]
            )
    return rows


def fetch_minute(
    candidates: Sequence[str], detectors: Sequence[str], refresh: bool
) -> tuple[str, list[list[float]]]:
    """The first of a slot's `candidates` cached for `detectors`, else the first
    the archive serves, kept to `detectors` and cached.

    The cache is read across the whole slot before the network, so a nearest
    minute that 404'd once is not asked for again on every run."""
    key = sorted(detectors)
    if not refresh:
        for stamp in candidates:
            path = DETECTOR_CACHE / f"{stamp}.json"
            if path.exists():
                cached = json.loads(path.read_text())
                if sorted(cached["detectors"]) == key:
                    return stamp, cached["rows"]
    for stamp in candidates:
        url = f"{ARCHIVE}/get-file?url={quote(DETECTOR_FEED, safe='')}&time={stamp}"
        body = _get(url, 120.0)
        if body is None:
            continue
        rows = parse_detectors(body, detectors)
        _write_atomic(
            DETECTOR_CACHE / f"{stamp}.json", json.dumps({"detectors": key, "rows": rows})
        )
        return stamp, rows
    raise ValueError(
        f"the archive served none of the {len(candidates)} minutes in {candidates[0]}'s slot"
    )


def speed_by_hour(readings: dict[int, Sequence[Sequence[float]]]) -> list[float]:
    """Each hour's space-mean speed, kph: the lane-periods' volume over their
    summed volume-over-speed, so a lane that carried more cars weighs more and a
    crawling lane weighs as the density it is. A lane-period that counted no car
    has no speed and is skipped, as is one that counted cars at speed 0 (41 of
    80,331 on the first 1,200 minutes read)."""
    speeds: list[float] = []
    for hour in range(HOURS):
        moving = [row for row in readings.get(hour, ()) if row[VOLUME] > 0 and row[SPEED] > 0]
        if not moving:
            raise ValueError(f"{hour:02d}:00: no detector counted a car")
        speeds.append(
            sum(row[VOLUME] for row in moving) / sum(row[VOLUME] / row[SPEED] for row in moving)
        )
    return speeds


def occupancy_by_hour(readings: dict[int, Sequence[Sequence[float]]]) -> list[float]:
    """Each hour's mean occupancy over its busiest hour's: the cross-check. An
    empty lane-period counts, as the 0% it is."""
    means: list[float] = []
    for hour in range(HOURS):
        rows = readings.get(hour, ())
        if not rows:
            raise ValueError(f"{hour:02d}:00: no detector reading")
        means.append(sum(row[OCCUPANCY] for row in rows) / len(rows))
    busiest = max(means)
    if busiest <= 0.0:
        raise ValueError("no detector was ever occupied")
    return [m / busiest for m in means]


def density_by_hour(flow: Sequence[float], speed: Sequence[float]) -> list[float]:
    """Flow over speed relative to the fastest hour, over its busiest hour."""
    fastest = max(speed)
    density = [f * fastest / v for f, v in zip(flow, speed, strict=True)]
    busiest = max(density)
    return [d / busiest for d in density]


def read_detectors(
    detectors: Sequence[str], days: Sequence[str], refresh: bool
) -> dict[int, list[list[float]]]:
    """Every sampled lane-period of `detectors` on `days`, by clock hour."""
    slots = [
        slot for day in days for slot in pick_minutes(list_minutes(day, refresh), MINUTES_PER_HOUR)
    ]
    readings: dict[int, list[list[float]]] = {hour: [] for hour in range(HOURS)}
    with ThreadPoolExecutor(FETCH_WORKERS) as pool:
        for stamp, rows in pool.map(lambda slot: fetch_minute(slot, detectors, refresh), slots):
            readings[_hour(stamp)].extend(rows)
    return readings


def _packed(values: Sequence[float], digits: int) -> str:
    return "PackedFloat32Array(" + ", ".join(f"{v:.{digits}f}" for v in values) + ")"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="refetch, ignoring the cache")
    args = parser.parse_args(argv)

    shapes: list[list[float]] = []
    counts: dict[int, list[dict[str, float]]] = {}
    vehicles: dict[int, float] = {}
    config = load_config()
    stations = config.census_stations
    if not stations:
        parser.error("hong_kong.yaml's traffic_census block names no station")
    if not config.census_detectors or not config.census_detector_days:
        parser.error("hong_kong.yaml's traffic_census block names no detector or day")
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

    flow = fleet_by_hour(shapes)
    readings = read_detectors(config.census_detectors, config.census_detector_days, args.refresh)
    speed = speed_by_hour(readings)
    occupancy = occupancy_by_hour(readings)
    fleet = density_by_hour(flow, speed)
    mix = mix_by_hour(counts)
    print(f"# vehicles classified per hour, all classes: {[int(vehicles[h]) for h in VCO_HOURS]}")
    print(
        f"# detectors: {len(config.census_detectors)} on {len(config.census_detector_days)}"
        f" weekdays, lane-periods per hour: {[len(readings[h]) for h in range(HOURS)]}"
    )
    print()
    print(
        "| hour | flow (of peak) | speed kph | fleet (of peak) | occupancy (of peak) | "
        + " | ".join(KIND_CLASS)
        + " |"
    )
    print("|---|---|---|---|---|" + "---|" * len(KIND_CLASS))
    for hour in range(HOURS):
        cells = " | ".join(f"{mix[kind][hour]:.1f}" for kind in KIND_CLASS)
        print(
            f"| {hour:02d} | {flow[hour]:.2f} | {speed[hour]:.1f} | {fleet[hour]:.2f}"
            f" | {occupancy[hour]:.2f} | {cells} |"
        )
    print()
    print("fleet_by_hour = " + _packed(fleet, 3))
    print("kinds = Dictionary[String, PackedFloat32Array]({")
    lines = [f'"{kind}": {_packed(mix[kind], 2)}' for kind in sorted(KIND_CLASS)]
    print(",\n".join(lines))
    print("})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
