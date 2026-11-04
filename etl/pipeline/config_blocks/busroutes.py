"""`bus_routes:` — the published bus and green-minibus routes (`P3-78`, `Q182`).

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.

Nothing in this file knows a Hong Kong fact: which property names a route, its
direction and its stop order, and which calendar day the headways are read for,
arrive from `config/hong_kong.yaml` (hard rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import _field, _measures, _require

# The roles `fields:` maps onto the publisher's properties.
ROUTE_ROLES = ("route", "bound", "seq", "stop", "name", "operator")
# The calendar's day columns, one of which `service_day` names.
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class RouteSet:
    """One published route file and the vehicle kind that runs it."""

    source: str
    # The parked library's kind a moving vehicle on this file's routes is drawn
    # as (`parked.vehicles`): a bus, or a minibus in its green licence.
    kind: str


@dataclass(frozen=True)
class BusRoutes:
    """How `pipeline/busroutes.py` reads the routes (`P3-78`)."""

    sets: tuple[RouteSet, ...]
    # The CRS the route files' points are published in.
    crs: str
    # Role -> property name, `ROUTE_ROLES` exactly.
    fields: dict[str, str]
    # The GTFS headways: `trips.txt`, `frequencies.txt` and `calendar.txt`, as
    # declared sources.
    trips: str
    frequencies: str
    calendar: str
    # Which calendar day the per-hour departures are counted for.
    service_day: str
    # A stop further than this from a level-0 centreline is published unsnapped.
    max_snap_m: float

    def field(self, role: str) -> str:
        return _field(self.fields, role, "bus_routes.fields")


def _bus_routes(body: Any, where: str) -> BusRoutes | None:
    # Optional: absent, the stage writes an empty document and no vehicle keeps
    # to a route.
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    raw_sets = _require(body, "sets", where)
    if not isinstance(raw_sets, list) or not raw_sets:
        raise ValueError(f"{where}:sets must be a non-empty list")
    sets: list[RouteSet] = []
    for index, entry in enumerate(raw_sets):
        entry_where = f"{where}:sets[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{entry_where} must be a mapping, got {entry!r}")
        sets.append(
            RouteSet(
                source=str(_require(entry, "source", entry_where)),
                kind=str(_require(entry, "kind", entry_where)),
            )
        )
    fields = _require(body, "fields", where)
    if not isinstance(fields, dict) or set(fields) != set(ROUTE_ROLES):
        raise ValueError(f"{where}:fields must name exactly {list(ROUTE_ROLES)}")
    day = str(_require(body, "service_day", where))
    if day not in DAYS:
        raise ValueError(f"{where}:service_day must be one of {list(DAYS)}, got {day!r}")
    return BusRoutes(
        sets=tuple(sets),
        crs=str(_require(body, "crs", where)),
        fields={str(role): str(name) for role, name in fields.items()},
        trips=str(_require(body, "trips", where)),
        frequencies=str(_require(body, "frequencies", where)),
        calendar=str(_require(body, "calendar", where)),
        service_day=day,
        **_measures(body, where, ("max_snap_m",), positive=True),
    )
