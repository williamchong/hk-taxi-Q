# Game Design

## Pillars

1. **It must feel like Hong Kong to a Hong Kong driver.** Recognition beats fidelity. A local should
   navigate by memory, not by minimap.
2. **Arcade, not simulation.** Three-minute sessions, instant restart, forgiving collision,
   unrealistic grip. Fun outranks accuracy every time they conflict.
3. **Readable at a glance.** Played one-handed on a phone, on a bus, in daylight.

## The central design tension

**Real geometry fights arcade fun, and fun wins.**

Real Hong Kong streets are narrow, densely one-way, and lined with pedestrian railings. Faithfully
reconstructed, that produces a traffic simulator with no room to be reckless. The genre needs wide
roads, ramps, shortcuts, and forgiving collision.

**Resolution: the open data is a skeleton, not ground truth.**

| Use the real data for | Deliberately diverge on |
|---|---|
| Road topology and connectivity | Road **width** — widen ~1.3–1.8× at grade, but **1.0× on structure**: a viaduct is parapet-to-parapet in the real city, and a widened ribbon there hangs over the edge of its own deck |
| One-way directions and turn restrictions (for **AI traffic**) | Player rule-breaking — always allowed |
| Building massing and position | Pedestrian railings — omit or make breakable |
| Landmark placement | Ramps, jumps, shortcuts — hand-added, and sparingly (see below) |
| Street and place names | Kerb heights — flatten for mountability |

The player may break every traffic rule. The AI obeys them. That asymmetry is what makes the city
read as real while staying playable.

⚠️ **The divergences are not all equally cheap, and one of them is priced against `P3-9`.** Widened
carriageways, flattened kerbs and omitted railings are invisible to a driver's memory of a street —
nobody navigates by kerb height. A hand-added ramp is not. It is new geometry standing somewhere the
player knows, and every one is a debit against the acceptance test at the bottom of this document.

**So prefer the shortcut that is there over the ramp that is not.** The region already holds the
vertical beat and the alternate lines in its own geometry — the Canal Road Flyover, the elevated
Gloucester approach, the plaza gaps, the alley grid. The ramps are real and they are in the source
data; `P2-7` put the carriageway on them, and `P4-1` is what opens them to driving. **Invent a ramp
only where a specific stretch is demonstrably dead, and record it as a decision when you do.**

---

## Core loop

```
    idle / cruising
          ↓  drive into a hail zone
       fare hailed
          ↓  passenger boards
    carrying passenger  ──── timer running ────┐
          ↓  reach destination zone            │
       delivered  → fare + time bonus + style  │
          ↓                                    ↓
    combo continues                     timer expires → passenger bails
          ↓                                    ↓
    ← ← ← ← ← back to idle ← ← ← ← ← ← ← ← ← ←
```

Session ends when the **global session timer** expires. Delivering fares adds time to it. This is the
genre's classic structure: the game ends when you stop being good.

- **Session length:** 3–5 minutes typical; skilled play extends it.
- **Restart:** instant, one tap. No loading screen between runs.

---

## Fares

Fare nodes come from `fares.json`, built from the Taxi Stands and Taxi Pick-up & Drop-off Points
datasets, plus hand-added POIs.

| Type | Source | Time allowance | Payout | Notes |
|---|---|---|---|---|
| Short hop | `pudo` | 30 s | 1× | Common; keeps the chain alive |
| Standard | `taxi_stand` (urban) | 60 s | 2× | The default fare |
| Long haul | `poi`, cross-district | 90 s | 4× | Rewards route knowledge |
| **Cross-harbour** | `taxi_stand` where category = `cross_harbour` | 75 s | 5× | Terminates at the tunnel approach |

**The cross-harbour fare is the signature mechanic.** It exists only because the source dataset
distinguishes that stand category, it pays the most, and it ends at a map boundary that is diegetic
rather than arbitrary. No other city's version of this game has it.

The obvious objection — there is no other side of the harbour in a Wan Chai region — is already
answered by the design: the fare *terminates at the tunnel approach* rather than crossing, and that
approach is in the region **at street level**. Three `CROSS HARBOUR TUNNEL` edges sit at elevation
level 0 and join ordinary streets through `WAN CHAI INTERCHANGE`; you can drive there from Hennessy
Road today. Distance from the six cross-harbour stands to the portal runs **191 m to 1,044 m** — a
usable spread, though 191 m is barely a trip, so `P3-1` needs either a minimum length or a different
destination for the near ones. Whether stopping at a portal *feels* like completing a cross-harbour
fare is a `P3-9` question, not a geometry one.

### Destination presentation

Destinations are announced **by name, bilingually** — `Times Square / 時代廣場`, `會展`, `灣仔碼頭` —
never by street address. Hong Kong drivers navigate by landmark name, and this is the cheapest,
highest-impact authenticity lever in the game. Names ship in `fares.json`.

A directional arrow assists, but the **acceptance test is that a local can find the destination with
the arrow disabled.**

---

## Scoring

| Component | Rule |
|---|---|
| Base fare | By fare type multiplier |
| Time bonus | Remaining seconds × rate |
| **Drift** | Points/second while sliding above a threshold angle |
| **Near miss** | Passing traffic within ~1 m at speed |
| **Air** | Points by airtime duration |
| **Sustained speed** | Points/second above a speed floor |

Style points are awarded **during** the drive and shown immediately — the feedback loop must be tight
enough that players learn what the game rewards without being told.

⚠️ **They accumulate into a *style chain* rather than popping and clearing, and that is a deliberate
divergence from the genre's usual per-event bonus.** A bonus that pays instantly teaches the player
what the game likes; only a multiplier that can be *lost* makes the next corner tense. It is the
project's bet on what makes a 1.5 km² map worth re-driving.

Two multipliers therefore exist — and **"chain" already means the fare sequence elsewhere in this
document**, so the style one is always the *style chain*:

| | Scope | Climbs on | Resets on |
|---|---|---|---|
| **Style chain** | Seconds of driving | Style components | A hard crash, or going quiet after it banks |
| **Fare combo** | The session | Consecutive deliveries | A bailed fare |

Sustained speed belongs to Gloucester Road, drift and near miss to tram-pinned Hennessy — so **which
route pays more becomes a real choice**. Air has no source geometry today and the flyovers are not
yet drivable; neither is scored until something can be jumped off.

---

## Controls

See `docs/ARCHITECTURE.md` for the action-set mapping across touch/gamepad/keyboard.

**Handling model:** Godot's `VehicleBody3D` with arcade overrides, since `Q50` (2026-08-18). It was a
custom raycast vehicle on `RigidBody3D` until then, and `P0-5a` measured why: `VehicleBody3D`'s wheel friction
is **isotropic**, so a drift cannot break lateral grip without destroying traction and braking with
it. 🔴 **That finding was never refuted — `Q50` accepted it as a cost.** `Q49`'s friction ellipse, and
the `grip_lateral` / `grip_longitudinal` semi-axes it spent from, are gone: `VehicleWheel3D` has one
`wheel_friction_slip`, so the budget is the circle `P0-5a` rejected and `tyre_grip` is the single
number both axes now come out of.

| Property | Target feel |
|---|---|
| Grip | High, forgiving. No spin-outs from small errors. 🔴 **`Q49`'s one-budget-per-tyre coupling is lost** — the ellipse is a circle now, so braking through a corner costs no cornering grip and a power-on corner **accelerates again**, which is the behaviour `Q49` was written to remove. Measured on the skidpad, the corner manoeuvre turns 16% less for the same speed: yaw −358.2° against the raycast car's −428.9° |
| Drift | Button-initiated, easy to hold, scrubs little speed. 🔴 **Not met, but not for the reason published until `Q84`.** The window is *not* 0.01–0.02 wide and 14° *is* reachable: swept at 0.002 rather than 0.02, the response is smooth and monotonic at ~990°/unit and `drift_rear_grip_scale` **0.6695** peaks at exactly 14.0°. The old cliff was a coarse grid read through a `%.2f` label that printed 0.670, 0.668 and 0.665 as one row. 🔴 **What is actually unreachable is holding it**: peak slip and dwell trade against speed on this one dial, so 0.6695 spends **0.05 s** above 14° (exit 48.6 kph), the shipped **0.66 → 21.8° peak, 0.57 s, exit 45.1 kph**, and buying dwell costs speed all the way down — 0.64 → 36.4°/0.77 s/41.1 kph, 0.60 → 75.2°/0.85 s/36.4 kph. "Easy to hold" and "scrubs little speed" are opposite ends of it, which is `Q50`'s isotropic cost stated properly. 🔴 **A tap does nothing at all, and `Q84` built the fix that was supposed to change that and measured no change.** The 0.5 s `tap` returns 1.9° peak with yaw and distance identical to `corner`. The diagnosis was instant grip restoration, so a release ramp was added — `drift_release_s`, on `steer_release_s`'s idiom — and the tap still returns 1.9°. Swept, a 1.0 s release reaches 2.0°, 2.0 s reaches 2.2°, 3.0 s reaches 3.3°; nothing there is a tap any more and none of it is a drift. ⚠️ **The cause is that the slide takes seconds to build, not that it ends too soon** — held, the car is above 14° for 0.57 s of a 4.00 s run, so the bar is not crossed until the fourth second. A locked raycast tyre made yaw the instant it stopped rolling (7.1°); an isotropic wheel has to be driven into saturation, which is a rate and not an event. 🔴 **And `Q85` closed the route all three of those named**: `get_rpm()` is road speed re-expressed, this class carries no wheel inertia, so per-wheel angular velocity cannot be read here at all. ✅ **The button now applies a yaw torque instead** (`drift_yaw_torque_nm`, 1000 at the time and 7000 since `Q86`), which is the game asserting rotation the tyres did not produce — licensed by `Q49`'s own finding that this target is anti-physical. The slide arrives at once rather than in 3.4 s and the angle is a real one: **42.1° peak, 0.78 s above 14°**, against 21.8°/0.57 s. 🔴 **It makes the speed half worse** (exit 45.06 → 40.96 kph), and the tap is still dead at this value — it needs 5000, where the held drift becomes a 162.9° spin. ⚠️ **Torque and grip are multiplicative, not alternatives**: with grip restored the assist is just tighter steering (1.8° slip), so the scrub is intrinsic and no pair of these dials separates "slides a lot" from "scrubs little" (`Q85`). ✅ **The tap is fixed, and `Q86` is how**: torque × time is rotation, so a 0.5 s tap collected one-eighth of a 4 s hold's angular impulse and no constant could serve both. The torque now decays from a peak toward `drift_yaw_sustain` over `drift_yaw_decay_s` — on **time**, never on measured slip, or the angle becomes the dial and `secs>thr` stops grading anything (`Q72`). Shipped at **7000 N⋅m / 0.8 s / 0.0**: the tap goes **2.4° → 16.0°** peak and **0.00 → 0.23 s** above the bar, the hold improves to 51.1°/0.82 s, and exit speed goes **40.96 → 41.29 kph** — the first change here that did not buy angle with speed. 🔴 **But "easy to hold" is still not met and the assist cannot meet it**: `secs>thr` was flat at 0.78–0.85 across all three yaw dials while peak slip ran 40° → 130°, so they buy angle and cost speed and never buy time above the bar. Dwell is the friction mechanism's to give, and `Q85` measured that slide self-terminating at ~1.8 s. ⚠️ **Three further facts about the mechanism no dial reaches** (`Q85`): lifting the throttle cancels the drift outright and re-applying does not recover it, so the genre's *lift-then-flick* entry does not exist here; the gripping turn beats the drift round a 90° corner on speed (63.4 against 52.8 kph) so a drift buys line and time but never pace; and there is **no sustained drift equilibrium at any counter-steer timing** — the car has two stable states, a gripping circle or a spin, so a held Initial-D line round a roundabout is not reachable in this model. 🔴 **And the button was, until `Q88`, only tuned for roughly 40–70 km/h** (`Q87`): every value was picked at the skidpad's single 63 km/h entry, and the assist had no fade-out, so the tap that gives 16.0° there **spun the car at 84**. A speed fade (`drift_fade_from_kph`/`_to_kph`, 65/85) fixes the assist's share — the 105 km/h tap goes 163.3° to **17.5°**, and its distance 39.2 → **80.0 m** — but with the assist switched off entirely the held drift still reads **95.2° at 86 km/h and 165.2° at 105**, because `drift_rear_grip_scale` spins the car on its own and carries **no speed term at all**. ✅ **That half is fixed too, and `Q88` is how**: `drift_rear_grip_scale_at_top` **0.80**, interpolated from the shared knee to `max_speed_kph` because the grip value the car wants *moves* with speed. **The spin is gone at every speed** — 86 km/h now reads **50.4°/0.98 s**, which reproduces the design-speed feel (51.1°/0.82), and 105 km/h reads 2.4° with its exit speed **21.95 → 70.14 kph**. The city tap that dropped the car to 27.69 kph now holds **76.00** against a 76.60 no-drift baseline. ⚠️ **The cost, plainly: the drift is inert above about 100 km/h.** A real 75.8° drift there is reachable at 0.78 and was refused — it sits 0.01 from a cliff down to 2.8°, and `Q84` is what this project already paid for a narrow band on this dial. So "easy to hold" is now honest rather than inverted: the button works up to ~100 km/h and stops working above it, instead of spinning you. ⚠️ **But the band has a bottom nobody has tuned, and it is where the game is played**: below ~50 km/h the drift returns **2.9–3.9°** and the car *accelerates* through the manoeuvre rather than scrubbing (`decay/s` goes negative), so the usable band is really **60–100 km/h** while typical city driving sits under it. Not caused by the tapers — nothing below the knee is touched — it is `Q84`'s momentum dependence, and it means the drift is least available exactly where it would be most used. ⬜ Unaddressed, and no current dial reaches it |
| Collision | Glancing hits deflect; head-on hits cost speed, never control |
| Recovery | Auto-righting if flipped, within ~1 s |
| Reverse | Instant, no gear delay |
| Braking | Strong (~0.8 g) and **as speed-uniform as the engine allows** — Godot's viscous `default_linear_damp` still costs 17% between 65 and 4 km/h, against 36% before `P0-5b/c/d`. Must also out-pull Wan Chai's ramps: `gravity_scale` 1.6 makes a slope pull 60% harder than its angle suggests |
| Coasting | Sheds a similar speed per second at 5 km/h as at 50, and **comes to a stop**. One pedal serves brake and reverse, so a driver arriving at walking pace has to lift off — coasting is the only thing that can park the car (`P0-5b/c/d`) |

All values live in `game/tuning/handling.tres`. **Expect to iterate on these more than any other part
of the project** — vehicle feel is the single biggest determinant of whether this is fun.

Two items were flagged during `P0-5d` and deliberately left for `P2-3`'s tuning pass. Sustained full
lock still spins the car. The second — `brake_force` giving 3 m/s² of braking against 5.33 m/s² of
acceleration, so **the car accelerated faster than it stopped** — was ✅ **closed 2026-08-17** at
`brake_force` 2,400 N: braking is now 8.0 m/s² and the inequality is the right way round
(`P0-5b/c/d`).

---

## Hong Kong authenticity mechanics

Ranked by impact-to-effort. The top four are where the "feels like HK" verdict is won.

| Mechanic | Effort | Source |
|---|---|---|
| **Bilingual destination callouts** | Trivial | `fares.json` |
| **Red urban taxi livery** | Trivial | Hand-authored. HK Island = red. Green or blue reads as *wrong* |
| **Trams as moving walls** | Low | Hand-authored on Hennessy/Johnston. Slow, wide, unpassable |
| **Bus lanes as penalty zones** | Low | `bus_lane` in `roadgraph.json` |
| Double-decker buses as sight blockers | Low | Traffic AI vehicle type |
| Bamboo scaffolding on buildings | Low | Prop instancing |
| Minibuses that stop abruptly | Medium | Traffic AI behaviour variant |
| Cross-harbour tunnel queue | Medium | Static congestion at the tunnel approach |
| Neon signage overhanging streets | Medium | Instanced props + emissive shader |

> **Trams are the highest-leverage single object in the game.** They constrain lane choice exactly the
> way they do in reality, they are instantly recognisable, and they cost far less than modelling
> another building.

⚠️ **Nothing in the table above is built yet, and neon is the highest-value gap.** **Sleeping Dogs**
is the nearest commercial precedent for a recognisable Hong Kong, and the common reading of why it
worked is signage density and overhanging shopfront light rather than street accuracy. Untested here
— but it names a failure mode `P3-9` should be listened to for, because *"the streets are bare"* and
*"the streets are wrong"* have completely different fixes.

Cheap when it comes: `ART_DESIGN.md` already reserves the emissive channel for the night variant, and
the signs are instanced props rather than anything the ETL derives. Not in the slice; first thing to
reach for once `P3-9` reports.

---

## Traffic AI

- Vehicles follow road-graph edges, respecting `direction`, `speed_limit_kph` and
  `turn_restrictions`. **The AI obeys the real rules; the player does not.**
- Density scales with the performance tier.
- Vehicle mix: private cars, red taxis, double-deckers, minibuses, trams (scripted, on fixed routes),
  delivery trucks.
- AI reacts to the player only minimally — braking for imminent collision. It should feel like
  traffic, not like opponents.

⚠️ One turn restriction in the region **excludes taxis**, and `roadgraph.json` has no field for that,
so the graph currently forbids a turn a real red taxi may make. Adding it is a schema change on both
sides.

---

## Region and free-slice boundary

PoC region is **Wan Chai → Causeway Bay** (see `docs/DATA_SOURCES.md` for bounds).

**Design Wan Chai to be standalone-playable.** It becomes the free tier and the web demo; Causeway
Bay and later Central are the unlock. Build this seam now even though monetisation is deferred — it
costs nothing during the vertical slice and keeps the launch model open.

### The circuit

The region's core gameplay asset is a real, natural loop:

```
Gloucester Road (east, fast, 4-6 lanes)
      ↓
Canal Road Flyover (elevated, the vertical beat)
      ↓
Hennessy Road (west, tram-pinned, technical)
      ↓
Fleming / Fenwick (cross-connectors)
      ↓  back to Gloucester
```

Fast spine plus technical parallel is the contrast arcade driving lives on — and here it already
exists in the real road layout. **The flyover half of that loop needs `P4-1`** before it is drivable.

**Map edges are diegetic:** Victoria Harbour north, the escarpment toward Kennedy Road south,
Admiralty west, Victoria Park east. No invisible walls needed.

---

## Modes

| Mode | Status | Notes |
|---|---|---|
| **Arcade** | Vertical slice | The main mode. Chain fares against the clock |
| **Free roam** | Vertical slice | No timer. Essential for playtesting and for the authenticity test. The state `Q8` was judged in — no fare, no timer, no arrow. Also where `P3-9` runs |
| Time trial | Later | Fixed A→B, leaderboard |
| Daily challenge | Later | Seeded fare sequence |

**`Q8` was judged in that state, though not in this mode.** The verdict that closed the project's top
risk came from a *dev scene*, driving the city with no fare, timer or arrow. Free roam is what turns
that state into something a player can reach, which is why it is in the slice rather than left as a
harness.

---

## Acceptance test

**Hand the build to a Hong Kong driver, disable the minimap and the direction arrow, and name a
destination.** If they can drive from the Convention Centre to Times Square from memory, using the
correct one-way streets, the city reads as Hong Kong.

If they need the minimap, the geometry is decorative and the pillar has failed. This test also reveals
*where* it fails, which side-by-side screenshot comparison never does.

Run it at the end of every phase from Phase 3 onward, with at least three different drivers.

---

## Anti-goals

Explicitly **not** building:

- A driving simulator. No realistic physics, damage modelling, or fuel.
- Energy timers, lives, or any session-gating monetisation.
- Gacha, loot boxes, or randomised rewards — including the wheelspin shape.
- Live-service, seasons, or anything always-online (hard rule 2: zero runtime network calls).
- Licensed-car collection as a progression spine. The art direction is 800–2,000-triangle toys.
- Pedestrians as collision targets. Keep pavements empty, or treat pedestrians as non-collidable
  ambience.
- An open-world map of all Hong Kong. Scope is deliberately one corridor.
- Multiplayer.
