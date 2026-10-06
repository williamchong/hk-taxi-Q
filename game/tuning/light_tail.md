# light_tail.tres

Rationale for `game/tuning/light_tail.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The light tail (`P3-70`, `Q158` reversed on the user's ask, 2026-10-07): while a slide counts,
each tail lamp leaves a streak along the arc it swings through, fading with age; the body carries
only the city's line. "Instead of the whole car tail for drifting after image, what if we only drag
the lights? literally lighttail" — the user, turning round `P3-65`'s afterimage, a hull off the end
of the car moving most that could be dragged no further than 0.15 m before it read as a second car.
A streak off the lamps alone cannot read as a car, so it can be as long as a light tail is.

`LightTail` (`scripts/vehicle/light_tail.gd`) finds the two brake lenses in the body mesh by the
import's stamps and `LightTrail` lays the streak as a ring of pieces, `SkidStrip`'s shape in the
air; `light_tail.gdshader` fades each corner against the clock it was laid at. The tier is the same
`SkillTracker.drift_tier` the sparks and the receipt take, so a streak is always a counted slide.

⚠️ EVERY KEY BELOW IS REQUIRED. `light_tail_profile.gd` declares no defaults, so a missing key reads
as zero, and the rig refuses to run on a zero (`LightTail.usable`). `verify_vehicle.gd` asserts the
scene hands the rig this very file, proves a zeroed `life_s` and an empty `colours` are refused,
and drives the trail without a car.

The ring's capacity is not a key: it is `life_s` of every lamp at the physics rate plus a tick
(`LightTail.capacity_for`), so a longer life can never overwrite a piece before it has faded.

Provisional: set by eye on the street, the user's look call to come (`P3-70`).

## `colours = (1, 0.16, 0.2, 1)`

One entry, so every tier streaks the same: the brake lens's lit red — `make_vehicle.py`'s `RED`
hue-normalised to a peak of 1, as `vehicle_body.gdshader` lights the lens. The tail is the lamps,
so it is the lamps' colour; `drift_sparks.tres` carries the tier's colour for the bonus's status.
The table takes the sparks' shape — a colour per tier, the last past the end — so the user can try
the tier's colours here by listing them, with no code moved.

## `life_s = 0.4`

How long a piece lives. At 60 Hz that is 24 pieces a lamp behind the car; at a slide's 40 kph
sideways the tip is about 4 m back. Long enough to draw the arc, short enough to end with the
slide.

## `fade_power = 1.0`

Linear: the streak thins evenly to its tip. Above 1 it drops sooner and lingers faint.

## `max_step_m = 2.0`

`skid_marks.tres`'s reason: twice what the car travels in a 60 Hz tick at 200 kph, so a fast slide
is unbroken and a teleport, a reset or a landing far from the take-off starts a new streak.

## `width_scale = 1.0`

The streak's cross-section is the lens's own box — its width across the car and its height — so
the tail is exactly the lamp drawn out. A cross of two quads, not a billboard: it reads from the
chase camera above and from level behind.
