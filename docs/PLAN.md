# Plan — Vertical Slice

**Scope:** prove three things before committing to full production.

1. The ETL pipeline works on real HK open data.
2. The driving is fun.
3. The city reads as Hong Kong to Hong Kong drivers.

**Out of scope for the slice:** monetisation, store assets, art polish, audio beyond placeholders,
Causeway Bay and Central, all modes except Arcade and Free Roam.

Task IDs are stable — reference them in commits and in `PROGRESS.md`.

---

## Phase 0 — Spikes and scaffolding

**Goal:** kill the unknowns that could invalidate the whole plan, before building on them.
Run these **in parallel**; `P0-2` is the one that can force a region change.

### `P0-1` Identify source data granularity
- **Deliverable:** documented list of LandsD 1:1000 sheet numbers covering the region; confirmation
  of whether non-textured glTF is delivered per sheet or per tile; one sheet downloaded by hand.
- **Accept:** `docs/DATA_SOURCES.md` "Access notes" open questions resolved; a real file on disk.
- **Deps:** none.

### `P0-2` ⚠️ Z-value spike — HIGHEST RISK
- **Deliverable:** a definitive answer to whether Road Network v2 centreline geometry carries a Z
  ordinate, with evidence (a parsed sample showing coordinate tuples).
- **Accept:** answer recorded in `PROGRESS.md`. If **no Z**, evaluate the three fallbacks in
  `docs/DATA_SOURCES.md` and record which is chosen.
- **Deps:** none.
- **Why first:** without elevation, every flyover becomes a false at-grade junction — and the Canal
  Road Flyover and elevated Gloucester Road are the most interesting driving in the region. A bad
  answer may force a move to Tsim Sha Tsui.

### `P0-3` Godot project scaffold
- **Deliverable:** `game/` opens in Godot 4.7; Mobile renderer configured; export presets for iOS,
  Android, desktop, and web-demo committed as configuration; a scene that renders a cube at 60fps.
- **Accept:** project imports with no errors; FPS counter visible; desktop and web presets export
  successfully.
- **Deps:** none.
- **Note:** the original acceptance criterion read "builds and runs on the device floor". That
  needs the Android SDK, Xcode, a signing identity and a physical 2019-era handset — a separate
  piece of work, not a scaffold. Split out as `P0-3b`.

### `P0-3b` Mobile device build verification
- **Deliverable:** a signed development build installed and running on the device floor, on both
  an iOS and an Android handset. Real reverse-domain bundle identifier replacing the placeholder
  in `export_presets.cfg`.
- **Accept:** the cube scene (or whatever `P0-5` has produced by then) runs on-device with the FPS
  counter visible; measured FPS recorded in `PROGRESS.md`.
- **Deps:** `P0-3`. Also needs `Q4` (device floor) confirmed and physical hardware on hand.
- **Note:** not on the critical path — `P0-5` does not depend on it. But it must land before
  `P2-6` can measure anything meaningful.

### `P0-4` ETL scaffold
- **Deliverable:** `etl/` Python package; `hong_kong.yaml` config; `crs.py` with EPSG:2326 →
  game-space transform; `ruff` + `pytest` configured.
- **Accept:** `pytest` passes with round-trip transform tests against known HK1980 reference points.
- **Deps:** none.

### `P0-5` Grey-box fun test
- **Deliverable:** a hand-built block of "Gloucester Road" — placeholder boxes, correct road widths
  — plus a tuned custom raycast vehicle on `RigidBody3D` (see `P0-5a` in `docs/PROGRESS.md`).
- **Accept:** **the user drives it and confirms it feels good.** This is a subjective gate and it
  is meant to be.
- **Deps:** `P0-3`.
- **Why early:** answers "is this a game?" before any ETL investment. If the driving isn't fun with
  boxes, real geometry will not save it.

> **Phase 0 gate:** do not start Phase 1 until `P0-2` is answered and `P0-5` has passed.

---

## Phase 1 — ETL vertical slice

**Goal:** real Wan Chai data → game-ready assets, reproducibly, with one command.

### `P1-1` Source fetching
- **Deliverable:** `fetch.py` downloads and caches the region's building, road, and fare datasets
  from CSDI / data.gov.hk into `etl/sources/`.
- **Accept:** re-running is idempotent and uses the cache; a fresh clone can fetch from scratch.
- **Deps:** `P0-1`, `P0-4`.

### `P1-2` Building meshes
- **Deliverable:** `buildings.py` — parse non-textured glTF / 3D-BIT00, clip to region, assign
  vertex colours by height band and class, merge per tile, emit LOD0–2.
- **Accept:** a tile `.glb` loads in Godot; under 3 draw calls per tile; vertex colours present;
  no textures in output.
- **Deps:** `P1-1`.

### `P1-3` Road graph
- **Deliverable:** `roads.py` — parse Road Network v2, extract nodes/edges, map `TRAVEL_DIRECTION`
  and `TURN_ID` restrictions, emit `roadgraph.json` per the data contract.
- **Accept:** schema-valid; graph is connected across the region; one-way directions spot-checked
  against reality on Lockhart and Jaffe Road; turn restrictions non-empty.
- **Deps:** `P1-1`, `P0-2`.
- **Note:** handle the known source quirks — dual carriageways as split one-ways, single junctions
  represented as two intersections.

### `P1-4` Road surface mesh
- **Deliverable:** ribbon mesh generated from road-graph polylines, with **widening applied**
  (~1.3–1.8×, per-class, from config), kerbs, and collision geometry.
- **Accept:** drivable surface with no gaps at junctions; widening factor is config-driven, not
  hardcoded.
- **Deps:** `P1-3`.

### `P1-5` Fare nodes
- **Deliverable:** `fares.py` — taxi stands + PUDO points → `fares.json`, snapped to the nearest
  road edge, with bilingual names.
- **Accept:** schema-valid; every node's `nearest_edge` resolves; `cross_harbour` category
  preserved; names populated in both `en` and `zh`.
- **Deps:** `P1-3`.

### `P1-6` Export and manifest
- **Deliverable:** `export.py` writes `city.json` plus all assets to `etl/out/`; one command runs
  the full pipeline.
- **Accept:** `python -m pipeline --city hong_kong --region wan_chai` produces a complete,
  schema-valid output set from a clean state.
- **Deps:** `P1-2`, `P1-4`, `P1-5`.

### `P1-7` Godot import
- **Deliverable:** Godot loads `city.json` and instantiates tiles at correct world positions.
- **Accept:** Wan Chai renders in-editor, correctly georeferenced, no z-fighting.
- **Deps:** `P1-6`, `P0-3`.

> **Phase 1 gate:** a screenshot of real Wan Chai massing rendering in Godot.

---

## Phase 2 — Driving the real city

**Goal:** the player drives real Wan Chai at 60fps on the device floor.

| ID | Deliverable | Accept | Deps |
|---|---|---|---|
| `P2-1` | `CityStreamer` — tile load/unload by distance, LOD switching | No hitching on tile boundaries; draw calls within budget | `P1-7` |
| `P2-2` | `RoadGraph` runtime — load JSON, nearest-edge and lane-centre queries | Query correctness unit-tested; sub-millisecond nearest-edge | `P1-3` |
| `P2-3` | `VehicleController` — custom raycast vehicle on `RigidBody3D`, arcade tuning in `handling.tres` | Matches the feel agreed in `P0-5`, now on real geometry | `P0-5`, `P1-7` |
| `P2-4` | `InputRouter` — touch, gamepad, keyboard → one action set | All three input paths drive the car; no gameplay script reads raw input | `P2-3` |
| `P2-5` | Chase camera with speed-based FOV and look-back | Readable at speed; no clipping through buildings | `P2-3` |
| `P2-6` | Performance pass to budget | 60fps on device floor, measured, recorded in `PROGRESS.md` | `P2-1`…`P2-5` |

> **Phase 2 gate:** 60fps on the device floor while driving real Wan Chai geometry.

---

## Phase 3 — Playable slice

**Goal:** a complete arcade loop that passes the authenticity test.

| ID | Deliverable | Accept | Deps |
|---|---|---|---|
| `P3-1` | `FareSystem` — hail → carry → deliver/fail state machine; 4 fare types | Full loop playable; cross-harbour fare works | `P1-5`, `P2-2` |
| `P3-2` | `ScoreSystem` — base, time bonus, drift/near-miss/air/speed, combo | Style points award live during driving | `P3-1` |
| `P3-3` | `TrafficSystem` — AI on road-graph splines obeying direction and turn restrictions | Traffic obeys real rules; density scales by perf tier | `P2-2` |
| `P3-4` | Trams on Hennessy/Johnston as scripted moving blockers | Unpassable, correctly routed, tram bell audio | `P3-3` |
| `P3-5` | HUD — meter, timer, arrow, bilingual destination callouts | Readable one-handed in daylight; safe areas respected | `P3-1` |
| `P3-6` | Hero buildings (5) authored and placed via `landmarks.json` | Source geometry excluded; no z-fighting | `P1-7` |
| `P3-7` | Window-band shader | Reads as HK density; no windows on roofs or podium faces | `P1-2` |
| `P3-8` | Bus-lane penalty + red taxi livery + minibus behaviour | Penalty triggers from `bus_lane` flag | `P3-3` |
| `P3-9` | **Authenticity test round 1** | ≥3 HK drivers navigate Convention Centre → Times Square with arrow disabled | all above |

> **Phase 3 gate — go/no-go on full production.**
> Required: `P3-9` passes; 60fps held on the device floor; the user judges the game fun.

---

## After the slice (outline only — refine once Phase 3 lands)

- **Phase 4 — Content:** Causeway Bay, then Central. Full vehicle roster, audio pass, night mode.
- **Phase 5 — Production polish:** menus, settings, save/progression, accessibility, localisation QA.
- **Phase 6 — Ship:** free-slice boundary implemented, one-time unlock IAP, store assets, web demo
  build, HK press outreach, legal sight-check of landmark depiction.

These are deliberately not broken down. Anything planned in detail now would be a guess, and the
slice will change the assumptions.

---

## Working agreements for agents

- Reference the task ID in every commit.
- Update `docs/PROGRESS.md` when a task changes status, and whenever a decision or open question
  arises.
- If a task's acceptance criteria turn out to be wrong, say so and propose a change rather than
  quietly redefining it.
- Do not start a task whose dependencies are unmet without flagging it.
