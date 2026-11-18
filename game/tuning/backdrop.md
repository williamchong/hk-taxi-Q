# backdrop.tres

A region's far version's material (`P3-100`, `Q249`): `BACKDROP_MATERIAL` in
`etl/pipeline/backdrop.py`, dispatched by `tools/generated_scene_import.gd`. `backdrop.gdshader`:
the blocks' and the ground's colours are on the vertex from `materials:`, and the shader adds the
rig's exposure, draws past the camera's far plane and skips every fragment nearer than
`street_far_m` from the eye, where the region's own tiles stand.

- `street_far_m = 400.0`: the drive camera's `far` (`city_drive.tscn`), restated because a shader
  cannot read it. `verify_backdrop.gd` holds the two together. Also the near skip's radius: the
  streamer loads every tile within 400 m (`streaming.tres`), so nearer than that the real city
  stands, and the far version's simplified blocks would show round it.
- `pin_band_m = 8.0`: the far shore is drawn in the street's last 8 m of depth, so only a street
  object 392 m or more from the camera can be drawn over by it. Wider gives a 24-bit depth buffer
  more to order the skyline's own walls with, and puts more of the street behind Kowloon.
- `pin_from_m = 500.0`: the true distance that lands on the band's near edge. A far version between
  400 and 500 m lands in front of the band, among the last 10 m of the street's depth: where it
  meets a real building there it is the same building. The far sea is nearer still, from the quay,
  and lands in front of the band where only more sea is.
- **`water.tres` carries the same three numbers** for the far sea, which is drawn by the water's
  own material. `verify_backdrop.gd` refuses a pair that differs.
- A block left on its imported `BaseMaterial3D` is culled at the far plane and draws nothing, so
  `verify_backdrop.gd` checks the dispatch by `resource_path`.
- `night_spot_strength = 0.55` (`Q252`, the user's pick from 0 / 0.35 / 0.55 / 1.0 / 2.0): Wan
  Chai's floodlight strength (`city_facade.tres`). 0 is `Q249`'s dark skyline. The colour, share
  0.6, reach 120 m and top 0.3 are the shader's defaults and Wan Chai's values; a wall is drawn
  lit or dark by its own plane, since the mesh carries no building.
- `wall_normal_max` (default 0.3) caps at 0.9 so a roof is never a wall.
- `roughness_value = 0.9`: matte.
