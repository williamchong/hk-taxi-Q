# Progress

**Live state only.** What is in flight, what is measured, what is at risk. Update it whenever a task
changes status, a number is re-measured, or a question opens or closes.

- **Why something is the way it is** → `DECISIONS.md`, keyed by the `Q` or task ID.
- **What happened when** → git.

Last updated: 2026-08-07

---

## Current status

**Phase 0 and Phase 1 are complete. Phase 2 is two hardware-blocked tasks from its gate.**

The ETL turns six government map sheets and one road geodatabase into a drivable Wan Chai in **3.0 s
from an empty `out/`**: 65 vertex-coloured tiles at two LOD tiers, 797 road edges over 615 nodes with
217 turn restrictions, one 35k-triangle road surface with trimesh collision, and 29 fare nodes. Godot
streams it, the car drives it, and it exports to a web PCK.

**Shipped in Phase 2, all five reviewed and passed:** `CityStreamer` (`P2-1`), `RoadGraph` (`P2-2`),
the queried start line (`P2-3`), the chase camera and building collision (`P2-5`), and the off-grade
carriageway on its real structure (`P2-7`). **Left:** `P2-4` (`InputRouter` across three input paths)
and `P2-6` (the perf pass) — both blocked on `P0-3b`, which needs a signing identity and the two
floor handsets. **Nothing on the critical path is blocked on software.**

**Phase 3 runs `B2` → `B1` → `B3` → `B4`** — the Hong Kong driving *experience* is finished and
tested before any taxi gameplay element exists, so test players judge the scene on its own. `B2`
carries the player taxi (`P3-11`), and `P3-9a` then puts that build in front of ≥3 HK drivers over a
web link. Order, deps and acceptance are in `PLAN.md`; the reorder and what it costs are in
`DECISIONS.md`.

**The premise is measured rather than assumed.** `Q8` closed when the user drove the real city: an
HK-like map is a fun enough gimmick on its own. That retires the founding risk and replaces it with a
narrower one — *gimmick* is the user's own word, and a gimmick carries a first session. "Novelty does
not survive the first session" is the live entry in the register, and it is `P3-*`'s to answer.

**Two things are knowingly missing from the world.** The **elevated network is closed to driving** —
`nearest_edge` refuses all 60 off-grade edges (`Q13`, reopened deliberately in Phase 4) — and
**nothing in the authenticity table is built**: no traffic, no trams, no neon (`P3-3`, `P3-4`,
`P3-8`). The ground shipped with `P3-10` and is solid, so leaving the carriageway now puts the car on
the pavement instead of through it.

### Task board

| ID | Task | Status | Notes |
|---|---|---|---|
| `P0-1` | Source data granularity | ✅ Done | 6 sheets, glTF per sheet ~44 MB. Buildings are scriptable; closed `Q2`, `Q3`, `Q5`. |
| `P0-2` | ⚠️ Z-value spike | ✅ Done | No Z, but `ELEVATION` encodes the level. Region holds. Closed `Q1`. |
| `P0-3` | Godot project scaffold | ✅ Done | Godot 4.7.1. macOS / web / Android export verified. |
| `P0-3b` | Mobile device build verification | ⬜ Not started | Needs a signing identity and the two floor handsets. Blocks `P2-4`'s and `P2-6`'s reviews. |
| `P0-4` | ETL scaffold | ✅ Done | `pipeline/` + `hong_kong.yaml`. Found the ~304 m datum trap. |
| `P0-5` | Grey-box fun test | ⚠️ Passed, conditional | Handling accepted; fun verdict deferred to `Q8`, now closed. |
| `P0-5a` | └ Vehicle controller approach | ✅ Done | Custom raycast on `RigidBody3D`. `VehicleBody3D` measured and rejected. |
| `P0-5b/c/d` | └ Circuit, camera, drive test | ✅ Done | Circuit from JSON, spring-arm camera, driven. |
| `P1-1` | Source fetching | ✅ Done | Sheets derived from the published index, not listed. Idempotent. |
| `P1-2` | Building meshes | ✅ Done | 65 tiles; 989k → 434k → 222k triangles. Verified in-engine. |
| `P1-2t` | └ Terrain evaluation | ⚠️ Superseded | Judged unaffordable at 267 MB — but 224 MB of that was the JPEG. Replaced by `P3-10`, which ships no texture. |
| `P1-3` | Road graph | ✅ Done | 797 edges, 615 nodes, 217 turns, 96.3% connected. Closed `Q9`, `Q11`, `Q12`. |
| `P1-4` | Road surface mesh | ✅ Done | One mesh, one draw call, kerbs, trimesh collision. All 393 single-level junctions covered. Opened `Q13`. Two driver-reported defects fixed: kerbs buried in a neighbour's carriageway, and the hull pinching the road at a bend. |
| `P1-5` | Fare nodes | ✅ Done | 29 nodes (14 stands, 6 cross-harbour; 15 PUDO) from 793 territory-wide points. Opened `Q14`, `Q15`. |
| `P1-6` | Export and manifest | ✅ Done | `city.json` + one-command pipeline; byte-reproducible. Opened `Q16`. |
| `P1-7` | Godot import | ✅ Done | **Phase 1 gate passed.** Georeferenced to 1 cm, checked in-engine. |
| `P2-1` | `CityStreamer` | ✅ Done — review passed | Threaded load/unload by published `aabb`. Draw calls 70 → 53; the review dropped the exact-weld tier, closing `Q16`. |
| `P2-2` | `RoadGraph` + debug overlay | ✅ Done — review passed | One parse per scene; p99 **45 µs** against a 1 ms budget. Refuses all 60 off-grade edges (`Q13`). Found the carriageway-width contract gap. |
| `P2-3` | Vehicle on real geometry | ✅ Done — review passed | `RoadSpawn` resolves the start line through `RoadGraph`; the hand-written transform is deleted. Verdict: *"car seems ok"*. |
| `P2-4` | `InputRouter` | ⬜ Not started | Touch, gamepad and keyboard → one action set. Its review needs `P0-3b`'s handset. |
| `P2-5` | Chase camera | ✅ Done — review passed | Unblocked by shipping building collision. No shape-cast needed. Opened `Q19`, `Q20`. |
| `P2-7` | Off-grade carriageway on its structure | ✅ Done — review passed | Deck heights sampled from `INFRASTRUCTURE`. \|error\| p90 **4.13 m → 0.095 m** against a 0.50 m criterion, graded against the shipped tiles by a tool sharing no code with the pipeline. Closed `Q20` and `Q23`, largely closed `Q13`, opened `Q21` and `Q22`. Nothing became drivable. |
| `P2-6` | Performance pass to budget | ⬜ Not started | **Phase 2 gate.** Runs last because it measures the geometry that ships. Needs `P0-3b`. |
| `P3-11` / `P3-10` / `P3-7` / `P3-6` | Build `B2` — "it reads as HK" — **runs 1st** | 🟡 In progress | Taxi first (it is in every later screenshot), then ground (`Q18`), then the window shader, then the hero buildings. `P3-6` is the only one not started. |
| `P3-11` | └ Player taxi model | 🟡 **Awaiting review** | Generated by `tools/make_vehicle.py`; **1,168 triangles** in scene across two `.glb`s (592 body, 4 × 144 tyres). Untextured. Chassis taken from the scene, not chosen. Latest shots in `build/driver/taxi_*`. ⚠️ The rocker strip and red valance are unjudged from the play camera, which never shows the flank. |
| `P3-10` | └ Ground surface | 🟡 **Awaiting review** | Terrain is a tiled class: **+87,649 triangles** at LOD0, no texture, **no extra draw call**, **+4.56 MB of PCK**, and it **collides**. `ground_sink_m: 0.20` sized by `tools/ground_clearance.py`. Reads as ground on the flat core; **buries the carriageway on hill streets** — `Q24`. `Q29` fixed what the review found: the ground was smooth-shaded. Shots in `build/driver/q29*`. |
| `P3-7` | └ Window-band shader, and its `TEXCOORD_0` payload | 🟡 **Awaiting review** | One commit across both sides; `city.json` schema 4 → 5. Storey height **2.8 m measured**, not guessed. **+4.01 MB of PCK**, **zero triangles moved**, no extra draw call. Shots in `build/driver/p37*`. Currently switched off — see `Q26`. |
| `P3-9a` | Recognition round 0 — the city, before the game | ⬜ Not started | ≥3 HK drivers on the `B2` web build. No HUD, nothing to do. Asks *do they know where they are*, and *did they keep driving anyway*. |
| `P3-1a` / `P3-5a` | Build `B1` — "one fare" — **runs 2nd** | ⬜ Not started | Fare state machine + deliberately ugly HUD. |
| `P3-3` / `P3-4` / `P3-8` / `P3-2a` | Build `B3` — "the streets are alive" — **runs 3rd** | ⬜ Not started | Traffic, trams, bus lanes, and near-miss scoring moved up from `B4`. |
| `P3-2b` / `P3-1b` / `P3-5b` | Build `B4` — "it's a game" — **runs 4th** | ⬜ Not started | Style chain, cross-harbour fares, full HUD. |
| `P3-9` | Authenticity test round 1 | ⬜ Not started | **Phase 3 gate.** ≥3 HK drivers on a handset, arrow disabled. Different drivers from `P3-9a` — that cohort has learnt the map. |
| `P4-*` | The elevated network | ⬜ Not started | Post-slice, but broken down: the data is measured and shipping collision half-opened the network by accident. Reverses `P2-2`'s refusal; closes `Q15`. |

Legend: ⬜ not started · 🟡 in progress · ✅ done · ⚠️ conditional · ❌ blocked

---

## Open questions

Each row is the live status. **The claim, the evidence and what is refused are in `DECISIONS.md`**
under the same ID.

| # | Question | Impact | Owner | Status |
|---|---|---|---|---|
| `Q6` | Does the region need Central for the circuit to feel complete? | Scope | after `P3-9` | 🟡 Deferred |
| `Q13` | Nothing ramps between elevation levels in the source's attributes | 23.3% of carriageway area unreachable | `P2-2` → `P4-1` | 🟢 Largely answered — all 36 mixed nodes are ramps, median step 0.04 m. What remains is 5 tunnel portals and a stub |
| `Q14` | Taxi stands carry operating-time restrictions that `P1-5` discards | A part-time cross-harbour stand is modelled as full-time | `P3-1` | 🟡 Open, deferred — a schema bump plus a parser whenever the fare loop needs it |
| `Q15` | Fare nodes snap by plan distance only, because the published points are 2D | A stand under a flyover cannot prefer the street below. No Wan Chai node is affected | `P4-2` | 🟡 Open — not reachable with this source |
| `Q19` | **5.17% of drawn carriageway has solid geometry standing in it at bumper height** | Invisible walls on legal carriageway, and `P3-3`'s traffic will route into them | `P3-3` | 🔴 Open. The `BUILDING` half is the 1.6× widening eating the frontage — a playability trade. The `INFRASTRUCTURE` half shrank with `Q20`. **Wants a verify tool that fails the build when the carriageway is occupied** |
| `Q21` | Should level −1 carriageway be drawn at all? | 11.6% of carriageway area with no viewer, solid since collision shipped | Phase 4 | 🟡 Open — heights cannot be improved (a tunnel is a void), and 11 of 30 ends are clipped at the region boundary |
| `Q22` | **10.2% of off-grade carriageway hangs past its structure** | Cosmetic until Phase 4, when a wheel leaving the deck finds air | Phase 4 | 🟡 Open — no width rule reaches the rest |
| `Q24` | **The road is a plane and the ground is not** | Solid geometry in legal road, on top of `Q19`'s 5.17% | `roads.py` | 🟢 Half closed — along the road, area proud **3.289% → 1.898%**. Across the road is untouched and is `Q19`'s |
| `Q26` | **Which look ships — the measured Hong Kong one or the clean/futuristic one?** | The art direction rests on "accurate city, toy vehicles", and recognition is the product | `P3-9a` | 🔴 Open, and a verdict rather than a measurement. Three candidates, one `cp` apart. ⚠️ **Every shot taken before `Q27` closed is unusable** — re-shoot before comparing |
| `Q30` | **The shipped façade palette is not the one `ART_DESIGN.md` authorises** | One building in five is more saturated than the direction sanctions | `Q26` | 🔴 Open. ⚠️ `facade_hue.strength` cannot fix it — amplifying chroma widens the spread faster than it moves the middle. **Belongs with `Q26`'s verdict** |
| `Q31` | **The city's value range has an empty middle** | Half a street frame carrying no information — the frame the player occupies all game | `P3-9a` | 🔴 Open. ⚠️ The palette lever has been pulled (`Q33`) and it was not the cause. **The shadow fill is the only untried candidate**, and both failing frames are the two shot in shade |
| `Q35` | **A per-building material draw gives a salt-and-pepper skyline** | Two adjacent blocks can land 13 reflectance points apart, where real blocks share cladding | `buildings.py`, `hong_kong.yaml` | 🔴 Open. Candidates: a spatial hash on position, a block join from an external dataset, or accepting it. ⚠️ **Grade it from the street, not the skyline** |
| `Q34′` | **The material ring weights are authored against a population that has moved** | `Q37`'s resurvey took the near-neutral ring from 51.6% to 40.5% of surveyed stock, so weights chosen to match the height ramp's expected reflectance no longer do | `hong_kong.yaml`, `buildings.py` | 🟡 Open, and mechanical rather than a judgement. `panel_grey` fell 33.7% → 28.6% on its own. ⚠️ The config block says **re-derive these if the ramp moves** — the survey moving counts |
| `Q38` | **`exposure_anchor` is baked into `COLOR_0` at build time**, so a time-of-day change is a full rebuild | Night is planned, and this is the lever it needs | night mode | 🟡 Open, deliberately not fixed. The fix is cheap and known; it costs `_check_exposure` and its test, both shipped to close a real defect |
| `Q39` | **`wall_sky_tint` is uniform**, so a canyon wall takes a rooftop parapet's sky bounce | Overstates sky bounce in exactly the frames `Q31` reports as broken | `Q31` | 🟡 Open — free once a sky-visibility term exists, and nothing before that. ⚠️ Do not lower it globally |

**Closed:** `Q1` `Q2` `Q3` `Q4` `Q5` `Q7` `Q8` `Q9` `Q10` `Q11` `Q12` `Q16` `Q17` `Q18` `Q20` `Q23`
`Q25` `Q27` `Q28` `Q29` `Q32` `Q33` `Q34` `Q36` `Q37`. Each has a record in `DECISIONS.md`.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Novelty does not survive the first session | **Medium** | The honest reading of the `Q8` verdict — "gimmick" was the user's own word, and a gimmick carries one session. `P3-9a` asks this risk directly and earliest: a `B2` city with no fares, traffic or score is its harshest form, and **how long each driver keeps going before stopping is the number to write down**. Three levers, all built from assets already scheduled: the **losable style chain** (`P3-2b`); a **drivable roster**, made cheap by `P3-11`'s generator, since the same script builds the minibus, double-decker and tram; and **world-embedded challenges** pinned game-side to edge IDs. Only the first is in the slice; the others are named so Phase 5 does not reinvent them |
| Doesn't read as HK to locals | **High** | `P3-9` with ≥3 real drivers; run again every phase after |
| Carriageway occupied by solid geometry | Medium | `Q19`, 5.17% at bumper height, real since collision shipped. Wants a verify tool that fails the build |
| Grade separation is unreachable | Medium | `Q13`. Largely closed by `P2-7`'s sampling — median step 0.04 m — but the network is still *closed to driving* by `P2-2`'s refusal. Opening it is `P4-1` |
| Perf misses 60fps on device floor | Medium | Budget defined up front; untextured merged tiles are the main lever; `P2-6` is a dedicated pass — and it needs `P0-3b`'s hardware |
| TAM too small to be commercial | Medium | City-agnostic ETL is the scaling answer — city packs, not one city. `Q8` strengthens this: if recognition is the product, a second city is a YAML file |
| GPLv3 forecloses the App Store | **Medium** | GPLv3 §6 conflicts with App Store terms, so store builds need a separate proprietary grant — available only while one party owns the whole copyright. Mitigated by `CONTRIBUTING.md` taking contributions **inbound MIT**. Zero exposure today (no outside contributors) and **no retrofit** once one declines, so the file must land before the repo goes public |
| Landmark depiction IP | Low | Untextured massing; legal sight-check before launch (Phase 7). **The top item in that brief** — the government data terms are permissive, so depiction is the one question left with a plausible adverse answer. See `LICENSING.md` |
| GDScript learning curve | Low | Small codebase; complexity lives in Python |

**Retired.** *Road data lacks Z values* (`Q1` — `ELEVATION` encodes the level; region holds). *Real
geometry isn't fun to drive* (`Q8` — replaced by the novelty risk above). *Source data quirks*
(`P1-3`/`P1-4` — both turned up and both were handled). *Building meshes blow the triangle budget*
(`P1-2`/`P2-1` — worst-case visible is 150,374 against 300k). *Terrain does not fit any budget* (224
of the 267 MB was the JPEG; `P3-10` ships none of it). *The player's car is two boxes* (`P3-11` —
24 → 1,168 triangles, generated from the chassis the scene already published; the lesson it leaves is
that **the docs specified the car so fully that it read as done**, which is how a capability with no
owner hides).

---

## Metrics

Record measured values here, not estimates. ⚠️ **Bundle size is measured from a PCK, never summed
from source files** — that rule has been wrong in both directions once each (`Q16`).

| Metric | Target (mobile) | Latest | Date |
|---|---|---|---|
| FPS on device floor | 60 | — (no device yet — `P0-3b`) | — |
| FPS, Chrome on macOS, 2880×1450 | — | **119** (worst frame 9.7 ms) | 2026-07-31 |
| Draw calls | < 150 | **53** ✅ | 2026-08-01 |
| Visible triangles, worst measured | < 300k | **150,374** ✅ | 2026-08-01 |
| Resident triangles, worst measured | — | **280,807** (a ceiling, not a gate — 236,882 before `P3-10`'s ground) | 2026-08-05 |
| Texture memory | < 128 MB | **0** — no textures ship, ground included | 2026-08-05 |
| Bundle size | < 200 MB | **32.30 MB** PCK, + wasm. **27.73 MB immediately before `P3-10`**, measured either side of the same build with one variable changed, so the **+4.56 MB is the ground and its collider** — and only the total was measured, not the split | 2026-08-05 |
| Tile triangles, LOD0 / LOD1 | — | **521,693 / 253,097** (434,149 / 222,375 before the ground) | 2026-08-05 |
| Ground the source has and the bundle does not | — | **0.76%** of the region (1.76% before `Q25`); **0.42%** within 2 m of a tile boundary against 0.54% in the interior | 2026-08-05 |
| Ground standing proud of the carriageway | — | **2.2% of area, 1.00% of sampled points.** ⚠️ Not comparable with the 1.9% / 0.49% recorded before `Q25`: closing tears made 3.35% more of the carriageway *measurable*. Like-for-like over what both bundles could see, **2.181% → 2.205%** | 2026-08-05 |
| Buildings stage, peak RSS | — | **657 MB** (924 MB before the ground was clipped to the region) | 2026-08-05 |
| Road surface triangles | — | **28,170** (25,028 before `Q24`'s stations; 35,039 before the kerb fix) | 2026-08-05 |
| Boot to drivable (web, warm) | — | 830 ms, of which 260 ms is tile instantiation | 2026-07-31 |
| Tab memory (web) | — | 307 MB | 2026-07-31 |
| ETL full-run time | — | **3.0 s**, whole region from an empty `out/` | 2026-08-02 |
| Deck error, \|error\| p90 vs shipped tiles | ≤ 0.50 m | **0.095 m** ✅ | 2026-08-02 |
| Taxi triangles in scene | 800–2,000 | **1,168** (592 body, 4 × 144 tyres) | 2026-08-07 |
