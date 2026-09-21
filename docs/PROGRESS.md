# Progress

Live state only: what is in flight, what is measured, what is at risk. Update it when a task
changes status, a number is re-measured, or a question opens or closes.

- Task definitions and acceptance → `PLAN.md`.
- Why something is the way it is → `DECISIONS.md`, keyed by the `Q` or task ID.
- What happened when → git.

Keep rows to one line. A row that needs a paragraph belongs in `DECISIONS.md`.

---

## Current status

- **Phase 0, Phase 1:** complete.
- **Phase 2:** two items from its gate, both blocked on hardware, not software — `P2-4`
  (`InputRouter`, built, needs a handset review) and `P2-6` (perf pass). Both wait on `P0-3b`
  (signing identity + the two floor handsets).
- **Phase 3** runs `B2` → `B1` → `B3` → `B4`.
  - `B2` ("it reads as HK") is shipped. `P3-9a` ran: three HK drivers recognised Wan Chai from
    geometry alone, and stopped because the bridges were blocked (`Q19`). `Q19` has since been
    carved and fenced (`P3-28`, `P3-29`), and level 1 is open to driving (`P4-1`, `Q111`).
  - The level-0 road is drawn as the carriageway region (`P3-33a`–`c`, `Q129`) and graded
    (`P3-33e`): the player is unharmed, and the one-lane bar now costs traffic 3,989 ordered pairs
    (`P3-3`'s question). `P3-33f` (the user's drive) is open.
  - `P3-34` (TD's longitudinal lines) and `P3-35` (ETL refactor, crossings, hatching, lane
    centre) are built; `P3-35g4` was measured and refused. `P3-35h`'s user drive is outstanding.
  - `P3-36` stands the arrows where TD surveyed them and `P3-37` paints the decks (`Q134`); the
    user's drive of both is owed.
  - `B1` ("one fare") is in progress: HUD chassis and wrong-way warning built; the fare state
    machine (`P3-1a`) and minimal fare HUD (`P3-5a`) remain. `B3`, `B4`, `P3-9` not started.
- **Phase 4:** `P4-1` built and reviewed; `P4-2`–`P4-5` not started. The 15 tunnels stay shut.
- **Phase 5:** `P5-1`–`P5-7`, `P5-9a`–`g`, `P5-10`–`P5-13`, `P5-15`–`P5-28` built. The runtime
  holds `wan_chai` + `causeway_bay` across a seam; `mong_kok` and `sha_tin` are built for
  measurement only. `P5-8` (content) is outline; `P5-14` not started.
- **Knowingly missing:** no traffic, no tram vehicles, no neon (`P3-3`, `P3-4`, `P3-8`); no night
  rig (`Q26`); no signal heads (`Q77`).

**Driver artefact.** Host: <https://williamchong.itch.io/hong-kong-taxi-q> (public page). The
last cut is `r5` (`build/hk-taxi-q-p39a-r5-itch.zip`, 55,511,080 B); it predates `P3-26` onward,
and the `P3-9a` round cannot be tied to a commit (`P3-9a′`).

Standing rules for any cut (`DECISIONS.md` `P3-9a`, `Q77`):

- One new name per cut, never an overwrite; check the name, not the mtime.
- Re-check "0 console errors" on every cut; `check.sh` cannot see that class.
- Re-export before packing; never pack what a measurement left in `build/web/`.
- Nothing in the repo builds the itch zip — re-pack by hand. The embed needs itch.io's
  "SharedArrayBuffer support" toggle; a missing one fails as `SharedArrayBuffer is not defined`.
- The console's `signs:` count minus `signs.json.triangles` must equal `text_plates × 2`.

### Task board

Legend: ⬜ not started · 🟡 in progress / awaiting review · ✅ done · 🟢 closed by verdict ·
🚫 built, not shipped · ❌ no-go

Phase 0–2

- `P0-1` ✅ Source data granularity — closed `Q2`, `Q3`, `Q5`.
- `P0-2` ✅ Z-value spike — no Z; `ELEVATION` encodes the level (`Q1`).
- `P0-3` ✅ Godot scaffold — macOS / web / Android export verified.
- `P0-3b` ⬜ Mobile device build — needs a signing identity and two handsets; blocks `P2-4`, `P2-6`.
- `P0-4` ✅ ETL scaffold — found the ~304 m datum trap.
- `P0-5` ✅ Grey-box fun test — verdict closed by `Q8`.
- `P0-5a` ✅ Vehicle controller — raycast then; `VehicleBody3D` since `Q50` (`Q84`).
- `P0-5b/c/d` ✅ Circuit, camera, drive test.
- `P1-1` ✅ Source fetching — idempotent, sheets derived from the published index.
- `P1-2` ✅ Building meshes — tiles at two LOD tiers.
- `P1-2t` Superseded by `P3-10`.
- `P1-3` ✅ Road graph (`Q9`, `Q11`, `Q12`).
- `P1-4` ✅ Road surface mesh — opened `Q13`.
- `P1-5` ✅ Fare nodes — opened `Q14`, `Q15`.
- `P1-6` ✅ Export and manifest — byte-reproducible.
- `P1-7` ✅ Godot import — Phase 1 gate passed.
- `P2-1` ✅ `CityStreamer` — reviewed (`Q16`).
- `P2-2` ✅ `RoadGraph` + overlay — reviewed; p99 45 µs against 1 ms.
- `P2-3` ✅ Vehicle on real geometry — reviewed; spawn clearance guard (`Q52`).
- `P2-4` 🟡 `InputRouter` — built; touch is three of five actions (`Q97`); `drift` and `look_back`
  have no touch home (`Q83`); every `touch.tres` value is a first guess. Review needs `P0-3b`.
- `P2-5` ✅ Chase camera — reviewed; yaw law corrected, dials in `camera.tres` (`Q98`).
- `P2-6` ⬜ Performance pass — Phase 2 gate; needs `P0-3b`.
- `P2-7` ✅ Off-grade carriageway on its structure — deck |error| p90 0.095 m (`Q20`, `Q23`).

Phase 3 — Build `B2`

- `P3-11` ✅ Player taxi — reviewed; `tools/make_vehicle.py`, 1,180 triangles.
- `P3-11c` 🟡 Body shader — awaiting review; look is a render + `grep -i "shader error"`.
- `P3-11d` ✅ Lamp circuits — reviewed; circuits are `instance uniform`; `lamp_emission` 1.6.
- `P3-11e` 🟡 Front lamps — awaiting review; night path has no rig to fire on (`Q26`).
- `P3-11f` 🟡 Roof sign — awaiting review; level 0.45, not a daylight dimmer.
- `P3-10` 🟡 Ground surface — awaiting review; buries the carriageway on hill streets (`Q24`).
- `P3-7` 🟡 Window-band shader — awaiting review; draws through `city_facade_clean`.
- `P3-7a` 🚫 Withdrawn (`Q102`) — `W1` (`Q44`) and `W2` (`Q45`) still ship; `W3` gone.
- `P3-6` 🟡 Hero buildings — HKCEC reviewed; Central Plaza unjudged; Hopewell, Times Square and
  the government slabs not built.
- `P3-12` 🟡 Road markings on the ribbon — awaiting review (`Q53`); shader lines now off (`Q132`).
- `P3-13` ✅ Kerbside no-stopping from `NSR` (`Q54`, `Q56`).
- `P3-14` 🟡 Tramway as geometry — awaiting review (`Q58`).
- `P3-15` 🟡 Turn arrows — awaiting review (`Q59`, `Q93`).
- `P3-16` ✅ Traffic signs (`Q64`).
- `P3-17` 🚫 Signal heads — built, dropped (`Q77`); layer removed by `P3-35a`.
- `P3-18` ✅ Yellow box junctions (`Q92`).
- `P3-19` ✅ Pedestrian railings — a panel library since `P5-5` (`Q60`, `Q61`, `Q112`).
- `P3-20` ✅ Sign faces as a texture atlas — `signs_text.png` (`Q68`, `Q70`).
- `P3-21` ❌ Road lettering — no-go under `Q65`; data findings kept in `PLAN.md`.
- `P3-22` ✅ Direction signs (`Q66`, `Q67`).
- `P3-23` ✅ Stop and give-way lines (`Q69`, `Q73`).
- `P3-26` ✅ Lamp posts from iB1000 (`Q82`).
- `P3-9a` 🟢 Recognition round 0 — run and closed; recognised, blocked by bridges (`P3-9a′`).
- `P3-28` ✅ `Q19` carve — 8 edges cut, `e99` at an authored width.
- `P3-29` ✅ `Q19` fence, dressed — car bar 1.80 m; the vertical term refuted.
- `P3-30` ✅ Box-junction extent grader — `tools/box_extent.py` (`Q104`).
- `P3-31` ✅ Median void closed — stub clusters and through corridors (`Q104`). Open: lamps,
  signs and railings do not refuse a foot standing under a level-0 cap.
- `P3-32` 🟡 Paint arm done; carve-wall arm open (wall 1.52–4.32 m inside the carriageway on
  the eight carved edges). Never answered by widening the carve prism.
- `P3-33` 🟡 Level-0 road as the carriageway region (`Q129`) — `a`–`c`, `e` built; `d` superseded by
  `P3-35e`; `f` (user's drive) open.
- `P3-34` ✅ Longitudinal lines from TD's survey (`Q132`), schema 33. Open: no `RM1002`/`RM1003`
  side checked against Street View; zigzags unbuilt.
- `P3-35` ✅ ETL after the region (`Q133`) — `a` signals removed; `b` `tools/battery.py`; `c`
  region-path fixture; `d` `pipeline/drawnroad.py` (signs, lamps, fence, railings on the running
  kerb line; the per-vertex `corridor_*` kerb built and withdrawn); `e` flanks deleted; `f`
  `drawnsurface.py`, `tools/_lib/`, `config_blocks/`; `g1` off-grade slide onto the deck; `g2`
  `crossings.glb` (schema 35); `g3` hatching (`oblique`); `h` `RoadGraph.lane_centre` about the
  drawn road — user's drive outstanding.
- `P3-36` ✅ Arrows stand where TD surveyed them (`Q134`) — `placed_by_slot` 16 / 6; user's drive owed.
- `P3-37` ✅ TD's paint on the decks (`Q134`) — lines 100 of 105 / 4 of 4, arrows 18 of 20 / 4 of 4; user's drive owed.
- `P3-38` ✅ Road paint casts no shadow (`Q135`) — `prims` −191,903, `draws` −10 on the throttle route.
- `P3-39` ✅ Street arrows' heights off the drawn road (`Q135`) — deep burials 31 → 9 / 36 → 21.
- `P3-40` ✅ `roadmarks.glb` in 300 m cells (`Q135`) — 72,356 a pass → 13–17k, +3 to +7 draws.
- `P3-42` ✅ `boxjunctions.glb` / `crossings.glb` in 300 m cells (`Q135`) — start line 20,642 a pass → 9,849, `f_045` 7,469 → 496; +1 / +0 draws. Boxes 9,411 against an 8k bar.
- `P3-41` ✅ Deck paint in `mong_kok` / `sha_tin` (`Q135`) — Sha Tin 33 markings / 324 m where two decks cross, counted, not moved.
- `P3-35g4` 🚫 Lane count hosted on the drawn ribbon — refused: 82% / 75% agreement against a
  high-80s bar, for ten edges. Instrument stays in `width_evidence.py` §2a.
- `P3-27` 🟡 Crossing paint built as `P3-35g2`; footway extent and the look-right / look-left
  glyphs still candidates (`Q101`).

Phase 3 — Builds `B1`, `B3`, `B4`

- `P3-24` ✅ HUD chassis — reviewed (`Q79`, `Q80`). A clean art frame needs both
  `--debug-view=off` and `--hud=off`.
- `P3-25` ✅ Wrong-way warning — reviewed (`Q81`).
- `P3-43` ⬜ `RoadRouter` (`Q137`) — first in `B1`; `P3-1a` and `P3-3` both stand on it.
- `P3-1a`, `P3-5a` ⬜ Fare state machine, minimal fare HUD — what `B1` still needs.
- `P3-3` / `P3-4` / `P3-8` / `P3-2a` ⬜ `B3` — `is_routable` exists (`Q51`); `P3-3` still owes
  adjacency (no `from`/`to` in the graph), the 217 turn restrictions nothing reads, the
  player's `BeamBudget` slot, and whether `is_routable`'s bar is a lane or a vehicle (`P3-33e`).
- `P3-44` ✅ Minimap (`Q136`), one panel with the street plate with one-way arrows — +4 `draws`, +13.4k `prims` over `--minimap=off` (37.7k built naively); whole HUD +15 `draws` (`Q139`); `map:` assertions in `verify_hud`, 12 mutations caught. The user's drive and the web build's clip frame owed.
- `P3-45` ⬜ Harbour and channels on the minimap (`Q140`) — asked for, surveyed, not built.
- `P3-2b` / `P3-1b` / `P3-5b` ⬜ `B4`.
- `P3-9` ⬜ Authenticity round 1 — Phase 3 gate; different drivers from `P3-9a`, on a handset.

Phase 4–5

- `P4-1` ✅ Level 1 open exactly where `clearance.LEVELS` measures — reviewed (`Q111`).
- `P4-2`–`P4-5` ⬜ — `P4-2` owns the rest of `Q15`; `P4-3` MARSH ROAD's lip; `P4-5` streaming
  distances and LOD0's cell.
- `P5-1`–`P5-5` ✅ Scripts merged; signs, lamps, arrows, barriers as props — reviewed (`Q115`).
- `P5-6` ✅ Road chunked by tile — 65 chunks, +13 to +17 draw calls on the route.
- `P5-7` ✅ Region join, `a`–`g` (`Q116`).
- `P5-8` ⬜ Content — outline only; behind `B1`–`B4`, `P3-9`, `Q6`.
- `P5-9` ✅ Two-region runtime, `a`–`d`, `f`, `g`; 🚫 `P5-9e` shared libraries refused (+3 to +11
  draw calls at the seam). Verdict on `P5-9f`'s drive across the line owed.
- `P5-10`–`P5-13` ✅ DCC door, real UV (schema 28), occluders, importer LODs off (`Q121`).
- `P5-14` ⬜ Textures as an option on tiles.
- `P5-15`–`P5-18` ✅ Verifier fix, sidecar ratchet, per-tier occluder policy,
  `tools/resident_budget.py` (`Q122`).
- `P5-19` ✅ Box-junction convexity guard (`Q123`).
- `P5-20`–`P5-27` ✅ Collaborator seam (`Q124`).
- `P5-28a`–`d` ✅ `exposure_anchor` un-baked (schema 31); `facade_hue.strength` 3.0 on the user's
  pick (`Q38`, `Q30`).

---

## Questions

The claim, evidence and refusals are in `DECISIONS.md` under the same ID. A question closes here
and there in the same change.

### Open

- `Q6` Does the region need Central? (after `P3-9`). Deferred.
- `Q13` Nothing ramps between levels in the source (`P4-*`). Level 1 open (`Q111`). Left: the 15
  bores (0 of 15 carry a corridor; `e489` lacks 0.22 m headroom) — needs a vertical instrument,
  not a wider `levels`.
- `Q14` Stands carry operating hours `P1-5` discards (`P3-1`). Deferred — schema bump + parser
  when the fare loop needs it.
- `Q15` Fare nodes snap by plan distance only (`P4-2`). Snap restricted to level 0
  (`off_grade_nearer` counts it). Left: a point genuinely on a deck snaps to the street below.
- `Q19` Level-0 edges with under one lane clear (user). Carved (`P3-28`) and fenced (`P3-29`).
  Left: the building half, a drive of `e99`, `P3-32`'s carve-wall arm.
- `Q21` Should level −1 be drawn at all? (Phase 4). Open — 11 of 30 ends clipped at the region
  boundary.
- `Q22` Off-grade carriageway hangs past its structure (Phase 4). 3.3% (`overhang.py`) after
  `Q107`; no width rule reaches the rest.
- `Q24` The road is a plane and the ground is not (unassigned). Three mechanisms, no shared fix;
  instrumented by `ground_clearance.py`, which mechanism to buy is unassigned.
- `Q30` Shipped façade palette exceeds `ART_DESIGN.md` (user). Widened on purpose at `strength`
  3.0: 35.2% over `C*` 20. `strength` cannot fix it.
- `Q31` The value range has an empty middle. `adjustment_contrast` 1.00 shipped; shadow mass
  still flat — needs a sky-visibility bake. Quote shadow-mass `L*` and sd, never band share.
- `Q35` Per-building material draw gives a salt-and-pepper skyline (`buildings.py`). Candidates:
  spatial hash, block join, accept. Grade from the street.
- `Q39` `wall_sky_tint` is uniform (`Q31`). Free once a sky-visibility term exists; do not lower
  it globally.
- `Q62` Sign facing is derived and ungraded (`signs.py`). Turn-restriction diff grades six plates
  only; measured shut as a grader.
- `Q65` Sign estate scoped to where-to-drive (user). Speed limits (73) on hold.
- `Q66` Deviation board direction is unpublished (`signs.py`). Shipped on an assumption (chevrons
  point away from the post's kerb); ungraded.
- `Q68` 讓 / 停 lettering atlas (`sign_text.py`). `_plate_box`'s correction never reached
  `sign_face_survey.measured()` — the two disagree on 10 of 21 faces.
- `Q79` Street-plate typeface (`hud.gd`). Free HK Kai ships; glyph subset recorded, not taken (≈
  +15% PCK).
- `Q104` Ribbon wider than the cleared corridor (`P3-32`). Carve-wall arm.
- `Q115` Props with placements vs merged meshes (Phase 5). `P5-1`–`P5-6` built; remaining Phase 5
  steps.
- `Q116` Two regions meet at a hard edge (`P5-9`). Built; a stub across the seam joins nothing;
  `P5-9f` verdict owed.
- `Q120` Scaling numbers extrapolated from Wan Chai (`P4-5`). `mong_kok` 35% denser; LOD0's cell +
  radius is the lever; `sha_tin` / `mong_kok` ungraded by the batteries.
- `Q121` Mesh contract vs a DCC workflow (Phase 5b). `P5-14` left. Held: non-convex cap,
  `authored_roads:`, decals, landmark LOD.
- `Q122` Occluder the web cut cannot use (user). Two one-line calls: far-tier occluder (culls
  nothing, 4.63 MB) and a web bundle without occluders.
- `Q126` Stacked arrows on two-way streets. Cause A closed (`lanes_forward`). C (lanes painted
  2.7–2.9 m) and D (tram reserve in the width) each need a decision.
- `Q127` Widths where the ray survey cannot read (user). `Q128` shipped the two survivors. Left:
  the street borrow; consensus of ≥ 2 as the next rung.
- `Q129` A width is the carriageway's (`P3-33`). `P3-33f`; the seam's 0.62 m overlap strip.
- `Q134` Paint stands where TD surveyed it (user). `P3-36`, `P3-37` built; the user's drive owed.
- `Q135` Road paint stays mesh; its frame cost measured (user). `P3-38`–`P3-42` built; the user's drive owed. Open: which deck where two cross (Sha Tin).
- `Q136` Minimap from `RoadGraph`, own off-switch (`P3-44`, built). Heading-up, the merged plate and the one-way arrows are the user's calls. Owed the user: a drive; `span_m`. Owed: the web frame.
- `Q140` Harbour on the minimap (user; `P3-45`). Surveyed, not built: no sea polygon in iB1000, and the waterfront is in three sheets north of the ones held.
- `Q139` One dark housing; dial for the speed, the 咪錶's red LED kept for the fare (user; built with `P3-44`). The user's drive owed.
- `Q138` Racing-game HUD arrangement, five reserved slots (user; built with `P3-44`). The user's drive owed.
- `Q137` A router, no route line (`P3-43`). Design call, not measured; reopens on `P3-9`. Held: arrow to the next junction.

Residue inside closed questions: `e257` paints 2.45 m inside its own bracket and a lane count
cannot vary along an edge (`Q113`, `Q114`); `e333`/`e504` count three and paint two (`Q130`);
single stations where HyD's polygon touches the centreline at a node (`Q131`); 52 RM1001
refusals need coverage-based hosting (`Q118`); MARSH ROAD's 0.65 m deck face needs a node-level
descent pass (`Q90`); 9,779 triangles a run hit `MAX_SUBDIVISIONS` in `clearance` (`Q51`).

### Closed — ID → what holds

- `Q1`–`Q5`, `Q7`–`Q12`, `Q16`–`Q18`, `Q20`, `Q23`, `Q25`–`Q29`, `Q32`–`Q34`, `Q34′`, `Q36`,
  `Q37`, `Q40`, `Q41`, `Q43`–`Q46` — records in `DECISIONS.md`. `Q26` closed on `C`.
- `Q38` — exposure is a Godot global per rig; `bounds:` required per material (`P5-28`).
- `Q42`, `Q48`, `Q47` (survey half) — moot since `Q102`; `Q47`'s `podiums.json` join survives.
- `Q49` — superseded in mechanism by `Q50`.
- `Q50` — `VehicleBody3D` ships; isotropic friction; `brake_force` 40.
- `Q51` — `is_passable` / `is_routable`; `ALONG_M = CELL_M`; width is a lower bound at the cell.
- `Q52` — `verify_spawn.gd` refuses a start line a car does not fit.
- `Q53` — procedural markings over the lane coordinate, no texture.
- `Q54`, `Q56` — kerbside yellow from `NSR`, `painted_vehicle_types: [1, 5]`.
- `Q55` — filler guard rejects repeated colours per texel; disjoint from `Q37`'s axis.
- `Q57` — "unsourceable" was a Road Network v2 fact generalised to the estate.
- `Q58` — `TW` is rails, not centrelines; tramway ships as geometry.
- `Q59`, `Q93`, `Q96` — arrows read as a fraction across the road; branch glyph authored; lane
  snap divides by the real width.
- `Q60`, `Q61`, `Q112` — railings registered not read; three classes; coverage shader; slab.
- `Q63` — textures fail unless a call site declares `texture_budget_px`.
- `Q64`, `Q67` — TD's sheet is authority; `tools/sign_face_survey.py` grades faces.
- `Q69` — transverse marks hosted by transversality; `host_disagreement` is the counter.
- `Q70` — atlas ships as `signs_text.png`, named in the manifest.
- `Q71` — `marking_paint.gdshader` shared; a shader change is every sharing layer's change.
- `Q72` — `faces_against_traffic`; a counter must be reachable, so mutation-check it.
- `Q73` — a layer can pass every check and be in no scene; `verify_city.gd` checks nodes.
- `Q74` — closed by `P5-1`.
- `Q75`, `Q99`, `Q119` — the editor never dropped a setting; configs committed in the writer's
  form, rationale in sidecars, `verify_settings.gd` reads values back.
- `Q76` (signals), `Q77` — signal layer built, dropped, removed (`P3-35a`); returns as a port.
- `Q76` (renderer) — web runs Compatibility and crushes shadows; no knob; name the renderer.
- `Q78` — sign registration is outward-only; railings keep `abs()` deliberately.
- `Q80` — HUD layout: a tap zone may overlap, a thumb may not be occluded; no HUD arrow slot.
- `Q81` — the nose raises the wrong-way sign, velocity may only withhold it; 120° bar.
- `Q82` — lamps from `LPO`; lantern unlit; mesh compression off project-wide.
- `Q83`, `Q97` — two relative thumbs; touch overrides the action map per axis.
- `Q84`–`Q89` — drift dials: graded on dwell, torque decays on time, speed fades at 65/85 kph,
  `drift_rear_grip_scale_at_top` 0.80, low branch latches (0.44 / 41 kph). Values need `P0-3b`.
- `Q90` — touchdowns descend; `touchdown_max_grade_pct` 10.0; `tools/touchdown_error.py`.
- `Q91` — `msaa_3d` 4x, pinned in `check.sh`; mobile unmeasured.
- `Q92` — paint sits on `DrawnSurface`, cut along its creases; never raise `lift_m`.
- `Q94`, `Q95`, `Q114`, `Q128`, `Q130` — width and lanes are measured; floor not multiplier;
  no floor under `lanes`; five width sources; `arrows_unmeasured`.
- `Q98` — exponential camera yaw law, `yaw_response` 6.0.
- `Q100` — Hong Kong only; `hong_kong.yaml` + `pipeline/hongkong.py`.
- `Q101` — crossings / footways re-opened (`P3-27`); TD publishes no coded-value domains.
- `Q102` — vision reader withdrawn on cost; `TEXCOORD_1` survey channel removed (schema 20).
- `Q103`, `Q105`–`Q110` — off-grade ribbon cut to its deck per station and side (`deck_rim_m`,
  `offset_m`); clearance published at levels (0, 1); tools share `overhang.cross_section`;
  `tools/corridor_truth.py` can clear an edge, never condemn one.
- `Q111` — level 1 open; `fence.touchdown_levels` `[-1, 2]`.
- `Q113` — the ribbon no longer shrinks at a ramp touchdown.
- `Q117`, `Q125` — opposed pairs found by geometry; join drawn as geometry from
  `opposed_pairs`; `draw_pair_join` off.
- `Q118`, `Q132` — longitudinal lines from TD's survey only; nothing where TD is silent.
- `Q123` — convexity guard on border quads (`P5-19`).
- `Q124` — collaborator seam built. Refused: feature folders. Held: HUD as a scene.
- `Q126` — see Open (C, D); `lanes_forward` shipped.
- `Q131` — `seam_m` 0.10, kerbed islands read through, no area cap.
- `Q133` — refactor, not rewrite (`P3-35`); OSM unevaluated (hard rule 7).

---

## Risk register

- **Web artefact and product render differently** — Medium. `Q76`: web crushes a third of the
  frame under `L*` 10 against 6.0% on Mobile; cause undiagnosed, no knob. Name the renderer in any
  round's write-up; diagnose before compensating.
- **Novelty does not survive the first session** — Medium. `P3-9a` could not measure it (sessions
  ended on `Q19`). Next round, record how long each driver keeps going. Levers: `P3-2b`, a roster,
  world-embedded challenges.
- **Doesn't read as HK to locals** — High, evidence against. Round 0 recognised Wan Chai. Stays
  High until `P3-9`: different drivers, handset, arrow off.
- **Carriageway occupied by solid geometry** — Medium. `Q19`: carved + fenced; `is_routable` keeps
  AI off, `verify_spawn.gd` guards the start. Left: building half, a drive of `e99`.
- **Building meshes blow the triangle budget** — High. `resident_budget.py`: `mong_kok` 184%,
  `wan_chai` 105% of 300k, LOD0 carrying 84–91%. Lever is LOD0's 1.5 m cell with the LOD0 radius
  (`P4-5`), not the LOD1 ratio. No handset has run it.
- **Perf misses 60 fps on the device floor** — Medium. `P2-6`, needs `P0-3b`.
- **Occluder is dead weight on the web cut** — Medium. `Q122`: stock web templates omit the
  raycast module; +10.3% download for nothing. User's call, one line per bundle.
- **Open network is untrafficked and unfinished** — Medium. `Q111`: MARSH ROAD's 35.8% lip is
  reachable (`P4-3`); streamer tuned without the extra area (`P4-5`).
- **A test depends on the developer's fetched sources** — Low. Only CI sees it. Recipe in
  `CONTRIBUTING.md`: run the suite with `pipeline.fetch.SOURCES_ROOT` at an empty directory. A
  habit, not a gate.
- **Vehicle shader unbinds silently** — Low. `verify_vehicle.gd` holds the binding; nothing
  compiles the shader — render + `grep -i "shader error"`.
- **`sha_tin`: 5 box-junction triangles inside no ring** — Low. `box_extent.py` `unattributed`
  must be 0; a hole in attribution, not a bar to widen (`Q123`).
- **3 road-mark triangles under the road at a ribbon overlap** — Low. `Q125`: worst 0.0151 m. Fix
  is a crease at the overlap switch in `DrawnSurface`; never `lift_m`.
- **`P3-11e` night path is untested** — Low. No night rig (`Q26`). A rig must dim its key light,
  never delete it; owes `sun_glint.gd` an `apply()`.
- **Roster headlamps cap at four cars** — Low. Forward Mobile pairs 8 spots per object;
  `BeamBudget` + `verify_beam_budget.gd`. `P3-3` decides whether the player's slot is reserved.
- **Podium floors measure the treatment band** — Medium. `Q47`: data-only pack; true fill owed.
- **`facade_lab.json` is an uncommitted input** — Low. Gitignored; `facade_survey.py
  --filler-report` reproduces `Q55`; hand-run.
- **TAM too small** — Medium. Hong Kong only (`Q100`); scale by regions behind the IAP boundary.
- **GPLv3 forecloses the App Store** — Medium. Contributions inbound MIT (`CONTRIBUTING.md`); no
  retrofit once an outside contributor declines.
- **Landmark depiction IP** — Low. Untextured massing; legal sight-check before launch
  (`LICENSING.md`).
- **GDScript learning curve** — Low. Complexity lives in Python.

Retired: road data lacks Z (`Q1`); a second city is a YAML file (`Q100`); real geometry isn't fun
(`Q8`); terrain fits no budget (`P3-10`); the car is two boxes (`P3-11`); settings vanish from
`project.godot` (`Q119` — they never did; the `[importer_defaults]` loss of one recurrence is the
one thing that does not explain); authored `.import` sidecars unpinned (`P5-20`); `sha_tin`'s
inverted triangle (`P5-19`); `P3-7a` riders invisible (`Q102`); grade separation reachable and
ungraded (`Q111`).

---

## Metrics

Measured values only, latest only. Bundle size is measured from a PCK, never summed from source
files (`Q16`). Layer counters are read from `etl/out/<region>/*.json`, not from prose — verify
there before quoting. Two values are `wan_chai` / `causeway_bay`.

Budget

| Metric | Target | Latest |
|---|---|---|
| FPS on device floor | 60 | — (`P0-3b`) |
| FPS, Chrome on macOS, 2880×1450 | — | 119, worst frame 9.7 ms (2026-07-31; stale) |
| Draw calls | < 150 | 136–150 on the seam line from `f_045` (`P5-9c`); `P2-6` measures properly |
| Resident triangles, worst camera | < 300k | `wan_chai` 112%, 144% with paint · `causeway_bay` 82%, 90% with paint (2026-09-21, `Q135`) · `sha_tin` 47% · `mong_kok` 184% (`tools/resident_budget.py`); seam camera 73% (`--pair`) |
| Paint layers, throttle route | — | 283,044 `prims` / 18 `draws` before `Q135`; shadows off (`P3-38`) and road marks in cells (`P3-40`) leave road marks 13–17k; boxes + crossings in cells (`P3-42`) 20,642 → 9,849 at the start line, 7,469 → 496 from `f_045`, peak `draws` 102 / 132 |
| Texture memory | < 128 MB | 131,072 px — one 512 x 256 atlas, 47,398 B (`signs_text.png`) |
| Bundle size (PCK) | < 200 MB | 55,955,496 B at `P5-13`; later tasks quoted deltas only — re-export before quoting |
| Boot to drivable (web, warm) | — | 830 ms (2026-07-31; stale) |
| Tab memory (web) | — | 307 MB (2026-07-31; stale) |
| ETL full run, warm cache | — | not re-timed since 27 s / 19 stages; `region` alone 9.4 s |
| Buildings stage peak RSS | — | 657 MB |
| Signs stage peak RSS | — | 514 MB |

Scaling (`Q120`, four regions)

- Tiles: 27.7 KB/building (1.8× spread). Thin layers: ~66 KB/road-km. Terrain: p50 66,432 B per
  building-free 150 m tile. 200 MB buys ~5–15 km² at current fidelity.
- Library meshes are region-invariant, so draw calls are too; only bytes and triangles scale.
- LOD1/LOD0 triangle ratio 0.49 / 0.38 / 0.45 / 0.39.

Bundle, from `etl/out` (schemas: `city.json` 35, `roadgraph.json` 15, `roadsurface.json` 12,
`carriageway_region.json` 4)

| Counter | Latest |
|---|---|
| Road graph | 792 edges, 614 nodes, 217 turn restrictions / 207, 166, 35 |
| Road surface triangles | 92,611 / 31,355 |
| Measured width coverage, level 0 (`Q128`) | 53.5% (393 of 734) / 63.3% (124 of 196) |
| Signs drawn | 873 of 3,276 published, 634 poles, 117 text plates / 285 of 1,009 |
| Lamps drawn | 1,077 of 1,263 candidates, `min_kerb_clearance_m` 0.1701 / 364 of 441 |
| Railings read | 16,954 m of 20,273 m published / 6,356 of 7,169 m |
| Arrows drawn | 741 of 1,365 symbols, `stacked_disagreeing` 18 (slots), `placed_by_slot` 16, `overlapping_drawn` 18 / 158 of 367, 0, 6, 2 |
| Road marks drawn | 2,197 of 2,437 candidates, `host_off_carriageway` 217 / 549 of 594, 37 |
| Deck paint (`P3-37`) | lines 100 of 105 (2,497 m), `stations_off_deck` 12; arrows 18 of 20 / 4 of 4 (175 m), 0; 4 of 4 |
| Crossings drawn | 120 of 121, 762 stripes / 16 of 17, 80 |
| Box junctions | 20 of 20, 14,931 triangles / 4 of 4 |
| Tramway | 126 of 132 rails (7,300 m), 55 beds, `off_gauge_stations` 53 of 1,041, `inverted` 0 |
| Player fence | 14 components, 15 mouths, 5 touchdowns / 3 components, 6 mouths |
| Kerbside restriction published | 33,385 m over 722 edge sides; 96.4% agreement with `DTAD_RST_ZONE_LINE` (pre-region figure) |

Graders (report-only unless a target is shown)

| Metric | Target | Latest |
|---|---|---|
| Deck error, \|error\| p90 vs shipped tiles | ≤ 0.50 m | 0.094 / 0.182 m |
| Off-grade carriageway hanging past its structure (`Q22`) | — | 5.0% / 25.3% `overhang.py` (Causeway Bay's is `Q116`'s far halves); 6.6% `deck_margin.py` (upper bound, not re-run). If the two ever agree suspiciously well, re-measure |
| Off-grade stations under the 3.20 m lane bar | — | 0 (`P3-35g1`) |
| Tunnel ribbon inside its own bore (`Q21`) | none | 0 |
| Paint below the road by > 10 mm, in carriageway | ≤ 0.5% of triangles | passes; boxes deep 0, road marks deep 0 before `Q125`'s join (3 of 24,023 since) |
| Box paint off the drawn carriageway | — | 0.58 m² pooled before `P3-33c`; 1.32 m² at EXPO DRIVE EAST after `P3-35e`. Quote basis (count or area) and `--ray-m` |
| `lane_paint` edges painting a lane under 3.00 m | — | 76 / 18 (`Q131`) |
| Occupancy share at bumper height | `BUILDING` ≤ 1.72%, `INFRA` ≤ 1.60% | 0.214% / 0.560% · 0.309% / 0.338% (`P3-33e`); the corridor gate fails as it always has, 27 / 11 edges under one lane |
| `clearance_reconcile` ratchet | — | 28 / 32 / 8 · 9 / 13 / 4 (all levels), 25 / 27 / 6 · 8 / 11 / 3 at grade; at the pipeline's 0.50 m cell the grader reads 24 / 10 (`P3-33e`) |
| Ground proud of the carriageway (`Q24`) | — | 38 of 734 / 49 of 196 level-0 edges past 0.18 m travel, 10 / 4 over a tenth of the ribbon |
| Railing to-source distance, p50 | — | 0.22 / 0.21 m (`railing_error.py`); `bends` 81 / 24 |
| Sign / lamp `shift_m` p90 | — | signs 0.54 / 0.45 m, lamps 0.93 / 0.26 m (`P3-35d`) |
| Reachability lost to the fence | 0 | 0 / 170 ordered pairs at the car's bar, no detour (`tools/reachability.py`; Causeway Bay's 170 predate the region). At the one-lane bar: 3,989 pairs (2.17%) / 173, `e53` and `e138` carrying Wan Chai's (`P3-33e`) |

Handling (skidpad, `VehicleBody3D`)

- Taxi: 1,180 triangles (604 body, 4 × 144 tyres).
- The drift works 34–86 km/h with no spin at any speed (`Q89`); the tap is dead below design
  speed. Per-dial tables live in `handling.md` and `DECISIONS.md` `Q84`–`Q89`; run
  `tools/skidpad.sh` before and after any change.
- Coast-down to rest: 6.5 s from 31 km/h (`rolling_resistance_mps2` 0.8). Godot's
  `default_linear_damp` 0.1 damps underneath the controller — tune against telemetry.
- The braking falloff curve is unmeasured on `VehicleBody3D`.
- Drag and brake coefficients are measured on `skidpad.tscn`, never `city_drive.tscn` (a 0.14°
  gradient is the size of the quantity under test).
