---
paths:
  - "game/scripts/ui/*.gd"
  - "game/scripts/core/wrong_way_*.gd"
  - "game/scripts/core/street_tracker*.gd"
  - "game/tuning/{hud_layout,hud_style,wrong_way,street_tracker,minimap}.{tres,md}"
  - "game/tuning/street_plate.json"
  - "game/tuning/menu.{tres,md}"
  - "game/tuning/menu_text.json"
  - "game/scripts/camera/menu_orbit.gd"
  - "game/scripts/camera/menu_shot.gd"
  - "game/scripts/core/settings.gd"
  - "game/tools/verify_hud.gd"
  - "game/tools/verify_menu.gd"
  - "tools/font_coverage.py"
  - "tools/make_fonts.py"
  - "game/scripts/ui/ink_stroke.gd"
  - "game/assets/authored/fonts/*"
---

# HUD, wrong-way warning, street names, menu and fonts — before marking work done

Every block: `tools/check.sh` is the reading (it runs `verify_hud` and `verify_menu`); a verify
tool prints `ok` having checked NOTHING when a `preload`ed script fails to compile. `verify_hud`
sees no frame, so each block also owes frames. A clean art frame needs BOTH `--debug-view=off` and
`--hud=off`. `drive.sh` appends `--menu=off` and `--lang=zh`. Looks cited to a `Q` are the user's
calls: do not reverse them.

## HUD and layout

Owed: an A/B render at one camera, HUD off and on, and the draw-call delta (both sides re-run).

- **A layout change is a `P2-4` change**: `touch_steer_*` (tap zones, the HUD may overlap) and
  `thumb_rest_*` (thumbs, it may not) are not interchangeable; both directions asserted (`Q80`).
- **A touch screen reads `hud_layout_touch.tres`** (`Q204`): a layout change owes BOTH tables and
  handset frames — `drive.sh --window=1368x630 --safe-area=102,0,102,30 --touch=on`, thumbs with
  `--finger=`. Shading and zones run to the glass; text stays inside the safe line, which is
  measured against the screen, not the window.
- One head-up display (`Q163`): bare readouts, a round scope map, only the 咪錶 boxed.
- A pedal shows its push as a level, never opacity (`Q228`). The wheel draws
  `InputRouter.wheel_position()` (before the curve, `Q251`) at `wheel_centre()`, never the thumb's
  offset (`Q238`).
- No screen blur in the drive: `backdrop_blur.gdshader` is the menu's.

## Wrong way — `wrong_way_monitor.gd`, `no_entry_icon.gd`, `wrong_way.tres`, `warn_*` keys

Owed: a drive that goes the wrong way, and the draw-call delta. Route: `--spawn-fare=wan_chai/f_004
--hold=accelerate@0.3+12.7 --hold=steer_right@4.6+1.3` (north up Expo Drive East's `e660`).

- **The nose raises the sign, the velocity may only withhold it** (`Q81`): reversing while pointed
  the legal way is not wrong-way.
- **Two bars, never merged**: `angle_deg` 120 (the nose) and `correcting_angle_deg` 90. The region
  is 93.5% one-way by drivable length, so the false alarm is the failure mode: a nose bar at 90
  rings on every legal turn across a one-way street.
- **A miss CLEARS here; `street_tracker.gd` HOLDS.** Do not align them.
- `warn_bar_length` / `warn_bar_thickness` are the world sign's (`TS115`,
  `signs.py::_NO_ENTRY_BAR_THICKNESS`, `Q67`), ratcheted by `verify_hud`. `warn_blink_hz` is capped
  at 3 Hz (WCAG 2.3.1).
- Do not force the sign visible with `if false:` — the HUD never builds and the run still says
  `DRIVER OK`.

## Minimap — `minimap*.gd`, `minimap.tres`, `map_*` keys

Owed: an A/B drive with and without `--minimap=off` on one route, both sides run together, `draws`
and `prims`. To hold, carrying with a route up: **14.9k prims / +7 draws** (naively 37.7k).

- `map_field` and `map_road` are opaque, asserted. Mesh colours are RGBA8. `min_stroke_px`,
  `casing_px`, `span_m` are baked at build.
- A mirrored map looks right on a grid: the east-is-right assertions are the evidence. One-way
  arrows are off (`arrow_px = 0`) with their direction asserted; so is `beacon_point`.
- Map and street plate are ONE panel: `abutting()` fails if either moves alone.
- Red is the fare's, speed is the dashboard's (`Q139`): the needle stays amber.
- **The route line is the fare's own `Route`** (`P3-46`), read inside `sampled`, a child of the
  ROADS; `route_px` 0 draws none. None while idle (`Q142`). The pin is the FIELD's child.
- Owed: the web build's `clip_children` frame (`Q136`).

## Fare HUD — `fare_face.gd`, `fare_guide.gd`, `guide.tres`, `locale.gd`, `seven_segment.gd`

Owed: three frames at `--debug-view=off` — boarding at the boot stand, carrying, idle (from
`--spawn-fare=wan_chai/f_025`; confirm it still boots idle) — and the draw delta against
`--hud=off`.

- **Every string is `FareFace`'s**; one decided in `hud.gd` is invisible to the check.
  **Signal-driven, never polled** (`fares.md`).
- **No goal until someone is aboard** (`Q142`): idle, the arrow points at the closest pending
  customer and every pending pickup has a pin and a road ring; all hidden while a fare runs. No
  nearest-pickup callout, no designated stand per hail.
- A stop is `Fare.Stop.place(language)` over its road name; the distance is never between two
  names. One language at a time (`--lang=`), the plate included.
- Every meter tick flashes under the clock (`tick`), the banked sum off `delivered`. A skill paid
  at the door is named in the delivery caption (its flash is overwritten). The receipt sums skills
  as ONE term. The combo's live line hangs from the tick's row (`Q212`); a third row does not fit.
- LEDs: the dot is a mark on the cell before it (`cells_of`); `meter_unlit` is a ghost under
  `MIN_CONTRAST`; the clock rounds UP; the total shares a line with the tip
  (`FareFace.show_total`), `total_lit` dimmer than `meter_lit`.
- Filled slots leave `reserved_slots()` and stay in `hud_slots()`; both asserted.
- No next-junction arrow yet (`Q138`).

## Start menu — `start_menu.gd`, `menu*`, `settings.gd`, `main.gd`'s park / resume

Owed: a frame at `--menu=on --seconds=3 --shots=2 --debug-view=off` in each language (`--lang=zh`,
`--lang=en`), and a default `drive.sh` run showing the car drives from tick one. Pages:
`--menu-page=home|play|guide|options|sound|controls|display|language|credits|notices|record|report|pause`;
`--menu-sample=on` fills the 成績表; `--mode=free` shoots free mode's REPORT; CONTROLS needs
`--touch=on`; shoot `pause` at `--debug-view=minimal`. A standing shot must sway or the capture
stalls. A run naming either flag saves no record.

- **A menu flow is tested by TAPPING** (`Q241`): `Input.parse_input_event` on the button's rect,
  never `_on_start()` or an emitted `started` — a direct call runs at a different point in the
  frame and hid a restart bug.
- **Credits wording is a licence term** (hard rule 6): `verify_menu` holds the phrases; clear a
  failing edit with `LICENSING.md`. Engine notices are `Engine.get_copyright_info()` +
  `get_license_info()` at runtime (`engine_notices.gd`), never pasted text.
- **The menu never reaches into the level**: `Main` parks it (`DriveLevel.park`) and resumes on
  `started(mode)`. The car stands at `showroom_fare_id`, not the start line.
- **The pause holds the TREE, never `DriveLevel.park`** (`Q165`); its OPTIONS omit language and
  thumb sides (a HUD renewed mid-fare misses the fare's signals). RESET CAR is
  `DriveLevel.recover` (`Q229`), fare and clock untouched.
- The pause draws at `pause_fps` at most (`ControlOptions.hold_frames`, `Q165`); a FRAME RATE pick
  under it lands on release. The boot menu is not held: its cover counts frames.
- A language change is a new HUD, not a relabel. `--lang=` beats the saved option and the OS's.
- Two modes behind PLAY (`Q162`); a shift's end opens a fresh menu on REPORT; the shift's clock is
  the hour, never a countdown; TIME OF DAY is free mode's alone.
- OPTIONS is a list of groups, a page each, never a scroll (`Q223`). A pick that changes a drive
  (`ControlOptions`) takes a `drive.sh` flag that beats it. Sound is the Master bus (`Q221`); MUSIC's
  switch and slider on the same page are the `Music` bus alone (`Q246`).
- The camera follows the page through `Main` → `DriveLevel.frame_menu` (`Q164`).
- The 成績表 (`LedgerCard`, `Q169`, `Q206`): on touch it stacks into one scrolling column — a
  change owes handset frames of RECORD and REPORT in both languages, and SAVE RESULT copies the
  whole card (`_check_stacked`). `ledger_px` is read off a frame.
- The guide's pictures are drawn (`GuideCard.KINDS`), never textures or screenshots (hard rule 7).
- Boot: `ShaderWarmup` (`Q184`) warms only what is in the tree under the cover; grade cold in
  Chrome with the GPU cache moved aside. Cover and boot splash are one drawing,
  `assets/authored/loading/taxi.json` (`Q209`): a change owes `tools/make_splash.py` and a frame
  of both.
- Two `_follow.bind` on one signal are ONE connection: a second follower connects a lambda.

## Type and street names

- Three hands (`Q218`): the brush for the menu's name, choices, headings and a skill's flashed
  name; the 黑體 for interface text; the Kai for NAMES alone (plate, place, road).
- **The 黑體 and brushes are subsets**: a wording change in `menu_text.json`, `exam_sheet.json` or
  a script's Chinese string owes `pytest etl/tests/test_fonts.py`, and on failure
  `tools/make_fonts.py`. A missing glyph silently falls to the next face.
- **`street_plate.json`, the typeface, or a new region**: `tools/font_coverage.py --region <r>`
  (non-zero on a character in neither the font nor the substitution table). Substitutions are a
  display fix; `roadgraph.json` is never edited (`Q54`).
- The fonts are a fourth and fifth licence (`LICENSING.md`, the credits, `Q79`); the OFL subsets
  must not be named Bakudai.
