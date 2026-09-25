---
name: run-hk-taxi-q
description: Build, launch, drive and screenshot the hk-taxi-Q Godot game. Use when asked to run the game, start it, drive it, take a screenshot of Wan Chai or the taxi, see a change working on real geometry, export the web build, or check that the city still renders.
---

# Running hk-taxi-Q

A Godot 4.7 arcade taxi game. The city is **build output**, not source — a fresh clone renders
nothing until the Python ETL has run. The game boots `main.tscn` — `World` holding
`city_drive.tscn`, `GUI` holding the HUD and the start menu (`P6-1`) — with the taxi on Expo Drive
under HKCEC. The menu parks the car and circles it with the camera until START is pressed;
`drive.sh` appends `--menu=off` so a scripted run drives at once, and `--menu=on` shoots the menu.

Drive it with **`.claude/skills/run-hk-taxi-q/drive.sh`**, which launches a scene, feeds it
scripted input, prints per-second telemetry, and writes PNGs. All paths below are relative to the
repo root.

## Prerequisites

Verified on macOS 15 (arm64), Godot 4.7.1, Python 3.13.

```bash
godot --version                  # 4.7.1.stable.official — brew install --cask godot
ls .venv/bin/gdformat            # from the venv below; check.sh will not run without it
```

## Build

The venv is the repo root's, not `etl/`'s. The first pipeline run downloads ~320 MB from
government servers and caches it in `etl/sources/`; after that the whole region is ~5 s.

```bash
python3 -m venv .venv && .venv/bin/pip install -e "etl/[dev]"

cd etl && ../.venv/bin/python -m pipeline --region wan_chai && cd ..
tools/sync_generated.sh
```

Ends by reporting the file count copied into `game/assets/generated/wan_chai/` (215 for Wan Chai
today). `tools/sync_generated.sh wan_chai causeway_bay` syncs both, the first the frame; a region
left off the list is deleted from the game tree. No
Godot import step is needed first — `drive.sh` builds `game/.godot/` on its first run, which is
slow the first time and instant afterwards.

## Run — agent path

```bash
.claude/skills/run-hk-taxi-q/drive.sh
```

Six seconds of full throttle from the start line, three screenshots into `build/driver/`
(gitignored). Output streams as it runs, a line a second:

```
vehicle: Taxi at (172.3485, 6.45805, 26.9396)
t= 0.00  pos=(  172.35,    6.46,    26.94)  speed=   0.00 kph  prims=142223 draws=5 phys=0.000ms
shot:    /Users/william/hk-taxi-Q/build/driver/t00.50.png  1920x1080  29 distinct colours
t= 3.00  pos=(  190.17,    6.20,    25.68)  speed=  45.30 kph  prims=132845 draws=33 phys=0.720ms
DRIVER OK
```

**Look at the PNGs.** `DRIVER OK` means nothing crashed and no frame was flat — not that the game
looked right.

`prims` and `draws` make a measurement a `drive.sh` run anyone can repeat, rather than a throwaway
probe that is deleted before the number is questioned. `phys` is the last physics tick's
`_physics_process` time in milliseconds (`P5-12`) — one tick, not an average, and run-to-run spread
on this machine is ±0.5 ms, so read the whole column and compare runs, never one line. Three things
to read the other two correctly:

- **Both are 0 under `--headless`** — the dummy rasteriser draws nothing.
- **`draws` is a budget metric directly; `prims` is not.** The budget in `docs/ARCHITECTURE.md` is
  stated in *visible* triangles, and `prims` counts every pass including shadows. Measured on this
  scene, the directional shadow costs roughly +1× the main pass per two cascades — 1 cascade ≈ 2.0×,
  2 ≈ 2.6×, 4 ≈ 4.1× — so treat it as a proxy that moves with the budget, not the budget itself.
- **The `t=0.00` line is a boot artefact.** It reports the frame drawn before the camera was placed
  and before the streamer had instanced any tile, which is why it reads far lower with a handful of
  draw calls. Start reading at `t=1.00`.

### Arguments

Everything after `drive.sh` goes to `driver.gd`. ⚠️ **The defaults above apply only when there are
no arguments at all** — pass any flag, even `--out=`, and the throttle hold is gone with them, so a
"throttle route" run with overlays off is `--seconds=6 --shots=0.5,3,6 --hold=accelerate@0.5+5.5
--debug-view=off --hud=off`. Six stationary seconds still print `DRIVER OK`.

| Argument | Meaning |
|---|---|
| `--scene=res://…` | default `res://scenes/main.tscn` (the drive, HUD included); also `res://scenes/dev/city_preview.tscn` and `res://scenes/dev/asset_viewer.tscn` |
| `--asset=res://…` | the `.glb` `asset_viewer.tscn` stands (`P5-22`); default the DCC fixture. Ignored by every other scene |
| `--seconds=6` | how long to simulate |
| `--shots=0.5,3,6` | sim times to capture |
| `--out=dir` | default `build/driver/`; relative paths anchor to the repo root, not to `game/` |
| `--hold=action@start+duration` | press an action; repeatable |
| `--camera=x,y,z` / `--look=x,y,z` | teleport the camera (preview scenes only) |
| `--spawn-fare=<region>/<id>` | start `city_drive` ON that fare node instead of 20 m short of the scene's `f_004` (`RoadSpawn.DEFAULT_SETBACK_M`; a named spawn takes no setback, so `--spawn-fare=wan_chai/f_004` is the old start line for a route timed from it) — any resident region, its fare placed through the merged graph — the only way to start a drive anywhere else, since `--camera` does not survive the chase camera; an unknown region or fare, or a scene with no drive harness, is refused |
| `--spawn-at=x,y,z` + `--spawn-facing=x,y,z` | put the car at a point in engine metres, facing another point, once the harness has placed it — the one way to start ON a deck, where no fare node stands (`P3-51`: `--spawn-at=268,10.5,531 --spawn-facing=268,10,600 --fares=off` is Fleming Road's flyover, `e208`, heading south). Both or neither; the harness's 25 m fall reset still measures from the start line |
| `--trace=<file>` | write one line per physics tick — plus `hit <tick> <m/s>` on a tick the car struck a wall, the speed into it as the penalty read it (`P3-50`) — — the car's position and velocity at six decimals (`tick`) and the collider under it (`under`) — plus every collision body entering (`body`) or leaving (`gone`) the tree, stamped with its tick (−1 is boot). The tool for "why don't two runs repeat": diff two traces for the **first divergent tick** and read the bodies that arrived just before it; the 1 s `%.2f` report cannot see either (`P5-9g`). Ticks spent waiting on a `--shots` capture are not traced, so compare traces from runs with the same shots. Inert: the `f_045` drive's report lines are identical with and without it, although it casts a ray every tick |
| `award:` lines | not a flag: every skill paid and every penalty docked prints as `award:   t= 5.13  skill 6  HK$-2.0` (`Fare.Skill` index, signed money) when the fare loop is on, so a drive into a wall leaves its evidence on stdout |
| `--hide-layers=a,b` | hide `layer_preview` nodes by `generated_layer.gd` id (`roadmarks`, `arrows`, …) in every resident region — what a layer costs a frame is the same drive with and without it, read off `prims` and `draws`. An unknown id is refused, and a run that hid no node fails. Inert on the car: positions match the unhidden run to the centimetre |
| `--debug-view=off\|minimal\|full` | debug overlay. **`drive.sh` defaults to `minimal`** |
| `--hud=off\|on` | the **player's** HUD — speed and street plate. On by default; this is not dev chrome |
| `--minimap=off\|on` | the minimap alone (`P3-44`); `--hud=off` takes it with everything else. `P3-9` runs with it off |
| `--fares=off\|on` | the fare loop (`P3-1a`). On by default — the car boots at a stand, so a stationary start hails within a second; `P3-9`'s free roam runs with it off |
| `--lang=en\|zh` | the language the callout, the street plate and the menu read in (`Locale`, `Q142`). **`drive.sh` appends `zh`** unless a run names it: absent, the game reads the option the menu saved (`user://settings.cfg`), then the OS language, then `zh`, and a frame must not depend on this machine's pick or locale |
| `--menu=off\|on` | the start menu (`P6-1`). **`drive.sh` appends `off`** unless a run names it, because the menu parks the car; `on` with `--seconds=3 --shots=2` is a menu frame — the orbit keeps the frame changing, so the capture never stalls |
| `--menu-page=home\|guide\|options\|credits\|notices` | the sheet the menu opens on, so a frame of any page is one run and never a click; needs `--menu=on`. Default `home` |
| `--fare-seed=<int>` | fix the destination draw, so two drives from one stand go to one place. Absent, randomised |
| `--touch=mouse\|off` | drive the **touch** scheme with the mouse as one finger (`P2-4`). Off by default |

One authored asset under the shipped rig, no city needed — the readout prints as `asset:` lines and
is drawn in the frame:

```bash
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/asset_viewer.tscn \
  --asset=res://assets/authored/vehicles/taxi_body.glb --seconds=1 --shots=0.8 --debug-view=off
```

Actions are the `[input]` names in `game/project.godot`: `accelerate`, `brake_reverse`,
`steer_left`, `steer_right`, `drift`, `look_back`. An unknown one fails rather than doing nothing.

⚠️ **`--touch=mouse` is one finger, so it cannot press two thumbs.** Hold the left button in the
lower-left of the window and drag sideways to steer; hold it in the lower-right and drag up or down
for throttle and brake. It exercises either thumb, never their interaction — `game/tools/verify_input.gd`
covers that — and it is a development aid, not the `P2-4` review, which needs `P0-3b`'s handset.

### The debug overlay

The game boots with **no overlay at all**; `F3` cycles it. `drive.sh` is the exception and appends
`--debug-view=minimal` unless you name a view yourself, because a screenshot that cannot say where
it was taken cannot be acted on.

| View | On screen | Draw calls |
|---|---|---|
| `off` | nothing — use it when the question is how the city *looks* | — |
| `minimal` | position block (top left) and fps/frame time (top right) | +8 |
| `full` | plus the road graph readout and its chevrons on the carriageway | +19 |

The position block is two lines, sized to survive a downscale:

```
taxi  X    184.39  Y     6.21  Z     26.09
grid 835949.4E 816098.9N   hdg 086   38 kph
```

`X/Y/Z` are engine metres — the same numbers as the telemetry lines. `grid` is **EPSG:2326**, the
CRS the ETL sourced the city in, so a suspicious frame can be checked against the source data
instead of against another screenshot. `hdg` is a compass bearing: `000` faces the harbour.
`cam` replaces `taxi` in the preview scenes, which is what makes a `--camera=` shot self-documenting.

⚠️ **A tall unshaded kite standing point-down on a kerb in a preview frame is a fare pin, not a
defect.** `fare_preview.gd` draws one per `fares.json` node in `city_preview.tscn` — 14 m tall, red
for a cross-harbour stand, amber for a stand, cyan for pick-up/drop-off, grey for drop-off only and
violet for a point of interest, each with a green tether to its snapped edge. One 20 m from the
camera reads as 40 m, and was recorded as an unattributed spike twice (`P3-35d5`, `P3-35g1`). They
stand on both sides of an A/B pair, so they never move a `cmp`.

⚠️ Remember the overlay when reading `draws`: the numbers in the sample output above were taken
with it off, and the default now adds 8.

A drift through the junction east of HKCEC — the taxi ends up facing back the way it came:

```bash
.claude/skills/run-hk-taxi-q/drive.sh --seconds=6 --shots=4.2 \
  --hold=accelerate@0.3+5.7 --hold=steer_right@3.0+1.5 --hold=drift@3.0+1.5 \
  --out=build/driver/drift
```

The whole region from the air, no car involved:

```bash
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/city_preview.tscn \
  --seconds=1 --shots=0.8 --camera=100,220,520 --look=250,0,50 --out=build/driver/preview
```

**The two colour viewpoints**, fixed by `Q27` so a look change can be judged against earlier shots
rather than against a fresh camera. Use both: they disagreed sharply about whether the city read
white, and that disagreement was itself a finding.

```bash
# street level, Hennessy Road canyon looking WSW — the shipping viewpoint
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/city_preview.tscn \
  --seconds=1 --shots=0.8 --camera=270,5.5,691 --look=30,4.5,719 \
  --debug-view=off --out=build/driver/street

# skyline, from over the harbour looking south — where "the city reads white" was judged
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/city_preview.tscn \
  --seconds=1 --shots=0.8 --camera=520,130,180 --look=520,45,640 \
  --debug-view=off --out=build/driver/skyline
```

`--debug-view=off` is not optional for these: the overlay's opaque text block is several per cent of
the frame and it lands in any statistic taken from the PNG.

⚠️ **Nor is `--hud=off`, since `P3-24`.** The player's HUD is not dev chrome and `--debug-view=off`
does not touch it: a street plate and a speed readout sit in the frame and land in the same
statistics. **A clean art-review frame needs both flags.** Conversely `--debug-view=full` is what
reveals the HUD's reserved slots (timer, combo, meter, award, callout) as cyan outlines, and its raw-versus-shown
street readout — which is how you tell a stale plate from a correct one.

Runs are **deterministic**. The clock reads the engine's physics-frame counter rather than
accumulating per iteration, so nothing that parks the driver for more than a tick — a screenshot, a
slow frame, a batch of catch-up steps — shifts the timeline. Two runs either side of a full asset
rebuild matched to the centimetre. You can diff telemetry between runs and trust the difference.

Bad input is refused rather than absorbed: a non-numeric `--seconds`, a flag with no value, a shot
past the end of the run, an unknown action name. Requested shot times closer than 0.01 s would
write the same filename, so they are merged and the surviving list is printed as `shots:`.

### Telemetry without a window

Faster, and works over SSH. Screenshots are refused in this mode, not attempted — see Gotchas.

```bash
godot --headless --path game --script "$PWD/.claude/skills/run-hk-taxi-q/driver.gd" -- \
  --seconds=3 --hold=accelerate@0+3
```

## Check

```bash
tools/check.sh                 # gdformat, import, GDScript warnings, 3 asset verifiers — ~90 s
.venv/bin/ruff check . && .venv/bin/ruff format --check .
cd etl && ../.venv/bin/pytest -q
```

`tools/check.sh` is the only Godot route that fails on error — read its exit code, never its
output. `VERIFY_GENERATED=0` skips the three asset verifiers for a clone with no city built.

## Run — in a browser

Verified end to end: exported, served, loaded in Chrome, taxi rendered on the road.

```bash
tools/export.sh web            # ~1 min, writes build/web/ (51 MB .pck)
tools/serve_web.py             # then http://127.0.0.1:8060
```

`tools/serve_web.py` exists because the build needs `SharedArrayBuffer`, which browsers gate behind
`Cross-Origin-Opener-Policy` / `Cross-Origin-Embedder-Policy` headers that `python -m http.server`
does not send. It boots into the drive scene with no console errors.

The editor path (`open -a Godot --args --path "$PWD/game"`, then F6) is in the README. Prefer not
to — see Gotchas.

## Gotchas

- ⚠️ **`drive.sh` does NOT re-import changed assets, and says nothing about it.** It builds
  `game/.godot/` on its first run and thereafter renders whatever is already in
  `game/.godot/imported/`. Rewrite a `.glb` and every screenshot afterwards is of the **old** mesh,
  with no warning and an exit code of `DRIVER OK`. This cost a long debugging session: geometry was
  removed, the render did not change, and the absent geometry was blamed for what was still on
  screen. **After changing any asset, run `godot --headless --path game --import` (or
  `tools/check.sh`, which does it) before believing a screenshot.** Check
  `ls -la game/.godot/imported/` against the asset's mtime when a render looks impossibly unchanged.
- **`--script` resolves relative paths against `res://`, not your shell.** `--script
  .claude/skills/…/driver.gd` fails with `File not found` because Godot looks for it inside
  `game/`. An absolute path works from anywhere; `drive.sh` builds one.
- **`--headless` hangs on screenshots, it does not error.** The dummy renderer never draws, so
  `RenderingServer.frame_post_draw` never fires and the first capture waits forever with no output.
  `driver.gd` refuses the combination up front, and bounds every capture at 600 physics ticks so
  any other stalled renderer fails with a message instead of hanging. If you write your own Godot
  tool, never `await` that signal unbounded.
- **GDScript lambdas capture locals by value.** A lambda connected to a signal cannot report back
  by assigning to a local in the enclosing function — the write lands on its own copy. It cost a
  screenshot that was written and then reported as a renderer failure. Use a field, or a bound
  method.
- **GDScript's `%` format has no `%g`,** and an unknown specifier is not an error: the string comes
  out verbatim, so a failure message prints `%g` where the number should be. Stick to `%s`, `%d`,
  `%f`.
- ⚠️ **A shader that fails to compile is invisible to `DRIVER OK` *and* to `tools/check.sh`.** Both
  exit `0`; the city just renders a blank fallback material where the facades were. Verified while
  closing `Q27`: `check.sh` printed `All checks passed` with 330 `SHADER ERROR` lines in its own log.
  After touching a `.gdshader`, grep the run for `SHADER ERROR` yourself —
  `drive.sh … 2>&1 | grep -i "shader error"`. ⚠️ **Do not try to spot it in the PNG.** "Featureless
  pale buildings with no window grid" was the tell until the facade elements were switched off in
  `tuning/city_facade.tres`, and it is now also what a *correct* render looks like. The grep is the
  only reliable test; the remaining visual tell is that the fallback loses the per-building colour
  too, so every building goes the same white.
- ⚠️ **Changing `generated_scene_import.gd` does not re-run it.** Godot caches imports on the source
  file, not on the post-import script, so `--import` — and even `touch`ing the `.glb` — leaves the old
  result in place, with no warning. This silently produced a "the fix does nothing" result that was
  really "the fix never ran". Delete the entries and reimport:
  `rm -f game/.godot/imported/<asset>.glb-*.{scn,md5} && godot --headless --path game --import`.
- **Godot exits `0` when a script fails to parse.** `quit(1)` never runs, so a broken tool reports
  success. `drive.sh` greps its own output for compile failures and supplies the exit code, the
  same trick `tools/check.sh` uses and for the same reason. Never read raw `godot` output and call
  it a pass.
- **Autoloads do not exist in `_init`.** Under `--script`, `root.has_node("InputRouter")` is false
  until after the first `process_frame`. Anything touching the action map has to wait a frame.
- **`--hold` cannot press `F3`.** The overlay toggle is a raw key, deliberately — the action map is
  the game's, and dev keys stay out of it — and `--hold` drives the action map and nothing else.
  Use `--debug-view=`. For the same reason the overlay is invisible to `--headless`, which parks it
  whatever the flag says: nothing draws there, so it would only cost the verify tools a tree walk.
- **`--camera` is ignored in `city_drive.tscn`.** The chase camera rewrites the transform every
  frame. It only bites in the preview scenes. To start a drive somewhere else, use `--spawn-fare=`.
- **`--hold` cannot fly the preview camera.** `free_look_camera.gd` reads
  `Input.is_physical_key_pressed` directly rather than the action map, so `Input.action_press` —
  how everything else here is driven — moves it not at all. Use `--camera` / `--look`.
- ⚠️ **Using the machine during a preview run corrupts the shot, and the log will not say so.** The
  window steals focus; a click on it puts `free_look_camera.gd` into `MOUSE_MODE_CAPTURED`, and from
  then on **every mouse movement rotates the audit camera**. Position is preserved and only
  orientation moves, which is what makes the result look like a plausible frame rather than an
  obvious failure. Three runs of one configuration returned whole-frame `L*` 41.39 (correct), 30.94
  (pitched down) and 55.75 (aimed at the sky). The run still exits `DRIVER OK`, and the `camera:`
  line prints the transform that was **requested** at placement — so the log of a ruined frame is
  identical to the log of a good one. **Leave the machine alone for the length of a preview shoot,
  and shoot every audit frame twice and `cmp` them; a single preview frame is not evidence.**
  ⚠️ Not to be confused with `free_look_camera.gd`'s `built` → `frame()` auto-framing, which
  `driver.gd` already handles by awaiting a process frame before placing the camera. That one moves
  position *and* orientation and is not the failure seen here.
- **`street` and `kerb` are static by `t=0.8`; ⚠️ `skyline` is NOT.** For the two street-level
  viewpoints `t=0.8`, `t=1.5` and `t=3.0` come out byte-identical once the streamer has settled, so
  there is nothing to be bought by a longer run and shooting early dodges the stall below. **The
  skyline camera sees the whole region and the streamer is still instancing at 0.8 s**: measured
  2026-09-08 (`P5-28c`), two runs at `t=0.8` returned 172 and 174 distinct colours, while four runs
  at `t=2.0` returned one hash. **Shoot the skyline at `--seconds=3 --shots=2.0`**, and on either
  camera shoot until a hash repeats — a run launched immediately after another one can still come
  back short.
- **`FAIL no frame drawn in 600 ticks` means NOTHING ON SCREEN CHANGED when the shot came due**
  (measured 2026-09-25, replacing an "obscured window" diagnosis that fitted the symptom): a car at
  rest with `--hud=off --debug-view=off` has no HUD and no fps counter redrawing, so no new frame
  is drawn and the capture waits on `frame_post_draw` for ever. A `TIME`-animated shader does not
  count. The same runs with `--debug-view=minimal` capture every shot, and a moving car never
  stalls. For a shot of a stationary car keep the overlay on; preview shots at `t=0.8` are fine
  because the frames after load count as changed.
- **Six seconds of full throttle leaves the carriageway.** The default run tops 56 kph and clips
  something at ~5 s. There is no terrain: everything that is not road is void, and the kerbs are
  0.15 m and mountable by design. `drive_harness.gd` respawns the car after a 25 m fall and says so
  on stdout — and since 2026-09-25 pulls a car that drives into the harbour back onto the nearest
  road (`in the harbour (n); back onto edge …`): full throttle from the start line is in the water
  at ~7 s.
- **The window steals focus** for the length of the run. Nothing to be done about it on macOS.
- **`game/project.godot` and `game/export_presets.cfg` are committed in Godot's own written form**
  (`Q119`), so an editor save, an export or a drive leaves them clean. If `git status` shows either
  modified after a run, that is a real settings change and `tools/check.sh`'s `settings` step says
  which value moved.
- **`build/` is gitignored**, so screenshots and web builds never dirty the tree.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `FAIL no usable city at …/city.json` | Fresh clone, or a `city.json` older than the current schema. The warning printed just above it names the fix. |
| `FAIL vehicle fell N m below its spawn` | No collider under the start line, or it drove off the map. The message carries the rebuild command. |
| `FAIL … wants a number` / `needs a value` | A malformed flag. Nothing ran; fix and re-invoke. |
| `FAIL no frame drawn in N ticks` | The renderer stopped producing frames. Not headless (that is refused earlier) — suspect the GPU or an occluded window. |
| `FAIL … is flat (N colours)` | The frame rendered nothing. Usually a missing city; check `game/assets/generated/` is populated. |
| `FAIL --shots=8 is past the end of a 6 s run` | Raise `--seconds` or lower `--shots`. |
| `FAIL no such input action 'turbo'` | Use the six action names above. |
| Run hangs with no output after `scene:` | You invoked `godot` directly with `--headless` and `--shots`, bypassing the guard. Drop one. |
| `godot not found as 'godot'` | Not on PATH. `brew install --cask godot`, or set `GODOT=`. |
| `cannot serve on port 8060: Address already in use` | A `serve_web.py` is already running. It will not pick another port; kill the old one or just use it. |
| `ERROR: Attempt to open script 'res://.claude/…' … File not found` | Relative `--script` path. Make it absolute. |
