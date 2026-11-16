# clean_daylight.tres

Rationale for `game/tuning/clean_daylight.tres` (`Q119`).

The high-key daylight environment, named by `scenes/world/clean_daylight.tscn`. It is the authored
day of the cycle (`day_to_night.md`) and the 15:00 and 17:00 keyframes' environment.
`golden_hour.tres` is the alternative rig's.

- Sky colours: a pale horizon under a deep top. The sky lights every unshadowed surface, so the
  cool shadows are tuned here, not in a material.
- `ambient_light_sky_contribution` 0.4, `ambient_light_color` `(0.82, 0.8, 0.76)`,
  `ground_bottom_color` `(0.5, 0.48, 0.45)` (`Q215`, the user's call): a street's shade is lit by
  its buildings as much as by the sky. A higher sky share turns the shaded asphalt, railings and
  parked cars blue; a neutral, lower one flattens the massing, because the cool shadow separates
  one pale face from the next. Judge `skyline` beside `street` before moving either.
- Glow: bloom on over-range pixels only. A lower threshold blooms the whole pale city.
- Fog: depth fog (the Mobile renderer has no volumetric fog). `fog_density` 0.00025 reaches about
  a quarter at the 400 m far plane; doubling it hides the city.
- `adjustment_saturation` 1.1 is why `adjustment_enabled` is true. `adjustment_contrast` is the
  default 1.0, so the writer omits it, and it must stay there (`Q31`): Godot pivots contrast about
  mid-grey, and 1.14 clipped every value below sRGB 15.7/255 to black. The shaded road stays flat
  at any setting; that wants the sky-visibility bake (`Q39`).
