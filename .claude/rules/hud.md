---
paths:
  - "game/scripts/ui/*.gd"
  - "game/scripts/core/wrong_way_*.gd"
  - "game/scripts/core/street_tracker*.gd"
  - "game/tuning/{hud_layout,hud_style,wrong_way,street_tracker}.{tres,md}"
  - "game/tuning/street_plate.json"
  - "game/tools/verify_hud.gd"
  - "tools/font_coverage.py"
  - "game/assets/authored/fonts/*"
---

# HUD, wrong-way warning, street names and the font — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

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
- **Wrong-way changes — `wrong_way_monitor.gd`, `no_entry_icon.gd`, `tuning/wrong_way.tres` (the two
  bars and two dwells since `P5-26`), or the `warn_*` keys in `hud_style.tres`: `tools/check.sh` (which runs the 23 `way:` assertions), plus a drive that
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
- **Street-name or font changes — `street_plate.json`, the bundled typeface, or any new region:
  also `tools/font_coverage.py --region <r>`.** It exits non-zero on a character that is in neither the font nor the
  display substitution table, which is the only thing standing between a data refresh and a tofu box
  on one street's plate. ⚠️ **Substitutions are a DISPLAY fix and `roadgraph.json` is never edited**
  — a street's name is the strongest case of `Q54`'s sourced-not-invented rule. ⚠️ The bundled font
  is the **fourth** licence in a repo whose hard rule 7 says three; `LICENSING.md` carries it, and
  the credits screen must when it exists — it does not yet, a recorded licence gap (`Q79`).
