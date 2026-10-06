# car_outline.tres

Rationale for `game/tuning/car_outline.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The outline's answers to the car (`P3-65`, `Q158`, the user's ask, 2026-10-07): the city's line
widens with speed, and the car carries a thin rim in its own outline colour while a slide counts.
Read by `CarOutline` on `taxi_tyre.tscn`; what the line does with the speed is `cel_outline.tres`'s
`speed_thin_px` and `speed_fade`.

- `full_speed_kph` 120: where `outline_speed` reaches 1 and the line is at its widest. The user
  asked to compare at rest, 60 and 120 kph, and 120 is the top of that range. Above it the line holds.
- `hull_width_m` 0.03: one width at every counted tier, so the car keeps its shape ("drains a
  little without breaking the shape of car", the user). A first cut widened it per tier to 0.09 m
  and read as a sudden bold; refused the same day.
- `trail_width_m` 0.04: up to that much more rim on the trailing side, the side the car slides away
  from, easing round the body with no step — a lopsided rim that reads as the car's afterimage,
  飄移殘影 ("make the drifting outline bolded on a side but not too much", the user, 2026-10-07).
- `seep_s` 0.25 / `drain_s` 0.6: the time constants of the ease in and out. The rim never arrives
  or leaves in a step; it drains slower than it seeps, so the end of a slide lingers.
- `smear_s` 0.04 / `smear_max_m` 0.3: the tail reaches the car's sideways speed times 0.04 s
  behind, at most 0.3 m, and fades along its length ("like a light tail when drifting but much
  shorter to not distract", the user). A first cut at 0.12 s and 1.2 m with the tail torn into blobs
  was refused as too much.
- `city_line` is `cel_outline.tres` itself: the rim's colour is each body part's paint darkened by
  that file's `surface_darkness`, the number that makes the city's line, so the two cannot drift.

The colour does not follow the tier yet. The rim taking a colour per tier, as the sparks do, to show
the drift bonus's status is the user's next step (2026-10-07).

⚠️ The rim is grown by the body's box, not its normals (`car_outline.gdshader`'s header): a flat-
shaded car's faces part along their normals. On the raked screens the rim runs a few millimetres
off the body.
