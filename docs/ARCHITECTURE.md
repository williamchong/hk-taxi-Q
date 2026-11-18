# Architecture

Per-stage rationale is in `.claude/rules/<name>.md` and `docs/DECISIONS.md` (by `Q` / task ID);
per-resource rationale in the sidecar `.md` beside each `.tres` / `.tscn`.

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Engine | Godot 4.7 (CI pins `4.7.1-stable`) | MIT, no royalties |
| Renderer | Mobile; Compatibility on web | Forward+ only if a desktop tier ever justifies it |
| Physics | Jolt | Trimesh collision; the car is a `VehicleBody3D` whose tyre force is `TyreVehicleController`'s (`Q50`, `Q152`) |
| Game language | GDScript, statically typed | C# has no web export and experimental mobile export. Escape hatch is GDExtension, never C# |
| ETL | Python 3.11+: numpy, pyproj, pyyaml, pyogrio, shapely, pillow, pypdfium2 | Build-time only; no system GDAL/GEOS (`Q129`) |
| Targets | iOS, Android, desktop, web demo | |

### The importer can reinstate `VehicleWheel3D`

Godot's glTF importer converts nodes by name suffix: `_wheel` becomes a `VehicleWheel3D`, and
`_col`, `_convcol`, `_navmesh`, `_occ`, `_rigid`, `_vehicle` likewise, with no error. The tyre mesh
is `taxi_tyre.glb` and must stay so: it is a child of a real `VehicleWheel3D`, and a rename to
`taxi_wheel.glb` nests a wheel in a wheel. When geometry goes missing, check the instantiated tree.

---

## Project settings

`game/project.godot`, `export_presets.cfg`, every `.tres` and `.tscn` are committed in the form the
editor's writer produces, so an editor save is a no-op (`Q119`). The writer drops comments and omits
any key equal to its default; such a key stays in force.

- Rationale lives in this table (config) or a sidecar `<name>.md` (resource), never in the file.
- Values are asserted by `game/tools/verify_settings.gd`, read back through `ProjectSettings`.
- A full scene save takes two passes: a scene saved before the scene it instances has a uid does
  not carry that uid.
- A typed node export (`@export var camera: Camera3D`) needs `node_paths=PackedStringArray(...)` on
  the node line or it reads null from a hand-authored scene. References to the `InputRouter`
  autoload stay `NodePath`, because `node_paths=` resolves inside the scene only.
- Headless runs leave both config files byte-identical. A dirty `project.godot` is a real change.

| Setting | Value | Why |
|---|---|---|
| `application/config/name` | `Hong Kong Taxi Ace` | `Q208`; `name_localized` has `zh_HK` 香港的士車神. Kept in step by hand with `menu_text.json`'s `title` and the Android preset's `package/name`. A desktop names `user://` after this key |
| `application/boot_splash/image`, `bg_color` | `assets/authored/loading/boot_splash.png`, `HudStyle.plate_field` | The loading cover's still (`Q209`, `tools/make_splash.py`); `verify_menu` holds both |
| `application/run/max_fps.mobile` | `60` | Desktop uncapped. The player's FRAME RATE pick replaces it on a phone (`Q223`) |
| `display/window/size`, `stretch/mode`, `stretch/aspect` | 1920 × 1080, `canvas_items`, `expand` | Resolution-independent UI over the HUD's design frame |
| `display/window/handheld/orientation` | `4` (sensor landscape) | Either landscape, never portrait (`Q224`); `HudLayout.inset_for_safe_area` gives both sides the larger inset |
| `rendering/renderer/rendering_method` | `mobile` | Locked decision. `.web` is `gl_compatibility` by engine default: absent from the file, asserted anyway |
| `rendering/textures/vram_compression/import_etc2_astc` | `true` | Required to export any arm64 target |
| `rendering/anti_aliasing/quality/msaa_3d` | `2` (4x) | A sub-pixel stripe breaks into dashes without it (`Q91`). Fill-rate cost, invisible to draw-call counts. Never 8x: WebGL2 `MAX_SAMPLES` is 4 |
| `rendering/anti_aliasing/quality/msaa_3d.mobile` | `1` (2x) | The phone app only: 270.4 → 235.9 MB video memory on an iPhone Air (`Q236`). Railing shimmer in motion is the user's to judge on the handset |
| `rendering/occlusion_culling/use_occlusion_culling` | `true` | Reads the tiles' `-occonly` occluders. Stock web templates cannot cull (`Q122`) |
| `physics/3d/physics_engine` | `Jolt Physics` | Locked decision, stated so an engine default change is not followed silently |
| `[importer_defaults] scene.import_script/path` | `res://tools/generated_scene_import.gd` | Dispatches materials by name; glTF cannot express them. A default because generated `.import` files are gitignored |
| `[importer_defaults] scene.meshes/force_disable_compression` | `true` | Godot quantises positions over the mesh's AABB: 0.025 m steps on `lamps.glb` against a 0.06 m arm (`Q82`). +2.0% PCK. The taxi body, tyre and `central_plaza.glb` imports keep `false` deliberately |
| `[importer_defaults] scene.meshes/generate_lods` | `false` | The ETL ships the tiers; −8.6% PCK (`Q120`) |
| `[shader_globals] exposure_anchor` | `float` `1.0` | The rig's exposure (`Q38`, `Q33`), set by `LightingRig`. Applied after `vertex_srgb_to_linear`, never to a `.tres` colour. Type pinned: an undeclared global resolves to zero (black city, green checks), an `int` truncates |
| `[shader_globals] outline_speed` | `float` `0.0` | Car speed as a share of `car_outline.tres`'s `full_speed_kph` (`Q158`). One writer: `car_outline.gd` on the player's car |
| `[shader_globals] sky_light`, `night_lights` | `vec3 (1,1,1)`, `float 0.0` | The rig's hour (`Q160`): reflected sky, and the scale of every lit layer. Defaults are noon |

`[importer_defaults]` seeds only a newly created `.import`. After changing a key, delete the sidecars
and re-import; `check.sh`'s `sidecars` step fails a stale one.

Deliberately not set: `directional_shadow/soft_shadow_filter_quality` (Godot ships a `.mobile`
override of 0, so a base value only degrades desktop) and `directional_shadow/size` (8192² costs
134 MB against a 512 MB budget). Cascade count and distance are properties of the rig's sun.

`run/main_scene` is `scenes/main.tscn`. `[input]` deadzones are 0.2 on axes, 0.5 on buttons.

**Autoloads** (three; hot-path code):

- `DebugHud` — every dev readout.
- `InputRouter` — the one reader of raw input. Reached by `NodePath` (`^"/root/InputRouter"`),
  never by global name.
- `BeamBudget` — the renderer-global spot-light cap.

Deliberately not autoloads: `RoadGraph.shared()` (a static `WeakRef`, parsed once per scene and
dropped with it, `Q124`), `Cmdline` (the one reader of the command line) and `Settings`
(`user://settings.cfg`). `Locale.language()` reads `--lang=`, then the saved setting, then the OS.
`RunSave` (`user://run.cfg`, `Q253`) is the run in play, written by `Main._save_run` and read back by
CONTINUE through `DriveLevel.continue_run`; a scripted run never writes or reads it.

Game flags follow `--` and are read through `Cmdline`; each is documented at its reader
(`grep -rn '"--' game/scripts`). The ones scripted runs use: `--region=`, `--menu=off`,
`--debug-view=`, `--hud=off`, `--minimap=off`, `--lang=`, `--fares=off`, `--fare-seed=`,
`--traffic=off`, `--trams=off`, `--time-of-day=`, `--touch=`, `--perf-log=`.

### `export_presets.cfg`

Four presets: macOS, Web Demo, Android (arm64 only), iOS. Committed comment-free. Never put keystore
passwords, provisioning profiles, signing identities or the App Store Team ID in it.

| Setting | Value | Why |
|---|---|---|
| `exclude_filter` (all four) | `tools/*`, `scenes/dev/*`, `scripts/dev/*`, `assets/authored/fixtures/*`, `assets/authored/greybox_wanchai.json` | The dev tree stays out of the PCK; the four move together |
| `application/bundle_identifier` (macOS, iOS), `package/unique_name` (Android) | `cloud.williamchong.hktaxiq` | Move together. Permanent once published |
| `shader_baker/enabled` (iOS) | `true` | First frame in ~12 s on an iPhone Air instead of none in 260 s (`Q207`). Others `false` until a handset measures them |
| `storyboard/image_scale_mode` (iOS) | `2` (Scale to Fit) | Matches the boot splash's fit, so the taxi does not shrink at the hand-over (`Q209`) |
| `application/export_project_only`, `app_store_team_id` (iOS) | `false`, empty | `tools/ios.sh` sets both for the length of an export and restores the file |
| `variant/thread_support` (web) | `true` | The host must serve cross-origin isolation headers |

The shader baker fails silently (unbaked PCK, exit 0) on a `--headless` export, which has no GPU,
and without Apple's Metal toolchain (`xcodebuild -downloadComponent MetalToolchain`). A baked PCK
holds `.godot/shader_cache/*.metal.cache` entries; `tools/ios.sh` refuses one without.

### The debug overlay

`DebugHud` (`scripts/ui/debug_hud.gd`). `F3` cycles off → minimal (position block, frame counter) →
full (registered readouts, 3D debug geometry); `--debug-view=` sets the start, and `off` is the
default in every build. `F3` is a raw key, so `drive.sh --hold=` cannot press it; `drive.sh`
(`.claude/skills/run-hk-taxi-q/`) appends `--debug-view=minimal` unless told otherwise. The player's
HUD is separate: a clean art frame needs `--debug-view=off` and `--hud=off`; `--minimap=off` takes
the map alone (`Q136`).

---

## Checks

Godot never signals failure through its exit code: a parse failure or promoted warning prints and
exits 0. `tools/check.sh` turns that output into an exit code. **Exit 0 means every step passed;
exit 1 means at least one printed `FAIL`.** Do not run the steps by hand and read the output.

Steps in run order. No Godot process may run before `--import`: a `class_name` resolves only from
the cache the import writes.

| Step | Covers | In CI |
|---|---|---|
| `instructions` | Root `CLAUDE.md` ≤ 40,000 characters | yes |
| `gdformat` | `gdformat --check game/`; 0 files checked is a failure | yes |
| `tuning` | Every `game/tuning/**/*.tres` and `game/scenes/**/*.tscn` has a non-empty sidecar `.md` unless `UNDOCUMENTED_OK` names it; no `;` line in a resource; no orphan sidecar or stale exemption | yes |
| `import` | `--headless --import`; builds `game/.godot/` | yes |
| `settings` | `verify_settings.gd`: the 21 warning promotions, pinned values, shader globals, the three `[importer_defaults]` keys | yes |
| `sidecars` | Every `*.glb.import` under `assets/generated/` and `assets/authored/` carries the pinned `meshes/*` keys. 0 sidecars passes (a clone has no city) | yes |
| `warnings` | `--check-only` per script, grepping `treated as error\|Parse Error`; the swept count must equal the script count | yes |
| Always tools | `verify_beam_budget`, `verify_vehicle`, `verify_mesh_contract`, `verify_hud`, `verify_input`, `verify_authored`, `verify_menu`, `verify_day_cycle`, `verify_perf_recorder`. No built region needed | yes |
| Region tools | Once per region in `regions.json` (`--region=`): `verify_city`, `verify_tiles`, `verify_road_surface`, `verify_road_graph`, `verify_city_streamer`, `verify_spawn`, `verify_landmarks`, `verify_fence`, `verify_tramway`, `verify_arrows`, `verify_boxjunctions`, `verify_crossings`, `verify_stopmarks`, `verify_stops`, `verify_railings`, `verify_signs`, `verify_roadmarks`, `verify_lamps`, `verify_fares`, `verify_water`, `verify_parked`, `verify_trees`, `verify_planters`, `verify_paths`, `verify_backdrop`, `verify_signals`, `verify_traffic`, `verify_trams` | no |
| `verify_join` | The runtime merge of the first two synced regions against `pipeline/join.py`; SKIPs on one region | no |

- `VERIFY_GENERATED=0` skips the last two rows and says so (CI sets it).
- `CHECK_JOBS` (default: cores, capped at 8) pools the sweep and the region tools; `CHECK_JOBS=1` is
  serial. `verify_road_graph` runs first and alone (`CLOCKED_TOOLS`): it gates on microsecond budgets.
- A Godot step fails on a non-zero exit or on `Parse Error|SCRIPT ERROR|Failed to load
  script|Failed to compile` in its output.
- `verify_road_graph` and `verify_join` need `reachability.json` beside each graph
  (`etl/out/<region>/`, `etl/out/<a>+<b>/`), written by `tools/reachability.py --region <r>
  [--graph-dir <dir>] --json`. Missing or stale FAILs, naming the command. After moving a region,
  rebuild the join (`python -m pipeline.join`) first.

Traps:

- A verify tool that hangs is usually a parse error: `_init` never runs, `quit()` is never called.
  Give scripted Godot runs a watchdog. Tools extend `game/tools/verify_tool.gd` by path (`_expect`,
  `_fail`, `_finish`, `_start_watchdog`); the per-layer tools run through `verify_layer.gd`.
- Verify tools `preload` every dependency and never name a `class_name` global: on a fresh clone the
  global cache does not exist, the tool fails to parse, and Godot exits 0.
- Autoloads register on the first frame; a tool that loads a scene awaits `process_frame` first.
- A verify tool proves an asset is correct, not that it renders (`Q73`). A new layer needs its node
  in `scenes/region.tscn` (`verify_city.gd` holds the `layer` ids both ways) and a frame looked at.
- `check.sh` exits 0 on a shader that fails to compile. A shader change owes a render and
  `grep -i "shader error"`.
- A headless `--import` re-tabs `game/assets/authored/greybox_wanchai.json` (`Q115`). Restore it
  after `check.sh`; never commit it.
- Exports are byte-deterministic given a clean `project.godot`. Bundle size is measured from a PCK,
  never summed from source files.

### Grading tools

`tools/battery.py <trigger> --region <r> --before <checkout root> [--jobs 4]` runs a trigger's
graders on this checkout and on a before build, saves outputs under `build/battery/` and writes a
diff per item. `--list` prints the table. **Its exit code says every item ran, never that a number
held.** Both sides are graded by this checkout's tools unless `--tools-from side`.

Triggers: `arrows`, `backdrop`, `boxjunctions`, `busroutes`, `carve`, `collider`, `crossings`, `fence`,
`lamps`, `lanes`, `off-grade`, `parked`, `paths`, `planters`, `q19`, `railings`, `region`, `roadmarks`, `signs`,
`stopmarks`, `stops`, `surface-region`, `width`. Not in the table: anything needing a frame, a
drive, a sweep of a free value, or `tools/skidpad.sh`.

Graders read back what shipped and share no code with the pipeline:

- `deck_error.py` (`Q20`), `overhang.py` (`Q22`/`Q23`), `ground_clearance.py` (`Q18`/`Q24`),
  `paint_clearance.py` (`Q92`), `lane_paint.py` (`Q113`/`Q114`; reads the synced bundle),
  `cap_pavement.py` (`P3-31`; grades, never gates), `kerbside_error.py` (`Q54`; reads the ETL out
  tree).
- `carriageway_occupancy.py` (`Q19`) gates and fails today; `clearance_reconcile.py` ratchets it
  against `clearance.py`'s own number (`Q51`).
- `narrowing.py` prices a lower `surface.floor_default_m` by importing `pipeline.clearance` whole;
  it refuses to print unless its baseline reproduces `clearance.json` edge for edge.
- Shared code is `tools/_lib/` (`bundle`, `ribbon`, `streets`). Graders read tiles through
  `gltf.read_render`, which drops helper primitives; reading the file whole counts walls twice.

### GDScript warnings

`[debug]` promotes 21 warnings to errors (level 2, the only level that reaches stdout). Three
default to error in 4.7, so the writer omits them; `verify_settings.gd` names all 21. Never edit
the list down to match a regression (`Q72`).

The enforced list is `verify_settings.gd`'s `PROMOTED`. Not enforced: `inferred_declaration` (`:=` is
static typing); the `unsafe_*` family and `return_value_discarded` (generated JSON arrives as
`Variant`).

### GDScript formatting

`gdformat` (from `gdtoolkit`, the `dev` extra in `etl/pyproject.toml`); its default line length of
100 matches `ruff`. `gdlint` is not wired in: it cannot check static typing.

### CI

`.github/workflows/ci.yml`, on push to `main` and every PR: `ruff check .`, `ruff format --check .`
(repo root) and `pytest` (in `etl/`) on Python 3.11 and 3.13; and `tools/check.sh` on Godot
`4.7.1-stable` with `VERIFY_GENERATED=0`. Checkout needs `lfs: true`. CI never runs the ETL (a
~320 MB government download).

---

## Repo layout

```
CLAUDE.md, .claude/rules/   agent instructions; change-scoped checklists
docs/
etl/config/hong_kong.yaml   the tunable city facts
etl/pipeline/               __main__.py (STAGES, NEEDS), config.py + config_blocks/ (the only route
                            config takes in), hongkong.py (Q100), one <stage>.py per stage, and
                            shared modules (crs, gdb, gltf, mesh, placements, drawnroad, …)
etl/sources/, etl/out/      downloads and output, gitignored
etl/tests/
game/scenes/                main.tscn, city_drive.tscn, region.tscn, vehicle/, world/ (rigs), dev/
game/scripts/               main.gd, core/ city/ level/ vehicle/ traffic/ fares/ input/ ui/ camera/
                            world/ dev/
game/assets/                generated/ (gitignored), authored/ (committed, LFS), shaders/
game/tuning/                .tres + sidecar .md; cars/, systems/
game/tools/                 import script, verify tools, mesh_contract.gd
tools/                      check.sh, battery.py, sync_generated.sh, export.sh, ios.sh, skidpad.sh,
                            graders, make_* asset scripts; _lib/ is what graders share
fastlane/                   the App Store listing
```

Stage order (29): `fetch`, `podiums`, `basemap`, `buildings`, `landmarks`, `roads`, `carve`,
`region`, `surface`, `clearance`, `fence`, `fares`, `tramway`, `arrows`, `boxjunctions`,
`crossings`, `stopmarks`, `roadmarks`, `railings`, `signs`, `lamps`, `trees`, `signals`,
`tramlines`,
`busroutes`, `parked`, `stops`, `planters`, `paths`, `backdrop`, `export`.

`scenes/dev/` and `scripts/dev/` are not shipped. A fresh clone boots to an empty world with a
`push_warning`, because the level needs the gitignored `assets/generated/`.

---

## Data contract

The interface between ETL and game. Change both sides together and bump `schema_version` where a
consumer would be wrong to keep its old interpretation, not wherever bytes change. Positions are
game-space metres. Each reader holds a `SCHEMA_VERSION` constant matching the writer's.

| Document | Schema | Writer | Reader |
|---|---|---|---|
| `city.json` | 51 | `export.py` `CITY_SCHEMA` | `scripts/city/city_manifest.gd` |
| `roadgraph.json` | 15 | `roads.py` | `generated_road_graph.gd`, `road_graph.gd` |
| `fares.json` | 1 | `fares.py` | `generated_fares.gd` |
| `landmarks.json` | 2 | `export.py` | `generated_landmarks.gd` |
| `fence.json` | 3 | `fence.py` | `generated_fence.gd` |
| `basemap.json` | 3 | `basemap.py` | `generated_basemap.gd`; `shore.py` and `buildings.py` in the ETL |
| `*_placements.json` | 1 | `placements.py` | `generated_placements.gd` |
| `signals_plan.json` | 1 | `signals.py` | `scripts/traffic/signal_plan.gd` |
| `tram_lines.json` | 1 | `tramlines.py` | `scripts/traffic/tram_lines.gd` |
| `bus_routes.json` | 1 | `busroutes.py` | `scripts/traffic/bus_routes.gd` |
| `regions.json` | 1 | `tools/sync_generated.sh` | `generated_regions.gd`; `far` lists the regions synced for their far version alone |
| `backdrop.json` | 2 | `backdrop.py` | `city_regions.gd`, for a region in `regions.json`'s `far`: its `city_offset` |

Not part of the contract: `roadsurface.json`, `carriageway_region.json`, `podiums.json` and the
per-stage reports (`buildings.json`, `clearance.json`, `signs.json`, …). The game reads none, and
`sync_generated.sh` copies only what the manifest names.

### `city.json` — manifest

```json
{
  "schema_version": 46, "city_id": "hong_kong", "region_id": "wan_chai",
  "source_crs": "EPSG:2326",
  "origin": { "easting": 835765.0, "northing": 816125.0, "elevation": 0.0 },
  "city_offset": [38379.0, 0.0, 32826.0],
  "bounds_game": { "min": [-32.0, -13.049, -73.571], "max": [1704.698, 378.532, 923.142] },
  "tile_size_m": 150,
  "tiles": [{ "id": "t_00_00", "lods": ["tiles/t_00_00_lod0.glb", "tiles/t_00_00_lod1.glb"],
              "aabb": [[8.37, 4.9, -16.6], [167.6, 70.8, 165.3]], "occluder": [true, true] }],
  "road_surface": [{ "id": "t_00_00", "file": "roads/t_00_00.glb", "aabb": [[], []] }],
  "carriageway": [{ "edge": 651, "half_width_m": [5.12, 4.32], "clear_width_m": [-1.0, 8.5],
                    "corridor_half_width_m": [7.4, 7.1], "corridor_offset_m": [2.1, 1.8],
                    "lanes_painted": 2, "trim_m": [5.4, 6.1], "stub": false }],
  "lane_width_m": 3.2, "car_width_m": 1.695,
  "landmark_assets": ["landmarks/hkcec.glb"], "taxi_licences": {},
  "road_graph": "roadgraph.json", "tramway": "tram.glb", "...": "one key per document or asset",
  "etl_version": "0.1.0", "generated_utc": "..."
}
```

- Required: `DOCUMENT_KEYS` (`road_graph`, `fares`, `landmarks`, `fence`, `basemap`) plus `tiles`,
  `road_surface`, `landmark_assets`, `bounds_game`. `fence` and `basemap` are written on every run;
  an empty document means nothing to draw, a missing one means the stage never ran.
- `OPTIONAL_ASSET_KEYS`, each nullable: `tramway`, `arrows`, `arrows_placements`, `boxjunctions`,
  `crossings`, `stopmarks`, `stops`, `stops_placements`, `planters`, `paths`, `backdrop`, `lamps`, `lamps_placements`, `railings`, `railings_placements`, `signs`,
  `signs_text_atlas`, `signs_placements`, `roadmarks`, `water`, `parked_placements`, `trees`,
  `trees_placements`, `signals_plan`, `signal_heads_placements`, `tram_lines`, `bus_routes`. Null
  where the estate publishes no such layer or every feature failed the join; a stage names its
  asset from what it drew. `city_manifest.gd`'s `shipped()` mirrors the list in order.
- `taxi_licences` (`Q183`): each taxi licence's mesh in `parked.glb` to its share of the region's
  taxis; `{}` where no stand lies in the region. Never null.
- The game finds its files through the manifest only: an exported `res://` is a PCK that
  `DirAccess.get_files_at` will not enumerate.
- `bounds_game` is the union of the content, not the region rectangle (Wan Chai: 1650 × 887 m
  declared, 1737 × 997 m drawn).
- `generated_utc` is the only field that differs between two builds of identical inputs.

`carriageway[]` — one row per edge, one value per station of that edge's `roadgraph.json` polyline.

- `half_width_m` is the drawn half-width, which the game cannot derive. It can equal `width_m / 2`
  (`Q95`): assert "not narrower", never "wider". `verify_road_graph.gd` treats a missing table as
  an error.
- A level-0 row is the edge's territory, its share of a carriageway several centrelines may share,
  not the road kerb to kerb (`Q129`). Those rows also carry `corridor_half_width_m` (half the
  kerb-to-kerb corridor `clear_width_m` is measured across), `corridor_offset_m` (that corridor's
  centre off the centreline, up to 7.71 m) and `lanes_painted`. `clear_width_m` can exceed
  `2 × half_width_m` there. Off-grade rows publish no corridor; `RoadGraph.corridor_half_width_of`
  falls back to the ribbon.
- `clear_width_m` (`Q51`): the widest continuous gap at that cross-section between 0.30 m and
  2.00 m above the deck. `-1.0` means no cross-section judged, never zero.
- `lane_width_m` and `car_width_m` are two bars over `clear_width_m`, never merged (`Q19`): traffic
  is routed on the first (`RoadGraph.is_passable`), the player is fenced at the second
  (`RoadGraph.fits_car`). `car_width_m` is null where no `clearance:` block is declared.
- `trim_m` is `[start, end]`, where each end's ribbon meets its junction cap. `stub` is true where
  both ends lie in one junction cluster; the traffic turns mouth to mouth and never drives a stub.
- Lane lines along a road are geometry in `roadmarks.glb`; `road_markings.tres` draws neither lane
  dashes nor a centre line (`Q132`). The two halves ship together.

#### Tiles

`lods` is nearest-first, one file per tier of `buildings.lod_cell_sizes_m` (`[1.5, 4.0]`), with
per-class overrides in `class_lod_cell_sizes_m`. Classes are collapsed separately then merged: one
mesh, one material, one draw call, no texture.

- The ground is decimated before it is tiled (`Q25`); cutting first tears it.
- `tiles[].aabb` is the union of the tiers shipped and can exceed the tile (buildings are assigned
  whole, by centre). Cull and stream by `aabb`, never grid position.
- `game/tools/mesh_contract.gd` walks every shader uniform and fails on any `Texture`; a data map
  sampled by world position is an amendment to this contract.

| Attribute | Meaning |
|---|---|
| `COLOR_0.rgb` | Albedo, sRGB-encoded `uint8`; every consumer linearises it. Not one colour per object: a surveyed building's bands carry their own hue (`Q197`) |
| `COLOR_0.a` | The podium line (`Q195`), constant per source object: codes 1–254 are metres above the object's base in 0.5 m steps (`buildings.PODIUM_STEP_M`); 255 is no line, and the shader reads 0 as no line too. Not opacity: enabling transparency on a tile renders lined buildings see-through |
| `TEXCOORD_0.x` | Metres along the wall, by the world axis the normal picks (`buildings.along_m`) |
| `TEXCOORD_0.y` | Metres above that source object's own base |
| `TEXCOORD_1.x` | `floor()` is the `SurfaceClass` (0 façade, 1 ground, 2 structure); `fract()` a per-object phase in 1/256 steps |
| `TEXCOORD_1.y` | The object row: an integer indexing the mesh `extras` table |
| Mesh `extras` | `{"objects": [{"id", "class", "aabb"}, …]}`, one row per source object in the tier. Read by `building_index.gd` (`object_at`); `ROW_SLACK_M` is 8 m. Custom `_` vertex attributes are dropped by the importer |
| Material name | `city_facade` → `tuning/city_facade.tres`. The name is the contract; `generated_scene_import.gd` dispatches on it |

- ETL material name, import script and shader must agree; a broken link fails silently to flat
  vertex colour. Codec constants are contract, never in the city yaml.
- `meshes/light_baking = 2` makes the importer overwrite `TEXCOORD_1` with its own UV2; tiles ship
  `= 1`. `verify_tiles.gd` asserts both.

**Collider.** Only tier 0 collides, through its own primitive `<tile_id>_collision-colonly`,
imported as a mesh-less `StaticBody3D`. Decimated at `buildings.collision_cell_m` (1.5 m, equal to
tier 0 today). Every class collides, the ground included; `buildings.ground_sink_m` (0.20) drops the
ground under the kerb. Helper primitives (collider, occluder, the road chunk's collider) ship
`POSITION`, indices and `TEXCOORD_1` and no `NORMAL`.

**Occluder.** A tier may ship `<tile_id>_occluder-occonly` → `OccluderInstance3D`.
`buildings.occluder_cell_m` is a list parallel to the tiers (`[4.0, 4.0]`; `null` for none), built
from `occluder_classes` (`BUILDING`, `INFRASTRUCTURE`). `city.json`'s `occluder` is parallel to
`lods`. It costs +10.3% of PCK and culls per instance (tile, road chunk, `MultiMesh`); handset CPU
cost is unmeasured (`Q122`).

The carve (`P3-28`, `P3-51`) cuts the render mesh, collider and occluder alike.

**Colour.** `COLOR_0` is sRGB and every consumer linearises it (`Q27`): each shader takes
`vertex_srgb_to_linear` from `assets/shaders/colour.gdshaderinc`, and `generated_scene_import.gd`
sets the `BaseMaterial3D` flags for anything that names no shader. Skipping it gives a pale city
with no error; measure with `tools/frame_stats.py`. A layer is a parameterisation, not a shader
(`Q71`): arrows, boxes and road marks share `marking_paint.gdshader`; railing classes share
`railings.gdshader`; lamps ride `signs.gdshader`.

### `roadgraph.json` — drivable network

```json
{
  "schema_version": 15,
  "nodes": [{ "id": 1, "pos": [120.5, 4.0, 300.2], "kind": "junction" }],
  "edges": [{
    "id": 1, "source_id": 4021, "run": 0, "from": 1, "to": 2,
    "polyline": [[120.5, 4.0, 300.2], [180.0, 4.1, 305.0]],
    "on_structure": [false, false], "structure_bounded": [false, false],
    "direction": "both", "lanes": 3, "lanes_source": "measured", "lanes_forward": 2,
    "width_m": 11.0, "width_source": "two_way_span",
    "width_publisher": "hyd_pavement+ib1000", "width_confirmed_by": "",
    "speed_limit_kph": 50, "bus_lane": false, "tram_tracks": false, "elevation_level": 0,
    "road_name": { "en": "Gloucester Road", "zh": "告士打道" }, "street_class": "main",
    "kerbside": [{ "side": "near", "from_m": 12.4, "to_m": 88.1, "kind": "double" }]
  }],
  "foreign_edges": [{ "id": 7, "source_id": 5310, "run": 0, "foreign": "causeway_bay" }],
  "turn_restrictions": [{ "from_edge": 1, "via_node": 2, "to_edge": 5 }]
}
```

| Field | Meaning |
|---|---|
| `id`, `source_id`, `run` | `id` is a per-region ordinal with gaps: never index `edges` by position. `(source_id, run)` is the identity across regions (`Q116`) |
| `direction` | `both` or `forward` only; the polyline runs the legal way |
| `turn_restrictions` | Edge `id`s; an arm may name a `foreign_edges` entry |
| `speed_limit_kph` | `SPEED_LIMIT` joined on `ROUTE_ID`, else the city default |
| `bus_lane`, `tram_tracks` | `BUS_ONLY_LANE` join; `tram_tracks` is a hand-authored street list in config |
| `lanes`, `lanes_source` | Bracketed off the measured width against a 3.0–3.65 m lane, never divided by `lane_width_m` (`Q94`). Sources: `measured`, `arrows`, `arrows_unmeasured` (`Q130`), `deck_capped`, `authored`. Can be 1 (`Q114`); the driving-line floor is `RoadGraph.LANE_FLOOR`. Moves no geometry. `.claude/rules/lanes.md` |
| `lanes_forward` | Lanes carrying the edge's own direction (`Q126`): `lanes` on a one-way; on a two-way the split a row of arrows states, half where even and unstated, `null` where odd and unsplit |
| `width_m`, `width_source`, `width_publisher`, `width_confirmed_by` | The street, never the ribbon (`Q95`, `Q128`). `width_m != lanes × lane_width_m`. Treat the source set as open. `width_publisher` is the set of publishers used, joined on `+`. `.claude/rules/carriageway.md` |
| `elevation_level` | An ordinal (−1/0/1), never a height |
| `polyline`, `pos` | `y` from ground level; an off-grade edge's `y` is sampled from the sheets' structure, ramped down where it stops short (`Q90`) |
| `on_structure` | Per vertex: that station's height came from sampled structure |
| `structure_bounded` | Per vertex: structure stands beside the carriageway. Not derivable from `on_structure` |
| `road_name` | `STREET_ENAME` / `STREET_CNAME`; either may be null |
| `street_class` | `main`, `minor` or null, from iB1000 `StreetCentreLines`; the minimap's main roads |
| `kerbside` | No-stopping runs per kerb (`Q54`): `side` `near` (`U = 0`) or `off`; `from_m` / `to_m` along this polyline, so a consumer on the trimmed ribbon subtracts the start trim; `kind` `double` (24 h) or `single`. Ordered and disjoint per side |
| `foreign_edges` | Neighbour-owned runs with `foreign: <owner>` and the authored width; drawn by nothing. A crossing feature is owned by the region whose `bounds` contain its travel-start vertex. `nodes` includes their far ends |

- Nodes form where centrelines share an endpoint, never where they cross in plan. `kind` is
  `junction` at degree ≥ 3, else `endpoint`.
- Geometry is clipped to the region and its declared neighbours (`Config.clip_extent`); `bounds` do
  not move (`Q10`).

### `roads/<tile>.glb` — the drivable surface

One mesh per tile of the building grid, built by `surface.py`, streamed by `aabb` like a tile.
`pipeline.surface.read_surface` merges the chunks back for graders.

| Property | Value |
|---|---|
| Meshes | `road_surface` (one draw call) and `road_surface_collision-colonly` (the ribbon's triangles, kerb riser included; kerbs are mountable) |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`, `TEXCOORD_0`, `TEXCOORD_1`; no texture |
| `TEXCOORD_0` | U is a lane coordinate, 0 at the nearside kerb line and `lanes` at the offside; V is metres along. Caps carry `(0, 0)` |
| `TEXCOORD_1.x` | Packed marking state, constant per edge: `class + 4·lanes + 64·direction + 256·bus_lane + 512·tram_tracks + 1024·offside_kerb + 2048·centre + 131072·kerb_near + 524288·kerb_off + 2097152·lanes_forward`. `class`: 0 carriageway, 1 kerb, 2 cap. `lanes` 1–15. `direction`: 1 both, 2 forward. `centre` (6 bits): sixteenths of a lane beyond the centreline where an opposed pair's flows meet, 0 = not a pair. `kerb_*` (2 bits): 0 absent, 1 unrestricted, 2 single, 3 double. `lanes_forward` (2 bits): 0 = not said. **The channel is full** (max 2²³ − 1, the limit of exact float32 rounding); the next field needs another channel |
| `TEXCOORD_1.y` | The edge's drawn length in metres after trims; caps 0.0 |
| `COLOR_0.a` | Where the kerbside restriction applies: 0 or 255 per rail; not opacity |
| Material name | `road_markings` → `tuning/road_markings.tres` |

- The codec is mirrored as `MARKING_*` in `etl/pipeline/surface.py`,
  `assets/shaders/road_markings.gdshader` and `game/tools/verify_road_surface.gd`; this table is the
  tiebreak.
- Nearside is left of travel. `etl/tests/test_kerbside.py` asserts the sign.
- `TEXCOORD_0` cannot be drawn on alone: kerbs run past both ends of the lane range and a cap's
  `(0, 0)` is in range; read `class` and `lanes`. A U-lane is `2·half_width / lanes` on the ground.
- A junction cap is the convex hull of its arms' corners, per level; one cap may close a cluster of
  nodes joined by stubs. A cap overlaps its arms (p90 1.17 m); the shader's 6 m junction fade hides
  it, which is why painted layers are their own meshes (`Q53`).
- An owned run's far half past the region join rides in the last column's chunk, so a chunk `aabb`
  can reach past the region.

`roadsurface.json` (schema 12, ETL-only) carries what only `surface.py` knows, for stages drawn on
the road: `ribbons` (each strip's rails as drawn), `caps`, `carriageway[].kerb_hidden_m`,
`opposed_pairs`, `junctions` / `clusters`, `corridor_*`, `lanes_painted`, `areas`, `join`,
`cut_vertices`, `trim_m`. `drawnroad.py` and `DrawnSurface` are the readers.

### `fares.json` — pickup and dropoff nodes

`{schema_version: 1, city_id, region_id, nodes: [...], street: [...]}`. A node is `{id, pos, kind,
stand_category, name: {en, zh}, nearest_edge, edge_t, pickup, dropoff, place: {en, zh}}`; a street
spot is `{id, pos, kind: "street", nearest_edge, edge_t, side, pickup, dropoff, place}`.

- `kind` is `taxi_stand`, `pudo` or `poi`; `stand_category` is null unless `taxi_stand`.
- `pos` is the kerbside where the passenger stands. The taxi stops at `nearest_edge`, `edge_t`
  (fraction of plan length). The snap considers level-0 edges only (`Q15`).
- `place` (`Q142`): the named building nearest `pos` within `fares.places.max_distance_m`; null
  where none. The HUD leads with it; `name` is the publisher's description of the kerb.
- `poi` is TD's tram stops: `name` null in both languages, `pickup` and `dropoff` both false.
- Honour `pickup`: a quarter of published PUDO points are drop-off only.
- `street`: a kerb a passenger flags a cab at, every `fares.street.spacing_m` along a level-0 edge
  clear of junctions, no-stopping runs and bus lanes, beside a named building (`place` never null).
  Kept apart from `nodes` so stages reading published points never meet one.

### `fence.json` — where the player is fenced

`{schema_version: 3, city_id, region_id, asset, barriers: [{edge, node, position, facing}], …}`.
`asset` is the committed barrier prop; `barriers` close edges `fits_car` refuses, touchdowns and the
region's line. The other keys are the stage's counters. `Fence` stands them as one `MultiMesh`.
`.claude/rules/fence.md`.

### `tram_lines.json` — the tracks a tram runs (`Q176`)

`{schema_version: 1, city_id, region_id, tracks: [{id, points, next, open_start, open_end,
stops: [{id, s_m}], signals: [{edge, along, s_m}]}]}`.

`points` run in travel order. `next` is the tracks a tram may join, by index. `open_*` means the
track reaches the region's rectangle: the runtime joins it to a resident neighbour's, else a tram
appears or leaves there. `stops` and `signals` are metres along the track; a `signals` entry past
the length stands in the chord to `next`. `edge` is the region's own id, re-keyed through
`RoadGraph.edge_id_in`.

### `bus_routes.json` — the stops a bus or green minibus keeps to (`Q182`)

`{schema_version: 1, city_id, region_id, service_day, routes: [{key, route_id, bound, kind, name,
operator, per_hour (24 counts), stops: [{seq, stop_id, plan: [x, z], edge, t, along, side}]}]}`.

One row per route direction with a departure on `service_day`, holding only the stops inside this
region in `seq` order. `per_hour` is departures from the terminus per hour. `edge` is the region's
own id, or −1 where no road lies within `max_snap_m`; `side` is +1 nearside, −1 offside.
`BusRoutes` re-keys `edge`, joins the regions' rows by `key` and cuts a route where a `seq` is
missing. The path between stops is not here: `RoadRouter.goal_tree` finds it.

### `signals_plan.json` — the signalled junctions (`Q173`)

`{schema_version: 1, city_id, region_id, junctions: [{id, nodes, pos, stop_lines, heads, stages,
crossing, approaches: [{edge, along, stop_m, heading_deg, stage}]}]}`.

- `id` is the junction's lowest node id in its own region; `nodes` its stub cluster.
- `stop_lines` and `heads` are the two witnesses that signalled it; the engine reads neither.
- An approach is a level-0 edge entering from outside. `stop_m` is plan distance from the edge's
  start to its stop bar or crossing, else its drawn mouth, never past the mouth. `heading_deg`: 0
  is −z.
- `stage` is authored (`signals.axis_tolerance_deg`). `crossing` is true where every approach
  shares one axis; the controller then runs an all-red stage.
- Null in the manifest where the city declares no `signals:` block or stages nothing.

### Placements documents

A library `.glb` holds one mesh per kind, drawn at the origin; `<layer>_placements.json` stands
them. Entries are `{mesh, transform: {pos, rot_y_deg}}` (compass bearing) plus per-layer keys. The
game draws one `MultiMesh` per library mesh per `prop_cells.tres` cell (`Q115`). Shape, rounding
and writer are `pipeline/placements.py`'s.

| Document | Library | Extra keys |
|---|---|---|
| `arrows_placements.json` | `arrows.glb`, one glyph per `RM` code | `pitch_deg` |
| `signs_placements.json` | `signs.glb`: a mesh per face variant (mirrored boards are their own mesh), a unit `pole`, a `signs_text_<code>` quad per lettered code | `scale` (never negative) |
| `lamps_placements.json` | `lamps.glb`, one mesh per drawn kind; `rot_y_deg` is the arm's bearing | |
| `railings_placements.json` | `railings.glb`, one unit panel per class (`railings`, `bollards`, `barriers`) | `pitch_deg` |
| `trees_placements.json` | `trees.glb`: `broadleaf`, `palm`, `fan_palm`, `conifer` | `scale` (3 axes), `tint`, and a `trunks` table (radius and bare-trunk height per kind) |
| `parked_placements.json` | Committed `res://assets/authored/vehicles/parked.glb` (`tools/make_parked.py`) | `kind`, `source`, `hours` (`[from_h, to_h]` or null), `chance`, `edge` |
| `signal_heads_placements.json` | Committed `res://assets/authored/signals/heads.glb` (`tools/make_signal_heads.py`) | `junction`, `edge`, `along`, `stage`, `primary` |

The last two libraries are not in the bundle; the document's `library` names the `res://` path.
`SignalHeads` refuses an entry the plan does not hold at that junction and stage.

### Drawn layers

Every layer: no texture, and no collider in the `.glb` (a rail or a stop line would be a kerb with
no visible cause; the verify tool fails on one). Colliders are the placer's, set on the layer's
node in `region.tscn`: railings a box per placement (`collides`, `Q159`), lamp and sign posts
(`posts`, `Q191`), tree trunks. What lies on the road casts no shadow; of a sign only the pole does
(`GeneratedLayer.casts_shadow` / `shadow_meshes`). Each stage's rules are in its
`.claude/rules/<name>.md`; each stage's report (`<stage>.json`) is ETL-only.

| Asset | Material name → `.tres` | Attributes | Notes |
|---|---|---|---|
| `tram.glb` | `tramway` | `COLOR_0`; `TEXCOORD_0` (fraction across, metres along); `TEXCOORD_1` (class 0 bed / 1 rail, metres along) | One primitive. Geometry, not ribbon paint: the rails are mostly off the ribbon (`Q58`). Cut at the region's rectangle. `TEXCOORD_1.y` duplicates `TEXCOORD_0.y` on purpose |
| `arrows.glb` | `arrows` | `POSITION`, `NORMAL` only | Rigid glyphs at `arrows.lift_m` 0.015. Colour lives in the `.tres` (`Q53`) |
| `boxjunctions.glb` | `boxjunctions` | `POSITION`, `NORMAL` | A mesh per 300 m cell; hatch at `lift_m` 0.012, border `border_lift_m` above |
| `crossings.glb` | `crossings_signal` (→ `boxjunctions.tres`), `crossings_zebra` (→ `roadmarks.tres`) | `POSITION`, `NORMAL` | A mesh per paint per 300 m cell, `<kind>_c<col>_r<row>`; `lift_m` 0.010, the lowest paint |
| `stopmarks.glb` | `stopmarks_white` (→ `roadmarks.tres`), `stopmarks_yellow` (→ `boxjunctions.tres`) | `POSITION`, `NORMAL` | Bus stop, stand and tram stop boxes and their legends (`Q242`), a mesh per paint per 300 m cell; `lift_m` 0.013 |
| `stops.glb` | `signs` | `COLOR_0` | Authored flags and tram shelters at published stops (`Q242`), a library stood by `stops_placements.json`: `pole` (unit, scaled), `bus_stop`, `minibus_stop`, `tram_shelter` (the roof), `tram_post`. `pole` and `tram_post` take a collider |
| `roadmarks.glb` | `roadmarks` | `POSITION`, `NORMAL` | Stop, give-way and longitudinal lines (`Q132`), a mesh per 300 m cell, `lift_m` 0.016 (above the arrows on purpose). A transverse line's host is the road it crosses, not the nearest (`Q69`) |
| `railings.glb` | the class id (mesh name and material name at once, `Q61`) | `TEXCOORD_0`: metres along the panel, metres above the deck | `cull_disabled`, so winding decides lighting; `facing_away` must be 0. Position is registered onto the drawn kerb (`Q60`) |
| `signs.glb` | `signs`; lettering on `signs_text` | `COLOR_0` (four-colour livery) | Position from the pole layer, facing derived per post then turned per plate (`Q62`, `Q72`). `cull_back`, each plate drawn twice. The lettering atlas ships as `signs_text.png` (`signs_text_atlas`), never embedded (`Q70`) |
| `lamps.glb` | `lamps` (on `signs.gdshader`) | `COLOR_0` | Registered outward onto the kerb, refused inside any ribbon (`Q78`). The lantern lights at night (`Q160`), with a pool under it (`lamp_pools.gd`) |
| `trees.glb` | `trees` (on `vertex_albedo.gdshader`) | `COLOR_0` | HyD and LCSD inventories only (`Q171`); refused in the carriageway, off the ground or under a deck |
| `planters.glb` | `planters` (on `vertex_albedo.gdshader`) | `COLOR_0` | HyD's planter walls and the beds they close (`Q247`), one merged mesh. Carries `planters_collision-colonly`, the walls alone — the one generated layer after the road with a body of its own |
| `paths.glb` | `paths` (on `vertex_albedo.gdshader`) | `COLOR_0` | iB1000 `CartoPedLine` pavement margins and footpaths as ribbons `lift_m` over the LOD0 ground (`Q250`), a mesh a 300 m cell. Cut back off the carriageway region, out of the sea and off ground steeper than `max_grade_pct`. No collider, no shadow |
| `water.glb` | `sea_water` → `water.tres`; the land on `harbour_land` → `harbour_land.tres` | `COLOR_0` | Mesh `water`: `basemap.json`'s `water` as one flat mesh at `water_level_m`, facing +Y. Mesh `harbour_land` (`Q250`), where the frame holds any: the land beside the sea that no region's tiles draw, flat at `land_level_m` with a face to `seabed_m` under its sea edge |
| `backdrop.glb` | `backdrop` → `backdrop.tres`; the far sea on `sea_water` → `water.tres` | `COLOR_0`; alpha 0 marks the far sea | The region's far version (`Q249`): mesh `backdrop` is its skyline on its ground, `backdrop_sea` the water round it (absent where there is none). Both stand past the camera's far plane and are drawn by `far_shore.gdshaderinc`'s depth squeeze, the skyline skipped nearer than the plane; no collider, no shadow. Every region ships one; a far-only region ships it with `backdrop.json` alone |

- Winding decides visibility under `cull_back`. Godot winds front faces clockwise and glTF
  counter-clockwise, so the engine-side and ETL-side tests have opposite signs (`Q59`).
- The engine re-quantises an imported mesh to a 16-bit lattice over its own AABB; a triangle
  thinner than the lattice can flip and be culled. Stages shipping thin geometry drop slivers under
  two lattice cells (`boxjunctions.json`'s `slivers_dropped`, `import_quantum_m`).

### `basemap.json` — the harbour and the parks

`{schema_version: 3, city_id, region_id, water, parks, asset, water_level_m, shoreline, report}`.

- `water`, `parks`: triangles `[x0, z0, x1, z1, x2, z2]` in the region's plan metres, no winding.
  Sea is the frame cut along iB1000 `Shoreline`, sealed at `basemap.seal_m`; the sheets publish no
  sea polygon. Parks are iB1000 `Site` open-space codes, less the sea.
- `asset` is null where the frame held no sea. `water_level_m` is +1.3 mPD.
- `shoreline` (schema 3, `Q250`): `{hard, soft}`, the published lines as `[x0, z0, x1, z1, ...]`
  in plan metres — `hard` the types in `shoreline.hard_types` (sea wall, breakwater), `soft` the
  rest (high-water mark).
- The stage runs before `buildings`, which cuts the decimated ground along `water`'s edge
  (`shore.cut_sea`, `Q140`, `Q250`): the sea side drops to `basemap.seabed_m` (−3.0), and where
  the nearer `shoreline` line is `hard` a vertical face joins it to the land. The face is ground:
  part of the tile and of its collider, and its sheet's row in the object table has a box grown
  to hold it.
- Frames overlap across regions; the minimap draws each resident region's ground at its offset.

### `landmarks.json` — hero building placement

`{schema_version: 2, city_id, region_id, landmarks: [{id, asset, transform: {pos, rot_y_deg},
name: {en, zh}, replaces_source_ids, excluded_bounds, triangle_budget}]}`.

Written by `export.py` from the config's `landmarks:` block; placed by `scripts/city/landmarks.gd`.

- `replaces_source_ids`: building stems the ETL excludes from the tiles. `export.py --check` holds
  the set equal to what the building stage dropped.
- `excluded_bounds`: the AABB union of the excluded meshes; null where no stem was claimed.
- `transform.pos.y` is the base elevation; models are footprint-centred with `y = 0` at the base.
  `rot_y_deg` is a compass bearing; `generated_landmarks.gd::placement_of` is the one conversion.
- `triangle_budget`: 8,000 by default; a mesh-sourced hero pins its measured count.
- Two kinds, separated by licence (`LICENSING.md`). An authored hero (`central_plaza.glb`) is
  committed under `game/assets/authored/landmarks/` (CC BY-SA 4.0) and never in `shipped()`. A
  mesh-sourced hero (HKCEC) is the government mesh repainted by `pipeline/landmarks.py`: gitignored,
  listed under `landmark_assets`, `rot_y_deg` 0.

**The authored door** (`Q121`). The `landmarks:` block is how a DCC-authored `.glb` enters: metres,
Y-up, footprint-centred; Godot's node suffixes are honoured (`-col`); a material name in
`generated_scene_import.gd::SHADERS` takes that layer's `.tres`, any other keeps its PBR material; a
packed image is extracted on first import and committed with its `.import`. `verify_authored.gd`
grades it against `assets/authored/fixtures/dcc_roundtrip.glb` (`tools/make_dcc_fixture.py`).

**The vehicle door** (`Q124`). A car's shader payload is carried as material names, stamped at
import (`generated_scene_import.gd::vehicle_body`); `tools/make_vehicle.py` emits the same names.

- Slots: `vehicle_paint`, `_glass`, `_trim`, `_cabin`, `_cabin_dim`, `_lamp`, and
  `vehicle_lamp_{brake,reverse,indicator_left,indicator_right,sidelamp,headlamp,roofsign}`. The
  importer stamps `UV = (circuit, marker)` and merges all slots into one `vehicle_body` surface on
  `tuning/vehicle_body.tres`. An unknown `vehicle_…` slot is refused.
- The slot's base colour is baked into `COLOR_0` as sRGB. `COLOR_0.a` is a relief code (`Q232`),
  moved to `UV.y`'s fraction; 255 is flat.
- One object, origin at the ground centre, nose toward −z, no vertex shared between parts.
- A `MultiMesh` car carries its state in `INSTANCE_CUSTOM`: livery in `rgb`; `a` bit 0 apply
  livery, bit 1 running, bit 2 braking (`VehicleBodyBatch`).

---

## Coordinates

| Item | Value |
|---|---|
| Source CRS | HK1980 Grid, EPSG:2326; vertical datum HKPD |
| Game space | Local metres, Y-up, origin at the region's NW corner |

```
game_x =  (easting   - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing  - origin_northing)
```

- `etl/pipeline/hongkong.py` is the only module that states EPSG:2326 (`Q100`); `crs.py` takes the
  codes as arguments. `CityManifest.to_grid` is the inverse.
- The negation on `z` is forced: east is `+X`, so north is `−Z`. Flip it and the city is mirrored.
- Origin easting is floored and northing ceiled, so offsets are non-negative and tile row 0 is north.
- `fetch.py` downloads every sheet that intersects the region; clip to the region before indexing.

### Two frames, and why

Each region is authored in its own frame (small numbers: float32 spacing at 38 km is ~3.9 mm
against a 50 mm suspension sag). `city_space = region_local + city_offset`, anchored on the city's
declared `bounds`.

- `CityRegions` places each synced region at `city_offset − city_offset(frame)`, the frame being
  the first region in `regions.json`. A region loaded alone can ignore `city_offset`.
- A city's `bounds` must not change once a `city.json` has shipped. `config.py` checks every region
  lies inside them.

---

## Runtime systems

`main.tscn` is `Main` with `World` (instances `city_drive.tscn`) and `GUI` (`Hud`, `StartMenu`).
`Main` parks the level under the start menu and resumes it on `started`. `city_drive.tscn` holds
`Regions`, `Lighting`, `DayClock`, `Taxi` (`taxi_tyre.tscn`), `Signals` / `Heads`, `Traffic`,
`Trams`, `Fares` (`Readout`, `Hire`), `Horn`, `Sounds`, `FareGuide`, `CameraRig`, `Attract`.
`region.tscn` holds one region's layer nodes, `Landmarks`, `Fence`, `Parked`.

| System | Responsibility |
|---|---|
| `CityRegions`, `CityStreamer` | One `region.tscn` per synced region; tiles and road chunks loaded by distance to their `aabb`, off the main thread (`tuning/streaming.tres`) |
| `RoadGraph`, `road_join.gd` | Nearest edge, lane centre, widths and the two bars; resident regions merged rule for rule with `pipeline/join.py`. Refuses off-grade edges (`Q13`); expresses passability, never enforces it |
| `RoadRouter` | Directed-edge search with one-way, turn bans and a bar: `Profile.legal()` (traffic) and `Profile.player()` (rules free, car bar). `prepare` a destination, then `route` is a lookup. `.claude/rules/router.md` |
| `RoadSpawn`, `DriveLevel` | The start line: first run at fare node `f_004` (`RoadSpawn.DEFAULT_FARE_ID`), later runs short of another pickup (`Q227`). Nearside lane, never the centreline; `Pose.blocked` fails a start in a wall (`Q52`) |
| `VehicleController`, `TyreVehicleController` | `VehicleBody3D` with arcade overrides and the per-wheel tyre model (`tyre.tres`, `tuning/cars/`, `tuning/systems/`). `Pushable` bodies exchange momentum (`Q180`). `.claude/rules/handling.md` |
| `LightingRig`, `DayClock` | Environment, sun, exposure and the `cycle` it blends through (`day_to_night.tres`, `Q160`) |
| `SignalController`, `SignalHeads` | Each junction's stages on the physics clock (`signal_plan.tres`); `state_of(edge, along)` is the one read; counts the player's reds, never docks |
| `TrafficSystem`, `TramSystem` | Kinematic traffic on the router's legal arcs, fleet by the game hour (`traffic.tres`, `Q186`), buses on `BusRoutes`; trams on `tram_lines.json` (`trams.tres`). `.claude/rules/signals.md`, `busroutes.md`, `trams.md` |
| `ParkedLayer` | The parked roster by the hour, re-stood only out of view (`Q161`) |
| `FareSystem` | The fare loop (`fares.tres`); `FareMeter` charges TD's tariff (`tariff.tres`); `SkillTracker`, `NearMiss`, `StyleCombo` (`skills.tres`); `SessionTally`. `.claude/rules/fares.md` |
| `Hud`, `StartMenu` | Speed, street plate, wrong-way sign, minimap, meter, tip clock, callout, `TouchSticks`, `PauseButton`; menu pages from `menu.tres` and `menu_text.json`, `LoadingCover`, `ShaderWarmup`, `LedgerCard`. `.claude/rules/hud.md` |
| Audio | No director: `TaxiAudio`, `TaxiHorn`, `TaxiDoor`, `TaxiHire`, the tram bell and traffic horns play their own. `DriveMusic` plays the driving music, by the rig's hour and the combo's count (`Q246`). Buses `SFX`, `Engine`, `Cabin`, `Music` under `Master` with a compressor (`default_bus_layout.tres`). `.claude/rules/audio.md` |

Rules:

- `scripts/core/` holds pure logic: no `Node` inheritance, no rendering calls.
- Tuning profiles declare no `@export` defaults; a zero is a missing key and the system goes inert,
  naming the file and field (`TuningTable`).
- Platform branching is the `.mobile` / `.web` setting suffixes plus `Handset` (below).
- A vehicle's drive layout is scene data (`VehicleWheel3D.use_as_traction` per wheel). The drift's
  axle is derived from chassis geometry (`VehicleController._group_axles`), not wheel role.

Each `game/tools/verify_*.gd` states what it checks in its header. `verify_vehicle` sees no frame,
so cannot tell a shader compiled. `bench_traffic.gd` measures a traffic tick and is not run by
`check.sh`. `--perf-log=<s>` writes a row per frame to `user://perf.csv` in any build.

---

## Input architecture

One action set; no gameplay script knows which scheme is live.

| Action | Type | Keyboard | Gamepad | Touch |
|---|---|---|---|---|
| `steer` | `float` −1…1 | `A`/`D`, ←/→ | Left stick X | steering thumb, horizontal from where it landed |
| `accelerate` | `float` 0…1 | `W`, ↑ | RT | drive thumb, above origin |
| `brake_reverse` | `float` 0…1 | `S`, ↓ | LT | drive thumb, below origin |
| `handbrake` | `bool` | `Space` | A / Cross | none yet |
| `look_back` | `bool` | `C` | B / Circle | none yet |
| `horn` | `bool` | `H` | X / Square | none yet (`Q178`) |

- Touch values are merged in `InputRouter`, never fed through the action map, whose 0.2 deadzone
  would eat the first fifth of the travel.
- Touch overrides the action map per axis; it does not replace it. Scripted drives run on
  `Input.action_press`.
- `InputRouter` samples in `_physics_process`.

### The three schemes

**Keyboard** is digital. Its steering is ramped in the input layer (`InputRouter.steer_for`,
`keyboard_steer.tres`, `Q210`), so the car's own rack is the same for every method. Input assists
are per input method; drive assists are per car, tuned against a linear input.

**Gamepad** is analog on steer and both triggers, so `handbrake` stays a `bool`.

**Touch** is two relative thumbs: the landing point is the origin (`Q83`). `TouchSticks` draws a
hint for each (`Q204`). `ControlOptions` picks the steering thumb's side (`--touch-side=`, default
from the saved option), the response (`--touch-steer=`, `touch.tres`'s `steer_curve`, `Q220`) and
whether the controls stand still (`--touch-anchor=relative|fixed`, default fixed, `Q239`) and
whether the wheel is spun or slid (`--touch-wheel=spin|slide`, default spin, `Q251`).

- `handbrake` is settled as a held offset on the steering thumb's vertical axis (`Q83`), not built.
  Nothing else goes on that axis.
- Zone geometry is `tuning/hud_layout.tres` through `HudLayout`'s placer, shared with the HUD so
  both resolve in one frame with one safe-area inset. `touch_zone_*` is where taps are detected and
  the HUD may overlap it; `thumb_rest_*` is what a fingertip covers and the HUD may not (`Q80`).
  The zones sit on their own `CanvasLayer`, so `--hud=off` keeps the steering.

---

## Performance budget

| Metric | Mobile | Desktop |
|---|---|---|
| Target | 60 fps @ 1080p | 60 fps @ 1440p |
| Draw calls | < 150 | < 400 |
| Visible triangles | < 300k | < 1M |
| Texture memory | < 128 MB | < 512 MB |
| Bundle size | < 200 MB (iOS cellular threshold) | no hard limit |
| Shadows | Two directional cascades at 100 m | Two at 400 m |

Device floor: iOS A13; Android Adreno 618 tier, Vulkan 1.1, 4 GB RAM. Android constrains the budget.

One content tier ships. Phone exceptions: `Handset.is_phone` (app or browser) pulls the sun's
shadow reach to the rig's `phone_shadow_max_distance_m` (`LightingRig.fit_shadow`) and hides SAVE
IMAGE; `Handset.is_app` draws the 3D scene at 0.75 of the window (`LightingRig.fit_scale`, `Q236`).
Shadows switched off looked flat and blown out; a cheaper tier needs the ambient re-tuned, not the
shadow removed.

What buys the budget: one merged mesh per tile; ETL-generated LOD tiers; repeated objects as a
library under a `MultiMesh` per `prop_cells.tres` cell (`Q115`); occluders.

---

## Build pipeline

```sh
python -m pipeline --region wan_chai                # etl/, repo-root .venv; all 26 stages
python -m pipeline --region wan_chai --from roads   # resume mid-chain
python -m pipeline --region wan_chai --jobs 4       # stages side by side, same bytes
python -m pipeline.buildings --region wan_chai      # one stage alone
python -m pipeline.export --region wan_chai --check # the cross-document checks alone
tools/sync_generated.sh wan_chai causeway_bay       # → game/assets/generated/ + regions.json
godot --headless --path game --import && tools/check.sh
tools/export.sh [macos|web|android|ios]             # default: macos + web
```

- The chain calls each stage's own `main`, so full and partial builds cannot drift. `fetch` is the
  only stage that touches the network; `--force` belongs to it and is refused with a `--from` that
  skips it.
- `--jobs N` starts a stage when the stages `NEEDS` names for it are done; a new stage needs a row.
  No stage reads another region's output.
- `gdb.read_layer` caches clipped reads under `etl/.cache/layers/` (`HK_TAXI_LAYER_CACHE=0` off).
- `export` validates across documents (a fare node naming a missing edge, a tile never written).
- `sync_generated.sh` copies exactly what `city.json` names (`python -m pipeline.export … --list`).
  **The argument list is the resident list**: it is written to `regions.json`, the first region is
  the frame, and anything else under `assets/generated/` is deleted. Always pass every region.
  Every other region whose far version is built (`python -m pipeline.backdrop --built`) goes with
  it as `far`: `backdrop.glb` and `backdrop.json` alone (`Q249`). A `far_only` region
  (`tsim_sha_tsui`) is built by `python -m pipeline --region tsim_sha_tsui`, which runs `fetch` and
  `backdrop` only.
- `IOS_TEAM_ID=<team> tools/ios.sh device` puts a Release build on a handset; `… testflight
  [<build number>]` archives and uploads. It exports with a window, refuses an unbaked PCK, and
  flattens the icon's alpha in the build copy.
- `fastlane/` is the App Store listing: `fastlane metadata` uploads the per-locale text and the
  screenshots `tools/store_screenshots.sh` takes; `fastlane submit` sends the version to review.
  Both want an App Store Connect API key in the environment (the `Fastfile`'s header). The
  description carries the data credit verbatim (hard rule 6).

### Looking at it

| Scene | For |
|---|---|
| `scenes/main.tscn` | Drive |
| `scenes/dev/city_preview.tscn` | Fly around; every tile at one tier, not a performance measurement |
| `scenes/dev/asset_viewer.tscn` | One `.glb` named by `--asset=`; needs no built region |
| `scenes/dev/skidpad.tscn`, `greybox.tscn` | The handling pad (`tools/skidpad.sh`, fixed-step and deterministic); the grey-box circuit |

- The spawn passes no heading: `nearest_edge` then takes the edge's vertex order, the legal
  direction.
- The fallback `Transform3D` literal in `city_drive.tscn` is a trap: the 12-float constructor fills
  `Basis` rows, while forward is `-basis.z`, a column. Use `RoadSpawn.basis_facing`. Eyeball check:
  the harbour is north.
- The flyovers cannot be driven onto (`Q13`). Level −1 runs under the terrain (`Q21`).

---

## Constraints

1. No runtime network calls.
2. No engine-specific formats out of the ETL: glTF, PNG and JSON only.
3. Hong Kong facts live in `etl/config/hong_kong.yaml` or `etl/pipeline/hongkong.py`, one home each
   (`Q100`).
4. Tuning values live in `game/tuning/`, never as constants in scripts.
