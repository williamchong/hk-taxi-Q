---
paths:
  - "game/scripts/vehicle/vehicle_controller.gd"
  - "game/scripts/vehicle/handling_profile.gd"
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
---

# Handling and the drift — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- Handling changes — `VehicleController`'s drive model, `HandlingProfile` or `handling.tres`: also
  `tools/skidpad.sh`, before **and** after, and paste both tables. It grades rather than checks, so
  `check.sh` cannot and should not run it. ⚠️ Run the **wrapper**, never `skidpad_ablation.gd`
  directly — Godot exits `0` on a parse error, so only the wrapper's exit code means anything.
  ⚠️ Measure on `skidpad.tscn`, never `city_drive.tscn` — a 0.14° micro-gradient there is worth the
  whole quantity under test, and a published figure has already had to be withdrawn over it
  (`P0-5b/c/d`).
  🔴 **A drift dial is graded on dwell (`longest`, `secs>thr`), never on landing peak slip on the
  threshold** — the game pays per second above it (`Q84`) — with the peak and the exit speed as the
  guard against a spin.
  ⚠️ **And the skidpad cannot settle a drift value on its own — drive it too.** An open pad has no
  far kerb, so 65.7° of peak slip reads as a healthy angle there and was `086° → 219°` and a railing
  across the carriageway on Expo Drive (`Q86`). It is not a licence to *measure* in
  `city_drive.tscn`; the numbers still come from the pad and the drive is a veto.
  ⚠️ **Sweep with `tools/skidpad.sh --sweep=<field>=<v,…>`, not by editing a `.tres` in a shell
  loop.** One such loop blanked the field it was sweeping and published a table of all-zero rows that
  read like a finding; the flag exists so that cannot happen again.
  🔴 **Grade anything speed-dependent at 42, 63 and 86 kph (`--entry-kph=`), because one entry speed
  is the tool's blind spot** — a yaw assist tuned at 63 and applied at 84 spun the car for a whole
  release with a green `check.sh` and five clean rows (`Q87`); rows compare only *within* one entry.
  🔴 **A static sweep of a speed-dependent dial gives an upper bound on a fix, never an estimate**:
  the car slows inside a drift and crosses the band under it (`Q88`). Sweep the band's own dials.
  The engine-tyre car's grip-cut and yaw-torque drift (`Q84`–`Q89`) went with the control car on
  2026-10-05; those Qs keep its lessons.
- 🔴 **`hold`'s driver commands a SHARE of the lock, so a steering-lock change re-tunes the driver,
  not the car** (`Q152`, the `slide_lock_deg` sweep in `systems/arcade_aids.md`): a wider lock while sliding read as
  a SHORTER `hold` at every speed, because three quarters of 35° is a straightening where three
  quarters of 14° was a catch. Its 20° target was itself set by the old lock. Grade a lock change on
  the user's own drive, and never read `hold` as evidence that a lock is too narrow or too wide.
- ⚠️ **`--only=catch` grades the CATCH, and reads two things a countersteer can do** (`Q152`, the
  street report of 2026-09-30): `snap` is the slip the other way after full opposite lock, and
  `yaw@hold` the heading swept while it was held. Neither car snaps — under 0.4° at every timing,
  early, at the peak or late, throttle held or lifted. Both TURN the other way once caught: full
  lock on gripping tyres sweeps 50–70° the other way inside the next 0.7 s of a 1.5 s hold, about
  85°/s, on the shipped car and the spike alike. A keyboard holds full lock for as long as the key
  is down, so this is what "the countersteer turns the car the other way" is; read `yaw@hold`, not
  `snap`, before reaching for a tyre dial — the shipped car does it too, so the tyre table is not
  the lever.
  ⚠️ Its timing columns (`to lock`, `settled`, `turns`, `wheel@turn`) say which half of the
  steering turns the car: held throttle turns at full lock, lifted before it (`Q152`'s timing
  round). A lever keyed on the slip falling back is late — the heading reverses first.
  🔴 **`catch_lock_deg` is graded on `catch`'s `yaw@hold` and `settled`, never on `hold`**
  (`Q152`'s catch cap round): `hold`'s driver never turns the car the other way, so the row is
  byte-identical with the cap set and says nothing about it. `wheel` and `to lock` read
  `steer_ratio`, the player's input, which the cap leaves alone — `fronts@off` reads the front
  wheels, `capped` when the cap engaged. The row runs to the end of its hold now, so its exit and
  `+0.5 s` do not compare with a table from before 2026-09-30. ⚠️ A countersteer latch keyed on
  the slip alone takes a turn-in plough for a slide: latch on tail out (yaw and countersteer sign
  disagree), and grade a latch change on the tap at 42 kph.
- ⚠️ **`--only=liftoff` grades a technique's DIRECTION against `corner`, its control** (`Q153`):
  read the windows around the lift, never a 4 s total — a coasting car slows and turns tighter
  for that alone, which read as a +132° pivot on the totals and is about the shipped car's tuck on
  the windows. 🔴 **`mu`, gravity, `engine_force` and `handbrake.torque_nm` move together** (`Q153`,
  2026-10-05): the two torques are sized to what the tyre can answer, and a grip or a weight change
  under the old torques spun every tap (168°) where no stability dial helped. 🔴 **A real taxi is
  the baseline** (the user's call): physical numbers are a Crown Comfort's, and gameplay is layered
  on top as an aid, never by bending one. `engine_force` is the car's whole drive, split across
  the driven wheels (`drive_scale`, which multiplied a per-wheel copy, is gone). The power-on corner's lever is
  `stability_control.understeer_power_cut` (`P3-55`), graded on `corner` across five entries — full lock runs to a TERMINAL speed, so one
  entry reads a transient — and on the pull-away from `--entry-kph=10`; `hold` and `ride` cannot
  see it while drift mode is engaged, and only their exits move.
- ⚠️ **`--only=technique` grades `P3-54`'s three techniques on DIRECTION, each against a control
  that differs by its input alone** (`Q153`): `flick@held` / `@lift` and `handbrake@held` / `@lift`
  against `corner`, `trailbrake` against `turnin` — the same steering and the same throttle after
  0.6 s, no brake. 🔴 Never grade the brake against `corner`: a car that sheds speed turns tighter
  for that alone, so read slip and turn rate in `+0.00..+0.50`, never radius. The windows run from
  each row's own input (the feint's end, the press, the brake), and the control is re-read at that
  same second, so `corner` prints different numbers under the flick and the handbrake. The flick at
  42 kph is recorded, not graded (a real car rarely flicks on tarmac that slowly). Graded
  2026-10-05: no flick on either car, the trail-brake ploughs at 42, the held handbrake swings
  after 0.5 s, and handbrake-and-lift at 86 spins with the assist off — a tyre dial aimed at one
  of these is read on its row and guarded by `corner`, `tap` and `turn`. ⚠️ Its last three
  columns are the tyre car's own (`wheel_slips`, `wheel_loads_n`): each axle's most-used tyre in
  multiples of its peak, and the rear load's swing. The fronts sit at their peak in a plain corner
  from 63 kph while the rears use about half of theirs, so a dial that "frees the rear" can read
  as nothing on the flick — read `rear use` before blaming the dial. ⚠️ It is COMBINED slip: a
  rear over 1.0 at 2° of slip is wheelspin, not the side letting go (`Q153`'s step 2).
- 🔴 **`--sweep` refuses a field the car reads once, in `_ready`** (`READY_ONLY_FIELDS`:
  `gravity_scale`, `centre_of_mass_offset_y`, the suspension, `wheel_radius_m`)
  — set live they moved nothing and printed identical rows under distinct labels. Sweep the body
  instead: `--sweep=body.center_of_mass_y|center_of_mass_z|gravity_scale=…` writes the rigid body
  live (`P3-54`). A probe only; a value worth keeping goes into `handling.tres`.
- ⚠️ **A flick engages drift mode like the button** (`FlickWatch`, `flick_*` in
  `systems/arcade_aids.tres`, `P3-54`): a lifted or braked feint, then the steering across within
  `flick_window_s`. Grade a change to it with `--sweep=arcade_aids.flick_window_s=0,<v>` on the full pad —
  0 is the car without it, so every row but the flick's must read the same at both values. 🔴
  Anything that adds a steering reversal with the throttle lifted to a pad row (a new driver, a
  lifted catch) now reaches it, unless traction control is already off there — it never fires
  then. `--catch-lift` was not run in the round that built it.
- ⚠️ **`--only=turn` grades the street's 90° drift** (`Q153`, the user's street report): the tap,
  ended at 45° of heading three ways, reading `slide at` / `turned` (when the slip first reaches
  the threshold, and how far the car had turned by then) and `came out`, the heading it settles on. The bar is
  80–110° settled at 42 and 63 kph. 🔴 A start bar that reads the PEAK passes a slide that begins
  after the corner is over (181° of heading at 42 kph before the cut) — read `slide at`.
  `drift_side_cut` and its band are graded here with `ride`'s peak as the guard (a cut right for
  42 kph spins the car at 63); `stability_control.slip_power_cut_*` on `ride`'s peak across 42–86 kph with `hold`
  as the guard; `drift_mode.rearm_on_steer_release` on the settled heading and on `hold`, which a re-arm on a
  steering REVERSAL kills. Refused, each measured: a locked handbrake (`handbrake_declutch`),
  every tyre dial at 42 kph. ⚠️ A lower `mu` was refused at 2.0's drive and shipped with the
  drive and handbrake rescaled (`mu` 1.0, `Q153`, 2026-10-05) — the `turn` let go then fails (136 /
  220° at 42 / 63 kph), owed.
- ⚠️ **`--only=wall` grades a penalty bar, not a handling dial** (`P3-50`, `Q148`): the tool
  stands a slab across the path at `--wall-deg` (10, 30, 90 by default) and reports `approach`,
  its own reading of the speed into the face on the tick before contact, beside `impact`, the
  controller's `take_impact_mps` latch, which is the number the game docks on — the two must
  agree, and they do to the hundredth on every row. Run it at 4, 6 and 8 s like anything speed
  dependent; `skills.md` quotes the matrix the bars were read from. ⚠️ **The latch reads
  `_velocity_into_step`**, the velocity at the end of `_physics_process`, because by
  `_integrate_forces` the solver has already removed the normal velocity — off the state a 69.5
  kph head-on read 1.6 kph and a 30° hit read nothing, the state already separating. 🔴 **The slide
  reads the same velocity** (`Q151`): off the state a 30° clip read as already separating and the
  arcade `collision_speed_retained` / `collision_deflection` response never ran — the car stopped
  DEAD at 30° and 90° while only the 10° brush kept its speed. Fixed 2026-09-29: exit on the clip
  0.09 → 28.8 / 51.3 / 76.2 kph at the three run-ups, the brush 34.5 → 57.1, the head-on a stop by
  construction. Anything new in `_integrate_forces` reads `_velocity_into_step`, never the state.
  ⚠️ The wall rows are noisy where the drift rows are not (the brush's exit moved 0.5 kph and a
  head-on's tick count 3 → 2 between two runs of one HEAD): grade a wall change against that band.
  🚫 Left: the scrub after a clip — on the street a 40 kph clip still rests within a second with
  the nose on the face. The lever is a yaw-away or a tyre-grip term while a wall contact is live,
  graded on the clip rows and the drive; `collision_deflection` scales only the first tick.
- ⚠️ **`drift_slip_threshold_deg` has a consumer since `P3-49`**: the fare's drift skill pays
  `SkillProfile.drift_hkd` per `drift_s` the slip holds at or over it past `drift_min_s` (`Q145`), so the number the
  skidpad's `secs>thr` column grades is now the number the game pays on. It stays a design target
  (`Q84`): a slide that should pay is answered on the grip dials against dwell, never by lowering
  the threshold — and the game's slip (`FareSystem.slip_deg_of`) is a deliberate second copy of
  the ablation's, so a change to the flattening or the 1 m/s floor is made in both.
- 🔴 **The car's dials are its systems, one table each under `game/tuning/systems/`** (`Q155`):
  traction control, stability control, drift mode, the countersteer assist, the handbrake, the rev
  limiter — real cars' — and `arcade_aids`, the game's own (the side cut, the flick, the catch
  limiter, the slide lock), never filed under a real system. `tyre.tres` is the tyre alone. A new
  dial goes in the system it belongs to, and an aid no real car has goes in `arcade_aids`; the old
  names are in `Q155`'s rename map. Each table is assigned on `taxi_tyre.tscn` by path, and
  `verify_vehicle.gd` refuses any other.
- 🔴 **The tyre car (`P3-52`, `Q152`) is the game's car since 2026-10-03 and the only car since
  2026-10-05**, graded on `skidpad.tscn` — `tools/skidpad.sh --entry-kph=63` (and 42, 86) — and
  driven with a plain `drive.sh`: `city_drive.tscn` instances `taxi_tyre.tscn`, and
  `verify_vehicle.gd` refuses it any other car (`--tyres=` fits a trial table). "The shipped car"
  in a note written before 2026-10-03 is `taxi.tscn` on the engine's tyres, the pad's control until
  it was dropped; its grip and yaw drift went with it, so `handling.tres` holds no drift dial but
  the button's ramp (`drift_attack_s`, `drift_release_s`) and the threshold. Compare two
  configurations at one `--entry-kph`, never one `--run-up`: two drives reach two speeds in the
  same seconds. `--sweep` reaches `TyreProfile` fields, and a system's as `<system>.<field>`
  (`Q155`); a drift_* field sweeps only the drift rows.
  🔴 **`hold`'s driver is the harness's, never the car's** (`Q72`): it plays the human, and both
  cars get the same one. `longest` is the unbroken dwell the fare's drift pays on (`drift_min_s`);
  `secs>thr` sums every run. ⚠️ `hold` on the spike carries ±0.3 s run to run at one
  configuration (`Q152`; three serial runs were byte-identical on 2026-10-02, `Q153` — run the
  repeats anyway). 🔴 **Anything new in the spin step is solved, never stepped**: explicit, a braked
  wheel past the curve's peak limit-cycled; clamped at zero slip, the drive could not carry the rim
  past the road. 🔴 **Where the sideways force goes in is a drift dial** (`TyreProfile.side_force_depth`):
  at the contact the car rolled at a kerb, at the shipped 0.2 nothing slides.
  🔴 **The drift assist is the player's option, default ON in the game and OFF on the pads
  (`P3-56`)** — `countersteer_assist.gain` and `stability_control.assisted_slip_cut_from_deg` act only while
  `TyreVehicleController.drift_assist` is true (`DriftAssist`: `--assist=`, the saved option, on).
  Grade a drift change in BOTH modes: off on `ride` AND `hold` (`ride` the player's plain input,
  `hold` a player who countersteers), on with `tools/skidpad.sh --assist=on` on `ride`, `turn` and
  `hold`. `turn` must read the same in both: the assist steps aside the moment the player lets go
  or countersteers, and an assist that did not brought the 90° turn out at 58°. `hold` must too:
  after a countersteer the assist stays aside until the slide is over (`CountersteerAssist.yields`); re-tested
  each tick it stepped back in at every zero crossing of the feathering driver, 0.27 s. ⚠️ At
  86 kph `hold` sits on its own cliff (about 3.1 s to 83 kph, about 1.4 from 90, both modes) —
  compare the modes across 76–95 kph before reading one cell there as a fight. `drive.sh` pins `--assist=on`. ⚠️ `--sweep` refuses a field in both tables — the tyre dial was
  renamed `side_force_depth` after a shared `roll_influence` swept the wrong table silently.
- ⚠️ **`wall@30`'s exit wanders 28.4–31.7 kph across runs of one HEAD** at 63 kph (`Q152`),
  approach and impact identical to the hundredth — wider than `Q151`'s 0.5 kph. Grade a wall change
  against that band.

