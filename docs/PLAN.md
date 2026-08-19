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
| `P3-6` | Hero buildings (5) — authored or mesh-sourced (`source_paint`), placed via `landmarks.json` | Source geometry excluded; no z-fighting |
| `P3-7a` | **Survey-driven façade variation** — the openings re-judged: punched windows are glass (`Q44`), panes vary per building (`Q45`), refusal drawn quietly (`W3`). ✅ **Closed as shipped at those three**; `Q42`'s riders are gated, not delivered | Met by what landed: everything dark behind `survey_apply`, parked look byte-identical at every step, each shipped step graded against a pre-fixed bar. ⚠️ **The remainder is gated on `P3-9a` reopening `Q26`** — `C` ships `survey_apply = 0.0`, so a rider built now renders nothing and cannot influence the round that would price it (`DECISIONS.md` `P3-7a`) |
| `P3-12` | **Road markings** — lane dividers, centre lines, kerbside double yellows and a bus-lane edge, drawn procedurally over the ribbon's lane coordinate, **and the `TEXCOORD_1` payload the shader reads**. Arrows, road text and box junctions deliberately out of scope | No texture ships and `mesh_contract.gd` still passes; one primitive, one material, no triangle moved; markings survive the playability widening because U is a lane coordinate; the junction fade is sized against the **measured** cap overlap rather than by eye; `schema_version` bumped on both sides in one commit |
| `P3-13` | ✅ **Kerbside no-stopping from `NSR`** — done 2026-08-19 — the one shipped marking that is invented, sourced. A linear-referencing stage joins the layer to the graph as `(edge, side, V-range, kind)`; the ribbon carries the extent per rail and the codec carries the kind. Parking bays, box junctions and the `ONSTREETPARK` complement deliberately out of scope | Painted length matches the restricted length to within the join's own resolution — graded by `tools/kerbside_error.py`. ✅ **4%**, from 240%; no vehicle class is asserted that the source does not name; the side convention is asserted against `surface.mitres` itself rather than reasoned about; `roadgraph.json` and the shader moved in one commit each per hard rule 5 |

- **Deps:** `P1-2`, `P1-7`. **No longer depends on `B1`** — that dependency was ordering, not
  substance. Nothing in the taxi, the ground, the shader or the hero buildings reads a fare.
- **Within the build:** `P3-11` first, because it appears in every screenshot of every later review —
  a shot taken before it is a shot that has to be retaken. Then `P3-10`, because the remaining two
  are judged against a city that has a floor. Then `P3-7`, then `P3-6`; `P3-7a` follows `P3-7` and
  the region survey, and may run beside `P3-6`.
- ⚠️ **`P3-12` was added after the build closed and after `P3-9a`'s artefact was cut** (2026-08-19).
  It belongs to `B2` by subject — it is the road half of "does this read as Hong Kong" — and it
  depends on nothing in the build, because `P1-4` shipped the lane coordinate it draws on. **Whether
  it goes in front of the drivers is a separate call**: landing it means re-exporting and
  re-verifying a 75.74 MiB web build. See `Q53`.
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
- ⚠️ **Accept, additionally: the wheels must still land where the arches are.** `P0-5` tuned handling
  against the hardpoints in `taxi.tscn` — `WheelMount` markers then, `VehicleWheel3D` nodes since
  `Q50`, at the same positions — and they are authored rather than inferred from the mesh either way.
  Moving the visual car without moving them is how a tuned vehicle silently stops matching its own
  tuning, and the drive would still look fine, because the mesh is not what the physics reads.
- **Review:** the taxi from behind at speed, and parked beside a building for scale | web build |
  **Does it read as a toy in an accurate city, rather than as a box?**

#### `P3-7a` — how the survey becomes the look

- ✅ **Closed as shipped.** `W1`, `W2` and `W3` landed, were graded against pre-fixed bars and were
  accepted by the user on frames. **Everything below from `W4` onward is gated, not scheduled**:
  `Q26` closed on candidate `C`, which ships `survey_apply = 0.0`, so every remaining rider renders
  nothing in the build that reaches a player — and none of them can influence `P3-9a`, the round
  that would price them, because `P3-9a` grades `C`. The gate reopens if `P3-9a`'s drivers reject
  the city *and* attribute it to flat surface; the ground-band batch is then the **first** item, not
  the last. The full argument, and what the remainder is worth, is `DECISIONS.md` `P3-7a`. **Read
  the rest of this section as the plan that resumes, not as work in flight.**
- **Deliverable:** the reliable half of `Q42`'s riders consumed end-to-end (merge vote →
  `TEXCOORD_1.y` → shader), plus the two corrections the user called from `A″`'s frames: punched
  openings behave as glass (`Q44`) and pane colour varies per building (`Q45`). Everything lands
  dark behind `survey_apply = 0.0`, and the parked look stays byte-identical at every step — `Q43`'s
  reducibility check, and how each commit proves it changed nothing it did not mean to. ⚠️ **A
  resumed rider cannot use that check** — see `DECISIONS.md` `P3-7a`.
- **Order — the look fixes run before the riders, because two of `A″`'s defects are already
  judged.** `Q26`'s verdict is a human preference over `A″`, and grading drivers on a look the user
  has already called wrong wastes the drivers. `W1`/`W2` are shader + tuning only — no ETL, no
  schema. The 2026-08-09 drive test added `W3`/`W4` ahead of the riders for the same reason:
  grading drivers on stock that is confidently wrong wastes the drivers. The riders then enrich the
  corrected candidate in reliability order (`Q42`'s fill rates):
  1. `W1` — punched openings as glass (`Q44`): re-scope what an unglazed opening is made of,
     re-shoot, hold the `Q30` chroma bar recorded there. ✅ Landed and accepted 2026-08-09.
  2. `W2` — per-building pane colour (`Q45`): seeded `L*`/`b*` jitter on the hashed fallback and/or
     a pull toward the building's own measured hue. Never on the surveyed tint. ✅ Landed and
     accepted 2026-08-09.
  3. `W3` — **quiet tier for survey-refused buildings.** From the 2026-08-09 drive test of the
     shipped default: shopfronts and confident fenestration on windowless stock — HKCEC's service
     base and tunnel piers, plant boxes, a footbridge lift tower, sportsground walls. The fix:
     `has_shop` runs its draw only where the grammar committed (positive evidence); refused
     buildings fall to punched-with-heavy-piers (never a hash-drawn curtain or fin, which describe a
     confidently glazed skin), a higher solid probability, and muted panes. Committed buildings are
     untouched — the accepted `A‴` look stays as graded. **Why refusal is the lever:** grammar
     committed on 65% of the 2,213 surveyed buildings, but only 12% under 4 m and 25% under 7 m
     against 78% over 40 m — the survey's occlusion bias makes refusal itself the small/occluded-
     structure signal — and `blank` committed **10 times region-wide**, so the one verdict that
     denies openings (`Q43`) is inert at scale. ⚠️ **Not a height gate.** `Q34` stands (height plus
     footprint explain 1.4% of façade signal); eligibility conditions on the survey's own refusal
     state, never on geometry. Consumer-side tunables only, zero schema change; graded like
     `W1`/`W2` (re-shoot, `Q30` bar on all three cameras, parked look byte-identical); its own
     record in `DECISIONS.md`, since it deliberately rebalances the "refusal falls to the hash"
     contract `Q40`/`Q41` wrote down. That record also carries one forward-looking sentence now:
     refusal conservatism extends to `lit_window_share` when the night variant lands. ✅ Landed
     2026-08-10 as five `quiet_*` tunables (`Q46`): `Q30` bar held (+1.10/+0.74/−0.04), parked
     byte-identity held with the quiet values authored; **accepted in scope the same day** on a
     `survey_debug`-tinted drive test — refused stock reads quiet, and the residual sightings
     moved to committed stock (`Q47`).
  4. `W4` — **authored override table, exceptions only.** A committed per-city data file keyed by
     the stable building-ID stem (`DATA_SOURCES.md`'s cross-dataset key), precedence
     **authored > survey > hash**, merged at the same site as the survey overrides. After `W3` this
     is heroes and stragglers, not a population — the canonical entry *was* HKCEC's base: a
     committed-glazed building that is right about its towers and wrong about its podium — and
     `Q47`'s call shrinks this entry: its podium is its own iB1000 `P` block (3.7→56.0 mPD), so
     the extent comes from data and any remaining override covers treatment only. ⚠️ **`P3-6`
     (2026-08-12) then removed HKCEC from the tiles entirely — the canonical entry is moot; do
     not author an HKCEC row.** Only the stragglers remain. ⚠️ Never a
     route around the survey at scale: 771 grammar-refused buildings is the population that
     disqualified overrides as the systematic fix. `Q47` re-proved that from the committed side —
     the tinted drive test put the
     residual wrong windows overwhelmingly on committed ground bands, a population `W4` must not
     absorb; the systematic routes are `R4`'s podium bits or a ground-band survey.
  5. `R1` — `emphasis` (bits 14–16). Fills essentially every read face and coheres with grammar; a
     committed value replaces the grammar-implied reading direction, a refusal keeps it. ⚠️ No hand
     labels exist for it — author emphasis labels for the 25 readable validation faces from the
     cached unwraps, and fix the bar **before** the grading runs (`Q41`'s shape).
  6. `R2` — reconciled storey pitch (bits 0–6). Per-building median over readable faces, the
     2.5–4.5 m sanity window, refusal outside — `Q42`'s own prescription; the field is *visible
     floors on this face*, never a raw read. A committed pitch replaces `floor_height_m` for that
     building; the city constant stays the fallback.
  7. `R3` — `balconies` (bits 12–13), selecting a punched variant.
  8. `R4` — podium (bits 7–11), **last, after `R2`, and data-only**: `Q43` named `podium_floors`
     ("lowest floors forming a visibly distinct podium") against `podium_height_m` ("where the
     tower grid starts") as the next semantic-drift casualty, and the graded run proved it —
     floors × reconciled pitch, graded against the joined boundaries in `podiums.json`
     (310 stems with data metres) on 2026-08-11 by `tools/podium_error.py`, **failed its
     pre-fixed bar** (\|err\| p50 10.76 m against 2.8; Spearman ρ = 0.076, no per-building
     signal). The re-call (`Q47`, same day): pack **data boundaries only**, converting against
     the packed pitch at pack time — after `R2`, so the round-trip bound holds; survey floors
     never pack metres; the complement keeps the shader uniform, and the ground-band batch's
     prompt owes the correctly-worded boundary predicate. `podium_glazed` still informs
     `has_shop`, the only data-supported route to a shopfront sitting roughly where one is —
     priced by Pool B's 40% blindness, bar owed at its turn.
- ⚠️ **Each rider owes its own validation, bar fixed before grading.** The graded run validated
  grammar and glazing only; `Q42`'s fill rates are prioritisation evidence, not validation. Each
  rider closes its slice of `Q42` in `DECISIONS.md` as it lands. ⚠️ **The storey-pitch rider reads
  `Q48` before its bar is fixed** — four instruments already measure pitch and the shipped constant
  (`floor_height_m` 2.8, from `P3-7`'s 2.77) is ~16% below the other three (3.38 / 3.32 / 3.28),
  unreconciled.
- ⚠️ **Three places per rider, one commit:** the merge/pack (`tools/facade_grammar.py`,
  `etl/pipeline/buildings.py`), the shader decode, and `game/tools/verify_tiles.gd` — which today
  asserts `uv2.y != 0.0` is a codec break, so the first written rider fails the verifier unless its
  range check moves in the same commit. No `schema_version` bump: filling a reserved field a
  refusal-aware consumer already reads as "0 = refused" changes bytes, not meaning (`Q42`).
- 🔴 **New reader fields: not paid for, and the bar to pay is now higher than "after `P3-9a`".**
  `Q26` closed on `C`, so a ground-band field bought today has no consumer in the shipped build and
  is a bet on `P3-9a` reopening the look. It is also the **only irreversible item** in the
  remainder — a shader or tuning rider is `git revert`, a paid batch is not — and the one whose wait
  is free by design, since the cache makes waiting cost nothing. So it goes **last among the stopped
  items and first among the resumed ones**, because it targets the player's eye level, the survey's
  worst-covered band and the most likely thing a driver panel faults. The prompt hash is the
  reader's identity; a new field means a
  new graded run plus a paid full re-survey, so everything wanted ships in **one** prompt revision.
  The batch is a **ground-band pass** — crop the bottom ~0–8 m of the existing unwrap, its own
  schema and prompt hash, so the validated façade reader is untouched — collecting the storefront
  fields the drive test showed the survey under-invests (the player's eye level is the survey's
  worst-covered band, so expect heavy refusal; `W3` is the backstop): ground-floor character
  (shop / lobby / carpark / utility / blank, 3 bits), shopfront extent (2 bits), signage density
  (2 bits — placement only, **never rendered text**, `Q42`), exactly filling `TEXCOORD_1.y` bits
  17–23. Opening proportion (the measured answer `glass_ratio`/`mullion_ratio` never got) rides
  `TEXCOORD_1.x`'s free bits. ⚠️ **The `x` bit budget is contested and gets settled on paper before
  anything writes to it**: opening proportion and the two-tone wall colour below are competing for
  11 free bits, and allocating them piecemeal is how the layout ends up needing the bump it was
  designed to avoid. Each field owes `Q43`'s written sentence-conversion check and its own
  validation, bar fixed first — unchanged.
- **Two-tone walls — option promoted to task, gated behind `W3`.** `facade_glazing`'s *light* mode
  is a measured wall/spandrel colour beside the glass tint (`Q42` recorded the option; the
  art-direction condition has now landed). Reuses the glass-tint codec shape in `x`'s free bits.
  ⚠️ The measurement is `L*`/`b*` only — no `a*` is stored — so the third channel is borrowed or
  authored, and the record must say so rather than cite the colour as fully measured. ⚠️ It
  restyles the *committed* stock `W3` promises not to touch, so it runs after `W3`'s re-shoot with
  its own grading (`Q30` bar), never in the same shot set.
- **Two scouts, cheap and offline, before anything is planned around them:**
  - **Street-facing bit (HOLD until measured).** Shopfronts currently wrap all faces of an eligible
    building — alleys and party walls included — and the road graph could gate them per face. But
    it is geometry→façade inference (`Q34`'s discipline applies even though the claim is adjacency,
    not height), and `mesh.py` records that **a per-face payload does not survive vertex
    clustering's representative pick** — the recorded reason survey verdicts are per-building. The
    scout, against data already on disk: what fraction of shopfront-eligible wall area is
    non-street-facing (is the win worth plumbing?); how many pedestrianised shopping streets are
    missing from Road Network v2's carriageways (false quiet on real shopfronts); what extending
    the cluster key by the flag costs in LOD1 vertices. No plumbing until those three numbers are
    in a record. ✅ The blocker itself is now measured (2026-08-10): a payload keyed by the
    survey's own quadrant rule ends with mixed-payload triangle corners on 0.88% / 0.62% of
    LOD0 / LOD1 triangles across 22.9% of buildings — dominated by `face_of` vs `_facing` bucket
    drift — and packed bits interpolate to garbage, so the hold stands. A `flat` varying would
    trade the garbage for whole-triangle flips, not fix it. The three win-sizing numbers above
    remain unmeasured.
  - **iB1000 structure classes.** 3D-BIT Level 1 footprints are extruded *from the B1000
    topographic map*; if the published iB1000 layers carry structure categories (shelter / tank /
    plant), a footprint join gives "utility structure" as data — per-city via config, no vision
    reader. The scalable long-term answer to `W3`'s whole class. Owes `DATA_SOURCES.md`-grade
    verification (format, licence, scriptability) before it is a plan item. ✅ Scouted 2026-08-10:
    the layers carry the categories and more — `Building` `P` podium blocks with base/roof levels
    (`Q47`'s third route), `BuiltStructurePolygon` / `UtilityPolygon` shelter / tank / plant
    classes; FGDB via CSDI dataset `landsd_rcd_1637223748322_25497`. ✅ **Verified to
    `DATA_SOURCES.md` grade 2026-08-10** — dataset entry in `DATA_SOURCES.md` ("iB1000 Digital
    Topographic Map"), numbers and method in `Q47`'s record. ✅ **The route call (2026-08-10)
    makes it the primary podium route**: ingest the `P`-block levels (`gdb.py` polygon-Z decoding
    — a pipeline task), boundary precedence data > survey-inferred, `R4` covering the blocks'
    complement. The `BuiltStructurePolygon` / `UtilityPolygon` classes ride the same ingestion.
    ✅ **Ingested 2026-08-10 (`P3-7a`)**: decoder, `topography` fetch, `podiums:` config and the
    `podium_blocks` reader landed; `Q47`'s counts reproduced in-pipeline. ✅ **Joined 2026-08-11
    (`P3-7a`)**: the `podiums` stage stitches the clipped pieces and writes per-stem boundary
    metres with mechanism-won provenance to `podiums.json` (`Q47`'s record has the measured
    counts). The utility classes now cost only a config block when `W3`'s successor wants them.
- **Accept:** `tools/check.sh` passes; ETL end-to-end on the Wan Chai config; parked `C` frames
  byte-identical at `survey_apply = 0.0` after every step; each rider's pre-fixed bar met and
  recorded; PCK re-measured per rider batch (`y` is all zeros today and pack-compresses at 97% —
  writing riders spends real bytes, and the rule is measure, never estimate); `ring_weights.py` and
  `facade_chroma.py` pastes on the survey-touching commits.
- **Review:** the three audit cameras re-shot at `survey_apply = 1.0` after `W1`/`W2` and again
  after the riders; the enriched candidate (`A‴`) replaces `A″` in `Q26`'s set | web build | **Do
  punched windows read as windows, and do two adjacent towers still read as two buildings?**
- **Deps:** `P3-7` ✅, the region survey ✅ (`Q41`). Independent of `P3-6`.

#### `P3-13` — how the kerbside restriction gets sourced

- **Why it exists:** `P3-12` paints a double yellow on every kerb in the region and `Q53` recorded it
  as unsourceable. It is not — `NSR` is in the same geodatabase the road graph is built from. **This
  is the task that closes `Q54`.**
- ⚠️ **The scale of the error is worse than `Q54` records, and the reason is a field it never read.**
  The data specification publishes `VEHICLE_TYPE`, and only **1 — all motor vehicles** is a yellow
  line: a goods-vehicle or PLB restriction is a sign. That is **33,074 m** of the layer's 44,220 m in
  region, against **131,283 m** of kerb painted today — **4.0x**, not the 3x recorded, and **297%**
  gross over-paint. `TIME_ZONE` is published too, and it is the double-versus-single distinction
  outright: `1` is 24 hours (**27,118 m**, double), `2`/`3`/`4`/`5` are posted hours (**5,956 m**,
  single). `EFFECTIVE_DAY` is uniformly `1` across every `VT=1` feature in region, so it carries
  nothing here and gets no field.
- ✅ **The payload question is settled by measurement, and the answer is the expensive one.**
  Quantising each restriction to a whole `(edge, side)` was the cheap route — four spare codec bits,
  no geometry moved. Measured against the linear-referenced truth, and excluding the 6 m the junction
  fade already blanks at each end, the best threshold leaves **33%** gross error: 3,178 m over-painted
  and 6,227 m missed. That is a large improvement on 297% and it is still a third of the answer wrong,
  so **exact V-ranges ship** (the user's call, 2026-08-19). The cheap route stays recorded because it
  is what the next person will propose.
- **How the extent is carried, without a new attribute.** `surface.py:_rgba` hardcodes `alpha = 255`
  on every road vertex, so **`COLOR_0.a` is already shipped, unread and unchecked** — it becomes the
  restriction extent, written **on the left rail for the nearside and the right rail for the
  offside**. The yellow sits at `U ~ 0.09` lanes, so a fragment on the line is ~95% weighted to its
  own rail and a 0.5 threshold is robust. The **kind** stays in `TEXCOORD_1.x` as two 2-bit fields
  (`kerb_near`, `kerb_off`: absent / none / single / double), max code 2,097,151, still far inside
  float32's 24 exact bits. **The codec says what kind of line; alpha says where it applies.**
- **What that costs, measured before building it:** 83% of covered `(edge, side)` pairs carry exactly
  one contiguous run, median 23 m, and the region has **1,636 run boundaries**. A station pair 0.25 m
  either side of each boundary is **3,272 inserted stations** against 4,596 today — roughly **+19% on
  the road mesh's vertices**, and a larger collision shape with it. Priced from a PCK, never summed.
- **Scope refusal, recorded rather than silent:** `VEHICLE_TYPE = 5` "Others" is **8,323 m** of kerb,
  mostly peak-hours and geometrically distinct from the `VT=1` lines (only 5% of its samples fall
  within 3 m of one). The class it restricts is not named in the data, and asserting a restriction on
  an unnamed class is the same invention this task exists to remove. Refused, with the 8,323 m
  written down. `VT=2/3/4` (2,822 m) are refused for the plainer reason that they are signs.
- ⚠️ **The side convention is the trap, and it renders plausibly when wrong.** `surface.py:mitres`
  offsets **left of travel** and `U = 0` is the nearside, because Hong Kong drives on the left; a
  `cross > 0` test in the source CRS is left-of-travel too, so they agree. Getting it backwards
  mirrors every yellow line in the city and looks like a road. Asserted on a fixture with a known
  side, never reasoned about in a comment.
- ⚠️ **`albedo_linear` is a `flat` varying resting on "no triangle spans two colours".** The alpha
  must be a **separate, non-flat** varying. The hoist survives because it reads `COLOR.rgb` — that
  argument goes in the shader, where the next person changes it.
- ⚠️ **Two owed checks are the non-obvious ones.** Inserting stations moves the ribbon's vertex set,
  which moves the population `clearance.py` reports at — so this owes `tools/narrowing.py` and
  `tools/clearance_reconcile.py --sweep`, exactly the trigger `CLAUDE.md` warns is not obvious. Plus
  `deck_error.py`, `overhang.py`, `ground_clearance.py` and `carriageway_occupancy.py` (which fails
  today; read the exit code against its recorded baseline).
- **Deliverables:** `etl/pipeline/kerbside.py` (new, `clearance.py`'s shape); a
  `roads.kerbside_restrictions:` block in the city yaml carrying both code vocabularies as data
  (hard rule 3 — the second city's codes differ); `roadgraph.json` **schema 3 -> 4**;
  `tools/kerbside_error.py` to grade painted-against-restricted metres and the fare-node table;
  `etl/tests/test_kerbside.py`; the `surface.py`/shader/`verify_road_surface.gd` half; `Q54` closed.
- ⚠️ **`Q54`'s harm argument needs correcting, not inheriting.** Tested against `fares.json`, roughly
  **7 of the 14 taxi stands sit inside a genuine all-motor-vehicle 24-hour restriction** — the source
  says the line really does run past them. The measure double-counts overlapping `NSR` parts (one
  stand read 110%), so the build dedupes runs and re-measures; but "the game paints no-stopping over
  its own 14 taxi stands" is looking like an overstatement, and the record should say so.
- ✅ **Built 2026-08-19, and every superseded number is here rather than edited into the paragraphs
  above.** **1,474 run boundaries**, not 1,636 — the estimate was taken on unclipped source parts
  rather than on the graph's own edges — and after filtering to the drawn ribbon only **1,179
  stations** were inserted. **26,065 m published over 650 edge sides**, not the 33,074 m of source,
  because 1,736 m of it is overlapping features and the rest leaves the region. Gross over-paint was
  **240%**, not 297%, measured off the shipped mesh rather than off a kerb total, and is now **4%**.
  The vertex cost is **+26.4%**, not +19% — a station lands on the carriageway strip *and* on every
  kerb strip beside it — which is **+477 KiB of PCK, +1.20%**. **9 of 14 taxi stands**, not ~7:
  `Q54`'s claim was an *under*statement once the overlaps were deduped. And one obstacle the plan did
  not see: **2,909 m of restriction lands on a kerb the 1.6x widening paved over**, where
  `MARKING_OFFSIDE_KERB` correctly says there is none, so no shader change reaches it and the
  reachable total is **16,726 m**. Full record in `DECISIONS.md` `Q54`.
- **Review:** a kerb known to be unrestricted and one known to be double, before and after |
  **Does the city stop asserting a restriction it cannot support?**
- **Deps:** `P3-12` (the codec and the shader it extends). Independent of everything else in `B2`.

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
- ✅ **`Q19`'s routing half landed ahead of this build, as `Q51` (2026-08-18).** `city.json` publishes a clear corridor width per station and `RoadGraph.is_routable` is the predicate to route on, so traffic will not be sent down an edge the bundle records as blocked. ✅ **That is 24 edges against `Q19`'s grader's 26, reconciled 2026-08-19** as plan cell size — and the reconciliation found and fixed the reason it had been 21: the pipeline's 1 m along-edge spacing was stepping over walls, so `is_routable` was routing traffic onto `e636` HARBOUR ROAD. `ALONG_M` is `CELL_M` now and the published width is a lower bound at that cell (`Q51`). ⚠️ The walls are still there — `Q19`'s geometry half is open — and `nearest_edge` deliberately still resolves them, so the *player* can drive into one. ⚠️ Still owed by this task itself: the graph stores no adjacency and reads none of its 217 turn restrictions.
  height, and `RoadGraph` has no idea any of it is there, so traffic will route into it.

### Build `B4` — "It's a game" — **runs fourth**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-2b` | `ScoreSystem` — base, time bonus, drift/air/speed, **the style chain and its banking**, and the fare combo. Absorbs `P3-2a`'s near miss | Style points award live during driving, and the style chain is **losable** — a hard crash costs it unbanked |
| `P3-1b` | Remaining fare types — **cross-harbour** and long haul | Cross-harbour fare works |
| `P3-5b` | Full HUD — bilingual destination callouts, safe areas, one-handed layout | Readable one-handed in daylight |

- **Deps:** `B1`, `B3`. **Review:** play a full session, twice | web build | **Do you want another
  go?** This is the risk register's "novelty does not survive the first session", put directly.
- ✅ **`P3-2b`'s two missing numbers arrived with `Q50`.** Skid smoke and tyre marks need a
  **traction-loss signal**, and wheels that spin up under power and lock under braking need
  **per-wheel angular velocity**. `VehicleWheel3D` publishes both — `get_skidinfo()` and `get_rpm()`
  — and since `Q50` made the car one, they cost nothing to read. ⚠️ **This is the one thing the
  switch bought that the raycast car could not give**, and it is worth stating next to what it cost
  (`Q50`): the same isotropic `friction_slip` that makes the drift untunable is what makes these
  free. `wheel_visual.gd`'s road-speed roll — the lie nobody could see until there was smoke to
  compare it against — is gone too, because a `VehicleWheel3D` rolls its own mesh from the
  simulation. **Wire them when the effects that consume them are built, not before.**

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
