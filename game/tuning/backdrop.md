# backdrop.tres

The far shore's material (`P3-100`, `Q249`): `BACKDROP_MATERIAL` in `etl/pipeline/backdrop.py`,
dispatched by `tools/generated_scene_import.gd`. `backdrop.gdshader`: the blocks' and the ground's
colours are on the vertex from `materials:`, and the shader adds the rig's exposure and draws past
the camera's far plane.

- `street_far_m = 400.0`: the drive camera's `far` (`city_drive.tscn`), restated because a shader
  cannot read it. `verify_backdrop.gd` holds the two together.
- `pin_band_m = 8.0`: the far shore is drawn in the street's last 8 m of depth, so only a street
  object 392 m or more from the camera can be drawn over by it. Wider gives a 24-bit depth buffer
  more to order the skyline's own walls with, and puts more of the street behind Kowloon.
- `pin_from_m = 500.0`: the true distance that lands on the band's near edge. The skyline is never
  nearer (`backdrop.json`'s `gap_m`); the far sea is, from the quay, and lands in front of the band
  where only more sea is.
- **`water.tres` carries the same three numbers** for the far sea, which is drawn by the water's
  own material. `verify_backdrop.gd` refuses a pair that differs.
- A block left on its imported `BaseMaterial3D` is culled at the far plane and draws nothing, so
  `verify_backdrop.gd` checks the dispatch by `resource_path`.
- Unlit at night (`Q160`).
- `roughness_value = 0.9`: matte.
