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
| Building source | **3D Visualisation Map (non-textured)** + **iB1000** for podium floors, tram rails and lamp posts | Already flat-shaded extruded volumes — the low-poly look is native to this data. ⚠️ **3D-BIT00 Level 1 was named here and never fetched** — iB1000, the map it is extruded from, took its place at `P3-7a`/`Q47` (`Q100`) |
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
   `etl/config/hong_kong.yaml` for anything that is tuning or a publisher's vocabulary (that is hard
   rule 4 — codes, `fields:` role maps, bounds, `elevation_levels`), and `etl/pipeline/hongkong.py`
   for the handful of constants that *are* the city (the CRS pair, drive-on-the-left, the branch
   sign codes). Never a second copy of either. Multi-**region** support stays (`Q6`, `Q10`); there
   is no second city and no `--city` flag. ⚠️ Records before `Q100` cite "the second city" as a
   reason — each stands on its other reason.
4. **All tuning values are data**, not constants in code. Handling curves, fare timers, road
   widths → Godot `.tres` resources or JSON.
   🔴 **The carriageway width is DATA in a second sense since `Q95`: it is measured, not authored.**
   `roadgraph.json`'s `width_m` comes from what TD, iB1000 and HyD drew on 292 of 737 level-0 edges, and
   the playability widening is a **floor** (`surface.floor_default_m`, 10.24 m) rather than a
   multiplier — `drawn = max(width_m, floor)`. A multiplier over-widens the streets that are already
   wide. ⚠️ **`width_m != lanes x lane_width_m` any more**; `width_source` says which an edge carries.
   🔴 **And `lanes` is measured too since `Q94`** — bracketed off that width against TPDM 4.3.9.8's
   3.0-3.65 m through lane, **never** divided by `lane_width_m`, which would make the instrument
   agree with the constant under test. It resolves on **210 of the 292** measured edges (96
   `measured`, 57 `floored`, 57 `arrows`); the rest are ambiguous and keep the authored count, and
   `lanes_source` says which. ⚠️ **A lane count moves no geometry** — the ribbon is `max(width_m, floor)` — so it
   changes the `TEXCOORD_0` lane coordinate and the arrow slots, and nothing else.
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
  ⚠️ **There is a THIRD envelope below the knee** — `drift_rear_grip_scale_at_low` /
  `drift_low_fade_kph` (`Q89`) — which deepens the cut as speed falls, because down there the tyre
  never saturates and the drift was inert. The usable band is now **34–86 kph**.
  🔴 **The low branch LATCHES at engagement and the high branch TRACKS, and that asymmetry must not
  be "made consistent".** A drift scrubs speed, so deepening the cut as speed falls is positive
  feedback — built as a tracking taper first, it turned the design speed into a **165.0° spin**.
  Above the knee the same tracking is stabilising, because losing speed returns the scale to the
  tuned base. Latching *both* costs the high end (86 kph 50.4° → 20.6°).
  🔴 **The yaw assist cannot substitute for the grip cut at low speed**: at 42 kph peak slip *falls*
  4.2° → 3.6° as torque goes 0 → 20000 N⋅m, the top of its range, because with grip unbroken the
  rotation becomes a tighter line rather than a slide. Do not reach for a torque dial down there.
  **Grade a drift change at a low `--run-up` as well as a high one** — three consecutive changes
  checked "design speed byte-identical" without once asking what happens beneath it (`Q88`).
  🔴 **A static sweep of a speed-dependent grip dial gives an upper bound on a fix, never an
  estimate.** Held constant, 0.710 reads 44.9° at 105 kph; reached via the taper at that same entry
  speed it read **159.4°**, because the car decelerates below the knee inside the drift and the cut
  deepens underneath it. Sweep the taper dial itself (`Q88`).
- **`surface.floor_default_m`, any `roads.surface` widening change, or anything that moves the pipeline's
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
- 🔴 **`carriageway_survey.edges` is THREE publishers since `Q94`, and the third is an AREA.** TD's
  painted edge and iB1000's margin are lines; HyD's Pavement Polygon draws the maintained carriageway
  as polygons, so `geometry: area` and `_union_boundary` — HyD tiles the region into **552** of them
  and a seam between two is not a kerb. ⚠️ **Preference order is load-bearing**: third, it adds 33
  edges and refines 50 without overriding a station the lines answered; **second, it re-baselines
  every published width**. ⚠️ **"Third" still does not mean "only where they are silent"** — the loop
  runs per station. ⚠️ It arrives via `paged_sources`, the third source kind, at **~163 MB on every
  clone** — second only to the 218 MB Traffic Aids geodatabase among sources a build reads.
- **`surface.floor_*`, `lanes_*`, `lane_width_m`, the `carriageway_survey` config block, or
  `pipeline/carriageway.py`: also
  `tools/carriageway_margin.py`, and paste its table.** It measures the drawn ribbon against the
  carriageway edge **two publishers actually print** — TD's `RM1108`/`RM1109`, then iB1000's `RM` —
  so its truth side is one no build reads, as `kerbside_source_audit.py`'s is. Unlike that one it
  shares no code with what it grades: the audit runs the pipeline's own join on a second source,
  this measures the shipped ribbon with neither. ⚠️ It **grades rather than checks** and exits 0
  whatever it finds; there is no bar, deliberately, and `Q19` records why.
  ⚠️ Quote the headline, not the two-source agreement: the headline is stable across
  the ray cap (p50 1.69 → 1.50 m from 10 to 25 m) and the agreement is not (p90 3.76 → 14.30 m over
  the same sweep).
  🔴 **It also publishes a per-edge SPAN since `Q95`, and that is a second table with different
  rules — paste both.** ⚠️ **The span is cap-sensitive where the overhang headline is not**, so quote
  its cap: coverage 54.7 → 81.8% and non-junction p50 7.40 → 9.15 m from 10 to 25 m. ✅ It saturates
  at the 15 m default — kept spans peak there at 8,204 and *fall* to 8,162 by 25 m — which is why
  there is one cap and not two. 🔴 **On a one-way edge the number is a KERB-TO-KERB SPAN and not a
  carriageway width** wherever the ray crosses an opposed pair; the TPDM ceiling cannot see that and
  `off_centre` is what does. The two coincide on 34 edges.
  🔴 **There is a THIRD table since the split, and it has different rules again — paste all four.**
  It pairs each one-way edge with its opposed partner and reports `own = 2 x near` per half with the
  leftover as the median. ⚠️ **Do not pool it into the span line**: that is `Q57`'s generalisation,
  a property established on one population and quoted for another. 🔴 **The load-bearing counter is
  the NEGATIVE residual, not the pairing count** — the parts exceeding the whole cannot be true, so
  it is the split refusing itself, and it reads **96 of 110** mutual pairs today because on most of
  the network *the ray never crossed the median at all*. All three LOCKHART ROAD pairs land there.
  A fall towards zero is a finding to go and look at, never a bar to retune.
  ⚠️ **"621 of 737 run as opposed pairs" was half asserted and is corrected**: 621 are one-way, and
  **110 of 352** with a median pair mutually. Only **14** decompose to a width.
  🔴 **The six shared-endpoint pairs in `surface.py` are the only ground truth for a pairing rule and
  cost nothing to check — check them.** Capping the partner search at the station's own far ray
  sounded principled and missed all three Lockhart pairs, whose partner centreline is 6.82 m away
  behind a far ray that stops at 3.5 m. The cap is `--max-ray-m`, the tool's own; 5 of 6 recover and
  the sixth is 9.0 m with no station clear of a node. ⚠️ **`--pair-bearing-deg` is the rule's one free
  value, so sweep it and paste the table** — `Q72` rejected a divider test whose count ran
  8 → 29 → 49 → 80 over a free radius, and this one is flat at 14 decomposed from 10° to 75°.
  🔴 **And a FOURTH since the crossing rule, which is the one that publishes WIDTHS — 276 of 387
  edges.** `beyond = span - 2 x near ray` is the room an opposed carriageway would need; under
  `hard_min_m` there is none, so the span *is* that edge's carriageway. ⚠️ **Three states, and the
  middle one publishes nothing on purpose** — TONNOCHY `e142` sits in it, and a single threshold in
  that gap ships a 16.7 m span as a width. ⚠️ **`carriageway_m` is not one population**: a decomposed
  row publishes half a span and every other row publishes the whole of one, so quote the `basis`
  column with it or it is `Q57`'s generalisation again.
  🔴 **`--dual-min-m` classifies and licenses NOTHING, so do not read its sweep as a plateau.**
  Over 3.0 → 14.6 the crossed count runs 79 → 0 while uncrossed and licensed stay flat at 230 and
  276 — that bound only moves rows between two states that both publish nothing, and every width
  rests on `hard_min_m` instead. Sweep it anyway; a *moving* licensed count means the states have
  stopped meaning what they say. ✅ **The width is cap-insensitive where the span is not** (p50
  7.15-7.18 m over a 10-25 m ray sweep), so quote the cap for the span line and not for this one.
  ⚠️ **The pairs' residual cross-checks this for free and its misses are about the PAIRING** — 12 of
  14 are rows whose partner claims an impossible half. A finding, never a bar to retune.
  ⚠️ `--json` writes `carriageway_width.json` under `etl/out/`, which is **gitignored** — a local act
  like `facade_lab.json`, and re-running is the only way back.
  🔴 **Lanes are a bracket from TPDM 4.3.9.8 (3.0-3.65 m) and never a division by `lane_width_m`** —
  dividing by the authored 3.2 makes the instrument agree with the value under test. ⚠️ **The bounds
  are config, not constants** (`carriageway_survey.width_bounds`), and the tool refuses to start
  unless `2 × max_ray_m` exceeds the ceiling — otherwise the cap manufactures a clean sweep, which is
  `Q58`'s `drawn_gauge_m` trap reachable from the command line. ⚠️ Its truth is a **2D projection carrying the publishers' own registration
  error**, which the bundle graders below do not inherit — that is the price of reading outside the
  bundle, not a defect to tune away.
- **`pipeline/carriageway.py`, the `carriageway_survey` block, or anything that moves `width_m`:
  paste the roads stage's `carriageway:` two lines before and after, run `tools/carriageway_margin.py`
  and paste all four of its tables, and run EVERY grader in the widening bullet above.** 🔴 **This
  stage is a SECOND implementation of the survey that tool performs and the duplication is
  deliberate** — the tool "shares no code with what it grades", and sharing a core to save six
  hundred lines would retire the only independent check on the reading. **They are expected to agree
  and a divergence is a finding**: today `|pipeline − tool|` is p50 **0.005 m** over the 259 edges
  both license, and the tool's own `measured − authored` line reads p50 **+0.00**. A drift there is
  the thing to go and look at. ⚠️ **Do not "fix" it by importing one into the other.**
  ⚠️ **The widths may never be read from `carriageway_width.json`** — it is gitignored generated city
  data under hard rule 7, so a build that reads it cannot be cloned (hard rule 2). That is *why* this
  stage exists. ⚠️ **`width_m` is no longer `lanes x lane_width_m`** and the schema is 5 because of
  it; `lanes` is still authored, so ⚠️ **this does NOT fix `Q94`** — `stacked_disagreeing` is
  byte-identical at 51 and only a lane count moves it. Numbers in `Q95`.
- 🔴 **The two station normals in this repo are OPPOSITE, and that is deliberate — do not "restore
  consistency".** `pipeline/carriageway.py::_stations` emits `[-unit[1], unit[0]]`, **right** of
  travel; `surface.mitres` and `tools/overhang.py::left_of` emit **left**, and `mitres` names its
  frame load-bearing because `TEXCOORD_0` is a lane coordinate from the nearside kerb and Hong Kong
  drives on the left. `carriageway.py` can hold the other convention because it keeps only
  `ahead + behind` and `min(ahead, behind)`, **both sign-free**. ⚠️ **Anything that keeps the
  DIFFERENCE inherits `Q78`'s defect** — an absolute value cannot report the direction of the move it
  measures — so it needs a named negation and a mutation check, never a comment.
  `tools/centreline_error.py` is the one consumer today and
  `test_the_station_normal_is_the_negation_of_mitres` is what fails loudly if either side moves.
- **`Q19`'s three candidates are all priced and candidate 1 is REFUTED — do not re-propose a
  centreline rule.** (Refuted, not refused: no rule declined it, a measurement disproved it.) `tools/centreline_error.py` registers the published centreline against the
  middle of the carriageway a publisher spanned: the correction available is 0.02-0.88 m where
  1.43-4.49 m is needed, it clears **0** edges at either bar, and `e233` has no clear cell in its
  cross-section at any offset. ⚠️ **Run it again if `pipeline/carriageway.py`'s survey, `_stations`,
  `surface.mitres` or `clearance.py` moves**; it grades and exits 0 whatever it finds. Numbers in
  `Q19`.
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
  (`Q56`). ⚠️ It needs `traffic_aids_drawings_gdb`, a **218 MB** fetch; get it with `--only` on a
  clone that has not built. ⚠️ **It is no longer "a fetch no build reads"** — that was true when
  this bullet was written and stopped being true at `P3-12`/`P3-14`: **seven** config blocks read it
  (`roads`, `carriageway_survey`, `arrows`, `signs`, `boxjunctions`, `road_marks`, `railings`), so it
  is ordinary build input. 🔴 **The audit's second-source property never rested on that** — it
  rests on the *layer*, TD's drawn marking codes against `NSR`'s restriction register.
  ⚠️ It grades rather than checks — a widening gap is a finding to go and look at, never a
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
  refusals live in two frames, published and ribbon, which is why `metres_dropped` is two fields. ⚠️ **A widening change is a railing change**: `surface.floor_default_m` moves the drawn kerb and
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
  not "restore consistency". ⚠️ **A widening change is a sign-position change** — `surface.floor_default_m`
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
  reading its 0, and do not describe it as grading the city. ⚠️ **`plates_turned` must equal the drawn NO ENTRY family exactly** (195 = `TS115` 177 + `TS116` 18 today; the invariant is the equality, not the number); a fall means the turn stopped happening, and a turn that stops renders perfectly.
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
  two partitions (`symbols` and `candidates`), `axis_residual_deg`, `offset_m`, `against_one_way`,
  `stacked_pairs`, `stacked_disagreeing`, `outside_carriageway` and `inverted`, before and after.**
  🔴 **The lane snap's denominator is the SURVEYED `width_m` and never `lanes x lane_width_m`** (`Q96`).
  That identity was `roadgraph.json`'s until `Q95` measured the width, and this stage went on rebuilding
  it for itself on 292 of 737 edges — reading `e351` CANAL ROAD EAST's 16.11 m as 6.4. ⚠️ **A change here
  is inert on the 445 authored rows by construction**, so force the old denominator region-wide first and
  require a **byte-identical** `arrows.glb`; that is what separates the refactor from the fix.
  ⚠️ **`outside_carriageway` is not `outside_drawn_ribbon`** — surveyed frame against drawn frame, 38
  against 9 — so quote both or neither. ⚠️ **At `lanes == 2` the snap reduces to `sign(offset_m)` and no
  width can reach it**, which is 670 of 737 edges, so a width change that moves nothing here is expected
  rather than a failure. There is no separate grader and there should not be: the stage grades itself,
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
  🔴 **And so is a *dimension* change, because that sheet publishes `LENGTH` for `RM1017`-`RM1030`
  and nothing else** — every proportion is read off TD's pictogram by eye (`Q59`), and `Q67`'s
  rasterise-and-diff cannot help here because the page is a scan. ⚠️ **The turn branch is not the
  ahead head**: reusing its length made `shoulder = reach - head_length` **negative**, put the turn
  head's base past the far side of the stem and merged the two into a blob on **416 of 747** arrows,
  through a release and a green `check.sh`. `config.py` refuses that now, and
  `test_no_head_overlaps_the_stem_it_grows_from` catches the class whatever the numbers are —
  ⚠️ **mutation-check it rather than reading its pass**, the way `Q72` says a counter is tested.
  ✅ **The sheet IS drawn to proportion despite the NOT TO SCALE stamp, and that is measured**:
  `RM1016` publishes `SIZE = 5600(H) x 2000` and its pictogram reads **2.802** against 2.800. So a
  proportion taken off a pictogram here is evidence — check a self-dimensioning code before assuming
  otherwise. 🔴 **The turn branch is authored anyway, and the reason is the trap**: TD's branch head
  is *wider than it is deep* because thin swept barbs do the work, so this model's plain triangle is
  a mushroom on the shaft and the faithful dart is a detached diamond — and its barbs are 0.09 m on a
  4 m arrow, which `Q91` removes at any driving distance. Fidelity to the drawing and legibility on
  the road are not the same target on this layer. ⚠️ **The ahead head and the stem taper are measured
  and must stay so** — the overlay agrees on both. Numbers in `Q93`.
  🔴 **`stacked_disagreeing` is `Q19`'s invented lane count arriving where a frame can show it, and
  it is 25 of 747 today** — 51 → 35 when the count became measured, 35 → 24 when the arrows' own
  row was let resolve an ambiguous bracket (`Q94`), 24 → 25 on 2026-08-30 (`e114` HENNESSY ROAD). The registration snaps a published offset to one
  of `ribbon.lanes` slots; the count came from the speed-limit table, so where the painted carriageway
  is wider two
  symbols collapse into one slot and draw **one shaft wearing two branches** — found from the driving
  seat, with every other counter correct and `inverted` 0. ⚠️ **Nothing is refused and nothing is
  moved**: de-duplicating would discard a published instruction on the authority of an invented
  width, which is `Q54` inverted. ⚠️ **A rising count is a finding, never a bar to retune** — and it
  is reachable at zero, so mutation-check it rather than reading its value. ✅ **The arrows are also a
  lane-count source** — a row across a carriageway is the count written down, 31 of 306 edges imply
  more lanes than the graph has — which is the most direct lead `Q19` has — ✅ **and it now ASSIGNS,
  not just grades**: a row resolves the brackets TPDM leaves ambiguous, `lanes` measured 153 → 210 of
  737. 🔴 **A row of ONE arrow is not a row.** It counts *painted* lanes, so it is a **lower bound** —
  an unpainted lane is invisible to it — and at one abreast it states a marking, not a count; 81 edges
  do that. ⚠️ **Refused, never floored**: flooring them published 28 edges whose `lanes_source` said
  `arrows` and whose count the arrows had not chosen, which is `Q72`'s tautology wearing the other hat.
  🔴 **Ambiguous brackets only, so the row is never a standalone publisher** — that keeps
  `verify_road_graph.gd`'s "measured lanes implies measured width" true by construction, and it is why
  **STEWART ROAD `e505` is still not fixed**: it states three lanes over an authored width.
  ⚠️ **The clustering is a SECOND implementation and the duplication is forced** — `arrows` imports
  `roads` imports `carriageway`, so no import exists — and `arrows.json`'s `lanes_row_disagreement`
  grades it at 0 of 57, over the rows the roads stage *published* and never all 306. Numbers in `Q94`.
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
- **`_deck_heights`, `_descend`, `_lifted_heights`, or `deck.touchdown_max_grade_pct`: also
  `tools/touchdown_error.py`, and paste its table — plus the roads stage's `descended / refused /
  graded across` line, before and after.** 🔴 **`deck_error.py` cannot see this defect and never
  could**: where the structure is absent there is nothing to measure against, so a ribbon clamped
  level in the air over an unmodelled touchdown reads as *uncovered* rather than wrong, and it
  scored a clean `P2-7` acceptance over a flyover visibly afloat above the street (`Q90`).
  ⚠️ **The grade is measured ribbon-to-ribbon, `clearance_m` included, never off the deck top** —
  the deck-top reading is ~0.2 m shallower over the same run and understated every row of `Q90`'s
  first table. ⚠️ **`touchdown_grade_pct` is recorded over the refusals as well as the keeps, and
  `n` exceeding `ends_descended` is how you tell** — recorded below the guard it is confined to the
  cap by construction and reports a clean sweep whatever the data does, which is `Q58`'s
  `drawn_gauge_m` trap for the fourth time. 🔴 **There is a THIRD refusal and it is deliberately
  OUTSIDE that distribution**: `ends_no_target` counts an end with no terrain to measure from, and
  it must stay counted rather than appended — an end with no grade has no grade to record, and
  review found this one holding the identity true by never reaching the list. So the partition is
  `len(touchdown_grade_pct) == ends_descended + ends_over_grade`, with `ends_no_target` beside it.
  🔴 **`_descend` gates on a LEVEL-0 edge at the node, never on "mixed"** — `elevation_levels`
  declares a level 2, and a `(1, 2)` node is mixed with no street to land on. ⚠️ **The grader cannot
  catch that**: a wrongly descended end is no longer clamped, so `clamped_m == 0` drops it from both
  halves of its partition. ⚠️ **`_deck_heights` and `_lifted_heights` ask different questions of the
  same node** — `sample_along` continuity against `sample_lowest_above` + `at_grade_m` — so both
  firing on one end is possible and would re-open a step; the 16 lifted and 9 descended ends are
  measured disjoint, which is data and not construction. ⚠️ **The bar is one-sided on purpose**: a ribbon still
  clamped *inside* the cap is the defect returning, one clamped *over* it is the refusal working.
  ⚠️ **`overhang.py` will read slightly worse and that is the instrument** — it asks whether
  structure lies under the ribbon, never whether air does, so a ramp resting on the terrain still
  counts as hanging and `Q22` is untouched. 🔴 **The evidence is a frame** (`Q62`): every counter
  read correctly while the bridge floated, so shoot one fixed camera in `city_preview.tscn` with
  `--debug-view=off --hud=off`, twice, and `cmp` them — a `minimal` pair differs in the fps readout
  alone. ⚠️ **`check.sh` cannot help**: both its `on_structure` assertions skip off-grade edges.
  Numbers in `Q90`.
- **Any painted layer's height, `surface.py`'s cap construction, or any paint `lift_m`: also
  `tools/paint_clearance.py`, and paste its table.** It asks the one question a marking stage cannot
  ask from inside — **is the paint on top of the asphalt or inside it?** — because every counter
  `boxjunctions.json` and `roadmarks.json` publish grades the ETL against its own intermediate
  values. 🔴 **`Q91` closed the previous box-junction defect on "a top-down raster of the shipped
  mesh is a complete grid", which is true and is exactly the projection that cannot see this**: the
  mesh is complete in **plan** and wrong in **Y**, and 23.2% of it shipped under the road. ⚠️ **Four
  columns, and only the last is gated** — `under hi` (what the depth buffer hides), `on kerb` (a
  surveyed extent past the drawn ribbon, which is registration and `Q54` refuses to scale), `in c'way`
  (the wrong height on the road it is drawn on) and `deep` (that, past `--accept-depth-m`). Pooling
  them leaves nothing to do but raise the bar. ⚠️ **`tramway` and `arrows` are reported and never
  gated**: `Q58` measured tram rails p50 3.26 m past the drawn kerb, so a third of them are over no
  carriageway at all and gating that fails the tool on a fact. ⚠️ **The shallow residue is geometric,
  not a defect** — paint is a flat triangle over a road that creases at every cap fan edge and every
  ribbon station, so its chord dips below the crown it spans by millimetres however right its
  vertices are. 🔴 **Do not answer a burial by raising `lift_m`**: clearing `Q92`'s p99 needed
  **0.158 m**, paint floating 16 cm over the road. ⚠️ **`vertices_over_cap` is the in-stage tripwire
  and there is deliberately no "placed minus drawn" counter** — that is `lift_m` by construction and
  `Q72`'s tautology. Numbers in `Q92`.
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
  ⚠️ **A widening change is a lamp-position change**: `surface.floor_default_m` moves the drawn kerb and
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
  also `tools/font_coverage.py --region <r>`.** It exits non-zero on a character that is in neither the font nor the
  display substitution table, which is the only thing standing between a data refresh and a tofu box
  on one street's plate. ⚠️ **Substitutions are a DISPLAY fix and `roadgraph.json` is never edited**
  — a street's name is the strongest case of `Q54`'s sourced-not-invented rule. ⚠️ The bundled font
  is the **fourth** licence in a repo whose hard rule 7 says three; `LICENSING.md` carries it, and
  the credits screen must when it exists — it does not yet, a recorded licence gap (`Q79`).
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
