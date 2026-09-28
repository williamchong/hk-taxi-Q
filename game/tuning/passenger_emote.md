# passenger_emote.tres

Rationale for `game/tuning/passenger_emote.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The passenger's face popping out of the back seat (`P3-49`, `Q145`): how far it
rises, how long it lives, how fast it pops and shrinks, and how many may be up
at once. These were `@export` defaults in `passenger_emote.gd` until `Q150`
moved them, against `ARCHITECTURE.md`'s Constraint 4 — tuning is data. Which
face is which mesh stays on the node in `taxi.tscn` (`grin`, `angry`, `hurt`
are asset links, not tuning).

⚠️ EVERY KEY BELOW IS REQUIRED. `passenger_emote_profile.gd` declares no
defaults, so a missing key reads as zero, and `show_face` refuses to pop
anything on a zero rather than fall back to a literal (`PassengerEmote.usable`)
— every key here has an export floor above zero, so every one is guarded.
`verify_vehicle.gd` reads this file, asserts the scene hands the node this very
resource, and proves a zeroed `life_s` puts up no face.

## `rise_m = 1.3`

Enough to clear the roof from the seat with room over it: the seat is 0.55 m
up and the roof 0.86.

## `life_s = 1.6`

From the pop to gone. Long enough to be read from the chase camera, short
enough that a slide paying every second does not stack a column of faces.

## `pop_s = 0.18`

The face scales from nothing to full over this — a pop, not a fade.

## `shrink_s = 0.3`

The face takes this long to shrink away at the end of its life, so it leaves
rather than blinks out.

## `most_live = 4`

Skills can pay several times a second in a long slide; past this the oldest is
dropped rather than the newest.
