# Data Sources

Facts verified against primary sources. If one turns out wrong, correct it here and record the
finding in `DECISIONS.md`. Which sources a build fetches is `etl/config/hong_kong.yaml`
(`sources:`, `paged_sources:`, `tiled_sources:`); `pipeline/fetch.py` walks them into `etl/sources/`.

## Licence

All datasets below are published via DATA.GOV.HK and the CSDI Portal. Both grant the same six acts —
*browse, download, distribute, reproduce, hyperlink to, print* — for **commercial and non-commercial
use, free of charge**, with no usage limit, quota or volume cap. Read verbatim 2026-08-02.

- **Attribution is stronger than naming a source**: acknowledge the Government's and the relevant
  organisations' *ownership of the intellectual property rights*, and name **both** portals.
- The indemnity is real and broad. Data is supplied "AS IS".
- "Adapt", "modify" and "derivative" appear in neither portal's terms. Expected: the restricted
  act for artistic works is *copying*, granted here as **reproduce**.

`LICENSING.md` is canonical — operative clauses, what may be relicensed, open legal items. Do not
restate the terms here.

### Required credits-screen text (draft)

> Contains geospatial data from the Lands Department, the Transport Department, the Highways
> Department, the Leisure and Cultural Services Department, the Buildings Department and the Food and
> Environmental Hygiene Department of the Government
> of the Hong Kong Special Administrative Region, obtained via DATA.GOV.HK and the Common Spatial
> Data Infrastructure (CSDI) Portal. **The Government of the HKSAR and the relevant organisations own
> the intellectual property rights in that data.** Used under the DATA.GOV.HK and CSDI Portal Terms
> and Conditions of Use. The Government of the HKSAR does not endorse this product.

The ownership sentence is not optional.

The build also bundles a typeface under CC BY 4.0 (`Q79`), whose attribution must travel with
**every distributed copy**. On the same screen:

> Street names are set in **Free HK Kai** (自由香港楷書) © 2016 Free Hong Kong Fonts, used under the
> Creative Commons Attribution 4.0 International licence.

Both texts ship on the start menu's CREDITS & LICENCES page from `game/tuning/menu_text.json` — the
English verbatim, with a Chinese rendering beside it. `game/tools/verify_menu.gd` fails `check.sh`
if the ownership sentence, either portal or the typeface's credit leaves the file, in either
language. Every wording change here is a change there. The lawyer's sight-check of both texts is
open (`LICENSING.md` item 2).

> **Legal note:** because this ships as a commercial product, have a Hong Kong IP lawyer sight-check
> landmark depiction and the credits text before launch. **Landmark depiction is the top item** —
> the data terms cleared the licensing question; building depiction is the one with a plausible
> adverse answer.

## Coordinate systems

| Item | Value |
|---|---|
| Source CRS | **HK1980 Grid System, EPSG:2326** (Transverse Mercator) |
| Geodetic CRS of region bounds and CSDI GeoJSON | **WGS84, EPSG:4326** (`crs` absent = CRS84, RFC 7946) |
| Vertical datum | Hong Kong Principal Datum (HKPD) |
| Game space | Local ENU metres, origin at region NW corner (`Q7`) |

```
game_x =  (easting  - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing - origin_northing)
```

- The conversion lives in `etl/pipeline/crs.py` only; the CRS pair is `pipeline/hongkong.py`.
- HK1980 and WGS84 geodetic differ by **~304 m on the ground** and select different sheets. The
  region bounds are WGS84, confirmed against geometry: sheet `11-SW-10C`'s buildings span easting
  836006–836752 / northing 815600–816173, the WGS84-projected sheet box.

## Regions and sheets

Regions are `hong_kong.yaml` `regions:` — `wan_chai` (114.172–114.188 E, 22.276–22.284 N, ~1.65 ×
0.9 km), `causeway_bay` (adjacent east), `sha_tin`, `mong_kok`, all the same 0.016 × 0.008° box.

Wan Chai is six 1:1000 sheets (`11-SW-9D`, `10C`, `10D`, `14B`, `15A`, `15B`). Never hardcode a
sheet list: `fetch.py` intersects the region bounds with the fetched sheet index. Hong Kong Island
uses **red urban taxis**; green (NT) or blue (Lantau) livery there reads as wrong.

---

## Buildings

### 3D Visualisation Map, non-textured models — in use

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-non-textured-models
  (CSDI `landsd_rcd_1742809441342_98380`). Lands Department. MAX, FBX, **glTF**; one zip per 1:1000
  sheet, 3,456 sheets, ~44 MB each.
- **Access:** the CKAN resource list points only at interactive portals; the sheet index is the API
  (`tiled_sources.buildings`):
  `https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=landsd_rcd_1742809441342_98380&format=geojson&layer_name=Nontextured_models`
  — WGS84 GeoJSON, properties `SHEETNO`, `Format_glTF`
  (`https://download.map.gov.hk/api/3d-zip/GLTF0/<sheet>.zip?key=…`), `REVISIONDATE` (the cache
  key). One public key is baked into the index: never write it into a committed file — `fetch.py`
  reads URLs at run time and records them through `redact()`.
- **A sheet:** `BUILDING/` one `.gltf` + `.bin` per building, `COLOR_0` and no UVs;
  `INFRASTRUCTURE/` elevated structures; `TERRAIN(TB)/` one mesh with one JPEG (70–81% of the zip).
- Node matrices translate to `(easting, elevation, -northing)` in HK1980 metres — already Godot's
  convention; `GameTransform` only subtracts the origin.
- Vertices are unwelded, exactly 3.0 per triangle, flat shading baked in. Never weld on position
  alone and never regenerate normals.
- 612 triangles per building: clipped to Wan Chai the finest tier is 989k against a <300k visible
  budget, so vertex-clustering LOD tiers are required.
- Infrastructure meshes are unbounded (one is 1,984 m): a spatial bucket must take a mesh larger
  than itself.
- **`INFRASTRUCTURE` is the only height source for off-grade roads**, and `pipeline/roads.py` also
  walks it laterally for `width_m` / `offset_m` on level-1 edges (`Q103`) — TD, iB1000 and HyD are
  2D plans, so a ray from a deck finds the street underneath. Traps:
  - Stacked decks (`CANAL ROAD FLYOVER`): follow the slab that continues the last, never the
    highest hit.
  - Not only decks: `ISLAND EASTERN CORRIDOR`'s stub finds structure 8.3 m below terrain;
    `roads.deck.max_below_terrain_m` gates it.
  - Tunnels have no structure; the level −1 portals' descent is outside the region.
  - Not watertight (`Q19`: 5.38% of edge slots open in source), so the lateral walk bridges gaps
    under 1.0 m and publishes a low percentile of an edge's stations.
- **Terrain** ships untextured: the JPEG is read at build time for per-vertex colour and discarded
  (`Q18`). It is also the height field (`Q11`); Wan Chai ground is ~4 m above datum.

### 3D Visualisation Map, individualised models — build-time reference only

- **Portal:** https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-individualised-models
  (CSDI `landsd_rcd_1671676915450_88604`, `layer_name=Individualised_models`).
- Same sheets and geometry as the non-textured set (12 of 12 sampled match), plus `TEXCOORD_0` and
  photo atlases. The download differs by one path segment: `…/3d-zip/GLTF0/…` non-textured,
  `…/3d-zip/GLTF/…` individualised (753 MB a sheet). Model IDs share a stem, suffix `…C0`
  non-textured / `…A0` individualised — a stable cross-dataset building key.
- **Use:** nothing ships. A landmark whose `source_paint` sets `reference_texture` samples the
  `…A0` atlas in `pipeline/landmarks.py`; the sheet zip is downloaded by hand to
  `etl/sources/individualised/<sheet>.zip` (HKCEC: `11-SW-9D.zip`). The façade surveys
  (`tools/facade_survey.py` and siblings) read it into `etl/sources/facade_colour/` and
  `facade_grammar/`.
- **Textures cannot ship**: `mesh.collapse` takes UVs from a cluster representative and
  `mesh.merge` refuses textured meshes. Wan Chai is 5.86 GB zipped, 93–96% texture.
- Imagery covers a median 14.3% of a building's wall area, biased to street faces (`Q37`), and
  2,429 of 3,203 atlases hold a grey filler colour over ≥ 20% of texels; the guard that rejects
  such a colour is a floor (`Q55`).
- Extra classes, refused: `VEGETATION(TB)` (1.52 M triangles, 3.0× the shipped city), `GENERIC`
  and `INFRASTRUCTURE(TB)` are one welded photogrammetry blob per sheet. `WATERBODY` is hillside
  features, not the harbour.

### iB1000 Digital Topographic Map (FGDB) — in use

- **Portal:** `https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637223748322_25497`.
  Lands Department (Survey and Mapping Office). FGDB, GML, DGN, DWG; one zip per 1:1000 sheet
  (~42–45 MB), laid out `<SHEETNO>/<SHEETNO>.gdb`. 71 layers, EPSG:2326, levels in mPD. Schema
  authority: *iB1000 Data Dictionary — FGDB* v1.2 in `resources_iB1000_FGDB.zip`.
- **Access** (`tiled_sources.topography`): index
  `file-api?dataset_id=landsd_rcd_1637223748322_25497&format=geojson&layer_name=TileIndex` (3,333
  sheets, WGS84, no key); each `FGDB` property is
  `https://open.hkmapservice.gov.hk/OpenData/directDownload?productName=iB1000&sheetName=T<SHEETNO>&productFormat=FGDB`.
  The full-set links return 403 / 504 to a script; per-sheet is the only route. Read through
  `/vsizip/<zip>/<SHEETNO>/<SHEETNO>.gdb`.
- `open.hkmapservice.gov.hk` serves its TLS chain without the issuing intermediate (Hongkong Post
  e-Cert SSL CA 3 - 17). It is committed at `etl/config/certs/` and declared in `extra_cas` —
  verification is completed, never relaxed. Expires 2032-06-03.
- `fetch_margin_m` (320 m) fetches past the region: Wan Chai's own sheets stop 76 m north of it,
  short of the shoreline.
- Geometry is MultiPolygon **Z** with GDAL's wkb25D high-bit flag, not ISO 1000-offset codes;
  `gdb.py` accepts both and refuses M and EWKB-SRID.
- A sheet cut clips a feature into one piece per sheet with identical attributes;
  `podiums.stitch` regroups blocks (Wan Chai 1,595 pieces → 1,480).
- Three-letter codes collide with TD's: `TW` is *Tramway* here and a tactile warning strip in
  Traffic Aids Drawings; `RM` is *Road margin* here and a road-marking prefix there.

Layers read:

| Layer | Vocabulary | Use and traps |
|---|---|---|
| `Building` | `TYPEOFBUILDINGBLOCK` `T` building / `P` podium block / `OS` open-sided / `TS` temporary; `BASELEVEL`, `ROOFLEVEL` | Podium boundary in metres (`Q47`): `buildings.podium_blocks` → `podiums` stage → `podiums.json`. Levels are 100% filled on `T` and `P`. Footprints agree with the 3D set to 0.1 m. `P` is partial — Central Plaza has none; absence means none surveyed |
| `BUILDINGNAME` via `BUILDINGRELATEBUILDINGNAME` | `NAMESTATUS` `E` current / `O` old spelling | Bilingual building names for fare nodes (`fares.places`, `Q142`). Relate tables are non-spatial and a name can sit in another sheet than its footprint, so names are pooled across sheets first. Only `E` ships |
| `CartoTransLine` | `RM` road margin, `RMU` road margin under structure, `TW` tramway | `RM`: the carriageway edge, a publisher of the width survey (`Q95`); a raw perpendicular probe over-reads through junction mouths and across a dual. `TW`: the tram rails — a part is **one rail**, not a track centreline (`Q58`): gauge p50 1.124 m (published 1.067), track separation p50 2.597 m. The tramway is mostly off the drawn carriageway (18.8% of sections have both tracks on the ribbon) |
| `StreetCentreLines` | `STREETTYPE` `HIG` `TUN` `ROB` `SLR` `MAR` `SER` `TRA` `RER`; `ST_CODE` | Street hierarchy (`roads.street_class`). 25 of 585 codes carry two types, so an edge takes its nearest same-code segment. Lockhart, Jaffe and Harbour Road are `SER` |
| `UtilityPoint` | `UTILITYPOINTTYPE = LPO` lamp post (coded domain in the gdb) | `pipeline/lamps.py`. A position only: no height, arm or lantern; Z is 0.0. Every drawn dimension is authored. Not the same population as TD's `DTAD_GIPOLE_PT` |
| `Shoreline` | `SHORELINETYPE` `SWA` sea wall, `HWM` high water mark, `BRE` breakwater | The harbour (`pipeline/basemap.py`). No sea polygon exists (`HydroPolygon` is culverts and ponds), so the sea is cut from the frame along these lines; they do not close, so they are thickened by `basemap.seal_m` first. `SWA` and `BRE` are cut to a vertical quay, `HWM` slopes (`pipeline/shore.py`, `Q250`) |
| `CartoPedLine` | `PEDESTRIANTYPE` (domain `dPedestrianLineType`): `PA` pavement margin (including bicycle track margin), `PAU` pavement margin under elevated structures, `FP` footpath 0.5–1.5 m wide, `FPW` footpath > 1.5 m wide, `FBR` footbridge / elevated walkway, `FBU` footbridge under elevated structures, `STP` step, `SWY` pedestrian subway, `CWY` covered walkway | `pipeline/paths.py` (`Q250`): `PA`, `FPW` and `FP` laid on the ground as ribbons. Lines only, no faces and no surface class. `FP` is a centreline (nearest other `FP` line 21 m off at the median, Causeway Bay) and `FPW` a pair of edges (1.85 m). Wan Chai publishes 1,040 `PA` and no `FP` / `FPW`; Causeway Bay 1,308 `PA`, 286 `FP`, 73 `FPW`. Not a kerb: under 1 km of 62 km of `PA` lies within 1 m of the carriageway |
| `Site` | `SITECODE` `PAR` `PLA` `SOA` `SGR` `PRO` | Parks on the minimap and painted on the ground (`Q144`). `SITESTYPE` is an integer category — key on `SITECODE` |

Unread: `CartoPedLine` (pavement margin, steps, footbridges), hydrants, `UtilityNumber` lamp-post
numbers (`Q65`). `Tree` is Old and Valuable Trees only (9 in Wan Chai), not a street canopy.

### Rejected

- **3D Visualisation Map, tile-based models** —
  https://data.gov.hk/en-data/dataset/hk-landsd-openmap-3d-visualisation-map-tile-based-models.
  Oblique-photogrammetry mesh, 150 m tiles, OBJ / OSGB / Cesium 3D Tiles. **Never use (hard rule
  1):** a prior public attempt loaded ~10,000 tiles into Unity and reported **ground gaps, level
  differences, and vehicles baked into the mesh**. Tiles carry no transform metadata (drawn in HK80
  minus 800,000). Decimating photogrammetry produces blobs and destroys the separation between
  road, building and street furniture. Reference:
  https://medium.com/@devlog/data-of-3d-visualisation-map-from-hk-landsd-4507ffdef598
- **3D Spatial Data (3D-BIT00)** — never declared, fetched or read (`Q100`); iB1000, the map it is
  extruded from, fills its role.

---

## Roads

### Road Network (2nd Generation) — in use

- **Portal:** https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2. Transport
  Department (IRNP). Monthly; snapshotted once.
- **File:** `https://static.data.gov.hk/td/road-network-v2/RdNet_IRNP.gdb.zip` — 17 MB FGDB, all
  seventeen layers, read through `pyogrio` `/vsizip/` (`Q9`). The per-layer GMLs (539 MB) are not
  fetched. Data dictionary: `…/road-network-v2/dataspec/rdnet_dataspec.zip`.
- **Geometry is 2D**, EPSG:2326, Measured MultiLineString (GDAL drops M).
- **`ELEVATION`** is an integer level (0, 1, −1) — an ordinal like OSM's `layer`, not a height.
  Config maps it to a deck height as the fallback where no structure can be sampled.
  It must not key nodes: every endpoint where two levels meet is a ramp touching down, and keying
  on level splits Wan Chai from 6 components into 24.
- **Feature identity is the FGDB `OBJECTID`.** `TURN` (`EDGE(1-8)FID`) and `INTERSECTION`
  (`RD_ID_1..10`) point at OBJECTIDs; a reader that renumbers on a filtered read resolves every
  restriction onto the wrong roads.
- Endpoints coincide to ~1 mm: nodes by coordinate identity. Geometry is over-densified (54,330
  vertices on one 51.7 m centreline): Douglas–Peucker at 0.2 m is a correctness measure.
- `ROUTE_ID` is 1:1 with the centreline; `SPEED_LIMIT` and `BUS_ONLY_LANE` join by key.
- Speed limits cover under 10% of edges (70 or 80 km/h); the 50 km/h default is config.
- `TURN` geometry is a hint: take the shared node.
- The null sentinel has four spellings (`-99`, `–９９`, `－９９`, `-９９`): normalise NFKC and fold
  Unicode dashes before comparing.
- Dual carriageways are opposed one-way pairs with no pairing attribute; `surface.py` pairs
  geometrically (`Q117`). Six places sharing both endpoints are the only ground truth.
- **No lane count exists** in this or any source. A row of ≥ 2 turn arrows abreast is a lower
  bound (`Q94`).
- Street names are bilingual: `STREET_ENAME` / `STREET_CNAME`, plus `ALIAS_*`.
- Read but not emitted: `TURN`'s `EXC_VEH_TYPE` / `INC_VEH_TYPE` (`TX` = taxi), `PART_TIME_REST`,
  `EFF_ALL_DAYS`, `OTHER_REST_TYPE`. Adding them is a schema change on both sides.

**`NSR` — kerbside yellow lines** (`pipeline/kerbside.py`). Kerb-referenced, median 2.76 m off the
nearest centreline.
- `VEHICLE_TYPE` decides what is paint (`Q56`): `1` all motor vehicles and `5` others are drawn;
  `2`/`3`/`4` (taxis, PLBs, goods) are refused — a class restriction is not a plain yellow line.
- `TIME_ZONE` `1` = 24 hours → double; `2`–`5` = posted hours → single. `EFFECTIVE_DAY` and
  `REMARKS` carry nothing.
- It carries `ST_CODE_1..6` and no edge key, so it is linear-referenced onto the graph; its M
  values are not a join.

**`ONSTREETPARK` — parking bays** (`Q161`, `pipeline/parked.py`): one point per bay, attribute
table `GISP_ON_STREET_PARKING` joined on `X_COOR` / `Y_COOR`. The positive "parking is allowed"
source. Motorcycle bays are ~1 m apart, car bays ~5 m.

### Traffic Aids Drawings (2nd Generation) — in use

- **`hk-td-tis_16-traffic-aids-drawings-v2`**, Transport Department, EPSG:2326, monthly.
  `https://static.data.gov.hk/td/traffic-aids-drawings-v2/dTAD_IRNP.gdb.zip` (218 MB, 51 layers);
  specification and index plans `…/traffic-aids-drawings-v2/dataspec/tadrawings_dataspec.zip`.
  The 1st generation (`tis_8`) is withdrawn.
- The gdb holds **no coded domains** (`Q101`): every `LINETYPE` / `REFNAME` table in
  `hong_kong.yaml` is a whitelist read off code strings.
- The specification zip is **read by the build**: `pipeline/sign_text.py` crops `TS102`'s lettering
  from `CT174/51-1(1)C` into the sign atlas, through `pipeline/sign_sheets.py`. The sheets have no
  text layer, so a cell's code is counted from the filename's range and grid position. The TS
  sheets are vector exports; the RM index plans are scans.
- **`ELEVATION` here is a 3-char text code with no domain**, not Road Network's integer. `A01` is
  the elevated network (93% within 8 m of a level-1 edge), null is at grade, `A03` is neither:
  `carriageway_survey.off_grade_codes: [A01, A03]`.

| Layer | What it is, and traps |
|---|---|
| `DTAD_RD_MARK_LINE` | `RM1108`/`RM1109` edge of carriageway (width survey); `RM1011`/`RM1012`/`RM1013` stop and give-way lines; `RM1001` double lines (`Q118`). Nearest-edge join is wrong for transverse marks on 43% of the layer — a stop line lies nearest the *major* road — so `roadmarks.py` hosts by transversality (`Q69`). Features and parts differ 2.5× |
| `DTAD_RD_MARK_LINE_C` | `RM1048` bus stop boundary and `RM1049` stand boundary (`stopmarks.py`; 44 of 113 `RM1049` are filed twice, vertex for vertex). Via `road_marks.more_layers` (`Q132`): `RM1101`/`RM1102` lane lines, `RM1103` centre, `RM1104`/`RM1105` warning, `RM1002`/`RM1003` broken doubles, `ZIGZAGL`/`ZIGZAGR`. `RULEID` 2 / 3 on `RM1002` / `RM1003` makes left/right the digitised direction's. A lane count off line spacing over-counts on 51 of 75 edges (`Q127`) |
| `DTAD_RD_MARK_SYM_PT` | Legends filed as a point and an angle, never also as strokes (`stopmarks.py`): `1047`'s heading reads with the traffic, `1175` / `1176`'s a quarter turn off it. Turn arrows (`pipeline/arrows.py`, `Q59`): `REFNAME` `RM1017`–`RM1029`, all the 4000 mm variant. **`ANGLE` is mathematical**: heading = `(90 − ANGLE) mod 360`. Not arrows: `RM1116`–`RM1119` warning arrows, `RM1135`/`RM1136` 望右/望左. Read by two stages (`arrows.py`, `carriageway.py`) that cluster independently |
| `DTAD_CROSSING_LINE` | Crossing stripes, each its own rectangle (`pipeline/crossings.py`), short side p50 0.600 m. `LINETYPE` does not give colour (`SOLID` / `Solid` / null / `RM1076` carry the same stripe) |
| `DTAD_YL_BOX_POLY` | Yellow box junctions (`pipeline/boxjunctions.py`). `ANGLE1`/`ANGLE2` published on 4 of 20 in Wan Chai; the stage derives the rest and grades against those four |
| `DTAD_TS_ABV_PT`, `DTAD_TS_POLE_PT` | Traffic signs (`pipeline/signs.py`). `ABV_PT` is a label placement, not the sign: none sits on a pole. **`GG_NAME` is the only join** (92.6% resolve to one pole). `ANGLE` is symbol rotation, not a facing; facing is derived from host edge, kerb side and drive-on-left. No dimension is published: plate size, mount height and pole diameter are authored. `SIGNID` resolves into the `Index Plan/(TS …).pdf` sheets, checked by `tools/sign_face_survey.py` (`Q67`) |
| `DTAD_RAILING_LINE` | Railings, bollards, barriers (`pipeline/railings.py`, `Q61`). `LINETYPE` classes: railings `CRAIL1` `CRAIL2` `HCAIL2` `RAIL1` `RAILING1`; bollards `bollard0..3`; barriers `CBARRIER` `CRASHGATE`. Unclassed: `SOLID`, `AMT*`, `EAG 3`, `MSB 5`. The weakest claim in the config (`Q60`); every dimension is authored |
| `DTAD_TRAFFIC_LIGHT_PT` | Signal posts (`pipeline/signals.py`, `Q76`, `Q173`). Some are not heads (bollards, `PBUTT`, `WIGWAG`). `ANGLE` is not a facing; no `GG_NAME` |
| `DTAD_RST_ZONE_LINE` | Kerbside yellow lines, `RM1040` / `RM1041`. Read only by `tools/kerbside_source_audit.py`: `TIME_ZONE` is null on every feature. `RM1040` sits on `NSR TIME_ZONE = 1` for 99.95% of its length |
| `DTAD_RD_MARK_SYM_LINE` | Legends as the strokes of a stick font, in place and to size (`pipeline/stopmarks.py`, `Q242`): `REFNAME` `1047` BUS STOP 巴士站 (letters 1600, characters 2700), `1175` / `1176` taxi drop-off / pick-up (800 / 1350). The bare number, no `RM`. Also `1049` stand outlines and `1051` parking bays, unread |
| `DTAD_RD_MARK_ANNO` | Road text (`CENTRAL`, `九龍`) as rotated rectangles, some with `<FNT …>` markup. Not in use (`P3-21`) |
| `DTAD_TW_STRIP_LINE` | **Not tramway** — tactile warning strips (`REFNAME = TACW`) |

**Marking codes** are defined in `Index Plan/(RM 1001 - 1080).pdf` (`CT174/51-5(1)F`) and
`(RM 1101 - 1180).pdf` (`CT174/51-5(2)G`) inside the specification zip, in mm. The codes in use
and their dimensions are `road_marks.marks` in `hong_kong.yaml`.

- `LINES SPACING` is the clear gap, not a centre-to-centre pitch.
- Colour is read off the description column: `RM1040`–`RM1045` are yellow, `RM1046`–`RM1048`
  white, `RM1049` alternates the two.
- `RM1013` give-way is a double broken line, not triangles. `RM1072`/`RM1073` zig-zags are the
  evidence a crossing is a zebra. `RM1076` signal-crossing stripes are surveyed 0.6 m wide.
- Arrows publish a length and no shape (`Q93`); the glyph is measured off the pictograms, which
  are drawn to proportion, and the turn branch is authored (`Q91`).

### HyD Pavement Polygon — in use (`Q94`)

**`hyd_rcd_1632210918434_60749`**, Highways Department, **CSDI Portal only**. ArcGIS `MapServer`
layer `INV_PG`, native EPSG:2326. The only source that gives the carriageway as an area.

- **Fetch:** `paged_sources.pavement_polygon` pages `MapServer/0/query` over the whole territory
  into one ~163 MB file. `orderByFields=OBJECTID` because paging without a stable sort is
  undefined; `max_pages` catches a service ignoring `resultOffset`. The `file-api` GeoJSON is
  WGS84 and `gdb.read_layer` does not reproject; a bbox query would put region bounds in a
  whole-config block.
- Domains, from the layer's own `?f=json`:

```
FEAT_TYPE   1 Carriageway   2 Footway   3 Other   5 Cycle Track   6 Side/Back Lane   7 Run-in
            8 PTI-Carriageway   9 PTI-Footway   23 Carpark-Carriageway   24 Carpark-Footway
           31 Traffic Island - Refuge Island    32 Traffic Island - Other
LVL         3/2/1 above ground · 0 ground · -1/-2/-3 below — mirrors Road Network v2's ELEVATION
```

- Read by point-in-union, never by a ray to the nearest polygon boundary: HyD tiles the
  carriageway into many polygons and an internal seam is not a kerb.
- It measures the trafficable surface, not kerb-to-kerb: islands, run-ins and car parks are carved
  out of `FEAT_TYPE = 1`. HyD − iB1000 over shared stations: p10 −3.39 / p50 0.00 / p90 +0.47 m.
- Attribution: this dataset makes the CSDI half of hard rule 6 load-bearing.

How the width survey combines TD, iB1000 and HyD is `.claude/rules/carriageway.md`.

### TD Transport Planning & Design Manual, Volume 2 — read, not fetched (`Q95`)

`https://www.td.gov.hk/filemanager/en/content_5055/V2_03_2026.pdf`, Chapter 3, March 2026 edition.
On `td.gov.hk`, not an open-data dataset. **A design standard is not a survey**: it may bound an
instrument and source an authored number, never assign a per-edge width.

Table 3.4.2.1 — Minimum Carriageway Widths in Urban Areas, per carriageway (m):

| Road type | single, 2 lane | single, 4 lane | dual, 2 lane | dual, 3 lane | dual, 4 lane |
|---|---|---|---|---|---|
| Trunk Road / Expressway | — | — | 7.3 | 11 | 14.6 |
| Primary Distributor | — | — | 6.75 | 10 | 13.5 |
| District Distributor | 7.3 or 10.3 | 13.5 | 6.75 | 10 | — |
| Local Distributor | 7.3 or 10.3 | 13.5 | 6.75 | — | — |

- 3.4.2.3: a double-track tram reserve needs 5.5 m. 3.4.2.6: an extra 3 m parking strip. 3.4.4.1:
  a 13.5 m four-lane widens to 15.8 m on a tight curve.
- 3.4.2.7: a two-way single carriageway must not be divided into three lanes.
- 4.3.9.8: a through lane is 3.0–3.65 m — the lane bracket. `roads.lane_width_m` is never the
  divisor.
- Wired as `carriageway_survey.width_bounds`: a two-sided span above ~16.5 m is refused;
  `dual_max_m` 14.6, `dual_min_m` 6.75, `median_max_m` 5.5 (reported, never refused).
- The table is headed *Minimum*, and 3.4.2.2 lets trunk widths fall below it.

### Rejected for kerbside restrictions (`Q56`)

A sweep of all 60 TD datasets on DATA.GOV.HK, the CSDI catalogue and 3,810 packages by keyword
found `NSR` and `DTAD_RST_ZONE_LINE` to be the only two that assert a kerbside stopping
restriction. Do not repeat it.

Not usable: `hk-td-msd_1` metered spaces (district counts, no geometry), `msd_2` (a ~250-space
trial), `tis_4` / `tis_5` (real-time occupancy), `tis_36` pedestrian streets (`PEDESTRIAN_ZONE`
covers it), `hk-landsd-openmap-road-centreline` (annotation-grade).

---

## Fares, stops and traffic

CSDI point sets download as
`https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=<id>&format=geojson` — no key, WGS84,
positions quantised to whole metres on the HK1980 grid.

| Source key | CSDI id | Use |
|---|---|---|
| `taxi_stands` | `td_rcd_1697081907714_17556` (`hk-td-tis_37`) | Pickup hotspots; `District_EN` also sets a region's taxi licence mix (`Q183`) |
| `taxi_pudo` | `td_rcd_1697082382328_14459` (`hk-td-tis_38`) | `Status_EN` `Taxi PU/DF` hail and deliver, `Taxi DF` drop-off only → `fares.json` `pickup` / `dropoff` |
| `tram_stops` | `td_rcd_1638875413253_59498` | `poi` fare nodes. Publishes no name (`OBJECTID`, `STOP_ID`, `LAST_UPDATE_DATE`): `name: null` |
| `bus_stops` | `td_rcd_1638874475129_49745` | Parked buses at stops (`Q161`); `STOP_ID` is the routes file's `stopId` |
| `gmb_termini` | `td_rcd_1638874728005_80512` | Parked minibuses at termini |

- Taxi stands' `Status_EN` is free text — sixteen spellings, some with an operating-time note
  after an embedded newline — mapped to `urban`, `urban_and_nt`, `nt`, `cross_harbour`, `lantau`.
  Matching is first-hit-wins over substrings, so rule order is load-bearing (`Urban and NT` before
  `NT Taxi Stand` before `Urban`); `load_config` refuses a shadowing table. Operating times are
  discarded (`Q14`).
- `Location_EN` / `Location_TC` are on every stand and PU/DF point. Some contain newlines
  (collapsed by `clean_text`) and full-width brackets: `clean_text` returns NFC and folds to NFKC
  only for the null-sentinel comparison.
- Snapping (`Q15`): the sources are 2D, so candidates are restricted to level 0 — a point under
  the Canal Road Flyover otherwise snaps to the deck.
- Not in use: `td_rcd_1760062901418_33580` Fleet Taxi Stopping Places (17 territory-wide, names
  are prose).

### Routes and Fares of Public Transport (`Q182`)

TD via DATA.GOV.HK: `JSON_BUS.json` (78 MB) and `JSON_GMB.json` (21 MB) under
`static.data.gov.hk/td/routes-fares-geojson/`. One GeoJSON point per stop of each route direction
(`routeId`, `routeSeq` the bound, `stopSeq`, `stopId`, `routeNameE`, `companyCode`), WGS84, UTF-8
with a byte-order mark. `pipeline/busroutes.py` snaps each direction's stops to the graph.

The line between stops is not published (GTFS `shapes.txt` answers 403): the game routes it
(`RoadRouter.goal_tree`) and `tools/bus_legs.py` grades the result.

### Public Transport Headways (GTFS)

`static.data.gov.hk/td/pt-headway-en/`: `trips.txt`, `frequencies.txt`, `calendar.txt`. CRLF,
byte-order mark. Departures per route direction per hour of `bus_routes.service_day` are the routed
fleet's spawn weights. The direction is spelled only in `trip_id`
(`<route_id>-<bound>-<service_id>-<HHMM>`); a trip with no `frequencies.txt` row departs once at
its `HHMM`; a `frequencies` end is exclusive.

### Annual Traffic Census (`Q186`)

- https://atc.td.gov.hk/ serves the 2025 census and every station's data form as JSON:
  `POST https://atc.td.gov.hk/api/analysis` with `{"req_station": "1029", "req_month": "0",
  "req_direction": 0, "req_vco_date": "Wed", "req_vco_time": "8"}`. `api/excel/list` lists
  stations, `api/search?q=1029&f=json` places one. Guide: https://atc.td.gov.hk/pdf/Users_Guide.pdf.
  The 2023 report PDF does not carry the station forms.
- `tools/traffic_census.py` (stations in the `traffic_census` block, cache under `build/census/`)
  reads `Hourly_Var`'s `M-F` row — weekday share by clock hour — and `VCO`'s `Veh` row — vehicles
  by ten classes (`M/C`, `P/C`, `Taxi`, `Priv.LB`, `PLB`, `L/G`, `H/G`, `Coach`, `B/SD`, `B/DD`),
  07:00–23:00 — into `traffic.tres` `fleet_by_hour` and `kinds`.
- A station on no cordon or screenline (1020, 1024, 1028, 1029) has no VCO: its row is ten `-`,
  read as unsurveyed, never zero.
- The VCO is one survey day: `req_vco_date` changes nothing.
- Pool stations by count, never average percentages: a local road's sample is ~20 vehicles an hour.

### Traffic Data of Strategic / Major Roads (`Q198`)

- TD via DATA.GOV.HK (`hk-td-sm_4-traffic-data-strategic-major-roads`):
  `https://resource.data.one.gov.hk/td/traffic-detectors/rawSpeedVol-all.xml` — per detector lane,
  each 30 s period's `speed` (kph), `occupancy`, `volume`, `s.d.`, `valid`. Detector locations:
  `https://static.data.gov.hk/td/traffic-data-strategic-major-roads/info/traffic_speed_volume_occ_info.csv`.
- History comes from the DATA.GOV.HK archive:
  `GET https://api.data.gov.hk/v1/historical-archive/list-file-versions?url=<feed>&start=YYYYMMDD&end=YYYYMMDD`,
  then `get-file?url=<feed>&time=<version>`.
- `tools/traffic_census.py` reads the detectors and weekdays listed in `traffic_census`
  (cache `build/detectors/`): each hour's space-mean speed feeds `fleet_by_hour` as flow over
  speed.
- A listed version can 404; the tool falls back to the nearest minute in the same ten-minute slot.
- A lane-period with no car reads speed 0 and is skipped. No detector stands on a side street.

---

## The far shore (`Q249`)

- **iB1000 `Building`** over each region and `backdrop.sea_reach_m` (600 m) round it, the same
  `tiled_sources.topography` sheets the basemap reads (`Config.fetch_extents`). Kowloon is the
  far-only region `tsim_sha_tsui`, 114.152–114.198 E, 22.2915–22.308 N, whose fetch takes that map
  alone. `BASELEVEL` and `ROOFLEVEL` are read: 3,536 footprints in its box, 133 with no level,
  1,146 at least 30 m tall. Its build also reads the sea of every driven region whose frame its
  reach meets — Mong Kok's included, so those sheets are fetched too.
- ⚠️ `Shoreline` does not separate land from sea there: West Kowloon's waterfront and east Tsim
  Sha Tsui's are gaps of several hundred metres, so `basemap.sea_of` finds one piece. The shore
  is a closing of the footprints and the sea walls instead.

## Roadside planters (`Q247`)

- **HyD Roadside Planter Wall** — `hyd_rcd_1632211024666_47455`, Highways Department,
  `csdi:INV_RPW`, native EPSG:2326, found 2026-11-18. `paged_sources.planter_walls` reads
  `OBJECTID` and the geometry: 5,325 polylines territory-wide, 48 in Wan Chai and 6 in Causeway
  Bay. ⚠️ A line and `RPW_UID`, nothing else: no height, no level, nothing on the planting. 22 of
  Wan Chai's 48 features close into a ring; the rest are a wall along one side.
- Looked at and not built: **HyD Vegetation** (`VIS_INV_VEG`) — Causeway Bay's 78 polygons are 79%
  slope and 90% under canopy the trees already stand; iB1000 has no grass, shrub or planter class;
  the 3D Visualisation Map's `VEGETATION(TB)` is ~97% tree canopy.

## Trees (`Q171`)

Three point inventories, paged off the CSDI REST service like the pavement polygons
(`MapServer/0/query`, `outSR=2326`). Only what they survey is drawn: no roadside inventory was
found.

- **HyD Tree** — `hyd_rcd_1632210213867_60179`, Highways Department, `csdi:VIS_INV_TREE`, native
  EPSG:2326. `paged_sources.tree_hyd` reads `TREE_ID,DBH`. `DBH` is trunk diameter in mm, turned
  into a height by the authored `trees.height_per_dbh_m`. `SPECIES_NAME` is null on every tree in
  the built regions, so every HyD tree is the default kind.
- **LCSD Trees (venues other than major parks)** — `lcsd_rcd_1760154188966_59086`, Leisure and
  Cultural Services Department. `paged_sources.tree_lcsd` reads `OBJECTID,Scientific_Name`; the
  genus picks the kind (`trees.genera`). This dataset is why LCSD is in the credits.
- **LCSD Trees (Major Parks)** — `lcsd_rcd_1730101435734_98947`, the same department, found
  2026-11-18. `paged_sources.tree_lcsd_parks` reads `OBJECTID,Scientific_Name`; 30,526 points,
  stored in WGS84. Victoria Park is 2,230 of them across Wan Chai and Causeway Bay (74 genera).

## Signboards (`Q260`)

- **BD Legal / Validated Signboards** — `bd_rcd_1629267205232_53467`, Buildings Department, CSDI
  `file-api` GeoJSON, layer `BDLSMW`, native EPSG:2326 (`Easting` / `Northing` columns beside the
  geometry). 69.7 MB territory-wide; 2,038 boards in Wan Chai, 132 in Causeway Bay. Each row has
  the board's type, its length, height and thickness in metres, `Location_Description_EN`
  ("FACING HENNESSY ROAD") and a link to a photo PDF. ⚠️ **It records only boards that went through
  the minor works or validation scheme**, so it is a lower bound: an unregistered board is absent.
  The point is the board's location, not its wall. `signboards.py` snaps it to the nearest shipped
  wall (p50 0.27 m, p90 0.98 m in Wan Chai).
- **The photos** — one PDF a board on `storage.googleapis.com/legal-signboard-image-hosting-prod/`.
  The board is outlined in red vector strokes on most of them. `tools/signboard_colour.py` reads that
  outline with `pypdfium2`, takes the k-means colour inside it, and writes **one colour a board** to
  `etl/sources/signboard_colour/signboard_colour.json`. Nothing else from a photo is kept. Across
  the four driven regions: 3,455 of 3,883 measured (3,362 vector outline, 93 raster ring), 422 with
  no outline, 5 dead links. Some photos are the applicant's own, extracted from minor works records.
  `LICENSING.md` item 6.
- **No owner and no trade name** in either: the database names no shop. The lettering (`P3-103`
  step 2) is generic, never a real name.
- **FEHD Restaurant Licences** — `fehd_rcd_1630036390312_58893`, Food and Environmental Hygiene
  Department, CSDI `file-api` GeoJSON, layer `FEHD_RL`, 17,272 licensed premises territory-wide
  with `EASTING` / `NORTHING` (EPSG:2326). Read for position alone: a board within
  `licences.reach_m` of one is more likely lettered as a food trade (959 of Wan Chai's 2,031).
  ⚠️ The licensee's shop name (`NSEARCH03_*`) and address are in the data and are **never read**.
