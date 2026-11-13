# clean_daylight.tscn

Rationale for `game/scenes/world/clean_daylight.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The lighting rig for the clean facade look — midday rather than golden hour.

The alternative to `golden_hour.tscn`, and the same shape: one Environment
resource plus one sun, instanced by every scene that needs to be looked at.
Which rig ships is one `ext_resource` line in each dev scene, and **both must
name the same one** — the city getting judged under two looks at once is what
that file's header warns against, and splitting the rigs does not change it.

⚠️ **A low warm sun is load-bearing for the *other* look and not for this one.**
Golden hour flatters flat shading by raking across faces; a white city under a
low sun goes to two values, blown and blue, with the massing lost between them.
The sun here is at 48° for the same reason the reference art's is: it separates
the faces by shading rather than by shadow, and leaves the long shadows to be
something the street furniture casts rather than the whole skyline.

## `[node name="Sun" type="DirectionalLight3D" parent="."]`

`directional_shadow_mode = 1` is SHADOW_PARALLEL_2_SPLITS, and 400 m is the
chase camera's far plane. Both carried over unchanged from `golden_hour.tscn`,
which measured them — see its header for the per-cascade primitive counts and
the three artefacts that ruled out a single cascade. Nothing about raising the
sun changes that argument, and re-deriving it here would only let the two rigs
drift apart.

## `phone_shadow_max_distance_m = 100.0`

On a phone the sun's shadows reach 100 m, not the `Sun`'s 400 (`P2-6`, the user's pick
2026-11-14); `LightingRig.fit_shadow` writes it at `_ready`, and nowhere else is touched. Both
cascades stay. The shadow map is one size whatever it covers, so the first cascade's 10% is 10 m
of ground, not 40: on the desktop's 4096 map the near shadows came out crisper than at 400 m, and
the 2048 map a phone uses (Godot's `.mobile` default) needs that more. Measured at 4a41de7c on the
desktop, traffic on: −26 / −24 / −29 draws and −17% / −17% / −16% primitives at the start line,
Hennessy Road and Times Square. One cascade at 100 m saved more primitives (−33% to −37%) for
fewer draws (−18 to −20), and the user took the draws and the sharper look.

⚠️ The cost is `golden_hour.md`'s 150 m artefact at 100: `directional_shadow_fade_start` is 0.8 of
the reach, so shadows fade out 80–100 m ahead and a long sunlit street is flat past that. Graded
by eye on the handset, not here. Both rigs carry it, for the reason the `Sun` block gives.

## `[node name="CelOutline" type="MeshInstance3D" parent="."]`

The ink line of the cel look (`P3-64`, `Q158`): a 2 x 2 quad that `cel_outline.gdshader` puts
straight onto the screen, numbers in `tuning/cel_outline.tres`. In the rig because the rig is what
every scene worth looking at instances, so one switch inks all of them. **`visible` is the switch**:
shown since 2026-10-07, the user's pick; hidden restores the unlined look. `extra_cull_margin` keeps the quad from being
frustum-culled at its true position (it has none), and `cast_shadow = 0` keeps it out of the shadow
pass. Both rigs carry it alike, for the reason the `Sun` block gives.

## `cycle = ExtResource("4_cycle")`

The day this rig runs through (`Q160`): `tuning/day_to_night.tres`, whose sidecar has the table.
On this rig and not on `golden_hour.tscn`, because this is the one the drive instances. 🔴 **The
rig moves only when something sets `time_of_day`** — `city_drive.tscn`'s `DayClock`, or
`--time-of-day=` for a frame — so the two dev scenes that instance this rig with no clock render
the noon they always did, and `verify_day_cycle.gd` holds that a rig at 0 writes nothing.
