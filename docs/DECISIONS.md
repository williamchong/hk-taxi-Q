# Decisions

Every standing decision, keyed by the `Q` or task ID the code cites — never by date. `PROGRESS.md`
holds live state and chronology lives in git; this file holds why things are the way they are.

## How to write a record

- A one-line `**Status.**` directly under the heading; the index is rebuilt from it by script.
- No dates, unless the date is the fact (a licence term, a data vintage, a cited user approval).
- No narration. State what is true and what is refused; relate records with
  `**Superseded by**` / `**See.**`.
- One claim per record. It grows only by carrying another distinct ⚠️.
- Do not restate a spec another doc owns (`ART_DESIGN.md` the palette, `ARCHITECTURE.md` the
  contract). Give claim, reason, evidence, link.
- Keep the deciding number. A refusal without its measurement gets re-proposed.

---

## Index

| ID | Decision | Status |
|---|---|---|
| `Q1` | Road Network v2 carries no Z, but `ELEVATION` encodes the level | ✅ Closed · `P0-2` |
| `Q2` `Q3` `Q5` | Building data is fully scriptable | ✅ Closed · `P0-1` |
| `Q2′` `Q3′` | Two façade-probe findings that reuse numbers already taken | ⚠️ ID collision, flagged rather than renumbered · `Q2′` superseded by `Q34` |
| `Q4` | Device floor: A13 (iOS) and Adreno 618 (Android) | ✅ Closed |
| `Q6` | Does the region need Central for the circuit to feel complete? | 🟡 Open, deferred to after `P3-9` · scope |
| `Q7` | Game-space origin is the region's north-west corner | ✅ Closed |
| `Q8` | The city itself is the fun | ✅ Closed · the user's verdict after driving `scenes/dev/city_drive.tscn` |
| `Q9` | Read the geodatabase, not the GML | ✅ Closed · `P1-3` |
| `Q10` | Region-local origin plus a recorded `city_offset` | ✅ Closed |
| `Q11` | Road heights sample the terrain height field | ✅ Closed · `P1-3` |
| `Q12` | The source's one-way directions match the street | ✅ Closed · the user's verdict after flying the road-graph preview |
| `Q13` | All 36 mixed-level nodes are ramps | 🟢 Largely answered · residual is `P4-1`'s |
| `Q14` | Taxi-stand operating-time restrictions are discarded | 🟡 Open, deferred deliberately · `P3-1` |
| `Q15` | Fare nodes snap by plan distance only | 🟡 Open, half fixed · `P4-2` |
| `Q16` | LOD0 does not ship | ✅ Closed · `P2-1` |
| `Q17` | CI runs `tools/check.sh` and cannot check the generated assets | ✅ Closed |
| `Q18` | Ground colour sits under a chroma knee, and the classifier is refused | ✅ Closed · chroma value superseded by `Q36` · `P3-10` |
| `Q19` | Solid geometry stands in the drawn carriageway | 🟢 Structure half carved (`P3-28`) and the car-bar fence built (`P3-29`), on the |
| `Q20` | Deck heights are sampled from `INFRASTRUCTURE` | ✅ Closed · **Owner.** `P2-7` |
| `Q21` | Should level −1 carriageway be drawn at all? | 🟡 Open · **Owner.** Phase 4 |
| `Q22` | Off-grade carriageway hangs past its structure | 🟡 Open · **Owner.** Phase 4 |
| `Q23` | Carriageway width is a property of the station, not of the edge | ✅ Closed · **Owner.** `P2-7` |
| `Q24` | The at-grade road follows the ground | 🟢 Half closed; the other half is `Q19`'s · **Owner.** `roads.py` |
| `Q25` | Ground is decimated once per tier and cut afterwards | ✅ Closed · **Owner.** `P1-2` / `P3-10` |
| `Q26` | Which look ships? | ✅ Closed 2026-08-17 — candidate `C` ships: accurate massing, flat per-building colour, |
| `Q27` | `COLOR_0` is authored sRGB and must be linearised by the consumer | ✅ Closed |
| `Q28` | A per-object seed must be `flat` | ✅ Closed |
| `Q29` | The ground's normals are rebuilt in the fragment stage | ✅ Closed |
| `Q30` | The shipped façade palette is not the one `ART_DESIGN.md` authorises | 🔴 Open, and widened deliberately on 2026-09-08 · **Owner.** `Q26` |
| `Q31` | The city's value range has an empty middle | 🟡 Open, cause measured · **Owner.** `P3-9a` |
| `Q32` | `INFRASTRUCTURE` is *not* the brightest large object in its frame | 🟢 Closed as wrong · **Owner.** `P3-9a` |
| `Q33` | Every authored colour is `material reflectance × exposure_anchor` | ✅ Closed; the mechanism is superseded by `Q38` · **Owner.** `config.py` |
| `Q34` | Material is declared, not implied from height | ✅ Closed · **Owner.** `config.py` |
| `Q34′` | The ring weights are re-derived by a tool, against `Q37`'s survey | ✅ Closed by `tools/ring_weights.py` · **Owner.** `hong_kong.yaml` |
| `Q35` | A per-building material draw gives a salt-and-pepper skyline | 🔴 Open · **Owner.** `buildings.py`, `hong_kong.yaml` |
| `Q36` | Wan Chai's ground is paving, not soil | ✅ Closed · **Owner.** `hong_kong.yaml` |
| `Q37` | 10.0% of the façade survey is atlas filler, not a photograph | ✅ Closed by `tools/facade_survey.py` · **Owner.** `buildings.py`, survey |
| `Q38` | `exposure_anchor` is baked into `COLOR_0` at build time | ✅ Closed 2026-09-08 by `P5-28c` — the exposure left `hong_kong.yaml` and is a Godot |
| `Q39` | `wall_sky_tint` is uniform across the city | 🟡 Open · **Owner.** `Q31` |
| `Q40` | Can façade grammar be surveyed instead of hashed? | ✅ Closed; its consumer is withdrawn by `Q102` (`TEXCOORD_1` removed, schema 20). The |
| `Q41` | A vision reader recovers the grammar the statistic could not | **Superseded by** `Q102` — withdrawn on cost at the user's call, not refuted. |
| `P0-1` | Building data is fully scriptable | ✅ Done |
| `P0-3` | A scaffold is not a signed on-device build | ✅ Done · `P0-3b` ⬜ Not started |
| `P0-4` | Config declares its datum, not just its CRS | ✅ Done |
| `P0-5` | The grey box cleared the handling and could not clear the premise | ⚠️ Passed, conditional |
| `P0-5a` | Custom raycast on `RigidBody3D`, not `VehicleBody3D` | **Superseded by** `Q50` — the shipped car is `VehicleBody3D`, on the user's instruction. |
| `P0-5b/c/d` | Five handling bugs no linter catches | ✅ Done. The raycast-model numbers are superseded by `Q50` (`brake_force` is now in the |
| `P1-1` | The fetcher derives its own sheet list | ✅ Done |
| `P1-2` | Vertex clustering, and meshes are assigned to tiles whole | ✅ Done |
| `P1-3` | Three things the source forced on the road graph | ✅ Done |
| `P1-4` | The road surface is one mesh, capped per level, never merged | ✅ Done. Widths and rails have since moved to `Q95` / `Q129`; the rule `surface` owns |
| `P1-5` | Fare nodes keep the kerbside position | ✅ Done |
| `P1-6` | The manifest names the other documents, and the export stage checks them | ✅ Done |
| `P1-7` | The manifest is the only route to the tiles | ✅ Done · Phase 1 gate passed |
| `P2-1` | The city streams, and LOD is per mesh class | ✅ Done — review passed |
| `P2-2` | Publish the derived width, not the widening rule | ✅ Done — review passed |
| `P2-3` | The start line is queried, not written down | ✅ Done — review passed |
| `P2-5` | Buildings get collision from a mesh name | ✅ Done — review passed |
| `P2-7` | The off-grade carriageway lies on its structure | ✅ Done — review passed |
| `P3-7` | Window bands are procedural, and the storey height was measured | 🟡 Awaiting review |
| `P3-7a` | The task closes at what was judged, and the riders are gated on the look | ✅ Closed as shipped — `W1` (`Q44`), `W2` (`Q45`), `W3` (`Q46`) landed and were accepted. |
| `P3-10` | The ground is a mesh class, and it collides | 🟡 Awaiting review |
| `P3-11` | The taxi is generated, and the chassis generates it | ✅ Passed review 2026-09-06 |
| `P3-6` | Two heroes replace their source meshes, and the contract is the deliverable | 🟡 HKCEC passed the user's review 2026-09-06 · two of five shipped (HKCEC mesh-sourced, |
| `P3-11c` | Gloss is priced per surface, and the gradient is what sells it | 🟡 Awaiting review · **Owner.** `P3-11`. Shipped in `vehicle_body.gdshader`, |
| `P3-11d` | The lamps switch, and that is what finally separates the red lens | ✅ Passed review 2026-09-06 · **Owner.** `P3-11`. In `tools/make_vehicle.py`, |
| `P3-11e` | The front lamps answer to the light, not to the driver | 🟡 Awaiting review · **Owner.** `P3-11`. Night path untested until `Q26`'s rig exists. |
| `P3-11f` | The roof sign lights, and it is the one lens that must not bloom | 🟡 Awaiting review · **Owner.** `P3-11`. |
| `BeamBudget` | the eight spot lights are rationed by distance, not by pair order | ✅ Shipped · **Owner.** `P3-11e` → `P3-3`. |
| `verify_vehicle.gd` | the import and the scene are the half no test could see | ✅ Shipped · **Owner.** `P3-11c`–`P3-11e` → `P3-3`. |
| `Q42` | The reader answers seven questions nobody consumes | 🚫 Moot — **Superseded by** `Q102`: the vision reader and `TEXCOORD_1` are removed; a |
| `Q43` | `glazed` is materiality; `fenestrated` is geometry | ✅ Closed — the split stays after `Q102`; re-merging re-opens the defect (grid zeroed |
| `Q44` | A punched opening is glass, not a black hole | ✅ Closed — ships on the hash path (`Q102`); user accepted 2026-08-09. |
| `Q45` | One pane palette across the city reads as wallpaper | ✅ Closed — ships on the hash path (`Q102`); user accepted 2026-08-09. |
| `Q46` | A grammar refusal draws a quiet tier, not invented fenestration | 🚫 **Superseded by** `Q102` — the five `quiet_*` uniforms were deleted with the reader. |
| `Q47` | A committed verdict is right about the tower, wrong about the ground band | 🟡 Data half survives `Q102`; survey half and the premise are moot (nothing commits a |
| `Q48` | A contrast ratio measures banding where an `L*` profile could not | 🟡 Open as a candidate — nothing built, nothing scheduled · **Owner.** `P3-7a` |
| `Q49` | A tyre spends one budget, and the handbrake that follows spins the car | Superseded by `Q50` (the raycast model and its friction ellipse are deleted) · findings |
| `Q50` | The shipped car is Godot's `VehicleBody3D`, and `P0-5a` was right | ✅ Shipped 2026-08-18 on the user's explicit instruction · **Owner.** `P0-5a` → `B4` |
| `P3-9a` | The build is threaded, so the host is not a free choice | 🟡 Open — build cut and verified; drivers not yet run |
| `Q51` | Traffic is never sent down an edge a car cannot fit through | ✅ Closed · **Owner.** `P3-3` · 🔴 `MAX_SUBDIVISIONS` smear still owed |
| `Q52` | The start line says what it is standing in, and the check is what refuses | ✅ Closed 2026-08-18 · **Owner.** `P2-3` |
| `Q53` | Markings are drawn, arrows are not, and the difference is data | ✅ Closed 2026-08-19 · **Owner.** `P3-12` · scope amended by `Q57`, `Q58`, `Q59` |
| `Q54` | The kerbside yellow is invented, and the layer that would source it was read past | ✅ Closed by `P3-13`, 2026-08-19 · vehicle-type scope amended by `Q56` |
| `Q55` | The filler guard reads greyness, and the placeholder panels are coloured | ✅ Closed 2026-08-21 · **Owner.** `tools/facade_survey.py` |
| `Q56` | `VEHICLE_TYPE = 5` is painted, and the way to know was a second dataset | ✅ Closed 2026-08-20 · **Owner.** `pipeline/kerbside.py` config, |
| `Q57` | The estate publishes the markings, the width and the tram | Closed as a survey (nothing built, nothing fetched) · Owner `DATA_SOURCES.md` |
| `Q58` | The published tramway is rails, not centrelines, and it is not on the carriageway | Closed — `P3-14` ships `tram.glb` · Owner `pipeline/tramway.py` |
| `Q59` | The arrows are published, and lane space is the answer | Closed by `P3-15` · Owner `pipeline/arrows.py`, `hong_kong.yaml` `arrows:` |
| `P3-16` / `P3-17` | Signs and signal heads ship as sourced geometry, scope-limited | Closed — `P3-16` shipped; `P3-17` was built, then removed (`Q77`, `Q133`) |
| `P3-16` | Signs ship where the poles are, because the sign layer is a drawing | Closed — `signs.glb` shipped; face table amended by `Q64`; live counts in `signs.json` |
| `P3-18` | Box junctions ship as read polygons | Closed — `boxjunctions.glb` shipped; height join replaced by `Q92` |
| `Q60` | The railings are published, their vocabulary is not, and the position is registered | Closed by `P3-19`, which ships `railings.glb` |
| `Q61` | The fence is coverage-masked, and the layer draws three classes | Closed by `P3-19`'s follow-up |
| `Q64` | The sign table took a sibling project's description over the publisher's sheet | Closed — face table corrected |
| `Q63` | The bundle carries no undeclared image | Closed, on the user's call — contract amended narrowly |
| `Q65` | The sign estate is scoped to what tells the player where to drive | Closed, on the user's instruction |
| `Q66` | A deviation board's direction is derived, because nobody publishes it | Closed — shipped on a stated, ungraded assumption (`Q62`-class) |
| `Q62` | The turn-restriction diff cannot grade the sign facing | Open on the facing (derived, ungraded); the diff shipped as a report-only counter. |
| `Q67` | Sign faces are graded against TD's sheet by an instrument, not by eye | Closed; four glyph-weight rows remain recorded, not fixed. |
| `Q68` | Sign lettering is read off the drawing into one opaque atlas | Closed (`P3-20`); two debts open — the survey's plate box and the pole standoff. |
| `Q69` | A stop line's host is the road it crosses, not the road it is nearest | Closed (`P3-23`). Height source superseded by `Q92`. |
| `Q70` | Everything under `game/assets/generated/` is named by the manifest | Closed. |
| `Q71` | One paint shader, three materials | Closed. The shader is `game/assets/shaders/marking_paint.gdshader`. |
| `Q72` | A NO ENTRY faces the traffic it forbids | Closed. The facing stays ungraded (`Q62`). |
| `Q73` | A layer can pass every check and be in no scene | Closed; the blind spot is closed by `Q115`'s layer table. |
| `Q74` | The preview scripts and loaders were merged | Closed by `P5-1` (`Q115`). |
| `Q75` | A setting that is no longer set cannot fail | Closed. The grep-count guard is superseded by `Q119` (`verify_settings.gd`). |
| `Q76` | The web build runs Compatibility; the product runs Forward Mobile | Closed, as a decision to proceed with the limitation recorded. |
| `P3-17` / `Q76` | Signal heads: a vocabulary nothing publishes, one head per assembly | Removed — dropped from the bundle by `Q77`, code deleted by `P3-35a` (`Q133`). What a |
| `Q77` | A dark signal asserts "out of service", and a lit one cannot be derived | Closed — layer dropped on the user's instruction; code since removed (`P3-35a`, |
| `Q78` | Sign registration is a one-way correction | Closed. `signs.json` schema 3 → 4. |
| `Q79` | The street plate's typeface: Free HK Kai, shipped whole | Closed (`P3-24`). Full font as an authored asset, on the user's call over an |
| `Q80` | HUD layout: a touch zone is not a thumb | Closed — `P3-24` passed the user's review 2026-09-06. |
| `Q81` | The wrong-way sign: an interrupt, and the nose decides | Closed — `P3-25` passed the user's review 2026-09-06. |
| `Q82` | Lamp posts: a published vocabulary, an unlit lantern, reachable counters | Closed (`P3-26`). Night mode refused as a justification; the layer ships for the |
| `Q83` | Touch scheme: two thumbs, both axes each | Decided 2026-08-27 on the user's instruction. Owner `P2-4` → `ARCHITECTURE.md` |
| `Q84` | The drift "cliff" was the sweep grid; the grip dial is graded on dwell | Closed. Method stands; every peak and dwell figure is superseded by `Q86`–`Q89`. |
| `Q85` | `VehicleWheel3D` simulates no wheel spin; the drift is assisted with a yaw torque | Closed. Corrects `PLAN.md` `B4`, `Q49`, `Q50`, `Q84`. The constant-torque values are |
| `Q86` | The yaw torque decays on time so a tap gets the kick | Closed. Extends `Q85`. The 63 km/h figures are superseded by `Q89`; values are desk |
| `Q87` | The yaw assist fades out with speed | Closed. Extends `Q86`; its open half (the grip cut) is closed by `Q88`. |
| `Q88` | The grip cut tapers with speed | Closed. Closes `Q87`'s open half; its open bottom is closed by `Q89`. 0.80 is a desk |
| `Q89` | The low end deepens the cut, and latches it | Closed. Closes `Q88`'s open bottom. Holds the current design-speed figures; `Q84` and |
| `Q90` | Every hole in the structure is a touchdown; the sampler descends instead of clamping | ✅ Closed, one named residue (node 269) · **Owner.** `pipeline/roads.py::_descend` |
| `Q91` | Thin markings were lost to the pixel grid; MSAA 4x | ✅ Closed · **Owner.** `game/project.godot`, `game/tools/verify_settings.gd` |
| `Q92` | Markings stand on the drawn road, not a model of it | ✅ Closed. `pipeline/drawnsurface.py::DrawnSurface` answers a point query over the |
| `Q93` | The turn-arrow glyph: head and stem measured off TD's sheet, branch authored | ✅ Closed. `pipeline/arrows.py`'s glyph, `config.Arrows`' proportions. |
| `Q94` | Two arrows in one lane: the lane count was invented, and the arrows are a source for it | 🟢 Closed, residue carried by later records: the `floored` source was replaced by |
| `Q95` | The authored carriageway width was outside TPDM's range; `width_m` is now measured | ✅ Closed — width assigned and the widening made a floor on the user's call, |
| `Q96` | The arrows' lane snap divides by the measured carriageway | Closed. Placement half superseded by `Q134`; the snap is the instrument. |
| `P3-9a′` | Round 0: the city is recognised, and it was not drivable far | Closed. Three HK drivers over the web link. |
| `Q97` | Touch drives on three of five actions | Closed on the user's instruction ("basic touch control support, dont support drifting |
| `Q98` | The chase camera's yaw is exponential, and its tuning is data | Closed. |
| `Q99` | An editor save stripped `project.godot` and a `.tres` | Closed. The comment-presence guard is superseded by `Q119` (rationale lives in a |
| `Q100` | Hong Kong is the only city; its config is the single source of truth | Closed, on the user's instruction. |
| `Q101` | Data-availability refusals re-read against the grown estate | Closed. Rows as recorded at closing; check `PLAN.md` for what has since been taken. |
| `Q102` | The vision façade reader is withdrawn on cost, and `TEXCOORD_1` goes with it | Closed, the user's call. Withdrawn, not refuted: `Q41`'s reader passed validation and |
| `Q103` | The off-grade network is drivable, and the ribbon is drawn on its deck | Half answered. Tunnel widths and deck-sourced flyover ribbons shipped |
| `Q104` | The cut face had no back, and the ribbon is drawn wider than the corridor | 🟡 Partly open — back face, stub clusters (`P3-31`), through corridors and box flanks |
| `Q105` | The asymmetric ribbon is priced, and it buys paint rather than width | Closed — report-only pricing; built by `Q107`, figures re-measured by `Q106`. |
| `Q106` | Four instruments measured a ribbon that is not drawn | Closed — tools read the drawn offset; per-station form superseded by `Q107`. |
| `Q107` | The off-grade ribbon is cut to its own deck, per station and per side | Closed — shipped; three residuals open. `Q113` later fixed `e208` being clamped to a |
| `Q108` | The off-grade network publishes a clearance | Closed — `clearance.LEVELS = (0, 1)`; level −1 refused. |
| `Q109` | The four blocked bridges, re-read on the ribbon that is drawn | Closed — report-only; its open fence question is answered by `Q110`. |
| `Q110` | The corridor measured exactly, and the disagreement `Q109` left open | Closed — report-only; no barrier owed on any off-grade edge. `Q113` later moved the |
| `Q111` | The elevated network opens, exactly where it is measured | Closed — shipped; human review passed 2026-09-06. A scope change against `Q13`, not a |
| `Q112` | The fence is one quad thick and disappears edge-on | Closed — the barrier family is a slab with a per-class `thickness_m`. |
| `Q113` | The ramp's ribbon shrinks at the touchdown, and paints a 1.57 m lane | Closed — fixed; the lane-count half it left open is `Q114`. |
| `Q114` | The lane count invented lanes the road has not got | Closed — fixed at `ROADGRAPH_SCHEMA` 11; per-edge `lanes` remains a limit. |
| `Q115` | What repeats ships as a prop with placements; what is measured stays merged | Open — `P5-1`–`P5-6` built and passed the user's drive; `P5-8` is outline only. |
| `Q116` | Two regions meet at a hard edge, and the join decides where the cut is, not the unit | Open — `P5-7a`–`g` and `P5-9a`–`d`, `f`, `g` built; `P5-9e` refused; remainder below. |
| `Q117` | Opposed one-way ribbons are paired geometrically, and the join is published | Closed. The pairing and the codec's `centre` step stand; the shader line it fed is off |
| `Q118` | RM1001 is drawn from TD's survey; `RoadMark.axis` selects the host rule | Closed. `longitudinal_legibility_scale` 1.0 and `draw_pair_join` 0.0 on the user's call. |
| `Q119` | An editor save is a no-op; resource rationale lives in sidecar `.md` files | Closed 2026-09-07. |
| `Q120` | Four regions measured: Wan Chai is not the dense extreme | Open. Coefficients closed; the streaming distances are `P4-5`'s. `carve.edges` is |
| `Q121` | The mesh contract against a DCC workflow | Open. `P5-10`–`P5-13` built; `P5-14` (textures as an option on tiles, under `P3-20`'s |
| `Q122` | The verifier's ambiguous sample, the per-tier occluder, and the resident budget | Open. `P5-15`–`P5-18` built; the far-tier occluder and a web bundle without one are the |
| `Q123` | A non-convex border quad folds `FlatBuilder`'s fan | Closed 2026-09-08 as `P5-19`. `inverted` reads 0 and `check.sh` exits 0 on all four |
| `Q124` | The distance to the Godot guide, read as three collaborators' first day | Open. `P5-20`–`P5-27` built; `P5-28` (reopening `Q38`'s baked exposure) is the user's |
| `Q125` | The opposed-pair centre line is drawn as geometry and yields to TD per metre | Closed. The shader's `draw_pair_join` stays off; the join shrank under `Q129`/`Q132`. |
| `Q126` | A row of arrows on a two-way edge is read by direction; `lanes_forward` | Closed for cause A. B half closed by `Q128`/`Q130`; C and D open. |
| `Q127` | Reading a carriageway width where the ray survey cannot | Closed — measurement only, nothing shipped. Its cascade shipped as `Q128`. |
| `Q128` | Two agreeing stations, and a strip of HyD's paint where no ray reaches | Closed — shipped, `ROADGRAPH_SCHEMA` 14. Coverage 39.5% → 53.5% Wan Chai, 34.2% → 63.3% |
| `Q129` | A width is the carriageway's, and most open edges are not a carriageway | Closed — built as `P3-33b`/`c`, graded by `P3-33e`. `P3-33d` superseded by `P3-35e`; `P3-33f` open. |
| `Q130` | A row of arrows sets the count on an unmeasured width; arrows stand in the drawn lanes | Closed — `ROADGRAPH_SCHEMA` 15. `Ribbon.kerb_target`'s frame defect closed by `P3-35d`. |
| `Q131` | A kerb in the road is not the road's edge: seams, islands, lines across | Closed — region schema 4. Open items below. |
| `Q132` | The longitudinal lines come from TD's survey; where TD is silent nothing is drawn | Closed — built as `P3-34b`–`d`, `CITY_SCHEMA` 33. `draw_centre_line` and |
| `Q133` | The ETL is refactored, not rewritten; the drawn road gets one reader | Closed — decided; `P3-35a`–`h` built below, `P3-35g4` refused. |
| `Q134` | Paint stands where TD surveyed it: arrows off the lane slot, and the decks' paint read | `P3-36`, `P3-37` built; the user's drive owed. |
| `Q135` | Road paint stays mesh; what it costs a frame is measured, and it casts no shadow | `P3-38`–`P3-42` built; the user's drive owed. Open: which deck, where two cross. |
| `Q136` | The minimap is drawn from `RoadGraph`, once, and switches off on its own | 🟡 Built (`P3-44`); the user's drive and the web build's clip frame owed. Heading-up and the merged plate are the user's calls; the one-way arrows were, and are off since 2026-09-24 for a border arrow toward an off-map target. Owed the user: `span_m`. |
| `Q140` | The harbour is a frame minus the land, and the land is north of the sheets we hold | ✅ Closed — the user's calls: on the minimap with `P3-44` (2026-09-24), in the world as a plane over sunk ground (2026-09-25) · `P3-45` |
| `Q141` | The 咪錶 runs TD's tariff on what was driven; the skill is the tip, and speed pays now | ✅ Closed — the user's calls, built as `P3-1a`. Four stranded pickups on the merged runtime, named. The user's drive owed. |
| `Q142` | The pending customer is the pickup pool, a stop is said as its building over its road, and the arrow is as the crow flies | ✅ Closed — the user's asks, built as `P3-5a`; iB1000's `BUILDINGNAME` joined in the ETL. The user's drive owed. |
| `Q139` | One voice: the cab's instruments in one dark housing — a dial for the speed, the 咪錶's red LED kept for the fare | ✅ Closed — the user's calls, built with `P3-44`. The user's drive owed. |
| `Q138` | The HUD takes the racing-game arrangement, and every known future component has a graded slot | ✅ Closed — the user's call, built with `P3-44`. The user's drive owed. |
| `Q137` | A router is built; a route line on the map is not | ✅ Closed — router ✅ built (`P3-43`), consumed by `P3-1a` (`Q141`): a directed-edge search prepared once per destination, diffed pair for pair against `reachability.py`. **Reopened and reversed by the user on 2026-09-24**: the legal route is drawn on the minimap (`P3-46`), and guidance routes legally. Held: the next-junction arrow. |

---

# Questions

## `Q1` — Road Network v2 carries no Z, but `ELEVATION` encodes the level

**Status.** ✅ Closed · `P0-2`

Centrelines carry no Z. `ELEVATION` is an integer grade-separation level; `elevation_levels` in
city config maps each to a height offset, measured from the ground rather than the datum (`Q11`).
Where a ramp climbs between levels is not expressed (`Q13`).

**See.** `DATA_SOURCES.md` · `Q11` · `Q13`

## `Q2` `Q3` `Q5` — Building data is fully scriptable

**Status.** ✅ Closed · `P0-1`

The CSDI portal serves a territory-wide index of 3,456 sheet polygons with direct download URLs and
a per-sheet `REVISIONDATE` (the cache key). Six sheets cover the region, ~44 MB each. One public key
covers all sheets; never commit it.

- ⚠️ 612 triangles per building, so LOD tiers are load-bearing.
- Coordinates arrive in Godot's convention `(easting, elevation, -northing)`; vertices are unwelded
  at exactly 3.0 per triangle, so flat shading is baked in. "Non-textured" describes the buildings —
  terrain ships with a JPEG.

**See.** `DATA_SOURCES.md` "Buildings" · `P1-1` · `P1-2`

## `Q2′` `Q3′` — Two façade-probe findings that reuse numbers already taken

**Status.** ⚠️ ID collision, flagged rather than renumbered · `Q2′` superseded by `Q34`

The façade-colour probe cites its findings as `Q2` and `Q3`; renumbering would falsify citations.

- `Q2′` — height does not predict façade colour: it explains 6.1% of `L*`, 1.0% of `a*`, 1.6% of
  `b*`. Superseded in full by `Q34`.
- `Q3′` — window period inconclusive, not negative: 54% of walls gave a period, median 1.19 m
  against `P3-7`'s 2.77 m, pinned at the search floor (harmonics). ⚠️ Answering it means rebuilding
  `P3-7`'s whole-wall autocorrelation, not extending the probe.

**See.** `Q34` · `Q37` · `P3-7`

## `Q4` — Device floor: A13 (iOS) and Adreno 618 (Android)

**Status.** ✅ Closed

iOS floor A13 (iPhone SE 2 / iPhone 11), a support-matrix question. Android floor Adreno 618 tier
(Vulkan 1.1, 4 GB RAM, Snapdragon 710–730G), a performance question and the only one that binds the
budget: A13 is ~3–4× its GPU throughput. The real floor is "Vulkan 1.1 with a maintained driver".
Chosen over a global-market floor because Hong Kong skews high-end. It is what makes <150 draw
calls, <300k triangles, <128 MB texture coherent.

**See.** `ARCHITECTURE.md` "Performance budget"

## `Q6` — Does the region need Central for the circuit to feel complete?

**Status.** 🟡 Open, deferred to after `P3-9` · scope

A question for drivers, not a measurement (`Q8`). `Q21`'s tunnel portals resolve only if the region
grows east — the Cross-Harbour descent lies outside the bounds.

**See.** `Q21` · `P3-9`

## `Q7` — Game-space origin is the region's north-west corner

**Status.** ✅ Closed

East is `+X`, north is `−Z`, zero at the region's north-west corner. The sign of Z is forced by
Godot's handedness; only the anchor was a choice, and north-west keeps tile indices non-negative.
Origin northing is ceiled where easting is floored (rounding outward).

⚠️ Non-negativity is a property of the region, not the source: `fetch.py` downloads every sheet that
intersects, so clipping before indexing is part of the data contract.

Rejected: a south-west (GIS bbox) origin — negative tile indices in every filename.

**See.** `ARCHITECTURE.md` "Coordinates" · `Q10`

## `Q8` — The city itself is the fun

**Status.** ✅ Closed · the user's verdict after driving `scenes/dev/city_drive.tscn`

Driving an HK-like map is a fun enough gimmick on its own, so "accurate city, toy vehicles" rests
on a verdict. ⚠️ A gimmick carries a first session and says nothing about the tenth: the live risk
is "novelty does not survive the first session" (`P3-9a`). The verdict does not cover `P3-*`.

**See.** `PROGRESS.md` risk register · `P3-9a`

## `Q9` — Read the geodatabase, not the GML

**Status.** ✅ Closed · `P1-3`

Road Network v2 ships as a 17 MB file geodatabase and 539 MB of GML. The pipeline reads the
geodatabase; every GML is dropped.

**See.** `DATA_SOURCES.md` "`Q9`"

## `Q10` — Region-local origin plus a recorded `city_offset`

**Status.** ✅ Closed

Each region keeps a local frame; `city.json` carries the `city_offset` into the city-wide frame. A
single city-wide origin was rejected on measurement: Hong Kong spans 62.9 × 45.4 km, putting Wan
Chai ~38 km out where float32 spacing is 3.91 mm — ~8% of the 50.6 mm suspension sag. float32 holds
millimetre precision to ~16 km (2¹⁴), not the ~65 km first assumed.

⚠️ A city's declared `bounds` never change — every offset is measured from them, so they are
declared, not derived. Enforced by the warning in the city file, a loader check that each region
lies inside, and a test that adding a region leaves the frame unchanged.

**See.** `ARCHITECTURE.md` "Two frames, and why" · `Q7`

## `Q11` — Road heights sample the terrain height field

**Status.** ✅ Closed · `P1-3`

`elevation_levels` offsets are from the sampled ground, taken from the terrain in the sheets
already downloaded; `roads.ground: terrain | datum` in config. Level-0 median 4.21 m against
`P1-2`'s independently measured building bases at 4.29 m — roads land 8 cm below the doorways,
untuned. Zero vertices with no terrain under them.

Rejected: nearest building bases (podiums sit above the pavement, max 75.92 m); one authored offset
per region (the region spans 55 m of relief).

**See.** `Q1` · `P1-2`

## `Q12` — The source's one-way directions match the street

**Status.** ✅ Closed · the user's verdict after flying the road-graph preview

`TRAVEL_DIRECTION` plus digitised vertex order matches the real street (Jaffe Road runs east), so
`P3-3` routes on the source's directions without hand correction.

⚠️ One street was checked. The geometry is separately quirky: Lockhart Road is two-way carried as
opposed one-way carriageways 2.73–3.41 m apart; six such pairs region-wide (1.96–3.85 m), a floor
that counts only pairs sharing both endpoints.

**See.** `P1-3` · `P1-4`

## `Q13` — All 36 mixed-level nodes are ramps

**Status.** 🟢 Largely answered · residual is `P4-1`'s

Every one of the 36 nodes joining two levels is a real ramp: 17 junctions, 13 attribute flips,
5 tunnel portals, 1 stub, zero plan-coincident crossings. 29 of 36 step under 0.5 m since `Q90`
ramped the touchdowns.

- The 13 flips are one road split where `ELEVATION` changes partway up the ramp, so both sides are
  wrong by about half a deck height. Clearances of 2.14–4.02 m are too low for a street to pass
  under; deck-above-terrain margins are bimodal with a gap between +0.93 and +2.14 m.
- Open: the 5 portals and `e425`'s stub (8 m over a 42 m stub is a 19% grade; needs the region to
  grow east, `Q6`), and node 269 MARSH ROAD, where the deck ends in a 0.65 m face and the missing
  descent belongs to level-0 `e466` beyond it.
- 🔴 `nearest_edge` refuses all 60 off-grade edges (7.5% of 797 edges, 19.6% by length, 23.3% by
  carriageway area) — a graph refusal whose premise expired (`Q103`): 39 of the 60 reach street
  height and a user drove one, while `clearance.py`, `fence.py`, `centreline_error.py`,
  `street_tracker.gd` and the wrong-way monitor all gate on level 0. `P4-1`'s job is "the network
  is open and ungraded".

**See.** `P2-7` · `Q20` · `Q21` · `Q6` · `Q90` · `Q103`

## `Q14` — Taxi-stand operating-time restrictions are discarded

**Status.** 🟡 Open, deferred deliberately · `P3-1`

`Status_EN` carries operating-time restrictions `P1-5` drops, so a part-time cross-harbour stand is
modelled as full-time; `fares.json` has no field. The source is already fetched — a schema bump and
a parser when the fare loop needs it.

**See.** `DATA_SOURCES.md` "Taxi Stands" · `P1-5`

## `Q15` — Fare nodes snap by plan distance only

**Status.** 🟡 Open, half fixed · `P4-2`

Fare points are 2D, so snapping compares plan distance. `fares.build_region` restricts candidates
to `elevation_level == 0`, as `kerbside.py`, `tramway.py` and `arrows.py` do. It fixed `f_032`
(tram stop on HENNESSY ROAD under CANAL ROAD FLYOVER, which lost to the deck by 0.80 m in plan and
shipped at `pos.y` 12.562 m; now edge 217, 3.947 m). 1 of 48 nodes moved.

### 🔴 It became live, and here is what fixed it

The earlier "no node is affected" was measured on `P1-5`'s taxi datasets and went stale when
`P3-14` added tram stops as a second producer. The level-0 restriction above is the fix.

### ⚠️ Nothing the stage published could see it, and that is why there is now a counter

`worst_snap_m` (10.04 m, `f_040`), `unsnapped` and every `by_category` count were identical across
the defect. `FareReport.off_grade_nearer` and `worst_off_grade_margin_m` count points with an
off-grade edge nearer than their level-0 host: Wan Chai reads 1, by 0.80 m, warned by the CLI.

- Named for the rule: it counts tunnels (15 level −1 edges) as well as decks.
- ⚠️ Counted before the `max_snap_m` refusal — below the guard it could never report the point the
  limit discards (`Q58`). Pinned by the fixture's snap-limit test (adrift point, 2 m margin).

### What is still open

A point that genuinely belongs to an elevated road now snaps to the street beneath; the source
cannot say otherwise. `P4-2`'s; `off_grade_nearer` is the detector.

### Why the number rather than a per-group config key

An `at_grade:` key on the fare group is refused: `_fare_group` does not reject unknown keys, so a
typo would silently restore the defect. "A 2D point snaps to the at-grade network" is a fact about
the join, not a place; three sibling stages encode it in code.

### ⚠️ Mechanism 1 — a claim generalised past the producer it was measured on

A claim measured against one producer, left standing when a second arrived (`Q54`, `Q56`, `Q57`
are the same shape). Re-check stage-level claims when a stage gains a producer.

### 🔴 Mechanism 2 — a rule discovered mid-task and not swept across the rest of it

`P3-14` invented the level-0 rule for tram rails and did not apply it to the tram stops it added in
the same commit. When a constraint is discovered mid-task, sweep the rest of that task for
consumers. ⚠️ A shared opt-in `Segments.at_grade` is refused — the author had the rule in hand and
still missed the consumer. If revisited, the form is a required `levels=` keyword on `Segments.of`.

### The three guards, and why none is redundant

`test_fares.py` grades the code, `off_grade_nearer` the run, `export.py`'s `_check_fares` the
artefact — a stale `fares.json` left through a `--from` rebuild, stopped by `sync_generated.sh`'s
`export --check`. ⚠️ `_check_fares` reads `elevation_level` strictly: a default would make the
guard agree with a document it cannot read. The fixture carries the field.

**See.** `P1-5` · `Q13` · `P3-14` · `Q58`

## `Q16` — LOD0 does not ship

**Status.** ✅ Closed · `P2-1`

The exact-weld tier is dropped: two tiers, one 250 m band edge, 400 m unload. PCK 51.6 → 21.1 MB
(−59%); worst-case visible triangles 249,210 → 150,374 (−40%, the dropped tier was the one drawn
nearest the camera); draw calls unchanged at 53. Roughly 4–5 regions per 200 MB instead of 2.

- ⚠️ `tiles[].aabb` is the union of the shipped tiers. Decimation does not only shrink a box:
  `collapse` buckets on `floor(position / cell_m)` and averages, so on `t_01_02` the 4.0 m tier
  stands 12.03 m taller than the 1.5 m tier. `verify_city.gd` checks it.
- Not closed: a desktop-only exact-weld tier is an export-filter question (200 MB is the iOS
  cellular threshold) — one entry in `lod_cell_sizes_m`.
- ⚠️ Bundle size is measured from a PCK, never summed from source files: the source saving here was
  74.7 MB against a PCK saving of 30.5 MB.

**See.** `PROGRESS.md` metrics · `P2-1`

## `Q17` — CI runs `tools/check.sh` and cannot check the generated assets

**Status.** ✅ Closed

Two jobs on every push and PR: `ruff` + `pytest` on Python 3.11 and 3.13, and `tools/check.sh`
against a pinned Godot. CI runs the script, never its steps restated as YAML.

- `game/assets/generated/` is gitignored, so `VERIFY_GENERATED=0` skips the generated-asset verify
  tools and the script prints that it skipped them. Region-free tools (`verify_beam_budget`,
  `verify_vehicle`) still run. Running the ETL in CI (320 MB from a government server per push) is
  declined.
- ⚠️ `if ((VERIFY_GENERATED))` is a false green under `set -u`: `=true` dies and exits 0, `=1x`
  falls into the skip branch. It is compared as a string; only an exact `0` skips.
- The `godot` job does not install the ETL; it reads the `gdtoolkit` pin from `etl/pyproject.toml`
  with `tomllib`. ⚠️ No pip cache on that job: `setup-python` keys its cache with no job component,
  so two jobs installing different things poison each other.

**See.** `ARCHITECTURE.md` "CI"

## `Q18` — Ground colour sits under a chroma knee, and the classifier is refused

**Status.** ✅ Closed · chroma value superseded by `Q36` · `P3-10`

- Chroma reaches the screen through a knee: at `L*` 52.6, authored `C*` 6.81 → screen 1.95,
  11.00 → 2.93, 14.00 → 6.25, 31.96 → 28.42. ⚠️ One viewpoint's number, not reusable: distance and
  surface brightness both move it, the mechanism is unidentified (`base_wash` is 0.0), and it was
  measured for up-facing ground — do not assume it on a façade.
- ⚠️ `Q36` supersedes the doubled chroma: it compensated a lightness problem `Q33` later fixed.
  Read `Q36` before raising chroma again.
- `ground_sink_m: 0.20` clears the carriageway; no z-fighting in the region (`P3-10`).
- Refused: the land-cover classifier, on a resolution mismatch no tuning reaches (source ~10 px/m,
  ground clusters at 4 m). The water class is shadow (51.1% of it on rooftops); the vegetation
  class is edge speckle (5.5% of 66,710 cells over 50% vegetation) and would halo every building.
  If parks are wanted, the source is vector land-use polygons.

**See.** `ART_DESIGN.md` "Ground" · `Q29` · `Q33` · `Q36` · `P3-10`

## `Q19` — Solid geometry stands in the drawn carriageway

**Status.** 🟢 Structure half carved (`P3-28`) and the car-bar fence built (`P3-29`), on the
user's call of 2026-08-31 · 🟡 building half open and unowned · drives owed (the 15 mouths, `e99`)

Solid geometry stands at bumper height (0.3–2.0 m above the deck) in drawn carriageway that
collides. `P3-9a′`'s three drivers stopped because they kept sticking on bridge rails. `Q51` keeps
traffic off these edges (`is_routable`); this record is the player's half. ⚠️ Figures below were
measured under the 1.6× widening that `Q95` replaced with a floor; re-measure before quoting.

Standing rules:

- The gate is per edge, not a region share: a clear corridor ≥ `lane_width_m` (3.20 m) held along
  every drivable level-0 edge. `tools/carriageway_occupancy.py` grades it from the shipped bundle,
  shares no code with the pipeline, and fails today by design.
- Two bars over one measurement: the lane (3.20 m) decides routing, the car (1.80 m, `taxi.tscn`'s
  body) decides whether the player is stuck. Never merge them.
- Two populations: the grader and the pipeline (`clearance.json`, `tools/narrowing.py`) differ by
  four edges (`e99`, `e207`, `e781` grader-only; `e702` pipeline-only) — `Q51`'s plan-cell gap.
  Never quote one as the other. `e702` EXPO DRIVE CENTRAL is a reconciliation row, not a defect.
- Extents are upper bounds (nominal 1 m pitch; a junction trim joins two starved runs). A single
  sweep cell is worth ±0.25 m (samples re-phase; the binding station changes hands).
- ⚠️ A first measurement read 13.71% by marking triangle bounding boxes; sampling surfaces cut it
  to a third. A vertical ray cannot find a wall, so `Faces.heights_at` is not reusable here.
- ⚠️ Grader traps: divide shares by the whole drawn area; never judge a trimmed cross-section (it
  condemned 18 clear edges); negate `rot_y_deg` for landmarks. The walk is recorded into a
  `Lattice` and replayed so the occupier prune stays a structural superset.

### The occupiers, named — 2026-08-20

- 26 grader failures: 14 `BUILDING`, 11 `INFRASTRUCTURE`, `e207` mixed, no `LANDMARK`. Building
  failures starve 1–3 m on short edges (12 of 15 under 20 m, median 11.0 m); structure failures are
  long ramps (median 101.8 m in plan, none under 20 m), one locality around WAN CHAI INTERCHANGE.
- Narrowing is refused: swept 1.60× → 1.30×, not one edge clears and two (`e595`, `e207`) are lost,
  because the figure is the widest continuous run and narrowing clips a run against one kerb.
  ⚠️ The Lockhart Road slot is no constraint in that range (it closes at f = 1.066).
- Lane counts and widths were invented (no lane attribute in Road Network v2). Published kerbs
  exist — iB1000 `CartoTransLine` `RM`, HyD Pavement Polygon (`Q57`, `Q94`, `Q95`).
  `tools/carriageway_margin.py` measures near-side overhang: p50 +1.59 m, 75.0% of stations past
  the kerb — but p50 −0.36 m on edges under 20 m. ⚠️ The ray method has no purchase on a 7–16 m
  junction stub ("short edge" and "junction" are one population); never quote its single-station
  readings, and never quote the two-publisher agreement without its ray cap.

### The building half is not a width defect — 2026-08-21

The centreline is inside the occupier on 13 of the 15 building-half edges (the other two are
0.49 m from it); sideways distance to the first clear cell 0.49–3.90 m, signs mixed (3 right,
9 left, 1 tie), so not a whole-layer registration shift. Profiles read the full drawn width and
collapse at one to three stations: the occupier crosses the carriageway. `lanes`, `width_m` and
any widening move ribbon edges, never the centreline — no width rule reaches these.

- Open: why a drivable level-0 centreline is inside a building — a building spanning the street
  extruded solid to ground, a per-site centreline/footprint disagreement, or a graph edge with no
  street. Sites cluster (`e314` `e335` `e405` `e499` within 80 m around Leighton Road; `e627`
  `e629` on Great George Street). Unassigned.
- Instrument: `tools/carriageway_occupancy.py --city hong_kong --corridor-report` — opt-in, the
  default listing byte-identical with it off. ⚠️ The centreline cell is `argmin(|offset|)` over
  judged cells, not walked ones; a side tie is reported as no side; lengths are in plan.

### The structure half, measured for the first time — 2026-08-30

- Of the 11 structure failures, 7 have the centreline inside `INFRASTRUCTURE` (`e233` `e125`
  `e788` `e485` `e327` `e256` `e55`) and 4 are clipped only by the widened ribbon (`e222` `e398`
  `e781` `e99`). The blocker's bottom sits at road level and its top 1.5–2.0 m above: a ramp flank
  or the wall a railing stands on. The collider is the tile; `railings.glb` has none.
- Every one is a ramp drawn at about double its surveyed width. `Q23`'s `floor_on_structure_m`
  cannot reach them: it keys on `on_structure`, a height-provenance flag a terrain-sampled ramp
  never trips. ⚠️ The lateral question here is not the vertical narrowing `Q23` refused.

### The probe is built and the narrowing it licenses is REFUSED — 2026-08-30

`roads.py::_structure_bounded` publishes `structure_bounded` per vertex (`roadgraph.json` schema
8): 427 stations, 1,192 m of level-0 centreline against `Q23`'s 546 m. The flag ships; nothing
consumes it (`_half_widths` reads `on_structure` alone).

- 🔴 Refused: consuming it narrowed 43 edges and drove `e55`, `e398` and `e788` to 0.00 m clear —
  the clear asphalt was a strip off-centre (`e55`: 4.49 m) that narrowing deletes. Clear at a point
  is not the clear run containing it.
- ⚠️ The count is a lower bound: `bound_step_m` does not converge (285 → 453 stations over
  1.0 → 0.0625 m; 0.25 is a knee). Never quote it without its step. `bound_reach_m` is a
  declaration, not a measurement. Published 427 vs 426 recomputed is `round_position`.

### The walls carry almost no through-route, and closing them is admissible — 2026-08-30

`tools/reachability.py` over `roadgraph.json` and `clearance.json`. ⚠️ `road_graph.gd` has no
adjacency or router, so the tool reimplements `is_routable` deliberately; a divergence is a
finding, never a bar to retune.

#### 🔴 The obvious instrument was wrong, and it was tried first

Strongly connected components are dominated by the region clip (largest 331 of 737) and do not
move when every starved edge is refused. The headline is pairwise reachability, over the edges
surviving in both worlds (`Q58`).

#### Measured, on the shipped bundle

Refusing all 24 lane-starved edges loses 1 ordered pair of 187,946, worst detour 55.8 m; at the
car's bar (19 edges) it loses 0. The one pair is `e168` WAN CHAI INTERCHANGE → `e219` CROSS HARBOUR
TUNNEL, severed by `e55` alone — a traffic loss, not a player one (`e55` clears the car).

#### 🔴 The two starved populations disagree about the COST, and this is the first time it mattered

The grader's 26 include `e207` CANAL ROAD EAST (1.95 m: under the lane bar, over the car bar);
refused alone it disconnects nothing and diverts 1,561 pairs by up to 976.8 m. That is `P3-3`'s.

#### Where the walls stand, which reachability cannot say

`e222` and `e256` are reachable only by way of another blocked edge, so their closure belongs at
the pocket mouth.

#### Checked

Mutation-checked (`Q72`): refusing 12 HENNESSY ROAD edges loses 14.87% of pairs, 12 GLOUCESTER ROAD
edges 12.54%. Traversal pinned by `etl/tests/test_reachability.py` (one-way, turn restriction,
U-turn exclusion, fixed population, detour arithmetic).

#### 🔴 What this licenses, and what it does not

Closing blocked edges to the player is admissible, graded at the car's bar, never the lane bar.
It prices removing the edges, not standing on them.

### The centreline is where the publishers put it, so candidate 1 is refuted — 2026-08-30

`tools/centreline_error.py`. No centreline-shift rule.

#### 🔴 The two normals are opposite, and this is the first code that could notice

`carriageway._stations` emits a right-of-travel normal; `surface.mitres` a left one (load-bearing:
`TEXCOORD_0` is measured from the nearside kerb). `carriageway.py` is not wrong — it keeps only
sign-free quantities. The tool carries one named negation (`_LEFT`) and a test asserting the two
stay opposite. Do not "restore consistency". Sign settled by measurement: shifting +1.0× takes
`|off-centre|` p50 0.376 → 0.043 m over the 289 edges licensed in both worlds.

#### The correction that is sourced, and it is under a metre

Over 292 licensed edges `|off|` p50 0.37 m, signed p50 −0.05 m, two-sided (132 left, 160 right).
⚠️ Quote by basis: `one_way_uncrossed` max 1.95 m, `two_way_span` 3.11 m. The tool's licensed set
equals `roadgraph.json`'s measured `width_source` set exactly; spans agree to 0.0005 m.

#### The seven, and the gap between what is available and what is needed

Sourced shifts on the six that licensed one are 0.02–0.88 m against 1.43–4.49 m to the first clear
cell (`e233`: the whole cross-section is blocked). ⚠️ `e99`, `e125`, `e207` are refused because
the ray crossed a median — shifting `e99` by its apparent 3.81 m would put it in the opposing
carriageway; the `crossing` refusal is load-bearing. On `e55` the residual is noise (19 of 42
stations on the far side of its median); on `e485` it wanders (`spread_m` p90 4.73 m).

#### Moving it there clears nothing, and moving it the wrong way clears more

The sourced shift clears 0 edges at either bar (24 under the lane, 19 under the car), tapered or
rigid; −2.00× clears 2, because the drivable strip is invented asphalt outside the published
carriageway. A rigid shift tears 4.0375 m open at a shared node. ⚠️ Measure that per node, not per
edge (head-to-head edges open twice the shift); `narrowing.moved` intersects edge sets before
counting cleared/lost.

#### 🔴 Candidate 3, priced: 143.2 m of published carriageway with a wall in it

At each edge's surveyed width, `INFRASTRUCTURE` only: 143.2 m under 1.80 m over 7 of 292 priced
edges (`e233` 50.60 m, 40.9%); `e222` 0.0 m. ⚠️ `ClearanceReport.corridor_m` is per polyline
vertex, not per cross-section — weight per station (`stations × ALONG_M` was wrong by 14×).
Unlicensed `e99` `e125` `e207` `e781` cannot be priced (`Q54`).

#### What this licenses

Candidate 1 refused: the wall stands in the published carriageway. `structure_bounded` has no
consumer.

### 🟢 The call: carve the seven the survey licenses, fence and dress the four it cannot — 2026-08-31 (user)

- Carve `e233` `e55` `e485` `e788` `e398` `e256` `e327` procedurally from sourced data. 🔴 The
  prism is the surveyed span, never the drawn floor — that would cut published structure on an
  invented width (`Q54` inverted).
- Fence what no publisher licensed, at the car's bar; the fence set is measured after the carve.
  `is_passable` stays at the lane bar — a car-bar predicate sits beside it.
- The fence is dressed, never invisible: authored barrier props (CC BY-SA), placed from the
  published blocked set. A barrier asserts a closure the real street lacks — accepted game fiction.
- Not decided: the building half (nothing licenses carving a building) and `Q22`'s off-grade family.

### 🔴 A ledge is not a wall, and the corridor metric cannot see one — 2026-09-01 (user, from the driving seat)

The user beached on `e99` FLEMING ROAD: `INFRASTRUCTURE` 0.356 m above the carriageway against
`suspension_travel_m` 0.18 m, while `e99` passed every lateral bar. The 0.18–0.30 m band sat
between `ground_clearance.py` (terrain only, then) and the occupancy bumper floor (`BUMPER_LOW_M`
0.30 m, `Q23`). ⚠️ Do not answer it with a lower corridor bar. Resolved by the three sections
below: vertical term refuted, band instrumented, `e99` carved.

### ✅ The carve is built and the seven are measured — `P3-28`, 2026-08-31

`pipeline/carve.py`, between `roads` and `surface`; publishes `carve.json`. 4 of 7 cleared
outright; occupancy 26 → 22; `INFRASTRUCTURE` 1.088% → 1.009% with `BUILDING` unchanged at 1.204%.
The retaining walls cost 2.1 MB.

- ⚠️ Residuals are predicted: the grader bins at `INDEX_CELL_M` 1.0 m, so width `w` reads ~`w − 2`
  (`e485` 2.90 m, `e256` 1.92 m). 🔴 Never answer a residual by widening the prism.
- 🔴 The estate is not watertight (5.38% of edge slots open in source meshes, 14–26% in tiles), so
  derived capping closed zero loops and carving at source rescues nothing. The cut face is a
  constructed retaining wall per station, height measured from the structure removed — a face no
  publisher drew. It takes its class from the removed structure, never the tile's first vertex
  (`FACADE` glazing on concrete).
- 🔴 A second pass degrades the first (`e327` wall 141.8 → 75.8 m): `buildings.json` carries a
  `carved_edges` marker and the stage raises on it; reachable via `--from roads`.
- ⚠️ The stage resolves `city.out_dir` and takes no `sources_root`. `buildings.Placement` couples
  a stage to a fetch silently — the refusal test once passed only on clones that had built, and CI
  was red for 8 runs.
- `facing_away` is 0 and reachable: derived from centreline positions, a test mirrors the wall.
- The soffit is read by ray parity (`terrain.undersides`), not `slab_gap_m` clustering, which
  offers a tall flank's own top as a soffit.
- Evidence is a frame: the `q19s` cameras re-shot, each twice and `cmp`-identical.

### 🔴 The vertical term is REFUTED, and `Q23`'s floor is why — `P3-29`, 2026-09-01

A second band `[deck + suspension_travel_m, deck + BUMPER_LOW_M]` in `clearance.py` was built,
measured and withdrawn. It added 3 fenced edges (`e411` `e522` `e520`), all climbing ribbons
resting on their own structure with ~0.2 m registration error — `Q23`'s suppression re-caught —
and did not catch `e99`, which has a genuine 4.50 m channel between two thin structure lines.
Reading the kerb-touching run instead fences 222 edges. `hong_kong.yaml`'s `clearance:` block
carries `car_width_m` and deliberately no `suspension_travel_m`; `_thresholds`' closed key set and
`test_a_vertical_bar_added_here_is_rejected` are the ratchet.

### ✅ The blind band has an instrument — `ground_clearance.py`'s second class, 2026-09-02

`tools/ground_clearance.py` grades structure proud of the road over the same walk, never pooled
with the ground class (`Q57`; ground is `Q24`'s). The 0.18–0.30 m band: 330 cells, 323.4 m²,
25 edges over the whole drawn ribbon — flat across `--structure-within-m` 0.50 → 8.00.

- 🔴 `structure_above` takes the lowest face strictly above the road. The terrain rule (nearest)
  reads a flyover deck top as +13.27 m proud on 210 edges. Both wrong rules delete the finding;
  both are tested.
- Bounds (`BUMPER_LOW_M`, `BUMPER_HIGH_M`) are imported from `pipeline.clearance` — a shared
  bound, never a shared method.
- 92.8% of road cells have no structure: absence is the normal answer, so no `--accept-coverage`.
- The section share separates a ledge (a strip: p50 14%) from ribbon-versus-deck (most of a
  section: `e125` 82%, `e411` 70%). ⚠️ The denominator is every road-drawn cell of the section,
  never the cells that found structure.
- It grades and does not gate: the exit code stays the ground half's (FAIL 89 against 87, `Q24`).
- ⚠️ `e99` is no longer a known positive (carved); the anchors are a synthetic step and the three
  ramps above.

### Two corrections from the review pass, same day

- `optional_structure_faces` degrades to an empty index so a region with no `structure_class`
  geometry cannot abort the ground gate; `ground_faces` deliberately still exits.
- `Structure.observe` owns the decode, so `Structure.check` compares two independent counts;
  `test_every_outcome_books_exactly_one_bucket` is the ratchet.

### ✅ The fence is built and dressed — `P3-29`, 2026-09-01

Every drivable level-0 edge under the car's 1.80 m ends at a visible barrier: 14 edges, all
`authored` width, mostly the building half — the user's decision, priced at 0 of 189,753 pairs
lost and 55.8 m worst detour. `e207`'s exemption is retired; the predicate decides it.

- Chain: `clearance.car_width_m` → `city.json` (schema 21) → `RoadGraph.fits_car` /
  `fenced_edge_ids`, beside `is_passable`, never inside it → `pipeline/fence.py` → `fence.json` →
  `game/assets/authored/barriers/barrier.glb`.
- `verify_road_graph.gd::_check_car_bar` re-derives the fence from `city.json`'s arrays, never the
  predicate (`Q72`), and asserts an edge exists between the two bars.
- A mouth is a node: fenced edges are grouped into components and closed at the boundary (14
  components, 15 mouths, 90 units). ⚠️ "Ends with no way in" (a clipped dead end) and "ends behind
  another fence" are separate counters; the latter counts ends, so a shared node counts twice.
- The prop is a row of 2.0 m units, never one scaled barrier; `fence.unit_width_m` must equal
  `make_barrier.UNIT_WIDTH_M` (test-bound).
- 🔴 It collides (`-col` suffix), unlike every generated railing class; `verify_fence.gd` asserts
  the opposite of `verify_railings.gd`. Its material is `barrier_vertex`, not `barriers`.
- One `MultiMesh` plus 90 `StaticBody3D`s sharing one shape: 57–61 draws against 81–92 for
  per-placement instancing. ⚠️ `verify_fence.gd` grades the `.glb` only, so `fence.gd` prints its
  own collider count.
- Owed: a drive down each of the 15 mouths for legibility at speed.

### ✅ `e99` is carved, and the licence rule is knowingly bent for it — 2026-09-01 (user)

The user reported "car stuck here if entered in bad angle". No width bar reaches it: the
obstruction is interior, and the rules that catch it test the widening rim and fence 41–67 edges,
major roads included. Its bumper-band hits were 100% `INFRASTRUCTURE`, 116 of 119 inside the
authored 6.40 m. The carve moves the wall to the cut face, turning an interior obstacle into a
continuous kerb; the corridor barely moves (4.50 → 5.00 m) — the signature of a topology fix.

- 🔴 Debit: `e99`'s `width_source` is `authored`, so its prism is cut at an invented width. Bent
  for this one edge because class and containment are measured; it does not generalise to `e125`
  `e207` `e781`. `carve.json` publishes `width_source` per row.
- Battery after: occupancy 22 → 21; `clearance_reconcile` grader 21, disagreements 4,
  `EXPECT_PIPELINE` 19.
- Owed: the drive — a frame cannot answer "does it strand the car at a bad angle".

**See.** `Q51` · `Q20` · `Q22` · `Q23` · `Q24` · `Q54` · `Q57` · `Q58` · `Q72` · `Q78` · `Q95` ·
`P3-6` · `P3-28` · `P3-29` · `P3-9a′`

## `Q20` — Deck heights are sampled from `INFRASTRUCTURE`

**Status.** ✅ Closed · **Owner.** `P2-7`

Off-grade carriageway height is sampled from the `INFRASTRUCTURE` structure the tiles ship, not
invented from a per-level offset. The structure is a collider, so the ramps are physically drivable
(`Q13`'s "geometrically unreachable" no longer holds).

- |error| p90 0.095 m against a 0.50 m criterion; 92.7% within ±0.10 m. Graded by
  `tools/deck_error.py` against the shipped tiles, sharing no code with the pipeline.
- ⚠️ Deepest intrusion is 0.48 m against the 0.50 m gate: one station of 3,286, at node 275, the
  `CANAL ROAD FLYOVER` touchdown (`Q13`'s residual). Nothing else is past 0.24 m.

**See.** `P2-7` · `Q13` · `Q22`

## `Q21` — Should level −1 carriageway be drawn at all?

**Status.** 🟡 Open · **Owner.** Phase 4

15 edges, 5,010 m, 11.6% of carriageway area, ribboned under the terrain where nothing sees or
drives it, and solid. It costs triangles, collider surface and bundle bytes. `P3-3` and Phase 4 want
the edges, and `roadgraph.json` keeps all 15 either way.

- Heights cannot be improved: a tunnel is a void with no structure to sample, and 11 of 30 ends are
  clipped at the region boundary (~42 m of run for an 8 m descent). Resolves only if the region
  grows east (`Q6`).
- Widths are drawn at the authored width since `Q103` (`floor_by_elevation_level` has a `-1` key).
  It bought no triangles, so the cost argument stands.
- ⚠️ `e489` is not clear: the road rides a flat `terrain − 8.00 m` into the tunnel box's slabs,
  0.22 m of headroom at worst. The fault is vertical, not lateral. The other 14 bores clear.

**See.** `Q13` · `Q20` · `Q6` · `Q103`

## `Q22` — Off-grade carriageway hangs past its structure

**Status.** 🟡 Open · **Owner.** Phase 4

10.0% of off-grade carriageway hangs in air (`tools/overhang.py`). Cosmetic until off-grade is
drivable; in Phase 4 a wheel leaving the deck finds air, not a parapet.

- Causes: a ramp drawn wider than its deck, a centreline not centred on its deck, and `P2-1`
  decimating `INFRASTRUCTURE` on a 0.5 m cell.
- `tools/deck_margin.py` gives deck span, centreline offset and hanging metres per edge: 11 of 35
  readable level-1 edges hang, and the ten worst are all authored `lanes = 3` (9.60 m on decks of
  5.90–8.30 m; worst `e306` CANAL ROAD FLYOVER).
- 🔴 Refused: extending the carriageway survey off-grade. The publishers license 5 of 45 edges and
  their 2D lines find the street under the deck (`Q103`). Only the model knows where a deck is;
  that is a new stage and a scope call.

**See.** `Q23` · `P2-7` · `Q103`

## `Q23` — Carriageway width is a property of the station, not of the edge

**Status.** ✅ Closed · **Owner.** `P2-7`

Width is decided per station, because a road becomes a bridge partway along an edge (`P2-7` lifted
16 level-0 edge ends onto their ramps). Two rules, ordered: the elevation-level rule first, then the
per-station structure test, with `structure_taper_m: 15.0` blending the transition. The widening
itself is a floor since `Q95` (`floor_by_elevation_level`, `floor_on_structure_m`); the ordering
is what survives.

- ⚠️ Level before station, and the order is load-bearing: a station rule would re-widen an
  off-grade edge wherever no structure was found (`ISLAND EASTERN CORRIDOR`'s stub).
- ⚠️ The residual is not zero and should not be. `roads.py` decides "on structure" topologically,
  `overhang.py` geometrically. Stations left wide sit a median 0.15 m above ground: abutments and
  retaining walls, which are streets. 546 m of level-0 centreline is on structure.
- `roadgraph.json` carries a per-vertex `on_structure`; `y` cannot stand in (a level-0 hill road
  reaches 49 m). Width travels as the fourth column of `_Edge.points`, so `dedupe` and `trim` carry
  it.

**See.** `ARCHITECTURE.md` data contract · `P2-7` · `Q22`

## `Q24` — The at-grade road follows the ground

**Status.** 🟢 Half closed; the other half is `Q19`'s · **Owner.** `roads.py`

`roads.ground_profile` densifies at-grade edges at 10 m, samples the terrain, then thins at a
0.10 m vertical error (half the sink). Thinning matters: 504 of 721 at-grade edges gained no
vertex. Centreline area with ground proud fell 2.274% → 0.712%.

- ⚠️ Across the road is untouched: the ribbon is flat across its width and cuts into a cross-slope
  at the kerb. The residual floor is the tunnel portals (`Q21`).
- ⚠️ A single camera barely shows the fix; the banded measurement is the proof.

### ⚠️ Amended 2026-08-28 — "the outer metre" understates it, and there are three mechanisms

`tools/ground_clearance.py` publishes the per-edge population and an authored/rim split, and gates
on the edge count as a ratchet. No fix shipped. Measured under the 10.24 m floor; level-0 floors
are 0.0 since `Q129`, so re-run before quoting.

- 87 of 737 level-0 edges carry ground proud past the car's 0.18 m suspension travel; 14 over more
  than a tenth of their ribbon. `e192` CAROLINE HILL ROAD read 10.5% of the authored carriageway
  proud, to +1.27 m.
- Refused as a region-wide fix: a best-fit cross-tilt per station moves the region only
  0.60% → 0.54% of ribbon area, and two edges get worse (`e191`, `e153`). Tilt p90 is 0.111 m;
  `e192`'s 0.575 m is the maximum.
- The three mechanisms share no fix: the widening (`Q19`'s; dominated 6 of the worst 12); the flat
  cross-section (a Caroline Hill outlier); and a street that perhaps should not be drivable —
  JARDINE'S CRESCENT `e757`, 51.1% proud inside its authored 6.4 m.
- ⚠️ `--ground-within-m` is 3.0 and stays. Cells past it are published as overflow beside the
  window, so every `worst_m` is a lower bound.
- ⚠️ The tool has a second class, structure standing in the carriageway (`Q19`, `Q57`). Only the
  ground half gates; never read a structure figure against `--accept-share` or
  `--accept-edges-over-travel`.

**See.** `Q19` · `Q21` · `P3-10`

## `Q25` — Ground is decimated once per tier and cut afterwards

**Status.** ✅ Closed · **Owner.** `P1-2` / `P3-10`

`_tile_ground` merges the region's ground, decimates it once per tier, then cuts — the reverse of
every other class. `collapse` takes `_cluster_mean` over the members present, so terrain split
before collapsing lands on different positions either side of a boundary and the sheet tears.
Holes within 2 m of a boundary 15.65% → 0.42%, below the 0.54% interior rate.

- The ground is the only class both cut and continuous. Buildings are assigned whole (and merging
  the massing would join neighbours across streets); `INFRASTRUCTURE` tears into slivers inside
  solid volumes.
- ⚠️ Clip to the region plus a one-tile margin before merging: 657 MB peak RSS against 924 MB,
  byte-identical interior tiles. Cutting flush trades the tile seam for a region-boundary one.
- ⚠️ A fix that changes coverage changes every share computed over it (`ground_clearance`'s share
  rose past its gate with no ground moving). Re-run the grader that owns a number.

**See.** `Q24` · `P3-10`

## `Q26` — Which look ships?

**Status.** ✅ Closed 2026-08-17 — candidate `C` ships: accurate massing, flat per-building colour,
no façade fabric, `survey_apply = 0.0`. The user's call · **Owner.** `P3-9a`, which can reopen it

- Reopen condition, pre-registered: drivers reject the city and attribute it to flat surface.
  `P3-9a′` (2026-08-30) fired only the attribution half — drivers recognised the city — so the
  gate stays shut. The remark was volunteered, not asked; a round meant to settle it must ask
  directly. Do not loosen the condition after the data (`Q58`, `Q72`).
- The three looks are three files in `game/tuning/`: `city_facade.tres` (`C`),
  `city_facade_elements.tres` (`A‴`), `city_facade_warm.tres` (`B`). `cp` restores either; no
  rebuild. `A‴` was accepted by the user on 2026-08-09 and never faulted.
- Cameras and candidate definitions regenerate the comparison set; `build/driver/` is gitignored
  and is not provenance.

### ✅ The verdict — `C`, and what closing on it costs

- 🔴 The surveyed-surface chain ships dark: `Q40`'s verdicts and tint, `Q41`'s grammar, `Q42`'s
  `TEXCOORD_1.y` riders and `Q47`'s podium pack are shipped and consumed by no pixel in the
  default build (+0.24 MB of PCK). Whether to keep paying for `P3-7a` riders is an open scope call.
- 🔴 Grade every remaining `P3-7a` step against `city_facade_elements.tres`, not the default:
  under `C` a rider that draws nothing passes "keeps `C` byte-identical" trivially.
- `Q30` is re-owned: under `C` the over-saturation is entirely the base palette (`facade_hue` ×
  height bands, baked into `COLOR_0`). The palette does not move into `height_bands`; that was
  conditional on `A`.
- Measured (`tools/frame_stats.py`, share of frame moving ≥ 0.5 `L*` against `C`): `B` touches
  2–7× more of the frame than `A` and moves each pixel less. `A` is near absent at `skyline`
  (8.9%), so the choice is a street-level one. `A` raises whole-frame `C*`; `B` does not.
- ⚠️ `B` carries three unported shader fixes (`band()` convergence, `along_m` from the face
  normal, the 90–240 m fade); `city_facade_warm.tres`'s header is the authority. Port them only
  after a verdict that wants them.

### ✅ The verdict does not move with the tone curve

Re-shot at `adjustment_contrast` 1.14 and 1.00: responding share moves ≤ 1.0 point and magnitudes
scale by 0.888 against a pivot null of 0.877. So `Q26` and `Q31` decouple. ⚠️ One-sided: the looks
stay measurably separated; it does not show a human verdict is stable.

### ⚠️ The shoot found a reproducibility hazard in the preview scene

- Using the machine during a preview shoot ruins the frame: a click puts `free_look_camera.gd` in
  `MOUSE_MODE_CAPTURED` and mouse movement rotates the audit camera. Position survives, the run
  exits `DRIVER OK`, and the log is identical to a good one's.
- Rule: shoot twice and `cmp`; a frame that stands alone is not evidence. A byte difference is the
  trigger to look, not the verdict — one archived pair differed by 1 pixel, delta 1. Grade the
  diff before discarding.
- The preview scene is settled by `t=0.8` (byte-identical to `t=3.0`), except the skyline camera:
  see `Q38`.

### 🔴 Candidate `A′` is not gradeable yet — the glazed gate deletes the punched city

**Superseded by** `Q43`. `glazed` meant "glazing dominates" to the reader and "has any
fenestration" to the shader, so `punched` stock (50.1% of wall vertices; 66.2% of walls forced
solid) rendered blank. `Q43` split the gate: `fenestrated` is geometry, `glazed` is materiality,
`blank` alone denies openings. `A″` followed, then `A‴` (`P3-7a` `W1`/`W2`, `Q44`, `Q45`:
`unglazed_glassy 0.65`, `pane_l_jitter 6.0`, `pane_b_jitter 4.0`, `pane_hue_pull 0.25`).

- `A‴` against `C`: chroma cost `street` +1.16, `kerb` +0.78, `skyline` −0.05, inside `Q44`'s bar
  (`A`: +2.28 / +1.43 / −0.02).
- ⚠️ Every statistic of the broken `A′` was plausible and reproducible; only the frames showed the
  defect. Shoot frames, not only statistics. State the denominator of a vertex share: all lod0
  vertices (639,834) dilute against façade wall vertices (346,656).

**See.** `ART_DESIGN.md` "The clean/futuristic variant", "The audit viewpoints" · `Q27` · `Q30` ·
`Q31` · `Q34` · `Q37` · `Q40` · `Q41` · `Q43` · `Q44` · `Q45`

## `Q27` — `COLOR_0` is authored sRGB and must be linearised by the consumer

**Status.** ✅ Closed

The ETL writes `COLOR_0` as sRGB bytes and every consumer shader converts. Godot 4 has no
`vertex_color_is_srgb` render mode and `COLOR` is not converted like a `source_color` uniform.
`ARCHITECTURE.md` states the colour space. Unconverted, 57% of a lit façade pixel's luminance was
albedo-independent (6% fixed): the city was too pale and buildings indistinguishable.

- Ablation: exposure, ambient, glow, fog, tonemap and specular each moved albedo gain by ≤ 0.05.
  ⚠️ That is albedo gain, not the value distribution; ambient does move the latter (`Q31`).
- ⚠️ Refused: writing linear `COLOR_0` in the ETL. Linear `uint8` starves the shadows, changes the
  contract and breaks graders matching vertex colours against `class_materials`.
- ⚠️ A whole-frame mean is diluted by pixels that cannot respond. `drive.sh` renders are
  pixel-aligned, so subtract: `tools/frame_stats.py` grades the responding pixels.

**See.** `ART_DESIGN.md` "Per-building façade colour" · `Q31` · `Q33`

## `Q28` — A per-object seed must be `flat`

**Status.** ✅ Closed

`buildings.facade_uv` packs `TEXCOORD_0.y` as `surface_class + phase`, a per-object quantity; the
façade shaders' `phase` and `marker` varyings are `flat`. Interpolated, `phase` became a ramp that
the seed hash turned into stripes inside one flat triangle. Corners disagree because `collapse`
takes colour and UV from one cluster representative — right for colour, wrong for a seed (2.7% of
LOD0 triangles). Row-to-row contrast 6.80 → 0.07.

- ⚠️ Tint the class before naming it. An ETL feature (`LedgeShading`, ~440 lines) was built on a
  wrong diagnosis, measured at no change and reverted.
- Open for `P2-6`: `B373231543201063A0` is 8,793 source triangles over 128 levels and `collapse`
  cannot remove them at any cell size (8 m leaves 76 levels), because the facing key only merges
  an up-face with another up-face.

**See.** `Q32` · `Q33`

## `Q29` — The ground's normals are rebuilt in the fragment stage

**Status.** ✅ Closed

LandsD ships faceted terrain; `mesh.collapse`'s `height_field=True` path smooths it (mean normal
error 8.72°). Both façade shaders rebuild the normal from view-space position derivatives, gated on
`MARKER_GROUND`. Zero geometry cost; unwelding in the ETL would cost ~219k vertices and ~8 MB.

- ⚠️ Take the derivative unconditionally, outside the `marker` branch (derivatives are undefined
  across a non-uniform branch). Orient against the interpolated normal with a comparison, not
  `sign()`, which returns zero on a perpendicular pair.
- ⚠️ Refused: the land-cover class in `collapse`'s cluster key. Error 8.72° → 8.15° for +69%
  clusters; it splits by colour where the error comes from slope.
- ⚠️ A verdict pending on a screenshot has an expiry date nothing in the repo records.

**See.** `Q18` · `Q36` · `ART_DESIGN.md` "Ground"

## `Q30` — The shipped façade palette is not the one `ART_DESIGN.md` authorises

**Status.** 🔴 Open, and widened deliberately on 2026-09-08 · **Owner.** `Q26`

The height bands sit at `C*` 1.76–13.83 as rendered. At the shipped `facade_hue.strength: 3.0` the
per-building colour is mean 17.97, p50 14.86, p90 34.97, p99 64.64, max 82.32: 35.2% over `C*` 20
and 24.8% under `C*` 8 at once. `ART_DESIGN.md`'s palette table describes what ships, not what the
direction authorises.

- 3.0 is the user's decision (`P5-28d`, see `Q38`), with both costs quoted; 2.5 reproduced the old
  distribution and was declined. Not a regression.
- ⚠️ No value of `strength` fills the middle: linear amplification widens the tail faster than it
  moves the median. Over 2.0 → 3.0, under-8 falls 39.9 → 24.8 while over-20 climbs 16.6 → 35.2.
- Measure with `tools/facade_chroma.py` and re-run before quoting; figures move with `strength`
  and with the survey. ⚠️ The two move different ends: a resurvey moves the median, `strength` the
  tail.
- Gamut: 7.8% outside sRGB, worst `dE76` 133.8. Definition: `colour.in_gamut` (true where
  `lab_to_srgb`'s clip changed no byte), CIE76. `max` saturates at 82.32, the gamut ceiling. Always
  name the `dE` definition.
- Options, undecided: lower `strength`, compress the tail rather than scale it, or re-author the
  palette table around what ships. The second is slightly favoured by the evidence.

**See.** `ART_DESIGN.md` "Palette" · `Q26` · `Q34` · `Q37` · `Q38`

## `Q31` — The city's value range has an empty middle

**Status.** 🟡 Open, cause measured · **Owner.** `P3-9a`

Shaded street frames are bimodal: much of the frame is one near-constant dark surface. Remaining
work is a sky-visibility bake (`P3-9a`); `Q39` is its second consumer. Acceptance is within-mass
sd, not band share.

### The statistic now has a mechanism

`tools/frame_stats.py` reports band shares against `SHADOW_L` and `MIDTONE_L`. ⚠️ Percentiles
cannot show an empty middle, and `np.percentile` interpolates across the gap (a 50/50 frame at `L*`
2 and 70 returns p50 36.0).

### The failing set, re-measured — and the second frame found

The failing frames are the ones shot in shade (`kerb`; `taxi` at t01.20), not the ones under a
deck: `infra`, beneath the Canal Road flyover, has the fullest middle. ⚠️ A low middle alone is not
a defect (`skyline` 3.8% is fine); the pathology is a high shadow share and a low middle together.

### ✅ Every row of this table reproduces exactly

⚠️ `build/driver/` is not provenance: directory names are reused and nothing records the commit.
The durable thing is `ART_DESIGN.md`'s audit-viewpoint table; re-shoot rather than look for a file.

### The cause is the tone curve, not the fill

`adjustment_contrast = 1.14` pivoted about mid-grey and crushed the 10–30 band into < 10; it is in
series downstream of the palette, which is why `Q33`'s +2.7 `L*` asphalt lift looked inert.
`adjustment_contrast = 1.00` shipped 2026-08-20 on the user's instruction: shadow-mass `L*` on
`kerb` 4.42 → 10.51.

### ⚠️ But closing the band does not deliver what the claim asks for

- The lift is a translation: `kerb`'s within-mass sd went 0.92 → 0.99. No monotone per-pixel lever
  produces variation on a uniform flat-shaded surface under uniform ambient, which is why the bake
  is structural rather than a preference.
- 🔴 Quote shadow-mass `L*` and within-mass sd, never band share: a near-constant mass within half
  a point of `L*` 10 made the same change read 0.9% in one shoot and 29.0% in another.
- ⚠️ Contrast dominates the ambient fill: `ambient_light_energy` 1.4 leaves the mass at 8.59 and
  costs more massing flatness (`skyline` spread 38.2 against 39.0).
- ⚠️ The drive scene is not frame-stable (`t04.50` differs by 55% of pixels between identical
  runs). Grade drive frames on repeat-until-consensus; preview viewpoints are byte-identical.
- The rig adds ~7 `C*` of blue to everything (`Q36`).
- ⚠️ `P5-28c` moved `kerb` to 33.2% under `L*` 10 with no mean change; cause unidentified (`Q38`).

**See.** `Q33` · `Q36` · `Q39` · `Q27` · `Q26` · `Q38`

## `Q32` — `INFRASTRUCTURE` is *not* the brightest large object in its frame

**Status.** 🟢 Closed as wrong · **Owner.** `P3-9a`

Tinting `MARKER_STRUCTURE` refuted the claim: the class is 2.71% of its showcase frame, its
up/side faces render at `L*` 51.1 against a non-sky mean of 48.1, and its soffits already sit at
35.9. The pale beams in that frame are `BUILDING`.

- ⚠️ "No AO, so a soffit renders like a deck top" confuses ambient occlusion with `N·L`. A
  `structure_soffit_darkness` term was built, measured and reverted. Do not re-propose.
- True and recorded in `ART_DESIGN.md` as a known gap: the class takes none of the shader's
  surface treatment (everything is gated on `is_facade`).
- Tint the class before naming it (`Q28`, `Q36`).

**See.** `ART_DESIGN.md` "Infrastructure" · `Q28` · `Q36`

## `Q33` — Every authored colour is `material reflectance × exposure_anchor`

**Status.** ✅ Closed; the mechanism is superseded by `Q38` · **Owner.** `config.py`

Every authored colour is a cited diffuse `reflectance`; the one art-direction number is
`exposure_anchor`. Since `P5-28c` (`Q38`) the colours are reflectance-level, the anchor lives in
the lighting rig, and the check is `config.py:_check_reflectance` against each material's
`bounds:`.

- Why: a palette judged only against itself indicts its one correct member. The fix is an
  external referent — asphalt was right at 8.2%; kerb claimed 58.9% against concrete's 20–30%.
  Kerb-to-road reflectance is now 2.5:1.
- ⚠️ Enforced over the whole config, never per section: the kerb drifted 19 `L*` by living in
  `RoadSurface` while a re-exposure edited `BuildingStyle`.
- ⚠️ The five `height_bands` are the soft spot (49–62%); that opened `Q34`.
- `P5-28a`: `render_cool` read 60.1% against a cited 30–60%, so the colour moved one code
  (`#949995` → `#939995`) and the range was not widened.
- ⚠️ A one-code base change moves two or three channels through `with_hue`'s CIELAB round trip.
  `frame_stats.py`'s "Nothing moved — check the reimport" means "under the 0.5 `L*` bar" whenever
  `cmp` says the frames differ.

**See.** `ART_DESIGN.md` "The rule" · `Q31` · `Q34` · `Q36` · `Q38`

## `Q34` — Material is declared, not implied from height

**Status.** ✅ Closed · **Owner.** `config.py`

A top-level `materials:` table holds every shipped colour as `Material(name, colour, reflectance,
source)` (plus `bounds:` since `Q38`); `buildings:` and `roads:` reference by name, and
`material_assignment` draws per building over authored chroma rings and hue sectors. No ETL→game
contract bump: no output records a reflectance.

- Why not height: on the survey, height explains 0.9% of `L*`; the best geometric key 1.4%; five
  clusters on measured hue capture 72.4% of hue variance.
- ⚠️ The fallback is the height ramp, not the surveyed marginal: `facade_hue` is optional by
  contract, so a survey-less clone must build the same city.
- ⚠️ The draw conditions lightness on hue only; `with_hue` replaces `a*`/`b*` afterwards.
- ⚠️ Bin by authored chroma and hue-angle thresholds, never k-means: data-dependent centres shift
  per region.
- ⚠️ Refused: measuring material from the imagery. Texel GSD is 13–18 cm, and glazed-vs-solid
  must not be used raw — glass has 8–15% diffuse reflectance and would render towers near-black.
- ⚠️ The draw's seed is a `blake2b` stream uncorrelated with the jitter seed; a prefix-salted
  `crc32` correlates at +0.507.
- No spatial coherence: that is `Q35`.

**See.** `ART_DESIGN.md` "Material is not a function of height" · `Q33` · `Q35` · `Q37` · `Q34′`

## `Q34′` — The ring weights are re-derived by a tool, against `Q37`'s survey

**Status.** ✅ Closed by `tools/ring_weights.py` · **Owner.** `hong_kong.yaml`

Each bin's weights are the minimum-norm move from the shipped weights that makes its expected
reflectance equal the mean the height ramp gives that bin's buildings. Re-run on its own output the
tool proposes no move. Re-run it if the ramp or the survey moves.

- ⚠️ The minimum-norm rule fixes a free degree of freedom (three materials, two constraints); any
  other point repaints buildings for no reason.
- A large change in a bin's share does not imply a large change in its weights: `Q37` moved the
  near-neutral share eleven points and no weight by more than 0.06.
- ⚠️ `test_config.py`'s bound stays loose on purpose: the suite must run without the 4.9 GB
  survey. The tool is the real check.

**See.** `Q34` · `Q37` · `Q35` · `CONTRIBUTING.md` "Checks"

## `Q35` — A per-building material draw gives a salt-and-pepper skyline

**Status.** 🔴 Open · **Owner.** `buildings.py`, `hong_kong.yaml`

Neighbours draw independently, so adjacent blocks can land 13 reflectance points apart where real
blocks share cladding. The ring weights bound the average, not any pair.

- ⚠️ Hue does not supply coherence at ~1 km (0.5% of hue variance between the six sheets). Block
  scale is untested: the survey carries `sheet` but no coordinates.
- ⚠️ Grade from the street, not the skyline.
- Candidates, none scouted: a spatial hash on building position (~50 m cell); a block join from an
  external lot dataset (new source, new licence review); or accept it.

**See.** `Q34` · `Q27`

## `Q36` — Wan Chai's ground is paving, not soil

**Status.** ✅ Closed · **Owner.** `hong_kong.yaml`

The ground material is `concrete_paving` at 20.0% reflectance: a material is a claim about the
visible surface, and a built-up reclamation's surface is pavement. Ground patch `C*` 6.71 → 3.53
at unmoved `L*`. Supersedes `Q18`'s doubled chroma.

- ⚠️ Two individually correct changes were never graded together (`Q18`'s chroma, then `Q33`'s
  −18 `L*`). A verdict on config expires like one on a screenshot.
- ⚠️ The rendered-chroma null is not at the greyest hex: rendered chroma is roughly |warm albedo −
  blue illuminant|. Do not simplify toward neutral grey.
- Refused: terrain hue from the aerial JPEG (baked shadow in the albedo channel; hue near `C*` 6;
  needs `Q30`'s amplification). An x,y hue field (invisible or patchy). A hillside split on
  elevation or slope: only 9.77% of terrain is above 10 m, it renders 0.000% of the six fixed
  viewpoints, and the reachable high ground is 97.5% flat built-on land. If vegetation is wanted,
  the source is vector land-use polygons.
- 🟡 Still open, and `B3`'s: a 200 m expanse of one correct colour with nothing standing on it. No
  colour operation substitutes for objects.

**See.** `Q18` · `Q29` · `Q31` · `Q33` · `Q34`

## `Q37` — 10.0% of the façade survey is atlas filler, not a photograph

**Status.** ✅ Closed by `tools/facade_survey.py` · **Owner.** `buildings.py`, survey

222 of 2,214 rows of the old `facade_lab.json` were atlas filler (23 distinct greys), rendering
10.1% of buildings dead-neutral and binning them as neutral material. `tools/facade_survey.py`
replaced the table; the old script's sampling is unrecoverable, so the old table could not be
repaired (median `Δab` 1.04 against it; the guard alone accounts for 0.000). The imagery covers a
median 14.3% of each building's walls.

- ⚠️ A bright-tail estimator (median above the 65th percentile of `L*`) concentrates bright filler
  instead of diluting it; above ~35% filler by area the result is filler.
- ⚠️ The guard is structural — reject exact `R == G == B` texels or the atlas's modal repeated
  colour — never an enumerated list of greys. Rejecting only achromatic rows treats one building in
  seven of those affected.
- ⚠️ Repetition is the defect's signature, not achromaticity: two genuine photographs still read
  `C* = 0`. A future check should count identical rows.
- The near-neutral ring (`C* <= 5`) fell 51.6% → 40.5% of stock; `Q34′` re-derived the weights.
- ⚠️ Open side question: the survey averages in sRGB, ~4.9 `L*` from a linear-light mean. Change
  one thing at a time.

**See.** `Q34` · `Q34′` · `Q27` · `Q30` · `Q26`

## `Q38` — `exposure_anchor` is baked into `COLOR_0` at build time

**Status.** ✅ Closed 2026-09-08 by `P5-28c` — the exposure left `hong_kong.yaml` and is a Godot
global shader parameter set by the lighting rig, so a time of day is one number in one scene ·
**Owner.** night mode

What ships (`P5-28a`–`d`):

- `project.godot` declares `[shader_globals] exposure_anchor`; `scripts/world/lighting_rig.gd` sets
  it from an `@export` on `clean_daylight.tscn` and `golden_hour.tscn`, both **0.520**.
- Shaders read it after `vertex_srgb_to_linear`, never on a `.tres` colour: `city_facade`,
  `city_facade_clean`, `road_markings`, `tramway`, `vertex_albedo`, and `signs` behind a per-`.tres`
  `apply_exposure` that only `lamps.tres` sets (the sign livery is exempt). ⚠️ `city_facade_clean`
  reads it at both sites `COLOR` is consumed, including `Q45`'s vertex-stage CIELAB pane pull.
- `materials:` colours are reflectance-level; `city.json` `schema_version` 30 → 31, because a v30
  reader draws the city 1/0.520 too bright. `make_landmark.py` and `make_barrier.py` no longer
  import `load_config`.
- 🔴 `bounds:` is required on every material and is the whole check (`_check_reflectance`);
  without it luminance equals reflectance by construction. Correct a colour outside its bounds;
  never widen the bounds.
- `facade_hue.strength` is **3.0**, the user's pick from a sweep of 2.0–3.5. It is louder than the
  pre-un-bake look, not a restoration (2.5 reproduced that and was declined). Costs accepted: 7.8%
  outside sRGB, 5.50% jitter clamp. Distribution: `Q30`.

Traps:

- ⚠️ `landmark_vertex` and `barrier_vertex` replace the import hook's `BaseMaterial3D` branch. They
  must state `diffuse_mode` and `specular_mode` and linearise in the vertex stage; the residual is
  101 px at ≤ 2 codes on the skyline, not byte-identical.
- 🔴 Two clips. The gamut clip is `lab_to_srgb` inside `with_hue`, reported by
  `facade_chroma.clipping()`. The jitter clamp in `colour_for` is applied after `with_hue`, and no
  counter in the bundle sees it (the sweep's column came from a script). Levers: `strength`,
  `colour_jitter`.
- ⚠️ `clearance.wears()`'s exactness guard aborts rather than degrades: the brightest material is
  211 against the 240.6 admitted at jitter 0.06. A brighter ground material or raised jitter
  `SystemExit`s the clearance stage and three graders.
- ⚠️ A uniform luminance scale multiplies `C*` by `anchor ** (1/3)` (0.804 at 0.520), so an
  unexposed grader reads 1.24× more saturated, not less. `facade_chroma.py --shipped` applies the
  exposure itself; `--strengths` names a sweep, default (1.0, 2.0, 3.0).
- ⚠️ `Q31`'s `kerb` band shares moved (29.0% → 33.2% under `L*` 10) at unmoved mean `L*`. "Chroma
  reaching the tone curve" is measured false: the shares are identical across `strength` 2.0–3.0.
  Cause unidentified; the clips are a lead.
- ⚠️ The skyline camera does not settle by `t=0.8` (the tile streamer is still instancing). Shoot
  at `t=2.0` until a hash repeats, with a forced re-import per side.
- ⚠️ `asset_viewer.tscn` is the wrong instrument for an A/B: its free-look camera framed one pixel
  apart between runs. The drive scene's chase camera is on the physics clock.
- A shader global is tested by whether it moves pixels (`Q72`): at 0.5, 91.5% of the driven frame
  moves and 0 of 17,889 exempt bodywork pixels do.

Night mode's precondition is met; what remains is a look nobody has chosen (`Q26`).

**See.** `Q33` · `Q30` · `ART_DESIGN.md` "Lighting"

## `Q39` — `wall_sky_tint` is uniform across the city

**Status.** 🟡 Open · **Owner.** `Q31`

`city_facade_clean.gdshader` mixes toward `sky_reflection` by `fresnel * wall_sky_tint` with no
occlusion term, so a canyon-bottom wall takes the same sky bounce as a rooftop parapet — overstated
in exactly the shaded frames `Q31` reports. Free once a sky-visibility term exists
(`fresnel * wall_sky_tint * sky_vis`); it is that bake's second consumer, not a task of its own.

⚠️ Do not lower `wall_sky_tint` globally: it flattens the massing, the same trade as lowering the
ambient fill.

**See.** `Q31` · `ART_DESIGN.md` "Lighting"

## `Q40` — Can façade grammar be surveyed instead of hashed?

**Status.** ✅ Closed; its consumer is withdrawn by `Q102` (`TEXCOORD_1` removed, schema 20). The
findings stand. `tools/facade_unwrap.py` and `tools/facade_glazing.py` are kept with no consumer.

No building source publishes `use`, `cladding` or `year`; the only evidence is the individualised
set's photography. Measured shut, per-pixel statistics on it:

- **Grammar (fin / curtain / punched) is not derivable from an `L*` profile.** 12 faces graded
  against their photographs: 1 right, 8 wrong, 3 unsure. Structural, not a threshold problem: `L*`
  modulation measures materials not recession (depth is what a texture cannot see), reflections are
  most of the signal on glass, and one wall classified `fin` from W and `curtain` from S.
- **The bimodality dip cannot gate glazing.** Six sheets, 2,143 gated buildings, against `Q41`'s
  reader: best Youden J 0.100, and the conditional medians flip sign across sheets. Blank walls read
  more bimodal (median dip 0.484) than windowed ones (0.850) — an `L*` split cannot tell glass from
  shadow.
- **Per-chart atlas analysis is dead.** Only 15.2% of wall area (47 charts of 5,831) spans three
  bays and three floors; median building 0% analysable. Work in the world-space unwrap
  (metres across × metres up, 8 texels/m), never in atlas space.
- **No warm-glass palette extension.** Conditioned on reader-glazed, warm dark modes fall to 0/15 on
  `11-SW-9D` and 6% region-wide (`b*` p90 +1.27); the authored cool tints span the measured glass.

What held: tint is a real measurement conditional on glazing (dark mode bluer than light on 89% of
2,142 buildings, median shift −6.08 `b*`), and is 2-D `L*` × `b*` (PC1 68.9%, PC2 24.7%, `a*` 6.5%).
`B353771561001063A0` returns a 3.38 m floor pitch on three faces independently — see `Q42`.

⚠️ Traps for any successor instrument:

- The per-mesh, per-normal wall selection admits foreign geometry (trees, neighbours).
  Decontaminating moved the verdict on 19 of 51 buildings on `11-SW-9D` and 195 of 699 on
  `11-SW-14B`, in both directions. One sheet does not calibrate the region (51% vs 73% unimodal).
- Resolution confounds: below ≥ 10 tex/m "no windows" and "badly photographed" read the same.
- Otsu `eta` never goes low on a unimodal blob; it is not evidence.
- A classifier needs an `unknown` outcome: a vertical profile that refused to compute was read as
  "no banding", and an autocorrelation peak pinned at the minimum lag (1.375 m) was read as a bay.
- A moving-average detrend consumed the signal on elevations under ~13 m; a degree-2 polynomial fit
  costs no samples.
- Features visible to a reader are not thereby measurable by a statistic.
- Integer codes in a float32 vertex channel cannot be quantised to half-float (11 mantissa bits);
  a per-building-constant channel cost +0.24 MB of PCK, not the ~2 MB estimated.

**See.** `Q26` · `Q35` · `Q37` · `Q41` · `Q42` · `Q102`

## `Q41` — A vision reader recovers the grammar the statistic could not

**Status.** **Superseded by** `Q102` — withdrawn on cost at the user's call, not refuted.
`tools/facade_grammar.py`, its labels and the `TEXCOORD_1` codec are deleted; no inference API
dependency remains.

What was established, for anyone reopening it:

- A vision model reading `tools/facade_unwrap.py` elevations classifies grammar, including both
  buildings `Q40`'s statistic got wrong. Graded on 40 pre-labelled faces from two sheets against
  bars fixed beforehand: `claude-opus-5` strict 19/20, marginal 6/6, refusal 14/14, glazed 23/24;
  `claude-sonnet-5` 18/20, 6/6, 14/14, 24/24 and ran the region; Haiku 4.5 failed (strict 15/20,
  refusal 12/14). Labels were human spot-checked; none corrected.
- Region run: 2,214 buildings, 8,704 faces, 54% read, 80% of buildings with at least one read face,
  ~$21 via the Batch API. `punched` 67% of reads. 88% of reads low-confidence. Rider fields
  (`storey_count`, `emphasis`, `signage`) were advisory and never validated; `band_period_floors`
  almost never committed.
- Coverage bounds any such survey: imagery carries real texels on a median 14.3% of wall area, so
  many buildings must refuse, and a refusal falls back to the hash.
- The licence covers sending sheet imagery through a third-party API (reproduction within the
  grant, `LICENSING.md`); survey output is derived government data and is never committed.

⚠️ Design rules that made it safe, to reuse for any non-deterministic build-time input:

- The model is pinned; a model change is a graded resurvey, not a cache hit.
- Cache raw responses keyed by prompt hash **and** a hash of the encoded image. Keying on unwrap
  source would discard paid reads on a no-op refactor; keying on neither replays stale answers.
- A row cache that skips the unwrap is guarded separately by a hash of the code the images pass
  through — source-keying is right there because invalidation costs no API spend.
- Batch is transport only: same request bytes, results written into the same cache entries, tables
  authored by a zero-call replay. Re-derivation acceptance is the thresholds passing, not
  byte-equality.
- Collect extra fields in the validated prompt rather than later: a new field changes the prompt
  hash, which costs a new graded run plus a paid re-survey.

**See.** `Q40` · `Q42` · `Q102` · `LICENSING.md`

---

# Tasks

## `P0-1` — Building data is fully scriptable

**Status.** ✅ Done

`Q2`/`Q3`/`Q5` hold the claim. ⚠️ The CKAN resource list only points at interactive portals; the
portal's own Downloads panel is where the scriptable files are.

## `P0-3` — A scaffold is not a signed on-device build

**Status.** ✅ Done · `P0-3b` ⬜ Not started

Split into `P0-3` (imports clean, exports verified) and `P0-3b` (signed on-device builds, needing
Android SDK, Xcode, a signing identity and hardware). Android exports a 25 MB APK from the prebuilt
template with no Gradle or SDK; iOS fails only on the missing Team ID.

- ⚠️ `rendering/textures/vram_compression/import_etc2_astc` must be enabled or Godot refuses every
  arm64 export, Apple Silicon macOS included.
- `P0-3b` blocks the `P2-4` and `P2-6` reviews (feel under a thumb); not on the critical path.

**See.** `Q4` · `ARCHITECTURE.md` "Project settings"

## `P0-4` — Config declares its datum, not just its CRS

**Status.** ✅ Done

`hong_kong.yaml` declares `crs.geodetic` beside `crs.projected`; `config.py` refuses to load without
it. HK1980 and WGS84 differ by ~304 m on the ground here.

- ⚠️ `test_crs.py` asserting >250 m disagreement is a canary: if it shrinks, PROJ has fallen back to
  a ballpark transformation. The load-bearing test projects the published grid origin to the
  published false easting/northing, sub-millimetre.
- `always_xy=True` everywhere; `transformer()` is cached per CRS pair; `GameTransform` is
  pyproj-free; the origin is rounded to whole metres so a library upgrade cannot renumber tiles;
  `deck_height_m()` raises on an unmapped `ELEVATION`.
- ⚠️ Elevation-level keys reject `bool`: YAML 1.1 reads a bare `off:` as `False`, which equals `0`
  as a dict key and would silently redefine ground level.

**See.** `Q10`

## `P0-5` — The grey box cleared the handling and could not clear the premise

**Status.** ⚠️ Passed, conditional

The grey box passed what it could test and could not answer "is this a game?"; that became `Q8`,
closed later on the real city. Phase 1 was released because ETL output is a precondition for
knowing.

**See.** `Q8` · `P0-5a`

## `P0-5a` — Custom raycast on `RigidBody3D`, not `VehicleBody3D`

**Status.** **Superseded by** `Q50` — the shipped car is `VehicleBody3D`, on the user's instruction.
The measurement below is still true; `Q84` corrected the drift-window reading.

- `wheel_friction_slip` is isotropic, so a drift cannot break lateral grip without losing traction
  and braking. Measured: rear friction × 0.35 under throttle cost 30% of speed over 2 s (scrub
  0.151/s against a 0.080 target) at a 162.6° peak slip angle against a 14° threshold — a spin.
- `VehicleBody3D` is not broken under Jolt; it simulates and its wheel query API works.
- `VehicleWheel3D` simulates only under a `VehicleBody3D`. Neither model publishes per-wheel angular
  velocity (`Q85`); `get_skidinfo()` is real.
- Spring rate is specified as natural frequency in Hz so it survives a mass change, but static sag
  is `g_eff / (2πf)²`, so `gravity_scale = 1.6` deepens it 1.6×.
- ⚠️ The glTF importer turns a mesh into a `VehicleWheel3D` from its name suffix alone —
  `ARCHITECTURE.md`.

**See.** `Q50` · `Q84` · `Q85` · `P3-11`

## `P0-5b/c/d` — Five handling bugs no linter catches

**Status.** ✅ Done. The raycast-model numbers are superseded by `Q50` (`brake_force` is now in the
engine's units, 40.0); `rolling_resistance_mps2` 0.8 and `coast_drag_per_s` 0.05 still ship.

Each was found by measuring, none by static analysis: anti-roll signs inverted; coast drag divided
by `delta` (~35× too strong); steering inverted (tests only ever steered one way); wheel raycasts
accepted walls as ground; road slabs coplanar with the ground z-fought. The fifth: too little
speed-independent longitudinal force, so braking fell 36% from 65 to 4 km/h and a coast never
reached zero.

- ⚠️ A `Node3D`-typed `@export` does not resolve from a hand-authored `.tscn`; it reads null
  silently.
- `rolling_resistance_mps2` is capped at the deceleration that lands exactly on zero this tick
  (`|rolling_speed| / delta`); uncapped, a constant force reverses the car. The viscous term stays —
  it is what reads as engine braking at speed. Under 0.8 m/s² the taxi holds on grades below ~2.9°.
- ⚠️ `project.godot` does not override `default_linear_damp` (0.1), so the engine damps under the
  controller: measured decay 0.100/s with both dials at zero, 0.150/s at `coast_drag_per_s` 0.05.
  The dial is one third of the viscous total. One pedal serves brake and reverse below
  `STATIONARY_KPH`, which is why a coast that never stops is player-visible.
- 🔴 Measure drag and braking on `skidpad.tscn`, never on the city: a 0.14° gradient at 4 km/h is
  worth ~0.05/s, the whole quantity under test, and a downhill sample flattened the 36% brake
  falloff into a verdict that the user's report was wrong. It was right. A measurement that
  contradicts the user's direct experience is re-run on known ground before it is reported.

**See.** `P0-5a` · `Q50` · `GAME_DESIGN.md` "Controls"

## `P1-1` — The fetcher derives its own sheet list

**Status.** ✅ Done

`fetch.py` handles fixed-URL sources (roads) and index-derived ones (buildings); the property that
holds the download URL is config. Intersecting the region bounds with the 3,456-feature index
selects the sheets; nothing in config names them.

- Fetch-once, not fetch-if-changed: a re-run must not adopt upstream's new month. `REVISIONDATE` is
  per sheet, so a forced re-snapshot is 3.2 MB, not 265 MB.
- The API key is never written down; everything recorded passes through `redact()`.
- Bounds are reprojected before comparison, never compared across datums. Edge contact counts as
  overlap. Selecting zero tiles is an error.
- ⚠️ `read(amt)` returns `b''` on a premature close, so a short response must be checked against
  its declared length or the truncation becomes a permanent cache hit. A portal answering an outage
  with HTTP 200 and a JSON error body parses fine and selects zero sheets. One transient failure
  must not discard the whole manifest.

**See.** `DATA_SOURCES.md` "Access notes"

## `P1-2` — Vertex clustering, and meshes are assigned to tiles whole

**Status.** ✅ Done

Buildings are decimated by vertex clustering (keeps extruded footprints blocky; one number in
metres), not quadric decimation, and assigned to tiles whole.

- The cluster key includes the facing, or wall normals average into the roof. The cluster takes a
  representative position, not a mean. The ground alone takes `height_field=True` (`Q29`, `Q25`).
- Exception to whole-mesh assignment: elevated structures run up to 1,984 m in one mesh, so
  oversized meshes are partitioned by triangle — otherwise a viaduct vanishes or gives a 150 m tile
  a 2 km box.
- Georeference check: the tallest building converts back to 374.5 m at 22.28011 N, 114.17358 E
  against Central Plaza's published 374 m, a 19 m offset inside its footprint.
- ⚠️ Godot's glTF importer leaves `vertex_color_use_as_albedo` off (fixed by a post-import script
  wired as a project-wide importer default), and the colour accessor's `"normalized": true` is
  load-bearing. Either failure renders the whole city white.
- No glTF library: `pipeline/gltf.py` reads and writes the format directly.
- The terrain verdict "267 MB, unaffordable" was 224 MB of JPEG; superseded by `P3-10`.

**See.** `Q16` · `Q25` · `Q29` · `P3-10`

## `P1-3` — Three things the source forced on the road graph

**Status.** ✅ Done

`python -m pipeline.roads` reduces the geodatabase to the road graph (797 edges, 615 nodes, 217 turn
restrictions on Wan Chai when recorded).

- ⚠️ `ELEVATION` must not key nodes: all 36 endpoints where two levels meet are ramp touchdowns, and
  keying by level takes the region from 6 components to 24, cutting a 163-node elevated island
  adrift.
- Roads are clipped to the region (buildings are not): the geodatabase filters on bounding box, and
  14.2% of selected road length lay outside the region.
- The road dataset has no lane attribute on any layer. `lanes` has since become measured —
  `Q57`, `Q94`.
- Endpoints coincide exactly (nearest distinct pair 2.26 m), so snapping needs no tolerance but must
  be no finer than a millimetre, or Johnston Road disconnects at Fenwick Street.
- The geometry is over-densified (one 51.7 m centreline carries 54,330 vertices), so
  Douglas–Peucker is a correctness measure for the surface, and is iterative to avoid stack
  overflow.
- `EDGE1END` is a hint: 4 of 217 name the wrong end; taking the shared node resolves all.
- Not in the output: the turn layer's `EXC_VEH_TYPE` / `INC_VEH_TYPE`, `PART_TIME_REST`,
  `EFF_ALL_DAYS`. ⚠️ One restriction in the region excludes taxis, so the graph forbids a turn a
  real taxi may make — a schema change for `P3-3` / `P3-8`, noted in `DATA_SOURCES.md`.
- Open, recorded not fixed: `roads.py` reaches into `buildings.py` for `Placement` and
  `read_sheet`, and reads its terrain class from the buildings config section.

**See.** `Q9` · `Q11` · `Q12` · `Q13` · `Q57` · `DATA_SOURCES.md` "Roads"

## `P1-4` — The road surface is one mesh, capped per level, never merged

**Status.** ✅ Done. Widths and rails have since moved to `Q95` / `Q129`; the rule `surface` owns
the current ribbon.

- Junction caps are per elevation level (the opposite of how `P1-3` keys nodes): a cap is tarmac,
  and there is none between a street and the tunnel roof below it.
- Too-tight corners: hold the inner boundary still where it would reverse (0 folds, 93 collapsed
  quads of 5,188). Refused: simplifying harder (8 folds left) and capping width to the turning
  radius (pinches the carriageway to zero at 24 places).
- Every edge was extruded alone, which put kerbs mid-road on opposed pairs (33.0 km of 98.6 km) and
  let the convex-hull cap pinch bends to `cos(half the turn)`. Fixed by mitring through the cap:
  overlapping kerbs → 0, pinched nodes 8 → 1 (a 172° hairpin). A 0.15 m kerb riser is 83% of
  `suspension_travel_m` and it is in the collider.
- Through-ness is not a tuning value: two arms mitre up to 90°; three or more drop to 45°, because
  a sharp corner there is pavement.
- Refused: merging opposed pairs into one ribbon — needs polygon clipping and changes what
  `roadsurface.json` indexes. Only the kerb asks about its neighbours.
- ⚠️ A per-sample Python loop with `np.errstate` made the stage 8.3× slower with every check
  passing; vectorised 2.49 s → 0.36 s.
- Open: the cap carries no kerb and no lane coordinate (`fan` writes zero UVs).

**See.** `Q13` · `Q19` · `Q23` · `Q24` · `ART_DESIGN.md` "Roads"

## `P1-5` — Fare nodes keep the kerbside position

**Status.** ✅ Done

`pos` is the source position, not snapped: the kerbside is where the passenger stands, and the stop
point is derivable from `nearest_edge` + `edge_t` while the reverse is not. Only the height comes
off the road. `pickup` / `dropoff` are published because 66 of 275 points territory-wide are
drop-off only.

- ⚠️ The `Status_EN` category table is first-hit-wins over substrings, so rule order is
  load-bearing: `DF` before `PU/DF` files every pick-up as drop-off only and still yields a
  plausible `fares.json`. `load_city` refuses a table where an earlier rule always shadows a later
  one, and an unmatched category raises.
- ⚠️ `clean_text` normalises to NFC, not NFKC — NFKC rewrites the full-width brackets in Chinese
  names that go on the HUD. NFKC is used only for the null-sentinel comparison.

**See.** `Q14` · `Q15` · `DATA_SOURCES.md` "Fares and points of interest"

## `P1-6` — The manifest names the other documents, and the export stage checks them

**Status.** ✅ Done

`city.json` references rather than inlines, because each document is separately versioned.
`bounds_game` is the union of the content, not the region rectangle (`ARCHITECTURE.md`).

- The export stage validates what no single stage can see: a fare node naming a missing edge, a
  tile whose GLB was never written, a document left from another region, geometry outside bounds.
- A rebuild from an empty `out/` is byte-identical apart from `generated_utc`, which is what makes
  `diff` answer "did this change anything?".
- The orchestrator calls each stage's own `main` with the documented arguments — no second code
  path.

**See.** `ARCHITECTURE.md` "Data contract" · `Q16`

## `P1-7` — The manifest is the only route to the tiles

**Status.** ✅ Done · Phase 1 gate passed

- ⚠️ `DirAccess.get_files_at` returns an empty array in an exported build (`res://` is a PCK), so a
  directory listing renders an empty city with no error. The manifest is the only route.
- `tools/verify_city.gd` holds each imported mesh to the `aabb` `export.py` recorded, within 1 cm;
  proven non-vacuous by nudging one tile 0.5 m.
- ⚠️ `--headless` has no frame, so it cannot see z-fighting. A windowed run can: render, nudge the
  camera 2 cm, diff (0.071% of pixels on Hennessy Road when recorded). One camera, evidence only.
- `tools/sync_generated.sh` copies what `city.json` names, which also deletes tiles a previous
  build left behind.

**See.** `ARCHITECTURE.md` "Build pipeline" · `P1-6`

## `P2-1` — The city streams, and LOD is per mesh class

**Status.** ✅ Done — review passed

`CityStreamer` loads tiles on a worker thread by published `aabb`. `class_lod_cell_sizes_m` holds
`INFRASTRUCTURE` at `[0.0, 0.5, 1.0]` against the building default `[0.0, 1.5, 4.0]`.

- Clustering merges the top of any structure thinner than the cell into its underside (a 0.8 m deck
  goes 12 triangles → 2 at a 1.0 m cell). Bucket by class, collapse each at its own cell, then
  merge — still one mesh and one draw call per tile. Cost +3.6% visible triangles; an outright
  exemption was refused at +20% / +57%.
- Resident triangles are reported, never gated: the budget is 300k visible, and the streamer culls
  to a disc where the renderer culls to a cone (402k resident drew as 240k visible).
- `TileStreaming` in `scripts/core/` is pure (`AABB` in, int out), so a distant tile cannot be
  rejected after loading.
- Towers ≥100 m keep 36% of triangles at LOD1 against 44% for the rest; `ART_DESIGN.md` says why
  they still read.
- No landmark LOD key: heroes never pass through `buildings.py`, which only removes (`P3-6`).
- ⚠️ A mutation that orphans a local fails to parse (`unused_variable` is an error), `quit(1)` never
  runs and Godot exits 0. Only `tools/check.sh` can fail. Compare before/after at the same places.

**See.** `Q16` · `Q28` · `ARCHITECTURE.md` "Runtime systems"

## `P2-2` — Publish the derived width, not the widening rule

**Status.** ✅ Done — review passed

`surface.py` records the half-width it draws and `export.py` carries it into `city.json`, so the
game knows the tarmac it drives on. Refused: publishing the widening rules (two implementations of
one rule across the contract) and mirroring the factor in a `.tres` (drift). Reading lanes from
`TEXCOORD_0` answers the inverse question and is `(0, 0)` on caps. ⚠️ Level-0 half-widths have new
rules since `Q129` — rule `region`.

- The nearest-edge query is gated on p99 over a region-wide 10 m lattice (45 µs against 1 ms), not
  max (44–229 µs across runs) and not a road-only probe: misses mid-block are the expensive
  population and a road-only probe understates the worst case five times.
- ⚠️ `RoadGraph.shared()` is a weak cache on a `RefCounted`; consumers must hold it in a member or
  it re-parses.
- Only level-0 segments enter the spatial index (`Q13`); `polyline_of` serves every edge.
- ⚠️ `str(null)` in Godot is `"<null>"`, so an `is_empty()` guard never fires on `{"en": null}`
  (74 of 797 edges).

**See.** `Q13` · `Q23` · `ARCHITECTURE.md` "`roadgraph.json`"

## `P2-3` — The start line is queried, not written down

**Status.** ✅ Done — review passed

`RoadSpawn.at_fare_node` resolves a fare node through `RoadGraph`; `basis_facing` uses
`Basis.looking_at`. The heading is not passed to the query — the street decides which way it runs.

- ⚠️ A transposed basis mirrors the heading about world −Z: 180° wrong on an east-west street and
  0° on a north-south one. `verify_spawn.gd` builds the transposed basis and requires it to fail,
  with a 10° floor on the discriminating angle.
- ⚠️ Autoloads are not registered under `--script`; a tool touching one errors yet can print `ok`
  and exit 0. `tools/check.sh` greps stderr as well.

**See.** `P0-3` · `ARCHITECTURE.md` "Coordinates"

## `P2-5` — Buildings get collision from a mesh name

**Status.** ✅ Done — review passed

`buildings.py` names its finest tier `<tile_id>-col`; the importer builds a `StaticBody3D` with a
`ConcavePolygonShape3D` at import time, so the collider is the mesh. Only tier 0, and
`verify_tiles.gd` asserts both directions. Cost +5.17 MB of PCK (21.10 → 26.27).

- ⚠️ `P2-6` must re-measure hitching: instantiating a tile now registers a trimesh with Jolt on the
  main thread, and "no hitching" was accepted before that cost existed.
- ⚠️ A capability named only in a design doc has no owner; the collider fell between `P2-1` and
  `P2-5` and the region shipped without it.
- ⚠️ An inline `{}` fallback is untyped; the script error left `_init` before `quit()` and the tool
  hung. `verify_spawn.gd` refuses on `has_carriageway_widths()`, which also catches an empty table.

**See.** `Q19` · `Q20` · `P2-1`

## `P2-7` — The off-grade carriageway lies on its structure

**Status.** ✅ Done — review passed

Claim and residual are `Q20`; width is `Q23`; ramp classification is `Q13`. Rule `deck` owns the
current checklist.

- Deck sampling: there is no parapet to subtract (lips sit off-centre at ±3 to ±6 m); take slab
  clusters plus continuity, not the nearest hit (the sampler hits top and underside of one slab,
  spread 1.7–2.2 m); the terrain gate is not a minimum clearance, because ramps touch down.
- ⚠️ `INFRASTRUCTURE` stops being modelled where a ramp reaches grade, so a `terrain + 6.0`
  fallback rebuilds the cliff. An uncovered station interpolates the deck either side.
- `build_region` is two passes: whether a level-0 edge sits on a ramp depends on every edge being
  placed. `deck.clearance_m: 0.20` is a wearing-course layer sized by the 0.5 m decimation lifting
  the deck a median +0.041 m; `deck_error.py` subtracts it.
- ⚠️ Grader traps (`tools/deck_error.py`, `tools/overhang.py`): `colour_for` jitters every class, so
  match a class as a ray through its base colour, not a value; drop the underside winding; do not
  sample `roads.glb`'s own vertices (they sit at the overhanging edges — that is `Q19`, not `Q20`);
  measure coverage against what the centrelines asked for and fail below 90%, or a partial break
  is silent; never make the probe depend on the drawn width it grades.
- ⚠️ The ETL's own error column asks the same `HeightField` that produced the heights; it validates
  the harness only. Neither grader is in `check.sh` — they need a built region.
- ⚠️ A `deck:` block that is empty, `.nan`, `.inf` or carries an unknown key is refused; each would
  otherwise load and produce output identical to a city that never asked for deck sampling.
- The schema-bump rule (`ARCHITECTURE.md`) comes from here: `roadgraph.json` → 2 because
  `polyline.y` changed meaning with no field change; `roads.glb` did not bump.

**See.** `Q13` · `Q20` · `Q21` · `Q22` · `Q23`

## `P3-7` — Window bands are procedural, and the storey height was measured

**Status.** 🟡 Awaiting review

`city_facade.gdshader` bands façades in world space from a surface marker and per-building phase in
`TEXCOORD_0`: no texture, no extra draw call, +4.01 MB of PCK, `city.json` 4 → 5.

- Storey height 2.8 m, measured by autocorrelation down wall textures (median floor pitch 2.77 m,
  column pitch 2.42 m); the 3.2 m guess is five floors of error at 40 storeys. `Q48` holds the
  instruments that disagree.
- ⚠️ `window_opacity` 0.62 stands: judged too strong by eye, the rendered frame measured 0.107
  against 0.126 in the photographs.
- ⚠️ A statistic that lands exactly on a search bound is reporting the bound (first answer:
  2.00 m). Detrend and take a local peak.
- `mesh.merge` refuses textures, not UVs: UVs without a texture are a shader coordinate.
- ⚠️ Marker and phase share one float; the phase is quantised to 1/256 so `marker + seed` never
  rounds onto the next marker. The test brute-forces all 768 combinations.
- ⚠️ The glTF material name `city_facade`, `generated_scene_import.gd`'s dispatch and the shader
  must agree, and a broken link renders flat vertex colour silently. `verify_tiles.gd` asserts the
  `TEXCOORD_0` format and the resolved material path.
- The marker derives from the palette; `FACADE` is the fallback, so a new massing class bands
  until given a flat colour.
- Float32, not `unorm16`: ~2 MB is available there if a later region is short.

**See.** `Q26` · `Q28` · `Q48` · `ART_DESIGN.md` "The window-band shader"

## `P3-7a` — The task closes at what was judged, and the riders are gated on the look

**Status.** ✅ Closed as shipped — `W1` (`Q44`), `W2` (`Q45`), `W3` (`Q46`) landed and were accepted.
The `W4`–`R4` continuation is **superseded by** `Q102` (reader, `survey_apply` and the quiet tier
removed).

Measured, for anyone reopening the riders: `R4` failed its pre-fixed bar (|err| p50 10.76 m against
2.8, Spearman ρ = 0.076); `band_period_floors` committed 0/25; `R1` has no hand labels; `R2` meets
`Q48`'s unreconciled 2.8 / 3.38 / 3.32 / 3.28. Overrides are never the systematic fix: 771
buildings refused grammar.

⚠️ A "lands dark behind a switch, parked look byte-identical" criterion proves nothing once the
switch is permanently off — a rider that draws nothing passes it.

**See.** `Q26` · `Q42` · `Q47` · `Q48` · `Q102` · `P3-7`

## `P3-10` — The ground is a mesh class, and it collides

**Status.** 🟡 Awaiting review

Terrain is one more entry in `buildings.classes`: the tile's single material, no draw call,
+87,649 triangles at LOD0, PCK +4.56 MB (27.73 → 32.30) — nearly twice the geometry-only
estimate; the collider is the difference, not separately measured.

- It collides by the user's call, and because `_write_tile` names the merged tier-0 mesh
  `<tile_id>-col`. ⚠️ Any class added to `classes` inherits tier-0 collision.
- `ground_sink_m: 0.20` is the shallowest value passing both gates (carriageway area proud: 0.00 →
  47.5%, 0.15 → 5.2%, 0.20 → 3.3%, 0.35 → 1.2%); deeper shows a gap under a 0.15 m riser.
- The residual proud ground is `Q24` (chord error between polyline vertices), not decimation, sink
  depth or tunnel portals — each measured and rejected. ⚠️ Probing at polyline vertices reads clean
  by construction; probing between them changed the answer sixteen-fold.
- ⚠️ `tools/ground_clearance.py` gates on the points the road's height was sampled from; the
  all-cells headline also carries `Q24` and is a regression bar. Do not deepen the sink to fix it.

**See.** `Q18` · `Q24` · `Q25` · `Q29` · `ART_DESIGN.md` "Ground"

## `P3-11` — The taxi is generated, and the chassis generates it

**Status.** ✅ Passed review 2026-09-06

`tools/make_vehicle.py` generates `taxi_body.glb` and `taxi_wheel.glb` around the wheel hardpoints
in `game/scenes/vehicle/taxi.tscn` (`VehicleWheel3D` nodes since `Q50`) and `handling.tres`. The
scene is the authority; a mesh built to its own wheelbase would look right and drive to the old
tuning.

- Rounded by chamfer, never smooth shading: faces stay flat. `corner_cut_m = 0` yields the cheap
  square car for `B3` traffic; detail knobs are `Proportions` fields. 1,168 triangles in scene
  against `ART_DESIGN.md`'s 800–2,000.
- Untextured: plates are flat colour, white front and yellow rear. `BADGE_GREEN` takes the palette
  to seven against `ART_DESIGN.md`'s 3–5.
- ⚠️ A guard is only as good as the copies it knows: wheel meshes once carried a fourth copy of
  `suspension_rest_length_m` the guard never looked at.
- ⚠️ `face_inset_m` is not monotonic; `_seated_depth` must sample all three profile points. Known
  limit: a fixture outboard of the corner chamfer floats up to 10 cm clear of the paint.
- ⚠️ Any test over a filtered set needs an assertion that the filter found something; a test that
  re-derives the formula cannot fail.
- ⚠️ A note that a feature is in the wrong form means change its form, not delete it.
- ⚠️ Features of 16–150 mm do not read from ~8 m; make them read rather than adding more. The
  rocker strip and valance are unjudged: the chase camera never shows the flank.
- ⚠️ The visual body is larger than the box collider; the roof can pass under geometry the collider
  would stop. For `P2-6`.
- ⚠️ `drive.sh` renders whatever is already imported. Run `godot --headless --path game --import`
  after rewriting a `.glb`; a pixel-identical frame more likely means the change never arrived.

**See.** `P0-5a` · `Q50` · `ART_DESIGN.md` "Vehicles" · `ARCHITECTURE.md` "The importer can
reinstate `VehicleWheel3D`"

## `P3-6` — Two heroes replace their source meshes, and the contract is the deliverable

**Status.** 🟡 HKCEC passed the user's review 2026-09-06 · two of five shipped (HKCEC mesh-sourced,
Central Plaza generated) · Central Plaza not yet judged; Hopewell, Times Square and the government
slabs not built

**Contract.** `landmarks.json` is assembled by `export.py` from the config's `landmarks:` block,
named in the manifest, keyed by building stems. Placement is authored in the projected CRS;
`rot_y_deg` is a compass bearing with one conversion site (`generated_landmarks.gd::placement_of`).
`city.json` 6 → 7 (landmarks) → 8 (`landmark_assets`); `landmarks.json` 1 → 2 (`triangle_budget`
per entry, read by `verify_landmarks.gd`).

- Exclusion is enforced from two sides. Identity: `export.py --check` holds config stems and
  `buildings.json`'s recorded exclusions set-equal in both directions, and holds the config asset,
  `landmark_assets.json` path and manifest list equal. Geometry: `verify_landmarks.gd` probes
  tier-0 tiles inside each excluded footprint's interior core (half the plan extents, floored 16 m
  above base), because the full AABB is honestly occupied at its rim by neighbours.
- `buildings.py` only removes, and records `excluded_bounds` there because identity dies at
  `merge`. ⚠️ `export.py` adds each `excluded_bounds` back into `bounds_game`, or the bounds
  contract past the hero. The placed-model check allows 15 m of overhang.
- Central Plaza stays generated (`tools/make_landmark.py`): reproducible from a fresh clone, a
  byte-comparison test catches a stale model, review happens in a diff. The source captures its
  crown and mast badly.
- Vertex-coloured only; light texturing is deferred, not refused (user call, 2026-08-12). Hero
  colours are checked against the live `exposure_anchor` (`Q33`, `Q38`). `landmark_vertex` is owned
  by `pipeline/landmarks.py` and imported by the generator.
- HKCEC is Phase 2 plus the atrium link only; the Phase 1 podium (`B358611580502063`) stays
  generated massing.

### Amendment — the HKCEC hero is the source mesh, repainted (2026-08-12)

Three review rounds each moved the generated hero toward the source mesh, and the user judged the
source superior; the generator's HKCEC half is deleted. `pipeline/landmarks.py` (a stage after
`buildings`) extracts stem `B358761603301063` from sheet `11-SW-9D`, keeps source orientation
(`rot_y_deg` 0.0), slices every triangle at the ribbon elevations (`mesh.slice_horizontal` — crisp
vertex-colour bands need real edges), repaints, welds with colour in the key (`mesh.weld`), and
writes to `assets/generated/landmarks/`.

- ⚠️ A repainted government mesh is government-derived data (hard rule 7): gitignored, never
  committed. The paint is config — a `source_paint` block on the landmark entry, materials by name
  into `materials:`.
- The classifier: roof and soffit are seeded by normal thresholds and grown across edges meeting at
  less than `crease_deg` (35°), so a steep roof roll stays roof. `reference_texture` — the
  individualised `…A0` variant's photo on identical geometry — vetoes a ribbon strip unless it
  reads darker than the same wall half a pitch above and below. Local contrast, because baked sun
  and shade span 0.03–0.66 luminance; decided strip-wise, because per-triangle verdicts made
  dashes. The texture is consulted and discarded; Pillow stays a dev extra behind a lazy import.
- Ribbons sit at constant absolute elevations measured off photos by pixel profile: 15 m + k·4.8 m,
  1.5 m thick, 10 strips. The real elevation is pale panels with thin dark ribbons under a darker
  roof (`panel_pale`, `roof_grey`).
- Measured: source 41,273 triangles → 99,577 shipped, budget 120k; walls-only slicing (90,171) was
  refused for its T-junctions. PCK 33.85 → 38.67 MB.
- ⚠️ Landmarks sit outside the streamer and are always resident: resident ceiling ≈ 380,700 (tile
  worst case 280,783 + heroes). The 300k visible budget was not re-measured; `P2-6` should measure
  a frame under HKCEC first, and the next always-resident landmark reopens this arithmetic.

**See.** `ARCHITECTURE.md` "landmarks.json" · `ART_DESIGN.md` "Hero buildings" · `Q33` · `Q38` ·
`Q47` · `P3-11`

---

# Standing decisions

## Foundations

**Status.** Standing.

- **Engine: Godot 4.7, Mobile renderer, Jolt.** Commercial store target: native mobile performance
  against Android WebView GPU throttling, one codebase for mobile, desktop and a web demo.
- **Language: GDScript, not C#.** C# web export is unsupported and Android/iOS export is
  experimental; the complex code is in the Python ETL anyway. The performance escape hatch is
  GDExtension, not C#.
- **Targets: mobile + desktop/Steam.** Gamepad/keyboard layer, resolution-independent UI, desktop
  LOD tier, Steam build path — ~15–20% overhead, accepted.
- **Region: Wan Chai → Causeway Bay**, over Tsim Sha Tsui and Central: a natural circuit, diegetic
  map edges, real grade separation without Central's multi-level data risk.
- **Building source: the non-textured 3D Visualisation Map, never photogrammetry** (hard rule 1:
  ground gaps, level differences, baked vehicles; decimation gives blobs, not low-poly).
  ⚠️ 3D-BIT00 Level 1 was named here and never fetched; iB1000 took its place (`Q47`, `Q100`).
- **Art direction: accurate city, toy vehicles.** Recognition is the product, charm comes from the
  cars. Measured on the open-road frame: taxi red `C*` 86.5 against a frame median of 7.5 and a
  city 99th percentile of 39.8.
- **Monetisation: free download + one-time unlock, deferred to launch.** Not F2P (2–5% conversion
  needs volume this TAM lacks); not paid-upfront (a free slice is the marketing). Wan Chai must be
  standalone-playable.

**See.** `ARCHITECTURE.md` · `ART_DESIGN.md` · `GAME_DESIGN.md`

## Region bounds are WGS84, by measurement

**Status.** Standing.

The bounds in `hong_kong.yaml` are WGS84. HK1980 versus WGS84 is ~304 m here and the two readings
select different sheets (WGS84 gives a contiguous `11-SW` block; HK1980 swaps two of six). Sheet
`11-SW-10C`'s buildings match the WGS84 projection to metres; HK1980 is out by ~250 m.

**See.** `P0-4` · `DATA_SOURCES.md` "The datum of these bounds is load-bearing"

## Licensing

**Status.** Standing — `LICENSING.md` is the policy.

- Code GPL-3.0-or-later, hand-authored assets CC BY-SA 4.0, generated city data stays under the
  government terms and is never committed. Contributions are inbound MIT.
- Why inbound MIT: GPLv3 cannot ship through the App Store, so store builds need a proprietary
  grant, which needs one copyright owner. MIT permits sublicensing with less friction than a CLA.
  ⚠️ No retrofit once a contributor declines.
- The government grant is permissive (commercial use explicit, no quota or volume cap), but
  attribution must acknowledge ownership of the intellectual property rights and name both portals
  (hard rule 6).
- ⚠️ False alarm, do not re-raise: the grants lack "adapt"/"modify"/"derivative". For artistic works
  the restricted act is copying, which covers 2D↔3D transformation and is granted as "reproduce".
- Landmark depiction, not adaptation, is the top item for legal review.

**See.** `LICENSING.md` · `CONTRIBUTING.md` · `DATA_SOURCES.md` "Licence"

## Genre direction

**Status.** Standing.

| Reference | Contributes | Landed in |
|---|---|---|
| *Crazy Taxi* | The loop — fare combo, session timer, arrow, three-minute sessions | The design |
| *Midtown Madness 2* | Real shortcuts over invented ramps, tone, drivable roster | `GAME_DESIGN.md` |
| *Forza Horizon* | The losable style chain, scoreable traffic | `GAME_DESIGN.md`; `B3`/`B4` |
| *Sleeping Dogs* | Recognisable HK; signage density is said to carry it — untested here | `P3-9` |
| *Burnout 3* | Traffic as reward — near miss, oncoming lane | `P3-2a` |
| *Art of Rally* | Flat-shaded untextured terrain as a finished look | `Q18`, `P3-10` |

- No open-world structure survives a 1.5 km² region (a checkpoint race across it is 60–90 s). The
  fare loop re-randomises routes through the same area, which makes a small map an asset.
- ⚠️ Plan-ordering trap: a unit whose acceptance depends on a capability scheduled after it.
  Traffic only reads as opportunity when threading it pays, so near-miss (`P3-2a`) moved into `B3`.
- Refused: wheelspins and randomised rewards (anti-goal); live-service/always-online (hard rule 2);
  licensed-car collection as progression; scattered absurd-geometry ramps (`P3-9` would pay in
  full).

**See.** `GAME_DESIGN.md` · `PLAN.md`

## `P3-11c` — Gloss is priced per surface, and the gradient is what sells it

**Status.** 🟡 Awaiting review · **Owner.** `P3-11`. Shipped in `vehicle_body.gdshader`,
`vehicle_body.tres`, `scripts/vehicle/sun_glint.gd` and the `UV.y` marker from
`tools/make_vehicle.py`; graded on the `taxi` audit frames (`t01.20` shade, `t04.50` sun) and, for
heading-dependent terms, a skidpad circle.

- The car has gloss on glazing, lenses and paint, each at its own strength over a shared sky
  gradient; the facades already had it (`city_facade_clean`).
- 🔴 Uniform gloss on paint is refused: `roughness 0.9 → 0.25` took red `C*` 79.06 → 70.08 (hue
  −7.9°) in sun while `L*` rose. With no SSR or probes on Mobile a specular lobe samples flat
  ambient — a sky wash, `Q27`'s albedo-independent light. Gloss on paint is priced, not refused
  outright: at the shipped `C*` 71.63 the taxi is still 9× the frame median.
- ⚠️ A shader, not a material: the body is one merged primitive holding seven colours and a
  `StandardMaterial3D` has one roughness per surface.
- Shipped vs the matte build: red `C*` 79.06 → 71.63 (sun), glazing `L*` 0.52 → 9.28; 0 pixels
  moved outside the car; one draw call, one material.
- Payload: `floor(UV.y)` is the surface marker `PAINT` / `GLASS` / `LAMP` / `TRIM`; `UV.x` is the
  lamp circuit (`P3-11d`). `TRIM` shares paint's branch and stays separable for later brightwork.
  ⚠️ Not `COLOR_0.a` (`ARCHITECTURE.md`).
- ⚠️ Colour is not materiality: `LAMP` and `AMBER` swatches are also the plates and roof sign, so
  lenses are marked by part name (`Q43`'s collision). `GLASS` and `SILVER` stay colour rules.
- `SILVER` was authored blue (`b*` −3.56); now `(175,171,166)`, `b*` +3.07, `L*` held at 70.17.
  Fixed at the colour because `SILVER` is also the wheel hubs, which get no shader.
- The red tail lens on red bodywork is not separable by shading (`L*` +0.77 / +0.41); recolouring
  it and faking the removed bezel are both refused. `P3-11d` answers it by lighting the lens.
- ⚠️ Every failure is silent (a missing material name leaves the body on its `BaseMaterial3D`).
  `TestSurfaceMarkers` holds the ETL end, `verify_vehicle.gd` the engine end; only a render plus
  `grep -i "shader error"` proves the shader compiled.
- ⚠️ `P3-9a` risk: the red identifies 紅的. If recognition scores poorly, `paint_reflect` /
  `paint_roughness` is the first dial to try.

**See.** `ART_DESIGN.md` "Vehicles" · `Q27` · `Q31` · `Q43` · `P3-11`

## The reflection needed a gradient, and strength was never the variable

**Status.** Part of `P3-11c`.

- A single flat reflection colour reads as a swatch at every strength (faint at 0.14, painted-on at
  0.34). The reflected ray's elevation picks between `sky_zenith`, `sky_horizon` and
  `ground_reflection`; glazing `L*` sd went 0.05 → 6.35 (`t01.20`). `glass_reflect` ships 0.45.
- ⚠️ The gradient is yaw-blind: `bounced.y` is invariant under yaw, so only roll and pitch move it
  (skidpad: glazing `L*` 23.85 → 27.87 across headings). A steering-responsive term must be
  rotationally asymmetric about the vertical — the sun glint below.

## The clearcoat, and the correction it forced

**Status.** Part of `P3-11c`.

Paint takes the same gradient at low strength through a near-zero `paint_face_on` (0.06), so a
panel square to the camera keeps its colour. The cost is roughly additive in reflect and roughness
(red `C*` at `t04.50`, `fresnel_power` 4.0): 79.06 matte → 73.65 at `0.12 / 0.9` → 69.86 at
`0.12 / 0.55`. Ships `paint_reflect 0.12`, `paint_roughness 0.55`; `0 / 0.9` is the matte car. One
file, no rebuild.

## Fresnel is not decoration here, and tightening it refunds a fifth of the price

**Status.** Part of `P3-11c`.

- 🔴 Fresnel is what makes the clearcoat affordable: forced to 1.0 the paint loses a further `C*`
  13.75 (69.86 → 56.11).
- `fresnel_power` 4.0 → 6.5 (shipped) gives back `C*` +1.77 (→ 71.63) for −0.06 glazing `L*`; the
  net price is −7.43.
- A rim light was held, not refused: nothing measures a silhouette problem, and it spends `Q27`'s
  additive-light budget. Night (`Q26`) is the frame that would justify it.

## The sun glint, and why `SPECULAR` could not be it

**Status.** Part of `P3-11c`.

- 🔥 `SPECULAR` 0.5 → 0.9 refused: glazing mean `L*` +5.8 while p99 spread across headings moved
  only 2.69 → 3.54 — a wash, because it scales ambient specular too — and paint lost a further
  `C*` 3.08.
- Shipped: `pow(dot(bounced, sun_toward), glint_sharpness)`, `glint_strength 0.4`, sharpness 24.
  Skidpad glazing `L*`: +0.01 at one heading, +6.03 at another; the audit cameras are unmoved.
- ⚠️ `sun_toward` is fed by `sun_glint.gd` from the scene's real `DirectionalLight3D`, never
  authored in the `.tres` — a second copy of the rig's rotation drifts silently.
- ⚠️ `sun_glint.gd` finds the sun from `get_tree().root`, not `current_scene`: `driver.gd`
  `add_child`s the scene and nothing sets `current_scene`. Tell of a term that never ran: numbers
  byte-identical to the baseline.
- 🔴 Before a second vehicle, move `sun_toward` to a global shader parameter set once by the world
  scene; per-vehicle `SunGlint` nodes repeat the tree walk and the write into one shared `.tres`.
- ⚠️ On flat panes the glint is per-facet — the pane flashes rather than a spot sliding. Strength
  1.1 blew the backlight to near-white.
- ⚠️ Measurement masks come from the baseline frame and apply to both sides.

## `P3-11d` — The lamps switch, and that is what finally separates the red lens

**Status.** ✅ Passed review 2026-09-06 · **Owner.** `P3-11`. In `tools/make_vehicle.py`,
`vehicle_body.gdshader`, `vehicle_body.tres`, `scripts/vehicle/vehicle_lamps.gd`,
`vehicle_controller.gd`.

- `floor(UV.x)` is the switched circuit: `NONE` / `BRAKE` / `REVERSE` / `INDICATOR_L` /
  `INDICATOR_R`. A second channel rather than more `UV.y` markers, because a lit lens still wants
  lens shading. Left and right are separate circuits
  (`test_the_indicators_are_split_left_from_right`).
- `LAMP_CIRCUITS` is keyed on full part names (`_indicator` / `_reverse` / `_brake`). ⚠️
  `_check_wiring` raises in the generator, because `CIRCUIT_NONE` is valid and a lens that loses
  its key ships dark for ever.
- ⚠️ The circuits are `instance uniform`: `vehicle_body.tres` is shared, so a plain uniform puts
  the whole roster on one brake pedal. `vehicle_lamps.gd` reads the car, never `InputRouter`.
- `VehicleController.is_braking()` / `is_reversing()` state the pedal rule once (brake above
  `STATIONARY_KPH`, reverse below). At a standstill with the pedal held the reverse lamps light.
- Emission normalises the lens hue and discards its level, so the high-level brake lamp is authored
  `DEEP_RED (58, 10, 12)` — an eighth palette colour, granted because its darkness is the feature —
  and burns like every other lens. It is seated `FIXTURE_PROUD_M` clear of the opaque backlight.
- ⚠️ `lamp_emission` 1.6 is the knee. ACES desaturates a clipped channel: strip `C*` 56.44 at 1.2,
  44.34 at 1.6, 31.81 at 2.3 (a white lamp with a red glow). Unlit `L*` 2.29 → lit 72.72.
- Indicators: threshold 0.35 of the lock available at that speed, plus a hold (`steer_hold_s`, now
  0.3 s — `P3-11f`); without the hold the tail strobes through every correction. Swapping sides
  restarts the hold.
- Head and fog lamps were `CIRCUIT_NONE` here. **Superseded by** `P3-11e` for the front lamps.

**See.** `P3-11` · `P3-11c` · `P3-11e` · `Q26` · `Q27`

## `P3-11e` — The front lamps answer to the light, not to the driver

**Status.** 🟡 Awaiting review · **Owner.** `P3-11`. Night path untested until `Q26`'s rig exists.

- Side lamps (`foglamp_*` parts, named for position) light in shade; main beams when the sky
  overhead is blocked or the rig is night. A `SUN` / `SHADOW` / `DARK` ladder from two raycasts.
  Cover is tested before shadow — under a deck both hit.
- Tunnel trigger is "sky overhead blocked" (level −1 is not drivable, `Q21`); proven under the
  HKCEC deck. Night is `read_rig` reading the real `DirectionalLight3D`: energy ≤ `night_energy`
  (0.05) or sun at/below the horizon. ⚠️ A night rig must dim its key light, not delete it — a
  missing sun reads as "no rig", so headless loads are not put on main beam.
- Two lens pairs, not one at two levels: a fraction of `lamp_emission` 1.6 falls under the 1.0 glow
  threshold and carries no bloom. ⚠️ Side lamps stay lit under main beams (handing over reads as a
  flicker).
- Thrown beams: two `SpotLight3D`s in `taxi.tscn`, full on `DARK`, `sidelamp_beam` 0.3 of energy
  and reach on `SHADOW`, hidden on `SUN`. One central spot was refused on the look. The scene owns
  brightness and reach; the script reads them once and only scales.
- ⚠️ `spot_angle` is Godot's half angle and the cone must not reach above horizontal: 14° down
  against 13° puts the top edge 1° below. 13° also keeps the two pools apart to ~2.5 m (lamps
  0.58 m off centre). `light_projector` for a sharp cutoff is refused — the bundle ships 0 images.
- ⚠️ Beams read the lighter of held and current state; lenses read the held state. A beam must
  never outlive the sun.
- ⚠️ The hold restarts only when a reading crosses the committed state, never on any change —
  otherwise alternating readings stall it for ever. Holds are asymmetric: 0.35 s on, 1.6 s
  (`light_hold_s`) off.
- Shadows off (mobile tier rule). Hidden, not zero-energy, when off: 1,200 lights at energy 0 cost
  +0.44 µs each, hidden cost 0.00. `prims` and `draws` are bit-identical with two cones or none.
- 🔴 Forward Mobile pairs at most 8 spot lights per rendered object; the 9th is exactly absent with
  no warning. `distance_fade` (begin 35 m, length 15 m) frees slots but does not cap competitors —
  see `BeamBudget`.
- Circuits 5–8 live in a second vector `lamp_front`. ⚠️ Ordering is the contract; both vectors are
  indexed with the same masked slot because Mobile drivers flatten ternaries. Guard bounds at
  `CIRCUIT_COUNT`.
- ⚠️ The sun probe is 200 m because only the finest tile tier has colliders (band 250 m). At
  `golden_hour.tscn`'s 30° sun a building over ~115 m throws shadow past the ray.
- Probes sample at `probe_hz` 10 (cover 0.49 µs, sun 0.91 µs; a wheel ray is 0.50 µs). ⚠️ Carry the
  remainder — assigning the period ran at 8.58 Hz.
- Refused on measurement: change-guarding `set_instance_shader_parameter` (33 ns unchanged, 50 ns
  changed); random probe phase (costs byte-deterministic driver runs).

**See.** `P3-11d` · `Q21` · `Q26` · `ART_DESIGN.md` "Vehicles"

## `P3-11f` — The roof sign lights, and it is the one lens that must not bloom

**Status.** 🟡 Awaiting review · **Owner.** `P3-11`.

- The roof box is a switched lens on `CIRCUIT_ROOFSIGN` (7), held on, at `sign_lit` 0.45 of lens
  level. No new geometry (604 triangles); spends a spare `lamp_front` channel.
- ⚠️ Below ~0.63 the emission stays under the glow threshold: a sign is a lit surface, not a
  source. Under the deck, 1.00 → 0.45 took bloom pixels 1,193 → 463.
- ⚠️ A lens by name: `sign` is a whole-name entry in `LAMP_PARTS`, so any later part starting
  `sign` joins silently; `test_the_roof_sign_is_the_only_thing_lit_above_the_roof` bounds it by
  geometry. The `SILVER` cap is deliberately a lens too — "fixing" the precedence leaves a lit box
  with a dark lid.
- ⚠️ Not scaled with the light ladder: the sign answers to "in service", which nothing simulates.
- `steer_hold_s` 0.5 → 0.3 s on the user's call; `steer_threshold` rejects corrections on
  amplitude. ⚠️ An amber-pixel count cannot grade indicators (the unlit lens and plate are amber);
  use an A/B frame diff.

**See.** `P3-11d` · `P3-11e` · `Q43`

## `BeamBudget` — the eight spot lights are rationed by distance, not by pair order

**Status.** ✅ Shipped · **Owner.** `P3-11e` → `P3-3`.

- Forward Mobile's 8-spots-per-object list is contended by every beam landing on the road mesh —
  four two-lamp cars — and the winners are pair order, not distance. `BeamBudget` (autoload,
  `beams.tres` / `beam_profile.gd`) grants beams to the rigs nearest the camera. ⚠️ Measured when
  roads were one region-wide `roads.glb`; they are per-tile chunks since `P5-6`, not re-measured.
- Only the thrown cone is rationed; a denied car's lenses still light, and it keeps running its
  ladder. Cost is `beam_count()` per rig; a rig too big for the remainder is skipped, not stopped
  at. `distance_fade` stays alongside.
- Hysteresis: `swap_margin_m` 8, `regrant_hz` 6.
- `verify_beam_budget.gd` runs in `check.sh` outside `VERIFY_GENERATED`: 16 cars spend exactly 8
  slots; nearest 4 win when registered farthest-first; a beamless rig takes none; a despawn hands
  its slot on.
- ⚠️ Verify-tool traps: a `Node3D` parented to the root `Window` reports `global_position` zero;
  global transforms need a deferred frame; integer division is a warning-as-error and a parse error
  in a `--script` tool exits 0. `_profile` is typed `Resource`, not `BeamProfile`, for the
  class-cache reason.
- Open for `P3-3`: ranking is distance to camera only; decide whether the player's slot is reserved
  before a cinematic or look-back camera exists.

**See.** `P3-11e` · `P3-3` · `PROGRESS.md` risk register

## `verify_vehicle.gd` — the import and the scene are the half no test could see

**Status.** ✅ Shipped · **Owner.** `P3-11c`–`P3-11e` → `P3-3`.

Holds the two silent channels from ETL to fragment shader — a glTF material name and
`instance uniform` names. Runs in `check.sh` outside `VERIFY_GENERATED`. Each check was proven by
breaking what it guards.

- Every body surface renders with `vehicle_body.tres` / `vehicle_body.gdshader`.
- Every channel `vehicle_lamps.gd` writes is in `GeometryInstance3D`'s
  `instance_shader_parameters/*` list; `sun_toward` is checked in
  `Shader.get_shader_uniform_list()`. ⚠️ The two lists are complementary — instance uniforms are
  excluded from the latter.
- The `UV` payload survived import: markers and circuits integral, no circuit past the declared
  width, none on a non-lens.
- The rig hangs where the scripts look (their `assert`s are stripped in release).
- Beams authored dark, no cone above horizontal.
- ⚠️ Cannot tell that the shader compiled — headless has no rasteriser. Needs a render plus
  `grep -i "shader error"`.
- ⚠️ Names no `class_name` global, and awaits a frame before loading `taxi.tscn` — autoloads
  register on the first frame, else `InputRouter` is unresolved and the broken class is cached.
- Grades `taxi.tscn` only; a roster car earns its own entry.

**See.** `BeamBudget` · `ARCHITECTURE.md` "Checks"

## Two shadow cascades at 400 m, not four at 600

**Status.** Standing.

- 2 PSSM cascades at 400 m — the chase camera's far plane and the streamer's unload. Distance is
  free: 150–600 m measure bit-identically per cascade count.
- Frame primitives vs the four-cascade default: −35% at two, −55% at one. ⚠️ A primitive count, not
  a frame time; GPU saving unmeasured. Draw calls go the other way: 4 → 32, 2 → 35, 1 → 39.
- 🔴 One cascade was shipped and withdrawn: shadows fade mid-street at 150 m, HKCEC bands at 250 m
  and vanishes at 400 m. ⚠️ `directional_shadow_fade_start` is a fraction of `max_distance`.
- No `LightingProfile` resource: a `.tscn` is data; an apply script would be a second source of
  truth the editor cannot show.
- ⚠️ `ART_DESIGN.md`'s "vehicle blob shadow only" needs re-examination before the mobile tier
  (`P2-6`).

**See.** `ART_DESIGN.md` "Lighting" · `Q31`

## Debug chrome: one owner, one key, off by default

**Status.** Standing.

- `DebugHud` autoload owns every dev readout. `F3` cycles `off → minimal → full`; `--debug-view=`
  sets the start. Default off in every build: 19 draw calls off, 27 minimal, 38 full.
- `drive.sh` defaults to `minimal`; the position block gives engine metres and the EPSG:2326 grid
  reference.
- ⚠️ The toggle is a raw key, not an action, so `drive.sh --hold=` cannot press it. Headless parks
  the HUD regardless.
- Font sizes are constants: hard rule 4 covers gameplay tuning, not dev chrome.

**See.** `ARCHITECTURE.md` "The debug overlay"

## The vertex stream carries both ground and building colour

**Status.** Standing.

- Colour rides `COLOR_0` on untextured meshes that merge to one primitive per tile.
- Refused: shipping the terrain orthophoto (~5.9 MB ASTC). +1 draw call per resident tile, and the
  real roads baked in show from under the wider generated ribbon; high-passing shadows worsens the
  misregistration. The texture is read at build time and discarded; the ground classifier was
  refused on resolution (`Q18`).
- ⚠️ Per-vertex payload goes in `TEXCOORD_0`, not `COLOR_0.a`: `vertex_color_use_as_albedo` is
  project-wide, and enabling transparency on a tile would render the city see-through.

**See.** `Q18` · `Q27` · `P3-7` · `P3-10`

## The audit viewpoints

**Status.** Standing.

Seven fixed cameras cover every shipped mesh class (`ART_DESIGN.md` "The audit viewpoints"; shots
under `build/driver/art_*`). Changes are graded against these, never a fresh camera. ⚠️ Ask which
classes a document covers before reading frames — infrastructure had no section at all.

**See.** `Q30` · `Q31` · `Q32`

## Rendering proposals: eight evaluated, two survive

**Status.** Standing — refusals below are measured shut.

Surviving, in order:

1. `Q31`'s bounce-fill: `ambient_light_color` / `ambient_light_energy`, one at a time, graded with
   `tools/frame_stats.py`. No rebuild.
2. A precomputed sky-visibility bake, only if 1 fails — the only occlusion the mobile tier can
   have. Inputs exist (`terrain.py` height field, extruded footprints). ⚠️ Tint-probe first off
   `TEXCOORD_0.x` (`Q32` skipped that step and was reverted). Second consumer: `Q39`.
3. `WATERBODY`, 605 triangles — tint-probe first; most is on the hillside `Q36` measured at 0.000%
   of every viewpoint.

Refused:

- Real-time GI: the sun does not move; night is a switch between two static rigs.
- Planar reflections / SSR: absent from the Mobile renderer; `city_facade_clean.gdshader` ships the
  cheap equivalent.
- Wet-material overlay: anti-goal; needs a material layer, UVs, textures and SSR.
- Restoring an unclustered LOD0 for UVs: the non-textured set ships 0 images and no `TEXCOORD_0`;
  30.5 MB and 40% of visible triangles for a difference `Q16` measured invisible.
- UVs from the individualised set: per-image atlas coordinates, useless without the images.
- Low-res terrain orthophoto (~1.1 MB ETC2): baked illumination (`Q36`), 1.6× road-width
  misregistration, +53 draw calls.
- `VEGETATION(TB)` / `GENERIC`: 1.52 M and 3.95 M triangles, one welded blob per sheet, no
  `COLOR_0`.
- 🔴 Glazed-vs-solid from imagery: does not separate (share above 0.3 is 29.8 / 24.4 / 25.7 / 16.7%
  across the height bands), and median 14.3% of wall area is photographed at all (`Q37`).

Method traps:

- ⚠️ A degenerate value repeating to the last decimal is the tell: 53.2% of samples were
  RGB(60,60,60) atlas filler (`Q37`).
- ⚠️ Shrinking atlases is safe for colour only (ΔE 0.64 at 1/4, 0.80 at 1/8), and only if the
  filler mask is computed at full resolution and carried as a fractional weight. Periodicity floors
  at ~1/2. A persistent shrunken cache is not worth it (242 MB to save under two minutes).

**See.** `ART_DESIGN.md` anti-goals · `DATA_SOURCES.md` · `Q31` · `Q37` · `Q39`

## `Q42` — The reader answers seven questions nobody consumes

**Status.** 🚫 Moot — **Superseded by** `Q102`: the vision reader and `TEXCOORD_1` are removed; a
new channel is a schema bump plus a fresh argument, not a reserved slot.

What was measured stands: storey pitch median 3.32 m/floor over ten faces against `Q40`'s
independent 3.38; `emphasis` filled 25/25 and coherent with grammar; `band_period_floors` 0/25.
🔴 `signage` read real identities (SHUI ON GROUP, YMCA, FWD) — trademarks, never to ship as
rendered text.

**See.** `Q40` · `Q41` · `Q102`

## `Q43` — `glazed` is materiality; `fenestrated` is geometry

**Status.** ✅ Closed — the split stays after `Q102`; re-merging re-opens the defect (grid zeroed
on 39.3% of wall vertices).

- In `city_facade_clean.gdshader`: `fenestrated` = the wall has openings; `glazed` = those openings
  are dominated by glass. Two floats.
- ⚠️ The `draws_detail` early-out tests `fenestrated`. `glazed` reaches albedo only through the
  pane material, whose mask requires `fenestrated`.
- `recess_colour` `(0.12, 0.12, 0.13)` and `unglazed_reflect` 0.18 in `city_facade.tres` —
  authored, not measured; deliberately not zero (openings would read as painted rectangles).
- ⚠️ `fin` and `curtain` ratios assume a glazed skin; on an unglazed wall they fall back to punched
  proportions and keep their own pier.
- ⚠️ Shopfronts are weighted per mask, not per building; `has_shop` never passes the glazed gate.
- ⚠️ A versioned interface catches shape drift, never semantic drift. Before consuming a field, put
  the producer's sentence beside the consumer's and convert rather than assign.

**See.** `Q26` · `Q30` · `Q40` · `Q102`

## `Q44` — A punched opening is glass, not a black hole

**Status.** ✅ Closed — ships on the hash path (`Q102`); user accepted 2026-08-09.

- `unglazed_glassy` floors per-building glassiness:
  `glassy = mix(mix(unglazed_glassy, 1.0, glazed), 1.0, shop_share)`. 0.0 is `Q43`'s matte
  behaviour; ships 0.65 in `city_facade.tres`. Reflection and roughness already scale with
  `glassy`.
- Bar (`Q30`): whole-frame mean `C*` cost vs `C` stays ≤ `A`'s on all three audit cameras. Held:
  `street` +1.16 ≤ +2.28, `kerb` +0.78 ≤ +1.43, `skyline` −0.05 ≤ −0.02.
- ⚠️ Punched panes take authored/hashed colour (`Q45`), never a measured glazing tint.

**See.** `Q30` · `Q43` · `Q45` · `Q26`

## `Q45` — One pane palette across the city reads as wallpaper

**Status.** ✅ Closed — ships on the hash path (`Q102`); user accepted 2026-08-09.

- `pane_l_jitter` 6.0 / `pane_b_jitter` 4.0 (seeded CIELAB jitter on the hashed tint, draw slots
  13/14) and `pane_hue_pull` 0.25 (pane `a*b*` mixed toward the building's own `COLOR_0`
  chromaticity, linearised first per `Q27`). Computed in `vertex()` into flat `fallback_pane`.
  `linear_to_lab()` mirrors `etl/pipeline/colour.py`; keep the pair together. Zero amplitude skips
  the Lab round trip and is bit-exact.
- The pull lowers frame chroma (`street` cost +1.40 → +1.16); variation arrives through `L*` / `b*`
  spread.
- ⚠️ Any retune is bounded by `Q35`: pane variation must read within a frame without a
  salt-and-pepper skyline.

**See.** `Q27` · `Q35` · `Q44`

## `Q46` — A grammar refusal draws a quiet tier, not invented fenestration

**Status.** 🚫 **Superseded by** `Q102` — the five `quiet_*` uniforms were deleted with the reader.

⚠️ They conditioned on the grammar refusing; with no reader every building refuses, so a leftover
tier would quiet the whole city. Stands as record: not a height gate (`Q34`: height plus footprint
explain 1.4% of the façade signal); mute pane chroma, never glassiness (`Q44`).

**See.** `Q34` · `Q44` · `Q102`

## `Q47` — A committed verdict is right about the tower, wrong about the ground band

**Status.** 🟡 Data half survives `Q102`; survey half and the premise are moot (nothing commits a
verdict). Nothing consumes `podiums.json` yet · **Owner.** `P3-7a`.

- iB1000's `Building` layer (EPSG:2326, levels in mPD) carries podiums first-class:
  `TYPEOFBUILDINGBLOCK` `T` / `P` "Podium Block" / `OS` / `TS`, `BASELEVEL` / `ROOFLEVEL`, and
  `CERTAINTY`. Wan Chai: 1,595 pieces (1,220 `T` / 280 `P` / 76 `OS` / 19 `TS`), levels 100% filled
  on `T` and `P`; podium height p50 14.6 m. Footprints register to 0.1 m against the shipped
  volumes.
- Fetch: 260 MB, six sheets, via the TileIndex's `directDownload` URLs — the only scriptable route
  (portal links 403, the seamless set 504s). The host's TLS chain is completed by a committed
  intermediate (`extra_cas`). `gdb.py` decodes polygon-Z in both WKB dialects.
- `podiums` stage (before `buildings`), `podiums:` config block → `podiums.json`, an ETL
  intermediate `export.py` never names. A sheet cut clips a block, so pieces group into 1,480
  logical blocks (1,134 `T` / 251 `P`). True-overlap join: 458 towers meet a `P` block, 228 exact
  level meets. Mesh join is spatial, depth-gated at 0.3 m: 310 of 1,385 stems carry a data boundary
  (291 certain, p50 13.6 m), `mechanism: "data"`. HKCEC 52.1 m over base 3.9; Times Square at
  exactly 75.6 mPD.
- ⚠️ The earlier 668 / 54.8% / 247 figures are a bounding-box frame, pinned by the acceptance test;
  the operative join is polygon overlap.
- ⚠️ `P` is a partial classification (Central Plaza has none): absence is not "no ground band".
- 🔴 Refused by measurement — survey `podium_floors` → metres. Against a bar fixed beforehand
  (|err| p50 ≤ 2.8 m, p90 ≤ 7.0 m) it graded p50 10.76 m, signed −10.76; 40.4% of certain data
  podiums were invisible to the reader; Spearman ρ 0.076. The reader measured the treatment band,
  the `P` roof measures the massing (`Q43`'s two-predicates trap). The shader's
  `podium_height_m = 12.0` uniform alone scores 2.97 / 5.99 on the same pool; retuning it (~13.5)
  is refused as an art call measured only on `P`-block towers.
- Contract argument, should a boundary ever ship: per-vertex constants only; pack floors against
  the same packed pitch the shader multiplies back, never a second metres grid or an ETL copy of
  the 2.8 m fallback; provenance stays ETL-side; precedence `authored > data > survey > hash`.
- Open: whether a data-only podium boundary ships at all. It now needs a new channel (`Q102`), and
  the shipped boundary would be graded before this closes.

**See.** `Q41` · `Q42` · `Q43` · `Q34` · `Q102` · `P3-7a`

## `Q48` — A contrast ratio measures banding where an `L*` profile could not

**Status.** 🟡 Open as a candidate — nothing built, nothing scheduled · **Owner.** `P3-7a`

`P3-6`'s HKCEC ribbon veto is a ratio, not a classifier:
`contrast = L(band sample) / mean(L(sample ± pitch/2))`, median per strip (one band level on one
connected wall component), vetoing at `veto_ratio` 0.9. Samples map through the parent source
triangle into `…A0` atlas coordinates; a sample leaving its parent is discarded, never clamped.

- Escapes `Q40` Probe 3: it compares samples in world metres on the same surface, so chart size is
  irrelevant. Describe it as *per-triangle atlas samples indexed by world elevation*, not "measured
  from the A0 atlases".
- Escapes `Q40` mode 1: band presence is a tone claim, not a depth claim. The ratio cancels baked
  sun/shade (0.03–0.66 wall luminance across facings); an absolute darkness cut fails.
- 🔴 Still reached by mode 4 (periods on blank walls, e.g. `B355691583201063A0`) — exactly `Q47`'s
  committed-but-blank ground bands. Also mode 2 (reflections on glass), mode 5 / `Q37` (wall
  selection; under 15% of wall area photographed), and it confirms an authored `ribbon_pitch_m` but
  cannot find one — sweeping the offset is `Q40`'s autocorrelation again.
- ⚠️ Usable only as a one-way veto: the photo may only remove bands; an undecided strip keeps the
  procedural verdict; fewer than five decided samples refuses. As an assertion this record does not
  carry. Evidence is n=1 (HKCEC), graded by eye.

### Two claims, and only one of them is new

Pitch is not new. Shipped `floor_height_m = 2.8` (`P3-7` atlas-V autocorrelation, 2.77 m, 227
walls) sits ~16% below three instruments that agree within 3%: `Q40` unwrap 3.38 m, `Q42` reader
3.32 m, `Q47` tower↔block join 3.28 m. The gap is unreconciled. A mechanical pitch measurement
would be the third grader `P3-7a`'s storey-pitch rider (`TEXCOORD_1.y`, 1/32 m steps, 2.5–4.5 m)
is short of.

Presence is the new claim: the discriminator `Q47`'s committed-stock population needs, and
`band_period_floors` is the one reader field that never commits (0 of 25 validation faces).

### What it would owe, if it is ever promoted

- Its own sample lattice: survey stock is unsliced, so sample sites are generated within each wall
  triangle; a usable neighbour needs a parent spanning ≥ pitch/2 vertically.
- A pre-fixed bar and a third-party instrument: `Q41`'s per-face `glazed`, on more than one sheet
  (`Q40`'s dip flipped sign between `11-SW-9D` and `11-SW-15A`).
- The three-places cost: merge/pack, shader decode, `verify_tiles.gd` (`uv2.y != 0.0` breaks on the
  first rider). No `schema_version` bump — a reserved field read as "0 = refused".
- ⚠️ All six individualised sheets are on disk in `etl/sources/individualised/` (5.7 GB) — the
  survey tools' `INDIVIDUALISED_DIR`, not `etl/sources/hong_kong/individualised/` (the
  `fetch.source_dir`, one sheet). A fresh clone pays 5.86 GB; `etl/sources/` is gitignored.
- No new source, licence position or rule reading; individualised is not the tile mesh of rule 1.

**See.** `Q40` · `Q41` · `Q42` · `Q47` · `Q37` · `P3-6` · `P3-7a`

## `Q49` — A tyre spends one budget, and the handbrake that follows spins the car

**Status.** Superseded by `Q50` (the raycast model and its friction ellipse are deleted) · findings
below still stand

- A fully locked rear axle spins the car (peak slip 162.1° from 62.78 km/h); lowering handbrake
  grip made it worse (177.3° at 0.05), and a 0.5 s tap spun it too. The spin is structural.
- ⚠️ `GAME_DESIGN.md`'s "easy to hold, scrubs little speed" is anti-physical — a real handbrake
  trades speed for rotation. This is what licensed the yaw assist (`Q85`).
- The throttle-sustained slide needs per-wheel angular velocity; `Q85` closed that route —
  `VehicleBody3D` has no wheel inertia.
- `tools/skidpad.sh` grades and does not check, so it stays out of `check.sh`. Its braking row
  reproduces `P0-5b/c/d`'s published stop. Displacement and yaw accumulate per tick; an empty run
  is a failure (`_printed_rows`); the run-up releases the throttle.
- ⚠️ Slip angle flattens both the velocity and the nose vector to the ground plane.
- ⚠️ A `--script` tool must not name `VehicleController`: the annotation resolves in `_init` before
  the `InputRouter` autoload exists, the class fails to compile, and `taxi.tscn` instances with a
  null script ("no vehicle"). `driver.gd`'s duck-typing is deliberate.

**See.** `P0-5a` · `Q50` · `Q84` · `Q85` · `PLAN.md` `B4`

---

## `Q50` — The shipped car is Godot's `VehicleBody3D`, and `P0-5a` was right

**Status.** ✅ Shipped 2026-08-18 on the user's explicit instruction · **Owner.** `P0-5a` → `B4`

`scenes/vehicle/taxi.tscn` is a `VehicleBody3D` with four `VehicleWheel3D`. `VehicleController`
keeps its name and consumers; suspension, friction and anti-roll are the engine's. The raycast car,
`wheel_mount.gd`, `wheel_visual.gd` and the built-in spike scenes are deleted. ⚠️ This reverses
`P0-5a` by instruction, not by re-measurement — `P0-5a`'s finding reproduces.

Costs accepted (`tools/skidpad.sh`, `skidpad.tscn`):

1. `Q49`'s friction ellipse is gone: one isotropic `wheel_friction_slip` is a circle, so braking
   through a corner costs no cornering grip (corner yaw −358.2° against −428.9°).
2. The drift dial: corrected by `Q84` — there is no cliff (0.6695 peaks at exactly 14.0°); the dial
   is graded on dwell above `drift_slip_threshold_deg`, and dwell is bought with exit speed. Read
   `Q84` before quoting a number.
3. A 0.5 s handbrake tap does nothing (1.9° slip, identical to `corner`): grip returns on the same
   tick as the release.

Braking and coasting reproduce the raycast baseline within 0.5%, so the hand-written coast drag and
arcade collision response (`_integrate_forces`; `collision_deflection`,
`collision_speed_retained`) ported correctly.

Re-seeded, not convertible from the old values:

- `brake_force` 40 — Godot's `brake` is its own quantity; the old 2400 stopped the car at 173 m/s².
- `tyre_grip` 2.5 — one number where there were two, chosen so `corner` holds the baseline speed.
- `roll_influence` replaces `anti_roll`; `VehicleWheel3D` publishes no suspension compression
  (`is_in_contact()` and `get_skidinfo()` only).
- `suspension_max_force_n` 19000 — load-bearing: static corner load ≈ 4704 N leaves Godot's 6000 N
  default 1.27× headroom, and the spring clips on the first kerb silently.

⚠️ `tools/skidpad_ablation.gd`'s `--drift-grip` sweeps `drift_rear_grip_scale` and checks the field
with `in` first: `Object.set()` on a missing name is a silent no-op that prints identical rows.

🔴 `Q85`: `get_rpm()` is road speed re-expressed, so per-wheel angular velocity cannot be read; the
drift is assisted with a yaw torque. Wheel rotation is road speed, and `P3-2b` inherits that when
tyre marks exist.

**See.** `P0-5a` · `Q49` · `Q84` · `Q85` · `Q89` · `.claude/rules/handling.md` ·
`ARCHITECTURE.md` "The importer can reinstate `VehicleWheel3D`"

---

## `P3-9a` — The build is threaded, so the host is not a free choice

**Status.** 🟡 Open — build cut and verified; drivers not yet run

- The `Web Demo` preset ships `variant/thread_support=true`, so the engine needs
  `SharedArrayBuffer`, gated behind `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp`. Without them it fails with a bare
  `SharedArrayBuffer is not defined`.
- This rules out GitHub Pages and is why `tools/serve_web.py` exists. Host: itch.io
  ("SharedArrayBuffer support" toggle; password-protected draft page).
- ⚠️ Do not turn `thread_support` off for this round: single-threaded web is a different frame
  budget, and `P3-9a` grades how the city feels to drive. Available to a later public demo.
- Before sending a link: `tools/check.sh` green, a scripted drive with 0 `SHADER ERROR`, Chrome
  over the real headers with 0 console errors. A smoke check, not the `verify_vehicle.gd` the risk
  register owes.
- ⚠️ The distributable zip is hand-packed; `tools/export.sh` has no zip step and nothing warns. It
  has gone stale twice (once shipping no road markings). Re-pack on every re-export and check the
  zip's mtime against `build/web/index.pck`.
- Last measured (2026-08-20): PCK 39.17 MiB + wasm 37.02 MiB = 76.19 MiB over the wire; itch zip
  47.43 MiB.

**See.** `PLAN.md` `P3-9a` · `PROGRESS.md` risk register · `Q26` · `P3-7a` · `P3-11e`

## `Q51` — Traffic is never sent down an edge a car cannot fit through

**Status.** ✅ Closed · **Owner.** `P3-3` · 🔴 `MAX_SUBDIVISIONS` smear still owed

`city.json` publishes a clear corridor width per carriageway station (`CITY_SCHEMA` 9 introduced
it); `RoadGraph` reads it as `is_passable` / `is_routable`, and `P3-3` routes on `is_routable`.
This is the routing half of `Q19`: it measures, it does not clear.

- Expressed, never enforced: `nearest_edge` still answers on a blocked edge, because a car can be
  there (unlike `Q13`'s off-grade refusal). `verify_road_graph.gd` asserts it finds every blocked
  edge.
- The number rides in `city.json`, not `roadgraph.json`: clearance is a fact about what was built
  beside the ribbon, not the authored street.
- `etl/pipeline/clearance.py` (between `surface` and `export`) measures;
  `tools/carriageway_occupancy.py` still grades. Publishing the grader's output would make the
  instrument load-bearing in the build it audits.
- Wan Chai at the shipped spacing: 24 of 737 level-0 edges keep less than one lane (3.20 m) clear,
  five at 0.00 m (e.g. `e636` HARBOUR ROAD). 4.4 s, 789 MB.
- ⚠️ The triangle count moves with the spacing because the occupier prune is corridor-shaped — not
  the city.
- ⚠️ `np.einsum` needs `optimize=True` to reach BLAS (was 30% of the stage). The memory budget must
  be on pieces (`PIECE_BUDGET`), not triangles: `MAX_SUBDIVISIONS` lets 3,773 triangles become
  763,000 pieces.
- ⚠️ Sample along the edge at `ALONG_M`, never at polyline vertices: `roads.py` simplifies to
  0.2 m, so a straight street is two stations, both inside the junction trims.
- ⚠️ A station the ribbon never reached publishes `-1.0`, not `0.0` (`roadsurface.json`
  `carriageway[].trim_m`); judging those condemned 18 innocent edges in `Q19`.
- ⚠️ Occupiers are subdivided by plan extent (≤ 0.5 m), never by area or edge length.
- ⚠️ The formulation is shared with `Q19`'s grader — surfaces standing in the bumper band; a
  footprint test marks everything under a flyover blocked. Do not quote the two as independent
  methods.
- ⚠️ The one place the pipeline reads the game tree: committed heroes (`central_plaza.glb`) are
  occupiers too.

### The two instruments, reconciled 2026-08-19

`tools/clearance_reconcile.py` runs both over one bundle and holds the counts as a ratchet.

- Dead mechanisms: drawn-vs-nominal corridor (median |Δ| 0.000 m) and trimmed stations (dropping
  all of them: 26 → 26).
- The mechanism is plan cell size: a cell blocks in full once one sample lands in it. Brute force
  on `e132` (109 M samples at 5 cm) gives 0.98 m in 1.00 m cells (the grader's figure) and 4.00 m
  in 0.25 m cells. Grader starved count by `--index-cell-m`: 1.00 m → 26, 0.50 m → 18, 0.25 m → 9.
- Both defaults stay. In plan both over-block; along the edge the pipeline missed walls between
  cross-sections, and the grader's 1 m bin is immune. Two instruments, two error dimensions.

### The `ALONG_M` call, taken 2026-08-19

`ALONG_M = CELL_M` (0.5 m): a walk at cell pitch cannot stride over a cell, so the published width
is a lower bound at `CELL_M`. Starved 21 → 24; disagreements with the grader 7 → 4 (grader-only
`e99` `e207` `e781`; pipeline-only `e702`).

- Refused: 0.25 m — one more edge for ~4× the run and 1.088 GB peak RSS. ⚠️ Residue: a diagonal
  walk can corner-cross an axis-aligned cell without landing in it.
- No schema bump: `clear_width_m` means the same, only more accurately (`CLEARANCE_SCHEMA` 1).
- ⚠️ `tools/narrowing.py` is owed by any spacing change — its split is over the pipeline's starved
  population. `Q19`'s refusal holds: 0 edges cleared at every factor down to 1.30×, 2 lost.
- 🔴 Owed: 9,779 triangles a run hit `MAX_SUBDIVISIONS` and block by their plan box at whole height
  range (hero meshes, long ramp faces; `build_region` warns the count). `e702` EXPO DRIVE CENTRAL
  is the signature (`LANDMARK`-blocked, 0.75 m against the grader's 3.41 m). Fix it alone — it
  moves the count the opposite way.
- Refused: a blanket margin on `is_passable` — dominating the grader needs a 5.00 m bar, refusing
  37 edges to cover 6 the grader over-blocks.
- Not done here: `RoadGraph` stores no adjacency and reads none of the 217 turn restrictions
  (`P3-3`).

**See.** `Q52` · `Q19` · `Q13` · `Q23` · `.claude/rules/clearance.md`

---

## `Q52` — The start line says what it is standing in, and the check is what refuses

**Status.** ✅ Closed 2026-08-18 · **Owner.** `P2-3`

`RoadSpawn.Pose` carries the clear width at the start line and `Pose.blocked`. `drive_harness.gd`
warns and places the car anyway; `tools/verify_spawn.gd` fails. Future respawn rules should ask
`Pose.blocked`.

- Reports, never relocates. Refused: relocating (the spawn is a published TD taxi stand, `P2-3`)
  and returning an unresolved `Pose` (falls to the authored literal on the same street, with name
  and lane blank). The check refuses, so the bundle gets fixed.
- ⚠️ The bar is the segment where the car stands, not `is_passable` (minimum over the whole edge).
  `Pose.edge_passable` is printed, not failed. Changes the verdict on 31 of 2959 segments, always
  toward blocked.
- ⚠️ `NOT_MEASURED` is `-1.0` and sorts below every real clearance. `RoadGraph._clear_at` takes the
  smaller of the two bounding stations and must skip unmeasured ends (19% of segments have one);
  a plain `minf` silences the guard. Both-ends-unmeasured reads unjudged; `has_clearances()` stops
  a whole bundle of those.
- It fires on nothing shipped (`f_004` on `e651` stands in 9.00 m), so the value is the check being
  non-vacuous: five built start lines `f_case_1..5`, each the only catch for one break
  (`blocked()` → false / true / `not edge_passable`, `_clear_at` → `minf`, `NOT_MEASURED` not
  excepted). All five must still resolve.
- Not proven against the bundle's worst edge: a build that clears every edge must pass.
- The proof is called from `_init` beside `_check`, not inside it, so it runs on a broken bundle.
- Does not stop the player driving into a blocked edge (`Q19`, open).

**See.** `Q51` · `Q19` · `Q13` · `P2-3`

---

## `Q53` — Markings are drawn, arrows are not, and the difference is data

**Status.** ✅ Closed 2026-08-19 · **Owner.** `P3-12` · scope amended by `Q57`, `Q58`, `Q59`

`road_markings.gdshader` draws markings procedurally in lane space over `roads.glb`: `TEXCOORD_0.x`
is a lane coordinate (0 at the nearside kerb, `lanes` at the offside), V is metres along. Current
draw switches are `roadmarks`' (`Q132`, `Q125`).

- 🔴 The original scope reason ("no marking data in any source") was false: Traffic Aids Drawings
  v2 publishes arrows (`RM` code + `ANGLE`), road text (`DTAD_RD_MARK_ANNO`), box junctions
  (`DTAD_YL_BOX_POLY`) and crossings (`DTAD_CROSSING_LINE`) — `Q56`, `Q57`. Arrows were built as
  their own mesh (`Q59`). Never conclude "no source" from Road Network v2 alone.
- Orthophoto markings stay refused on registration (`Q18`/`Q36`): the ribbon is drawn wider than
  the real carriageway, so imagery can vote on whether, never where.
- No texture, enforced: `scripts/city/mesh_contract.gd` fails any shader uniform holding a
  `Texture`.
- ⚠️ The lane coordinate alone cannot be drawn on: kerbs run off both ends of the lane range
  (`[−0.156, 0]`, `[lanes, lanes + 0.156]`); `U = 3.0` is a kerb on a three-lane road and a lane
  line on a four-lane one; caps carry `(0, 0)` and `U = 0` is the nearside kerb line. `TEXCOORD_1`
  answers: packed codec in `x`, the edge's drawn length in `y`.
- ⚠️ `y` is the edge length, not distance-to-nearer-end: a two-station edge (204 of 797)
  interpolates that distance flat to zero. The shader computes `min(V, length − V)` per fragment.
- Junction fade `fade_m` 6.0 (`tuning/road_markings.tres`): the worst cap overlap onto an arm is
  4.21 m (203 of 1,398 ends overlap). 4.0 does not clear it; 9.0 left 21.2% of edges unmarked
  against 15.2%.
- ⚠️ The overlap (6,051 m² of 52,985 m²) is hidden, not fixed; anything drawn on a cap re-exposes
  it. The fix is a non-convex cap (polygon clipping), unbuilt. A world-space hatch masked on
  distance-to-node is immune.
- `offside_kerb` is published from `_hide_buried_kerbs`, so the offside yellow follows a
  measurement; a missed opposed pair costs a centre line, never a yellow line mid-road.
- Opposed-pair join (six pairs, 564 m in Wan Chai, e.g. `e86`/`e89` LOCKHART ROAD) is a codec
  field, sixteenths of a lane beyond the edge's own centreline.
  - ⚠️ One U-lane is `2·half_width / lanes` as drawn, not `lane_width_m`.
  - ⚠️ Measure the separation on the trimmed ribbon, averaged both ways; shared endpoints
    contribute hard zeros and halve a median. The test fixture must share its nodes.
  - ⚠️ The range guard bounds the carriageway (`lanes/2 + k/16 < lanes`), not the six-bit field;
    `steps == 0` is refused.
  - Pairs are found by shared endpoints — a lower bound (`P1-4`).
- ⚠️ Widening a codec field inside an existing channel does not bump `city.json`: fields are
  masked on read, and shader and ETL ship in one commit.
- ⚠️ Marking colours are authored in `tuning/road_markings.tres`, outside `Q33`'s checks (user's
  call, 2026-08-19). A third road colour authored elsewhere is the predicted failure.
- ⚠️ A `ShaderMaterial` skips the importer's `vertex_color_is_srgb`, so the shader converts by hand
  via `assets/shaders/colour.gdshaderinc` (shared by all shaders that need it). Forgetting it fails
  silently: the asphalt lightens.
- ⚠️ Godot rejects `return` in `fragment()` at run time; `check.sh` exits 0. Only
  `grep -i "shader error"` sees it.
- `verify_road_surface.gd` holds the material check, a codec scan, `meshes/light_baking = 1` and
  16-bit attribute compression. Shared checks live in `mesh_contract.gd`
  (`check_uv2_import_settings`, `check_shader_material`) — do not copy them.
- Tram rails are geometry (`Q58`): only 18.8% of cross-sections have both tracks on the drawn
  carriageway. `MARKING_TRAM` ships undecoded.
- Open: each ribbon of an opposed pair draws lane dividers across its partner's carriageway.

**See.** `Q54` · `Q56` · `Q57` · `Q58` · `Q59` · `ARCHITECTURE.md` `roads.glb` · `Q27` · `Q23` ·
`Q18`/`Q36` · `.claude/rules/roadmarks.md`

---

## `Q54` — The kerbside yellow is invented, and the layer that would source it was read past

**Status.** ✅ Closed by `P3-13`, 2026-08-19 · vehicle-type scope amended by `Q56`

`pipeline/kerbside.py` linear-references Road Network v2's `NSR` (No-Stopping Restriction) onto the
finished graph; `roadgraph.json` publishes `(edge, side, V-range)` runs; `tools/kerbside_error.py`
grades the shipped mesh. A line on every kerb over-painted 3.4×; sourced paint closed at 4% gross
error (3% after `Q56`). A double yellow is a legal assertion, not kerb trim.

### What `P3-13` built, and what this record got wrong

- The join: samples every 1 m to the nearest level-0 edge, side from the offset's sign, 1 m cells,
  gaps under 3 m bridged, runs under 5 m dropped. `NSR` keys on `ST_CODE_1..6`, so no key join;
  only 78% of line parts keep one side and 49% span more than one centreline feature.
- ⚠️ Level 0 only: for 7% of samples the nearest edge of any level is elevated (Canal Road
  flyover), and the restriction belongs to the street beneath.
- `TIME_ZONE` 1 is a double yellow, posted hours a single (confirmed 99.95% by `Q56`).
  `VEHICLE_TYPE` decides what is a painted line — see `Q56`.
- The widening is not an obstacle: the source is read for side and extent along, never position.
- Payload: two 2-bit codec fields `kerb_near` / `kerb_off` (absent / none / single / double) say
  the kind; `COLOR_0.a`, per rail, says where. ⚠️ The shader's `flat` sRGB hoist covers
  `COLOR.rgb` only; alpha is a separate non-flat varying.
- Refused: whole-edge quantisation — 33% gross error at the best threshold. Exact V-ranges ship
  (user's call, 2026-08-19): `surface.py` inserts a station pair 0.25 m either side of each
  boundary.
- ⚠️ `_rail_stations` thins kerb stations only where free. Height is interpolated along the
  centreline while a mitre displaces a vertex along its segment, so dropping a station can step the
  kerb off the carriageway by up to 87 mm. Kept: height stations, buried-kerb run ends, ribbon
  ends. `_off_line` bar 0.1 mm.
- ⚠️ 2,909 m of real restriction lands on a kerb the drawn city lacks (overlapping widened
  ribbons: Gloucester Road, Lung Wo Road, Harbour Drive). No shader change reaches it;
  `kerbside_error.py` reports it on its own line.
- One kind per edge side; the longer run wins. Wrong kind on 359 m after `Q56`. Refused: a per-run
  kind channel (a second byte per road vertex).
- ⚠️ Side convention: `surface.mitres` offsets left of travel and `U = 0` is that side.
  `tests/test_kerbside.py` asserts the join against `mitres` itself. `verify_road_surface.gd`
  requires `COLOR_0.a` to be 0 or 1, opaque outside the carriageway, and not uniform.
- Open: triangles folding inward at hairpins on the carriageway strip (11, 2.41 m² after `Q56`).
- `draw_double_yellow` in `tuning/road_markings.tres` turns the sourced marking off.
- Out of scope: `ONSTREETPARK`'s 607 bays.

**See.** `Q53` · `Q56` · `DATA_SOURCES.md` · `.claude/rules/kerbside.md`

## `Q55` — The filler guard reads greyness, and the placeholder panels are coloured

**Status.** ✅ Closed 2026-08-21 · **Owner.** `tools/facade_survey.py`

`Q37`'s `is_filler` rejected only exact `R == G == B` texels, but the imagery also carries flat
coloured placeholder panels — byte-identical files repeated across buildings, e.g. `(68,65,65)` on
21. Repetition, not greyness, is the defect's signature.

- ⚠️ Reject texels, never atlases: six 4096² photographs carry a baked flat fill at 23–57%.
  Distinct-colour count separates the populations (≤ 122 against ≥ 33,981) but is a diagnostic, not
  the guard.
- ⚠️ A repeated grey stays `Q37`'s and is filtered out of the colour set; otherwise
  `--filler-report` lists every grey-padded building with a zero delta. A test holds this.
- ⚠️ A dark panel wins too: above roughly half the sample the order statistic is inside the filler
  wherever the `L*` percentile cut falls. The error runs both ways (worst `ΔL*` +54.69 / −33.22,
  median +0.00).
- Result: with the colour axis off, the superseded table reproduces on all 2,213 rows. With it on,
  100 buildings carry a panel, 90 rows move, 61 past `Q33`'s 0.46 `Δab`; none fell under
  `MIN_TEXELS`.
- Re-derivations: `tools/ring_weights.py` — every weight exactly as shipped;
  `tools/facade_chroma.py` — share over `C*` 20 moved 26.4% → 26.5%. The panels damaged lightness,
  so `Q30` (chroma) survives.
- Open: a share-based refusal beside `MIN_TEXELS = 64` (one building is 96% filler and still
  answers). `--filler-report` grades the guard, not the table. `tools/facade_glazing.py` stays on
  `Q37`'s axis alone.
- ⚠️ `facade_lab.json` is under gitignored `etl/sources/`; republishing is local, reversible from
  `facade_colour/superseded/`, and owes the two re-derivations above.

### What shipped

`filler_colours` reads each atlas's repeated colours on a 1-in-16 lattice; `is_filler` rejects
them per atlas colour, per texel, beside the channel tie. `MODAL_SHARE` 0.20; every colour over
the bar is taken, not only the modal one.

**See.** `Q37` · `Q34′` · `Q30` · `Q33` · `.claude/rules/facade.md`

## `Q56` — `VEHICLE_TYPE = 5` is painted, and the way to know was a second dataset

**Status.** ✅ Closed 2026-08-20 · **Owner.** `pipeline/kerbside.py` config,
`tools/kerbside_source_audit.py`

`painted_vehicle_types` is `[1, 5]`. `NSR`'s spec names no class for `5 – Others`; a second dataset
settled it. Traffic Aids Drawings v2 (`hk-td-tis_16-traffic-aids-drawings-v2`, 51 layers,
EPSG:2326, monthly; the 1st generation `tis_8` is being withdrawn) draws what is painted:
`DTAD_RST_ZONE_LINE`, `RM1040` = double yellow, `RM1041` = single, `TIME_ZONE` null throughout.

- 93.9% of code-5 metres carry a painted line (96% `RM1041`); only 24 m of the drawings' 39,292 m
  is unexplained by `NSR`. `RM1040` lands on `TIME_ZONE = 1` for 99.95% of its length.
- ⚠️ Codes `2`, `3`, `4` stay refused because a class-specific restriction is not a plain yellow
  line and the codec cannot say which class (2,847 m) — not because they are "signs": code 2 is
  100% painted, code 4 90.2%, code 3 48.4%.
- Wan Chai publishes 33,385 m over 722 edge sides (19,764 double / 13,621 single).

### `tools/kerbside_source_audit.py`, and why it is not a second join

It feeds the drawings through `pipeline/kerbside.py`'s own join and diffs run sets cell by cell: a
second source through one join isolates the source; a second join would not say which is wrong.
With `[1, 5]`: both sources 96.4% of the union (77.0% with `[1]`); kind agreed 99.2%; opposite
kerb 35 m.

- ⚠️ It does not cover the side convention — both sources reach a side through
  `kerbside._Segments`, so a mirrored city agrees perfectly. `tests/test_kerbside.py` holds that.
- The build's "wrong kind" figure (359 m) counts source overlap within one side — a different
  population from the audit's kind column.

### What it cost, and one thing that went the other way

28% more restriction made the mesh smaller (boundary stations 1,179 → 1,113): a restriction costs
its ends, not its length, and a code-5 run usually continues a code-1 run. Double fell while single
rose because the cell vote now lets the posted-hours feature win where the drawing agrees.

### What the survey of the rest of the catalogue found, so it is not re-run

Swept: every TD dataset on DATA.GOV.HK (60), the CSDI transport theme, and every road / parking /
marking / kerb-named dataset in the 3,810-package index. Only `NSR` and `DTAD_RST_ZONE_LINE` assert
a kerbside stopping restriction.

| Dataset | Why it does not answer |
|---|---|
| `NSR`'s `ONSTREETPARK` | The complement (607 bays, operative hours in prose). Out of scope |
| `hk-td-msd_1` / `msd_2` parking | Counts per district; ~250 sensored spaces territory-wide |
| `hk-td-tis_4` / `tis_5` | Real-time occupancy |
| `hk-td-tis_36` Pedestrian Streets | `PEDESTRIAN_ZONE` already covers it |
| `hk-td-tis_39` Fleet Taxi Stopping Places | Bears on `fares.json` — worth its own look |
| `hk-hyd-csdi-pavement-polygon` | Bears on the carriageway; fetched under `Q94` (`Q57`) |
| `hk-landsd-openmap-road-centreline` | Labelling centreline, not a second road graph |

Also inside the drawings: `DTAD_YL_BOX_POLY` (20 box junctions in region), `RM1038`, `RM1043`
no-parking hatch (560 m), `DTAD_CROSSING_LINE` (121 features).

⚠️ The index plan defining every `RM` code ships inside the published `dataspec` zip stamped
"FOR INTERNAL ONLY"; `LICENSING.md`'s terms are unchanged by it.

**See.** `Q54` · `Q53` · `Q57` · `DATA_SOURCES.md` · `.claude/rules/kerbside.md`

## `Q57` — The estate publishes the markings, the width and the tram

**Status.** Closed as a survey (nothing built, nothing fetched) · Owner `DATA_SOURCES.md`

Four "unsourceable" claims were wrong the same way: a fact established against Road Network v2 (the
semantic dataset) generalised to the estate. Paint comes from Traffic Aids Drawings (cartographic),
physical edges from iB1000 (topographic). Swept: 3,810 DATA.GOV.HK packages, 1,144 CSDI records, all
51 `dTAD_IRNP.gdb` layers, all ~71 iB1000 layers; codes read from the publishers' dictionaries,
never inferred from code letters.

- Markings are published (`Q53`'s data argument retired, its scope call untouched):
  `DTAD_RD_MARK_SYM_PT` arrows, `DTAD_RD_MARK_ANNO` road text ×274, `DTAD_YL_BOX_POLY` ×20, plus
  stop lines `RM1011`, give-way `RM1013`, hatched islands `RM1037` ×414, bus-stop boxes `RM1047`
  ×82, parking bays ×169, carriageway edge `RM1108`/`RM1109` ×317.
- Carriageway width is published: iB1000 `CartoTransLine` `RM` = "Road margin", and HyD Pavement
  Polygon (`hyd_rcd_1632210918434_60749`). Instrument: `tools/carriageway_margin.py`. ⚠️ A
  perpendicular probe over-reads at junction mouths and dual carriageways; it proves a width exists,
  it is not a width to ship (`Q95` is the measured width).
- Tram is published: `CartoTransLine` `TW`, `RailwayPolygon` `RAILWAYTYPE = TW`, `RM1034`,
  `RM1045`/`RM1046`, 19 CSDI tram stops in region. `tram_streets` still stands: a nearest-centreline
  join confirms six of seven authored streets (RUSSELL STREET unseen); a naive join lands samples on
  CANAL ROAD FLYOVER above the track.
- Lane counts: no lane attribute exists anywhere, but lane lines (`RM1101`–`RM1104`) between
  published edges make a count derivable. ⚠️ Not `Q19`'s fix: `Q19` found the centreline inside the
  occupier on 13 of 15 edges, which no width or lane count moves.
- ⚠️ Trap: `DTAD_TW_STRIP_LINE` (`REFNAME = TACW`) is tactile warning strips at dropped kerbs, not
  tramway — it joins to every street in the region. The same `TW` means Tramway in iB1000.
- Genuinely absent: a lane-count attribute; and the real-time feeds, which hard rule 2 bars anyway.
- Follow-ons since taken: width (`Q95`), arrows (`Q59`), tram (`Q58`), boxes (`P3-18`). Still open:
  bus / GMB / tram / taxi stops into `fares.json`.

**See.** `Q53` `Q54` `Q56` `Q19` · `DATA_SOURCES.md`

---

## `Q58` — The published tramway is rails, not centrelines, and it is not on the carriageway

**Status.** Closed — `P3-14` ships `tram.glb` · Owner `pipeline/tramway.py`

The tramway is geometry at its published position, not a lane-space marking on the ribbon.

- A `TW` part is one rail: gap to nearest other part p50 1.154 m (published gauge 1,067 mm); track
  separation p50 2.597 m. Read as centrelines, a mis-paired bed is a lane wide.
- Refused: lane-space rails. 80 of 86 `tram_streets` edges are one-way opposed pairs, so the reserve
  runs between two ribbons; both tracks land on the drawn ribbon at only 18.8% of 1,698 sections
  (HENNESSY 1.5%, YEE WO 0%), outer rail p50 3.26 m past the drawn kerb. It would be an invented
  marking (`Q54`). `tram_streets` keeps its job: which streets carry a tram, not where.
- Ships: rails paired into tracks, one primitive, one draw call, no collider; heights from the
  nearest level-0 centreline via `fares.Segments`. `city.json` 10 → 11, key optional and nullable.
  Cost +178,688 B PCK (+0.43%).
- ⚠️ Failures that render as nothing: winding (`mitres` offsets left; 5,111 of 5,112 inverted under
  `cull_back`) → `TramwayReport.inverted` must be 0. Bed flared at sheet boundaries → trimmed to
  where both rails run. Mutual-only pairing lost 38 of 132 parts (iB1000 is split per sheet) →
  one-way vote too, 8.
- ⚠️ `drawn_gauge_m` is confined to [0.717, 1.417] m by `pair_tolerance_m` and cannot detect a
  cross-track pairing; the detectors are `off_gauge_stations` (53 of 1,041) and `pairs` vs `tracks`
  (74 → 55).
- ⚠️ Godot 16-bit vertex compression applies to this mesh (`roads.glb` escapes it only because its
  marking codes do not fit); `verify_tramway.gd` bounds must allow for it.
- `rail_metallic` ships 0.0: metal reflects the sky and 0.65 rendered the rails sky blue. The cue is
  `rail_roughness` 0.28 against the road's 0.95.
- Tram stops (TD Tram Stop Location, 19 in region) ship as `poi` with no schema bump. The source
  publishes no name, so `name_en`/`name_zh` are optional roles; `pickup`/`dropoff` are stated false.
- Not done: platforms (⚠️ the centreline is invariant under widening, so a centre-island platform
  registers better than anything kerbside), `RM1045`/`RM1046`/`RM1034`, collision
  (`verify_tramway.gd` fails on any collider).
- Deliberately not refactored: `_Rails` vs `tools/carriageway_margin.py`'s `_Index` (the grader's
  independence is a property); the tiled/untiled source block shared by `tramway.read_rails` and
  `carriageway_margin.published_edges`; `verify_tramway.gd`'s scaffolding shared with
  `verify_road_surface.gd` — a third copy should force extraction into `mesh_contract.gd`.
- Lesson: `ART_DESIGN.md` was misquoted in two places as wanting inset geometry; a claim can be
  unsupported by its citation and still be true — only measuring settles it.

**See.** `Q57` `Q53` `Q54` · `.claude/rules/tramway.md` · `ARCHITECTURE.md` (`tram.glb`)

---

## `Q59` — The arrows are published, and lane space is the answer

**Status.** Closed by `P3-15` · Owner `pipeline/arrows.py`, `hong_kong.yaml` `arrows:`

`DTAD_RD_MARK_SYM_PT` turn arrows ship as `arrows.glb` (747 at landing): one primitive, one draw
call, no collider, position and normal only. `city.json` 11 → 12. Cost +159,636 B PCK (+0.39%).

- Position is read as a fraction across the carriageway, which picks a drawn lane — data, not
  geometry (`Q54`). `Q58`'s refusal does not transfer: the ribbon contains the real carriageway
  (97.2% of symbols on it; gap ÷ half-width p50 0.51), where a tram rail sits off it.
  ⚠️ The denominator is now the surveyed `width_m`, never `lanes × lane_width_m` (`Q96`).
- Alternative kept on record: draw at the published position; the arrow then sits ~1 m off the drawn
  lane centre and reads as a rendering fault. `lane_shift_m` publishes what the choice moved
  (p50 1.11 m, max 5.84).
- Heading is `(90 − ANGLE) mod 360`: 97.8% within 10° of the host on `RM1017`, against 2.9% as-is.
  One publisher, so no second source; `tests/test_arrows.py` asserts it against `fares.Snap`.
- Codes are transcribed from TD drawing CT174/51-5(1)F (scanned, in `etl/sources/`), never from the
  histogram. ⚠️ Not turn arrows: `RM1116`–`RM1119` WARNING ARROW (61 in region), `RM1135`/`RM1136`
  LOOK RIGHT/LEFT, `RM1167`–`RM1169` cycle, `RM1144`.
- Refused: arrows against a one-way host (9 of 761), and re-matching them to the nearest agreeing
  edge — a missing arrow costs nothing against a misplaced one. ⚠️ The axis test folds modulo 180;
  the facing test does not (two-way hosts split 52/48).
- ⚠️ `axis_residual_deg` is recorded over refused symbols too (`n` > `drawn`); appended after the
  guard it is bounded by `bearing_tolerance_deg` by construction (max 28.87° against a 30° bar).
  Residuals publish p90/p99/max: a near-zero median is also what a broken join looks like.
- `symbol_size` is published and unread (populated on 2 of 747).
- Separate mesh, not a codec field: `TEXCOORD_1.x` is a full per-edge constant, the junction fade
  (`fade_m` 6.0) blanks where arrows live, and lifted geometry is immune to the cap overlap (`Q53`).
- No vertex colour: paint stays outside `Q33`'s exposure rule, in a `.tres`;
  `MeshContract.check_surface` has `expect_vertex_colours` so the exception is stated at the call.
- ⚠️ Heights come from the host edge's own polyline, not a second snap (43 of 747 took an endpoint
  from another edge, up to 0.515 m off). The sign is load-bearing on two-way hosts.
- ⚠️ Opaque: `paint_opacity` next door mixes into the road's albedo; on a lifted surface `ALPHA` is
  a sorted transparent pass.
- ⚠️ Godot winds front faces clockwise, glTF counter-clockwise: the ETL and engine winding tests
  have opposite signs on purpose. Settled on meshes that render (`roads.glb` 32,222 of 32,233,
  `tram.glb` all).
- ⚠️ The glyph origin is assumed to be its centre; nothing downstream can detect otherwise.
- Do not ship an attribute nothing reads (a `TEXCOORD_0` was dropped, 59,300 B).

**See.** `Q53` `Q57` `Q54` `Q58` `Q96` · `.claude/rules/arrows.md` · `ARCHITECTURE.md`

## `P3-16` / `P3-17` — Signs and signal heads ship as sourced geometry, scope-limited

**Status.** Closed — `P3-16` shipped; `P3-17` was built, then removed (`Q77`, `Q133`)

Plan for both layers in `Q58`/`Q59`'s pattern (one primitive, one draw call, no collider, optional
`city.json` key, self-published counters). Not gated on `P3-9a`, on the user's call. No new fetch:
both layers are in `dTAD_IRNP.gdb.zip`.

- Region: `DTAD_TS_ABV_PT` / `DTAD_TS_POLE_PT` 3,276 signs over 193 `SIGNID`s, 2,227 poles;
  `DTAD_TRAFFIC_LIGHT_PT` 913 heads.
- Refusals: no pictogram or text faces at the time (no-texture contract; since amended — `Q63`,
  `Q65`, `P3-20`); no invented signal state (nothing publishes timing; route is `B3` with `P3-3`'s
  traffic); no colliders before `P2-6` measures the device floor (breakaway poles are `B3`).
- `~/hk-traffic-sign-map`'s `signCatalogue.json` is cross-check only, never authority; the whitelist
  transcribes TD's own `TS` sheets (`Q64` is what breaching this cost).
- The instruction subset duplicates the graph (NO ENTRY vs one-way, turn signs vs the 217 turn
  restrictions), so a report-only second-source diff is owed — landed, see `Q62`.

**See.** `Q58` `Q59` `Q54` `Q56` `Q15` `Q77`

## `P3-16` — Signs ship where the poles are, because the sign layer is a drawing

**Status.** Closed — `signs.glb` shipped; face table amended by `Q64`; live counts in `signs.json`

Landed as 583 plates on 443 posts (`city.json` 14 → 15); later counts in `Q64`, `P3-22`, `Q67`.

- `DTAD_TS_ABV_PT` is a label layer: 0 of 3,276 points sit on a pole (nearest p50 2.63 m). Position
  comes from the pole through `GG_NAME`, which resolves 92.6% to exactly one pole; none or several
  is refused, never dragged to the nearest. `GG_NAME` is reused kilometres apart, so a 15 m cap
  applies (taken from `~/hk-traffic-sign-map`); `pole_offset_m` republishes the distribution.
- 🔴 Nothing publishes the facing. `ANGLE` is the MicroStation cell rotation and is flat against the
  road (p50 44.2°; 19.2% along, 18.1% across, 22.2% uniform). It is published as
  `axis_residual_deg` and consumed by nothing. ⚠️ Comparing it to a grid angle rather than a game
  heading manufactures a 76.3% "across" mode — an artefact of Wan Chai's grid.
- Facing is derived: host tangent + kerb side + drive-on-left (`Snap.heading_deg`, sign of
  `Snap.offset_m` asserted against `surface.mitres`). ⚠️ On a one-way edge both kerbs face back
  along it; without that branch `no_entry_with_flow` read 117 of 253, now a 0 self-check.
  `no_entry_on_two_way` (6) is a report-only diff. The derivation is ungraded (`Q62`).
- Scope: shape, never text; refusal rests on the no-texture contract (`Q63`), not `Q42` or hard
  rule 8. No dimension is published (sheets are NOT TO SCALE): plate size, mount height and pole
  diameter are authored.
- ⚠️ Stack order is the sheet class (regulatory above supplementary), not `SIGNID`.
- Position across the road is registered onto the drawn kerb at `outset_m` (`Q60`'s move): 77.3% of
  poles were surveyed inside the then-drawn ribbon. `max_shift_m` 6.0 is a pathology bar, not a
  tight one. Refused: iterating the push — residue 22.1% → 10.6% → 9.7%, never zero, while worst
  shift goes 5.52 → 16.77 m; the residue is dropped as `in_carriageway`. `Q78` made the push
  outward-only.
- Coincident poles (33.1% within 0.6 m; several `GG_NAME` groups per post) are merged, greedily over
  a sorted input for determinism.
- ⚠️ Geometric defects no counter saw: plate must stand off the post's front tangent; rotated arrows
  take reach and cross separately; `layer_lift_m` 4 mm z-fought (now 0.018 in config). A distant
  screenshot is not a render check.
- `signs.glb` ships `COLOR_0` (four colours, one draw call) and needs `colour.gdshaderinc`'s
  `vertex_srgb_to_linear`. This is the one prefix-scoped exemption to `Q33`'s palette rule; any
  other colour key still fails `test_no_colour_escapes_the_materials_table`.
- `cull_back` with plates drawn twice (face and grey reverse); `facing_away` must be 0 — the pole
  ring shipped 3,200 triangles backwards on the first build.
- No collider is a budget call, not a correctness one; breakaway posts are `B3`.

**See.** `Q60` `Q61` `Q62` `Q64` `Q78` `Q33` `Q15` · `.claude/rules/signs.md`

## `P3-18` — Box junctions ship as read polygons

**Status.** Closed — `boxjunctions.glb` shipped; height join replaced by `Q92`

All 20 `DTAD_YL_BOX_POLY` polygons: one primitive, one draw call, no collider, position and normal
only; `city.json` 12 → 13. Border 300 mm, hatch 100 mm, spacing 2000, read by eye off CT174/51-5(1)F
`RM1038`. Purely visual — a blocking penalty contradicts `GAME_DESIGN.md`; any hook is `B3`.

- Hatch is triangles, not a shader: a lifted fill needs alpha blend (sorted pass) or scissor
  (re-aliases) to show asphalt between stripes.
- Drawn at the surveyed extent and never scaled to the ribbon — stretching an extent is invented
  geometry (`Q54`). Registration counter `nearest_node_m` (p50 3.67 m, max 52.88 m — a box on a
  crossing the graph does not drive).
- Hatch direction: `ANGLE1`/`ANGLE2` on 4 of 20, converted as arrows; else min-area-rectangle long
  axis + 45° (residuals 0.3 / 5.6 / 29.3 / 35.9° mod 90; beats nearest-edge heading 3 pairs to 1).
  `hatch_angle_residual_deg` is republished each run.
- Heights: the original distance-weighted blend (`height_blend_m`) left 23.2% of the mesh under the
  asphalt; `Q92` deleted `blended_height` and `surface.DrawnSurface` reads the cap fan.
  Near-vertical shards are caught by `verify_boxjunctions.gd` faces-up while ETL `inverted` reads
  0 — keep both.
- ⚠️ Godot's importer quantises positions to a 16-bit lattice over the mesh AABB (~17 mm
  region-wide); a triangle thinner than the pitch can flip winding (217 of 12,181 did). Triangles
  under two quanta are dropped per triangle, not per polygon; `slivers_dropped` and
  `import_quantum_m` ship. Every thin mesh inherits this.
- `lift_m` 0.012 sits below arrows' 0.015 so arrows paint over boxes; border at `border_lift_m`
  0.002 above the hatch. The hatch is not clipped to an inward offset (self-intersects on concave
  rings); `degenerate_border_segments` 7.
- ⚠️ A burial is never answered by raising `lift_m` (`Q92`).
- Unread: `RM1038` companion lines, `RM1140` KEEP CLEAR.

**See.** `Q53` `Q56` `Q59` `Q92` · `.claude/rules/boxjunctions.md`

## `Q60` — The railings are published, their vocabulary is not, and the position is registered

**Status.** Closed by `P3-19`, which ships `railings.glb`

`DTAD_RAILING_LINE` joins to the graph as `(edge, side, V-range)` in `kerbside.py`'s machinery and
is drawn on the kerb the ribbon actually has. No collider. `city.json` 13 → 14, key optional.

- The only layer whose vocabulary the publisher does not define: `LINETYPE` has 19 values and no
  domain, and no index-plan sheet has a railing row. `drawn_line_types` is a whitelist on the code
  strings, not a type map; no claim is made within a class. Refused metres are published per code.
- 🔴 No physical dimension or appearance is published. `SYMBOL_SIZE_*`/`SYMBOL_STEP_*` are plot
  symbology in inches (null on all 196 bollards); `COLOR` has no domain; `LINE_*` are null.
  `height_m` 1.1, `station_m` 2.0, `outset_m` 0.6, `base_sink_m` 0.25 are authored and say so.
- Position: the longitudinal extent is read and never stretched; the lateral offset is a rigid move
  onto the drawn kerb, because 67.9% of published metres fell inside the then-drawn ribbon.
  `max_shift_m` 3.0 keeps two-thirds of the metres; beyond it the object is a plaza edge or
  footbridge balustrade, not a kerb railing. Applied per sample, not per run. `shift_m` is recorded
  over refused samples too.
- A buried kerb is not a kerb: `roadsurface.json` publishes `carriageway[].kerb_hidden_m`
  (`SURFACE_MANIFEST_SCHEMA` 5) rather than letting a second stage recompute coverage (`Q56`).
- ⚠️ `features` counts features, everything under it counts parts. `metres_bridged` is the only
  invented length (gaps ≤ `bridge_gap_m`; 3.6% at landing). Dropped metres are two counters in two
  frames (published vs ribbon) and no identity holds across them. `on_structure_m` is kept apart
  from `refused_m` — 1,579 m of whitelisted `CRAIL1` sits on a flyover parapet.
- ⚠️ `railings.gdshader` is `cull_disabled`, the only generated mesh that is; winding decides
  lighting. `facing_away` must be 0, and `verify_railings.gd` reads `render_mode` from the shader
  source. `rail_metallic` 0.0 (`Q58`).
- Grader `tools/railing_error.py` shares no code with the join; side-of-street disagreement must be
  0 (0 of 17,111). ⚠️ A quad's "two lowest corners" per triangle is its diagonal — the first version
  over-read length by 49%.
- No collision by design (`GAME_DESIGN.md`: omit or make breakable); consistent only because the
  fence stands on the drawn kerb and narrows nothing. Breakaway is `B3`.
- Cost +255,208 B PCK (+0.611%).

**See.** `Q54` `Q56` `Q58` `Q59` `Q61` `Q78` · `.claude/rules/railings.md`

## `Q61` — The fence is coverage-masked, and the layer draws three classes

**Status.** Closed by `P3-19`'s follow-up

- The opaque panel read as a white concrete parapet. The opacity objection belonged to paint
  (`Q59`); here the railing is the bundle's first transparent material, with nothing to sort
  against, and `depth_prepass_alpha` covers self-overlap. `bars()` integrates the pulse train over
  the fragment's `fwidth`, so nothing shimmers.
- ⚠️ `ALPHA` is coverage computed from authored dimensions, not translucency; there is no opacity
  uniform and must not be one.
- `railings.glb` ships `TEXCOORD_0` = (metres along the fence line, metres above the deck), +82,900
  B. `u` is the fence line's arc length, not the centreline's; `v = 0` is the ground line.
- Colour is dead-neutral grey, classes separated by value only; the sky supplies the cool cast
  (a +0.03 blue albedo read B−R +11.5 against neutral's +5.7). The check is the frame.
- The data can source the class and nothing finer (`Q60`'s columns are cartography). Classes:
  `railings` (`CRAIL1` `CRAIL2` `HCAIL2` `RAIL1` `RAILING1`), `bollards` (`bollard0..3`), `barriers`
  (`CBARRIER` `CRASHGATE`). Still refused: `AMT*` (1,099 m — suffixes only look like dimensions),
  `SOLID`, `EAG 3`/`MSB 5`, and the flyover parapet (needs level-aware assignment, `Q15`).
- ⚠️ A class is a parameterisation of one `railings.gdshader` via six mask numbers in its `.tres`; a
  class handed the wrong `.tres` renders perfectly, so `verify_railings.gd` checks dispatch per
  class. Bollards are flat masked quads.
- `RAILINGS_MANIFEST_SCHEMA` 1 → 2 (3 today): top-level `drawn_m` removed rather than broadened.
  Run parameters are per class (bollard median length 1.00 m against the fence's `min_run_m` 4.0).
  The class is part of the cell key. `config._railing_class` refuses an id ending `-col`.
  `samples*` counters stay shared; per-class `read_m` vs `drawn_m` shows a class that joins nothing.
- Three draw calls. Collision stays `B3`: a fence moved up to 6.24 m is a cue; collidable, a wall in
  the wrong place.

**See.** `Q60` `Q59` `Q58` · `ART_DESIGN.md`

---

## `Q64` — The sign table took a sibling project's description over the publisher's sheet

**Status.** Closed — face table corrected

- `TS182` is ONE WAY TRAFFIC and `TS183` is NO STOPPING (CT174/51-1(1)C, anchored on `TS174`). The
  table was shifted one row: 11 mislabelled plates shipped and 155 `TS182` were refused. Fixed with
  no texture: 583 → 706 plates, 443 → 541 posts.
- Cause: `signCatalogue.json`'s `desc` strings are shifted across `TS181`–`TS183` while its crops
  are right. The sheet is the authority; the catalogue is cross-check only — the rule existed and
  was not followed.
- ⚠️ A correctly drawn sign meaning something else passes every counter; only a human reading the
  code beside the publisher's cell catches it. A mislabelled sign must never ship.
- Prohibition bar `_SLASH_THICKNESS` 0.097 of the diameter, measured off the cells (was 0.130) — the
  one measured sign dimension; a proportion survives a NOT TO SCALE sheet.
- ⚠️ A `disc` is a 12-gon (`disc_segments: 12`): a full-diameter saltire pokes out at 45°, so
  `TS183` draws at 0.95. A saltire is two layers, not one `cross` word, or its bars are coplanar.

**See.** `Q59` `Q63` `Q60` `P3-20`

---

## `Q63` — The bundle carries no undeclared image

**Status.** Closed, on the user's call — contract amended narrowly

- What refused sign lettering was `mesh_contract.gd` (no shader uniform may hold a `Texture`), not
  `Q42` or hard rule 8. The load-bearing reason for no textures is `merge` refusing textured
  buildings (draw calls); it does not apply to `signs.glb`, which is its own draw call.
- `check_surface` gained `texture_budget_px`: 0 by default (the old refusal); a declaration buys a
  ceiling, summed across the surface; a declared texture that never arrives also fails (it would
  otherwise sample white silently). Refused: deleting the check and trusting a generous budget.
- ⚠️ The declaration is a call-site parameter, not a `city.json` key. `AtlasTexture` is measured at
  its underlying image; `PlaceholderTexture2D`, layered and 3D textures are refused as unmeasurable.
- `tools/verify_mesh_contract.gd` asserts the refusal paths on its own one-triangle meshes (no built
  region, runs in CI), for both `ShaderMaterial` and `BaseMaterial3D`, each expecting exactly one
  problem; mutation-checked.
- The one declared texture today is the signs text atlas, `GeneratedSigns.TEXT_ATLAS_BUDGET_PX`
  (`P3-20`, `Q68`). Tile textures are `P5-14`.

**See.** `P3-20` `Q64` `Q65` · `ART_DESIGN.md`

---

## `Q65` — The sign estate is scoped to what tells the player where to drive

**Status.** Closed, on the user's instruction

- Out of scope as content: time plates, parking, no-stopping zones, vehicle-class prohibitions
  (~2,100 of 3,276 signs).
- Shape-only direction codes, read off TD's sheets, ship with no texture (`P3-22`): `TS414`,
  `TS735`, `TS615`, `TS589`. Composite glyphs bake as one `draw` word (`_bent_arrow`,
  `_u_turn_arrow`), not a per-layer offset in the face schema.
- GIVE WAY 讓 (`TS102` ×74) and STOP 停 (`TS101` ×18) need lettering, so the atlas shrank from 193
  cells to two. Shipped by `P3-20` as a second primitive inside `signs.glb`, keeping the untextured
  majority byte-identical (`mesh.py` refuses to merge meshes with and without UVs) — `Q68`.
- Refused: bend and narrows warnings `TS401`–`TS418` — 13 new primitives for 53 plates.
- Held: speed limits (`TS174` ×37, `TS175` ×28) — a ten-numeral atlas is the cheap route.
- Refused: `P3-21` road lettering — no instruction the graph does not give, and it needs a licensed
  typeface. Findings kept: `DTAD_RD_MARK_ANNO` is `MultiPolygon` rotated rectangles, 67 distinct
  strings.

**See.** `Q64` `Q63` `Q68` `P3-22`

---

## `Q66` — A deviation board's direction is derived, because nobody publishes it

**Status.** Closed — shipped on a stated, ungraded assumption (`Q62`-class)

- TD codes direction for NO THROUGH ROAD (`TS615`/`TS616`/`TS617`) but not for chevron boards
  (`TS414`, `TS588`, `TS589`); the sheet's drawing is indicative. A fixed direction is wrong on
  about half and renders perfectly.
- Assumption: chevrons point away from the kerb the post stands on, into the carriageway, reusing
  the side `_facing_from_side` consumes. `+u` is the viewer's right, glyphs are authored for the
  offside, and the nearside board is mirrored.
- Counters `boards_mirrorable` / `boards_mirrored` (11 / 4 at landing): either extreme means the
  kerb side stopped being read. They are named for the board, and one `_mirrors()` decides both what
  is drawn and what is counted.
- 49 of 61 `TS414` and all 10 `TS589` are on structures (`Q15`), so 11 boards draw and `TS589`
  draws none here; its `board_tall` kind and `yellow` are kept as publisher vocabulary.
- ⚠️ A chevron is concave and `_Builder.polygon` fans from vertex 0: split into convex quads.
  Mirroring reverses winding silently (`facing_away` stays 0): `[::-1]` restores it, pinned by
  `test_a_mirrored_board_flips_its_glyphs_and_keeps_its_winding`.
- ⚠️ Orientation is asserted on the chevrons in both halves; whole-mesh extents are symmetric about
  `u` and assert nothing. Mutations `side > 0.0` → `<` and `_chevrons` authored `+u` once passed.
- `_straight_arrow` spans ±reach: size `TS735`'s two arrows accordingly.

**See.** `Q65` `Q64` `Q15` `Q62`

---

## `Q62` — The turn-restriction diff cannot grade the sign facing

**Status.** Open on the facing (derived, ungraded); the diff shipped as a report-only counter.

- The facing is derived from host edge + kerb side + drive-on-left; dTAD publishes none and `ANGLE`
  is the label rotation. `TS131`/`TS132`/`TS133` were matched against `roadgraph.json`'s 217 turn
  restrictions to grade it.
- Refuted: mirroring the whole region moved `turn_sign_agreed` 29 → 30. `_facing_from_side` turns
  both kerbs of a one-way to face its traffic, and `turn_sign_on_one_way` is 62 of 68, so only six
  plates can speak to the kerb side.
- What it does grade is `Q64`'s class (wrong code, renders perfectly): Wan Chai `agreed` 29,
  `disagreed` 14, `unmatched` 25 (= 68 = `TS131` 38 + `TS132` 25 + `TS133` 5);
  `turn_sign_to_junction_m` p50 18.86. The 14 disagreements are the live finding.
- ⚠️ `unmatched` is not a failure: the graph carries 34 banned lefts against 38 drawn `TS131`. Read
  `agreed` against `disagreed` only. Report-only, never a bar (`Q56`): `P1-3` reads `EXC_VEH_TYPE`,
  `PART_TIME_REST`, `EFF_ALL_DAYS`, `OTHER_REST_TYPE` and emits none.
- The graph publishes no movement type, so the class is read off the signed heading change:
  `turn_straight_deg` 30, `turn_u_deg` 135 (`hong_kong.yaml`). Over 217: 99 right, 80 U, 34 left,
  4 straight; all resolve. `TS133` needs no branch: leaving by the arrival edge is exactly 180°.
- ⚠️ Test trap (`Q66`): a movement at exactly 0° and a post at `t` 0.5 are symmetric under the
  mutations they guard; the tests use opposite-leaning arms and `t` 0.25.
- A facing or position on this layer cannot be graded against anything published, so the evidence
  for a change is an A/B render at one fixed camera.

See `P3-16`, `Q56`, `Q64`, `Q66`, `Q72`.

---

## `Q67` — Sign faces are graded against TD's sheet by an instrument, not by eye

**Status.** Closed; four glyph-weight rows remain recorded, not fixed.

- `pipeline/sign_sheets.py` resolves a `TSnnn` to its cell on the TD index plan;
  `tools/sign_face_survey.py` rasterises the config face and compares, per colour, the area
  fraction and the bounding-box extent inside the plate outline.
- ⚠️ Extents as well as area: `TS115`'s shipped bar (0.66 x 0.22) and the sheet's (0.868 x 0.187)
  had the same area within four points. ⚠️ The converse: `TS102`'s field reads 0.79 wide against a
  drawn 0.72 only because the sheet's corners are rounded; area agrees, so it was left alone.
- 🔴 The row is counted, not read (sheets have no text layer): filename range plus grid position.
  The grid is asserted — `blocks x rows` must bracket the filename's span or the sheet is refused.
  Sheets in use recover as 5 x 21. Row rules are solved as a lattice (a chain locks onto double
  pitch); column blocks come from the sheet's regularity (gutters and grey fills add rules).
- Found and fixed: `TS414` drawn in negative (the sheet is a black board, white chevrons), plus
  four proportion errors. The prohibitory ring is one number: 0.10 of the diameter.
- Still disagree, all glyph weight (re-cut the draw word, not a config number): `TS733`/`TS734`
  black 0.286 vs drawn 0.478 (`_straight_arrow` ties stem thickness to `reach`, the long axis on a
  2.4-aspect plate); `TS589` white 0.341 vs 0.139 (`_chevrons` is right on `TS414`); `TS182` white
  0.290 vs 0.224 (`head_half` capped at `0.52 * reach`); `TS615` red 0.083 vs 0.035 (`_tee_bar`).
- ⚠️ It looks a face up by its code, so a face under the wrong code agrees with itself; `--contact`
  writes every graded cell to one page for looking. It grades and exits 0.
- ⚠️ The sheet is classified by hue family, not against `signs.colours`: the livery is muted, TD
  prints saturated primaries, and the first version read every blue disc as white.
- `rank` is the publisher's sheet class and a stack order: `TS414`/`TS589` are WARNING
  (CT174/51-2), `TS615` INFORMATORY (CT174/51-3(1)). `TS589` has no TC number on the sheet.

See `Q64`, `Q59`, `Q60`, `Q68`, `P3-22`.

---

## `Q68` — Sign lettering is read off the drawing into one opaque atlas

**Status.** Closed (`P3-20`); two debts open — the survey's plate box and the pole standoff.

- `TS102` GIVE WAY / 讓 (74 plates) and `TS101` STOP / 停 (10 drawn of 18 published) carry
  lettering. Atlas 512 x 256, `text_plates` 84, `text_atlas_px` 131,072, `text_coverage` `TS102`
  0.278 / `TS101` 0.193, `text_facing_away` 0.
- Opaque RGB, no alpha, no `discard`: the field colour is baked behind the glyph from
  `signs.colours` at build time, so the sign layer stays out of the transparency pass and gains no
  `ALPHA` dial. The PNG is generated city data (hard rule 7).
- Placement is read: the cell is cropped to the plate's bounding box and the lettering box is a
  fraction of it (`plate_rect`). The face schema stays `(draw, colour, size)`; `size` is ignored
  on a `text` layer.
- A second primitive in `signs.glb`, not a second file: `TEXCOORD_0` on every sign vertex would
  cost 292,928 B to serve the lettered plates. +1 draw call.
- Polarity is derived, not flagged: the `text` layer's `colour` against the layer beneath it
  (lighter than its field is a knockout). `TS101` is white knocked out of red; black ink covers
  0.0000 of its cell. `config.py` refuses a leading `text` layer (no field to sit on).
- 🔴 The plate box is the ink connected to the white it encloses (`sign_sheets.enclosed_white`).
  TD's red dimension extension lines sit outside the plate: on `TS101` a bare ink box read 308 px
  where the octagon is 269, shipping lettering at 0.873 size.
- 🟡 Open: `sign_face_survey.measured()` still uses the uncorrected box on 10 of 21 faces
  (`TS101`, `TS106`–`TS112`, `TS414`, `TS615`); extent rows read small by up to that ratio, area
  rows are unaffected. Fixing it moves ten published rows and is owed its own diff.
- ⚠️ The octagon's vertices sit at `22.5 + k * 45` degrees (flat top); `k * 45` renders as a
  rotated square. `octagon_height_m: 0.60` is across the flats and authored (`Q60`).
- The budget is a ceiling (`SIGNS_TEXT_ATLAS_BUDGET_PX` = 512 x 256 in `generated_layer.gd`);
  `verify_signs.gd` fails over it and on a missing material dispatch. Both mutation-checked; a
  missing atlas samples white and is invisible in a frame.
- ⚠️ `check_shader_material` cannot check the lettering: the material is duplicated at import and
  has no `resource_path`, so `check_shader_source` checks the shader. Never use it to quiet its
  sibling — it would pass a surface that should share a material and does not.
- 🔴 `layer_lift_m` is two-sided and empirical: 0.012 glyphs fight their plate, 0.018 clean at 2,
  6 and 15 m (shipped), 0.024 the pole shows through the plate, 0.030 clean. Mechanism not
  isolated. 🟡 Open: `face_centre` stands the plate off by exactly `pole_radius_m`, so plate and
  post are tangent; the standoff should clear the pole.

See `Q63`, `Q65`, `Q67`, `Q70`.

---

## `Q69` — A stop line's host is the road it crosses, not the road it is nearest

**Status.** Closed (`P3-23`). Height source superseded by `Q92`.

- `roadmarks.glb` draws `RM1011` STOP LINE, `RM1012` STOP LINES and `RM1013` GIVE WAY LINES from
  `DTAD_RD_MARK_LINE`. One primitive, one draw call, no collider, texture or `COLOR_0`.
  211 parts (209 at grade) → 191 drawn: `stop_line` 114, `give_way_lines` 75, `stop_lines` 2.
- 🔴 Nearest-edge hosting is wrong here: a stop line sits at a junction mouth, about a metre off
  the major road's kerb. `|90° − angle to host|` p50 10.8 (`RM1011`) / 16.5 (`RM1013`) under
  nearest edge against 1.8 / 4.0 under the transverse pick; `host_disagreement` 90 of 209.
- Rule: among level-0 segments within `host_radius_m` (20), minimise
  `|90 − angle| + proximity_weight_deg_per_m (0.05) × distance`. Proximity only breaks ties.
- ⚠️ A wrong host does not move the paint (the extent is published); it moves the height, the
  refusal and every counter.
- ⚠️ `axis_residual_deg` grades the quantity the rule optimises (`Q58`'s trap); the counter that
  can see a regression is `host_disagreement`.
- Sheet `CT174/51-5(1)F` is a scan, so `Q67`'s rasterise-and-diff does not transfer. Line width
  200 on all three; `RM1012` spacing 300, continuous; `RM1013` spacing 200, 600 mark / 300 gap — a
  double broken line, not triangles.
- ⚠️ `LINES SPACING` is the clear gap, not a pitch: `RM1001` publishes width 150, spacing 100.
- Not published: which of a double line's two lines the polyline is (drawn symmetric, worst case
  0.2 m), and the dash phase (anchored at the line's start).
- The length is the publisher's, never stretched to the kerb (`Q54`). `underfill_m` reads the
  drawn half-width from `roadsurface.json` `carriageway[].half_width_m`, never `roadgraph.json`'s
  `width_m` (that was an 18x error), so `roadmarks` runs after `surface`.
- `no_transverse_host` 18 of 209 are refused and counted, never rotated onto a road (`Q54`).
- ⚠️ `_runs` uses `index * period` with a `_MIN_MARK_M` floor; `start += period` drifted and
  emitted a 3e-16 m mark into `slivers_dropped`.
- ⚠️ The partition is over parts, not features (4,162 vs 1,679 on the layer). `lift_m` 0.016 sits
  above `arrows.lift_m` 0.015 on purpose: a stop line is the boundary, an arrow already read.
- **Superseded by** `Q92`: `blended_height` is deleted; this stage and `boxjunctions` read
  `surface.DrawnSurface`. 20.0% of the mesh had shipped under the road.

See `Q53`, `Q54`, `Q58`, `Q59`, `Q60`, `Q92`.

---

## `Q70` — Everything under `game/assets/generated/` is named by the manifest

**Status.** Closed.

- An image embedded in a `.glb` is extracted by Godot's importer to `<stem>_<index>.png` beside
  the asset; `sync_generated.sh` rightly sweeps what `city.json` does not name; an unchanged
  `.glb` is not re-imported, so `verify_signs.gd` went red on alternate runs.
- Decision: name the file, never exempt it from the sweep. `Texture` has a `uri`, `write_glb`
  writes `signs_text.png` before the container (one owner for reference and referent), and
  `city.json` names it under `signs_text_atlas`.
- Refused: `gltf/embedded_image_handling` = Embed as Uncompressed — ~262 KB raw against a 28.5 KB
  PNG (about +0.5% of the PCK) and no mipmaps.
- ⚠️ `signs.json`'s `bytes` is `signs.glb` alone; `text_atlas_bytes` is the image.
- ⚠️ On a fresh clone the PNG must import before the GLB; otherwise the texture is null and
  `verify_signs.gd` fails loudly on the declared-texture check.
- ⚠️ A generated directory can have a second, invisible writer (the engine's importer). Any new
  image owes the same treatment.

See `Q63`, `Q68`.

---

## `Q71` — One paint shader, three materials

**Status.** Closed. The shader is `game/assets/shaders/marking_paint.gdshader`.

- `arrows`, `boxjunctions` and `roadmarks` shaders were byte-identical but for a dead default
  colour. Merged on the repo's own rule (`mesh_contract.gd`, `Q58`): a third copy forces the
  merge. A layer is a parameterisation, not a shader (`railings.gdshader`'s precedent); colour
  lives in each layer's `.tres`.
- Dispatch still holds: `MeshContract.check_shader_material` compares the material's
  `resource_path`, so a box junction handed `roadmarks.tres` fails. ⚠️ `check_shader_source` is
  for the duplicated sign lettering (`Q68`) only.
- ⚠️ A shader change is a change to every layer sharing it: render each and grep for
  `SHADER ERROR` — `check.sh` exits 0 on a shader that fails to compile.
- ⚠️ Closed `DECISIONS.md` records naming the old shader files were left as written; a comment
  citing a deleted file is invisible to every check, so grep both `game/` and `etl/` on a rename.

See `Q58`, `Q61`, `Q68`.

---

## `Q72` — A NO ENTRY faces the traffic it forbids

**Status.** Closed. The facing stays ungraded (`Q62`).

- The facing is a property of the plate, not the post, so back-to-back plates are representable.
  `SignFace.faces_against_traffic` (config) is set on `TS115` and `TS116` only;
  `_plate_facing_deg` turns such a face 180° off its post. 82 of 499 drawn posts carry both a NO
  ENTRY and a forward-instruction sign.
- Refused: detecting a central divider by an opposed carriageway within radius `R` — the count
  runs 8 → 29 → 49 → 80 as `R` goes 10 → 30 m, so `R` has no principled value.
- 🔴 The old `no_entry_with_flow` was a tautology that certified the wrong state: every one-way
  sign was turned to face its traffic, so it read 0 while every NO ENTRY was 180° out.
- `no_entry_against_flow` replaces it and is still not data-sensitive (a flagged plate's residual
  is identically 0). It guards config against code: flag off → `plates_turned` 0 and the counter
  173. It grades the union of the flag and `_NO_ENTRY` so it survives the flag being dropped.
  ⚠️ The flag dropped from a face that is not `_NO_ENTRY` is undetectable.
  🟡 Not built: a check reading `_downstream_node` (NO ENTRY at the mouth traffic enters by).
- `plates_turned == sum(by_code[c])` over flagged faces is raised on (197 = 179 + 18). A face may
  not carry both `mirror` and `faces_against_traffic`.
- `signs.json` schema 2 → 3 (the rename is the bump); `city.json` not bumped.
- Not fixed: two plates of the same class back-to-back share one face. `no_entry_on_two_way` (6)
  stays report-only (`Q56`).
- ⚠️ `hk-traffic-sign-map`'s `compute-stacks.mjs` rotates the whole post by the primary's bearing
  — the same bug.
- ⚠️ A counter is tested by whether a reachable configuration moves it, not by whether it is 0.

See `Q62`, `Q56`, `Q58`, `Q66`.

---

## `Q73` — A layer can pass every check and be in no scene

**Status.** Closed; the blind spot is closed by `Q115`'s layer table.

- `P3-23` shipped `roadmarks.glb` with its manifest key, locator, `.tres` and verify tool, and no
  scene node. A verify tool grades the `PackedScene` in isolation, so it answers "is the asset
  correct", never "is it on screen".
- The node is part of the layer. No scene-instantiating check is built (`Q17` keeps `check.sh`
  free of a rendering device); a new layer is looked at in a frame before it is done.
  `verify_city.gd` now holds both scenes' `layer` ids against `generated_layer.gd`'s table.
- ⚠️ A GIVE WAY plate with no bar is still expected: of 121 `TS102` plates, 99 have a drawn line,
  12 have none published within 30 m, 10 have one the transverse join refused.

---

## `Q74` — The preview scripts and loaders were merged

**Status.** Closed by `P5-1` (`Q115`).

- `MeshContract.colliders(node) -> int` defines `has_collision`; `generated_layer.gd` is the one
  loader table; `layer_preview.gd` is the one preview.
- Each layer's own no-collider argument is a node comment in `city_drive.tscn` and
  `city_preview.tscn`.
- ⚠️ The road surface is in the table with an empty `absence`, which makes `is_optional` false
  and its missing asset a `push_warning` rather than a report.

---

## `Q75` — A setting that is no longer set cannot fail

**Status.** Closed. The grep-count guard is superseded by `Q119` (`verify_settings.gd`).

- An editor rewrite of `game/project.godot` silently dropped three warning promotions
  (`native_method_override`, `get_node_default_without_onready`, `onready_with_export`) and
  `renderer/rendering_method.web="gl_compatibility"`. Nothing failed: the warnings sweep reads its
  bar from the file it checks. Restoring all 21 promotions surfaced zero errors.
- Pinned by `check.sh`'s `settings` step, which now runs `tools/verify_settings.gd` (`Q119`): the
  21 promotions by name, `rendering_method.web`, `max_fps.mobile`. ⚠️ Never edit the expected
  values down to match a regression. `ARCHITECTURE.md` "Project settings" owns the rationale.
- Corrected claim: a missing `rendering_method.web` does not break web export — Godot 4.7 forces
  Compatibility on web regardless. The override is stated anyway.
- 🔴 The "recurrence" was three restorations never committed; `git show <commit>:<path>` settles
  such a claim. A fix in the working tree is not a fix.
- ⚠️ Headless `check.sh` leaves `project.godot` byte-identical; `tools/export.sh web` rewrote it
  (`Q77`). Test an intervention against a restored baseline, never the regressed one.

---

## `Q76` — The web build runs Compatibility; the product runs Forward Mobile

**Status.** Closed, as a decision to proceed with the limitation recorded.

- A browser has no `RenderingDevice` backend, so web is always Compatibility (WebGPU:
  `godot-proposals#6646`, unimplemented). An engine fork is refused: it fixes a target that is not
  the product, makes export templates this project's problem, and brings code of contested
  provenance into a commercial binary.
- Measured on `city_preview.tscn`, fixed camera, Mobile vs Compatibility: mean L* 28.3 / 27.0;
  under L* 10 6.0% / 33.1%; the 10–30 band (`Q31`) 27.0% / 0.7%; C* p90 14.2 / 8.7. It crushes,
  it does not dim.
- Refused: a web-only Environment. Ambient `0.85 → 1.8` moved the crushed share 33.1% → 33.0% and
  lowered chroma (8.7 → 8.1); light does not reach the loss, and it would be a second look.
- `P3-9a` runs on Compatibility and its write-up must name the renderer. It may not reopen `Q26`
  or re-price `Q30`/`Q31`: those numbers are Forward Mobile and stay correct for the product.
- ⚠️ Measure a look on a fixed camera in a preview scene, never a driven frame (a driven pair
  reported a 31-point L* gap that was camera position).
- Reproduce: a wrapper `exec godot --rendering-method gl_compatibility "$@"` as `GODOT=` for the
  run skill's `drive.sh` on `city_preview.tscn` (`--camera=163,9.2,28.5 --look=205,6.2,24.5`),
  then `tools/frame_stats.py`. Desktop `gl_compatibility` matches the browser frame.

See `Q75`, `Q31`, `Q30`, `Q26`, `P3-9a`.

## `P3-17` / `Q76` — Signal heads: a vocabulary nothing publishes, one head per assembly

**Status.** Removed — dropped from the bundle by `Q77`, code deleted by `P3-35a` (`Q133`). What a
return must keep:

- 🔴 `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has no domain and no index-plan sheet. The code is a gate
  (head or not: `P<n>`, `S<n>` admitted via `head_prefixes`), never a look — every admitted code
  draws the same head. `drawn_by_code` / `refused_by_code` over the whole vocabulary make the gate
  reviewable. `M<n>` (19, all within 2.57 m of a head) is refused as a judgement; bollards and
  push buttons on scope — a `KLBOLL` legitimately stands in the carriageway.
- `ANGLE` carries no facing: p50 44.3° from the host axis (uniform is 45°). The facing comes from
  `signs.facing_from_side`. `DTAD_TRAFFIC_LIGHT_LINE` cannot cross-check it (`SIGNID` null on all
  53).
- 🔴 An assembly is not a stack: 470 of 913 points are coincident; stacking them drew 8.53 m
  masts that passed every check and were caught only in a render. One head per assembly;
  `assembly_size` publishes the collapse. `drawn` counts features, `posts_drawn` heads.
- 72.7% of points sit inside the drawn ribbon, so the layer takes `Q60`'s registration.
  `host_ambiguous` (18 of 514, report-only) uses `Segments.rivals_within` (`pipeline/polyline.py`).
- `sheeting_glow` must be 0 on a signal material; no colliders; no signal state.
- ⚠️ Defects no counter saw: posts rooted at world y=0 (`_draw_post` lacked `base_y`), the head
  hung behind its post (plate standoff applied to a 0.30 m box), and `_merge_placements` folded
  heads across facings (one at 94.9°; `merged_facing_deg`).
- `signs.disc`, `plate_frame` and `facing_from_side` stay public for it. Cost when shipped: 415
  heads, 26,560 triangles, PCK +598,788 B (+1.40%).

See `Q54`, `Q56`, `Q60`, `Q62`, `Q69`, `Q77`.

## `Q77` — A dark signal asserts "out of service", and a lit one cannot be derived

**Status.** Closed — layer dropped on the user's instruction; code since removed (`P3-35a`,
`Q133`). Bringing it back is a port (`.claude/rules/signs.md`), not a re-declared block.

- Dark is not neutral: a real head is always lit, so 415 unlit heads claim the signals are off.
- A lit one needs what nothing publishes — which heads share a green, stage order, timings,
  clearance intervals. Shared greens are derivable at 18 of 107 multi-head junctions, and 57 of
  137 junctions are partially populated by the in-carriageway refusal, so lighting amplifies the
  gaps. `P3-18`'s purely-visual precedent does not transfer: a green claims the cross street is
  red.
- Honest route: `B3` — `P3-3`'s traffic needs a checkable phase plan; heads then render it via
  `P3-11d`'s `instance uniform` lamp circuit.
- ⚠️ An optional layer's node must guard with `is_present()` before loading: Godot's `load()` on
  an absent path writes `ERROR: No loader found…` before returning null. All four `CACHE_MODE_*`
  make no difference and `load_threaded_request()` only defers the error. A corrupt asset and an
  absent one stay different findings. `check.sh` cannot see this; the browser console did.
- ⚠️ `tools/export.sh web` rewrote `game/project.godot` (`Q75`'s signature); the settings step
  caught it.
- Amended by `Q100`: there is no second city; the optional-block mechanism stands on this record.

See `Q76`, `Q62`, `Q54`, `Q73`, `Q75`.

## `Q78` — Sign registration is a one-way correction

**Status.** Closed. `signs.json` schema 3 → 4.

- Registration exists because the drawn ribbon is wider than the real one, so a post on the real
  kerb lands in the drawn lane. It was an unconditional `target_m = side * (half_width_m +
  outset_m)`, which also pulled 95 posts (14.5%) inward — 36 by over a metre.
- Now a post surveyed beyond `half_width_m + outset_m` keeps its surveyed point
  (`posts_kept_as_surveyed` 95). The threshold is not the bare kerb: that strands 56 posts in the
  0–0.6 m gutter band. Unconditional, no config flag (a rule, not tuning). `in_carriageway` still
  runs on the kept point. `_register` is its own function so the branch is tested directly.
- 🔴 `shift_m` is an absolute value and cannot report its own direction; it appends a real `0.0`
  for a kept post so the identity `len(shift_m) == poles_drawn + posts_over_shift +
  posts_in_carriageway + posts_merged_after_shift` closes (654 = 504 + 0 + 140 + 10).
- ⚠️ `drawn` (681 plates) is the invariant, not `poles_drawn`: kept posts merge less.
  `max_shift_m` can now only refuse a push.
- 🔴 Deliberately not consistent: `railings.py` keeps the unconditional push. A fence is a run and
  the bar is per sample, so a conditional push would kink a straight fence into a zigzag. A point
  object can take this rule; a polyline cannot.
- Not fixed: every pushed post stands on one identical offset because `outset_m` is one constant.
  Per-post jitter is refused (`Q54`: invented position).
- Evidence is an A/B render at one fixed camera (`Q62`): `city_preview.tscn`
  `--camera=932,9,736 --look=958,3.5,757`.

See `Q60`, `Q58`, `Q54`, `Q62`, `Q72`.

---

## `Q79` — The street plate's typeface: Free HK Kai, shipped whole

**Status.** Closed (`P3-24`). Full font as an authored asset, on the user's call over an
English-only plate and over a subset.

- **Free HK Kai 4700 v1.02** (CC BY 4.0, 6.4 MB TTF, 14,061 glyphs, HK glyph forms) in
  `game/assets/authored/fonts/` with its `LICENSE`. HK street plates are set in 楷書; the Latin line
  stays a grotesque, as the real plate does.
- Refused: Noto Sans HK (sans is legible and wrong; OFL forbids derivatives without a rename).
  AR PL UKai — the Arphic licence restricts commercial use, so it cannot be in a store build.
- A bundled third-party font is a fourth owner beside hard rule 7's three: own `LICENSING.md`
  section and a credits line. ⚠️ `assets/authored/` now holds something this project did not
  author; committed anyway because a fetched font would make the UI depend on a build-time network
  call.
- Wan Chai needs 166 CJK characters; the font covers 165. The miss is `啓` (U+5553) in `啓超道`
  (2 edges); the font carries `啟` (U+555F). ⚠️ The ETL does not rewrite the name (`Q54`): the
  substitution is display-side config, applied when the plate is drawn.
- `en` and `zh` are never independently missing, so there is no mixed-language fallback.
- `tools/font_coverage.py` exits non-zero when a published street-name character is in neither the
  font's `cmap` nor the substitution table. Run by hand on a font or street-name change (needs a
  built region). ⚠️ It reads the graph through `pipeline.roads.read_graph`, never `json.loads` — the
  first version reported `streets 0` and exited 0 on a reshaped document. It parses `cmap` directly;
  no `fontTools` dependency.
- Cost: ≈ +15% PCK, the largest single movement. ⚠️ A dynamic font's glyph atlas is the first
  texture that grows at runtime; `Q63`'s declaration check grades generated meshes and cannot see
  it — only the `ARCHITECTURE.md` budget line covers it.
- Open option, not taken: the region uses 1.2% of the glyphs; a subset is ~100 KB and CC BY permits
  it, but it would be an ETL stage with a coverage contract owned by `font_coverage.py`.

See `Q54`, `Q63`, `Q64`, `Q65`, `P3-21`.

---

## `Q80` — HUD layout: a touch zone is not a thumb

**Status.** Closed — `P3-24` passed the user's review 2026-09-06.

- The first rule, "no HUD rect may intersect a touch rect" with tap zones as the rects, was wrong:
  a tap zone is where input is detected (every HUD Control is `MOUSE_FILTER_IGNORE`), a thumb is
  what occludes. NFS No Limits, a touch game, puts its speedometer under the steering thumb.
- `hud_layout.tres`: `touch_steer_*` is recorded for `P2-4` and the HUD may overlap it;
  `thumb_rest_*` (a fingertip in each outer bottom corner) is what `verify_hud.gd` enforces.
  ⚠️ The check also asserts that a rect over a tap zone is accepted, so tightening it back onto
  zones fails the suite. The probe uses the zone's upper half, because a zone contains its own rest.
- Arrangement rule: left is the car, right is the world, top is the fare, the middle is the road.
  Speed bottom-left, plate bottom-right (paired with the future minimap), one baseline at y 860.
  ⚠️ **The sides are superseded by `Q138`** (mirrored); top, middle and baseline stand.
- User's rule: plan the area, do not hold the space — no gaps left for UI that does not exist yet.
- HUD sized to the references (speed ~7% of frame width). `hud.gd::_fit_plate` cuts the plate to its
  lettering, clamps to the reserved width, and grows away from whichever edge the layout pins;
  lettering centres. ⚠️ The speed chip deliberately keeps a fixed bezel.
- The bar under the speed draws acceleration, not revs: no gearbox, so `get_rpm()` is road speed
  (`Q85`). Centre origin, full scale 5.0 m/s² (measured 2.55–3.34 in ordinary driving),
  differentiated every frame and filtered. Green gains, red loses — convention outranks the
  palette rule; `verify_hud.gd` asserts the direction, that the hues differ and that the bed exists.
- Style: flat-shaded like the city. `ChamferPanel` — four cut corners, one fill, one hard keyline;
  no radius, gradient or shadow. White is the city speaking, dark is the car speaking
  (`verify_hud.gd` asserts the plate is lighter than the chip). ⚠️ **Superseded by `Q139`**: one
  dark housing.
- ⚠️ The UI palette deliberately does not reuse the road's paint constants (`Q53`). Taxi red stays
  out of HUD furniture; the bar's red and `Q81`'s sign are the stated exceptions.
- ⚠️ `HudLayout` and `HudStyle` exports carry no defaults, like `HandlingProfile`: a default is a
  second copy that drifts. A key missing from the `.tres` reads zero and `verify_hud.gd` fails it
  by name; probes duplicate the loaded resource, never `new()`.
- The destination arrow belongs in the world, not the HUD (both references with a destination do
  this); `hud_layout.tres` reserves no arrow slot.
- Refused: street name top-centre. It rendered well, but it is the loudest slot for the quietest
  readout, it splits the plate from the map, and the slot belongs to `P3-5a`'s bilingual
  destination callout.

See `Q79`, `Q53`, `Q62`.

---

## `Q81` — The wrong-way sign: an interrupt, and the nose decides

**Status.** Closed — `P3-25` passed the user's review 2026-09-06.

- Wan Chai is 93.5% one-way by drivable length, so the failure that matters is the false alarm.
  `wrong_way_monitor.gd` reads the `Hit` the street plate already fetches at 5 Hz (`Hit.one_way`;
  `RoadGraph._fill` deliberately does not correct `forward` on a one-way edge).
- Heading raises the sign; velocity may only withhold it (a car reversing out of its own mistake).
  Refused by the user: raising on velocity — NO ENTRY means "turn around", and a car facing the
  legal way has nothing to turn. ⚠️ Stated cost: reversing at speed up a one-way street is unsigned.
- Rules (`wrong_way.tres`): raise dwell 0.5 s (junction strobe; 34 streets mix `forward` and `both`
  edges); clear dwell 0.8 s (asymmetric, holds through a junction); nose bar 120°, not 90 (a legal
  turn across a one-way passes through perpendicular); speed floor 10 kph on the withholding side
  only, so a stationary wrong-way car is signed.
- ⚠️ The withholding bar is its own constant, `CORRECTING_ANGLE_DEG` = 90, not the nose bar's 120:
  shared, a sideways drift counted as "correcting". Found by mutation, not by reading.
- ⚠️ Deliberate departure from `street_tracker.gd`: a miss and a two-way edge count toward clearing
  (the tracker holds). A latched alarm can be neither dismissed nor acted on. `stand_down()` clears
  it when the vehicle is freed.
- Top-centre is shared with `P3-5a`'s callout, not taken: the rect is 96 x 96, and the callout
  inherits one constraint — it starts below y 136.
- Icon, not words: NO ENTRY (`TS115`, 179 plates in the region). No typeface, no translation, no
  `font_coverage.py` entry. A disc is signage, not furniture, so `Q80`'s cut-polygon rule stands.
- ⚠️ The bar proportions (0.868 of the diameter, 0.187 thick, `Q67`) are a knowing third copy in
  `hud_style.tres`; `verify_hud.gd` ratchets it against the ETL's. The one place the UI palette
  quotes the world.
- Blink capped at 2 Hz and asserted (WCAG 2.3.1 threshold is three flashes per second); toggles
  `visible`, so a hidden sign queues no redraw.
- Cost: +3 draw calls lit, 0 hidden; the whole HUD is +8.
- `verify_hud.gd`: 23 assertions written from both sides (`Q72`); ten mutations, all caught.
- ⚠️ `verify_hud` can print `ok` having checked nothing: a `preload`ed script that fails to compile
  aborts the calling function, and no in-tool guard can fire. Only `check.sh`'s `SCRIPT ERROR` grep
  catches it — never read a verify tool's output by hand. The same applies to a driver run: a
  file rejected by the promoted-warnings sweep gave `DRIVER OK` with no HUD and exit 0.

See `Q80`, `Q67`, `Q79`, `Q62`, `Q72`.

## `Q82` — Lamp posts: a published vocabulary, an unlit lantern, reachable counters

**Status.** Closed (`P3-26`). Night mode refused as a justification; the layer ships for the
daylight street scene.

- Poles do not prepare for night mode. Night is blocked on `Q38` (`exposure_anchor` baked into
  `COLOR_0`), `Q26`, a single lighting rig and a Mobile tier without shadow maps. The lantern is
  unlit and `lamps.tres` says so. The layer earns its place as the only vertical element between
  kerb and façade.
- Source: `UtilityPoint.UTILITYPOINTTYPE` = `LPO`, a coded-value domain inside the geodatabase —
  the first street-furniture vocabulary the publisher defines. `refused_by_kind` publishes the rest
  of the domain. ⚠️ No dimension is published and geometry `Z` is 0.0, so every drawn dimension is
  authored (`Q60`).
- No column in the road takes two refusals: `_register` clears the host kerb, then the placed point
  is re-snapped against every edge and refused inside any drawn ribbon. Iterating the push instead
  was measured on signs: plateaus at 9.7% while the worst shift goes 5.52 → 16.77 m.
- `max_shift_m` 3.0 ships: 6.0 converts 204 over-shift refusals to pushes and stage two then refuses
  136 of them. 897 drawn of 1,263. `min_kerb_clearance_m` +0.0313 m is not a tautology — a foot
  reconstructed from `offset_m` drives it negative.
- ⚠️ `Q78`'s outward-only clamp applies here and deliberately not in `railings.py` (a fence is a
  run; a conditional push zigzags it).
- Refused: an `arms_against_kerb` counter — the arm direction is derived from the kerb side, so it
  reads 0 by construction (`Q72`). Shipped instead: `lantern_overhang_m` (p50 1.00 m = `arm_reach_m`
  less `outset_m`) and `lanterns_past_centreline` (must be 0; raising `arm_reach_m` moves it).
  Facing is graded by an A/B render at one fixed camera (`Q62`).
- Colour goes through `Q33`, unlike signs: `column_material: galvanised_steel` in `materials:`
  (28.0%, neutral `#6b6b6b`), graded by `_check_exposure`.
- ⚠️ `lamps._strut`'s ring is not reversed, unlike `signs._draw_pole`'s: it builds its own frame
  with `u x v == axis`. Copying the signs' fix inverted 25,116 of 35,880 triangles (`facing_away`
  caught it).
- `verify_lamps.gd`'s upright bar is 0.35, from an enumerated 20 of 40 triangles per lamp (ETL mesh
  exactly 50.000%). `check_stands_upright` lives in `mesh_contract.gd`.
- ⚠️ A layer must be added to `city_drive.tscn` as well as `city_preview.tscn`; no verify tool can
  see the omission (`Q73`).
- `meshes/force_disable_compression = true` in `project.godot` `[importer_defaults]`. Godot
  quantises positions over each mesh's own AABB — `lamps.glb` is 1,646 m wide, a 0.025 m step, 42%
  of the 0.06 m arm radius and wider than `signs.glb`'s 0.032 m pole. Cost +958,720 B (+2.002%) PCK,
  +14.57% render buffer, 0 draw calls. Project-wide because `generated/` is gitignored and a
  per-asset `.import` does not survive a clone; tiles and `roads.glb` never compressed anyway.
  ⚠️ `[importer_defaults]` seeds only a newly created `.import`: delete the sidecars and re-import
  before measuring this key. `check.sh`'s `settings` step pins the value but cannot see a stale
  sidecar. Three authored imports (taxi body, tyre, `central_plaza.glb`) deliberately stay `false`.
- The export is deterministic: three `tools/export.sh web` runs from a restored `project.godot`
  gave one sha256, and the instrument resolves 1 B. ⚠️ An unrestored `project.godot` is packed as
  `project.binary`, so a delta means something only against a baseline measured the same way.
- ⚠️ An ablation control is a baseline only for the variable it ablates: the feature is +888,852 B
  (+1.891%) — +17,184 engine side, +871,668 `lamps.glb` — not the asset pair alone.
- ⚠️ A lamp row's regularity is its content, so a refusal is a hole. Both spacing distributions
  ship and the difference is the finding: p50 16.74 → 20.15 m, gaps over 40 m 5 → 16. A widening
  moves this without touching a lamp.
- Limitation: `UtilityPoint` publishes no elevation, so a lamp on a flyover is drawn on the street
  below. `nearest_is_elevated` (177 of 1,263) sizes the problem; nothing can fix the placement.
- Cost: 40 triangles per lamp (35,880), one draw call, no collider, no texture.

See `Q60`, `Q78`, `Q72`, `Q33`, `Q62`, `Q38`, `Q26`, `Q73`.

---

## `Q83` — Touch scheme: two thumbs, both axes each

**Status.** Decided 2026-08-27 on the user's instruction. Owner `P2-4` → `ARCHITECTURE.md`
"The three schemes". Thresholds open, blocked on `P0-3b` hardware.

- Thumb 1 is one bipolar vertical axis: `accelerate` above the origin, `brake_reverse` below,
  centre coasts (`P0-5b/c/d`'s one pedal needs lift-off to park). Thumb 2 is `steer` horizontally
  and `drift` held past a vertical threshold. Both are relative: the landing point is the origin.
- `auto_accelerate` stays as an accessibility / one-handed option and is no longer the touch
  default. Before this, both thumbs steered and three of five actions had no home.
- `hud_layout.tres` is unchanged. A throttle sharing an axis adds no rest; a control that cannot
  share an axis still lands a third rest, and `verify_hud` failing is then the right outcome.
- Absolute sliders refused: 20 px between the readouts (y 860) and the rests (y 880) leaves no throw.
- Drift schemes refused: a tap (dead on the model — see `Q86`, `Q89`); reaching the steering zone's
  outer end (the counter-steer gesture would start the opposite drift); armed by where the gesture
  began (exit means lifting the steering thumb, and the state is latched history).
- ⚠️ The drift threshold needs hysteresis, must be a distance from the origin (a rooted thumb sweeps
  an arc) and is invisible, so drift state must show on the HUD — the speed chip's `AccentBar`.
- ⚠️ `InputRouter.drift` stays a `bool`; the ramp lives in the vehicle (`_drift_engagement`,
  `Q84`).
- Open: `look_back` is unplaced (thumb 1's horizontal axis is the candidate); the threshold and
  hysteresis values need a handset.

See `Q80`, `Q50`, `P0-5b/c/d`, `PLAN.md` `P2-4` and `P0-3b`.

---

## `Q84` — The drift "cliff" was the sweep grid; the grip dial is graded on dwell

**Status.** Closed. Method stands; every peak and dwell figure is superseded by `Q86`–`Q89`.
Corrects `Q50` regression 2.

- `drift_rear_grip_scale` has no cliff: swept at 0.002 the response is smooth, ~990°/unit between
  0.68 and 0.66. `Q50`'s 0.01–0.02 window was a 0.02 grid hidden behind a `%.2f` sweep label (now
  `%.4f`). ⚠️ A finding about a response's shape must justify its sampling resolution.
- Peak slip is the wrong target: drift pays per second above `drift_slip_threshold_deg` (14°).
  `skidpad_ablation.gd`'s `secs>thr` column grades this dial; read it with `peak slip` and
  `yaw_deg`, because dwell alone cannot tell a drift from a spin.
- Refused: retuning to 0.6695, which peaks at exactly 14.0° — 0.05 s of dwell against 0.57 s at the
  shipped 0.66.
- Structural: dwell rises as grip falls and exit speed collapses with it (55.4 → 36.4 kph over
  0.68 → 0.60). "Easy to hold" and "scrubs little speed" are opposite ends of one isotropic dial.
  0.66 stays; the tie-break is feel.
- ⚠️ The threshold is a design target, never a tuning knob (`Q58`). Refused for the same reason: a
  slip servo writing grip from slip makes "peak ≈ setpoint" true by construction (`Q72`). The
  ablation's slip calculation is the only copy and the grader must never call what it grades.
- `_drift_engagement` with `drift_attack_s` / `drift_release_s` (0.06 / 0.5) was built to make a
  tap persist and does not: `drift_release_s` 0.5 → 3.0 moves the tap 1.9° → 3.3°. The slide takes
  seconds to build. Kept for `Q83`'s hysteresis and `Q85`'s torque scaling.
- ⚠️ `@export_range` step is 0.001 on this dial, so an editor touch cannot snap an off-grid value.

See `Q50`, `Q58`, `Q83`, `GAME_DESIGN.md` "Drift".

---

## `Q85` — `VehicleWheel3D` simulates no wheel spin; the drift is assisted with a yaw torque

**Status.** Closed. Corrects `PLAN.md` `B4`, `Q49`, `Q50`, `Q84`. The constant-torque values are
superseded by `Q86`.

- `get_rpm()` is road speed re-expressed (Bullet raycast vehicle, no wheel inertia): the ratio to
  road rpm is −1.010 at rear grip 1.00 and −1.014 at 0.10, and −0.98 through a full brake. `B4`'s
  per-wheel angular velocity cannot be read. `get_skidinfo()` is real for traction loss and is not
  a lockup signal.
- ⚠️ `P3-2b` inherits it: once there are tyre marks or smoke, the wheel mesh rolls at road speed
  under them, and no check can see it.
- The button applies `drift_yaw_torque_nm`, signed by `steer_ratio` and scaled by
  `_drift_engagement`. 🔴 It is a torque and must never become a slip-angle setpoint, or `secs>thr`
  grades "the player held the button" (`Q72`).
- The assist cannot replace the grip cut: at grip 1.00, torque 2000–3000 gives 1.7–1.8° — tighter
  steering only. The two are multiplicative, and the speed scrub is intrinsic to one isotropic
  `wheel_friction_slip`.
- Mechanism findings no dial moves:
  - the slide self-terminates at ~1.8 s under held throttle, so `exit kph` includes ~2 s of a car
    no longer drifting, and slip is not monotonic;
  - lifting the throttle cancels the drift (21.8° → 7.3°) and re-applying does not recover it, so
    there is no lift-then-flick entry;
  - on a 90° corner the gripping turn is faster (63.4 kph exit against 52.8) — a drift buys line
    and time, never speed;
  - there is no sustained drift equilibrium at any counter-steer timing: a gripping circle or a
    spin. No roundabout-holding line in this model.
- Open: a tyre model layered on `VehicleWheel3D` is the only route to the physical mechanism; a
  `Q50`-scale call nobody has made.

See `Q50`, `Q49`, `Q84`, `Q72`, `PLAN.md` `B4`, `P0-5a`.

---

## `Q86` — The yaw torque decays on time so a tap gets the kick

**Status.** Closed. Extends `Q85`. The 63 km/h figures are superseded by `Q89`; values are desk
picks awaiting `P0-3b`.

- Built because drift is a feel mechanic, not only a score (user's correction; `GAME_DESIGN.md`
  "Target feel").
- The torque decays from a peak toward `drift_yaw_sustain` over `drift_yaw_decay_s`, timed from the
  press. A constant cannot serve both: a 0.5 s tap collects one-eighth of a 4 s hold's impulse
  (1000 N⋅m left the tap at 2.4°; 5000 spun the hold to 162.9°). At 0.8 s the ratio is ~1.2:1.
- 🔴 The decay runs on time, never on measured slip (`Q72`).
- Shipped 7000 N⋅m / 0.8 s / sustain 0.0. Refused: 9000 — fine on the skidpad, rotated the car
  086° → 219° into the railing on Expo Drive; an open pad has no far kerb. ⚠️ Sustain 0.0 leaves
  its own dial inert; kept for the handset to judge.
- 🔴 The three yaw dials cannot buy dwell: `secs>thr` stayed 0.78–0.85 across all three sweeps while
  peak ran 40° → 130°. Grade them on peak slip and exit speed, never on `secs>thr` — the opposite
  of `Q84`'s rule for the grip dial. State the grading rule per dial.
- `corner`, `brake` and `coast` rows were byte-identical across the change.
- `tools/skidpad_ablation.gd`: `--sweep=<field>=<v1,v2,…>` over any profile float (`--drift-grip`
  is an alias). One sweep per run, a second is refused. A non-`drift_` field re-runs all five
  manoeuvres. `drift_slip_threshold_deg` is refused outright (cached at boot, so it would print
  identical rows under distinct labels). Never sweep with a shell loop editing `handling.tres`.
- ⚠️ The held clock advances only while a wheel is down, so a drift held over a jump keeps its kick
  for the landing; the skidpad cannot see this.
- ⚠️ A `.tres` omitting `drift_yaw_decay_s` (or `drift_attack_s`) reads 0.0; the division gives
  `+INF`, the clamp saturates and the assist silently disappears. Stated, not clamped.

See `Q87`, `Q85`, `Q84`, `Q72`, `Q50`.

---

## `Q87` — The yaw assist fades out with speed

**Status.** Closed. Extends `Q86`; its open half (the grip cut) is closed by `Q88`.

- The assist had no fade-out, and every value had been picked at the skidpad's 63 km/h: the tap
  that gives 16.0° there spun the car at 84. `drift_fade_from_kph` 65 / `drift_yaw_fade_to_kph` 85
  (desk picks). At 105 km/h the tap went 163.3° → 17.5°; 63 km/h was untouched.
- `tools/skidpad.sh --run-up=<seconds>` varies entry speed (4 s → 63.02, 6 s → 86.36, 8 s → 105.47
  km/h). ⚠️ Rows compare only within one run-up; quote `entry kph`. Entry above 119 km/h walks into
  the drive taper and prints a note.
- ⚠️ The tap peaks at ~69 km/h, not at the design speed: entry speed makes slip on its own.
- The fade was necessary, not sufficient: with the assist off, the grip cut alone gave 95.2° at 86
  and 165.2° at 105 (`Q88`).
- ⚠️ The zero-span guard returns full assist (1.0), not none: an unauthored profile reads all
  zeroes and `speed >= fade_to` would switch the assist off everywhere. An equal non-zero pair is a
  deliberate hard cutoff. Above `drift_yaw_fade_to_kph` the assist is skipped, after the airborne
  refusal.
- Open: nobody has judged whether the 20 km/h linear band is felt as the button going dead.

See `Q86`, `Q84`, `Q50`, `Q85`.

---

## `Q88` — The grip cut tapers with speed

**Status.** Closed. Closes `Q87`'s open half; its open bottom is closed by `Q89`. 0.80 is a desk
pick awaiting `P0-3b`.

- `drift_rear_grip_scale_at_top` = 0.80, interpolated from `drift_rear_grip_scale` starting at
  `drift_fade_from_kph` and running to `max_speed_kph`. No spin at any speed: 86 km/h gives
  50.4° / 0.98 s, and the 84 km/h city tap holds 76.00 against a 76.60 no-drift baseline.
- ⚠️ Chosen cost: the drift is inert above ~100 km/h (2.4°).
- Refused: 0.78, which gives 75.8° / 1.07 s at 105 km/h but sits 0.01 from a cliff (0.79 → 2.8°).
  0.80 fails safe — inert rather than spinning. Sweep at 0.005 or finer near the knee; the window
  closes above, not below.
- 🔴 Method: a static sweep of a dial about to become speed-dependent is an upper bound on the fix,
  not an estimate. Constant 0.710 gave 44.9° at 105; the taper fitted to match gave 159.4°, because
  the car decelerates inside the drift and the cut deepens under it. Sweep the dial in its final
  form.
- The knee `drift_fade_from_kph` is shared by both mechanisms; the tops deliberately are not (yaw
  spent at 85, grip runs to `max_speed_kph`), because the grip value the car wants moves with speed.
- ⚠️ A zero `at_top` returns the base scale; read literally it would drive rear grip to zero at
  speed. `drift_front_grip_scale` has no speed term and was not measured to need one.

See `Q87`, `Q84`, `Q50`, `Q86`.

---

## `Q89` — The low end deepens the cut, and latches it

**Status.** Closed. Closes `Q88`'s open bottom. Holds the current design-speed figures; `Q84` and
`Q86`'s 63 km/h numbers describe a superseded car.

- `drift_rear_grip_scale_at_low` 0.44 and `drift_low_fade_kph` 41 deepen the cut as speed falls,
  latched at engagement (`_drift_low_locked`). The drift works 34–86 km/h, no spin anywhere, dwell
  0.42–0.98; flat 0.44 below the floor is safe (26 km/h: 35.1°; 18 km/h: 13.4°).

| entry km/h | held peak | `secs>thr` |
|---|---|---|
| 34.51 | 35.1° | 0.77 |
| 42.18 | 17.8° | 0.42 |
| 49.48 | 49.2° | 0.82 |
| 56.42 | 76.8° | 0.80 |
| 63.02 | 69.8° | 0.87 |
| 75.27 | 65.8° | 0.95 |
| 86.36 | 50.4° | 0.98 |
| 105.47 | 2.4° | 0.00 |

  Tap at 63 km/h: 20.5° / 0.40 s.
- The yaw assist cannot substitute at low speed: at 42 km/h, torque 0 → 20000 N⋅m gives
  4.2° → 3.6°. With grip unbroken, torque is a tighter line (`Q85`).
- 🔴 A tracking taper below the knee is unstable: slower → deeper cut → more scrub → slower. Built
  that way, 63 km/h became a 165.0° spin. Above the knee tracking is stabilising. The asymmetry is
  deliberate — the low branch latches, the high branch tracks. Latching both cost the high end
  (86 km/h: 50.4° → 20.6°).
- ⚠️ The window is narrow and the two dials interact: at 49 km/h `at_low` 0.50 gives 5.2°; at
  56 km/h `low_fade` 45 gives 104.7°.
- The latch releases at the knee and never re-arms on the way down. ⚠️ Reasoned, not measured: a
  skidpad drift always decelerates. A re-press inside the 0.5 s release ramp does not re-latch —
  inert, therefore safe.
- ⚠️ Guards live inside the branch that reads the value: the `at_top` guard had been left in a
  callerless wrapper (mutation: `at_top = 0` gives 103.2° at 86 km/h, not a blowup), and
  `_low_grip_scale`'s span guard sits before the floor return so an inverted pair behaves as no
  taper.
- Open: the tap is still dead below the design speed (3.9° at 42 km/h, 3.8° at 49); 0.44 and 41 are
  desk picks for `P0-3b`; a 2 s hold at 50 km/h nearly stops the car (52 → 3 km/h). `Q85`'s four
  mechanism findings are untouched.

See `Q88`, `Q87`, `Q85`, `Q84`.

## `Q90` — Every hole in the structure is a touchdown; the sampler descends instead of clamping

**Status.** ✅ Closed, one named residue (node 269) · **Owner.** `pipeline/roads.py::_descend`

`INFRASTRUCTURE` stops where a ramp reaches grade. `_deck_heights` interpolates across a hole, and
at an edge end `np.interp` clamps to the first covered station, so the ribbon hung level in the air to
the node. `_descend` now ramps from the node's at-grade height (`terrain + level_zero_m`, the
unlifted street) to the first covered station, bounded by `deck.touchdown_max_grade_pct` (10.0).

- Wan Chai: 9 clamped ends, 8 descended (2.0–6.8%, each landing at +0.00 m), 1 refused. 81 of 90
  off-grade ends were never clamped. Mixed nodes inside `P2-7`'s 0.5 m: 24 → 29 of 36.
- There are zero interior holes on level-1 edges in the region: every gap is a touchdown.
- The cap is a classifier, not a tuning value: the worst refusal is 5x the steepest keep, so 8–15
  gives the same answer. Still config.
- Refused: `e248` at node 269, MARSH ROAD, 35.8% over a 1.9 m hole. The deck ends in a 0.65 m face
  1.8 m past the node; the real touchdown is part-way along level-0 `e466` (`Q13`'s attribute
  flip). Open: no per-edge sampler can reach it (`e466` has structure under 0 of 2 stations); it
  needs a node-level pass after every edge is shaped. One node wants it.
- The other six residual steps at mixed nodes are `at_grade_m` (0.30) + `clearance_m` (0.20) by
  construction, not defects.
- `e365` at node 30 has a negative step (ribbon 0.43 m below the street) and descends correctly at
  2.0%. Its level-1 label on an at-grade run is still `Q13`'s flip; only the render is fixed.

⚠️ Traps:

- Grade is measured ribbon-to-ribbon, `clearance_m` included (`out[index]`), in both `_descend` and
  `tools/touchdown_error.py`. Reading it off the deck top understates it by about 0.2 m of rise.
- `touchdown_grade_pct` is recorded over refusals as well as keeps:
  `len(touchdown_grade_pct) == ends_descended + ends_over_grade` (`Q58`'s trap). `ends_no_target`
  (terrain NaN at the node) is counted deliberately outside it — an end with no terrain has no
  grade.
- `_ramp_ends` asks each end its own question off one `_levels_at_node` map: `_lifted_heights`
  whether another level is present, `_descend` whether level 0 is. "Mixed" alone is too weak — a
  `(1, 2)` node has no street to land on, and the grader cannot see a wrongly descended end.
- `_deck_heights` and `_lifted_heights` gate on different tests and both can fire at one node,
  re-opening a step. Measured disjoint here (16 lifted, 9 descended ends) — a fact about the data,
  not the construction.
- `tools/touchdown_error.py` is a one-sided bar: an end still clamped inside the cap fails; one
  clamped over the cap is the refusal working. `deck_error.py` cannot see this defect (a clamped
  end is uncovered, not wrong). `overhang.py` (`Q22`) reads a ramp resting on terrain as hanging
  (10.0 → 10.1%); not a regression.
- 14 of 90 ends read uncovered on the tiles against 9 clamped in the pipeline: `P2-1`'s 0.5 m
  decimation. The grader reports the gap and does not fail on it.
- `check.sh`'s `on_structure` assertions are level-0 only. No schema bump: a descended station's
  height comes from the street, so `on_structure` false is the field's existing meaning.

**See.** `Q20` · `Q13` · `Q22` · `Q21` · `Q62`

## `Q91` — Thin markings were lost to the pixel grid; MSAA 4x

**Status.** ✅ Closed · **Owner.** `game/project.godot`, `game/tools/verify_settings.gd`

`rendering/anti_aliasing/quality/msaa_3d` is 2 (4x), and its value is pinned by
`verify_settings.gd`. Dropped or zeroed, nothing errors and no counter moves; the only symptom is
thin geometry breaking into dashes at middle distance.

- Mechanism: sub-pixel rasterisation, not data and not z-fighting. On the chase rig the 0.1 m hatch
  is one pixel tall at 13.6 m and the 0.3 m border at 23.6 m. The same frame at two resolutions
  covers 0.0580 against 0.0574 of yellow: the amount of paint is right, its continuity is lost. So
  a brighter colour, a higher `lift_m` or a wider `hatch_width_m` (`Q54` forbids it) fix nothing.
- FXAA and TAA refused: a post-process cannot restore a stripe the rasteriser dropped; TAA ghosts
  under fast camera motion.
- 8x refused: WebGL2 `MAX_SAMPLES` is 4 in Chrome, so `msaa_3d=3` would clamp on web and ship a
  different frame per platform. Web runs `gl_compatibility`; 4x verified there in a real export.
  ⚠️ The canvas reporting `antialias: false` is not evidence — Godot resolves its own target.
- `Q61`'s analytic coverage (`railings.gdshader`) stays available per layer; complementary, not
  competing. Not taken here because every thin layer aliases, not only the hatch.
- Cost: draw calls and primitives identical at 0/2x/4x. ⚠️ The `ARCHITECTURE.md` budget tracks
  neither fill rate nor framebuffer bandwidth, so passing it means nothing here.
- Open: mobile is unmeasured (blocked on `P0-3b`); roughly +50 MB of framebuffer at 1080p by
  arithmetic. No `.mobile` override is set, deliberately. Desktop only shows 4x holds 120 Hz.
- ⚠️ `Q27`'s two audit viewpoints and their render-derived figures were measured without AA; the
  conclusions stand, the pixels do not.

**See.** `P3-18` · `Q61` · `Q71` · `Q82` · `Q75` · `Q54` · `Q62`

## `Q92` — Markings stand on the drawn road, not a model of it

**Status.** ✅ Closed. `pipeline/drawnsurface.py::DrawnSurface` answers a point query over the
published surface; `boxjunctions.py` and `roadmarks.py` read it; `tools/paint_clearance.py` grades.

`lift_m` is 0.012 m and the height under it was a centreline blend (`blended_height`, deleted with
both `height_blend_m` keys) that disagreed with the drawn cap fan by p99 0.158 m: 23.2% of box
triangles sat under the top road face. Raising `lift_m` to clear it was refused — 16 cm of floating
paint is worse than the gap.

What ships:

- `roadsurface.json` publishes `caps` (each junction hull ring, x/y/z) and `ribbons` (every drawn
  strip's two rails, post-trim and post-mitre, in the order `_Builder.strip` received them — the
  quad diagonal depends on it). `DrawnSurface` rebuilds the builder's own fan and strip triangles.
- `sample` = highest cap covering the point, highest strip covering it, the higher of the two;
  where nothing covers it, the height at the nearest drawn edge (rail, ribbon end line, cap ring),
  found by widening rings of a 16 m grid. No centreline, no radius, no knob. `of` refuses a
  manifest that draws nothing at the level.
- `split` cuts each convex paint polygon along the surface's creases (fan spokes, ring edges, rails,
  station lines, quad diagonals) before placing. A flat piece with corners on a convex `max`
  surface and no crease inside stands on or above it, so chord residue is zero by construction.
  Both `_place`s cut first. Counters `polygons_placed` / `polygons_split` / `pieces_placed`.
- `roadmarks._place` refuses a piece over nothing at level 0 whose every corner is under a drawn
  level above 0 (`levels_drawn`); published as `stations_on_drawn_structure` /
  `on_drawn_structure_m`, apart from the source's `on_structure`. The user chose refuse-and-count
  over hosting on the deck (`Q15`). Wan Chai: 5 stations / 7.736 m; Causeway Bay 0.
- Result, Wan Chai: deeper than 10 mm under the carriageway → 0 on boxes and road marks. Mesh
  price: box triangles x1.95, road marks x1.34; web PCK +568,812 B (+0.71%).

⚠️ Traps:

- A cut that would leave a piece thinner than `FlatBuilder.build`'s sliver bar is refused
  (`split(thin_m=)`); cutting regardless lost 1.96% of box paint area.
- The drawn road steps as well as folds (0.46 m at one Causeway Bay cap ring). A cut vertex on a
  step has two heights, so `sample(toward=)` and `covers(toward=)` ask a tenth of a millimetre
  into the piece. Without it paint is drawn down the riser (`check_faces_up` catches it; the ETL's
  plan-winding `inverted` reads 0), and without `covers(toward=)` nothing is ever refused.
- A void station with nothing drawn over it is kept — a stop line past a kerb is `Q54`'s protected
  population. "Over void → refuse" is wrong.
- No "placed minus drawn height" counter: it is `lift_m` by construction (`Q72`). The revert
  tripwires are `vertices_over_cap` (reads 0 if `caps` stops being published) and
  `vertices_over_void` / `void_reach_m` (reads every off-cap vertex if `ribbons` stops).
  `over_cap_rise_m` is the cap over the strip it overlaps.
- This does not re-open the nearest-arm cliff (172 near-vertical triangles): the cap ring passes
  through each ribbon's end corners, so the two cases meet continuously. Pinned by
  `test_the_cap_meets_the_ribbon_without_a_step`, and the fan/strip reproduction tests use a tilted
  ring and a swapped rail order because a flat one passes under any interpolation.
- The void-wedge flank closing built here (`_paint_flanks`, `_add_paint_stations`) was deleted by
  `P3-35e` (`Q133`).

Left, ungated: paint covered by a second surface drawn over it (`Q53`'s overlap) is reported in its
own column by `paint_clearance.py`; box paint on a kerb top is registration, which `Q54` refuses to
fix by scaling a surveyed extent. Evidence is a frame (`Q62`): box 8 at
`--camera=636,22,200 --look=651,1,176`; delete the paint meshes' import sidecars before each side.

**See.** `Q91` · `Q53` · `Q69` · `Q58` · `Q72` · `Q62` · `Q54`

## `Q93` — The turn-arrow glyph: head and stem measured off TD's sheet, branch authored

**Status.** ✅ Closed. `pipeline/arrows.py`'s glyph, `config.Arrows`' proportions.

Defect: the branch reused the ahead head's length, so with reach 0.28 < head 0.325 the shoulder
went negative and the turn head straddled the stem — on 416 of 747 arrows, since `P3-15`.

- `CT174/51-5(1)F` publishes only `LENGTH = 4000` / `6000` for `RM1017`–`RM1030` and is stamped NOT
  TO SCALE, but it is to proportion: `RM1016`'s published 2.800 ratio measures 2.802. So the
  pictogram is evidence. Measured (fraction of glyph length): head length 0.390, head width 0.122,
  stem tapering 0.076 → 0.032.
- The branch is authored, deliberately declining the published shape (reach 0.150, head 0.100,
  barb span 0.233): as a plain triangle it is a mushroom; a faithful six-point dart reads as a
  detached diamond, and TD's 0.09 m barbs are sub-pixel (`Q91`). Ships as an arrowhead longer than
  wide, 0.54 x 0.46 m with its tip 0.76 m out on a 4 m arrow.
- ⚠️ The ahead head and stem stay measured; this is no licence to re-author them. `Q67`'s
  rasterise-and-diff does not transfer — the page has no scale, only shape at normalised length.
- Guards: `config.py` refuses `branch_reach_frac <= branch_head_length_frac` and a stem widening
  toward the head. `test_arrows.py::test_no_head_overlaps_the_stem_it_grows_from` clips every head
  against the stem on every published movement at both lengths (arm excluded); mutation-checked,
  0.620 m² on the pre-fix config.
- Cost: same triangle count and bytes; every counter unchanged.

**See.** `Q59` · `Q67` · `Q54` · `Q60` · `P3-16`

## `Q94` — Two arrows in one lane: the lane count was invented, and the arrows are a source for it

**Status.** 🟢 Closed, residue carried by later records: the `floored` source was replaced by
`Q114`, the two-way split is `Q126`, and rows over an authored width (STEWART ROAD `e505`) are
`Q130`'s `arrows_unmeasured`.

`arrows.py` snaps a published offset into one of `ribbon.lanes` slots. With `lanes` authored from
the speed-limit table (2 on nearly every edge), arrows TD painted in different lanes landed in one
slot. `arrows.json` publishes `stacked_pairs` / `stacked_disagreeing`; the latter ran 51 → 35 → 24
as the count was sourced.

Decisions:

- Nothing is de-duplicated or moved: dropping a published instruction on the authority of an
  invented width is `Q54` inverted. The counter says how much contradiction remains.
- `lanes` is bracketed off the measured `width_m` against TPDM 4.3.9.8's 3.0–3.65 m through lane,
  never divided by `lane_width_m` (the constant under test). The permissive bracket contains TD's
  own count on 9 of 9 rows of Table 3.4.2.1; requiring an exact partition into legal lanes fails
  two of them, so it was refused.
- A row of turn arrows abreast is a lane count stated by the publisher. `arrows.py` publishes
  `implied_lanes` per edge, clustered on the published offset, never the placed one (grouping on
  the placed offset returns `ribbon.lanes` to itself). The cluster bar 2.00 m sits mid-plateau
  (flat 1.50–2.50) and collapses at TPDM's 3.0 m lane.
- The row resolves ambiguous brackets only — a tie-breaker between two readings of a measured
  width, never a standalone publisher — so a measured `lanes_source` implies a measured
  `width_source` by construction (`verify_road_graph.gd` asserts it; `Q130` is the one exception).
- A row of one arrow is not a row (`_ROW_MIN` = 2): the row counts painted lanes, a lower bound.
  The first build floored those rows instead and published 28 edges whose `lanes_source` said
  `arrows` for a count the arrows had not chosen.
- Row against published count has three states: fewer (an unpainted lane, expected), more (a
  finding, never corrected; `e403` reads 7.70 m with four abreast), equal (the free cross-check).
  Filed against the published count, not the bracket.
- Odd counts on two-way edges (`e10` TUNG LO WAN ROAD, `e529` MARSH ROAD; TPDM 3.4.2.7) are
  reported, never corrected (`Q54`).
- A lane count moves no geometry: the ribbon is `max(width_m, floor)`. Only the `TEXCOORD_0` lane
  coordinate, the marking codec and arrow slots change, so every clearance grader must come back
  unchanged — checked as a gate.
- HyD Pavement Polygon is the third width publisher (`paged_sources`, `geometry: area`). The
  publisher loop runs per station, so third means it never overrides a station the line publishers
  answered, not "only where they are silent"; put second it destroyed `e119`'s 16.25 m.
  `width_publisher` is a `+`-joined set of who was used, not who could have answered. Engine
  invariant: `width_source == "authored"` iff `width_publisher` is empty.
- STEWART ROAD `e504`/`e505` measure 16.77 / 16.69 m from iB1000 and 16.72 / 16.66 m from HyD, and
  are refused by `width_bounds.max_m` 16.5 (13.5 m four-lane + 3.0 m parking strip). TD's painted
  edge covers 0 stations there. The ceiling must not move: the 44 refused spans are a continuum to
  26.71 m with no break, and 16.8 m admits 13 of them. 3.4.4.1's curve widening does not apply
  (radius near 420 m). Even lifted, 16.7 m brackets to an ambiguous 4–5.

⚠️ Traps:

- HyD tiles the carriageway into 552 polygons in region; an internal seam is not a kerb.
  `_union_boundary` drops every segment two polygons share (agrees with point-in-union walking to
  0.037 m). HyD carves traffic islands out and iB1000 does not: p10 −3.39 m (`DATA_SOURCES.md`).
- `tools/carriageway_margin.py` has its own area reader, written from the rule, not imported.
- The arrow-row clustering is duplicated in `carriageway.py` and `arrows.py` — forced by the import
  order (`arrows` → `roads` → `carriageway`). `lanes_row_disagreement` is their diff, graded only
  where the roads stage published a row; the two are not expected to agree everywhere because
  `arrows.py` counts symbols that survived registration against a ribbon the roads stage lacks.
- `pipeline/polyline.py` is a leaf holding `Segments`, `Snap`, the heading residuals and
  `plan_steps_2d`: shared primitives, imported rather than restated.
- The fetch is whole-territory (64,644 features, 22 requests, 163.2 MB), not a bbox, because
  `sources` are per-city and an envelope is per-region (hard rule 3); `geometryPrecision=2` is
  lossless here. Plain GeoJSON has no spatial index: about 2.43 s per region per build.
- `download_paged` needs `crs_seen` separate from `crs` — one sentinel doing two jobs spliced a
  `crs` member into the open `features` array.
- `verify_road_graph` asserts the derivation travelled (force every `lanes_source` to `authored`
  and it fails); its older lane checks re-derive from the `lanes` they read.
  `_check_structure_width` asserts not-narrower with a `tapered` counter beside it.
- `drive.sh` does not re-import changed assets: run `godot --headless --import` between A/B sides.
  Never `git add -A` after an editor session.

**See.** `Q19` · `Q57` · `Q54` · `Q72` · `Q93` · `Q95` · `Q114` · `Q126` · `Q130`

## `Q95` — The authored carriageway width was outside TPDM's range; `width_m` is now measured

**Status.** ✅ Closed — width assigned and the widening made a floor on the user's call,
2026-08-29. Coverage and floors moved on since: `Q128`, `Q129`.

The authored `width_m` = `lanes x lane_width_m` = 6.4 m on 720 of 737 Wan Chai edges is below
TPDM Vol 2 Ch 3's 7.3 m two-lane single carriageway minimum (Table 3.4.2.1; table in
`DATA_SOURCES.md`). The standard corroborates a measurement and bounds the instrument; it must not
assign a width — it says what a road should be, not what it is, the table is headed Minimum, and
3.4.2.2 lets widths fall below it. Widths under 7.3 m are reported, never refused.

What ships:

- `pipeline/carriageway.py` measures `width_m` per level-0 edge by two-sided ray from one
  publisher per station; per-edge median over non-junction stations, then the refusal.
  `width_source` says authored or measured. `roadgraph.json` schema 5 for this field (15 now).
- `drawn = max(width_m, floor)` replaced `widen_default: 1.6`: a multiplier over-widens streets
  that are already wide. Floors were 10.24 m / 12.48 m (70 kph) / 0.0 on decks; with the floor
  alone live 0 of 797 half-widths moved
  (`test_the_floor_is_inert_on_the_width_the_multiplier_was_tuned_against`).
  `surface.floor_default_m` is 0.0 since `P3-33c` (`Q129`).
- Bounds live in `carriageway_survey.width_bounds`: `max_m` 16.5 is a plausibility ceiling for a
  single carriageway, not a confound filter. The crossing test is `beyond_m = span − own`
  (`own` = 2 x the median near ray): under `hard_min_m` 3.0 → uncrossed, the span is this edge's
  width; at or over `dual_min_m` 6.75 → crossed, stays a span; between → unresolved, nothing read.
  Both ends are transcribed clauses. The middle state is load-bearing: TONNOCHY ROAD `e142`
  (`beyond` 4.96) and `e130` (10.30) publish nothing, where any single threshold would have
  published 16.7 m as a carriageway.
- Every published width rests on `hard_min_m`; `dual_min_m` is descriptive (licensed count flat at
  276 across 3.0–14.6). The uncrossed width is ray-cap-insensitive (p50 7.15–7.18 m over 10–25 m)
  where the raw span is not. `pair_bearing_tolerance_deg` 30: decomposed count flat at 14 from
  10° to 75°.
- The pipeline is a second, independent implementation of `tools/carriageway_margin.py`, on the
  user's instruction — the generated `carriageway_width.json` cannot be committed (hard rule 7)
  or read by a clean build. They agree p50 0.005 m / p90 0.098 over 259 edges. The tool also
  licenses `decomposed` halves (mutual-pair split); the pipeline deliberately does not.
  `decomposed` is tested before the span ceiling and answers to `dual_max_m`.

⚠️ Traps:

- Lanes come out as a bracket against 3.0–3.65 m; dividing by `lane_width_m` is `Q72`'s tautology.
- "621 of 737 edges are one-way" is measured; "run as opposed pairs" was not — `surface.py` finds
  six shared-endpoint pairs and geometry finds 110 mutual. On most one-way edges the ray stops at
  the edge's own far kerb, so a one-way span is a width only where `beyond_m` says so.
- A pair residual is contaminated by the partner's reading (12 of 14 misses); `beyond_m` is not.
  Reported, not retuned.
- Counters are derived from one unfiltered population (`survey` takes no bounds), so `n` and the
  keeps cannot drift apart (`Q58`). The tool refuses to start unless `2 x max_ray_m` exceeds the
  ceiling, or the cap manufactures a clean sweep.
- A floor is not a multiplier: `_road_surface` refuses a floor below 0.0 (not below 1.0);
  `verify_road_graph` asserts not-narrower with a `widened` counter; `narrowing.py` must not apply
  the swept default over the per-speed and per-level floors (`check_baseline` caught it on 42
  edges, then 6 on 3-decimal rounding).
- A widening moves every layer registered on the kerb (signs, lamps, railings, kerbside, arrows)
  and owes their graders. The one real cost: `ground_clearance` 87 → 89 edges, `e116` LEIGHTON
  ROAD and `e643` GLOUCESTER ROAD, both widened here; `Q24`'s, not a bar to retune.
- `Q94`'s early scratch width table does not reproduce; use `tools/carriageway_margin.py`.

Left: the decomposed widths the tool licenses and the pipeline does not.

**See.** `Q94` · `Q19` · `Q57` · `Q54` · `Q24` · `Q128` · `Q129` · `GAME_DESIGN.md`

---

## `Q96` — The arrows' lane snap divides by the measured carriageway

**Status.** Closed.

- `pipeline/arrows.py` reads a published arrow offset as a fraction across the **surveyed**
  carriageway (`width_m`), then `_offset_of` places that fraction on the drawn ribbon. The old
  denominator `lanes x lane_width_m` was the identity `Q95` severed; it differed on 292 of 737
  level-0 edges (worst `e351`, 16.11 m measured against 6.4 m assumed).
- Reach is small by construction: at `lanes == 2` the snap is `sign(offset_m)` and the denominator
  cancels. 7 of 747 arrows changed lane. Pinned by
  `test_a_two_lane_edge_is_insensitive_to_the_carriageway_width`.
- `stacked_disagreeing` rose 24 → 25, all on `e114` HENNESSY ROAD (14.43 m, `lanes = 3` from a row
  spanning only 6.07 m). Reported, not retuned: a rising `stacked_disagreeing` is a finding (`Q94`).
  Open lead: nothing grades a row's lateral span against the width it resolved.
- New counter `outside_carriageway` (38): the offset falls outside the measured carriageway, so the
  fraction clamped. `outside_drawn_ribbon` (9) is a strict subset because
  `drawn = max(width_m, floor)`; if that ever inverts, it is a finding. No
  `ARROWS_MANIFEST_SCHEMA` bump.
- ⚠️ `lanes` moves no ribbon geometry but does move where an arrow is drawn.
- ⚠️ NaN guard: `x <= 0.0` is False for NaN and `min(1.0, nan)` is 1.0. Use `not x > 0.0`; pinned
  by a test. An absent width is refused in `ribbons()` into `no_lane`, never counted in
  `outside_carriageway`.
- ⚠️ `_lane_of` and `_offset_of` are stated inverses; keep the U side convention in that one pair
  (`Q59`).
- ⚠️ Test fixtures must not default the carriageway to `2 x half_width_m` (10.24): that is the one
  value where the surveyed and drawn frames coincide.
- Rule kept: prove a refactor byte-identical before the behavioural change. The mutation fails
  only `test_the_denominator_is_the_measured_carriageway_and_not_lanes_x_lane_width`.

**See.** `Q95` · `Q94` · `Q92` · `Q72` · `Q62` · `Q59`

---

## `P3-9a′` — Round 0: the city is recognised, and it was not drivable far

**Status.** Closed. Three HK drivers over the web link.

- Recognised as Wan Chai from geometry alone (no HUD, plates or fares in `B2`) — the acceptance
  criterion, and the strongest evidence for `Q8`'s bet.
- Drivers repeatedly stuck "on bridge rails" and stopped early. `railings.glb` has no collider;
  what stops a car is `INFRASTRUCTURE` geometry, i.e. `Q19`. At the time 7 of 16
  structure-touching level-0 edges were blocked against 19 of 721 others (16.6x), four of them WAN
  CHAI INTERCHANGE. Fencing every blocked edge costs 1 ordered pair of 187,946
  (`tools/reachability.py`; `RoadGraph` has no router). Resolution: carve the licensed seven, fence
  and dress the rest (`Q19`).
- "Some buildings read as unfinished" was volunteered, not asked. `Q26`'s gate needs rejection of
  the city **and** attribution to flat surface; only half was met, so it stays shut. A
  pre-registered condition is not loosened after seeing the data.
- ⚠️ The round cannot be tied to a build: the `P3-9a` rule (a new name per cut, never an overwrite)
  was skipped. Follow it next round.

Open:
- A round that asks the building question directly, if `Q26` is to move.
- `P3-9` proper — different drivers, on a handset, arrow disabled.

**See.** `Q19` · `Q51` · `Q26` · `P3-7a` · `Q8` · `Q76`

---

## `Q97` — Touch drives on three of five actions

**Status.** Closed on the user's instruction ("basic touch control support, dont support drifting
yet"). `P2-4` stays open: its review needs `P0-3b`'s handset.

- `InputRouter` reads touch. Left zone steers; right zone is one bipolar axis (`accelerate` above
  the touch origin, `brake_reverse` below). Both thumbs relative (`Q83`). `drift` and `look_back`
  have no touch home; thumb 2's vertical axis is read and discarded.
- Touch overrides the action map per axis, only while that axis's finger is down; it never
  replaces it. `driver.gd`'s `--hold=` drives through `Input.action_press`, so an unconditional
  touch read would zero every scripted drive and still print `DRIVER OK`. `verify_input.gd` asserts
  both sides.
- ⚠️ Touch cannot go through the action map: all four axis actions carry `"deadzone": 0.2` and
  `get_action_strength` returns 0 beneath it. Values merge in the router as floats; `touch.tres`'s
  `jitter_deadzone_px` is a distance applied before normalising.
- Handedness lives in `HudLayout.steer_zone()` / `drive_zone()`, not the input code; `P3-5b`'s
  one-handed layout replaces those two functions. Rects are named `touch_zone_*`.
- `place`, `offsets`, `axis`, `inset_for_safe_area` live on `HudLayout` — one placer for HUD, touch
  overlay and check. Zones sit on their own `CanvasLayer` because `--hud=off` frees the HUD.
- ⚠️ `verify_input.gd` asserts containment in design space and edges in resolved space: the
  headless viewport is 1920x1920, where rests and zones genuinely separate.
- ⚠️ An autoload identifier does not exist under `--script`; use
  `get_node_or_null("/root/DebugHud")`. A `SceneTree` tool that aborts before `quit()` never exits
  and wedges `check.sh`; `verify_input.gd` carries a 30 s watchdog. A hung Godot instance rewrites
  `project.godot` on shutdown — `ps aux | grep godot` after any hang.
- `verify_input.gd` is in `ALWAYS_TOOLS`; `drive.sh` takes `--touch=mouse|off`, validated in
  `driver.gd`. `--touch=mouse` is one finger and can never be the review.

Open:
- `touch.tres` numbers are first guesses (`steer_travel_px` 140, `drive_travel_px` 110,
  `jitter_deadzone_px` 6), unmeasured against a thumb.
- Drift gesture (threshold and hysteresis blocked on `P0-3b`; `Q84`'s ramp is built) and
  `look_back` placement (candidate: thumb 1's horizontal axis, which `verify_input.gd` asserts
  moves nothing today).
- No visible touch chrome, on the user's call; drift state at the speed-chip `AccentBar` arrives
  with the drift.

**See.** `Q83` · `Q80` · `Q84` · `PLAN.md` `P2-4`, `P0-3b` · `ARCHITECTURE.md` "The three schemes"

## `Q98` — The chase camera's yaw is exponential, and its tuning is data

**Status.** Closed.

- Origin: the user found the rigid camera dizzying in turns. The old
  `rotate_toward(_yaw, desired_yaw, yaw_lag * delta)` at 7.0 rad/s was 3.12x the taxi's peak
  steering yaw rate (2.245 rad/s at 97 kph), so it never lagged.
- Gate run first: dizziness was unchanged at matched 60 fps (`--max-fps 60`), so the cause was the
  yaw and not the 60 Hz write under a 120 Hz render.
- Exponential law, `yaw_response = 6.0`. Lowering the constant rate was refused: `desired_yaw`
  also carries the look-back π flip and one rate governs both. Steady-state lag is
  `ω·delta / (1 - exp(-k·delta))`: 11.9° at 30 kph, 22.4° at 105 (the `ω/k` limit reads 5.1% low).
- ⚠️ Yaw follows facing, never velocity — at `Q86` slip angles velocity points at the kerb.
- `ChaseProfile` (`camera.tres`) follows `HandlingProfile`: schema only, no defaults, including
  `fov_full_kph`. `follow_response` 13.388613 is the old 12.0 behaviour in the exact form.
- ⚠️ A `.tres` missing a key reads 0.0 and renders; asserts cover the dials that may not be zero
  (`follow_response` among them). While the working tree is under test, restore from a backup
  file, never `git checkout`.
- Refused: a shared `1 - exp(-k·dt)` helper with `hud.gd` — no util module, and the two
  parameterise reciprocally (time constant against rate; recorded in `chase_profile.gd`).
  `verify_camera.gd` scoped out on the user's call, so `camera.tres` has no verify coverage.

**See.** `P2-5` · `Q96` · `Q84`–`Q89` · `Q62` · `Q72`

## `Q99` — An editor save stripped `project.godot` and a `.tres`

**Status.** Closed. The comment-presence guard is superseded by `Q119` (rationale lives in a
sidecar `.md`; the four file classes are committed in Godot's writer form).

- The editor re-persists a base value and drops a feature override it did not create:
  `msaa_3d` survived, `renderer/rendering_method.web` and three warning promotions died.
  `check.sh`'s `settings` step pins them.
- A `.tres` cannot lose behaviour this way — the writer omits only values equal to the class
  default (0 differing stored properties measured on `clean_daylight.tres`). What is at risk is
  the argument, never the numbers. `glow_levels/*` do not follow the ordinary storage rule.
- `check.sh`'s `tuning` step keeps the inverted default: anything in `game/tuning/*.tres` or
  `game/scenes/**/*.tscn` fails unless documented or named in `UNDOCUMENTED_OK`, so a new resource
  cannot slip in unexplained. A list of files that must comply would pass that case.
- Cause of the strip never reproduced (`Q97` records one route: a hung headless run).

**See.** `Q119` · `Q75` · `Q98` · `Q91` · `Q82` · `Q72`

## `Q100` — Hong Kong is the only city; its config is the single source of truth

**Status.** Closed, on the user's instruction.

- Retired, not refuted: the city-agnostic rule was never exercised (one city file ever). Nine
  datasets from four publishers, each with its own vocabulary, mean a second city would be a
  second pipeline, not a YAML file.
- Now: `etl/config/hong_kong.yaml` (`SUPPORTED_SCHEMA` 4, no `id:`/`name:`/`crs:`),
  `load_config()`, `Config`, no `--city` flag, paths `etl/sources/<source>` and
  `etl/out/<region>`.
- `etl/pipeline/hongkong.py` holds the constants that are the city: the CRS pair
  (`EPSG:2326` / `EPSG:4326`), drive-on-the-left, `TS115` NO ENTRY and the `TS131`–`TS133` turn
  prohibitions. A code that drives a branch is declared there, never copied into config (`Q72`).
  ⚠️ `Q67`'s 0.187 bar thickness stays in `signs.py`: it is a drawing coefficient, not a branch.
- Survives: multi-region (`Q6`, `Q10`, `city_offset`; a city's `bounds` must not change once a
  `city.json` has shipped); hard rule 4 — tuning and publisher vocabulary stay in the yaml;
  `city_id` and `source_crs` still written to every manifest, so `CITY_SCHEMA` does not move;
  `export.py`'s same-city/region cross-check; `test_crs.py`'s 304 m datum canary.
- Deliberately not merged: `pipeline/carriageway.py` and `tools/carriageway_margin.py`; the two
  lane-row clusterings; `railings` not clamping outward where `signs` and `lamps` do (`Q78`; the
  hoisted `_register` takes it as an explicit parameter); the two opposite station normals;
  `lamps._strut`'s unreversed ring; the five station walkers; the two `measured` percentile sets;
  the nine `_write_manifest` bodies (shared signature only); `railings.Ribbon` and `arrows.Ribbon`
  (shared name only).
- `signals.py` was kept latent here and later deleted (`Q133`); a test asserts the config declares
  no `signals:` block.
- Records citing a second city each stand on their other reason: `Q15`, `Q33`, `Q34`, `P1-1`,
  `P3-16`, `P3-22`, `Q67`, `Q68`, `Q72`, `Q77`, `Q79`, `Q81`, `Q90`, the iB1000 bbox refusal,
  `Q95`.

**See.** `Q101` · `Q96` · `Q77` · `Q6` · `Q10` · `Q72` · `P0-4`

## `Q101` — Data-availability refusals re-read against the grown estate

**Status.** Closed. Rows as recorded at closing; check `PLAN.md` for what has since been taken.

| Refused as unsourced | Now published by | Standing |
|---|---|---|
| Pedestrian crossings / footway | `DTAD_CROSSING_LINE`, `RM1135`/`RM1136`, iB1000 `CartoPedLine PA`, HyD `FEAT_TYPE=2`, `DTAD_DROP_KERB_LINE` | Re-opened (`P3-27` candidate) |
| Speed-limit signs `TS174`/`TS175` | On disk since `P3-16` (37 + 28 points) | `Q65`'s hold — scope, not data |
| `LINETYPE` (`Q60`) / `REFNAME` (`Q76`) domains | — | Measured shut, below |
| Road text (`DTAD_RD_MARK_ANNO`, 274) | Data always existed | No-go on scope (`Q65`); the typeface/licence half is gone (`Q79`) |
| Kerb registration of railings / signs / lamps | `Q95`'s measured `width_m` postdates all three | Re-opened as a measurement: re-derive `shift_m` per class before touching code |
| `EXC_VEH_TYPE`, `PART_TIME_REST` | Same geodatabase as the graph | Deferred to `P3-3`/`P3-8`; schema change both sides |
| Fare density (29 taxi points) | Bus stops (70), GMB termini (52), iB1000 `BUILDINGNAME`/`ADDRESS` | Unassigned; lands with `P3-1a` |
| Road elevation second opinion (`Q13`, `Q21`) | iB1000 `FY`/`FYU`/`TUR`, HyD `LVL` | Unread |
| `tram_streets` authored list | `CartoTransLine TW`, already read by `tramway.py` | Derive from the layer and retire the list (`Q57`) |

- Domain probe, measured shut: a scan of every `.gdbtable` for `GDB_CodedDomains` content finds 85
  pairs on iB1000 sheet `11-SW-10C` (the control) and none in any of `dTAD_IRNP.gdb.zip`'s 58
  tables. `Q60`'s whitelist and `Q76`'s spelling gate stay rules this project wrote.
- Outbound publication of derived data: not pursued, on the user's call. An outbound-data policy
  must be written before any derived dataset leaves the repo (`LICENSING.md`).

**See.** `Q57` · `Q100` · `Q65` · `Q95` · `Q77`

---

## `Q102` — The vision façade reader is withdrawn on cost, and `TEXCOORD_1` goes with it

**Status.** Closed, the user's call. Withdrawn, not refuted: `Q41`'s reader passed validation and
`Q40`'s limit on a per-pixel statistic stands.

**Supersedes.** `Q41` · `Q46` · `Q42`'s unbuilt riders · `P3-7a`'s `W4`–`R4` continuation.
**Amends.** `Q40` (the tint has no consumer) · `Q26` (`A‴`) · `Q47` (`R4` loses its survey side).

- Deleted: `tools/facade_grammar.py` and labels, `tools/podium_error.py`, the grammar/tint codec,
  the `facade_survey:` block, the shader's `survey_*` and `quiet_*` uniforms and branches, the
  `survey` extra. No `anthropic` dependency remains.
- `TEXCOORD_1` is removed, not shipped all-zero: `0` was a legal code ("refused"), so an
  all-sentinel tile is indistinguishable from a survey that declined everything. `schema_version`
  19 → 20. Ratchets: `test_tiles_ship_no_survey_channel_at_all`, and `verify_tiles.gd`'s
  `_check_survey_payload` asserts absence (also catches `meshes/light_baking = 2` synthesising a
  UV2). `ARCHITECTURE.md` records the attribute as forbidden.
- ⚠️ The `quiet_*` tier had to go with the reader: it conditioned on the grammar refusing, which
  without a reader is every building.
- Survives: the hash path (`fract(UV.y)`), `Q44`, `Q45`, and `Q43`'s `glazed`/`fenestrated` split
  (re-merging re-opens a defect on 39.3% of wall vertices). The colour survey
  (`facade_survey.py` → `COLOR_0`; `Q30`, `Q34`, `Q37`, `Q55`) is untouched.
- Kept with no consumer: `tools/facade_unwrap.py`, `tools/facade_glazing.py`. Re-consuming the
  tint needs a new glazed verdict, and the dip cannot be it (`Q40`: best Youden 0.100).
- ⚠️ A stale `facade_survey:` block is refused by `config.py`, testing presence, not truthiness (a
  bare key parses as `None`). `_building_style` still has no general unknown-key check.
- ⚠️ Removing dead shader branches still moved 1.6% of pixels by ≤ 2 of 255 (compiler
  precision, geometry byte-identical).
- Re-proposing costs three decisions: the survey's cost, the dependency, and re-adding the channel
  with a schema bump.

**See.** `Q40` · `Q41` · `Q46` · `Q26` · `Q47` · `Q77`

## `Q103` — The off-grade network is drivable, and the ribbon is drawn on its deck

**Status.** Half answered. Tunnel widths and deck-sourced flyover ribbons shipped
(`schema_version` 9). Level 1 has since been measured and opened (`Q108`, `Q110`); level −1 stays
closed. Open: `e489`'s headroom, and the `e208` / `e306` pinches. **Owner.** `P4-1`. Figures below
predate `Q106`–`Q109`, which moved the ribbon; membership held, numbers did not.

**Trigger.** The user met a parapet 1.08 m from `e208`'s centreline on the FLEMING ROAD ramp.
`Q13`'s "geometrically unreachable" premise expired when the touchdowns were ramped: 39 of 60
off-grade edges reach street height, and every instrument gated on level 0. ⚠️ `Q15`'s shape — a
decision falsified by another stage gaining capability; nothing fails when it expires.

### The finding is that `Q13`'s premise expired and nothing noticed

A graph refusal (`nearest_edge`) does not close geometry: `surface.py` still draws the ribbon and
`roads.glb` its collider. 23.3% of the region's carriageway area was reachable and ungraded.

### What was measured, none of it shipping

- `tools/deck_margin.py` decomposes `overhang.py`'s `Q22` figure into deck span, signed centreline
  offset and hanging metres. Not independent of `overhang.py` (same faces and tiles).
- ⚠️ The estate is not watertight (`Q19`): 921 of 1,948 stations read two or more runs, gaps
  bimodal (p50 0.40 m, tail p90 3.37 m), so `--bridge-m` defaults where the clusters part.
- ⚠️ Quote `--max-lateral-m` with a span, never with an overhang: hanging is cap-stable
  (10.4–11.8%), span p90 is not.
- `clearance.LEVELS` is `(0, 1)` since `Q108`; `centreline_error.py --levels` still defaults to
  `(0,)` and `narrowing.py` is pinned at `AT_GRADE`.

### Level −1 is fixed

`floor_by_elevation_level` has a `-1` key, so 15 tunnel edges draw at their authored width rather
than `floor_default_m`. Only `roadsurface.json` geometry moved; no kerb-registered layer did,
because tunnels carry none. ⚠️ The drawn width is not a clearance reading (see `e489`). Level 2 is
declared, unused, and deliberately has no rule.

### Level 1: extending the publisher survey off-grade is REFUTED

- Publishers license 5 of 45 level-1 edges, and their lines are a 2D plan projection: a ray from a
  deck finds the kerb of the street underneath. 2 of the 5 would publish wider than the deck
  (`e104`: 11.04 m against a 7.50 m deck). `Q15`'s defect as a width.
- A sourced centreline correction does not exist off-grade: `centreline_error.py --levels 1` reads
  max 1.15 m against offsets up to 4.90 m. No publisher draws a viaduct deck edge.
- So the model is the only source for a deck. `test_no_off_grade_edge_is_licensed_by_a_publisher`
  pins the gate.

### The network is closed at its touchdowns — a closure, not a fix

- `fence.touchdown_levels` closes off-grade levels at the nodes they share with level 0
  (reachable ⟺ graded). Today `[-1, 2]`: every mapped level `clearance.LEVELS` does not measure,
  pinned by `test_the_open_levels_are_the_measured_levels`.
- ⚠️ `touchdown_edges` is published apart from `fenced_edges`, which
  `RoadGraph.fenced_edge_ids` re-derives from the car bar. These edges are closed because nothing
  grades them, not because they are narrow. Disjointness is mutation-checked in
  `verify_fence.gd`.
- Inert with the key absent. `reachability.py` finds none of them in its level-0 graph, so the
  closure costs the open network 0 pairs.

### The geometry — the ribbon is drawn on its deck, `schema_version` 9

- `carriageway_survey.levels: [0, 1]`; a test pins it to `clearance.LEVELS`. The deck walk rides
  on the `INFRASTRUCTURE` `HeightField` `roads.py` already reads — no new stage. It reaches 36
  off-grade edges where publishers reach 5. Level −1 is out of the walk: a bore has no deck.
- Publishes a width and a signed offset (`width_source` / `offset_source` `deck`). Schema 8 → 9
  because a consumer reconstructing `polyline ± width_m / 2` is now wrong off-grade. The
  centreline itself does not move (`Q54`).
- `overhang.py` level +1: 10.3% → 5.6% hanging (5,449 → 3,326 m²). ⚠️ Per-edge `over p50` got
  worse on 22 of 35 edges; one width per edge cannot fit a varying deck. Area is the metric.
- `DECK_WIDTH_PERCENTILE` is p10 by judgement on a trade curve with no plateau (p0 5.3 / p10 5.6 /
  p25 6.2 / p50 7.0%). p0 rejected: one unbridged hole shrinks the whole ribbon.
- ⚠️ The 0.40 m attribution and 1.0 m bridge are shared with `deck_margin.py`, not chosen twice.
  Compare slab to slab and refuse junction stations, as that tool does.
- ⚠️ The offset is signed and the two station normals are opposite; `_reassign` negates once, by
  name, and a test pins it.
- ⚠️ The arrow-row reader stays level 0: handed the walked set, an arrow hosted to the flyover
  above its road (`e263` lanes 3 → 2). `deck` is a third `width_source` state in
  `verify_road_graph.gd`.

### What is left

- Residual `|pipeline − deck_margin|` p50 0.60 m, max 3.80 m (level-0 survey: 0.005 m).
- 155 of 1,556 walk directions reach `DECK_MAX_LATERAL_M` (12.0), counted as
  `deck_stations_saturated`; a rising count means the cap no longer clears what it is sized for.
- `clearance.py --levels` is report-only and `_write` refuses anything but the shipped `LEVELS`.
  The walk is additive: widening it does not move level-0 answers.
- ⚠️ `roads._structure_bounded` is not an instrument for bores: `HeightField.from_meshes` drops
  near-vertical triangles (1 of 75 level −1 stations, modelled or not). `clearance.py` rasterises
  triangles and sees walls.
- `P4-1` owns opening what remains.

### `e489`'s cause — the road's vertical alignment

- `e489` CENTRAL-WAN CHAI BYPASS TUNNEL reads 0.00 m in the middle four stations and 6.40 m at both
  ends. Not intrusion (0 of 345 blocking corners inside the ±3.20 m ribbon) and not the lining: 8
  slabs spanning the bore do all the blocking.
- The road rides a flat `terrain − 8.00 m` (`elevation_levels[-1]`) while the tunnel box keeps
  fixed levels; the terrain humps 3.3 m, leaving 0.22 m of headroom at the worst station.
- ⚠️ A headroom defect published as a width: `clearance.py` measures a horizontal corridor in a
  0.30–2.00 m band, and no instrument publishes a height.
- Open, `P4-1`: a `roads.py` height-rule change (sample the bore or descend the ramp); owes
  `touchdown_error.py` and the height battery. Widening makes it worse.

### `carriageway_occupancy.py` has the `levels` knob

- `--levels` widens the corridor half only; the area half always walked every level. Inert at the
  default. Off-grade rows are reported, never gated (`Q57`).
- ⚠️ A set omitting level 0 is refused (`test_a_set_without_level_zero_is_refused`): an empty
  gated population printed "Within the accepted bounds."
- Negative levels are refused: they would enter `drawn_share`'s denominator and loosen both gated
  bars. So this tool cannot corroborate `e489`.
- ⚠️ `--corridor-report` is a level-0 report and must be byte-identical between `--levels 0` and
  `--levels 0,1` (`test_the_gated_population_is_invariant_under_widening`). The level is recorded
  where the population is decided and indexed, never `.get(..., 0)` — that defaults a missing edge
  into the gated half. The parse is written out, not imported from `pipeline.clearance`.

### The off-grade corridor is diagnosed per station

- `off_grade_report` is a separate function from `corridor_report`; merging them makes the
  level-0 labels false (`Q57`). `split_by_level` is named and tested (`TestSplitByLevel`).
- Four level-1 edges were under the lane bar at the 1.0 m bin, each a short pinch on a ribbon
  otherwise at full width: `e208` FLEMING ROAD, `e306`, `e257`, `e450` CANAL ROAD FLYOVER. On the
  shipped bundle (`Q109`): 1.35 / 1.86 / 2.81 / 2.98 m. Exact figures: `Q110`.
- ⚠️ The `authored` column is a tautology off-grade (no floor at level +1); the section prints
  the count instead. Nothing is gated and there is deliberately no bar.

### The mechanism — the occupier moves

- `--probe-edges` walks named edges through `occupier_report` (a third report, own function).
- Headroom refuted on all four: `base` is negative at every occupied station. ⚠️ `base` is an
  upper bound, so a negative reading is proof; `top` is a lower bound and never evidence of clear
  air. The occupier is 100% `INFRASTRUCTURE`.
- ⚠️ `_covers_centreline` asks the occupied stretches (`Standing.bands`), never their hull, and
  counters read judged stations only (`_CORRIDOR_MEASURED`).
- "A migrating occupier, so registration is spent" was an artefact of the plan bin (below).

### Two of the four edges were the plan bin

- `--index-cell-m` 1.0 → 0.5: `e257` and `e450` clear, and the grader agrees with
  `clearance.walk` on membership (`e208`, `e306`) — `Q51`'s `e132` shape.
- ⚠️ A finer plan bin flatters: it prices the instrument, never clears an edge. The default stays
  1.0 m — at 0.25 m level-0 `BUILDING` share reads 1.324% → 0.286% against a 1.72% bar, passing a
  gate on edges nobody re-examined.
- ⚠️ A plan-bin sweep needs the `--sample-m` control to tell smear from index holes (it was
  smear). Cost is flat: `cell_m` changes a dict key, not the sample count.

### The across cell is swept — the two edges survive

- ⚠️ `--across-m` must be ≤ `--index-cell-m`: the across cell is a point probe into the index
  grid, and a coarser probe steps over its own index (occupier found at 130 of 206 stations on
  `e208` against 187 matched). Open: refuse it at startup, as `carriageway_margin.py` guards
  `2 x max_ray_m` (`Q58`); the shipped 0.5 / 1.0 satisfies it.
- Matched at 0.125 / 0.25: `e208` 2.74 m, `e306` 3.09 m against the 3.20 m lane bar.
- ⚠️ `--across-m` runs the unflattering way and is near-inert on the gated half; `--index-cell-m`
  flatters. It changes the lattice size (28.6 → 97.0 s). Shipped `ACROSS_M` stays 0.5.
- Shape: `e208` is one 11 m pinch near one end; `e306` is three 1 m spots. They do not share a
  fix (`Q57`). The blockage does not close as an instrument finding.

### The ribbon is registered against the deck per station

- `tools/deck_margin.py --probe-edges` prints one row per walked station. ⚠️ Join the two tools on
  `along_m`, never on station index: real pitch is `L / ceil(L / spacing)` and the tools walk at
  2.0 m and 1.0 m (`occupancy_indices` re-walks). A refused station prints its reason in place —
  refusals outnumber keeps (`e208` keeps 27 of 106).
- `e208`'s occupier is the deck's own left rim: the two move together (−0.93 m against −1.10 m).
  Nothing crosses the ribbon; ribbon and deck separate. `e306` is the clean control (`off_ctr`
  within ±0.50 m).
- Refused: a per-vertex deck offset. At the interchange the contiguous structure at ribbon height
  is 7.9 m to ≥24 m wide, so its middle is not this carriageway's middle (`Q19` candidate 1's
  shape). What would settle it is attributing deck extent to this edge's own carriageway — `P4-1`.
- `edges_argument`, `edges_label` and `pipeline.polyline.plan_lengths` are imported, not restated
  (a primitive; the duplicate-deliberately rule does not reach it). Tests:
  `etl/tests/test_deck_margin.py`.

**See.** `Q13` · `Q19` · `Q22` · `Q51` · `Q57` · `Q58` · `Q106`–`Q110`

## `Q104` — The cut face had no back, and the ribbon is drawn wider than the corridor

**Status.** 🟡 Partly open — back face, stub clusters (`P3-31`), through corridors and box flanks
(`P3-32` paint arm) ship; the carve-wall arm, the edge-on railing and posts under caps are open ·
**Owner.** `P3-28` / `Q19`

Found from the seat with every counter green (`Q62`: the evidence is a frame).

**Carve back face (shipped).** `_retaining_wall` emitted one single-sided quad per station under
`cull_back` tiles, so the cut face was invisible from behind (the estate is not watertight, `Q19`).
`carve._double_side` emits one reversed, coincident triangle per drawn triangle — never offset, so
nothing z-fights. `cull_disabled` is unavailable: the wall rides in the tile with every building.
Cost +2,232 tile triangles (+0.291%); every per-edge `carve.json` row byte-identical.
- ⚠️ `_facing_away` is taken before the mirror; after it the counter reads half the wall by
  construction (`Q72`). `test_the_mirror_is_why_the_counter_is_taken_first` pins it.
- ⚠️ The back face inherits the removed structure's channels, or the window-band shader glazes it.
- ⚠️ A/B frames: a camera outside the rail is occluded and reads identical; shoot from behind the
  face, and compare only after both runs have exited (a PNG caught mid-write fooled `cmp`).

**Ribbon wider than the carve corridor (open — `P3-32`'s other arm).** On structure ribbon and prism
both use the authored width; at grade the ribbon takes the 10.24 m floor and the prism does not, so
the wall stands 1.52–4.32 m inside the drawn carriageway on all eight carved edges (`e256` worst,
`e99` 1.92 m), 0.7–1.0 m proud — "a wild kerb". Fix shape: neck the ribbon to the corridor as a deck
is treated (`structure_taper_m`); never widen the prism (`Q54`). It is a `surface.py` widening, owes
the whole widening battery, and is the user's call.

**Railing edge-on (open).** `railings.glb` `barriers` are one quad thick; `cull_disabled` fixes
from-behind, not edge-on. `railings.gdshader`'s header claim that thickness "buys nothing a driver
can see" was falsified from the seat. Roughly doubles a 460,940-byte mesh and interacts with
`ALPHA`-as-coverage, so it needs its own budget argument.

**Yellow boxes are a fourth extent publisher.** A box is painted on carriageway by definition, and
only occurs at junctions, where `Q95`'s ray survey refuses stations. 20 boxes in Wan Chai: thin as a
width source, useful as a grader. `paint_clearance.py` reports the same set and deliberately does
not gate it (`Q54`); ⚠️ its `on kerb` column is a height population — never pool it with plan
coverage (`Q57`). Off-road paint was two defects wanting opposite fixes: the void between two
ribbons that never meet, and paint past a kerb. ⚠️ The void/past-kerb split is a function of
`--ray-m` (void 5.1% → 77.8% by count over 1 → 8 m) and differs by count vs by area — quote radius
and basis, per box, and grade the two arms separately. Not a junction-mouth flare (off-road paint
sits further from nodes than on-road) and not the authored-width fallback (`e591` is measured).

### `P3-30` — the instrument

`tools/box_extent.py` — grades, never gates, exit 0, ~4 s. 20 rows; originally 38.75 m² of 577.83
(6.71%) off-road, on only five boxes.
- Box identity is point-in-polygon against `DTAD_YL_BOX_POLY` via `gdb`; clustering the shipped mesh
  returns 18 flat from 1.5 to 15 m (`Q58`'s trap). `unattributed` is 0 and is never pooled.
- Two free values on purpose: `--ray-m` (4.0) classifies, `--reach-m` (10.0) measures; a reach under
  the radius is refused. Distance is the minimum over eight centroid rays marched in `--step-m` — an
  upper bound twice over.
- Naming uses `polyline.Segments.nearest`, level 0 only; nearest-vertex naming was wrong on 6 of 20.
- `PLAN.md`'s "a widening moves past-kerb and not void" criterion was withdrawn as unreachable — a
  widening closes voids too. Disjointness is structural instead: a partition identity at runtime and
  `test_the_three_classes_are_exhaustive_and_disjoint` over all 256 ray patterns.

**`P3-31` — stub clusters (done).** Road Network v2 joins two dual carriageways with several nodes
and short links; per-node caps left a void between them. `_Edge.is_stub` is the two existing trim
clamps read together — no new knob (`Q72`): 87 of 792 edges. `_stub_clusters` unions the
`(node, level)` groups a stub joins (54 clusters over 139 nodes) and `_cap_ring` hulls the non-stub
mouths once. Outside a cluster the cap is byte-identical; `carriageway[]`, `offset_m`, `trim_m`
byte-identical on all edges; no schema bump (manifest gains a `clusters` block).
- Refused on numbers: one hull per stub — covers neither reported point, LOCKHART stays at 6.05 m².
- ⚠️ A stub across the seam joins nothing (`P5-7f`): `_stub_clusters` takes an `owned` predicate,
  because the neighbour's build caps the far node per node.
  `test_a_stub_across_the_seam_joins_nothing`.
- `tools/cap_pavement.py` prices cap growth against HyD's Pavement Polygon at 0.25 m; past-kerb
  share flat at 17.5%. `--near-m` is its one free value; grades only. Clipping the hull to the HyD polygon
  is the shape to try if a cluster is ever refused.
- Fixture `stubville`; `clusters` is reachable at zero via `junction_trim_max_fraction` 0.49.

**Through corridors (done).** Both carriageways attach to one node at each crossing, so centrelines
splay into it (88 of 228 cluster arms turn ≥15° within 12 m) and a hull of splayed mouths drew a
bow-tie with pavement in the through lane. `_through_corridors`: two arms at different nodes whose
far axes face within `_THROUGH_TURN_DEG` (45) and overlap laterally are one street; the quad between
their far sections is a cap of its own. 68 corridors over 28 clusters (Wan Chai), 13 over 8
(Causeway Bay). Price: 745 m² new asphalt, 325 past a HyD kerb. Fixture `splayville`.
- Refused: a kerb-line corner rule — it paired arms 23 m apart at Lockhart / Marsh.
- ⚠️ Unioned, never hulled into the cluster cap — the hull sweeps the pavement corner.
- Open: layers registered against the kerb never read the caps, so posts stand in the road — lamps
  20, sign plates 86, railing panels 12 inside a level-0 cap. Fix: those stages refuse a foot under
  a cap, read from `roadsurface.json`.

**`P3-32` paint arm — flank caps (done).** The ribbon yields to the box as a flank cap, never as a
width: widening would move the lane coordinate, arrow slots and every post, and merge two ribbons
under a box across a dual carriageway. `surface.py` reads boxes via `boxsource.read_boxes`,
`_add_paint_stations` adds a station every `_PAINT_STATION_M` (2 m) and at each box-edge crossing,
`_paint_flanks` draws rail → paint edge as a convex quad in the cap class, closing each run at the
rail's own crossing of the ring. Wan Chai: 186 flanks, 22 m² new asphalt; pooled off-road box paint
38.75 → 0.58 m² (0.10%), none past a kerb.
- ⚠️ A flank thinner than the kerb is not drawn; a flank stops one kerb width into the next ribbon
  it meets, at that ribbon's height (`test_a_flank_stops_at_the_next_ribbon_at_its_height`).
- ⚠️ The bbox prefilter is the rail's box grown by the reach; `_shoelace` is twice the area; ribbon
  bounding boxes are taken once (`_Rings`).
- Residual deep `paint_clearance` triangles were `DrawnSurface` reading a model instead of the rails
  (`Q92`, closed) — never answered with `lift_m`.
- The FLEMING ROAD ramp tail drawn at deck width is `Q113`'s, not a junction item.

**See.** `Q19` · `Q23` · `Q54` · `Q57` · `Q58` · `Q62` · `Q72` · `Q92` · `Q94` · `Q95` · `Q103` ·
`Q113`

## `Q105` — The asymmetric ribbon is priced, and it buys paint rather than width

**Status.** Closed — report-only pricing; built by `Q107`, figures re-measured by `Q106`.

One symmetric deck-derived width and offset per off-grade edge hangs paint on one side and stops
short on the other (`e208`: the flyover's parapet inside the drawn lane). `tools/deck_margin.py`
gained a clamp table pricing `left = min(half, deck_left)`, `right = min(half, deck_right)`.

- Licensed: cutting paint back to structure. Not licensed: publishing the result as `width_m` — the
  rims come from one contiguous run of structure, which at an interchange is not this carriageway's
  (`Q57`, `Q103`). Lifting that is `P4-1`'s: attribute deck extent to this edge's carriageway.
- ⚠️ "Stations on deck after the clamp" is 100% by algebra; no such counter is printed (`Q58`).
- ⚠️ A negative half (centreline outside its own deck) is undrawable, not narrow. `Clamp.undrawable`
  reads the two halves, never their sum; `clamp_report` refuses to print unless the count equals
  `centre_off_deck`; `priced_widths` excludes them (`TestPricedWidths`). `e104` carries a run of
  them, so any build owes a fallback.
- Cost on the drawn ribbon (`Q106`): 2 of 1,327 stations under the 3.20 m lane bar, 1 under the
  1.80 m car bar, all on `e208`. Two bars, counted apart (`Q19`), read from config. The paint given
  up is `overhang_m` exactly. The clamp removes a defect; it does not open a road.
- The clamp is bounded by the ribbon, so `--max-lateral-m` does not move it; quote the cap with a
  span. `--bridge-m` moves pooled figures only at 0 (an unbridged walk is a hole detector); `e208`'s
  rim is identical across 0–4.0.
- The clamp is arithmetic on columns `survey` already records, not a second walk. A missing
  `clearance:` block degrades (`car_bar_m` is `float | None`); one `kept` predicate, not two.
- ⚠️ A restore within the same filesystem second reloads the mutated `.pyc`; clear `__pycache__`
  between mutation runs.

**See.** `Q103` · `Q57` · `Q58` · `Q72` · `Q78` · `Q19` · `P4-1`

## `Q106` — Four instruments measured a ribbon that is not drawn

**Status.** Closed — tools read the drawn offset; per-station form superseded by `Q107`.

`surface._shape` draws the rails at `±half + shift`, where `shift` is the graph's `offset_m` (set on
36 of 45 off-grade edges by `Q103`, up to 4.95 m on `e337`). Every tool reconstructing the ribbon
through `overhang.cross_section` walked `[-half, +half]` about a centreline the paint had left.

- The two off-grade graders failed in opposite directions: `overhang.py` drops samples with no road
  under them and read low; `deck_margin.py` keeps them and read high. A divergence between them is a
  bug, not a model difference.
- `carriageway_occupancy.py --levels 0,1` was wrong too: all four blocked off-grade edges (`e208`,
  `e306`, `e257`, `e450`) are under the 3.20 m bar at its 1.0 m bin (`Q109` corrects the sizes).
- Level 0 cannot move: `offset_m` is exactly 0.0 on every level-0 edge and the parameter defaults to
  0.0.
- ⚠️ `ground_clearance.py` and `carriageway_occupancy.py` already had an `offset_m` — a cell's own
  distance from the centreline, which `Section.is_inside` splits `Q19`'s populations on. The drawn
  offset is a separate name, added to it; threading it into the old name re-splits every row.
- ⚠️ `offset_m` is indexed, never `.get` with a default — a bundle without it is stale and must say
  so. Mutation-checked: ignoring the shift fails 3 tests, flipping its sign fails 2.

**See.** `Q103` · `Q105` · `Q22` · `Q19` · `Q78` · `Q72`

## `Q107` — The off-grade ribbon is cut to its own deck, per station and per side

**Status.** Closed — shipped; three residuals open. `Q113` later fixed `e208` being clamped to a
deck it was not standing on.

`carriageway._walk_the_deck` keeps both reaches per station, `_rims_at_vertices` interpolates them
onto the published vertices, `roads.py` publishes `deck_rim_m` (roadgraph schema 10), and
`surface._clamped_rails` cuts each rail to its own rim:

    upper = min(shift + half, left_rim)      lower = max(shift - half, -right_rim)

346 stations cut across 36 edges (`e337` worst, 2.16 m off each half); `overhang.py` hanging 4.3% →
3.3%.

- It cuts and never extends (`Q54`); `width_m` and `offset_m` in `roadgraph.json` do not move —
  paint, not width (`Q105`).
- Level 0 is untouched by arithmetic: no deck is `inf`, not `0.0`. 0 of 737 level-0 edges changed.
- Fallback: a station whose rails would cross keeps its unclamped ribbon and is counted. Reads 0,
  reachable (`test_crossing_rails_keep_the_unclamped_ribbon_and_are_counted`). ⚠️ The bar is
  `_MIN_SEGMENT_M`, not zero — touching rails leave a collapsed quad, a gap in the collider.
- The ribbon is asymmetric, so `half_width_m` is half the distance between the rails:
  `roadsurface.json` gains `carriageway[].offset_m` (schema 7), `city.json` carries it (schema 22);
  tools read `overhang.drawn_offsets` / `offset_at`. `cross_section` returns the signed cell offset
  so no caller rebuilds it.
- ⚠️ `generated_road_graph.gd` deliberately does not read `deck_rim_m` — the result ships in
  `city.json`; a second implementation in the engine is `Q106`'s split.
- ⚠️ `_rims_at_vertices` applies no negation: the right/left frame difference is paid once, by
  `roads._reassign`, on the signed `offset_m`; the rims are unsigned reaches named by side.
- The rims ride as columns of `_Edge.points`, so `trim`, `dedupe`, `_add_kerb_stations` carry them.
- ⚠️ `deck_margin.deck_run` selects the deck nearest the ribbon's centre (`nearest_to_m`), not the
  centreline — at an interchange they can be different structures.
- ⚠️ A paint clamp is a corridor change (`Q109`): it cost `e208` 0.41 m (`Q110`). A build that
  clamps owes the corridor readings before and after.
- ⚠️ A/B frames need a forced re-import (Godot serves the cached mesh), and a camera on an edge
  where the change is large — `e337`, not `e208`.

Open, each needing rim data at a station the deck walk refuses:
- Junction caps: `end_half_width_m` reads the unclamped `_WIDTH`, so the cap hull can re-draw paint
  the clamp removed. `overhang.py` walks edges, not caps; nothing reports it.
- Edge ends: `_stations` skips within `JUNCTION_M` of a node and `np.interp` flat-extrapolates the
  nearest rim, so ends are over-cut where a deck normally flares.
- The kerb and lip are drawn `kerb_width_m` outside the clamped rails, so 0.5 m still overhangs. No
  instrument sees it — both graders read the clamped half-width.

**See.** `Q105` · `Q106` · `Q103` · `Q54` · `Q57` · `Q62` · `Q19` · `Q113`

## `Q108` — The off-grade network publishes a clearance

**Status.** Closed — `clearance.LEVELS = (0, 1)`; level −1 refused.

All 60 off-grade edges used to publish `clear_width_m: -1.0`. `P4-1`'s precondition.

- `clearance.walk` had `Q106`'s defect: it now reads `roadsurface.json`'s `offset_m`, negated —
  `walk`'s `across` is the right of travel (as `carriageway._stations`), `offset_m` is in
  `surface.mitres`' left frame. Unnegated it mirrors every off-grade section and publishes a
  plausible table (`Q78`). `test_the_walk_normal_is_the_negation_of_mitres` reads the production
  `_across`. Level 0 is byte-identical because the offset is 0.0 there.
- Result: 782 edges measured (was 737); under the 3.20 m lane bar 19 → 21 (`e208` 2.00 m, `e306`
  2.50 m); under the 1.80 m car bar 14, none off-grade. No schema bump — `clear_width_m` means what
  it meant (hard rule 5).
- Level −1 refused: a bore has no deck to walk, and `e489`'s defect is 0.22 m of headroom — a
  horizontal corridor cannot express a vertical fact. `carriageway_survey.levels` matches and
  `test_the_shipped_levels_match_the_width_surveys` pins the two keys together.
- Publishing a second level broke tools that assumed one population: `clearance_reconcile.py` takes
  one `--levels` for both halves (a ratchet over two populations is not a ratchet);
  `narrowing.py::check_baseline` is pinned at `AT_GRADE` on purpose (it sweeps `floor_default_m`,
  which off-grade edges do not read). `edge_levels(graph)` is the shared, indexed level map — an
  unknown edge never defaults into the gated population.
- Ratchet at the time: `EXPECT_PIPELINE` 21, `EXPECT_GRADER` 25, `EXPECT_DISAGREEMENT` 6, at-grade
  halves unchanged at 19 / 21 / 4. ⚠️ A ratchet move that cannot name its unchanged at-grade half is
  a bar retuned to fit.
- Cost: +8.2% occupier triangles, +5% wall time, +2% peak RSS. ⚠️ A region whose level-1 decks
  stand above every level-0 sample would widen the prune's height band and this would not hold.
- The fence's level handling moved on in `Q111`.

**See.** `Q13` · `Q103` · `Q106` · `Q107` · `Q51` · `Q19` · `Q72` · `Q78`

## `Q109` — The four blocked bridges, re-read on the ribbon that is drawn

**Status.** Closed — report-only; its open fence question is answered by `Q110`.

- `Q103`'s 2–2 split survives `Q106` and `Q107`: on `e208` and `e306` the occupier migrates across
  the ribbon (centreline occupied at some stations); on `e257` and `e450` it stands on the rims (0
  stations). `P4-1`'s two-fix strategy is confirmed: a width rule can reach the rim pair; neither a
  width nor a constant offset reaches the migrating pair.
- The migrating pair read narrower after `Q107` because the corridor is measured inside the paint:
  a paint clamp is a corridor change and owes this reading.
- `Q106`'s corridor table mixed three instruments in one column; the offset fix moved only `e208`
  and `e306`. ⚠️ Quote every corridor figure with its instrument and bin (`Q57`) — `e257`'s closest
  approach is 0.34 m at the 1.0 m bin and 1.19 m at 0.5/0.5.
- ⚠️ `clearance_reconcile.py` is a lane-bar ratchet and is blind to a disagreement at the car bar
  (`e208`: grader 1.35 m against pipeline 2.00 m, both under 3.20 m, booked `agree`).
- `Q103`'s "7.9 m deck against a 5.60 m ribbon" on `e208` is localised to the interchange half of
  the edge (from `st` 71); `e306` is the clean control.
- ⚠️ A digest over a report that prints its own `built` timestamp expires at the next build; pin
  the numbers. Level-0 inertness is held on the 21 starved edges and their worst readings.
- ⚠️ A dirty `game/project.godot` after an engine launch can be lost keys, not noise
  (`renderer/rendering_method.web`, three `gdscript/warnings/*`): check `git diff`, restore, and let
  `check.sh`'s settings step confirm (`Q75`, `Q99`, `Q119`).

**See.** `Q103` · `Q106` · `Q107` · `Q108` · `Q110` · `Q51` · `Q57` · `Q58`

---

## `Q110` — The corridor measured exactly, and the disagreement `Q109` left open

**Status.** Closed — report-only; no barrier owed on any off-grade edge. `Q113` later moved the
`e208` readings (exact 2.57 m, grader 2.00 m).

`tools/corridor_truth.py` (+ `etl/tests/test_corridor_truth.py`): clips every triangle of the
shipped tiles against the station slab and the bumper band in closed form — no plan cell, no colour
classification; 0.25 m station pitch.

- It can clear an edge and never condemn one: the reading is a lower bound on the true corridor, so
  above a bar is proof and below one is evidence of nothing. ⚠️ Level-0 rows are a control on the
  machinery (`e0` reads 10.24 of 10.24), not a reconciliation — terrain blocks there.
- Both shipped instruments publish lower bounds at their own bin, ordered by bin: grader 1.0 m <
  grader 0.5 m ≈ pipeline 0.5 m < exact. At the time: `e208` 1.35 / 1.90 / 2.00 / 2.37 m, `e306`
  1.86 / 2.50 / 2.50 / 3.06, `e257` exact 4.21, `e450` exact 5.04. The grader at the pipeline's
  resolution (`--across-m 0.25 --index-cell-m 0.5 --spacing-m 0.5`) closes the gap to 0.10 m.
- Verdict: all four clear the 1.80 m car bar, so `fence.py` owes no barrier and `Q108` stands. At
  the 3.20 m lane bar the starved set is two, `e208` and `e306`. Never pool the two bars (`Q57`).
- Open paint lead for `P4-1`: the blockage is one parapet face about 2 cm wide standing 0.6–0.8 m
  inboard of `deck_rim_m`. The rim is the structure's outer edge and includes the parapet, so the
  ribbon is painted over a wall. A rim stopping at the drivable face would cost no corridor.
- Not settled here: whether deck beyond the paint belongs to this edge's carriageway — this tool
  asks what stands in the band, never what stands under it; `deck_margin.py` answers that half.
- `--window-m` is flat 0 → 2.0 on all four; what a zero window loses is an obstruction between two
  stations (the aliasing `clearance.py` pins `ALONG_M == CELL_M` against), not a thin wall.
- ⚠️ Independent in method, not in frame, on purpose: the ribbon comes from `city.json`
  `carriageway[]` via `overhang.py`'s helpers, interpolated between vertices (nearest-vertex is
  0.5 m out at `e208`'s pinch). `BUMPER_LOW_M` / `BUMPER_HIGH_M` are restated, on
  `carriageway_occupancy.py`'s precedent. The clip runs on plain tuples (8.0 s → 3.1 s); exactness
  is the closed form, not numpy — do not "restore" arrays. `deck_rims` defaults an absent deck to
  `inf`. Ten mutations, ten failures.

**See.** `Q109` · `Q51` · `Q108` · `Q107` · `Q106` · `Q57` · `Q58` · `Q37` · `Q113`

---

## `Q111` — The elevated network opens, exactly where it is measured

**Status.** Closed — shipped; human review passed 2026-09-06. A scope change against `Q13`, not a
bug fix: its premise expired, not its reasoning.

- Invariant: every mapped level that `clearance.LEVELS` does not measure is closed, every level it
  measures is open. `fence.touchdown_levels` is `[-1, 2]`;
  `test_the_open_levels_are_the_measured_levels` refuses `[-1, 1]`, `[-1]` and `[]`. ⚠️ Level 2 is
  listed and inert so the rule is total over `elevation_levels` — a level-2 edge in a later region
  is closed until measured.
- `RoadGraph.is_drivable` is `_levels[slot] == 0 or _measured[slot] == 1`. ⚠️ The level-0 arm is
  load-bearing: an edge wholly inside junction trims publishes no corridor and must stay in the
  network. Off-grade has no fallback — that is the refusal.
- `fenced_edges` takes the closed levels and fences every open level. 0 of 45 open off-grade edges
  reach the car bar, so only `test_an_off_grade_edge_on_an_OPEN_level_IS_fenced` and its
  closed-level twin tell the rules apart.
- `P2-2`'s criterion is reversed: a closed level never leaks into a query, and an open deck is
  served at its own height. `verify_road_graph` asserts both and refuses to pass vacuously; its
  counters are split by level and never pooled (`Q57`).
- `nearest_edge` height rule is a preference, never a rank: `Hit.distance` stays plan distance;
  prefer a road within `LEVEL_REACH_M` (2.5 m, `road_graph.gd`) of the query's height, else the
  nearest at any height. Without it 318 of 825 level-1 vertices within 5 m in plan of a level-0 edge
  put a flyover under a car on the street. The value is not load-bearing: different-road vertical
  separation is p10 7.07 m, and 1 of 263 stays ambiguous from 1.0 to 5.0 m. ⚠️ The ring early-out
  tests the on-level best only; breaking on the fallback can return a deck overhead.
- Moved: barrier units 253 → 113 (touchdown ends 39 → 5, the tunnel portals); indexed segments
  2,959 → 3,739 (= +780 level-1 exactly); off-grade impassable 2 (`e208`, `e306`), off-grade fenced
  0; at-grade 19 impassable / 14 fenced unchanged.

Not done:
- Tunnels stay shut; opening them needs a vertical instrument, not a wider `levels` (`Q103`,
  `Q108`).
- `P4-2` owns the reverse case — a point that belongs on a deck but is asked from 2D (`Q15`).
- `P4-3`, `P4-4`, `P4-5` untouched: no traffic on the elevated network (`P3-3`), the MARSH ROAD
  `e248` ramp step is a 35.8% lip now reachable, and the streamer's bands were tuned without 23.3%
  more drivable area resident.

**See.** `Q13` · `Q103` · `Q108` · `Q110` · `Q57` · `Q72` · `Q62`

---

## `Q112` — The fence is one quad thick and disappears edge-on

**Status.** Closed — the barrier family is a slab with a per-class `thickness_m`.

A zero-thickness sheet seen along its length covers under a pixel and the coverage shader
dissolves it (`Q58`'s failure-to-nothing).

- `railings` block: `thickness_m` per class (0.05 / 0.14 / 0.10 for `railings` / `bollards` /
  `barriers`). A run is a road-side face, a far face and a cap; the cap fixes the grazing angle.
- ⚠️ Extruded outward only, so the road-side face stays where `_station` registered it (`Q78`).
  The three windings come from one convention (near `flip`, far `not flip`, cap `flip`), never
  chosen per quad. Every published metre held per class.
- `_distinct` merges stations under `min_station_gap_m` (0.01): a duplicated ribbon vertex gives
  two stations on one point with two facings. 27 of 5,532 steps, the same 27 from 1 mm to 2 cm.
- `_folded` / `_unfold` (`fold_tolerance_deg` 45): inside a tight bend the offset rail folds
  (`e530`: 78° to its centreline). A station is repaired only when **every** one of its steps
  folds — 1 station. "Any step" broke `e642` station 18 (far face −0.55).
- ⚠️ The fold test is not a squareness bar: squareness is `facing_away`'s own predicate and a
  repair keyed on it reads 0 by construction (`Q58`). `facing_away` is non-zero at 4 of 16 swept
  rows, so it is reachable. The two dials are separate on purpose.
- ⚠️ `facing_away` reads each triangle's first-vertex normal and `_Builder` reverses nearside
  winding, so an offside quad is graded against station `i`, a nearside one against `i+1`.
- `tools/railing_error.py` folds both faces onto their mid-surface by mutual-nearest pairing;
  the faces are deliberately not told apart ("nearer a centreline" is wrong on 2,526 of 5,067
  pairs). Cost: every p50 reads half the class thickness further out.
- ⚠️ `cull_disabled` stays: the fence is 60-75% air and the far face shows through the gaps.
- ⚠️ Evidence is a frame (`Q62`): delete the imported `.scn`, re-import, shoot until a hash repeats.

**See.** `Q60`, `Q61` · `Q58` · `Q78`.

---

## `Q113` — The ramp's ribbon shrinks at the touchdown, and paints a 1.57 m lane

**Status.** Closed — fixed; the lane-count half it left open is `Q114`.

`Q107`'s clamp cut the off-grade ribbon to `deck_rim_m` at vertices not on structure: `e208`
FLEMING ROAD's last vertices read `on_structure: False` with a rim of 0.100 —
`carriageway.DECK_ACROSS_M`, the end of the structure, not the edge of the road. The ribbon went
5.60 → 3.15 m and the markings shader, which cuts the **drawn** ribbon into `lanes` equal strips,
painted a 1.57 m lane.

- Fix: `surface._deck_rims` discards the rim where `on_structure` is `False` — `Q107`'s own rule,
  absence of a deck is `inf`, never 0.0. 20 vertices over 6 edges, binding on 4; levels 0 and −1
  byte-identical; only `clearance` moved. `e208` `clear_width_m` 2.00 → 2.25 m.
- 🚫 Not by removing `Q107`'s clamp (`overhang.py` 4.3% → 3.3%, right wherever the deck is real),
  and not by moving `width_m`. The remaining cuts (93 vertices, 18 edges) are all on structure.
- ⚠️ `overhang.py` reads 0.1 pp worse: a ramp resting on terrain counts as hanging (`Q90`).
- ⚠️ A wider ribbon can lose clearance (`e365` 4.75 → 4.50): the corridor is measured inside the
  paint (`Q109`).
- ⚠️ The test fixture `_edge` defaults every vertex off structure; clamp fixtures set
  `on_structure`, which also switches `Q23`'s authored-width drawing.
- Latent faults fixed in review: `nearest_edge` took the off-level fallback only when nothing
  on-level was found (233 of 17,400 probes missed a road); `fence._adjacency` filtered to literal
  level 0, so `place` raised `KeyError` on an open off-grade edge; `fenced_edges` fenced id `1`
  when nothing was closed. `PlanLattice.over` now probes at the road's median height, so its
  timing is a different population from earlier figures.
- ⚠️ `tools/reachability.py`'s `DRIVABLE_LEVEL` no longer restates `RoadGraph.is_drivable` since
  `P4-1`; inert while every fenced edge is level 0.
- Open, unscoped: the real lane count varies along an edge (FLEMING ROAD flyover: 2 splitting to
  2+1 on landing) and `lanes` is one number per edge.

**See.** `Q107` · `Q110` · `Q103` · `Q109`.

---

## `Q114` — The lane count invented lanes the road has not got

**Status.** Closed — fixed at `ROADGRAPH_SCHEMA` 11; per-edge `lanes` remains a limit.

The painted strip is drawn ribbon ÷ `lanes`, a quotient no stage computes (`carriageway.py` owns
one, `surface.py` the other). 10 edges / 764 m painted under 2.50 m, worst `e306` at 1.15 m.

- `tools/lane_paint.py` is the sweep. Its bar is TPDM 4.3.9.8's narrow end from
  `carriageway_survey.width_bounds.lane_m` (3.00 m), swept; it imports
  `carriageway_margin.lane_bracket` rather than restating it. ⚠️ The verdict is three states: a
  missing bracket or an authored width (`lanes × 3.2`, a tautology) is `ungraded`, never
  agreement. ⚠️ `narrow_points` is min/p1/p10/p50 on purpose — a lane fails at its narrow end.
- At grade: `LANES_FLOOR` published 2 wherever 1 was measured, to keep `RoadGraph.lane_offset`
  off the centreline. The floor now lives in the consumer as `RoadGraph.LANE_FLOOR`
  (`lane_offset(w, 1) == lane_offset(w, 2)`) and the published count is the measurement: 60 edges
  publish one lane. `lanes_single` replaces the write-only `lanes_floored`.
- 🔴 `_ROW_MIN` did not follow the floor down: a row of one arrow is a marking, not a count (81
  edges state one). `test_the_row_bar_is_NOT_tied_to_a_publishing_floor` pins it.
- Off grade every count is `authored` (no turn arrows on any deck here; 2D rays find the street
  underneath). The deck is a ceiling, never a source — paint cannot be wider than its structure
  (`Q107`'s licence). One-sided on purpose: of 36 deck-width edges, 6 cut (`deck_capped`), 22
  inside, 8 below and untouched. `_deck_lane_ceiling` **refuses** a `(0, 0)` bracket rather than
  clamping it to one.
- Result: under 2.50 m → 1 edge / 41 m; none under 2.00 m. No geometry moved — only
  `TEXCOORD_0` / `TEXCOORD_1` and the arrows' lane snap. `tools/carriageway_margin.py`, which
  shares no code, disagrees on 0 of 208 measured counts.
- ⚠️ Removing the floor exposed `lanes_row_over_bracket` 6 → 9 (`e36`, `e163`, `e642`: two arrows
  abreast over a one-lane bracket) and `stacked_disagreeing` 25 → 29. Reported, never used; a
  rising count is a finding, not a bar to retune (`Q19`).
- ⚠️ GDScript `##` attaches to the next declaration, so a constant above a function takes its docs.
- Left: `e257` CANAL ROAD FLYOVER at 2.45 m inside its `(1, 2)` bracket — narrow, not a defect.
  At the 3.00 m bar 7 off-grade edges / 352 m remain, all inside their brackets; whether that is
  the right bar for a painted strip is unasked. STEWART ROAD `e505` was later answered by `Q130`.

**See.** `Q113` · `Q94` · `Q95` · `Q107` · `Q103` · `Q72` · `Q126`, `Q130`.

## `Q115` — What repeats ships as a prop with placements; what is measured stays merged

**Status.** Open — `P5-1`–`P5-6` built and passed the user's drive; `P5-8` is outline only.

Rule: modularise where the real object repeats. Each step keeps the ETL's registration and every
counter; only the output changes, from merged triangles to a library `.glb` plus a
`*_placements.json`. Each step owes an A/B frame at a fixed camera (`Q62`).

- ⚠️ The draw-call budget stays (mobile 150, the Adreno 618 floor; web runs `gl_compatibility`);
  no device exists to re-measure on. A `MultiMesh` costs the same draw as a merged mesh, plus one
  per shadow cascade — about 1.7 draws a library mesh. It is one AABB, so instancing buys bundle
  size and per-prop quantisation (`Q82`), not culling.
- ⚠️ `prims` counts a `MultiMesh`'s base mesh once per pass, so it no longer proxies drawn
  triangles on a prop layer.
- Convention, stated once per side: `gltf.placed_positions` (scale, pitch about the mesh's own
  `+X`, bearing, move) and `GeneratedPlacements.placement_of` (`basis * Basis(RIGHT, pitch)`;
  ⚠️ `Basis.rotated` turns about the world's X). Shared code: `pipeline/placements.py`
  (`Library`, `stand_library`, `placed_at`, `pitch_between`, `PLACEMENTS_SCHEMA`) and
  `GeneratedPlacements.check_join`. Each stage asserts
  `placements + placements_refused == drawn`.
- ⚠️ `facing_away` / `inverted` are asked of the library mesh or the stood copies, never of a
  basis determinant, which passes by construction (`Q72`).
- ⚠️ An entry carries only channels something reads (`Q54`); the arrows' unread `edge` / `lane`
  keys were 14.6% of their document and were dropped.
- ⚠️ Undecided: `indent=2` is 831,665 B across the four placements documents; `documents.py`'s
  argument defends `ensure_ascii` and the trailing newline, not the indent.
- PCK across `P5-3`–`P5-5`: 50,443,828 → 49,209,752 B (−2.45%).

### 🔴 Refused, each with its number

- **A road kit.** Of 737 level-0 edges, 418 (57%) bow over 0.5 m off a straight piece (p90
  7.2 m); 88 distinct widths; 301 of 380 junctions are 3-way; half the arm angles are over 10° off
  a grid. A kit moves streets by metres between surveyed footprints; below the measured geometry
  is a stylised city, a reversal of "accurate city, toy vehicles" and the user's call. The
  reusable part of a procedural road is the generator.
- **The Unity grid asset** — wrong engine; partitioning is the 150 m tile grid.
- **Runtime road extrusion** (`Path3D` + `CSGPolygon3D`, or a port of `surface.py`) — poor
  collision, or 2,700 lines duplicated with every grader re-pointed.
- **Box junctions and stop / give-way lines as props** — 20 unique polygons and 191 bars,
  conformed to the cap fan (`Q92`); no repeated rigid unit.
- **Decals for road paint** — an image, refused by `mesh_contract.gd` and `P3-16`. ⚠️ `Decal` on
  the Compatibility renderer is unverified on 4.7.
- **One shared `_register` across `signs`, `lamps`, `railings`** — each difference prevents a
  recorded defect (`Q78`, `P3-26`, `Q95`).

### ✅ `P5-6` — the road is one chunk per tile

The ribbon is built per station and never decimated, so a cut at a station that duplicates the
shared vertices is seamless by construction (`Q25`). `_Builder` keys a quad by the plan centre of
its two stations and a cap by its centroid (a junction goes whole to one tile); `chunk()`
partitions and moves no vertex. Wan Chai: 65 chunks whose union is the old `roads.glb`; 1,836
duplicated vertices published as `cut_vertices`; +13 to +17 draw calls; PCK +0.31%. The road is
`CityManifest.road_chunks`, streamed by `CityStreamer`; graders read through `read_surface`;
`verify_road_surface.gd` asks the kerbside-extent rule of the union. ⚠️ The streamer holds the
chunks under the start line synchronously; a threaded load would move every `drive.sh` timeline.

### ✅ `P5-1` — `generated_layer.gd` and `layer_preview.gd`

Eighteen per-layer scripts became one table-driven loader and one preview; bundle byte-identical;
closed `Q74`. ⚠️ Callers pass constants (`GeneratedLayer.LAMPS`), never strings: a misspelt id
makes `is_present` false and a verify tool's skip branch exits 0. `verify_city.gd` holds both
scenes' `layer` strings against `ids()`. ⚠️ `is_present` exists because `load()` on an absent
path prints `ERROR: No loader found` (`Q77`). ⚠️ A script deletion owes a grep of the whole
repo — `.claude/`, `.tres` and `.gdshader` included.

### ✅ `P5-2` — the signs are a library

`signs.glb`: 24 meshes / 455 triangles (20 face codes, 2 mirrored boards — a mirror cannot be a
transform under `cull_back`, `Q66` — 2 lettering quads, a unit pole, the one `scale`).
`signs_placements.json`: 1,251 = 671 plates + 83 lettering + 497 poles, within 0.13 mm of the
merged mesh; `signs.json` schema 5. Draw calls +35, not the +22 planned (shadow passes).
⚠️ Whether small faces cast shadows is `P2-6`'s.

### ✅ `P5-3` — the lamps are one prop

One mesh `LPO` (40 triangles) stood 892 times; `lamps.json` schema 2; draw calls 1 → 1; counters
byte-identical. ⚠️ The column's hexagonal ring is seeded from its own arm so it turns with the
stand — up to 46.6 mm from the merged build (`column_radius_m` 0.09). Mesh compression stays off:
road, tiles and fence are still region-wide (`Q82`).

### ✅ `P5-4` — the arrows are a glyph library, pitched in the transform

7 glyph meshes stood 747 times with `rot_y_deg` and `pitch_deg` (max 7.69°, `e71`); `arrows.json`
schema 2; +10 draw calls; counters byte-identical; the lane snap stays in the ETL. ⚠️ The glyph
is rigid where the merged build sheared it, so its plan footprint shortens by
`length × (1 − cos pitch)` (max 18.2 mm) — the more faithful form. `paint_clearance.py` expands
the library with `stood_positions`.

### ✅ `P5-5` — the barrier family is tiled panels, and the cost is published

One 6-triangle unit panel per class, `panel_m` wide (2.0 / 1.5 / 3.0), stood 5,035 times;
`railings.json` schema 3. A piece is `floor(length / panel_m + 0.5)` rigid copies; under half a
panel lays none. 🔴 `panel_m` is the post pitch in the class's `.tres`, bound by a test: a joint
stands under a post, as a real HK railing does — the one step that trades accuracy, toward the
city. The cost is published and never closed (`metres_snapped`, `joints`, `joint_gap_m` max
59 mm, `bends`): a panel stretched to hide a wedge is a fence the survey did not publish (`Q54`).
The sharpest joint, 61.3° at `(1443.2, 138.6)`, stands as a counted wedge; the user asked for no
mitre. ⚠️ `railing_error.py` walks the unit panel, seeded at its foot height (a pitch moves plan
by `sin(pitch) × y`); walking the expansion reads 21,499 m of an 8,850 m fence.

**See.** `Q116` · `P3-29` · `Q82` · `Q62` · `Q92` · `Q25` · `Q78`, `P3-26` · `Q10`.

## `Q116` — Two regions meet at a hard edge, and the join decides where the cut is, not the unit

**Status.** Open — `P5-7a`–`g` and `P5-9a`–`d`, `f`, `g` built; `P5-9e` refused; remainder below.

Remainder: the user's verdict on the legal line; the cap's foreign mouth drawn as a hard edge at
node 224; `_read_offside` pairs owned edges only; `e364`'s per-edge `offset_m`, handed to `Q103`.

- A whole-city model is refused twice: `Q10` (float32 spacing 3.9 mm at 38 km) and size (`Q115`).
  The region is the unit above the tile; the streaming unit is the 150 m tile (per edge is 737
  draw calls and a cut edge is still cut).
- The defect was the cut: `roads.py` clipped to the rectangle, the two rectangles do not share a
  line (0.624 m apart, `Q7`'s flooring plus projection), and per-edge `width_m` / `lanes`
  disagreed on 7 / 3 of the 9 crossing pairs.

### ✅ The assignment rule

1. Membership is on the declared geodetic `bounds`, half-open, never the projected rectangle.
   `config.py` refuses overlapping regions.
2. A crossing feature is clipped to the union of the declared regions it touches and kept whole
   across internal lines. The rectangle stays for undeclared territory and as the sheet selector;
   `bounds` never move (`Q10`).
3. The owner is the region containing the run's first vertex in the direction of travel (after
   `BACKWARD` normalisation; source order for `both`) — tolerance-free, the same from either build.
4. The owner publishes the edge measured over its whole run; every other region it enters
   publishes a foreign copy. Identity across bundles is `(source_id, run ordinal)`.
5. A boundary node is a graph node, never a rectangle intersection. Caps go whole to the region
   containing the node.
6. A prop is owned by the region containing its surveyed point and may host onto a foreign edge.
7. A turn restriction is published by the region owning its pivot node.

`join.reach_m` (133) widens sheet selection and source-read boxes toward a declared neighbour so
the owner can measure its far half (user: "always fetch more data if useful"); a region with no
neighbour is byte-identical. `stations_beyond_reach` refuses what falls outside (`Q54`).

🚫 Refused: length-share or midpoint ownership (48/52, 49/51, 46/54 — flips under a
`simplify_tolerance_m` change); one agreed easting (a cut vertex is not a graph node); omitting
the foreign copy (the boundary junction loses a mouth); moving `bounds` to a grid line (`Q10`).

### ✅ The rule applied to the nine crossing runs (`P5-7b`–`P5-7g`)

Wan Chai owns 4 crossing runs (`e171`, `e356`, `e364`, `e691`), Causeway Bay 5 (`e1`, `e11`,
`e20`, `e93`, `e96`); the level-1 ramps split one each way, so both regions owe the reach.

- `GameTransform.from_bounds` floors the origin outward (`Q7`), so a run clipped at an outer edge
  can start inside no region; the fallback is the clip rectangle, asserted never to fire on an
  internal line.
- Both regions clip to `Config.clip_extent`, the own rectangle extended along the shared axis
  only. ⚠️ One seam node of sixteen is therefore 4 cm off (CAROLINE HILL ROAD's south end); the
  merge takes the owner's copy.
- Foreign copies live under a top-level `foreign_edges` list (`ROADGRAPH_SCHEMA` 12), not behind
  a filter: nineteen readers iterate `edges`, and a list none opens is inert by construction. A
  copy carries the authored width; `foreign: <owner>` says whose measurement a merge takes.
- Edge ids keep their read ordinal, with gaps, so every cited id holds. Node ids renumbered.
- ⚠️ Foreign edges are offered to the kerbside join as tracks and published on nothing; without
  them a restriction past the line snapped to the neighbour's road. ⚠️ The turn resolver indexes
  by id, so its sequence stays in id order — `owned + foreign` resolved 35 → 11 turns silently.
- `P5-7f`: `surface.py` shapes the neighbour's runs against a scratch report so a cap's hull
  reads every mouth; cap ownership is `roads.Ownership`; 0 foreign ribbon drawn. An owned far
  half rides in the last column's chunk, and `city_streamer.gd` picks by `aabb`, never tile id —
  load-bearing, because the tile grids are 1,649 m apart, not a multiple of 150.
- `P5-7g`: `tools/join_seam.py`'s bar is one owner per run, 0 nodes on the internal line, 0
  unmatched copies. `pipeline/join.py` is the reference merge (delta `[1649, 0, 0]`, owner's copy
  kept, seam nodes named by `(source_id, run)`, never a distance): **999 edges / 764 nodes (16
  unified) / 252 turns / 0 dropped / 999 clearance rows**. `tools/reachability.py --graph-dir`
  routes 126,275 pairs across the join.
- 🔴 The cut's one finding: `Edge.offset_m` is one median per edge. Whole, `e364`'s far half drags
  it −0.1 → −2.9 m and `_clamped_rails` cuts the near half 3.35 → 2.05 m. The fix is a
  per-station offset (`Q103` / `Q107`). `clearance_reconcile.EXPECT` is region-keyed, and a
  region with no recorded triple is refused.
- ⚠️ A region's `deck_error` / `overhang` read worse at the seam (Causeway Bay 25.1%): an owned
  far half rides over tiles its bundle lacks. Its far-half `clear_width_m` is refused, never read
  off the neighbour's `etl/out` — one region's build must not depend on another's.
- Causeway Bay: no carve (`e45`, `e46`); the fence's 170 of 39,402 pairs is what a carve must beat.

### ✅ The runtime half (`P5-9a`–`P5-9f`)

- One `Node3D` per region at `city_offset(r) − city_offset(frame)`; origins are whole metres, so
  the sum is exact. ⚠️ The translated `bounds_game` overlap by ~250 m of owned far halves, so a
  region-space cull would drop them.
- Ids collide across regions (`clearance.json`, `city.json` `carriageway[]`, `fence.json`,
  `fares.json`). The runtime carries one id map per region — `(source_id, run)` to merged id, the
  frame's kept, the second's renumbered from `max + 1`, a foreign copy aliasing its owner —
  applied at load; no document is edited (`Q54`); a fare is `(region_id, id)`.
- 🚫 Refused: a city-wide id space at export (the join is a runtime act); anchoring the scene in
  city space (`Q10`); one streamer over N manifests.

### ✅ `P5-9a` — the seam is priced, and it is under budget

`tools/resident_budget.py --pair`: the seam camera `(1703.2, 437.9)` holds 73% and the pair's
worst stays Wan Chai's `(1125, 525)`, so `P4-5` inherits only its own 105%.
`driver.gd --spawn-fare=<region>/<id>` starts a drive anywhere and refuses what the harness
would only warn about.

### ✅ `P5-9b` — a directory per region

`generated_regions.gd::dir(region)` is the one root; `""` means `--region=`, else the frame.
`check.sh` runs every verify tool per region listed in the sync-written, gitignored
`regions.json`. ⚠️ `landmarks.json` still names `res://assets/generated/landmarks/hkcec.glb`;
`CityManifest.resolve_asset` and `carriageway_occupancy.py` map that prefix onto the region's
directory. ⚠️ The sync deletes a region synced before and not listed now.

### ✅ `P5-9c` — one node per region; the tiles are not in it

`region.tscn` holds the eight layers, `Landmarks` and `Fence`; `CityRegions` places one per
region and adds a `CityStreamer` when handed a `StreamingProfile`, `tile_preview.gd` otherwise.
⚠️ `hold_ground_at` asks every region, because the boxes overlap along the line.

### ✅ `P5-9d` — the runtime merge is `join.py`'s, plus the id map

`road_join.gd` ports `pipeline/join.py`, and `verify_join.gd` holds it to the Python field by
field. ⚠️ No shipped fare, fence row or turn names a foreign id, so the aliases are guarded only
by the check that every foreign copy resolves to its own `(source_id, run)`. ⚠️ `shared()` merges
what `resident()` answers; `--region=` narrows it to one for the per-region verify tools.

### 🚫 `P5-9e` — sharing the prop libraries: built, measured, refused

A `MultiMesh` is culled by its own box, so unshared per-region batches cost nothing out of view;
one batch per mesh name across regions spans 1.6 km and is never culled: +3 to +11 draw calls
and up to +262,000 primitives at the seam for an identical picture. ⚠️ The library files differ
(Causeway Bay alone has `TS589`) but every shared mesh name is identical — a future design keys
by name. Re-propose only with a culling argument; a shared `Mesh` buys memory, not draw calls.

### ✅ `P5-9f` — the taxi crosses the join

From `f_045` (CAUSEWAY ROAD, on `e356`) a throttle-only drive enters Causeway Bay's westbound
one-way at the bend and the wrong-way siren rings — the merged graph working. The legal line is
one 0.22 s left steer at the seam node `(1703.2, 4.5, 437.9)`: no step, no barrier, no siren.

### ✅ `P5-9g` — the `f_045` drive was non-deterministic: the camera booted at `f_004`

`DriveHarness._ready` runs last, after `ChaseCamera` snapped to the authored `f_004` start, so
`CityStreamer._collect` measured from ~1.5 km off and freed all 29 held chunks on the first
frame; runs parted at tick 10–11 and the harness switched off fall recovery on every drive not
started at `f_004`. Fix: `ChaseCamera.snap_to_target()`, called by the harness after every
teleport. 🔴 Not from `VehicleController.place_at` — auto-right teleports through it.
`verify_city.gd` fails when `city_drive.tscn` leaves `camera_rig` unassigned.
`driver.gd --trace=<file>` is the instrument that found it. ⚠️ Residual: the t 3 frame of a pair
differs by 0.40% of pixels with identical car state — `cmp` a later frame. ⚠️ Distant bodies
still arrive on disk-chosen ticks; nothing holds the route.

**See.** `Q115` · `Q10` · `Q6` · `Q25` · `Q103`.

---

## `Q117` — Opposed one-way ribbons are paired geometrically, and the join is published

**Status.** Closed. The pairing and the codec's `centre` step stand; the shader line it fed is off
(`draw_pair_join` 0.0 since `Q118`, `draw_centre_line` 0.0 since `Q132`), and the join is drawn as
geometry by `Q125`.

- Road Network v2 gives each carriageway of a dual road its own nodes, so the old shared-endpoint
  match in `surface._read_offside` found 6 pairs where 49 exist (12 of 98 paired edge ends).
- Rule: a one-way ribbon's partner is the one-way ribbon at the same level, anti-parallel within
  `roads.surface.opposed_pair_bearing_deg` (30; refused at 0 and at 90 or more), whose centreline
  lies inside the edge's own drawn width — nearest first, and only where the two choose each other.
- No free search radius: the reach is the codec's publish guard read backwards (`steps < 8 * lanes`
  reduces to gap under drawn width). `Q72` refused a radius whose count ran 8 → 80 over 10 → 30 m.
  ⚠️ Since `Q125` the search reach is drawn width plus one kerb; the pairs that adds fail the
  publish guard (`opposed_pairs_unpublishable` 5 → 13, the same 95 edges carry a `centre_step`).
- The angle is the one free value and it is swept, not a plateau: paired ends 84 → 112 over 10–75°
  (1.35x), while `opposed_pairs_one_sided` climbs 4 → 17 as the bar widens. 30 is where it is still
  6.
- ⚠️ `opposed_pair_bearing_deg` and `carriageway_survey.width_bounds.pair_bearing_tolerance_deg` are
  deliberately separate: the survey block is optional, and the two are read in different frames.
- ⚠️ Mutuality is load-bearing: each half computes the join in its own lane coordinate, so a
  one-sided vote draws a second line (the 3.9 m double line `P3-12` shipped on FLEMING ROAD).
  `test_a_one_sided_vote_publishes_nothing` is the mutation check.
- Refused: an angle-free rule (mutual offside-kerb burial). It lands on the same population but its
  "buried share" bar swings the pair count 62 → 4 over 0.10 → 1.00 (15x), against the angle's 1.35x.
- A centre line moves no geometry: only `TEXCOORD_1.x`'s centre field differs. A missed pair costs a
  centre line, never a kerbside yellow — `offside_kerb` rests on buried-kerb geometry, not on
  pairing.
- ⚠️ The plan-bounds reject in the pairing loop is plain floats on a `_Ribbon` NamedTuple (34 ms
  against 395 ms as arrays), so the box-disjoint test is written twice on purpose beside
  `_Occluders.cover`. It is a bound, not a reading: deleting it leaves the votes byte-identical.
  `_pair_gap_m` is memoised on the unordered pair.
- Shader facts that still hold (`road_markings.gdshader`, `tuning/road_markings.tres`):
  - RM1001 on `CT174/51-5(1)F` is `LINE WIDTH = 150, LINES SPACING = 100`. ⚠️ `LINES SPACING` is the
    clear gap, not a pitch; `centre_gap` 0.0367 is exactly 100/150 of `centre_width`.
    `RoadMark.band_offsets_m` makes the same derivation.
  - ⚠️ `yellow_gap` is a pitch, not a clear gap; no shared "double line" helper, deliberately.
  - ⚠️ U is normalised to the ribbon as drawn: a U-lane is `2 * half_width / lanes` (5.12 m here),
    not `lane_width_m`. `surface.py::_u_metres` is the ETL-side form.
  - ⚠️ Summing the two `line_coverage` calls is exact because the intervals are disjoint; do not
    change it to `max` (`railings.gdshader::bars()` uses `max` for the opposite, correct reason).
    No distance fade is wanted.
  - The divider-suppression window is `max(CENTRE_DIVIDER_CLEARANCE_U, <geometry>)` and the test is
    `<=`: `centre_at` is in sixteenths, so a join can land exactly on 0.25.
- Open: the range guard is per edge, so 5 pairs publish from one half only (e.g. `e208` FLEMING);
  refusing both halves is a one-line change and the user's call. The 6 one-sided votes are
  unexamined — a finding to look at, never a bar to retune.

**See.** `Q53` · `Q72` · `Q94` · `Q54` · `Q62` · `Q118` · `Q125`

---

## `Q118` — RM1001 is drawn from TD's survey; `RoadMark.axis` selects the host rule

**Status.** Closed. `longitudinal_legibility_scale` 1.0 and `draw_pair_join` 0.0 on the user's call.
Open items at the end.

- `DTAD_RD_MARK_LINE` publishes RM1001 (double continuous white) as surveyed polyline; drawing it
  replaces `Q117`'s inferred no-overtaking line (`Q54`). ⚠️ WHITE is read off the sheet's
  Description column; `LINETYPE` carries no colour, and RM1040–RM1049 on the same sheet are yellow.
- Drawable population is 5,745 m at grade, not the 19,308 m in region: 12,681 m is A03 structure
  (the Central–Wan Chai Bypass grazing the bounds) and 882 m is A01. 91 parts / 3,416 m draw.
- ⚠️ RM1002/RM1003 are not absent: TD files them in `DTAD_RD_MARK_LINE_C` (2,046 m + 2,165 m at
  grade, `Q132`). They break one line of the pair, a per-line module the `marks:` schema cannot
  say; RM1004 has `LINES SPACING = VARIABLE` (40.7 m in region).
- `RoadMark.axis` is required with no default: transverse scores `|90 - crossing|`, longitudinal
  `crossing`. `bearing_tolerance_deg` is shared and means degrees off the marking's own axis.
- Markings are clipped to the region with `roads.clip` (6 of 143 at-grade parts reached outside).
  ⚠️ Not inert on transverse marks. `clip` returning no runs is counted as `outside_region`; the
  counter is 0 here and unexercised.
- Height: `DrawnSurface.sample` resolves to the nearest level-0 centreline, and level-0 ribbons
  stack in plan (`e465` climbs 7.87 m; 16 level-0 edges stand on structure), so
  `tools/paint_clearance.py` failed at 1.50% against 0.50%.
  - Refused: sampling from the host's own edge — 1.50% → 8.58%, because a marking up to 236 m long
    spans several edges and flat-lines past its host.
  - Shipped: a longitudinal marking must lie within its host's drawn half-width or it is refused
    (`host_off_carriageway`, 52; `_on_its_own_carriageway`). Buried share 0.21%. ⚠️ Transverse marks
    are exempt on purpose — a stop line's `host_distance_m` p90 is 16.1 m.
  - ⚠️ The gate reads `host.width_m`, an edge mean and a midpoint measure: it catches a line beside
    the wrong road, not one across it, which is the bearing guard's job.
- `road_marks.longitudinal_legibility_scale` is 1.0 (the user refused 1.88 as too thick). The dial
  is kept; below 1.0 is refused as a transcription error; the gap scales with the lines;
  longitudinal only. ⚠️ The sub-pixel illegibility at distance remains — the answer is
  antialiasing, not width.
- `draw_pair_join` stays 0.0 and must not be switched back on: RM1001's host is a one-way edge on
  85 of 91 parts, so the two lines fight. `centre_at` stays in the codec. The pairs no survey covers
  are drawn as geometry by `Q125`.
- ⚠️ Per-marking host search is cubic in marking length (8 markings carry 69% of it), invisible
  today. Batching the height join (`Segments.nearest_many`, `DrawnSurface.sample_many`) measured
  378 → 155 ms and was refused: ~0.22 s of build time, new shared API, and not bit-identical
  (heights differ to 9.9e-11 m). Take both halves together when a region makes it bite.
- Open: the 52 refusals are recoverable only by making `DrawnSurface.sample` resolve by ribbon
  coverage, a change to `Q92`'s shared accessor. RM1002/RM1003 need a per-line module.

**See.** `Q117` · `Q125` · `Q132` · `Q54` · `Q92` · `Q59` · `Q69`

## `Q119` — An editor save is a no-op; resource rationale lives in sidecar `.md` files

**Status.** Closed 2026-09-07.

- The "dropped settings" were engine defaults. Godot's writer omits any key equal to its registered
  default, so the three warning promotions and `rendering_method.web="gl_compatibility"` were in
  force on every build that "lost" them. `run/max_fps.mobile` survives because it has no default.
  ⚠️ The `[importer_defaults]` loss in `Q104` is not explained by this; `verify_settings.gd` pins
  it.
- A grep of `project.godot` is the wrong instrument: presence is not the setting.
  `game/tools/verify_settings.gd` reads every promotion and pinned value back through
  `ProjectSettings`. `project.godot`, `export_presets.cfg`, every `.tres` and `.tscn` are committed
  in the writer's own form; only a GUI save writes, and it writes what is committed.
- Every `;` comment block moved to `<name>.md` beside its resource (0 differing stored properties
  across 33 files). `check.sh`'s `tuning` step requires a non-empty sidecar per resource unless
  `UNDOCUMENTED_OK` names it, refuses any `;` line, an orphan sidecar or a stale exemption.
  ⚠️ `beams.tres` is empty because all its values equal `beam_profile.gd`'s defaults.
- Divergences from Godot's best-practice guide, priced and kept:
  - HUD built in code — 387 µs against 140 µs from a `PackedScene`, once per load; a scene would be
    a second copy of `hud_style.tres` / `hud_layout.tres`.
  - Input polled in `_physics_process` — 0.149 µs per tick; `driver.gd` replays through
    `Input.action_press`, which emits no event.
  - `BeamBudget` as an autoload — a scene that forgets the node takes the "light everything" branch.
  - Typed node exports: the null measured here was the missing `node_paths=PackedStringArray(...)`
    attribute on the node line; re-measured and migrated at `P5-21` (`Q124`), bar the two autoload
    references.
- Followed: `.gitattributes`; `FpsCounter` folded into `DebugHud`; the input source injected by
  `NodePath` into `VehicleController` and `ChaseCamera`; `main.tscn` as Main / World / GUI, with
  `scenes/city_drive.tscn` moved out of `scenes/dev/`. Inertness proof: `skidpad.sh` byte-identical
  and draw calls 102 / 110 / 139 (off / minimal / full) unchanged. ⚠️ The wrong-way route's 9 s
  frame can differ between runs by the driver's sampling phase; the 8 s and 10 s samples are stable.
- 🔴 No Godot process may be launched above `==> import` in `check.sh`: autoloads are instantiated
  around any `--script` run and name `class_name` globals, which resolve only from
  `.godot/global_script_class_cache.cfg`, which only the import scan writes. A verify tool printing
  `ok` is not evidence its run was clean — `run_godot` reads stderr too. ⚠️ `Q75`'s "a `settings`
  step, before `--import`" is history.
- ⚠️ `check.sh` writes `FAIL` lines to stderr and CI interleaves them by arrival; search the log for
  `FAIL`, never read what precedes `FAILED`.
- False greens closed: the warnings sweep and `gdformat` both assert a non-zero file count (a `cd`
  inside `$( )` exits only the subshell). The sweep pattern is `treated as error|Parse Error`.
  ⚠️ Do not widen it to `$FATAL`: `--check-only` resolves no autoloads, so a healthy sweep emits 4
  `SCRIPT ERROR|Failed to load script` lines and 0 `Parse Error`. A semantic parse error in a file
  no autoload reaches is invisible to `gdformat` and to `--import`.
- `skidpad.sh` and `drive.sh` name the missing class cache on a run that is already failing; the
  hint is never a pre-check. ⚠️ `FATAL` and this hint are hand-copied across `check.sh`,
  `skidpad.sh` and `drive.sh`; there is no `tools/_lib.sh`, and adding one is the user's call.
- Refused: parallelising the sweep. `--check-only` writes nothing under `.godot/`, so it is safe
  (1.47 s against 10.09 s), but BSD `xargs` has no `-d` and the `-I{} sh -c` form interpolates a
  filename into a shell command.

**See.** `Q75` · `Q99` · `Q104` · `Q91` · `Q82` · `Q72` · `Q124`

---

## `Q120` — Four regions measured: Wan Chai is not the dense extreme

**Status.** Open. Coefficients closed; the streaming distances are `P4-5`'s. `carve.edges` is
region-keyed (`P5-7`); the `Q19` battery ran on `causeway_bay` (`P5-7a`); `sha_tin` and `mong_kok`
are unmeasured.

`causeway_bay`, `sha_tin` and `mong_kok` were added to `hong_kong.yaml`, each the same
0.016° × 0.008° box as `wan_chai` (1.457 km²). `causeway_bay` shares Wan Chai's east edge at 114.188
exactly, which makes it the join fixture.

| region | buildings | LOD0 tri | tile MB | road km | edges |
|---|---:|---:|---:|---:|---:|
| `wan_chai` | 1,419 | 515,025 | 39.9 | 56.15 | 797 |
| `causeway_bay` | 570 | 322,864 | 20.6 | 13.43 | 211 |
| `sha_tin` | 761 | 245,491 | 15.6 | 22.33 | 250 |
| `mong_kok` | 2,061 | 944,004 | 53.9 | 37.97 | 537 |

- `mong_kok` is 35% denser than Wan Chai (37.0 against 27.4 tile MB/km²). The ≈2.4 GB
  whole-territory estimate holds in order of magnitude and was never conservative.
- Planning denominators: tiles scale on building count (27.7 KB/building, 1.8x spread, against 3.5x
  per km²); the thin drawn layers on road-km (~66 KB/road-km, 1.47x spread; drawn layers only);
  terrain on area — a zero-building 150 m tile costs p50 66,432 B, ~2.9 MB/km², ~290 MB over a
  ~100 km² territory, and nobody has costed it.
- A 200 MB bundle buys 5.0 km² at Mong Kok density, 6.3 at Wan Chai, 13.0 at Causeway Bay, 15.5 at
  Sha Tin. Plan the free/IAP boundary against 5–15 km²; it is a fidelity question first.
- Libraries are flat: 40 library meshes in every region, `lamps.glb` byte-identical in all four. So
  draw calls are region-invariant, and chunking `roads.glb` (`P5-6`) costs a bounded +20–25.
- 🔴 Resident budget, as corrected by `Q122`: banded the way the engine bands (plan distance to the
  tile `aabb`, `TileStreaming.band_of`), the shipped `streaming.tres` pair (`tier_distances_m`
  [250], `unload_distance_m` 400) holds 105 / 76 / 47 / 184% of the 300k-triangle budget at the
  worst camera in `wan_chai` / `causeway_bay` / `sha_tin` / `mong_kok`. `tools/resident_budget.py`
  is the instrument (`--band-by centre` reproduces this record's original, wrong 71 / 51 / 31 /
  108%). The worst camera, not the region average, is the statistic. ⚠️ Pull-in distance is a look
  decision (`Q26`) and a hitch decision (`P4-5`), so no replacement pair is chosen here. The
  LOD1-ratio lever this record proposed is refuted in `Q122`.
- The retired risk "building meshes blow the triangle budget" is un-retired: its evidence was
  single-region.
- Refused again: a road component kit (`Q115`). `roads.glb` is 2.4% of the bundle in `mong_kok` and
  4.4% in `wan_chai` — the denser the region, the smaller the payoff; buildings are 83%+.
  ⚠️ Chunking is not a kit: it splits the same measured geometry and invents nothing.
- Limits: two of the four regions are flat (`roadsurface` vertical span 183.1 m in `causeway_bay`
  against 59.2 m in `wan_chai`); no handset ran any of it (`P0-3b`); the three new regions carve
  nothing, so their tile bytes read marginally high.
- `carve.edges` is keyed by region; `station_m`, `floor_below_m`, `headroom_m` and
  `soffit_clearance_m` stay city-wide. Region keys are checked against `regions:` at config load.
  `CARVE_SCHEMA` stays 1.
  - 🔴 Edge ids are per-region ordinals (`roads.py`: `edge_id = len(pending)`), so a Wan Chai list
    resolves elsewhere — 7 of 8 name real roads in `mong_kok`. Never build "skip the ids the graph
    does not carry": it turns the loud failure into a silent carve of whatever the integers name.
  - ⚠️ A region absent from the block carves nothing — a measurement not yet taken.
  - ⚠️ Known and left: carve a region, drop its entry, re-run, and `carve.json` publishes
    `edges: []` while the manifest still says tiles are cut. Geometry is never corrupted; the fix
    (reading the manifest on the no-op path) re-couples a bundle-only path to a file that need not
    exist, which is `Q19`'s recorded CI failure.
- `Q19` battery on `causeway_bay` (`P5-7a`): the pipeline runs and `check.sh` exits 0 on its sync.
  - 5 starved level-0 edges; `fence.json` fences `[45, 46, 122]` unattended. Refusing them loses 170
    of 39,402 pairs (1.26%; `e45` KA NING PATH alone 171), against 1 of 187,946 in Wan Chai — the
    fence here walls off a hillside link, not a pocket.
  - No carve list is written; it is the user's call edge by edge. `e45` meets `Q19`'s licence, but
    the blocker is a ramp's mass descending through the path at two crossings, not a flank. `e46`
    TUNG LO WAN DRIVE reads as `Q90`'s class — a touchdown the height model did not lift, which
    `touchdown_error.py` passes over — so it is a height finding (`P2-7`); a cut would remove the
    deck the road should be on.
  - Fails recorded, outside scope: `BUILDING` share of carriageway 2.477% against 1.720%; ground
    proud 2.953% / 7.289% against 1.5% / 3.5% (`Q24`'s hill-street class); `clearance_reconcile`
    7 / 8 / 1. `narrowing` clears 0 edges.

**See.** `Q115` · `Q116` · `Q87` · `Q19` · `Q82` · `Q77` · `Q122`

## `Q121` — The mesh contract against a DCC workflow

**Status.** Open. `P5-10`–`P5-13` built; `P5-14` (textures as an option on tiles, under `P3-20`'s
budget) is held for an artist. Numbers per task in `PLAN.md` Phase 5b.

An outside 3D developer's review found that the defect is not "generated from data" but that there
was no seam between the generated world and a hand-authored asset: identity destroyed at build
time, standard channels carrying payloads, textures contractually forbidden (`mesh_contract.gd`),
collision equal to the render mesh, the road a ribbon overlay with no override layer, and one path
in through `city.json`.

Measured on Godot 4.7.1: node and mesh `extras` are imported; custom `_` vertex attributes are
dropped; a glTF material is kept with its `resource_name`. So per-object identity is a table in
`extras`, and per-vertex identity travels in a UV channel.

- `P5-10` — the `landmarks:` block is the authored door (`replaces_source_ids` optional). The first
  DCC export (`tools/make_dcc_fixture.py`, Blender) is graded by `tools/verify_authored.gd` in
  `check.sh`'s always-on set.
- `P5-11` — `TEXCOORD_0` is a planar façade UV in metres; `TEXCOORD_1` carries marker, phase and
  object row; each tier ships its object table as mesh `extras`. Graded by `verify_tiles.gd`.
  ⚠️ PCK +10.9%, of which the per-vertex along-coordinate is +10.2%; reversible in one line and the
  user's call. The carve reads tiles back and is a consumer of these channels.
- `P5-12` — the collider is its own `<tile>_collision-colonly` primitive at
  `buildings.collision_cell_m` (per-class overrides), and every road chunk carries a `-colonly`
  ribbon. The cell equals the finest tier's by value, so `tools/collider_offset.py` reads 0.000 m.
  Sweep: 2 / 3 / 4 m cells keep 87.8 / 72.9 / 63.5% of the triangles at a façade p90 offset of
  0.47 / 0.62 / 0.91 m. The carve cuts every primitive.
- `P5-13` — each tier file carries a `<tile>_occluder-occonly` primitive from `BUILDING` and
  `INFRASTRUCTURE` at `buildings.occluder_cell_m` (per tier since `Q122`; 4 m, `INFRASTRUCTURE` 1
  m). `rendering/occlusion_culling` is on and pinned.
  - ⚠️ The culling unit is an instance, and instances here are 150 m tiles, road chunks and
    region-wide `MultiMesh`es: it culls 2 draw calls on Wan Chai's throttle route and 12–47 at
    Mong Kok's worst camera. Price: PCK +5,734,832 B (+10.3%) on Wan Chai. 8 m keeps the east win
    and loses west; 16 m loses it entirely.
  - Not measured: the handset CPU cost (Embree raycast per frame, BVH rebuild per tile swap;
    `P0-3b`).
- `meshes/generate_lods = false` ships: PCK −5,262,224 B (−8.6%), draw calls and frames identical,
  primitives submitted +16–30% — the importer's LODs were being drawn, not wasted. ⚠️ Reversing it
  is one value plus deleting every generated `.import` sidecar (`Q122`, `P5-16`).

Refused: per-building nodes (Godot 4 has no static batching; ~50 draw calls a tile); custom vertex
attributes (dropped on import, measured); a convex hull per building (an L-shaped podium's hull
blocks the street); heightfield terrain (the ground is a decimated source mesh, not a grid).

Held, with the trigger: the non-convex cap (an authored piece on a cap); `authored_roads:` (an
artist); decals (`Q115` stands; a Mobile-renderer decal test first); the opposed-ribbon collider
union; a landmark LOD tier (`P0-3b`).

**See.** `Q115` · `Q102` · `Q63` · `Q82` · `Q53` · `Q62` · `Q122`

## `Q122` — The verifier's ambiguous sample, the per-tier occluder, and the resident budget

**Status.** Open. `P5-15`–`P5-18` built; the far-tier occluder and a web bundle without one are the
user's call. Numbers per task in `PLAN.md` Phase 5b.

- `P5-15` — the red `mong_kok` check was the verifier, not the road. `verify_road_graph.gd` sampled
  station `size / 2`, which is the end node of a two-point edge, where `RoadGraph.nearest_edge`
  breaks an exact tie by scan order. It now samples the midpoint of the middle segment, expects the
  lerp of the two stations' drawn half-widths, and asserts the hit's edge; a mismatch is a finding,
  never a skip. No ETL or schema change. It prints its exposure per region (`at end node /
  resolving elsewhere`): 18/0, 13/0, 15/1, 22/5.
- `P5-16` — `check.sh`'s `sidecars` step (after `settings`) holds every generated `.import` sidecar
  present to the `meshes/*` keys `[importer_defaults]` pins; it passes on an empty tree.
  `[importer_defaults]` seeds new sidecars only (`Q82`), and `sync_generated.sh` keeps a sidecar
  wherever its asset persists. `Q124` / `P5-20` extended it to `authored/`.
- `P5-17` — `buildings.occluder_cell_m` is a per-tier list (`null` = none); `city.json` 30 carries
  the flag per tier.
  - At Mong Kok's worst camera `[4.0, null]` is identical to `[4.0, 4.0]` in draws, primitives and
    pixels for −4,628,128 B of PCK (Wan Chai −3,037,152 B); `[null, null]` is −6,072,928 B (−10.9%).
    ⚠️ `[4.0, 4.0]` still ships; each alternative is one line.
  - Refuted, not merely held: the occluder as a streamer content class — the far tier's occluder
    culls nothing this camera set can see.
- The stock Web export template cannot cull: occlusion culling needs the `raycast` module
  (`module_raycast_enabled=yes`), so on the itch.io cut the occluder is pure download. ⚠️ The
  constraint is the template, not the Compatibility renderer. A web cut without it is a second ETL
  build with `[null, null]`; there is no per-preset switch, because the occluder is a primitive
  inside each tile `.glb`. Refused: an 8 m occluder "for the web" — an inert occluder wants zero
  bytes.
- `P5-18` — `tools/resident_budget.py` bands by plan distance to the tile `aabb`, as `CityStreamer`
  does. The shipped distances hold 184% of budget at Mong Kok's worst camera and 105% at Wan Chai's,
  with 21 LOD0 tiles carrying 84–91% of it. With the importer's LODs off, the manifest's tier
  triangle count is the drawn count for a resident tile.
  - Refuted: the LOD1 ratio as the cheap lever. A 4 → 12 m LOD1 cell moves 184 → 163%, and a third
    tier touches the same 9–16%. What is left is LOD0's own cell and radius (`P4-5`, `Q26`).
- Held, with the trigger: custom Web templates with the raycast module (a measured draw-call
  problem on the web cut); the handset CPU cost of the occluder (`P0-3b`).

**See.** `Q121` · `Q120` · `Q114` · `Q82` · `Q62`

---

## `Q123` — A non-convex border quad folds `FlatBuilder`'s fan

**Status.** Closed 2026-09-08 as `P5-19`. `inverted` reads 0 and `check.sh` exits 0 on all four
regions; `boxjunctions.glb` is byte-identical on the other three.

- One border quad on one `sha_tin` box junction was simple, correctly wound and non-convex, so
  `FlatBuilder.polygon`'s fan from vertex 0 emitted one backward triangle (0.0327 m²). A fan from
  `v0` is valid iff the reflex vertex is `v0` or `v2`; the precondition is stated in the docstring
  and not checked.
- Fix: `boxjunctions.border_polygons` refuses a segment whose quad is not convex
  (`_turns_one_way`, on `geometry.orient`), dropped and counted in `degenerate_border_segments` —
  the function's existing drop-never-repair policy. 1 quad in 7,807 across four regions.
  - ⚠️ The convexity test subsumes the older `inner_edge · units[index] > 0` test (0 segments are
    refused by the dot product alone), so nothing can mutation-fail the older one.
  - ⚠️ `_turns_one_way` is a quad rule, not a general fan guard: a pentagram passes it and still
    folds. `test_a_star_polygon_turns_one_way_and_folds_anyway` pins the limit.
- `arrows.json`, `roadmarks.json` and `boxjunctions.json` each publish an `inverted` counter that
  must be 0. Nothing in the ETL enforces it; the engine gates it, and only on a synced bundle. The
  gap was process: an unsynced region's manifest is never read.
- Refused:
  - Masking inverted triangles out of `FlatBuilder.build` — it makes `inverted` 0 by construction
    (`Q58`, `Q72`), the same refusal `railings.py` records for `facing_away`.
  - Widening the sliver bar — a thinness rule answering a winding fault; the fragment measures
    0.0494 m against the bar's 0.0446 m.
  - A build-stopping assertion in `FlatBuilder`, or the ETL refusing a non-zero `inverted` — a
    counter is a finding to look at, never a bar.
- Held, with the trigger: ear clipping or a validity-chosen fan apex in `FlatBuilder` (a second
  producer of non-convex polygons, or visible dropped border metres); a manifest-invariant sweep
  over every `etl/out/<region>/*.json` (a second region publishing a non-zero must-be-0 counter).
- Open, not this defect: `box_extent.py` reports 5 triangles (0.053 m²) inside no published ring on
  `sha_tin`, where `unattributed` must be 0. `PROGRESS.md`'s risk table carries it.

**See.** `Q122` · `Q120` · `Q59` · `Q58` · `Q72` · `Q82` · `Q104`

---

## `Q124` — The distance to the Godot guide, read as three collaborators' first day

**Status.** Open. `P5-20`–`P5-27` built; `P5-28` (reopening `Q38`'s baked exposure) is the user's
call. Numbers per task in `PLAN.md` Phase 5c. A delta on `Q119` and `Q121`: every divergence those
priced and kept still stands.

- `P5-20` — `check.sh`'s `sidecars` step reads `authored/` beside `generated/`. All five committed
  authored sidecars had contradicted `[importer_defaults]`; a committed `.import` is never reseeded
  from the project.
- `P5-21` — the editor save is its own commit. A typed node export resolves from an editor-saved
  and from a hand-authored scene, provided the node line carries `node_paths=`. Seven references
  are typed exports; the two autoload ones stay `NodePath`.
- `P5-22` — `scenes/dev/asset_viewer.tscn` stands one `.glb` under the shipped rig and needs no
  built region; the driver takes `--asset=`.
- `P5-23` — the vehicle contract is material-slot names (`vehicle_paint`, `vehicle_glass`,
  `vehicle_lamp_*`), stamped into `UV` and merged into one `vehicle_body` surface by the import
  hook; `make_vehicle.py` emits the same names through a `MeshGroup` writer. A misspelt slot is
  refused by name.
- `P5-24` — `main.gd` hands the HUD its car, and each scene hands the taxi its `Sun`; no sibling
  searches the tree. `first_in` keeps one caller, the autoload `DebugHud`.
- `P5-25` — `Cmdline` (`scripts/core/cmdline.gd`) is the one command-line reader;
  `RoadGraph.shared()` is declared beside the three autoloads as the singleton that is not one.
- `P5-26` — `tuning/wrong_way.tres` and `tuning/street_tracker.tres` replace six script constants;
  `verify_hud.gd` asserts the two angle bars are 120 and 90. ⚠️ An invalid profile makes the class
  inert with the cause named: `_init` cannot refuse, and an `assert` there is walked past headless.
- `P5-27` — the eight authored binaries (6.2 MB) are Git LFS objects, tracked forward with no
  history rewrite. A clone without `git-lfs` fails `check.sh` at `verify_vehicle`.

Still true for a collaborator:

- Shader dispatch is by material name (`generated_scene_import.gd::SHADERS`), so a mesh whose
  material is called `signs` takes that shader silently. An artist reads this and `ART_DESIGN.md`'s
  anti-goals before a first export.
- Exposure is baked into `COLOR_0` at build time (`Q38`), so a lighting iteration is an ETL rebuild,
  a sync and a re-import. `TEXCOORD_1` is still a bitfield and `COLOR_0.a` a flag (`Q121` gap 2),
  which is why light baking and compression are pinned off.
- ⚠️ The four `InputRouter` signals are emitted and connected by nothing; they are the API `P2-4`'s
  touch consumers will take.
- Tooling is bash, a Python venv and `gdformat`, with CI on Linux; there is no Windows path.

Refused: a feature-folder reorganisation (moves every `ext_resource` path for no behaviour); making
`Tiles`' `../CameraRig/Camera3D` path "consistent" (it is the parent initialising a `NodePath`);
event-driven input (`Q119`); connecting the `InputRouter` signals to satisfy a grep (`Q72`).

Held, with the trigger: the HUD as a `.tscn` (a Godot developer iterating it in the editor); a
no-Python onboarding path (a licensing call — `LICENSING.md` says the data is regenerated, not
redistributed); a Windows path for `check.sh` (a Windows contributor); `P5-14` (an artist); LFS
history migration (rewrites every commit; the user's call).

**See.** `Q119` · `Q121` · `Q122` · `Q82` · `Q38` · `Q72` · `Q62`

---

## `Q125` — The opposed-pair centre line is drawn as geometry and yields to TD per metre

**Status.** Closed. The shader's `draw_pair_join` stays off; the join shrank under `Q129`/`Q132`.

- `surface.py` publishes `opposed_pairs` (`[a, b, gap_m]` per mutual pair). `roadmarks.py` walks the
  line midway between the two centrelines per station, cuts every stretch a drawn `RM1001` covers,
  and draws the rest as the `marks:` entry `opposed_join_mark` names (TD's 150/100 double white). A
  region draws none by leaving the key out. Counted apart in `roadmarks.json`'s `join` block
  (`ROADMARKS_MANIFEST_SCHEMA` 2), never folded into `drawn` / `drawn_by_id`.
- Why geometry: a per-edge shader switch is wrong on partly covered pairs (24 of 95 pair ends;
  13 fully covered, 58 not at all). `centre_step` is a flat per-strip code, `COLOR_0.a` is taken,
  the shader line is 28 cm against the survey's 15 cm. 🚫 A flat varying per station: the
  provoking-vertex convention differs between the Mobile and Compatibility renderers.
- No new knob. Covered = a surveyed line within half the pair's own `gap_m` and within
  `bearing_tolerance_deg` of parallel. A run shorter than the mark's `line_width_m` is refused.
  Search bound is `_opposed_gaps`' own; `Q72`'s free radius stays refused.
- The pairing reach gains one kerb width (0.5 m, the bar `_paint_flanks` used): two ribbons closer
  than a kerb are one surface with a seam. Swept flat at +0.25 / +0.50 (54 pairs); `one_sided`
  climbs 7 → 18 by +4.0. It widens what is found, never what the codec draws: `centre_step`'s
  `steps < 8 * lanes` guard refuses the added pairs (`opposed_pairs_unpublishable` 5 → 13).
  Example: EXPO DRIVE EAST `e656`/`e657`, gap 10.485 m.
- ⚠️ `over_refused_survey_m` grades and never gates: the inferred line standing in for a surveyed
  one this stage refused. A rise is a finding about the survey's placement.
- ⚠️ `opposed_pair_bearing_deg` is not on a plateau (pairs 43 / 48 / 50 / 51 / 54 / 58 at
  10 / 20 / 30 / 45 / 60 / 75°).
- ⚠️ In-carriageway triangles under `paint_clearance.py --layer roadmarks` are the stacked-ribbon
  chord, not paint over void; not answered with `lift_m` (`Q92`). A void-refusal rule was built,
  read 0 pieces and was removed.
- ⚠️ `_covered` pre-filters markings by bounding box padded `0.5 * gap_m` — exact, byte-identical,
  marks stage 7.57 → 3.30 s. A build-time regression is invisible to every counter; time stages.
  🚫 Vectorising `_nearest_on` (not bit-identical, `Q118`). `polyline.plan_projections` is the
  shared kernel; `Segments._plan_distances` is deliberately left out (`hypot` vs `norm`, reaches
  `clearance.json`).
- Debit (`Q54`): the line is inferred, and a double white instructs no overtaking. At `e656`/`e657`
  it stands for a real 3–4 m median the old floor paved over. Small lateral step where surveyed
  hands over to inferred. Sourced route still open: TD surveying the rest.

**See.** `Q117` pairing · `Q118` survey and switch-off · `Q54` · `Q92` · `Q62`

---

## `Q126` — A row of arrows on a two-way edge is read by direction; `lanes_forward`

**Status.** Closed for cause A. B half closed by `Q128`/`Q130`; C and D open.

`stacked_disagreeing` arrow pairs (two surveyed arrows snapped into one lane), four causes:

| | cause | example |
|---|---|---|
| A | two-way, bracket `(2, 3)`, TPDM 3.4.2.7 struck the 3 | WAN CHAI ROAD `e50` |
| B | no measured width, so the authored count stands | STEWART ROAD `e504`/`e505` |
| C | lanes painted 2.7–2.9 m, under TPDM 4.3.9.8's 3.0 m | MATHESON STREET, HENNESSY ROAD `e120` |
| D | the width includes the tram reserve | HENNESSY ROAD `e114` |

- Rule (both `carriageway._row_reading` and `arrows._row_reading`, deliberately duplicated;
  `lanes_split_disagreement` is their diff, 0): each run across the road is a lane, the row states
  `max(forward, 1) + max(backward, 1)` with split `max(forward, 1)`. A run pointing both ways states
  no split. Tie-break keys on `(lanes, painted)` in both readers.
- ⚠️ The row is a lower bound: it only puts a count back above the narrowed bracket and inside
  `_lane_bracket(two_way=False)`. A row the width refutes is a finding (`lanes_row_over_bracket`)
  and is used in neither part — LEIGHTON ROAD `e136` went `arrows` → `authored`. 🚫 Publishing the
  painted count as a fallback: `arrows.json` grades the count against the graph.
- `lanes_forward` (`ROADGRAPH_SCHEMA` 13): `lanes` on one-way; on two-way the row's split where the
  row's count stands, half where even, `null` where odd and unsplit. A row splits only the count
  that stands; `roads._reassign` reads it after every other rule. Shader centre select is
  `U = lanes_forward` (`draw_centre_line` itself is off since `Q132`).
- No geometry or driving line moves: `RoadGraph.lane_offset` is a function of the count alone, so
  `road_graph.gd` does not read the field.
- 🔴 The marking codec is full. The shader decodes `TEXCOORD_1.x` with `floor(x + 0.5)`, exact only
  to 2²³. `MARKING_LANES_FORWARD = 2097152`, span 4, `MARKING_CODE_MAX` 8,388,607. A split over 3
  is written 0 and counted (`lanes_forward_unsaid`). The next field needs another channel. Held by
  `test_the_widest_legal_code_survives_the_shaders_decode`, `test_marking_codec_copies.py`,
  `verify_road_surface.gd`, `verify_road_graph.gd::_check_lanes_forward`.
- `tools/carriageway_margin.py` and `tools/lane_paint.py` grade an `arrows` count against TD's
  widths before 3.4.2.7 (restated, not imported).

Cause B swept (`JUNCTION_M` / `MIN_STATIONS` on scratch bundles; harness not committed — a survey
constant is not a knob, `Q72`):

- 🚫 Moving the 12 m junction guard. At 10 m LEIGHTON ROAD `e263` reads 10.57 → 15.34 m (a ray
  across the mouth, `Q57`'s over-read), two measured edges are lost, and `clearance_reconcile.py`'s
  ratchet moves.
- Two stations is clean (0 measured widths move, by construction). Shipped in `Q128` as two
  *agreeing* stations.
- B2 STEWART ROAD spans 16.7–16.8 m against TD's 16.5 m `max_m`, which may not move (`Q94`). B3
  (`e194`, `e657`): `beyond` lands in the band that publishes nothing on purpose.

Open: C (the 3.0 m bar is TD's; `Q113` swept an unsourced 2.50) and D. Mong Kok and Sha Tin
unscanned.

**See.** `Q94` · `Q114` · `Q95`/`Q96` · `Q54` (why `null`, not a guess) · `Q62`

---

## `Q127` — Reading a carriageway width where the ray survey cannot

**Status.** Closed — measurement only, nothing shipped. Its cascade shipped as `Q128`.

The survey drops stations within `JUNCTION_M` 12 m of any node and needs `MIN_STATIONS` 3 at 4 m,
so an edge needs ~34 m. Under 10 m nothing reaches. Tools: `tools/carriageway_margin.py` (last
section), `tools/width_evidence.py` (`--agree-m`, `--max-ray-m`). Config
`carriageway_survey.lane_lines` is grader-only.

- 🚫 Junction-opening gate on the ray survey (drop a station only where a side street's opening
  `width_m / 2 + R` reaches it): loses and moves already-measured widths at every R 0–8 and angle
  10–60° (R 0: 10 lost, 25 moved > 0.5 m). Kept near-node stations read > 0.5 m off their median
  on 47–67% against 29.4% mid-block. `e263`'s over-read is a foreign node's (`foreign_node_m`).
- Readings graded against the survey-measured edges, one-way apart from two-way, Wan Chai |p90|:

| reading | one-way | two-way | verdict |
|---|---|---|---|
| authored `lanes x 3.2` (pooled) | 4.14 | — | the bar; reads narrow, p50 −0.83 |
| stop line length | 6.07 | 8.04 | 🚫 refuted |
| lane-line pitch × lanes seen | 10.88 | 4.64 | 🚫 sees the other carriageway (`P3-35g4`) |
| turn-arrow pitch × abreast | 3.47 | — | weak, lower bound |
| HyD area / length | 3.62 | 1.28 | a junction flare inflates it |
| HyD strip through centre, clear of openings | 2.96 | 0.85 | best single reading |
| street borrow (leave-one-out) | 3.74 | 2.90 | 🚫 |

- 🚫 As bounds: lamp posts (17.1% wrong), sign poles (27.7%), railings (49.3%), stop line (56.0%),
  lane lines (27.9%). Building frontage is usable but loose (0.5%).
- ⚠️ The ray survey may never be a confirming voter: on a reference edge it is the reference.
- ⚠️ The reference is long by construction (min 34.5 m); unmeasured edges run p50 24 m, and every
  reading is worse there. Only a confirmed reading beats the authored width on short edges in both
  regions: HyD strip + another within 1 m, short-end |p90| 1.2–1.6 m against 4.6 / 3.7. The
  unconfirmed strip is no better on Wan Chai (4.70 against 4.56).
- Tolerance is a trade curve, not a plateau: 0.75 / 1.23 / 1.58 m at 11.3 / 21.8 / 34.9% reach for
  0.5 / 1.0 / 2.0 m.

**See.** `Q126` · `Q95` · `Q94` · `Q19` · `Q57` · `Q58`

---

## `Q128` — Two agreeing stations, and a strip of HyD's paint where no ray reaches

**Status.** Closed — shipped, `ROADGRAPH_SCHEMA` 14. Coverage 39.5% → 53.5% Wan Chai, 34.2% → 63.3%
Causeway Bay, 0 measured widths moved or lost.

User's calls: coverage first, floor re-priced not removed; confirmed readings only.

- Voters are `borrow + arrows`, fixed by the import graph (`arrows` → `roads` → `carriageway`).
  Dropping the stop line improved the cascade (pooled / short 1.23 / 1.56 → 0.95 / 1.32). The ray
  survey may never join. A row's name carries its roster.
- Two-station licence: the tolerance is derived, never config — the region's own mid-block
  leave-one-out p90 (2.81 m Wan Chai, 2.91 Causeway Bay), read over edges the bounds admit, not the
  edges `_license` attributed (that reads 2.13 m). Strictly additive by construction: three-station
  edges are assigned first; `_assign` takes no tolerance. `tools/carriageway_margin.py` moved with
  it (`shipped_rows`).
- 🚫 The deck bar stays at three stations: `_deck_width_or_none` reduces with
  `DECK_WIDTH_PERCENTILE`, and a p10 of `[8.0, 12.0]` is 8.4 — one lucky ray. Reachable on `e729`,
  `e731`.
- HyD strip, `pipeline/carriageway_area.py`: corridor rastered 1.0 × 0.25 m, each cell to the
  nearest centreline with its foot inside that edge, width = the unbroken owned run through the
  centre column. ⚠️ The widest run in the row reads the service road beyond an island.
- 🔴 The confirmation is the licence: the strip alone is |p90| 2.53 m, 4.69 on short edges.
  `confirm_within_m` (1.0) is config because it is a trade curve; omit the key and no strip
  publishes. `_confirmed` asserts a ray-licensed edge is never offered a strip, so the opening
  filter used here is not `Q127`'s refuted gate.
- `width_source` gains a fifth value with `width_confirmed_by`; `verify_road_graph.gd` refuses a
  strip with no confirmation and a confirmation on any other source. `carriageway_survey` has a
  closed key set. `strip_agreement_m` (|strip − ray| on ray-measured edges, p90 2.53) is recorded,
  never gated.
- Floor priced: `tools/narrowing.py` sweeps it uniformly (0 cleared, `e207` and `e595` lost, all
  authored). Floor off the measured half only: starved 22 → 22 (lane bar), 14 → 14 (car bar), same
  fenced edges. Acted on in `Q129`.
- Build time: roads stage 10.3 → 24.1 s on Wan Chai, all the raster (`inside_polygon` 9.8 s,
  intrinsic). Not taken, each a decision: cache `gdb.read_layer` (2.15 s; `INV_PG.geojson` is
  parsed twice); skip ray-measured edges (7.2 s, costs `strip_agreement_m`). 🚫 Narrowing the
  corridor ±15 → ±8.5 m: not inert, 8 more edges publish and 10+ widths move.
- Open: reach past ~53% on Wan Chai is not bought with accuracy; next rung is consensus of ≥ 2
  within 1 m (short-end 1.90 m). Mong Kok and Sha Tin ungraded.

Reproduce: `tools/width_evidence.py --region wan_chai --voters borrow,arrows`.

**See.** `Q127` · `Q126` · `Q95` · `Q94` · `Q19` · `Q72`

---

## `Q129` — A width is the carriageway's, and most open edges are not a carriageway

**Status.** Closed — built as `P3-33b`/`c`, graded by `P3-33e`. `P3-33d` superseded by `P3-35e`;
`P3-33f` open.

User's calls: draw the carriageway region itself, the drive as judge; `shapely` approved.

Finding: on still-authored edges only 19.8% (Wan Chai) / 25.6% (Causeway Bay) of mid-block
cross-sections end kerb | kerb; the rest end in another centreline's share of the same asphalt
(control: ray-measured edges 84.3% / 93.5%). Road Network v2 draws several centrelines per
carriageway, so no tolerance or publisher can license a width there. ⚠️ Quote the mid-block column:
inside the junction guard a station ends in a share by geometry (`Q57`).

Model:

- R — the at-grade carriageway: union of HyD's Pavement Polygons, holes kept; where HyD is silent,
  rails cast per station to the line publishers' kerbs. Cut to the region's rectangle. HyD covers
  86.1% / 87.4% of level-0 length; the authored width survives on 2.0% / 2.2%.
- T_e — R cut by the Voronoi cell of edge e's centreline sampled at 1 m; foreign edges take part
  and own nothing.
- Territory span against the ray `width_m` reads |p50| 0.04 m, but it is not a second source: the
  ray's third publisher is the same polygon.

Refuted, do not re-propose:

1. Polygonising the line publishers' kerbs where HyD is silent — they do not close: 24 faces, 0.3%
   of the length (GLOUCESTER ROAD `e382`/`e383`, HKCEC). Rails, not faces.
2. R unclipped — 6.8% orphan territory, one piece 228.6 m from its owner. Clipped 0.9%.
3. Borrowing width from the through-neighbour — leave-one-out |p90| 3.23 m.

⚠️ GEOS: a self-touching Voronoi cell is repaired with `make_valid`, never dropped; the cells are
not a valid coverage, so `coverage_union_all` raises. Left and right were once swapped with every
table unmoved; `test_left_is_left_of_travel` holds it.

Not decided here: 🚫 `width_m` does not move — a territory is a share (`Q57`); lanes, arrow snap
and `e99`'s carve prism keep `Q128`'s five sources. 🚫 Levels ±1 keep their ribbons (`Q103`,
`Q107`).

Reproduce: `tools/carriageway_region.py --region wan_chai` (`--svg out.svg --window 150 0 450 250`
for HKCEC). Cameras (`city_preview.tscn --seconds=1 --shots=0.8 --debug-view=off --hud=off`):
`hkcec` `--camera=235,45,265 --look=235,0,195` · `street` `--camera=270,5.5,691 --look=30,4.5,719`.

### `P3-33b` — the `region` stage

- `pipeline/region.py`, between `carve` and `surface`, writes `carriageway_region.json`
  (`REGION_SCHEMA` now 4; ~11 MB on Wan Chai, under `etl/out/`, not bundled). Config
  `carriageway_region: {sample_m, rail_m, station_m, …}` are resolutions; the rails' cap and
  refusal are `carriageway_survey.width_bounds`' `max_m` / `hard_min_m`, so region and ray survey
  share one bar.
- Extents are per station at `station_m` 2.0 with `vertex_station` indexing `roadgraph.json`'s
  numbering — per published vertex described a wedge, since a straight street is two vertices at
  nodes. An end vertex is measured half a sample in from its node.
- ⚠️ The stage's `ends` block runs over every station and is not the mid-block finding.
- `|stage − tool|` (max 0.025 / 0.014 m²) is why the stage and `tools/carriageway_region.py` stay
  two implementations. It found: silence is asked of the publisher's union, never the clipped one,
  and a station on the publisher's edge is covered (`intersects`, not `contains`).
- `join_seam.py` checks that R's two builds agree along the shared line (`P3-33e`, below).

### `P3-33c` — the level-0 road is drawn from the region, and the floor is off

- Rails: a level-0 ribbon is the same quad strip between the same trims; its rails are its
  territory's extents (`Q107`'s clamp with `exact=True`). U runs 0 → `lanes` rail to rail, so the
  codec, restriction alpha, kerb strips and `DrawnSurface` rails are unchanged.
- Areas: `R − ribbons`, constrained Delaunay as one surface, drawn `MARKING_CLASS_CAP`. Hull caps,
  stub clusters, corridors no longer run at level 0 (caps are all off-grade).
- `floor_default_m` and the 70 kph floor are 0.0 (user's call); they still set `_WIDTH`: the
  junction trim radius and the plain ribbon of a run past its rectangle.
- Seam: a run's ribbon stays its owner's whole (`Q116`) — territory rails inside the owner's
  rectangle, plain ribbon past it. All other asphalt is drawn by the region whose rectangle holds
  it, the neighbour's ribbons subtracted there.
- Schemas: `city.json` 32, `roadsurface.json` 12, region 3. Game: `RoadGraph.has_corridor` /
  `corridor_half_width_of`.

Traps, each pinned by a test:

- An inserted station's rim is assigned from the measurement; `min` is for a deck rim only
  (`e709` drew 1.2 m wide in a 6.5 m territory).
- 🔴 A share is not a corridor (`Q57`). The stage also measures kerb to kerb through every share
  (`*_kerb_m`), `surface` publishes `corridor_*`, and `clearance` and `roadmarks`' own-carriageway
  bar read that (GLOUCESTER ROAD `e390` owns 1.56 m of 25 m; the fence went 14 → 25 on the share).
- The territory is a ceiling on the painted count only: `lanes_painted`, p10 of the span clear of
  the mouths, one-sided (`Q114`'s deck rule). `lane_paint.py` divides by it; the graph's `lanes` is
  untouched.
- Station count is triangle count: stations kept by Douglas-Peucker over `(along, left, right)` at
  `rail_tolerance_m` 0.10. 🚫 Cutting areas per owner (+45k triangles for nothing).
- `carriageway[]` at a vertex inside a junction trim publishes the ribbon's width at the trim.
- `_reach` `line_merge`s territory pieces before casting (GEOS may return touching parts). Each
  edge casts against R clipped with `clip_by_rect` (18.6 → 9.4 s); `_union` keeps polygons only.
  `linalg.norm` vs `hypot` is a knife-edge at `e223`.
- 🚫 `roads.simplify_mask` for `_stations_kept` (single-channel; rails are judged jointly).

Rail shaping (from the seat: "a straight road broadened and shrank"):

- `surface_region.bridged`: a share run between two kerbed stations is held to the straight line
  between them, `min` with the measured extent. A share run reaching an edge end is left alone.
  FLEMING ROAD `e264` bulged 11.63 m into a mouth.
- `opened`: morphological opening of each rail over `rail_opening_m` (20.0, authored; sweep flat by
  20 m, not a plateau). Never widens. Four guards: a run must stand out by more than
  `kerb_width_m`; only stations clear of both mouths take part; a bay needs a quarter-window of
  kept rail either side; a side let go of its kerb stops being a kerb. 🚫 Inward classes are left —
  closing a pinch is a widening.
- Areas carry their own kerb (`_kerb_lines`, `_draw_area_kerb`), less every stretch a ribbon's kerb
  runs beside. Codec value is a one-lane one-way kerb, never a bare class.
- `flare_m`: the junction trim read off the territory; `_assign_trims` takes `max(radius, flare)`.

Open: `lane_paint` still reads edges under 3.00 m (mouth end vertices, one-lane shares);
`paint_clearance` `deeper than` on boxes; `P3-33f`, the user's drive.

### `P3-33e` — the battery, the routing price and the seam

Before side: a worktree of `e483329`, the commit before `P3-33c`, built whole and graded by its own
tools (`battery.py --tools-from side`; this checkout's tools refuse a schema-31 bundle). It
reproduced 22 / 26 / 6 and 6 / 7 / 1 exactly. Two values are `wan_chai` / `causeway_bay`.

- **The grader walks the corridor.** `carriageway_occupancy.py` walks twice: the ribbon for the
  area half (ribbons tile, so cells sum to an area) and kerb to kerb for the corridor half
  (`survey_both`). Corridors of centrelines sharing a carriageway overlap, so that walk's areas are
  dropped. `clearance_reconcile.py` takes the corridor walk alone.
- 🔴 **`city.json` shipped half a corridor.** It carried `corridor_half_width_m` without
  `corridor_offset_m`, and the corridor sits 0.91 m off the centreline at p50, 7.71 m at worst —
  `Q106` again, invisible to the pipeline because `clearance.py` reads `roadsurface.json`. Now
  published as a pair; additive, no bump (the game compares widths). `_lib.ribbon.corridors` refuses
  a bundle with one and not the other.
- Two rules the corridor needed and the ribbon never did. **Tapered between vertices**, as
  `clearance.py` walks it: `e751` runs 22.5 m → 6.4 m in 9.5 m and the wide end's window read
  21.04 m clear where the pipeline reads 0.75 m. **An undrawn corridor cell stands at its own
  ribbon's height**: R is plan-only, so a corridor holds a ramp rising alongside; dropped, those
  cells tripped `_trimmed` and `e402` lost the 28 stations a deck walls to 2.75 m. Only where the
  station's own ribbon is drawn, so a junction trim is still refused.
- Ratchet: 22 / 26 / 6 → **28 / 32 / 8**, 6 / 7 / 1 → **9 / 13 / 4**; at grade 25 / 27 / 6 and
  8 / 11 / 3. Across the share the grader had read 64 / 17. At the pipeline's 0.50 m cell it reads
  24 against 28 and 10 against 9 — `Q51`'s gap at `Q51`'s size, which is the proof of one corridor.
- Occupancy at grade, `BUILDING` / `INFRASTRUCTURE` share of all drawn: 1.184% / 0.986% →
  **0.214% / 0.560%**; 2.444% / 0.480% → **0.309% / 0.338%**. Causeway Bay failed the 1.72% bar
  before and passes. Drawn level-0 area 500,610 → 337,143 m² and 134,393 → 90,266 m²: the invented
  floor was a third of the road. The corridor gate still fails (27 / 11 edges), as it did (21 / 5).
- 🔴 **The routing price is at the one-lane bar, and it is 3,989 ordered pairs.** Starved at 3.20 m
  19 → 25 at grade on Wan Chai (+11 −5): refusing them lost 0 pairs before and loses 2.17% now, with
  7,052 surviving pairs detouring past 200 m (p90 676 m, max 1,875 m). Three edges carry it —
  `e53` CANAL ROAD WEST 2.67 m (2,479 pairs), `e138` FLEMING ROAD 3.00 m (1,632), `e384`
  GLOUCESTER ROAD 3.05 m (10) — and `e53`, `e384`, `e412`, `e187`, `e632` have nothing standing in
  them: the kerb-to-kerb corridor is under `lane_width_m` where the floor used to draw 10.24 m.
  Causeway Bay went the other way, 455 → 173. At the CAR's 1.80 m bar nothing moved: 14 → 14
  and 3 → 3 starved, 0 and 170 pairs lost on both sides, and Wan Chai's 55.8 m detour is gone. So the player is unharmed and `P3-3`'s
  traffic inherits the question — whether `is_routable`'s bar is a lane or a vehicle. Not decided
  here.
- `narrowing.py`: the floor sweep is inert at level 0 (every column identical), as it must be with
  the floor off. `e207` 3.25 → 2.00 m and `e595` 3.50 → 1.50 m — both authored widths, both now
  under the bar at every floor; `e132` and `e499` left the pipeline's list and are grader-only.
- Registration collapsed toward zero, which was the test: signs `shift_m` p50 1.74 → 0.00 /
  1.97 → 0.09 m (drawn 670 → 873 / 185 → 285), lamps 1.38 → 0.00 / 1.23 → 0.00 m (890 → 1,077 /
  331 → 364), railings to-source p50 1.44 → 0.22 / 1.32 → 0.21 m. Not a registration finding.
- `cap_pavement.py` has no level-0 population left ("publishes no level-0 caps"). Before: 11,400 m²
  (15.3%) / 2,422 m² (14.6%) of cap past a HyD kerb; the areas are HyD's own polygons.
- Seam: `join_seam.py` sections each build's R along the shared line and diffs the stretches: 8
  roads, 64.62 m each side, **0.00 m** disagreement. Mutation-checked by a kerb stepping 1.5 m.
  ⚠️ Both builds are sectioned on ONE city-frame line: `city_offset` is whole metres, so Wan Chai's
  east edge stands 0.62 m inside Causeway Bay, and an inset per side read every oblique crossing
  0.5 m apart. ⚠️ Open and unmeasured: both rectangles hold that 0.62 m strip, so wherever both
  draw it as AREA (a ribbon has one owner) the asphalt is coplanar twice — 40 m² at most.
- Cost: the second walk takes the grader's walking from 15.5 s to ~40 s on Wan Chai (corridor cells
  1.47× the ribbon's). Reusing the ribbon's cells for the 58 off-grade edges would save 5% and change
  44 results, since the taper reaches them too. ⚠️ Open: `Faces.heights_at` is 15.75 µs of numpy
  overhead a call over 9,161 distinct grid cells; batching it per cell is what would pay for it.
- Fence: mouths 16 → 15 on Wan Chai, Causeway Bay unchanged. Deck error p90 0.094 m; `overhang.py`
  level 1 4.8% → 5.0% / 25.1% → 25.3% (`P3-35g1`'s slide, `Q116`'s far halves).

**See.** `Q128` · `Q127` · `Q95` · `Q94` · `Q57` · `Q116` · `Q104`, `Q117`, `Q125` · `PLAN.md`
`P3-33`

## `Q130` — A row of arrows sets the count on an unmeasured width; arrows stand in the drawn lanes

**Status.** Closed — `ROADGRAPH_SCHEMA` 15. `Ribbon.kerb_target`'s frame defect closed by `P3-35d`.

- `carriageway._raise_unmeasured_with_rows`: on a level-0 edge with no licensed width, a row of at
  least `_ROW_MIN` arrows abreast raises the authored count, never lowers it. Published as
  `lanes_source: arrows_unmeasured`, kept in `CarriagewayReport.lanes_unmeasured` so every bracket
  counter is untouched. `width_m` stays authored; `verify_road_graph.gd` requires that, both ways.
  6 Wan Chai edges (`e657` EXPO DRIVE EAST, `e504`/`e505` STEWART ROAD, `e137`, `e333`, `e615`).
- ⚠️ Licensing `e657`'s width would not fix it: 13.49 m brackets to `(4, 4)`; the road is three
  lanes plus a hatched strip. 🚫 The unresolved band (`Q95`) is not reopened.
- `arrows._slot_offset`: the slot is found in the surveyed frame (`_lane_of`, `Q96`) and drawn
  about the ribbon's middle (`Ribbon.offset_at`), since level-0 ribbons sit up to 6.49 m off their
  centreline after `P3-33c` (288 of 734 over 1 m). `outside_drawn_ribbon` is asked in the drawn
  frame.
- ⚠️ The slot count stays `lanes`, not `lanes_painted`: 107 arrow-carrying edges paint fewer lanes
  than they have, and slotting into the painted count would stack arrows. `e333` and `e504` publish
  three and paint two.

**See.** `Q94` · `Q95` · `Q96` · `Q106`/`Q107` · `Q129`

---

## `Q131` — A kerb in the road is not the road's edge: seams, islands, lines across

**Status.** Closed — region schema 4. Open items below.

A cross-section stops at the first kerb, so a refuge ring, a HyD tile seam or a line carried across
a mouth pinched the rail (example: EXPO DRIVE EAST `e659`, ring `k1333`).

- `region._closed`, `carriageway_region.seam_m` 0.10: HyD's union is closed (dilate, erode,
  mitred) before anything reads it. On a plateau: Wan Chai adds 5.3 / 7.0 / 8.9 m² at 0.05 / 0.10 /
  0.15, then 17.6 at 0.25 and 161 at 0.40. 🚫 Not raised to clear a pinch.
- `region.islands_of`, `_through`: a kerbed island (HyD hole, or a closed kerb ring no other kerb
  line touches) is read through — in the rails only where a kerb stands behind it inside `max_m`;
  in `measure` only where the ray comes out in its own territory (a median's nose stays a kerb).
  An island is shorter than `rail_opening_m` and no wider than `lane_width_m`; the width bar is
  waived where a centreline runs through the ring (`e785`, `e124`). 🚫 An area cap: at 40 m²
  Causeway Bay's platform strips qualified and R grew 282 m².
- ⚠️ The corridor (`left_kerb_m` / `right_kerb_m`) still stops at an island.
- Across refusal in `rails`: a hit is refused where its line reaches this centreline nearer, along
  the road, than the hit stands off it. No angle declared. Main effect: stub streets that read the
  main road's kerb at long range (`e635`, `e744`, `e315`) now take the authored half-width, so
  `silent_m[0]` rose and the fence gained `e315`, `e744` (`reachability.py --refuse`: 0 routes
  lost).
- `surface_region`: a ribbon runs under an island; each is ringed (riser only) and topped with one
  slab (`island_tops`). `region.islands` is published.
- `tools/carriageway_region.py` restates all three (island finder by swept rectangle; `crosses` /
  `within` for the waiver). ⚠️ `unary_union` over the slivers filled HyD's holes (+9,010 m²,
  silently); use a pairwise union.
- The inward-dip heuristic that located the classes is not monotone and does not grade the fix.

Open:

- Single stations where HyD's polygon touches the centreline near a node (`e37` is drawn; `e125`,
  `e426` are inside the trim). 🚫 A one-station dip filter: it is a closing, which `opened` refuses,
  and a dip is what a short island looks like.
- At `e785` one `RM1021` arrow stands half under the slab (the lane snap put it there).
- ⚠️ An earlier note called `e124` "`Q19` candidate 1, refuted". `Q19` measured a centreline shift
  only against edges with a building in the corridor (0 cleared); it says nothing else.

**See.** `Q129` · `Q57` · `Q95` · `Q19`

---

## `Q132` — The longitudinal lines come from TD's survey; where TD is silent nothing is drawn

**Status.** Closed — built as `P3-34b`–`d`, `CITY_SCHEMA` 33. `draw_centre_line` and
`draw_lane_lines` off.

Decided (user's call): TD's codes are the source of truth; no inferred fallback. The shader's
`draw_centre_line` painted `RM1001`'s shape down every even two-way ribbon from no survey.

- Where TD surveys the divider it is broken on 80–90% of it (`RM1104` WARNING LINE, 4000 mark /
  2000 gap), so a double continuous line is the wrong instruction.
- Where TD is silent there is no marking within 1.5 m of the middle on 94% / 84% of stations; these
  are surveyed streets (JARDINE'S CRESCENT carries only `RM1040`/`RM1041`). Where the middle is
  occupied it is hatching, boxes or zigzags an inferred line would run through. No main two-way
  road is missing its divider.
- ⚠️ A code absent from one layer is not absent from the geodatabase: `RM1002`/`RM1003` are in
  `DTAD_RD_MARK_LINE_C`, not `DTAD_RD_MARK_LINE`.
- `RM1101`+ is a second sheet, `CT174/51-5(2)G`; rows live in `DATA_SOURCES.md` only. `RM1107` is
  the lay-by / bus-stop edge line, not a lane line. TD publishes whole runs, so the dash phase is
  this project's, starting at each part's first vertex.
- `RM1002`/`RM1003` LEFT / RIGHT are of the digitised direction (`RULEID` 2 / 3, ArcGIS
  representation rules). ⚠️ A part TD digitised backwards is invisible to every counter; no Street
  View site has been checked.

### Built — `P3-34b`-`d`, schema 33

- Lane lines and centre family land together (the region is 93.5% one-way; drawing `RM1104` while
  the shader dashed would draw every lane line twice). TD surveys a longitudinal line on 65.7% /
  67.8% of `lanes >= 2` stations; JAFFE ROAD (986 m) has none and draws none.
- Rows: `lane_line` (`RM1101`), `warning_line` (`RM1104`), `double_white_left_broken` /
  `right_broken`, `centre_line` (`RM1103`), via `more_layers`. Longitudinal metres drawn 3,764 →
  30,828 Wan Chai, 1,608 → 6,910 Causeway Bay; `roadmarks.glb` 1.0 → 2.9 MB, one mesh.
- Host fix: `_host` prefers a candidate the line lies on (within that candidate's drawn half-width
  and `bearing_tolerance_deg`), falling back to the old angle pick, which
  `_on_its_own_carriageway` still refuses. Angle alone had lost 44 of 143 `RM1001`.
- ⚠️ `slivers_dropped` is large (a 100 mm line is 2× the 0.050 m lattice bar), 0.41% of paint
  area. `height_spread_m`'s tail is a long line on a hill, not a burial.
- `lane_paint.py`'s question moved: the shader's lane strips now place only the bus-lane line and
  the kerbside yellows.
- Zigzags are still drawn by nobody; hatching shipped as `P3-35g3`.

**See.** `Q118` · `Q125` · `Q54` · `Q131`

## `Q133` — The ETL is refactored, not rewritten; the drawn road gets one reader

**Status.** Closed — decided; `P3-35a`–`h` built below, `P3-35g4` refused.

Decided: no rewrite, no new source; a refactor in `PLAN.md` `P3-35`'s order, centred on one reader
of the drawn road. Signal layer removed on the user's call.

- Why not a rewrite: the bulk is rationale (`hong_kong.yaml` 73% comment); the code records defects
  that render as a plausible road under a green `check.sh`; 26% of tests name a private, many of
  them `CLAUDE.md` ratchets.
- Why not another source: HyD is silent on ~2% of level-0 length; no lane-count attribute exists in
  3,810 packages (`Q57`). The binding limit is one `width_m`, `lanes` and `offset_m` per edge.
  🚫 OpenStreetMap is unevaluated and not proposed: ODbL share-alike meets hard rule 7; the user's
  decision only.
- 🚫 A schema library for `config.py`; merging the four `_register`s (`Q78`, `Q115`); moving the
  YAML's prose to sidecars.
- Open: an edge whose `vertex_station` mismatches falls back silently (counted since `P3-35c`);
  nothing checks the age of a build a battery side points at.

**See.** `PLAN.md` `P3-35` · `Q106`/`Q130` · `Q129` · `Q76`/`Q77`

### Built — `P3-35a`, the signal layer removed

`pipeline/signals.py`, its tests, `verify_signals.gd`, `tuning/signals.tres` and the config block
removed; `city.json` 33 → 34 (an asset key taken away). Code is at the commit before; `Q76`/`Q77`
are the record. Its return is a port to library + placements (`P5-2`), not a re-declared block.
`signs.disc`, `facing_from_side`, `plate_frame` stay public. ⚠️ `verify_join` fails against a stale
`etl/out/wan_chai+causeway_bay/`; run `python -m pipeline.join`.

### Built — `P3-35b`, the battery as a table

`tools/battery.py <trigger> --region <r> --before <root>`; outputs and diffs under
`build/battery/`. Exit code means every item ran, not that nothing moved. Both sides are graded by
this checkout's tools; `--tools-from side` for a moved schema. 🔴 A tool given `--region` alone
reads this checkout's `etl/out` on both sides and diffs empty (`narrowing.py` did);
`test_every_tool_is_pointed_at_its_own_side` is the ratchet. `--jobs` is safe: no grader writes
without `--json` / `--svg`. `generated_utc` is rewritten to `<built>`. Not in the table: a frame, a
drive, a sweep, the skidpad.

### Built — `P3-35c`, the shipped path gets an end-to-end test

`tests/test_surface_on_region.py` (`regionville`): runs `region.build`, writes the document through
`_document`, builds `surface`, and reads truth back off the mesh. ⚠️ With `_shape`'s `exact=` off
only the mesh read fails — `carriageway[]` is written from the territory whatever the geometry did
(`Q106`). New log-only counters `territory_mismatched_edges` and `territory_missing_edges`, 0 / 0
on both regions. `test_surface.py` still drives the region-less path.

### Built — `P3-35d` (1)–(2): one reader; signs and lamps on the road's kerb

`pipeline/drawnroad.py` holds `nearside`, `Ribbon`, `ribbons`; `kerb_target` and `past_kerb_m` read
the road, not `±half` about the centreline. Extent chosen by grading iB1000 lamp posts (they stand
just outside the kerb) — posts reading as in the road, Wan Chai / Causeway Bay:

| extent | in the road |
|---|---|
| `±half` about the centreline | 21.8% / 14.5% |
| 🚫 `roadsurface.json` per-vertex `corridor_*` | 24.2% / 8.7% |
| region's dense kerb stations, raw | 14.9% / 4.1% |
| shipped: each side at kerb-ended stations, line between | 13.3% / 3.6% |

- 🚫 Per-vertex `corridor_*` made signs worse (`shift_m` p90 1.34 → 4.24 m, over-shift 2 → 43): a
  straight street's two vertices stand in junction mouths. 🚫 The share's rail (`Q57`): a post
  hosted by an inner share would register to the middle of the asphalt.
- Result: signs `shift_m` p90 1.34 → 0.54 / 1.15 → 0.45, lamps 1.48 → 0.93 / 0.80 → 0.26; refused
  in carriageway 19 → 5 / 6 → 1. ⚠️ p99 rises (signs 3.80 → 7.83): posts surveyed deep inside a
  wide road are now measured against the real kerb and refused. `target_m` stays in the
  centreline's frame.
- ⚠️ 259 of Wan Chai's 1,468 territory sides have no kerbed station and register against the
  16.5 m ray cap — `drawnroad`'s to answer.
- Owed: the lamp-post grader as a `tools/` instrument. ⚠️ An A/B made by swapping only a placements
  JSON gave one hash for both sides; not evidence.

### Built — `P3-35d` (3) fence; (4) railings priced and left

`fence._ribbon_at_end` reads `(half, offset)` and `_dress` centres the row on the ribbon.
🔴 `offset_m` is positive to the nearside of the published direction, and the row's tangent points
into the street, so the sign reverses at an end mouth; pinned against `surface.mitres` at both
mouths. Counters unchanged; KA NING PATH `e45` moved 2.41 m. Railings priced here, built below.

### Built — `P3-35e`, the ungated stations

`_add_paint_stations` gated on `region is None` like its only consumer. Road 93,015 → 92,647
triangles on Wan Chai; box paint triangles fell with every painted area unchanged.

### Built — `P3-35e`, second half: the flanks deleted

`_paint_flanks`, `_add_paint_stations`, eleven helpers, the manifest's `paint` block and
`build_region`'s `sources_root` deleted (`surface.py` 5,088 → 4,628). Inert on both regions, no
schema bump. 🔴 Cost: a region-less bundle (tests only) draws nothing under a box overhanging its
ribbon. `Q104`'s lessons stand. Caps, clusters, corridors and buried kerbs stay — off-grade edges
draw with them. `_opposed_gaps` → territory adjacency is out of scope (owes `Q117`/`Q125`'s
proofs).

### Built — `P3-35d` (4): railings on the road's running kerb line

`railings.ribbons` takes `drawnroad.kerbed_ribbons`, stationed at published vertices and the
region's dense kerb stations. Three rules, each with its own mutation test:

- where — `near + outset` and `off − outset` from `Ribbon.kerb_at`, never `±(half + outset)`;
- which side — the nearer kerb about the road's middle (`SideIndex`'s side is about the
  centreline);
- facing — toward `Ribbon.middle`.

Inert with the road forced symmetric. `shift_m` p50 0.54 → 0.14 / 0.48 → 0.12; `railing_error.py`
to-source p50 0.46 → 0.22 / 0.45 → 0.21 (it never read `±half`; it measures steel against TD's
lines). ⚠️ `bends` 32 → 84 / 10 → 27. 🚫 "Panels standing in the road against the kerb line" is
not re-quoted: the fence is built from that line, so it reads 0 by construction (`Q58`).

### Built — `P3-35f`: the three moves, and every block's key set closed

- `pipeline/drawnsurface.py` — `DrawnSurface`, `DrawnHeight`, crease cutting (`surface.py` →
  3,953 lines).
- `tools/_lib/{bundle,ribbon,streets}.py` — what tools imported sideways from `deck_error`,
  `overhang`, `carriageway_occupancy`. ⚠️ Proving a tools move needs `--tools-from side` against a
  worktree of the commit before; both sides on this checkout proves only that they run.
- `pipeline/config_blocks/` — assigned by reach. `config.py` (1,153 lines) stays a file and
  re-exports every name (`Path(__file__)` roots, `from pipeline.config import _private` in tests).
- Closed keys: `_Read` records which keys a parser asked for and `load_config` refuses the rest
  (1,033 of 1,033). ⚠️ Iterating a mapping reads all of it, so this is a floor under the per-block
  checks. 🚫 Routing `_measures` blocks through `_thresholds` (they hold roles and optional keys).

### Planned — `P3-35g` priced into four tasks

- `g1` off-grade: the drawn offset is already per station (`Q107`); only the clamp's `shift` is per
  edge.
- `g2` crossings: of `Q101`'s five publishers only `DTAD_CROSSING_LINE` publishes crossing paint.
  ⚠️ Road Network v2's `TRAFFIC_FEATURES` reads one zebra point against 121 crossings.
- `g3` hatching: in scope on the user's call (2026-09-20), lifting `Q65`'s scope refusal for
  `RM1035`–`RM1037`.
- `g4` lane-line count: `Q127`'s refuted reading, planned as a grader-only probe.
- `P3-35d5`: two of railings (4)'s "costs" were one defect. `P3-35h`: its own task.

### Built — `P3-35d5`: two stations at one place, and a fence line that is not a polygon

- `railings._own_places`: a kerb station within `min_station_gap_m` of a published vertex or the
  previous kerb station is dropped; the vertex wins. (`np.union1d` left a 0.000217 m step at
  Causeway Bay `e10`, and `surface.boundary`'s backward test pinned six stations on one point.)
- `_sides` takes the plain offset, not `surface.boundary`'s — deliberately not inert on a symmetric
  road. `boundary` pins the inside rail past a corner because a polygon must not cross itself; a
  fence is a line stood on by station. `surface.boundary` is untouched.
- Causeway Bay to-source max 5.53 → 3.07 m. Cost: Wan Chai's widest joint wedge 41 → 52 mm.
- 🚫 `bends` is the kerb's roughness: Douglas-Peucker made it worse (91) and a moving average gave
  back a third of the registration. The mitre stays `Q115`'s open point.
- ⚠️ Tall coloured spikes in `city_preview.tscn` frames are `fare_preview.gd`'s pins
  (`pin_height_m`), a dev tool, never in `city_drive`.

### Built — `P3-35g1`: the off-grade ribbon slides onto its deck before it is cut

`surface._slid_onto_deck`, ahead of `_clamped_rails` at the two off-grade call sites; a territory
never reads the shift. Where the ribbon hangs off one rim, the shift is carried back by the
overhang; the clamp still only cuts. Published `offset_m` stays the intent.

- 🚫 Not what `Q103` refused (an offset sourced from the deck's middle); this never reads the
  middle. Three refusals, no knob: an `inf` rim, a ribbon wholly off its deck, and a deck that
  would hold the ribbon twice (somebody else's too; slides 238 / 258 / 274 / 302 at 1.25× / 1.5× /
  2× / 3×, no cliff). The `measured` guard protects the count.
- Wan Chai: 274 slid / 28 refused; stations under the 3.20 m lane bar 5 → 0; `e364` median drawn
  4.31 → 6.80 m, corridor 1.34 → 1.94 m (still starved). 0 level-0 rows moved, 0 stations narrower.
- Cost: ~12% of newly drawn area hangs (rims are per published vertex). `clearance_reconcile` was
  already failing (`P3-33e`) and reads the same; Causeway Bay's `overhang.py` gate fails at 25.3%
  as at 25.1% (`Q116`).
- ⚠️ `etl/out/wan_chai+causeway_bay` must be rebuilt (`python -m pipeline.join`) or `verify_join`
  fails. Camera: `--camera=1575,40,425 --look=1625,12,455` (`e364`).

### Built — `P3-35g2`: pedestrian crossings

`pipeline/crossings.py` after `boxjunctions`; `crossings.glb`, `crossings.json`; `CITY_SCHEMA` 35.
Placement is `boxjunctions._place`, imported.

- A stripe is a face: each feature is polygonised (many stripes are surveyed as four loose edges);
  line enclosing nothing is refused and counted. Safe only because the survey never draws a ladder:
  `faces_touching` is published and must be 0. `unclosed_m` uses the union of face boundaries.
- 🔴 Colour is not published (`LINETYPE` separates nothing). From `CT174/51-5(1)F`: `RM1070` zebra
  white, `RM1076` light-signal yellow. A zebra always has zigzags and TD surveys them (`ZIGZAGL` /
  `ZIGZAGR` in `DTAD_RD_MARK_LINE_C`): the nearest zigzag is 0.33 m from one Causeway Bay
  crossing and 481.85 m from the next. `zebra.within_m` 10.0 sits on that plateau;
  `zigzag_gap_m` publishes both sides.
- Line-type whitelist read off four regions (Mong Kok `ZEBRA4`; Sha Tin `CROSS_ANNO`, `RM1077`),
  exact, refusals counted by code.
- Wan Chai 120 of 121 drawn, 758 stripes; Causeway Bay 16 of 19, one zebra. PCK +222,660 B
  (+0.364%); draws 107 → 109. `vertices_over_void` is registration, not scaled (`Q54`).
- Use `region._box_sides`, never `minimum_rotated_rectangle` (divides by zero on an axis-aligned
  ring). 🚫 `_is_convex` is not merged with `boxjunctions._turns_one_way` (sound for a quad only).
- The two paints ride `boxjunctions.tres` and `roadmarks.tres`; `verify_crossings.gd` holds the
  pairing.
- Not built: look-right / look-left glyphs (`1135` / `1136`), the footway-extent publishers
  (`P3-27`), `RM1071` give-way line, zigzags.

### Built — `P3-35g3`: hatching, a third host axis, a chevron told by its shape

Two `marks:` rows (`hatched_island`, `prohibitory_chevron`), no new stage, material or draw call;
`RM1035`–`RM1037` are all white.

- `axis: oblique`: `_host` scores on proximity with the lies-on-a-road preference; no residual, so
  `axis_residual_deg` is unchanged. Its one bar is `_on_its_own_carriageway`, published in metres
  by marking (14% refused). ⚠️ The preference only matters where the nearest centreline is a slip
  road too narrow for the stripe; that case is the test.
- `RM1035`/`RM1036` carry two widths under one code (`LINE WIDTH` 150, `CHEVRON WIDTH` 900). A
  chevron is a 3-vertex V: no 3-vertex part turns 10–30° (19 under 10°, 215 over 30°).
  `chevron_turn_deg` 20 sits in the gap; `chevron_turn_gap_deg` publishes both sides. `_apex`
  closes the V with a bevel, not a mitre.
- Drawn: hatched 2,314 / 725 m, chevrons 2,973 / 210 m. PCK +697,168 B (+1.137%).
- Debits: chevrons surveyed as two 2-vertex legs are drawn at 150 (`Q54`; ceiling 667 m on Wan
  Chai); 45% / 20% of `RM1035`/`RM1036` metres are lost to `ELEVATION`; `deep` 40 → 81 triangles,
  mostly stripe under an island slab (`Q131`). `_on_its_own_carriageway` still asks about the
  centreline and errs toward refusing.

### Measured and REFUSED — `P3-35g4`: a lane count off TD's lane lines

`tools/width_evidence.py` §2a `hosted_count`: dividers strictly inside the edge's own drawn ribbon
`[offset − half, offset + half]`, half a narrowest lane clear of each rail, plus one. Bar set before
the run: agreement in the high 80s, over-count near zero.

- Hosting fixes `Q127`'s over-count (Wan Chai `measured`: 24% → 79% agree, 84 → 15 over), but
  pooled agreement is 82% / 75%, and the prize is ten edges. `Q114` shipped against 0 of 208.
- 🚫 Sweeping the rail clearance to reach the bar (`Q72`). 🚫 Not an argument to switch
  `draw_lane_lines` on.
- Reopens only on an edge-by-edge account of the 21 / 10 disagreements that is not a knob (a row of
  arrows is a lower bound, so some "over" may be right). The instrument stays in the tool.

### Built — `P3-35h`: the game places a lane about the road that is drawn

`RoadGraph.lane_centre` is taken about the middle of the drawn road, `point + edge_left × offset`,
with `_offset_at` interpolating `carriageway_offset_m` per station. No schema moves.

- 🔴 The offset belongs to the road: `edge_left` is taken before the asker's heading reverses
  `along`. `verify_road_graph.gd` asks both ways, requires the two lane centres to straddle the
  drawn middle, and requires `offset_checked` on a region with offset ribbons.
- Readers: `road_spawn.gd` (spawn moved 0.95 m across EXPO DRIVE) and the debug overlay.
- ⚠️ A mutation that trips GDScript's unused-variable error hangs headless Godot; write mutations
  that compile and time-limit each run.
- `driver.gd`: an action is wanted while any of its `--hold`s covers `t`.
- Open: the user's own drive on `e657` with `F3` on `full`; a scripted drive showed the marker in
  the nearside lane.

## `Q134` — Paint stands where TD surveyed it: arrows off the lane slot, and the decks' paint read

**Status.** `P3-36` (arrows) and `P3-37` (deck paint) built; the user's drive of both owed. Opened by the user from the driving
seat on FLEMING ROAD, 2026-09-21: arrows off the centre of the painted lane, and no lane lines on
the bridges.

One cause under both: a placement rule outlived its reason.

- **Arrows.** `Q96`/`Q106` read TD's offset as a lane slot and redrew the arrow at the slot's centre,
  so it agreed with the equal strips `road_markings.tres` cut the ribbon into. `Q132` switched those
  strips off and drew TD's surveyed lines, so the slot centre became the position that reads as a
  fault: `lane_shift_m` p50 0.48 / p90 1.94 / max 11.15 m over Wan Chai's 741. FLEMING ROAD's row of
  three, surveyed 3.3 m apart, stood 0.82, 0.08 and 2.07 m off, across two converging hosts
  (`e531`, `e446`); `e174`'s two arrows shared one point, one moved 5.22 m.
- **Decks.** `roadmarks.py` and `arrows.py` refuse every feature whose `level` is not null, citing
  `Q13`'s closed elevated network; `Q111` opened level 1. With `draw_lane_lines` off nothing paints a
  deck. Measured on Wan Chai: 287 marks / 18,637 m refused — `A01` 107 / 3,917 m, 87% of its vertices
  over the drawn level-1 deck; `A03` 180 / 14,720 m, the bores (`Q21`). 20 arrows.

### Built — `P3-36`: an arrow stands at its surveyed position

`arrows._placed_offset`: the surveyed offset where the point is inside the host's share **or** on
the drawn level-0 road (`DrawnSurface.covers`); else the slot `_lane_of` chose, counted
`placed_by_slot` with `fallback_shift_m`.

- 🔴 The host's share is not the road (`Q57`): the arrow the task was opened over is outside
  `e446`'s 4.18 m share with `e531`'s tarmac under it. The share-only gate left it on the slot; 14 of
  the two regions' 36 `outside_drawn_ribbon` arrows stand on a neighbour's share or a cap.
- The slot stays the lane-count instrument. Byte-identical across the change, both regions: both
  partitions, `axis_residual_deg`, `offset_m`, `against_one_way`, `outside_carriageway` 31 / 5,
  `outside_drawn_ribbon` 29 / 7, `lane_shift_m`, `stacked_pairs` 44 / 7, `stacked_disagreeing`
  18 / 0, the row counters, `inverted` 0, `arrows.glb`. Only `arrows_placements.json` positions move
  (712 / 151 stands; heading, mesh and height none). No schema bump.
- New: `placed_by_slot` 16 / 6 (`fallback_shift_m` p50 2.00 / 3.75 m); `overlapping_drawn` 18 / 2 —
  pairs DRAWN within half a glyph, where `stacked_*` is now asked of the slots. Of Wan Chai's 18, 11
  are TD's own duplicate or near-duplicate rows of one code (5 exact) and drew stacked before; 5 are
  new, surveyed 1–2 m apart. Differing instructions drawn on top of each other: 18 → 2.
- `paint_clearance --layer arrows`: 2.2% of paint area buried both sides; deeper than 10 mm in the
  carriageway 38 → 31; on a raised edge 6 → 13 (arrows surveyed beside a kerb lip). Within bounds.
  Heights still come from the host's centreline.
- Mutation-checked: always-slot, no-fallback, `on_drawn_road` ignored, NaN guard dropped, the
  overlap counter reading the slot — each fails its own test.
- 🚫 Refusing the `placed_by_slot` arrows: the slot is on the host's own tarmac, and it was the
  user's call.
- Seen beside it, not this layer: `P3-35g3`'s chevrons heap at the island nose north of the row.

### Built — `P3-37`: TD's paint on the decks

`road_marks.deck_codes` / `arrows.deck_codes` `[A01]` (publisher vocabulary, so config).
`roadmarks.draw_decks` and `arrows.stand_on_decks` host a deck feature among off-grade edges only —
the nearest level-0 edge to a line on a flyover is the street under it, the guard's own reason and
still true — and stand it on `DrawnSurface.of(level=host's)`. Every bar is the street's.

| Wan Chai / Causeway Bay | candidates | drawn | refused |
|---|---|---|---|
| lines | 105 / 4 | 100 (2,497 m) / 4 (175 m) | 1 no edge, 2 off carriageway, 2 off axis / 0 |
| arrows | 20 / 4 | 18 / 4 | 2 `off_deck` / 0 |

- 🔴 The void rule is inverted on a deck, on the user's call: a piece the deck's surface does not
  cover is refused and counted (12 stations / 13.8 m; 0 on Causeway Bay), never floated. On the
  street a void piece is kept (`Q54`). Deck arrows have no slot fallback — a deck's width and
  `lanes` are authored.
- Inertness: both level-0 reports byte-identical but for mesh totals (`triangles`, `vertices`,
  `bytes`, `aabb`, `placements`); level-0 geometry is an identical prefix of `roadmarks.glb`, level-0
  stands an identical prefix of `arrows_placements.json`. `roadmarks.glb` +408,636 / +40,932 B
  (glb bytes, not a PCK figure). No schema bump: both `deck` blocks are additive.
- `paint_clearance --layer roadmarks` unchanged in code: every deck triangle finds a road face,
  buried under the lowest face 1,477 → 1,477 / 398 → 398; "more than one face" 2.0% → 10.2% is
  overlapping deck ribbons.
- Mutation-checked: hosting among every edge, no rim refusal (lines and arrows), nothing-placed
  still `drawn`, the own-carriageway bar dropped, the one-way refusal dropped.
- 🚫 `A03` and the bores (`Q21`); the inferred join off-grade (`Q125`); deck crossings and boxes;
  `draw_lane_lines`.
- ⚠️ The first deck frame was bare: Godot rendered the cached mesh until `--import`.
- Open: `sha_tin` / `mong_kok` unbuilt with it; the 5 refused lines unexamined edge by edge.
- Cost, measured: ~0.95 s on a ~27 s build — `draw_decks` 767 ms, and arrows' new level-0
  `DrawnSurface` 176 ms, 118 ms of it crease and edge indices that stage never reads. Recorded, not
  taken: lazy indices would touch `Q92`'s reader for 0.4% of the build. 🚫 Reading `_place_on_deck`'s
  coverage off `sample`'s `over_void`: it answers the POINT where the rule asks the piece's SIDE —
  0 of 13,831 corners disagree today, which is what makes the swap dangerous.

**See.** `Q96` · `Q106` · `Q132` · `Q57`/`Q129` · `Q111` · `Q103` · `.claude/rules/arrows.md`,
`roadmarks.md` · `PLAN.md` `P3-36`, `P3-37`

## `Q135` — Road paint stays mesh; what it costs a frame is measured, and it casts no shadow

**Status.** `P3-38`–`P3-42` built; the user's drive owed. Opened by the user, 2026-09-21: review `P3-36`/`P3-37` against
the asset standard, and ask again whether road paint should be mesh or texture.

### Mesh, decal or texture

- ⚠️ `mesh_contract.gd`'s texture refusal is a DEFAULT a call site overrides with a declared budget
  (`Q63`), not a hard rule — the user's correction. Texture cost is a price, not a bar.
- 🚫 **Decals, with web droppable on the user's word.** The Mobile renderer keeps a per-object list
  of 8 decals — `BeamBudget`'s limit for spots, from the engine's documentation, ⚠️ not measured on
  4.7. Wan Chai paints ~3,100 features over 65 road chunks, ~48 a chunk before a curved line is cut
  into boxes. The exits are Forward+ (the locked renderer) or ~10x the road meshes (the draw
  budget). Dropping web does not move either. Arrows are the one fit and already the cheapest layer
  (3,284 triangles, an 8 KB library). `Q115`'s held trigger stands: a Mobile-renderer test first.
- 🚫 **A region texture**: a 100 mm line over 1.5 km² at 25 mm a texel is ~60k x 40k px.
- 🚫 **Shader paint on the ribbon** is what `Q132` left: surveyed lines do not follow lane space, a
  cap has no lane coordinate, and the fade blanks where stop lines and arrows sit.
- Held: striped texture for boxes and zebras (14,931 triangles over 20 boxes). Alpha scissor
  re-aliases (`marking_paint.gdshader`); alpha-to-coverage on `gl_compatibility` is unverified.
  Trigger: distant hatching judged unacceptable from the driving seat.

### Measured — what the paint costs a frame

`drive.sh --hide-layers=` (new; refuses an unknown id, fails a run that hid nothing). Throttle route,
overlay and HUD off, both regions resident, positions identical to the centimetre:

| | `prims` t=1–6 s | `draws` |
|---|---|---|
| Shown | 900,927–1,022,097 | 107–109 |
| `roadmarks` hidden | −217,068 at every sample | −2 |
| All four paint layers hidden | −283,044 at every sample | −18 |

- Constant to the triangle while the frame swings 120k: one AABB a region, never culled inside it.
  Causeway Bay's copy costs 0 from this route, so the region AABB does cull.
- 217,068 = 3 x 72,356, `roadmarks.json`'s `triangles`: the main pass and two shadow cascades. No
  layer node set `cast_shadow`, and a `GeometryInstance3D` casts by default.
- ⚠️ `tools/resident_budget.py` sums tiles and road chunks only. Wan Chai's ~93k paint triangles are
  outside its 105%.

### Built — `P3-38`: what lies on the road casts no shadow

`GeneratedLayer.LAYERS` gains a required `casts_shadow` key — `false` for `tramway`, `arrows`,
`boxjunctions`, `crossings`, `roadmarks` — and `layer_preview.gd` applies it to every
`GeometryInstance3D` it built. In the node, not the importer: an import is cached on the `.glb`,
not on the post-import script.

- Same route, t=6 s, same position: `prims` 906,456 → 714,553 (−191,903), `draws` 108 → 98.
- A/B at `--camera=188,11,40 --look=215,5,16`, `t=0.8`, each side shot twice and byte-identical:
  21 of 2,073,600 px differ (max 32, one 16 x 8 px box on a kerb flank). `check.sh` 0, no shader
  error.
- ⚠️ A drive frame cannot A/B this: a capture waits for the next rendered frame and the car moves.
- ⚠️ Nothing for the mobile tier, which has no cascades: ~94k unculled paint triangles remained,
  31% of 300k. `P3-40` below.

### Built — `P3-39`: a street arrow's heights are the road's under its own ends

`arrows._end_heights`: `DrawnSurface.height_at` under the glyph's tail and nose, as
`stand_on_decks` reads a deck; an end over nothing drawn keeps the host centreline's height and is
counted (`ends_off_drawn_road` 14 / 4), never refused — the street's void rule is `Q54`'s.

| `paint_clearance --layer arrows` | Wan Chai | Causeway Bay |
|---|---|---|
| under the highest face | 84 → 56 | 53 → 34 |
| inside the carriageway | 54 → 28 | 47 → 27 |
| deeper than 10 mm — the bar, set beforehand | **31 → 9** | **36 → 21** |
| on a raised edge | 13 → 11 | 6 → 7 |

- ⚠️ The evaluation predicted less — "no crossfall, so only arrows on a neighbour's share or a cap
  can move". Wrong: 493 / 99 of 759 / 162 heights moved (p90 5 / 10 mm, max 0.18 / 0.23 m). A
  centreline interpolated along `t` is not the surface under a point metres off it.
- Inert: every other counter and `arrows.glb` byte-identical, both regions; no stand's plan
  position, heading or mesh moved; `pitch_deg` p99 4.06 → 4.45 / 8.77 → 8.77. No schema bump —
  the counter is additive.
- Mutation-checked: `centreline` returned unread, `covers` not asked — each fails its own test.
- Left: 9 / 21 deep. A rigid glyph over a crest or beside a kerb lip; unexamined.

### Built — `P3-40`: `roadmarks.glb` is a mesh per 300 m cell

`meshbuild.CellBuilder` routes each placed piece whole to the cell its centroid is in; one `.glb`,
a mesh a cell, so the importer makes a `MeshInstance3D` and a box per cell. `road_marks.cell_m`
300; manifest schema 3 (a v2 reader grading "the one primitive" reads one cell);
`verify_roadmarks.gd` grades every cell through `library_meshes`.

| | cells | largest | `bytes` |
|---|---|---|---|
| Wan Chai | 21 | 8,346 of 72,356 | 4,348,808 → 3,931,716 |
| Causeway Bay | 10 | 4,553 of 21,787 | 1,179,544 → 1,187,172 |

| `drive.sh`, road marks' cost (shown − hidden) | before | after | `draws` |
|---|---|---|---|
| start line, first frame / t=6 s | 72,356 a pass | 13,184 / 17,155 | +3 / +4 |
| `--spawn-fare=wan_chai/f_045`, first / t=6 s | 72,356 a pass | 16,299 / 13,459 | +7 / +5; 132 peak |

- ⚠️ Two samples a run: unattended, macOS stopped presenting and `prims` froze between them.
- Inert: the cells' triangles equal the uncut mesh's as a multiset, both regions; every report key
  but `cells`, `cell_triangles_max`, `bytes`, `schema_version` unmoved; `paint_clearance --layer
  roadmarks` buried under the lowest face 1,477 / 398, `Q134`'s figures. Level-0 stays an identical
  prefix of each cell.
- `tools/resident_budget.py` prints the paint: never streamed, so resident from every camera.
  Wan Chai's worst camera 112% → **144%** with it, Causeway Bay 82% → 90%. ⚠️ `PROGRESS.md`'s 105%
  was stale. The budget is stated in VISIBLE triangles; resident is its upper bound.
- `DrawnSurface.decks(surface)` replaces three copies of the levels-above-the-street
  comprehension (`roadmarks.py` twice, `arrows.py`); outputs byte-identical.
- 🚫 **One shared piece-placer**, which the review proposed: the arithmetic the three placers share
  — cut along the creases, sample each corner from the piece's own side — is already
  `DrawnSurface.sampled_pieces`, written so they cannot drift. What is left in each is its own
  report's counters and its own void rule; a keep-predicate plus counter callbacks adds
  indirection and removes nothing.
- 🚫 **`FlatBuilder.build` returning its sliver count**: `CellBuilder` sums over private reports and
  writes once, so boxes, crossings and every test keep the signature.
- 🚫 Streaming the cells (4 MB; the budget is visible triangles). 🚫 The 150 m tile (draws).
- Mutation-checked: keyed on the first vertex, the report handed to each cell.
- Left: boxes (14,931) and crossings (5,711) are still one box each; ~21k a pass, unculled. `P3-42` below.

### Built — `P3-41`: the other two regions carry deck paint, and a crossing of decks is counted

`mong_kok` and `sha_tin` built end to end; `inverted` 0 on both layers.

| | lines drawn | refused | `stations_off_deck` | arrows | cells |
|---|---|---|---|---|---|
| Mong Kok | 18 of 20 | 1 no edge, 1 off carriageway | 30 / 44.5 m | 0 of 0 | 19, largest 3,810 of 45,539 |
| Sha Tin | 446 of 521 | 4 no edge, 48 off carriageway, 3 off axis, 20 wholly off deck | 418 / 482.9 m | 23 of 25 (1 against a one-way, 1 off deck) | 16, largest 5,721 of 28,456 |

- 🔴 **`A01` says "on a structure" and never which; the lines carry no Z (0 of Sha Tin's 2,376
  parts).** A deck feature is hosted by the plan-nearest edge over every level above the street, so
  where two decks cross the level is a guess. New counters, additive, no schema bump:
  `roadmarks.json` `deck.under_another_deck` / `_m` — drawn markings with another level drawn over
  or under them, by segment middle — and `arrows.json` `deck.under_another_deck`.
  Sha Tin **33 markings / 324.1 m**, arrows 0 of 23; Mong Kok (levels 1 and 2), Wan Chai and
  Causeway Bay 0. One hatched island's ladder of stripes is split 11 on level 1 and 20 on level 2,
  decks 9 m apart (`e220` at 10.05 m against `e149`/`e152` at ~19 m).
- 🚫 **No rule picks the deck.** Nothing in the data says which is right, and moving paint on a
  guess is `Q54` inverted. Candidates, unbuilt: one level per source FEATURE (needs the owner
  carried on `Marking`); the level whose edge is on axis AND nearest. Sha Tin ships in no build,
  so it waits for the region or a Street View site.
- ⚠️ The arrows host by plain nearest edge, so an arrow nearer a CROSSING deck's centreline than its
  own is hosted there and refused `off_bearing` — the same ambiguity's other face; 0 in every
  built region, pinned in `test_an_arrow_where_two_decks_cross_stands_and_is_counted`'s note.
- ⚠️ Sha Tin's 48 off carriageway and 20 wholly off deck are unexamined edge by edge, as Wan
  Chai's 5 are (`Q134`).
- Inert on the shipped pair: `roadmarks.glb` byte-identical, every report key but the new two
  unmoved. Mutation-checked: the `level !=` filter dropped — three tests fail.

### Built — `P3-42`: the boxes and the crossings are a mesh per 300 m cell

`P3-40`'s "Left". `boxjunctions.py` and `crossings.py` build into `meshbuild.CellBuilder`, unchanged;
`boxjunctions.cell_m` and `crossings.cell_m` 300, a dial a block on the user's call; both manifests
schema 2. A crossing cell is named `<kind>_c<i>_r<j>` and its glTF material stays the bare kind, so
the importer's `SHADERS` is untouched and `verify_crossings.gd` reads the kind back off the NAME —
off the material, a yellow zebra checks out against itself. `verify_boxjunctions.gd` grades every
cell through `library_meshes`.

| | boxes: cells, largest | crossings: cells, largest |
|---|---|---|
| Wan Chai | 10, 7,585 of 14,931 | 14, 993 of 5,711 |
| Causeway Bay | 4, 698 of 1,318 | 4 (3 signal + 1 zebra), 248 of 534 |
| Mong Kok | 5, 2,492 of 4,082 | 19, 2,343 of 12,219 |
| Sha Tin | 6, 1,923 of 4,776 | 3, 372 of 713 |

| `drive.sh`, boxes + crossings (shown − hidden) | before | after | `draws` | peak `draws` |
|---|---|---|---|---|
| start line, t=1 s / t=6 s | 20,642 / 20,642 | 9,849 / 9,849 | +2 → +3 | 101 → 102 |
| `--spawn-fare=wan_chai/f_045`, t=1 s / t=6 s | 7,469 / 1,758 | 496 / 390 | +3 → +3 / +2 → +2 | 132 → 132 |

- The hidden runs are identical before and after to the triangle at every sample, both routes.
- ⚠️ **The boxes missed their bar.** Set beforehand: boxes ≤ 8k, crossings ≤ 2k, peak `draws` under
  the 136–150 line. At the start line the boxes read **9,411** over 2 draws — the 7,585 cell, which
  the start line is inside, and a 1,826 neighbour — and the crossings 438 over 1. Half of Wan
  Chai's box paint is in one 300 m cell, so from inside it no `cell_m` culls the rest; 600 is worse
  (9,723 in one cell). 🚫 Not answered by a smaller cell on this evidence: a draw call a cell.
- ⚠️ Two samples a run, as `P3-40`: `prims` froze from t=1 to t=5 on the start-line runs under
  `caffeinate`. The before side is the old `.glb`s swapped into the game tree and force-reimported.
- Inert, all four regions: the cells' triangles equal the uncut mesh's as a multiset per material;
  every report key but `cells`, `cell_triangles_max`, `bytes`, `schema_version` unmoved.
  `paint_clearance --layer boxjunctions` / `crossings` and `box_extent.py` byte-identical against a
  bundle holding the old meshes, both shipped regions, so its `--ray-m` sweep was not re-run.
  `check.sh` 0; no shader error.
- 🐛 Latent, fixed: `crossings.build_region` handed ONE report to both kinds' `build`, which
  ASSIGNS `slivers_dropped` — the last kind drawn overwrote the first. 0 in every region, so no
  number moved; `cell_meshes` sums a report a kind.
- ⚠️ `box_extent.py` reads **1.32 m² of 577.90 (0.23%)** of Wan Chai's box paint over nothing drawn,
  both sides, where `.claude/rules/boxjunctions.md` still quotes 6.71%. Not this task's; the rule's
  figure is stale.
- Mutation-checked: `triangles` read off the last cell, `inverted` assigned in the loop, the
  stage's report handed to each kind, the two `KIND_MATERIALS` swapped — each fails its own test.
  ⚠️ Not the `-?` in `_kind_of`: no shipped region has a negative cell, so nothing reachable moves it.
- 🚫 Signal crossings folded into the box mesh to save draws (one `.tres`, but two `lift_m` rungs and
  two verify contracts). 🚫 A whole box routed to one cell: a piece to its centroid's cell is what
  makes the union the uncut mesh.

**See.** `Q134` · `Q115` · `Q63` · `Q132` · `Q91` · `Q120`/`Q122` · `BeamBudget` · `PLAN.md` `P3-38`–`P3-42`

---

## `Q136` — The minimap is drawn from `RoadGraph`, once, and switches off on its own

**Status.** 🟡 Built (`P3-44`) — the user's drive and the web build's clip frame owed

- The slot exists and is graded empty: `hud_layout.tres` `minimap`, bottom-right above the plate
  (`Q80`: "the two are one question"). `hud.gd` names `P3-5b` as its filler; `PLAN.md`'s `P3-5b`
  never mentions a map, so it is `P3-44`, in `B4`.
- Source: the `RoadGraph` the HUD already holds — Wan Chai is 792 edges / 4,573 vertices. No ETL
  change, no schema bump, no new generated asset (hard rules 2, 5).
- One static `ArrayMesh` in plan metres on a `MeshInstance2D`; per frame only its transform moves.
  Stroked at `width_of`, levels emitted ascending with a field-coloured casing under each deck, so
  a flyover draws over the street. Undrivable edges are not drawn.
  🚫 The plan's one `_draw()` of a `draw_polyline` an edge: a canvas polyline is its own polygon
  command and does not batch — up to a draw call an edge against a 136–150 frame. Not built.
- **Cost, throttle route, `--debug-view=off`, against `--minimap=off`:** `draws` 110 → 115 at
  t=1 s and 132 → 137 at the t=6 s peak (**+5**: field, clip, roads, chevron, frame); `prims`
  760,295 → 772,505 (**+12,210**), both regions resident.
  ⚠️ Built naively it was **+37,696** — an eighth of the mobile budget's 300k. Cut by one cap a
  junction instead of one a stroke end, one bevel on the outside of a turn over `sin` 0.1 instead
  of two on every vertex, and dropping vertices under 0.4 px off their road. Same frame by eye.
- `clip_children` on the chamfered field works on Metal/Mobile and is one of the five draws.
  ⚠️ **Not seen on the web build**: it exports, but headless Chrome's one-shot screenshot returns
  the loading splash and the DevTools profile was in use. Owed before `B4`'s web review.
- Tuning is data: `tuning/minimap.tres` + `minimap.md` (`Q119`), no defaults on the exports;
  colours from `hud_style.tres`.
- 🔴 **`--minimap=off`, separate from `--hud=off`.** `GAME_DESIGN.md`'s acceptance test disables the
  minimap and the arrow; it does not disable the speed or the plate. `P3-9` runs with it off.
- The projection is a pure static function so `verify_hud` can assert it without a frame. ⚠️ The
  defect to catch is a **mirrored** map (3D −Z-forward to 2D +Y-down flips handedness), which looks
  plausible on a grid: east-is-right-when-heading-north is the assertion, mutation-checked. One
  compass convention — `CityManifest.bearing_deg`'s — never a second.
- **One component with the street plate, the user's call (2026-09-22)**: the map over a name
  strip, one keyline, 280 x 324 — 14.6% of frame width, inside `Q80`'s 18%. ⚠️ First built
  340 x 390 (17.7%) to seat the longest names; the user read it as too large on the frame, and the
  lettering shrinks instead. `Q80` had called the
  two "one question". Anchored as the plate is (bottom, with the speed); the map's own rect spans
  the middle and would float off the baseline on a tall window. `HudLayout.abutting()` refuses a
  layout where the two rects do not share a width and an edge. `draws` +5 → **+4**.
  ⚠️ Amends `Q80`: in the strip the LETTERING is cut, not the box — `StreetPlate.fitted_size`,
  measured off the font (a `Label` out of the tree reports no minimum size, and a fit that reads 0
  never shrinks). `CENTRAL-WAN CHAI BYPASS TUNNEL`, the longest of four regions, sets at 16 px.
  Under `--minimap=off` the plate stands alone and is cut to its lettering as before.
- **Driving only**: roads and the car. No destination pip — nothing has a destination until
  `P3-1a`, which adds it (clamped to the rim along the ray from the car, not per axis, or the pip
  points the wrong way in a corner). No `route` seam was built either: it is one more child in the
  same map space whenever `Q137` reopens.
- `verify_hud`: the `map:` assertions — both orientations, mirror, anchor, chevron, draw order,
  casing, shared caps, bevel side, simplification; 12 mutations, each caught. ⚠️ One survived
  first (a cap at the narrower half) and bought the shared-cap assertion. ⚠️ A mesh keeps colours
  as RGBA8, so the order test uses black and white.
- 🚫 An orthographic `SubViewport` over the city: a second pass of the city on the Mobile renderer,
  and a look that fights flat shading. 🚫 An ETL-baked map texture: a schema bump and a fixed
  resolution for data already in memory. Neither was measured — refused on cost of entry.
- **Heading-up, the user's call (2026-09-22): "like a real world gps".** It is the convention a
  driver already reads, and `hud_layout.gd` places the map to be "glanced at mid-corner".
  ⚠️ North-up is the one that rewards a local's memory, and was weighed and not taken; it stays a
  `.tres` bool, and both orientations stay asserted in `verify_hud`.
- **One-way arrows, the user's call (2026-09-22)**, over a recommendation to hold them for `B3`:
  an arrowhead about every 53 m of one-way road, in the same mesh after each level's roads — no
  draw call, +1,080 `prims`. No third colour: the field's inside a road it fits, the road's as
  barbs where it does not. 🔴 Direction is asserted, not looked at — tip ahead along the vertex
  order, which is how the ETL guarantees a `forward` edge runs; 5 mutations, each caught.
  The panel with them: **+4 `draws`, +13.4k `prims`** against `--minimap=off` (`Q139` has the
  three-state table).
- **Arrows off, and a border arrow on (2026-09-24, the user's calls).** The user found the one-way
  arrows "not providing anything useful or clear"; trial frames at 7 px and at 13 px every 110 px
  agreed — at 13 px the head is wider than most Wan Chai streets and draws as barbs — and a GPS
  prints none at this scale, the route doing their job. `arrow_px = 0`; the mesh code and its
  assertions stay behind the dial. In their place, from "what does an ordinary GPS show that we
  are missing": while the target is off the 320 m map, a plain triangle stands on the border on
  the line from the car toward it, in the target's colour (`map_beacon_px`, `beacon_point`, three
  `verify_hud` assertions and the anchor held inside its room). **+6 `draws`, +12.6k `prims`**
  against `--minimap=off` carrying a fare 1.2 km off (the pin and the border arrow one call each),
  from +4 / +13.4k. The harbour and a main-road class are the same round's other two asks.
- **Main roads apart (2026-09-24, the user's call).** Nothing in the road network ranks a road —
  `ROUTE_NUM` numbers only Route 1 and 4's flyovers and tunnels, and speed ≥ 70 or `lanes` ≥ 3
  flag Gloucester Road and miss Hennessy — but iB1000's `StreetCentreLines.STREETTYPE` is a
  published domain beside the same `ST_CODE`. `roads.py` joins it by code and places it by the
  nearest same-code segment to an edge's middle (25 of 585 codes carry two types; the majority
  misclassed 38 of 762 edges). Wan Chai 320 main / 424 minor, Causeway Bay 48 / 139; the rest
  carry no code or have no segment within 30 m — Convention Avenue until the north row of sheets
  is fetched. Published as `street_class`, additive, no bump. The map draws `main` near-white
  over a mid-grey minor grid, each its own pass so a main road runs through the junctions. As
  published: Lockhart, Jaffe and Harbour Road are secondary. ⚠️ Convention Avenue's `ST_CODE`
  10334 is in no sheet's street centrelines, so its 7 edges stay unclassed — a data gap, not a
  missing sheet.
- **The harbour and the parks (2026-09-24, the user's call).** A new stage, `pipeline/basemap.py`
  → `basemap.json` (`CITY_SCHEMA` 36, required on `fence`'s terms). The sheets publish no sea
  polygon, so the frame (read box + the map's 320 m) is cut along iB1000 `Shoreline`
  (`SWA`/`HWM`/`BRE`) and a piece with no `Building` on it is sea. The region's own sheets stop
  76 m north of Wan Chai — short of the HKCEC frontage and the typhoon shelter — so
  `tiled_sources.topography.fetch_margin_m` = 320 fetches the ring (8 + 8 sheets, 257 MB each
  region, shared), and `config.py` refuses a `reach_m` past it: a missing sheet reads as open
  sea. ⚠️ **Bridging loose shoreline ends was built and refused** — pier and shelter outlines
  dangle at dozens of sub-metre joins no nearest-line rule closes; thickening the whole line by
  `seal_m` = 40 m closes the one real gap (~35 m at a pier end) at the price of any inlet under
  40 m, which a 240 px map cannot show anyway. Wan Chai 748,723 m² of sea, Causeway Bay 177,055;
  parks off `Site.SITECODE` (`PAR`/`PLA`/`SOA`/`SGR`/`PRO`), Victoria Park one 188,001 m² `PAR`.
  Triangles first in the minimap's mesh, so every road is over them: **+5 `draws`, +14.7k
  `prims`** against `--minimap=off` carrying (one mesh, so no new call).
- **No dependency on the fare system or the router.** It needs `RoadGraph`, the car and the slot,
  all shipped; free roam has no fare and the map is whole there. Only the pip waits on `P3-1a`, and
  it is an empty setter. Listed under `B4` because `hud.gd` gave the slot to `P3-5b` — a grouping,
  not `B4`'s `B1`/`B3` deps. Buildable now; `P3-43` goes first only because it unblocks `B1`.

**See.** `Q80` · `Q137` · `Q119` · `GAME_DESIGN.md` "Acceptance test" · `.claude/rules/hud.md`

---

## `Q137` — A router is built; a route line on the map is not

**Status.** ✅ Closed. The router half is ✅ built (`P3-43`). The guidance stance below was a
design call, not a measurement, and **the user reversed it on 2026-09-24, before `P3-9`**: the
legal route to the fare's destination is drawn on the minimap — `P3-46`, the section at the end.

- **The router is owed whatever the map does.** `P3-3` needs a legal route; `P3-1a` needs road
  distance for a minimum trip and for a fair allowance — in a region 93.5% one-way by drivable
  length, two stands 200 m apart can be a far longer drive. Nothing in `game/` traversed the graph
  before `P3-43` (`tools/reachability.py`'s header). Its own task, first in `B1`.

### The router — `P3-43`, built

- **The search state is a directed edge.** A restriction is `from_edge → via_node → to_edge`; one
  state per one-way edge, two per two-way. `scripts/city/road_router.gd` builds them from
  `RoadGraph`'s accessors — `from_node_of`, `to_node_of`, `is_turn_banned`, `plan_length_of`, all
  new — and never inside it. U-turns are refused with the source (`reachability.py` bans them).
- **One search per destination, not per query.** `prepare(edge, t)` runs a reverse Dijkstra from
  the goal and keeps the tree; `route()` from any source is a lookup and a path walk. Measured on
  the shipped graphs: `prepare` p50 0.59 ms, max 0.70 ms on Wan Chai's legal network (857 states)
  and 1.86 ms on the player's (1,528); prepared `route()` p50 5 µs, p99 8 µs over every admitted
  edge to every fare node (36,000 routes). ⚠️ **`PLAN.md`'s "one query under 1 ms" is read as the
  prepared query**, and `prepare` is priced against a frame (16 ms). A per-query search would in
  fact also fit — a full exhaustive search IS the 0.6 ms `prepare` — so the tree is not what
  makes the budget; it is what makes a route at 5 Hz cost nothing, which is `PLAN.md`'s own usage
  ("once per fare and on leaving the path, never per frame"). 🚫 A* was not built: 40% of ordered
  fare pairs have no route (893 of 2,244; the clip is not strongly connected), and an unreachable
  query exhausts its component whatever the heuristic.
- **The cost convention is `reachability.py`'s, exactly.** Entering an edge costs its whole plan
  length, the source's own length is excluded, the target's included; the tree holds that reversed
  (`to_goal[state]` from the state's entry node). A fare route seeds the source's remainder
  `(1 - t)·len` along, `t·len` against, and the goal's part likewise. 🔴 **Lengths are 64-bit**:
  `RoadGraph._lengths` is summed from the document's doubles before the `Vector3` cast, because a
  float32 sum drifts 4.7e-4 m over the longest route — inside a millimetre, and not by enough to
  call a 0.001 m agreement a check. `_check_topology` pins the loader to that at 1e-6 m.
- **Diffed pair for pair, not sampled.** `reachability.py --json` publishes its `control` and
  `starved at one lane` tables as `reachability.json` beside the graph; `verify_road_graph.gd`
  routes every pair under `Profile.survey(NONE | LANE)` — level 0, every rule, no U-turn, the
  tool's own population — and `verify_join.gd` does the same over the runtime merge against the
  reference merge's table, **with no id map**: both renumber the second region from the frame's
  maximum in document order and `_check_edges` asserts `from` / `to` already. Every pair agrees at
  0.000000 m: 194,774 / 13,718 control pairs, 179,601 / 12,716 one-lane, 334,767 / 288,626 across
  the join. The tree and the table are not even the same search direction, so an agreement is
  two implementations agreeing, not one reading itself.
- **Two profiles, two bars, never merged (`Q19`).** `Profile.legal()` obeys direction, turns and
  the U-turn ban at the lane bar — `admits` is pinned to `is_routable` edge by edge. `Profile.player()`
  frees direction, turns and U-turns at the car bar — `admits` is `is_drivable and fits_car`, the
  fence's complement. ⚠️ The shipped profiles are NOT the survey population: `is_drivable` admits
  the 41 / 9 measured level-1 edges the tool never routes, so they are pinned by monotonicity
  instead — every one-lane pair is still routed by `legal` no longer than before, every legal pair
  by `player` no longer, and 332,054 of 352,803 strictly shorter (rules broken buy something) —
  and by state count (the player holds exactly two states per edge). Which par a fare uses stays
  `P3-1a`'s call; recommend legal.
- **"No route" is an answer.** `Route.found` false, `edges` empty, `distance_m` the plan distance.
  `verify_road_graph.gd` checks it on 20 severed pairs per region, and ties `route(1.0 → 1.0)` on
  20 one-way pairs to the table's own cell.
- Mutation-checked, eight ways (`.claude/rules/router.md` lists them); each fails by name.
- 🚫 Not built here: a consumer. `hud.gd`, `fare_preview.gd` and the minimap are untouched; the
  world-space arrow to the next junction is still held for after the first fare review.
- **No turn-by-turn line on the minimap.** Pillar 1 is "navigate by memory, not by minimap"; the
  arrow *assists*; the long haul "rewards route knowledge", which a drawn route pays to whoever
  follows it. `Q80`'s references put the destination in the world and neither draws a route.
  ⚠️ **Not measured shut** — nothing was built or driven. It is the pillar applied, and it reopens
  on evidence from `P3-9`.
- Deferral is cheap: `Q136`'s map takes a `route` polyline in the same map space, empty until
  something sets it.
- **Held for after the first fare review:** the world-space arrow (`P3-5a`) pointing at the next
  junction on the route rather than as the crow flies. In a one-way grid a straight-line arrow
  often points down a street that cannot be entered; this helps a non-local without drawing the
  answer.
- ~~Still open: whether guidance, if it ever ships, routes legally or as the player drives.~~
  Answered by `P3-46`: legally.

### The route line — `P3-46`, built (the user's call, 2026-09-24)

- **What the user asked for**: an "ideal" GPS route on the minimap whenever there is a goal,
  "which follows all the road direction and rules", against the arrow that only points at the
  goal. That is the legal profile, and the pillar-1 stance above is reversed on instruction, not
  on `P3-9`'s evidence; `P3-9` still runs with it off (`route_px = 0`, `--minimap=off`, `--hud=off`).
- **The fare's own route, drawn.** `FareSystem` already routed from the car's `Hit` at 5 Hz while
  carrying and kept only the distance; now it keeps the `Route` on the fare (`Fare.route`,
  `route_from_t`), set at the hail from the pickup and refreshed each carrying sample. `hud.gd`
  reads it inside the `sampled` signal, like everything else it reads from the system, and hands
  the map plan points. **Par and the line are the same drive**, so the clock and the line agree.
- **Only while there is a goal** (`Q142`): from the hail to the delivery or bail, on the
  destination. Idle has no goal, so no line to the nearest customer.
- **Starts on the car, ends on the stop point.** `MinimapMesh.route_points` reads each edge's
  polyline in driving order (reversed where `forward` is 0), cuts the first at the hit's `t` and
  the last at the stop's, by plan length — the same parameter `Hit.t` and `point_at` use.
  `verify_road_graph.gd` pins it on real routes: starts on the source point, ends on the target
  point, and re-sums to `distance_m` within 5 cm (float32 polyline against 64-bit lengths).
- **A wrong turn re-routes for free**: the next sample routes from wherever the car is, a lookup
  on the hail's tree. **No route is no line**: an edge the legal network does not reach clears
  the line, and the pin and the border arrow stay — `Route.found` false is an answer, not a stale
  line. A car facing the wrong way down a one-way street is drawn the law's way out; the wrong-way
  sign (`Q81`) already covers that case.
- **Seeded the way the car faces.** `route()` takes an optional `Facing` (`ALONG`, `AGAINST`,
  `EITHER` — the default and the tables' convention); the fare passes `Hit.along`, new on the hit, so on a
  two-way street the line leaves along the car rather than starting behind it with a U-turn the
  profile bans anyway. `verify_road_graph.gd` pins both seeds on a two-way edge: along, the point
  behind is reached round the block or not at all and never shorter; against, the direct drive
  back. Every existing call is unchanged and the tables did not move (regenerated, three lines).
- **One mesh, the roads' child.** `MinimapMesh.route_mesh` is one stroke in `map_route`,
  `route_px` wide at the slot's scale, over every road and under the pins; it rides the roads'
  transform so `follow` never touches it. `hud.gd` walks and rebuilds it only when the edges
  change or the start moves `ROUTE_STEP_M` (0.5 m) along the first — a parked car's `Hit.t`
  jitters every sample — and `set_route` rebuilds nothing for the same points. Cost: +1 draw and
  the route's quads — measured in `PROGRESS.md`.
- **Colour**: `map_route` (`hud_style.tres`), opaque like the roads, asserted legible on the field
  and apart from both road colours by `MAIN_ROAD_CONTRAST`; a first guess ahead of the user's frame.
- Mutation-checked (each fails by name): the reverse dropped in `route_points` → the drawn start;
  the `along` seed ignored → the same-edge pin; `set_route` never hiding → the map's empty-route
  assertion; the roads' transform not carrying the route → facing east.
- 🚫 Not built: the next-junction arrow (held), a route while idle, a route on the player's profile.

**See.** `Q136` · `Q80` · `Q51` · `Q19` · `Q95` · `PLAN.md` `P3-43` · `.claude/rules/router.md`

---

## `Q138` — The HUD takes the racing-game arrangement, and every known future component has a graded slot

**Status.** ✅ Closed — the user's call (2026-09-22), built with `P3-44`. The user's drive owed.

- **Map bottom-left, speed bottom-right** — Forza, Need for Speed, Gran Turismo. `Q80` took
  Midtown Madness 2's mirror of it; what survives of that reference is the pairing of the street
  map with the street name (now one panel, `Q136`), not the side. The rule becomes: **left is the
  world, right is the car, top is the fare, the middle is the road.** A `.tres` edit, as `Q80`
  built it to be; `verify_hud` passed with nothing but the rects moved.
- On touch each readout sits over the thumb that acts on it — map over `steer_zone()`, speed over
  `drive_zone()`. A consequence, not the reason: the reason is where a player of the genre looks.
  ⚠️ `steer_zone()` / `drive_zone()` are still where handedness lives (`Q83`); a left-handed
  scheme swaps the thumbs and, to keep this, would swap the two bottom rects with them.
- **Plan the area, do not hold the space** (`Q80`, the user's rule) now covers every HUD
  component a planned task is known to add, each a reserved rect `verify_hud` grades against the
  thumb rests and the design frame, drawn only under `--debug-view=full`:

  | Slot | Task | Where |
  |---|---|---|
  | `timer` | `P3-5a` | top-left |
  | `combo` | `P3-2b` | under the timer — both count the session |
  | `meter` | `P3-5a` | top-right |
  | `award` | `P3-2a`, `P3-2b` | under the meter — points are money |
  | `callout` | `P3-5a` | top-centre, under the wrong-way sign's y 136 — since `Q142` flush with the top edge, the sign moved under the countdown |

- 🚫 The award in the middle of the frame, where an arcade racer puts it: the middle is the road.
- 🚫 A slot for the destination arrow: it is in the world (`Q80`). 🚫 A pause button: no planned
  task names one, and it is a control — `input_router`'s layer, not this `MOUSE_FILTER_IGNORE` HUD.

**See.** `Q80` · `Q136` · `Q83` · `game/tuning/hud_layout.md`

---

## `Q139` — One voice: the cab's instruments in one dark housing

**Status.** ✅ Closed — the user's calls (2026-09-22), built with `P3-44`. The user's drive owed.

- **Consistent, and dark.** The user asked for one style once the map made `Q80`'s white half the
  larger one; chosen from two rendered frames (all dark, all light) over keeping two voices.
  `plate_field`, `chip_field` and `map_field` are one value; `verify_hud` holds them equal, dark
  and opaque, where it used to assert the plate lighter than the chip. One bezel on every panel —
  the speed chip had none.
- **的士咪錶 as the language** (`ART_DESIGN.md` always named it; only the signage half was drawn).
  🔴 Two corrections from the user, each of which a first build got wrong: **red digits are the
  fare's**, and **speed was never on a meter**. So the cab's two instruments keep their own faces:
  - **Speed is the dashboard's** — `SpeedDial`: ticks and an amber needle over printed numerals,
    a Crown Comfort's cluster. Ticks one static mesh, the needle a polygon that only rotates; +2
    `draws`. Scale 160 against the car's 140. The needle is held off red.
  - **The fare is the meter's** — `SevenSegment`: seven-segment digits with the unlit ghost
    showing, one mesh. ⚠️ Built for the speed, first in red and then in white; nothing draws with
    it now. It stays, graded, for `P3-5a`'s meter, which brings its own red key.
- **The style table is the theme.** A Comfort Hybrid's modern cluster is a second `hud_style`
  `.tres` the car names. Nothing selects one while there is one car; the constraint it puts on
  today's code is that every look stays in the table and out of `hud.gd`.
- `warn_bar` is its own key: the NO ENTRY bar borrowed the plate's white while there was one.
- `verify_hud`: the segment table is asserted in LETTERS, not by count — a `4` lit as `abfg` has
  four segments and survived the count. Dial: zero, sweep clockwise, linear, pinned at both ends,
  arc over the top. 9 mutations, each caught after that fix.
- **Cost, one route, three states** (throttle, `--debug-view=off`, t=1 s / t=2 s): `--hud=off`
  102 / 101 `draws`; `--minimap=off` 113 / 112; full 117 / 116. So the HUD is **+15** — +11
  without the map (it was +8 before the dial and the bezel, and `ARCHITECTURE.md` still said
  `P3-24`'s +5) — and the map panel **+4 `draws`, +13.4k `prims`**.
  ⚠️ A "+6" for the panel was reported first: a new frame against a `--minimap=off` baseline taken
  before the dial existed. Both sides of an A/B are re-run together.
- 🚫 White seven-segment for the speed: consistent, and the language of an instrument the speed
  is not on. 🚫 A dot-matrix face for the street name: a fifth licence (`Q79`).

**See.** `Q80` · `Q136` · `Q138` · `Q79` · `game/tuning/hud_style.md`

---

## `Q140` — The harbour is a frame minus the land, and the land is north of the sheets we hold

**Status.** ✅ Closed — the user's calls. The minimap half was built with `P3-44` (2026-09-24,
`basemap.json`; the section under `Q136`). The world half — "draw something blue where the water
is" — was built on 2026-09-25, the section at the end; it reverses the "out of scope" below.
`P3-45`. The user's frame owed.

- **Why it is wanted.** On a heading-up map the harbour is the one fixed cue — north is always the
  water (`000` faces it). The only borrowed map convention judged to pay at this scale (`Q136`).
- **The source is one we hold.** iB1000 (`topography`), already fetched and licensed. 🚫 Not
  OpenStreetMap (`Q133`, hard rule 7). 🚫 Not the 3D map's `WATERBODY` — hillside features at
  24.6–113.6 m, not the harbour (`DATA_SOURCES.md`).
- **There is no sea polygon.** `HydroPolygon` is inland water only: over the 26 sheets held, `CHA`
  199,590 m² (Sha Tin's Shing Mun channel — worth drawing), `RIV` 22,864, `PON` 6,414, and nothing
  off Wan Chai larger than 887 m². The sea is what `Shoreline` bounds: `SWA` seawall 3,324 m and
  `HWM` 269 m over Wan Chai's three northern sheets.
- 🔴 **Most of that shoreline is the sheet edge.** Wan Chai's north bound (northing 816,198) sits on
  the 1:1000 sheet line at 816,200, and the waterfront — the HKCEC peninsula, the ferry piers — is
  in `11-SW-10A`, `10B` and `9B`, which the region's rectangle never selected. Inside the bounds
  the sea is three inlets. A harbour worth drawing reads a margin north of the region
  (~400 m: the map shows 180 m past the car), as `join.reach_m` does sideways.
- **Shape of the build.** Sea = a frame (bounds + margin, clipped to the sheets actually held —
  no data is not water) minus the land; the land is the union of iB1000's polygon layers, closed
  over ~2 m; a candidate is kept only where its boundary runs along a `Shoreline` for some length,
  which is what separates the harbour from an inland gap between polygons. 34 shoreline lines in
  Wan Chai's frame merge to 26 parts; ends mostly meet exactly, the rest gap 2.5–40 m (structures),
  so 🚫 polygonising the shoreline alone does not close.
- A new stage and document (`water.json`, triangulated at build), a `city.json` key, the game's
  loader, `map_water` in `hud_style.tres`, drawn first in the minimap mesh — no draw call.
  Hard rule 5: both sides together.
- Not decided: whether the 3D city should get the same water plane. Out of scope here — until
  the user asked for it (below).

### The world's water — a plane at sea level over ground the tile stage sinks (2026-09-25, the user's call)

- **What ships.** `water.glb`: the basemap's sea triangles as one flat mesh at
  `basemap.water_level_m` = 1.3 (mean sea level +1.3 mPD; game y = 0 is the Principal Datum),
  `COLOR_0` from `materials.sea_water`, drawn by `region.tscn`'s `Water` node through the layer
  table (`generated_layer.gd`), one draw call a region, no collider, no shadow. `city.json` names
  it as `water` (schema 37), null where the frame holds no sea; `basemap.json` (schema 2) names
  it as `asset` and publishes `water_level_m`, which `verify_water.gd` holds the mesh flat at.
- 🔴 **A plane over the ground as shipped does not work, and it was measured before the sink was
  built.** The 3D map's terrain over the harbour is not flat: sampled at 4 m over Wan Chai's sea
  on the LOD0 tiles, 1.1–4.2 m (p10 1.2, median 2.3, p90 3.0), and the land within 12 m of the
  shore is 2.7–4.9 m (median 3.7). No level separates them: at 3.0 m 9.6% of the sea shows grey
  through the plane, at 3.5 m 0.4% does but ~40% of the shore band is under water, and at 2.5 m a
  third of the sea is grey. So `buildings.sink_sea` drops every terrain vertex inside the sea
  polygon to `basemap.seabed_m` = −3.0 before decimation — vertices, not triangles, so a triangle
  straddling the shoreline slopes down over its own width, the sea wall the low-poly look
  affords. Re-measured after: **2.1%** of the sea's ground above the water (12.6% in the 0–4 m
  band, 0.5% past 16 m — the slopes), and **10.1%** of the land within 12 m of the shore under it
  (p10 exactly 1.30 — the same slopes, from the other side). 12,270 vertices sunk in Wan Chai,
  3 in Causeway Bay, whose read box stops at the shore. Cost on the throttle route: +1 `draws`,
  +213 `prims` (frames in `build/driver/water_after_ground`, `water_drive_on`). `basemap` moved ahead of `buildings` in `__main__` for it.
- **The colour obeys `Q33`.** `sea_water` is 8.2% — turbid coastal water's *diffuse* albedo,
  5–12% — and renders near-black on its own; the blue is the sky reflected off
  `tuning/water.tres`'s roughness, `tramway.md`'s split for the rail head — 0.45 ships: at 0.15
  the harbour is a near-white mirror of the horizon haze, at 0.45 one deep blue plane (both frames
  under `build/driver/`, the user's pick owed). `ART_DESIGN.md`'s
  table carries it. Do not lighten the entry to make the harbour bluer.
- ⚠️ **The car can leave the quay.** Water is not a floor: a car that drives off lands on the sunk
  ground under the plane, 4 m down, and stays there. Before it drove onto grey sea at 1–4 m and
  kept going; neither is a game state, and a reset is owed (`P3-9`'s family, not this task's).
- ⚠️ **The plane ends at `reach_m`** (320 m past the read box) — beyond the fetched sheets there is
  no shoreline to cut, so no water. From the HKCEC frontage that is ~250 m of sea before the fog
  and the sky's horizon; Kowloon is not drawn either. A skirt past the frame is a look question
  for the user's frame, not a data one.
- ⚠️ **A pier narrower than `seal_m` is sea** — the mirror of the inlet rule above — and its
  ground sinks with the rest; the pier's own building stays at its base height, on nothing. Not
  seen from the road in Wan Chai; recorded so it is not re-found.
- **Waves (2026-09-25, the user's ask: "a moving simple texture trick").** No texture — the
  bundle carries none (`Q63`) and the plane has 213 triangles to displace — so `water.gdshader`
  fakes them per pixel: two crossed sine trains in world plan (6.0 m and 3.6 m, 0.25 Hz and 0.7 of
  it, bearing 20°) tilt the shading normal by a slope of 0.12 so the sky's reflection breaks into
  moving bands, and their product lifts the crests 6%. Every number is in `water.tres`. Its own
  shader, not a change to `vertex_albedo.gdshader`, whose header forbids growing it. Measured:
  73k pixels of the `ground` frame move between t=0.8 and t=2.8, all on the water; `check.sh` and
  the runs report no shader error; the drive frame's cost is unchanged (804,679 / 108).
- 🚫 **Not built**: draping the plane on the terrain (bumpy water), rendering it with no depth test
  (draws over the piers), flattening the terrain to a level instead of sinking it (the shore band
  is the same noise from the other side).

**See.** `Q136` · `Q133` · `Q33` · `DATA_SOURCES.md` iB1000 · `PLAN.md` `P3-45` ·
`.claude/rules/basemap.md`

## `Q141` — The 咪錶 runs Transport Department's tariff on what was driven; the skill is the tip

**Status.** ✅ Closed — the user's calls (2026-09-23), built as `P3-1a`. The user's drive owed.

- **The meter is real money.** `tuning/tariff.tres` is TD's urban fare, effective 14 July 2024:
  HK$29 for the first 2 km, HK$2.1 per 200 m or per minute of waiting until HK$102.5, HK$1.4
  after; cited in `tariff.md`. It runs on the metres the car actually drove and the seconds it
  actually waited (`FareMeter`, `scripts/core/`, integer cents). 🚫 No abstract multiplier: the
  user chose the meter over `GAME_DESIGN.md`'s 1× / 2× table and over a fare fixed at the hail.
  ⚠️ The stated cost: inside a 1.5 km² region most trips are under the flagfall, so the reading is
  HK$29 for most fares and only waiting past 2 km moves it. Authentic, and why the tip carries
  the skill.
- **The unit rule is "or part thereof", on two buckets.** A unit is charged when it begins (2,001 m
  reads 31.1, 2,200 m still 31.1, 2,201 m 33.2); either bucket exceeding its unit charges and
  resets both; nothing is charged for waiting inside the flagfall distance. No waiting-speed
  threshold exists as a field: the tariff's own two units cross at 12 kph. `verify_fares` pins
  2,001 / 2,200 / 2,201 / 9,000 (= 102.5, the 35th unit) / 9,200 m (= 103.9, the first 1.4) and
  the bucket reset from both sides.
- **The tip is the skill, and speed pays now.** The user asked that a fast arrival — a shortcut
  or speeding — be rewarded. A shortcut *lowers* the meter (less distance), so the reward is on
  the clock: `tip_hkd = remaining_s × tip_hkd_per_s` at delivery, HK$0.5 a second. `P3-2b`'s
  style chain adds to the same `Fare.tip_hkd`; delivery banks meter + tip as one HK$ sum, one
  seven-segment display (`Q139`). Measured on Wan Chai's seed-7 fare: par 1,575 m, allowance
  189 s, delivered after 1.25 s banks HK$122.88 (29.00 + 93.88); the same trip 2 s later
  HK$121.88. Driven (`--fare-seed=1` from the Expo Drive stand): aboard by 0.8 s, a short hop of
  par 1,216 m on a 146 s clock, meter HK$29.0, the remaining road distance falling as the car
  goes. 🚫 Separate score points beside the money — weighed, not taken.
- **The allowance is road distance with a floor**: `max(kind floor, legal route / par_kph)`,
  `par_kph` 30, `GAME_DESIGN.md`'s 30 s / 60 s becoming the floors. Par is `Profile.legal()`
  (`Q137`'s recommendation): what obeying the signs costs; the player may break every rule to
  beat it. 🚫 Fixed per kind — weighed, not taken.
- **The reach is computed at load, not at the hail.** `setup` prepares every destination once and
  routes every pickup to it (Wan Chai 16 × 23, 14.0 ms), keeping per pickup what the legal network
  reaches at `min_trip_m` (300 m) or beyond; a hail draws uniformly from that list on the seeded
  RNG (`--fare-seed=`) and pays one `prepare`. 🚫 Built first and refused: drawing blind and
  retrying up to eight times — a stand with one reachable destination was refused most of its
  hails.
- **Stranded pickups.** A pickup reaching no destination at the bar is dropped from the pickup
  pool, kept as a destination, counted (`FareSystem.stranded`) and named. Wan Chai: `f_017`,
  `f_018`, `f_020` — westbound Hennessy and Johnston Road PUDO points at the clip's west edge,
  where forward leaves the clip and the one-way network never comes back. Causeway Bay alone:
  `f_001`, `f_002`, its only two stands, so that region has no pickup of its own; its five other
  nodes are tram stops. `verify_fares` says SKIP there rather than certifying nothing. On the
  merged runtime (`wan_chai` + `causeway_bay`) the join un-strands `f_002` (Tung Lo Wan Road) and
  `f_001` (Electric Road) stays stranded: 17 pickups, 4 stranded, 25 destinations, reach 18.1 ms
  on the boot line. ⚠️ A new stranded node is a finding about the data, never a reason to lower
  the bar.
- **The pools are the yaml's rules.** A stand is a pickup and a destination unless
  `cross_harbour` (`P3-1b`); a PUDO point is what `pickup` / `dropoff` say; a `poi` tram stop is
  neither. The kind is the destination's. Wan Chai: 19 pickups → 16, 23 destinations.
- **A fare cannot start where the last one ended.** The hail re-arms only once a sample finds no
  pickup in reach; otherwise a delivery at a stand that is also a pickup hails again on the spot.
- **No dev chrome in the system.** `fare_readout.gd` names the `DebugHud` autoload;
  `fare_system.gd` cannot, because `verify_fares.gd` loads it before any autoload exists
  (`Identifier not found: DebugHud`, measured). `GraphOverlay`'s arrangement.
- **`--fares=off`** is free roam, what `P3-9` runs. Both flags through `Cmdline`.
- 🚫 Not here: the session timer and fare combo (`P3-2b`), cross-harbour and long haul with the
  HK$25 + HK$25 return toll (`P3-1b`), the HUD's meter, timer, callout, world arrow and minimap
  pip (`P3-5a`), operating hours (`Q14`).

**See.** `Q137` · `Q139` · `Q142` · `.claude/rules/fares.md` · `tuning/tariff.md` · `tuning/fares.md` ·
`PLAN.md` `P3-1a`

---

## `Q142` — The pending customer is the pickup pool, said as its building; the arrow points as the crow flies

**Status.** ✅ Closed — the user's asks (2026-09-23 and 24), built as `P3-5a`. The user's drive owed.

The user asked, with the minimal fare HUD, for "simple UI on where the pending customer is (taxi
stand?)". Nothing in `P3-1a` is a pending customer: the loop hails whichever pickup the car stops
within `hail_radius_m` of, drawn from a pool of 17 on the merged runtime (`Q141`). So the question
had two readings, and the one built is the one that changes no loop.

- **The pool is the customer.** Every pickup in the pool is an amber pip on the minimap
  (`map_pickup`, one mesh under the roads' transform, so it costs a matrix a frame and no
  geometry); the callout names the NEAREST one with its plan distance while the loop is idle
  (`Paterson Street between Kingston Street and Great George Street  31 m`), and the world arrow
  points at it in the pips' amber. Once hailed, all three turn to the destination: the callout
  reads `→ <name>`, the pip is one in the chevron's red, the arrow is red. `FareFace` decides every
  string and `verify_hud` reads it on synthetic fares: idle names the pickup, boarding names the
  destination and not the stand under the car, a new hail inside the DELIVERED hold wins.
- 🚫 **Not one designated waiting passenger per hail.** That reading would make the loop refuse a
  hail anywhere but the drawn stand — a `FareSystem` change, a different game, and not what a Hong
  Kong player expects of a cab that stops where it is flagged. Weighed, not taken; reopens only on
  the user's word.
- **A stop is said the way a passenger says it: the building first, the road under it** (the
  user's call, 2026-09-24, on seeing "→ Leighton Road eastbound near Matheson Street" as a
  destination). TD's `Location_EN` describes the kerb; a passenger says "皇冠假日酒店". The
  building comes from the source `DATA_SOURCES.md` flagged for exactly this on day one — iB1000's
  `BUILDINGNAME` — joined in the ETL (`fares.places`, `pipeline/fares.py::read_places`):
  `Building` footprint → `BUILDINGRELATEBUILDINGNAME` → `BUILDINGNAME`, names pooled across sheets
  first because a footprint's name can live in a neighbouring sheet, `NAMESTATUS` `E` only (the 45
  `O` rows are old spellings beside current ones), lowest name id where a block carries several.
  A node takes the footprint nearest its kerbside `pos` within 25 m — **and where the point's own
  text names a building inside that radius, that one wins over a nearer one**: "Jaffe Road outside
  Elizabeth House" sits nearer Tak Fai Building's footprint, across the footway, and both readings
  are the publisher's, the text the more specific. iB1000 names the tower ("Elizabeth House Tower
  C", "伊利莎伯大廈Ｃ座") where TD names the house, so the city's `block_suffix` regex is stripped
  before the search; the published `place` keeps the publisher's full name. Wan Chai: 47 of 48
  nodes placed, furthest 24.6 m; `f_001` "opposite to Great Eagle Centre" is correctly none —
  opposite is not at. Published as `fares.json`'s `place` (schema 1, additive; `ARCHITECTURE.md`).
  The runtime: `Fare.Stop.place(language)` falls back to the description where there is no place, and
  the road is the graph's own name for the stop's edge (`RoadGraph.name_of`), never re-parsed out
  of the text. The callout is two rows of English beside Chinese — the Kai face has no Latin —
  the English shrinking first because the Chinese is the shorter string in every name this city
  publishes. 🚫 Parsing the building out of TD's free text ("near X", "outside X", "X對面") —
  weighed, not taken: a second reading of a description when the survey publishes the footprint.
- **The arrow is as the crow flies**, a flat unshaded arrow 2.6 m over the car's origin
  (`fare_guide.gd`, in the world per `Q80`, no slot). `Q138` holds the next-junction arrow for
  after the first fare review; in a one-way grid this one will sometimes point down a street the
  car cannot enter, which is the acceptance test's premise. `--fares=off` takes it with the loop;
  it reads the loop only inside `sampled`, where the node is alive by definition.
- **The 咪錶 is the LED** (`Q139` paid out): `SevenSegment` draws the fare in dollars to one place,
  right-aligned in five cells over their ghosts, with a decimal point that marks a cell rather than
  taking one (`cells_of`). Between fares it reads the last banked sum, as a real meter does at a
  stand; before the first, 0.0. The tip clock is seconds left on the allowance, rounded UP, in the
  chip's ink until `timer_warn_s` (10 s) and the fare's red after.
- **Cost.** At the boot stand, one route, `--debug-view=off`: HUD off 103 `draws` / 760,232
  `prims`; HUD on with the loop carrying 134 / 774,153. The whole HUD is now **+31 draws** against
  `Q139`'s +15: the three housings, the LED mesh, the currency and unit labels, four callout
  labels, the pool mesh, the destination pip and the 3D arrow. The brief was "deliberately ugly, no layout
  work"; the draw count is the first thing `P3-5b` should spend on.
- **Measured shut here:** a fare hailed at a "drop-off only" spawn (`f_023`) is not a pool leak —
  `f_022` is inside 12 m of it across the kerb; `verify_fares` still refuses a drop-off-only point
  in the pool. `f_025` (31 m from any pickup) is the spawn that boots idle.
- **The user's six calls on the first frames (2026-09-24), all built:**
  1. **The guide answers distance** — `tuning/guide.tres` (`fare_guide.gd`, was `fare_arrow.gd`):
     the arrow over the taxi is 1.0 m and red at 400 m and beyond, 2.4 m and green inside 30 m,
     straight between (`closeness`, asserted at both ends and the middle).
  2. **A pin, not a dot, on the map** at the target — the nearest pickup while idle in the pool's
     amber, the destination in its red — the field's child so it stands upright as the map turns,
     re-placed by `follow`. The pool's other pickups stay dots.
  3. **A ring on the road** at the target: a 4 m radius band 0.6 m wide, 8 cm over the surface,
     pulsing at 1.2 Hz by 15%, alpha-blended, the guide's colour.
  4. **The countdown is centred, with no housing** — bare 84 px numerals outlined in
     the housing's dark, the one readout allowed in the middle (`hud_layout.md`).
  5. **The distance is never between two names**: "TONNOCHY ROAD  320 m", the road first.
  6. **One language at a time** — `Locale.language()`, `--lang=en|zh` until the options menu owns
     it; the callout reads "新鴻基中心 / 杜老誌道  320 m" or the English, never both on a row.
     The street plate stayed bilingual because the real one is — until the user asked for it in
     the one language too (2026-09-24), and for **Chinese as the default**. `Fare.Stop.place(language)` /
     `road(language)`; `FareFace` takes the language at construction and `verify_hud` reads it in
     both.
- **The user's four calls on the second frames (2026-09-24), all built:**
  1. **Nothing is shown until there is a customer.** The nearest-pickup callout, the guide and
     the pin are down while idle — only the pool's pips on the map remain. 🚫 The "pending
     customer is the pool" reading above is withdrawn as a *display*; the loop is unchanged.
     After a delivery everything but the total resets: the meter reads 0.0, the clock is down,
     and DELIVERED holds in the callout for its three seconds.
  2. **The goal box reads as one thing**: a caption line (DESTINATION / PICKING UP / DELIVERED),
     the building, and the road with the **road distance left** after it — `remaining_road_m` at
     5 Hz, metres under a kilometre, a tenth of a kilometre above.
  3. **The total sits under the meter** without overlapping it: the LED at 46 px, the stack
     unsqueezed.
  4. **Every meter tick flashes near the centre**: "+HK$2.1" as a unit begins, "+HK$29.0" at the
     flagfall, and the banked sum in the gain's green at delivery — bare outlined numerals in the
     `tick` rect under the clock, fading over `tick_fade_s` (1.2 s). Driven by
     `FareSystem.meter_changed` and `delivered`, never polled.
- **The user's third round (2026-09-24), built:** with no one aboard and one or more pending
  customers, the **arrow points at the closest one** — no goal box, no clock — and **every pending
  customer in range is marked, like a map**: an amber pin per pickup on the minimap (the field's
  children, upright, re-placed by `follow`; hidden while a fare runs), and an amber ring on the
  road at each (one `MultiMeshInstance3D`, one draw, pulsed with the destination's). Hailed, the
  pending marks go down and the destination's pin and ring come up. This supersedes item 1 of the
  round above: idle is no longer dark, but the goal UI still is.
- **Layout (2026-09-24, the user's call):** every housed panel sits flush on the screen's edge —
  the map and the speed on the side edges (the bottom edge is the thumbs', so their y 860 baseline
  stays), the meter and the callout on the top edge — the countdown moves up to sit just under the goal
  box (y 116), the tick under it, and the NO ENTRY sign moves from the top to under them both, at
  y 320. The map and the speed then moved down to a y 960 baseline, the thumb rests shrinking to
  the bottom 100 px to let them (`P2-4` has no handset yet; the rest's height was a guess and is
  now the user's). The goal box narrowed to 520 px once it carried one language. A `.tres` edit,
  as `Q80` built it to be; `verify_hud` passed with nothing but the rects moved. The reserved
  `award` and `combo` rects followed their neighbours.
- **The user's fourth round (2026-09-24), built:**
  1. **The clock's unit on the number's row**, `99 秒`, on one baseline: the unit is lifted by
     the difference of the two fonts' descents, so it follows the sizes and the language's face;
     `timer_unit_gap` (4 px) is the one new dial.
  2. **The end of a trip is not the start of another.** A delivery at a stand that is also a
     pickup put a pending ring under the car the moment the passenger was out. The loop was
     already disarmed there and the arrow already skipped it; the ring and the map pin now do
     too, through `FareSystem.withheld_pickups` — the pickups inside `hail_radius_m` while
     disarmed, one rule with `nearest_pending`. `verify_fares` asserts it at the delivery, and
     returning nothing from it fails by name.
  3. **The game starts when the player pulls forward.** The car started on `f_004`'s stand and
     boarded before a key was pressed; it now starts `RoadSpawn.DEFAULT_SETBACK_M` (20 m) back
     along the road, 8 m outside the hail reach, and `verify_spawn` holds it behind the stand and
     out of reach. A setback that would land on a road running another way is not taken.
     `--spawn-fare` still starts ON the named node (setback 0), so a dev route timed from a fare
     node keeps its timing; a route timed from the default start moved 20 m.
- 🚫 Not here: the session timer and the combo (`P3-2b`), the award (`P3-2a`), the next-junction
  arrow (`Q138`), a route line (`Q137`), the options menu (`P3-5b`).

**See.** `Q141` · `Q139` · `Q138` · `Q80` · `.claude/rules/hud.md` · `.claude/rules/fares.md` ·
`tuning/hud_style.md` · `tuning/guide.md` · `PLAN.md` `P3-5a`

## `Q143` — A street the region cuts is closed on the line; the neighbour's way in never is

**Status.** ✅ Closed — the user's ask (2026-09-25), built as `P3-29a`. The user's drive owed.

The user asked for "some blockage" on every road not yet connected to another region — the
streets that reach the region boundary and stop. `GAME_DESIGN.md` calls the map edges diegetic and
that holds for the harbour and the escarpment; it never held for the 67 Wan Chai and 19 Causeway
Bay streets the clip cuts on the rectangle. Past that line there is no tile and no ground, so a
car driven down one left the world and `drive_harness` respawned it after a 25 m fall.

- **A third fence population, not a third bar.** `pipeline/fence.py` already closes two sets with
  one row of the authored barrier: the starved edges (`Q19`) and the ungraded touchdowns
  (`Q103`). A clipped end is neither narrow nor ungraded, so it travels as `clipped_edges`, a
  third list with its own counters (`clipped_ends`, `clipped_no_width`), under the same
  `closes()` identity, and `fenced_edges` does not gain it — `RoadGraph.fits_car` re-derives that
  set and must not. Schema 2 → 3 on `fence.json`; a v2 reader reports every clipped row as a
  barrier on an edge nothing closes.
- **The rule is read off the built graph, never off `neighbours:`.** An end is clipped when its
  node carries one open arm (the same level policy as `fenced_edges` and `_adjacency`), no
  `foreign_edges` run touches it, and the edge's own polyline end lies within
  `fence.clipped_within_m` (1.0 m) of the region rectangle's line **from the inside**. A foreign
  run at the node is the join `P5-7e` publishes — the road continues into the neighbour — and that
  is what "not yet connected to another region" means. A neighbour declared and not built leaves
  nothing open on a promise. The row stands `inset_m` inside the map and faces the interior; the
  prop has no front, so the facing is kept right without being visible.
- 🔴 **The first build closed five ends on the neighbour's ground.** An owned run that crosses the
  line is kept whole (`P5-7`), so its far end has degree 1 in *this* graph and stands at a junction
  in the neighbour's: COTTON PATH `e691` ends 51 m past the line in Causeway Bay, TUNG LO WAN ROAD
  `e1` 37 m inside Wan Chai. A signed distance to the nearest side read them as on the line. The
  test is the unsigned distance and the point within the rectangle grown by the reach; `verify_fence.gd`
  re-derives the whole set from `edges`, `foreign_edges` and the document's own `region_extent_m`
  (never `bounds_game`, the content's union) and a wrong edge either way fails it — mutation-checked
  three ways: an edge dropped, an interior edge added, the rectangle shrunk.
- **Left open on purpose:** the 9 + 2 level −1 tunnel ends on the line (behind their own touchdown
  closure, `Q21`), a fenced edge's line end (behind its mouth, `ends_with_no_way_in` counts it),
  and cul-de-sacs inside the region. The far ends of crossing runs get nothing here; when both
  regions are resident the neighbour's own graph carries on from them.
- **Cost.** 239 + 61 units, +45,888 / +11,712 triangles on the one static `MultiMesh`; draw calls
  unchanged. Wan Chai's barrier layer is now 60,672 triangles — 20% of the mobile `< 300k` budget,
  the figure `fence.py`'s docstring said to have on hand. Every pre-existing row is byte-identical.
  `tools/reachability.py --refuse` on the fenced set is unchanged (0 pairs lost).
- **Frames.** `build/driver/clip_{before,after}_{1,2}/` — Convention Avenue `e573` at the western
  line from `--camera=34,7,256 --look=4,4.3,254.6`; each pair hash-identical, the rows across three
  streets in the after frame and open road into the void in the before.

**See.** `Q19` · `Q103` · `P5-7` · `.claude/rules/fence.md` · `PLAN.md` `P3-29a`
