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

`P3-1a`, `Q141`. `FareSystem` (`game/scripts/fares/fare_system.gd`) runs hail → board → carry →
deliver / bail over the published fare nodes, metered by `FareMeter`
(`game/scripts/core/fare_meter.gd`) at Transport Department's tariff (`tuning/tariff.tres`), with
the loop's own numbers in `tuning/fares.tres`.

- 🔴 **`tariff.tres` is the government's table, not ours.** Every value is TD's published urban
  fare with its effective date in `tariff.md`; a change there is a tariff revision, cited, never a
  tuning pass. What is ours — radii, dwells, the par speed, the tip rate — lives in `fares.tres`.
  🚫 No abstract multiplier (`1×`, `2×`) anywhere: the meter shows money.
- 🔴 **The meter is honest and the tip is the skill.** The reading is the tariff on the metres
  driven and the seconds waited; nothing a player does at the wheel moves it except driving
  further or sitting still. Everything earned — the seconds left on the allowance now, `P3-2b`'s
  style chain later — is `Fare.tip_hkd`, and the two bank as one sum. 🚫 Do not make a shortcut
  or a fast run *raise the meter*; a shortcut lowers it and raises the tip, by design.
- 🔴 **The unit rule is "or part thereof", on two buckets, no speed bar.** A unit is charged when
  it BEGINS (one centimetre past 2,000 m reads 31.1), either bucket exceeding its unit charges and
  resets both, and nothing is charged for waiting inside the flagfall distance. `verify_fares.gd`
  pins 2,001 / 2,200 / 2,201 / 9,000 / 9,200 m and the bucket reset; a "waiting speed" threshold
  is not a field because the tariff's two units already cross at 12 kph.
- 🔴 **Cents, not dollars, inside `FareMeter`.** 29 + 35 × 2.1 must land on 102.50 exactly for
  the threshold comparison; `_cents_of` rounds once at construction.
- ⚠️ **Par is the legal profile** (`Q137`'s recommendation): the allowance is
  `max(kind floor, legal route / par_kph)`. `GAME_DESIGN.md`'s 30 s / 60 s are the floors, not the
  allowance. 🚫 Not the player's profile: par is what obeying the signs costs, and the player may
  break every rule to beat it.
- ⚠️ **The reach table is built once at load; the hail pays one `prepare`.** `_build_reach`
  prepares every destination and routes every pickup to it (14 ms on Wan Chai, `reach_ms` on the
  boot line and in `verify_fares`); `pick_destination` draws uniformly from a pickup's reachable
  list on the seeded RNG; `route` at the sample rate from the car's `Hit`; never per frame
  (`router.md`). 🚫 Drawing blind and retrying at the hail was built and refused: a stand with one
  reachable destination was refused most of its hails. 🚫 "No route" is a pool decision, never an
  assert (`Q137`).
- ⚠️ **The pools are the yaml's rules.** A stand is a pickup and a destination unless
  `cross_harbour` (`P3-1b`'s); a PUDO point is what its `pickup` / `dropoff` say — a quarter are
  drop-off only, and a hail at one is what a Hong Kong player notices; a `poi` tram stop is
  neither. The kind of a fare is the DESTINATION's (`pudo` → short hop, `taxi_stand` → standard).
- ⚠️ **A pickup that reaches no destination at `min_trip_m` is stranded**: dropped from the
  pickup pool at load, kept as a destination, counted in `FareSystem.stranded` and named by
  `verify_fares` and the boot line. Five region by region, four on the merged runtime (`Q141`), all
  at a clip edge whose forward direction leaves it. A new one is a finding about the data, answered by looking at the
  node — never by lowering the bar silently, and never by an assert that would fail every region
  with an edge.
- ⚠️ **`nearest_pending` never returns a pickup the loop would refuse**: disarmed after a
  delivery, it skips every pickup inside `hail_radius_m` — the user read an arrow at the kerb
  under the car as a "dumb 3 s cooldown". `verify_fares` asserts it at the delivery.
- ⚠️ **Nor is it marked** (`Q142`'s fourth round, the user's call): `withheld_pickups` is the
  same rule as `nearest_pending`'s skip, and the road rings and map pins hide those indices. A
  new marker of pending customers reads it too, or the drop-off grows a ring under the car.
- ⚠️ **The game starts short of the stand** (`RoadSpawn.DEFAULT_SETBACK_M`, 20 m back, outside
  the 12 m hail): `verify_spawn` fails a `hail_radius_m` raised past it. `--spawn-fare` is on the
  node itself.
- ⚠️ **A fare cannot start where the last one ended.** `_armed` clears on every end and on a
  refusal, and sets again only once a sample finds no pickup in reach. Without it a delivery at a
  stand that is also a pickup hails again on the spot.
- ⚠️ **Mutation-check it rather than reading its pass** (`Q72`). Each of these fails by name in
  `verify_fares.gd`: `step_m = 1` (a linear meter) at the 2,200 m point; a zero price (an inert
  meter); a drop-off-only point, a tram stop and a cross-harbour stand smuggled into `fares.json`
  (the pools); `min_trip_m` raised past every route (every pickup stranded, the pool empty);
  half the tip rate (what the same drive banks); the same trip delivered 2 s later (banks
  strictly less). Dwells and bars are asserted from BOTH sides: 0.75 s boarding and 1.0 s
  aboard; arriving fast and arriving stopped; one tick short of the allowance and one past it.
- ⚠️ **Verify tools never run by hand and read** (`verify_hud`'s rule): `verify_fares.gd` can
  print `ok` having checked nothing when a preload fails to compile. `tools/check.sh` is the
  reading. `TICK_S` is 0.25 — exact in binary — so a 1.0 s dwell lands on the fourth tick and not
  the fifth; do not "round" it to 0.2.
- ⚠️ **Two tables, two sidecars, both required** (`Q119`): `tariff.md` and `fares.md` beside the
  `.tres`, no defaults in either profile script, and `FareSystem.setup` refuses a zero field with
  the file named rather than run on a literal.
- ⚠️ **`--fares=off` is free roam** and what `P3-9` runs with the arrow off; `--fare-seed=<int>`
  fixes the draw for an A/B drive. Both go through `Cmdline`, like `--hud=`.
- ⚠️ **A stop carries its building and its road** (`Q142`): `fares.json`'s `place` is iB1000's
  `BUILDINGNAME` for the footprint nearest the kerbside `pos` within `fares.places.max_distance_m`
  (25 m), the one the point's text names where it names one inside the radius, `NAMESTATUS` `E`
  only, the city's `block_suffix` stripped for the search and never from the published name;
  `Fare.Stop.place(language)` falls back to the description, and `road_en` is `RoadGraph.name_of` at
  load. A node that loses its place on a rebuild is a finding about the data (`f_001`, opposite
  its building, is correctly none). `pytest tests/test_fares.py::TestNearestPlace` holds the
  radius, the footprint-not-centroid distance and the mention rule from both sides.
- ⚠️ **The HUD reads this through signals only** (`P3-5a`, `Q142`): `hud.gd` and
  `fare_guide.gd` connect `sampled`, `delivered` and `bailed` and read `state`, `fare`,
  `nearest_pending` and `pickups()` inside them, because under `--fares=off` the system frees
  itself in `_ready` before `Main` hands it over. A new consumer that polls it from `_process`
  reads a freed node on the second frame. `fare_face.gd` is the one place a string is decided.
- 🔴 **The skills are flat money per event, paid as they happen** (`P3-49`, `Q145`, the user's
  call over the style chain): `SkillTracker` (`skill_tracker.gd`) is fed every tick's speed and
  slip by `sample()` while carrying, `tuning/skills.tres` prices them (sidecar `skills.md`), and
  each award lands on `Fare.awards`, in `skills_hkd` and `tip_hkd` at once, and out on `skilled`.
  `time_hkd` is the seconds left priced at the door; `tip = time + skills`. 🚫 No multiplier, no
  chain, no crash detector here — `P3-2b` layers on top, the awards do not change.
- 🔴 **A drift must qualify, and the speed skill is paid by the metre** (the user's calls,
  2026-09-25, `Q145`): a slide counts once it has held `drift_min_s` (2 s, over the 1 s that paid a
  tap) and pays again every `drift_s`; a run at or over `speed_min_kph` pays every `speed_hold_m`
  DRIVEN, and `verify_fares` refuses `speed_hold_m` under `tariff.step_m` so the skill can never
  tick faster than the meter's 200 m unit. 🚫 No `speed_hold_s`: time at speed is what the clock
  already pays. The drift's bar is seconds because `Q84` grades drift on dwell.
- 🔴 **The drift's angle has ONE copy: `HandlingProfile.drift_slip_threshold_deg`** (`Q84`'s
  design target), handed to `setup` and loaded by `verify_fares` through `HandlingProfile.PATH`;
  `skills.tres` carries no angle. ⚠️ `FareSystem.slip_deg_of` DUPLICATES
  `skidpad_ablation.gd::_slip_deg` on purpose — the grader must never call what it grades — so a
  change to either's flattening or floor is made twice, by hand, and named.
- 🔴 **The bars are inclusive and every dwell is asserted from both sides** in `verify_fares`'s
  `skills:` block: one tick short of `drift_min_s` / `speed_hold_m` pays nothing and the tick that
  reaches it pays, a slide as long as `drift_s` but short of `drift_min_s` pays nothing, twice the
  speed pays in half the ticks (distance, not time); a degree under the threshold never pays; a
  slide or run that ends forfeits its unpaid part (two short ones are not one long one); the share
  a tick under and on. Mutations:
  a zeroed `drift_hkd` and a zero threshold are inert systems, named; half the price banks less.
  ⚠️ Arriving with the clock nearly full IS an early arrival, so the loop's own delivery check
  expects `time + early_hkd`.
- 🔴 **The live tip is the skills alone, floored at zero; the time joins it at the door** (the
  user's call, 2026-09-25: a tip that fell with the clock read as a penalty). `time_hkd` is 0
  while carrying and priced once in `_deliver`, before the early arrival; `tip_hkd =
  FareSystem.tip_of(time, skills)` after every award and at the door. `FareFace.tip_text` is the
  bare digits for a second `SevenSegment` under the meter's, in `meter_lit` at `tip_digit_px`,
  with `tip_caption` ("TIP" / 小費) beside it — the meter's face, never a green label. `verify_fares`
  asserts the tip does not move over two seconds of clock. A penalty (`P3-50`) is an `Award`
  with negative `hkd` — same receipt, minus sign,
  `accent_negative` flash — and `tip_of` never goes below 0: the passenger docks the tip, never
  the meter (`Q141`). 🚫 No penalty on the meter, no negative bank.
- 🔴 **A bail forfeits every award and keeps every award**: `tip_hkd` and `banked_hkd` are 0,
  `awards` and `skills_hkd` stay on the fare so `FareFace.forfeit` can say what walked out.
- ⚠️ **What listens to `skilled`**: `hud.gd` flashes `FareFace.award_text` in the gain's green;
  `taxi_hire.gd` pops the grin (`PassengerEmote`, `vehicle/passenger_emote.gd`) and pops the rage
  on `bailed`. A new consumer connects the signal; it never reads `awards` from `_process`.
- 🚫 **Not here**: near miss and air (`Fare.Skill` slots — `B3`'s traffic, and something to jump
  off), the session timer and the fare combo (`P3-2b`), cross-harbour and long haul with the tunnel
  toll (`P3-1b`), operating hours (`Q14`).
