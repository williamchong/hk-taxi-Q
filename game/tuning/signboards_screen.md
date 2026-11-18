# signboards_screen.tres

The signboards' screens (`P3-103` step 3, `Q260`): `SCREEN_MATERIAL` in
`etl/pipeline/signboards.py`, dispatched by `SHADERS` in `tools/generated_scene_import.gd`. The
boards are the authored `signboards.screens` ids; the loop is generic and carries no brand.

- `pixel_m` 0.3: an LED pitch at street scale, read in metres off the face's UVs, so every screen
  shares it. Where an LED is smaller than a pixel the dot grid fades to its mean.
- `drift` 0.25 and `slide_s` 7.0: the field moves slowly and cuts to a new direction and scale every
  seven seconds, offset per screen by the `COLOR_0` seed.
- `gap_dark` 0.45: how dark the gaps between LEDs read up close.
- `day_glow` 1.2 / `night_glow` 2.2: a screen is a light, so it emits by day too; at night it burns
  brighter, blended by the rig's `night_lights`. Under the glow pass's 3.0 threshold.
- Squared colour (`colour * colour`): deeper, more saturated hues than the raw cosine palette, which
  read washed out by day.
