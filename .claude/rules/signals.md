---
paths:
  - "etl/pipeline/signals.py"
  - "etl/pipeline/config_blocks/signals.py"
  - "etl/tests/test_signals.py"
  - "game/scripts/traffic/signal_plan.gd"
  - "game/scripts/traffic/signal_controller.gd"
  - "game/scripts/traffic/signal_heads.gd"
  - "game/assets/shaders/signal_head.gdshader"
  - "game/tuning/signal_heads.tres"
  - "tools/make_signal_heads.py"
  - "game/scripts/traffic/signal_plan_profile.gd"
  - "game/tools/verify_signals.gd"
  - "game/tuning/signal_plan.tres"
  - "game/scripts/traffic/traffic_system.gd"
  - "game/scripts/traffic/traffic_profile.gd"
  - "game/tools/verify_traffic.gd"
  - "game/tuning/traffic.tres"
---

# The signal plan, its controller and the traffic — before marking work done

- **`pipeline/signals.py`, the `signals` block, `surface.py`'s `junctions` key, or
  `roadmarks.transverse_host`: paste the stage's `signals:` line for BOTH regions, before and
  after** (`P3-3a`, `Q173`) — the two partitions (stop lines → no host / off axis / dead end /
  hosted; junctions → staged / at the seam / not owned / no approach), the approaches with their own
  stop line, and the stages histogram — and the heads' two partitions (features → refused / on
  structure / empty / admitted; posts → no host / dead end / hosted) with the junctions by witness
  (bar / heads / both). Wan Chai 120 bars + 514 head posts → 72 staged of 73, 178 approaches;
  Causeway Bay 15 + 89 → 21 of 22, 41. 🔴 **A head is a second witness, not a second rule**
  (`Q173`, 2026-10-30): it signals a junction by the bar's own host rule (the nearest level-0
  edge's nearer node, as its cluster) — TD's `RM1011` survey is about half its light estate. Do
  not add a posts floor or a radius to "clean up" lone-head junctions. 🔴 **`RM1011` is the signal stop line BY MEASUREMENT** (115 of 120 within 15 m of a
  head; `RM1012` / `RM1013` p50 52 / 46 m): do not add a give-way or STOP-sign code to
  `stop_line_codes`. 🔴 **The junction is `surface.py`'s stub cluster or a lone node — no radius**
  (`Q72`: 15 / 25 / 35 m give 297 / 240 / 202 junctions, no plateau). 🔴 **The host fixes the
  JUNCTION, never the approach**: 68 of 120 stop lines cross no centreline and the host is often
  the edge LEAVING the junction, so the approaches are every level-0 edge entering it, stopped at
  `trim_m`. Do not "fix" an approach to the host edge. 🔴 **The stop moves BACK only** (`own_stop`,
  `Q173`): to the approach's own square bar, else a crossing's near edge, within its corridor, its
  nearside half and the mouth's half of the edge — paste `stops by source` and `moved back` for
  both regions. Mutations caught by name: either side on a two-way road, no squareness, no floor,
  no mouth cap, a crossing beating a bar, the farthest line winning. ⚠️ **`axis_tolerance_deg` is the one free
  value and it is authored** — sweep it and paste the stages table (`hong_kong.yaml` has 20 / 30 /
  45). ⚠️ A junction a neighbour's edge reaches is refused (`at_seam`, 1 on Wan Chai): its
  approaches are split across two bundles.
- **The heads (`P3-3e`): `bind_heads`, `signals.heads` (`outset_m`, `max_shift_m`, `library`,
  `drawing`), `make_signal_heads.py`, `signal_heads.gd`, `signal_head.gdshader`,
  `signal_heads.tres`: paste the stage's `bound` clause for both regions, and `verify_signals`'
  `heads:` lines** (Wan Chai 276 + 92 bound, every stage shown at 56 of 72; Causeway Bay 40 + 24,
  14 of 21). 🔴 **The binding is the kerb's side, never `ANGLE` or the code** (`Q76`): one-way or
  nearside means along the edge, `signs.facing_from_side`'s rule. 🔴 **Never a dark head**: an
  entry the plan does not hold at its own junction and stage is refused and counted, never drawn.
  🔴 **The circuit is `UV.x`** — the Compatibility renderer reads `COLOR_0` alpha as 0; a shader
  change owes a frame on BOTH renderers (`GODOT=` a wrapper adding `--rendering-method
  gl_compatibility`) and the `shader error` grep. ⚠️ Lit by day: the emission does not multiply
  `night_lights`. ⚠️ A drawing change is `python tools/make_signal_heads.py`,
  `test_make_signal_heads.py` (byte-identical), and a forced reimport before any frame. Mutations
  caught by name (2026-10-30): the side flipped, no stage check, the half flipped, no stub refusal,
  always registering, the facing unturned; and in the layer, no write on change, a clamped datum,
  the stage check inverted, grouping without the stage.
- **`signal_controller.gd`, `signal_plan.gd`, `signal_plan.tres` or `verify_signals.gd`: run
  `tools/check.sh` and paste `verify_signals`' `plan:` line for both regions.** 🔴 **The timeline is
  a pure function of the clock** (`light_at`): no state may depend on what was asked before, or
  the tool's walk stops being the controller. 🔴 **The conflict check is graded on a junction
  built to fail it** (`_check_the_checker`); mutation-check the tool rather than reading its pass —
  `light_at` returning GREEN outside its slot, and `along` flipped in `SignalPlan.add_region`, both
  fail it by name (2026-10-29). ⚠️ `CONFLICT_DEG` (45) checks the ETL's result and is not its
  tolerance; do not tie the two. ⚠️ **Every timing is authored** (`signal_plan.md`): TD publishes
  none, and red-and-amber 2 s / amber 3 s are the British values, TD's own unread.
- **`traffic_system.gd`, `traffic.tres` or `verify_traffic.gd`: run `tools/check.sh`, paste
  `verify_traffic`'s three `lights:` lines and its `lane:` line, and a throttle-route `draws` /
  `phys` with and without `--traffic=off`** (`P3-3c`; 24 cars: +7 draws, ~+1 ms). 🔴 **A car moves
  only by `RoadRouter.moves_from` under `Profile.legal()`** — never a second successor rule.
  🔴 **Amber is judged at `brake_max_mps2`, TO THE LINE** (`to_stop + STOP_SHORT_M`): at the planned
  rate a braking car rode its own judgement into the red, and to the aim point a crawling car met
  the red a hair short (seed 4, which `SEEDS` keeps). Mutation-check rather than reading a pass:
  red never stopping, no path reading and an illegal move each fail by name (2026-10-29).
  🔴 **A car gives way at its line** (`_give_way_gap`, `Q173` 2026-11-04): keep clear, then a car in
  the junction, then a free car coming that ranks first (straight, left, right, then id). Its
  deadlock argument is in `Q173` — a car in the junction never gives way, and a wait on a coming
  car is only on one held by nothing; keep both. Paste the `crossing:` and `give way:` lines for
  both regions: signalled is gated at 0, unsignalled is printed (curve sweeps over a road outside
  the junction, simultaneous commits). ⚠️ A car clearing the last junction is NOT excused its next
  line (`_past_stopping`, not `committed`). Mutations: the rule off, and `committed` without the
  just-joined tail, each fail by name. ⚠️ A long Causeway Bay stand is a keep-clear chain ending at
  a parked pinch; do not shorten `give_way_look_m` or the keep-clear room to clear it.
  ⚠️ `_lane_centre` rounds an interior vertex (`_bent_dir`): off the segment perpendicular alone a
  lane jumps `o·√2` there (4.64 m on edge 904) — the probe is the largest move over a 0.05 m step.
  ⚠️ `lane_at` and `Hit.lane_centre` share `RoadGraph._lane_centre`; the `lane:` line holds them
  together. 🔴 **A parked vehicle is a car ahead that never moves** (`P3-3f1`), read off each
  region's `ParkedLayer` (`is_standing`, never a second roster) — paste `verify_traffic`'s `parked:`
  table and its per-drive `parked:` lines, and mutation-check by switching `_nearest_parked`'s
  match off (2,429–4,811 car-ticks inside). ⚠️ **Over the centre line only on a give-way**: the free
  drive need not meet it (Wan Chai's alone never does), so `give way:` STAGES it — removing
  `_oncoming_clear` or `_coming_over` each fails it by name. ⚠️ The overlap tolerance (`INSIDE_M`
  0.15) is measured on one right-angle corner (0.086 / 0.13 m, a car's heading snapping at a vertex); do not raise it to clear a new overlap — probe
  the car's lane, the footprint's corners and the bend. ⚠️ A long stand behind a parked vehicle is
  the roster's pinch (a car honestly too wide); `side_clear_m` is not lowered to clear one.
  🔴 **`near_cars` is what the near miss reads** (`Q175`): a live car's own pose and real velocity,
  out to the disc plus `speed × look_s`; `verify_traffic`'s `near:` lines. ⚠️ `FareSystem` finds the
  system by `GROUP`, joined at the end of `setup`, so `--traffic=off` leaves none.
  🔴 **A turn runs mouth to mouth** (`trim_m`, city schema 41) and a stub is crossed,
  never driven — `verify_traffic`'s `graph:` stub line; do not go back to a span round the node
  (the user's report, 2026-10-29). 🔴 **The lane is the turn's** (left nearside, right offside),
  and a lane change looks first: two cars side by side are passed, not queued, and a change into a
  car beside fails `queue:` (seed 7). ⚠️ The lamp bits ride `INSTANCE_CUSTOM.a` above the livery
  bit; a shader change owes a day and a night frame and the `shader error` grep. 8 / 16 are the
  indicators (`P3-3f2`): paste both `wink:` lines (the second: still winking as a turn joins,
  `wink_hold_m`); the beat is `vehicle_lamps.tres`' via `wire_blink`, never
  a shader default.
- **`TrafficSystem` is split by concern** (`P3-3c`, `Q187`): `TrafficTurns` (static turn
  geometry), `TrafficHorns`, `TrafficFleetMix`, `TrafficRouted` and `TrafficKerbside`, each owned
  by the system and reading it back. 🔴 **A stream moves with its owner and keeps its seed and draw
  order**; a change that moves a draw between pieces moves every later car. A refactor here is
  gated on `verify_traffic` byte-identical on both regions, not on its pass.
- **The routed fleet** (`P3-78`): the three seeds drive the wandering cars alone and a fourth drive
  adds the buses — its rules are `busroutes.md`'s. ⚠️ The wandering fleet alone meets in a
  signalled junction on seeds 1, 2 and 8 (two merges, `Q182`); the gate holds on 7 / 4 / 23 only.
- **The taxis** (`Q183`): `verify_traffic`'s `licence:` lines — paste them. 🔴 **A taxi's licence
  and roof sign come off its id and spawn count, never `_rng`**: one more roll moves every later
  car and every seed's staged case. 🔴 **One slot per licence per taxi, the rest hidden** — a
  `MultiMesh`'s `instance_count` clears its buffer, so a taxi cannot be moved between batches after
  `setup`. The roof sign is bit 32 (`ROOF_SIGN`) at `vehicle_lamps.tres`' `sign_lit` through
  `wire_blink`; a shader change owes a day and a night frame and the `shader error` grep.
  ⚠️ A car still clearing the last junction within `give_way_look_m` of its next line carries BOTH
  turns in `_turn_path` (`Q183`): seed 7's minibus on a short link turned right across a left turn
  when it carried only the turn behind it.
- **The hours** (`Q186`): `kinds` by clock hour and `fleet_by_hour` are TD's census, printed by
  `tools/traffic_census.py` — 🔴 **never edited by hand, never retuned for the look without the
  user's call**: rerun the tool. Paste `verify_traffic`'s `hours:` lines. 🔴 **A respawn's kind
  comes off its id and lives (`TrafficFleetMix.kind_for`), never `_rng`**; the first life keeps `setup`'s draw so
  that roll is unchanged. 🔴 **The fleet changes only by the ring**: nothing is removed for the
  hour, so no car pops in view; `cars` is the busiest hour's fleet and the ceiling. ⚠️ Every
  wandering car holds a slot in every kind the hours draw and every licence: a kind added to
  `kinds` adds a hidden instance per car to every batch. ⚠️ The seeds drive at `PEAK_HOUR` 12:00,
  the whole fleet; at 07:00 they would drive 19 cars and every staged case would move.
- **The player's red** (`P3-3d`): `SignalController.observe` and `StopLine.crossed_by`. 🔴 **Counted,
  never paid or docked** until the user calls it a bonus or a penalty — do not wire it to
  `FareSystem` on a guess. ⚠️ The taxi's MIDDLE crosses, not its nose: a car stopped nose-over
  has not run the red. ⚠️ The line is `width_of` (published) wide, not the drawn ribbon. Mutations:
  counting green, and crossing either way, fail `watch:` by name (2026-10-29).
- **The horn** (`Q178`, `Q185`): `verify_traffic`'s `horn:` lines, and `tools/make_vehicle_sounds.py` is byte-identical. 🔴 **A pattern draws on `TrafficHorns`' own `_rng`, never the traffic's `_rng`** — one more roll there moves every later car; `react:` checks `_rng.state` unmoved. A kind with no `horn_<kind>.wav` sounds `HORN_FALLBACK_KIND`'s; a new kind owes a file (`test_every_kind_the_traffic_draws_has_its_own_horn`). ⚠️ A cross car's draws are judged on the MEAN press: a total-held check missed an untempered press length, since a cross car also presses more often. (`test_make_sounds.py`)
  🔴 **A red does not count towards the wait.** 🔴 **Silent while the taxi is
  `parked`**: `verify_traffic` cannot see this, so a change near it owes a `--menu=on` run. ⚠️ A car's
  pitch comes from its id: a roll would move every later car on the seeded RNG. ⚠️ The taxi's gap is
  `_taxi_gap`, apart from `_gap_ahead` only so that `Held.TAXI` can name it. 🔴 **`react_to` answers the
  loop's awards whatever the car's wait**: a close call by `Award.passed` (by reference, never by id), a
  docked hit by `_taxi_gap` and `_struck`; `verify_traffic`'s `react:` lines. The loop is found by
  `FareSystem.GROUP`, so `--fares=off` draws none.
- **The knock** (`Q180`): `verify_traffic`'s `knock:` lines, in both regions. 🔴 **A knocked car is
  an obstacle at any heading** in `_gap_ahead` and is skipped by every rule that reads a car's lane
  (`_oncoming_clear`, `_lane_blocked`, `_give_way_gap`, `_queued_past_join`): its lane is where it
  WAS. Once still it is a `Parked` footprint (`_stand_wreck`), which the pass-a-parked rules read.
  🔴 **It never reverses to recover** (`recover_heading_deg`), and it looks only for cars under
  way — one queued behind it would hold it for ever; the swept curve stops it on any body. ⚠️ A
  staged `TrafficSystem` in a verify tool leaves the tree with `free()`, not `queue_free()`: a
  script runs in one frame and a later check finds the first system in `GROUP`.
