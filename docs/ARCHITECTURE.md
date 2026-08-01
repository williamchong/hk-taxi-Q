# Architecture

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Engine | **Godot 4.7** | MIT, no royalties or seat fees |
| Renderer | **Mobile** (primary), Compatibility for web demo | Forward+ only if desktop tier justifies it later |
| Physics | **Jolt** — Godot's default since 4.4 | Has a wheeled vehicle controller |
| Engine language | **GDScript**, statically typed | See decision below |
| ETL | **Python 3.11+** — numpy, pyproj, pyyaml, pyogrio | Build-time only |
| Targets | iOS, Android, Windows/macOS/Linux (Steam) | Web export reserved for the free demo slice |

### Decision: GDScript, not C#

C# platform support in Godot as of 4.7 (re-verified against the official docs on 2026-07-29):

- Desktop (Windows/macOS/Linux): fully supported
- Android: supported since 4.2 but **experimental** — requires .NET 7.0+, linux-bionic Mono
  runtime, arm64/x64 only
- iOS: **experimental**
- Web: **not supported** — C# projects cannot export to web at all

Mobile is a primary target and the free web demo is the planned marketing funnel. C# compromises
both. GDScript also hot-reloads, which directly speeds up the vehicle-feel tuning loop that
carries most of this project's risk.

**Performance escape hatch:** if a system profiles too slow, use **GDExtension** (C++, or Rust via
godot-rust). It preserves every export target, including web. Do not reach for C#.

> **Note for JS/TS developers:** GDScript is Python-like with optional static typing. Always
> annotate (`var speed: float = 0.0`) — it is both faster and catches errors the untyped form
> won't. Godot's `signal`/`connect` is its event-emitter equivalent. `.tres` resource files are
> the idiomatic place for tuning data, roughly equivalent to a typed JSON config.

### Project settings

`game/project.godot` is **regenerated from scratch** by Godot whenever Project Settings is saved in
the editor, discarding any comments in it. This table is the durable record — check it against the
file after anyone touches the editor's settings dialog.

⚠️ **It also drops hand-written feature overrides** — settings with a `.web` / `.mobile` suffix.
Observed three times in one session: `renderer/rendering_method.web` disappeared on every editor
save, which silently breaks web export because WebGL2 cannot run the mobile renderer. Editing the
file by hand is what makes them fragile; the editor only persists an override it created itself.
**Set them through Project Settings → right-click the property → "Override For…"** and Godot will
keep them. Until that is done for a given key, re-check this table after opening the editor:

```sh
grep -c 'rendering_method.web' game/project.godot   # must be 1
```

| Setting | Value | Why |
|---|---|---|
| `rendering/renderer/rendering_method` | `mobile` | Locked decision. Set as the **base** value, not only the `.mobile` override, so the editor and desktop builds preview the renderer the phone will actually run. |
| `rendering/renderer/rendering_method.web` | `gl_compatibility` | Web export is WebGL2-only. |
| `rendering/textures/vram_compression/import_etc2_astc` | `true` | Godot refuses to export **any** arm64 target without it — iOS, Android, and Apple Silicon macOS alike. |
| `physics/3d/physics_engine` | `Jolt Physics` | Locked decision. It is the default since 4.4, but stated explicitly so the project does not silently follow a changed engine default. |
| `application/run/max_fps.mobile` | `60` | Rendering uncapped on a 90/120 Hz phone panel buys nothing above the 60fps target and throttles the device — the most likely way to lose the frame-rate floor in a sustained session. Desktop stays uncapped. |
| `display/window/stretch/mode` | `canvas_items` | Resolution-independent UI; desktop is a target alongside phones. |
| `[importer_defaults] scene.import_script/path` | `res://tools/generated_scene_import.gd` | Godot 4.7's glTF importer reads `COLOR_0` into the mesh but leaves `vertex_color_use_as_albedo` **off**, so every generated tile imports as a white block — with or without a material in the file. Nothing in the glTF can express it, because there `COLOR_0` always multiplies base colour. Set as an importer *default* rather than per file: generated assets are gitignored, so their `.import` files do not survive a fresh clone. |

**Deliberately not set:** `rendering/lights_and_shadows/directional_shadow/soft_shadow_filter_quality`.
Godot already ships a `.mobile` override of `0` for it, and feature overrides beat an explicitly-set
base value — so setting the base only degrades the desktop tier, which is specified to get one
directional shadow cascade.

**Also deliberately not set:** `rendering/lights_and_shadows/directional_shadow/size`. The engine
default is already 4096 (`.mobile` 2048), and writing a base value equal to the default is noise.
The next step up, 8192², is **~134 MB** of shadow map against a 512 MB desktop texture budget —
`directional_shadow/16_bits` defaults to `true`, so it is `D16_UNORM` at 8192² × 2, not the 268 MB
the 32-bit figure would suggest. Measured rather than quoted: raising the atlas to 8192 moved
texture memory by exactly 134,217,728 B.

**Cascade count costs no VRAM.** Godot allocates one `size × size` depth texture whatever the split
mode and subdivides the rect per cascade, so four 2048² quadrants and one 4096² are the same
allocation — measured identical at 79,592,192 B under both. Cascades buy geometry submission, not
memory, and the shadow-map fill is unchanged either way.

There are no `rendering/lights_and_shadows/*` keys in `project.godot` at all, and the shadow work
added none — cascade count and distance are node properties on the one shared sun, which is where
the editor renders them.

**Autoloads:** `FpsCounter` (debug builds, or `--fps`) and `InputRouter`. Both run every frame for
the life of the process, so treat them as hot-path code.

### GDScript warnings

The `[debug]` block promotes 21 GDScript warnings to errors. This is the engine's own type-aware
checker, and the only one available that resolves types at all: a grammar-level linter sees
`basis.z` as an identifier and a dot, where the engine sees a `Vector3` on a `Basis`.

**Godot never signals any of this through its exit code.** A script that fails to parse, a warning
promoted to an error, a dependency that will not compile — all of them print and exit `0`.
`tools/check.sh` exists to turn that output into an exit code, and is the only thing that does; see
"Checks" below. Running `--import` by hand tells you nothing unless you read the output.

**Level 1 is invisible.** Warnings only reach stdout at level `2`. A warning left at `1` shows up in
the editor's script panel and nowhere else, and the contributor workflow is deliberately headless,
so a `1` here would be decorative. Every warning is therefore at `2` or left at its engine default.
The list below covers the ones that were considered, not all 51 the engine offers.

**Enforced (`=2`):**

| Group | Warnings |
|---|---|
| Typing | `untyped_declaration` — the one hard convention in `CLAUDE.md` that no third-party tool can check |
| Shadowing | `shadowed_variable`, `shadowed_variable_base_class` |
| Confusables | `confusable_identifier`, `confusable_local_declaration` |
| Numerics | `integer_division`, `narrowing_conversion` — the arithmetic that silently truncates under a physics tick |
| Dead code | `unused_variable`, `unused_parameter`, `unused_local_constant`, `unused_private_class_variable`, `unused_signal` |
| No-ops | `standalone_expression`, `standalone_ternary`, `redundant_await` |
| Typing traps | `incompatible_ternary` (result degrades to `Variant`), `int_as_enum_without_cast`, `int_as_enum_without_match` |
| Node wiring | `get_node_default_without_onready`, `onready_with_export` |
| Overrides | `native_method_override` |

**Adopting them was not free**, contrary to the first version of this note. `shadowed_variable_base_class`
caught eight real violations across three files: `root` in `verify_tiles.gd` and
`verify_road_surface.gd` (both `extends SceneTree`, so shadowing `SceneTree.root`), and `basis` ×4
plus `transform` in `greybox_builder.gd` (`extends Node3D`). Renamed to `scene_root`, `frame` and
`placement`. In a file whose own comments warn about `Basis` conventions, a local `basis` shadowing
`self.basis` is exactly the confusion worth forbidding.

**Deliberately not enforced**, with counts measured at the time:

- `inferred_declaration` (~25 hits). It flags `:=`, which *is* static typing — just inferred. The
  `CLAUDE.md` rule asks for static types, not for spelling every one of them out, and rewriting
  `const _ONE_WAY := Color(...)` to name its type buys no safety.
- `unsafe_method_access`, `unsafe_property_access`, `unsafe_cast`, `unsafe_call_argument`
  (~21 hits between them) and `return_value_discarded` (~8). Both trace to a boundary the design
  chose: generated JSON arrives as `Variant`, and `Packed*Array.append()` returns a `bool` nobody
  reads. Enforcing them would mean threading typed locals through every loader for no defect
  caught. Revisit if the data contract ever gains a typed loading layer.
- The remaining ~22 sit at their engine defaults and have not been assessed. `unassigned_variable`,
  `unreachable_code` and `assert_always_false` look worth promoting and were measured as costing
  nothing; they are left for a pass that can give them attention rather than being swept in here.

**This is not a bug-catcher.** None of the four defects recorded under `P0-5b` / `P0-5c` — inverted
steering sign, framerate-dependent drag, an `@export`ed `Node3D` silently null from a hand-authored
`.tscn`, wheel raycasts accepting wall faces — would have been caught by any linter. A review pass
caught them.

### GDScript formatting

`gdformat` (from `gdtoolkit`, in the `dev` extra) is the GDScript counterpart to `ruff format`. Its
default line length is 100, matching `ruff`, so it needs no config file.

**`gdlint` is installed but deliberately not wired into the checks.** Run against the codebase it
reported 17 problems, 16 of them the single cosmetic rule `class-definitions-order` across four
preview scripts; acting on them would mean reordering commented files for no behavioural gain. The
17th was one long line, which `gdformat` then fixed — so it now reports 16. It also cannot check
static typing, which is the convention that actually matters here. `gdparse` is redundant outright:
the checks already parse every script with the engine's own parser.

### Checks

`tools/check.sh` runs the whole Godot-side suite and is the only route that fails on error, because
Godot itself always exits `0`:

| Step | Covers | In CI |
|---|---|---|
| `gdformat --check` | Layout across all of `game/` | yes |
| `--import` | Autoloads and what they reach; also builds `game/.godot/` | yes |
| warnings sweep | `--check-only` per script, grepping for `treated as error`. This is what makes the 21 warnings bind on every file — `--import` alone reaches only autoload-connected scripts, measured by planting an untyped variable in `greybox_builder.gd` and seeing it go unreported | yes |
| `verify_city`, `verify_tiles`, `verify_road_surface` | The generated-asset contracts | **no** |

The sweep must run with `game/` as the project directory. Run from elsewhere, `res://` does not
resolve, every script silently analyses clean, and the check passes having checked nothing — the
`dea1f36` failure mode, one directory over.

### CI

`.github/workflows/ci.yml` runs on every push to `main` and every pull request, in two jobs:
`ruff check` / `ruff format --check` / `pytest` on Python 3.11 and 3.13, and `tools/check.sh`
against the Godot version pinned in the workflow — `game/project.godot` records only the minor, and
the editor rewrites that file, so the workflow is where the patch version lives. It runs the script
rather than repeating its steps in YAML,
for the reason the script exists: reimplemented in YAML, the Godot steps would pass on failure.

**CI cannot check the generated-asset contracts.** `game/assets/generated/` is gitignored build
output, so a fresh checkout has no city and every verify tool that reads it exits `1` on the missing
manifest. The workflow sets `VERIFY_GENERATED=0`, which skips them and *prints that it skipped
them* — an unannounced skip would be the same silence the script was written to break. Those
stay a local check, run after a pipeline build.

Giving CI a city means running the ETL there, whose first act is downloading ~320 MB from a
government server. That is a deliberate non-goal on every push; if the contracts ever need
CI coverage, the shape is a scheduled job with the source cache restored, not a per-push one.

---

## Repo layout

```
hk-taxi-Q/
├── CLAUDE.md                    # agent instructions — read first
├── docs/
├── etl/                         # Python: geodata → game assets (build time)
│   ├── config/
│   │   └── cities/
│   │       └── hong_kong.yaml   # CRS, bounds, source URLs, tiling — ALL city specifics
│   ├── pipeline/
│   │   ├── config.py            # loads cities/*.yaml — the only route city facts take in
│   │   ├── crs.py               # ONLY module that knows about EPSG:2326
│   │   ├── fetch.py             # download from CSDI / data.gov.hk, cache to sources/
│   │   ├── documents.py         # read/write a stage's JSON + its schema check; no policy
│   │   ├── gltf.py              # glTF read + GLB write; no dependency, see its docstring
│   │   ├── gdb.py               # geodatabase layers + WKB → numpy; format only, no policy
│   │   ├── mesh.py              # merge, partition, LOD collapse — geometry, no policy
│   │   ├── terrain.py           # terrain mesh → sampleable height field (Q11)
│   │   ├── buildings.py         # sheets → vertex-coloured tiles + LOD tiers
│   │   ├── roads.py             # Road Network geodatabase → roadgraph.json
│   │   ├── surface.py           # roadgraph.json → roads.glb; ribbon, kerbs, junctions
│   │   ├── fares.py             # taxi stands + PUDO + POIs → fare nodes
│   │   ├── export.py            # → city.json, assembles the tile/road/fare outputs
│   │   └── __main__.py          # `python -m pipeline` — every stage, in order
│   ├── sources/<city>/<source>/ # raw downloads — GITIGNORED
│   ├── out/<city>/<region>/     # pipeline output — GITIGNORED
│   └── tests/
├── game/                        # Godot project
│   ├── project.godot
│   ├── export_presets.cfg       # COMMITTED — never put signing credentials here
│   ├── scenes/
│   │   ├── dev/                 # grey-box circuit, city preview — see the ⚠️ below
│   │   └── world/               # shared rigs: lighting, sky
│   ├── scripts/
│   │   ├── core/                # pure logic, minimal engine coupling
│   │   ├── city/                # tile streaming, road graph runtime
│   │   ├── vehicle/
│   │   ├── traffic/
│   │   ├── fares/
│   │   ├── input/               # touch / gamepad / keyboard abstraction
│   │   └── ui/
│   ├── assets/
│   │   ├── generated/           # ETL output — GITIGNORED, build artefact
│   │   ├── authored/            # hero buildings, vehicles, UI — COMMITTED
│   │   └── shaders/
│   ├── tuning/                  # .tres resources: handling, fares, scoring
│   └── tools/                   # editor/headless scripts — import fixups, asset checks
└── tools/                       # dev scripts: ETL→game sync, export automation
```

⚠️ **`scenes/dev/` is not shipped — except that `main.tscn` currently boots one.** Since the web
demo, `run/main_scene` reaches `scenes/dev/city_drive.tscn`, so every export starts in a dev scene.

~~That is a knowing Phase-1 placeholder with two consequences worth stating: `city_drive.tscn` puts
`tile_preview.gd` — which its own docstring calls "a dev tool, not the streamer… **not** a
performance measurement" — on the boot path at **1.16 M primitives against a 300k mobile budget**.~~
**Closed 2026-08-01 by `P2-1`.** `CityStreamer` is on the boot path in its place, and the same
measurement now reads **268,709 primitives at the spawn and a worst measured 240,598 visible
triangles** across the region — inside the budget rather than four times over it. The 1.16 M figure
was reproduced first and then replaced; see PROGRESS.md for the five-point before/after.

The other consequence stands: the scene needs the gitignored `assets/generated/`, so a fresh clone
boots to an empty world with only a `push_warning`. An export is still a demo rather than a build
until there is a real main scene, but it is no longer a demo that blows the frame budget.

**Why the ETL is a separate Python project:** it runs rarely, at build time, and needs GDAL —
which has no good Godot equivalent. Keeping it out of the engine also keeps it reusable for the
second city.

---

## Data contract

The interface between ETL and game. **Versioned — change both sides together and bump
`schema_version`.** All positions are game-space metres (see Coordinates below).

### `city.json` — manifest

```json
{
  "schema_version": 3,
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
      "lods": ["tiles/t_00_00_lod0.glb", "tiles/t_00_00_lod1.glb", "tiles/t_00_00_lod2.glb"],
      "aabb": [[8.37,4.935,-16.588],[167.562,70.801,165.268]]
    }
  ],
  "road_graph": "roadgraph.json",
  "road_surface": "roads.glb",
  "carriageway": [{ "edge": 651, "half_width_m": 5.12 }],
  "fares": "fares.json",
  "etl_version": "0.1.0",
  "generated_utc": "2026-07-30T20:04:03Z"
}
```

Every value above is a real one from the Wan Chai build, not an illustration.

`origin` is computed by the ETL from the region bounds, never authored — `floor(min_easting)` and
`ceil(max_northing)`, i.e. the region's **north-west** corner. Anything reading `city.json` should
treat them as data, not as constants. The game itself never needs them; they are what puts a
game-space position back on the source map.

**`city.json` names the other documents, it does not contain them.** The road graph is 0.65 MB on
disk and ~6 MB parsed, and `RoadGraph` wants it at a different moment from when `CityStreamer`
wants the tile list.
Each of the three is separately versioned below, and `export.py` writes the manifest that points
at them. A build ships exactly what the manifest names: the three documents and every path in
`tiles[].lods` — **134 files and 30.8 MB** for Wan Chai, exporting to a **21.1 MB** PCK. It was
199 files and 105.5 MB for a 51.6 MB PCK until `P2-1`'s review dropped the exact-weld tier; see
`Q16` in `docs/PROGRESS.md`.

⚠️ **`carriageway` is the drawn half-width per edge, and the game cannot derive it** (schema 2,
`P2-2`). `roadgraph.json` publishes the **authored** street — `lanes × lane_width_m` — while `P1-4`
draws the ribbon at `width_m × widen_for(speed_limit_kph)`, 1.6× by default. The widening lives on
the ETL's surface style, and `etl/pipeline/config.py` keeps it there deliberately: *"the graph is a
description of the city, this is how wide and how kerbed to draw it. A change here never changes
`roadgraph.json`."* So the drawn width reaches the runtime through the manifest or not at all.

`surface.py` records it — the one place the widening is applied — and `export.py` carries it here
without recomputing, because a second evaluation of `widen_for` is a second thing to keep in step
with the config. It is the same category as `tiles[].aabb`: geometry the runtime cannot work out
for itself, measured once by the stage that drew it.

Without it a lane centre falls short by a quarter of the widening — **0.96 m on a two-lane street**,
putting a car that much nearer the seam where opposed ribbons overlap and a suspension ray hunts
between two coplanar triangles. `RoadGraph` warns and falls back to the authored width rather than
failing, and `verify_road_graph.gd` treats the table's absence as an error.

**The game must read the manifest to find its tiles — there is no fallback.** In the editor
`res://` is a real directory and `DirAccess.get_files_at` lists it; in an exported build it is a
PCK archive that Godot's virtual filesystem will not enumerate, so the same call returns nothing
and the city renders empty. `scripts/city/city_manifest.gd` is the only supported route, and
`tiles[].aabb` is what lets `CityStreamer` (`P2-1`) reject a tile without loading its ~400 KB of
geometry first.

⚠️ **`bounds_game` is the union of the content, not the region rectangle.** Wan Chai's declared
region is 1650 × 887 m; its geometry spans 1668 × 942 m, because a building is assigned to a tile
whole and may overhang the region's edge — and because the road ribbon is drawn outward from
centrelines that run right up to it. A consumer sizing a spatial partition, framing a camera, or
placing diegetic map edges off the rectangle will clip real geometry. The rectangle itself is not
in the manifest; it is a build-time concept, and after clipping the content is what exists.

`generated_utc` is a build stamp and the **only** field that changes between two builds of
identical inputs — verified by rebuilding the region from a clean `out/` and diffing: every GLB and
every JSON byte-identical, this line the sole difference. Strip it before diffing two builds.

`lods` is ordered nearest-first, one file per tier, matching `lod_cell_sizes_m` in city config —
except where `class_lod_cell_sizes_m` holds a mesh class back from it. A tier is **not** a single
cell size: a building decimates at 1.5 m and an elevated road deck at 0.5 m, because a deck thinner
than the cell flattens into it. The tile is still one mesh and one draw call, because each class is
collapsed separately and merged afterwards. See `ART_DESIGN.md` "LOD policy".

⚠️ **`tiles[].aabb` is the union of the tiers a build actually ships, not of the source geometry.**
It was the source's until `P2-1`'s review dropped the exact-weld tier — correct only while the
finest tier lost nothing. Decimation moves corners and drops anything thinner than a cell, so a
source box can describe geometry no shipped mesh contains: one Wan Chai tile declared a height 19 m
past its own LOD0. Nor is tier 0's box enough on its own — `collapse` buckets on
`floor(position / cell_m)` and averages, so a coarser grid can leave an extreme vertex alone in its
cell and preserve it where a finer grid averaged it inward, measured at 12.03 m on `t_01_02`.
`game/tools/verify_city.gd` asserts every tier is contained and the union is tight to 1 cm.
Separate files rather than one GLB holding every tier, because the streamer loads one at a time.

**A tile's `aabb` can be larger than the tile.** Buildings are assigned to a tile whole, by their
centre, so one may overhang its neighbour by half a footprint — measured at up to 222 m across a
150 m tile in Wan Chai. Use the `aabb` for culling and streaming distance, never the tile's grid
position.

**Tile output carries no textures.** One material, one primitive, colour in `COLOR_0` — that is
what makes a tile one draw call, and it is checked in-engine by
`game/tools/verify_tiles.gd`.

**The finest tier ships collision; no other tier does.** The tier-0 mesh is named
`<tile_id>-col`, and Godot's glTF importer reads that suffix into a `StaticBody3D` carrying a
`ConcavePolygonShape3D` — the same mechanism `roads.glb` uses for the carriageway, and chosen for
the same reason: the collider is part of the asset, so `CityStreamer` builds no shape at load and
the collider cannot drift from the geometry it is drawn from.

Only the finest tier, because a tier is selected by distance and the coarse one is resident only
*beyond* the 250 m near band, where nothing can touch a building. Suffixing both would pay for a
shape in the bundle for geometry that exists to be looked at from 300 m away.
`verify_tiles.gd` asserts it in both directions — present on tier 0, absent on every other — because
a suffix that spread would be invisible in every screenshot and would show up only as bundle bytes.

⚠️ **The collider costs 5.17 MB of PCK, measured**: 21.10 → 26.27 MB on a `Web Demo` export, one
variable changed. Not 14.91 MB, which is what tier 0's 434,149 triangles come to as raw
un-indexed faces — the pack compresses them. Both figures are here because the gap is the point:
`Q16`'s rule is that bundle size is measured from a PCK and never summed from geometry.

**Two additions to the vertex stream are planned, and both bump `schema_version`.** Neither adds a
texture or a second primitive, which is the point:

| Addition | Task | Cost |
|---|---|---|
| `TEXCOORD_0.xy` = height above the building's own base, per-building seed | `P3-7` | ~2 bytes/vertex quantised. The window-band shader cannot derive either from a vertex, so the ETL must ship them — one commit across both sides, per hard rule 5 |
| Terrain merged into the tile primitive, vertex-coloured | `P3-10` | ~1,355 triangles per tile. No texture, and **no extra draw call**, because it merges rather than becoming a second surface |

⚠️ `COLOR_0.a` is a constant `255` today and looks like the cheaper place for a shader mask. It is
not. `game/tools/generated_scene_import.gd` sets `vertex_color_use_as_albedo` project-wide, and an
opaque `BaseMaterial3D` ignores albedo alpha only until somebody enables transparency on a tile —
after which the city renders see-through with no error. `TEXCOORD_0` has no such failure mode.

### `buildings.json` — an ETL intermediate, *not* part of this contract

`buildings.py` writes one of these next to its tiles, recording the grid, the LOD cell sizes, and
each tile's paths, AABB and triangle counts. It exists so the building stage and `export.py` stay
independently runnable; `city.json` is the versioned interface and `export.py` is what writes it.
Nothing in the game should read `buildings.json`.

### `roadgraph.json` — drivable network

```json
{
  "schema_version": 1,
  "nodes": [
    { "id": 1, "pos": [120.5, 4.0, 300.2], "kind": "junction" }
  ],
  "edges": [
    {
      "id": 1, "from": 1, "to": 2,
      "polyline": [[120.5, 4.0, 300.2], [180.0, 4.1, 305.0]],
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
  "turn_restrictions": [
    { "from_edge": 1, "via_node": 2, "to_edge": 5 }
  ]
}
```

Field provenance:

| Field | Source |
|---|---|
| `direction` | `TRAVEL_DIRECTION` (1 = bidirectional → `both`, 3 = one-way → `forward`). Closed vocabulary: **only `both` and `forward` are ever written.** A city whose source codes direction against its own digitisation declares `backward` in config, and the ETL normalises it away by reversing the polyline. |
| `turn_restrictions` | `TURN_ID` + `EDGE(1-8)FID`. Edge references are **indices into `edges`**, not source ids. |
| `speed_limit_kph` | `SPEED_LIMIT` layer where present, joined on `ROUTE_ID`; otherwise the city's default. Hong Kong signs only exceptions, so **the default covers ~90% of edges.** |
| `bus_lane` | `BUS_ONLY_LANE` layer, joined on `ROUTE_ID` |
| `tram_tracks` | ⚠️ **Hand-authored.** Not present in the source dataset. A list of street names in city config. |
| `lanes` | ⚠️ **Not published.** Road Network v2 carries no lane attribute in any layer. Authored per road class in city config, keyed on speed limit. |
| `width_m` | Derived from `lanes`, then **hand-tuned upward** for playability (see Game Design) |
| `elevation_level` | `ELEVATION` integer attribute (verified: −1/0/1 in the region). Ordinal level, **not** a height — map to deck heights via city config. Those heights are offsets **from ground level, not from the vertical datum**; see `Q11`. ⚠️ The mapping is a **constant per level**, so no edge ever ramps. The map sheets' `INFRASTRUCTURE` class carries the real deck profile and samples at a 3.01% median grade, but it cannot repair the junctions — see `Q13`. |
| `road_name` | `STREET_ENAME` / `STREET_CNAME` — **bilingual names ship in the source.** The null sentinel has four spellings; normalise NFKC and fold dashes before comparing. |

**Nodes are formed where centrelines share an endpoint, and nothing else.** Not where they cross:
two roads crossing in plan at different `ELEVATION` share no endpoint, so no junction is invented.
Conversely `ELEVATION` is deliberately **not** part of a node's identity — every place two levels
meet at a shared endpoint is a ramp touching down, and splitting there severs the elevated network
from the ground one. See `docs/DATA_SOURCES.md`.

**Geometry is clipped to the region, not kept whole.** Unlike a building — which is assigned to a
tile whole and allowed to overhang — a road feature is cut at the region boundary, because a
polyline cut in two is two polylines with nothing to seam. Without it, 14% of the region's road
length is geometry the player cannot reach, including a tunnel running 570 m out into the harbour.

`node.kind` is `junction` where three or more edge ends meet and `endpoint` otherwise. Degree, not
the source's intersection layer: two centrelines meeting end to end is one road continuing through
a geometry break, and the source records those as intersections too.

### `roads.glb` — the drivable surface

One vertex-coloured mesh for the whole region, generated from `roadgraph.json` by `surface.py`.
Not tiled: at 28,423 triangles it is a fortieth of the massing, it is on screen whenever the player
is, and splitting it would buy nothing but seams and draw calls.

| Property | Value |
|---|---|
| Mesh name | `road_surface-col` |
| Primitives | 1 — one draw call, like a tile |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`, `TEXCOORD_0`; no texture |
| `TEXCOORD_0` | **U is a lane coordinate**, 0 at the **nearside** kerb line and `lanes` at the offside, so an integer U is a lane boundary whatever the widening did to the metres. V is metres along the carriageway. `docs/ART_DESIGN.md` drives lane markings from these rather than from a texture atlas. Junction caps carry `(0, 0)` — a junction is not a length of lane. |

Nearside means left of travel, because Hong Kong drives on the left. The sign is not a free
convention: flip it and every asymmetric marking — a kerbside bus lane, a nearside double yellow —
lands on the wrong side of the road, while the geometry still renders perfectly.

**The `-col` suffix is load-bearing.** Godot's glTF importer reads it and builds a static
`ConcavePolygonShape3D` beside the visible mesh, which is how `P1-4` delivers collision without
the game building a shape at load. `game/tools/verify_road_surface.gd` checks that it survived,
because nothing on the Python side can see it.

**Ribbon widths are the graph's `width_m` times a playability factor** from `roads.surface:` in
city config, never the graph's width raw. Opposed carriageway pairs are drawn as two overlapping
ribbons and deliberately not merged: measured across the region's six pairs, the widening already
closes every gap between them.

**Junctions are capped per elevation level.** The cap is the convex hull of the carriageway corners
each arm presents to the node, which is what makes it meet every arm across its full width. Arms at
different levels are never joined — see `Q13`.

⚠️ **A cap overlaps its arms rather than abutting them** where they stop at different distances from
the node, which happens whenever a short edge is held back by `junction_trim_max_fraction` — 210 of
the region's 1,398 trimmed ends. Measured at 6,051 m² of 52,985 m² of cap area. Invisible today,
since cap and carriageway are the same colour at the same height in one material; it becomes
visible when the markings shader lands, because the cap carries no lane coordinate and the ribbon
beneath it does. The fix is a non-convex cap — the union boundary rather than the hull — which is
polygon clipping and is deliberately not built yet.

### `roadsurface.json` — an ETL intermediate, *not* part of this contract

The counterpart of `buildings.json`, and there for the same reason: it records what the surface
stage knows — the mesh path, its triangle and vertex counts, its AABB — so the stage stays
independently runnable, while `city.json` remains `export.py`'s to write.

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

**`pos` is the source position — the kerbside, not the carriageway.** That distinction is not
cosmetic: 11 of Wan Chai's 29 fare nodes lie outside even the widened road surface, because the
published points sit on the pavement and `P1-4` draws from centrelines. This is where the
passenger stands. Where the *taxi* stops is `nearest_edge` at `edge_t`, and that is derivable
while the kerbside position would not be if it were overwritten. `pos.y` comes off the snapped
edge rather than the terrain, so a node always sits at the height of the road it belongs to.

**`edge_t`** is the fraction along that edge's plan length, 0 at its `from` node and 1 at its
`to`. Without it `nearest_edge` names a road that can be 200 m long, and the game would have to
redo the projection the ETL already did.

**`pickup` and `dropoff`** say what may happen at the node. Both are true at a taxi stand; a
quarter of Hong Kong's published pick-up/drop-off points are **drop-off only** (66 of 275
territory-wide, 4 of the region's 15), and letting a player hail a fare at one would be wrong in
a way a local would notice. `P3-1` should hail only where `pickup`, and deliver only where
`dropoff`.

Positions are millimetre-rounded like `roadgraph.json`'s, through the same `round_position`.

### `landmarks.json` — hero building placement

```json
{
  "schema_version": 1,
  "landmarks": [
    {
      "id": "hkcec",
      "asset": "res://assets/authored/landmarks/hkcec.glb",
      "transform": { "pos": [800, 0, 120], "rot_y_deg": 12.5 },
      "name": { "en": "Convention Centre", "zh": "會展" },
      "replaces_source_ids": ["bldg_88213"]
    }
  ]
}
```

`replaces_source_ids` tells the ETL to **exclude** those buildings from the generated tile mesh so
the hand-made model doesn't z-fight with the extruded one.

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

**`etl/pipeline/crs.py` is the only module permitted to reference EPSG:2326.** Everything else
reads the CRS from city config. This is what makes the second city cheap.

Godot uses a right-handed, Y-up coordinate system with **−Z as forward**. The negation on `z`
above is **forced, not chosen**: rotating `+X` by 90° counter-clockwise about `+Y` lands on `−Z`,
so if east is `+X` then north must be `−Z`. Flip it and the city is mirrored — a plausible-looking
map no local recognises.

**The origin sits at the north-west corner** (`Q7`, resolved 2026-07-30). Because the Z sign is
forced, anchoring at the *northern* edge is the only way to keep the region in the positive
quadrant: X runs east from 0 and Z runs south from 0, so tile indices are natural numbers with
row 0 at the north, as in a raster or a map sheet. A south-west origin — the GIS bbox convention —
would have put every Z at or below zero and every tile index at `0, -1, -2 …`.

Origin easting is floored and origin northing is **ceiled**: rounding outward keeps every offset
inside the region non-negative, and rounding at all stops a sixth-decimal difference between PROJ
releases renumbering every tile.

⚠️ **Non-negativity is a property of the region, not of the source data — so clipping to the region
bbox is a requirement of this contract, not an optimisation.** `fetch.py` deliberately downloads
every map sheet that *intersects* the region, so the building data on disk extends past all four
edges. Any vertex north or west of the region still yields a negative coordinate and a negative
tile index, and the outward rounding buys less than a metre of slack. Whatever consumes the sheets
must clip before indexing.

### Two frames, and why (`Q10`, resolved 2026-07-30)

Each region's geometry is authored in its **own** local frame, origin at its own NW corner. That is
what keeps the numbers the player interacts with small: Wan Chai spans 0–1650 m, where float32
resolves to well under a millimetre.

`city_offset` is the translation from a region's local frame into a **city-wide** frame shared by
every region — anchored on the city's declared `bounds`, not on any region. Add it to a
region-local position to get a city-space one:

```
city_space = region_local + city_offset
```

**A region loaded on its own can ignore `city_offset` entirely.** It exists so two regions can be
placed correctly relative to each other without either giving up its local precision — the
floating-origin approach. Anchoring everything in city space instead would put Wan Chai ~38 km from
the origin, where float32 spacing is ~3.9 mm; that is invisible on a building and awkward on a
vehicle whose suspension sag is 50 mm.

⚠️ **A city's `bounds` must not change once a `city.json` has shipped.** Every region's
`city_offset` is measured from them, so moving them silently relocates every region already
published. They are declared rather than derived from the regions that exist, for the same reason:
a frame computed from "the regions so far" would move each time one was added. `config.py` checks
every region lies inside them.

---

## Runtime systems

| System | Responsibility |
|---|---|
| `CityStreamer` | Load/unload tile meshes by camera distance; owns the LOD tier |
| `RoadGraph` | Runtime queries over `roadgraph.json` — nearest edge, routing, lane centre |
| `VehicleController` | Player car. Custom raycast vehicle on `RigidBody3D` + arcade overrides |
| `TrafficSystem` | AI vehicles following road-graph splines; trams as scripted blockers |
| `FareSystem` | Fare state machine: idle → hailed → carrying → delivered/failed |
| `ScoreSystem` | Base fare, time bonus, style points, combo chain |
| `InputRouter` | Abstracts touch / gamepad / keyboard into one action set |
| `HUD` | Meter, timer, arrow, destination callout (bilingual) |
| `AudioDirector` | Engine, radio, callouts, ambience buses |

**Architectural rule:** `scripts/core/` holds pure logic — scoring, fare state, traffic rules —
with no `Node` inheritance and no rendering calls. It should be unit-testable via GUT and
portable if the engine ever changes.

---

## Input architecture

Desktop/Steam is a target, so input is abstracted from day one via a single action set:

| Action | Touch | Gamepad | Keyboard |
|---|---|---|---|
| `steer` (axis) | Left/right screen zones | Left stick X | A / D |
| `accelerate` | Auto-on, or right zone | RT | W |
| `brake_reverse` | Left-bottom button | LT | S |
| `drift` | Dedicated button | A / Cross | Space |
| `look_back` | Swipe down | B / Circle | C |

**Touch default is auto-accelerate** — the player only steers, brakes, and drifts. This is the
genre convention and it keeps mobile input to two thumbs.

`InputRouter` emits the action set; no gameplay script reads raw input events.

It samples in `_physics_process`, not `_process`. Godot runs every physics step before idle
processing, so a vehicle polling from `_physics_process` would otherwise read a sample one render
frame stale — a guaranteed extra ~16.7 ms of latency, doubling whenever the render rate falls below
the physics tick. Autoloads are the first children of `root`, so the router runs before any gameplay
node in the same tick.

---

## Performance budget

Two tiers.

⚠️ **"Selected at runtime by platform" is what this said, and it is not true.** Nothing in
`game/scripts/` reads `OS.has_feature`, `OS.get_name` or any quality setting — the only platform
branching in the project is the `.mobile` / `.web` suffixes in `project.godot`. **One tier ships
today**, the desktop one. The mobile tier is unbuilt and blocked on `P0-3b`, which needs a signing
identity and the two floor handsets. Corrected here rather than left as an aspiration written in the
present tense.

| Metric | Mobile tier | Desktop tier |
|---|---|---|
| Target | 60 fps @ 1080p | 60 fps @ 1440p |
| Draw calls | < 150 | < 400 |
| Visible triangles | < 300k | < 1M |
| Texture memory | < 128 MB | < 512 MB |
| Bundle size | < 200 MB (iOS cellular threshold) | no hard limit |
| Shadows | Vehicle blob shadow only | One cascade directional |

**Device floor (assumption — confirm in `PROGRESS.md`):** iPhone XR (A12) / Snapdragon 730-class
Android, roughly 2019–2020 hardware.

Key techniques:

1. **Merge aggressively at build time.** Untextured buildings with vertex colours merge into one
   mesh per tile — no atlas packing, no texture juggling. This is the main reason the untextured
   dataset was chosen.
2. `MultiMeshInstance3D` for repeated props (lamp posts, railings, signage frames).
3. LOD via ETL-generated tiers, not runtime decimation.
4. Occlusion is largely free — dense HK street canyons occlude naturally.

---

## Build pipeline

```
etl/  →  python -m pipeline --city hong_kong --region wan_chai
      →  etl/out/<city>/<region>/{city.json, roadgraph.json, roads.glb, fares.json, tiles/*.glb}
      →  tools/sync_generated.sh → game/assets/generated/
      →  Godot export presets → iOS / Android / desktop / web-demo
```

Six stages in one dependency chain — `fetch`, `buildings`, `roads`, `surface`, `fares`, `export`.
**4.4 s end to end** for Wan Chai against a warm source cache, of which the buildings stage is 3.2 s.

Each stage also runs on its own against the same arguments, which is how they are developed and
how a partial rebuild is done:

```
python -m pipeline.fetch     --city hong_kong --region wan_chai
python -m pipeline.buildings --city hong_kong --region wan_chai
python -m pipeline --city hong_kong --region wan_chai --from roads   # resume mid-chain
```

`python -m pipeline` invokes each stage through the *same* entry point those commands use, so a
full build and a partial one cannot drift apart. A stage that exits non-zero stops the run rather
than letting the next one read the previous build's output.

`fetch` is the only stage that touches the network; everything after it reads `etl/sources/`.

**`export` also validates.** It re-reads what it just wrote and checks what no single stage
checks: a fare node naming an edge the graph no longer has, a tile whose GLB was never written, a
document left over from another region, a manifest listing tiles the building stage did not build,
geometry outside the declared bounds. Each stage's output is internally valid in every one of
those cases. Everything the manifest asserts is checked against the document it came from, never
against the manifest itself — a stale `city.json` is perfectly self-consistent, so checking it
against itself confirms nothing. `python -m pipeline.export --city … --region … --check` runs the
checks alone and exits non-zero on any finding.

The ETL is **not** run by CI on every commit — it is run when source data or pipeline logic
changes, and its output is treated as a versioned build artefact.

**Getting a build into the game:** `tools/sync_generated.sh [city] [region]`. It copies exactly
the files `city.json` names — asked of the ETL (`python -m pipeline.export … --list`), never
inferred from a directory listing. That is what keeps `buildings.json` and `roadsurface.json`, which
sit in the same output directory and are not part of the contract, out of the bundle. It also
removes tiles a previous build left behind, because nothing else would ever notice them: every
check in the project starts from the manifest, and the manifest has forgotten them.

**Generated assets are checked in-engine, not by eye.** Three headless tools, run after a rebuild,
because the ETL cannot assert engine-side facts about its own output. `--import` first, because a
fresh sync writes GLBs with no import sidecars:

```
godot --headless --path game --import                                    # ~8 s cold
godot --headless --path game --script res://tools/verify_tiles.gd        # the mesh contract
godot --headless --path game --script res://tools/verify_city.gd         # the manifest vs the geometry
godot --headless --path game --script res://tools/verify_road_surface.gd # collision and UVs
```

⚠️ These tools **`preload` every dependency rather than naming a `class_name` global**, and that is
load-bearing. Global classes resolve through `game/.godot/global_script_class_cache.cfg`, which is
gitignored — so on a fresh clone a tool referencing one fails to *parse*, `_init` never runs, and
`quit(1)` is never reached. The SceneTree then exits **0**: the check reports success having
checked nothing. Reproduced on `verify_city.gd` and `verify_tiles.gd` at `P1-7` and fixed by
preloading. Never reference a `class_name` global from a `--script` tool.

`verify_tiles.gd` asserts the draw-call, vertex-colour and no-texture properties this contract
states, for every tier of every tile the manifest names. `verify_city.gd` closes the other half of
the round trip: it measures **every** imported tier and compares their union to the `aabb`
`export.py` recorded, to 1 cm — an axis flip, a unit scale or a dropped offset moves a corner by
metres, and nothing else in the project would see it. It also checks that each tier individually
sits inside the box the streamer culls against, that the tiers together sit inside `bounds_game`,
and that the three documents the manifest names exist.

It compared tier 0 alone until `P2-1` dropped the exact-weld tier, on the assumption that the finest
tier contained the rest. It does not: a coarser grid can preserve an extreme vertex a finer one
averaged inward, measured at 12.03 m. The residual gap is named in the tool — the union being tight
does not pin any *individual* tier, so a defect confined to one that stays inside the declared box
now passes, and closing that needs a per-tier `aabb` in the contract. **Z-fighting it cannot check** — `--headless` loads the dummy
rasteriser, so there is no frame to inspect. A windowed run can: render, nudge the camera ~2 cm,
diff. A fighting surface flips wholesale under a sub-pixel move where anti-aliased edges only
shift. Measured 0.071% on Hennessy Road at `P1-7`; one camera at one place, so flying around is
still the acceptance.

⚠️ Both tools need Godot's global class cache, which lives in the gitignored `game/.godot/`. Open
the project in the editor once (or `godot --headless --path game --editor --quit`) after a fresh
clone, or `CityManifest` will not resolve.

⚠️ **Running Godot rewrites two committed config files**, stripping every comment in them and, in
`project.godot`, the `renderer/rendering_method.web="gl_compatibility"` line the web export needs.
Restore both afterwards and *verify*, because the restore command reports nothing useful:

```
git checkout game/project.godot game/export_presets.cfg
git diff --exit-code game/project.godot game/export_presets.cfg   # this is the check
```

`git checkout` prints `Updated 0 paths from the index` whether or not it restored anything, so its
output is not confirmation. `export_presets.cfg` loses the "never put signing credentials here"
warning and the `TODO(P0-3b)` placeholder-identifier note; `project.godot` loses the settings
rationale. Both were caught this way during `P1-7`, one of them twice.

**To look at the result:** open `scenes/dev/city_preview.tscn` and run it (F6).
It instantiates every tile — no streaming, no LOD switching, so it is *not* a performance
measurement — and frames whatever is on disk. Set the `Tiles` node's `lod` to see a coarser tier.
Tile vertices are in region game space, so tiles need no transform; dropping one at the origin
puts it where it belongs. That is why `city.json` gives tiles an `aabb` but no position.

**To drive it:** open `scenes/dev/city_drive.tscn` and run it (F6). Same assets, but with the
`P0-5` taxi on the road surface's collider and the chase camera instead of the fly camera.
Separate from `city_preview.tscn` because the two answer different questions and want different
cameras.

**The spawn is resolved at runtime, and since `P2-3` it is not written down anywhere.**
`drive_harness.gd` asks `RoadSpawn.at_fare_node` for **fare node `f_004`, "Expo Drive eastbound
underneath HKCEC Phase II"** — a real taxi stand in the Transport Department's data, so the car
begins where a Hong Kong taxi would actually be waiting — and `RoadGraph.nearest_edge` returns the
edge, the lane centre and the legal travel direction in one query. Change `spawn_fare_id` on the
scene root to start somewhere else; there is nothing else to edit.

The heading is **not** supplied to the query. A zero heading makes `nearest_edge` take the edge's
own vertex order, and `P1-3` reversed the polyline of every backward edge precisely so that order
*is* the legal direction — the directions `Q12` confirmed against the real street. Passing the
car's authored rotation in would let the car decide which way a two-way street runs, which is
backwards.

The car sits in the **nearside lane, 2.56 m left of the centreline** on this edge —
`width_m × widen_for(speed_limit_kph) / 4`, which is 1.6 below 70 kph and 1.3 at or above it, so
the figure is not a constant — and never on the centreline. Partly because a car should start in a
lane, and partly because the centreline is the worst place on the network to put a wheel: it is
where opposed carriageway ribbons overlap and where junction caps double up, so a raycast can find
two coplanar collision triangles a few centimetres apart and the wheel picks between them.

**Y is the one number not published**: lane centre + `HandlingProfile.ray_length_m()` +
`RoadSpawn.DROP_CLEARANCE_M`, which is 0.70 + 0.30 today. The car is dropped, not set down, and
settles onto its suspension. It is load-bearing beyond the spawn — `drive_harness.gd` sets
`_floor_m` from `spawn.origin.y - fall_margin_m`, so moving the spawn moves the fall-detection
floor with it.

⚠️ **The trap this replaced, kept because the fallback literal in `city_drive.tscn` still has it.**
`Transform3D`'s 12-float constructor fills `Basis` rows, while "forward" is `-basis.z` — and in
GDScript `basis.z` *is* the column (`get_column` is C++-only). Building a literal as columns
therefore transposes the basis. **A transpose is not a 180° flip.** Transposing a yaw-only basis
gives `yaw(-θ)`, which mirrors the heading about world −Z: 172° wrong for this spawn, 180° for a
due east-west street, and **0° — a silent no-op — for a north-south one**. So the error is
invisible on exactly the streets where you would trust an eyeball check. `RoadSpawn.basis_facing`
takes a direction and builds the rotation with `Basis.looking_at`, so there is no literal left to
transpose; `tools/verify_spawn.gd` asserts `(-basis.z).is_equal_approx(forward)` and *also*
requires the transposed basis to fail, which is what stops the assertion passing vacuously.

There is also a check needing no tooling at all, and it is the one that caught this: **the harbour
is north**, so from a car facing east, a left turn heads for the water. Getting that wrong is
visible from the driver's seat.

Two things are knowingly missing, and both are someone else's task: **there is no ground** so
anything off the carriageway is void (the terrain did not fit any budget — see `P1-2`, now
scheduled as `P3-10`), and **the flyovers cannot be reached** (`Q13`). A dev harness on the root
catches the car when it falls out of the world, because the kerbs are 0.15 m and mountable by
design.

**Buildings had no collision until `P2-5`, and that was the third.** `P2-1` was nominated to decide
where tile colliders come from and decided they were an ETL product — which was the right answer and
left nobody holding the work, so the region shipped as a hologram the car drove straight through.
It surfaced as a blocker on `P2-5`, whose acceptance criterion is "no clipping through buildings":
a `SpringArm3D` has nothing to collide *with* until the buildings do. See the tile contract above.

| Path | Role |
|---|---|
| `scripts/city/city_manifest.gd` | **`city.json`, typed.** The shipping route into the generated city: the tile list, their AABBs, the per-edge carriageway widths, and the resolved paths of the three documents |
| `scripts/city/city_streamer.gd` | **`CityStreamer` (`P2-1`).** Loads and frees tiles by distance to their published `aabb`, off the main thread, and owns the LOD tier. On the boot path in place of `tile_preview.gd` |
| `scripts/core/tile_streaming.gd` | The streaming **policy**, pure — distance to an `AABB` in, tier out. No `Node`, no `load()`, so the whole decision table is testable headlessly and a tile cannot be rejected *after* being loaded |
| `scripts/core/plan_lattice.gd` | An even grid of plan positions over a region's bounds. Both region-sweeping verify tools take their sample points from it — counted, not float-accumulated, so the far row and column cannot be dropped |
| `scripts/city/streaming_profile.gd` | Schema for the distance bands, hysteresis and per-frame budgets. Numbers live only in `tuning/streaming.tres` |
| `scripts/city/road_graph.gd` | **`RoadGraph` (`P2-2`).** One parse per scene, nearest-edge and lane-centre queries over a plan grid. Refuses off-grade edges — see `Q13` |
| `scripts/city/road_spawn.gd` | **`RoadSpawn` (`P2-3`).** Where a car starts, resolved from a fare node through `RoadGraph`. `basis_facing` builds the rotation from a direction, which is what deleted the hand-written transform literal and the transpose trap with it |
| `scripts/city/road_graph_overlay.gd` | Dev: draws the resolved edge, lane centre and legal travel direction under the moving car |
| `scripts/city/generated_road_surface.gd` | Dev locator for `roads.glb` — one definition, two readers |
| `scripts/city/generated_road_graph.gd` | Same, for `roadgraph.json` |
| `scripts/city/generated_fares.gd` | Same, for `fares.json`. The one place that knows that document's shape: the `kind` and `stand_category` spellings — the ETL is authoritative for those — plus `node_by_id` and `position_of` |
| `scripts/city/generated_document.gd` | Parse and version-check a JSON document the ETL wrote. Shared by the locators above and by `CityManifest`, so the stale-copy message exists once |
| `scripts/city/mesh_contract.gd` | The mesh rules every generated asset is held to, plus `triangles` and `bounds`. Every verify tool that touches geometry reads it, as do the previews and `CityStreamer` |
| `scripts/city/preview_draw.gd` | Flat ribbons and the unshaded vertex-colour material, shared by the dev previews |
| `scripts/city/tile_preview.gd` | Dev: instantiate every tile the manifest names at one tier, report triangles. Still used by `city_preview.tscn`, where looking at the whole region is the point — **not** a performance measurement, and no longer on the boot path |
| `scripts/city/road_surface_preview.gd` | Dev: instantiate the road surface, report triangles and colliders |
| `scripts/city/road_preview.gd` | Dev: draw the road graph flat, with one-way arrows. Answered `Q12` |
| `scripts/city/fare_preview.gd` | Dev: pin every fare node and tether it to `nearest_edge` at `edge_t` |
| `scripts/city/drive_harness.gd` | Dev: place the car on the resolved start line, and return it there when it leaves the world. On the scene root so its `_ready` runs after the car's |
| `scripts/camera/free_look_camera.gd` | Dev: fly camera. Bypasses `InputRouter` so dev keys stay out of the shipped action map |
| `scenes/world/golden_hour.tscn` | The one lighting rig, per `ART_DESIGN.md`. Instance it rather than authoring a second Environment |
| `tools/verify_tiles.gd` | Headless acceptance check for generated tiles — the mesh contract |
| `tools/verify_city.gd` | Headless acceptance check for `city.json` — georeferencing, bounds, and the files it names |
| `tools/verify_road_graph.gd` | Headless acceptance check for `RoadGraph`'s queries — the `Q13` refusal, edge resolution, lane placement against the published carriageway width, and query time against a 1 ms budget over a region-wide probe lattice |
| `tools/verify_road_surface.gd` | Headless acceptance check for `roads.glb` — one draw call, UVs, trimesh collision |
| `tools/verify_city_streamer.gd` | Headless acceptance check for the streaming policy — band edges, hysteresis in both directions, and a region-wide residency sweep against the draw-call budget. Reports resident triangles as a ceiling rather than gating on them |
| `tools/verify_spawn.gd` | Headless acceptance check for `P2-3`'s start line — the orientation against its edge vector, the nearside-lane placement, the drop height, and that the resolved edge is the one the fare node publishes. **Builds the transposed basis and requires it to fail**, so the check cannot pass vacuously on a street where the bug is invisible |
| `tools/generated_scene_import.gd` | Import fixup — see the `[importer_defaults]` row above |

---

## Constraints

1. No runtime network calls. The game is fully offline.
2. No engine-specific formats out of the ETL — glTF and JSON only.
3. No hardcoded Hong Kong specifics outside `etl/config/cities/`.
4. Tuning values live in `game/tuning/*.tres`, never as constants in scripts.
