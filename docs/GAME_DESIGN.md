# Game Design

## Pillars

1. **It must feel like Hong Kong to a Hong Kong driver.** Recognition beats fidelity. A local should
   navigate by memory, not by minimap.
2. **Arcade, not simulation.** Short sessions, instant restart, forgiving collision, easy to drive.
   The car's physics are a real Toyota Crown Comfort's (`Q153`); the ease is layered on top as
   hidden aids (`tuning/systems/`), never by bending a physical number. The drift is the one place
   for sim-lite skill: easy to start, forgiving to lose, held longer by throttle and countersteer.
3. **Readable at a glance.** Two thumbs on a phone, on a bus, in daylight (`Q97`).

## The central design tension

Real geometry fights arcade fun, and fun wins. The open data is a skeleton, not ground truth.

| Use the real data for | Deliberately diverge on |
|---|---|
| Road topology, widths and connectivity | Kerb heights — flattened for mountability |
| One-way directions, turn restrictions and signals (for AI traffic) | Player rule-breaking — always allowed, never penalised (`Q181`) |
| Building massing and position | Street furniture — railings, lamp columns, sign and signal posts are solid (`Q159`, `Q191`) and do not break away |
| Landmark placement, street and place names | Ramps, jumps, shortcuts — hand-added, sparingly |

The player may break every traffic rule; the AI obeys them. A breach is paid for only when
something in the world catches it, and nothing does yet (`Q181`).

A hand-added ramp is new geometry somewhere the player knows. Prefer the shortcut that is there —
the Canal Road Flyover (drivable, `Q111`), the plaza gaps, the alley grid — and invent one only
where a stretch is demonstrably dead, recorded as a decision.

## Core loop

```
cruising → stop beside a waiting customer → passenger boards → carry, allowance running
        → stop at the destination: meter + tip banked → cruising
        → allowance runs out: the passenger walks without paying → cruising
```

- **A shift (特更, `Q162`)** runs the HUD's clock 07:00 → 21:00 over fourteen minutes of driving, a
  clock minute a second (`Q233`), the sky with it. The total fare is the score. A delivery adds
  money, never time. At 21:00 no new customer hails and the passenger aboard is the last fare; then
  交更, the report against the best.
- The clock stops under the menu. AGAIN on the report restarts in place, no loading screen.
- Boarding and delivery: stop (`stop_below_kph`) inside `hail_radius_m` / `deliver_radius_m`
  (`fares.tres`).

## Fares

Fare nodes come from `fares.json`: Taxi Stands, Taxi Pick-up & Drop-off Points, tram-stop POIs, and
**street spots** (`Q203`) — any kerb no no-stopping run reaches, off bus lanes and trunk roads,
beside a named building. `live_pickups` customers wait at once, `street_share` of them at street
spots, each already knowing where they are going; a new one appears as a fare ends.

- **The meter is real** (`Q141`, `tariff.tres`, TD's urban tariff): HK$29 for the first 2 km, then
  HK$2.1 per 200 m or per minute waiting until HK$102.5, HK$1.4 after — on metres driven and
  seconds waited. Inside one region most trips stay on the flagfall, so the drive earns the rest
  as a tip.
- **The allowance is the legal route alone**: its length over `par_kph` (19, the legal traffic's
  measured median), no floor by kind. A destination is at least `min_trip_m` (300) of legal route
  away; a pickup that reaches none is not a pickup.
- A fare's kind is its destination's (`pudo`, `taxi_stand`, `poi`, `street`). Nothing prices a kind.
- Destinations are announced by name, bilingually — `Times Square / 時代廣場` — never by street
  address. A guide assists, but the acceptance test is run with it off.

**Designed, not built (`P3-1b`):** long-haul fares across districts, and the **cross-harbour** fare
— the signature mechanic. The source data distinguishes `cross_harbour` stands; the fare pays the
meter plus the HK$25 toll and return toll and terminates at the tunnel approach, which is in the
region at street level. The cross-harbour stands sit 191–1,044 m from the portal, so the near ones
need a minimum length or another destination.

## Scoring

Values are `tuning/skills.tres` and `fares.tres`.

| Component | Rule |
|---|---|
| Base fare | The meter's reading at delivery |
| **Tip** (小費) | Everything below, in HK$, banked with the meter as one sum |
| Time bonus | Remaining seconds × `tip_hkd_per_s`, priced at the door; never in the live tip (`Q145`) |
| Drift (甩尾) | Once a slide has held `drift_min_s` over the slip threshold, and again per `drift_s`, each award `drift_step_hkd` more than the last (`Q172`) |
| Sustained speed | Per `speed_hold_m` driven over `speed_min_kph` |
| Early arrival | Once at the door with `early_share` of the allowance left |
| Near miss | Passing a vehicle, parked or moving, inside `near_miss_m` at or over `near_miss_min_kph`, only when the car was heading for it a moment before; inside `close_call_m` it is a close call at twice the price (`Q161`, `Q175`) |
| Air | At the landing once every wheel has been off the ground `air_min_s`, and per `air_s` of flight; upright landings only (`Q147`) |
| Penalty | A wall or vehicle hit is tiered on closing speed: a touch is free, a collision (`bump_min_kph`) and a crash (`crash_min_kph`) dock the tip, never the meter (`Q148`) |

- **Flat money per event** (`Q145`), not a multiplier a crash resets: a pop the player can read
  beats a multiplier they cannot.
- Skills pay during the drive and show at once: a flash, the tip on its own LED under the meter,
  the passenger's face. The live tip only rises or is docked; the time bonus joins at the door,
  because a tip that fell with the clock read as a penalty for driving.
- With no passenger aboard the skills still flash by name, unpaid, and count for the record.
- The delivery callout is a receipt: meter, time left, each skill with its count.
- **Names are the driving test's** (`Q169`, `tuning/exam_sheet.json`): a bump and a crash are the
  黃紙's 碰及物體（輕微／嚴重）; a bonus is a feat — 貼身而過, 險過剃頭, 高速行駛, 凌空飛躍,
  走得快好世界, 甩尾. Names only: no pass or fail.
- **The style combo (車手, `Q205`, `Q212`) is a count, never money.** Each skill has its own count;
  any skill keeps every count alive; a collision, or `combo_gap_s` with no skill in progress,
  ends it and calls out the total from ×2 up. Best combos go in the 成績表 and the lifetime record.
- Not built: a **fare combo** for consecutive deliveries; achievements and a share sheet (`Q188` —
  the 成績表 saves as a picture).

Sustained speed belongs to Gloucester Road, drift and near miss to tram-pinned Hennessy, so which
route pays more is a real choice. Air pays off any deck edge: the flyovers are jumpable by design.

## Controls

Action mapping is `docs/ARCHITECTURE.md`; handling is `.claude/rules/handling.md`. All values live
in `game/tuning/` (`handling.tres`, `tyre.tres`, `pace.tres`, `cars/`, `systems/`); grade every
change on `tools/skidpad.sh`, never against a number written here.

**Handling model:** Jolt `VehicleBody3D` with the engine's tyre force turned off and a per-wheel
tyre model applied instead (`TyreVehicleController`, `Q152`), because `VehicleWheel3D` friction is
isotropic and cannot break lateral grip while keeping traction.

| Property | Target feel |
|---|---|
| Grip | High, forgiving. No spin-outs from small errors |
| Drift | Started with the handbrake (`Space`, `Q170`), held by throttle and countersteer; traction control returns when the steering is let go. A handbrake scrubs speed, so a drift buys line, never pace. Graded on dwell over the threshold, never on peak slip (`Q84`) |
| Collision | Glancing hits deflect; head-on hits cost speed, never control |
| Recovery | Auto-righting if flipped; RESET CAR on the pause puts the car on the nearest road it can leave (`Q229`, `Q241`) |
| Reverse | Instant, no gear delay |
| Braking | Strong, a road tyre's limit with ABS; must out-pull the ramps. The car stops faster than it accelerates |
| Coasting | Comes to a stop: one pedal serves brake and reverse, so only coasting parks the car |

- **Touch carries steer, accelerate and brake/reverse** (`Q97`), drawn as the taxi's wheel and
  pedals (`Q204`, `touch.tres`). The handbrake, `look_back` and the horn are keyboard/gamepad only
  until a handset prices the gesture (`P0-3b`); thumb 2's vertical axis is reserved for the
  handbrake.
- `auto_accelerate` (one-handed play) is designed, not built.
- Driving against a one-way raises a blinking NO ENTRY disc (`Q81`, `wrong_way.tres`). It informs;
  it does not penalise.
- Owed: the handset drive of the tyre model and of the reset.

## Hong Kong authenticity mechanics

| Mechanic | Status |
|---|---|
| Bilingual destination callouts | Built |
| Red urban taxi livery | Built. HK Island is red; green or blue reads as wrong |
| Trams as moving walls | Built (`Q176`, `Q180`): on the published rails, stopping at the published stops and the reds. The taxi pushes one along its rails by momentum, never off them |
| Buses and green minibuses on their published routes | Built (`Q182`): they stop at their stops; double-deckers block sight |
| Traffic signals | Built (`Q173`): an authored phase plan, heads showing what it runs |
| Parked vehicles from published bays, stops, termini and stands | Built (`Q161`) |
| Bus lanes, reds and double yellows as penalties | Refused until something in the world enforces them (`Q181`) |
| Bamboo scaffolding, cross-harbour tunnel queue, neon signage | Not built |

Neon is the highest-value gap: "the streets are bare" and "the streets are wrong" have different
fixes, and the handset round should listen for which.

## Traffic

Built (`.claude/rules/signals.md`, `busroutes.md`, `trams.md`, `parked.md`; `traffic.tres`).

- Vehicles follow road-graph edges, obeying direction, turn bans and signals. Traffic, not
  opponents. Mix and size follow the clock hour off TD's census and detectors (`Q186`, `Q198`).
- No vehicle appears or vanishes in view (`Q214`).
- A car the taxi hits is knocked by momentum (`Q180`): it slides, stands on its hazards, and drives
  on if it can rejoin a lane, or stays a wreck the others pass. Parked vehicles stay fixed. The
  crash costs the closing speed alone, whatever the mass.
- One turn restriction in the region excludes taxis and `roadgraph.json` has no field for that, so
  the graph forbids a turn a real red taxi may make. Adding it is a schema change on both sides.

## Region and free-slice boundary

Regions are in `etl/config/hong_kong.yaml`; the game ships `wan_chai` and `causeway_bay` joined.
Design Wan Chai to be standalone-playable: it becomes the free tier and the web demo, the rest the
unlock.

**The circuit:** Gloucester Road (east, fast) → Canal Road Flyover (the vertical beat) → Hennessy
Road (west, tram-pinned, technical) → Fleming / Fenwick back to Gloucester. Fast spine plus
technical parallel is the contrast arcade driving lives on, and it exists in the real layout.

**Map edges are diegetic:** Victoria Harbour north, the escarpment south, Admiralty west. Streets
the rectangle cuts are closed on the line with the fence's barrier row (`Q143`); a road a
neighbouring region continues is never closed.

## Modes

| Mode | Status | Notes |
|---|---|---|
| **特更 / THE SHIFT** | Built (`Q162`) | The main mode: 07:00 to 21:00, then 交更 and the total against the best |
| **兜風 / FREE MODE** | Built (`Q162`) | Fares on, no end; DAY TO NIGHT, ALWAYS DAY or ALWAYS NIGHT, picked as it begins and on its pause (`Q266`). Ends from PAUSE on its own report (`Q189`) |
| Free roam (dev) | Built | `--fares=off`: no fare or guide |
| Time trial, daily challenge | Not built | Fixed A→B; seeded fare sequence |

## Acceptance test

**Hand the build to a Hong Kong driver, disable the minimap (`--minimap=off`) and the guide, and
name a destination.** If they can drive from the Convention Centre to Times Square from memory,
using the correct one-way streets, the city reads as Hong Kong. If they need the minimap, the
pillar has failed — and the test shows where.

Run it at the end of every phase, with at least three drivers. Round 0 (`P3-9a`, web, no HUD): three
HK drivers recognised Wan Chai from geometry alone. `P3-9`, the handset round, is owed and needs
different drivers — that cohort has learnt the map.

## Anti-goals

- A driving simulator: no damage modelling or fuel.
- Energy timers, lives, or any session-gating monetisation.
- Gacha, loot boxes, or randomised rewards — including the wheelspin shape.
- Live-service, seasons, or anything always-online (hard rule 2).
- Licensed-car collection as a progression spine.
- Pedestrians as collision targets. Keep pavements empty, or non-collidable ambience.
- An open-world map of all Hong Kong.
- Multiplayer.
