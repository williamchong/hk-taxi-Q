# hk-taxi-Q — Agent Instructions

Arcade taxi game set in Hong Kong, built from HK government open geodata.

**Read `docs/` before starting any task.** These decisions are settled — do not re-litigate
them without explicit instruction from the user.

## Locked decisions

| Decision | Value | Why |
|---|---|---|
| Engine | **Godot 4.7**, Mobile renderer | Commercial mobile app target; native perf; MIT, no royalties |
| Physics | **Jolt** (Godot default since 4.4), driving `VehicleBody3D` | Stable trimesh collision under the vehicle. ⚠️ **`Q50` reversed `P0-5a` on the user's explicit instruction (2026-08-18).** The car was a custom raycast controller until then, because `VehicleWheel3D` friction is isotropic and so cannot express a drift that breaks lateral grip while keeping traction. That is still true, and the way it was re-measured was wrong. ⚠️ **`Q84` corrected it**: the drift window is *not* 0.01–0.02 wide and `drift_slip_threshold_deg`'s 14° *is* reachable, at `drift_rear_grip_scale` **0.6695** — the cliff was a 0.02 sweep grid read through a `%.2f` label that could not resolve its own step. What survives is the cost, restated: peak slip and *dwell* pull opposite ways against speed, so 0.6695 holds 14° for **0.05 s** where the shipped 0.66 holds it for **0.57 s**, and landing the peak on the threshold is the wrong aim. The engine model ships anyway; `docs/DECISIONS.md` `Q50` and `Q84` are the record |
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
  🔴 **The drift dials are graded on OPPOSITE columns and there is no single rule for "the drift".**
  `drift_rear_grip_scale` is graded on `secs>thr` and never on `peak slip`, because the game pays per
  second above the threshold (`Q84`). The three yaw dials — `drift_yaw_torque_nm`, `drift_yaw_decay_s`,
  `drift_yaw_sustain` — are graded on **peak slip and exit speed**, and never on `secs>thr`, because
  that column was flat at 0.78–0.85 across all three of them while peak ran 40° → 130° (`Q86`). Tuning
  a yaw dial against dwell is tuning against a number it cannot move.
  ⚠️ **And the skidpad cannot settle a yaw value on its own — drive it too.** An open pad has no far
  kerb, so 65.7° of peak slip reads as a healthy angle there and is `086° → 219°` and a railing across
  the carriageway on Expo Drive. That is what rejected 9000 N⋅m (`Q86`). It is not a licence to
  *measure* in `city_drive.tscn`; the numbers still come from the pad and the drive is a veto.
  ⚠️ **Sweep with `tools/skidpad.sh --sweep=<field>=<v,…>`, not by editing `handling.tres` in a shell
  loop.** One such loop blanked the field it was sweeping and published a table of all-zero rows that
  read like a finding; the flag exists so that cannot happen again.
  🔴 **Grade anything speed-dependent at more than one `--run-up`, because the default entry speed is
  the tool's blind spot.** A fixed 63 kph entry is what makes every other column comparable across
  rows, and it is also why a yaw assist tuned at 63 and applied at 84 spun the car for a whole
  release with a green `check.sh` and five clean rows (`Q87`). 4 s → 63.02 kph, 6 s → 86.36, 8 s →
  105.47; rows compare only *within* one run-up, so quote `entry kph`.
  ⚠️ **The drift withdraws with speed and there are TWO envelopes, sharing a knee and not a top.**
  `drift_fade_from_kph` (65) is where both begin; the yaw is fully spent at `drift_yaw_fade_to_kph`
  (85), while `drift_rear_grip_scale` interpolates toward `drift_rear_grip_scale_at_top` all the way
  to `max_speed_kph`, because the grip value the car wants **moves** with speed (`Q88`). Above about
  100 kph the button is deliberately **inert**, which is the safe side of a cliff, not a bug.
  🔴 **A static sweep of a speed-dependent grip dial gives an upper bound on a fix, never an
  estimate.** Held constant, 0.710 reads 44.9° at 105 kph; reached via the taper at that same entry
  speed it read **159.4°**, because the car decelerates below the knee inside the drift and the cut
  deepens underneath it. Sweep the taper dial itself (`Q88`).
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
  opaque and the gaps are gaps. One would repeat `marking_paint.gdshader`'s recorded misreading of
  `paint_opacity`.
  ⚠️ **A railings change is also a shader change** —
  `check.sh` exits 0 on a shader that fails to compile, so render and `grep -i "shader error"`.
  Numbers in `Q60` and `Q61`.
- **`signs.outset_m`, `max_shift_m`, or `signs._register`: paste `signs.json`'s `drawn`,
  `poles_drawn`, `posts_kept_as_surveyed`, `posts_over_shift`, `posts_in_carriageway`,
  `posts_merged_after_shift` and `shift_m`, before and after — and A/B render one street that
  carries kept posts.** 🔴 **`shift_m` is an absolute value, so it CANNOT report the direction of
  the move it measures.** That is what let the registration pull 95 of 654 posts *toward* the
  carriageway — a correction whose stated reason runs outward only — through three published
  distributions and a green `check.sh` (`Q78`). ⚠️ **`drawn` is the invariant, NOT `poles_drawn`**:
  a post left where it was surveyed keeps its separation from its neighbour, so
  `posts_merged_after_shift` can only fall and `poles_drawn` rises by exactly what it stops folding
  away. A stop-condition on `poles_drawn` halts a correct build. ⚠️ **The identity must still
  close** — `len(shift_m) == poles_drawn + posts_over_shift + posts_in_carriageway +
  posts_merged_after_shift` — which is why a post that does not move appends a real `0.0` rather
  than being skipped. ⚠️ **A position on this layer cannot be graded against anything published**
  (`Q62`), so the evidence is an **A/B render at one fixed camera** — `city_preview.tscn` with an
  explicit `--camera`/`--look`, never a driven frame, and shoot each side twice and `cmp` them.
  ⚠️ **`railings.py` and `signals.py` compute `shift_m` the same way and are deliberately NOT
  aligned**: a fence is a run and the bar is per sample, so a conditional push would zigzag it. Do
  not "restore consistency". ⚠️ **A widening change is a sign-position change** — `widen_default`
  moves the drawn kerb and therefore moves every post, silently and plausibly. Numbers in `Q78`.
- **`signs.faces_against_traffic`, `_facing_from_side` or `_plate_facing_deg`: paste `signs.json`'s
  `plates_turned`, `no_entry_against_flow`, `no_entry_on_two_way` and `facing_away`, before and
  after — and mutation-check the flag by turning it off and confirming the counters move.** 🔴 **The
  counter that stood here before `Q72` was a tautology that certified the wrong state**: every NO
  ENTRY in the region faced the traffic it was not addressing while `no_entry_with_flow` read 0,
  because the rule turned every one-way sign to face its traffic and 0 was unreachable. The test of
  a counter here is not whether it reads 0 but whether **any reachable configuration makes it
  non-zero**. ⚠️ **`no_entry_against_flow` is a config-and-code ratchet and NOT data-sensitive** —
  no readable input moves it, only dropping the flag or the turn does — so mutate it rather than
  reading its 0, and do not describe it as grading the city. ⚠️ **`plates_turned` must equal the drawn NO ENTRY family exactly** (197 = `TS115` 179
  + `TS116` 18); a fall means the turn stopped happening, and a turn that stops renders perfectly.
  ⚠️ **Which faces turn is config, never a code constant** — a second face quietly gaining the flag
  rotates a whole code across the region and renders perfectly (`Q64`'s class).
  ⚠️ **A facing change cannot be graded against anything published** (`Q62`), so the evidence is an
  **A/B render at one camera**, before and after. Numbers in `Q72`.
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
  🔴 **The atlas ships as its own file, `signs_text.png`, named by `city.json` under
  `signs_text_atlas` — never embedded in `signs.glb`, and that is not a style preference** (`Q70`).
  Godot's `gltf/embedded_image_handling` defaults to *Extract Textures*, so an embedded image
  becomes a PNG beside the asset that the manifest has never heard of, and `sync_generated.sh`
  deletes exactly that — on every run, leaving `verify_signs` red until someone forces a re-import
  by hand. ⚠️ **Anything that adds a second image owes the same treatment**: name it in the
  manifest, or the sweep is right to delete it. ⚠️ **`signs.json`'s `bytes` is `signs.glb` alone**
  and `text_atlas_bytes` is the image — two numbers where there was one.
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
  ⚠️ `inverted` must be **0**: `marking_paint.gdshader` is `cull_back`, so winding decides visibility and
  the normal attribute does not. ⚠️ **The engine-side and ETL-side winding tests have opposite
  signs** — Godot winds front faces clockwise and glTF counter-clockwise — so do not "fix" one to
  agree with the other; `Q59` records how that was settled and against which meshes.
  ⚠️ **A glyph-table change is a `DATA_SOURCES.md` change**: the codes come from TD drawing
  `CT174/51-5(1)F`, a **scanned** sheet with no text layer, and reading the histogram instead would
  have painted 61 `RM1116`-`RM1119` *warning* arrows as turn instructions.
  ⚠️ **An arrows change is also a shader change** — `check.sh` exits 0 on a shader that fails to
  compile, so render and `grep -i "shader error"`. Numbers in `Q59`.
  🔴 **And a shader change is a change to THREE layers**: `marking_paint.gdshader` is shared by the
  arrows, the box junctions and the stop lines since `Q71`, on `railings.gdshader`'s precedent — a
  layer is a parameterisation, not a shader, and the colour lives in each `.tres`. So render and
  look at all three, not just the one you changed. ⚠️ The per-layer dispatch is still checked:
  `check_shader_material` compares the material's `resource_path`, not the shader, so a mesh handed
  the wrong `.tres` still fails — do not reach for `check_shader_source` to quiet it.
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
  `marking_paint.gdshader` is `cull_back`, so winding decides visibility and the normal attribute does
  not; and the engine-side and ETL-side winding tests have **opposite signs** (`Q59`), so do not
  "fix" one to agree with the other. ⚠️ **A dimension change is a `DATA_SOURCES.md` change**: every
  width, count, gap and dash module comes from TD drawing `CT174/51-5(1)F`, a **scanned** sheet with
  no text layer, so `Q59`'s by-eye rule applies and `Q67`'s rasterise-and-diff cannot help. And
  ⚠️ **`LINES SPACING` is the clear gap, not a centre-to-centre pitch** — the pitch reading draws
  every double marking at twice the weight and renders perfectly. ⚠️ **A roadmarks change is also a
  shader change, and its shader is shared with the arrows and the boxes** (`Q71`) — `check.sh` exits
  0 on a shader that fails to compile, so render and `grep -i "shader error"`, and look at all three
  layers rather than only this one. Numbers in `Q69`.
- 🚫 **`P3-17`'s signal layer is NOT SHIPPED** (`Q77`): `hong_kong.yaml` declares no `signals:`
  block, so nothing below applies until one is declared again. Kept because re-declaring the block
  is the whole of the work to bring it back. **`pipeline/signals.py`, the `signals` config block, or any signal-head change: paste
  `signals.json`'s two partitions, `drawn_by_code` **and** `refused_by_code`, `assembly_size`,
  `axis_residual_deg`, `shift_m` (with its `n`), `host_ambiguous` and `facing_away`, before and
  after.** There is no separate grader and there should not be: the stage grades itself, because
  every way this breaks renders as a perfectly drawn signal head or as nothing.
  🔴 **`refused_by_code` is load-bearing, not decoration.** `REFNAME` has **no published domain** —
  no index-plan sheet defines it, the fgdb spec gives it 8 untyped characters, and
  `signCatalogue.json` is `TS`-only — so what admits a code is a rule about *spelling* this project
  wrote, and publishing both halves of the vocabulary is the only thing that can grade it. A change
  to `head_prefixes` or `refuse_codes` is a **`DATA_SOURCES.md` change** (`railings.py`'s `classes`,
  at a second layer). ⚠️ **`drawn` counts FEATURES and `posts_drawn` counts HEADS** — one head stands
  for a whole assembly — so do not quote one as the other.
  🔴 **`assembly_size` is the counter that would have caught the defect that shipped.** This layer
  publishes no `GG_NAME`, so a post is a cluster of coincident points; the first build stacked them
  and drew **8.53 m** five-head masts while both partitions closed, `facing_away` read 0 and
  `check.sh` was green. It was caught by *looking*, which is why the render below is not optional.
  ⚠️ **A facing change cannot be graded against anything published** (`Q62`), so the evidence is an
  **A/B render at one camera** — shoot one head from the front and from the back, and the aspects
  must appear only from the front. ⚠️ **`facing_away` must be 0** and ⚠️ **a signals change is also
  a shader change** — but `signs.gdshader` is **shared with the signs** since `P3-17`, so render and
  look at **both** layers, and `grep -i "shader error"` because `check.sh` exits 0 on a shader that
  fails to compile. ⚠️ **`sheeting_glow` must stay 0**: any glow makes an unlit lens read as a lit
  one, which is an instruction this game refuses to give. Numbers in `Q76`.
- Road-surface, deck-height or ground changes: also `tools/deck_error.py`, `tools/overhang.py`,
  `tools/ground_clearance.py` and `tools/carriageway_occupancy.py`, by hand after a build. They grade
  the *shipped* bundle and share no code with the pipeline — `check.sh` does not require a built
  region and should not start requiring one. Moving the road moves what `ground_clearance.py`
  measures, so it is not only a ground check — and **widening, building footprints and landmark
  placement move `carriageway_occupancy.py`'s answer** without touching the road at all, so that one
  is owed for those too. It gates per *edge*, because `RoadGraph` routes on edges. ⚠️ It **fails
  today**; read the exit code rather than the table, and see `PROGRESS.md` for what it is failing on.
- **HUD changes — `hud.gd`, `hud_layout.tres`, `hud_style.tres`, `chamfer_panel.gd` or
  `street_tracker.gd`: `tools/check.sh` (which runs `verify_hud`), plus an A/B render at one camera
  with `--debug-view=off --hud=off` and again with the HUD on, and the draw-call delta pasted.**
  ⚠️ **A clean art-review frame needs BOTH `--debug-view=off` and `--hud=off`** — the player's HUD is
  not dev chrome and the first flag does not touch it. ⚠️ **`verify_hud` sees no frame**: two defects
  here shipped past a green `check.sh` and were caught by looking — a safe-area inset measured
  against the window instead of the screen, which pushed the whole HUD off its own edges and logged
  nothing, and a `--hud=off` crash from `queue_free()` being deferred while `_process` ran once more
  (Godot exits **0** on a script error). ⚠️ **A layout change is a `P2-4` change**: `hud_layout.tres`
  is where the touch geometry lives, and 🔴 **`touch_steer_*` and `thumb_rest_*` are not
  interchangeable** — the HUD may overlap a tap zone and may not overlap a thumb, and the check
  asserts **both** directions so that "tightening" it back onto zones fails rather than silently
  banning the corners every shipped reference uses (`Q80`).
- **Wrong-way changes — `wrong_way_monitor.gd`, `no_entry_icon.gd`, or the `warn_*` keys in
  `hud_style.tres`: `tools/check.sh` (which runs the 23 `way:` assertions), plus a drive that
  actually goes the wrong way, and the draw-call delta pasted.** 🔴 **The nose raises the sign and
  the velocity may only withhold it, and that asymmetry is the user's call, not a detail to
  "restore consistency" on** — reversing while pointed the legal way is not wrong-way, because
  NO ENTRY's instruction is *turn around*. Built the other way round first, and the taxi does
  40 kph backwards, so the speed floor did not save it (`Q81`). ⚠️ **A miss CLEARS here where
  `street_tracker.gd` HOLDS** — a stale street name is honest, a latched siren is not — so do not
  align the two. ⚠️ **The false alarm is the failure mode, not the missed alarm**: the region is
  **93.5% one-way by drivable length**, so the dwells and the **120°** bar are load-bearing and a
  bar at 90 rings on every legal turn across a one-way street. ⚠️ **`warn_bar_length` and
  `warn_bar_thickness` are the WORLD sign's numbers** — `hong_kong.yaml`'s `TS115` and
  `signs.py::_NO_ENTRY_BAR_THICKNESS`, measured by `Q67` — and `verify_hud` is the ratchet, so a
  change there is a change to the sign on the pole or it is a defect. ⚠️ **`warn_blink_hz` is capped
  at 3 Hz on WCAG 2.3.1** and asserted, not commented. ⚠️ **The evidence is a frame**: Wan Chai is
  dual-carriageway near the start line, so drifting across simply makes you legal — the route that
  works is the user's, `--hold=accelerate@0.3+12.7 --hold=steer_right@4.6+1.3`, right out of HKCEC
  and straight down Expo Drive East's northbound carriageway (`e660`). ⚠️ **`DEFAULT_ANGLE_DEG` and
  `CORRECTING_ANGLE_DEG` are two bars and must not be re-merged** — the nose bar decides, the
  withholding bar is the neutral 90, and reusing one number let a car pointed backwards *while
  drifting sideways* read as already correcting. 🔴 **`verify_hud` can print `ok` having checked
  NOTHING**: a `preload`ed script that fails to compile makes `new()` abort the calling function, so
  every assertion is skipped and `_failed` stays 0 — only `check.sh`'s `SCRIPT ERROR` grep catches
  it, which is why its exit code is the only thing that means anything. ⚠️ **Do not force the sign
  visible with `if false:`** — the promoted-warnings sweep rejects the file, the HUD never builds,
  and the run still says `DRIVER OK`. Numbers in `Q81`.
- **`pipeline/lamps.py`, the `lamps` config block, or any lamp-post change: paste `lamps.json`'s two
  partitions, `min_kerb_clearance_m`, `shift_m` (with its `n`), `lantern_overhang_m`,
  `lanterns_past_centreline`, `spacing_surveyed_m` vs `spacing_drawn_m`, `gaps_over_report_m` and
  `facing_away`, before and after — and A/B render one street at a fixed camera.** There is no
  separate grader and there should not be: the stage grades itself, because every way this breaks
  renders as a perfectly drawn lamp post or as nothing.
  🔴 **`min_kerb_clearance_m` is the invariant the user asked for — no column stands in the road —
  and it comes from TWO refusals, not from `max_shift_m`.** `_register` clears a column's own host
  kerb; a second pass re-snaps the *placed* point against every edge and refuses it where 1.6x
  ribbons overlap. Deleting that pass leaves both partitions closing, `facing_away` at 0 and
  `check.sh` green, with columns standing in junction mouths. It is **not** a tautology: a foot
  reconstructed from `offset_m` rather than read off the polyline drives it negative (`signs.py`'s
  recorded 10.6 m defect). ⚠️ **Do not "fix" it by iterating the push** — measured on the SIGNS
  and cited as precedent, not measured here: 9.7% plateau, worst shift 5.52 → 16.77 m (`Q78`), where
  this layer's own `shift_m` max is 6.7329. The lamps sweep was never run and the argument is
  borrowed; say so rather than quoting another layer's numbers as this one's.
  🔴 **There must be NO `arms_against_kerb` counter.** The arm direction is derived from the kerb
  side, so such a counter reads 0 by construction — `Q72`'s tautology, which certified a whole
  region's signs as correct while every one faced the wrong way. `lantern_overhang_m` and
  `lanterns_past_centreline` are what ship, and the second is reachable by raising `arm_reach_m`,
  which is the test a counter here has to pass. The facing itself **cannot** be graded against
  anything published (`Q62`) — the evidence is an A/B render at one fixed camera, shot twice and
  `cmp`'d.
  🔴 **The prism ring is NOT reversed here, and `signs._draw_pole`/`signals._draw_post` both reverse
  theirs.** Both of those carry a paragraph calling the reversal "the whole correctness of this
  function" and both are right about their own frame; `lamps._strut` builds an explicit one with
  `u x v == axis`, because a bracket arm is not vertical. Inheriting their fix inverted **25,116 of
  35,880** triangles. Do not "restore consistency".
  ⚠️ **`shift_m` is recorded over refusals as well as keeps, and `n` exceeding `drawn` is how you
  tell** (`Q58`'s trap); `Q78`'s outward-only clamp applies here and deliberately **not** in
  `railings.py`/`signals.py` — a fence is a run, a lamp post is not.
  ⚠️ **A widening change is a lamp-position change**: `widen_default` moves the drawn kerb and
  therefore moves every column, silently and plausibly.
  ⚠️ **The spacing pair is this layer's own failure mode and no other layer here has it** — a lamp
  row's regularity *is* its content, so a refusal is a hole where a missing sign is invisible. Quote
  both distributions; the *difference* is the finding.
  ⚠️ **The colour is in `materials:` and answers to `Q33`** — `signs.colours`' exemption does not
  transfer, because a lamp post is not a printed specification and is one colour. ⚠️ **A lamps change
  is also a shader change, and its shader is shared with the signs and the signals** — `check.sh`
  exits 0 on a shader that fails to compile, so render and `grep -i "shader error"`, and look at all
  three layers. 🔴 **Do not light the lantern**: `Q38` bakes the exposure at build time and `Q26` has
  not chosen a look, so a glow here is wrong in every frame the project renders.
  ⚠️ **`verify_lamps.gd`'s upright bar grades the IMPORTED mesh, and the two used to differ.** Godot
  quantises imported vertex positions over each mesh's **own AABB**, so the step scales with how wide
  a layer is rather than how big its objects are — 0.025 m across `lamps.glb`'s 1,646 m, against a
  0.06 m bracket arm and `signs.glb`'s 0.032 m poles. It read 18,484 upright against the ETL's exact
  17,940 until `Q82` turned compression off project-wide, at **+958,720 B (+2.002%)** of PCK and **+3.19 MiB** of GPU buffer, with **0** extra draw calls or primitives. 🔴 **It
  is `[importer_defaults]` in `project.godot` and `check.sh`'s `settings` step pins its value**,
  because `game/assets/generated/` is gitignored and a per-asset `.import` does not survive a clone.
  An editor save drops it silently and every generated mesh then imports geometry the ETL did not
  build. 🔴 **And `[importer_defaults]` seeds only a NEW `.import`** — changing the key does not
  migrate assets that already have a sidecar, and `check.sh` cannot see a stale one. Delete the
  sidecars and re-import, then re-measure. Do not "tighten" the bar toward a measured value either — it is a lay-flat detector.
  Numbers in `Q82`.
- **Street-name or font changes — `street_plate.json`, the bundled typeface, or any new region:
  also `tools/font_coverage.py --city <c> --region <r>`.** It exits non-zero on a character that is in neither the font nor the
  display substitution table, which is the only thing standing between a data refresh and a tofu box
  on one street's plate. ⚠️ **Substitutions are a DISPLAY fix and `roadgraph.json` is never edited**
  — a street's name is the strongest case of `Q54`'s sourced-not-invented rule. ⚠️ The bundled font
  is the **fourth** licence in a repo whose hard rule 7 says three; `LICENSING.md` and the credits
  screen both carry it (`Q79`).
- Update `docs/PROGRESS.md` — task status, metrics, risks, and the questions index.
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
