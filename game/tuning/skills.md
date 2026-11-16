# skills.tres

What a drift, a run at speed, a jump, a near miss and an early arrival pay into the tip, and what a
hit docks (`P3-49`, `Q145`; air `Q147`; penalties `Q148`; near miss `Q161`; combo `Q205`). Each
skill is a flat HK$ per event, paid when earned; a bail forfeits the lot. Prices and bars are
first guesses ahead of the user's drive.

The drift's angle is not here: `handling.tres`'s `drift_slip_threshold_deg` (14°) is the skidpad's
target (`Q84`) and this table reads it.

Every key is required: `skill_profile.gd` declares no defaults and `FareSystem` refuses a zero
dwell, bar or price.

## Drift

- `drift_min_s = 0.5`: a slide must hold over the threshold this long before it counts (`Q172`,
  the user's call). At 2.0 the pace-2 car almost never paid: `hold` dwells 0.68 / 0.83 / 3.57 s at
  42 / 63 / 86 kph. Seconds, not metres: `Q84` grades dwell, and speed is the speed skill's job.
- `drift_s = 1.0`: a counted slide pays again each further second; releasing forfeits the unpaid
  part. Also the sparks' cadence (`drift_sparks.md`).
- `drift_hkd = 1.0`: the first award. Small, since every tap reaches it.
- `drift_step_hkd = 1.0`: the n-th award pays `drift_hkd + (n − 1) × drift_step_hkd` (`Q172`), so
  a slide banks HK$1 at 0.5 s, 3 at 1.5, 6 at 2.5, 10 at 3.5. A new slide starts again.
- No cap (`Q179`): on open ground a slide holds 30 s (`ride` from 20 kph, 28.6 s, HK$435), but no
  street allows past 1.5 s. Re-measure before any open space ships.

## Speed

- `speed_min_kph = 80.0`: meant to pay Gloucester Road and not Hennessy between the trams. Set on
  an older car; at pace 2.0 the car reaches 80 in about 2.8 s and which street pays is not
  re-measured. Left on the user's call (`Q152`).
- `speed_hold_m = 200.0`: pays once per 200 m at or over the floor. `tariff.tres`'s `step_m`, so
  it never ticks faster than the meter; `verify_fares` refuses a value under `step_m`. Distance,
  so a faster run pays sooner.
- `speed_hkd = 5.0`.

## Air

- `air_min_s = 0.5`: all wheels off the ground this long, judged at the landing (`Q147`). A kerb
  hop is 0.1–0.2 s, a drop off a flyover deck 0.8–1.2 s.
- `air_s = 0.5`: each further half second pays again, all at the landing.
- `air_hkd = 5.0`: paid only on an upright landing.

## Early arrival

- `early_share = 0.5`: half the allowance left at the door. Par is 30 kph over the legal route
  (`fares.md`), so this is a 60 kph average or a shortcut.
- `early_hkd = 10.0`: twice a skill; the receipt's biggest line under the time itself.

## Penalties (`P3-50`, `Q148`)

One number is read: the speed into the obstacle on the tick of the hit
(`VehicleController.take_impact_mps`); on a moving car, the closing speed, only when the taxi is
moving into it (`Q175`). Two bars make three tiers. The meter is never docked (`Q141`) and the tip
floors at zero.

- `bump_min_kph = 20.0`: under it a contact is a touch: free, but it ends a slide so a wall cannot
  farm the drift. A 10° brush reads 11.6 / 15.4 / 18.6 / 22.6 kph from 63 / 86 / 105 / 130 kph
  entries, so a brush at 130 is a collision. Left on the user's call.
- `bump_hkd = 2.0`: a warning, less than one skill.
- `crash_min_kph = 60.0`: must be over `bump_min_kph` (`FareSystem.setup`). A 30° clip reads
  37.6 / 47.5 / 55.9 / 65.5 kph and a head-on 77.7 / 97.3 / 113.5 / 131.1, so 60 does not split
  them at 130; a bar between 65.5 and 77.7 would. Left on the user's call.
- `crash_hkd = 5.0`: one skill's worth.
- `crash_cool_s = 1.0`: one wall is one dock; a hit reports 2 to 24 contact ticks inside a second.

Re-measure with `tools/skidpad.sh --only=wall`.

## Near miss (`P3-2a`, `Q161`)

- `near_miss_m = 0.9`: flank-to-corner clearance at or under which a pass is a near miss, the
  least while alongside. The user's swerves read 0.69–0.85 m. A lane-centred pass of a bay-row car
  is about 0.65 m, inside the band, so `near_miss_look_s` is the whole refusal of a lane pass.
- `close_call_m = 0.25`: under it the pass pays `close_call_hkd` instead. Must be under
  `near_miss_m`. The path rule does not apply inside this band (the user's call): that close at
  speed is danger in any lane. A touch or a flight while alongside pays nothing.
- `near_miss_min_kph = 40.0`: the highest speed while alongside, so braking into the pass does not
  forfeit it.
- `near_miss_look_s = 1.5`: a parked vehicle is in the path when part of it lies ahead within this
  many seconds of travel and inside the car's own width (the user's call: no pay for passing cars
  in the next lane). Floored at one car length. Not applied to an oncoming car (the user's call):
  the closing speed is the danger, so an oncoming pass inside `near_miss_m` pays unaimed.
- `near_miss_memory_s = 2.0`: how long a vehicle stays "was in the path" after leaving it. A touch
  or a flight forgets every threat (`NearMiss.tick`).
- `near_miss_hkd = 5.0`, `close_call_hkd = 10.0`.

## Combo (`P3-2b`, `Q205`)

- `combo_gap_s = 2.5`: seconds of doing nothing after a skill pays before the combo ends. The
  clock does not run while a skill is in progress (`SkillTracker.holding`), because a speed run
  pays 9 s apart at 80 kph.
- `combo_show_min = 2`: the smallest total whose end is called out; "×1" is noise. Records keep
  every combo.
