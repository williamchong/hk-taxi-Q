# hud_layout_touch.tres

Rationale for `game/tuning/hud_layout_touch.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The touch screen's table (`Q204`, the user's ask from the first handset,
an iPhone Air, 2026-11-13). `HudLayout.for_device()` reads it wherever
`DisplayServer.is_touchscreen_available()`, or under `--touch=mouse|on`; the
desk keeps `hud_layout.tres`.

🔴 `design_size` IS THE SCALE. The canvas is stretched by
`1080 / design_size.y` over the desk's frame (`HudLayout.apply_scale`), so the
readouts here keep the desk's sizes in units and draw larger — the menu too.
The thumbs are physical, so the zones and rests are the desk's numbers over the
scale.

🔴 THE RESTS ARE THE HANDSET'S, NOT THE DESK'S 100-UNIT STRIP: the user's
thumbs covered the map and the speed in the bottom corners, so each rest is the
lower 380 desk units of its side, and `verify_hud` then refuses either readout
there. Each rest stays inside its zone's lower half, so the check's probe that
a rect over a tap zone is permitted still means something.

🔴 THE USER'S PICKS OFF RENDERED OPTIONS (2026-11-13): scale 1.25 over 1.0 and
1.15 (`design_size` 1536 × 864); layout A over B (map in the top-left corner,
clock under it) and C (speed bottom-centre, which the chase camera puts on the
taxi's boot). A keeps the desk's rule — left is the world, right is the car,
top is the fare — one storey up: the map under the clock on the left, the
speed under the meter on the right, at y 300 so 148 units clear the meter (the
user asked for more than 244's 92).

⚠️ `award` and `combo` stay reserved where the desk has them, over the map and
the speed's columns. `pause` is 96 units, 47 pt on an iPhone at 1.25, over
the 44 pt minimum the desk's 88 missed (34 pt).
