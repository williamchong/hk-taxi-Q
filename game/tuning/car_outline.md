# car_outline.tres

Rationale for `game/tuning/car_outline.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The outline's answers to the car (`P3-65`, `Q158`, the user's ask, 2026-10-07): the city's line
thins and fades with speed, and while a slide counts the end of the car moving most leaves an
afterimage in its own outline colour.
Read by `CarOutline` on `taxi_tyre.tscn`; what the line does with the speed is `cel_outline.tres`'s
`speed_thin_px` and `speed_fade`.

- `full_speed_kph` 120: where `outline_speed` reaches 1 and the line is at its thinnest and faintest. The user
  asked to compare at rest, 60 and 120 kph, and 120 is the top of that range. Above it the line holds.
- `hull_width_m` 0.06, `drag_from` 0.3, `ghost` 0.35: the afterimage hangs off the end of the car
  moving most across its length — in a slide, the tail swinging out — picked each tick from the two
  ends' point velocities, the car's yaw included ("only drag the end of car which moves most
  instead of whole car rim as afterimage", the user, 2026-10-07). It starts 30% of the way from
  the middle to that end, is 0.06 m wide at the end, and fades to 35% at its tip, so it reads as a
  ghost of the car (飄移殘影). The rest of the car keeps only the city's line. Before it, a rim
  ran round the whole car — first 0.03 m to 0.09 m by tier ("sudden bold"), then 0.03 m with up to
  0.04 m more on the trailing side — and both were turned round.
- `rim_colour` `#c62028`, `make_vehicle.py`'s `RED`: the afterimage is one colour, the paint
  darkened by `city_line`'s `surface_darkness` — the colour the city's line draws the car's edge. A
  cut drawn in each part's own colour ghosted the lamps, glass and bumper too: "having the whole car
  body as after image is strange, can we just do outline color for the car outermost rim", then
  "skip the details" (the user, 2026-10-07).
- `seep_s` 0.25 / `drain_s` 0.6: the time constants of the ease in and out. The afterimage never
  arrives or leaves in a step; it drains slower than it seeps, so the end of a slide lingers.
- `smear_s` 0.04 / `smear_max_m` 0.15: the afterimage's tip reaches that end's sideways speed times
  0.04 s behind it, along that end's own motion, at most 0.15 m (0.3 m read as a second car), fading to `ghost` at its tip ("like
  a light tail when drifting but much shorter to not distract", the user). A first cut at 0.12 s
  and 1.2 m with the tail torn into blobs was refused as too much.
- `city_line` is `cel_outline.tres` itself, for its `surface_darkness`: the number that makes the
  city's line darkens the afterimage too, so the two cannot drift.

The colour does not follow the tier yet. The afterimage taking a colour per tier, as the sparks do, to show
the drift bonus's status is the user's next step (2026-10-07).

⚠️ The afterimage is grown by the body's box, not its normals (`car_outline.gdshader`'s header): a flat-
shaded car's faces part along their normals. On the raked screens it runs a few millimetres
off the body.
