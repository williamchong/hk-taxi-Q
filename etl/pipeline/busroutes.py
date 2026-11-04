"""The bus and green-minibus routes a moving vehicle keeps to (`P3-78`, `Q182`).

TD's Routes and Fares of Public Transport publish each route direction as its
stops in order — a Point per stop, keyed `routeId`, `routeSeq` (the direction)
and `stopSeq` — and nothing between them: GTFS `shapes.txt` answers 403. So this
stage publishes the stops, and the game's legal router (`RoadRouter`) drives
from one to the next. `tools/bus_legs.py` grades those legs.

🔴 **A stop is snapped, never moved.** Each in-region stop is snapped to its
nearest level-0 centreline exactly as `parked.stops` snaps a pole, and the side
of the drawn road it falls on is which way a bus at it is heading: the
nearside kerb of a two-way road flows with the edge, the offside against it,
and both kerbs of a one-way road flow its way. A stop past `max_snap_m` is
published with `edge` -1 — the bus passes it, and the run is not broken.

🔴 **The seam is the game's.** A route that leaves the region and comes back,
or crosses into a neighbour, is published here as only the stops inside this
rectangle, each with its `seq`; `bus_routes.gd` joins the resident regions'
stops by `key` and order, and a `seq` no resident region holds is where the
route left the map.

🔴 **A route runs only at the hours TD's headways say.** `per_hour` is the
departures from the route's first stop in each hour of `service_day`, every
trip of `trips.txt` counted once at its `HHMM` and again every `headway_secs`
of its `frequencies.txt` rows. A route direction with no trip on that day
runs at no hour and is refused (`no_headway`).

The partition closes: `directions` = `kept` + `no_headway`; `stops` = `snapped`
+ `unsnapped`.
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.config import BusRoutes, Config, load_config
from pipeline.crs import GameTransform, transformer
from pipeline.documents import read_document, write_document
from pipeline.drawnroad import Ribbon, kerbed_ribbons
from pipeline.fetch import cached_source, read_feature_collection
from pipeline.polyline import Segments
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

BUSROUTES_MANIFEST_NAME = "busroutes.json"
BUSROUTES_MANIFEST_SCHEMA = 1
BUS_ROUTES_NAME = "bus_routes.json"
BUS_ROUTES_SCHEMA = 1

HOURS = 24
# `roadgraph.json`'s two-way edge; every one-way edge runs `forward` after `roads`.
_BOTH = "both"


@dataclass
class BusRoutesReport:
    """What the stage read, kept and snapped."""

    directions: int = 0
    kept: int = 0
    no_headway: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    stops: int = 0
    snapped: int = 0
    unsnapped: int = 0
    # Stops on the offside kerb of a one-way road: a bus pulls in on its right.
    offside_one_way: int = 0
    # Kept directions with two or more stops inside the region.
    two_or_more: int = 0
    # Departures across every kept direction in the busiest hour, and which.
    peak_hour: int = 0
    peak_departures: int = 0


@dataclass(frozen=True)
class Stop:
    """One published stop of one route direction."""

    seq: int
    stop_id: str
    lon: float
    lat: float


@dataclass
class Direction:
    """One route direction, as the route file publishes it."""

    route_id: str
    bound: int
    kind: str
    name: str
    operator: str
    stops: list[Stop] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.route_id}-{self.bound}"


def read_directions(city: Config, spec: BusRoutes, *, root: Path | None = None) -> list[Direction]:
    """Every route direction in every declared set, its stops in published order."""
    found: dict[str, Direction] = {}
    for route_set in spec.sets:
        path = cached_source(city, route_set.source, root=root)
        # The files open with a byte-order mark, which `json.loads` on bytes reads past.
        document = read_feature_collection(path, f"bus_routes '{route_set.source}'")
        for feature in document["features"]:
            properties = feature["properties"]
            lon, lat = (float(v) for v in feature["geometry"]["coordinates"][:2])
            route_id = str(properties[spec.field("route")])
            bound = int(properties[spec.field("bound")])
            direction = found.setdefault(
                f"{route_id}-{bound}",
                Direction(
                    route_id,
                    bound,
                    route_set.kind,
                    str(properties[spec.field("name")]),
                    str(properties[spec.field("operator")]),
                ),
            )
            direction.stops.append(
                Stop(
                    int(properties[spec.field("seq")]),
                    str(properties[spec.field("stop")]),
                    lon,
                    lat,
                )
            )
    for direction in found.values():
        direction.stops.sort(key=lambda stop: stop.seq)
    return [found[key] for key in sorted(found)]


def departures_per_hour(
    city: Config, spec: BusRoutes, *, root: Path | None = None
) -> dict[str, list[int]]:
    """Departures in each hour of `service_day`, by `<route_id>-<bound>`.

    A trip with `frequencies.txt` rows departs at each row's start and every
    `headway_secs` until its end (exclusive, GTFS); a trip with none departs once,
    at the `HHMM` its id spells. A time past 24:00 folds back onto the clock.
    """
    running = {
        row["service_id"]
        for row in _rows(city, spec.calendar, root)
        if row[spec.service_day] == "1"
    }
    spans: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    for row in _rows(city, spec.frequencies, root):
        spans[row["trip_id"]].append(
            (_seconds(row["start_time"]), _seconds(row["end_time"]), int(row["headway_secs"]))
        )
    counts: dict[str, list[int]] = {}
    for row in _rows(city, spec.trips, root):
        trip_id = row["trip_id"]
        # `<route_id>-<bound>-<service_id>-<HHMM>`: the direction is spelled here only.
        route_id, bound, service_id, first = trip_id.split("-")[:4]
        if service_id not in running:
            continue
        hours = counts.setdefault(f"{route_id}-{bound}", [0] * HOURS)
        rows = spans.get(trip_id)
        if not rows:
            hours[int(first[:2]) % HOURS] += 1
            continue
        for start_s, end_s, headway_s in rows:
            at = start_s
            while True:
                hours[(at // 3600) % HOURS] += 1
                at += headway_s
                if headway_s <= 0 or at >= end_s:
                    break
    return counts


def _rows(city: Config, source: str, root: Path | None) -> list[dict[str, str]]:
    with cached_source(city, source, root=root).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _seconds(text: str) -> int:
    hours, minutes, seconds = (int(part) for part in text.strip().split(":"))
    return hours * 3600 + minutes * 60 + seconds


def snap_stop(
    segments: Segments,
    ribbons: dict[int, Ribbon],
    edges: dict[int, dict[str, Any]],
    x: float,
    z: float,
    max_snap_m: float,
) -> dict[str, Any] | None:
    """Where a stop attaches: its edge, `t`, the way a bus at it drives, and its
    kerb — or None past `max_snap_m` or off any drawn ribbon."""
    snap = segments.nearest(x, z)
    if snap.distance_m > max_snap_m or snap.edge not in ribbons:
        return None
    middle_m, _ = ribbons[snap.edge].kerb_at(snap.t)
    # `parked._Street.kerb_side`'s expression: `+` nearside, `-0.0` the nearside.
    side = 1 if snap.offset_m - middle_m >= 0.0 else -1
    two_way = str(edges[snap.edge]["direction"]) == _BOTH
    return {
        "edge": snap.edge,
        "t": round(float(snap.t), 6),
        # The nearside flows with the edge; a two-way edge's offside against it;
        # a one-way edge's two kerbs both its way (`parked._flow_heading`).
        "along": side > 0 or not two_way,
        "side": side,
    }


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> BusRoutesReport:
    """Publish every route direction's stops inside the region, in order."""
    report = BusRoutesReport()
    out_dir = city.out_dir(region_id, out_root)
    spec = city.bus_routes
    if spec is None:
        log.info("city '%s' declares no bus_routes block; nothing to publish", city.id)
        _write_manifest(out_dir, city, region_id, report, wrote=False)
        return report

    transform = city.game_transform(region_id)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, "python -m pipeline.surface"
    )
    ribbons = kerbed_ribbons(city, out_dir, region_id, graph, surface)
    edges = {int(edge["id"]): edge for edge in graph["edges"]}
    segments = Segments.of([edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0])
    per_hour = departures_per_hour(city, spec, root=sources_root)
    to_projected = transformer(spec.crs, city.projected_crs)
    far_x, far_z = city.region_high(region_id)

    routes: list[dict[str, Any]] = []
    for direction in read_directions(city, spec, root=sources_root):
        inside = _inside(direction, to_projected, transform, far_x, far_z)
        if not inside:
            continue
        report.directions += 1
        hours = per_hour.get(direction.key)
        if hours is None or not any(hours):
            report.no_headway += 1
            continue
        report.kept += 1
        report.by_kind[direction.kind] = report.by_kind.get(direction.kind, 0) + 1
        report.two_or_more += len(inside) >= 2
        stops: list[dict[str, Any]] = []
        for stop, (x, z) in inside:
            report.stops += 1
            entry: dict[str, Any] = {
                "seq": stop.seq,
                "stop_id": stop.stop_id,
                "plan": [round(x, 3), round(z, 3)],
                "edge": -1,
            }
            snapped = snap_stop(segments, ribbons, edges, x, z, spec.max_snap_m)
            if snapped is None:
                report.unsnapped += 1
            else:
                report.snapped += 1
                if snapped["side"] < 0 and snapped["along"]:
                    report.offside_one_way += 1
                entry.update(snapped)
            stops.append(entry)
        routes.append(
            {
                "key": direction.key,
                "route_id": direction.route_id,
                "bound": direction.bound,
                "kind": direction.kind,
                "name": direction.name,
                "operator": direction.operator,
                "per_hour": hours,
                "stops": stops,
            }
        )
    if routes:
        by_hour = [sum(route["per_hour"][hour] for route in routes) for hour in range(HOURS)]
        report.peak_departures = max(by_hour)
        report.peak_hour = by_hour.index(report.peak_departures)
        write_document(
            out_dir / BUS_ROUTES_NAME,
            {
                "schema_version": BUS_ROUTES_SCHEMA,
                "city_id": city.id,
                "region_id": region_id,
                "service_day": spec.service_day,
                "routes": routes,
            },
        )
    report.by_kind = dict(sorted(report.by_kind.items()))
    _write_manifest(out_dir, city, region_id, report, wrote=bool(routes))
    return report


def _inside(
    direction: Direction,
    to_projected: Any,
    transform: GameTransform,
    far_x: float,
    far_z: float,
) -> list[tuple[Stop, tuple[float, float]]]:
    """The direction's stops inside the region's rectangle, in game plan."""
    found: list[tuple[Stop, tuple[float, float]]] = []
    for stop in direction.stops:
        easting, northing = to_projected.transform(stop.lon, stop.lat)
        x, _, z = transform.to_game(easting, northing)
        if 0.0 <= x <= far_x and 0.0 <= z <= far_z:
            found.append((stop, (float(x), float(z))))
    return found


def _write_manifest(
    out_dir: Path, city: Config, region_id: str, report: BusRoutesReport, *, wrote: bool
) -> None:
    document: dict[str, Any] = {
        "schema_version": BUSROUTES_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "document": BUS_ROUTES_NAME if wrote else None,
    }
    document.update(vars(report))
    write_document(out_dir / BUSROUTES_MANIFEST_NAME, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "busroutes: %d directions -> %d kept %s, %d no headway; %d with two or more stops; "
        "stops %d -> %d snapped, %d unsnapped (%d offside of a one-way); "
        "peak %d departures at %02d:00",
        report.directions,
        report.kept,
        report.by_kind,
        report.no_headway,
        report.two_or_more,
        report.stops,
        report.snapped,
        report.unsnapped,
        report.offside_one_way,
        report.peak_departures,
        report.peak_hour,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
