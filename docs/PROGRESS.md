# Progress

Living document. **Update this whenever a task changes status, a decision is made, or an open
question is answered.** Newest entries at the top of each log.

Last updated: 2026-08-01 (debug chrome gathered under one `F3`-toggled autoload, and turned off by default)

---

## Current status

**Phase 0 complete enough to proceed. Phase 1 is under way and is the critical path.**

The Godot project is scaffolded and exports to macOS, web and Android; the grey-box circuit is
drivable and the handling is accepted; the ETL package exists with the coordinate conversion under
test. **`P0-1` closed on 2026-07-30, taking `Q2`, `Q3` and `Q5` with it** — building data turned
out to be fully scriptable, which retires the top data risk. Only `P0-3b` remains open, and it
needs hardware rather than work.

**`P1-1` closed on 2026-07-30.** `fetch.py` derives the region's six map sheets from the published
index and downloads them; re-running is a no-op. The six sheets it derives match the six `P0-1`
recorded by hand, which is the first end-to-end confirmation that the bounds, the datum and the
index agree.

**`P1-2` closed on 2026-07-30.** `buildings.py` turns the six sheets into **65 vertex-coloured
tiles at three LOD tiers** in six seconds, and all 195 GLBs pass an automated check inside Godot
4.7.1 — one draw call each, vertex colours live, no textures. Real Wan Chai massing now exists as
game-ready assets. Two findings came out of it that change later tasks: the **terrain is not
affordable as shipped** (267 MB of JPEG, 405k triangles), and **ground level in Wan Chai is ~4 m
above the datum**, which `P1-3`'s deck heights currently assume is zero. See `Q11`.

**`P1-3` closed on 2026-07-30, taking `Q9`, `Q11` and `Q12` with it.** `roads.py` turns the road
network geodatabase into **797 edges over 615 nodes with 217 turn restrictions** in 0.8 seconds,
and the graph sits on real ground: sampling the terrain under every vertex puts level-0 roads at a
median **4.21 m**, against the 4.29 m median building base `P1-2` measured independently. **All
four acceptance criteria are met** — the last of them, the one-way spot check, by the user driving
the preview rather than by any test.

**`P1-4` closed on 2026-07-30.** `surface.py` turns the graph into **28,423 triangles of drivable
road** — carriageway, kerbs, junction caps and a trimesh collider — in 0.43 seconds, as one mesh and
one draw call. Both acceptance criteria are met and both were measured rather than argued: the
widening comes from city config, and **all 393 single-level junctions in the region are covered**
under a dense point sample inside the junction radius. It resolved the open decision it inherited
and opened `Q13`, which is the first thing `P1-3` got wrong rather than merely left out.

**The car is on the real city.** `scenes/dev/city_drive.tscn` spawns the `P0-5` taxi in the
nearside lane and drives on `P1-4`'s collider — verified in-engine at the original Hennessy Road
spawn: road at 3.636 m, car at rest at 4.286 m, **all four wheels grounded**, and the 0.649 m
between them is the suspension holding it up rather than the chassis sitting on the tarmac. That
last figure is the cross-check worth having: `handling.tres` predicts a 0.65 m static ride height
from spring rate and corner load, and nothing was tuned to make it agree.

> ⚠️ That spawn was described here and in `ARCHITECTURE.md` as **westbound**, and it never was. The
> transform's basis was hand-written transposed, so the car faced **east — 96.5°** — while sitting
> 2.01 m from the centreline of the *westbound* carriageway (edge 745, travel 263.9°), whose
> widened half-width is 5.12 m. The eastbound carriageway's centreline was 9.34 m away, further
> than its own half-width, so the car was never on it. Right road, right lane for westbound travel,
> facing the wrong way. `Q8`'s drive test was therefore conducted against the legal flow; with no
> traffic and symmetric geometry that does not invalidate the verdict, but it should be on the
> record. The user caught it from the driver's seat before any tool did — *the harbour is north, and
> reaching it meant turning left, so the car was facing east.* The spawn moved to HKCEC on
> 2026-07-31 and is now asserted against its edge vector in-engine.

**The car does not start on the centreline, and that was a real bug rather than a preference.**
Spawned centred it sat at 3 of 4 wheels grounded and crept at 0.8 m/s. The centreline is the worst
place on the network to put a wheel: it is where opposed carriageway ribbons overlap and where
junction caps double up, so a suspension raycast finds two coplanar collision triangles a few
centimetres apart and hunts between them. Moved into the nearside lane, it is 4 of 4 and dead
still. Worth remembering when `P2-2` picks lane centres — the carriageway centre is a seam.

That makes `Q8` **answerable for the first time**: `P0-5`'s verdict was that a grey box cannot say whether this is fun, and this is the same
car on real geometry. It is still a dev scene: since `P1-7` the tiles come from `city.json`, but
there is no ground off the carriageway and the flyovers are unreachable (`Q13`) — `P3-10`'s and
`Q13`'s respectively. **Buildings had no collision until 2026-08-01**, when `P2-5` turned out to be
blocked on it; see the decision log.

**`P1-5` closed on 2026-07-31.** `fares.py` turns two whole-territory taxi datasets — 793 points —
into **29 fare nodes** for the region: 14 stands, of which **6 are cross-harbour**, and 15
pick-up/drop-off points, of which 4 are drop-off only. All four acceptance criteria are met, and
the interesting one is met twice over: every node's `nearest_edge` resolves, and **28 of the 28
nodes whose road has an English name land on a street named in that point's own free-text
description**. The geometry pipeline never reads that prose, so the sources agree with each other
through a route neither was designed to check.

Snapping needed no tolerance to tune. The points are kerbside and the graph is centrelines, so
every one sits 1.18–8.37 m from its road with at least a 4.28 m margin over the runner-up — the
same shape of result as `P1-3`'s node snapping, and for the same reason: the data is cleaner than
a defensive implementation would assume. Two things the source *cannot* say are recorded as `Q14`
and `Q15` rather than guessed at.

**`P1-6` closed on 2026-07-31.** `export.py` reconciles the four stage outputs into `city.json`,
and `python -m pipeline --city hong_kong --region wan_chai` runs the whole chain — fetch,
buildings, roads, surface, fares, export — **in 4.4 seconds from an empty `out/`**. Both acceptance
criteria are met: the set is complete, and it is schema-valid because the stage now says so rather
than because nobody checked.

Two results are worth more than the plumbing. **The build is reproducible**: rebuilt from a clean
`out/`, every one of the 199 shipped files is byte-identical to the previous run, and the sole
difference across the whole tree is the `generated_utc` stamp. And **the region already occupies
102.6 MB of a 200 MB bundle budget** — one region, buildings only, before a single vehicle, sound
or UI asset. That is `Q16`.

**`P1-7` closed on 2026-07-31, and with it Phase 1.** Godot builds Wan Chai from `city.json`:
`CityManifest` reads the manifest, `tile_preview.gd` instantiates the 65 tiles it names —
**989,212 triangles at LOD0** — and `tools/sync_generated.sh` puts a build in front of the engine
by copying exactly what the manifest lists and nothing else.

The gate's wording is "correctly georeferenced", and that is a claim about two parties agreeing:
what `export.py` measured in float64, and where Godot's glTF importer actually put the vertices.
Neither side could check it before. `tools/verify_city.gd` now does, headless: **all 65 tiles agree
with their declared `aabb` to within 1 cm**, every coarser tier stays inside the extent the streamer
will cull against, every tile sits inside `bounds_game`, and the three documents the manifest names
resolve. The check was proven non-vacuous by nudging one tile 0.5 m east, renaming a document and
shrinking `bounds_game` — 15 findings, exit 1, nothing spurious, and the offset reported as
"0.500 m out".

The bug it retires was not cosmetic. Tiles were found by `DirAccess.get_files_at("res://…")`, which
lists a real directory in the editor and returns **nothing** from a PCK — so the shipped game would
have rendered an empty city with no error. That code path is deleted rather than deprecated.

**`P2-*` is unblocked.** `P2-1` (`CityStreamer`) and `P2-3` (`VehicleController` on real geometry)
are the two that matter; `P2-2` (`RoadGraph`) is the one that finally owns the graph parse the
previews currently duplicate.

**`P2-3` closed on 2026-08-01.** The car is no longer placed by a hand-written transform:
`RoadSpawn` resolves fare node `f_004` through `RoadGraph` and reproduces the old literal to 4 dp,
with the orientation asserted against the edge vector by `verify_spawn.gd` — the sixth verify tool,
and one that requires a transposed basis to fail so the assertion cannot pass vacuously. The user's
verdict on *"is this still the `P0-5` car?"* was **"car seems ok"**, which is a pass on the question
that was asked and nothing more: it says the placement change did not damage the handling `P0-5`
already accepted. It is not a statement about feel under a thumb, which is review point 2's job and
still needs `P0-3b`'s hardware. `P2-4` and `P2-5` are what remain before that gate.

**`P0-5` passed conditionally, not cleanly** — the user drove it, found the handling acceptable, and
judged that *fun* cannot be assessed from a grey box at all. See the decision log. The risk it
existed to retire stayed open through the entire ETL slice.

**`Q8` closed on 2026-07-31, and with it that risk.** Driving the real city, the user's verdict is
that an HK-like map is a fun enough gimmick already. The premise the whole project rests on —
recognition is the product — is now measured rather than assumed, and the expensive half of the art
direction is justified by it. Read narrowly, though: a gimmick carries a first session. The
register now tracks "novelty does not survive the first session" in its place, and that is `P3-*`'s
to answer, not Phase 1's.

**The city has no ground, and that is now scheduled rather than merely known.** An evaluation on
2026-08-01 put two questions together — colour the terrain from the source aerial texture, and
colour the buildings without a size or perf cost — and both resolve the same way: **the vertex
stream carries colour, the source texture is read at build time and never shipped.** Terrain
decimated at 4 m is ~88k triangles that merge into the existing tile primitive at no extra draw
call; buildings get their surface detail from two channels already in the bundle carrying nothing.
Neither is next — `P2-3` is the Phase 2 gate — but both land in `B2`, as `P3-10` and inside `P3-7`.
See the decision log and `Q18`.

**The genre direction is settled across three references rather than one, and it changed the plan
once.** Crazy Taxi keeps the loop, Midtown Madness 2 supplies the world philosophy — real shortcuts
over invented ramps — and Forza Horizon supplies the reward layer, chiefly a **losable style
chain**. The one scheduling
consequence: near-miss scoring splits out as **`P3-2a` and moves from `B4` into `B3`**, because that
build's review asks whether traffic is *harder in a good way* and traffic has no upside until
threading it pays. See the decision log.

### Task board

| ID | Task | Status | Notes |
|---|---|---|---|
| `P0-1` | Identify source data granularity | ✅ **Done** | 6 sheets identified, glTF per sheet, ~44 MB each. Buildings are scriptable after all. |
| `P0-2` | ⚠️ Z-value spike | ✅ **Done** | No Z, but `ELEVATION` encodes level. Region holds. |
| `P0-3` | Godot project scaffold | ✅ **Done** | Godot 4.7.1. Imports clean; macOS/web/Android export verified. |
| `P0-3b` | Mobile device build verification | ⬜ Not started | Split out of `P0-3`. `Q4` resolved; now needs only a signing identity and the two floor handsets. Not on the critical path. |
| `P0-4` | ETL scaffold | ✅ **Done** | `pipeline/` + `hong_kong.yaml`; 23 tests, `ruff` clean. Datum trap found — see log. |
| `P0-5` | Grey-box fun test | ⚠️ **Passed, conditional** | Handling accepted. Fun verdict deferred — see decision log. |
| `P0-5a` | └ Vehicle controller approach | ✅ **Done** | Measured. Custom raycast on `RigidBody3D`; `VehicleBody3D` rejected. |
| `P0-5b` | └ Grey-box Gloucester block | ✅ **Done** | Circuit built from JSON; widen_factor is data |
| `P0-5c` | └ Minimal chase camera | ✅ **Done** | Spring arm, speed FOV, look-back |
| `P0-5d` | └ The drive test | ⚠️ **Passed, conditional** | Driven and verified. No blocking feel problem; no fun verdict possible yet. |
| `P1-1` | Source fetching | ✅ **Done** | `fetch.py`; sheets derived from the index, not listed. 67 tests, `ruff` clean. |
| `P1-2` | Building meshes | ✅ **Done** | 65 tiles × 3 LODs; 989k → 184k triangles. Verified in Godot by `game/tools/verify_tiles.gd`. 153 tests, `ruff` clean. |
| `P1-2t` | └ Terrain evaluation | ⚠️ **Measured — not viable as shipped** | 267 MB JPEG, 405k tris. See the decision log; needs a resampling pass to survive. **Superseded 2026-08-01 by `P3-10`:** 224 of the 267 MB was texture, and the answer is to drop the texture rather than resample it. |
| `P1-3` | Road graph | ✅ **Done** | 797 edges, 615 nodes, 217 turn restrictions, 96.3% connected, 0.80 s. `Q9`, `Q11` and `Q12` all resolved here. 234 tests, `ruff` clean. All four acceptance criteria met, the last by the user's eye. |
| `P1-4` | Road surface mesh | ✅ **Done** | 28,423 triangles, one draw call, kerbs and trimesh collision, 0.43 s. All 393 single-level junctions covered. Opened `Q13`. 259 tests, `ruff` clean. |
| `P1-5` | Fare nodes | ✅ **Done** | 29 nodes (14 stands, 15 PUDO) from 793 territory-wide points. All four acceptance criteria met and independently corroborated. Opened `Q14`, `Q15`. 297 tests, `ruff` clean. |
| `P1-6` | Export and manifest | ✅ **Done** | `city.json` + `python -m pipeline`; whole region in 4.4 s, byte-reproducible, 199 files / 102.6 MB. Validation catches what no single stage can. Opened `Q16`. 323 tests, `ruff` clean. |
| `P1-7` | Godot import | ✅ **Done** | **Phase 1 gate passed.** 65 tiles from `city.json`, georeferenced to 1 cm and checked in-engine by `verify_city.gd`. `DirAccess` tile listing deleted — it could never have worked in an export. 329 tests, `ruff` clean. |
| `P2-2` | `RoadGraph` runtime and debug overlay | ✅ **Done — all four criteria met** | One parse per scene, nearest-edge over a 25 m plan grid, lane centres from the **drawn** carriageway. Refuses all 60 off-grade edges (`Q13`), proven over 505 probes. Query time closed 2026-08-01: **p99 45 µs against a 1 ms budget**, timed over 15,865 region-wide probes. `verify_road_graph.gd` is the fourth verify tool. 331 tests, `ruff` clean. |
| `P2-1` | `CityStreamer` | ✅ **Done — review passed 2026-08-01** | Threaded load/unload by distance to the published `aabb`. Draw calls 70 → 53 against a 150 budget. The review verdict dropped LOD0: worst-case **visible triangles 249,210 → 150,374** against 300k, and the **PCK 51.6 → 21.1 MB**. Bands are now a single 250 m edge, 400 m unload, 15 m hysteresis, in `streaming.tres`. `verify_city_streamer.gd` is the fifth verify tool. Opened the shadow-cascade finding. |
| `P2-3` | Vehicle on real geometry | ✅ **Done — review passed 2026-08-01** | The hand-written spawn transform is gone: `RoadSpawn` resolves fare node `f_004` through `RoadGraph` and `drive_harness.gd` places the car, reproducing the old literal to **4 dp** and reporting `0.00 m` from the lane centre with `+1.00` heading agreement. `verify_spawn.gd` is the sixth verify tool and asserts the orientation against the edge vector. The user's verdict on *is this still the `P0-5` car?* was **"car seems ok"** — a pass, and read no wider than it is said. |
| `P2-5` | Chase camera | ✅ **Done — review passed 2026-08-01** | Unblocked by shipping building collision — its "no clipping through buildings" criterion was unreachable while the city had none. Speed FOV and look-back already existed and now run on real geometry. **No shape-cast needed**: the 0.3 m spring-arm margin already exceeds the 6 cm near plane, proven by flipping the camera into a wall with look-back. Verdict *"camera work mostly with one exception where a road suddenly appears mid air"* — measured and found to be geometry, not the camera: nothing sits in the car's 0.3–3.0 m band there. Opened `Q19` and `Q20`. |
| `P2-7` | Off-grade carriageway on its structure | 🟡 **In progress — passing, and the drive's two findings are fixed; the re-drive is left** | **New 2026-08-01.** Sample deck heights from `INFRASTRUCTURE` instead of the flat `elevation_levels` offset; the network stays closed to driving. Placed in Phase 2 because it is a **data-contract** change and `P3-3`'s traffic will run on that contract. Answers `Q20`, shrinks `Q19`. **The 36 nodes are classified and they are all ramps — 17 junctions, 13 attribute flips, 5 tunnel portals, 1 stub, and no plan-coincident crossings at all.** Steps 4 and 5 landed 2026-08-02: `build_region` split into two passes, 44 of 45 off-grade edges sampled, 16 level-0 ends lifted onto their ramp, and node heights now follow a stated rule instead of source iteration order. **The median step at the 36 nodes went 6.00 m → 0.04 m, and the 6 left over 2 m are exactly the 5 tunnel portals and the stub step 1 predicted.** Three plan answers have now been measured and replaced, the latest being the *fallback*: an uncovered station takes the deck either side of it, because `INFRASTRUCTURE` stops being modelled where a ramp reaches grade. 390 tests, `ruff` clean, `tools/check.sh` green, 737 drivable edges unchanged. Step 6 bumped `roadgraph.json` to **schema 2** across both sides. Step 7 graded it against the **shipped tiles** with `tools/deck_error.py`, which shares no code with the pipeline: **|error| p90 4.131 m to 0.095 m against a 0.50 m criterion**, deepest intrusion 4.67 m to 0.34 m, and the tool reproduces the recorded 4.19 m baseline at 4.13 m. **Acceptance met.** The step-8 drive then found the two things no internal number could: coincident surfaces, fixed with a 0.20 m clearance, and **widening on structure**, fixed 2026-08-02 by holding off-grade ribbon to its authored width — carriageway hanging in air 20.1% → **10.2%**, off-grade drawn area −31%, `roadgraph.json` byte-identical. 433 tests, `ruff` clean, `tools/check.sh` exit 0, 737 drivable edges unchanged, `deck_error` still passing at p90 0.094 m — though its deepest intrusion moved 0.30 → **0.48 m against a 0.50 gate**, one station of 3,286 at the `CANAL ROAD FLYOVER` touchdown. Opens `Q22`. **The re-drive then found the rule's boundary**: width is keyed on the edge, but 1,070 m of level-0 carriageway across 28 edges sits on structure at full width — `Q23`, which needs a per-station width and a schema bump. See the decision log. |
| `P4-*` | The elevated network | ⬜ Not started | **New 2026-08-01.** Post-slice, and **broken down** where the other post-slice phases are not — the data is measured and shipping collision already half-opened the network by accident. Reverses `P2-2`'s off-grade refusal deliberately and closes `Q15`. |
| `P3-2a` | Near-miss scoring | ⬜ Not started | **New 2026-08-01.** Build `B3`. Split out of `P3-2` and moved from `B4` into `B3`: that build's review asks whether traffic is *"harder in a good way, or just annoying"*, and it cannot answer honestly while threading traffic pays nothing. See the decision log. |
| `P3-7` | Window-band shader | ⬜ Not started | Build `B2`. **Acceptance grew 2026-08-01:** the shader's two inputs ship as `TEXCOORD_0` from the ETL, so this is one commit across both sides with a `schema_version` bump. See the decision log. |
| `P3-10` | Ground surface | ⬜ Not started | **New 2026-08-01.** Build `B2`. There is no ground today. Decimated terrain, vertex-coloured, merged into the tile primitive; no texture ships. Flat colour first, photo-derived land-cover classes only if flat reads dead — that is `Q18`. |
| `P3-*` | Playable slice | ⬜ Blocked | Gated on `P2-3`; `P2-2` cleared |

Legend: ⬜ not started · 🟡 in progress · ✅ done · ❌ blocked

---

## Open questions

| # | Question | Impact | Owner | Status |
|---|---|---|---|---|
| Q1 | Do Road Network v2 centrelines carry Z values? | **Critical** — was the region-choice risk | `P0-2` | ✅ **Resolved 2026-07-29** |
| Q2 | Which LandsD 1:1000 sheet numbers cover the region? | Blocks automated fetching of building data | `P0-1` | ✅ **Resolved 2026-07-30** — 6 sheets, derived not hardcoded |
| Q3 | Can building data be downloaded programmatically at all? | Was the top risk | `P0-1` | ✅ **Resolved 2026-07-30** — yes, the sheet index carries direct URLs |
| Q4 | Confirm the device floor | Sets the whole perf budget and gates `P0-3b` | user | ✅ **Resolved 2026-07-29** |
| Q5 | Actual file sizes of the region's building data | Affects fetch time and disk planning | `P0-1` | ✅ **Resolved 2026-07-30** — ~44 MB/sheet, ~280 MB for the region. Roads: `CENTERLINE.gml` is 486 MB territory-wide |
| Q6 | Does the region need Central for the circuit to feel complete? | Scope | after `P3-9` | 🟡 Deferred |
| Q7 | Does game-space Z run negative northward, or should the origin move to the NW corner? | Data contract — tile IDs and every position in `city.json` | `P1-6` | ✅ **Resolved 2026-07-30** — NW corner |
| Q8 | What is the cheapest build that lets the user judge "is this fun?" | Was the top project risk — `P0-5` did not answer it | user | ✅ **Resolved 2026-07-31** — the car on real Wan Chai. Verdict: driving an HK-like map is a fun enough gimmick already |
| Q9 | Does `P1-3` read the 17 MB FGDB or the 539 MB per-layer GML? | 522 MB of download and disk per clone | `P1-3` | ✅ **Resolved 2026-07-30** — the geodatabase; every GML dropped from config |
| Q10 | Is the game-space origin per region, or shared per city? | Whether two regions can stitch into one continuous map | `P1-6` | ✅ **Resolved 2026-07-30** — both: local origin plus a recorded `city_offset` |
| Q11 | Where is ground level? `elevation_levels[0] = 0.0` puts at-grade roads at y=0, but 99.9% of Wan Chai's buildings have their base **above 2 m** (median 4.29 m) | Roads would run ~4 m below every front door, and under the terrain | `P1-3` | ✅ **Resolved 2026-07-30** — sample the terrain height field |
| Q12 | Are the road graph's one-way directions right on the ground? | `P1-3`'s last acceptance criterion, and the thing no test can settle | user | ✅ **Resolved 2026-07-30** — Jaffe Road confirmed eastbound; the source agrees with the street |
| Q13 | Nothing ramps between elevation levels. All 36 nodes where two levels meet step by a whole deck height — 6 m at a flyover, 8 m at a tunnel mouth | The elevated and underground networks are topologically connected and geometrically unreachable; **23.3% of the region's carriageway area** cannot be driven onto | `P2-2` | 🟡 **Open — raised 2026-07-30 by `P1-4`; narrowed 2026-07-31, again 2026-08-01, and largely answered 2026-08-02 when `P2-7` shipped the sampling.** All 36 are classified and **every one is a ramp**: 17 junctions where the structure reaches grade, 13 where the source's `ELEVATION` attribute flips partway up, 5 tunnel portals, 1 stub with no structure. **Measured after the fix: the median step is 0.04 m and 26 of the 36 are inside 0.5 m.** The ramp junctions closed to 0.62–1.63 m rather than the ≤0.93 m step 1 predicted — `INFRASTRUCTURE` stops being modelled where a ramp reaches grade, so the last stretch of a touchdown is interpolated rather than sampled. What is left is **the 5 portals and the stub** — a tunnel is a void and no height source repairs it. See the decision log |
| Q14 | Taxi stands carry **operating-time restrictions** in `Status_EN` — eight territory-wide, one in the region (Russell Street, cross-harbour 1200-0600) — and `P1-5` discards them | A part-time cross-harbour stand is modelled as a full-time one. Small today; it is exactly the kind of detail `P3-9`'s authenticity test would catch | `P3-1` | 🟡 **Open — raised 2026-07-31 by `P1-5`**, deliberately deferred |
| Q15 | Fare nodes snap to the road graph by **plan distance only**, because the published points are 2D | A stand under a flyover has nothing in it to prefer the street below over the deck above. No node in Wan Chai is affected — every winner is level 0 — but this shares a root cause with `Q13` | `P2-2` | 🟡 **Open — raised 2026-07-31 by `P1-5`**, not reachable with this source |
| Q17 | No CI. Every check is a local convention, and `tools/check.sh` runs only when someone remembers — on a repo where two verify tools shipped broken-and-green inside one commit | The checks exist and are now capable of failing; nothing makes them run. The Python half (`ruff`, `pytest`, `gdformat`) needs no engine and is nearly free to automate; the Godot half needs the binary plus export templates in a runner | — | ✅ **Resolved 2026-07-31** — GitHub Actions runs both halves. Export templates turned out not to be needed: only exports want them, and CI does not export. **Three of the six checks; the generated-asset contracts are not covered** — see the decision log |
| Q16 | One region measures **56.4 MB** in the PCK against a 200 MB bundle budget — before any vehicle, audio or UI asset, and before a second region | Half the iOS cellular threshold spent on the part of the game the player looks at but never touches | `P2-1` | ✅ **Resolved 2026-08-01** — the tiers do not all ship. LOD0 dropped after the `P2-1` review found it indistinguishable; **51.6 → 21.1 MB PCK**, measured from real exports |
| Q19 | **5.17% of the drawn carriageway has solid geometry standing in it at bumper height.** Split by grade: `BUILDING` at grade 1.72%, `INFRASTRUCTURE` at grade 1.60%, and **1.87% on off-grade ribbon nobody can reach**. The rows do not sum to the headline and are not meant to — 38 cells hold both classes and are counted in each. Cosmetic until 2026-08-01; now every square metre is a collider | The car is stopped by invisible walls on legal carriageway, and `P3-3`'s traffic will route into them. The at-grade half is a real defect; the off-grade half is an artefact of `Q20` and disappears with it | `P2-7` | 🔴 **Open — raised 2026-08-01** by the user's `P2-5` drive, then measured, then re-split |
| Q20 | **The off-grade carriageway is drawn at an invented height, and collision has made the ramps climbable.** `elevation_levels` gives level 1 a flat **+6.0 m** offset, but the real decks vary: measured against the `INFRASTRUCTURE` structure the ribbon is off by **>1 m in 78%** of samples and **>2 m in 54%**, median **−1.51 m**, p10–p90 spread **6.51 m**, and it sits *below* the structure 72% of the time. So 23.3% of drawn carriageway floats through a flyover instead of lying on it, with no ramps because `Q13`'s ramps are the missing piece | `Q13` deferred this on the grounds that the elevated network was **unreachable**. That premise died on 2026-08-01: tile geometry is now solid, so the physical ramps are drivable and a player who climbs one arrives at a ribbon that is not there. Either close the network properly or open it properly — it is no longer a drawing question | `P2-7` | 🟢 **Answered 2026-08-02.** Implemented and then **graded against the shipped tiles** by `tools/deck_error.py`, which shares no code with the pipeline: |error| p90 **4.131 m to 0.095 m** against a 0.50 m criterion, deepest intrusion **4.67 m to 0.34 m**, 92.3% of the carriageway within ±0.10 m of its deck. The tool validates itself by reproducing the recorded 4.19 m baseline at 4.13 m. Closes once the review drive confirms it (step 8). Slab-continuity sampling of `INFRASTRUCTURE`, 10 m resampling, a terrain gate, and a level-0 half nobody had seen: the edges leading into 13 of the 36 nodes are themselves on the ramp. Baseline to beat is \|error\| p90 **4.19 m** against the shipped tiles. See the decision log |
| Q18 | Does flat-coloured ground read as ground, or does it need land-cover colour classified from the source aerial texture? And does sinking the terrain ~0.2 m under the road deck actually clear the carriageway on cross-slopes? | Decides whether `P3-10` ends after its cheap half or grows an image-decode stage and a **Pillow** dependency. The z-fighting half is not a preference — get it wrong and the ground fights every road in the region | `P3-10` | 🟡 **Open — raised 2026-08-01** by the ground/colour evaluation |
| Q21 | **Should level −1 carriageway be drawn at all?** 15 edges, 5,010 m, **11.6% of the region's carriageway area**, ribboned under the terrain where nothing can see it and nobody can drive it — and solid since collision shipped. `P2-7` cannot improve their height: they are a void, so there is nothing to sample, and **11 of their 30 ends are clipped at the region boundary**, so the two Cross-Harbour portals have only ~42 m of run for an 8 m descent (19%) | Triangles, collider surface and bundle bytes spent on geometry with no viewer and no driver, plus a permanent unresolvable entry in `Q13`. Against that: `P3-3`'s traffic and any Phase 4 work want the edges to *exist*, and drawing is not the same as existing — `roadgraph.json` would keep all 15 either way | `P2-7` | 🟡 **Open — raised 2026-08-01** by `P2-7`'s classification, then sharpened by the user's guess that the portals sit outside the region |
| Q23 | **Width is keyed on the edge, but a road becomes a bridge partway along one.** `elevation_level` is an attribute of a whole edge, so the 16 level-0 ends `P2-7` lifted onto their ramps are drawn at the full at-grade widening while sitting on the deck: **1,070 m of level-0 centreline across 28 edges, every metre of it widened**, worst at the `WAN CHAI INTERCHANGE` approaches and `HUNG HING ROAD FLYOVER`. The fix is a **per-station** half-width, which needs a per-vertex "on structure" signal only `roads.py` can produce — `surface.py` reads the graph alone, and `y` cannot stand in for it because `ground: terrain` puts an at-grade hill road at 49 m | Visible from the driver's seat and reported from it: the carriageway climbs onto a bridge at full width, then snaps narrow at an invisible boundary. It also blocks `Q22` from being measured honestly, since the two defects overlap on the same ramps | `P2-7` follow-up | 🔴 **Open — raised 2026-08-02** by the user's re-drive, then measured |
| Q22 | **10.2% of off-grade carriageway still hangs past its structure**, after narrowing took it from 20.1%. No width rule reaches the rest: the causes are that a single-lane ramp is drawn at the two-lane default, that a source centreline is not always centred on the deck it runs along, and that `P2-1` decimates `INFRASTRUCTURE` on a 0.5 m cell so the deck's own edge is not where the survey put it | Cosmetic today, because nothing off-grade is drivable. It stops being cosmetic in Phase 4: opening the elevated network puts a player on a ribbon whose outer metre has nothing under it, and a wheel that leaves the deck finds air rather than a parapet | Phase 4 | 🟡 **Open — raised 2026-08-02** by the width fix, which halved the problem and could not touch the remainder |

### Q18 — deliberately asked in the order that might avoid answering it

**Prior art points at stopping after the first half.** *Art of Rally* ships flat-shaded untextured
terrain as its **finished** look, not as a placeholder. That is evidence, not proof — it is open
countryside where large flat colour fields have room to breathe, and Wan Chai is dense urban. What
it buys is an order of investigation: if the first pass reads dead, tune the palette before reaching
for the classifier and the Pillow dependency behind it.

`P3-10` ships flat-coloured decimated terrain first and looks at it. The classification pass —
sample the 45 MPix source JPEG per triangle, snap to a land-cover palette, put the class in
`mesh.collapse`'s cluster key so boundaries stay crisp — is real work with a new dependency behind
it, and the flat version is the screenshot that says whether it is needed. If flat reads fine, the
question closes without the code ever being written.

The second half is not optional and not a matter of taste. `roads.py` places the level-0 ribbon at
`terrain + 0.0`, so ground and carriageway are **coplanar by construction** and will z-fight across
the whole network. The 0.15 m kerb riser and 0.5 m lip that `P1-4` already draws are what a sunken
terrain tucks under, and ~0.2 m is a guess until it is driven. Measure it on a cross-sloped street
before measuring anything else.

### Q16 — how much of the bundle one region costs, measured rather than summed

`export.py` reports what the *manifest* names: the three documents plus every path in
`tiles[].lods` — **199 files and 102.6 MB** of source for Wan Chai, against `ARCHITECTURE.md`'s
200 MB mobile bundle budget. That was the figure this question opened on, and it is not the
bundle figure. See the measurement below.

| Part | Size |
|---|---|
| LOD0 tiles (65) | 74.7 MB |
| LOD1 tiles (65) | 17.9 MB |
| LOD2 tiles (65) | 7.8 MB |
| `roads.glb` | 1.5 MB |
| `roadgraph.json` | 0.65 MB |
| `city.json`, `fares.json` | 0.04 MB |

⚠️ **Source bytes are not bundle bytes. `P1-7` measured the real thing, and both numbers above are
wrong in opposite directions.**

Godot ships what is in `.godot/imported/`, never the source file. A `.glb` becomes a compact binary
`.scn`; a `.jpg` becomes a `.ctex` whose size depends on the import mode and can be far *larger*
than the source. Measured on a real `Web Demo` export:

| | Source on disk | In the PCK |
|---|---|---|
| 195 tile scenes | 100.4 MB | **48 MB** |
| `roads.glb` | 1.5 MB | 1.1 MB |
| **Whole export (`index.pck`)** | — | **56.4 MB** |

So the region costs **56.4 MB, not 102.6 MB** — Godot's `.scn` is roughly half its glTF source.

The other direction was worse. `game/assets/generated/` also held **120 MB of `P1-2t` terrain
evaluation** referenced by no scene, script, tool or manifest, and `export_presets.cfg` uses
`export_filter="all_resources"` with an empty `exclude_filter`, so it shipped. Two of those files
were byte-identical copies of the same aerial JPEG — one of them not even in `terrain/` — and each
imported at `compress/mode=0` (lossless) to a **79 MB** `.ctex`, *expanding* 39 MB of source into
79 MB of bundle. The measured PCK was **222.8 MB, over budget on its own**, before the 38.8 MB of
wasm beside it.

Deleting the two duplicates took the PCK from **222.8 MB to 56.4 MB — 166.3 MB measured**, with the
city still fully present (195 tile scenes verified in the export).

The terrain GLB then moved to `etl/out/<city>/<region>/terrain/`, where `build_terrain` writes it,
taking the PCK to **51.8 MB**. An `export_presets.cfg` exclusion was considered and rejected:
`assets/generated/` is contractually what the manifest names and `sync_generated.sh` now enforces
that, so the file would be swept regardless — the exclusion would have been a second rule losing a
fight with the first. Copy it back temporarily when the visual judgement is finally made.

> ⚠️ That last move saved **4.6 MB, not the ~48 MB its 47.9 MB source suggests** — the embedded
> texture does not survive glTF import, so the mesh lands as a 4.4 MB `.scn`. The estimate was made
> by summing source bytes *in the same session that wrote the rule against doing so*. The rule is
> not a slogan: measure the PCK.

Three lessons. Bundle size must be **measured from a PCK**, never summed from source files. "Nothing
references it" was a property nothing in the project checked, because every check starts from the
manifest and the manifest had forgotten these — `tools/sync_generated.sh` now sweeps the whole asset
tree, not `tiles/` alone. And a lossless-mode texture import is a bundle trap that grows silently.

Raised now rather than at `P2-6` because it is cheap to note and expensive to discover late — but
deliberately **not** acted on, because the answer depends on decisions that are not made yet. Three
plausible ones, and they are not exclusive:

- **Not every tier ships.** LOD0 is 73% of the bundle and is only ever drawn for the handful of
  tiles nearest the camera. If `P2-1` finds LOD1 acceptable at the closest range in a street canyon
  where nothing is visible past a block anyway, the bundle drops to 28 MB and the question closes.

  ⚠️ **Narrowed 2026-08-01 by `P2-1`, and then half-answered the same day.**
  Matched pairs at Hennessy Road and at the Gloucester Road flyover, same camera, one variable. In
  the canyon LOD1 is very nearly indistinguishable from LOD0: the facades read the same, the street
  reads the same, and it costs 478,076 primitives against 629,975. **For buildings the answer is
  yes.** But the elevated road structures and the footbridge canopies come apart — crisp thin slabs
  at LOD0 become warped dark slivers at LOD1, because `INFRASTRUCTURE` geometry is long and thin and
  does not survive vertex-cell decimation the way an extruded building block does. So dropping LOD0
  wholesale would have cost the flyovers their silhouette, and the flyovers are the most
  recognisable thing in the region after the harbour.

  **That half is now fixed** — `class_lod_cell_sizes_m` holds infrastructure at a 0.5 m cell, and
  the flyover reads correctly at LOD1 for +3.6% of visible triangles. See the decision log entry
  above and the before/after in `build/lod-review/`. What remains open is the actual `Q16` question:
  whether LOD0 ships at all. LOD1 is now good enough at closest range for *both* mesh classes, so
  the bundle case is stronger than it was — 65 tiles of LOD0 are 74.7 MB of the 105.5 MB shipped —
  but dropping a tier is a product decision and still the user's call at the `P2-1` review.
- **LOD0 gets cheaper.** It is currently an exact weld — 989k triangles across the region, no
  simplification at all. A 0.5 m cell would sit between the current LOD0 and LOD1.
- **The budget was for the wrong thing.** 200 MB is the iOS cellular download threshold, not a
  memory limit, and it applies to the whole app rather than to one region.

What makes this a question rather than a task is that the second region is the business case. One
region at 102.6 MB means the second cannot ship in the same download, and that is a product
decision — on-demand resources, a smaller free slice, or fewer tiers — not an ETL one.

### Q14 and Q15 — both are "the source cannot say", not "we did not look"

Neither is a bug and neither is currently visible. They are recorded because both will be
*invisible* right up until something depends on them.

`Q14` is a contract gap: there is no field for opening hours in `fares.json` and no consumer for
one, so parsing `(1200-0600 daily)` would have been building a feature nothing asked for. The
information is not lost — it is in the fetched source, and adding it later is a schema bump plus
a parser, not a re-derivation.

`Q15` is a source limit. The taxi datasets publish lon/lat and nothing else, so there is no height
to disambiguate with; any level-preference rule would be a guess dressed as logic. The measurement
that makes this safe to defer is that the runner-up margin is at least 4.28 m and every winner in
the region is at level 0. It becomes real in a region with stands under an elevated road — and
`Q13` is the same underlying fact, that this project's vertical information about roads is
authored rather than surveyed.

### Q13 — the flyovers are floating slabs

`elevation_levels` maps a grade-separation level to a constant height, so every edge on a level sits
at that height for its whole length and **no edge ever ramps**. `P1-3` measured this as a 4.21 m
median for level 0 and cross-checked it against the building bases; what nobody measured until
`P1-4` had to draw it is what happens *between* levels. Nothing does. The step is exactly the deck
height, 36 times over.

The surface stage does the only honest thing available to it — it caps junctions per level, so a
street and the tunnel roof 8 m below it are two separate pieces of tarmac rather than one welded
through a vertical wall. That is correct output for an incorrect height model.

**Why it is not fixed here.** A ramp is not a mesh problem, it is a graph-height problem, and the
source carries no Z at all — every height in this pipeline is authored or sampled. Blending each
off-grade edge to grade over its own length was measured: median gradient 3.9%, but **10 of the 39
off-grade edge ends exceed 12% and the worst is 29%**, because the ramps are chains of short
connector edges (`WAN CHAI INTERCHANGE` arrives in 21 m) rather than single features. Doing it
properly means relaxing heights across the whole graph, which is its own task with its own probes.

**Why it is not urgent.** The player drives Wan Chai's streets. The elevated network being
unreachable is a missing feature, not a broken one, and arguably the right first slice — but it must
be decided rather than inherited, and `P2-2`'s nearest-edge queries will hand the car onto a flyover
if nothing stops them.

⚠️ **Narrowed 2026-07-31: "the source carries no Z" is true of the road network and false of the map
sheets.** `INFRASTRUCTURE` holds the elevated structures *including their ramps*, it is already
parsed and already rendered, and sampling it with `terrain.HeightField` covers **45/45 elevated
edges at a 3.01% median grade** — better than the blend measured above on every count. It does not
close the step: 15 of 22 resolvable flyover junctions still exceed 0.5 m, and the 5 tunnel nodes
have no structure to sample because a tunnel is a void. So `P2-2` takes the street-level slice, and
the full fix keeps a measured starting point instead of an open question. Numbers, artefacts and
the reasoning are in the decision log.

**Narrowed 2026-07-31: `Q13` does not block the cross-harbour fare.** The user's objection to `P1-5`
was the obvious one — the region is Wan Chai, so there is no other side of the harbour to deliver
anyone to. Checked against the graph, and the design already answers it: `docs/DATA_SOURCES.md`
specifies a cross-harbour fare that *terminates at the tunnel approach* rather than crossing, and
that approach is in the region **at street level**. Three `CROSS HARBOUR TUNNEL` edges (`e219`,
`e344`, `e465`) sit at elevation level 0 and join ordinary streets through `WAN CHAI INTERCHANGE`
at nodes 90, 240 and 333. You can drive there from Hennessy Road today.

The 8 m step is at nodes 250 and 430 — the portals themselves, where the approach dives to level
−1, and only 81 m of tunnel is inside the region at all before the harbour boundary clips it. So
`Q13` costs the ability to drive *into* the tunnel, which the fare design never asked for. Straight-
line distance from the six cross-harbour stands to the portal runs **191 m to 1,044 m**, which is a
usable spread of fare lengths — though 191 m (Jaffe Road) is barely a trip, and `P3-1` will need
either a minimum length or a different destination for the near ones.

What this does **not** settle is whether stopping at a portal *feels* like completing a cross-
harbour fare. That is a `P3-9` question, not a geometry one.

### Q12 — resolved: **the source agrees with the street**

User verdict 2026-07-30, after flying the road-graph preview: **Jaffe Road is eastbound**, exactly
as `roadgraph.json` says. `P1-3`'s last acceptance criterion is met, and the task is closed.

**The useful part is what this licenses downstream.** Direction reaches the graph through
`TRAVEL_DIRECTION` and the digitised vertex order, and there was no independent way to know whether
that chain — or the publisher's own survey — matched the road. It does. So `P3-3` can route traffic
on the source's directions rather than treating them as a starting guess to be hand-corrected
street by street, which is a materially different amount of work for Causeway Bay and every city
after it. A disagreement here would have been the more interesting finding and much the worse one.

Confirmed by eye rather than by test on purpose. `PLAN.md` asked for a check "**against reality**",
and the only authority on that is the road; `game/scripts/city/road_preview.gd` exists to make it a
ten-second question rather than a survey.

What the data said, kept for the record and because `P1-4` needs the Lockhart row:

| Street | What `roadgraph.json` says | Where |
|---|---|---|
| **Jaffe Road** | **One-way eastbound.** 7 of its 9 edges run east; the 2 that run west are at the far eastern end past Paterson Street, and one of those is two-way | 22.27858 N 114.17213 E → 22.28113 N 114.18377 E |
| **Lockhart Road** | **Two-way**, carried as *opposed one-way carriageways* rather than as two-way edges — three such pairs, **2.73 / 3.07 / 3.41 m** apart. 8 of its 26 edges are marked two-way outright | 22.27812 N 114.17171 E → 22.28069 N 114.18470 E |
| Gloucester Road | One-way throughout, both carriageways present | — |

The Lockhart finding is the one worth a second look: it is the documented "dual carriageways are
modelled as separate one-way segments" quirk, but tighter than the phrase suggests — the two
carriageways are **three metres apart**, which is narrow enough to look like a doubled centreline
until you measure it. It was measured: **6 opposed pairs** in the emitted graph, separations
**1.96 m to 3.85 m**. `P1-4` has to decide whether a 3 m pair becomes two ribbons or one. Treat 6
as a floor — it counts only pairs sharing *both* endpoints, and carriageways that diverge at one
end are the same pattern uncounted.

~~**Carried into `P1-4` as an open decision, not a question:** whether a 3 m opposed pair becomes two
ribbons or one.~~ **Closed 2026-07-30 by `P1-4`, and the decision turned out not to exist.** The
premise — that two ribbons leave a gap down the middle of Lockhart Road — was never checked against
the ribbon widths. It is false. At their authored 6.4 m each, five of the six pairs already overlap
by **2.71 m to 4.91 m**; the sixth (Lockhart, the widest at 6.82 m apart) leaves a 0.42 m slot at
1.0× and overlaps by **3.42 m** at the 1.6× widening the design already called for. So: two
ribbons, no merging, no pair detection, and nothing in `surface.py` knows what a dual carriageway
is. The lesson is the cheap one — the decision was framed from a separation measurement without the
width measurement that made it moot.

### Q11 — resolved: sample the terrain height field under every vertex

Opened by `P1-2`, closed by `P1-3` on the same day. `elevation_levels` was always an *offset* per
grade-separation level; what was missing was what it is an offset **from**. The answer is the
ground, and the ground is in the sheets we already download.

`pipeline/terrain.py` indexes the region's terrain triangles into a uniform grid and interpolates
a height barycentrically under each road vertex. Measured on the real region:

| | Before (`elevation_levels` from the datum) | After (from sampled ground) |
|---|---|---|
| Level 0 road height, median | 0.00 m | **4.21 m** |
| Level 1 (flyover), median | 6.00 m | 10.08 m |
| Level −1 (tunnel), median | −8.00 m | −3.53 m |
| Vertices with no terrain under them | — | **0** |

**The cross-check is the point.** `P1-2` measured the region's building bases at a median 4.29 m
by a completely separate path — glTF node matrices out of the LandsD sheets. Roads now land 8 cm
below the doorways on them, which is what a kerb is. Nothing was tuned to make those agree.

This also settles the standing question about whether the terrain earns its place in the pipeline
when it is **too expensive to render** (267 MB of texture, see the `P1-2` decision). It does: it is
the only source that knows where the ground is, and sampling costs nothing at runtime.

Chosen over the two alternatives recorded when `Q11` was opened. Sampling the nearest buildings'
bases is available without the terrain but noisy — podium bases sit above the pavement and the
maximum is 75.92 m. One authored offset per region is cheapest and wrong the moment the road climbs
toward Kennedy Road, since the region spans 55 m of relief.

`roads.ground: terrain | datum` in city config, because a city whose sources carry no height field
must still be able to build.

### Q9 — resolved: the geodatabase, and every GML dropped

`RdNet_IRNP.gdb.zip` is **17.4 MB and contains all seventeen layers**; the per-layer GML
conversions of the same content total **539 MB**, `CENTERLINE.gml` alone being 486 MB because GML
spends most of its bytes on XML tags. `hong_kong.yaml` listed both while `P1-3` had not chosen a
reader. It has, so **a clean fetch is now 522 MB lighter** and `sources:` holds two entries: the
geodatabase, and the data specification PDFs that every field mapping is verified against.

The reader is **`pyogrio`**, which is GDAL/OGR shipped inside its own wheels — the thing that makes
it installable without a system GDAL, which is the platform-awkwardness that got this deferred out
of `P0-4`. It reads the geodatabase **inside its zip** through OGR's `/vsizip/`, so nothing is
unpacked. geopandas was not needed: `pipeline/gdb.py` wants coordinate arrays, and a GeoDataFrame
would add pandas on the way to the same numpy underneath.

### Q7 — resolved: the origin sits at the **north-west** corner

Surfaced by `P0-4`, resolved on the user's call 2026-07-30 and implemented.

`ARCHITECTURE.md` stated the conversion as `game_z = -(northing - origin_northing)` with the origin
at the region's **south-west** corner — putting the whole region at Z ≤ 0 — then two sections later
showed a `bounds_game` example running to `[1650, 220, 900]`, i.e. **positive** Z. Both could not be
true.

**The two halves were never equally free, which is what made the decision easy.** The sign of Z is
forced by handedness: Godot is right-handed and Y-up, so rotating `+X` by 90° counter-clockwise
about `+Y` lands on `−Z`. If east is `+X`, north **must** be `−Z` or the city comes out mirrored.
Only *where zero sits* was ever a choice, and it is a pure translation — nothing about the geometry,
the import, or the precision changes with it.

**North-west chosen** because the Z sign being forced means anchoring at the northern edge is the
only way to keep the region in the positive quadrant. Measured after the change:

| Corner | game X | game Z |
|---|---|---|
| NW (origin) | 0.64 | 0.97 |
| SE (far) | 1649.62 | 886.88 |

Tile indices at 150 m now run `(0,0)` to `(10,5)` instead of `(0,0)` to `(10,-5)` — natural numbers,
row 0 at the north, as in a raster or a map sheet. The rejected alternative, a south-west origin, is
the GIS bbox convention and is defensible; it loses on the fact that negative tile indices are a
papercut paid every time anyone writes a filename, a `Vector2i`, or a debug print. The tie-breaker
was that the `bounds_game` example already showed positive Z, which reads as the formula section
having drifted rather than two deliberate choices colliding.

Origin northing is now **ceiled** where easting is floored — rounding outward, so every offset
inside the region stays non-negative.

**Caveat worth carrying into `P1-2`:** non-negativity is a property of the *region*, not of the
source data. `fetch.py` downloads every sheet that intersects the region, so the geometry on disk
runs past all four edges, and anything north or west of the region still produces a negative
coordinate. Clipping to the region bbox before indexing is therefore part of the data contract
rather than an optimisation. Recorded in `ARCHITECTURE.md`.

**Exposed a second question, `Q10`:** the origin is per *region*. Two regions cannot be stitched
into one continuous map unless they share one. Not urgent, same `city.json` schema, and settling it
before `P1-6` is much cheaper than after.

### Q10 — resolved: **both**, a local origin plus a recorded `city_offset`

Opened by `Q7`'s resolution, settled on the user's call the same day and implemented in
`config.py`. The answer was not either/or.

**The problem.** `GameTransform` is built from a *region's* bounds, so Wan Chai's origin is Wan
Chai's north-west corner — and Central's would be Central's. Both regions would start at zero, so
`(100, 0, 100)` would name a place in each and the two could not be loaded together.

**Why a single city-wide origin was not the answer.** Hong Kong spans **62.9 km × 45.4 km**, which
would put Wan Chai ~38 km out. Float32 spacing exceeds 1 mm above 2¹⁴ = 16,384 m:

| Distance from origin | float32 spacing |
|---|---|
| 8 km | 0.49 mm |
| 16 km | 0.98 mm |
| 32 km | 1.95 mm |
| **38 km (Wan Chai)** | **3.91 mm** |

Invisible on a building; awkward on a vehicle. Godot stores `Transform3D` as float32, so the car's
own position would quantise to ~4 mm against a measured suspension sag of 50.6 mm — about 8% of it.
That is the classic large-world jitter problem, and it would have been self-inflicted.

**What was done instead.** Regions keep their local origins, and `city.json` carries a
`city_offset` — the translation into a city-wide frame anchored on the city's declared bounds:

```
city_space = region_local + city_offset      # Wan Chai: (38379.0, 0.0, 32826.0)
```

A region loaded alone ignores it. A build that streams neighbours applies it as a translation. This
is the floating-origin approach: local precision where the player is, global placement when needed.

**The constraint that makes it work, and the one worth guarding:** the city's `bounds` are
**declared in config, never derived from the regions that exist**. A frame computed from "the
regions so far" would move every time one was added, silently relocating every region already
published against the old value. `hong_kong.yaml` therefore declares deliberately generous
territory bounds with a do-not-change warning, `config.py` rejects any region falling outside them,
and a test asserts the city frame is unchanged by adding a region. Mutation-tested: switching
`city_transform` to derive from region bounds fails that test.

Shipping in `schema_version: 1` rather than arriving later as a migration, which is the whole
reason for settling it before `P1-6`.

### Q8 — `P0-5` did not retire the risk it existed to retire

`PLAN.md` justified `P0-5` as answering "is this a game?" *before* any ETL investment, on the
reasoning that "if the driving isn't fun with boxes, real geometry will not save it." The drive test
established that the driving is **not bad** — no blocking handling problem — but the user's verdict
is that fun is not assessable without either the real Hong Kong scene or the fare loop. The premise
that a grey box could answer the question was wrong.

Two candidate answers, both cheaper than waiting for the Phase 3 gate:

1. **Real geometry first** — proceed through Phase 1 as planned. Answers "does it read as Hong
   Kong, and is driving *this city* interesting?" Multi-week, but every hour of it is on the
   critical path regardless.
2. **A throwaway fare loop on the existing grey box** — four hand-placed markers, a timer, a
   destination arrow. Roughly a day, answers "is the core loop interesting?" independently of
   geometry, and is a rehearsal for `P3-1`. But it is throwaway work, and `GAME_DESIGN.md` ties the
   loop's appeal to recognisable places, which a grey box cannot supply.

### Q1 — resolved in full

**No true Z coordinates, but grade separation is encoded as an integer `ELEVATION` attribute.**
Verified against live data: `CENTERLINE.gfs` declares 2D LineString, every `gml:posList` carries
`srsDimension="2"`, and `ELEVATION` takes values 0 (86.5%), 1 (2.0%), and 2 (11.5%) across samples
spanning the full 486 MB file.

**The Wan Chai region choice holds. No fallback to Tsim Sha Tsui.** Map `ELEVATION` to authored
deck heights in city config; only allow junctions between edges at matching levels. Full detail in
`docs/DATA_SOURCES.md`.

**Bonus:** bilingual street names (`STREET_ENAME` / `STREET_CNAME`) ship in the source — one less
thing to hand-author. `-99` and `–９９` are null sentinels.

### Q4 — resolved

**iOS: A13 (iPhone SE 2nd gen / iPhone 11). Android: Adreno 618, Vulkan 1.1, 4 GB RAM.**
Reference Android handsets: Pixel 4a (SD730G), Redmi Note 9 Pro (SD720G), Galaxy A52 (SD720G).

The two floors are separate decisions and only one sets the budget — see the decision log entry
below.

---

## Decision log

### 2026-08-02 — `P2-7` review, second finding: **structure is drawn at its authored width**

The user's second observation from the step-8 drive: *"the elevated part of road should not widen
because the bridges are not widen and has guardrails, which make road widening pointless and
confusing"*. Evaluated and implemented — `widen_by_elevation_level: {1: 1.0}` in `roads.surface:`,
and `widen_for` gains an `elevation_level` argument.

**The level rule wins outright over the speed rule**, which is the only real design decision here.
They are different kinds of claim: the speed table is a *preference* about how much room a fast road
wants, while a level rule is a *statement about what the carriageway is sitting on*. The Wan Chai
Interchange matches both — signed at 70 and up on structure — and a combined or speed-first reading
would still draw it 1.3× and hang it over the parapet.

The two arguments the widening rests on are both **at-grade** arguments, and neither survives the
trip onto a deck:

| The argument at grade | Why it does not transfer |
|---|---|
| A gap between opposed carriageways leaves a slot showing the void where unshipped terrain would be | On a flyover the slot shows the **deck**, which `P2-7` put under the ribbon and which the tiles *do* ship |
| Real street widths are unforgiving at arcade speeds | A viaduct is parapet-to-parapet in the real city, and the guardrail reads as the edge whatever the asphalt does |

Measured on Wan Chai, ribbon sampled on a 2.0 × 0.5 m grid across its **full drawn width**, a cell
counted as supported when `INFRASTRUCTURE` has an upward face within ±1.0 m of the drawn surface:

| | before | after |
|---|---|---|
| off-grade carriageway hanging in air | 20.1% | **10.2%** |
| off-grade drawn area | 67,369 m² | **46,783 m²** (−31%) |
| … as a share of all drawn carriageway | 11.2% | **8.0%** |

`roadgraph.json` is **byte-identical** across the change (same MD5), which is `RoadSurface`'s own
docstring holding: *"A change here never changes `roadgraph.json`."* No schema bump — `carriageway`
half-widths change value, not shape, and step 6 wrote the rule down: bump where a consumer would be
wrong to keep its old interpretation. A consumer that reads the table stays right; one that *derived*
a width from the graph and a factor was already wrong.

**What got worse, stated rather than buried.** `deck_error` was expected to be unchanged, because it
samples centrelines and a centreline is inside its ribbon at any width. That reasoning was wrong: it
attributes each station to the nearest *drawn* surface, and the junction trim is a multiple of the
widest half-width at a node, so narrowing moved where the ribbon ends and the cap begins.

| | before | after |
|---|---|---|
| \|error\| p90 | 0.095 m | **0.094 m** |
| within ±0.10 m | 92.3% | **92.7%** |
| below the deck by over 0.10 m | 6.9% | **6.6%** |
| stations unmatched by any drawn road | 21 | **19** |
| **deepest below the deck** | **0.30 m** | **0.48 m** (accepts 0.50) |

The distribution improved on every axis and one tail sample got 0.18 m worse. It is **one station of
3,286** — nothing else is past 0.24 m — and it sits 0.05 m from **node 275**, the `CANAL ROAD
FLYOVER` touchdown where level-1 edge 257 meets its level-0 continuation. The node is at 4.43 m
because `_node_heights` takes the smallest \|level\|, i.e. the at-grade side, while the ramp's tile
geometry there still reads 4.71 m. That disagreement is the `Q13` residual already on record —
`INFRASTRUCTURE` stops being modelled where a ramp reaches grade — and narrowing did not create it,
it changed which drawn surface covers that last station and so exposed it. **0.48 against a 0.50 gate
is a thin margin and is named as a risk**, not a pass to be quoted.

The surface also grew **34,920 → 35,039 triangles**, which is the same mechanism read from the other
end: ends clamped by edge length went 210 → 208, so slightly less trim, so the ribbons keep a little
more of their resampled polyline.

Opens `Q22`: 10.2% still hangs in air, and no width rule reaches it.

**The re-drive found the rule's own boundary, and it is a real one.** The user: *"strange that the
road dont stop widen where the bridge structure and guardrail already start, but it is elevated
first into the bridge until widening stop. ideally it should stop widen where it meets any bridge
structure"*. Correct, and it is the caveat about touchdown nodes turning out to be bigger than it
was written. `elevation_level` is an attribute of an **edge**, but a road does not become a bridge
at an edge boundary — `P2-7` itself lifted **16 level-0 ends onto their ramp**, so those stations
are on the deck while their edge is still labelled level 0 and keeps the full 1.6×.

Measured with the same probe, counting a level-0 station as on structure when `INFRASTRUCTURE` has
an upward face within ±1.0 m of the drawn surface: **1,070 m of level-0 centreline sits on structure,
and every metre of it is widened**, across **28 edges** — worst are the `WAN CHAI INTERCHANGE`
approaches (94 m, 94 m, 78 m …) and `HUNG HING ROAD FLYOVER` (72 m). Not a tail: it is all of it.

The cheap fix was checked and does not exist. `surface.py` reads `roadgraph.json` and nothing else,
and the published `y` cannot identify structure on its own — `roads.ground` is `terrain`, so a level-0
road climbing the Mid-Levels escarpment reaches 49 m while at grade, against a level-0 median of
4.22 m. Only `roads.py` knows which stations it lifted, at the point it lifts them. So the fix is a
**per-station width** fed by a per-vertex signal the graph does not yet carry — a `schema_version`
bump on both sides under hard rule 5. Opened as `Q23` and deliberately not folded into this commit:
this one is complete and measured, and a schema change is not a review fix.

### 2026-08-01 — One owner for the debug chrome, one key, and **off by default**

`DebugHud` (`scripts/ui/debug_hud.gd`) is a new autoload that owns every dev readout in the project.
It exists because three scripts were each deciding independently what to draw on the screen — the
frame counter, `road_graph_overlay.gd`'s text block at a hardcoded `(16, 96)`, and that script's
chevrons — and a fourth would have been a fourth offset picked by eye. Overlays now register a label
with the HUD and ask it what to show; `F3` cycles `off → minimal → full`, and `--debug-view=` sets
where a run starts.

**The default is off, in every build**, which is a change: a debug build previously always had the
counter, and `city_drive.tscn` always had the graph readout and chevrons. Two reasons, in order.
First, every screenshot anyone judged Wan Chai from had a five-line text block over it, including the
ones about how the city looks. Second, measured on the standard driver run at 2.0 s:

| View | Draw calls | Against the <150 budget |
|---|---|---|
| off | 19 | — |
| minimal | 27 | +8 |
| full | 38 | **+19** |

Debug text was costing half as many draw calls as the entire city — text with an outline does not
batch the way a flat-shaded mesh does. Affordable, but not something to pay for unasked.

**`drive.sh` defaults to `minimal` instead**, which is the one place the reasoning inverts: a
scripted run is somebody debugging, and a screenshot that cannot say where it was taken cannot be
acted on. The position block answers that in two lines — engine metres, **and** the EPSG:2326 grid
reference via a new `CityManifest.to_grid`, so a suspicious frame is checkable against the ETL's own
source data rather than only against another frame. It reports the camera when there is no car,
which is what makes a `--camera=` preview shot self-documenting.

Three smaller calls, recorded because each has a trap behind it:

- **The toggle is a raw key, not an action.** `free_look_camera.gd` set that precedent and the
  reason holds: `[input]` is the *shipped* map. The cost is that `drive.sh --hold=` cannot press it,
  so the flag is not a convenience — it is the only route a scripted run has.
- **`--debug-view` had to be taught to `driver.gd`,** which fails on unknown arguments by design.
  The autoload reads the command line itself, and reads **both** arg lists: Godot splits at `--`,
  and `fps_counter.gd`'s old `--fps` check looked only at the engine's half, so it would never have
  fired from `drive.sh` at all.
- **Headless parks the HUD whatever the flag says.** Nothing draws there, and every `check.sh` tool
  runs headless — the overlay would only cost them a tree walk and a second parse of `city.json`.
- **`VehicleController` now joins a `vehicle` group** and answers `first_in(tree)`. Two dev overlays
  were each walking the whole tree to find the car, and the HUD repeats its search for as long as it
  comes back empty — which in a preview scene, where a car can never appear, is for ever. The group
  makes it O(1). It is the project's first use of a node group.

Font sizes are constants in the script rather than a `.tres`, which is a deliberate reading of hard
rule 4: tuning values are *gameplay* values, balanced by someone who should not need a code change.
Nothing about dev chrome is balanced. The position block's 40 px is set by what a vision model can
still read after a 1920-wide screenshot is downscaled, which is now the most common reader.

### 2026-08-02 — `P2-7` step 8: the drive found what the measurements could not — two coincident surfaces

**The user drove the ramp and it works** — *"nice ramp"* — **and reported it "a little bumpy where the
white and grey mix together".** The screenshot shows the white tile deck sawtoothing through the dark
carriageway along the ramp.

That is a defect `P2-7` **introduced**, and no number in this task could have caught it. Before, the
ribbon floated a median 1.31 m clear of the deck, so the two surfaces never met. Landing the ribbon
*on* the deck — the entire point — made them coincident, and coincident surfaces interleave: visually
as that sawtooth, physically as wheels riding whichever collider happens to be higher.

The cause is not the sampling. Against the **source sheets** the ribbon is exact, median −0.000 m.
`P2-1` decimates `INFRASTRUCTURE` on a 0.5 m cell, and that collapse lifts the shipped deck a median
**+0.041 m**, p99 **0.163 m**, max **0.339 m** above where it was sampled. The road is right and the
deck the player meets moved.

#### `deck.clearance_m: 0.20`, which is a layer rather than a fudge

A real road is a wearing course laid **on** a structural deck, so a clearance is the right shape of
answer. Its *size* is set by the decimation rather than by paving practice — 5 to 10 cm would be
realistic, 0.20 m is what the 0.5 m cell forces:

| clearance | still poking through, LOD0 | LOD1 |
|---|---|---|
| 0.15 m | 1.31% | 8.0% |
| **0.20 m** | **0.37%** | **5.4%** |
| 0.25 m | 0.06% | 2.4% |

User's call, taken 2026-08-02: **0.20 m**. A finer LOD0 cell would let it come back down.

Applied only where the deck is what decides the height — the sampled branch and the lifted level-0
branch — and never to the flat-offset fallback, which is not on a deck at all. `tools/deck_error.py`
**subtracts** it, so the acceptance metric still measures error rather than counting a deliberate
layer as one.

#### Fixing it exposed a measurement bug of its own

`deepest below the deck` jumped 0.34 → 0.54 m, which looked like the clearance had made something
worse. It had not: at the Wan Chai Interchange the tool was attributing a **level-0 junction cap** —
which carries no clearance — to a level-1 edge 0.45 m away, inside a 1.0 m attribution window. The
clearance simply widened a mis-attribution that was already there.

The window was sized by caution rather than by what it must tolerate. A ribbon is extruded from the
polyline it is compared against, so a correctly attributed surface differs only by mitre and trim
interpolation — centimetres. **0.40 m** is still nearly three kerb heights, removes the
mis-attribution, and costs no coverage at all.

#### Where it landed

| measured against shipped LOD0 tiles | before | after |
|---|---|---|
| **\|error\| p90** | 4.107 m | **0.095 m** *(accepts 0.50)* |
| deepest into the structure | 4.67 m | **0.30 m** *(accepts 0.50)* |
| within ±0.10 m | 1.5% | **92.3%** |
| below the deck by over 0.10 m | 66.1% | **6.9%** |
| measured | 96.7% | **96.9%** |

The `before` column is graded with `--clearance-m 0`, because that bundle was built before the key
existed and subtracting a layer its geometry never had would shift every figure by 0.20 m. That
override exists for exactly this comparison. It still reproduces the recorded **4.19 m** baseline and
its 66% below-deck figure, which is what makes the `after` column worth believing.

The median step at the 36 level-change nodes is now **0.19 m** rather than 0.04 m, and 24 of 36 sit
inside 0.5 m rather than 26 — the clearance raises the off-grade side of every mixed node by 0.20 m,
which is the cost of the fix and is recorded rather than hidden.

### 2026-08-02 — `P2-7` step 8a: everything mechanical is verified; the drive is the last gate

Clean rebuild from source, then every check the project has:

| Check | Result |
|---|---|
| Full pipeline, `etl/out` deleted first | all six stages, **3.0 s** |
| `ruff check .` / `ruff format --check .` from root | clean, 42 files |
| `pytest` from `etl/` | **426 passed** |
| `tools/check.sh` | **exit 0** — format, import, GDScript warnings, four verify tools |
| `tools/deck_error.py` | **exit 0** — \|error\| p90 0.095 m, 96.9% measured |
| Web export | built; `project.godot` and `export_presets.cfg` restored and `git diff --exit-code` **verified** |

`verify_road_graph` still reports **737 drivable edges of 797**, which is the scope note holding:
nothing became drivable, and `nearest_edge` refuses all 60 off-grade edges exactly as `P2-2`
accepted.

**What is left is the review drive**, and it is the one gate no measurement replaces — `PLAN.md`
asks *"does the elevated road now sit where the structure says it does?"*, on a web build, at the
Tonnochy Road approach and the Wan Chai Interchange. The numbers say yes at 0.095 m; whether it
*reads* right from the driver's seat is the user's call, and the `P2-5` drive is the precedent for
why that is asked separately — it found a defect every internal number had passed.

### 2026-08-02 — `P2-7` step 7: graded against the shipped tiles, and it **passes** — after the tool was wrong three times

`tools/deck_error.py` measures the drawn carriageway against the structure in the **shipped tile
GLBs**. Nothing it uses is shared with the code it grades: geometry from the decimated tiles rather
than the source sheets, deck faces by **winding** rather than slab clustering, structure by **vertex
colour** rather than sheet sub-directory, and its own point-in-triangle query.

| measured against shipped LOD0 tiles | before | after |
|---|---|---|
| median | −1.311 m | **−0.041 m** |
| p10 / p90 | −2.93 / +3.66 | **−0.09 / +0.00** |
| **\|error\| p90** | **4.131 m** | **0.095 m** *(accepts 0.50)* |
| deepest into the structure | 4.67 m | **0.34 m** *(accepts 0.50)* |
| within ±0.10 m | 1.5% | **92.3%** |
| below the deck by over 0.10 m | 66.0% | **7.0%** |
| coverage | 97.6% | 97.4% |

**`P2-7`'s acceptance is met.** The `before` column is the load-bearing one: it reads **4.131 m**
where the recorded baseline — measured months of reasoning ago by dense sampling of the *source
sheets* — is **4.19 m**, and reproduces its 66% below-deck figure at **66.0%**. Two methods
sharing no code agreeing to 1.4% and to a tenth of a point is what makes the `after` column
worth believing.

The `before` bundle was built by rerunning roads, surface and export with `roads.deck` set to `None`
into a scratch tree, so both columns are real pipeline output graded by one tool.

#### The tool was wrong three times, and each error flattered or damned by metres

⚠️ **This is the finding worth keeping.** An acceptance tool is the last thing anyone checks, and
every one of these produced a *plausible table*.

| Wrong | Read | Why |
|---|---|---|
| Matched the structure colour exactly | 428 of 434,149 triangles | `colour_for` **jitters every class**, one factor across all three channels. A class is a *ray* through its base colour, not a value |
| Kept both face windings | 1.07 m p90 | A deck's underside is as horizontal as its top, so a carriageway sunk into a deck scored against the face 1.5 m below and read as a small positive |
| Sampled the road mesh's own vertices | 1.31 m p90, 8.4 m on `CANAL ROAD FLYOVER` | `roads.glb` carries vertices **only at the carriageway edges**, and `width_m` is hand-tuned wider than the real road for playability. The drawn edges overhang the deck *by design*; the tool was measuring overhang |

The third was the instructive one. It looked exactly like a real defect — one named flyover, a
consistent 8 m, the deck separation of a double-decker. Chasing it found the source sheets and the
shipped tiles agreeing to within 0.05 m at those positions, which meant the geometry was right and the
*question* was wrong. Sampling down the centreline instead took p90 from 1.31 m to 0.095 m with no
change to the ETL at all. **Overhang is `Q19`'s question; height is `Q20`'s, and conflating them
manufactures a failure.**

#### The "0.1 m below" half of the criterion was superseded by measurement

`P2-7` restated *"no ribbon below the deck"* as *"no sample more than 0.1 m below"*. That was set
against the internal check, where the geometry is exact. It is not a threshold the shipped tiles can
resolve: measured with the carriageway held still, `P2-1`'s 0.5 m decimation of `INFRASTRUCTURE`
alone moves the deck top by **−0.041 m median** and widens |error| p90 from **0.030 m** (source
sheets) to **0.095 m** (shipped tiles). A 0.1 m gate sits under the noise floor of the surface being
measured.

So the gate is now the **deepest single intrusion**, at the same 0.5 m as the p90 criterion — *"how
far does the road ever sink into the flyover"* is what `Q20` actually asked. It reads **0.34 m**,
against 4.67 m before.

#### The review pass found a fourth way to be quietly wrong, and it was the worst one

**The tool could be made to pass by breaking the thing it grades.** A station whose drawn height was
not within `--attribute-within-m` of the graph left no trace: it was not a station, so it was not in
any denominator. The review demonstrated it — raise 35% of the elevated carriageway 30 m in the
graph and leave the mesh alone, and the tool reported |error| p90 **0.09 m**, coverage **97.6%** and
**"P2-7 acceptance met"**, exit 0. The broken third had simply stopped being measured, and every
ratio improved because of it.

A total break was already loud (no samples → exit). A *partial* one was silent, which is the
dangerous shape: a defect that makes geometry unmeasurable flatters every number computed over
what survives.

Fixed by gating the denominator, not just the ratios above it. Coverage is now **measured against
what the centrelines asked for** rather than against the survivors, it fails below 90%, and an
elevated edge that matches no drawn road at all fails outright. Re-running the injected regression
now gives *"only 58.2% of the carriageway could be measured"* and *"21 elevated edges matched no
drawn road at all"*, exit 1. The real bundle reads **96.9% measured** — 16 stations of 3,392 lost to
junction trims, 89 to structure that stops at a ramp foot.

Two more, both latent rather than live. The channel-limit guard on the colour classifier tested
`>= 255`, but `colour_for` clamps as soon as the *brightest* jittered value would exceed 255 — at a
jitter of 0.06 that is any channel over about 240, so a city colouring its structure near-white
would have been silently over-matched. And the module's independence table overclaimed: the
barycentric kernel in `Faces.heights_at` is `terrain._hits` with different names, so a sign or
inclusivity error there would be present in both and invisible to this tool. Both corrected — the
second by narrowing the claim rather than by rewriting the kernel, since the independence that
matters is the geometry source and the deck classification, not the arithmetic of a point query.

Measured while checking the classifier: the nearest **rejected** colour in the shipped tiles sits
**0.28 degrees** off the structure's own ray and is refused only for being 39% too bright. An
angular tolerance loose enough to absorb rounding would have taken it, which is why the test is an
interval on the scale factor rather than an angle.

#### The claim is bounded to the tier that collides

Everything above is **LOD0**, which is the finest shipped tier since `P2-1` dropped the exact weld —
what the player meets from 0 to 250 m, and what carries the trimesh collider. Run against **LOD1**
the same bundle reads a deepest intrusion of **0.54 m** and fails: that tier decimates
`INFRASTRUCTURE` on a 1.0 m cell instead of 0.5 m, and the extra 0.2 m is the collapse, not the
carriageway. It is a drawing artefact seen from over 250 m away, where the road is a few pixels
wide and nothing drives on it. Recorded because "the acceptance passes" is only true of the tier the
criterion is about, and the tool will say so to anyone who passes `--lod 1`.

#### What the tool still reports and does not fail on

`furthest above the deck` is **14.32 m**, unchanged from before, and it is `e425` — the `ISLAND
EASTERN CORRIDOR` stub whose every sample the terrain gate refuses, leaving it on the flat offset.
Eight stations of the 3,287 that had a deck beneath them. Recorded rather than hidden: it is the one edge `P2-7` knowingly does not
fix, and `Q13`'s remaining answer already names it.

The tool is **not** wired into `tools/check.sh`. It needs a built region under `etl/out`, which
`check.sh` does not require and should not start requiring. Run it after a build:
`.venv/bin/python tools/deck_error.py --city hong_kong --generated etl/out/hong_kong/wan_chai`.

### 2026-08-02 — `P2-7` step 6: `roadgraph.json` goes to schema 2, and only it does

`ROADGRAPH_SCHEMA` 1→2, `GeneratedRoadGraph.SCHEMA_VERSION` 1→2, and
`ARCHITECTURE.md`'s field provenance, in one commit per hard rule 5.

**The bump exists because nothing visible changed.** No field was added, removed or renamed —
`polyline.y` simply means something different: sampled from the structure the road is built on
rather than one flat offset per level. A consumer cannot tell those apart by inspection, and a diff
of the document shows only numbers moving. That is precisely the case a version number is for.

Verified the gate is live rather than decorative: hand-editing the shipped asset back to
`schema_version: 1` makes `verify_road_graph` fail with *"declares schema_version 1, this build
reads 2. Re-run the ETL and re-copy."* There is no cross-language check that the two constants
agree, and none is needed — a forgotten half fails loudly in `tools/check.sh` on the next run.

**Nothing else bumped, and that is a judgement.** `roads.glb` and `roadsurface.json` are rebuilt
from the graph so their content moves with it, but neither gains, loses or repurposes a field;
`city.json` moves only on its AABB. The rule now written into `ARCHITECTURE.md`: **bump where a
consumer would be wrong to keep its old interpretation, not wherever bytes change.**

`surface.py`'s module docstring had to be corrected too — it opened by asserting that all 36 nodes
step by a whole deck height "because `elevation_levels` is a constant offset per level and no edge
ramps between them", which was one of the three measurements its design rests on and is now false
for 26 of them. Per-level capping survives on the five tunnel portals, which is a narrower reason
than it had before, and `P4-*` is where the difference will start to matter.

### 2026-08-02 — `P2-7` steps 4 and 5: the carriageway lands on its structure, and the **fallback** turned out to be the interesting half

`roads.py` now samples. The headline numbers, on Wan Chai, measured against the built graph:

| | before | after |
|---|---|---|
| Step at the 36 mixed-level nodes, median | 6.00 m | **0.04 m** |
| …nodes stepping over 0.5 m | 36 | **10** |
| …nodes stepping over 2 m | 36 | **6** — the 5 tunnel portals and the stub, exactly what step 1 predicted |
| Off-grade ribbon vs structure, \|error\| p90 | 4.14 m | **0.02 m** |
| …worst | 6.37 m | **0.68 m** |
| …ribbon below the deck | 66% | **0%** |

⚠️ **That error column is not the acceptance measurement**, and must not be quoted as one. It
resamples the written polyline and asks the *same* `HeightField` that produced it, so it can only
show that the write-out is faithful to the sampler — the internal number, which reads near zero by
construction. The `before` column reproducing the recorded 4.19 m baseline as 4.14 m is what makes
it worth keeping: it validates the harness, not the fix. Step 7's `tools/deck_error.py` measures
against the **shipped tile GLBs** and is the number that decides `P2-7`.

ℹ️ The `surface` stage prints a median of **0.06 m** for the same 36 nodes, not 0.04. Both are
right: it measures the **trimmed ribbon** ends, which are held back from a junction, while the table
above measures the graph polyline ends. Noted because the two will keep disagreeing slightly and the
difference is a stage boundary rather than a defect.

Counters, from the stage's own report: 44 of the 45 off-grade edges took their height from the
structure over 660 added stations and 794 sampled vertices; 16 level-0 ends were lifted onto a ramp;
3 structure samples were refused for sitting under the terrain. The 45th edge is `e425`, whose every
sample the gate refuses — which is the case the gate was measured for.

#### `build_region` had to become two passes, and that is also step 5

Whether a level-0 edge sits on a ramp depends on whether its node is *also* reached by another
level, and no edge can know that until every edge has been clipped and placed. So the single pass
splits: read, clip, simplify and name the nodes; then work out the mixed set; then measure.

`_Nodes` keys on plan position and never did carry a height for identity, so the seam was already
there. What it did carry was a height recorded **on first sight** — whichever edge the source
happened to list first won. That was invisible while every edge at a level shared one flat offset,
and stops being invisible the moment two ends are sampled independently. `_node_heights` replaces it
with a stated rule: **the level nearest grade, and the highest edge end on it.** Nearest grade
because everything that reads a node position reads it for an at-grade purpose; highest for
`HeightField.sample`'s own reason, that a node below a ribbon end is a node inside the road.

#### The fallback was the bug, and it was hiding behind a correct-looking result

First run: median step 6.00 → 0.04 m, but **14** nodes still stepped, where step 1 predicted 6. Nine
of them were flyover nodes stepping the full 6.00 m, unchanged.

The cause is not in the sampler. `INFRASTRUCTURE` **stops being modelled where a ramp reaches
grade**, so the last stretch of every touchdown is uncovered — and at those 9 nodes that is
precisely the node itself: the structure query returns *nothing at all* there. Falling back to
`terrain + 6.0` rebuilt the exact cliff the task exists to remove, at the most visible place in the
region.

Measured just inside the hole, the structure sits **-0.6 to +1.1 m** of the terrain. The ramp has
arrived; what is missing is a volume nobody modelled, not a deck. So an uncovered station now takes
the deck **either side of it**, interpolated along the edge, and only an edge with no usable sample
*anywhere* falls back to the flat offset — which is `e425`, and the case the offset is still right
for. That closed 4 of the 9 outright, took the worst of the rest from 6.00 m to 1.63 m, and dropped
the worst ribbon error from 4.48 m to 0.68 m.

⚠️ **This is the third time in `P2-7` that the plan's answer was measured and replaced.** The first
was "seed the sample from the existing height", the second was "gate on minimum clearance", and this
one never appeared in any plan at all — it was found only because the node-step number came back
worse than step 1 had predicted and the gap was chased instead of rounded off. A per-station
fallback to the flat offset is the obvious implementation and it is silently wrong in exactly the
places that matter most.

#### What is left, and what it is not

| Nodes still stepping over 0.5 m | Step | Why |
|---|---|---|
| 5 tunnel portals | 8.00 m | A tunnel is a void. No height source repairs this — `Q21` asks whether they should be drawn at all |
| Node 389, `e425`'s stub | 6.00 m | The only edge with no usable structure sample anywhere |
| Node 175, `FLEMING ROAD` | **1.63 m** | Both level-1 edges are uncovered for their first 20 m, so the held deck overestimates |
| Nodes 394, 392, 30 | 0.62-0.67 m | Inside step 1's predicted ≤0.93 m for a ramp junction |

Node 175 is the one that misses step 1's prediction. Chasing it would mean extrapolating the deck's
*trend* into the hole rather than holding its value — a rule tuned to one node, on two knots, which
is the kind of unmeasured constant this project's rules exist to refuse. Recorded rather than fixed.

**Two things deliberately did not change.** Nothing became drivable: `verify_road_graph` still
reports 737 drivable edges of 797, so `nearest_edge` refuses all 60 off-grade edges exactly as
`P2-2` accepted. And `resample` **adds** stations without moving any existing vertex — restating the
line at evenly spaced stations is the obvious implementation and it silently cuts every corner
`simplify` just decided to keep, which no height measurement would ever reveal.

`surface.py` now reports the whole distribution of level steps rather than a running maximum. The
maximum is the five portals and always will be; quoting it alone would report a stage that closed 26
of these 36 as one that closed none.

Still open, in order: the `ROADGRAPH_SCHEMA` 1→2 bump with `ARCHITECTURE.md` and the GDScript
constant in one commit (step 6, hard rule 5), `tools/deck_error.py` (step 7), and the drive at the
Tonnochy Road approach and the Wan Chai Interchange (step 8).

### 2026-08-02 — `P2-7` step 3: the thresholds become config, and the gate is not a clearance

Four tuning values and a class name move into `hong_kong.yaml` under `roads.deck:` and
`buildings.structure_class`, with `DeckSampling` and the validation in `config.py`. **Nothing reads
them yet** — that is step 4. Deliberately so: it keeps the `roads.py` diff to the behaviour change
alone, and it costs one commit where the city file has inert keys.

Two of the four had no measured number, and measuring them changed one of them.

#### The terrain gate cannot be a minimum clearance

The plan called for `min_clearance_m`: reject a sample that sits too close to the ground to be a
deck. **That threshold does not exist.** Level-1 ramps genuinely touch down, so of the 645 covered
level-1 stations, 33 sit within a metre above terrain and 8 sit *below* it, by 0.54 m at worst — the
positive range is a continuous ramp-to-flyover spectrum from 0 to 15 m with no gap anywhere to put a
cut in. Any positive threshold would throw away real ramp ends to catch bad samples.

What separates is the other side, decisively:

| Sampled minus terrain | Edge |
|---|---|
| **−8.305 m**, **−8.181 m** | `e425` `ISLAND EASTERN CORRIDOR` |
| *(7.64 m of nothing)* | |
| −0.543 m and up | `e365`, `MARSH ROAD`, three `WAN CHAI INTERCHANGE` ramps — all genuine |

So the key is **`max_below_terrain_m: 1.0`** — how far *under* the ground a sample may sit and still
be a deck. It rejects exactly those two stations region-wide, which leaves `e425` with no valid
sample and so wholly on the fallback: today's behaviour, for the one edge that has no deck.

The step 0/1 entry below already framed this correctly — *"a deck cannot sit below the ground under
it"* — and the plan drifted to calling it a clearance in between. Worth recording because the drift
was silent and only re-measuring caught it.

#### `at_grade_m` is bounded by consequence, not by a gap

The 143 non-zero lift values across the region's 16 lifted level-0 edge ends run **continuously**
from 0.004 m up. There is no population boundary here either, so this one is a tolerance rather than
a discriminator, and it is bounded from both sides by what it costs instead:

- **Above:** the value *is* the residual step the lift leaves behind, so it has to stay well inside
  `P2-7`'s 0.5 m acceptance.
- **Below:** it has to clear the 0.1–0.2 m sampling wobble that makes profiles like `e401`'s
  non-monotone (`0.55, 0.44, 0.48, 0.37, 0.28, 0.33`).
- **Measured:** across 0.1–0.3 the run length moves by at most one 5 m station on 13 of the 16
  ends, so the band is flat; at 0.5 `e451` loses its lift entirely, and at 1.0 `e168` and `e520`
  do too.

**0.30 m** confirmed, as the largest value in the stable band — it propagates the lift no further
into edges that do not need it than it must.

#### Where the keys live, and the two ways they can be inert

`structure_class` sits in `buildings:` beside `terrain_class`, following that key's precedent: sheet
class names are declared there, and `roads.py` already reaches across for `terrain_class`. Unlike
`terrain_class` it must be **inside** `buildings.classes`, and that is load-checked — `P2-7` is
accepted against the *shipped* tiles, so a carriageway laid on geometry only the ETL can see would
be accurate against nothing the player meets.

That split leaves two ways to write a block that parses and can never run, and both are refused
rather than ignored, because the symptom of either is *output identical to a city that never asked
for deck sampling* — a config error shaped to survive review:

- `roads.deck` without `ground: terrain` — the gate and the fallback both measure against terrain.
- `roads.deck` without `buildings.structure_class` — thresholds with no geometry to apply them to.

Only that direction. A `structure_class` with no `deck:` block is merely unused, and refusing it
would reject a city whose output is correct.

`roads.deck` is optional throughout, so `testville` and any future city without structure keep
working untouched, exactly as `ground: datum` is framed.

#### The review pass found four more ways to be silently inert

The first draft argued hard that this block must never load in a state it cannot act on, and then
left four spellings that did exactly that. Each was reproduced against the real loader, not reasoned
about:

| Spelling | Was |
|---|---|
| `deck:` with nothing under it | Loaded as `deck=None` — indistinguishable from a city that never asked, and the natural state while commenting values out to tune |
| `resample_m: .nan` | Loaded. NaN passes `<= 0.0` **and** `< 0.0`, then makes every downstream comparison false without ever raising |
| `at_grade_m: .inf` | Loaded. The lift never stops; an infinite `slab_gap_m` merges every stacked structure into one slab |
| a fifth key beside the four | Loaded and tuned nothing. *Misspelling* one of the four was already caught by its absence; adding one was not |

All four now refuse, with a test each. `.nan` is the one worth naming: it is the only bad value that
passes a sign check *and* stays silent downstream, and this file already depends on YAML 1.1
resolving `.inf` for `height_bands`' open last band — so finiteness has to be asserted per field
rather than assumed.

The sign-checking and float-coercion the block needed was already written in `_road_surface`, so it
became a shared `_measures` helper — which also gave that path its first test, and gave both a
message naming the key and file instead of a bare `could not convert string to float`.

Verified: 370 tests pass (19 new), `ruff` clean, and the pipeline from `roads` onward leaves
`roadgraph.json` and `roadsurface.json` **byte-identical** — `city.json` moves only on its
`generated_utc` stamp.

### 2026-08-01 — `P2-7` step 2: the slab query lands in `terrain.py`, and two measured claims were wrong

`HeightField` grew a second query. `sample` is unchanged in behaviour and answers *how high is the
ground*; `sample_along` answers *which deck is this carriageway on* and needs the path, because a
station over a flyover gets the deck top, its underside, and anything stacked above. `_highest_hit`
became `_hits`, returning every hit instead of the maximum, so both queries share one routine —
which makes the terrain path identical **by construction** rather than by test.

Two regression checks, because a rewrite that merely looks equivalent would silently invalidate
every number in the step 0/1 entry below:

| Check | Result |
|---|---|
| pre-refactor `_highest_hit` vs new `sample`, 40,000 points incl. off-grid | NaN pattern identical, heights **bit-identical** |
| scratchpad `continuous_profile` vs `sample_along`, 11,392 real L0+L1 stations | **0 disagreements** |

#### Two things the step 0/1 write-up got wrong, found by re-measuring rather than by argument

⚠️ **The slab separation is far tighter than recorded.** The earlier note cited "1.7–2.2 m within a
deck against 9.2–16.4 m between stacked ones". Those are two *different* metrics — 9.2–16.4 m was
the total top-to-bottom spread at a stacked station, which includes both slabs' thickness, not the
gap between them. Measured properly, over 645 covered stations:

| Gap | Range |
|---|---|
| within one deck | 0.00 – **2.57** m |
| between stacked structures | **3.36** – 8.49 m |

So `slab_gap_m` = 3.0 sits in a **0.79 m** margin, not a 7 m one. It stays a tuning value, and a
second city must be measured rather than assumed.

⚠️ **"Single-slab stations are the majority on every edge" is false.** They are 73.1% or more on
44 of 45 elevated edges. The exception is `ISLAND EASTERN CORRIDOR`, which crosses the region on two
stations and is stacked on both — so it has no anchor at all and degrades to `sample`. That is the
same edge probe 6 flagged for sampling structure at −2 m, and it stays on the list for step 4's
terrain gate.

#### One latent defect, fixed although Wan Chai does not trigger it

The walk originally grew outward from the *first* anchor only. A station with no structure under it
settles nothing and continuity cannot cross it, so any run walled off behind such a gap fell back to
the highest hit — the flyover, which is precisely what the query exists to reject. Now every anchor
seeds both directions, which is also less code. Wan Chai has **zero** gaps strictly inside an edge's
covered span, so nothing in the region exercises it; it is guarded because the sampler will meet
other regions, and it is tested.

Also: NaN hits are now dropped in `slab_tops`. `np.sort` puts NaN last and no comparison against one
is ever true, so a single NaN would have survived as the top of the highest slab and propagated down
the rest of a path.

**Not wired in.** `roads.py` still does `sample(x, z) + deck_m`, so pipeline output is byte-identical.
Config keys are step 3.

### 2026-08-01 — `P2-7` steps 0 and 1: the 36 nodes are **all ramps**, and the height model is wrong on *both* sides of them

`PLAN.md` makes classifying the 36 mixed-level nodes `P2-7`'s first job and says to treat the answer
as the task's real finding. It is. Probes ran before any production code, in the scratchpad, against
the built graph and the cached sheets; every number below is measured.

#### The classification — and `PLAN.md`'s second hypothesis has no instances

| Kind | Count | Residual step once the deck is sampled |
|---|---|---|
| **Ramp junction** — structure already reaches grade at the node | **17** | median **0.33 m**, max **0.93 m**; 10 under 0.5 m |
| **Ramp mid-point** — the source's `ELEVATION` attribute flips partway up | **13** | median **3.09 m**, range 2.14–4.02 m |
| **Tunnel portal** — a void, so no structure and never will be | **5** | unchanged, 8.00 m |
| **No usable structure** — node 389, `e425`'s 25 m stub at the region corner | **1** | unchanged |

The deck-above-terrain margins are **bimodal with a gap between +0.93 m and +2.14 m**, so the split
is a property of the data rather than of where a threshold was put.

⚠️ **There are zero plan-coincident crossings.** `PLAN.md` framed the second hypothesis as "a
flyover passes over a street and the source joined them because they share a plan position", and the
first pass of this classification duly labelled 13 nodes that way. It was wrong, and what exposed it
was the clearance: **2.14–4.02 m is too low for a street to pass under.** Checked properly, 12 of
the 13 are **degree 2 with a level-0 edge ending and a level-1 edge starting** (node 386 is degree
3, with two level-1 edges leaving it), 11 of the 13 **share a road name across the node**, and the
structure runs continuously through: climbing +2.1 → +5.1…+7.4 m over the next 40 m on the level-1
side, and descending to grade on the level-0 side within **3.8–88.3 m**.

That is one road, split where the publisher's attribute changes, at a point **partway up the ramp**.
`ELEVATION` is an attribute of a feature, not a survey of where the road is, and nothing obliges the
flip to coincide with the touchdown. It is why those 13 look like a 6 m cliff: **both sides are
wrong, by about half a deck height each, in opposite directions.**

`_Nodes`' own docstring had this right from `P1-3` — "every one of the 36 endpoints where two levels
meet is a ramp touching down". It is now measured rather than inferred, and the refinement is that
13 of them touch down some distance *past* the node.

**A correction to `PLAN.md`'s worked example.** It cites `e318` climbing "3.70 m over 39.5 m, which
is a ramp gradient". The edge does rise +3.36 m over 39 m, but every level-1 vertex is `terrain +
6.0`, so that is the **terrain** rising under a flat ribbon, not a ramp. The ramp is real and it is
in the structure beneath: −0.02 → +5.55 m over the same 39 m. Right conclusion, coincidental
evidence.

#### The consequence: sampling only off-grade edges would **relocate** the step, not close it

At those 13 nodes the level-0 edge is itself sitting on the ramp — 2.1 to 4.0 m above terrain at the
node — and it is drawn at `terrain + 0`. Fix only the level-1 side and a 2.1–4.0 m cliff remains at
the flip point, now **mid-ramp**, where it is more visible rather than less. It is also the
likeliest literal cause of the `P2-5` drive report: *"I hit the road going up from a ramp, but the
road is not aligned to the ramp"* — driving up a physical ramp collider while the level-0 ribbon
stayed at ground level beneath it.

**User's call, taken 2026-08-01: sample level-0 edges too.** This changes at-grade drivable geometry
on 16 edge ends, in a task whose scope note says nothing becomes drivable. Nothing does — the
network stays closed, `nearest_edge` keeps refusing off-grade edges — but the surface under the car
moves, and that was not the ETL's decision to make.

#### Which level-0 rule, measured rather than argued

| Rule | What it touches | Verdict |
|---|---|---|
| **Height cap** — lowest slab top within `[terrain, terrain + cap]` | 173 of 737 level-0 edges, 707 stations, ~81 lifting over 1 m | ❌ Ramp and flyover-deck populations separate at **4.95 m vs 5.33 m** — 0.38 m to place a threshold in, and it lifts five times what is broken |
| **Walk** — only edges meeting a mixed node, from that node until the structure meets the ground | **16 edge ends**, runs 3.8–88.3 m, all fitting inside their own edge | ✅ Monotonic descents to grade, no threshold to tune |

The walk rule answers "is this structure the road's own ramp?" from **topology** — the road is on
this ramp because it connects to the edge that is on it. That is the third place in this task where
the naive answer was "pick by height" and the measured answer was "pick by what it connects to".

`TONNOCHY ROAD` is in the 16 (`e520`, +0.89 m over 13.5 m). It is also the approach `PLAN.md` names
as the review location, which is a useful coincidence rather than a designed one.

#### The sampler itself: two ideas were wrong before they were measured

**1. There is no parapet to subtract.** Transverse profiles across 8 flyovers at 3 stations each:
the deck centre is a flat plateau, and the raised lips are **+0.11 to +0.92 m sitting off-centre at
±3 to ±6 m** — a centreline never touches one. `Q13`'s "+1.22 m, about railing height" reproduces
here as **+1.27 m median deck-above-ribbon**, which is the genuine gap between the invented height
and the deck. One config knob deleted before it was written, and the acceptance metric measures
against the deck top directly.

**2. Seeding the sample from the existing height and taking the nearest hit is *worse* than taking
the highest.** The multi-hit spread is **1.7–2.2 m on most edges** — deck slab thickness. The
sampler is hitting the top *and the underside of the same slab*, and today's seed sits below the
deck 66% of the time, so nearest-to-seed flips between the two faces and manufactures 80–96% grades.

What works is slab clustering plus continuity: cluster each station's hits into slabs (a gap over 3
m is a different structure), take each slab's top, then walk the edge choosing the slab that
continues the last, **anchored on the stations that have only one slab** rather than on any seed.

| Selector, 1188 segments over 45 level-1 edges | Segments over 12% | Worst grade |
|---|---|---|
| highest hit | 6 | **163.1%** |
| slab continuity | **2** | **13.7%** |

Median grade 2.47%, p90 8.04%, coverage 97.1% — consistent with the `Q13` spike's 3.01% / 7.45% /
95.3%. It fixes both stacked-deck edges (`e105` 124.6% → 6.9%, `e271` 163.1% → 8.1%). The residual
13.7% on `e521` is not artefact-scale; 12% was an arbitrary threshold inherited from that spike.

⚠️ `HeightField.sample` returns the maximum by design — the top of a sea wall is the drivable
face. Pointed at `INFRASTRUCTURE`, which is closed volumes rather than a surface, the same rule
reads Canal Road's upper deck while the edge is on the lower one. Same code, opposite correctness.
The class carries no normals, so "the top" needs a **per-slab** definition; anchoring on unambiguous
stations supplies one without needing normals at all.

#### Densification is needed, for the opposite reason to the one assumed

Off-grade vertex spacing is median 10.8 m but **p90 56.4 m and max 446.2 m**, which looked like it
would leave a chord across every ramp climb. Measured against dense truth at 2.5 m stations, it
mostly does not:

| Ribbon | median | p10 | p90 | **\|error\| p90** | max | below deck |
|---|---|---|---|---|---|---|
| today, as shipped | −1.27 | −2.87 | +3.74 | **4.19 m** | 14.42 | 66% |
| sampled at today's vertices | +0.00 | −0.13 | +0.05 | **0.30 m** | 4.84 | 16% |
| resampled at 10 m first | −0.00 | −0.03 | +0.01 | **0.04 m** | 0.57 | 3% |

Sampling alone already clears ±0.5 m at p90. **Densification is justified by the maximum, not the
p90:** 4.84 m, all of it on `e118` `FLEMING ROAD`, where a 71.5 m vertex gap spans structure
climbing 4.25 → 5.05 m. That is precisely the defect the user drove into, and p90 hides it. 10 m
spacing takes level-1 vertices from 430 to 667 and removes it.

#### A fallback gate, and the edge that proves it is needed

`INFRASTRUCTURE` is not only elevated decks. **`e425` `ISLAND EASTERN CORRIDOR`** — a 25 m stub at
the region's north-east corner — has no deck at all: 5 of its 11 stations return nothing and the
rest find structure at −2 m and −11 m. Testing *a deck cannot sit below the ground under it*
separates cleanly:

- `e425`: **−8.14 to −8.28 m** below terrain
- next worst: **−0.54 m**, and every other case is a genuine ramp grazing grade (`WAN CHAI
  INTERCHANGE` `e146`/`e294`/`e318`/`e399`, `MARSH ROAD`)

A 7.6 m gap between the two populations, and those near-zero margins are independent corroboration
that the interchange edges are real ramps. 18 of 1233 stations (1.5%) sample below terrain.

#### What this leaves of `Q13`

From "36 nodes step by a whole deck height" to **5 tunnel portals and 1 stub**. The 17 ramp
junctions close to ≤0.93 m and the 13 attribute flips close on both sides. A tunnel is a void, so no
height source will ever repair those five — that remainder is answered rather than merely left open.
Whether they should be *drawn* at all is a different question, and it is `Q21`.

#### And the portals are **clipped**, which is a better reason than "a tunnel is a void"

The user's guess on reading the above: *"the tunnel entrances are not in the Wan Chai area and are
in a wider nearby region not included."* Checked, and it holds — every one of the five has an edge
cut at the region boundary.

| Node | Road | Level −1 run inside the region | What is clipped |
|---|---|---|---|
| 250 | `CROSS HARBOUR TUNNEL` | **42 m** | the tunnel itself, at the harbour edge (z=0) |
| 430 | `CROSS HARBOUR TUNNEL` | **40 m** | the tunnel itself, at the harbour edge |
| 540 | `CENTRAL-WAN CHAI BYPASS TUNNEL` | 63 m | the tunnel, at the western edge (x=0) |
| 399 | `CENTRAL-WAN CHAI BYPASS TUNNEL` | 356 m | the level-0 continuation, heading west |
| 444 | `CENTRAL-WAN CHAI BYPASS TUNNEL` | 486 m | two level-0 continuations, heading west |

**11 of the 30 level −1 edge ends sit on the region boundary** — the underground network is clipped
harder than any other part of the graph, which follows from `P1-3` cutting roads at the boundary
where buildings are kept whole.

For the Cross-Harbour Tunnel this is decisive: **8 m of descent over a 42 m stub is a 19% grade.**
The descent happens outside Wan Chai, so there is no horizontal run inside the region to distribute
it over, and no height model — sampled, blended or authored — can put one there. That is a stronger
statement than "a tunnel is a void": even with perfect information the geometry does not fit in the
slice. It would resolve itself if the region ever grew east, which is `Q6`'s territory.

The bypass is the opposite shape — 356 m and 486 m of run — so those three *could* be blended
gently. But they are tunnel: invisible, under the terrain, and carrying colliders no one can reach.
That points at whether level −1 should be drawn at all rather than at a height fix, which is `Q21`.

#### Two acceptance criteria restated, because they are not literally achievable

- **Error against the structure** is measured against the **shipped tiles**, not against the
  sampler. An ETL-internal number reads 0.04 m at p90 and is very nearly tautological, since the fix
  and the measurement would share a selector. Baseline to beat: **4.19 m**.
- **"No ribbon left below the deck"** becomes *no sample more than 0.1 m below*. A piecewise-linear
  ribbon on a convex structure dips below it between vertices; at 10 m spacing that is 3% of
  samples, by centimetres.

#### Settled design, nothing implemented yet

| Edge | Height source |
|---|---|
| Level +1 | Resample at 10 m → slab-continuity walk → terrain gate → fall back to `terrain + deck_height_m(level)` where no valid sample |
| Level 0 **meeting a mixed node** | Walk from that node, lowest slab top at or above terrain, until the lift reaches ≤0.3 m — 16 edge ends |
| Level 0 elsewhere | Unchanged — `terrain`, exactly as today |
| Level −1 | Unchanged — `elevation_levels[-1]`; a tunnel is a void |

### 2026-08-01 — Genre direction: **three references, three different questions** — and one of them moves a task between builds

**Three references, three layers, and no contest between them.** Crazy Taxi, Midtown Madness 2 and
Forza Horizon are each strongest at a different layer, and the docs were already leaning each way in
different places without saying so.

| Reference | Contributes | Landed in |
|---|---|---|
| **Crazy Taxi** | The loop — fare combo, session timer, arrow, three-minute sessions | Already the design. Unchanged. |
| **Midtown Madness 2** | The world — real streets over invented ramps, tone, drivable roster | `GAME_DESIGN.md` divergence table and modes; the risk register |
| **Forza Horizon** | The reward layer — the losable style chain, scoreable traffic, world challenges | `GAME_DESIGN.md` scoring; `PLAN.md` `B3` and `B4` |

**Neither open-world structure survives a 1.5 km² region, and the reason is size rather than taste.**
Midtown Madness consumes map area as content — learn a route, beat it, need another — and Forza
Horizon uses the open world as its menu, which needs traversal distance to be a pleasure rather than
a formality. The region is **1.5 km²**; a checkpoint race across it is 60–90 seconds, and the slice
stops there deliberately. The fare loop does the opposite: it re-randomises the route through the
same 1.5 km² every session, which makes a small map an **asset** rather than a liability. Two
further things point the same way — multiplayer and licensed-car collection carried
those games' longevity, and both are unavailable here, one by anti-goal and one by budget and art
direction.

**The finding is a plan-ordering bug, and it is a shape this project has seen before.** `B3` ships
traffic, trams and minibuses, and its review question is *"harder in a
good way, or just annoying?"* `P3-2`'s near-miss scoring sat in `B4`, one build later. Dense traffic
converts from obstacle to opportunity only when threading it **pays** — so `B3` would have been
reviewed in the single state where traffic has no upside, and a "just annoying" verdict would have
been an artifact of the ordering rather than a finding about the traffic. Near-miss detection is
split out as `P3-2a` and moved into `B3`.

That is the same failure shape as `P2-5`'s missing building collision: **a unit whose acceptance
depends on a capability scheduled after it.** `PLAN.md` closed that note with *"worth a glance at
the other acceptance criteria for the same shape"*.

**Refused, and named here so they are not revisited.** Forza Horizon's wheelspins and randomised
rewards (already an anti-goal in `GAME_DESIGN.md`); its live-service, seasons and always-online
structure (hard rule 2 — the game makes zero network calls at runtime); licensed-car collection as a
progression spine (the art direction is 800–2,000-triangle toys, which is the opposite of a
collection); and Crazy Taxi's absurd-geometry philosophy — ramps and jumps scattered wherever the
driving goes quiet — which the divergence table licensed in one line and which `P3-9` would have
charged for in full.

**Three further references, one job each.**

| Reference | Job | Applies to |
|---|---|---|
| **Sleeping Dogs** | The nearest commercial precedent for a recognisable HK. The common reading is that **signage density carried it, not street accuracy** — untested here | `P3-9`, and the neon note now in `GAME_DESIGN.md` |
| **Burnout 3** | The fullest working-out of traffic as reward rather than obstacle — near miss, oncoming lane, risk-fed boost | `P3-2a` |
| **Art of Rally** | One shipped game whose flat-shaded untextured terrain is the **finished look**, not a placeholder — evidence, not proof | `Q18`, and `P3-10`'s cheap half |

**Neon is named but deliberately not scheduled.** There is none in the game and none in the slice.
It is on the record because it is the highest-value missing thing if Sleeping Dogs' lesson transfers
— the note in `GAME_DESIGN.md` carries the argument. First thing to reach for after `P3-9` reports.

**Nothing here is next.** `Q19` and `Q20` are both open and both owned by `P2-7`, and `P0-3b` needs
hardware before review point 2 can run. Phase 2 closes before any of this is reachable.

### 2026-08-01 — `P2-5` **closed**, and the exception it found is `Q20`: the flyovers are drawn twice

The camera verdict: *"camera work mostly with one exception where a road suddenly appears mid air and
block everything"*, with a shot from Tonnochy Road of an elevated ribbon sweeping across the view
and ending abruptly.

**That is not the camera, and `P2-5` passes.** The spring arm is behaving; the world has a road in
the air. Measured at the car's own position — `t=0.751` along edge 588 — road geometry within 60 m
is either y 2–4 (the street) or y 8–10 (the deck above it), and **nothing sits in the 0.3–3.0 m band
the car occupies**. Both halves of the review question hold: the road reads at speed, and the camera
stays out of the buildings.

#### What the drive actually found

`Q13` decided the elevated network is out of the slice, and `nearest_edge` refuses all 60 off-grade
edges accordingly. That decision was about **driving**. Nobody made the matching decision about
**drawing**, so `surface.py` still ribbons every off-grade edge:

| Level | Edges | Carriageway area | y range |
|---|---|---|---|
| −1 tunnel | 15 | 11.6% | −9.08 … 1.09 |
| 0 street | 737 | 76.7% | −2.85 … 49.84 |
| +1 elevated | 45 | 11.7% | 9.23 … 13.56 |

**23.3% of drawn carriageway is off-grade** — the figure `Q13` opened on, now with a second
consequence attached. Those ribbons have no ramps, because the ramps are precisely what `Q13` found
missing, so a deck starts and stops in mid-air. That is what the user drove up to.

**And the deck is already there.** Sampling along every level-1 centreline, `INFRASTRUCTURE` tile
geometry sits a median **0.51 m** away vertically, 78.4% of samples inside 2 m. The 3D Visualisation
Map models the flyover as a solid and `class_lod_cell_sizes_m` holds it at a 0.5 m cell precisely so
it survives decimation — and then `surface.py` draws a second carriageway on top of it. Two
coincident surfaces half a metre apart, both solid since collision shipped.

#### It also corrects `Q19`, which this session got wrong

Re-splitting the occupancy measurement by deck height:

| | Cells | Share | Reachable |
|---|---|---|---|
| `INFRASTRUCTURE` off grade | 8,508 | 1.73% | no |
| `BUILDING` at grade | 8,472 | 1.72% | yes |
| `INFRASTRUCTURE` at grade | 7,859 | 1.60% | yes |
| `BUILDING` off grade | 665 | 0.14% | no |

`Q19` was first written up as "`INFRASTRUCTURE` 3.32%, the larger half". **Over half of that sits on
ribbon nobody can drive on**, and most of it is the duplicate deck measuring itself against the tile
beneath it. The real at-grade defect is split roughly evenly between the two classes and is smaller
than reported. The lesson is one this project keeps relearning: a number is only as good as the
question it answers, and "blocked carriageway" without "carriageway the player can reach" was the
wrong question.

#### Then the user drove up a ramp, and `Q13`'s premise turned out to be dead

*"I hit the road going up from a ramp, but the road is not aligned to the ramp at all… there is
really supposed to be some road up on there near by, but the location is off."*

Both halves of that are right, and together they close the diagnosis.

**The height is invented, not measured.** `roads.py` sets every vertex to `terrain + deck_height_m(level)`,
and `elevation_levels` makes level 1 a flat **+6.0 m**. Real flyover decks do not sit at a constant
height above the ground they cross. Measured against the `INFRASTRUCTURE` structure the ribbon is
supposed to lie on:

| | |
|---|---|
| Signed error, ribbon minus deck top | median **−1.51 m**, mean −1.57 m |
| p10 … p90 | **−4.06 … +2.45 m** — a 6.51 m spread |
| Ribbon *below* the structure | **72%** of samples |
| Off by more than 1 m / 2 m | **78%** / **54%** |

So the ribbon is mostly buried inside the flyover it should be lying on, and where the structure
ramps the ribbon stays flat. That is exactly "there is supposed to be a road up there, but the
location is off" — and it is `Q13`'s own spike finding, already recorded on 2026-07-31: *the map
sheets carry the ramps, and sampling them beats inventing them.* It was deferred because sampling
fixes heights and not topology.

⚠️ **What changed is the reason it was safe to defer.** `Q13` reads "the elevated and underground
networks are topologically connected and **geometrically unreachable**", and that was true while the
only solid thing in the world was `roads.glb`. Since collision shipped, the `INFRASTRUCTURE`
structure is a collider — so **the physical ramps are drivable**, and the player arrives on a deck
whose carriageway is a metre and a half away in the wrong direction. Nobody decided to open the
elevated network; a change made for the camera opened it.

This stops being a drawing question. Either the network is closed properly, or it is opened
properly, and that is a product decision rather than an ETL one.

### 2026-08-01 — `P2-5` drive: collision passes, and it **promoted a cosmetic overlap into a blocker**

The user drove the streamed city and returned *"collision seems ok, note that some building actually
went onto part of road"*, with a shot of a slab standing across the carriageway under a flyover.

**Read the verdict narrowly, as `P2-3`'s was.** It answers the collision question and it does not
answer the one `PLAN.md` names for `P2-5` — *can you read the road at speed, and does the camera
stay out of the buildings?* No camera complaint was raised, which is not the same as a pass, and
this is the project's own lesson: a review finds what its question asks for, and the transposed
basis survived a full drive because nobody had asked. **`P2-5`'s camera half stays open.**

#### The overlap, measured rather than eyeballed

Geometry was rasterised to a 1 m plan grid: deck height per cell from `roads.glb` taken as the
*minimum*, so a flyover overhead does not raise the street beneath it, and tile geometry sampled
over each triangle's surface. A cell counts only when solid geometry sits in the band
**0.3–2.0 m above the deck** — bumper to roofline. A podium 6 m up overhanging the street is Hong
Kong working as intended; a slab at bumper height on a legal carriageway is the defect.

| | Cells (1 m) | Share of drivable surface |
|---|---|---|
| Drivable surface | 492,320 | — |
| **Blocked** | **25,466** | **5.17%** |
| └ `INFRASTRUCTURE` | 16,367 | 3.32% |
| └ `BUILDING` | 9,137 | 1.86% |

Class comes from the vertex colour, the only place a merged tile still records it —
`INFRASTRUCTURE` is `#9d9a93` against height bands of 191–211, so the gap is clean. The two rows
overlap slightly where a cell holds both.

⚠️ **These are two defects wearing one symptom, and they do not share a fix.**

- **`INFRASTRUCTURE`, 3.32% — the larger half, and it belongs to `Q13`.** Flyover piers, deck
  undersides and ramps that descend toward grade sit in the street because the elevated network's
  *structure* is modelled at its true height while the level-0 ribbon is drawn straight under it.
  A first bad measurement put this at 13.71% by marking each triangle's bounding box; sampling the
  actual surfaces cut it to a third of that, which is worth recording because the bbox number was
  the one that looked like a crisis.
- **`BUILDING`, 1.86% — this one the project chose.** `roads.surface.widen_default` is **1.6×**, and
  `GAME_DESIGN.md` fixes the range at 1.3–1.8× because real Wan Chai streets are unforgiving at
  arcade speeds. Widening eats the pavement first and then the ground-floor frontage. The config
  already knew: `widen_by_min_speed_limit_kph` holds expressways to 1.3 with the comment *"widening
  them the same amount pushes the deck through the buildings beside it"* — the same effect, found
  once, fixed locally, and never checked across the network.

**Nothing here is new geometry; only the consequence is new.** All of it predates 2026-08-01 and
none of it mattered while the city was a hologram. Collision is what turned 25,466 m² of overlap
into 25,466 m² of invisible wall on roads the graph says are legal — and `P3-3`'s traffic will
route into it too, because `RoadGraph` has no idea any of it is there.

**Not fixed here, and deliberately.** The `BUILDING` half is a tuning value the game design fixes a
range for, so lowering it is a playability decision rather than a bug fix, and it trades against the
one thing `P1-4` measured it for — at 1.0× the widest opposed pair leaves a 0.42 m slot down the
middle of Lockhart Road. The `INFRASTRUCTURE` half is `Q13`'s, which is already open and already
knows the elevated network is unresolved. Both want the same missing tool first: **a check that
fails the build when the carriageway is occupied**, which is the only reason this number is known at
all and is currently a script in a scratchpad rather than a seventh verify tool.

### 2026-08-01 — Buildings get collision from a **mesh name**, and the task that owned it had already closed

`P2-5`'s acceptance criterion is *"no clipping through buildings"*. It is not reachable: a
`SpringArm3D` collides with nothing until the buildings do, and `city_streamer.gd` said in its own
docstring that tiles carry none. `PLAN.md` gave that decision to `P2-1` — "decides where tile
colliders come from" — and `P2-1` decided correctly that **a building collider is an ETL product,
not a runtime one**, then closed. The decision was right and it left nobody holding the work, so the
region shipped as a hologram: 65 tiles the car drove straight through, and a camera with nothing to
be stopped by. Neither the streamer review nor the `P2-3` drive would have caught it, because
neither asked.

**The answer was already in the repo.** `P1-4` gives the carriageway its collider by naming the mesh
`road_surface-col`: Godot's glTF importer reads the suffix and builds a `StaticBody3D` carrying a
`ConcavePolygonShape3D` at **import** time. `buildings.py` now names its finest tier
`<tile_id>-col`, and that is the entire game-side change — the collider arrives inside the
`PackedScene` the streamer already instantiates, on the load thread it already uses. No shape is
built at runtime, and the collider cannot drift from the mesh it is drawn from because it *is* the
mesh.

**Only the finest tier, and that is policy rather than economy.** A tier is chosen by distance, so
the coarse one is resident only beyond the 250 m band, where nothing can touch a building.
`verify_tiles.gd` asserts both directions — present on tier 0, absent on every other — because a
suffix that spread would be invisible in every screenshot and would show up only as bundle bytes,
which is `Q16`'s failure mode exactly.

| | PCK |
|---|---|
| Before | 22,121,216 B — **21.10 MB** |
| After | 27,546,816 B — **26.27 MB** |
| Cost of collision | **+5.17 MB, +24.5%** |

Measured from two `Web Demo` exports, one variable changed. Worth stating what it is *not*: tier 0
is 434,149 triangles region-wide, which as raw un-indexed `ConcavePolygonShape3D` faces would be
**14.91 MB**. The pack compresses them to a third of that. `Q16`'s rule — measure the PCK, never sum
the source — earned its keep in both directions in one session.

Against a 200 MB budget, one full region with collision is 26.27 MB. The cheaper alternatives were
priced and not needed: a `-colonly` third file per tile, or building the shape in GDScript at load.
Both trade bundle bytes for either mismatched geometry or main-thread time, and neither is worth
5 MB.

**Driven, not argued.** Full throttle into the HKCEC massing: 42.32 kph at t=4, **0.05 kph at t=5**,
and pinned at (189.5, 6.16, 42.2) for the remaining three seconds with the throttle still held.
Before this it would have carried on into the void and been respawned by the harness. Shots in
`build/driver/wall-right/`.

**`P2-5` needed no shape-cast, and that is a result too.** The spring arm is a plain raycast with a
0.3 m margin. The margin is larger than the camera's near plane is wide — 6 cm at 70° FOV — so a
corner cannot slip between the ray and the frustum, and adding a `SphereShape3D` would have been
complexity bought on a hunch. Tested where it is hardest: with the car pinned nose-first against a
wall, **holding look-back flips the rig 180° and drives the camera into that building**. The arm
compresses and the view stays clear. See `build/driver/lookback-wall/` and the drift through the
junction east of HKCEC in `build/driver/p25-drift/`.

⚠️ **`P2-6` must re-measure hitching.** Instantiating a tile now also registers a trimesh with Jolt
on the main thread, and `max_instantiations_per_frame` is 2. `P2-1`'s "no hitching on tile
boundaries" was accepted before that cost existed. It is invisible at 120 fps on an M4 Pro and is
exactly the kind of thing the device floor finds.

#### Two bugs found on the way, and the second was the dangerous one

Both were in code that had passed every check, and both were reachable only when the manifest was
stale — which is why nothing had met them.

1. **`RoadGraph.shared()` returned `null` from a guard written to stop it.** The fallback read
   `manifest.carriageway_half_width_m if manifest != null else {}`, and `_build` takes a
   `Dictionary[int, float]`. An inline `{}` is **untyped**, so the null branch — the only branch the
   guard exists for — raised *"does not have the same element type"*, aborted the function, and
   returned `null` from a call whose docstring promises it never does. The guard had never worked in
   the one case it was written for.
2. **`verify_spawn.gd` hung instead of failing.** It called `.is_empty()` on that `null`, the script
   error left `_init` before any `quit()`, and the `SceneTree` then ran forever. `tools/check.sh`
   hung with it — twice for over ten minutes each — and in CI that is the whole job timeout spent
   producing no diagnosis. **A check that hangs is worse than a check that fails**, because a
   timeout names nothing.

Fixing (1) turned the hang into a **silently wrong pass**: with no manifest the graph builds without
carriageway widths, and the spawn assertion still reported `ok` — at **1.60 m** off the centreline
instead of 2.56 m, a number computed from absent data. `verify_spawn.gd` now refuses on
`RoadGraph.has_carriageway_widths()`, which `verify_road_graph.gd` already used for this exact
failure. That is stronger than the manifest null-check it replaced, and the difference is not
academic: a `city.json` that loads cleanly but publishes an **empty** carriageway table passes a
null-check and fails this one.

That is the third distinct way this project has produced a green check that checked nothing, after
the two `Q17` records. The pattern is always the same — a fallback that lets a tool carry on with
less than it needs — and the fix is always to assert the property the tool actually depends on
rather than the file it came in.

### 2026-08-01 — `P2-3` review **passed**: "car seems ok"

The verdict on *"is this still the `P0-5` car?"*, recorded in the user's own words because the
wording is the finding. It is a pass, and a narrow one: it says the placement change did not damage
handling that `P0-5` had already accepted. `handling.tres` was not touched by `P2-3` and did not need
to be, so that is exactly the claim the review was set up to test.

**What it does not say** is anything about feel in the hand — that is review point 2, it needs
`P0-3b`'s signing identity and handsets, and it is still open. Recorded this way for the reason
`Q8`'s entry gives: a verdict read wider than it was given is how a conditional pass turns into an
assumption nobody remembers making.

### 2026-08-01 — `P2-3`: the start line is **queried, not written down**, and the transpose trap is deleted rather than documented

`P2-3`'s deliverable is the car "placed by `P2-2`'s lane-centre query rather than by a hand-written
transform", and almost all of it is a deletion. `RoadGraph.Hit` has carried `lane_centre` and a
resolved `forward` since `P2-2`; `city_drive.tscn` carried a twelve-float `Transform3D` literal and
`ARCHITECTURE.md` carried forty lines explaining how to not transpose it. `RoadSpawn.at_fare_node`
connects the two that already existed, and `basis_facing` — `Basis.looking_at` on a direction —
means there is no literal left to get wrong.

**The query reproduces the literal to 4 dp**, which is the result worth recording: resolved
`(172.3485, 6.579562, 26.93956)` against an authored `(172.3485, 6.5796, 26.9396)`, and the
`P2-2` overlay reads `0.00 m` from the nearside lane centre with `heading agrees with travel:
+1.00`. The hand-derivation in `ARCHITECTURE.md` was right; it just should not have had to be done.

**The heading is deliberately not passed to the query.** A zero heading makes `nearest_edge` take
the edge's own vertex order, and `P1-3` reversed the polyline of every backward edge precisely so
that order *is* the legal direction. Passing the car's authored rotation in would let the car decide
which way a two-way street runs, which is the wrong way round: the street decides.

#### The orientation check, and why it proves itself

`verify_spawn.gd` is the sixth verify tool. `P2-3`'s acceptance criterion is "spawn orientation
asserted against its edge vector", and the assertion on its own is not enough — **a transpose is not
a 180° flip.** It mirrors the heading about world −Z: 171.9° wrong on Expo Drive, 180° on a due
east-west street, and **0° on a north-south one**. A tool that only asserted the good case would
pass on a north-south spawn with the bug present. So the tool builds the transposed basis and
requires it to *fail*, and floors the discriminating angle at 10°:

```
facing: 0.0000° off the edge vector; a transposed basis would be 171.9° off
spawn:  f_004 on edge 651 (EXPO DRIVE), 2.56 m off the centreline, 1.00 m of air
```

Proven non-vacuous the way `verify_city.gd` was: transposing `basis_facing`'s return makes it exit
`1` with both halves firing, and pointing it at a fare id that does not exist exits `1` with the
reason.

#### Two findings that changed the shape

**`ray_length_m` lives on `HandlingProfile`, not on `VehicleController`.** It went on the controller
first and the check caught it: `vehicle_controller.gd` reads the `InputRouter` autoload, **autoloads
are not registered under `--script`**, so any headless tool that touches the controller fails to
compile. Worse, `verify_spawn.gd` then *printed `ok` and exited 0* while erroring — the exact false
green the repo's checks exist to prevent, caught only because `tools/check.sh` greps stderr for
compile failures as well as reading the exit code. The number is a fact about the profile anyway,
which `suspension_rest_length_m`'s own comment already stated in prose.

**The authored transform stays in the scene as a fallback, and says so.** `assets/generated/` is
gitignored, so a fresh clone has neither graph nor fare nodes — and no road to drive on either. The
literal keeps the camera somewhere sensible while the "run the ETL" warning gets read. The harness
prints how far the resolved spawn has drifted from it, because a fallback nobody looks at drifts.

**Resolution lives in `drive_harness.gd` rather than in a node of its own.** The harness is on the
scene root, so its `_ready` runs after every child's — there is no arrangement of siblings that can
beat it to the car, and the fall floor it derives is read from the pose it just applied.

#### What the review pass then caught, and it was not style

Two defects in code that had already passed every check:

1. **The nearside-lane assertion was measuring against the wrong street.** It took the centreline
   from a fresh unconstrained `nearest_edge(lane_centre)`, which can land on a *neighbouring* edge,
   and compared that vector against `pose.forward`, which belongs to the spawn's edge. Where the two
   differ the verdict is meaningless. `Pose` now carries `point` from the same `Hit` as `forward`, so
   the two are correct by construction. The independent query survives for the seam-clearance check,
   where asking "the nearest centreline *anywhere*" is the stricter question and the right one.
2. **A keep-alive comment stated the opposite of the truth.** `drive_harness.gd` held the graph in a
   member "so a local would not drop the 6 MB parse the overlay is using" — but the harness readies
   *last*, so the overlay is already the strong owner and a local could drop nothing. It is a local
   now.

Three smaller ones: an unused `clearance_m` parameter that made the drop-height check valid only
because nobody passed it; a malformed `pos` degrading to `Vector3.ZERO`, which in a region-local
frame is a real place and would have resolved to a plausible wrong street instead of failing; and
`spawn_fare_id = "f_004"` duplicated into the scene file, so changing `DEFAULT_FARE_ID` would have
silently done nothing to the scene that actually boots.

The fares document's shape — the `nodes` array, `id` and `pos` — moved to `generated_fares.gd`,
which already existed to be the one place that knows it, and `fare_preview.gd`'s own copy went with
it. `RoadGraph.left_of` names the left-of-travel cross product that four other sites write out by
hand.

### 2026-08-01 — Ground and building colour: **the vertex stream carries both**, and the source texture is a build-time colour *source*, never a shipped one

An evaluation, not an implementation. It answers two questions the user put together — "should the
ground be simply coloured from the huge source texture?" and "how do buildings get colour without a
size or perf cost?" — and they turn out to be one question: **what channel carries colour.** The
project already answered it. Colour rides `COLOR_0` on an untextured mesh that merges to one
primitive per tile, and that single choice is what produces 53 draw calls and a 21.1 MB PCK. Both
answers below are that rule applied twice.

**There is currently no ground at all.** `ART_DESIGN.md` says it outright — the kerb lip exists
because "the terrain is too expensive to ship, [so] it is what stops the carriageway ending in
mid-air" — and `drive_harness.gd` carries a fall floor to catch the car when it leaves the ribbon.
Between the roads and under the buildings is skybox. `B2`'s verdict question is *"Does this read as
Wan Chai?"*, and a city floating over a void cannot pass it whatever the window shader does.

#### The terrain budget that terrain failed no longer exists

`P1-2t` measured 267 MB and 405k triangles against a bundle already holding 51.6 MB of tiles. `Q16`
then dropped LOD0. Re-read against today's numbers, the old verdict says something narrower than
"unaffordable":

| | `P1-2t`, 2026-07-30 | Today |
|---|---|---|
| PCK | 51.6 MB | **21.1 MB** of 200 MB |
| Draw calls | 70 | **53** of 150 |
| Worst-case visible triangles | 249,210 | **150,374** of 300k |
| Terrain texture | **224 MB** — the whole failure | — |
| Terrain geometry | 43 MB, 88,081 tris at 4 m cells | — |

**224 of the 267 MB was the JPEG. Geometry was never the problem**, and the resampling that would
have fixed the texture was simply never written.

#### Three shapes it could take, and why the middle one wins

**Rejected — ship the texture, resampled.** 2 px/m over the region is 5.94 MPix ≈ 5.9 MB as ASTC,
affordable in isolation. It fails on two other counts. A textured surface cannot merge with the
vertex-coloured building primitive, so it costs **+1 draw call per resident tile** and introduces
the first texture into a pipeline whose entire economics rest on having none. And an orthophoto has
the *real* roads baked into it at their real width, while `roads.py` places the generated ribbon at
`terrain + deck_height` — coplanar, and **widened 1.6×**. The result is photographic asphalt with
photographic lane markings poking out from under a wider synthetic road, plus parked cars and hard
shadows baked into the ground. That is the `ART_DESIGN.md` photogrammetry-texture anti-goal.

**Chosen — the texture is read at build time and thrown away.** Sample the full-res JPEG per source
triangle, **classify** to a small land-cover palette (asphalt / pavement / vegetation / water /
bare), write the result into `COLOR_0`, ship no texture. Then:

- Zero texture memory, zero texture bytes in the bundle.
- Terrain is untextured and vertex-coloured, so it **merges into the existing tile primitive** —
  one draw call per tile, `verify_tiles.gd`'s invariant intact.
- ~88k triangles region-wide ≈ **1,355 per tile**; a ~30-tile resident set adds ~40k to 150,374.
- Geometry ≈ 1.5–2.5 MB on a 21.1 MB PCK.
- **The UV-smearing objection to decimating terrain evaporates** — there are no UVs left to smear,
  so `mesh.collapse` runs on it for free. `P1-2t` named that smearing as the reason decimation was
  awkward; deleting the texture deletes the reason.

The implementation idiom already exists. `mesh.collapse` puts *facing* in the cluster key so a wall
vertex never averages into the roof above it. Put the **land-cover class** in the key the same way
and cluster boundaries land exactly on the park, pavement and water edges instead of blending
across them. That is what makes 4 m colour blobs read as deliberate low-poly ground rather than as
mush.

**Ordered first — geometry only, one flat colour.** Decimate, colour it warm grey, ship it. No image
decode, no new dependency, and it produces the screenshot that says whether flat ground reads dead
or fine. If flat is fine, the classification code is never written. That ordering is `P3-10` and
`Q18`.

Three caveats carried into the task:

1. **Sink the terrain ~0.2 m below the road deck** so it tucks under the kerb lip that already
   exists rather than z-fighting the carriageway. Whether 0.2 m survives cross-slopes is the one
   thing that must be measured rather than assumed — it is the likeliest thing to go wrong.
2. **Visual only, no collider,** in the first pass. The kerb currently defines the drivable world;
   giving the pavement collision is a gameplay change wearing an art change's clothes.
3. Classification needs an image decoder. The ETL has none — `gltf.Texture` passes bytes through
   untouched — so it means adding **Pillow**, and six 45 MPix decodes at ~136 MB of RAM each.
   That cost belongs to the second phase, not the first.

#### Buildings do not have a colour problem

They have a **surface-detail** problem, and the fix was already designed as `P3-7`. Colour itself is
solved: `colour_for` assigns a height-band or per-class colour with `crc32`-seeded jitter, stable
across rebuilds, palette in city config.

Three routes were put and two are rejected:

- ❌ **Low-res texture or atlas.** Any texture needs UVs, and **UVs do not survive vertex
  clustering** — which is how both shipped LOD tiers are produced. This is paying to break the LOD
  system.
- ❌ **Per-building colour sampled from the individualised set's full-res textures.** The
  non-textured buildings carry no texture at all, so this means the individualised download —
  **5.86 GB zipped for Wan Chai, 93–96% of it texture** — plus matching ids across two sets that
  disagree on building count (738 vs 769 on one sheet). The payoff is a median photogrammetric
  façade colour, which in oblique aerial capture is dominated by shadow, sky bounce and haze: it
  converges on desaturated grey-beige for everything and flattens exactly the old-below/new-above
  contrast the height bands exist to express. High cost, plausibly negative result.
- ✅ **Spend the channels already in the bundle carrying nothing.**

| Channel | Today | Cost to use |
|---|---|---|
| `COLOR_0.a` | constant `255` | **zero bytes** |
| `TEXCOORD_0` | absent — buildings ship no UVs | ~2 bytes/vertex quantised |

The window-band shader needs two things a vertex cannot derive on its own: **height above its own
building's base** (a vertex knows world Y, not where its building starts) and a **per-building
seed** (so neighbours do not share a window pattern). Put both in `TEXCOORD_0.xy` at ETL time and
`P3-7` is a few ALU instructions with no texture, no atlas, and full LOD compatibility — clustering
carries UVs through the same representative-selection path it already uses for colours. A third
trick is free on top: **bake a vertical gradient into `COLOR_0`** darkening the bottom couple of
metres, which grounds buildings where they meet the pavement and costs nothing at runtime.

⚠️ **Use `TEXCOORD_0`, not `COLOR_0.a`, for the mask.** `generated_scene_import.gd` sets
`vertex_color_use_as_albedo = true` project-wide. Opaque `BaseMaterial3D` ignores albedo alpha, so a
mask in alpha is safe *today* — and the day anyone enables transparency on a tile the city goes
see-through with no error. UVs have no such failure mode.

If the palette itself turns out to be wrong, the cheap lever is a **throwaway offline script** over
one or two individualised sheets: cluster the dominant façade colours and re-author the five
`height_bands` in YAML from the result. Evidence-based palette, no pipeline change, nothing extra in
the build path — the whole benefit of the photo data at about 1% of the cost.

#### Sequencing

Neither is next. `P2-3` is the Phase 2 gate. The ground is `P3-10`, landing in `B2` where it is
judged; the `TEXCOORD_0` payload lands **inside** `P3-7`, in one commit that changes ETL and game
together and bumps `schema_version` — hard rule 5. Writing them down now is the point: the ETL half
of `P3-7` is the part that gets discovered late otherwise.

### 2026-08-01 — **Two** shadow cascades, not four: 35% off the frame's primitives

`ART_DESIGN.md` specifies "Desktop tier: one directional shadow cascade". `golden_hour.tscn` never
set `directional_shadow_mode`, so it took Godot's default of **four PSSM cascades** at a
`directional_shadow_max_distance` of 600 m — past both the chase camera's 400 m far plane and the
streamer's 400 m unload. `P2-1`'s review had already measured and named this as "the single largest
lever left on the frame cost" and left it to `P2-6`; it turned out cheap enough to take now.

Per-second primitives, from a `drive.sh` run out of the HKCEC spawn — reproducible, since `ee0ebea`
put the counters in the harness:

| Config | t=1 | t=3 | t=6 | vs default |
|---|---|---|---|---|
| 4 cascades @ 600 m (was) | 244,888 | 215,071 | 263,077 | — |
| **2 cascades @ 400 m (shipped)** | **159,739** | **132,845** | **155,032** | **−35%** |
| 1 cascade @ any distance | 110,644 | 93,206 | 112,142 | −55% |

⚠️ **One cascade is what the spec asks for, was shipped first, and had to be withdrawn.** It has a
distinct artefact at every distance tried, and they are all visible on screen:

| Distance | What breaks |
|---|---|
| 150 m | Shadows fade out over 120–150 m while the camera draws to 400 m, so the far half of a long street is flatly lit behind a visible cutoff |
| 250 m | The HKCEC shadow across Expo Drive East comes out **banded** — the shadow map's own texels showing through the filter, at 0.092 m each |
| 400 m | The HKCEC shadow **disappears**; the caster is behind the camera and falls outside the ortho volume's near plane |

**The first two are one artefact, not two, and that is what caught me out.**
`directional_shadow_fade_start` is a *fraction* of `max_distance` (0.8), so shortening the distance
to sharpen the near field silently drags the fade band in with it — 480–600 m became 120–150 m.
The plan named this risk; I then checked the two artefacts I expected, peter-panning and acne, on a
**near-field crop** and never looked down a long street. The user did, and asked why the road went
flat. Two cascades removes all three at once: a fine near split and a coarse far one.

**400 m rather than 600** because it is exactly the chase camera's far plane and the streamer's
unload distance, so shadow reach and draw distance now end together. Distance is free either way —
150, 250, 400 and 600 measure **bit-identically** for a given cascade count, verified across all
four.

**`ART_DESIGN.md` amended, deliberately.** Its one-cascade line was written before anyone measured
it. The desktop tier is now two cascades, with the artefact table above as the reason.

**Peter-panning did not appear.** Godot scales directional `shadow_bias` by cascade extent, so a
longer cascade carries a larger world-space bias and contact shadows detaching was the likely
failure. A matched pair with the car in open sun shows its shadow still attached, same shape and
softness. `shadow_bias`, `shadow_normal_bias`, `directional_shadow_pancake_size`, `shadow_blur` and
`fade_start` all stay at engine defaults.

**Cascade count costs draw calls, which the headline hides.** 32 → 35 at t=1, monotonic with fewer
cascades (4 → 32, 2 → 35, 1 → 39, off → 26). Against a 400 desktop budget it is a non-issue, but it
moves in the opposite direction to the primitive count and is not noise.

⚠️ **"55% off the frame" is a primitive count, not a frame time.** Every configuration pinned to
8.3 ms on this machine — the display refresh — so the real GPU saving is **unmeasured**, and
shadow-map fill is unchanged either way since the atlas is one texture at any cascade count. The
change is justified as headroom for the unbuilt mobile tier and as spec conformance, not as a
measured speed-up.

**No `LightingProfile` resource, deliberately.** Hard rule 4 says tuning values are data rather than
constants in code, and a `.tscn` *is* data — `city_drive.tscn` already carries `far = 400.0` the same
way. A profile plus an apply script would move values out of a scene the editor renders correctly and
into a script that writes them in `_ready()`: two sources of truth whose disagreement would be
invisible in the editor. It is also the shape of the `stats()` API deleted three commits ago.

**Three things this does not do, named so they are not mistaken for oversights.**

- **The mobile tier is still unbuilt.** `ARCHITECTURE.md` claimed two tiers "selected at runtime by
  platform"; nothing in `game/scripts/` reads `OS.has_feature` or any quality setting, so that line
  was false and is corrected. ⚠️ And "vehicle blob shadow only" deserves re-examination before anyone
  implements it: shots with shadows *off* looked markedly worse than the line implies — flat and
  blown out, the canyon losing its depth entirely. A real mobile tier needs the ambient and tonemap
  re-tuned around a blob shadow, not the shadow switched off. `P2-6` inherits that.
- **`greybox.tscn` keeps its own `Sun`**, a second light outside the shared rig. Deliberately neutral
  grey-box lighting, off the boot path, in a nearly empty scene where four cascades cost nothing.
- **Nothing asserts the rig stays on spec.** An editor save could restore the four-cascade default
  silently, exactly as it strips comments from `project.godot`. Not worth a `verify_lighting.gd`
  today, but when the second tier lands the check worth writing is "each tier's `max_distance` ≤ its
  camera's far plane".

**Unrelated finding, recorded while looking at the shots.** The dark wedges at junctions — the thing
that prompted the user to ask about shadows in the first place — are **not shadows and not the
missing terrain**. They are gaps in the road mesh: `surface.py` trims each edge end back from a node
and fills the middle with a cap built as a ring fanned from its centroid, so where roads meet at an
angle the cap's straight chord cuts inside the corner and leaves a wedge no ribbon reaches. The
roundabout island east of HKCEC is a genuine hole for the same reason. They read as shadows because
the sky's ground gradient shows through, tinting blue-grey at grazing angles and tan at steeper ones.
A `P1-4` surface-coverage question, and worth taking before `P3-9`'s authenticity test.

### 2026-08-01 — `P2-1` review **passed**, and it closes `Q16`: **LOD0 does not ship**

Both halves of the gate, answered by driving rather than by argument. The user drove a build with no
exact-weld tier at all — not a distance-band trick, an actual two-tier build — and the verdict was
*"they look ok"* on the buildings and *"not much pop"* on the transitions.

| | 3 tiers | 2 tiers | |
|---|---|---|---|
| Files shipped | 199 | 134 | −65 |
| Source bytes | 105.5 MB | 30.8 MB | −74.7 MB |
| **PCK** | **51.6 MB** | **21.1 MB** | **−30.5 MB (59%)** |
| Worst-case visible triangles | 249,210 | **150,374** | **−40%** |
| Worst-case resident triangles | 424,648 | 236,882 | −44% |
| Draw calls | 53 | 53 | — |

**Both budgets improve, and the second one is the surprise.** Dropping a tier was supposed to be a
bundle decision; it also took 40% off the frame cost, because the tier it removed was the one drawn
nearest the camera where the least is culled. Worst-case resident is now *under* the 300k visible
budget on its own, so the disc-versus-cone caveat `P2-1` recorded no longer even bites.

**`Q16`'s own lesson applied to itself, again.** The source saving is 74.7 MB and the PCK saving is
30.5 MB, because Godot's `.scn` is roughly half its glTF source. `PROGRESS.md` had estimated "the
bundle drops to 28 MB"; measured, it is **21.1 MB**. Better than the guess this time, and still 33%
out — which is the entire reason `Q16` insists on measuring a PCK.

For the business case the question actually turns on: roughly **4–5 regions in a 200 MB download
instead of 2**.

**The bands were retuned with it.** Two tiers want one edge, not two. Left at `[100, 250]` the
coarsest band clamps, so everything past 100 m drew at 4.0 m cells — one step coarser than intended.
`streaming.tres` now carries a single 250 m edge: the 1.5 m mesh across 0–250 m, the 4.0 m mesh from
250 m to the 400 m unload. Worth noting the user's verdict was given on the *coarser* version, which
makes it a stronger yes than it needed to be.

⚠️ **Dropping the finest tier broke the `aabb` contract, and `verify_city.gd` caught it — 34 tiles.**
`tiles[].aabb` was measured from the **uncollapsed source**, which was right only while tier 0 was an
exact weld and therefore matched it corner for corner. Once the finest shipped tier was decimated,
the published box described geometry no build contained: one tile declared a height **19 m** past its
own LOD0, a mast too thin to survive a 1.5 m cell. The ETL now publishes the union of the **shipped
tiers**.

**And that union is not a formality.** The obvious fix — publish tier 0's box — is wrong, measured on
`t_01_02`: its **4.0 m tier stands 12.03 m taller than its 1.5 m tier**, and exactly equals the
source. `collapse` buckets on `floor(position / cell_m)` and averages each bucket, so a *coarser*
grid can leave an extreme vertex alone in its cell and preserve it exactly where a finer grid
averaged it inward. Decimation does not only shrink a box.

`verify_city.gd`'s assertion moved with it: from "tier 0 equals the declared box" to "every tier is
contained by it, and their union is tight to 1 cm". Re-proven non-vacuous by nudging a tile 0.5 m
east — both halves fire and it reports "0.500 m out", the same way `P1-7` validated the original.

**What is not closed.** LOD0 can come back for one platform: the 200 MB budget is the *iOS cellular*
threshold and `ARCHITECTURE.md` gives desktop no hard limit, so a desktop-only exact-weld tier is an
export-filter question rather than a settled no. It is one entry in `lod_cell_sizes_m` and a 3 s
rebuild.

### 2026-08-01 — LOD is **per mesh class**: a deck is not a building, and one cell size cannot serve both

`P2-1`'s LOD1 shots showed the flyovers and footbridges coming apart while the buildings beside them
were near-indistinguishable. The cause is geometric and it is exact: **`collapse` clusters vertices
by cell, so any structure thinner than the cell has its top surface merged into its bottom one.**
Measured on two synthetic solids:

| Solid | raw | 0.5 m | 1.0 m | 1.5 m | 4.0 m |
|---|---|---|---|---|---|
| Deck, 30 m across and **0.8 m thick** | 12 | 12 | **2** | **2** | **2** |
| Tower, 20 × 20 × 60 m | 12 | 12 | 12 | 12 | 12 |

A tower is untouched at every cell size the pipeline uses. A deck flattens to two triangles the
moment the cell exceeds its own thickness. The tier was never too coarse for buildings — it was
always too coarse for infrastructure, and merging the two into one mesh before collapsing meant one
cell size had to serve both.

**`class_lod_cell_sizes_m` in city config, and the merge moves after the collapse.** `buildings.py`
now buckets a tile by class, collapses each class at its own cell, then merges. Ordering is the
whole fix: merging first puts a deck and a wall in the same cluster grid. Merging *after* keeps the
tile **one mesh and one draw call**, which `verify_tiles.gd` enforces from the engine side and which
a new test asserts at every tier.

Hong Kong sets `INFRASTRUCTURE: [0.0, 0.5, 1.0]` against the building default `[0.0, 1.5, 4.0]`.
The same shape of config as `class_colours`, which exists for the same reason — infrastructure is
concrete whatever its height, and it is thin whatever the tier.

| | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| Before | 989,212 | 400,154 | 183,792 |
| **After (0.5 / 1.0)** | 989,212 | **434,149** (+8.5%) | **222,375** (+21%) |
| Full exemption, rejected | 989,212 | 480,538 (+20%) | 288,275 (+57%) |

**Chosen over an outright exemption because a deck only has to beat its own thickness.** 0.5 m
clears a 0.8 m deck with room to spare and costs less than half what exempting infrastructure
entirely would. What it buys, measured in-engine at the same five places `P2-1` used: worst-case
visible triangles **240,598 → 249,210**, or **+3.6%**, against a 300k budget — so ~50k of headroom
survives. Draw calls are unchanged at 53.

**The landmark half of the question was declined, and for a better reason than "not implemented".**
There is no landmark key in the source: the sheets carry `BUILDING` and `INFRASTRUCTURE` and nothing
else. More usefully, `ART_DESIGN.md` already specifies the ~5 hero buildings as **hand-authored**
3–8k-triangle models placed via `landmarks.json` — they never pass through `buildings.py`, so their
source massing is *replaced* rather than decimated and the question is moot for exactly the
buildings that motivated it.

⚠️ **One correction on the way there.** `P2-1` recorded that tall towers survive LOD1 well because
they are big boxes. Measured, the opposite is true: towers ≥100 m keep **36%** of their triangles at
LOD1 against **44%** for everything else. They are hit *harder*, not less. They read as fine in the
canyon shot because they were distant, where a tower is mostly silhouette. That does not change the
decision — a height-based exemption would cost roughly +43% of LOD1 building triangles and is a
blunt proxy for what `landmarks.json` solves properly — but the reasoning in the earlier entry was
wrong and is corrected here.

### 2026-08-01 — `P2-1`: the city streams, and **visible triangles come inside budget for the first time**

`CityStreamer` replaces `tile_preview.gd` on the boot path. Measured in-engine at five places, the
same five before and after — because quoting one spot's "before" against another's "after" is how
every bundle figure in this project drifted:

| Place | Draw calls | Visible triangles (main pass) | With the shadow pass |
|---|---|---|---|
| (172, 27) — the HKCEC spawn | 63 → **32** | 163,384 → **60,758** | 1,164,133 → 268,709 |
| (1114, 506) — worst residency | 52 → **46** | **398,574 → 240,598** | 1,591,160 → 1,028,399 |
| (700, 400) | 70 → **53** | 375,574 → **167,914** | 1,772,341 → 696,374 |
| (400, 300) | 70 → **48** | 211,236 → **106,180** | 1,353,530 → 447,561 |
| (1400, 700) | 29 → 29 | 134,971 → **119,570** | 586,893 → 530,584 |

**Both acceptance criteria that can be checked are met.** Draw calls peak at 53 against a 150
budget. And the number that was never in budget now is: worst-case *visible* triangles went
**398,574 → 240,598** against 300k. The baseline was over; the streamed city is under.

The method is corroborated rather than trusted: the baseline at the spawn measured **1,164,133**
primitives against the **1.16 M** `ARCHITECTURE.md` recorded independently for the same setup.

**Bands are 100 m / 250 m with a 400 m unload and 15 m of hysteresis**, all in
`game/tuning/streaming.tres` per hard rule 4. The unload distance is paired with the chase camera's
400 m far plane rather than tuned alone — nearer and buildings visibly vanish at the horizon,
further and it holds memory nothing draws.

**The design is split in two, and that is what makes the third criterion structural.** `P2-1` asks
that "a distant tile is rejected by its `aabb` **before** its mesh is loaded". `TileStreaming` lives
in `scripts/core/`, is pure, and takes an `AABB` and returns an int — there is no code path from it
to a file, so the rejection cannot happen after a load rather than before one. It also means the
whole decision table is testable headlessly, which is what `verify_city_streamer.gd` does.

**Resident triangles are reported, never gated, and the measurement says that was right.** The
sweep's worst case is 405,210 resident against a 300k budget, and gating on it would have failed.
But the budget is 300k *visible*, and the streamer culls to a **disc** while the renderer
frustum-culls to a **cone**: at that same point, 402k resident draws as **240k visible**. Failing a
disc figure against a cone budget would have tightened the bands by ~40% to satisfy an arithmetic
mismatch, buying LOD popping for a cost frustum culling was already paying. The tool prints the
number and names it a ceiling.

**A review pass over the finished code found four defects, and two of them were in the check
rather than the thing checked.** Recorded because "the check was wrong" is this repo's recurring
failure and it does not get less likely once the check exists.

- **The draw-call gate read the wrong sample.** The sweep tracked the resident-tile count *at the
  worst-triangle sample* rather than its own maximum. The two peak in different places and by a
  real margin — 31 tiles where the triangles peak, **37 tiles at (1114, 381)** where the tiles do —
  so `P2-1`'s only failing assertion was gating on a number that was not the worst case. Tracked
  separately now, and both places are printed.
- **The residency sweep measured a smaller city than the streamer holds.** It culled on
  `unload_distance_m`, but a tile already resident keeps its band for another `hysteresis_m`, so the
  real disc is 415 m and not 400. `TileStreaming.residency_radius_m` now says so once and both
  callers use it. Worst-case residency was 402,169 under the old sweep and is **405,210** under the
  honest one.
- **A failed tile load leaked and then repeated forever.** `load_threaded_get` is the only call that
  releases a `ResourceLoader` task — `load_threaded_get_status` does not — so a failure that skipped
  collection pinned the request for the life of the process. Worse, `_clear_pending` left the tile
  wanting its tier, so `_collect` re-requested it the next frame: one missing tile meant a
  `push_warning` and an in-flight slot burned at 60 Hz forever. Failures are now collected, and a
  `failed_tier` on the resident stops the re-request.
- **A superseded tier was instantiated rather than discarded.** The comment claimed the in-flight
  load was "discarded on arrival"; it was not — the arrival check tested only for `UNLOADED`, so a
  stale tier was instantiated, added, and then thrown away next frame, spending one of the two
  per-frame instantiation slots exactly when they are scarcest. It is dropped on arrival now unless
  nothing is drawn there yet, because a stale tier still beats a hole.

**Proven able to fail — and the first attempt at proving it was itself a false green.** Inverting
the distance bands gives a named failure and exit 1. Breaking `plan_distance_to` to measure to the
AABB *centre* instead of its nearest point reported **exit 0 and no failures** — because the edit
orphaned a local, `unused_variable` is promoted to error, the script never parsed, and `quit(1)`
never ran. This is `dea1f36` and `Q17` all over again, caught only because the result looked too
good. Re-run with the local still used, the check fails correctly: *"a camera 10 m off a tile's edge
measured 85.000 m"*. The lesson is the one already written down and worth writing again: **never
read raw `godot` output and call it a pass** — `tools/check.sh` is the only thing that can fail.

**Two findings this opened, neither of them `P2-1`'s to fix.**

⚠️ **The directional shadow costs 4.3× the main pass** — 1,028,399 primitives against 240,598 at the
worst point. `golden_hour.tscn` enables `shadow_enabled` on a `DirectionalLight3D`, which takes
Godot's default **4 PSSM cascades**, and its `directional_shadow_max_distance` is **600 m** against
the streamer's 400 m unload, so every resident tile is re-rendered in every cascade. The budget
table already says mobile is "vehicle blob shadow only" and desktop is "one cascade directional", so
the rig is off-spec at both tiers. It is `P2-6`'s, but it is now a measured number rather than a
suspicion — and it is the single largest lever left on the frame cost.

⚠️ **LOD1 is fine for buildings at closest range and destroys the thin structures.** Matched pairs
at Hennessy Road and at the Gloucester Road flyover — `build/lod-review/`, same camera, one
variable. In the canyon LOD1 is very nearly indistinguishable — the facades read the
same and the street reads the same, at 478,076 primitives against 629,975 and 120 fps against 92.
But the elevated road structure and the footbridge canopy come apart: crisp thin slabs at LOD0
become warped dark slivers at LOD1, because `INFRASTRUCTURE` geometry is long and thin and does not
survive vertex-cell decimation the way an extruded building block does. So `Q16`'s "drop LOD0 and
the bundle falls to 28 MB" is **live for buildings and not for infrastructure**, which makes it a
per-mesh-class decision in `buildings.py` rather than a per-tile one. That is a `P1-2`/`P2-6`
follow-up and the user's call at the review point.

**Where tile colliders come from — the decision `P2-1` was assigned.** Not from the streamer.
Building collision is an ETL product, not a runtime one: `create_trimesh_collision()` on a streamed
tile would build a `ConcavePolygonShape3D` from a 9.5k-triangle mesh on the main thread, which is
exactly the hitch the instantiation budget exists to prevent, and it would do it again on every tier
swap. The tiers are also the wrong shape for it — LOD2 silhouettes are visibly wrong up close, and
LOD0 is far more detail than a collision hull needs. The right answer is a fourth per-tile product
from `buildings.py`: one coarse collision mesh per tile, tier-independent, loaded once and never
swapped. That is a data-contract change and its own task. Until then buildings have no collision and
the road surface is what keeps the car honest.

### 2026-08-01 — `P2-2`'s last acceptance criterion, measured: **p99 45 µs against a 1 ms budget**

The criterion said sub-millisecond nearest-edge; the task shipped with it unmeasured and the gap
recorded rather than closed. It is closed now, inside `verify_road_graph.gd` — so it is a check that
runs on every `tools/check.sh` rather than a number someone wrote down once.

| Population | n | p50 | p99 | max |
|---|---|---|---|---|
| Whole region — 10 m lattice, 14,107 hit / 1,758 miss | 15,865 | 14 µs | **45 µs** | 191–229 µs |
| On the road — every drivable edge midpoint | 737 | 4–5 µs | 9–10 µs | 44–101 µs |

**22× headroom on p99, and the criterion is met.** Two ranges are given because they are what varied
across runs, which turns out to be the interesting part.

**Probing the whole region rather than the road is the whole design, and the numbers say so.** A
query on a centreline is won in the first ring; a query in the middle of a block finds nothing near
it and expands rings until the 60 m radius bound stops it. So the misses are the expensive
population — 1,758 of 15,865 lattice probes, 11%, which is more than the top 1% and therefore
exactly what p99 lands in. A road-only probe would have reported **9 µs and called it the answer**,
understating the real worst case by five times. Both populations are timed and both are printed.

**The gate is p99, not max, and that was not a judgement call in the end — it was measured.** Across
runs the maximum ranged **44 µs to 229 µs** while p99 moved by a single microsecond. The maximum is
a fact about what else the machine was doing; the p99 over thousands of probes is a fact about the
code. Max is printed anyway, because a pathological one is worth seeing, but gating on it would buy
a flaky check for no information.

**Proven capable of failing, twice, because in this repo that is not optional.** Tightening the
budget to 20 µs produced a named failure and exit 1. Then a genuine regression: disabling
`nearest_edge`'s ring early-exit — the optimisation whose comment claims a query would otherwise
"scan every cell it is allowed to" — moved on-road p50 from **5 µs to 56 µs** and p99 from **10 µs
to 117 µs**. That comment is now measured rather than asserted.

⚠️ **And that second test found the limit of this check: the 11× regression stayed under budget.**
117 µs is still comfortably sub-millisecond, so the gate would have passed a change that cost an
order of magnitude. This is an acceptance criterion, not a regression alarm, and the distinction is
recorded in the tool. Catching that drift means comparing the printed distribution against the table
above — which is why the numbers are printed on success rather than only on failure. Tightening the
budget until the regression fails was considered and rejected: it would invent a requirement `P2-2`
never set, and the honest place for a performance-regression gate is `P2-6`, with the device floor
in hand.

**One incidental finding worth keeping for `P2-6`.** With the early-exit disabled, on-road queries
became *slower* than region-wide ones — p50 56 µs against 48 µs — which inverts the normal
relationship. The reason is that a cell on a road holds many segments while a cell inside a block
holds none, so scanning all 49 cells unconditionally costs most where the roads are densest. The
early-exit is worth the most exactly where the car actually drives.

### 2026-07-31 — `P2-2`: the drawn carriageway width is a **contract gap**, and the overlay is what found it

`RoadGraph` lands the queries the previews were faking: one parse per scene held through a
`WeakRef` — so a scene means a parse, without pinning 6 MB for the life of the process the way
`fare_preview.gd` warned against — nearest-edge over a 25 m plan grid, lane centres, and typed
accessors. `road_preview.gd` and `fare_preview.gd` now read it instead of parsing `roadgraph.json`
twice in one scene, which is the note `P1-6` left for this task.

⚠️ **That last sentence was false when first written, and review caught it.** Both previews took
`RoadGraph.shared()` into a **local**. `RoadGraph` is `RefCounted` and the cache is weak, so the
only strong reference died when `_ready` returned and the next sibling re-parsed — `city_preview.tscn`
still read the document twice, which is exactly the cost the class exists to remove. A weak cache
only works if consumers hold a member; both previews and the overlay now do. Worth remembering for
`P3-1`, which will take the same accessor.

**`Q13` is enforced rather than described.** Only level-0 segments enter the index, so
`nearest_edge` cannot return one of the 60 off-grade edges, while `polyline_of` still serves all
797 because `P3-3`'s traffic will need them. `verify_road_graph.gd` probes **every vertex of every
off-grade edge** — 505 of them, the exact places a flyover centreline is nearest in plan to a car
underneath it. Proven non-vacuous by indexing off-grade segments on purpose: 482 of 505 probes
resolved to a flyover and the tool named edge 62.

**Three more defects came out of review, and the overlay found a fourth from the driver's seat.**
74 of the 797 edges publish `{"en": null}` for their road name, and `str(null)` in Godot is the
literal string `"<null>"` — so the `is_empty()` guard meant to substitute "(unnamed)" never fired
for 9% of the network. `has_carriageway_widths()` documented "every" and implemented "any", which
would have let a one-entry table pass the gate that exists to catch a missing one. And `_fill`
re-walked the polyline twice to re-derive the segment `nearest_edge` had already won — 14% of a
typical query and 31% on a long edge, but the real cost was that the second walk could pick a
*different* segment on a tie, leaving `t` and `forward` describing somewhere other than `point`.

**The fourth is a naming problem, not a bug, and it is worth recording.** Driving a multi-lane
street, the user observed that the green marker stays on the outermost lane whatever lane the car
is in. It does, and it should: `lane_centre` is the **placement target** — where `P2-3` spawns and
where `P3-3` will route traffic — not a tracker of the player's lane. **There is no runtime lane
concept to track.** `lanes` is authored config keyed on speed limit, not published by Road Network
v2, and nothing routes by it. The overlay called it "lane centre", which implied otherwise; it now
says what it is and reports the car's own signed offset from the centreline beside it. Building
lane tracking would have been inventing a mechanic ahead of any need for one.

**The overlay is a deliverable, and it earned that on its first run.** It draws the resolved
centreline, the nearside lane centre and the legal travel direction under the moving car, with the
same facts as text so a screenshot carries them. At the HKCEC spawn it read `edge 651 EXPO DRIVE,
t=0.599` — against `fares.json`'s published `nearest_edge 651, edge_t 0.598491` for stand `f_004`.
Two derivations that share no code agreeing to three decimals.

Then it disagreed. It reported the lane centre **1.60 m** off the centreline where
`ARCHITECTURE.md` puts the spawn at **2.56 m**, and the car 0.96 m adrift.

**The cause was a hole in the data contract, not a bug in the arithmetic.** `roadgraph.json`
publishes `width_m` as the *authored* street — `lanes × lane_width_m` — while `P1-4` draws the
ribbon at `width_m × widen_for(speed_limit_kph)`, 1.6× by default. The widening lives on the
surface style, and `config.py` keeps it there on purpose: *"the graph is a description of the city,
this is how wide and how kerbed to draw it. A change here never changes `roadgraph.json`."* So the
game had no route to the width of the tarmac it was driving on, and a lane centre taken from the
graph sat a quarter of the widening short — 0.96 m nearer the seam where opposed ribbons overlap
and a suspension ray hunts between two coplanar triangles.

**Three ways out were weighed and two rejected.**

- **Publish the widening rules in `city.json`** — rejected. GDScript would have to reimplement
  `widen_for` and `_by_fastest_rule`'s "fastest matching rule" semantics: two implementations of
  one rule across a versioned interface, which is what the contract exists to prevent.
- **Read lane geometry from the surface mesh UVs** — rejected *for this*, and worth keeping for
  `P3-8`. `TEXCOORD_0` is built for lane questions, but it answers "which lane am I in?" — a
  lookup — where `P2-2` needs "where is the lane centre?", which is the inverse and a search. It is
  also undefined exactly where it would matter most: junction caps carry `(0, 0)`.
- **Mirror the factor in a `.tres`** — rejected. Satisfies the tuning-as-data rule literally while
  creating the drift this repo keeps paying for.

**What shipped: publish the derived result, not the rule.** `surface.py` records the half-width it
already computes in `_prepare` — the one place the widening is applied — as `carriageway` in
`roadsurface.json` (schema 2). `export.py` carries it into `city.json` (schema 2) without
recomputing, because a second `widen_for` call is a second thing to keep in step with the config.
It is the same category as `tiles[].aabb`: geometry the runtime cannot derive, measured once by the
stage that produced it. The graph/surface boundary is untouched.

The result is a cross-check nothing was tuned to produce. `city_drive.tscn`'s spawn was derived by
hand in `P1-7` from `width_m × widen / 4`; `RoadGraph` now computes the nearside lane centre from
the published half-width and the overlay reports the car **0.00 m** from it.

Absence of the table is an error in `verify_road_graph.gd` rather than a fallback, because
`RoadGraph` degrades to the authored width — a wrong answer that looks like a right one. It warns
and names the rebuild command.

~~⚠️ **Not done here:** `P2-2`'s acceptance criterion says sub-millisecond nearest-edge and that is
**not yet measured**. The index exists — 2311 segments over a 25 m grid, ring search that stops as
soon as a ring cannot beat the incumbent — but no timing was taken. It belongs with `P2-6`'s
measurement pass or a probe of its own.~~ **Measured 2026-08-01 and it belonged here after all** —
p99 **45 µs** against the 1 ms budget, timed inside `verify_road_graph.gd` rather than deferred to
`P2-6`. See the entry above.

### 2026-07-31 — `Q13` narrowed: the ramps **are** in the source, and sampling them beats inventing them

`Q13` was written as though the height model had no better input available — "the source carries no
Z at all — every height in this pipeline is authored or sampled". That is true of *Road Network v2*.
It is not true of the map sheets. The user asked whether the original data contains the actual ramp
geometry, and it does.

**`INFRASTRUCTURE` is a third mesh class, and it holds the elevated road structures.** It has been
in `hong_kong.yaml`'s mesh list since `P1-2` and is already rendered into the tiles with its own
colour — the flyovers are on screen today. `DATA_SOURCES.md` mentions the class only as a *tiling
hazard* ("one of them is 1,984 m long in a single mesh"), never as a height source, which is why
nobody had looked. In the one sheet extracted to disk its 12 meshes each span **continuously from
about 3 m up to 13–32 m**. A flat deck would occupy a narrow band; a 29 m span is the ramp.

**So there are two representations of the same flyover and they disagree.** The graph puts decks at
`terrain + 6.0 m` — 9.23 to 13.56 m across the region — while the structure the player can see is
somewhere else. That is the half of `Q13` nobody had noticed: not merely that the graph has no
ramps, but that the geometry beside it does.

**A spike sampled the structures with `terrain.HeightField`** — the same class, the same query
shape, pointed at `INFRASTRUCTURE` instead of `TERRAIN(TB)`; 266,092 usable triangles across the
region's six sheets. Results against every level-1 edge in the graph:

| | `P1-4`'s blend | Sampled from the structure |
|---|---|---|
| Coverage | — | **45/45 edges, 410/430 vertices (95.3%)** |
| Median grade | 3.9% | **3.01%** |
| p90 grade | — | 7.45% |
| Segments over 12% | **10 of 39 edge ends** | **2 of 365 segments** |
| Worst | 29% | 224%, and both outliers are artefacts |

**Both outliers are the sampler, not the road.** They sit on `CANAL ROAD FLYOVER`, and a dense
21-point re-sample of one shows a **7.00 m jump inside a 2.91 m run** — a stacked deck, where
`HeightField.sample` returns the *highest* hit and so reads the upper deck while the graph edge is
on the lower one. The same mechanism biases every sampled height by a median **+1.22 m**, which is
about parapet height. Both are fixed the same way: window the sample around the expected deck rather
than taking the global maximum.

**What it does not fix, and this is why `Q13` stays open.** The step at level-change nodes improves
but does not close, and it splits by cause:

| Nodes | Count | Step today | Sampled | Resolved |
|---|---|---|---|---|
| Flyover `(0, 1)` | 31 | 6.00 m | **2.56 m** median, 4.02 m max | 22, of which only **7 under 0.5 m** |
| Tunnel `(−1, 0)` | 5 | 8.00 m | — | **0** |

Tunnels get nothing and always will: a tunnel is a void, so there is no structure mesh under it.
Nine of the 31 flyover nodes have no structure at one end either. Sampling therefore lands the
elevated network at *geometrically honest but not reliably connected*, and 15 of 22 flyover
junctions still step more than half a metre.

**And the residual step is topological, not a height error.** Walking each level-1 edge outward from
a mixed-level node: **20 of 28 start already elevated**, at a gentle 0.2–1.6% grade, which is a deck
run rather than a ramp. Only 8 begin near street level and climb. The graph simply has no edge
spanning the climb at those junctions, so there is no horizontal run to distribute a rise over and
**no height source can repair it** — the fix would have to add geometry the source never published.

> ❌ **Superseded 2026-08-01 by `P2-7`'s classification.** The observation is right and the
> conclusion drawn from it is wrong. The climb *is* in the graph; it is split across a level-0 edge
> and a level-1 edge, because the source flips `ELEVATION` partway up the ramp rather than at the
> touchdown. So a level-1 edge "starting already elevated" is not a deck run with no approach — its
> approach is the level-0 edge on the other side of the node, which is itself sitting 2.1–4.0 m up on
> the same structure. Nothing needs inventing; both halves need sampling. See the decision log.
Where the graph *does* carry the ramp the result is excellent: `CANAL ROAD FLYOVER` samples 4.62 m →
11.55 m over 254 m at **2.7%**, and 4.66 m → 11.87 m over 218 m at **3.3%**. Across all 28, no
junction edge exceeds **6.2%**. So the ceiling on this approach is set by the road network's
topology, not by the map sheet's geometry.

**The decision.** `P2-2` still takes the street-level slice — `nearest_edge` refuses off-grade
edges — because "honest but disconnected" is worse for a driving game than "clearly not part of the
map". What changes is the price of the full fix. Relaxing heights across the graph was the
open-ended option; it now has a measured starting point that needs no new dependency, no new
download and no new parser. Three things it will still have to do: window the sample to kill the
Canal Road artefacts and the parapet bias, handle tunnels by some other means, and tie the ramp ends
to street height at the junctions as its own step.

**A correction while measuring.** `Q13` claimed "a third of the region's road area cannot be driven
onto". Measured from `roadgraph.json`: **60 of 797 edges are off-grade (7.5%), 11.02 km of 56.15 km
by length (19.6%), and 93,208 m² of 400,146 m² by carriageway area (23.3%)**. The register row is
corrected below.

### 2026-07-31 — CI runs `tools/check.sh`, and **cannot** check the generated assets — closes `Q17`

`.github/workflows/ci.yml`, on every push to `main` and every pull request. Two jobs: `ruff check`,
`ruff format --check` and `pytest` on Python 3.11 and 3.13; and `tools/check.sh` against a pinned
Godot `4.7.1-stable`.

**CI runs the script, not its steps.** Repeating `--import` and the warnings sweep as YAML steps
would have been the obvious shape and would have been wrong for the reason the script exists —
Godot exits `0` through a parse failure, so YAML steps would go green on a broken build. The two
env overrides the script already had (`GODOT=`, `GDFORMAT=`) turned out to be exactly the seam CI
needed, since the default `gdformat` path points at the README's repo-root venv.

**Three of the six checks cannot run there.** `game/assets/generated/` is gitignored build
output; a fresh checkout has no city, and `verify_city` exits `1` on the missing manifest —
confirmed by cloning the repo to a scratch directory and running each step. So the workflow sets a
new `VERIFY_GENERATED=0`, and the script prints a `SKIP` line naming all three tools and stating
that the contracts were not checked. Silence was the alternative and is not available here: a check
that reported nothing because it had nothing to look at is the `dea1f36` failure, and this script
is the thing that exists to stop it.

Formatting, the import and the warnings sweep all cover the whole tree without a built city, so the
loss is bounded and named. Giving CI a city means running the ETL there — 320 MB from a government
server, per push. Declined. If the contracts ever need CI coverage, it is a scheduled job with the
source cache restored, not a per-push one.

**The skip's own guard was a false green, which is the joke this repo keeps not getting to make
once.** `if ((VERIFY_GENERATED))` is the obvious bash and is a trapdoor under `set -u`, measured:
`VERIFY_GENERATED=true` evaluates the string as an arithmetic expression, looks up a variable named
`true`, dies with `unbound variable` **and exits 0**; `=1x` reports "value too great for base",
returns non-zero, falls into the skip branch, and prints `All checks passed`. So a typo in the one
knob that turns checks off would have turned them all off, silently, green. Now compared as a
string with only an exact `0` skipping, so anything unrecognised runs the checks. `((failed))` six
lines down is untouched and fine — its operand is script-controlled, never environment.

**The `godot` job does not install the ETL.** `pip install -e "etl/[dev]"` is the obvious way to
get `gdformat` and drags in pyogrio's bundled GDAL, numpy and pyproj: ~70 MB of geodata stack to
format GDScript. It reads the `gdtoolkit` pin out of `etl/pyproject.toml` with `tomllib` instead —
one source of truth for the version, without the payload. That change also forced dropping the pip
cache from that job: `setup-python` keys its cache on OS + Python version + dependency-file hash
with **no job component**, so the two jobs shared a key while installing different things, and
whichever finished last would poison the other.

**Python is a matrix of 3.11 and 3.13** — the floor `etl/pyproject.toml` declares and the version
in use locally. Both ends, or neither is checked. `ruff` runs from the repo root, never `etl/`, for
the reason the root `ruff.toml` exists at all.

### 2026-07-31 — GDScript linting: the engine's own warnings, `gdformat`, no `gdlint` — and **the checks never had exit codes**

Evaluated `gdtoolkit` (Scony). Adopted `gdformat`, declined `gdlint`, and turned on Godot's own
warnings instead. The configuration and what was left out live in `docs/ARCHITECTURE.md`
"GDScript warnings" and "GDScript formatting"; this records how it went, because it went badly
before it went well.

**`gdlint` declined on its numbers:** 17 problems over 24 scripts, 16 of them
`class-definitions-order` across four preview scripts — reordering commented files for no
behavioural gain, the churn `CLAUDE.md` prohibits.

**The find was that `game/project.godot` had no `[debug]` section at all**, so Godot's own GDScript
warnings had sat at defaults since `P0-3` — `untyped_declaration` among them, off. Static typing is
a hard `CLAUDE.md` convention that `gdlint` has no rule for and, being a grammar-level tool with no
type resolution, could never have one.

**Two things were wrong with the first version of this, and both are the same mistake.**

*The gate broke two of the three verify tools, and the breakage reported success.*
`shadowed_variable_base_class` fires on `root` in `verify_tiles.gd` and `verify_road_surface.gd` —
both `extends SceneTree` — and on `basis`/`transform` in `greybox_builder.gd`. Those scripts then
failed to *parse*, so `_init` never ran, so `quit(1)` was never reached, and the SceneTree exited
`0`. Eight violations across three files, all shipped green. The claim "all twenty passed, the gate
cost zero code changes" was false, and it was published in five places. Renamed to `scene_root`,
`frame` and `placement` — the warning was right: in a file whose own comments warn about `Basis`
conventions, a local `basis` shadowing `self.basis` is worth forbidding.

*It was verified with `godot … && echo PASS`.* Godot exits `0` when a script fails to parse, when a
warning is promoted to an error, when a dependency will not compile. The verification could not
have failed. This is `dea1f36` — "wrong in the safe-looking direction is the one failure mode a
check must never have" — reintroduced by the commit that came directly after it, through a door
that commit did not close.

**So `tools/check.sh` now exists**, and is the only thing in the repo that can fail. It greps
Godot's output for compile failures and supplies the exit code the engine will not, checks the
process status too, and runs `gdformat`, the import, a per-script warnings sweep and the three
verify tools. Tested against five planted defects — untyped variable in an autoload, in a
scene-only script, and in an autoload-referencing script; a shadowing regression; bad formatting —
all exit `1`, clean tree exits `0`.

**The sweep is separate from `--import` because `--import` does not do the job.** Measured: an
untyped variable planted in `greybox_builder.gd` went unreported, because the import step compiles
autoloads and what they reach, and that script is only reachable through a dev scene. Per-script
`--check-only` covers the rest — but only when run with `game/` as the project directory. Run from
the repo root, `res://` does not resolve, every script analyses clean, and the sweep passes having
checked nothing. That trap cost a wrong measurement on the way here.

**Level 1 is invisible headlessly**, which shaped the config: only level `2` reaches stdout, so a
warning left at `1` is decoration in a workflow that never opens the editor. Everything is `2` or
at its engine default.

**A tool was written and thrown away.** `verify_scripts.gd` walked `res://` and `load()`ed every
script to force full compilation. Autoload identifiers do not resolve under `--script`, so it
needed a deferral list; the list needed a transitive closure over `preload`; and then
`drive_harness.gd` turned out to reference `VehicleController` by `class_name` rather than by path,
which would have needed class-name resolution too. Deleted at that point. The `--check-only` sweep
gets the same coverage for four lines of shell.

**Not a bug-catcher**, and `docs/ARCHITECTURE.md` says so: none of the four `P0-5b`/`P0-5c` bugs
would have been caught by any of this.

**Open question — `Q17`:** still no CI, so `tools/check.sh` runs only when someone remembers.
*(Closed the same day by the CI entry above.)*

### 2026-07-31 — `P1-7`: the manifest is the **only** route to the tiles, and the georeference is now checked by the engine

**The listing had to go, and it was not a style preference.** `generated_tiles.gd` found tiles with
`DirAccess.get_files_at("res://assets/generated/tiles")`. In the editor `res://` is a folder and
that works; in an exported build it is a PCK archive Godot's virtual filesystem will not enumerate,
so the call returns an empty array, the loop does nothing, and the game renders an empty city
**without a single error**. It would have looked like a content problem in the first device build.
The file is deleted rather than deprecated, so nothing can reach for it again; `CityManifest` is the
one route, and `verify_tiles.gd` now iterates the manifest too — checking the shipped set by
construction rather than whatever happens to be on disk.

**The gate's word is "georeferenced", so something had to be able to disagree.** Until now nothing
could: the ETL measures its own arithmetic and never sees an importer, and `verify_tiles.gd` checks
the mesh contract — draw calls, vertex colours, textures — which says nothing about *where*. So
`tools/verify_city.gd` measures each imported LOD0 mesh and compares it to the `aabb` `export.py`
recorded. **All 65 tiles agree to within 1 cm.** The tolerance is generous against what actually
causes drift — float64 measurement into float32 storage costs about 0.1 mm at Wan Chai's 1.7 km
extent — and tight against what it is looking for, since an axis flip, a unit scale or a dropped
offset moves a corner by metres.

It was proven non-vacuous before being believed, the same way `P1-6`'s validator was: nudge one
tile 0.5 m east, point `fares` at a file that is not there, shrink `bounds_game` by 100 m. Fifteen
findings, exit 1, nothing spurious, and the offset reported as *0.500 m out*. Two real bugs in the
tool surfaced on its first run — it grew *both* boxes before an `encloses` test, which cancels out
and leaves no tolerance at all for the millimetre rounding that separates `bounds_game` from the
tile AABBs it was summed from; and it read `global_transform`, which returns identity outside the
tree, and a `--script` run has no tree. Transforms are now accumulated by hand, which also means a
transformed importer root would be caught rather than silently applied.

> ⚠️ An earlier version of this entry said `encloses` "does not treat a shared face as enclosed".
> That is false — measured on 4.7.1, an AABB encloses an identical one, and growing both by the
> same epsilon still returns true. The code was right for a reason the comment got wrong, which is
> its own kind of latent bug: the next person to touch the tolerance would have reasoned from it.

**What it cannot check is z-fighting**, and that is stated in the tool rather than glossed. There is
no *headless* assertion for it — `--headless` loads the dummy rasteriser, so `get_texture()` returns
nothing at all. A **windowed** run can measure it, though, and did: render Hennessy Road, nudge the
camera 2 cm, diff the frames. A fighting surface flips wholesale under a sub-pixel move; anti-aliased
edges change a little. **653 of 921,600 pixels flipped — 0.071%**, and the diff image is sparse
dotted lines along silhouettes and kerbs, with no flat region flipping. That is evidence, not proof:
it covers one camera at one place. Flying around is still the acceptance.

**A camera-framing bug surfaced while taking the gate screenshot, and it was mine.** The preview
scenes opened at the origin looking at the horizon. `_ready` runs children-first, `Tiles` is the
first child and `Camera3D` the last, so `built` was emitted before the camera connected — reaching
nobody, with no error to notice: the connection existed, it was made too late. It has been quietly
false since `P1-4` gave the camera something to frame, and the docs claimed the opposite. Emitting
deferred fixes it after every `_ready` in the scene, so it survives a node reorder as well.

**The sync is manifest-driven, not a directory copy.** `tools/sync_generated.sh` asks the ETL what
`city.json` names (`python -m pipeline.export … --list`) and copies that. A `cp -R` of the output
directory would ship `buildings.json` and `roadsurface.json`, which are stage intermediates and
explicitly not part of the contract. It also deletes tiles a previous build left behind — nothing
else in the project would ever notice them, because every check starts from the manifest and the
manifest has forgotten them, so they would sit in the bundle costing megabytes against `Q16`.

**The three `generated_*.gd` locators keep their constant paths, for now.** They are dev-scene and
verify-tool plumbing that predates the manifest, and routing them through it today would be churn
in code `P2-2` and `P3-1` are about to replace. What is not deferred is the drift: `verify_city.gd`
asserts each locator's constant equals the path `city.json` declares, so the two definitions cannot
quietly diverge in the meantime.

### 2026-07-31 — `P1-6`: the manifest **names** the other documents, and the export stage **checks** them

Two decisions, and the second is the one with teeth.

**`city.json` references rather than inlines.** The alternative was tempting for exactly one
reason — the previews parse `roadgraph.json` twice in the same scene — and it was the wrong reason.
`RoadGraph` wants the graph when it starts; `CityStreamer` wants the tile list at load; `FareSystem`
wants the fare nodes when a shift begins. Merging them would make every consumer parse all three to
learn any one, and each is separately versioned in the contract, so a change to fare nodes would
bump the schema on the document that carries the tiles. The duplicate parse is `P2-2`'s to remove
by owning the graph, not the manifest's to remove by absorbing it. The comment in `fare_preview.gd`
that predicted otherwise has been corrected rather than left to be inherited as fact.

**`bounds_game` is the union of the content, not the region rectangle.** These differ by more than
rounding: the region is 1650 × 887 m and its geometry spans **1668 × 942 m**, because a building is
assigned to a tile whole and is allowed to overhang, and because the road ribbon is drawn outward
from centrelines that run to the boundary. The rectangle is a build-time concept — after clipping,
what exists is the content. A camera framed on the rectangle, or a spatial partition sized to it,
would silently clip real buildings along every edge.

**The stage validates what it wrote, and that is the actual deliverable.** `P1-6` reads as plumbing;
the plumbing took an afternoon and the check is what will earn its keep. Four classes of error
exist that **no individual stage can see, because each document is internally valid in all of
them**:

| Failure | How it happens |
|---|---|
| A fare node names an edge the graph does not have | Re-run `roads` and every `nearest_edge` written before it points at a different street |
| A tile whose GLB was never written | A build interrupted between the manifest and the mesh |
| A document from another region | Build a second region over the first one's output directory |
| Geometry outside the declared bounds | A manifest carried over from a previous, smaller run |

Each is a real sequence rather than a hypothetical, and each is now one line of output naming the
file and the reason. Verified against the real region by breaking all three of the first kinds at
once: three findings, exit 1, and nothing else reported.

**Reproducibility was measured, not assumed.** The region was rebuilt from an empty `out/` and
diffed against the previous build: **every one of the 199 files byte-identical**, the sole
difference in the entire tree being the `generated_utc` stamp. That makes "did this change
anything?" answerable by `diff` for every future ETL change, which is the property that made the
`P1-5` refactors safe to do at all. `build_region` takes the stamp as an argument so a test can pin
it.

The orchestrator calls each stage's own `main` with the arguments the documented per-stage command
would pass. Composing them any other way — importing `build_region` directly — would create a
second code path that could drift from the one people actually run, and the drift would surface as
a full build quietly differing from a partial one. A non-zero exit stops the chain, because every
later stage reads what an earlier one wrote.

Opened `Q16`: one region is 102.6 MB of a 200 MB bundle budget, and 73% of that is LOD0.

### 2026-07-31 — `P1-5`: fare nodes keep the **kerbside** position, and carry three fields the contract did not have

Three decisions, all forced by measurement rather than taste.

**`pos` is the source position, not the snapped one.** 11 of the 29 nodes lie outside even the
1.6×-widened carriageway, because the published points are on the pavement and `P1-4` draws from
centrelines. The tempting fix — move each node onto the road so a marker never floats — throws away
the only thing the source actually surveyed. The kerbside is where the passenger stands; where the
taxi stops is derivable from `nearest_edge` and `edge_t`, and the reverse is not. Only the height
comes off the road, because the source has none and the terrain eight metres away might be a podium.

**`edge_t`, `pickup` and `dropoff` were added to the contract.** `nearest_edge` alone names a road
that can be 200 m long, which would leave `P3-1` redoing the projection this stage just did.
`pickup`/`dropoff` exist because a quarter of the published points are **drop-off only** — 66 of 275
territory-wide — and flattening that would let a player hail a fare somewhere no taxi may stop for
one. Both are free here and expensive later: `P1-6` freezes this shape into `city.json`. No
`schema_version` bump was needed because no `fares.json` had ever been written.

**The category table lives in config, and its *order* is validated.** `Status_EN` is free text with
sixteen spellings, several carrying an operating-time note after a newline, so matching is
first-hit-wins over substrings. That makes rule order load-bearing in a way that fails silently:
`DF` before `PU/DF` files every pick-up point as drop-off only and still produces a complete,
plausible `fares.json`. `load_city` now refuses a table where an earlier rule always shadows a
later one. An *unmatched* category raises rather than defaulting, on the same reasoning as
`deck_height_m` — these datasets are republished twice a year, and a new category quietly filed
under `urban` is a premium fare type missing from the game.

**A bug found on the way, in `P1-3`'s code rather than this stage's.** `clean_text` normalised to
NFKC, which is a *compatibility* fold: it rewrites the full-width brackets Chinese sets its
parentheticals in as ASCII. Harmless for road names, wrong for 98 of the fare-node names, which go
on a bilingual HUD. Now NFC, with NFKC used only for the null-sentinel comparison. Verified by
re-running `P1-3`: `roadgraph.json` is byte-identical.

### 2026-07-31 — `Q8` closed: **the city itself is the fun**, and that is the whole bet

The user drove `scenes/dev/city_drive.tscn` and returned the verdict that driving an HK-like map is
a fun enough gimmick already.

**This is the question the project has been carrying since `P0-5`.** That test cleared the handling
and explicitly could not clear the premise — a grey box can tell you whether a car feels good, and
nothing about whether *this city* is worth driving. The whole ETL slice, `P1-1` through `P1-4`, was
built on an unvalidated bet: that accurate Hong Kong massing is itself the product. It is answered
now, and it is answered the right way round — by driving the real thing rather than by arguing
about it.

**What it licenses.** The core direction needs no revisiting. `docs/ART_DESIGN.md`'s first line —
"accurate city, toy vehicles", recognition is the product — is now a measured position rather than
an assumption, which is what makes the expensive half of that trade (accurate massing, real street
widths, real one-way directions) worth what it cost. It also strengthens the commercial argument
already in the risk register: if recognition is the product, the city-agnostic ETL is the scaling
answer, because a second city is a YAML file and a fun-enough gimmick again.

**What it does not license, and the word matters.** *Gimmick* is the user's own, and it is accurate
rather than dismissive — a gimmick carries a first session. It says nothing about the tenth. So the
`Q8` risk is retired and replaced rather than deleted: the register now carries "novelty does not
survive the first session" in its place. The mitigations do not change, because they were already
the plan — `P3-*` is where the fare loop has to earn a second session, and `P3-9` is where real
Hong Kong drivers say whether the recognition holds up to people who know the streets. The failure
mode to avoid is reading this verdict as covering those.

One process note worth keeping: the verdict cost one dev scene assembled from parts that already
existed — `P0-5`'s car and camera, `P1-2`'s tiles, `P1-4`'s collider. `Q8` asked for "the cheapest
build that lets the user judge", and the answer turned out to be *no new build at all*, only
wiring. It was worth asking in that form.

### 2026-07-30 — `P1-4`: the road surface is **one mesh**, capped per level, and never merged

Four decisions came out of this stage, all of them settled by measuring the emitted graph before
`surface.py` existed rather than by choosing and then discovering.

**One mesh for the region, not tiles.** The buildings are tiled at 150 m because they are 989k
triangles and the streamer needs them by distance. The whole road network is **28,423 triangles** —
a fortieth of that — and it is on screen whenever the player is. Tiling it would buy nothing but
seams and 65 draw calls in place of one.

**Junctions are filled by the convex hull of the arms' corners.** Each ribbon stops one half-width
short of the node and the hull of the corners it leaves fills the middle. The property that makes
this right is convexity: the hull's boundary passes through every arm's two end corners, so the
mouth between them is inside the cap by construction — no gap is possible — and the hull stops at
the kerb line rather than spilling into the corner between two streets, which is pavement. Measured
on the region: **393 of 393 single-level junctions covered** under a 60-point sample inside the
junction radius. Three flagged initially; all three were T-junctions where the sampling disc
reached into the 175° sector that has no road in it.

**Capped per elevation level, which is the opposite of how `P1-3` keys nodes — and right for the
opposite reason.** A node exists so a flyover and the ramp under it stay one network. A junction cap
is a piece of tarmac, and there is none between a street and the tunnel roof 8 m below. This is
where `Q13` was found.

**Opposed carriageways are drawn twice and left overlapping.** See the Lockhart entry above: the
inherited decision dissolved on measurement.

The one thing that needed real geometry work was self-intersection. A corner tighter than the road
is wide has no inner offset curve — the naive one crosses itself, which renders as an inverted
sliver and is invisible to a one-sided collider. Wan Chai has such corners: a slip road off Hung
Hing Road loops at a **5 m radius** while the widened carriageway is 10.2 m across. Three repairs
were measured against each other:

| Repair | Folds left | Cost |
|---|---|---|
| Simplify harder before offsetting | 8 of 89 at a 1.02 m tolerance | 43% of the region's segments, and visible on curves |
| Cap the width to the local turning radius | 1 | **Pinches the carriageway to zero** at 24 places |
| Hold the inner boundary still where it would reverse | **0** | 93 collapsed quads out of 5,188, dropped at build |

The third is also what the offset of a too-tight corner actually *is*: the inside stops while the
outside sweeps past. It touches neither the centreline nor the width. Four triangles covering
0.53 m² still fold at the region's single sharpest hairpin; the stage counts and reports them every
run, so the number is tracked rather than assumed away.

**Collision ships in the asset.** The mesh is named `road_surface-col`, which Godot's importer reads
as "build a static trimesh collider from this". `game/tools/verify_road_surface.gd` confirms it
imported, alongside the draw-call, vertex-colour and no-texture checks — all engine-side facts that
neither the ETL nor its tests can see, which is the same gap `verify_tiles.gd` was written to close.

### 2026-07-30 — `Q12` closed: the published road directions **match the street**

User verdict after flying the road-graph preview: Jaffe Road runs east, as `roadgraph.json` says.
That clears `P1-3`'s fourth and last acceptance criterion.

**Recorded as a decision rather than just an answer, because of what now rests on it.** Until this
was checked, nothing established that `TRAVEL_DIRECTION` plus the digitised vertex order actually
described the road on the ground — only that the ETL reproduced them faithfully. `P3-3` traffic and
any routing can now take the source's directions as authoritative instead of as a first draft to be
corrected street by street. That is the difference between a data import and a hand-authored map,
and it compounds across Causeway Bay and every city after.

Not a blanket warranty: one street was checked, and the source's *geometry* is separately known to
be quirky (dual carriageways as opposed one-way pairs, one centreline densified to 0.4 mm
segments). The claim is about direction, on the streets `PLAN.md` named.

### 2026-07-30 — `P1-3`: `ELEVATION` is **not** part of a node's identity

This reverses an implementation note in `DATA_SOURCES.md` that had survived since `P0-2`: "two
edges may only form a junction if their `ELEVATION` values match." It sounds obviously right — a
flyover must not become a junction with the street it passes over — and it breaks the network.

**Measured on the real region.** All 36 endpoints where two levels meet are **ramp touchdowns**:
`HUNG HING ROAD FLYOVER` at level 1 meeting itself at level 0, `WAN CHAI INTERCHANGE` (1)↔(0),
`FLEMING ROAD` (1)↔(0), `VICTORIA PARK ROAD` meeting an unnamed level-1 ramp. Applying the rule:

| Node key | Nodes | Components | Largest |
|---|---|---|---|
| position | 599 | 6 | 583 |
| position + `ELEVATION` | 635 | **24** | **389** |

A 163-node elevated island cut adrift, which is most of the Wan Chai Interchange and the Canal Road
Flyover — the most interesting driving in the region, and the reason the region was chosen.

**The hazard the rule was aimed at does not exist here**, because nodes are formed only where
centrelines share an *endpoint*. A flyover crossing over a street shares no vertex with it, so no
junction was ever going to be invented. The rule is correct about crossings and wrong about
junctions, and the two were conflated.

### 2026-07-30 — `P1-3`: roads are **clipped** to the region, where buildings are not

`P1-2` assigns a building to a tile whole and lets it overhang, because splitting a mesh at a
boundary leaves an open shell and half a building popping in and out. Roads take the opposite rule
and it is not an inconsistency: **a polyline cut in two is two polylines**, with nothing to seam
and no shell to open. The cut point becomes an ordinary endpoint node, which is what a map edge
should be anyway.

It is also not optional. The geodatabase filters on bounding box, so the Central–Wan Chai Bypass is
selected because its box grazes the region and then runs **570 m out into the harbour**. Measured
before clipping: **14.2% of the region's road length — 9.3 km of 65.6 km — was outside the region**,
and `P1-4` would have built ribbon mesh for all of it. After clipping, polylines span exactly
0…1649.6 × 0…886.9 m.

**Two consequences worth carrying forward.** One source feature can become several edges, so turn
restrictions resolve across every combination rather than a single id lookup. And clipping removed
the last of the terrain-sampling gaps: 46 vertices had no ground under them because they were
outside the sheets, and now none are.

### 2026-07-30 — `P1-3`: **lane counts are authored, not published**

`ARCHITECTURE.md`'s provenance table implied `lanes` came from "Road Network v2 attributes". It
does not. Verified against every field of every layer in the published data specification: the
dataset has **no lane attribute anywhere**. What it does carry is a signed speed limit on the 10%
of edges that differ from the urban default, which is a decent proxy for expressway versus street.

So `roads.lanes_default`, `roads.lanes_by_min_speed_limit_kph` and `roads.lane_width_m` are city
config, and the table now says so. `P1-4` applies the playability widening on top; this is the
number it widens *from*, and it is a guess with a documented basis rather than a measurement.

### 2026-07-30 — Region placement: local origin **plus** a recorded `city_offset`

User call, resolving `Q10`. Regions keep their own local frames; `city.json` gains a `city_offset`
that translates a region-local position into a city-wide frame. Full reasoning under *Open
questions*; the short version is that a single city-wide origin would put Wan Chai ~38 km out,
where float32 quantises to ~3.9 mm — about 8% of the vehicle's 50.6 mm suspension sag, on a
`Transform3D` Godot stores as float32.

**The load-bearing constraint is that a city's declared `bounds` never change.** Every region's
offset is measured from them. They are declared in config rather than derived from the regions that
exist, because a derived frame would move each time a region was added and silently relocate
everything already published. Enforced three ways: a do-not-change warning in `hong_kong.yaml`,
a loader check that every region lies inside the city bounds, and a test asserting the city frame
is unchanged by adding a region.

Ships in `schema_version: 1`, which is the point of settling it before `P1-6` writes the first real
`city.json`.

### 2026-07-30 — `P1-2` terrain: **measured, and not affordable as it ships**

Answers the three questions the "keep it and evaluate in place" decision below set. Measured on the
real six sheets, after clipping to the region.

| | Whole region | Budget |
|---|---|---|
| Terrain triangles | **404,669** | <300k *visible*, everything included |
| Terrain texture | **224 MB** of JPEG, 6 × 7531 × 6031 px | <128 MB texture memory |
| As ASTC 4×4 | ~272 MB VRAM (272 megapixels) | — |
| Emitted GLBs | **267 MB** — 224 MB texture + 43 MB geometry | — |
| Bundle contribution | 267 MB on its own | <200 MB total (iOS cellular) |

Clipping to the region removes triangles but not texture: each sheet's JPEG is carried through
whole so its UVs stay valid, which is why the texture figure is the full 224 MB either way.

So it fails on all three counts at once, by roughly 2×. That is not a close call and no amount of
LOD tiering fixes a texture budget.

**It is not hopeless, though, and the failure is entirely in the resampling that was never done.**
The source is ~10 px/m — survey resolution, for ground seen at 60 km/h. At 2 px/m the whole region
is ~5.9 MPix, about 6 MB as ASTC, which is affordable. Geometry decimates the same way: running the
existing `mesh.collapse` over it gives 196,721 triangles at 2 m cells and **88,081 at 4 m**, though
clustering moves UVs and a photographic texture will smear where it does.

**Two things keep the terrain in the pipeline regardless of whether it is ever rendered:**

1. It is a **height field**, and `Q11` — opened by this same task — needs one. Road Network v2 has
   no Z, and ground level in Wan Chai is ~4 m above the datum, not 0. Sampling the terrain under
   each road node is the best answer to that, and it costs nothing at runtime.
2. Judging "does photographic ground read wrong next to flat-shaded massing?" still needs eyes on
   it. `--terrain` emits it as a separate, textured, evaluation-only output for exactly that.

**Not decided here:** whether to ship it at all. That needs the visual judgement, and now also a
resampling pass, which is Pillow-shaped work that does not belong inside `P1-2`. The tile output
deliberately contains **no textures at all**, per the task's acceptance criteria, so nothing about
the buildings depends on the answer.

### 2026-07-30 — `P1-2`: vertex clustering for LODs, and whole-mesh tiling with one exception

Three choices worth recording, all validated on the real data.

**Vertex clustering, not quadric decimation.** The source is extruded footprints, so clustering
keeps silhouettes blocky and axis-aligned — which *is* the art direction, where quadric decimation
would smooth the corners and fight it. It is also robust on triangle soup, which this is: unwelded,
non-manifold in places, no shared topology between buildings. And its aggressiveness is one number
in metres, so the tiers stay tuning data in city config (hard rule 4). Measured over the region:
**989,212 → 400,139 → 183,773 triangles** at 0.0 / 1.5 / 4.0 m cells.

**The cluster key includes the facing, not just the cell.** Merging on position alone averages a
wall normal into the roof normal above it and rounds off the faceting the whole style rests on.
With facing in the key, LOD0 is an *exact* weld — every surviving vertex is a source vertex, and
still worth doing because the source repeats every vertex per triangle.

⚠️ "Lossless" is precise about **positions**, which are reproduced bit for bit. It was first
implemented as a cluster mean, which is not the same thing: summing k equal doubles and dividing
by k need not reproduce them. Taking a representative instead fixed that, and moved LOD0 normals
by up to one float32 ulp (1.5e-08) in 60 of 65 tiles — invisible, but a real change of bytes, so
recorded rather than described as neutral.

**Meshes are assigned to tiles whole, except those too big for a tile.** Splitting a building at a
tile boundary leaves an open shell and makes half of it pop as the streamer loads one tile and not
its neighbour. But the source contains elevated road structures **up to 1,984 m long in a single
mesh**, and whole-mesh assignment handles those two ways, both wrong: one whose centre falls outside
the region vanishes entirely — taking a viaduct that crosses the whole map with it — and one whose
centre falls inside gives a 150 m tile a 2 km bounding box, defeating distance-based streaming.
Oversized meshes are partitioned by triangle instead. Nothing is cut, so the pieces abut exactly.

**Godot needed a fix the ETL could not make.** Godot 4.7's glTF importer reads `COLOR_0` into the
mesh but leaves `vertex_color_use_as_albedo` off, so every tile imports as a white block — with or
without a material in the file. Nothing in the glTF can express it, because there `COLOR_0` always
multiplies base colour. Corrected by a post-import script wired up as a project-wide importer
default; per-file would not survive a fresh clone, since generated assets are gitignored. Separately
measured: the `"normalized": true` flag on the colour accessor is load-bearing — drop it and Godot
reads every colour as 1.0 and the whole city renders white, silently.

### 2026-07-30 — Game-space origin: the region's **north-west** corner

User call, resolving `Q7`. Recorded here as a locked decision; the full reasoning and the measured
corner positions are in the `Q7` section under *Open questions*.

**The sign of Z was never the free part.** Godot is right-handed and Y-up, so rotating `+X` by 90°
counter-clockwise about `+Y` lands on `−Z`: if east is `+X` then north must be `−Z`, or the city is
mirrored. Only *where zero sits* was a choice, and it is a pure translation.

**North-west, because the forced Z sign means anchoring north is the only way to keep the region in
the positive quadrant.** Tile indices then run `(0,0)`…`(10,5)` rather than `(0,0)`…`(10,−5)` —
natural numbers, row 0 at the north, as in a raster or a map sheet. The rejected south-west origin
is the GIS bbox convention and was defensible; it lost on negative tile indices being a papercut
paid every time anyone writes a filename, a `Vector2i`, or a debug print.

One line in `GameTransform.from_bounds` — origin northing now **ceils** `max_northing` where
easting floors `min_easting`, rounding outward so offsets inside the region stay non-negative.
`ARCHITECTURE.md`'s `bounds_game` example turned out to be correct already, which is what suggests
the formula section had drifted rather than two deliberate choices colliding.

Opened `Q10` (per-region vs per-city origin) and surfaced a data-contract requirement: clipping to
the region bbox before indexing, since fetched sheets extend past all four edges.

### 2026-07-30 — `P1-2`: **keep the textured terrain mesh** and evaluate it in place

User call, resolving the question `P0-1` left open. Each sheet ships one terrain mesh with a JPEG
texture, and the alternative was discarding it unseen on the grounds that `P1-4` generates the road
surface from the road graph anyway.

**Keeping it is the cheaper way to find out.** The terrain is already downloaded — it is inside the
sheet zip either way — so the only cost is import time and a decision later. What it might buy is
the ground *between* the roads: pavements, the harbourfront, Victoria Park. What it might cost is
80 MB of texture against a <128 MB budget, plus 250,911 vertices per sheet, plus a visual clash
with flat-shaded buildings.

**Judge it against three things when `P1-2` lands:** whether it z-fights or gaps against the `P1-4`
road ribbon, what it costs in texture memory across six sheets, and whether photographic ground
reads as wrong next to untextured massing. Discarding it later is a one-line change in the importer;
this is a reversible decision taken in the cheap direction.

### 2026-07-30 — `P1-1`: the fetcher derives its own tile list

`fetch.py` handles two source shapes — fixed-URL (roads) and index-derived (buildings) — because
that is what the publishers offer, and the second shape is what keeps hard rule 3 intact. The
pipeline knows "some feature property holds a download URL"; that it is called `Format_glTF` is
config.

**The six sheets are derived, and they match.** Intersecting the region bounds with the 3,456-feature
index selects exactly the six `P0-1` recorded by hand — `11-SW-9D/10C/10D/14B/15A/15B`. Nothing in
config names them. That agreement is the real result: the bounds, the datum and the index all line
up, and a bounds change now re-derives the set rather than needing a doc edit.

**The index endpoint is stable and public**, which `P0-1` did not establish — it had only a manual
portal download. `https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=…&format=geojson&layer_name=…`
returns bytes **identical by SHA-256** to the portal's download, and it is parameterised by dataset
rather than baked per-dataset, so it generalises. Found in the portal's own ISO 19139 metadata
record. `P1-1`'s "fresh clone can fetch from scratch" criterion depends on this.

**Decisions worth knowing:**

- **Caching is fetch-once, not fetch-if-changed.** CLAUDE.md fixes the snapshot, so re-running must
  not quietly adopt upstream's new month of road data. `--force` takes a new snapshot; because the
  index is itself a cached artefact, revisions stay pinned until you ask for them.
- **`REVISIONDATE` is per sheet**, so a re-snapshot only re-downloads sheets that actually moved.
- **Downloads are atomic** — write to `.part`, then `os.replace`. Without it an interrupted 44 MB
  sheet leaves a truncated file that every later run treats as complete. The manifest's size check
  is the second line of defence and is regression-tested.
- **The API key is never written down.** URLs are read from the fetched index at run time, and
  everything recorded in the manifest passes through `redact()`, which strips the query string.
  Tested. `etl/sources/` is gitignored too, but a credential that is never recorded cannot leak from
  a pasted build log.
- **Bounds are reprojected before comparison, never compared across datums.** `test_fetch.py` pins
  this with a sheet that only the HK1980 misreading selects — the ~304 m error made observable as a
  wrong download rather than as a wrong number.
- **Edge contact counts as overlap.** Sheets tile the territory edge to edge, so a region boundary
  landing exactly on a shared edge must pull both neighbours rather than fall down the crack.
- **A malformed index feature only fails the build if the region needs it.** The index is
  territory-wide; one broken sheet in a district we never visit is not our problem, and one we do
  visit must not be skipped silently.
- **`--dry-run` still fetches the index**, and it is the one thing that does. Without it a dry run on
  a cold cache cannot name a single tile, which is the only question it is asked.

**Surfaced, not fixed:** the two road formats in config are redundant and differ 31× in size. See
`Q9`.

### 2026-07-30 — `P0-1`: building data is **fully scriptable**; the top data risk is retired

Reverses the `P0-2` finding that "the top data risk has moved from roads to buildings." That
conclusion came from reading the CKAN resource list, which genuinely does only point at interactive
portals — and stopping there. **Opening the portal's own Downloads panel tells a different story.**

**The CSDI portal serves a sheet index, not the models.** For the non-textured dataset it offers
FGDB / GeoPackage / GeoJSON / GML / SHP / KML — GIS vector formats, which looked wrong for 3D
buildings and is what prompted a closer look. The payload is a territory-wide index of **3,456
sheet polygons**, and every feature carries direct download URLs:

```
SHEETNO      11-SW-10C
Format_glTF  https://download.map.gov.hk/api/3d-zip/GLTF0/11-SW-10C.zip?key=…
REVISIONDATE 20250929
```

One public key covers all 3,456 sheets — not per-user, not per-session. **It must not be committed
anywhere.** `P1-1` fetches the index and reads URLs out of it, so a rotated key costs nothing and
the sheet list is derived rather than hardcoded. `REVISIONDATE` is per sheet and is the natural
cache key for idempotent re-runs.

**Verified by actually downloading `11-SW-10C`** (44.3 MB, HTTP 200, no auth beyond the public
key). Contents, and the three things that change `P1-2`:

- Coordinates are **already in Godot's convention** — each node matrix translates to
  `(easting, elevation, -northing)` in HK1980 metres, exactly the conversion in `ARCHITECTURE.md`.
  `GameTransform` reduces to subtracting the origin. Note this bears on `Q7` only for the axis
  *direction*, which both candidate origins preserve; it does not settle where the origin sits.
- Vertices are **unwelded, exactly 3.0 per triangle** — flat shading is baked in, which is the art
  direction's native form. Do not weld, do not generate normals.
- **"Non-textured" describes buildings, not terrain.** Terrain ships with a JPEG. Decide in `P1-2`
  whether to discard it rather than importing it by accident; `P1-4` generates the road surface
  from the road graph regardless.

**New risk, registered:** 612 triangles per building is far more than an LOD1 extrusion needs.
Six sheets extrapolate to ~555k triangles against a **<300k visible** budget. `P1-2` decimation and
LOD tiers are now load-bearing rather than optional. `DATA_SOURCES.md` previously claimed "no
decimation needed"; corrected.

### 2026-07-30 — Region bounds confirmed **WGS84**, by measurement

`P0-4` flagged that the region bounds were authored with no datum stated, and that HK1980 vs WGS84
is a ~304 m question in Hong Kong. That turned out to be load-bearing rather than pedantic: the two
readings select **different sheets** — WGS84 gives a contiguous `11-SW` block, HK1980 swaps two of
six for `11-SE-11A` and `11-SE-6C`. A third of the region rode on an unstated assumption.

Settled by comparing sheet `11-SW-10C`'s real building positions against both readings. The WGS84
projection matches to within metres and the HK1980 one is out by ~250 m; the terrain node sits at
the WGS84-projected sheet centre exactly. `crs.geodetic: EPSG:4326` in `hong_kong.yaml` is correct
as authored. Full table in `DATA_SOURCES.md`.

### 2026-07-29 — `P0-5` gate: **released conditionally**; the fun question moves to Phase 1

User verdict after driving the grey-box circuit: *"verified and seems acceptable, but I don't know
if it is fun or good until we have either the Hong Kong scene or game mechanism."*

**Read as a pass on what `P0-5d` could actually test, and a rejection of its premise.** The
acceptance criterion was "the user drives it and confirms it feels good," and the handling cleared
it — no blocking problem, nothing that must be fixed before real geometry. But `PLAN.md` claimed the
grey box would answer "is this a game?", and it did not. Recorded as `Q8`, and the risk register
updated: `P0-5` is no longer a valid mitigation for "real geometry isn't fun to drive."

**Phase 1 is released.** The gate's purpose was to avoid sinking ETL effort into a game that does
not work; the user's answer is that the ETL output is a *precondition* for knowing. Continuing to
hold Phase 1 would deadlock the project.

**Deliberately not actioned:** the two feel items flagged during `P0-5d` — sustained full lock still
spins the car (`GAME_DESIGN.md:114` wants a drift that is easy to hold), and `brake_force = 900`
gives 3 m/s² of braking against 5.33 m/s² of acceleration, so **the car accelerates faster than it
stops**. Both are real, neither is blocking, and both belong with `P2-3`, which tunes the controller
against real geometry. Revisit them there rather than tuning twice.

### 2026-07-29 — `P0-4` ETL scaffold: config declares its **datum**, not just its CRS

The scaffold landed as planned — `pipeline/` package, `config/cities/hong_kong.yaml`, `crs.py`,
`ruff` and `pytest` — but building the round-trip tests turned up something that would have been an
expensive silent failure.

**HK1980 and WGS84 differ by ~304 m on the ground in Hong Kong.** Measured, not assumed: EPSG:2326's
own natural origin is published as 114°10′42.80″E, 22°18′43.68″N **on the HK1980 datum**, and feeding
those identical digits in as WGS84 lands 304 m away. That is a fifth of the width of the Wan Chai
region, and it is far larger than the ~10 m people expect from a datum shift.

The region bounds in `DATA_SOURCES.md` are quoted as bare lat/lon with **no datum stated**. Read off
any consumer web map they are WGS84; handed to the projection as HK1980 they would have placed the
entire region 304 m from the road data — with no error, no warning, and entirely plausible-looking
output. So `hong_kong.yaml` declares `crs.geodetic` alongside `crs.projected`, `config.py` refuses
to load without it, and `test_crs.py` asserts the two datums disagree by >250 m. That last assertion
is really a canary: if it ever shrinks, PROJ has fallen back to a **ballpark** transformation. It
has not — pyproj 3.7.2 / PROJ 9.5.1 selects the 7-parameter `Hong Kong 1980 to WGS 84 (1)` operation
at 1 m accuracy.

**Verification is against external facts, not the code's own output.** The load-bearing test projects
the published grid origin from EPSG:4611 and expects the published false easting/northing
(836694.05, 819069.80); it reproduces them to sub-millimetre. Corroboration: the config's bounds
project to 1649.0 × 885.9 m against a documented 1.65 km × 0.9 km, and to 66 tiles at 150 m against
a documented ~66.

**Other choices worth knowing:**
- `transformer()` is `@cache`d per CRS pair. Construction queries the PROJ database and costs
  milliseconds; the pipeline pushes millions of vertices through a handful of pairs.
- `always_xy=True` everywhere. EPSG:4326 officially declares lat-then-lon, and a silent axis swap
  is the classic way to relocate a city into the Indian Ocean.
- `GameTransform` is **pyproj-free** and pure arithmetic. The source CRS is already projected and
  metric, so the per-vertex hot path never re-enters PROJ, and the transform serialises into
  `city.json` as three numbers.
- The origin is **rounded to whole metres**. Every tile boundary is measured from it, so inheriting
  the sixth decimal place of whatever PROJ release generated it would renumber every tile on a
  library upgrade. *(Floored on both axes as written here; `Q7` later made it floor east and ceil
  north, so the rounding is outward from the origin corner.)*
- `deck_height_m()` raises on an unmapped `ELEVATION` rather than defaulting to 0.0 — a defaulted
  tunnel would be dragged to street level and invent a junction with the road above it.
- **Elevation-level keys reject `bool`, not just non-`int`.** Caught in review, reproduced, and now
  regression-tested. PyYAML implements YAML 1.1, where a bare `on`/`off`/`yes`/`no` key resolves to
  a boolean — and because `bool` subclasses `int` in Python, `isinstance(key, int)` waves it
  straight through. `False == 0` as a dict key, so a stray `off:` would silently redefine **ground
  level**. Verified: a config with a boolean key loaded without error and returned 42.0 m for
  level 1. One residual case is unreachable from here — writing both `1:` and `on:` in the same
  mapping collapses inside PyYAML before the loader sees either.
- Bounds are projected with pyproj's `transform_bounds` and edge densification, not by projecting
  four corners. A geodetic rectangle is not a rectangle once projected. Irrelevant at 1.5 km,
  wrong at city scale.
- Deps are only `pyproj` and `pyyaml`. GDAL/OGR and geopandas are heavy and platform-awkward and
  stay out until `P1-1` actually imports them.

**Surfaced, not fixed:** the data contract contradicts itself on the sign of game-space Z. See `Q7`.

### 2026-07-29 — `P0-5a` Vehicle controller: **custom raycast on `RigidBody3D`**, not `VehicleBody3D`

Measured, not assumed. A throwaway headless spike built a `VehicleBody3D` with four
`VehicleWheel3D` on a flat plane under Godot 4.7.1 + Jolt and drove it through settle → accelerate →
steer → drift phases.

**`VehicleBody3D` is not broken under Jolt.** It instantiates, simulates, accelerates, steers and
brakes. The wheel query API works: `is_in_contact()` reported 4/4 while cornering, with
`get_skidinfo()` at 0.894 and `get_rpm()` at 269.5. Anyone repeating this spike should not expect a
crash — the problem is subtler.

**The problem is that the tuning schema is inexpressible.** `ClassDB` introspection shows
`VehicleBody3D` exposes exactly three tunables — `engine_force`, `brake`, `steering` — with the rest
on `VehicleWheel3D`. Mapping the 18 `HandlingProfile` fields against that surface:

| Fit | Count | Fields |
|---|---|---|
| Direct | 4 | `engine_force`, `brake_force`, `centre_of_mass_offset_y`, `gravity_scale` |
| Partial / fightable | 4 | `steer_angle_max_deg`, `grip_lateral`, `grip_longitudinal`, `drift_grip_scale` |
| **Absent** | **10** | both speed caps, three steering-curve fields, two drift fields, all three collision/recovery fields |

**The decisive finding: `wheel_friction_slip` is isotropic.** One friction number covers every
direction, so `grip_lateral` and `grip_longitudinal` collapse into each other, and a drift cannot
break lateral grip without destroying traction and braking with it. Measured, holding throttle:

| Drift variant | Speed lost over 2 s | Implied scrub/s (target **0.080**) | Peak slip angle (threshold **14°**) |
|---|---|---|---|
| Friction × 0.35, all four wheels | 57% | 0.285 | 162.7° |
| Friction × 0.35, rear axle only | 30% | 0.151 | 162.6° |

Both violate `GAME_DESIGN.md` on two counts at once: `drift_speed_scrub_per_s` is "deliberately
small — drifting must not feel like a penalty" (missed by 1.9–3.6×), and grip must be "high,
forgiving, no spin-outs" (162° is a full spin, not a slide).

**Could it be tuned out? Partly — and that is the argument against it.** Yaw damping, counter-steer
assist and per-axle friction curves would suppress the spin. But that is an arcade correction layer
built on top of a physical model actively resisting it, leaving `VehicleBody3D` contributing only
suspension raycasts — perhaps 100 lines of the eventual controller. Every future tuning change would
be a negotiation with the engine rather than a dial. `GAME_DESIGN.md:120` expects vehicle feel to be
iterated on more than anything else in the project, which makes that friction compound.

**Consequences:**
- `handling_profile.gd` gains a `Suspension` group — the original schema had none, having assumed
  `VehicleBody3D` would own them. Values seeded in `handling.tres`.
- Spring rate is specified as **natural frequency in Hz, not a raw N/m constant**, so it stays
  correct when vehicle mass changes or a heavier vehicle joins the roster. It is *not* gravity-
  independent, though: static sag is `g_eff / (2πf)²`, so `gravity_scale = 1.6` deepens sag by the
  same 1.6× and eats the bump travel that absorbs kerbs and jump landings. The seed is therefore
  **2.8 Hz** — 2.2 Hz scaled by `√1.6`. Anyone retuning `gravity_scale` must rescale this with it.
- Forward note for `P2-3`: the class docstring promises an unassigned profile "fails loudly", but
  nothing enforces that yet. `wheel_radius_m = 0.0` divides by zero and `suspension_frequency_hz =
  0.0` is a dead spring, so the controller should assert both non-zero on assign. It should also
  cache the derived `k = mω²` and `c = 2ζ√(km)` rather than recomputing transcendentals per wheel
  per tick on the Adreno 618 floor.
- New `anti_roll` field: the spike rolled the car over even with `centre_of_mass_offset_y` applied,
  so roll resistance needs its own dial rather than being a side effect of centre-of-mass placement.
- Wheel **geometry** (wheelbase, track, mount points) deliberately stays out of `HandlingProfile` —
  that is per-vehicle model data; the resource describes feel, which is shared across the roster.
- `P2-3` is now "finish and tune the controller", not "adopt `VehicleBody3D`".

Spike files were deleted after the numbers were recorded here.

### 2026-07-29 — Device floor: **A13 / Adreno 618**, named as two separate floors

Resolves `Q4`, on the user's call. Reverses the earlier assumption of iPhone XR (A12) /
Snapdragon 730-class.

- **iOS floor: A13** — iPhone SE 2nd gen (2020) or iPhone 11 (2019).
- **Android floor: Adreno 618 tier** — Vulkan 1.1, 4 GB RAM. Spans Snapdragon 710/712/720G/730/730G.

**These are two decisions, not one, and the old single-device phrasing hid that.** The iOS floor is
a *support-matrix* question — A12 is off the current iOS train, so an XR would mean testing against
hardware that can no longer take OS updates. The Android floor is a *performance* question, and it
is the only one that constrains the budget: A13 is roughly 3–4× the GPU throughput of the Adreno 618
tier, so anything that holds 60fps on the Android floor is free on iOS.

**The Mobile renderer requires Vulkan**, so the real floor is "Vulkan 1.1 with a maintained driver"
before it is any particular chip. `project.godot` locks `rendering_method="mobile"`; cheap hardware
with broken or absent Vulkan drivers is out regardless of the name on the floor.

**Chosen over a more conservative floor because Hong Kong skews high-end** — iPhone share is far
above global average and the Android side skews Samsung and flagship-adjacent brands rather than
budget hardware. A global-market floor would cost art fidelity for users this TAM does not have.

**This makes the existing perf budget coherent rather than arbitrary.** <150 draw calls, <300k
triangles and <128 MB texture are sane Adreno-618 numbers — needlessly tight for a 2022 floor,
unachievable on a 2017 one.

**Follow-through:** the floor defines **tier 0** of the perf tiers that `P3-3` scales traffic
density against. Per hard rule 4 that lives in config, not constants — to be authored in `P2-6`.
Hardware to acquire for `P0-3b`: one A13 iPhone and one Adreno 618 Android, both viable secondhand.

### 2026-07-29 — Engine version: Godot 4.6 → **4.7.1**
Reverses the locked "Godot 4.6" decision, on the user's call. Homebrew's cask ships 4.7.1, which is
current stable; 4.6.3 would have needed a manual pinned download for no gain this early. Nothing in
the project depends on 4.6 specifically — no code existed when the switch was made.

**The GDScript-not-C# decision is unaffected.** Re-verified against the official 4.7 docs: desktop
C# is fully supported, Android and iOS remain **experimental**, and web export remains
**unsupported entirely**. The reasoning stands unchanged.

`CLAUDE.md` and `docs/ARCHITECTURE.md` updated to match.

### 2026-07-29 — `P0-3` acceptance criteria split
The written criterion, "builds and runs on the device floor", bundled a scaffold together with
Android SDK setup, Xcode, an Apple signing identity and physical 2019-era hardware. Split per the
working agreement in `PLAN.md` rather than quietly redefined:

- **`P0-3`** — project imports clean, cube scene at 60fps with an FPS counter, export presets
  committed as configuration, desktop and web verified to export.
- **`P0-3b`** — signed on-device builds for iOS and Android, and the real bundle identifier.

`P0-5` depends only on `P0-3`, so the critical path is not affected.

### 2026-07-29 — `P0-2` resolved without writing code
Answered Q1 by inspecting the live dataset directly (GFS schema + ranged reads across the 486 MB
GML). No Z ordinates, but `ELEVATION` encodes grade separation as an ordinal level. Region choice
holds. Also surfaced: bilingual street names ship in the source, `-99` is the null sentinel, and
the file must be streamed and clipped rather than loaded whole.

~~**Top data risk has moved from roads to buildings.** Roads are fully scriptable via static URLs;
building data is portal-only with no direct download endpoint. Not slice-blocking — the region is
a handful of 1:1000 sheets and can be fetched by hand — but it must be solved before a second city.~~

> **Superseded 2026-07-30 — this was wrong.** Building data *is* fully scriptable; the sheet index
> carries direct download URLs. Struck through rather than deleted, because the error is instructive:
> it came from reading the CKAN resource list, which really does only list portals, and not opening
> the portal itself. See the `P0-1` entry at the top of this log.


Decisions are **settled**. Do not re-litigate without explicit instruction from the user — but do
flag it here if new evidence contradicts one.

### 2026-07-29 — Engine language: GDScript, not C#
Verified Godot C# platform support: desktop full, **Android and iOS experimental**, **web
unsupported entirely**. Mobile is a primary target and the free web demo is the planned marketing
funnel — C# compromises both. The complex code lives in the Python ETL anyway, so C#'s tooling
advantage earns little. Performance escape hatch is **GDExtension** (C++/Rust), not C#.

### 2026-07-29 — Target platforms: mobile + desktop/Steam
User decision. Adds a gamepad/keyboard input layer, resolution-independent UI, a desktop LOD tier,
and a Steam build path. ~15–20% engineering overhead across input and UI, accepted for the broader
revenue options.

### 2026-07-29 — Scope: vertical slice first
Plan covers Phases 0–3 in executable detail. Phases 4–6 are outline only and will be refined after
the Phase 3 gate.

### 2026-07-29 — Engine: Godot 4.6
Chosen after the target shifted from a free web release to a commercial store product. Reversed an
earlier web-first (three.js + Rapier) recommendation. Decisive factors: native mobile performance
versus Android WebView GPU throttling, and a single codebase covering mobile, desktop, and a web
demo. Store-service integration turned out to be a weak argument, since a one-time unlock IAP is
small on any stack.

### 2026-07-29 — Monetisation: free download + one-time unlock (deferred)
Not F2P (2–5% conversion needs volume this TAM can't supply, and retention mechanics would corrode
a 3-minute arcade loop). Not paid-upfront (paid games are <5% of App Store revenue, and this
product's appeal — "it feels like Hong Kong" — cannot be conveyed in a screenshot; a free slice
*is* the marketing). **Build implication:** design Wan Chai to be standalone-playable as the free
tier. Final call deferred to launch.

### 2026-07-29 — Region: Wan Chai → Causeway Bay
Chosen over Tsim Sha Tsui and Central. Reasons: a natural circuit exists in the real road layout
(Gloucester → Canal Road Flyover → Hennessy), map edges are diegetic (harbour north, escarpment
south), and it has real grade separation without Central's multi-level data risk. TST is the
fallback if `Q1` resolves badly.

### 2026-07-29 — Building source: non-textured / LOD1, NOT photogrammetry
The tile-based photogrammetry mesh was rejected: a prior public attempt found ground gaps, level
differences, and vehicles baked into the geometry, and concluded it suited flight rather than
driving simulation. Decimating photogrammetry produces blobs, not low-poly style. The non-textured
and 3D-BIT00 Level 1 products are already extruded flat-shaded volumes — the target art style is
the data's native form.

### 2026-07-29 — Art direction: accurate city, toy vehicles
Stylise the actors, not the stage. Recognition is the product, so building proportions stay
accurate; charm and readability come from Choro-Q vehicle proportions.

---

## Planned vehicle roster (user direction, 2026-07-29)

Real models, not generic cars. Recorded because the **drive layout differs across them**, which is
an architecture constraint rather than an art note.

| Vehicle | Drivetrain | Notes |
|---|---|---|
| Old Toyota Crown (Comfort) | LPG, **rear-wheel drive** | The iconic HK red taxi |
| New Toyota Crown | Hybrid, **front-wheel drive** | |
| Toyota Hiace | CVT | Van proportions — tall, high centre of mass |

**Already supported without code changes:** `WheelMount.drives` is authored per wheel in each
vehicle scene, so RWD and FWD are scene data. Each vehicle gets its own `HandlingProfile`, and
`centre_of_mass_offset_y` plus `anti_roll` already cover the Hiace's height.

**This is why drift bias is derived from chassis geometry, not from `drives`.** `VehicleController`
computes `WheelMount.is_front` from the wheel's position along the chassis. Had it keyed off
`drives` or `steers`, the front-wheel-drive Crown would have had its drift bias inverted — the
front would break away instead of the rear.

**Not yet modelled:** transmission character. `engine_force` is a flat constant with no gears or
torque curve, so an LPG Crown, a hybrid and a CVT would accelerate identically. Hybrid instant
torque versus LPG's laggier delivery would need a torque curve in `HandlingProfile`. Open, not
urgent — flag it before the roster work in Phase 5.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Road data lacks Z values | **High** | `P0-2` first. Fallbacks documented in `DATA_SOURCES.md`. Worst case: switch region to TST. |
| Real geometry isn't fun to drive | High → **Retired** | **Closed 2026-07-31.** `P0-5` could not answer this from a grey box, which is why it sat open through the whole ETL build. Answered by driving the real thing: the user's verdict on `scenes/dev/city_drive.tscn` is that an HK-like map is a fun enough gimmick on its own. The premise the project is built on holds. What replaces it is a *different* risk — see "Novelty does not survive the first session" below. |
| Novelty does not survive the first session | **Medium** | **New 2026-07-31, and it is the honest reading of the `Q8` verdict.** "Gimmick" was the user's own word, and a gimmick reliably carries one session. Recognition is doing the work, which is a strong start and not yet a loop. The mitigations were already scheduled and are now the ones that matter: `P3-*` for whether the fare loop sustains, and `P3-9`'s authenticity test with real HK drivers for whether recognition holds up to people who know the streets. **Three levers added 2026-08-01** by the genre evaluation, all built from assets already scheduled: the **losable style chain** in `P3-2b`; a **drivable vehicle roster** — the minibus, double-decker and tram are already authored for `B3`'s traffic, so making one or two drivable costs a `HandlingProfile` and a mount point; and **world-embedded challenges** (drift zones, speed traps) pinned game-side to edge IDs, which keeps them out of the data contract. Only the first is in the slice; the other two are named here so **Phase 5** does not reinvent them. |
| Doesn't read as HK to locals | **High** | `P3-9` authenticity test with ≥3 real drivers; run again every phase after. |
| Perf misses 60fps on device floor | Medium | Budget defined up front; untextured merged tiles are the main lever; `P2-6` is a dedicated pass. |
| Source data quirks (dual carriageways, doubled junctions) | Medium → **Low** | **Mitigated 2026-07-30 by `P1-3`, and the directions confirmed against the street (`Q12`).** Both quirks turned up and both were handled: dual carriageways arrive as 6 opposed one-way pairs 1.96–3.85 m apart (median 2.9 m), and doubled junctions never form because nodes are made only at shared endpoints. **Closed 2026-07-30 by `P1-4`:** the residual — whether a 3 m pair becomes two ribbons or one — was not a decision. The widened ribbons overlap, so both carriageways draw as one continuous surface and no pair handling exists in the code. |
| Building meshes blow the triangle budget | Medium → **Low** | **Mitigated 2026-07-30 by `P1-2`.** The estimate was low: 2,200 buildings across the six sheets, not the ~900 extrapolated from one. Real region totals are **989k / 400k / 184k** triangles at LOD0/1/2, averaging 15.2k per tile at LOD0. Against a <300k *visible* budget that leaves room, but not much — a viewpoint holding LOD0 on the nearest ring plus LOD1 behind it lands in the low 300k range before occlusion. `P2-1`'s switch distances now decide this, not the ETL. |
| Grade separation is unreachable | Medium | **New 2026-07-30, raised by `P1-4` as `Q13`.** Deck heights are a constant per level, so nothing ramps: all 36 nodes joining two levels step by a whole deck height. The flyovers and the tunnels render correctly and cannot be driven onto. Not a blocker for the street-level slice, but `P2-2`'s nearest-edge query will put the car on a flyover unless it is told not to. |
| Terrain does not fit any budget | Medium → **Low** | **New 2026-07-30.** Measured 267 MB of texture and 405k triangles for the ground alone — roughly 2× over on texture memory, triangles *and* bundle size simultaneously. Resampling to ~2 px/m and decimating to ~88k triangles brings it into range, but that work is not done and is not scheduled. Nothing in the tile output depends on it. **Reassessed 2026-08-01:** 224 of the 267 MB was the JPEG, and the answer is to read it at build time and ship none of it. Vertex-coloured terrain decimated at 4 m is ~88k triangles and 1.5–2.5 MB against a 21.1 MB PCK, merges into the tile primitive so it costs no extra draw call, and needs no texture budget at all. Scheduled as `P3-10`. |
| The city has no ground | **Medium** | **New 2026-08-01.** There is no ground surface in the game: between the roads and under the buildings is skybox, the kerb lip is what keeps the carriageway from ending in mid-air, and `drive_harness.gd` carries a fall floor for when the car leaves the ribbon. `B2`'s review asks "does this read as Wan Chai?" and cannot be answered honestly over a void. Mitigated by `P3-10`, which is scheduled into `B2` for exactly that reason. |
| GDScript learning curve | Low | Small codebase; complexity lives in Python. |
| Landmark depiction IP | Low | Untextured massing; legal sight-check before launch (Phase 7). |
| TAM too small to be commercial | Medium | City-agnostic ETL is the scaling answer — city packs, not one city. |

---

## Metrics to track from Phase 2

Record measured values here, not estimates.

| Metric | Target (mobile) | Latest | Date |
|---|---|---|---|
| FPS on device floor | 60 | — (no device yet — `P0-3b`) | — |
| FPS, Chrome on macOS, 2880×1450 | — | **119** (worst frame 9.7 ms) | 2026-07-31 |
| Draw calls | < 150 | **48** ✅ | 2026-07-31 |
| Visible triangles | < 300k | **1.16 M** ❌ — 3.9× over | 2026-07-31 |
| Texture memory | < 128 MB | 0 — no textures ship | 2026-07-31 |
| Bundle size | < 200 MB | **51.8 MB** PCK (+38.8 MB wasm) | 2026-07-31 |
| Boot to drivable (web, warm) | — | 830 ms, of which 260 ms is tile instantiation | 2026-07-31 |
| Tab memory (web) | — | 307 MB | 2026-07-31 |
| ETL full-run time | — | 4.4 s, whole region from empty | 2026-07-31 |

⚠️ **The triangle count is over budget by design, not by accident.** These are `city_drive.tscn`
numbers, and that scene loads all 65 tiles at LOD0 with no culling and no LOD switching, because it
is a dev scene. `CityStreamer` (`P2-1`) is what makes this measurable as a real figure; until then
the draw-call number is encouraging and the triangle number is not a verdict. The chase camera's
400 m far plane is doing all the culling there is.

---

## Session log

### 2026-07-30 — `P1-3` Road graph

Three new pipeline modules — `gdb.py` (geodatabase and WKB), `terrain.py` (height field),
`roads.py` (policy) — mirroring the `gltf.py` / `mesh.py` / `buildings.py` split that `P1-2`
settled on, plus the whole source schema as city config.

**Result:** `python -m pipeline.roads --city hong_kong --region wan_chai` turns the 17 MB
geodatabase into **797 edges over 615 nodes with 217 turn restrictions in 1.4 seconds**.

| | |
|---|---|
| Centrelines read (region bbox) | 796 |
| Edges after clipping | 797 — one feature split, none dropped |
| Vertices | 175,610 → **3,553** (2.0%), worst deviation 0.1997 m against a 0.2 m tolerance |
| Connectivity | **592 of 615 nodes** in one component (96.3%) |
| Directions | 679 one-way, 117 two-way |
| Levels | 736 at grade, 45 elevated, 15 tunnel |
| Named | 723 of 797 edges, **bilingual, straight from the source** |
| Output | `roadgraph.json`, 649 KB |

**The 23 nodes outside the main component are correct, not a defect.** Four of the six minor
components are the **Central–Wan Chai Bypass tunnel**, which passes under the region with no ramp
inside it — genuinely unreachable from Wan Chai's streets. The other two are two-node stubs on the
region boundary. There is nothing to fix.

**Three findings that changed the design, all measured before any code was written:**

1. **Endpoints coincide exactly** — 601 distinct at full float precision, and the nearest
   *distinct* pair is **2.26 m apart**. So node snapping needs no tolerance and has none to tune.
   It does need to be no finer than a millimetre: two clusters differ in their last bits, and at a
   tenth of a millimetre they split — which silently disconnected Johnston Road at Fenwick Street
   and dropped the turn restriction there. Caught by a turn that would not resolve.
2. **`ELEVATION` must not key nodes.** See the decision log.
3. **The geometry is over-densified past belief** — one 51.7 m centreline carries **54,330
   vertices**, a median segment of 0.4 mm, and five features hold three quarters of the region's
   vertices. Douglas–Peucker is a correctness measure for `P1-4`, not a size optimisation. Written
   iteratively rather than recursively, because nearly-collinear input is exactly what produces
   both the vertex count and the stack overflow.

**Two more the source made necessary:**

- **`ROUTE_ID` is 1:1 with the centreline**, so the speed-limit and bus-lane layers — modelled as
  linear-referenced route events — collapse into a key join with no measuring along the route.
- **`EDGE1END` is a hint.** It names the end of the first edge a turn passes through, and in 4 of
  217 it names an end 4–39 m from the second edge while the *opposite* end coincides exactly.
  Taking the shared node as the truth resolves all 217.

**Q11 is resolved and the answer cross-checks.** Sampling the terrain under every vertex puts
level-0 roads at a median **4.21 m**, against the **4.29 m** median building base `P1-2` measured
through an entirely separate path. Roads sit 8 cm below the doorways on them. Nothing was tuned to
make that happen.

**What is deliberately not in the output:** the turn layer's `EXC_VEH_TYPE` / `INC_VEH_TYPE`,
`PART_TIME_REST` and `EFF_ALL_DAYS`. One restriction in the region excludes taxis — a turn a real
red taxi may make and the graph says it may not. `roadgraph.json` has no field for it, and adding
one is a schema change on both sides (hard rule 5), so it is recorded in `DATA_SOURCES.md` for
`P3-3` and `P3-8` rather than smuggled in.

**234 tests, `ruff` clean.** The road tests build a whole synthetic city — config, geodatabase and
all — through pyogrio's writer, so they read their input back through the same GDAL that reads the
real thing rather than proving the parser agrees with itself.

**Review pass, same day: 1.26 s → 0.80 s and 962 MB → 523 MB peak, output byte-identical.**

| Fix | Effect |
|---|---|
| `np.allclose` on 2-vectors, 41,406× in `clip` | **−0.32 s.** Also a latent bug: its default `rtol=1e-5` widened an intended 1 nm join test to **~15 mm** at the far edge of the region, so two runs re-entering within a centimetre would have merged into one segment crossing outside. Now an explicit metre tolerance. |
| Terrain read 224 MB of JPEG the height field never looks at | **−300 MB.** `_ground` yields a generator and strips `texture`/`uvs`, so six sheets' textures are no longer live at once. |
| Height field indexed the whole six sheets | **−80 ms, −34 MB.** Sheets overlap a region rather than matching it: 54% of the terrain lies outside Wan Chai and can never be queried, because clipping guarantees every road vertex is inside. |

Four hypotheses were **measured and rejected**, which is the more useful half: vectorising
`HeightField.sample` gives *no gain* (3,553 query points land in 2,023 distinct cells, so there is
nothing to amortise), a counting sort is no faster than `argsort`, `_write`'s list building is
9.4 ms, and the redundant `projected_bounds` calls cost 0.6 ms between them.

Three correctness fixes came out of the same pass. `parse_speed_limit` searched rather than
matched, so a free-text `"Route 4, 70 km/h"` would have read as **4 km/h**. `clip`'s whole-array
fast path skipped the minimum-length rule the slow path applied, so one function carried two
policies. And an empty or single-vertex geometry — legal in a geodatabase — reached
`polyline[0]` and raised `IndexError` with nothing to say which feature caused it.

**The graph is previewable.** `game/scripts/city/road_preview.gd` draws every edge as a flat
ribbon of its `width_m` at its real deck height, with arrows along the one-ways, in the same scene
as the massing. Verified in Godot 4.7.1 headless: 797 edges, 680 one-way, 1,124 arrows, spanning
**1650 x 887 m** against a 1649.6 x 886.9 m region and y −8.9 to 50.0 m. Those spans are the check
worth keeping — a sign error or a missed origin puts the graph somewhere plausible and elsewhere.

Built for `Q12` specifically. Arrows over buildings a Hong Kong driver recognises is the cheapest
way to ask whether Jaffe Road really runs east, and it is not a question any test can answer.

**Recorded, not fixed:** `roads.py` reaches into `buildings.py` for `Placement` and `read_sheet`,
and reads its terrain class out of the *buildings* config section. The layering rule says format
and policy stay apart, and this crosses it. The right shape — a shared sheet-reading module — is
easier to see once `P1-4` and `P1-5` have said what they need from the same sheets, so it is
deliberately left until then rather than guessed at now. Also latent: `_shared_node`'s `EDGE1END`
hint is stated against the source feature's digitisation, which reversing or splitting an edge
breaks; the geometric fallback covers it unless a turn's two edges ever meet at *both* ends, which
no data has produced.

### 2026-07-30 — `P1-2` Building meshes

Three new pipeline modules — `gltf.py` (format), `mesh.py` (geometry ops), `buildings.py` (policy)
— plus the palette and LOD tiers as city config, and a Godot-side verifier.

**Result:** `python -m pipeline.buildings --city hong_kong --region wan_chai` turns the six cached
sheets into **65 tiles × 3 LOD tiers in 6 seconds**. 2,274 source meshes read, 881 clipped away,
1,393 placed.

| Tier | Cell | Triangles | Size |
|---|---|---|---|
| LOD0 | exact weld | 989,212 | 74.7 MB |
| LOD1 | 1.5 m | 400,139 | 17.9 MB |
| LOD2 | 4.0 m | 183,773 | 7.8 MB |

**Acceptance, checked rather than asserted.** `game/tools/verify_tiles.gd` loads every tile inside
Godot 4.7.1 headless and checks the four criteria the task states. All **195 tiles pass**: one
surface each (so one draw call, against a budget of three), `ARRAY_FORMAT_COLOR` present,
`vertex_color_use_as_albedo` on, and no texture in any slot.

**The geometry is verifiably really Wan Chai**, which matters because a coordinate bug here
produces a plausible-looking city in the wrong place — the failure this whole pipeline is most
exposed to. Taking the tallest building the region produces and converting its centre back out to
WGS84:

| | |
|---|---|
| Source id | `B359321570101063C0` |
| Height | **374.5 m**, roof at game y = 378.5 |
| Position | 22.28011 N, 114.17358 E |
| Central Plaza (published) | 374 m; 22.28028 N, 114.17361 E |
| Offset | **19 m** — within its own 78 m footprint |

Right building, right height, right place, through the whole chain: node matrix → HK1980 →
region origin → tile. Footprints also land inside the region with only the expected overhang
(x −11.3…1656.9, z −18.8…923.3 against a 1649.6 × 886.9 m region).

**No glTF library.** `pipeline/gltf.py` reads and writes the format directly, in ~380 lines. The
read side would have used a few percent of trimesh or pygltflib, and the write side has to lay out
accessors and buffer views by hand under either, since neither merges a vertex-coloured tile mesh
for you. `numpy` is the one dependency added.

**Bugs found and fixed while building it:**

- **Flyovers deleted.** Whole-mesh tile assignment by centre dropped a 1,984 m elevated road
  structure whose centre lay outside the region, though it crosses the whole map. Oversized meshes
  are now partitioned by triangle. See the decision log.
- **White city.** Godot 4.7 does not set `vertex_color_use_as_albedo` on import; separately,
  omitting `"normalized": true` on the colour accessor makes Godot read every colour as 1.0. Both
  fail silently and look identical. Fixed by a post-import script and covered by tests.
- **Reader could not read what the writer wrote.** `read_scene` deliberately skipped `COLOR_0`,
  since the LandsD source is a uniform 0.8 grey the pipeline replaces anyway — which meant no test
  could check the colours in an emitted tile without hand-parsing GLB. Now decoded to RGBA bytes.

**A preview scene, so the city can be looked at before `P1-7`.**
`scenes/dev/city_preview.tscn` instantiates every tile and frames whatever is on disk; a fly
camera moves through it. It reports **65 tiles, 989,212 triangles** — matching the ETL exactly,
which is a second confirmation that every triangle survives the trip into the engine. It is a dev
tool, not the streamer: no distance culling, no LOD switching, so it measures nothing. `P1-7` still
owns the real path, and still needs `city.json` from `P1-6`.

Lighting moved to one shared rig, `scenes/world/golden_hour.tscn`, with the Environment as a
`.tres` in `tuning/`. The grey-box scene had been carrying its own — flat background, white sun —
so the two dev scenes lit the city differently and neither matched `ART_DESIGN.md`.

**Deliberately not done:** terrain resampling (see the decision log).

**Correction, same day.** This section first recorded the cluster-key optimisation as skipped
because it "changes every output byte". Measured, that was wrong twice over, so it was implemented:

- Packing the key into a 1-D **void** view — what I had assumed the win was — saves **nothing**.
  That is exactly what `np.unique(axis=0)` already does internally.
- Packing the **binned** tiers' key into a mixed-radix **int64** is 8.2× on that stage, because
  small integers sort without memcmp. Most-significant digit first reproduces the lexicographic
  order the row-wise sort produced, so the clusters and their ordering are unchanged — verified
  **byte-identical across all 195 tiles**. Whole build **5.95 s → 3.24 s (−46%)**.
- The exact tier keys on raw float64 and cannot be packed at all. Its share is irreducible, which
  is why LOD0 still pays for the row-wise unique.

Guarded: it falls back to the row-wise path if the grid cannot be encoded, which needs a region
~3,500 km across at 1.5 m cells.

153 tests, `ruff` clean.

### 2026-07-30 — `Q7` Game-space origin moved to the NW corner

One line in `GameTransform.from_bounds`, plus tests and the three docs that state the coordinate
contract. **67 tests pass, `ruff` clean.** Measured after the change: origin `(835765, 816125)`,
region spanning X `0.64 → 1649.62` and Z `0.97 → 886.88`, tiles `(0,0)` → `(10,5)` — 66 at 150 m,
matching the count `DATA_SOURCES.md` already recorded.

Mutation-tested rather than assumed: reverting to the SW origin fails two tests, and the subtler
floor-instead-of-ceil off-by-one (which puts the NW corner at Z = −0.03) fails one. Three
overlapping tests were consolidated into one that names the invariant, and the class fixture's
origin — which still carried the old SW northing — was corrected.

**Two errors of my own, caught in review:**

- I wrote that float32 holds millimetre precision to ~65 km. It is **~16 km** (2¹⁴ = 16,384 m).
  That number was the sole quantitative input to `Q10`, and being 4× optimistic made a city-wide
  origin look comfortably safe when it costs ~4 mm of quantisation at 50 km. Then, correcting it,
  I quoted spacings sampled at powers of two while labelling them decimal kilometres — which made
  the correction contradict its own headline. Now a measured table.
- The claim "tile indices are natural numbers" was stated unconditionally. It holds for the
  *region*, not for the data on disk: `fetch.py` fetches every sheet that intersects the region, so
  geometry runs past all four edges and anything north or west of it still indexes negative.
  Clipping is therefore part of the data contract, not an optimisation — now recorded in
  `ARCHITECTURE.md` and flagged for `P1-2`.

**Still open:** `Q10`, whether the origin is per region or per city. Cheap now, a `schema_version`
bump plus asset regeneration after `P1-6`.

### 2026-07-30 — `P1-1` Source fetching

`pipeline/fetch.py` plus `TiledSource` in the config layer and two new primitives in `crs.py`
(`reproject_bounds`, `GeodeticBounds.intersects`). **67 tests pass, `ruff check` and
`ruff format --check` clean.** Run end-to-end against the live endpoints.

The headline is that the derived sheet list matches `P0-1`'s hand-derived one exactly. The
supporting find is a stable, parameterised CSDI endpoint for the index — byte-identical to the
portal download — which is what actually makes "a fresh clone can fetch from scratch" true rather
than aspirational.

**Fetched and verified:** all six sheets (299 MB) plus the small road files (23 MB). `11-SW-10C`
came down **byte-identical by SHA-256** to the sheet downloaded by hand during `P0-1`, and a second
run re-downloaded nothing. `CENTERLINE.gml` and `INTERSECTION.gml` (535 MB) were deliberately left
unfetched pending `Q9` — same code path, no new coverage, and they are duplicates of the FGDB.

**Hardened against the index being untrusted input.** Tile URLs and filenames come out of a remote
document, so `download()` refuses non-HTTP(S) schemes (urllib will open `file://` quite happily) and
filenames are constrained to a single path segment. Low likelihood, but the cost of the guard is
twelve lines.

Deliberately **not** built: `--jobs` parallel downloading, and HTTP range resumption. Six sheets on
a good link do not need either, and both add failure modes; the retry comment in `download()` says
where resumption would go if the 486 MB road GML proves flaky.

**Corrected while here:** `DATA_SOURCES.md` gave `11-SW-10C`'s `REVISIONDATE` as `20250929`. That is
`1-SE-19D`'s date; `11-SW-10C` reads `20260424`. The field really is per sheet, which is what makes
it usable as a cache key.

**Review pass found four defects the end-to-end run could not have surfaced**, all reproduced
before fixing and all now regression-tested (the two most serious were mutation-checked — the fix
was backed out and the test confirmed to fail):

1. **A short HTTP response was committed as complete, then cached forever.** `read(amt)` returns
   `b''` on a premature close rather than raising — CPython declines to raise `IncompleteRead`
   there for compatibility — so a server dropping mid-transfer produced a truncated file that
   `os.replace` committed and the manifest then recorded *at its short size*, making the truncation
   a permanent cache hit. Reproduced against a real socket: 5,000 bytes accepted against a declared
   1,000,000. The atomic-rename machinery only ever protected against interruption of *our* write.
   Now the declared length is enforced and a mismatch retries.
2. **A failure partway through discarded the whole manifest.** It was written only on the happy
   path, so one dropped connection on the sixth sheet cost the record of the five that landed —
   ~283 MB re-pulled after one transient error, on exactly the link most likely to drop. Now
   written in a `finally`.
3. **`--force` re-downloaded everything, contradicting its own documentation.** Both this file and
   the README promised revision-aware re-snapshotting; the code short-circuited the version check.
   The docs described the better tool, so the code changed to match: `--force` now overrides
   fetch-once but still respects each sheet's `REVISIONDATE`. Measured: a forced re-snapshot costs
   **3.2 MB instead of 265 MB**.
4. **A poisoned index would have cached as "zero buildings" silently.** A portal answering an
   outage with HTTP 200 and a JSON error body parsed fine, selected zero sheets, and exited 0 —
   and every later run was a clean cache hit on it. The index is now validated as a non-empty
   `FeatureCollection` before use, and evicted if it fails so a retry can recover.

Also tightened: tiles are named after their id rather than their URL basename (two sheets differing
only by query string would have overwritten each other); the retry loop no longer treats `ENOSPC`
as a network error worth three attempts; `redact()` strips `userinfo` as well as the query string;
and selecting **zero** tiles is now an error, since a silent no-op is the failure mode this module
refuses everywhere else.

**Decided this session:** `P1-2` keeps the textured terrain (user call). **Still open:** `Q7`
origin placement, `Q8` the fun question, and the new `Q9` on redundant road formats.

### 2026-07-30 — `P0-1` Source data granularity

Closed `P0-1` and with it `Q2`, `Q3` and `Q5`. Detail in the decision log; the short version is
that building data is scriptable, six sheets cover the region, and the datum question `P0-4` raised
was real and is now settled by measurement.

**`DATA_SOURCES.md` needed correcting, not just extending.** It stated the building datasets expose
"no direct download URLs" and that the only API required an emailed key for rejected photogrammetry
tiles. Both false. The correction is marked as such in the doc rather than quietly rewritten,
because that file's whole premise is "do not re-research these" — a silent edit would leave no
signal that the earlier verification had been wrong. It also carried a "no decimation needed" claim
the triangle measurements contradict.

**Not yet decided:** whether to keep or discard the textured terrain mesh (`P1-2`), and `Q7`'s
origin placement (`P1-6`). Neither blocks `P1-1`.

Raw downloads sit in `etl/sources/` (gitignored): the sheet index plus one sheet, ~113 MB.

### 2026-07-29 — `P0-4` ETL scaffold

`etl/` now exists: `pipeline/` package, `config/cities/hong_kong.yaml`, `crs.py`, `config.py`,
`pyproject.toml` with `ruff` and `pytest` configured, and `tests/`. **22 tests pass, `ruff check`
and `ruff format --check` clean.** Verified on Python 3.13.5 with pyproj 3.7.2 / PROJ 9.5.1.

The interesting finding is the ~304 m HK1980/WGS84 datum shift and the config change it forced —
full detail in the decision log. Two things came out of the same work:

- **`Q7` opened:** `ARCHITECTURE.md` states a conversion that puts game-space Z at ≤ 0 across the
  region, then shows a `bounds_game` example with positive Z. The formula is implemented and pinned
  by a test; the contradiction needs the user's call before `P1-6` writes a real `city.json`.
- **`hong_kong.yaml` carries the verified road source URLs** from `DATA_SOURCES.md` so `P1-1` does
  not rediscover them. Building sources are deliberately absent — those datasets expose no download
  endpoint at all (`Q3`).

Deliberately **not** built: `fetch.py`, `buildings.py`, `roads.py`, `tiles.py`, `export.py`. Those
are Phase 1 tasks with their own acceptance criteria, and stub modules would only be deleted.

### 2026-07-29 — `P0-5b` / `P0-5c` Grey-box circuit, vehicle controller and chase camera

`VehicleController` implemented per the `P0-5a` decision: raycast suspension on `RigidBody3D`,
spring and damper sized from natural frequency, tyre forces capped **independently** for lateral and
longitudinal grip. That separation is the whole reason for the custom controller, and it verified:

| Same corner, held 4 s | Speed scrubbed /s | Peak slip angle |
|---|---|---|
| Gripping (no drift) | 0.297 | 16.4° |
| **Drift held** | **0.270** | 12.6° |

Drifting is *cheaper* than gripping, because breaking lateral grip removes the cornering force that
was scrubbing speed. Under `VehicleBody3D` the same manoeuvre cost 30–57% extra and spun to 162°.
The measured 0.27 is full-lock cornering, not the drift mechanic — a straight-line drift figure
comparable to `drift_speed_scrub_per_s = 0.08` needs a clean skid pad, which `P0-5d` can judge by
feel instead.

Headless verification on the built circuit: suspension settles at **50.6 mm sag** against 50.7 mm
predicted, body rests at 0.649 m, 4/4 wheels grounded, accelerates smoothly and dead straight to
49.9 km/h, corners upright without flipping, and the camera tracks at 2.2 m.

**Three bugs found and fixed by measuring rather than reading:**
- **Anti-roll signs were inverted** — force pushed *down* on the already-compressed side, amplifying
  roll instead of resisting it. The car flipped on the first hard corner. This is why `P0-5a`'s
  spike flip was not purely a centre-of-mass problem.
- **Coasting drag divided by `delta`**, making it framerate-dependent and roughly 35× too strong
  (~70% of velocity shed per second). `apply_force` already integrates over the tick.
- **A `Node3D`-typed `@export` does not resolve from a hand-authored `.tscn`** — it silently read
  null and the camera never moved. `ChaseCamera` now takes a `NodePath` and resolves it explicitly.
  Worth remembering for every scene authored outside the editor.

**Review pass found a fourth bug the drive tests could not have caught: steering was inverted.**
`InputRouter.steer` is `+1` for right, but a *positive* rotation about `+Y` turns the `-Z` forward
vector toward `-X` — left. Press D, car goes left. The headless tests missed it because they only
ever steered one direction and never checked which. Verified fixed by yaw sign: held right lock now
gives monotonically decreasing yaw, i.e. clockwise from above. Also fixed in the same pass: wheel
raycasts accepted wall faces as ground (free traction and a launch ramp off any building), six
buildings sat inside the carriageway at the junctions the circuit has to turn through, road slabs
were exactly coplanar with the ground plane and z-fought across their whole surface, and auto-right
teleported the car after that tick's forces had already been queued for its overturned pose.

**Open question for `P0-5d`:** slip angle is *lower* with drift held (12.6°) than without (16.4°),
because `drift_grip_scale` currently applies to all four wheels equally — that ploughs (understeer)
rather than rotating the car (oversteer). An arcade drift usually wants the rear to break away
first, which would need a per-axle bias the schema does not yet have. **Deliberately not added
before the user has driven it**, since which way it should feel is exactly what `P0-5d` decides.

`P0-5b` road widths live in `game/assets/authored/greybox_wanchai.json` as `real_width_m` ×
`widen_factor`, so the arcade divergence stays visible and re-drivable in seconds. `P0-5c` is
explicitly throwaway — `P2-5` owns the real camera.


### 2026-07-29 — Planning
Feasibility evaluated, region selected, engine and language decided, monetisation direction set.
Wrote `CLAUDE.md`, `README.md`, and the five docs in `docs/`. No code yet.

**Immediate next steps:** `git init`; then run `P0-2` (Z-value spike) and `P0-5` (grey-box fun
test) in parallel — one kills the data assumption, the other kills the design assumption.

### 2026-07-29 — `P0-3` Godot project scaffold
`game/` scaffolded on Godot 4.7.1 and machine-verified headlessly: clean import, all GDScript
parses, Mobile renderer and Jolt confirmed active at runtime, all six input actions bound to both
keyboard and gamepad.

Seams for `P0-5` laid deliberately: `InputRouter` autoload sampling in `_physics_process` (so no
gameplay script ever reads raw input, and the vehicle never reads a stale sample), `HandlingProfile`
+ `tuning/handling.tres` where the `.tres` is the **only** home for the numbers, and an FPS /
frame-time overlay autoload that gates itself out of release builds unless run with `--fps`.

**Export results:** macOS (57 MB) and Web (37 MB wasm) verified. Android also exports to a 25 MB
APK using the prebuilt template — no Gradle or Android SDK required, which is better than
expected. iOS fails only on a missing App Store Team ID, which is the correct failure: that
credential must never be committed.

**Discovered:** `rendering/textures/vram_compression/import_etc2_astc` must be enabled or Godot
refuses to export **any** arm64 target — including Apple Silicon macOS, not just phones. Needed for
the mobile tier regardless; the desktop export just surfaced it early.

**Not verified, and needs the user:** the cube scene rendering at 60fps in an actual window
(`tools/export.sh` builds it; running it needs a display), and anything on physical hardware
(`P0-3b`).

**Placeholder to replace:** bundle identifier `com.hktaxiq.game` in `game/export_presets.cfg`.
