# Plan — Vertical Slice

**Scope:** prove three things before committing to full production.

1. The ETL pipeline works on real HK open data.
2. The driving is fun.
3. The city reads as Hong Kong to Hong Kong drivers.

**Out of scope for the slice:** monetisation, art polish, Central.

Task IDs are stable — reference them in commits and in `PROGRESS.md`. Live status and measured
numbers live in `PROGRESS.md`'s task board; a task's record is in `DECISIONS.md` under the `Q`
named beside it. Here a done task is one line.

Legend: ⬜ not started · 🟡 built or in progress, something owed · ✅ done · 🚫 built, not shipped
or withdrawn · ❌ no-go.

---

## Review protocol

Every reviewable unit from Phase 2 onward (a task in Phase 2, a build in Phase 3) carries
`Review: <what to look at> | <the command that produces it> | <the verdict question>`.

- A unit is machine-checked (`tools/check.sh`, `verify_*.gd`, `pytest`) or human-judged (the user,
  driving or looking). Two machine-checked units in a row may not pass without a human-judged
  artifact.
- Review points are hard gates: work stops until the user has driven the build. Status goes in
  `PROGRESS.md`, what the verdict decided in `DECISIONS.md`.
- Name the verdict question in advance; a verdict is read no wider than the question asked
  (`Q8`, `Q98`).
- Default route is the web build (`.claude/skills/run-hk-taxi-q/`). Driver screenshots are the
  progress report, not the verdict. A debug overlay is reviewed under the driver;
  feel-in-the-hand needs the handset.
- A dependency graph does not catch a missing capability no task owns (`P2-5` needed building
  collision; `B2` needed a taxi model). Check acceptance criteria for that shape.

---

## Phase 0 — Spikes and scaffolding

| ID | Task |
|---|---|
| `P0-1` | ✅ Source data granularity — per-sheet glTF, fully scriptable |
| `P0-2` | ✅ Z-value spike — Road Network v2 has no Z; `ELEVATION` encodes the level |
| `P0-3` | ✅ Godot 4.7 Mobile project; macOS, web and Android export |
| `P0-4` | ✅ `etl/` package, `hong_kong.yaml`, `crs.py` |
| `P0-5` | ✅ Grey-box vehicle — conditional pass, closed by `Q8` |

### `P0-3b` Mobile device build verification 🟡

- **Built:** the real bundle identifier in `export_presets.cfg`; a signed build on the user's
  iPhone Air through `tools/ios.sh`, also on TestFlight.
- **Remains:** a build on both floor handsets (`Q4`: A13 / Adreno 618) — FPS on an A13, and Android.
- **Accept:** the current scene runs on-device with the FPS counter visible; measured FPS recorded.
- Blocks `P2-4`'s and `P2-6`'s reviews.

---

## Phase 1 — ETL vertical slice ✅

Gate passed: Wan Chai renders in Godot from `city.json`, georeferenced and verified in-engine.

| ID | Task |
|---|---|
| `P1-1` | ✅ `fetch.py` — idempotent, sheets from the published index |
| `P1-2` | ✅ `buildings.py` — tile meshes, vertex colours, no textures |
| `P1-3` | ✅ `roads.py` → `roadgraph.json` (`Q12`) |
| `P1-4` | ✅ Ribbon mesh with kerbs and collision (`Q13`) |
| `P1-5` | ✅ `fares.py` → `fares.json` |
| `P1-6` | ✅ `export.py` — `city.json`, byte-reproducible |
| `P1-7` | ✅ Godot loads `city.json` |

---

## Phase 2 — Driving the real city

**Goal:** the player drives real Wan Chai at 60fps on the device floor. Review points 1 and 2 are
passed; point 3 is `P2-6`.

| ID | Task |
|---|---|
| `P2-1` | ✅ `CityStreamer` (`Q16`) |
| `P2-2` | ✅ `RoadGraph` runtime and debug overlay |
| `P2-3` | ✅ `VehicleController` on real geometry (drive model since `Q50`, `Q152`) |
| `P2-5` | ✅ Chase camera (`Q98`) |
| `P2-7` | ✅ Off-grade carriageway on its structure (`Q23`); sequenced before `P2-6` |

### `P2-4` `InputRouter` 🟡

- **Built:** touch, gamepad and keyboard → one action set (`Q83`, `Q97`, `Q204`, `Q238`, `Q239`).
- **Accept:** all three input paths drive the car; no gameplay script reads raw input.
- **Review:** all three paths | on-device build | the user says whether touch steering is usable.
- **Remains:** the review on the floor handsets (`P0-3b`).

### `P2-6` Performance pass to budget 🟡

- **Built:** the frame log (`--perf-log=<s>`); the phone's app draws 3D at 0.75 scale and MSAA 2x
  (`Q236`), measured on an iPhone Air.
- **Accept:** 60fps on the device floor while driving real Wan Chai, measured, recorded in
  `PROGRESS.md`. Review point 3 and the Phase 2 gate.
- **Review:** the same drive on the handset | on-device build | **Does it feel smooth?**
- **Remains:** the A13 floor and Android (`P0-3b`); the user's look at the railings in motion;
  tile hitching re-measured with the trimesh registered on the main thread.

---

## Phase 3 — Playable slice

**Goal:** a Wan Chai that reads as Hong Kong to strangers, then a complete arcade loop around it.

Four builds run `B2` → `B1` → `B3` → `B4`. Build letters name content, not running order; do not
renumber. The city comes before the loop on the user's call (`Q8`: "the city itself is the fun").

### Build `B2` — "It reads as Hong Kong"

**Review:** drive Hennessy Road and look around | web build | **Does this read as Wan Chai?**
Content added after `P3-9a`'s cut reaches drivers only by re-exporting and re-packing the itch zip
by hand (`Q53`).

| ID | Task |
|---|---|
| `P3-11` | ✅ Player taxi from `tools/make_vehicle.py` (`Q190`) |
| `P3-13` | ✅ Kerbside no-stopping from `NSR` (`Q54`, `Q56`) |
| `P3-14` | ✅ Tramway as published geometry, `tram.glb` (`Q58`) |
| `P3-15` | ✅ Turn arrows from `DTAD_RD_MARK_SYM_PT` (`Q59`, `Q93`) |
| `P3-16` | ✅ Traffic signs on TD's surveyed poles (`Q60`, `Q62`, `Q64`, `Q67`) |
| `P3-18` | ✅ Yellow box junctions (`Q54`, `Q92`) |
| `P3-19` | ✅ Railings, bollards, barriers (`Q60`, `Q61`) |
| `P3-20` | ✅ Sign text atlas — `TS101`, `TS102` (`Q63`, `Q65`, `Q68`) |
| `P3-22` | ✅ Shape-only direction signs (`Q66`, `Q67`) |
| `P3-23` | ✅ Stop and give-way lines, `roadmarks.glb` (`Q69`) |
| `P3-26` | ✅ Lamp posts from iB1000 (`Q82`, `Q199`) |
| `P3-17` | 🚫 Signal heads as a merged layer — dropped (`Q77`), removed by `P3-35a`; returned lit as `P3-3e` |
| `P3-7a` | 🚫 Façade survey look — withdrawn with the vision reader (`Q102`); `Q44` and `Q45` ship. Findings in `Q34`, `Q47`, `Q48` |
| `P3-21` | ❌ Road lettering from `DTAD_RD_MARK_ANNO` — no-go (`Q65`): no direction value, needs an authored typeface. Data: 274 rotated-rectangle `MultiPolygon`s, 67 distinct strings (word fragments), sizes on `CT174/51-5(1)F` |

Awaiting the user's review:

- `P3-10` 🟡 Ground surface — terrain merged into the tile primitive, one draw call per tile.
  Second half (land-cover classes from the aerial JPEG) only if flat ground reads dead (`Q18`).
- `P3-7` 🟡 Window-band shader and its `TEXCOORD_0` payload. One commit across both sides
  (hard rule 5).
- `P3-6` 🟡 Hero buildings via `landmarks.json`. HKCEC passed review; Central Plaza shipped,
  unjudged. **Remains:** three not built (Hopewell, Times Square, the government slabs).
- `P3-12` 🟡 Road markings over the ribbon's lane coordinate. `draw_lane_lines` and
  `draw_centre_line` are off (`Q132`, `Q125`).

### `P3-9a` Recognition round 0 ✅

Three HK drivers recognised Wan Chai unaided over the web link; the blocked bridges named `Q19`
next. The web build runs Compatibility and crushes the dark band (`Q76`), so a web round may not
reopen `Q26` or re-price `Q30`/`Q31`. `P3-9` remains the handset test.

### The road after `P3-9a`

| ID | Task |
|---|---|
| `P3-28` | ✅ The carve — `INFRASTRUCTURE` cut to the surveyed span on the listed edges (`Q19`, `Q104`) |
| `P3-29` | ✅ The fence — `fits_car` beside `is_passable`, barrier props at the post-carve fence set (`Q19`) |
| `P3-29a` | ✅ Region-edge closure, `fence.clipped_within_m` (`Q143`) |
| `P3-30` | ✅ `tools/box_extent.py` (`Q104`) |
| `P3-31` | ✅ One cap per stub cluster, through corridors (`Q104`) |
| `P3-32` | ✅ Flank caps out to the paint edge (`Q92`); the carve-wall arm not taken |
| `P3-33` | Level-0 road drawn as the carriageway region (`Q129`): `P3-33a` ✅ record and second implementation · `P3-33b` ✅ stage `region` · `P3-33c` ✅ ribbons on territory rails · `P3-33e` ✅ the battery and the routing price · `P3-33f` open, below |
| `P3-33d` | Superseded by `P3-35e` |
| `P3-34` | ✅ Longitudinal lines from TD's survey (`Q132`): `P3-34a` sheets transcribed · `P3-34b` broken lines, `RM1002` / `RM1003` · `P3-34c` `draw_centre_line` off · `P3-34d` `draw_lane_lines` off |
| `P3-35` | ✅ The ETL after the region (`Q133`): `P3-35a` signal layer removed · `P3-35b` `tools/battery.py` · `P3-35c` region-path test · `P3-35d` `pipeline/drawnroad.py` · `P3-35d5` railings stations · `P3-35e` flanks deleted · `P3-35f` verbatim moves, `config_blocks/` · `P3-35g1` off-grade slide onto the deck · `P3-35g2` `crossings` stage · `P3-35g3` hatching · `P3-35h` `lane_centre` about the drawn road |
| `P3-35g4` | 🚫 Lane count off TD's lane lines — refused: 82% / 75% agreement against a high-80s bar, for ~10 edges (`Q127`) |
| `P3-36` | ✅ Turn arrows stand where TD surveyed them (`Q134`) |
| `P3-37` | ✅ TD's surveyed paint on the decks (`Q134`) |
| `P3-38` | ✅ What lies on the road casts no shadow (`Q135`) |
| `P3-39` | ✅ Street arrows' heights off the drawn road (`Q135`) |
| `P3-40` | ✅ `roadmarks.glb` a mesh per 300 m cell (`Q135`) |
| `P3-41` | ✅ `mong_kok` and `sha_tin` built with deck paint (`Q135`) |
| `P3-42` | ✅ `boxjunctions.glb` and `crossings.glb` per 300 m cell (`Q135`) |

Open:

- `P3-33f` ⬜ The user's drive of the region road. Follow-up: drop the outward-only registration
  push (`Q78`) where a post already stands outside R.
- `P3-33c` left `lane_paint` edges under 3.00 m at 6 → 79 and `paint_clearance` deep boxes at 0 → 7.
- The user's drives of `P3-35h`, `P3-36` and `P3-37` are owed.
- Unowned: `ZIGZAGL` / `ZIGZAGR` as paint; no `RM1002` / `RM1003` side checked against the street.
- Unscheduled: the `barriers` railing's edge-on collapse (`Q104`) — one quad thick; the cure
  roughly doubles the mesh and needs its own budget argument.
- OpenStreetMap is unevaluated and not proposed (ODbL share-alike meets hard rule 7); the user's
  decision, never a default.

### Build `B1` — "One fare"

**Review:** play one fare, start to finish | web build | **Is completing a fare worth doing
twice?** Owed by the user, with the drive under `--debug-view=full`.

| ID | Task |
|---|---|
| `P3-24` | ✅ HUD chassis (`Q79`, `Q80`) |
| `P3-25` | ✅ Wrong-way warning (`Q81`) |
| `P3-43` | ✅ `RoadRouter` (`Q137`) |
| `P3-1a` | ✅ `FareSystem` — TD's tariff on what was driven, the time left as a tip (`Q141`) |
| `P3-5a` | ✅ Minimal fare HUD (`Q142`) |

### Build `B3` — "The streets are alive"

**Review:** drive the `B1` fare again among the streets, by day and at night | web build |
**Harder in a good way, or just annoying?** — and do the near misses pay where a player expects?

Done: `P3-77` ✅ trees from HyD's and LCSD's inventories (`Q171`) · `P3-3e` ✅ the signal heads,
lit by the controller (`Q173`) · `P3-80` ✅ the 成績表 saved as a picture (`Q188`).

Built, something owed (🟡). Each is checked by its verify tool; the row names what is left.

| ID | Task | Owed |
|---|---|---|
| `P3-71` | Parked vehicles from published data — `pipeline/parked.py` → `parked_placements.json` (`Q161`) | The user's drive by day and night; the handset's frame time |
| `P3-72` | The parked roster — `tools/make_parked.py`, `parked.glb` | With `P3-71` |
| `P3-73` | The placer by the hour — `ParkedRoster`, a `MultiMesh` per kind per prop cell, a box body per placement (`Q159`) | With `P3-71` |
| `P3-2a` | Near-miss scoring against parked and moving vehicles (`Q161`, `Q175`) | The user's drive |
| `P3-75` | The parked roster, detailed (`Q166`) | The user's look |
| `P3-76` | The 黃紙's names, a 成績表 and a lifetime record (`Q169`) | The user's look, a whole shift to 交更; no red-light row until `P3-3d` is decided |
| `P3-3` | `TrafficSystem`, built as `P3-3a`–`g` (`Q173`). **Accept:** traffic obeys direction, turn bans and signals; density scales by perf tier | The perf tier (none exists; `P0-3b`); the handset re-take |
| `P3-3a` | Signalled junctions — `pipeline/signals.py` → `signals_plan.json` | — |
| `P3-3b` | Phase controller — `signal_controller.gd`, `signal_plan.tres`, `verify_signals` | — |
| `P3-3c` | The AI cars — `traffic.tres`, `verify_traffic` (`Q214`, `Q219`) | The user's drive |
| `P3-3d` | The player at a red — counted (`ran_red`), neither paid nor docked | The user's call: bonus or penalty |
| `P3-3f` | Cars pass the parked ones (`P3-3f1`), indicators (`P3-3f2`), hazards (`P3-3f3`) | The user's drive |
| `P3-3g` | Traffic by the hour off TD's census (`Q186`, `Q198`) | The user's drive across a shift |
| `P3-4` | The trams — `tramlines.py`, `TramSystem`, the bell (`Q176`) | The user's drive and ears; the handset's cost |
| `P3-8` | Taxis in the traffic by licence (`Q183`); the bus-lane penalty dropped (`Q181`) | Minibus behaviour, the user's to define first; the user's look and drive |
| `P3-78` | Buses and green minibuses on their published routes (`Q182`) | The user's drive |
| `P3-79` | The taxi's own sounds — `tools/make_vehicle_sounds.py`, `taxi_audio.tres` (`Q185`) | The user's ears; the PCK cost |
| `P3-97` | The driving music — `tools/make_bgm.py`, `music.tres`, `DriveMusic`: a bed for each part of the day, layers by the style combo's count, MUSIC options on SOUND (`Q246`) | The user's drive heard; the web build; a handset; the PCK cost |
| `P3-81` | A free drive's REPORT (`Q189`) | The user's look and a real drive ended |
| `P3-82` | The taxi at a die-cast's detail (`Q190`) | The user's look; the headlamp spots |
| `P3-83` | Posts collide — a cylinder per lamp column, sign pole and signal post (`Q191`) | `phys` on the throttle route; the user's drive into each |
| `P3-84` | Detail lines on the vehicles — `tools/vehicle_ink.py` (`Q196`) | The user's pick of the weight; a night frame; the PCK; the handset's frame time |
| `P3-85` | The roster at its die-casts' detail (`Q200`) | The user's look and drive; the handset; the box lorry in moving traffic is the user's call |
| `P3-86` | Street hails and a measured par (`Q203`) | The user's drive |
| `P3-87` | Pressed panels on the vehicles (`Q232`) | The user's pick of the dials |
| `P3-88` | The tram's doors and lamps (`Q234`) | A moving tram seen from the taxi |
| `P3-89` | Stop and stand paint — `pipeline/stopmarks.py`: `RM1048` / `RM1049` boxes, `RM1045` (`Q242`) | The user's look and drive; the handset's frame time |
| `P3-100` | The far shore — `pipeline/backdrop.py`: Kowloon's skyline from iB1000 roof levels as one capped silhouette mesh, its shore and the sea run on to it, drawn past the 400 m far plane by a depth squeeze (`Q249`) | The user's pick of the density; a night look; the handset and the web build; the PCK |
| `P3-99` | Glossy, inked vehicles — crowned panels, the painted sky on paint, black detail lines, and the city's screen line black round everything (`Q248`) | The handset's frame time; the web build |
| `P3-98` | Roadside planters — `pipeline/planters.py`: HyD's planter walls at kerb height, a clumped shrub bed where a ring closes, the walls a collider (`Q247`; the look the user's pick of three) | The user's drive into one; the PCK and the draw |
| `P3-93` | Stop furniture — `pipeline/stops.py`: a flag at each bus and minibus stop, a shelter on two solid posts at each tram stop (`P3-94`, `P3-95`; `Q242`; sizes the user's pick) | The user's drive into a pole and a shelter post; a tram drawn at a shelter |
| `P3-96` | The stop layers' cost (`Q242`: 3 + 6 draws, 2.30 MB of PCK, desktop frame time unmoved, iPhone Air at its 120 fps cap either way) | The user's own drive on the handset; the A13 floor and Android, which need the hardware |
| `P3-92` | Stand signs — `TS324` TAXI STAND, the minibus stands' `TS322` / `TS323` and the pick-up plate `TS3643`, each from the sheet's cell, double-sided (`Q242`) | The user's look |
| `P3-91` | Stop legends — BUS STOP 巴士站 and the taxi drop-off / pick-up lettering, strokes and point-filed (`Q242`; `P3-90` was its spike) | The user's pick of `legend_stroke_m` |

- Where a van belongs has no source (no land use or ground-floor attribute); `P3-71` uses the
  goods bays and podium frontages as the proxy. The Planning Department's land utilisation
  polygons are the fetch if it reads wrong — a schema bump.
- The drawings' `RM1051` / `RM1052` are motorcycle and car / LGV parallel parking places
  (`CT174/51-5(1)F`), undrawn.

### Build `B4` — "It's a game"

**Review:** play a full session, twice | web build | **Do you want another go?**

| ID | Task |
|---|---|
| `P3-44` | ✅ Minimap (`Q136`) |
| `P3-45` | ✅ The harbour on the map and in the world (`Q140`). The Shing Mun channel waits on Sha Tin |
| `P3-46` | ✅ Route line on the minimap (`Q137` reversed) |
| `P3-47` | ✅ The parks painted on the ground (`Q144`) |
| `P3-52` | ✅ The tyre model, shipped as the game's car (`Q152`) |
| `P3-59` | ✅ The car's dials as its systems, `tuning/systems/` (`Q155`) |
| `P3-60` | ✅ The car as a spec sheet, `tuning/cars/` (`Q156`) |
| `P3-64` | ✅ The cel outline (`Q158`); its frame time owed to the handset |
| `P3-66` | ✅ A sign's post casts a shadow, its plates do not (`Q135`) |
| `P3-56` | 🚫 Drift assist as a setting — built and dropped on the user's call (`Q153`) |

Built, something owed (🟡):

| ID | Task | Owed |
|---|---|---|
| `P3-2b` | The style combo — a count, never money (`Q205`) | The user's drive and gap; **the fare combo is not built** |
| `P3-74` | Two modes behind PLAY — 特更 / THE SHIFT 07:00 → 21:00 and 兜風 / FREE MODE (`Q162`, `Q233`) | A full shift and the click-through by the user |
| `P3-5b` | Full HUD — safe areas and the touch layout built (`Q204`, `Q206`, `Q228`). **Accept:** readable one-handed in daylight | The handset drive; the sheet's thumb scroll; the one-handed layout |
| `P3-48` | The fare on the car — roof sign and kerbside door | The user's drive |
| `P3-49` | The skills and the receipt (`Q145`) | The user's drive |
| `P3-50` | Penalties — the tip docked on one impact number (`Q148`) | The user's drive |
| `P3-51` | Jump off a carved ramp and pay the flight (`Q147`); the flyover band built and withdrawn | The user's drive off a ramp |
| `P3-53` | The drift's bars (`Q153`) | The kerb slide at speed; the tap under 30 kph |
| `P3-54` | Real technique works — `skidpad.sh --only=technique` (`Q153`) | The user's call on which failing rows matter; the user's drive |
| `P3-55` | The power-on corner (`Q153`) | The street drive; the value is provisional |
| `P3-57` | Tyre marks and smoke (`Q154`) | The user's look and drive; the handset |
| `P3-58` | Drift sparks off the tracker that pays, no boost (`Q154`) | The user's colour and tier pick; the drive |
| `P3-61` | Stability control's yaw brake (`Q156`) | `turn@off` at 63 kph 8° over the bar; the user's drive |
| `P3-62` | The pace as one scale, `pace.tres` (`Q156`) | The value is the user's drive |
| `P3-63` | The aids no car has (`Q156`) | The game's bars re-read at the settled pace; a limited-slip differential deferred |
| `P3-65` | The outline thins with the car's speed (`Q158`) | The user's drive |
| `P3-67` | Lamps as a `MultiMesh` per 300 m cell (`Q135`) | The user's drive — no lamp seen to appear or vanish |
| `P3-68` | Fences and railings collide as a box per prop (`Q159`) | The user's drive into each |
| `P3-69` | The day runs to night as game time (`Q160`) | The user's night drive; the handset's frame time |
| `P3-70` | The light tail (`Q158`) | The user's look call from the variant sheet; the drive |

Not started:

- `P3-1b` ⬜ Remaining fare types — cross-harbour and long haul. **Accept:** a cross-harbour fare
  works.

### `P3-9` Authenticity test round 1 ⬜

- **Deliverable:** the test run with HK drivers who have not seen the game before — not the
  `P3-9a` cohort, who have learnt the map.
- **Accept:** ≥3 HK drivers navigate Convention Centre → Times Square with the arrow disabled
  (`--hud=off`, `--minimap=off`, `--fares=off` exist for this).
- **Review:** the drivers themselves | a build on a handset | human-judged, by people who are
  not the user.
- **Deps:** all four builds, and `P0-3b` for the handset.

> **Phase 3 gate — go/no-go on full production.** Required: `P3-9` passes; 60fps held on the device
> floor; the user judges the game fun.

---

## After the slice

### Phase 4 — The elevated network

**Goal:** the carriageway `Q13` excluded becomes drivable network rather than scenery.

| ID | Deliverable | Accept |
|---|---|---|
| `P4-1` | ✅ `RoadGraph` serves off-grade edges, open where `clearance.LEVELS` measures (`Q111`) | — |
| `P4-2` | ⬜ Level-aware nearest-edge — by 3D proximity, not plan distance. The ETL half is done (`Q15`) | Beside a deck a query resolves to the deck when it carries height and to the street when not |
| `P4-3` | ⬜ Ramp traversal — grade → deck → grade | No step over 0.15 m at any of the 36 mixed-level nodes, measured. MARSH ROAD `e248`'s 35.8% lip is reachable |
| `P4-4` | ⬜ Traffic across levels — extends `P3-3` | AI obeys direction and turn restrictions on ramps |
| `P4-5` | ⬜ Perf pass with the elevated network resident | 60fps on the device floor. The lever is LOD0's cell and radius; a harsher LOD1 moves 4–8% (`Q120`, `Q122`). Pull-in distance is also `Q26`'s look decision |

- `fence.touchdown_levels` is `[-1, 2]` and is pinned by
  `test_the_open_levels_are_the_measured_levels`. The tunnels stay shut: level −1 publishes no
  clearance (`Q108`), and opening them needs a vertical instrument first.
- What holds off-grade is in `.claude/rules/deck.md` and `Q103`, `Q105`, `Q107`, `Q109`, `Q110`,
  `Q113`.
- Open: attribute deck extent to this edge's carriageway rather than a contiguous run — the rim
  includes the parapet, so ~0.77 m of paint lies on a wall at `e208` (`Q110`). `lanes` cannot say
  a count that varies along an edge (`Q113`).

### Phase 5 — Content, and the modularisation that precedes it

Everything but `P5-8` is built. Refused, with numbers in `Q115`: a road kit, runtime extrusion,
decals, the conformed paint layers as props, reuse across the ETL registrations; a whole-city
mesh (`Q116`).

| ID | Task |
|---|---|
| `P5-1` | ✅ `generated_layer.gd` and `layer_preview.gd` replace the per-layer scripts (`Q115`) |
| `P5-2` | ✅ Signs as a face library + placements (`Q115`) |
| `P5-3` | ✅ Lamps as one prop + placements (`Q115`) |
| `P5-4` | ✅ Arrows as a glyph library + placements (`Q115`) |
| `P5-5` | ✅ Railings, bollards, barriers tiled from one unit per class (`Q115`) |
| `P5-6` | ✅ Roads chunked by tile under `roads/` (`Q120`) |
| `P5-7` | ✅ The region join (`Q116`, `Q120`): `P5-7a` the `Q19` battery on `causeway_bay` · `P5-7b` `tools/join_seam.py` · `P5-7c` `join.reach_m` · `P5-7d` the reach fetched · `P5-7e` the cut, `foreign_edges` · `P5-7f` boundary caps · `P5-7g` `pipeline/join.py` |
| `P5-9` | ✅ Two regions resident: `P5-9a` `resident_budget.py --pair` · `P5-9b` `sync_generated.sh`, `regions.json` · `P5-9c` `region.tscn` + `CityRegions` · `P5-9d` `road_join.gd`, `verify_join.gd` · `P5-9g` drive determinism |
| `P5-9e` | 🚫 Libraries shared across regions — built, measured, reverted: +3 to +11 draw calls on the seam drive. Re-measure if a region list gives a long sightline onto a neighbour's props |
| `P5-9f` | 🟡 The drive across the join — scripted pass; the user's verdict owed |
| `P5-8` | ⬜ **Content** — Causeway Bay, then Central (`Q6`); outline only, after `P3-9`. `Q120`: 200 MB buys 5–15 km² at current fidelity, so which regions ship is a fidelity question first |

### Phase 5b — The asset seam (`Q121`)

A hand-made DCC asset can enter the bundle and be collided, culled and textured by the engine's
own machinery; the merged tile, vertex-colour albedo and procedural façade stay the default.

| ID | Task |
|---|---|
| `P5-10` | ✅ The authored door — `landmarks:` generalised, `verify_authored.gd` (`Q121`) |
| `P5-11` | ✅ Tile identity and channel contract, `pick_building(ray)` (`Q121`) |
| `P5-12` | ✅ Colliders on `-colonly` nodes, `buildings.collision_cell_m` (`Q121`) |
| `P5-13` | ✅ `-occonly` occluder per tile; importer LODs off (`Q121`, `Q122`) |
| `P5-15` | ✅ `verify_road_graph.gd`'s lane-centre check fixed (`Q122`) |
| `P5-16` | ✅ `check.sh` `sidecars` step (`Q122`) |
| `P5-17` | ✅ `buildings.occluder_cell_m` per tier; `[4.0, 4.0]` ships, the far tier's cost is the user's call (`Q122`) |
| `P5-18` | ✅ `tools/resident_budget.py` (`Q122`, `Q120`) |
| `P5-19` | ✅ Box-junction convexity guard (`Q123`) |

`P5-14` ⬜ **Textures as an option on tiles.** Trigger: an artist. `merge` carries a texture when
every input shares the same one; tiles declare a `texture_budget_px` on `P3-20`'s mechanism; the
façade shader gains a gated `albedo_atlas` sampler. **Accept:** sampler off, bundle and frame
byte-identical; with one 1024² atlas `mesh_contract.gd` passes on the declared budget and fails
one pixel over; the atlas footprint quoted against the 128 MB mobile texture budget; `merge`
still refuses two different textures. Owes the inertness proof (`Q96`, `Q117`) and an A/B frame.

Held — not refused, not re-proposed without the trigger:

- A non-convex junction cap (`Q53`). Trigger: the first authored piece that must sit on a cap.
- An `authored_roads:` seam (a node id and a `.glb`). Trigger: an artist.
- Markings as `Decal` nodes (`Q115`). Trigger: a measured need to edit paint by hand, and a
  Mobile-renderer decal test first.
- A landmark LOD tier for HKCEC. Trigger: the mobile tier (`P0-3b`).
- Custom Web export templates with `module_raycast_enabled=yes` (`Q122`). Trigger: a measured
  draw-call problem on the web cut.

### Phase 5c — The collaborator seam (`Q124`)

An artist, a graphics engineer and a Godot developer can each do a first day's work without
running the ETL or rewriting files they did not touch.

| ID | Task |
|---|---|
| `P5-20` | ✅ `sidecars` step walks the authored `.glb.import` files (`Q124`) |
| `P5-21` | ✅ First editor save committed alone; typed node exports migrated (`Q124`, `Q119`) |
| `P5-22` | ✅ `scenes/dev/asset_viewer.tscn`, `--asset=` (`Q124`) |
| `P5-23` | ✅ Vehicle contract as material names (`Q124`) |
| `P5-24` | ✅ `main.gd` wires the HUD its vehicle; no `find_children` (`Q124`) |
| `P5-25` | ✅ `scripts/core/cmdline.gd` (`Q124`) |
| `P5-26` | ✅ `wrong_way.tres`, `street_tracker.tres` (`Q124`, `Q81`) |
| `P5-27` | ✅ Git LFS for `*.glb`, `*.png`, `*.ttf` (`Q124`) |
| `P5-28` | ✅ The exposure anchor un-baked (`Q38`): `P5-28a` `render_cool` · `P5-28b` the `exposure_anchor` global · `P5-28c` colours at reflectance level · `P5-28d` `facade_hue.strength` 3.0 |

Held — not refused, not re-proposed without the trigger:

- The HUD as a `.tscn` (`Q119` priced it). Trigger: a Godot developer iterating the HUD in the
  editor.
- A no-Python onboarding path (a pre-built bundle) — a licensing call, since `LICENSING.md` says
  generated data is regenerated, not redistributed. Trigger: the first collaborator who will not
  run the ETL.
- A Windows path for `check.sh`. Trigger: a Windows contributor.

Refused (`Q124`): feature-folder reorganisation; event-driven input (`Q119`); a listener on the
four `InputRouter` signals.

### Outline only

- **`P3-27` (candidate) — Footway extent and crossing glyphs** (`Q101`). Crossing paint shipped
  as `P3-35g2`. Still undrawn from already-fetched publishers: iB1000 `CartoPedLine PA`, HyD
  `FEAT_TYPE=2` footway, `DTAD_DROP_KERB_LINE`, the look-right / look-left glyphs
  (`RM1135` / `RM1136`). Scope as `P3-18` was: one primitive, one draw call, counters that publish
  both partitions, a `DATA_SOURCES.md` entry per layer read.
- **Phase 6 — Production polish:** settings, save/progression, accessibility, localisation QA.
  `P6-1` ✅ the start menu, pause and credits, pulled forward (`Q146`, `Q164`, `Q165`, `Q229`,
  `Q241`); the handset drive of the reset is owed.
- **Phase 7 — Ship:** free-slice boundary, one-time unlock IAP, store assets, web demo, HK press
  outreach, legal sight-check of landmark depiction.

Phases 6 and 7 are not broken down; the slice will change the assumptions.

---

## Working agreements for agents

Commit style, the checks to run and the doc updates are in the root `CLAUDE.md` and
`CONTRIBUTING.md`. Beyond those:

- If a task's acceptance criteria turn out to be wrong, say so and propose a change rather than
  quietly redefining them.
- Do not start a task whose dependencies are unmet without flagging it.
- Producing the review artifact is the agent's job; answering the verdict question is not.
- Stop at every review point and wait. Machine-checked is never a substitute.
- Look at the screenshots before saying a build is ready to review. A green driver run is not a
  rendered game.
