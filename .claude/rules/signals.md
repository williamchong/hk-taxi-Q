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

Mutation-check a new assertion; a seeded drive not meant to move stays byte-identical in both
regions (diff the whole `verify_traffic` output).

## The ETL stage — `signals.py`, the `signals` block, `surface.py`'s `junctions`, `roadmarks.transverse_host`

Paste the stage's `signals:` line for both regions, before and after (`P3-3a`, `Q173`), with
`stops by source` and `moved back`.

- **`RM1011` is the signal stop line by measurement** (115 of 120 within 15 m of a head; `RM1012`
  / `RM1013` p50 52 / 46 m): no give-way or STOP code in `stop_line_codes`.
- **The junction is `surface.py`'s stub cluster or a lone node — no radius** (`Q72`: 15 / 25 / 35 m
  give 297 / 240 / 202 junctions, no plateau).
- **The host fixes the JUNCTION, never the approach**: 68 of 120 stop lines cross no centreline, so
  the approaches are every level-0 edge entering it, stopped at `trim_m`.
- **A head is a second witness, not a second rule** (`Q173`): it signals a junction by the bar's own
  host rule. No posts floor or radius to clean up lone-head junctions.
- **The stop moves BACK only** (`own_stop`): to the approach's own square bar, else a crossing's
  near edge.
- `axis_tolerance_deg` is the one free value and is authored: sweep it and paste the stages table.
- A junction a neighbour's edge reaches is refused (`at_seam`).

## The heads (`P3-3e`) — `bind_heads`, `signals.heads`, `make_signal_heads.py`, the head scripts and shader

Paste the stage's `bound` clause for both regions and `verify_signals`' `heads:` lines.

- **The binding is the kerb's side, never `ANGLE` or the code** (`Q76`, `signs.facing_from_side`).
- **Never a dark head**: an entry the plan does not hold at its junction and stage is refused and
  counted.
- **The circuit is `UV.x`** (`Q226`: Compatibility read `COLOR_0` alpha as 0; a batch with custom
  data owes a white instance colour). A shader change owes a frame on BOTH renderers (`GODOT=` a
  wrapper adding `--rendering-method gl_compatibility`) and `grep -i "shader error"`.
- Lit by day: the emission does not multiply `night_lights`.
- A drawing change is `python tools/make_signal_heads.py`, `test_make_signal_heads.py`
  (byte-identical) and a forced reimport before any frame.

## The plan and controller

`tools/check.sh`, and `verify_signals`' `plan:` line for both regions.

- **The timeline is a pure function of the clock** (`light_at`).
- The conflict check is graded on a junction built to fail it (`_check_the_checker`).
  `CONFLICT_DEG` checks the ETL's result and is not its tolerance; do not tie them.
- Every timing is authored (`signal_plan.md`): TD publishes none.
- **The player's red** (`P3-3d`: `SignalController.observe`, `StopLine.crossed_by`, `watch:`) is
  counted, never paid or docked until the user says which. The taxi's MIDDLE crosses; the line is
  `width_of` wide.

## The traffic

`tools/check.sh`; paste the `verify_traffic` lines named below for both regions, and a
throttle-route `draws` / `phys` with and without `--traffic=off`. A fleet-size or thinning change
also owes `game/tools/bench_traffic.gd --cars=40,60,80` with and without `--view=on` (a
measurement, not a gate).

- **A car moves only by `RoadRouter.moves_from` under `Profile.legal()`.**
- **RNG discipline**: one more roll on the traffic's `_rng` moves every later car and staged case.
  A taxi's licence and roof sign, a respawn's kind (`TrafficFleetMix.kind_for`) and a horn's pitch
  come off the id; `TrafficHorns`, `TrafficRouted` and `TrafficKerbside` roll their own `_rng`. A
  refactor across the parts is gated on byte-identical output.
- **Seeds**: `SEEDS` 7 / 4 / 23 drive the wandering fleet alone at `PEAK_HOUR`; it meets in a
  signalled junction on seeds 1, 2 and 8 (`Q182`). The camera drive is seed 7, the routed drive
  seed 23 over `ROUTED_RUNS` (`busroutes.md`).
- **Do not retune to clear a stand or an overlap**: not `give_way_look_m` or the keep-clear room
  (a Causeway Bay stand is a keep-clear chain ending at a parked pinch), not `side_clear_m`, not
  `INSIDE_M` (measured on one right-angle corner, 0.086 / 0.13 m), not `spawn_clear_m`. Probe the
  car's lane, the footprint's corners and the bend. `cars = 80` fails Causeway Bay: lower `cars`.

By `verify_traffic` line:

- `lights:` — amber is judged at `brake_max_mps2`, TO THE LINE (`to_stop + STOP_SHORT_M`).
- `crossing:`, `give way:` (`_give_way_gap`, `Q173`) — keep clear, then a car in the junction, then
  a free car coming that ranks first. A car in the junction never gives way, and a wait on a coming
  car is only on one held by nothing: keep both (the deadlock argument). Signalled is gated at 0,
  unsignalled printed. A car clearing the last junction is not excused its next line
  (`_past_stopping`) and carries BOTH turns in `_turn_path`. Over the centre line only on a
  give-way, which the line stages (`_oncoming_clear`, `_coming_over`).
- `lane:` — `lane_at` and `Hit.lane_centre` share `RoadGraph._lane_centre` (`_bent_dir` rounds an
  interior vertex). A lane change is DRAWN turned (`Q244`, `Car.steer`, `drawn_pose`): the body,
  the instance and the beam take it, `car.pose` and every rule keep the road's heading, so the
  seeded drives do not move. Do not fold the steer into `pose`. A grade is drawn the same way
  (`Q258`, `Car.pitch`), and a knock never folds it in: `_centre_of` reads the upright pose.
- `graph:` — a turn runs mouth to mouth (`trim_m`); a stub is crossed, never driven. The second
  witness (`_witness_move`, `Q267`) reads the graph, never the router: a check that asks
  `system.router` passes whatever the router dropped. `levels:` and `arcs:` say how much was off
  grade; the signal drives must take a ramp.
- `queue:` — the lane is the turn's (left nearside, right offside); a lane change needs room to
  stop from the closing speed (`_lane_blocked`, `_moving_onto`); a car ahead on its own edge is as
  far as the road says (`_leads_on_edge`).
- `parked:` — a parked vehicle is a car ahead that never moves, read off `ParkedLayer.is_standing`.
- `near:` — `near_cars` is what the near miss reads (`Q175`). `FareSystem` finds the system by
  `GROUP`, so `--traffic=off` leaves none.
- `wink:` — lamp bits ride `INSTANCE_CUSTOM.a` (8 / 16 indicators, 32 `ROOF_SIGN`, 64–256 the
  fade); the beat is `vehicle_lamps.tres`' through `wire_blink`. A shader change owes a day and a
  night frame and the `shader error` grep.
- `beams:` (`Q213`, `TrafficBeams`) — never a spot light (the 8-slot list is the taxi's,
  `beams.md`). A live car throws one beam, a parked vehicle none. A shader change owes a night
  frame against an oncoming car and a day frame.
- `view:` (`Q214`) — with no camera nothing is in view. Only the city hides a car
  (`CITY_COLLIDER_SUFFIX`). `spawn_seen_min_m` stays over the beams' `draw_m`. The `discard` is in
  the batched shader variant only; a change owes the forced dither frame (`fade_bits(0.5)`) on
  Mobile AND Compatibility.
- `thin:`, `spawn:` (`Q219`) — with no camera no car is thinned; a thinned car still moves and
  stops for a red; `thin_every = 1` is off. `_ids_near` hands cars in fleet order. The spawn's
  pick is one `_rng` roll over cumulative lane-metres (`_pick_spawn_edge`); a placement leaves the
  car behind room to stop (`_room_behind`).
- `licence:` (`Q183`, `Q200`) — a batch is sized once in `setup` and draws its first
  `visible_instance_count` (`_take_slot` / `_drop_slot`). Never hide a car at no size: it still
  costs its triangles.
- `hours:` (`Q186`, `Q198`) — `kinds` by hour and `fleet_by_hour` are TD's census, printed by
  `tools/traffic_census.py` (`traffic_census:` in the yaml): rerun it, never edit by hand. The
  fleet changes only by the ring; `cars` is the ceiling.
- `horn:`, `react:` (`Q178`, `Q185`) — a new kind owes a `horn_<kind>.wav`
  (`test_make_sounds.py`). A red does not count towards the wait. `react_to` answers a close call
  by `Award.passed` and a docked hit by `_taxi_gap`. Silent while the taxi is `parked`, which
  `verify_traffic` cannot see: owes a `--menu=on` run.
- `knock:` (`Q180`) — a knocked car is an obstacle at any heading and is skipped by every rule that
  reads a car's lane; once still it is a `Parked` footprint (`_stand_wreck`). It never reverses to
  recover.
- A staged `TrafficSystem` in a verify tool leaves with `free()`, not `queue_free()`.
