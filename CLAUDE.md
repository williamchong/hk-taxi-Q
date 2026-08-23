# hk-taxi-Q — Agent Instructions

Arcade taxi game set in Hong Kong, built from HK government open geodata.

**Read `docs/` before starting any task.** These decisions are settled — do not re-litigate
them without explicit instruction from the user.

## Locked decisions

| Decision | Value | Why |
|---|---|---|
| Engine | **Godot 4.7**, Mobile renderer | Commercial mobile app target; native perf; MIT, no royalties |
| Physics | **Jolt** (Godot default since 4.4), driving `VehicleBody3D` | Stable trimesh collision under the vehicle. ⚠️ **`Q50` reversed `P0-5a` on the user's explicit instruction (2026-08-18).** The car was a custom raycast controller until then, because `VehicleWheel3D` friction is isotropic and so cannot express a drift that breaks lateral grip while keeping traction. That is still true and was re-measured on the way in: the drift window is **0.01–0.02 wide** and nothing in it lands on `drift_slip_threshold_deg`. The engine model ships anyway; `docs/DECISIONS.md` `Q50` is the record |
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
- Godot changes: `tools/check.sh` passes, and the target scene runs. The script covers formatting,
  the import, the GDScript warnings sweep and the verify tools. **Do not run those by hand
  and read the output** — Godot exits `0` even when a script fails to parse, so only the script's
  exit code means anything. See `docs/ARCHITECTURE.md` "Checks".
- Height-ramp or façade-survey changes: also `tools/ring_weights.py`, and paste what it derives. The
  surveyed material weights are authored against both, and no check can see them go stale (`Q34′`).
- Façade-survey or `facade_hue.strength` changes: also `tools/facade_chroma.py`, and paste its table
  into `docs/ART_DESIGN.md`. `Q30`'s numbers are the argument that the shipped palette is not the
  authored one, and they are only an argument while they describe the survey that ships.
- **Filler-guard changes — `is_filler`, `filler_colours`, `MODAL_SHARE`, `MODAL_STRIDE`: also
  `tools/facade_survey.py --all --filler-report`, and paste its table.** It is the only thing that
  reproduces `Q55`, whose every number came from a scratch script — the same debt `Q37` was opened
  about. ⚠️ **Validate with the guard off first**: re-run the survey with `MODAL_SHARE` above 1.0
  and diff against the shipped table. It must differ on **zero** rows, and that is what proves
  nothing but the guard moved — `Q37`'s own validation move. ⚠️ **The two axes must stay
  disjoint**: a repeated *grey* belongs to `Q37`'s channel tie and is filtered out of the colour
  set, or the sweep reports every grey-padded building in the region instead of the 100 that carry
  a panel. ⚠️ `facade_lab.json` is **not committed** — it is under `etl/sources/`, which is
  gitignored — so re-publishing it is a local act and `superseded/` is the only way back.
- Handling changes — `VehicleController`'s drive model, `HandlingProfile` or `handling.tres`: also
  `tools/skidpad.sh`, before **and** after, and paste both tables. It grades rather than checks, so
  `check.sh` cannot and should not run it. ⚠️ Run the **wrapper**, never `skidpad_ablation.gd`
  directly — Godot exits `0` on a parse error, so only the wrapper's exit code means anything.
  ⚠️ Measure on `skidpad.tscn`, never `city_drive.tscn` — a 0.14° micro-gradient there is worth the
  whole quantity under test, and a published figure has already had to be withdrawn over it
  (`P0-5b/c/d`).
- **`widen_default`, any `roads.surface` widening change, or anything that moves the pipeline's
  starved population — `ALONG_M` included: also `tools/narrowing.py`, before and after.** It is what
  priced the current value: narrowing clears *no* blocked edge at any factor down to the 1.3x floor
  and loses two — `e207` and `e595` (`Q19`). A change that does not re-run it is re-opening a
  question that has been measured shut. ⚠️ **The second trigger is the non-obvious one**: this tool
  imports `pipeline.clearance` whole, so its class split and refusal table are computed over the
  pipeline's own starved set and a resolution constant moves them without touching a width.
- **`clearance.py` or `carriageway_occupancy.py` changes: also `tools/clearance_reconcile.py`, and
  paste its table.** The pipeline publishes a number that tool grades, they disagree — 24 starved
  edges against 26 — and the gap is **reconciled** as plan cell size (`Q51`). The reconcile tool is
  the ratchet that keeps both figures describing the same bundle, and it fails when either count
  moves: a finding to go and look at, never a bar to retune. Add `--sweep` when the change touches a
  resolution constant — `ALONG_M`, `ACROSS_M`, `CELL_M`, `SUBDIVIDE_M`, `MAX_SUBDIVISIONS`,
  `INDEX_CELL_M` — because those are what the gap is made of.
  ✅ **`ALONG_M` is `CELL_M` since 2026-08-19, so the published clearance is a lower bound** at that
  cell and `is_routable` no longer routes traffic onto a wall. ⚠️ It is a bound at `CELL_M` and no
  finer — a diagonal edge can corner-cross a cell, which a 0.25 m walk catches and the shipped one
  does not. ⚠️ **`ALONG_M` is still shipped behaviour, not a tuning knob**: moving it re-publishes
  `city.json` and changes what routing refuses, so it is the user's call. Numbers in `Q51`.
  ⚠️ **`tools/narrowing.py` is owed too** — see the bullet above for why that is not obvious.
- **`widen_default`, `lanes_*`, `lane_width_m`, or the `carriageway_survey` config block: also
  `tools/carriageway_margin.py`, and paste its table.** It measures the drawn ribbon against the
  carriageway edge **two publishers actually print** — TD's `RM1108`/`RM1109`, then iB1000's `RM` —
  so its truth side is one no build reads, as `kerbside_source_audit.py`'s is. Unlike that one it
  shares no code with what it grades: the audit runs the pipeline's own join on a second source,
  this measures the shipped ribbon with neither. ⚠️ It **grades rather than checks** and exits 0
  whatever it finds; there is no bar, deliberately, and `Q19` records why.
  ⚠️ Quote the headline, not the two-source agreement: the headline is stable across
  the ray cap (p50 1.69 → 1.50 m from 10 to 25 m) and the agreement is not (p90 3.76 → 14.30 m over
  the same sweep). ⚠️ Its truth is a **2D projection carrying the publishers' own registration
  error**, which the bundle graders below do not inherit — that is the price of reading outside the
  bundle, not a defect to tune away.
- **`pipeline/kerbside.py`, the `NSR` config block, or any kerbside-marking change: also
  `tools/kerbside_error.py`, and paste its table.** It grades the shipped `roads.glb` against the runs
  `roadgraph.json` publishes, and it is the only instrument that can see the side convention flip —
  a mirrored city renders as a city. ⚠️ It **does not** grade the join itself: the truth side is what
  the pipeline published, so a restriction on the wrong centreline is agreed with rather than caught.
  What covers that is `etl/tests/test_kerbside.py`, which pins the side against `surface.mitres`
  rather than against a comment.
- **`painted_vehicle_types`, `kinds`, or anything that changes *which* restrictions are published:
  also `tools/kerbside_source_audit.py`, and paste its table.** It runs the pipeline's own join over
  the Traffic Aids Drawings — a second, independently digitised source of the same restrictions —
  and diffs the two answers. It is **the only instrument that can grade the kind**: every consumer
  takes double-versus-single on trust from `NSR.TIME_ZONE`, so a wrong mapping renders perfectly
  (`Q56`). ⚠️ It needs `traffic_aids_drawings_gdb`, a **218 MB** fetch no build reads; get it with
  `--only`. ⚠️ It grades rather than checks — a widening gap is a finding to go and look at, never a
  bar to retune against — and it **cannot** see the side convention flip, because that mirrors both
  sources at once.
- **`pipeline/tramway.py`, the `tramway` config block, or any tram-rail change: paste `tramway.json`'s
  `off_gauge_stations`, `pairs` vs `tracks`, and `inverted`, before and after.** There is no separate
  grader and there should not be: the stage grades itself, because the three ways this can break all
  render as **nothing** and none is visible in a frame. ⚠️ **The mis-pairing detector is
  `off_gauge_stations`, not `drawn_gauge_m`** — a bed drawn between two rails that are not a track
  renders perfectly and is a lane wide, but the trim rejects every one of its stations, so it shows
  up as rejected stations and as `pairs` exceeding `tracks`. `drawn_gauge_m` is bounded by
  `pair_tolerance_m` *by construction* and cannot read outside it; the p90 **1.92 m** and **4.62 m**
  that caught two shipped defects were measured before the trim existed. `inverted`
  must be **0**: `tramway.gdshader` is `cull_back`, so winding decides visibility and the normal
  attribute does not, and the first build had **5,111 of 5,112** triangles facing the ground with
  everything else correct. ⚠️ **A tramway change is also a shader change** — `check.sh` exits 0 on a
  shader that fails to compile, so render and `grep -i "shader error"`. Numbers in `Q58`.
- **`pipeline/railings.py`, the `railings` config block, or any railing change: paste, PER CLASS,
  `railings.json`'s `shift_m` (with its `n`), `samples_over_shift`, `metres_on_buried_kerb`,
  `metres_bridged` and `facing_away`, plus the shared `refused_m`, before and after — and run
  `tools/railing_error.py` and paste all three of its tables.** ⚠️ **Per class since `Q61`, and
  pooling them defeats the point**: the fence is 90% of the metres, so anything the two small
  classes did wrong disappears into its average. ⚠️ **The
  position of a railing is *registered*, not read** — the one place in the bundle a published extent
  is moved — because **67.9%** of the region's railing metres were surveyed inside the 1.6x ribbon
  (`Q60`). `shift_m` is the price of that and is recorded over the samples `max_shift_m` refuses, so
  **`n` must exceed what was drawn**; move that append below the guard and every percentile is
  confined to the bar by construction — `Q58`'s `drawn_gauge_m` trap, and the defect review caught in
  `arrows.py`. ⚠️ **`metres_bridged` is the one part of `drawn_m` the stage invents** — fence drawn
  across a gap the source never published, 322.88 m today — so a jump in it is `bridge_gap_m`
  reaching further, not more railing. ⚠️ **The metre counters do not form a partition**: the
  refusals live in two frames, published and ribbon, which is why `metres_dropped` is two fields. ⚠️ **A widening change is a railing change**: `widen_default` moves the drawn kerb and
  therefore moves every fence, silently and plausibly. ⚠️ `facing_away` must be **0** and
  `railings.gdshader` must stay `cull_disabled` — it is the only generated mesh that is, a fence is
  one quad thick, and `cull_back` would delete half of them with a byte-identical mesh.
  ⚠️ **`classes` is a whitelist read off code strings and nothing published defines them** — no
  index-plan sheet covers railings, and the layer's other 40 columns are cartography (`SYMBOL_SIZE_*`
  is plot inches, `COLOR` has no domain, `LINE_WIDTH_*` is null) — so a change to it is a
  `DATA_SOURCES.md` change and the refused metres are what makes it reviewable. ⚠️ **The split is by
  class of object and never within one**: five codes draw one fence, and keying a style to `CRAIL1`
  versus `HCAIL2` is `Q54`'s debit on the bundle's weakest-evidenced field.
  ⚠️ **A class is a parameterisation, not a shader** — all three share `railings.gdshader` and differ
  only in six mask numbers in their `.tres`, so a class handed the wrong `.tres` is a picket fence
  standing where a bollard should be and it renders perfectly. `verify_railings.gd` checks the
  dispatch per class; a new class needs a row there, in `generated_scene_import.gd` and in the config,
  and `check.sh` fails if the three disagree.
  ⚠️ **`ALPHA` is coverage, not translucency, and there must be no opacity dial** — the steel is
  opaque and the gaps are gaps. One would repeat `arrows.gdshader`'s recorded misreading of
  `paint_opacity`.
  ⚠️ **A railings change is also a shader change** —
  `check.sh` exits 0 on a shader that fails to compile, so render and `grep -i "shader error"`.
  Numbers in `Q60` and `Q61`.
- **`signs.faces`, `signs.colours`, any plate dimension, or `pipeline/signs.py`'s glyph geometry:
  also `tools/sign_face_survey.py`, and paste its two tables.** It rasterises the config's own face
  from `layer_polygons` and diffs it against the cell TD published that code in, as **area and
  extent per livery colour**. It is the only instrument that can see a face drawn in the wrong
  *proportions*, and on its first run it found five: `TS414` drawn in negative, `TS735` given the
  wrong border, `TS115`'s bar a quarter short, `TS116`'s ring a third thick, and every straight
  mandatory arrow 17% small (`Q67`). ⚠️ **Area alone is not enough and that is the point**: the
  shipped NO ENTRY bar and the published one have the same area to four points and are visibly
  different bars. ⚠️ It **grades rather than checks** and exits 0 whatever it finds — the truth side
  is a drawing whose corner radii and keylines this pipeline does not model. ⚠️ **It cannot see a
  face on the wrong CODE**, because it looks the config up by code and fetches that code's cell;
  `Q64`'s own defect would still be invisible. Run `--contact` and *look at the page* when the change
  touches which code draws what.
- **`text` layers, `text_cell_px`, `text_source`, or `pipeline/sign_text.py`: paste `signs.json`'s
  `text_plates`, `text_facing_away`, `text_atlas_px` and `text_coverage`, before and after** — and
  move `GeneratedSigns.TEXT_ATLAS_BUDGET_PX` in the same diff. 🔴 **This is the one place the bundle
  ships an image**, admitted by `Q63`'s declaration check rather than in spite of it, so a budget
  with slack in it is a metric nobody reads. ⚠️ **`text_coverage` is the detector**: a cell cropped
  off the lettering bakes paper, and a blank square on a plate renders as the blank plate it already
  was. ⚠️ `text_facing_away` must be **0** — a quad wound the wrong way under `cull_back` is not a
  backwards word, it is no word. ⚠️ **A lettering change is also a shader change** — `check.sh` exits
  0 on a shader that fails to compile, so render and `grep -i "shader error"`. Numbers in `Q68`.
- **`pipeline/arrows.py`, the `arrows` config block, or any turn-arrow change: paste `arrows.json`'s
  two partitions (`symbols` and `candidates`), `axis_residual_deg`, `offset_m`, `against_one_way` and
  `inverted`, before and after.** There is no separate grader and there should not be: the stage grades itself,
  because **every way this breaks renders as a perfectly drawn arrow, or as nothing**. An arrow on
  the wrong street, turned 180°, or drawn from a mis-transcribed glyph table all look correct in a
  frame. ⚠️ **The residual distributions publish p90/p99/max, not a median** — the tail is where a
  match to the wrong road goes, and a median near zero is also what a wholly broken join looks like.
  ⚠️ **`axis_residual_deg` is recorded over the symbols the stage *refuses* as well as the ones it
  keeps, and `n` exceeding `drawn` is how you tell.** Move that append below the guard and every
  percentile is confined to `bearing_tolerance_deg` by construction — it read max 28.87 against a
  30 deg bar for exactly that reason until review caught it. `Q58`'s `drawn_gauge_m` trap.
  ⚠️ `inverted` must be **0**: `arrows.gdshader` is `cull_back`, so winding decides visibility and
  the normal attribute does not. ⚠️ **The engine-side and ETL-side winding tests have opposite
  signs** — Godot winds front faces clockwise and glTF counter-clockwise — so do not "fix" one to
  agree with the other; `Q59` records how that was settled and against which meshes.
  ⚠️ **A glyph-table change is a `DATA_SOURCES.md` change**: the codes come from TD drawing
  `CT174/51-5(1)F`, a **scanned** sheet with no text layer, and reading the histogram instead would
  have painted 61 `RM1116`-`RM1119` *warning* arrows as turn instructions.
  ⚠️ **An arrows change is also a shader change** — `check.sh` exits 0 on a shader that fails to
  compile, so render and `grep -i "shader error"`. Numbers in `Q59`.
- **`pipeline/roadmarks.py`, the `road_marks` config block, or any stop / give-way line change:
  paste `roadmarks.json`'s two partitions, `host_disagreement` with `host_considered`,
  `axis_residual_deg`, `underfill_m` and `inverted`, before and after.** ⚠️ **`underfill_m` is
  measured against `roadsurface.json`'s DRAWN half-width, never the graph's authored `width_m`** —
  shipping the latter was an 18x error (p50 0.22 m against 4.04), and it is why this stage depends
  on `surface` as well as `roads`. There is no separate grader
  and there should not be: the stage grades itself, because every way this breaks renders as a
  perfectly drawn bar, or as nothing. 🔴 **`host_disagreement` is the load-bearing counter and
  `axis_residual_deg` is not** — the residual grades a rule that *optimises the thing it reports*,
  which is `Q58`'s `drawn_gauge_m` trap for the third time. The disagreement count is how often the
  transverse pick and the plain nearest edge choose different hosts, **90 of 209** today, and a fall
  towards zero means the pick has stopped picking. ⚠️ **This is the one stage that does NOT host by
  nearest edge, and that is not a bug to tidy away**: a stop line sits at a junction mouth, so
  proximity picks the road it is parallel to on 43% of the layer (`Q69`). ⚠️ **`axis_residual_deg`
  is recorded over refusals as well as keeps, and `n` exceeding `drawn` is how you tell** — move
  that append below the guard and every percentile is confined to `bearing_tolerance_deg` by
  construction, the defect review caught in `arrows.py`. ⚠️ **`inverted` must be 0** —
  `roadmarks.gdshader` is `cull_back`, so winding decides visibility and the normal attribute does
  not; and the engine-side and ETL-side winding tests have **opposite signs** (`Q59`), so do not
  "fix" one to agree with the other. ⚠️ **A dimension change is a `DATA_SOURCES.md` change**: every
  width, count, gap and dash module comes from TD drawing `CT174/51-5(1)F`, a **scanned** sheet with
  no text layer, so `Q59`'s by-eye rule applies and `Q67`'s rasterise-and-diff cannot help. And
  ⚠️ **`LINES SPACING` is the clear gap, not a centre-to-centre pitch** — the pitch reading draws
  every double marking at twice the weight and renders perfectly. ⚠️ **A roadmarks change is also a
  shader change** — `check.sh` exits 0 on a shader that fails to compile, so render and
  `grep -i "shader error"`. Numbers in `Q69`.
- Road-surface, deck-height or ground changes: also `tools/deck_error.py`, `tools/overhang.py`,
  `tools/ground_clearance.py` and `tools/carriageway_occupancy.py`, by hand after a build. They grade
  the *shipped* bundle and share no code with the pipeline — `check.sh` does not require a built
  region and should not start requiring one. Moving the road moves what `ground_clearance.py`
  measures, so it is not only a ground check — and **widening, building footprints and landmark
  placement move `carriageway_occupancy.py`'s answer** without touching the road at all, so that one
  is owed for those too. It gates per *edge*, because `RoadGraph` routes on edges. ⚠️ It **fails
  today**; read the exit code rather than the table, and see `PROGRESS.md` for what it is failing on.
- Update `docs/PROGRESS.md` — task status, metrics, risks, and the open-questions index.
- Record any new decision, or any question that closes, in `docs/DECISIONS.md`, keyed by its ID.
- **Bundle size is measured from a PCK, never summed from source files.** That rule has been wrong
  in both directions once each.

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
