# Decisions

Every decision this project has taken, as a standing statement. **Keyed by ID, never by date** —
look a decision up by the `Q` or task ID the code already cites, not by when it was made.

`PROGRESS.md` holds live state: what is in flight, what is measured, what is at risk. Chronology
lives in git. This file holds *why things are the way they are*.

## How to write a record

- **No dates.** A date appears only where it is the fact itself — a licence term, a data vintage.
- **No narration.** Not "this was tried, then reverted"; state what is true and what is refused.
  Relations are `**Superseded by.**` / `**See.**` links between IDs.
- **One claim per record.** A record grows only by carrying another *distinct* ⚠️ — never by
  narrating how the claim was reached. The longest records here (`P3-11`, `P2-7`, `P1-4`) are long
  because those tasks produced many separate reusable warnings, not because they tell a story.
- **Do not restate a spec another doc owns.** `ART_DESIGN.md` owns the palette, `ARCHITECTURE.md`
  owns the data contract. A record gives the claim, the reason and the evidence, then links.
- **Keep the numbers and the ⚠️.** A refusal without its measurement gets re-proposed.

---

## Index

| ID | Decision | Status |
|---|---|---|
| `Q1` | Road Network v2 carries no Z, but `ELEVATION` encodes the grade-separation level | ✅ Closed |
| `Q2` `Q3` `Q5` | Building data is fully scriptable — 6 sheets, ~44 MB each | ✅ Closed |
| `Q2′` `Q3′` | Height does not predict façade colour; the window period is not detectable from photographs | ⚠️ ID collision — see the record |
| `Q4` | Device floor is A13 (iOS) and Adreno 618 (Android), named as two separate floors | ✅ Closed |
| `Q6` | Does the region need Central for the circuit to feel complete? | 🟡 Deferred |
| `Q7` | Game-space origin is the region's north-west corner | ✅ Closed |
| `Q8` | The city itself is the fun | ✅ Closed |
| `Q9` | Read the 17 MB geodatabase, not the 539 MB of GML | ✅ Closed |
| `Q10` | Region-local origin **plus** a recorded `city_offset` | ✅ Closed |
| `Q11` | Road heights sample the terrain height field under every vertex | ✅ Closed |
| `Q12` | The source's one-way directions match the street | ✅ Closed |
| `Q13` | All 36 mixed-level nodes are ramps; driving the network is Phase 4 | 🟢 Largely answered |
| `Q14` | Taxi-stand operating-time restrictions are discarded by `P1-5` | 🟡 Open, deferred |
| `Q15` | Fare nodes snap by plan distance only, because the published points are 2D | 🟡 Open, not reachable with this source |
| `Q16` | LOD0 does not ship | ✅ Closed |
| `Q17` | CI runs `tools/check.sh` and cannot check the generated assets | ✅ Closed |
| `Q18` | Ground colour sits under a chroma knee; the land-cover classifier is refused | ✅ Closed |
| `Q19` | 5.17% of drawn carriageway has solid geometry standing in it at bumper height | 🔴 Open |
| `Q20` | Deck heights are sampled from `INFRASTRUCTURE`, not invented | ✅ Closed |
| `Q21` | Should level −1 carriageway be drawn at all? | 🟡 Open |
| `Q22` | 10.2% of off-grade carriageway hangs past its structure | 🟡 Open |
| `Q23` | Carriageway width is a property of the station, not of the edge | ✅ Closed |
| `Q24` | The at-grade road follows the ground; the cross-slope half is `Q19`'s | 🟢 Half closed |
| `Q25` | Ground is decimated once per tier and cut afterwards | ✅ Closed |
| `Q26` | Which look ships — the measured Hong Kong one or the clean/futuristic one? | ✅ Closed on candidate `C` — flat per-building colour, the user's call; closed ahead of `P3-9a`, which can now reopen it |
| `Q27` | `COLOR_0` is authored sRGB and must be linearised by the consumer | ✅ Closed |
| `Q28` | A per-object seed must be `flat`, or the GPU interpolates it into bands | ✅ Closed |
| `Q29` | The ground's normals are rebuilt in the fragment stage | ✅ Closed |
| `Q30` | The shipped façade palette is not the one `ART_DESIGN.md` authorises | 🔴 Open |
| `Q31` | The city's value range has an empty middle; the shadow fill is the last candidate | 🔴 Open |
| `Q32` | ~~`INFRASTRUCTURE` is the brightest large object in its frame~~ | 🟢 Closed as **wrong** |
| `Q33` | Every authored colour is `material reflectance × exposure_anchor` | ✅ Closed |
| `Q34` | Material is declared in a `materials:` table, not implied from height | ✅ Closed |
| `Q34′` | The ring weights are re-derived by a tool, against `Q37`'s survey | ✅ Closed |
| `Q35` | A per-building material draw gives a salt-and-pepper skyline | 🔴 Open |
| `Q36` | Wan Chai's ground is paving, not soil | ✅ Closed |
| `Q37` | 10.0% of the façade survey is atlas filler, not a photograph | ✅ Closed |
| `Q38` | `exposure_anchor` is baked into `COLOR_0` at build time | 🟡 Open, deliberately not fixed |
| `Q39` | `wall_sky_tint` is uniform, so a canyon wall takes a parapet's sky bounce | 🟡 Open |
| `Q40` | Can façade grammar be surveyed instead of hashed? | ✅ Closed — the surveyed verdicts ship in `TEXCOORD_1` (schema 6, +0.24 MB PCK); glazing and tint are the reader's, the dip gate is dead, and the overrides land dark behind `survey_apply = 0.0` until `Q26`. ⚠️ Rendering them at 1.0 for the first time found the consumer defect under `Q26` — the shader's `glazed` gate zeroes the punched grammar it also ships |
| `Q41` | A vision reader recovers the grammar the statistic could not | ✅ Closed — reader validated, region surveyed, and the majority-voted verdicts consumed into `TEXCOORD_1` beside `Q40`'s; refusals fall to the hash |
| `Q42` | The reader answers seven questions nobody consumes | 🟡 Open — `TEXCOORD_1.y` is reserved at a documented layout, so each rider now needs only its own validation, not a schema bump |
| `Q43` | `glazed` is materiality; `fenestrated` is geometry | ✅ Closed — shipped in `city_facade_clean.gdshader`, graded as `A″` under `Q26` |
| `Q44` | A punched opening is glass, not a black hole | ✅ Closed — the `unglazed_glassy` floor shipped (`P3-7a` W1), the `Q30` bar held, and the user accepted the `A‴` frames |
| `Q45` | One pane palette across the city reads as wallpaper | ✅ Closed — the fallback modulation shipped (`P3-7a` W2) and the user accepted the `A‴` frames; `Q35` bounds any retune |
| `Q46` | A grammar refusal draws a quiet tier, not invented fenestration | ✅ Closed — accepted in scope 2026-08-10 on a `survey_debug`-tinted drive test: refused stock reads quiet; the residual sightings sit on committed stock and open `Q47` |
| `Q47` | A committed verdict is right about the tower, wrong about the ground band | 🟡 Route decided 2026-08-10, join landed 2026-08-11 — iB1000 `P`-block metres where a tower meets one (data > survey-inferred; 310 stems carry a data boundary in `podiums.json`, contract argued 2026-08-11), `R4`'s floors→metres conversion elsewhere graded against the joined boundaries before packing; closes when the shipped boundary is graded |
| `Q48` | A contrast ratio measures banding where an `L*` profile could not | 🟡 Open as a **candidate only** — recorded 2026-08-13 from `P3-6`'s photo veto, nothing built and nothing scheduled; Probe 3 and mode 1 do not reach it, mode 4 does, and the evidence is one hero building graded by its author's eye |

| ID | Decision | Status |
|---|---|---|
| `P0-1` | Building data is fully scriptable; the top data risk is retired | ✅ Done |
| `P0-3` | Acceptance split — a scaffold is not a signed on-device build | ✅ Done / ⬜ `P0-3b` |
| `P0-4` | Config declares its **datum**, not just its CRS | ✅ Done |
| `P0-5` | Grey-box gate released conditionally; the fun question moved to `Q8` | ⚠️ Conditional |
| `P0-5a` | Custom raycast on `RigidBody3D`, not `VehicleBody3D` | ✅ Done |
| `P0-5b/c/d` | Four handling bugs no linter catches | ✅ Done |
| `P1-1` | The fetcher derives its own sheet list | ✅ Done |
| `P1-2` | Vertex clustering, whole-mesh tiling with one exception | ✅ Done |
| `P1-3` | `ELEVATION` must not key nodes; roads are clipped, buildings are not | ✅ Done |
| `P1-4` | The road surface is one mesh, capped per level, never merged | ✅ Done |
| `P1-5` | Fare nodes keep the **kerbside** position | ✅ Done |
| `P1-6` | The manifest **names** the other documents, and the export stage checks them | ✅ Done |
| `P1-7` | The manifest is the **only** route to the tiles | ✅ Done |
| `P2-1` | The city streams, and LOD is **per mesh class** | ✅ Done |
| `P2-2` | `RoadGraph` publishes the derived width, not the widening rule | ✅ Done |
| `P2-3` | The start line is **queried**, not written down | ✅ Done |
| `P2-5` | Buildings get collision from a **mesh name** | ✅ Done |
| `P2-7` | The off-grade carriageway lies on its structure | ✅ Done |
| `P3-7` | Window bands are procedural, and the storey height was measured | 🟡 Awaiting review |
| `P3-7a` | The task closes at what was judged, and the riders are gated on the look | ✅ Closed as shipped — the remainder is conditional on `P3-9a` reopening `Q26` |
| `P3-10` | The ground is a mesh class, and it collides | 🟡 Awaiting review |
| `P3-11` | The taxi is generated, and the chassis generates it | 🟡 Awaiting review |

| Topic | Decision | Status |
|---|---|---|
| Foundations | Engine, language, targets, region, building source, art direction, monetisation | ✅ Settled |
| Region bounds are WGS84 | Confirmed by measurement, and it selects different sheets | ✅ Settled |
| Licensing | GPLv3 out for store builds, contributions inbound MIT, generated data unrelicensable | ✅ Settled |
| Genre | Three references, three different questions | ✅ Settled |
| Two shadow cascades | 400 m, not four at 600 | ✅ Settled |
| Debug chrome | One owner, one key, **off by default** | ✅ Settled |
| The vertex stream | Carries both ground and building colour | ✅ Settled |
| Audit viewpoints | Seven fixed cameras, so a later change is graded against these | ✅ Settled |
| Rendering proposals | Eight evaluated; two survive | ✅ Settled |

---

# Questions

## `Q1` — Road Network v2 carries no Z, but `ELEVATION` encodes the level

**Status.** ✅ Closed · **Owner.** `P0-2`

**Claim.** The centrelines carry no Z ordinate. `ELEVATION` is an integer grade-separation level, and
`elevation_levels` in city config maps each level to a height offset.

**Why it matters.** The region was chosen for its grade separation, so a source with no vertical
information at all would have forced a fallback to Tsim Sha Tsui. The region holds.

**Consequences.** The offset is measured *from the ground*, not from the datum — see `Q11`. What the
levels cannot express is where a ramp climbs between them; that is `Q13`.

**See.** `DATA_SOURCES.md` "no true Z, but grade separation IS encoded" · `Q11` · `Q13`

## `Q2` `Q3` `Q5` — Building data is fully scriptable

**Status.** ✅ Closed · **Owner.** `P0-1`

**Claim.** The CSDI portal serves a territory-wide index of **3,456 sheet polygons**, each carrying
direct download URLs and a per-sheet `REVISIONDATE` that is the natural cache key. Six sheets cover
the region, ~44 MB each. **One public key covers all 3,456 sheets** — not per-user, not per-session,
and it must never be committed.

**Why.** The CKAN resource list points only at interactive portals, which is what produced the
earlier finding that buildings were the top data risk. The portal's own Downloads panel is the route.

**Consequences.** ⚠️ 612 triangles per building is far more than an LOD1 extrusion needs, so LOD
tiers are load-bearing rather than optional. Coordinates arrive **already in Godot's convention**
(`(easting, elevation, -northing)`), vertices are **unwelded at exactly 3.0 per triangle** so flat
shading is baked in, and "non-textured" describes the *buildings* — terrain ships with a JPEG.

**See.** `DATA_SOURCES.md` "Buildings" · `P1-1` · `P1-2`

## `Q2′` `Q3′` — Two façade-probe findings that reuse numbers already taken

**Status.** ⚠️ **ID collision — unresolved, flagged rather than renumbered**

**The collision.** The façade-colour probe records a finding as "`Q2`" (height does not predict
façade colour) and another as "`Q3`" (the window period is not reliably detectable from
photographs). Both numbers were already spent on the building-data questions above. Renumbering
would falsify citations elsewhere, so both readings are recorded here until the numbering is
settled deliberately.

**`Q2′` — height is not the signal.** Mean ΔE to the photographs: current 5 colours keyed by height
**24.93**; the same 5 best-matched instead of height-keyed 21.14; 5 clustered from the data 7.61;
**8 clustered 5.50**; 12 clustered 4.79. Height explains **6.1% of `L*`, 1.0% of `a*`, 1.6% of
`b*`**. Superseded in full by `Q34`, which measured the same thing at 16× the sample.

**`Q3′` — the window period is inconclusive, not negative.** Only 54% of walls gave a vertical period
at all, and the median came back **1.19 m against `P3-7`'s 2.77 m** — pinned at the search floor, so
the detector is landing on harmonics. This probe reads one triangle where `P3-7` autocorrelated whole
rectified walls. ⚠️ Answering it means rebuilding `P3-7`'s autocorrelation, not extending the probe.

**See.** `Q34` · `Q37` · `P3-7`

## `Q4` — Device floor: A13 (iOS) and Adreno 618 (Android)

**Status.** ✅ Closed

**Claim.** **iOS floor A13** — iPhone SE 2nd gen or iPhone 11. **Android floor Adreno 618 tier** —
Vulkan 1.1, 4 GB RAM, spanning Snapdragon 710/712/720G/730/730G.

**Why two floors and not one.** They answer different questions. The iOS floor is a *support-matrix*
question — A12 is off the current iOS train. The Android floor is a *performance* question, and it is
the only one that constrains the budget: A13 is roughly 3–4× the GPU throughput of the Adreno 618
tier, so anything holding 60 fps on the Android floor is free on iOS.

**Consequences.** The Mobile renderer requires Vulkan, so the real floor is "Vulkan 1.1 with a
maintained driver" before it is any particular chip. Chosen over a more conservative floor because
**Hong Kong skews high-end** — a global-market floor would cost art fidelity for users this TAM does
not have. It is what makes <150 draw calls, <300k triangles and <128 MB texture coherent rather than
arbitrary.

**See.** `ARCHITECTURE.md` "Performance budget"

## `Q6` — Does the region need Central for the circuit to feel complete?

**Status.** 🟡 Deferred to after `P3-9` · **Impact.** Scope

**Why it is open.** Recognition is the product (`Q8`), and whether the Wan Chai → Causeway Bay
circuit reads as complete is a question for the drivers rather than for a measurement.

**What depends on it.** `Q21`'s tunnel portals resolve only if the region grows east — the
Cross-Harbour descent happens outside the current bounds, so no height model can put a run there.

**See.** `Q21` · `P3-9`

## `Q7` — Game-space origin is the region's north-west corner

**Status.** ✅ Closed

**Claim.** East is `+X`, north is `−Z`, and zero sits at the region's **north-west** corner.

**Why.** The two halves were never equally free. **The sign of Z is forced by handedness** — Godot is
right-handed and Y-up, so rotating `+X` by 90° counter-clockwise about `+Y` lands on `−Z`. If east is
`+X`, north *must* be `−Z` or the city comes out mirrored. Only where zero sits was ever a choice,
and it is a pure translation. North-west is the only anchor that keeps the region in the positive
quadrant, so tile indices run `(0,0)`…`(10,5)` instead of `(0,0)`…`(10,−5)`.

**Consequences.** Origin northing is **ceiled** where easting is floored, rounding outward.
⚠️ **Non-negativity is a property of the region, not of the source data** — `fetch.py` downloads
every sheet that *intersects* the region, so geometry on disk runs past all four edges. **Clipping
before indexing is part of the data contract, not an optimisation.**

**Rejected.** A south-west origin, the GIS bbox convention — defensible, and it loses on negative
tile indices being a papercut paid every time anyone writes a filename or a debug print.

**See.** `ARCHITECTURE.md` "Coordinates" · `Q10`

## `Q8` — The city itself is the fun

**Status.** ✅ Closed · **Verdict.** The user's, after driving `scenes/dev/city_drive.tscn`

**Claim.** Driving an HK-like map is a fun enough gimmick on its own. The project's founding bet —
that accurate Hong Kong massing is itself the product — is measured rather than assumed, and
`ART_DESIGN.md`'s "accurate city, toy vehicles" rests on a verdict rather than on an assumption.

**Why it needed a drive.** `P0-5` cleared the handling and explicitly could not clear the premise. A
grey box cannot answer it; the real thing can, and did.

**Consequences.** ⚠️ **What it does not license.** *Gimmick* is the user's own word, and it is
accurate rather than dismissive — a gimmick carries a first session and says nothing about the tenth.
The founding risk is **replaced**, not deleted: "novelty does not survive the first session" is the
live entry in the register, and `P3-9a` asks it in its harshest form. Reading this verdict as
covering `P3-*` or `P3-9` is the failure mode.

**Method note.** The verdict cost one dev scene assembled from parts that already existed — the
cheapest build that lets the user judge turned out to be no new build at all, only wiring.

**See.** `PROGRESS.md` risk register · `P3-9a`

## `Q9` — Read the geodatabase, not the GML

**Status.** ✅ Closed · **Owner.** `P1-3`

**Claim.** Road Network v2 ships as a 17 MB file geodatabase and as 539 MB of GML. The pipeline reads
the geodatabase; every GML is dropped.

**See.** `DATA_SOURCES.md` "`Q9` — the geodatabase, and every GML dropped"

## `Q10` — Region-local origin plus a recorded `city_offset`

**Status.** ✅ Closed

**Claim.** Every region keeps its own local frame. `city.json` carries a `city_offset` translating a
region-local position into a city-wide frame.

**Why a single city-wide origin was rejected — on measurement.** Hong Kong spans 62.9 × 45.4 km,
which would put Wan Chai ~38 km out, where float32 spacing is **3.91 mm** — about 8% of the vehicle's
measured 50.6 mm suspension sag, on a `Transform3D` Godot stores as float32. That is the classic
large-world jitter problem, self-inflicted.

**The load-bearing constraint.** A city's declared `bounds` never change, because every region's
offset is measured from them. They are declared in config rather than derived from the regions that
exist — a derived frame would move each time a region was added and silently relocate everything
already published. Enforced three ways: a do-not-change warning in the city file, a loader check that
every region lies inside the bounds, and a test asserting the city frame is unchanged by adding a
region.

⚠️ **The number that decided this was wrong once.** float32 holds millimetre precision to **~16 km**
(2¹⁴), not the ~65 km first recorded — and that figure was the sole quantitative input here. Being 4×
optimistic made a city-wide origin look comfortably safe.

**See.** `ARCHITECTURE.md` "Two frames, and why" · `Q7`

## `Q11` — Road heights sample the terrain height field

**Status.** ✅ Closed · **Owner.** `P1-3`

**Claim.** `elevation_levels` is an offset per grade-separation level; what it is an offset *from* is
the sampled ground, taken from the terrain in the sheets the pipeline already downloads.
`roads.ground: terrain | datum` in city config, because a city whose sources carry no height field
must still be able to build.

**Evidence.** Level 0 median 0.00 → **4.21 m**; level 1 6.00 → 10.08 m; level −1 −8.00 → −3.53 m;
**zero vertices with no terrain under them**. The cross-check is the point: `P1-2` measured the
region's building bases at a median **4.29 m** by a completely separate path — glTF node matrices out
of the sheets. Roads land **8 cm below the doorways**, which is what a kerb is, and nothing was tuned
to make those agree.

**Rejected.** Sampling the nearest buildings' bases — available without the terrain but noisy, since
podium bases sit above the pavement (max 75.92 m). One authored offset per region — cheapest, and
wrong the moment the road climbs toward Kennedy Road, since the region spans 55 m of relief.

**See.** `Q1` · `P1-2`

## `Q12` — The source's one-way directions match the street

**Status.** ✅ Closed · **Verdict.** The user's, after flying the road-graph preview

**Claim.** Jaffe Road runs east, as `roadgraph.json` says. Direction reaches the graph through
`TRAVEL_DIRECTION` and the digitised vertex order, and that chain matches the real street.

**What it licenses.** `P3-3` can route traffic on the source's directions rather than treating them
as a first draft to be hand-corrected street by street — a materially different amount of work for
Causeway Bay and every city after.

⚠️ **Not a blanket warranty.** One street was checked, and the source's *geometry* is separately
quirky: **Lockhart Road is two-way carried as opposed one-way carriageways**, 2.73 / 3.07 / 3.41 m
apart — narrow enough to look like a doubled centreline until you measure it. Six opposed pairs
region-wide, 1.96–3.85 m apart, and that is a **floor**, counting only pairs sharing *both* endpoints.

**See.** `P1-3` · `P1-4`

## `Q13` — All 36 mixed-level nodes are ramps

**Status.** 🟢 Largely answered · **Owner.** `P2-2` → Phase 4 (`P4-1`)

**Claim.** Nothing in the source ramps between elevation levels *as an attribute*, but every one of
the 36 nodes joining two levels is a real ramp: **17 junctions, 13 attribute flips, 5 tunnel portals,
1 stub, and zero plan-coincident crossings.** After `P2-7`'s deck sampling the median step is
**0.04 m** and 26 of 36 are inside 0.5 m.

**Why the 13 look like a 6 m cliff.** They are **one road, split where the publisher's `ELEVATION`
changes partway up the ramp** — so both sides are wrong by about half a deck height each, in opposite
directions. What exposed the earlier "plan-coincident crossing" reading was the clearance:
**2.14–4.02 m is too low for a street to pass under.** The deck-above-terrain margins are bimodal
with a gap between +0.93 and +2.14 m, so the split is a property of the data rather than of where a
threshold was put.

**What remains.** The 5 portals and `e425`'s stub. A tunnel is a void, and the descent happens
outside the region — **8 m over a 42 m stub is a 19% grade** for the Cross-Harbour approach. It
resolves only if the region grows east (`Q6`).

**Consequences.** The network is still *closed to driving*: `nearest_edge` refuses all 60 off-grade
edges. Opening it is `P4-1`, which reverses `P2-2`'s refusal.

**Scope correction.** `Q13` was first written as "a third of the region's road area cannot be driven
onto". Measured: **60 of 797 edges (7.5%), 19.6% by length, 23.3% by carriageway area.**

**See.** `P2-7` · `Q20` · `Q21` · `Q6`

## `Q14` — Taxi-stand operating-time restrictions are discarded

**Status.** 🟡 Open, deferred deliberately · **Owner.** `P3-1`

**Claim.** `Status_EN` carries operating-time restrictions that `P1-5` drops, so a part-time
cross-harbour stand is modelled as full-time. `fares.json` has no field for it.

**Why deferred rather than fixed.** The source is already fetched, so adding it is a schema bump plus
a parser — cheap whenever the fare loop needs it, and premature before then.

**See.** `DATA_SOURCES.md` "Taxi Stands" · `P1-5`

## `Q15` — Fare nodes snap by plan distance only

**Status.** 🟡 Open — not reachable with this source · **Owner.** `P4-2`

**Claim.** The published fare points are 2D, so snapping compares plan distance alone. A stand under
a flyover cannot prefer the street below over the deck above.

**Why it is not a live defect.** No Wan Chai node is affected — every winner is level 0, with a
≥4.28 m margin.

**See.** `P1-5` · `Q13`

## `Q16` — LOD0 does not ship

**Status.** ✅ Closed · **Owner.** `P2-1` review

**Claim.** The exact-weld tier is dropped. Two tiers ship, with a single 250 m band edge and a 400 m
unload.

**Evidence.** Files 199 → 134; **PCK 51.6 → 21.1 MB (−59%)**; worst-case visible triangles
249,210 → **150,374 (−40%)**; worst-case resident 424,648 → 236,882; draw calls unchanged at 53. Both
budgets improve, and the second was the surprise — dropping a tier was meant to be a bundle decision,
and it also took 40% off the frame cost, because the tier removed was the one drawn nearest the
camera where the least is culled. For the business case: roughly **4–5 regions in a 200 MB download
instead of 2**.

⚠️ **Dropping the finest tier broke the `aabb` contract**, caught by `verify_city.gd` on 34 tiles.
`tiles[].aabb` was measured from the uncollapsed source, right only while tier 0 was an exact weld.
**And publishing tier 0's box is also wrong**: on `t_01_02` the 4.0 m tier stands **12.03 m taller**
than the 1.5 m tier, because `collapse` buckets on `floor(position / cell_m)` and averages, so a
*coarser* grid can leave an extreme vertex alone where a finer grid averaged it inward.
**Decimation does not only shrink a box.** The ETL publishes the union of the shipped tiers.

**What is not closed.** LOD0 can come back for one platform — 200 MB is the *iOS cellular* threshold
and desktop has no hard limit, so a desktop-only exact-weld tier is an export-filter question rather
than a settled no. One entry in `lod_cell_sizes_m` and a 3 s rebuild.

**The rule this earned.** ⚠️ **Bundle size is measured from a PCK, never summed from source files.**
That rule has now been wrong in both directions once each: the source saving here is 74.7 MB against
a PCK saving of 30.5 MB, and an earlier estimate of "the bundle drops to 28 MB" measured at 21.1.

**See.** `PROGRESS.md` metrics · `P2-1`

## `Q17` — CI runs `tools/check.sh` and cannot check the generated assets

**Status.** ✅ Closed

**Claim.** Two jobs on every push and PR: `ruff` + `pytest` on Python 3.11 and 3.13, and
`tools/check.sh` against a pinned Godot. **CI runs the script, not its steps** — repeating `--import`
and the warnings sweep as YAML would have been the obvious shape and wrong for the reason the script
exists.

**Why three of the six checks cannot run there.** `game/assets/generated/` is gitignored build
output, so `VERIFY_GENERATED=0` skips the verify tools and the script **prints that it skipped
them** — silence is the failure mode the script exists to break. Giving CI a city means running the
ETL there, 320 MB from a government server per push. Declined.

⚠️ **The skip's own guard was a false green, and the shape is reusable.** `if ((VERIFY_GENERATED))`
is the obvious bash and is a trapdoor under `set -u`: `=true` looks up a variable named `true`, dies
with `unbound variable` **and exits 0**; `=1x` reports "value too great for base", falls into the
skip branch, and prints `All checks passed`. A typo in the one knob that turns checks off would have
turned them all off, silently, green. Compared as a string now, with only an exact `0` skipping.

**Consequences.** The `godot` job does not install the ETL — `pip install -e "etl/[dev]"` drags in
pyogrio's bundled GDAL, numpy and pyproj, ~70 MB of geodata stack to format GDScript. It reads the
`gdtoolkit` pin out of `etl/pyproject.toml` with `tomllib`. ⚠️ That forced dropping the pip cache
from that job: `setup-python` keys its cache with **no job component**, so two jobs installing
different things share a key and whichever finishes last poisons the other.

**See.** `ARCHITECTURE.md` "CI"

## `Q18` — Ground colour sits under a chroma knee, and the classifier is refused

**Status.** ✅ Closed · **Owner.** `P3-10`

**Claim, colour half.** Chroma does not arrive in proportion to what is authored — there is a **knee**
an authored hue has to clear, and the ground's warmth sat under it. Measured on the faceted ground at
one hue angle and an identical `L*` 52.6: authored `C*` 6.81 → screen 1.95; 11.00 → 2.93;
**14.00 → 6.25**; 31.96 → 28.42. `TERRAIN(TB)` ships at `C*` 14.0, `L*` unchanged.

**Claim, z-fighting half.** `ground_sink_m: 0.20` clears the carriageway. **No z-fighting anywhere in
the region.** See `P3-10` for how the sink was sized.

⚠️ **The knee is one viewpoint's number and is not reusable.** On the region's hillside the same
change buys 5.09 `C*` at 200 m and nothing at 350 m; chroma also survives better where the ground
renders darker (`C*` 8–10 under `L*` 55, only 3–5 at `L*` 65–75). Distance and surface brightness
both move it, and the mechanism is **not identified** — `base_wash` is 0.0, so it is fog, the
shader's sky tint or tonemapping. ⚠️ Measured for *ground* — up-facing and bright. A façade is
vertical and darker; do not assume it there.

**Superseded.** ⚠️ **`Q36` supersedes the doubled chroma.** It was compensation for a lightness
problem `Q33` later fixed, and the pair was never re-graded. Read `Q36` before raising chroma again.

**Refused: the land-cover classifier — refused, not deferred, on a resolution mismatch no tuning
reaches.** The source is ~10 px/m and the ground clusters at **4 m**. Measured by area over the
terrain that ships (463,049 triangles, 1.695 km²) the classifier speaks to 25% of ground, and both
classes fall apart: the **water class is shadow** — 7.36% of roof area against 7.45% of open ground,
with **51.1% of the class on rooftops** — and the **vegetation class is edge speckle**, only 5.5% of
66,710 cells over 50% vegetation, falling as one-cell fringes tracing building footprints. Colouring
it would halo every building. ⚠️ **If parks are wanted the source is vector land-use polygons** —
crisp edges at any cell size and a clean key for `collapse`.

**See.** `ART_DESIGN.md` "Ground" · `Q29` · `Q33` · `Q36` · `P3-10`

## `Q19` — Solid geometry stands in the drawn carriageway

**Status.** 🔴 Open · **Owner.** `P3-3`

**Claim.** **5.17% of drawn carriageway has solid geometry standing in it at bumper height** —
`BUILDING` 1.72% and `INFRASTRUCTURE` 1.60% at grade, plus a further 1.87% on off-grade ribbon nobody
can reach. Measured on a 1 m plan grid, counting a cell only when geometry sits **0.3–2.0 m above the
deck**, so a podium overhanging the street 6 m up is Hong Kong working as intended.

**Two defects wearing one symptom, and they do not share a fix.** The `INFRASTRUCTURE` half shrinks
with `Q20`. The **`BUILDING` half this project chose**: `widen_default` is 1.6× and `GAME_DESIGN.md`
fixes the range at 1.3–1.8×, so widening eats the pavement first and then the ground-floor frontage.
That is a playability trade, not a bug — and the config already knew, holding expressways to 1.3×
with the comment *"widening them the same amount pushes the deck through the buildings beside it"*.
The same effect, found once, fixed locally, never checked across the network.

**Why it is not cosmetic.** Collision shipped, so this is invisible wall on roads the graph says are
legal, and `P3-3`'s traffic will route into it — `RoadGraph` has no idea any of it is there.

⚠️ **A first measurement read 13.71% by marking each triangle's bounding box**; sampling the actual
surfaces cut it to a third.

**What it wants.** A verify tool that **fails the build when the carriageway is occupied**. Both
halves want the same missing tool.

**See.** `Q20` · `Q24` · `P2-5`

## `Q20` — Deck heights are sampled from `INFRASTRUCTURE`

**Status.** ✅ Closed · **Owner.** `P2-7`

**Claim.** The off-grade carriageway's height is sampled from the `INFRASTRUCTURE` structure the
tiles already ship, not invented from a per-level offset.

**Why it was urgent rather than cosmetic.** `surface.py` ribbons every off-grade edge — 23.3% of
drawn carriageway — while the deck is *already there*, and the invented height was **below the
structure in 72% of samples**, median error −1.51 m. So the ribbon was buried inside the flyover it
should lie on. ⚠️ And the reason it was safe to defer had expired: `Q13` reads "topologically
connected and **geometrically unreachable**", true only while `roads.glb` was the only solid thing in
the world. Since collision shipped the structure is a collider, so the physical ramps are drivable.
**Nobody decided to open the elevated network; a change made for the camera opened it.**

**Evidence.** \|error\| p90 **4.131 → 0.095 m** against a 0.50 m criterion; deepest intrusion
4.67 → **0.48 m**; within ±0.10 m 1.5% → **92.7%**; median step at the 36 mixed nodes
6.00 → **0.19 m**. Graded by `tools/deck_error.py` against the shipped tiles, sharing no code with
the pipeline.

⚠️ **0.48 m against a 0.50 m gate is a thin margin, named as a risk rather than quoted as a pass.**
One station of 3,286 — nothing else is past 0.24 m — at **node 275**, the `CANAL ROAD FLYOVER`
touchdown. That is `Q13`'s residual; narrowing exposed it rather than creating it.

**See.** `P2-7` for the sampler's four wrong ideas and the two grading tools · `Q13` · `Q22`

## `Q21` — Should level −1 carriageway be drawn at all?

**Status.** 🟡 Open · **Owner.** Phase 4

**The question.** 15 edges, 5,010 m, **11.6% of carriageway area**, ribboned under the terrain where
nothing can see it and nobody can drive it — and solid since collision shipped. It costs triangles,
collider surface and bundle bytes for geometry with no viewer.

**Against removing it.** `P3-3` and Phase 4 want the *edges* to exist, and `roadgraph.json` would
keep all 15 either way.

**Why the heights cannot be improved.** `P2-7` could not help — a tunnel is a void, so there is no
structure to sample — and **11 of their 30 ends are clipped at the region boundary**, leaving the
Cross-Harbour portals ~42 m of run for an 8 m descent. It resolves only if the region grows east
(`Q6`).

**See.** `Q13` · `Q20` · `Q6`

## `Q22` — Off-grade carriageway hangs past its structure

**Status.** 🟡 Open · **Owner.** Phase 4

**Claim.** **10.2% of off-grade carriageway hangs in air**, after `Q23`'s narrowing took it from
20.1%. `tools/overhang.py` is the committed instrument and reads 10.0% against the 10.2% recorded by
hand.

**Why no width rule reaches the rest.** A single-lane ramp is drawn at the two-lane default; a source
centreline is not always centred on its deck; and `P2-1` decimates `INFRASTRUCTURE` on a 0.5 m cell.

**Impact.** Cosmetic while nothing off-grade is drivable. It stops being cosmetic in Phase 4: a wheel
leaving the deck finds air, not a parapet.

**See.** `Q23` · `P2-7`

## `Q23` — Carriageway width is a property of the station, not of the edge

**Status.** ✅ Closed · **Owner.** `P2-7`

**Claim.** Width is decided per station. Two rules, ordered: `widen_by_elevation_level: {1: 1.0}`
first, then the per-station structure test, with `structure_taper_m: 15.0` blending the transition.

**Why the level rule wins outright over the speed rule.** The speed table is a *preference* about how
much room a fast road wants; a level rule is a *statement about what the carriageway is sitting on*.
The Wan Chai Interchange matches both — signed at 70 and up on structure — so a speed-first reading
would still draw it 1.3× and hang it over the parapet. Both arguments the widening rests on are
at-grade arguments.

**Why the station rule was then needed.** `elevation_level` is an attribute of a whole edge, and a
road does not become a bridge at an edge boundary: `P2-7` lifted **16 level-0 edge ends** onto their
ramps, so those stations sat on a deck while their edge was still labelled level 0 — **1,070 m of
level-0 centreline across 28 edges, every metre widened at 1.6×.**

⚠️ **Level before station, and the ordering is load-bearing.** Letting the station win would re-widen
an off-grade edge wherever structure was never found — `ISLAND EASTERN CORRIDOR`'s stub reports every
station as off structure *precisely because* nothing is under it.

⚠️ **The residual does not go to zero, and should not.** `roads.py` decides "on structure"
*topologically*; `overhang.py` decides it *geometrically* (an upward face within 1 m). The populations
separate cleanly: stations narrowed sit a median **1.55 m** above ground, those left wide **0.15 m** —
abutments and retaining walls. **A street on an abutment is a street.** So 1,070 m was a geometric
upper bound and **546 m** is the honest count.

**Consequences.** `roadgraph.json` gained a per-vertex `on_structure`, because nothing downstream
could recover it — the published `y` cannot identify structure, a level-0 road climbing the
Mid-Levels reaching 49 m while at grade. The width travels as a **fourth column of `_Edge.points`**,
not a parallel array, so `dedupe` and `trim` carry it for free.

**See.** `ARCHITECTURE.md` data contract · `P2-7` · `Q22`

## `Q24` — The at-grade road follows the ground

**Status.** 🟢 Half closed; the other half is `Q19`'s · **Owner.** `roads.py`

**Claim.** `roads.ground_profile` densifies at-grade edges at 10 m, samples the terrain, then
**thins** at a 0.10 m vertical error — so the road follows the ground instead of chording over it.

**Why thinning, not just densifying.** Densifying alone is the obvious implementation and is twice
the price for nothing: 6,222 stations against 3,506, for the same 0.11% proud. Wan Chai is mostly
flat and a flat street needs no vertex it does not already have — **504 of the 721 at-grade edges
gained nothing at all**. 0.10 m is half the sink, so a station kept at that tolerance cannot poke
through on its own.

**Evidence.** Carriageway area with ground proud **3.289% → 1.898%**; at the centreline
**2.274% → 0.712%**; road surface triangles 25,028 → 28,170; graph query p99 45 → 47 µs against a
1 ms budget.

⚠️ **Across the road is untouched, and it is `Q19`'s.** The ribbon is drawn flat across a width the
1.6× widening made too wide, so it cuts into a cross-slope at the kerb — the outer rim moved only
5.393% → 4.360%. The residual floor is the tunnel portals (`Q21`), which no station spacing reaches.

⚠️ **A screenshot alone would have suggested this failed.** At CAROLINE HILL ROAD the centreline went
from 2.98 m under the ground to **0.32 m** — a road again from the driver's seat — while the *same
camera* barely changes, because what is left there is the outer metre of a widened ribbon cutting
into the hillside. The banded measurement is both the proof and the accounting.

**See.** `Q19` · `Q21` · `P3-10`

## `Q25` — Ground is decimated once per tier and cut afterwards

**Status.** ✅ Closed · **Owner.** `P1-2` / `P3-10`

**Claim.** `_tile_ground` merges the region's ground, decimates it **once per tier**, and cuts the
result — the reverse of every other class.

**Why.** `collapse` bins world-anchored but takes `_cluster_mean` over *the members present in that
mesh*. Terrain split across tiles before collapsing averages differently either side of a boundary,
so the two sides land on different positions and the sheet pulls apart.

**Evidence.** Region holes **1.76% → 0.76%**; within 2 m of a boundary **15.65% → 0.42%**, *below*
the 0.54% interior rate, so the boundary stopped being special. Triangles unchanged.
`INFRASTRUCTURE` comes out byte-identical, which is the cheapest proof only the ground moved.

**Why buildings must not be treated this way.** A building is assigned to a tile *whole*, so it is
never cut and has no seam to open — and collapsing the region's massing as one mesh would merge
neighbours across the streets between them. **The ground is the only class that is both cut and
continuous.** `INFRASTRUCTURE` is cut too and tears the same way, but a viaduct is a closed volume,
so its tears are slivers inside solid geometry rather than holes.

⚠️ **Clip to the region before merging.** The sheets are 750 m squares against a 1.65 × 0.9 km
region, so most of the source terrain is outside it — geometry every other class discards in `assign`
*before* `collapse` sees it. Decimating it anyway cost **924 MB of peak RSS** against **657 MB**
clipped, for byte-identical interior tiles. The one-tile margin is load-bearing: cutting flush at the
region edge trades the tile seam for a region-boundary one.

⚠️ **A fix that changes coverage changes every share computed over it.** Closing these holes raised
`ground_clearance`'s sampled share to 1.0003% against a 1.000% gate without any ground moving —
3.35% more of the carriageway simply became *measurable*, at the region's own proud rate.
Like-for-like over what both bundles could see: **2.181% → 2.205%**. Re-run the grader that owns a
number, not only the ones a checklist names.

**See.** `Q24` · `P3-10`

## `Q26` — Which look ships?

**Status.** ✅ **Closed 2026-08-17 — candidate `C` ships.** Accurate massing, flat per-building
colour, no façade fabric and no surveyed verdicts. The user's call, on the configuration that had
already been the working default since 2026-08-16 · **Owner.** `P3-9a`, which can reopen it

### ✅ The verdict — `C`, and what closing on it costs

**No asset moved to close this.** `city_facade.tres` already carried `C`, byte-verified against the
graded frames at both audit cameras on the 2026-08-16 swap, so this is a verdict on what was
shipping rather than a change to it. The three looks stay three files: closing the question retires
the *question*, not the alternatives, and `cp city_facade_elements.tres city_facade.tres` still
restores `A‴` exactly.

⚠️ **It closes ahead of its own stated confirmatory half, and that is a real deviation.** Every
version of this record said the ≥3-HK-driver recognition round at `P3-9a` grades whatever ships.
That round has not run. So `C` ships on the user's own judgement — given twice, 2026-08-16 as the
default and 2026-08-17 as the verdict — and the driver round changes role: it is no longer what
*decides* this, it is the test that can **reopen** it. A recognition failure at `P3-9a` that the
drivers attribute to flat surface reopens `Q26` with `A‴` and `B` still on disk and the tables
below still valid. Nothing about that path is expensive, which is most of why closing early is
affordable.

⚠️ **The 2026-08-09 enable of `A‴` is not superseded as evidence, and `A‴` was never faulted.** It
was a verdict on the fixed render and it stands. What this closure says is which of two accepted
looks ships, not that the other is wrong — anyone re-reading for the *reason* will not find a fault
in `A‴`, because there is not one.

🔴 **The whole surveyed-surface chain now ships dark, and this is the price.** `survey_apply = 0.0`
under `C`, so `Q40`'s reader-glazed verdicts and surveyed tint, `Q41`'s grammar, `Q42`'s reserved
`TEXCOORD_1.y` riders and `Q47`'s podium pack are all shipped, validated, and consumed by no pixel
in the default build — about **$21 of paid reads** and **+0.24 MB of PCK** with no viewer. That does
not make any of it wrong; it is one `cp` from being consumed, and the reader survey is what made
`A‴` a *measured* look rather than an invented one. But **`P3-7a`'s remaining riders now have no
shipping consumer**, and whether to continue paying for them — the ground-band batch above all — is
a scope call this closure deliberately does **not** make.

**`Q30` is re-owned rather than answered.** It was parked on this verdict. Under `C` the elements'
chroma addition is gone — `C` is the low-chroma end of the set (whole-frame mean `C*` 16.56
`street` / 15.30 `kerb`, against `A‴`'s 17.72 / 16.08) — so the 26.4%-over-`C*`-20 that `Q30`
reports is now **entirely the base palette**: `facade_hue` × the height-band weights, baked into
`COLOR_0` by the ETL and therefore present under all three looks. `Q30` stays open, better posed,
and owned by `hong_kong.yaml` / `ART_DESIGN.md`.

**The palette does not move.** "If the clean look wins, the palette moves from the shader's
`base_wash` into `height_bands`" was conditional on `A`. It never fires.

✅ **The swap was verified rather than assumed.** The shipped `city_facade.tres` renders
byte-identical frames to the graded `C` at both audit cameras, and the parameter block differs from
`city_facade_elements.tres` by exactly the eight documented values and no others.

🔴 **Consequence for `P3-7a`, and it is a trap.** Every remaining rider on that task — `W4`, the
`emphasis` and storey-pitch riders, `balconies`, the podium pack — is consumed behind
`survey_apply`, which is now `0.0` in the shipped file. They will land **invisible in the default
build**. `PLAN.md` already requires them to land dark and to keep the `C` look byte-identical, so
this does not change what is built; what it changes is that the criterion is now satisfied
*trivially*, and a rider that draws nothing at all would pass it. **Grade every remaining `P3-7a`
step against `city_facade_elements.tres`, not against the default**, or the grading measures a
uniform that is switched off.

**The question.** The measured Hong Kong look — `P3-7`'s accurate window bands, called dull — or
`city_facade_clean`, which is bolder and is *not* what Wan Chai looks like. A third candidate
exists and shipped as the default until 2026-08-09: **elements off, flat per-building colour on
accurate massing**.

**Why it is a verdict.** The whole art direction rests on "accurate city, toy vehicles", and
recognition is the product (`Q8`). A white city with amber accent plinths keeps the accurate
*massing* and abandons the accurate *surface* — which may be the right trade or may be the one thing
that cannot be traded. Both looks are one `cp` apart and neither needs a rebuild, so this can go to
the ≥3 HK drivers as an A/B rather than being decided in advance.

**The comparison set.** `build/driver/q26_{C,A,B}_cf19201/{street,skyline,kerb}/`, shot against
`cf19201` with the region rebuilt and synced first, `--debug-view=off`, on the fixed audit cameras.
`C` is what ships, `A` is the clean look with its seven elements on, `B` is `city_facade_warm.tres`.
All nine frames differ by hash, so each swap reached the frame. `build/driver/` is gitignored, so the
set does not survive a clone — but unlike the dangling commit below it is **regenerable**, and the
three candidate definitions here plus `ART_DESIGN.md`'s cameras are what regenerate it. ⚠️ Shots
before `Q27` closed — `build/driver/h4` and `build/driver/clean` — remain unusable, because albedo
was reaching the screen at a third strength in all of them.

⚠️ **Candidate `A` was not reproducible as written.** The recovery note in `city_facade.tres` gave
`solid_share 0.38` and pointed at `42da0fb`, a commit contained in no branch. No commit in the
repository has ever carried `0.38`; the switched-on value is **`0.27`**, and `542cac3` is an ancestor
of `main` whose `city_facade.tres` is byte-identical to the dangling one. Both are corrected in the
file. A look that is "one `cp` apart" has to survive a fresh clone to be one `cp` apart.

**What the set measures.** Responding share is the fraction of the frame each look moves by
≥ 0.5 `L*` against `C`, from `tools/frame_stats.py`:

| viewpoint | `A` responds | `A` \|d`L*`\| p90 | `B` responds | `B` \|d`L*`\| p90 |
|---|---|---|---|---|
| `street` | 24.3% | 17.82 | **50.9%** | 13.30 |
| `skyline` | 8.9% | 7.21 | **60.9%** | 7.99 |
| `kerb` | 14.1% | 23.09 | **42.9%** | 13.81 |

**`B` touches two to seven times more of the frame than `A`, and moves each pixel less.** That is the
2.4 m pitch against the 9 m bay, in numbers: the measured look textures nearly everything faintly,
the clean look articulates fewer surfaces strongly. It is the same observation as "reads as noise
rather than as architecture" in `city_facade.tres`, without relying on the phrasing.

**`A` is close to absent at skyline** — 8.9% responding, whole-frame `L*` 61.3 → 61.0 and `C*`
unchanged — because its 140–244 m fade retires the detail. `B`'s grid survives to the horizon. So the
massing-and-silhouette viewpoint barely discriminates `A` from `C`, and whoever runs the A/B should
know the choice is a street-level one.

⚠️ **`A` adds chroma to a distribution `Q30` already calls oversaturated, and `B` does not.** The
clean figure is the whole frame, where all three are measured over the same pixels: `C*` mean at
`street` is 16.6 (`C`) → **18.8** (`A`) → 16.7 (`B`). On responding pixels at `kerb`, `C*` p90 goes
20.7 → **32.2** under `A` and 32.5 → 35.2 under `B` — ⚠️ read each arrow alone and never across, as a
responding set is defined per comparison and those two are statistics over different pixels. The
cause is visible in the frames: `A`'s glazing reflects sky and its accent courses are saturated red,
blue and orange, so a large share of wall area stops showing the building's **surveyed** hue at all.
`B` leaves that hue legible. `Q37` and `Q34` paid for that hue, which makes this a cost and not only
a preference.

⚠️ **If the clean look wins, the palette moves** from the shader's `base_wash` into `height_bands` in
the city config, where CLAUDE.md says palettes live.

**Evidence that arrived late.** The source massing carries **real window reveals and structural fins
on a minority of towers**, so with the shader grid off the city draws surface three ways at once, and
the relief aliases into speckle at the distance it is seen from. That was not on the table when this
question was written.

⚠️ **`B` is shown with three known defects and the verdict has to be told so.** `city_facade.gdshader`
was forked into the clean one and then fixed in three places never back-ported — `band()` without the
analytic duty-cycle convergence, `along_m` taken from the face normal, and a 90–240 m fade safe
against the 250 m LOD1 switch only by accident. `city_facade_warm.tres`'s header is the authority on
that list; if one is ever ported, that is the file to correct and this paragraph follows it. They are
why `B`'s skyline responds across 60.9% of the frame at low amplitude, so the figure is partly moiré
and not only texture. Porting them first was rejected: the point of `city_facade_warm.tres` is to be
a faithful record of what `P3-7` measured, and a driver judging a repaired variant would be judging
something the repo does not have. The three are cheap to port **after** a verdict that wants them.

### ✅ The verdict does not move with the tone curve

`Q31` found `adjustment_contrast = 1.14` to be the dominant term in the city's value distribution and
parked its own fix behind this question, on the grounds that "the tone curve is the thing three
drivers are about to judge `Q26` through". That made the two questions mutually blocking, and the
dependency had never been measured. It now has: the three candidates were re-shot at contrast **1.14
and 1.00**, on the same three audit cameras, and paired **within** each contrast.

| viewpoint | `A` responds | `A` p90 | `B` responds | `B` p90 | `B`:`A` |
|---|---|---|---|---|---|
| `street` 1.14 | 24.3% | 17.82 | 50.9% | 13.30 | **2.10** |
| `street` 1.00 | 24.2% | 15.76 | 51.0% | 11.77 | **2.10** |
| `skyline` 1.14 | 8.9% | 7.21 | 60.9% | 7.99 | **6.84** |
| `skyline` 1.00 | 8.4% | 6.68 | 59.9% | 6.98 | **7.10** |
| `kerb` 1.14 | 14.1% | 23.09 | 42.9% | 13.81 | **3.05** |
| `kerb` 1.00 | 14.0% | 20.24 | 42.6% | 12.14 | **3.05** |

✅ **All nine archived frames were re-shot and came out byte-identical** — `A` and `B` at all three
viewpoints, `C` at `kerb`, `C` at `street` from the gate run, and `C` at `skyline` from two
independent shots that agree with each other and with the archive. That is the reproduction claim;
the 1.14 rows matching the published table follows from it and is not separate evidence.

⚠️ **`C` at `skyline` cost five attempts to yield two clean frames.** The batch run was ruined by the
camera hazard below; of the four re-shoots after it, two died to the renderer stall and two came out
clean and agreeing. The rule that finally produced it is the rule stated below: shoot twice, `cmp`,
and discard any frame that stands alone.

⚠️ The gap is **six commits and under three hours, all of them docs**. This shows the build is
stable, not that it survives change.

**Nothing candidate-specific survives the curve.** Responding share moves by at most 1.0 point
anywhere; the `B`:`A` ratio — the read the pivot scaling divides out of — holds at 2.10 and 3.05
exactly and moves 6.84 → 7.10 at `skyline`. Magnitudes shrink uniformly: p90 retains a mean of
**0.888** across all six pairings, spread 0.874–0.926, against a null of **`1/1.14 = 0.877`** stated
before the shoot. The contrast adjustment scales every difference by its pivot factor and does
nothing else.

⚠️ **The prediction made in advance was wrong, and it is recorded because it was wrong.** `B` was
expected to lose more than `A` — broad-and-faint differences should fall under a fixed 0.5 `L*`
threshold first. Neither lost: `A` retained 95–100% of its responding share and `B` 98–100%. The
differences between these looks sit far enough above the threshold that a 12% shrink cannot reach it.

🔴 **This is a one-sided test and does not license the reverse claim.** It shows the candidates stay
*measurably* separated, in the same order, under both curves. Measurable difference is necessary for
a preference, not sufficient for one, so this cannot show that a *human* verdict is stable — only
that the specific mechanism `Q31` feared is absent. `Q40` died of taking a reader's ability to see a
thing as evidence a statistic could measure it; the same overclaim run backwards is available here
and is refused.

**What it releases.** `Q26` and `Q31` **decouple**. `Q31`'s contrast change no longer waits on this
verdict, and the driver panel can be shown frames under whichever curve ships.

### ⚠️ The shoot found a reproducibility hazard in the preview scene

**Using the machine during a preview shoot ruins the frame.** `drive.sh` steals focus for the length
of a run; a click on that window puts `free_look_camera.gd` into `MOUSE_MODE_CAPTURED`, and every
mouse movement after it rotates the audit camera. Three runs of one configuration returned
whole-frame `L*` of **41.39** (correct), **30.94** (pitched down) and **55.75** (aimed at the sky).

⚠️ **Position survives and only the aim moves, which is what makes it dangerous.** The result is a
plausible frame of the wrong thing, not a visibly broken one. The run exits `DRIVER OK`,
`tools/check.sh` is not involved, and the `camera:` line prints the transform requested at placement
— so the log of a ruined frame is byte-identical to the log of a good one. Two of eighteen frames
were lost this way, and the only thing that caught them was a byte-comparison against an archived
shot. **A preview audit frame is not evidence until it has been checked against a sibling.**

🔴 **The first diagnosis of this was wrong and is recorded because the wrong one is plausible.** It
blamed `free_look_camera.gd`'s `built` → `frame()` auto-framing racing the driver's camera placement.
Two things refute it: `frame()` sets position *and* orientation, lifting the camera ~600 m to an
aerial vantage, whereas both ruined frames kept street-level position; and `driver.gd:150-153`
already awaits a process frame precisely so `frame()` runs first. By elimination, mouse-look is the
only path in that script that rotates without translating. **The evidence that separated them was
looking at the frames** — the telemetry, the logs and the exit codes are identical either way.

✅ **The preview scene is fully settled by `t=0.8`**, and `t=0.8`, `t=1.5` and `t=3.0` are
byte-identical. The three-second runs the archived set used were buying nothing.

### 🔴 Candidate `A′` is not gradeable yet — the glazed gate deletes the punched city

`A′` — `survey_apply = 1.0` **plus** the seven un-parked fabric values, "measured surface on accurate
massing" — was shot at `e5fb391` on all three cameras and is in `build/driver/q26b/`. The shoot
itself is clean, and it found a defect that no statistic in this record would have caught.

**The shoot reproduces.** 18 runs, three candidates × three cameras × two runs, zero `SHADER ERROR`.
Every `r1`/`r2` pair is byte-identical, so no frame was lost to the camera hazard above, and `t=0.8`
matches `t=3.0` in all nine. `C→A` returns **24.3% / 17.82**, **8.9% / 7.21**, **14.1% / 23.09** —
the published table to the decimal, at a commit six ahead of `cf19201` and across `Q40`/`Q41`'s
schema-6 change. `C` is byte-identical to the archive at all three viewpoints, which is what licenses
reading `B`'s published row beside the new ones without re-shooting it.

⚠️ **One archived frame differs by a single pixel.** `A`/`street` failed `cmp` against `cf19201`;
the diff is **1 pixel of 2,073,600, one channel, delta 1**, and the frames are identical to the
grader (0.0% responding). So the shoot-twice-and-`cmp` rule has a false-positive mode: a byte
difference is the *trigger* to look, not the verdict. Grade the diff before discarding the frame.

**What `A′` measures, taken at face value:**

| viewpoint | `A` responds | `A` p90 | `A′` responds | `A′` p90 | `A′`→ whole-frame `C*` |
|---|---|---|---|---|---|
| `street` | 24.3% | 17.82 | **14.5%** | 13.37 | 18.8 → **18.1** (`C` 16.6) |
| `skyline` | 8.9% | 7.21 | **10.3%** | 6.75 | 15.7 → 15.7 (`C` 15.7) |
| `kerb` | 14.1% | 23.09 | **8.8%** | 22.37 | 16.7 → **15.9** (`C` 15.3) |

Read alone, that says the survey makes `A` quieter and gives back roughly half its chroma cost at
`kerb` and a third at `street` — which would answer part of `Q30`. 🔴 **It does not say that, and the
frames are why.**

**The cause. `glazed` means two different things on the two sides of the contract.** To the reader it
is "whether glazing **dominates** the façade area" (`facade_grammar.py`); `punched` is defined there
as "openings cut into a **dominant solid** wall — tenements, public housing, concrete frames". So
`(glazed=false, grammar=punched)` is the coherent, expected pair, and `building_verdicts` nulls only
the two genuine contradictions, `(true, blank)` and `(false, curtain)`. **The ETL is correct.** The
shader then reads `glazed` as "has any fenestration at all": `tower = ribbon_mask * glazed * above *
fade` at `city_facade_clean.gdshader:694` zeroes the entire grid. Its own comment — "`blank` was
already handled through `glazed`" — is the tell: the glazed axis was collapsed onto the `blank` case,
and `punched` arrives through the same door.

**Measured over the shipped tiles: 59.7% of vertices carry a committed grammar that describes
fenestration, and 43.4% of the city renders blank anyway** — `punched` alone is **39.3%**, and every
one of its 251,720 vertices is `glazed=false` (100%, by construction, not by accident). `fin` loses
82.7% of itself the same way and `mixed` 29.5%. The dominant real Hennessy Road stock is exactly the
class that disappears.

⚠️ **Those shares were first published as "of wall vertices" and they are not** — re-derived at
`Q43`, all four reproduce exactly on a denominator of **every lod0 vertex in the tiles, ground and
structure included**, which is 639,834 of them. Ground and road carry no grammar by construction, so
they dilute every row. Against the population the gate actually acts on — 346,656 lod0 vertices that
are facade-marked and steeper than `wall_normal_max` — **the defect is half again as large**: 75.0%
carry a committed grammar, `punched` is **50.1%**, and **66.2% of the city's walls are forced solid**.
The finding was never in doubt; the denominator was, and it understated it.

⚠️ **The punched treatment already exists and is unreachable.** Line 637 sets `h_ratio = glass_ratio
* 0.62` under the comment "Punched windows in solid wall — the older stock", and the grammar override
at 615–624 will duly set `treatment = 3.0` — then feed a mask multiplied by `glazed = 0`. The feature
was written, shipped, and has never drawn a pixel.

**So the `A′` row above grades a defect, not a look.** Its lower responding share is mostly deleted
fenestration, not a measured finding about Hong Kong, and its chroma improvement is bought the same
way. **`A′` must not go in front of drivers in this state**, and the numbers must not be quoted as
`Q40`'s surveyed city being quieter than the hash.

✅ **This is the argument for shooting the frames rather than the statistics.** Every number in the
table above is plausible, self-consistent, and reproduces on a re-run. `Q40` closed on evidence that
the plumbing was correct; it was — the defect is one gate downstream, on a path that had never been
rendered because `survey_apply` shipped at 0.0.

**Settled at `Q43`, and re-shot as `A″`.** The gate was split rather than forced: `fenestrated` is
geometry, `glazed` is materiality, and `blank` is the only verdict that denies openings. Twelve runs
at that commit, `build/driver/q43/`, every `r1`/`r2` pair byte-identical and `t=0.8` matching `t=3.0`
in all six — and **all twelve `C` frames are byte-identical to `q26b`**, so the parked look is
unmoved and the baseline is the same one the rows below were graded against.

| viewpoint | | `A` (hash) | `A′` (defect) | `A″` (`Q43`) | `C` |
|---|---|---|---|---|---|
| `street` | responds | 24.3% | 14.5% | **19.7%** | — |
| | p90 \|d`L*`\| | 17.82 | 13.37 | **32.43** | — |
| | mean `C*` | 18.84 | 18.09 | **17.96** | 16.56 |
| `skyline` | responds | 8.9% | 10.3% | **11.6%** | — |
| | p90 \|d`L*`\| | 7.21 | 6.75 | **9.47** | — |
| | mean `C*` | 15.66 | 15.67 | **15.62** | 15.68 |
| `kerb` | responds | 14.1% | 8.8% | **14.8%** | — |
| | p90 \|d`L*`\| | 23.09 | 22.37 | **36.79** | — |
| | mean `C*` | 16.73 | 15.93 | **15.87** | 15.30 |

**The fenestration is back, and the frames say so in the right shape.** Responding share rises off
`A′` at every viewpoint, and at `kerb` it passes the hash — 14.8% against 14.1% — which is what
surveyed `punched` stock drawing where the hash had made it solid looks like. It does *not* return to
`A` at `street` (19.7% against 24.3%), and should not: the survey says some of those walls really are
blank, and a punched opening is narrower than a ribbon by `glass_ratio * 0.62`.

**The p90 spread is the half that is new rather than restored.** It roughly doubles against `A′` at
`street` (13.37 → 32.43) and `kerb` (22.37 → 36.79). A matte recess against pale concrete is a far
larger lightness step than tinted glass carrying a sky mirror — so buildings now differ in *material*
and not only in window spacing, which is what `Q40` was run to buy.

✅ **It answers part of `Q30` for free, and this time not by deletion.** `A′` bought its chroma back
by removing the glass; `A″` keeps every opening and still lands *below* `A′` on all three cameras.
Against `C`, `A″` gives back **39% of `A`'s chroma cost at `street`** (+1.40 against +2.28) and **60%
at `kerb`** (+0.57 against +1.43); at `skyline` it sits 0.06 *under* `C`. Matte openings take no sky
reflection, and sky reflection was a chunk of why `A` raised `C*` above what `ART_DESIGN.md`
sanctions.

**Re-shot as `A‴` after `P3-7a`'s `W1`/`W2` (2026-08-09, commit `422ee16`) — the candidate the
verdict now grades.** The user judged two of `A″`'s defects directly from its frames — punched
openings drawn as matte holes (`Q44`) and one pane palette city-wide (`Q45`) — so `A″` is
superseded, not merely refined: grading drivers on a look already called wrong wastes the drivers.
`A‴` is `A″`'s tuning plus `unglazed_glassy 0.65`, `pane_l_jitter 6.0`, `pane_b_jitter 4.0`,
`pane_hue_pull 0.25`, all shader-side, no rebuild. Shot into `build/driver/q26_A3_422ee16/`,
every viewpoint sibling-`cmp`'d; one kerb frame arrived corrupt (78 distinct colours against 185)
and was caught by exactly that protocol — three clean kerb runs agree byte for byte.

| viewpoint | | `A″` (`Q43`) | `A‴` (`P3-7a`) | `C` |
|---|---|---|---|---|
| `street` | responds | 19.7% | **19.7%** | — |
| | p90 \|d`L*`\| | 32.43 | **19.15** | — |
| | mean `C*` | 17.96 | **17.72** | 16.56 |
| `skyline` | responds | 11.6% | **11.6%** | — |
| | p90 \|d`L*`\| | 9.47 | **9.03** | — |
| | mean `C*` | 15.62 | **15.63** | 15.68 |
| `kerb` | responds | 14.8% | **14.7%** | — |
| | p90 \|d`L*`\| | 36.79 | **24.37** | — |
| | mean `C*` | 15.87 | **16.08** | 15.30 |

**The shape is the intended one: same reach, smaller step, glass where holes were.** Responding
share is unchanged at every viewpoint — the same walls answer — while p90 \|d`L*`\| falls 41% at
`street` and 34% at `kerb`: an opening that is dark glass carrying a sky mirror sits far
closer to pale concrete than a matte near-black recess does, so the buildings still differ in
material without the openings reading as punched-out voids.

✅ **The `Q30` bar (`Q44`'s acceptance) holds on all three cameras, and only `kerb` re-spent.**
Against `C`, the chroma cost is `street` **+1.16** (`A″` +1.40, bar `A` +2.28), `kerb` **+0.78**
(`A″` +0.57, bar +1.43), `skyline` **−0.05** (`A″` −0.06, bar −0.02). `kerb` re-spent part of the
give-back exactly as `Q44` predicted — glassed openings take sky reflection again — while
`street` moved the *other* way: the `Q45` pull mixes each pane's chromaticity toward its
building's measured `a*b*`, and against a mostly near-neutral stock that *lowers* pane chroma —
the variation arrives through `L*`/`b*` spread rather than saturation.

✅ **Graded, and enabled (2026-08-09).** The user answered the named review question — *do punched
windows read as windows, and do two adjacent towers still read as two buildings?* — in `A‴`'s
favour from the frames ("much more acceptable now") and called the default: `city_facade.tres`
now ships the seven fabric values with `survey_apply = 1.0` and the `W1`/`W2` knobs — the exact
configuration the `A‴` frames were shot from, proved by byte-comparing a fresh shoot of the
shipped file against `build/driver/q26_A3_422ee16/`. The ≥3-HK-driver round at `P3-9a` is the
confirmatory half, on the web build, against whatever is shipping then.

⚠️ **Superseded as the default on 2026-08-16, and only as the default.** The user moved the
working look back to candidate `C` to continue development on flat colour; `A‴` moved out of
`city_facade.tres` into `city_facade_elements.tres` unchanged, and this grading stands. See the
status at the head of `Q26`.

**See.** `ART_DESIGN.md` "The clean/futuristic variant" · `ART_DESIGN.md` "The audit viewpoints" ·
`Q27` · `Q30` · `Q31` · `Q34` · `Q37` · `Q40` · `Q41` · `Q43` · `Q44` · `Q45`

## `Q27` — `COLOR_0` is authored sRGB and must be linearised by the consumer

**Status.** ✅ Closed

**Claim.** The ETL writes `COLOR_0` as **sRGB bytes**. Every colour *uniform* in the façade shaders
carries `: source_color`, which Godot converts to linear; `COLOR` carried no such marking and arrived
unconverted, so the shaders mixed sRGB into linear. Godot 4 has no `vertex_color_is_srgb` render mode
— it survives only as a `BaseMaterial3D` flag — so nothing converted it and nothing complained. The
consumers convert; `ARCHITECTURE.md` now states the colour space, because **the contract being silent
on it is the defect that allowed this**.

**Why it read as "the lights are too bright".** sRGB interpreted as linear is *lighter* than
intended, and light the albedo did not ask for is light that does not vary *with* albedo. Measured on
a lit façade pixel, **57% of its luminance was albedo-independent** — so the city was simultaneously
too pale and unable to show which building was which. One cause, two symptoms that look like two
problems. Fixed, the additive share falls **57% → 6%** at street level and 61% → 19% at skyline, and
the 19% is fog doing aerial perspective.

**The light-levels half is answered "no", by ablation.** Each of `tonemap_exposure` 1.0→0.5,
`ambient_light_energy` 0.85→0.30, glow off, fog off, ACES→linear tonemap, `SPECULAR`→0, and all
shader effects off **moved albedo gain by at most 0.05** (0.38 shipped). Halving exposure drops the
frame 21 `L*` and buys 0.05 of gain. **That invariance is the fingerprint** — fog and glow are
additive and the tonemap is compressive, so all three *should* have moved it; that none did puts the
loss upstream of the light.

⚠️ **Why not fix it in the ETL.** Writing linear `COLOR_0` would be glTF-conformant and materially
worse: linear `uint8` spends its codes on highlights the eye cannot separate and starves the shadows,
which is the problem sRGB encoding exists to solve. It would also change the data contract and break
the graders, which match shipped vertex colours against `class_materials`.

⚠️ **The reusable lesson is the statistic, not the bug.** The headline "frame `L*` 86.8 → 83.3" was a
whole-frame mean, and a third of that frame is sky, fog and glass — pixels that cannot respond and
dilute the ones that do. `drive.sh` is deterministic, so two renders are pixel-aligned and can be
subtracted: a pixel that did not move is a pixel the change could not reach, and it identifies itself
with no mask or depth buffer. That is `tools/frame_stats.py`, and re-reading the original evidence
with it moved the gain 0.19 → 0.28 before anything was changed.

**See.** `ART_DESIGN.md` "Per-building façade colour" · `Q31` · `Q33`

## `Q28` — A per-object seed must be `flat`

**Status.** ✅ Closed

**Claim.** `buildings.facade_uv` packs `TEXCOORD_0.y` as `surface_class + phase`, a *per-object*
quantity. Both façade shaders read it into a plain `varying`, so the GPU interpolates it across the
face. `flat` on `phase` and `marker` fixes it. The geometry was never at fault.

**The mechanism.** Where a triangle's corners disagree, `phase` becomes a **ramp**,
`seed = floor(phase * 256 + 0.5)` quantises that ramp into integer steps, and `draw()`'s `sin` hash
maps each step to an unrelated brightness. At `value_jitter = 0.35` that is ±35% re-rolled every
1/256 of the ramp — stripes drawn *inside* a single flat triangle. Corners disagree because
`collapse` takes colour and UV from **one cluster representative**, which is right for colour
(averaging two buildings at a shared wall would invent a third) and wrong for a seed. Measured on
shipped LOD0: **14,012 of 521,693 triangles (2.7%)**, worst spread 0.4336 — 111 of 256 seed values
inside one triangle.

**Evidence.** Row-to-row contrast on the reported surface **6.80 → 0.07**, sd 12.70 → 2.95;
whole-frame −13.2% there, −12.1% and −15.2% at the two fixed viewpoints, at a frame mean that moves
0.2 `L*`. Noise removed, not exposure shifted.

⚠️ **Two confident diagnoses were measured wrong first, and the first cost an ETL feature** —
`LedgeShading`, ~440 lines, built, measured at no banding change anywhere, and reverted. What settled
it was a probe: project the shipped tiles onto the reported frame and read off what covers the banded
pixels. One flat 707 m² triangle, constant normal, the engine's own normal buffer agreeing at sd 0.00.
**Tint the class before naming it.**

**Unrelated finding that stands.** `B373231543201063A0` really is 8,793 source triangles over 128
horizontal levels, and `collapse` cannot remove them at any cell size — 1.5 m leaves 105 levels, 8 m
leaves 76 — because the facing key means a slab's up-face can only merge with another up-face. A live
triangle-budget question for `P2-6`, and not what anyone could see.

**See.** `Q32` · `Q33`

## `Q29` — The ground's normals are rebuilt in the fragment stage

**Status.** ✅ Closed

**Claim.** LandsD ships the terrain **faceted** — all three vertex normals agree on every one of the
sheet's 83,637 source triangles. `mesh.collapse` is what smooths it: the `height_field=True` path
drops the facing term from the cluster key, and `_cluster_mean` then averages the normals of whatever
shares a 4 m cell. Mean normal error **8.72°**, with 27.5% of vertices off by more than 10°. The
ground was the only smooth-shaded surface in a flat-shaded city. Rebuilt from the derivatives of
view-space position in both façade shaders, gated on `MARKER_GROUND`.

**Cost.** **Zero triangles, zero vertices, zero draw calls, no geometry change** — the diff is two
shaders. The ETL alternative, unwelding the ground for per-face normals, costs ~219k more vertices
and about **8 MB against a 32.3 MB PCK**.

⚠️ **Two implementation details are load-bearing.** The derivative is taken **unconditionally**, not
inside the `marker` branch: derivatives are undefined where a pixel quad straddles a non-uniform
branch, and a quad on a seam straddles two triangles whose marker differs. And the result is
**oriented against the interpolated normal** rather than by a hand-picked sign, using a comparison
rather than `sign()` — which returns zero on a perpendicular pair and would hand the mix a zero
vector.

⚠️ **The land-cover classifier would not have fixed this, and that is measured.** Putting the class in
`collapse`'s cluster key genuinely splits often — 47.8% of cells hold more than one class — but it
splits by *colour* where the error comes from *slope*, and on this terrain the two are uncorrelated:
normal error **8.72° → 8.15°, 6.5%**, for clusters **8,718 → 14,770 (+69%)**. A 19th of the fix, paid
for in geometry.

⚠️ **The stale-shot trap cost a day here.** A verdict was read against shots taken one palette commit
earlier. **A verdict pending on a screenshot has an expiry date that nothing in the repo records.**
`Q36` records the same trap on config rather than on shots.

**See.** `Q18` · `Q36` · `ART_DESIGN.md` "Ground"

## `Q30` — The shipped façade palette is not the one `ART_DESIGN.md` authorises

**Status.** 🔴 Open · **Owner.** `Q26`

**Claim.** The five `height_bands` sit at `C*` 1.92–13.84. At `facade_hue.strength: 2.0` the shipped
per-building colour is `C*` mean 15.37, p90 30.39, p99 60.27, max 104.55, with **26.4% of 2,177
buildings over `C*` 20** against 4.6% at faithful strength 1.0. The palette table describes a city
that does not exist, and one building in four is more saturated than anything the direction sanctions.

⚠️ **The knob cannot fix this, which is the argument against tuning it further rather than for.**
Amplifying chroma linearly widens the spread far faster than it moves the middle, so at 2.0 the
distribution is *both* too grey (median 12.25) and too candy (p99 60.3).

**Measured by `tools/facade_chroma.py`, and re-run it before quoting any of this.** Every figure
here moves when `strength` moves or the survey is re-run, and both have happened. ⚠️ **The two move
different ends**: `Q37`'s resurvey lifted the median 28.7% (9.52 → 12.25) and the p99 5.1%
(57.33 → 60.27), because the table it replaced held 222 filler rows at exactly `C*` 0. `strength`
widens the tail and barely moves the middle. A re-grade that read one as a proxy for the other would
tune the city the wrong way.

⚠️ **`strength: 2.0` puts 0.6% of surveyed buildings outside the sRGB gamut, worst `dE76` 67.5 —
and this does not restate the 2.2% / 61.5 recorded here before, which does not reproduce.** Six
definitions were tried against the superseded table on which that pair was computed — linear-channel
bounds, encoded bounds, four `dE` thresholds — over both the filtered and unfiltered populations,
and none returns it. The figure is therefore replaced rather than corrected, and the definition is
named this time so the next re-grade can reproduce it: **`colour.in_gamut`, which is true exactly
where `lab_to_srgb`'s clip changed no byte**, and CIE76 for the distance. An unnamed `dE` is a number
the next measurement cannot check.

**Options.** Drop toward 1.0–1.5; compress the tail rather than scale it; or re-author the palette
table around what ships. **Belongs with `Q26`'s verdict, not before it.** ⚠️ The re-grade did not
choose between them, and it slightly strengthens the second: the tail moved 5.1% while the middle
moved 28.7%, so the saturated buildings are not an artefact of the survey that was withdrawn.

**See.** `ART_DESIGN.md` "Palette" · `Q26` · `Q34` · `Q37`

## `Q31` — The city's value range has an empty middle

**Status.** 🟡 Open, but **re-diagnosed, with the cause measured** · **Owner.** `P3-9a`

**Claim.** Street frames come out bimodal. Causeway Bay in shade is **51.4% of pixels under `L*` 10
and 0.5% between 10 and 30**; under the HKCEC deck 28.9% and 2.0%. Half a street frame carrying no
information — and it is the frame the player occupies for the whole game.

⚠️ **The palette lever has been pulled and it was not the cause.** `Q33` re-placed the asphalt against
published albedo and it moved **+2.7 `L*`**, because `#3c3a37` was already claiming 8.2% reflectance
against aged asphalt's real 7–12%. Re-graded on the same two frames: shaded street under `L*` 10
**51.4% → 51.3%**, the 10–30 band 0.5% → 2.7%; Hennessy Road 13.2% → 13.0%.

### The statistic now has a mechanism

**It did not have one until now, which is why every figure above was unauditable.**
`tools/frame_stats.py` reported percentiles and never band shares, so nothing in the repo could
reproduce the numbers this question is *stated in*. It now reports both, against `SHADOW_L` and
`MIDTONE_L`, with the first tests the tool has had.

⚠️ **Percentiles cannot show an empty middle, and this is structural rather than a matter of
resolution.** The shipped `kerb` frame reports p50 7.9 and p90 58.8 — the entire 10–30 band falls
between two adjacent reported percentiles, and the emptier the middle gets the further apart the
percentiles straddling it move. ⚠️ Worse, at an exactly even split `np.percentile` *interpolates
across the gap*: a 50/50 frame at `L*` 2 and 70 returns p50 **36.0**, a confident mid-grey for a
frame that has no mid-greys. `kerb` escapes that only by being 51/49.

**The reproduction is exact in three cells of four.** `kerb` returns 51.3% / 2.7% and `street` 13.0%
under `L*` 10, matching the published post-`Q33` figures. ⚠️ `street`'s 10–30 band returns **25.4%
against a recorded 25.1%** on a **byte-identical** frame, so that one cell was always slightly wrong.

### The failing set, re-measured — and the second frame found

✅ **"The two failing frames are exactly the two shot in shade" holds.** The deck frame was not lost:
it is **`taxi` at t01.20**, named in `ART_DESIGN.md`'s Lighting section as `build/driver/art_taxi`
t01.20, and it reproduces **28.9%** to the decimal.

| viewpoint | under `L*` 10 | 10–30 | reading |
|---|---|---|---|
| `kerb` — Causeway Bay in shade | **51.3%** | **2.7%** | the pathology |
| `taxi` t01.20 — the car in shade | **28.9%** | **12.1%** | the pathology, milder |
| `street` | 13.0% | 25.4% | healthy — a full middle |
| `infra` | 0.0% | 39.6% | healthy — the *fullest* middle measured |
| `skyline` | 0.0% | 3.8% | healthy — its mass is *above* 30 |
| `taxi` t04.50 — the car in sun | 1.7% | 22.0% | healthy, and the same camera |

⚠️ **What does *not* hold is "under a deck".** `infra` is shot from directly beneath the Canal Road
flyover and has the **fullest** middle of every frame measured. Being under a structure does not
predict the fault; being *in shade* does, and the same `taxi` camera grades clean at t04.50 in sun.

✅ **`Q33` helped this frame six-fold and it was never recorded.** The 10–30 band is written as 2.0%
and now reads **12.1%**, because the post-`Q33` re-grade covered only `kerb` and `street`. The palette
lever was more effective than the record credits — on the frame nobody re-measured.

⚠️ **A low middle band is not by itself a defect** — `skyline` has 3.8% and is fine. The pathology is
a high shadow share **and** a low middle together. Read the two columns as a pair or the next person
optimises `skyline` upward for nothing.

### ✅ Every row of this table reproduces exactly

Audited after `Q26`'s tone-curve shoot found that a preview frame can be silently mis-aimed. Nothing
here was affected. Measured with `tools/frame_stats.py` on framing-verified frames — the three
preview viewpoints from the set proven byte-identical to a fresh `HEAD` shot, and `infra` re-shot at
`7d2f073` in three runs that agreed byte for byte:

| row | published | re-measured |
|---|---|---|
| `kerb` | 51.3% / 2.7% | ✅ 51.3% / 2.7% |
| `street` | 13.0% / 25.4% | ✅ 13.0% / 25.4% |
| `skyline` | 0.0% / 3.8% | ✅ 0.0% / 3.8% |
| `infra` | 0.0% / 39.6% | ✅ 0.0% / 39.6% |

The two `taxi` rows come from `city_drive.tscn`, where `--camera` is ignored outright, so the hazard
cannot reach them.

🔴 **A first pass at this audit reported three of the four as irreproducible, and it was wrong.** It
took the `build/driver/art_*` directories to be the frames the table was computed from, on the
strength of their names, and they are different shots — `art_infra` returns 0.1% / 0.1% against the
published 39.6%. The lesson is not that the figures were fragile but that **`build/driver/` is not
the provenance and must never be read as though it were.** Directory names there are reused between
shoots and nothing records which commit a frame is of.

✅ **What makes these figures durable is `ART_DESIGN.md`'s audit-viewpoint table, not any PNG.** The
cameras are fixed and the renders are deterministic, so any row can be regenerated on demand — which
is the same property `Q26` relies on for its comparison set. Re-shoot; do not go looking for a file.

✅ **`Q27` was audited the same way and is clean.** All 32 of its ablation pairs are internally
aligned — responding share is uniform at 55.9% (`skyline`) and ~40% (`street`) across all sixteen
variants, so no pair has a mis-framed member. ✅ **`Q30` is immune**: `tools/facade_chroma.py` reads
the survey and city config, never a render.

### The cause is the tone curve, not the fill

**`adjustment_contrast = 1.14` is the dominant term, and it had never been ablated.** `Q27`'s sweep
covered exposure, ambient energy, glow, fog, tonemap and specular; `Q33` was the palette. The
contrast adjustment was in neither list. Measured on `kerb`, one `.tres` line:

| `adjustment_contrast` | under `L*` 10 | 10–30 | `skyline` `L*` p90−p10 |
|---|---|---|---|
| 1.14 (shipped) | 51.3% | 2.7% | 44.1 |
| 1.11 | 50.4% | 3.5% | 42.9 |
| 1.07 | 49.6% | 4.3% | 41.5 |
| 1.00 | **0.9%** | **52.9%** | 39.0 |

✅ **It generalises to the second failing frame.** The same one-line change takes `taxi` t01.20 from
**28.9% → 0.8%** under `L*` 10, and its middle band 12.1% → 40.2%. Two frames, one cause.

**Godot's contrast adjustment pivots about mid-grey, so at 1.14 everything below it is pushed down**
and the 10–30 band is precisely the region evacuated into <10. ✅ **That explains why `Q33` looked
inert on the statistic it was graded against.** The palette and the contrast are **in series with the
contrast downstream**, so a +2.7 `L*` lift on a surface sitting at `L*` 5 is re-crushed and the mass
never crosses 10 — 51.4% → 51.3%. What it did move was the band above, which is why the same change
reads as 0.5% → 2.7% on `kerb` and 2.0% → 12.1% on `taxi`.

⚠️ **It does not explain `Q27`'s null, and the two should not be merged.** `Q27`'s ablations were
graded on **albedo gain**, which its own encoding fault accounts for; the contrast curve is a claim
about the **value distribution**. Different statistic, different cause — see the trap below.

### ⚠️ But closing the band does not deliver what the claim asks for

**The 51.3% → 0.9% is one flat surface crossing a threshold, not a frame gaining information.**
Graded on the *same pixels* — the renders are deterministic and pixel-aligned, so the mask is fixed
by the baseline:

| frame · variant | shadow-mass `L*` | shadow-mass sd | under `L*` 10 | `skyline` spread |
|---|---|---|---|---|
| `kerb` shipped | 4.91 | **0.79** | 51.3% | 44.1 |
| `kerb` `contrast` 1.00 | 10.99 | **0.85** | 0.9% | 39.0 |
| `kerb` `ambient_light_energy` 1.4 | 8.59 | **1.05** | 46.7% | 38.2 |
| `taxi` t01.20 shipped | 4.76 | **0.83** | 28.9% | — |
| `taxi` t01.20 `contrast` 1.00 | 10.77 | **1.39** | 0.8% | — |

Half the `kerb` frame is the shaded road at a near-constant value, and it stays near-constant: the
internal spread moves 0.79 → 0.85 against a frame-wide spread of 54. 🔴 **The band share can therefore
be satisfied by translation**, and "half a street frame carrying no information" is a claim about
information. The two are not the same test.

⚠️ **`taxi` separates a little more (0.83 → 1.39) and that is not a counter-example.** Its shadow mass
is several surfaces — soffit, walls, pavement, car — so a uniform lift spreads them by their differing
albedo. `kerb`'s is one road. Neither reaches a spread a viewer could read as form, and the mechanism
is the same in both: the lift is uniform, so it can only separate surfaces that already differ.

⚠️ **Contrast strictly dominates the fill on this trade**, which inverts the assumption above: raising
ambient 65% moves the mass only to 8.59 — *still under 10* — buys 4.6 points of band share, and costs
**more** massing flatness (38.2) than contrast 1.00 does (39.0). The fill is the weaker lever in both
directions at once.

✅ **This makes the sky-visibility term a structural conclusion rather than a preference.** Both levers
are monotone per-pixel functions, and the shaded road is one flat-shaded surface of uniform albedo and
normal under uniform ambient — a constant. No monotone function of a constant produces variation, at
any setting. `Q39` is the second consumer. `P3-9a` should carry the bake, and the acceptance test
should be **within-mass sd, not band share**.

⚠️ **Nothing was shipped.** `clean_daylight.tres` is restored byte-for-byte.

✅ **The wait this paragraph imposed is over, and it was never necessary.** It read: "the tone curve
is the thing three drivers are about to judge `Q26` through, and moving it now would change the thing
under test — the contrast change waits on that verdict." `Q26` has since re-shot all three candidates
at 1.14 *and* 1.00 and found the separation between them unchanged — responding share within 1.0
point everywhere, the `B`:`A` ratio holding at 2.10 and 3.05 exactly, and magnitudes shrinking by a
uniform 0.888 against a pivot null of 0.877. The curve scales every difference alike, so it is not
the thing the looks are being told apart by. **The contrast change no longer waits on `Q26`.**

⚠️ It still waits on the acceptance test below — band share is the wrong measure, and within-mass sd
needs the sky-visibility bake. Being unblocked from `Q26` is not the same as being ready to ship.

⚠️ **`Q27` is a trap for the next reader.** It ablated `ambient_light_energy` 0.85 → 0.30 and reports
it moved albedo gain "by at most 0.05", which reads as *ambient does nothing*. It says no such thing:
`Q27` measured **albedo gain**, this measures the **value distribution**, and ambient moves the second
while barely touching the first. Same knob, two statistics, opposite verdicts.

**Corroboration from a second axis.** `Q36` reached the same rig pass on *hue*: `asphalt_aged` is the
frame's grey card at authored `C*` 2.14 hue 84.6 (warm) and rendered `C*` 7.05 hue **275** (blue), so
the rig adds ~7 `C*` of blue to everything and the below-horizon frame is 70.7% cool.

**See.** `Q33` · `Q36` · `Q39` · `Q27` · `Q26`

## `Q32` — `INFRASTRUCTURE` is *not* the brightest large object in its frame

**Status.** 🟢 Closed as **wrong** · **Owner.** `P3-9a`

**The refuted claim.** That `INFRASTRUCTURE` renders as the brightest large object in its own frame
and that a deck soffit sits at nearly the value of its deck top.

**What a probe found.** Tinting `MARKER_STRUCTURE` refuted both in one render. In the viewpoint
chosen to *showcase* the class it is **2.71% of the frame**; its up/side faces render at `L*` **51.1**
against a non-sky frame mean of **48.1** — three points, not "the brightest"; and its soffits were
already at `L*` **35.9**, fifteen points below its own up-faces.

⚠️ **The pale beams filling that frame are `BUILDING`.** Naming the class from the silhouette was the
error.

⚠️ **The reusable part is the reasoning fault: "no AO, therefore a soffit renders like a deck top"
confuses ambient occlusion with `N·L`.** Under one directional light a down-face takes no direct sun
at all, so the 15 `L*` gap *is* the renderer working. A `structure_soffit_darkness` term was built,
measured (soffits `L*` 36.3 → 25.8, frame mean 0.05) and **reverted to a byte-identical render** — a
correct implementation of a wrong premise is still cruft.

✅ **What survives and is true.** The class takes none of the shader's surface treatment — everything
is gated on `is_facade` at `city_facade_clean.gdshader:437`. Recorded in `ART_DESIGN.md` as a known
gap rather than as a defect.

⚠️ **Fourth of a kind.** `LedgeShading`, `reface_ledges`, this, and `Q36`'s hillside split all failed
the same way. **Tint the class before naming it.**

**See.** `ART_DESIGN.md` "Infrastructure" · `Q28` · `Q36`

## `Q33` — Every authored colour is `material reflectance × exposure_anchor`

**Status.** ✅ Closed · **Owner.** `config.py`

**Claim.** Every authored colour equals a published diffuse `reflectance` times one per-city
`exposure_anchor`. `config.py:_check_exposure` refuses to load one that is not, within 8-bit
quantisation. Reflectance is cited evidence and portable to the second city; the anchor is the one
art-direction number. It is the same split `facade_hue.strength` already makes, and it is what hard
rule 3 wants: the physical half travels, the taste half does not.

**Why.** A palette judged only on internal consistency always indicts its most extreme member — here
the one colour that was already right. Divided by the anchor, the shipped palette was *claiming*
asphalt **8.2%** (real aged asphalt 7–12% ✅), kerb **58.9%** (concrete 20–30% 🔴), ground **39.6%**
(15–25% 🔴), infrastructure 32.4% (⚠️ marginal). Shipped, lightness only, every authored hue
preserved to within `Δab` 0.46: asphalt `#3c3a37` → **`#42403d`** (+2.7 `L*`), infrastructure
→ `#615f5a` (−7.7), ground → `#645a45` (**−13.9**), kerb → `#68655c` (**−19.4**). Kerb-to-road
reflectance lands at 2.5:1, which is what concrete against asphalt is; it was 6.6:1 — and that still
leaves 15.6 `L*` of separation, so the 0.15 m riser reads as an edge.

**Why the kerb had drifted 19 `L*`.** It became the brightest surface in the city **by not moving** —
`kerb_colour` lives in `RoadSurface` while the re-exposure commit edited `BuildingStyle`.
⚠️ **Enforced over the whole config, never per section**, precisely for that reason.

⚠️ **The five `height_bands` are the rule's soft spot.** The anchor is calibrated on them, so they
cannot also be checked by it, and they read 49–62% — at the top of what render and tile do. That soft
spot is what opened `Q34`.

**The method lesson.** A palette compared only to itself cannot tell you its outlier is its only
correct member. The fix is not more rigour, it is an **external referent**.

**See.** `ART_DESIGN.md` "The rule" · `Q31` (not fixed by this) · `Q34` · `Q36` · `Q38`

## `Q34` — Material is declared, not implied from height

**Status.** ✅ Closed · **Owner.** `config.py`

**Claim.** A top-level `materials:` table holds all nine colours the city ships as
`Material(name, colour, reflectance, source)`; `buildings:` and `roads:` reference them by name, plus
a `material_assignment` rule with a hue-conditioned draw over authored chroma rings and hue sectors.
`_check_exposure` is total because the *table* is, rather than because the loop is careful.
`schema_version` 3, and **no ETL→game contract bump** — no output artefact records a reflectance.

**Why height cannot carry a material claim.** On the 2,171-building survey, height explains **0.9% of
`L*`** once log pixel count is controlled and **0.7% of `a*`**. The best geometric key of any kind —
height plus footprint — reaches **1.4%**; slenderness `h/√A` is worse at 0.5%. Meanwhile **five
clusters on measured hue capture 72.4% of hue variance**. The structure is real, strong, and simply
not a function of shape. On a height bucket, "48.7% = grey painted render" reads as *"buildings under
12 m are grey painted render"* — a claim about one city's stock that the data refuses. It also breaks
hard rule 3: concrete is concrete in the second city, where a height→material mapping must be
re-derived from scratch.

**Evidence of grading.** Shipped in two halves: a pure refactor verified **byte-identical across all
138 output files** bar `city.json`'s timestamp, then the look change at whole-frame `L*` **−0.8**
street / **−0.1** skyline, with ~32% of pixels moving a mean 2.2–2.5 `L*` — because every bin's
weights are authored so its expected reflectance matches what the ramp gave that population. A
redistribution, not a level change.

⚠️ **The fallback is the height ramp, not the surveyed marginal.** `facade_hue` is optional *by
contract*, so a survey-less clone must build the **same** city — verified byte-for-byte. A marginal
draw would build a different one. Recorded so it is not re-proposed; it was the first proposal here.

⚠️ **It conditions lightness on hue only.** `with_hue` replaces `a*`/`b*` a line later, so for a
surveyed building the drawn material's own chroma never reaches the screen. What it buys is that a
cream-rendering building gets an albedo plausible for cream (60–75%) rather than for concrete
(20–30%).

⚠️ **Bin by authored chroma and hue-angle thresholds, never by k-means.** Cluster centres are
data-dependent, so they shift per region and per city and break hard rule 3.

⚠️ **It buys no spatial coherence** — only 0.5% of hue variance lies between the six sheets. That is
`Q35`, and it is the live half.

⚠️ **Not a route to fixing the numbers by measurement.** Texel ground sample distance is 13–18 cm, so
mosaic joints (3 cm), brick courses (7 cm) and render texture are all below resolution; only the
window/mullion grid at 2.4 m resolves. The one cut the imagery could support — glazed vs solid — is
the one that must not be used raw: curtain-wall glass has a **diffuse** reflectance of 8–15%, which
flat-shaded renders a tower near-black, because real glass towers are bright by *specular* sky
reflection this renderer does not do.

**Seeding note.** The draw is seeded by a `blake2b` stream deliberately uncorrelated with the jitter
seed. ⚠️ A prefix-salted `crc32` measures **+0.507** against it — CRC32 is affine over GF(2).

**See.** `ART_DESIGN.md` "Material is not a function of height" · `Q33` · `Q35` · `Q37` · `Q34′`

## `Q34′` — The ring weights are re-derived by a tool, against `Q37`'s survey

**Status.** ✅ Closed by `tools/ring_weights.py` · **Owner.** `hong_kong.yaml`

**Claim.** Each bin's weights are the smallest move that makes its expected reflectance the mean the
height ramp hands that bin's own buildings. Near-neutral `panel_grey` **0.50 → 0.56**, `render_cool`
0.30 → 0.28, `tile_neutral` 0.20 → 0.16; warm `render_pale` 0.45 → 0.46, `tile_neutral` 0.35 → 0.36,
`render_warm` 0.20 → 0.18; cool `panel_grey` **0.85 → 0.89**, `render_cool` 0.15 → 0.11. Targets
57.58 / 57.79 / 55.73%, met to 0.001 / 0.017 / 0.004. Re-run on its own output the tool proposes no
further move.

**The share moved eleven points and the target moved 0.35.** That is the whole finding, and it is
`Q34`'s own near-independence result arriving from the other direction: the bins partition on hue,
every target is a mean over *height*, so `Q37` taking a fifth of the near-neutral ring's stock out of
it barely moved the height distribution of what stayed or of what arrived. **A large change in a
bin's share does not imply a large change in its weights** — no weight here moved by more than 0.06.

**Why a tool rather than a spreadsheet.** The config has said *re-derive these if the ramp moves*
since `Q34` and had no mechanism behind it, which is the same shape of debt `Q37` closed — a table
nobody could re-derive, wrong for two years. It reads the survey through `facade_hue`'s own
vegetation filter and bins through the config's own rings, so the population it measures cannot drift
from the population the pipeline draws for.

⚠️ **The free degree of freedom is fixed by a stated rule, because the target does not fix it.**
Three materials against two constraints leave a line of solutions and every point on it hits the
target exactly; picking a different one repaints different buildings for no reason anyone could name
afterwards. The rule is the minimum-norm move from the shipped weights, which keeps whichever
material was made dominant dominant.

**Evidence of grading.** Skyline whole-frame `L*` **−0.0**, street **+0.4**, at responding shares of
4.3% and 7.8% moving a mean 2.65 and 4.82 `L*`. ⚠️ **The street's +0.4 is a draw, not a level** — a
canyon shows three façades where the skyline averages hundreds, and the skyline is the population an
expectation is an expectation over. Expected city-wide reflectance moved **57.54 → 57.49**.

⚠️ **`test_config.py`'s bound stays loose, and tightening it is the wrong instinct.** It compares each
bin against the ramp's *unweighted* band mean because the suite must run without the 4.9 GB survey,
so it catches a bin re-weighted to one end of the palette and nothing finer. The real check needs the
survey and is the tool.

**See.** `Q34` · `Q37` · `Q35` · `CONTRIBUTING.md` "Checks"

## `Q35` — A per-building material draw gives a salt-and-pepper skyline

**Status.** 🔴 Open · **Owner.** `buildings.py`, `hong_kong.yaml`

**Claim.** Neighbours draw independently from the same distribution, so two adjacent 1970s blocks can
land on materials **13 reflectance points apart**, where real blocks share cladding.

⚠️ **Hue does not supply the coherence, and the guess that it would was published before it was
measured** — only **0.5%** of hue variance lies between the survey's six sheets. Block scale is
*untested* rather than ruled out: the survey carries `sheet` but no coordinates, so the only spatial
resolution testable is ~1 km, far coarser than a city block.

**The day-one mitigation is real but narrow.** Every bin's weights are authored so its expected
reflectance matches what the height ramp gave that population, which bounds how far apart two
neighbours land *on average* without constraining any individual pair. It cannot make a block read as
a block.

⚠️ **Grade it from the street, not the skyline.** A canyon shows two or three façades at once where
the skyline averages hundreds — this is exactly where the defect is visible, and the two viewpoints
disagreed sharply once before (`Q27`).

**Candidates, none scouted.** A **spatial hash** on the building's own position, so the draw is
seeded by which ~50 m cell it sits in rather than by its id — cheap, no new data, and a knob rather
than a rewrite. A **block join** from an external footprint/lot dataset — correctness for a new source
and a new licence review. Or **accepting it**, on the grounds that Hong Kong's stock genuinely is more
heterogeneous per block than most cities and the arcade camera moves fast.

**See.** `Q34` · `Q27`

## `Q36` — Wan Chai's ground is paving, not soil

**Status.** ✅ Closed · **Owner.** `hong_kong.yaml`

**Claim.** `fill_dry` → `concrete_paving`, `#645a45` → `#5f5a51`, **reflectance unchanged at 20.0%**,
so lightness never moved and the change is single-variable. 20.0% orders correctly against the
concrete already in the table (`concrete_kerb` 25.0, `concrete_sooty` 22.0) — a pavement is the
dirtiest concrete in the city.

**Why.** `Q34`'s rule is that a material is a claim about a **surface**, and "dry soil and urban fill"
was a claim about what is *under* the surface of a fully built-up reclamation whose visible surface is
pavement, plaza, apron and promenade. The file already disagreed with itself — the comment said "fill
and hardstanding" while the material said soil.

**Evidence.** Ground patch `C*` **6.71 → 3.53** at an unmoved `L*` 49; warm share of the
below-horizon frame **29.3% → 2.0%**. ✅ `street` and `kerb` verified byte-for-byte unmoved.

⚠️ **This supersedes `Q18`'s doubled chroma, and it is the entry to read before raising it again.**
`Q18` measured a low-chroma ground reading as "white plaster" at rendered `L*` 67.2; `Q33` then took
18 `L*` out of the render for an unrelated reason and **nobody re-graded the pair**. At `L*` 49.2 the
same low chroma reads as a concrete apron. **The reusable lesson: two individually-correct changes,
never graded together.** Its cousin is `Q29`'s stale-shot trap; the guard is the same one
`ART_DESIGN.md` states for screenshots — a verdict has an expiry date nothing in the repo records.
Extend it to config.

⚠️ **There is a null and it is not at the greyest hex.** Rendered chroma is roughly \|warm albedo −
blue illuminant\|, so authored `C*` 5.93 renders at **3.53** while authored `C*` 4.47 renders at
**5.04**, pulled cool. Authoring a little warmth is what cancels the sky. **Do not "simplify" toward
neutral grey.**

**Refused, recorded so they are not re-proposed.** ⚠️ **Sourcing terrain hue from the aerial JPEG** —
not `Q18`'s classifier but the `facade_hue` pattern applied to `TERRAIN(TB)` — fails on three reasons
`Q18` never gave: an aerial's variation is baked shadow, and baked illumination in the albedo channel
is wrong under both rigs; measured hue lands near `C*` 6, under the knee; and the amplification it
would need is `Q30`, open and red. ⚠️ **An x,y hue field** — below the knee it is invisible, above it
the ground goes patchy, and the palette's real variation is *lightness*: every structural material
sits in an 83–96° hue band spanning 16 `L*`. What the ground already varies by is `Q29`'s faceting.
⚠️ **A hillside split on an elevation threshold** — specified, probed and refused, and the probe
refuted the causal story behind it. Over 604,465 terrain triangles, area-weighted, only **9.77%** of
terrain sits above 10 m, and height and slope pick different sets (3.98% both, against 5.79%
high-but-flat and 2.45% steep-but-low — sea walls and embankments, which are concrete). Then the tint
settled it: high terrain renders **0.000% of all six fixed viewpoints**, and where a driver *can* see
it — the one road that climbs it, 2 of 615 graph nodes reaching `y≥20` — the visible high ground is
**97.5% the flat kind**. The high ground the player can reach is precisely the ground that *was*
built on. Slope-only fails too: a 0.21% interleaved speckle fringe, and `collapse` takes the
*representative* vertex's colour rather than averaging, so speckle survives decimation as speckle.
**If vegetation is wanted, the source is vector land-use polygons.**

🟡 **What stays open is the audit's actual finding**, untouched by any of this: *an unbroken 200 m
expanse of one correct colour with nothing standing on it*. That is emptiness, it is `B3`'s, and no
colour operation substitutes for objects.

**See.** `Q18` · `Q29` · `Q31` · `Q33` · `Q34`

## `Q37` — 10.0% of the façade survey is atlas filler, not a photograph

**Status.** ✅ Closed by `tools/facade_survey.py` · **Owner.** `buildings.py`, survey

**Claim.** 222 of 2,214 rows in `facade_lab.json` are achromatic — `a* = b* = 0` — across **23
distinct greys**, RGB(128,128,128) the most common at 85 rows and RGB(231,231,231) next at 46. Every
one of them is independently observable as fill in the raw atlases. `lab` is `srgb_to_lab(lit_rgb)`
to within 0.005 for all 2,214 rows, so `lit_rgb` carries the artefact and `lab` only inherits it.
**The imagery also covers only a median 14.3% of each building's walls.**

**Why it matters.** It is the **same error class the survey already caught once and fixed** — *"a
texel at 255 is `a* = b* = 0`"* — at the other end of the range. 220 of the 222 clear
`vegetation_max: 0.5`, so **10.1% of the 2,171 buildings that reach the city** render dead-neutral
because they were *not measured*, and under `Q34` they also fall into the neutral-grey material bin,
so a material is assigned from absent data.

⚠️ **The estimator concentrates filler instead of diluting it.** Filler is bright — `L*` 53.6 at
grey 128, 78.4 at 194, 91.6 at 231 — and the estimator takes the median of texels above the **65th
percentile of `L*`**, so filler preferentially wins the cut. Above roughly 35% filler by area the
entire selected set is filler and the median lands exactly on it. **166 of the 222 carry a chromatic
`naive_rgb`**: those buildings *were* photographed, and the selection discarded the photograph. A
mean would have diluted the filler; a bright-tail order statistic cannot.

⚠️ **222 is a floor, and the pixels put the real reach near five times it.** Filler below that ~35%
share pulls a row toward neutral without ever reaching `a* = b* = 0`, and the JSON cannot see it:
excluding the 222, chroma does fall with atlas size — `corr(log pixels, C*)` **−0.20**, largest pixel
quartile median `C*` **2.91** against 5.8–6.6 for the other three — but the signal is confounded with
height and is not monotone, appearing only at 40–80 m (6.78 → 2.74) and *reversing* below 20 m
(6.10 → 7.18). Measured against the imagery instead, on `11-SW-9D`: rejecting filler moves **20 of 59
buildings** past `Δab` 0.46 and **4** past 2.0, where only **3** were achromatic. 30 of the 59 carry
filler at all. **Any fix that keys on the achromatic rows treats one building in seven of those it
should.**

⚠️ **The fix is structural, not another entry in a list.** The guard has been wrong once already —
the first padding guard caught only pure black, and `#3c3c3c` **is** RGB(60,60,60). 23 distinct
greys is the measure of why enumeration keeps failing. **Reject exact `R == G == B` texels** — a
photographic texel essentially never is — or detect each atlas's filler as its modal
exactly-repeated colour.

⚠️ **The replacement survey is `tools/facade_survey.py`, and it cannot re-base the old table.** The
lost script's *sampling* is not recoverable from its outputs: its `pixels` column stands in a ratio of
**0.17 to 241** against covered wall texels on one sheet, and is no better explained by wall area
(4.5 to 2,877 per m²), so it counted neither. Nothing left in the file pins it. On `11-SW-9D` the new
tool matches `height_m` **exactly** on 59 of 59, agrees with the `vegetation` column to a median
**0.0070**, and — run *without* its filler guard — lands on the shipped achromatic value for the two
rows that are more than 30% filler, which is what identifies it as the same measurement. Against the
shipped `a*`/`b*` it still sits at a median `Δab` of **1.20**, and that residue is sampling, not the
fix: the guard alone accounts for a median of **0.000**.

| Gate | Threshold | Shipped result |
|---|---|---|
| Rows at `C* = 0` | zero | **2** of 2,213, both genuine — see below |
| Shipped achromatic rows | chromatic, or dropped to the height band | ✅ 221 recovered, 1 dropped |
| `height_m`, `vegetation` | reproduced | ✅ exact; median 0.0084 |
| Median `Δab` against the shipped table | **≤ 0.46** (`Q33`'s tolerance) | ❌ **1.04** |

⚠️ **So this replaced the old table rather than repairing it**, and that last row is the price, not a
defect left standing — no reconstruction can meet it, because what it measures is the lost sampling
scheme. 76.6% of rows moved past 0.46 and 15.6% past 5.0. What identifies the new table as the same
measurement is different evidence: run *without* its filler guard it lands on the shipped achromatic
value for the rows above 30% filler, reproducing the bug on demand, and the guard alone accounts for
a median `Δab` of **0.000**. `Q26`'s pending A/B, `Q30` and `Q34` are re-graded against a survey that
can be re-derived instead of one that cannot. `Q34` re-derived as `Q34′` and `Q30` is re-measured;
`Q26`'s A/B is shot and graded against this survey, so what it still owes is the verdict itself.

⚠️ **Two rows still read `C* = 0` and both are photographs.** `naive_rgb` of `[82,82,81]` and
`[87,81,77]` over 2.7 and 3.8 million texels — the per-channel medians simply rounded to a tie.
**Achromatic is not the defect's signature; repetition is.** 485 shipped rows shared an `(a*, b*)`
with another row and `lit_rgb` `[128,128,128]` appeared 85 times; here it is 113 rows and a top
repeat of 5. Padding produces identical rows, photography does not, and a future check should read
that rather than the neutral count.

⚠️ **`Q34`'s ring weights are authored against this population, and `Q34′` re-derived them against
it.** The near-neutral ring (`C* <= 5`) falls from **51.6% to 40.5%** of surveyed stock and the
population median `C*` rises from 4.78 to 6.12, so `panel_grey`'s expected share drops **33.7% →
28.6%** — **5.1 points of the neutral bin was filler**. The config's own ⚠️ — *re-derive these if the
ramp moves* — covers the survey moving as well, which is the reading `Q34′` had to make first.

⚠️ **Averaging in sRGB is a second, separate question** worth settling in the same pass: ~4.9 `L*`
away from a linear-light mean, and the same family as the bug `Q27` closed. **Change one at a time.**

**See.** `Q34` · `Q34′` · `Q27` · `Q30` · `Q26`

## `Q38` — `exposure_anchor` is baked into `COLOR_0` at build time

**Status.** 🟡 Open, and **deliberately not fixed now** · **Owner.** night mode

**Claim.** `config.py` applies the anchor at load, so the product ships it baked into the vertex
stream — and changing the time of day is a full tile rebuild. It is also the one place the project
puts an illumination term in the albedo channel it otherwise guards strictly (`Q27`, `Q36`), though a
far milder violation: one invertible, spatially-uniform scalar.

**Why it is not fixed.** The fix is cheap and known — the two façade shaders already linearise
`COLOR_0` and could take the anchor as a uniform, and the road's `BaseMaterial3D` has `albedo_color`,
which multiplies vertex colour. What it costs is `_check_exposure` and
`test_no_colour_escapes_the_materials_table`, both built around *authored colour = reflectance ×
anchor* and both shipped to close a real defect.

**Recorded so the constraint is found before night mode rather than during it.**

**See.** `Q33` · `ART_DESIGN.md` "Lighting"

## `Q39` — `wall_sky_tint` is uniform across the city

**Status.** 🟡 Open · **Owner.** `Q31`

**Claim.** `city_facade_clean.gdshader` mixes toward `sky_reflection` by `fresnel * wall_sky_tint`
with no occlusion term, so a wall at the bottom of a canyon takes the same grazing sky bounce as a
rooftop parapet.

**Why it matters beyond its size.** It overstates sky bounce in exactly the frames `Q31` reports as
broken — the two shot in shade — and it shares its input with `Q31`'s candidate fix.

**Cost.** Nothing to fix **once a sky-visibility term exists** (`fresnel * wall_sky_tint * sky_vis`),
and nothing before that. It is a second consumer for that bake rather than a task of its own.

⚠️ **Do not "fix" it by lowering `wall_sky_tint` globally.** `ART_DESIGN.md` records that lowering the
ambient fill corrects the road and flattens the massing at once; this is the same trade on the same
axis.

**See.** `Q31` · `ART_DESIGN.md` "Lighting"

## `Q40` — Can façade grammar be surveyed instead of hashed?

**Status.** ✅ **Closed** — the statistic's grammar branch 🔥 killed, the dip gate 🔥 killed at
region calibration, and what survived — reader-decided glazing, surveyed tint conditional on it —
**ships**: packed with `Q41`'s grammar into `TEXCOORD_1`, `schema_version` 5 → 6 both sides in one
commit, **measured +0.24 MB of PCK** against the "~2 MB" estimated below. The shader overrides land
dark behind `survey_apply = 0.0` (user's call, 2026-08-09), so the shipped frame is unchanged until
`Q26` grades the surveyed city as its own candidate · **Owner.** `P3-9a`

**The question.** `city_facade_clean.gdshader` decides whether a building is glazed, which of three
grammars it draws, and which of three glass tints it uses — all from `draw(seed, n)`, a hash of the
building's UV phase. `float glazed = step(solid_share, draw(seed, 1.0))` at line 449 is a coin flip.
Can any of it come from the source data instead?

**Why it is worth asking.** `Q26`'s central objection to candidate `A` is that it "keeps the accurate
*massing* and abandons the accurate *surface*". Surveyed grammar dissolves that objection: `A` stops
being invented surface and becomes measured surface, which is a materially different thing to put in
front of three drivers. It should also help `Q35`, since real neighbouring blocks do share cladding
where a hash does not.

### There is no published attribute, and there was never going to be

Both building sources are geometry only. The **non-textured** models carry `COLOR_0` in one primitive
with **no images and no UVs at all**; **3D-BIT00 Level 1** is footprints extruded between base and top
level, explicitly "with no photorealistic texture applied". No `use`, `structure`, `cladding` or
`year` field exists in either. ✅ **The evidence is the individualised set's photography**, which
`tools/facade_survey.py` already walks — and then collapses to one order statistic, discarding the
distribution the answer lives in.

### Probe 1 — glazed-vs-blank and tint, from the 1-D distribution

56 of 59 buildings on `11-SW-9D`. Otsu's split of each building's wall-texel `L*` population, then the
histogram dip between the two modes.

| | |
|---|---|
| photographic texels per linear metre | median **13.6**, p25 5.5, min 2.3 |
| buildings at ≥ 10 tex/m (≈15 texels across a 1.5 m window) | **61%** |
| clearly bimodal (dip < 0.25) | **50%** |
| clearly unimodal (dip > 0.60) | 23% |

⚠️ **Otsu separability is not evidence and was nearly recorded as if it were.** `eta` ranges 0.46–0.95
with a median of 0.72 and never goes low, because Otsu splits a unimodal blob just as happily. The
dip depth is the statistic; `eta` is decoration.

⚠️ **Resolution is a confound and has to be gated.** `corr(log tex/m, dip) = −0.463`; the
well-photographed half has a median dip of 0.18 against 0.42 for the rest. At low resolution **"no
windows" and "badly photographed" are the same reading**. Controlled to the 34 buildings at
≥ 10 tex/m the residual correlation falls to −0.28 and 23/7/4 split bimodal/middling/unimodal, so
real architectural variation does survive. The gate is the answer, and the pattern already exists:
`estimate()` returns `None` below `MIN_TEXELS`, and `facade_hue` sends an unmeasured building to its
height band.

✅ **Tint is the better-founded half.** The dark mode is bluer than the light in **77%** of buildings,
mean `b*` shift **−4.87**, dark-mode `b*` spanning **−11.9 to +14.2**. The three authored glass tints
convert to `b*` of **−9.20, −1.62 and −14.34 — all cool** — while the shader's own header says Hong
Kong curtain walls run "from near-black **bronze** through blue-green to pale blue". **17 of 56
buildings measure a warm dark mode (`b*` > +3) that the authored palette cannot express at any mix.**

⚠️ **The dark mode is "the dark population", not "the glass".** On a curtain wall it is the glazing;
on a punched-window building it is a shadowed reveal. Tint is only a glass measurement **conditional
on the building being glazed**, so type has to be decided first.

### Probe 2 — the atlas is axis-aligned but not upright

14 buildings. World-up pushed through each wall triangle's position↔UV Jacobian.

- Wall triangles within 10° of a UV axis: median **100%**, min 85%.
- Within-building agreement on *which* axis is up: median **0.14**, min 0.00.
- Dominant angles cluster on 0°/90°/180°; the 42.5°/45° entries are the artefact of averaging a
  bimodal 0°/90° distribution in doubled-angle space.

So the ambiguity is **90°-discrete per chart, not continuous** — correctable by transpose, with no
resample. Retaining the mask is nearly free: `coverage()` already builds it and discards it one line
later, and holding it costs median **0.34 MB** packed (max 6.4 MB) against a tool whose largest
building already gathers 90.1 million texels.

### Probe 3 — and none of that matters, because the atlas is shredded

20 buildings, **5,831 wall charts**: median **30 per building**, max **1,837**, median chart area
**3.8 m²** — about one window bay.

| span | ≥1 | ≥2 | ≥3 | ≥5 |
|---|---|---|---|---|
| bays across (9 m) | 56.7% | 35.0% | **20.4%** | 4.3% |
| floors up (2.8 m) | 82.9% | 73.0% | 67.4% | 36.6% |

🔴 **Only 15.2% of wall area — 47 charts of 5,831 — spans three bays *and* three floors.** Median
building: **0% analysable**. ⚠️ **The asymmetry is the finding:** photogrammetry charts tall narrow
strips, so the axis the atlas preserves is the *vertical* one, and fin-versus-curtain-versus-punched
is a claim about *horizontal* structure. Per-chart analysis is dead, and Probe 2's transpose plan
with it — a 90° transpose is cheap on 30 charts and meaningless on 1,837 of 3.8 m².

### ✅ The world-space unwrap works

Re-project texels through the same Jacobian into a grid whose axes are **metres across the face** and
**metres up**, at 8 texels/m. Every island lands in one picture, the 90° ambiguity cannot arise
because the axes are world axes, and a period in the output is a period in metres. It is also
*smaller* than retaining the atlas mask — a 100 × 60 m face is 0.38 Mpx against the atlas's 2.7 Mpx
median.

Verified by eye on a 51 × 110 m tower whose 1,837 islands stitch into a legible elevation: continuous
glazed floor bands, regular mullions, heavier structural bands every ~8 floors, and a dark plant
floor two-thirds up. A 26 × 42 m block beside it unwraps to blank render with punched openings at
the base. **The classifier's features are visible in the pictures before any code is written.**

🔴 **That last sentence was the overclaim, and it is retained because it is the fault.** Features being
*visible to a reader* was taken as evidence they were *measurable by a statistic*. They are not: the
reader was using recession, reflection and context, none of which survive into an `L*` profile. The
sentence is true and it licensed nothing.

### The classifier's two artefacts, and the refusal that fixed them

34 faces over 10 buildings. Two artefacts, both found by reading the numbers rather than the images:

1. ⚠️ **A false `fin` from a missing measurement.** Seven faces reported `floor 0.00 m, s = 0.00`,
   which is the vertical profile refusing to compute — *no usable measurement*, not *no banding*. The
   classifier read `floor_s < WEAK` and called it a fin. Absence of evidence laundered into evidence
   of absence, which is `Q31`'s confound wearing a different hat.
2. ⚠️ **Bay periods pinned at the band floor.** `1.38 m` recurred constantly and
   `int(1.4 × 8) / 8 = 1.375` — the autocorrelation peak landing on the *minimum lag allowed*, so it
   found no bay and reported noise.

**Both shared one root: four outcomes and no way to say "I don't know",** so every failure to measure
became a confident architectural claim. The fix is a three-valued measurement — `period` / `flat`
(measured, no repeat) / `unknown` (no finding) — plus a peak that must be a genuine local maximum
rather than a shoulder of the autocorrelation's decay from lag 0.

⚠️ **Chasing the first artefact turned up a third bug.** The moving-average detrend needed a window
wider than the longest period it guarded against (5.2 m → 83 rows) and `mode="same"` corrupts half of
it at each end, so it **consumed** the signal: a 79-row elevation was left 41 samples where 51 were
needed, and every elevation under ~13 m was refused outright. A degree-2 polynomial fit removes the
same storey-wise brightening and costs no samples. **The detrend was the wrong instrument for its own
stated job.**

Refusals rose 2 → 5, no spurious `1.38 m` survived, and the class tally barely moved — while
membership churned almost completely. **And none of it mattered.**

### 🔥 The sheet killed the grammar branch

12 of the 34 faces graded against their own photographs: **1 right, 8 wrong, 3 unsure.** Five failure
modes, of which the first three admit no threshold at all:

1. 🔴 **`L*` modulation measures materials, not recession.** `DEEP = 6.0` was meant to separate
   punched holes from a hairline grid. `B352631575201063A0`'s dark glass against pale spandrels reads
   `L*` **17.4** and classifies `punched`; a genuinely punched render-and-window block reads less and
   classifies `curtain`. Punched-ness is a **depth** property, and depth is exactly what a texture
   cannot see. The taxonomy's central axis is not measurable from colour at any threshold.
2. 🔴 **Reflections are most of the signal on glass.** That tower's four elevations carry reflected
   streets, cars, trees and sky. A mirror-glass tower's texture is substantially **not the tower** —
   which is why its four faces disagree with each other.
3. 🔴 **It is not self-consistent.** One decorative lattice screen — an unmistakable 2-D grid —
   reads `fin` from W and `curtain` from S. A classifier that disagrees with itself about a single
   physical wall cannot be repaired by moving thresholds.
4. ⚠️ **Periods appear in blank walls.** `B355691583201063A0` is flat render and returned `punched`
   and `fin` on two faces. `WEAK = 0.16` is cleared by accident at some lag by the autocorrelation of
   a smoothly-shaded surface.
5. ⚠️ **The unwrap admits things that are not façade** — trees, a hillside, an entire neighbouring
   curved-roof building. Anything in the document whose normal faces that compass direction lands in
   the elevation.

⚠️ **The single correct call is weaker than it looks.** That wall carries panel joints ~4 m apart,
inside `BAY_BAND`, and both axes were still reported flat. Right answer, and not obviously for the
right reason — which in a validation exercise is barely evidence.

⚠️ **The grading was by the classifier's own author, not a third party.** Modes 1, 3 and 5 are
checkable from the sheet by anyone, which is why it is retained rather than the verdict alone.

**Fin-versus-curtain-versus-punched is not derivable from this data.** Not deferred — modes 1–3 are
structural. The shader keeps `draw(seed, …)` for grammar, and `Q26`'s objection to candidate `A`
stands undiminished on that point. ⚠️ **`Q41` narrows this claim to *not derivable by a per-pixel
statistic*.** The data demonstrably carries the signal — what is structural is the measurement
class, not the source. Modes 1–3 remain a complete account of why no threshold on an `L*` profile
can work.

✅ **Real periodicity does exist in the data.** `B353771561001063A0` returns a **3.38 m floor pitch
independently on three faces** — that building's storey height, measured from photography. *Storey
height* may therefore be surveyable even though *grammar* is not; it is a different claim, needs its
own record, and nothing here establishes it. **That record now exists: `Q42`**, where a second
instrument lands on the same number.

### What survives, and the check it is still owed

Glazed-vs-blank and the 2-D tint rest on a **bimodality dip**, not on periodicity, so modes 1–4 do not
reach them. 🔴 **Mode 5 does.** The wall selection that let trees into an elevation is the same
per-mesh, per-normal test `facade_survey.py` uses, so foreign geometry may also have reached Probe 1's
histograms — and non-building content would bias a dip toward *bimodal*, in the direction that flatters
the result. It was visible in a picture and would be invisible in a histogram. **That check is owed
before the glazing gate is trusted.**

✅ **The check ran, committed as `tools/facade_glazing.py`, and contamination is real and material.**
The tool computes one dip statistic from both selections per building — Probe 1's `wall_texels()`
against the pooled depth-filtered unwrap elevations. ⚠️ The two populations differ by more than
occlusion, deliberately: the unwrap re-grids at 8 texels/m, so its histogram is area-weighted where
the atlas one is texel-count-weighted, and a well-photographed balcony no longer outvotes the wall
behind it. On `11-SW-9D`, 52 of 59 buildings measured, 51 gated at ≥ 10 tex/m (as
√(photographic texels / wall m²)): **the verdict moves on 19 of 51** — 11 toward unimodal, 8 toward
bimodal — tallies 11/17/23 bimodal/middling/unimodal becoming **9/16/26**, median dip 0.490 → 0.611.
The flattering direction holds on net, and by name: `B358341572401063A0`, the blank render block
whose W face `Q41`'s reader refused, reads **bimodal (dip 0.241)** through the wall selection and
**unimodal (0.972)** decontaminated — the selection invented glazing on a blank wall. The reverse
also occurs: `B358891570501063A0` goes 1.000 → **0.006** and `B357961566001063A0` 0.896 → **0.054**,
occluding geometry having *hidden* real bimodality on the buildings it covered.

✅ **The second sheet agrees the movement is material, and adds that its direction is not fixed.**
`11-SW-14B`, 715 measured and 699 gated: verdicts move on **195 of 699** — 102 toward unimodal
against 93 toward bimodal — tallies 51/152/496 becoming **66/123/510**, median dip 0.857 → 0.891.
Where `11-SW-9D`'s movement ran net toward unimodal, `14B` sharpens both ends and drains the
middling bucket: decontamination is not a uniform correction some scale factor on the old numbers
could reproduce, it changes individual buildings' answers in both directions. The sheets also
disagree about the city itself — 51% against 73% clearly unimodal — so the threshold re-derivation
needs more than one sheet, as this record already warns for other numbers. (Both figures are the
decontaminated column: 26/51 against 510/699.)

⚠️ **Probe 1's absolute numbers do not carry, for a second reason: its implementation was never
committed** — this record's own `Q37` ghost. The new tool's atlas column, same selection but its own
histogram parameters, reads 11/51 clearly bimodal against Probe 1's 50%, and its density metric runs
about twice Probe 1's 13.6 median. So the Probe 1 table above describes an uncommitted statistic
over a contaminated selection, and the glazing gate's thresholds are **owed a re-derivation from the
decontaminated selection** — on more than one sheet — when the survey extension is built. The dip
boundaries (0.25 / 0.60) and the ≥ 10 tex/m gate are pinned in the tool so that re-derivation moves
them deliberately rather than by reimplementation drift.

### 🔥 The re-derivation ran, and the answer is that no threshold exists

The survey extension was built (`225a564`: `facade_glazing.py` writes per-building dip, dark/light
`(L*, b*)` and density tables), run over all six sheets — **2,171 buildings, 2,143 gated** — and
calibrated against an instrument Probe 1 never had: `Q41`'s reader, whose region survey carries an
independent per-face `glazed` verdict ("does glazing dominate the façade area") on 1,629 gated
buildings.

**The dip cannot predict glazing at any threshold.** Sweeping the cut over the full range, the best
Youden J is **0.100** (0 = chance); "bimodal → glazed" precision is 0.19–0.21 against a 0.14 base
rate at every candidate boundary; and the conditional medians **flip sign across sheets** — on
`11-SW-9D` reader-glazed buildings have *higher* dips than the rest (0.792 vs 0.593), on `11-SW-15A`
*lower* (0.536 vs 0.833). A threshold that must point opposite directions on two sheets of the same
city is not a threshold.

**The charitable re-scoping fails harder.** Probe 1's framing was glazed-vs-*blank* — two `L*`
populations against one — so the dip was also tested against the reader's majority grammar,
`blank` vs any windowed class. The direction is *inverted*: blank walls read **more** bimodal
(median dip 0.484, n=10) than windowed ones (0.850, n=1,425), negative J at every cut. No grammar
class separates either (punched 0.870, curtain 0.790, mixed 0.722, fin 1.000). The mechanism is
mode 1 reaching the histogram: **an `L*` split cannot tell glass from shadow.** A punched tenement
is exactly as bimodal as a curtain wall — dark window-holes against light wall — and a blank render
wall splits on weathering and baked occluders. "Two modes" never meant "glazed"; it meant "two
tones", which every façade in the city has.

**So the glazing decision goes to the reader, and the dip is retired from gating.** `Q41`'s
`glazed` field covers 80% of buildings with at least one read face; a refusal falls back to the
hash — the identical consumption contract as grammar, decided in the same `TEXCOORD_1` pass. The
dip column stays in the table as the contamination check's own measurement, consumed by nothing.

**✅ Tint survives, re-scoped: the reader decides eligibility, the survey provides the value.** The
dark-mode `(L*, b*)` from the decontaminated selection orders exactly as it should against the
reader's independently-read tint enum — blue **−4.83** < green **−2.62** < neutral **−1.92**
median `b*` — which is the behaviour of a real measurement and not of a coincidence. The
directional claim strengthens at region scale: the dark mode is bluer than the light on **89%** of
2,142 gated buildings (was 77% on contaminated `9D`), median shift **−6.08 `b*`**. The reader's
enum is four colour families; the survey's continuous `L*` × `b*` is what the 480-state encoding
actually wants — the two are complements, not rivals.

**🔥 And the warm-glass palette gap dissolves.** The recorded 17/56 warm dark modes (`b*` > +3) on
`9D` decomposes cleanly: decontamination alone takes it to 7/51, and conditioning on the reader's
`glazed` — the conditionality *this record's own caveat demanded* ("tint is only a glass
measurement conditional on the building being glazed") — takes it to **0/15**. All seven surviving
warm dark-modes belong to buildings the reader reads as *not glazed*: punched tenements whose dark
population is shadowed reveals and warm render, not glass. Region-wide, 14 of 226 reader-glazed
buildings (6%) measure warm, medians negative on all six sheets, `b*` p90 **+1.27**. The authored
cool palette (`b*` −9.20, −1.62, −14.34) spans the measured glass (median −4.11, p10 −9.20); no
extension is warranted, no config moves, and `facade_chroma.py` / `ring_weights.py` are not
triggered — nothing they are authored against changed.

### Decided

- **Work in the world-space unwrap, never in atlas space.** Probe 3 is the reason. It survives the
  grammar branch's death because glazing and tint are measured per building, not per chart.
- **Tint is 2-D, `L*` × `b*`, dropping `a*`.** PCA over the measured glass: PC1 68.9% (essentially
  `L*`), PC2 24.7% (the `b*` cool↔warm axis), PC3 6.5% (`a*`). A 1-D ramp would discard a quarter of
  the variance, and it is the quarter that separates bronze from blue.
- **The code rides `TEXCOORD_1` (`UV2`), not `COLOR_0`'s alpha byte.** ⚠️ Killing grammar drops the
  state count from 720 to **glazed/blank × 15 `L*` × 16 `b*` = 480**, which still does not fit in a
  byte, so the decision holds — but on the smaller margin, and the original arithmetic no longer
  describes it. `facade_uv` already spends both existing channels (`UV.x` height, `UV.y` class +
  phase), and `Q27` makes `COLOR_0`'s sRGB/linear semantics somewhere to stay away from. ~2 MB over
  the region, and a `schema_version` bump on both sides.
- **Every gate refuses rather than guesses**, and a refusal falls back to the existing hash.
- **Glazing is the reader's call, not the dip's.** The region calibration above found no dip
  threshold with predictive power in either scoping; `Q41`'s `glazed` field decides, a refusal
  falls to the hash, and the tint is read from `facade_glazing.json` only for reader-glazed
  buildings.

### Open

Nothing. ✅ The contamination check is discharged by `tools/facade_glazing.py`; ✅ the survey ran
region-wide; ✅ the threshold re-derivation is discharged by the kill above; ✅ and the `TEXCOORD_1`
plumbing shipped — reader-glazed + surveyed tint + `Q41`'s grammar in one `schema_version` 5 → 6
pass, the channel spec recorded in `ARCHITECTURE.md`'s contract table.

Three closure notes that correct this record's own estimates:

- **The measured cost is +0.24 MB of PCK, not the ~2 MB above.** 36.32 → 36.57 MB, one variable
  changed. The reasoning held — a per-building-constant `x` and an all-zero `y` compress where
  `TEXCOORD_0`'s per-vertex fractions could not — but at 97% pack compression, not the ~50%
  extrapolated from `TEXCOORD_0`.
- **The shipped layout is field-packed, not the flat 480.** "Glazed/blank × 15 × 16 = 480" was the
  capacity argument that one float suffices; what ships is `glz + 4·tint + 1024·grammar` with an
  independent refusal zero per field — 4,338 legal codes, max 6082, still exact in float32 with two
  orders of magnitude to spare. The 480 was an argument, not a format; the format is the table in
  `ARCHITECTURE.md`.
- **Float32 over `unorm16`, re-decided on stronger grounds.** `TEXCOORD_0`'s budget argument
  carries over, and the exactness argument is now structural: integer codes up to 131,071 (riders
  included) cannot survive a half-float's 11 mantissa bits, so quantising the channel is not an
  optimisation held in reserve — it is unavailable. The 2 MB `TEXCOORD_0` was told it was hiding is
  real; the 0.24 MB this channel costs hides nothing worth a scale factor in the contract.

**See.** `Q26` · `Q30` · `Q35` · `Q37` · `Q27` · `Q41` · `DATA_SOURCES.md` "Buildings"

## `Q41` — A vision reader recovers the grammar the statistic could not

**Status.** ✅ **Closed** — the reader passed its graded run first run, the full region is surveyed
(4,734 faces read, 80% of buildings with at least one read face), and **the verdicts are
consumed**: `tools/facade_grammar.py --merge` reduces the faces to per-building majority votes
(glazed commits on 1,626 of 2,214 buildings, grammar on 1,442, zero contradictions), and the
verdicts ship in `TEXCOORD_1` beside `Q40`'s tint. A refusal at any stage — face, vote, or absent
survey — is the same zero, falling back to the hash. `Q42`'s riders remain the open follow-on ·
**Owner.** `P3-9a`

**The claim.** `Q40`'s kill of fin-versus-curtain-versus-punched is real but narrower than its
wording: the taxonomy is unreachable *by a per-pixel statistic*, not unreachable from the data. Read
by a vision model, the world-space elevations classify — including both buildings `Q40`'s
classifier got wrong. `B352631575201063A0`, the dark-glass tower the `L*` threshold called
`punched`, unwraps to an unmistakable ribbon curtain wall with its rooftop signage legible;
`B355691583201063A0`, the flat render block that returned `punched` and `fin`, unwraps to a plainly
blank wall with one vent. A 19-building pilot across the height range found every well-photographed
face classifiable and every smear correctly unclassifiable.

**The mechanism is why this is not a rerun of `Q40`'s overclaim.** `Q40`'s five failure modes are
failures of context-free measurement. A reflected street raises local `L*` variance — noise to a
histogram — but a reader parses it as *reflection on glass*, which is evidence **for** curtain wall.
The signal the statistic discarded as contamination is diagnostic to a reader. `Q40` recorded
"features visible to a reader" as the overclaim that licensed nothing; it licensed nothing *about a
statistic*. A reader is now a thing a build-time tool can invoke, and that sentence becomes the
capability under test.

**The unwrap is a committed tool, and its depth buffer retires half of `Q40`'s mode 5.**
`tools/facade_unwrap.py` re-projects wall texels into metres-across × metres-up at `Q40`'s
8 texels/m, keeping per texel the surface *outermost* along the face normal — so foreign geometry
behind a façade can no longer land in its elevation. ⚠️ **Texture-baked occluders survive by
design**: a tree photographed in front of a wall is in the wall's texels, visible to the reader *as
a tree*. The histogram half of mode 5 — foreign texels feeding the glazing dip — is still owed
before `Q40`'s statistic gate is trusted; nothing here discharges it.

**The validation protocol.** 40 faces, drawn deterministically (seeded `blake2b`) from two sheets —
`11-SW-9D` and `11-SW-14B`, the second because `Q40` warns one sheet underlies every prior number —
stratified by height quartile, taking each sampled building's best- *and worst*-covered face so
refusal behaviour is tested, not avoided. Labels are in `tools/facade_grammar_labels.json`, written
from the images before the reader tool existed. The reader passes when, on its first graded run:

1. **Strict pool** (readable, refusal not acceptable, n=20): grammar agreement — label or its
   recorded `alt_grammar` — on **≥ 16 of 20**.
2. **Marginal pool** (readable but `refusal_ok`, n=6): refusal *or* agreeing classification on
   **≥ 5 of 6**; a confident disagreeing classification is the only miss.
3. **Refusal pool** (unreadable, n=14): refusal or low confidence on **≥ 13 of 14** — at most one
   confident grammar claim on a face a reader should have declined.
4. **Glazed axis**: agreement on **≥ 90%** of faces where both sides commit to a value.

Misses are adjudicated by re-inspection; a demonstrably wrong label is corrected **and every
correction is listed here** — the metric is computed against corrected labels, so label errors
cannot silently rescue a failing reader without leaving a record.

**The graded run: ✅ PASS, on the first run.** Reader `claude-opus-5`, prompt hash
`61fae4b11722bb5c`, 40 API calls and no errors:

| Pool | Result | Bar |
|---|---|---|
| Strict grammar | **19 / 20** | ≥ 16 |
| Marginal | **6 / 6** | ≥ 5 |
| Refusal | **14 / 14** | ≥ 13 |
| Glazed axis | **23 / 24** | ≥ 90% |

Every pool cleared the threshold fixed at `738e958` before the reader ran. `Q40`'s kill is therefore
confirmed as **narrow**: the taxonomy is unreachable by a per-pixel statistic and reachable by a
reader. ⚠️ **The adjudication clause above was not exercised** — no label was re-inspected and none
was corrected, so these numbers are against the labels exactly as authored. That is the stronger
reading, but it also means the one miss below is *unadjudicated*, not *upheld*.

The single strict miss is `11-SW-9D` `B358341572401063A0` W: the reader refused at high confidence
where the label says `blank`. ⚠️ **This is the taxonomy's own boundary, not obviously a reader
error** — a solid wall with no fenestration and a filler-dominated unreadable face are near
identical in an unwrap, yet the schema forces them into different pools (`blank` is a grammar;
refusal is not). The reader's note reads *"flat grey untextured filler blocks with no legible
fenestration"*, a defensible account of the same image. The lone glazed mismatch, `11-SW-14B`
`B355381529401063A0` S, is the same face where the reader read `curtain` against a `punched` label —
one coherent disagreement, not two independent ones.

✅ **Refusal is decisive, which is what makes the fallback safe.** All 14 refusal-pool faces were
refused at **high** confidence, while most marginal-pool calls returned **low**. The reader declines
where declining is right and hedges where a reasonable reader could disagree — `Q40`'s "refuse
rather than guess" contract, measured rather than assumed.

⚠️ **The labeller and the reader are the same model family, and that is recorded rather than
hidden.** Independence holds in the direction that matters — the labels predate the reader and its
API calls never see them — but a family-shared blind spot would pass undetected. A human spot-check
of the labels against the PNGs is owed before the survey is trusted at region scale; the label file
carries the images' provenance so the check is one directory of side-by-side comparisons.
✅ **Discharged 2026-08-09**: the 40 faces were reviewed side-by-side against their native-resolution
unwraps (labels shown, reader answers deliberately withheld), and no label was corrected. The
adjudication clause therefore remains unexercised, and the graded numbers stand against the labels
exactly as authored — now with a human check behind them rather than only a same-family one.

✅ **Resurveyed onto `claude-sonnet-5` (2026-08-09), by the rule this record fixed.** The pin exists
so that a model change is a graded resurvey, not a settings tweak — and that is how it was changed.
When the full-sheet run was priced (8,661 paid calls, ~$103 on Opus), Sonnet 5 and Haiku 4.5 were
graded against the same 40 labels and the same pre-fixed bars. Sonnet 5 **passed** — strict 18/20,
marginal 6/6, refusal 14/14, glazed **24/24**, prompt `d6e59b39307b215d` — at two-fifths of Opus's
price. Haiku 4.5 **failed** both the strict pool (15/20) and the refusal pool (12/14), in the
mirror-image ways the pools exist to catch: high-confidence refusals of degraded-but-readable faces,
and high-confidence reads of faces a human refused. The region survey therefore runs on Sonnet 5.
The 40 Opus responses stay in the cache under their own prompt hash — the raw record of the original
graded run, and a free replay if the pin ever moves back.

**The full-sheet spend rides the Batch API, and the batch layer is transport, never
interpretation.** Batch pricing halves the run again (~$21 against ~$41 synchronous, from ~$103 on
Opus). The design keeps the validated reader's authority intact: a submitted request carries
`request_params` verbatim — the same bytes the synchronous path sends, built in one function so the
transports cannot drift — and `--batch-collect` writes each result into the same content-addressed
entry `cached_read` would have written, keyed by prompt hash and image fingerprint via the
`custom_id`. The output tables are then authored by the ordinary survey path replaying that cache
with **zero API calls**, so the committed, validated code path still writes every row. An errored or
expired face is left a cache miss — any later run, batch or synchronous, simply reads it again.

✅ **The full-region survey ran 2026-08-09**: 2,214 buildings, 8,704 faces, 8,614 paid batch reads
with **zero transport errors**, ~$21 all-in against the ~$103 the run priced at synchronously on
Opus. All six tables were authored by a credential-less replay — zero API calls — so the committed
tool re-derives the region from the cache alone. The read rate lands where the coverage-bias caveat
above said it must: **54% of faces read** (4,734), 46% refused, **80% of buildings carry at least
one read face** (1,769 of 2,214). The distribution is the city the art direction describes:
`punched` **3,195 of 4,734 reads (67%)** — tenement and public-housing fabric — then `mixed` 739,
`curtain` 554, `fin` 124, `blank` 122; the one sheet where `curtain` outnumbers `punched` is
`11-SW-9D`, the Gloucester Road tower cluster, which is exactly where it should. 88% of reads are
low-confidence — the validated hedge on degraded photogrammetry, not a defect. `Q42`'s free riders
populated at region scale: `storey_count` on 3,786 faces (median 15), `emphasis` on essentially
every read, `signage` on 1,045 faces, and `band_period_floors` still almost never commits (143) —
consistent with its 0/25 validation showing.

**Reproducibility answers `Q37`'s ghost by tolerance, not byte-equality.** This is the repo's first
non-deterministic input producer: a rerun against the same bytes may differ. The tool therefore
caches every raw API response beside its output table in the sources cache, keyed by content, model
and prompt hash; every output row records the model ID and prompt hash that produced it; and
re-derivation acceptance is defined as *the validation thresholds above passing again*, not as
byte-identical tables — the same shape `Q37` used when it made survey acceptance a tolerance.

✅ **Replay is verified, not just designed.** A second `--validate` immediately after the graded run
made **zero API calls** and returned an identical verdict. `cached_read` takes the client as a
factory rather than an instance, so a fully-cached rerun needs neither the SDK nor a credential. The
40 responses live under `etl/sources/hong_kong/facade_grammar/raw/<sheet>/`, gitignored under hard
rule 7, sharing a key with the full-sheet survey so a validated face is free when the sheet runs.

🔴 **`PROMPT_HASH` does not cover the unwrap, and the cache is now populated.** The hash is
`blake2b(prompt + schema + model)`; the *image* is the reader's other load-bearing input and appears
in neither the key nor the row. `435f079` refactored `facade_unwrap.py` between the labelling and
the graded run, so this run is trustworthy only because the refactor was checked to be
output-preserving **first** — 40/40 canvases byte-identical against `738e958`, and the new `faces=`
narrowing output-neutral. **Nothing on disk records that check.** The next unwrap change will replay
40 cached answers against images they no longer describe, silently, and the thresholds will pass on
a reader nobody measured — `Q37`'s ghost re-entering through the one input the stamp omits. Owed
before the full-sheet run: fingerprint the encoded PNG in each cached entry and refuse a hit whose
image no longer matches. ⚠️ **Folding the unwrap into `PROMPT_HASH` is the wrong shape** — it keys
on source rather than output, so it would discard every paid entry on any unwrap edit, including a
proven no-op like `435f079`'s.

✅ **Fingerprinted, and the replay re-verified against the fingerprinted entries.** A cache entry's
key is now `<face>.<PROMPT_HASH>.<image_hash>.json`, where `image_hash` is the `blake2b` of the
encoded PNG — a hit is defined by prompt *and* image, so a stale entry is unfindable rather than
silently replayed, and every output row records the `image_hash` it was read from, closing both
halves of "neither the key nor the row". Superseded entries are kept: they are the raw record of a
paid read, and an unwrap change that is later reverted hits them again for free. The 40 existing
entries were backfilled by **pure rename** — no paid bytes rewritten — with fingerprints computed
from the current unwrap, which is sound only because `435f079`'s byte-identical check tied that
unwrap to the one the graded run used; the backfill is that unrecorded check becoming disk state.
Acceptance: `--validate` with no credential in the environment returned the identical verdict —
zero API calls against the new keys — and a test pins that a mutated canvas forces a re-read while
the superseded entry still answers for its own image.

**The per-building row cache is guarded separately, by `UNWRAP_HASH`.** A row hit skips the unwrap
itself, so the image fingerprint above can never protect it. Its key therefore hashes the code the
images actually pass through: `facade_survey.py`, `facade_unwrap.py`, the glTF parser and texture
decoder under both (`pipeline/gltf.py`, `pipeline/buildings.py`), and `facade_grammar.py`'s encoder
with its two row-shaping knobs — deliberately *not* the whole reader file, so a log-message tweak
does not re-rasterise a sheet.
That is source-keying — the shape rejected for `PROMPT_HASH` above — and it is correct *here*
because the two caches cost different currencies: invalidating a row costs file reads and
rasterising with **no API spend** (regeneration re-checks each face against the response cache, so
a no-op refactor replays every paid entry free), while source-keying the response cache would
discard the paid reads themselves. No row files existed when the guard landed, so nothing needed
migrating.

**The licence covers the read.** The data grant is explicit — *"browse, download, distribute,
reproduce … for both commercial and non-commercial purposes"* (`LICENSING.md`) — and sending sheet
imagery through a third-party API is reproduction within that grant. The survey's output is derived
government data and stays in the uncommitted cache like `facade_lab.json`; the labels file is
hand-authored judgment *about* the imagery and is committed.

⚠️ **Coverage bias bounds what the survey can ever claim.** The imagery carries real texels on a
median 14.3% of wall area, occlusion-biased toward street-facing walls (`DATA_SOURCES.md`). A large
share of the 2,214 buildings will refuse, and must — refusal falls back to the existing hash, which
is the same contract every `facade_hue` gate already keeps.

**What it feeds.** Grammar rides the `TEXCOORD_1` payload `Q40` already designed for glazing and
tint — an enum of five states beside the 480 `Q40` counted, decided in the same channel-design pass.
`Q26`'s objection to candidate `A` — invented surface on accurate massing — is what a validated
survey dissolves.

### Decided

- **The reader is `claude-sonnet-5` through the official SDK, structured-output constrained**, so a
  malformed response is a retry at the API layer, not a parse. The model is pinned in the tool; a
  model change is a resurvey, not a cache hit — exercised once, above, when the pin moved from
  `claude-opus-5` on a passing graded run.
- **The schema collects render-facing fields beyond the graded axes** — storey count, heavy-band
  period, podium split and shopfront glazing, balconies, pattern emphasis — because they ride the
  same call for free and adding them later would change the prompt hash, making the shipping reader
  a different reader from the validated one. ⚠️ **They are advisory until separately validated**:
  the thresholds above grade grammar, refusal behaviour and the glazed axis, and nothing else. The
  prompt orders nulls over estimates for every one of them — a storey count is *counted or absent*,
  never inferred from the building's size.
- **Validation before scale, one sheet before six.** The reader touches `11-SW-9D` in full only
  after the 40-face gate passes, and the other five sheets only after that run is graded.
- **Every gate refuses rather than guesses**, and a refusal falls back to the existing hash —
  `Q40`'s contract, unchanged.

### Open

Nothing. ✅ The graded validation run — the acceptance test this record existed to hold — passed,
every gate between it and the region was discharged in order (image fingerprint, label spot-check,
the Sonnet 5 resurvey, the full-region run), and ✅ the consumption shipped with `Q40`'s: the
face→building reduction votes each axis independently under a strict majority (a tie refuses), a
glazed-true-`blank` or glazed-false-`curtain` contradiction refuses the grammar and keeps the
24/24-graded glazed axis, and `signage` never leaves the per-sheet tables. In the shader the
surveyed grammar maps onto the existing four-treatment grid — `mixed` takes the generic ribbon,
`blank` forces solid through the glazed override — and a hash-drawn treatment remains the refusal
behaviour, per building, exactly as this record specified. `Q42`'s riders are the follow-on, in
`Q42`.

**See.** `Q40` · `Q26` · `Q37` · `Q35` · `DATA_SOURCES.md` "Buildings" · `LICENSING.md`

---

# Tasks

## `P0-1` — Building data is fully scriptable

**Status.** ✅ Done

See `Q2`/`Q3`/`Q5` above for the claim and its consequences. What belongs here is the method fault:
the earlier finding that buildings were the top data risk came from **reading the CKAN resource list
and stopping there**, instead of opening the portal's own Downloads panel. The CKAN list genuinely
does only point at interactive portals.

**See.** `Q2` `Q3` `Q5` · `DATA_SOURCES.md`

## `P0-3` — A scaffold is not a signed on-device build

**Status.** ✅ Done · `P0-3b` ⬜ Not started

**Claim.** The written criterion "builds and runs on the device floor" bundled a project scaffold
together with Android SDK setup, Xcode, an Apple signing identity and physical hardware. Split into
`P0-3` (imports clean, exports verified) and `P0-3b` (signed on-device builds).

**What the split found.** Android exports to a 25 MB APK using the prebuilt template with **no Gradle
or Android SDK required**. iOS fails only on a missing App Store Team ID, which is the correct
failure.

⚠️ **`rendering/textures/vram_compression/import_etc2_astc` must be enabled** or Godot refuses to
export **any** arm64 target, including Apple Silicon macOS.

**Consequences.** `P0-3b` blocks `P2-4`'s and `P2-6`'s reviews — how the car feels under a thumb is
reachable no other way. It is not on the critical path.

**See.** `Q4` · `ARCHITECTURE.md` "Project settings"

## `P0-4` — Config declares its datum, not just its CRS

**Status.** ✅ Done

**Claim.** `hong_kong.yaml` declares `crs.geodetic` alongside `crs.projected`, and `config.py`
refuses to load without it.

**Why.** **HK1980 and WGS84 differ by ~304 m on the ground in Hong Kong** — measured, not assumed:
EPSG:2326's own natural origin is published on the HK1980 datum, and feeding those identical digits
in as WGS84 lands 304 m away. That is a fifth of the width of the region, and far larger than the
~10 m people expect.

**How it is held.** `test_crs.py` asserts the two datums disagree by >250 m. ⚠️ **That assertion is
really a canary** — if it ever shrinks, PROJ has fallen back to a *ballpark* transformation.
Verification is against external facts, not the code's own output: the load-bearing test projects the
published grid origin and expects the published false easting/northing, to sub-millimetre.

**Other choices worth knowing.** `transformer()` is `@cache`d per CRS pair; `always_xy=True`
everywhere, because EPSG:4326 officially declares lat-then-lon and a silent axis swap is the classic
way to relocate a city into the Indian Ocean; `GameTransform` is **pyproj-free** so the per-vertex hot
path never re-enters PROJ; the origin is **rounded to whole metres**, so a library upgrade cannot
renumber every tile; and `deck_height_m()` raises on an unmapped `ELEVATION` rather than defaulting.

⚠️ **Elevation-level keys reject `bool`, not just non-`int`.** PyYAML implements YAML 1.1, where a
bare `on`/`off`/`yes`/`no` key resolves to a boolean — and because `bool` subclasses `int`,
`isinstance(key, int)` waves it through. `False == 0` as a dict key, so a stray `off:` would silently
redefine **ground level**. Verified: such a config loaded without error and returned 42.0 m for level 1.

**See.** Region bounds · `Q10`

## `P0-5` — The grey box cleared the handling and could not clear the premise

**Status.** ⚠️ Passed, conditional

**Verdict.** *"verified and seems acceptable, but I don't know if it is fun or good until we have
either the Hong Kong scene or game mechanism."* Read as a pass on what `P0-5d` could test, and a
rejection of its premise — `PLAN.md` claimed the grey box would answer "is this a game?", and it did
not. Recorded as `Q8`, which closed later on the real city.

**Phase 1 released anyway**, because the gate's purpose was to avoid sinking ETL effort into a game
that does not work, and the user's answer is that the ETL output is a *precondition* for knowing.

**Deliberately not actioned.** Sustained full lock still spins the car, and `brake_force = 900` gives
3 m/s² of braking against 5.33 m/s² of acceleration — **the car accelerates faster than it stops**.
Both real, neither blocking.

**See.** `Q8` · `P0-5a`

## `P0-5a` — Custom raycast on `RigidBody3D`, not `VehicleBody3D`

**Status.** ✅ Done · **Locked** (CLAUDE.md)

**Claim.** The vehicle is a custom raycast controller on `RigidBody3D`. Jolt is used for trimesh
collision and raycasts, *not* for its built-in `VehicleBody3D`.

⚠️ **`VehicleBody3D` is not broken under Jolt.** It instantiates, simulates, accelerates, steers and
brakes; the wheel query API works. Anyone repeating the spike should not expect a crash — the problem
is subtler.

**The decisive finding: `wheel_friction_slip` is isotropic.** One friction number covers every
direction, so `grip_lateral` and `grip_longitudinal` collapse into each other and a drift cannot break
lateral grip without destroying traction and braking with it. Measured while holding throttle,
friction × 0.35 on the rear axle alone cost **30% of speed over 2 s** — an implied scrub of 0.151/s
against a target of 0.080 — at a **162.6°** peak slip angle against a 14° threshold. A full spin, not
a slide, violating `GAME_DESIGN.md` on two counts at once. Of 18 `HandlingProfile` fields, 4 map
directly, 4 are fightable and **10 are absent**.

**Could it be tuned out? Partly — and that is the argument against it.** Yaw damping, counter-steer
assist and per-axle friction curves would suppress the spin, but that is an arcade correction layer
built on a physical model actively resisting it, leaving `VehicleBody3D` contributing only suspension
raycasts. Every future tuning change becomes a negotiation with the engine rather than a dial, and
vehicle feel is expected to be iterated on more than anything else here.

**Re-asked and re-refused.** The user asked directly whether the built-in vehicle would give
anything, which is the explicit instruction hard rule 1 requires to reopen a locked decision. It
genuinely would — per-wheel angular velocity for wheelspin and lockup, `get_skidinfo()` for smoke and
tyre marks, ~340 lines deleted. Still refused on the capability gap above. "Wheels only" is not
available either: `VehicleWheel3D` simulates solely under a `VehicleBody3D`. ✅ **The two features
worth having are cheap to build here instead** — `_apply_tyre_forces` already computes the slip both
need — and are scheduled into `B4`.

**Consequences.** `HandlingProfile` gains a `Suspension` group and an `anti_roll` field. **Spring rate
is specified as natural frequency in Hz**, so it stays correct when vehicle mass changes — ⚠️ but it
is *not* gravity-independent: static sag is `g_eff / (2πf)²`, so `gravity_scale = 1.6` deepens sag by
the same 1.6×. Wheel **geometry** stays out of the profile; the resource describes feel, which is
shared across the roster.

**Verified.** Drifting is *cheaper* than gripping — 0.270 speed scrubbed per second against 0.297, at
a 12.6° peak slip angle against 16.4°. Suspension settles at **50.6 mm sag** against 50.7 predicted.

⚠️ **The importer can reinstate `VehicleWheel3D` behind your back**, from nothing but a mesh name.
The mechanism and the suffix list are in `ARCHITECTURE.md`.

**See.** `ARCHITECTURE.md` "Stack" · `P3-11`

## `P0-5b/c/d` — Five handling bugs no linter catches

**Status.** ✅ Done — the fifth found 2026-08-17, long after the other four

Recorded because each was found by *measuring* rather than by reading, and none is reachable by
static analysis:

- **Anti-roll signs were inverted** — force pushed *down* on the already-compressed side, amplifying
  roll instead of resisting it. The car flipped on the first hard corner.
- **Coasting drag divided by `delta`**, making it framerate-dependent and ~35× too strong.
  `apply_force` already integrates over the tick.
- ⚠️ **A `Node3D`-typed `@export` does not resolve from a hand-authored `.tscn`** — it silently read
  null and the camera never moved. Worth remembering for every scene authored outside the editor.
- **Steering was inverted.** `InputRouter.steer` is `+1` for right, but a *positive* rotation about
  `+Y` turns the `−Z` forward vector toward `−X` — left. The headless tests missed it because they
  only ever steered one direction and never checked which.

Also fixed: wheel raycasts accepted wall faces as ground (free traction and a launch ramp off any
building), and road slabs were exactly coplanar with the ground plane and z-fought across their whole
surface.

**The fifth, found 2026-08-17 from a user report — too little speed-independent longitudinal force.**
Reported as "the car should brake at similar force at high speed and low speed, but it brakes very
slowly at low speed". ✅ **The report was exactly right, and one root cause produced two separate
faults.**

Godot's `default_linear_damp` (0.1, unoverridden — see below) is *viscous*: it scales with speed and
vanishes as the car slows. The controller's own speed-independent forces were small enough beside it
that the engine's share dominated the feel, so every longitudinal deceleration fell away at low
speed. Ablated on the flat skidpad at the shipped `brake_force = 900`:

| mid-speed | deceleration under full brake |
|---|---|
| ~65 km/h | **4.78 m/s²** |
| ~35 km/h | 3.95 m/s² |
| ~15 km/h | 3.38 m/s² |
| ~4 km/h | **3.07 m/s²** |

**A 36% fall** — the constant 3.0 m/s² the dial buys, plus `0.1 × v` that is worth 1.81 m/s² at
65 km/h and 0.12 at 4. And the coast had the same defect in its pure form: `-rolling_speed ·
corner_mass · coast_drag_per_s` is viscous with no constant at all, so it is an exponential decay
with no zero. Coasting from 30.6 km/h the taxi was **still rolling at 3.9 km/h 13.8 s later** and
would never have stopped.

⚠️ **An earlier draft of this record claimed the brake was already speed-independent** (12.4 km/h/s
at 62 km/h against 11.2 at 5) and blamed the coast alone. That was the gradient error recorded
below: the high-speed sample was taken on a downhill stretch of Expo Drive, which ate exactly the
term under test and made the curve look flat. The user's premise was sound and the measurement was
not.

⚠️ **It is player-visible only because one pedal serves brake and reverse.** Below `STATIONARY_KPH`
the pedal means reverse, so a driver arriving at walking pace *must* release it — and then there is
nothing left that can bring the car to rest. The two designs are independently reasonable and the
gap is in the seam between them, which is why neither `P0-5a`'s measurements nor `P3-11d`'s lamp
work saw it.

Fixed by `rolling_resistance_mps2`, a speed-independent term in the coast, shipped at **0.8 m/s²**;
that same 31 km/h coast now reaches a **dead stop in 6.5 s**, and 5 km/h takes **1.5 s**. Two
properties are load-bearing:

- **It is capped at the deceleration that lands exactly on zero this tick** — `|rolling_speed| /
  delta`, the same treatment the lateral force already gets. Uncapped, a constant force does not
  stop a rolling car, it *reverses* it and then holds it reversing. The cap is also what stops the
  car juddering on a shallow gradient: it settles at the gravity term instead of flipping sign.
- **The viscous term stays.** It is what makes lift-off at 100 km/h read as engine braking rather
  than as a handbrake, and a constant alone cannot express that. The terms add, so lift-off drag at
  60 km/h goes **2.50 → 3.30 m/s², up 32%**; `coast_drag_per_s` is the dial if that reads as too
  much. Throttle-on acceleration is byte-identical — the coast branch is gated on both pedals.

⚠️ Under 0.8 m/s² the taxi holds still on grades below ~2.9°, since `gravity_scale` 1.6 makes a
slope pull 60% harder than its angle suggests.

### ⚠️ `coast_drag_per_s` is the minority of the coast drag

Found while checking the arithmetic above, and the reason the 60 km/h figures are 2.50 rather than
the 0.83 the dial predicts. `project.godot` does not override Godot's `default_linear_damp` of 0.1,
so the engine damps the body underneath the controller. Ablated on `skidpad.tscn`:

| `coast_drag_per_s` | `rolling_resistance_mps2` | measured decay |
|---|---|---|
| 0.0 | 0.0 | **0.100/s** — the engine default, to three figures |
| 0.05 | 0.0 | **0.150/s** — the dial contributes 0.0497 against its stated 0.05 |
| 0.05 | 0.8 | reaches zero; no exponential constant to quote |

So the dial is honest about its own contribution and still only **one third of the viscous total**.
Every coast number in this record is the total, taken end-to-end from `drive.sh` telemetry; anyone
tuning from the written value alone is reasoning about a third of the force. Not changed: the engine
default is doing no harm, and `project.godot` is the file `CLAUDE.md` forbids touching casually.

### 🔴 The first round of these numbers was measured on a gradient, and did not compose

Recorded because the error was invisible in every individual figure and only showed up when two of
them were added together. The first ablation ran on `city_drive.tscn`, where the two runs happened
to sit on different stretches of Expo Drive: engine-only came out **0.089/s** and engine-plus-dial
**0.108/s**, a difference of 0.019 where the dial asks for 0.050. Both figures were real
measurements of the car; neither was a measurement of the *dial*, because at 4 km/h a **0.14°**
micro-gradient — two centimetres of fall over eight metres, far below anything a telemetry line
shows — is worth about 0.05/s on its own, the whole quantity under test.

⚠️ **A drag coefficient must be measured where the ground is known flat.** `skidpad.tscn` exists for
exactly this and its header already says so ("a measuring instrument, not a place to play"); it was
not reached for because the bug had been *found* on the city scene and the ablation simply continued
there. Re-run on the skidpad, the same three runs compose to within 0.6%.

🔴 **The expensive consequence was not a wrong number, it was a wrong verdict.** The same gradient
put the 62 km/h brake sample on a downhill and the 5 km/h sample on the flat, which flattened a
36% falloff into an apparent 12.4-against-11.2 — and on that basis this record's first draft told
the user their premise was mistaken and that only the coast was at fault. It was the user who was
right. A measurement that contradicts a user's direct experience of their own software is the
case for re-running it on known ground, not the case for closing the question.

### `brake_force` 900 → 2,400 N — the other half of the same fix

Raising the constant term is the only lever that makes braking speed-uniform, because the viscous
share it competes with is the engine's and is not tunable from the profile. Same skidpad ablation,
both values:

| mid-speed | 900 N | 2,400 N |
|---|---|---|
| ~65 km/h | 4.78 m/s² | 9.65 m/s² |
| ~35 km/h | 3.95 m/s² | 8.88 m/s² |
| ~15 km/h | 3.38 m/s² | 8.36 m/s² |
| ~4 km/h | 3.07 m/s² | **8.06 m/s²** |
| **fall, 65 → 4 km/h** | **−36%** | **−17%** |

Low-speed braking is **2.6× stronger in absolute terms and less than half as speed-dependent**,
which is precisely what was asked for. A stop from 72.8 km/h now takes 2.30 s over 21.9 m.

The old value was also simply too weak to be safe on this map: 3,600 N on 1,200 kg is **0.31 g**, and
on the HKCEC down-ramp the taxi *gained* speed under full braking (38.90 → 40.65 km/h) because
`gravity_scale` 1.6 makes the slope pull harder than 0.31 g. It now sheds ~20 km/h/s there.

⚠️ **Grip was never the constraint and still is not.** `grip_longitudinal` 2.0 caps each wheel at
2 × its load, ~9.4 kN at rest against 900 N of brake — the old value was using **10%** of the
traction available. Load transfer under 0.8 g moves ~646 N per wheel across a 2.6 m wheelbase, so
the unloaded rear axle still holds ~8.1 kN of cap. The dial stays linear well past here; it does
not begin locking wheels as it rises, and a future stronger brake is a tuning change and not a
model change.

**See.** `P0-5a` · `GAME_DESIGN.md` "Controls"

## `P1-1` — The fetcher derives its own sheet list

**Status.** ✅ Done

**Claim.** `fetch.py` handles two source shapes — fixed-URL (roads) and index-derived (buildings) —
because that is what the publishers offer. The pipeline knows "some feature property holds a download
URL"; that it is called `Format_glTF` is config, which is what keeps hard rule 3 intact.

**The corroboration is the result.** Intersecting the region bounds with the 3,456-feature index
selects exactly the six sheets `P0-1` recorded by hand, and **nothing in config names them**. The
bounds, the datum and the index all line up.

**Decisions worth knowing.** Caching is **fetch-once, not fetch-if-changed** — CLAUDE.md fixes the
snapshot, so re-running must not quietly adopt upstream's new month of road data. `REVISIONDATE` is
per sheet, so a forced re-snapshot costs **3.2 MB instead of 265 MB**. Downloads are atomic. **The
API key is never written down** — URLs are read from the fetched index at run time and everything
recorded passes through `redact()`. **Bounds are reprojected before comparison, never compared across
datums**, pinned by a test using a sheet that only the HK1980 misreading selects. Edge contact counts
as overlap. Selecting zero tiles is an error.

⚠️ **Four defects an end-to-end run could not have surfaced.** A short HTTP response was committed as
complete and cached forever — `read(amt)` returns `b''` on a premature close rather than raising, so
a truncated file was committed and recorded *at its short size*, making the truncation a permanent
cache hit (reproduced: 5,000 bytes accepted against a declared 1,000,000). **The atomic-rename
machinery only ever protected against interruption of *our* write.** A failure partway through
discarded the whole manifest, costing ~283 MB after one transient error. `--force` re-downloaded
everything, contradicting its own documentation. And a poisoned index would have cached as "zero
buildings" silently — a portal answering an outage with HTTP 200 and a JSON error body parsed fine,
selected zero sheets, and exited 0.

**See.** `DATA_SOURCES.md` "Access notes"

## `P1-2` — Vertex clustering, and meshes are assigned to tiles whole

**Status.** ✅ Done

**Claim.** Buildings are decimated by **vertex clustering**, not quadric decimation, and assigned to
tiles **whole** except where a mesh is too big for a tile.

**Why clustering.** The source is extruded footprints, so clustering keeps silhouettes blocky and
axis-aligned — which *is* the art direction, where quadric decimation would smooth the corners and
fight it. It is robust on triangle soup, which this is, and its aggressiveness is one number in
metres, so the tiers stay tuning data.

**The cluster key includes the facing, not just the cell**, or a wall normal averages into the roof
normal above it and rounds off the faceting the whole style rests on. ⚠️ "Lossless" is precise about
**positions**: a cluster *mean* is not the same thing — summing k equal doubles and dividing by k need
not reproduce them. A representative fixes it. ⚠️ The ground is the one exception and takes
`height_field=True`, dropping the facing term — see `Q29` and `Q25`.

**Why whole-mesh assignment, and its exception.** Splitting a building at a boundary leaves an open
shell and makes half of it pop. But the source contains elevated road structures **up to 1,984 m long
in a single mesh**, which whole-mesh assignment handles two ways, both wrong: one whose centre falls
outside the region **vanishes entirely**, taking a viaduct across the whole map with it; one whose
centre falls inside gives a 150 m tile a 2 km bounding box. Oversized meshes are partitioned by
triangle.

**The geometry is verifiably really Wan Chai**, which matters because a coordinate bug here produces a
plausible-looking city in the wrong place. The tallest building converts back to **374.5 m at
22.28011 N, 114.17358 E** against Central Plaza's published 374 m at 22.28028 N, 114.17361 E — a
**19 m** offset, inside its own 78 m footprint.

⚠️ **Two silent Godot failures, and they look identical.** Godot 4.7's glTF importer reads `COLOR_0`
but leaves `vertex_color_use_as_albedo` **off**, so every tile imports as a white block — corrected by
a post-import script wired as a project-wide importer *default*, since per-file would not survive a
fresh clone. And the `"normalized": true` flag on the colour accessor is load-bearing: drop it and
Godot reads every colour as 1.0 and the whole city renders white.

**No glTF library.** `pipeline/gltf.py` reads and writes the format directly in ~380 lines. The read
side would have used a few percent of trimesh or pygltflib, and the write side has to lay out
accessors and buffer views by hand under either.

**Superseded.** ❌ The terrain verdict — "267 MB, unaffordable" — was **224 MB of JPEG and 43 MB of
geometry**. Geometry was never the problem. Replaced by `P3-10`, which ships no texture.

**See.** `Q16` · `Q25` · `Q29` · `P3-10`

## `P1-3` — Three things the source forced on the road graph

**Status.** ✅ Done

**Claim.** `python -m pipeline.roads` turns the 17 MB geodatabase into **797 edges over 615 nodes with
217 turn restrictions**: 175,610 → 3,553 vertices, 592 of 615 nodes in one component (96.3%), 736 at
grade / 45 elevated / 15 tunnel.

⚠️ **`ELEVATION` must not key nodes.** It sounds obviously right and it breaks the network: all 36
endpoints where two levels meet are **ramp touchdowns**, so applying the rule takes the region from 6
connected components to **24**, dropping the largest from 583 nodes to 389 and cutting a **163-node
elevated island** adrift — most of the Wan Chai Interchange and the Canal Road Flyover, the reason
the region was chosen. `DATA_SOURCES.md` carries why the hazard it guards against never arises here.

**Roads are clipped to the region, where buildings are not.** A building is assigned to a tile whole
because splitting a mesh leaves an open shell; **a polyline cut in two is two polylines**, with
nothing to seam. It is also not optional: the geodatabase filters on bounding box, so the
Central–Wan Chai Bypass is selected and then runs **570 m out into the harbour**. Measured before
clipping, **14.2% of the region's road length was outside the region**.

**Lane counts are authored, not published.** Verified against every field of every layer: **there is
no lane attribute anywhere**. What the source does carry is a signed speed limit on the 10% of edges
that differ from the urban default, a decent proxy for expressway versus street.

**Other properties worth knowing.** Endpoints coincide exactly — 601 distinct at full float precision,
nearest *distinct* pair **2.26 m** apart — so node snapping needs no tolerance, but must be no finer
than a millimetre: two clusters differ in their last bits and at a tenth of a millimetre they split,
silently disconnecting Johnston Road at Fenwick Street. The geometry is over-densified past belief —
one 51.7 m centreline carries **54,330 vertices** — so Douglas–Peucker is a *correctness* measure for
`P1-4`, not a size optimisation, and is written iteratively because nearly-collinear input is exactly
what produces both the vertex count and the stack overflow. `EDGE1END` is a hint, not the truth: in 4
of 217 it names an end 4–39 m away while the opposite end coincides exactly, and taking the shared
node resolves all 217.

**Deliberately not in the output.** The turn layer's `EXC_VEH_TYPE` / `INC_VEH_TYPE`,
`PART_TIME_REST` and `EFF_ALL_DAYS`. ⚠️ One restriction in the region excludes taxis — a turn a real
red taxi may make and the graph says it may not. Adding a field is a schema change on both sides, so
it is recorded in `DATA_SOURCES.md` for `P3-3` and `P3-8`.

**Recorded, not fixed.** `roads.py` reaches into `buildings.py` for `Placement` and `read_sheet`, and
reads its terrain class out of the *buildings* config section, crossing the format/policy layering
rule. The right shape — a shared sheet-reading module — is easier to see once more stages have said
what they need from the same sheets.

**See.** `Q9` · `Q11` · `Q12` · `Q13` · `DATA_SOURCES.md` "Roads"

## `P1-4` — The road surface is one mesh, capped per level, never merged

**Status.** ✅ Done

**Claim.** One mesh for the whole region — 28,423 triangles, a fortieth of the massing, and on screen
whenever the player is. Tiling it would buy nothing but seams and 65 draw calls in place of one.

**Junctions are filled by the convex hull of the arms' corners.** The property that makes this right
is convexity: the hull's boundary passes through every arm's two end corners, so the mouth between
them is inside the cap **by construction** — no gap is possible — and it stops at the kerb line rather
than spilling into the corner between two streets, which is pavement. 393 of 393 single-level
junctions covered.

**Capped per elevation level**, which is the opposite of how `P1-3` keys nodes and right for the
opposite reason: a node exists so a flyover and the ramp under it stay one network, where a junction
cap is a piece of tarmac, and there is none between a street and the tunnel roof 8 m below.

**Self-intersection was the one thing needing real geometry work.** A corner tighter than the road is
wide has no inner offset curve. Three repairs measured: simplify harder before offsetting (8 folds
left, 43% of the region's segments); cap the width to the local turning radius (1 fold, but
**pinches the carriageway to zero** at 24 places); **hold the inner boundary still where it would
reverse** (0 folds, 93 collapsed quads of 5,188). The third is also what the offset of a too-tight
corner actually *is* — the inside stops while the outside sweeps past — and it touches neither the
centreline nor the width.

**Opposed carriageways are drawn twice and left overlapping**, and that decision turned out not to
exist: the premise that two ribbons leave a gap down the middle of Lockhart Road was never checked
against the widths, and is false. Five of six pairs already overlap at their authored width. **Nothing
in `surface.py` knows what a dual carriageway is.**

**Two driver-reported defects, one root cause: every edge was extruded alone.** ⚠️ **A kerb lying
mid-road is a kerb, not a lane marking** — `kerb_colour` against asphalt, 0.5 m wide and 0.15 m tall,
at **33.0 km of 98.6 km of kerb line**, because a dual carriageway is two edges each kerbed on both
sides and `widen_default: 1.6` exists *precisely so* those pairs overlap. Not cosmetic: the mesh ships
as `road_surface-col` so the collider covers the risers, and `suspension_travel_m = 0.18` means a
0.15 m step is **83% of the car's total bump travel**. ⚠️ **The junction pinch is the convex hull** —
at a bend the hull's straight chord cuts the outside of the turn off, narrowing the road to
`cos(half the turn)` of its width; 8 of 49 two-arm nodes were narrower than their own thinner arm.
Fixed by mitring through the cap: kerbs overlapping a neighbour's carriageway **33.0 km → 0**, nodes
pinched **8 → 1** (a 172° hairpin, which no mitre should reach), triangles 35,039 → **25,028**.

**What qualifies as "through" is not a tuning value.** Two arms at a node is one street bending, so
the corner is carriageway and up to 90° is mitred; three or more and a sharp corner is the pavement
between two streets, so the limit drops to 45°. Filling that corner would pave the footpath, which is
what the hull was chosen to avoid.

**Rejected: merging opposed pairs into one ribbon.** The tempting read of the kerb bug. It reopens a
decision this module's docstring closed with measurements, needs polygon clipping, and would change
what `roadsurface.json` indexes. Only the *kerb* asks about its neighbours.

⚠️ **The first cut of the overlap test made the stage 8.3× slower and every check still passed** —
`_within` was **86% of the whole stage**, from a Python loop the file's own style forbids and 476,000
`np.errstate` context managers (**15% of the stage on their own**) guarding a division whose result
was masked away. Vectorised: 2.49 s → **0.36 s**, agreeing with the old test on 39,048 samples with
zero disagreements.

**Still open, deliberately.** The cap carries **no kerb and no lane coordinate** — `fan` writes zero
UVs. Both were true before and neither was what was reported.

**See.** `Q13` · `Q19` · `Q23` · `Q24` · `ART_DESIGN.md` "Roads"

## `P1-5` — Fare nodes keep the kerbside position

**Status.** ✅ Done

**Claim.** `pos` is the **source** position, not the snapped one. 11 of 29 nodes lie outside even the
widened carriageway, because the published points are on the pavement and `P1-4` draws from
centrelines. Only the height comes off the road.

**Why not snap.** Moving each node onto the road throws away the only thing the source surveyed. **The
kerbside is where the passenger stands**; where the taxi stops is derivable from `nearest_edge` and
`edge_t`, and the reverse is not.

**What the contract gained, and why then rather than later.** `edge_t`, because `nearest_edge` alone
names a road that can be 200 m long. `pickup`/`dropoff`, because a quarter of the published points are
**drop-off only** (66 of 275 territory-wide), and flattening that would let a player hail a fare where
no taxi may stop for one. Both free here and expensive after `P1-6` freezes the shape.

⚠️ **Rule order in the category table is load-bearing and fails silently.** `Status_EN` is free text
with sixteen spellings, so matching is first-hit-wins over substrings: `DF` before `PU/DF` files every
pick-up point as drop-off only and still produces a complete, plausible `fares.json`. `load_city`
refuses a table where an earlier rule always shadows a later one, and an *unmatched* category raises.

⚠️ **A `P1-3` bug found on the way.** `clean_text` normalised to NFKC, a *compatibility* fold that
rewrites the full-width brackets Chinese sets its parentheticals in as ASCII. Harmless for road names,
wrong for 98 fare-node names that go on a bilingual HUD. NFC now, with NFKC used only for the
null-sentinel comparison.

**See.** `Q14` · `Q15` · `DATA_SOURCES.md` "Fares and points of interest"

## `P1-6` — The manifest names the other documents, and the export stage checks them

**Status.** ✅ Done

**Claim.** `city.json` **references** rather than inlines. Each consumer wants a different document at
a different moment, and each is separately versioned, so merging would make a change to fare nodes
bump the schema on the document carrying the tiles.

**`bounds_game` is the union of the content, not the region rectangle** — `ARCHITECTURE.md` carries
the figures and what a consumer gets wrong by sizing off the rectangle.

**The stage validates what it wrote, and that is the actual deliverable.** Four classes of error exist
that **no individual stage can see, because each document is internally valid in all of them**: a fare
node naming an edge the graph no longer has; a tile whose GLB was never written; a document left over
from another region; geometry outside the declared bounds. Each is a real sequence rather than a
hypothetical. Verified by breaking three at once.

**Reproducibility was measured, not assumed.** Rebuilt from an empty `out/`, **every one of the 199
files was byte-identical**, the sole difference being the `generated_utc` stamp. That is what makes
"did this change anything?" answerable by `diff` for every future ETL change.

**The orchestrator calls each stage's own `main`** with the arguments the documented per-stage command
would pass. Composing them any other way creates a second code path that can drift from the one people
actually run.

**See.** `ARCHITECTURE.md` "Data contract" · `Q16`

## `P1-7` — The manifest is the only route to the tiles

**Status.** ✅ Done · **Phase 1 gate passed**

⚠️ **The directory listing had to go, and it was not a style preference.** `DirAccess.get_files_at`
works in the editor, where `res://` is a folder. In an **exported build** it is a PCK archive Godot's
virtual filesystem will not enumerate, so the call returns an empty array and the game renders an
empty city **without a single error**. It would have looked like a content problem in the first device
build. Deleted rather than deprecated.

**The gate's word is "georeferenced", so something had to be able to disagree.** `tools/verify_city.gd`
measures each imported mesh against the `aabb` `export.py` recorded: **all 65 tiles agree to within
1 cm**. The tolerance is generous against what causes drift (float64 into float32 costs ~0.1 mm at
1.7 km) and tight against what it looks for (an axis flip or dropped offset moves a corner by metres).
Proven non-vacuous by nudging one tile 0.5 m east: 15 findings, exit 1, nothing spurious.

⚠️ **What it cannot check is z-fighting.** `--headless` loads the dummy rasteriser, so there is no
frame. A **windowed** run can: render, nudge the camera 2 cm, diff — a fighting surface flips wholesale
under a sub-pixel move where anti-aliased edges only shift. **653 of 921,600 pixels — 0.071%** on
Hennessy Road. Evidence, not proof: one camera at one place.

**The sync is manifest-driven, not a directory copy.** `tools/sync_generated.sh` asks the ETL what
`city.json` names and copies that, which keeps stage intermediates out of the bundle and deletes tiles
a previous build left behind — nothing else would notice them, because every check starts from the
manifest and the manifest has forgotten them.

**See.** `ARCHITECTURE.md` "Build pipeline" · `P1-6`

## `P2-1` — The city streams, and LOD is per mesh class

**Status.** ✅ Done — review passed

**Claim.** `CityStreamer` loads and unloads tiles on a worker thread by the published `aabb`.
`class_lod_cell_sizes_m` holds `INFRASTRUCTURE` at `[0.0, 0.5, 1.0]` against the building default
`[0.0, 1.5, 4.0]`.

**Why LOD is per class.** `collapse` clusters vertices by cell, so **any structure thinner than the
cell has its top surface merged into its bottom one**. A 30 m-wide, **0.8 m-thick** deck goes 12
triangles → **2** at a 1.0 m cell; a 20 × 20 × 60 m tower stays at 12 at every cell size. The tier was
never too coarse for buildings — it was always too coarse for infrastructure, and merging the two into
one mesh before collapsing meant one cell size had to serve both. **Ordering is the whole fix:** bucket
by class, collapse each at its own cell, *then* merge — which keeps the tile one mesh and one draw
call. Cost: worst-case visible triangles +3.6% against a 300k budget, chosen over an outright exemption
(+20% at LOD1, +57% at LOD2) because a deck only has to beat its own thickness.

**Evidence.** Draw calls peak **70 → 53** against 150; worst-case *visible* triangles
**398,574 → 240,598** against 300k — the baseline was over, the streamed city is under. Measured
in-engine at the same five places before and after, because quoting one spot's "before" against
another's "after" is how every bundle figure in this project drifted.

**Resident triangles are reported, never gated, and the measurement says that was right.** The worst
case is 405,210 resident against a 300k budget — but the budget is 300k *visible*, and the streamer
culls to a **disc** while the renderer frustum-culls to a **cone**: at that same point, 402k resident
draws as 240k visible. Gating on it would have tightened the bands by ~40% to satisfy an arithmetic
mismatch.

**The design is split in two, and that is what makes the third criterion structural.**
`TileStreaming` lives in `scripts/core/`, is pure, and takes an `AABB` and returns an int — there is no
code path from it to a file, so a distant tile cannot be rejected *after* being loaded.

⚠️ **One correction to a claim made here.** Tall towers do *not* survive LOD1 well because they are
big boxes — measured, towers ≥100 m keep **36%** of their triangles at LOD1 against **44%** for
everything else. They are hit *harder*. `ART_DESIGN.md`'s LOD policy carries why they read as fine
anyway.

**The landmark half was declined for a better reason than "not implemented".** There is no landmark
key in the source — the sheets carry `BUILDING` and `INFRASTRUCTURE` and nothing else. More usefully,
`ART_DESIGN.md` specifies the ~5 hero buildings as hand-authored models placed via `landmarks.json`;
they never pass through `buildings.py`, so the question is moot for exactly the buildings that
motivated it. (Still true after the `P3-6` amendment made HKCEC mesh-sourced: `pipeline/landmarks.py`
reads the same sheets as a stage of its own, and `buildings.py` still only *removes* — the two meet
nowhere but `export.py --check`'s set-equality.)

⚠️ **Proving a check can fail was itself a false green.** Breaking `plan_distance_to` reported exit 0
and no failures — the edit orphaned a local, `unused_variable` is promoted to error, the script never
parsed, and `quit(1)` never ran. **Never read raw `godot` output and call it a pass**; `tools/check.sh`
is the only thing that can fail.

**See.** `Q16` · `Q28` · `ARCHITECTURE.md` "Runtime systems"

## `P2-2` — Publish the derived width, not the widening rule

**Status.** ✅ Done — review passed

**Claim.** `roadgraph.json` publishes `width_m` as the *authored* street, while `P1-4` draws the ribbon
at `width_m × widen_for(...)`. The widening lives on the surface style and `config.py` keeps it there
on purpose, so the game had no route to the width of the tarmac it was driving on — a lane centre from
the graph sat a quarter of the widening short. **What ships: `surface.py` records the half-width it
already computes, and `export.py` carries it into `city.json` without recomputing.**

**Two routes rejected.** **Publish the widening rules** — GDScript would reimplement `widen_for` and
its "fastest matching rule" semantics: two implementations of one rule across a versioned interface.
**Mirror the factor in a `.tres`** — satisfies the tuning-as-data rule literally while creating exactly
the drift this repo keeps paying for. A third, **read lane geometry from the surface UVs**, is rejected
*for this* and worth keeping for `P3-8`: `TEXCOORD_0` answers "which lane am I in?", a lookup, where
`P2-2` needs the inverse — and it is `(0, 0)` on junction caps.

**Performance is a check, not a number someone wrote down.** Region-wide 10 m lattice, 15,865 probes:
p50 14 µs, **p99 45 µs** against a 1 ms budget. **Probing the whole region rather than the road is the
whole design** — a query on a centreline is won in the first ring, a query mid-block expands rings
until the 60 m bound stops it, so the **misses are the expensive population** (11%, which is more than
the top 1% and therefore exactly what p99 lands in). A road-only probe reports 9 µs and understates the
worst case by five times.

⚠️ **The gate is p99, not max, and that was measured rather than judged.** Across runs the maximum
ranged 44–229 µs while p99 moved by a single microsecond. *A lone outlier is a fact about the machine;
a p99 over thousands of probes is a fact about the code.*

⚠️ **The "one parse" claim was false when first written.** Both previews took `RoadGraph.shared()` into
a **local**. `RoadGraph` is `RefCounted` and the cache is weak, so the only strong reference died when
`_ready` returned. **A weak cache only works if consumers hold a member.**

**`Q13` is enforced rather than described.** Only level-0 segments enter the index, while `polyline_of`
still serves all 797 because `P3-3`'s traffic will need them. Proven non-vacuous by indexing off-grade
segments on purpose: 482 of 505 probes resolved to a flyover.

**Two contract defects worth keeping.** 74 of 797 edges publish `{"en": null}`, and `str(null)` in
Godot is the literal `"<null>"`, so the `is_empty()` guard meant to substitute "(unnamed)" never fired
for 9% of the network. And `has_carriageway_widths()` documented "every" and implemented "any".

**See.** `Q13` · `Q23` · `ARCHITECTURE.md` "`roadgraph.json`"

## `P2-3` — The start line is queried, not written down

**Status.** ✅ Done — review passed · **Verdict.** *"car seems ok"*

**Claim.** `RoadSpawn.at_fare_node` resolves fare node `f_004` through `RoadGraph`, and `basis_facing`
builds the rotation with `Basis.looking_at`. Almost all of `P2-3` is a deletion: a twelve-float
`Transform3D` literal in the scene and forty lines of `ARCHITECTURE.md` explaining how not to transpose
it. **The query reproduces the literal to 4 dp.**

**The heading is deliberately not passed to the query** — `ARCHITECTURE.md` states why. The
principle: passing the car's rotation in would let the car decide which way a two-way street runs.
**The street decides.**

⚠️ **An assertion alone is not enough, because a transpose is not a 180° flip.** It mirrors the heading
about world −Z: 171.9° wrong on Expo Drive, 180° on a due east-west street, and **0° — a silent no-op —
on a north-south one.** So `verify_spawn.gd` builds the transposed basis and requires it to *fail*,
with a 10° floor on the discriminating angle.

⚠️ **Autoloads are not registered under `--script`**, so any headless tool touching one fails to
compile — and `verify_spawn.gd` then *printed `ok` and exited 0* while erroring, caught only because
`tools/check.sh` greps stderr as well as reading the exit code.

**The verdict is narrow.** It says the placement change did not damage handling `P0-5` had already
accepted. It says nothing about feel in the hand, which needs `P0-3b`.

**See.** `P0-3` · `ARCHITECTURE.md` "Coordinates"

## `P2-5` — Buildings get collision from a mesh name

**Status.** ✅ Done — review passed

**Claim.** `buildings.py` names its finest tier `<tile_id>-col`; Godot's glTF importer reads the suffix
and builds a `StaticBody3D` with a `ConcavePolygonShape3D` at **import** time. That is the entire
game-side change. **No shape is built at runtime, and the collider cannot drift from the mesh because
it *is* the mesh.** The idiom was already in the repo — `P1-4` gives the carriageway its collider the
same way.

**Why it had no owner.** `P2-5`'s criterion is *"no clipping through buildings"* — unreachable, because
a `SpringArm3D` collides with nothing until the buildings do. `PLAN.md` gave that decision to `P2-1`,
which decided correctly that **a building collider is an ETL product, not a runtime one**, then closed.
The decision was right and it left nobody holding the work, so the region shipped as a hologram.
⚠️ **A capability named only in a design doc has no owner** — dependency graphs link tasks to tasks,
and the collision was never a task to depend on. The same shape recurred with the player's own car.

**Only the finest tier, and that is policy rather than economy.** A tier is chosen by distance, so the
coarse one is resident only beyond the 250 m band where nothing can touch a building.
`verify_tiles.gd` asserts **both directions** — present on tier 0, absent on every other — because a
suffix that spread would be invisible in every screenshot and show up only as bundle bytes.

**Cost: 21.10 → 26.27 MB PCK, +5.17 MB**, measured from two exports with one variable changed. Worth
stating what it is *not*: tier 0's 434,149 triangles as raw un-indexed faces would be 14.91 MB, and the
pack compresses them to a third.

⚠️ **`P2-6` must re-measure hitching.** Instantiating a tile now also registers a trimesh with Jolt on
the main thread, and `max_instantiations_per_frame` is 2. `P2-1`'s "no hitching" was accepted before
that cost existed. It is invisible at 120 fps on an M4 Pro and is exactly what the device floor finds.

**The camera verdict was narrow and it stood.** *"camera work mostly with one exception where a road
suddenly appears mid air"* — that is not the camera. Measured at the car's own position, road geometry
within 60 m is either y 2–4 (the street) or y 8–10 (the deck above), and **nothing sits in the
0.3–3.0 m band the car occupies**. It is `Q20`.

⚠️ **A check that hangs is worse than a check that fails**, because a timeout names nothing.
`RoadGraph.shared()` returned `null` from a guard written to stop it — the fallback used an inline
`{}`, which is **untyped** — and the resulting script error left `_init` before any `quit()`, so the
SceneTree ran forever. Fixing that turned the hang into a **silently wrong pass**, reporting `ok`
computed from absent data. `verify_spawn.gd` now refuses on `has_carriageway_widths()`, which is
stronger than a null-check: a `city.json` that loads cleanly but publishes an **empty** table passes
the null-check and fails this one.

**See.** `Q19` · `Q20` · `P2-1`

## `P2-7` — The off-grade carriageway lies on its structure

**Status.** ✅ Done — review passed

The claim, the evidence and the residual are `Q20`; the width rule is `Q23`; the ramp classification is
`Q13`. What belongs here is what the task learned about **measuring**.

⚠️ **Four sampler ideas were wrong before they were measured.** `1.` **There is no parapet to
subtract** — transverse profiles across 8 flyovers show the deck centre is a flat plateau with raised
lips **+0.11 to +0.92 m, off-centre at ±3 to ±6 m**, which a centreline never touches. One config knob
deleted before it was written. `2.` **Seeding from the existing height and taking the nearest hit is
worse than taking the highest** — the multi-hit spread is 1.7–2.2 m (slab thickness), so the sampler
hits the top *and the underside of the same slab*, and the old seed sits below the deck 66% of the
time. What works is **slab clustering plus continuity**. `3.` **The terrain gate cannot be a minimum
clearance** — level-1 ramps genuinely touch down, a continuous 0–15 m spectrum with no gap to cut in.
What separates is the other side, decisively: `e425` samples **8.3 m below** terrain against a
next-worst of 0.54 m. `4.` ⚠️ **The fallback was the bug, and it hid behind a correct-looking result.**
`INFRASTRUCTURE` **stops being modelled where a ramp reaches grade**, so falling back to `terrain + 6.0`
rebuilt the exact cliff the task exists to remove, at the most visible place in the region. An
uncovered station now takes the deck **either side of it**, interpolated. **Three of those four were
the plan's own answer; the fourth appeared in no plan** and was found only because a number came back
worse than predicted and the gap was chased instead of rounded off.

⚠️ **The two grading tools were wrong seven times between them, and every one produced a plausible
table.** `deck_error.py`: matching the structure colour *exactly* found 428 of 434,149 triangles,
because `colour_for` **jitters every class** — a class is a *ray* through its base colour, not a value.
Keeping both face windings scored the carriageway against a deck's underside. Sampling the road mesh's
own vertices measured **overhang**, because `roads.glb` carries vertices only at the carriageway edges,
which overhang the deck *by design* — and it looked exactly like a real defect, one named flyover at a
consistent 8 m. **Overhang is `Q19`'s question; height is `Q20`'s, and conflating them manufactures a
failure.** Worst, leaving unmeasurable stations out of the denominator read "acceptance met, exit 0"
while a third of the carriageway had stopped being measured: a total break was already loud, a
*partial* one was silent. Coverage is now measured against what the centrelines asked for and fails
below 90%. `overhang.py` was wrong three ways, all **a probe that measures itself** — asking "on
structure?" across the whole ribbon made the measurement depend on the drawn width, so narrowing would
shrink the very number that says whether narrowing worked.

⚠️ **The ETL's own error column is not an acceptance measurement.** It resamples the written polyline
and asks the *same* `HeightField` that produced it, so it can only show the write-out is faithful to
the sampler. Its value is that its `before` column reproduces the recorded baseline — it validates the
harness, not the fix.

**Both graders are committed and neither is wired into `tools/check.sh`** — they need a built region,
which `check.sh` does not require and should not start requiring. The reason to commit them: **a
measurement that cannot be re-run is an anecdote.**

**Two structural changes the fix forced.** `build_region` became **two passes**, because whether a
level-0 edge sits on a ramp depends on whether its node is also reached by another level, which no edge
can know until every edge has been placed. And `deck.clearance_m: 0.20` is **a layer rather than a
fudge** — a real road is a wearing course laid *on* a structural deck — but its size is set by `P2-1`'s
0.5 m decimation lifting the shipped deck a median +0.041 m, not by paving practice. `deck_error.py`
**subtracts** it, so the metric still measures error rather than counting a deliberate layer as one.

⚠️ **Four config spellings loaded in a state they could not act on**, each now refused with a test,
because the symptom of any of them is *output identical to a city that never asked for deck sampling* —
a config error shaped to survive review: `deck:` with nothing under it; `.nan`, which passes both
`<= 0.0` and `< 0.0` then makes every downstream comparison false without raising; `.inf`; and a fifth
unknown key beside the four.

**The schema-bump rule this established**, now in `ARCHITECTURE.md`: **bump where a consumer would be
*wrong* to keep its old interpretation, not wherever bytes change.** `roadgraph.json` → 2 is the pure
case — nothing added, removed or renamed; `polyline.y` simply began meaning something different, which
a consumer cannot tell by inspection and a diff cannot show. `roads.glb` did **not** bump: its geometry
moved and no attribute changed meaning.

**See.** `Q13` · `Q20` · `Q21` · `Q22` · `Q23`

## `P3-7` — Window bands are procedural, and the storey height was measured

**Status.** 🟡 Awaiting review

**Claim.** `assets/shaders/city_facade.gdshader` bands every vertical façade in world space — no
texture, no atlas, no second draw call — reading a surface marker and a per-building phase the ETL
packs into `TEXCOORD_0`. **Zero triangles moved**, one draw call per tile, **+4.01 MB of PCK**,
`city.json` schema 4 → 5.

**The storey height was measured off real façades rather than chosen, and the guess would have been
wrong.** One individualised sheet, autocorrelated down each wall texture's V axis and discarded:
height-weighted median floor pitch **2.77 m**, column pitch **2.42 m**. Shipped as **2.8 m**. The
obvious guess was 3.2 — a Western commercial storey — and at 40 storeys that is five floors of error on
one tower. Hong Kong's domestic floor-to-floor really is that tight.

⚠️ **The eye said the contrast was too strong and the measurement said the opposite.** `window_opacity`
was dropped 0.62 → 0.30 on judgement; the *rendered* frame measured the same way as the photographs
came back **0.107 against 0.126** in the source. It was already under, and went back to 0.62. A dark
square on a pale wall in full sun reads far stronger than its share of the row.

⚠️ **A statistic that lands exactly on a limit you chose is reporting the limit.** The probe's first
answer was a median floor pitch of exactly **2.00 m** — the lower bound of its own search range.
Autocorrelation decays monotonically away from lag 0 unless something genuinely repeats, so `argmax`
over a window returns the window's own left edge on every aperiodic wall. Detrending and taking a
*local peak* moved the median to 2.70 m.

⚠️ **`mesh.merge` refused any mesh carrying UVs at all** — one condition covering two questions — so
every tile would have failed. The texture half is still right: two textures cannot share a primitive
without an atlas. **UVs with no texture are a shader coordinate and merge like any other attribute.**

⚠️ **A float32 rounding trap.** The marker and phase share one float as `marker + seed`; float32's
spacing near 2.0 is ~2.4e-7, so `STRUCTURE + 0.9999999998` rounds to **exactly 3.0** — an unknown
marker with a zero phase. The phase is quantised to 1/256, exactly representable at every marker, and
the test brute-forces all 768 combinations rather than sampling.

⚠️ **Three places must agree and only one can fail loudly.** The ETL names the glTF material
`city_facade`, `generated_scene_import.gd` dispatches on that name, and the shader reads the payload.
Break any link and every tile keeps its default `BaseMaterial3D` and renders in flat vertex colour —
**which is exactly what the city looked like before this task**. `verify_tiles.gd` asserts both the
`TEXCOORD_0` format and the resolved material path, because **a check performed by hand is a check
that will not be performed again.**

**The marker is derived from the palette, not from a new config key** — `ARCHITECTURE.md` states the
rule. `FACADE` is the fallback rather than a listed case, so a new massing class bands until someone
gives it a flat colour.

⚠️ **`ARCHITECTURE.md` predicted "~2 bytes/vertex quantised" and this ships float32 at four times
that** — measured at +4.01 MB over 937,889 vertices. `unorm16` would save perhaps 2 MB and costs a
scale factor in the contract on both sides; not done, because the budget is 200 MB. Recorded so a later
region short of room knows where the 2 MB is.

**See.** `Q26` · `Q28` · `Q2′`/`Q3′` · `ART_DESIGN.md` "The window-band shader"

## `P3-7a` — The task closes at what was judged, and the riders are gated on the look

**Status.** ✅ **Closed as shipped.** `W1`, `W2` and `W3` landed, graded and accepted; `R1`, `R2`,
`R3`, `R4`'s pack, two-tone walls and the paid ground-band batch are **neither cancelled nor
scheduled** — conditional on `P3-9a` reopening `Q26` · **Owner.** `P3-9a`

**Claim.** Every remaining rider is consumed behind `survey_apply`, and `Q26` closed on `C`, which
ships `survey_apply = 0.0`. The remainder therefore renders nothing in the build that reaches a
player, and **cannot influence `P3-9a`** — the round that would price it, because `P3-9a` grades
`C`. Running the gate first prices every rider for free; building them first spends the expensive
half of the set just before the odds become knowable at no cost.

**What shipped is what was judged.** `W1` (`Q44`), `W2` (`Q45`) and `W3` (`Q46`) are user verdicts
on frames. The riders are enrichment *beyond* the `A‴` the user accepted, so stopping does not
degrade `A‴`: `city_facade_elements.tres` holds exactly the configuration that was graded, and the
answer to a driver panel that rejects flat surface is one `cp`, available now, not a rider.

⚠️ **The task's own safety criterion no longer proves anything, and that is why it stops rather than
coasts.** "Everything lands dark behind `survey_apply`; parked look byte-identical at every step"
was load-bearing while the look was undecided — it let risky work proceed behind a switch. With the
switch permanently off, **a rider that draws nothing at all passes it**. A check whose difficulty
depends on a decision taken elsewhere has to be re-read when that decision lands.

⚠️ **The remainder is the low-reliability half, and this is measured rather than felt.** `Q42`'s
fill rates are prioritisation evidence, not validation, and the validated items are the ones that
landed. `R4` was graded against a pre-fixed bar and **failed** — \|err\| p50 **10.76 m** against
2.8, Spearman **ρ = 0.076**, no per-building signal. `R3` has no validation. `band_period_floors`
commits **0/25**. `R1` has **no hand labels in existence**: 25 must be authored before its bar can
be fixed. `R2` walks into `Q48`, where four instruments read 2.8 / 3.38 / 3.32 / 3.28 and nothing
reconciles them.

⚠️ **Cost is not symmetric across the remainder, so the stop order is not the dependency order.** A
shader or tuning rider is `git revert`. The ground-band batch is not — the prompt hash *is* the
reader's identity, so a new field costs a new graded run **plus** a paid full re-survey. It is also
the one item whose wait is free by design (the cache), and the one that becomes **most** valuable if
`P3-9a` fails on street-level surface, since it targets the player's eye level — the survey's
worst-covered band.

**What closing it unblocks.** `P3-7a` was the last task in flight before the `P3-9a` gate, so
closing it is what opens the gate. `P3-9a` answers the register's top risk — novelty not surviving
the first session — which no façade rider addresses.

**What reopens it.** `P3-9a`'s ≥3 HK drivers rejecting the city *and* attributing it to flat
surface. `Q26` then reopens on one `cp`, and the ground-band batch becomes the first item rather
than the last.

⚠️ **`W4` is idle, not stopped, and must not grow.** Its canonical entry was HKCEC's base, and
`P3-6` removed HKCEC from the tiles entirely, so what remains is stragglers rather than a
population. It is **never** a route around the survey at scale: **771 grammar-refused buildings** is
the measurement that disqualified overrides as the systematic fix.

**See.** `Q26` · `Q30` · `Q42` · `Q44` · `Q45` · `Q46` · `Q47` · `Q48` · `P3-7` · `PLAN.md` `P3-9a`

## `P3-10` — The ground is a mesh class, and it collides

**Status.** 🟡 Awaiting review

**Claim.** Terrain is one more entry in `buildings.classes`. That is the whole design: being a class
gets it the tile's single material for free, so it costs **no draw call**, and it cannot end up
somewhere the buildings are not.

**Evidence.** LOD0 +87,649 triangles; 65 → 66 tiles (ground reaches a corner no building did); draw
calls per tile unchanged at **1**; **PCK 27.73 → 32.30 MB (+4.56)**. ⚠️ **The PCK grew nearly twice
what `ART_DESIGN.md` predicted, and the collider is the difference** — the 1.5–2.5 MB estimate counted
geometry. The split between geometry and `ConcavePolygonShape3D` was *not* separately measured, so it
is not quoted.

**It collides, and that was a decision rather than an inheritance.** `ART_DESIGN.md` said the first
pass was "visual only, with no collider" while two other lines promised it merged into the tile
primitive for "+0 draw calls". **Those were never compatible** — `_write_tile` names the merged tier-0
mesh `<tile_id>-col`, so anything merged into it is solid. User's call: merged and solid. Ground you
can see and fall through is worse than no ground for a free-roam recognition test. ⚠️ **The standing
consequence belongs in `ARCHITECTURE.md`:** any future class added to `classes` inherits tier-0
collision whether or not it asked.

**`ground_sink_m: 0.20` — the guess and the measurement agreed, which is not the same as not
measuring.** Share of carriageway area proud: 0.00 m → 47.5%; 0.15 → 5.2%; **0.20 → 3.3%**; 0.35 →
1.2%. 0.20 is the shallowest value passing both gates, and deeper costs a visible gap under a 0.15 m
riser.

⚠️ **Shipping ground did not create a defect, it revealed one.** See `Q24`. Three explanations were
measured and rejected first, each of which would have sent the fix somewhere useless: tile decimation
(median +0.000 at the 4 m cell, inside the sink); the sink being too shallow (refuted by the table
above); and the tunnel portals (the tail is spread across ordinary hill streets, not concentrated).
⚠️ **The first measurement was taken at polyline vertices and came back clean**, which is exactly where
a chord error is zero by construction — **a probe placed where the geometry is defined cannot see a
defect that lives between definitions.** Asking the same question *between* vertices changed the answer
by a factor of sixteen.

⚠️ **`tools/ground_clearance.py` gates on a different population from the one it reports first**,
because the two measure different defects and blending them makes the sink unfalsifiable. The gate is
the share of **points the road's height was sampled from**; the headline share over all cells carries
`Q24` as well and is a regression bar, not a standard. A single number would have read 3.3%, looked
like a failing sink, and sent the next person to deepen it.

**See.** `Q18` · `Q24` · `Q25` · `Q29` · `ART_DESIGN.md` "Ground"

## `P3-11` — The taxi is generated, and the chassis generates it

**Status.** 🟡 Awaiting review · **Verdict on the first round.** *reads as 紅的, does not read as a
Crown Comfort*

**Claim.** `tools/make_vehicle.py` generates `taxi_body.glb` and `taxi_wheel.glb`. **The chassis is an
input, and that is the whole design** — `Chassis` mirrors the `WheelMount` markers and `handling.tres`
rather than proposing geometry of its own, so the mesh is built *around* hardpoints `P0-5` tuned
against. The desync this avoids is the nastiest kind: the physics never reads a mesh, so a model built
to its own wheelbase looks right, drives to the old tuning, and shows nothing wrong in a drive.
**The scene is the authority; the generator follows.**

⚠️ **A guard is only as good as the copies it knows about.** The wheel meshes were parented at an
authored offset — a fourth copy of `suspension_rest_length_m` — and the guard filtered on the
`WheelMount` script id, so it never looked at those nodes. Retuning the spring would have moved the
raycasts and left the meshes behind, which is *precisely* the failure the design exists to prevent.

**Rounded by chamfer, not by smoothing.** This reverses an earlier caution that bevels would fight the
flat-shaded city. **They do not.** The distinction that matters is chamfer versus smooth shading: faces
stay flat, edges stay crisp, there are simply more of them. `corner_cut_m = 0` still yields the cheap
square car `B3`'s traffic wants.

**Triangle budget: `ART_DESIGN.md`'s 800–2,000 stands and the model came up to meet it**, currently
**1,168 in scene**. The detail knobs are `Proportions` fields, so `B3` can instance a cheap variant by
passing fewer segments — which answers the objection that a heavier player car makes traffic expensive.

**The car is untextured all the way through.** The decal sheet and its bitmap font are deleted; the
plates are flat colour, white front and yellow rear per the HK standard, and that asymmetry is what
proves the model is not mirrored. ⚠️ `BADGE_GREEN` takes the palette to **seven** where `ART_DESIGN.md`
says 3–5. Flagged rather than quietly taken.

⚠️ **Removing a part is not free when other parts are mounted on it.** `_seated_depth` derives each
fixture's depth instead of taking a thickness. It sampled two points of a profile that has **three** —
`face_inset_m` is *not* monotonic, the body being furthest out in the *middle* of the range — so a lens
stood **8.5 mm proud where 15 mm was promised**, and nothing showed because the shortfall was smaller
than the margin. **A contract test that checks the sign of a quantity does not check the quantity.**
⚠️ Known limit, not fixed: `_seated_depth` compensates in y and the corner chamfer is a function of x,
so a fixture outboard of the chamfer floats clear of the paint by up to 10 cm.

⚠️ **The instruction described where something should end up and was read as permission to delete it**
— three times, on the bumper, the decal and the badge. **When a note says a feature is in the wrong
form, the default is to change its form; deleting it needs its own reason.**

⚠️ **Tests written in the same round as the code they check can be unable to fail.** Four found in one
review: an area sum over a strict selector that collapsed to `0.0 == 0.0` on an empty selection; a test
that re-derived the formula and compared it against itself, staying green when `-` became `+`; a
"clears both wheel openings" check that pooled every face and took one global `min`, so deleting the
rear handle passed. **Any test whose subject is "a filtered set" needs one assertion that the filter
found anything at all.**

⚠️ **The rocker strip and the red valance are unjudged from the play camera**, and the reason is
structural: the chase camera tracks the car's *facing*, so it stays behind the car even through a full
drift, and the flank never enters frame. The argument for them — that a long high-contrast line
survives where an isolated small shape does not — is an argument, not a measurement.

⚠️ **Detail that cannot be seen at review distance is not detail, it is triangles.** The mirrors, door
handles, shut lines and pillars were listed as missing while already modelled — 16–150 mm features seen
from ~8 m in a 1080p frame. The fix is to make them read, not to add them again.

⚠️ **The visual body is not the collider, and the collider did not move.** `P0-5a` rejected a trimesh
player collider and `P0-5` tuned against the box. The mesh is larger on every axis, which is the safe
direction — but the visible roof can pass under geometry the collider would have stopped. Worth a look
when `P2-6` measures.

⚠️ **`drive.sh` renders whatever is already imported.** Rewrite a `.glb` and every screenshot afterwards
is of the *old* mesh, silently, with `DRIVER OK` and exit 0. **A probe that comes back pixel-identical
far more likely means the change never arrived than that it had no effect.** Run
`godot --headless --path game --import` before believing any screenshot.

**See.** `P0-5a` · `ART_DESIGN.md` "Vehicles" · `ARCHITECTURE.md` "The importer can reinstate
`VehicleWheel3D`"

## `P3-6` — Two heroes replace their source meshes, and the contract is the deliverable

**Status.** 🟡 Awaiting review · two of five shipped (HKCEC mesh-sourced, Central Plaza
generated), 2026-08-12 · **amended same day: HKCEC ships as its repainted source mesh**

### Amendment — the HKCEC hero is the source mesh, repainted (2026-08-12)

**The user called it, and the record below had already conceded the premise.** Three review
rounds (below) each moved the generated hero *toward* the source mesh by measurement — 8 m
slices, the banana plan, the fairing — until the generator was a lossy compressor of a mesh
already on disk, and the user judged the source "clearly superior in model details and quality".
The evaluated verdict: use it. `pipeline/landmarks.py` (a stage of its own, after `buildings`)
extracts stem `B358761603301063` from sheet `11-SW-9D`, moves it to the landmark local frame
(`rot_y_deg` pins to 0.0 — the mesh keeps source orientation, so the 6.4° PCA bearing retired),
**slices every triangle at the ribbon elevations** (`mesh.slice_horizontal` — crisp vertex-colour
bands are edges the mesh must actually have), repaints per triangle by authored-normal facing and
centroid elevation, welds attribute-identical vertices back (`mesh.weld` — colour in the key, so
a band edge never bleeds), and ships it as **generated output** under
`assets/generated/landmarks/`.

⚠️ **Licensing is why nothing about this is committed.** A repainted government mesh is
government-derived data (hard rule 7): it lands in the gitignored bundle under the publisher's
terms, `LICENSING.md` and both LICENSE files now say so, and the committed
`assets/authored/landmarks/hkcec.glb` is deleted. The paint itself became config data: a
`source_paint` block on the landmark entry (materials by name into the `materials:` table, so
`Q33`'s exposure check stays total; ribbon constants moved from the retired `Hkcec` dataclass
with their pixel-profile provenance). The generator keeps Central Plaza and the three unshipped
heroes; its HKCEC half — `WingStation`, the wing lofts, the deck/pier/infill machinery the last
review round added — is deleted, with the measured knowledge preserved here and in the yaml
comments.

**Contract changes.** `city.json` 7 → 8 (manifest gains `landmark_assets`; the authored hkcec
asset a v7 bundle names no longer exists — same asset-set argument as 6 → 7), `landmarks.json`
1 → 2 (entries gain `triangle_budget`, read per entry by `verify_landmarks.gd`; the authored 8k
stays as its fallback for authored heroes). `export.py --check` now holds three spellings of each
built model equal (config asset, `landmark_assets.json` path, manifest list) and *does* stat the
generated `.glb` — the authored ones remain deliberately unstatted. `P2-1`'s sentence survives on
its letter and its point: heroes never pass *through* `buildings.py`; the mesh-sourced ones are
built by a stage of their own from the same sheets, meeting the exclusion only at `--check`'s
set-equality.

**Measured.** Source 41,273 triangles → **99,577 shipped** (the growth is walls cut at every
ribbon edge — the price of crisp bands in vertex colour; walls-only slicing was measured at
90,171 and rejected as not worth the T-junctions), 203,302 vertices after the weld (298k
unshared), 6.72 MB glb. Budget pinned at 120k. PCK **33.85 → 39.04 MB** (+5.19 MB; budget
200 MB). ⚠️ Triangle residency: the streamer's tile worst case is unchanged (**280,783** — the
verify samples tiles only), but landmarks sit *outside* the streamer and are always resident, so
the true resident ceiling is now ≈ **380,700** (tiles + 99,877 of heroes) where the hero used to
ride inside the tile figure at a third of the size. The 300k budget is stated in *visible*
triangles and was not re-measured; `P2-6` (the performance gate) should measure a frame under
HKCEC first, and the next always-resident landmark re-opens this arithmetic before it ships.
Draw calls unchanged (one hero node either way). `check.sh` all green including
`verify_landmarks` (both heroes ok); the three road graders re-run by hand and within bounds
(deck p90 96.8% measured, P2-7 met). Street and wing screenshots from the Expo Drive East
viewpoints confirm pale hull / dark storey ribbons / darker roof on the real massing — canopy
trusses, roof layering and prow the generator never carried.

⚠️ **The photos demanded a fourth correction, and it rebuilt the classifier** (user review,
2026-08-13: "the texture doesn't follow the accurate shape"). The first repaint classified each
triangle by its own normal, so wherever the seabird roof rolls steep its faces fell past the
threshold and took banded wall — ribbons ran across the sweeps like contour lines. Two mechanisms
replaced it, both data-tuned on the `source_paint` block. **(1) Surfaces grow.** Roof and soffit
are seeded by the normal thresholds and then grown across every edge whose faces meet at less than
`crease_deg` (35°): the sweep stays one surface to its rolled edges because it is smooth, and
growth stops at the eave because that is a crease. **(2) The building's own photo vetoes the
bands** (`reference_texture` — the user's call to "ref the original texture"). The individualised
`…A0` variant carries the aerial atlas on identical geometry, so each source triangle maps to its
photo by corner identity, threaded through the slicer as a scratch UV channel. A ribbon strip —
one band level on one connected wall, decided strip-wise because per-triangle verdicts turned
photo noise into broken dashes — survives only where its samples read darker than the same wall
half a pitch above and below (local vertical contrast; an absolute cut fails because baked sun and
shade span 0.03-0.66 luminance, an order of magnitude over the glazing's own contrast, measured
in-band vs out on all eight facings). Uniform surfaces contrast at ~1.0 and lose their strips;
strips the photo cannot decide keep the measured procedural layout. The texture is consulted and
discarded — nothing shipped carries it, the palette stays the four `Q33`-checked materials, and
Pillow stays a dev extra behind a lazy import (`pyproject` note updated;
`DATA_SOURCES.md`'s "NOT NEEDED" verdict on the individualised set amended to "NOT SHIPPED",
with the sheet expected at `sources/<city>/individualised/`). Triangle count unchanged (99,577 —
the slicing is identical); PCK **39.04 → 38.67 MB** (fewer colour boundaries weld better); the
street and wing frames now match the reference photos on both counts the user reviewed: grey
sweeps clean to their edges, thin storey ribbons only where the elevation carries them.

⚠️ **What did *not* change:** the exclusion machinery and its two-sided acceptance, the
`landmarks.json` placement contract, Central Plaza (authored features — crown, mast — the source
captures badly; the generated model stays), the `W4`-is-moot call, and the vertex-colour-only
rule (`landmark_vertex` is now owned by `pipeline/landmarks.py` and imported by the generator, so
the two emitters cannot drift).

**Claim.** `landmarks.json` ships as drafted in `ARCHITECTURE.md`, with the gaps the draft left
now decided: it is **assembled by `export.py`** from a `landmarks:` block in the city config (no
new stage — ~2 entries and one CRS conversion do not buy a stage's ceremony), named in the
manifest under a `landmarks` key (`city.json` 6 → 7 — an old reader would draw holes where the
excluded buildings stood), and keyed by **stems**, the `DATA_SOURCES.md` cross-dataset building
key, not the draft's invented `bldg_*` ids. Placement is authored in the projected CRS — the
numbers are checkable against the sheets by eye — and `rot_y_deg` is a **compass bearing** with
exactly one conversion site (`generated_landmarks.gd::placement_of`). `P2-1`'s "heroes never pass
through `buildings.py`" survives intact: the stage only *removes* — and the removal is where
`excluded_bounds` gets recorded, because identity dies at `merge` and nothing downstream can
recover where a building stood.

**The acceptance criterion is enforced from two sides that cannot see each other.** "Source
geometry excluded" is an identity claim and a geometry claim. Identity: `export.py --check` holds
the config's stems and `buildings.json`'s recorded exclusions **set-equal, both directions** — a
typo'd stem (z-fighting) and an orphaned exclusion (a hole) are different failures with different
messages. Geometry: `verify_landmarks.gd` probes the shipped tier-0 tiles for triangles inside
each excluded footprint's **interior core** — half the plan extents, floored 16 m above base —
because the full AABB is honestly occupied at its rim (Phase 1's shared wall overlaps HKCEC's
corner by metres; Central Plaza's footbridge clips its box) and a naive probe would fail forever
on neighbours that belong there.

⚠️ **Generated, not modelled — but not on `P3-11`'s argument.** That rationale was a proportion
family with a roster behind it, and five bespoke silhouettes have neither. The argument here is
reproducibility: a committed generator builds the models from a fresh clone, the byte-comparison
test catches "edited the generator, forgot to re-run", the proportions are parameterised from
surveyed dimensions that cite their sheets, and review happens in a diff. A modelled `.glb` would
be a binary blob whose provenance is a commit message.

⚠️ **Vertex-coloured only; "light texturing" is deferred, not refused** (user call, 2026-08-12).
The anti-goals ban textures because `merge` cannot carry them; heroes bypass `merge`, so the ban's
stated reason does not reach them — but the first texture in an untextured bundle is its own
decision, and the wing and crown carried the silhouettes without it. Hero colours obey `Q33`/`Q38`
mechanically: `make_landmark.py` self-checks its palette against the live `exposure_anchor` on the
same tolerance `_check_exposure` applies to the YAML, so an anchor change stops the generator
loudly.

⚠️ **HKCEC is Phase 2 plus the atrium link, and nothing else.** The named iB1000 block (1103124251)
covers the island and link; the Phase 1 podium south of Harbour Road is a different stem
(`B358611580502063`) carrying four separately-named towers, all still generated. **This makes
`W4`'s canonical HKCEC entry moot** — `P3-7a`'s override table was headlined by HKCEC's committed-
glazed base, and that base is no longer in any tile. `W4` shrinks; do not author an HKCEC row.

⚠️ **The excluded footprints must stay inside `bounds_game`.** Removal shrinks tile AABBs, and the
bounds would silently contract past geometry the region still contains — the hero standing where
the source stood — so `export.py` adds each `excluded_bounds` back into the union. The placed-
model check in `verify_landmarks.gd` allows 15 m of overhang for the plinth and for the rotated
massing's AABB swinging past the source's axis-aligned one (~11 m on HKCEC's 349 m at 6.4°).

**Measured.** `replaced = 2` meshes (= 2 stems; no sheet-edge duplicates), 66 tiles unchanged in
count. Heroes 3,484 + 300 triangles against 8k each — the wing is an arced shell over stations sliced from the source mesh, and the deck bridges the streets on piers authored against the road graph, because the source building is elevated over Expo Drive and Convention Avenue and a solid base would dead-end both. PCK **36.57 → 33.95 MB** — the exclusion gave
back ~2.7 MB of tile geometry and the heroes cost ~230 KB. Draw calls: 53 measured pre-`P3-6`
resident set + 2 heroes, still far under 150. A review pass culled ~1,600 dead triangles the
banding had been shipping (overtaken ribbon strips as 2 cm hairlines, buried loft caps): dead
levels now collapse to coincident rings and `loft` drops degenerate bands and takes `None` caps —
the slivers were a third of the model and sat in the Jolt collider too.

⚠️ **The photos are the arbiter, and they demanded three corrections** (user review rounds,
2026-08-12, against Expo Drive East street views; the user judged the *source mesh* closer to the
photos than the hero, and the fixes below are why). **(1) The values were inverted:** the real
Phase 2 elevation is *pale* panels carrying six-plus thin *dark* ribbon-glazing strips under a
roof *darker* than the wall; the first treatment shipped a dark glass hull with light bands under
a near-white roof. Two hero-only materials landed (`panel_pale` 42%, `roof_grey` 22%,
`Q33`-checked; `aluminium_roof` now touches only Central Plaza). A follow-up round moved the
ribbons from wall-height *fractions* to **constant absolute elevations**: fractions squeezed every
strip into a zebra fan where the east roll pinches the wall to half a metre, where the real strips
are storey lines the descending roofline cuts off one by one — each line clamps into
[floor, soffit] and a strip the roof has passed degrades to a hairline. Pitch and thickness were
then **measured off the photos by pixel profile** (six sampled columns: dark share 0.27-0.37,
9-10 bands over ~45 m of hull): 15 m + k·4.8 m, 1.5 m thick, 10 strips — the eyeballed first pass
(6 m pitch, 2.2 m strips) was both too fat and too sparse. **(2) The symmetric plan was
fat:** re-sliced at 8 m bands, the island is an eastward-leaning banana (plan centre drifting
-22 → +13 m), the prow tapers to a **14 m** half-width the symmetric model had fattened to 40, the
east flank's roof rolls to ~20 m where the west stays ~30-45, and the hull edges are their own
measurement (flush with the roof edge mid-south, 15-20 m inboard at the prow) — `WingStation`
carries all of it, and the grounded base follows the measured hull instead of a rectangle that
jutted ~60 m east of the prow. The link's top was also 10 m short (measured 61-67; was 53), and
its block is the same striped hull, not glass. **(3) Measured is not yet fair:** 1-3 m of
slice-to-slice noise reads as creases once flat facets amplify it, so every profile column is
faired with a σ = 1-band Gaussian along z (user call: the SOM seabird roof is one smooth sweep) —
the facets stay, honouring `P3-11`'s chamfer-never-smooth rule; only the noise goes. Where the
faired east roll lands within a fascia of deck level the wall pinches to 0.5 m rather than to a
zero-height quad. Derivations live in the `Hkcec` dataclass comments; the slicing itself is
scratch, per the original station authoring.

⚠️ **The under-deck is solid, not a pier field — the kerb said so** (user review, 2026-08-12).
The first shipped deck stood on bare piers, and from street level the hall read as a slab floating
on stilts over open sky. The fix inverts the default: `infill` fills the deck plan to the soffit
everywhere a *surface* carriageway does not need daylight — derived from the shipped road graph
exactly as the piers were (4 m occupancy grid, solid at `width/2 + 4.8 m` from every densified
sample, greedily merged, nothing thinner than 8 m, rim 6 m inboard so the slab still reads as a
deck), leaving the streets real portals. The bypass tunnel's samples sit at local y ≈ −7 and carve
nothing — a buried road needs no daylight — and the Lung Wo interchange (local z 93..130) stays
fully bridged, which is what the real link does. The wing stations are untouched: the curve is the
identity and the user called its preservation out explicitly. Piers the infill swallowed are
dropped at build time; the ones standing in portals stay.

**See.** `ARCHITECTURE.md` "landmarks.json" · `ART_DESIGN.md` "Hero buildings" · `Q33` · `Q38` ·
`Q42` · `Q47` · `P3-7a` `W4` · `P3-11`

---

# Standing decisions

## Foundations

**Engine: Godot 4.7, Mobile renderer, Jolt.** Chosen after the target shifted from a free web release
to a commercial store product, reversing an earlier web-first recommendation. Decisive: native mobile
performance versus Android WebView GPU throttling, and one codebase covering mobile, desktop and a web
demo.

**Language: GDScript, not C#.** Desktop C# is fully supported; Android and iOS remain **experimental**;
web export is **unsupported entirely**. Mobile is a primary target and the free web demo is the planned
marketing funnel. The complex code lives in the Python ETL anyway, so C#'s tooling advantage earns
little. The performance escape hatch is **GDExtension** (C++/Rust), not C#.

**Targets: mobile + desktop/Steam.** Adds a gamepad/keyboard input layer, resolution-independent UI, a
desktop LOD tier and a Steam build path — ~15–20% engineering overhead, accepted for the broader
revenue options.

**Region: Wan Chai → Causeway Bay.** Chosen over Tsim Sha Tsui and Central: a natural circuit exists in
the real road layout, map edges are diegetic, and it has real grade separation without Central's
multi-level data risk.

**Building source: non-textured / 3D-BIT00 Level 1, never photogrammetry.** The tile-based
photogrammetry mesh has ground gaps, level differences and vehicles baked into the geometry; a prior
public attempt concluded it suited flight rather than driving simulation. Decimating photogrammetry
produces blobs, not low-poly style. This is hard rule 1.

**Art direction: accurate city, toy vehicles.** Stylise the actors, not the stage. Recognition is the
product, so building proportions stay accurate; charm comes from Choro-Q vehicle proportions. Measured:
on the open-road frame the taxi's red is **`C*` 86.5 against a frame median of 7.5**, with the rest of
the city's 99th percentile at 39.8. An order-of-magnitude chroma gap, not a metaphor.

**Monetisation: free download + one-time unlock, deferred to launch.** Not F2P — 2–5% conversion needs
volume this TAM cannot supply, and retention mechanics would corrode a 3-minute arcade loop. Not
paid-upfront — paid games are <5% of App Store revenue, and "it feels like Hong Kong" cannot be
conveyed in a screenshot, so **a free slice *is* the marketing**. Build implication: design Wan Chai to
be standalone-playable.

**See.** `ARCHITECTURE.md` · `ART_DESIGN.md` · `GAME_DESIGN.md`

## Region bounds are WGS84, by measurement

**Claim.** The region bounds in `hong_kong.yaml` are WGS84.

**Why it is load-bearing rather than pedantic.** HK1980 versus WGS84 is a **~304 m** question in Hong
Kong, and the two readings select **different sheets** — WGS84 gives a contiguous `11-SW` block, HK1980
swaps two of six. A third of the region rode on an unstated assumption.

**Evidence.** Sheet `11-SW-10C`'s real building positions match the WGS84 projection to within metres
and the HK1980 one is out by ~250 m; the terrain node sits at the WGS84-projected sheet centre exactly.

**See.** `P0-4` · `DATA_SOURCES.md` "The datum of these bounds is load-bearing"

## Licensing

**Claim.** Code is **GPL-3.0-or-later**, hand-authored assets are CC BY-SA 4.0, and the generated city
data is **nobody's to relicense** — it stays under the government terms and is never committed.
Contributions come in **inbound MIT**. `LICENSING.md` is the standing policy.

**The licence choice decided the contribution policy.** GPLv3 cannot ship through the App Store, so
store builds need a separate proprietary grant — which works only while one party owns the whole
copyright. A single GPL-only patch would close the iOS route permanently, as it did for VLC. Inbound
MIT permits sublicensing, which is the exact property that keeps dual licensing available, at far less
friction than a signed CLA. ⚠️ **No exposure today and no retrofit once a contributor declines**, so
the file must land before the repo goes public.

**Reading the terms verbatim corrected the credits draft.** The grant is permissive — six acts,
commercial use explicit, **no usage limit, quota or volume cap of any kind**, so player count consumes
no government allowance. But the attribution requirement is **stronger than naming a source**: it
demands acknowledging *ownership of the intellectual property rights*, and **both portals** must be
named. Hard rule 6 says so.

⚠️ **One false alarm, recorded so it is not re-raised.** Neither portal's grant contains "adapt",
"modify" or "derivative", which looks alarming for a pipeline that does nothing but derive geometry. It
is expected: **"adaptation" is a term of art** attaching to literary, dramatic and musical works, and
for artistic works the restricted act is *copying* — which expressly covers 2D↔3D transformation and is
granted here as **reproduce**. The alarm came from grepping for a word rather than from the structure
of the right.

**Landmark depiction, not adaptation, is the top item for legal review.**

**See.** `LICENSING.md` · `CONTRIBUTING.md` · `DATA_SOURCES.md` "Licence"

## Genre direction

| Reference | Contributes | Landed in |
|---|---|---|
| *Crazy Taxi* | The loop — fare combo, session timer, arrow, three-minute sessions | Already the design |
| *Midtown Madness 2* | The world — real shortcuts over invented ramps, tone, drivable roster | `GAME_DESIGN.md`; the risk register |
| *Forza Horizon* | The reward layer — the losable style chain, scoreable traffic | `GAME_DESIGN.md`; `B3`/`B4` |
| *Sleeping Dogs* | The nearest commercial precedent for a recognisable HK. The common reading is that **signage density carried it, not street accuracy** — untested here | `P3-9`, the neon note |
| *Burnout 3* | Traffic as reward rather than obstacle — near miss, oncoming lane, risk-fed boost | `P3-2a` |
| *Art of Rally* | Flat-shaded untextured terrain as a **finished** look, not a placeholder | `Q18`, `P3-10` |

**Neither open-world structure survives a 1.5 km² region, and the reason is size rather than taste.**
Midtown Madness consumes map area as content; Forza Horizon uses the open world as its menu, which
needs traversal to be a pleasure rather than a formality. A checkpoint race across this region is 60–90
seconds. **The fare loop does the opposite** — it re-randomises the route through the same 1.5 km²
every session, which makes a small map an *asset*.

⚠️ **A plan-ordering bug this exposed, and it is a shape this project has seen before.** Dense traffic
converts from obstacle to opportunity only when threading it **pays**, so `B3` would have been reviewed
in the single state where traffic has no upside, and a "just annoying" verdict would have been an
artifact of the ordering. Near-miss detection split out as `P3-2a` and moved into `B3`. Same shape as
`P2-5`'s missing building collision: **a unit whose acceptance depends on a capability scheduled after
it.**

**Refused, and named so they are not revisited.** Wheelspins and randomised rewards (already an
anti-goal); live-service and always-online structure (hard rule 2); licensed-car collection as a
progression spine (the art direction is 800–2,000-triangle toys); and *Crazy Taxi*'s absurd-geometry
philosophy — ramps scattered wherever the driving goes quiet — which `P3-9` would charge for in full.

**See.** `GAME_DESIGN.md` · `PLAN.md`

## `P3-11c` — Gloss is priced per surface, and the gradient is what sells it

**Status.** 🟡 Awaiting review — shipped in `vehicle_body.gdshader`, `vehicle_body.tres`,
`scripts/vehicle/sun_glint.gd` and the `UV.y` marker `tools/make_vehicle.py` writes; graded on the
`taxi` audit frames and, for anything heading-dependent, a skidpad circle · **Owner.** `P3-11`

**The question asked.** Whether the car and some buildings could have glossy PBR surfaces, as a
modern driving game does.

**The answer, and it is a split.** The buildings already do — `city_facade_clean` ships
`glass_roughness 0.12` against `wall_roughness 0.82` with a per-pane bowed fresnel, and `Q31`'s
record already refuses SSR and planar reflections on the grounds that the cheap equivalent ships.
The car now does too — glazing, lamp lenses **and paint**, each at its own strength over a shared
sky gradient. Nothing here is refused outright; what this record establishes is a **price** for
gloss on paint, and where the dial sits.

**The probe that decided it, run before any shader existed.** The shipped car, uniform
`roughness 0.9 → 0.25`, nothing else changed, graded at both `taxi` cameras:

| surface | `t01.20` (shade) | `t04.50` (sun) |
|---|---|---|
| red bodywork | `C*` 57.47 → 53.15, hue −14.5° | `C*` **79.06 → 70.08**, hue **−7.9°** |
| dark glazing | `L*` 0.13 → 1.75, `C*` +5.50 | `L*` 0.52 → 1.69, `C*` +3.77 |

🔴 **The paint row is the finding.** With no SSR and no probes on the Mobile renderer a specular
lobe samples flat ambient, so what gloss adds to a panel is a *wash of sky*, not a reflection —
`L*` **rises** while `C*` **falls**, which is `Q27`'s albedo-independent light arriving on the one
object the direction says carries the frame's colour (`C*` 86.5 against a frame median of 7.5).

⚠️ **This record first concluded that nine points "is not affordable", and that was wrong — twice
over.** It is corrected below rather than edited away, because the reasoning failed in a way worth
keeping. First, the price is real but the property it threatens is not: at `C*` 71.63 the taxi is
still **9× the frame median** and clear of the city's 99th percentile of 39.8, so "the only
chromatic object in the frame" survives the whole cost. A large margin got smaller; nothing
inverted. Second, "no tuning recovers it" mistook one *instrument* for the mechanism — see the
clearcoat section. The measurement was sound; the verdict drawn from it was not.

✅ **The glazing row is worth having, and `ART_DESIGN.md` already authorised it** — "flat dark
colour with a fixed specular hint, no reflection probes".

**Why a shader rather than a material.** ⚠️ **A `StandardMaterial3D` carries one roughness for a
whole surface, and the body is one merged primitive holding seven colours** — verified from the
imported asset, `surface 0` and no other. So the two rows above cannot be bought separately without
a shader, and "set roughness on the body material" is not a cheaper version of this change; it is
the paint row.

**Shipped result**, same cameras, against the pre-shader build:

| surface | `t01.20` (shade) | `t04.50` (sun) |
|---|---|---|
| red paint | `L*` +1.18, `C*` −3.48 | `L*` +0.70, `C*` **79.06 → 71.63** |
| silver trim | `L*` +0.23, `C*` −0.31 | `L*` +0.06, `C*` **10.00 → 7.59** |
| dark glazing | `L*` 0.13 → 9.51, sd **0.05 → 6.35** | `L*` 0.52 → 9.28, sd **1.25 → 7.69** |

**0 pixels moved outside the car** at either camera — the whole change is contained to the taxi.
⚠️ An intermediate build held paint at `C* −0.62` by leaving it matte; that is the `paint_reflect 0`
end of the dial below, not a superseded measurement.

**The payload.** `UV.y` carries a surface marker, `floor()`-read, the same shape the tiles use;
`UV.x` is reserved and zero — ⚠️ **`P3-11d` spent it**, on the switched lamp circuit. Markers are
`PAINT` / `GLASS` / `LAMP` / `TRIM`. ⚠️ **`TRIM` is carried but
takes no branch of its own** — it shares paint's clearcoat, because silver is a near-neutral with
the least hue of its own to defend and is the surface a sky wash disfigures first. Keeping it
separable costs nothing now and is what a later brightwork treatment would need; the tiles reserved
their ground marker on the same reasoning. ⚠️ **Not `COLOR_0.a`**, per `ARCHITECTURE.md`.

⚠️ **Colour is not materiality, and the first pass got this wrong.** Marking by swatch alone handed
a lens's gloss to the **registration plates and the roof sign**, because `LAMP` and `AMBER` are also
those parts — the same collision `Q43` records under two predicates wearing one name. `GLASS` and
`SILVER` name one material each and stay colour rules; every lens is marked by part name.

✅ **The ice-blue roof is fixed, and half of it was never a lighting problem.** `ART_DESIGN.md`
diagnosed the silver roof as a near-neutral taking its hue from ambient. It is — but measured,
`SILVER` was itself authored blue at **`b* −3.56`**, so no lighting change could have reached it.
Now `(168,172,178) → (175,171,166)`: `b* −3.56 → +3.07` with `L*` held at 70.21 → **70.17**, one
axis moved and the value headroom the original comment exists to protect untouched. Fixed at the
colour rather than in the shader **because `SILVER` is also the wheel hubs**, which are on the tyre
mesh and get no shader — a shader-only fix would have split the trim across two meshes.

🔴 **The red tail lens is *not* fixed, and this round should not be read as having fixed it.**
Marked as a lens and given the lens roughness, it separates only where light actually falls on it;
at both audit cameras the rear face takes none and the cluster still reads amber-over-white with a
bump. Lamp pixels moved `L*` **+0.77** in shade and **+0.41** in sun — real, and not enough. The two
fixes that would work are both closed: recolouring the lens is the earlier bug and a white tail lamp
besides, and the bezel behind the cluster **was removed on request with the trade understood**.
Faking that bezel in the shader is the same reversal wearing a different hat, so it was not done.
This needs a decision, not another round of tuning. ✅ **`P3-11d` is that decision** — the lens is
wired to a brake circuit and lights, which recolours nothing and puts nothing behind the cluster.

## The reflection needed a gradient, and strength was never the variable

⚠️ **`glass_reflect` went 0.34 → 0.14 → 0.45, and the middle value is the one worth understanding.**
At 0.34 against a single flat `sky_reflection` colour the backlight came back at `C*` 21 and read as
a panel painted blue, so it was cut to 0.14 — which the user then judged from the driver's seat as
barely different, correctly. **Both readings were right and neither was about strength.** A flat
colour is a swatch at *every* value: faint at 0.14, painted-on at 0.34.

`ART_DESIGN.md` had already recorded this exact failure against the facades — *"a single reflection
colour is why glass read as a swatch rather than a mirror"* — and the fix transfers whole: reflect
the view ray and let its own elevation choose between `sky_zenith`, `sky_horizon` and
`ground_reflection`. Measured on the glazing, `L*` spread went **sd 0.05 → 6.35** at `t01.20`
(range 0.1–0.3 → 0.2–22.2) and **1.25 → 7.69** at `t04.50`. That is structure, and it is what the
mean figures could not see: the flat 0.34 build and the gradient build have *similar means* and look
nothing alike.

⚠️ **This record first claimed the car "sweeps the gradient continuously" as it turns. That is
wrong, and the correction is the more useful fact.** `bounced.y` selects the band, and `y` is
**invariant under yaw** — steering rotates the view ray and the surface normal about the vertical
axis together, so a flat corner moves nothing. What tilts the normal out of plane is **roll and
pitch**: cornering lean, acceleration squat, braking dive, kerbs. Measured on a skidpad circle at
fixed lighting and fixed camera-relative pose, the glazing moves `L*` **23.85 → 27.87** across
headings — genuinely responsive to driving, by about four points, and through the suspension rather
than the steering. 💡 **A yaw-responsive term would have to be something the sky gradient is not:
rotationally asymmetric about the vertical.** A sun-glint on `dot(bounced, sun)` is the cheap
candidate and is not built.

## The clearcoat, and the correction it forced

**The user asked for the body to look "glossy like just waxed new cars".** The probe above had been
read as refusing that. It does not: it refuses a **uniform** gloss, and a waxed panel is not uniform
— it picks up sky at its shoulders and dark ground below its beltline, concentrated where the
surface turns away from the eye. So paint takes the same gradient at low strength through a
near-zero `paint_face_on`, leaving a panel square to the camera with its colour untouched.

🔴 **The hypothesis that this would be nearly free was wrong, and isolating the knobs is what showed
it.** Both cost, and roughly additively:

| `paint_reflect` | `paint_roughness` | red `C*` at `t04.50` | cost |
|---|---|---|---|
| — | 0.9 | 79.06 | — |
| 0.12 | 0.9 | 73.65 | −5.42 |
| 0.12 | 0.55 | **69.86** | **−9.20** |
| uniform probe | 0.25 | 70.08 | −8.98 |

⚠️ **All four rows are at `fresnel_power` 4.0**, which is no longer what ships — see the refund
below. The *shape* of the table is what survives: gloss on paint is priced, not refused, and the
price is roughly linear in how much is asked for. The dial is `paint_reflect` / `paint_roughness`
in the `.tres`, with `0.12 / 0.9` the half-price middle and `0 / 0.9` the matte car this task
started from — no rebuild, one file.

## Fresnel is not decoration here, and tightening it refunds a fifth of the price

**Asked whether the taxi could "have some fresnel", the answer was that it already does** — every
surface class has carried `pow(1 - dot(NORMAL, VIEW), fresnel_power)` since this shader existed.
What was not known is how much work it does.

🔴 **Ablated — `fresnel` forced to 1.0, so the reflection lands at every angle — the paint loses a
*further* `C*` 13.75** (69.86 → 56.11 at `t04.50`, `L*` rising 43.88 → 46.81). So the fresnel term
is the whole reason the clearcoat is affordable: it is what keeps the reflection off a panel facing
the camera, and `paint_face_on` 0.06 is the knob that says so. Without it there is no priced trade,
only a wash.

✅ **And it was under-tightened. `fresnel_power` 4.0 → 6.5 gives back `C*` +1.77** (69.86 → 71.63 in
sun, 53.62 → 54.00 in shade) and takes the hue rotation from −7.4° to −6.3°, for a glazing cost of
**−0.06 `L*`** — the shipped price falls **−9.20 → −7.43**, a 19% refund. A tighter fresnel
concentrates the sheen nearer the edges, which is both cheaper *and* closer to what "a fresnel
effect" is usually asking for.

⚠️ **A rim light was evaluated at the same time and held, not refused.** No rule blocks it and it is
cheap, but nothing measures a problem it solves: silhouette legibility has never been flagged, and
the car already sits at `C*` 86.5 against a frame median of 7.5. It also spends the `P3-9a`
recognition budget through `Q27`'s additive-light mechanism. 💡 The frame that would justify it is
**night** — "one directional light is the look" is a daylight argument, and `Q26`'s unchosen night
rig has no sun to shape the car at all.

⚠️ **The residual risk is `P3-9a`, and it is a recognition risk rather than an art one.** The red is
an identifying feature of 紅的, the gate is ≥3 Hong Kong drivers, and washing it toward pink is
exactly the axis that gate measures. If recognition scores poorly, this dial is the first thing to
try before anything structural.

**No contract bump.** `schema_version` covers the ETL→game city artefacts; the taxi is a committed
authored asset and its vertex format is not versioned. Triangles unchanged at 592, one draw call,
one material.

**No verify tool covers vehicles**, and every failure here is silent — a missing material name
leaves the body on its `BaseMaterial3D` and the car renders exactly as before. `TestSurfaceMarkers`
in `test_make_vehicle.py` is what holds the ETL end; the engine end is held by a render and nothing
else.

**See.** `ART_DESIGN.md` "Vehicles" and anti-goals · `ARCHITECTURE.md` tile contract · `Q27` ·
`Q31` · `Q43` · `P3-11`

## The sun glint, and why `SPECULAR` could not be it

**The gradient is yaw-blind by construction** (see the correction above), so a highlight that
responds to *steering* has to come from something rotationally asymmetric about the vertical. The
sun is the only such thing in the scene.

🔥 **`SPECULAR` was tried first and refused with a measurement.** Raising it 0.5 → 0.9 lifted the
glazing's mean `L*` by 5.8 while its p99 spread across headings moved only 2.69 → 3.54 — a uniform
wash, not a moving hotspot — and the glass went back to reading as a panel painted blue. The cause
is the one behind everything else in this task: **`SPECULAR` scales ambient specular as well as the
sun's**, and with no probes the ambient half dominates. It also cost the paint a further `C*` −3.08
(−9.20 → −12.28) for no glint. Reverted to Godot's default.

**Shipped instead: `pow(dot(bounced, -sun_direction), sharpness)`, isolated from the sun alone.**
⚠️ **`sun_direction` is fed by `sun_glint.gd` from the scene's real `DirectionalLight3D`**, never
authored in the `.tres`. A typed-in vector would be a second copy of the rig's rotation and would
drift silently the first time the sun is retuned or `Q26`'s night mode adds a second rig — the
desync shape `P3-11`'s chassis guard exists for, and nothing here would catch it.

**Measured on the skidpad**, mask fixed from the no-glint frame:

| heading | glazing `L*` | peak pixel |
|---|---|---|
| `t04.00` | +2.48 | +23.69 |
| `t06.00` | **+0.01** | +27.40 |
| `t08.00` | **+6.03** | — |

Absent at one heading and strong at another, which is what distinguishes a glint from a wash. The
audit cameras are unmoved — paint `C*` −9.20 exactly as before at the then-shipped `fresnel_power`
4.0, glazing +0.28 — so this costs
nothing where the look was already graded, and fires where it was not.

🔴 **The placement does not scale past one vehicle, and this is a note for whoever builds traffic.**
`SunGlint` hangs off `taxi.tscn` and pushes into the material exported on that node. With one car
that is correct and cheap — one tree walk, one write, at `_ready()`. But the roster is six vehicles
(`ART_DESIGN.md`), `P3-11`'s generator exists to build the rest of them, and `scripts/traffic/` is
still an empty stub. Copy this node onto N vehicles and you get N recursive `find_children` walks
finding the same sun and N writes of the same vector into the same **shared** `.tres` — idempotent,
so not a bug, but pure waste and an invitation to diverge. ⚠️ **The right shape at that point is a
Godot global shader parameter** (`uniform vec3 sun_direction : global;`), set once from the world
scene that owns the sun, which removes the per-vehicle material coupling entirely. Not done now
because it needs a `[shader_globals]` block in `project.godot` — a file with its own documented
hazard — for a saving of zero on a one-car scene. **Do it before the second vehicle, not after.**

⚠️ **On flat geometry a glint is per-facet, not a moving spot.** Every fragment of a pane shares one
normal, so the whole screen lifts at once and the effect reads as a pane *flashing* as the car
turns rather than as a highlight sliding across it. At `glint_strength 1.1` that flash blew the
backlight to near-white; 0.4 with `sharpness 24` makes it a lift. Real glass at distance does flash,
so this is a property to tune rather than a defect — but it is why the strength that looks right on
a curved reference car is far too high here.

🔴 **A guard added to silence a warning disabled the feature in every measurement, and that is the
lesson worth keeping.** `sun_glint.gd` first returned early when `get_tree().current_scene` was
null, to stop a `push_warning` firing on every `tools/check.sh` run. But `driver.gd` instantiates
the scene and `add_child`s it — **nothing sets `current_scene`**, which only `change_scene_to_*` and
the boot path assign. So the glint silently kept its default direction through two rounds of
tuning, and the result read as "the term does nothing" rather than "the term never ran". It is
found by searching from `get_tree().root`, which is populated on every load path. ⚠️ The tell was
that the numbers came back *byte-identical* to the no-glint baseline; a term that is running but
mistuned does not reproduce a baseline to two decimals.

⚠️ **One measurement artefact, recorded because it inverted a sign.** The first read of the glint
showed a heading getting *darker*, which is impossible for a purely additive term. The mask was
`L* ∈ (10, 50)` recomputed per frame, so brightening pushed pixels out of the sample. Masks come
from the baseline frame and are applied to both.

## `P3-11d` — The lamps switch, and that is what finally separates the red lens

**Status.** 🟡 Awaiting review — shipped in `tools/make_vehicle.py` (`UV.x` circuits, `DEEP_RED`,
`_high_brake_lamp`), `vehicle_body.gdshader`, `vehicle_body.tres`, `scripts/vehicle/vehicle_lamps.gd`
and `scripts/vehicle/vehicle_controller.gd`; graded on paired driver frames at `t03.30` ·
**Owner.** `P3-11`

**The question asked.** Brake lamps that light under braking, reverse lamps under reverse, and
indicators that blink on the side the car is turning.

**It closes `P3-11c`'s one open 🔴.** That round left the red tail lens unfixed and said so in
terms: it is `RED` on `RED` bodywork with no bezel, shading alone moved it `L*` +0.77 in shade and
+0.41 in sun — "real, and not enough" — and **both obvious fixes were closed**, recolouring the lens
being the earlier bug and faking the removed bezel being that reversal wearing a different hat. It
asked for a decision rather than another round of tuning. This is the decision: a lens that
**lights** separates itself, it recolours nothing, and it puts nothing back behind the cluster.
⚠️ The lens is still invisible when the car is coasting, and that is now correct rather than a
defect — an unlit brake lamp is supposed to disappear.

**The payload is `UV.x`, which `P3-11c` reserved and left at zero.** `floor(UV.x)` is the switched
circuit: `NONE` / `BRAKE` / `REVERSE` / `INDICATOR_L` / `INDICATOR_R`. ⚠️ **A second channel rather
than four more `UV.y` markers**, because the two questions are independent — a lit lens still wants
the lens roughness and the lens reflection, and folding the wiring into the marker would make the
shading branch enumerate it. Left and right are **separate** circuits: one amber circuit is a hazard
warning, not a turn, and a swapped pair signals the opposite of where the car is going. Neither
failure reads as a bug in a screenshot, so both are held in
`test_the_indicators_are_split_left_from_right`.

**Names are the wiring, and a rename is a rewiring.** `LAMP_CIRCUITS` is keyed on full part names —
the tail cluster is one prefix and three circuits — and the tail lenses were renamed from `_0/_1/_2`
to `_indicator` / `_reverse` / `_brake` so the stacking order and the wiring are one list.
⚠️ `_check_wiring` raises in the *generator* rather than in a test, because `CIRCUIT_NONE` is a
valid value meaning "never lights": a lens that loses its key ships a well-formed file, imports
clean, renders, and is simply dark for ever.

**⚠️ The circuits are `instance uniform`, and that is not an optimisation.** `vehicle_body.tres` is
one shared resource — `generated_scene_import.gd` hands the same material to every mesh that asks
for `vehicle_body` by name — so a plain `set_shader_parameter` would put the whole roster on one
brake pedal, and `ART_DESIGN.md` schedules an AI red taxi on this body. `sun_toward` stays a plain
uniform for the mirror-image reason: there is one sun and every car agrees where it is. For the same
reason `vehicle_lamps.gd` reads the *car* and never `InputRouter` — reading the player's input works
exactly once, and then every AI taxi indicates whenever the player turns.

**One pedal, two lamps, and one statement of the rule.** `brake_reverse` means braking above
`STATIONARY_KPH` and reverse below it, which is a rule and not an input. `VehicleController` now
publishes `is_braking()` / `is_reversing()` and `_longitudinal_force()` reads them, so the lamp is
lit exactly when the brakes are applied. ⚠️ At a standstill with the pedal held the **reverse** lamps
light, not the brake lamps — reverse is what the pedal is asking for.

**The high-level brake lamp, and the shader change it forced.** Asked for as "only visible when the
brake light is on", which is a harder specification than it sounds: the emission was
`albedo × lamp_emission`, so "invisible when off" and "bright when on" were the same dial pulled in
opposite directions. Fixed by **normalising the hue and discarding the level** — an unlit lens is
dark because of its reflector, not because it is a weaker bulb — which let the strip be authored at
`DEEP_RED (58, 10, 12)` and burn at the same intensity as every other lens. ⚠️ **An eighth palette
colour**, on a table that says 3–5 and a count `ART_DESIGN.md` already calls the standing exception;
granted because its *darkness* is the feature and `RED` would be a bright bar across a black window
every time the car coasts. ⚠️ "Inside the window" is a **look, not a coordinate** — the glazing is
opaque, so a lamp behind it is never drawn; it is seated `FIXTURE_PROUD_M` clear of the backlight,
against the 30° rake, exactly as `_seated_depth` seats the tail lamps against the nose profile.

**⚠️ `lamp_emission` buys bloom and spends redness, and by 1.2 it is spending nothing else.** The
tonemap is ACES, which desaturates a clipped channel toward white, and the lens's red channel is at
255 from 1.2 upward — so every further unit lands on green and blue. Measured on the strip, the same
294 px, braking at `t03.30`:

| `lamp_emission` | `L*` | `C*` | mean sRGB |
|---|---|---|---|
| 0.0 (ablated) | 2.29 | 9.35 | (16, 4, 15) |
| 1.2 | 67.04 | 56.44 | (255, 123, 120) |
| **1.6 shipped** | **72.72** | **44.34** | (255, 149, 142) |
| 2.3 | 79.17 | 31.81 | (255, 176, 170) |

`L* 2.29 → 72.72` is the whole feature: the lens is black when the circuit is out. 1.6 is the knee —
over the 1.0 glow threshold by enough to carry a halo, still `C*` 44 at the core. **2.3 is a white
lamp with a red glow round it**, which is the failure this document has refused twice already.

**Indicators need a hold as well as a threshold, and the threshold cannot do it alone.** One says
how hard a turn is, the other how long it lasts, and an arcade car crosses hard lock constantly — a
flick round a parked lorry, a correction out of a drift, a lane change. Without `steer_hold_s` the
tail strobes amber through all of them, which is worse than no indicator: it stops meaning
"turning". Held at **0.5 s**, on a threshold of 0.35 of the lock available *at that speed* — a
fraction rather than an angle, because full lock at 140 km/h is a quarter of full lock parked.
⚠️ Swapping sides restarts the hold; one lock straight to the other is two turns, not one long one.
The cost is that the lamp is late by half a second, which is the honest thing for it to be: this is
a read-out of what the car is doing, not a signal of intent.

**What is deliberately not wired.** Headlamps and fog lamps ship `CIRCUIT_NONE` — lenses that catch
the sun and never light. There is one lighting rig and it is daytime, so there is nothing for a
headlamp to switch on *for*; `Q26`'s night mode is what would wire them, and the channel is already
there for it.

⚠️ **Superseded by `P3-11e`, and the reasoning above is why rather than how it was wrong.** Both
pairs now switch. What changed is not the rig but the premise: the switch turned out not to need a
night rig at all, because *where the car is standing* — under a deck, in a tower's shade — is a
question this daytime rig answers all day. The channel this entry reserved is the one that paid for
it, and the out-of-range guard it shipped "against a fifth circuit" is what made widening safe.

**See.** `P3-11` · `P3-11c` · `P3-11e` · `Q26` · `Q27` · `ART_DESIGN.md` "Vehicles"

## `P3-11e` — The front lamps answer to the light, not to the driver

**Claim.** The small bumper lamps light when the car is in shade; the main beams light when the sky
overhead is shut out, or when the rig is a night one. Both circuits were `CIRCUIT_NONE` until now.

**This reverses nothing — it supplies the premise `P3-11d` said was missing.** That entry left the
head and fog lamps unwired with a reason rather than an omission: *"there is one lighting rig and it
is daytime, so there is nothing for a headlamp to switch on for"*. Asked for by the user, the switch
is no longer the rig — it is **where the car is standing**, which the daytime rig supplies plenty
of. The channel `P3-11d` said was "already there for it" is the one this spends.

**⚠️ Two of the three asked-for triggers have no shipped content to fire on, and are wired anyway.**

- **Tunnel.** `Q21` records level −1 as 15 edges *"ribboned under the terrain where nothing can see
  it and nobody can drive it"*, and `road_graph.gd`'s `is_drivable` admits level 0 only. So the
  trigger is implemented as **"the sky directly overhead is blocked"**, which is the same question a
  tunnel asks and one the region can actually answer — proven under the HKCEC deck, where the car
  spawns. A roofed tunnel would trip the identical probe.
- **Night.** `Q26`'s rig does not exist and this document records night as *a switch between two
  static rigs*. `read_rig` therefore reads the **scene's real `DirectionalLight3D`** — key-light
  energy at or below `night_energy`, or a sun at/below the horizon — for the same reason
  `sun_glint.gd` reads it: a rig fact copied into a second place drifts the first time the rig
  changes, and nothing reports it. ⚠️ **A night rig must dim or drop its key light, not delete it.**
  A missing sun is read as "no rig", not as night, deliberately: a verify tool or an import loads
  the taxi with no world around it, and calling that night puts every headless render of the car on
  main beam — visible in exactly one place, a graded frame.

**Two lens pairs, not one lens at two levels.** The alternative was a single headlamp circuit driven
at a fraction for "small". It fails on the shader's own arithmetic: `lamp_emission` is 1.6 against
`clean_daylight.tres`'s 1.0 glow threshold, so a lens at a fraction of that carries **no bloom**,
and `P3-11d` measured bloom as *"the whole difference at the distance a chase camera holds"*. It
also reads wrong — a dim main beam is a weak headlamp, not a different lamp. `taxi_body` already
builds *"a small white lamp low in the bumper"* per side, so the pair exists. ⚠️ It is named
`foglamp_*`, for where it sits rather than what it now does.

**⚠️ The side lamps stay lit under the main beams.** Handing over rather than stacking makes the two
states a different pair of lamps at the same count, which reads as a flicker; stacked, the nose
visibly gains a lamp — and it is what a car does.

**⚠️ A lit lens and a thrown beam are two features, and shipping only the first looked finished.**
The emissive lenses were graded from *behind* the car, where they are the whole picture. From ahead
they light nothing: under the HKCEC deck the taxi drove with blazing lamps over a **black road**,
which the user caught on a chase-camera frame. So `taxi.tscn` now carries a `SpotLight3D` that
`vehicle_lamps.gd` switches on the same ladder — full on `DARK`, `sidelamp_beam` (0.3) of the energy
*and of the reach* on `SHADOW`, hidden on `SUN`. Scaling reach with brightness matters: a dim lamp
that still reaches 40 m lights a far kerb it could never touch, which reads as the road brightening
by itself rather than as the car lighting it.

**One spot, not one per lamp.** Two cones from 1.2 m apart merge into a single pool within a couple
of metres, so the second light buys a light and no picture. ⚠️ **`spot_angle` is Godot's *half*
angle, and that is the trap in this node** — the first version authored 34, which is a 68° flood
from a lamp 0.3 m off the ground: most of the cone pointed at the sky and the rest landed under the
bumper, reading as a puddle round the car rather than a beam. 24° with the lamp at bumper height is
a beam. `spot_attenuation` sits at 0.45 rather than Godot's 1.0 because the default dies within a
few metres of a 55 m light, which makes the range dial look broken.

⚠️ **Shadows off, and that is the tier's rule rather than a saving** — `ART_DESIGN.md` grants the
mobile tier vehicle blob shadows and no realtime shadow maps. It is also why the light is free:
A/B'd on the same seeded run, `prims` and `draws` are **bit-identical** with the beam and without
it. Hidden rather than dimmed to zero when off, because a zero-energy light is still a light the
renderer gathers and loops over per object — and "off" is most cars, most of the time.

**`lamp_lit` was full, so there are two vectors now.** Circuits 5–8 live in `lamp_front`, and ⚠️ the
**ordering is the contract, not the declaration** — a channel inserted ahead of the others silently
moves every lens behind it across the seam. The bounds guard `P3-11d` shipped "against a fifth
circuit the generator could add" is what made this safe, and it now bounds at `CIRCUIT_COUNT`.
⚠️ Both vectors are indexed with the **same masked slot**: a ternary is specified to evaluate one
operand, but Mobile drivers flatten branches, and a flattened `channel - 4` at `channel = 0` is the
negative index the guard exists to stop, arriving through the fix for it.

**Cover is tested before shadow, and the order is the answer.** Under a deck both probes hit, so
asking about shadow first puts a car in an underpass on side lamps and never reaches the main beams.

**⚠️ The hold restarts when a reading crosses the committed state, never merely when it changes —
and this shipped wrong first.** Zeroing the timer on every change reads like a stricter hold and is
actually a **stall**: two readings that disagree with each other but agree about the *direction* are
both evidence for the same move, so they cancel each other for ever. It fails on the exact case the
hold is for. Committed to `DARK` under the deck, then out into a street alternating `SUN`/`SHADOW`
about once a second, the timer never reaches 1.6 s and **the main beams stay on for the whole
drive** — the failure the hold was built to prevent, arriving through the hold itself. A canyon
flickering `DARK`/`SHADOW` stalls the mirror image, with no front lamp lighting at all. Caught in
review, not by a check: every frame renders, the car drives, and nothing exits non-zero.

**⚠️ The holds are asymmetric, and that is the whole anti-flicker mechanism.** 0.35 s to come on,
**1.6 s** to go out. A Wan Chai street is a picket fence of shadow — kerbside towers, gantries,
footbridges — and a car at 50 km/h crosses one a second; symmetric holds strobe the lamps through
all of it, which is the failure this document already records for the indicators. Being late *into*
a dark place is the one a driver notices, so only that side is short.

**⚠️ The sun probe is bounded by where collision exists, not by where shadow does.** Only the finest
tile tier ships a collider (`city_streamer.gd`) and `streaming.tres` puts that band at 250 m, so a
longer ray passes through the coarse tiles beyond as if they were air. 200 m keeps the probe inside
the band. It is **not enough for every caster**: `golden_hour.tscn`'s sun sits at 30°, where a
shadow runs 1.73× the caster's height, so a building **taller than about 115 m** throws its far
shadow past the end of the ray and that shadow reads as sunlit. Raising the ray past the collider
band cannot fix that and would only look as though it had.

**Cost, and why it is sampled.** Everything else in `vehicle_lamps.gd` reads a value the controller
*wrote* that tick; these two probes **ask the physics world**, per car, and `ART_DESIGN.md`'s roster
multiplies that. Sampled at 10 Hz, which is all the holds can use — 60 Hz re-derives the same answer
59 times inside the shortest one.

Measured on the built region, 65 tier-0 tiles resident, Forward Mobile: cover ray **0.49 µs**, sun
ray **0.91 µs**, against **0.50 µs** for one of the four wheel rays the controller already casts
*every* tick. A probe is three wheel rays, twenty times a second.

⚠️ **Guarding the `set_instance_shader_parameter` writes was proposed and refused on the
measurement.** The call is a queued RenderingServer command against a CPU-side per-instance value —
no GPU round-trip — at **33 ns** unchanged and **50 ns** changed. Both writes per car per tick come
to ~80 ns, so a twenty-car roster spends 1.6 µs a frame; a change-guard would save ~40 ns a skipped
write and cost two cached `Vector4` fields and two comparisons. The pre-existing `lamp_lit` write
stays unguarded for the same reason. ⚠️ **`probe_hz` assigned rather than accumulated ran at 8.58 Hz,
not 10** — `0.1` is not a whole number of 60 Hz ticks, so discarding the overshoot quantised the
period up by a tick. Fixed by carrying the remainder.

⚠️ **The roster will probe in lockstep, and the obvious fix is refused.** `_probe_due_s` starts at
zero on every instance — ~28 µs on one tick at twenty cars against 1.4 µs amortised. A random
starting phase buys ~1% of a frame on the device floor and costs **byte-deterministic driver runs**,
which is how this project grades frames at all. Stagger from something stable if it ever matters.

**Evidence.** Under the HKCEC deck the lit lens clips **L\* 100.00** against a **38.74** mean for
the cluster box; the same lenses parked in open sun **peak 96.71** and never clip. Zero
`SHADER ERROR` lines in the drive log, which is the only reliable test that a `.gdshader` compiled.
`taxi_body.glb` is unchanged in size and triangle count — 47,608 bytes, 604 triangles — because only
`UV.x` moved. ⚠️ Not an ablation: a stationary before/after was attempted and abandoned, since the
streamer is still instancing tiles across the hold window and 41% of the frame changes with it.

**See.** `P3-11d` · `P3-11c` · `Q21` · `Q26` · `ART_DESIGN.md` "Vehicles"

## Two shadow cascades at 400 m, not four at 600

**Claim.** `directional_shadow_mode` is 2 PSSM cascades at 400 m.

**Why 400 m.** It is exactly the chase camera's far plane and the streamer's unload, so shadow reach
and draw distance end together. Distance is free either way — 150, 250, 400 and 600 measure
**bit-identically** for a given cascade count.

**Evidence.** Frame primitives against Godot's four-cascade default: **−35%** at two cascades, −55% at
one.

⚠️ **One cascade is what the spec asked for, was shipped first, and had to be withdrawn.** It has a
distinct artefact at every distance: at 150 m shadows fade out mid-street while the camera draws to
400 m; at 250 m the HKCEC shadow comes out **banded**; at 400 m it **disappears**, the caster falling
outside the ortho volume's near plane. The first two are one artefact, not two —
`directional_shadow_fade_start` is a *fraction* of `max_distance`, so shortening the distance to
sharpen the near field silently drags the fade band in with it. The two expected artefacts were checked
on a near-field crop and nobody looked down a long street.

⚠️ **"35% off the frame" is a primitive count, not a frame time.** Every configuration pinned to 8.3 ms
on this machine, so the GPU saving is **unmeasured**, and shadow-map fill is unchanged since the atlas
is one texture at any cascade count. Justified as headroom for the unbuilt mobile tier and as spec
conformance, not as a measured speed-up. Cascade count also costs draw calls in the opposite direction:
4 → 32, 2 → 35, 1 → 39, off → 26.

**No `LightingProfile` resource, deliberately.** A `.tscn` *is* data — `city_drive.tscn` already carries
`far = 400.0` the same way. A profile plus an apply script would move values out of a scene the editor
renders correctly and into a script that writes them in `_ready()`: two sources of truth whose
disagreement would be invisible in the editor.

⚠️ **`ART_DESIGN.md`'s "vehicle blob shadow only" line needs re-examination before anyone builds
the mobile tier**, and that section carries the evidence. `P2-6` inherits it.

**See.** `ART_DESIGN.md` "Lighting" · `Q31`

## Debug chrome: one owner, one key, off by default

**Claim.** `DebugHud` is an autoload owning every dev readout. `F3` cycles `off → minimal → full`;
`--debug-view=` sets where a run starts. **The default is off in every build.**

**Why off.** Every screenshot anyone judged Wan Chai from had a five-line text block over it. And
measured on the standard driver run: **19 draw calls off, 27 at minimal, 38 at full** — debug text was
costing half as many draw calls as the entire city, because text with an outline does not batch the way
a flat-shaded mesh does.

**`drive.sh` defaults to `minimal`**, which is the one place the reasoning inverts: a scripted run is
somebody debugging, and a screenshot that cannot say where it was taken cannot be acted on. The
position block reports engine metres **and** the EPSG:2326 grid reference, so a suspicious frame is
checkable against the ETL's own source data.

⚠️ **The toggle is a raw key, not an action** — `[input]` is the *shipped* map, so `drive.sh --hold=`
cannot press it and the flag is the only route a scripted run has. **Headless parks the HUD whatever
the flag says.**

**Font sizes are constants rather than a `.tres`, and that is a deliberate reading of hard rule 4:**
tuning values are *gameplay* values, balanced by someone who should not need a code change. Nothing
about dev chrome is balanced.

**See.** `ARCHITECTURE.md` "The debug overlay"

## The vertex stream carries both ground and building colour

**Claim.** Colour rides `COLOR_0` on an untextured mesh that merges to one primitive per tile. That
single choice is what produces 53 draw calls and the bundle the project ships. Ground colour and
building colour are the same question — *what channel carries colour* — and the project had already
answered it.

**Rejected: ship the terrain orthophoto, resampled.** ~5.9 MB as ASTC, affordable in isolation. It
fails on two other counts: a textured surface cannot merge with the vertex-coloured building
primitive, so it costs **+1 draw call per resident tile**; and an orthophoto has the *real* roads baked
in at their real width while the generated ribbon sits coplanar and **1.6× wider**, so photographic
asphalt and lane markings would show from under a wider synthetic road, along with parked cars and
baked shadows. ⚠️ **High-passing to remove the shadows makes the misregistration worse**, because road
edges *are* the high frequencies.

**Chosen: the texture is read at build time and thrown away.** ⚠️ Note the ordering that followed —
flat colour first, look at it, and only then decide whether classification is earned. The classifier
was subsequently **refused** on resolution grounds (`Q18`), so what ships is flat colour plus
`facade_hue`'s per-building measurement.

⚠️ **Use `TEXCOORD_0`, not `COLOR_0.a`.** `generated_scene_import.gd` sets `vertex_color_use_as_albedo`
project-wide. An opaque material ignores albedo alpha only until somebody enables transparency on a
tile, after which the city renders see-through with no error.

**See.** `Q18` · `Q27` · `P3-7` · `P3-10`

## The audit viewpoints

**Claim.** Seven fixed cameras cover every mesh class the pipeline ships, recorded in `ART_DESIGN.md`
so a later change is graded **against these** rather than against a fresh camera. Shots live under
`build/driver/art_*`.

**Why a fixed set.** Every class had been fixed individually and none had been graded against the
others. A fresh camera per change makes two changes incomparable.

⚠️ **A gap in coverage is cheaper to find than a defect in a render, and it does not depend on reading
a frame correctly.** `ART_DESIGN.md` had **no infrastructure section at all**, for a class with its own
colour, its own LOD cell sizes and its own grader — found by asking which classes the document covers,
not by looking at a frame. Worth repeating for the other classes.

**See.** `ART_DESIGN.md` "The audit viewpoints" · `Q30` · `Q31` · `Q32`

## Rendering proposals: eight evaluated, two survive

**What survives, in the order it should be done.**

1. 🟢 **`Q31`'s bounce-fill pass — first, and it costs nothing.** *Mirror's Edge*'s radiosity is the
   observation that **shadow needs its own light**, which is exactly `Q31`'s last untried lever.
   `ambient_light_color` and `ambient_light_energy`, one variable at a time, graded with
   `tools/frame_stats.py`. No rebuild.
2. 🟡 **A precomputed sky-visibility bake — only if 1 fails, and probe before building.** It is the
   only occlusion the **mobile tier** can have, since it ships no realtime shadow maps, and it breaks a
   tie `ART_DESIGN.md` records as unbreakable: raising the fill *"fixes the road and flattens the
   massing at once"*, true only while ambient is uniform. Inputs already exist — `terrain.py` parses a
   real height field and buildings are extruded footprints, so the bake is numpy with no new dependency.
   ⚠️ **Tint-probe it first** with an analytic term off the existing `TEXCOORD_0.x`; `Q32` built,
   measured and reverted a whole shader term for want of that step. 💡 It has a **second consumer** for
   free: `Q39`.
3. 🟡 **`WATERBODY`, 605 triangles — tint-probe it, do not ship it on the strength of the number.**
   Most of it is on the hillside `Q36` measured at 0.000% of every viewpoint.

**Refused with a measurement, recorded so they are not re-proposed.**

- **Real-time GI (Enlighten).** The premise is absent: *Catalyst* moved off baked lighting because its
  sun moved through a 48-minute cycle. **This sun does not move** — night is a *switch* between two
  static rigs. Its 3 ms was a 2016 console at 60 fps; the target is a phone. **The sequel's story is
  evidence *for* baking, not against.**
- **Planar reflections and SSR.** Unimplemented in the locked Mobile renderer, and the cheap equivalent
  already ships — `city_facade_clean.gdshader` bows a reflected ray per pane through a sky gradient.
- **The wet-material overlay.** Anti-goal, and it needs a second material layer, UVs, mask and noise
  textures, and SSR — four things the pipeline deliberately lacks.
- **Keeping UVs by restoring an unclustered LOD0.** There are no UVs to keep: the non-textured set
  ships **0 images and no `TEXCOORD_0`**, and an exact weld would not preserve them anyway (see
  `ART_DESIGN.md`, "What buildings will *not* get"). Cost would be 30.5 MB and 40% of visible
  triangles for a difference `Q16` measured as invisible from the driver's seat.
- **Stealing UVs from the individualised set.** Cheap to acquire — `Accept-Ranges: bytes`, and geometry
  is 4–7% of the download. But **a UV without its image is not data**: they are per-image atlas
  coordinates across primitives that overlap in `[0,1]`, useless as a lightmap parameterisation, and
  Godot's importer generates a better unwrap from geometry alone.
- **Shipping the terrain orthophoto at low resolution.** Size is genuinely a non-issue (~1.1 MB in
  ETC2). It fails on baked illumination (`Q36`), a **1.6×** road-width misregistration, and +53 draw
  calls.
- **`VEGETATION(TB)` and `GENERIC`.** 1.52 M and 3.95 M triangles, one welded blob per sheet, no
  `COLOR_0`.
- 🔴 **Deriving glazed-vs-solid from the imagery — and this one had looked promising.** The consumer
  exists and currently guesses: `city_facade_clean` ships `glass_ratio 0.52` hashed per building.
  **Measured, it does not separate.** A dark-and-blue curtain-wall proxy gives a smooth decay, not two
  populations, and height does not split it either — share above 0.3 runs 29.8% / 24.4% / 25.7% /
  16.7% across the 0–15, 15–30, 30–60 and 60 m+ bands, if anything inverted. ⚠️ **And coverage caps
  every version of it**: median **14.3%** of wall area is photographed at all (`Q37`).

**Two method notes worth more than the findings.**

⚠️ **A degenerate value that repeats to the last decimal is the tell.** The first run of the glass
probe was invalid and looked *better* than the truth — 53.2% of samples landed on exactly RGB(60,60,60)
atlas filler, producing `b*` of exactly `-0.00` at both quartiles across 354 buildings. Chasing it is
what found `Q37` in shipped data.

⚠️ **Shrinking the atlases to probe them faster is safe for colour and unsafe for everything else.**
Mean ΔE **0.64** at 1/4 and **0.80** at 1/8, and coverage survives *exactly* — **provided the filler
mask is computed at full resolution and carried through the shrink as a fractional weight**. Shrink
first and coverage is unrecoverable, because filler and clipping are exact-value tests. Periodicity has
a hard floor at ~1/2. ⚠️ **A persistent shrunken cache is not worth it** — 242 MB at 1/16 to save a
full-res local pass measured at under two minutes.

**See.** `ART_DESIGN.md` anti-goals · `ARCHITECTURE.md` tile contract · `DATA_SOURCES.md` · `Q31` ·
`Q37` · `Q39`

## `Q42` — The reader answers seven questions nobody consumes

**Status.** 🟡 Open — analysis of the 40 paid validation responses; nothing rider-shaped is
validated at region scale or consumed, **but the channel is now waiting for them**: the `Q40`/`Q41`
plumbing shipped `TEXCOORD_1` with `y` written `0.0` and its rider layout fixed in
`ARCHITECTURE.md`'s contract table (storey pitch in 1/32 m steps over the 2.5–4.5 m window, podium
floors with "no podium" distinct from refusal, balconies, emphasis). Filling a field a
refusal-aware consumer already reads as "0 = refused" changes bytes, not meaning — so each rider
now owes exactly its own validation, and no further `schema_version` bump. Consumption is planned
as `P3-7a`, in reliability order. The podium slice was graded 2026-08-11 against the joined
boundaries and **failed its pre-fixed bar** — the record is under `Q47` · **Owner.** `P3-7a`

**The observation.** `Q41`'s reader schema asks for more than grammar, glazing and tint: it returns
`storey_count`, `band_period_floors`, `podium_floors`, `podium_glazed`, `balconies`, `emphasis` and
`signage` on every call — and the plan that survived `Q40` consumes none of them. Every full-sheet
call collects these fields whether or not anything reads them, so their marginal *collection* cost
is zero; what they cost is validation and plumbing. The 40 cached responses are already paid for,
and this record is what they say.

**Fill rates over the 25 readable validation faces** — the reader nulls a field it cannot see, per
its prompt, so a low count is refusal behaviour, not absence of the feature: `emphasis` 25/25,
`balconies` 22/25, `tint` 14/25, `storey_count` 10/25, `signage` 9/25, `podium_floors` and
`podium_glazed` 6/25, `band_period_floors` **0/25**.

**Storey pitch is the strong result, and it is the record `Q40` said storey height was owed.**
Dividing each face's unwrap height by the reader's `storey_count`: median **3.32 m/floor** over ten
faces — against the **3.38 m** `Q40` measured by autocorrelation on three faces of a building the
reader never counted. Two instruments that share nothing but the photography agree to within 2%.
The caveats are real: the field is *visible floors on this face*, not building storeys — one 55 m
face with four legible floors computes 13.81 m/floor, and two faces of the same tower disagree 30
against 35 — so consumption needs a per-building reconciliation (median across faces, a 2.5–4.5 m
sanity window, and refusal outside it), not a raw read.

**The rest, briefly.** `emphasis` is filled on every readable face and coheres with grammar
(curtain → horizontal/grid, blank → none) — a shader-ready reading-direction parameter that doubles
as a grammar cross-check. `balconies` selects punched variants. `podium_floors`/`podium_glazed` are
sparse but plausibly real, and they are the measured answer to where `P3-7`'s "no windows on podium
faces" boundary sits. `band_period_floors` never commits and should not be planned around.

🔴 **`signage` reads real identities, which is exactly why it must not ship as content.** The
validation set alone returned 瑞安集團 / SHUI ON GROUP, REVENUE TOWER, YMCA and FWD — correct,
verifiable Wan Chai buildings. Real brand text and logos are trademarks (the same instinct as hard
rule 8): the field's value is hero-building *identification*, generic-signage *placement*, and
`P3-9a` recognisability grading — never rendered text. The survey table is gitignored government-
derived data regardless (hard rule 7).

**The consumption shape held, and the contract bumped once.** The `Q40`/`Q41` plumbing spent the
`schema_version` bump on `TEXCOORD_1` with the graded axes in `x` and this record's riders
*reserved* in `y` — reconciled storey pitch (quantised to 1/32 m), podium floors, `balconies`,
`emphasis` — at the bit layout `ARCHITECTURE.md` records. The vertex contract will not change again
for them: writing a reserved field is bytes, not meaning. Each consumed field still owes its own
cheap validation first — the graded run validated grammar and glazing only.

**Also visible from here, recorded as options rather than plans** (both are `Q26` art-direction
calls): the glazing dip's *light* mode is the wall/spandrel colour, so `facade_glazing`'s split can
emit a measured two-tone — wall `L*a*b*` beside glass tint — rather than tint alone; and the
glazed/blank state in `UV2` could drive a specular split so glass reads as glass at grazing light.
Neither moves until the flat-shaded direction says it may.

**See.** `Q40` · `Q41` · `Q26` · `P3-7` · `ARCHITECTURE.md` "Tile output"

## `Q43` — `glazed` is materiality; `fenestrated` is geometry

**Status.** ✅ Closed — shipped in `city_facade_clean.gdshader`, graded as `A″` under `Q26` ·
**Owner.** `P3-9a`

**Claim.** The reader's `glazed` and the shader's `glazed` were two different predicates wearing one
name, and the collision deleted the windows on half the city's walls. They are now two floats:

- **`fenestrated`** — does this wall have openings at all. Only the grammar answers it, and only
  `blank` answers it *no*.
- **`glazed`** — are those openings glass. This is the reader's axis, defined in
  `tools/facade_grammar.py` as whether glazing **dominates** the façade area, and graded 24/24.

**Why the ETL was not the thing to change.** `punched` is defined to the reader as "openings cut
into a **dominant solid** wall", so `(glazed=false, punched)` is not a contradiction — it is the
modal Hong Kong tenement, and `building_verdicts` is right to null only `(true, blank)` and
`(false, curtain)`. Forcing `glazed = 1.0` for any committed fenestrated grammar was the other
candidate fix and is one line, but it makes the graded glazing axis **inert on 75% of wall vertices**
— paying for a survey and then not consuming it wherever it overlaps a grammar — and it inverts the
precedence the ETL already sets, where `glazed` stands and the grammar refuses.

**Precedence, and why it is not symmetric.** A committed `glazed` raises `fenestrated` and never
lowers it: "glazing dominates" is positive evidence that openings exist, while "glazing does not
dominate" is no evidence at all that they do not. Where the grammar refused, `fenestrated` keeps the
hash — nothing the reader returns says "this wall is blank" except the grammar itself, and a refusal
must not acquire a verdict by inference.

⚠️ **The `draws_detail` early-out is where this bug would have survived the fix.** It is a derived
predicate over five conditions, and it tested `glazed`; splitting the term at the point of use and
leaving the guard alone would have skipped the whole block and drawn exactly as many pixels as
before — feature implemented, feature unreachable, for the second time in one file. It now tests
`fenestrated`, and the invariant that licenses dropping `glazed` from it is written down: since this
change `glazed` reaches the albedo only through the pane material, which is multiplied by a mask
that requires `fenestrated`.

**What an unglazed opening is made of.** Two new tunings, in `city_facade.tres` per hard rule 4:
`recess_colour` (a dark reveal, `0.12, 0.12, 0.13`) and `unglazed_reflect` (`0.18`, the share of
`glass_reflect` a non-dominant opening keeps). ⚠️ **Deliberately not zero** — a Hong Kong tenement
window is dark glass in a concrete hole and does catch the sky; at zero the openings stop reading as
openings and read as dark rectangles painted on the wall. ⚠️ **Authored, not measured.** `Q40`
measured the tint of *glazing*; nothing has measured a concrete reveal, and `A″` is where these get
judged.

⚠️ **Making unreachable code reachable is its own hazard, and it caught two branches.** The `fin` and
`curtain` ratios describe a *glazed* skin — the fin switches the horizontal cut off entirely, and the
curtain opens the mask to 92% — because until this change they could only ever be filled with glass.
Handed a recess they paint a full-height dark slab instead of windows, on about **2% of wall
vertices**: a committed `fin` the survey calls unglazed (0.94%), plus whatever the hash draws as fin
or curtain on a wall the reader called unglazed and left the grammar refused (~1.1%). A committed
unglazed `curtain` is not among them — the merge nulls that pair — but the hashed treatment is. Both
now fall back to punched proportions where materiality contradicts the grammar, and keep their own
pier, which is what still tells the types apart. **The review that found it read the diff; the shoot
did not** — the eight fin buildings are not prominent at any of the three cameras, and the re-shoot
moved exactly one published number (`kerb` p90 36.67 → 36.79).

⚠️ **Shopfronts are weighted per mask, not per building.** `has_shop` never passed through the glazed
gate and must not start: a shopfront is glass whatever the tower above it is made of, and a
per-building weight turns every tenement's ground floor to concrete. The tower and podium masks are
disjoint by construction, so the weight is coverage, not a blend of two materials.

**Cost.** Two uniforms and about 25 lines across four sites. **No `schema_version` bump, no rebuild,
no re-survey** — `TEXCOORD_1` and its bit layout are untouched; this is entirely a consumer-side
reading of fields that already ship. `tools/check.sh` passes, and all twelve parked `C` frames are
byte-identical to `q26b`, which is the reducibility the split was written to preserve: at
`survey_apply = 0.0` one hash draw still answers both questions, exactly as before.

⚠️ **The lesson is not "check your gates".** Both sides of this contract were internally correct and
independently validated — the axis was graded 24/24, the plumbing closed on evidence, and `A′`
reproduced across 18 runs. What nobody checked was whether two correct definitions were the *same*
definition. A versioned interface catches shape drift, never semantic drift, and the only instrument
that caught this one was a rendered frame. Every `Q42` rider consumed from here owes the same check
in writing: put the reader's sentence beside the uniform's sentence, and if they differ, convert
rather than assign. `podium_floors` — "lowest floors forming a visibly distinct podium" — against
`podium_height_m` — "where the tower grid starts" — is the next one queued to make this mistake.

**See.** `Q26` · `Q30` · `Q40` · `Q41` · `Q42` · `ART_DESIGN.md` "The clean/futuristic variant"

## `Q44` — A punched opening is glass, not a black hole

**Status.** ✅ **Closed** — mechanism shipped (`P3-7a` W1), the `Q30` bar held on all three audit
cameras, and the user accepted the `A‴` frames and enabled the look as the shipped default
(2026-08-09). This is the judgment `Q43` said `recess_colour` / `unglazed_reflect` were owed ·
**Owner.** `P3-7a`

**The call.** Hong Kong punched windows are traditional glass windows, usually in aluminium frames —
dark glass in a concrete hole, but *glass*: they catch the sky, mirror at grazing angles, and read
as windows. `A″` draws them as matte near-black holes, on the stock that is 67% of read faces and
the whole of Hennessy Road.

**Confirmed in code, not only on frames.** Three terms compound in `city_facade_clean.gdshader`:

1. `opening_colour` stays `recess_colour` (0.12): the tint pick runs only for `glazed || has_shop`,
   and even when a shopfront takes the branch, `glassy = 0` on unglazed tower fragments returns the
   recess whatever the pane.
2. Reflection: `glass_reflect` 0.58 × `unglazed_reflect` 0.18 ≈ 0.10 at grazing, and
   × `glass_face_on` 0.18 head-on — **about 2% of the mirror** on a wall faced squarely.
3. Roughness stays the wall's 0.82: `glassy` zeroes the `glass_roughness` path, so the opening has
   no specular life either.

**The re-scope.** `Q43` was right to split materiality from geometry — and then wrong to let
"glazing does not dominate" decide materiality. The reader's `glazed` is a **coverage** claim —
dominance over the façade area — and coverage never decided what the opening is made of: a
tenement's openings are still glass; what differs is how much wall surrounds them, which the
punched ratios and heavy piers already express. Candidate mechanisms, judged on a re-shoot rather
than argued: a glassiness floor for unglazed openings, or `glazed` re-scoped to coverage only with
opening material always glass — `recess_colour` / `unglazed_reflect` becoming the frame-and-reveal
treatment rather than the whole opening.

**The mechanism, landed (`P3-7a` W1, 2026-08-09).** One tunable spans both candidates rather than
forking the code: `unglazed_glassy` in `city_facade_clean.gdshader` floors the per-building
glassiness — `glassy = mix(mix(unglazed_glassy, 1.0, glazed), 1.0, shop_share)` — so 0.0 is the
`Q43` behaviour exactly (the inner mix collapses to `glazed`), 1.0 makes the opening material
always glass with the recess reduced to frame-and-reveal, and the shipping point between them is a
tuning verdict on the `A‴` re-shoot. The tint-pick guard widens to
`glazed || has_shop || unglazed_glassy > 0` — the *uniform*, not the per-fragment `glassy`, so the
branch stays coherent — and `reflected` / `roughness` need no edit because both already scale with
`glassy`, which is what made the floor sufficient. Shader default 0.0; **0.65 authored in
`city_facade.tres` as the re-shoot's starting point**, not a verdict. Parked byte-identity held:
`street` / `skyline` / `kerb` at `survey_apply = 0.0`, shot twice and sibling-`cmp`'d, are
byte-identical to `q26_C_cf19201`. The dark-mode-tint guard below needed no code: the ETL writes a
tint only at `glz = 2` and `verify_tiles.gd` asserts tint → glazed, so the widened branch cannot
route `survey_pane` onto punched stock — now stated at the override site.

⚠️ **The `Q30` trade-off is the bar.** Matte openings are where `A″` gave back 39% / 60% of `A`'s
chroma cost at `street` / `kerb`; re-glassing re-spends part of that. Acceptance: whole-frame mean
`C*` against `C` stays ≤ `A`'s cost on all three audit cameras. ✅ **Graded on the `A‴` re-shoot
and held**: `street` +1.16 ≤ +2.28, `kerb` +0.78 ≤ +1.43, `skyline` −0.05 ≤ −0.02 — only `kerb`
re-spent, and less than half its headroom. The full table is in `Q26`; what remains open here is
the user's verdict on the frames.

⚠️ **Punched panes must not take `facade_glazing`'s dark-mode tint.** `Q40` conditioned the tint on
`glazed` for exactly this stock — on a punched building the dark population is shadowed reveals and
warm render, not glass. Their pane colour is authored/hashed (and `Q45`-modulated), never the
unconditioned measurement.

**See.** `Q30` · `Q40` · `Q43` · `Q45` · `Q26`

## `Q45` — One pane palette across the city reads as wallpaper

**Status.** ✅ **Closed** — mechanism shipped (`P3-7a` W2) at the authored 6.0 / 4.0 / 0.25, and
the user accepted the `A‴` frames and enabled the look as the shipped default (2026-08-09). The
`Q35` salt-and-pepper bound stands as the constraint on any retune · **Owner.** `P3-7a`

**Confirmed state.** Pane colour has exactly four values city-wide: three authored tints hashed per
building (`glass_colour`, `glass_tint_b`, `glass_tint_c`) plus one `recess_colour` shared by every
punched opening. The surveyed 240-bin tint varies properly but is written only for reader-glazed
buildings (~226 of 2,214). Within a building every pane is one colour, and the wall's
`value_jitter` / `warm_cool_jitter` never reaches the pane — the glazing mix *replaces* the jittered
albedo rather than modulating it. What varies per pane today is lighting (`pane_bow`,
`pane_jitter`), not colour.

**The direction.** Modulate pane colour per building: a seeded `L*` / `b*` jitter on the hashed
fallback, and/or a pull toward the building's own measured hue (`COLOR_0`, linearised through the
shader's existing `vertex_srgb_to_linear` — `Q27`'s conversion is mandatory here as everywhere).

**The mechanism, landed (`P3-7a` W2, 2026-08-09).** Both halves, as three tunables:
`pane_l_jitter` / `pane_b_jitter` (seeded CIELAB jitter on the hashed pick, draw slots 13/14) and
`pane_hue_pull` (the pane's full `a*b*` mixed toward the building's own measured chromaticity,
`COLOR_0` linearised first — a chromaticity pull, not a hue rotation: near-neutral buildings pull
their panes toward grey, and running after the jitter it scales the effective `b*` amplitude by
`1 − pull`; both effects are in the accepted `A‴` frames). The whole computation is hoisted to `vertex()` into a `flat` varying
`fallback_pane` — `survey_pane`'s exact precedent, since it is per-building constant — using a new
`linear_to_lab()` that mirrors `etl/pipeline/colour.py`'s forward conversion, kept beside its
inverse so the pair cannot drift apart separately. The fragment's survey override is untouched:
`pane_colour = survey_pane` still replaces the fallback wherever a tint was measured, so the
modulation reaches only the hash tints and (post-`Q44`) the punched panes — exactly where the
record said the variation belongs. Zero-amplitude is guarded to skip the Lab round trip, so at 0.0
the pick is bit-exact with the old inline select. Shader defaults 0.0; **6.0 / 4.0 / 0.25
authored in `city_facade.tres` as `A‴` starting points**, not verdicts. Parked byte-identity
held: all three audit cameras byte-identical to `q26_C_cf19201`, shot twice and sibling-`cmp`'d.
On the `A‴` re-shoot the modulation *lowered* frame chroma — `street` mean `C*` cost fell +1.40 →
+1.16 against `C` relative to `A″`, the chromaticity pull toward near-neutral buildings doing
exactly what the mixing maths says — and the variation arrives through `L*`/`b*` spread instead.
The `Q35` salt-and-pepper bound stands as the constraint on any retune.

⚠️ **Modulate the fallback, never the measurement.** A surveyed tint is the answer for that
building; jittering it re-invents what `Q40` measured. The hash tints and the punched panes
(`Q44`) are where the variation belongs.

⚠️ **`Q35` interplay, in the opposite direction.** `Q35` complains adjacent blocks land too far
apart in *wall* reflectance where real blocks share cladding; this record wants panes further
apart. Both are graded from the street, and the resolution is scale: pane variation should read
within a frame without turning the skyline into salt-and-pepper glass.

**See.** `Q27` · `Q35` · `Q40` · `Q44` · `P3-7a`

## `Q46` — A grammar refusal draws a quiet tier, not invented fenestration

**Status.** ✅ **Closed — accepted in scope, 2026-08-10.** The `Q30` bar held on all three audit
cameras, parked byte-identity held, and the user's verdict came from a `survey_debug`-tinted
drive test: refused stock reads quiet; the residual sightings sit on committed stock (`Q47`) ·
**Owner.** `P3-7a`

**The call.** The 2026-08-09 drive test of the shipped `A‴` default returned five sightings of
invented fenestration on windowless stock — HKCEC's service base and tunnel piers, plant boxes, a
footbridge lift tower, sportsground walls — all grammar-refused, where the hash drew with the same
confidence as anywhere: it could pick curtain or fin, and rolled a shopfront at `shopfront_share`
without consulting the survey at all. This record deliberately rebalances `Q40`/`Q41`'s "refusal
falls to the hash": the hash still draws, but from a conservative distribution.

**What refused means — and does not.** Refused is the survey's own small-or-occluded signal —
grammar commits on 12% of buildings under 4 m against 78% over 40 m, on photography that covers a
median 14.3% of wall area and is occlusion-biased to the street — not "this wall is blank":
`blank` is the only opening-denying verdict (`Q43`) and committed 10× region-wide. So the tier
lowers confidence rather than denying openings: solid probability rises, what still fenestrates is
punched-with-heavy-piers, panes mute, and a shopfront needs positive evidence. Count as of this
record: **772 grammar-refused of 2,214** in `facade_grammar.json` (earlier docs recorded
771/2,213; those figures stand as written).

**The mechanism, landed (`P3-7a` W3, 2026-08-10).** Five tunables in
`city_facade_clean.gdshader`, eligibility `survey_state.z < 0.5` under `survey_on` — never
geometry: `quiet_shopfront` shrinks the shopfront lottery on refused stock (authored 1.0 = never,
the categorical half); `quiet_clamp` is the share of refused stock whose hashed treatment falls to
punched, on draw slot 15 (authored 1.0); `quiet_pier_ratio` is a `max()` floor over the
treatment's pier (authored 0.68, against `punched_pier_ratio` 0.52); `quiet_solid` raises the
solid-share threshold by `mix` toward 1.0 (authored 0.55: solid probability 0.27 → ≈0.67);
`quiet_pane_mute` scales `fallback_pane`'s chroma in CIELAB after the `Q45` jitter and pull
(authored 0.5). All five are bit-exactly inert at 0.0 and dead at `survey_apply = 0.0`. Committed
stock is untouched by construction: the clamp sits upstream of the committed override, which
rewrites `treatment` unconditionally; the pier is a refusal-gated floor; the solid raise sits
upstream of the glazed override, so the 46 refused-grammar buildings whose glazed axis committed
`True` are re-glazed by the committed evidence; and the mute touches only `fallback_pane`, so a
committed tint wins unmuted (`Q45`'s rule).

**The bar, held.** Whole-frame mean `C*` vs `C`: `street` **+1.10** ≤ +2.28 · `kerb` **+0.74** ≤
+1.43 · `skyline` **−0.04** ≤ −0.02 — below `A‴`'s +1.16/+0.78 on the two street-level cameras,
the tier removing chroma as the maths says it must. Parked byte-identity: all three cameras at
`survey_apply = 0.0` with the quiet values authored, shot twice, sibling-`cmp`'d, byte-identical
to `q26_C_cf19201`. Against the accepted `A‴` frames the change reaches 1.6% / 1.8% / 0.9% of the
`street` / `skyline` / `kerb` frames, and the responding pixels' `C*` p90 falls 28.1 → 22.6
(`street`) and 27.6 → 19.3 (`kerb`) — the response is confined to refused stock and is quieter
than what it replaced.

⚠️ **Not a height gate.** `Q34` stands — height plus footprint explain 1.4% of the façade signal.
Eligibility is the survey's own refusal state: a tall occluded tower quiets, a short committed
building does not.

⚠️ **A committed `blank` can still draw a shopfront.** The tier conditions on refusal, and `blank`
is committed — 10 buildings region-wide, out of scope because committed stock is untouched. If one
is sighted, `W4`'s override table is the remedy, not a wider gate here.

⚠️ **Mute chroma, never glassiness.** `quiet_pane_mute` scales `a*b*` only. Dimming the mirror
instead would re-create the matte holes `Q44` closed — quiet openings are still glass.

**The verdict, and a correction (2026-08-10).** The `A⁗` taxi pair could not carry the verdict —
its drive script diverged from the pre-`W3` comparison in `build/driver/w3_before_taxi/`, so the
underpass sighting had no matched "after" — and the verdict came instead from a live drive with
`survey_debug`, a triage tint in `city_facade_clean.gdshader` that paints each facade by survey
state (magenta refused, orange this record's 46-building carve-out, green committed). The user's
finding: refused stock reads quiet, and the surviving wrong windows sit **overwhelmingly on
committed (green) stock**, the carve-out a minor contributor. That corrects the call above:
HKCEC's service base and tunnel piers are **grammar-committed** — the tower's verdict paints
them — so that sighting was never this tier's to fix. The committed-stock residual is a
population, too many for `W4`'s exceptions-only table; it opens `Q47`.

**Forward.** Refusal conservatism extends to `lit_window_share` when the night variant lands: a
refused building draws fewer lit windows, on this same eligibility signal.

**See.** `Q34` · `Q40` · `Q41` · `Q43` · `Q44` · `Q45` · `Q30` · `Q26` · `Q47` · `P3-7a`

## `Q47` — A committed verdict is right about the tower, wrong about the ground band

**Status.** 🟡 **Route decided 2026-08-10** — the sequence in "The call" below; `R4`'s conversion
**failed its pre-fixed bar 2026-08-11** and the route was **re-called the same day: data-only** —
survey podium metres never pack; closes when the shipped boundary is graded · **Owner.** `P3-7a`

**The finding.** With `survey_debug` tinting the city by survey state, the user attributed the
wrong windows that survived `Q46`'s quiet tier **overwhelmingly to committed (green) stock**:
`Q41`'s per-building majority verdict, earned by tower-biased photography (grammar commits on 12%
of buildings under 4 m against 78% over 40 m), is painted over the whole massing — podium, service
wings, ground band — exactly where the player looks from the kerb. HKCEC is the canonical case
(`W4`'s entry: right about its towers, wrong about its podium), but the drive says it is a
population, not an exception. The survey's occlusion bias shows up twice with opposite signs: on
small stock it refuses, which `Q46` now handles; on tall stock it commits from the tower and
over-generalises downward, which nothing handles.

**What is disqualified.** `W4` overrides at this scale — the same argument that disqualified
overrides as the systematic fix for the 771 refused buildings (`Q46`). Retuning `W3` — the quiet
tier conditions on refusal, and these verdicts committed. Any geometry gate — `Q34` stands.

**The candidate routes.** (1) **`R4`, the podium rider** (bits 7–11): `podium_floors` /
`podium_glazed` are already collected by the graded run's reader (`Q42` — the bits are reserved,
nothing packed yet), and a committed tower treatment would stop at a data-supported boundary. Its preconditions stand unchanged — the `podium_floors` →
metres conversion written down before anything is assigned (`Q43`'s drift warning), its own
validation bar fixed before grading. This finding is an *impact* argument for revisiting the
rider order, which `Q42` set by fill-rate reliability alone; revisiting it is a decision to
record, not a default. (2) **A ground-band survey pass** — the storefront batch (design now, pay
after `P3-9a`) reads exactly the band the photography under-covered, and `podium_glazed →
has_shop` is already named the only data-supported route to a shopfront. Choosing between the
routes, or sequencing them, was the open decision — made in "The call" below.

**The routes, measured (2026-08-10).** The podium fields the graded run already collected, mined
from the cached sheets — zero API spend. Fill on the population this question names: **981 of the
1,442 committed-grammar buildings (68.0%) have at least one readable face committing
`podium_floors`**. Committed stock ≥ 40 m: 417/633 (65.9%) any-face, 322 (50.9%) on a strict
per-building majority; committed 20–40 m: 298/411 (72.5%) and 289 (70.3%). Region-wide, 1,100
buildings (49.7%) carry a strict-majority podium; refused stock fills at 33.0%, but `Q46` already
owns it. The values look like podiums: 1,079 of the 1,100 (98%) say 1–3 floors, and only 42 of the
1,043 with a visible-storey count exceed it. `podium_glazed` commits beside it — 594 True / 413
False / 93 refused among the majority-podium buildings — so the `has_shop` route rides the same
bits. Faces disagree enough that the vote is doing real work: of 472 buildings with two or more
podium votes, 278 (58.9%) are unanimous. ⚠️ **Fill is prioritisation evidence, not validation** —
`Q42`'s discipline stands, `R4` still owes its own bar fixed before grading, and no hand labels
exist for podium yet. The ground-band survey pass, by contrast, starts from zero collected reads
and pays per face: it remains the only route that *measures* the band rather than inferring its
extent, but its impact case now has to beat data that is one-half to two-thirds already in hand.

**`R4`'s conversion, written ahead of the call** (`Q43`'s precondition, discharged here). The
reader answered: *"how many lowest floors form a visibly distinct podium (shopfronts, different
treatment), null if none."* The shader needs: *the height, in metres, where the committed tower
treatment stops.* The conversion is `podium_floors` × the building's reconciled pitch (`R2`'s
per-building median where it commits, the city `floor_height_m` fallback where it refuses) →
metres, computed at pack time — never `podium_floors` assigned as though floors were metres.

**A third route, scouted (2026-08-10) and verified to `DATA_SOURCES.md` grade the same day.**
iB1000 — the digital topographic map 3D-BIT Level 1 is extruded from — carries the podium as a
**first-class feature**. The scout's layer names were close but not exact: it is one `Building`
polygon layer (EPSG:2326 verified, levels in mPD), whose `TYPEOFBUILDINGBLOCK` domain splits `T`
building / `P` "Podium Block" / `OS` open-sided / `TS` temporary, with `BASELEVEL` / `ROOFLEVEL`
and a `CERTAINTY` flag the data dictionary defines as "certainty of the podium polygon". All three
owings verified over Wan Chai's six sheets. **(a) Levels ship 100% filled on every `T` (1,220) and
every `P` (280) block** — nulls exist but live entirely on open-sided (84%) and temporary (68%)
structures. Podium heights (roof − base) p50 14.6 m, p10 6.0, p90 19.6; `CERTAINTY` 262 certain /
18 not. 668 towers (54.8%) intersect a podium block, and 247 meet one *exactly*: Times Square's
`T` base 75.6 mPD = its `P` roof 75.6, Sun Hung Kai Centre 16.4 = 16.4, and HKCEC's podium is its
own block (3.7→56.0 mPD) beside the 70.3 m old wing — the boundary in metres, per building,
exactly where `Q41`'s tower verdicts paint today. **(b) Footprints register sub-metre** against
the shipped volumes: 0.1 m edge agreement where a block and a mesh correspond 1:1 (Sun Hung Kai
podium); the larger bbox deltas are 3D-BIT merging tower+podium into one mesh where iB1000 splits
blocks — the added information, not misregistration. **(c) 41.8–45.3 MB per sheet, 260 MB for the
region**, ~21 s each, keyless. Access *inverts* the scout's caveat: the TileIndex's per-sheet
`directDownload` URLs return plain 200s (the intranet redirect was the human download form), while
the ISO record's `download/common/<hash>` portal links 403 to scripted GET and the seamless set
still 504s — the TileIndex is the only scriptable route, and it is enough.
`BuiltStructurePolygon` / `UtilityPolygon` carry `W3`'s signal as coded domains (Wan Chai: 10
ventilation shafts, 10 swimming pools, 6 each fountains / pavilions / basketball courts, an
electricity substation; 2 pylons, a water tank). Method, for repeatability: grep the ISO record
for `layer_name=` → fetch the `TileIndex` → intersect with the region's geodetic bounds from
`load_city` → fetch the six `FGDB` URLs → pyogrio over `/vsizip/<zip>/<SHEETNO>/<SHEETNO>.gdb`
(raw API and `read_bounds`; `gdb.py` decodes linestrings only and refuses Z, so it sat this probe
out — consuming iB1000 is a pipeline task, not a config edit). Probe uncommitted per `P3-7`'s
pattern, download discarded; the dataset entry is in `DATA_SOURCES.md`. ⚠️ Two things the data
does not do: `P` is a partial classification (Central Plaza has none — absence means no distinct
podium block surveyed, not "no ground band"), and `podium_glazed` still comes only from a survey,
so iB1000 bounds the treatment, not the shopfront.

**The call (2026-08-10).** The sequence, not a single route: **iB1000 primary, `R4` complement,
the ground-band batch unchanged in scope.** (a) Where a committed tower intersects a `P` block,
the boundary is the block's levels — metres from data, no inference. Precedence is
**data > survey-inferred**, extending the existing `authored > survey > hash` ladder rather than
inventing a second conflict rule. (b) Where no `P` block exists, `R4`'s conversion supplies the
boundary — and the 668-tower iB1000 overlap becomes `R4`'s validation set: grade floors→metres
against the block metres **before anything packs**. That discharges `Q42`'s bar by a join instead
of hand labels, and the 247 exact level meets show the datasets share a survey lineage (3D-BIT
Level 1 is extruded from B1000), so the grade tests the reader, not dataset disagreement. (c) The
post-`P3-9a` batch keeps its existing storefront scope; `has_shop` still rides `R4`'s
`podium_glazed`, which no topographic layer carries. **Why not the alternatives:** iB1000-only
leaves 45.2% of towers unfixed by design (`P` is partial — Central Plaza); `R4`-only rests the fix
on the same tower-biased photography that caused this finding, with a hand-labelling debt the
overlap pays for free; widening the survey batch pays per face, from zero, in the band the reader
refuses most, for extent data the other two routes already hold. **Costs accepted:** `gdb.py`
polygon-Z decoding is a pipeline task, the region build gains a 260 MB build-time download, and
the merge must record which mechanism won per building. `W4`'s flagship entry shrinks accordingly:
HKCEC's podium is its own `P` block (3.7→56.0 mPD), so its extent comes from data and any
remaining override covers treatment only.

**Ingestion half landed 2026-08-10 (`P3-7a`).** `gdb.py` decodes polygon-Z (both WKB dialects —
GDAL hands back the wkb25D high-bit form, not ISO offsets; M and EWKB-SRID refused), the
`topography` tiled source fetches the six sheets (260 MB, idempotent; the host's incomplete TLS
chain is completed by a committed intermediate, `extra_cas` in the yaml), and
`buildings.podium_blocks` reads the `Building` layer per sheet behind the `podiums:` config
block. The acceptance test reproduces this record's verified numbers from inside the pipeline —
1,595 blocks (1,220 `T` / 280 `P` / 76 `OS` / 19 `TS`), levels 100% filled on every `T` and `P`,
every geometry decoded. Nothing consumes the blocks yet; the tower↔block join, the
mechanism-won provenance, and the contract question stay queued as the second half.

**The contract question argued (2026-08-11), against `ARCHITECTURE.md`, in its own commit.** Five
points, none of which bumps `schema_version`. (i) Per-building data reaches the game only as
per-vertex constants on the merged tiles — `city.json` gains no buildings section for this, and
the join's full-precision output lives in an ETL intermediate (`podiums.json`, written by the new
`podiums` stage) that `export.py` never names, exactly `buildings.json`'s standing. (ii) Bits 7–11
stay **floors**, and iB1000's metres convert *against the packed storey pitch* at pack time — not
because metres would not fit (30 floors ≈ 84 m at the fallback pitch clears HKCEC's 52.3 m), but
because the shader draws window rows at pitch intervals, so a boundary is only renderable on the
storey grid: floors × the same packed pitch the shader multiplies back bounds the round-trip error
at half a pitch by construction, where a separately-quantised metres field would add a second grid
that cannot agree with the first. (iii) The mechanism-won provenance is ETL-side only — the
runtime never branches on where a boundary came from, and `R4`'s grading, its only consumer, runs
in the pipeline; vertex bits spent on it would ship bytes no shader reads. (iv) `R4`'s eventual
write stays the documented "filling a reserved field a refusal-aware consumer already reads as
0 = refused" case — `verify_tiles.gd`'s range check moves in *that* commit, per the
three-places-one-commit rule. (v) The ladder extends to **`authored > data > survey > hash`**:
authored stays on top because `W4` exists to correct both instruments where the user's eye rules
(this record already shrank HKCEC's override to treatment-only, its extent now data), data sits
above survey by this record's own call, and the hash remains the floor every refusal falls to.

**Join landed 2026-08-11 (`P3-7a`, the second half).** The `podiums` stage (between `fetch` and
`buildings` — the dependency direction `R4`'s pack will need) stitches the per-sheet pieces and
joins them to the shipped meshes. Two findings the probe's frame could not see, both measured
against the live sheets: **a sheet cut clips a block** (zero whole-block duplicates; the pieces
abut exactly on the cut line, so identity is attributes plus contact, and 1,595 pieces group into
**1,480 logical blocks** — 1,134 `T` / 251 `P`, 104 groups spanning a cut), and **this record's
668/54.8%/247 is a strict positive-area bounding-box frame** — reproduced verbatim by the
acceptance test so the numbers stay tied to their method, while the operative join uses true
polygon overlap: **458/1,134 towers meet a `P` block, 538 pairs, 228 exact level meets**. The
mesh join is spatial (iB1000 carries no stem) and depth-gated at 0.3 m against the 0.1 m
registration noise: **310 of 1,385 stems carry a data boundary** (291 certain; p50 13.6 m), each
row in `podiums.json` recording boundary metres, base, winning blocks, and `mechanism: "data"` —
the provenance `R4`'s grading conditions on. HKCEC gets 52.1 m over base 3.9 from `11-SW-9D:77`,
its own `P` block; Times Square's boundary lands at exactly 75.6 mPD, the record's flagship level
meet. Remaining before this closes: `R4` graded against the joined boundaries **before packing**,
the pack itself (floors against the packed pitch, per the contract argument above), and the
shipped boundary graded.

**`R4`'s bar, fixed 2026-08-11, before the grader exists.** `Q41`'s discipline, adapted: there,
hand labels pre-existed and the pools could be counted before the run; here membership is
data-determined, so what this record fixes is the pool *definitions*, the bars, and a minimum-n
gate that keeps the headline pool from passing vacuously — the run fills in the n's. The only
numbers consulted in advance are census, not metres: the join figures above, plus one count taken
while writing this bar — **235 of the 310 boundary stems have at least one readable face
committing `podium_floors`** (259 for `storey_count`). Nothing error-shaped was computed before
this text was committed.

*The instruments.* The grade compares two instruments that share nothing but the stem key and a
government survey lineage: the vision reader over individualised-mesh unwraps (the survey side)
against iB1000 `P`-block levels joined to the shipped meshes by geometry (the data side,
`podiums.json` above). It is therefore not a `deck_error.py`-style re-measurement — the join has
its own pinned acceptance test — and the grader reads an ETL intermediate rather than the shipped
bundle because the boundary never ships and its provenance is ETL-side by contract point (iii).
The tool sits in `tools/` and is run by hand all the same; `ARCHITECTURE.md`'s "a stage cannot
mark its own work" is satisfied here by instrument independence, not bundle reading.

*The conversion, made executable.* The conversion under grade is the one written ahead of the
call: floors × reconciled pitch, never floors assigned as metres. `R2` has no code yet, so the
grader's definition is normative for the pack: per readable face committing `storey_count` ≥ 1,
pitch = building height ÷ that count; the per-building pitch is the **median over those faces**,
accepted iff it lands in the 2.5–4.5 m window, else the building refuses to the 2.8 m city
fallback. A committed pitch is quantised to the bits-0–6 grid (2.5 + (k−1)/32) so the graded
conversion is byte-for-byte the future packed one. Two deviations confessed now: per-face heights
exist only at unwrap time, so the pitch divides the *building* height (`facade_lab.json`) by a
per-face count — the median-over-faces step keeps `Q42`'s face-disagreement signal, the numerator
does not; and the 2.8 m fallback is *not* on the grid (k − 1 = 9.6), which is itself an argument
that the refusal path stays a shader uniform rather than ever packing.

*The verdict.* Per building, readable faces vote `podium_floors` with null counted as an explicit
**0 — "no podium"** (the prompt makes null a commitment, and the codec's k = 1 encodes exactly
this); the strict-majority rule is the reader tool's own (`_majority`: a tie, like an empty
ballot, refuses). Mapping null to 0 first is load-bearing — without it a no-podium majority and a
refusal are indistinguishable.

**The grader passes when, on its first graded run,** over the **291 `certain` rows** (the 19
uncertain rows are reported beside the pools, never in them — `certain` survives stitching only
unanimously, so they are exactly the rows whose polygon the source doubts):

| Pool | Membership | Bar |
|---|---|---|
| A — metres | certain ∧ majority ≥ 1 floor | \|floors × pitch − `boundary_m`\| p50 ≤ **2.8 m**, p90 ≤ **7.0 m**; gate n ≥ 100 |
| B — semantic | certain ∧ majority = 0 | ≤ **1/3** of the certain rows holding any majority |
| C — coverage | certain rows with any majority | ≥ **60%** |

*The arguments.* Half a pitch (≈1.4 m) is the floor the contract argument already accepts by
construction; one reader floor is one pitch, so a median asked to beat 2.8 m is asked to be
within ±1 floor — tighter would ask the instrument to beat its own granularity. p90 is two
miscounted floors plus the half-pitch floor (2 × 2.8 + 1.4 = 7.0). Pool B: every pooled stem
carries a `P` block, so the survey must beat the 49.7% region-wide base rate of majority podiums
by a wide margin — if over a third of *certain* data podiums are invisible to the reader, the
reader's notion of "podium" cannot supply boundaries where no data exists, which is `R4`'s whole
job under the call. Pool C: below 60%, A and B are measured on too little of the population to
mean anything; the census (235/310 any-face) makes 60% of *majority* verdicts reachable, not
pre-passed. Reported unbarred, because they are diagnostics rather than acceptance: the signed
median (the expected systematic offset — the reader counts the treatment band, the `P` roof
includes everything under the tower), the committed-vs-fallback pitch split, the join's exact-meet
count (aggregate only — a `podiums.json` row does not identify its meet), and the uncertain 19.

*Adjudication.* Misses are adjudicated by re-inspecting the cached unwraps; a demonstrably wrong
reading is corrected and **every correction is listed in the result**, so reader errors cannot
silently rescue a failing grade without leaving a record.

*What the outcome buys.* Pass → the pack proceeds as routed: survey floors only where no `P`
block, data metres converting against the packed pitch, precedence data > survey-inferred. Fail →
the route reopens with numbers, and the options are pre-committed: pack data boundaries only and
refuse survey inference, or a stated-rule correction (`Q34′`'s shape) recorded as fitted on this
validation set — never a quietly moved bar. The priors make failure live (98% of survey podiums
say 1–3 floors ≈ 2.8–10 m converted, against a boundary p50 of 13.6 m); that is the grade
working, not a reason to soften it.

**Graded 2026-08-11 — the bar failed, and the failure is `Q43`'s gap, measured.**
`tools/podium_error.py`, first graded run, defaults = the bar above. Every bar was fixed at
`3949e41` before the grader existed; one diagnostic clause (the exact-meet subset, which a
`podiums.json` row cannot identify) was clarified to aggregate-only at `6aa28dc`, also before the
run.

| Pool | Result | Bar |
|---|---|---|
| A — metres | n=121 (gate 100 met) · \|err\| p50 **10.76 m** · p90 **12.87 m** | ≤ 2.8 / ≤ 7.0 — **FAIL** |
| B — semantic | 82 of 203 decided, **40.4%** | ≤ 33.3% — **FAIL** |
| C — coverage | 203 of 291 certain rows decided, **69.8%** | ≥ 60% — pass |

The signed median is **−10.76 m**: the conversion undershoots the data boundary by three to four
storeys, systematically — only 2.5% of Pool A lands within half a pitch, so this is not noise
around a workable mean. The pitch is not what failed: 124/310 buildings commit a reconciled
pitch, p50 **3.28 m**, within 1% of `Q42`'s 3.32 — `R2`'s prescription is validated in passing.
The uncertain 19 tell the same story from outside the pools (8 verdicts, \|err\| p50 10.46).

*Adjudication: zero corrections.* The five worst misses were re-inspected on both sides; every
reading is a defensible answer to the reader's own question, so no relabelling can rescue the
grade. The worst miss is the flagship itself: the 75.6 mPD exact meet — its `P` block is the
~16-storey podium mall (`boundary_m` 71.4 over base 4.2), and the reader, correctly by its own
prompt, saw "2 lowest floors of visibly distinct treatment" on three faces. Three of the other
four are low buildings that *are* mostly podium block — `boundary_m` within ~3 m of the roof —
wearing one or two floors of shopfront treatment. `podium_floors` measures the treatment band;
the `P` roof measures the massing under the tower. Two predicates, `Q43`'s pair, now 10.8 m apart
at the median.

*What the fail buys, per the pre-commitment.* The complement half of the route reopens on the
recorded options: **(a)** pack data boundaries only and refuse survey-inferred podium metres, or
**(b)** a stated-rule correction fitted on this validation set, recorded as such (`Q34′`'s
shape). The evidence leans (a): Pool B failing beside Pool A says 40% of certain data podiums are
*invisible* as treatment, so no scalar correction of the visible ones closes that gap — but the
re-call is a route decision, not this grading's to make. What survives untouched: iB1000 primary
(the 310 data boundaries this grade conditioned on), the reconciled-pitch prescription, and
`podium_glazed → has_shop`, which never depended on the metres conversion. The pack stays
blocked until the route is re-called.

**The re-call (2026-08-11): data-only — option (a), by measurement.** The reopened half closed
the day it opened, because the choice was measurable on data already in hand. Within Pool A the
rank correlation between the survey's converted metres and the data boundary is **Spearman
ρ = 0.076** — no per-building signal — so the best affine correction option (b) could ever ship
(\|err\| p50 2.46 m, fitted *in-sample* on the set that would grade it) is dominated by
constants: the shader's existing `podium_height_m = 12.0` uniform already achieves 2.97 / 5.99 on
the same pool, and the pool's own median (14.31) achieves 1.36. At ρ ≈ 0.08 any honest stated
rule collapses to "ignore `podium_floors`", which *is* option (a) — and no correction reaches
Pool B's 40% of certain podiums the reader cannot see at all. Three consequences:

1. **Bits 7–11 fill from `podiums.json` rows alone** (`mechanism: "data"`), converting against
   the packed pitch at pack time, in `R4`'s existing slot **after `R2`**. The order is
   load-bearing, not ceremony: a boundary packed today would convert against an ETL copy of the
   2.8 m fallback while the shader multiplies its own uniform — two 2.8s that a `.tres` retune
   could split silently, the exact two-grid drift point (ii) refuses. The complement packs
   nothing and keeps the uniform, which this grade measured as the better estimator anyway.
2. **Survey `podium_floors` never packs metres.** `podium_glazed → has_shop` survives — it never
   depended on the conversion — but Pool B prices its blindness: the reader misses 40% of
   certain podiums, so that rider owes its own bar at its own turn.
3. **The ground-band batch now owns the complement's boundary predicate.** Its prompt (design
   now, pay after `P3-9a`) owes the question this grade proved unasked — *where the tower grid
   starts, in floors* — so the complement's bits have a named future filler under the same
   codec, not a hope. A uniform retune (12 → ~13.5) is refused for now: it is an art call
   (`Q26`) measured only on `P`-block towers, and it moves every building to chase a population
   that may not generalise.

**See.** `Q46` · `Q41` · `Q42` · `Q43` · `Q34` · `P3-7a`

## `Q48` — A contrast ratio measures banding where an `L*` profile could not

**Status.** 🟡 **Open as a candidate — nothing built, nothing scheduled** (recorded 2026-08-13 from
`P3-6`'s photo veto). Both halves of the case are below: why the mechanism escapes `Q40`, and why
one hero building is not evidence that it scales · **Owner.** `P3-7a`

**Where it comes from.** `P3-6`'s photo-referenced repaint (2026-08-13) had to decide which of
HKCEC's procedural ribbon strips the real elevation carries. What shipped is neither a classifier
nor a threshold on brightness — it is a ratio:

```
contrast = L(band sample) / mean(L(sample +pitch/2), L(sample −pitch/2))
```

median-aggregated per **strip** — one band level on one connected wall component, because
per-triangle verdicts turned photo noise into broken dashes — vetoing the ribbon at
`veto_ratio` 0.9. Each sample is four points per triangle (centroid and edge midpoints) mapped
through the *parent* source triangle's barycentric frame into its `…A0` atlas coordinates; a lifted
sample that leaves its parent is discarded rather than clamped, because a clamped coordinate would
silently read another storey's pixels.

**Why it earns a record: Probe 3 does not reach it.** `Q40` killed per-chart analysis because
photogrammetry charts tall narrow strips — median 30 charts per building, max 1,837, median chart
area 3.8 m², and only **15.2% of wall area** (47 charts of 5,831) spanning three bays *and* three
floors. That finding is about needing a contiguous 2-D neighbourhood **in the image**. This
statistic needs none: it compares a triangle's photo sample against samples at ±pitch/2 on the same
surface **in world metres**, mediated by geometry rather than by image adjacency, so chart size is
irrelevant. `Q40`'s "work in the world-space unwrap, never in atlas space" was a conclusion about
*pictures*; this is neither an atlas-space read nor a picture but a scattered
`(world elevation, luminance)` cloud — a third option that record did not consider.

⚠️ **So "measure it from the A0 atlases" is the wrong description, and the next reader will bounce
it off Probe 3.** The accurate phrasing is *per-triangle atlas samples indexed by world elevation.*

**And mode 1 does not reach it, because the claim is smaller.** `Q40` mode 1 is structural: `L*`
modulation measures materials, not recession, so punched-versus-curtain — a **depth** property — is
not derivable from colour at any threshold (`DEEP = 6.0`; dark glass against pale spandrels reads
`L*` 17.4 and classifies `punched`). *Does this wall carry a repeating horizontal tone modulation at
storey pitch* is a **tone** claim, and tone is exactly what a texture can see. Band presence is
strictly weaker than grammar, and mode 1 does not disqualify it. ✅ The lighting objection, which is
what normally kills a tone claim on an aerial, is answered by the ratio rather than argued away:
baked sun and shade span **0.03–0.66** wall luminance across facings, an order of magnitude over the
glazing's own contrast, and dividing by the same wall half a pitch above and below cancels it. An
absolute darkness cut was tried first and fails.

**What still reaches it — four things, one of them serious.**

1. 🔴 **Mode 4 — periods appear in blank walls — and it lives in the target population.**
   `B355691583201063A0` is flat render and returned `punched` and `fin` on two faces. Weathering
   streaks, floor-slab staining and a balcony's baked shadow all produce local vertical contrast on
   a wall with no windows. The population where this instrument would be *most* valuable — `Q47`'s
   committed-but-blank ground bands — is precisely the population where its known failure mode
   lives.
2. ⚠️ **Mode 2 — reflections are most of the signal on glass.** A mirror tower's bands may be the
   street opposite it, which is why that tower's four faces disagreed with each other.
3. ⚠️ **Mode 5 and `Q37` — the selection, not the statistic.** Trees, hillsides and neighbouring
   buildings reach the survey's wall selection; `facade_glazing.py`'s depth filter moved 19 of 51
   verdicts on `11-SW-9D` and 195 of 699 on `11-SW-14B`, **in both directions**. And under 15% of
   wall area is photographed at all, occlusion-biased to street-facing faces.
4. ⚠️ **It confirms a pitch; it cannot find one.** `ribbon_pitch_m` is an authored input to both the
   band elevations and the neighbour offset. Sweeping that offset to *find* a period is
   autocorrelation — `Q40`'s instrument with a better detrend, not a different instrument.

✅ **The one-way veto is the mitigation, and it is a constraint on any future use rather than an
implementation detail.** The photo may only *remove* bands: a strip it cannot decide — no coverage,
or a parent too short for a neighbour sample — keeps the procedural verdict, and fewer than five
decided samples refuses outright (an evidence floor, not a knob: less than that is one parent
triangle's worth, where a single seam decides the strip). That is what makes mode 4 survivable — a
false band-signal on a blank wall leaves the existing answer standing, and the useful direction
(deleting invented fenestration) is the safe one. **Used as an assertion rather than a veto, this
record does not carry.**

🔴 **The evidence is n=1, graded by its author's eye.** `Q40` retains its own overclaim — "the
classifier's features are visible in the pictures before any code is written" — as the fault,
because visible-to-a-*reader* was taken as measurable-by-a-*statistic*. One hero building reviewed
against reference photographs is the same size of evidence, and that its output was *accepted* is a
statement about HKCEC's frames, not about the city.

### Two claims, and only one of them is new

**Pitch is not a new question.** Four instruments already measure storey pitch, and the one that
ships is the outlier:

| Instrument | Pitch | n |
|---|---|---|
| `P3-7` atlas-V autocorrelation — **ships as `floor_height_m = 2.8`** | 2.77 m | 227 walls / 219 buildings |
| `Q40` world-space unwrap autocorrelation | 3.38 m | 3 faces, 1 building |
| `Q42` reader `storey_count` ÷ face height | 3.32 m | 10 faces |
| `Q47`'s tower↔block join, validated in passing | 3.28 m | 124 / 310 stems |

The last three agree within 3%; the shipped constant sits **~16% below** them and nobody has
reconciled the gap (height-weighted walls against unweighted faces is the obvious candidate, and it
is a guess). `PLAN.md` already queues **storey pitch as a rider** in `P3-7a`'s sequence, at the
reserved `TEXCOORD_1.y` layout in 1/32 m steps over a 2.5–4.5 m window, owing its own pre-fixed bar.
So a mechanical pitch measurement is not a `W`-item of its own — **it is the third grader that rider
is short of**, and `Q47` is this repo's own record of what a rider costs when it is graded against a
spatial join instead of an independent instrument (\|err\| p50 10.76 m against a 2.80 m criterion,
zero adjudicated corrections, the miss a predicate gap all along).

**Presence is the new claim**, and its ground is unclaimed twice: it is the discriminator `Q47`'s
committed-stock population needs and that `W4` cannot reach at exceptions scale, and
`band_period_floors` is the one reader field that **never commits** — 0 of 25 on the validation
faces. A mechanical band detector would not audit a verdict the reader gives; it would supply the
one the reader refuses.

### What it would owe, if it is ever promoted

⚠️ **The statistic transfers; the code does not.**

- **Its own sample lattice.** `lift_m` re-maps into the parent source triangle and discards a sample
  that leaves it, so a usable neighbour needs a parent spanning ≥ pitch/2 vertically — 2.4 m at
  HKCEC's 4.8 m grid, ~1.7 m at the region's measured pitch. HKCEC works because the slicer had
  already cut 99,577 triangles at band elevations; survey stock is unsliced, so a tool would
  generate sample sites *within* each wall triangle rather than inherit them. The corner-identity
  path is hero-specific too — `facade_survey.py` loads `…A0` meshes with real `TEXCOORD_0` and needs
  no parent-id channel.
- **A pre-fixed bar and a third-party instrument.** `Q41`'s per-face `glazed` and its majority
  grammar are the obvious calibration set, **on more than one sheet**: `Q40` records that the dip's
  conditional medians flipped sign between `11-SW-9D` and `11-SW-15A`, and that a threshold which
  must point opposite directions on two sheets of the same city is not a threshold.
- **The standing three-places cost if anything ships** — merge/pack, shader decode, and
  `verify_tiles.gd`, whose `uv2.y != 0.0` assertion breaks on the first written rider. No
  `schema_version` bump: filling a reserved field a refusal-aware consumer already reads as
  "0 = refused" changes bytes, not meaning (`Q42`).

⚠️ **The dataset decision is already made; the bytes are not on disk.** `facade_glazing.py`'s region
run (2,171 buildings, 2,143 gated) proves the read works at region scale, but it did not leave the
sheets behind: `etl/sources/hong_kong/individualised/` holds **one of six**, the `11-SW-9D` the
HKCEC repaint needs, and `DATA_SOURCES.md` records the same discard-after-use pattern for `P3-7`'s
1.10 GB probe. So a region band survey costs a **5.86 GB hand re-download**, not nothing. ✅ What is
free is that it needs no new source, no new licence position and no new rule reading — the texture
is consulted at build time and discarded, the palette stays the `Q33`-checked materials, and
individualised is the per-building set, not the tile-based welded mesh rule 1 forbids.

**Not decided: whether to build it at all.** `PROGRESS.md` records that no unstarted task remains
before the `P3-9a` gate, and adding one would be the first thing to break that. The cost of doing
nothing is bounded: the storey-pitch rider grades against the reader alone, and `Q47`'s ground-band
batch (designed now, paid after `P3-9a`) may recover the presence signal from a re-worded prompt —
at the price of a new prompt hash and a paid re-survey, which is the asymmetry that made this worth
recording rather than discarding.

**See.** `Q40` · `Q41` · `Q42` · `Q47` · `Q37` · `P3-6` · `P3-7a` · `PLAN.md` `P3-7a`

## `Q49` — A tyre spends one budget, and the handbrake that follows spins the car

**Status.** ✅ Ellipse shipped · 🟡 **Drift feel unresolved** — the value is a compromise, not an
answer

**Claim.** `_apply_tyre_forces` caps lateral and longitudinal force together, on a **friction
ellipse** with semi-axes `grip_lateral × load` and `grip_longitudinal × load`, instead of clamping
each axis independently. The handbrake then blends the rear tyres toward a **locked** state, where
friction opposes the whole slip vector rather than resolving into axes.

⚠️ **An ellipse is not the isotropic circle `P0-5a` rejected, and that distinction is the whole
licence for this change.** `VehicleWheel3D` has one `friction_slip`, so its budget is a circle and
the two grip dials collapse into each other. Here the semi-axes stay separate and both dials keep
their meaning. What is new is only the *coupling*: before this, the two clamps never spoke, so the
car could brake at 0.8 g through full lock and lose no cornering grip whatsoever.

**What the handbrake now is.** Nothing scales grip down. A locked tyre is not rolling, so it has no
preferred direction — its friction opposes the entire contact-patch velocity, and at speed that
vector points nearly straight backwards, so the *lateral* component collapses out of the geometry.
That is the real mechanism, and it retired both `drift_grip_scale` and `drift_front_grip_scale`,
which were the result modelled without its cause — which is why one of them had to soften the
**front** axle for a manoeuvre that does nothing to the front axle. The front is now untouched.

⚠️ **Measured: a fully locked rear axle spins this car, and no dial prevents it.** Held at full lock
from 62.78 km/h, peak slip reached **162.1°**, against the **162.6°** `P0-5a` recorded for the
*rejected* `VehicleBody3D` and called a full spin rather than a slide. ⚠️ Read the two as the same
verdict, not as agreement to a decimal: `P0-5a`'s figure predates this entry's unification of the
slip formula (below), and it was a different car on a different model. Two findings make the spin
structural rather than a tuning miss:

- **Lowering the handbrake's grip made it worse.** Swept 0.05 → 0.30, peak slip went **177.3° →
  162.3°** and exit speed **−17.45 → 0.00 km/h**. This axle's friction is the only thing resisting
  yaw once the tail is loose, so weakening it removes the brake on the spin, not the cause.
- **A 0.5 s tap spun it too** — 135.8° to 170.5° across the same sweep. The spin is not an artefact
  of holding the button, which is what a "make it a tap" fix would have assumed.

This is correct physics. A real car at full lock with a locked rear axle really does spin. It is
also the wrong game, so `handbrake_lock` blends the rolling and locked forces rather than switching
between them, and the full-lock spin stays reachable at 1.0.

**The compromise, and why it is not a solution.** With the blend, slip rises monotonically and the
spin is gone — but slide and scrub are welded together, and the old model was **strictly better at
the design targets**:

| `handbrake_lock` | exit km/h | decay /s | decel m/s² | peak slip° | yaw° | distance m |
|---|---|---|---|---|---|---|
| 0.10 | 37.56 | 0.128 | 1.75 | 12.7 | −376.1 | 43.1 |
| **0.15 (shipped)** | **28.39** | **0.198** | **2.39** | **16.0** | **−343.1** | **36.9** |
| 0.20 | 19.41 | 0.293 | 3.01 | 18.8 | −306.3 | 31.0 |
| 0.30 | 1.97 | 0.865 | 4.22 | 23.5 | −225.1 | 20.0 |
| 1.00 | 0.00 | — | 4.36 | 48.1 | −125.1 | 7.8 |
| *old model* | *34.55* | *0.149* | *1.96* | *57.8* | *−346.6* | *40.6* |

The old fudge held a **57.8°** slide while scrubbing **1.96 m/s²**. Nothing on this curve reaches
it: 0.15 buys 16.0° for 2.39. ⚠️ **`GAME_DESIGN.md`'s "easy to hold, scrubs little speed" is
anti-physical** — a real handbrake trades speed for rotation, and the old model got the feel by
declining to. 0.15 is chosen as the only value clearing `drift_slip_threshold_deg` (14.0°) while
keeping decay nearest the authored `drift_speed_scrub_per_s` (0.08); both are still missed.

✅ **The route out is already scheduled, and this is evidence for it.** A real driver sustains the
slide on the throttle, spinning the driven rear wheels back up — that restores forward thrust while
lateral grip stays broken, which is exactly "slides a lot, scrubs little". It is unreachable here
because the model has no per-wheel angular velocity. `PLAN.md` schedules that into `B4` for skid
smoke and lockup, with "do it when the effects that consume it are built, not before" — this is a
second consumer, and a load-bearing one.

**Also measured.** Cornering is no longer free: a 4 s full-lock corner at throttle **held 62.26 km/h
where it used to gain to 81.64**, turning tighter for it (yaw −428.9° against −354.9°) over 68.2 m
instead of 82.0. Braking and coasting are **byte-identical** — 8.79 m/s², stop in 1.97 s / 16.6 m;
coast to rest in 9.40 s — which is the ellipse behaving: neither manoeuvre asks for two axes at once.

**The instrument.** `tools/skidpad.sh`, five manoeuvres on `skidpad.tscn`, `--handbrake=` to
sweep, `--scene=` to point it at `skidpad_builtin.tscn` and grade `P0-5a`'s rejected car on the same
ground. It grades and does not check, so it stays out of `check.sh`. Every figure above is one
command. Its braking row reproduces `P0-5b/c/d`'s published stop — 72.8 km/h in 2.30 s / 21.9 m
scales to 1.98 s / 16.3 m at this entry speed, against 1.97 / 16.6 measured — which is the closest
thing to a calibration this project has.

⚠️ **Three harness bugs, recorded because each produced a plausible number.** The run-up left the
throttle held, so the coast manoeuvre measured 30 s of *acceleration* to 126 km/h and failed for not
stopping — wearing the costume of `P0-5b/c/d`'s fifth bug, which is that exact symptom. Displacement
and `angle_difference` were read end-to-end, so a car that circles reported **6.2 m** travelled and
**5.1°** of yaw where the truth was ~70 m and ~360°; both accumulate per tick now. And an
`Array`/`Array[float]` mismatch killed the coroutine mid-run, leaving `ABLATION OK` printed over no
table — `_printed_rows` now makes an empty run a failure.

⚠️ **The two instruments were measuring different angles.** `builtin_vehicle_controller.gd`'s
`slip_angle_deg()` flattened the *velocity* to the ground plane and left the **nose** vector pitched,
so it read the car's attitude into its slip — immaterial on the level skidpad every recorded figure
came from, wrong the moment a kerb or a landing is involved, and not a like-for-like basis for the
comparison this entry makes. Both now flatten both vectors, and the two agree exactly: driven through
`--scene=res://scenes/dev/skidpad_builtin.tscn`, the spike's own telemetry and the ablation's
independent computation both report **2.2°** peak. One definition, computed in two places because a
`--script` tool can reach neither class.

⚠️ **A `--script` tool must not name `VehicleController`.** `handling_profile.gd` already said so;
this was rediscovered the hard way. A type annotation resolves the class in `_init`, before the
first frame, where the `InputRouter` autoload does not exist — the class fails to compile, GDScript
caches the failure, and `taxi.tscn` instances a `RigidBody3D` with a **null script**. The run then
reports "no vehicle" while `WheelMount`, touching no autoload, is found perfectly. `driver.gd`'s
duck-typing is deliberate, not incidental.

**Consequences.** `HandlingProfile` loses `drift_grip_scale` and `drift_front_grip_scale`, gains
`handbrake_lock`. `builtin_vehicle_controller.gd` — the rejected `P0-5a` spike — now holds the two
retired values as frozen constants rather than reading a profile that has moved on, so it keeps
reproducing the run its findings were taken from.

**See.** `P0-5a` · `P0-5b/c/d` · `GAME_DESIGN.md` "Controls" · `PLAN.md` `B4` · `P3-2b`
