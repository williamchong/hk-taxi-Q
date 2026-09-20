# Architecture

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Engine | **Godot 4.7** | MIT, no royalties or seat fees |
| Renderer | **Mobile** (primary), Compatibility for the web demo | Forward+ only if a desktop tier ever justifies it |
| Physics | **Jolt** (Godot default since 4.4) | Trimesh collision; `VehicleBody3D` for the car (`Q50`, reversing `P0-5a`) |
| Engine language | **GDScript**, statically typed | See below |
| ETL | **Python 3.11+** — numpy, pyproj, pyyaml, pyogrio, shapely (`Q129`) | Build-time only |
| Targets | iOS, Android, Windows/macOS/Linux (Steam) | Web export reserved for the free demo slice |

### ⚠️ The importer can reinstate `VehicleWheel3D` behind your back

Godot's glTF importer converts nodes by **name suffix**: `_wheel` imports as a `VehicleWheel3D`, and
`_col`, `_convcol`, `_navmesh`, `_occ`, `_rigid`, `_vehicle` likewise. Nothing reports an error —
import, `check.sh` and the driver all pass, and the only symptom is missing geometry.

The tyre mesh is `taxi_tyre.glb` and must stay so: since `Q50` it is a child of a real
`VehicleWheel3D`, so a rename to `taxi_wheel.glb` nests a wheel in a wheel, silently. When geometry
goes missing, check the instantiated tree, not the source scene.

### Why GDScript, not C#

C# in Godot 4.7: desktop supported, Android and iOS experimental, web unsupported. Mobile is a
primary target and the web demo is the marketing funnel. GDScript also hot-reloads, which speeds
the handling-tuning loop.

Performance escape hatch: **GDExtension** (C++, or Rust via godot-rust) — it keeps every export
target, web included. Do not reach for C#.

Always annotate types (`var speed: float = 0.0`). `.tres` resources are the home for tuning data.

---

## Project settings

`game/project.godot`, `export_presets.cfg`, every `.tres` and every `.tscn` are committed in the
form the **editor's** writer produces, so an editor save is a no-op (`Q119`, `P5-21`). The writer
drops every comment and omits any key equal to its engine or script default — such a key stays in
force. So:

- Rationale lives in this table (config) or a sidecar `<name>.md` beside the resource, never in
  the file. `check.sh`'s `tuning` step requires the sidecar and refuses a `;` line.
- Values are asserted by `tools/verify_settings.gd`, which reads them back through
  `ProjectSettings` (the value in force, not the line in the file).
- ⚠️ A full scene save takes two passes: a scene saved before the scene it instances has a uid does
  not carry that uid.
- ⚠️ A typed node export (`@export var camera: Camera3D`) needs `node_paths=PackedStringArray(...)`
  on the node line or it reads null from a hand-authored scene. The two references that reach the
  `InputRouter` autoload stay `NodePath`, because `node_paths=` resolves inside the scene only.
- Headless runs (`check.sh`, `--import`, open-and-quit) leave both config files byte-identical.

| Setting | Value | Why |
|---|---|---|
| `rendering/renderer/rendering_method` | `mobile` | Locked decision. Set as the base value so editor and desktop preview the phone's renderer |
| `rendering/renderer/rendering_method.web` | `gl_compatibility` | Engine default, so absent from the file; Godot forces Compatibility on web regardless. Asserted anyway: the project states the renderer it wants |
| `rendering/textures/vram_compression/import_etc2_astc` | `true` | Godot refuses to export any arm64 target without it |
| `rendering/anti_aliasing/quality/msaa_3d` | `2` (4x) | For thin geometry: a sub-pixel stripe breaks into dashes (0.1 m box hatch is one pixel at 13.6 m on the chase rig; sign poles are 0.032 m). Coverage is conserved, so brightening or lifting paint cannot fix it. ⚠️ Invisible to the performance budget — draw calls and primitives are identical at 0/2x/4x; the cost is fill rate. Never 8x: WebGL2 `MAX_SAMPLES` is 4. No `.mobile` override; the mobile tier (`P0-3b`) must re-take this. Desktop cost unmeasured. `Q91` |
| `physics/3d/physics_engine` | `Jolt Physics` | Locked decision, stated so an engine default change is not followed silently |
| `application/run/max_fps.mobile` | `60` | Above the 60 fps target only throttles the device. Desktop uncapped |
| `display/window/stretch/mode` | `canvas_items` | Resolution-independent UI |
| `[importer_defaults] scene.import_script/path` | `res://tools/generated_scene_import.gd` | The importer leaves `vertex_color_use_as_albedo` off and glTF cannot express it. An importer default because generated `.import` files are gitignored |
| `[importer_defaults] scene.meshes/force_disable_compression` | `true` | Godot quantises positions over the mesh's own AABB: `lamps.glb`'s 1,646 m AABB gives a 0.025 m step against a 0.06 m arm; sign poles are thinner than the step. Costs +958,720 B (+2.0%) of PCK. Project-wide because per-asset `.import` does not survive a clone. ⚠️ Three authored imports (taxi body, tyre, `central_plaza.glb`) keep `false` deliberately — metre-scale AABBs. `Q82` |
| `[importer_defaults] scene.meshes/generate_lods` | `false` | The ETL ships the tiers (`P5-13`). Off buys −5,262,224 B of PCK (−8.6%) and raises primitives 16–30% on the throttle route; draw calls and frames identical. Triangle relief is the ETL's LOD ratio (`Q120`) |
| `rendering/occlusion_culling/use_occlusion_culling` | `true` | Reads the `-occonly` occluder tiles ship (`P5-13`). ⚠️ Stock Web export templates omit the raycast module, so the web cut cannot cull and the occluder is download cost there (`Q122`, `P5-17`) |
| `[shader_globals] exposure_anchor` | `float`, `1.0` | The rig's exposure (`P5-28b`, `Q38`, `Q33`). Six shaders read it — `city_facade`, `city_facade_clean`, `road_markings`, `tramway`, `vertex_albedo`, and `signs` behind a per-`.tres` `apply_exposure` bool only `lamps.tres` sets — always after `vertex_srgb_to_linear`, never on a `.tres` colour. 🔴 Pinned type included: an undeclared global resolves to zero (black city, green checks) and an `int` truncates. The value is the project default; `scripts/world/lighting_rig.gd` sets what a scene renders at |

🔴 `[importer_defaults]` seeds only a **newly created** `.import`. After changing a key, delete the
sidecars and re-import; a hand edit is undone by the next `--import`. `check.sh`'s `sidecars` step
fails a stale one (`P5-16`).

Deliberately not set (measured):

- `directional_shadow/soft_shadow_filter_quality` — Godot ships a `.mobile` override of `0`, and
  overrides beat the base, so setting the base only degrades desktop.
- `directional_shadow/size` — default 4096 (`.mobile` 2048). 8192² is 134,217,728 B more shadow map
  against a 512 MB desktop texture budget.
- Cascade count costs no VRAM (one `size × size` texture whatever the split); it costs geometry
  submission. Cascade count and distance are node properties on the one shared sun.

**Autoloads** — three, each a wide-scope system that owns its data and that others register with
(`Q119`). All run for the life of the process; treat as hot-path code.

- `DebugHud` — every dev readout. The frame counter is a `Label` it builds, not another autoload.
- `InputRouter` — the one reader of raw input. Reached by `NodePath` (`^"/root/InputRouter"`),
  never by global name, so no gameplay script depends on autoload registration at compile time.
- `BeamBudget` — the renderer-global spot-light cap. An autoload because its "no arbiter" branch
  lights every beam, and a scene that forgot a regular node would take it silently.

Not autoloads, deliberately:

- `RoadGraph.shared()` — a `static var WeakRef`, parsed once per scene and dropped with it
  (`P5-25`, `Q124`). An autoload would hold ~6 MB for the process and serve a stale graph across an
  ETL re-run. `verify_road_graph.gd` builds its own through `from_document`.
- `Cmdline` (`scripts/core/cmdline.gd`) — a `class_name` static; `--debug-view=`, `--hud=`,
  `--touch=` and `--asset=` go through it.

### The debug overlay

`DebugHud` (`scripts/ui/debug_hud.gd`) owns every dev readout and, through `view_changed`, the road
graph's chevrons. `F3` cycles off → minimal → full; `--debug-view=off|minimal|full` sets the start.

| View | Shows | Draw calls (delta) |
|---|---|---|
| `off` | nothing — the default in every build | — |
| `minimal` | position block and frame counter | +8 |
| `full` | plus registered readouts and 3D debug geometry | +19 |

- `drive.sh` (`.claude/skills/run-hk-taxi-q/drive.sh`) appends `--debug-view=minimal` unless the
  caller names a view, so a scripted screenshot says where it was taken.
- ⚠️ The player's HUD is separate and ON by default (+5 draw calls); `--debug-view=off` does not
  touch it. A clean frame for art review needs `--debug-view=off` and `--hud=off`.
- The position block reports game metres and the source-CRS grid reference
  (`CityManifest.to_grid`, inverse of `crs.py`'s `to_game`).
- ⚠️ The toggle is a raw key, not an action — dev keys stay out of `[input]` — so `drive.sh
  --hold=` cannot press it; scripted runs use the flag.

---

## Checks

**Godot never signals failure through its exit code** — a parse failure or a promoted warning
prints and exits `0`. `tools/check.sh` turns that output into an exit code, and is the only thing
that does.

Rows are in run order. 🔴 No Godot process may run above `--import`: a `class_name` resolves only
from the cache the import scan writes, and the autoloads instantiated around every `--script` run
name globals whatever the tool does (`Q119`).

| Step | Covers | In CI |
|---|---|---|
| `instructions` | Root `CLAUDE.md` under 40,000 characters; scoped checklists live in `.claude/rules/<name>.md` | yes |
| `gdformat --check` | Layout across `game/`. The file count is asserted — on a tree with no `.gd` it exits 0 (`Q119`) | yes |
| `tuning` | Every `game/tuning/*.tres` and `game/scenes/*.tscn` has a non-empty sidecar `.md` unless `UNDOCUMENTED_OK` names it; no `;` comment in a resource; no orphan sidecar or stale exemption (`Q119`) | yes |
| `--import` | Autoloads and what they reach; builds `game/.godot/` | yes |
| `settings` | `tools/verify_settings.gd` — the 21 warning promotions, every pinned value, all three `[importer_defaults]` keys, read through `ProjectSettings` | yes |
| `sidecars` | Every `*.glb.import` under `assets/generated/` and `assets/authored/` carries the `meshes/*` keys `[importer_defaults]` pins (`P5-16`, `Q122`; authored since `P5-20`, `Q124`). Keys are read from the project file and their count asserted. 0 sidecars checked passes — a clone has no city | yes |
| warnings sweep | `--check-only` per script, grepping `treated as error\|Parse Error` — never `$FATAL`, which fires on healthy lines. An empty file list is fatal and the swept count is printed (`Q119`) | yes |
| `verify_beam_budget`, `verify_vehicle`, `verify_mesh_contract`, `verify_hud`, `verify_input`, `verify_authored` | Spot-light cap; the taxi's shader binding, lamp channels and beam aim; the no-texture contract; HUD layout against `hud_layout.tres` (`Q80`); the touch scheme by synthetic fingers (the only touch test, `P0-3b`); the DCC fixtures. None needs a built region | yes |
| `verify_city`, `verify_tiles`, `verify_road_surface`, `verify_road_graph`, `verify_city_streamer`, `verify_spawn`, `verify_landmarks`, `verify_fence`, `verify_tramway`, `verify_arrows`, `verify_boxjunctions`, `verify_crossings`, `verify_railings`, `verify_signs`, `verify_roadmarks`, `verify_lamps` | The generated-asset contracts, once per synced region (`regions.json`, `--region=`) | **no** |
| `verify_join` | The runtime merge of the first two synced regions against `pipeline/join.py` (`P5-9d`); SKIPs on one region | **no** |

Traps:

- The sweep is separate because `--import` compiles only autoloads and what they reach. It must
  run with `game/` as the project directory, or `res://` does not resolve and every script
  analyses clean.
- ⚠️ A verify tool that appears to hang is a parse error: `_init` never runs, `quit()` is never
  called. Read the log for `Parse Error` / `Compile Error`, and give scripted Godot runs a
  watchdog.
- 🔴 A verify tool proves an asset is correct; nothing proves it is in the world.
  `verify_roadmarks.gd` passed while `roadmarks.glb` was in no scene (`Q73`). Adding a layer
  includes its node in `region.tscn` (instanced by `city_drive.tscn` and `city_preview.tscn`), and
  the check that it renders is a frame someone looked at.
- ⚠️ Verify tools `preload` every dependency and never name a `class_name` global: globals resolve
  through the gitignored `game/.godot/global_script_class_cache.cfg`, so on a fresh clone the tool
  fails to parse and exits 0.
- ⚠️ Autoloads are registered on the first frame; a verify tool that loads a scene should `await
  process_frame` first (`verify_vehicle.gd`, `skidpad_ablation.gd`). `free()` any scene
  instantiated but never added to the tree before `quit()`, or Godot prints `leaked at exit` lines
  that are not a failure.
- ⚠️ A headless `--import` re-saves `game/assets/authored/greybox_wanchai.json` with tabs
  (`Q115`). `git checkout` it after `check.sh`; never commit it.
- Exports are byte-deterministic given a clean `project.godot` (it is packed as
  `project.binary`). Quote a PCK delta only between two exports measured the same way, and verify
  the tree is clean before exporting.

**Grading tools**, run by hand or through `tools/battery.py` (`CLAUDE.md` "Before marking work
done" and `.claude/rules/` index the full list). Each reads back what shipped and shares no code
with the pipeline, because a stage cannot mark its own work.

| Tool | Answers |
|---|---|
| `tools/deck_error.py` | `Q20` — vertical distance from the drawn carriageway to the deck beneath, down centrelines. Gates on \|error\| p90, deepest intrusion, share measured |
| `tools/overhang.py` | `Q22`/`Q23` — whether there is a deck beneath, across the full drawn width |
| `tools/ground_clearance.py` | `Q18`/`Q24` — whether drawn ground stands in the at-grade carriageway. Sizes `buildings.ground_sink_m` |
| `tools/carriageway_occupancy.py` | `Q19` — whether anything solid stands in the road at bumper height, per **edge**. ⚠️ Fails today. Also grades `clearance.py`'s own number (`Q51`), ratcheted by `tools/clearance_reconcile.py`. `--corridor-report` prints the corridor profile per failing edge; opt-in, gates nothing |
| `tools/paint_clearance.py` | `Q92` — whether painted layers are above the road or inside it. Splits a burial into a kerb top past the ribbon (never gated) and a wrong height (gated) |
| `tools/lane_paint.py` | `Q113`/`Q114` — whether the painted lane is wide enough to be one, against `width_bounds.lane_m` (3.00 m); carries `carriageway_margin.lane_bracket`'s verdict |
| `tools/cap_pavement.py` | `P3-31` — junction cap drawn where HyD's Pavement Polygon says no carriageway. Three states per cell (on carriageway, past a HyD kerb within `--near-m`, unsurveyed). Grades, never gates; compare at one `--cell-m` and `--near-m` |
| `tools/kerbside_error.py` | `Q54` — how much kerbside yellow the source supports. ⚠️ Does not grade the join. Reads the ETL out tree, because trims travel in `roadsurface.json` |

- `tools/narrowing.py` is not a grader: it prices a lower `surface.floor_default_m` by importing
  `pipeline.clearance` whole, deliberately. It refuses to print unless its baseline column
  reproduces `clearance.json` edge for edge.
- Shared code: `tools/_lib/` (`bundle`, `ribbon`, `streets`); `deck_error.py` owns the bundle
  reader and `overhang.py` the width sweep (`walk_width`, `cross_section`, `left_of`,
  `half_width_at`) — reuse it, its duplicated-vertex guard is not obvious.
- ⚠️ A tool needing two passes over the carriageway must still walk it once and replay
  (`carriageway_occupancy.py`'s `Lattice`): a first pass visiting less than the second reads as
  **clear**, the one direction a grader must never flatter.

### GDScript warnings

The `[debug]` block promotes 21 GDScript warnings to errors — the engine's type-aware checker.
Three of them (`native_method_override`, `get_node_default_without_onready`,
`onready_with_export`) default to error in 4.7, so the writer omits them from the file;
`verify_settings.gd` names all 21. ⚠️ Never edit that list down to match a regression (`Q72`).

Warnings reach stdout only at level `2`, so every enforced warning is at `2`.

**Enforced (`=2`):** `untyped_declaration` · `shadowed_variable`, `shadowed_variable_base_class` ·
`confusable_identifier`, `confusable_local_declaration` · `integer_division`, `narrowing_conversion`
· `unused_variable`, `unused_parameter`, `unused_local_constant`, `unused_private_class_variable`,
`unused_signal` · `standalone_expression`, `standalone_ternary`, `redundant_await` ·
`incompatible_ternary`, `int_as_enum_without_cast`, `int_as_enum_without_match` ·
`get_node_default_without_onready`, `onready_with_export` · `native_method_override`.

**Deliberately not enforced:**

- `inferred_declaration` — `:=` is static typing.
- `unsafe_method_access` / `unsafe_property_access` / `unsafe_cast` / `unsafe_call_argument` and
  `return_value_discarded` — generated JSON arrives as `Variant`, and `Packed*Array.append()`
  returns an unread `bool`. Revisit if the contract gains a typed loading layer.
- `unassigned_variable`, `unreachable_code`, `assert_always_false` look worth promoting and were
  measured as costing nothing.

Not a bug-catcher: none of the defects under `P0-5b`/`P0-5c` would have been caught by a linter.

### Formatting

`gdformat` (from `gdtoolkit`, in the `dev` extra); default line length 100 matches `ruff`, so no
config. `gdlint` is installed but not wired in: it cannot check static typing.

### CI

`.github/workflows/ci.yml` runs on every push to `main` and every PR: `ruff` + `pytest` on Python
3.11 and 3.13, and `tools/check.sh` against the pinned Godot version. It runs the script rather
than repeating its steps in YAML, where the Godot steps would pass on failure.

CI cannot check the generated-asset contracts: `game/assets/generated/` is gitignored. The
workflow sets `VERIFY_GENERATED=0`, which skips those tools and prints that it did. Running the
ETL in CI (a ~320 MB government download per push) is a non-goal.

---

## Repo layout

```
hk-taxi-Q/
├── CLAUDE.md                    # agent instructions — read first
├── .claude/rules/               # change-scoped checklists, loaded by path
├── docs/
├── etl/                         # Python: geodata → game assets (build time)
│   ├── config/
│   │   └── hong_kong.yaml       # bounds, source URLs, tiling, vocabularies — the tunable city facts
│   ├── pipeline/
│   │   ├── config.py            # loads hong_kong.yaml — the only route config takes in; re-exports every block
│   │   ├── config_blocks/       # one module per stage: dataclasses and parsers. Import via config.py
│   │   ├── hongkong.py          # the constants that ARE the city: CRS pair, drive-on-left (Q100)
│   │   ├── crs.py               # projected coords -> game space
│   │   ├── fetch.py             # download from CSDI / data.gov.hk, cache to sources/
│   │   ├── documents.py         # read/write a stage's JSON + its schema check
│   │   ├── report.py            # what every stage's manifest says the same way (Q133)
│   │   ├── gltf.py              # glTF read + GLB write; no dependency
│   │   ├── gdb.py               # geodatabase layers + WKB → numpy
│   │   ├── geometry.py          # plan-space helpers shared by the drawing stages
│   │   ├── polyline.py          # polyline walking/measure helpers
│   │   ├── mesh.py              # merge, partition, LOD collapse
│   │   ├── meshbuild.py         # the shared mesh accumulator (Q100)
│   │   ├── colour.py            # the authored palette, resolved
│   │   ├── terrain.py           # terrain / structure mesh → sampleable height field
│   │   ├── podiums.py           # iB1000 blocks → podiums.json
│   │   ├── buildings.py         # sheets → vertex-coloured tiles + LOD tiers
│   │   ├── landmarks.py         # mesh-sourced hero models → landmarks/*.glb
│   │   ├── roads.py             # Road Network geodatabase → roadgraph.json
│   │   ├── join.py              # two neighbours' roadgraph.json → one (P5-7g)
│   │   ├── carriageway.py       # the width/lane survey roads.py publishes (Q94/Q95)
│   │   ├── carriageway_area.py  # width from HyD's pavement area where no ray reaches (Q128)
│   │   ├── kerbside.py          # NSR restrictions linear-referenced onto the graph
│   │   ├── carve.py             # INFRASTRUCTURE cut back to the surveyed carriageway (P3-28, Q19)
│   │   ├── region.py            # level-0 carriageway as territories → carriageway_region.json (Q129)
│   │   ├── surface_region.py    # what surface.py takes from carriageway_region.json (P3-33c)
│   │   ├── surface.py           # roadgraph.json → roads/<tile>.glb; ribbon, kerbs, junctions
│   │   ├── drawnsurface.py      # DrawnSurface + crease cutting, for layers painted on the road
│   │   ├── drawnroad.py         # the ONE reader of the drawn road: ribbon and running kerb line (Q133)
│   │   ├── clearance.py         # what stands in the ribbon → clear width per station
│   │   ├── fence.py             # barriers where fits_car refuses an edge → fence.json (P3-29)
│   │   ├── fares.py             # taxi stands + PUDO + POIs → fares.json
│   │   ├── tramway.py           # tram rails → tram.glb (P3-14)
│   │   ├── arrows.py            # turn arrows → arrows.glb + arrows_placements.json (P3-15, P5-4)
│   │   ├── boxsource.py         # the box reader boxjunctions.py and surface.py share (P3-32)
│   │   ├── boxjunctions.py      # box junctions → boxjunctions.glb (P3-18)
│   │   ├── crossings.py         # crossing stripes → crossings.glb, two paints (P3-35g2)
│   │   ├── roadmarks.py         # stop / give-way / longitudinal lines → roadmarks.glb (P3-23, P3-34)
│   │   ├── railings.py          # railings → railings.glb + railings_placements.json (P3-19, P5-5)
│   │   ├── signs.py             # traffic signs → signs.glb + signs_placements.json (P3-16, P5-2)
│   │   ├── sign_sheets.py       # TD's sign drawings, rasterised (P3-20)
│   │   ├── sign_text.py         # sign lettering → signs_text.png (P3-20, Q68)
│   │   ├── lamps.py             # lamp posts → lamps.glb + lamps_placements.json (P3-26, P5-3)
│   │   ├── placements.py        # a prop library's stands: entry shape, pitch, totals, writer
│   │   ├── export.py            # → city.json; assembles and validates the stage outputs
│   │   └── __main__.py          # `python -m pipeline` — 20 stages, in order
│   ├── sources/<source>/        # raw downloads — GITIGNORED
│   ├── out/<region>/            # pipeline output — GITIGNORED
│   └── tests/
├── game/                        # Godot project
│   ├── project.godot
│   ├── export_presets.cfg       # COMMITTED — never put signing credentials here
│   ├── scenes/
│   │   ├── main.tscn            # Main / World / GUI — the boot scene
│   │   ├── city_drive.tscn      # the level World holds: streamer, regions, taxi, chase camera
│   │   ├── region.tscn          # one region's layers, placed per synced region by CityRegions (P5-9c)
│   │   ├── dev/                 # grey-box circuit, skidpad, city preview, asset viewer
│   │   ├── vehicle/             # taxi.tscn
│   │   └── world/               # lighting rigs: clean_daylight, golden_hour
│   ├── scripts/
│   │   ├── core/                # pure logic, minimal engine coupling
│   │   ├── city/                # tile streaming, road graph runtime
│   │   ├── vehicle/  traffic/  fares/  input/  ui/  camera/  world/
│   ├── assets/
│   │   ├── generated/           # ETL output — GITIGNORED
│   │   ├── authored/            # hero buildings, vehicles, fixtures, UI — COMMITTED
│   │   └── shaders/
│   ├── tuning/                  # .tres resources + sidecar .md
│   └── tools/                   # headless scripts — import fixup, verify tools
└── tools/                       # dev scripts: check, battery, sync, export, grading, make_*
    └── _lib/                    # what graders share: bundle, ribbon, streets (P3-35f)
```

Stage order: `fetch`, `podiums`, `buildings`, `landmarks`, `roads`, `carve`, `region`, `surface`,
`clearance`, `fence`, `fares`, `tramway`, `arrows`, `boxjunctions`, `crossings`, `roadmarks`,
`railings`, `signs`, `lamps`, `export`.

⚠️ `scenes/dev/` is not shipped. `run/main_scene` is `scenes/main.tscn`: `Main` with a `World` that
instances `city_drive.tscn` and a `GUI` holding the HUD, so a level change swaps `World`'s children
(`Q119`). A fresh clone boots to an empty world with a `push_warning`, because the level needs the
gitignored `assets/generated/`. An export is a demo until there is a menu in front of it.

The ETL is a separate Python project because it runs rarely, at build time, and needs GDAL.

---

## Data contract

The interface between ETL and game. **Versioned — change both sides together and bump
`schema_version`.** All positions are game-space metres.

> **When to bump:** where a consumer would be **wrong** to keep its old interpretation, not
> wherever bytes change. `P2-7` bumped `roadgraph.json` because `polyline.y` changed meaning while
> looking identical, and did not bump the road mesh, whose geometry moved but whose attributes
> kept their meaning.

### `city.json` — manifest

```json
{
  "schema_version": 35,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "source_crs": "EPSG:2326",
  "origin": { "easting": 835765.0, "northing": 816125.0, "elevation": 0.0 },
  "city_offset": [38379.0, 0.0, 32826.0],
  "bounds_game": { "min": [-32.0, -13.049, -73.571], "max": [1704.698, 378.532, 923.142] },
  "tile_size_m": 150,
  "tiles": [
    {
      "id": "t_00_00",
      "lods": ["tiles/t_00_00_lod0.glb", "tiles/t_00_00_lod1.glb"],
      "aabb": [[8.37,4.935,-16.588],[167.562,70.801,165.268]],
      "occluder": [true, true]
    }
  ],
  "road_graph": "roadgraph.json",
  "road_surface": [
    { "id": "t_00_00", "file": "roads/t_00_00.glb",
      "aabb": [[-5.154,-2.957,-1.775],[175.845,6.336,151.9]] }
  ],
  "carriageway": [
    { "edge": 651, "half_width_m": [5.12, 5.12, 4.32, 3.2],
      "clear_width_m": [-1.0, 10.24, 8.5, 0.0],
      "corridor_half_width_m": [7.4, 7.4, 7.1, 6.9],
      "corridor_offset_m": [2.1, 2.1, 1.8, 1.6], "lanes_painted": 2 }
  ],
  "lane_width_m": 3.2,
  "car_width_m": 1.8,
  "fares": "fares.json",
  "tramway": "tram.glb",
  "arrows": "arrows.glb",
  "arrows_placements": "arrows_placements.json",
  "boxjunctions": "boxjunctions.glb",
  "crossings": "crossings.glb",
  "lamps": "lamps.glb",
  "lamps_placements": "lamps_placements.json",
  "railings": "railings.glb",
  "railings_placements": "railings_placements.json",
  "signs": "signs.glb",
  "signs_text_atlas": "signs_text.png",
  "signs_placements": "signs_placements.json",
  "roadmarks": "roadmarks.glb",
  "landmarks": "landmarks.json",
  "fence": "fence.json",
  "landmark_assets": ["landmarks/hkcec.glb"],
  "etl_version": "0.1.0",
  "generated_utc": "2026-07-30T20:04:03Z"
}
```

Keys (`etl/pipeline/export.py`):

- Required: `DOCUMENT_KEYS` (`road_graph`, `fares`, `landmarks`, `fence`) plus `tiles`,
  `road_surface`, `landmark_assets`, `bounds_game`. `fence` is written on every run: an empty
  `barriers` list means nothing to close, a missing file means the stage never ran.
- `OPTIONAL_ASSET_KEYS`, each optional and nullable: `tramway`, `arrows`, `arrows_placements`,
  `boxjunctions`, `crossings`, `lamps`, `lamps_placements`, `railings`, `railings_placements`,
  `signs`, `signs_text_atlas`, `signs_placements`, `roadmarks`. Null where the estate publishes no
  such layer, **or** where every feature failed the join — a stage names its asset from what it
  drew.
- The manifest names the other documents, it does not contain them; each is separately versioned.
  A build ships exactly what the manifest names (`shipped()`); `sync_generated.sh` copies only
  that. Bundle size is measured from the PCK (`PROGRESS.md`), never summed from these files.
- 🔴 The game must read the manifest to find its tiles. In an exported build `res://` is a PCK
  that `DirAccess.get_files_at` will not enumerate, so a directory listing renders an empty city
  with no error. `scripts/city/city_manifest.gd` is the only supported route.
- `origin` is computed from the region bounds — `floor(min_easting)`, `ceil(max_northing)`, the
  north-west corner. It puts a game-space position back on the source map.
- ⚠️ `bounds_game` is the union of the content, not the region rectangle (Wan Chai: 1650 × 887 m
  declared, 1737 × 997 m drawn). Do not size a partition or place map edges off the rectangle.
- `generated_utc` is the only field that differs between two builds of identical inputs; strip it
  before diffing.

`carriageway[]` — one row per edge, one value per station, indexed by that edge's `roadgraph.json`
polyline and the same length (schema 4: a road becomes a bridge partway along an edge).

- `half_width_m` is the drawn half-width, which the game cannot derive: `surface.py` draws
  off-grade ribbons at `max(width_m, floor_for(...))` — `0.0` floor on structure — and level-0
  ribbons from their territory's rails (`Q129`). ⚠️ The drawn width can equal `width_m` (`Q95`);
  assert "not narrower", never "wider". `RoadGraph` warns and falls back to the authored width
  where the table is missing; `verify_road_graph.gd` treats absence as an error.
- 🔴 Since schema 32 (`Q129`, `P3-33c`) a level-0 row is the edge's **territory** — its share of a
  carriageway several centrelines may share — not the road kerb to kerb. Three keys on those rows
  only: `corridor_half_width_m`, half the kerb-to-kerb corridor `clear_width_m` is measured
  across; `corridor_offset_m`, where that corridor is centred in `offset_m`'s frame (`P3-33e`,
  additive, no bump: the corridor sits 0.91 m off the centreline at p50 and 7.71 m at worst, so a
  grader handed the half-width alone walks the wrong window — the game compares widths and never
  places it); and `lanes_painted`, the lane count the ribbon is painted with once a narrow share
  has cut it. A reader holding `clear_width_m <= 2 × half_width_m`, or the ribbon to cover `width_m`,
  is wrong there. `RoadGraph.corridor_half_width_of` falls back to the ribbon where a row
  publishes no corridor (off-grade edges; no `carriageway_region:` block).
- `clear_width_m` (schema 9, `Q51`): the widest continuous gap a car could get through at that
  cross-section, measured by `clearance.py` between 0.30 m and 2.00 m above the deck (`Q19`'s
  band). **`-1.0` = no cross-section judged** (ribbon held back for a junction cap) — never zero,
  which would read as blocked. `RoadGraph` reads it as `is_passable` / `is_routable` and does not
  fold it into `nearest_edge`; `Hit.clear_width_m` reports it and `RoadSpawn` is the consumer
  (`Q52`) — `verify_spawn.gd` is what fails.
- ⚠️ `lane_width_m` and `car_width_m` are two bars over `clear_width_m`, never merged (`Q19`):
  traffic is routed on the first (`RoadGraph.is_passable`, `Q51`), the player is fenced at the
  second (`RoadGraph.fits_car`, `P3-29`). `car_width_m` is `null` where no `clearance:` block is
  declared, meaning nothing is fenced.
- 🔴 Since schema 33 (`Q132`, `P3-34`) the white lines along a road are geometry in
  `roadmarks.glb`, and `road_markings.tres` draws neither lane dashes nor a two-way centre line.
  The two halves ship together: a mismatched bundle has no lane lines or each twice.
  `lanes_painted` still cuts the ribbon for the bus-lane line and the kerbside yellows.

#### Tiles

`lods` is nearest-first, one file per tier, matching `lod_cell_sizes_m` — except where
`class_lod_cell_sizes_m` holds a class back (a building decimates at 1.5 m, a deck at 0.5 m). Each
class is collapsed separately then merged, so a tile is still one mesh and one draw call. See
`ART_DESIGN.md` "LOD policy".

- ⚠️ The ground is decimated before it is tiled (`Q25`): cutting a continuous surface first tears
  it — 15.65% of probes within 2 m of a tile boundary had no ground, against 0.61% beyond 10 m.
- ⚠️ `tiles[].aabb` is the union of the tiers actually shipped, not of the source geometry, and
  tier 0's box alone is not enough (a coarser grid can preserve an extreme vertex a finer one
  averaged inward). `verify_city.gd` asserts every tier contained and the union tight to 1 cm.
- A tile's `aabb` can be larger than the tile (buildings are assigned whole, by centre; up to
  222 m across a 150 m tile). Use the `aabb` for culling and streaming, never the grid position.
  Tile vertices are in region game space; a tile needs no transform.
- No textures: one material, one drawn primitive, colour in `COLOR_0`; `merge` refuses a textured
  mesh. ⚠️ `scripts/city/mesh_contract.gd` walks **every shader uniform** and fails on any
  `Texture`, so a region-wide data map sampled by world position is an amendment to this contract
  — change `mesh_contract.gd` and this paragraph together.

| Attribute | Meaning |
|---|---|
| `COLOR_0.rgb` | Albedo, **sRGB-encoded** normalised `uint8`. Every consumer must linearise it |
| `TEXCOORD_0.x` | Metres along the wall (`P5-11`, schema 28): the world axis chosen by the vertex normal, blended over 45° (`buildings.along_m`). Stamped on the shipped tier after `collapse`; the carve re-stamps it |
| `TEXCOORD_0.y` | Metres above that source object's own base. Metres, not a fraction: the floor count is what the window shader carries. With `.x`, a real planar UV in metres |
| `TEXCOORD_1.x` | `floor()` is the `SurfaceClass` marker — 0 façade, 1 ground, 2 structure. `fract()` is a per-object phase in 1/256 steps |
| `TEXCOORD_1.y` | The object row: an exact integer indexing the tier's `extras` table, constant per source object. `verify_tiles.gd` holds every vertex to an existing row and that row's box within `BuildingIndex.ROW_SLACK_M` (8 m) |
| Mesh `extras` | The object table: `{"objects": [{"id", "class", "aabb"}, …]}`, one row per source object with a vertex left in the tier; `aabb` is the source mesh's game-space box before decimation. Imported as `Mesh.get_meta("extras")` (`Q121`); `scripts/city/building_index.gd` reads it, `object_at(root, point)` answers by smallest containing box, ties by nearest vertex's row. ⚠️ Custom `_` vertex attributes are dropped by the importer |
| Material name | **`city_facade`** — the name is the contract. `tools/generated_scene_import.gd` dispatches on it and hands the tile `tuning/city_facade.tres` |

- ⚠️ The phase is quantised to 1/256 because float32 rounds a raw seed near 1 into the next marker.
- ⚠️ The marker is derived from the palette: a class with a flat `class_materials` entry has no
  floors to band; anything the height ramp colours is a façade. No class name reaches pipeline
  logic.
- ⚠️ ETL material name, import script and shader must agree, and a broken link fails silently to
  flat vertex colour. `verify_tiles.gd` asserts the payload and the resolved material path.
- ⚠️ Codec constants are contract, not tuning — never in the city yaml. The façade-survey codec
  that rode `TEXCOORD_1` from schema 6 to 19 was removed at schema 20 (`Q102`): its only producer
  was withdrawn, and a channel that can only say "refused" asserts a survey it does not carry.
- ⚠️ `meshes/light_baking = 2` makes the importer generate its own UV2 and overwrite `TEXCOORD_1`
  with plausible fractions. Tiles ship `= 1`; `verify_tiles.gd` asserts it and the row check
  catches it a second way.
- Podium metres (`Q47`) stay in the ETL intermediate `podiums.json`, which `export.py` never
  names; the runtime does not branch on provenance.
- `SurfaceClass.GROUND` is reserved for a future ground shader; the shader ignores it today. It
  does not buy a usable ground height — `TEXCOORD_0.y` is per source mesh.
- `TEXCOORD_0` ships float32 (+4.01 MB of PCK when added). Quantising to `unorm16` would save
  ~2 MB at the price of a scale factor in the contract; not done while the 200 MB budget is far.

**Collider** (`P5-12`). Only tier 0 ships collision, as its own primitive
`<tile_id>_collision-colonly`, which the importer reads into a mesh-less `StaticBody3D` named
`<tile_id>_collision` with a `ConcavePolygonShape3D`. The render mesh is `<tile_id>` and collides
with nothing. `CityStreamer` builds no shape at load.

- Decimated at its own cell, `buildings.collision_cell_m` (per class). Today equal to the finest
  tier's by value, so `tools/collider_offset.py` reads 0.000 m. Its sweep prices a coarser one: at
  2 / 3 / 4 m the trimesh is 87.8 / 72.9 / 63.5% of render triangles, façade offset p90 0.47 /
  0.62 / 0.91 m.
- Only tier 0, because the coarse tier is resident only beyond the 250 m near band.
- ⚠️ The suffix goes on the merged mesh, so every class in `buildings.classes` collides — the
  ground included (terrain ships in the tile since `P3-10`). `buildings.ground_sink_m` drops the
  ground under the kerb; `tools/ground_clearance.py` grades it.
- `verify_tiles.gd` asserts one mesh-less body named for the tile on tier 0, none under a render
  mesh, none on other tiers.
- ⚠️ Graders read tiles through `gltf.read_render`, which drops the helper primitives; reading the
  file whole counts every wall twice.

**Occluder** (`P5-13`, `P5-17`). A tier may ship `<tile_id>_occluder-occonly`, read into an
`OccluderInstance3D` with an `ArrayOccluder3D` and no mesh.

- `buildings.occluder_cell_m` is a list parallel to `lod_cell_sizes_m`, `null` for a tier with
  none: `[4.0, 4.0]` ships today's build, `[null, null]` is what the web cut wants (`Q122`).
  Built from `buildings.occluder_classes` (`BUILDING`, `INFRASTRUCTURE`, never the ground), with
  `class_occluder_cell_m` per class.
- `city.json`'s `occluder` is a list parallel to `lods`. `verify_tiles.gd` asserts exactly one
  `OccluderInstance3D` where true, none where false — never by name.
- ⚠️ The culling unit is the instance (a 150 m tile, road chunk or region-wide `MultiMesh`): it
  culls 2 draw calls on Wan Chai's throttle route and 12–47 at Mong Kok's worst camera.
  🔴 It costs +5,734,832 B of PCK (+10.3%). 8 m and 16 m cells and a separately streamed occluder
  are priced in `PLAN.md` `P5-13`/`P5-17` (`Q122`). Handset CPU cost is unmeasured.
- The carve cuts all three primitives.

**`COLOR_0` is sRGB-encoded and every consumer linearises it itself** (`Q27`). Godot 4 has no
`vertex_color_is_srgb` render mode, so every shader takes `vertex_srgb_to_linear` from
`assets/shaders/colour.gdshaderinc`, and `generated_scene_import.gd` sets the `BaseMaterial3D`
flag for anything that names no shader. Skipping it gives a pale city whose palette "does nothing"
(57% of a lit façade pixel's luminance was albedo-independent) — reach for `tools/frame_stats.py`
before the lights.

- ⚠️ The two branches are exclusive; moving an asset from the flag to a shader must pick up the
  conversion in the same commit, and nothing fails loudly if it does not.
- 🔴 Reproducing `BaseMaterial3D` in a shader without moving the frame takes two more things
  (`P5-28b`, `vertex_albedo.gdshader`): name `diffuse_mode` Burley and `specular_mode`
  Schlick-GGX explicitly, and linearise in the **vertex** stage — the fragment-stage form is
  uniformly darker across a triangle. Not a reason to move the other shaders. Residual: 101 px at
  ≤ 2 codes, cause unidentified.
- A layer is a parameterisation, not a shader (`Q71`): arrows, box junctions and stop lines share
  `marking_paint.gdshader`; `railings` / `bollards` / `barriers` share `railings.gdshader`.
  `MeshContract.check_shader_material` holds each layer to its own `.tres` by `resource_path`.
- ⚠️ `COLOR_0.a` on tiles is a constant `255` and is not a safe place for a shader mask: enable
  transparency on a tile and the city renders see-through with no error.

### `roadgraph.json` — drivable network

```json
{
  "schema_version": 15,
  "nodes": [{ "id": 1, "pos": [120.5, 4.0, 300.2], "kind": "junction" }],
  "edges": [
    {
      "id": 1, "source_id": 4021, "run": 0, "from": 1, "to": 2,
      "polyline": [[120.5, 4.0, 300.2], [180.0, 4.1, 305.0]],
      "on_structure": [false, false],
      "structure_bounded": [false, false],
      "direction": "both",
      "lanes": 3,
      "lanes_source": "measured",
      "lanes_forward": 2,
      "width_m": 11.0,
      "width_source": "two_way_span",
      "width_publisher": "hyd_pavement+ib1000",
      "width_confirmed_by": "",
      "speed_limit_kph": 50,
      "bus_lane": false,
      "tram_tracks": false,
      "elevation_level": 0,
      "road_name": { "en": "Gloucester Road", "zh": "告士打道" },
      "kerbside": [{ "side": "near", "from_m": 12.4, "to_m": 88.1, "kind": "double" }]
    }
  ],
  "foreign_edges": [
    { "id": 7, "source_id": 5310, "run": 0, "foreign": "causeway_bay", "...": "the same fields" }
  ],
  "turn_restrictions": [{ "from_edge": 1, "via_node": 2, "to_edge": 5 }]
}
```

| Field | Source |
|---|---|
| `direction` | `TRAVEL_DIRECTION` (1 → `both`, 3 → `forward`). Only those two are ever written; a source coded against its digitisation declares `backward` in config and the ETL reverses the polyline |
| `turn_restrictions` | `TURN_ID` + `EDGE(1-8)FID`, as edge `id`s. Since schema 12 an arm may name a `foreign_edges` entry |
| `speed_limit_kph` | `SPEED_LIMIT` layer joined on `ROUTE_ID`; otherwise the city default (~90% of edges) |
| `bus_lane` | `BUS_ONLY_LANE` layer, joined on `ROUTE_ID` |
| `tram_tracks` | ⚠️ Hand-authored: a list of street names in city config |
| `lanes` / `lanes_source` | Measured where possible (`Q94`): `carriageway.py` brackets the measured width against TPDM 4.3.9.8's 3.0–3.65 m lane — ⚠️ never divided by `lane_width_m`. `measured` where the bracket is one integer; `arrows` where a row of ≥ 2 turn arrows settles an ambiguous bracket (a row of one is refused — a lower bound); `arrows_unmeasured` (schema 15, `Q130`) where a row raises the authored count on an unlicensed width, which stays `authored`; `deck_capped` where an off-grade authored count is cut to the deck's ceiling — a refusal, not a reading; `authored` = `lanes_for(speed_limit_kph)`. 🔴 `lanes` can be 1 (schema 11, `Q114`); the floor a driving line needs is `RoadGraph.lane_offset`'s `LANE_FLOOR`. A lane count moves no geometry. `.claude/rules/lanes.md` |
| `lanes_forward` | How many of `lanes` carry the edge's own direction (schema 13, `Q126`). `lanes` on a one-way edge; on a two-way edge the split a row of arrows states, half where none does and the count is even, **`null`** where odd and unsplit. Forward lanes are `U ∈ [0, lanes_forward]`. A row can also put back an odd count TPDM 3.4.2.7 struck from an ambiguous two-way bracket (WAN CHAI ROAD `e50`: `(2, 3)` → three, two forward) — ⚠️ above the narrowed bracket only. Moves no geometry and no driving line. `arrows.json`'s `lanes_split_disagreement` grades the second reader |
| `width_m` / `width_source` | The **street**, never the ribbon. Measured from what TD, iB1000 and HyD drew where licensed (`Q95`, `Q128`), authored `lanes × lane_width_m` elsewhere. ⚠️ A consumer may not invert `width_m / lanes`. Schema 14 added `width_source: hyd_strip` — treat the source set as open. `.claude/rules/carriageway.md` |
| `width_confirmed_by` | Schema 14 (`Q128`): the independent reading that licensed a `hyd_strip` width; empty otherwise |
| `width_publisher` | Which publishers supplied the stations behind `width_m`, joined on `+`; empty where authored (schema 7). ⚠️ A set, not a winner, and who was **used**, not who could have answered. HyD's `pavement_polygon` reads the trafficable surface where TD's and iB1000's lines run to the kerb — p10 −3.39 m apart |
| `elevation_level` | `ELEVATION` (−1/0/1 here). An ordinal level, never a height, and since `P2-7` not what decides `y` |
| `polyline` / `pos` | Game metres, `y` from ground level, not the vertical datum. An off-grade edge's `y` is sampled from the sheets' `INFRASTRUCTURE` structure (schema 2). Level-0 edges meeting a node another level reaches are lifted onto the ramp; off-grade ones are ramped down where the structure stops short (`Q90`). `elevation_levels` in config supplies a flat offset where structure covers nothing. A node's `y` is the level nearest grade among its edges, highest end on that level |
| `on_structure` | ⚠️ Derived, per vertex (schema 3): true where that station's height came from sampled structure. False where ramped down to a node (`Q90`). Only `roads.py` can produce it |
| `structure_bounded` | Derived, per vertex (schema 8): true where structure stands **beside** the carriageway. `on_structure` cannot stand in — a walled approach ramp sampled off terrain is off structure (`e233`, `e55`, `e398`) |
| `road_name` | `STREET_ENAME` / `STREET_CNAME`. The null sentinel has four spellings; normalise NFKC and fold dashes |
| `kerbside` | `NSR` (schema 4, `P3-13`, `Q54`): runs of one kerb under a no-stopping restriction. ⚠️ Not a key join — `pipeline/kerbside.py` linear-references it. `side` is `near` (`U = 0`) or `off` (`U = lanes`); `from_m`/`to_m` are along this polyline, so a consumer on the trimmed ribbon subtracts `trim_start_m`. `kind` is `double` (24-hour) or `single`, from `TIME_ZONE`. Only `VEHICLE_TYPE = 1`. Runs ordered and disjoint per side |
| `source_id` / `run` | 🔴 The identity that survives across regions (schema 12, `P5-7e`, `Q116`). `id` is a per-region read ordinal with gaps — never index `edges` by position; dedupe merged regions on `(source_id, run)` |
| `foreign_edges` | Neighbour-owned runs, in their own list and never a flag on `edges` (so every reader of `edges` is inert). A crossing feature is kept whole and owned by the region whose `bounds` contain its travel-start vertex, half-open; the non-owner publishes it here with `foreign: <owner>` and the authored width — drawn by nothing, so a boundary junction keeps its mouth (`P5-7f`) and the merged graph its handover edge (`P5-9`). `nodes` includes their far ends |

- Nodes form where centrelines share an endpoint, and nowhere else — not where they cross in plan.
  `ELEVATION` is not part of a node's identity: a shared endpoint across levels is a ramp touching
  down.
- `node.kind` is `junction` at degree ≥ 3, else `endpoint` — degree, not the source's
  intersection layer.
- Geometry is clipped to the region and its declared neighbours (`Config.clip_extent`); without
  it 14% of road length is unreachable. Since `P5-7e` the cut is on the graph (`Q116`): the clip
  box widens along the shared axis only, the rectangle still selects sheets, and `bounds` do not
  move (`Q10`).

### `roads/<tile>.glb` — the drivable surface

One vertex-coloured mesh per tile of the building grid, built from `roadgraph.json` by
`surface.py` and listed as `road_surface: [{id, file, aabb}, …]` (`P5-6`; a region-wide mesh is
never culled or streamed — `Q115`, `Q120`).

- The chunks partition the built mesh by triangle; the ribbon is per station and never decimated,
  so a cut is seamless by construction. Duplicated station vertices are `roadsurface.json`'s
  `cut_vertices`.
- A strip quad belongs to the tile its two stations' plan centre falls in; a junction cap belongs
  whole to the tile of its centroid.
- Since `P5-7e` an owned run's far half past the region join rides in the last column's chunk
  (`_tile_keys`), with an `aabb` reaching past the region; a seam junction's cap is built by the
  region holding the node (`roadsurface.json`'s `join` block, `P5-7f`).
- `CityStreamer` streams a chunk by `aabb` like a tile; `drive_harness.gd` holds the chunks under
  the start line synchronously before the first physics tick.
- `pipeline.surface.read_surface` merges the chunks back into the one mesh every grader measures.

| Property | Value |
|---|---|
| Mesh name | `road_surface` in every chunk; beside it `road_surface_collision-colonly` (`P5-12`) |
| Primitives | 1 drawn per chunk, plus the collider, whose mesh the importer removes |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`, `TEXCOORD_0`, `TEXCOORD_1`; no texture |
| `TEXCOORD_0` | **U is a lane coordinate**, 0 at the nearside kerb line and `lanes` at the offside. V is metres along. Junction caps carry `(0, 0)` |
| `TEXCOORD_1.x` | The packed marking state, constant per edge: `class + 4·lanes + 64·direction + 256·bus_lane + 512·tram_tracks + 1024·offside_kerb + 2048·centre + 131072·kerb_near + 524288·kerb_off + 2097152·lanes_forward`. `class`: 0 carriageway · 1 kerb · 2 cap. `lanes` 1–15. `direction`: 1 both · 2 forward · 0 absent. `offside_kerb`: 1 where `U = lanes` is a real kerb. `centre` (6 bits): where an opposed pair's flows meet, sixteenths of a lane beyond the centreline, `k − 1` steps, 0 = not a pair. `kerb_near` / `kerb_off` (2 bits each, `P3-13`): 0 absent · 1 known unrestricted · 2 single · 3 double. `lanes_forward` (2 bits, `Q126`): 0 = not said. 🔴 Max code 8,388,607 = 2²³ − 1 and the channel is **full**: the consumer's `floor(x + 0.5)` stops being exact above 2²³. The next field needs another channel |
| `TEXCOORD_1.y` | The edge's drawn length in metres, after junction trims. Caps carry `0.0`. Distance to the nearer end is `min(V, length − V)` — a length, because a two-station edge would interpolate a distance flat to zero |
| `COLOR_0.a` | Where the kerbside restriction applies (`P3-13`, `Q54`): 0 or 255 per rail; 255 on kerbs and caps. `surface.py` inserts a station pair 0.25 m either side of each boundary. ⚠️ Not opacity; a shader that makes `COLOR_0.rgb` `flat` must keep this non-flat |
| Material name | **`road_markings`** → `tuning/road_markings.tres` |

- Nearside is left of travel (drive-on-left). Flip the sign and every asymmetric marking lands on
  the wrong side while geometry renders fine; `etl/tests/test_kerbside.py` asserts it against
  `surface.mitres`.
- ⚠️ The codec constants are contract: mirrored as `MARKING_*` in `etl/pipeline/surface.py`,
  `assets/shaders/road_markings.gdshader` and `tools/verify_road_surface.gd`; this table is the
  tiebreak.
- ⚠️ `TEXCOORD_0` cannot be drawn on alone: kerbs run off both ends of the lane range
  (`outside = kerb_width_m / lane_width_m ≈ 0.156`), and `U = 3.0` is a kerb on three lanes but a
  lane boundary on four. A cap's `(0, 0)` is an in-range value, not a sentinel. `class` and
  `lanes` in `TEXCOORD_1` answer both.
- ⚠️ A U-lane is `2·half_width / lanes` on the ground, not `lane_width_m`.
- The `-colonly` collider is on every chunk: the ribbon's own triangles, kerb riser included
  (kerbs are mountable, `P2-3`), its own primitive so the two may diverge (`Q121`).
  `verify_road_surface.gd` checks it per chunk; the kerbside-extent rule is asked of the union of
  chunks.
- Opposed carriageway pairs are two overlapping ribbons, deliberately not merged.
- Junctions are capped per elevation level with the convex hull of the corners each arm presents;
  since `P3-31` one cap may close a cluster of nodes joined by stubs. ⚠️ A cap overlaps its arms
  where they stop at different distances (p90 1.17 m, worst 4.21 m; ~6,051 m² on Wan Chai). The
  shader's 6 m junction fade hides it; anything drawn **on** a cap re-exposes it, which is why the
  painted layers are their own meshes (`Q53`). A non-convex cap is not built.

### `fares.json` — pickup and dropoff nodes

```json
{
  "schema_version": 1,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "nodes": [
    {
      "id": "f_001",
      "pos": [420.0, 3.5, 610.0],
      "kind": "taxi_stand",
      "stand_category": "cross_harbour",
      "name": { "en": "Times Square", "zh": "時代廣場" },
      "nearest_edge": 42,
      "edge_t": 0.6382,
      "pickup": true,
      "dropoff": true
    }
  ]
}
```

- `kind` ∈ `taxi_stand` | `pudo` | `poi`. `stand_category` is null unless `taxi_stand`.
- `poi` is TD's tram stops (`P3-14`). ⚠️ Their `name` is null in both languages — the source
  publishes none — so `name_en`/`name_zh` are optional roles in a fare group; and `pickup` and
  `dropoff` are both false, which must be said because `FareCategory` defaults both true.
- `pos` is the source position — the kerbside, where the passenger stands; many lie outside the
  drawn road. Where the taxi stops is `nearest_edge` at `edge_t` (fraction along the edge's plan
  length). `pos.y` comes off the snapped edge.
- ⚠️ The snap considers `elevation_level == 0` edges only, so a point under a flyover takes the
  street's height (`Q15`).
- A quarter of published PUDO points are drop-off only (66 of 275 territory-wide); honour
  `pickup`.

### `tram.glb` — the published tramway (`P3-14`)

Two rails and a bed per track, where iB1000's `CartoTransLine` tramway code publishes them. One
primitive, one material named `tramway`, one draw call, **no collider**.

| Channel | Carries |
|---|---|
| `COLOR_0.rgb` | `steel_rail` or `concrete_sooty` from `materials:`, constant per strip |
| `TEXCOORD_0` | `x` a fraction across the strip, `y` metres along |
| `TEXCOORD_1` | `x` the class — 0 bed, 1 rail; `y` metres along, again |

- Geometry rather than a marking on the `tram_tracks` bit, because the rails are not on the
  ribbon: 18.8% of cross-sections have both tracks on the drawn surface, and the outer rail sits a
  median 3.26 m past the drawn kerb (`Q58`).
- ⚠️ It must not collide — a 30 mm rail is a kerb with no visible cause. `verify_tramway.gd` fails
  on any collider.
- ⚠️ `TEXCOORD_1.y` duplicates `TEXCOORD_0.y` on purpose, the road mesh's shape: where Godot's
  16-bit vertex compression applies, a contract read off `TEXCOORD_0` reads a quantised copy.
- The class is shipped, not inferred from strip width or colour.
- `tramway.json`: `off_gauge_stations` plus `pairs` against `tracks` is what sees a pair joined
  across two tracks; `drawn_gauge_m` is bounded by `pair_tolerance_m` by construction (`Q58`).

### `arrows.glb` — the published turn arrows (`P3-15`, `P5-4`)

One flat glyph per marking symbol TD publishes, laid `lift_m` above the carriageway. One material
named `arrows`, **no collider**.

🔴 The file is a **library** and the city is `arrows_placements.json` (`P5-4`, `Q115`): one mesh
per `RM` code, drawn flat at the origin nose north, stood at `rot_y_deg` plus a `pitch_deg`
between the deck heights under tail and nose. The glyph is rigid — TD's `LENGTH` is the length
painted on the road. `arrows.json` is schema 2: `triangles`, `vertices`, `aabb` describe what is
drawn; `library_*`, `placements*`, `pitch_deg` describe the library. `tools/paint_clearance.py`
expands the library under its placements.

| | |
|---|---|
| Primitives | one per library mesh — one per `RM` code |
| Attributes | `POSITION` and `NORMAL` only — no `COLOR_0`, no UVs, no texture |

- No `COLOR_0` by decision: marking colours live in `.tres` (`game/tuning/arrows.tres`), outside
  `Q33`'s exposure rule (`Q53`). `MeshContract.check_surface` takes `expect_vertex_colours`.
- No codec: every vertex is already where `pipeline/arrows.py` put it, which is what makes the
  arrow immune to the ribbon's junction fade and cap overlap.
- A channel earns its place when something reads it — an unread `TEXCOORD_0` cost 59,300 B.
- ⚠️ Winding decides visibility (`marking_paint.gdshader` is `cull_back`). `arrows.json`'s
  `inverted` is asked of the **stood** copies and must be 0. Godot winds front faces clockwise and
  glTF counter-clockwise, so the engine-side and ETL-side tests have opposite signs — both right
  (`Q59`).
- ⚠️ Residuals are published at p90/p99/max: the tail is the finding, and a median near zero is
  also what a broken join looks like.

### `crossings.glb` — the published pedestrian-crossing stripes (`P3-35g2`)

One rectangle per surveyed stripe of `DTAD_CROSSING_LINE`, placed on the drawn road by
`boxjunctions._place` at `lift_m` 0.010, the lowest rung of the paint ladder. Two meshes, one per
paint: `crossings_signal` (yellow, `tuning/boxjunctions.tres`) and `crossings_zebra` (white,
`tuning/roadmarks.tres`), each present only where drawn. A crossing TD's surveyed zigzags reach is
a zebra. No `COLOR_0`, no collider. `crossings.json` publishes three closing partitions,
`faces_touching` (must be 0) and both sides of the plateau the zebra bar sits on.
`.claude/rules/crossings.md`.

### `boxjunctions.glb` — the published yellow box junctions (`P3-18`)

Border and cross-hatch per `DTAD_YL_BOX_POLY` polygon, hatch `lift_m` above the junction and the
border `border_lift_m` above that, both below the arrows. One primitive, one material named
`boxjunctions`, one draw call, **no collider**. `POSITION` and `NORMAL` only.

⚠️ The engine re-quantises an imported mesh to a 16-bit lattice over its own AABB (~17 mm for a
region-spanning mesh), and a triangle thinner than that can come back with its winding flipped and
be culled (217 measured). The stage ships nothing thinner than two lattice cells;
`boxjunctions.json` publishes `slivers_dropped` and `import_quantum_m`. Any stage shipping thin
geometry inherits this.

Winding and p90/p99/max reporting follow `arrows.glb`.

### `roadmarks.glb` — the published stop and give-way lines (`P3-23`)

`RM1011` STOP LINE, `RM1012` STOP LINES and `RM1013` GIVE WAY LINES from `DTAD_RD_MARK_LINE`, at
their surveyed extents, `lift_m` above the carriageway — and since schema 33 the longitudinal
white lines too (`Q132`, `P3-34`; `.claude/rules/roadmarks.md`). One primitive, one material
named `roadmarks`, one draw call, **no
collider** (a stop line would be a step at every junction). `POSITION` and `NORMAL` only.

- Its own mesh because a stop line sits on the cap, inside the ribbon's junction fade.
- 🔴 The host edge is picked by **transversality**, not proximity: a stop line sits at a junction
  mouth, so the nearest centreline is usually the road it is parallel to. The two joins disagree
  on 44% of stop lines and 43% of give-way lines. A wrong host moves the height, not the plan.
  `roadmarks.json` publishes `host_disagreement`; `axis_residual_deg` cannot see it (`Q69`).
- ⚠️ `lift_m` is 0.016, deliberately above `arrows`' 0.015 — a legibility order, a clear
  millimetre because the engine re-quantises Y.
- `surface.py`'s `opposed_pairs` (below) is what lets it place a centre line between the halves
  of a dual carriageway (`Q125`).
- The import-lattice constraint, winding and reporting follow `boxjunctions.glb` and `arrows.glb`.

### `lamps.glb` — the published lamp posts (`P3-26`, `Q82`, `P5-3`)

A 9 m hexagonal column `outset_m` outside the drawn carriageway edge, a bracket arm `arm_reach_m`
out and `arm_drop_m` down, and a lantern box — one per `LPO` point in iB1000's `UtilityPoint` that
clears the road. **No collider** (a budget call pending `P2-6`; breakaway is `B3`).

🔴 A **library** plus `lamps_placements.json` (`P5-3`, `Q115`): one mesh per drawn kind, drawn at
the origin arm north, stood at the arm's compass bearing. The column's ring is seeded from the arm
so the stood library is the column drawn in place (`tests/test_lamps.py`). `lamps.json` is schema
2. Entry shape, rounding, totals and writer are `pipeline/placements.py`'s, shared with signs and
arrows; the rotation is `gltf.placed_positions`.

| | |
|---|---|
| Primitives | one per library mesh — one per drawn kind |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`; no UVs, no texture |
| `COLOR_0` | One colour from `materials:` via `lamps.column_material`. Carried although monochrome, because `signs.gdshader` reads it |
| Material name | `lamps` → `res://tuning/lamps.tres`, on `signs.gdshader` |

- The vocabulary is the publisher's: `UTILITYPOINTTYPE` has a coded-value domain (`LPO - Lamp
  post`). `lamps.json` publishes `refused_by_kind` over the rest.
- 🔴 The position is registered, and "no column in the carriageway" comes from **two** refusals:
  `_register` pushes a column outward only (`Q78`) to `half_width + outset_m` of its host edge or
  refuses past `max_shift_m`; the placed point is then re-snapped against **every** edge and
  refused inside any drawn ribbon. `min_kerb_clearance_m` is the invariant.
- ⚠️ The arm direction is derived from the kerb side and cannot be graded (`Q62`);
  `lantern_overhang_m` ships instead of a counter that would read 0 by construction (`Q72`).
- ⚠️ `UtilityPoint` publishes no elevation, so a flyover lamp is drawn on the street beneath;
  `nearest_is_elevated` reports how often that is possible.

### `railings.glb` — the published street furniture (`P3-19`, `Q61`, `P5-5`)

A vertical strip `height_m` tall, `outset_m` outside the drawn carriageway edge, for every run of
`DTAD_RAILING_LINE` the city draws. **No collider** — a design decision: `GAME_DESIGN.md` lists
railings under "deliberately diverge on". Breakaway is `B3`.

🔴 A **library** plus `railings_placements.json` (`P5-5`, `Q115`): one unit panel per class,
`panel_m` wide (2.0 / 1.5 / 3.0 m, bound by test to the post pitch in that class's `.tres`), drawn
along north with the road to its east, stood `floor(length / panel_m + 0.5)` times per visible
piece, yawed to the chord and pitched to the deck. What tiling costs is published per class:
`metres_snapped`, `joints`, `joint_gap_m`, `bends` above `bend_report_deg`.

| | |
|---|---|
| Primitives | one library mesh per class — `railings`, `bollards`, `barriers` — each one `MultiMesh` |
| Attributes | `POSITION`, `NORMAL`, `TEXCOORD_0`; no `COLOR_0`, no texture |
| `TEXCOORD_0.x` | Metres along the panel, `0` to `panel_m`, so a post stands on every joint |
| `TEXCOORD_0.y` | Metres above the ribbon deck: `-base_sink_m` at the buried foot, `+height_m` at the top |

- A class id is the mesh name and the glTF material name at once (`Q61`); classes are
  `hong_kong.yaml`'s `railings.classes`. They share `railings.gdshader` and differ in `.tres` mask
  numbers; `verify_railings.gd` checks the dispatch per class.
- `TEXCOORD_0` is a shader payload, not a texture coordinate.
- ⚠️ `railings.gdshader` is `cull_disabled` — the only generated mesh that is — so winding decides
  lighting, not visibility. `railings.json` publishes `facing_away` per class, each must be 0.
  `verify_railings.gd` reads the render mode from the shader source.
- `railings.json` is `RAILINGS_MANIFEST_SCHEMA` 3 with no top-level `drawn_m`: counters below the
  join live under `classes[<id>]` (`drawn_m` = tiled metres, `panels`, `metres_snapped`, `joints`,
  `joint_gap_m`, `bends`, `library_*`, `placements*`).
- ⚠️ The position is registered, not read (`Q60`): 67.9% of surveyed railing metres fall inside
  the drawn ribbon. The longitudinal extent is never stretched; the lateral offset is a rigid
  move bounded by `max_shift_m` and priced by `shift_m`. The push is unconditional, unlike the
  signs' outward-only clamp (`Q78`) — deliberate.

`roadsurface.json` (`SURFACE_MANIFEST_SCHEMA` 12) — an ETL intermediate the game never reads —
carries what only `surface.py` can know, for the stages drawn on or beside the road:

| Key | For |
|---|---|
| `carriageway[].kerb_hidden_m` | Ribbon-metre ranges where a side draws no kerb because a neighbour covers it (railings) |
| `caps` | Each junction cap's hull ring in x/y/z (`Q92`); `DrawnSurface` is the reader |
| `ribbons` | Every drawn strip's two rails, post-trim and post-mitre, in the order `_Builder.strip` received them — quad diagonals depend on it (`Q92`) |
| `opposed_pairs` | Which two edges are halves of one dual carriageway and how far apart (`Q125`); `roadmarks.py` reads it |
| `clusters`, `paint` | `P3-31` cluster caps (`stub_edges`, `count`, `nodes`, `corridors`) and `P3-32` flank caps (`boxes_read`, `stations`, `flanks`, `flank_m2`) — counters only |
| `corridor_half_width_m`, `corridor_offset_m`, `lanes_painted`, `areas` | `Q129`: the level-0 corridor, and the carriageway outside every ribbon as drawn triangles, read as cap-class |
| `join`, `cut_vertices`, `trim_m` | Seam junctions (`P5-7f`), chunk cuts, junction trims |

### `signs.glb` — the published traffic signs (`P3-16`)

A plate per whitelisted sign on the pole `DTAD_TS_POLE_PT` surveyed. **No collider** — a budget
decision pending `P2-6`; breakaway is `B3`.

- 🔴 The position comes from the pole, not the sign: `DTAD_TS_ABV_PT` is a drawing label, a median
  2.63 m off the pole, joined through `GG_NAME`. Nothing publishes which way a sign faces
  (`ANGLE` is symbol-cell rotation), so the facing is derived from host edge, kerb side and
  drive-on-left (`Q62`).
- 🔴 A **library** plus `signs_placements.json` (`P5-2`, `Q115`): one mesh per face variant
  (`TS115`; a mirrored board is its own mesh, `TS414_mirrored`, because a mirror is not a
  transform under `cull_back`), a unit `pole`, and one `signs_text_<code>` quad per lettered code.
  A placement is `landmarks.json`'s transform (`pos`, compass `rot_y_deg`) plus optional `scale`;
  a negative scale is refused. `layer_preview.gd` draws one `MultiMesh` per library mesh (24 draw
  calls on Wan Chai, +35 with shadow passes). `verify_signs.gd` grades the join both ways.
  `signs.json` is `SIGNS_MANIFEST_SCHEMA` 5.

| | |
|---|---|
| Primitives | one per library mesh — a face variant, the pole, a lettering quad per lettered code |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`; no `TEXCOORD_*` |
| `COLOR_0` | The plate livery as sRGB bytes from `hong_kong.yaml`'s `signs.colours` |

- The only road-furniture mesh with a multi-colour `COLOR_0` (four colours in one draw call), so
  `vertex_srgb_to_linear` is mandatory in `signs.gdshader`. Also the one exemption from `Q33`'s
  palette-exposure rule (`test_config.py`).
- ⚠️ `signs.gdshader` is `cull_back`; every plate is drawn twice, face and grey reverse.
  `signs.json`'s `facing_away` must be 0.
- 🔴 Facing is derived per **post**, then turned per **plate** (`Q72`): `_facing_from_side` points
  a post at the traffic it addresses; the NO ENTRY family is turned 180° by `_plate_facing_deg`.
  Without it back-to-back plates are unrepresentable (74 of Wan Chai's 503 posts). Which faces
  turn is config (`SignFace.faces_against_traffic`). `signs.json` publishes `plates_turned` and
  `no_entry_against_flow` (must be 0 — a regression guard, not proof).
- 🔴 The lettering atlas ships as `signs_text.png`, named by `signs_text_atlas` (`Q70`). Not
  embedded: Godot's default `gltf/embedded_image_handling` extracts an embedded image to a file
  the manifest never named, which `sync_generated.sh` deletes. Nothing loads it by path — the key
  exists for `shipped()`. Null where no signs ship, or none are lettered.
- `signs.json`'s `bytes` is `signs.glb` alone; the atlas is `text_atlas_bytes`.

### `signals.glb` — removed (`P3-17`, `Q77`, `P3-35a`)

🚫 Not in the bundle and not in the code. `Q77` dropped the layer — an unlit head asserts a signal
out of service, and a lit one cannot be derived from anything published — and `P3-35a` (`Q133`)
removed the stage, config block, material, verify tool, preview node and tests on the user's call.
`city.json` lost the `signals` key at schema 34. Record: `DECISIONS.md` `Q76`/`Q77`. ⚠️ Its return
is a port to a library + placements (`P5-2`'s shape), not a re-declared block.

### `landmarks.json` — hero building placement

```json
{
  "schema_version": 2,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "landmarks": [
    {
      "id": "hkcec",
      "asset": "res://assets/generated/landmarks/hkcec.glb",
      "transform": { "pos": [102.5, 4.0, 84.0], "rot_y_deg": 0.0 },
      "name": { "en": "Convention Centre", "zh": "會展" },
      "replaces_source_ids": ["B358761603301063"],
      "excluded_bounds": [[8.37, 3.99, -73.57], [209.63, 71.92, 275.45]],
      "triangle_budget": 120000
    }
  ]
}
```

Written by `export.py` from the config's `landmarks:` block (`P3-6`).
`game/scripts/city/landmarks.gd` places the models; `generated_landmarks.gd` is the locator.

- `replaces_source_ids` — building **stems** (the cross-dataset key, `DATA_SOURCES.md`) the ETL
  excludes from the tiles. `export.py --check` holds the set equal, both ways, to what the
  building stage dropped.
- `excluded_bounds` — the game-space AABB union of the excluded meshes, recorded by `buildings.py`
  at exclusion time. `verify_landmarks.gd` probes the tier-0 tiles against its interior. `null`
  only where no stem was claimed.
- `transform.pos` — game metres, `y` the base elevation; models are footprint-centred with
  `y = 0` at the base. `rot_y_deg` is a **compass bearing** (`CityManifest.bearing_deg`); the one
  conversion to a Godot rotation is `generated_landmarks.gd::placement_of`.
- `triangle_budget` (schema 2) — the ceiling `verify_landmarks.gd` holds the model to; 8,000 by
  default, a mesh-sourced hero pins its measured count.
- Two kinds of `.glb`, separated by licence (`LICENSING.md`). An **authored** hero (Central Plaza)
  is committed under `game/assets/authored/landmarks/` (CC BY-SA 4.0, `tools/make_landmark.py`);
  `shipped()` never lists it. A **mesh-sourced** hero (HKCEC) is the government mesh extracted,
  sliced and repainted by `pipeline/landmarks.py` — gitignored, listed under `landmark_assets`,
  never committed. `source_paint` in config declares it and forces `rot_y_deg: 0.0`.

#### The authored door — a hand-made `.glb` (`P5-10`, `Q121`)

The `landmarks:` block is the one way a DCC-authored asset enters the bundle.
`replaces_source_ids` is optional for an authored asset, so a prop can exclude nothing
(`excluded_bounds` is then `null`). A mesh-sourced hero still needs its stems.

| Rule | What happens |
|---|---|
| Path | a `.glb` under `game/assets/authored/landmarks/`, committed, CC BY-SA 4.0. `sync_generated.sh` never touches `authored/` |
| Units and axes | metres, Y-up, footprint-centred, `y = 0` at the base |
| Nodes | names and hierarchy survive import; Godot's suffixes are honoured — `-col` grows a trimesh collider on that node only |
| Materials | an **unrecognised** name keeps the PBR material as authored. A **recognised** name (`city_facade`, `road_markings`, …) takes that layer's `.tres`; the table is `tools/generated_scene_import.gd::SHADERS`. `COLOR_0` under an unrecognised name gets `vertex_color_use_as_albedo` and `vertex_color_is_srgb` |
| Textures | a packed image is extracted beside the asset on first import; commit it and both `.import` sidecars. The no-texture contract covers generated tiles, not this door |
| Budget | `triangle_budget` per entry, 8,000 by default |

Fixture: `assets/authored/fixtures/dcc_roundtrip.glb`, a Blender export (unapplied child scale,
packed image, `-col` node) from `tools/make_dcc_fixture.py`, byte-reproducible.
`tools/verify_authored.gd` grades every row against it, mutation-checked, with or without a built
region.

#### The vehicle door — a car with named material slots (`P5-23`, `Q124`)

The body's shader payload — a surface marker in `UV.y`, a switched lamp circuit in `UV.x`, read by
`vehicle_body.gdshader` — is carried as a **material name** and stamped at import by
`generated_scene_import.gd::vehicle_body` from its `VEHICLE` table. `tools/make_vehicle.py` emits
the same names; `etl/tests/test_make_vehicle.py` binds the two tables.

| Rule | What happens |
|---|---|
| Slots | one slot per part: `vehicle_paint`, `vehicle_glass`, `vehicle_trim`, `vehicle_lamp` (unswitched), and per circuit `vehicle_lamp_brake`, `_reverse`, `_indicator_left`, `_indicator_right`, `_sidelamp`, `_headlamp`, `_roofsign`. The importer stamps `UV = (circuit, marker)` and merges every slot into **one** `vehicle_body` surface on `tuning/vehicle_body.tres` |
| Colour | the slot's base colour, baked into `COLOR_0` as sRGB (`Q27`); a slot already carrying `COLOR_0` keeps it, sRGB-encoded |
| Geometry | one object, transforms applied, origin at the ground centre, `y = 0` at the base, nose toward `-z`. Flat-shaded; no vertex shared between parts |
| Refusal | an unknown `vehicle_…` slot is refused, not guessed: `push_error`, body left as authored, and `verify_authored.gd` fails it as "not one surface" |
| Fixture | `assets/authored/fixtures/dcc_vehicle.glb` from `tools/make_dcc_fixture.py --vehicle`; `verify_authored.gd` classifies every vertex by the box it lies in. The misspelt variant (`--vehicle <out> vehicle_lamp_break`) is the mutation |

### Not part of the contract

`buildings.json`, `roadsurface.json`, `podiums.json`, `carriageway_region.json` and the per-stage
manifests (`arrows.json`, `signs.json`, …) are ETL intermediates written beside their stage
outputs so each stage stays independently runnable. `city.json` is the versioned interface and
`export.py` writes it. **Nothing in the game reads an intermediate**, and `sync_generated.sh`
copies only what the manifest names.

---

## Coordinates

| Item | Value |
|---|---|
| Source CRS | HK1980 Grid, **EPSG:2326** |
| Vertical datum | Hong Kong Principal Datum |
| Game space | Local ENU metres, Y-up, **origin at region NW corner** |

```
game_x =  (easting   - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing  - origin_northing)
```

- `etl/pipeline/hongkong.py` is the only module that states EPSG:2326 (`Q100`). `crs.py` holds the
  arithmetic and takes the codes as arguments; everything else reads the CRS through the config.
- The negation on `z` is forced: Godot is right-handed and Y-up, so east `+X` makes north `−Z`.
  Flip it and the city is mirrored.
- The origin is the NW corner so X runs east and Z runs south from 0, and tile indices are natural
  numbers with row 0 at the north. Origin easting is floored and origin northing **ceiled** —
  rounding outward keeps offsets non-negative, and rounding at all stops a PROJ release
  renumbering every tile.
- ⚠️ Clipping to the region bbox is a requirement of the contract, not an optimisation. `fetch.py`
  downloads every sheet that *intersects* the region, so source data extends past all four edges;
  a consumer must clip before indexing or it gets negative coordinates and tile indices.

### Two frames, and why

Each region is authored in its own local frame, origin at its own NW corner, which keeps the
numbers small (Wan Chai spans 0–1650 m; float32 resolves well under a millimetre).

`city_offset` translates a region's local frame into a city-wide frame anchored on the city's
declared `bounds`, not on any region:

```
city_space = region_local + city_offset
```

- A region loaded alone can ignore `city_offset`. `CityRegions` places each synced region at
  `city_offset − city_offset(frame)`, the frame being the first region in `regions.json` (`P5-9c`).
- Everything is not anchored in city space because Wan Chai would sit ~38 km from the origin, where
  float32 spacing is ~3.9 mm against a suspension sag of 50 mm.
- ⚠️ A city's `bounds` must not change once a `city.json` has shipped: every `city_offset` is
  measured from them. They are declared, not derived from the regions that exist, and `config.py`
  checks every region lies inside them.

---

## Runtime systems

| System | Responsibility | Status |
|---|---|---|
| `CityRegions` | One `region.tscn` per synced region at `city_offset − city_offset(frame)`, each with its tiles; holds the road under a point in every region that has some | ✅ `P5-9c` |
| `CityStreamer` | Loads/unloads tile meshes and road chunks by camera distance, one per region, camera through `to_local`; owns the LOD tier | ✅ `P2-1`, `P5-6`, `P5-9c` |
| `Landmarks` | Places the authored heroes from `landmarks.json`; always resident, no LOD | ✅ `P3-6` |
| `RoadGraph` | Queries over `roadgraph.json` — nearest edge, lane centre, routing | ✅ `P2-2` |
| `RoadSpawn` | Where a car starts, resolved from a fare node, and what it stands in (`Q52`) | ✅ `P2-3` |
| `VehicleController` | Player car: `VehicleBody3D` + arcade overrides — steering rate, top-speed taper, coast drag, drift, collision response, auto-right | ✅ `P0-5`/`P2-3`/`Q50` |
| `InputRouter` | Touch / gamepad / keyboard into one action set (autoload) | 🟡 touch ships 3 of 5 actions; `P2-4` |
| `DebugHud` | Every dev readout, behind `F3` (autoload) | ✅ |
| `BeamBudget` | Hands the renderer's spot-light slots to the cars nearest the camera (autoload) | ✅ |
| `Fence` | Stands the authored barriers where `fence.json` places them, one `MultiMesh` (`prop_batch.gd`) | ✅ `P3-29` |
| `TrafficSystem` | AI vehicles on road-graph splines; trams as scripted blockers | ⬜ `P3-3` |
| `tram.glb` | The published tramway where iB1000 prints it — not a marking on the ribbon (`Q58`). One primitive, no collider | ✅ `P3-14` |
| `arrows.glb` + `arrows_placements.json` | Turn arrows in the lane the ribbon has — not ribbon paint, because the junction fade blanks the approach (`Q59`). Library of one flat glyph per `RM` code; placements carry the transform plus `pitch_deg` and nothing else (`Q54`). No collider | ✅ `P3-15`, `P5-4` |
| `crossings.glb` | Pedestrian-crossing stripes at the surveyed extent; signal yellow and zebra white as two meshes. No collider | ✅ `P3-35g2` |
| `boxjunctions.glb` | Yellow box junctions at the surveyed extents, lifted under the arrows that paint over them. One primitive, no collider | ✅ `P3-18` |
| `roadmarks.glb` | Stop and give-way lines, hosted by the road each one *crosses*, not the nearest. One primitive, no collider | ✅ `P3-23` |
| `signs.glb` + `signs_placements.json` | Traffic signs on the poles TD surveyed. Shape-faced signs only. Library of one mesh per face variant plus a unit pole; one placement per plate, lettering quad and pole (`scale` on the pole). No collider | ✅ `P3-16`, `P5-2` |
| `lamps.glb` + `lamps_placements.json` | Lamp posts on the drawn kerb with a bracket arm over the carriageway; `rot_y_deg` is the arm's bearing. Unlit (`Q38`, `Q26`). Library of one mesh per drawn kind. No collider | ✅ `P3-26`, `P5-3` |
| `railings.glb` + `railings_placements.json` | Railings, bollards, vehicle barriers on the drawn kerb. One unit panel per class, its `.tres` post pitch wide, tiled per run with `pitch_deg`; tiling cost is reported in `railings.json` (`metres_snapped`, `joint_gap_m`, `bends`), never closed by a stretched panel. Three draw calls, `cull_disabled`, no collider | ✅ `P3-19`, `Q61`, `P5-5` |
| `FareSystem` | Fare state machine: idle → hailed → carrying → delivered/failed | ⬜ `P3-1` |
| `ScoreSystem` | Base fare, time bonus, **style chain** and **fare combo** — two distinct multipliers | ⬜ `P3-2` |
| `HUD` | Speed, the bilingual street plate and the wrong-way sign (`P3-25`) ship; minimap, timer and meter are reserved, empty, checked slots. Flat chamfered polygons. `--hud=off` for `P3-9` and art frames | 🟡 `P3-24`; meter, timer and the world-space destination marker are `P3-5a` |
| `AudioDirector` | Engine, radio, callouts, ambience buses | ⬜ Phase 5 |

Every library layer draws one call per library mesh through a `MultiMesh`; each placements document
uses `landmarks.json`'s transform shape, is written beside its `.glb` and is null on its terms.

**Architectural rule:** `scripts/core/` holds pure logic with no `Node` inheritance and no rendering
calls — unit-testable headlessly and portable.

**A vehicle's drive layout is scene data.** `VehicleWheel3D.use_as_traction` is authored per wheel,
each vehicle has its own `HandlingProfile`, and `centre_of_mass_offset_y` plus `roll_influence`
cover a tall van. The roster is in `ART_DESIGN.md`.

⚠️ Drift bias is derived from chassis geometry, not wheel role: `VehicleController._group_axles`
splits wheels by position along the chassis. Keying off `use_as_traction` / `use_as_steering` would
silently invert the drift bias on a front-wheel-drive car.

### Script map

All paths under `game/`.

| Path | Role |
|---|---|
| `scripts/main.gd` | Entry point (`P5-24`): holds `World` and `GUI`, hands the HUD its car through typed exports `level` and `hud`; nothing under `GUI` searches for a car |
| `scripts/city/city_manifest.gd` | `city.json`, typed: tiles, AABBs, per-edge widths and clearances, the lane-width bar, resolved document paths |
| `scripts/city/city_regions.gd` | `CityRegions` (`P5-9c`) |
| `scripts/city/generated_regions.gd` | The one place the generated root is spelled: synced regions, the frame, each directory; `--region=` picks one (`P5-9b`) |
| `scripts/city/road_join.gd` | Two regions' graphs as one, rule for rule with `etl/pipeline/join.py`, plus the per-region id maps (`P5-9d`) |
| `scripts/city/city_streamer.gd` | Loads and frees tiles by distance to their published `aabb`, off the main thread; owns the LOD tier |
| `scripts/core/tile_streaming.gd` | The streaming policy, pure — distance to an `AABB` in, tier out |
| `scripts/core/plan_lattice.gd` | An even, counted grid of plan positions over a region's bounds, used by the region-sweeping verify tools |
| `scripts/city/streaming_profile.gd` | Schema for bands, hysteresis and per-frame budgets; numbers in `tuning/streaming.tres` |
| `scripts/city/road_graph.gd` | One parse per scene; nearest-edge and lane-centre queries over a plan grid. Refuses off-grade edges (`Q13`); expresses, never enforces, passability (`Q51`) |
| `scripts/city/road_spawn.gd` | `basis_facing` builds the rotation from a direction; `Pose.blocked` fails a start line in a wall (`Q52`) |
| `scripts/city/generated_document.gd` | Parse and version-check an ETL JSON document; the stale-copy message exists once |
| `scripts/city/generated_layer.gd` | Locator table for the eight drawn `.glb` layers — `tramway`, `arrows`, `boxjunctions`, `crossings`, `roadmarks`, `railings`, `lamps`, `signs` — with id constants, absence terms and each library's placements document (`P5-1`, `Q115`). Owns the sign text-atlas budget (`Q63`) |
| `scripts/city/generated_placements.gd` | Reads a `*_placements.json` into transforms (`P5-2`) |
| `scripts/city/prop_batch.gd` | One `MultiMesh` over many transforms — how every prop layer draws (`P3-29`, `Q115`) |
| `scripts/city/generated_{road_graph,fares,landmarks,fence}.gd` | Locators for the JSON documents. `generated_fares.gd` alone knows that document's shape; `generated_landmarks.gd::placement_of` is the one place a compass bearing becomes a Godot rotation |
| `scripts/city/landmarks.gd`, `scripts/city/fence.gd` | Place the heroes and the barriers; always resident |
| `scripts/city/building_index.gd` | Which source object a point of a tile belongs to, from the glTF mesh `extras` (`P5-11`) |
| `scripts/city/mesh_contract.gd` | The mesh rules every generated asset is held to, plus `triangles` and `bounds`; also the shader-dispatch and `TEXCOORD_1` importer-drift checks |
| `scripts/city/preview_draw.gd` | Flat ribbons and the unshaded vertex-colour material for dev previews |
| `scripts/city/{tile,road,fare}_preview.gd`, `layer_preview.gd` | Dev previews. `layer_preview.gd` draws any drawn layer by the `layer` id on its node. 🔴 The layer nodes live in `scenes/region.tscn`, which `city_drive.tscn` and `city_preview.tscn` both place through `CityRegions`; `verify_city.gd` holds its `layer` ids against `generated_layer.gd`'s table in both directions (`Q73`, `Q82`, `Q115`). `road` and `fare` are preview-only by design (`road` z-fights the surface; `city_drive.tscn` carries `GraphOverlay`). Not performance measurements |
| `scripts/city/road_graph_overlay.gd` | Dev: resolved edge, lane centre and legal direction under the car |
| `scripts/city/drive_harness.gd` | `DriveHarness`, the level root: places the car on the resolved start line and returns it when it leaves the world. `Main` reads the car from it |
| `scripts/city/asset_viewer.gd` | Dev: one `.glb` named by `--asset=` under `clean_daylight.tscn`, with what the importer did to it (`P5-22`, `Q124`). Needs no built region |
| `scripts/city/greybox_builder.gd` | Builds the `P0-5b` grey-box circuit from `assets/authored/greybox_wanchai.json` |
| `scripts/camera/chase_camera.gd`, `chase_profile.gd` | The follow camera (`P2-5`, `Q98`); numbers in `tuning/camera.tres` |
| `scripts/camera/free_look_camera.gd` | Dev fly camera; bypasses `InputRouter` |
| `scripts/input/input_router.gd`, `touch_profile.gd` | `InputRouter` and the touch travel schema (`tuning/touch.tres`) |
| `scripts/vehicle/vehicle_controller.gd`, `handling_profile.gd` | The car and its tuning schema (`tuning/handling.tres`) |
| `scripts/vehicle/vehicle_lamps.gd`, `sun_glint.gd`, `beam_budget.gd`, `beam_profile.gd` | Lamp circuits written as instance uniforms (`P3-11d`), the sun direction for `vehicle_body.gdshader`, and the spot-light budget |
| `scripts/world/lighting_rig.gd` | `LightingRig`: an environment, a sun and the exposure (`P5-28b`, `Q38`) |
| `scripts/ui/debug_hud.gd`, `fps_counter.gd` | The one owner of dev chrome, off by default; the counter is a `Label` it builds and stops counting while hidden (`Q119`) |
| `scripts/ui/hud.gd` | `Hud`. Reads the car `Main` handed it. Samples speed at 10 Hz and the road graph at 5 Hz, sets text only on change, registers a raw-versus-displayed readout with `DebugHud` |
| `scripts/ui/hud_layout.gd` | Every HUD rect and the touch geometry. ⚠️ `touch_zone_*` is where taps are detected and the HUD may overlap it; `thumb_rest_*` is what a fingertip covers and the HUD may not (`Q80`). Holds the shared placer — `place`, `axis`, `inset_for_safe_area` — so HUD and zones resolve in the same frame (`Q97`) |
| `scripts/ui/hud_style.gd` | Palette, chamfer, type scale; deliberately not the road's paint constants (`Q53`). ⚠️ No `@export` defaults, like `HandlingProfile` and `StreamingProfile` — a default is a second copy of the tuning table (`Q80`) |
| `scripts/ui/chamfer_panel.gd`, `accent_bar.gd` | The HUD's one shape (a polygon, not a `StyleBox`), and the speed chip's signed acceleration bar; `bar_span` is a pure static so `verify_hud.gd` can grade its direction |
| `scripts/ui/street_plate.gd`, `no_entry_icon.gd` | The plate's tuning and substitution table (`tuning/street_plate.json`, shared with `tools/font_coverage.py`), and the wrong-way NO ENTRY icon (`P3-25`) |
| `scripts/core/cmdline.gd` | `Cmdline`, the one reader of the command line, both halves (`P5-25`) |
| `scripts/core/street_tracker.gd`, `wrong_way_monitor.gd` | Pure policy: which street the plate names (dwell, unnamed edges are not evidence, `changes` counter), and whether the car runs against a one-way |
| `scripts/core/wrong_way_profile.gd`, `street_tracker_profile.gd` | Schemas for `tuning/wrong_way.tres` and `tuning/street_tracker.tres` (`P5-26`). No `@export` defaults; both refuse a zero |
| `scenes/world/golden_hour.tscn`, `clean_daylight.tscn` | The two lighting rigs; both dev scenes instance `clean_daylight.tscn`. Instance a rig rather than authoring a second Environment |
| `scenes/region.tscn` | One region's drawn layers, landmarks and fence |
| `tools/generated_scene_import.gd` | Import fixup — see `[importer_defaults]`. Also the vehicle door (`P5-23`): `vehicle_*` slots are stamped and merged into one `vehicle_body` surface; an unknown `vehicle_*` name is refused |

Verify tools (`game/tools/`, run by `tools/check.sh`):

| Tool | Checks |
|---|---|
| `verify_settings.gd` | Project settings read back through `ProjectSettings` (`Q119`) — see "Checks" |
| `verify_tiles.gd` | The mesh contract, per tier of every tile the manifest names |
| `verify_city.gd` | `city.json` — georeferencing, per-tier AABB containment, `bounds_game`, named documents exist, layer nodes in `region.tscn` |
| `verify_road_surface.gd` | Every `roads/<tile>.glb` chunk: one draw call, UVs, trimesh collision, the marking codec, kerbside extent over the union |
| `verify_road_graph.gd` | `RoadGraph` queries — off-grade refusal, edge resolution, lane placement against published width, per-station width, `Q51` passability (`nearest_edge` still answers on a blocked edge), and a 1 ms query budget over a region-wide lattice |
| `verify_join.gd` | The runtime merge against `etl/out/<frame>+<other>/`, field by field; SKIP on one region; `--dump=` for `reachability.py --graph-dir` (`P5-9d`) |
| `verify_city_streamer.gd` | Band edges, hysteresis both ways, and a residency sweep against the draw-call budget |
| `verify_spawn.gd` | Orientation against the edge vector, nearside-lane placement, drop height, resolved edge against the fare node, and that a car fits (`Q52`). Builds the transposed basis and five known-clearance start lines and requires each to fail or answer — nothing in the shipped city fires the guard |
| `verify_landmarks.gd` | Assets load with mesh and `-col` collision, triangle budget, placed AABB near `bounds_game`, no tier-0 tile triangle inside an excluded footprint's core |
| `verify_fence.gd` | `fence.json` against the prop it names and the graph it fences (`P3-29`) |
| `verify_{tramway,arrows,boxjunctions,crossings,roadmarks,railings,signs,lamps}.gd` | One per drawn layer — mesh contract, draw-call and collider claims, per-class material dispatch. ⚠️ A new railing class needs a row in `verify_railings.gd`, `generated_scene_import.gd` and the config; `check.sh` fails if they disagree |
| `verify_beam_budget.gd` | The spot-light cap is never exceeded or under-spent, nearest cars win, a beamless rig takes no slot, a despawn hands its slot on. No built region needed |
| `verify_hud.gd` | Thumb-rest reservation (overlapping a tap zone stays legal), light-plate/dark-chip rule, the plate's font and substitution table, the street tracker from both sides of its dwell. No built region needed |
| `verify_mesh_contract.gd` | The `Q63` texture amendment — asserts the *failures* (undeclared, over budget, never arrives), since no shipped asset declares a texture. No built region needed |
| `verify_input.gd` | The touch scheme — zone geometry, both relative axes, two thumbs, per-axis override, `--touch=mouse`. Drives the router's `_input` directly. No built region needed. 🔴 Carries a 30 s watchdog: a `SceneTree` tool that aborts before `quit()` never exits, wedges `check.sh`, and a wedged instance rewrites `project.godot` on shutdown (`Q97`) |
| `verify_vehicle.gd` | The taxi's wiring — `vehicle_body.tres` via the name channel, lamp instance uniforms, integral `UV` payload on lens vertices only, rig position, beams authored dark and below horizontal. No built region; ⚠️ sees no frame, so cannot tell the shader compiled |
| `verify_authored.gd` | The authored-asset door against a real Blender export, `assets/authored/fixtures/dcc_vehicle.glb` (`P5-10`, `Q121`) |

---

## Input architecture

One action set; three schemes feed it and no gameplay script knows which is live.

| Action | Router type | Keyboard | Gamepad | Touch (`P2-4`) |
|---|---|---|---|---|
| `steer` | `float`, −1…1 | `A` / `D`, ← / → | Left stick X (axis 0) | ✅ thumb 2, horizontal from touch origin |
| `accelerate` | `float`, 0…1 | `W`, ↑ | RT (axis 5) | ✅ thumb 1, above touch origin |
| `brake_reverse` | `float`, 0…1 | `S`, ↓ | LT (axis 4) | ✅ thumb 1, below touch origin |
| `drift` | `bool` | `Space` | A / Cross (button 0) | ⬜ thumb 2, held past the drift threshold |
| `look_back` | `bool` | `C` | B / Circle (button 1) | ⬜ unplaced |

Deadzones are **0.2** on the axes and **0.5** on the buttons, in `project.godot`'s `[input]` map.

- Touch ships three of five (`Q97`). `drift` needs a threshold and hysteresis only a handset can
  pick (`Q83`, `P0-3b`); `look_back` is unplaced. Thumb 2's vertical axis is read and discarded, not
  lent to another control.
- 🔴 Touch values are merged in `InputRouter`, never fed through the action map:
  `get_action_strength` returns 0 under the 0.2 deadzone, which would eat the first fifth of every
  thumb's travel.
- ⚠️ Touch overrides the action map per axis; it does not replace it. Every scripted drive runs on
  `Input.action_press` (`drive.sh --hold=`), so an unconditional touch read would zero every
  regression run and each would still exit `DRIVER OK`.
- `InputRouter` samples in `_physics_process`: physics steps run before idle processing, so sampling
  in `_process` costs ~16.7 ms of latency. As an autoload it runs before any gameplay node.

### The three schemes

**Keyboard** is digital on every action; `steer_attack_s` / `steer_release_s` in
`VehicleController` do all the smoothing.

**Gamepad** is analog on steer and both triggers; `drift` and `look_back` are face buttons.
⚠️ Both triggers are spent, so `drift` stays a `bool`. Drift duration is the vehicle's job and is
⬜ not built — the drift ends on the tick the input stops (`Q50`, `Q83`).

**Touch** is two thumbs:

| | Horizontal | Vertical |
|---|---|---|
| **thumb 1** (bottom **right**) | free — `look_back` candidate | `accelerate` above origin, `brake_reverse` below |
| **thumb 2** (bottom **left**) | `steer` | `drift` while held past the threshold |

- Left steers, right drives (`Q97`; `Q83` left it open). The side lives in
  `HudLayout.steer_zone()` / `drive_zone()`, so swapping it is one edit. The rects are
  `touch_zone_left` / `touch_zone_right`.
- 🔴 Both thumbs are relative: the landing point is the origin and travel from it is the input.
  Absolute sliders were refused — `speed` and `street_plate` share a baseline at y 860 and the thumb
  rests start at y 880, so a slider collides with the HUD at 20 px of growth (`Q83`).
- `brake_reverse` is the negative half of one longitudinal axis, matching the one-pedal
  brake-and-reverse of `P0-5b/c/d`; centre is coast.
- ⚠️ `drift` is a held offset on thumb 2 — not a tap, an origin latch or a screen-edge zone (`Q83`).
  Its threshold needs hysteresis (larger to enter than to leave), and is a *distance* from the
  origin, not a horizontal line: a thumb sweeps an arc, and a straight boundary would inject
  steering into every drift entry.
- ⚠️ Zone geometry is `tuning/hud_layout.tres`, read through `HudLayout`'s own placer — the zones
  are two invisible `MOUSE_FILTER_IGNORE` Controls anchored as the HUD's slots are, so they share
  the anchor rule and safe-area inset. `verify_hud.gd` fails if they disagree. They sit on their
  own `CanvasLayer`: `--hud=off` frees the HUD, and a touch layer parented to it would lose the
  steering. Do not conflate `touch_zone_*` with `thumb_rest_*` (`Q80`, script map above).

---

## Performance budget

⚠️ One tier ships, the desktop one. Nothing in `game/scripts/` reads `OS.has_feature`,
`OS.get_name` or a quality setting; the only platform branching is the `.mobile` / `.web` suffixes
in `project.godot`. The mobile tier is unbuilt and blocked on `P0-3b` (signing identity, the two
floor handsets).

| Metric | Mobile tier | Desktop tier |
|---|---|---|
| Target | 60 fps @ 1080p | 60 fps @ 1440p |
| Draw calls | < 150 | < 400 |
| Visible triangles | < 300k | < 1M |
| Texture memory | < 128 MB | < 512 MB |
| Bundle size | < 200 MB (iOS cellular threshold) | no hard limit |
| Shadows | Vehicle blob shadow only ⚠️ | Two directional cascades at 400 m |

⚠️ Shots with shadows off looked flat and blown out. A mobile tier needs the ambient and tonemap
re-tuned around a blob shadow, not the shadow switched off.

**Device floor:** iOS **A13** (iPhone SE 2nd gen / iPhone 11); Android **Adreno 618** tier, Vulkan
1.1, 4 GB RAM. The Android floor is the one that constrains the budget.

Techniques, in order of what they buy:

1. Merge at build time: untextured vertex-colour buildings merge into one mesh per tile.
2. LOD via ETL-generated tiers, not runtime decimation.
3. One draw call per generated layer mesh. Repeated objects — signs, lamps, arrows, the barrier
   family — ship as a library stood by a `MultiMesh` (`Q115`; `P3-29`: +1 draw call against +36 for
   per-scene instancing), multiplied by the shadow passes per library mesh. The road, boxes and
   stop lines stay merged because nothing in them repeats.
4. Occlusion is largely free in dense street canyons.

---

## Build pipeline

```
etl/  →  python -m pipeline --region wan_chai
      →  etl/out/<region>/{city.json, roadgraph.json, roads/*.glb, …, tiles/*.glb}
      →  tools/sync_generated.sh <region>... → game/assets/generated/<region>/ + regions.json
      →  Godot export presets → iOS / Android / desktop / web-demo
```

Twenty stages in one chain, the list `etl/pipeline/__main__.py` owns: `fetch`, `podiums`,
`buildings`, `landmarks`, `roads`, `carve`, `region`, `surface`, `clearance`, `fence`, `fares`,
`tramway`, `arrows`, `boxjunctions`, `crossings`, `roadmarks`, `railings`, `signs`, `lamps`,
`export`. Each also runs alone:

```sh
python -m pipeline.buildings --region wan_chai
python -m pipeline --region wan_chai --from roads   # resume mid-chain
```

- The chain invokes each stage through the same entry point, so full and partial builds cannot
  drift. A non-zero exit stops the run. `fetch` is the only stage that touches the network;
  `--force` belongs to it and is refused with a `--from` that skips it.
- `export` also validates what no single stage checks — a fare node naming a missing edge, a tile
  whose GLB was never written, a document from another region, geometry outside the bounds — always
  against the source document, never the manifest. `python -m pipeline.export … --check` runs the
  checks alone.
- The ETL is not run by CI; its output is a versioned build artefact.

**Sync.** `tools/sync_generated.sh <region> [<region>...]` copies into
`game/assets/generated/<region>/` exactly the files `city.json` names, asked of the ETL
(`python -m pipeline.export … --list`), so intermediates stay out and stale tiles are removed.
🔴 The resident list is the argument list (`P5-9b`): it is written to
`game/assets/generated/regions.json`, the first region is the frame, and anything else at the top
level is swept. Every locator asks `generated_regions.gd` for its directory, `check.sh` runs each
verify tool once per listed region with `--region=`, and a landmark `asset` under
`res://assets/generated/` means that region's bundle (`CityManifest.resolve_asset`).

**`game/export_presets.cfg`** is committed comment-free in the export dialog's own form. Never put
keystore passwords, provisioning profiles or signing identities in it. ⚠️ `com.hktaxiq.game` is a
`P0-3b` placeholder in three places — `application/bundle_identifier` twice, `package/unique_name`
once — and all three must change before any store submission.

**Then check in-engine:** `--import` first (a fresh sync has no import sidecars), then
`tools/check.sh`.

### Looking at it

| Scene | For |
|---|---|
| `scenes/dev/city_preview.tscn` | Fly around. Every tile at one tier, no streaming — not a performance measurement |
| `scenes/main.tscn` | Drive. `World` instances `scenes/city_drive.tscn` (taxi on the road collider, chase camera); `GUI` holds the HUD |
| `scenes/dev/asset_viewer.tscn`, `skidpad.tscn`, `greybox.tscn` | One authored `.glb`; the handling pad (`tools/skidpad.sh`); the `P0-5b` circuit |

- The spawn is resolved at runtime: `drive_harness.gd` asks `RoadSpawn.at_fare_node` for
  `spawn_fare_id`, default `f_004` — "Expo Drive eastbound underneath HKCEC Phase II", a real taxi
  stand.
- The heading is not supplied. A zero heading makes `nearest_edge` take the edge's vertex order,
  which `P1-3` made the legal direction; passing the car's rotation would let the car decide which
  way a street runs.
- The car sits in the nearside lane, never on the centreline, where opposed ribbons and junction
  caps leave coplanar collision triangles. Y is lane centre plus ride height plus
  `DROP_CLEARANCE_M`: the car is dropped, and the harness's fall-detection floor moves with the
  spawn.
- ⚠️ The fallback `Transform3D` literal in `city_drive.tscn` is a trap: the 12-float constructor
  fills `Basis` rows, while forward is `-basis.z`, a column. Writing columns transposes the basis,
  which mirrors the heading about world −Z — 180° wrong on an east-west street and a silent 0° on a
  north-south one. Use `RoadSpawn.basis_facing`. Eyeball check: the harbour is north.
- The flyovers cannot be driven onto (`Q13`). Off the carriageway is solid ground (`P3-10`). The
  fall-out harness still runs — the region has edges, and level −1 runs under the terrain (`Q21`).

---

## Constraints

1. No runtime network calls. The game is fully offline.
2. No engine-specific formats out of the ETL — glTF and JSON only.
3. Hong Kong facts live in `etl/config/hong_kong.yaml` (tuning, vocabularies) or
   `etl/pipeline/hongkong.py` (the CRS pair, drive-on-the-left, branch sign codes) — one home
   each, never both (`Q100`).
4. Tuning values live in `game/tuning/*.tres`, never as constants in scripts.
