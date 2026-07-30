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

**Autoloads:** `FpsCounter` (debug builds, or `--fps`) and `InputRouter`. Both run every frame for
the life of the process, so treat them as hot-path code.

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
│   │   ├── gltf.py              # glTF read + GLB write; no dependency, see its docstring
│   │   ├── gdb.py               # geodatabase layers + WKB → numpy; format only, no policy
│   │   ├── mesh.py              # merge, partition, LOD collapse — geometry, no policy
│   │   ├── terrain.py           # terrain mesh → sampleable height field (Q11)
│   │   ├── buildings.py         # sheets → vertex-coloured tiles + LOD tiers
│   │   ├── roads.py             # Road Network geodatabase → roadgraph.json
│   │   ├── surface.py           # roadgraph.json → roads.glb; ribbon, kerbs, junctions
│   │   ├── fares.py             # taxi stands + PUDO + POIs → fare nodes
│   │   └── export.py            # → city.json, assembles the tile/road/fare outputs
│   ├── sources/<city>/<source>/ # raw downloads — GITIGNORED
│   ├── out/<city>/<region>/     # pipeline output — GITIGNORED
│   └── tests/
├── game/                        # Godot project
│   ├── project.godot
│   ├── export_presets.cfg       # COMMITTED — never put signing credentials here
│   ├── scenes/
│   │   ├── dev/                 # grey-box circuit, city preview — not shipped
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
└── tools/                       # dev scripts, export automation
```

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
  "schema_version": 1,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "source_crs": "EPSG:2326",
  "origin": { "easting": 835765.0, "northing": 816125.0, "elevation": 0.0 },
  "city_offset": [38379.0, 0.0, 32826.0],
  "bounds_game": { "min": [0, -20, 0], "max": [1650, 220, 900] },
  "tile_size_m": 150,
  "tiles": [
    {
      "id": "t_00_00",
      "lods": ["tiles/t_00_00_lod0.glb", "tiles/t_00_00_lod1.glb", "tiles/t_00_00_lod2.glb"],
      "aabb": [[0,0,0],[150,120,150]]
    }
  ],
  "etl_version": "0.1.0",
  "generated_utc": "2026-07-29T00:00:00Z"
}
```

`origin` is computed by the ETL from the region bounds, never authored. The values above are the
real ones for Wan Chai — `floor(min_easting)` and `ceil(max_northing)`, i.e. the region's
**north-west** corner. Anything reading `city.json` should treat them as data, not as constants.

`lods` is ordered nearest-first, one file per tier, matching `lod_cell_sizes_m` in city config.
Separate files rather than one GLB with three meshes, because the streamer loads a tier at a time.

**A tile's `aabb` can be larger than the tile.** Buildings are assigned to a tile whole, by their
centre, so one may overhang its neighbour by half a footprint — measured at up to 222 m across a
150 m tile in Wan Chai. Use the `aabb` for culling and streaming distance, never the tile's grid
position.

**Tile output carries no textures.** One material, one primitive, colour in `COLOR_0` — that is
what makes a tile one draw call, and it is checked in-engine by
`game/tools/verify_tiles.gd`.

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
| `elevation_level` | `ELEVATION` integer attribute (verified: −1/0/1 in the region). Ordinal level, **not** a height — map to deck heights via city config. Those heights are offsets **from ground level, not from the vertical datum**; see `Q11`. |
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
  "nodes": [
    {
      "id": "f_001",
      "pos": [420.0, 3.5, 610.0],
      "kind": "taxi_stand",
      "stand_category": "cross_harbour",
      "name": { "en": "Times Square", "zh": "時代廣場" },
      "nearest_edge": 42
    }
  ]
}
```

`kind` ∈ `taxi_stand` | `pudo` | `poi`. `stand_category` is null unless `kind` is `taxi_stand`.

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

Two tiers, selected at runtime by platform.

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
      →  etl/out/<city>/<region>/{city.json, roadgraph.json, fares.json, tiles/*.glb}
      →  copied to game/assets/generated/
      →  Godot export presets → iOS / Android / desktop / web-demo
```

Each stage also runs on its own against the same arguments, which is how they are developed and
how a partial rebuild is done:

```
python -m pipeline.fetch     --city hong_kong --region wan_chai
python -m pipeline.buildings --city hong_kong --region wan_chai
```

`fetch` is the only stage that touches the network; everything after it reads `etl/sources/`.

The ETL is **not** run by CI on every commit — it is run when source data or pipeline logic
changes, and its output is treated as a versioned build artefact.

**Generated assets are checked in-engine, not by eye.** `godot --headless --path game --script
res://tools/verify_tiles.gd` loads every tile and asserts the draw-call, vertex-colour and
no-texture properties this contract states. Run it after a rebuild; the ETL cannot assert
engine-side facts about its own output.

**To look at the result before `P1-7`:** open `scenes/dev/city_preview.tscn` and run it (F6).
It instantiates every tile — no streaming, no LOD switching, so it is *not* a performance
measurement — and frames whatever is on disk. Set the `Tiles` node's `lod` to see a coarser tier.
Tile vertices are in region game space, so tiles need no transform; dropping one at the origin
puts it where it belongs. That is why `city.json` gives tiles an `aabb` but no position.

| Path | Role |
|---|---|
| `scripts/city/generated_tiles.gd` | Where tile output lives and how to list it — one definition, two readers |
| `scripts/city/tile_preview.gd` | Dev: instantiate every tile, report bounds |
| `scripts/camera/free_look_camera.gd` | Dev: fly camera. Bypasses `InputRouter` so dev keys stay out of the shipped action map |
| `scenes/world/golden_hour.tscn` | The one lighting rig, per `ART_DESIGN.md`. Instance it rather than authoring a second Environment |
| `tools/verify_tiles.gd` | Headless acceptance check for generated tiles |
| `tools/generated_scene_import.gd` | Import fixup — see the `[importer_defaults]` row above |

---

## Constraints

1. No runtime network calls. The game is fully offline.
2. No engine-specific formats out of the ETL — glTF and JSON only.
3. No hardcoded Hong Kong specifics outside `etl/config/cities/`.
4. Tuning values live in `game/tuning/*.tres`, never as constants in scripts.
