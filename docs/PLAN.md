# Plan — Vertical Slice

**Scope:** prove three things before committing to full production.

1. The ETL pipeline works on real HK open data.
2. The driving is fun.
3. The city reads as Hong Kong to Hong Kong drivers.

**Out of scope for the slice:** monetisation, store assets, art polish, audio beyond placeholders,
Central, all modes except Arcade and Free Roam.

Task IDs are stable — reference them in commits and in `PROGRESS.md`. Live status lives in
`PROGRESS.md`'s task board, not here. A done task is one line; its record is in `DECISIONS.md`.

---

## Review protocol

Every reviewable unit from Phase 2 onward (the task in Phase 2, the build in Phase 3) carries:

```
Review: <what to look at> | <the command that produces it> | <the verdict question>
```

| Kind | Who says yes | Example |
|---|---|---|
| Machine-checked | `tools/check.sh`, `verify_*.gd`, `pytest` | a tile's mesh agrees with its `aabb` |
| Human-judged | the user, driving or looking | `Q12` — Jaffe Road is eastbound |

- No more than one reviewable unit may pass without a human-judged artifact: two machine-checked
  units in a row may not.
- Review points are hard gates. Work stops until the user has driven the build; the status goes in
  `PROGRESS.md`, what the verdict decided in `DECISIONS.md`.
- ⚠️ Name the verdict question in advance. `Q8`'s drive asked "is this fun?", nobody asked "is the
  car facing the legal direction?", and a transposed spawn basis survived a full drive. A verdict
  is read no wider than the question asked (`P2-5`: comfort was never asked, `Q98`).
- Default route is the web build, per `.claude/skills/run-hk-taxi-q/`. Driver screenshots are the
  progress report, not the verdict. Exceptions: a debug overlay is reviewed under the driver;
  feel-in-the-hand needs the handset.
- ⚠️ A declared dependency graph does not catch a missing *capability* no task owns (`P2-5` needed
  building collision; `B2` needed a taxi model). Check acceptance criteria for that shape.

---

## Phase 0 — Spikes and scaffolding ✅

| ID | Outcome |
|---|---|
| `P0-1` | ✅ 6 LandsD sheets, per-sheet glTF, ~44 MB; building data fully scriptable |
| `P0-2` | ✅ Road Network v2 has no Z, but `ELEVATION` encodes the level; region holds |
| `P0-3` | ✅ Godot 4.7 Mobile project; macOS, web and Android export verified |
| `P0-4` | ✅ `etl/` package, `hong_kong.yaml`, `crs.py` tested against published HK1980 points |
| `P0-5` | ⚠️ Grey-box vehicle passed conditionally — fun not assessable from a grey box (`Q8`) |

### `P0-3b` Mobile device build verification ⬜

- **Deliverable:** a signed development build on both an iOS and an Android floor handset; a real
  reverse-domain bundle identifier replacing the placeholder in `export_presets.cfg`.
- **Accept:** the current scene runs on-device with the FPS counter visible; measured FPS recorded.
- **Deps:** `P0-3`, physical hardware. `Q4` confirmed (A13 / Adreno 618).
- Blocks `P2-4`'s and `P2-6`'s reviews.

---

## Phase 1 — ETL vertical slice ✅

Gate passed: Wan Chai renders in Godot from `city.json`, georeferenced and verified in-engine.

| ID | Outcome |
|---|---|
| `P1-1` | ✅ `fetch.py` — sheets derived from the published index; re-running is a no-op |
| `P1-2` | ✅ `buildings.py` — one draw call per tile, vertex colours, no textures |
| `P1-3` | ✅ `roads.py` → `roadgraph.json`; one-way directions confirmed on the street (`Q12`) |
| `P1-4` | ✅ Ribbon mesh with kerbs and collision; opened `Q13` |
| `P1-5` | ✅ `fares.py` — stands + PUDO → `fares.json`, snapped, bilingual |
| `P1-6` | ✅ `export.py` — `city.json`, one command, byte-reproducible, cross-stage validation |
| `P1-7` | ✅ Godot loads `city.json`; 1 cm agreement, checked headlessly. No `DirAccess` listing |

---

## Phase 2 — Driving the real city

**Goal:** the player drives real Wan Chai at 60fps on the device floor. Review points 1 and 2 are
passed; point 3 is `P2-6`.

### `P2-1` `CityStreamer` ✅

Tile streaming and LOD by camera distance, bands in `.tres`; colliders are an ETL product. Review
closed `Q16` — the exact-weld tier does not ship.

### `P2-2` `RoadGraph` runtime **and debug overlay** ✅

One parse per scene, nearest-edge and lane-centre queries, overlay under the car. Nearest-edge
never returns an off-grade edge (`Q13`).

### `P2-3` `VehicleController` on real geometry ✅

Placed by the lane-centre query; spawn orientation asserted against its edge vector. Drive model
since replaced by `VehicleBody3D` (`Q50`).

### `P2-5` Chase camera ✅

Speed-based FOV and look-back. Review asked only "can you read the road, does the camera stay out
of buildings"; the yaw law was corrected later (`Q98`).

### `P2-7` Put the off-grade carriageway on the structure it belongs to ✅

Deck heights sampled from `INFRASTRUCTURE`; |error| p90 0.095 m against 0.50. All 36 mixed-level
nodes are ramps, none a crossing. Elevated network stays closed to driving. `Q23`. Numbered after
`P2-6` but sequenced before it, because `P2-6` measures the geometry that ships.

### `P2-4` `InputRouter` 🟡 — built, review blocked on `P0-3b`

- **Deliverable:** touch, gamepad and keyboard → one action set. Built (`Q83`/`Q97`): touch is two
  relative thumbs carrying three of five actions.
- **Accept:** all three input paths drive the car; no gameplay script reads raw input.
- **Review:** all three paths | on-device build | machine-checked for coverage; the user says
  whether touch steering is usable at all.
- **Deps:** `P2-3`, `P0-3b`.

### `P2-6` Performance pass to budget ⬜

- **Accept:** 60fps on the device floor while driving real Wan Chai, measured, recorded in
  `PROGRESS.md`. This is review point 3 and the Phase 2 gate.
- **Review:** the same drive on the handset | on-device build | **Does it feel smooth?**
- **Deps:** `P2-1`…`P2-5`, `P2-7`, `P0-3b`.
- **Inherits:** re-measure tile hitching now that instantiation registers a trimesh with Jolt on
  the main thread; re-examine "vehicle blob shadow only" — shadows-off shots looked markedly worse.

---

## Phase 3 — Playable slice

**Goal:** a Wan Chai that reads as Hong Kong to strangers, then a complete arcade loop around it.

Four playable builds run `B2` → `B1` → `B3` → `B4`. ⚠️ Build letters name content, not running
order; renumbering would falsify records in `DECISIONS.md`.

The city comes before the loop on the user's call: `Q8` closed on "the city itself is the fun", so
that bet is tested on strangers first. ⚠️ The cost: "is completing a fare worth doing twice?" is
answered later, on a city already built; if the loop wants a different world, `B2`'s art is spent.
Scoring still comes last, and `P3-2a` still moves up to `B3`.

### Build `B2` — "It reads as Hong Kong" — **runs first**

| ID | State |
|---|---|
| `P3-11` | ✅ Player taxi, generated by `tools/make_vehicle.py`; see below |
| `P3-10` | 🟡 Ground surface — terrain merged into the tile primitive, no texture, one draw call per tile, no z-fight with the carriageway. Awaiting review. Second half (land-cover classes from the aerial JPEG, adds Pillow) only if flat ground reads dead (`Q18`) |
| `P3-7` | 🟡 Window-band shader and its `TEXCOORD_0` payload (height-above-own-base, per-building seed). No windows on roofs or podium faces. Awaiting review |
| `P3-6` | 🟡 Hero buildings (5) via `landmarks.json`, authored or `source_paint`; source geometry excluded, no z-fighting. HKCEC passed review; Central Plaza shipped, unjudged; three not built |
| `P3-7a` | 🚫 Withdrawn at `Q102`; `Q44` and `Q45` ship; see below |
| `P3-12` | 🟡 Road markings, procedural over the ribbon's lane coordinate via `TEXCOORD_1`; no texture, no triangle moved. Awaiting review. `draw_lane_lines` / `draw_centre_line` are off since `Q132`, `Q125` |
| `P3-13` | ✅ Kerbside no-stopping from `NSR`; see below |
| `P3-14` | ✅ Tramway as published geometry — `tram.glb` from `CartoTransLine TW`, plus TD's 19 tram stops as `poi`. Lane space refused on a measurement (18.8% of cross-sections on the ribbon). No collider |
| `P3-15` | ✅ Turn arrows from `DTAD_RD_MARK_SYM_PT` — `arrows.glb`; glyph table transcribed from TD's index plan; the 61 `RM1116`–`RM1119` warning arrows are refused. No collider |
| `P3-16` | ✅ Traffic signs — `signs.glb`, plates on TD's surveyed poles. Position comes from the pole via `GG_NAME` (`DTAD_TS_ABV_PT` is a label layer, 0 of 3,276 on a pole); facing is derived and ungraded (`Q62`); whitelist from TD's `TS` sheets, `signCatalogue.json` cross-check only (`Q59`, `Q64`). `signs.json` `by_code` is the live count. `Q60`, `Q67` |
| `P3-20` | ✅ Sign text — `TS102` GIVE WAY / 讓 and `TS101` STOP / 停 baked from TD's cells into an atlas embedded in `signs.glb` as a second primitive; opaque RGB, polarity derived from the layer colours; ceiling `GeneratedSigns.TEXT_ATLAS_BUDGET_PX`. `Q63`, `Q65`, `Q68` |
| `P3-21` | ❌ Road lettering from `DTAD_RD_MARK_ANNO` — no-go under `Q65`: no direction value, needs an authored typeface. Data findings kept: 274 rotated-rectangle `MultiPolygon`s, 67 distinct strings (word fragments), sizes on `CT174/51-5(1)F` |
| `P3-22` | ✅ Shape-only direction signs `TS414`, `TS735`, `TS615`, `TS589`, no texture; `Q67` then refused orphaned supplementary plates. ⚠️ Chevron direction is a stated assumption (away from the host kerb), `Q62`-class. Bend/narrows warnings `TS401`–`TS418` refused (`Q65`) |
| `P3-17` | 🚫 Signal heads from `DTAD_TRAFFIC_LIGHT_PT` — built, then dropped from the bundle (`Q77`): a dark head asserts "out of service", and a phase plan cannot be made honest (18 of 107 multi-head junctions have an opposable pair). Code and tests remain; re-declaring the `signals:` block restores it. Returns with `P3-3`'s traffic in `B3`. `Q76` |
| `P3-18` | ✅ Yellow box junctions from `DTAD_YL_BOX_POLY` — `boxjunctions.glb`, extent read never derived (`Q54`), visual only, no collider |
| `P3-19` | ✅ Railings from `DTAD_RAILING_LINE` — `railings.glb`, registered onto the drawn kerb within `max_shift_m`; balusters, bollards and barriers as their own classes (`Q61`); never on a kerb `surface.py` hides (`kerb_hidden_m`). No collider; breakaway is `B3`. `Q60` |
| `P3-23` | ✅ Stop and give-way lines (`RM1011`–`RM1013`) — `roadmarks.glb`. ⚠️ Host is picked by transversality, not proximity (nearest-edge is wrong on 44%); `host_disagreement` is the counter, `axis_residual_deg` cannot grade it. `underfill_m` reads the drawn half-width from `roadsurface.json`. `Q69` |
| `P3-26` | ✅ Lamp posts from iB1000 `UtilityPoint` `LPO` — `lamps.glb`; no column in the drawn carriageway (`min_kerb_clearance_m`); arm direction derived and ungraded (`Q62`, `Q72`); dimensions authored; lantern not lit (`Q26`). `Q82` |

- **Deps:** `P1-2`, `P1-7`. Nothing in `B2` reads a fare.
- **Review:** drive Hennessy Road and look around, same viewpoints before and after | web build |
  **Does this read as Wan Chai?**
- ⚠️ `P3-7` is one commit across two sides (hard rule 5).
- ⚠️ Content added after `P3-9a`'s artefact was cut reaches drivers only by re-exporting the web
  build and re-packing the itch zip by hand (`Q53`).

#### `P3-11` — how the taxi gets built

✅ `tools/make_vehicle.py` emits `game/assets/authored/vehicles/taxi.glb` from named proportions;
the `.glb` is committed (authored, CC BY-SA 4.0). The same tool makes the rest of the roster for
`B3`. ⚠️ The wheels must land where the arches are: the `VehicleWheel3D` hardpoints in `taxi.tscn`
are authored, not read from the mesh, so moving the visual car without them silently detunes it.

#### `P3-7a` — how the survey becomes the look

🚫 Withdrawn at `Q102` with the vision reader it consumed; `TEXCOORD_1` on buildings went with it
and `verify_tiles.gd` asserts its absence. `W1` (punched openings as glass, `Q44`) and `W2`
(per-building pane colour, `Q45`) ship, because they run off the hash. `W3`'s `quiet_*` values are
gone: they conditioned on refusal, and with no reader every building refuses. The riders
(`R1`–`R4`, `W4`, ground-band pass, two-tone walls) were never delivered; re-proposing any means
re-proposing the reader first — a cost and dependency decision.

Findings that outlive it:
- `R4` failed its pre-fixed bar: surveyed podium floors × pitch against `podiums.json`, |err| p50
  10.76 m against 2.8. Podium boundaries come from iB1000 `P` blocks only (`Q47`).
- A per-face payload does not survive vertex clustering: mixed-payload corners on 0.88% / 0.62% of
  LOD0 / LOD1 triangles across 22.9% of buildings, so façade data stays per-building.
- Geometry does not predict façade (`Q34`); eligibility never conditions on height.
- iB1000 `BuiltStructurePolygon` / `UtilityPolygon` classes are ingested-ready and cost one config
  block. Storey pitch instruments disagree (2.8 shipped against ~3.3), unreconciled (`Q48`).

#### `P3-13` — how the kerbside restriction gets sourced

✅ `etl/pipeline/kerbside.py` joins `NSR` to the graph as `(edge, side, V-range, kind)`; graded by
`tools/kerbside_error.py` — gross over-paint 240% → 4%. Closed `Q54`.

- Extent rides `COLOR_0.a` (left rail nearside, right rail offside); kind rides `TEXCOORD_1.x` as
  `kerb_near` / `kerb_off`. The codec says what kind of line; alpha says where it applies.
- Refused: whole-`(edge, side)` quantisation — 33% gross error at the best threshold.
- `painted_vehicle_types` is `[1, 5]` (`Q56`); `VT=2/3/4` refused because the codec cannot name the
  class. `TIME_ZONE` 1 is double, 2–5 single.
- ⚠️ Side convention: `surface.mitres` offsets left of travel and `U = 0` is the nearside; asserted
  on a fixture, never reasoned in a comment. Backwards mirrors every line and looks like a road.
- ⚠️ `albedo_linear` is a `flat` varying; the alpha must be a separate non-flat varying.
- ⚠️ Inserting stations moves the ribbon's vertex set, so it owes the `clearance` battery.
- 2,909 m of restriction lands on a kerb the widening hid and cannot be drawn. 9 of 14 taxi stands
  sit inside a genuine restriction.

### `P3-9a` Recognition round 0 — the city, before the game

✅ Run and closed: three HK drivers, free roam over the web link, recognised Wan Chai unaided; the
city was not drivable far, which named `Q19`'s walls next. ⚠️ The web build runs Compatibility, not
Forward Mobile, and crushes the dark band (`Q76`) — a web round may not reopen `Q26` or re-price
`Q30`/`Q31`. It is a keyboard desk test; `P3-9` remains the handset test.

### `Q19` implementation — the carve and the dressed fence

Candidate 3 (carve) on the edges the survey licenses, candidate 2 (dressed fence) where it cannot.
The order is load-bearing: the fence set is measured after the carve.

| ID | What shipped |
|---|---|
| `P3-28` | ✅ The carve — cuts `INFRASTRUCTURE` back to the surveyed span; prism is centreline × surveyed `width_m`, never the drawn floor. The cut face is a constructed retaining wall, because the estate is not watertight (5.38% of edge slots open at source). `e99` is the one exception, carved at its authored 6.40 m. `Q19`, `Q104` |
| `P3-29` | ✅ The fence — `fits_car` beside `is_passable` (`clearance.car_width_m`), and authored barrier props with colliders at the mouths of the post-carve fence set, computed never hand-kept. `e207` needs no exemption (3.25 m). `Q19` |

- ⚠️ The carve reads spans from the published graph (`width_source` measured), never from
  `carriageway_width.json`. It inherits the station-normal trap (`Q78`).
- ⚠️ The source is a surface, not a solid: an uncapped cut is a hole. The barrier collider is the
  physical stop; the predicate only keeps the game from routing there.
- 🔴 Refused: a vertical term in the `clearance:` block — built and withdrawn. It adds 3 ramp
  edges (`e411`, `e522`, `e520`) that `Q23`'s 0.30 m bumper floor exists to suppress and misses
  `e99`; reading the kerb-adjacent run instead fences 222 edges. Do not lower the corridor bar.
- The 0.18–0.30 m band is measured by `tools/ground_clearance.py` `structure_class` (25 level-0
  edges), never pooled with `terrain_class` (`Q57`). It grades and does not gate.

### `Q104` follow-on — the drawn ribbon against what the publishers painted

TD's yellow boxes painted past the drawn kerb are a published witness that the ground is
carriageway. 🔴 Two defects wanting opposite fixes — void between ribbons, and ribbon narrower
than the paint: grade per box, never pooled, and quote the basis (count or area) and `--ray-m`.
Only 5 of 20 boxes ever carried off-road paint.

| ID | What shipped |
|---|---|
| `P3-30` | ✅ `tools/box_extent.py` — per-box off-road paint area, distance past the drawn edge, three-way classification. Shares no code with `boxjunctions.py`; grades, never gates |
| `P3-31` | ✅ One cap per stub cluster (`_stub_clusters`, `_cap_ring`) plus `_through_corridors`; pooled off-road box paint 38.75 → 4.29 m². Priced by `tools/cap_pavement.py` |
| `P3-32` | ✅ Flank caps out to the paint edge, not a width — `carriageway[]`, `offset_m`, `trim_m` byte-identical; pooled 4.29 → 0.93 m². The carve-wall arm (neck to the corridor) not taken. `Q92` |

- At level 0 these are replaced by the region (`P3-33c`); they still serve off-grade edges.
- 🔴 Never answered by widening the carve prism — the invented width is the one that yields.
- ⬜ Open, unscheduled: the `barriers` railing's edge-on collapse (`Q104`) — one quad thick, the
  cure roughly doubles a 460,940-byte mesh; needs its own budget argument.

### `P3-33` The level-0 road drawn as the carriageway region (`Q129`)

The carriageway is drawn as an area and the widening is off at level 0; the ribbon survives as the
carrier of lane coordinates and paint. Levels ±1 keep their ribbons (`Q103`, `Q107`). 🚫 `width_m`
does not move — a territory's span is a share, not kerb-to-kerb (`Q57`).

| Step | State |
|---|---|
| `P3-33a` | ✅ `Q129` recorded, `shapely>=2.1`, `tools/carriageway_region.py` as the second implementation |
| `P3-33b` | ✅ Stage `region` between `carve` and `surface` → `carriageway_region.json`. The seam is a cut in R, not in runs, so `foreign` territories are published. `join_seam.py` checks the areas' seam (`P3-33e`) |
| `P3-33c` | ✅ Level-0 ribbons take their territory's extents as rails; `R − ribbons` drawn cap-class; floors to 0; `lanes_painted` ceiling; `clearance` and `roadmarks` read `corridor_*`. ⚠️ Open: `lane_paint` edges under 3.00 m 6 → 79, `paint_clearance` deep boxes 0 → 7 |
| `P3-33d` | **Superseded by** `P3-35e` (`Q133`) — caps, clusters, corridors and buried kerbs still serve 58 off-grade edges, so the deletion list cannot run as written |
| `P3-33e` | ✅ The battery and the routing price — numbers in `Q129`. The price is 3,989 ordered pairs at the one-lane bar and 0 at the car's; whether `is_routable`'s bar is a lane or a vehicle is `P3-3`'s. As written: first move `carriageway_occupancy.py` onto `corridor_*` (else `clearance_reconcile` fails its ratchet) and add `join_seam.py`'s area check. Then the `Q19` battery rebaselined by region; railings, signs, lamps `shift_m` per class — if it does not collapse toward zero, that is a registration finding; `narrowing.py`, since `e207`, `e595`, `e132`, `e499` are authored. **Graded on:** every table before and after, from a worktree of the commit before `P3-33c` |
| `P3-33f` | ⬜ The user's drive. Follow-up: drop the outward-only registration push (`Q78`) where a post already stands outside R. **Graded on:** the seat |

- **Deps:** `e` after `c`; `f` last.
- 🔴 Refuted, do not re-propose: kerb-line faces where HyD is silent (24 faces, 0.3% of length —
  the linework does not close) and an unclipped R (6.8% orphan, one piece 228 m from its owner).
- ⚠️ About 2% of the network (926 m / 270 m) still draws at an invented `width_m`: a side no kerb
  answers on. Counted, never widened.

### `P3-34` The longitudinal lines from TD's survey (`Q132`)

TD's codes are the truth and where TD is silent nothing is drawn (the user's call). All ✅.

- `P3-34a` ✅ — `Q132` recorded; both index-plan sheets transcribed into `DATA_SOURCES.md`;
  `RM1002`/`RM1003` live in `DTAD_RD_MARK_LINE_C`.
- `P3-34b` ✅ — `roadmarks.py` draws the broken single lines (`RM1103`, `RM1104`) and
  `RM1002`/`RM1003` (`RULEID` 2/3 gives LEFT/RIGHT of the digitised direction); dashes cut
  ETL-side; a longitudinal line is hosted by a road it lies ON. Schema 33. `RM1004` stays refused.
- `P3-34c` ✅ — `draw_centre_line` → 0; nothing inferred replaces it. ⚠️ `lanes_forward`'s centre
  field stays in the codec (`Q118`).
- `P3-34d` ✅ — lane lines the same way, landed with `b`; `draw_lane_lines` → 0. ⚠️ Not `RM1107`
  (lay-by / bus-stop edge line).
- ⚠️ Still unowned: `ZIGZAGL`/`ZIGZAGR` as paint. (`RM1035`–`RM1037` hatching shipped at
  `P3-35g3`.)

### `P3-35` The ETL after the region: one drawn road, fewer doors (`Q133`)

Verdict in `Q133`: no rewrite; the remaining inaccuracy is the model, not the data; every reader
of the drawn road goes through one door. Complete but for `g4`'s refusal.

🚫 Nothing here may touch a recorded deliberate duplication — `carriageway.py` /
`carriageway_margin.py`, `region.py` / `carriageway_region.py`, the four `_register`s (`Q78`,
`Q115`), the two station normals, `_Ribbon`'s scalar fields.

- `P3-35a` ✅ — signal layer removed (the user's call; it returns as a port to library +
  placements, `Q76`/`Q77`, code at the commit before). `city.json` schema 34. ⚠️ `signs.disc`,
  `facing_from_side`, `plate_frame` stay public.
- `P3-35b` ✅ — `tools/battery.py <trigger> --before <root>`: 16 triggers, 16 graders, 7 stage
  reports. Exit code = every grader ran, never that a number moved. ⚠️ Every row must carry
  `{generated}` or `{out_root}` (`test_every_tool_is_pointed_at_its_own_side`).
- `P3-35c` ✅ — `tests/test_surface_on_region.py`: the shipped region path tested end to end off
  the mesh. Two silent fallbacks given counters, `territory_mismatched_edges` and
  `territory_missing_edges`, both 0 / 0. ⚠️ `carriageway[]`-only assertions pass with `exact=`
  off — only a mesh read catches it (`Q106`).
- `P3-35d` ✅ — `pipeline/drawnroad.py`, one reader of the drawn road; signs, lamps, fence and
  railings register to the road's running kerb line (`Ribbon.kerb_at`), read at kerb-ended
  stations. 🚫 `roadsurface.json`'s per-vertex `corridor_*` as the kerb was built and withdrawn:
  signs `shift_m` p90 1.34 → 4.24 m. ⚠️ Costs: signs p99 rises (posts deep in a wide road are
  refused); railings `bends` 32 → 84 / 10 → 27. `_register`'s four bodies are not merged.
- `P3-35e` ✅ — `P3-33d` re-scoped: `_paint_flanks`, `_add_paint_stations` and helpers deleted
  (`surface.py` 5,088 → 4,628). ⚠️ A region-less bundle no longer grows a flank under an
  overhanging box. Caps, clusters, corridors and buried kerbs stay (58 off-grade edges use them).
  `_opposed_gaps` → territory adjacency is out of scope and owes `Q117`/`Q125`'s proofs.
- `P3-35f` ✅ — verbatim moves: `pipeline/report.py::tail_of`, `pipeline/drawnsurface.py`,
  `tools/_lib/{bundle,ribbon,streets}.py`, `pipeline/config_blocks/` (`config.py` 6,544 → 1,153,
  still the one door, re-exports every name). `load_config` refuses any key no parser read
  (`_Read`) — a floor under the per-block checks, not a replacement. 🚫 No schema library.
- `P3-35d5` ✅ — railings: a kerb station within `min_station_gap_m` of a published vertex is
  dropped; `railings._sides` takes the naive offset. 🚫 `surface.boundary` untouched. 🚫 `bends`
  (81 · 24) stays a cost: Douglas-Peucker made it worse (91); the fix is `Q115`'s mitre, deferred.
- `P3-35g1` ✅ — off-grade ribbons slide onto their deck before the cut (`e364` 4.31 → 6.80 m);
  never widen, never centre from the deck's middle (`Q103`), refuse where the deck span exceeds
  the edge's `width_m`. `width_m`, `lanes`, `roadgraph.json` do not move (`Q105`, `Q114`).
- `P3-35g2` ✅ — `crossings` stage: `DTAD_CROSSING_LINE` stripes as surveyed, `crossings.glb`,
  `CITY_SCHEMA` 35, `.claude/rules/crossings.md`. 🚫 Out: `RM1135`/`RM1136` look-right/left
  glyphs; the footway publishers (`P3-27`'s other half).
- `P3-35g3` ✅ — hatching on a third host axis (`oblique`): `RM1037`, and `RM1035`/`RM1036` with
  chevrons told from outline by shape and drawn at the sheet's 900. 🚫 Its population is never
  pooled into `axis_residual_deg`.
- `P3-35g4` 🚫 — a lane count off TD's lane lines hosted on the drawn ribbon: agreement 24% → 79%
  on Wan Chai, 82% · 75% pooled against a bar in the high 80s, for ~10 edges. Refused; the
  instrument stays in `tools/width_evidence.py` §2a (`Q127`). Not an argument to switch
  `draw_lane_lines` on.
- `P3-35h` ✅ — `RoadGraph.lane_centre` is placed about the drawn road (`carriageway_offset_m`),
  the offset not turning with the asker; `verify_road_graph.gd` asserts it. Scripted; the user's
  own drive outstanding. ⚠️ Graded with the overlay's lane marker (`--debug-view=full`).
- `P3-36` ✅ — a turn arrow stands where TD surveyed it (`Q134`), the frame its lane lines are in
  since `Q132`; the lane slot carries only an arrow surveyed over no drawn road (`placed_by_slot`)
  and stays the lane-count instrument. 🔴 "On the road" is the drawn surface, never the host's share.
- `P3-37` ✅ — TD's surveyed paint on the decks (`Q134`): `deck_codes: [A01]` lines (`a`, 100 of
  105 / 4 of 4) and arrows (`b`, 18 of 20 / 4 of 4) hosted among off-grade edges only and stood on
  the host level's `DrawnSurface`; a piece the deck does not cover is refused and counted, never
  floated; level-0 reports byte-identical. `c`: `paint_clearance.py` needed no change. 🚫 `A03` and
  the bores (`Q21`), the inferred join off-grade, deck crossings and boxes, `draw_lane_lines`.
  User's drive owed.
- `P3-38` ✅ — what lies on the road casts no shadow (`Q135`): `GeneratedLayer`'s `casts_shadow`
  key, applied by `layer_preview.gd`. `prims` 906,456 → 714,553 and `draws` 108 → 98 on the
  throttle route; 21 px of an A/B frame. `drive.sh --hide-layers=` is the instrument.
- `P3-39` ✅ — a street arrow's heights are the drawn road's under its own tail and nose, as the
  decks' are (`Q135`); an end over nothing drawn keeps the centreline's. Deeper than 10 mm in the
  carriageway 31 → 9 / 36 → 21 on `paint_clearance --layer arrows`; every other counter inert.
- `P3-40` ✅ — `roadmarks.glb` is a mesh per 300 m plan cell (`road_marks.cell_m`,
  `meshbuild.CellBuilder`, manifest schema 3) so the engine can cull it (`Q135`): 72,356 a pass →
  13–17k for +3 to +7 draws; the cells' union is the uncut mesh. `resident_budget.py` counts the
  paint (Wan Chai 144%). 🚫 One shared piece-placer — `sampled_pieces` already is the shared part.
- `P3-42` ✅ — `boxjunctions.glb` and `crossings.glb` are a mesh per 300 m plan cell too, each on
  its own `cell_m` (manifest schemas 2), a crossing cell named `<kind>_c<i>_r<j>` under the bare
  kind's material (`Q135`). Start line 20,642 a pass → 9,849 (+1 draw); from `f_045` 7,469 → 496
  (+0). ⚠️ The boxes read 9,411 against a bar of 8k set beforehand: one cell holds 7,585 of 14,931.
  The cells' union is the uncut mesh in all four regions; every grader byte-identical.
- `P3-41` ✅ — `mong_kok` and `sha_tin` built with deck paint (18 of 20 / 446 of 521 lines, 23 of
  25 arrows). `A01` never says which structure and the lines carry no Z: `deck.under_another_deck`
  counts paint where two deck levels cross — Sha Tin 33 markings / 324 m, 0 elsewhere. 🚫 No rule
  picks the deck (`Q135`).

- ⚠️ `P3-33d` is superseded by `P3-35e`.
- ⚠️ `hong_kong.yaml` is 73% comment. Moving the prose to sidecars (`Q119`'s precedent) is the
  user's call and not taken: provenance beside the value is what it buys.
- 🚫 OpenStreetMap is unevaluated and not proposed — ODbL share-alike meets hard rule 7. A
  decision for the user, never a default.

### Build `B1` — "One fare" — **runs second**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-24` ✅ | HUD chassis — speed, bilingual street plate, reserved slots, thumb-rest contract | Built; passed review (`Q79`, `Q80`) |
| `P3-25` ✅ | Wrong-way warning — blinking NO ENTRY, top-centre | Built; passed review (`Q81`) |
| `P3-43` | `RoadRouter` — directed-edge search over `RoadGraph`: one-way, the 217 turn restrictions, `is_routable`; a legal profile and a player profile | Agrees with `tools/reachability.py`'s pairwise table on both shipped regions and across the join; one query under 1 ms |
| `P3-1a` | `FareSystem` — hail → carry → deliver/fail state machine. Standard and short hop only | The loop runs end to end and can be failed |
| `P3-5a` | Minimal HUD — destination arrow, timer, meter. Deliberately ugly | Legible; no layout work |

- **Deps:** `P1-5`, `P2-2`, `B2` (by order: the review is played on the city that ships).
- **Review:** play one fare, start to finish | web build | **Is completing a fare worth doing
  twice?**
- Cross-harbour and long-haul are held to `B4`.

#### `P3-43` — the router `B1` and `B3` both stand on

`RoadGraph` is a spatial index and an attribute table: no adjacency, no traversal, and
`turn_restrictions` is only counted (`tools/reachability.py` says so, having needed one). Shared
infrastructure, so its own task, first in `B1` (`Q137`).

- **Consumers:** `P3-1a` — a fare's length and its time allowance are road distance, and
  `GAME_DESIGN.md` already owes a minimum trip for the cross-harbour stands 191 m from the portal;
  `P3-3` — a legal route; `P3-44` — nothing yet (`Q137`).
- `scripts/city/road_router.gd`, reading `RoadGraph`, never inside it. ⚠️ The search state is a
  **directed edge**, not a node: a restriction is `from_edge → via_node → to_edge`, which a node
  search cannot express. `RoadGraph` does not load `from`/`to` today; this task adds that.
- Endpoints are `fares.json`'s published `nearest_edge` / `edge_t` — **no schema bump**.
- Two profiles: traffic obeys everything; the player's may not ("the player may break every
  traffic rule"). Which a fare's par distance uses is `P3-1a`'s call, recorded there.
- ⚠️ A 1.5 km² clip is not strongly connected — `reachability.py`'s largest component is 331 edges
  of 737. "No route inside the clip" is a defined answer (plan distance, flagged), never an assert.
- 🔴 `reachability.py` stays a **second implementation** and `verify_road_graph.gd` diffs the two:
  a divergence is a finding. Do not import one into the other (`Q95`'s arrangement).
- Once per fare and on leaving the path, off the `Hit` `hud.gd` already fetches at 5 Hz. Never
  per frame.

#### `P3-24` — how the HUD gets its chassis

✅ Built. What `P3-5a`/`P3-5b` inherit (`Q80`, `.claude/rules/hud.md`):

- Left is the world, right is the car (`Q138`, mirrored from `Q80`), top is the fare, the middle
  stays empty; every known future component has a graded slot. The destination
  arrow goes in the world, not in a slot.
- Plan the area, do not hold the space: reserved rects (minimap, timer, meter) say where furniture
  goes; a release places what it has. Moving a neighbour is a `.tres` edit.
- ⚠️ `tuning/hud_layout.tres` names HUD slots, `P2-4`'s tap zones and the thumb rests;
  `tools/verify_hud.gd` asserts the HUD clears the rests, and that overlapping a tap zone stays
  legal — a tap zone is not a thumb.
- The bar under the speed reads acceleration (no gearbox, so RPM would repeat the speed).
  Nothing on the HUD is decoration. Flat-shaded panels: white is the city, dark is the car.
- `--hud=off` exists for `P3-9`'s arrow-disabled test first, art frames second.
- First bundled typeface: licence entry and the one uncovered character in `Q79`.

### Build `B3` — "The streets are alive" — **runs third**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-3` | `TrafficSystem` — AI on road-graph splines obeying direction and turn restrictions | Traffic obeys real rules; density scales by perf tier |
| `P3-4` | Trams on Hennessy/Johnston as scripted moving blockers | Unpassable, correctly routed, tram bell audio |
| `P3-8` | Bus-lane penalty + red taxi livery + minibus behaviour | Penalty triggers from the `bus_lane` flag |
| `P3-2a` | Near-miss scoring only — detection plus a live on-screen award | Passing AI traffic inside the threshold at speed awards points, shown live. No style chain, no banking |

- **Deps:** `P2-2`, `B1`. `P3-4` and `P3-8` follow `P3-3`; `P3-2a` follows all three.
- **Review:** drive the `B1` fare again with traffic | web build | **Harder in a good way, or
  just annoying?**
- `P3-2a` is here so the review judges traffic with an upside; prior art Burnout 3 (threshold,
  speed gate and pop are tuned quantities).
- Route on `RoadGraph.is_routable` (`Q51`): `city.json` publishes a clear corridor width per
  station, 24 blocked edges; `ALONG_M` is `CELL_M`. ⚠️ `nearest_edge` deliberately still resolves
  blocked edges, so the player can drive into one (`Q19`'s geometry half is open).
- ⚠️ Owed by `P3-3`: the graph stores no adjacency and reads none of its 217 turn restrictions.

### Build `B4` — "It's a game" — **runs fourth**

| ID | Deliverable | Accept |
|---|---|---|
| `P3-2b` | `ScoreSystem` — base, time bonus, drift/air/speed, the style chain and its banking, the fare combo. Absorbs `P3-2a` | Style points award live, and the chain is losable — a hard crash costs it unbanked |
| `P3-1b` | Remaining fare types — cross-harbour and long haul | Cross-harbour fare works |
| `P3-5b` | Full HUD — bilingual destination callouts, safe areas, one-handed layout | Readable one-handed in daylight |
| `P3-44` ✅ | Minimap — the reserved slot filled from `RoadGraph`: drawn once, moved by a transform; player chevron, destination pip; `--minimap=off` (`Q136`). ⚠️ **Not bound by `B4`'s deps** — needs nothing unbuilt; only the pip waits on `P3-1a` | `verify_hud` projection assertions, mutation-checked; A/B frame and draw-call delta; clipped correctly on the web build; `P3-9` runs with it off. Built; the user's drive and the web frame owed |

- **Deps:** `B1`, `B3`. **Review:** play a full session, twice | web build | **Do you want
  another go?**
- ⚠️ `P3-2b` (`Q50`, `Q85`): `VehicleWheel3D.get_skidinfo()` is a real traction-loss signal
  (1.000 → 0.717 when grip breaks) — wire it when skid smoke / tyre marks are built, not before.
  🔴 `get_rpm()` is road speed re-expressed (no wheel inertia): wheelspin and lockup are not
  available, and a wheel mesh rolls smoothly while smoke pours off it — only looking sees that.

### `P3-9` Authenticity test round 1

- **Deliverable:** the test run with HK drivers who have not seen the game before.
- **Accept:** ≥3 HK drivers navigate Convention Centre → Times Square with the arrow disabled.
- **Review:** the drivers themselves | a build on a handset | human-judged, by people who are
  not the user.
- **Deps:** all four builds, and `P0-3b` for the handset.
- Not a repeat of `P3-9a` (city, keyboard, desk); this tests the game on a handset. Recruit
  different drivers — the `P3-9a` cohort has learnt the map.

> **Phase 3 gate — go/no-go on full production.** Required: `P3-9` passes; 60fps held on the device
> floor; the user judges the game fun.

---

## After the slice

### Phase 4 — The elevated network

**Goal:** the 23.3% of carriageway that `Q13` excluded becomes drivable network rather than
scenery. `P2-7` does the geometry; everything here is about driving.

| ID | Deliverable | Accept |
|---|---|---|
| `P4-1` ✅ | `RoadGraph` serves off-grade edges (`Q111`) | Shipped: open exactly where `clearance.LEVELS` measures — `fence.touchdown_levels: [-1, 2]`; review passed |
| `P4-2` | Level-aware nearest-edge — a query resolves by 3D proximity, not plan distance | Beside an elevated deck a query resolves to the deck when it carries height and to the street when not. ETL half done (`Q15`: fare snap restricted to level 0); what remains is the runtime query and a point that belongs on a deck. Closes the rest of `Q15` |
| `P4-3` | Ramp traversal — grade → deck → grade without leaving the surface | No step over 0.15 m (kerb height) at any of the 36 nodes, measured. MARSH ROAD `e248`'s 35.8% lip is now reachable |
| `P4-4` | Traffic across levels — extends `P3-3` | AI obeys direction and turn restrictions on ramps; density scales by tier |
| `P4-5` | Perf pass — the streamer's bands were tuned without the elevated network | 60fps on the device floor with it resident, at two operating points (`Q120`, `Q122`): the engine bands by `aabb`, holds 21 LOD0 tiles at the worst camera, LOD0 is 84–91% of the resident set — `mong_kok` 184%, `wan_chai` 105% of the 300k budget. The lever is LOD0's cell and radius; 🚫 a harsher LOD1 moves 4–8%. ⚠️ Pull-in distance is also `Q26`'s look decision |

- **Deps:** `P2-7`, `P3-3`. `P4-3` follows `P4-1`. ⚠️ `P3-3` is not started, so the network is
  open with no traffic on it.
- **Review:** drive the Wan Chai Interchange from Gloucester Road onto the deck and back down |
  web build | passed for `P4-1` on the user's drive.
- `P4-1` reverses `P2-2`'s criterion — recorded against `Q13` as a scope change, not a bug fix.
  `verify_road_graph` asserts both halves (no closed level leaks into a query; an open deck is
  served at its own height) and refuses to pass vacuously.
- 🔴 `touchdown_levels` is never `[]`, `[-1]` or `[-1, 1]` —
  `test_the_open_levels_are_the_measured_levels` pins it. Level −1 publishes no clearance
  (`Q108`): a bore has no deck to walk and `e489`'s defect is 0.22 m of headroom, which needs a
  vertical instrument before the tunnels open.
- What holds off-grade, each measured shut in its record:
  - Width and signed offset come from the deck (`Q103`, schema 9); the carriageway publishers'
    2D lines find the street under the deck and are not a source.
  - The drawn ribbon is clamped to the deck rims per station and side (`Q107`), never clamped
    off structure (`Q113`), slid before cut (`P3-35g1`). The rims license paint, not a
    `width_m` (`Q105`).
  - `Q110`: `tools/corridor_truth.py` measures the corridor exactly and can clear an edge, never
    condemn one; no barrier is owed on `e208`, `e306`, `e257`, `e450` (all clear the 1.80 m car
    bar). `e208` and `e306` stay under the 3.20 m lane bar — the router refuses them, the
    player is not fenced out. The two bars are not pooled (`Q57`).
  - ⚠️ A paint clamp is a corridor change: off-grade work owes the four corridor readings and
    the starved runs before and after (`Q109`).
- ⬜ Open: attribute deck extent to this edge's carriageway rather than a contiguous run — the
  rim includes the parapet, so ~0.77 m of paint lies on a wall at `e208` (`Q110`); residual
  overhang 3.3% where the two deck models differ (`Q22`, `Q107`). `lanes` cannot say a count
  that varies along an edge (`Q113`).

### Phase 5 — Content, and the modularisation that precedes it

**Goal:** a second region loads beside the first, and the bundle is built from parts an artist
can author and a second region can reuse.

The thin layers scale linearly with the region (`Q115`); a whole-city mesh is refused on
precision and size (`Q116`). The draw-call budget stays — a `MultiMesh` costs the draw call the
merged glb costs. 🔴 Every step owes an A/B render at one fixed camera, shot twice a side and
`cmp`'d (`Q62`). Refused, with numbers in `Q115`: a road kit, runtime extrusion, decals, the
conformed paint layers as props, reuse across the ETL registrations.

- `P5-1` ✅ — `generated_layer.gd` (one table for the `.glb` layers) and `layer_preview.gd`
  replace nine `generated_*.gd` and nine `*_preview.gd`; bundle byte-identical (`Q115`). ⚠️ A
  consumer lives in `.claude/skills/…/driver.gd`, which no grep of `game/` sees.
- `P5-2` ✅ — signs as a face library + `signs_placements.json`, one `MultiMesh` per library
  mesh; generated per region from the config's faces. 🔴 Draw calls +35, not 22 — the shadow
  passes (`Q115`).
- `P5-3` ✅ — lamps as one 40-triangle prop + `lamps_placements.json`; `lamps.glb` 2,377,500 →
  3,568 B; draw calls 1 → 1. ⚠️ The column's ring turns with the arm (≤ 46.6 mm from the merged
  build). ⚠️ `prims` counts a `MultiMesh`'s base mesh per pass, so it no longer proxies drawn
  triangles on a prop layer.
- `P5-4` ✅ — arrows as a glyph library + `arrows_placements.json` (position, yaw, pitch);
  draw calls +10. 🚫 Lane slot not shipped — an unread channel (`Q54`). ⚠️ The glyph is rigid
  where the merged build sheared it (max 18 mm). Box junctions and stop lines stay merged (`Q92`).
- `P5-5` ✅ — railings, bollards, barriers tiled from one unit per class; `metres_snapped`,
  `joints`, `joint_gap_m`, `bends` published; gaps at bends counted, never closed by stretching
  a panel; `panel_m` is the `.tres` post pitch. Draw calls 3 → 3. The user accepted the wedge at
  a bend; no mitre.
- `P5-6` ✅ — roads chunked by 150 m tile under `roads/<tile>.glb`, caps whole to one tile, one
  `-col` per chunk; `city.json` `road_surface: [{id, file, aabb}]` (schema 27, `roadsurface.json`
  8); union identical to the old mesh, seam gap 0.000 m; graders read through `read_surface`.
  Draw calls +13 to +17 on the throttle route (`Q120`). ⚠️ The road is `CityManifest.road_chunks`,
  not a `generated_layer.gd` row; `drive_harness.gd` holds the chunks under the start line
  synchronously. ⚠️ The 8-light beam budget is now per chunk.
- `P5-7` ✅ — the region join (`Q116`): an edge belongs whole to one region, owned by the region
  holding its travel-start vertex; boundary nodes published by both; caps whole to one side.
  ⚠️ The rectangle still selects sheets and `bounds` do not move (`Q10`).
- `P5-7a` ✅ — the `Q19` battery on `causeway_bay` (`Q120`). No carve list, the user's call:
  `e45` KA NING PATH is a ramp's mass through the path, `e46` a `Q90` touchdown the height model
  did not lift. Fence `[45, 46, 122]` loses 170 of 39,402 pairs — the number a carve must beat.
- `P5-7b` ✅ — `tools/join_seam.py`: pairs two bundles' seam nodes and runs; grades, exits 0.
- `P5-7c` ✅ — `join.reach_m: 133.0`; `load_config` derives neighbours (shared whole edge only;
  overlap refused); `Config.neighbours` / `read_reach` / `read_bounds` / `read_box` /
  `read_extent`; `HeightField.from_meshes` gained `region_low`. `bounds`, `city_offset` and the
  tile grid do not move.
- `P5-7d` ✅ — the reach fetched: Wan Chai's sheets 6 → 8; `test_fetch` pins both lists.
- `P5-7e` ✅ — the cut: runs kept whole across the internal line; non-owner copies ship under a
  top-level `foreign_edges` list with `width_source: authored` and `foreign: <owner>`;
  `source_id` and run ordinal on every edge; `ROADGRAPH_SCHEMA` 12, `CITY_SCHEMA` unmoved; ids
  keep their read ordinal with gaps. ⚠️ The outer clip edge is floored outward up to 0.56 m
  (`Q7`), so ownership falls back to the clip rectangle there, never on an internal line.
  Foreign edges are offered to the kerbside join as tracks and published on nothing.
  `foreign_unmeasured_stations` counts survey stations beyond reach.
- `P5-7f` ✅ — a boundary node's cap admits the foreign mouth at its authored width and is built
  only by the region `roads.Ownership` gives the node; 0 foreign ribbon drawn. An owned far half
  rides in the last column's chunk; the streamer picks by `aabb`, never tile id. ⚠️ Open seam
  gaps: a foreign arm's trim is this region's while its ribbon is the owner's (visible as a dark
  edge at node 224, not a step); `_read_offside` pairs owned edges only.
- `P5-7g` ✅ — `pipeline/join.py` merges two graphs (792 + 207 → 999 edges, 764 nodes, 16 seam
  nodes, 252 turns); `reachability.py --graph-dir` control 0.00%. The reconcile ratchet is
  region-keyed. 🚫 The far half's `clear_width_m` is refused and counted, never read off a
  neighbour's tiles. ⚠️ `deck_error` / `overhang` read worse on Causeway Bay because far halves
  ride over tiles its bundle does not carry. ⚠️ A sync without a headless `--import` renders no
  buildings — the cache, not the bundle.
- `P5-9` ✅ — two regions resident: a bundle per region under `game/assets/generated/<region>/`,
  a `Node3D` per region at the `city_offset` difference, one merged `RoadGraph`. `P5-9e`
  refused; `P5-9f`'s verdict is the user's.
- `P5-9a` ✅ — `tools/resident_budget.py --pair <a> <b>` (and `--at X Z`) through
  `Config.frame_offset`; `driver.gd --spawn-fare=<region>/<id>`. The seam is not over budget
  (73%); the pair's worst camera is Wan Chai's own.
- `P5-9b` ✅ — `sync_generated.sh <region>...` writes one directory per region and
  `generated/regions.json` (schema 1, first listed is the frame; build output, gitignored);
  `generated_regions.gd` is the one place the root is spelled; `check.sh` runs the verify tools
  per region. ⚠️ `landmarks.json`'s `res://assets/generated/` prefix is read as the region's own
  directory (`CityManifest.resolve_asset`; `carriageway_occupancy.py` likewise). ⚠️ Graders'
  `--generated` default is the frame region's directory. ⚠️ macOS Bash 3.2: no associative arrays.
- `P5-9c` ✅ — `region.tscn` + `CityRegions` (`city_regions.gd`), one per region at
  `[1649, 0, 0]`; the streamer takes the eye through `to_local`; the road hold is asked of every
  streamer because translated `bounds_game` overlap ~250 m. 🚫 One streamer over N manifests not
  taken. ⚠️ ~150 draw calls on the line touches `verify_city_streamer`'s budget. ⚠️ A re-sync
  needs a headless `--import` before a drive or the car falls.
- `P5-9d` ✅ — `road_join.gd` ports `join.py` rule for rule; `RoadGraph.shared()` builds over
  `GeneratedRegions.resident()`; `verify_join.gd` diffs against `etl/out/<frame>+<other>/`
  (re-run `python -m pipeline.join` when a region moves). 🔴 `clearance`, `carriageway[]`,
  `fence` and `fares` collide on per-region integer ids: a foreign copy's id aliases the owner's
  merged id, fare identity is `(region_id, id)`, everything goes through `edge_id_in(region, id)`.
  ⚠️ Nothing may cache a `_index` cell key across a build. ⚠️ A fold past two regions drops a
  foreign copy owned by a third.
- `P5-9e` 🚫 — libraries shared across regions: built, measured, reverted. The libraries are not
  identical files (each region ships the variants it stands), and a per-region `MultiMesh` is
  already culled (+0 draw calls with two regions); the fold made each batch span both regions:
  +3 to +11 draw calls and up to +262,000 primitives on the seam drive. ⚠️ Re-measure if a later
  region list gives a long sightline onto a neighbour's props — the argument is culling.
- `P5-9f` ✅ — the drive across the join: `--spawn-fare=wan_chai/f_045 --hold=accelerate@0.5+9.5
  --hold=steer_left@6.0+0.22` crosses seam node 224 with no step, barrier or NO ENTRY. Draw-call
  gate holds at 150 with two streamers. ⚠️ The unsteered drive rings NO ENTRY, correctly (it
  enters westbound one-way `911`). Verdict owed by the user.
- `P5-9g` ✅ — drive determinism: `ChaseCamera.snap_to_target()` after each teleport (not from
  `place_at`); the boot-frame streamer had freed the held chunks. `driver.gd --trace=<file>`.
  `city_drive.tscn` assigns `camera_rig`, `verify_city.gd` fails without it. ⚠️ A route that
  outruns the streaming radius is not held. `DECISIONS.md` `P5-9g`.
- `P5-8` ⬜ — **Content**: Causeway Bay, then Central (`Q6`, deferred until after `P3-9`); full
  vehicle roster, audio pass, night mode. Outline only. Waits on Builds `B1`–`B4`. ⚠️ `Q120`:
  200 MB buys 5–15 km² at current fidelity, so which regions ship is a fidelity question first.

**Order.** Everything but `P5-8` is built; `P5-8` waits on Phase 3's builds.

### Phase 5b — The asset seam (`Q121`)

**Goal:** a hand-made DCC asset can enter the bundle, be told apart in it, and be collided, culled
and textured by the engine's own machinery, while the generated city keeps its one-draw-call tiles.
Measured on Godot 4.7.1: glTF node and mesh `extras` survive import as metadata; custom
`_`-prefixed vertex attributes do not. The scope is the seam, not the style: merged tile,
vertex-colour albedo and procedural facade stay the default.

🔴 Every step owes the inertness proof of `Q96`/`Q117` — name the channels that must be
byte-identical and the one that may move — and an A/B frame at one fixed camera, shot twice a side
and `cmp`'d (`Q62`).

| ID | Deliverable | Accept |
|---|---|---|
| `P5-10` ✅ | The authored door: `landmarks:` generalised (not renamed; `replaces_source_ids` optional for an authored asset), Blender round-trip fixture from `tools/make_dcc_fixture.py`, `verify_authored.gd` in `ALWAYS_TOOLS` — `Q121` | — |
| `P5-11` ✅ | Tile identity and channel contract, `city.json` 27 → 28: `extras` row table, `TEXCOORD_0` a real planar UV, payload and per-building row in `TEXCOORD_1`, `pick_building(ray)`, codec constants tested. ⚠️ The per-vertex along coordinate costs +10.2% PCK, reversible in one line (zero `uvs[:, 0]`), the user's call; `carve` re-stamps it. Per-building nodes and custom attributes refused — `Q121` | — |
| `P5-12` ✅ | Colliders on `-colonly` nodes, none on a render mesh; `buildings.collision_cell_m` 1.5, the finest tier's by value, so wall offset is 0.000 m. ⚠️ A coarser cell was priced and not taken (2 m: facade p90 0.469 m, thin geometry lost). Kerb riser stays in the collider; the carve cuts both primitives; graders read `gltf.read_render` — `Q121` | — |
| `P5-13` ✅ | `-occonly` occluder per tile, occlusion culling on and pinned by `verify_settings.gd`; `meshes/generate_lods = false` in `[importer_defaults]` (−8.6% PCK for 16–30% more primitives; reversing needs the value plus deleting the sidecars) — `Q121`, `Q122` | — |
| `P5-14` | **Textures as an option on tiles** — `merge` carries a texture when every input shares the same one, tiles declare a `texture_budget_px` on `P3-20`'s mechanism, the facade shader gains a gated `albedo_atlas` sampler; procedural windows stay the default. Trigger: an artist | Sampler off: bundle and frame byte-identical. One 1024² atlas: `mesh_contract.gd` passes on the declared budget and fails one pixel over; atlas footprint quoted against the 128 MB mobile texture budget; A/B frame at the `Q27` street; `merge` still refuses two different textures |
| `P5-15` ✅ | `verify_road_graph.gd`'s lane-centre check samples the middle segment's midpoint and asserts `hit.edge_id`; no runtime change. ⚠️ A GDScript mutation must keep every local in use or it tests the linter — `Q122` | — |
| `P5-16` ✅ | `check.sh` `sidecars` step: every generated `*.import` held to `[importer_defaults]`, keys read from `project.godot`, passes on an empty tree — `Q122` | — |
| `P5-17` ✅ | `buildings.occluder_cell_m` is a per-tier list (`null` = none), `city.json` 29 → 30 with `occluder` on the tier row. 🔴 The far-tier occluder culls nothing measured and costs 4.63 MB (Mong Kok) / 3.04 MB (Wan Chai); `[4.0, 4.0]` still ships, `[4.0, null]` and the web cut's `[null, null]` are the user's call. Stock Web templates cannot cull — `Q122` | — |
| `P5-18` ✅ | `tools/resident_budget.py`: bands by plan distance to the tile `aabb`, as `TileStreaming.band_of` does. 🔴 `mong_kok` is 184% of budget and no LOD1 cell (163% at 12 m) or third tier reaches 100% — LOD0 carries 78–91% of the resident set; the lever left is LOD0's 1.5 m cell and radius (`P4-5`, `Q26`). LOD1 stays 4.0 m. Cost side provisional until `P0-3b` — `Q122`, `Q120` | — |
| `P5-19` ✅ | `boxjunctions.border_polygons` drops a non-convex mitre quad, counted in `degenerate_border_segments`. 🔴 Never mask inverted triangles in `FlatBuilder.build` and never widen the sliver bar; `FlatBuilder.polygon`'s fan precondition is pinned in `test_meshbuild.py`, and `_turns_one_way` is a quad rule only — `Q123` | — |

**Held — not refused, and not re-proposed without the trigger:**

- A non-convex junction cap (union boundary, not hull; polygon clipping) — prerequisite for
  anything hand-drawn on a cap (`Q53`). Trigger: the first authored junction piece or box junction
  that must sit on a cap. The opposed-ribbon overlap in the road collider is the same union.
- An `authored_roads:` seam (a node id and a `.glb`; ETL skips that node's cap and arm trims, the
  game places it as a landmark, routing untouched). Trigger: an artist.
- Markings as `Decal` nodes — refused by `Q115` on the Mobile renderer and on cost. Trigger: a
  measured need to edit paint by hand, and a Mobile-renderer decal test first.
- A landmark LOD tier for the 173k-vertex HKCEC. Trigger: the mobile tier (`P0-3b`).
- The occluder as its own streamed unit — refuted by `P5-17`: the far tier culls nothing (`Q122`).
- Custom Web export templates with `module_raycast_enabled=yes`, the only way the web cut culls
  (`Q122`). Trigger: a measured draw-call problem on the web cut.

### Phase 5c — The collaborator seam (`Q124`)

**Goal:** a 3D artist, a graphics engineer and a Godot developer can each do a first day's work
without running the ETL, without reading `DECISIONS.md` first, and without a diff that rewrites
files they did not touch. The scope is the seam, not the style: merged tile, procedural facade and
code-built HUD stay.

🔴 Every step owes `Q119`'s inertness proof: `skidpad.sh` byte-identical at 63.02 and 86.36 kph
entry, the driver run's draw calls per debug view unchanged, and `Q81`'s wrong-way route raising
its sign in a frame `cmp`'d to the before side.

| ID | Deliverable | Accept |
|---|---|---|
| `P5-20` ✅ | `sidecars` step also walks `game/assets/authored/**/*.glb.import`; five sidecars reseeded. ⚠️ Reseed by deleting and re-importing, never by hand-editing — `Q124` | — |
| `P5-21` ✅ | First editor save committed alone (`uid=`, `unique_id=`); ⚠️ one pass is not a fixed point — save twice. 🔴 A typed node export resolves only with `node_paths=PackedStringArray(...)` on the node line; seven exports migrated, the two `input_path` exports stay `NodePath` (an autoload is not in the scene) — `Q124`, `Q119` | — |
| `P5-22` ✅ | `scenes/dev/asset_viewer.tscn` + `scripts/city/asset_viewer.gd`: `--asset=res://…` under `clean_daylight.tscn` with the import hook and a readout; needs no built region; missing file exits 1. ⚠️ The first frame after a re-import may not reproduce (`Q114`, `Q117`) — `Q124` | — |
| `P5-23` ✅ | Vehicle contract as material names: `generated_scene_import.gd::vehicle_body` stamps `UV = (circuit, marker)` from the slot name and merges to one surface; `make_vehicle.py` goes through the same door; a misspelt name is refused by name. ⚠️ Recipe: apply object scale, set the origin — a joined object keeps the first cube's. The shipped `.glb` is still Python's — `Q124` | — |
| `P5-24` ✅ | `scripts/main.gd` wires the HUD its vehicle; `VehicleController.sun` is a typed export per scene; `find_children` has 0 callers under `scripts/`. `DebugHud` keeps its group lookup (an autoload nothing can inject). ⚠️ A HUD-on frame can differ in the speed label alone by render phase — grade with `--hud=off` — `Q124` | — |
| `P5-25` ✅ | `scripts/core/cmdline.gd` (`Cmdline`, statics) replaces `DebugHud`'s parser; `RoadGraph.shared()` declared in `ARCHITECTURE.md` as the singleton that is not an autoload. `check.sh` passes from an empty `game/.godot` — `Q124` | — |
| `P5-26` ✅ | `tuning/wrong_way.tres` and `tuning/street_tracker.tres` with sidecars, no `@export` defaults (`Q80`). 🔴 The two angle bars stay two (`Q81`), ratcheted in `verify_hud.gd`. ⚠️ An invalid profile makes the object inert — `_init` cannot refuse, and `assert` is walked past headless — `Q124` | — |
| `P5-27` ✅ | Git LFS for `*.glb`, `*.png`, `*.ttf`, forward only; CI checkout takes `lfs: true`. ⚠️ A clone without LFS first fails at `verify_vehicle` (pointer files). The history rewrite is the user's call; free quota is 1 GB — quote the tracked total on release — `Q124` | — |
| `P5-28` ✅ | The exposure anchor un-baked, in four steps. ⚠️ Lab chroma does not commute with a linear-light scale, so the look was re-judged, not reproduced (ΔE 1.2–6.0, mostly b*) — `Q38` | — |
| `P5-28a` ✅ | `render_cool` `#949995` → `#939995`, inside its cited 30–60% range; the range was not widened — `Q38`, `Q33` | — |
| `P5-28b` ✅ | `exposure_anchor` global shader parameter, pinned by `verify_settings.gd`, set by `scripts/world/lighting_rig.gd`; `signs.gdshader` reads it behind `apply_exposure` (`lamps.tres` true, signs and signals false); `vertex_albedo.gdshader` replaces the `BaseMaterial3D` branch. ⚠️ `barrier_vertex` must stay a different name from `barriers`; `skidpad.tscn` and the grey box run at the default 1.0 — `Q38` | — |
| `P5-28c` ✅ | Un-bake: config `schema_version` 4 → 5, `city_manifest.gd` 30 → 31, colours at reflectance level with `bounds:` per material, `_check_reflectance` checks luminance against `reflectance` and `reflectance` inside `bounds`; rigs carry `exposure_anchor` 0.52; `facade_chroma.py --shipped` and `frame_stats.py --albedo-l` read it from the rig scene — `Q38` | — |
| `P5-28d` ✅ | `facade_hue.strength` swept 2.0–3.5; the user chose 3.0. Strength is art direction, not survey fidelity — `Q38`, `Q30`, `Q40` | — |

**Held — not refused, and not re-proposed without the trigger:**

- The HUD as a `.tscn` — `Q119` priced it (387 µs against 140 µs, and a second copy of two `.tres`).
  Trigger: a Godot developer iterating the HUD in the editor.
- A no-Python onboarding path (a pre-built bundle or CI artefact) — a licensing call, since
  `LICENSING.md` says generated data is regenerated, not redistributed. Trigger: the first
  collaborator who will not run the ETL.
- A Windows path for `check.sh`. Trigger: a Windows contributor.

**Refused (`Q124`).** Feature-folder reorganisation — it crosses every scene's `ext_resource` paths
for no behaviour. Event-driven input (`Q119`). A listener on the four `InputRouter` signals to give
a grep something to find (`Q72`).

### Outline only — refine once Phase 3 lands

- **`P3-27` (candidate) — Footway extent and crossing glyphs** (`Q101`). Crossing paint shipped as
  `P3-35g2`; still undrawn from already-fetched publishers: iB1000 `CartoPedLine PA` (50.9 km), HyD
  `FEAT_TYPE=2` footway (917 polygons), `DTAD_DROP_KERB_LINE` (738), the look-right / look-left
  glyphs. Also a lead on `carriageway_occupancy.py`'s open failure. Scope as `P3-18` was: one
  primitive, one draw call, counters that publish both partitions, a `DATA_SOURCES.md` entry per
  layer read.
- **Phase 6 — Production polish:** menus, settings, save/progression, accessibility,
  localisation QA.
- **Phase 7 — Ship:** free-slice boundary, one-time unlock IAP, store assets, web demo, HK press
  outreach, legal sight-check of landmark depiction.

Phases 6 and 7 are deliberately not broken down; the slice will change the assumptions.

---

## Working agreements for agents

- Reference the task ID in every commit.
- Update `docs/PROGRESS.md` when a task changes status, and `docs/DECISIONS.md` when a decision or
  open question arises.
- If a task's acceptance criteria turn out to be wrong, say so and propose a change rather than
  quietly redefining them.
- Do not start a task whose dependencies are unmet without flagging it.
- Producing the review artifact is the agent's job; answering the verdict question is not.
- Stop at every review point and wait. "Machine-checked" is never a substitute — the verify tools
  have shipped broken-and-green inside a single commit.
- Look at the screenshots before saying a build is ready to review. A green driver run is not a
  rendered game.
