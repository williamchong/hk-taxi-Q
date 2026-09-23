# hud_style.tres

Rationale for `game/tuning/hud_style.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

ONE VOICE: the cab's instruments in one black housing (`Q139`, the user's
calls). Every panel is `plate_field` under one `plate_edge` bezel; the speed is
the DASHBOARD's — a dial, an amber needle, printed numerals — and the 咪錶's red
seven-segment LED is kept for the fare (`P3-5a`), because speed was never on a
meter. It was "white is the city speaking, dark is the car speaking" (`Q80`)
until the map made the white half the larger one and the two read as two
designs.

🔴 THIS TABLE IS THE THEME. A Comfort Hybrid's modern cluster is a second
`.tres` of this class that the car names; nothing selects one while there is
one car. Keep every look here and out of `hud.gd`.

⚠️ `plate_field`, `chip_field` and `map_field` ARE ONE VALUE in three keys —
three panels read them, one housing — and `verify_hud.gd` holds them equal,
dark and OPAQUE. The housing is NOT the road's asphalt constant, for the
reason the plate white was not its paint (`Q53`, `Q79`).

⚠️ THE SIZE RULE, measured off the references this layout is taken from: the
speed reads at about 7% of frame width and the plate under about 18%, which is
where Midtown Madness 2 puts the same two things. Anything larger reads as
furniture, and the city is the deliverable.

⚠️ EVERY KEY BELOW IS REQUIRED. `hud_style.gd` declares no defaults, so a key
missing here is zero rather than something sensible; `verify_hud.gd` refuses a
zero it would otherwise draw with.

## `warn_disc = Color(0.761, 0.102, 0.149, 1)`

NO ENTRY (TS115), the same sign standing on 179 posts in the region. The red
and the two proportions are quoted from the world sign and graded against it
by verify_hud; the bar draws in plate_field. See hud_style.gd and Q81.

## `map_field = Color(0.07, 0.07, 0.075, 1)`

The minimap (`P3-44`, `Q136`): light roads on the housing — a figure-ground
plan, which is what survives under a pixel to the metre.
🔴 `map_field` AND `map_road` ARE OPAQUE, and verify_hud refuses otherwise:
strokes overlap at every joint, a deck's casing is the field drawn over the
street beneath it, and minimap.gd clips by the field's drawn alpha. The chevron
is taxi red: it is the taxi, and the one saturated thing on the map.

## `dial_needle = Color(1, 0.6, 0.12, 1)`

The speedometer's needle: amber, a Crown Comfort's. 🔴 NOT RED, and verify_hud
holds it off: red is the fare's, and the acceleration bar's red two pixels
below it already means "losing speed". `dial_full_scale_kph` is 160 against a
car that tops out at 140 — a dial that ends where the car does never looks
fast, and one the car can run off pins the needle when it matters.

## `warn_bar = Color(0.941, 0.941, 0.918, 1)`

The NO ENTRY bar's white, the world sign's `#f0f0ea`. It borrowed the plate's
white while the plate had one (`Q139`).

## `meter_lit = Color(1, 0.22, 0.12, 1)`

The 咪錶's LED (`P3-5a`, `Q139`): the fare in red seven-segment digits over
their ghosts (`meter_unlit`), dollars to one place, right-aligned in five cells
— a Hong Kong meter's face, and the one place red is spent. `verify_hud.gd`
holds the lit digit off the ghost and the ghost off the housing, so the unlit
segments stay a face and never a second reading.

## `timer_outline_px = 6`

The tip clock has no housing (`Q142`, the user's call: the countdown in the
middle of the frame, no backdrop), so its numerals carry the housing's dark as
an outline instead, and `verify_hud.gd` refuses a zero: a bare white 84 px
number over a light road is the one place this HUD could vanish.

## `timer_warn_s = 10.0`

The tip clock is seconds left on the allowance (`Q141`: the seconds left are
the tip), in the chip's ink until ten seconds, then the fare's red — the
passenger is about to bail, and it is the tip draining, so it takes the meter's
colour. A first guess ahead of the user's drive.

## `callout_sub_size = 20`

The callout is the place over the road (`Q142`, the user's call: a passenger
says a building, not a kerb): the building's name on the first line in both
languages at the plate's sizes, and the street under it at this size in the
chip's muted ink, with the distance while idle. Both lines shrink to the box,
the English giving way first because the Chinese is the shorter.

## `tick_fade_s = 1.2`

Each meter tick flashes "+HK$2.1" under the clock at `tick_size` and fades over
this (the user's call: feedback near the centre for every tick). Long enough to
be read at a glance, short enough that ticks a few seconds apart never stack.
`callout_caption_size` is the small line over the goal — DESTINATION, PICKING
UP, DELIVERED — that says what the box is, which the box alone did not.
⚠️ THE CHINESE SIZES ARE LARGER (`callout_size_zh` 40, `callout_caption_size_zh`
22, `callout_sub_size_zh` 26): the Kai face's strokes thin out at the Latin
sizes and the user read the box as unreadable at 30 / 15 / 20.

## `callout_hold_s = 3.0`

How long DELIVERED or PASSENGER BAILED stays in the callout before the box goes
down: fifteen samples at the loop's 5 Hz, and the model counts samples, not
seconds, so `verify_hud.gd` can step it.

## `map_pin_px = 26.0`

The destination's marker on the map is a PIN, not a dot (`Q142`, the user's
calls): its tip on the point, upright whatever the map's heading, in
`map_destination`, up only while a fare has one. Every PENDING customer in
range is a pin too — all of them, like a map, not the closest alone — at
`map_pending_px` in `map_pickup`, shown only while no one is aboard.

## `map_pickup = Color(0.9, 0.75, 0.3, 1)`

Every pending customer as an amber pin on the map (`Q142`, the user's call:
the pool, not one invented passenger). The destination is ONE pin in
`map_destination`, the chevron's red, because the destination is the fare and
red is the fare's.
