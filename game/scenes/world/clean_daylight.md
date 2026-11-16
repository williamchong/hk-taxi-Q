# clean_daylight.tscn

The lighting rig the drive and every dev scene instance: one `LightingRig` root, one Environment
(`tuning/clean_daylight.tres`), one sun and the ink line. All scenes that are looked at must name
the same rig, or the city is judged under two looks.

- `exposure_anchor = 0.52`: the linear scale on every `COLOR_0` albedo (`Q33`). The ETL publishes
  `materials:` at reflectance level and this scales them; both halves move together, guarded by
  `city.json`'s `schema_version`. It does not move with the hour (`Q160`).
- `cycle`: `tuning/day_to_night.tres` (`Q160`); its sidecar has the table. The rig moves only when
  something sets `time_of_day`: `city_drive.tscn`'s `DayClock`, or `--time-of-day=` for a frame.
  Dev scenes with no clock render the authored day, and `verify_day_cycle.gd` holds that a rig at
  0 writes nothing.
- `phone_shadow_max_distance_m = 100.0` (`P2-6`, the user's pick): on a phone the sun's shadows
  reach 100 m, not 400; `LightingRig.fit_shadow` writes it at `_ready`. Both cascades stay. Desk
  measurement: −24 to −29 draws and −16% to −17% primitives at three views, with crisper near
  shadows on the phone's 2048 map. Cost: `directional_shadow_fade_start` is 0.8 of the reach, so
  shadows fade out 80–100 m ahead. One cascade saved more primitives but fewer draws.
- `phone_scale_3d = 0.75` (`P2-6`, `Q236`): the share of the window the 3D scene is drawn at in a
  phone's app; `LightingRig.fit_scale` writes `scaling_3d_scale`, and the HUD stays at full
  resolution. 56% of the pixels; on the iPhone Air video memory went 358.9 MB → 270.4 MB. Small
  sign plates and the roof sign's lettering blur and the ink line thickens by about a third; the
  user accepted it. The app only, never a phone's browser (`Handset.is_app`): the web renderer
  came out stair-stepped. Move it only with a `--perf-log` run on the device before and after.
- `Sun`: a high sun (48°), so a pale city's faces separate by shading; a low sun on white
  buildings goes to two values. `directional_shadow_mode = 1` is two PSSM splits and 400 m is the
  chase camera's far plane; `golden_hour.md` has the measurement behind both.
- `CelOutline` (`P3-64`, `Q158`): a 2 × 2 quad that `cel_outline.gdshader` puts on the screen,
  numbers in `tuning/cel_outline.tres`. `visible` is the switch (shown, the user's pick).
  `extra_cull_margin` stops it being frustum-culled and `cast_shadow = 0` keeps it out of the
  shadow pass.
