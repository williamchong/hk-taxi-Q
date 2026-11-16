# dawn.tres

Rationale for `game/tuning/dawn.tres` (`Q119`).

The 06:15 look on a free drive's lap (`Q225`), one of those `day_to_night.tres` blends through. A
copy of `dusk.tres` with only the blended values moved; only what `LightingRig.BLENDED` and
`BLENDED_SKY` name is read (`dusk.md`).

- Blue (`Q235`, the user's ask): a pale blue horizon under a deeper blue, with a blue ambient, fog
  and key light, so dawn is told from the yellow dusk by colour. The strength is provisional: the
  middle of three rendered, and the user has not chosen.
- `ambient_light_energy` 0.6, `fog_density` 0.0006 (dusk 0.0004), `adjustment_saturation` 1.05: a
  dimmer, mistier, paler morning, so the sunrise is not the sunset backwards.
- `radiance_size = 0` on the `Sky`: required of every keyframe environment (`day_to_night.md`).
