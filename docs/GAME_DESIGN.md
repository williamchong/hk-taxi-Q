# Game Design

## Pillars

1. **It must feel like Hong Kong to a Hong Kong driver.** Recognition beats fidelity. A local
   should navigate by memory, not by minimap.
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
| Road topology and connectivity | Road **width** — widen ~1.3–1.8× |
| One-way directions and turn restrictions (for **AI traffic**) | Player rule-breaking — always allowed |
| Building massing and position | Pedestrian railings — omit or make breakable |
| Landmark placement | Ramps, jumps, plaza shortcuts — hand-added |
| Street and place names | Kerb heights — flatten for mountability |

The player may break every traffic rule. The AI obeys them. That asymmetry is what makes the city
read as real while staying playable.

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

Session ends when the **global session timer** expires. Delivering fares adds time to it. This is
the genre's classic structure: the game ends when you stop being good.

- **Session length:** 3–5 minutes typical; skilled play extends it.
- **Restart:** instant, one tap. No loading screen between runs.

---

## Fares

### Sources

Fare nodes come from `fares.json`, built from the Taxi Stands and Taxi Pick-up & Drop-off Points
datasets, plus hand-added POIs.

### Fare types

| Type | Source | Time allowance | Payout | Notes |
|---|---|---|---|---|
| Short hop | `pudo` | 30 s | 1× | Common; keeps the chain alive |
| Standard | `taxi_stand` (urban) | 60 s | 2× | The default fare |
| Long haul | `poi`, cross-district | 90 s | 4× | Rewards route knowledge |
| **Cross-harbour** | `taxi_stand` where category = `cross_harbour` | 75 s | 5× | Terminates at the tunnel approach |

**The cross-harbour fare is the signature mechanic.** It exists only because the source dataset
distinguishes that stand category, it pays the most, and it ends at a map boundary that is
diegetic rather than arbitrary. No other city's version of this game has it.

### Destination presentation

Destinations are announced **by name, bilingually** — `Times Square / 時代廣場`, `會展`,
`灣仔碼頭` — never by street address. Hong Kong drivers navigate by landmark name, and this is the
cheapest, highest-impact authenticity lever in the game. Names ship in `fares.json`.

A directional arrow assists, but the **acceptance test is that a local can find the destination
with the arrow disabled.**

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
| **Combo** | Consecutive deliveries without a fail; multiplier climbs, resets on bail |

Style points are awarded **during** the drive and shown immediately — the feedback loop must be
tight enough that players learn what the game rewards without being told.

---

## Controls

See `docs/ARCHITECTURE.md` for the action-set mapping across touch/gamepad/keyboard.

**Handling model:** custom raycast vehicle on `RigidBody3D` with arcade overrides — not Godot's
`VehicleBody3D`, and not a physical simulation. `P0-5a` measured why; see `docs/PROGRESS.md`.

| Property | Target feel |
|---|---|
| Grip | High, forgiving. No spin-outs from small errors. |
| Drift | Button-initiated, easy to hold, scrubs little speed |
| Collision | Glancing hits deflect; head-on hits cost speed, never control |
| Recovery | Auto-righting if flipped, within ~1 s |
| Reverse | Instant, no gear delay |

All values live in `game/tuning/handling.tres`. **Expect to iterate on these more than any other
part of the project** — vehicle feel is the single biggest determinant of whether this is fun.

---

## Hong Kong authenticity mechanics

Ranked by impact-to-effort. The top four are where the "feels like HK" verdict is won.

| Mechanic | Effort | Source |
|---|---|---|
| **Bilingual destination callouts** | Trivial | `fares.json` |
| **Red urban taxi livery** | Trivial | Hand-authored. HK Island = red. Green or blue reads as *wrong*. |
| **Trams as moving walls** | Low | Hand-authored on Hennessy/Johnston. Slow, wide, unpassable. |
| **Bus lanes as penalty zones** | Low | `bus_lane` in `roadgraph.json` |
| Minibuses that stop abruptly | Medium | Traffic AI behaviour variant |
| Cross-harbour tunnel queue | Medium | Static congestion at the tunnel approach |
| Double-decker buses as sight blockers | Low | Traffic AI vehicle type |
| Bamboo scaffolding on buildings | Low | Prop instancing |
| Neon signage overhanging streets | Medium | Instanced props + emissive shader |

> **Trams are the highest-leverage single object in the game.** They constrain lane choice exactly
> the way they do in reality, they are instantly recognisable, and they cost far less than
> modelling another building.

---

## Traffic AI

- Vehicles follow road-graph edges, respecting `direction`, `speed_limit_kph`, and
  `turn_restrictions`. **The AI obeys the real rules; the player does not.**
- Density scales with the performance tier.
- Vehicle mix: private cars, red taxis, double-deckers, minibuses, trams (scripted, on fixed
  routes), delivery trucks.
- AI reacts to the player only minimally — braking for imminent collision. It should feel like
  traffic, not like opponents.

---

## Region and free-slice boundary

PoC region is **Wan Chai → Causeway Bay** (see `docs/DATA_SOURCES.md` for bounds).

**Design Wan Chai to be standalone-playable.** It becomes the free tier and the web demo; Causeway
Bay and later Central are the unlock. Build this seam now even though monetisation is deferred —
it costs nothing during the vertical slice and keeps the launch model open.

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
exists in the real road layout.

**Map edges are diegetic:** Victoria Harbour north, the escarpment toward Kennedy Road south,
Admiralty west, Victoria Park east. No invisible walls needed.

---

## Modes

| Mode | Status | Notes |
|---|---|---|
| **Arcade** | Vertical slice | The main mode. Chain fares against the clock. |
| **Free roam** | Vertical slice | No timer. Essential for playtesting and for the authenticity test. |
| Time trial | Later | Fixed A→B, leaderboard |
| Daily challenge | Later | Seeded fare sequence |

---

## Acceptance test

**Hand the build to a Hong Kong driver, disable the minimap and the direction arrow, and name a
destination.** If they can drive from the Convention Centre to Times Square from memory, using the
correct one-way streets, the city reads as Hong Kong.

If they need the minimap, the geometry is decorative and the pillar has failed. This test also
reveals *where* it fails, which side-by-side screenshot comparison never does.

Run it at the end of every phase from Phase 3 onward, with at least three different drivers.

---

## Anti-goals

Explicitly **not** building:

- A driving simulator. No realistic physics, damage modelling, or fuel.
- Energy timers, lives, or any session-gating monetisation.
- Gacha, loot boxes, or randomised rewards.
- Pedestrians as collision targets. (Avoid the genre's tonal baggage; keep pavements empty or
  treat pedestrians as non-collidable ambience.)
- An open-world map of all Hong Kong. Scope is deliberately one corridor.
- Multiplayer.
