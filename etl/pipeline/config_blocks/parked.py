"""`parked:` — the stationary vehicles a region's streets carry (`P3-71`, `Q161`).

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.

Nothing in this file knows a Hong Kong fact. The publisher's bay vocabulary
(`"Motor Cycles"`, `"Coaches/Buses"`), which point sets are a bus stop and a
minibus terminus, what a name like "Hotel" says about a frontage, and every
length and share below arrive from `config/hong_kong.yaml` (hard rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    LayerSpec,
    SourceLayer,
    _measures,
    _require,
    _source_layer,
    _spec_header,
)

# The roster a city may draw on. The library `tools/make_parked.py` writes
# carries one mesh per kind, named after it; a kind not in this tuple is a mesh
# nothing authored, so the loader refuses it rather than publish a placement of
# nothing.
ROSTER = ("car", "taxi", "minibus", "bus", "coach", "van", "tram", "motorcycle")

# What a placement cites, so a reader can tell a published bay from a fill
# the stage invented at a config share (`Q161`: the complement of the
# restriction layer is a FILL, never a licence).
SOURCE_BAY = "bay"
SOURCE_STOP = "stop"
SOURCE_STAND = "stand"
SOURCE_LAYBY = "layby"
SOURCE_FRONTAGE = "frontage"
SOURCE_FILL = "fill"
SOURCES = (SOURCE_BAY, SOURCE_STOP, SOURCE_STAND, SOURCE_LAYBY, SOURCE_FRONTAGE, SOURCE_FILL)
# The sources that stand a vehicle where the kerb was FOUND — a published bay or
# stop, a lay-by read off the kerb line — and so take neither the corner
# setback nor the lane bar the stage puts on what it invents.
AS_FOUND = (SOURCE_BAY, SOURCE_STOP, SOURCE_LAYBY)

# A placement present through the whole day. Spelled once so a reader, the
# stage and the engine agree on what an absent window means.
ALWAYS: tuple[float, float] | None = None


@dataclass(frozen=True)
class Vehicle:
    """One roster kind's plan footprint, in metres.

    🔴 **Pinned against the authored library's own extent** by
    `tests/test_make_parked.py`: the ETL places by these numbers and the engine
    draws the mesh, and a kind whose two disagree is a car drawn through the
    kerb or standing in the lane, invisibly.
    """

    kind: str
    length_m: float
    width_m: float
    # The gap this kind keeps from a neighbour, where it is not the shared
    # `clearances.gap_m`: motorcycles stand a hand apart in a bay row.
    gap_m: float | None = None
    # Stands nose to the kerb rather than along it: a motorcycle in a bay row,
    # whose published bays are a metre apart.
    across: bool = False
    # The library meshes this kind is drawn from, one picked per placement on
    # a seeded draw: a private car has two liveries. Defaults to the kind.
    meshes: tuple[str, ...] = ()

    @property
    def library_meshes(self) -> tuple[str, ...]:
        return self.meshes if self.meshes else (self.kind,)


@dataclass(frozen=True)
class Bays(LayerSpec):
    """Road Network v2's published on-street parking: one point per bay, and a
    non-spatial attribute table joined on the point's own coordinate.

    `kinds` maps the publisher's vehicle-type text onto the roster; a text the
    table does not name is refused and counted, never guessed.
    """

    attributes: SourceLayer
    kinds: dict[str, str]
    # The attribute row's coordinate against the point: the publisher writes
    # the same grid metre in both, so this is slack for a rounding and no more.
    join_m: float


@dataclass(frozen=True)
class StopSet:
    """One point set a vehicle kind waits at — a bus stop, a minibus terminus."""

    source: str
    crs: str
    kind: str
    # The share of visits a vehicle is found here (`Q161`: a bus is not always
    # at the same stop). 1.0 is a vehicle always present.
    chance: float
    hours: tuple[float, float] | None
    # Where the published point is a KERBSIDE position (a bus stop pole) the
    # vehicle stands on the road beside it; the point is snapped as a fare node
    # is, and refused past this.
    max_snap_m: float


@dataclass(frozen=True)
class Stand:
    """What waits at one of `fares.json`'s own kinds: a queue of taxis behind a
    stand, a tram at a tram stop."""

    kind: str
    queue: int
    pitch_m: float
    chance: float
    hours: tuple[float, float] | None


@dataclass(frozen=True)
class FrontageClass:
    """What a building's published name says about its kerb (`Q161`): a hotel
    has a coach and a taxi outside it, an office tower a van. First-hit-wins
    over substrings, in the order written — `fares.groups`' rule, for the same
    reason: the names are free text."""

    id: str
    match: tuple[str, ...]
    kinds: tuple[str, ...]
    hours: tuple[float, float] | None


@dataclass(frozen=True)
class Frontage:
    classes: tuple[FrontageClass, ...]
    # A named footprint further than this from the kerb it would be served at
    # stands on no street this stage furnishes.
    max_distance_m: float
    pitch_m: float

    def class_of(self, name: str) -> FrontageClass | None:
        for klass in self.classes:
            if any(token in name for token in klass.match):
                return klass
        return None


@dataclass(frozen=True)
class Laybys:
    """A lay-by read off the kerb line (the user's drive, 2026-10-11: "allow
    stopped cars on lane that suddenly widen and shrink back because those
    area are probably for stopping cars"): a run of the road's kerb standing
    a parking lane's depth proud of the edge's own median kerb, between
    `min_bulge_m` and `max_bulge_m` (deeper is a junction flare or a slip
    road), `min_run_m` to `max_run_m` long, inside the edge's trim. Stood
    whatever the street's class or speed — the widening IS the stopping
    place — on either kerb."""

    min_bulge_m: float
    max_bulge_m: float
    min_run_m: float
    max_run_m: float
    pitch_m: float
    kinds: dict[str, float]
    chance: float
    hours: tuple[float, float] | None


@dataclass(frozen=True)
class Fill:
    """The restriction layer's complement as a density fill.

    🔴 **A share, never a licence** (`Q161`): 57 of Wan Chai's 90 km of level-0
    kerb carries no published restriction, which is far more kerb than is ever
    parked, so the stage draws slots `pitch_m` apart and keeps `share` of them
    on a seeded draw. `single_yellow_hours` is when a posted-hours restriction
    holds; outside it the kerb joins the fill, which is the one place the night
    street carries more cars than the day.
    """

    share: float
    pitch_m: float
    kinds: dict[str, float]
    single_yellow_hours: tuple[float, float]
    hours_by_kind: dict[str, tuple[float, float] | None]


@dataclass(frozen=True)
class SlowStreets:
    """Where the stage may INVENT a kerb — the fill, a frontage — as against
    where the publisher put a bay or a stop (the user's drive, 2026-10-11:
    "cars dont park in fast lanes"). A street class the graph publishes
    (`roads.street_class`), at or under a speed, with no bus lane; an edge the
    class join never reached is refused too."""

    street_classes: tuple[str, ...]
    max_speed_kph: float
    bus_lane: bool
    # Fewer authored lanes than this stands nothing: a one-lane street parked
    # on is a street blocked. And a bridge or a flyover (`on_structure` at any
    # station) parks nobody.
    min_lanes: int
    on_structure: bool

    def allows(self, edge: dict) -> bool:
        """An edge missing its class or its limit is refused: the safe default
        for a gate that keeps cars off fast roads."""
        if edge.get("street_class") not in self.street_classes:
            return False
        speed = edge.get("speed_limit_kph")
        if speed is None or float(speed) > self.max_speed_kph:
            return False
        if int(edge.get("lanes", 0)) < self.min_lanes:
            return False
        if not self.on_structure and any(bool(flag) for flag in edge.get("on_structure", ())):
            return False
        return self.bus_lane or not bool(edge.get("bus_lane"))

    @staticmethod
    def allows_side(edge: dict, side: float) -> bool:
        """The nearside always; the offside only on a two-way street, where it
        is the other flow's nearside. On a one-way street the offside is the
        fast lane (the user's drive, 2026-10-11: "cars dont park in right most
        lane which is fast lane in hong kong")."""
        return side > 0.0 or str(edge.get("direction")) == "both"


@dataclass(frozen=True)
class Clearances:
    # Between the vehicle's outer flank and the kerb.
    kerb_gap_m: float
    # No vehicle inside this of an edge's end, past the junction trim.
    junction_m: float
    # No vehicle inside this of a fare node: the hail ring, the spawn's
    # set-back and the passenger's own kerb stay clear.
    fare_m: float
    # No vehicle on or beside a crossing.
    crossing_m: float
    # Between two vehicles, nose to tail or flank to flank.
    gap_m: float
    # An invented row whose kerb leaves less than the lanes it must keep
    # beside the parked vehicle is refused: the road is not wide enough to
    # park on and keep them.
    lane_width_m: float
    # How many of the authored lanes a parked row takes (the user's drive,
    # 2026-10-11): Hong Kong parks one side of a 6.4 m two-way back street and
    # passes in the one lane left, so a row keeps `lanes - row_lanes` lanes
    # and never fewer than one. A second row on the other kerb keeps
    # `lanes - 2 * row_lanes`.
    row_lanes: int

    def lanes_kept(self, lanes: int, rows: int) -> int:
        return max(1, lanes - rows * self.row_lanes)


@dataclass(frozen=True)
class Parked:
    """The stationary roster (`P3-71`, `Q161`) — see each part."""

    library: str
    vehicles: dict[str, Vehicle]
    bays: Bays | None
    stops: tuple[StopSet, ...]
    stands: dict[str, Stand]
    frontage: Frontage | None
    fill: Fill | None
    laybys: Laybys | None
    tram_max_track_m: float
    clearances: Clearances
    slow_streets: SlowStreets

    def vehicle(self, kind: str) -> Vehicle:
        if kind not in self.vehicles:
            known = ", ".join(sorted(self.vehicles)) or "none"
            raise KeyError(f"parked: no vehicle called {kind!r}. Declared: {known}")
        return self.vehicles[kind]


def _hours(value: Any, where: str) -> tuple[float, float] | None:
    """`[from_h, to_h]` on a 24 h clock, wrapping past midnight, or `null`."""
    if value is None:
        return ALWAYS
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{where} must be [from_h, to_h] or null, got {value!r}")
    low, high = (float(value[0]), float(value[1]))
    for hour in (low, high):
        if not 0.0 <= hour <= 24.0:
            raise ValueError(f"{where} hours must be within 0..24, got {value!r}")
    if low == high:
        raise ValueError(f"{where} is an empty window: {value!r}")
    return (low, high)


def _share(value: Any, where: str) -> float:
    share = float(value)
    if not 0.0 < share <= 1.0:
        raise ValueError(f"{where} must be a share in (0, 1], got {value!r}")
    return share


def _kind(value: Any, where: str) -> str:
    kind = str(value)
    if kind not in ROSTER:
        raise ValueError(f"{where} names {kind!r}, which is not in the roster {ROSTER}")
    return kind


def _vehicles(body: Any, where: str) -> dict[str, Vehicle]:
    if not isinstance(body, dict) or not body:
        raise ValueError(f"{where} must be a mapping of kind to footprint, got {body!r}")
    vehicles: dict[str, Vehicle] = {}
    for kind, entry in body.items():
        kind_where = f"{where}:{kind}"
        _kind(kind, kind_where)
        if not isinstance(entry, dict):
            raise ValueError(f"{kind_where} must be a mapping, got {entry!r}")
        lengths = _measures(entry, kind_where, ("length_m", "width_m"), positive=True)
        gap_m = None if entry.get("gap_m") is None else float(entry["gap_m"])
        if gap_m is not None and gap_m < 0.0:
            raise ValueError(f"{kind_where}:gap_m must not be negative, got {gap_m}")
        raw_meshes = entry.get("meshes") or []
        if isinstance(raw_meshes, str) or not isinstance(raw_meshes, (list, tuple)):
            raise ValueError(f"{kind_where}:meshes must be a list, got {raw_meshes!r}")
        vehicles[str(kind)] = Vehicle(
            kind=str(kind),
            gap_m=gap_m,
            across=bool(entry.get("across", False)),
            meshes=tuple(str(mesh) for mesh in raw_meshes),
            **lengths,
        )
    return vehicles


def _bays(body: Any, where: str) -> Bays | None:
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    header = _spec_header(body, where, ())
    attributes = _source_layer(
        _require(body, "attributes", where),
        f"{where}:attributes",
        ("x", "y", "vehicle_type", "hours"),
    )
    raw_kinds = _require(body, "kinds", where)
    if not isinstance(raw_kinds, dict) or not raw_kinds:
        raise ValueError(f"{where}:kinds must map the publisher's text to a roster kind")
    kinds = {str(text): _kind(kind, f"{where}:kinds[{text!r}]") for text, kind in raw_kinds.items()}
    return Bays(
        **header,
        attributes=attributes,
        kinds=kinds,
        **_measures(body, where, ("join_m",), positive=True),
    )


def _stops(body: Any, where: str) -> tuple[StopSet, ...]:
    if body is None:
        return ()
    if not isinstance(body, (list, tuple)):
        raise ValueError(f"{where} must be a list, got {body!r}")
    stops: list[StopSet] = []
    for index, entry in enumerate(body):
        entry_where = f"{where}[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{entry_where} must be a mapping, got {entry!r}")
        stops.append(
            StopSet(
                source=str(_require(entry, "source", entry_where)),
                crs=str(_require(entry, "crs", entry_where)),
                kind=_kind(_require(entry, "kind", entry_where), f"{entry_where}:kind"),
                chance=_share(_require(entry, "chance", entry_where), f"{entry_where}:chance"),
                hours=_hours(entry.get("hours"), f"{entry_where}:hours"),
                **_measures(entry, entry_where, ("max_snap_m",), positive=True),
            )
        )
    return tuple(stops)


def _stands(body: Any, where: str) -> dict[str, Stand]:
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ValueError(f"{where} must map a fare kind to what waits there, got {body!r}")
    stands: dict[str, Stand] = {}
    for fare_kind, entry in body.items():
        entry_where = f"{where}:{fare_kind}"
        if not isinstance(entry, dict):
            raise ValueError(f"{entry_where} must be a mapping, got {entry!r}")
        queue = int(entry.get("queue", 1))
        if queue < 1:
            raise ValueError(f"{entry_where}:queue must be at least 1, got {queue}")
        stands[str(fare_kind)] = Stand(
            kind=_kind(_require(entry, "kind", entry_where), f"{entry_where}:kind"),
            queue=queue,
            pitch_m=float(entry.get("pitch_m", 0.0)),
            chance=_share(entry.get("chance", 1.0), f"{entry_where}:chance"),
            hours=_hours(entry.get("hours"), f"{entry_where}:hours"),
        )
        if queue > 1 and stands[str(fare_kind)].pitch_m <= 0.0:
            raise ValueError(f"{entry_where}: a queue of {queue} needs a positive pitch_m")
    return stands


def _frontage(body: Any, where: str) -> Frontage | None:
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    raw = _require(body, "classes", where)
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{where}:classes must be a non-empty mapping")
    classes: list[FrontageClass] = []
    for class_id, entry in raw.items():
        class_where = f"{where}:classes:{class_id}"
        if not isinstance(entry, dict):
            raise ValueError(f"{class_where} must be a mapping, got {entry!r}")
        match = tuple(str(token) for token in _require(entry, "match", class_where))
        kinds = tuple(
            _kind(kind, f"{class_where}:kinds") for kind in _require(entry, "kinds", class_where)
        )
        if not match or not kinds:
            raise ValueError(f"{class_where} needs at least one match token and one kind")
        classes.append(
            FrontageClass(
                id=str(class_id),
                match=match,
                kinds=kinds,
                hours=_hours(entry.get("hours"), f"{class_where}:hours"),
            )
        )
    # ⚠️ ORDER IS LOAD-BEARING, and a token that an earlier class already
    # matches can never fire: refused as `fares.groups` refuses a shadowed
    # category, so the shadowing is a decision and not a typo.
    for index, klass in enumerate(classes):
        for earlier in classes[:index]:
            for token in klass.match:
                if any(prior in token for prior in earlier.match):
                    raise ValueError(
                        f"{where}:classes:{klass.id} token {token!r} is shadowed by "
                        f"{earlier.id}'s {earlier.match}"
                    )
    return Frontage(
        classes=tuple(classes),
        **_measures(body, where, ("max_distance_m", "pitch_m"), positive=True),
    )


def _weighted_kinds(raw: Any, where: str, vehicles: dict[str, Vehicle]) -> dict[str, float]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{where} must map a roster kind to its weight")
    kinds = {_kind(kind, where): float(weight) for kind, weight in raw.items()}
    if any(weight <= 0.0 for weight in kinds.values()):
        raise ValueError(f"{where} weights must be positive, got {raw!r}")
    for kind in kinds:
        if kind not in vehicles:
            raise ValueError(f"{where} names {kind!r}, which vehicles: does not size")
    return kinds


def _laybys(body: Any, where: str, vehicles: dict[str, Vehicle]) -> Laybys | None:
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    lengths = _measures(
        body,
        where,
        ("min_bulge_m", "max_bulge_m", "min_run_m", "max_run_m", "pitch_m"),
        positive=True,
    )
    if (
        lengths["max_bulge_m"] <= lengths["min_bulge_m"]
        or lengths["max_run_m"] <= lengths["min_run_m"]
    ):
        raise ValueError(f"{where}: each max must be over its min")
    return Laybys(
        kinds=_weighted_kinds(_require(body, "kinds", where), f"{where}:kinds", vehicles),
        chance=_share(body.get("chance", 1.0), f"{where}:chance"),
        hours=_hours(body.get("hours"), f"{where}:hours"),
        **lengths,
    )


def _fill(body: Any, where: str, vehicles: dict[str, Vehicle]) -> Fill | None:
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    kinds = _weighted_kinds(_require(body, "kinds", where), f"{where}:kinds", vehicles)
    raw_hours = body.get("hours_by_kind") or {}
    hours_by_kind = {
        _kind(kind, f"{where}:hours_by_kind"): _hours(window, f"{where}:hours_by_kind:{kind}")
        for kind, window in raw_hours.items()
    }
    single = _hours(_require(body, "single_yellow_hours", where), f"{where}:single_yellow_hours")
    assert single is not None
    return Fill(
        share=_share(_require(body, "share", where), f"{where}:share"),
        kinds=kinds,
        single_yellow_hours=single,
        hours_by_kind=hours_by_kind,
        **_measures(body, where, ("pitch_m",), positive=True),
    )


_CLEARANCES = ("kerb_gap_m", "junction_m", "fare_m", "crossing_m", "gap_m", "lane_width_m")


def _clearances(body: Any, where: str) -> Clearances:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    row_lanes = int(_require(body, "row_lanes", where))
    if row_lanes < 1:
        raise ValueError(f"{where}:row_lanes must be at least 1, got {row_lanes}")
    return Clearances(**_measures(body, where, _CLEARANCES), row_lanes=row_lanes)


def _slow_streets(body: Any, where: str) -> SlowStreets:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    raw = _require(body, "street_classes", where)
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError(f"{where}:street_classes must be a non-empty list, got {raw!r}")
    min_lanes = int(_require(body, "min_lanes", where))
    if min_lanes < 1:
        raise ValueError(f"{where}:min_lanes must be at least 1, got {min_lanes}")
    return SlowStreets(
        street_classes=tuple(str(klass) for klass in raw),
        max_speed_kph=float(_require(body, "max_speed_kph", where)),
        bus_lane=bool(body.get("bus_lane", False)),
        min_lanes=min_lanes,
        on_structure=bool(body.get("on_structure", False)),
    )


def _parked(body: Any, where: str) -> Parked | None:
    """The optional parked-vehicle block (`P3-71`).

    Absent, the region ships no `parked_placements.json` and the manifest names
    none — the shape every furniture block takes. Every kind a part of the
    block names must be sized under `vehicles:`, because the stage places by
    the footprint and a kind with none would stand at no width.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    vehicles = _vehicles(_require(body, "vehicles", where), f"{where}:vehicles")
    parked = Parked(
        library=str(_require(body, "library", where)),
        vehicles=vehicles,
        bays=_bays(body.get("bays"), f"{where}:bays"),
        stops=_stops(body.get("stops"), f"{where}:stops"),
        stands=_stands(body.get("stands"), f"{where}:stands"),
        frontage=_frontage(body.get("frontage"), f"{where}:frontage"),
        fill=_fill(body.get("fill"), f"{where}:fill", vehicles),
        laybys=_laybys(body.get("laybys"), f"{where}:laybys", vehicles),
        clearances=_clearances(_require(body, "clearances", where), f"{where}:clearances"),
        slow_streets=_slow_streets(_require(body, "slow_streets", where), f"{where}:slow_streets"),
        **_measures(body, where, ("tram_max_track_m",), positive=True),
    )
    named: set[str] = set()
    if parked.bays is not None:
        named.update(parked.bays.kinds.values())
    named.update(stop.kind for stop in parked.stops)
    named.update(stand.kind for stand in parked.stands.values())
    if parked.frontage is not None:
        for klass in parked.frontage.classes:
            named.update(klass.kinds)
    unsized = sorted(named - set(vehicles))
    if unsized:
        raise ValueError(f"{where} places {unsized}, which vehicles: does not size")
    if parked.clearances.gap_m <= 0.0 or parked.clearances.kerb_gap_m < 0.0:
        raise ValueError(f"{where}:clearances gap_m must be positive and kerb_gap_m not negative")
    return parked
