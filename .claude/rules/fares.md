---
paths:
  - "game/scripts/fares/*.gd"
  - "game/scripts/core/fare_meter.gd"
  - "game/tuning/tariff.tres"
  - "game/tuning/tariff.md"
  - "game/tuning/fares.tres"
  - "game/tuning/fares.md"
  - "game/tools/verify_fares.gd"
---

# The fare loop — before marking work done

`P3-1a`, `Q141`. `FareSystem` runs hail → board → carry → deliver / bail, metered by `FareMeter`
at TD's tariff (`tariff.tres`); the loop's dials are `fares.tres` and `skills.tres`, with values
and reasons in their sidecars.

**Check**: `tools/check.sh` (runs `verify_fares`, a named block per rule below); run by hand the
tool prints `ok` having checked nothing when a preload fails to compile. Mutation-check a new
assertion (`Q72`); bars are asserted from BOTH sides. `TICK_S` 0.25 is exact in binary; keep it.
`--fares=off` is free roam; `--fare-seed=<int>` fixes the draw for an A/B drive.

## Meter and tip

- **`tariff.tres` is TD's table**, cited with its effective date in `tariff.md`; a change is a
  tariff revision. No abstract multiplier anywhere: the meter shows money.
- **The meter is honest, the tip is the skill.** Only metres driven and seconds waited move the
  reading; a shortcut lowers it and raises the tip. No penalty on the meter, no negative bank.
- **"Or part thereof", two buckets, no speed bar**: a unit is charged when it BEGINS, either bucket
  charging resets both, nothing for waiting inside the flagfall. `FareMeter` works in cents.
- **Par is the legal profile** (`Q137`): allowance = legal route / `par_kph`, no floor by kind
  (`Q203`). `par_kph` is the AI traffic's measured median run (recipe in `fares.md`); re-measure
  after a change to `traffic.tres`' `cruise_of_limit` or the signal timings. Never the player's
  profile.
- **The live tip is the skills alone, floored at zero; the time joins at the door**
  (`FareSystem.tip_of`; a tip falling with the clock read as a penalty). An early arrival pays in
  `_deliver` too, so a full-clock delivery expects `time + early_hkd`.
- **A bail forfeits the money and keeps the list**: `tip_hkd` and `banked_hkd` 0, `awards` and
  `skills_hkd` stay for `FareFace.forfeit`.
- **The books are `SessionTally`'s** (`Q169`): an award goes on `counts`, its HK$ joins `banked`
  only at the door; `total_hkd()` equals `earned_hkd`. A new `Fare.Skill` goes in `BONUSES` or
  `PENALTIES` and needs a row's height (`menu.md`).

## Customers and pools

- **The pools are the yaml's rules**: a stand is pickup and destination unless `cross_harbour`; a
  PUDO point is what its `pickup` / `dropoff` say; a `poi` tram stop is neither; a `station_exit`
  (`Q268`) is a destination only, named by `fares.stations.table`; a street spot
  (`fares.street`) is both where the legal router admits its edge. A fare's kind is its
  destination's and prices nothing (`Q203`). `street_share` 0 is the off switch, the one key
  `setup` does not refuse at zero.
- **A few wait, each paired as it is drawn** (`Q203`): `pickups()` is the live set, and a
  destination comes from one forward search (`RoadRouter.source_tree`, uncached) at `min_trip_m`.
  Never a `prepare` for a pairing: it would evict the tree the car's route reads (`TREE_CACHE`).
  Refused: drawing blind and routing each try (24 `prepare`s for a stranded kerb); an all-pairs
  reach table (~390 street spots, seconds at load); drawing blind at the hail.
- **A pickup that reaches nothing is stranded**: dropped as a pickup, kept as a destination,
  counted in `stranded`. Found by the draw, so the set depends on the seed. "No route" is a pool
  decision, never an assert; a new pattern is a finding about the node, not a reason to lower the
  bar.
- **The waiting stay near the car and stay put** (`Q203`): placed within `place_m`, swapped past
  `retire_m` by `_turn_over` — one draw a sample (Causeway Bay strands 9 in a row at its far
  corner), and a swap, never a removal alone. Customers do not follow the car.
- **The start stand always has a customer** (`wait_at`, `Q203`); later runs draw the stand from
  `published_pickups()` (`Q227`). A rule that empties `_pool` leaves every run on the boot stand,
  silently.
- The game starts `RoadSpawn.DEFAULT_SETBACK_M` short of the stand; `verify_spawn` fails a
  `hail_radius_m` raised past it.
- **A fare cannot start where the last ended**: `_armed` clears on every end and sets once a sample
  finds no pickup in reach. `nearest_pending` and `withheld_pickups` skip those pickups, and rings
  and pins hide them (`Q142`); a new marker of pending customers reads `withheld` too.
- **A stop carries its building** (`Q142`): `place` is iB1000's `BUILDINGNAME` within
  `fares.places.max_distance_m`; `Fare.Stop.place(language)` falls back to the description
  (`test_fares.py::TestNearestPlace`).

## Skills and penalties (`skills.tres` / `skills.md`, `SkillTracker`, `NearMiss`)

- **Flat money per event, paid as it happens** (`Q145`): `tip = time + skills`, no multiplier.
- **Empty, skills are shown and never paid**: an award goes out on `practised`, counts in
  `skill_counts`, never in `earned_hkd`. `_tracker.reset()` at `_board` keeps a held slide off the
  receipt.
- **Drift** (`Q172`): counts after `drift_min_s`, pays every `drift_s`, each award `drift_step_hkd`
  over the last within ONE slide; seconds, because `Q84` grades drift on dwell. Slip past
  `REVERSED_SLIP_DEG` (90°) is reversing.
- **The drift angle has one copy**, `HandlingProfile.drift_slip_threshold_deg`. The slip
  (`FareSystem.slip_deg_of` → `SlipAngle.deg_of`) deliberately duplicates
  `skidpad_ablation.gd::_slip_deg` (`Q84`): change the flattening or the floor in both.
- **Speed is paid by the metre** (`speed_hold_m`, refused under `tariff.step_m`). No
  `speed_hold_s`: the clock already pays time.
- **Air pays at the landing** (`Q147`), only when `is_upright` on the first grounded tick.
- **Penalties read one number** (`Q148`): `VehicleController.take_impact_mps`. Under `bump_min_kph`
  a touch is free but ends a slide; then `BUMP`, then `CRASH`; `crash_cool_s` makes one wall one
  dock. The bars are the skidpad's wall rows (`tools/skidpad.sh --only=wall`; `--only=traffic` for
  a moving car, `Q175`): change one only against a new matrix. Refused: a speed-loss detector
  (braking and `place_at` look like walls), the contact impulse, a second wall list.
- **Near miss and close call** are `NearMiss`'s (`parked.md`): `setup` takes the car's plan
  half-extents and refuses an inert detector. `Award.passed` names the obstacle for
  `TrafficSystem.react_to`.
- **The style combo is a count, never money** (`Q205`, `StyleCombo`): a penalty ends it, any other
  award adds to it. The gap stands still while `SkillTracker.holding()`, or the speed skill never
  passes ×1.

## Session and consumers

- **`close()` (交更) closes the loop, it does not end a fare** (`Q162`): hails and scans no one,
  cancels a BOARDING passenger, lets a CARRYING one finish; `finished` fires once. `reset()` is a
  fresh run on the same pools. A delivery adds no time: the shift's clock is `DayClock`'s.
- **Readers use signals, never `_process`**: under `--fares=off` the system frees itself in
  `_ready`. `hud.gd` and `fare_guide.gd` connect `sampled`, `delivered`, `bailed`,
  `pickups_changed` and read `state`, `fare`, `pending`, `withheld`, `pickups()` inside them.
  `pending` and `withheld` are one scan per sample (`_rescan`); a reader never rescans the pool.
  Strings are `fare_face.gd`'s, a reader's target `FareFace.target_of`.
- `skilled` → the HUD flash and `taxi_hire.gd`'s emote; `drift_tier_changed` → `DriftSparks`.
- **Cabin sounds are `TaxiHire`'s, on the loop's signals** (`Q185`, `Q178`): flag down at `boarded`,
  up at `delivered` / `bailed`, card beep and a coin per `coin_hkd` of tip up to `coin_max`, the
  meter's beep on `meter_changed` only. No sound on a skill or penalty (built, heard, removed).
  The music's layers follow the combo's count (`DriveMusic`, `Q246`): music, not an award's sound.
- A zero field is refused with the file named (`TuningTable.any_zero`); no defaults in a profile.
- Not here: cross-harbour and the tunnel toll (`P3-1b`), operating hours (`Q14`).
