# hud_layout.tres

Rationale for `game/tuning/hud_layout.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The racing-game arrangement (`Q138`, the user's call): map bottom-left, speed
bottom-right, and the middle kept for what the player is reading now. It was
Midtown Madness 2's mirror of this until `P3-44`. See hud_layout.gd, and Q80 for
why the check grades `thumb_rest_*` and not `touch_zone_*`.

⚠️ EVERY HOUSED PANEL SITS ON THE SCREEN'S EDGE (`Q142`, the user's call,
2026-09-24): the map and the speed on the side edges, the meter and the
callout on the top edge, no margin — the safe-area inset is the only gap. The
two bottom readouts share a baseline at y 960, one clear band above
`thumb_rest_*`, which is as low as the touch contract allows: the bottom edge
is the thumbs', so those two go to the SIDE edges only. ⚠️ THE RESTS ARE THE
BOTTOM 100 px, not 200, since the user asked for the map and the speed closer
to the bottom (2026-09-24): `P2-4` has no handset yet, so the rest's height is
a guess either way, and this one is the user's. `P2-4` re-measures it.

⚠️ THE GOAL BOX IS 520 WIDE, not 700: it carries one language since `Q142`,
and the street plate's strip is 56 tall for the same reason — one line.

⚠️ THE NO ENTRY SIGN SITS UNDER THE COUNTDOWN AND THE TICK (y 320, the user's
call), not at the top: the top-centre is the callout's, flush with the edge.

🔴 ONE RULE, AND IT IS ABOUT WHAT A READOUT MEANS: left is the world, right is
the car, top is the fare, and the middle is the road — with ONE exception the
user called (`Q142`, 2026-09-24): the tip clock's bare numerals sit centred
just under the goal box (y 116), with no housing behind them, and the meter's
tick and the NO ENTRY sign follow down the same column. A countdown is what an
arcade racer puts there, and it is only up while a fare runs. The meter's tick — "+HK$2.1" — flashes in `tick` just under it and
fades; nothing else joins them.

🔴 PLAN THE AREA, DO NOT HOLD THE SPACE. What ships is placed as though the
reserved slots do not exist, because they do not; a slot's contents arriving
is an edit to this file.

🔴 `minimap` AND `street_plate` ARE ONE PANEL (`P3-44`, `Q136`, the user's
call): the map sits on the plate at the plate's width, under one keyline, and
`HudLayout.abutting()` fails a layout that moves either alone. 280 wide is
14.6% of the frame, inside the 18% the size rule in hud_style.md allows; 340
was built first and read as too large (the user's call). The
pair is anchored as the PLATE is — bottom, with the speed.

⚠️ `award` AND `combo` ARE RESERVED: one rect for every component a planned
task is known to add (`Q138`), graded now and drawn only under
`--debug-view=full`. `timer`, `meter` and `callout` were, until `P3-5a` filled
them — the 咪錶 top-right, the callout top-centre as they stood, and the tip
clock moved to the middle of the frame (`Q142`) — and they stay graded against
the thumbs as filled slots.

⚠️ EVERY KEY BELOW IS REQUIRED. `hud_layout.gd` declares no defaults, so a key
missing here is a zero-size rect rather than something sensible, and
`verify_hud.gd` refuses one.
