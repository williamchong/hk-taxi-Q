# hud_layout.tres

Rationale for `game/tuning/hud_layout.tres`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

Midtown Madness 2's arrangement: speed bottom-left, map bottom-right, and the
middle kept for what the player is reading now. See hud_layout.gd, and Q80 for
why the check grades `thumb_rest_*` and not `touch_zone_*`.

⚠️ BOTH DRAWN READOUTS SHARE A BASELINE AT y 860 — one clear band above
`thumb_rest_*`, which is as low as the touch contract allows, and level with
each other so they read as a pair of corners rather than as two floats.

🔴 ONE RULE, AND IT IS ABOUT WHAT A READOUT MEANS: left is the car, right is
the world, top is the fare, and the middle is the road and stays empty.

🔴 PLAN THE AREA, DO NOT HOLD THE SPACE. What ships is placed as though the
reserved slots do not exist, because they do not; a slot's contents arriving
is an edit to this file.

⚠️ EVERY KEY BELOW IS REQUIRED. `hud_layout.gd` declares no defaults, so a key
missing here is a zero-size rect rather than something sensible, and
`verify_hud.gd` refuses one.
