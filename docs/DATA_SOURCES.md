# Data Sources

All facts below were verified against primary sources. **Do not re-research these** — if
something turns out wrong, correct it here and note it in `PROGRESS.md`.

## Licence summary

All datasets below are published via DATA.GOV.HK and the CSDI Portal, and are available for
**free re-use for both commercial and non-commercial purposes**, subject to the DATA.GOV.HK
Terms and Conditions of Use.

Requirements we must meet:

- **Attribution** — identify the source of the data and acknowledge the Government of the HKSAR
  and the relevant organisations' ownership, with proper credit to DATA.GOV.HK.
- Data is supplied **"AS IS"** with no warranty as to accuracy, completeness, or fitness.
- The terms include an **indemnity** clause in favour of the Government.

### Required credits-screen text (draft)

> Contains geospatial data from the Lands Department and the Transport Department of the
> Government of the Hong Kong Special Administrative Region, obtained via DATA.GOV.HK and the
> Common Spatial Data Infrastructure Portal. Used under the DATA.GOV.HK Terms and Conditions
> of Use. The Government of the HKSAR does not endorse this product.

> **Legal note:** because this ships as a commercial product, have a Hong Kong IP lawyer
> sight-check landmark depiction and the credits text before launch. Government geodata licensed
> for commercial use is about as clean as it gets, but this is cheap insurance.

---

## Buildings

### ✅ USE — 3D Visualisation Map (Non-textured models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-non-textured-models
- **Publisher:** Lands Department (LandsD)
- **Formats:** MAX, FBX, **glTF** — one zip per 1:1000 sheet.
- **Content:** Geometry and position only — no textures **on buildings**. Terrain ships textured.
- **Coverage:** Whole territory of Hong Kong, 3,456 sheets.
- **Why:** Flat-shaded extruded volumes are exactly the target art style.
- **Access: fully scriptable** — see "Access notes" below. The CSDI portal serves a *sheet index*
  in GIS vector formats; the index carries direct download URLs for the models.
- ⚠️ **Decimation is needed after all** at 612 tris/building — see the triangle-budget note below.

### ✅ USE — 3D Spatial Data (3D-BIT00), Level 1

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-development-hkms-digital-3d-bit00
- **Publisher:** Lands Department
- **Formats:** MAX, 3DS, FBX, VRML
- **Level 1 definition (verified):** every building and/or podium with a footprint area greater
  than **4 m²** in the B1000 digital topographic map, **extruded from its footprint** between the
  relevant building base and top level, with **no photorealistic texture applied**.
- **Why:** This is a low-poly building by construction. Use as primary massing source or as a
  cross-check against the non-textured models.

### ⚠️ PROBABLY NOT NEEDED — 3D Visualisation Map (Individualised models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-individualised-models
- **Formats:** MAX, FBX, glTF. Includes textures.
- **Official description (verified 2026-07-31):** "digital data of 3D models featuring geometry
  models **and texture maps** to represent the geometrical shape, **appearance** and position of
  different types of ground objects" — building, infrastructure, **vegetation, waterbody**,
  terrain and **generic (others)**. The non-textured set's description is the same sentence minus
  the texture maps, minus "appearance", and minus three object classes: it ships building,
  infrastructure and terrain only.
- ⚠️ **"Individualised" does not mean "per-object separated."** It distinguishes this set from
  **tile-based** (one welded photogrammetry mesh per tile), not from non-textured. Both per-building
  sets are individuated — a non-textured sheet unpacks to one `.gltf` per building (see "What a
  sheet actually contains") — and the **building count is identical: 59 in both** on `11-SW-9D`.
  Whole-sheet model counts differ only because individualised ships extra object classes (73 vs 69
  on `9D`, 769 vs 738 on `14B`). **Textured ≠ individualised** either, since tile-based carries
  textures too. Between *these two* sets, texture maps and object classes are the discriminators.
- **Coverage: whole territory, same sheet grid as non-textured** — the index is 3,456 features with
  the same `SHEETNO` scheme. All six Wan Chai sheets are present: `11-SW-9D`, `10C`, `10D`, `14B`,
  `15A`, `15B`.
- **The download discriminator is one character** in the format code — the trailing `0` *is* the
  non-textured variant. Same host, same sheet number, same shared key:

  ```
  …/api/3d-zip/GLTF0/11-SW-10C.zip?key=…   → non-textured      44 MB
  …/api/3d-zip/GLTF/11-SW-10C.zip?key=…    → individualised   753 MB
  ```

- ⚠️ **This bullet used to read "use only for the ~5 hero landmarks whose silhouettes LOD1
  extrusion destroys". The measurements below refute it** — the non-textured set carries the
  identical geometry, so this buys **texture maps and three extra object classes, not shape**. The
  only reason to reach for it is textures. See the verdict at the end of this section.

#### Measured cost (verified 2026-07-31)

Wan Chai in individualised form is **5.86 GB zipped** — 15–27× the non-textured equivalent:

| Sheet | Individualised | Non-textured |
|---|---|---|
| `11-SW-9D` | 588 MB | 40 MB |
| `11-SW-10C` | 753 MB | 44 MB |
| `11-SW-10D` | 1,091 MB | — |
| `11-SW-14B` | 1,329 MB | 49 MB |
| `11-SW-15A` | 1,094 MB | — |
| `11-SW-15B` | 1,002 MB | — |
| **Total** | **5,859 MB** | — |

**93–96% of that is texture**, read from the zip central directory without downloading the payloads:

| | `11-SW-9D` | `11-SW-14B` |
|---|---|---|
| Individualised — textures (jpg + png) | **545.9 MB — 93%** | **1,277 MB — 96%** |
| Individualised — geometry (bin + gltf) | 42.2 MB | 51.3 MB |
| Non-textured — terrain jpg (1 file) | 32.5 MB | 34.2 MB |
| Non-textured — geometry (bin + gltf) | 7.2 MB | 14.9 MB |

#### The two sets share their building geometry exactly (verified 2026-07-31)

**The buildings are the same models.** Sheet `11-SW-9D` carries **59 building models in both sets**,
and the per-building geometry is identical: **12 buildings sampled, 12 matched exactly** on both
triangle and vertex count, spanning 12 to 12,274 triangles. Both sets are unwelded at exactly 3.0
verts per triangle. Individualised splits a mesh into 1–4 primitives depending on how many textures
it takes, but the triangle total is unchanged.

**Building IDs match on a shared stem, with the variant in the suffix:**

```
BUILDING/B352631575201063C0/…   → non-textured     …C0
BUILDING/B352631575201063A0/…   → individualised   …A0
```

That makes the stem a **stable cross-dataset building key** — a landmark can be matched between the
two sets by ID, with no spatial join.

What actually differs per building is how the surface is described:

| | Non-textured | Individualised |
|---|---|---|
| Attributes | `POSITION`, `NORMAL`, **`COLOR_0`** | `POSITION`, `NORMAL`, **`TEXCOORD_0`** |
| Primitives | 1 | 4 (one per texture) |
| Materials / images | 1 / 0 | 4 / 4 |
| `.bin` for all 59 buildings | 14.0 MB | **12.2 MB** |

Individualised buildings are *slightly smaller* on disk — `TEXCOORD_0` costs less than `COLOR_0`.

**The extra ~94 MB of geometry is three object classes the non-textured set does not ship at all**,
not denser buildings. Uncompressed `.bin` by folder on `11-SW-9D`:

| Folder | Non-textured | Individualised |
|---|---|---|
| `BUILDING` (59 models) | 14.0 MB | 12.2 MB |
| `TERRAIN(TB)` | 8.1 MB | 8.1 MB |
| `INFRASTRUCTURE` (9 models) | 4.4 MB | 3.9 MB |
| `GENERIC` | — | **47.1 MB** |
| `INFRASTRUCTURE(TB)` | — | **36.5 MB** |
| `VEGETATION(TB)` | — | **12.8 MB** |
| `WATERBODY` | — | 0.0 MB |
| **Total** | **26.5 MB** | **120.7 MB** |

Shared classes are equal to within a rounding error. Terrain is byte-identical.

✅ **This confirms `P3-6` rather than reopening it.** The stated reason to reach for individualised
models is hero landmarks "whose silhouettes LOD1 extrusion destroys" — but that concern belongs to
**3D-BIT00 Level 1**, which is extruded from footprints by definition. The non-textured 3D
Visualisation Map is *not* an extrusion: it already carries the individualised set's exact
silhouette, at the same **612 triangles per building** measured elsewhere in this file (up to
~12k for the largest of 12 sampled). **Individualised therefore buys textures and three extra
object classes — not one triangle of extra shape.** `PLAN.md`'s `P3-6` already specifies authored
geometry with *"source geometry excluded"*; this measurement explains why that was the right call.
If hero landmarks need to read as landmarks, the lever is textures or hand-authored geometry, not
this dataset swap.

✅ **`P3-6` never needs the 5.9 GB.** `download.map.gov.hk` returns `Accept-Ranges: bytes`, so the
zip central directory can be read with a range request on the tail, and the hero building's
`.gltf`/`.bin` entries then pulled by byte range — leaving the ~700 MB of JPEGs undownloaded. That
is also how the split above was measured.

💡 **The "non-textured" download is itself 70–81% texture.** Each GLTF0 zip carries one terrain
JPEG — 32.5 MB of a 40 MB sheet — for the terrain *texture*, rejected under "Terrain does not fit
any budget". The terrain mesh itself stays in the pipeline regardless: it is the height field `Q11`
is resolved by sampling.
Actual building geometry is only ~7–15 MB per sheet.

### ❌ DO NOT USE — 3D Visualisation Map (Tile-based models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-tile-based-models
- **What it is:** Oblique-photogrammetry mesh, 150 m × 150 m tiles, OBJ / OSGB / Cesium 3D Tiles.
- **Why rejected:** A prior public attempt downloaded ~10,000 tiles and imported them into Unity.
  Reported defects: **ground gaps, level differences, and vehicles baked into the mesh**. The
  author concluded it suited flight simulation rather than driving. Tiles also carry **no
  transform metadata**.
- Decimating photogrammetry does not produce low-poly style — it produces blobs, and destroys the
  semantic separation between road, building, and street furniture.
- Reference: https://medium.com/@devlog/data-of-3d-visualisation-map-from-hk-landsd-4507ffdef598

---

## Roads

### ✅ USE — Road Network (2nd Generation)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2
- **Publisher:** Transport Department, part of the Intelligent Road Network Package (IRNP)
- **Formats:** File Geodatabase (FGDB, zipped), KML, GML+GFS. Delta changes as CSV.
- **Update frequency:** Monthly. *(We snapshot once — do not track upstream.)*
- **Verified contents:** road centrelines, intersection points, bus-only lanes, speed limits,
  pedestrian zones, turn movement restrictions, vehicle restrictions, no-stopping zones,
  roundabouts, on/off-street parking access points, zebra crossings, toll plazas.
- **Known attributes:** `INT_ID` (intersection), `RD_ID` (centreline), `ROUTE_ID`,
  `TRAVEL_DIRECTION` (1 = bidirectional, 3 = single direction), `TURN_ID` with `EDGE(1-8)FID`
  for turn restrictions.
- **Known parsing difficulties (reported by a prior integrator):**
  - Dual carriageways are modelled as separate one-way segments that converge to a point.
  - A single physical junction may be represented by **two** intersections.
  - Turn-restriction representation is non-obvious.
  - Geometry appears under `<gen:lod4Geometry>` tags in the GML, in HK80 coordinates.
- Reference: https://medium.com/@devlog/parsing-hong-kong-road-network-data-5b9b80874704

### ✅ RESOLVED (2026-07-29) — no true Z, but grade separation IS encoded

Verified directly against the live data. **No fallback needed. The Wan Chai region choice holds.**

**Finding 1 — geometry is 2D.**
`CENTERLINE.gfs` declares `<GeometryType>2</GeometryType>` (OGR `wkbLineString`, 2D) with
`<SRSName>EPSG:2326</SRSName>`. In the GML, every `gml:posList` carries `srsDimension="2"` and
contains flat easting/northing pairs. There are **no Z ordinates**.

**Finding 2 — an integer `ELEVATION` attribute encodes the level.**
Each centreline feature has `<gen:intAttribute name="ELEVATION">`. Sampled across five ~500 KB
windows spanning the whole 486 MB file (148 features):

| Level | Share |
|---|---|
| `0` (ground) | 86.5% |
| `1` | 2.0% |
| `2` | 11.5% |

This is the standard GIS idiom for grade separation — an ordinal level, like OSM's `layer` tag —
not a measured height. Negative values (tunnels) are plausible but were not observed in the
sample; **handle them defensively.**

**This is arguably better than true Z for our purposes.** It gives clean topological separation —
which is all that's needed to avoid false junctions — while leaving deck heights to us. Authored
heights are smooth and game-friendly; raw survey Z would be noisy and need smoothing anyway.

**Implementation:** map `ELEVATION` → authored deck height in city config, e.g.
`{-1: -8.0, 0: 0.0, 1: 6.0, 2: 12.0}` metres, then ramp smoothly between levels at transitions.
Those are offsets from **ground level**, not from the vertical datum — see `Q11` and
`roads.ground` in city config.

> ⚠️ **Corrected by `P1-3` (2026-07-30).** This section previously ended "Two edges may only form
> a junction if their `ELEVATION` values match." That rule is right about *crossings* and wrong
> about junctions, and applying it breaks the network. Every one of the 36 endpoints in the Wan
> Chai region where two levels meet is a **ramp touching down** — `HUNG HING ROAD FLYOVER` at
> level 1 meeting itself at level 0, `WAN CHAI INTERCHANGE` (1)↔(0), `FLEMING ROAD` (1)↔(0).
> Keying nodes on the level takes the region from **6 connected components to 24**, drops the
> largest from 583 nodes to 389, and cuts a 163-node elevated island adrift.
>
> The rule was aimed at a real hazard — a flyover crossing *over* a street must not become a
> junction — but that hazard never arises, because nodes are formed only where centrelines share
> an **endpoint**, and a flyover crossing a street shares nothing with it.

### Other verified facts from the same inspection

- **Bilingual street names ship in the source**: `STREET_ENAME` / `STREET_CNAME`, plus
  `ALIAS_ENAME` / `ALIAS_CNAME`. Names confirmed present for our region — Hennessy Road, Lockhart
  Road, Jaffe Road, Arsenal Street, Yun Ping Road. **We do not need to hand-author road names.**
- **`-99` is the null sentinel** for string fields (and `–９９` in the Chinese field, in full-width
  characters). The ETL must treat both as null.
- Format is **CityGML 2.0** — features are `gen:GenericCityObject` with geometry under
  `gen:lod4Geometry` → `gml:LineString`. Despite the `lod4` name, the geometry is 2D.
- **`CENTERLINE.gml` is ~486 MB** for the whole territory. **Stream and clip to the region — never
  load it whole.** Prefer the FGDB with an OGR spatial filter. *(`P1-3` did; `Q9` resolved.)*
- Data was last modified 2026-07-29 — actively maintained on a monthly cycle.

### ✅ MEASURED (2026-07-30) — what `P1-3` found in the geodatabase

Read with `pyogrio` (GDAL 3.12.4) through `/vsizip/`, clipped to the Wan Chai region by OGR
spatial filter. **796 centrelines, 529 intersections, 217 turns, 83 speed limits, 14 bus lanes.**
Everything below is measured on that selection, and the numbers are what `etl/pipeline/roads.py`
is built around.

**The geodatabase holds all seventeen layers** — `CENTERLINE`, `INTERSECTION`, `TURN`,
`SPEED_LIMIT`, `BUS_ONLY_LANE`, `ROUNDABOUT`, `PROHIBITION`, `NSR`, `PEDESTRIAN_ZONE`,
`TRAFFIC_FEATURES`, `VEHICLE_RESTRICTION`, `PERMIT`, `RUN_IN_OUT`, `ONSTREETPARK`,
`GISP_ON_STREET_PARKING`, `TUN_BRIDGE_TOLL`, `TUN_BRIDGE_TV_TOLL`. There is no reason to fetch
any per-layer GML.

**Centrelines are `Measured MultiLineString`.** GDAL drops the M ordinate on read and says so in
a warning; the geometry that arrives is plain 2D, which is what the schema declares. Every
feature in the region is single-part.

| Finding | Measurement | Consequence |
|---|---|---|
| Endpoints coincide **exactly** | 601 distinct at full float precision, 599 at millimetre rounding; nearest *distinct* pair **2.26 m** apart | Nodes by coordinate identity. No snapping tolerance to tune — anything from ~1 mm to ~1 m gives the same graph. It must be at least ~1 mm: two clusters differ in the last bits and merge only once rounded. |
| Geometry is **wildly over-densified** | one 51.7 m centreline carries **54,330 vertices** (median segment 0.4 mm); five features hold 132k of the region's 176k | Douglas–Peucker at 0.2 m is a correctness measure for `P1-4`, not a size optimisation. 175,610 → 3,553 vertices, worst deviation 0.1997 m. |
| `ROUTE_ID` is **1:1 with the centreline** | 796 distinct values across 796 features | `SPEED_LIMIT.ROAD_ROUTE_ID` and `BUS_ONLY_LANE.ROAD_ROUTE_ID` join by key. No linear referencing needed, despite both being modelled as route events. |
| Speed limits cover **under 10%** | 77 of 796 edges, all `70 km/h` or `80 km/h`, as free text with units | Hong Kong signs only exceptions to the 50 km/h urban default, so the default must come from city config. |
| **Lane counts do not exist** | no lane attribute in any field of any layer | `roadgraph.json`'s `lanes` is authored policy keyed on speed limit, not published data. |
| `ELEVATION` **negatives are real** | 0 (736), 1 (45), **−1 (15)** — the Cross-Harbour Tunnel and the Central–Wan Chai Bypass | The defensive `-1` mapping added before any negative was seen turns out to be load-bearing. |
| Dual carriageways are **opposed one-way pairs** | 6 places in the emitted graph where two one-way edges share both endpoints in opposite directions, separated by **1.96–3.85 m** (median 2.9 m); three of them are Lockhart Road, at 2.73 / 3.07 / 3.41 m | Lockhart Road is two-way *modelled as two one-ways*. `P1-4` must expect two ribbons ~3 m apart, not one. This is a **lower bound** on the pattern — carriageways that do not share both endpoints are not counted. |
| Turn geometry is a **hint, not the truth** | `EDGE1END` names an end that touches the second edge in 213 of 217; in the other 4 the *opposite* end coincides exactly | Take the shared node; use the field only to break ties. All 217 then resolve. |
| The **null sentinel has four spellings** | `-99`, and three using full-width digits with an en-dash or a full-width hyphen (`–９９`, `－９９`, `-９９`) | Normalise NFKC *and* fold Unicode dashes before comparing. A raw string compare catches one of four. |

**Feature identity is the FGDB `OBJECTID`**, which OGR returns as the feature id. `TURN` points at
centrelines through `EDGE(1-8)FID` and `INTERSECTION` through `RD_ID_1..10`; both are OBJECTIDs, so
a reader that renumbers features on a filtered read resolves every restriction onto the wrong roads.

**Attributes `P1-3` reads but does not emit**, recorded so they are not rediscovered: `TURN` carries
`EXC_VEH_TYPE` / `INC_VEH_TYPE` (vehicle classes the restriction does *not* apply to — `TX` = taxi,
and one restriction in the region excludes taxis), `PART_TIME_REST`, `EFF_ALL_DAYS` and
`OTHER_REST_TYPE`. `roadgraph.json`'s `turn_restrictions` has no field for any of them. They matter
for `P3-3` traffic and `P3-8`, and adding them is a schema change on both sides.

---

## Direct download URLs

Discovered via the data.gov.hk CKAN API (`package_show?id=hk-td-tis_15-road-network-v2`). These
save rediscovery — verify they still resolve before relying on them.

> **Only the first two are in `hong_kong.yaml`.** `P1-3` reads the geodatabase, which contains
> every layer in 17 MB; the per-layer GML below is the same content in 539 MB. The rest are kept
> here as a record of what the publisher offers, not as things to fetch. Resolves `Q9`.

| Resource | URL |
|---|---|
| Data dictionary | `https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip` |
| Consolidated file list | `https://static.data.gov.hk/td/road-network-v2/dataspec/file_list.csv` |
| Full FGDB | `https://static.data.gov.hk/td/road-network-v2/RdNet_IRNP.gdb.zip` |
| Centrelines | `https://static.data.gov.hk/td/road-network-v2/CENTERLINE.gml` (+ `.gfs`) |
| Intersections | `https://static.data.gov.hk/td/road-network-v2/INTERSECTION.gml` |
| Bus-only lanes | `https://static.data.gov.hk/td/road-network-v2/BUS_ONLY_LANE.gml` |
| Roundabouts | `https://static.data.gov.hk/td/road-network-v2/ROUNDABOUT.gml` |
| Pedestrian zones | `https://static.data.gov.hk/td/road-network-v2/PEDESTRIAN_ZONE.gml` |
| Prohibitions | `https://static.data.gov.hk/td/road-network-v2/PROHIBITION.gml` |
| No-stopping restrictions | `https://static.data.gov.hk/td/road-network-v2/NSR.gml` |

The CKAN API itself is the reliable way to enumerate all 61 resources:
`https://data.gov.hk/en-data/api/3/action/package_show?id=hk-td-tis_15-road-network-v2`

---

## Fares and points of interest

Both datasets below are read by `P1-5`. Verified 2026-07-31.

**data.gov.hk lists only a portal link for each — no direct file.** The CKAN API returns a single
resource of format `API` pointing at the CSDI geoportal. The downloadable URL is the CSDI
`file-api`, the same endpoint the buildings sheet index uses, keyed on the CSDI dataset id:

```
https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=<id>&format=geojson
```

Unlike the buildings index these carry **no API key and need no `layer_name`**, so the URLs live
in `hong_kong.yaml` directly. Both are whole-territory point GeoJSON, and both are small enough
to fetch and filter in full.

Two properties are shared by both and matter to the pipeline:

- **`crs` is absent**, which is CRS84 per RFC 7946 — WGS84 lon/lat. Declared explicitly in config
  rather than assumed, like every other datum in this project.
- **Positions are quantised to whole metres on the HK1980 grid.** Published as lon/lat to ten
  decimal places, but every point round-trips to an exact metre (e.g. E 835010.0003,
  N 815587.9997). So a fare node carries about half a metre of its own positional uncertainty.

### ✅ USE — Taxi Stands

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_37-taxi-stands
- **CSDI dataset id:** `td_rcd_1697081907714_17556` — 518 features, 343 KB.
- Update frequency: twice per year.
- **Gameplay use:** pickup hotspots. The *Cross Harbour* category becomes a distinct premium fare
  type that terminates at the tunnel approach — a fare that only makes sense in Hong Kong.

**⚠️ `Status_EN` is free text, not an enum.** It carries the licensing category *and*, in eight
cases, an operating-time restriction after an embedded newline. All sixteen spellings in the
territory, with the category `fares.groups[].categories` maps each to:

| Count | `Status_EN` | → |
|---:|---|---|
| 312 | `Urban Taxi Stand` | `urban` |
| 75 | `Both of Urban and NT Taxi Stand` | `urban_and_nt` |
| 68 | `NT Taxi Stand` | `nt` |
| 30 | `Cross Harbour Taxi Stand` | `cross_harbour` |
| 21 | `Lantau Taxi Stand` | `lantau` |
| 2 | `Cross Harbour Taxi Stand\n(2200-0700 daily)` | `cross_harbour` |
| 1 | `Cross Harbour Taxi Stand\n(0000-0500 on Sat & Sun)` | `cross_harbour` |
| 1 | `Cross Harbour Taxi Stand\n(1200-0600 daily)` | `cross_harbour` |
| 1 | `Urban and Cross Harbour Taxi Stands` | `cross_harbour` |
| 1 | `Urban and NT Taxi Stand` | `urban_and_nt` |
| 1 | `NT Taxi Stand\n(2300-0630 daily)` | `nt` |
| 4 | `Urban Taxi Stand` + a time note (four spellings) | `urban` |

Matching is **first-hit-wins over substrings**, so rule order is load-bearing: `Urban and NT`
must precede `NT Taxi Stand`, which must precede `Urban`. `load_city` refuses a table where an
earlier rule would always shadow a later one, and `test_config.py` pins all sixteen spellings —
the Wan Chai region only ever exercises two of them.

`Q14`: the operating-time restrictions are **discarded**. There is no contract field for them and
no consumer; a part-time cross-harbour stand is currently modelled as a full-time one.

### ✅ USE — Taxi Pick-up & Drop-off Points

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_38-taxi-pick-up-drop-off-points
- **CSDI dataset id:** `td_rcd_1697082382328_14459` — 275 features, 192 KB.
- Update frequency: twice per year.
- **Gameplay use:** legal drop-off targets; denser than stands.

`Status_EN` here has only two values, and the distinction is gameplay-relevant: **`Taxi PU/DF`**
(209) may be hailed at and delivered to, **`Taxi DF`** (66, a quarter of the dataset) is
**drop-off only**. Carried into `fares.json` as `pickup`/`dropoff` rather than flattened.

### Names, in both datasets

`Location_EN` / `Location_TC` are populated on **every** feature in both datasets — the
acceptance criterion for bilingual names is satisfied by the source, not by a fallback. Two
traps:

- **31 of the 793 names contain embedded newlines**, wrapping a long place name across lines.
  Collapsed to single spaces by `clean_text`; a fare node's name goes on the HUD.
- **98 names use full-width brackets** (`（1）`). `clean_text` returns **NFC** and folds to NFKC
  only for the null-sentinel comparison, because NFKC is a *compatibility* fold and would rewrite
  those as ASCII — wrong typography in Chinese. This changed nothing for `P1-3`: all 198 road
  names in the region are already NFC, and `roadgraph.json` is byte-identical across the change.

`Location_SC` (simplified) is not read — Hong Kong sets traditional. It is also the only field in
either dataset with an observed data-entry error: one `Taxi DF` row carries the traditional
`的士落客點` in the simplified column.

### Snapping fare nodes to the road graph (`P1-5`)

Measured across the region's 29 points, and the reason no tie-breaking rule exists:

- Distance to the nearest centreline: **1.18–8.37 m** (median 3.2 m) — about half a carriageway,
  which is what a kerbside point against a centreline graph should measure.
- Margin over the *second* nearest edge: **at least 4.28 m**. Never ambiguous.
- **28 of the 28** nodes whose snapped edge has an English name land on a street whose name
  appears in that point's own free-text `Location_EN`. The geometry pipeline never reads that
  prose, so this is independent corroboration rather than a tautology.
- Every winner is at **elevation level 0**. One level-1 edge appears as a runner-up, losing by
  7 m. `Q15`: the sources are 2D, so a stand under a flyover has nothing in it to prefer the
  street below over the deck above. Plan distance is the only defensible measure; a city with
  stands under elevated roads would need height in the source to do better.

> **Region note:** Hong Kong Island uses **red urban taxis**. Green (NT) or blue (Lantau) livery in
> this map would read as wrong to any local player.

---

## Coordinate systems

| Item | Value |
|---|---|
| Source CRS | **HK1980 Grid System, EPSG:2326** (Transverse Mercator) |
| Vertical datum | Hong Kong Principal Datum (HKPD) |
| Tile-based model quirk | Drawn in **HK80 coordinates minus 800,000** (rejected dataset, recorded for completeness) |
| Game space | Local ENU metres, **origin at region NW corner** (`Q7`) |

**Godot axis convention** (Y-up, right-handed):

```
game_x =  (easting  - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing - origin_northing)
```

The `-Z` is forced by handedness; the *origin corner* was the free choice, and it is north-west so
the region lands in the positive quadrant. Reasoning in `ARCHITECTURE.md`, "Coordinates".

Keep this conversion in `etl/pipeline/crs.py` only. Nothing else in the pipeline may assume
EPSG:2326.

---

## Region of interest (PoC)

**Wan Chai → Causeway Bay north-shore corridor.**

| Bound | Value |
|---|---|
| West | 114.172 E |
| East | 114.188 E |
| South | 22.276 N |
| North | 22.284 N |
| Approx. size | 1.65 km × 0.9 km ≈ **1.5 km²** |
| Tiles @ 150 m | 66 (computed, matches the earlier estimate) |
| **Datum of the bounds above** | **WGS84 — confirmed against real geometry, 2026-07-30** |

### ⚠️ The datum of these bounds is load-bearing

HK1980 and WGS84 differ by **~304 m on the ground** in Hong Kong — far more than the ~10 m people
expect. These four numbers were authored without stating a datum, and the two readings select
**different sheets**: WGS84 gives a contiguous `11-SW` block, HK1980 swaps two of the six for
`11-SE-11A` and `11-SE-6C`. A third of the region, decided by an unstated assumption.

**Resolved by measurement, not inference.** Sheet `11-SW-10C` was downloaded and its building
positions compared against both readings:

| | Easting | Northing |
|---|---|---|
| **Actual building positions** | 836006–836752 | 815600–816173 |
| Sheet bbox **if index is WGS84** | 836000–836750 | 815600–816200 |
| Sheet bbox if index is HK1980 | 836252–837003 | 815431–816031 |

The terrain node sits at exactly (836375, 815900) — the WGS84-projected sheet centre to the metre.
`etl/config/cities/hong_kong.yaml` therefore declares `crs.geodetic: EPSG:4326`, and the loader
refuses to run without an explicit datum.

### Covering sheets (`P0-1`, resolved 2026-07-30)

Six 1:1000 sheets cover the region. glTF is delivered **per sheet**, ~44 MB each, so the full
region is **~280 MB** of source download:

```
11-SW-9D    11-SW-10C   11-SW-10D
11-SW-14B   11-SW-15A   11-SW-15B
```

Do not hardcode this list. `P1-1` derives it by intersecting the region bounds with the fetched
sheet index, so a bounds change or a second city re-derives it for free.

Key roads: Gloucester Road, Harbour Road, Hennessy Road, Lockhart Road, Jaffe Road, Johnston Road,
Queen's Road East, Canal Road East/West + flyover, Yee Wo Street, Percival Street.

Natural map edges: Victoria Harbour (north), the escarpment toward Kennedy Road / Mid-Levels
(south), Admiralty (west), Victoria Park (east).

---

## Access notes

### Roads — fully scriptable ✅

Direct static URLs (see table above), enumerable via the data.gov.hk CKAN API. No key, no portal,
no account. This half of the pipeline is solved.

⚠️ **The two formats are redundant, and one is 31× larger.** Measured 2026-07-30:

| File | Size | |
|---|---|---|
| `RdNet_IRNP.gdb.zip` | **17.4 MB** | FGDB — **every layer** |
| `CENTERLINE.gml` | 485.9 MB | one layer |
| `INTERSECTION.gml` | 49.0 MB | one layer |
| `PROHIBITION.gml` | 3.2 MB | |
| `ROUNDABOUT.gml` | 0.7 MB | |
| `BUS_ONLY_LANE.gml` | 0.4 MB | |
| `CENTERLINE.gfs` | 2.6 KB | schema for the above |
| `dataspec/rdnet_dataspec.zip` | 1.3 MB | data dictionary |

Same content; GML spends its bytes on XML tags. `hong_kong.yaml` lists both because `P1-3` has not
chosen a reader yet — see `PROGRESS.md`, `Q9`. Drop the loser once it has.

### Buildings — fully scriptable ✅

> **Correction, 2026-07-30.** This section previously stated that the building datasets expose
> **no direct download URLs** and that the only API served rejected Cesium 3D Tiles behind an
> emailed key. **Both are wrong**, and that error made "buildings are unautomatable" the project's
> top data risk for a day. Corrected below against a real download. The mistake was reading the
> CKAN resource list — which does only point at portals — and stopping there, instead of opening
> the portal's own download panel.

**The sheet index is the API.** The CSDI portal's Downloads panel serves the non-textured dataset
as ordinary GIS vector formats, not as 3D models. What you get is a **territory-wide index of
3,456 sheet polygons**, each carrying direct download URLs for the models themselves:

| Property | Example |
|---|---|
| `SHEETNO` | `11-SW-10C` |
| `Format_glTF` | `https://download.map.gov.hk/api/3d-zip/GLTF0/11-SW-10C.zip?key=…` |
| `Format_FBX` | `…/api/3d-zip/FBX0/11-SW-10C.zip?key=…` |
| `Format_MAX` | `…/api/3d-zip/MAX0/11-SW-10C.zip?key=…` |
| `REVISIONDATE` | `20260424` (for `11-SW-10C`; it is genuinely per sheet — `1-SE-19D` reads `20250929`) |

- **One public key is shared by all 3,456 sheets** — not per-user, not per-session. It is baked
  into an index anyone can download.
- ⚠️ **Do not hardcode the key into `hong_kong.yaml` or any committed file.** `P1-1` fetches the
  index and reads URLs out of it. The index is the source of truth, and a rotated key then costs
  nothing.
- `REVISIONDATE` is per sheet — use it as the cache key so re-runs are idempotent.
- Index CRS is **WGS84** (GeoJSON with `crs: null`, i.e. CRS84 per RFC 7946). Confirmed against
  real geometry, not assumed — see "Region of interest" below.

**The index itself has a direct URL** — confirmed 2026-07-30 by `P1-1`, and it is what makes a
fresh clone able to fetch without anyone visiting the portal:

```
https://portal.csdi.gov.hk/csdi-webpage/file-api
    ?dataset_id=landsd_rcd_1742809441342_98380
    &format=geojson
    &layer_name=Nontextured_models
```

Verified to return bytes **identical by SHA-256** to the portal's own download button (3,167,143 B,
`38e270f8…`). No key, no session, no account. The endpoint is parameterised by dataset, format and
layer rather than being one-off, so it generalises to any CSDI dataset — including 3D-BIT00.

✅ **The generalisation is verified, not assumed** (2026-07-31). Swapping in the individualised
dataset returned its 3,456-feature index with no key, no session and no account:

```
https://portal.csdi.gov.hk/csdi-webpage/file-api
    ?dataset_id=landsd_rcd_1671676915450_88604
    &format=geojson
    &layer_name=Individualised_models
```

Its features carry the same `SHEETNO` / `REVISIONDATE` / `Format_glTF|FBX|MAX` properties as the
non-textured index, plus `URL_3D_Visualisation_Map` and `Download_API`. Layer names come from the
ISO 19139 record — grep it for `layer_name=` rather than guessing the capitalisation.

It is published in the portal's ISO 19139 metadata record, which is the thing to re-read if the URL
ever stops working:
`https://portal.csdi.gov.hk/geoportal/rest/metadata/item/<datasetId>`. That record also advertises
WFS, WMS and an ArcGIS `FeatureServer` for the same layer — server-side bbox queries are available
if the 3.2 MB whole-index download ever becomes inconvenient. It has not.

**Portal entry points** (for a human re-checking the index):

- Non-textured models: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1742809441342_98380`
- Individualised models: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1671676915450_88604`
- 3D-BIT00: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637306559892_42396`

**The Cesium 3D Tiles API remains irrelevant**, and that part of the old note stands:
`https://data.map.gov.hk/api/3d-data/3dtiles/{sheet}/tileset.json` serves the tile-based
photogrammetry variant we rejected. We do not need it, and we do not need a key from
`3dmap@landsd.gov.hk`.

### What a sheet actually contains

Measured by downloading `11-SW-10C` in glTF (2026-07-30):

| | |
|---|---|
| Download size | **44.3 MB** zipped, ~65 MB unpacked |
| Sheet extent | ~744 m × 603 m |
| `BUILDING/` | 151 buildings — one `.gltf` + `.bin` each, `default_material`, **no textures** |
| `INFRASTRUCTURE/` | 12 items, sitting 2.4–9.3 m up — very likely elevated road structures |
| `TERRAIN(TB)/` | 1 mesh, 250,911 verts, **one `.jpg` texture** |

Three findings that shape `P1-2`:

1. **Coordinates already match Godot's convention.** Each node's matrix translates to
   `(easting, elevation, -northing)` in HK1980 grid metres — exactly the conversion in
   `ARCHITECTURE.md`. `GameTransform` reduces to subtracting the region origin; there is no axis
   work to do.
2. **Vertices are unwelded — exactly 3.0 per triangle.** Flat shading is baked in, which is the
   art direction's native form. Never weld on position alone and never regenerate normals; `P1-2`
   welds on *position and facing together*, which is lossless and removes the repetition.
3. **"Non-textured" describes the buildings, not the terrain.** Terrain ships with a JPEG — one
   **7531 × 6031** texture per sheet, 45 megapixels. See the terrain verdict below.

### Measured across all six sheets (`P1-2`, 2026-07-30)

The one sheet downloaded by hand turned out to be among the sparsest, so extrapolating from it was
low by 2.4×.

| | `11-SW-10C` | All six sheets |
|---|---|---|
| Buildings | 151 | **2,200** — `11-SW-14B` alone has 720 |
| Infrastructure items | 12 | 74 |
| Terrain meshes | 1 | 6 |
| Terrain texture | 39.1 MB | **224 MB** |

⚠️ **Triangle budget pressure — confirmed, then mitigated.** 612 triangles per building. Clipped to
the region, `P1-2` emits **989k triangles at LOD0**, 400k at LOD1 and 184k at LOD2, against a
**<300k visible** budget. Vertex-clustering LOD tiers are what make that fit, so the risk now sits
with `P2-1`'s switch distances rather than with the ETL.

⚠️ **Infrastructure meshes are enormous and unbounded.** `INFRASTRUCTURE/` holds elevated road
structures, and one of them is **1,984 m long in a single mesh** with 208k triangles. Anything that
buckets source meshes spatially has to handle a mesh larger than its own bucket — see `P1-2`'s
tile assignment.

❌ **Terrain does not fit any budget as it ships.** Clipped to the region it is still 404,669
triangles, and its six GLBs total **267 MB** — of which **224 MB is the JPEGs**, carried through
untouched, and 43 MB is geometry. Clipping removes triangles, not texture. Over on triangles,
texture memory and bundle size at once, by roughly 2× each. The source is ~10 px/m, which is
survey resolution for ground seen at 60 km/h; resampling to ~2 px/m (~6 MB as ASTC) and
decimating to ~88k triangles would bring it into range,
but that work is not scheduled. It is still parsed and still worth keeping, because it is a
**height field** and `Q11` needs one: Road Network v2 carries no Z, and ground level in Wan Chai is
~4 m above the datum rather than 0. `python -m pipeline.buildings --terrain` emits it separately
for evaluation; the tile output contains no textures at all. See `PROGRESS.md`.
