# minimap.tres

Rationale for `game/tuning/minimap.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The minimap's scale and orientation (`P3-44`, `Q136`). Colours are
`hud_style.tres`'s `map_*`; the slot is `hud_layout.tres`'s `minimap`.

⚠️ EVERY KEY BELOW IS REQUIRED. `minimap_profile.gd` declares no defaults and
`verify_hud.gd` refuses a zero by name.

⚠️ `min_stroke_px` and `casing_px` are BAKED into the road mesh at build, as
metres at the slot's scale, so a change to them — or to `span_m`, or to the
slot's width — is seen on the next launch and not live.

## `span_m = 320.0`

Metres of city across the slot's width: 0.875 px to the metre in a 280 px slot.
Wan Chai's blocks are 50-150 m, so two to four of them show either side, and a
10 m carriageway is 8.75 px — a street and not a hairline. Not yet driven
against a wider or tighter span; the first review's to move.

## `heading_up = true`

The nose is up and the map turns. `hud_layout.gd` puts the map near the road
because it is "glanced at mid-corner", and a glance has no time to rotate a
north-up map in the head. The user's call, `Q136`: "like a real world gps" —
the convention a driver already reads. ⚠️ North-up is the one that rewards a
local's memory, which was pillar 1's argument for it; weighed, not taken.

## `anchor = Vector2(0.5, 0.66)`

The car sits two thirds of the way down, so more of the slot is road ahead than
road behind. Under north-up 0.5, 0.5 is the honest value: "ahead" is no longer
a direction on the map.

## `min_stroke_px = 2.0`

An alley at its authored width is under 2 px here and flickers out as the map
turns. A floor, never a multiplier — `Q95`'s rule for the drawn road, borrowed.

## `arrow_px = 7.0`

The one-way arrows (`Q136`, the user's call): an arrowhead 7 px long and 0.8
as wide, about every `arrow_spacing_px` along a one-way road, pointing the way
the law runs. 93.5% of Wan Chai's drivable length is one-way, so without them
the map says where the streets are and not which can be entered. No colour of
its own: the field's inside a road it fits, the road's where the road is
narrower than the head. 0 draws none. ⚠️ Baked, like the strokes.

## `arrow_spacing_px = 56.0`

About 64 m at the shipped scale: one or two to a Wan Chai block, which is as
many as say the direction once. Every edge half a spacing long gets at least
one, centred, so a short link between two junctions is not left unsigned.

