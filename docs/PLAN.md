# Plan — Vertical Slice

**Scope:** prove three things before committing to full production.

1. The ETL pipeline works on real HK open data.
2. The driving is fun.
3. The city reads as Hong Kong to Hong Kong drivers.

**Out of scope for the slice:** monetisation, store assets, art polish, audio beyond placeholders,
Causeway Bay and Central, all modes except Arcade and Free Roam.

Task IDs are stable — reference them in commits and in `PROGRESS.md`.

---

## Review protocol

**Every task ends in something a human can look at, and this plan says what.**

Every **reviewable unit** from Phase 2 onward carries a `Review:` line with three fields:

```
Review: <what to look at> | <the command that produces it> | <the verdict question>
```

The unit is the **task** in Phase 2 and the **build** in Phase 3, where the individual systems are
not separately playable. Whichever it is, the line is part of the definition of done.

Two kinds of check, and the difference matters:

| Kind | Who says yes | Example |
|---|---|---|
| **Machine-checked** | `tools/check.sh`, `verify_*.gd`, `pytest` | every tile's mesh agrees with the `aabb` the manifest declares |
| **Human-judged** | the user, driving or looking | `Q12` — Jaffe Road is eastbound; `Q8` — the city itself is the fun |

**The rule: no more than one reviewable unit may pass without a human-judged artifact.** A
machine-checked unit may follow a human-judged one; two in a row may not.

**Review points are hard gates.** Work stops until the user has driven the build and the verdict is
recorded in `PROGRESS.md`. This is deliberate and it costs turnaround time.

**Name the verdict question in advance.** This is the field that does the work. `Q8`'s drive test
asked "is this fun?", nobody had written down "is the car facing the legal direction?", and so a
spawn with a transposed basis survived a full user drive-through — the user caught it later, from
the driver's seat, when the harbour turned out to be on the wrong side. A review with no stated
question only finds what someone happens to notice.

**The default route is the web build**, exported and served per
`.claude/skills/run-hk-taxi-q/SKILL.md`. Driver screenshots are the *progress* report; a build the
user can drive is the *verdict* route. Two exceptions, named in the tasks that use them: a debug
overlay is reviewed under the driver, and anything about feel-in-the-hand needs the handset.

> **Precedent.** Phase 1 already worked this way without being told to — every ETL stage grew a
> preview (`road_preview`, `fare_preview`, `road_surface_preview`, `tile_preview`, `city_drive`),
> and the two verdicts that closed `Q12` and `Q8` came from the user's eye rather than from any
> test. This section writes down a habit that was already earning its keep. Phase 1 is complete and
> Phase 0 is complete but for `P0-3b`, which the protocol picks up at review point 2; both phases
> are otherwise left as the record.

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
- **Scheduled at Phase 2's review point 2**, beside `P2-5`.

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

**Three review points**, marked below. Each is a hard gate.

### `P2-1` `CityStreamer`
- **Deliverable:** tile load/unload by camera distance and LOD tier switching, per the data contract
  in `ARCHITECTURE.md`. Distance bands and hysteresis margin are tuning data (`.tres`), not
  constants. Decides where tile colliders come from.
- **Accept:** no hitching on tile boundaries; draw calls within budget; a distant tile is rejected
  by its `aabb` **before** its mesh is loaded.
- **Review:** the streamed city driven from HKCEC, plus a matched pair of shots showing LOD0 and
  LOD1 at closest range in a street canyon | web build | **Does LOD popping read as acceptable, and
  is LOD1 good enough at closest range?**
- **Deps:** `P1-7`.
- **Note:** the second half of that verdict is `Q16`'s answer — yes closes it, no sends it to LOD0
  simplification. Take the before/after from a fresh PCK; every bundle figure written down so far
  has drifted, which is what `Q16` says about summing instead of measuring.

### `P2-2` `RoadGraph` runtime **and debug overlay**
- **Deliverable:** load `roadgraph.json` once, own nearest-edge and lane-centre queries, and retire
  the duplicate parse `road_preview.gd` and `fare_preview.gd` do in the same scene. **Plus a debug
  overlay** drawing the resolved edge, the lane centre and the legal travel direction under the
  moving car.
- **Accept:** query correctness unit-tested; sub-millisecond nearest-edge; exactly one parse of the
  graph in the running game; **nearest-edge never returns an off-grade edge** — 60 of the region's
  797 edges, per `Q13`'s decision — and a test proves it at the 36 mixed-level nodes.
- **Review:** the overlay while driving — the named exception to the web-build route, because the
  overlay wants frame-by-frame inspection | driver run | **Does the graph agree with where the car
  actually is** — at the centreline seam, and at the nodes `Q13` names?
- **Deps:** `P1-3`.
- **Why the overlay is a deliverable, not a nicety:** without it this task is a parse and two query
  functions, with nothing whatsoever to look at — the only task in the project in that position. It
  is also the task that will hand the car onto an unreachable flyover if `Q13` is not settled first.

> ⚠️ **Review point 1 — the city streams and the graph is trustworthy.** `Q13` was decided ahead of
> this task on 2026-07-31: **nearest-edge refuses off-grade edges**, and the elevated network is out
> of the slice. A spike measured the alternative first — the map sheets do carry the ramps — but the
> residual step is topological, so no height source repairs it. See the decision log.

### `P2-3` `VehicleController` on real geometry
- **Deliverable:** the custom raycast vehicle on `RigidBody3D`, arcade tuning in `handling.tres`,
  now placed by `P2-2`'s lane-centre query rather than by a hand-written transform.
- **Accept:** matches the feel agreed in `P0-5`; spawn orientation asserted against its edge vector.
- **Review:** a drive along Hennessy Road | web build | **Is this still the `P0-5` car?**
- **Deps:** `P0-5`, `P1-7`, `P2-2`.

### `P2-4` `InputRouter`
- **Deliverable:** touch, gamepad and keyboard → one action set.
- **Accept:** all three input paths drive the car; no gameplay script reads raw input.
- **Review:** all three input paths exercised | on-device build at `P0-3b` | **Machine-checked** for
  coverage; the user says whether touch steering is usable at all.
- **Deps:** `P2-3`.

### `P2-5` Chase camera
- **Deliverable:** speed-based FOV and look-back, on real geometry.
- **Accept:** readable at speed; no clipping through buildings.
- **Review:** a drive through the junction east of HKCEC and a drift | web build |
  **Can you read the road at speed, and does the camera stay out of the buildings?**
- **Deps:** `P2-3`, **and building collision** — which no task owned. `P2-1` was asked to decide
  where tile colliders come from, decided they were an ETL product, and closed; the second half
  never got scheduled. The acceptance criterion here is what surfaced it, because a spring arm
  cannot stay out of buildings that are not there. Shipped 2026-08-01 as a `-col` mesh name on the
  finest tier, `schema_version` 3. See `docs/PROGRESS.md`.
- **Note:** a declared dependency graph does not catch this class of gap — `P2-5` depends on a
  *capability*, not on a task, and the capability's owner had already closed. Worth a glance at the
  other acceptance criteria for the same shape.

> ⚠️ **Review point 2 — the car drives the real city.** The first build worth putting in a hand, so
> `P0-3b` runs here: how the car feels under a thumb is reachable no other way.

### `P2-7` Put the off-grade carriageway on the structure it belongs to

> **Numbered after `P2-6` and sequenced before it**, which is the one place in this plan where ID
> order and running order disagree. `P2-6` is the phase gate and it measures frame time on the
> geometry that ships, so it has to run last; this task changes that geometry. The ID is late
> because the task was found late — task IDs are stable and `P2-6` is already referenced from
> `P0-3b`, so renumbering would cost more than this note.

- **Deliverable:** deck heights **sampled from the `INFRASTRUCTURE` geometry** instead of the flat
  `elevation_levels` offset, so a flyover ribbon lies on the flyover and a ramp edge climbs with the
  ramp. The elevated network stays **closed to driving** — `nearest_edge` keeps refusing off-grade
  edges, exactly as `P2-2` accepted.
- **Accept:** ribbon-to-structure vertical error inside ±0.5 m at the 90th percentile, against
  today's ±4.06/+2.45 m; no ribbon left *below* the deck it should sit on; `schema_version` bumped
  and `ARCHITECTURE.md` changed in the same commit. **Plus the classification below**, because a
  sampled height is only meaningful where the node is real.
- **Review:** the Tonnochy Road approach and the Wan Chai Interchange, before and after |
  web build | **Does the elevated road now sit where the structure says it does?**
- **Deps:** `P1-2`, `P1-4`. Independent of `P2-4`/`P2-5`.
- **Why here and not in Phase 4:** this is a **data-contract** change, and Phase 3 builds on the
  contract — `P3-3`'s traffic drives the graph and `P3-1`'s fares snap to it. Changing deck heights
  after traffic exists means redoing traffic. It is also the fix for the only defect the `P2-5`
  drive reported, and it costs nothing in scope because nothing becomes drivable.
- ⚠️ **First, classify the 36 mixed-level nodes**, and treat the answer as the task's real finding.
  `Q13` recorded the elevated network as *topologically connected*, which means the 36 nodes are
  either genuine ramp junctions — in which case sampling makes them continuous and `Q13` largely
  dissolves — or plan-coincident crossings where a flyover passes over a street and the source
  joined them because they share a plan position, in which case sampling cannot help and the
  connection is spurious data that `RoadGraph` should refuse on its own terms. The `WAN CHAI
  INTERCHANGE` edges look like the first kind: edge 318 climbs 3.70 m over 39.5 m, which is a ramp
  gradient. Do not assume it generalises to all 36.

### `P2-6` Performance pass to budget
- **Deliverable:** measured and recorded, on the device floor.
- **Accept:** 60fps on the device floor, measured, recorded in `PROGRESS.md`.
- **Review:** the same drive on the handset | on-device build | **Does it feel smooth?** The frame
  numbers are the acceptance criterion above; a held 60 that still stutters under a thumb is a
  finding no counter reports.
- **Deps:** `P2-1`…`P2-5`, `P0-3b`.

> ⚠️ **Review point 3 — and the Phase 2 gate:** 60fps on the device floor while driving real Wan
> Chai geometry.

---

## Phase 3 — Playable slice

**Goal:** a complete arcade loop that passes the authenticity test.

**Four playable builds, then the test.** All nine original tasks are here and their IDs are
preserved, with `P3-1`, `P3-2` and `P3-5` each split into an `a`/`b` pair. The reorder changes
**when** they land, not what they are, so that the user plays something after each build rather than
after all of it. Builds run in order, `B1` → `B4`.

Why reordered, in one line each:

- **The thin loop comes first** because "is completing a fare worth doing twice?" is cheap to
  answer and expensive to get wrong, and the other eight tasks currently stand between it and being asked.
- **Art comes second, not sixth.** `P3-9` asks HK drivers to navigate *with the arrow disabled* —
  that is a test of **recognition**, which `P3-6` and `P3-7` deliver and `P3-2b` does not touch at
  all. It is also the project's central bet (`Q8`), so it wants the most iteration time.
- **Scoring comes last** because it answers "does novelty survive the first session," the live
  entry in the risk register, and that question wants every other system in place before it is put.
  **One exception, added 2026-08-01:** near-miss scoring moves up to `B3` as `P3-2a`, because it is
  what makes that build's review question answerable at all. See `B3`.

### Build `B1` — "One fare"

| ID | Deliverable | Accept |
|---|---|---|
| `P3-1a` | `FareSystem` — hail → carry → deliver/fail state machine. **Standard and short hop only** | The loop runs end to end and can be failed |
| `P3-5a` | Minimal HUD — destination arrow, timer, meter. Deliberately ugly | Legible; no layout work |

- **Deps:** `P1-5`, `P2-2`.
- **Review:** play one fare, start to finish | web build | **Is completing a fare worth
  doing twice?**
- **Note:** cross-harbour and long-haul are held back to `B4` on purpose — they are the interesting
  fares, and they are worth tuning once the plain one is known to work.

### Build `B2` — "It reads as Hong Kong"

| ID | Deliverable | Accept |
|---|---|---|
| `P3-10` | **Ground surface** — decimated terrain, vertex-coloured, merged into the tile primitive | Ground everywhere the region has terrain; **no texture ships**; one draw call per tile still; no z-fighting against the carriageway |
| `P3-7` | Window-band shader, **and the `TEXCOORD_0` payload it reads** | Reads as HK density; no windows on roofs or podium faces. ETL ships height-above-own-base and a per-building seed in `TEXCOORD_0`; `schema_version` bumped in the same commit |
| `P3-6` | Hero buildings (5) authored, placed via `landmarks.json` | Source geometry excluded; no z-fighting |

- **Deps:** `P1-2`, `P1-7`, `B1`. Within the build, `P3-10` comes first — the other two are judged
  against a city that has a floor.
- **Review:** drive Hennessy Road and look around; the same viewpoints before and after |
  web build | **Does this read as Wan Chai?** Dress rehearsal for `P3-9`, with the
  project's central bet on the table.
- **`P3-10` runs in two halves, and may stop after the first.** Flat-coloured decimated terrain
  ships first, because it is small and it produces the screenshot that answers `Q18` — *does flat
  ground read as ground?* Only if it reads dead does the second half follow: sample the source
  aerial JPEG per triangle, classify to a land-cover palette, and put the class in `mesh.collapse`'s
  cluster key so boundaries stay crisp. That half adds **Pillow** to the ETL and is not written
  until the first half has been looked at. See `docs/PROGRESS.md`.
- ⚠️ **`P3-7` is one commit across two sides.** The shader cannot derive height-above-own-base or a
  per-building seed from a vertex, so the ETL must ship them; buildings carry no UVs today, and
  `TEXCOORD_0` is where they go. Hard rule 5 — ETL output and game input change together.

### Build `B3` — "The streets are alive"

| ID | Deliverable | Accept |
|---|---|---|
| `P3-3` | `TrafficSystem` — AI on road-graph splines obeying direction and turn restrictions | Traffic obeys real rules; density scales by perf tier |
| `P3-4` | Trams on Hennessy/Johnston as scripted moving blockers | Unpassable, correctly routed, tram bell audio |
| `P3-8` | Bus-lane penalty + red taxi livery + minibus behaviour | Penalty triggers from the `bus_lane` flag |
| `P3-2a` | **Near-miss scoring only** — detection plus a live on-screen award. Split out of `P3-2` | Passing AI traffic inside the threshold at speed awards points, shown during the drive. No style chain, no banking |

- **Deps:** `P2-2`, `B2`. Within the build, `P3-4` and `P3-8` follow `P3-3`, and `P3-2a` follows all
  three — it has nothing to detect until there is traffic to pass.
- **Review:** drive the `B1` fare again, now with traffic | web build | **Harder in a
  good way, or just annoying?**
- ⚠️ **`P3-2a` is here because the review question is otherwise rigged against the build.** Dense
  traffic is what converts an obstacle into an opportunity *only if threading it pays*; with scoring
  wholly in `B4`, this review would judge traffic in the one state where traffic has no upside, and
  a "just annoying" verdict would be an artifact of the ordering rather than a finding about the
  traffic. Near-miss detection alone is a small slice — a threshold, a speed gate and a HUD pop —
  and the rest — `P3-2b` — stays in `B4` where it belongs.
- **Prior art: Burnout 3.** Near-miss, oncoming-lane driving and a boost meter fed by risk are the
  fullest working-out of *traffic as the reward rather than the obstacle*, and the threshold, the
  speed gate and the pop are all tuned quantities there rather than obvious ones. Worth studying
  before tuning ours.

### Build `B4` — "It's a game"

| ID | Deliverable | Accept |
|---|---|---|
| `P3-2b` | `ScoreSystem` — base, time bonus, drift/air/speed, **the style chain and its banking**, and the fare combo. Absorbs `P3-2a`'s near miss | Style points award live during driving, and the style chain is **losable** — a hard crash costs it unbanked |
| `P3-1b` | Remaining fare types — **cross-harbour** and long haul | Cross-harbour fare works |
| `P3-5b` | Full HUD — bilingual destination callouts, safe areas, one-handed layout | Readable one-handed in daylight |

- **Deps:** `B1`, `B3`.
- **Review:** play a full session, twice | web build | **Do you want another
  go?** This is the risk register's "novelty does not survive the first session", put directly.

### `P3-9` Authenticity test round 1
- **Deliverable:** the test run with HK drivers who have not seen the game before.
- **Accept:** ≥3 HK drivers navigate Convention Centre → Times Square with the arrow disabled.
- **Review:** the drivers themselves | a build on a handset | **Human-judged, by people who are not
  the user.** The only test in this plan whose verdict the team cannot give itself.
- **Deps:** `B1`…`B4`.

> **Phase 3 gate — go/no-go on full production.**
> Required: `P3-9` passes; 60fps held on the device floor; the user judges the game fun.

---

## After the slice

### Phase 4 — The elevated network

**Goal:** the 23.3% of carriageway that `Q13` excluded becomes drivable network rather than scenery.

**Broken down, where the other post-slice phases are not.** Two reasons. It is the only one whose
assumptions the slice will *not* change — the data is measured and the defects are named in `Q13`,
`Q15`, `Q19` and `Q20`. And it stopped being hypothetical on 2026-08-01: shipping tile collision
made the physical ramps climbable, so the network is already half-open by accident, and a plan is
cheaper than discovering the rest of it from a bug report.

**`P2-7` is the prerequisite and does the geometry.** Everything here is about *driving*.

| ID | Deliverable | Accept |
|---|---|---|
| `P4-1` | `RoadGraph` serves off-grade edges — nearest-edge, lane centres and travel direction across all three levels | The `P2-2` criterion "nearest-edge never returns an off-grade edge" is **deliberately reversed**, its test rewritten to assert the new rule, and the reversal recorded against `Q13` |
| `P4-2` | Level-aware nearest-edge — a query resolves by 3D proximity, not plan distance | A stand under a flyover resolves to the street, not the deck above it. **Closes `Q15`** |
| `P4-3` | Ramp traversal — the car drives grade → deck → grade without leaving the surface | No step over 0.15 m at any of the 36 nodes, measured; the kerb height is the tolerance because it is what the suspension already survives |
| `P4-4` | Traffic across levels — extends `P3-3` onto the elevated network | AI obeys direction and turn restrictions on ramps; density scales by tier |
| `P4-5` | Perf pass — 23.3% more drivable area, and the streamer's bands were tuned without it | 60fps on the device floor with the elevated network resident |

- **Deps:** `P2-7`, `P3-3`. `P4-3` follows `P4-1`.
- **Review:** drive the Wan Chai Interchange from Gloucester Road onto the deck and back down |
  web build | **Can you get up there, and does it feel like a road rather than a ramp-shaped bug?**
- **Note:** `P4-1` reverses an acceptance criterion this project measured and proved over 505
  probes. That is not a mistake being corrected — `Q13`'s refusal was the right call for a slice
  with no ramps. Record it as a scope change, not a bug fix, or the history stops making sense.

### Outline only — refine once Phase 3 lands

- **Phase 5 — Content:** Causeway Bay, then Central. Full vehicle roster, audio pass, night mode.
- **Phase 6 — Production polish:** menus, settings, save/progression, accessibility, localisation QA.
- **Phase 7 — Ship:** free-slice boundary implemented, one-time unlock IAP, store assets, web demo
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
- **Producing the review artifact is the agent's job; answering the verdict question is not.** See
  the review protocol above for the format and the gate.
- **Stop at every review point and wait.** "Machine-checked" is never a substitute — the verify
  tools shipped broken-and-green inside a single commit once already.
- **Look at the screenshots before saying a build is ready to review**, per the `DRIVER OK` caveat
  in `.claude/skills/run-hk-taxi-q/SKILL.md`. A green driver run is not a rendered game.
