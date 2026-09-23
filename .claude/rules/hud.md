---
paths:
  - "game/scripts/ui/*.gd"
  - "game/scripts/core/wrong_way_*.gd"
  - "game/scripts/core/street_tracker*.gd"
  - "game/tuning/{hud_layout,hud_style,wrong_way,street_tracker,minimap}.{tres,md}"
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
- **Minimap changes — `minimap*.gd`, `tuning/minimap.tres`, the `map_*` keys in `hud_style.tres`:
  `tools/check.sh` (the `map:` assertions), an A/B drive with and without `--minimap=off` at one
  route, and BOTH deltas pasted — `draws` and `prims`.** ⚠️ **Re-run BOTH sides together**: a "+6" was reported here off a baseline taken before the dial existed. 🔴 **The map is a mesh drawn every frame,
  so it has a triangle cost the rest of the HUD does not**: built naively it was **37.7k** prims,
  an eighth of the mobile budget; it ships at **13.4k / +4 draws** over `--minimap=off` (whole HUD +15), arrows and the merged plate included, on shared junction caps,
  one-sided bevels and sub-pixel simplification (`minimap_mesh.gd`). ⚠️ **`map_field` and `map_road`
  are opaque and asserted** — strokes overlap, a deck's casing is the field's colour, and the clip
  is the field's alpha. ⚠️ **A mirrored map looks right on a grid**; the east-is-right assertions
  are the evidence, not the frame. ⚠️ A mesh keeps colours as **RGBA8**, so a test comparing them
  uses colours that survive 8 bits. ⚠️ `min_stroke_px`, `casing_px` and `span_m` are baked at
  build, not live. 🔴 **The map and the street plate are ONE panel** (the user's call): move
  `minimap` or `street_plate` alone and `abutting()` fails; in the strip the lettering shrinks,
  never the box, and `--minimap=off` is the only place the plate is still cut to its name. 🔴 **A one-way arrow's direction is asserted, never eyeballed** — tip ahead along the vertex order. 🔴 **Red is the fare's and speed is the dashboard's** (`Q139`, the user's calls): the needle stays amber, `SevenSegment` is the meter's and draws nothing until `P3-5a`, and the three panel fields are ONE housing value. 🚫 No route line (`Q137`). Owed: the web build's `clip_children` frame (`Q136`).
- **Fare HUD changes — `fare_face.gd`, the fare panels in `hud.gd`, `fare_guide.gd` and
  `tuning/guide.tres`, `locale.gd`, the pips and the pin in
  `minimap.gd`, `seven_segment.gd`'s dot, or the `meter_*` / `timer_*` / `callout_*` / `map_pickup`
  / `map_destination` / `map_pip_px` keys: `tools/check.sh` (the `face:`, `digits:` and pip
  `map:` assertions), plus THREE frames at `--debug-view=off` — boarding at the boot stand,
  carrying, and idle from `--spawn-fare=wan_chai/f_025` (31 m from any pickup, the one spawn that
  boots idle) — and the draw-call delta against `--hud=off` pasted.** 🔴 **Nothing is shown until there is a customer** (`Q142`, the user's call): idle, the
  callout, the guide and the pin are down and only the pool's pips remain; do not bring the
  nearest-pickup callout back, and do not invent a designated stand per hail — that is a
  `FareSystem` change and the user's call. 🔴 **Every meter tick flashes under the clock**
  (`tick` rect, `tick_fade_s`) off `meter_changed`, and the banked sum in green off `delivered`;
  after a delivery everything but the total resets. 🔴 **Every string is `FareFace`'s** and `verify_hud` reads it on synthetic fares; a string
  decided in `hud.gd` is one the check cannot see. 🔴 **A stop is its building over its road**
  (`Q142`): the first row is `Fare.Stop.place_en()` / `place_zh()` — `fares.json`'s `place`, iB1000's
  name, falling back to TD's description — and the second is the graph's road name for the stop's
  edge with the distance while idle. 🚫 Do not parse the building out of the description; the
  ETL publishes the footprint's name (`fares.places`, `pipeline/fares.py::read_places`). 🔴 **Signal-driven, never polled**: the system
  frees itself under `--fares=off` before `Main` hands it over (`fares.md`). ⚠️ **The filled slots
  leave `reserved_slots()` and stay in `hud_slots()`** — `verify_hud` asserts both, because a slot
  that leaves the graded set can drift onto a thumb with the check green. ⚠️ **The LED's dot is a
  mark on the cell before it**, appended after every cell's segments so the stride-of-12 reader
  still sees the cells first; `cells_of` is the one reader of a `.`. ⚠️ **`meter_unlit` is a ghost,
  not a reading**: held under `MIN_CONTRAST` of the housing and over it from `meter_lit`. ⚠️ **The
  clock rounds UP**: 0.2 s left reads 1, never 0 with time on it. ⚠️ **+31 draws for the whole
  HUD** (103 → 134 on the boot stand) against `Q139`'s +15 — the three housings, the LED, two
  labels, four callout labels, two pip nodes and the arrow; measure BOTH sides again after any
  change here. 🔴 **One language at a time in the callout** (`Locale`, `--lang=`): never English beside
  Chinese on a row; the plate alone stays bilingual. 🔴 **The distance is never between two
  names** — road first, then "320 m". 🔴 **The guide answers distance** (`tuning/guide.tres`,
  `guide.md`): the arrow small and red far, large and green near, the ring on the road the same
  colour; `verify_hud`'s `guide:` assertions hold both ends and the middle. 🔴 **The countdown
  is bare and centred** — the one readout in the middle, outlined in the housing's dark
  (`timer_outline_px`), no panel. ⚠️ **The pin is the field's child, not the roads'** — it must
  stand upright as the map turns; `follow` re-places it. 🚫 No route line (`Q137`), no
  next-junction arrow yet (`Q138`), no options menu yet (`P3-5b`).
- **Street-name or font changes — `street_plate.json`, the bundled typeface, or any new region:
  also `tools/font_coverage.py --region <r>`.** It exits non-zero on a character that is in neither the font nor the
  display substitution table, which is the only thing standing between a data refresh and a tofu box
  on one street's plate. ⚠️ **Substitutions are a DISPLAY fix and `roadgraph.json` is never edited**
  — a street's name is the strongest case of `Q54`'s sourced-not-invented rule. ⚠️ The bundled font
  is the **fourth** licence in a repo whose hard rule 7 says three; `LICENSING.md` carries it, and
  the credits screen must when it exists — it does not yet, a recorded licence gap (`Q79`).
