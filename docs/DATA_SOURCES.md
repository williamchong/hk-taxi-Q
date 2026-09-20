# Data Sources

All facts below were verified against primary sources. **Do not re-research these** — if something
turns out wrong, correct it here and record the finding in `DECISIONS.md`.

## Licence

All datasets below are published via DATA.GOV.HK and the CSDI Portal. Both grant the same six acts —
*browse, download, distribute, reproduce, hyperlink to, print* — for **commercial and non-commercial
use, free of charge**, with no usage limit, quota or volume cap. Read verbatim 2026-08-02.

- **Attribution is stronger than naming a source**: acknowledge the Government's and the relevant
  organisations' *ownership of the intellectual property rights*, and name **both** portals.
- The indemnity is real and broad. Data is supplied "AS IS".
- ℹ️ "Adapt", "modify" and "derivative" appear in neither portal's terms. Expected: the restricted
  act for artistic works is *copying*, granted here as **reproduce**. Not an alarm.

`LICENSING.md` is canonical — operative clauses, what may be relicensed, open legal items. Do not
restate the terms here.

### Required credits-screen text (draft)

> Contains geospatial data from the Lands Department, the Transport Department and the Highways
> Department of the Government
> of the Hong Kong Special Administrative Region, obtained via DATA.GOV.HK and the Common Spatial
> Data Infrastructure (CSDI) Portal. **The Government of the HKSAR and the relevant organisations own
> the intellectual property rights in that data.** Used under the DATA.GOV.HK and CSDI Portal Terms
> and Conditions of Use. The Government of the HKSAR does not endorse this product.

⚠️ The ownership sentence is not optional.

A second, non-government attribution is required since `P3-24` (`Q79`): the build bundles a typeface
under CC BY 4.0, whose attribution must travel with **every distributed copy**. Add to the same
screen:

> Street names are set in **Free HK Kai** (自由香港楷書) © 2016 Free Hong Kong Fonts, used under the
> Creative Commons Attribution 4.0 International licence.

🔴 **Not yet discharged: there is no credits screen.** `game/scripts/ui/` holds only the driving HUD,
so the text exists only here and in `game/assets/authored/fonts/LICENSE` while the font ships in the
PCK. This is a licence gap; build the screen before publishing anything beyond a playtest link.
`LICENSING.md`, `Q79`.

> **Legal note:** because this ships as a commercial product, have a Hong Kong IP lawyer sight-check
> landmark depiction and the credits text before launch. **Landmark depiction is the top item** —
> the data terms cleared the licensing question; building depiction is the one with a plausible
> adverse answer.

---

## Buildings

### ✅ USE — 3D Visualisation Map (Non-textured models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-non-textured-models
- **Publisher:** Lands Department. **Formats:** MAX, FBX, **glTF** — one zip per 1:1000 sheet.
- **Content:** geometry and position only — no textures on buildings. Terrain ships textured.
- **Coverage:** whole territory, 3,456 sheets. Fully scriptable — see "Access notes".
- **Why:** flat-shaded extruded volumes are exactly the target art style.
- ⚠️ Decimation is needed at 612 triangles per building — see the budget note below.

### 🚫 NAMED AND NEVER ADOPTED — 3D Spatial Data (3D-BIT00), Level 1

`Q100`: was a locked decision and was never declared, fetched or read. Its cross-check role is
filled by **iB1000** (below), the map it is extruded from (`P3-7a`/`Q47`).

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-development-hkms-digital-3d-bit00
- **Formats:** MAX, 3DS, FBX, VRML.
- **Level 1 (verified):** every building and/or podium with a B1000 footprint over **4 m²**,
  extruded from its footprint between base and top level, untextured.

### ✅ USE — iB1000 Digital Topographic Map (FGDB)

- **Portal:** `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637223748322_25497`
- **Publisher:** Lands Department (Survey and Mapping Office). **Formats:** FGDB, GML, DGN, DWG —
  one zip per 1:1000 sheet, laid out `<SHEETNO>/<SHEETNO>.gdb`. Schema authority: *iB1000 Data
  Dictionary — FGDB* v1.2 PDF inside `resources_iB1000_FGDB.zip` on the download host.
- **CSDI dataset id:** `landsd_rcd_1637223748322_25497` — a `TileIndex` of 3,333 sheet polygons
  (3.9 MB GeoJSON, WGS84), revision `20260716`. Wan Chai is the same six `11-SW-*` sheets as the
  building models: 41.8–45.3 MB each, **260 MB total**. See "Access notes".
- **Content:** 71 layers, **EPSG:2326 (verified)**, levels in mPD. The `Building` polygon layer
  carries `TYPEOFBUILDINGBLOCK` (`T` building / `P` "Podium Block" / `OS` open-sided / `TS`
  temporary), `BASELEVEL` / `ROOFLEVEL`, per-level survey-source codes and `CERTAINTY` ("certainty
  of the podium polygon"). `BUILDINGNAME` relate tables name landmarks.
- **Wan Chai:** 1,595 pieces — 1,220 `T`, 280 `P`, 76 `OS`, 19 `TS`. `BASELEVEL`/`ROOFLEVEL` are
  100% filled on every `T` and `P`; nulls only on `OS` (84%) and `TS` (68%). Podium height p50
  **14.6 m** (p10 6.0, p90 19.6). Pinned by `test_real_blocks_reproduce_the_documented_counts`.
- ⚠️ **A sheet cut clips a block** — one piece per sheet, identical attributes. `podiums.stitch`
  groups the 1,595 into **1,480 logical blocks** (1,134 `T` / 251 `P` / 76 `OS` / 19 `TS`). By true
  overlap (ε = 0.01 m), 458 of 1,134 towers (40.4%) meet a `P` block, 228 at an exact level. Joined
  to the shipped meshes (depth-gated at 0.3 m against ~0.1 m registration noise): **310 of 1,385
  stems carry a data boundary**, p50 13.6 m. Pinned by `test_real_join_reproduces_both_frames`,
  which also reproduces the looser bounding-box frame (668 towers, 247 exact).
- **Alignment:** same CRS as the shipped volumes; 1:1 footprint edges agree to **0.1 m**. Larger
  bbox deltas are the 3D set merging tower+podium where iB1000 splits them.
- **Why:** the podium boundary in metres, from data (`Q47`). `BuiltStructurePolygon` /
  `UtilityPolygon` usage codes are a "utility structure" signal as data.
- ⚠️ `P` is a partial classification — Central Plaza has no `P` block. Absence means none surveyed.
- ⚠️ Geometry is MultiPolygon **Z** (GDAL drops M with a warning). The WKB arrives with GDAL's
  **wkb25D high-bit Z flag**, not ISO 1000-offset codes; `gdb.py` accepts both and refuses M and
  EWKB-SRID.
- **Ingest:** `topography` tiled source → `etl/sources/topography/`; `buildings.podium_blocks` reads
  `Building` per sheet; the `podiums` stage writes `podiums.json`, a stage intermediate `export.py`
  never names.

#### ⚠️ The road layers of this file, surveyed by `Q57` (2026-08-20) — three now in use

The pipeline reads `Building` (podium join), `CartoTransLine` (`TW` tramway, `RM` carriageway
survey) and `UtilityPoint` (lamps). Domain codes quoted from the data dictionary; counts are the six
Wan Chai sheets.

| Layer / code | Count | Use |
|---|---|---|
| `CartoTransLine`, `RM` — *"Road margin"* | 56,286 segments | **The carriageway edge**; a publisher of the width survey since `Q95`. ⚠️ A raw perpendicular probe over-reads: it escapes through junction mouths and crosses both halves of a dual |
| `CartoTransLine`, `RMU` — *"Road margin under elevated structures"* | 415 / 9,232 m | The same edge under a deck |
| `CartoTransLine`, `TW` — *"Tramway"* | 168 parts / 12,292 m (132 / 9,912 m in region) | **The tram rails** (`P3-14`). 🔴 A part is **one rail**, not a track centreline (`Q58`): 56.5% of cross-sections cross exactly four parts, neighbour gap modal at 1.05–1.20 m. `RailwayPolygon` `RAILWAYTYPE = TW` carries the same extent as 62 polygons |
| derived from `TW` (`Q58`), 1,698 four-rail sections | gauge p10 **1.066** / p50 1.124 / p90 1.221 m; track separation p50 **2.597** m | Published gauge is 1.067 m. ⚠️ The tramway is mostly **not** on the drawn carriageway: only 18.8% of sections have both tracks on the ribbon (Hennessy 1.5%), because the reserve runs between two one-way ribbons |
| `CartoTransLine`, `FY` / `FYU` / `TUR` | 89 / 16 / 14 | Flyover, flyover-under-flyover, tunnel — a second opinion on `ELEVATION`. Not in use |
| `CartoPedLine`, `PA` — *"Pavement margin"* | 2,945 / 50,904 m | The footway edge. Not in use |
| `CartoPedLine`, `STP` / `FBR` / `SWY` / `CWY` | 3,577 / 384 / 18 / 85 | Steps, footbridge, subway, covered walkway. Not in use |
| `StreetCentreLines`, `STREETTYPE` | 794 | Carries `ST_CODE`, the same street code `NSR` joins on — a second key, not a second graph |
| `BUILDINGNAME` / `ADDRESS` / `Street_Code` | 306 / 422 / 112 per sheet | Bilingual building names and addresses; bears on fare destinations |

⚠️ **Three-letter codes are traps.** `TW` is *Tramway* here and *tactile warning strip* in Traffic
Aids Drawings; `RM` is *Road margin* here and a road-marking prefix there.

#### The street-furniture layers of this file (`P3-26`, 2026-08-27)

| Layer / code | Six sheets | In region | Use |
|---|---|---|---|
| **`UtilityPoint`, `UTILITYPOINTTYPE = LPO`** | 2,096 | **1,263** | **Lamp posts** — `pipeline/lamps.py` → `lamps.glb` |
| `UtilityPoint`, `FWH` / `SWH` / `EPO` | 365 / 39 / 2 | 215 / 26 / 2 | Hydrants, poles. Not in use |
| `RoadAssetPoint` `RAC`/`BAC`; `BuiltStructurePoint` | 11 / 3; 30 | 5 / 2; 5 | Not in use |
| `Tree`, `TREETYPE` | 40 | 9 (`OVT` ×8) | 🔴 **Not a street canopy**: individually surveyed Old and Valuable Trees — a landmark layer. `LandCoverVector2` is 0 features. Not in use |

- ✅ `UTILITYPOINTTYPE` has a **published coded-value domain inside the geodatabase** (`LPO - Lamp
  post`), stronger than `DTAD_RAILING_LINE.LINETYPE` (`Q60`) or `DTAD_TRAFFIC_LIGHT_PT.REFNAME`
  (`Q76`), which have none. `Q101` measured that `dTAD_IRNP.gdb.zip`'s 58 tables hold no coded
  domains at all.
- ⚠️ The layer publishes a position and nothing else: no level, angle, height, lantern type or arm
  direction. Geometry Z is `0.0` on all 1,263 (file convention — `SpotHeight` does the same). Every
  dimension `lamps.py` draws is authored. `STATUS` is `E` on all.
- ⚠️ `UtilityNumber` (lamp-post numbers) is a related table via `LampPostHasNumber`. Not in use
  (`Q65`'s effort-per-plate refusal).
- ⚠️ `LPO` is not `DTAD_GIPOLE_PT`, a different pole population this stage does not read.
- Spacing p10 7.09 / p50 **16.74** / p90 27.63 m, zero coincident pairs. 64.1% (810) were surveyed
  inside the drawn carriageway (pre-`Q95` multiplier; re-opened by `Q101`), so they are registered
  onto the drawn kerb (`Q82`).

### ⚠️ NOT SHIPPED — 3D Visualisation Map (Individualised models)

Ships nothing. **Consulted at build time** by the `P3-6` hero repaint: a landmark whose
`source_paint` sets `reference_texture` samples the `…A0` photo atlas in `pipeline/landmarks.py`.
The sheet zip is downloaded by hand to `etl/sources/individualised/<sheet>.zip` (HKCEC:
`11-SW-9D.zip`, 753 MB).

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-individualised-models
- Same sheet grid and index scheme. **The download discriminator is one character** — the trailing
  `0` is the non-textured variant:

  ```
  …/api/3d-zip/GLTF0/11-SW-10C.zip?key=…   → non-textured      44 MB
  …/api/3d-zip/GLTF/11-SW-10C.zip?key=…    → individualised   753 MB
  ```

- ⚠️ "Individualised" distinguishes it from **tile-based**, not from non-textured. Both per-building
  sets share building geometry **exactly** (12 of 12 sampled match on triangle and vertex count).
  IDs share a stem with the variant in the suffix (`…C0` non-textured, `…A0` individualised) — a
  **stable cross-dataset building key**.
- Non-textured buildings carry `COLOR_0` and **no UVs at all**; individualised carries `TEXCOORD_0`
  and images (3,204 primitives / 3,202 images over 2,214 buildings).
- It buys textures and three extra classes, not one triangle of shape: Wan Chai is **5.86 GB**
  zipped, 93–96% texture.
- ❌ **Textures cannot ship**, structurally: `mesh.collapse` takes UVs from a cluster
  representative, and `mesh.merge` refuses textured meshes — it breaks both LOD tiers and the
  one-draw-call tile.
- ❌ **No PBR data**: every material is an exporter default (`BUILDING` roughness 0.984375, metallic
  0.5); only `baseColorTexture` exists. Roughness is not recoverable from 13–18 cm imagery (`Q34`).
  If wanted, author it in the `materials:` table beside `reflectance`.
- ⚠️ **Imagery covers little of each building**: on `11-SW-14B`, median **14.3%** of wall area
  carries real texels (mean 26.6%), occlusion-biased toward street faces (`Q37`).
- ⚠️ **Filler panels**: 2,429 of 3,203 atlases hold a grey modal colour over ≥ 20% of texels, and
  duplicated non-grey placeholder panels exist. `filler_colours` rejects any colour holding ≥ 20% of
  an atlas; `facade_survey.py --all --filler-report` publishes 100 buildings on 132 atlas slots.
  It remains a floor (`Q55`).
- `P3-7` read `11-SW-15A` once offline (1.10 GB, discarded): 227 usable walls on 219 buildings,
  floor pitch **2.77 m**, column pitch p50 **2.42 m**, authored into `game/tuning/city_facade.tres`.
  The probe is uncommitted; the method is in `DECISIONS.md`.
- `download.map.gov.hk` returns `Accept-Ranges: bytes`, so a single building can be pulled by byte
  range; a member-range fetcher (~80 MB instead of 753 MB) is the follow-up if this becomes routine.
- 💡 The "non-textured" zip is itself 70–81% texture: one terrain JPEG, 32.5 MB of a 40 MB sheet.

### What the extra classes actually are (scouted 2026-08-07)

All six Wan Chai sheets, individualised set:

| Class | Objects | Prims | Triangles | Images | Attributes |
|---|---:|---:|---:|---:|---|
| `GENERIC` | **6** | 470 | **3,946,502** | 470 | POS+N+UV |
| `INFRASTRUCTURE(TB)` | **6** | 191 | 1,554,585 | 190 | POS+N+UV+COL |
| `VEGETATION(TB)` | **6** | 118 | **1,520,184** | 118 | POS+N+UV |
| `BUILDING` | 2,214 | 3,204 | 1,327,925 | 3,202 | POS+N+UV+COL |
| `TERRAIN(TB)` | 6 | 6 | 881,735 | 6 | POS+N+UV |
| `INFRASTRUCTURE` | 77 | 273 | 413,213 | 273 | POS+N+UV |
| `WATERBODY` | 22 | 22 | **605** | 22 | POS+N+UV |

- Six objects means one welded blob per sheet. Only `BUILDING`, `INFRASTRUCTURE` and `WATERBODY`
  are per-object.
- ❌ **`VEGETATION(TB)` refused**: 1.52 M triangles is 3.0× the shipped city; photogrammetry, no
  per-tree object, no `COLOR_0`. `GENERIC` and `INFRASTRUCTURE(TB)` fail the same way. ⚠️ `(TB)` is
  not an automatic ban — `TERRAIN(TB)` ships because it is a height field `collapse` has a path for.
- 💡 `WATERBODY` is cheap and **not the harbour**: small hillside features at 24.6–113.6 m, which
  `Q36` measured at 0.000% of all six viewpoints. Needs a tint probe before it is named.
- 🔴 **`INFRASTRUCTURE` is a measurement source as well as geometry** (`Q103`): sampled for deck
  height since `P2-7`, and `pipeline/roads.py` also walks it laterally to publish `width_m` and
  `offset_m` on level-1 edges (36 of 45). Reason: TD, iB1000 and HyD are 2D plan projections, so a
  ray from a deck finds the street underneath — they license 5 of 45 level-1 edges and 2 of those
  publish a width wider than the deck.
- ⚠️ The class is **not watertight** (`Q19`: 5.38% of edge slots open in source, 14–26% in the
  decimated tiles), so the lateral walk bridges gaps under 1.0 m and publishes a low percentile of
  an edge's stations, never a single reading.

### ❌ DO NOT USE — 3D Visualisation Map (Tile-based models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-tile-based-models
- Oblique-photogrammetry mesh, 150 m × 150 m tiles, OBJ / OSGB / Cesium 3D Tiles.
- **Why rejected:** a prior public attempt loaded ~10,000 tiles into Unity and reported **ground
  gaps, level differences, and vehicles baked into the mesh**. Tiles carry no transform metadata.
  Decimating photogrammetry produces blobs, and destroys the separation between road, building and
  street furniture. Hard rule 1.
- Reference: https://medium.com/@devlog/data-of-3d-visualisation-map-from-hk-landsd-4507ffdef598

### What a sheet contains

`11-SW-10C`: 44.3 MB zipped, ~65 MB unpacked, ~744 × 603 m. `BUILDING/` one `.gltf` + `.bin` each,
`default_material`. `INFRASTRUCTURE/` elevated structures spanning continuously from ~3 m ground to
13–32 m — **that span is the ramp**. `TERRAIN(TB)/` one mesh with one 7531 × 6031 JPEG.

1. **Coordinates already match Godot's convention**: each node's matrix translates to
   `(easting, elevation, -northing)` in HK1980 metres. `GameTransform` only subtracts the origin.
2. **Vertices are unwelded — exactly 3.0 per triangle**; flat shading is baked in. Never weld on
   position alone and never regenerate normals; `P1-2` welds on position and facing together.
3. "Non-textured" describes the buildings, not the terrain.

### Measured across all six sheets

**2,200** buildings (`11-SW-14B` alone 720), 74 infrastructure items, 6 terrain meshes with
**224 MB** of JPEG.

- ⚠️ **Triangle budget**: 612 triangles per building; clipped to the region `P1-2` emits **989k** at
  its finest tier against a <300k visible budget. Vertex-clustering LOD tiers make it fit.
- ⚠️ **Infrastructure meshes are unbounded**: one is 1,984 m long with 208k triangles. Anything
  that buckets spatially must handle a mesh larger than its bucket.
- 💡 **`INFRASTRUCTURE` is the only height source for off-grade roads** (`P2-7`): 44 of 45 off-grade
  edges sampled, |error| p90 against the shipped tiles 4.13 m → **0.095 m**. Traps:
  - **Stacked decks** (`CANAL ROAD FLYOVER`): cluster hits into slabs and follow the slab that
    continues the last, anchored on single-slab stations. Never take the highest hit.
  - **Parapets** sit off-centre at ±3 to ±6 m; a centreline never touches one.
  - ⚠️ Not only decks: `ISLAND EASTERN CORRIDOR`'s 25 m stub finds structure **8.3 m below** terrain.
    `roads.deck.max_below_terrain_m` is the gate.
  - ❌ Cannot fix tunnels: the five level −1 portal nodes have no structure, and their descent is
    outside the region.
- **Terrain**: as shipped it is 404,669 triangles and 267 MB clipped. `P3-10` ships it
  **untextured** — the JPEG is read at build time for flat per-vertex colour and discarded: ~88k
  triangles, zero texture memory, no extra draw call (`ART_DESIGN.md` "Ground", `Q18`). It is also
  the **height field** `Q11` samples: ground level in Wan Chai is ~4 m above datum.

---

## Roads

### ✅ USE — Road Network (2nd Generation)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2
- **Publisher:** Transport Department, part of the Intelligent Road Network Package (IRNP).
- **Update frequency:** monthly. We snapshot once — do not track upstream.
- **Read as:** the zipped File Geodatabase, through `pyogrio`'s `/vsizip/` (`Q9`).
- **Contents:** seventeen layers in the 17 MB geodatabase — centrelines, intersections, bus-only
  lanes, speed limits, pedestrian zones, turn and vehicle restrictions, no-stopping zones,
  roundabouts, parking access, zebra crossings, toll plazas.
- Reference: https://medium.com/@devlog/parsing-hong-kong-road-network-data-5b9b80874704

### ✅ RESOLVED — no true Z, but grade separation IS encoded

- **Geometry is 2D**, EPSG:2326. Centrelines are Measured MultiLineString; GDAL drops M with a
  warning.
- **An integer `ELEVATION` encodes the level**: region has 0 (736 edges), 1 (45), **−1 (15)** — the
  Cross-Harbour Tunnel and Central–Wan Chai Bypass. An ordinal like OSM's `layer`, not a height.
- Map `ELEVATION` → an authored deck height in config as an offset from **ground level** (`Q11`,
  `roads.ground`). Since `P2-7` that is only the fallback where no structure can be sampled.
- ⚠️ **`ELEVATION` must not key nodes.** All 36 endpoints where two levels meet are ramps touching
  down; keying on level takes the region from 6 connected components to **24**. Nodes form only
  where centrelines share an endpoint, and a flyover crossing a street shares none (`P1-3`).

### What `P1-3` measured in the geodatabase

Region clip: **796 centrelines, 529 intersections, 217 turns, 83 speed limits, 14 bus lanes.**

| Finding | Measurement | Consequence |
|---|---|---|
| Endpoints coincide exactly | 601 distinct; nearest distinct pair 2.26 m | Nodes by coordinate identity, tolerance ≥ ~1 mm (two clusters differ in the last bits) |
| Geometry is over-densified | one 51.7 m centreline carries 54,330 vertices | Douglas–Peucker at 0.2 m is a correctness measure: 175,610 → 3,553 vertices |
| `ROUTE_ID` is 1:1 with the centreline | 796 of 796 | `SPEED_LIMIT` and `BUS_ONLY_LANE` join by key; no linear referencing |
| Speed limits cover under 10% | 77 of 796 edges, all 70 or 80 km/h, free text | The 50 km/h urban default comes from config |
| Turn geometry is a hint | `EDGE1END` is right in 213 of 217 | Take the shared node; use the field only to break ties |
| Null sentinel has four spellings | `-99`, `–９９`, `－９９`, `-９９` | Normalise NFKC **and** fold Unicode dashes before comparing |
| Dual carriageways are opposed one-way pairs | 6 places share both endpoints, 1.96–3.85 m apart (three are Lockhart Road) | A lower bound. `surface.py` pairs **geometrically** since `Q117`: 49 pairs / 3,958 m. ⚠️ The six are the only ground truth for a pairing rule |

**`NSR` — the kerbside yellow lines** (`pipeline/kerbside.py`, `P3-13`). 579 features / 44,220 m in
region, kerb-referenced (median 2.76 m off the nearest centreline).
- `VEHICLE_TYPE` decides what is paint (`Q56`): `1` "all motor vehicles" (33,074 m) and `5` "Others"
  (8,323 m; the drawings paint 93.9% of it) are drawn. `2`/`3`/`4` (taxis, PLBs, goods, 2,822 m) are
  refused — a class-specific restriction is not a plain yellow line and the codec cannot say which
  class.
- `TIME_ZONE` `1` = 24 hours → double; `2`–`5` = posted hours → single. `EFFECTIVE_DAY` and
  `REMARKS` carry nothing. `ONSTREETPARK` carries 607 bays.
- ⚠️ The one overlay that is **not a key join**: it carries `ST_CODE_1..6`, so it is
  linear-referenced onto the graph; its M values are not a join. 33,385 m over 722 edge sides
  survive, deduped into 1 m cells.

**Lane counts do not exist in this dataset** — no lane attribute anywhere. No source publishes a
count. Traffic Aids Drawings publishes lane *lines*, and a **row of turn arrows abreast is a lower
bound on the count** (`Q94`): `pipeline/carriageway.py` lets a row resolve an ambiguous TPDM bracket
(`lanes_source: arrows`). 🔴 A row of one arrow is refused.

**Feature identity is the FGDB `OBJECTID`.** `TURN` (`EDGE(1-8)FID`) and `INTERSECTION`
(`RD_ID_1..10`) point at OBJECTIDs, so a reader that renumbers on a filtered read resolves every
restriction onto the wrong roads.

**Bilingual street names ship in the source** — `STREET_ENAME` / `STREET_CNAME`, plus `ALIAS_*`.

**Read but not emitted:** `TURN`'s `EXC_VEH_TYPE` / `INC_VEH_TYPE` (`TX` = taxi; one restriction in
region excludes taxis), `PART_TIME_REST`, `EFF_ALL_DAYS`, `OTHER_REST_TYPE`. Matter for `P3-3` and
`P3-8`; adding them is a schema change on both sides.

### `Q9` — the geodatabase, and every GML dropped

`RdNet_IRNP.gdb.zip` is **17.4 MB with all seventeen layers**; the per-layer GMLs of the same
content total 539 MB. `hong_kong.yaml` lists only the geodatabase and the specification PDFs.

| Resource | URL |
|---|---|
| Full FGDB (the one we use) | `https://static.data.gov.hk/td/road-network-v2/RdNet_IRNP.gdb.zip` |
| Data dictionary | `https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip` |
| Consolidated file list | `https://static.data.gov.hk/td/road-network-v2/dataspec/file_list.csv` |
| Per-layer GML (not fetched) | `https://static.data.gov.hk/td/road-network-v2/{CENTERLINE,INTERSECTION,BUS_ONLY_LANE,ROUNDABOUT,PEDESTRIAN_ZONE,PROHIBITION,NSR}.gml` |

CKAN enumerates all 61 resources:
`https://data.gov.hk/en-data/api/3/action/package_show?id=hk-td-tis_15-road-network-v2`

---

### ✅ USE — Traffic Aids Drawings (2nd Generation)

**`hk-td-tis_16-traffic-aids-drawings-v2`** · Transport Department · EPSG:2326 · monthly ·
FGDB `dTAD_IRNP.gdb.zip`, **218 MB**, 51 layers · added by `Q56`

- ⚠️ The 1st generation (`hk-td-tis_8-traffic-aids-drawings`) is withdrawn; its only resource is a
  CSV pointing here. Skip it.
- TD's drawing set as spatial features (MicroStation levels, `LINETYPE`, `SYMBOL_STEP`, hatch
  angles). Road Network v2 is *semantic*; this is *cartographic* — a genuine second opinion.
- `traffic_aids_drawings_gdb` is build input: seven config blocks read it (`roads`,
  `carriageway_survey`, `arrows`, `signs`, `boxjunctions`, `road_marks`, `railings`), plus
  `crossings`, `tools/kerbside_source_audit.py` and `tools/carriageway_margin.py`.
- 🔴 `traffic_aids_data_dictionary` (8.5 MB) is **read by the build** too: `pipeline/sign_text.py`
  crops `TS102`'s lettering from `CT174/51-1(1)C` into the sign atlas, so the shipped city contains
  pixels cut from this PDF (government data, never committed). `tools/sign_face_survey.py` reads it
  as well.
- ⚠️ Both go through `pipeline/sign_sheets.py`. The sheets have **no text layer**, so a cell's code
  is *counted* from the filename's range and grid position, asserted by `blocks x rows` bracketing
  the span (5 x 21 on every sheet in use). Three 6-block sheets are refused loudly.
- The TS sheets are **vector DGN exports** (not scans), which is what `Q67`'s rasterise-and-diff
  depends on. The RM index plans are **scans** — read by eye (`Q59`).

| Layer | In Wan Chai | What it is |
|---|---|---|
| `DTAD_RST_ZONE_LINE` | 1,763 / 39,292 m; `RM1040` 24,932 m, `RM1041` 14,164 m | **Kerbside yellow lines**; read only by the kerbside audit. ⚠️ `TIME_ZONE` is null on every feature — posted hours live in `NSR` |
| `DTAD_YL_BOX_POLY` | 20 polygons | **Yellow box junctions** — `pipeline/boxjunctions.py` → `boxjunctions.glb` (`P3-18`). 2D single-ring, 20–469 m². ⚠️ `ANGLE1`/`ANGLE2` published on only 4 of 20; the stage derives the rest and grades against those four. `ELEVATION` null on all. `RM1038` lines in `DTAD_RD_MARK_LINE` stay unread |
| `DTAD_RD_MARK_LINE` | 1,679 features / **4,162 parts** / 61,903 m | `RM1109` 25,204 m and `RM1001` 19,308 m dominate. In use: `RM1108`/`RM1109` edge of carriageway (317 features, width survey); `RM1011`/`RM1012`/`RM1013` stop and give-way lines (`P3-23`, `roadmarks.glb`); `RM1001` double lines (`Q118`). 2D `MultiLineString`. 🔴 **Nearest-edge join is wrong for transverse marks** on 43% of the layer — a stop line lies p50 1.10 m from the *major* road's centreline. `roadmarks.py` hosts by transversality and publishes `host_disagreement` (`Q69`). ⚠️ Features and parts differ 2.5× |
| `DTAD_RD_MARK_LINE_C` | 1,413 features | The other marking half, read via `road_marks.more_layers` (`P3-34`, `Q132`): `RM1101`/`RM1102` lane lines, `RM1103` centre, `RM1104`/`RM1105` warning, `RM1002`/`RM1003` broken doubles (2,046 m / 2,165 m at grade). ⚠️ `RULEID` is 2 on `RM1002` and 3 on `RM1003`, which makes LEFT/RIGHT the digitised direction's. Also read by `tools/width_evidence.py` (`Q127`): line spacing agrees with arrow spacing to p50 0.29 m, but a lane *count* off lines over-counts on 51 of 75 edges |
| `DTAD_CROSSING_LINE` | 121 features / 1,082 parts / 6,698 m | **Crossing stripes, each its own rectangle** — `pipeline/crossings.py` (`P3-35g2`). Short side p50 0.600 m, long 3.500 m. ⚠️ `LINETYPE` has no domain and does not give colour (`SOLID` / `Solid` / null / `RM1076` all carry the same stripe). Also `CROSS_BOUNDARY`, `CROSS_ANNO`, `RM1077`, `ZEBRA4` |
| `DTAD_RD_MARK_SYM_PT` | 1,365 points; `REFNAME`, `ANGLE`, `ELEVATION`, `SYMBOL_SIZE` | **Turn arrows** — `pipeline/arrows.py` (`P3-15`, `Q59`). 781 in region: `RM1017` ×353, `RM1019` ×179, `RM1027` ×102, `RM1021` ×92, `RM1025` ×46, `RM1023` ×8, `RM1029` ×1, all the 4000 mm variant. ⚠️ **`ANGLE` is mathematical**: heading = `(90 − ANGLE) mod 360` (p50 0.9° off the host edge). ⚠️ Look-alikes: `RM1116`–`RM1119` WARNING ARROW ×61, `RM1135`/`RM1136` 望右/望左 ×127/×123; `RM1167`–`RM1169` and `RM1144` are 0 here. `SYMBOL_SIZE` is populated on 2. 🔴 Read by **two** stages (`arrows.py` glyph, `carriageway.py` lane row) that cluster independently; `lanes_row_disagreement` is their diff |
| `DTAD_RD_MARK_ANNO` | 274 | **Road text** (`CENTRAL`, `九龍`). Geometry is a `MultiPolygon` rotated rectangle, so position, angle and extent are all read (`Q54`). Some strings carry `<FNT …>` markup; 67 distinct fragments. Not in use — `P3-21` |
| `DTAD_TS_ABV_PT` / `DTAD_TS_POLE_PT` | 3,276 signs / 2,227 poles | **Traffic signs** — `pipeline/signs.py` → `signs.glb` (`P3-16`); `TS102`/`TS101` carry baked lettering (`P3-20`). See notes below |
| `DTAD_RAILING_LINE` | 1,753 features / 1,763 parts / 20,273 m | **Railings, bollards, barriers** — `pipeline/railings.py` → `railings.glb` (`P3-19`, `Q61`). See notes below |
| `DTAD_TRAFFIC_LIGHT_PT` | 913 points | Signal estate; 51 are not heads (bollards, `PBUTT`, `WIGWAG`). 🔴 `REFNAME` has **no published domain** (`Q76`). `ANGLE` is not a facing; no `GG_NAME`; `ELEVATION` null on 906. Read by `pipeline/signals.py` (`P3-17`) but **not shipped** (`Q77`) |
| `DTAD_TY_BAR_LINE`, `DTAD_RD_MARK_SYM_LINE`, `DTAD_DROP_KERB_LINE` | 4 / 173 / 738 | Yellow bars; bus-stop boxes, KEEP CLEAR, taxi PU/DF `RM1176` ×5; dropped kerbs. Not in use |
| ⚠️ `DTAD_TW_STRIP_LINE` | 778, `REFNAME = TACW` | **Not tramway** — tactile warning strips. The tramway is in iB1000 |

**Signs (`DTAD_TS_*`):**
- `SIGNID` resolves into the twenty `Index Plan/(TS …).pdf` sheets; the whitelist is transcribed by
  eye and checked by `tools/sign_face_survey.py` (`Q67`), which cannot see a face on the wrong
  *code* — its contact sheet is for that. 🔴 The whitelist once shifted a row at `TS182`/`TS183`
  (`Q64`); read `~/hk-traffic-sign-map`'s `signCatalogue.json` for crops, never for `desc`.
- 🔴 **`DTAD_TS_ABV_PT` is not where the sign is** — it is a label placement ("abbreviation point"):
  zero of 3,276 sit on a pole, nearest pole p50 2.63 m. **`GG_NAME` is the only join**: 3,032
  (92.6%) resolve to one pole, 24 to several, 220 to none.
- 🔴 **`ANGLE` is not a facing** — the spec says "same as Ustn angle" (symbol rotation); p50 44.2°
  from the road axis, uniform. ⚠️ Comparing against a *grid* bearing falsely shows 76.3% square to
  the road. Facing is derived from host edge + kerb side + drive-on-left.
- 🔴 77.3% of poles are surveyed inside the drawn ribbon (pre-`Q95`; re-opened by `Q101`), so posts
  are registered onto the drawn kerb — **outward only** since `Q78`; posts already clear keep TD's
  point (`posts_kept_as_surveyed`).
- ⚠️ No sign dimension is published (sheets are "NOT TO SCALE"): plate size, mount height and pole
  diameter are authored. `ELEVATION` null on 3,140 (`A01` ×123, `A03` ×13).
  `DTAD_TS_PLATE_LINE` is cartographic ticks (median 0.06 m), not a plate outline.

**Railings (`DTAD_RAILING_LINE`):**
- Three classes: `railings` (`CRAIL1` `CRAIL2` `HCAIL2` `RAIL1` `RAILING1`), `bollards`
  (`bollard0..3`), `barriers` (`CBARRIER` `CRASHGATE`). Split by class of object, never within one.
- Nineteen `LINETYPE` values by metres of parts: `CRAIL1` 10,499, `CRAIL2` 2,921, `HCAIL2` 2,073,
  `CBARRIER` 1,369, `SOLID` 511, `AMT1` 502, `RAIL1` 472, `AMT` 457, `CRASHGATE` 301, `bollard0`
  285, `RAILING1` 283, `bollard2` 235, `bollard3` 153, `AMT2_1.5` 118, `EAG 3` 46, `MSB 5` 23,
  `AMT1.5_1.0` 17, `AMT-1.5` 4, `bollard1` 3.
- 🔴 **`LINETYPE` has no published domain** and the index plans carry no railing sheet, so the
  `classes` table is a whitelist read off code strings — the weakest claim in `hong_kong.yaml`
  (`Q60`). Height, post pitch and thickness (`Q112`) are authored.
- ⚠️ `SYMBOL_SIZE_*` / `SYMBOL_STEP_*` are plot sizes in inches, not street metres, and null on all
  bollards. `COLOR` separates classes but has no coded table. 2D; `ELEVATION` null on 1,737, `A01`
  on 16.

**The marking codes are defined by the publisher.** `dataspec/tadrawings_dataspec.zip` holds
`Index Plan/(RM 1001 - 1080).pdf` (drawing `CT174/51-5(1)F`) and `Index Plan/(RM 1101 - 1180).pdf`
(`CT174/51-5(2)G`). Rows verbatim, dimensions in mm:

| Code | Description | Dimensions | Kind |
|---|---|---|---|
| `RM1001` (TC 501) | DOUBLE LINES — WHITE | width 150, spacing 100, both continuous | double |
| `RM1002` (TC 502) | DOUBLE LINES — WHITE | width 150, spacing 100, left continuous, right 1000 mark / 5000 gap | double, one broken |
| `RM1003` (TC 502) | DOUBLE LINES — WHITE | width 150, spacing 100, left 1000 mark / 5000 gap, right continuous | double, one broken |
| `RM1004` (TC 503) | CONTINUOUS DOUBLE LINES WITH HATCHING — WHITE | width 150, spacing VARIABLE, hatching ≯ 3000 apart | — |
| `RM1011` (TC 506) | STOP LINE — WHITE | width 200, continuous | single |
| `RM1012` (TC 507) | STOP LINES — WHITE | width 200, spacing 300, both continuous | double |
| `RM1013` (TC 508) | GIVE WAY LINES — WHITE | width 200, spacing 200, both 600 mark / 300 gap | double, broken |
| `RM1017`-`RM1030` (TC 509) | TURN ARROWS — WHITE | `LENGTH = 4000` or `6000`, nothing else | — |
| `RM1035` / `RM1036` (TC 512) | PROHIBITORY CHEVRON — WHITE | width 150, continuous, chevron width 900, 2000 apart | — |
| `RM1037` (TC 513) | PROHIBITORY HATCHED TRAFFIC ISLAND MARKING — WHITE | width 150, hatching ≯ 3000 | — |
| `RM1038` (TC 514) | BOX JUNCTION — YELLOW | boundary 300, hatched 100, spacing 2000 (2500) | — |
| `RM1040` (TC 515) | NO STOPPING AT ANY TIME — YELLOW | width 100, spacing 100, both continuous | double |
| `RM1041` (TC 519) | NO STOPPING PART TIME — YELLOW | width 100, continuous | single |
| `RM1043` (PA 12) | NO PARKING HATCHED MARKINGS — YELLOW | width 100 | — |
| `RM1070` (TC 801) | ZEBRA CROSSING — WHITE | width 500-700, spacing 500-700, length ≥ 2500 | stripes |
| `RM1071` (TC 802) | ZEBRA CROSSING GIVE WAY LINE — WHITE | width 200, 500 mark / 500 gap | — |
| `RM1072` / `RM1073` (TC 802) | ZIG ZAG MARK — WHITE | width 100, 2000 mark / 150 gap. Surveyed as `ZIGZAGL` / `ZIGZAGR` in `DTAD_RD_MARK_LINE_C`; the evidence a crossing is a zebra | — |
| `RM1076` (TC 806) | LIGHT SIGNAL CROSSING YELLOW STRIPED MARKINGS — YELLOW | width 250-350, first marking 500-1300 from kerb, spacing 600-800. ⚠️ surveyed 0.6 m wide | stripes |
| `RM1101` (TC 601) | LANE LINES — WHITE | width 100, 1000 mark / 5000 gap | single, broken |
| `RM1102` (TC 601) | LANE LINES — WHITE | width 100, 2000 mark / 7000 gap | single, broken |
| `RM1103` (TC 602) | CENTRE LINE — WHITE | width 100, 3000 mark / 5000 gap | single, broken |
| `RM1104` (TC 603) | WARNING LINE — WHITE | width 100, 4000 mark / 2000 gap | single, broken |
| `RM1105` (TC 603) | WARNING LINE — WHITE | width 100, 6000 mark / 3000 gap | single, broken |
| `RM1106` (TC 605) | JUNCTION EDGE LINE — WHITE | width 100, 600 mark / 300 gap | single, broken |
| `RM1107` (TC 606) | MERGING/DIVERGING LANES, LAYBY, BUS STOP, PASSING PLACE EDGE LINE — WHITE | width 100, 1000 mark / 1000 gap | single, broken |
| `RM1108` (TC 607) | EDGE OF CARRIAGEWAY — WHITE | width 100, 1000 mark / 3500 gap | single, broken |
| `RM1109` (TC 607) | EDGE OF CARRIAGEWAY — WHITE | width 100, continuous | single |

- ⚠️ **`LINES SPACING` is the clear gap, not a centre-to-centre pitch**: `RM1001`'s 150 mm lines at
  a 100 mm pitch would be one 250 mm line.
- ⚠️ Colour is read off the Description column: `RM1040`–`49` on the same sheet are yellow.
- ⚠️ `RM1013` is a double broken line, not triangles (`Q69`).
- **`RM1001`** (`Q118`): 5,745 m of the 19,308 m is at grade, the rest on structure. `Q125` draws
  the inferred opposed-pair join as this same mark (`road_marks.opposed_join_mark`) where no
  surveyed line covers the pair — shape TD's, placement inferred (a `Q54` debit).
- 🔴 **Arrows publish a length and no shape** (`Q93`). Proportions measured at 700 dpi off the
  pictograms of `RM1017`/`RM1027`: ahead head **0.390** of length long, **0.122** across; stem tapers
  0.076 → 0.032; branch reach 0.150, barb span 0.233. ✅ The sheet is drawn to proportion despite
  "NOT TO SCALE": `RM1016` publishes 5600 x 2000 (2.800) and its pictogram measures 2.802. The turn
  **branch is authored** — a faithful barb is 0.09 m on a 4 m arrow, sub-pixel (`Q91`). `Q67`'s diff
  cannot grade this scanned page.
- ⚠️ The RM sheet is stamped "FOR INTERNAL ONLY" yet ships in the open-data bundle; the terms are
  unchanged by it.

⚠️ **`ELEVATION` here is a 3-char relative-level text code with no published domain** — not Road
Network v2's integer. Measured over the 317 `RM1108`/`RM1109` features:

| `ELEVATION` | features | median to level 0 | median to level 1 | within 8 m of level 1 |
|---|---|---|---|---|
| `A01` | 180 | 5.6 m | **2.6 m** | **93%** |
| *null* | 126 | **2.7 m** | 11.4 m | 38% |
| `A03` | 11 | 27.4 m | 218.1 m | 0% |

**`A01` is the elevated network despite being the commonest value; at grade is null.** So
`carriageway_survey` states an exclusion, `off_grade_codes: [A01, A03]`.

**Agreement with `NSR`:** `RM1040` sits on `NSR TIME_ZONE = 1` for 99.95% of its length, confirming
"24 hours is a double yellow". Only 24 m of the 39 km is unexplained by `NSR` (`Q56`).

| Resource | URL |
|---|---|
| Full FGDB | `https://static.data.gov.hk/td/traffic-aids-drawings-v2/dTAD_IRNP.gdb.zip` |
| Data specification + `Index Plan` | `https://static.data.gov.hk/td/traffic-aids-drawings-v2/dataspec/tadrawings_dataspec.zip` |
| Per-layer GML / KMZ (not fetched) | `https://static.data.gov.hk/td/traffic-aids-drawings-v2/DTAD_{LAYER}.{gml,kmz}` |

### ❌ Surveyed and rejected for kerbside restrictions (2026-08-20)

`Q56` swept all 60 TD datasets on DATA.GOV.HK, the CSDI catalogue and 3,810 packages by keyword.
**`NSR` and `DTAD_RST_ZONE_LINE` are the only two datasets that assert a kerbside stopping
restriction.** Do not repeat the sweep.

| Dataset | Why not |
|---|---|
| `hk-td-msd_1` Metered Parking Spaces | Counts per district; no per-bay geometry |
| `hk-td-msd_2` Non-metered On-street Parking | ~250 sensored spaces territory-wide, a trial |
| `hk-td-tis_4` / `tis_5` parking distribution, vacancy | Real-time occupancy, not restriction |
| `hk-td-tis_36` Pedestrian Streets | `PEDESTRIAN_ZONE` already covers it |
| `hk-landsd-openmap-road-centreline` | For "approximate location query and map annotation" |

The sweep also surfaced `hk-td-tis_39` Fleet Taxi Stopping Places (see "Fares and points of
interest") and the HyD pavement polygons (next).

### ✅ USE — HyD Pavement Polygon (`Q94`, 2026-08-29)

**`hyd_rcd_1632210918434_60749`** · Highways Department · **CSDI Portal only**, no DATA.GOV.HK
package · ArcGIS `MapServer` layer `INV_PG`, **native EPSG:2326**.

🔴 The only source that gives the carriageway as an **area** rather than an edge line.

- **Fetch:** `paged_sources.pavement_polygon` — `MapServer/0/query` paged over the whole territory:
  64,644 features, 22 requests, one **163.2 MB** file. `pipeline/fetch.py` walks it.
- Refused routes: `file-api` GeoJSON is 317 MB **WGS84** (`gdb.read_layer` does no reprojection); a
  bbox query would put per-region bounds in a whole-config `sources:` block (hard rule 3).
- ⚠️ `geometryPrecision=2` (centimetres) cuts 41% with 0.000 m change on the STEWART ROAD edges.
  `orderByFields=OBJECTID` because paging without a stable sort is undefined. The walk stops on a
  short page; `max_pages` 60 catches a service ignoring `resultOffset`.

The domains are published in the layer's own `?f=json`:

```
FEAT_TYPE   1 Carriageway   2 Footway   3 Other   5 Cycle Track   6 Side/Back Lane   7 Run-in
            8 PTI-Carriageway   9 PTI-Footway   23 Carpark-Carriageway   24 Carpark-Footway
           31 Traffic Island - Refuge Island    32 Traffic Island - Other
SUR_TYPE_1  1 Flexible  2 Rigid  3 Pavers  7 Flexible w/ anti-skid  8 Rigid w/ anti-skid
           10 Works In Progress
PAVER_TYPE  A Artificial Granite · C Clay · E Recycle · G Granite · H High Quality Concrete
            M Mixed Granite+Clay · N Mixed Granite+Concrete · R Concrete · S Concrete w/ glass
LVL         3/2/1 above ground · 0 ground · -1/-2/-3 below — mirrors Road Network v2's ELEVATION
```

Wan Chai (1.461 km² envelope): 1,714 polygons, 509,446 m² clipped (34.9%). `FEAT_TYPE` 1
Carriageway 552 polygons / **358,599 m² (24.5%)**; 2 Footway 917 / 122,413 m²; 31 Refuge Island 98 /
3,192 m². `LVL` splits 1,665 ground / 33 above / 16 below.

- 🔴 **Read by walking point-in-union, never by a ray to the nearest polygon boundary** — HyD tiles
  the carriageway into 552 polygons, and an internal seam is not a kerb. ⚠️ Stations within 12 m of
  a node read the cap both ways; that is why `JUNCTION_M` exists.
- 🔴 **It measures the trafficable surface, not kerb-to-kerb**: islands, run-ins and car parks are
  carved out of `FEAT_TYPE = 1`. Over 4,925 shared stations, HyD − iB1000 is p10 −3.39 / p50 −0.00 /
  p90 +0.47 m; 57.3% agree within 0.10 m. Left as the reading — arguably the better answer for a
  carriageway a car must fit down.
- It agrees with iB1000 on STEWART ROAD to within 5 cm (`e503` 10.50, `e504` 16.72, `e505` 16.66 m).
  ⚠️ `e504`/`e505` are still refused by TD's 16.5 m ceiling, which refuses a span before asking who
  drew it.
- 🔴 Third in preference does **not** mean "only where the others are silent": the publisher loop
  runs per *station*. It never overrides a station another publisher answered. HyD reaches 880
  stations neither line publisher spans.
- `roadgraph.json` `width_publisher` (schema 7) is a **set** joined on `+`, empty where authored. It
  records who was used, not who could have answered.
- ⚠️ **Attribution:** Highways Department via the CSDI Portal — this dataset makes the CSDI half of
  hard rule 6 load-bearing.

### ✅ READ, not fetched — TD's Transport Planning & Design Manual, Volume 2 (`Q95`)

**`https://www.td.gov.hk/filemanager/en/content_5055/V2_03_2026.pdf`** · Transport Department ·
on `td.gov.hk`, not an open-data dataset · Chapter 3, **March 2026 edition**, real text layer.

🔴 **A design standard is not a survey.** It says what a road *should* be, so it may bound an
instrument and source an authored number — never assign a per-edge width.

**Table 3.4.2.1 — Minimum Carriageway Widths in Urban Areas**, per carriageway (m):

| Road type | single, 2 lane | single, 4 lane | dual, 2 lane | dual, 3 lane | dual, 4 lane |
|---|---|---|---|---|---|
| Trunk Road / Expressway | — | — | 7.3 | 11 | 14.6 |
| Primary Distributor | — | — | 6.75 | 10 | 13.5 |
| District Distributor | **7.3 or 10.3** | **13.5** | 6.75 | 10 | — |
| Local Distributor | **7.3 or 10.3** | **13.5** | 6.75 | — | — |

- **3.4.2.3** — a double-track tram reserve requires **5.5 m**.
- **3.4.2.6** — distributors may carry an extra **3 m** parking strip.
- **3.4.4.1** — widening on curves under 400 m radius: a 13.5 m four-lane becomes **15.8 m** below
  150 m.
- **4.3.9.8** — a through lane is **3.0–3.65 m**, exclusive of hard strips.
- **3.4.2.7** — a two-way single carriageway must not be divided into three lanes (except a
  climbing lane). A derived odd count on a `direction=both` edge is a finding.

How it is wired (`carriageway_survey.width_bounds` in `hong_kong.yaml`):
- A two-sided span above ~**16.5 m** (13.5 + parking strip; 15.8 on a curve) crossed a median, tram
  reserve or junction mouth, and is refused.
- A carriageway split out of a pair is bounded by `dual_max_m` **14.6 m**; the separator by
  `median_max_m` **5.5 m**, which is ⚠️ reported and never refused.
- Whether a ray crossed a median: span minus twice the near ray under **3.0 m** → one carriageway;
  at or above `dual_min_m` **6.75 m** → may have crossed; between, nothing is read. ⚠️ The middle
  band is load-bearing (TONNOCHY ROAD sits in it), and the permissive end is chosen on purpose.
- ⚠️ **4.3.9.8's 3.0–3.65 m is the lane divisor; `roads.lane_width_m` must never be** — dividing by
  the authored constant makes the instrument agree with it by construction. The count is a bracket.
- 🔴 The bound does not filter the opposed-pair confound: two one-way carriageways summing to 13 m
  pass as a legal four-lane. Such spans publish as kerb-to-kerb, never as a width. Measured: most
  paired one-way spans are in fact *one* carriageway (96 of 110 refuse their own split); the
  population separates on `off_centre` (p50 0.20 refused vs 0.58 read). `Q95`.
- ⚠️ `pipeline/carriageway.py` and `tools/carriageway_margin.py` deliberately share no measurement
  code; their agreement (5 mm median) is the check. A consumer may not invert
  `width_m / lane_width_m` to recover a lane count (schema 5).
- ⚠️ Read, not fetched — nothing in `etl/` downloads it. City-specific values go in
  `hong_kong.yaml`. The table is headed *Minimum*, and 3.4.2.2 lets trunk widths fall below it.

## Fares and points of interest

data.gov.hk lists only a portal link for each. The downloadable URL is the CSDI `file-api`:

```
https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=<id>&format=geojson
```

No API key and no `layer_name`, so the URLs live in `hong_kong.yaml` directly.

- **`crs` is absent** = CRS84 per RFC 7946 (WGS84 lon/lat), declared explicitly in config.
- **Positions are quantised to whole metres on the HK1980 grid** — about half a metre of
  uncertainty per fare node.

### ✅ USE — Taxi Stands

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_37-taxi-stands
- **CSDI dataset id:** `td_rcd_1697081907714_17556` — 518 features, 343 KB. Updated twice a year.
- **Gameplay use:** pickup hotspots. *Cross Harbour* becomes a premium fare type that terminates at
  the tunnel approach.

⚠️ **`Status_EN` is free text** — sixteen spellings, some with an operating-time note after an
embedded newline:

| Count | `Status_EN` | → |
|---:|---|---|
| 312 | `Urban Taxi Stand` (+4 with a time note) | `urban` |
| 75 | `Both of Urban and NT Taxi Stand` (+1 `Urban and NT Taxi Stand`) | `urban_and_nt` |
| 68 | `NT Taxi Stand` (+1 with a time note) | `nt` |
| 30 | `Cross Harbour Taxi Stand` (+3 with a time note, +1 `Urban and Cross Harbour Taxi Stands`) | `cross_harbour` |
| 21 | `Lantau Taxi Stand` | `lantau` |

Matching is **first-hit-wins over substrings**, so rule order is load-bearing: `Urban and NT` before
`NT Taxi Stand` before `Urban`. `load_config` refuses a shadowing table and `test_config.py` pins
all sixteen spellings. `Q14`: operating-time restrictions are discarded — no contract field.

### ✅ USE — Taxi Pick-up & Drop-off Points

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_38-taxi-pick-up-drop-off-points
- **CSDI dataset id:** `td_rcd_1697082382328_14459` — 275 features, 192 KB. Updated twice a year.
- `Status_EN`: **`Taxi PU/DF`** (209) hail and deliver; **`Taxi DF`** (66) drop-off only. Carried
  into `fares.json` as `pickup`/`dropoff`.

### Names, in both datasets

`Location_EN` / `Location_TC` are populated on every feature.

- 31 of 793 names contain embedded newlines — collapsed by `clean_text`.
- 98 names use full-width brackets (`（1）`). `clean_text` returns **NFC** and folds to NFKC only for
  the null-sentinel comparison, because NFKC would rewrite them as ASCII.
- `Location_SC` is not read.

### Snapping fare nodes to the road graph

Over the region's 29 points: distance to nearest centreline 1.18–8.37 m (median 3.2 m); margin over
the second-nearest edge at least **4.28 m**; 28 of 28 named edges match the point's own
`Location_EN` prose — independent corroboration.

⚠️ `Q15`: the sources are 2D, so plan distance is the only measure, and candidates are **restricted
to level 0** — tram stop `f_032` on Hennessy Road under the Canal Road Flyover otherwise snaps to
the deck by 0.80 m.

> **Region note:** Hong Kong Island uses **red urban taxis**. Green (NT) or blue (Lantau) livery in
> this map would read as wrong to any local player.

### ✅ SURVEYED — four more point sets that bear on this section (`Q57`; one, the tram stops, since fetched and shipped by `P3-14`)

All CSDI `file-api` GeoJSON, no key.

| Dataset | Territory | In region | Note |
|---|---|---|---|
| `td_rcd_1760062901418_33580` Fleet Taxi Stopping Places | 17 | 2 | One is Expo Drive outside HKCEC. ⚠️ Names are prose, not a street code. Not in use |
| `td_rcd_1638874475129_49745` Bus Stop Location | 4,480 | 70 | `P3-3` traffic. Not in use |
| `td_rcd_1638874728005_80512` GMB Terminus Location | 4,760 | 52 | Not in use |
| ✅ `td_rcd_1638875413253_59498` Tram Stop Location | 117 | **19** | Shipped by `P3-14` as the `poi` kind. ⚠️ Publishes no name (`OBJECTID`, `STOP_ID`, `LAST_UPDATE_DATE` only): `fares.json` carries `name: null`, `pickup`/`dropoff` both false |

---

## Coordinate systems

| Item | Value |
|---|---|
| Source CRS | **HK1980 Grid System, EPSG:2326** (Transverse Mercator) |
| Vertical datum | Hong Kong Principal Datum (HKPD) |
| Game space | Local ENU metres, **origin at region NW corner** (`Q7`) |
| Tile-based model quirk | Drawn in HK80 coordinates minus 800,000 (rejected dataset) |

```
game_x =  (easting  - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing - origin_northing)
```

The `-Z` is forced by handedness; the NW origin puts the region in the positive quadrant
(`ARCHITECTURE.md`). **Keep this conversion in `etl/pipeline/crs.py` only.** Nothing else may assume
EPSG:2326.

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

HK1980 and WGS84 differ by **~304 m on the ground** in Hong Kong, and the two readings
select different sheets. Settled by measurement: sheet `11-SW-10C`'s buildings span easting
836006–836752 / northing 815600–816173, matching the WGS84-projected sheet bbox (836000–836750 /
815600–816200) and not the HK1980 one (836252–837003 / 815431–816031). `hong_kong.yaml` declares
`crs.geodetic: EPSG:4326`, and the loader **refuses to run without an explicit datum.**

### Covering sheets

Six 1:1000 sheets, ~44 MB each — **~265 MB**:

```
11-SW-9D    11-SW-10C   11-SW-10D
11-SW-14B   11-SW-15A   11-SW-15B
```

**Do not hardcode this list.** `fetch.py` derives it by intersecting the region bounds with the
fetched sheet index.

Key roads: Gloucester Road, Harbour Road, Hennessy Road, Lockhart Road, Jaffe Road, Johnston Road,
Queen's Road East, Canal Road East/West + flyover, Yee Wo Street, Percival Street.

Natural map edges: Victoria Harbour (north), the escarpment toward Kennedy Road / Mid-Levels (south),
Admiralty (west), Victoria Park (east).

---

## Access notes

### Roads — fully scriptable ✅

Direct static URLs, enumerable via the data.gov.hk CKAN API. No key, no portal, no account.

### Buildings — fully scriptable ✅

⚠️ The CKAN resource list points only at interactive portals. **The sheet index is the API**: the
CSDI portal serves a territory-wide index of 3,456 sheet polygons, each carrying direct download
URLs.

| Property | Example |
|---|---|
| `SHEETNO` | `11-SW-10C` |
| `Format_glTF` | `https://download.map.gov.hk/api/3d-zip/GLTF0/11-SW-10C.zip?key=…` |
| `Format_FBX` / `Format_MAX` | `…/api/3d-zip/FBX0/…`, `…/api/3d-zip/MAX0/…` |
| `REVISIONDATE` | `20260424` — per sheet |

- One public key is shared by all sheets, baked into the index.
- ⚠️ **Do not hardcode the key into `hong_kong.yaml` or any committed file.** `fetch.py` reads URLs
  from the index at run time and everything it records passes through `redact()`.
- `REVISIONDATE` is the cache key, so a forced re-snapshot costs 3.2 MB instead of 265 MB.
- Index CRS is **WGS84** (GeoJSON with `crs: null`).

The index has a direct URL — no key, session or account:

```
https://portal.csdi.gov.hk/csdi-webpage/file-api
    ?dataset_id=landsd_rcd_1742809441342_98380
    &format=geojson
    &layer_name=Nontextured_models
```

The endpoint generalises by dataset, format and layer (individualised:
`landsd_rcd_1671676915450_88604`, `layer_name=Individualised_models`). Layer names come from the
ISO 19139 record — grep it for `layer_name=`:
`https://portal.csdi.gov.hk/geoportal/rest/metadata/item/<datasetId>`. That record also advertises
WFS, WMS and an ArcGIS `FeatureServer`.

### iB1000 (topographic map) — fully scriptable ✅, but only via the TileIndex

- Index: `file-api?dataset_id=landsd_rcd_1637223748322_25497&format=geojson&layer_name=TileIndex` —
  3,333 sheet polygons, WGS84, no key. Properties: `SHEETNO`, `REVISIONDATE`, and per-sheet `FGDB` /
  `GML` / `DGN` / `DWG` / `TIFF` URLs with no API key in any of them.
- Each `FGDB` property is
  `https://open.hkmapservice.gov.hk/OpenData/directDownload?productName=iB1000&sheetName=T<SHEETNO>&productFormat=FGDB`
  → a plain HTTP 200 zip.
- ❌ The `portal.csdi.gov.hk/csdi-webpage/download/common/<hash>` full-set links return **403 to
  scripted GET**, and the seamless full-set `directDownload` 504s. Per-sheet is the only route.
- Read with pyogrio through `/vsizip/<zip path>/<SHEETNO>/<SHEETNO>.gdb`; sheets cache under
  `etl/sources/topography/`.
- ⚠️ **`open.hkmapservice.gov.hk` serves its TLS chain without the issuing intermediate** (Hongkong
  Post e-Cert SSL CA 3 - 17). Python's OpenSSL does not chase AIA, so `urlopen` fails
  `CERTIFICATE_VERIFY_FAILED`. The intermediate is committed at `etl/config/certs/` and declared in
  `hong_kong.yaml`'s `extra_cas` — verification is completed, never relaxed. Expires 2032-06-03.

**Portal entry points:**

- Non-textured: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1742809441342_98380`
- Individualised: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1671676915450_88604`
- 3D-BIT00: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637306559892_42396`
- iB1000: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637223748322_25497`

The Cesium 3D Tiles API (`https://data.map.gov.hk/api/3d-data/3dtiles/{sheet}/tileset.json`) serves
the rejected tile-based variant; not needed, and no key from `3dmap@landsd.gov.hk` is needed.
