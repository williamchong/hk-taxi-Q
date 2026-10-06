# car_outline.tres

Rationale for `game/tuning/car_outline.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The outline's answer to the car (`P3-65`, `Q158`, the user's ask, 2026-10-07): the city's line
thins and fades with speed. Read by `CarOutline` on `taxi_tyre.tscn`; what the line does with the
speed is `cel_outline.tres`'s `speed_thin_px` and `speed_fade`.

The drift's afterimage that this table also held — a hull off the end of the car moving most, in
the paint's darkened red, dragged at most 0.15 m — was reversed the same day on the user's ask for
the lamps alone: "instead of the whole car tail for drifting after image, what if we only drag the
lights? literally lighttail". That is `light_tail.tres`; the hull, its four turned cuts and its
measurements stay on the record in `Q158`.

## `full_speed_kph = 120`

Where `outline_speed` reaches 1 and the line is at its thinnest and faintest. The user asked to
compare at rest, 60 and 120 kph, and 120 is the top of that range. Above it the line holds.
