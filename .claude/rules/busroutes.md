---
paths:
  - "etl/pipeline/busroutes.py"
  - "etl/pipeline/config_blocks/busroutes.py"
  - "etl/tests/test_busroutes.py"
  - "tools/bus_legs.py"
  - "game/scripts/traffic/bus_routes.gd"
---

# The bus and green-minibus routes — before marking work done

`P3-78`, `Q182`. TD publishes each route direction's stops in order and nothing between them;
the ETL snaps the stops (`pipeline/busroutes.py`), the game drives the legs on the legal router
(`RoadRouter.goal_tree`), and `tools/bus_legs.py` grades them.

- **`pipeline/busroutes.py` or the `bus_routes` block: paste the stage's `busroutes:` line for BOTH
  regions, before and after, and `tools/bus_legs.py` for both** — `tools/battery.py busroutes` runs
  both. On 2026-11-05: Wan Chai 486 directions → 464 kept (405 bus, 59 minibus), 22 no headway, 1,395
  stops → 1,355 snapped, 40 unsnapped (8 offside of a one-way), peak 1,099 departures at 07:00;
  Causeway Bay 251 → 241 (229, 12), 10, 531 → 527 / 4 (13), 528 at 07:00. Legs: Wan Chai 862 → 830
  reached, 32 unreachable, path / straight p50 1.02 p90 1.32 p99 3.86 max 5.34, 21 over 2×; Causeway
  Bay 252 → 189, 63 unreachable, p50 1.17 max 7.96, 2 over 2×. 🔴 **The partition closes**:
  `directions` = `kept` + `no_headway`, `stops` = `snapped` + `unsnapped`.
- 🔴 **A stop is snapped, never moved, and its kerb is its direction** — `parked._flow_heading`'s
  rule: nearside flows with the edge, a two-way edge's offside against it, both kerbs of a one-way
  edge its way. `test_busroutes.py`'s `TestSnap` holds all three; dropping the one-way clause fails
  it by name (2026-11-05). ⚠️ An offside stop on a one-way street is counted, and the bus still
  dwells in the nearside lane.
- 🔴 **The direction is spelled only in the GTFS `trip_id`** (`<route_id>-<bound>-<service>-<HHMM>`).
  6,149 of 82,692 trips have no `frequencies.txt` row and depart once at their `HHMM`; the files are
  CRLF with a byte-order mark. A `frequencies` end is exclusive; the `>=` → `>` mutation fails
  `TestHeadways` by name.
- ⚠️ **`bus_legs.py` routes level 0 only** (`reachability.DRIVABLE_LEVEL`): the game's
  `Profile.legal()` also admits the measured level-1 edges, so an unreachable leg here may be driven
  in the game over a flyover. It grades rather than checks and exits 0. 🔴 Its search is
  `reachability.build()`, the router's second implementation — never `RoadRouter`'s.
- **`bus_routes.gd` or the routed fleet in `traffic_system.gd`: `tools/check.sh`, and paste
  `verify_traffic`'s `route:` lines** (the routed drive at 08:00). 🔴 **A routed vehicle moves only
  by `RoadRouter.next_toward` over `goal_tree`, whose arcs are `moves_from`'s** — never a second
  successor rule. 🔴 **The goal is one WAY of the stop's edge**: the other way is not seeded, so a
  bus on the far side of a two-way street goes round rather than dwelling on the wrong kerb.
  🔴 **The routed fleet rolls on its own RNG** (`_route_rng`), so the wandering cars draw what they
  always drew. ⚠️ **The three gated seeds drive the wandering fleet alone** (`bus_routes` set empty):
  the routed drive's signalled meetings are printed, not gated, because the wandering fleet ALONE
  meets at two merges on seeds 1, 2 and 8 (e114 / e216 into e333 at 0.20 m; e618's fork at
  0.18–0.23 m), and every routed-drive meeting on 2026-11-05 was the e114 / e216 one. Do not gate it
  by picking seeds, and do not raise `INSIDE_M`; the merge is its own finding (`Q182`).
- ⚠️ **Mutation-check the `route:` lines** (2026-11-05, each fails by name): a dwell that drives
  on at 4× `dwell_reach_m` → "stands still" and "at its stop's pole"; `_pick_move` never taking
  the goal's move → "drove to its stop and stood" (0 served, all unreachable); a routed car that
  wanders but keeps its route → "plans the move its stop's search takes" (2,926 car-ticks).
  🚫 "On SOME legal path to its stop" was the first form of that last line and read 0 under the
  same mutation: on a connected network almost every state reaches the stop.
- ⚠️ **`_aim` runs one uncached `goal_tree` (a full reverse search, ~0.7 ms) per stop it tries**,
  only on a departure. One a departure today (`stops_unreachable` 0 in the routed drive); a run of
  unreachable stops costs one search each. A cache keyed by stop is the fix if that counter rises
  or the frame cost shows it — not before.
- 🔴 **The colour is the licence** (`Q167`): a wandering minibus wears `wander_liveries` (red), a
  routed one `route_liveries` (green); the bus wears none. `verify_traffic`'s `route:` livery line.
- ⚠️ **A knocked bus leaves its route** and wanders (`_leave_route` in `_knock`); its mass is
  `parked.tres` `masses_kg["bus"]`, cited in `parked.md`.
- 🔴 **A bus parks only at a terminus** (`Q187`): `parked.terminals` reads THIS stage's
  `bus_routes.json` (a direction's first stop), so `busroutes` runs before `parked` and a change
  here moves the parked roster — paste `parked.json`'s `terminal*` counters too.
- **The stop signals** (`Q187`): brake + left from `lane_change_m` short of the pole and while it
  stands, right for `pull_out_m` as it leaves; `verify_traffic`'s `route:` lamp lines. The kerbside
  stop (`kerb_stop_kinds`, `_kerb_rng`, `RoadGraph.no_stopping`) shares them; 🔴 a routed vehicle
  never stops on a restriction run (`_may_stop_unlawfully`), only a red minibus or a taxi.
