# Decisions

Every standing decision, keyed by the `Q` or task ID the code cites — never by date. `PROGRESS.md`
holds live state and chronology lives in git; this file holds why things are the way they are.

## How to write a record

- A one-line `**Status.**` directly under the heading. There is no index table: the headings are
  the index (`grep -n '^## ' docs/DECISIONS.md`).
- No dates, unless the date is the fact (a licence term, a data vintage, a cited user approval).
- No narration. State what is true and what is refused; relate records with
  `**Superseded by**` / `**See.**`.
- One claim per record. It grows only by carrying another distinct ⚠️.
- Do not restate a spec another doc owns (`ART_DESIGN.md` the palette, `ARCHITECTURE.md` the
  contract). Give claim, reason, evidence, link.
- Keep the deciding number. A refusal without its measurement gets re-proposed.

---

# Questions

## `Q1` — Road Network v2 carries no Z, but `ELEVATION` encodes the level

**Status.** Closed · `P0-2`

Centrelines carry no Z. `ELEVATION` is an integer grade-separation level; `elevation_levels` in
city config maps each to an offset from the sampled ground (`Q11`). Ramps between levels are not
expressed (`Q13`).

## `Q2` `Q3` `Q5` — Building data is fully scriptable

**Status.** Closed · `P0-1`

The CSDI portal serves an index of 3,456 sheet polygons with direct download URLs and a per-sheet
`REVISIONDATE` (the cache key). One public key covers all sheets; never commit it. Vertices arrive
unwelded, so flat shading is baked in. Details: `DATA_SOURCES.md` "Buildings".

## `Q2′` `Q3′` — Two façade-probe findings that reuse numbers already taken

**Status.** ID collision, flagged rather than renumbered · `Q2′` superseded by `Q34`

- `Q2′`: height does not predict façade colour (6.1% of `L*`).
- `Q3′`: window period inconclusive — median 1.19 m against `P3-7`'s 2.77 m, pinned at the search
  floor.

## `Q4` — Device floor: A13 (iOS) and Adreno 618 (Android)

**Status.** Closed

iOS floor A13. Android floor Adreno 618 tier (Vulkan 1.1 with a maintained driver, 4 GB RAM), the
one that binds the budget: <150 draw calls, <300k triangles, <128 MB texture.

## `Q6` — Does the region need Central for the circuit to feel complete?

**Status.** Open, deferred to after `P3-9` · scope

A question for drivers, not a measurement. `Q21`'s tunnel portals resolve only if the region grows
east.

## `Q7` — Game-space origin is the region's north-west corner

**Status.** Closed

East is `+X`, north is `−Z`, zero at the region's north-west corner, which keeps tile indices
non-negative — provided content is clipped to the region before indexing.

## `Q8` — The city itself is the fun

**Status.** Closed · the user's verdict after driving the city

Driving an HK-like map is fun enough on its own. The verdict covers a first session only; "novelty
does not survive the first session" stays a live risk (`P3-9a`).

## `Q9` — Read the geodatabase, not the GML

**Status.** Closed · `P1-3`

Road Network v2 ships as a 17 MB file geodatabase and 539 MB of GML; the pipeline reads the
geodatabase only.

## `Q10` — Region-local origin plus a recorded `city_offset`

**Status.** Closed

Each region keeps a local frame; `city.json` carries its `city_offset`. One city-wide origin was
rejected: Wan Chai would sit ~38 km out, where float32 spacing is 3.91 mm. A city's declared
`bounds` never change — every offset is measured from them.

## `Q11` — Road heights sample the terrain height field

**Status.** Closed · `P1-3`

`elevation_levels` offsets are from the ground sampled from the downloaded terrain
(`roads.ground: terrain`). Level-0 median 4.21 m against building bases at 4.29 m. Rejected:
nearest building bases (podiums), one offset per region (55 m of relief).

## `Q12` — The source's one-way directions match the street

**Status.** Closed · the user's verdict on the road-graph preview

`TRAVEL_DIRECTION` plus digitised vertex order matches the street, so routing uses the source
unchanged. One street was checked. Two-way roads can arrive as opposed one-way carriageways.

## `Q13` — All 36 mixed-level nodes are ramps

**Status.** Largely answered · residual is `P4-1`'s

Every node joining two levels is a real ramp (zero plan-coincident crossings), so `ELEVATION` never
keys nodes. Touchdowns are ramped (`Q90`); level 1 is open to the player (`Q103`, `Q108`, `Q110`);
level −1 stays closed. Open: the 5 tunnel portals. `e425`'s stub is closed and node 269 MARSH
ROAD landed (`Q264`).

## `Q14` — Taxi-stand operating-time restrictions are discarded

**Status.** Open, deferred · `P3-1`

`Status_EN` carries operating-time restrictions the fare stage drops, so a part-time stand is
full-time. Needs a schema bump and a parser.

## `Q15` — Fare nodes snap by plan distance only

**Status.** Closed 2026-11-21 · `P4-1`, `P4-2` · reopens on a fare point at deck level

Fare points are 2D, so `fares.build_region` snaps only to `elevation_level == 0` edges, as
`kerbside.py`, `tramway.py` and `arrows.py` do.

- `FareReport.off_grade_nearer` counts points with an off-grade edge nearer than their host;
  `export.py`'s `_check_fares` reads `elevation_level` strictly.
- The runtime half shipped with `P4-1`: `RoadGraph.nearest_edge` takes the nearest edge within
  `LEVEL_REACH_M` (2.5 m) of the query's height and falls back to plan distance only when none
  is, which is `P4-2`'s accept. Nothing was left to build.
- Deciding number: 1 of Wan Chai's 48 points and 0 of Causeway Bay's 7 have an off-grade edge
  nearer than their host — `f_032`, by 0.80 m, under the Canal Road Flyover, where a taxi cannot
  stop; Hennessy Road is its right host. No point in either region belongs on a deck.
- Reopens: a region with a stand at deck or podium level; `off_grade_nearer` is the counter.
- Refused: an `at_grade:` config key — a typo silently restores the defect.
- Trap: a claim measured on one producer goes stale when a stage gains a second.

## `Q16` — LOD0 does not ship

**Status.** Closed · `P2-1`

The exact-weld tier is dropped: `lod_cell_sizes_m: [1.5, 4.0]`, 250 m band edge, 400 m unload.
PCK −59%, worst-case visible triangles −40%. `tiles[].aabb` is the union of the shipped tiers (a
coarser tier can stand taller); `verify_city.gd` checks it.

## `Q17` — CI runs `tools/check.sh` and cannot check the generated assets

**Status.** Closed

Two jobs: `ruff` + `pytest` on Python 3.11 and 3.13, and `tools/check.sh` against a pinned Godot.
Generated assets are gitignored, so CI sets `VERIFY_GENERATED=0` (only an exact `0` skips);
region-free verify tools still run. Running the ETL in CI is declined (320 MB per push). The
`godot` job uses no pip cache.

## `Q18` — Ground colour sits under a chroma knee, and the classifier is refused

**Status.** Closed · chroma value superseded by `Q36` · `P3-10`

`ground_sink_m: 0.20` clears the carriageway. Refused: a land-cover classifier from the orthophoto
— its water class is shadow (51.1% on rooftops) and its vegetation class edge speckle. Parks come
from vector polygons (rule `basemap`).

## `Q19` — Solid geometry stands in the drawn carriageway

**Status.** Structure half carved (`P3-28`), car-bar fence built (`P3-29`), on the user's call of 2026-08-31 · building half open and unowned · drives owed (the fence mouths, `e99`, `e207`)

Rules `clearance`, `carve`, `fence` and `ground_clearance` own the checklists.

- Gate: a clear corridor ≥ `lane_width_m` (3.20 m) along every drivable level-0 edge, graded by
  `tools/carriageway_occupancy.py` from the shipped bundle.
- Two bars, never merged: the lane decides routing (`is_passable`); the car
  (`clearance.car_width_m`, 1.695 m) decides whether the player is stuck (`fits_car`).
- The grader and `clearance.json` are two populations; `tools/clearance_reconcile.py` holds the
  difference.
- Carve (`pipeline/carve.py`, `carve.json`): the prism is the surveyed span, never the drawn floor.
  `e99` FLEMING ROAD and `e207` CANAL ROAD EAST are carved at an `authored` width, each on the
  user's report. The stage raises on a second pass (`carved_edges` marker).
- `e207` (2026-11-18): three piers of the `e257` ramp stood in a 5.0 m kerb-to-kerb lane, 100%
  `INFRASTRUCTURE`. Corridor 1.95 → 4.96 m (`corridor_truth.py`); 141 triangles, 93.8 m², no other
  `carve.json` row moved; reconcile ratchet 28 / 32 / 8 → 27 / 31 / 8. The ramp is left
  unsupported there, and traffic now routes down the edge.
- Fence (`pipeline/fence.py`, `fence.json`): every drivable level-0 edge under the car bar ends at
  a colliding barrier; closing them cost 0 routable pairs.
- Structure between suspension travel and the bumper floor is graded, not gated, by
  `tools/ground_clearance.py`.

Refused:

- Narrowing the ribbon: 1.60× → 1.30× clears 0 edges and loses 2.
- A centreline shift: sourced shifts 0.02–0.88 m against 1.43–4.49 m needed; clears 0 edges.
- Consuming `structure_bounded` (published, no consumer): drove three edges to 0.00 m clear.
- A vertical term in `clearance:`: fenced 3 ribbons resting on their own structure, missed `e99`.
- Widening a carve prism: the grader bins at 1.0 m, so width `w` reads ~`w − 2`.

Open: on 13 of 15 building-half edges the centreline is inside a `BUILDING`; no width rule reaches
them and nothing licenses carving a building.

## `Q20` — Deck heights are sampled from `INFRASTRUCTURE`

**Status.** Closed · `P2-7`

Off-grade carriageway height is sampled from the `INFRASTRUCTURE` the tiles ship, which is also the
collider. |error| p90 0.095 m against a 0.50 m criterion (`tools/deck_error.py`). Rule `deck`.

## `Q21` — Should level −1 carriageway be drawn at all?

**Status.** Open · Phase 4

15 edges, 5,010 m, drawn under the terrain where nothing sees or drives them. Heights cannot
improve (a tunnel is a void; ends are clipped at the boundary) unless the region grows east.
`e489` has 0.22 m of headroom at worst.

## `Q22` — Off-grade carriageway hangs past its structure

**Status.** Open · Phase 4

Part of the off-grade ribbon overhangs its deck (`tools/overhang.py`, `tools/deck_margin.py`).
Refused: extending the carriageway survey off-grade — publishers license 5 of 45 edges and their
2D lines find the street under the deck (`Q103`).

## `Q23` — Carriageway width is a property of the station, not of the edge

**Status.** Closed · `P2-7`

Width is decided per station. The elevation-level rule applies first, then the per-station
structure test, blended over `structure_taper_m: 15.0`; the order is load-bearing. The widening is
a floor since `Q95`. `roadgraph.json` carries per-vertex `on_structure`.

## `Q24` — The at-grade road follows the ground

**Status.** Half closed; the other half is `Q19`'s

`roads.ground_profile` densifies at-grade edges, samples the terrain and thins at 0.10 m vertical
error. The ribbon stays flat across its width. `tools/ground_clearance.py` gates on the count of
edges with ground proud past suspension travel. Refused: a per-station cross-tilt (proud area
0.60% → 0.54%, two edges worse).

## `Q25` — Ground is decimated once per tier and cut afterwards

**Status.** Closed · `P1-2` / `P3-10`

`_tile_ground` merges the region's ground, decimates once per tier, then cuts; cutting first tears
the sheet at tile boundaries (holes near a boundary 15.65% → 0.42%). Clip to the region plus a
one-tile margin before merging.

## `Q26` — Which look ships?

**Status.** Closed 2026-08-17, the user's call — candidate `C` ships. `P3-9a` can reopen it.

`C` (`city_facade.tres`) is accurate massing with flat per-building colour.
`city_facade_elements.tres` (`A‴`) and `city_facade_warm.tres` (`B`) are kept; `cp` swaps a look.
Later layers: `Q158`, `Q240`.

- Reopen condition, fixed in advance: drivers reject the city and attribute it to flat surface.
- Grade façade-detail work against `city_facade_elements.tres`; under `C` it passes trivially.
- Shoot preview frames twice and `cmp`.

## `Q27` — `COLOR_0` is authored sRGB and must be linearised by the consumer

**Status.** Closed

The ETL writes `COLOR_0` as sRGB bytes and every consumer shader converts. Refused: writing linear
`COLOR_0` (linear `uint8` starves the shadows and breaks colour-matching graders).

## `Q28` — A per-object seed must be `flat`

**Status.** Closed

`TEXCOORD_0.y` packs `surface_class + phase`; the façade shaders' `phase` and `marker` varyings are
`flat`, or the seed stripes inside flat triangles.

## `Q29` — The ground's normals are rebuilt in the fragment stage

**Status.** Closed

The façade shaders rebuild the ground normal from view-space position derivatives, gated on
`MARKER_GROUND`. Take the derivative outside the branch; orient with a comparison, not `sign()`.

## `Q30` — The shipped façade palette is not the one `ART_DESIGN.md` authorises

**Status.** Open, widened deliberately 2026-09-08 · `Q26`

At the shipped `facade_hue.strength: 3.0` (the user's pick, `Q38`), 35.2% of buildings are over
`C*` 20 and 24.8% under `C*` 8; 7.8% fall outside sRGB. No `strength` fills the middle. Measure
with `tools/facade_chroma.py`. Undecided: lower `strength`, compress the tail, or re-author the
palette table.

## `Q31` — The city's value range has an empty middle

**Status.** Open, cause measured · `P3-9a`

Shaded street frames are bimodal. The tone curve was the cause; `adjustment_contrast` 1.00 ships
(user, 2026-08-20). What remains is a uniform shadow mass, which needs a sky-visibility bake. Quote
shadow-mass `L*` and within-mass sd, never band share.

## `Q32` — `INFRASTRUCTURE` is *not* the brightest large object in its frame

**Status.** Closed as wrong

Tinting `MARKER_STRUCTURE` refuted the claim (2.71% of its frame). A `structure_soffit_darkness`
term was built, measured and reverted; do not re-propose.

## `Q33` — Every authored colour is `material reflectance × exposure_anchor`

**Status.** Closed · mechanism superseded by `Q38`

Every authored colour is a cited diffuse reflectance, checked config-wide by
`config.py:_check_reflectance` against each material's `bounds:`. A colour outside its bounds
moves; the bounds do not.

## `Q34` — Material is declared, not implied from height

**Status.** Closed

A top-level `materials:` table holds every shipped colour; `material_assignment` draws per building
over authored chroma rings and hue sectors (height explains 0.9% of surveyed `L*`). The fallback
is the height ramp, so a survey-less clone builds. Bin by authored thresholds, never k-means.
Refused: material from imagery (glass would render near-black).

## `Q34′` — The ring weights are re-derived by a tool, against `Q37`'s survey

**Status.** Closed by `tools/ring_weights.py`

Each bin's weights are the minimum-norm move that matches the height ramp's mean reflectance.
Re-run the tool when the ramp or the survey moves.

## `Q35` — A per-building material draw gives a salt-and-pepper skyline

**Status.** Open

Neighbours draw independently, up to 13 reflectance points apart. Candidates, none scouted: a
spatial hash on position, a block join from a lot dataset, or accept it.

## `Q36` — Wan Chai's ground is paving, not soil

**Status.** Closed

The ground material is `concrete_paving` at 20.0% reflectance. Do not simplify toward neutral
grey. Refused: terrain hue from the aerial JPEG (baked shadow) and a hillside split (0.000% of the
audit viewpoints).

## `Q37` — 10.0% of the façade survey is atlas filler, not a photograph

**Status.** Closed by `tools/facade_survey.py`

The survey rejects atlas filler structurally — exact `R == G == B` texels or the atlas's modal
repeated colour — never by a list of greys. Imagery covers a median 14.3% of a building's walls.
Rule `facade`.

## `Q38` — `exposure_anchor` is baked into `COLOR_0` at build time

**Status.** Closed 2026-09-08 by `P5-28c` — the exposure is a global shader parameter set by the lighting rig

- `lighting_rig.gd` sets the `exposure_anchor` global; `clean_daylight.tscn` and `golden_hour.tscn`
  hold 0.52. It does not move with the hour (`Q160`).
- Shaders apply it after linearising `COLOR_0`, never to a `.tres` colour.
- `materials:` colours are reflectance-level; `bounds:` is required and is the whole check.
- Traps: the jitter clamp in `colour_for` runs after `with_hue` and no counter sees it;
  `clearance.wears()` aborts if ground brightness or jitter passes its exactness guard; an
  unexposed grader reads 1.24× more saturated (`facade_chroma.py --shipped`).

## `Q39` — `wall_sky_tint` is uniform across the city

**Status.** Open · `Q31`

`city_facade_clean.gdshader` has no occlusion term on the sky reflection. Fixed for free by `Q31`'s
bake. Do not lower `wall_sky_tint` globally; it flattens the massing.

## `Q40` — Can façade grammar be surveyed instead of hashed?

**Status.** Closed · consumer withdrawn by `Q102`

Measured shut for per-pixel statistics: grammar from an `L*` profile (12 faces: 1 right, 8 wrong);
a bimodality gate for glazing (best Youden J 0.100); per-chart atlas analysis (15.2% of wall area
usable). `tools/facade_unwrap.py` and `tools/facade_glazing.py` are kept with no consumer.

## `Q41` — A vision reader recovers the grammar the statistic could not

**Status.** Superseded by `Q102` — withdrawn on cost at the user's call, not refuted; the reader and the `TEXCOORD_1` codec are deleted.

---

# Tasks

## `P0-1` — Building data is fully scriptable

**Status.** Done — see `Q2` `Q3` `Q5`.

## `P0-3` — A scaffold is not a signed on-device build

**Status.** Done · `P0-3b` in progress (needs two floor handsets)

`P0-3b` is signed on-device builds and blocks the `P2-4` and `P2-6` reviews.
`rendering/textures/vram_compression/import_etc2_astc` must stay enabled or arm64 exports fail.

## `P0-4` — Config declares its datum, not just its CRS

**Status.** Done

`hong_kong.yaml` declares `crs.geodetic` beside `crs.projected`; HK1980 and WGS84 differ by ~304 m
here. `always_xy=True` everywhere; the origin is rounded to whole metres. Elevation-level keys
reject `bool` (YAML reads `off:` as `False`, which equals `0`).

## `P0-5` — The grey box cleared the handling and could not clear the premise

**Status.** Passed, conditional — the premise question became `Q8`, since closed.

## `P0-5a` — Custom raycast on `RigidBody3D`, not `VehicleBody3D`

**Status.** Reversed by `Q50` — the shipped car is `VehicleBody3D`, with its own tyre force since `Q152`.

Still true: `VehicleWheel3D` friction is isotropic. The glTF importer makes a `VehicleWheel3D` from
a mesh name suffix alone.

## `P0-5b/c/d` — Five handling bugs no linter catches

**Status.** Done · numbers superseded by `Q50`

- `rolling_resistance_mps2` is capped at the deceleration that lands on zero this tick.
- A `Node3D`-typed `@export` does not resolve from a hand-authored `.tscn`; it reads null.
- Measure drag and braking on `skidpad.tscn`, never on the city: a 0.14° gradient is the whole
  quantity under test.

## `P1-1` — The fetcher derives its own sheet list

**Status.** Done

`fetch.py` intersects the region bounds with the sheet index; config names no sheet. Fetch-once: a
re-run must not adopt upstream's new month. Everything recorded passes through `redact()`. A short
response is checked against its declared length; selecting zero tiles is an error.

## `P1-2` — Vertex clustering, and meshes are assigned to tiles whole

**Status.** Done

- Buildings are decimated by vertex clustering (facing in the key, representative position) and
  assigned to tiles whole; oversized meshes (viaducts) are partitioned by triangle.
- The post-import script sets `vertex_color_use_as_albedo`, and the colour accessor's
  `"normalized": true` is load-bearing; either failure renders the city white.
- No glTF library: `pipeline/gltf.py` reads and writes the format.

## `P1-3` — Three things the source forced on the road graph

**Status.** Done

- `ELEVATION` must not key nodes (`Q13`).
- Roads are clipped to the region; the geodatabase filters on bounding box only.
- No layer carries a lane attribute; `lanes` is measured (`Q94`).
- Snapping must be no finer than a millimetre.
- Centrelines are over-densified, so Douglas–Peucker is a correctness measure.
- `EDGE1END` is a hint (4 of 217 wrong); take the shared node.
- The turn layer's vehicle-type and part-time fields are dropped; one restriction excludes taxis.

## `P1-4` — The road surface is one mesh, capped per level, never merged

**Status.** Done · widths and rails moved to `Q95` / `Q129`; rule `surface` owns the ribbon.

Junction caps are per elevation level. Kerbs mitre through the cap: two arms up to 90°, three or
more up to 45°. Refused: capping width to the turning radius (pinches to zero at 24 places) and
merging opposed pairs into one ribbon.

## `P1-5` — Fare nodes keep the kerbside position

**Status.** Done

`pos` is the source kerbside position, not snapped; only the height comes off the road. The
`Status_EN` category table is first-hit-wins, so rule order is load-bearing. `clean_text`
normalises to NFC, not NFKC (full-width brackets in HUD names).

## `P1-6` — The manifest names the other documents, and the export stage checks them

**Status.** Done

`city.json` references separately versioned documents; `bounds_game` is the union of the content.
The export stage validates cross-document facts. A rebuild is byte-identical apart from
`generated_utc`.

## `P1-7` — The manifest is the only route to the tiles

**Status.** Done · Phase 1 gate passed

`DirAccess.get_files_at` returns nothing in an exported build, so tiles are found through the
manifest. `verify_city.gd` holds each mesh to its recorded `aabb`. `sync_generated.sh` copies what
`city.json` names and deletes the rest.

## `P2-1` — The city streams, and LOD is per mesh class

**Status.** Done — review passed

`CityStreamer` loads tiles on a worker thread by published `aabb`. `class_lod_cell_sizes_m` holds
`INFRASTRUCTURE` at `[0.5, 1.0]`, because clustering merges a thin deck's top into its underside.
Resident triangles are reported, never gated; the budget is 300k visible.

## `P2-2` — Publish the derived width, not the widening rule

**Status.** Done — review passed

`surface.py` records the half-width it draws and `export.py` carries it into `city.json`; the rule
itself is not published. Level 0 follows `Q129` (rule `region`). `RoadGraph.shared()` is a weak
cache; hold it in a member. `str(null)` is `"<null>"`.

## `P2-3` — The start line is queried, not written down

**Status.** Done — review passed

`RoadSpawn.at_fare_node` resolves a fare node through `RoadGraph`; the street decides the heading.
Autoloads are not registered under `--script`, so `check.sh` greps stderr.

## `P2-5` — Buildings get collision from a mesh name

**Status.** Done — review passed

A mesh named `<tile_id>-col` becomes a `StaticBody3D` trimesh at import; `verify_tiles.gd` asserts
both directions. Rule `tiles`. `P2-6` owes a hitch measurement.

## `P2-7` — The off-grade carriageway lies on its structure

**Status.** Done — review passed

Claim `Q20`, width `Q23`, ramps `Q13`, checklist rule `deck`. Deck sampling takes slab clusters
plus continuity; an uncovered station interpolates. `deck.clearance_m: 0.20` is a wearing-course
layer. The graders need a built region and are not in `check.sh`.

## `P3-7` — Window bands are procedural, and the storey height was measured

**Status.** Awaiting review

Façades are banded in world space from a surface marker and per-building phase in `TEXCOORD_0`,
drawn through `city_facade_clean.gdshader`. `floor_height_m` 2.8 is measured (median 2.77 m;
`Q48`). The glTF material name `city_facade`, the import dispatch and the shader must agree;
`verify_tiles.gd` asserts it.

## `P3-7a` — The task closes at what was judged, and the riders are gated on the look

**Status.** Closed as shipped (`Q44`, `Q45`) · the continuation is superseded by `Q102`

## `P3-10` — The ground is a mesh class, and it collides

**Status.** Awaiting review

Terrain is one more entry in `buildings.classes`; any class added there inherits collision.
`ground_sink_m: 0.20` is the shallowest value passing both gates (carriageway area proud 3.3%
against 5.2% at 0.15). Do not deepen it to fix residual proud ground (`Q24`).

## `P3-11` — The taxi is generated, and the chassis generates it

**Status.** Passed review 2026-09-06

`tools/make_vehicle.py` generates the taxi meshes around the wheel hardpoints in `taxi.tscn`; the
scene is the authority. Rounded by chamfer, never smooth shading. The visual body is larger than
the box collider. Re-import after rewriting a `.glb`.

## `P3-6` — Two heroes replace their source meshes, and the contract is the deliverable

**Status.** HKCEC passed the user's review 2026-09-06 · two of five shipped · Central Plaza not yet judged; Hopewell, Times Square and the government slabs not built

- `landmarks.json` is assembled by `export.py` from the config's `landmarks:` block, keyed by
  building stems; `rot_y_deg` is a compass bearing.
- Exclusion is enforced twice: `export.py --check` (identity) and `verify_landmarks.gd`
  (geometry). `export.py` adds each `excluded_bounds` back into `bounds_game`.
- Central Plaza is generated and committed (`tools/make_landmark.py`). HKCEC is the source mesh
  repainted by `pipeline/landmarks.py` from a `source_paint` block (user's call, 2026-08-12):
  government-derived, never committed.
- Landmarks are always resident, outside the streamer.

---

# Standing decisions

## Foundations

**Status.** Standing — the table is `CLAUDE.md` "Locked decisions".

Also standing: targets are mobile plus desktop/Steam; Wan Chai must be standalone-playable; the
performance escape hatch is GDExtension, not C#.

## Region bounds are WGS84, by measurement

**Status.** Standing.

The bounds in `hong_kong.yaml` are WGS84; read as HK1980 (~304 m off) they select different sheets.

## Licensing

**Status.** Standing — `LICENSING.md` is the policy.

Contributions are inbound MIT because store builds need a proprietary grant from one owner. Do not
re-raise: the grants lack "adapt"/"modify" — for artistic works the restricted act is copying,
granted as "reproduce". Landmark depiction is the top item for legal review.

## Genre direction

**Status.** Standing.

References: *Crazy Taxi* (the fare loop), *Midtown Madness 2* (real shortcuts), *Forza Horizon*
(losable style chain), *Burnout 3* (traffic as reward), *Art of Rally* (flat-shaded terrain). No
open-world structure survives a 1.5 km² region. Refused: randomised rewards, live service,
licensed-car collection, scattered absurd ramps.

## `P3-11c` — Gloss is priced per surface, and the gradient is what sells it

**Status.** Awaiting review · paint gloss superseded by `Q215` (the engine's clearcoat)

`vehicle_body.gdshader` gives glazing, lenses and paint their own gloss over a shared sky gradient.
`floor(UV.y)` is the surface marker (`PAINT` / `GLASS` / `LAMP` / `TRIM`) and `UV.x` the lamp
circuit; never `COLOR_0.a`. Refused: uniform low roughness on paint (red `C*` 79.06 → 70.08).
Only a render plus `grep -i "shader error"` proves the shader compiled.

## The reflection needed a gradient, and strength was never the variable

**Status.** Part of `P3-11c` — the reflected ray's elevation picks sky or ground; the gradient is yaw-blind.

## The clearcoat, and the correction it forced

**Status.** Superseded by `Q215`.

## Fresnel is not decoration here, and tightening it refunds a fifth of the price

**Status.** Part of `P3-11c` — `fresnel_power` ships 6.5.

## The sun glint, and why `SPECULAR` could not be it

**Status.** Part of `P3-11c`.

The glint is `pow(dot(bounced, sun_toward), glint_sharpness)`; raising `SPECULAR` was refused as a
wash. `sun_glint.gd` feeds `sun_toward` from the scene's real `DirectionalLight3D`, found from
`get_tree().root`. Before a second vehicle uses it, make `sun_toward` a global.

## `P3-11d` — The lamps switch, and that is what finally separates the red lens

**Status.** Passed review 2026-09-06 · front lamps superseded by `P3-11e`

`floor(UV.x)` is the switched circuit. `LAMP_CIRCUITS` is keyed on full part names and
`_check_wiring` raises in the generator. Circuits are `instance uniform`s because
`vehicle_body.tres` is shared. `lamp_emission` 1.6 is the knee; higher desaturates the lens.

## `P3-11e` — The front lamps answer to the light, not to the driver

**Status.** Awaiting review · the night path runs under `Q160`'s cycle

- A `SUN` / `SHADOW` / `DARK` ladder from two raycasts: side lamps in shade, main beams under
  cover or at night. A night rig dims its key light, never deletes it.
- Beams read the lighter of held and current state; lenses the held state. Off means hidden.
- Forward Mobile pairs at most 8 spot lights per object; the 9th is silently absent.
- `spot_angle` is a half angle; the cone must not reach above horizontal.

## `P3-11f` — The roof sign lights, and it is the one lens that must not bloom

**Status.** Awaiting review

The roof box is a switched lens at `sign_lit` 0.45, under the glow threshold (~0.63). It answers
to `for_hire` (`P3-48`), not the light ladder.

## `P3-48` — The fare shows on the car: the sign goes out with a passenger aboard, and the rear kerbside door swings

**Status.** Awaiting review · the user's drive owed

`VehicleLamps.for_hire` gates the roof sign: out at `boarded`, back at `delivered` / `bailed`. The
rear kerbside door (`DRIVES_ON_LEFT`) opens from `hailed` to `boarded` and at a drop. The doorway
is cut out of the flank, `bevel_m` deep and no deeper. Presentation only (`TaxiHire`, `TaxiDoor`).

## `P3-49` — The skills pay as they happen, the delivery is a receipt, and the passenger's face says so

**Status.** Awaiting review · the user's drive owed

`SkillTracker` pays each skill as a dwell meter while a passenger is aboard; delivery banks
`meter + tip`, a bail pays none (`Q145`). Slip is computed twice on purpose (`Q84`). Values:
`skills.tres`; rule `fares`. The passenger's face is an unshaded mesh (`tools/make_emote.py`).

## `BeamBudget` — the eight spot lights are rationed by distance, not by pair order

**Status.** Shipped

`BeamBudget` (autoload, `beams.tres`) grants thrown beams to the rigs nearest the camera; lenses
still light on a denied car. `verify_beam_budget.gd` runs in `check.sh`. Open: the player's slot is
not reserved.

## `verify_vehicle.gd` — the import and the scene are the half no test could see

**Status.** Shipped

Holds the silent channels from ETL to shader: the glTF material name, the `instance uniform` names,
the `UV` payload, the rig's node paths. Runs in `check.sh` outside `VERIFY_GENERATED`. It cannot
tell that the shader compiled. Grades `taxi.tscn` only.

## Two shadow cascades at 400 m, not four at 600

**Status.** Standing.

2 PSSM cascades at 400 m; frame primitives −35% against four. One cascade was shipped and
withdrawn (shadows fade mid-street at 150 m).

## Debug chrome: one owner, one key, off by default

**Status.** Standing.

`DebugHud` autoload owns every dev readout. `F3` cycles `off → minimal → full`; `--debug-view=`
sets the start; off by default. The toggle is a raw key, not an action.

## The vertex stream carries both ground and building colour

**Status.** Standing.

Colour rides `COLOR_0` on untextured meshes merged per tile. Refused: shipping the terrain
orthophoto (+1 draw call per tile, baked roads). Per-vertex payload goes in `TEXCOORD_0`, not
`COLOR_0.a`.

## The audit viewpoints

**Status.** Standing.

Fixed cameras cover every shipped mesh class (`ART_DESIGN.md` "The audit viewpoints"). Changes are
graded against these, never a fresh camera.

## Rendering proposals: eight evaluated, two survive

**Status.** Standing — the refusals are measured shut.

Surviving: `Q31`'s ambient fill, then a sky-visibility bake (`Q39`). Refused:

- Real-time GI, planar reflections, SSR: absent from the Mobile renderer.
- Wet-material overlay: anti-goal.
- An unclustered LOD0 for UVs: 30.5 MB and 40% of visible triangles (`Q16`).
- Low-res terrain orthophoto: baked illumination, +53 draw calls.
- `VEGETATION(TB)` / `GENERIC`: 1.52 M and 3.95 M triangles, one welded blob per sheet.
- Glazed-vs-solid from imagery: 14.3% of wall area is photographed (`Q37`).

## `Q42` — The reader answers seven questions nobody consumes

**Status.** Moot — superseded by `Q102`. The reader's `signage` field returned real trademarks; never ship them as rendered text.

## `Q43` — `glazed` is materiality; `fenestrated` is geometry

**Status.** Closed — the split stays after `Q102`

In `city_facade_clean.gdshader`, `fenestrated` means the wall has openings and `glazed` that they
are mostly glass; merged, the grid zeroed on 39.3% of wall vertices. The `draws_detail` early-out
tests `fenestrated`.

## `Q44` — A punched opening is glass, not a black hole

**Status.** Closed — user accepted 2026-08-09

`unglazed_glassy` (0.65) floors per-building glassiness. Bar: whole-frame mean `C*` cost against
`C` stays ≤ `A`'s on the audit cameras (`street` +1.16 ≤ +2.28).

## `Q45` — One pane palette across the city reads as wallpaper

**Status.** Closed — user accepted 2026-08-09

`pane_l_jitter` 6.0 and `pane_b_jitter` 4.0 jitter the hashed pane tint; `pane_hue_pull` 0.25 pulls
it toward the building's own chromaticity. `linear_to_lab()` mirrors `etl/pipeline/colour.py`.
Retunes are bounded by `Q35`.

## `Q46` — A grammar refusal draws a quiet tier, not invented fenestration

**Status.** Superseded by `Q102` — the `quiet_*` uniforms were deleted with the reader.

## `Q47` — A committed verdict is right about the tower, wrong about the ground band

**Status.** Closed in part — the survey half is moot (`Q102`); the data line ships as a cornice (`Q195`).

- iB1000's `Building` layer (EPSG:2326, mPD) carries podiums: `TYPEOFBUILDINGBLOCK` `T` / `P` /
  `OS` / `TS`, `BASELEVEL` / `ROOFLEVEL`, `CERTAINTY`. The `podiums` stage writes `podiums.json`;
  the tower join is polygon overlap, depth-gated at 0.3 m.
- `P` is a partial classification (Central Plaza has none): absence is not "no ground band".
- Refused: survey `podium_floors` → metres. Bar p50 ≤ 2.8 m, graded 10.76 m, Spearman ρ 0.076.

## `Q48` — A contrast ratio measures banding where an `L*` profile could not

**Status.** Open as a candidate — nothing built, nothing scheduled (`P3-7a`).

- `contrast = L(band sample) / mean(L(sample ± pitch/2))`, median per strip, veto at 0.9.
- Usable only as a one-way veto (the photo may remove bands, never add). It fails on periodic
  blank walls and glass reflections and cannot find a pitch. Evidence is n=1 (HKCEC), by eye.
- Unreconciled: shipped `floor_height_m` 2.8 sits ~16% below three instruments agreeing within 3%
  (3.28–3.38 m; `Q40`, `Q42`, `Q47`).

## `Q49` — A tyre spends one budget, and the handbrake that follows spins the car

**Status.** Superseded by `Q50`, then `Q152` — the raycast model and its friction ellipse are deleted.

Trap that survives: a `--script` tool must not name `VehicleController` (it resolves before the
`InputRouter` autoload exists and the taxi instances with a null script).

## `Q50` — The shipped car is Godot's `VehicleBody3D`, and `P0-5a` was right

**Status.** Shipped 2026-08-18 on the user's instruction, reversing `P0-5a`; the tyre force is `Q152` / `Q153`'s since.

- The taxi is a `VehicleBody3D` with four `VehicleWheel3D`. The reversal was by instruction, not
  re-measurement: `P0-5a`'s finding reproduces.
- `wheel_friction_slip` is isotropic, so it cannot break lateral grip while keeping traction.
  Hence `TyreVehicleController` (`taxi_tyre.tscn`, `tyre.tres`) applies its own tyre force.
- Trap: `Object.set()` on a missing field is a silent no-op; a sweep checks the field with `in`.

## `P3-9a` — The build is threaded, so the host is not a free choice

**Status.** Closed — round 0 ran (`P3-9a′`); the rules below stand for any web cut.

- The `Web Demo` preset has `variant/thread_support=true`, so the page needs
  `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`.
  That rules out GitHub Pages. Host: itch.io ("SharedArrayBuffer support"). Local:
  `tools/serve_web.py`.
- Do not turn threads off for a graded round: single-threaded web is a different frame budget.
- Before sending a link: `tools/check.sh` green, a scripted drive with 0 `SHADER ERROR`, Chrome
  over the real headers with 0 console errors.
- Trap: the zip is hand-packed (`tools/export.sh` has no zip step) and has gone stale twice.
  Compare its mtime with `build/web/index.pck`, and name each cut anew.

## `Q51` — Traffic is never sent down an edge a car cannot fit through

**Status.** Closed (`P3-3`); the `MAX_SUBDIVISIONS` smear is still owed.

`pipeline/clearance.py` publishes a clear corridor width per carriageway station in `city.json`;
`RoadGraph` reads it as `is_passable` / `is_routable`. It measures, it does not clear (`Q19`).

- Expressed, never enforced: `nearest_edge` still answers on a blocked edge.
- `tools/carriageway_occupancy.py` stays the grader, never published. The two share a formulation,
  so they are not independent; `tools/clearance_reconcile.py` ratchets both counts. They differ by
  plan cell size (`e132`: 0.98 m in 1.00 m cells, 4.00 m in 0.25 m cells). Both defaults stay.
- `ALONG_M = CELL_M` (0.5 m) makes a published width a lower bound. Refused: 0.25 m — one more edge
  for 1.088 GB peak RSS against 789 MB.
- Refused: a blanket margin on `is_passable` — it needs a 5.00 m bar, refusing 37 edges to cover 6.
- Owed: triangles that hit `MAX_SUBDIVISIONS` block by their plan box at whole height range
  (`e702` reads 0.75 m against the grader's 3.41 m).
- Traps: a station the ribbon never reached publishes `-1.0`, not `0.0`. Sample along the edge,
  never at polyline vertices. Committed hero meshes are occupiers too.

## `Q52` — The start line says what it is standing in, and the check is what refuses

**Status.** Closed (`P2-3`).

- `RoadSpawn.Pose` carries the clear width at the start line and `Pose.blocked`. The harness warns
  and places the car; `verify_spawn.gd` fails. It reports, never relocates: the spawn is a
  published TD taxi stand.
- The bar is the segment the car stands on, not `is_passable` (the whole edge's minimum).
- Trap: `NOT_MEASURED` (`-1.0`) sorts below every real clearance; a plain `minf` silences the
  guard.

## `Q53` — Markings are drawn, arrows are not, and the difference is data

**Status.** Closed (`P3-12`); scope amended by `Q57`–`Q59`, draw switches by `Q125` / `Q132`.

`road_markings.gdshader` draws in lane space: `TEXCOORD_0.x` is a lane coordinate (0 at the
nearside kerb, `lanes` at the offside), V is metres along; `TEXCOORD_1` is a packed codec in `x`
and the edge's drawn length in `y`. No texture.

- "No marking data in any source" was false (`Q56`, `Q57`). Never conclude "no source" from Road
  Network v2 alone. Orthophoto markings stay refused on registration (`Q18` / `Q36`).
- `fade_m` 6.0 hides the cap overlap onto arms (worst 4.21 m); 9.0 left 21.2% of edges unmarked.
  Hidden, not fixed: anything drawn on a cap re-exposes it.
- Marking colours are authored in `road_markings.tres`, outside `Q33`'s checks (user's call).
- Traps: a `ShaderMaterial` skips the importer's sRGB conversion (`colour.gdshaderinc` does it).
  Godot rejects `return` in `fragment()` at run time while `check.sh` exits 0.

## `Q54` — The kerbside yellow is invented, and the layer that would source it was read past

**Status.** Closed by `P3-13`; vehicle-type scope amended by `Q56`.

`pipeline/kerbside.py` linear-references Road Network v2's `NSR` onto the graph as
`(edge, side, V-range)` runs; `tools/kerbside_error.py` grades. A line on every kerb over-painted
3.4×; sourced paint closed at 3% gross error. The principle later records cite: a surveyed position
or extent is never invented, moved or stretched.

- Level 0 only. `TIME_ZONE` 1 is a double yellow, posted hours a single. The source is read for
  side and extent along, never position.
- Codec fields `kerb_near` / `kerb_off` say the kind, `COLOR_0.a` per rail says where. One kind per
  edge side. Refused: whole-edge quantisation (33% gross error).
- Side convention: `surface.mitres` offsets left of travel and `U = 0` is that side.
- `draw_double_yellow` in `road_markings.tres` is the off switch.

## `Q55` — The filler guard reads greyness, and the placeholder panels are coloured

**Status.** Closed (`tools/facade_survey.py`).

- The imagery carries flat coloured placeholder panels repeated across buildings. Repetition, not
  greyness, is the signature: `is_filler` rejects each atlas's repeated colours per texel
  (`MODAL_SHARE` 0.20) beside `Q37`'s channel tie.
- Reject texels, never atlases: six real photographs carry a baked flat fill at 23–57%.
- Open: a share-based refusal beside `MIN_TEXELS` (one building is 96% filler and still answers).

## `Q56` — `VEHICLE_TYPE = 5` is painted, and the way to know was a second dataset

**Status.** Closed (`tools/kerbside_source_audit.py`).

- `painted_vehicle_types` is `[1, 5]`. Traffic Aids Drawings v2
  (`hk-td-tis_16-traffic-aids-drawings-v2`, EPSG:2326) draws what is painted: `DTAD_RST_ZONE_LINE`
  `RM1040` double yellow, `RM1041` single. 93.9% of code-5 metres carry a line.
- Codes `2`–`4` stay refused because the codec cannot say which vehicle class, not because they
  are unpainted.
- The audit feeds the drawings through the pipeline's own join: both sources cover 96.4% of the
  union (77.0% with `[1]`). It cannot see the side convention; `test_kerbside.py` holds that.
- Catalogue sweep, not to be re-run: no other dataset asserts a kerbside stopping restriction.

## `Q57` — The estate publishes the markings, the width and the tram

**Status.** Closed as a survey; follow-ons taken by `Q58`, `Q59`, `Q95`, `P3-18`.

- Paint is in Traffic Aids Drawings, physical edges in iB1000; Road Network v2 has neither. Read
  codes from the publishers' dictionaries, never from code letters.
- No lane-count attribute exists anywhere; lane lines `RM1101`–`RM1104` make one derivable.
- Trap: `DTAD_TW_STRIP_LINE` is tactile warning strips; `TW` means Tramway only in iB1000.
- Open: bus / GMB / taxi stops into `fares.json`.

## `Q58` — The published tramway is rails, not centrelines, and it is not on the carriageway

**Status.** Closed — `P3-14` ships `tram.glb` (`pipeline/tramway.py`).

- Refused: lane-space rails. Both tracks land on the drawn ribbon at 18.8% of sections.
  `tram_streets` says which streets carry a tram, never where.
- A rail is cut at its region's rectangle and a far station trims it, never drops it.
- A strip lies on the highest drawn road or ground face within `surface_within_m` of the
  centreline's height, so the stage depends on `surface` and `buildings`. Raising whole
  `height_step_m` spans floated a fifth of the rail over 0.10 m.
- `inverted` must be 0. `drawn_gauge_m` cannot see a cross-track pairing; `off_gauge_stations` and
  `pairs` against `tracks` can.
- `rail_metallic` 0.0: metal rendered the rails sky blue. The cue is `rail_roughness`.
- Not done: platforms, and the beds the pairing leaves undrawn.

## `Q59` — The arrows are published, and lane space is the answer

**Status.** Closed by `P3-15`; placement amended by `Q134` (the surveyed position, the slot as fallback).

- `DTAD_RD_MARK_SYM_PT` turn arrows ship as `arrows.glb`: no collider, no vertex colour, opaque.
- Heading is `(90 − ANGLE) mod 360`: 97.8% within 10° of the host, against 2.9% as-is.
- Codes are transcribed from TD drawing CT174/51-5(1)F. Not turn arrows: `RM1116`–`RM1119`,
  `RM1135` / `RM1136`, `RM1167`–`RM1169`, `RM1144`.
- Refused: arrows against a one-way host, and re-matching them to the nearest agreeing edge.

## `P3-16` / `P3-17` — Signs and signal heads ship as sourced geometry, scope-limited

**Status.** Closed — a plan record. Signs: `P3-16` below. Heads: removed by `Q77`, returned by `Q173`.

## `P3-16` — Signs ship where the poles are, because the sign layer is a drawing

**Status.** Closed — `signs.glb` shipped; amended by `Q64`, `Q72`, `Q78`. Live counts in `signs.json`.

- `DTAD_TS_ABV_PT` is a label layer: no point sits on a pole. Position comes from the pole through
  `GG_NAME` (92.6% resolve to one pole; none or several is refused; 15 m cap).
- Nothing publishes the facing: `ANGLE` is the drawing cell's rotation. Facing is derived from
  host tangent + kerb side + drive-on-left, ungraded (`Q62`).
- No dimension is published: plate size, mount height and pole diameter are authored.
- The post is registered onto the drawn kerb at `outset_m`. Refused: iterating the push — residue
  22.1% → 9.7%, never zero, worst shift 5.52 → 16.77 m. The residue drops as `in_carriageway`.
- `signs.glb`'s `COLOR_0` is the one prefix-scoped exemption to `Q33`'s palette rule.
- `facing_away` must be 0. A distant screenshot is not a render check.

## `P3-18` — Box junctions ship as read polygons

**Status.** Closed — `boxjunctions.glb` shipped; heights are `Q92`'s.

- `DTAD_YL_BOX_POLY`, no collider, purely visual. Border 300 mm, hatch 100 mm, spacing 2000, off
  CT174/51-5(1)F `RM1038`. Drawn at the surveyed extent, never scaled to the ribbon.
- Godot's importer can flip a triangle thinner than its position quantum, so those are dropped
  (`slivers_dropped`). Every thin mesh inherits this.
- `lift_m` 0.012 sits below the arrows' 0.015. A burial is never answered by raising it.

## `Q60` — The railings are published, their vocabulary is not, and the position is registered

**Status.** Closed by `P3-19`; "no collider" reversed by `Q159` (a box per panel).

- `DTAD_RAILING_LINE` joins to the graph as `(edge, side, V-range)`. `LINETYPE` has no published
  domain, so classes are a whitelist on code strings; refused metres are published per code.
- No dimension is published: `height_m`, `station_m`, `outset_m`, `base_sink_m` are authored.
- The extent along is read and never stretched; the lateral offset is a rigid per-sample move
  onto the drawn kerb. `max_shift_m` 3.0: beyond it the object is not a kerb railing.
- `railings.gdshader` is `cull_disabled`, so winding decides lighting: `facing_away` must be 0.
- `tools/railing_error.py` shares no code with the join; side disagreement must be 0.

## `Q61` — The fence is coverage-masked, and the layer draws three classes

**Status.** Closed (`P3-19`'s follow-up).

- `ALPHA` is coverage computed from authored dimensions, not translucency. No opacity uniform.
- Classes: `railings` (`CRAIL1` `CRAIL2` `HCAIL2` `RAIL1` `RAILING1`), `bollards` (`bollard0..3`),
  `barriers` (`CBARRIER` `CRASHGATE`). Refused: `AMT*`, `SOLID`, the flyover parapet (`Q15`).
- A class is one shader parameterised by its `.tres`; the wrong `.tres` renders perfectly, so
  `verify_railings.gd` checks dispatch per class.
- Under `cull_disabled` Godot already negates a back face's normal; the shader must not flip it.

## `Q64` — The sign table took a sibling project's description over the publisher's sheet

**Status.** Closed — face table corrected.

- `TS182` is ONE WAY TRAFFIC and `TS183` is NO STOPPING (CT174/51-1(1)C). `signCatalogue.json`'s
  descriptions are shifted across `TS181`–`TS183`; the sheet is the authority.
- A correctly drawn sign meaning something else passes every counter. Read the code beside the
  publisher's cell.
- `_SLASH_THICKNESS` 0.097 of the diameter is measured: a proportion survives a NOT TO SCALE sheet.

## `Q63` — The bundle carries no undeclared image

**Status.** Closed on the user's call — the no-texture contract amended narrowly.

- The reason for no textures is `merge` refusing textured buildings (draw calls); it does not
  apply to a layer that is its own draw call.
- `MeshContract.check_surface` takes `texture_budget_px`: 0 by default; a declaration buys a
  ceiling, and a declared texture that never arrives also fails.
- Declared today: the signs text atlas, `GeneratedLayer.SIGNS_TEXT_ATLAS_BUDGET_PX` (`Q68`).

## `Q65` — The sign estate is scoped to what tells the player where to drive

**Status.** Closed on the user's instruction.

- Out of scope: time plates, parking, no-stopping zones, vehicle-class prohibitions.
- Shape-only direction codes ship untextured (`TS414`, `TS735`, `TS615`, `TS589`); `TS102` and
  `TS101` carry lettering (`Q68`).
- Refused: bend and narrows warnings `TS401`–`TS418` (13 primitives for 53 plates) and `P3-21`
  road lettering. Held: speed limits `TS174` / `TS175`.
- `P3-21`'s refusal reversed on the user's instruction (2026-11-20): `Q262`.

## `Q66` — A deviation board's direction is derived, because nobody publishes it

**Status.** Closed — shipped on a stated, ungraded assumption.

- TD codes no direction for chevron boards (`TS414`, `TS588`, `TS589`). Assumption: chevrons point
  away from the kerb the post stands on; the nearside board is mirrored.

## `Q62` — The turn-restriction diff cannot grade the sign facing

**Status.** Open on the facing (derived, ungraded); the diff ships as a report-only counter.

- Matching `TS131`–`TS133` against the graph's turn restrictions does not grade the facing:
  mirroring the whole region moved `turn_sign_agreed` 29 → 30.
- Nothing published can grade a facing or position on this layer; the evidence for a change is an
  A/B render at one fixed camera.

## `Q67` — Sign faces are graded against TD's sheet by an instrument, not by eye

**Status.** Closed; four glyph-weight rows recorded, not fixed.

- `pipeline/sign_sheets.py` resolves a `TSnnn` to its cell on the index plan;
  `tools/sign_face_survey.py` compares area fraction and bounding-box extent per colour. It grades
  and exits 0.
- Still disagree, all glyph weight: `TS733` / `TS734`, `TS589`, `TS182`, `TS615`.

## `Q68` — Sign lettering is read off the drawing into one opaque atlas

**Status.** Closed (`P3-20`); two debts open — the survey's plate box and the pole standoff.

- `TS102` 讓 and `TS101` 停 take lettering from a 512 x 256 atlas, a second primitive in
  `signs.glb`. Opaque, the field colour baked behind the glyph, so signs stay out of the
  transparency pass. The PNG is generated city data (hard rule 7).
- The plate box is the ink connected to the white it encloses (`sign_sheets.enclosed_white`); a
  bare ink box shipped lettering at 0.873 size.
- Open: `sign_face_survey.measured()` still uses the uncorrected box on 10 faces. Open: the plate
  stands off by exactly `pole_radius_m`, tangent to the post.
- `layer_lift_m` is two-sided and empirical: 0.012 fights the plate, 0.018 clean (shipped), 0.024
  the pole shows through.

## `Q69` — A stop line's host is the road it crosses, not the road it is nearest

**Status.** Closed (`P3-23`); the height source is `Q92`'s.

- `roadmarks.glb` draws `RM1011`, `RM1012`, `RM1013` from `DTAD_RD_MARK_LINE`.
- Host: among level-0 segments within `host_radius_m`, minimise
  `|90 − angle| + proximity_weight_deg_per_m × distance`. Nearest-edge hosting leaves a residual
  of p50 10.8° against 1.8°.
- A wrong host moves the height, the refusal and every counter, not the paint.
  `host_disagreement` is the counter that sees a regression.
- The length is the publisher's. A line with no transverse host is refused, never rotated.

## `Q70` — Everything under `game/assets/generated/` is named by the manifest

**Status.** Closed.

- Godot extracts a `.glb`'s embedded image to a file `sync_generated.sh` then sweeps. So the file
  is named, never exempted: `city.json` carries `signs_text_atlas`.
- Refused: embedding uncompressed — about 262 KB against a 28.5 KB PNG, and no mipmaps.

## `Q71` — One paint shader, three materials

**Status.** Closed — `game/assets/shaders/marking_paint.gdshader`.

- A layer is a parameterisation, not a shader; colour lives in each layer's `.tres`.
  `MeshContract.check_shader_material` compares `resource_path`, so the wrong `.tres` fails.
- A shader change is a change to every layer sharing it: render each and grep for `SHADER ERROR`.

## `Q72` — A NO ENTRY faces the traffic it forbids

**Status.** Closed; the facing stays ungraded (`Q62`).

- The facing is a property of the plate, not the post. `faces_against_traffic` is set on `TS115`
  and `TS116`; such a face turns 180° off its post.
- Refused: detecting a central divider by an opposed carriageway within radius `R` — the count
  runs 8 → 80 as `R` goes 10 → 30 m.
- The old `no_entry_with_flow` read 0 by construction while every NO ENTRY was 180° out. Standing
  rule: a counter is tested by whether a reachable configuration moves it.

## `Q73` — A layer can pass every check and be in no scene

**Status.** Closed — `verify_city.gd` holds both scenes' layer ids against `generated_layer.gd`'s table (`Q115`).

A verify tool grades the asset, never "is it on screen". The scene node is part of the layer, in
`city_drive.tscn` and `city_preview.tscn`; a new layer is looked at in a frame.

## `Q74` — The preview scripts and loaders were merged

**Status.** Closed by `P5-1` (`Q115`) — `generated_layer.gd` is the one loader table.

## `Q75` — A setting that is no longer set cannot fail

**Status.** Closed — pinned by `game/tools/verify_settings.gd` (`Q119`).

- An editor rewrite of `project.godot` silently dropped three warning promotions; the sweep reads
  its bar from the file it checks. `verify_settings.gd` names the 21 promotions and the pinned
  keys. Never edit the expected values down to match a regression.
- Test an intervention against a restored baseline, never the regressed one.

## `Q76` — The web build runs Compatibility; the product runs Forward Mobile

**Status.** Closed — proceed, with the limitation recorded.

- A browser has no `RenderingDevice` backend. An engine fork is refused.
- Mobile against Compatibility, one fixed camera: pixels under L* 10 are 6.0% / 33.1%. It
  crushes, it does not dim.
- Refused: a web-only Environment — ambient 0.85 → 1.8 moved the crushed share 33.1% → 33.0%.
- Measure a look on a fixed camera in a preview scene, never a driven frame.

## `P3-17` / `Q76` — Signal heads: a vocabulary nothing publishes, one head per assembly

**Status.** Built, removed by `Q77`, returned by `Q173` (`pipeline/signals.py`); these findings stand.

- `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has no published domain. The code is a gate (`head_prefixes`
  `P`, `S`), never a look. `ANGLE` carries no facing.
- An assembly is not a stack: 470 of 913 points are coincident, and stacking drew 8.53 m masts
  that passed every check. One head per assembly.

## `Q77` — A dark signal asserts "out of service", and a lit one cannot be derived

**Status.** Reversed by `Q173` on the user's instruction — heads return lit by an authored, checked phase plan.

- Still true: nothing publishes shared greens, stage order or timings.
- Trap: an optional layer's node guards with `is_present()` before loading — `load()` on an
  absent path prints `ERROR: No loader found`, which `check.sh` cannot see.

## `Q78` — Sign registration is a one-way correction

**Status.** Closed.

- A post surveyed beyond `half_width_m + outset_m` keeps its surveyed point
  (`posts_kept_as_surveyed`); the unconditional push pulled 14.5% of posts inward.
- Deliberately not consistent: `railings.py` keeps the unconditional push, because a per-sample
  conditional push would zigzag a straight fence.
- Refused: per-post jitter to break the identical offsets (invented position).

## `Q79` — The street plate's typeface: Free HK Kai, shipped whole

**Status.** Closed (`P3-24`) on the user's call; the interface faces came later (`Q218`).

- Free HK Kai 4700 v1.02 (CC BY 4.0, 6.4 MB) in `game/assets/authored/fonts/`. HK street plates
  are set in 楷書. It sets names only.
- Refused for the plate: a sans (legible and wrong); AR PL UKai (commercial use restricted).
- A bundled font is another owner beside hard rule 7's three: a `LICENSING.md` section and a
  credits line.
- `啓` (U+5553) is missing and drawn as `啟`. The substitution is display-side
  (`street_plate.json`); the ETL does not rewrite the name.
- `tools/font_coverage.py --region <r>` exits non-zero on an uncovered street-name character.

## `Q80` — HUD layout: a touch zone is not a thumb

**Status.** Closed (`P3-24`, user's review); sides superseded by `Q138`, the two-tone housing by `Q139`.

- A tap zone is where input is detected; a thumb is what occludes. `verify_hud.gd` enforces
  `thumb_rest_*`, and asserts that a rect over a tap zone is accepted.
- `HudLayout` and `HudStyle` exports carry no defaults; a missing key reads zero and fails by
  name.
- The destination arrow belongs in the world. Refused: the street name top-centre.

## `Q81` — The wrong-way sign: an interrupt, and the nose decides

**Status.** Closed (`P3-25`, user's review).

- Wan Chai is 93.5% one-way by drivable length, so the failure that matters is the false alarm.
- Heading raises the sign; velocity may only withhold it. Refused by the user: raising on
  velocity. Cost: reversing at speed up a one-way is unsigned.
- `wrong_way.tres`: `angle_deg` 120, not 90 (a legal turn across a one-way passes through
  perpendicular). `correcting_angle_deg` 90 is its own bar: sharing the 120, a sideways drift
  counted as correcting.
- Trap: a verify tool prints `ok` having checked nothing when a `preload`ed script fails to
  compile. Only `check.sh`'s `SCRIPT ERROR` grep catches it.

## `Q82` — Lamp posts: a published vocabulary, an unlit lantern, reachable counters

**Status.** Closed (`P3-26`); the unlit lantern reversed by `Q160` (lit at night, with a pool).

- Source: iB1000 `UtilityPoint.UTILITYPOINTTYPE` = `LPO`. No dimension or elevation is published:
  every drawn dimension is authored, and a lamp on a flyover is drawn on the street below.
- `_register` clears the host kerb, then the point is refused inside any drawn ribbon.
  `max_shift_m` 3.0: at 6.0 the second stage refuses 136 of the 204 it converts.
- `meshes/force_disable_compression = true` in `project.godot`: 16-bit positions over a 1,646 m
  mesh step 0.025 m, 42% of the arm radius. `[importer_defaults]` seeds only a new `.import`.

## `Q83` — Touch scheme: two thumbs, both axes each

**Status.** Decided 2026-08-27 on the user's instruction; relative thumbs confirmed by `Q204`. Values are `touch.tres`'s.

- One thumb is a bipolar vertical axis (`accelerate` above the origin, `brake_reverse` below); the
  other steers. Both are relative: the landing point is the origin.
- Refused: absolute sliders; drift on a tap, on the steering zone's outer end, or armed by where
  the gesture began.
- Open: `look_back` has no touch home.

## `Q84` — The drift "cliff" was the sweep grid; the grip dial is graded on dwell

**Status.** Closed; method stands. The dials it graded went with the engine-tyre car (`Q153`).

- A drift dial is graded on dwell above `drift_slip_threshold_deg` (14°), read with peak slip and
  yaw. Refused: tuning the peak onto the threshold (0.05 s of dwell against 0.57 s).
- The threshold is a design target, never a knob. Refused: a slip servo — "peak ≈ setpoint" is
  then true by construction. The grader never calls what it grades.

## `Q85` — `VehicleWheel3D` simulates no wheel spin; the drift is assisted with a yaw torque

**Status.** Engine finding stands; the yaw-torque assist is superseded by `Q152`'s tyre model.

`get_rpm()` is road speed re-expressed (ratio −1.010 at full grip, −0.98 through a full brake), and
`get_skidinfo()` is not a lockup signal. The engine's tyre has no sustained drift equilibrium.

## `Q86` — The yaw torque decays on time so a tap gets the kick

**Status.** Superseded by `Q152` / `Q153` — the yaw assist is deleted.

Lesson: the skidpad cannot settle a drift value alone — a value fine on the open pad rotated the
car 086° → 219° into a railing on Expo Drive. Sweep with `tools/skidpad.sh --sweep=`, never a
shell loop editing a `.tres`.

## `Q87` — The yaw assist fades out with speed

**Status.** Superseded by `Q152` / `Q153` — the assist is deleted.

Lesson: a tap tuned at 63 km/h spun the car at 84. Grade anything speed-dependent at several entry
speeds; rows compare only within one.

## `Q88` — The grip cut tapers with speed

**Status.** Superseded by `Q152` / `Q153` — the grip cut is deleted.

Lesson: a static sweep of a dial about to become speed-dependent is an upper bound on the fix
(constant 0.710 gave 44.9° at 105 km/h; the fitted taper gave 159.4°).

## `Q89` — The low end deepens the cut, and latches it

**Status.** Superseded by `Q152` / `Q153` — the grip cut and its latch are deleted.

Lesson: a taper tracking speed below the knee is unstable (slower → deeper cut → slower; 63 km/h
became a 165° spin).

## `Q90` — Every hole in the structure is a touchdown; the sampler descends instead of clamping

**Status.** Closed (`pipeline/roads.py::_descend`); node 269's residue closed by `Q264`.

- `INFRASTRUCTURE` stops where a ramp reaches grade. `_descend` ramps from the node's at-grade
  height to the first covered station, bounded by `deck.touchdown_max_grade_pct` (10.0). The cap
  is a classifier: the worst refusal is 5x the steepest keep.
- Refused: `e248` at node 269, MARSH ROAD, 35.8% over a 1.9 m hole. The real touchdown is part-way
  along `e466`; it needs a node-level pass.
- Grade is measured ribbon-to-ribbon, `clearance_m` included, in `_descend` and
  `tools/touchdown_error.py` alike.

## `Q91` — Thin markings were lost to the pixel grid; MSAA 4x

**Status.** Closed (`project.godot`, pinned by `verify_settings.gd`); 2x on the phone's app by `Q236`.

- `msaa_3d` is 2 (4x), `.mobile` 1 (2x). Zeroed, nothing errors; thin paint breaks into dashes.
- The mechanism is sub-pixel rasterisation: a brighter colour, a higher `lift_m` or a wider hatch
  fix nothing.
- Refused: FXAA / TAA (a post-process cannot restore a dropped stripe); 8x (WebGL2 `MAX_SAMPLES`
  is 4 in Chrome).

## `Q92` — Markings stand on the drawn road, not a model of it

**Status.** Closed — `pipeline/drawnsurface.py::DrawnSurface`; `tools/paint_clearance.py` grades.

- A centreline height blend disagreed with the drawn cap fan by p99 0.158 m; 23.2% of box
  triangles sat under the road. Refused: raising `lift_m` to clear it.
- `roadsurface.json` publishes `caps` and `ribbons`; `DrawnSurface` rebuilds the builder's own
  triangles. `sample` is the higher of the covering cap and strip, else the nearest drawn edge's
  height. No centreline, no radius, no knob.
- `split` cuts each paint polygon along the surface's creases before placing; a cut that would
  leave a sliver is refused.
- The drawn road steps as well as folds, so `sample(toward=)` / `covers(toward=)` ask just inside
  the piece. Without it paint is drawn down the riser.
- `roadmarks` refuses a piece whose corners are all under a drawn higher level
  (`stations_on_drawn_structure`). A void station with nothing over it is kept.

## `Q93` — The turn-arrow glyph: head and stem measured off TD's sheet, branch authored

**Status.** Closed (`pipeline/arrows.py`, the `arrows` block's `*_frac` keys).

- CT174/51-5(1)F is NOT TO SCALE but to proportion (`RM1016`'s published 2.800 measures 2.802).
  Measured as fractions of glyph length: head 0.390 x 0.122, stem 0.076 → 0.032.
- The branch is authored: a faithful dart reads as a detached diamond and its barbs are
  sub-pixel. No licence to re-author the head or stem.

## `Q94` — Two arrows in one lane: the lane count was invented, and the arrows are a source for it

**Status.** Closed; residue carried by `Q114` (one-lane), `Q126` (two-way split), `Q130` (`arrows_unmeasured`).

- Nothing is de-duplicated or moved; `stacked_disagreeing` reports the contradiction left.
- `lanes` is bracketed off the measured `width_m` against TPDM 4.3.9.8's 3.0–3.65 m lane, never
  divided by `lane_width_m`. The bracket contains TD's count on 9 of 9 rows of Table 3.4.2.1.
- A row of ≥ 2 turn arrows abreast (`_ROW_MIN`) is a lower bound on painted lanes and resolves
  ambiguous brackets only. Rows cluster on the published offset; the 2.00 m bar sits mid-plateau
  (flat 1.50–2.50).
- A lane count moves no geometry.
- HyD Pavement Polygon is the third width publisher: it never overrides a station the line
  publishers answered. `_union_boundary` drops HyD's internal seams.
- `width_bounds.max_m` 16.5 must not move: the refused spans are a continuum to 26.71 m, and 16.8
  admits 13 of them.

## `Q95` — The authored carriageway width was outside TPDM's range; `width_m` is now measured

**Status.** Closed on the user's call; coverage and floors moved on in `Q128`, `Q129`.

- The authored 6.4 m was below TPDM Vol 2 Ch 3's 7.3 m two-lane minimum. The standard
  corroborates a measurement and must not assign one.
- `pipeline/carriageway.py` measures `width_m` per level-0 edge by two-sided rays; `width_source`
  says which.
- `drawn = max(width_m, floor)` replaced a 1.6× multiplier, which over-widens wide streets.
- Crossing test `beyond_m = span − own`: under `hard_min_m` 3.0 the span is this edge's width; at
  or over `dual_min_m` 6.75 it stays a span; between, nothing is read. Any single threshold
  publishes TONNOCHY ROAD's 16.7 m as one carriageway.
- The pipeline and `tools/carriageway_margin.py` are two independent implementations on the
  user's instruction (p50 0.005 m apart). Only the tool licenses `decomposed` halves.

## `Q96` — The arrows' lane snap divides by the measured carriageway

**Status.** Closed; placement half superseded by `Q134` — the snap is now the fallback and the instrument.

- A published offset is read as a fraction across the surveyed `width_m`, never
  `lanes x lane_width_m`.
- `outside_drawn_ribbon` should be a subset of `outside_carriageway`; an inversion is a finding.
- NaN guard: `not x > 0.0`. `_lane_of` and `_offset_of` are stated inverses.
- Test fixtures must not default the carriageway to `2 x half_width_m`, the one value where the
  surveyed and drawn frames coincide.

## `P3-9a′` — Round 0: the city is recognised, and it was not drivable far

**Status.** Closed — three HK drivers over the web link.

- Recognised as Wan Chai from geometry alone, the acceptance criterion.
- Drivers stuck on bridge structures: `INFRASTRUCTURE` geometry, i.e. `Q19`. Resolution: carve the
  licensed ramps, fence and dress the rest.
- "Some buildings read as unfinished" was volunteered. `Q26`'s gate needs rejection of the city
  and attribution to flat surface; half was met, so it stays shut.
- Open: `P3-9` proper — different drivers, on a handset.

## `Q97` — Touch drives on three of five actions

**Status.** Closed on the user's instruction (no touch drift yet); "no visible touch chrome" reversed by `Q204`. `P2-4`'s review waits on `P0-3b`.

- `InputRouter`: left zone steers, right zone is one bipolar axis (`accelerate` above the touch origin, `brake_reverse` below), both thumbs relative (`Q83`). `drift` and `look_back` have no touch home.
- Touch overrides the action map per axis only while that axis's finger is down: `driver.gd --hold=` drives through `Input.action_press`, and an unconditional touch read would zero every scripted drive. `verify_input.gd` asserts both sides.
- Open: `touch.tres` travel numbers (140 / 110 / 6 px) are unmeasured against a thumb; the drift gesture; `look_back` placement.

## `Q98` — The chase camera's yaw is exponential, and its tuning is data

**Status.** Closed.

- Exponential yaw, `yaw_response` 6.0 (`camera.tres`, `ChaseProfile`, no script defaults). The old constant 7.0 rad/s was 3.12x the taxi's peak yaw rate and never lagged; a lower constant was refused because one rate also governs the look-back flip.
- Yaw follows facing, never velocity: mid-drift, velocity points at the kerb.

## `Q99` — An editor save stripped `project.godot` and a `.tres`

**Status.** Closed. Superseded by `Q119`.

## `Q100` — Hong Kong is the only city; its config is the single source of truth

**Status.** Closed, on the user's instruction. Root `CLAUDE.md` hard rule 3 is the standing form.

- The city-agnostic rule was retired, not refuted: nine datasets from four publishers mean a second city is a second pipeline, not a YAML file.
- `etl/config/hong_kong.yaml` (`SUPPORTED_SCHEMA` 5), no `--city` flag, paths `etl/sources/<source>` and `etl/out/<region>`.
- `etl/pipeline/hongkong.py` holds the constants that are the city: `EPSG:2326` / `EPSG:4326`, drive-on-the-left, `TS115`, `TS131`–`TS133`. A code that drives a branch is declared there, never copied into config.

## `Q101` — Data-availability refusals re-read against the grown estate

**Status.** Closed. Check `PLAN.md` for what has since been taken.

- Measured shut: `dTAD_IRNP.gdb.zip`'s 58 tables carry no coded-domain content (control: 85 pairs on an iB1000 sheet). `Q60`'s `LINETYPE` whitelist and `Q76`'s `REFNAME` gate stay rules this project wrote.
- An outbound-data policy must be written before any derived dataset leaves the repo (`LICENSING.md`); not pursued, on the user's call.

## `Q102` — The vision façade reader is withdrawn on cost, and `TEXCOORD_1` goes with it

**Status.** Closed, the user's call. Withdrawn, not refuted. Supersedes `Q41`, `Q46`, `Q42`'s riders; amends `Q40`, `Q26`, `Q47`.

- Deleted: `tools/facade_grammar.py`, `tools/podium_error.py`, the grammar/tint codec, the `facade_survey:` block (now refused by `config.py`), the shader's `survey_*` and `quiet_*` uniforms. No `anthropic` dependency remains.
- The survey channel was removed, not shipped all-zero (`0` was a legal code). Tile `TEXCOORD_1` now carries `Q121`'s payload.
- Survives: the hash path, `Q44`, `Q45`, `Q43`'s `glazed`/`fenestrated` split (re-merging re-opens a defect on 39.3% of wall vertices), and the colour survey (`facade_survey.py` → `COLOR_0`).
- `tools/facade_unwrap.py` and `tools/facade_glazing.py` are kept with no consumer. Re-proposing costs three decisions: the survey's cost, the dependency, a channel with a schema bump.

## `Q103` — The off-grade network is drivable, and the ribbon is drawn on its deck

**Status.** Partly open. Level 1 is measured and open (`Q108`, `Q110`, `Q111`); level −1 stays closed. Open: `e489`'s headroom; the `e208` / `e306` lane-bar pinches.

- Refuted: extending the publisher survey off-grade. Publishers license 5 of 45 level-1 edges and their lines are a plan projection, so a ray from a deck finds the street's kerb underneath (`e104`: 11.04 m against a 7.50 m deck).
- The model is the only source for a deck. The deck walk rides the `INFRASTRUCTURE` `HeightField` and publishes a width and a signed offset (`width_source` / `offset_source` `deck`); `carriageway_survey.levels: [0, 1]` is pinned to `clearance.LEVELS`. The centreline does not move (`Q54`).
- `e489` CENTRAL-WAN CHAI BYPASS TUNNEL: the road rides a flat `terrain − 8.00 m` while the tunnel box keeps fixed levels, leaving 0.22 m of headroom. No instrument publishes a height. The fix is a `roads.py` height rule; widening makes it worse.
- Refused: a per-vertex deck offset. At the interchange the contiguous structure is 7.9 to ≥24 m wide, so its middle is not this carriageway's.

## `Q104` — The cut face had no back, and the ribbon is drawn wider than the corridor

**Status.** Mostly closed. Back face, stub clusters and through corridors ship (off-grade only since `Q129`); the flank caps were deleted by `P3-35e`; the edge-on railing is fixed by `Q112`. The carve-wall arm was not taken.

- Back face: `carve._double_side` emits one reversed, coincident triangle per drawn triangle (`cull_disabled` is unavailable: the wall rides in the tile). `_facing_away` is counted before the mirror. The back face inherits the removed structure's channels, or the window-band shader glazes it.
- Carve-wall arm: the wall stood 1.52–4.32 m inside the drawn carriageway while the at-grade ribbon took a 10.24 m floor. The floor is 0.0 since `Q129` and this is not re-measured. Never widen the prism (`Q54`).
- Stub clusters (`P3-31`): `_Edge.is_stub` is the two existing trim clamps read together, no new knob. `_stub_clusters` unions the groups a stub joins and `_cap_ring` hulls the non-stub mouths once. A stub across the seam joins nothing. Refused: one hull per stub.
- Through corridors: two facing arms at different nodes are one street, capped by their own quad. Refused: a kerb-line corner rule (paired arms 23 m apart at Lockhart / Marsh).

## `Q105` — The asymmetric ribbon is priced, and it buys paint rather than width

**Status.** Closed. Built by `Q107`.

- Licensed: cutting paint back to structure. Not licensed: publishing the result as `width_m`; the rims come from one contiguous structure, which at an interchange is not this carriageway's (`Q57`).
- "Stations on deck after the clamp" is 100% by algebra; no such counter (`Q58`).

## `Q106` — Four instruments measured a ribbon that is not drawn

**Status.** Closed. Per-station form superseded by `Q107`.

- `surface._shape` draws the rails at `±half + shift`, `shift` being the graph's `offset_m` (up to 4.95 m off-grade). Any tool reconstructing the ribbon reads the drawn offset.
- `overhang.py` drops samples with no road under them and `deck_margin.py` keeps them; a divergence between them is a bug.
- `offset_m` is indexed, never `.get` with a default: a bundle without it is stale.

## `Q107` — The off-grade ribbon is cut to its own deck, per station and per side

**Status.** Closed. Three residuals open; `Q113` fixed the clamp off structure.

- `roads.py` publishes `deck_rim_m`; `surface._clamped_rails` cuts each rail to its own rim: `upper = min(shift + half, left_rim)`, `lower = max(shift - half, -right_rim)`. It cuts, never extends. `width_m` and `offset_m` do not move: paint, not width.
- No deck is `inf`, never 0.0. A station whose rails would cross (bar `_MIN_SEGMENT_M`) keeps its unclamped ribbon and is counted.
- Open: junction caps read the unclamped width and can re-draw cut paint; edge ends are over-cut where a deck flares; the kerb is drawn `kerb_width_m` outside the clamped rails and no grader sees it.

## `Q108` — The off-grade network publishes a clearance

**Status.** Closed. `clearance.LEVELS = (0, 1)`; level −1 refused.

- `clearance.walk` reads `roadsurface.json`'s `offset_m` negated (`walk`'s `across` is right of travel; `offset_m` is in `surface.mitres`' left frame). Unnegated it mirrors every off-grade section and publishes a plausible table.
- Level −1 refused: a bore has no deck to walk, and a horizontal corridor cannot express `e489`'s headroom.
- `clearance_reconcile.py` takes one `--levels` for both halves; `narrowing.py` is pinned at grade. `edge_levels(graph)` is indexed: an unknown edge never defaults into the gated population.

## `Q109` — The four blocked bridges, re-read on the ribbon that is drawn

**Status.** Closed. Report-only; its fence question is answered by `Q110`.

- On `e208` and `e306` the occupier migrates across the ribbon; on `e257` and `e450` it stands on the rims. A width rule can reach the rim pair; neither a width nor a constant offset reaches the migrating pair.
- Quote every corridor figure with its instrument and bin (`Q57`): `e257` reads 0.34 m at the 1.0 m bin and 1.19 m at 0.5.

## `Q110` — The corridor measured exactly, and the disagreement `Q109` left open

**Status.** Closed. Report-only; no barrier owed on any off-grade edge.

- `tools/corridor_truth.py` clips every tile triangle against the station slab and the bumper band in closed form. Its reading is a lower bound: it can clear an edge, never condemn one.
- All four edges clear the 1.80 m car bar. At the 3.20 m lane bar the starved set is `e208` (exact 2.57 m after `Q113`) and `e306` (3.06 m). Never pool the two bars.
- Open paint lead: the blockage is a parapet face 0.6–0.8 m inboard of `deck_rim_m`, which is the structure's outer edge. A rim stopping at the drivable face would cost no corridor.

## `Q111` — The elevated network opens, exactly where it is measured

**Status.** Closed. Shipped as `P4-1`; the user's review passed 2026-09-06. A scope change against `Q13`.

- Invariant: every mapped level `clearance.LEVELS` does not measure is closed, every level it measures is open. `fence.touchdown_levels` is `[-1, 2]` (level 2 listed and inert so the rule is total), pinned by `test_the_open_levels_are_the_measured_levels`.
- `RoadGraph.is_drivable` is level 0 or measured. The level-0 arm is load-bearing: an edge wholly inside junction trims publishes no corridor and must stay in the network.
- `nearest_edge` prefers a road within `LEVEL_REACH_M` (2.5 m) of the query's height, else the nearest at any height; `Hit.distance` stays plan distance. Without it 318 of 825 level-1 vertices put a flyover under a car on the street.

## `Q112` — The fence is one quad thick and disappears edge-on

**Status.** Closed. The barrier family is a slab with a per-class `thickness_m`.

- `thickness_m` 0.05 / 0.14 / 0.10 for `railings` / `bollards` / `barriers`. Extruded outward only, so the road-side face stays where it was registered (`Q78`).
- The fold test is not a squareness bar: a repair keyed on `facing_away`'s predicate reads 0 by construction (`Q58`).

## `Q113` — The ramp's ribbon shrinks at the touchdown, and paints a 1.57 m lane

**Status.** Closed. The lane-count half is `Q114`.

- `surface._deck_rims` discards the rim where `on_structure` is `False`: there the rim read 0.100 (`DECK_ACROSS_M`), the end of the structure, not the edge of the road. Not fixed by removing `Q107`'s clamp, nor by moving `width_m`.
- Open: the real lane count varies along an edge and `lanes` is one number per edge.

## `Q114` — The lane count invented lanes the road has not got

**Status.** Closed. Per-edge `lanes` remains a limit.

- The published count is the measurement and can be 1. The floor a one-lane road needs is the consumer's: `RoadGraph.LANE_FLOOR` (2) in `lane_offset`.
- `_ROW_MIN` (2) did not follow the floor down: a row of one arrow is a marking, not a count.
- Off grade every count is authored and the deck is a ceiling, never a source (`lanes_source: deck_capped`). `_deck_lane_ceiling` refuses a `(0, 0)` bracket rather than clamping it to one.

## `Q115` — What repeats ships as a prop with placements; what is measured stays merged

**Status.** Open. `P5-1`–`P5-6` built and passed the user's drive; `P5-8` (content) waits on Phase 3.

- Rule: modularise where the real object repeats. The ETL keeps its registration and counters; the output is a library `.glb` plus a `*_placements.json` (signs, lamps, arrow glyphs, barrier panels).
- Instancing buys bundle size, not draw calls: a `MultiMesh` costs a draw plus one per shadow cascade. Props are batched per `prop_cells.tres` cell (`Q135`).
- `generated_layer.gd` is one table-driven loader. Callers pass constants (`GeneratedLayer.LAMPS`), never strings: a misspelt id makes `is_present` false and a verify tool's skip branch exits 0.
- Barriers: one unit panel per class, `panel_m` wide (2.0 / 1.5 / 3.0), equal to the class's `post_pitch_m`, bound by a test. The snapping cost is published (`metres_snapped`, `joints`, `joint_gap_m`, `bends`) and never hidden by stretching a panel. The user asked for no mitre. `railing_error.py` walks the unit panel, not the expansion.

Refused:
- A road kit: of 737 level-0 edges 418 bow over 0.5 m off a straight piece, with 88 distinct widths; 301 of 380 junctions are 3-way. A kit moves streets by metres between surveyed footprints.
- One shared `_register` across `signs`, `lamps`, `railings`: each difference prevents a recorded defect (`Q78`, `P3-26`, `Q95`).

## `Q116` — Two regions meet at a hard edge, and the join decides where the cut is, not the unit

**Status.** Open. `P5-7a`–`g` and `P5-9a`–`d`, `f`, `g` built; `P5-9e` refused. Remainder: the user's verdict on the legal line; the cap's foreign mouth at node 224; `_read_offside` pairs owned edges only; `e364`'s per-edge `offset_m`.

The region is the unit above the 150 m tile. A whole-city model is refused (`Q10`: float32 spacing 3.9 mm at 38 km).

Assignment rule:
1. Membership is on the declared geodetic `bounds`, half-open, never the projected rectangle. Overlapping regions are refused.
2. A crossing feature is clipped to the union of the declared regions it touches and kept whole across internal lines.
3. The owner is the region containing the run's first vertex in the direction of travel. Tolerance-free.
4. The owner publishes the edge measured over its whole run; every other region it enters publishes a foreign copy (top-level `foreign_edges`). Identity across bundles is `(source_id, run ordinal)`.
5. A boundary node is a graph node, never a rectangle intersection. A cap goes whole to the region containing the node.
6. A prop is owned by the region containing its surveyed point and may host onto a foreign edge.
7. A turn restriction is published by the region owning its pivot node.

- `join.reach_m` (133) widens source reads toward a declared neighbour so the owner can measure its far half; `stations_beyond_reach` refuses what falls outside.
- Refused: length-share or midpoint ownership (48/52, 49/51, 46/54; flips under a `simplify_tolerance_m` change); one agreed easting; omitting the foreign copy; moving `bounds` to a grid line.
- `city_streamer.gd` picks by `aabb`, never tile id: the two tile grids are 1,649 m apart, not a multiple of 150.
- `pipeline/join.py` is the reference merge (owner's copy kept, seam nodes named by `(source_id, run)`); `road_join.gd` ports it and `verify_join.gd` holds it field by field. `tools/join_seam.py`'s bar: one owner per run, 0 nodes on the internal line, 0 unmatched copies.
- Finding: `Edge.offset_m` is one median per edge. `e364`'s far half drags it −0.1 → −2.9 m and `_clamped_rails` cuts the near half 3.35 → 2.05 m. The fix is a per-station offset.
- Ids collide across regions. The runtime carries one id map per region, applied at load; no document is edited; a fare is `(region_id, id)`. Refused: a city-wide id space at export; anchoring the scene in city space; one streamer over N manifests.
- `P5-9e`, refused: sharing prop batches across regions. One batch per mesh name spans 1.6 km and is never culled: +3 to +11 draw calls and up to +262,000 primitives at the seam. Re-propose only with a culling argument.

## `Q117` — Opposed one-way ribbons are paired geometrically, and the join is published

**Status.** Closed. The pairing stands; the shader lines are off (`Q118`, `Q132`) and the join is drawn as geometry (`Q125`).

- A one-way ribbon's partner is the one-way ribbon at the same level, anti-parallel within `roads.surface.opposed_pair_bearing_deg` (30), whose centreline lies inside the edge's drawn width plus one kerb, nearest first, and only where the two choose each other.
- No free search radius (`Q72`: count ran 8 → 80 over 10 → 30 m).
- The angle is swept, not a plateau: paired ends 84 → 112 over 10–75° while `opposed_pairs_one_sided` climbs 4 → 17; at 30 it is still 6.
- Mutuality is load-bearing: a one-sided vote draws a second line.
- Refused: an angle-free rule (mutual offside-kerb burial). Its bar swings the pair count 62 → 4 over 0.10 → 1.00, against the angle's 1.35x.

## `Q118` — RM1001 is drawn from TD's survey; `RoadMark.axis` selects the host rule

**Status.** Closed. `longitudinal_legibility_scale` 1.0 and `draw_pair_join` 0.0 on the user's call.

- `RoadMark.axis` is required with no default: transverse scores `|90 - crossing|`, longitudinal `crossing`.
- A longitudinal marking must lie within its host's drawn half-width or it is refused (`host_off_carriageway`). Transverse marks are exempt. Refused: sampling height from the host's own edge (buried share 1.50% → 8.58%; a marking up to 236 m long spans several edges).
- `longitudinal_legibility_scale` stays 1.0: the user refused 1.88 as too thick. The answer to sub-pixel illegibility is antialiasing, not width.
- `draw_pair_join` must stay 0.0: RM1001's host is a one-way edge on 85 of 91 parts, so the two lines fight.

## `Q119` — An editor save is a no-op; resource rationale lives in sidecar `.md` files

**Status.** Closed 2026-09-07. Supersedes `Q99`'s and `Q75`'s guards.

- Godot's writer omits any key equal to its registered default, so a "dropped" setting was in force all along. `game/tools/verify_settings.gd` reads every pinned value back through `ProjectSettings`; a grep of `project.godot` is the wrong instrument.
- `project.godot`, `export_presets.cfg`, every `.tres` and `.tscn` are committed in the writer's own form; rationale lives in `<name>.md` beside the resource. `check.sh`'s `tuning` step requires the sidecar (unless `UNDOCUMENTED_OK`) and refuses a `;` line, an orphan sidecar or a stale exemption.
- The writer also omits a key equal to the script's `@export` default, so a profile script carries no defaults (`Q150`).
- No Godot process may be launched above `==> import` in `check.sh`: `class_name` globals resolve only from the cache the import scan writes.

## `Q120` — Four regions measured: Wan Chai is not the dense extreme

**Status.** Open. Coefficients closed; the streaming distances are `P4-5`'s; `sha_tin` and `mong_kok` are ungraded.

Each region is a 0.016° × 0.008° box (1.457 km²).

| region | buildings | LOD0 tri | tile MB | road km |
|---|---:|---:|---:|---:|
| `wan_chai` | 1,419 | 515,025 | 39.9 | 56.15 |
| `causeway_bay` | 570 | 322,864 | 20.6 | 13.43 |
| `sha_tin` | 761 | 245,491 | 15.6 | 22.33 |
| `mong_kok` | 2,061 | 944,004 | 53.9 | 37.97 |

- Resident budget (`tools/resident_budget.py`, banded by plan distance to the tile `aabb`): `streaming.tres` (`tier_distances_m` [250], `unload_distance_m` 400) holds 105 / 76 / 47 / 184% of the 300k-triangle budget at the worst camera, in table order. The worst camera is the statistic.
- `carve.edges` is keyed by region. Edge ids are per-region ordinals, so a Wan Chai list names real roads elsewhere (7 of 8 in `mong_kok`). Never build "skip the ids the graph does not carry". A region absent from the block carves nothing.

## `Q121` — The mesh contract against a DCC workflow

**Status.** Open. `P5-10`–`P5-13` built; `P5-14` (textures on tiles) is held for an artist.

Godot 4.7.1 imports node and mesh `extras`, drops custom `_` vertex attributes, and keeps a glTF material's name. So per-object identity is a table in `extras` and per-vertex identity travels in a UV channel.

- `P5-11`: `TEXCOORD_0` is a planar façade UV in metres; `TEXCOORD_1` carries marker, phase and object row; each tier ships its object table as mesh `extras`. PCK +10.9%; reversible, the user's call. The carve reads these channels back.
- `P5-12`: the collider is its own `<tile>_collision-colonly` primitive at `buildings.collision_cell_m`; every road chunk carries a `-colonly` ribbon. 2 / 3 / 4 m cells keep 87.8 / 72.9 / 63.5% of triangles at a façade p90 offset of 0.47 / 0.62 / 0.91 m.
- `P5-13`: each tier carries a `<tile>_occluder-occonly` primitive at `buildings.occluder_cell_m`. The culling unit is an instance: 2 draw calls culled on Wan Chai's route, 12–47 at Mong Kok's worst camera, for PCK +10.3%. Handset CPU cost unmeasured (`P0-3b`).
- `meshes/generate_lods = false` ships: PCK −8.6%, primitives +16–30%. Reversing it also means deleting every generated `.import` sidecar.
- Refused: per-building nodes (no static batching; ~50 draw calls a tile); a convex hull per building (an L-shaped podium's hull blocks the street); heightfield terrain.

## `Q122` — The verifier's ambiguous sample, the per-tier occluder, and the resident budget

**Status.** Open. `P5-15`–`P5-18` built; the far-tier occluder and a web bundle without one are the user's call.

- `buildings.occluder_cell_m` is a per-tier list; `[4.0, 4.0]` ships. `[4.0, null]` is identical in draws and pixels at Mong Kok's worst camera for −4.6 MB of PCK; `[null, null]` is −10.9%.
- The stock Web export template cannot cull (no `raycast` module), so on the itch.io cut the occluder is pure download. A web cut without it is a second ETL build. Refused: an 8 m occluder "for the web".
- Refuted: the LOD1 ratio as the cheap budget lever (a 4 → 12 m LOD1 cell moves 184 → 163%). 21 LOD0 tiles carry 84–91% of the resident set; what is left is LOD0's cell and radius (`P4-5`).

## `Q123` — A non-convex border quad folds `FlatBuilder`'s fan

**Status.** Closed 2026-09-08 as `P5-19`.

- `FlatBuilder.polygon` fans from vertex 0; the convexity precondition is documented, not checked. `boxjunctions.border_polygons` refuses a non-convex border quad (`_turns_one_way`) and counts it in `degenerate_border_segments` (1 in 7,807). It is a quad rule: a pentagram passes it and still folds.
- Refused: masking inverted triangles out of `FlatBuilder.build` (0 by construction, `Q58`); widening the sliver bar; a build-stopping assertion.
- Open: `box_extent.py` reports 5 triangles (0.053 m²) inside no published ring on `sha_tin`.

## `Q124` — The distance to the Godot guide, read as three collaborators' first day

**Status.** Closed. `P5-20`–`P5-28` built. Every divergence `Q119` and `Q121` priced and kept stands.

- Shader dispatch is by material name (`generated_scene_import.gd::SHADERS`): a mesh whose material is called `signs` takes that shader silently.
- Refused: a feature-folder reorganisation; event-driven input; connecting the unused `InputRouter` signals to satisfy a grep.

## `Q125` — The opposed-pair centre line is drawn as geometry and yields to TD per metre

**Status.** Closed. The shader's `draw_pair_join` stays off.

- `surface.py` publishes `opposed_pairs`. `roadmarks.py` walks the line midway between the two centrelines, cuts every stretch a drawn `RM1001` covers, and draws the rest as the mark `road_marks.opposed_join_mark` names. A region draws none by leaving the key out. Counted in `roadmarks.json`'s `join` block.
- Why geometry: a per-edge shader switch is wrong on partly covered pairs (24 of 95 pair ends). Refused: a flat varying per station (the provoking-vertex convention differs between renderers).
- No new knob: covered means a surveyed line within half the pair's own `gap_m` and within `bearing_tolerance_deg` of parallel.
- Debit (`Q54`): the line is inferred, and a double white instructs no overtaking. At `e656`/`e657` it stands for a real 3–4 m median.

## `Q126` — A row of arrows on a two-way edge is read by direction; `lanes_forward`

**Status.** Closed for cause A; B closed by `Q128` / `Q130`; C and D open.

`stacked_disagreeing` arrow pairs have four causes: A, a two-way bracket `(2, 3)` narrowed by TPDM 3.4.2.7 (WAN CHAI ROAD `e50`); B, no measured width (STEWART ROAD); C, lanes painted 2.7–2.9 m, under TPDM's 3.0 m (HENNESSY ROAD `e120`); D, the width includes the tram reserve (`e114`).

- Rule, in both `_row_reading` copies (`lanes_split_disagreement` is their diff): each run across the road is a lane; the row states `max(forward, 1) + max(backward, 1)` with split `max(forward, 1)`.
- The row is a lower bound: it only puts a count back above the narrowed bracket. A row the width refutes is a finding (`lanes_row_over_bracket`). Refused: publishing the painted count as a fallback.
- `lanes_forward`: `lanes` on one-way; on two-way the row's split, half where even, `null` where odd and unsplit. `road_graph.gd` does not read it.
- The marking codec is full: the shader decodes `TEXCOORD_1.x` with `floor(x + 0.5)`, exact only to 2²³. A split over 3 is written 0 and counted (`lanes_forward_unsaid`).
- Refused: moving the 12 m junction guard. At 10 m LEIGHTON ROAD `e263` reads 10.57 → 15.34 m (a ray across the mouth) and two measured edges are lost.

## `Q127` — Reading a carriageway width where the ray survey cannot

**Status.** Closed. Measurement only; its cascade shipped as `Q128`.

The survey drops stations within `JUNCTION_M` (12 m) of a node and needs `MIN_STATIONS` 3, so an edge needs ~34 m. Tools: `tools/carriageway_margin.py`, `tools/width_evidence.py`.

- Refused: a junction-opening gate on the ray survey. It loses and moves measured widths at every radius 0–8 m (at 0: 10 lost, 25 moved > 0.5 m).
- Readings against survey-measured edges, Wan Chai |p90| m, one-way / two-way: authored `lanes x 3.2` 4.14 (the bar); stop line length 6.07 / 8.04; lane-line pitch 10.88 / 4.64; arrow pitch 3.47; HyD area / length 3.62 / 1.28; HyD strip through centre 2.96 / 0.85 (best single); street borrow 3.74 / 2.90.
- Refused as bounds: lamp posts (17.1% wrong), sign poles (27.7%), railings (49.3%), stop line (56.0%), lane lines (27.9%).
- The ray survey may never be a confirming voter.
- Only a confirmed reading beats the authored width on short edges: HyD strip plus another within 1 m reads 1.2–1.6 m against 4.6 / 3.7. The unconfirmed strip is no better (4.70 against 4.56).

## `Q128` — Two agreeing stations, and a strip of HyD's paint where no ray reaches

**Status.** Closed. Coverage 39.5% → 53.5% Wan Chai, 34.2% → 63.3% Causeway Bay, 0 measured widths moved.

- Two stations publish when they agree within the region's own mid-block leave-one-out p90 (2.81 m Wan Chai, 2.91 Causeway Bay): derived, never config. Three-station edges are assigned first, so it is additive.
- The deck bar stays at three stations: a p10 of `[8.0, 12.0]` is 8.4, one lucky ray.
- The confirmation is the licence: the strip alone is |p90| 2.53 m (4.69 on short edges). It publishes only where `borrow` or `arrows` agrees within `confirm_within_m` (1.0); omit the key and no strip publishes. `width_confirmed_by` names the evidence.
- Refused: narrowing the raster corridor ±15 → ±8.5 m (8 more edges publish, 10+ widths move).
- Reproduce: `tools/width_evidence.py --region wan_chai --voters borrow,arrows`.

## `Q129` — A width is the carriageway's, and most open edges are not a carriageway

**Status.** Closed. Built as `P3-33b`/`c`, graded by `P3-33e`; `P3-33d` superseded by `P3-35e`. Open: `P3-33f`, the user's drive.

User's calls: draw the carriageway region itself; the floor is off; `shapely` approved.

- Finding: on authored edges only 19.8% / 25.6% (Wan Chai / Causeway Bay) of mid-block cross-sections end kerb to kerb; the rest end in another centreline's share of the same asphalt. No tolerance can license a width there.
- R: the union of HyD's Pavement Polygons, holes kept; where HyD is silent, rails cast per station to the line publishers' kerbs. Cut to the region's rectangle.
- T_e, the territory: R cut by the Voronoi cell of edge e's centreline. Foreign edges take part and own nothing.
- `pipeline/region.py` (between `carve` and `surface`) writes `carriageway_region.json` (`REGION_SCHEMA` 4; not bundled), extents per station at `station_m` 2.0.
- A level-0 ribbon's rails are its territory's extents; U runs 0 → `lanes` rail to rail. The rest of R is drawn as areas in the cap class. Hull caps, stub clusters and corridors run off-grade only.
- `floor_default_m` is 0.0; it still sets the junction trim radius and the plain ribbon of a run past its rectangle.
- `width_m` does not move: a territory is a share (`Q57`). Levels ±1 keep their ribbons.
- A share is not a corridor: the stage also measures kerb to kerb, `surface` publishes `corridor_*`, and `clearance` reads that (GLOUCESTER ROAD `e390` owns 1.56 m of 25 m). `city.json` carries `corridor_half_width_m` and `corridor_offset_m` as a pair.
- Rail shaping (`surface_region`): `bridged` holds a share run between two kerbed stations to the straight line between them. `opened` is a morphological opening over `rail_opening_m` (20.0, not a plateau) and never widens; closing a pinch would be a widening. Stations are thinned at `rail_tolerance_m` 0.10. `flare_m` is the junction trim read off the territory.

Refuted:
1. Polygonising the line publishers' kerbs where HyD is silent: 24 faces, 0.3% of the length. Rails, not faces.
2. R unclipped: 6.8% orphan territory, one piece 228.6 m from its owner (clipped: 0.9%).
3. Borrowing width from the through-neighbour: leave-one-out |p90| 3.23 m.

Graded (`wan_chai` / `causeway_bay`):
- `clearance_reconcile.EXPECT` is 28 / 32 / 8 and 9 / 13 / 4.
- At the 3.20 m lane bar, refusing starved edges loses 2.17% of ordered pairs on Wan Chai (`e53` CANAL ROAD WEST 2.67 m, `e138` FLEMING ROAD 3.00 m, `e384` GLOUCESTER ROAD 3.05 m). At the car's 1.80 m bar nothing moved. Whether traffic's bar is a lane or a vehicle is `P3-3`'s.

Reproduce: `tools/carriageway_region.py --region wan_chai` (`--svg out.svg --window 150 0 450 250`).

## `Q130` — A row of arrows sets the count on an unmeasured width; arrows stand in the drawn lanes

**Status.** Closed. `ROADGRAPH_SCHEMA` 15.

- `carriageway._raise_unmeasured_with_rows`: on a level-0 edge with no licensed width, a row of at least `_ROW_MIN` arrows abreast raises the authored count, never lowers it (`lanes_source: arrows_unmeasured`). `width_m` stays authored and `verify_road_graph.gd` requires that.
- `arrows._slot_offset`: the slot is found in the surveyed frame and drawn about the ribbon's middle (level-0 ribbons sit up to 6.49 m off their centreline).
- The slot count stays `lanes`, not `lanes_painted`, or arrows would stack.

## `Q131` — A kerb in the road is not the road's edge: seams, islands, lines across

**Status.** Closed. Open items below.

- `carriageway_region.seam_m` 0.10: HyD's union is closed before anything reads it. On a plateau (5.3 / 7.0 / 8.9 m² added at 0.05 / 0.10 / 0.15, then 17.6 at 0.25 and 161 at 0.40). Not raised to clear a pinch.
- `region.islands_of`: a kerbed island is read through, in the rails only where a kerb stands behind it inside `max_m`. An island is shorter than `rail_opening_m` and no wider than `lane_width_m`, the width waived where a centreline runs through the ring. Refused: an area cap (at 40 m² Causeway Bay's platform strips qualified and R grew 282 m²).
- Open: single stations where HyD's polygon touches the centreline near a node (`e37`). Refused: a one-station dip filter (a closing; a dip is what a short island looks like). At `e785` one `RM1021` arrow stands half under an island slab.

## `Q132` — The longitudinal lines come from TD's survey; where TD is silent nothing is drawn

**Status.** Closed, the user's call. Built as `P3-34b`–`d`; `draw_centre_line` and `draw_lane_lines` are off.

- No inferred fallback. Where TD surveys the divider it is broken on 80–90% of it (`RM1104` WARNING LINE), so a double continuous line is the wrong instruction. Where TD is silent there is no marking within 1.5 m of the middle on 94% / 84% of stations.
- A code absent from one layer is not absent from the geodatabase: `RM1002`/`RM1003` are in `DTAD_RD_MARK_LINE_C`. `RM1101`+ is sheet `CT174/51-5(2)G` (rows in `DATA_SOURCES.md`). `RM1107` is the lay-by edge line, not a lane line.
- `RM1002`/`RM1003` LEFT / RIGHT are of the digitised direction (`RULEID` 2 / 3). A part digitised backwards is invisible to every counter; no site has been checked.
- Rows via `more_layers`: `lane_line` (`RM1101`), `warning_line` (`RM1104`), `double_white_left_broken` / `right_broken`, `centre_line` (`RM1103`). JAFFE ROAD (986 m) has no surveyed line and draws none.

## `Q133` — The ETL is refactored, not rewritten; the drawn road gets one reader

**Status.** Closed — `P3-35a`–`h` built, `P3-35g4` refused. The signal layer `P3-35a` deleted has since returned as an authored phase plan (`Q173`).

No rewrite and no new source: the code records defects that render as a plausible road under a green
`check.sh`, and the binding limit is one `width_m`, `lanes` and `offset_m` per edge, not the source
(HyD is silent on ~2% of level-0 length; no lane-count attribute exists, `Q57`).

- Refused: OpenStreetMap (unevaluated; ODbL share-alike meets hard rule 7; the user's decision
  only); a schema library for `config.py`; merging the four `_register`s (`Q78`, `Q115`); moving the
  YAML's prose to sidecars.
- `P3-35b` — `tools/battery.py`; its contract is in the root `CLAUDE.md`.
- `P3-35c` — `tests/test_surface_on_region.py` drives the shipped (region) path end to end and
  reads truth off the mesh. `carriageway[]` is written from the territory whatever the geometry did
  (`Q106`), so only the mesh read catches a broken `_shape`. Log-only counters
  `territory_mismatched_edges` / `territory_missing_edges`, 0 / 0.
- `P3-35d` — `pipeline/drawnroad.py` is the one reader of the drawn road (`Ribbon`,
  `kerbed_ribbons`, `kerb_target`, `past_kerb_m`); signs, lamps, the fence and railings register
  to the real kerb, not `±half` about the centreline. Extent chosen by grading iB1000 lamp posts
  read as in the road (Wan Chai / Causeway Bay): `±half` 21.8% / 14.5%; `roadsurface.json`
  per-vertex `corridor_*` 24.2% / 8.7% and signs `shift_m` p90 1.34 → 4.24 m — refused; shipped
  (each side at kerb-ended stations) 13.3% / 3.6%. The share's rail (`Q57`) is refused too: a post
  hosted by an inner share would register to mid-asphalt.
  - `offset_m` is positive to the nearside of the published direction; the fence row's tangent
    points into the street, so the sign reverses at an end mouth (`fence._ribbon_at_end`).
  - Railings: where from `Ribbon.kerb_at`, side = the nearer kerb about the road's middle, facing
    toward `Ribbon.middle`. `railings._own_places` drops a kerb station within `min_station_gap_m`
    of a published vertex; `_sides` takes the plain offset, not `surface.boundary`'s (a fence is a
    line, not a polygon). Smoothing `bends` is refused: Douglas-Peucker made it worse (84 → 91), a
    moving average gave back a third of the registration.
  - "Panels standing in the road against the kerb line" reads 0 by construction (`Q58`).
  - Open: 259 of Wan Chai's 1,468 territory sides have no kerbed station and register against the
    16.5 m ray cap. Owed: the lamp-post grader as a `tools/` instrument.
- `P3-35e` — the paint flanks and their stations are deleted. A region-less bundle (tests only)
  draws nothing under a box overhanging its ribbon. `_opposed_gaps` → territory adjacency stays out
  of scope (owes `Q117` / `Q125`'s proofs).
- `P3-35f` — `pipeline/drawnsurface.py`, `tools/_lib/`, `pipeline/config_blocks/`; `config.py`
  re-exports every name. `load_config` refuses any key no parser asked for; iterating a mapping
  reads all of it, so this is a floor under the per-block checks. Proving a tools move needs
  `--tools-from side` against a worktree of the commit before.
- `P3-35g1` — `surface._slid_onto_deck` slides an off-grade ribbon onto its deck before
  `_clamped_rails` cuts it; published `offset_m` stays the intent. Not `Q103`'s refused
  deck-middle offset. Three refusals, no knob: an `inf` rim, a ribbon wholly off its deck, a deck
  that would hold the ribbon twice. Wan Chai 274 slid / 28 refused; `e364` still starved (corridor
  1.94 m). ~12% of newly drawn area hangs (rims are per published vertex).
- `P3-35g2` — `pipeline/crossings.py` (`.claude/rules/crossings.md`). Each feature is polygonised;
  `faces_touching` must be 0. Colour is not published: `RM1070` zebra white, `RM1076` signal
  yellow, told apart by TD's surveyed zigzags — nearest zigzag 0.33 m from one crossing, 481.85 m
  from the next, so `zebra.within_m` 10.0 sits on a plateau. Use `region._box_sides`, never
  `minimum_rotated_rectangle`. `_is_convex` is not merged with `boxjunctions._turns_one_way`.
  Not built: look-right / look-left glyphs, `RM1071`, zigzags.
- `P3-35g3` — hatching (`RM1035`–`RM1037`, lifting `Q65`'s scope refusal on the user's call) as
  two `marks:` rows on `axis: oblique`. A chevron is a 3-vertex V: none turns 10–30° (19 under,
  215 over), so `chevron_turn_deg` 20 sits in the gap. Debits: chevrons surveyed as two 2-vertex
  legs draw at 150 mm; `_on_its_own_carriageway` errs toward refusing (14%).
- `P3-35g4`, refused — a lane count off TD's lane lines (`width_evidence.py` `hosted_count`).
  Hosting fixes `Q127`'s over-count (24% → 79% agree) but pooled agreement is 82% / 75% against a
  high-80s bar set beforehand, for ten edges. No sweeping the rail clearance to reach the bar
  (`Q72`); not an argument for `draw_lane_lines`. Reopens only on an edge-by-edge account of the
  21 / 10 disagreements.
- `P3-35h` — the game places a lane about the middle of the drawn road (`RoadGraph._lane_centre`,
  `_offset_at` interpolating `carriageway_offset_m` per station). `edge_left` is taken before the
  asker's heading reverses `along`; `verify_road_graph.gd` asks both ways.
- Open: a `vertex_station` mismatch falls back silently (counted); nothing checks the age of a
  build a battery side points at.

## `Q134` — Paint stands where TD surveyed it: arrows off the lane slot, and the decks' paint read

**Status.** Built (`P3-36`, `P3-37`) on the user's report from FLEMING ROAD; the user's drive owed. Supersedes `Q96`'s placement half.

- Arrows (`arrows._placed_offset`): an arrow stands at its surveyed offset where the point is
  inside the host's share or on the drawn level-0 road (`DrawnSurface.covers`); else at the slot
  `_lane_of` chose, counted `placed_by_slot` (16 / 6). Why: with `Q132` drawing TD's lines, the
  slot centre read as a fault (`lane_shift_m` p90 1.94 m). The share alone is not the road
  (`Q57`). The slot stays the lane-count instrument; refusing the `placed_by_slot` arrows is
  refused. `overlapping_drawn` counts pairs drawn within half a glyph (18 / 2).
- Decks: `road_marks.deck_codes` / `arrows.deck_codes` `[A01]`; `roadmarks.draw_decks` and
  `arrows.stand_on_decks` host a deck feature among off-grade edges only and stand it on that
  level's `DrawnSurface`. The void rule is inverted on a deck (the user's call): a piece the deck
  does not cover is refused and counted, never floated; on the street it is kept (`Q54`). Deck
  arrows have no slot fallback.
- Refused: `A03` and the bores (`Q21`); the inferred join off-grade (`Q125`); deck crossings and
  boxes; reading `_place_on_deck`'s coverage off `sample`'s `over_void` (it answers the point where
  the rule asks the piece's side).
- Open: the refused deck lines are unexamined edge by edge.

## `Q135` — Road paint stays mesh; what it costs a frame is measured, and it casts no shadow

**Status.** Built (`P3-38`–`P3-42`, `P3-66`, `P3-67`); the user's drive owed. Open: which deck, where two cross.

- Paint stays mesh. `mesh_contract.gd`'s texture refusal is a default a call site overrides with a
  declared budget (`Q63`), not a hard rule. Refused: decals (the Mobile renderer keeps 8 per
  object, from the engine docs, unmeasured on 4.7, against ~48 features a road chunk; the exits
  are Forward+ or ~10x the road meshes); a region texture (~60k x 40k px at 25 mm a texel); shader
  paint on the ribbon (`Q132`). Held: a striped texture for boxes and zebras, if distant hatching
  is judged unacceptable from the driving seat.
- `drive.sh --hide-layers=` measures a layer's frame cost. `tools/resident_budget.py` prints the
  paint: never streamed, so resident from every camera (Wan Chai's worst camera 144%).
- `P3-38`, `P3-66` — `GeneratedLayer.LAYERS` carries required `casts_shadow` and `shadow_meshes`;
  what lies on the road casts none, and a sign casts from its `pole` only (`verify_signs.gd` holds
  the name). Set on the node, not the importer. Refused: signs as a `MultiMesh` per cell (+65 to
  +94 draws); merging signs into cell meshes (reverses `P5-2`'s library, moved 2,694 px).
  `Q115`'s "`prims` counts a `MultiMesh`'s base mesh once per pass" does not hold on 4.7.2.
- `P3-39` — a street arrow's heights are the drawn road's under its own tail and nose
  (`arrows._end_heights`); an end over nothing drawn keeps the centreline's height and is counted
  (`ends_off_drawn_road`), never refused. Left: 9 / 21 arrows deeper than 10 mm, unexamined.
- `P3-40`, `P3-42` — `roadmarks.glb`, the boxes and the crossings are a mesh per 300 m cell
  (`meshbuild.CellBuilder`, `cell_m` per block); a piece goes whole to its centroid's cell.
  Refused: one shared piece-placer (the shared arithmetic is already
  `DrawnSurface.sampled_pieces`); streaming the cells; a 150 m tile (draws); signal crossings
  folded into the box mesh; a smaller cell for the boxes (half of Wan Chai's box paint is in one
  cell — 9,411 triangles at the start line against an 8k bar; 600 m is worse).
  `verify_crossings.gd` reads a crossing's kind off the cell's name, not its material.
- `P3-41` — `A01` says "on a structure", never which, and the lines carry no Z, so a deck feature
  is hosted by the plan-nearest edge over every level above the street. Where decks cross the
  level is a guess, counted as `deck.under_another_deck` (Sha Tin 33 markings / 324.1 m; shipped
  regions 0). No rule picks the deck (`Q54` inverted); it waits for Sha Tin to ship.
- `P3-67` — `tuning/prop_cells.tres` cuts the listed prop layers into a `MultiMesh` per 300 m
  cell with `visibility_range_end` 400 m; game side only. The range is to the cell box's centre,
  so a prop up to ~210 m nearer can be hidden. Refused: a 150 m cell (+20 to +35 draws), merging
  lamps into road chunks, the signs in the list.
- `box_extent.py` reads 0.23% of Wan Chai's box paint over nothing drawn (1.32 of 577.90 m²).

## `Q136` — The minimap is drawn from `RoadGraph`, once, and switches off on its own

**Status.** Built (`P3-44`) — the user's drive, `span_m` and the web build's clip frame owed. Side moved by `Q138`; the panel became a round scope in `Q163`.

- Source is the `RoadGraph` in memory: no ETL change for the roads. One static mesh in plan
  metres; per frame only its transform moves. Levels ascend with a casing under each deck.
  Refused: a `draw_polyline` an edge (a draw call each); an orthographic `SubViewport` (a second
  city pass); an ETL-baked texture. Built naively the mesh was +37,696 `prims`; shared junction
  caps, one bevel a turn and dropping sub-0.4 px vertices cut it to +12,210.
- Tuning in `tuning/minimap.tres` (`span_m` 320). `--minimap=off` is separate from `--hud=off`;
  `P3-9` runs with it off.
- The projection is a pure static function `verify_hud` asserts. The defect to catch is a
  mirrored map: east is right when heading north. One compass convention,
  `CityManifest.bearing_deg`'s.
- Heading-up (the user's call); north-up stays a `.tres` bool, both asserted.
- One-way arrows are off (`arrow_px = 0`, the user's call: unreadable at this scale); the code
  stays behind the dial. A triangle on the rim points at a target off the map
  (`Minimap.beacon_point`).
- Main roads are drawn apart: `roads.py` joins iB1000 `StreetCentreLines.STREETTYPE` by `ST_CODE`,
  placed by the nearest same-code segment (the per-code majority misclassed 38 of 762 edges);
  published as `street_class`. Convention Avenue's `ST_CODE` 10334 is in no sheet, so it stays
  unclassed.
- The harbour and parks come from `basemap.json` (`Q140`, `Q144`), first in the mesh.
- The street name's lettering is cut to fit, not its box (`StreetPlate.fitted_size`, measured off
  the font: a `Label` out of the tree reports no minimum size).
- Not seen on the web build: `clip_children` exports, but the headless screenshot returned the
  splash.

## `Q137` — A router is built; a route line on the map is not

**Status.** Closed — router built (`P3-43`); the "no route line" stance was reversed by the user (2026-09-24): the legal route is drawn (`P3-46`). Held: the next-junction arrow.

- `scripts/city/road_router.gd`; the search state is a directed edge, built from `RoadGraph`'s
  accessors, U-turns refused. `prepare(edge, t)` runs one reverse Dijkstra per destination;
  `route()` is a lookup (`prepare` ≤ 1.86 ms, `route()` p50 5 µs). A* is refused: 40% of ordered
  fare pairs have no route, and an unreachable query exhausts its component.
- Cost convention is `tools/reachability.py`'s exactly; lengths are 64-bit (a float32 sum drifts
  4.7e-4 m). `verify_road_graph.gd` and `verify_join.gd` diff every pair against
  `reachability.json` at 0 m.
- Two profiles, never merged (`Q19`): `Profile.legal()` (direction, turns, no U-turn, lane bar)
  and `Profile.player()` (`is_drivable and fits_car`). The shipped profiles are not the survey
  population, so they are pinned by monotonicity.
- "No route" is an answer: `Route.found` false.
- The route line is the fare's own legal route (`Fare.route`), refreshed at 5 Hz while carrying,
  seeded the way the car faces (`Facing`), drawn by `MinimapMesh.route_mesh` at `route_px`; no
  route is no line. `hud.gd` rebuilds only when the edges change or the start moves `ROUTE_STEP_M`.
- Not built: a route while idle, a route on the player's profile.
- Mutations and the rest: `.claude/rules/router.md`.

## `Q138` — The HUD takes the racing-game arrangement, and every known future component has a graded slot

**Status.** Closed — the user's call, built with `P3-44`. "No award in the middle" reversed for one line by `Q212`; a pause button added by `Q165`.

- Map bottom-left, speed bottom-right: left is the world, right is the car, top is the fare, the
  middle is the road. Supersedes `Q80`'s sides.
- On touch each readout sits over the thumb that acts on it; handedness lives in `steer_zone()` /
  `drive_zone()` (`Q83`).
- Every HUD component a planned task adds gets a reserved rect in `hud_layout.tres` that
  `verify_hud` grades (`timer`, `combo`, `meter`, `award`, `callout`, `tick`, `pause`).
- Refused: a slot for the destination arrow (it is in the world, `Q80`).

## `Q139` — One voice: the cab's instruments in one dark housing

**Status.** Closed — the user's calls, built with `P3-44`. Superseded by `Q163` for every panel but the meter's box and the map's field.

- `plate_field`, `chip_field` and `map_field` are one value, dark and opaque (`verify_hud`).
- Red digits are the fare's; speed was never on a meter. Speed is `SpeedDial` (ticks and an amber
  needle, held off red); the fare, tip and session total are `SevenSegment` LEDs. The total has 6
  cells against the fare's 5 and `total_lit` is `meter_lit` at 65%, so tip and total are told apart.
- Every look stays in `hud_style.tres` and out of `hud.gd` (a second car's cluster is a second
  `.tres`).
- `verify_hud` asserts the segment table in letters, not by count.
- Refused: seven-segment for the speed; a dot-matrix face for the street name (a fifth licence,
  `Q79`).
- Both sides of a draw-count A/B are re-run together.

## `Q140` — The harbour is a frame minus the land, and the land is north of the sheets we hold

**Status.** Closed — the user's calls, built as `P3-45`: on the minimap and in the world. The user's frame owed.

- Source is iB1000. Not OpenStreetMap (`Q133`), not the 3D map's `WATERBODY` (hillside features),
  and `HydroPolygon` is inland water only. The sheets publish no sea polygon:
  `pipeline/basemap.py` cuts the frame (read box + `reach_m` 320) along `Shoreline` and a piece
  with no `Building` on it is sea.
- The region's own sheets stop short of the waterfront, so `topography.fetch_margin_m` 320 fetches
  the ring, and `config.py` refuses a `reach_m` past it: a missing sheet reads as open sea.
- Bridging loose shoreline ends was built and refused; thickening the line by `seal_m` 40 closes
  the one real gap (~35 m) at the price of any inlet under 40 m. A pier narrower than `seal_m` is
  sea, and its building stands on nothing.
- The world: `water.glb` is the sea triangles flat at `water_level_m` 1.3, one draw a region, no
  collider, no shadow. A plane over the terrain as shipped fails — no level separates sea (1.1–4.2
  m) from shore (2.7–4.9 m): at 3.0 m 9.6% of the sea shows through, at 3.5 m ~40% of the shore
  band drowns. So `buildings.sink_sea` drops terrain vertices inside the sea to `seabed_m` −3.0
  before decimation. Refused: draping the plane, no depth test, flattening instead of sinking.
- Colour obeys `Q33`: `sea_water` is 8.2% diffuse albedo; the blue is the sky off
  `tuning/water.tres`'s roughness (0.45; 0.15 is a near-white mirror). Do not lighten the entry.
  Waves are per-pixel sine trains in its own shader, numbers in `water.tres`; each train takes its
  own `fract` (a shared wrapped phase jumped every 4 s — a jump needs a frame series to see).
- A car `drown_depth_m` (1.0) under the surface and inside the sea in plan is put back on the
  nearest edge (`drive_level.gd`). Both halves, never the level alone: the Cross-Harbour Tunnel
  approach is 8 m under datum on dry road.
- The plane ends at `reach_m`; a skirt past it is a look question for the user.

## `Q141` — The 咪錶 runs Transport Department's tariff on what was driven; the skill is the tip

**Status.** Closed — the user's calls, built as `P3-1a`. The reach table, the pools and the allowance are superseded by `Q203`. The user's drive owed.

- `tuning/tariff.tres` is TD's urban fare (effective 14 July 2024, cited in `tariff.md`): HK$29
  for the first 2 km, HK$2.1 per 200 m or minute of waiting until HK$102.5, HK$1.4 after.
  `FareMeter` runs it on metres driven and seconds waited, in integer cents. No abstract
  multiplier. Most trips in a 1.5 km² region stay under the flagfall, which is why the tip carries
  the skill.
- Unit rule: "or part thereof" on two buckets; either exceeding its unit charges and resets both;
  no waiting charge inside the flagfall distance. `verify_fares` pins 2,001 / 2,200 / 2,201 /
  9,000 / 9,200 m.
- A shortcut lowers the meter, so speed is rewarded on the clock: the seconds left at delivery ×
  `tip_hkd_per_s` (0.5), banked with the meter as one HK$ sum. No separate score points.
- Par is `Profile.legal()` (`Q137`); the allowance is the legal route over `par_kph` (19, measured,
  `fares.md`), with no floor by kind (`Q203`).
- A pickup reaching no destination at `min_trip_m` (300) is stranded: dropped as a pickup, kept as
  a destination, counted and named. Wan Chai's `f_017`, `f_018`, `f_020` and Causeway Bay's
  `f_001` are closed as the data's — one-way streets leaving the clip. A new stranded node is a
  finding about the data, never a reason to lower the bar; a par route that breaks a sign is
  refused. Reopens with `Q6`.
- Refused: drawing a destination blind at the hail and retrying.
- The hail re-arms only once a sample finds no pickup in reach.
- `fare_system.gd` names no autoload (`verify_fares.gd` loads it before any exists).
  `--fares=off` is free roam; `--fare-seed=` seeds the draws.

## `Q142` — The pending customer is the pickup pool, said as its building; the arrow points as the crow flies

**Status.** Closed — the user's asks, built as `P3-5a`. The pool-is-the-customer reading is superseded by `Q203` (a live set of four); the flush layout by `Q163`.

- A stop is said as a passenger says it: the building, then the road. iB1000 `BUILDINGNAME` is
  joined in the ETL (`pipeline/fares.py::read_places`; `NAMESTATUS` `E` only, names pooled across
  sheets) and published as `fares.json` `place`. A node takes the nearest footprint within 25 m,
  unless the point's own text names a building inside that radius. `Fare.Stop.place(language)`
  falls back to the description; the road is `RoadGraph.name_of`. Refused: parsing the building
  out of TD's free text.
- The guide (`fare_guide.gd`, `tuning/guide.tres`) is a flat arrow over the car pointing as the
  crow flies, red and small far off, green and large near, with a pulsing ring on the road at the
  target. Unhailed it points at the closest waiting customer, in amber; hailed, at the destination.
- No goal box or clock until a fare is aboard. The box reads caption, building, road and the road
  distance left; the countdown stands bare in the middle; every meter tick flashes in `tick`.
- One language at a time (`Locale.language()`), Chinese the default; `FareFace` decides every
  string.
- A delivery at a stand that is also a pickup shows no pending mark there
  (`FareSystem.withheld_pickups`).
- The car starts `RoadSpawn.DEFAULT_SETBACK_M` (20 m) short of the stand, so the game starts when
  the player pulls forward; `--spawn-fare` starts on the node. Later starts: `Q227`.
- `verify_fares` refuses a drop-off-only point in the pool.

## `Q143` — A street the region cuts is closed on the line; the neighbour's way in never is

**Status.** Closed — the user's ask, built as `P3-29a`. The user's drive owed.

- A third fence population, not a third bar: `clipped_edges` in `fence.json` with its own
  counters; `fenced_edges` does not gain it (`RoadGraph.fits_car` re-derives that set).
- The rule is read off the built graph, never `neighbours:`: a node with one open arm, no
  `foreign_edges` run touching it, and the edge's end within `fence.clipped_within_m` (1.0) of the
  region rectangle from the inside. A neighbour declared and not built leaves nothing open.
- Trap: an owned run crossing the line is kept whole (`P5-7`), so its far end has degree 1 on the
  neighbour's ground. The test is the unsigned distance with the point inside the rectangle;
  `verify_fence.gd` re-derives the set from `region_extent_m`, never `bounds_game`.
- Left open on purpose: level −1 tunnel ends on the line (`Q21`), a fenced edge's line end,
  cul-de-sacs inside the region.
- Cost: 239 + 61 barrier units; Wan Chai's barrier layer is 60,672 triangles.

## `Q144` — The parks in the world are the ground painted green, every code the minimap draws

**Status.** Closed — the user's calls, built as `P3-47`. "Trees are not built" reversed by `Q171`. The user's frame owed.

- `buildings.paint_parks` recolours terrain vertices inside `basemap.json`'s `parks` to
  `materials.park_grass` before decimation: no mesh, draw call or collider change.
- Every open-space code (`PAR`, `PLA`, `SOA`, `SGR`, `PRO`), the user's pick over `PAR` alone.
- `park_grass` is 10.0% (mown turf's luminous reflectance, `Q33`); dark on purpose.
- No schema bump: `COLOR_0` already means reflectance; a new material has no game half.
- The edge fades over one ground triangle and long triangles draw a green streak. Cutting the
  ground along the outline is not built — a look question for the user.

## `Q145` — Skills pay flat money per event, the delivery is a receipt, and the passenger's face pops from the back seat

**Status.** Closed — the user's calls, built as `P3-49`. Drift bar and price amended by `Q172`; names by `Q169`; the combo is `Q205`. The user's drive owed.

- Each skill is a flat HK$ price in `tuning/skills.tres`, paid into `Fare.tip_hkd` as it is
  earned. Penalties are awards with negative `hkd`; `tip_of` floors the tip at zero and the meter
  is never docked (`Q141`).
- Drift pays per second held over `drift_slip_threshold_deg`, read from `handling.tres` and never
  restated (`Q84`). Refused: a second threshold in `skills.tres`; reading `_drift_engagement` (a
  held button on a straight would pay).
- Speed pays per `speed_hold_m` (200) driven at or over `speed_min_kph`; `verify_fares` refuses a
  value under `tariff.step_m`.
- The live tip is the skills alone; the time bonus is priced once at delivery, so the readout
  never runs down. The early arrival is named in the delivery caption.
- The delivery callout is a receipt: meter, time, each skill with its count. A bail reads "RAN OFF
  WITHOUT PAYING" / 乘客走數 over what was lost.
- The passenger's face is a low-poly mesh (`tools/make_emote.py`), not an emoji font (a fifth
  licence), rising through the roof from the rear kerbside seat; features on −Z.
- Skills run with the cab empty: one `SkillTracker` a session; `FareSystem._award` pays onto the
  fare when aboard, else emits `practised` — shown, never paid. Every award counts in
  `skill_counts`. Refused: paying practice into `earned_hkd`, or carrying it into the next tip.

## `Q146` — A start menu over the parked taxi; the language is the flag, then the saved option, then the OS, then Chinese

**Status.** Closed — the user's asks, built as `P6-1`. Camera per page is `Q164`; "no pause menu" reversed by `Q165`; the glass look is `Q163`.

- The menu is a `CanvasLayer` under `GUI`; `Main` parks the level (`DriveLevel.park` / `resume`):
  pedals gated, fare tick held, guide hidden, physics running.
- The car stands at `showroom_fare_id` `f_001` (Harbour Road) — the start line is under a podium
  soffit. The same chase rig, so the streamer keeps one camera.
- Language order: `--lang=`, the saved option (`Settings`, `user://settings.cfg`),
  `OS.get_locale_language()`, then Chinese. `drive.sh` appends `--lang=zh --menu=off` unless the
  run names them, so frames compare across machines.
- The credits discharge hard rule 6; `verify_menu.gd` fails `check.sh` if the ownership sentence,
  either portal, the typeface or the CC BY name leaves `menu_text.json` in either language.
  `LICENSING.md` item 2 (the lawyer's sight-check) stays open.
- Engine third-party notices are read from the engine (`EngineNotices.compose()`:
  `Engine.get_copyright_info()` and `get_license_info()`), never pasted.
  `Engine.get_license_text()` is the MIT screen alone, not the notices.
- The guide's steps are drawn `GuideCard`s, not screenshots (a screenshot of the city is generated
  data, hard rule 7).
- Refused: a `TranslationServer` / `tr()` port; a second camera; a third language.
- `--menu-page=` opens the menu on a named page.

## `Q147` — A carved ramp's edge is jumpable, and the flight is a skill paid at the landing

**Status.** Built (`P3-51`) — air skill shipped; the parapet band ships on the eight carved ramps; the every-deck-edge band was built, measured and withdrawn on the user's call.

- Nothing synthesises a rail on a deck edge. What stops a car is the source `INFRASTRUCTURE`
  parapet, the 0.15 m kerb, and on the eight carved Wan Chai ramps the carve's cut face.
  Reverting `P3-28` / `Q104` was asked and refused: it restores the block in the carriageway.
- Air skill: `VehicleController.is_airborne()` / `is_upright()`; `SkillTracker` pays `air_hkd` on
  the first grounded tick after `air_min_s` (0.5 s) aloft, again per `air_s`, only if upright. At
  the landing, never per second in the air (that would pay a car falling off the world). The
  drift meter refuses airborne ticks.
- Parapet band (`carve.parapets`): population is the carve's own `edges`; `levels` and
  `on_structure` widen it and both ship off (`[]`, `false`). The band runs from the deck's rim
  (`deck_rim_m`) out `reach_m` 1.5; a wall or cap whose top is within `wall_max_m` 2.50 of the
  deck is a parapet, anything higher stays. A parapet is taken whole by its centroid after one
  floor cut, with no prism — per-station prisms grew Wan Chai's tiles 974,450 → 1,433,856
  vertices, and two prism variants left 1,120 and 7,492 slivers on one tile.
- Every deck edge (`levels: [1]`, `on_structure: true`), withdrawn: it removed 11,741 m² of
  published structure in Wan Chai on a design call and grew the tiles 4.6%; the user kept the
  flyovers' parapets. The switch is one config line.
- The ramps' cut face is capped at the deck plus `parapets.face_above_m` (0, flush — a 0.30 m lip
  sat in `Q19`'s beaching band); uncapped it stood up to 1.12 m over `e99`. The cap takes the
  higher of a segment's two stations, or a slit opens into the hollow.
- Shipped: 8 band rows, 665 m² removed in Wan Chai; Causeway Bay 0.
- Kept: flyover parapets, the cut faces below the deck, tunnel touchdown fences, the kerb.

## `Q148` — The penalties are three tiers on the speed into the wall, read off the skidpad's wall rows

**Status.** Closed — the user's ask, built as `P3-50`. The dead stop at 30° / 90° found here is fixed by `Q151`; hits on moving cars are `Q175`. Crash-tier drive owed.

- `VehicleController.take_impact_mps` latches the pre-step velocity along the contact normal;
  `SkillTracker` tiers it: under `bump_min_kph` (20) a free touch that still ends a slide; at or
  over it a `BUMP` docking `bump_hkd` (2); at or over `crash_min_kph` (60) a `CRASH` docking
  `crash_hkd` (5). `crash_cool_s` (1 s) makes one wall one dock.
- Bars are read off `tools/skidpad.sh --only=wall` (`--wall-deg`), speed into the wall in kph at
  63 / 86 / 105 kph entry: 10° 11.2 / 15.2 / 18.4; 30° 34.1 / 44.8 / 53.9; 90° 69.5 / 90.5 /
  108.3. So 20 frees every brush and 60 splits the hardest clip from the softest head-on.
- The latch reads `_velocity_into_step`, never `state.linear_velocity`: the solver has already
  removed the normal velocity (a 69.5 kph head-on read 1.6 kph).
- Refused: a per-tick speed-loss detector (braking and `place_at` read as a wall); the engine's
  contact impulse (measures the solve); a kerb penalty (a kerb mount reads no hit); a price for
  the touch.
- `last_impact_mps` is for readers that must not drain the latch.

## `Q149` — A refactor pass over the game scripts and the verify tools: what moved, what was found, what was refused

**Status.** Closed — the user's ask; eight batches over `game/scripts` and `game/tools`. Its deferred tuning migration is `Q150`.

- Standing shapes: `tools/verify_layer.gd` (one init for the per-layer verify tools);
  `tools/verify_tool.gd` (one base with a watchdog, extended by path); `CityManifest.shared`;
  `TuningTable.any_zero`; `FareFace.target_of`.
- Not refactored: a shared predicate under `is_passable` / `fits_car` (`Q19`);
  `HandlingProfile.PATH` is live. The ETL was left out — its duplication is deliberate.
- Found: `surface_get_arrays` returns `null` for an absent array, so `MeshContract`'s winding
  checks threw before their guard (`_indices_of`).
- Deferred: `VehicleLamps`'s indicator and lighting-ladder policies into `scripts/core/` (needs an
  A/B render).
- A mutation must compile, and is undone from a copy, never `git checkout`.

## `Q150` — The taxi rigs' dials are tuning resources, one profile per script, and a zero key makes a rig inert

**Status.** ✅ Closed — `Q149`'s deferred migration, on the user's call for one profile per script.

- The rigs' dials live in `tuning/vehicle_lamps.tres`, `taxi_door.tres`, `passenger_emote.tres` and
  `beams.tres`, each assigned as the node's `profile` in `taxi.tscn`, each with a sidecar. The
  emote's three face `PackedScene`s stay on the node: asset links, not tuning.
- Each rig's `usable()` is pure over `profile` (`TuningTable.any_zero`). Inert means lamps never
  tick or write a beam, the door stays shut, no face goes up, `BeamBudget` grants nothing.
  `BeamBudget.adopt(table)` is the one path in.
- Required set = every key whose `@export_range` floor is above zero, nothing else: a key the editor
  may legally write as 0 cannot be told from a missing one. The unguarded keys are named in each
  sidecar; closing that hole is a floor (schema) decision.
- Trap: Godot's writer drops any key equal to its script default, so a script-side default hides an
  empty `.tres` (`beams.tres` was empty this way). Profiles carry no second copy of a value.

## `Q151` — The wall slide reads the velocity the wall met, so a clip deflects instead of stopping the car dead

**Status.** ✅ Closed — built and graded on the wall rows; the scrub it left open is answered by `Q230`'s `collision_align_s`.

- `_integrate_forces` computes the arcade wall response (`velocity.slide(normal)` scaled by
  `collision_speed_retained` / `collision_deflection`) off `_velocity_into_step`, the same velocity
  the impact latch reads (`P3-50`), and chains it through the contact loop. `state.linear_velocity`
  there is already solved: the normal component is gone, so the slide was a no-op and a 30° clip
  stopped dead (exit 0.09 kph; 28.8 / 51.3 / 76.2 after the fix at the three run-ups).
- Anything new in `_integrate_forces` reads `_velocity_into_step`, never the state.
- Spin is halved once per tick (`SCRAPE_SPIN_RETAINED`), not per contact: a head-on reports two or
  three contacts on one slab.
- A head-on stays a stop by construction (`slide` leaves nothing along a face met square).
- `collision_deflection` scales the first tick only; the speed lost after a clip goes to the tyres
  while the nose stays into the face.

---

## `Q152` — A per-wheel tyre model on `VehicleBody3D` can hold a physical slide, and costs the car its everyday cornering

**Status.** ✅ Shipped on the user's call (`P3-52`): the tyre car is the game's only car. Its catch-round refusal of a keyboard ramp is reversed by `Q210` (the cap stays).

Grading rules for every row named here are in `.claude/rules/handling.md`; live values are in
`tuning/tyre.tres`, `tuning/systems/*.tres` and their sidecars.

- **The model.** `Q50`'s engine is kept (Godot's suspension ray, spring, damper, contact). The
  engine's tyre force is off (`wheel_friction_slip` 0) and `TyreVehicleController` applies a
  per-wheel force at each contact from `TyreProfile`. `city_drive.tscn`, `skidpad.tscn` and
  `greybox.tscn` instance `taxi_tyre.tscn` (which inherits `taxi.tscn`); `verify_vehicle.gd` refuses
  any other car or table. A table the model cannot run parks the car. There is no off switch and no
  engine-tyre control car; its grip-cut and yaw-torque drift (`Q84`–`Q89`) went with it.
- **Load is rebuilt exactly** from Godot's own ray and spring. Trap: the ray starts one radius above
  the hardpoint and the hit is rescaled onto the rest length; read as the hub's drop minus a radius,
  the four loads sum to 1.50× the weight. The pad prints the at-rest sum as `loads:`.
- **Wheel spin is solved implicitly** (safeguarded Newton, 8 substeps, brake as Coulomb friction).
  Stepped explicitly a braked wheel limit-cycled and the car crept at 1.2 m/s with the pedal down;
  clamped at zero slip the tap fell 35° → 8°.
- **The forward force is never capped on a turning wheel** (a one-tick cap held the car to 8.5 kph
  after 4 s of throttle); the sideways force keeps its cap near rest.
- **`side_force_depth` is a drift dial.** At the contact the car rolled over on a kerb at 86 kph; at
  Godot's `roll_influence` 0.2 nothing slides (`hold` peaks 5.9° / 4.4°).
- **No automatic countersteer.** The user: "i want counter steering to be part of gameplay". The
  assist was built, made an option, then dropped (`Q153`). Do not re-add one to lengthen `ride`.
- **`slide_lock_deg` is refuted and absent**, mechanism kept: a wider lock while sliding read as a
  SHORTER `hold` at every speed (86 kph: 1.40 → 0.90 → 0.40 → 0.33 s at 0 / 24 / 35 / 45°). The
  pad's driver commands a share of the lock, so the row re-tunes the driver, not the car.
- **A countersteer does not snap; it turns.** `catch` reads under 0.4° of slip the other way at any
  timing. Once caught, full opposite lock on gripping tyres turns the car the other way at about
  85°/s, and a key holds full lock. A lock-to-lock reversal runs at `steer_attack_s` the whole way
  (`steer_release_s` applies only while the target is inside the current angle). The heading
  reverses before the slip reads as caught, so a lever keyed on slip is late.
- **The catch limiter** (`CatchLimiter`, `arcade_aids.catch_*`): once a tail-out slide's heading
  turns the other way, the fronts are capped at `catch_lock_deg` while the player still steers that
  way. `yaw@hold` over a 1.5 s hold: +52° uncapped, within 2.4° of flat at 6°. It caps an angle and
  adds none (`Q72`). The side latches only on tail out (yaw and countersteer sign disagree): latched
  on slip alone it took a turn-in plough for a slide (tap peak 28.0° → 22.3° at 42 kph).
- **Skill bars not re-set for this car**: `speed_min_kph`, `bump_min_kph`, `crash_min_kph` were read
  off an older, slower car and are the user's call; `skills.md` carries the wall matrix.
- **Owed.** The tyre model's cost on a handset (about 216 µs a tick on the desk, `P0-3b`); a wheel
  lifting at a kerb at speed.
- Hands-on pad drive: `godot --path game res://scenes/dev/skidpad.tscn` (5 m grid,
  `GreyboxBuilder.ground_grid_m`). A trial tyre table on the street: the run skill's `--tyres=`.

## `Q153` — Arcade grip, sim-lite slide: the drift is where the skill lives

**Status.** ✅ Closed on the user's calls. Its `mu` 2.0 / gravity 1.6 car is reversed inside this record by the real-taxi baseline; the pace moved to `Q156`, the drift's pay bar to `Q172`, key shaping to `Q210`.

**The design.**
- Pillar 2 reads **easy to drive**: the ease comes from hidden aids (traction control, stability
  control, the speed-narrowed lock, the catch limiter), not from unrealistic grip.
- The drift is the one place for sim-lite skill: easy to start, forgiving to lose, held longer by
  the player's throttle and countersteer, paid per second (`Q145`, `Q172`).
- Reference is Forza Horizon's split, not Mario Kart's. The button guarantees the start and is
  never the holder. Real technique works in the direction a driver expects. Borrowed from Mario
  Kart: legibility only (a tier that grows while held). No boost: a drift buys line, never pace.
- A drift lever takes power away or filters an input; it never asks for a slip angle (`Q72`).
  Stability control's yaw brake (`Q156`) is the one stronger hand, a ceiling.

**The car.**
- **A real taxi is the baseline** (the user): physical numbers are a Toyota Crown Comfort LPG's
  (`tuning/cars/crown_comfort.md`), on a road tyre's `mu` 1.0 and gravity 1.0; gameplay is layered
  on top as aids, never by bending a physical number. The body collider is the real 1.695 m wide,
  mirrored in `clearance.car_width_m` (`hong_kong.yaml`) and the `CAR_WIDTH_M` defaults in
  `tools/`, which move with it.
- **`mu`, gravity, the drive and the handbrake's torque move together.** At `mu` 2.0 under gravity
  1.6 the tyres held about 3.2 g, so a lift or a feint never unloaded the rear. `mu` 1.0 under the
  old torques spun every tap (164–180°) and no stability dial helped. `Q156` derives the handbrake
  and scales gravity through the pace; the drive is still authored.
- **The drive** is launch force `engine_force` up to the speed where `engine_power_kw` ×
  `driveline_efficiency` ÷ speed takes over, sized per driven wheel on its own rim speed
  (`_drive_force_at`): a spinning wheel gets no more power than the engine has. `taxi.tscn` zeroes
  Godot's linear damp; air is `drag_area_m2`.
- **Slip is read at the rear axle** (`VehicleController.rear_axle_velocity`) by the fare, drift
  mode, stability control and the pad. At the centre of mass a gripping full-lock turn read 15° by
  geometry and paid as a drift. Past 90° (`REVERSED_SLIP_DEG`, a car rolling backwards) the slip
  cuts stand aside, or a spun car gets no drive.
- **`steer_to_grip`** caps full input at the angle the tyres can use (full key lock put the fronts
  at 2.54× their grip at 50 kph). It lifts only on the countersteer side of a slide and in drift
  mode.
- **The rear side cut** (`arcade_aids.drift_side_cut*`) starts the slide: while the button's ramp is
  engaged the rears' sideways force is capped at a share of what the turn asks, latched on the speed
  at the press (`Q89`). Capped, not scaled: scaled, the tyre ran more slip angle and held. Known: a
  straight-line press inside the band leaves the rears no sideways force through the ramp.
- **`drift_mode.rearm_on_steer_release`** ends the slide: traction control returns the tick the
  steering is let go. Never on a reversal: re-armed on a countersteer, `hold` fell 2.63 → 0.60 s.
- **The flick** (`FlickWatch`, `arcade_aids.flick_*`): a lifted or braked feint, then the steering
  across within the window, stands traction control down as the button does, never the side cut. A
  held-throttle feint never fires (a slalom). On the real car the tail barely comes round; the
  figures are in `.claude/rules/handling.md` and `systems/arcade_aids.md`.
- **The drift assist is gone** (the user: "if all drift assist do is just auto counter steer, we
  should drop it first"): the automatic countersteer, its slip-cut band, the menu option and
  `--assist=`. One car, graded on `ride` and `hold`.

**Measured shut.**
- **A feint alone does not break the rear**: peak slip ≤ 8.7° for any feint of 0.35–1.5 s at 42 /
  63 / 86 kph. The car is front-limited: fronts at or past their peak, rears at 0.3–0.9 of theirs.
- **No single dial gives a flick and keeps the corner** (nine swept). What frees the flick frees
  `corner` too: traction control off slides both to 40–48°; a raised centre of mass spins.
  `side_force_depth`, the lock at speed, `steer_attack_s` and the understeer cut leave it under 9°.
- **`understeer_power_cut` is not re-keyed on a yaw-rate deficit, and traction control is not put on
  the tyre's combined slip** (tried twice). The deficit band is 85–90% holding against 70–86%
  ploughing. The governor parks the rear at its 8° peak: 0.82 / 0.73 g against 0.91 / 0.85 at 63 /
  86 kph, pull-away 26.9 kph against 30.8.
- **Every tyre dial failed to start the 90° drift at 42 kph**, as did a truly locked, declutched
  handbrake (no slide under about 60 kph, 40% of the speed gone).
- A technique is graded on windows around its input against a control that differs by that input
  alone, never on 4 s totals (a coasting car turns tighter by itself; that read as a +132° pivot).

**Open.**
- Whether the lifted flick should slide again (untried lever: the trigger taking the side cut).
- The trail-brake ploughs at 42 kph (a binary full brake on fronts near their peak); candidate: a
  brake share while the fronts are turned.
- Handbrake-and-lift in a turn spins at 63 / 86 kph; a big input, the user's call whether to forgive.
- The user's street drive is the veto on every drift value.

## `Q154` — The drift is shown on two signals: the tyres mark the road, the tracker lights the sparks

**Status.** 🟡 Built (`P3-57`, `P3-58`) on provisional values; open on the look alone (colours, tier count, smoke), the user's pick from frames.

- Two layers, two signals. Marks and smoke are the tyres' (`TyreVehicleController.wheel_slips`: any
  slide, wheelspin or lockup, paid or not; `tuning/skid_marks.tres`). Sparks are the tracker's
  (`SkillTracker.drift_tier`, the meter that pays; `tuning/drift_sparks.tres`), so a spark is a
  counted slide. No third slip reading (`Q84`, `Q145`).
- No boost (`Q153`) and no fire (flames on a taxi in a real street read as a crash).
- Every mark is one draw call: one `ArrayMesh` ring of `capacity` quads written in place with
  `mesh_surface_update_vertex_region`, refused unless the stride is the 12 bytes written. A
  `StandardMaterial3D`, not a shader (a shader that fails to compile is invisible to `check.sh`).
- `CPUParticles3D`, not `GPUParticles3D`: the web build runs the Compatibility renderer.
- Sparks hang on the fare loop (`TaxiHire` wires `drift_tier_changed` to `DriftSparks.show_tier`),
  so `--fares=off` shows none; marks hang on the car.
- Cost: marks +1 draw call always, smoke +1 per smoking rear, sparks +1 per rear while lit.
- Owed: the user's look pick and drive; the handset's fill rate (`P0-3b`).

## `Q155` — The car's dials are its systems: one table each, named as the system names them

**Status.** ✅ Closed on the user's calls (`P3-59`). Since: the countersteer-assist table is gone (`Q153`), ABS was added, and the handbrake is a ratio (`Q156`).

- `game/tuning/systems/` holds one table per system: `traction_control`, `stability_control`,
  `drift_mode`, `handbrake`, `rev_limiter`, `anti_lock_brakes` (real cars') and `arcade_aids` (the
  game's own: the rear side cut, the flick, `steer_to_grip`, the catch limiter, the slide lock).
  `tyre.tres` is the tyre alone; the car's own numbers are its `CarSpec` (`Q156`).
- A new dial goes in the system it belongs to; an aid no real car has goes in `arcade_aids`.
- A system with state owns it in its class (`DriftMode`, `CatchLimiter`, `FlickWatch`); a stateless
  one is its table and a named function on `TyreVehicleController`. A null table parks the car;
  `verify_vehicle.gd` refuses any table but the shipped one by path.
- `tools/skidpad.sh --sweep=<system>.<field>=…` writes a system's table.

Rename map, for reading older records and sweeps:

| Old (`tyre.tres`) | Now |
|---|---|
| `traction_limit` | `traction_control.wheelspin_limit` |
| `turn_drive_cut` | `stability_control.understeer_power_cut` |
| `slide_drive_fade_from_deg` / `_to_deg` | `stability_control.slip_power_cut_from_deg` / `_to_deg` |
| `traction_rearm_s` | `drift_mode.rearm_s` |
| `rearm_on_steer_release` | `drift_mode.rearm_on_steer_release` |
| `handbrake_torque_nm` | `handbrake.torque_nm`, now `handbrake.lock_ratio` |
| `rim_overspeed` | `rev_limiter.overspeed_share` |
| `drift_side_cut*`, `flick_*`, `slide_lock_deg`, `catch_*` | `arcade_aids.` + the same name |
| "traction control off" (`_traction_off`) | drift mode engaged (`DriftMode.engaged`) |
| `countersteer_assist`, `countersteer_lock_deg`, `assist_drive_fade_from_deg`, `drive_scale`, `yaw_assist_scale`, `handbrake_declutch`, `drive_boost` | removed |

## `Q156` — The car is a spec sheet, its forces are derived, and the game's pace is one named scale

**Status.** ✅ Shipped (`P3-60`–`P3-63`); `pace_scale` 2.0 on the user's drive ("i like 2.0, keep 2.0"). `Q170` renamed the button the handbrake; `Q172` re-set the drift's pay bar; `Q230` added the drive fade.

The user asked for no made-up physics parameters and real assist systems rather than "arcade god
forces", so that another car is a spec sheet and not a re-tune.

- **The spec sheet.** A car's own numbers are a `CarSpec`, one table per car under
  `game/tuning/cars/` (mass, limiter, launch force, power, drag area, brakes, lock at rest, centre
  of mass, wheel, suspension). `handling.tres` keeps the game layer.
- **A force the car's size decides is derived, never authored**: the brake (`brake_g` of the
  weight), the handbrake (`handbrake.lock_ratio` × `mu` × a wheel's load at rest × its radius) and
  a spring's ceiling (`suspension_max_load_ratio` × a wheel's load at rest), all through
  `VehicleController._wheel_load_at_rest_n`. Hand-sized, they were re-seeded at every change of mass,
  gravity or `mu`, and one missed round spun every tap at 168°.
- `armed_slip_cut_*` stays in degrees: its ends are swept dials, and deriving them removes the sweep.
- **Stability control brakes a wheel** (`stability_control.yaw_brake_*`): past a band of rear-axle
  slip the front wheel outside the slide is braked, in drift mode too. A spin left after the power
  cuts is the car's own momentum; a tyre force is bounded by that wheel's grip where a body torque
  is not. `yaw_brake_lock_ratio` 0 takes it out. It moved `turn@off` from 180 / 164 / 146° to 95 /
  118 / 110° at pace 1 and cost `hold` at 86 kph 0.9 s.
- **The pace is one scale on the world** (`tuning/pace.tres`, Froude scaling): gravity × the pace,
  forces follow it, speeds and clocks follow its root, power both; mass, `mu`, drag, angles and
  every input's seconds nothing. The car at pace k is the pace-1 car with speeds × √k. `.claude/rules/handling.md`
  holds the rules for a new dial; `pace.md` holds the tables.
- **60 Hz holds the scaling to pace 2.0 and not 2.5** (brake 19.7 of 22.8 m/s² at 2.5). A higher
  pace is a tick-rate decision first.
- **The player does not scale**, so dwell falls with the pace: no pace over 1.55 keeps `hold` over
  2 s at 42 kph (1.92 → 0.72 s between 1.55 and 1.6). Taken knowingly at 2.0; `Q172` moved the pay
  bar instead.
- **`drive_boost` is retired**: the pace is that, for the whole car.
- **`drift_side_cut` stays, measured**: at 0 the turn under-rotates (`turn@off` 59 / 78 / 146° at
  42 / 63 / 86 kph against 91 / 97 / 110°) and no handbrake ratio from 1.08 to 2.0 brings 42 kph
  past 70°. Its real replacement, a limited-slip differential, is deferred, not measured shut: a
  joint solve of both rear wheels in `_solve_spin`, graded on `turn` at 42 kph with the cut at 0.
- **The game's bars are not scaled**: they read real kph and real seconds, and each is the user's
  call (`speed_min_kph`, the wall tiers, `fares.par_kph`).
- **Open.** The lifted handbrake in a turn at 63 / 86 kph, which one front tyre cannot hold.

---

## `Q157` — The checks and the build run side by side, and each is proven against its serial self

**Status.** ✅ Closed — built on the user's ask; every parallel path is byte-identical to its serial run.

- `tools/check.sh` pools the warnings sweep and the per-region verify tools (54 s → 21 s);
  `CHECK_JOBS=1` is the serial form. One output file per job, a job with no status is a FAIL.
  `CLOCKED_TOOLS` (`verify_road_graph`) run first and alone: it reads the clock, and beside 35
  processes a maximum read 745 µs for 28.
- `verify_traffic` runs as one pooled job per `--part=` (its `PARTS`: each seeded drive, the
  census's hours, the staged checks), fed to the pool first and longest first across regions:
  whole it was ~240 s a region and set the run alone; `check.sh` went 290–305 s → 127 s
  (2026-11-18). Each part's lines are the whole run's, byte for byte, but for the `near:` group
  line, which the whole run reached in drive 0 alone: its `queue_free`d systems stay in the group
  because `_run` never yields.
- `pytest -n auto` (`pytest-xdist`, a dev dependency, 52 s → 10 s) is opt-in, never `addopts`: CI
  stays serial, which is what shows a test leaning on another's leftovers.
- `python -m pipeline --region <r> --jobs 4` (73 s → 30 s) starts a stage when the stages in `NEEDS`
  (`etl/pipeline/__main__.py`) are done, each as its own process. No stage opens another region's
  directory, so two regions build as two commands.
- Clipped layer reads are cached under `etl/.cache/layers/`, keyed on the source's size and mtime;
  `HK_TAXI_LAYER_CACHE=0` turns the cache off.
- `tools/battery.py … --jobs 4` gives identical outputs at every `--jobs`.
- Left alone: `roadmarks`' 10 s (`DrawnSurface._covering` repeats only 26% of 379,000 calls, so a
  memo buys about a second).

## `Q158` — The city takes an outline in its own hue, not a banded sun

**Status.** ✅ Closed on the user's pick from frames (`P3-64`, `P3-65`); the car's hull afterimage is reversed by `P3-70` (a light tail). ⚠️ The own-hue ink below is reversed by `Q248`'s amendment (2026-11-18): the line is black, the own-hue path behind `SURFACE_INK` and the colour copy gone with it. The handset's frame time is owed.

- **The outline ships**: `cel_outline.gdshader`, one full-screen quad (`CelOutline`) in both rigs,
  values in `tuning/cel_outline.tres`. It inks where the Laplacian of inverse depth is large (zero
  across any plane, non-zero at a crease or silhouette). Depth only: the Mobile renderer has no
  normal buffer. Not a hull per mesh: that redraws every tile against a 150 draw-call budget.
- **The ink is the nearer surface's own hue, darkened** (`ink_from_surface`, `surface_darkness`):
  the frame is read at whichever depth tap is nearest, so a tower's edge is the tower's colour.
- **The banded sun is not shipped** (`city_facade_cel.gdshader` stays as the switchable sibling,
  sharing `city_facade_clean.gdshaderinc`): it moved whole faces 3–6 `L*` and added no edge inside
  a face. It is a sibling shader because a `light()` replaces the engine's lighting outright.
- **Speed thins and fades the line, never bolds it** (the user): speed smears edges. The speed
  arrives as the `outline_speed` global, written only by the player's car (`car_outline.tres`).
- **A drift's afterimage is the brake lamps' alone** (`light_tail.gdshader`,
  `tuning/light_tail.tres`): streaks laid a tick at a time like the tyre marks. A dragged hull read
  as a second car past 0.15 m.
- Traps: at `edge_distance_m` 0 the far harbour stripes (depth rounding on a grazing plane); a pole
  under about two line widths inks solid; the pass is screen-wide and inks the car, roads, signs
  and fences too (a building-only mask is new machinery, not built).
- Cost: +1 draw call. Unmeasured on a handset: a visible depth reader likely makes the Mobile
  renderer end its pass, resolve the 4× MSAA depth (`Q91`) and copy it, plus a colour copy. Retreats,
  cheapest first: `ink_from_surface` 0, then the rigs' `CelOutline` hidden.
- Vehicle detail lines are `Q196`.

## `Q159` — The fences and the railings collide as a box per prop

**Status.** ✅ Closed on the user's instruction (`P3-68`); reverses the railings' no-collider stance (`P3-19`), a design call never measured shut. `Q191` extends it to posts.

- Every collidable prop stands a `BoxShape3D` over its own extent, one shape shared per prop, one
  `StaticBody3D` per placement (`PropBatch.bodies`).
- The closure barrier (`P3-29`) is a box over its `-col` trimesh's extent; the trimesh left open air
  under the bottom rail for a bumper to snag in. The `-col` stays the source of the extent.
- The railings, bollards and barriers take a box from each library mesh's AABB when `collides` is
  set on `region.tscn`'s `Railings` node; `collides = false` is the off switch. `railings.glb`
  stays collider-free and `verify_railings.gd` asserts it.
- The risk the old stance named, measured: no panel crosses a road centreline at its own level in
  either region. The measure is live (panels stretched to 8 m cross 149 times).
- No CCD on the car: a thin box resolves backward against the far larger hull.
- Breakaway stays `B3`. Owed: the user's drive into a railing and a barrier.

## `Q160` — The day runs to night as game time

**Status.** Built (`P3-69`) on the user's instruction; re-paced by `Q222` / `Q233` / `Q235`, looped for a free drive by `Q225`. Reverses "night is a switch between two static rigs" and `Q82`'s unlit lantern. Handset cost owed.

- One rig that blends, never two cross-fading: `LightingRig` blends a copy of the day's environment toward `tuning/day_to_night.tres`'s keyframes (`RigCycle`); `changed` tells cached readers (`SunGlint`, `VehicleLamps`).
- Game time is `DayClock`'s: seconds driven on the physics tick, held under the menu. `--day-cycle=off` (appended by `drive.sh`) keeps scripted frames in daylight; `--time-of-day=<0..1>` pins a rig.
- Two shader globals: `night_lights` (0 day, 1 night), which every lit layer multiplies its own `.tres` strength by, and `sky_light`, which scales the painted sky. Nothing lights by day.
- `exposure_anchor` does not move with the hour: it scales `COLOR_0` alone and would split walls from paint, fences and glass. The dark comes from the light.
- Lit layers: the lantern (`COLOR_0` alpha 0 marks luminous faces, `lantern_glow`); the pool on the road (`lamp_pool.gdshader`, a shader volume, not a light); floodlit buildings (`night_spot_*`); road paint (`paint_night_glow`); the outline's `night_colour`; tail lamps (`tail_lit`).
- Refused on the user's look: lit windows and an all-over building glow (`lit_window_share` stays 0.0); a cyan outline over a black sky.
- Trap: the daylight frame is not byte-identical to a build without the cycle. The cause is five recompiled shaders (0 px differ with the shaders reverted), not a value.
- Owed: the handset (the sky's radiance re-renders as the rig moves; levers `update_hz` and the pools' `radius_m`). No neon (`P3-8`).

See `game/tuning/day_to_night.md`, `.claude/rules/facade.md`.

## `Q161` — Parked vehicles before moving traffic

**Status.** Built (`P3-71`–`P3-73`, `P3-2a`) on the user's ask; parked trams removed by `Q176`, parked buses at stops by `Q187`, the taxi's body by `Q200`. Rules and counts live in `.claude/rules/parked.md`.

- `pipeline/parked.py` → `parked_placements.json` over the committed `parked.glb` (`tools/make_parked.py`). Sources in precedence: published bays (`ONSTREETPARK`, one point a bay, joined to `GISP_ON_STREET_PARKING` for class and hours), stops and stands, frontages, lay-bys, then a fill of the `NSR` complement.
- A published position takes no invented bar: a bay, stop or stand is placed wherever the junction trim leaves a kerb, and `published_in_lane` counts those that leave less than the lanes. `junction_m` and the lane-room bar refuse only the fill, a frontage and a taxi queue.
- The fill is a share, never a licence (57 of Wan Chai's 90 km of level-0 kerb is unrestricted). It and a frontage take `parked.slow_streets` only: `minor` class, ≤ 50 km/h, no bus lane, not one-lane, not on a structure, not the offside of a one-way street (the user: "cars dont park in fast lanes").
- A parked row takes one lane (`row_lanes` 1), and a two-way street parks one side unless it keeps its lanes past two rows. Demanding the authored lanes beside the row left 303 of 359 eligible Wan Chai streets empty.
- A lay-by is read off `carriageway_region`'s kerb line: a run standing 1.8–4.0 m proud of the edge's median kerb for 8–90 m (26 runs in Wan Chai, 16 in Causeway Bay). `RM1107` is 0 in region, so the geometry is the evidence. `laybys:` stands vehicles there on any street class.
- Time is the rig's `time_of_day` on `parked.tres`'s clock, never a second clock. A cell re-rolls only when out of range, so nothing pops.
- The near miss pays for danger, not proximity (`NearMiss`, bars in `skills.tres`): a pass inside `near_miss_m` at speed pays only when the vehicle was in the taxi's path shortly before coming alongside, with no touch. Inside `close_call_m` the path rule does not apply. A touch or flight while alongside pays nothing (`Track.spoiled`). `near_miss_m` is 0.9 after the user's logged drive (swerves at 0.69–0.85 m went unpaid at 0.6). Moving cars: `Q175`.
- Owed: handset frame time; the meaning of `RM1051` / `RM1052`; the user's drive.

## `Q162` — Two modes: 特更 to the handover, 兜風 with no end

**Status.** Built (`P3-74`) on the user's calls; shift length now `Q233` (840 s), sky keyframes `Q222`, free mode's sky `Q225`, free mode's END DRIVE report `Q189`. A full shift driven by the user is owed.

- 特更 / THE SHIFT runs 07:00 → 21:00 (`shift.tres`) over `day_to_night.tres`'s `length_s`, so the HUD clock and the sky end on the same game second. 兜風 / FREE MODE has no end. Both sit under one PLAY on HOME.
- One clock: `DayClock` carries the mode and emits `closed` once. `parked.tres`'s clock is 7/21 to match.
- The day does not stretch: a delivery adds money, never time (replaces `P3-2b`'s timer). No countdown on screen; the HUD shows the hour over "交更 21:00", then 最後一程 / LAST FARE.
- 交更: `FareSystem.close()` hails no one and lets the passenger aboard finish; `finished` follows, `DriveHarness` relays `shift_over`, `Main` opens REPORT.
- The best is in `Settings`' `records` section, a player's only: a scripted run (`--menu=off`) writes nothing. A tie is not a record.
- Free mode keeps daylight by default (`Settings.free_time()` "day"); fares stay on. Its hour is picked as it begins, never in OPTIONS (`Q266`).
- Dev flags: `--mode=shift`, `--shift-s=<seconds>`, `--menu-page=`.
- Out: an online leaderboard (zero network calls at runtime).

## `Q163` — One head-up display, not four boxes

**Status.** Built on the user's pick of three mockups; touch layout later by `Q204`, type by `Q218`. Details in `.claude/rules/hud.md`, `hud_layout.md`, `hud_style.md`.

- No housing but the meter's: clock, callout, speed and street name float bare with a dark shadow. The 咪錶 keeps its black box because it is a real meter. `verify_hud` holds the meter's and map's housing keys equal, dark and opaque.
- `HeadUpFrame` (corner brackets and a top/bottom vignette, one mesh) is what makes it one display. The map is a round scope (`ScopeDisc`) whose rim fade is also the clip.
- The menu is on the same glass, over `backdrop_blur.gdshader`. No blur in the drive: reading the screen back is a copy and a mip chain every frame on a phone. The menu pays it only while the level is parked; capturing the parked frame once would save that and is not built.

## `Q164` — The menu's camera follows its page

**Status.** Built on the user's ask.

- A `MenuShot` per page on `menu.tres`: HOME the turntable, PLAY the kerbside front three-quarter with the rear door open, OPTIONS at the tail, sheets high over the street, REPORT head on.
- One rig (`MenuOrbit`): the menu emits `page_shown(shot)` and the orbit eases toward it (`shot_response`); the opening page is cut to.
- Every standing shot sways: a still menu stalls a capture on "no frame drawn", and `verify_menu` refuses a shot that neither turns nor sways.

## `Q165` — The drive pauses the tree, not the level

**Status.** Built on the user's ask, reversing "no pause menu"; "no OPTIONS on PAUSE" amended by `Q223`, free mode's way out by `Q189`, RESET CAR added by `Q229`.

- `get_tree().paused`, never `DriveHarness.park`: `park` moves the car to the showroom and `resume` to the start line.
- `Main` stays pausable (its children inherit its mode); the pause menu sets `PROCESS_MODE_ALWAYS` on itself.
- END SHIFT / 收工 parks the level, opens HOME and writes no best: half a shift is not a total.
- Ways in, all refused under `--menu=off`: Esc (`ui_cancel`, also resumes), the HUD's `PauseButton`, a tap on the 咪錶 (a style-less `PauseButton` over the meter), and the app losing the screen or focus.
- The button is `FOCUS_NONE`: Space is the handbrake and a focused button takes `ui_accept`. Hidden where nothing can pause (`Hud.pausable`).
- `InputRouter` releases both thumbs on `NOTIFICATION_PAUSED`: a paused tree sends no input, so a finger lifted over the menu would hold its last steer.
- Not built: Android's back button (`quit_on_go_back` is the default, so back quits; `P0-3b`).
- The pause draws at `menu.tres`'s `pause_fps` 30 at most (2026-11-18, `ControlOptions.hold_frames`): the tree is held but the city is still drawn, and `keep_screen_on` is the engine's default, so a phone left on PAUSE never sleeps. Never above the cap in force; the cap it found is restored on release, then the saved pick, so a FRAME RATE change under the pause lands on resume. Refused: low-processor mode (`water.gdshader` and the blinkers read `TIME`) and a frozen frame (the backdrop blur reads the live screen). The watts saved are not measured on a handset.

## `Q166` — The parked roster is detailed inside its footprint

**Status.** Built (`P3-75`); its refusal to reuse the player's taxi body is reversed by `Q200`, which also re-detailed the roster, and the tram's doors and lenses are `Q234`'s.

- Nothing stands proud of the footprint: `parked_layer.gd` sizes each collider from the mesh's box, and `test_make_parked.py` pins that box to `parked.vehicles:` within 5 cm. The body is drawn `SKIN_M` inside the flanks; bumpers, folded mirrors and handles stand in that margin.
- The tram is 8.89 m long on the user's call (the fleet's figure), boxy, no exposed wheels.

## `Q167` — A parked vehicle wears a livery drawn per placement, unless its colour means something

**Status.** Built (`P3-75`) on the user's rule.

- A surface marker, not more meshes: `make_parked.py` names one authored colour per kind as its `livery`; those vertices take `MARKER_LIVERY`, and `vehicle_body.gdshader` paints them from the instance's `INSTANCE_CUSTOM.rgb`. A mesh per colour would cost a `MultiMesh` a variant a cell.
- Taxi, bus and tram have no livery: their colour is their identity (a taxi's is its licence, `Q183`; a minibus's, `Q182`). The player's taxi carries no livery vertex.
- The palette is `parked.tres`'s `liveries` (reasoning in `parked.md`). `ParkedRoster.livery` draws on its own roll (`LIVERY_ROLL`), so a vehicle keeps its colour across re-rolls. No saturated red but the player's taxi.
- Trap: `INSTANCE_CUSTOM` is shared. `rgb` is the livery; `a` is a bit field (livery switch, lamp circuits, hazards, roof sign, `Q214`'s bits). A new per-instance flag needs a free bit, not a new channel.

## `Q168` — Rails and fences take the car's painted sky, never metalness

**Status.** Built on the user's ask after a re-evaluation; the car's own painted-sky mix was later superseded by `Q215`, which also re-coloured the railings. The rails' and fences' mirror stands.

- `rail_metallic` stays 0.0 on rails, railings, bollards and barriers. The reason was never a constant light: metal reflects its environment, and the only environment is the sky's radiance (`P3-14`: rails at 0.65 rendered sky blue). The pools and floodlit fronts are shaders, not lights (`Q160`), so metal cannot pick them up.
- `tramway.gdshader` (rail head only) and `railings.gdshader` mix `sky_zenith` / `sky_horizon` / `ground_reflection` × `sky_light` into the albedo by a fresnel on the reflected ray. Dials in each `.tres` (`rail_reflect` 0.5 on rails, the user's pick over 1.0; 0.25 on fences).
- Known: a fence darkens slightly at every hour (a vertical face's reflected ray is near level, half in `ground_reflection`). Shipped on the user's call.
- `ReflectionProbe` refused on cost, not capability (Forward Mobile supports it): a capture goes stale as the hour moves, and a moving car needs a chain of probes or six redraws per update. Revisit only if wet roads or neon need the city in a reflection, and measure one car-mounted probe on a handset first.
- Owed: handset cost.

## `Q169` — The skills take the 黃紙's names; a 成績表 and a record follow

**Status.** Built (`P3-76`) on the user's calls; phone layout by `Q206`, save-as-picture by `Q188`. A whole shift to 交更 played by hand is owed.

- Names live in `tuning/exam_sheet.json` (`ExamSheet`, read by `FareFace.skill_name`). Penalties keep TD's fault-sheet wording and tier: 碰及物體（輕微） / （嚴重）. Bonuses are feats with no fault word, on the user's pick ("a bonus is not a fault"): 貼身而過, 險過剃頭, 高速行駛, 凌空飛躍, 走得快好世界. The drift stays 甩尾.
- Names only: a bonus pays, a penalty docks. TD's three-minors rule is not applied; no pass/fail line. The wrong-way warning stays a warning.
- The 成績表 is the driver's books, two tables (bonus and penalty), not TD's form: no 輕微 / 嚴重 boxes, no section headings (they read as fault marks over bonuses). No 衝紅燈 row until `P3-3d` is decided (`Q181`).
- `SessionTally` holds a run's books. An award is not money banked: a walked fare forfeits, the tip floors, practice pays nothing. `counts` holds every award, `banked` only what a delivery kept, so a row's count and money do not divide. The page closes: `meter + time + bonus + penalty + floored == earned_hkd`.
- `LedgerCard` is the one form for REPORT, free mode's PAUSE and RECORD. A shift's PAUSE has none. `--menu-sample=on` fills it for a frame.
- The record is in `Settings`' `[records]` section, keyed by skill name. `take_unsaved` hands over only what is new, so saving at every pause counts each event once. Saved at 交更, as a pause opens, and on the window's close request. Scripted runs save nothing.

## `Q170` — Space is the handbrake

**Status.** Built on the user's ask. A rename: no force on the car moved.

- The action is `handbrake` (`project.godot`, `InputRouter`, `handbrake_input`); HOW TO PLAY says 空白鍵拉手掣. 甩尾 stays the skill's name: the drift is what the fare pays for, never the control.
- Kept behind the press: the rear side cut (`arcade_aids.drift_side_cut`) and drift mode. The cut at 0 was measured (`arcade_aids.md`, `Q156`): `turn@off` 59 / 78 / 146° against 91 / 97 / 110° at 42 / 63 / 86 kph, and no `lock_ratio` bought it back. A handbrake alone is a re-tune, not a simplification.

## `Q171` — Trees are built from the published inventories, and only where one is surveyed

**Status.** Built (`P3-77`) on the user's calls. Reverses `Q144`'s "trees are not built". Checklist in `.claude/rules/trees.md`.

- Sources (CSDI, paged from the REST service in EPSG:2326): HyD Tree (`VIS_INV_TREE`, `hyd_rcd_1632210213867_60179`: `TREE_ID`, `DBH`, no species in region) and LCSD Trees in venues other than major parks (`lcsd_rcd_1760154188966_59086`: species, no size). Neither publishes a height or crown. DEVB, DSD, CEDD and HA layers were not fetched.
- Where nothing is surveyed, nothing stands: Hennessy Road (no roadside inventory) is bare. A fill would be `Q144`'s invention and is a separate call.
- Victoria Park stands since 2026-11-18: LCSD's Trees (Major Parks) (`lcsd_rcd_1730101435734_98947`) is a third publisher, `lcsd_parks`. 2,230 read, 2,135 stood (Wan Chai 1,061 → 2,254 trees, Causeway Bay 2,375 → 3,317); 80 of the 95 refused are `no_ground` on the seam, where the neighbour region draws the ground. `min_kerb_clearance_m` unmoved at 0.36 / 0.50 m.
- The library is the ETL's (`pipeline/trees.py`, `trees:` block): `broadleaf`, `palm`, `fan_palm`, `conifer`, by genus. A tree is a crash: a trunk `CylinderShape3D` each, in one `StaticBody3D` per kind and prop cell (Jolt's `max_bodies` is 10,240 and the railings hold 7,693).
- Every size is an estimate: HyD height = `DBH` × `height_per_dbh_m`, clamped (an authored ratio; no Hong Kong allometric curve was found); LCSD by its kind's height range.
- Refused and counted, never pushed: `in_carriageway` (the level-0 region plus `kerb_clear_m`), `no_ground`, `under_structure`.
- Colour is the user's pick near the top of `Q33`'s 5–15% leaf range, so the per-tree tint only darkens (`tint_darken`, `tint_warmth`, `width_jitter`), written as the `MultiMesh` instance colour at no draw cost.

## `Q172` — A drift counts at half a second, and its money grows with its length

**Status.** Built on the user's ask; amends `Q145`'s bar and price, not the angle. Numbers in `skills.tres` / `skills.md`; rules in `.claude/rules/fares.md`.

- `drift_min_s` is 0.5: at 2.0 only a countersteered slide at 86 kph ever paid (skidpad dwell at ≥ 14°: `tap` and `ride` 0.87–1.00 s, `hold` 0.68 / 0.83 / 3.57 s at 42 / 63 / 86 kph).
- The n-th award of one slide pays `drift_hkd + (n − 1) × drift_step_hkd`. Arithmetic, not geometric: a doubling price makes a ten-second slide worth more than a shift's fares. A new slide starts again at `drift_hkd`; an ended slide forfeits its unpaid part. Not the fare-wide chain (`P3-2b`).
- Reversing is not a drift: `FareSystem.REVERSED_SLIP_DEG` (90°) stops the meter past a right angle. A constant, not tuning. `slip_deg_of` is unchanged, so the skidpad's duplicate holds.
- The light tail lays from `LightTail.PAID_TIER` (1), the slide's first award; sparks keep the counting tier. Refused: paying from the threshold (`drift_min_s` 0), which pays every twitch (`Q145`).

## `Q173` — Signals return as a phase plan we author and can check, and heads show only what it runs

**Status.** Built (`P3-3a`–`P3-3f`) on the user's instruction. Reverses `Q77`'s closure; `Q76`'s findings on `DTAD_TRAFFIC_LIGHT_PT` stand. Posts collide since `Q191`. Checklist in `.claude/rules/signals.md`.

Several standing decisions:

- **The plan is authored and says so.** Approaches whose travel axes agree share a green; a one-axis junction gets an all-red stage for its crossing. TD publishes no stage order or timings. Heads are lit by the controller and stand only at junctions it runs. `Q77`'s refusals (dark heads; a plan derived from heads alone, opposable at 18 of 107 junctions) stay refused.
- **What is signalled.** A junction is signalled when an `RM1011` stop line is hosted at it (115 of Wan Chai's 120 lie within 15 m of a head, p50 3.9 m; `RM1012` / `RM1013` sit ~50 m away) or a published head is, by the same host rule. TD's stop-line survey covers about half the junctions its heads signal (Wan Chai: 34 of 63 headed junctions had no bar). A lone head signals, with no count floor: nothing to plateau on.
- **A junction is `surface.py`'s stub cluster**, never nodes grouped by distance: 15 / 25 / 35 m give 297 / 240 / 202 junctions, no plateau (`Q72`).
- **The host fixes the junction, never the approach.** 68 of Wan Chai's 120 `RM1011` cross no level-0 centreline. Approaches are every drivable level-0 edge entering the cluster.
- **An approach stops at its own line** (`own_stop`): back from the drawn mouth to a square stop bar in its own reach, else a crossing's near edge, never forward. The mouth alone was past the painted stop at two thirds of matched Wan Chai approaches (p50 6.3 m), standing cars on crossings.
- **Heads.** `bind_heads` binds each post to the approach whose light it shows and registers it to the drawn kerb as signs do (outward only, `Q78`). One authored head (`tools/make_signal_heads.py` → `signals/heads.glb`). `SignalHeads` writes `SignalController.light_at` per junction stage into `INSTANCE_CUSTOM.a` on change. Lit by day; night only raises it (`lamp_night_gain`).
- **Trap: the lens circuit is `UV.x`, not `COLOR_0` alpha.** The heads' `MultiMesh` carries custom data and no colours, which the Compatibility renderer reads as alpha 0 (`Q226`).
- **The player.** A red is for AI cars. The player's crossing is counted (`ran_red_count`) and neither paid nor docked (`Q181`).
- **Turns and lanes.** A turn runs mouth to mouth (`trim_m`) across every stub of the cluster in one curve. Left from the nearside into the nearside, right from the offside; one lane per `lane_change_m`, only while clear. `RoadGraph._bent_dir` rounds a lane offset at a polyline vertex (it jumped up to 9.83 m in a 0.05 m step before).
- **Parked vehicles are read off the layer that stands them**, never a second roster. With no whole lane clear a car edges over a two-way centre line only while nothing comes, kept `side_clear_m` from the parked flank, not the kerb.
- **Lamps.** A moving car is lit, a parked one dark. Indicators use the taxi's circuits and beat (`VehicleLampsProfile.wire_blink`), phased off the `MultiMesh` slot, never position. Hazards are by source (`parked.tres` `hazard_sources`), never by kind.
- **Give way at the line** (`TrafficSystem._give_way_gap`), with or without a light: keep clear of a queued exit; yield to a car in the junction crossing the path; yield to a free car coming that ranks first (straight, then left, then right, then lower fleet id). It cannot deadlock: a car in the junction never gives way, a keep-clear wait points down the road ahead, and waits at lines follow one strict order. A car clearing the last junction is not excused its next line (`_past_stopping`, not `committed`), and carries both turns in `_turn_path` when within `give_way_look_m` of it (`Q183`'s finding).
- **Known gaps, ungraded:** a turn curve sweeping a road outside its junction; a long straight-through curve cutting another approach's stop line; two cars committing on one tick. Not built: priority off TD's give-way lines, giving way to the taxi or a tram.

## `Q174` — The wheel goes to lock slower at speed, and a slide keeps the quick ramp

**Status.** Built on the user's report; moved off the car to the keys by `Q210` (`keyboard_steer.tres` `attack_at_top_s` 2.0, the car's rack a flat 0.2 s), and given to the thumb by `Q230`.

- A full-lock left-right swap with the throttle held (`--only=flick`, `flick@held`) slid from about 95 kph on the 0.2 s ramp: 20.8° at 110 kph, 29.8° at 120. With the ramp easing to 2.0 s at the limiter on the square of the speed share: 6.3° and 6.5°.
- Not the levers, each swept: `steer_to_grip` 0.6 still slid to 25.6° at 120 kph; an earlier yaw brake only reached 19–22°; `steer_release_s` moved nothing.
- Drift mode and the countersteer side of a slide keep the quick ramp. Guard in `.claude/rules/handling.md`.

## `Q175` — A hit on a moving car reads the closing speed, and the near miss looks at moving cars

**Status.** Built; extends `P3-2a` and `P3-50`, bars and prices unmoved. Not yet shown: a near miss paid on a real car on a real street (the user's drive).

- The impact latch and the slide work in the collider's frame (`get_contact_collider_velocity_at_position`): the impact is the closing speed, and only when the taxi is itself moving into the contact. Before, a 5 kph tap on a slower car read the taxi's whole speed (100–126 kph) and stopped it dead; a head-on read the taxi's share alone. A taxi at 20 into a car coming at 40 reads 60, on purpose. Static walls are unchanged.
- Near miss: an obstacle may carry a `velocity`. The look runs on the closing speed (`near_miss_look_s`); a car pulling away is no threat; a car that pulls clear ahead starts a fresh approach. `near_miss_min_kph` stays on the taxi's own speed.
- An oncoming car lifts the path rule across the whole near-miss band (`Track.oncoming`, at `NearMiss.SPEED_FLOOR_MPS` or more), on the user's report that straight bare misses did not pay. A same-way lane pass and a parked car keep the path rule.
- `TrafficSystem.near_cars` hands live cars in; `FareSystem` finds it by `TrafficSystem.GROUP`.

## `Q176` — The trams run the published rails as walls that never push

**Status.** Built (`P3-4`); pushing by momentum added by `Q180`. Owed: the user's drive and ears, and handset cost (`P0-3b`). Checklist in `.claude/rules/trams.md`.

- Which way a track runs is read, not authored. Three witnesses in order: the other track on the right of travel (trams run on the left), the flow of a one-way street beside it, what it continues. Unresolved is refused and counted.
- `TramSystem` is separate from `TrafficSystem`: a tram is a number along a route, with no edge or lane. The whole fleet (`trams.tres`) runs always, not in a ring: a tram appearing up a straight street would be seen.
- The regions' seam is joined at runtime, because which regions are resident is a fact about the run.
- A tram stops for what is down the rails, not in a cone (a cone missed a taxi on a curve). It ignores a car crossing, for the traffic's deadlock reason. A car behind a tram waits.
- Nothing parks in a tram's path, published sources included (3 minibus stops in Wan Chai, 2 lay-bys in Causeway Bay): a tram drives through what it cannot stop for. Furniture in the path is reported (`in_tram_path`), never moved; a tram draws through it, a known visual fault.
- Traps: `--fares=off` writes no `hit` line (`last_impact_mps` moves only when `FareSystem` takes the latch). Removing `seam_heading_deg` changes nothing on shipped data; that bar is a guard no data tests.

## `Q177` — Public transport's windows light at night, and a tram runs with its side lamps on

**Status.** Built on the user's asks. Owed: the user's drive.

- Two markers, no per-instance bit: `MARKER_CABIN` (bus, tram) and `MARKER_CABIN_DIM` (minibus) on a kind's glass; `vehicle_body.gdshader` adds `cabin_light × level × night_lights`. The coach stays dark (it only parks); a taxi is not lit indoors.
- The tram's head lamp is `headlamp_l`: `headlamp_c` is on no circuit (the motorcycle's stays there; it only parks).
- The tram's side lamps are the `sidelamp` circuit (`foglamp_{side}` names), white in front and red behind, lit by day as well (`traffic_side_lit`), a deliberate reading of the user's "always". One multiply by `night_lights` undoes it.

## `Q178` — Cars sound their horns at the taxi, the taxi has its own, and the meter beeps when the reading moves

**Status.** Built on the user's asks; the horn files and per-kind patterns are `Q185`'s (`tools/make_vehicle_sounds.py`), volume is `Q221`'s. No ear has graded the levels.

- A car sounds its horn only at the taxi (`TrafficHorns.wants_horn`), on two bars: cut up (the taxi leaves it `horn_cut_mps` over the speed it can still stop from) and stood (`horn_after_s` behind the taxi with nothing else holding it). A red does not count: the wait starts at the green.
- Silent while the taxi is parked under the menu (`VehicleController.parked`). `verify_traffic` cannot hold that; check with a `--menu=on` run.
- The taxi's horn is the `horn` action (`H`, gamepad button 2), `TaxiHorn`, once per press. No touch home: a thumb-zone button waits on `P0-3b`.
- Cars answer the loop's awards (`TrafficSystem.react_to`): a CLOSE_CALL sounds the car passed (`Fare.Award.passed`); a BUMP or CRASH sounds the car struck and every car with the taxi in its path. A near miss does not.
- The meter's beep (`tools/make_meter_beep.py`) is `TaxiHire`'s, on `FareSystem.meter_changed`. The tariff decides how often (`Q141`): no unit is charged inside the 2 km flagfall, and 18% of routes exceed it, so most fares beep once. A shorter invented unit would be a meter that lies.

## `Q179` — A drift can be held for thirty seconds on the pad and not for two on the street, so it is not capped

**Status.** Measured; no cap. Owed: the user's own attempt to hold one on a street.

- The risk: `Q172`'s price has no cap; the 8th award of one slide (7.5 s) totals HK$36, past a flagfall.
- On the pad it holds: from 20 kph plain input settles into a powered circle (~36 kph, 28° slip) for 28.6 s, HK$435; `hold` from 76 kph and up likewise.
- On the street it does not: from six fare stands the longest paid slide was 1.5 s, and at the eight widest level-0 junctions (sixteen runs) none reached a second award. Every circle ended on a kerb, railing or parked car.
- Reopens on: the user's attempt; any open drivable space (car park, plaza); a kerb or railing change that opens a junction; a drift or tyre change. Re-run `tools/skidpad.sh --only=ride --entry-kph=20 --manoeuvre-s=30` and `--only=hold` at 76–95 kph.
- If it ever holds, the fix is a per-slide HK$ total in `skills.tres`: a plateau on the price still out-pays the clock.
- Trap: the pad's `longest` could not read past its 4 s window; `--manoeuvre-s=` lengthens `drift`, `tap`, `lift` and `hold` (`catch` keeps 4 s), `--hold-target-deg=` moves the driver's aim.

## `Q180` — The taxi knocks moving cars and pushes trams by momentum, and a tram never leaves its rails

**Status.** Built on the user's ask. Parked vehicles stay fixed (a scope cut, v2). Owed: the user's drive.

- A hit on a moving car or tram exchanges momentum along the contact (`VehicleController._integrate_forces`, `Pushable`): `J = (1 + e) · closing / (1/m_taxi + gives)`. A car is a free box in plan, so an off-centre push turns it. A tram gives `(n · rails)² / m`: nothing across its rails, so it cannot derail. The push is applied at the middle of the contact patch (`_contact_middle`); at the first corner it read a spurious turn.
- Walls, kerbs, railings, trees and parked vehicles are unmarked and keep the arcade response. `--push=off` restores walls everywhere.
- Masses are kerb weights, cited in `parked.md`, in `parked.tres` `masses_kg` (the tram 12.5 t from Hong Kong Tramways' own figure; a fan site's 27 t is wrong).
- `collision_restitution` 0.15 (`handling.tres`): crash-reconstruction literature reads 0.1–0.2 (Tanner et al.; Monson & Germane, SAE 1999-01-0097). A wall never reads it, so the taxi bounces harder off a tram than off a wall.
- A knocked car slides on the tyre's grip, rolls `react_s` (the Road Users' Code's thinking distance) then brakes, stands on its hazards as a parked footprint, and after `recover_after_s` rejoins the nearside lane if it faces a drivable road's way. Otherwise it stays a wreck.
- The penalty stays on the closing speed alone (the user's call): a heavier target costs no more.
- Graded: `--only=traffic`'s six push rows, `verify_traffic` `knock:`, `verify_trams` `push:`. Left: a knocked car keeps its height, so it slides level on a ramp.

## `Q181` — No traffic-law penalty until something in the game enforces it

**Status.** Decided on the user's instruction. No enforcer is designed yet.

`P3-8` does not dock for a bus lane. A breach of the road's law is paid for only when something in the world catches it ("something like a policeman"). Four breaches return together behind that mechanic, never one at a time as a flag off the road graph: a red the player runs (counted as `ran_red_count`, never docked), stopping on a double yellow (`NSR`), a bus lane, a bus stop. `bus_lane` stays in the road graph and the router's rules.

## `Q182` — Buses and green minibuses run their published routes, and stop at their stops

**Status.** Built (`P3-78`) on the user's asks; "a bus at a stop may be parked, at random" is reversed by `Q187` (a bus parks only at its terminus). Owed: a drive. Checklist in `.claude/rules/busroutes.md`.

- Source: TD's Routes and Fares of Public Transport (`static.data.gov.hk/td/routes-fares-geojson/` `JSON_BUS.json`, `JSON_GMB.json`): one record per stop of a route direction; `stopId` is our `STOP_ID`. Headways from TD's GTFS (`pt-headway-en`), a Wednesday's service.
- The line between stops is not published (GTFS `shapes.txt` answers 403), so the path is inferred by the legal router and graded, not trusted.
- The ETL publishes stops, not paths (`pipeline/busroutes.py` → `bus_routes.json`). The path is found at runtime with `RoadRouter.goal_tree` under the cars' legal profile: the seam is joined only at runtime, and a baked path would be a second successor rule. No bus profile; bus lanes are not enforced (`Q181`).
- Grader: `tools/bus_legs.py`, path length over the straight gap per leg (Wan Chai p50 1.02, 32 of 862 legs unreachable; Causeway Bay p50 1.17, 63 of 252). Level 0 only, so an unreachable leg may still be drivable over a level-1 edge.
- The routed fleet is `traffic.tres` `buses`, dwelling at stops in the nearside lane. Past its last stop, or knocked, a vehicle wanders. A minibus on a route is green (`route_liveries`), one without is red (`wander_liveries`): the colour is the licence. Red minibuses publish no route.
- Open: the wandering fleet alone meets in a signalled junction on seeds 1, 2 and 8 (two merges). The gate holds on seeds 7 / 4 / 23, driven without the buses; the routed drive's meetings are printed, not gated. Do not answer by picking seeds or raising `INSIDE_M`.

## `Q183` — Taxis join the traffic at TD's measured share, each wearing a licence its region's stands name

**Status.** Built on the user's asks; the flat 16.8% share is superseded by `Q186` (mix by hour off the census). The licence rules stand. Owed: the user's look and drive.

- One mesh per licence in `parked.glb`: `taxi` (red), `taxi_nt` (green), `taxi_lantau` (blue). The colour is the licence, never a livery (`Q167`).
- Which licence where is read off TD's Taxi Stands, never authored: a stand's `Status_EN` category names its licences (`parked.licences.by_category`); a region's mix is every stand in the districts (`District_EN`) its own stands lie in. A parked taxi at a stand wears the stand's category; any other taxi draws on the region's mix; a region with no stand wears red. Wan Chai and Causeway Bay read 100% red.
- A moving taxi re-dresses at each spawn, off its id and spawn count, never the seeded RNG.
- The roof sign is lit for hire on `taxi_for_hire` of spawns (authored: TD publishes no vacancy rate). A parked taxi's stays dark.

## `Q184` — The web build compiles its shaders under a boot cover, and a batched car holds no instance uniform

**Status.** ✅ Built 2026-11-05 on the user's ask; amended by `P3-3f` (one writer for the blink uniforms).

- The web runs Compatibility (`Q76`): a shader variant compiles at its first draw and there is no baker. A cold load stalled 733 / 2124 / 595 ms in the menu and 312 / 462 ms at the drive's start. To reproduce on macOS, move Chrome's Metal cache aside; a fresh profile alone is warm.
- `ShaderWarmup` (`scripts/ui/shader_warmup.gd`) is a boot cover `Main` opens under the menu only (`--menu=off` and scripted runs never see it). It waits for `CityRegions.built` plus `cover_settle_frames`, then draws one shrunk copy of each distinct draw for `cover_warm_frames`. Particles are `ParticleWarmup`'s. Numbers: `menu.tres` `cover_*` / `warm_*`. After: no task over 50 ms once the cover lifts.
- A batched car drops its instance uniforms: `VehicleBodyBatch` duplicates `vehicle_body.tres` with `#define VEHICLE_BATCHED`, and a batch reads its lamps from `INSTANCE_CUSTOM.a`. WebGL2's buffer holds about 60 nodes with an instance uniform; errors went 83 a load → 0. Only the player's car keeps them.
- `VehicleBodyBatch.material()` calls `VehicleLampsProfile.wire_material`: one writer for `traffic_blink_hz`, `traffic_blink_duty` and `traffic_sign_lit`, never a shader default.
- Not covered: the first dusk's new light-count variants.

## `Q185` — The taxi's own sounds: the meter's flag, an engine, the tyres, crashes by what was hit, a horn per kind in patterns, and the payout

**Status.** 🟡 Built 2026-11-06 (`P3-79`) on the user's asks and trimmed on his notes; only the engine has been graded by ear. Owed: the PCK cost, his ears on the rest.

- Every file is `tools/make_vehicle_sounds.py`'s: authored, 22,050 Hz mono, byte-identical per run. A loop is exactly periodic and carries a `smpl` chunk Godot imports as the loop, so no `.import` is hand-edited. Levels and dials: `taxi_audio.tres` / `.md`; horns: `traffic.tres` / `.md`.
- What plays: the flag's motor (`TaxiHire`); the engine (`TaxiAudio`, three loops crossfaded in log rpm on a virtual 4-speed; `hybrid` off, the car is the LPG Crown Comfort); the squeal from `SkidMarksProfile.mark_from_slip`, following slip and speed; crashes off `VehicleController.step_hit_mps` / `step_hit_with` / `step_scrape_mps` (per-step readings, so the fare's latch is not drained), tiered on `skills.tres`' bars, layered by the struck body's node name; a horn loop per kind in patterns per reason; at the door the card reader's beep and a coin per HK$2 of tip, at most 15; the door, the indicator relay, the landing.
- Removed on the user's word: the handbrake ratchet, the bonus and penalty chimes, the wrong-way buzzer.
- The engine has nothing over 1.5 kHz and idles at 135 Hz (66 Hz does not play on a phone). Always-on loops sit under the events; a loop is raised only against a drive.
- Traps: the box's downshift must sit under the lightest upshift's landing rpm or it hunts (`verify_vehicle` sweeps it). The horns draw on their own RNG, never the wandering `_rng`. The player's horn sounds as long as it is held. Under the menu the loops fade over `park_fade_s`; the check reads the level, not `stream_paused`.
- Buses: `SFX`, `Engine`, `Cabin` under `Master`; the volume option is `Q221`. Not built: another car's crash or engine, a touch horn (`Q178`).

## `Q186` — The traffic's mix and size follow the clock hour, off TD's census on these streets

**Status.** 🟡 Built 2026-11-06 (`P3-3g`) on the user's ask; `fleet_by_hour` amended by `Q198`, the hidden slots by `Q200`, `cars` by `Q219`. Owed: a drive across a shift.

- `traffic.tres` `kinds` is a weight per kind per clock hour and `fleet_by_hour` the share of `cars` alive; the hour is `_hour_now`.
- Source: TD's *Annual Traffic Census 2025* through `atc.td.gov.hk/api/analysis` (`DATA_SOURCES.md`). The mix is the classification surveys at stations 1002, 2214 and 1107, pooled by vehicles counted: taxis are 24–42% of the drawn traffic by hour. `tools/traffic_census.py` prints the tables; they are never edited by hand.
- Authored inside the census: the 4 : 3 split of private cars between `car_a` and `car_b`; which classes are drawn; hours outside 07:00–23:00 hold the nearest surveyed hour.
- A spawn's kind comes off the car's id and lives, never `_rng`: one more roll moves every later car and every seeded case. Batches are sized once in `setup` (`instance_count` clears the buffer).
- The fleet changes only by the ring: no car is placed while the fleet stands at its hour's size, and none is removed for the hour.

## `Q187` — A bus parks only at its terminus, on the timetable; the routed fleet and the kerb-stopping kinds signal like their drivers

**Status.** 🟡 Built 2026-11-06 (`P3-78`) on the user's calls; reverses `Q182`'s parked bus at a street stop. Owed: his drive by day and night.

- No bus parks at a street stop. `parked.stops` keeps the minibus termini only (`gmb_termini`, chance 0.8).
- A terminus is filled by the timetable (`parked.terminals`): a route direction's first stop in `bus_routes.json`, read off busroutes' manifest, so `busroutes` runs before `parked`. Each clock hour `ceil(departures × layover_min / 60)` buses queue, at most `queue`. `layover_min` 10 is authored: TD publishes none. An unsnapped terminus is re-snapped within `terminals.max_snap_m` (Wan Chai Ferry Pier stands 12.3 m off its road).
- At a stop a routed vehicle winks left from `lane_change_m` short and while it stands, brake lamps lit, then right for `pull_out_m`. A tram winks left at its stop (`TramSystem.at_stop`). The player's taxi flashes hazards from the hail to the boarding and for `alight_hazards_s` at a delivery (`TaxiHire`).
- The kerbside stop (`kerb_stop_kinds`: minibus, taxi): chance is the usable length over `kerb_stop_every_m`, on its own RNG, on level 0, beside no parked vehicle, never before a right turn, on no restriction run (`RoadGraph.no_stopping`; a single yellow counts, since hours are not carried to the graph). `kerb_unlawful_share` of a red minibus's or a taxi's stops ignore the line, wandering vehicles only. A taxi's rules are its family's, not its licence's (`TrafficSystem.rules_kind`).
- A kerb's side and flow are spelled once, in `pipeline/drawnroad.py` (`Ribbon.kerb_side`, `flows_along`).
- `TrafficSystem`'s pieces (`TrafficTurns`, `TrafficHorns`, `TrafficFleetMix`, `TrafficRouted`, `TrafficKerbside`) each keep their RNG's seed and draw order.

## `Q188` — The result sheet is saved as a picture; no share sheet, no achievements

**Status.** ✅ Built 2026-11-06 (`P3-80`) on the user's calls; the button renamed SAVE RESULT by `Q189`. Owed: his look, a press on the web build.

- The picture is the 成績表 itself, `Node.duplicate`d into a `SubViewport` (`scripts/ui/sheet_image.gd`, `menu.tres` `sheet_image_scale`). Never a crop of the screen, which would carry our render of the government's data out of the game.
- On REPORT, free mode's PAUSE and RECORD. A computer writes the PNG to Pictures (else `user://`); the web downloads it.
- No button on a phone (`Handset.is_phone`: `mobile`, `web_android`, `web_ios`). Godot 4.7.2 has no share sheet and no save-to-Photos; both need Phase 7's store plugins. `navigator.share` was declined too.
- Achievements dropped: RECORD (`P3-76`) is the lifetime table.

## `Q189` — A free drive ends from its PAUSE on a REPORT of its own, with the time driven

**Status.** ✅ Built 2026-11-06 (`P3-81`) on the user's ask. Owed: a real drive ended from the pause.

- Free mode's PAUSE ends on END DRIVE / 收車 and `Main._free_report` opens REPORT. A shift's END SHIFT still goes HOME: half a shift is not a total (`Q165`).
- The free REPORT (`StartMenu.Report.mode`) is headed by the mode's name and reads TIME DRIVEN (`StartMenu.duration_text`) where a shift reads its best. No best is kept; AGAIN starts a free drive.
- The time is `SessionTally.driven_s`, added on `FareSystem`'s physics tick, so the menu and the pause stop it. Not `DayClock.elapsed_s`, which a held day turns off.

## `Q190` — The taxi takes a 1:64 die-cast's proportions and detail, without its lettering

**Status.** ✅ Built 2026-11-09 (`P3-82`) on the user's "go model scale"; the lettering added by `Q202`. Owed: his look.

- The player's taxi has the Tiny City Crown Comfort's proportions (4.54 m on the 2.785 m wheelbase; the real car is 4.695 m) and every feature it carries, built in `tools/make_vehicle.py` (`Proportions`).
- The bumper is a part, not paint. Tail lamps are red over amber over white: a reference call, the user's to correct.
- `body_offset_z_m` is 0.2175: at the photograph's 0.23 a sliver of panel stood through the front wheel opening.
- The collider follows the body: a 4.575 m box set 0.2175 m back. Trap: Jolt derived the inertia from the box, so `CarSpec.inertia_kgm2` freezes the old 4.0 m box's values and `VehicleController._ready` refuses a zero. The skidpad's driving rows were byte-identical; only contact moved.

## `Q191` — Lamp columns, sign posts and signal posts collide, as a cylinder up each post

**Status.** ✅ Built 2026-11-09 (`P3-83`) on the user's ask; reverses the lamps', signs' and signal heads' (`Q76`) "no collider" budget stances. Owed: his drive into each.

- `PropBatch.post_of` reads the ring at a library mesh's foot and returns an upright cylinder to its top. No radius is copied into code. A sign's face, a lamp's arm and its lantern get no shape.
- A body per kind and plan cell, never per post (`PropBatch.posts`): Jolt's `max_bodies` is 10,240 and the railings hold 7,693. The trunks use the same path.
- The switch is `posts` on `region.tscn`'s `Lamps` and `Signs` and `city_drive.tscn`'s `Heads`. The `.glb`s stay collider-free and `verify_lamps` / `verify_signs` assert it.
- Breakaway poles stay `B3`'s.

## `Q192` — The bus lane's line is TD's survey, and the shader's bar is off

**Status.** ✅ Built 2026-11-09 on the user's report from Hennessy Road.

- `draw_bus_lane` is 0.0 in `road_markings.tres`. The shader painted a bar at `U = 1` of every `bus_lane` edge, but that flag (Road Network v2's `BUS_ONLY_LANE`) says a bus lane exists on the route, not where its line runs: on edge 237 the bar stood ~1.7 m inside the traffic lane with no surveyed `RM1006` within 282 m. The bit stays in the codec; the router reads it.
- `RM1006` BUS LANE (continuous) and `RM1007` CONTINUATION (1 m mark, 1 m gap), 250 mm white, are `road_marks.marks` rows: `longitudinal`, never `divides_flows`.
- Known under-draw: `RM1006`'s diagonal lead-in and `RM1007`'s corner curve lie along no longitudinal host. They are refused and counted (`no_host_on_axis`), not re-hosted as `oblique`. `RM1048`, the bus-stop box, is not drawn.

## `Q193` — A building's street band takes no measured colour of its own

**Status.** 🚫 Refused by measurement 2026-11-09; reversed on the user's instruction by `Q197` (hue, noise-weighted) and `Q240` (the street band's lightness). The numbers stand.

- Bar: a band is distinct when its gap to the band above is ≥ 2.0 Δab and ≥ 2× its own wall-to-wall spread; a split earns a channel at ≥ 25% of tall buildings. Wan Chai, 970 tall: shop vs tower distinct on 10.8%; all three bands distinct on 1.2%.
- The gap is the size of the noise: street vs tower on the same wall is a median 6.1 Δab, two walls of one tower 6.5.
- Trap: a one-wall band is untested, never passed. Reading its missing spread as zero reported 25.1%.

## `Q194` — The tower's surveyed hue is mostly the building, not the light

**Status.** ✅ Closed 2026-11-09, no change; a per-wall light correction refused on yield.

- Two walls of one tower differ by a median 6.7 Δab. Compass explains 6.3% of the hue variance within a building, brightness 13.7%, both 15.0% (spread 6.71 → 6.07); the photo sheet 1.4% between buildings. This is not `Q34`'s 1.4%, which is `L*` against the whole stock.
- Reliability of a building's wall-mean hue: `a*` 0.70, `b*` 0.74; corrected for light 0.71 and 0.78. Not worth a survey change that would owe `facade`'s re-derivations.
- Standing bias: the pooled estimator leans to the lit walls, `db*` +0.81 at p50, about +3 `b*` on screen at `strength` 3.0. It belongs to `Q30`.

## `Q195` — A podium's cornice is drawn at iB1000's line and nowhere else

**Status.** ✅ Shipped 2026-11-11 on the user's instructions; the podium's colour was built later by `Q197`.

- The line is data only. `podiums.json` (schema 2) carries `top_mpd`, and a line ships where the building rises at least `podiums.min_tower_above_m` (6.0) above it.
- Refused: a 12 m default on every other building. It would invent a line on ~78% of the stock, where `Q193` found 4.2% distinct.
- `COLOR_0.a` carries the line (`CITY_SCHEMA` 46): metres above the object's base in 0.5 m steps, codes 1–254; 255 is no line, and the shader reads 0 as none too. Per building, since a per-face payload does not survive the collapse (`P3-7a`). It was the only free channel.
- The shader draws a cornice only where a line is (`city_facade.md`). `podium_height_m` stays the parked grid's fallback anchor and draws nothing.
- Shopfronts on every wall were rendered and dropped.

## `Q196` — Vehicles take detail lines from their own mesh, a width in metres

**Status.** 🟡 Built 2026-11-11 (`P3-84`); pressed relief added by `Q232`. Owed: the user's pick of the weight, a night frame, the PCK, the handset's frame time.

- The depth-pass outline (`Q158`) cannot ink a change of colour on a flat panel. `tools/vehicle_ink.py` inks an edge where no triangle of the same colour and marker touches it, and writes the distance to inked edges into `TEXCOORD_1`.
- The body shader draws the line `ink_width_m` wide in metres on the vehicle, in the surface colour × `ink_darkness` (`vehicle_body.tres`: 2 cm / 0.35, the middle of the sheet, not the user's pick). Thinning with speed is the global `outline_speed`, the player's speed.
- Refused: a per-vehicle speed (a hull or ID buffer against the 150 draw-call budget; `P3-65` withdrew the hull) and a colour-edge term in the screen pass (it would ink every lane line).
- Traps: a `global uniform` declared inside a `group_uniforms` block compiled silently and miscoloured the façades; declare it beside the other globals. The `.glb` has no `TEXCOORD_0` (`Q124`); `generated_scene_import.gd` carries `TEXCOORD_1`, and a body without it draws no line.

## `Q197` — A building's street band and podium take the survey's colour, weighed by its own noise

**Status.** ✅ Shipped 2026-11-11 on the user's instruction and pick; reverses `Q193` on instruction, not measurement; the street band's lightness added by `Q240`.

- `facade_survey.survey_bands` measures three bands by wall-triangle centroid: the street to `STREET_BAND_M` (5.0 m), the podium to the iB1000 line (`Q195`), the tower. Each has `lab`, cut heights and `noise` (median pairwise Δab between its walls, squared over their count; fallback the city median 6.5).
- `buildings.band_hue` ships the building's hue plus `w·(band − tower)`, `w = gap² / (gap² + noise_band + noise_tower)`. Street bands measure a median 6.6 Δab from their tower and ship 3.3. The tower keeps its exact colour.
- `cut_bands` cuts the finished tier, after `collapse`: cut on the source, the cluster means fuse the two colours. Only triangles whose three corners are one object's are cut.
- A podium band ships only where the build ships that line (`_ship_line`), so band and cornice agree.
- Switch: `facade_hue.bands`. Cost: Wan Chai's finest tier +16.2% triangles, the web PCK +5.5 MB. No schema bump.

## `Q198` — The traffic is the cars on the street: flow over TD's detector speed, 40 at the evening rush

**Status.** 🟡 Built 2026-11-11 (`P3-3g`) on the user's ask; amends `Q186`'s `fleet_by_hour`; `cars` 40 raised to 60 by `Q219`. Owed: his drive at the rush.

- The cars on a street are its density, flow over speed. The census flow alone saturates in a jam: 08:00–19:00 sat within 7% of noon.
- Speed: TD's raw detector feed (`rawSpeedVol-all.xml`) from DATA.GOV.HK's historical archive, eight detectors (Canal Road Flyover ×4, Gloucester Road ×4), 18 weekdays 2026-10-12 → 2026-11-05, space-mean per hour. Both tables are `hong_kong.yaml`'s `traffic_census:` block, off the hand-run `tools/traffic_census.py`, never edited by hand.
- The fleet peaks at 18:00 (29 kph against 58–62 overnight). The detectors' occupancy peaks at the same hour.
- `TrafficSystem._room_behind`: a placement must leave the car behind room to stop at `brake_mps2` and `gap_m`. `spawn_clear_m` is a point's distance, blind to a bus's length and to speed.
- Authored inside: the detectors are trunk roads only.

## `Q199` — A flyover's lamp stands on the flyover, a lamp under one stands shorter, and no column passes through a deck or a roof

**Status.** 🟡 Built 2026-11-11 (`P3-26`) on the user's report; the junction test added by `Q237`. Owed: his look.

- `UtilityPoint` publishes no elevation. A column inside an elevated edge's drawn ribbon, or within `outset_m` of its kerb, is the deck's: an inference from the plan. A tunnel is not a deck.
- A deck column always takes `deck_outset_m` 0.1, pulled in as well as pushed out. At 0.6, 53 of 81 deck columns had no slab under the foot; at 0.1, one.
- Any other column with a shipped face over its foot between `overhead_clear_m` and its top (`trees.shipped_faces`) is shortened to `soffit_gap_m` under it, as the stand's `Y` scale, and refused (`under_structure`) below `min_column_height_m` 5.0. `lamps` runs after `carve` for it.
- Columns through a deck or roof: Wan Chai 206, Causeway Bay 20 → 0.
- Open: about ten deck columns stand with the foot just off the slab's edge.

## `Q200` — The roster takes its die-casts' detail, the taxi's the player's own body, and a batch draws only the cars shown

**Status.** 🟡 Built 2026-11-11 (`P3-85`); reverses `Q166`'s refusal to reuse the player's body, amends `Q186`; later detail in `Q232`, `Q234`. Owed: the user's look and the handset's frame time.

- A roster taxi is the player's body (`make_parked.Taxi` off `make_vehicle.taxi_parts`), door shut, wheels baked in, mirrors tucked (`TAXI_MIRROR_REACH_M`) because a roster vehicle's box is its collider. `parked.vehicles: taxi` is 4.575 m. Licence paint goes by part name; a rename fails the build.
- Lofted kinds take their die-casts' features as `Shape` fields, off by default. No proportions were re-measured: a 1:76 model has the real vehicle's.
- The bus and tram are flat-sided (`Shape.slab_sided`). The tram's cream band is gone (the model is plain green) and its skirt still hides the trucks (`Q166`): both the user's to reverse.
- Glass is the user's pick: streaks (`GLINT`) on the bus, the tram and the taxi's side windows.
- A batch draws only the cars shown (`TrafficSystem._take_slot` / `_drop_slot`, `visible_instance_count`). A hidden instance of no size still costs its triangles: the throttle route fell 1,010,611 → 890,847 primitives at 1 s.
- The goods lorry is parked only: TD's `Goods Vehicles` bays, and an invented second rank at an office frontage (`kinds: [van, lorry]`). Not in the moving traffic: its census share is unmeasured and a new kind moves every seeded draw.
- Taken with the user away, his to correct: the roster taxi at the player's length, the references, the ink at 2 cm.

## `Q201` — The chase camera sits low and close on a narrow lens

**Status.** ✅ Built 2026-11-11 on the user's ask and his racing-game references. His look owed.

- Values are `camera.tres`'s. `fov_base` is a vertical angle: the old 70° was 102° across 16:9 and stretched the car long and thin.
- The rig looks along its arm at the anchor, so `height` places the car in the frame and `pitch_deg` alone only moves the camera. The camera's height is `height + distance · sin(pitch)`, and only a lower camera flattens the road edges.
- Closer than 6.0 m at a 50° lens cuts the bumper off the rest frame; a wider lens is the thin car again. The menu's shots (`menu.tres`) carry their own distances.

## `Q202` — The player's taxi carries its plate, its roof sign's lettering and a boot seam

**Status.** ✅ Built 2026-11-11 on the user's ask; amends `Q190`'s "without its lettering".

- Strokes, not a texture: `make_vehicle._text` draws glyphs as flat quads (`GLYPHS`) in colours the car already has. One material.
- The plate `TX 852` (made up) and the sign `的 TAXI 士` are from memory, the user's to correct (`Proportions.plate_text`, `sign_text`).
- The sign's lettering is paint on the lens: parts `roof_text_*`, off the `sign` prefix `LAMP_PARTS` lights.
- The player's car alone (`player_detail` in `taxi_body`, not `taxi_parts`): the roster would all wear its mark.
- The player's car has a standing ceiling of 2,200 triangles (`test_make_vehicle.TRIANGLE_CEILING`); the roster's stays 2,000.

## `Q203` — Customers wait at street kerbs as well as stands; the allowance is the route at a measured par

**Status.** ✅ Built 2026-11-12 (`P3-86`) on the user's asks; reopens `Q142`'s designated-passenger refusal; a later run's start is `Q227`'s. His drive owed.

- Street spots are the ETL's (`fares.street`, `fares.json`'s `street` key): a station every `spacing_m` along each level-0 edge, `junction_clear_m` in from junction ends only, nearside of a one-way and both kerbs of a two-way. Refused beside a `kerbside` run (single yellow too: the graph carries no hours), on a bus-lane edge or a limit over 50 kph, outside the region, or with no named building within 25 m. Wan Chai 221, Causeway Bay 166.
- A live set (`FareSystem`): `live_pickups` wait, `street_share` of the draws come from the street, and each is paired with a destination the legal network reaches at `min_trip_m` by one forward search (`RoadRouter.source_tree`, uncached); a kerb that pairs with nothing is stranded for the session and never shown.
- Turnover: a new customer is placed within `place_m` (half the minimap's span). `_turn_over` refills the set or swaps the farthest past `retire_m`, placing and pairing first. A swap, never a removal alone.
- `FareSystem.wait_at` seats a customer at the start stand.
- The allowance is the legal route over `par_kph`, no floor by kind. Par 19 is the median of the AI traffic's runs of 200 m or more (p50 18.8 / 19.2 kph at 18:00 / 12:00); the old 30 was its 90th percentile. Recipe in `fares.md`.
- Dial reasons are in `hong_kong.yaml` beside `fares.street` and in `fares.md`. `street_share` is the user's call: TD publishes no split. Parked vehicles on a hail kerb are left: the cab stops alongside.
- Refused: an all-pairs reach table (seconds at load); blind destination draws routed per try (~20 ms a stranded kerb, and wrongly stranded 29% of the time); drawing at the hail and retrying (`Q141`); customers that move with the car.

## `Q204` — The touch screen lays out for thumbs: its own table at 1.25, sticks drawn as the taxi's wheel and pedals, the glass to the edge

**Status.** ✅ Closed 2026-11-13 on the user's picks from the handset; reverses `Q97`'s "no visible touch chrome"; `Q83`'s relative thumbs stand; amended by `Q220`, `Q224`, `Q228`, `Q238`, `Q239`. The handset drive owed.

- Shading and touch zones run to the glass (`HudLayout.bleed`, `place_to_glass`); text and buttons stay inside the safe area. Insetting the zones left a dead strip under the thumb.
- A touch screen reads `hud_layout_touch.tres` (`HudLayout.for_device()`; `--touch=mouse|on|off`). Its `design_size` is the scale, `1080 / design_size.y` = 1.25, applied once as the root's `content_scale_factor` by `InputRouter`.
- The thumbs rest on the lower corners, so the map sits left under the clock and the speed right under the meter, on one line.
- `TouchSticks` draws `hud_style.touch_look` `wheel_pedals`. Steering draws sideways travel only and the pedals upright travel only: the driving thumb's sideways axis is the handbrake's (`Q83`). The wheel is `CarSpec.steering_wheel`, from memory of the cab.
- `drive.sh` emulates a handset: `--window=WxH --safe-area=l,t,r,b --touch=on`, and `--finger=fx,fy>gx,gy@t+d`.
- Open: menu buttons are ~35 pt at 1.25, under 44; whether the idle hint fades.

## `Q205` — The style combo is a count per skill, shown and recorded, never money

**Status.** ✅ Built 2026-11-13 (`P3-2b`, first part) on the user's design; its HUD placement moved by `Q212`. Owed: his drive, and with it `combo_gap_s`.

- The combo moves no fare: the meter, the tip and `earned_hkd` are unchanged. The same skill again within the timeout adds to its count; another skill keeps the first's alive; it ends on `BUMP` / `CRASH` or the timeout; the final is the sum of the counts.
- One shared timer. Practice counts. A combo carries across a hail, boarding and delivery, is recorded if running at a pause or the end, and is called out only at ×2 or more. Name: 車手 / COMBO. No sound.
- The timer stands still while a skill is in progress (`SkillTracker.holding`); otherwise the speed skill, paid every 200 m, could never pass ×1.
- `StyleCombo` (`scripts/fares/style_combo.gd`); `SessionTally` keeps `combo_best` per skill and `combo_best_total`, per session and lifetime.

## `Q206` — On a phone the 成績表 is one column the thumb scrolls, its type 1.4×

**Status.** ✅ Closed 2026-11-13 on the user's pick, the hierarchy added 2026-11-15 (`P3-5b`); the desk keeps `Q169`'s two tables. Owed: the thumb's drag on the handset.

- On touch (`HudLayout.is_touch()`, or `StartMenu.stacked`) `LedgerCard` stacks into one column in a `ScrollContainer`, type at `ledger_stacked_scale`, in the order sums, bests, bonuses, penalties.
- SAVE RESULT saves the whole sheet, never the scroll's window (`SheetImage.stage`).
- Four ranks of type (`LedgerCard.Rank`). A row nothing happened on is muted, never dropped. The block titles are not `Q169`'s refused TD section headings.
- `ScrollContainer` drag-scrolls only where the display reports a touch screen, so the drag is unproven at a desk.

## `Q207` — The iOS build bakes its shaders at export

**Status.** ✅ Decided 2026-11-13 (`P0-3b`); Android's preset is unchanged until a handset measures it.

- The iOS preset sets `shader_baker/enabled`. On an iPhone Air: unbaked, no first frame within 260 s of a fresh install; baked, 11.9–12.4 s fresh and 3.8–4.3 s on relaunch. PCK 98,585,688 → 109,157,308 B.
- Two silent failures ship an unbaked PCK and exit 0: a `--headless` export skips the baker, and without Apple's Metal toolchain (`xcodebuild -downloadComponent MetalToolchain`) it bakes SPIR-V only. Check the PCK: count `.godot/shader_cache/*.metal.cache` entries (70).
- `tools/export.sh ios` cannot produce a signed build; the recipe is in `docs/ARCHITECTURE.md`. The Air is not the A13 floor (`P2-6`).

## `Q208` — The game is 香港的士車神 / Hong Kong Taxi Ace

**Status.** ✅ Decided 2026-11-13, the user's pick. Open: the trademark registers (USPTO, HK IPD) for the final name.

- Store and menu name: 香港的士車神 / Hong Kong Taxi Ace. Subtitle: 港艇試駕版 / Island Test Drive Edition. The repository, bundle identifier (`cloud.williamchong.hktaxiq`) and export names keep `hk-taxi-Q`.
- Turned down: 紅的 / Red Cab and 飛的 (existing taxi apps); 暴走的士 / Taxi Rampage and other "crazy" synonyms (hard rule 8); 的士牛奶仔 (a YouTube channel).
- Where it lives: `project.godot` `config/name` and `config/name_localized`, Android's `package/name`, and `menu_text.json`'s `title` for the menu.
- Trap: a desktop names `user://` after `config/name`, and `use_custom_user_dir` does not keep the old folder.
- Not built: a rank ladder from trade slang (牛奶仔 → 行家 → 車神); a working driver should read the words first.

## `Q209` — The loading screen is a toy taxi idling over the cab's meter

**Status.** ✅ Built 2026-11-13 (`P6-1`), the user's picks. Owed: the cold launch watched on the iPhone.

- The splash and the boot cover are one screen: a small toy taxi, 載入中… · Loading…, and the cab's meter ticking from the flag fall to HK$99.9 while its cells fill with real progress. No title.
- One drawing, two readers: `assets/authored/loading/taxi.json`. `tools/make_splash.py` draws `boot_splash.png`, `LoadingCover` draws it live, and a test fails a stale PNG.
- Progress is counted: `CityStreamer.tiles_remaining`, then each settle and warm frame. It never runs back.
- The splash is a still because the main thread builds the city in one block (1.3 s on the desk). A bar from the first second needs a loader scene and a city built in steps; not built.
- The splash is the bundle's one UI texture (the engine and iOS take nothing else there): shapes and the bundled font, CC BY-SA, never a frame of the city.

## `Q210` — A key is shaped into a linear input before the car sees it; the car's assists are tuned against that input

**Status.** ✅ Built 2026-11-14 on the user's instruction; reverses `Q152`'s cap-over-ramp choice (the cap stays, as a drive assist); the thumb's own curve and speed slew are `Q220` and `Q230`. Owed: his keyboard drive of the flick at 0.6 s.

- Input assist is one per input method, in the input layer: `KeyboardSteerProfile` (`keyboard_steer.tres`), `TouchProfile`, nothing for a stick. `InputRouter.steer_for(speed_share, quick, delta)` is what the car drives on. A key ramps over `attack_s` at rest to `attack_at_top_s` at the limiter (`Q174`'s numbers, moved); easing off is not shaped.
- Drive assist is per car: `handling.tres`'s rack (`steer_attack_s`), `steer_to_grip`, the catch cap, the flick. The car never sees which device steered.
- `InputRouter.steer_from_keys` is true until a stick or thumb steers, so `Input.action_press` runs (`drive.sh`, the skidpad) steer as a key.
- Skidpad: keys held every graded figure. A full-lock analog input brings `Q174`'s slide back: `flick@held` 9.7 / 20.8 / 29.8° at 95 / 110 / 120 kph against the keys' 5.9 / 6.3 / 6.5°.
- `flick_window_s` 0.3 → 0.6: a shaped key takes 0.38 s across centre at 63 kph and the flick had stopped firing.


## `Q214` — No vehicle appears or vanishes in view

**Status.** ✅ Built 2026-11-14 on the user's ask; the spawn's sampling amended by `Q219`. Owed: the handset's frame time for the dither's `discard` (`P2-6`).

- Traffic is placed out of sight (`TrafficSystem.placed_fade`): a place in the camera's frustum with its roof in sight takes a car only past `spawn_seen_min_m`, and the car fades in. "In sight" is a ray to the roof that meets nothing the ETL ships (a `*_collision` body, `CITY_COLLIDER_SUFFIX`); another vehicle hides nothing.
- Traffic is retired out of sight (`_step_view`): past `retire_m` a car goes after `retire_unseen_s` out of view; in view it is kept until `retire_far_margin_m` short of the camera's `far`, then fades.
- The fade is dithered, never blended (`vehicle_body.gdshader`, batched variant, `INSTANCE_CUSTOM.a` bits 64–256). Fallback if `discard` costs on a tile GPU: a second small batch for fading cars.
- With no camera nothing is in view, so the seeded `verify_traffic` drives are unchanged; the rules are held by a staged `view:` block.
- Parked cells carry no `visibility_range_end`: the engine measures it to a 300 m cell's centre and cut whole cells about 190 m ahead. A cell is rebuilt only while its nearest edge (`ParkedRoster.cell_distance`) is past the camera's `far` plus `range_margin_m`.
- Open, the same fault: lamps, signs and signal heads (`prop_cells.tres`) still set `visibility_range_end`.

## `Q213` — Every moving vehicle throws a headlamp beam at night

**Status.** ✅ Built 2026-11-14 on the user's ask; closes `Q160`'s open note on rationing traffic beams. Owed: the handset's fill, and his pick of the loudness.

- Not a light: Forward Mobile pairs 8 spot lights with an object and a road chunk is one object. Each vehicle draws a box of air ahead of its nose and `traffic_beam.gdshader` adds light to whatever the depth buffer holds inside its dipped cone (`lamp_pool.gdshader`'s method).
- One `MultiMesh` an owner (`TrafficBeams`): `TrafficSystem` and `TramSystem` hand it their live vehicles each tick; a parked vehicle never. A beam is not drawn past `draw_m`, and by day the box collapses to a point.
- +1 draw on the desk. On a handset a box is a full-screen additive pass at worst; the levers are `draw_m` and `reach_m` (`traffic_beams.md`).
- The player's beams stay real lights (`P3-11e`).

## `Q212` — The style combo splits: the live total where the skill flashed, the summary under the meter

**Status.** Built 2026-11-14, restacked 2026-11-16, both the user's picks; amends `Q205`'s HUD and reverses `Q138`'s "no award mid-frame" for this one line. The user's drive owed, with `Q205`'s.

- The combo is a count, never money (`Q205`), so it left the meter's stack. Live line in the `tick`
  row: 車手 ×N in green, the gap's bar, then the skill that joined, small, on a row below
  (`FareFace.combo_skill_text`). Under the meter: the per-skill summary, one line.
- One row, two tenants: before `combo_show_min` a skill flashes as before; after, it joins the line
  (`Hud._join_live`). A meter tick or a delivery takes the row and the line returns; a skill's
  flash yields at once (`Hud._tick_yields`).
- Refused on handset frames: the combo under the 特更 clock (crowds 交更), or whole under the
  flash (sits on the 的士 roof sign).
- Trap: the skill's row runs ~30 px under the rect, hence touch `tick` y 338; on the desk it
  overlaps the NO ENTRY sign (y 352) when both show. `hud_layout.md`.

## `Q215` — Shade is lit by the street, paint gloss is the engine's clearcoat, and the railings are the lamp posts' steel

**Status.** Built 2026-11-14, the user's call from trial frames; supersedes `P3-11c`'s paint reflection. Owed: a sunlit frame with the clearcoat lobe facing the camera, and the lobe's cost on a handset.

- `clean_daylight.tres`: ambient sky contribution 0.4 toward a warm grey, so shade reads neutral,
  not navy. Albedos and roughnesses were already in a real range.
- `vehicle_body.gdshader`: paint and trim use `CLEARCOAT`; the painted sky is no longer mixed into
  their albedo (`paint_reflect`, `paint_face_on` gone). Red `C*` in sun 68.90 → 75.51.
- `railings.tres` `rail_colour` 0.569 = `galvanised_steel`, copied, not read through `materials:`
  (`Q53`). Barriers and bollards unmoved: nothing says they are galvanised.
- Refused: a canyon band in the painted reflection (~3k px moved, the railing's mean not at all);
  a glossier hub material (1,152 px against 1,456 of run noise).
- Trap: `CLEARCOAT` adds a second specular term on every car fragment — profile the fleet
  (`--perf-log`) before calling it free.

## `Q216` — The five façade colours are 20% darker, by eye

**Status.** Built 2026-11-14, the user's call from an A/B. Owed: a source — 40–48% is a judgement, not a measurement.

The five façade `materials:` were back-derived at 49–62% reflectance and read chalky; each is scaled
in linear light (hue held) to 40–48%, inside its own `bounds:` (`hong_kong.yaml`). No schema bump.
Shipped `L*` 61.3 → 56.1.

## `Q217` — The architecture pass: what was fixed, what waits, what was refused

**Status.** Built 2026-11-14 on the user's instruction. Its refusal of staggered traffic decisions is reversed by `Q219`.

- Behaviour: no coast drag with no wheel grounded; `place_at` clears the impact reading and
  `ChaseCamera.snap_to_target` snaps the camera; a bare `tools/sync_generated.sh` keeps the
  resident regions (naming one still drops the others); `load_config` checks every declared source.
- All export presets exclude `tools/`, dev scenes and fixtures. ETL ratchets: a stage `NEEDS`
  every stage whose document it reads; every report counter is read somewhere.
- Performance, result-identical under the seeded verify tools: `PerfClock` columns under
  `--perf-log`; the streamer re-reads its bands only after `recollect_m` of camera travel; railing
  and fence boxes are one body a plan cell (`PropBatch.boxes`: 7,693 railing bodies → 54).
- On hold: a typed `Obstacle` for the near miss (waits on `Q175`), physics interpolation (waits on
  seen judder at 120 Hz), threading the boot (regions ~300 ms is not yet a reason).
- Refused: splitting `TrafficSystem` or `Hud` further, typed ETL documents, an artifact registry,
  one body for the parked cars (cells are freed and re-stood).

## `Q218` — Three hands: a brush for the menu, 黑體 for interface, the Kai for names

**Status.** Built 2026-11-15, the user's picks from sheets. Owed: a frame on a phone (iOS / Android).

- Brush (`TaxiAceBrush-Bold` the game's name; `-Medium` menu choices, headings, a flashed skill or
  penalty name); 黑體 (`NotoSansHK-subset`) for interface text; Free HK Kai (`Q79`) for names —
  street plate, callout place and road; `Knewave` for the English menu and flash. Other English
  stays the theme's sans.
- Faces load over each other, so a missing glyph is the wrong hand, never a box.
- Subsets are cut to the game's own text by `tools/make_fonts.py`; `etl/tests/test_fonts.py` fails
  when the text outruns a subset. Trap: new UI text may need a re-cut.
- Licence: SIL OFL 1.1. Bakudai reserves its name, so its subsets ship as "Taxi Ace Brush"
  (clause 3). Credits name all three (`verify_menu`). 勁揪體 is commercial and cannot be bundled.
  `LICENSING.md`, `fonts/LICENSE`.

## `Q219` — More traffic: the far cars' rules thinned, the cars indexed, the spawn by lane-metres, 60 cars

**Status.** Built 2026-11-15; `cars = 60` and `spawn_main_weight = 1.0` are the user's picks. Reverses `Q217`'s refusal of staggered decisions. Owed: the handset re-take of the tick (`P0-3b`).

- Cars are indexed on a 64 m grid, read **in fleet order** — any other order moves every seeded
  drive (`_turn_path` caches at first read, `_give_way_gap` returns at its first hit).
- A far car reads its rules every `thin_every`-th tick: only past `thin_beyond_m` AND out of the
  frustum, never with no camera, so the seeded drives did not move. `thin_every = 1` is off.
- A spawn picks a road by lane-metres, a main road's × `spawn_main_weight`, one roll of `_rng`.
- Two following rules: a lead on the same edge is as far as the road says (`_leads_on_edge`); a
  lane change needs room to stop from the closing speed (`_lane_blocked`, `_moving_onto`).
- Why 60, not 80: at 80 Causeway Bay fails two gates (two cars meet in a signalled junction; no
  routed vehicle reaches a stop and stands).
- A per-tick give-way memo: built, 2%, removed. A far-car LOD: on hold — the fleet is +2–4 draws.

## `Q220` — The steering thumb has a response curve: the lock is the travel squared

**Status.** Built 2026-11-16 on the user's handset report; extended to three curves by `Q223`. A desk pick; the handset drive owed.

`TouchProfile.steer_curve` (`touch.tres`): `steer_from` raises the share of usable travel to it. An
assist per input method (`Q210`): car, rack, keyboard table and pad rows untouched. Not a longer
`steer_travel_px` (moves full lock away and grows the drawn wheel, `Q204`); that is the next dial.
Pedals stay linear.

## `Q221` — The sound is an option: on or off, and a volume slider, on the Master bus

**Status.** Built 2026-11-16 on the user's ask; on PAUSE too since `Q223`. Owed: the user's ears and a slider drag on a handset.

- `Settings` saves `sound` and `volume` (`user://settings.cfg`); `Settings.apply_sound` sets the
  Master bus. One slider: the buses' balance is `taxi_audio.tres`'s (`Q185`); there is no music.
- The level is the travel squared (`Settings.level_db`, half = −12 dB), in code: it is what a
  slider position means, not a tuned level. Off and zero both mute; saved apart.

## `Q222` — The whole day moves: the sun on one arc at one speed, the colours eased

**Status.** Built 2026-11-16 on the user's instruction; reverses `Q162`'s "the authored daylight holds to 17:00". Pace reset by `Q233`, the night leg added by `Q225`. Owed: the user's drive of a shift; the floor handset.

- The authored rig is one moment of the cycle (`day_at` 0.174, 09:26); `day_until` is gone.
  Daylight keyframes at 07:00, 12:00, 15:00, 17:00 (`day_to_night.md`).
- `Q160`'s "the day writes nothing" holds: an unmoved rig is `resting`, and `DayClock` rests it
  whenever daylight is held (`--day-cycle=off`, ALWAYS DAY), so scripted frames did not move. A
  resting rig reads `time_of_day` 0: the parked roster and traffic keep 07:00.
- The sun's direction slerps along great circles solved so every daylight leg runs at one speed
  (`verify_day_cycle.gd`, within 2%). Colours and energy ease on a smoothstep.
- Noon's key light 2.2 and blue sky are the user's picks. Trap: a blue ground half tints every
  shadow purple (the sky is the ambient); the ground stays grey.

## `Q223` — OPTIONS is a list of groups, the pause has one, and three options join: steering response, steering thumb, frame cap

**Status.** Built 2026-11-16, the user's picks; amends `Q165`'s "no OPTIONS on PAUSE" and `Q221`. `Q239` adds the anchor to CONTROLS. Owed: everything a hand decides — the curves, the swapped sides, the 30 / 120 caps on a phone.

- PAUSE omits what needs a new HUD (language, thumb sides — a HUD readied mid-fare misses the
  fare's signals, `Q165`) and the hour.
- A flag beats the saved pick (`ControlOptions`): `--touch-steer=`, `--touch-side=`; `drive.sh`
  names both at defaults.
- Frame rate 60 / 30 on a phone only, plus 120 where the screen reports it
  (`ControlOptions.caps_for`) — a pick, never the default. Trap: its flag is the engine's
  `--max-fps`; `apply_frame_cap` must not overwrite a booted cap (`P2-6`'s headroom runs read 60.0
  when it did).

## `Q224` — The screen turns to either landscape, and the side insets are the larger of the two on both

**Status.** Built 2026-11-16 on the user's ask. Owed: a handset turned over on iOS and Android (the Android manifest was not read).

`project.godot` `window/handheld/orientation=4` (sensor landscape); no portrait. Left and right
insets both take the larger (`HudLayout.inset_for_safe_area`): the inset is read once and a half
turn resizes nothing, so a re-read would need a poll.

## `Q225` — A free drive's sky comes round: night, a dawn, the morning again

**Status.** Built 2026-11-16 on the user's instruction; reverses `Q160`'s "a cycle is not a loop" for a free drive only. Lap length reset by `Q233`, dawn's colour by `Q235`. Owed: the user's drive of a night.

- `RigCycle.loop_at` 1.714 = 24 h where 1.0 is the shift's 14. `DayClock` wraps a free drive there
  and caps a shift at 1.0, so 特更 still ends at 21:00. `loop_at` 0 is the off switch.
  `--time-of-day=` takes up to 1.714.
- The key light changes hands
  between two keyframes of energy 0 (`verify_day_cycle.gd`). Dawn has its own `dawn.tres`; first
  light borrows `twilight.tres`.
- Memory trap: a loaded `Sky` allocates its radiance map even undrawn — keyframe skies carry
  `radiance_size = 0` (110 MB → 4.7 MB for six). While live, the rig shrinks the authored `Sky` to
  32 px and `_drop_live` restores it: its one write to an authored resource.

## `Q226` — A batch with custom data and no colours draws black on the web: it carries a white one

**Status.** Fixed 2026-11-16 on the user's web report; seen on desktop Compatibility. Owed: the browser, a tram and a signal head.

- Compatibility packs instance colour and custom data into one attribute, zero-fills it and
  multiplies `COLOR` by it (4.7.2); Forward Mobile reads white.
- Fix is data: `use_colors` on and white written once sized — `PropBatch.batch`,
  `TrafficSystem.setup`, `TramSystem.setup`. `TrafficBeams` reads no `COLOR` and is exempt.
- Trap: a new `MultiMesh` with `use_custom_data` whose shader reads `COLOR` owes the white.
  Nothing checks it: headless draws nothing and Mobile is right without it.

## `Q227` — A run after the first starts short of a stand drawn afresh

**Status.** Built 2026-11-16 on the user's ask. Owed: the user's drive; no frame of a drawn start.

- The first run of a session starts at the scene's `spawn_fare_id`; every scripted run is a first
  run, so no `drive.sh` timeline moved.
- Later runs: `DriveLevel._draw_start_line`, uniform over `FareSystem.published_pickups()`, never
  the last run's stand — after 收工, AGAIN and END DRIVE alike. `--fare-seed=` does not reach it.
- `RoadSpawn.starts_a_run` is the bar (resolved, drivable, fits a car `Q52`, short of its stand,
  off a centreline); a refused stand is passed over. 26 of 27 pickup nodes clear it.
- Trap, unchecked: traffic or a parked vehicle standing on a drawn line.

## `Q228` — The pedals show how far they are pushed: a green level up the accelerator, a red one down the brake

**Status.** Built 2026-11-16, arrows amended 2026-11-17, the user's asks. Owed: a handset and a new player's hands.

- A level, not a fade (`TouchSticks.level_box`): the accelerator fills upward, the brake downward,
  by the share of `drive_travel_px`. `hud_style.tres` `touch_go` / `touch_stop` are the only red
  or green on the sticks.
- Open: fading the hint after a first drive (`Q204`); a line of words on the guide page.

## `Q229` — The pause has RESET CAR: back onto the nearest road, the run going on

**Status.** Built 2026-11-16 on the user's ask; the landing rule is amended by `Q241`. Owed: the user's own stuck car — no wedged spot was reproduced.

- RESET CAR / 重置的士, second on PAUSE in both modes: `StartMenu.reset` → `Main._on_reset` →
  `DriveLevel.recover` (`_back_onto_road`, the harbour's recovery).
- Costs nothing but time: no penalty, fare and clock untouched. So it is also a free un-wedge
  mid-fare; a charge or cooldown is the user's call.
- 重置的士, not 重置車輛: 輛 is in neither font subset.

## `Q230` — The drive fades from 60 kph, a thumb is slewed at speed, and a wall turns the nose along it

**Status.** Built 2026-11-16 on the user's report, graded on the pad. Owed: the user's drive on all three, the handset on the thumb.

- Drive fade (`handling.tres` `drive_fade_from_kph`, `drive_fade_curve`): the game's dial, not the
  car's; ~80 kph in 3 s and ~139 in 20 (was 188). Trap: it stands down in drift mode
  (`TyreVehicleController._drive_fade`) — applied there `hold`'s `longest` fell 3.57 → 1.02 s.
- A steering thumb is slewed at speed (`touch.tres` `steer_attack_at_top_s`): `flick@held` peak
  slip at 110 / 120 / 150 kph 20.8 / 29.8 / 31.4° → 7.2°. A stick passes through.
- A wall turns the nose along it (`collision_align_s` 0.3, `VehicleController._align_yaw_rate`):
  `bump@brush30` exit speed at 42 / 63 / 86 kph 0.85 / 18 / 37 → 76 / 77 / 88. 0.1 s swings past
  the wall, 0.2 overshoots. Walls only.
- Not built: a box caught by the car's corner (`bump@post`) is still a dead stop — an off-centre
  deflection is new machinery and the user's call.

## `Q231` — The boot menu is lit at its own hour: 12:44, the stand in the sun

**Status.** Built 2026-11-16 on the user's ask.

The showroom stand (`f_001`) is in HKCEC's shadow at the authored hour and in sun only at 0.36–0.46.
`DriveLevel.showroom_time_of_day` on `city_drive.tscn` (negative = the clock's own hour). Boot only
(`Main` → `light_showroom` → `DayClock.show_hour`); every PLAY restores the run's hour. Trap: a
`--menu=on` frame is this hour, not the authored day.

## `Q232` — A vehicle's panels are pressed in the shader: joints, a crease, and every inked edge seated

**Status.** Built 2026-11-17 (`P3-87`) on the user's ask; the bow 0.04 is his pick. Owed: a handset frame time, the browser.

- No texture, no new vertex channel. `vehicle_body.gdshader` tilts `NORMAL` from a per-face pitch
  (`make_vehicle.embossed`: `COLOR_0.a` in the `.glb`, moved to `UV.y`'s fraction on import) and
  from every inked edge (`UV2`, `Q196`), which seats panes, frames and lenses on every vehicle.
- Only what the real vehicle carries (the user's rule): bus panel joints, box-lorry ribs, a flank
  crease on the saloon, Alphard, Hiace and Coaster. None on the tram (smooth sheet), the coach
  (unsourced, withdrawn) or the taxi (bevelled geometry). The model's readings, his to strike.
- Trap: not `COLOR.a` in the engine — Compatibility multiplies it by the instance colour (`Q226`).
  `verify_parked`'s `pressed kinds:` holds the six kinds. Parameters: `vehicle_body.md`.

## `Q233` — A second driven is a minute on the clock: the shift is 14 minutes

**Status.** Built 2026-11-17 on the user's ask. Not driven by hand: a whole shift, and whether the fare pools and combo hold over ~3× the fares.

- `day_to_night.tres` `length_s` 840: 14 hours at 60 s each; a free lap (`Q225`) is 1440 s.
  Keyframes are fractions, so nothing was re-solved.
- Trap: the rate is `length_s` over `shift.tres`'s hours, not its own dial.
- Trap: a `shift_best_hkd` saved from a 300 s shift is easy to beat; not reset.
- `GAME_DESIGN.md`'s "three-minute sessions" pillar is left for the user to call.

## `Q234` — The tram's doors are folding leaves, four at the entrance and two at the exit; its lenses are faceted

**Status.** Built 2026-11-17 (`P3-88`) on the user's ask. Not seen: a moving tram from the taxi; a Compatibility frame.

- `tools/make_parked.py` `Shape.door_leaves` `(2, 4)`, kerb side only: exit by the driver two
  leaves, entrance at the tail four. The model's reading of "the 4 doors" from reference
  photographs; a doorway per corner would be `Shape.doors_m` and a side.
- Relief is `Q232`'s seat, no shader change: each layer stands ≥ 2.5 mm proud
  (`DOOR_LEAF_PROUD_M`), over the ink's 1.5 mm touch.
- Lenses are geometry (`Shape.lens_bevel_m`, the tram alone): the ink seat never reaches a box's
  front face, and inking the fold would redraw every vehicle's lamps.

## `Q235` — Dawn is blue and dusk is yellow, so the hour reads off the colour

**Status.** Built 2026-11-17 on the user's ask; the strength is the model's middle-of-three pick, the user has not chosen.

Values only: `dawn.tres`, `dusk.tres` and the 06:15 and 18:00 `sun_colour` / `sky_light` in
`day_to_night.tres`; no angle, `at` or energy moved. Not done: first light (05:30) and 19:00 still
share `twilight.tres`, a rose horizon; a shift never sees the 06:15 dawn.

- The 07:00 morning is cool too (2026-11-17, the user: "dawn is still yellow toned"):
  `morning.tres`' horizon, ambient and fog and its keyframe's `sun_colour` / `sky_light`. The blue
  held only at 06:15: the leg into a warm 07:00 left a frame's mean at R 67 / B 64 by 06:45 and
  R 75 / B 62 at 07:00, the shift's opening hour; now R 56 / B 76 and R 60 / B 77. Strength again
  the middle of three, not the user's pick.

## `Q236` — The phone's app draws the 3D scene at 0.75 of the window; a phone's browser does not

**Status.** Built 2026-11-17, the user's picks; measured on the iPhone Air. Reverses `Q91`'s "no `.mobile` MSAA override" for the app. Owed: the user's handset drive at 2x MSAA; the A13 floor and Android.

- `clean_daylight.tscn` `phone_scale_3d = 0.75`. App only (`Handset.is_app`: `mobile` and not
  `web`) — on the web's Compatibility renderer the same scale stair-steps, so a phone's browser
  stays 1.0 (`LightingRig.fit_handset`; `verify_day_cycle` holds each build's pair).
- iPhone Air, 1.0 → 0.75: video memory 359 → 270 MB; a lap's frames over 16.7 ms 26% → 1%. Cost:
  small sign plates and roof lettering blur, the ink line ~⅓ thicker.
- `project.godot` `msaa_3d.mobile = 1` (2x; desk and browser keep 4x), pinned in
  `verify_settings`: 270 → 236 MB. Trap: a still cannot show railing shimmer in motion, `Q91`'s
  reason for 4x.

## `Q237` — A post is tested against the drawn asphalt itself, because a ribbon's kerb is a share inside a junction

**Status.** Built 2026-11-17 on the user's report (a lamp column in a Percival Street turning lane). Not done: the signal heads (`signals.py` `bind_in_carriageway` asks the same ribbon question).

- Inside a junction `Ribbon.past_kerb_m` reads kerb stations that describe a share (`Q57`), so
  `in_carriageway` passed posts standing 2–3 m inside the drawn road.
- `drawnroad.drawn_carriageway` (the region's `whole` less its islands) is a third refusal in
  `lamps.py` and `signs.py`, booked under the existing `in_carriageway` counters;
  `in_carriageway_area` / `posts_in_carriageway_area` count what only the polygon caught. Refused,
  never pushed. A deck's column is exempt.
- Cost over the two regions: 18 lamp columns and 39 signs (9 NO ENTRY plates among them) are
  holes. Most stand on refuges the region paves; drawing those as islands would bring them back.

## `Q238` — The touch wheel is the car's: it stays turned when the thumb lifts, comes back with speed, and a thumb that goes round it turns it

**Status.** Built 2026-11-17 on the user's design, amended the same day off the handset (path-based spin detection withdrawn). `Q243` reverses "no spin state" and "the larger steers". Desk picks; the handset drive owed.

- The wheel has a position (`InputRouter._wheel`): a sliding thumb adds to it, a lift leaves it,
  and `steer_for` returns it in proportion to speed (`steer_return_at_top_s`) — it holds on a
  standing car. Keys or a stick take it over; a pause zeroes it.
- The wheel hangs from the thumb: the landing is its twelve o'clock, its middle `wheel_radius_px`
  below; the turn is the thumb's angle round that middle (`_go_round`), `spin_lock_deg` for full
  lock, nothing read inside `wheel_hub_px`. No spin state: slide and turn are both read every tick
  and the larger steers (`_thumb_wheel`). A slide along the top is unchanged by construction
  (`TouchProfile.spin_share`; `verify_input.gd`).
- Withdrawn: a SLIDE / SPIN option (the user: one scheme); detecting a spin from the path's
  curvature (it took a hooked slide for a spin).
- Costs are listed in `touch.md`. Not done: a hint that teaches the spin, haptics.

## `Q239` — The wheel and the pedals may stand still: CONTROLS offers FOLLOW THUMB or FIXED

**Status.** Built 2026-11-17 on the user's ask; relative (`Q83`, `Q204`) was the default until 2026-11-18, when the user made FIXED the default (`resolve_anchor`, and `drive.sh` names it). The handset drive owed.

- `ControlOptions.anchor`, `--touch-anchor=relative|fixed`: 操控位置 on CONTROLS, on the pause's
  too (no HUD is renewed).
- Fixed changes only the thumb's origin (`InputRouter.Thumb.fixed`): the middle of its rest
  instead of where it landed. A fixed wheel is where the thumb is on it — never added to.

## `Q240` — A building's street band takes its measured lightness, shrunk by what its walls disagree

**Status.** Built 2026-11-17 on the user's ask; reverses the photographs'-`L*` refusal (`Q37`) for the street band alone. Owed: the user's drive; Causeway Bay frames.

- `buildings.band_lift` ships `step³ / (step² + noise_street + noise_tower)`, step being the
  street band's `L*` less the tower's; `colour.with_lightness` applies it after the hue.
  `facade_hue.band_lightness` scales it; 0.0 is `Q197` byte for byte.
- Noise is per building: `facade_survey.band_noise_l` → `bands.noise_l`; under two faces takes
  `FALLBACK_SPREAD_L` 13.2. The build refuses `band_lightness` > 0 on a table without `noise_l`.
- Why only this band: the refusal's number is the `L*` spread within one building (22.9) against
  16.25 between; a step between two bands of one building is read under the same sun. A building's
  own lightness is still the height ramp's; podium and tower take none.
- Ships on 1,644 of 2,213 surveyed buildings, median share 0.53. No channel, no schema bump.
- Measured and not built: the cut at the shopfront's own head (moves 10k–34k px beside
  lightness's 97k–148k); storey relief from photographs (a pitch two faces agree on for 187 of
  2,198 buildings, barely visible; `tools/facade_unwrap.py` has no consumer); an invented storey
  relief (reads in sun only; not picked).

## `Q241` — A placed car is pushed to the physics server at once, and a reset lands on a road it can leave

**Status.** Built 2026-11-17 on the user's bug report, reproduced through synthetic taps (`--touch=on`); amends `Q229`. The user's own handset drive owed.

- `VehicleController.place_at` calls `force_update_transform()`: a tap or click arrives after the
  frame's last transform flush and before the physics sync, which wrote the old pose back. Every
  menu teleport failed for a person and passed every scripted check. `verify_vehicle` reads the
  body off `PhysicsServer3D` before any flush.
- Trap: test a menu flow by tapping its buttons (`Input.parse_input_event`), never by calling the
  handler or emitting its signal.
- A reset lands on an edge that is `is_routable` and joined to the run's start line in the
  player's network (`DriveLevel._drives_away`, `RoadGraph.nearest_edge`'s `accept`): of 984
  drivable edges, 37 refused at the lane bar and 14 as cut off. The legal network is wrong for
  this — one-ways and turn bans leave 8 edges that lead to the start line.
- On a two-way edge dead-ended ahead (`RoadRouter.moves_from`) the car is turned round.
- Radius stays `RoadGraph.NEAREST_REACH_M` 60 m: 99 of 6,933 lane samples fall to the start line,
  and 100 / 150 / 250 m still leave 71 / 63 / 62.

## `Q242` — Stops and stands are drawn from TD's own paint, legends included

**Status.** Built 2026-11-17 on the user's instruction ("add bus stop, mini bus stop, taxi on/off area and tram station according to data"); lifts `Q65`'s refusal of road lettering and stand markings for these codes. The user's look and drive owed.

- `pipeline/stopmarks.py` → `stopmarks.glb` (`CITY_SCHEMA` 47), two paints on the road marks' and
  box junctions' `.tres`. Wan Chai draws 188 markings (23 bus stop boxes, 48 stand boxes, 105 BUS
  STOP legends, 12 taxi legends), 37,524 triangles, 2.05 MB; Causeway Bay 44, 7,654, 0.42 MB.
- A legend needs no typeface: `DTAD_RD_MARK_SYM_LINE` files it as stick-font strokes in place and
  to size (BUS STOP 巴士站 is 11.6 x 2.5 m, the sheet's 1600 / 2700 / 1000). `P3-21`'s no-go was
  `DTAD_RD_MARK_ANNO`'s rectangles and stands. Authored: the stroke's width, 0.12 m.
- A legend filed as a point (33 in the two regions) is stood with the region's stroke legends as
  its glyph: their vertex-wise median, each laid onto it. Fit p50 3.6 mm over 89 legends, turn p50
  0.64 deg. The point is taken for the legend's middle — unpublished, and nothing calibrates it:
  0 of 1,205 `1047` points citywide lie inside a stroke legend.
- Refused and counted: 44 `RM1049` filed twice; 22 features wholly past the drawn kerb (the stand
  boxes' 0.1–0.8 m returns, the one `RM1045` tram stop line on the reserve); point codes `1047
  (n*` / `(w*`, `1048`, `1149`.
- Stand signs (`P3-92`): `TS324` TAXI STAND 的士站 is drawn, white on green from the sheet's own
  cell — 42 plates in Wan Chai, 3 in Causeway Bay, 18 poles double-sided (`back_to_back`). The
  minibus stands' `TS322` (green, 35 and 5) and `TS323` (red, 4) are a coloured ink on white, so
  the whole plate is the baked cell; the taxi pick-up / drop-off plate `TS3643` (9) is black on
  white with the taxi's red as a second ink (a `text` layer's `accent`). 29 plates hang back to
  back in Wan Chai. The atlas is 1536 x 256, 119,611 B. An earlier note here said those three
  carry three colours and could not be baked: wrong for the minibus pair, which carry two.
  Not drawn: `TS659` and `TS3649`, blank on the sheet.
- Furniture (`P3-93` to `P3-95`, `pipeline/stops.py`, `CITY_SCHEMA` 48): a flag on a pole at each
  operator stop in `bus_routes.json` (Wan Chai 70 bus, 50 minibus; Causeway Bay 32, 15), a
  shelter on the track's left at each tram stop (19, 5). Authored, since nothing publishes it: 0
  of iB1000's open-sided blocks lie within 6 m of a stop. 5,004 triangles a region's library.
- The user's picks, 2026-11-18: the flags stay at the first sizes (shown small, as built and
  large); no taxi-point flag, since TD's `TS3643` and the lettering mark the point; a shelter's
  two posts are solid and its roof is not, with no island. Two calls stand that he was not
  asked: lettering and stand paint are back in scope against `Q65`, and a minibus flag stands at
  every published stop, not only termini (the routes data carries them all).
- Cost from the start line at 3 s (`P3-96`): `stopmarks` 3 draws, `stops` 6 (only the shelter
  casts; 12 with every mesh casting). `prims` moves run to run by more than either layer. The
  Both layers, both regions: 2.30 MB of a 101.1 MB PCK (`Web Demo` preset, 101,148,268 against
  98,849,920 B). Desktop frame time over 17 s from the start line, three runs a side: p95 11.7 to
  12.0 ms with the layers and 11.6 to 11.9 without — inside the noise. iPhone Air, release build, parked on the start line under
  `--max-fps 120`, 25 s a side: 120.0 fps with both layers (143 draws) and 120.0 without (133),
  p95 14.8 ms each — at the screen's cap, so the layers cost nothing it can show. With the camera moving (the
  menu's orbit, traffic running, 138 to 197 draws, 30 s, the final build): 120.0 fps, worst frame
  14.6 ms.
  Look sheet: `asset_viewer.tscn --asset=…/wan_chai/stops.glb --lineup=2.5`.
- Off switch: delete the `stop_marks:` block.

## `Q243` — A thumb spins the wheel only once it is well down its side; until then the slide steers

**Status.** ⛔ Superseded 2026-11-18 by `Q251`: spin and slide are an explicit pick, never a switch mid-stroke. Was built 2026-11-18 on the user's ask ("only a more explicit spin turns the wheel into spin mode, and left right works most of the time"); reversed `Q238`'s "no spin state" and "the larger steers".

- The slide alone steers, at any height, until the thumb is `spin_enter_deg` (120°) round the
  wheel's middle. Then the spin carries the wheel from where the slide had it to full lock at
  `spin_lock_deg` (180°); back inside 120° the slide steers again, the difference shrinking to
  nothing by the landing point (`InputRouter._go_round`, `_thumb_wheel`).
- Reason: under `Q238` a slide that sank about a radius (77 units, 6 mm) was read as a turn, and a
  stroke back across under the hub left a bearing that outvoted the slide on the other side.
- Deciding number: a slide 100 units out now sinks 135 units before it is a spin, 106 at 50 out;
  about 77 before. Above the wheel's middle the bearing is re-read from the thumb's place, so
  nothing a hub pass left is carried.
- `TouchProfile.spin_share` and `rim_travel_px` are gone with the rule they served.
  `verify_input.gd` holds a sunk slide across the wheel as a slide; it fails at
  `spin_enter_deg = 92`.
- Still withdrawn: curvature detection, a SLIDE / SPIN option. Cost: the wheel eases from 0.28 to
  0.21 of lock between three and four o'clock on the way into a spin.

## `Q244` — A traffic car is drawn turned the way it moves across the lanes

**Status.** Built 2026-11-18 on the user's ask ("turn when changing lanes, instead of just sliding into it"). Desk-checked; the user's drive owed.

- `Car.steer` is the angle the car's path makes with its road — the lanes it crossed this step over
  the metres it travelled — eased over `lane_steer_m` (3 m) of travel and back to 0 once the lane
  is held. `TrafficSystem.drawn_pose` turns the body, the instance and the beam by it.
- Reason: `_pose_on_edge` faced a car down its road while `_change_lane` moved it sideways.
- Drawn only: `car.pose` and every rule that reads a heading are untouched, so `verify_traffic` is
  byte-identical on both regions but for the new `lane:` lines. A knock folds the steer into the
  pose the car slides from.
- Deciding number: 6.2° drawn of the path's 6.0° (Wan Chai), 6.5° of 6.6° (Causeway Bay) on the
  staged road. Mutations caught: the sign, a steer that never straightens, half the angle.
- A car pulling out from behind a parked vehicle crosses at the turning pace whatever it drove
  (`_drive`'s top-up), so its path is steeper and it is drawn so; `Car.lanes_moved` carries every
  lane it crossed in the tick to `_steer`. One that crosses while standing still is not turned.
- A sharper turn is a shorter `lane_change_m` (25 m), which moves every seeded drive: not done.

## `Q245` — The taxi's tail clusters run in to the plate, its grille is mostly chrome, and its front amber is the slim corner lens

**Status.** 🟡 Built 2026-11-18 (`P3-82`) on the user's "build the geometry pass"; amends `Q190`'s rear and nose. Owed: his look, a handset frame.

- Laid beside the real car (Commons: KX3816, VK5888, VV9455), the Tomica Limited Vintage Neo 1:64 and the Tiny 1:18, the taxi's visible gaps were geometry, not relief: a sampled normal map was planned first and not built.
- `tools/make_vehicle.py` `Proportions`: `tail_lamp_half_width_m` 0.10 → 0.22 at `tail_lamp_x_m` 0.44 (corner to 2.5 cm off the plate frame); `grille_bars` 4 → 6 on `grille_half_width_m` 0.385; `headlamp_half_width_m` 0.17 (was a literal 0.15); the front amber 0.13 → 0.09 m wide (`front_indicator_*`).
- The lens order stays `Q190`'s red over amber over white, and `headlamp_x_m` stays 0.58 under `taxi.tscn`'s spots.
- `boot_seam_x_m` 0.46 is its own dial: the seam was read off the lamps' inner edge and would have followed them in.
- Refused: the boot lid's share of each cluster as separate lenses. 2,226 triangles against the 2,200 ceiling; one lens a side is 2,154 (was 2,130).
- Not seen: the Tiny City 1:64 `Q190` was built from. If it carries the corner cluster, the old pair of values is the way back.
- The roster taxi follows (`Q200`): `parked.glb` rebuilt. Roster 11,650 → 11,722 triangles and the throttle route 727,638 → 728,814 primitives at 1 s, both measured before the picks below, which add 24 triangles a taxi.
- The user's picks from a sheet of four (2026-11-18): the head lamp lens is `CLEAR`, a tenth colour, so the lit lamp burns white; the reversing lens is the inboard `reverse_lamp_width_m` 0.16 of the cluster's foot and the rest of that band is brake lens (2,178 triangles). Not taken: brighter hubs, a chrome strip under the clusters.

## `Q246` — The drive has music: a bed for each part of the day and layers that climb with the style combo

**Status.** 🟡 Built 2026-11-18 (`P3-97`) on the user's ask and the user's picks by ear from rendered loops. Reverses `Q221`'s "there is no music" and, for the music alone, its "sound is the Master bus alone". Owed: the user's drive heard (`bed_db` is not yet set against one), the web build, a handset, the PCK.

- Thirteen loops of the same eight bars at 84 bpm (75 until 2026-11-18, below), synthesised by `tools/make_bgm.py` like every other sound: four beds and six combo layers. They play locked in one `AudioStreamSynchronized` and are only turned up and down (`DriveMusic`, `music.tres`), so nothing waits for a beat and nothing drifts.
- **The hour is the rig's.** Morning from 05:30, afternoon from 11:00, night from 18:30, midnight from 00:00, each fading in over half an hour of the clock. A held hour (ALWAYS DAY) plays the afternoon bed.
- The user's picks: day in the major (Fmaj9 Em7 Dm9 G13sus), night on its minor side (Dm9 Am9 B♭maj9 G9sus) for "more difference"; morning a single-note piano line; midnight no piano at all. Each night chord shares three notes with the day chord in its slot, so the two cross-fade.
- **The combo is ×1 to ×8** (`StyleCombo.total()`, a count past 8 keeps the last row): shaker, congas, muted guitar, arpeggio, clap, horn stabs, then everything lifted. Each count adds or lifts and none drops. The layers leave over 2.5 s when the combo ends.
- This is not `fares.md`'s refused "sound on a skill": no one-shot, no award sound — the count moves the music's own layers. The combo is still never money (`Q205`).
- The menu's SOUND page gains MUSIC on / off and its own slider, on a `Music` bus; the sound's switch and slider stay the Master and silence the music with everything else. Silent while parked, like the taxi (`Q185`), and faded in over 5 s as the car drives off (the user's ask); the menu has no music.
- Cost: 3.01 MB imported (QOA) for 14.9 MB of source `.wav` (3.37 and 16.7 at 75 bpm), which is in git and not LFS. The PCK delta is not measured.
- **The bed is a street groove** (2026-11-18, the user: the first beds "feel too spacy, can we have sth more city"; picked by ear from three rendered takes over city pop at 96 bpm and funk at 104). Swung drums, a walking bass and an electric piano at 84 bpm replace the pad, the echoing bells, the held lead and the noise wash. The hours thin the one groove: morning keeps its single-note piano line, midnight still has no piano and holds a low pad for its harmony. The chords are unchanged.
- The bed now carries drums and bass, so the thump, root-pulse and top-line layers became congas, a muted guitar and horn stabs; `tiers` is unchanged. The beds average −17 to −19 dBFS against −23 to −26, so `bed_db` went −12 → −18 to hold the level; still not set against a drive.
- Not built: a cab-radio filter (rendered, heard once, not picked); music under the menu; a `drive.sh` flag (the music moves no frame).

## `Q247` — HyD's roadside planters are built: a kerb-height wall, and a shrub bed where the walls close

**Status.** 🟡 Built 2026-11-18 (`P3-98`) on the user's ask ("vegetation marked in open data which is not tree") and the user's pick of three renders. Owed: the user's drive into one, the PCK. Checklist in `.claude/rules/planters.md`.

- Source: HyD Roadside Planter Wall (`INV_RPW`, `hyd_rcd_1632211024666_47455`), paged from CSDI in EPSG:2326. A polyline and an id; no height, level or planting. Wan Chai 48 features (22 close into a ring), Causeway Bay 6 (1).
- The other candidates were measured and refused: iB1000 has no grass, shrub or planter class; the 3D Visualisation Map's `VEGETATION(TB)` is ~97% tree canopy; HyD Vegetation in Causeway Bay is 79% slope and 90% under canopy.
- The look is the user's pick, B of three: A a kerb-height box with a flat green top (a thin line from a car), B the box with a low shrub mass, C the shrub alone. Wall 0.45 m; clumps 1.6 m across, 0.45–0.85 m over the wall, each its own height and green. All authored.
- Only where surveyed, as `Q171`: a bed is a ring one feature's walls close; an open wall stands bare.
- Never on the drawn road: cut back to 0.05 m outside the level-0 carriageway region (58.9 m² in Wan Chai), refused whole over half on it (3 of 22 rings). Cut by the tiles' walls that stand through it (5.2 m²): a ring round a lift tower is not planted through.
- Built: Wan Chai 19 beds, 30 walls, 897 m² planted, 10,166 triangles; Causeway Bay 1 bed, 5 walls, 26 m², 374. One draw a region.
- A planter is a crash: the walls ship as `planters_collision-colonly` in the same `.glb` (3,481 / 213 triangles), the first generated layer after the road to carry its own body. The planting collides with nothing.
- `city.json` schema 49 names `planters`.
- Walls under a deck (checked 2026-11-18): 22 of Wan Chai's 48 features, 710 of 2,224 m. In plan the 17 under a flyover are street-level islands (the large ones cross the deck's carriageway); four under footbridges, 139 m, sit on street islands but are not settled by shape; one (10 m under) was not looked at. None found on a deck.
- Not done: registering the railings beside a wall; lighting at night.

## `Q249` — The far shore is built: Kowloon's skyline as one silhouette mesh, drawn past the far plane

**Status.** 🟡 Built 2026-11-18 (`P3-100`) on the user's ask; the density (5,000 of 2,000 / 5,000 / 10,000) and the dark night skyline are the user's picks from frames, the same day (the dark skyline reversed by `Q252`: floodlit at night); measured on the handset. **Amended 2026-11-18** on the user's ask: every region ships its own far version, and Kowloon is a far-only region (last bullet). The handset measured, no cost it can show (last bullet). Checklist in `.claude/rules/backdrop.md`.

- A real mesh at its true place, not a sky panorama: iB1000 `Building` footprints over a strip of Kowloon (114.152–114.198 E, 22.2915–22.308 N; 27 more sheets, 922 MB fetched), each extruded to its published `ROOFLEVEL`, tallest first under `triangle_cap`. At 5,000: 278 of 1,146 blocks over 30 m, down to 56.0 m, tallest 460.6 m; 4,976 skyline + 434 shore + 216 sea triangles, 378 KB, 510 m off the frame.
- **The camera's `far` stays 400 m.** Raising it to 8,000 was measured and refused: `prims` 460–587k → 781–930k (+70%), draws 139–156 → 253–290, the streamed city behind the car entering the frustum. `far_shore.gdshaderinc` squeezes everything past `pin_from_m` (500 m) into the last `pin_band_m` (8 m) of depth instead, in one projective step so depth order holds; `extra_cull_margin` defeats the engine's own cull.
- Cost, measured by `--hide-layers=backdrop` on the same drive: +5,626 primitives and +2 draws, every tick, with traffic or trams alone.
- The shore is a closing (200 m) of the footprints and sea walls, holes filled — not `basemap.sea_of`. Kowloon's published shoreline has gaps of hundreds of metres (West Kowloon, east Tsim Sha Tsui) and the cut finds no sea.
- The far sea is a rectangle from the frame's north edge to the strip, plus the sea of the region and its neighbours a second time: the far plane clips the basemap's water 400 m out, short of the frame on a diagonal. Drawn by `water.gdshader`, told apart by `COLOR_0` alpha 0. ⚠️ Not a survey: undrawn land beside the region reads as water from across the map.
- PCK: 105,267,184 → 105,397,204 bytes, +130,020 (0.12%), the web preset exported from a clean tree with `backdrop.glb` out and in; the second export with it repeats to the byte.
- Only Wan Chai ships it; Causeway Bay is drawn beside it, and a frame from its side of the joined map shows the skyline and the sea. `city.json` schema 50 names `backdrop`.
- 24-bit depth (Compatibility, the web build) orders the band at about 35 m a step at 1 km. Frames from Expo Drive East under `gl_compatibility` show no artefact, and the web preset, exported from a clean tree and driven in Chrome (WebGL 2) to the same junction, draws the skyline and the sea out to it with no shader error.
- Unlit at night, the user's pick over lit windows and over hiding it after dusk: the skyline is dark blocks against the sky. 🔁 Reversed by `Q252`.
- Two costs read off the code in review and closed in `city_layer.gd`, neither measurable on the desktop (frame time is at its 60 fps cap with the layer and without, GPU time not reported). The cull margin put the far shore's box round every lamp, so it is drawn on its own visual layer (`FAR_VISUAL_LAYER`) that a vehicle's beams leave out of `light_cull_mask`. The far sea repeats each frame's own water, so it carries a `sorting_offset` that sorts it as the furthest thing drawn and the copy fails the depth test rather than being shaded first. ⚠️ The opaque sort is in coarse depth layers, so the handset is the measurement.
- **Culled by hand when out of view** (the user's ask, 2026-11-18): the engine cannot cull through the margin, so `city_layer.gd` hides each mesh whose own box, grown 200 m, lies outside a side of the camera's view (`far_cull.gd`; the far plane is never asked). From Expo Drive East, traffic off: facing the harbour +5,626 primitives and +2 draws as before, the skyline pixel-identical; facing south +216 and +1. The far sea is still drawn there — its box covers the region, so the camera stands in it.
- iPhone Air, release build of `7290d97b` from a clean tree, the menu's orbit with traffic running, `--max-fps 120`, 18 s recorded after a 12 s skip, two runs a side: 120.0 and 119.8 fps with the far shore, 119.7 and 119.3 with `backdrop.glb` taken out; p95 13.2 ms and p99 13.4 to 13.5 ms on all four; worst frame 14.0 to 16.4 ms with, 14.1 to 14.5 without. At the screen's cap either way, so it costs nothing the phone can show. Video memory 318 MB against 316.
- Colour is three height bands off `materials:` (`Q33`); the density is 5,000, the user's pick.
- **Amended 2026-11-18: a far version per region, never a far shore per viewer** (the user's ask: Kowloon will be driven, and must be seen from Wan Chai and Wan Chai from it). Refused from the same `/eval`: raising `far` to 800–1,000 m with a third LOD tier (the harbour is ~1 km, so Kowloon's tiles would still be unloaded, and `+70%` primitives at 8 km is the nearest measurement), and a second camera for the far view (a second render pass for the depth split `far_shore.gdshaderinc` already makes in one).
  - `pipeline/backdrop.py` builds every declared region's `backdrop.glb` over its own `bounds`: skyline, shore slab, and water. `backdrop.bounds`, `backdrop.regions`, the strip's two checks and the far-sea rectangle are gone. The water is a driven region's frame sea (as before) plus the **open water** out to `sea_reach_m` 600: the reach less the shore's closing, outside every driven frame, kept where it joins a frame's sea. 600 m because Wan Chai's frame stops 510 m short of Tsim Sha Tsui's box.
  - Kowloon is `regions.tsim_sha_tsui`, `far_only: true`: `__main__` runs `fetch` (the backdrop's map alone) and `backdrop` for it, and no `city.json`. Its far version reproduces the old one exactly: 278 of 1,146 tall blocks, down to 56.0 m, 4,976 skyline triangles. Wan Chai: 422 blocks down to 50.3 m, 4,994; Causeway Bay 128 down to 30.3 m, 2,037; Mong Kok 292, 4,995; Sha Tin 93, 1,973 and no water.
  - `sync_generated.sh` ships the far version of every built region it is not asked for (`python -m pipeline.backdrop --built`), listed as `regions.json`'s `far`; `CityRegions` stands `region.tscn`'s `Backdrop` node alone for each at the `city_offset` its `backdrop.json` (schema 2) carries. `city.json` schema 52.
  - `backdrop.gdshader` discards every fragment nearer than `street_far_m` from the eye, where the streamer has every tile loaded, so the simplified blocks never show round the real ones. Fog reads the true view position, so a far version is fogged at its real distance (frames: the skyline hazes with distance by day; floodlit at night; no artefact under `gl_compatibility`).
  - **Distance cap** (`far_view.tres`): a far mesh whose box's nearest point is past `max_far_m` 8,000 (86% fog at noon's density), ±`hysteresis_m` 100, is hidden. Lifting it to 50 km adds Sha Tin, ~11 km off: +1 draw, +2,002 primitives (its build of the day, 2,002 triangles). No line-of-sight table: a hidden near region costs vertices only.
  - Cost, traffic off, against `--hide-layers=backdrop`: Expo Drive East facing the harbour +15,834 primitives and +7 draws (+5,626 and +2 before); facing south +5,264 and +2 (+216 and +1); Hennessy Road looking east +12,992 and +6, where the gap at the street's far end now holds the rest of Wan Chai and Causeway Bay. Desktop at its 120 fps cap either way. The web PCK +340,904 bytes (107,455,096 to 107,796,016; Kowloon's strip alone before, five far versions after).
  - **iPhone Air**, release build of `0c2185b8`, the menu's orbit with traffic running, `--max-fps 120`, 18 s recorded after a 12 s skip, two runs a side: 120.0 and 118.9 fps with the five far versions, 118.5 and 119.0 with every one taken out; p99 13.3 and 14.1 ms with, 13.7 and 15.3 without; worst frame 14.1 to 17.2 ms with, 14.7 to 16.2 without. At the screen's cap either way. Draws 180 to 182 against 174; video memory 319 to 320 MB against 316 to 318.

## `Q250` — The waterfront is drawn from what is published: pedestrian lines on the ground, a quay cut into it, and the land beside the harbour

**Status.** 🟡 Built 2026-11-18 (`P3-101`) on the user's ask ("more vivid without inventing too many things"), after a trial he saw in frames. Owed: his pick of the line tone (25 / 30 / 35 / 40 / 50% rendered beside none, `build/driver/tone_sheets/`), the handset's frame time. Checklists in `.claude/rules/paths.md` and `.claude/rules/basemap.md`. Per region like every other layer, on his call.

- **Why the waterfront was one grey slab.** The ground is flat `concrete_paving` by design (`Q36`), iB1000 publishes open space on about a sixth of the 150 m shore band and no surface class at all, and what it does publish there is lines.
- **The lines** (`pipeline/paths.py`, `paths.glb`, `city.json` schema 51). iB1000 `CartoPedLine`, domain decoded from the data dictionary: `PA` pavement margin and `FPW` footpath over 1.5 m are edges, drawn 0.3 m wide; `FP` footpath 0.5–1.5 m is a centreline (nearest other `FP` line 21 m off at the median, against 1.85 m for `FPW`), drawn 1.0 m, the middle of its class. Steps, footbridges, subways, covered walkways and margins under structures are not drawn. Wan Chai: 21,733 m read, 20,565 m drawn in 14,212 triangles; Causeway Bay: 42,110 m read, 38,863 m drawn in 43,312.
- **Not the kerb.** The kerb stays `CartoTransLine` `RM`, HyD and TD. Under 1 km of 62 km of `PA` lies within 1 m of the carriageway; a line is cut back 0.5 m outside the carriageway region (207 m and 123 m).
- **`max_grade_pct` 100** refuses ground no path lies on (430 m, 2,415 m): a retaining wall or cliff the 4 m terrain cell smears into a slope. `verify_paths.gd` found it — 60 triangles steeper than 60° in Causeway Bay.
- Tone: `path_edging` 35%, the clean end of concrete, so a line reads on paving (20%) and on grass. Every rendered tone reads near white on grass under the rig's exposure; the pick is between them on paving.
- Cost: +3,576 primitives and +4 draws on the throttle route (`--hide-layers=paths`). Resident paint by `resident_budget.py`: Wan Chai 173% → 178%, Causeway Bay 93% → 108%; the cells cull at draw (`Q135`). The lever is `sag_m` / `lift_m` (43,312 → 34,926 triangles at 0.07 / 0.10) and the plan corners (24,186 of them).
- **The quay** (`pipeline/shore.py`). 🔁 Reverses `Q140`'s "the triangle that straddles the shoreline slopes over its own width, which is the sea wall the low-poly look affords", on the user's instruction. The decimated ground is cut along the sea polygon's edge after `collapse` (`Q25`'s order): land keeps the terrain to the line, the sea drops to `seabed_m`, and where the nearer published line is a sea wall or a breakwater (`shoreline.hard_types: [SWA, BRE]`) a vertical face in `concrete_sooty` joins them — part of the tile and its collider. A high-water mark slopes from the line, on his call. `basemap.json` schema 3 publishes the lines as `shoreline.hard` / `soft`.
- Wan Chai: 3,062 m of sea edge over the ground, 2,776 m of it quay, 1,484 triangles; Causeway Bay's box holds 165 m. The two shoreline numbers, 4 m samples on LOD0: sea ground above the water 1.7% → 0.0%; land within 12 m of the sea under it 17.8% → 9.6%. The residue is the sheets' own terrain at 1.1 m in inlets narrower than `seal_m`, which the sea polygon closes.
- Hard or soft is read per point by position (the nearer line), so a wall and a slope meet without a crack. A cut point takes its colour and UV payloads from its nearest corner: blended, 500 triangles stopped being ground to `trees.tile_corners`. The cut loses no plan area (2,088,688.5 m² before and after); GROUND collider offset 0.000 m; a car driven off the quay lands under the water and is pulled out.
- **The land outside the tiles** (`basemap.land_mesh`, a second mesh in `water.glb` on `harbour_land.tres`). The breakwaters were bare background: the water frame reaches 320 m past the region and nothing drew the land in it. Now flat at `land_level_m` 2.6 (the median top of Wan Chai's own quay, 2.62 m) in `concrete_paving`, within `land_within_m` 250 of the sea, less every declared region's box, with a face to the seabed under every sea edge. 24.7 ha and 3,337 m of face in Wan Chai's frame, 12.1 ha and 1,565 m in Causeway Bay's; 472 and 147 triangles.
- ⚠️ Out there a natural shore is a wall too — no terrain is read, so nothing slopes. ⚠️ Authored: `land_within_m` (the frame also holds the hillside) and the slab's flatness. ⚠️ The two frames overlap, so the land between them is drawn by both; from the air the slab stops 250 m inland against bare background.
- PCK: 105,449,332 → 107,482,328 bytes, +2,032,996 (1.9%), the web preset exported from a clean worktree before and after; the two `paths.glb` are 2.15 MB of it on disk. `tools/check.sh` exits 0 in that worktree.
- A ground row's box grows to hold what the cut made of it (`buildings._hold`): the seabed is under every sheet's terrain, and a point cut into a triangle spanning two sheets carries its nearest corner's row. `verify_tiles.gd` found it — 8 vertices 13 m east of their sheet's box.
- A moored Star Ferry at the pier (the user's suggestion): built as `Q254`.

## `Q248` — Vehicles are glossy and inked: crowned panels, the painted sky back on paint, black lines and a black outline

**Status.** 🟡 Built 2026-11-18 (`P3-99`) on the user's picks from sheets, set against a photo of a real Crown Comfort. Reverses `Q215`'s "paint takes none of the painted sky" and amends `Q196`'s line weight. Owed: the handset's frame time, the web build (varyings), a night look, the PCK.

- All in `vehicle_body.gdshader` and `vehicle_body.tres`, so the taxi, the traffic and the parked roster take it together. No texture, no vertex channel, no mesh rebuilt.
- **Crown**: each panel's normal leans away from the body's middle by the fragment's own place on the body (`crown` 1.0 over 3 m). A flat bonnet shades and reflects as a gradient; before it, the sky on a flat panel was a wash.
- **Sky on paint**: `paint_reflect` 0.6, `paint_face_on` 0.12, power 2.5, base `paint_roughness` 0.55 → 0.35 — the stronger of two, the user's pick over 0.35 / 0.0 / 4.0. Price, chase camera, red paint: `C*` 68.7 → 64.7 in sun, 61.4 → 57.9 in shade, hue 22° → 15° there (toward pink).
- **Trim** takes the sun's glint (`trim_glint` 1.5); it could not be picked out on a grille at roster size.
- **Ink** is black (`ink_darkness` 0.35 → 0.0) at the old 2 cm. 4 cm was built and refused by the user: a line exists only inside the triangle that owns its edge, so a pane's diagonal cut the wider line into a wedge. A bold even line needs `tools/vehicle_ink.py` to carry an edge across triangles, about two triangles a pane (the taxi has 22 under its ceiling).
- **Outline**: `vehicle_outline.gdshader` as the material's `next_pass`, the body grown and inside out, 1 cm (3 cm read too thick from the chase camera, the user's call). Grown by the vertex's place on the body, not its normal — flat-shaded faces opened at every fold and the line came out dashed. Folded away in the shadow pass; fades with a traffic car (`vehicle_fade.gdshaderinc`).
- Cost, Fleming Road with traffic, desktop: frame p95 12.5–12.6 → 12.6–12.8 ms (inside run noise); `prims` 0.96–0.97 M → 1.49 M, every vehicle submitted twice.
- Refused from the same sheets: a sampled normal map for the crown (per-kind maps, and its spike moved nothing from the chase camera), two-tone cel light, white strokes on glass, a line or seat removed from glass alone.
- Way back: `paint_reflect` 0 and `crown` 0 are `Q215`'s car.
- **Amended 2026-11-18, the user's pick from a sheet of seven city lines and a night A/B: the city's line goes black and the vehicles' outline pass comes off.** `cel_outline.tres`'s own-hue ink (`ink_from_surface` 1.0) gives way to `ink_colour` at the same 1.5 px, reversing `Q158`; the own-hue path sits behind the shader's `SURFACE_INK` define, so the frame's colour copy is no longer made. The screen pass then draws the black line round every vehicle, so `next_pass` is removed; `vehicle_outline.gdshader` and its batching stay as the way back. Start line, same tick: `prims` 988,372 → 709,510 by day, 1,145,639 → 854,323 at night. The one-pass line is a fixed 1.5 px, thins with speed and is gone by 240 m.
- Refused on the same sheets: 2.5 px (lamp posts and sign poles ink solid), half black, a darker own-hue, and a moonlit rim on the vehicles' own pass at night — the screen pass already draws that rim round a car, and at 1 cm the two were not told apart.
- **Amended 2026-11-20, the user's pick from a sheet of 1 / 0.5 / 0 on the bus and the tram: the glazing takes none of the crown** (`glass_crown` 0.0). Flush panes leaned with the paint, so a flank and its windows reflected as one sheet. Flat, each pane breaks from its hull; one faced squarely mirrors the road and reads near black. Every vehicle's glass; lamps keep the crown. 1.0 is the way back.
- Next, planned not built: façade glass a step glossier; the handset's cost of the screen pass (`Q158`) now carries the vehicles' line too.

## `Q251` — The wheel is spun or slid, the player's pick, spin by default; the controls stand fixed by default

**Status.** Built 2026-11-18 on the user's ask ("make the wheel explicit about spin vs slide no matter the position mode, make spin default"; "static control position"); supersedes `Q243`, amends `Q239`'s default. The handset drive owed.

- CONTROLS' 方向盤 is 轉動 (SPIN) or 滑動 (SLIDE), on the pause's too: `ControlOptions.wheel`,
  `--touch-wheel=spin|slide`, `drive.sh` names spin. 操控位置 now defaults to 固定 (FIXED).
- Spun and relative: the thumb's angle round the wheel's middle over `spin_lock_deg` (180°), from
  twelve o'clock where it landed, added to the wheel it found; the rim keeps up with the finger.
  A move through the hub turns nothing.
- Spun and fixed (the user's follow-up: "push/pull the wheel all the way and back just via
  vertical movement" left of the control): a PUSH. The landing fixes the way the rim moves
  clockwise under the thumb (`InputRouter.push_along`: up on the wheel's left, right along its
  top, a slide's on the hub); the stroke's length along it turns the wheel from where it was,
  `push_travel_px` (242, pi x `wheel_radius_px`: the rim moves with the thumb) to full lock. An
  absolute angle (built first) jumped the wheel on landing and could not reach lock by a vertical
  stroke. Fixed used to be slide-only.
- The push at a slide's 140 was too quick even on GENTLE (the user, from the handset): the drawn
  rim ran 1.7x ahead of the thumb. Raise `push_travel_px` for a slower push.
- And a thumb going round the wheel could not turn it (the user): the straight push folds back
  on itself round a circle. The fixed wheel also sums each move's length along the rim where the
  thumb is, and takes whichever of the two has gone further.
- And a steady circle did not turn the wheel at the finger's pace (the user): the drawn wheel took
  the steering's curve, so it crept then raced, and a length round the hub runs fast on a wide
  circle and slow on a tight one. The wheel is drawn at its position (`wheel_position`), the curve
  left to the steering alone, as a variable-ratio rack; the way round is its ANGLE as a length on
  the drawn rim (x `wheel_radius_px` / reach), a length only within `round_floor_px` (40) where an
  angle jumps. Half a circle of any size outside that is full lock. A thumb landed outside the rim
  has its straight push scaled the same way (x `wheel_radius_px` / its reach): unscaled, a circle
  twice the rim's size ran the wheel at up to twice the finger's pace while the push read the
  larger. Inside the rim the push is the thumb's own length, so the stroke up the wheel's left
  still reaches lock. The user's pick over "own length always": a thumb landed left of the wheel
  needs a longer stroke for lock (2x at twice the rim's reach). A straight vertical stroke cannot reach lock going round (at the rim it
  sweeps under 90°), so neither reading alone serves both gestures.
- Slid: the sideways offset alone, at any height (`Q243`'s slide without its spin).
- Each wheel has its own two: slid, `steer_travel_px` and `steer_curve`; spun, `spin_lock_deg`
  (`push_travel_px` fixed) and `spin_curve` (2026-11-18, the user: "lets try spinning to be raw
  input instead of easing"). `spin_curve` 1.0: the steering is the wheel's position, as drawn.
  STEERING RESPONSE's three curves are the slide's; a spun wheel reads `spin_curve` under any pick,
  so CONTROLS hides the row while SPIN is picked (the user: "hide steering response when spin is
  picked").
- Gone: `spin_enter_deg` and the slide bias. The frame cap was already 60 by default on a phone
  (`Settings.FRAME_CAPS[0]`, `Q223`); a desk stays uncapped.

## `Q252` — The far shore is floodlit at night, like Wan Chai at its level of detail

**Status.** 🟡 Built 2026-11-18 (`P3-100`) on the user's ask ("can the kowloon light up like current wanchai in a low lod way at night?"); 🔁 reverses `Q249`'s dark night skyline. Strength 0.55, the user's pick from frames (0 / 0.35 / 0.55 / 1.0 / 2.0, and 0.55 with a 300 m reach). Owed: the handset at night.

- `backdrop.gdshader` alone; no data, no schema. At night a share of the walls take one wash of their own colour, `night_spot_strength` at the foot dimming to `night_spot_top` by `night_spot_reach_m` — Wan Chai's floodlights (`Q160`, `city_facade.tres`: 0.55, share 0.6, reach 120 m, top 0.3) without the 14 m cones, which are under a pixel across the harbour and would shimmer. Walls only; roofs, the sea and by day draw nothing. Scaled by `night_lights`.
- **Per wall, not per building**: `backdrop.glb` carries no building, so the draw hashes the wall's plane (its bearing to the degree, its offset to the metre). From 600 m a block shows one or two walls. A per-building seed would be `COLOR_0` alpha on the skyline (the far sea holds 0), an ETL change through `meshbuild.prism`; not built.
- Decided per vertex into a `flat` varying: every face has its own vertices and one normal (`ColouredBuilder.polygon`). Per fragment, a wall whose offset lies near a metre's half could split where rounding crossed it (read in review, not seen in a frame).
- Cost: Expo Drive East at `--time-of-day=1.0`, 0 against 0.55: `prims` 451,593 and `draws` 70 both, no geometry added.
- ⚠️ Under `gl_compatibility` (the web build) night emission is far fainter — Wan Chai's floodlights too, the same frame pair on Hennessy Road — so the far shore reads near dark there, as the city does. Not this change's; no shader error.

## `Q253` — A run is saved as it is played, and HOME offers CONTINUE

**Status.** 🟡 Built 2026-11-18 (`P6-2`) on the user's ask ("allow user to resume a session when the app is killed or it is explicitly quit via pause menu"). The three picks are the user's: restore the fare aboard, CONTINUE on HOME, a free drive's END still opens REPORT. Owed: the handset kill-and-resume.

- One slot, `user://run.cfg` (`RunSave`), beside `settings.cfg` and never in it: PLAY clears it, 交更 clears it, END keeps it.
- Saved: the mode, `DayClock.elapsed_s`, the car's transform, and `FareSystem.snapshot` — the books, the tally, and a passenger CARRYING with meter, clock, tip and receipt. Not saved: traffic, trams, the waiting customers (the city's, as `reset` keeps them), a slide or a combo in progress.
- Written as the pause opens (the app losing the screen and END pass through it), as the window closes, at every boarding, delivery and walk-off, and every `menu.tres` `autosave_s` (30) game seconds against a kill with no notice. Never for a scripted run (`Main._records_run`, `_bank_tally`'s gate).
- **Banked before it is written**, so a resumed tally is already in the lifetime record (`SessionTally.from_dict` sets its baseline) and a resume never counts a run twice.
- A passenger walking to the car is seated at their kerb, hailed again by the next stop: nothing was on their meter. A fare whose stop no longer resolves resumes the books with nobody aboard. A save over other resident regions is refused and removed: its pose is in another frame.
- A shift saved past 交更 with its last passenger aboard closes again on its first tick; nothing special-cased.
- No confirmation when PLAY replaces a save: picking a new run is the choice.
- CONTINUE and PLAY share PLAY's row as two half-width choices, the run's line under them: HOME grows up from the bottom, and a whole row for CONTINUE pushed the title off a 1368x630 handset.

## `Q254` — A Star Ferry is moored at Wan Chai Ferry Pier and rocks on its own swell

**Status.** 🟡 Built 2026-11-18 (`P3-102`) on the user's ask ("a star ferry parked near wanchai pier that move slightly according to wave"; Wan Chai alone, his call). Remodelled the same day from his photos of the fleet at the piers (alongside, not end-on as first assumed). Owed: his look at the remodel and the amplitude pick, the PCK, a night frame (the windows are not lit).

- **Through the landmark door, not a new stage.** `star_ferry.glb` is authored by `tools/make_landmark.py` (`StarFerry`, 2,246 triangles, its own collider) and placed by the `landmarks:` block. It replaces nothing (`P5-10`).
- **Flat vertex colour on `landmarks.tres`, not the vehicle shader.** `vehicle_body.gdshader` is sized to a car: crown over 3 m, `INK_SPAN_M` 16 m "longer than any vehicle", per-car instance uniforms. A 35 m hull would need each one reopened.
- **Size**: Electric Star's 116 x 28 ft, 35.4 x 8.5 m, the fleet's common size (World Star 46 m and Golden Star 47 m are the exceptions).
- **Look, from the user's photos**: a green hull to a bulwark at the main deck over red antifouling at the waterline, a black rubbing strake and tyres over the side; the main deck open between green posts, its teak set back 1.2 m so the upper deck's overhang shades it; a green band; a white upper saloon with rounded ends, a row of life rings under its windows; a white roof, a black-topped funnel amidships, a mast and crosstree at each end. No name, lettering or star (`Q42`). Refused: the first model's wheelhouse boxes on the roof, which no photo shows. A ring has no wall inside its hole (a pixel from the chase camera, a third of its triangles). The collider is still the drawn mesh, as every landmark's is: a hull-only `-colonly` shell would save Jolt nothing it pays for, a static trimesh costing nothing until touched.
- **Placement, from iB1000 11-SW-10C**: the pier is block 1810133737 (BUILDINGNAME 1810037446, 灣仔渡輪碼頭), a 27 m finger whose west face bears 353.9°. The hull lies alongside that face, as the fleet berths in the photos, its seaward end at the pier's corner, 0.5 m of water off the strake: E 836180.76, N 816072.47.
- **`afloat`** (`landmarks.json` still schema 2): an afloat entry authors no elevation; the config puts it at `basemap.water_level_m`, so the sea level keeps one home (hard rule 3). Refused: an authored elevation, a mesh-sourced hero afloat, an afloat entry with no basemap.
- **The motion is its own swell, not the water shader's chop.** The chop's 6 m crests average to almost nothing over 35 m. `moored.gd` sums three sines on `moored.tres`: heave 0.08 m at 5.3 s, roll 1.2° at 6.7 s, pitch 0.35° at 4.1 s — a mast top moves ~20 cm. It runs through a pause, as the water's `TIME` does. Visual only: `moored.gd` lifts the model's static body out of the hull onto itself, so the collider stays at rest and Jolt is never handed a moving static body.
- `verify_landmarks.gd` holds an afloat entry to the basemap's water level (2 mm), the heave to within 95–100% of `heave_m`, and the hull's bottom under the water at the worst pose over 120 s. Each check mutation-checked: no heave, the hull lifted 2 m, the document's y at 2.3 m.
- **Culling** (the user's question): an ordinary `MeshInstance3D`, so the engine's frustum culling is the whole of it. Preview A/B with the entry removed from the synced bundle: facing it from the water +6,738 primitives and +2 draws (colour and shadow); facing away +0 and +0. Not occlusion-culled: from the street behind the pier, the first model, hidden in the frame, still cost +696 and +2 — the pier's own occluder does not cover it. The drive camera's 400 m far plane culls it past that.

## `Q255` — The wheel's arrow lights on the side it turns, and the touch controls light from any input

**Status.** 🟡 Built 2026-11-18 (`P2-4`) on the user's ask ("can the wheel arrows light up when turning to that direction, like throttle does?"; "even when it is controlled via keyboard/other input, but when a touch ui is also shown"). Owed: his look on a handset.

- The wheel's arrow on the side `InputRouter.steer` points is drawn in `HudStyle.touch_turn`, the dial needle's amber at 0.9: a car's indicator, and neither the pedals' green nor their red. `verify_hud` holds it amber.
- The pedals' levels and arrows, and the lever's handle, read `accelerate - brake_reverse` from any input, no longer only under a driving thumb. The arrows read `steer`, which a key, a pad and a thumb all write.
- The wheel itself still turns only under a thumb: `wheel_position()` is the thumb's wheel (`Q238`), and a key leaves it centred.

## `Q256` — Anonymous usage events go to PostHog, the game's one runtime network call

**Status.** 🟡 Built 2026-11-18 (`P6-3`) on the user's ask (analytics "with minimal data permission, and proper settings for ios/android/web", the official PostHog Godot SDK, his project token). Reverses hard rule 2's "zero network calls at runtime" for this alone; the online leaderboard refused under `Q162` stays out. Owed: a played run's own events seen in PostHog, a device run per store build, the store forms, the PCK.

- **The SDK is vendored, not fetched**: `game/addons/posthog/` is the 0.1.4 release zip (SHA256SUMS checked), MIT, pure GDScript, no native code. It passes gdformat and the warnings sweep unedited (`exclude_addons`). Its licence is read into ENGINE NOTICES at runtime (`EngineNotices.ADDONS`) and named in the credits; `include_filter` puts the file in every PCK.
- **One door**: `Analytics` (static, `scripts/core/`) is the only caller of the `PostHog` autoload. Not an autoload itself: a `--script` tool compiles `StartMenu` with no autoload names in scope, and the first build broke `verify_menu` that way.
- **Only a player's run sends**: `Main` calls `Analytics.start()` under `_records_run()`; an editor build (every `drive.sh`, verify tool and editor play) never sends without `--analytics=on`, and `--analytics=off` stops any build. The config is not `posthog/config`, which would set the SDK up in its own `_ready` before `Main` decides.
- **Minimal data**: `person_profiles` NEVER (no `identify`), no feature flags (no flag request, no device properties for one), no exception capture (a Godot error can carry a path holding the OS user name), IP discarded server-side (`anonymize_ips`, set 2026-11-18). Events carry numbers, enums and flags only: `run_started`, `fare_delivered` / `fare_bailed`, `run_ended`, plus the SDK's lifecycle four. The SDK still adds `$os`, `$device_model`, `$locale`, screen size and a random per-install ID.
- **Consent**: on by default with PRIVACY → SEND ANONYMOUS USAGE STATS on the boot menu (`Settings.analytics_on`, the one source; pushed onto the SDK's own). Off clears the unsent queue. The user's pick between default-on and opt-in was put to him and not answered; default-on is the recommendation he was given, and the switch's default is one line.
- **Region**: US (`us.i.posthog.com`), because the project was created there and a token works only on its own region's host.
- **Platforms**: Android `permissions/internet` on (install-time, no dialog). iOS and macOS privacy manifests declare Product Interaction, not linked, not tracking, purpose Analytics (bit `1`, read off the 4.7.2 binary's list order); `tracking_enabled` stays off, so no ATT prompt. Web: nothing; ad blockers will drop some events, and a reverse proxy is deferred.
- `verify_menu` holds the PRIVACY switch's save both ways and the add-on's licence carried whole; each mutation-checked (the setter forced true; the notice cut to 40 characters).
- Live 2026-11-18: an editor boot with `--analytics=on` delivered `Application Installed` / `Opened` / `Backgrounded` to project 746655; `$process_person_profile` false. Those four predate `anonymize_ips` and carry an IP.

## `Q257` — An off-grade edge with no structure under it is drawn between the roads at its ends

**Status.** Closed 2026-11-19 (`pipeline/roads.py::_bridge_uncovered`) on the user's report from
the drive (a Moreton Terrace road that "becomes a disconnected huge slope spike").

- `_deck_heights` puts an off-grade edge the structure covers nowhere on the level's flat offset.
  Causeway Bay's TAI HANG ROAD `e57` / `e59` are labelled level 1, have nothing under them, and run
  from MORETON TERRACE FLYOVER's end (12.0 m) to the at-grade street (13.3 m); the offset drew them
  at 16.3-19.3 m, a slab 4.3-6.0 m up at both ends.
- Rule: each end targets the highest end at that node of an edge whose height was measured (never
  another uncovered edge); with both targets, the ribbon is linear between them along the plan.
  Refused over `deck.touchdown_max_grade_pct`, as `_descend` refuses. One end open keeps the offset:
  `ISLAND EASTERN CORRIDOR`'s stub `e425` (Wan Chai) is unchanged.
- Measured: Causeway Bay 2 uncovered, 2 bridged; nodes 73 / 76 17.68 / 16.29 → 12.02 m;
  `touchdown_error` steps at node 69 +6.00 → +0.00. Wan Chai: 1 uncovered, 0 bridged, roadgraph
  byte-identical.

## `Q258` — A traffic car is drawn pitched on the road's grade

**Status.** Built 2026-11-19 on the user's report from the drive (traffic "horizontal when moving
up or down a slope"). Desk-checked; the user's drive owed.

- `Car.pitch` is the grade between the car's axle stations on its edge (`car.s ± half_length`,
  `RoadGraph.point_at`), or ±0.05 of its turn's curve, recomputed only when it moves along.
  `drawn_pose` tilts the body, the instance and the beam about the car's own right.
- Drawn only, as `Q244`'s steer: `car.pose` stays upright, so every rule that reads a heading or a
  centre is untouched and the seeded drives (`drive0`–`drive5`, `hours`) are byte-identical on both
  regions. A knock folds the steer into the pose but not the pitch: `_centre_of` reads the upright
  pose, and folding it moved the push's centre and spun a car pushed through its middle.
- Trams stay level: the tram line is flat by the user's word, and a grade on it would be noise.
- Deciding number: on the steepest road by its ends, `e335` (Wan Chai, 16.5 %) and `e21` (Causeway
  Bay, 14.5 %), the nose reads ±0.163 / ±0.143, opposite each way. Mutation caught: the sign.

## `Q259` — An exception lives at its own code and in a test, never in a list

**Status.** Closed 2026-11-19 on the user's instruction ("we really dont want a list of exceptions
like this"). `CLAUDE.md`'s "Deliberately NOT consistent" and "Deliberately DUPLICATED" bullets are
gone.

- Each of the twelve entries was checked against the code. One was never an inconsistency
  (`min_station_gap_m` beside `fold_tolerance_deg`: two bars for two degeneracies, `railings`),
  one is gone (the lamps' unreversed ring beside the signs' reversed one: both are
  `meshbuild.strut` now), and the rest stand, each held where it lives.
- Held by a test: the four grader copies (`carriageway_margin.py`, `carriageway_region.py`, the
  arrows' row reader, `skidpad_ablation.gd`) by `test_grader_copies.py`, which fails on the
  forbidden import; the railings' unconditional push (`Q78`) by a zigzag survey that must draw one
  straight fence; the winding signs, the station normals and the wrong-way monitor's two bars and
  miss rule by the tests that already pinned them.
- Held by the code's own docstring and its rule file: `opposed_pair_bearing_deg` beside
  `pair_bearing_tolerance_deg` (`surface`), `_Ribbon`'s scalar filter (`surface`, 34 ms against
  395 ms).
- Two citations were wrong: the winding signs are not `Q59` (arrows) but `ARCHITECTURE.md`'s
  drawn-layers note; the row readers' rule is `Q126`, not `Q94`.
- Deciding number: every new guard fails on its mutation — five forbidden imports or calls (a
  mention in a comment passes), a per-sample outward-only push, a `+X` pole seed.

## `Q260` — Signboards come from the Buildings Department's register, coloured from their photos

**Status.** 🟡 Steps 1–3 built 2026-11-19 (`P3-103`) on the user's plan: coloured boards, the
colour surveyed, generic trade names, then the screens. Owed: the user's look day and night, the
handset, the screens' heights. Canopies are a later task. Canopies come later and apart. Checklist in
`.claude/rules/signboards.md`.

- **Source.** BD's Legal / Validated Signboards (`bd_rcd_1629267205232_53467`, `BDLSMW`): a point,
  a type, a size in metres, the street it faces and a photo PDF. Registered boards only, so it is a
  lower bound. No owner and no trade name, and none is invented from elsewhere: a text face will be
  generic and seeded per `OBJECTID`.
- **Placed on the shipped walls**, not on the footprints: the nearest wall triangle within
  `max_snap_m` 4.0, pulled toward the street named in `FACING` by `facing_weight_m` 2.0 (cost =
  distance + weight × (1 − cos)). Wan Chai: 2,031 of 2,038 drawn, snap p50 0.27 m / p90 0.98 m,
  613 turned to their named street, 84 naming a street the graph does not carry. Causeway Bay: 131
  of 132.
- **Heights are authored by type** (`mounts:` `base_m`): wall 3.0 m, blade 3.5 m, roof on the
  wall's top, the canopy type 2.6 m. Boards on one wall that overlap stack 0.3 m apart (447). A
  blade over the drawn carriageway is raised to 5.5 m above the ground (64), clear of a
  double-decker's 4.4 m. Missing sizes take the type's median (370); none collides.
- **Colour from the photo.** Most photos outline the board in red vector strokes. Reading them
  out of the PDF (`pypdfium2`, already a dependency; PyMuPDF refused as AGPL) and taking the
  dominant Lab k-means colour inside measures 3,455 of 3,883 boards across the four driven
  regions. A board with no outline, or a winner under `survey_min_share` 0.25, takes a palette
  pick seeded by its ID. Lightness clamped to 12–90 so a blown-out photo is not drawn white.
  Wan Chai: 1,768 surveyed, 263 palette.
- **Lit at night** by the rig's `night_lights` (`Q160`): the two faces carry `COLOR_0` alpha 0 (the
  lantern convention) and emit their own colour × `face_glow` 1.5; the edges are darkened 45% and
  never glow. Nothing lights by day.
- The palette is the third colour authored outside `materials:` (after `signs.colours` and the
  signal heads): a board is a printed ground, not cladding, and each board is its own colour in
  one draw call.
- Cost: Hennessy Road's street viewpoint 621,329 → 633,497 primitives, 108 → 113 draws; the
  throttle route +5–8 k primitives and +6 draws. Web PCK 107,918,012 → 108,498,072 bytes
  (+580,060, 0.5%). `city.json` schema 53.
- ⚠️ A brand's colour comes through the survey (`LICENSING.md` item 6). The photos are the
  applicant's in part; only one colour a board leaves the build machine.
- **Step 2, the lettering: generic, never real.** Two picks from 32 auspicious characters and a
  trade's suffix (`金興茶餐廳`), seeded by the board's id. The trade is weighted by mount (a pawn's
  `大押` only on a blade, a group's name only on a roof), by a FEHD restaurant licence within 15 m
  (food ×8 there, ×0.25 elsewhere; 959 of Wan Chai's 2,031 boards are near one) and by street
  (Lockhart Road's bars, authored). FEHD's data names each licensee; only the position is read.
- Set in the committed brush subset (`TaxiAceBrush-Medium`, +54 KB for the 95 characters), one
  coverage cell a character in a 512 × 1024 atlas, its own primitive a cell on
  `signboards_text.gdshader`: the ink rides `COLOR_0` (the one of four with the most WCAG
  contrast against the board), an alpha scissor cuts the glyph, and it burns at night with its
  board. A board taller than 1.3 × its width is lettered top to bottom; a blade on both faces.
- Cost: the street viewpoint 633,497 → 641,767 primitives, 113 → 118 draws; Wan Chai's 20,120
  lettering triangles; web PCK 108,498,072 → 109,316,536 bytes (+818,464, the atlas, the
  lettering and both fonts' new characters); `city.json` schema 54 for the atlas key. FEHD joins
  the credits.
- ⚠️ Owed: the atlas imports with no mipmaps (as the signs' does), so a far glyph can shimmer
  under the scissor; and each region ships its own identical atlas (70 KB, 0.5 MP of memory).
- **Step 3, the screens: authored, generic.** The register does not say which board is a screen, so
  `screens:` names two by `OBJECTID`: 2297, East Point Centre's 73.45 × 20.7 m board over Hennessy
  Road, and 1934, the 12 × 11.32 m board facing Russell Street at Times Square (a candidate, the
  user's to confirm). Each is drawn as a quad on its lit face with UVs in metres, its own primitive
  on `signboards_screen.gdshader`: a drifting colour field cut to a new slide every 7 s, seen
  through a 0.3 m LED grid that fades where an LED is under a pixel. No texture, no brand. It emits
  by day (1.2) and more at night (2.2). A screen is not lettered.
- **The lettering is off (2026-11-20), on the user's call**: the boards ship colour only.
  `text.lettered: false` drops the names and the atlas; the `text:` block stays validated and its
  characters stay in the brush subset, so one line turns it back on. The screens are unaffected.
- **The screens show plain blue (2026-11-20), on the user's call**: `plain` in
  `signboards_screen.tres` holds every screen on `plain_colour` through the same LED grid and glow;
  the loop stays in the shader for when it is switched off.
- ⚠️ A screen's height is a wall board's authored 3 m base, so Times Square's sits at street level
  where the real one stands higher up the façade. A per-screen base is owed with the user's pick.
- **Neon at night (2026-11-22), on the user's ask: a tube round the face, the face keeping its
  colour.** Every board but a screen carries one quad per lit face, `neon_lift_m` 0.03 off it, its
  own primitive on `signboards_neon.gdshader`, which cuts it to a rounded tube 0.15 m in from the
  rim and draws nothing by day. The tube is the board's colour pushed from grey (`saturation` 5.0)
  and burns at `neon_glow` 3.0. The rig's night switch hides its meshes by day and they cast no
  shadow (`GeneratedLayer.NIGHT_ONLY`), saving 3 draws by day and 2 at night under the HKCEC
  footbridge. A brighter face would not do it: the surveyed colours are muted,
  and at unpushed saturation the tubes burned white. Wan Chai +4,874 triangles in 16 cells.

## `Q261` — A solid pointer hangs over every fare ring

**Status.** 🟡 Built 2026-11-20 (`P3-104`) on the user's ask; the size and height are first guesses
for his pick from frames. Extends `Q142`'s guide, reopens nothing.

- A flat ring on the road is lost a block or two out. Over every ring — the destination's and each
  pending customer's — `fare_guide.gd` hangs a four-sided spike, tip down, in the ring's own
  colour (distance colour for the destination, `pending_colour` for the waiting); withheld pickups
  get none, as they get no ring.
- Opaque and unshaded, each face's shade baked as a vertex colour, so it reads as a solid at any
  hour without the rig. Drawn as one mesh and one multimesh beside the rings'.
- Its numbers are `guide.tres`'s `pointer_*`: 3.0 m from ring to tip, 2.0 × 1.4 m, a 0.4 m bob
  that never sinks below the height, one turn in 4 s.

## `Q262` — Road lettering is TD's string in TD's rectangle, in Noto Sans HK, facing the traffic

**Status.** 🟡 Built 2026-11-20 (`P3-21`) on the user's instruction, reversing `Q65`'s refusal.
The face's weight is a first pick (700) for the user's look from frames.

- `DTAD_RD_MARK_ANNO` gives each legend its string, an `Angle` and the rectangle it fills, word
  fragments apart (`CEN`, `TRAL`). `pipeline/roadtext.py` lays each where filed; no word is joined,
  translated or invented.
- `Q65`'s two blockers: **no direction** — `Angle` is right modulo 180 (`FlipAngle` 90 on 465 of
  466), so the letters face the nearest flow (`stopmarks._in_flow_frame`'s rule); **no typeface** —
  Noto Sans HK (OFL), fetched as a source, not committed. TD's faces are sans (`ENGINEERING`,
  `chinese` / 微軟正黑體); Free HK Kai was refused: plates are Kai, road paint is not, and a brush
  hairline vanishes at 28% width.
- `fontTools` becomes an ETL dependency (outlines, weight instancing). Refused: tracing a Pillow
  raster (edges a pixel off) and an alpha decal (leaves `Q68`'s opaque rule).
- The fill is non-zero by winding: the variable face's strokes overlap, and even-odd holes them.
- The sliver bar is authored (`sliver_m` 0.01), not the paint's 2 × `import_quantum_m`: 4.5 cm
  dropped 5,775 of 24,586 pieces (holes in 5 cm strokes); 0 let `split` cut mm slivers onto the
  tunnel portal cap's steep facets, 74 triangles on edge. 1.5 cm: 0 on edge in both regions.
- The rectangle is the text's frame (advances × `hhea` line box), not its ink: `東` and `及` file
  identical 1.34 × 2.82 m rectangles 1.9 m apart, and ink stretched to fill them overlapped the
  next row by half. Set by the frame, letters p50 1.36 m (2.56 stretched).
- Wan Chai: 274 read, 5 on a bore (`A03`), 259 drawn, 10 off axis (two junction mouths where the
  nearest centreline is the crossing road), 0 inverted, letters p50 1.36 m, 24,335 triangles,
  1.84 MB. Causeway Bay: 17 read, 14 drawn, 2 too far, 1 off axis, 722 triangles.
- Refused: re-hosting an off-axis legend on the aligned road (a second host rule on `Segments`);
  destination wording on direction-sign boards (`DTAD_DS_*` publishes the plate, not its words —
  ⚠️ wrong: it publishes the words as line-work, and `Q265` fills them).
- Owed: the user's look and weight pick, the handset's frame time, the PCK.


## `Q263` — A trap written as a warning becomes a check that fails on it

**Status.** Closed 2026-11-21 on the user's go for the pstack-gap plan: each mechanical trap kept
in a memory or a ⚠️ line gets a check, proven by planting the trap, and its warning shrinks to a
pointer. Judgment calls stay as prose. `CLAUDE.md`'s enforcer table lists what is left as text. A
before-side builder script was skipped on the user's call; the battery recipe stays a memory.

- Shaders: `check.sh`'s `shaders` step compiles every `.gdshader` windowed on `mobile` and
  `gl_compatibility` (`compile_shaders.gd`) and fails on `SHADER ERROR`. `--headless` compiles
  none, and a bare `load()` compiled none either. CI has no display and SKIPs, saying so.
  Deciding number: `undefined_symbol_xyz` in `marking_paint.gdshader` passed every step before,
  and now fails exactly the two `shaders` steps.
- Hangs: every `check.sh` Godot run goes through `timeout` (`GODOT_TIMEOUT`, 900 s), and exit 124
  is a FAIL naming the limit. A planted early `return` in `verify_menu`'s `_init` hung the run
  before; at 30 s it now fails `verify_menu` alone.
- Sync: `sync_generated.sh` refuses a list that omits a synced region unless `--drop` comes first.
  `tools/sync_generated.sh wan_chai` on the two-region tree used to delete Causeway Bay; it now
  exits 1 before touching anything.
- Export: `export.sh` names the missing `export_templates/<version>.stable/` before exporting. A
  Godot reporting 4.9.1 or 4.8 now fails at once; 4.7.2 passes.
- Gone, not encoded: the headless import no longer re-tabs `greybox_wanchai.json`. A plain
  import, a forced re-import, an editor run and four `check.sh` runs left it clean, so the
  warning (miscited `Q115`, which is prop placements) is removed rather than guarded.
- Review: `.claude/skills/prove-review` proves a change by running something (a mutation, a battery
  item, a before-side comparison, a frame), drops any finding not run, and checks the touched
  comments are still true. pstack's `/no-comments` was evaluated and not adopted: its deletion
  rules remove the measured reasons `CONTRIBUTING.md` keeps beside the code.
- Principle, not a check: attack the premise after two failed fixes on one assumption
  (`CLAUDE.md`).
- Citations: `test_decision_citations.py` holds every backticked `Qnnn` in a tracked text file
  to a `DECISIONS.md` heading (a heading can carry several: `Q2` `Q3` `Q5`). All 6,174 resolve
  today; a planted citation of an unused id, a heading stripped of its ids and `Q3` dropped from
  its heading each fail it. It cannot tell a wrong decision cited from a right one.
- Python mutations: `godot-mutation-check/mutate.sh` (the user's skill repo) reads `SyntaxError`,
  `ImportError` and pytest's collection errors as INVALID and writes no `.pyc`. A syntax-breaking
  mutation of `meshbuild.strut` read KILLED before and reads INVALID now.


## `Q264` — A deck that stops above the street is met by the street, and the step is graded on the drawn road

**Status.** 🟡 Built 2026-11-21 (`P4-3`); the user's drive over nodes 269 and 369 owed.

- Acceptance restated on the user's call: no step over 0.15 m on the drawn road at any node joining
  level 0 to an *open* deck. The 5 level −1 portals step 8 m and stay closed (`Q13`).
- Grader: `tools/node_step.py` walks 15 m either side of each node on `roads.glb`, following the
  surface it is on; open edges are the game's rule read off `city.json`. Following the highest face
  instead read overlapping carriageways as eleven false steps.
- Mechanism: the structure model stops at or before the node 0.3–0.5 m above the street, and the
  deck rides `clearance_m` on it. The deck cannot come down (at node 269 a 10% descent sinks the
  road 0.24 m into its structure), so `roads._land_on_street` raises each street end to the deck
  and falls at `touchdown_max_grade_pct` until it meets its own profile, one vertex inserted;
  a run that cannot land inside its edge is refused, never cut short.
- `surface._landing_groups`: a deck group whose node a street reaches is neither trimmed nor
  capped, as a lone arm is not. Its own level-1 cap was the step at node 175 (0.27 m) and a cap
  reaching down to 5.2 m at node 385 (0.87 m and a hole).
- `clearance.stubs` closes, by publishing it unmeasured, an off-grade edge with no station on
  structure and an end no other road reaches: Wan Chai's `e425` only, 6.0 m over Victoria Park
  Road, which traffic was routed down. Not drawn differently.
- Deciding numbers: Wan Chai 10 of 30 nodes over the bar (worst 0.87 m) → 0 of 29, worst 0.080 m;
  8 street ends raised, max 0.67 m, 0 refused; Causeway Bay 0 → 0. Carve knock-on: `e398`'s carved
  area 172 → 157 m², no grader worse. `touchdown_error` reads node 269 as landed rather than missed.


## `Q265` — TD's gantry boards are filled from their line-work and hung on their beams

**Status.** Shipped 2026-11-21 (`P3-105`) on the user's go: "aa x4 +1 bold cm" for the Chinese,
"Add an authored gantry frame if data supports it", "ship td version".

- `DTAD_DS_PLATE_LINE` draws every direction sign's face — English, Chinese, arrows, shields,
  symbols, panel frames — as a callout beside the road, with its size label under it. Nothing is
  text. `Q262`'s "the plate, not its words" was wrong.
- The fill: parts deduplicated (TD draws each Chinese outline twice: 62 of 125 on G27A); a panel is
  a connected face ≥ `panel_min_m2` of the **noded** line-work (un-noded, G26A's two top plates were
  lost); the rest is the label, dropped. Chinese is closed rings, XOR-filled in raster (TD's
  outlines self-intersect, which GEOS refuses) and dilated `bold_m` 1 cm; English is single strokes,
  drawn `stroke_m` 4 cm; a face of open strokes ≤ `counter_max_m2` is a counter. 64 px/m at 4×
  supersample, LANCZOS down.
- Scale: 4.96 drawing units a metre, measured against the size label on G27A and G26A; not
  published.
- Place: the leader that touches the board ends on a `GS` line (`DTAD_DS_POLE_LINE_C`) — the beam.
  Its middle must be on the drawn level-0 asphalt within `host_max_m` of a level-0 edge; the board
  faces back down that edge's traffic (a `both` edge by the side the beam's middle is on).
- Steel is authored: a 0.6 m beam with its underside 5.1 m over the road, the board on top (G57A in
  Street View), a leg at each end pushed ≤ 4 m off the asphalt to 0.6 m clear, else a cantilever.
  Legs collide (`-colonly`); the boards do not.
- A deck over the beam within the board's height plus `deck_depth_m` 1.0 m moves the gantry along
  its normal to the nearest clear line (≤ `clear_max_push_m`), else `under_deck`. G26A's GS line
  runs the length of a footbridge (walkway 6.8 m, board top 8.8 m): unmoved, its plates stood
  through the deck.
- Wan Chai: 18 gantry boards read, 9 drawn, 5 no leader, 3 off road, 1 under a deck; 3 cleared
  ≤ 0.6 m; 15 legs, 3 cantilevers; atlas 2048 × 1024 (399 KB PNG); 768 + 107 triangles; +3 draws,
  +2.4k prims at G57A (the face casts no shadow; the frame holds the slab). Causeway Bay: 1 read, 0 drawn (no leader).
- Refused: roadsignfactory.hk (a vendor's catalogue, not the government's data, and no licence to
  ship); rewording a stale board to match Street View (the user: ship TD's).
- Owed: the PCK delta, the handset's frame time, the scale on more boards, the 5 leaderless boards.

## `Q266` — Free mode's hour is picked as the drive begins, and on its pause

**Status.** Shipped 2026-11-22 on the user's ask: "set when beginning a new free roam session, and
maybe ingame pause menu… don't put day/night in main menu option", "3 options: day/night shift,
always day, always night".

- PLAY → FREE opens a page of three: DAY TO NIGHT, ALWAYS DAY, ALWAYS NIGHT. Each starts the
  drive; the last pick is saved (`Settings.free_time()`, falling back to the old `day_cycle`
  switch) and focused next time. HOME's OPTIONS no longer carries the hour, so a desk's boot menu
  has no DISPLAY group.
- A free drive's pause offers the same three under OPTIONS → DISPLAY (a desk's free pause now
  lists SOUND and DISPLAY). A shift's pause does not: 特更 always runs the day (`Q162`).
- ALWAYS NIGHT holds the rig at `day_to_night.tres`' `night_at` 1.214 (00:00), written once.
  DAY TO NIGHT picked mid-drive runs on from the look held (`day_at` or `night_at`) through
  `DayClock.day_from_s`, which `RunSave` keeps so CONTINUE does not jump the hour.
- `--day-cycle=night` holds the night for a scripted run.

## `Q267` — Traffic across levels is graded off the graph alone

**Status.** Closed 2026-11-22 · `P4-4` · reopens on a traffic move that is not a `moves_from` arc

Traffic already moved only by `RoadRouter.moves_from` under `Profile.legal()`, which admits every
routable level. Nothing was left to build. What was missing was a witness: `verify_traffic`'s
`graph:` gate asked the same router the cars drive by, so a rule the router dropped passed.

- `_witness_move` / `_witness_way` read each move off `RoadGraph` alone: the shared node, a one-way
  its signed way, no U-turn, no published ban. The drive checks every move; the `checks` part
  (`_check_arcs`) walks every arc the legal profile offers and every ban in reach.
- Deciding numbers: Wan Chai 1,077 routed arcs, 60 off grade, 153 bans in reach, 2 off grade
  (`336→312`, `424→248`); Causeway Bay 314, 9, 23, 0. The signal drives take 12–26 level moves in
  Wan Chai and 15–41 in Causeway Bay (`levels:`); the back-street drive takes none.
- Mutations of `road_router.gd`, the old gate silent on every one: bans dropped where a deck is
  touched (Wan Chai's 2 caught by `_check_arcs`; the drives never pick them), every ban dropped
  (153 / 23), a deck's one-way driven both ways (48 / 8 arcs, thousands of car-ticks in the drives).
- Refused: a ramp-centred seeded drive — the signal drives already reach the decks, and a 2-ban
  population is proved exhaustively, not by a seed's luck.

## `Q268` — An MTR exit is a destination, named by a station table

**Status.** Shipped 2026-11-22 (`P3-106`) on the user's call: "just do mtr, use table".

- Source: iB1000 `RailwayEntrance`, already fetched with the basemap sheets. `TYPEOFENTRANCE` is
  `MTE` on every exit; `ENTRANCENAME` is the letter only (`A1`, `B`, sometimes null). No station
  name is published: `PlaceNameAnno` / `BuildingAnno` carry substations and a PTI, not stations.
- The station is `fares.stations.table`'s: nine stations, bilingual, each at the mean of its own
  exits. An exit takes the one station within `reach_m` 250 m; none or two stops the build. Over
  the four driven regions' 42 exits: own station ≤ 140 m, any other ≥ 403 m. The table lists
  every station within `reach_m` of a driven region (Mong Kok East, 233 m outside `mong_kok`), so
  an exit's nearest station is always in it.
- Named "Causeway Bay Station Exit F1" / "銅鑼灣站F1出口", or "… Station" with no letter; `place` is
  the name, because a passenger names the exit, not the building over it.
- Kind `station_exit`, drop-off only: a passenger is set down at an exit and does not hail at one.
  Snapped like the other published points (level 0, `max_snap_m`), appended after them so no id
  moves. `fares.json` stays schema 1: an older reader skips a kind it does not know.
- `stations.max_snap_m` 25 m, under the groups' 30 m: `verify_join` bars a stop 25 m from where
  the taxi stops, and three Exhibition Centre exits stand 25.5–29.2 m back across a plaza. Every
  other node in the four regions is within 21 m.
- Wan Chai 17 of 20 exits placed (Wan Chai 7, Exhibition Centre 3, Causeway Bay 7), Causeway Bay
  3 (Tin Hau), Mong Kok 14, Sha Tin 4 of 5. The existing 48 / 7 / 28 / 4 nodes and every street
  spot are byte-identical to `HEAD`'s.
- Owed: the user's fares driven to an exit.

## `Q269` — An MTR exit wears a portal in its station's colour on the wall the 3D map draws there

**Status.** Built 2026-11-22 (`P3-107`) on the user's ask, "draw mtr exits with signs and station
theme colors according to model", reshaped the same day after three street entrances the user sent
(Central D1, Jordan, HKU); the colours are open for the user to correct.

- The model already draws the exit. Against iB1000's footprints, 19 of the four regions' 42 exits
  are their own small block (12–161 m², 2–6 m tall: a stair head), 21 open from a larger
  building and 2 stand beside a podium. So no block is stood: the portal is drawn on the shipped
  tile wall nearest the surveyed exit within `wall_reach_m` 5 m, a wall facing the exit's road
  winning (`facing_weight_m` 6 m > the reach), inside the wall's ends, its fascia under the
  wall's brow, and out past any wall facing its way across its width (a recess the 3D map draws
  out of plane buried Causeway Bay F1 flush). Where no wall is in reach the fascia tops a post;
  none does in the two driven regions (20 of 20 on a wall, the furthest 4.4 m: Wan Chai A3 behind
  its podium's face).
- The portal, after the photos: a black fascia lettered `灣仔站 Wan Chai Station` in white, a grey
  trim under it, a jamb of the station's colour each side of a 2.4 x 2.5 m doorway dark as the
  stairwell, and the exit letter white on blue on a plate beside the door. No MTR logo and no
  word mark: the user's call. The lettering is Noto Sans HK outlines as triangles
  (`roadtext.Face`) on the signs' material: no atlas, no new material, no `city.json` field.
  ~13,300 triangles for Wan Chai's 17.
- The colour is the station table row's `colour`, a name in `signs.colours`. ⚠️ Authored
  estimates: no dataset publishes a station's colour. Mong Kok red is SCMP's (2016), Wan Chai olive
  zh.wikipedia's 橄欖綠; the other seven are guesses.
- `fares.json` gains `exit: {station, letter}` on `station_exit` nodes only, so every other node's
  bytes are unchanged and the schema stays 1: a reader that ignores it is not wrong.
- One library mesh an exit (its letter and station are its own), so one draw call each in the
  game; a frame at a station may add 3–8. Split into a plate a station and a glyph a letter if a
  measurement there says so.
- Owed: the user's look and the colours' correction; the handset's frame time at a station.

## `Q270` — A car stopped part way across lanes keeps only straight on

**Status.** Decided 2026-11-22, on `P3-106`'s rebuilt bundle breaking `verify_traffic` drive3 and
drive4.

- drive3 (seed 7, Wan Chai): a car making for lane 0 and a left turn off e72 was blocked by the car
  beside it at lane 0.248, stood there 26 m, and on the replan kept its turn: `_replan_for_lane`
  took "already in the move's lane" as `same_lane` (under `SAME_LANE` 0.75), so a quarter-lane
  short counted as in lane 0. The turn swung its tail into the straight-on car in lane 1, 0.752
  lanes away (12 car-ticks, one meeting). The replan now keeps a move only when the car stands
  exactly in its lane, so a car stopped between lanes takes straight on from where it is: the
  missed turn the code's own comment promised. drive3 0 meetings after.
- drive4 (seed 23, routed, 08:00) drew no minibus at all: six routed buses for the whole 58 s and
  no wandering minibus at the census's 08:00 share. The livery line rested on a seed's luck, so a
  routed minibus (each minibus stop offered in turn, through `TrafficRouted.try_spawn`) and a
  wandering one (`_redraw` at the first life `kind_for` draws a minibus) are staged after the
  drive. Mutation-checked: each palette swapped fails its own half only.
- The whole `verify_traffic` output before and after the replan, every part in both regions: 12 of
  16 parts move (a replan's rolls move every later car); signalled meetings Wan Chai drive3 1 → 0,
  drive4 (printed, not gated, `Q182`) 2 → 3, every other drive 0 both sides; no other check fails.
- Not a seed swap, and no tuning moved (`signals.md`: never retune to clear an overlap).
