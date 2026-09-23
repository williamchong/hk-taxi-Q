# hud_layout.tres

Rationale for `game/tuning/hud_layout.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The racing-game arrangement (`Q138`, the user's call): map bottom-left, speed
bottom-right, and the middle kept for what the player is reading now. It was
Midtown Madness 2's mirror of this until `P3-44`. See hud_layout.gd, and Q80 for
why the check grades `thumb_rest_*` and not `touch_zone_*`.

⚠️ BOTH DRAWN READOUTS SHARE A BASELINE AT y 860 — one clear band above
`thumb_rest_*`, which is as low as the touch contract allows, and level with
each other so they read as a pair of corners rather than as two floats.

🔴 ONE RULE, AND IT IS ABOUT WHAT A READOUT MEANS: left is the world, right is
the car, top is the fare, and the middle is the road — with ONE exception the
user called (`Q142`, 2026-09-24): the tip clock's bare numerals sit centred at
y 300, over the road and under the horizon, with no housing behind them. A
countdown is what an arcade racer puts there, and it is only up while a fare
runs. Nothing else joins it.

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
