# Progress

Living document. **Update this whenever a task changes status, a decision is made, or an open
question is answered.** Newest entries at the top of each log.

Last updated: 2026-08-01 (`P2-1` — the city streams and is inside the visible-triangle budget; LOD is now per mesh class, so the flyovers survive it)

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
buildings have no collision, there is no ground off the carriageway, and the flyovers are
unreachable (`Q13`). Those are `P2-1`'s, `P1-2`'s and `Q13`'s respectively.

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

**`P0-5` passed conditionally, not cleanly** — the user drove it, found the handling acceptable, and
judged that *fun* cannot be assessed from a grey box at all. See the decision log. The risk it
existed to retire stayed open through the entire ETL slice.

**`Q8` closed on 2026-07-31, and with it that risk.** Driving the real city, the user's verdict is
that an HK-like map is a fun enough gimmick already. The premise the whole project rests on —
recognition is the product — is now measured rather than assumed, and the expensive half of the art
direction is justified by it. Read narrowly, though: a gimmick carries a first session. The
register now tracks "novelty does not survive the first session" in its place, and that is `P3-*`'s
to answer, not Phase 1's.

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
| `P1-2t` | └ Terrain evaluation | ⚠️ **Measured — not viable as shipped** | 267 MB JPEG, 405k tris. See the decision log; needs a resampling pass to survive. |
| `P1-3` | Road graph | ✅ **Done** | 797 edges, 615 nodes, 217 turn restrictions, 96.3% connected, 0.80 s. `Q9`, `Q11` and `Q12` all resolved here. 234 tests, `ruff` clean. All four acceptance criteria met, the last by the user's eye. |
| `P1-4` | Road surface mesh | ✅ **Done** | 28,423 triangles, one draw call, kerbs and trimesh collision, 0.43 s. All 393 single-level junctions covered. Opened `Q13`. 259 tests, `ruff` clean. |
| `P1-5` | Fare nodes | ✅ **Done** | 29 nodes (14 stands, 15 PUDO) from 793 territory-wide points. All four acceptance criteria met and independently corroborated. Opened `Q14`, `Q15`. 297 tests, `ruff` clean. |
| `P1-6` | Export and manifest | ✅ **Done** | `city.json` + `python -m pipeline`; whole region in 4.4 s, byte-reproducible, 199 files / 102.6 MB. Validation catches what no single stage can. Opened `Q16`. 323 tests, `ruff` clean. |
| `P1-7` | Godot import | ✅ **Done** | **Phase 1 gate passed.** 65 tiles from `city.json`, georeferenced to 1 cm and checked in-engine by `verify_city.gd`. `DirAccess` tile listing deleted — it could never have worked in an export. 329 tests, `ruff` clean. |
| `P2-2` | `RoadGraph` runtime and debug overlay | ✅ **Done — all four criteria met** | One parse per scene, nearest-edge over a 25 m plan grid, lane centres from the **drawn** carriageway. Refuses all 60 off-grade edges (`Q13`), proven over 505 probes. Query time closed 2026-08-01: **p99 45 µs against a 1 ms budget**, timed over 15,865 region-wide probes. `verify_road_graph.gd` is the fourth verify tool. 331 tests, `ruff` clean. |
| `P2-1` | `CityStreamer` | ✅ **Done — pending the review verdict** | Threaded load/unload by distance to the published `aabb`, tiers at 100/250 m, 400 m unload, 15 m hysteresis, all in `streaming.tres`. Draw calls 70 → 53 against a 150 budget; **visible triangles 398,574 → 240,598 against 300k**, in budget for the first time. `verify_city_streamer.gd` is the fifth verify tool. Opened the shadow-cascade and LOD1-vs-thin-structure findings. |
| `P2-3` | Vehicle on real geometry | 🟢 **Unblocked** | `P2-3` now has `P2-2`'s lane-centre query to spawn against |
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
| Q13 | Nothing ramps between elevation levels. All 36 nodes where two levels meet step by a whole deck height — 6 m at a flyover, 8 m at a tunnel mouth | The elevated and underground networks are topologically connected and geometrically unreachable; **23.3% of the region's carriageway area** cannot be driven onto | `P2-2` | 🔴 **Open — raised 2026-07-30 by `P1-4`; narrowed 2026-07-31.** The ramps exist in `INFRASTRUCTURE` and sampling them beats the blend, but it does not close the step. `P2-2` takes the street-level slice — see the decision log |
| Q14 | Taxi stands carry **operating-time restrictions** in `Status_EN` — eight territory-wide, one in the region (Russell Street, cross-harbour 1200-0600) — and `P1-5` discards them | A part-time cross-harbour stand is modelled as a full-time one. Small today; it is exactly the kind of detail `P3-9`'s authenticity test would catch | `P3-1` | 🟡 **Open — raised 2026-07-31 by `P1-5`**, deliberately deferred |
| Q15 | Fare nodes snap to the road graph by **plan distance only**, because the published points are 2D | A stand under a flyover has nothing in it to prefer the street below over the deck above. No node in Wan Chai is affected — every winner is level 0 — but this shares a root cause with `Q13` | `P2-2` | 🟡 **Open — raised 2026-07-31 by `P1-5`**, not reachable with this source |
| Q17 | No CI. Every check is a local convention, and `tools/check.sh` runs only when someone remembers — on a repo where two verify tools shipped broken-and-green inside one commit | The checks exist and are now capable of failing; nothing makes them run. The Python half (`ruff`, `pytest`, `gdformat`) needs no engine and is nearly free to automate; the Godot half needs the binary plus export templates in a runner | — | ✅ **Resolved 2026-07-31** — GitHub Actions runs both halves. Export templates turned out not to be needed: only exports want them, and CI does not export. **Three of the six checks; the generated-asset contracts are not covered** — see the decision log |
| Q16 | One region measures **56.4 MB** in the PCK against a 200 MB bundle budget — before any vehicle, audio or UI asset, and before a second region. Unreferenced assets shipped alongside it until `P1-7` measured the export | Half the iOS cellular threshold is spent on the part of the game the player looks at but never touches. Either the tiers do not all ship, or LOD0 gets cheaper, or the budget was wrong | `P2-6` | 🔴 **Open — raised 2026-07-31 by `P1-6`** |

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
urgent — flag it before the roster work in Phase 4.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Road data lacks Z values | **High** | `P0-2` first. Fallbacks documented in `DATA_SOURCES.md`. Worst case: switch region to TST. |
| Real geometry isn't fun to drive | High → **Retired** | **Closed 2026-07-31.** `P0-5` could not answer this from a grey box, which is why it sat open through the whole ETL build. Answered by driving the real thing: the user's verdict on `scenes/dev/city_drive.tscn` is that an HK-like map is a fun enough gimmick on its own. The premise the project is built on holds. What replaces it is a *different* risk — see "Novelty does not survive the first session" below. |
| Novelty does not survive the first session | **Medium** | **New 2026-07-31, and it is the honest reading of the `Q8` verdict.** "Gimmick" was the user's own word, and a gimmick reliably carries one session. Recognition is doing the work, which is a strong start and not yet a loop. The mitigations were already scheduled and are now the ones that matter: `P3-*` for whether the fare loop sustains, and `P3-9`'s authenticity test with real HK drivers for whether recognition holds up to people who know the streets. Nothing to do differently today; the point is not to read `Q8` as more than it says. |
| Doesn't read as HK to locals | **High** | `P3-9` authenticity test with ≥3 real drivers; run again every phase after. |
| Perf misses 60fps on device floor | Medium | Budget defined up front; untextured merged tiles are the main lever; `P2-6` is a dedicated pass. |
| Source data quirks (dual carriageways, doubled junctions) | Medium → **Low** | **Mitigated 2026-07-30 by `P1-3`, and the directions confirmed against the street (`Q12`).** Both quirks turned up and both were handled: dual carriageways arrive as 6 opposed one-way pairs 1.96–3.85 m apart (median 2.9 m), and doubled junctions never form because nodes are made only at shared endpoints. **Closed 2026-07-30 by `P1-4`:** the residual — whether a 3 m pair becomes two ribbons or one — was not a decision. The widened ribbons overlap, so both carriageways draw as one continuous surface and no pair handling exists in the code. |
| Building meshes blow the triangle budget | Medium → **Low** | **Mitigated 2026-07-30 by `P1-2`.** The estimate was low: 2,200 buildings across the six sheets, not the ~900 extrapolated from one. Real region totals are **989k / 400k / 184k** triangles at LOD0/1/2, averaging 15.2k per tile at LOD0. Against a <300k *visible* budget that leaves room, but not much — a viewpoint holding LOD0 on the nearest ring plus LOD1 behind it lands in the low 300k range before occlusion. `P2-1`'s switch distances now decide this, not the ETL. |
| Grade separation is unreachable | Medium | **New 2026-07-30, raised by `P1-4` as `Q13`.** Deck heights are a constant per level, so nothing ramps: all 36 nodes joining two levels step by a whole deck height. The flyovers and the tunnels render correctly and cannot be driven onto. Not a blocker for the street-level slice, but `P2-2`'s nearest-edge query will put the car on a flyover unless it is told not to. |
| Terrain does not fit any budget | Medium | **New 2026-07-30.** Measured 267 MB of texture and 405k triangles for the ground alone — roughly 2× over on texture memory, triangles *and* bundle size simultaneously. Resampling to ~2 px/m and decimating to ~88k triangles brings it into range, but that work is not done and is not scheduled. Nothing in the tile output depends on it. |
| GDScript learning curve | Low | Small codebase; complexity lives in Python. |
| Landmark depiction IP | Low | Untextured massing; legal sight-check before launch (Phase 6). |
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
