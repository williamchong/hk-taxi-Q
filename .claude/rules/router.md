---
paths:
  - "game/scripts/city/road_router.gd"
  - "game/tools/router_diff.gd"
  - "tools/reachability.py"
  - "etl/tests/test_reachability.py"
---

# The router — before marking work done

`P3-43`, `Q137`. `RoadRouter` (`game/scripts/city/road_router.gd`) is a directed-edge search over
`RoadGraph`'s accessors, and `tools/reachability.py` is its second implementation.

- 🔴 **Anything that moves a route — `road_router.gd`, `RoadGraph`'s `from` / `to`, `is_turn_banned`
  or `plan_length_of`, a profile's rules or bar, `reachability.py`'s traversal: regenerate the
  tables and run `tools/check.sh`.** The tables are a grader's reading of the bundle and live
  beside it, gitignored; `verify_road_graph.gd` and `verify_join.gd` FAIL naming the command when
  one is missing or stale:

      .venv/bin/python tools/reachability.py --region wan_chai --json
      .venv/bin/python tools/reachability.py --region causeway_bay --json
      .venv/bin/python tools/reachability.py --region wan_chai --graph-dir etl/out/wan_chai+causeway_bay --json

  A rebuilt bundle owes the same three lines (the header carries the edge and turn counts). Paste
  the `router[control]` / `router[lane]` lines (pairs diffed, worst metres) and the two `route time`
  lines, before and after.
- 🔴 **Neither side imports the other** (`Q95`'s arrangement). `reachability.py` stays pure Python
  over the documents; the router reads `RoadGraph`. A divergence is a finding, never a bar to
  retune, and making one call the other leaves one implementation grading itself.
- 🔴 **The cost convention is `reachability.py`'s, exactly**: entering an edge costs its whole plan
  length, the source's own length is excluded, the target's included. The tree holds it reversed —
  `to_goal[state]` from the state's ENTRY node — so a table cell is the least `to_goal` over the
  source's successors. A fare route seeds the source's remainder (`(1 - t)·len` along, `t·len`
  against) and the goal's part. Do not "simplify" either end to a node cost: a node cannot carry a
  turn restriction.
- 🔴 **Two bars, one measurement, never merged** (`Q19`): `Profile.legal()` is `is_routable` (lane,
  3.20 m) and `Profile.player()` is `is_drivable and fits_car` (car, 1.80 m). Each profile reads
  its own predicate; `verify_road_graph.gd` pins `admits` to them edge by edge, and pins direction
  by STATE COUNT — a player profile that quietly obeyed one-way would still shorten routes through
  the turns and U-turns it frees, so "shorter somewhere" cannot tell the two apart.
- ⚠️ **The exact diff is the survey population, not the shipped one.** `Profile.survey(bar)` is
  level 0, every rule, no U-turn — the tool's `nothing (control)` and `starved at one lane` rows.
  `legal` and `player` admit the measured level-1 edges the tool never routes, so they are pinned by
  monotonicity (lane ⊆ legal ⊆ player, distances no longer, and the player strictly shorter
  somewhere). Widening the tool to level 1 is a change to what it grades and wants its own numbers
  (`DRIVABLE_LEVEL`'s note).
- ⚠️ **"1 ms" is the PREPARED query.** `prepare(edge, t)` is one reverse Dijkstra, priced against a
  frame (`PREPARE_BUDGET_USEC`, measured 0.7 ms legal / 1.9 ms player on Wan Chai); `route()` is
  then microseconds. Call `prepare` at the hail and `route` off the 5 Hz `Hit`, never per frame.
  ⚠️ A full search also fits inside 1 ms today — the tree is what makes 5 Hz free, not what makes
  the budget; do not cite it as the reason a per-query search was refused.
- ⚠️ **Lengths are 64-bit and the pin is 1e-6.** `RoadGraph._lengths` sums the document's doubles
  before the `Vector3` cast. A float32 sum lands within 0.001 m anyway (4.7e-4 over the longest
  route), so the millimetre tolerance would not catch it — `_check_topology`'s 1e-6 m re-sum does.
- ⚠️ **Mutation-check it rather than reading its pass** (`Q72`). Each of these fails by name; a
  mutation must keep every local in use or it tests the linter (`Q122`):
  a. `_build`: drop the `is_turn_banned` test → `control` diff (pairs only ours, metres over).
  b. `survey()`: `allow_u_turn = true` → `control` diff.
  c. Build the backward state on one-way edges under `obey_direction` → `control` diff.
  d. `_pred` filled from `onward` instead of `state` → almost every pair "only the tool's".
  e. `route()`: the against partial written `(1 - source_t)` → the path re-sum.
  f. `player()`: `obey_direction = true` → the state count.
  g. `RoadGraph._build`: store the reversed triple → `_check_topology`, 314 lines.
  h. A table header edited (`"edges"`) → the stale guard, naming the command.
  i. Python: `--json` rows from `world.reach` instead of `distances` → `TestTable`.
  🚫 Storing `false` under the key is NOT a mutation: `is_turn_banned` tests presence.
- ⚠️ **One consumer is wired: `FareSystem`** (`P3-1a`, `fares.md`). It pays `prepare` at the hail,
  one per candidate destination, and `route` at its own 5 Hz sample from the car's `Hit`; its par
  is `Profile.legal()` (`Q141`). The minimap draws that same `Route` (`P3-46`, `hud.md`) off the
  fare, never a second search; `fare_preview.gd` still does not call it.
- ⚠️ **`route(..., facing)` seeds one direction of the source edge** (`P3-46`): `Facing.ALONG`,
  `AGAINST`, or `EITHER` — the default, and every table pin and the tables themselves use it. A
  direction the profile has no state for falls back to either. `verify_road_graph.gd`'s same-edge check pins
  both seeds on a two-way edge; `Hit.along` is what the fare passes.
