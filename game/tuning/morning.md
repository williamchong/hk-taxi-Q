# morning.tres

Rationale for `game/tuning/morning.tres` (`Q119`).

The 07:00 look (`Q222`), the shift's opening hour, one of those `day_to_night.tres` blends
through. A copy of `clean_daylight.tres` with only the blended values moved; only what
`LightingRig.BLENDED` and `BLENDED_SKY` name is read (`dusk.md`).

- A pale warm horizon under the day's blue, a lower ambient (`ambient_light_energy` 0.7) and a
  slightly thicker, sunlit haze (`fog_sun_scatter` 0.2). Provisional: picked from frames, not yet
  driven by the user.
- `radiance_size = 0` on the `Sky`: required of every keyframe environment (`day_to_night.md`).
