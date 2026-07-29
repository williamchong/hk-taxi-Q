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
- **Formats:** MAX, FBX, **glTF**
- **Content:** Geometry and position only — no textures.
- **Coverage:** Whole territory of Hong Kong.
- **Why:** Flat-shaded extruded volumes are exactly the target art style. No decimation needed.

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
| Tiles @ 150 m | ~66 |

Key roads: Gloucester Road, Harbour Road, Hennessy Road, Lockhart Road, Jaffe Road, Johnston Road,
Queen's Road East, Canal Road East/West + flyover, Yee Wo Street, Percival Street.

Natural map edges: Victoria Harbour (north), the escarpment toward Kennedy Road / Mid-Levels
(south), Admiralty (west), Victoria Park (east).

---

## Access notes

### Roads — fully scriptable ✅

Direct static URLs (see table above), enumerable via the data.gov.hk CKAN API. No key, no portal,
no account. This half of the pipeline is solved.

### Buildings — portal-only ⚠️

**Verified 2026-07-29 via CKAN:** the non-textured 3D Visualisation Map and 3D-BIT00 datasets
expose **no direct download URLs**. Every resource points at an interactive portal:

- `portal.csdi.gov.hk/geoportal/?datasetId=...` — map-based selection UI
- `hkmapservice.gov.hk/OneStopSystem/map-search?product=OSSCatB&series=3D-BIT00` — likely requires
  an account

**The documented 3D Visualisation Map API does not help us.** It serves
`https://data.map.gov.hk/api/3d-data/3dtiles/{sheet}/tileset.json` — **Cesium 3D Tiles**, i.e. the
tile-based photogrammetry variant we rejected. It also needs an API key (free on request from
`3dmap@landsd.gov.hk`, GIS Projects Section, LandsD) and is rate-limited to 5 GB/s and 100
concurrent users.

**Assessment: this is not a blocker for the vertical slice.** The region is ~1.5 km², which is a
small number of 1:1000 sheets — a one-off manual download. Automation only matters when adding
cities, which is a Phase 4+ concern.

**Options, in order of preference:**
1. **Manual download** of the region's sheets via the CSDI portal. Sufficient for the slice.
   Record exactly which sheets were taken so the step is reproducible.
2. **Email `3dmap@landsd.gov.hk`** and ask whether a programmatic endpoint exists for the
   non-textured or 3D-BIT00 products. Costs one email; keys are issued free.
3. **Reverse-engineer the portal's download URL structure.** A prior integrator did exactly this
   for the tile-based product and automated ~10,000 downloads. Last resort — brittle, and be a
   good citizen about request rates.

⚠️ **Still open (`P0-1`):** which 1:1000 sheet numbers cover the region, and whether non-textured
glTF is delivered per sheet or per tile.
