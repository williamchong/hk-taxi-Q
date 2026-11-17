# Art Design

## Direction

**Low-poly, flat-shaded, saturated. Accurate city, toy vehicles.** Stylise the actors, not the
stage: recognition is the product, and stylised proportions destroy it (`Q8`).

- **City:** real massing and position, real street layout, flat per-building colour, an ink
  outline in each surface's own hue.
- **Vehicles:** die-cast toys. The taxi's body is a 1:64 Tiny City Crown Comfort's (`Q190`) on the
  real car's wheelbase, track and wheels (`Q153`) — physics hardpoints and model are one set of
  numbers (`make_vehicle.Chassis`).

The source data (3D Visualisation Map non-textured, iB1000) is extruded volumes with no textures,
which is already a flat-shaded low-poly building. Untextured vertex-coloured meshes merge into one
mesh per tile, which is what holds draw calls (`PROGRESS.md` owns the budget figures).

- The bundle is not image-free: the sign lettering atlas ships (`Q68`). `mesh_contract.gd` admits
  an image only where a call site names a pixel budget (`Q63`).

## Palette

**The rule (`Q33`):** every authored colour is a real material's diffuse albedo and declares the
published range it comes from. The `materials:` table in `etl/config/hong_kong.yaml` holds every
colour the city ships and is the authority; `buildings:` and `roads:` reference entries by name.
`config.py` refuses a colour outside its `bounds:`, an unused material, and
`test_no_colour_escapes_the_materials_table` fails on a `#rrggbb` anywhere else.

- **Authored is not rendered.** The game multiplies `COLOR_0` by the global shader parameter
  `exposure_anchor`, set by `scripts/world/lighting_rig.gd` from the rig (0.52, `Q38`). It does not
  move with the hour.
- Correct a colour that falls outside its bounds; never widen the bounds.
- The five façade materials (`render_warm`, `render_pale`, `tile_neutral`, `render_cool`,
  `panel_grey`, 40–48%) are uncited and set by eye (`Q216`). They are one family at five
  lightnesses (`Q34`); do not rename `panel_grey` to anything glazed.
- `asphalt_aged` looked like a hole against its neighbours and was right against published
  albedo (7–12%): judge a colour against its referent, not its neighbours.
- `sea_water` is the harbour's diffuse albedo and renders near-black alone; the blue is the sky
  reflected off `tuning/water.tres`'s roughness. Do not lighten the entry.
- Vegetation sits at the top of the 5–15% leaf range (`tree_foliage`, `palm_frond`, `Q171`); a
  darker canopy read near-black in its own shade. `park_grass` stays deeper.
- `COLOR_0` is authored in sRGB and every consumer must linearise it (`Q27`).

**Anchors:** warm off-white, beige and pale grey-green buildings; dark warm grey road (HK asphalt
reads warm, not blue-grey); bright white and saturated yellow markings; the player taxi **red with
a silver roof** (HK Island urban taxi, non-negotiable); cream minibus with a green roof; green and
white tram.

### Per-building colour

- A surveyed building carries its own measured hue, read offline from the individualised set's
  photo atlases and joined on the building id's stem. It lands in `COLOR_0`; switch and strength
  are `buildings.facade_hue` in the config, conversion `etl/pipeline/colour.py`.
- **Hue is taken, lightness refused**: `L*` spread within one building is 22.9 mean against 16.25
  between buildings — the sun confound exceeds the signal. The one exception is the street band
  (`Q197`, `Q240`): its colour and its `L*` step from its own tower ship, shrunk by that band's own
  noise.
- **Material is not a function of height** (`Q34`): height explains 0.9% of façade `L*` and about
  1% of `a*`/`b*`. A surveyed building draws its material from a distribution selected by its
  measured chroma and hue; an unsurveyed one takes the five-step height ramp, a lightness ramp
  only. Do not put colour on `height_bands` and do not re-author the bands from clustered façade
  colour. `tools/ring_weights.py` re-derives the draw weights whenever ramp or survey moves.
- Neighbours draw independently (`Q35`); jitter and the material draw are seeded from the LandsD
  id. Jitter makes a class a ray through its base colour: a tool matching a class by colour must
  test the scale factor, not equality.
- **`facade_hue.strength` ships 3.0**, the user's pick on a sweep (`P5-28d`). At 3.0 one façade in
  three exceeds `C*` 20 and 7.8% are outside sRGB; the mint, teal, lilac and peach blocks are the
  palette, not a fault. "Too grey or too candy" is not one axis (`Q30`): 24.8% sit under `C*` 8
  and 35.2% over 20 at once, and no value of this dial fills the middle. Re-run
  `tools/facade_chroma.py` when strength or survey moves (`.claude/rules/facade.md`).

## Buildings

### The façade shaders

Three looks are files, all reading the same vertex payload (`TEXCOORD_0` = metres along the wall,
metres above the building's base; `TEXCOORD_1` = surface marker + per-building phase, object row;
contract in `ARCHITECTURE.md`). `tools/generated_scene_import.gd` binds the ETL's material to
`tuning/city_facade.tres` only, so switching is a `cp` and a reimport, never a rebuild.

| File | Shader | Look |
|---|---|---|
| `city_facade.tres` (ships) | `city_facade_clean.gdshader` | `Q26` candidate `C`: flat per-building colour, glazing and shopfront shares at 0 |
| `city_facade_elements.tres` | `city_facade_clean.gdshader` | `A‴`: grammar elements on (`Q44`, `Q45`) |
| `city_facade_warm.tres` | `city_facade.gdshader` | `B`: window bands at the measured 2.8 m storey × 2.4 m column |

- `city_facade_clean.gdshaderinc` is the clean shader's body, shared with
  `city_facade_cel.gdshader` (banded sun — built, not shipped: on flat-shaded buildings it only
  moves whole faces 3–6 `L*` and hardens the shadow map's stair, `Q158`).
- `Q26` chose `C` on the user's call. The web build (Compatibility renderer) cannot reopen it
  (`Q76`); that needs a handset round.
- The sidecars (`city_facade*.md`) hold each dial's reason. The `.tres` values are the authority,
  not the shader defaults.

Rules any façade change must keep:

- **The fade must finish before the LOD switch.** `streaming.tres` swaps to LOD1 at 250 m, where
  `TEXCOORD_0.y` comes from a cluster representative and is wrong by up to a storey and a half.
  Check `fade_end_m` (244) against `tier_distances_m`.
- `TEXCOORD_0.y` is metres, never normalised, or a shophouse and a tower get the same row count.
- Do not derive the horizontal coordinate from the face normal — curved façades shatter into
  strips. Project onto a world axis chosen by the normal.
- A band needs analytic antialiasing: past a quarter period per pixel, converge on its duty
  cycle. Geometry too thin to sample is answered by `msaa_3d` 4x (`Q91`).
- An opening is not necessarily glass (`Q43`): where glazing does not dominate, openings are dark
  reveals with a non-zero `unglazed_reflect`.
- Roofs are excluded from the grid but need `roof_darkness`, or a high sun clips every roof white.
- The podium cornice is drawn at iB1000's line, carried on `COLOR_0.a`, and nowhere else (`Q195`).
- Ground normals are averaged by `mesh.collapse`'s height-field path, so the façade shaders
  rebuild a flat normal from screen-space derivatives where the marker is ground (`Q29`). Any
  other ground material must do the same.

### The outline (`Q158`)

Every crease and silhouette carries a thin line in its own surface's hue, darkened — the user's
pick over black ink and over no line. `cel_outline.gdshader` on the rig's `CelOutline` quad
(`visible` is the switch; values in `tuning/cel_outline.tres`): depth-only edges, colour read from
the nearer side at half its linear value, faded out by 240 m, a pale rim at night. One draw call;
it inks everything on screen. Vehicles add detail lines from their own mesh (`Q196`, `Q232`).

### What buildings will not get

- **No per-building texture and no atlas.** `mesh.merge` refuses textured meshes, so a textured
  building is its own draw call. An exact-weld LOD0 does not rescue it and costs 30.5 MB and 40% of
  worst-case visible triangles (`Q16`).
- **No photograph's lightness** for a whole building (above).
- **No surveyed window grammar**: the vision reader was withdrawn on cost (`Q102`).

### Hero buildings

Placed via `landmarks.json`; the ETL excludes the source geometry a hero replaces
(`replaces_source_ids`). Heroes bypass `merge` and ship vertex-coloured; colours obey `Q33`.

| Building | Status |
|---|---|
| **HKCEC** | Shipped: the source mesh itself, extracted by `pipeline/landmarks.py`, sliced at photo-measured ribbon elevations and vertex-repainted; ribbons kept only where the building's `A0` atlas confirms glazing (build-time read). Generated, never committed; `triangle_budget` 120,000 |
| **Central Plaza** | Shipped: authored by `tools/make_landmark.py` from surveyed dimensions (`central_plaza.glb`), budget 8,000 |
| Hopewell Centre, Times Square, Wan Chai government slabs | Not built. Times Square is massing and placement only, never rendered text (`Q42`) |

Where identity is the massing (HKCEC), repaint the source; where it is a feature the source
captures badly (Central Plaza's crown and mast), generate. Light texturing of heroes is deferred,
not refused, and would be its own decision record.

## Roads

Each layer's checklist is its `.claude/rules/` file; its dials are a `.tres` with a sidecar.
`marking_paint.gdshader` is shared by arrows, boxes and stop lines; `signs.gdshader` by signs and
lamps.

- **Ribbon:** generated from the road graph, vertex-coloured. `TEXCOORD_0.x` is a lane coordinate,
  `y` metres along; a junction cap identifies itself in `TEXCOORD_1`, not by `U = 0`.
- **Ribbon shader** (`road_markings.gdshader`, `tuning/road_markings.tres`): draws only the
  kerbside double yellow. `draw_lane_lines`, `draw_centre_line`, `draw_pair_join` and
  `draw_bus_lane` are 0.0 (`Q132`, `Q125`, `Q192`): TD's surveyed lines are drawn as geometry by
  `roadmarks.py`, and where TD surveys none, none is drawn. Ribbon markings fade 6 m from a node.
- **Surveyed paint** is lifted geometry, one mesh each, no collider: arrows, box junctions, stop
  lines, crossings, road marks, and the stop and stand boxes with their legends (`Q242`). Other
  road text is held on scope (`Q65`, `Q101`).
- **Kerbs:** low and mountable, 0.15 m riser and 0.5 m lip; the ground tucks under the lip.
- **Tramway:** its own mesh at iB1000's rail positions, `steel_rail`, `tuning/tramway.tres`. It
  reads by `rail_roughness` against the road's. `rail_metallic` stays 0.0 — the only environment
  is sky and metal rendered the rails sky blue; the sheen is the painted sky at `rail_reflect`,
  dimmed with the hour (`Q168`). A lane-space rail is refused (`Q58`: the rails are on the ribbon
  in 18.8% of cross-sections).
- **Railings** (`Q61`): a vertical quad per station on the drawn kerb; the shader cuts balusters,
  posts and rails out of it by integrating coverage per fragment. `ALPHA` is coverage, so there
  is no opacity dial. Three classes (railings, bollards, barriers) share the shader and differ
  only in their `.tres`; `verify_railings.gd` checks the dispatch. `rail_colour` is the lamp
  columns' `galvanised_steel`, dead neutral (`Q215`) — the cool cast is the sky's and stays out of
  the albedo. All dimensions are authored (`Q60`).
- **Lamps, signs, signals:** lanterns light at night (`Q160`) and throw a projected pool on the
  road (`lamp_pool.gdshader`) rather than a light each.

## Infrastructure

Flyovers, ramps, footbridges and podium decks are mesh class `INFRASTRUCTURE`: one flat colour
(`concrete_sooty`) for deck, soffit, pier and parapet, none of the façade treatment, its own LOD
cells so a thin deck keeps its depth.

- Name a class with a tint probe, not from its silhouette.
- **No `structure_soffit_darkness` term** (`Q32`): built and reverted — soffits are 0.42% of the
  audit frame and already 15 `L*` under their deck from `N·L`.
- Do not darken the colour by eye; it needs a material (`Q33`).

## Ground

The source terrain's photo is read at build time for colour and never shipped. Ground is
vertex-coloured, merged into the tile's primitive and its collider, and solid: a driver who leaves
the road drives on the pavement.

- **Colour:** flat `concrete_paving` — the surface is paving and apron, not soil (`Q36`). Do not
  simplify to neutral grey: a less warm albedo renders bluer under the sky. Parks are iB1000 `Site`
  polygons painted `park_grass` (`Q144`); the harbour is `water.glb`.
- **Land-cover classes from the photo — refused** (`Q18`): the photo is ~10 px/m and the ground
  clusters at 4 m; its "water" class is shadow (51.1% on rooftops). A hillside split is refused
  too (`Q36`: high terrain draws 0.000% of the audit viewpoints).
- **The orthophoto does not ship**: a draw call per tile, with real markings, parked cars and
  shadows baked in under the synthetic ribbon.
- **`ground_sink_m` is 0.20** (`tools/ground_clearance.py`): the shallowest value passing both
  gates, 3.3% of carriageway area and 0.36% of road height samples still proud; deeper shows a gap
  under the kerb riser.

## Vehicles

| Property | Target |
|---|---|
| Triangles | 800–2,000; the player's taxi may reach 2,200 for its lettering and boot seam (`Q202`) |
| Materials | One shared `ShaderMaterial` for bodies; the source's per-part slots merge on import |
| Colours | 3–5 flat colours; the taxi's ten are a standing exception (`Q245`) |
| Windows | Flat dark with a painted sky reflection — no probes |

- Generated by `tools/make_vehicle.py` (taxi) and `tools/make_parked.py` (the roster,
  `parked.glb`: the kinds parked and in traffic, detailed inside their footprints, `Q166`, `Q200`)
  into `game/assets/authored/vehicles/`, committed.
- The taxi's arches must line up with the wheel mounts in `taxi.tscn`: physics never reads the
  mesh, so a mismatch looks correct and drives to the old tuning.
- Only the player's car carries a plate and roof-sign lettering, as flat strokes (`Q202`).
- **Body shader** (`vehicle_body.gdshader`, `tuning/vehicle_body.tres`): a surface marker in
  `UV.y` gives glazing, lenses and paint a three-band painted sky chosen by the reflected ray's
  elevation; a single flat reflection colour reads as a swatch. Paint gloss is the engine's
  clearcoat lobe added over the paint (`Q215`), and since `Q248` a share of the painted sky mixed
  into the albedo again over crowned panels, on the user's pick: it costs the red `C*` 4.0 in sun,
  and red identifies 紅的.
- **Comic line** (`Q248`): every vehicle's detail lines are black, and a 1 cm black outline is
  drawn round it by a second pass (`vehicle_outline.gdshader`). The city keeps `Q158`'s outline
  in its own hue.
- **Lamps** (`vehicle_lamps.gd`, `tuning/vehicle_lamps.tres`): `UV.x` carries a circuit id per
  lens, written per instance. Rear lamps read the car, front lamps read the light, and the roof
  sign reads the fare — lit for hire, dark with a passenger. Emission is the lens's hue at a fixed
  intensity; more emission past the tonemap shoulder is only more white. Moving vehicles throw a
  headlamp beam at night (`Q213`); public transport's windows light (`Q177`).
- One player car ships (`tuning/cars/crown_comfort.tres`); a FWD Crown and a Hiace are not built.

## Lighting

One rig, `scenes/world/clean_daylight.tscn`, named by every scene. `golden_hour.tscn` is kept and
unused.

- One directional sun with two shadow cascades to 400 m; a phone pulls the reach in
  (`phone_shadow_max_distance_m`) and draws 3D at `phone_scale_3d` (`Q236`). One cascade showed an
  artefact at every distance.
- Gradient sky ambient — no HDRI, no probes, no GI, no SSAO. Resist adding lights.
- **The day runs to night as game time** (`Q160`, `Q222`): one rig blending keyframes in
  `tuning/day_to_night.tres` (morning, noon, afternoon, dusk, twilight, night, dawn), never two
  rigs cross-fading. Night is a realistic one with lit touches — lantern pools, floodlit blocks,
  lit paint, the pale outline rim. A lit layer multiplies the rig's `night_lights`; nothing lights
  by day. `lit_window_share` ships 0.0; neon signage is not built.
- Shade is lit by the street (`Q215`): sky contribution 0.4, the rest a warm grey bounce. A
  saturated sky paints dark asphalt blue; do not reach for the road palette.
- `adjustment_contrast` stays at 1.0 (`Q31`): Godot's contrast pivots about mid-grey and at 1.14
  it crushed half the shaded `kerb` frame under `L*` 10. Raise the ceiling, never the floor.
- A washed-out frame is not evidence about the lights. Grade a pair of renders with
  `tools/frame_stats.py` and ask first whether an albedo change reaches the screen.

## LOD policy

Tiers are generated by the ETL by vertex clustering on grid cell and facing (position alone
rounds the hard normals; quadric decimation smooths corners the style wants kept).

| Tier | Distance | Cell size |
|---|---|---|
| LOD0 | 0–250 m | 1.5 m (infrastructure 0.5 m, terrain 4 m) |
| LOD1 | 250–400 m | 4.0 m (infrastructure 1.0 m, terrain 8 m) |

- Values: `lod_cell_sizes_m`, `class_lod_cell_sizes_m`, `tuning/streaming.tres`.
- No exact-weld tier (`Q16`): side by side the user could not tell, for 30.5 MB of bundle.
- Anything smaller than a cell disappears and anything thinner flattens, hence per-class cells. A
  class is collapsed at its own cell and the tile merged afterwards — still one draw call.

## UI

Hong Kong road signage and the taxi meter; `tuning/hud_style.tres`, `hud_layout.tres` and
`.claude/rules/hud.md` are the authority.

- Minimap and street plate bottom-left, speed dial bottom-right (`Q138`), flat chamfered panels in
  one dark housing (`Q139`, `Q163`). The fare is the 咪錶's red seven-segment LED.
- Bilingual throughout. Three hands (`Q218`): a brush for the menu, 黑體 for interface, Free HK
  Kai (`Q79`) for names.
- The wrong-way NO ENTRY disc carries the world sign's measured proportions (`Q81`).
- High-contrast for daylight phone use; safe areas respected.

## Audio direction

Built (`.claude/rules/audio.md`): engine, tyres, crashes by what was hit, horns per vehicle kind,
the meter's flag and beep, the tram bell, the payout. Not built: minibus whine, bilingual
passenger callouts (Cantonese primary), ferry horn, radio stings.

## The audit viewpoints

Fixed cameras, so a look change is judged against the last one. All run through
`.claude/skills/run-hk-taxi-q/drive.sh` (flags in its `SKILL.md`).

| Name | Scene | Camera → look | Evidence for |
|---|---|---|---|
| `street` | preview | `270,5.5,691` → `30,4.5,719` | Hennessy Road canyon: façade colour at eye level |
| `skyline` | preview | `520,130,180` → `520,45,640` | Massing and silhouette over the harbour |
| `kerb` | preview | `283,6,684` → `300,3.2,700` | Causeway Bay in shade: the value gap, the chroma tail |
| `ground` | preview | `400,45,300` → `250,0,60` | The waterfront reclamation and the region edge |
| `infra` | preview | `1010,9,890` → `930,13,800` | Canal Road flyover from beneath |
| `taxi` | drive | `--seconds=6 --shots=1.2,4.5 --hold=accelerate@0.3+4` | The car in shade and in sun |
| `aerial` | preview | `850,620,1750` → `850,10,400` | The whole region; a fog check |

- Use `--debug-view=off`. Preview shots still carry `road_preview.gd`'s polylines and arrows.
- A run can stall (`no frame drawn`); it exits 1 with no frame. Retry; conclude nothing.
- A click on the run window captures the mouse and rotates the camera while the run still exits
  `DRIVER OK`. Shoot each viewpoint twice and compare.
- A screenshot verdict expires with the next palette commit (`Q29`): say which commit a shot is of.

## Anti-goals

Revisable with evidence; each reason is load-bearing.

- **No photorealism, texture-map PBR workflow or reflection probes.** Not anti-physics: `Q33` is
  PBR's albedo discipline as data, and the shaders write roughness and fresnel. Metalness has
  nothing to reflect on the Mobile renderer (no SSR, no probes).
- **No photogrammetry textures in the bundle.** The reason is the look and the structural
  blockers, not size or licence. Reading one at build time to derive a flat colour is allowed.
- **No per-building textures and no building atlas.** The reason is `merge`, not memory or UVs.
- **No realistic weather or wet-road reflections.**
- **No baked illumination.** A lightmap is blocked by texel budget, the moving sun and LOD1
  carrying none across the 250 m switch. Raising `meshes/light_baking` to Static Lightmaps would
  regenerate UV2 over the tiles' `TEXCOORD_1` payload; `verify_tiles.gd` asserts the setting.
  Baked ambient occlusion alone is not refused.
