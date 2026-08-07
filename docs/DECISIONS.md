# Decisions

Every decision this project has taken, as a standing statement. **Keyed by ID, never by date** —
look a decision up by the `Q` or task ID the code already cites, not by when it was made.

`PROGRESS.md` holds live state: what is in flight, what is measured, what is at risk. Chronology
lives in git. This file holds *why things are the way they are*.

## How to write a record

- **No dates.** A date appears only where it is the fact itself — a licence term, a data vintage.
- **No narration.** Not "this was tried, then reverted"; state what is true and what is refused.
  Relations are `**Superseded by.**` / `**See.**` links between IDs.
- **Twenty-five lines is the ceiling.** A record that needs more is restating a spec.
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
| `Q35` | A per-building material draw gives a salt-and-pepper skyline | 🔴 Open |
| `Q36` | Wan Chai's ground is paving, not soil | ✅ Closed |
| `Q37` | 10.0% of the façade survey is atlas filler, not a photograph | 🔴 Open |
| `Q38` | `exposure_anchor` is baked into `COLOR_0` at build time | 🟡 Open, deliberately not fixed |
| `Q39` | `wall_sky_tint` is uniform, so a canyon wall takes a parapet's sky bounce | 🟡 Open |

Task and unnumbered decisions follow the questions, in ID order.

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

⚠️ **Every shot taken before `Q27` closed is unusable for this**, `build/driver/h4` and
`build/driver/clean` included, because albedo was reaching the screen at a third strength in all of
them. Re-shoot before comparing.

⚠️ **If the clean look wins, the palette moves** from the shader's `base_wash` into `height_bands` in
the city config, where CLAUDE.md says palettes live.

**Evidence that arrived late.** The source massing carries **real window reveals and structural fins
on a minority of towers**, so with the shader grid off the city draws surface three ways at once, and
the relief aliases into speckle at the distance it is seen from. That was not on the table when this
question was written.

**See.** `ART_DESIGN.md` "The clean/futuristic variant" · `Q27` · `Q30` · `Q31`

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
the graders, which match shipped vertex colours against `class_colours`.

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
per-building colour is `C*` mean 12.59, p90 27.35, p99 57.33, max 96.73, with **20.1% of 2,171
buildings over `C*` 20** against 3.9% at faithful strength 1.0. The palette table describes a city
that does not exist, and one building in five is more saturated than anything the direction sanctions.

⚠️ **The knob cannot fix this, which is the argument against tuning it further rather than for.**
Amplifying chroma linearly widens the spread far faster than it moves the middle, so at 2.0 the
distribution is *both* too grey (median 9.52) and too candy (p99 57.3). `strength: 2.0` also puts
**2.2% of surveyed buildings out of gamut, worst `dE` 61.5**.

**Options.** Drop toward 1.0–1.5; compress the tail rather than scale it; or re-author the palette
table around what ships. **Belongs with `Q26`'s verdict, not before it.**

**See.** `ART_DESIGN.md` "Palette" · `Q26` · `Q34`

## `Q31` — The city's value range has an empty middle

**Status.** 🔴 Open · **Owner.** `P3-9a`

**Claim.** Street frames come out bimodal. Causeway Bay in shade is **51.4% of pixels under `L*` 10
and 0.5% between 10 and 30**; under the HKCEC deck 28.9% and 2.0%. Half a street frame carrying no
information — and it is the frame the player occupies for the whole game.

⚠️ **The palette lever has been pulled and it was not the cause.** `Q33` re-placed the asphalt against
published albedo and it moved **+2.7 `L*`**, because `#3c3a37` was already claiming 8.2% reflectance
against aged asphalt's real 7–12%. Re-graded on the same two frames: shaded street under `L*` 10
**51.4% → 51.3%**, the 10–30 band 0.5% → 2.7%; Hennessy Road 13.2% → 13.0%.

🔴 **That leaves the shadow fill as the only untried candidate**, and the two failing frames are
still exactly the two shot *in shade*. It belongs in the owed rig pass, not in the palette.

**Corroboration from a second axis.** `Q36` reached the same rig pass on *hue*: `asphalt_aged` is the
frame's grey card at authored `C*` 2.14 hue 84.6 (warm) and rendered `C*` 7.05 hue **275** (blue), so
the rig adds ~7 `C*` of blue to everything and the below-horizon frame is 70.7% cool.

⚠️ **Both levers produce the same symptom on the lowest-albedo surface**, so change one at a time and
grade with `tools/frame_stats.py`. `Q27`'s ablation discipline applies. ⚠️ Do not simply raise the
fill: `ART_DESIGN.md` records that lowering it corrects the road and flattens the massing at once, and
raising it is the same trade on the same axis — which is true only while ambient is uniform. `Q39` is
the second consumer for a sky-visibility term.

**See.** `Q33` · `Q36` · `Q39` · `Q27`

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
preserved to within `Δab` 0.46: asphalt **+2.7 `L*`**, infrastructure −7.7, ground **−13.9**, kerb
**−19.4**. Kerb-to-road reflectance lands at 2.5:1, which is what concrete against asphalt is; it was
6.6:1.

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

**See.** `ART_DESIGN.md` "Material is not a function of height" · `Q33` · `Q35` · `Q37`

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

**Status.** 🔴 Open · **Owner.** `buildings.py`, survey

**Claim.** 222 of 2,214 rows in `facade_lab.json` carry `naive_rgb` and `lit_rgb` of exactly
`[128,128,128]` — `a* = b* = 0`, `clipped` 0.0005, and a *higher* median pixel count than the rest
(102,942 against 57,059). RGB(128,128,128) is independently observable as one of the fill colours in
the raw atlases. **The imagery also covers only a median 14.3% of each building's walls.**

**Why it matters.** It is the **same error class the survey already caught once and fixed** — *"a
texel at 255 is `a* = b* = 0`"* — at the other end of the range. 10% of buildings render dead-neutral
because they were *not measured*, and under `Q34` they also fall into the neutral-grey material bin,
so a material is assigned from absent data. `Q34` reports that bin at 36.3%; up to ten points of it
may be filler.

⚠️ **The fix is structural, not another entry in a list.** The guard has been wrong once already —
the first padding guard caught only pure black, and `#3c3c3c` **is** RGB(60,60,60), so (128,128,128)
is the *third* filler colour and the second miss. Enumerating them has failed twice. **Reject exact
`R == G == B` texels** — a photographic texel essentially never is — or detect each atlas's filler as
its modal exactly-repeated colour.

⚠️ **The survey script was never committed and is not in history**, so this is a reconstruct-and-
revalidate job, not an edit. The method: median of texels above the **65th percentile of `L*`**,
filler and foliage excluded, per-face `L*` retained. **Acceptance: 1,992 of 2,214 rows come back
unchanged** — anything less and every building's colour moves, invalidating `Q26`'s pending A/B,
`Q30` and `Q34`'s grading.

⚠️ **Averaging in sRGB is a second, separate question** worth settling in the same pass: ~4.9 `L*`
away from a linear-light mean, and the same family as the bug `Q27` closed. **Change one at a time.**

**See.** `Q34` · `Q27` · `Q30` · `Q26`

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
