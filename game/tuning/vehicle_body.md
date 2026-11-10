# vehicle_body.tres

Rationale for `game/tuning/vehicle_body.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The taxi's body material — clearcoat over a sky gradient.

`tools/generated_scene_import.gd` maps the ETL's `vehicle_body` material name
to this path and only this path, so this file is the switch: delete the entry
there and the body falls straight back to the `BaseMaterial3D` it imported
with before `P3-11c`, with no rebuild.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants — and beside `golden_hour.tres`, because the sun these are
judged under is tuned in the same directory.

⚠️ **`paint_reflect` and `paint_roughness` are the gloss dial, and it is
priced.** Measured on the red bodywork at `taxi` t04.50, at `fresnel_power`
4.0: matte `C* 79.06`, `0.12`/`0.9` gives 73.65, `0.12`/`0.55` gives 69.86 —
roughly linear in between. The shipped car reads **71.63**, because
`fresnel_power` 6.5 refunds 1.77 of the cost.

⚠️ **`fresnel_power` is not a free knob in the other direction.** Lowering it
broadens the reflection toward the ablated case, where the paint loses a
further `C* 13.75` — fresnel is what keeps the clearcoat off a panel facing
the camera, not a decoration on top of it. Backing it off is a one-file change with no rebuild,
and it is the **first** thing to try if `P3-9a` recognition scores poorly,
because a washed red is the axis that gate measures.

⚠️ **`glass_reflect` went 0.34 → 0.14 → 0.45, and the middle value is the one
worth understanding.** At 0.34 against a single flat `sky_reflection` colour the
backlight came back at `C* 21` and read as a panel painted blue, so it was cut
to 0.14 — which the user then judged from the driver's seat as barely
different, correctly. Both readings were right, and neither was about strength:
a flat colour is a swatch at *every* value, faint at 0.14 and painted-on at
0.34. `ART_DESIGN.md` had already recorded exactly this against the facades —
"a single reflection colour is why glass read as a swatch rather than a mirror".
With the sky *gradient* in (zenith / horizon / ground, chosen by the reflected
ray's own elevation) the surface has structure to show, and it can carry 0.45
without flattening — because what lands is no longer one colour.

⚠️ **`lamp_emission` is above 1.0 because the glow threshold is 1.0.**
`clean_daylight.tres` blooms on HDR over 1.0, so a lit lens under that is a
brighter swatch and not a lamp — the bloom is what separates the red brake
lens from the red bodywork it is seated in, which is the whole reason the
circuits exist (`P3-11d`).

⚠️ **Turning it up buys bloom and spends redness, and by 1.2 it is spending
nothing else.** The tonemap is ACES and the lens's red channel is clipped at
255 from 1.2 upward, so every further unit lands on green and blue — a lamp
that goes whiter rather than brighter. Measured on the high-level strip, same
294 px, braking at `t03.30`: ablated `L* 2.29 / C* 9.35`, then 1.2 →
`67.04 / 56.44`, **1.6 → `72.72 / 44.34`**, 2.3 → `79.17 / 31.81`. Shipped at
the knee. Going up is how the tail cluster becomes the white tail lamp
`ART_DESIGN.md` has refused twice already.

The circuits themselves are **not** here — they are per-instance state written
by `scripts/vehicle/vehicle_lamps.gd`, because this file is shared by every
vehicle and one car braking must not brake the rest of the roster.

Judged on the two `taxi` audit frames — `t01.20` in shade, `t04.50` in sun —
per `ART_DESIGN.md`'s viewpoint table.

## cabin_light, cabin_glow, cabin_glow_dim

A saloon lit behind its windows at night (`Q177`), multiplied by the rig's `night_lights`, so it is
the plain glazing by day. `cabin_glow` 0.25 is the bus and the tram, `cabin_glow_dim` 0.12 the
minibus, whose saloon is dimmer on the street (the user, 2026-11-01). Both sit well under the 1.0
glow threshold: a lit room, not a lamp. 0.9 and 0.4 were shot first and refused as too bright, and
the first colour, `(1, 0.93, 0.76)`, read as a cream panel rather than a light.

## ink_width_m, ink_max_px, ink_darkness, ink_speed_thin, ink_speed_fade

The detail lines (`P3-84`, `Q196`, the user's report, 2026-11-11: "there is no lines in vehicle
details"). The city's outline reads depth, so on a vehicle it draws the silhouette and the folds
and nothing else: a window, a livery band or a lens is a change of colour on one flat panel.
`tools/vehicle_ink.py` marks those edges in the mesh and this shader draws them.

- `ink_width_m` 0.02 is a width on the vehicle, in metres, so the line is bold on a near car and
  thins with distance — the user's first question was whether vehicles should have lines bolded by
  distance. Under a pixel it is held a pixel wide and faded by its true width. `ink_max_px` 4.0
  stops it swelling on a car against the lens.
- `ink_darkness` 0.35 scales the surface's own colour, as the city's line does at 0.5. Darker than
  the city's because the line lies inside the detail: a 0.5 line on dark glass does not read.
- `ink_speed_thin` 0.33 / `ink_speed_fade` 0.2 take the same share off the line at the player's
  full speed as `cel_outline.tres` takes off the city's (1.5 px to 1.0 px, 80% strength), on the
  same `outline_speed` global. It is the player's speed, not each vehicle's own.

Rendered at 0.012 / 0.5, 0.02 / 0.35 and 0.03 / 0.2 beside no line; 0.02 / 0.35 is the middle of
that sheet and ⚠️ **not yet the user's pick**. At 0.012 the line is barely there; 0.03 is the only
one that still reads on a tram at 115 kph. A black panel takes no darker line at any weight.

⚠️ `global uniform float outline_speed` must be declared OUTSIDE a `group_uniforms` block. Inside
the `ink` group it compiled without an error and the city's façades drew with wrong colours.
