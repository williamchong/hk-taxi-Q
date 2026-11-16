# Progress

Live state only: what is in flight, what is owed, what is at risk, what was last measured.

- Task definitions and acceptance → `PLAN.md`.
- Why something is the way it is → `DECISIONS.md`, keyed by the `Q` or task ID.
- What happened when → git.

Keep rows to one line. A row that needs a paragraph belongs in `DECISIONS.md`.

---

## Current status

- **Phases 0–1:** complete.
- **Phase 2:** the gate waits on hardware, not software. `P2-4` (touch) and `P2-6` (perf) need
  `P0-3b`'s floor handsets (A13, Adreno 618). A signed build runs on an iPhone Air and 1.0.0 (1) is
  on TestFlight (`tools/ios.sh`; store listing in `fastlane/`). Android is unbuilt.
- **Phase 3:** all four builds are built ahead of their reviews.
  - `B2` (reads as Hong Kong) shipped; `P3-9a` recognised Wan Chai from geometry alone.
  - `B1` (one fare): router, TD's tariff, fare HUD, street hails, minimap with route line.
  - `B3` (streets alive): parked roster, signals, 60 AI cars by the hour, routed buses and
    minibuses, trams, horns, push on impact.
  - `B4` (a game): skills, penalties, air, the style combo, 特更 / 兜風 modes, the 成績表 and record.
  - The car is a per-wheel tyre model on a spec sheet at pace 2.0 (`Q152`, `Q153`, `Q156`). The day
    runs to night and round again (`Q160`, `Q222`, `Q225`), a clock minute a second (`Q233`).
- **Phase 6:** `P6-1` (menu, options, credits and licences, pause, RESET CAR) built early.
- **Phase 4:** `P4-1` done; the 15 tunnels stay shut. **Phase 5:** all built but `P5-8` (content)
  and `P5-14`. The runtime holds `wan_chai` + `causeway_bay` across a seam; `mong_kok` and
  `sha_tin` are built for measurement only.

**Owed next**

- The user's drive of nearly every 🟡 row below; the largest are one fare start to finish (`B1`), a
  whole shift to 交更 (`P3-74`), a night drive (`P3-69`), and the touch scheme on a handset (`Q238`,
  `Q239`, `Q230`, `Q241`).
- `P0-3b`: FPS on an A13, an Android build, then `P2-6` and the handset re-take of `traffic.tres`
  `cars`.
- `P3-9` (authenticity round 1, the Phase 3 gate): different drivers from `P3-9a`, on a handset.
- Not started: `P3-1b`, the one-handed layout (`P3-5b`), `P4-2`–`P4-5`, `P5-8`, `P5-14`.
- Known gaps: signal heads at 16 of Wan Chai's 72 staged junctions and 7 of Causeway Bay's 21 do
  not show every stage (`P3-3e`); a new driver cut (below).

**Driver artefact.** Host: <https://williamchong.itch.io/hong-kong-taxi-q>. The last named cut is
`r5` (`build/hk-taxi-q-p39a-r5-itch.zip`); it predates `P3-26` onward. Rules for any cut
(`DECISIONS.md` `P3-9a`, `Q77`):

- One new name per cut, never an overwrite.
- Re-export before packing (`tools/export.sh web`); never pack what a measurement left in
  `build/web/`. Nothing in the repo builds the itch zip.
- Re-check "0 console errors" on every cut; `check.sh` cannot see that class.
- The embed needs itch.io's "SharedArrayBuffer support" toggle.
- The console's `signs:` count minus `signs.json.triangles` must equal `text_plates × 2`.

### Task board

⬜ not started · 🟡 built, the user's drive / look / review owed · ✅ done · 🟢 closed by verdict ·
🚫 built, withdrawn · ❌ no-go. A clause names only what is owed beyond the drive, or the blocker.

Phase 0–2

- ✅ `P0-1`, `P0-2`, `P0-3`, `P0-4`, `P0-5` (`a`–`d`), `P1-1`–`P1-7`, `P2-1`–`P2-3`, `P2-5`, `P2-7`.
  `P1-2t` superseded by `P3-10`.
- `P0-3b` 🟡 Mobile device build — owed: FPS on an A13, Android. The iOS simulator cannot run it
  (the 4.7.2 template's simulator slice is x86_64 only).
- `P2-4` 🟡 `InputRouter` — touch drives three of five actions (`Q97`); every `touch.tres` value is
  a desk pick; needs `P0-3b`.
- `P2-6` 🟡 Performance pass — `--perf-log=<s>` built; the phone's app at 0.75 scale and MSAA 2x
  (`Q236`); owed: the A13 floor, Android, the railings in motion.

Phase 3 — `B2` and the road

- ✅ `P3-11`, `P3-11d`, `P3-13`, `P3-16`, `P3-18`–`P3-20`, `P3-22`, `P3-23`, `P3-26`, `P3-28`–`P3-31`
  (`P3-29a` included), `P3-34`, `P3-36`–`P3-42`, `P3-66`, `P3-77`.
- `P3-9a` 🟢 Recognition round 0 — recognised; stopped by the blocked bridges (`P3-9a′`).
- `P3-6` 🟡 Hero buildings — HKCEC reviewed; Central Plaza unjudged; three not built.
- `P3-7` 🟡 Window-band shader. `P3-10` 🟡 Ground surface — buries the carriageway on hill streets
  (`Q24`).
- `P3-11c` 🟡 Body shader. `P3-11e` 🟡 Front lamps. `P3-11f` 🟡 Roof sign. `P3-48` 🟡 Hire state on
  the car.
- `P3-12` 🟡 Road markings on the ribbon — the shader's lines are off (`Q132`).
- `P3-14` 🟡 Tramway as geometry. `P3-15` 🟡 Turn arrows.
- `P3-27` 🟡 Crossing paint shipped as `P3-35g2`; footway extent and look-right glyphs are
  candidates (`Q101`).
- `P3-31` open item: lamps, signs and railings do not refuse a foot under a level-0 cap.
- `P3-32` ✅ Paint arm; the carve-wall arm is not taken (`Q104`) — never by widening the carve
  prism.
- `P3-33` 🟡 Level-0 road as the carriageway region — `a`–`c`, `e` built, `d` superseded by
  `P3-35e`; `f` (the user's drive) open.
- `P3-34` open items: no `RM1002`/`RM1003` side checked against Street View; zigzags unbuilt.
- `P3-35` ✅ `a`–`g3`, `h` built — `h`'s drive owed. `P3-35g4` 🚫 lane count hosted on the drawn
  ribbon: 82% / 75% agreement against a high-80s bar.
- `P3-67` 🟡 Lamps as a `MultiMesh` per 300 m cell. `P3-68` 🟡 Fences and railings collide.
- `P3-69` 🟡 Day to night — owed: the handset's frame time.
- `P3-70` 🟡 Light tail — owed: the look pick from `build/driver/tail_sheet/sheet.png`.
- `P3-82` 🟡 Taxi at a die-cast's detail — owed: the headlamp spots sit 16 cm above the moved
  lenses.
- `P3-83` 🟡 Posts collide — owed: `phys` on the throttle route.
- `P3-84` 🟡 Detail lines on vehicles — owed: the weight pick (1.2 / 2 / 3 cm), a night frame.
- `P3-85` 🟡 Roster at die-cast detail — owed: the box lorry's share of moving traffic (parked only).
- `P3-87` 🟡 Pressed panels. `P3-88` 🟡 Tram doors and lamps.
- 🚫 `P3-7a` (withdrawn, `Q102`), `P3-17` (returned as `P3-3e`, `Q173`). ❌ `P3-21` (`Q65`).

Phase 3 — `B1`, `B3`, `B4`

- ✅ `P3-24`, `P3-25`, `P3-43`, `P3-1a`, `P3-5a`, `P3-44`–`P3-47`, `P3-52`, `P3-59`, `P3-60`, `P3-64`,
  `P3-80`, `P3-3e`. Owed on them: the `B1` drive; a press of SAVE RESULT on the web build; the
  minimap's web clip frame; the outline's handset frame time.
- `P3-1a` note: four pickups are stranded by one-way exits off the map (`wan_chai/f_017`, `f_018`,
  `f_020`, `causeway_bay/f_001`); only `Q6` reopens them.
- `P3-86` 🟡 Street hails and a measured par (`Q203`).
- `P3-3` 🟡 Traffic — `a`–`c`, `e`, `f1`–`f3`, `g` built; owed: the handset re-take of `cars`,
  whether `is_routable`'s bar is a lane or a vehicle (`P3-33e`). Seeds 1, 2 and 8 meet in a
  signalled junction (`Q182`).
- `P3-3d` 🟡 The player's red — counted, never paid or docked until something enforces it (`Q181`).
- `P3-2a` 🟡 Near miss, parked and moving (`Q161`, `Q175`).
- `P3-71`–`P3-73`, `P3-75` 🟡 Parked roster — finding: the fill's lane-room bar does not count a bay
  on the far kerb.
- `P3-4` 🟡 Trams — owed: the handset's cost. Push on impact (`Q180`) 🟡.
- `P3-8` 🟡 Taxis in the traffic — owed: minibus behaviour.
- `P3-78` 🟡 Routed buses and green minibuses — owed: the frame cost.
- `P3-79` 🟡 The taxi's sounds — owed: the user's ears, the PCK cost.
- `P3-49` 🟡 Skills, the receipt, the passenger's face. `P3-50` 🟡 Penalties — owed: a crash-tier
  hit on the street.
- `P3-51` 🟡 Air and the eight jumpable ramps — the flyover parapet band stays off (`Q147`).
- `P3-53` 🟡 Drift bars — owed: the kerb slide at speed, the tap under 30 kph.
- `P3-54` 🟡 Real technique — the lifted flick stays under the threshold on the `mu` 1.0 car except
  at 63 kph; which fails to work is the user's call.
- `P3-55` 🟡 Power-on corner — `turn_drive_cut` 0.5 is provisional.
- `P3-56` 🚫 Drift assist as a setting — dropped; one car, no automatic countersteer.
- `P3-57` 🟡 Tyre marks and smoke. `P3-58` 🟡 Drift sparks — owed: the colour and tier pick.
- `P3-61` 🟡 Overspin — open: `turn@off` at 63 kph 8° over its bar.
- `P3-62`, `P3-63` 🟡 Pace 2.0 — owed: the game's bars re-read at the pace; the LSD deferred.
- `P3-65` 🟡 Outline answers the car.
- `P3-74` 🟡 Two modes — owed: a full shift. `P3-76` 🟡 成績表 and record — no red-light row.
- `P3-81` 🟡 A free drive's REPORT.
- `P3-2b` 🟡 Style combo — `combo_gap_s` 2.5 is a guess; the fare combo is unbuilt.
- `P3-5b` 🟡 Safe areas and touch layout — owed: the one-handed layout.
- `P3-1b` ⬜ Cross-harbour and long haul. `P3-9` ⬜ Authenticity round 1.

Phase 4–6

- `P4-1` ✅. `P4-2`–`P4-5` ⬜ — `P4-2` owns the rest of `Q15`; `P4-3` MARSH ROAD's lip; `P4-5`
  streaming distances and LOD0's cell.
- ✅ `P5-1`–`P5-7`, `P5-9a`–`d`, `f`, `g`, `P5-10`–`P5-13`, `P5-15`–`P5-28`. `P5-9e` 🚫 shared
  libraries (+3 to +11 draw calls at the seam). Owed: the drive across the seam (`P5-9f`).
- `P5-8` ⬜ Content — behind `P3-9`, `Q6`. `P5-14` ⬜ Textures as an option on tiles.
- `P6-1` 🟡 Start menu, options, credits, pause — owed: Android's back button (`P0-3b`).

---

## Questions

Every record is in `DECISIONS.md` under its ID. A question closes here and there in the same
change. Closed questions are not listed here: see the headings in `DECISIONS.md`.

### Open

- `Q6` Does the region need Central? Deferred to after `P3-9`.
- `Q13` Nothing ramps between levels in the source. Left: the 15 bores — needs a vertical
  instrument, not a wider `levels`.
- `Q14` Stands carry operating hours `P1-5` discards. Deferred.
- `Q15` Fare nodes snap by plan distance; a point on a deck snaps to the street below (`P4-2`).
- `Q19` Solid geometry in the carriageway. Left: the building half, a drive of `e99`, the
  carve-wall arm (`Q104`).
- `Q21` Should level −1 be drawn at all? 11 of 30 ends clipped at the region boundary.
- `Q22` Off-grade carriageway hangs past its structure; no width rule reaches the rest.
- `Q24` The road is a plane and the ground is not. Three mechanisms, none assigned
  (`ground_clearance.py`).
- `Q30` Shipped façade palette exceeds `ART_DESIGN.md`, on purpose; `strength` cannot fix it.
- `Q31` The value range has an empty middle; needs a sky-visibility bake. `Q39` (`wall_sky_tint`
  uniform) is free once that exists.
- `Q35` Per-building material draw gives a salt-and-pepper skyline. Candidates: spatial hash,
  block join, accept.
- `Q62` Sign facing is derived and ungraded.
- `Q115`, `Q116` Props and the two-region seam: built; a stub across the seam joins nothing.
- `Q120` Scaling numbers extrapolated from Wan Chai (`P4-5`); `sha_tin` / `mong_kok` are ungraded
  by the batteries.
- `Q121` Mesh contract vs a DCC workflow: `P5-14` left.
- `Q122` Two one-line calls for the user: the far-tier occluder (culls nothing, 4.63 MB) and a
  web bundle without occluders.
- `Q126` Stacked arrows on two-way streets: C (lanes painted 2.7–2.9 m) and D (tram reserve in
  the width) each need a decision.
- `Q135` Which deck's paint where two decks cross (Sha Tin).
- `Q179` A drift holds 30 s on the pad and under 2 s on the street, so it is not capped; reopens
  on any open space.
- `Q181` Traffic-law penalties (red light, bus lane, double yellow) wait for an enforcer; no task.

### Picks owed by the user on built work

- `Q154` spark colours and tiers · `Q196` ink weight · `Q235` dawn / dusk strength · `Q213`
  headlamp beam loudness · `Q229` whether RESET CAR costs anything · `Q208` a slang rank ladder ·
  `Q234` glazed or open upper tram leaves · `Q220` steering curve 2.0 against 1.5.
- `Q237` leaves the signal heads untested against junction asphalt. `Q226` is unseen in a browser.
  `Q233`: a best set on the 5-minute shift still stands.

### Residue inside closed questions

- `e257` paints 2.45 m inside its own bracket; a lane count cannot vary along an edge (`Q113`,
  `Q114`). `e333` / `e504` count three and paint two (`Q130`).
- Single stations where HyD's polygon touches the centreline at a node (`Q131`). The seam's
  0.62 m overlap strip (`Q129`). The street borrow for unread widths (`Q127`).
- 52 `RM1001` refusals need coverage-based hosting (`Q118`).
- MARSH ROAD's 0.65 m deck face needs a node-level descent pass (`Q90`).
- 9,779 triangles a run hit `MAX_SUBDIVISIONS` in `clearance` (`Q51`).
- Speed-limit signs (73) on hold (`Q65`); deviation boards ship on an ungraded assumption (`Q66`);
  the sign survey's plate box and `_plate_box` disagree on 10 of 21 faces (`Q68`).

---

## Risk register

- **Doesn't read as HK to locals** — High until `P3-9`: different drivers, handset, arrow off.
- **Building meshes blow the triangle budget** — High. `wan_chai` 128%, `mong_kok` 184% of 300k;
  LOD0 carries 84–91%. The lever is LOD0's cell and radius (`P4-5`), not the LOD1 ratio.
- **Perf misses 60 fps on the device floor** — Medium. Only an iPhone Air has run it (`P2-6`).
- **The tyre model is unpriced on the floor handsets** — Medium. ~216 µs a tick on the desk, eight
  substeps a wheel; the lever is `substeps`; there is no other car to fall back to (`Q152`).
- **Web artefact and product render differently** — Medium. The web runs Compatibility and crushes
  shadows, cause undiagnosed (`Q76`). Name the renderer in any write-up.
- **Novelty does not survive the first session** — Medium. Unmeasured; record how long each
  `P3-9` driver keeps going.
- **Carriageway occupied by solid geometry** — Medium. Carved and fenced (`Q19`); the building half
  is left.
- **Occluder is dead weight on the web cut** — Medium. Stock web templates omit the raycast
  module (`Q122`).
- **Open elevated network is unfinished** — Medium. MARSH ROAD's 35.8% lip is reachable (`P4-3`);
  the streamer is tuned without the extra area (`P4-5`).
- **Podium floors measure the treatment band** — Medium. `Q47`; true fill owed.
- **TAM too small** — Medium. Hong Kong only (`Q100`); scale by regions behind the IAP boundary.
- **GPLv3 forecloses the App Store** — Medium. Contributions come in under MIT
  (`CONTRIBUTING.md`); no retrofit once an outside contributor declines.
- **`facade_lab.json` is an uncommitted input** — Low. Gitignored and hand-run; it carries the
  bands and `noise_l` (`Q197`, `Q240`), so a podium change wants `facade_survey.py --regions`
  re-run.
- **A test depends on the developer's fetched sources** — Low. Run the suite with
  `pipeline.fetch.SOURCES_ROOT` at an empty directory (`CONTRIBUTING.md`).
- **A shader fails silently** — Low. `check.sh` exits 0; render and `grep -i "shader error"`.
- **`tools/collider_offset.py --sweep` crashes** — Low. Its scratch build lacks `basemap.json`;
  the plain run grades.
- **3 road-mark triangles under the road at a ribbon overlap** — Low. Worst 0.0151 m (`Q125`); the
  fix is a crease in `DrawnSurface`, never `lift_m`.
- **`sha_tin`: 5 box-junction triangles inside no ring** — Low. `box_extent.py` `unattributed`
  must be 0 (`Q123`).
- **Landmark depiction IP** — Low. Legal sight-check before launch (`LICENSING.md`).

---

## Metrics

Latest values only. Layer counters are read from `etl/out/<region>/*.json` — verify there before
quoting. Two values are `wan_chai` / `causeway_bay`.

Budget

| Metric | Target | Latest |
|---|---|---|
| FPS on device floor | 60 | — (`P0-3b`); iPhone Air ~96 fps under `--max-fps 120` (`Q222`) |
| Video memory, iPhone Air | — | 235.9 MB at 0.75 scale, MSAA 2x (`Q236`) |
| Draw calls | < 150 | throttle route 116–122 with traffic, HUD off (`Q214`); `P2-6` measures properly |
| Resident triangles, worst camera | < 300k | 128% / 82%; with paint 161% / 91%; buildings alone 110% / 73% (`tools/resident_budget.py`, 2026-11-17). `mong_kok` 184%, `sha_tin` 47% (2026-09) |
| Texture memory | < 128 MB | one 512 x 256 atlas, 47,398 B (`signs_text.png`) |
| Bundle size (PCK) | < 200 MB | web 98,750,864 B (`build/web/index.pck`, 2026-11-17); iOS app 116,032,712 B (`build/ios/app`, 2026-11-17). Re-export before quoting |
| First load, web, cold shader cache | — | 14.0–14.8 s boot, then the cover ~6 s (`Q184`) |
| First frame, iOS fresh install | — | ~12 s with baked shaders; relaunch ~4 s (`Q207`) |
| Traffic tick, 60 cars | — | 1.67 ms bench, 2.59 ms p50 in game (`Q219`) |

Scaling (`Q120`, four regions)

- Tiles 27.7 KB a building (1.8× spread); thin layers ~66 KB a road-km; 200 MB buys ~5–15 km².
- Library meshes are region-invariant, so draw calls are too; only bytes and triangles scale.

Bundle, from `etl/out` (schemas: `city.json` 46, `roadgraph.json` 15, `roadsurface.json` 12,
`carriageway_region.json` 4, `basemap.json` 2)

| Counter | `wan_chai` / `causeway_bay` |
|---|---|
| Road graph | 792 edges, 614 nodes, 217 turn restrictions / 207, 166, 35 |
| Road surface triangles | 92,611 / 31,355 |
| Measured width, level 0 | 393 of 734 (53.5%) / 124 of 196 (63.3%) |
| Signs drawn | 840 of 3,276 published, 614 poles, 110 text plates / 279 of 1,009, 213, 51 |
| Lamps drawn | 997 of 1,263 candidates, `on_deck` 92, `min_kerb_clearance_m` 0.0397 / 361 of 441, 16, 0.1 |
| Railings read | 16,954 of 20,273 m / 6,356 of 7,169 m |
| Arrows drawn | 741 of 1,365 symbols, `stacked_disagreeing` 18, `placed_by_slot` 16 / 158 of 367, 0, 6 |
| Road marks drawn | 2,279 of 2,593 candidates, `host_off_carriageway` 267 / 568 of 626, 47 |
| Crossings drawn | 120 of 121, 762 stripes / 16 of 17, 80 |
| Box junctions | 20 of 20, 14,931 triangles / 4 of 4, 1,318 |
| Tramway | 132 rails (9,086 m), 63 tracks, `off_gauge_stations` 62 of 1,978 / 34 (2,854 m), 15, 11 of 433 |
| Tram lines | 60 directed tracks (4,393 m), 19 stops / 13 (1,371 m), 5 |
| Signals | 73 junctions, 72 staged, 178 approaches, 514 head posts / 22, 21, 41, 89 |
| Parked placed | 716 of 1,346 candidates / 340 of 705; no parked trams |
| Trees drawn | 1,061 of 1,123 / 2,375 of 2,413 |
| Bus route directions kept | 464 of 486 / 241 of 251 |
| Fare nodes, street spots | 48, 221 / 7, 166 |
| Harbour | 748,723 m² of sea / 177,055 m² |
| Parks | 86 polygons, 131,534 ground vertices painted / 57, 122,157 |
| Player fence | 14 components, 15 mouths, 5 touchdowns, 67 clipped ends / 2, 4, 0, 19 |

Graders (last battery readings; report-only unless a target is shown)

| Metric | Target | Latest |
|---|---|---|
| Deck error, \|error\| p90 vs shipped tiles | ≤ 0.50 m | 0.094 / 0.182 m |
| Off-grade carriageway past its structure (`Q22`) | — | 5.0% / 25.3% (`overhang.py`; Causeway Bay's is the seam's far halves) |
| Off-grade stations under the 3.20 m lane bar | — | 0 |
| Paint below the road by > 10 mm | ≤ 0.5% of triangles | passes; 3 of 24,023 road-mark triangles deep (`Q125`) |
| `lane_paint` edges painting a lane under 3.00 m | — | 76 / 18 |
| Occupancy share at bumper height | `BUILDING` ≤ 1.72%, `INFRA` ≤ 1.60% | 0.214% / 0.560% · 0.309% / 0.338%; the corridor gate fails, 27 / 11 edges under one lane |
| Ground proud of the carriageway (`Q24`) | — | 38 of 734 / 49 of 196 level-0 edges past 0.18 m |
| Railing to-source distance, p50 | — | 0.22 / 0.21 m |
| Reachability lost to the fence | 0 at the car's bar | 0 / 170 ordered pairs; at the one-lane bar 3,989 (2.17%) / 173 |
| `RoadRouter` against `reachability.py` | within 0.001 m | worst 0.000000 m on every pair, and across the join |
| `RoadRouter.prepare`, max | ≤ 16 ms | legal 0.70 / 0.13 ms, player 1.86 / 0.59 ms |
| `RoadRouter.route`, prepared, p99 | ≤ 1 ms | 8 / 7 µs |

Handling

- The car is `TyreVehicleController` on `tuning/cars/crown_comfort.tres`, `tyre.tres` (`mu` 1.0)
  and `tuning/systems/`, at `pace.tres` `pace_scale` 2.0. Run `tools/skidpad.sh` before and after
  any change; the pad is fixed-step and byte-repeatable.
- Player taxi: 2,130 triangles against a 2,200 ceiling (`Q202`).
- Drag and brake coefficients are measured on the pad, never in `city_drive.tscn` (a 0.14°
  gradient is the size of the quantity under test).
