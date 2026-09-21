# Game Design

## Pillars

1. **It must feel like Hong Kong to a Hong Kong driver.** Recognition beats fidelity. A local should
   navigate by memory, not by minimap.
2. **Arcade, not simulation.** Three-minute sessions, instant restart, forgiving collision,
   unrealistic grip. Fun outranks accuracy whenever they conflict.
3. **Readable at a glance.** Two thumbs on a phone, on a bus, in daylight (`Q97`); one-handed stays
   the deferred accessibility option (`auto_accelerate`, `P3-5b`).

## The central design tension

Real geometry fights arcade fun, and fun wins. The open data is a skeleton, not ground truth.

| Use the real data for | Deliberately diverge on |
|---|---|
| Road topology and connectivity | Road width — a minimum drawn width at grade (10.24 m; 12.48 m on ≥70 kph roads; a floor, not a multiplier, `Q95`), but authored width on structure: a widened ribbon overhangs its own deck |
| One-way directions and turn restrictions (for AI traffic) | Player rule-breaking — always allowed |
| Building massing and position | Pedestrian railings — drawn, no collider (`P3-19`); breakaway and collision wait for `B3` |
| Landmark placement | Ramps, jumps, shortcuts — hand-added, sparingly |
| Street and place names | Kerb heights — flattened for mountability |

The player may break every traffic rule; the AI obeys them. That asymmetry makes the city read as
real while staying playable.

⚠️ The divergences are not equally cheap. Width, kerbs and railings are invisible to a driver's
memory of a street; a hand-added ramp is new geometry somewhere the player knows, and a debit
against the acceptance test below. Prefer the shortcut that is there — the Canal Road Flyover, the
elevated Gloucester approach, the plaza gaps, the alley grid. The ramps are in the source data:
`P2-7` put the carriageway on them and `P4-1` (`Q111`) opened them to driving; `Q19`'s at-grade
blockers were carved and fenced (`P3-28`, `P3-29`). Invent a ramp only where a specific stretch is
demonstrably dead, and record it as a decision.

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

The session ends when the global session timer expires; delivering fares adds time to it.

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

The cross-harbour fare is the signature mechanic: the source dataset distinguishes that stand
category, it pays the most, and it ends at a diegetic map boundary. The fare terminates at the
tunnel approach, which is in the region at street level — three `CROSS HARBOUR TUNNEL` edges at
elevation level 0 join ordinary streets through `WAN CHAI INTERCHANGE`. The six cross-harbour
stands sit 191 m to 1,044 m from the portal; 191 m is barely a trip, so `P3-1` needs a minimum
length or a different destination for the near ones. Whether stopping at a portal feels like
completing the fare is a `P3-9` question.

### Destination presentation

Destinations are announced by name, bilingually — `Times Square / 時代廣場`, `會展`, `灣仔碼頭` —
never by street address. Hong Kong drivers navigate by landmark name. Names ship in `fares.json`.

A directional arrow assists, but the acceptance test is that a local can find the destination with
the arrow disabled.

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

Style points are awarded during the drive and shown immediately, so players learn what the game
rewards without being told.

⚠️ They accumulate into a *style chain* rather than popping and clearing — a deliberate divergence
from the genre's per-event bonus: only a multiplier that can be lost makes the next corner tense.
"Chain" elsewhere in this document means the fare sequence, so the style one is always the *style
chain*.

| | Scope | Climbs on | Resets on |
|---|---|---|---|
| **Style chain** | Seconds of driving | Style components | A hard crash, or going quiet after it banks |
| **Fare combo** | The session | Consecutive deliveries | A bailed fare |

Sustained speed belongs to Gloucester Road, drift and near miss to tram-pinned Hennessy, so which
route pays more is a real choice. Air is not scored until something can be jumped off.

---

## Controls

See `docs/ARCHITECTURE.md` for the action-set mapping across touch/gamepad/keyboard.

**Handling model:** Godot's `VehicleBody3D` with arcade overrides (`Q50`). ⚠️ Its wheel friction is
isotropic (`P0-5a`, never refuted; `Q50` accepted it as a cost): one `wheel_friction_slip`, one
`tyre_grip`, no friction ellipse (`Q49`'s is gone). All values live in `game/tuning/handling.tres`;
grade every change on `tools/skidpad.sh` and tune against a measurement, never a number written
here. See `.claude/rules/handling.md`.

| Property | Target feel |
|---|---|
| Grip | High, forgiving. No spin-outs from small errors. ⚠️ Braking through a corner costs no cornering grip and a power-on corner accelerates — `Q49`'s one-budget coupling is lost |
| Drift | Button-initiated, easy to hold, scrubs little speed. Partly met — see below |
| Collision | Glancing hits deflect; head-on hits cost speed, never control |
| Recovery | Auto-righting if flipped, within ~1 s |
| Reverse | Instant, no gear delay |
| Braking | Strong (~0.9 g, 8.75 m/s²; `brake_force` 40, a post-`Q50` unit that does not convert from newtons) and as speed-uniform as the engine allows. Must out-pull the ramps: `gravity_scale` 1.6 makes a slope pull 60% harder than its angle suggests. The car must stop faster than it accelerates |
| Coasting | Sheds a similar speed per second at 5 km/h as at 50, and comes to a stop. One pedal serves brake and reverse, so coasting is the only thing that can park the car (`P0-5b/c/d`) |

### The drift as shipped

- Three mechanisms: a rear grip cut (`drift_rear_grip_scale` 0.66), a yaw torque that decays on
  **time**, never on measured slip (`drift_yaw_torque_nm` 7000, `drift_yaw_decay_s` 0.8,
  `drift_yaw_sustain` 0.0; `Q85`, `Q86`), and speed envelopes: `drift_rear_grip_scale_at_top` 0.80
  with the assist faded 65 → 85 km/h (`drift_fade_from_kph`, `drift_yaw_fade_to_kph`; `Q87`, `Q88`),
  and `drift_rear_grip_scale_at_low` 0.44 below `drift_low_fade_kph` 41 (`Q89`).
- Works 34–86 km/h with 0.42–0.98 s above the 14° bar; design speed 63 km/h reads 69.8° held, 20.5°
  tapped. Figures in `Q84`/`Q86` describe a superseded car.
- ⚠️ Inert above about 100 km/h by choice: a real drift there (grip 0.78) sits 0.01 from a cliff
  and was refused (`Q88`).
- ⚠️ The low branch latches at engagement where the high branch tracks (`Q89`): deepening the cut
  as speed falls is positive feedback, and built as a tracker it spun the design speed to 165°.
- ⚠️ Grade the dial on dwell (`secs>thr`), never on landing peak slip on the threshold (`Q84`): peak
  slip and dwell trade against exit speed on the one dial, so "easy to hold" and "scrubs little
  speed" are opposite ends of it. The yaw dials buy angle and cost speed; they never buy dwell.
- Not reachable in this model (`Q85`): `get_rpm()` is road speed, so wheel spin cannot be read;
  lifting the throttle cancels the drift (no lift-then-flick entry); a gripping turn beats the drift
  round a 90° corner (63.4 against 52.8 kph), so a drift buys line, never pace; there is no
  sustained drift equilibrium — a gripping circle or a spin.
- ⬜ Open: the tap is dead below the design speed (3.9° at 42 km/h), and the yaw assist cannot fix
  it — there, unbroken grip turns torque into a tighter line (`Q89`). Sustained full lock spinning
  the car was never re-measured after `Q50`; re-grade before citing it.

⚠️ Touch carries three of five actions (`Q97`): steer, accelerate, brake/reverse. Drift and
`look_back` stay keyboard/gamepad until `P0-3b`'s handset can price the gesture.

Driving against a one-way raises a blinking NO ENTRY disc (`Q81`, `P3-25`): raised by the car's
nose (velocity may only withhold it), a 120° bar and dwells against false alarms in a region 93.5%
one-way by drivable length, blink under the 3 Hz WCAG ceiling. It informs; it does not penalise.

---

## Hong Kong authenticity mechanics

Ranked by impact-to-effort. The top four are where the "feels like HK" verdict is won.

| Mechanic | Effort | Source |
|---|---|---|
| **Bilingual destination callouts** | Trivial | `fares.json` |
| **Red urban taxi livery** | Trivial | ✅ Shipped (`P3-11`): red, silver roof. HK Island = red; green or blue reads as wrong |
| **Trams as moving walls** | Low | Rails are published data (`P3-14`, `tram.glb`); the moving vehicle is outstanding (`P3-4`), its route no longer hand-authored |
| **Bus lanes as penalty zones** | Low | `bus_lane` in `roadgraph.json` |
| Double-decker buses as sight blockers | Low | Traffic AI vehicle type |
| Bamboo scaffolding on buildings | Low | Prop instancing |
| Minibuses that stop abruptly | Medium | Traffic AI behaviour variant |
| Cross-harbour tunnel queue | Medium | Static congestion at the tunnel approach |
| Neon signage overhanging streets | Medium | Instanced props + emissive shader |

> **Trams are the highest-leverage single object in the game.** They constrain lane choice as they
> do in reality, are instantly recognisable, and cost far less than another building.

Only the livery and the tram rails are built. Neon is the highest-value gap: the common reading of
why Sleeping Dogs' Hong Kong worked is signage density, not street accuracy — untested here, but
`P3-9` should listen for it, because "the streets are bare" and "the streets are wrong" have
different fixes. The night variant is blocked on `Q38` and `Q82` refused lit lanterns, so neon
would have to be justified in the daylight rig — unpriced. Not in the slice; first thing to price
once `P3-9` reports.

---

## Traffic AI

- Vehicles follow road-graph edges, respecting `direction`, `speed_limit_kph` and
  `turn_restrictions`. The AI obeys the real rules; the player does not.
- Density scales with the performance tier.
- Vehicle mix: private cars, red taxis, double-deckers, minibuses, trams (scripted, fixed routes),
  delivery trucks.
- AI reacts to the player minimally — braking for imminent collision. Traffic, not opponents.

⚠️ One turn restriction in the region excludes taxis and `roadgraph.json` has no field for that, so
the graph forbids a turn a real red taxi may make. Adding it is a schema change on both sides.

---

## Region and free-slice boundary

PoC region is **Wan Chai → Causeway Bay** (bounds in `docs/DATA_SOURCES.md`).

Design Wan Chai to be standalone-playable: it becomes the free tier and the web demo; Causeway Bay
and later Central are the unlock. The seam costs nothing now and keeps the launch model open.

### The circuit

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

Fast spine plus technical parallel is the contrast arcade driving lives on, and it exists in the
real layout. The flyover half rests on `P4-1` (`Q111`); `P4-2`–`P4-5` are not started.

**Map edges are diegetic:** Victoria Harbour north, the escarpment toward Kennedy Road south,
Admiralty west, Victoria Park east. No invisible walls needed.

---

## Modes

| Mode | Status | Notes |
|---|---|---|
| **Arcade** | Vertical slice | The main mode. Chain fares against the clock |
| **Free roam** | Vertical slice | No timer, fare or arrow — the state `Q8` was judged in (from a dev scene), made reachable by a player. Where `P3-9` runs |
| Time trial | Later | Fixed A→B, leaderboard |
| Daily challenge | Later | Seeded fare sequence |

---

## Acceptance test

**Hand the build to a Hong Kong driver, disable the minimap (`--minimap=off`) and the direction
arrow, and name a destination.** If they can drive from the Convention Centre to Times Square from memory, using the
correct one-way streets, the city reads as Hong Kong. If they need the minimap, the pillar has
failed — and the test shows where, which screenshot comparison never does.

Run it at the end of every phase from Phase 3 onward, with at least three different drivers.

Round 0 (`P3-9a`, no-HUD free roam, 2026-08-30): three HK drivers recognised Wan Chai from geometry
alone. The sessions ended on `Q19`'s blocked bridges; who said what was not captured and the build
cannot be tied to a commit (`P3-9a′`). `P3-9` remains the handset test, with different drivers —
that cohort has learnt the map.

---

## Anti-goals

Explicitly **not** building:

- A driving simulator. No realistic physics, damage modelling, or fuel.
- Energy timers, lives, or any session-gating monetisation.
- Gacha, loot boxes, or randomised rewards — including the wheelspin shape.
- Live-service, seasons, or anything always-online (hard rule 2: zero runtime network calls).
- Licensed-car collection as a progression spine. The art direction is 800–2,000-triangle toys.
- Pedestrians as collision targets. Keep pavements empty, or non-collidable ambience.
- An open-world map of all Hong Kong. Scope is deliberately one corridor.
- Multiplayer.
