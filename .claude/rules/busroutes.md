---
paths:
  - "etl/pipeline/busroutes.py"
  - "etl/pipeline/config_blocks/busroutes.py"
  - "etl/tests/test_busroutes.py"
  - "tools/bus_legs.py"
  - "game/scripts/traffic/bus_routes.gd"
---

# The bus and green-minibus routes — before marking work done

`P3-78`, `Q182`, `Q187`. TD publishes each direction's stops in order; the ETL snaps them, the
game drives the legs on the legal router, and `tools/bus_legs.py` grades them.

- **`pipeline/busroutes.py` or the `bus_routes` block**: `tools/battery.py busroutes --region <r>
  --before <checkout root>` for both regions — the stage's `busroutes:` line and `bus_legs.py`.
  The partition closes: `directions` = `kept` + `no_headway`, `stops` = `snapped` + `unsnapped`.
- **A stop is snapped, never moved, and its kerb is its direction** (`parked._flow_heading`'s rule:
  nearside with the edge, a two-way edge's offside against it, both kerbs of a one-way edge its
  way; `TestSnap`). An offside stop on a one-way street is counted, and the bus still dwells in the
  nearside lane.
- **GTFS**: the direction is spelled only in `trip_id` (`<route_id>-<bound>-<service>-<HHMM>`); a
  trip with no `frequencies.txt` row departs once at its `HHMM`; the files are CRLF with a
  byte-order mark; a `frequencies` end is exclusive (`TestHeadways`).
- **`bus_legs.py` routes level 0 only** (`reachability.DRIVABLE_LEVEL`): `Profile.legal()` also
  admits the measured level-1 edges, so a leg unreachable here may be driven over a flyover. It
  grades and exits 0. Its search is `reachability.build()`, never `RoadRouter`'s.
- **`bus_routes.gd` or the routed fleet in `traffic_system.gd`**: `tools/check.sh`, and paste
  `verify_traffic`'s `route:` lines (the routed drive).
  - A routed vehicle moves only by `RoadRouter.next_toward` over `goal_tree`, whose arcs are
    `moves_from`'s — never a second successor rule.
  - The goal is ONE way of the stop's edge; the other is not seeded, so a bus on the far side goes
    round rather than dwelling on the wrong kerb.
  - The routed fleet rolls on `TrafficRouted`'s own `_rng`, so the wandering cars' draws hold.
  - The routed drive's signalled meetings are printed, not gated: the wandering fleet alone meets
    at two merges on seeds 1, 2 and 8 (e114 / e216 into e333 at 0.20 m; e618's fork). Do not gate
    by picking seeds or raise `INSIDE_M` (`Q182`).
  - A counter of cars "on SOME legal path to its stop" reads 0 by construction (a connected
    network); the `route:` line is "plans the move its stop's search takes".
- `TrafficRouted.aim` runs one uncached `goal_tree` (~0.7 ms) per stop tried, on a departure only;
  cache by stop only if `stops_unreachable` rises.
- **The colour is the licence** (`Q167`): a wandering minibus wears `wander_liveries` (red), a
  routed one `route_liveries` (green), the bus none. `route:` livery line.
- A knocked bus leaves its route and wanders (`TrafficRouted.leave_route`); its mass is
  `parked.tres` `masses_kg["bus"]`.
- **A bus parks only at a terminus** (`Q187`): `parked.terminals` reads this stage's
  `bus_routes.json`, named by busroutes' MANIFEST (never a probe of the file), so `busroutes` runs
  before `parked` and a change here moves the parked roster: paste `parked.json`'s `terminal*`
  counters. A run that keeps no route deletes `bus_routes.json` (`TestTheTerminus`).
- **The stop signals** (`Q187`): brake + left from `lane_change_m` short of the pole and while
  standing, right for `pull_out_m` leaving; `route:` lamp lines. The kerbside stop
  (`kerb_stop_kinds`, `TrafficKerbside`'s own `_rng`, `RoadGraph.no_stopping`) shares them. A routed
  vehicle never stops on a restriction run (`TrafficKerbside.may_stop_unlawfully`): only a red
  minibus or a taxi does.
