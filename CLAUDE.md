# hk-taxi-Q — Agent Instructions

Arcade taxi game set in Hong Kong, built from HK government open geodata.

**Read `docs/` before starting any task.** These decisions are settled — do not re-litigate
them without explicit instruction from the user.

## Locked decisions

| Decision | Value | Why |
|---|---|---|
| Engine | **Godot 4.7**, Mobile renderer | Commercial mobile app target; native perf; MIT, no royalties |
| Physics | **Jolt**, driving `VehicleBody3D` | Stable trimesh collision under the vehicle. ⚠️ `Q50` reversed `P0-5a`'s custom raycast controller on the user's instruction (2026-08-18). `VehicleWheel3D` friction is isotropic, so it cannot break lateral grip while keeping traction — still true; the engine model ships anyway. The drift dial is graded on *dwell*, never on landing peak slip on the threshold (`Q84`) |
| Language | **GDScript** (not C#) | C# web export is unsupported, and iOS/Android C# export is experimental. See `docs/ARCHITECTURE.md`. |
| ETL | **Python 3.11+** (`pyogrio`, `pyproj`, `numpy`, `shapely`) | Best geodata tooling; runs offline at build time. `pyogrio` ships its own GDAL and `shapely` its own GEOS (`Q129`, approved 2026-09-18), so no system install. **No geopandas** — `gdb.py` wants coordinate arrays, and GeoDataFrames would add pandas to reach the same numpy underneath |
| Building source | **3D Visualisation Map (non-textured)** + **iB1000** for podium floors, tram rails and lamp posts | Already flat-shaded extruded volumes — the low-poly look is native to this data (`Q47`, `Q100`) |
| Region (PoC) | **Wan Chai → Causeway Bay**, ~1.5 km² | Natural circuit, diegetic map edges, moderate Z-complexity |
| Art direction | Low-poly flat-shaded; **accurate city, toy vehicles** | Recognisability requires accurate massing; charm comes from the cars |
| Monetisation | Free download + one-time unlock IAP | Deferred to launch; affects only the free-slice boundary |

## Hard rules

1. **Never use the tile-based photogrammetry mesh** for buildings. It has ground gaps, level
   differences, and vehicles baked into the geometry. A prior public attempt found it unsuitable
   for driving. See `docs/DATA_SOURCES.md`.
2. **ETL is build-time only.** The game makes zero network calls at runtime. Never couple the
   game to a government API.
3. **Hong Kong is the only city (`Q100`).** Its facts live in **one** place each:
   `etl/config/hong_kong.yaml` for tuning and a publisher's vocabulary (codes, `fields:` role maps,
   bounds, `elevation_levels`), and `etl/pipeline/hongkong.py` for the constants that *are* the city
   (the CRS pair, drive-on-the-left, the branch sign codes). Never a second copy. Multi-**region**
   support stays (`Q6`, `Q10`); there is no second city and no `--city` flag.
4. **All tuning values are data**, not constants in code. Handling curves, fare timers, road
   widths → Godot `.tres` resources or JSON. The road's own numbers are *measured* data:
   - **Level-0 ribbon** (`Q129`): not drawn at a width at all — its rails are its territory's
     extents in `carriageway_region.json`, and `floor_default_m` is 0.0 on the user's call.
     `drawn = max(width_m, floor)` describes only off-grade edges, a run past its rectangle, and the
     junction trim radius. The widening is a **floor, never a multiplier** (`Q95`).
   - **`width_m`** (`Q95`, `Q128`): measured from TD, iB1000 and HyD, five sources; `width_source`
     says which, `width_confirmed_by` names the evidence. Two ray stations publish when they agree
     within the region's leave-one-out scatter; HyD's paint strip publishes only where an
     independent reading confirms it — alone it is no better than the invented width.
     ⚠️ `width_m != lanes x lane_width_m`.
   - **`lanes`** (`Q94`): bracketed off the width against TPDM 4.3.9.8's 3.0–3.65 m lane, **never**
     divided by `lane_width_m` (the instrument would agree with the constant under test).
     Ambiguous edges keep the authored count; `lanes_source` says which. ⚠️ A lane count moves no
     geometry — only the `TEXCOORD_0` lane coordinate and the arrow slots.
   - **`lanes` can be 1** (`Q114`) with no floor under it here; `lanes_source` has `deck_capped`,
     not `floored`. The floor a one-lane road needs lives in `RoadGraph.lane_offset`.
   - **`arrows_unmeasured`** (`Q130`, schema 15): on an authored width, a row of ≥2 arrows abreast
     RAISES the count, never lowers it. Kept out of `CarriagewayReport.lanes`;
     `verify_road_graph.gd` requires the authored width beside it.
   - **`lanes_forward`** (`Q126`, schema 13): a row of turn arrows on a two-way edge is read by
     direction, and the shader draws the centre line at `U = lanes_forward`. Above the narrowed
     bracket only — the row is a lower bound. `null` on an odd two-way count nothing split.
     ⚠️ **The codec is full**: the next field needs another channel. Both row readers
     (`carriageway._row_reading`, `arrows._row_reading`) restate the rule;
     `lanes_split_disagreement` is their diff.
5. **Respect the data contract** in `docs/ARCHITECTURE.md`. ETL output and game input are a
   versioned interface; change both sides together and bump `schema_version`. Bump where a consumer
   would be **wrong** to keep its old interpretation — not wherever bytes change.
6. **Attribution is mandatory, and it is stronger than naming a source.** The credits screen must
   acknowledge the Government of the HKSAR, the relevant organisations, and **both** DATA.GOV.HK and
   the CSDI Portal — including their **ownership of the intellectual property rights**. Draft text in
   `docs/DATA_SOURCES.md`; the operative terms are quoted in `LICENSING.md`.
7. **Three licences, three owners.** Code is GPL-3.0-or-later, hand-authored assets are CC BY-SA 4.0,
   and the generated city data is **nobody's to relicense** — it stays under the government terms and
   is never committed. Contributions come in under MIT so store builds stay possible. `LICENSING.md`.
8. **Never use the phrase "Crazy Taxi"** in any user-facing text, store listing, marketing copy,
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
- **Rationale for a `.tres`, `.tscn`, `project.godot` or `export_presets.cfg` goes in prose beside
  the file, never in it** (`Q119`): a resource's in a sidecar (`handling.md` beside
  `handling.tres`), the config files' in `docs/ARCHITECTURE.md`. Godot's writer drops comments and
  default values, so the files are committed in the writer's own form and an editor save is a
  no-op. `check.sh` refuses a `;` line in a resource and requires the sidecar.
  ⚠️ A headless `--import` re-tabs the tracked `game/assets/authored/greybox_wanchai.json`
  (`Q115`): `git status` after `check.sh`, and `git checkout` it.
- Hand-authored assets go to `game/assets/authored/` and **are** committed.
- This is not a Node project. Do not run npm/npx/node commands.

## Before marking work done

- **Grader batteries are a table** (`Q133`): `tools/battery.py <trigger> --region <r> --before
  <checkout root> [--jobs 2]`; `--list` prints it. It runs this checkout against a detached
  worktree holding the before build, saves outputs under `build/battery/` and writes a diff per
  item. ⚠️ Its exit code says every item RAN, never that a number held — a grader that gates and
  fails (`carriageway_occupancy`, `clearance_reconcile`) still ran. ⚠️ Both sides are graded by
  THIS checkout's tools; `--tools-from side` is for a bundle whose schema moved. ⚠️ A row must
  carry `{generated}` or `{out_root}` — `--region` alone reads this checkout on both sides and
  diffs empty; `test_every_tool_is_pointed_at_its_own_side` is the ratchet. Not in the table:
  anything needing a frame, a drive, a sweep of a free value, or `tools/skidpad.sh`.
- Python changes: `ruff check .` and `ruff format --check .` **from the repo root** (the root
  `ruff.toml` extends the ETL rules to `tools/*.py`; running ruff from `etl/` skips them), and
  `pytest` from `etl/`.
- ETL changes: the pipeline runs end-to-end on the Wan Chai config without errors.
- Godot changes: `tools/check.sh` passes, and the target scene runs. The script covers formatting,
  the import, the GDScript warnings sweep and the verify tools. **Do not run those by hand
  and read the output** — Godot exits `0` even when a script fails to parse, so only the script's
  exit code means anything. See `docs/ARCHITECTURE.md` "Checks".
- Update `docs/PROGRESS.md` — task status, metrics, risks, and the questions index.
- Record any new decision, or any question that closes, in `docs/DECISIONS.md`, keyed by its ID.
- **Bundle size is measured from a PCK, never summed from source files.** That rule has been wrong
  in both directions once each.

### Scoped checklists — `.claude/rules/`

🔴 **Every other checklist lives in `.claude/rules/<name>.md` and loads ITSELF when a file in its
`paths:` is read.** A change that arrives another way — a `hong_kong.yaml` block, `config.py` (a stage's own
`config_blocks/<stage>.py` does load its rule; `roads.py` there serves too many to), a
shared helper — loads nothing, so **match it against this table and read the rule by hand before
marking work done.** `tools/battery.py --list` carries the same triggers with their commands. A new
checklist goes in a rule file, never back here: `check.sh` refuses a root `CLAUDE.md` over 40k chars.

| Rule | Read it when the change touches |
|---|---|
| `facade` | Height ramp, façade survey, `facade_hue.strength`, `materials:` colours or `bounds:`, the rigs' `exposure_anchor`, the filler guard (`is_filler`, `MODAL_SHARE`, `MODAL_STRIDE`) |
| `handling` | `VehicleController`'s drive model, `HandlingProfile`, `handling.tres`, any drift dial — `tools/skidpad.sh` before and after |
| `lanes` | `lanes`, `lanes_source`, `LANE_FLOOR`, `_ROW_MIN`, `_deck_lane_ceiling`, the drawn ribbon's width |
| `carriageway` | `pipeline/carriageway.py`, `carriageway_area.py`, the `carriageway_survey` block, `width_m`, `surface.floor_*`, `lane_width_m`, `MIN_STATIONS` and the two-station / HyD-strip licences, `confirm_within_m`, `width_evidence.py`, a station normal, any centreline rule |
| `clearance` | `clearance.py`, `carriageway_occupancy.py`, `clearance.LEVELS`, `ALONG_M` and the resolution constants, `surface.floor_default_m` or any widening, a disagreement between the two corridor instruments |
| `region` | `pipeline/region.py`, `surface_region.py`, `tools/carriageway_region.py`, the `carriageway_region` block (`seam_m`, `rail_tolerance_m`, `rail_opening_m`), islands, `opened` / `flare_m`, the level-0 floors, any new reader of `half_width_m` at level 0 |
| `surface` | `surface.py`: `_read_offside` / `_opposed_gaps` / `opposed_pair_bearing_deg`, stubs, clusters, caps and corridors, `_clamped_rails` and `deck_rim_m`, **any tool that reconstructs the drawn ribbon** (`offset_m`), road-surface, deck-height or ground changes |
| `deck` | An off-grade ribbon (`floor_by_elevation_level`, `floor_on_structure_m`), `_deck_heights`, `_descend`, `_lifted_heights`, `touchdown_max_grade_pct` |
| `ground_clearance` | `ground_clearance.py`'s structure half, `structure_class`, `BUMPER_LOW_M` / `BUMPER_HIGH_M`, anything that carves |
| `kerbside` | `pipeline/kerbside.py`, the `NSR` block, `painted_vehicle_types`, `kinds` |
| `tramway` | `pipeline/tramway.py`, the `tramway` block |
| `railings` | `pipeline/railings.py`, the `railings` block, `railings.gdshader`, a railing class's `.tres` |
| `signs` | `pipeline/signs.py`, `sign_text.py`, the `signs` block (`outset_m`, `max_shift_m`, `faces`, `faces_against_traffic`, `colours`, `text*`), the signs atlas, and the removed `P3-17` signal layer |
| `arrows` | `pipeline/arrows.py`, the `arrows` block, the glyph table, `marking_paint.gdshader` |
| `roadmarks` | `pipeline/roadmarks.py`, the `road_marks` block (`more_layers`, `marks:`, `broken_line`, `divides_flows`, `axis` — `oblique` included — `chevron_width_m` / `chevron_turn_deg`, `opposed_join_mark`), `draw_lane_lines` / `draw_centre_line` / `draw_pair_join`, `marking_paint.gdshader` |
| `carve` | `pipeline/carve.py`, the `carve` block, which edges are carved |
| `crossings` | `pipeline/crossings.py`, the `crossings` block (`line_types`, `zebra`, `lift_m`, `max_stripe_width_m`), which paint a crossing takes |
| `boxjunctions` | `pipeline/boxjunctions.py`, the `boxjunctions` block, the drawn ribbon's extent, any painted layer's height or `lift_m`, `DrawnSurface` |
| `hud` | `hud.gd`, `hud_layout.tres`, `hud_style.tres`, `wrong_way_monitor.gd`, `wrong_way.tres`, `street_plate.json`, the bundled font, any new region's street names, the start menu (`start_menu.gd`, `menu.tres`, `menu_text.json`, `settings.gd`, `main.gd`'s park / resume) |
| `lamps` | `pipeline/lamps.py`, the `lamps` block |
| `fence` | `pipeline/fence.py`, the `clearance` or `fence` blocks (`clipped_within_m` included), `RoadGraph`'s car bar |
| `join` | `join.reach_m`, `Config.neighbours` / `read_*`, a region's `bounds`, who owns a crossing road |
| `fares` | `fare_system.gd`, `fare_meter.gd`, `fare.gd`, `tariff.tres` (TD's numbers, cited), `fares.tres` (ours), the pools, the allowance, the tip, `verify_fares.gd` |
| `router` | `road_router.gd`, `RoadGraph`'s `from` / `to` / turn bans / `plan_length_of`, `tools/reachability.py`, a profile's rules or bar, anything that consumes a route |
| `tiles` | Colliders (`collision_cell_m`, `_collider`, `_road_collider`) and occluders (`occluder_cell_m`, `use_occlusion_culling`), any tile reader |
| `basemap` | `pipeline/basemap.py`, the `basemap` block (`seal_m`, `water_level_m`, `seabed_m`, `water_material`, `park_material`), `buildings.sink_sea` and `paint_parks`, `water.tres`, the `Water` node |

⚠️ **Three changes reach past their own rule.** A **widening** (`surface.floor_default_m`, any
`roads.surface` width) moves the drawn kerb, so it owes `clearance`, `carriageway`, `railings`,
`signs`, `lamps` and `boxjunctions`. A **shader** change owes a render and
`grep -i "shader error"` — `check.sh` exits 0 on a shader that fails to compile — on every layer
that shares it (`marking_paint`: arrows, boxes, stop lines; `signs.gdshader`: signs and lamps). And
**anything that carves** owes `carve`, `ground_clearance` and `clearance`.

### Measured shut — do not re-propose

Each of these was built or measured and refused; the rule file and the `Q` hold the numbers. Several
read like inconsistencies and are not — "restoring consistency" is how most of them broke before.

- **No centreline-shift rule** (`Q19` candidate 1, refuted: clears 0 edges) — `carriageway`.
- **No junction-opening gate on the ray survey** (`Q127`), and **no polygonising the line
  publishers' kerbs** where HyD is silent (`Q129`: rails, not faces) — `carriageway`, `region`.
- **No area cap for islands, and `seam_m` is not raised to clear a pinch** (`Q131`) — `region`.
- **No angle-free opposed-pair rule** (mutual kerb burial, `Q117`), **no free search radius**
  (`Q72`), and **no kerb-line corner rule for caps** (`Q104`) — `surface`.
- **`draw_lane_lines`, `draw_centre_line` and `draw_pair_join` stay off** (`Q132`, `Q125`), and a
  longitudinal mark is **not sampled from its host's own edge** (`Q118`) — `roadmarks`.
- **No vertical term in the `clearance:` block** (`P3-29` built and withdrew it), and **`is_passable`
  and `fits_car` are two bars, never merged** (`Q19`) — `fence`.
- **The survey is not extended off-grade; a deck is a ceiling on `lanes` and paint, never a source of
  a count or a `width_m`** (`Q103`, `Q105`, `Q114`) — `deck`, `lanes`.
- **A territory is a share, never a `width_m`, a corridor or a carriageway** (`Q57`), and the kerb is
  **not** `roadsurface.json`'s per-vertex `corridor_*` (built, measured, withdrawn, `Q133`) —
  `region`, `surface`.
- **A burial is never answered by raising `lift_m`**, a residual never by widening a carve prism, a
  colour never by widening its `bounds:` — `boxjunctions`, `carve`, `facade`.
- **No `arms_against_kerb`, "placed minus drawn" or "stations on deck after the clamp" counter** —
  each reads 0 by construction (`Q72`, `Q58`). A counter is tested by whether a reachable
  configuration moves it; mutation-check it rather than reading its value.
- **The lantern is not lit** (`Q38`, `Q26`), a fence has **no opacity dial**, and the signal layer
  comes back as a **port**, not a re-declared block (`Q77`) — `lamps`, `railings`, `signs`.
- **Deliberately NOT consistent — leave them**: the two station normals (`carriageway._stations`
  right, `surface.mitres` left); the ETL-side and engine-side winding tests' opposite signs (`Q59`);
  `lamps._strut`'s unreversed ring beside `signs._draw_pole`'s reversed one; `railings.py`'s
  unconditional push beside the signs' outward-only clamp (`Q78`); the drift's low branch that
  LATCHES beside the high branch that TRACKS (`Q89`); the wrong-way monitor that CLEARS on a miss
  beside `street_tracker.gd` that HOLDS, and its two angle bars (`Q81`); `min_station_gap_m` beside
  `fold_tolerance_deg`; `opposed_pair_bearing_deg` beside `pair_bearing_tolerance_deg`.
- **Deliberately DUPLICATED — do not import one into the other**: `pipeline/carriageway.py` and
  `tools/carriageway_margin.py` (`Q95`); `pipeline/region.py` and `tools/carriageway_region.py`
  (`Q129`); the two arrow-row readers (`Q94`); `_Ribbon`'s scalar filter beside `_Occluders.cover`;
  `skidpad_ablation._slip_deg` beside `FareSystem.slip_deg_of` (`Q84`, `Q145`).

## Where to look

| Doc | Contains |
|---|---|
| `docs/DATA_SOURCES.md` | Verified datasets, formats, licences, CRS, known issues. **Read before touching ETL.** |
| `LICENSING.md` | Which licence covers what, and what must never be relicensed |
| `CONTRIBUTING.md` | Checks to run, commit style, inbound-MIT licensing of contributions |
| `docs/ARCHITECTURE.md` | Stack, repo layout, data contract, performance budget, runtime systems |
| `docs/GAME_DESIGN.md` | Core loop, fares, scoring, controls, HK authenticity mechanics |
| `docs/ART_DESIGN.md` | Visual direction, palette, shaders, LOD policy, hero buildings |
| `docs/PLAN.md` | Phased task breakdown with acceptance criteria |
| `docs/PROGRESS.md` | Live status — task board, open questions, risks, measured metrics |
| `docs/DECISIONS.md` | **Why anything is the way it is**, keyed by `Q` or task ID. Read before re-proposing something |
