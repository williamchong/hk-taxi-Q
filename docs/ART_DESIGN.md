# Art Design

## Direction

**Low-poly, flat-shaded, saturated. Accurate city, toy vehicles.**

That split is deliberate and is the core art decision:

| | Treatment | Why |
|---|---|---|
| **City** | Accurate proportions, real massing, real street widths (then widened for play) | Recognition is the product. Stylising building proportions destroys the one thing that makes this game worth making |
| **Vehicles** | Choro-Q / toy proportions — short wheelbase, oversized wheels, chunky | Charm and readability. Cars are what the player looks at for hours |

Stylise the actors, not the stage. A deformed Hopewell Centre stops being Hopewell Centre; a deformed
taxi is just cuter. **`Q8` measured this rather than assuming it:** driving the real city was judged
fun on the strength of recognition alone, which is what makes the expensive half of the trade worth
what it costs.

---

## Why the art style and the data choice are the same decision

The source data — 3D Visualisation Map (non-textured) and 3D-BIT00 Level 1 — is **extruded footprints
with no textures**. That is already a flat-shaded low-poly building. Consequences that make the whole
project affordable:

- No texture atlas packing, no KTX2 transcoding, no texture memory pressure
- Untextured meshes with vertex colours **merge into one mesh per tile**, which is what keeps draw
  calls under budget — 53 against a 150 budget, measured
- Geometry-only glTF quantises and compresses far better than textured assets

The art direction isn't a stylistic preference layered on top of the data. It *is* the data.

---

## Palette

Hong Kong-specific, not generic-city. Anchor colours:

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

**Time of day: golden hour by default.** Low warm sun flatters flat shading, gives long readable
shadows, and separates building faces without any texture work. Night (neon-forward) is a strong later
variant — plan the emissive channel now, build the mode later.

---

## Buildings

### General fabric (≈95% of buildings)

- Source: extruded footprints, untextured
- **Vertex colour**, assigned by ETL from height band and building class — no textures
- Flat/faceted shading, hard normals
- Subtle per-building colour jitter so blocks don't read as uniform

**The palette lives in `etl/config/cities/hong_kong.yaml` under `buildings:`**, not in code — five
height bands from warm beige for the low pre-war and post-war stock up to cool pale grey for
commercial towers, a flat concrete grey for `INFRASTRUCTURE`, and the jitter amount. Change it there;
change *why* here first. The jitter is seeded from each building's LandsD id, so it is stable across
rebuilds.

⚠️ **The jitter means a class is a *ray* through its base colour, not a value.** Any tool matching a
class by colour must test the scale factor, not equality — `tools/deck_error.py` matched 428 of
434,149 triangles before this was understood.

### The window-band shader

Cheap, and does more for "this is Hong Kong" than any other single technique. Instead of window
textures, a shader draws **horizontal banding in world space** on vertical faces — floor lines and
window rows, procedurally. Dense repetitive window grids are the defining visual signature of HK
residential towers.

```
Inputs:  face normal, TEXCOORD_0.x = height above the building's own base (0-1),
                      TEXCOORD_0.y = per-building seed
Output:  band mask → darkened window rows, occasional lit window (emissive at night)
Cost:    a few instructions, zero texture memory
```

⚠️ **Two of those inputs have to come from the ETL, and they are why `P3-7` is one commit across both
sides.** A vertex knows its world Y, not where its building starts — a podium vertex and a 30th-floor
vertex are indistinguishable to the shader — and it has no seed at all, so neighbouring towers would
share a window pattern. Buildings ship **no UVs today**, so `TEXCOORD_0` is free, costs about 2 bytes
per vertex quantised, and survives vertex clustering through the same representative-selection path
that already carries colours.

⚠️ **Not `COLOR_0.a`**, although it is free and currently a constant `255`: the project-wide import
default sets `vertex_color_use_as_albedo`, and an opaque material ignores albedo alpha only until
somebody enables transparency on a tile, at which point the city goes see-through with no error.

A third thing rides the same stream for nothing: **bake a vertical gradient into `COLOR_0`**,
darkening the bottom couple of metres of every building. Grounding a wall where it meets the pavement
does more for perceived quality than per-building colour accuracy, and costs zero at runtime.

Windows must **not** appear on roofs or ground-level podium faces — mask by normal and by height above
ground.

### What buildings will *not* get

- **No per-building texture, and no low-res atlas.** Any texture needs UVs, and UVs do not survive the
  vertex clustering that produces both shipped LOD tiers. It is paying to break the LOD system.
- **No colour sampled per building from the individualised set.** That means the 5.86 GB download for
  one region, 93–96% of it texture, plus matching ids across two sets that disagree on model count.
  And oblique aerial capture is dominated by shadow, sky bounce and haze, so the median converges on
  grey-beige for everything — flattening exactly the old-below/new-above contrast the height bands
  exist to express. High cost, plausibly negative result.
- **What the photo data may be used for** is a one-off offline read: cluster the dominant façade
  colours from a sheet or two and re-author the five `height_bands` in city config from the result.
  Evidence-based palette, nothing added to the build path.

### Hero buildings (~5)

Distinctive silhouettes need hand-authored low-poly models with light texturing, placed via
`landmarks.json`:

| Building | Why it needs authoring |
|---|---|
| **HK Convention & Exhibition Centre** | The curved "flying wing" roof |
| **Central Plaza** | Pyramid crown |
| **Hopewell Centre** | Cylindrical tower |
| **Times Square** | Needs its signage identity |
| **Wan Chai government slabs** | Read fine as boxes, but the grouping needs composition |

The ETL must exclude the source geometry these replace (`replaces_source_ids`) to prevent z-fighting.
**Budget:** ~3–8k triangles each — silhouette landmarks seen from a distance at speed, not hero props.

⚠️ **The reason is *not* "LOD1 extrusion flattens them", which was the original wording.** Measured,
the non-textured source is not an extrusion at all: it carries the individualised set's exact
silhouette. The lever these buildings need is texture and hand-authored detail, not a better source
dataset.

---

## Roads

- Ribbon mesh generated from road-graph polylines, vertex-coloured
- Markings via **shader along the ribbon's UV** (lane lines, yellow boxes, crossings) rather than a
  texture atlas — keeps the untextured pipeline intact. `P1-4` already ships the UVs the shader will
  read: **U is a lane coordinate**, 0 at the nearside kerb line and `lanes` at the offside, so an
  integer U is a lane boundary regardless of the playability widening — including the per-station
  widening `Q23` introduced. V is metres along the carriageway, so dashes keep a real-world pitch.
  Junction caps carry `(0, 0)`; a box junction is a mask keyed on the node, not a length of lane.
- Kerbs modelled but low and mountable — collision is forgiving by design. Built as a 0.15 m riser
  and a 0.5 m lip. The lip does double duty: with no terrain shipped yet, it is what stops the
  carriageway ending in mid-air. `P3-10` gives it a second job — the ground tucks *under* the lip,
  which is what hides the seam.
- Tram tracks as an inset strip on flagged edges — **not yet built.** `tram_tracks` reaches the graph
  but `P1-4` draws no inset; it belongs with the markings shader, not with the ribbon.

⚠️ **When the markings shader lands it will expose a junction defect that is invisible today.** A cap
overlaps its arms rather than abutting them wherever a short edge is held back by the junction trim —
6,051 m² of 52,985 m² of cap area. Cap and carriageway are the same colour at the same height in one
material, so nothing shows; give the ribbon lane markings and the cap will read as a patch over them.

---

## Ground

⚠️ **There is no ground in the game today.** Between the roads and under the buildings is skybox.
`P3-10` is what fixes it, and it lands in `B2` because the build whose verdict question is "does this
read as Wan Chai?" cannot be judged over a void.

**The source ships one, and it ships it textured** — 224 MB of JPEG across the region's six sheets
against 43 MB of geometry. The texture is the whole reason terrain was called unaffordable.

**So the texture is read at build time and never shipped.** Ground obeys the same rule as buildings:
untextured, vertex-coloured, merged into the tile's single primitive. That is not a compromise — it is
what keeps the invariant the whole pipeline rests on.

| | Result |
|---|---|
| Triangles, decimated at 4 m cells | **88,081** region-wide ≈ 1,355 per tile |
| Texture memory | **0** |
| Bundle | 1.5–2.5 MB against a 26.3 MB PCK |
| Draw calls | **+0** — it merges with the buildings in the same tile |

Deleting the texture also deletes the reason terrain was awkward to decimate: clustering moves UVs and
a photographic texture smears where it does, and there are no UVs left to move.

**Colour comes in two steps, and may stop after the first.**

1. **Flat.** One warm ground colour, height- or slope-varied at most. Small, no new dependency, and it
   is the screenshot that says whether flat ground reads as ground at all — `Q18`.
2. **Land-cover classes,** only if flat reads dead. Sample the source JPEG per source triangle, snap
   to a small palette — asphalt, pavement, vegetation, water, bare — and put the class in the cluster
   key alongside the facing. Cluster boundaries then land *on* the park and harbour edges instead of
   blending across them, which is what makes 4 m colour blobs read as deliberate low-poly ground
   rather than as mush.

**Prior art says the first step can be the last one.** *Art of Rally* ships flat-shaded untextured
terrain as its finished look, not as a placeholder. Wan Chai is far denser than that game's
countryside, so it settles nothing here — but if the first pass reads dead, **suspect the palette
before the technique**.

**What is explicitly not done: shipping the orthophoto, resampled or otherwise.** It would cost a draw
call per tile, since a textured surface cannot merge with a vertex-coloured one. And an orthophoto has
the *real* roads baked into it at their real width, while the generated ribbon sits coplanar with the
terrain and **1.6× wider** — so photographic asphalt and photographic lane markings would show from
under a wider synthetic road, along with parked cars and baked shadows.

⚠️ **Two things to get right, both cheap to get wrong.** The ground sits coplanar with the level-0
carriageway by construction, so it must be **sunk under the kerb lip** — roughly 0.2 m, and that
number is a guess until it is driven on a cross-sloped street. And the first pass is **visual only,
with no collider**: the kerb currently defines the drivable world, and giving the pavement collision
is a gameplay change wearing an art change's clothes.

---

## Vehicles

| Property | Target |
|---|---|
| Triangles | 800–2,000 |
| Materials | 1–2, flat shaded |
| Colours | 3–5 flat colours per vehicle |
| Wheels | Oversized, separate mesh, simple rotation |
| Windows | Flat dark colour with a fixed specular hint — no reflection probes |

Proportions: shortened wheelbase, tall greenhouse, exaggerated wheel arches. Readable silhouette from
behind at speed — that's the only angle most players ever see.

**Vehicle roster for the slice:** player taxi, private car (2 variants), red taxi (AI), double-decker
bus, green minibus, tram. See `PROGRESS.md` for the real models these are based on and the drivetrain
differences that make it an architecture constraint rather than an art note.

---

## Lighting

- One directional light (sun), warm, low angle, from the shared `golden_hour.tscn` rig
- Ambient from a simple gradient sky — no HDRI, no reflection probes
- **Mobile tier:** vehicle blob shadows only, no realtime shadow maps
- **Desktop tier:** **two** directional shadow cascades at 400 m — the camera's far plane
- No global illumination, no SSAO on mobile

⚠️ **This said "one cascade" until it was measured.** One is cheaper — 55% off the frame's primitives
against 35% for two — and unusable: it has a distinct artefact at every distance, a visible shadow
cutoff mid-street at 150 m, banding on large soft shadows at 250 m, and off-screen casters dropping
out entirely at 400 m. Two gives a fine near split and a coarse far one and shows none of them.

⚠️ **"Vehicle blob shadow only" deserves re-examination before anyone builds the mobile tier.** Shots
with shadows *off* looked markedly worse than that line implies — flat and blown out, the canyon
losing its depth entirely. A real mobile tier needs the ambient and tonemap re-tuned around a blob
shadow, not the shadow switched off.

Flat shading plus a single strong key light is what makes low-poly read as intentional rather than
cheap. Resist adding lights.

---

## LOD policy

Generated by the ETL, not decimated at runtime.

| Tier | Distance | Content | Cell size | Wan Chai triangles |
|---|---|---|---|---|
| LOD0 | 0–250 m | Merged massing, window shader, props | 1.5 m (infrastructure 0.5 m) | 434,149 |
| LOD1 | 250–400 m | Silhouette-only merged block, flat colour | 4.0 m (infrastructure 1.0 m) | 222,375 |

Desktop tier shifts these distances outward rather than adding a new tier.

⚠️ **There is no exact-weld tier, and that is a measured decision rather than an omission.** The table
carried one at 0–150 m until `P2-1`'s review: driven side by side against a build that had none, the
user could not tell them apart, because extruded massing is big boxes and a 1.5 m cell takes half the
triangles while leaving the silhouette. Dropping it cost **30.5 MB of a 51.6 MB bundle** and **40% of
worst-case visible triangles**, both measured from real exports rather than summed from source.
Restoring it is one entry in `lod_cell_sizes_m` and a rebuild, so a later region or a desktop-only
asset split can have it back.

Tiers are produced by **vertex clustering** — merging vertices that share a grid cell *and* a facing.
Facing is in the key deliberately: cluster on position alone and a wall vertex averages with the roof
vertex above it, rounding off the hard normals this whole style rests on. Clustering also suits
extruded footprints better than quadric decimation, which smooths corners the art direction wants
kept.

⚠️ Anything **smaller** than a cell disappears entirely at that tier — intended for street furniture
at 400 m, but it means the cell sizes cannot be raised much further without losing small buildings.

⚠️ **And anything *thinner* than a cell flattens, which is a different failure and a worse-looking
one.** Clustering merges a structure's top surface into its bottom one, so a 0.8 m deck goes from 12
triangles to 2 at a 1.0 m cell while a 60 m tower is untouched at every cell the pipeline uses. That
is why cell size is **per mesh class**: `class_lod_cell_sizes_m` overrides the table above, and Hong
Kong holds `INFRASTRUCTURE` at `[0.0, 0.5, 1.0]` so flyover decks, ramps and footbridge canopies keep
their depth. A class is collapsed at its own cell and the tile is merged afterwards, so it is still
one mesh and one draw call.

⚠️ **Towers are hit harder by LOD1 than the rest, not less** — 36% of their triangles kept against 44%
for everything else. They read as fine in a canyon shot because they were distant, where a tower is
mostly silhouette. Recorded because the opposite was written down first.

---

## UI

**Visual language: Hong Kong road signage and the taxi meter.**

- Typography: condensed grotesque for English, paired with a clean Traditional Chinese face.
  **Bilingual throughout** — this is not a localisation afterthought, it is part of the art.
- Fare display styled as a **taxi meter** — LCD segments, red digits
- Direction arrow styled after HK directional road signs
- Colour: high-contrast, safe for outdoor phone use in daylight
- Safe areas respected for notches and rounded corners; **resolution-independent** because desktop is
  a target

---

## Audio direction

Not art, but it belongs to the same authenticity budget and is cheap:

- Tram bell — the single most evocative HK sound
- Minibus engine whine
- Bilingual passenger callouts (Cantonese primary)
- Ferry horn from the harbour side
- Radio stings between fares

---

## Anti-goals

- No photorealism, PBR metalness workflow, or reflection probes
- No photogrammetry textures — a trademark surface as well as an aesthetic mismatch. **Reading one at
  build time to *derive* a flat colour is not the same thing and is allowed**; what must not happen is
  a photograph reaching the bundle
- No per-building unique textures; the window shader replaces them
- No texture atlas for buildings. UVs do not survive the vertex clustering that builds both LOD tiers,
  so an atlas costs the LOD system, not just memory
- No realistic weather or wet-road reflections in the slice
- No baked lightmaps — flat shading plus one directional light is the look
