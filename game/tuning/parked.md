# parked.tres

Rationale for `game/tuning/parked.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How the parked roster (`P3-73`, `Q161`) is read against the clock and cut into cells. What a
placement IS — its kind, its hours, its chance — is the ETL's (`parked_placements.json`); this
table says only which hour the rig's `time_of_day` means and how the layer rebuilds out of view.
Every key is required: `parked_profile.gd` declares no defaults, and `ParkedLayer` refuses a zero
cell or an empty day rather than stand on a literal.

## `clock_start_h = 12.0`

`time_of_day` 0 is noon. The cycle (`day_to_night.tres`) holds the authored day until 0.25 and
reaches dusk at 0.55, twilight at 0.72 and night at 0.90: on this clock that is 15:00, 18:36,
20:38 and 22:48, which is a Hong Kong October evening within half an hour. First guess ahead
of the user's drive; the day's start is the one number here that is a look decision.

## `clock_end_h = 24.0`

`time_of_day` 1 is midnight, where the cycle's night holds. The metered bays' 8am-to-midnight
and the vans' 8-19 windows both close inside this day; the single-yellow fill (19-7) opens at
dusk, which is what makes the night street carry more cars than the day.

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
hours and an hour is 20 s of the 240 s day, so once a second is twenty chances to catch it.

## `reroll_s = 90.0`

A hidden cell holding a placement with a chance under 1 — a bus at a stop a third of the time —
is drawn again this long after it was built. Longer than a lap of the region at the pace the
fare loop drives, so the same bus is there when the player comes straight back and may be gone
the next time round.
