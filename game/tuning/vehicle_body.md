# vehicle_body.tres

Rationale for `game/tuning/vehicle_body.tres`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

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
