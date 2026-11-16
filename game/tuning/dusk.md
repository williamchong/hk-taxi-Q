# dusk.tres

Rationale for `game/tuning/dusk.tres` (`Q119`).

The 18:00 look (`Q160`), one of those `day_to_night.tres` blends through. A copy of
`clean_daylight.tres` with only the blended values moved.

- Only what `LightingRig.BLENDED` and `BLENDED_SKY` name is read from a keyframe environment: the
  ambient, the fog, the glow's intensity, the saturation and the sky's four colours. The switches,
  tonemapper and glow levels are the day's, carried unread. A property that should move with the
  hour is added to those lists first.
- Yellow (`Q235`, the user's ask): the horizon, fog and ambient, under a grey-blue zenith, so the
  evening is told from the blue dawn by colour. The strength is provisional: the middle of three
  rendered, and the user has not chosen.
- `fog_sun_scatter` 0.25: the fog thick with the low sun.
- `radiance_size = 0` on the `Sky`: required of every keyframe environment (`day_to_night.md`).
