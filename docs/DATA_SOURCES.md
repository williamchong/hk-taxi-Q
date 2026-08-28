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

🔴 **A second attribution is now required and it is not the government's.** Since `P3-24` the build
bundles a third-party typeface under CC BY 4.0, whose attribution must travel with **every
distributed copy** — not merely sit in the repository. Add to the same screen:

> Street names are set in **Free HK Kai** (自由香港楷書) © 2016 Free Hong Kong Fonts, used under the
> Creative Commons Attribution 4.0 International licence.

⚠️ **This obligation is recorded and NOT yet discharged: there is no credits screen.** `game/scenes/`
has no UI scene at all, so the text above exists only here and in
`game/assets/authored/fonts/LICENSE`. The font ships in the PCK today, which means **the build is
currently distributing a CC BY work without its credit visible to the person running it.** That is a
licence gap, not a to-do — it closes when the screen is built, and it should be built before anything
is published beyond a playtest link. `LICENSING.md`, `DECISIONS.md` `Q79`.

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

#### ⚠️ The road layers of this file, surveyed by `Q57` (2026-08-20) and not in use

**These sheets are already on disk.** The pipeline reads one layer of ~71 — `Building` — for the
podium join. The rest cost nothing to read, and two of them refute claims this project has been
making. Domain codes are the data dictionary's own words, quoted, not inferred:

| Layer / code | In Wan Chai (six sheets) | What it answers |
|---|---|---|
| **`CartoTransLine`, `TRANSPORTATIONLINETYPE = RM`** — *"RM - Road margin"* | **56,286 segments** | **The carriageway edge.** ⚠️ `Q19` and `PROGRESS.md` have said the carriageway width "no source publishes". It is published, and has been on disk since `P3-7a`. Probed by casting a perpendicular from each centreline station to the first road margin each side — 9,822 stations on 701 centrelines — the width reads p25 **7.02 m**, p50 **9.84 m**, p75 **15.36 m**, against a shipped `width_m` that takes exactly two values, 6.4 m on 720 edges and 9.6 m on 77. ⚠️ **That probe is not a shippable width** — the perpendicular escapes through junction mouths and crosses both halves of a dual carriageway, so it over-reads at the top of the distribution |
| `CartoTransLine`, `RMU` — *"Road margin under elevated structures"* | 415 features / 9,232 m | The same edge where a deck is overhead. Pairs with `elevation_level` |
| **`CartoTransLine`, `TW`** — *"TW - Tramway"* | **168 parts / 12,292 m** (132 parts / 9,912 m clipped to region) | **The tram rails**, and `P3-14` draws them. `hong_kong.yaml` said "no dataset marks tram tracks" until `Q57`. `RailwayPolygon`, `RAILWAYTYPE = TW`, carries the same extent as **62 polygons**. 🔴 **This row said "the tram tracks" and meant centrelines, and that was wrong** — `Q58` measured it: **56.5%** of stations cast across a tram-flagged edge cross exactly **four** parts, and the perpendicular gap between neighbouring parts is sharply unimodal at **1.05-1.20 m** with essentially nothing at track separation. A part is **one rail**; the 1,067 mm gauge is what the modal gap is. Read as centrelines it draws a bed a lane wide down each rail |
| Derived from `TW` by `Q58`, over 1,698 four-rail cross-sections | gauge p10 **1.066** / p50 **1.124** / p90 **1.221** m · track separation p10 **2.445** / p50 **2.597** / p90 **2.768** m | The published gauge is 1.067 m, so the low tail sits exactly on it and the median reads 5% over — digitising width, not a wider tramway. ⚠️ **The tramway is not on the drawn carriageway**: only **18.8%** of those cross-sections have both tracks on the ribbon (Hennessy **1.5%**, Yee Wo 0.0%, Causeway 0.0%, Johnston 54.4%), because 80 of the 86 `tram_streets` edges are one-way and the reserve runs *between* two ribbons. The outer rail sits a median **3.26 m** past the drawn kerb |
| `CartoTransLine`, `FY` / `FYU` / `TUR` | 89 / 16 / 14 features | *"Flyover / Elevated road / Bridge"*, flyover-under-flyover, and *"Tunnel for vehicles or railway"* — a second opinion on `ELEVATION`, which `Q13` and `Q21` both turn on |
| `CartoPedLine`, `PA` — *"Pavement margin"* | 2,945 features / **50,904 m** | The footway edge. With `RM` above, the pavement is bounded on both sides — bears on `carriageway_occupancy`'s open failure |
| `CartoPedLine`, `STP` / `FBR` / `SWY` / `CWY` | 3,577 / 384 / 18 / 85 | Steps, *"Footbridge (over road / water) / Elevated walkway"*, pedestrian subway, covered walkway |
| `StreetCentreLines`, `STREETTYPE` | 794 features, `SER` 492 / `MAR` 259 / `TRA` 30 / `TUN` 12 | LandsD's own centrelines, carrying `ST_CODE` — the **same street code `NSR` joins on**. Not a second road graph; a second key |
| `BUILDINGNAME` / `ADDRESS` / `Street_Code` | 306 / 422 / 112 per sheet | Bilingual building names and street addresses. Bears on fare destinations, which today are 29 taxi points |

⚠️ **Codes are three letters and several are traps.** `TW` is *Tramway* here and *tactile warning
strip* in Traffic Aids Drawings; `RM` is *Road margin* here and a *road-marking code prefix* there.
Read the dictionary for the file in hand.

#### The street-furniture layers of this file (`P3-26`, 2026-08-27)

**`Q57` surveyed this file's *road* layers and never opened its utility ones.** They are in the same
six sheets, already on disk, and one of them is a shipped layer since `P3-26`.

| Layer / code | In Wan Chai (six sheets) | In region | What it is |
|---|---|---|---|
| **`UtilityPoint`, `UTILITYPOINTTYPE = LPO`** | **2,096** | **1,263** | **The lamp posts.** ✅ **In use since `P3-26`** — `pipeline/lamps.py` draws them as `lamps.glb` |
| `UtilityPoint`, `FWH` / `SWH` | 365 / 39 | 215 / 26 | Fresh- and salt-water hydrants. **Not in use** — 0.7 m of street furniture buys none of the vertical rhythm `P3-26` is for |
| `UtilityPoint`, `EPO` | 2 | 2 | **Not in use**, and two features is not a layer |
| `RoadAssetPoint`, `RAC` / `BAC` | 11 / 3 | 5 / 2 | **Not in use** |
| `BuiltStructurePoint`, `GIC` `MON` `UNC` `MAS` `SHR` | 30 | 5 | **Not in use** |
| ⚠️ `Tree`, `TREETYPE` | **40** | **9** (`OVT` ×8, `TE` ×1) | 🔴 **NOT a street canopy, and the count is not why.** `SOURCEREFNO` reads `ARCHSD WCH/3`, `EMSD WCH/1`, `HKP WCH/1`, `LCSD WCH/6` — per-department survey references, i.e. trees surveyed **individually**, which is never how a street canopy is captured. `OVT` is the *Old and Valuable Tree* register: legally protected specimens. This is a **landmark** layer with nine members. `LandCoverVector2` is **0 features across all six sheets**, so there is no polygon fallback. **Not in use**, and named here so the hour is not spent again |

🔴 **`UTILITYPOINTTYPE` HAS A PUBLISHED DOMAIN, AND IT IS INSIDE THE GEODATABASE.** `LPO - Lamp post`
and `TE - Tree` / `OVT - Old valuable tree` are coded-value domains (`dTreeType` and its sibling)
stored in the `.gdbtable` bytes of every sheet. That is a **materially stronger** claim than the two
layers this project has previously had to guess at: `DTAD_RAILING_LINE.LINETYPE` has no domain
anywhere (`Q60`) and `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has none either (`Q76`), which is part of why
`Q77` was arguable at all. It is arguably stronger than `arrows.py`'s glyph table, which is
transcribed **by eye** off a drawing (`Q59`). ⚠️ So a change to which codes this pipeline draws is
**not** `railings.py`'s situation — the publisher has already answered, and the answer is checkable
without leaving the file.

⚠️ **The layer publishes a position and nothing else.** Its six columns are `LASTUPDATEDATE`,
`UTILITYPOINTID`, `UTILITYPOINTTYPE`, `STATUS`, `DISPLAYSTATUS`, `DATASOURCE`. There is **no
elevation level, no angle, no height, no lantern type and no arm direction**. ⚠️ **Geometry Z is
`0.0` on all 1,263** and that is the file's convention rather than a defect: `SpotHeight` — a layer
whose entire purpose is heights — also reads Z `0.0` and keeps its value in a `HEIGHTVALUE` column.
`UtilityPoint` has no such column, so **every dimension `lamps.py` draws is authored**, which is
`Q60`'s railing debt and `P3-16`'s plate debt at a third layer. `STATUS` is `E` on all 1,263.

⚠️ **`UtilityNumber` is a related table, not a column** — 377 rows per sheet, `UTILITYNUMBER` joined
to `UTILITYPOINTID` through the `LampPostHasNumber` relationship. These are Hong Kong's lamp-post
numbers. **Not in use**: drawing them needs `P3-20`'s atlas machinery for lettering no driver can
read at speed, which is `Q65`'s effort-per-plate refusal.

⚠️ **`LPO` is a trap in the same family as `TW` and `RM` above.** It is *Lamp post* here; the
`DTAD_GIPOLE_PT` layer next door in Traffic Aids Drawings is a different pole population entirely and
is **not** read by this stage.

**Measured over the region (`P3-26`, and reproduced by the stage's own counters):** nearest-neighbour
spacing p10 **7.09** / p50 **16.74** / p90 **27.63** m with **zero** coincident pairs under 0.05 m —
alternating-side street lighting, and an independent agreement with the domain string. ⚠️ **64.1%
(810 of 1,263) are surveyed inside the drawn 1.6x carriageway**, a median 1.46 m past the drawn kerb,
so drawn where published nearly two thirds of Wan Chai's lamp columns stand in the road.
They are **registered onto the drawn kerb** — `Q60`'s move at a fourth layer. See `DECISIONS.md`
`Q82`.

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

⚠️ **That exclusion was itself incomplete, and is now measured.** The set carries **duplicated flat
placeholder panels that are not grey** — one 4,584-byte PNG on 21 buildings, one 1,761-byte panel on
29, and two further panels that are a *single* colour — and the survey's filler guard originally
rejected only an exact `R == G == B` tie, so it passed all of them. The grey half was always caught:
2,429 of 3,203 `B`-model atlases hold a grey modal colour over ≥ 20% of their texels, 1,982 at
`#3c3c3c`.

✅ **Since 2026-08-21 the guard also reads repetition**, which is what `Q37` said the signature was:
`filler_colours` takes any colour holding ≥ 20% of an atlas and rejects those texels per texel, and
`facade_survey.py --all --filler-report` publishes what it finds — **100 buildings on 132 atlas
slots, 90 rows corrected**. So the coverage figure above is still an **over**-estimate of how much
real photography there is, but the amount is no longer unmeasured: it is that report, and it is
reproducible. ⚠️ It remains a **floor** — detection needs one exact colour at ≥ 20% of one atlas.
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
| **`NSR` is the kerbside yellow lines, and `VEHICLE_TYPE` is the field that decides how many** | **579 features / 44,220 m** in region, **kerb-referenced** (median **2.76 m** off the nearest centreline, p99 8.24 m, 0% on it). ⚠️ **`VEHICLE_TYPE` decides which features are paint, and `Q56` corrected who is on that list.** `1` "all motor vehicles" (33,074 m) **and** `5` "Others" (8,323 m) are painted — the specification still names no class for `5`, but the Traffic Aids Drawings draw a line on **93.9%** of its metres in region, 96% of them single yellow. `2`/`3`/`4` (taxis, PLBs, goods vehicles, 2,822 m) are **refused, and not because they are signs** — the drawings paint those too (code 2 at 100%, code 4 at 90.2%, code 3 at 48.4%). They are refused because a class-specific restriction is not a plain yellow line and the codec cannot say which class. `TIME_ZONE` separates double from single outright: `1` is 24 hours (27,118 m, double), `2`–`5` are posted hours (5,956 m, single). `EFFECTIVE_DAY` is uniformly `1` in region and carries nothing. `REMARKS` is `None` for 31,919 m of the 33,074 and **never mentions taxis** within `VEHICLE_TYPE = 1`. `ONSTREETPARK` carries **607** bays as the complement | Ingested by `pipeline/kerbside.py` since `P3-13`, and it is the **one overlay that is not a key join**: `NSR` carries `ST_CODE_1..6` — street codes — where `SPEED_LIMIT` and `BUS_ONLY_LANE` carry `ROUTE_ID`, so it is linear-referenced onto the finished graph. **33,385 m over 722 edge sides** survive (26,065 m over 650 before `Q56` admitted code 5); overlapping features are deduped into 1 m cells rather than counted twice. ⚠️ The layer is a *Measured* MultiLineString and its M values are **not** a join — there is no route key to resolve them against |
| **Lane counts do not exist *in this dataset*** | no lane attribute in any field of any layer | `roadgraph.json`'s `lanes` is authored policy keyed on speed limit, not published data. ⚠️ **`Q57` narrowed this claim on 2026-08-20 without refuting it.** No source in the estate publishes a lane *count*; Traffic Aids Drawings publishes the lane *lines* — `RM1101`/`RM1102` LANE LINES (212 features in region), `RM1103` CENTRE LINE, `RM1109` EDGE OF CARRIAGEWAY (317) — so a count is derivable per cross-section from geometry. It is authored today because nobody has counted them, not because the city withholds the number. 🔴 **Narrowed again on 2026-08-28 by `Q94`, and this time from a layer already in the bundle**: a *row of turn arrows across a carriageway is a lane count*, stated by the publisher and read by a shipped stage. `DTAD_RD_MARK_SYM_PT` puts three symbols side by side at one station on STEWART ROAD `e505` — left | left-or-right | right at offsets +2.96 / −0.32 / −3.59 — which is a three-lane approach written down. Grouped by along-edge station and split at 1.6 m, **31 of the 306 arrow-carrying edges imply more lanes than the graph gives them**, nine of them four against two. It is a *sparser* source than the lane lines — only 306 edges carry arrows — but it needs no new geometry and no new fetch, and it is what `Q94` measured the cost of ignoring |
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

### ✅ USE (audit only) — Traffic Aids Drawings (2nd Generation)

**`hk-td-tis_16-traffic-aids-drawings-v2`** · Transport Department · EPSG:2326 · **monthly** ·
FGDB `dTAD_IRNP.gdb.zip`, **218 MB**, 51 layers · added by `Q56`, 2026-08-20

⚠️ **The 1st generation (`hk-td-tis_8-traffic-aids-drawings`) is being withdrawn.** Its only
remaining resource is a CSV pointing at this one. It is the URL a search engine still returns, so it
is named here to be recognised and skipped.

**This is TD's drawing set as spatial features** — MicroStation levels (`LV21`–`LV38`), `LINETYPE`,
`SYMBOL_STEP`, hatch angles, `GAZETTE_DATE`. Where Road Network v2 is *semantic* (what is
restricted, for whom, when), this is *cartographic* (what is painted, in what linetype). That is
what makes it a genuine second opinion and not a copy.

✅ **Built since `P3-15`, and it was "fetched, never built" for three weeks before that.**
`traffic_aids_drawings_gdb` is now read by `pipeline/arrows.py` as well as by
`tools/kerbside_source_audit.py` and `tools/carriageway_margin.py`, so a build **does** need it and
`--only` can no longer skip it for a region declaring an `arrows:` block.
🔴 **Since `P3-20` and `Q67` (2026-08-23), `traffic_aids_data_dictionary` is READ BY THE BUILD, not
only by a human.** It was a reference document — a zip you opened to transcribe a glyph table from.
Two things now open it programmatically:

- `pipeline/sign_text.py` crops the lettering out of `TS102`'s cell on `CT174/51-1(1)C` and bakes it
  into the sign atlas, so **the shipped city contains pixels cut from this PDF**. It is government
  data like any other, gitignored and never committed (hard rule 7), and it means a build now needs
  this 8.5 MB archive as well as the 218 MB fgdb.
- `tools/sign_face_survey.py` measures every drawn face against its published cell.

⚠️ **Both go through `pipeline/sign_sheets.py`, and the risk it carries is worth stating here**: the
sheets have **no text layer**, so nothing on one says which cell is which code. The row is *counted*
from the filename's range and a grid position, never read. That is asserted rather than assumed —
`blocks x rows` must bracket the filename's span — and every sheet the region uses recovers as
5 x 21. Three 6-block sheets carrying no code we ship are refused loudly rather than mis-indexed.

⚠️ **Its sibling role was already load-bearing.** TD drawing
**CT174/51-5(1)F**, inside `Index Plan/(RM 1001 - 1080).pdf`, is the only definition of what each `RM`
code means, and `hong_kong.yaml`'s glyph table is transcribed from it. It is a **scanned drawing with
no text layer** — `pdftotext` returns nothing — so it has to be read by eye, and `Q59` records what
reading the histogram instead would have painted.
It is the **largest single fixed-URL source in the city file**, 13× the road network, because it
carries the whole territory's markings, signs, railings and poles to reach one layer. A build that
never runs the audit can skip it with `--only`.

| Layer | In Wan Chai | What it is |
|---|---|---|
| **`DTAD_RST_ZONE_LINE`** | **1,763 features / 39,292 m**, `RM1040` 24,932 m + `RM1041` 14,164 m | **The kerbside yellow lines.** The only layer in use. `LINETYPE` carries the marking code; `COLOR = 6` is yellow on 1,559 of them. ⚠️ **`TIME_ZONE` is null on every feature in region** — the posted hours live in `NSR` and nowhere here |
| **`DTAD_YL_BOX_POLY`** | **20 polygons**, `YELLOWBOX_TYPE = "Yellow Box"` | Yellow box junctions, which `Q53` listed as an unsourced marking. ✅ **In use since `P3-18` (2026-08-22)** — `pipeline/boxjunctions.py` draws all 20 as `boxjunctions.glb`. `MultiPolygon`, **2D**, all single-ring with no holes in region, 5–106 vertices (four strongly concave), 20–469 m². ⚠️ **`ANGLE1`/`ANGLE2` — the two hatch directions, always 90° apart — are published on only 4 of the 20**; the stage derives the rest and grades the derivation against those pairs on every run. `ELEVATION` is null/empty on all 20 — at grade under the convention below. The 540 m of `RM1038` lines in `DTAD_RD_MARK_LINE` are a partial companion (6 features against 20 polygons) and stay unread |
| **`DTAD_RD_MARK_LINE`** | 1,679 features / **4,162 parts** / 61,903 m | Every other marking: `RM1109` 25,204 m and `RM1001` 19,308 m dominate; yellow ones are `RM1043` hatched no-parking (560 m) and `RM1038` box junction (540 m). ✅ **`RM1108`/`RM1109` EDGE OF CARRIAGEWAY (317 features) in use since 2026-08-20** by `tools/carriageway_margin.py` — the preferred publisher of the carriageway edge, ahead of iB1000's topographic margin. ✅ **The transverse markings in use since `P3-23` (2026-08-24)** — `pipeline/roadmarks.py` draws `RM1011` STOP LINE ×**120** (775.6 m), `RM1012` STOP LINES ×**8** (156.8 m) and `RM1013` GIVE WAY LINES ×**83** (741.0 m) as `roadmarks.glb`, **191 of 211 drawn**. Geometry is plain `MultiLineString`, **2D**, so it needs none of the Z decoding iB1000's lines do, and the bars are straight to four decimal places — chord over length p50 **1.0000**, and **192 of 211** parts are two-vertex. `ELEVATION` is null on **209 of 211** (2 `RM1012` on `A01`), read as at grade like `arrows:` and `boxjunctions:`. 🔴 **The nearest-edge join every other consumer of this geodatabase uses is WRONG here, on 43% of the layer**: a stop line sits at a junction *mouth*, drawn across the minor road while lying p50 **1.10 m** from the major road's centreline, so proximity picks the road it is parallel to. `roadmarks.py` picks the host by transversality instead and publishes `host_disagreement` (**90 of 209**) as the counter that can see that regress. See `DECISIONS.md` `Q69`. ⚠️ **Features and parts differ by 2.5x on this layer** — 1,679 against 4,162 — so a count keyed on one is not the other |
| `DTAD_CROSSING_LINE` | 121 features / 6,698 m | Crossings. **Not in use** |
| `DTAD_TY_BAR_LINE` | 4 features / 283 m | Transverse yellow bars. **Not in use** |
| **`DTAD_RD_MARK_SYM_PT`** | **1,365 points**, `REFNAME` = `RM` code, `ANGLE` = bearing, `ELEVATION` = structure or null, `SYMBOL_SIZE` | **The turn arrows `Q53` called unsourceable**, added by `Q57`. ✅ **In use since `P3-15`** — `pipeline/arrows.py` draws 747 of them (`Q59`). **781 turn arrows in region**, 761 at grade: `RM1017` ahead ×353, `RM1019` left ×179, `RM1027` ahead+left ×102, `RM1021` right ×92, `RM1025` ahead+right ×46, `RM1023` left+right ×8, `RM1029` ahead+left+right ×1 — all of them the **4000 mm** variant of a pair the index plan publishes at 4 m and 6 m. ⚠️ **`ANGLE` is a mathematical angle, not a compass bearing**: game heading is `(90 − ANGLE) mod 360`, which lands p50 **0.9°** from the host edge against 52.0° for the raw value (`Q59`). ⚠️ **Four families of code look like turn arrows and are not.** Two of them are here in force: `RM1116`–`RM1119` **WARNING ARROW** — the deviation arrow before a lane closure — at **61 in region**, the commonest arrow-shaped code after `RM1017`; and `RM1135`/`RM1136`, the 望右/望左 pedestrian crossing markings, at **127** and **123**. The other two are checked and absent here — `RM1167`–`RM1169` cycle-track arrows and `RM1144` LET IN LANE lettering, both **0** — and are named because a second region is what this table exists for. ⚠️ **`SYMBOL_SIZE` is populated for only 2 of the 747 drawn arrows**, so it cannot carry a length |
| **`DTAD_RD_MARK_ANNO`** | **274 annotations** | **The road text `Q53` called unsourceable.** `TextString` carries `CENTRAL`, `九龍`, `KOW`, `LOON`; `FontName` (`ENGINEERING` 181, `chinese` 91, `blhei1506` 2), `FontSize`, `Angle`, `CharacterWidth`. 🔴 **Geometry is `MultiPolygon`, not a point** — every feature is a closed 5-point rotated rectangle, the text's own envelope, so position, angle and extent are all read (`Q54`). ⚠️ Some `TextString`s carry embedded `<FNT …>` markup; unwrapped there are **67 distinct strings**, and they are painted-word *fragments* (`CEN`+`TRAL`) plus two-line blocks. **Not in use** — `P3-21` |
| `DTAD_RD_MARK_LINE_C` | 1,413 features | The other marking half: `RM1104` warning line 409, `RM1101` lane lines 212, `RM1054` angled parking bays 169, `RM1007` bus-lane continuation 136. **Not in use** |
| `DTAD_RD_MARK_SYM_LINE` | 173 features | `RM1047` bus-stop box ×82, `RM1051` motorcycle bay ×21, `RM1140` KEEP CLEAR ×19, `RM1176` taxi pick-up/drop-off ×5. **Not in use** |
| `DTAD_TRAFFIC_LIGHT_PT` | 913 points, with `ANGLE` | The signal estate — **and not 913 heads**. 46 distinct `REFNAME`s: `P<n>` ×654, `S<n>` ×189, `M<n>` ×19, plus **51 features that are not heads at all** (`KLBOLL`/`KRBOLL` keep-left/right bollards ×27, `PBUTT` ×8, `PBOLL` ×6, `WIGWAG` ×4, `PTR01`/`PTR02`/`STR02` ×5, `TRAML`). 🔴 **`REFNAME` HAS NO PUBLISHED DOMAIN** — the fgdb spec gives it 8 characters of untyped text, no Index Plan sheet defines it (both Miscellaneous Details sheets were rendered and read: they are the `RS/S/` sign pictograms), and `signCatalogue.json` is `TS`-only. So the whitelist is read off code strings, `railings.py`'s situation rather than `arrows.py`'s, and changing it is a change to **this file** (`Q76`). ⚠️ **`ANGLE` is not a facing** — re-measured on this layer: p50 44.3° off the host axis, 21.3% along / 19.3% across against 22.2% uniform. ⚠️ **No `GG_NAME`**, so an assembly is derived from coincidence — 470 of 913 points are within 0.05 m of another. ⚠️ `ELEVATION` is null on **906 of 913**, so null is the normal value here. `_LINE` 53 and `_FILLED` 84 are the same objects drawn, and `_LINE` publishes `SIGNID` **null on all 53**, so it cannot be joined back. **Read by `pipeline/signals.py` (`P3-17`), but NOT SHIPPED** — the layer was built and dropped from the bundle (`Q77`) |
| **`DTAD_TS_ABV_PT`** / **`DTAD_TS_POLE_PT`** | **3,276 signs / 2,227 poles**, both with `ANGLE` | **The traffic signs.** ✅ **In use since `P3-16` (2026-08-23)** — `pipeline/signs.py` draws **681 plates on 504 posts** as `signs.glb`, of which **84** carry lettering baked out of this same archive's own cells — `TS102` GIVE WAY / 讓 ×74 and `TS101` STOP / 停 ×10 (`P3-20`). `SIGNID` (`TS115` ×277, `TS182` ×155) resolves into the twenty `Index Plan/(TS …).pdf` sheets in the same `dataspec` zip; those sheets have **no text layer** (`pdftotext` returns nothing), so the shipped whitelist is transcribed by eye — `Q59`'s rule. 🔴 **And by eye is no longer the only check on it**: `tools/sign_face_survey.py` (`Q67`) rasterises each config face and diffs it against the published cell as area and extent per colour, which caught `TS414` drawn in negative, `TS735`'s border, `TS115`'s bar and `TS116`'s ring. It still cannot see a face on the wrong *code* — that is what its contact sheet is for. 🔴 **They are NOT scanned, which this row used to say**: `pdfinfo` reads `CT174_51_11.dgn` / PScript5.dll / Distiller and `pdffonts` returns no embedded font — a MicroStation DGN export whose ruling lines, digits and most pictograms are vector *paths*, with a handful of small indexed images. `P3-20` depends on the difference. 🔴 **The whitelist was shifted one row at `TS182`/`TS183` and shipped a mislabelled plate — `Q64`**, which is also why `~/hk-traffic-sign-map`'s `signCatalogue.json` may be read for its *crops* and not for its `desc`. 🔴 **`DTAD_TS_ABV_PT` IS NOT WHERE THE SIGN IS.** The fgdb spec calls it *"Traffic sign **abbreviation** point"* and calls the pole layer *"Traffic sign pole point"*. Measured: **zero** of the region's 3,276 abbreviation points sit on a pole, nearest pole p50 **2.63 m** (p90 8.25, max 115.5), and the offset direction is uncorrelated with `ANGLE`. It is a draughtsman's label placement — it says *which* sign, never *where*. ⚠️ **`GG_NAME` — *"Graphical group Name"* — is the join, and the only one there is**: it resolves **3,032 of 3,276 (92.6%)** to exactly one pole, 24 to more than one, 220 to none, and groups 1–7 signs per pole. `~/hk-traffic-sign-map` uses the same key for its signpost stacks. 🔴 **`ANGLE` IS NOT A FACING, and the publisher says so**: the spec's row reads *"Angle (For carto-rep feature, same as **Ustn** angle)"* — the MicroStation symbol-cell rotation. Measured in the frame `arrows.py` validated, it is flat against the road: p50 **44.2°** from the road axis, 19.2% within 20° of along and 18.1% of across, against 22.2% for uniform; `TS115` NO ENTRY reads 19.0/19.5. The pole layer's `ANGLE` is the same (26.4/17.6). `~/hk-traffic-sign-map` established this first — it fed `ANGLE` to `icon-rotate`, found **59% of same-code signs within 30 m share one**, and reverted (`fde0258` → `42c343a`). ⚠️ **The trap**: comparing `ANGLE` against a road bearing taken as a *grid* angle rather than a game heading appears to show 76.3% lying square across the road — an artefact of Wan Chai's strongly oriented grid, and it is enough to design a stage around. So the facing is **derived** from the host edge plus the kerb side plus drive-on-left. 🔴 **And so is the position across the road**: **77.3%** of the region's poles are surveyed *inside* the 1.6x drawn ribbon (p50 1.52 m past the drawn kerb, max 4.92), so drawn where published three quarters of the city's signs stand in the carriageway. They are registered onto the drawn kerb, `Q60`'s railing move at a second layer. 🔴 **Outward only, since `Q78`** — that reason covers a post the drawn kerb has moved past and no other, and the unconditional assignment was also dragging the **95 of 654** posts already standing clear back *toward* the carriageway (p50 0.69 m, max 4.51), invisibly, because `shift_m` is an absolute value. Those keep the point TD surveyed and are counted as `posts_kept_as_surveyed`. ⚠️ **No sign dimension is published anywhere**: every TS sheet is stamped **"NOT TO SCALE"** and refers dimensions to working drawings the `dataspec` bundle does not contain, so plate size, mount height and pole diameter are **authored** — the same debt `Q60` records for railing height. ⚠️ `ELEVATION` is null on 3,140 of 3,276 (`A01` ×123, `A03` ×13), read as at-grade like `arrows:` and `boxjunctions:`. ⚠️ **`DTAD_TS_PLATE_LINE` is not a plate outline** — 83,880 parts of median length **0.06 m**, cartographic ticks; it cannot serve as a second source for the facing. See `DECISIONS.md` `P3-16` |
| **`DTAD_RAILING_LINE`** | **1,753 features / 1,763 parts / 20,273 m** | **Hong Kong's signature street railings — and, since `Q61`, its bollards and vehicle barriers.** ✅ **In use since `P3-19` (2026-08-22)** — `pipeline/railings.py` draws the layer as **three classes** into one `railings.glb`: `railings` **9,017 m** (`CRAIL1` `CRAIL2` `HCAIL2` `RAIL1` `RAILING1`), `bollards` **463 m** (`bollard0..3`), `barriers` **935 m** (`CBARRIER` `CRASHGATE`). ⚠️ **Split by class of object and never within one** — all five fence codes draw one fence, because nothing published says they differ. Geometry is plain `MultiLineString`, **2D**, so heights come from a join; `ELEVATION` is null on 1,737 and `A01` on 16. 🔴 **This row said four `LINETYPE` values and there are nineteen** — `CRAIL1` 10,499 m, `CRAIL2` 2,921 m, `HCAIL2` 2,073 m, `CBARRIER` 1,369 m, `SOLID` 511 m, `AMT1` 502 m, `RAIL1` 472 m, `AMT` 457 m, `CRASHGATE` 301 m, `bollard0` 285 m, `RAILING1` 283 m, `bollard2` 235 m, `bollard3` 153 m, `AMT2_1.5` 118 m, `EAG 3` 46 m, `MSB 5` 23 m, `AMT1.5_1.0` 17 m, `AMT-1.5` 4 m, `bollard1` 3 m. ⚠️ **And the counts it gave were features where the metres here are parts** — `CRAIL1` is 532 features and 535 parts. 🔴 **`LINETYPE` HAS NO PUBLISHED DOMAIN, and this is the only layer the pipeline reads of which that is true.** The fgdb specification gives the column the description *"Line Type"* and nothing else, and the index-plan bundle carries no railing sheet — both "Miscellaneous Details" drawings, `CT174/51-6(1)E` and `6(2)F`, are sign pictograms and lettering, checked by eye. So `Q59`'s glyph-table rule **cannot be satisfied** here and `hong_kong.yaml`'s `classes` table is a whitelist read off the code strings, which is the weakest claim in that file. No railing *dimension* is published either — height and post pitch are authored. 🔴 **And the rest of the layer's 42 columns are cartography, not description.** `SYMBOL_SIZE_*`/`SYMBOL_STEP_*` are the spec's own *"Symbol size of **marker symbol** in first layer"* — plot sizes in **inches**, not metres on the street: all 21 `RAILING1` features read 0.8503937 (**21.6 mm** on paper) at step 5.669300 (**144 mm**), and `RAIL1` carries two numbers, a dash pattern. They are **null on 0-of-196 bollard features** in all five slots, so the earlier claim that they carry bollard spacing and diameter was wrong on both the reading and the population. `COLOR` is populated and separates the classes (`CRAIL1` 7 on 509/532, `bollard0` 0 on 143/161) but the spec gives it only *"Color of Feature", Number* and the document has **no coded-value table for any column** — same wall as `LINETYPE`. `LINE_PATTERN_*`, `LINE_WIDTH_*` and `LINE_OFFSET_*` are entirely null in the region. See `DECISIONS.md` `Q60` |
| `DTAD_DROP_KERB_LINE` | 738 features | Dropped kerbs, `REFNAME` `MDK_L`/`MDK_R`/`MDK` — where a vehicle may legally mount. **Not in use** |
| ⚠️ `DTAD_TW_STRIP_LINE` | 778 features, `REFNAME = TACW` | **Not tramway.** Tactile warning strips at dropped kerbs. Named here because `TW` reads as tramway and a `Q57` probe matched it to *every* street in the region before the join gave it away. The tramway is in iB1000, below |

**The marking codes are defined by the publisher, not inferred.** `dataspec/tadrawings_dataspec.zip`
contains `Index Plan/(RM 1001 - 1080).pdf`, drawing `CT174/51-5(1)F` from TD's Road Safety &
Standards Division, which gives every `RM` code its marking, description and dimensions:

| Code | Description | Dimensions | Kind |
|---|---|---|---|
| `RM1040` (TC 515) | NO STOPPING AT ANY TIME — YELLOW | line width 100, spacing 100, **left line continuous, right line continuous** | **double** |
| `RM1041` (TC 519) | NO STOPPING PART TIME — YELLOW | line width 100, **module continuous** | **single** |
| `RM1038` (TC 514) | BOX JUNCTION — YELLOW | boundary 300, hatched 100, spacing 2000 (2500) | — |
| `RM1043` (PA 12) | NO PARKING HATCHED MARKINGS — YELLOW | line width 100 | — |
| `RM1011` (TC 506) | **STOP LINE — WHITE** | line width 200, **module continuous** | **single** |
| `RM1012` (TC 507) | **STOP LINES — WHITE** | line width 200, lines spacing 300, **upper continuous, lower continuous** | **double** |
| `RM1013` (TC 508) | **GIVE WAY LINES — WHITE** | line width 200, lines spacing 200, **upper 600 mark / 300 gap, lower 600 mark / 300 gap** | **double, broken** |
| `RM1001` (TC 501) | DOUBLE LINES — WHITE | line width 150, lines spacing 100, both continuous | **double** |
| `RM1017`-`RM1030` (TC 509) | **TURN ARROWS — WHITE** | **`LENGTH = 4000` or `6000`, and nothing else** | — |

🔴 **The arrows are the row where the sheet publishes a length and no shape, and `Q93` is what that
cost.** `RM1017`-`RM1030` carry `LENGTH` alone; head, stem and branch are not dimensioned anywhere in
the `dataspec` bundle, and the sheet is stamped **NOT TO SCALE**. So the proportions can come from
nowhere but the pictogram in the sheet's own `Marking` column, which is what `hong_kong.yaml`'s
comment claimed and was not: measured at 700 dpi off `RM1017` and `RM1027`, two cells that agree,
**every authored figure was wrong** — the ahead head 0.325 → **0.390** of the glyph's length long and
0.235 → **0.122** across, nearly twice the drawing, and a uniform 0.085 stem where the drawing tapers
**0.076 → 0.032**. The branch reach is **0.150** and its barb span **0.233**.

✅ **The sheet is drawn to proportion, and that is measured rather than assumed.** It is stamped
**NOT TO SCALE**, which would ordinarily make any proportion read off it worthless. `RM1016` AUTOTOLL
publishes its own `SIZE = 5600(H) x 2000` — a ratio of **2.800** — and its pictogram measures
**2.802**. So the stamp means there is no scale bar on the sheet, not that the symbols are stylised,
and a proportion taken off a pictogram here is evidence. That is what licenses the head and stem
figures above, and it is worth knowing before the next glyph is transcribed.

🔴 **The turn branch is nevertheless AUTHORED, and that reversal is the interesting half.** Measured,
`RM1027`'s branch head is **wider than it is deep** — reach 0.150, barb span 0.233 — because what
makes it read as a direction is a pair of thin barbs sweeping back from the tip. `arrows.py` draws a
straight arm and a plain triangle, and at those proportions that is a mushroom on the shaft; drawn
faithfully as a six-point dart it becomes a detached diamond instead. And the barbs are **0.09 m on a
4 m arrow**, below a lane stripe, so `Q91`'s sub-pixel problem removes them at any driving distance.
So the branch ships as the one shape this model can state clearly — an arrowhead longer than it is
wide, sized against the frame rather than the sheet. `Q60`'s railing height and `P3-16`'s plate
dimensions at a third layer, with the difference that here something *is* published and is declined
rather than missing. The hook and the barbs are not modelled.

⚠️ **`Q67`'s rasterise-and-diff cannot grade any of it.** That tool compares a config face against the
cell TD published the code in, and works because the TS sheets are vector DGN exports. This page is a
**scan** — `pdffonts` returns nothing and it is eight indexed 2400-ppi images — so `Q59`'s by-eye rule
is the whole of the check on these numbers.

⚠️ **`LINES SPACING` IS THE CLEAR GAP BETWEEN THE TWO LINES, NOT A CENTRE-TO-CENTRE PITCH**, and the
sheet proves it rather than this note: `RM1001` publishes line width **150** with spacing **100**,
and two 150 mm lines whose centres are 100 mm apart is one 250 mm line. Only the gap reading draws a
shape. Read as a pitch, every double marking in the estate ships at the wrong weight and renders
perfectly. `RM1001` is listed above solely because it is what settles this, and is otherwise unread.

⚠️ **`RM1013` is a double *broken* line and not triangles.** The give-way triangle is a different
marking on a different row; TC 508 is two dashed lines. Recorded because the scoping note for
`P3-23` guessed otherwise (`Q69`).

⚠️ **That sheet is stamped "FOR INTERNAL ONLY"** and TD ships it inside the published open-data
`dataspec` bundle. Recorded so a reader who finds it is not surprised; `LICENSING.md`'s terms are the
government's own and are unchanged by it.

⚠️ **`ELEVATION` is a relative-level *text code*, its domain is not published, and the obvious
reading of it is wrong.** The FGDB data specification defines the column on every layer that carries
it as only *"Relative level (e.g. A01, A02)"*, 3-char text — it is **not** Road Network v2's integer
`ELEVATION`, despite the shared name. Measured 2026-08-20 over the 317 `RM1108`/`RM1109` features in
region, taking each feature's midpoint and asking how far it lies from the nearest level-0 and
level-1 graph edge:

| `ELEVATION` | features | median to level 0 | median to level 1 | within 8 m of a level-1 edge |
|---|---|---|---|---|
| `A01` | 180 | 5.6 m | **2.6 m** | **93%** |
| *null* | 126 | **2.7 m** | 11.4 m | 38% |
| `A03` | 11 | 27.4 m | 218.1 m | 0% |

**`A01` is the elevated network, not the at-grade one, despite being the commonest value**, and the
at-grade case is the *unmarked* one — a null. A filter written as "keep the codes that mean at
grade" therefore cannot spell the answer, and one written on "commonest must mean normal" keeps
exactly the wrong 57% of the layer and still reports a plausible number. `carriageway_survey`
states it as an **exclusion**, `off_grade_codes: [A01, A03]`. `A03` is excluded as neither: 27 m
from any level-0 edge, so it describes nothing an instrument on this graph measures.

**What it agrees with `NSR` about, measured.** 1 m samples, 3 m radius, before `Q56` changed
anything: `RM1040` sits on `NSR TIME_ZONE = 1` for **99.95%** of its length, which independently
confirms the "24 hours is a double yellow" mapping `P3-13` had asserted from a code table. **Only
24 m of the 39 km is unexplained by `NSR` at all.** The full table is in `Q56`.

**Resources**, verified to resolve 2026-08-20:

| Resource | URL |
|---|---|
| Full FGDB (the one the audit reads) | `https://static.data.gov.hk/td/traffic-aids-drawings-v2/dTAD_IRNP.gdb.zip` |
| Data specification + `Index Plan` | `https://static.data.gov.hk/td/traffic-aids-drawings-v2/dataspec/tadrawings_dataspec.zip` |
| Per-layer GML / KMZ | `https://static.data.gov.hk/td/traffic-aids-drawings-v2/DTAD_{LAYER}.{gml,kmz}` — `DTAD_RD_MARK_LINE.gml` alone is 163 MB, the same trade the road network's GML makes (`Q9`) |

### ❌ Surveyed and rejected for kerbside restrictions (2026-08-20)

`Q56` swept every Transport Department dataset on DATA.GOV.HK (60), the CSDI Portal catalogue, and
every one of the 3,810 packages whose name touches road, parking, marking, restriction, kerb,
street, lane, loading, stopping, sign or bay. **`NSR` and `DTAD_RST_ZONE_LINE` are the only two
datasets in the estate that assert a kerbside stopping restriction** — there is no third opinion.
Recorded so the sweep is not repeated:

| Dataset | Why not |
|---|---|
| `hk-td-msd_1` Metered Parking Spaces | CSV of counts per district plus new-meter occupancy. No per-bay geometry |
| `hk-td-msd_2` Non-metered On-street Parking | ~250 sensored spaces **territory-wide**, a trial scheme |
| `hk-td-tis_4` / `tis_5` parking distribution, vacancy | Real-time occupancy, not restriction |
| `hk-td-tis_36` Pedestrian Streets | Area and effective hours; Road Network v2's `PEDESTRIAN_ZONE` already covers it |
| `hk-landsd-openmap-road-centreline` | LandsD's own description: "primarily focused on approximate location query and map annotation labelling" |

⚠️ **Two the sweep turned up that are worth their own look, and are *not* about yellow lines:**
`hk-td-tis_39` **Fleet Taxi Stopping Places** (new, Oct 2025 — bears on `fares.json`) and
`hk-hyd-csdi-pavement-polygon`, the Highways Department's maintained pavement extents, which bear on
`carriageway_occupancy`'s open failure and on the play widening.

✅ **Both had that look, in `Q57`, 2026-08-20.** Fleet Taxi Stopping Places is under "Fares and
points of interest" below; the pavement extents are next.

### ✅ SURVEYED, not fetched — HyD Pavement Polygon

**`hyd_rcd_1632210918434_60749`** · Highways Department · CSDI Portal only, no DATA.GOV.HK package ·
ArcGIS `MapServer` layer `INV_PG` and a WFS endpoint

*"The data provides location information of types of pavement maintained by Highways Department"* —
the maintained pavement as **polygons**, the second independent answer to the carriageway width
`Q19` called unpublished until `Q57`. Queried over the Wan Chai envelope in EPSG:2326:
**1,714 polygons**, carrying `FEAT_TYPE`, `SUR_TYPE_1`, `PAVER_TYPE`, and an **`LVL` of `0` / `1` /
`-1`** that mirrors Road Network v2's `ELEVATION` convention.

| `FEAT_TYPE` | polygons | `Shape_Area` |
|---|---|---|
| `1` | 552 | 599,162 m² |
| `2` | 917 | 129,352 m² |
| `6` | 85 | 10,763 m² |
| others (`3`, `7`, `8`, `9`, `31`, `32`) | 160 | 19,842 m² |

⚠️ **The `FEAT_TYPE` domain is not decoded and the areas are not clipped.** The envelope is 1.46 km²
and the query is `intersects`, so a polygon reaching outside contributes its whole area — `1` at
599,162 m² is not 41% carriageway, it is an unclipped sum. Anyone acting on this owes the HyD
specification and a real clip first.

### ✅ READ, not fetched — TD's Transport Planning & Design Manual, Volume 2 (`Q95`)

**`https://www.td.gov.hk/filemanager/en/content_5055/V2_03_2026.pdf`** · Transport Department ·
published on `td.gov.hk`, **not** a DATA.GOV.HK or CSDI dataset · Chapter 3, **March 2026 edition**,
282 pages, with a real text layer (`pdffonts` lists embedded fonts, `pdftotext` recovers the tables).

🔴 **A design standard is not a survey, and the difference decides what it may be used for.** It says
what a Hong Kong road *should* be, never what one *is* — so it cannot give a per-edge width, and
using it to assign one would be authoring policy with better provenance, which is the move
`lanes_by_min_speed_limit_kph` already makes and `Q54` argues against. What it *can* do is bound an
instrument and give an authored number its source.

**Table 3.4.2.1 — Minimum Carriageway Widths in Urban Areas**, per carriageway:

| Road type | single, 2 lane | single, 4 lane | dual, 2 lane | dual, 3 lane | dual, 4 lane |
|---|---|---|---|---|---|
| Trunk Road / Expressway | — | — | 7.3 | 11 | 14.6 |
| Primary Distributor | — | — | 6.75 | 10 | 13.5 |
| District Distributor | **7.3 or 10.3** | **13.5** | 6.75 | 10 | — |
| Local Distributor | **7.3 or 10.3** | **13.5** | 6.75 | — | — |

And four clauses this project touches directly:

- **3.4.2.3** — a double-track tram reserve requires **5.5 m**. `pipeline/tramway.py`'s territory.
- **3.4.2.6** — distributors may carry an extra **3 m** parking strip beside the running lanes.
- **3.4.4.1** — carriageways widen on curves under 400 m radius: a 13.5 m four-lane becomes **15.8 m**
  below 150 m.
- **4.3.9.8** — a through traffic lane is **3.0–3.65 m**, exclusive of hard strips.
- **3.4.2.7** — a two-way single carriageway **must not** be divided into three lanes, other than a
  climbing lane on a gradient. A derived odd lane count on a `direction=both` edge is therefore a
  finding, not a reading.

🔴 **What this says about what ships.** `roadgraph.json`'s `width_m` is `lanes × lane_width_m` =
2 × 3.2 = **6.4 m** on 720 of the region's 737 edges. That is **below every figure in the table** —
under the 7.3 m minimum for a two-lane single carriageway, and under even the 6.75 m allowed *per
direction* on a dual carriageway. The authored width is not merely underived; it is outside the range
TD permits.

✅ **And STEWART ROAD's measured 14.81 m is corroborated rather than merely observed**: it matches a
13.5 m four-lane urban carriageway with a parking strip, or a four-lane widened on a curve (15.8 m).
It is reconcilable with no two-lane figure in the table. `Q94`'s arrows say the same thing
independently — three symbols side by side at one station.

✅ **The bound an instrument needs.** The widest urban carriageway here is 13.5 m, 15.8 m on a tight
curve, ~16.5 m with a parking strip. So a two-sided ray returning **36.09 m on LUNG WO ROAD** or
**35.26 m on FLEMING ROAD** has crossed a median, a tram reserve or a junction mouth — which is now a
citable refusal rather than a suspicion, and is what `tools/carriageway_margin.py` would need to
measure a *width* rather than a one-sided overhang.

⚠️ **Read, not fetched.** Nothing in `etl/` downloads this and nothing should: it is one table, and
the figures above are transcribed here the way `CT174/51-5(1)F`'s marking dimensions are. ⚠️ **It is
city-specific**, so any value taken from it belongs in `etl/config/cities/hong_kong.yaml` under hard
rule 3 — the second city has its own manual. ⚠️ **A standard is a floor, not a description**: the
table is headed *Minimum*, and 3.4.2.2 lets trunk widths fall below it "on economic or other
grounds".

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
  ⚠️ **Measured over these 29 points and true of them, but it is not a property of the stage.**
  `P3-14` added 19 tram stops, and one of them — `f_032`, on Hennessy Road under the Canal Road
  Flyover — has a level-1 runner-up that **wins**, by 0.80 m. Candidates are restricted to level 0
  since 2026-08-21; `Q15` records what changed and what is still open.

> **Region note:** Hong Kong Island uses **red urban taxis**. Green (NT) or blue (Lantau) livery in
> this map would read as wrong to any local player.

### ✅ SURVEYED, not fetched — four more point sets that bear on this section (`Q57`)

The two above are what `P1-5` reads. These are the rest of what the estate publishes, all CSDI
`file-api` GeoJSON on the same pattern and needing no key. Counted inside the region on 2026-08-20:

| Dataset | Territory | In region | Bears on |
|---|---|---|---|
| `td_rcd_1760062901418_33580` Fleet Taxi Stopping Places | 17 | **2** | The fare loop. One is *"A section of Expo Drive eastbound outside Hong Kong Convention and Exhibition Centre"* — a landmark the bundle already ships. ⚠️ Names are **prose, not a street code**, so it does not snap the way the two above do |
| `td_rcd_1638874475129_49745` Bus Stop Location | 4,480 | **70** | `P3-3` traffic, POI density |
| `td_rcd_1638874728005_80512` GMB Terminus Location | 4,760 | **52** | as above |
| ✅ `td_rcd_1638875413253_59498` Tram Stop Location | 117 | **19** | trams, which `GAME_DESIGN.md` calls the highest-leverage single object in the game. **Fetched and shipped by `P3-14`** as the `poi` kind — the first thing ever to produce one. ⚠️ **It publishes no name**: `OBJECTID`, `STOP_ID` and `LAST_UPDATE_DATE`, and nothing else, across all 117 features. `fares.json` carries `name: null` for all 19 rather than shipping `STOP_ID` as a place name, and `pickup`/`dropoff` are both **false** — a tram stop is somewhere a *tram* stops |

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
