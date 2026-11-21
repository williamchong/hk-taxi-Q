---
paths:
  - "game/scripts/city/road_router.gd"
  - "game/tools/router_diff.gd"
  - "tools/reachability.py"
  - "etl/tests/test_reachability.py"
---

# The router — before marking work done

`P3-43`, `Q137`. `RoadRouter` searches directed edges over `RoadGraph`; `tools/reachability.py`
is its second implementation.

- **Anything that moves a route** — `road_router.gd`, `RoadGraph`'s `from` / `to`, `is_turn_banned`,
  `plan_length_of`, a profile's rules or bar, `reachability.py`'s traversal — and any rebuilt
  bundle: regenerate the gitignored tables, then `tools/check.sh`. `verify_road_graph.gd` and
  `verify_join.gd` fail naming the command when one is missing or stale.

      .venv/bin/python tools/reachability.py --region wan_chai --json
      .venv/bin/python tools/reachability.py --region causeway_bay --json
      .venv/bin/python tools/reachability.py --region wan_chai --graph-dir etl/out/wan_chai+causeway_bay --json

  Paste the `router[control]` / `router[lane]` lines and the two `route time` lines, before and
  after.
- **Neither implementation imports the other** (`Q95`'s arrangement). A divergence is a finding,
  never a bar to retune.
- **The cost convention is `reachability.py`'s**: entering an edge costs its whole plan length, the
  source's own length excluded, the target's included. The tree holds it reversed (`to_goal[state]`
  from the state's ENTRY node). A fare route seeds the source's remainder and the goal's part.
  Never simplify an end to a node cost: a node cannot carry a turn restriction.
- **Two bars, never merged** (`Q19`): `Profile.legal()` is `is_routable` (lane, 3.20 m) and
  `Profile.player()` is `is_drivable and fits_car` (`car_width_m`, 1.695 m). `verify_road_graph.gd`
  pins `admits` edge by edge and direction by STATE COUNT — "shorter somewhere" cannot tell a
  player profile that obeys one-way from one that does not.
- **The exact diff is the survey population**: `Profile.survey(bar)` is level 0, every rule, no
  U-turn. `legal` and `player` admit level-1 edges the tool never routes (`DRIVABLE_LEVEL`), so
  they are pinned by monotonicity (lane ⊆ legal ⊆ player). Off grade, `verify_traffic`'s
  `_check_arcs` reads every `legal()` arc and ban in reach off `RoadGraph` alone (`Q267`).
- **`prepare(edge, t)` is one reverse Dijkstra** (`PREPARE_BUDGET_USEC`; 0.7 ms legal / 1.9 ms
  player on Wan Chai); `route()` is then microseconds. `prepare` at the hail, `route` off the 5 Hz
  `Hit`, never per frame. `TREE_CACHE` trees are kept: a new `prepare` can evict one in use.
- **Lengths are 64-bit** (`RoadGraph._lengths`), pinned by `_check_topology`'s 1e-6 m re-sum; a
  float32 sum would pass a millimetre bar.
- **`source_tree` / `distance_from`** (`Q203`) is the forward search, uncached so it evicts no
  prepared tree. `distance_from` is INF for no route: a bar test must refuse INF by name.
  `verify_road_graph`'s `source trees:` line ties it to `route()`.
- **`route(..., facing)`** (`P3-46`) seeds `Facing.ALONG`, `AGAINST` or `EITHER` (the default, and
  what the tables use); a direction with no state falls back to either. The fare passes `Hit.along`.
- **Mutation-check, do not read a pass** (`Q72`); keep every local in use (`Q122`). Storing `false`
  under a turn-ban key is not a mutation: `is_turn_banned` tests presence.
- **Consumers**:
  - `FareSystem` (`fares.md`): `prepare` per candidate at the hail, `route` at its sample, par on
    `Profile.legal()` (`Q141`). The minimap draws that same `Route` (`hud.md`), never a second
    search.
  - `TrafficSystem` builds its own `Profile.legal()` router and walks `moves_from`; its routed
    fleet uses `goal_tree` / `next_toward` (`busroutes.md`). Neither touches the prepared cache.
  - `DriveLevel` holds a `Profile.player()` router for the reset alone (`Q241`):
    `distances_to(start line)`. Not `legal()` — only 8 edges lead legally to the HKCEC line.
