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
| `Q26` | Which look ships — the measured Hong Kong one or the clean/futuristic one? | 🔴 Open — a verdict, not a measurement |
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

**Status.** 🔴 Open, and **a verdict rather than a measurement** · **Owner.** `P3-9a`

**The question.** The measured Hong Kong look — `P3-7`'s accurate window bands, called dull — or
`city_facade_clean`, which is bolder and is *not* what Wan Chai looks like. A third candidate now
exists and is what currently ships: **elements off, flat per-building colour on accurate massing**.

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

**See.** `ART_DESIGN.md` "The clean/futuristic variant" · `Q27` · `Q30` · `Q31` · `Q34` · `Q37`

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

⚠️ **Nothing was shipped.** `clean_daylight.tres` is restored byte-for-byte. The tone curve is the
thing three drivers are about to judge `Q26` through, and moving it now would change the thing under
test — the contrast change waits on that verdict.

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

**Status.** 🟡 Open — **feasibility established, classifier not yet trustworthy** · **Owner.** `P3-9a`

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

### 🔴 The classifier is not trustworthy yet, and the sheet is why

34 faces over 10 buildings. Two artefacts, both found by reading the numbers rather than the images:

1. ⚠️ **A false `fin` from a missing measurement.** Seven faces report `floor 0.00 m, s = 0.00`, which
   is the vertical profile refusing to compute — *no usable measurement*, not *no banding*. The
   classifier reads `floor_s < WEAK` and calls it a fin. Absence of evidence laundered into evidence
   of absence, which is `Q31`'s confound wearing a different hat.
2. ⚠️ **Bay periods pinned at the band floor.** `1.38 m` recurs constantly and
   `int(1.4 × 8) / 8 = 1.375` — the autocorrelation peak is landing on the *minimum lag allowed*, so
   it found no bay and reported noise. Those faces must refuse, not measure.

**Both share one root: the classifier has four outcomes and no way to say "I don't know",** so every
failure to measure becomes a confident architectural claim. ✅ Real signal is present alongside them —
`B353771561001063A0` returns a **3.38 m floor pitch independently on three faces**, which is that
building's storey height measured from photography.

### Decided

- **Work in the world-space unwrap, never in atlas space.** Probe 3 is the reason.
- **Tint is 2-D, `L*` × `b*`, dropping `a*`.** PCA over the measured glass: PC1 68.9% (essentially
  `L*`), PC2 24.7% (the `b*` cool↔warm axis), PC3 6.5% (`a*`). A 1-D ramp would discard a quarter of
  the variance, and it is the quarter that separates bronze from blue.
- **The code rides `TEXCOORD_1` (`UV2`), not `COLOR_0`'s alpha byte.** Three grammars × 15 `L*` × 16
  `b*` is 720 states and will not fit in a byte; `facade_uv` already spends both existing channels
  (`UV.x` height, `UV.y` class + phase); and `Q27` makes `COLOR_0`'s sRGB/linear semantics somewhere
  to stay away from. ~2 MB over the region, and a `schema_version` bump on both sides.
- **Every gate refuses rather than guesses**, and a refusal falls back to the existing hash.

### Open

Fixing the two artefacts, then a validation sheet — elevations with the predicted grammar on each —
before any of the contract change is written. `Q32`'s "tint the class before naming it" is the rule
this is following; the sheet is the tinting.

**See.** `Q26` · `Q30` · `Q35` · `Q37` · `Q27` · `DATA_SOURCES.md` "Buildings"

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

## `P0-5b/c/d` — Four handling bugs no linter catches

**Status.** ✅ Done

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

**See.** `P0-5a`

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
motivated it.

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
