# vehicle_body.tres

The shared body material of every vehicle: the taxi, the traffic and the parked library.
`tools/generated_scene_import.gd` maps the `vehicle_body` material name to this file. Lamp
circuits are not here: they are per-instance state written by `vehicle_lamps.gd`, because one car
braking must not brake the rest.

- `sky_zenith`, `sky_horizon`, `ground_reflection`: the painted sky the glazing and lenses
  reflect, chosen by the reflected ray's elevation. A single flat colour read as a painted swatch
  at every strength.
- `glass_reflect = 0.45`, `glass_face_on = 0.25`, `fresnel_power = 6.5`, `glass_roughness = 0.14`:
  the glazing. `fresnel_power` shapes glass and lenses only; paint takes the engine's fresnel.
- `lamp_roughness = 0.35`, `lamp_reflect = 0.06`: the lenses unlit.
- `lamp_emission = 1.6`: over 1.0 because the glow threshold is 1.0; the bloom is what separates a
  red brake lens from red bodywork (`P3-11d`). Not higher: the red channel clips from 1.2 up, so
  more goes to green and blue and the lamp whitens (`C*` 56.4 at 1.2, 44.3 at 1.6, 31.8 at 2.3).
- `paint_roughness = 0.55`, `clearcoat = 1.0`, `clearcoat_roughness = 0.12` (`Q215`): the paint's
  gloss is the engine's clearcoat lobe over a base coat, which leaves the albedo's red alone.
  Mixing the sky into the albedo cost chroma. `clearcoat` 0 is the matte car and the first thing
  to try if `P3-9a` recognition scores poorly.
- `sun_toward`, `glint_strength = 0.4`, `glint_sharpness = 24.0`: the sun's glint on glass and
  lenses. `sun_toward` is fed at runtime by `sun_glint.gd` from the rig; the stored value is a
  placeholder. Not on paint: the clearcoat has its own sun lobe.
- `cabin_light`, `cabin_glow = 0.25`, `cabin_glow_dim = 0.12` (`Q177`): a saloon lit behind its
  windows, times the rig's `night_lights`. 0.25 is the bus and the tram, 0.12 the minibus (the
  user's call). Well under the glow threshold: a lit room, not a lamp. 0.9 and 0.4 were too
  bright.
- `ink_width_m = 0.02`, `ink_max_px = 4.0`, `ink_darkness = 0.35`, `ink_speed_thin = 0.33`,
  `ink_speed_fade = 0.2` (`P3-84`, `Q196`): detail lines on the edges `tools/vehicle_ink.py`
  marks, since the city's depth outline draws only silhouettes and folds. Width is in metres on
  the vehicle (held at a pixel minimum and faded, capped at `ink_max_px`). Darkness scales the
  surface's own colour. The speed pair matches `cel_outline.tres` on the `outline_speed` global.
  The model's pick from a sheet; the user's is owed.
  - `global uniform float outline_speed` must be declared outside any `group_uniforms` block.
    Inside one it compiled and the façades drew with wrong colours.
- `relief_groove_m = 0.02`, `relief_groove_slope = 1.2`, `relief_pillow = 0.04`,
  `relief_edge_m = 0.03`, `relief_edge_slope = 0.6` (`P3-87`, `Q232`): pressed panels by tilting
  `NORMAL`, no texture. Grooves sit at the pitches `tools/make_parked.py` gives a kind
  (`joints_m`, `crease_y_m`, `box_ribs_m`). `relief_pillow` bows a panel between joints so a far
  bus keeps some shape; 0.04 is the user's pick (0.08 read as quilting). The edge pair seats a
  pane in its frame and must be wider than the ink. Every slope at 0 is flat sheet. The groove and
  edge values are the model's; the user's pick is owed.
