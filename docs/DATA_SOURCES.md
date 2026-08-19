# Data Sources

All facts below were verified against primary sources. **Do not re-research these** — if something
turns out wrong, correct it here and record the finding in `DECISIONS.md`.

## Licence

All datasets below are published via DATA.GOV.HK and the CSDI Portal, and both portals grant the same
six acts — *browse, download, distribute, reproduce, hyperlink to, print* — for **commercial and
non-commercial use, free of charge**, with **no usage limit, quota or volume cap**. Read verbatim
2026-08-02.

What that costs us, and the part an ETL author needs:

- **Attribution is a stronger obligation than naming a source.** The terms require acknowledging the
  Government's and the relevant organisations' *ownership of the intellectual property rights*, and
  each portal requires acknowledgement of itself — so both must be named.
- **The indemnity is real and broad**, not boilerplate.
- Data is supplied **"AS IS"** with no warranty as to accuracy, completeness or fitness.

ℹ️ "Adapt", "modify" and "derivative" appear in neither portal's terms. That is expected rather than
alarming — "adaptation" is a term of art that does not attach to artistic works, where the restricted
act is *copying*, granted here as **reproduce**. Recorded so nobody re-derives an alarm from a
keyword search.

**`LICENSING.md` is canonical for all of this** — the operative clauses quoted in full, what may and
may not be relicensed, and the open items for legal review. Do not restate the terms here; this
section exists so an ETL change can be made without opening that file.

### Required credits-screen text (draft)

> Contains geospatial data from the Lands Department and the Transport Department of the Government
> of the Hong Kong Special Administrative Region, obtained via DATA.GOV.HK and the Common Spatial
> Data Infrastructure (CSDI) Portal. **The Government of the HKSAR and the relevant organisations own
> the intellectual property rights in that data.** Used under the DATA.GOV.HK and CSDI Portal Terms
> and Conditions of Use. The Government of the HKSAR does not endorse this product.

⚠️ The ownership sentence is not optional padding — see the attribution note above.

> **Legal note:** because this ships as a commercial product, have a Hong Kong IP lawyer sight-check
> landmark depiction and the credits text before launch. **Landmark depiction is the top item** in
> that brief: reading the data terms verbatim cleared the licensing question, which leaves building
> depiction as the one with a plausible adverse answer.

---

## Buildings

### ✅ USE — 3D Visualisation Map (Non-textured models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-non-textured-models
- **Publisher:** Lands Department. **Formats:** MAX, FBX, **glTF** — one zip per 1:1000 sheet.
- **Content:** geometry and position only — no textures **on buildings**. Terrain ships textured.
- **Coverage:** whole territory, 3,456 sheets. **Access: fully scriptable** — see "Access notes".
- **Why:** flat-shaded extruded volumes are exactly the target art style.
- ⚠️ **Decimation is needed after all** at 612 triangles per building — see the budget note below.

### ✅ USE — 3D Spatial Data (3D-BIT00), Level 1

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-development-hkms-digital-3d-bit00
- **Formats:** MAX, 3DS, FBX, VRML.
- **Level 1 definition (verified):** every building and/or podium with a footprint area greater than
  **4 m²** in the B1000 digital topographic map, **extruded from its footprint** between the relevant
  base and top level, with **no photorealistic texture applied**.
- **Why:** a low-poly building by construction. Use as a cross-check against the non-textured models.

### ✅ USE — iB1000 Digital Topographic Map (FGDB)

- **Portal:** `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637223748322_25497`
- **Publisher:** Lands Department (Survey and Mapping Office). **Formats:** FGDB, GML, DGN, DWG —
  one zip per 1:1000 sheet, laid out `<SHEETNO>/<SHEETNO>.gdb`. The schema authority is the *iB1000
  Data Dictionary — FGDB* v1.2 PDF inside `resources_iB1000_FGDB.zip` on the download host.
- **CSDI dataset id:** `landsd_rcd_1637223748322_25497` — a `TileIndex` of 3,333 sheet polygons
  (3.9 MB GeoJSON, WGS84), revision `20260716`. Wan Chai is the **same six `11-SW-*` sheets** as the
  building models: **41.8–45.3 MB each, 260 MB total**, ~21 s per sheet. See "Access notes".
- **Content:** the vector topographic map 3D-BIT Level 1 is extruded from — 71 layers,
  **EPSG:2326 (verified)**, levels in mPD. One `Building` polygon layer carries
  `TYPEOFBUILDINGBLOCK` (`T` building / **`P` "Podium Block"** / `OS` open-sided / `TS` temporary),
  `BASELEVEL` / `ROOFLEVEL`, per-level survey-source codes, and `CERTAINTY` — defined by the data
  dictionary as "certainty of the podium polygon". `BUILDINGNAME` relate tables name landmarks.
- **Verified over the Wan Chai region (2026-08-10):** 1,595 blocks — 1,220 `T`, 280 `P`, 76 `OS`,
  19 `TS`. **`BASELEVEL`/`ROOFLEVEL` are 100% filled on every `T` and every `P` block**; nulls live
  only on open-sided (84%) and temporary (68%) structures. Podium heights (roof − base) p50
  **14.6 m**, p10 6.0, p90 19.6. 668 towers (54.8%) intersect a podium block; 247 meet one exactly
  (Times Square: `T` base 75.6 mPD = `P` roof 75.6). ⚠️ The probe's "intersect" is a strict
  positive-area **bounding-box** overlap on per-sheet features — the join's acceptance test
  reproduces these numbers under exactly that frame, and the operative true-geometry counts below
  are smaller for two stacked reasons: boxes overcount diagonal neighbours, and a block clipped by
  a sheet cut counted once per sheet here.
- **Stitched and joined (2026-08-11, `P3-7a`):** a sheet cut **clips** a block — one piece per
  sheet, identical attributes, abutting exactly on the cut line — so `podiums.stitch` groups the
  1,595 pieces into **1,480 logical blocks** (1,134 `T` / 251 `P` / 76 `OS` / 19 `TS`; 104 groups
  span a cut, some three sheets wide). By true polygon overlap (ε = 0.01 m contact), **458 of the
  1,134 logical towers (40.4%) meet a `P` block** — 538 pairs, **228 exact level meets**. Joined
  to the shipped meshes (spatial, depth-gated at 0.3 m against the ~0.1 m registration noise):
  **310 of 1,385 stems carry a data boundary** (291 of them `CERTAINTY`-certain), boundary p50
  13.6 m. HKCEC lands at 52.1 m over base 3.9 from its own `P` block; Times Square's boundary sits
  at exactly 75.6 mPD. All pinned by `test_real_join_reproduces_both_frames`.
- **Alignment with the shipped volumes:** same CRS, and where a block and a mesh correspond 1:1 the
  footprint edges agree to **0.1 m** (Sun Hung Kai Centre podium). Larger bbox deltas are 3D-BIT
  merging tower+podium into one mesh where iB1000 splits blocks — the added information, not
  misregistration.
- **Why:** the podium boundary **in metres, from data** (`Q47`'s third route), and
  `BuiltStructurePolygon` / `UtilityPolygon` usage codes (ventilation shaft, electricity
  substation, water tank, pavilion, swimming pool…) are `W3`'s "utility structure" signal as data.
- ⚠️ **`P` is a partial classification, not a promise** — Central Plaza has no `P` block. Absence
  means no distinct podium block was surveyed, not "no ground band".
- ⚠️ Geometry is MultiPolygon **Z** (M ordinates exist and are dropped by GDAL with a warning).
  ✅ Ingested `P3-7a` (2026-08-10): `gdb.py` decodes polygon-Z, the sheets fetch to
  `etl/sources/hong_kong/topography/` via the `topography` tiled source, and
  `buildings.podium_blocks` reads the `Building` layer per sheet. The verified counts above are
  reproduced from inside the pipeline by `test_real_blocks_reproduce_the_documented_counts`.
  Note the WKB arrives with GDAL's **wkb25D high-bit Z flag**, not the ISO 1000-offset codes —
  the decoder accepts both dialects and refuses M and EWKB-SRID forms.
  ✅ Joined `P3-7a` (2026-08-11): the `podiums` stage stitches, joins, and writes the per-stem
  boundary with mechanism-won provenance to `podiums.json` — a stage intermediate `export.py`
  never names. Contract argument under `Q47` in `DECISIONS.md`.

### ⚠️ NOT SHIPPED — 3D Visualisation Map (Individualised models)

*(Headed "NOT NEEDED" until the `P3-6` amendment. The dataset still ships nothing
and the case against its textures below stands whole — but the mesh-sourced hero
repaint now **consults** one sheet of it at build time: a landmark whose
`source_paint` sets `reference_texture` samples the `…A0` variant's photo atlas
to decide which ribbon strips the real elevation carries, per
`pipeline/landmarks.py`. The stage expects the sheet zip at
`etl/sources/<city>/individualised/<sheet>.zip`, downloaded by hand via the URL
pattern below; the texture votes and is discarded, exactly the shape of read
`P3-7`'s storey-pitch probe established.)*

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-individualised-models
- Same sheet grid and same 3,456-feature index scheme as non-textured. **The download discriminator
  is one character** in the format code — the trailing `0` *is* the non-textured variant:

  ```
  …/api/3d-zip/GLTF0/11-SW-10C.zip?key=…   → non-textured      44 MB
  …/api/3d-zip/GLTF/11-SW-10C.zip?key=…    → individualised   753 MB
  ```

⚠️ **"Individualised" does not mean "per-object separated."** It distinguishes this set from
**tile-based** (one welded photogrammetry mesh per tile), not from non-textured. Both per-building
sets are individuated, and the **building count is identical** — 59 in both on sheet `11-SW-9D`.
Whole-sheet model counts differ only because individualised ships extra object classes.

**The two sets share their building geometry exactly** (verified 2026-07-31). 12 buildings sampled,
12 matched exactly on both triangle and vertex count, spanning 12 to 12,274 triangles. Building IDs
match on a shared stem with the variant in the suffix (`…C0` non-textured, `…A0` individualised),
which makes the stem a **stable cross-dataset building key** — a landmark can be matched between the
two sets by ID with no spatial join. What differs is how the surface is described: non-textured
carries `COLOR_0` in 1 primitive with 0 images; individualised carries `TEXCOORD_0` in 4 primitives
with 4 images. ⚠️ **"4 and 4" is one building, not the rule** — measured across all six sheets,
individualised `BUILDING` is 3,204 primitives and 3,202 images over 2,214 objects, so **1.45 on
average** and many carry exactly one. The load-bearing half of the sentence is the other one: the
non-textured buildings have **no UVs at all**, so there is nothing for `collapse` to corrupt and
nothing to "keep" by weakening a LOD tier.

**So individualised buys texture maps and three extra object classes — not one triangle of extra
shape**, at 15–27× the download. Wan Chai in individualised form is **5.86 GB zipped**, of which
**93–96% is texture**, and the extra ~94 MB of geometry is entirely classes the non-textured set does
not ship at all (`GENERIC` 47.1 MB, `INFRASTRUCTURE(TB)` 36.5 MB, `VEGETATION(TB)` 12.8 MB on one
sheet). Shared classes are equal to within a rounding error; terrain is byte-identical.

### What the extra classes actually are (scouted 2026-08-07)

**Measured over all six Wan Chai sheets, so nobody re-downloads 6.1 GB to learn this.** Read locally
from the cache; the whole scan is a `.gltf` parse and needs none of the imagery.

| Class | Objects | Prims | Triangles | Images | Attributes |
|---|---:|---:|---:|---:|---|
| `GENERIC` | **6** | 470 | **3,946,502** | 470 | POS+N+UV |
| `INFRASTRUCTURE(TB)` | **6** | 191 | 1,554,585 | 190 | POS+N+UV+COL |
| `VEGETATION(TB)` | **6** | 118 | **1,520,184** | 118 | POS+N+UV |
| `BUILDING` | 2,214 | 3,204 | 1,327,925 | 3,202 | POS+N+UV+COL |
| `TERRAIN(TB)` | 6 | 6 | 881,735 | 6 | POS+N+UV |
| `INFRASTRUCTURE` | 77 | 273 | 413,213 | 273 | POS+N+UV |
| `WATERBODY` | 22 | 22 | **605** | 22 | POS+N+UV |

⚠️ **Six objects means one per sheet.** `GENERIC`, both `(TB)` classes and terrain are single welded
blobs per map sheet. Only `BUILDING`, `INFRASTRUCTURE` and `WATERBODY` are per-object.

❌ **`VEGETATION(TB)` is refused, and it is not close.** 1.52 M triangles is **3.5× the entire shipped
city** (434,149 at LOD0) and 1.15× the whole 2,214-building stock — when trees outweigh every
building in Wan Chai, the mesh is photogrammetry, not modelled trees. It is one welded blob per sheet,
so there is no per-tree object to instance, cull or LOD; it carries **no `COLOR_0`**, so the
terrain trick of deriving a flat colour and discarding the image has nothing honest to derive (a
canopy is not one colour per 4 m cell); and decimating it lands on hard rule 1's own reasoning —
*"decimating photogrammetry does not produce low-poly style — it produces blobs."* ⚠️ **The `(TB)`
suffix is not an automatic ban** — `TERRAIN(TB)` ships — but terrain gets away with it by being a
**height field**, which `collapse` has a dedicated path for. A canopy is not.

`GENERIC` (3.95 M triangles) and `INFRASTRUCTURE(TB)` (1.55 M) fail the same way, and the
non-textured set already ships 77 per-object `INFRASTRUCTURE` items.

💡 **`WATERBODY` is the only cheap one — 605 triangles for all 22 objects across the region — and it
is not the harbour.** They are small inland features, 2–137 triangles each, extents of 3–44 m, and
several sit at origin heights of **24.6, 62.4 and 113.6 m**: nullahs, catchwaters and service
reservoirs on the hillside `Q36` measured at **0.000% of all six fixed viewpoints**. So the cheapest
class here may also be the least visible. It is cheap enough to be worth a **tint probe** and it must
have one before it is named — that is `Q36`'s "tint the class before naming it", which has now fired
four times.

❌ **There is no PBR material data in this dataset, and none can be inferred.** Every material is
`pbrMetallicRoughness` with an exporter default and nothing else — `BUILDING` at `roughnessFactor
0.984375` (= 252/256) and `metallicFactor 0.5`, `VEGETATION` at `0.9375` and `0.5`, i.e. half-metal
leaves. There are **no roughness, metallic or normal maps anywhere in the set**, only
`baseColorTexture`. Nor is roughness recoverable from the imagery: it is surface microstructure, and
`Q34` put the ground sample distance at **13–18 cm**, two orders of magnitude above it. Roughness and
metallic are *material constants* with published values — if they are ever wanted they belong as a
column in the `materials:` table beside `reflectance`, cited the same way and portable under hard
rule 3, not derived from a photograph.

⚠️ **And the imagery covers far less of each building than "2,214 matched" suggests.** Sampling six
barycentric points per near-vertical triangle on `11-SW-14B`, area-weighted, with the atlas filler
excluded: **median 14.3% of wall area carries real texels, mean 26.6%, and 50.7% of buildings fall
under 15%.** In a dense district most walls are party walls or occluded, and an aerial only ever saw
the street-facing faces. Any per-building façade claim from this source therefore rests on a small,
**occlusion-biased** sample of that building — worth knowing before another attribute is derived from
it. See `Q37`.

⚠️ **That exclusion is itself incomplete.** The set carries **duplicated flat placeholder panels
that are not grey** — one 4,584-byte 512×512 PNG on 21 buildings, one 1,761-byte panel on 29, and
two further panels that are a *single* colour — and the survey's filler guard rejects only an exact
`R == G == B` tie, so it passes all of them. **97 atlases on 93 of the 2,213 buildings**, and 92 of
those clear `vegetation_max`. The grey half is caught: 2,429 of 3,203 `B`-model atlases hold a grey
modal colour over ≥ 20% of their texels, 1,982 at `#3c3c3c`. So the coverage figure above is an
**over**-estimate of how much real photography there is, by an amount nobody has measured.
See `Q55`.

✅ **`P3-7` read one sheet of it, once, offline — and it still does not ship.** The window-band shader
needed a storey height, and guessing one would have put the wrong floor count on every tower in the
region. So `11-SW-15A` was fetched in individualised form (**1.10 GB**, discarded afterwards), the
wall textures of 515 buildings were autocorrelated down their V axis, and the result — **227 usable
walls on 219 buildings, height-weighted median floor pitch 2.77 m, column pitch p50 2.42 m** — was
authored into `game/tuning/city_facade.tres` as three numbers. `ART_DESIGN.md` already sanctioned
exactly this shape of read for *colour*; this is the same move for spacing.

The probe is **not committed**, deliberately. `deck_error.py`, `overhang.py` and `ground_clearance.py`
are committed because they grade the *shipped bundle* on every build; this graded a 1.10 GB download
that no build has, produced three constants, and would be rewritten rather than re-run. The numbers
and the method are in `DECISIONS.md`, which is what makes it repeatable.

⚠️ **Nothing about that changes the case against shipping the textures**, and the reasons are
structural rather than budgetary: `mesh.collapse` takes UVs from a *cluster representative*, which is
meaningless for an atlas coordinate, and `mesh.merge` refuses textured meshes because two textures
cannot share one primitive. Per-building texture breaks both LOD tiers and the one-draw-call tile —
before the 5.86 GB is even considered.

✅ **This confirms `P3-6` rather than reopening it.** The stated reason to reach for individualised
models was hero landmarks "whose silhouettes LOD1 extrusion destroys" — but that concern belongs to
**3D-BIT00 Level 1**, which is extruded from footprints by definition. The non-textured 3D
Visualisation Map is *not* an extrusion: it already carries the individualised set's exact
silhouette. If hero landmarks need to read as landmarks, the lever is textures or hand-authored
geometry, not this dataset swap — and `PLAN.md`'s `P3-6` already specifies authored geometry.

✅ **`P3-6` would never need the 5.9 GB anyway.** `download.map.gov.hk` returns
`Accept-Ranges: bytes`, so the zip central directory can be read with a range request on the tail and
a single building's `.gltf`/`.bin` pulled by byte range, leaving the JPEGs undownloaded. That is also
how the split above was measured. *(The `P3-6` amendment's photo reference weakens "never" to "one
sheet": the HKCEC repaint samples the JPEGs too, so its build wants `11-SW-9D.zip` whole — 753 MB,
once, cached. A member-range fetcher that pulls just the one building's directory would shrink that
to ~80 MB and is the natural follow-up if a second city makes this routine.)*

💡 **The "non-textured" download is itself 70–81% texture.** Each GLTF0 zip carries one terrain JPEG —
32.5 MB of a 40 MB sheet. Actual building geometry is only ~7–15 MB per sheet.

### ❌ DO NOT USE — 3D Visualisation Map (Tile-based models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-tile-based-models
- Oblique-photogrammetry mesh, 150 m × 150 m tiles, OBJ / OSGB / Cesium 3D Tiles.
- **Why rejected:** a prior public attempt downloaded ~10,000 tiles into Unity and reported **ground
  gaps, level differences, and vehicles baked into the mesh**, concluding it suited flight simulation
  rather than driving. Tiles also carry **no transform metadata**. Decimating photogrammetry does not
  produce low-poly style — it produces blobs, and destroys the semantic separation between road,
  building and street furniture.
- Reference: https://medium.com/@devlog/data-of-3d-visualisation-map-from-hk-landsd-4507ffdef598

### What a sheet contains

Measured on `11-SW-10C`: **44.3 MB** zipped, ~65 MB unpacked, extent ~744 × 603 m. `BUILDING/` 151
buildings, one `.gltf` + `.bin` each, `default_material`, no textures. `INFRASTRUCTURE/` 12 elevated
road structures, each spanning continuously from ~3 m ground to 13–32 m — **that span is the ramp**.
`TERRAIN(TB)/` one mesh, 250,911 verts, **one `.jpg`**.

Three findings that shaped `P1-2`:

1. **Coordinates already match Godot's convention.** Each node's matrix translates to
   `(easting, elevation, -northing)` in HK1980 grid metres, exactly the conversion in
   `ARCHITECTURE.md`. `GameTransform` reduces to subtracting the region origin.
2. **Vertices are unwelded — exactly 3.0 per triangle.** Flat shading is baked in, which is the art
   direction's native form. Never weld on position alone and never regenerate normals; `P1-2` welds
   on *position and facing together*, which is lossless.
3. **"Non-textured" describes the buildings, not the terrain.** Terrain ships with one
   **7531 × 6031** JPEG per sheet — 45 megapixels.

### Measured across all six sheets

The one sheet downloaded by hand turned out to be among the sparsest, so extrapolating from it was
low by 2.4×.

| | `11-SW-10C` | All six sheets |
|---|---|---|
| Buildings | 151 | **2,200** — `11-SW-14B` alone has 720 |
| Infrastructure items | 12 | 74 |
| Terrain meshes / texture | 1 / 39.1 MB | 6 / **224 MB** |

⚠️ **Triangle budget pressure — confirmed, then mitigated.** 612 triangles per building. Clipped to
the region, `P1-2` emits **989k triangles** at its finest tier against a **<300k visible** budget.
Vertex-clustering LOD tiers are what make that fit.

⚠️ **Infrastructure meshes are enormous and unbounded.** One is **1,984 m long in a single mesh**
with 208k triangles. Anything that buckets source meshes spatially has to handle a mesh larger than
its own bucket.

💡 **`INFRASTRUCTURE` is also the *only* height source for off-grade roads.** Road Network v2 carries
no Z, but the map sheets model the elevated structures *including their approach ramps* as continuous
geometry. `P2-7` samples it, which is what puts the flyover carriageway on the flyover: **44 of 45
off-grade edges sampled**, along-edge grade median 2.47%, and \|error\| p90 against the shipped tiles
**4.13 m → 0.095 m**. Two traps, both from taking the *highest* hit:

- **Stacked decks.** `CANAL ROAD FLYOVER` is double-decked, so a naive sampler reads the upper deck
  while the graph edge is on the lower one. Fixed by clustering hits into slabs and walking the edge
  choosing the slab that continues the last, anchored on stations with only one slab.
- **Parapets.** The raised lips sit **off-centre at ±3 to ±6 m**, so a centreline never touches one —
  the apparent "+1.22 m parapet bias" was the genuine gap between the invented height and the deck.

⚠️ **`INFRASTRUCTURE` is not only elevated decks**, so a sampler needs a rejection rule.
`ISLAND EASTERN CORRIDOR`'s 25 m stub at the region corner has no deck at all: half its stations
return nothing and the rest find structure **8.3 m below** the terrain it should be sitting above,
against a next-worst of 0.54 m. `roads.deck.max_below_terrain_m` is that gate.

❌ **It cannot fix tunnels.** A tunnel is a void, so the five level −1 portal nodes have no structure
to sample and never will — and their descent happens **outside the region**, so no height model can
put a run there.

❌ **Terrain does not fit any budget as it ships.** Clipped to the region it is still 404,669
triangles and its six GLBs total **267 MB** — of which **224 MB is the JPEGs**. Over on triangles,
texture memory and bundle size at once.

✅ **The geometry was never the problem — the JPEG was.** `P3-10` ships the terrain
**untextured**, reading the JPEG at build time to derive flat per-vertex colour and then discarding
it: ~88k triangles, 1.5–2.5 MB of geometry, **zero** texture memory, and **no extra draw call**,
because an untextured vertex-coloured surface merges into the same tile primitive as the buildings.
It also removes the objection to decimating it, since clustering smears UVs and there are no longer
any UVs. See `ART_DESIGN.md` "Ground" and `Q18`.

The terrain mesh stays in the pipeline regardless, because it is the **height field** `Q11` is
resolved by sampling: Road Network v2 carries no Z, and ground level in Wan Chai is ~4 m above the
datum rather than 0.

---

## Roads

### ✅ USE — Road Network (2nd Generation)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2
- **Publisher:** Transport Department, part of the Intelligent Road Network Package (IRNP).
- **Update frequency:** monthly. *(We snapshot once — do not track upstream.)*
- **Read as:** the zipped File Geodatabase, through `pyogrio`'s `/vsizip/`. See `Q9` below.
- **Contents:** road centrelines, intersections, bus-only lanes, speed limits, pedestrian zones, turn
  movement restrictions, vehicle restrictions, no-stopping zones, roundabouts, parking access points,
  zebra crossings, toll plazas — **seventeen layers, all in the 17 MB geodatabase.**
- Reference: https://medium.com/@devlog/parsing-hong-kong-road-network-data-5b9b80874704

### ✅ RESOLVED — no true Z, but grade separation IS encoded

Verified directly against the live data. **No fallback needed. The Wan Chai region choice holds.**

**Geometry is 2D.** `CENTERLINE.gfs` declares `<GeometryType>2</GeometryType>` with
`<SRSName>EPSG:2326</SRSName>`; every `gml:posList` carries `srsDimension="2"`. There are **no Z
ordinates**. In the geodatabase, centrelines are `Measured MultiLineString` and GDAL drops the M
ordinate on read with a warning.

**An integer `ELEVATION` attribute encodes the level.** Measured on the region: 0 (736 edges), 1
(45), **−1 (15)** — the Cross-Harbour Tunnel and the Central–Wan Chai Bypass. This is the standard
GIS idiom for grade separation — an ordinal level, like OSM's `layer` tag — not a measured height.
**The defensive `-1` mapping added before any negative was seen turns out to be load-bearing.**

**Implementation:** map `ELEVATION` → an authored deck height in city config as an offset from
**ground level**, not from the vertical datum (`Q11`, `roads.ground`). Since `P2-7` that offset is
only the *fallback*: where the map sheets cover the structure, the real deck is sampled instead.

⚠️ **`ELEVATION` must not key nodes** — "two edges may only form a junction if their `ELEVATION`
values match" is right about *crossings* and wrong about junctions, and applying it breaks the
network. Every one of the 36 endpoints where two levels meet is a **ramp touching down**, so keying
nodes on the level takes the region from 6 connected components to **24**, cutting a 163-node
elevated island adrift. The hazard it is aimed at never arises here, because nodes are formed only
where centrelines share an **endpoint**, and a flyover crossing a street shares nothing with it.
`P1-3`.

### What `P1-3` measured in the geodatabase

Read with `pyogrio` (GDAL 3.12.4) through `/vsizip/`, clipped to the Wan Chai region by OGR spatial
filter: **796 centrelines, 529 intersections, 217 turns, 83 speed limits, 14 bus lanes.**

| Finding | Measurement | Consequence |
|---|---|---|
| Endpoints coincide **exactly** | 601 distinct at full float precision; nearest *distinct* pair **2.26 m** apart | Nodes by coordinate identity. No snapping tolerance to tune — but it must be at least ~1 mm: two clusters differ in the last bits and split below that |
| Geometry is **wildly over-densified** | one 51.7 m centreline carries **54,330 vertices** (median segment 0.4 mm); five features hold 132k of the region's 176k | Douglas–Peucker at 0.2 m is a correctness measure, not a size optimisation. 175,610 → 3,553 vertices, worst deviation 0.1997 m |
| `ROUTE_ID` is **1:1 with the centreline** | 796 distinct values across 796 features | `SPEED_LIMIT` and `BUS_ONLY_LANE` join by key. No linear referencing needed, despite both being modelled as route events |
| Speed limits cover **under 10%** | 77 of 796 edges, all 70 or 80 km/h, as free text with units | Hong Kong signs only exceptions to the 50 km/h urban default, so the default must come from city config |
| **`NSR` is the kerbside yellow lines, and `VEHICLE_TYPE` is the field that decides how many** | **579 features / 44,220 m** in region, **kerb-referenced** (median **2.76 m** off the nearest centreline, p99 8.24 m, 0% on it). ⚠️ **Only `VEHICLE_TYPE = 1` "all motor vehicles" is a painted line — 33,074 m.** `2`/`3`/`4` (taxis, PLBs, goods vehicles, 2,822 m) are signs; `5` "Others" (8,323 m) names no class at all and is **refused**. `TIME_ZONE` separates double from single outright: `1` is 24 hours (27,118 m, double), `2`–`5` are posted hours (5,956 m, single). `EFFECTIVE_DAY` is uniformly `1` in region and carries nothing. `REMARKS` is `None` for 31,919 m of the 33,074 and **never mentions taxis** within `VEHICLE_TYPE = 1`. `ONSTREETPARK` carries **607** bays as the complement | Ingested by `pipeline/kerbside.py` since `P3-13`, and it is the **one overlay that is not a key join**: `NSR` carries `ST_CODE_1..6` — street codes — where `SPEED_LIMIT` and `BUS_ONLY_LANE` carry `ROUTE_ID`, so it is linear-referenced onto the finished graph. **26,065 m over 650 edge sides** survive; 1,736 m of the region's samples are overlapping features and are deduped rather than counted twice. ⚠️ The layer is a *Measured* MultiLineString and its M values are **not** a join — there is no route key to resolve them against |
| **Lane counts do not exist** | no lane attribute in any field of any layer | `roadgraph.json`'s `lanes` is authored policy keyed on speed limit, not published data |
| Dual carriageways are **opposed one-way pairs** | 6 places where two one-way edges share both endpoints in opposite directions, **1.96–3.85 m** apart; three of them are Lockhart Road | Lockhart Road is two-way *modelled as two one-ways*. A **lower bound** — carriageways that do not share both endpoints are not counted |
| Turn geometry is a **hint, not the truth** | `EDGE1END` names an end that touches the second edge in 213 of 217; in the other 4 the *opposite* end coincides exactly | Take the shared node; use the field only to break ties. All 217 then resolve |
| The **null sentinel has four spellings** | `-99`, plus three using full-width digits with an en-dash or full-width hyphen (`–９９`, `－９９`, `-９９`) | Normalise NFKC *and* fold Unicode dashes before comparing. A raw string compare catches one of four |

**Feature identity is the FGDB `OBJECTID`**, which OGR returns as the feature id. `TURN` points at
centrelines through `EDGE(1-8)FID` and `INTERSECTION` through `RD_ID_1..10`; both are OBJECTIDs, so a
reader that renumbers features on a filtered read resolves every restriction onto the wrong roads.

**Bilingual street names ship in the source** — `STREET_ENAME` / `STREET_CNAME`, plus `ALIAS_*`.
Confirmed present for the region. **We do not need to hand-author road names.**

**Attributes `P1-3` reads but does not emit**, recorded so they are not rediscovered: `TURN` carries
`EXC_VEH_TYPE` / `INC_VEH_TYPE` (vehicle classes the restriction does *not* apply to — `TX` = taxi,
and one restriction in the region excludes taxis), `PART_TIME_REST`, `EFF_ALL_DAYS` and
`OTHER_REST_TYPE`. `roadgraph.json` has no field for any of them. They matter for `P3-3` and `P3-8`,
and adding them is a schema change on both sides.

### `Q9` — the geodatabase, and every GML dropped

⚠️ **The two published formats are redundant, and one is 31× larger.** `RdNet_IRNP.gdb.zip` is
**17.4 MB and contains all seventeen layers**; the per-layer GML conversions of the same content
total **539 MB**, `CENTERLINE.gml` alone being 486 MB because GML spends most of its bytes on XML
tags. `hong_kong.yaml` now lists only the geodatabase and the data specification PDFs — **a clean
fetch is 522 MB lighter.**

Kept as a record of what the publisher offers, not as things to fetch:

| Resource | URL |
|---|---|
| Full FGDB (the one we use) | `https://static.data.gov.hk/td/road-network-v2/RdNet_IRNP.gdb.zip` |
| Data dictionary | `https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip` |
| Consolidated file list | `https://static.data.gov.hk/td/road-network-v2/dataspec/file_list.csv` |
| Per-layer GML | `https://static.data.gov.hk/td/road-network-v2/{CENTERLINE,INTERSECTION,BUS_ONLY_LANE,ROUNDABOUT,PEDESTRIAN_ZONE,PROHIBITION,NSR}.gml` |

The CKAN API enumerates all 61 resources:
`https://data.gov.hk/en-data/api/3/action/package_show?id=hk-td-tis_15-road-network-v2`

---

## Fares and points of interest

Both datasets are read by `P1-5`. **data.gov.hk lists only a portal link for each — no direct file.**
The downloadable URL is the CSDI `file-api`, the same endpoint the buildings sheet index uses:

```
https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=<id>&format=geojson
```

Unlike the buildings index these carry **no API key and need no `layer_name`**, so the URLs live in
`hong_kong.yaml` directly. Two properties shared by both matter to the pipeline:

- **`crs` is absent**, which is CRS84 per RFC 7946 — WGS84 lon/lat. Declared explicitly in config
  rather than assumed, like every other datum in this project.
- **Positions are quantised to whole metres on the HK1980 grid.** Published as lon/lat to ten decimal
  places, but every point round-trips to an exact metre. So a fare node carries about half a metre of
  its own positional uncertainty.

### ✅ USE — Taxi Stands

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_37-taxi-stands
- **CSDI dataset id:** `td_rcd_1697081907714_17556` — 518 features, 343 KB. Updated twice a year.
- **Gameplay use:** pickup hotspots. The *Cross Harbour* category becomes a distinct premium fare
  type that terminates at the tunnel approach — a fare that only makes sense in Hong Kong.

**⚠️ `Status_EN` is free text, not an enum.** Sixteen spellings territory-wide, carrying the licensing
category *and*, in eight cases, an operating-time restriction after an embedded newline:

| Count | `Status_EN` | → |
|---:|---|---|
| 312 | `Urban Taxi Stand` (+4 more with a time note) | `urban` |
| 75 | `Both of Urban and NT Taxi Stand` (+1 `Urban and NT Taxi Stand`) | `urban_and_nt` |
| 68 | `NT Taxi Stand` (+1 with a time note) | `nt` |
| 30 | `Cross Harbour Taxi Stand` (+3 with a time note, +1 `Urban and Cross Harbour Taxi Stands`) | `cross_harbour` |
| 21 | `Lantau Taxi Stand` | `lantau` |

Matching is **first-hit-wins over substrings**, so rule order is load-bearing: `Urban and NT` must
precede `NT Taxi Stand`, which must precede `Urban`. `load_city` refuses a table where an earlier
rule would always shadow a later one, and `test_config.py` pins all sixteen spellings — the Wan Chai
region only ever exercises two of them.

`Q14`: the operating-time restrictions are **discarded**. There is no contract field for them and no
consumer; a part-time cross-harbour stand is currently modelled as a full-time one.

### ✅ USE — Taxi Pick-up & Drop-off Points

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_38-taxi-pick-up-drop-off-points
- **CSDI dataset id:** `td_rcd_1697082382328_14459` — 275 features, 192 KB. Updated twice a year.
- **Gameplay use:** legal drop-off targets; denser than stands.

`Status_EN` here has only two values, and the distinction is gameplay-relevant: **`Taxi PU/DF`** (209)
may be hailed at and delivered to; **`Taxi DF`** (66, a quarter of the dataset) is **drop-off only**.
Carried into `fares.json` as `pickup`/`dropoff` rather than flattened.

### Names, in both datasets

`Location_EN` / `Location_TC` are populated on **every** feature in both datasets — the acceptance
criterion for bilingual names is satisfied by the source, not by a fallback. Two traps:

- **31 of the 793 names contain embedded newlines**, wrapping a long place name across lines.
  Collapsed to single spaces by `clean_text`; a fare node's name goes on the HUD.
- **98 names use full-width brackets** (`（1）`). `clean_text` returns **NFC** and folds to NFKC only
  for the null-sentinel comparison, because NFKC is a *compatibility* fold and would rewrite those as
  ASCII — wrong typography in Chinese.

`Location_SC` (simplified) is not read — Hong Kong sets traditional. It is also the only field in
either dataset with an observed data-entry error: one `Taxi DF` row carries traditional Chinese in
the simplified column.

### Snapping fare nodes to the road graph

Measured across the region's 29 points, and the reason no tie-breaking rule exists:

- Distance to the nearest centreline **1.18–8.37 m** (median 3.2 m) — about half a carriageway, which
  is what a kerbside point against a centreline graph should measure.
- Margin over the *second* nearest edge: **at least 4.28 m**. Never ambiguous.
- **28 of the 28** nodes whose snapped edge has an English name land on a street whose name appears in
  that point's own free-text `Location_EN`. The geometry pipeline never reads that prose, so this is
  independent corroboration rather than a tautology.
- Every winner is at **elevation level 0**. One level-1 edge appears as a runner-up, losing by 7 m.
  `Q15`: the sources are 2D, so a stand under a flyover has nothing in it to prefer the street below
  over the deck above. Plan distance is the only defensible measure.

> **Region note:** Hong Kong Island uses **red urban taxis**. Green (NT) or blue (Lantau) livery in
> this map would read as wrong to any local player.

---

## Coordinate systems

| Item | Value |
|---|---|
| Source CRS | **HK1980 Grid System, EPSG:2326** (Transverse Mercator) |
| Vertical datum | Hong Kong Principal Datum (HKPD) |
| Game space | Local ENU metres, **origin at region NW corner** (`Q7`) |
| Tile-based model quirk | Drawn in **HK80 coordinates minus 800,000** (rejected dataset, recorded for completeness) |

```
game_x =  (easting  - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing - origin_northing)
```

The `-Z` is forced by handedness; the *origin corner* was the free choice, and it is north-west so the
region lands in the positive quadrant. Reasoning in `ARCHITECTURE.md`. **Keep this conversion in
`etl/pipeline/crs.py` only.** Nothing else in the pipeline may assume EPSG:2326.

---

## Region of interest (PoC)

**Wan Chai → Causeway Bay north-shore corridor.**

| Bound | Value |
|---|---|
| West / East | 114.172 E / 114.188 E |
| South / North | 22.276 N / 22.284 N |
| Approx. size | 1.65 km × 0.9 km ≈ **1.5 km²** |
| Tiles @ 150 m | 66 computed, 65 with content |
| **Datum of the bounds above** | **WGS84 — confirmed against real geometry** |

### ⚠️ The datum of these bounds is load-bearing

HK1980 and WGS84 differ by **~304 m on the ground** in Hong Kong — far more than the ~10 m people
expect. These four numbers were authored without stating a datum, and the two readings select
**different sheets**: WGS84 gives a contiguous `11-SW` block, HK1980 swaps two of the six. A third of
the region, decided by an unstated assumption.

**Resolved by measurement, not inference.** Sheet `11-SW-10C` was downloaded and its building
positions compared against both readings:

| | Easting | Northing |
|---|---|---|
| **Actual building positions** | 836006–836752 | 815600–816173 |
| Sheet bbox **if index is WGS84** | 836000–836750 | 815600–816200 |
| Sheet bbox if index is HK1980 | 836252–837003 | 815431–816031 |

The terrain node sits at exactly (836375, 815900) — the WGS84-projected sheet centre to the metre.
`hong_kong.yaml` therefore declares `crs.geodetic: EPSG:4326`, and the loader **refuses to run
without an explicit datum.**

### Covering sheets

Six 1:1000 sheets cover the region, ~44 MB each — **~280 MB** of source download:

```
11-SW-9D    11-SW-10C   11-SW-10D
11-SW-14B   11-SW-15A   11-SW-15B
```

**Do not hardcode this list.** `fetch.py` derives it by intersecting the region bounds with the
fetched sheet index, so a bounds change or a second city re-derives it for free — and the derived set
matches these six exactly, which is the first end-to-end confirmation that the bounds, the datum and
the index agree.

Key roads: Gloucester Road, Harbour Road, Hennessy Road, Lockhart Road, Jaffe Road, Johnston Road,
Queen's Road East, Canal Road East/West + flyover, Yee Wo Street, Percival Street.

Natural map edges: Victoria Harbour (north), the escarpment toward Kennedy Road / Mid-Levels (south),
Admiralty (west), Victoria Park (east).

---

## Access notes

### Roads — fully scriptable ✅

Direct static URLs, enumerable via the data.gov.hk CKAN API. No key, no portal, no account.

### Buildings — fully scriptable ✅

⚠️ **The CKAN resource list is not the whole story, and reading it alone is what makes buildings look
unautomatable.** It genuinely does only point at interactive portals. **Open the portal's own
Downloads panel.**

**The sheet index is the API.** The CSDI portal's Downloads panel serves the non-textured dataset as
ordinary GIS vector formats, not as 3D models. What you get is a **territory-wide index of 3,456
sheet polygons**, each carrying direct download URLs for the models themselves:

| Property | Example |
|---|---|
| `SHEETNO` | `11-SW-10C` |
| `Format_glTF` | `https://download.map.gov.hk/api/3d-zip/GLTF0/11-SW-10C.zip?key=…` |
| `Format_FBX` / `Format_MAX` | `…/api/3d-zip/FBX0/…`, `…/api/3d-zip/MAX0/…` |
| `REVISIONDATE` | `20260424` — genuinely per sheet |

- **One public key is shared by all 3,456 sheets** — not per-user, not per-session. It is baked into
  an index anyone can download.
- ⚠️ **Do not hardcode the key into `hong_kong.yaml` or any committed file.** `fetch.py` reads URLs
  out of the index at run time, and everything it records passes through `redact()`. The index is the
  source of truth, and a rotated key then costs nothing.
- `REVISIONDATE` is per sheet — used as the cache key, so re-runs are idempotent and a forced
  re-snapshot costs **3.2 MB instead of 265 MB**.
- Index CRS is **WGS84** (GeoJSON with `crs: null`, i.e. CRS84 per RFC 7946).

**The index itself has a direct URL**, which is what makes a fresh clone able to fetch without anyone
visiting the portal. Verified to return bytes **identical by SHA-256** to the portal's own download
button. No key, no session, no account:

```
https://portal.csdi.gov.hk/csdi-webpage/file-api
    ?dataset_id=landsd_rcd_1742809441342_98380
    &format=geojson
    &layer_name=Nontextured_models
```

✅ **The endpoint is parameterised by dataset, format and layer rather than being one-off, and that
generalises** — verified by swapping in the individualised dataset
(`landsd_rcd_1671676915450_88604`, `layer_name=Individualised_models`), which returned its own
3,456-feature index with no key. Layer names come from the ISO 19139 record — grep it for
`layer_name=` rather than guessing the capitalisation:
`https://portal.csdi.gov.hk/geoportal/rest/metadata/item/<datasetId>`. That record also advertises
WFS, WMS and an ArcGIS `FeatureServer` for server-side bbox queries, if the 3.2 MB whole-index
download ever becomes inconvenient. It has not.

### iB1000 (topographic map) — fully scriptable ✅, but only via the TileIndex

The same index-is-the-API pattern, with one inversion: **the per-sheet URLs work and the portal's
own download links do not** (verified 2026-08-10).

- Index: `file-api?dataset_id=landsd_rcd_1637223748322_25497&format=geojson&layer_name=TileIndex` —
  3,333 sheet polygons, WGS84, no key. Properties: `SHEETNO`, `REVISIONDATE`, and per-sheet `FGDB` /
  `GML` / `DGN` / `DWG` / `TIFF` download URLs — **no API key in any of them**, so nothing to redact.
- Each `FGDB` property is
  `https://open.hkmapservice.gov.hk/OpenData/directDownload?productName=iB1000&sheetName=T<SHEETNO>&productFormat=FGDB`
  → a plain HTTP 200 zip, no session, no redirect — verified on all six Wan Chai sheets. The
  2026-08-10 scout's intranet-redirect caveat was about the human download *form*, not these URLs.
- ❌ The `portal.csdi.gov.hk/csdi-webpage/download/common/<hash>` links in the ISO record (full-set
  FGDB, GPKG, GeoJSON, GML, SHP, KML) return **403 to scripted GET**, and the seamless full-set
  `directDownload` still 504s. Per-sheet via the TileIndex is the only verified scriptable route —
  and at 260 MB per region it is enough.
- Read with pyogrio through `/vsizip/<zip path>/<SHEETNO>/<SHEETNO>.gdb`. The probe that verified
  this (`Q47`) is uncommitted per `P3-7`'s pattern; the *pipeline* ingestion that replaced it
  landed as `P3-7a` (2026-08-10) — `topography` tiled source, `podiums:` block, sheets cached
  under `etl/sources/hong_kong/topography/`.
- ⚠️ **`open.hkmapservice.gov.hk` serves its TLS chain without the issuing intermediate**
  (Hongkong Post e-Cert SSL CA 3 - 17) — leaf and root only. Browsers and curl chase the gap via
  the certificate's AIA URL; Python's OpenSSL does not, so a plain `urlopen` fails
  `CERTIFICATE_VERIFY_FAILED` against an otherwise-trusted chain. The intermediate is committed at
  `etl/config/certs/` (provenance and fingerprint in the PEM header) and declared in
  `hong_kong.yaml`'s `extra_cas`, which `fetch.py` loads as an additional verify anchor —
  verification is completed, never relaxed. Expires 2032-06-03.

**Portal entry points** (for a human re-checking the index):

- Non-textured: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1742809441342_98380`
- Individualised: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1671676915450_88604`
- 3D-BIT00: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637306559892_42396`
- iB1000: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637223748322_25497`

**The Cesium 3D Tiles API remains irrelevant.**
`https://data.map.gov.hk/api/3d-data/3dtiles/{sheet}/tileset.json` serves the tile-based
photogrammetry variant we rejected. We do not need it, and we do not need a key from
`3dmap@landsd.gov.hk`.
