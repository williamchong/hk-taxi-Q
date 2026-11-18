# hud_style.tres

Rationale for `game/tuning/hud_style.tres` (`Q119`).

The HUD's theme. Keep every look here and out of `hud.gd`; a second car's cluster would be a
second `.tres` of this class. Every key is required: `hud_style.gd` declares no defaults, and
`verify_hud.gd` refuses a zero it would draw with.

One head-up display (`Q163`): readouts float bare on a bracketed, vignetted frame, and only the
咪錶 keeps its box. Colour has fixed meanings (`Q139`): red is the fare's, amber the speed's, green
a gain.

Size rule: the speed reads at about 7% of frame width and the plate under about 18%. Larger reads
as furniture.

- `plate_field`, `chip_field`, `map_field`: one housing value in three keys. `verify_hud.gd`
  holds them equal, dark and opaque. Not the road's asphalt constant (`Q53`, `Q79`).
- `float_shadow`, `float_shadow_px`, `float_shadow_drop_px`: the shadow every floating readout
  casts, which keeps a white numeral readable on a white sky. `verify_hud` refuses a zero or a
  light one.
- `frame_*`: the four corner brackets, in the plate's ink at 0.55. `vignette`, `vignette_share`:
  the top and bottom 16% darkened to 0.4 at the edge.
- `dial_needle`: amber, a Crown Comfort's. Never red; `verify_hud` holds it off.
  `dial_full_scale_kph` 160 is past the car's top speed, so the needle never pins.
  `dial_sweep_px`: the amber arc from zero to the needle.
- `warn_disc`, `warn_bar`, `warn_bar_length`, `warn_bar_thickness` (`Q81`): NO ENTRY (TS115).
  The red, the white and the two proportions are the world sign's, graded against it by
  `verify_hud`. `warn_blink_hz` is capped at 3 Hz (WCAG 2.3.1).
- `map_road`, `map_road_main` (`P3-44`, `Q136`): light roads on the dark field. Main roads
  (`roadgraph.json`'s `street_class`) are near-white, minor ones mid-grey; `verify_hud` holds the
  main 0.15 of luminance over the minor. Not amber: that is a waiting customer's. Both and
  `map_field` are opaque, because strokes overlap and `minimap.gd` clips by the field's alpha.
- `map_water`, `map_park`: the harbour and parks from `basemap.json`, barely off the field;
  `verify_hud` holds a minor road 0.30 of luminance over both.
- `map_marker`: the car's chevron, taxi red, the one saturated thing on the map.
- `map_pickup`, `map_pending_px` (`Q142`): every pending customer in range as an amber pin, only
  while no one is aboard. `map_destination`, `map_pin_px`: the one destination pin, red, upright
  whatever the map's heading.
- `map_beacon_px`: while the target is off the map, a plain triangle on the border on the line
  from the car, in the target's colour. Not the car's chevron.
- `map_fade_px`: the round map's rim fading out, and its clip. `map_route`: the fare's route line.
- `meter_lit`, `meter_unlit` (`P3-5a`): the 咪錶's red seven-segment LED over its ghosts, five
  cells, dollars to one place. `verify_hud.gd` holds the lit digit off the ghost and the ghost off
  the housing.
- `tip_digit_px`, `tip_segment_px` (`P3-49`): the tip's LED under the meter's, same red, a bit
  over half its size. It shows the skills paid so far while carrying.
- `total_digit_px`, `total_segment_px`, `total_cells` 6: the session's takings on a third LED at
  the tip's size. One more cell than the fare's, because an overflow drops the leading digit.
- `total_lit`: `meter_lit` at 65%, so the row is told from the tip's. `verify_hud` holds it to
  half the meter's contrast bar off the ghost; `meter_lit` itself clears the full bar by 0.006,
  so no dimmer red could.
- `timer_outline_px` 6 (`Q142`): the tip clock has no housing, so its numerals carry the
  housing's dark as an outline. `verify_hud.gd` refuses a zero.
- `timer_unit_gap`: pixels between the seconds and the unit on one baseline (`99 秒`).
- `timer_warn_s` 10: the clock turns the fare's red for the last ten seconds. A first guess.
- `callout_*` (`Q142`): the building's name on the first line, the street under it at
  `callout_sub_size` in muted ink, `callout_caption_size` for the line saying what the box is.
  The `_zh` sizes are larger and `callout_line_gap_zh` wider: the Kai face's strokes thin out at
  the Latin sizes.
- `callout_hold_s` 5: how long a delivery's or bail's receipt stays up. Counted in samples at the
  loop's 5 Hz. Five seconds is what reading the sum takes.
- `tick_size`, `tick_fade_s` 1.2: each meter tick flashes under the clock and fades. Short
  enough that ticks never stack.
- `scrim`: the tint the menu's blurred backdrop is pulled toward (`menu.md`).
- `brush_stroke` (`Q218`): the menu's brush (`InkStroke`), the taxi's body red, a shade under the
  NO ENTRY disc's.
- `touch_hint`, `touch_live`, `touch_px` (`Q204`): the thumbs' controls on a touch screen, in the
  bracket's ink, faint at rest and 0.8 under a thumb.
- `touch_go`, `touch_stop` (`Q228`): a pedal shows its push as a level, never as opacity. Green
  up the accelerator, red down the brake: `accent` and `accent_negative` at 0.9. The one place a
  touch control is red.
- `touch_turn`: the wheel's arrow on the side the steering is turned takes it, as a pedal's arrow
  takes its pedal's paint. The dial needle's amber at 0.9 — a car's indicator, never green or red,
  which are the pedals'. The pedals' arrows and levels and the wheel's arrows read the steering and
  pedals the car is given, so a key or a pad lights them under a shown touch HUD too.
- `slot_fill`, `slot_edge`, `slot_edge_px`: the reserved slots under `--debug-view=full`.
