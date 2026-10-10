# parked.tres

Rationale for `game/tuning/parked.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How the parked roster (`P3-73`, `Q161`) is read against the clock and cut into cells. What a
placement IS — its kind, its hours, its chance — is the ETL's (`parked_placements.json`); this
table says only which hour the rig's `time_of_day` means and how the layer rebuilds out of view.
Every key is required: `parked_profile.gd` declares no defaults, and `ParkedLayer` refuses a zero
cell or an empty day rather than stand on a literal.

## `clock_start_h = 7.0`

`time_of_day` 0 is 07:00, 特更's opening hour (`shift.tres`, `Q162`, 2026-10-11): the roster reads
the same clock the player reads on the HUD, so a van that leaves at 19:00 leaves when the dash
says 19:00. 🔴 **This pair must equal `shift.tres`'s `opens_h` / `closes_h`** —
`verify_day_cycle` holds it. The cycle holds the authored day until 0.71 and reaches dusk at 0.79,
twilight at 0.86 and night at 0.93: 17:00, 18:00, 19:00 and 20:00, a Hong Kong October evening.
Was 12.0 against the 240 s cycle that opened at noon.

## `clock_end_h = 21.0`

`time_of_day` 1 is 21:00, 交更, where the cycle's night holds — in free mode too, whose day runs
the same table when its option is DAY TO NIGHT. The vans' 8-19 window closes inside the day and
the single-yellow fill (19-7) opens at twilight, which is what makes the night street carry more
cars than the day. The metered bays' 8am-to-midnight window opens an hour in, so the first game hour
of a shift (about 21 s) stands no metered car — the window as published.

## `cell_m = 300.0`

`prop_cells.tres`'s cell: the lamps' unit, measured there (`P3-67`). One `MultiMesh` a kind a
cell, about nine kinds, so Wan Chai's 863 vehicles are some forty draws resident.

## `range_m = 400.0`

`prop_cells.tres`'s range, for the same reason, and the bar a cell must be past before it is
rebuilt: a vehicle appearing or leaving inside this is a pop, and the street in view never
changes under the player.

## `range_margin_m = 15.0`

The engine's hysteresis about `range_m`, `prop_cells.tres`'s value.

## `poll_s = 1.0`

How often the layer asks the rig's clock and walks the cells. A placement's windows are whole
hours and an hour is about 21 s of the 300 s day, so once a second is twenty chances to catch it.

## `reroll_s = 90.0`

A hidden cell holding a placement with a chance under 1 — a bus at a stop a third of the time —
is drawn again this long after it was built. Longer than a lap of the region at the pace the
fare loop drives, so the same bus is there when the player comes straight back and may be gone
the next time round.
