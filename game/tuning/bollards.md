# bollards.tres

Rationale for `game/tuning/bollards.tres` (`Q119`).

Footway bollards: the railing layer's `bollard0..3`, as their own class (`Q61`). Same shader as
`railings.tres`; the mask numbers are the whole difference: wide uprights at a wide pitch, no
balusters, no rails. A bollard is a flat masked quad, `cull_disabled`, not a round post.

- `rail_colour` 0.43 grey: the fence's galvanised steel, darker so the two do not read as one
  object. A value difference, not a hue one.
- `rail_metallic` 0.0: the only environment is sky, so a metallic rail renders sky blue (`P3-14`).
- `sky_zenith`, `sky_horizon`, `ground_reflection`, `rail_reflect`, `rail_face_on`,
  `fresnel_power`: `railings.tres`'s sheen and values (`Q168`).
- `baluster_width_m` 0.0, `top_rail_m` and `bottom_rail_m` `(0, 0)`, `skirt_top_m` 0.0: off. Zero
  width and zero-height bands are the shader's "off" convention.
- `post_pitch_m` 1.5, `post_width_m` 0.16: the bollard itself, authored. No source carries spacing
  or diameter: `SYMBOL_STEP_1` / `SYMBOL_SIZE_1` are plot sizes, and no bollard feature populates
  them (`Q60`).
