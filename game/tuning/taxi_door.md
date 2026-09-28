# taxi_door.tres

Rationale for `game/tuning/taxi_door.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The passenger door's swing (`P3-48`). These were `@export` defaults in
`taxi_door.gd` until `Q150` moved them, against `ARCHITECTURE.md`'s Constraint 4
— tuning is data. Which door, which way it swings and what it is made of are
`taxi.tscn`'s and `make_vehicle.py`'s; this file is how far and how fast.

⚠️ EVERY KEY BELOW IS REQUIRED. `taxi_door_profile.gd` declares no defaults, so
a missing key reads as zero, and the door refuses to swing on a zero `open_deg`
or `swing_s` rather than fall back to a literal (`TaxiDoor.usable`).
`alight_hold_s` may legally be 0.0 (its export floor), so a missing one cannot
be told from a chosen one and is not guarded: it reads 0 and the door shuts the
moment it is open. `verify_vehicle.gd` reads this file, asserts the scene hands
the node this very resource, and proves a zeroed `swing_s` leaves the door shut.

## `open_deg = 65.0`

Short of square on purpose. At 90° from the chase camera the leaf is edge-on
and vanishes into a line; 65° keeps its red face turned towards a camera
behind the car, which is the only place anyone sees it from.

## `swing_s = 0.35`

Under `fares.tres`'s `board_s` with room left over, so a hail shows the door
standing open for most of the boarding rather than still moving when it ends.

## `alight_hold_s = 0.8`

How long `open_briefly` holds the door fully open before shutting it — the
fare stepping out at the destination, or storming out of a bail. The hold
starts once the door is fully open, so a shorter swing never eats into the
time the passenger has to step out.
