# Art Design

## Direction

**Low-poly, flat-shaded, saturated. Accurate city, toy vehicles.**

| | Treatment | Why |
|---|---|---|
| **City** | Accurate proportions, real massing, real street widths (then widened for play) | Recognition is the product; stylised proportions destroy it |
| **Vehicles** | Choro-Q / toy proportions — short wheelbase, oversized wheels, chunky | Charm and readability. Cars are what the player looks at for hours |

Stylise the actors, not the stage. `Q8` measured it: driving the real city was judged fun on
recognition alone.

---

## Why the art style and the data choice are the same decision

The source data — 3D Visualisation Map (non-textured) and iB1000 — is extruded footprints with no
textures, which is already a flat-shaded low-poly building.

- No texture atlas packing, no KTX2 transcoding, no texture memory pressure.
- Untextured vertex-coloured meshes **merge into one mesh per tile**, which keeps draw calls under
  the 150 budget (`PROGRESS.md` owns the figure).
- ⚠️ Godot's import-time mesh quantisation is OFF project-wide (`Q82`, +958,720 B of PCK): it
  corrupted the ETL's exact geometry.

⚠️ The bundle is not literally image-free: one 512 x 256 atlas ships, the GIVE WAY and STOP plate
lettering (`P3-20`, `Q68`). It is its own primitive with its own material, so `merge` is untouched.
"No textures" is a declaration check: `mesh_contract.gd` admits an image only where a call site
names a pixel budget, and `PROGRESS.md`'s `Texture memory` carries the ceiling (`Q63`).

---

## Palette

### The rule (`Q33`)

Every authored colour is a real material's diffuse albedo, declares the published range it comes
from, and `config.py` refuses to load one that fails. `reflectance:` is evidence; exposure is art
direction.

The exposure lives in the game, not the config (`Q38`, `P5-28c`): a Godot global shader parameter
`exposure_anchor`, set by `scripts/world/lighting_rig.gd` from an `@export` on `clean_daylight.tscn`
and `golden_hour.tscn` — **0.520 in both**. So `authored` (in `hong_kong.yaml`) and `rendered` (on
screen) are different colours; do not read one as the other.

| material | reflectance | bounds | source | authored | rendered |
|---|---|---|---|---|---|
| `render_warm` | 48.7% | 30–60% | ⚠️ back-derived, not cited | `#c9b79a` | `#968872` |
| `render_pale` | 58.4% | 30–60% | ⚠️ back-derived, not cited | `#d3c8b4` | `#9d9586` |
| `tile_neutral` | 61.5% | 45–65% | ⚠️ back-derived, not cited | `#cfcfc1` | `#9a9a90` |
| `render_cool` | 59.9% | 30–60% | ⚠️ back-derived, not cited | `#c5cdc8` | `#939995` |
| `panel_grey` | 55.2% | 45–60% | ⚠️ back-derived, not cited | `#bfc5c5` | `#8e9393` |
| `concrete_kerb` | 25.0% | 20–30% | weathered concrete, 20–30% | `#8d897d` | `#68655c` |
| `concrete_sooty` | 22.0% | 20–30% | weathered + sooty concrete | `#84817b` | `#615f5a` |
| `concrete_paving` | 20.0% | 20–30% | weathered concrete, grubby end of 20–30% | `#817b6f` | `#5f5a51` |
| `asphalt_aged` | 10.0% | 7–12% | aged urban asphalt, 7–12% | `#5b5854` | `#42403d` |

- ⚠️ The five façade materials are the soft entries: their reflectance is what the shipped colour
  claims, 49–62%, the top of what painted render and ceramic tile do. If that is wrong every other
  colour moves.
- 🔴 `bounds: [lo, hi]` is what grades an entry. Un-baked, colour and reflectance are the same
  number, so comparing them only catches a colour edited without its number. **Correct a colour
  that falls outside its bounds; never widen the bounds** (`P5-28a` moved `render_cool` one 8-bit
  code from 60.1% to 59.9%).
- ⚠️ The five façade names are one material family at five lightnesses (`Q34`). Do not rename
  `panel_grey` to anything glazed — 55.2% contradicts curtain-wall glass's 8–15% diffuse albedo.

### Material is not a function of height (`Q34`)

A top-level `materials:` table in the city config declares every colour the city ships, and nowhere
else does; `buildings:` and `roads:` reference entries by name. The table above is the
façade/ground/road subset — the config's full set (`panel_pale`, `roof_grey`, `curtain_glass`,
`concrete_pale`, `steel_rail`, `galvanised_steel`, …) is the authority.

- `colour` and `reflectance` must not be fields on `height_bands`: that makes the schema assert
  material is a function of height. Measured on the 2,171-building photo survey, height explains
  **0.9% of façade `L*`** and 0.7% of `a*`; the best geometric key reaches 1.4%.
- Five clusters on measured hue capture **72.4%** of hue variance. A surveyed building draws its
  material from a distribution selected by its measured chroma and hue angle, seeded from its LandsD
  id; an unsurveyed one takes the height ramp, which is a *lightness* ramp only.
- ⚠️ That buys lightness conditioned on hue and no more: `with_hue` replaces `a*`/`b*` afterwards,
  so the drawn material's own chroma never reaches the screen.
- ⚠️ Not spatial coherence: neighbours draw independently (only 0.5% of hue variance lies between
  the survey's six sheets). That is `Q35`; grade it from the street, not the skyline.
- Each bin's weights are authored so its expected reflectance matches what the height ramp gave the
  same population. `tools/ring_weights.py` derives them and must be re-run whenever the ramp or the
  survey moves (`Q34′`).
- `_check_reflectance` loops over `materials:` and is total only because the table is. Two checks
  hold that: `_check_every_material_is_used` at load, and
  `test_no_colour_escapes_the_materials_table`, which fails when a `#rrggbb`-shaped value appears outside `materials:`.

### Anchor colours

| Role | Colour family | Notes |
|---|---|---|
| Building base | Warm off-white, beige, pale grey-green | HK tenement and podium concrete |
| Building accent | Muted terracotta, jade, faded blue | Older Wan Chai stock |
| Road surface | Dark warm grey | Not blue-grey; HK asphalt reads warm |
| Road markings | Bright white, saturated yellow | Yellow box junctions are iconic |
| **Player taxi** | **Red** with silver roof | HK Island urban taxi. Non-negotiable |
| Minibus | Cream body, **green** roof | Green minibus |
| Tram | Green and white | Instantly recognisable silhouette |
| Neon | Saturated magenta, cyan, gold — emissive | Sparingly; accent only |
| Vegetation | Deep saturated green | HK street trees are dark and dense |

**Time of day: golden hour by default**; night (neon-forward) is a later variant. A time of day is
one number in one rig scene (`Q38`). What blocks night is `Q26` (look unchosen) and `Q82`'s refusal
of the lit lantern — `lit_window_share` ships 0.0 and the emissive channel is a reserved uniform.

🔴 **The table is the authored palette, not the shipped one.** The five `height_bands` honour it
(`C*` 1.76–13.83 rendered), but `facade_hue.strength` multiplies each building's measured chroma on
top. `tools/facade_chroma.py`, 2,177 surveyed buildings passing `vegetation_max`:

| `facade_hue.strength` | `C*` mean | median | p90 | p99 | max | under `C*` 8 | over `C*` 20 | outside sRGB |
|---|---|---|---|---|---|---|---|---|
| 1.0 (faithful) | 6.24 | 4.93 | 12.33 | 24.57 | 54.07 | 72.8% | 2.3% | 0.5% |
| 2.0 | 12.29 | 9.90 | 24.37 | 44.25 | 79.14 | 39.9% | 16.6% | 2.6% |
| **3.0 (ships)** | **17.97** | **14.86** | **34.97** | **64.64** | **82.32** | **24.8%** | **35.2%** | **7.8%** |

- The user chose 3.0 on a sweep (`P5-28d`). ⚠️ It is not a restoration: 2.5 reproduced the
  pre-un-bake distribution (p50 12.38 against 12.25) and was not taken. One façade in three exceeds
  `C*` 20 — the mint, teal, lilac and peach blocks are the palette, not a fault.
- ⚠️ "Too grey or too candy" is not one axis (`Q30`): at 3.0 the city is 24.8% under `C*` 8 and
  35.2% over 20 at once. The middle is missing and no value of this dial fills it — linear chroma
  gain widens the spread faster than it moves the median.
- ⚠️ Accepted costs at 3.0: 7.8% of buildings outside sRGB, and `colour_for`'s uncounted jitter
  clamp fires on 5.50%. `max` saturates at 82.32 from about 2.5 — above that only more buildings
  clip.
- `L*` is flat across the sweep (61.3–61.5): `strength` assigns chroma, not albedo lightness.
  ⚠️ Rendered lightness does move — responding pixels on `street` `|ΔL*|` p90 1.61 at 3.0 — the
  tonemapper following chroma. Whole-frame `L*` holds (43.1 → 42.8 `street`).
- ⚠️ `tools/facade_chroma.py` applies the rig's exposure itself (read from `clean_daylight.tscn`).
  A uniform luminance scale multiplies `C*` by `anchor ** (1/3)` = 0.804; a tool that skipped it
  would report a palette 1.24x more saturated than the screen.
- Re-run the tool whenever `strength` or the survey moves — the two move opposite ends of the
  distribution (`Q37`'s resurvey lifted the median 28.7%, the p99 5.1%). `Q55`'s survey correction
  damaged lightness, not chroma, and barely moved this table.
- Open: whatever look wins should rewrite the anchor table to describe the city that ships (`Q30`).

---

## Buildings

### General fabric (≈95% of buildings)

- Source: extruded footprints, untextured. Vertex colour assigned by ETL from the building's
  material and class. Flat/faceted shading, hard normals. Subtle per-building colour jitter.
- The palette is `etl/config/hong_kong.yaml`'s `materials:`; `buildings:` says which building gets
  which — a measured-hue draw where the survey has a row, otherwise a five-step lightness ramp (warm
  beige low stock → cool pale grey towers). `INFRASTRUCTURE` and ground take flat materials.
- Jitter is seeded from the LandsD id (stable across rebuilds); the material draw uses the same id
  through a separate `blake2b` stream, deliberately uncorrelated.
- ⚠️ Jitter makes a class a *ray* through its base colour, not a value. A tool matching a class by
  colour must test the scale factor, not equality (`tools/deck_error.py` once matched 428 of
  434,149 triangles).
- ⚠️ A minority of towers carry real recessed window reveals and fins in the geometry. At distance
  sub-pixel openings alias into speckle, and LOD1's 4 m cell swallows them. Accept it, or make any
  returning shader grid cover these buildings too. Evidence for `Q26`.

### The window-band shader

A shader draws horizontal banding in world space on vertical faces — floor lines and window rows —
instead of window textures. ⚠️ Off in the shipped look (candidate `C`, below); the payload it reads
ships regardless.

```
Inputs:  face normal, TEXCOORD_0 = (metres along the wall, metres above the building's own base),
                      TEXCOORD_1 = (surface marker + per-object phase, object row)   [P5-11]
Output:  band mask → darkened window rows, occasional lit window (emissive at night)
Cost:    a few instructions, zero texture memory
```

- ⚠️ `TEXCOORD_0.y` is metres above the building's base, never normalised: normalised, a 3-storey
  shophouse and a 40-storey tower get the same number of rows. The channel table in
  `ARCHITECTURE.md` is the contract.
- **Storey height is measured: 2.8 m** (227 walls on 219 buildings of one individualised sheet,
  height-weighted median 2.77 m; read offline and discarded). Column pitch 2.4 m, same method.
- Both inputs come from the ETL: a vertex knows neither where its building starts nor a seed. They
  survive clustering through the representative-selection path that carries colours.
- ⚠️ Not `COLOR_0.a`: the import default sets `vertex_color_use_as_albedo`, so the city goes
  see-through the day a tile enables transparency.
- The bottom couple of metres of every building are darkened in the shader
  (`smoothstep(0, h, UV.y)`), not baked into `COLOR_0` — baking would force `colour_for` to
  materialise a per-vertex array.
- Windows must not appear on roofs or ground-level podium faces — masked by normal and by height.
  Shader: `assets/shaders/city_facade.gdshader`; numbers: `tuning/city_facade_warm.tres`.
  ⚠️ `tuning/city_facade.tres` binds the *clean* shader.

### The clean/futuristic variant

**What ships is candidate `C`** — accurate massing, flat per-building colour, no fabric (`Q26`,
user's call). All three `Q26` looks are files: `city_facade.tres` = `C`,
`city_facade_elements.tres` = `A‴` (elements on; punched openings are glass `Q44`, panes vary per
building `Q45`), `city_facade_warm.tres` = `B`. Switching is a `cp` and a reimport, never a rebuild:
both shaders read the same payload, and `tools/generated_scene_import.gd` maps the ETL's material
name to `tuning/city_facade.tres` only.

- ⚠️ Nothing was faulted in `A‴`; the closure chose between two accepted looks. `A‴` lost its
  surveyed half at `Q102` (`survey_apply`, the vision reader, withdrawn on cost), so the
  `q26_A3_422ee16` frames record a look no file reproduces.
- 🔴 The web round (`P3-9a`) cannot reopen `Q26` (`Q76`): the web build runs Compatibility, which
  crushes the frame (`L*` 10–30 band 27.0% → 0.7%, `C*` p90 14.2 → 8.7). Reopening needs `P3-9`'s
  handset round on the product's renderer.
- `C` is also the reducibility baseline the remaining `P3-7a` steps are proved byte-identical
  against.

`assets/shaders/city_facade_clean.gdshader` answers "dull": the window bands at 2.8 m × 2.4 m are
about four pixels at 30 m, so it moves the unit of variation from the window to the building. The
`.tres` values are the authority, not the shader defaults.

| | `city_facade` | `city_facade_clean` |
|---|---|---|
| Vertical unit | 2.8 m window row | 2.8 m glazing ribbon, doubled on 22% of buildings |
| Horizontal unit | 2.4 m column | 5.5 m structural bay, hashed ×0.72–1.45 per building |
| Per building | rows offset by phase | **treatment** — 38% solid mass, 62% glazed, 22% accented |
| Glass | flat dark mix | fresnel toward a sky colour |
| Distance fade | 90–240 m | 140–244 m |

Three tricks, none a texture: per-building treatment hashed from the `TEXCOORD_1` phase; fresnel
sky reflection (`pow(1 - dot(NORMAL, VIEW), p)`), no probe; grazing sky bounce on solid wall.

Traps, each paid for once:

- **Podium.** `podium_height_m` protects shopfronts from banding but left kerb-to-cornice blank at a
  1.5 m eyeline. The podium gets its own elements: shopfront glazing at 0.7–4.6 m, a cornice, the
  accent on the plinth. Ask of anything added: *is it visible from a car?*
- **Grammar, not phase.** Offsetting one grid leaves one grid. The seed picks a grammar — fin tower,
  curtain wall, punched, ribbon — as one grid with different ratios, not four code paths. Bay and
  band span are hashed per building; only `floor_height_m` is a constant of the city.
- **Glass.** Reflect the sky *gradient* by the reflected ray's elevation (darker below the horizon);
  bow the ray per pane; do not let fresnel fall to nothing head-on. Glass colour sets the value and
  reflection only lifts it — HK curtain wall is body-tinted and dark. Three tints hashed per
  building.
- **Too coarse is worse than too fine.** A 5.6 m band at 52% glass is a 2.9 m black slot and reads
  as a parking deck. One ribbon per storey. A mullion is wall, not a dark line.
- **An opening is not necessarily glass** (`Q43`). One switch for both deleted the windows on 66% of
  wall vertices. Where glazing does not dominate, openings are dark reveals: `recess_colour`, and
  `unglazed_reflect` — ⚠️ not zero, or they read as painted rectangles.
- **`band()` needs analytic antialiasing**, not just `fwidth`: past a quarter period per pixel,
  converge on the band's duty cycle. For geometry too thin to sample (0.1 m hatch, poles) the answer
  is `msaa_3d=2` (4x), `Q91`; `check.sh` pins it.
- **Shopfront** is hashed per building at a varying height with heavy podium piers; unconditional,
  it draws one dark ribbon down a street.
- ⚠️ **"True to site" is unreachable from this data**: no land use, building use or ground-floor
  attribute. Routes if it ever matters, cheapest first: a frontage test against the road graph
  (build-time, no new source); land utilisation data (new dataset, schema bump); `landmarks.json`.
- 🔴 **The fade must finish before the LOD switch.** `tuning/streaming.tres` swaps to LOD1 at 250 m,
  where `TEXCOORD_0.y` comes from a cluster representative and is wrong by up to a storey and a
  half. Shipped fade 140–244 m. Any change to `fade_end_m` must be checked against
  `tier_distances_m`.
- ⚠️ **Do not derive the horizontal coordinate from the face normal** — curved façades shatter into
  per-triangle strips. Project onto a world axis *chosen* by the normal.
- ⚠️ Residual moire round the flyovers is likely not the shader's: `Q20` records that the flyovers
  are drawn twice, and distinct phases reveal the overlap.
- ⚠️ Roofs are excluded from the grid (`upness < wall_normal_max`) but not from the look:
  `roof_darkness` is the whole roof treatment, or a 48° sun clips every roof white.
- ⚠️ "Washed out" was four settings: `tonemap_white`, `ambient_light_energy`, `glow_bloom` (a
  global lift regardless of threshold) and fog. Raise the ceiling, never the floor.
- 💡 `city_preview.tscn` instantiates `road_preview.gd`, which draws the road graph as coloured
  lines and 1,125 direction arrows; they have been mistaken for art. `city_drive.tscn` puts the
  overlay behind `--debug-view`.

### What buildings will *not* get

- **No per-building texture, and no low-res atlas.** The binding reason is `merge`, which refuses
  textured meshes — a textured building becomes its own draw call. UVs are the weaker half: the
  shipped set has none to lose. ⚠️ An unclustered LOD0 does not rescue it: `collapse`'s
  `cell_m <= 0` welds on position and normal, exactly what a UV seam shares, and that tier costs
  30.5 MB and 40% of worst-case visible triangles (`Q16`).
- Colour sampled per building is *not* on this list — buildings get it (below). What stays refused
  is the photographs' `L*`.
- ⚠️ Do not re-author the five height bands from clustered façade colour: height explains 1.2% of
  `a*` and 0.8% of `b*` across 2,214 buildings. The ramp is a lightness ramp, the one thing height
  predicts (10.9%).

### Per-building façade colour

Every building carries its own measured hue, read offline from the individualised set's photo
textures and joined by the building id's stem — 2,214 buildings, 100% matched. It lands in the
`COLOR_0` the tiles already ship: no new attribute, schema change or shader change. An unreadable
atlas falls back to the height band, material included (`Q34`). Switch in `hong_kong.yaml`;
conversion in `etl/pipeline/colour.py`.

- ⚠️ **Hue is taken, lightness refused, on measurement.** `L*` spread *within* one building is 22.9
  mean and 41.1 at p90, against 16.25 between buildings — the sun confound exceeds the signal.
  `facade_hue.strength` scales the chroma and is the stylisation knob, kept separate.
- **`COLOR_0` is authored in sRGB and every consumer must linearise it** — both façade shaders and
  `road_markings.gdshader` (`Q27`). Consumed as linear, 57% of a lit façade pixel's luminance is
  albedo-independent; converted, 6%.
- ⚠️ A washed-out frame is not evidence about the lights. Ambient, exposure, glow, fog, tonemap and
  specular were each ablated and none moved albedo transmission by more than 0.05. Grade a pair of
  renders with `tools/frame_stats.py` and ask whether an albedo change reaches the screen first.

### Hero buildings (~5)

Distinctive silhouettes placed via `landmarks.json`:

| Building | Why | Status |
|---|---|---|
| **HKCEC** | The curved "flying wing" roof | ✅ `P3-6` amendment — the **source mesh itself** (41,273 triangles), extracted by `pipeline/landmarks.py`, sliced at photo-measured ribbon elevations (15 m + k·4.8 m, 1.5 m strips) and vertex-repainted pale panels / dark ribbons under `roof_grey`; 99,577 triangles shipped, generated, never committed. Ribbon strips kept only where the building's own `A0` atlas (build-time only) confirms glazing. Phase 2 only |
| **Central Plaza** | Pyramid crown | ✅ `P3-6` — banded triangular shaft, arcade piers, pyramid, two-stage mast |
| **Hopewell Centre** | Cylindrical tower | ⬜ unscheduled (`P3-6` is 🟡, 2 of ~5 shipped) |
| **Times Square** | Signage identity — massing and placement only, never rendered text (`Q42`) | ⬜ |
| **Wan Chai government slabs** | Grouping needs composition | ⬜ |

- The ETL must exclude the source geometry a hero replaces (`replaces_source_ids`).
- Two budgets, two claims. *Authored*: up to ~8k triangles, a design target (Central Plaza: 300
  against `triangle_budget: 8000`), generated by `tools/make_landmark.py` from surveyed dimensions,
  chamfered, never smoothed. *Mesh-sourced*: a measured regression tripwire pinned per entry in the
  city config and enforced by the stage and `verify_landmarks.gd` (HKCEC 99,577 against 120k).
- ⚠️ Heroes ship vertex-coloured; light texturing is deferred, not refused (user call, `P3-6`).
  Heroes bypass `merge`, so a texture is structurally possible here only — but it is its own
  `DECISIONS.md` record. Hero colours obey `Q33`: mesh-sourced paint names `materials:` entries;
  the authored palette is self-checked by the generator.
- ⚠️ The reason for heroes is not "extrusion flattens them" — the non-textured source carries the
  exact silhouette. Where identity *is* the massing (HKCEC), repaint the source; where it is an
  authored feature the source captures badly (Central Plaza's crown and mast), generate.

---

## Roads

Later layers keep their art direction in their own records: stop/give-way lines (`P3-23`, `Q69`),
signs and lettering (`P3-16`/`P3-20`/`P3-22`), lamp posts (`P3-26`, `Q82` — never a lit lantern,
`Q38`), surveyed road marks (`roadmarks.py`, `Q118`/`Q125`/`Q132`). `marking_paint.gdshader` is
shared by arrows, boxes and stop lines (`Q71`); `signs.gdshader` by signs and lamps.

- **Ribbon**: generated from road-graph polylines, vertex-coloured. **U is a lane coordinate** (0 at
  the nearside kerb, `lanes` at the offside), V is metres along, so dashes keep a real pitch
  whatever the widening. ⚠️ Junction caps carry `(0, 0)` but that does not identify a cap — `U = 0`
  *is* the nearside kerb; a cap says what it is in `TEXCOORD_1` (`ARCHITECTURE.md`).
- **Ribbon shader markings** (`P3-12`, `road_markings.gdshader`, `tuning/road_markings.tres`):
  what it draws now is the kerbside double yellow and the bus-lane edge on the 13 edges the
  `BUS_ONLY_LANE` join reaches. 🔴 `draw_lane_lines`, `draw_centre_line` and `draw_pair_join` are
  0.0 (`Q132`, `Q125`): TD's surveyed lines are drawn as geometry by `roadmarks.py`, and where TD
  surveys none, none is drawn. Do not switch them back on (`road_markings.md`).
- **Junction fade**: a cap overlaps its arms where the junction trim holds a short edge back (6,051
  of 52,985 m² of cap area), so ribbon markings fade out 6 m from a node — also what real lines do.
  ⚠️ Edges are short (drawn length p10 4.0 m, p25 12.5 m): a 9 m fade left 169 of 797 edges bare,
  6 m leaves 121. Judge on the alley grid.
- 🔴 **The kerbside double yellow is invented**, and it asserts *no stopping at any time* on about
  three times the kerb it applies to, taxi stands included. An invented marking is a debit with a
  driver in a way a missing one is not. `draw_double_yellow` reverses it in one line; the source
  that would replace it is `Q54`.
- **Arrows** (`P3-15`, `Q59`): Traffic Aids Drawings v2 publishes them (`DTAD_RD_MARK_SYM_PT`, 1,365
  symbols in region; `Q56`, `Q57`). The ribbon is wider than the carriageway about the same
  centreline, so 97.2% of symbols fall inside it; the published position is read as a *fraction
  across the road*, which picks a drawn lane. `arrows.glb`, own mesh, one draw call, no collider.
- **Box junctions** (`P3-18`): `boxjunctions.glb` from `DTAD_YL_BOX_POLY`'s 20 surveyed polygons —
  border + hatch as lifted geometry (hatch `lift_m` 0.012, below the arrows; border 2 mm above),
  unwidened index-plan widths, one draw call, no collider. Marking yellow is authored a third time
  in `boxjunctions.tres` on `arrows.tres`'s terms (`Q53`).
- ⚠️ **Road text is held on scope** (`Q65`, `Q101`): `DTAD_RD_MARK_ANNO`'s 274 annotations carry no
  instruction the graph does not give the player.
- **Kerbs**: low and mountable, 0.15 m riser and 0.5 m lip. The lip's job is the seam — the ground
  tucks under it, 0.20 m down.
- **Tramway** (`P3-14`): its own mesh, `tram.glb`, two rails and a bed per track at iB1000's
  position; `steel_rail`; dial `tuning/tramway.tres`. ⚠️ What makes it read is `rail_roughness`
  0.28 against the road's 0.95 — judge it at a low sun. ⚠️ `rail_metallic` ships 0.0: the only
  environment is sky, and 0.65 rendered the rails sky blue. A lane-space rail is refused (`Q58`):
  the published rails are on the ribbon in only 18.8% of cross-sections (1.5% on Hennessy).
  `tram_tracks` stays shipped in `TEXCOORD_1` and undecoded.
- **Railings** (`P3-19`, `Q61`): `railings.glb`, one vertical quad per 2 m standing 0.6 m outside
  the drawn carriageway edge, `TEXCOORD_0` = (metres along the run, metres above the deck); the
  shader cuts balusters, posts and two rails out of it.
  - A fence, not a panel: drawn solid it read as a white concrete parapet. It is the bundle's one
    transparent object, so nothing to sort against; `depth_prepass_alpha` removes self-blending; the
    shader *integrates* coverage over each fragment's footprint, so it neither shimmers nor
    vanishes.
  - ⚠️ `ALPHA` is coverage, not translucency — there is no opacity dial and must not be one.
  - ⚠️ `railings.gdshader` is the only `cull_disabled` shader; the back face negates its normal.
  - ⚠️ `rail_metallic` 0.0, for the tramway's reason.
  - ⚠️ `rail_colour` has no second reading to check it against and has been wrong twice (too near
    white; then a green bias). Now 0.64/0.64/0.64, dead neutral — HK street railings are galvanised
    grey. The cool cast is the sky's and is deliberately not in the albedo (a +0.03 blue bias
    doubled B−R from +5.7 to +11.5). Judge at `street` and `kerb`.
  - Mesh vs mask: height, station pitch, outset and sink are mesh (`hong_kong.yaml` `railings:`);
    baluster/post pitch and width and the rail bands are mask (`tuning/railings.tres`). All
    authored — no sheet publishes a railing dimension (`Q60`).
  - ⚠️ The fence stands on the drawn kerb, not where surveyed (`Q60`; re-opened as a measurement by
    `Q101`).
  - Three classes, one shader: `railings` 9,017 m, `bollards` 463 m, `barriers` 935 m, differing
    only in the six mask numbers of `railings.tres`, `bollards.tres`, `barriers.tres`. ⚠️ A class
    handed the wrong `.tres` renders perfectly as the wrong object; `verify_railings.gd` checks the
    dispatch. Bollards are flat masked quads, not round posts. Class colours are authored
    (`COLOR` has no published domain). Three draw calls; separate meshes also let
    `railing_error.py` walk one class.

🔴 **The asphalt is the one colour that was already right.** Against its neighbours (all within 15
`L*`) `L*` 24.5 looked like a hole; against published albedo it claimed 8.2%, inside aged asphalt's
7–12%. A palette judged only on internal consistency always indicts its most extreme member — it
takes an external referent (`Q33`).

The shaded frames stay bimodal with an empty middle (`tools/frame_stats.py`): `kerb` 51.3% of pixels
under `L*` 10 and 2.7% in 10–30; `street` 13.0% and 25.4%.

- 🔴 That is the rig, not the road, and the term is `adjustment_contrast`, not the fill: 1.14 →
  1.00 takes `kerb` from 51.3% to 0.9%. Godot's contrast pivots about mid-grey; the fill is upstream
  of the curve and is re-crushed by it (`Q31`).
- The gap is lit-versus-unlit, not dark albedo. ⚠️ "Under a deck" is not the predictor: `infra`,
  beneath the Canal Road flyover, has the fullest middle of any audit frame (39.6%).
- 🔴 Do not treat the band share as the acceptance test: the shaded road is one near-constant value
  crossing a threshold (spread 0.79 → 0.85 sd). Grade **variation within the shadow mass**, which
  neither contrast nor a uniform fill can supply — a sky-visibility term is structural. One lever
  at a time.

---

## Infrastructure

Flyovers, ramps, footbridge canopies and podium decks are mesh class `INFRASTRUCTURE`, with its own
colour, LOD cells and grader. A reference section, not a work list.

- One flat colour, `#615f5a` (`concrete_sooty`, 22%) for deck, soffit, pier, parapet and footbridge
  alike, overriding the height bands.
- Cell sizes held at `[0.0, 0.5, 1.0]` so a thin deck keeps its depth (see LOD policy).
- The class takes none of the façade shader's treatment: `roof_darkness`, grounding gradient and
  jitter sit inside `if (is_facade)`, and `MARKER_STRUCTURE` is `2.0`.

Measured on `build/driver/art_infra` with a tint probe:

| | |
|---|---|
| `INFRASTRUCTURE` share of the frame | **2.71%** |
| …of which faces downward | **15.6%** (0.42% of frame) |
| Structure up/side faces | `L*` **51.1** against a non-sky frame mean of **48.1** |
| Structure soffits | `L*` **35.9** |

- ⚠️ The pale beams filling that frame are `BUILDING`, not `INFRASTRUCTURE`. Name a class with a
  tint probe, not from the silhouette.
- ⚠️ A soffit already sits 15 `L*` under its deck: that is `N·L` under one directional light, not
  missing AO.
- ⚠️ **Do not add a `structure_soffit_darkness` term** — built, measured (soffits 36.3 → 25.8,
  frame mean moved 0.05) and reverted; 0.42% of one frame closed it (`Q32`).
- What survives: one flat colour makes a viaduct's massing legible only where the sun catches a
  face. Not urgent. Re-measure the share before reopening, and do not darken `#615f5a` by eye — it
  needs a material (`Q33`).

---

## Ground

Shipped `P3-10`. The source terrain is textured (224 MB of JPEG against 43 MB of geometry); the
texture is **read at build time and never shipped**. Ground is untextured, vertex-coloured and
merged into the tile's single primitive, decimated at 4 m cells.

- Cost, measured: +87,649 triangles at LOD0, +30,695 at LOD1; 0 texture memory; +0 draw calls;
  **+4.56 MB of PCK**. ⚠️ Nearly double the geometry-only prediction, because the ground merges into
  the tier-0 `-col` mesh and so also gets a `ConcavePolygonShape3D`.
- ⚠️ The ground collides, by decision: merged into `-col` means solid, and a driver who leaves the
  road drives on the pavement (`ARCHITECTURE.md`).
- Resident triangles ≈380,700 at the worst streaming sample (tiles plus 99,877 of always-resident
  heroes; `PROGRESS.md`) against a 300k *visible* mobile budget — different quantities, and
  `verify_city_streamer.gd` refuses to gate one on the other, but headroom is thin for `P2-6`.
- ⚠️ **Flat shading has to be asked for** (`Q29`): `mesh.collapse`'s `height_field` path averages
  normals (8.72° mean error), so both façade shaders rebuild the normal from screen-space
  derivatives where `marker` is `MARKER_GROUND`. Any other ground material must do the same.

Colour:

1. **Flat** — `concrete_paving` `#5f5a51`, 20%. The surface is paving, plaza and apron, not soil
   (`Q36`); authored `C*` 5.9, rendered 3.53. ⚠️ `Q18`'s doubled chroma is superseded — read `Q36`
   before restoring it. ⚠️ Do not simplify to neutral grey: rendered chroma is roughly
   \|warm albedo − blue illuminant\|, so authored `C*` 4.47 renders *bluer* (5.04) than 5.93 does.
2. ❌ **Land-cover classes — refused.** Resolution mismatch no tuning reaches: the photo is ~10 px/m,
   the ground clusters at 4 m. Its "water" class is shadow (51.1% on rooftops); vegetation resolves
   to one-cell fringes round footprints (5.5% of cells above half vegetation). **If parks are
   wanted, the source is vector land-use polygons** (`Q18`). A geometric hillside split was also
   refused (`Q36`): high terrain draws 0.000% of all six viewpoints, and the road that climbs looks
   over ground that is 97.5% flat.

⚠️ **Solved as a surface, unsolved as a place.** In `build/driver/art_ground` the reclamation south
of HKCEC is 200 m of one correct colour carrying nothing, and converges on beach whatever its hue.
The colour levers are all pulled (`Q18`, `Q33`, `Q36`). The lever is what stands *on* the ground —
`B3`'s `P3-3`, `P3-4`, `P3-8`. If a first pass reads dead, suspect the palette before the
technique (the city reading white was the `height_bands` 19 `L*` too light).

**Not done: shipping the orthophoto**, resampled or otherwise. A draw call per tile, and the real
roads, markings, parked cars and shadows baked in it would show from under the wider synthetic
ribbon.

**`ground_sink_m` is 0.20**, measured by `tools/ground_clearance.py` — share of ground still proud
of the shipped road:

| `ground_sink_m` | of carriageway area | of the road's height sample points |
|---|---|---|
| 0.00 | 47.5% | 49.9% |
| 0.10 | 9.3% | 1.8% |
| 0.15 | 5.2% | 0.97% |
| **0.20** | **3.3%** | **0.36%** |
| 0.25 | 2.2% | 0.24% |
| 0.35 | 1.2% | 0.12% |

0.20 is the shallowest value passing both gates; deeper is gap seen under the 0.15 m riser. ⚠️ The
first column is mostly not the sink's to fix: the road is a plane interpolated between retained
vertices and flat across an over-drawn width. `roads.ground_profile` closed the along-the-road half
(area proud 3.289% → 1.898%); the across-the-road half is `Q19`'s trade.

---

## Vehicles

| Property | Target |
|---|---|
| Triangles | 800–2,000 |
| Materials | 1–2 — the body's is one `ShaderMaterial` (`P3-11c`). ⚠️ The source carries a slot per part (`vehicle_paint`, `vehicle_glass`, `vehicle_lamp_*`) which the import merges (`P5-23`); the budget is what renders |
| Colours | 3–5 flat colours per vehicle (⚠️ the taxi is at eight, each granted for a stated reason — a standing exception) |
| Wheels | Oversized, separate mesh, simple rotation |
| Windows | Flat dark colour with a fixed specular hint — no reflection probes |

Proportions: shortened wheelbase, tall greenhouse, exaggerated arches. Readable from behind at
speed.

**Body shader** (`vehicle_body.gdshader`, `P3-11c`): "flat" means flat *albedo*. A surface marker in
`UV.y` gives glazing, lenses and paint a clearcoat over a three-band sky gradient (zenith, horizon,
dark ground) chosen by the reflected ray's elevation.

- ⚠️ A single flat reflection colour is a swatch at any strength; with the gradient, glazing `L*`
  spread went sd 0.05 → 6.35. It responds to roll and pitch, not steering (yaw leaves the ray's `y`
  untouched).
- The sun glint is the one term that responds to steering. On flat-shaded geometry it is per-facet —
  a pane flashes whole. Its direction is read from the scene's `DirectionalLight3D`, never authored
  twice.
- ⚠️ Gloss on paint is priced in chroma: the shipped car pays `C*` −7.43 (`paint_reflect` 0.12,
  roughness 0.55, `fresnel_power` 6.5) and at `C*` 71.63 is still 9× the frame median. Fresnel is
  what makes it affordable — ablated, paint loses a further `C*` 13.75. Red identifies 紅的, so
  this dial is the first to back off if recognition scores poorly (`DECISIONS.md` `P3-11c`).
- `SILVER` is `(175,171,166)`, `b*` +3.07: it had been authored blue, and is fixed at the colour
  because the hubs share it on the tyre mesh, which gets no shader.

**Shape** (`tools/make_vehicle.py`): screens are raked by angle — 35° front, 30° rear — and
`roof_*_taper_m` is derived; windscreen and cant rail are one plane. The lower body breaks once at
`bumper_bottom_y_m`: red valance at nose and tail, dark rocker along the flank. ⚠️ The rocker is the
third dark strip tried there and is on trial at 60 mm; `rocker_top_y_m = sill_y_m` removes it.

**In situ**: on `build/driver/art_taxi` t04.50 the red bodywork is `C*` 86.5 against a frame median
of 7.5 and a city p99 of 39.8 — the only chromatic object in the frame.

**Lamps** (`P3-11d`–`f`): `UV.x` carries a circuit id per lens — brake, reverse, an indicator per
side, two front pairs, the roof sign; eight circuits across two `instance uniform` vectors
(`lamp_lit` is a `vec4`, running on into `lamp_front`). `vehicle_lamps.gd` writes them per
instance, because the body material is shared by the roster.

- The rear lamps read the car, the front lamps read the light (shade, or no sky overhead), and the
  roof sign reads neither — held on, and deliberately off the light ladder.
- Two front lens pairs, not one at two brightnesses: a lens under the 1.0 glow threshold has no
  bloom, which is the whole difference at chase distance. The sign is a lit surface, not a source,
  so `sign_lit` runs 0.45, under the 0.63 where `lamp_emission` 1.6 crosses the threshold.
- ⚠️ Emission is the lens's hue at a fixed intensity, not its albedo scaled. `lamp_emission` 1.6
  (`C*` 44 at the core); past 1.2 the tonemap is ACES and more emission is more white. Braking takes
  the lens `L*` 2.29 → 72.72.
- ⚠️ Indicators need a hold: half a second of held lock at 0.35 of the lock available at that speed.

**Roster for the slice** (only the player taxi is built — `P3-11`, 1,180 triangles; the rest are
`B3`'s `P3-3`/`P3-4`/`P3-8`): player taxi, private car (2 variants), red taxi (AI), double-decker
bus, green minibus, tram. Player-side vehicles are real models because drive layout differs
(`ARCHITECTURE.md`):

| Vehicle | Drivetrain | Notes |
|---|---|---|
| Old Toyota Crown (Comfort) | LPG, **rear-wheel drive** | The iconic HK red taxi |
| New Toyota Crown | Hybrid, **front-wheel drive** | |
| Toyota Hiace | CVT | Van proportions — tall, high centre of mass |

⚠️ Transmission character is not modelled (`engine_force` is a flat constant); flag it before the
Phase 5 roster work.

Vehicles are generated by `tools/make_vehicle.py` into `game/assets/authored/vehicles/` from named
proportions, and committed (CC BY-SA 4.0). ⚠️ The taxi's arches must line up with the wheel mount
points in `taxi.tscn`; physics never reads the mesh, so a mismatch looks correct and drives to the
old tuning.

---

## Lighting

- One directional light (sun), warm, low angle, from the shared `golden_hour.tscn` rig.
- Ambient from a simple gradient sky — no HDRI, no reflection probes.
- Two shadowless spots per taxi, one per headlamp, switched with the front lamps (`P3-11e`), hidden
  in daylight; measured at 0 extra draw calls and primitives.
- **Mobile tier:** vehicle blob shadows only, no realtime shadow maps.
- **Desktop tier:** two directional shadow cascades at 400 m, the far plane.
- No global illumination, no SSAO on mobile. Resist adding lights.

⚠️ Two cascades, not one: one is cheaper (55% off the frame's primitives against 35%) and shows an
artefact at every distance — cutoff at 150 m, banding at 250 m, dropped casters at 400 m.

⚠️ Re-examine "blob shadow only" before building the mobile tier: shadows off looked flat and blown
out. The tier needs ambient and tonemap re-tuned around a blob shadow.

**The clean look's rig is `scenes/world/clean_daylight.tscn`**: 48° sun, pale horizon under deep
blue, thresholded glow, light depth fog. A low warm sun rakes a white city to two values. Both dev
scenes must name the same rig.

- ⚠️ `ambient_light_sky_contribution` is the colour of every shadow: dark albedo takes nearly all
  its light from ambient, so a saturated sky paints the `#42403d` asphalt blue — and it is also what
  separates one white face from the next. Blend low toward a cool neutral `ambient_light_color`;
  do not reach for the road palette.
- 🔴 The clean rig was tuned against the pre-`Q27` colour-space bug and is due a pass (`Q26` owns
  the look, `Q31` the levers). Grade it on the **shadow value**, not the key: the failing frames
  are the two in shade (51.4% and 28.9% under `L*` 10). The dominant term is `adjustment_contrast`
  (1.14 → 1.00: `kerb` 51.3% → 0.9%, `taxi` t01.20 28.9% → 0.8%); a 65% lift of
  `ambient_light_energy` leaves the shadow mass under `L*` 10 and flattens massing more.
- A washed-out frame is not evidence about the lights — grade with `tools/frame_stats.py` whether
  an albedo change reaches the screen before touching one.

---

## LOD policy

Generated by the ETL, not decimated at runtime.

| Tier | Distance | Content | Cell size | Wan Chai triangles |
|---|---|---|---|---|
| LOD0 | 0–250 m | Merged massing, window shader, props | 1.5 m (infrastructure 0.5 m) | 506,045 |
| LOD1 | 250–400 m | Silhouette-only merged block, flat colour | 4.0 m (infrastructure 1.0 m) | 245,145 |

Desktop shifts these distances outward rather than adding a tier.

- ⚠️ **No exact-weld tier, by measurement** (`P2-1`, `Q16`): side by side the user could not tell,
  and it cost 30.5 MB of bundle and 40% of worst-case visible triangles. Restoring it is one entry
  in `lod_cell_sizes_m` and a rebuild.
- Tiers are **vertex clustering** on grid cell *and* facing — position alone averages a wall vertex
  with the roof above it and rounds the hard normals. Quadric decimation smooths corners the style
  wants kept.
- ⚠️ Anything smaller than a cell disappears at that tier, so cells cannot rise much further.
- ⚠️ Anything *thinner* than a cell flattens: a 0.8 m deck goes 12 triangles → 2 at a 1.0 m cell.
  Hence per-class cells: `class_lod_cell_sizes_m` holds `INFRASTRUCTURE` at `[0.0, 0.5, 1.0]`. A
  class is collapsed at its own cell and the tile merged afterwards — still one draw call.
- ⚠️ Towers are hit harder by LOD1 than the rest: 36% of triangles kept against 44%.

---

## UI

**Visual language: Hong Kong road signage and the taxi meter.** `game/tuning/hud_style.tres` and
`hud_layout.tres` are the authority (`P3-24`). The racing-game arrangement (`Q138`): minimap and
street name, one panel, bottom-left; speed bottom-right. Flat chamfered panels in one dark
housing under one bezel (`Q139`), the cab's two instruments keeping their own faces — the
dashboard's dial for the speed, the 咪錶's red seven-segment LED kept for the fare. The CJK face is **Free HK Kai** (`Q79`). The wrong-way NO ENTRY disc
carries the world sign's measured proportions (`Q81`).

- **Bilingual throughout** — part of the art, not a localisation afterthought.
- Fare display styled as a taxi meter — LCD segments, red digits (unbuilt; `P3-5a`).
- Direction arrow styled after HK directional signs (unbuilt; `P3-5a`).
- High-contrast, safe for outdoor phone use in daylight.
- Safe areas respected; resolution-independent because desktop is a target.

---

## Audio direction

Same authenticity budget, and cheap:

- Tram bell — the single most evocative HK sound
- Minibus engine whine
- Bilingual passenger callouts (Cantonese primary)
- Ferry horn from the harbour side
- Radio stings between fares

---

## The audit viewpoints

Seven fixed cameras, so a look change is judged against the last change. Two viewpoints can disagree
about whether the city reads white, and the disagreement is the finding (`Q27`). All run through
`.claude/skills/run-hk-taxi-q/drive.sh`, deterministic to the centimetre.

| Name | Scene | Camera → look | What it is the evidence for |
|---|---|---|---|
| `street` | preview | `270,5.5,691` → `30,4.5,719` | Hennessy Road canyon. Façade colour at eye level, the shipping viewpoint |
| `skyline` | preview | `520,130,180` → `520,45,640` | Massing and silhouette over the harbour |
| `kerb` | preview | `283,6,684` → `300,3.2,700` | Causeway Bay in shade. The value gap, and the chroma tail at its loudest |
| `ground` | preview | `400,45,300` → `250,0,60` | The waterfront reclamation. Terrain as an expanse, and the region edge |
| `infra` | preview | `1010,9,890` → `930,13,800` | Canal Road flyover from beneath. Deck, soffit, pier |
| `taxi` | drive | `--seconds=6 --shots=1.2,4.5 --hold=accelerate@0.3+4` | The car in shade at 1.2 s and in sun at 4.5 s |
| `aerial` | preview | `850,620,1750` → `850,10,400` | The whole region. Chiefly a fog check |

- ⚠️ Use `--debug-view=off` on every one; the overlay's text block lands in any PNG statistic.
- ⚠️ Preview shots carry `road_preview.gd`'s polylines and 1,125 arrows whatever the flag says.
- ⚠️ A run can stall the renderer intermittently (`no frame drawn in 600 ticks`). It fails loudly —
  exit 1, no frame. Retry the viewpoint; conclude nothing about the look.
- ⚠️ A pending screenshot verdict expires with the next palette commit (`Q29`). Re-shoot before
  comparing and say which commit a shot is of.
- ⚠️ A click on the run window puts `free_look_camera.gd` into captured-mouse mode, and mouse
  movement then rotates the audit camera — position survives, aim moves, the run still exits
  `DRIVER OK` and logs the requested transform. Leave the machine alone, shoot each viewpoint twice
  and `cmp` (`Q26`).
- These viewpoints are static by `t=0.8` (byte-identical to `t=1.5` and `t=3.0`); capture early.

---

## Anti-goals

⚠️ Anti-goals, not hard rules: revisable with evidence. Each entry's stated reason is load-bearing —
a wrong reason changes what lifting the entry would make possible.

- No photorealism, PBR metalness workflow, or reflection probes
- No photogrammetry textures in the bundle. **Reading one at build time to derive a flat colour is
  allowed, and is how the ground is coloured**
- No per-building unique textures
- **No texture atlas for buildings.** `merge` refuses textured meshes, and one primitive per tile is
  what holds draw calls (`Q16`)
- No realistic weather or wet-road reflections in the slice
- **No baked illumination** — flat shading plus one directional light is the look

Reasons, stated exactly:

- ⚠️ "No PBR" is not anti-physics: `Q33`'s `reflectance` table is PBR's albedo discipline as data,
  and the shaders write `ROUGHNESS` and a fresnel term. What is refused is the texture-map
  workflow — and metalness has nothing to reflect on the Mobile renderer (no SSR, no probes).
  Measured (`P3-11c`): uniform gloss moved the taxi's red `C*` 79.06 → 70.08 and hue −7.9° while
  raising `L*`. Gloss is affordable only where the surface should read as a dark mirror — glazing.
- ⚠️ The photogrammetry entry rests on the *look* (a mismatch with flat shading) and the structural
  blockers. Not size (a 45 MP sheet is ~1 MB against a 128 MB texture budget), not trademark, not
  licence (`LICENSING.md`: commercial use is explicit).
- ⚠️ The atlas entry's reason is `merge`, not memory and not UVs.
- ⚠️ Baked *occlusion* is not refused: AO is sun-independent and is the only occlusion the mobile
  tier could have on static geometry. What blocks a *lightmap* is texel budget (2.143 km² of terrain
  is 2.1 M texels at one per m²), the unchosen sun, and LOD1 carrying none across the 250 m switch.
  🔴 Raising `meshes/light_baking` to Static Lightmaps would regenerate UV2 over the tiles'
  `TEXCOORD_1` payload (marker, phase, object row — `P5-11`); `verify_tiles.gd` asserts the import
  setting and the payload's integer exactness.
