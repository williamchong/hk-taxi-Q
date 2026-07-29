# Architecture

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Engine | **Godot 4.7** | MIT, no royalties or seat fees |
| Renderer | **Mobile** (primary), Compatibility for web demo | Forward+ only if desktop tier justifies it later |
| Physics | **Jolt** — Godot's default since 4.4 | Has a wheeled vehicle controller |
| Engine language | **GDScript**, statically typed | See decision below |
| ETL | **Python 3.11+** — GDAL/OGR, geopandas, trimesh/pygltflib | Build-time only |
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

| Setting | Value | Why |
|---|---|---|
| `rendering/renderer/rendering_method` | `mobile` | Locked decision. Set as the **base** value, not only the `.mobile` override, so the editor and desktop builds preview the renderer the phone will actually run. |
| `rendering/renderer/rendering_method.web` | `gl_compatibility` | Web export is WebGL2-only. |
| `rendering/textures/vram_compression/import_etc2_astc` | `true` | Godot refuses to export **any** arm64 target without it — iOS, Android, and Apple Silicon macOS alike. |
| `physics/3d/physics_engine` | `Jolt Physics` | Locked decision. It is the default since 4.4, but stated explicitly so the project does not silently follow a changed engine default. |
| `application/run/max_fps.mobile` | `60` | Rendering uncapped on a 90/120 Hz phone panel buys nothing above the 60fps target and throttles the device — the most likely way to lose the frame-rate floor in a sustained session. Desktop stays uncapped. |
| `display/window/stretch/mode` | `canvas_items` | Resolution-independent UI; desktop is a target alongside phones. |

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
│   │   ├── fetch.py             # download from CSDI / data.gov.hk, cache to sources/
│   │   ├── crs.py               # ONLY module that knows about EPSG:2326
│   │   ├── buildings.py         # non-textured glTF / 3D-BIT00 → merged tile meshes
│   │   ├── roads.py             # Road Network FGDB/GML → road graph + ribbon meshes
│   │   ├── fares.py             # taxi stands + PUDO + POIs → fare nodes
│   │   ├── tiles.py             # spatial partition, LOD generation
│   │   └── export.py            # → glTF + JSON, writes manifest
│   ├── sources/                 # raw downloads — GITIGNORED
│   ├── out/                     # pipeline output — GITIGNORED
│   └── tests/
├── game/                        # Godot project
│   ├── project.godot
│   ├── export_presets.cfg       # COMMITTED — never put signing credentials here
│   ├── scenes/
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
│   └── tuning/                  # .tres resources: handling, fares, scoring
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
  "bounds_game": { "min": [0, -20, 0], "max": [1650, 220, 900] },
  "tile_size_m": 150,
  "tiles": [
    { "id": "t_00_00", "mesh": "tiles/t_00_00.glb", "aabb": [[0,0,0],[150,120,150]] }
  ],
  "etl_version": "0.1.0",
  "generated_utc": "2026-07-29T00:00:00Z"
}
```

`origin` is computed by the ETL from the region bounds, never authored. The values above are the
real ones for Wan Chai — `floor(min_easting)` and `ceil(max_northing)`, i.e. the region's
**north-west** corner. Anything reading `city.json` should treat them as data, not as constants.

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
| `direction` | `TRAVEL_DIRECTION` (1 = bidirectional → `both`, 3 = one-way → `forward`) |
| `turn_restrictions` | `TURN_ID` + `EDGE(1-8)FID` |
| `speed_limit_kph`, `bus_lane` | Road Network v2 attributes |
| `tram_tracks` | ⚠️ **Hand-authored.** Not present in the source dataset. |
| `width_m` | Derived from `lanes`, then **hand-tuned upward** for playability (see Game Design) |
| `elevation_level` | `ELEVATION` integer attribute (verified: 0/1/2 present). Ordinal level, **not** a height — map to deck heights via city config. Two edges may only form a junction if levels match. |
| `road_name` | `STREET_ENAME` / `STREET_CNAME` — **bilingual names ship in the source.** Treat `-99` and `–９９` as null. |

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

⚠️ The origin is currently **per region**. If two regions must ever stitch into one continuous
map, they need a shared per-city origin instead — a `schema_version` change, not a tuning change.
Unresolved; see `PROGRESS.md`, `Q10`.

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
      →  etl/out/{city.json, roadgraph.json, fares.json, tiles/*.glb}
      →  copied to game/assets/generated/
      →  Godot export presets → iOS / Android / desktop / web-demo
```

The ETL is **not** run by CI on every commit — it is run when source data or pipeline logic
changes, and its output is treated as a versioned build artefact.

---

## Constraints

1. No runtime network calls. The game is fully offline.
2. No engine-specific formats out of the ETL — glTF and JSON only.
3. No hardcoded Hong Kong specifics outside `etl/config/cities/`.
4. Tuning values live in `game/tuning/*.tres`, never as constants in scripts.
