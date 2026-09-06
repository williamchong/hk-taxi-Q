# touch.tres

Rationale for `game/tuning/touch.tres`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

How far a thumb travels (P2-4). See touch_profile.gd for what each number
means, and Q83 for the scheme these serve.

🔴 THESE ARE A FIRST GUESS AND THE FILE EXISTS SO THEY CAN BE RE-SEEDED. Q83
says no desk can pick them and P2-4's review is blocked on P0-3b for the
handset. Nothing here has been measured against a thumb.

⚠️ DESIGN UNITS, NOT DEVICE PIXELS — the same 1920x1080 frame hud_layout.tres
is written in. On a 2340-wide panel every number here is scaled by the
canvas_items stretch before it reaches a finger.

⚠️ EVERY KEY BELOW IS REQUIRED. touch_profile.gd declares no defaults, so a
missing key is a zero rather than something sensible — and a zero travel is a
car at full lock the instant a thumb lands. verify_input.gd refuses one.
