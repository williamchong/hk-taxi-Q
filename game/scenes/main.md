# main.tscn

Rationale for `game/scenes/main.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The boot scene, in the shape Godot's own guidance names: `Main` is the entry
point, `World` holds the level, `GUI` holds what is drawn over it, and a level
change swaps `World`'s children without touching the HUD (`Q119`). Until that
change `main.tscn` instanced `city_drive.tscn` whole, with the HUD inside the
level; the `P3-1`, `P3-2` and `P3-5` UI and the credits screen hard rule 6
requires all land under `GUI`, which is why the split precedes them.

`World` carries the one level there is. `city_drive.tscn` moved out of
`scenes/dev/` in the same change, because it is what this scene boots and
`PROGRESS.md` had already stopped calling it a dev scene; the dev previews,
the skidpad and the grey box stay there.

## `[node name="GUI" type="Node" parent="."]`

After `World`, and that order is load-bearing: a sibling's subtree is readied
and processed before the next sibling's, so everything under `GUI` finds the
car already placed and its `speed_kph` already written for the tick.

## `[node name="Hud" type="CanvasLayer" parent="GUI"]`

The player's HUD (`P3-24`) — speed, the street you are on, and three reserved
slots that `P3-5a` and `P3-5b` fill. Under `GUI`, after `World`, so the Taxi it
reads already exists when it first looks, and on layer 10 so `DebugHud` (127)
and its frame counter still win the corners when someone turns them on.

⚠️ `--hud=off` frees it. That is for `P3-9` first — the authenticity test is a
drive with the direction arrow disabled, and a permanent street plate is
closer to a navigation aid than that test's premise assumes — and for clean
art-review frames second.
