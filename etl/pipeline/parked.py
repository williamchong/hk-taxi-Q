"""The stationary vehicles a region's streets carry (`P3-71`, `Q161`).

Writes `parked_placements.json`, a placements document (`P5-2`'s shape) over
the AUTHORED library `tools/make_parked.py` commits — one mesh per roster kind —
and `parked.json`, the stage's own report. No `.glb` is built here: the
vehicles are hand-authored assets under CC BY-SA, not build output.

**Where a vehicle stands is published data, in this precedence:**

1. **A bay** — Road Network v2's `ONSTREETPARK`, one point per bay, whose
   attribute table says what parks there (a motorcycle on 342 of Wan Chai's
   607). The one positive "parking is allowed here" source the estate has.
2. **A stop** — TD's bus stop and minibus terminus point sets, each a position
   and a stop id, snapped as a fare node is (`Q15`: level 0, plan distance),
   with a bus present by a seeded CHANCE so the same stop is not always served.
3. **A stand** — `fares.json`'s own kinds: a queue of taxis behind a taxi
   stand, a tram at a tram stop on the bed `tramway.py` laid.
4. **A frontage** — what a building's published name says about its kerb: a
   coach and a taxi at a hotel, a van at an office. The proxy for a land use
   the estate does not publish (`ART_DESIGN.md`).
5. **A fill** — the restriction layer's complement at a config SHARE, never a
   licence: a posted-hours single yellow joins it outside those hours, which
   is the one place the night street carries more cars than the day.

Every placement carries `kind`, `source`, `hours` (`[from_h, to_h]` on a 24 h
clock, wrapping, or `null` for always) and `chance`; the engine resolves which
stand at the rig's hour (`Q160`), never a second clock.

**Where a vehicle stands on the road.** At the kerb of the ROAD (`Ribbon.kerb_at`,
the corridor, not the ribbon's territory — `Q57`), `kerb_gap_m` off it, nose
along the flow of its own side: nearside traffic flows with the edge, the
offside of a two-way edge against it, and a one-way street parks both kerbs
facing the way it runs. Refused: inside the junction trim plus `junction_m`;
within `fare_m` of a fare node (the hail ring and the spawn's set-back stay
clear); within `crossing_m` of a crossing; on a fenced edge; on a kerb whose
width leaves less than the authored lanes beside the vehicle; and overlapping
a vehicle already placed — a bay beats a stop beats a stand beats a frontage
beats a fill, and `gap_m` separates neighbours.

⚠️ **The side convention is `kerbside.py`'s trap, and it renders plausibly when
wrong.** A vehicle facing against its kerb's flow is a perfectly drawn vehicle.
`Snap.offset_m` is positive on the nearside — the one statement, asserted
against `mitres` in `tests/test_fares.py` — and `_flow_heading` reads it; the
test here stands a car on each side of a two-way fixture edge and checks the
two face apart.
"""

from __future__ import annotations

import argparse
import logging
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import shapely
from shapely.strtree import STRtree

from pipeline.config import (
    ALWAYS,
    SOURCE_BAY,
    SOURCE_FILL,
    SOURCE_FRONTAGE,
    SOURCE_LAYBY,
    SOURCE_STAND,
    SOURCE_STOP,
    SOURCES,
    Config,
    Parked,
    load_config,
)
from pipeline.crossings import CrossingReport, read_crossings
from pipeline.crs import GameTransform, transformer
from pipeline.documents import read_document, write_document
from pipeline.drawnroad import Ribbon, kerbed_ribbons, nearside
from pipeline.fares import FARES_NAME, FARES_SCHEMA, read_places
from pipeline.fence import FENCE_NAME, FENCE_SCHEMA
from pipeline.fetch import cached_source, read_feature_collection
from pipeline.gdb import points as gdb_points
from pipeline.gdb import read_layer, read_table
from pipeline.kerbside import NEARSIDE, OFFSIDE
from pipeline.placements import PLACEMENTS_SCHEMA, Placement, placement
from pipeline.polyline import Segments, Snap, bearing_deg, frame, plan_lengths
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA
from pipeline.tramway import TRAMWAY_MANIFEST_NAME, TRAMWAY_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

PARKED_PLACEMENTS_NAME = "parked_placements.json"
PARKED_MANIFEST_NAME = "parked.json"
PARKED_MANIFEST_SCHEMA = 1

# The order a placement wins a kerb in: a published bay over a stop over a
# stand over a frontage over the fill.
_PRIORITY = {source: rank for rank, source in enumerate(SOURCES)}

# `fares.json`'s kinds this stage furnishes. The tram stop is a `poi`.
_FARE_TAXI_STAND = "taxi_stand"
_FARE_TRAM_STOP = "poi"

# A kerbside run's kinds, as `roadgraph.json` publishes them (`P3-13`).
_DOUBLE = "double"
_SINGLE = "single"

# The refusals, in the order they are asked; `ParkedReport.refused` is keyed
# by these, and `_stand` returns one instead of a `Stood`.
FENCED = "fenced"
NO_RIBBON = "no_ribbon"
AT_JUNCTION = "at_junction"
KERB_HIDDEN = "kerb_hidden"
TOO_NARROW = "too_narrow"
IN_KEEP_OUT = "in_keep_out"
OVERLAPPING = "overlapping"
# An invented kerb on a street the stage may not invent one on.
FAST_STREET = "fast_street"


@dataclass
class ParkedReport:
    """What the stage read, placed and refused — every partition closes."""

    bays_read: int = 0
    bays_outside: int = 0
    bays_unjoined: int = 0
    bays_unsnapped: int = 0
    bays_unknown_type: int = 0
    bays_by_type: dict[str, int] = field(default_factory=dict)
    # 🔴 A published bay lying inside a published restriction run: TD's two
    # layers disagreeing, counted and placed (the bay is the positive source).
    bays_on_restriction: int = 0
    stops_read: int = 0
    stops_outside: int = 0
    stops_unsnapped: int = 0
    stands_read: int = 0
    trams_no_track: int = 0
    places_read: int = 0
    frontages_classified: int = 0
    frontages_too_far: int = 0
    layby_runs: int = 0
    layby_m: float = 0.0
    fill_slots: int = 0
    fill_kept: int = 0
    fill_night_only: int = 0
    # Every refusal, by the source that asked and the rule that answered, in
    # the order the rules are asked: `FENCED`, `NO_RIBBON`, `AT_JUNCTION`,
    # `KERB_HIDDEN`, `TOO_NARROW`, `IN_KEEP_OUT` (a fare node or a crossing),
    # `OVERLAPPING`, and `FAST_STREET` for a frontage on a street the stage
    # may not invent a kerb on (the fill never draws a slot there).
    # ⚠️ Partition: `candidates` = `placed` + every count here.
    refused: dict[str, dict[str, int]] = field(default_factory=dict)
    candidates: int = 0
    placed: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    by_hours: dict[str, int] = field(default_factory=dict)
    # The room left beside the narrowest parked vehicle, against the lanes —
    # and how many PUBLISHED positions (a bay, a stop) leave less than the
    # authored lanes beside them. Those stand anyway: the publisher put them
    # there, and a bus at its stop is in the lane in Hong Kong too. The fill
    # never does: it is refused as `too_narrow`.
    narrowest_lane_room_m: float = math.inf
    published_in_lane: int = 0

    def refuse(self, source: str, reason: str) -> None:
        by_reason = self.refused.setdefault(source, {})
        by_reason[reason] = by_reason.get(reason, 0) + 1


@dataclass(frozen=True)
class Candidate:
    """A vehicle asked to stand somewhere, before the shared refusals."""

    kind: str
    source: str
    edge: int
    t: float
    # +1 nearside, -1 offside — the kerb it stands against.
    side: float
    hours: tuple[float, float] | None
    chance: float
    # A stand told to face a bearing of its own (a tram on its bed) rather
    # than its kerb's flow.
    heading_deg: float | None = None
    # A stand placed off the kerb (a tram on its bed): the plan point itself.
    plan: tuple[float, float] | None = None
    height_m: float | None = None
    # How many invented rows the street carries with this one: 1 for a row on
    # one kerb, 2 where the fill takes both. Published sources are 0 — they
    # take no lane bar.
    rows: int = 0


@dataclass(frozen=True)
class Stood:
    """A candidate that passed, with its footprint for the overlap test."""

    candidate: Candidate
    x: float
    y: float
    z: float
    rot_y_deg: float
    footprint: shapely.Polygon
    lane_room_m: float


class _Street:
    """The region's level-0 roads as the stage asks about them."""

    def __init__(self, graph: dict, surface: dict, ribbons: dict[int, Ribbon]) -> None:
        self.ribbons = ribbons
        self.edges = {int(edge["id"]): edge for edge in graph["edges"]}
        self.segments = Segments.of(
            [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
        )
        self.hidden = {
            int(entry["edge"]): entry.get("kerb_hidden_m") or {} for entry in surface["carriageway"]
        }

    def length_m(self, edge: int) -> float:
        return float(self.ribbons[edge].length_m)

    def one_way(self, edge: int) -> bool:
        return str(self.edges[edge]["direction"]) != "both"

    def runs(self, edge: int, side: float) -> list[tuple[float, float, str]]:
        """The kerbside restriction runs on one side, `(from_m, to_m, kind)`."""
        name = NEARSIDE if side > 0.0 else OFFSIDE
        return [
            (float(run["from_m"]), float(run["to_m"]), str(run["kind"]))
            for run in self.edges[edge].get("kerbside", ())
            if str(run["side"]) == name
        ]

    def kerb_hidden(self, edge: int, side: float, along_m: float) -> bool:
        name = NEARSIDE if side > 0.0 else OFFSIDE
        return any(low <= along_m <= high for low, high in self.hidden.get(edge, {}).get(name, ()))

    def height_at(self, edge: int, t: float) -> float:
        ribbon = self.ribbons[edge]
        return float(np.interp(t, ribbon.at, ribbon.height_m))

    def heading_deg(self, edge: int, t: float) -> float:
        """The edge's own bearing at `t`, from its polyline."""
        ribbon = self.ribbons[edge]
        index = int(np.clip(np.searchsorted(ribbon.at, t) - 1, 0, len(ribbon.at) - 2))
        return bearing_deg(ribbon.plan[index + 1] - ribbon.plan[index])

    def kerb_side(self, snap: Snap) -> float:
        """Which kerb of the ROAD a snapped point is nearer: `+1` nearside,
        `-1` offside — `Ribbon.kerb_target`'s expression, `-0.0` reading as
        the nearside for its reason."""
        middle_m, _ = self.ribbons[snap.edge].kerb_at(snap.t)
        return 1.0 if snap.offset_m - middle_m >= 0.0 else -1.0


def _flow_heading(street: _Street, edge: int, t: float, side: float) -> float:
    """Which way a vehicle on `side` faces: the flow of that kerb's traffic.

    Nearside flows with the edge; the offside of a two-way edge flows against
    it; a one-way street's two kerbs both face the way it runs. 🔴 Side is
    `Snap.offset_m`'s sign (`+` nearside), read nowhere else.
    """
    heading = street.heading_deg(edge, t)
    if side < 0.0 and not street.one_way(edge):
        return (heading + 180.0) % 360.0
    return heading


def _footprint(x: float, z: float, rot_y_deg: float, length_m: float, width_m: float):
    """The plan rectangle of a vehicle stood at `(x, z)` facing `rot_y_deg`."""
    along, across = frame(rot_y_deg)
    half_l, half_w = length_m / 2.0, width_m / 2.0
    centre = np.array([x, z])
    corners = [
        centre + along * half_l + across * half_w,
        centre + along * half_l - across * half_w,
        centre - along * half_l - across * half_w,
        centre - along * half_l + across * half_w,
    ]
    return shapely.Polygon([tuple(map(float, corner)) for corner in corners])


def _window_key(hours: tuple[float, float] | None) -> str:
    return "always" if hours is None else f"{hours[0]:g}-{hours[1]:g}"


def in_window(hour: float, hours: tuple[float, float] | None) -> bool:
    """Whether a 24 h clock reading falls in `[from_h, to_h)`, wrapping past
    midnight. The engine's `ParkedRoster` restates this in GDScript."""
    if hours is None:
        return True
    low, high = hours
    if low < high:
        return low <= hour < high
    return hour >= low or hour < high


def _complement(hours: tuple[float, float]) -> tuple[float, float]:
    """The window a posted-hours restriction leaves free."""
    return (hours[1], hours[0])


def _seeded(*parts: Any) -> random.Random:
    """A draw that depends on what it is for and nothing else, so a rebuild
    places the same fill and a battery diff moves only on a real change."""
    return random.Random(":".join(str(part) for part in parts))


def _read_bays(
    city: Config,
    spec: Parked,
    region_id: str,
    transform: GameTransform,
    report: ParkedReport,
    *,
    sources_root: Path | None,
) -> list[tuple[float, float, str]]:
    """Every bay in region as `(x, z, kind)`, through the publisher's vocabulary."""
    bays = spec.bays
    assert bays is not None
    path = cached_source(city, bays.source, root=sources_root)
    layer = read_layer(
        path,
        bays.layer.layer,
        columns=bays.layer.columns,
        bbox=city.read_box(region_id).bbox,
        zip_member=bays.member,
        expect_crs=city.projected_crs,
    )
    _owners, plan = gdb_points(layer)
    report.bays_read = len(plan)
    table = read_table(path, bays.attributes.layer, columns=bays.attributes.columns)
    xs = table.column(bays.attributes.field("x"))
    ys = table.column(bays.attributes.field("y"))
    types = table.column(bays.attributes.field("vehicle_type"))
    by_grid: dict[tuple[int, int], int] = {}
    quantum = max(bays.join_m, 1e-3)
    for row in range(len(xs)):
        try:
            key = (round(float(xs[row]) / quantum), round(float(ys[row]) / quantum))
        except (TypeError, ValueError):
            continue
        by_grid.setdefault(key, row)
    far_x, far_z = city.region_high(region_id)
    found: list[tuple[float, float, str]] = []
    for easting, northing in plan:
        if not (math.isfinite(easting) and math.isfinite(northing)):
            continue
        x, _, z = transform.to_game(float(easting), float(northing))
        if not (0.0 <= x <= far_x and 0.0 <= z <= far_z):
            report.bays_outside += 1
            continue
        row = None
        base = (round(float(easting) / quantum), round(float(northing) / quantum))
        for dx in (0, -1, 1):
            for dy in (0, -1, 1):
                row = by_grid.get((base[0] + dx, base[1] + dy))
                if row is not None:
                    break
            if row is not None:
                break
        if row is None:
            report.bays_unjoined += 1
            continue
        text = str(types[row])
        report.bays_by_type[text] = report.bays_by_type.get(text, 0) + 1
        kind = bays.kinds.get(text)
        if kind is None:
            report.bays_unknown_type += 1
            continue
        found.append((float(x), float(z), kind))
    report.bays_by_type = dict(sorted(report.bays_by_type.items()))
    return found


def _read_stop_points(
    city: Config,
    source: str,
    crs: str,
    region_id: str,
    transform: GameTransform,
    report: ParkedReport,
    *,
    sources_root: Path | None,
) -> list[tuple[float, float]]:
    features = read_feature_collection(
        cached_source(city, source, root=sources_root), f"parked stops '{source}'"
    )["features"]
    report.stops_read += len(features)
    to_projected = transformer(crs, city.projected_crs)
    far_x, far_z = city.region_high(region_id)
    found: list[tuple[float, float]] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue
        easting, northing = to_projected.transform(float(coordinates[0]), float(coordinates[1]))
        x, _, z = transform.to_game(easting, northing)
        if not (0.0 <= x <= far_x and 0.0 <= z <= far_z):
            report.stops_outside += 1
            continue
        found.append((float(x), float(z)))
    return found


def _snap_candidate(
    street: _Street,
    x: float,
    z: float,
    kind: str,
    source: str,
    hours: tuple[float, float] | None,
    chance: float,
    max_snap_m: float,
) -> tuple[Candidate | None, Snap]:
    snap = street.segments.nearest(x, z)
    if snap.distance_m > max_snap_m or snap.edge not in street.ribbons:
        return None, snap
    side = street.kerb_side(snap)
    return Candidate(kind, source, snap.edge, snap.t, side, hours, chance), snap


def _stand(street: _Street, spec: Parked, candidate: Candidate) -> Stood | str:
    """One candidate stood, or the name of the refusal that stopped it."""
    vehicle = spec.vehicle(candidate.kind)
    clear = spec.clearances
    if candidate.plan is not None:
        # Placed off the kerb — a tram on its bed — so the kerb rules do not
        # apply; the overlap test still does.
        assert candidate.heading_deg is not None and candidate.height_m is not None
        x, z = candidate.plan
        return Stood(
            candidate,
            x,
            candidate.height_m,
            z,
            candidate.heading_deg,
            _footprint(x, z, candidate.heading_deg, vehicle.length_m, vehicle.width_m),
            math.inf,
        )
    ribbon = street.ribbons.get(candidate.edge)
    if ribbon is None:
        return NO_RIBBON
    length_m = ribbon.length_m
    along_m = candidate.t * length_m
    half_l = vehicle.length_m / 2.0
    # A PUBLISHED position — a bay, a stop — is where the publisher put it,
    # and stands wherever the junction trim leaves a kerb; `junction_m` and the
    # lane-room bar are for what this stage invents. A lay-by is the kerb's
    # own widening and takes neither either.
    published = candidate.source in (SOURCE_BAY, SOURCE_STOP, SOURCE_LAYBY)
    setback_m = 0.0 if published else clear.junction_m
    if (
        along_m - half_l < ribbon.trim_start_m + setback_m
        or along_m + half_l > length_m - ribbon.trim_end_m - setback_m
    ):
        return AT_JUNCTION
    if street.kerb_hidden(candidate.edge, candidate.side, along_m):
        return KERB_HIDDEN
    middle_m, half_m = ribbon.kerb_at(candidate.t)
    edge = street.edges[candidate.edge]
    lanes = int(edge["lanes"])
    road_m = 2.0 * half_m
    # Across the kerb (a motorcycle), the vehicle's LENGTH is what it takes
    # off the road.
    across_m = vehicle.length_m if vehicle.across else vehicle.width_m
    # The lanes a row keeps: the fill and a frontage take one (`row_lanes`),
    # the second row down a street's other kerb another, and a street keeps
    # at least one. `lane_room_m` is measured against those, so the counter
    # says what an invented row left to pass in.
    kept = clear.lanes_kept(lanes, candidate.rows)
    # A second row down the other kerb takes its own width too, taken as this
    # vehicle's: the fill decides the rows a street carries from the same sum.
    rows_m = max(1, candidate.rows) * (across_m + clear.kerb_gap_m)
    lane_room_m = road_m - rows_m - kept * clear.lane_width_m
    if lane_room_m < 0.0 and not published:
        return TOO_NARROW
    lateral_m = middle_m + candidate.side * (half_m - clear.kerb_gap_m - across_m / 2.0)
    edge_heading = street.heading_deg(candidate.edge, candidate.t)
    if candidate.heading_deg is not None:
        heading = candidate.heading_deg
    elif vehicle.across:
        # Nose to the kerb: the bearing of the vector from the centreline to
        # this side's kerb.
        heading = bearing_deg(candidate.side * nearside(edge_heading))
    else:
        heading = _flow_heading(street, candidate.edge, candidate.t, candidate.side)
    foot = ribbon.foot_at(candidate.t)
    point = foot + lateral_m * nearside(edge_heading)
    x, z = float(point[0]), float(point[1])
    return Stood(
        candidate,
        x,
        street.height_at(candidate.edge, candidate.t),
        z,
        heading,
        _footprint(x, z, heading, vehicle.length_m, vehicle.width_m),
        lane_room_m,
    )


def _fill_candidates(street: _Street, spec: Parked, report: ParkedReport) -> list[Candidate]:
    """Slots `pitch_m` apart down every free kerb, `share` of them kept — spread
    evenly along the kerb from a seeded phase, so a street is parked at a
    steady rhythm rather than in clumps (the user's drive, 2026-10-11) — with a
    kind drawn by weight and the hours its kind keeps, or on a posted-hours
    single yellow the hours the restriction leaves.

    Which kerbs: a street wide enough to keep its lanes past two rows takes
    both; one too narrow for that but wide enough past one row takes its
    nearside only — Hong Kong's 6.4 m back street, parked on one side and
    passed in the lane left. The widths are the ROAD's, kerb to kerb, read at
    the edge's middle."""
    fill = spec.fill
    assert fill is not None
    clear = spec.clearances
    kinds = sorted(fill.kinds)
    weights = [fill.kinds[kind] for kind in kinds]
    widest_m = max(spec.vehicle(kind).width_m for kind in kinds) + clear.kerb_gap_m
    candidates: list[Candidate] = []
    for edge_id in sorted(street.ribbons):
        edge = street.edges[edge_id]
        if not spec.slow_streets.allows(edge):
            continue
        length_m = street.length_m(edge_id)
        _middle_m, half_m = street.ribbons[edge_id].kerb_at(0.5)
        road_m = 2.0 * half_m
        lanes = int(edge["lanes"])
        rows = 0
        if road_m - 2.0 * widest_m >= clear.lanes_kept(lanes, 2) * clear.lane_width_m:
            rows = 2
        elif road_m - widest_m >= clear.lanes_kept(lanes, 1) * clear.lane_width_m:
            rows = 1
        if rows == 0:
            continue
        for side in (1.0, -1.0):
            if side < 0.0 and rows < 2:
                continue
            if not spec.slow_streets.allows_side(edge, side):
                continue
            runs = street.runs(edge_id, side)
            draw = _seeded("fill", edge_id, side)
            phase = draw.random()
            slots = int(length_m // fill.pitch_m)
            for index in range(slots):
                along_m = (index + 0.5) * fill.pitch_m
                report.fill_slots += 1
                restrictions = {kind for low, high, kind in runs if low <= along_m <= high}
                if _DOUBLE in restrictions:
                    continue
                # Every `1 / share` slots, from the phase: the slot is kept
                # where the running share crosses a whole number.
                if int((index + phase) * fill.share) == int((index + phase - 1.0) * fill.share):
                    continue
                kind = draw.choices(kinds, weights=weights)[0]
                hours = fill.hours_by_kind.get(kind, ALWAYS)
                if _SINGLE in restrictions:
                    # Only outside the posted hours — and a kind with hours of
                    # its own (a van by day) never parks on a day restriction.
                    if hours is not None:
                        continue
                    hours = _complement(fill.single_yellow_hours)
                    report.fill_night_only += 1
                report.fill_kept += 1
                candidates.append(
                    Candidate(
                        kind, SOURCE_FILL, edge_id, along_m / length_m, side, hours, 1.0, rows=rows
                    )
                )
    return candidates


def _layby_candidates(street: _Street, spec: Parked, report: ParkedReport) -> list[Candidate]:
    """Slots down every run of kerb standing a parking lane proud of its edge's
    median kerb — a lay-by, read off `carriageway_region.json`'s kerb line
    through `Ribbon.kerb_left_m` / `kerb_right_m` (`Laybys` says the bars)."""
    laybys = spec.laybys
    assert laybys is not None
    kinds = sorted(laybys.kinds)
    weights = [laybys.kinds[kind] for kind in kinds]
    candidates: list[Candidate] = []
    for edge_id in sorted(street.ribbons):
        ribbon = street.ribbons[edge_id]
        if ribbon.kerb_at_t is None or ribbon.kerb_left_m is None or ribbon.kerb_right_m is None:
            continue
        along = ribbon.kerb_at_t * ribbon.length_m
        low_m = ribbon.trim_start_m
        high_m = ribbon.length_m - ribbon.trim_end_m
        for side, kerb in ((1.0, ribbon.kerb_left_m), (-1.0, ribbon.kerb_right_m)):
            bulge = kerb - float(np.median(kerb))
            proud = (bulge >= laybys.min_bulge_m) & (bulge <= laybys.max_bulge_m)
            start = 0
            while start < len(proud):
                if not proud[start]:
                    start += 1
                    continue
                stop = start
                while stop < len(proud) and proud[stop]:
                    stop += 1
                run_from = float(along[start])
                run_to = float(along[min(stop, len(along) - 1)])
                run_m = run_to - run_from
                inside = run_from > low_m and run_to < high_m
                if inside and laybys.min_run_m <= run_m <= laybys.max_run_m:
                    report.layby_runs += 1
                    report.layby_m += run_m
                    draw = _seeded("layby", edge_id, side, round(run_from, 1))
                    slots = int(run_m // laybys.pitch_m)
                    for index in range(slots):
                        at_m = run_from + (index + 0.5) * laybys.pitch_m
                        kind = draw.choices(kinds, weights=weights)[0]
                        candidates.append(
                            Candidate(
                                kind,
                                SOURCE_LAYBY,
                                edge_id,
                                at_m / ribbon.length_m,
                                side,
                                laybys.hours,
                                laybys.chance,
                            )
                        )
                start = stop
    return candidates


def _nearest_track(
    tracks: list[np.ndarray], x: float, z: float, max_m: float
) -> tuple[np.ndarray, float] | None:
    """The bed nearest a point and the fraction along it, within `max_m`."""
    best: tuple[np.ndarray, float, float] | None = None
    for bed in tracks:
        if len(bed) < 2:
            continue
        line = shapely.LineString(bed[:, [0, 2]])
        distance = line.distance(shapely.Point(x, z))
        if distance <= max_m and (best is None or distance < best[2]):
            best = (bed, float(line.project(shapely.Point(x, z), normalized=True)), distance)
    return None if best is None else (best[0], best[1])


def _on_track(bed: np.ndarray, fraction: float) -> tuple[float, float, float, float]:
    """`(x, y, z, bearing_deg)` at a fraction along a bed."""
    along = plan_lengths(bed)
    at_m = fraction * float(along[-1])
    index = int(np.clip(np.searchsorted(along, at_m) - 1, 0, len(along) - 2))
    span = along[index + 1] - along[index]
    f = 0.0 if span <= 0.0 else float((at_m - along[index]) / span)
    point = bed[index] + f * (bed[index + 1] - bed[index])
    step = bed[index + 1] - bed[index]
    return float(point[0]), float(point[1]), float(point[2]), bearing_deg(step[[0, 2]])


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> ParkedReport:
    """Read the region's published parking and write its placements."""
    spec = city.parked
    report = ParkedReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no parked block; nothing to place", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, "python -m pipeline.surface"
    )
    street = _Street(graph, surface, kerbed_ribbons(city, out_dir, region_id, graph, surface))
    fares = read_document(out_dir / FARES_NAME, FARES_SCHEMA, "python -m pipeline.fares")
    fence = read_document(out_dir / FENCE_NAME, FENCE_SCHEMA, "python -m pipeline.fence")
    fenced = {int(edge) for edge in fence.get("fenced_edges", ())}
    clear = spec.clearances

    # ---- the zones nothing parks in ----
    keep_out: list[shapely.Geometry] = []
    fare_points: list[tuple[float, float, float, float, str]] = []
    for node in fares.get("nodes", ()):
        x, _, z = (float(v) for v in node["pos"])
        # A node a passenger stands at keeps its ring clear; a `poi` tram stop
        # is neither a pickup nor a drop-off, and the tram stands AT it.
        if bool(node.get("pickup")) or bool(node.get("dropoff")):
            keep_out.append(shapely.Point(x, z).buffer(clear.fare_m))
        fare_points.append(
            (
                x,
                z,
                float(node.get("edge_t", 0.0)),
                float(node.get("nearest_edge", -1)),
                node["kind"],
            )
        )
    if city.crossings is not None:
        crossing_report = CrossingReport()
        for crossing in read_crossings(
            city, city.crossings, region_id, transform, crossing_report, sources_root=sources_root
        ):
            for part in crossing.lines:
                if len(part) >= 2:
                    keep_out.append(shapely.LineString(part).buffer(clear.crossing_m))
    candidates: list[Candidate] = []
    max_snap_m = city.fares.max_snap_m

    if spec.bays is not None:
        for x, z, kind in _read_bays(
            city, spec, region_id, transform, report, sources_root=sources_root
        ):
            candidate, snap = _snap_candidate(
                street, x, z, kind, SOURCE_BAY, ALWAYS, 1.0, max_snap_m
            )
            if candidate is None:
                report.bays_unsnapped += 1
                continue
            along_m = candidate.t * street.length_m(candidate.edge)
            if any(
                low <= along_m <= high
                for low, high, _kind in street.runs(candidate.edge, candidate.side)
            ):
                report.bays_on_restriction += 1
            candidates.append(candidate)

    for stop_set in spec.stops:
        for x, z in _read_stop_points(
            city,
            stop_set.source,
            stop_set.crs,
            region_id,
            transform,
            report,
            sources_root=sources_root,
        ):
            candidate, _ = _snap_candidate(
                street,
                x,
                z,
                stop_set.kind,
                SOURCE_STOP,
                stop_set.hours,
                stop_set.chance,
                stop_set.max_snap_m,
            )
            if candidate is None:
                report.stops_unsnapped += 1
                continue
            # A stop is a kerb, so a car's slot there is a bus's: the point
            # itself keeps cars away at the fill's own gap.
            keep_out.append(shapely.Point(x, z).buffer(clear.gap_m))
            candidates.append(candidate)
    keep_out_tree = STRtree(keep_out) if keep_out else None

    tracks: list[np.ndarray] = []
    if _FARE_TRAM_STOP in spec.stands:
        tramway = read_document(
            out_dir / TRAMWAY_MANIFEST_NAME, TRAMWAY_MANIFEST_SCHEMA, "python -m pipeline.tramway"
        )
        tracks = [np.asarray(line, dtype=np.float64) for line in tramway.get("track_lines", ())]
    for x, z, t, edge, kind in fare_points:
        stand = spec.stands.get(kind)
        if stand is None:
            continue
        report.stands_read += 1
        edge_id = int(edge)
        if kind == _FARE_TRAM_STOP:
            found = _nearest_track(tracks, x, z, spec.tram_max_track_m)
            if found is None:
                report.trams_no_track += 1
                continue
            bed, fraction = found
            tx, ty, tz, bearing = _on_track(bed, fraction)
            if edge_id in street.ribbons:
                # Face the flow of the kerb the stop is on: a tram runs on the
                # left too.
                snap = street.segments.nearest(x, z)
                flow = _flow_heading(street, edge_id, snap.t, street.kerb_side(snap))
                if math.cos(math.radians(flow - bearing)) < 0.0:
                    bearing = (bearing + 180.0) % 360.0
            candidates.append(
                Candidate(
                    stand.kind,
                    SOURCE_STAND,
                    edge_id,
                    fraction,
                    1.0,
                    stand.hours,
                    stand.chance,
                    heading_deg=bearing,
                    plan=(tx, tz),
                    height_m=ty,
                )
            )
            continue
        if edge_id not in street.ribbons:
            report.refuse(SOURCE_STAND, NO_RIBBON)
            continue
        snap = street.segments.nearest(x, z)
        side = street.kerb_side(snap)
        length_m = street.length_m(edge_id)
        # Behind the stand, against its kerb's flow, so the hail ring and the
        # passenger's own kerb stay clear: the queue starts `fare_m` back.
        with_flow = side > 0.0 or street.one_way(edge_id)
        for rank in range(stand.queue):
            back_m = clear.fare_m + spec.vehicle(stand.kind).length_m / 2.0 + rank * stand.pitch_m
            along_m = t * length_m - back_m if with_flow else t * length_m + back_m
            if not 0.0 <= along_m <= length_m:
                continue
            candidates.append(
                Candidate(
                    stand.kind,
                    SOURCE_STAND,
                    edge_id,
                    along_m / length_m,
                    side,
                    stand.hours,
                    stand.chance,
                )
            )

    if spec.frontage is not None and city.fares.places is not None:
        places = read_places(
            city, city.fares.places, region_id, transform, sources_root=sources_root
        )
        report.places_read = len(places)
        for place in places:
            name = place.name_en or ""
            klass = spec.frontage.class_of(name)
            if klass is None:
                continue
            report.frontages_classified += 1
            centroid = place.footprint.centroid
            snap = street.segments.nearest(float(centroid.x), float(centroid.y))
            if snap.edge not in street.ribbons:
                report.refuse(SOURCE_FRONTAGE, NO_RIBBON)
                continue
            if not spec.slow_streets.allows(street.edges[snap.edge]):
                report.refuse(SOURCE_FRONTAGE, FAST_STREET)
                continue
            foot = street.ribbons[snap.edge].foot_at(snap.t)
            if place.distance_m(float(foot[0]), float(foot[1])) > spec.frontage.max_distance_m:
                report.frontages_too_far += 1
                continue
            side = street.kerb_side(snap)
            if not spec.slow_streets.allows_side(street.edges[snap.edge], side):
                report.refuse(SOURCE_FRONTAGE, FAST_STREET)
                continue
            length_m = street.length_m(snap.edge)
            for rank, kind in enumerate(klass.kinds):
                along_m = snap.t * length_m + rank * spec.frontage.pitch_m
                if not 0.0 <= along_m <= length_m:
                    continue
                candidates.append(
                    Candidate(
                        kind,
                        SOURCE_FRONTAGE,
                        snap.edge,
                        along_m / length_m,
                        side,
                        klass.hours,
                        1.0,
                        rows=1,
                    )
                )

    if spec.laybys is not None:
        candidates.extend(_layby_candidates(street, spec, report))
    if spec.fill is not None:
        candidates.extend(_fill_candidates(street, spec, report))

    # ---- the shared refusals, in precedence ----
    candidates.sort(key=lambda c: (_PRIORITY[c.source], c.edge, c.t, c.side))
    report.candidates = len(candidates)
    stood: list[Stood] = []
    # Accepted footprints, each padded by half its gap, bucketed by a plan cell
    # two buses long: an overlap test walks one cell and its eight neighbours.
    taken: dict[tuple[int, int], list[shapely.Polygon]] = {}
    cell_m = 2.0 * max(vehicle.length_m for vehicle in spec.vehicles.values())
    for candidate in candidates:
        if candidate.edge in fenced:
            report.refuse(candidate.source, FENCED)
            continue
        placed = _stand(street, spec, candidate)
        if isinstance(placed, str):
            report.refuse(candidate.source, placed)
            continue
        if (
            keep_out_tree is not None
            and candidate.source != SOURCE_STOP
            and len(keep_out_tree.query(placed.footprint, predicate="intersects")) > 0
        ):
            report.refuse(candidate.source, IN_KEEP_OUT)
            continue
        gap_m = spec.vehicle(candidate.kind).gap_m
        spaced = placed.footprint.buffer((clear.gap_m if gap_m is None else gap_m) / 2.0)
        cell = (int(placed.x // cell_m), int(placed.z // cell_m))
        neighbours = [
            taken.get((cell[0] + dx, cell[1] + dz), ()) for dx in (-1, 0, 1) for dz in (-1, 0, 1)
        ]
        if any(spaced.intersects(other) for near in neighbours for other in near):
            report.refuse(candidate.source, OVERLAPPING)
            continue
        stood.append(placed)
        taken.setdefault(cell, []).append(spaced)

    stands: list[Placement] = []
    for placed in stood:
        meshes = spec.vehicle(placed.candidate.kind).library_meshes
        mesh = meshes[0]
        if len(meshes) > 1:
            mesh = _seeded(
                "mesh", placed.candidate.edge, placed.candidate.side, placed.candidate.t
            ).choice(meshes)
        entry = placement(mesh, (placed.x, placed.y, placed.z), placed.rot_y_deg)
        entry["kind"] = placed.candidate.kind
        entry["source"] = placed.candidate.source
        entry["hours"] = None if placed.candidate.hours is None else list(placed.candidate.hours)
        entry["chance"] = round(placed.candidate.chance, 3)
        entry["edge"] = placed.candidate.edge
        stands.append(entry)
        report.placed += 1
        report.by_kind[placed.candidate.kind] = report.by_kind.get(placed.candidate.kind, 0) + 1
        report.by_source[placed.candidate.source] = (
            report.by_source.get(placed.candidate.source, 0) + 1
        )
        key = _window_key(placed.candidate.hours)
        report.by_hours[key] = report.by_hours.get(key, 0) + 1
        report.narrowest_lane_room_m = min(report.narrowest_lane_room_m, placed.lane_room_m)
        if placed.lane_room_m < 0.0:
            report.published_in_lane += 1
    for kind in spec.vehicles:
        report.by_kind.setdefault(kind, 0)
    for source in SOURCES:
        report.by_source.setdefault(source, 0)
    report.by_kind = dict(sorted(report.by_kind.items()))
    report.by_source = dict(sorted(report.by_source.items()))
    report.by_hours = dict(sorted(report.by_hours.items()))
    for source in SOURCES:
        report.refused.setdefault(source, {})
    report.refused = {
        source: dict(sorted(reasons.items())) for source, reasons in sorted(report.refused.items())
    }
    if not math.isfinite(report.narrowest_lane_room_m):
        report.narrowest_lane_room_m = 0.0

    write_document(
        out_dir / PARKED_PLACEMENTS_NAME,
        {
            "schema_version": PLACEMENTS_SCHEMA,
            "city_id": city.id,
            "region_id": region_id,
            "library": spec.library,
            "placements": stands,
        },
    )
    _write_manifest(out_dir, city, region_id, report)
    return report


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: ParkedReport) -> int:
    document: dict[str, Any] = {
        "schema_version": PARKED_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "placements_document": PARKED_PLACEMENTS_NAME if report.placed else None,
        "library": city.parked.library if city.parked is not None else None,
    }
    for name, value in vars(report).items():
        document[name] = round(value, 3) if isinstance(value, float) else value
    return write_document(out_dir / PARKED_MANIFEST_NAME, document)


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
        "parked: %d bays (%d unjoined, %d unsnapped, %d on a restriction), %d stops in region, "
        "%d stands, %d frontages, %d of %d fill slots -> %d of %d candidates placed %s, "
        "refused %s, narrowest lane room %.2f m",
        report.bays_read,
        report.bays_unjoined,
        report.bays_unsnapped,
        report.bays_on_restriction,
        report.stops_read - report.stops_outside,
        report.stands_read,
        report.frontages_classified,
        report.fill_kept,
        report.fill_slots,
        report.placed,
        report.candidates,
        report.by_kind,
        report.refused,
        report.narrowest_lane_room_m,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
