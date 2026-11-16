# hud_layout_touch.tres

Rationale for `game/tuning/hud_layout_touch.tres` (`Q119`).

The touch screen's table (`Q204`). `HudLayout.for_device()` reads it where
`DisplayServer.is_touchscreen_available()`, or under `--touch=mouse|on`; the desk keeps
`hud_layout.tres`. `hud_layout.md` has the rules both tables share.

- `design_size` 1536 × 864 is the scale: the canvas is stretched by `1080 / design_size.y`
  (`HudLayout.apply_scale`), 1.25, the user's pick. Readouts keep the desk's sizes in units and
  draw larger, the menu too. Zones and rests are physical, so they are the desk's numbers over
  the scale.
- `thumb_rest_*`: the lower 264 units of each side, not the desk's strip. On the handset the
  thumbs covered the map and the speed in the bottom corners, and `verify_hud` refuses either
  readout there. Each rest stays inside its zone's lower half.
- `minimap`, `street_plate`, `speed`: one storey up from the desk (the user's pick). The map
  under the clock on the left, the speed under the meter on the right, on one line (`verify_hud`).
- `timer` y 236: under the guide's arrow, which projects to about 18–24% of the screen's height
  here and hid the countdown at the desk's y. `tick` and `wrong_way` follow down the same column.
- `tick` y 338: the combo's skill row runs about 30 px under the rect, and lower is the taxi's
  roof sign (`Q212`).
- `pause` 96 units: 47 pt on an iPhone at 1.25, over the 44 pt minimum.
- `award`, `combo`, `clock`, `meter`, `callout`: where the desk has them, shifted for the width.
