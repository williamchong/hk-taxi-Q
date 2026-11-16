# golden_hour.tscn

The alternative rig: a low warm sun (30°) over `tuning/golden_hour.tres`. Same shape as
`clean_daylight.tscn`, which is the one the game and the dev scenes instance. No `cycle`, and
`phone_scale_3d` is unset (1.0). `exposure_anchor`, `phone_shadow_max_distance_m` and `CelOutline`
are as in `clean_daylight.md`; keep the two rigs alike.

## `Sun`

`directional_shadow_mode = 1` is `SHADOW_PARALLEL_2_SPLITS` (the scene stores the bare integer).
Godot's default is four cascades.

| Cascades | Primitives at t = 1 / 3 / 6 s from the HKCEC spawn |
|---|---|
| 4 (default) | 244,888 / 215,071 / 263,077 |
| 2 | 159,739 / 132,845 / 155,032 (−35%) |
| 1 | 110,644 / 93,206 / 112,142 (−55%), unusable |

One cascade has an artefact at every `max_distance`: at 150 m shadows fade out while the camera
draws to 400 m; at 250 m the HKCEC shadow bands on the map's own texels; at 400 m it disappears
because the caster falls outside the ortho volume. `directional_shadow_fade_start` is a fraction
of the distance (0.8), so shortening it moves the fade band too. Two cascades removes all three.

`directional_shadow_max_distance = 400.0` is the chase camera's far plane and the streamer's
unload distance. Distance itself costs nothing (150 to 600 measured identical). Bias, pancake,
blur and fade are engine defaults.
