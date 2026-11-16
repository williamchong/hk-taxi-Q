# hud_layout.tres

Rationale for `game/tuning/hud_layout.tres` (`Q119`).

The desk's HUD arrangement (`Q138`): map bottom-left, speed bottom-right, the middle kept for what
the player is reading now. A touch screen reads `hud_layout_touch.tres`; a layout change owes both.

Every key is required: `hud_layout.gd` declares no defaults, and `verify_hud.gd` refuses a
zero-size rect.

The rule: left is the world, right is the car, top is the fare, the middle is the road. One
exception (`Q142`): the tip clock's bare numerals sit centred under the goal box, and the tick and
the NO ENTRY sign follow down the same column.

- Readouts stand 32 px in from the edges (`Q163`): with no housings, the corner brackets are the
  screen's edge.
- `minimap` and `street_plate` are one panel (`P3-44`, `Q136`): the map sits on the plate at the
  plate's width, and `HudLayout.abutting()` fails a layout that moves either alone. The map is
  square for the round scope. 280 wide is 14.6% of the frame, inside `hud_style.md`'s 18%.
- `speed` and `street_plate` end at y 960, one clear band above `thumb_rest_*`.
- `thumb_rest_*`: the bottom 100 px, the user's call; `P2-4` re-measures it. The check grades
  the rests, not `touch_zone_*`: the HUD may overlap a tap zone and may not overlap a thumb
  (`Q80`).
- `callout` 520 wide and the plate's strip 56 tall: one language, one line (`Q142`).
- `timer` y 116: the countdown, centred under the goal box, only up while a fare runs.
- `tick` 800 wide at y 288 (`P3-76`, `Q169`, `Q212`): the meter's "+HK$2.1" flash, the longest
  fault-sheet line a skill flashes, and the style combo's live line (車手 ×N on top, the skill
  that joined in a row below). Above the touch zones (y 480), clear of the pause button, and
  below the world's guide arrow (about y 180–260). `hud.gd` shrinks a line to the box.
- `wrong_way`: 4 px under the tick in both tables.
- `meter`: the 咪錶, top-right. `award` under it holds the combo's summary (`Q205`, `Q212`).
- `clock` (`Q162`): 特更's hour, never a countdown ("14:32" over "交更 21:00"). Top-left, shown
  only in a shift.
- `combo` is reserved (`Q138`): graded now, drawn only under `--debug-view=full`. Plan the area,
  do not hold the space: what ships is placed as though reserved slots do not exist.
- `pause` (`P6-1`, `Q165`): the one slot that takes a tap. 88 × 88 in the top band left of the
  meter, above y 480 so outside both `touch_zone_*`.
