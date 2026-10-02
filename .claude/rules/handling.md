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
  - "game/scenes/dev/skidpad_tyre.{tscn,md}"
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
  🔴 **The drift dials are graded on OPPOSITE columns and there is no single rule for "the drift".**
  `drift_rear_grip_scale` is graded on `secs>thr` and never on `peak slip`, because the game pays per
  second above the threshold (`Q84`). The three yaw dials — `drift_yaw_torque_nm`, `drift_yaw_decay_s`,
  `drift_yaw_sustain` — are graded on **peak slip and exit speed**, and never on `secs>thr`, because
  that column was flat at 0.78–0.85 across all three of them while peak ran 40° → 130° (`Q86`). Tuning
  a yaw dial against dwell is tuning against a number it cannot move.
  ⚠️ **And the skidpad cannot settle a yaw value on its own — drive it too.** An open pad has no far
  kerb, so 65.7° of peak slip reads as a healthy angle there and is `086° → 219°` and a railing across
  the carriageway on Expo Drive. That is what rejected 9000 N⋅m (`Q86`). It is not a licence to
  *measure* in `city_drive.tscn`; the numbers still come from the pad and the drive is a veto.
  ⚠️ **Sweep with `tools/skidpad.sh --sweep=<field>=<v,…>`, not by editing `handling.tres` in a shell
  loop.** One such loop blanked the field it was sweeping and published a table of all-zero rows that
  read like a finding; the flag exists so that cannot happen again.
  🔴 **Grade anything speed-dependent at more than one `--run-up`, because the default entry speed is
  the tool's blind spot.** A fixed 63 kph entry is what makes every other column comparable across
  rows, and it is also why a yaw assist tuned at 63 and applied at 84 spun the car for a whole
  release with a green `check.sh` and five clean rows (`Q87`). 4 s → 63.02 kph, 6 s → 86.36, 8 s →
  105.47; rows compare only *within* one run-up, so quote `entry kph`.
  ⚠️ **The drift withdraws with speed and there are TWO envelopes, sharing a knee and not a top.**
  `drift_fade_from_kph` (65) is where both begin; the yaw is fully spent at `drift_yaw_fade_to_kph`
  (85), while `drift_rear_grip_scale` interpolates toward `drift_rear_grip_scale_at_top` all the way
  to `max_speed_kph`, because the grip value the car wants **moves** with speed (`Q88`). Above about
  100 kph the button is deliberately **inert**, which is the safe side of a cliff, not a bug.
  ⚠️ **There is a THIRD envelope below the knee** — `drift_rear_grip_scale_at_low` /
  `drift_low_fade_kph` (`Q89`) — which deepens the cut as speed falls, because down there the tyre
  never saturates and the drift was inert. The usable band is now **34–86 kph**.
  🔴 **The low branch LATCHES at engagement and the high branch TRACKS, and that asymmetry must not
  be "made consistent".** A drift scrubs speed, so deepening the cut as speed falls is positive
  feedback — built as a tracking taper first, it turned the design speed into a **165.0° spin**.
  Above the knee the same tracking is stabilising, because losing speed returns the scale to the
  tuned base. Latching *both* costs the high end (86 kph 50.4° → 20.6°).
  🔴 **The yaw assist cannot substitute for the grip cut at low speed**: at 42 kph peak slip *falls*
  4.2° → 3.6° as torque goes 0 → 20000 N⋅m, the top of its range, because with grip unbroken the
  rotation becomes a tighter line rather than a slide. Do not reach for a torque dial down there.
  **Grade a drift change at a low `--run-up` as well as a high one** — three consecutive changes
  checked "design speed byte-identical" without once asking what happens beneath it (`Q88`).
  🔴 **A static sweep of a speed-dependent grip dial gives an upper bound on a fix, never an
  estimate.** Held constant, 0.710 reads 44.9° at 105 kph; reached via the taper at that same entry
  speed it read **159.4°**, because the car decelerates below the knee inside the drift and the cut
  deepens underneath it. Sweep the taper dial itself (`Q88`).
- 🔴 **`hold`'s driver commands a SHARE of the lock, so a steering-lock change re-tunes the driver,
  not the car** (`Q152`, the `slide_lock_deg` sweep in `tyre.md`): a wider lock while sliding read as
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
  the windows. 🔴 `drive_scale` is not the power-on corner's lever: below 2.0 the spike's slide dies
  at 30–63 kph before the corner stops accelerating (`tyre.md`). The lever is `turn_drive_cut`
  (`P3-55`), graded on `corner` across five entries — full lock runs to a TERMINAL speed, so one
  entry reads a transient — and on the pull-away from `--entry-kph=10`; `hold` and `ride` cannot
  see it while traction control is disarmed, and only their exits move.
- ⚠️ **`--only=turn` grades the street's 90° drift** (`Q153`, the user's street report): the tap,
  ended at 45° of heading three ways, reading `slide at` / `turned` (when the slip first reaches
  the threshold, and how far the car had turned by then) and `came out`, the heading it settles on. The bar is
  80–110° settled at 42 and 63 kph. 🔴 A start bar that reads the PEAK passes a slide that begins
  after the corner is over (181° of heading at 42 kph before the cut) — read `slide at`.
  `drift_side_cut` and its band are graded here with `ride`'s peak as the guard (a cut right for
  42 kph spins the car at 63); `slide_drive_fade_*` on `ride`'s peak across 42–86 kph with `hold`
  as the guard; `rearm_on_steer_release` on the settled heading and on `hold`, which a re-arm on a
  steering REVERSAL kills. Refused, each measured: a lower `mu`, a locked handbrake
  (`handbrake_declutch`), every tyre dial at 42 kph.
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
- ⚠️ **The tyre-model spike (`P3-52`, `Q152`) is a second car, graded on its own pad** —
  `tools/skidpad.sh --scene=res://scenes/dev/skidpad_tyre.tscn --entry-kph=63` (and 42, 86), and
  driven with `drive.sh --tyres=res://tuning/tyre.tres`. Compare the two cars at one `--entry-kph`,
  never one `--run-up`: at `drive_scale` 2 the spike makes 119 kph in the 4 s the shipped car makes
  63. `--sweep` reaches `TyreProfile` fields; a drift_* field still sweeps only the drift rows.
  🔴 **`hold`'s driver is the harness's, never the car's** (`Q72`): it plays the human, and both
  cars get the same one. `longest` is the unbroken dwell the fare's drift pays on (`drift_min_s`);
  `secs>thr` sums every run. ⚠️ `hold` on the spike carries ±0.3 s run to run at one
  configuration (`Q152`; three serial runs were byte-identical on 2026-10-02, `Q153` — run the
  repeats anyway). 🔴 **Anything new in the spin step is solved, never stepped**: explicit, a braked
  wheel past the curve's peak limit-cycled; clamped at zero slip, the drive could not carry the rim
  past the road. 🔴 **Where the sideways force goes in is a drift dial** (`TyreProfile.side_force_depth`):
  at the contact the car rolled at a kerb, at the shipped 0.2 nothing slides.
  🔴 **`countersteer_assist` ships at 0 on the user's call (2026-09-29) — grade on `ride` AND
  `hold`.** `ride` is the player's plain input (tap, steering and throttle held), `hold` a player
  who countersteers. With the assist on, grade on `ride` only: `hold`'s driver countersteers on
  top of the assist and kills the slide (0.13 s). ⚠️ `--sweep` refuses a field in both tables — the tyre dial was
  renamed `side_force_depth` after a shared `roll_influence` swept the wrong table silently.
- ⚠️ **`wall@30`'s exit wanders 28.4–31.7 kph across runs of one HEAD** at 63 kph (`Q152`),
  approach and impact identical to the hundredth — wider than `Q151`'s 0.5 kph. Grade a wall change
  against that band.

