# hk-taxi-Q — Agent Instructions

Arcade taxi game set in Hong Kong, built from HK government open geodata.

**Read `docs/` before starting any task.** These decisions are settled — do not re-litigate
them without explicit instruction from the user.

## Locked decisions

| Decision | Value | Why |
|---|---|---|
| Engine | **Godot 4.7**, Mobile renderer | Commercial mobile app target; native perf; MIT, no royalties |
| Physics | **Jolt** (Godot default since 4.4) | Stable trimesh collision and raycasts under the custom vehicle controller. ⚠️ *Not* for its built-in `VehicleBody3D` — `P0-5a` measured that and rejected it; `VehicleWheel3D` friction is isotropic, so it cannot express a drift that breaks lateral grip while keeping traction |
| Language | **GDScript** (not C#) | C# web export is unsupported, and iOS/Android C# export is experimental. See `docs/ARCHITECTURE.md`. |
| ETL | **Python 3.11+** (`pyogrio`, `pyproj`, `numpy`) | Best geodata tooling; runs offline at build time. `pyogrio` ships its own GDAL, so no system install. **No geopandas** — `gdb.py` wants coordinate arrays, and GeoDataFrames would add pandas to reach the same numpy underneath |
| Building source | **3D Visualisation Map (non-textured)** + **3D-BIT00 Level 1** | Already flat-shaded extruded volumes — the low-poly look is native to this data |
| Region (PoC) | **Wan Chai → Causeway Bay**, ~1.5 km² | Natural circuit, diegetic map edges, moderate Z-complexity |
| Art direction | Low-poly flat-shaded; **accurate city, toy vehicles** | Recognisability requires accurate massing; charm comes from the cars |
| Monetisation | Free download + one-time unlock IAP | Deferred to launch; affects only the free-slice boundary |

## Hard rules

1. **Never use the tile-based photogrammetry mesh** for buildings. It has ground gaps, level
   differences, and vehicles baked into the geometry. A prior public attempt found it unsuitable
   for driving. See `docs/DATA_SOURCES.md`.
2. **ETL is build-time only.** The game makes zero network calls at runtime. Never couple the
   game to a government API.
3. **ETL stays city-agnostic.** CRS, source schemas, and bounds live in
   `etl/config/cities/*.yaml`. Never hardcode `EPSG:2326` or Hong Kong bounds in pipeline logic —
   the second city is the business case.
4. **All tuning values are data**, not constants in code. Handling curves, fare timers, road
   widths → Godot `.tres` resources or JSON.
5. **Respect the data contract** in `docs/ARCHITECTURE.md`. ETL output and game input are a
   versioned interface; change both sides together and bump `schema_version`.
6. **Attribution is mandatory.** The credits screen must acknowledge the Government of the HKSAR,
   the relevant departments, and DATA.GOV.HK. See `docs/DATA_SOURCES.md`.
7. **Never use the phrase "Crazy Taxi"** in any user-facing text, store listing, marketing copy,
   or ASO keyword. It is a SEGA trademark. Use it only in internal docs as a genre shorthand.

## Commits — gitmoji

Format: `<emoji> <task-id> <imperative summary>` — **no brackets**, as in the examples below.

The task ID is **required** when the work maps to a task in `docs/PLAN.md`, omitted otherwise.

```
✨ P1-3 Extract road graph from Road Network v2
🐛 P2-3 Stop vehicle losing grip when mounting kerbs
📝 Record Z-value spike findings in DATA_SOURCES
⚡ P2-6 Merge tile meshes to cut draw calls below budget
```

Common emoji for this project:

| Emoji | Code | Use |
|---|---|---|
| ✨ | `:sparkles:` | New feature |
| 🐛 | `:bug:` | Bug fix |
| 📝 | `:memo:` | Docs |
| ⚡ | `:zap:` | Performance |
| ♻️ | `:recycle:` | Refactor |
| 🎨 | `:art:` | Art assets, structure/format of code |
| 🔧 | `:wrench:` | Config |
| ✅ | `:white_check_mark:` | Tests |
| 🚚 | `:truck:` | Move/rename files |
| 🔥 | `:fire:` | Remove code or files |

## Conventions

- Python: `ruff` for lint/format, type hints on public functions, `pytest` for tests.
- GDScript: `snake_case` files and functions, `PascalCase` classes, static typing (`var x: int`;
  `:=` counts). `gdformat` owns layout — do not hand-format around it. Untyped declarations fail
  the build, so this is enforced, not advisory.
- Generated assets go to `game/assets/generated/` and are **gitignored** — they are build output.
- ⚠️ Opening the Godot editor or running an export rewrites `game/project.godot` and
  `game/export_presets.cfg`, stripping their comments. Never commit either as a side effect; see
  `docs/ARCHITECTURE.md` for how to restore and verify. Headless `--import`/`--script` are safe.
- Hand-authored assets go to `game/assets/authored/` and **are** committed.
- This is not a Node project. Do not run npm/npx/node commands.

## Before marking work done

- Python changes: `ruff check .` and `ruff format --check .` **from the repo root** (the root
  `ruff.toml` extends the ETL rules to `tools/*.py`; running ruff from `etl/` skips them), and
  `pytest` from `etl/`.
- ETL changes: the pipeline runs end-to-end on the Wan Chai config without errors.
- Godot changes: `gdformat --check` passes over `game/**/*.gd`, the project imports without script
  errors (GDScript warnings are errors — see `docs/ARCHITECTURE.md`), the target scene runs, and
  the three headless checks pass — `verify_city.gd`, `verify_tiles.gd`, `verify_road_surface.gd`.
- Update `docs/PROGRESS.md` — task status, plus any new decision or open question.

## Where to look

| Doc | Contains |
|---|---|
| `docs/DATA_SOURCES.md` | Verified datasets, formats, licences, CRS, known issues. **Read before touching ETL.** |
| `docs/ARCHITECTURE.md` | Stack, repo layout, data contract, performance budget, runtime systems |
| `docs/GAME_DESIGN.md` | Core loop, fares, scoring, controls, HK authenticity mechanics |
| `docs/ART_DESIGN.md` | Visual direction, palette, shaders, LOD policy, hero buildings |
| `docs/PLAN.md` | Phased task breakdown with acceptance criteria |
| `docs/PROGRESS.md` | Live status, decision log, open questions |
