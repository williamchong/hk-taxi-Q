---
name: run-hk-taxi-q
description: Build, launch, drive and screenshot the hk-taxi-Q Godot game. Use when asked to run the game, start it, drive it, take a screenshot of Wan Chai or the taxi, see a change working on real geometry, export the web build, or check that the city still renders.
---


# Running hk-taxi-Q

The city is build output: a fresh clone renders nothing until the Python ETL has run. The game
boots `scenes/main.tscn` — `World` holding `city_drive.tscn`, `GUI`
holding the HUD and the start menu — with the taxi 20 m short of fare `wan_chai/f_004` on Expo
Drive under HKCEC. The menu parks the car until PLAY → a mode is pressed.

`.claude/skills/run-hk-taxi-q/drive.sh` launches a scene, feeds it scripted input, prints
per-second telemetry and writes PNGs. Paths below are relative to the repo root.

## Build

Needs `godot` 4.7 on PATH (`brew install --cask godot`, or set `GODOT=`), Git LFS, and the
repo-root `.venv` (never one in `etl/`, never `uv run`). The first pipeline run downloads the
source data into `etl/sources/`.

```bash
python3 -m venv .venv && .venv/bin/pip install -e "etl/[dev]"

cd etl
../.venv/bin/python -m pipeline --region wan_chai --jobs 4
../.venv/bin/python -m pipeline --region causeway_bay --jobs 4
../.venv/bin/python -m pipeline.join --region-a wan_chai --region-b causeway_bay
cd ..
tools/sync_generated.sh wan_chai causeway_bay
```

The first region synced is the frame, and **a region left off the list is deleted from the game
tree**. With no arguments it re-syncs the regions already there. Wan Chai alone is enough to drive.

## Run and drive

```bash
.claude/skills/run-hk-taxi-q/drive.sh
```

With no arguments: 6 s of full throttle from the start line, shots at 0.5, 3 and 6 s into
`build/driver/` (gitignored). **Pass any argument and those defaults are gone** — the equivalent
run with clean frames is
`--seconds=6 --shots=0.5,3,6 --hold=accelerate@0.5+5.5 --debug-view=off --hud=off`.

```
t= 3.00  pos=(  190.17,    6.20,    25.68)  speed=  45.30 kph  prims=132845 draws=33 phys=0.720ms
DRIVER OK
```

`DRIVER OK` means nothing crashed and no frame was flat. **Look at the PNGs.**

- `prims` and `draws` are 0 under `--headless`. `draws` is a budget metric; `prims` counts every
  pass including shadows, so it is a proxy for the visible-triangle budget, not the budget.
- `phys` is one physics tick's time, not an average. Ignore the `t=0.00` line: it is the frame
  before the camera and the streamer are placed.
- `award:` lines print each skill paid or penalty docked; `red:` lines each red light run.
- Runs are deterministic, so a telemetry diff between runs is real. Bad input is refused.

A drift through the junction east of HKCEC:

```bash
.claude/skills/run-hk-taxi-q/drive.sh --seconds=6 --shots=4.2 \
  --hold=accelerate@0.3+5.7 --hold=steer_right@3.0+1.5 --hold=handbrake@3.0+1.5 \
  --out=build/driver/drift
```

Telemetry without a window (no screenshots; `--script` needs an absolute path):

```bash
godot --headless --path game --script "$PWD/.claude/skills/run-hk-taxi-q/driver.gd" -- \
  --seconds=3 --hold=accelerate@0+3
```

### Arguments

`drive.sh` appends `--debug-view=minimal`,
`--menu=off`, `--lang=zh`, `--day-cycle=off`, `--touch-steer=normal`, `--touch-side=left`,
`--touch-anchor=fixed` and `--touch-wheel=spin` (the defaults) unless the run names them, so a
frame does not depend on this machine's saved options.

| Argument | Meaning |
|---|---|
| `--scene=res://…` | default `res://scenes/main.tscn`; also `res://scenes/dev/city_preview.tscn`, `res://scenes/dev/asset_viewer.tscn` |
| `--seconds=6` | how long to simulate |
| `--shots=0.5,3,6` | sim times to capture; times within 0.01 s merge |
| `--out=dir` | default `build/driver/`; relative paths anchor to the repo root |
| `--hold=action@start+duration` | press an action; repeatable. Actions are `[input]` in `game/project.godot`: `accelerate`, `brake_reverse`, `steer_left`, `steer_right`, `handbrake`, `horn`, `look_back` |
| `--camera=x,y,z` / `--look=x,y,z` | place the camera — preview scenes only; the chase camera overwrites it in a drive |
| `--spawn-fare=<region>/<id>` | start the drive on that fare node, no setback (`wan_chai/f_004` is the start line itself). |
| `--spawn-at=x,y,z` + `--spawn-facing=x,y,z` | put the car at a point in engine metres facing another; the way to start on a deck (`--spawn-at=268,10.5,531 --spawn-facing=268,10,600` is Fleming Road's flyover) |
| `--tyres=res://tuning/<table>.tres` | run the car's tyre model on a trial table (the shipped car is on `tyre.tres`) |
| `--trace=<file>` | a line per physics tick (position, velocity, nose, collider under the car, wall hits, bodies entering or leaving). Diff two traces for the first divergent tick; same `--shots` on both |
| `--hide-layers=a,b` | hide layers by `generated_layer.gd` id (`roadmarks`, `arrows`, …) to cost them off `prims` and `draws` |
| `--debug-view=off\|minimal\|full` | debug overlay. `minimal`: position block and fps (+8 draws). `full`: plus the road graph readout, chevrons and the HUD's reserved slots (+19) |
| `--hud=off\|on` | the player's HUD; on by default |
| `--minimap=off\|on` | the minimap alone |
| `--fares=off\|on` | the fare loop; on by default, and a stationary start hails within a second |
| `--fare-seed=<int>` | fix the destination draw |
| `--traffic=off\|on`, `--trams=off\|on` | moving traffic with its signals; moving trams. On by default |
| `--push=off\|on` | whether the taxi knocks moving cars and trams by mass; `off` makes them walls |
| `--mode=free\|shift` | the mode a run with no menu plays; default free. `shift` ends with `shift over: HK$…` |
| `--shift-s=<seconds>` | run the whole shift in that many game seconds; needs `--mode=shift` |
| `--day-cycle=off\|on\|night` | whether the day runs to night; `night` holds free mode at `night_at` |
| `--time-of-day=<0..2>` | hold the lighting rig at one point of `tuning/day_to_night.tres`: 0 morning (07:00), 0.174 the authored day, 0.36 noon, 0.79 dusk, 0.86 twilight, 0.93–1 night, 1.464 moon low, 1.661 dawn |
| `--lang=en\|zh` | language of the callout, street plate and menu |
| `--menu=off\|on` | the start menu; `--menu=on --seconds=3 --shots=2` is a menu frame |
| `--menu-page=home\|play\|free\|guide\|options\|credits\|notices\|report\|record\|pause\|sound\|controls\|display\|language\|privacy` | the sheet the menu opens on; needs `--menu=on`. `pause` drives 1 s first — shoot it after 1 s at `--debug-view=minimal`. `controls` shows nothing without `--touch=on` |
| `--menu-sample=on` | fill the report sheet with a made-up result; saves no record |
| `--touch=mouse\|on\|off` | `on` lays out for touch; `mouse` also drives the touch scheme with the mouse as one finger |
| `--touch-steer=gentle\|normal\|sharp`, `--touch-side=left\|right`, `--touch-anchor=relative\|fixed`, `--touch-wheel=spin\|slide` | touch steering curve, steering thumb's side, whether the controls follow the thumbs, whether the wheel is spun or slid |
| `--finger=fx,fy>gx,gy@start+dur` | a scripted touch in shares of the window; repeatable, so two are both thumbs |
| `--window=WxH` | window size from boot; `1368x630` is an iPhone Air at half size |
| `--safe-area=l,t,r,b` | handset insets in window pixels; `102,0,102,30` for the size above |
| `--asset=res://…`, `--lineup=<gap m>` | `asset_viewer.tscn` only: the `.glb` it stands (default the DCC fixture), and its top-level nodes in a row that gap apart |
| `--perf-log=<s>` / `--perf-skip=<s>` | frame recorder: rows to `user://perf.csv` and a p50/p95/p99 summary, skipping the first `--perf-skip` seconds (default 10) |

## Screenshots

The overlay's position block reads `X/Y/Z` in engine metres, `grid` in EPSG:2326 and a compass
`hdg` (`000` faces the harbour); `cam` replaces `taxi` in preview scenes. A frame judged on looks,
or measured, needs both `--debug-view=off` and `--hud=off`.

```bash
# the whole region from the air
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/city_preview.tscn \
  --seconds=1 --shots=0.8 --camera=100,220,520 --look=250,0,50 --out=build/driver/preview

# the two fixed colour viewpoints (Q27) — use both
# street: Hennessy Road canyon looking WSW
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/city_preview.tscn \
  --seconds=1 --shots=0.8 --camera=270,5.5,691 --look=30,4.5,719 \
  --debug-view=off --out=build/driver/street
# skyline: from over the harbour looking south — the streamer is still loading at 0.8 s
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/city_preview.tscn \
  --seconds=3 --shots=2.0 --camera=520,130,180 --look=520,45,640 \
  --debug-view=off --out=build/driver/skyline

# one authored asset under the shipped rig, no city needed
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/asset_viewer.tscn \
  --asset=res://assets/authored/vehicles/taxi_body.glb --seconds=1 --shots=0.8 --debug-view=off
```

Before/after comparisons: the `godot-ab-render` skill.

## Check it still renders

```bash
tools/check.sh                 # gdformat, tuning sidecars, import, settings, warnings, verify_*.gd
```

Read its exit code, not its output. `VERIFY_GENERATED=0` skips the verify tools that need a built
city. Then run `drive.sh` and look at a frame.

## Export web

```bash
tools/export.sh web            # writes build/web/; needs the export templates for this Godot version
tools/serve_web.py             # http://127.0.0.1:8060, or pass a port
```

`python -m http.server` cannot serve it: the build needs COOP/COEP headers for `SharedArrayBuffer`.

## Traps

- **`drive.sh` does not re-import changed assets.** It renders what is in `game/.godot/imported/`.
  After changing any asset run `godot --headless --path game --import` (or `tools/check.sh`) before
  believing a screenshot.
- **Changing `generated_scene_import.gd` does not re-run it.** Imports are cached on the source
  file. `rm -f game/.godot/imported/<asset>.glb-*.{scn,md5}` and reimport.
- **A shader that fails to compile exits 0** from `drive.sh` and renders a blank fallback
  (`tools/check.sh`'s `shaders` step fails it). After touching a `.gdshader`: `drive.sh … 2>&1 | grep -i "shader error"`. Do
  not judge it from the PNG.
- **Godot exits 0 when a script fails to parse.** `drive.sh` and `check.sh` grep their output and
  supply the exit code. Never read raw `godot` output and call it a pass.
- **`--headless` cannot screenshot.** `driver.gd` refuses the combination and bounds every capture
  at 600 physics ticks. In your own tool never `await RenderingServer.frame_post_draw` unbounded.
- **`FAIL no frame drawn in 600 ticks` usually means nothing on screen changed** when the shot came
  due: a car at rest with `--hud=off --debug-view=off` draws no new frame. Keep
  `--debug-view=minimal` for a stationary car, or shoot a still preview camera at
  `--seconds=2 --shots=1.0`. It also happens on moving runs now and then; keep runs short and retry.
- **Leave the machine alone during a preview shoot.** The window takes focus; a click captures the
  mouse and every movement then rotates `free_look_camera.gd`, while the log still prints the
  requested `camera:` transform. Shoot each audit frame twice and `cmp`.
- **`--hold` drives the action map only.** It cannot press `F3` (use `--debug-view=`) or fly the
  preview camera (use `--camera` / `--look`).
- `--touch=mouse` is one finger; for two thumbs use `--finger=` twice.
- A tall unshaded kite on a kerb in a preview frame is a fare pin (`fare_preview.gd`), not a defect.
- Six seconds of full throttle leaves the carriageway. `drive_level.gd` respawns the car after a
  25 m fall and pulls it out of the harbour, saying so on stdout.
- If `game/project.godot` or `game/export_presets.cfg` is modified after a run, that is a real
  settings change (`Q119`).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `FAIL no usable city at …/city.json` | No city built or synced, or a `city.json` older than the current schema. Rebuild and sync |
| `FAIL vehicle fell N m below its spawn` | No collider under the start line, or it drove off the map |
| `FAIL … is flat (N colours)` | The frame rendered nothing; check `game/assets/generated/` is populated |
| A wall of parse errors naming scripts a drive never touches | The clone is unimported: `godot --headless --path game --import` |
| `cannot serve on port 8060: Address already in use` | A `serve_web.py` is already running; use it or kill it |
