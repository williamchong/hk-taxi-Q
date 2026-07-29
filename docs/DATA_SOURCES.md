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

### ✅ USE (sparingly) — 3D Visualisation Map (Individualised models)

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-individualised-models
- **Formats:** MAX, FBX, glTF. Includes textures.
- **Use only for the ~5 hero landmarks** whose silhouettes LOD1 extrusion destroys.

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
Two edges may only form a junction if their `ELEVATION` values match.

### Other verified facts from the same inspection

- **Bilingual street names ship in the source**: `STREET_ENAME` / `STREET_CNAME`, plus
  `ALIAS_ENAME` / `ALIAS_CNAME`. Names confirmed present for our region — Hennessy Road, Lockhart
  Road, Jaffe Road, Arsenal Street, Yun Ping Road. **We do not need to hand-author road names.**
- **`-99` is the null sentinel** for string fields (and `–９９` in the Chinese field, in full-width
  characters). The ETL must treat both as null.
- Format is **CityGML 2.0** — features are `gen:GenericCityObject` with geometry under
  `gen:lod4Geometry` → `gml:LineString`. Despite the `lod4` name, the geometry is 2D.
- **`CENTERLINE.gml` is ~486 MB** for the whole territory. **Stream and clip to the region — never
  load it whole.** Prefer the FGDB with an OGR spatial filter.
- Data was last modified 2026-07-29 — actively maintained on a monthly cycle.

---

## Direct download URLs

Discovered via the data.gov.hk CKAN API (`package_show?id=hk-td-tis_15-road-network-v2`). These
save rediscovery — verify they still resolve before relying on them.

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

### ✅ USE — Taxi Stands

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_37-taxi-stands
- Categories include **Urban, NT, Lantau, NT and Urban, and Cross Harbour**.
- Update frequency: twice per year.
- **Gameplay use:** pickup hotspots. The *Cross Harbour* category becomes a distinct premium fare
  type that terminates at the tunnel approach — a fare that only makes sense in Hong Kong.

### ✅ USE — Taxi Pick-up & Drop-off Points

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_38-taxi-pick-up-drop-off-points`
- Update frequency: twice per year.
- **Gameplay use:** legal drop-off targets; denser than stands.

> **Region note:** Hong Kong Island uses **red urban taxis**. Green (NT) or blue (Lantau) livery in
> this map would read as wrong to any local player.

---

## Coordinate systems

| Item | Value |
|---|---|
| Source CRS | **HK1980 Grid System, EPSG:2326** (Transverse Mercator) |
| Vertical datum | Hong Kong Principal Datum (HKPD) |
| Tile-based model quirk | Drawn in **HK80 coordinates minus 800,000** (rejected dataset, recorded for completeness) |
| Game space | Local ENU metres, origin at map SW corner |

**Godot axis convention** (Y-up, right-handed):

```
game_x =  (easting  - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing - origin_northing)
```

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

It is published in the portal's ISO 19139 metadata record, which is the thing to re-read if the URL
ever stops working:
`https://portal.csdi.gov.hk/geoportal/rest/metadata/item/<datasetId>`. That record also advertises
WFS, WMS and an ArcGIS `FeatureServer` for the same layer — server-side bbox queries are available
if the 3.2 MB whole-index download ever becomes inconvenient. It has not.

**Portal entry points** (for a human re-checking the index):

- Non-textured models: `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1742809441342_98380`
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
   art direction's native form. Do not weld; do not generate normals.
3. **"Non-textured" describes the buildings, not the terrain.** Terrain ships with a JPEG. We
   generate the road surface from the road graph (`P1-4`), so terrain is expected to be discarded
   — decide explicitly in `P1-2` rather than importing it by accident.

⚠️ **Triangle budget pressure.** 92,457 triangles across 151 buildings — **612 per building**,
far more than an LOD1 extrusion needs. Extrapolated over six sheets that is ~555k triangles against
a **<300k visible** budget. Not fatal (visible ≠ total, and HK street canyons occlude heavily) but
it makes `P1-2`'s decimation and LOD tiers load-bearing rather than optional.
