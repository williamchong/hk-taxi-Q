---
paths:
  - "game/scripts/vehicle/vehicle_controller.gd"
  - "game/scripts/vehicle/handling_profile.gd"
  - "game/tuning/handling.{tres,md}"
  - "tools/skidpad.sh"
  - "tools/skidpad_ablation.gd"
  - "game/scenes/dev/skidpad.{tscn,md}"
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
- ⚠️ **`drift_slip_threshold_deg` has a consumer since `P3-49`**: the fare's drift skill pays
  `SkillProfile.drift_hkd` per `drift_s` the slip holds at or over it (`Q145`), so the number the
  skidpad's `secs>thr` column grades is now the number the game pays on. It stays a design target
  (`Q84`): a slide that should pay is answered on the grip dials against dwell, never by lowering
  the threshold — and the game's slip (`FareSystem.slip_deg_of`) is a deliberate second copy of
  the ablation's, so a change to the flattening or the 1 m/s floor is made in both.
