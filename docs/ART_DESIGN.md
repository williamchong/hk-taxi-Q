# Art Design

## Direction

**Low-poly, flat-shaded, saturated. Accurate city, toy vehicles.**

That split is deliberate and is the core art decision:

| | Treatment | Why |
|---|---|---|
| **City** | Accurate proportions, real massing, real street widths (then widened for play) | Recognition is the product. Stylising building proportions destroys the one thing that makes this game worth making. |
| **Vehicles** | Choro-Q / toy proportions — short wheelbase, oversized wheels, chunky | Charm and readability. Cars are what the player looks at for hours. |

Stylise the actors, not the stage. A deformed Hopewell Centre stops being Hopewell Centre; a
deformed taxi is just cuter.

---

## Why the art style and the data choice are the same decision

The source data — 3D Visualisation Map (non-textured) and 3D-BIT00 Level 1 — is **extruded
footprints with no textures**. That is already a flat-shaded low-poly building.

Consequences that make the whole project affordable:

- No decimation step, and no decimation artefacts
- No texture atlas packing, no KTX2 transcoding, no texture memory pressure
- Untextured meshes with vertex colours **merge into one mesh per tile**, which is what keeps draw
  calls under budget
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
| **Player taxi** | **Red** with silver roof | HK Island urban taxi. Non-negotiable. |
| Minibus | Cream body, **green** roof | Green minibus |
| Tram | Green and white | Instantly recognisable silhouette |
| Neon | Saturated magenta, cyan, gold — emissive | Sparingly; accent only |
| Vegetation | Deep saturated green | HK street trees are dark and dense |

**Time of day: golden hour by default.** Low warm sun flatters flat shading, gives long readable
shadows, and separates building faces without any texture work. Night (neon-forward) is a strong
later variant — plan the emissive channel now, build the mode later.

---

## Buildings

### General fabric (≈95% of buildings)

- Source: extruded footprints, untextured
- **Vertex colour**, assigned by ETL from height band and building class — no textures
- Flat/faceted shading, hard normals
- Subtle per-building colour jitter so blocks don't read as uniform

**The palette lives in `etl/config/cities/hong_kong.yaml` under `buildings:`**, not in code — five
height bands from warm beige for the low pre-war and post-war stock up to cool pale grey for
commercial towers, a flat concrete grey for `INFRASTRUCTURE`, and the jitter amount. Change it
there; change *why* here first. The jitter is seeded from each building's LandsD id, so it is
stable across rebuilds.

### The window-band shader

Cheap, and does more for "this is Hong Kong" than any other single technique.

Instead of window textures, a shader draws **horizontal banding in world space** on vertical
faces — floor lines and window rows, procedurally. Dense repetitive window grids are the defining
visual signature of HK residential towers.

```
Inputs:  world Y position, face normal, building height, per-building seed
Output:  band mask → darkened window rows, occasional lit window (emissive at night)
Cost:    a few instructions, zero texture memory
```

Windows must **not** appear on roofs or ground-level podium faces — mask by normal and by height
above ground.

### Hero buildings (~5)

LOD1 extrusion flattens distinctive silhouettes into meaningless boxes. These get hand-authored
low-poly models with light texturing, placed via `landmarks.json`:

| Building | Why LOD1 fails it |
|---|---|
| **HK Convention & Exhibition Centre** | The curved "flying wing" roof becomes a slab |
| **Central Plaza** | Pyramid crown lost |
| **Hopewell Centre** | Cylindrical tower becomes a prism |
| **Times Square** | Needs its signage identity |
| **Wan Chai government slabs** | Read fine as boxes, but the grouping needs composition |

The ETL must exclude the source geometry these replace (`replaces_source_ids`) to prevent
z-fighting.

**Budget:** ~3–8k triangles each. They are silhouette landmarks seen from a distance at speed, not
hero props.

---

## Roads

- Ribbon mesh generated from road-graph polylines, vertex-coloured
- Markings via **shader along the ribbon's UV** (lane lines, yellow boxes, crossings) rather than
  a texture atlas — keeps the untextured pipeline intact
  - `P1-4` ships the UVs the shader will read: **U is a lane coordinate**, 0 at the left kerb line
    and `lanes` at the right, so an integer U is a lane boundary regardless of the playability
    widening. V is metres along the carriageway, so dashes keep a real-world pitch. Junction caps
    carry `(0, 0)` — a box junction is a mask keyed on the node, not a length of lane.
- Kerbs modelled but low and mountable — collision is forgiving by design
  - Built by `P1-4` as a 0.15 m riser and a 0.5 m lip. The lip does double duty: with the terrain
    too expensive to ship, it is what stops the carriageway ending in mid-air.
- Tram tracks as an inset strip on flagged edges — **not yet built.** `tram_tracks` reaches the
  graph but `P1-4` draws no inset; it belongs with the markings shader, not with the ribbon.

---

## Vehicles

| Property | Target |
|---|---|
| Triangles | 800–2,000 |
| Materials | 1–2, flat shaded |
| Colours | 3–5 flat colours per vehicle |
| Wheels | Oversized, separate mesh, simple rotation |
| Windows | Flat dark colour with a fixed specular hint — no reflection probes |

Proportions: shortened wheelbase, tall greenhouse, exaggerated wheel arches. Readable silhouette
from behind at speed — that's the only angle most players ever see.

**Vehicle roster for the slice:** player taxi, private car (2 variants), red taxi (AI),
double-decker bus, green minibus, tram.

---

## Lighting

- One directional light (sun), warm, low angle
- Ambient from a simple gradient sky — no HDRI, no reflection probes
- **Mobile tier:** vehicle blob shadows only, no realtime shadow maps
- **Desktop tier:** one directional shadow cascade
- No global illumination, no SSAO on mobile

Flat shading plus a single strong key light is what makes low-poly read as intentional rather than
cheap. Resist adding lights.

---

## LOD policy

Generated by the ETL, not decimated at runtime.

| Tier | Distance | Content | Cell size | Wan Chai triangles |
|---|---|---|---|---|
| LOD0 | 0–150 m | Full massing, window shader, props | exact weld | 989,212 |
| LOD1 | 150–400 m | Merged massing, window shader, no props | 1.5 m | 400,139 |
| LOD2 | 400 m+ | Silhouette-only merged block, flat colour | 4.0 m | 183,773 |

Desktop tier shifts these distances outward rather than adding a new tier.

Tiers are produced by **vertex clustering** — merging vertices that share a grid cell *and* a
facing. Facing is in the key deliberately: cluster on position alone and a wall vertex averages
with the roof vertex above it, rounding off the hard normals this whole style rests on. Clustering
also suits extruded footprints better than quadric decimation, which smooths corners the art
direction wants kept. Cell sizes are `lod_cell_sizes_m` in city config.

⚠️ Anything smaller than a cell disappears entirely at that tier — intended for street furniture at
400 m, but it means the cell sizes cannot be raised much further without losing small buildings.

---

## UI

**Visual language: Hong Kong road signage and the taxi meter.**

- Typography: condensed grotesque for English, paired with a clean Traditional Chinese face.
  **Bilingual throughout** — this is not a localisation afterthought, it is part of the art.
- Fare display styled as a **taxi meter** — LCD segments, red digits
- Direction arrow styled after HK directional road signs
- Colour: high-contrast, safe for outdoor phone use in daylight
- Safe areas respected for notches and rounded corners; **resolution-independent** because desktop
  is a target

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
- No photogrammetry textures — a trademark surface as well as an aesthetic mismatch
- No per-building unique textures; the window shader replaces them
- No realistic weather or wet-road reflections in the slice
- No baked lightmaps — flat shading plus one directional light is the look
