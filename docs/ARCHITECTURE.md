# Architecture

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Engine | **Godot 4.7** | MIT, no royalties or seat fees |
| Renderer | **Mobile** (primary), Compatibility for the web demo | Forward+ only if a desktop tier ever justifies it |
| Physics | **Jolt** — Godot's default since 4.4 | Trimesh collision, and `VehicleBody3D` for the car since `Q50` reversed `P0-5a` (2026-08-18) |
| Engine language | **GDScript**, statically typed | See below |
| ETL | **Python 3.11+** — numpy, pyproj, pyyaml, pyogrio | Build-time only |
| Targets | iOS, Android, Windows/macOS/Linux (Steam) | Web export reserved for the free demo slice |

### ⚠️ The importer can reinstate `VehicleWheel3D` behind your back

Godot's glTF importer converts nodes by **name suffix**. A node whose name ends in `_wheel` is
imported as a `VehicleWheel3D`, not as the `MeshInstance3D` the file describes — and the same
applies to `_col`, `_convcol`, `_navmesh`, `_occ`, `_rigid` and `_vehicle`.

`P3-11` shipped its tyre mesh as `taxi_wheel.glb`, so every wheel arrived wrapped in a
`VehicleWheel3D` with no `VehicleBody3D` above it. The wheels stopped drawing. **Nothing reported an
error**: the import succeeded, `tools/check.sh` passed, the driver printed `DRIVER OK`, and the only
symptom was a car that rendered without wheels. The mesh is now `taxi_tyre.glb`.

Worth its own heading because of *what* it reinstated. `P0-5a` had measured `VehicleWheel3D` and
rejected it — its friction is isotropic, so it cannot express a drift — and a filename put it back
into the scene tree. **A locked decision can be undone by a naming convention.** Check the
instantiated tree, not the source scene, when geometry goes missing.

⚠️ **`Q50` made the car a real `VehicleBody3D`, and that makes this trap worse rather than moot.**
The tyre mesh is now a child of an actual `VehicleWheel3D`, so a rename back to `taxi_wheel.glb`
would nest a wheel inside a wheel — which the engine accepts silently, because the outer one is
legitimately parented to the body. The mesh is `taxi_tyre.glb` and must stay so.

### Why GDScript, not C#

C# platform support in Godot 4.7 (re-verified against the official docs 2026-07-29): desktop fully
supported, **Android and iOS experimental**, **web not supported at all**. Mobile is a primary target
and the web demo is the planned marketing funnel, so C# compromises both. GDScript also hot-reloads,
which directly speeds up the vehicle-feel tuning loop that carries most of this project's risk.

**Performance escape hatch:** if a system profiles too slow, use **GDExtension** (C++, or Rust via
godot-rust). It preserves every export target, including web. Do not reach for C#.

> **Note for JS/TS developers:** GDScript is Python-like with optional static typing. Always annotate
> (`var speed: float = 0.0`) — it is faster *and* catches errors the untyped form won't.
> `signal`/`connect` is the event-emitter equivalent. `.tres` resource files are the idiomatic home
> for tuning data, roughly a typed JSON config.

---

## Project settings

⚠️ **`game/project.godot` is regenerated from scratch whenever Project Settings is saved in the
editor**, discarding every comment. This table is the durable record — check it against the file
after anyone touches the settings dialog.

⚠️ **It also drops hand-written feature overrides** — settings with a `.web` / `.mobile` suffix.
Observed three times in one session: `renderer/rendering_method.web` disappeared on every editor
save, which silently breaks web export because WebGL2 cannot run the mobile renderer. Editing the
file by hand is what makes them fragile; the editor only persists an override it created itself.
**Set them through Project Settings → right-click the property → "Override For…"**. Until that is
done for a given key, re-check with `grep -c 'rendering_method.web' game/project.godot` (must be 1).

| Setting | Value | Why |
|---|---|---|
| `rendering/renderer/rendering_method` | `mobile` | Locked decision. Set as the **base** value, not only as a `.mobile` override, so the editor and desktop builds preview the renderer the phone will run |
| `rendering/renderer/rendering_method.web` | `gl_compatibility` | Web export is WebGL2-only |
| `rendering/textures/vram_compression/import_etc2_astc` | `true` | Godot refuses to export **any** arm64 target without it — iOS, Android and Apple Silicon macOS alike |
| `physics/3d/physics_engine` | `Jolt Physics` | Locked decision. The default since 4.4, but stated so the project does not silently follow a changed engine default |
| `application/run/max_fps.mobile` | `60` | Rendering uncapped on a 90/120 Hz panel buys nothing above the 60fps target and throttles the device. Desktop stays uncapped |
| `display/window/stretch/mode` | `canvas_items` | Resolution-independent UI; desktop is a target alongside phones |
| `[importer_defaults] scene.import_script/path` | `res://tools/generated_scene_import.gd` | Godot 4.7's glTF importer reads `COLOR_0` but leaves `vertex_color_use_as_albedo` **off**, so every generated tile imports as a white block. Nothing in the glTF can express it. Set as an importer *default* rather than per file: generated assets are gitignored, so their `.import` files do not survive a fresh clone |

**Deliberately not set**, both measured rather than reasoned:

- `directional_shadow/soft_shadow_filter_quality` — Godot already ships a `.mobile` override of `0`,
  and feature overrides beat an explicitly-set base value, so setting the base only degrades desktop.
- `directional_shadow/size` — the engine default is already 4096 (`.mobile` 2048). The next step up,
  8192², is **~134 MB** of shadow map against a 512 MB desktop texture budget; measured, raising the
  atlas moved texture memory by exactly 134,217,728 B.

**Cascade count costs no VRAM.** Godot allocates one `size × size` depth texture whatever the split
mode and subdivides the rect per cascade — four 2048² quadrants and one 4096² measured identical at
79,592,192 B. Cascades buy geometry submission, not memory. There are no `lights_and_shadows/*` keys
in `project.godot` at all: cascade count and distance are node properties on the one shared sun.

**Autoloads:** `DebugHud`, `FpsCounter`, `InputRouter`, registered in that order — the counter asks
the HUD what to show in its `_ready`, and an autoload listed later does not exist yet. All three run
every frame for the life of the process, so treat them as hot-path code.

### The debug overlay

`DebugHud` (`scripts/ui/debug_hud.gd`) owns every dev readout: the frame counter, the position block,
the text blocks overlays register with it, and — through `view_changed` — the road graph's chevrons.
**`F3` cycles off → minimal → full**, and `--debug-view=off|minimal|full` sets where a run starts.

| View | Shows | Draw calls |
|---|---|---|
| `off` | nothing. **The default, in every build** | 19 |
| `minimal` | position block and frame counter | 27 |
| `full` | plus registered readouts and 3D debug geometry | 38 |

Measured on `city_drive.tscn` at 2.0 s into the standard driver run. Against the <150 budget that is
affordable, but it is not free: left on, a fifth of the scene's draw calls go on debug text — and it
sits over every screenshot anyone judges the city from. That second reason, more than the cost, is
why the default is off.

`drive.sh` is the exception: it appends `--debug-view=minimal` unless the caller names a view, on the
grounds that a scripted run is someone debugging and a screenshot that cannot say where it was taken
cannot be acted on. The position block reports game metres **and** the source-CRS grid reference
(`CityManifest.to_grid`, the inverse of `crs.py`'s `to_game`), so a frame can be checked against the
ETL's own data rather than only against another frame.

⚠️ The toggle is a **raw key**, not an action: the `[input]` map is the game's, and dev keys stay out
of it (`free_look_camera.gd` set that precedent). So `drive.sh --hold=` cannot press it — scripted
runs use the flag.

---

## Checks

**Godot never signals failure through its exit code.** A script that fails to parse, a warning
promoted to an error, a dependency that will not compile — all of them print and exit `0`.
`tools/check.sh` exists to turn that output into an exit code, and is the only thing in the repo that
does. Running `--import` by hand tells you nothing unless you read the output.

| Step | Covers | In CI |
|---|---|---|
| `gdformat --check` | Layout across all of `game/` | yes |
| `--import` | Autoloads and what they reach; also builds `game/.godot/` | yes |
| warnings sweep | `--check-only` per script, grepping for `treated as error` | yes |
| `verify_beam_budget` | The spot-light cap — needs no built region, so CI can check it | yes |
| `verify_vehicle` | The taxi's shader binding, lamp channels, imported payload and beam aim — the taxi is committed, so this needs no built region either | yes |
| `verify_city`, `verify_tiles`, `verify_road_surface`, `verify_road_graph`, `verify_city_streamer`, `verify_spawn`, `verify_landmarks` | The generated-asset contracts | **no** |

The sweep is separate from `--import` because `--import` does not do the job: measured, an untyped
variable planted in `greybox_builder.gd` went unreported, because the import step compiles only
autoloads and what they reach. **The sweep must run with `game/` as the project directory** — run
from elsewhere, `res://` does not resolve, every script silently analyses clean, and the check passes
having checked nothing.

⚠️ **A verify tool that appears to hang is a parse error, not slow work.** When a script fails to
compile, `_init` never runs, so `quit()` is never called and the SceneTree spins forever. Warnings
are promoted to errors here, so something as small as an unused parameter does it. If a step sits
there, read the log for `Parse Error` / `Compile Error` rather than waiting it out — and when
scripting a Godot run, give it a watchdog rather than a long timeout.

⚠️ **Verify tools `preload` every dependency rather than naming a `class_name` global**, and that is
load-bearing. Global classes resolve through the gitignored
`game/.godot/global_script_class_cache.cfg`, so on a fresh clone a tool referencing one fails to
*parse*, `_init` never runs, `quit(1)` is never reached, and the SceneTree exits **0** — the check
reports success having checked nothing. **Never reference a `class_name` global from a `--script`
tool.**

⚠️ **Autoloads are registered on the first frame, not before, and a verify tool that loads a scene
must `await process_frame` first.** Anything loaded from `_init` compiles while `InputRouter` is
unresolvable, so `vehicle_controller.gd` fails to compile, GDScript **caches the broken class**, and
the scene instances a `RigidBody3D` with a *null script* — measured. The run then prints
`SCRIPT ERROR`, which `check.sh` fails on, having graded a car that never loaded.
`tools/verify_vehicle.gd` and `tools/skidpad_ablation.gd` both open with that `await` for this
reason. A scene instantiated but never added to the tree must also be `free()`d before `quit()`, or
Godot reports a page of `ERROR: ... leaked at exit` lines that read like a failure and are not one.

⚠️ **Running Godot rewrites two committed config files**, stripping every comment and, in
`project.godot`, the `rendering_method.web` line the web export needs. Restore both afterwards and
*verify*, because `git checkout` prints `Updated 0 paths from the index` whether or not it restored
anything:

```sh
git checkout game/project.godot game/export_presets.cfg
git diff --exit-code game/project.godot game/export_presets.cfg   # this is the check
```

**Four grading tools sit beside the suite and are run by hand.** All read only the *shipped bundle*
and share no code with the pipeline, because a stage cannot mark its own work — ask the ETL's own
sampler about the ETL's own output and it reads |error| p90 0.02 m, which is the sampler agreeing
with itself.

| Tool | Answers |
|---|---|
| `tools/deck_error.py` | `Q20` — how far the drawn carriageway sits from the deck beneath it, *vertically*, sampled down centrelines. Gates on \|error\| p90, deepest intrusion, and the share it managed to measure at all |
| `tools/overhang.py` | `Q22`/`Q23` — whether there is a deck beneath it at all, sampled *across the full drawn width*. A ribbon can pass the first and fail the second |
| `tools/ground_clearance.py` | `Q18`/`Q24` — whether the drawn ground stands *in* the at-grade carriageway. Sizes `buildings.ground_sink_m`, and gates the sink separately from the road's own shape |
| `tools/carriageway_occupancy.py` | `Q19` — whether anything **solid stands in the road at bumper height**, buildings and structure told apart by vertex colour. The only one that gates per *edge* rather than region-wide, because `RoadGraph` routes on edges and a share cannot tell a wall across the road from clutter beside it. ⚠️ **Fails today**. Since `Q51` it also grades a number the pipeline publishes for itself — `clearance.py`'s — and the two disagree by 21 edges against 26, recorded rather than reconciled |

**`tools/narrowing.py` sits beside them and is not one of them.** It prices a *proposal* — what
`Q19`'s clearances would read at a lower `widen_default` — rather than grading what shipped, and it
does that by importing `pipeline.clearance` and reusing it whole. That is the opposite of the rule
the four above keep, and deliberate: the question is not whether the measurement is right, which
`carriageway_occupancy.py` answers, but what the same measurement says at a different width. A
second implementation would confound the two. Hand-run, reads the ETL out tree rather than the
shipped bundle, and needs no rebuild — buildings do not move when the ribbon narrows. It **refuses
to print a table whose baseline column does not reproduce `clearance.json` edge for edge**: the
1.60x column is the one thing in the sweep that can be checked against something, so it is a
precondition rather than a diagnostic.

`deck_error.py` owns the shared bundle reader (`bundle_arguments`, `load_bundle`, `log_bundle`,
`Faces`, `wears`, `nearest`); `overhang.py` owns the shared width sweep (`walk_width`,
`cross_section`, `left_of`, `half_width_at`) and the other two import it, because reimplementing
that walk means rediscovering its duplicated-vertex guard the hard way.

⚠️ **A tool that needs two passes over the carriageway must still *walk* it once.**
`carriageway_occupancy.py` genuinely needs two — the occupier index can only be pruned to the band
the road occupies, so the road has to be measured before the buildings are read — and writing the
walk out twice cost **22 s of a 47 s run** *and*, far worse, made the prune's superset property a
convention rather than a guarantee: pass one visiting less than pass two asks about reads as
**clear**, which is the one direction these tools must never flatter. It records the walk into a
`Lattice` and replays it instead.

### GDScript warnings

The `[debug]` block promotes 21 GDScript warnings to errors. This is the engine's own type-aware
checker, and the only one available that resolves types at all: a grammar-level linter sees `basis.z`
as an identifier and a dot, where the engine sees a `Vector3` on a `Basis`.

**Level 1 is invisible.** Warnings only reach stdout at level `2`; a warning left at `1` shows up in
the editor's script panel and nowhere else, and the contributor workflow is deliberately headless.
Every enforced warning is therefore at `2`.

**Enforced (`=2`):** `untyped_declaration` · `shadowed_variable`, `shadowed_variable_base_class` ·
`confusable_identifier`, `confusable_local_declaration` · `integer_division`, `narrowing_conversion`
· `unused_variable`, `unused_parameter`, `unused_local_constant`, `unused_private_class_variable`,
`unused_signal` · `standalone_expression`, `standalone_ternary`, `redundant_await` ·
`incompatible_ternary`, `int_as_enum_without_cast`, `int_as_enum_without_match` ·
`get_node_default_without_onready`, `onready_with_export` · `native_method_override`.

**Deliberately not enforced**, with counts measured at the time:

- `inferred_declaration` (~25 hits). It flags `:=`, which *is* static typing — just inferred. The
  `CLAUDE.md` rule asks for static types, not for spelling every one of them out.
- `unsafe_method_access` / `unsafe_property_access` / `unsafe_cast` / `unsafe_call_argument` (~21)
  and `return_value_discarded` (~8). Both trace to a boundary the design chose: generated JSON
  arrives as `Variant`, and `Packed*Array.append()` returns a `bool` nobody reads. Revisit if the
  data contract ever gains a typed loading layer.
- The remaining ~22 sit at engine defaults. `unassigned_variable`, `unreachable_code` and
  `assert_always_false` look worth promoting and were measured as costing nothing.

**This is not a bug-catcher.** None of the four defects recorded under `P0-5b`/`P0-5c` — inverted
steering sign, framerate-dependent drag, an `@export`ed `Node3D` silently null from a hand-authored
`.tscn`, wheel raycasts accepting wall faces — would have been caught by any linter. A review pass
caught them.

### Formatting

`gdformat` (from `gdtoolkit`, in the `dev` extra) is the GDScript counterpart to `ruff format`. Its
default line length is 100, matching `ruff`, so it needs no config file. **`gdlint` is installed but
deliberately not wired in:** it reported 16 hits of one cosmetic rule across four preview scripts,
and it cannot check static typing, which is the convention that actually matters here.

### CI

`.github/workflows/ci.yml` runs on every push to `main` and every pull request, in two jobs: `ruff` +
`pytest` on Python 3.11 and 3.13, and `tools/check.sh` against the Godot version pinned in the
workflow. It runs the script rather than repeating its steps in YAML, for the reason the script
exists: reimplemented in YAML, the Godot steps would pass on failure.

**CI cannot check the generated-asset contracts.** `game/assets/generated/` is gitignored build
output, so a fresh checkout has no city. The workflow sets `VERIFY_GENERATED=0`, which skips those
tools and *prints that it skipped them* — an unannounced skip would be the same silence the script
was written to break. Giving CI a city means running the ETL there, whose first act is downloading
~320 MB from a government server; that is a deliberate non-goal on every push.

---

## Repo layout

```
hk-taxi-Q/
├── CLAUDE.md                    # agent instructions — read first
├── docs/
├── etl/                         # Python: geodata → game assets (build time)
│   ├── config/cities/
│   │   └── hong_kong.yaml       # CRS, bounds, source URLs, tiling — ALL city specifics
│   ├── pipeline/
│   │   ├── config.py            # loads cities/*.yaml — the only route city facts take in
│   │   ├── crs.py               # ONLY module that knows about EPSG:2326
│   │   ├── fetch.py             # download from CSDI / data.gov.hk, cache to sources/
│   │   ├── documents.py         # read/write a stage's JSON + its schema check; no policy
│   │   ├── gltf.py              # glTF read + GLB write; no dependency
│   │   ├── gdb.py               # geodatabase layers + WKB → numpy; format only, no policy
│   │   ├── mesh.py              # merge, partition, LOD collapse — geometry, no policy
│   │   ├── terrain.py           # terrain / structure mesh → sampleable height field
│   │   ├── buildings.py         # sheets → vertex-coloured tiles + LOD tiers
│   │   ├── roads.py             # Road Network geodatabase → roadgraph.json
│   │   ├── surface.py           # roadgraph.json → roads.glb; ribbon, kerbs, junctions
│   │   ├── clearance.py         # what stands in the ribbon → clear width per station
│   │   ├── fares.py             # taxi stands + PUDO + POIs → fare nodes
│   │   ├── export.py            # → city.json, assembles and validates the stage outputs
│   │   └── __main__.py          # `python -m pipeline` — every stage, in order
│   ├── sources/<city>/<source>/ # raw downloads — GITIGNORED
│   ├── out/<city>/<region>/     # pipeline output — GITIGNORED
│   └── tests/
├── game/                        # Godot project
│   ├── project.godot
│   ├── export_presets.cfg       # COMMITTED — never put signing credentials here
│   ├── scenes/
│   │   ├── dev/                 # grey-box circuit, city preview, city drive
│   │   └── world/               # shared rigs: lighting, sky
│   ├── scripts/
│   │   ├── core/                # pure logic, minimal engine coupling
│   │   ├── city/                # tile streaming, road graph runtime
│   │   ├── vehicle/  traffic/  fares/  input/  ui/  camera/
│   ├── assets/
│   │   ├── generated/           # ETL output — GITIGNORED, build artefact
│   │   ├── authored/            # hero buildings, vehicles, UI — COMMITTED
│   │   └── shaders/
│   ├── tuning/                  # .tres resources: handling, streaming, fares, scoring
│   └── tools/                   # headless scripts — import fixups, verify tools
└── tools/                       # dev scripts: check, sync, export, grading
```

⚠️ **`scenes/dev/` is not shipped — except that `run/main_scene` currently boots
`scenes/dev/city_drive.tscn`.** A knowing placeholder: the scene needs the gitignored
`assets/generated/`, so a fresh clone boots to an empty world with only a `push_warning`. An export
is a demo rather than a build until there is a real main scene — but since `P2-1` put `CityStreamer`
on the boot path in place of `tile_preview.gd`, it is no longer a demo that blows the frame budget:
268,709 primitives at the spawn against the 1.16 M the preview cost.

**Why the ETL is a separate Python project:** it runs rarely, at build time, and needs GDAL — which
has no good Godot equivalent. Keeping it out of the engine also keeps it reusable for the second
city.

---

## Data contract

The interface between ETL and game. **Versioned — change both sides together and bump
`schema_version`.** All positions are game-space metres.

> **When to bump:** where a consumer would be **wrong** to keep its old interpretation, not wherever
> bytes change. `P2-7` bumped `roadgraph.json` because `polyline.y` began meaning something new while
> looking identical — the case a diff cannot show you — and did *not* bump `roads.glb`, whose
> geometry moved but whose attributes kept their meaning.

### `city.json` — manifest

```json
{
  "schema_version": 8,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "source_crs": "EPSG:2326",
  "origin": { "easting": 835765.0, "northing": 816125.0, "elevation": 0.0 },
  "city_offset": [38379.0, 0.0, 32826.0],
  "bounds_game": { "min": [-11.343, -13.049, -18.802], "max": [1656.889, 378.532, 923.32] },
  "tile_size_m": 150,
  "tiles": [
    {
      "id": "t_00_00",
      "lods": ["tiles/t_00_00_lod0.glb", "tiles/t_00_00_lod1.glb"],
      "aabb": [[8.37,4.935,-16.588],[167.562,70.801,165.268]]
    }
  ],
  "road_graph": "roadgraph.json",
  "road_surface": "roads.glb",
  "carriageway": [
    { "edge": 651, "half_width_m": [5.12, 5.12, 4.32, 3.2],
      "clear_width_m": [-1.0, 10.24, 8.5, 0.0] }
  ],
  "lane_width_m": 3.2,
  "fares": "fares.json",
  "landmarks": "landmarks.json",
  "landmark_assets": ["landmarks/hkcec.glb"],
  "etl_version": "0.1.0",
  "generated_utc": "2026-07-30T20:04:03Z"
}
```

`origin` is computed by the ETL from the region bounds, never authored — `floor(min_easting)` and
`ceil(max_northing)`, i.e. the region's **north-west** corner. The game never needs it; it is what
puts a game-space position back on the source map.

**The manifest names the other documents, it does not contain them.** The road graph is 0.65 MB on
disk and ~6 MB parsed, and `RoadGraph` wants it at a different moment from when `CityStreamer` wants
the tile list. Each of the three is separately versioned. A build ships exactly what the manifest
names — **138 files and 54.1 MB** for Wan Chai, exporting to a **39.0 MB** PCK with tile collision.

**The game must read the manifest to find its tiles — there is no fallback.** In the editor `res://`
is a real directory and `DirAccess.get_files_at` lists it; in an exported build it is a PCK archive
Godot's virtual filesystem will not enumerate, so the same call returns nothing and the city renders
empty **with no error**. `scripts/city/city_manifest.gd` is the only supported route.

⚠️ **`carriageway` is the drawn half-width, and the game cannot derive it.** `roadgraph.json`
publishes the **authored** street (`lanes × lane_width_m`) while `surface.py` draws the ribbon at
`width_m × widen_for(...)` — 1.6× by default and **1.0× on structure**, where the deck is a fixed
width the ribbon must not overhang. So a consumer must read this table rather than assume the drawn
width exceeds the authored one. The widening lives on the ETL's surface style, deliberately: *"the
graph is a description of the city, this is how wide and how kerbed to draw it. A change here never
changes `roadgraph.json`."* Without it a lane centre falls short by a quarter of the widening —
0.96 m on a two-lane street — putting a car that much nearer the seam where opposed ribbons overlap
and a suspension ray hunts between two coplanar triangles.

⚠️ **One value per station since schema 4**, indexed by that edge's `roadgraph.json` polyline and the
same length as it. `elevation_level` is an attribute of a whole edge, but a road becomes a bridge
partway along one. Reading `[0]` as if it covered the edge is right on 769 of the region's 797 edges
and 0.96 m out on the rest, which is exactly the error this table exists to prevent. `RoadGraph`
warns and falls back to the authored width rather than failing; `verify_road_graph.gd` treats the
table's absence as an error.

⚠️ **`clear_width_m` is what *stands in* the tarmac, and no consumer can derive it either.**
Published since schema 9 (`Q51`), one value per station beside `half_width_m` and indexed the same
way, so both come off one station. It is the widest continuous gap a car could get through at that
cross-section, measured by `clearance.py` between 0.30 m and 2.00 m above the deck — the same band
`Q19` measures over, so the two stay comparable. **`-1.0` means no cross-section was judged there**,
because `surface.py` had held the ribbon back for a junction cap; negative rather than zero because
no real clearance can be, and zero is the one value that would read as *blocked solid* on precisely
the stations that are not. `lane_width_m` travels with it as the bar: `roadgraph.json`'s `width_m`
is `lanes × lane_width_m` **hand-tuned upward for playability**, so dividing it back does not
recover this number. `RoadGraph` reads the pair as `is_passable` / `is_routable` and — deliberately
— does **not** fold either into `nearest_edge`.

⚠️ **`bounds_game` is the union of the content, not the region rectangle.** Wan Chai's declared
region is 1650 × 887 m; its geometry spans 1737 × 977 m, because a building is assigned to a tile
whole and may overhang, and because the road ribbon is drawn outward from centrelines that run right
up to the edge. A consumer sizing a spatial partition, framing a camera, or placing diegetic map
edges off the rectangle will clip real geometry.

`generated_utc` is a build stamp and the **only** field that changes between two builds of identical
inputs — verified by rebuilding from a clean `out/` and diffing. Strip it before diffing two builds.

#### Tiles

`lods` is ordered nearest-first, one file per tier, matching `lod_cell_sizes_m` in city config —
except where `class_lod_cell_sizes_m` holds a mesh class back. A tier is **not** a single cell size:
a building decimates at 1.5 m and an elevated road deck at 0.5 m, because a deck thinner than the
cell flattens into it. The tile is still one mesh and one draw call, because each class is collapsed
separately and merged afterwards. See `ART_DESIGN.md` "LOD policy".

⚠️ **The ground is decimated before it is tiled, not after** (`Q25`). Every other class is cut into
tiles and then decimated per tile — which is safe for a building, because a building is assigned to
one tile whole and never cut. Cutting a *continuous surface* first makes each side of a boundary
average over different vertices, so the two land in different places and the sheet tears: measured
at **15.65%** of probes within 2 m of a tile boundary with no ground over them, against 0.61%
beyond 10 m. Decimating the region's ground once and cutting the result closes that by construction.

⚠️ **`tiles[].aabb` is the union of the tiers a build actually ships, not of the source geometry.**
Decimation moves corners and drops anything thinner than a cell, so a source box can describe
geometry no shipped mesh contains — one Wan Chai tile declared a height 19 m past its own LOD0. Nor
is tier 0's box enough on its own: `collapse` buckets on `floor(position / cell_m)` and averages, so
a coarser grid can leave an extreme vertex alone in its cell and preserve it where a finer grid
averaged it inward, measured at 12.03 m on `t_01_02`. `verify_city.gd` asserts every tier is
contained and the union is tight to 1 cm.

**A tile's `aabb` can be larger than the tile.** Buildings are assigned to a tile whole, by their
centre, so one may overhang its neighbour by half a footprint — measured at up to 222 m across a
150 m tile. **Use the `aabb` for culling and streaming distance, never the tile's grid position.**
Tile vertices are in region game space, so a tile needs no transform; that is why `city.json` gives
tiles an `aabb` but no position.

**Tile output carries no textures.** One material, one primitive, colour in `COLOR_0` — that is what
makes a tile one draw call, checked in-engine by `verify_tiles.gd`. Since `P3-7` it also carries
`TEXCOORD_0`, which is **not** a texture coordinate: no image is sampled, and `merge` still refuses a
textured mesh outright.

⚠️ **"No textures" is stricter than it sounds, and the strict part is enforced in code rather than
only stated here.** `scripts/city/mesh_contract.gd` walks **every shader uniform** and fails on any
that holds a `Texture`, not just the `BaseMaterial3D` albedo/normal/ORM slots — *"a sampler bound here
would ship an image into a bundle specified to carry none while every other check passed."* So a
single region-wide data map sampled by world position — a sky-visibility or AO bake, which needs no
UVs and adds no draw call — is **not** a loophole in this contract. It is a deliberate amendment to
it, and it has to change `mesh_contract.gd` and this paragraph together. The check exists to force
that conversation rather than to make it impossible.

| Attribute | Meaning |
|---|---|
| `COLOR_0.rgb` | The surface's albedo, **sRGB-encoded**, as normalised `uint8`. Every consumer must linearise it — see the warning below |
| `TEXCOORD_0.x` | Metres above **that source object's own base**. A vertex knows its world Y, not where its building starts, and the region's ground moves 40 m — so world Y is not even a proxy. Metres rather than a 0-1 fraction because the floor *count* is the signature the window shader exists to carry |
| `TEXCOORD_0.y` | `floor()` is a `SurfaceClass` marker — 0 façade, 1 ground, 2 structure. `fract()` is a per-object phase in 1/256 steps, so neighbouring towers do not line their window rows up |
| `TEXCOORD_1.x` | The packed **façade-survey state** (`Q40`/`Q41`), a non-negative integer, constant per source building: `code = glz + 4·tint + 1024·grammar`. `glz`: 0 refused · 1 not glazed · 2 glazed (the reader's verdict). `tint`: 0 refused/absent, else `t = 1..240` with `t−1 = L_bin·16 + b_bin` over `L* ∈ [5, 65]` in 15 bins of 4.0 and `b* ∈ [−16, +16]` in 16 bins of 2.0 (dark-mode glass tint, written only when `glz = 2`). `grammar`: 0 refused · 1 curtain · 2 punched · 3 fin · 4 blank · 5 mixed, pinned to `GRAMMARS` in `tools/facade_grammar.py`. **Every field's 0 means "refused — fall back to the hash"**, so an absent channel, an unsurveyed city and a refused building are the same state. Max legal code 6082 ≪ 2²⁴, so every code is exact in float32; consumers still decode with `floor(x + 0.5)` first |
| `TEXCOORD_1.y` | **Reserved for `Q42`'s riders and written `0.0` in schema 6.** The layout is fixed now so each field can land later, individually, with no further bump — filling a field a refusal-aware consumer already reads as "0 = refused" changes bytes, not meaning. Bits 0–6: storey pitch, `k = 1..65` → `2.5 + (k−1)/32` m (1/32 steps are exact binary fractions). Bits 7–11: podium floors, `k−1` floors with 1 = "no podium", distinct from refusal. Bits 12–13: balconies, 1 no · 2 yes. Bits 14–16: emphasis, 1 horizontal · 2 vertical · 3 grid · 4 none. Max 131,071 < 2²⁴. Each rider owes its own validation before it is written or read |
| Material name | **`city_facade`**, and the name is the contract. glTF cannot say "use this shader", so `tools/generated_scene_import.gd` dispatches on the name and hands the tile `tuning/city_facade.tres`; everything else in the bundle keeps its `BaseMaterial3D` |

⚠️ **The `TEXCOORD_1` codec constants are contract, not tuning.** The bin ranges and field
multipliers above are mirrored as constants in `etl/pipeline/buildings.py` (`facade_state`) and
`assets/shaders/city_facade_clean.gdshader` (`SURVEY_*`) — the same standing as the 1/256 phase — and
this table is the tiebreak. They do not belong in the city yaml: a codec has no per-city meaning, and
a one-sided "tuning" of a bin edge decodes every surveyed building silently wrong, which is precisely
the drift the version exists to catch. What *is* tuning is how the decoded state is applied:
`survey_apply` and `glass_astar` in `tuning/city_facade.tres`.

⚠️ **Data-supplied podium metres enter through the floors field, not around it** (`Q47`, argued
2026-08-11). `Q47`'s route makes an iB1000 `P` block the boundary authority where a tower meets one —
in metres — and bits 7–11 still carry floors. The two agree by construction: the pack converts
metres → floors against the same packed storey pitch (bits 0–6) the shader multiplies back, so the
round-trip lands within half a pitch, and a boundary between floor lines was never renderable
anyway — window rows exist only on the storey grid. A separately-quantised metres field would add a
second grid that cannot agree with the first. Full-precision metres, the block references and the
mechanism that won (`authored > data > survey > hash`) stay in the ETL intermediate `podiums.json`,
which `export.py` never names: the runtime does not branch on provenance, and `R4`'s grading — its
only consumer — runs in the pipeline. Nothing in this route bumps `schema_version`: `y` is still all
zeros, and `R4`'s eventual write remains the "filling a reserved field" case above, whose
`verify_tiles.gd` range check moves in that commit.

⚠️ **The phase is quantised to 1/256 because float32 rounds it into the next marker otherwise.** The
raw seed reaches 1 − 2⁻³², and float32's spacing near 2.0 is ~2.4e-7, so `STRUCTURE + 0.9999999998`
becomes exactly `3.0` — an unknown marker with a lost phase, on whichever viaduct drew a high seed.
1/256 is exactly representable at every marker, so `floor` and `fract` round-trip in the shader.

⚠️ **The marker is derived from the palette, not from a config key.** A class with a flat
`class_materials` entry is one whose colour does not depend on its height, which is exactly the set
with no floors to band; anything the height ramp colours is a façade. So a second city gets the right
answer from its own palette, and no class name reaches pipeline logic (hard rule 3).

⚠️ **Three places have to agree and only one of them can fail loudly.** The ETL names the material,
the import script recognises the name, the shader reads the payload — and if any link breaks, every
tile keeps its default `BaseMaterial3D` and renders in flat vertex colour, which is what the city
looked like *before* `P3-7`. There is no error and nothing on screen that reads as broken.
`verify_tiles.gd` therefore asserts both the payload and the resolved material path.

**The finest tier ships collision; no other tier does.** The tier-0 mesh is named `<tile_id>-col`,
and Godot's glTF importer reads that suffix into a `StaticBody3D` carrying a
`ConcavePolygonShape3D` — the same mechanism `roads.glb` uses, chosen for the same reason: the
collider is part of the asset, so `CityStreamer` builds no shape at load and the collider cannot
drift from the geometry it is drawn from. Only the finest tier, because a tier is selected by
distance and the coarse one is resident only *beyond* the 250 m near band, where nothing can touch a
building. `verify_tiles.gd` asserts it in both directions — present on tier 0, absent on every other
— because a suffix that spread would be invisible in every screenshot and show up only as bundle
bytes. **Measured cost: 5.17 MB of PCK** (21.10 → 26.27 MB, one variable changed), not the 14.91 MB
tier 0's 434,149 triangles come to as raw faces; the pack compresses them.

**Terrain ships in the tile primitive since `P3-10`.** It is one more entry in `buildings.classes`,
so it collapses at its own cell size (4 m / 8 m) and then merges with the massing: **+87,649
triangles at LOD0, no texture, and no extra draw call.** No `schema_version` bumped — nothing was
added, removed or renamed, and no attribute changed meaning. A consumer reading a tile is not
*wrong* to keep its old interpretation; it simply draws more. `tiles[].aabb` and `bounds_game` grew
(1668 × 942 m → 1737 × 977 m, quoted as 1728 until `P3-7` rebuilt and checked it against a `HEAD`
baseline) and the region gained a 66th tile, because ground reaches corners no
building did.

⚠️ **The tier-0 collider now includes the ground, and nothing in the ETL says so.** The suffix goes
on the *merged* mesh, so anything in `classes` collides at that tier whether or not it was asked to
— which is what makes the pavement drivable, and is worth knowing before adding a third class.
`buildings.ground_sink_m` drops the ground under the kerb so the two surfaces do not fight;
`tools/ground_clearance.py` grades it.

**The vertex stream gained `TEXCOORD_0` in `P3-7`, and `schema_version` went 4 to 5.** Its meaning is
in the table above. Two things about what it cost:

⚠️ **It ships float32, not the "~2 bytes/vertex quantised" this file predicted, and the prediction
was out by more than the encoding.** Measured from PCKs with one variable changed: **32.36 → 36.37 MB,
+4.01 MB**, against 937,889 vertices across both tiers — 7.50 MB of raw VEC2 that the pack compresses
by 47%. Quantising to `unorm16` would halve the raw side and save perhaps 2 MB, at the price of a
scale factor in the contract on both sides. **Not done, because the bundle budget is 200 MB and this
build is at 36.37**; the note is here so a later region short of room knows where 2 MB is hiding.
Peak ETL RSS went **800 → 900 MB** on the same machine, from materialising 8 bytes a vertex through
the bucket phase where `colour_for` gets away with a broadcast view.

**The vertex stream gained `TEXCOORD_1` in the `Q40`/`Q41` plumbing, and `schema_version` went 5
to 6.** Its meaning is in the table above: the measured façade verdicts — reader-glazed, binned
glass tint, five-state grammar — packed as one integer state code per building, with the second
float reserved at a documented layout so `Q42`'s riders can land without a third bump (the same
argument the reserved GROUND marker made below). The channel ships **float32 VEC2, not `unorm16`,
for the `TEXCOORD_0` reasons plus one of its own**: the budget is 200 MB and the build is nowhere
near it, and a 16-bit path could not hold the codes exactly anyway — half floats carry 11 mantissa
bits against codes that reach 6082 now and 131,071 when the riders land. Measured from PCKs with
one variable changed: **36.32 → 36.57 MB, +0.24 MB** — 7.50 MB of raw VEC2 that the pack compresses
by 97%. Far cheaper than `TEXCOORD_0`'s +4.01 MB because the payload is a per-building constant
(and `y` all zeros), which the compressor rewards where `TEXCOORD_0`'s per-vertex fractions gave it
nothing — `Q40`'s "~2 MB" estimate had this reasoning and still overshot eightfold. ETL peak RSS
did not repeat `TEXCOORD_0`'s +100 MB either: `facade_uv2` is a broadcast view through the bucket
phase, materialised only at the tile merge.

⚠️ **Two importer settings would silently destroy this channel, and `verify_tiles.gd` now checks
both.** `meshes/light_baking = 2` (Static Lightmaps) makes Godot's importer generate its own UV2
unwrap over the payload — fractions in `[0, 1]` that pass every visual inspection; the tiles ship
`= 1` (Static). And any 16-bit vertex-attribute compression corrupts large codes. The verifier
asserts the `.import` setting directly and scans every `TEXCOORD_1` value for exactness and field
range, so either regression fails the check instead of hashing 1,600 surveyed buildings.

⚠️ **The ground marker was reserved here rather than left to a later task.** Merging bought the
ground a free draw call and cost it its own material, so a ground-only treatment — slope blending, a
PBR-ish roughness variation, any ground shader — had nothing to select on. `SurfaceClass.GROUND` is in
the payload now and the shader ignores it, which cost one commit instead of a second schema bump. What
it does **not** buy is a usable height: `TEXCOORD_0.x` measures from each source mesh's own base, and
the ground's meshes are sheet-shaped, so the value is not comparable across a sheet boundary.

⚠️ **`COLOR_0` is sRGB-encoded, and every consumer has to linearise it itself.** The ETL picks
colours in CIELAB and writes the sRGB bytes, because sRGB is what 8 bits are *for* — it spends its
codes where the eye can tell them apart, and a linear `uint8` would starve the shadows to gild
highlights nobody can separate. The cost is that nothing downstream converts for free. Godot 4 has no
`vertex_color_is_srgb` **render mode** (it survives only as a `BaseMaterial3D` flag), so the two
facade shaders each carry a `vertex_srgb_to_linear` of their own, and `generated_scene_import.gd`
sets the flag for everything else — the road surface included.

This was silent until `Q27`. Skipping the conversion does not merely lighten the city: sRGB read as
linear is *brighter than it should be*, and brightness the albedo did not ask for is brightness that
does not vary with albedo. Measured, **57%** of a lit facade pixel's luminance was albedo-independent,
and a per-building albedo difference reached the screen at **a third** of its size. No lighting change
touches it, which is why it survived a full sweep of the rig. If a future consumer of `COLOR_0`
forgets this, the symptom is a pale city whose palette "does not seem to do anything" — reach for
`tools/frame_stats.py` before reaching for the lights.

⚠️ `COLOR_0.a` is a constant `255` today and looks like the cheaper place for a shader mask. It is
not: `generated_scene_import.gd` sets `vertex_color_use_as_albedo` project-wide, and an opaque
`BaseMaterial3D` ignores albedo alpha only until somebody enables transparency on a tile — after
which the city renders see-through with no error. `TEXCOORD_0` has no such failure mode.

### `roadgraph.json` — drivable network

```json
{
  "schema_version": 3,
  "nodes": [{ "id": 1, "pos": [120.5, 4.0, 300.2], "kind": "junction" }],
  "edges": [
    {
      "id": 1, "from": 1, "to": 2,
      "polyline": [[120.5, 4.0, 300.2], [180.0, 4.1, 305.0]],
      "on_structure": [false, false],
      "direction": "both",
      "lanes": 3,
      "width_m": 11.0,
      "speed_limit_kph": 50,
      "bus_lane": false,
      "tram_tracks": false,
      "elevation_level": 0,
      "road_name": { "en": "Gloucester Road", "zh": "告士打道" }
    }
  ],
  "turn_restrictions": [{ "from_edge": 1, "via_node": 2, "to_edge": 5 }]
}
```

| Field | Source |
|---|---|
| `direction` | `TRAVEL_DIRECTION` (1 = bidirectional → `both`, 3 = one-way → `forward`). Closed vocabulary: **only `both` and `forward` are ever written.** A city whose source codes direction against its own digitisation declares `backward` in config, and the ETL normalises it away by reversing the polyline |
| `turn_restrictions` | `TURN_ID` + `EDGE(1-8)FID`. Edge references are **indices into `edges`**, not source ids |
| `speed_limit_kph` | `SPEED_LIMIT` layer where present, joined on `ROUTE_ID`; otherwise the city default. Hong Kong signs only exceptions, so **the default covers ~90% of edges** |
| `bus_lane` | `BUS_ONLY_LANE` layer, joined on `ROUTE_ID` |
| `tram_tracks` | ⚠️ **Hand-authored.** Not in the source. A list of street names in city config |
| `lanes` | ⚠️ **Not published.** Road Network v2 carries no lane attribute in any layer. Authored per road class in city config, keyed on speed limit |
| `width_m` | Derived from `lanes`, then hand-tuned upward for playability |
| `elevation_level` | `ELEVATION` integer attribute (−1/0/1 in this region). An ordinal level, **not** a height, and never a height — it says which deck a road is on, not where that deck is. Since `P2-7` it is also **not** what decides `y` |
| `polyline` / `pos` | Game-space metres, `y` measured **from ground level, not from the vertical datum**. Since schema 2 an off-grade edge's `y` is **sampled from the map sheets' `INFRASTRUCTURE` structure**, so it follows the real deck and varies along an edge — median grade 2.47%, p90 8.04%. Level-0 edges meeting a node another level also reaches are lifted onto the ramp they sit on. Where the structure covers nothing, `elevation_levels` in city config supplies the flat offset. A node's `y` is the **level nearest grade** among the edges meeting it, and the highest end on that level |
| `on_structure` | ⚠️ **Derived, not published by any source.** One flag per vertex, added in schema 3: true where that station's height came from sampled structure. `elevation_level` says which deck an edge *belongs to*; this says which of its stations are *standing on one*, and the two differ because a road becomes a bridge partway along an edge. Only `roads.py` can produce it — `y` cannot stand in, since `ground: terrain` puts an at-grade hill road at 49 m. All-false for a city that samples no decks. **897 stations** in Wan Chai, **546 m** of level-0 centreline |
| `road_name` | `STREET_ENAME` / `STREET_CNAME` — **bilingual names ship in the source.** The null sentinel has four spellings; normalise NFKC and fold dashes before comparing |

**Nodes are formed where centrelines share an endpoint, and nothing else.** Not where they cross: two
roads crossing in plan at different `ELEVATION` share no endpoint, so no junction is invented.
Conversely `ELEVATION` is deliberately **not** part of a node's identity — every place two levels
meet at a shared endpoint is a ramp touching down, and splitting there severs the elevated network
from the ground one.

**Geometry is clipped to the region, not kept whole.** Unlike a building — assigned to a tile whole
and allowed to overhang — a road feature is cut at the boundary, because a polyline cut in two is two
polylines with nothing to seam. Without it, 14% of the region's road length is geometry the player
cannot reach, including a tunnel running 570 m out into the harbour.

`node.kind` is `junction` where three or more edge ends meet and `endpoint` otherwise. Degree, not
the source's intersection layer: two centrelines meeting end to end is one road continuing through a
geometry break, and the source records those as intersections too.

### `roads.glb` — the drivable surface

One vertex-coloured mesh for the whole region, generated from `roadgraph.json` by `surface.py`. Not
tiled: at 35k triangles it is a fortieth of the massing, it is on screen whenever the player is, and
splitting it would buy nothing but seams and draw calls.

| Property | Value |
|---|---|
| Mesh name | `road_surface-col` |
| Primitives | 1 — one draw call, like a tile |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`, `TEXCOORD_0`; no texture |
| `TEXCOORD_0` | **U is a lane coordinate**, 0 at the **nearside** kerb line and `lanes` at the offside, so an integer U is a lane boundary whatever the widening did to the metres. V is metres along the carriageway. Junction caps carry `(0, 0)` — a junction is not a length of lane |

Nearside means left of travel, because Hong Kong drives on the left. The sign is not a free
convention: flip it and every asymmetric marking — a kerbside bus lane, a nearside double yellow —
lands on the wrong side of the road while the geometry still renders perfectly.

**The `-col` suffix is load-bearing**, for the same reason as on tiles. `verify_road_surface.gd`
checks that it survived, because nothing on the Python side can see it.

**Opposed carriageway pairs are drawn as two overlapping ribbons and deliberately not merged**:
measured across the region's six pairs, the widening already closes every gap between them.

**Junctions are capped per elevation level.** The cap is the convex hull of the carriageway corners
each arm presents to the node, which is what makes it meet every arm across its full width. Arms at
different levels are never joined.

⚠️ **A cap overlaps its arms rather than abutting them** where they stop at different distances from
the node — 210 of the region's 1,398 trimmed ends, 6,051 m² of 52,985 m² of cap area. Invisible
today, since cap and carriageway are the same colour at the same height in one material; it becomes
visible when the markings shader lands, because the cap carries no lane coordinate and the ribbon
beneath it does. The fix is a non-convex cap — the union boundary rather than the hull — which is
polygon clipping and is deliberately not built yet.

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

`kind` ∈ `taxi_stand` | `pudo` | `poi`. `stand_category` is null unless `kind` is `taxi_stand`.

**`pos` is the source position — the kerbside, not the carriageway.** 11 of Wan Chai's 29 fare nodes
lie outside even the widened road surface, because the published points sit on the pavement and the
ribbon is drawn from centrelines. This is where the *passenger* stands. Where the *taxi* stops is
`nearest_edge` at `edge_t`, and that is derivable while the kerbside position would not be if it
were overwritten. `pos.y` comes off the snapped edge rather than the terrain.

**`edge_t`** is the fraction along that edge's plan length. Without it `nearest_edge` names a road
that can be 200 m long, and the game would have to redo the projection the ETL already did.

**`pickup` and `dropoff`** say what may happen at the node. Both are true at a taxi stand; a quarter
of Hong Kong's published pick-up/drop-off points are **drop-off only** (66 of 275 territory-wide, 4
of the region's 15), and letting a player hail a fare at one would be wrong in a way a local would
notice.

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

Written by `export.py` from the city config's `landmarks:` block (`P3-6`) — ~2 entries derived
from config plus one CRS conversion, which is why the *document* is not a stage of its own. The
manifest names it under the `landmarks` key; `game/scripts/city/landmarks.gd` places the models,
and `generated_landmarks.gd` is the locator. The mesh-sourced *models* do have a stage:
`pipeline/landmarks.py` extracts each `source_paint` landmark's own source mesh, slices it at the
ribbon elevations so vertex colour can hold a crisp band, repaints it, and writes it into the out
tree — the manifest lists those files under `landmark_assets`, `shipped()` carries them, and
`sync_generated.sh` copies them like any tile.

**`triangle_budget`** (schema 2) is the ceiling `verify_landmarks.gd` holds the placed model to —
per entry, because the authored heroes budget 8k where a mesh-sourced hero pins its measured
count. Schema 1 → 2 was bumped for the asset set, not the added field: a v1 document names a
committed `assets/authored/landmarks/hkcec.glb` that no longer exists, and a stale bundle would
draw a hole where the hero stands — the same "version gates the whole asset set" argument as
`city.json` 7 → 8.

`replaces_source_ids` tells the ETL to **exclude** those buildings from the generated tile mesh so
the hand-made model doesn't z-fight with the extruded one. Its entries are **stems** — the
cross-dataset building key `DATA_SOURCES.md` establishes, the same keying as the façade survey and
`P3-7a`'s override table. `export.py --check` holds the set equal, in both directions, to what the
building stage actually dropped.

**`excluded_bounds`** is the game-space AABB union of the meshes each entry excluded, recorded by
`buildings.py` at exclusion time — the only moment a mesh still has an identity, since `merge`
erases it. `verify_landmarks.gd` probes the shipped tier-0 tiles against its interior core, which
is the in-engine half of "source geometry excluded"; `null` means no stem matched, which
validation refuses.

**`transform.pos`** is game-space metres with `y` the building's base elevation; models are
authored footprint-centred with `y = 0` at the base. **`rot_y_deg` is a compass bearing** — 0 at
north, rising eastward, the `CityManifest.bearing_deg` convention — and the one conversion to a
Godot rotation lives in `generated_landmarks.gd::placement_of` (game north is -Z, so a bearing is
a negative rotation about +Y).

The `.glb` assets come in two kinds, and the licence is what separates them (`LICENSING.md`). An
*authored* hero (Central Plaza) is **committed** under `game/assets/authored/landmarks/`
(CC BY-SA 4.0, generated by `tools/make_landmark.py`); it is not build output, so `shipped()`
never lists it and `sync_generated.sh` never touches it. A *mesh-sourced* hero (HKCEC) is the
government's own building mesh repainted by `pipeline/landmarks.py` — generated city data under
government terms, gitignored, shipped from `game/assets/generated/landmarks/`, and never
committed. The config's `source_paint` block is what declares the second kind, and it forces
`rot_y_deg: 0.0` because the extracted mesh keeps its source orientation.

### Not part of the contract

`buildings.json` and `roadsurface.json` are ETL intermediates written beside their stage outputs, so
that each stage stays independently runnable. `city.json` is the versioned interface and `export.py`
is what writes it. **Nothing in the game should read either**, and `sync_generated.sh` keeps them out
of the bundle by copying only what the manifest names.

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

**`etl/pipeline/crs.py` is the only module permitted to reference EPSG:2326.** Everything else reads
the CRS from city config. This is what makes the second city cheap.

**The negation on `z` is forced, not chosen.** Godot is right-handed and Y-up, so rotating `+X` by
90° counter-clockwise about `+Y` lands on `−Z`: if east is `+X` then north must be `−Z`. Flip it and
the city is mirrored — a plausible-looking map no local recognises.

**The origin sits at the north-west corner.** Because the Z sign is forced, anchoring at the
*northern* edge is the only way to keep the region in the positive quadrant: X runs east from 0 and Z
runs south from 0, so tile indices are natural numbers with row 0 at the north, as in a raster.
Origin easting is floored and origin northing is **ceiled** — rounding outward keeps every offset
inside the region non-negative, and rounding at all stops a sixth-decimal difference between PROJ
releases renumbering every tile.

⚠️ **Non-negativity is a property of the region, not of the source data — so clipping to the region
bbox is a requirement of this contract, not an optimisation.** `fetch.py` deliberately downloads
every map sheet that *intersects* the region, so the building data on disk extends past all four
edges. Any vertex north or west of the region still yields a negative coordinate and a negative tile
index. Whatever consumes the sheets must clip before indexing.

### Two frames, and why

Each region's geometry is authored in its **own** local frame, origin at its own NW corner. That is
what keeps the numbers the player interacts with small: Wan Chai spans 0–1650 m, where float32
resolves to well under a millimetre.

`city_offset` is the translation from a region's local frame into a **city-wide** frame shared by
every region — anchored on the city's declared `bounds`, not on any region:

```
city_space = region_local + city_offset
```

**A region loaded on its own can ignore `city_offset` entirely.** It exists so two regions can be
placed correctly relative to each other without either giving up its local precision. Anchoring
everything in city space would put Wan Chai ~38 km from the origin, where float32 spacing is ~3.9 mm
— invisible on a building and awkward on a vehicle whose suspension sag is 50 mm.

⚠️ **A city's `bounds` must not change once a `city.json` has shipped.** Every region's `city_offset`
is measured from them, so moving them silently relocates every region already published. They are
declared rather than derived from the regions that exist, for the same reason. `config.py` checks
every region lies inside them.

---

## Runtime systems

| System | Responsibility | Status |
|---|---|---|
| `CityStreamer` | Load/unload tile meshes by camera distance; owns the LOD tier | ✅ `P2-1` |
| `Landmarks` | Place the authored heroes from `landmarks.json`; always resident, no LOD | ✅ `P3-6` |
| `RoadGraph` | Runtime queries over `roadgraph.json` — nearest edge, lane centre, routing | ✅ `P2-2` |
| `RoadSpawn` | Where a car starts, resolved from a fare node through `RoadGraph` | ✅ `P2-3` |
| `VehicleController` | Player car. `VehicleBody3D` + arcade overrides — steering rate, top-speed taper, coast drag, drift, collision response, auto-right | ✅ `P0-5`/`P2-3`/`Q50` |
| `InputRouter` | Abstracts touch / gamepad / keyboard into one action set | 🟡 keyboard + gamepad; `P2-4` |
| `DebugHud` | Every dev readout, behind `F3` | ✅ |
| `TrafficSystem` | AI vehicles following road-graph splines; trams as scripted blockers | ⬜ `P3-3` |
| `FareSystem` | Fare state machine: idle → hailed → carrying → delivered/failed | ⬜ `P3-1` |
| `ScoreSystem` | Base fare, time bonus, **style chain** and **fare combo** — two distinct multipliers | ⬜ `P3-2` |
| `HUD` | Meter, timer, arrow, destination callout (bilingual) | ⬜ `P3-5` |
| `AudioDirector` | Engine, radio, callouts, ambience buses | ⬜ Phase 5 |

**Architectural rule:** `scripts/core/` holds pure logic — scoring, fare state, traffic rules — with
no `Node` inheritance and no rendering calls. It should be unit-testable headlessly and portable if
the engine ever changes.

**A vehicle's drive layout is scene data, not code.** `VehicleWheel3D.use_as_traction` is authored
per wheel in each vehicle scene, so RWD and FWD need no code change; each vehicle gets its own
`HandlingProfile`, and `centre_of_mass_offset_y` plus `roll_influence` already cover a tall van's
height. The roster this serves is in `ART_DESIGN.md`.

⚠️ **This is why drift bias is derived from chassis geometry, not from a wheel's role.**
`VehicleController._group_axles` splits the wheels by their position along the chassis. Had it keyed
off `use_as_traction` or `use_as_steering` — which since `Q50` are the roles a `VehicleWheel3D`
carries — the front-wheel-drive Crown would have had its drift bias inverted, silently, and only on
the second vehicle anyone built.

### Script map

| Path | Role |
|---|---|
| `scripts/city/city_manifest.gd` | **`city.json`, typed.** The shipping route into the generated city: the tile list, their AABBs, the per-edge carriageway widths and clearances, the lane-width bar, the resolved document paths |
| `scripts/city/city_streamer.gd` | Loads and frees tiles by distance to their published `aabb`, off the main thread, and owns the LOD tier |
| `scripts/core/tile_streaming.gd` | The streaming **policy**, pure — distance to an `AABB` in, tier out. No `Node`, no `load()`, so the decision table is testable headlessly and a tile cannot be rejected *after* being loaded |
| `scripts/core/plan_lattice.gd` | An even grid of plan positions over a region's bounds. Both region-sweeping verify tools take their sample points from it — counted, not float-accumulated, so the far row and column cannot be dropped |
| `scripts/city/streaming_profile.gd` | Schema for distance bands, hysteresis and per-frame budgets. Numbers live only in `tuning/streaming.tres` |
| `scripts/city/road_graph.gd` | One parse per scene, nearest-edge and lane-centre queries over a plan grid. Refuses off-grade edges (`Q13`), and **expresses** — never enforces — passability on the rest (`Q51`) |
| `scripts/city/road_spawn.gd` | `basis_facing` builds the rotation from a direction, which is what deleted the hand-written transform literal and its transpose trap |
| `scripts/city/generated_document.gd` | Parse and version-check a JSON document the ETL wrote. Shared by the locators and by `CityManifest`, so the stale-copy message exists once |
| `scripts/city/generated_{road_graph,road_surface,fares,landmarks}.gd` | Locators — one definition per document, two readers. `generated_fares.gd` is the one place that knows that document's shape, and `generated_landmarks.gd::placement_of` is the one place the compass bearing becomes a Godot rotation |
| `scripts/city/landmarks.gd` | Places the authored heroes where `landmarks.json` puts them. ~2 models, always resident — no streaming, no LOD |
| `scripts/city/mesh_contract.gd` | The mesh rules every generated asset is held to, plus `triangles` and `bounds`. Read by every verify tool that touches geometry, the previews, and `CityStreamer` |
| `scripts/city/preview_draw.gd` | Flat ribbons and the unshaded vertex-colour material, shared by the dev previews |
| `scripts/city/{tile,road_surface,road,fare}_preview.gd` | Dev previews — instantiate tiles, the road surface, the graph with one-way arrows, and the fare nodes tethered to their edges. **Not performance measurements** |
| `scripts/city/road_graph_overlay.gd` | Dev: the resolved edge, lane centre and legal travel direction under the moving car |
| `scripts/city/drive_harness.gd` | Dev: place the car on the resolved start line, and return it there when it leaves the world. On the scene root so its `_ready` runs after the car's |
| `scripts/camera/free_look_camera.gd` | Dev fly camera. Bypasses `InputRouter` so dev keys stay out of the shipped action map |
| `scripts/ui/debug_hud.gd` | The one owner of dev chrome. Off by default |
| `scripts/ui/fps_counter.gd` | Frame rate and frame time. Gated by `DebugHud`, and it stops counting while hidden |
| `scenes/world/golden_hour.tscn` | The one lighting rig. Instance it rather than authoring a second Environment |
| `tools/verify_tiles.gd` | The mesh contract, per tier of every tile the manifest names |
| `tools/verify_city.gd` | `city.json` — georeferencing, per-tier AABB containment, `bounds_game`, and that the named documents exist |
| `tools/verify_road_surface.gd` | `roads.glb` — one draw call, UVs, trimesh collision |
| `tools/verify_road_graph.gd` | `RoadGraph`'s queries — the off-grade refusal, edge resolution, lane placement against the published carriageway width, per-station width on a genuinely mixed edge, `Q51`'s passability (every edge measured, `is_routable` agreeing with the published blocked set, and `nearest_edge` **still** answering on a blocked edge), and query time against a 1 ms budget over a region-wide lattice |
| `tools/verify_city_streamer.gd` | The streaming policy — band edges, hysteresis both ways, and a region-wide residency sweep against the draw-call budget |
| `tools/verify_spawn.gd` | The start line — orientation against its edge vector, nearside-lane placement, drop height, and the resolved edge against the fare node. **Builds the transposed basis and requires it to fail** |
| `tools/verify_landmarks.gd` | `landmarks.json` — assets load with mesh and `-col` collision, triangle budget, placed AABB near `bounds_game`, and no tier-0 tile triangle inside each excluded footprint's interior core |
| `tools/verify_beam_budget.gd` | `BeamBudget` — the spot-light cap is never exceeded **or under-spent**, the nearest cars win when registered farthest-first, a beamless rig takes no slot, and a despawn hands its slot on. ⚠️ One of the two verify tools that need **no built region**: it builds its own stub rigs, so it runs whatever `VERIFY_GENERATED` says |
| `tools/verify_vehicle.gd` | The taxi's engine-side wiring — the body renders with `vehicle_body.tres` through the import's name channel, the channels `vehicle_lamps.gd` writes are instance uniforms the renderer lists, the imported `UV` payload is integral and inside those channels on lens vertices only, the rig hangs where the script looks, and every beam is authored dark with its cone below horizontal. ⚠️ Needs **no built region** (the taxi is authored and committed), and ⚠️ **sees no frame** — it cannot tell you the shader compiled |
| `tools/generated_scene_import.gd` | Import fixup — see `[importer_defaults]` above |

---

## Input architecture

Desktop/Steam is a target, so input is abstracted from day one via a single action set:

| Action | Touch | Gamepad | Keyboard |
|---|---|---|---|
| `steer` (axis) | Left/right screen zones | Left stick X | A / D, ← / → |
| `accelerate` | Auto-on, or right zone | RT | W, ↑ |
| `brake_reverse` | Left-bottom button | LT | S, ↓ |
| `drift` | Dedicated button | A / Cross | Space |
| `look_back` | Swipe down | B / Circle | C |

**Touch default is auto-accelerate** — the player only steers, brakes and drifts. This is the genre
convention and it keeps mobile input to two thumbs.

`InputRouter` emits the action set; no gameplay script reads raw input events. It samples in
`_physics_process`, not `_process`: Godot runs every physics step before idle processing, so a
vehicle polling from `_physics_process` would otherwise read a sample one render frame stale — a
guaranteed extra ~16.7 ms of latency, doubling whenever the render rate falls below the physics tick.
Autoloads are the first children of `root`, so the router runs before any gameplay node in the same
tick.

---

## Performance budget

⚠️ **One tier ships today, the desktop one.** Nothing in `game/scripts/` reads `OS.has_feature`,
`OS.get_name` or any quality setting — the only platform branching in the project is the `.mobile` /
`.web` suffixes in `project.godot`. The mobile tier is unbuilt and blocked on `P0-3b`, which needs a
signing identity and the two floor handsets.

| Metric | Mobile tier | Desktop tier |
|---|---|---|
| Target | 60 fps @ 1080p | 60 fps @ 1440p |
| Draw calls | < 150 | < 400 |
| Visible triangles | < 300k | < 1M |
| Texture memory | < 128 MB | < 512 MB |
| Bundle size | < 200 MB (iOS cellular threshold) | no hard limit |
| Shadows | Vehicle blob shadow only ⚠️ | Two directional cascades at 400 m |

⚠️ "Vehicle blob shadow only" deserves re-examination before anyone implements it: shots with shadows
*off* looked markedly worse than the line implies — flat and blown out, the canyon losing its depth.
A real mobile tier needs the ambient and tonemap re-tuned around a blob shadow, not the shadow
switched off.

**Device floor:** iOS **A13** (iPhone SE 2nd gen / iPhone 11); Android **Adreno 618** tier, Vulkan
1.1, 4 GB RAM. Two separate decisions — the iOS floor is a support-matrix question, the Android floor
is the one that constrains the budget.

Key techniques, in order of what they buy:

1. **Merge aggressively at build time.** Untextured buildings with vertex colours merge into one mesh
   per tile — no atlas packing, no texture juggling. This is the main reason the untextured dataset
   was chosen.
2. LOD via ETL-generated tiers, not runtime decimation.
3. `MultiMeshInstance3D` for repeated props (lamp posts, railings, signage frames).
4. Occlusion is largely free — dense HK street canyons occlude naturally.

---

## Build pipeline

```
etl/  →  python -m pipeline --city hong_kong --region wan_chai
      →  etl/out/<city>/<region>/{city.json, roadgraph.json, roads.glb, fares.json, tiles/*.glb}
      →  tools/sync_generated.sh → game/assets/generated/
      →  Godot export presets → iOS / Android / desktop / web-demo
```

Six stages in one dependency chain — `fetch`, `buildings`, `roads`, `surface`, `fares`, `export` —
**3.0 s end to end** for Wan Chai against a warm source cache. Each stage also runs on its own
against the same arguments, which is how they are developed:

```sh
python -m pipeline.buildings --city hong_kong --region wan_chai
python -m pipeline --city hong_kong --region wan_chai --from roads   # resume mid-chain
```

`python -m pipeline` invokes each stage through the *same* entry point those commands use, so a full
build and a partial one cannot drift apart. A stage that exits non-zero stops the run rather than
letting the next one read the previous build's output. `fetch` is the only stage that touches the
network.

**`export` also validates.** It re-reads what it just wrote and checks what no single stage checks: a
fare node naming an edge the graph no longer has, a tile whose GLB was never written, a document left
over from another region, geometry outside the declared bounds. Each stage's output is internally
valid in every one of those cases. Everything the manifest asserts is checked against the document it
came from, never against the manifest itself — a stale `city.json` is perfectly self-consistent.
`python -m pipeline.export … --check` runs the checks alone.

The ETL is **not** run by CI. It runs when source data or pipeline logic changes, and its output is a
versioned build artefact.

**Getting a build into the game:** `tools/sync_generated.sh [city] [region]` copies exactly the files
`city.json` names — asked of the ETL (`python -m pipeline.export … --list`), never inferred from a
directory listing. That keeps the stage intermediates out of the bundle, and it removes tiles a
previous build left behind, because nothing else would ever notice them: every check in the project
starts from the manifest, and the manifest has forgotten them.

**Then check it in-engine**, because the ETL cannot assert engine-side facts about its own output.
`--import` first, since a fresh sync writes GLBs with no import sidecars — then `tools/check.sh`.

### Looking at it

| Scene | For |
|---|---|
| `scenes/dev/city_preview.tscn` | Fly around. Instantiates **every** tile at one tier — no streaming, no LOD switching, so it is *not* a performance measurement |
| `scenes/dev/city_drive.tscn` | Drive. Same assets with the taxi on the road surface's collider and the chase camera |

**The spawn is resolved at runtime and is not written down anywhere.** `drive_harness.gd` asks
`RoadSpawn.at_fare_node` for fare node **`f_004`, "Expo Drive eastbound underneath HKCEC Phase II"** —
a real taxi stand in the Transport Department's data, so the car begins where a Hong Kong taxi would
be waiting. Change `spawn_fare_id` on the scene root to start somewhere else.

The heading is **not** supplied to the query. A zero heading makes `nearest_edge` take the edge's own
vertex order, and `P1-3` reversed the polyline of every backward edge precisely so that order *is*
the legal direction. Passing the car's authored rotation in would let the car decide which way a
two-way street runs, which is backwards.

The car sits in the **nearside lane**, 2.56 m left of the centreline on this edge, and never on the
centreline itself — partly because a car should start in a lane, and partly because the centreline is
the worst place on the network to put a wheel: it is where opposed ribbons overlap and where junction
caps double up, so a raycast can find two coplanar collision triangles a few centimetres apart and
the wheel picks between them. **Y is the one number not published**: lane centre plus ray length plus
`DROP_CLEARANCE_M`. The car is dropped, not set down, and settles onto its suspension — and moving
the spawn moves the harness's fall-detection floor with it.

⚠️ **The trap this replaced, kept because the fallback literal in `city_drive.tscn` still has it.**
`Transform3D`'s 12-float constructor fills `Basis` **rows**, while "forward" is `-basis.z` — and in
GDScript `basis.z` *is* the column. Building a literal as columns therefore transposes the basis, and
**a transpose is not a 180° flip**: transposing a yaw-only basis mirrors the heading about world −Z,
which is 172° wrong for this spawn, 180° for a due east-west street, and **0° — a silent no-op — for
a north-south one.** So the error is invisible on exactly the streets where you would trust an
eyeball check. There is also a check needing no tooling at all, and it is the one that caught this:
**the harbour is north**, so from a car facing east, a left turn heads for the water.

**One thing is knowingly missing:** **the flyovers cannot be driven onto** (`Q13`). Off the
carriageway is ground, and solid (`P3-10`), so mounting a kerb puts the car on the pavement rather
than through it. The dev harness that catches a car falling out of the world still runs — the region
has edges, and level −1 runs under the terrain (`Q21`).

---

## Constraints

1. No runtime network calls. The game is fully offline.
2. No engine-specific formats out of the ETL — glTF and JSON only.
3. No hardcoded Hong Kong specifics outside `etl/config/cities/`.
4. Tuning values live in `game/tuning/*.tres`, never as constants in scripts.
