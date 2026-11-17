---
paths:
  - "game/scripts/vehicle/vehicle_controller.gd"
  - "game/scripts/vehicle/handling_profile.gd"
  - "game/scripts/vehicle/car_spec.gd"
  - "game/scripts/vehicle/pace_profile.gd"
  - "game/tuning/pace.{tres,md}"
  - "game/tuning/cars/*.{tres,md}"
  - "game/tuning/handling.{tres,md}"
  - "tools/skidpad.sh"
  - "tools/skidpad_ablation.gd"
  - "game/scenes/dev/skidpad.{tscn,md}"
  - "game/scripts/vehicle/tyre_vehicle_controller.gd"
  - "game/scripts/vehicle/tyre_profile.gd"
  - "game/tuning/tyre.{tres,md}"
  - "game/scenes/vehicle/taxi_tyre.{tscn,md}"
  - "game/scripts/vehicle/systems/*.gd"
  - "game/tuning/systems/*.{tres,md}"
  - "game/tuning/touch.{tres,md}"
---

# Handling and the drift — before marking work done

**Any change to the drive model, a car table, a system table, `pace.tres`, `tyre.tres` or a drift
dial: `tools/skidpad.sh` before AND after, both tables pasted.** It grades, so `check.sh` does not
run it.

## Running the pad

- Run the wrapper, never `skidpad_ablation.gd` (Godot exits 0 on a parse error). Measure on
  `skidpad.tscn`, never `city_drive.tscn` (a 0.14° gradient there is worth the quantity under test).
- It runs `--fixed-fps 60`: about 5 s a pad, byte-identical run to run except the `us/tick`
  columns. Run 42, 63 and 86 kph (`--entry-kph=`) at once with `&` and `wait`.
- **Always re-run the before side.** Tables in a `Q` or sidecar were read under older slip, drive,
  pace or timing conventions and do not compare.
- **A drift dial is graded on dwell** (`longest`, `secs>thr`), never on landing peak slip on the
  threshold (`Q84`); peak and exit speed guard against a spin. `longest` cannot read past the 4 s
  window (`Q179`): a drift or tyre change also re-reads `--only=ride --entry-kph=20` and
  `--only=hold` at 76–95 kph with `--manoeuvre-s=30`.
- **The pad cannot settle a drift value alone — drive it** (`Q86`: 65.7° of peak slip read healthy
  on the pad and spun into a railing on Expo Drive). The drive is a veto; numbers come from the pad.
- **Grade anything speed-dependent at all three entries** (`Q87`), and compare rows only within one
  `--entry-kph` (never one `--run-up`). A static sweep of a speed-dependent dial is an upper bound
  (`Q88`): sweep the band's own dials.
- **`--sweep=<field>=<v,…>`**, never a shell loop over a `.tres`. It reaches handling, car and tyre
  fields bare, a system's as `<system>.<field>`, `pace.pace_scale`, and
  `body.center_of_mass_y|center_of_mass_z|gravity_scale`. It refuses a name in two tables and a
  field read once in `_ready` (`READY_ONLY_FIELDS`). A `drift_*` field sweeps the drift rows only.
- **`hold`'s driver is the harness's** (`Q72`) and commands a SHARE of the lock, so a lock change
  re-tunes the driver: grade a lock on the user's drive, never on `hold` (`Q152`). `hold` at 86 kph
  sits on a cliff — read 76–95 kph. Grade a drift change on `ride` (plain input) AND `hold`
  (countersteering).
- **A drive assist is tuned against a linear input** (`Q210`): keys are shaped by
  `keyboard_steer.tres` in `InputRouter.steer_for`; the pad steers as a key unless `--steer=analog`.
  A dial that moves on keys alone belongs in `keyboard_steer.tres`.

## Rows (`--only=`)

| Row | Grades | Read / trap |
|---|---|---|
| `catch` | a countersteer; `arcade_aids.catch_lock_deg` | `yaw@hold` and `settled`, never `snap` or `hold`. The car turns the other way under held full lock (about 85°/s); the tyre table is not the lever. A latch keyed on slip alone takes a plough for a slide: latch on tail out, grade on `tap` at 42 kph |
| `flick` | `keyboard_steer.attack_at_top_s` (`Q174`); `touch.steer_attack_at_top_s` with `--steer=touch` | `flick@held` at 95, 110, 120 kph; the three-entry pad is the guard |
| `liftoff` | a technique's direction against `corner` (`Q153`) | the windows round the lift, never a 4 s total |
| `technique` | flick and handbrake against `corner`, `trailbrake` against `turnin` | slip and turn rate in `+0.00..+0.50`, never radius; never the brake against `corner`. `rear use` over 1.0 at 2° slip is wheelspin (combined slip) |
| `turn` | the street's 90° drift: `arcade_aids.drift_side_cut`, `stability_control.yaw_brake_*`, `drift_mode.rearm_on_steer_release` | `slide at` / `turned` / `came out`, bar 80–110° settled at 42 and 63 kph. A bar on the PEAK passes a slide that starts after the corner. Guards: `ride`'s peak, `hold`'s `longest` |
| `ride`, `hold` | `stability_control.slip_power_cut_*` (ride's peak, hold the guard) | drift mode engaged hides `understeer_power_cut` |
| `corner` | `stability_control.understeer_power_cut` | five entries (full lock runs to a terminal speed) and the pull-away from `--entry-kph=10` |
| `wall` | a penalty bar (`skills.md`), `collision_*` | `impact` (the `take_impact_mps` latch) must equal `approach`. `--wall-deg` 10, 30, 90. `wall@30`'s exit wanders 28.4–31.7 kph at 63 |
| `traffic` | latch and slide against a moving body (`Q175`); six push rows (`Q180`) | `back20` above 0 means the moving-into-contact test is gone. Push rows match `J = (1 + e) · closing / (1/m + gives)`; a `collision_restitution` change re-reads them alone. `wall` must stay byte-identical |
| `brake` | `drive_fade_from_kph` / `drive_fade_curve` (`Q230`) | `entry` across `--run-up=2…20`; `hold` at 76–95 kph is the guard (the fade stands down in drift mode: applied there `hold` at 86 fell 3.57 → 1.02 s) |
| `bump` | `collision_align_s` on `brush30` | `yaw` is the face's 30° when right; under 0.3 s the car swings past the wall. The kerb and rut rows read nothing |

No pad row exists for `touch.steer_return_at_top_s`, `wheel_radius_px`, `wheel_hub_px`,
`spin_enter_deg`, `spin_lock_deg` (`Q238`, `Q243`): `verify_input.gd` holds the logic, the handset
grades the values.

## Where a number lives

- **`CarSpec`** (`tuning/cars/`, `Q156`): the maker's sheet, a Crown Comfort's — never a feel dial.
  A force the car's size decides is derived (`brake_g`, `handbrake.lock_ratio`,
  `suspension_max_load_ratio`, through `_wheel_load_at_rest_n`). `engine_force` is the whole drive,
  split across the driven wheels.
- **Systems** (`tuning/systems/`, `Q155`): a real car's system each in its own table; an aid no
  real car has goes in `arcade_aids`. `tyre.tres` is the tyre alone, `handling.tres` the game
  layer. `taxi_tyre.tscn` is the only car (`verify_vehicle.gd`); `drive.sh --tyres=` fits a trial
  tyre table.
- **Pace** (`pace.pace_scale`, `Q156`): the world's gravity with every force following. "Feels
  slow" or "wants grip" is this dial, never `mu`, `engine_force` or a boost. A speed-keyed dial
  reads `_car_kph()`, a speed floor takes `_pace_root()`, a system's clock steps `delta ×
  _pace_root()`. 60 Hz holds to pace 2.0, not 2.5 (`pace.md`).
- `mu`, gravity and `engine_force` move together (`Q153`): a grip change under the old torque spun
  every tap.

## Traps in the controller

- **The slip is the rear axle's** (`rear_axle_velocity`): at the centre of mass a gripping
  full-lock turn carried 15° and paid as a drift. A slip band under the tyre's 8° peak cuts a
  gripping corner.
- **Anything in `_integrate_forces` reads `_velocity_into_step`, never the state**: the solver has
  already removed the normal velocity (a 69.5 kph head-on read 1.6; a 30° clip stopped dead).
- The push goes in at the middle of the contact patch (`_contact_middle`).
- The drive is sized on each driven wheel's own rim speed (`_drive_force_at`).
- Anything new in the spin step is solved, never stepped. `TyreProfile.side_force_depth` is a drift
  dial.
- `drift_slip_threshold_deg` is what the fare pays on and a design target (`Q84`): never lower it
  to make a slide pay. `SlipAngle` duplicates the ablation's `_slip_deg` on purpose; change both.
- A flick stands traction control down (`FlickWatch`). Grade with
  `--sweep=arcade_aids.flick_window_s=0,<v>`: every row but the flick's reads the same. A new pad
  row with a lifted steering reversal triggers it.

## Measured shut, and open

- `understeer_power_cut` is not re-keyed on a yaw-rate deficit (bands overlap: 85–90% holding
  against 70–86% ploughing), and traction control is not put on combined slip (0.82 / 0.73 / 0.63 g
  against 0.91 / 0.85 / 0.72 at 63 / 86 / 105 kph; pull-away 26.9 against 30.8 kph) — `Q153`.
- `drift_side_cut` 0 was tried and kept (59° at 42 kph). A locked handbrake
  and every tyre dial at 42 kph were refused on `turn`.
- Gone: the engine-tyre control car, the drift assist (`P3-56`), the drive boost.
- Open: `turn`'s let-go at `mu` 1.0 (136 / 220° at 42 / 63 kph); `turn@off` at 63 (118°); the
  lifted handbrake in a turn at 63 / 86; the scrub after a wall clip; `flick@lift` barely brings
  the tail round (3.7 / 19.2 / 9.3° at 42 / 63 / 86); `--catch-lift` ungraded; `bump@post` is a
  dead stop; a limited-slip differential is deferred, not refused.
