# clean_daylight.tres

Rationale for `game/tuning/clean_daylight.tres`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

A high-key midday environment, for the clean facade look.

The alternative to `golden_hour.tres`, and switched the same way its facade
counterpart is: `scenes/world/clean_daylight.tscn` names this one, and
`scenes/world/golden_hour.tscn` names the other. **Only one is instanced at a
time** — both dev scenes point at the same rig, because the city getting judged
under two looks at once is the thing `golden_hour.tscn` was written to prevent.

What the clean look needs that golden hour does not, and why:

- **A pale horizon and a deep top.** The sky is what a white city is lit by:
  `ambient_light_sky_contribution` means every unshadowed surface takes its
  colour from this gradient, so the cool shadows are tuned here rather than in
  any material. Golden hour's warm cream horizon is what made the road read
  dark navy against it.
- **Glow.** Bloom on the brightest surfaces is the reference look's signature
  and it is not available any other way — there is no emissive on the fabric.
  Thresholded at 1.0 so only genuinely over-range pixels bloom: a lower
  threshold blooms the whole white city into mush, which is the failure mode to
  watch for if these numbers get raised.
- **Fog.** Aerial perspective is what separates one white block from the white
  block behind it. Density is deliberately low — at the camera's 400 m far
  plane it reaches about a quarter, which is haze, and doubling it starts
  hiding the city rather than layering it.

⚠️ Volumetric fog is Forward+ only and is **not** used here; this is depth fog,
which the Mobile renderer supports. `project.godot` sets `mobile`.

## `ambient_light_source = 3`

⚠️ **`ambient_light_sky_contribution` is what colours every shadow in the
city, and at 0.9 it turned the road cobalt.** Dark albedo takes almost all of
its light from ambient, so a saturated blue sky paints the asphalt blue while
leaving the white facades — which are mostly lit by the sun — untouched. The
blend back toward a neutral `ambient_light_color` is the control for that, and
it is the one to reach for if a *surface* looks wrong rather than a *light*.

## `ambient_light_color = Color(0.8, 0.84, 0.9, 1)`


⚠️ And it is a **balance**, not a floor: at 0.55 with a neutral ambient the
road came right and the massing went flat, because the cool shadow is also the
only thing separating one white face from the next. The fix was to keep the
blend low but make what it blends toward cool rather than neutral — shadow
colour without sky saturation.

## `adjustment_enabled = true`

⚠️ **A contrast pivot is a black-clipper, not a dimmer.** Godot pivots about
mid-grey — `v' = (v - 0.5) * contrast + 0.5` — which extrapolates past the
endpoints, so at 1.14 every value below sRGB **15.7/255 lands on exactly 0**
and the information in it is gone. `Q31` measured the consequence and it was
the dominant term in the city's value distribution, ahead of ambient, glow,
fog, the tonemap and the palette. 1.14 → 1.00 lifts the shadow mass **+6.1
`L*`** on all three frames it was failing on — `kerb` 4.42 → 10.51, `taxi`
t01.20 4.59 → 10.67, chase t03.00 4.32 → 10.37.

⚠️ **Do not quote `Q31`'s 51.3% → 0.9% as the expected result.** Re-shot on
this build the same change gives 51.0% → **29.0%**, and neither number is
wrong: the lifted mass lands within half a point of the `L*` 10 band edge, so
a band share on a near-constant surface is a coin toss. That fragility is
`Q31`'s own argument for grading **within-mass sd** instead — which barely
moves here (0.92 → 0.99), because the lift is a translation. **The shaded road
is still flat, and no setting of this dial can change that**: it is one
flat-shaded surface of uniform albedo and normal under uniform ambient, and no
monotone function of a constant produces variation. That wants the
sky-visibility bake, `Q39`.

`adjustment_enabled` stays `true` — `adjustment_saturation` is still 1.1, so
this is not a no-op block to switch off.
