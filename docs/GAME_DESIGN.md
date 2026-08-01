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

**Handling model:** custom raycast vehicle on `RigidBody3D` with arcade overrides — not Godot's
`VehicleBody3D`, and not a physical simulation. `P0-5a` measured why: `VehicleBody3D`'s wheel friction
is **isotropic**, so a drift cannot break lateral grip without destroying traction and braking with
it.

| Property | Target feel |
|---|---|
| Grip | High, forgiving. No spin-outs from small errors |
| Drift | Button-initiated, easy to hold, scrubs little speed |
| Collision | Glancing hits deflect; head-on hits cost speed, never control |
| Recovery | Auto-righting if flipped, within ~1 s |
| Reverse | Instant, no gear delay |

All values live in `game/tuning/handling.tres`. **Expect to iterate on these more than any other part
of the project** — vehicle feel is the single biggest determinant of whether this is fun.

Two items flagged during `P0-5d` and deliberately left for `P2-3`'s tuning pass: sustained full lock
still spins the car, and `brake_force` gives 3 m/s² of braking against 5.33 m/s² of acceleration, so
**the car accelerates faster than it stops.**

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
