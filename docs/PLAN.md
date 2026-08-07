# Plan — Vertical Slice

**Scope:** prove three things before committing to full production.

1. The ETL pipeline works on real HK open data.
2. The driving is fun.
3. The city reads as Hong Kong to Hong Kong drivers.

**Out of scope for the slice:** monetisation, store assets, art polish, audio beyond placeholders,
Causeway Bay and Central, all modes except Arcade and Free Roam.

Task IDs are stable — reference them in commits and in `PROGRESS.md`. Live status lives in
`PROGRESS.md`'s task board, not here.

---

## Review protocol

**Every task ends in something a human can look at, and this plan says what.** Every reviewable unit
from Phase 2 onward carries:

```
Review: <what to look at> | <the command that produces it> | <the verdict question>
```

The unit is the **task** in Phase 2 and the **build** in Phase 3, where the individual systems are
not separately playable. Whichever it is, the line is part of the definition of done.

| Kind | Who says yes | Example |
|---|---|---|
| **Machine-checked** | `tools/check.sh`, `verify_*.gd`, `pytest` | every tile's mesh agrees with the `aabb` the manifest declares |
| **Human-judged** | the user, driving or looking | `Q12` — Jaffe Road is eastbound; `Q8` — the city itself is the fun |

**The rule: no more than one reviewable unit may pass without a human-judged artifact.** A
machine-checked unit may follow a human-judged one; two in a row may not.

**Review points are hard gates.** Work stops until the user has driven the build and the verdict is
recorded — the status in `PROGRESS.md`, and what the verdict decided in `DECISIONS.md`.

**Name the verdict question in advance.** This is the field that does the work. `Q8`'s drive test
asked "is this fun?", nobody had written down "is the car facing the legal direction?", and so a
spawn with a transposed basis survived a full user drive-through — the user caught it later, from the
driver's seat, when the harbour turned out to be on the wrong side. **A review with no stated
question only finds what someone happens to notice.**

**The default route is the web build**, exported and served per `.claude/skills/run-hk-taxi-q/`.
Driver screenshots are the *progress* report; a build the user can drive is the *verdict* route. Two
exceptions, named in the tasks that use them: a debug overlay is reviewed under the driver, and
anything about feel-in-the-hand needs the handset.

> **Precedent.** Phase 1 worked this way without being told to — every ETL stage grew a preview, and
> the two verdicts that closed `Q12` and `Q8` came from the user's eye rather than from any test.

---

## Phase 0 — Spikes and scaffolding ✅

**Goal:** kill the unknowns that could invalidate the whole plan. Complete but for `P0-3b`, and left
here as the record.

| ID | Deliverable | Outcome |
|---|---|---|
| `P0-1` | LandsD sheet numbers covering the region; confirmation of glTF delivery granularity | ✅ 6 sheets, per sheet, ~44 MB. Building data turned out **fully scriptable** — the top data risk, retired |
| `P0-2` | ⚠️ Whether Road Network v2 centrelines carry a Z ordinate, with evidence | ✅ No Z, but `ELEVATION` encodes the level. **Region holds** — no fallback to Tsim Sha Tsui |
| `P0-3` | `game/` opens in Godot 4.7, Mobile renderer, export presets committed, a scene at 60fps | ✅ Imports clean; macOS, web and Android export verified |
| `P0-4` | `etl/` package, `hong_kong.yaml`, `crs.py`, `ruff` + `pytest` | ✅ Round-trip transform tests against published HK1980 reference points |
| `P0-5` | A hand-built grey-box "Gloucester Road" plus a tuned custom raycast vehicle | ⚠️ Passed conditionally — handling accepted, **fun not assessable from a grey box** (`Q8`) |

### `P0-3b` Mobile device build verification ⬜

- **Deliverable:** a signed development build installed and running on the device floor, on both an
  iOS and an Android handset. Real reverse-domain bundle identifier replacing the placeholder in
  `export_presets.cfg`.
- **Accept:** the current scene runs on-device with the FPS counter visible; measured FPS recorded.
- **Deps:** `P0-3`, plus physical hardware. `Q4` is confirmed (A13 / Adreno 618).
- **Note:** not on the critical path, but it **blocks `P2-4`'s and `P2-6`'s reviews** — how the car
  feels under a thumb is reachable no other way. Scheduled at Phase 2's review point 2.

---

## Phase 1 — ETL vertical slice ✅

**Goal:** real Wan Chai data → game-ready assets, reproducibly, with one command. **Gate passed** —
Wan Chai renders in Godot from `city.json`, georeferenced and verified in-engine.

| ID | Deliverable | Outcome |
|---|---|---|
| `P1-1` | `fetch.py` — download and cache the region's building, road and fare datasets | ✅ Sheets derived from the published index, not listed. Re-running is a no-op |
| `P1-2` | `buildings.py` — parse glTF, clip, colour by height band and class, merge per tile, emit LOD tiers | ✅ 65 tiles; one draw call each, vertex colours live, no textures |
| `P1-3` | `roads.py` — parse Road Network v2 → `roadgraph.json` per the data contract | ✅ 797 edges, 615 nodes, 217 turn restrictions, 96.3% connected. One-way directions confirmed against the real street (`Q12`) |
| `P1-4` | Ribbon mesh with widening, kerbs and collision | ✅ One mesh, one draw call. All 393 single-level junctions covered. Opened `Q13` |
| `P1-5` | `fares.py` — stands + PUDO → `fares.json`, snapped, bilingual | ✅ 29 nodes; every `nearest_edge` resolves, corroborated independently by the source's own prose |
| `P1-6` | `export.py` — `city.json` plus one command for the whole pipeline | ✅ Byte-reproducible. The stage also **validates** what no single stage can see |
| `P1-7` | Godot loads `city.json` and instantiates tiles at correct world positions | ✅ **Gate passed.** 1 cm agreement, checked headlessly. The `DirAccess` tile listing deleted — it could never have worked in an export |

---

## Phase 2 — Driving the real city

**Goal:** the player drives real Wan Chai at 60fps on the device floor. **Three review points**, each
a hard gate.

### `P2-1` `CityStreamer` ✅ — review passed

- **Deliverable:** tile load/unload by camera distance and LOD tier switching. Distance bands and
  hysteresis are tuning data (`.tres`), not constants. Decides where tile colliders come from.
- **Accept:** no hitching on tile boundaries; draw calls within budget; a distant tile is rejected by
  its `aabb` **before** its mesh is loaded.
- **Review:** the streamed city driven from HKCEC, plus a matched pair showing both tiers at closest
  range in a street canyon | web build | **Does LOD popping read as acceptable, and is the coarse
  tier good enough at closest range?**
- **Outcome:** yes to both, which closed `Q16` — the exact-weld tier does not ship. PCK 51.6 →
  21.1 MB, worst-case visible triangles 249,210 → 150,374.

### `P2-2` `RoadGraph` runtime **and debug overlay** ✅ — review passed

- **Deliverable:** load `roadgraph.json` once, own nearest-edge and lane-centre queries, and retire
  the duplicate parse the previews were doing. **Plus a debug overlay** drawing the resolved edge, the
  lane centre and the legal travel direction under the moving car.
- **Accept:** query correctness tested; sub-millisecond nearest-edge; exactly one parse per scene;
  **nearest-edge never returns an off-grade edge** — 60 of 797, per `Q13` — proven at the 36
  mixed-level nodes.
- **Review:** the overlay while driving — the named exception to the web-build route, because it
  wants frame-by-frame inspection | driver run | **Does the graph agree with where the car actually
  is**, at the centreline seam and at the nodes `Q13` names?
- **Why the overlay was a deliverable, not a nicety:** without it this task is a parse and two query
  functions, with nothing whatsoever to look at — the only task in the project in that position. It
  is also what found the carriageway-width contract gap.

### `P2-3` `VehicleController` on real geometry ✅ — review passed

- **Deliverable:** the custom raycast vehicle, arcade tuning in `handling.tres`, now placed by
  `P2-2`'s lane-centre query rather than by a hand-written transform.
- **Accept:** matches the feel agreed in `P0-5`; spawn orientation asserted against its edge vector.
- **Review:** a drive along Hennessy Road | web build | **Is this still the `P0-5` car?**
- **Outcome:** *"car seems ok"* — a pass on the question asked, read no wider than it was said.

### `P2-5` Chase camera ✅ — review passed

- **Deliverable:** speed-based FOV and look-back, on real geometry.
- **Accept:** readable at speed; no clipping through buildings.
- **Review:** a drive through the junction east of HKCEC and a drift | web build | **Can you read the
  road at speed, and does the camera stay out of the buildings?**
- ⚠️ **Was blocked on building collision, which no task owned.** `P2-1` was asked to decide where
  tile colliders come from, decided correctly that they are an ETL product, and closed; the second
  half never got scheduled. A spring arm cannot stay out of buildings that are not there. **A
  declared dependency graph does not catch this class of gap** — `P2-5` depends on a *capability*,
  not on a task, and the capability's owner had already closed. Worth a glance at the other
  acceptance criteria for the same shape.

> ⚠️ **Review points 1 and 2 are passed.** `Q13` was decided ahead of `P2-2`: nearest-edge refuses
> off-grade edges, and the elevated network is out of the slice.

### `P2-7` Put the off-grade carriageway on the structure it belongs to ✅ — review passed

> **Numbered after `P2-6` and sequenced before it** — the one place where ID order and running order
> disagree. `P2-6` is the phase gate and measures frame time on the geometry that ships, so it has to
> run last; this task changes that geometry. The ID is late because the task was found late.

- **Deliverable:** deck heights **sampled from the `INFRASTRUCTURE` geometry** instead of the flat
  `elevation_levels` offset, so a flyover ribbon lies on the flyover and a ramp edge climbs with the
  ramp. The elevated network stays **closed to driving**.
- **Accept:** ribbon-to-structure vertical error inside ±0.5 m at p90, measured against the **shipped
  tiles**; no ribbon left below the deck it should sit on; `schema_version` bumped and
  `ARCHITECTURE.md` changed in the same commit. **Plus the classification below.**
- **Review:** the Tonnochy Road approach and the Wan Chai Interchange, before and after | web build |
  **Does the elevated road now sit where the structure says it does?**
- **Deps:** `P1-2`, `P1-4`.
- **Why here and not in Phase 4:** this is a **data-contract** change, and Phase 3 builds on the
  contract — `P3-3`'s traffic drives the graph and `P3-1`'s fares snap to it. Changing deck heights
  after traffic exists means redoing traffic.
- ⚠️ **First, classify the 36 mixed-level nodes, and treat the answer as the task's real finding.**
  Either they are genuine ramp junctions — in which case sampling makes them continuous — or
  plan-coincident crossings, in which case sampling cannot help and the connection is spurious data
  `RoadGraph` should refuse on its own terms.
- **Outcome:** \|error\| p90 **0.095 m** against 0.50, graded against the shipped tiles; the
  classification found **all 36 are ramps and none is a crossing**. Three review findings were fixed
  across as many drives — coincident surfaces, widening on structure, and widening past the point
  where a road becomes a bridge (`Q23`) — **each found by a drive and by no internal number.**

### `P2-4` `InputRouter` ⬜

- **Deliverable:** touch, gamepad and keyboard → one action set.
- **Accept:** all three input paths drive the car; no gameplay script reads raw input.
- **Review:** all three paths exercised | on-device build at `P0-3b` | **Machine-checked** for
  coverage; the user says whether touch steering is usable at all.
- **Deps:** `P2-3`, and `P0-3b` for the review.

### `P2-6` Performance pass to budget ⬜

- **Deliverable:** measured and recorded, on the device floor.
- **Accept:** 60fps on the device floor, measured, recorded in `PROGRESS.md`.
- **Review:** the same drive on the handset | on-device build | **Does it feel smooth?** The frame
  numbers are the acceptance criterion above; a held 60 that still stutters under a thumb is a
  finding no counter reports.
- **Deps:** `P2-1`…`P2-5`, `P2-7`, `P0-3b`.
- **Inherits:** re-measuring tile hitching now that instantiation also registers a trimesh with Jolt
  on the main thread, and re-examining "vehicle blob shadow only" — shots with shadows off looked
  markedly worse than that line implies.

> ⚠️ **Review point 3 — and the Phase 2 gate:** 60fps on the device floor while driving real Wan Chai.

---

## Phase 3 — Playable slice

**Goal:** a Wan Chai that reads as Hong Kong to strangers, then a complete arcade loop around it.

**Four playable builds, then the test.** Every task keeps its ID: `P3-1`, `P3-2` and `P3-5` remain
split into `a`/`b` pairs, `P3-9` gains an earlier `P3-9a` round in front of it, and `P3-11` is added
for the player taxi. Builds run **`B2` → `B1` → `B3` → `B4`**.

⚠️ **The build letters name content, not running order** — the convention `P2-7` already set, for the
same reason. Renumbering would silently falsify a dozen records in `DECISIONS.md` that say things like
"`P3-10`, build `B2`". Where letter order and running order disagree, this plan says which is which.
`B2` runs first.

Why the city comes before the loop — **user's call**:

- **The scene is the bet, so the scene gets tested first.** `Q8` closed on "the city itself is the
  fun", and the user's own word for it was *gimmick*. Fares, traffic and scoring are all built on the
  assumption that driving this city is worth doing, and that assumption currently rests on one
  person's drive. `B2` puts it in front of strangers while it is still cheap to change what the city
  is made of.
- **`B2` is a purer recognition test than `P3-9`.** `P3-9` asks HK drivers to navigate *with the
  arrow disabled*; `B2` has no arrow to disable, because it has no HUD, because it has no fare
  system. The thing `P3-9` must artificially suppress does not exist yet. That is an argument for
  testing recognition now rather than later, and it is why `P3-9a` exists.
- **The taxi is in every screenshot, and no task owned it.** `ART_DESIGN.md` specifies the roster and
  an 800–2,000 triangle budget, but no Phase 3 task delivered even the player's own car — so the
  thing the player looks at for hours is still two `BoxMesh` primitives. **Same shape as `P2-5`'s
  missing building collision:** a capability the docs assumed and no task owned. Now `P3-11`.
- **Scoring still comes last**, and `P3-2a` still moves up to `B3`, both for the reasons recorded
  below. This reorder moves `B2` ahead of `B1`; it does not disturb `B3` or `B4`.

⚠️ **What the reorder costs, recorded so it is not rediscovered as a surprise.** `B1` was scheduled
first because *"is completing a fare worth doing twice?"* is cheap to answer and expensive to get
wrong. It is now answered later, on a city already built. If the fare loop turns out to want
something different of the world — other fare-node density, other block sizes, ground the player
stops on — `B2`'s art is already spent. The user judged the scene the larger risk; that is the
trade.

### Build `B2` — "It reads as Hong Kong" — **runs first**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-11` | **Player taxi model** — low-poly toy taxi, generated by a committed script rather than hand-modelled | 800–2,000 triangles; 1–2 flat-shaded materials; 3–5 colours; red body, silver roof; silhouette readable from behind at speed |
| `P3-10` | **Ground surface** — decimated terrain, vertex-coloured, merged into the tile primitive | Ground everywhere the region has terrain; **no texture ships**; one draw call per tile still; no z-fighting against the carriageway |
| `P3-7` | Window-band shader, **and the `TEXCOORD_0` payload it reads** | Reads as HK density; no windows on roofs or podium faces. ETL ships height-above-own-base and a per-building seed; `schema_version` bumped in the same commit |
| `P3-6` | Hero buildings (5) authored, placed via `landmarks.json` | Source geometry excluded; no z-fighting |

- **Deps:** `P1-2`, `P1-7`. **No longer depends on `B1`** — that dependency was ordering, not
  substance. Nothing in the taxi, the ground, the shader or the hero buildings reads a fare.
- **Within the build:** `P3-11` first, because it appears in every screenshot of every later review —
  a shot taken before it is a shot that has to be retaken. Then `P3-10`, because the remaining two
  are judged against a city that has a floor. Then `P3-7`, then `P3-6`.
- **Review:** drive Hennessy Road and look around; the same viewpoints before and after | web build |
  **Does this read as Wan Chai?** No longer a dress rehearsal — `P3-9a` follows immediately and puts
  the same build in front of people who are not the user.
- **`P3-10` runs in two halves and may stop after the first.** Flat-coloured decimated terrain ships
  first, because it produces the screenshot that answers `Q18` — *does flat ground read as ground?*
  Only if it reads dead does the second half follow: sample the source aerial JPEG per triangle,
  classify to a land-cover palette, and put the class in `mesh.collapse`'s cluster key so boundaries
  stay crisp. That half adds **Pillow** and is not written until the first has been looked at.
- ⚠️ **`P3-7` is one commit across two sides.** The shader cannot derive height-above-own-base or a
  per-building seed from a vertex, so the ETL must ship them. Hard rule 5.

#### `P3-11` — how the taxi gets built

- **Deliverable:** `tools/make_vehicle.py` emits `game/assets/authored/vehicles/taxi.glb` from named
  proportions — wheelbase, track, greenhouse height, arch flare, roof taper, colour list. The `.glb`
  is **committed**: it is a hand-authored asset under CC BY-SA 4.0, not build output, so it does not
  go to `assets/generated/` and is not gitignored. See `LICENSING.md`.
- **Why generated and not modelled:** the Choro-Q look is a proportion problem, not a detail problem.
  `ART_DESIGN.md` asks for "shortened wheelbase, tall greenhouse, exaggerated wheel arches" — three
  numbers. Scripting them makes the toy look **tunable in a diff** rather than guessed in a mesh, and
  the same tool goes on to make the rest of `ART_DESIGN.md`'s roster, which `B3` needs. Hard rule 4
  in spirit: the proportions are data.
- ⚠️ **Accept, additionally: the wheel raycasts must still land where the arches are.** `P0-5` tuned
  handling against the mount points in `taxi.tscn`, and `P0-5a` chose a custom raycast controller
  precisely so those points are authored rather than inferred. Moving the visual car without moving
  the raycasts is how a tuned vehicle silently stops matching its own tuning — and the drive would
  still look fine, because the mesh is not what the physics reads.
- **Review:** the taxi from behind at speed, and parked beside a building for scale | web build |
  **Does it read as a toy in an accurate city, rather than as a box?**

### `P3-9a` Recognition round 0 — the city, before the game

- **Deliverable:** the `B2` build put in front of HK drivers who have not seen it, as free roam —
  no HUD, no objective, nothing to do but drive.
- **Accept:** ≥3 HK drivers, none of them the user, each asked to get from the Convention Centre to
  Times Square **unaided** — there is no arrow to disable — and to say aloud what they recognise on
  the way.
- **Review:** the drivers themselves | web build link | **Do they know where they are?**
- **Deps:** `B2`.
- **Why a web link and not a handset:** it costs the tester one click and the project nothing, which
  is the only reason this round can happen early — `P0-3b` stays off the critical path. The trade is
  real and belongs in the write-up: this is a desk test on a keyboard, and it says nothing about how
  the car feels under a thumb. `P3-9` remains the handset test.
- ⚠️ **Two verdict questions, and the second is the one that matters.** Recognition is the stated
  bet, but *"did they keep driving when there was nothing to do?"* is the risk register's **"novelty
  does not survive the first session"** asked at the earliest possible moment and in its harshest
  form — a city with no fares, no traffic and no score. A no there is not a failure of `B2`; it is
  `B1` and `B3` turning out to be more urgent than the schedule assumed. **Record it either way**,
  including how long each driver lasted before stopping.

### Build `B1` — "One fare" — **runs second**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-1a` | `FareSystem` — hail → carry → deliver/fail state machine. **Standard and short hop only** | The loop runs end to end and can be failed |
| `P3-5a` | Minimal HUD — destination arrow, timer, meter. Deliberately ugly | Legible; no layout work |

- **Deps:** `P1-5`, `P2-2`, and now `B2` — added by the reorder, not by substance: the fare loop
  needs no art, but its review should be played on the city that ships.
- **Review:** play one fare, start to finish | web build | **Is completing a fare worth doing twice?**
- Cross-harbour and long-haul are held back to `B4` on purpose — they are the interesting fares, and
  they are worth tuning once the plain one is known to work.

### Build `B3` — "The streets are alive" — **runs third**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-3` | `TrafficSystem` — AI on road-graph splines obeying direction and turn restrictions | Traffic obeys real rules; density scales by perf tier |
| `P3-4` | Trams on Hennessy/Johnston as scripted moving blockers | Unpassable, correctly routed, tram bell audio |
| `P3-8` | Bus-lane penalty + red taxi livery + minibus behaviour | Penalty triggers from the `bus_lane` flag |
| `P3-2a` | **Near-miss scoring only** — detection plus a live on-screen award | Passing AI traffic inside the threshold at speed awards points, shown during the drive. No style chain, no banking |

- **Deps:** `P2-2`, `B1` — which now carries `B2` behind it, so this is unchanged in substance.
  Within the build, `P3-4` and `P3-8` follow `P3-3`, and `P3-2a` follows all three — it has nothing
  to detect until there is traffic to pass.
- **Review:** drive the `B1` fare again, now with traffic | web build | **Harder in a good way, or
  just annoying?**
- ⚠️ **`P3-2a` is here because the review question is otherwise rigged against the build.** Dense
  traffic converts an obstacle into an opportunity *only if threading it pays*; with scoring wholly in
  `B4`, this review would judge traffic in the one state where traffic has no upside, and a "just
  annoying" verdict would be an artifact of the ordering rather than a finding about the traffic.
- **Prior art: Burnout 3.** Near-miss, oncoming-lane driving and a risk-fed boost meter are the
  fullest working-out of *traffic as reward rather than obstacle*, and the threshold, the speed gate
  and the pop are tuned quantities there rather than obvious ones.
- ⚠️ **`Q19` lands here.** 5.17% of drawn carriageway has solid geometry standing in it at bumper
  height, and `RoadGraph` has no idea any of it is there, so traffic will route into it.

### Build `B4` — "It's a game" — **runs fourth**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-2b` | `ScoreSystem` — base, time bonus, drift/air/speed, **the style chain and its banking**, and the fare combo. Absorbs `P3-2a`'s near miss | Style points award live during driving, and the style chain is **losable** — a hard crash costs it unbanked |
| `P3-1b` | Remaining fare types — **cross-harbour** and long haul | Cross-harbour fare works |
| `P3-5b` | Full HUD — bilingual destination callouts, safe areas, one-handed layout | Readable one-handed in daylight |

- **Deps:** `B1`, `B3`. **Review:** play a full session, twice | web build | **Do you want another
  go?** This is the risk register's "novelty does not survive the first session", put directly.
- ⚠️ **`P3-2b` wants two numbers the controller does not publish yet.** Skid smoke and tyre marks
  need a **traction-loss signal**, and wheels that spin up under power and lock under braking need
  **per-wheel angular velocity**. `VehicleWheel3D` gives both free through `get_skidinfo()` — and is
  still refused, because its single `friction_slip` cannot break lateral grip while keeping
  longitudinal traction, which is the drift the style chain is built on (`P0-5a`, asked twice and
  refused twice). Both are cheap to add here instead: `_apply_tyre_forces` already computes
  lateral and longitudinal slip per wheel, so publishing them onto `WheelMount` beside `compression`
  and `steer_angle` costs ~20 lines and changes no physics. **Do it when the effects that consume it
  are built, not before** — `wheel_visual.gd` currently rolls the wheels from road speed, which is a
  lie nobody can see until there is smoke to compare it against.

### `P3-9` Authenticity test round 1

- **Deliverable:** the test run with HK drivers who have not seen the game before.
- **Accept:** ≥3 HK drivers navigate Convention Centre → Times Square with the arrow disabled.
- **Review:** the drivers themselves | a build on a handset | **Human-judged, by people who are not
  the user.** The only test in this plan whose verdict the team cannot give itself.
- **Deps:** all four builds, and `P0-3b` for the handset.
- **Still needed after `P3-9a`, and not a repeat of it.** `P3-9a` tests the city on a keyboard at a
  desk with nothing to do; this tests the *game* on a handset under a thumb, with a HUD whose arrow
  has to be deliberately switched off. **Recruit different drivers** — the `P3-9a` cohort has already
  learnt the map, which is the exact thing being measured.

> **Phase 3 gate — go/no-go on full production.** Required: `P3-9` passes; 60fps held on the device
> floor; the user judges the game fun.

---

## After the slice

### Phase 4 — The elevated network

**Goal:** the 23.3% of carriageway that `Q13` excluded becomes drivable network rather than scenery.

**Broken down, where the other post-slice phases are not**, for two reasons. It is the only one whose
assumptions the slice will *not* change — the data is measured and the defects are named in `Q13`,
`Q15`, `Q19`, `Q21` and `Q22`. And it stopped being hypothetical when shipping tile collision made
the physical ramps climbable: the network is already half-open by accident, and a plan is cheaper
than discovering the rest of it from a bug report.

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
- ⚠️ **Also inherits `Q22`** — 10.2% of off-grade carriageway hangs past its structure, which is
  cosmetic only while nothing off-grade is drivable. Opening the network puts a player on a ribbon
  whose outer metre has nothing under it.
- **Note:** `P4-1` reverses an acceptance criterion this project measured and proved over 505 probes.
  That is not a mistake being corrected — `Q13`'s refusal was the right call for a slice with no
  ramps. **Record it as a scope change, not a bug fix**, or the history stops making sense.

### Outline only — refine once Phase 3 lands

- **Phase 5 — Content:** Causeway Bay, then Central. Full vehicle roster, audio pass, night mode.
- **Phase 6 — Production polish:** menus, settings, save/progression, accessibility, localisation QA.
- **Phase 7 — Ship:** free-slice boundary, one-time unlock IAP, store assets, web demo, HK press
  outreach, legal sight-check of landmark depiction.

Deliberately not broken down. Anything planned in detail now would be a guess, and the slice will
change the assumptions.

---

## Working agreements for agents

- Reference the task ID in every commit.
- Update `docs/PROGRESS.md` when a task changes status, and `docs/DECISIONS.md` when a decision or open question
  arises.
- If a task's acceptance criteria turn out to be wrong, say so and propose a change rather than
  quietly redefining it.
- Do not start a task whose dependencies are unmet without flagging it.
- **Producing the review artifact is the agent's job; answering the verdict question is not.**
- **Stop at every review point and wait.** "Machine-checked" is never a substitute — the verify tools
  shipped broken-and-green inside a single commit once already.
- **Look at the screenshots before saying a build is ready to review.** A green driver run is not a
  rendered game.
