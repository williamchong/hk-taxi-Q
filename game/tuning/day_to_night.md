# day_to_night.tres

Rationale for `game/tuning/day_to_night.tres` (`Q119`).

The day that runs to night as game time passes (`Q160`), read by `scripts/world/lighting_rig.gd`
off `clean_daylight.tscn`'s `cycle` and driven by `scripts/world/day_clock.gd`. No `@export` in
`rig_cycle.gd` or `rig_keyframe.gd` declares a default (`Q150`), so a key absent from a keyframe is
0 (`at`, `sun_energy`, `night_lights`).

The authored day is not in this file. The rig scene as authored (`clean_daylight.tres`, its `Sun`)
is the look at `day_at`, read off the scene. A rig nobody moves is resting and writes nothing;
`DayClock` rests it (`LightingRig.rest()`) for every run that holds the daylight.
`verify_day_cycle.gd` holds that.

- `length_s` 840: game seconds of driving from 07:00 to 21:00, and the length of 特更 (`Q162`);
  `shift.tres` holds the hours and takes its length from here. One second driven is one minute on
  the clock (`Q233`): 14 hours x 60. Game time; the clock stops under the start menu.
- `day_at` 0.174 (09:26): where the authored scene stands on the cycle. Solved, not picked: the
  authored sun's angle before noon at the daylight speed. Move noon, dusk or their `at`s and this
  moves with them.
- `loop_at` 1.714 (`Q225`): where a free drive's day comes round to 07:00, 24 hours on the scale
  where 1.0 is the shift's 14, so the night runs at the day's pace. A shift never passes 1.0;
  `DayClock` caps it and only a free drive wraps. 0 would hold the last keyframe.
- `update_hz` 10: how often the rig is moved. Each move re-renders the sky's radiance, so it is
  the cost lever. About 0.15 ms a frame on an iPhone Air (`Q222`); the floor handset is not
  measured.

## The keyframes

| `at` | Look | Key light | `sky_light` | `night_lights` |
|---|---|---|---|---|
| 0.00 (07:00) | `morning.tres` | 16.6° up in the SSE, `(0.92, 0.95, 1)`, 0.70 | `(0.88, 0.94, 1)` | 0 |
| 0.174 (09:26) | the rig scene, in no keyframe | 48° up in the SSE, `(1, 0.98, 0.95)`, 0.90 | white | 0 |
| 0.36 (12:00) | `noon.tres` | 80° up, due south, `(1, 1, 0.98)`, 2.20 | white | 0 |
| 0.57 (15:00) | `clean_daylight.tres` | 47.2° up in the WSW, the day's colour, 0.90 | white | 0 |
| 0.71 (17:00) | `clean_daylight.tres` | 22.3° up in the WSW, `(1, 0.9, 0.76)`, 0.88 | `(1, 0.95, 0.88)` | 0 |
| 0.79 (18:00) | `dusk.tres` | 8° up in the WSW, `(1, 0.82, 0.34)`, 0.80 | `(1, 0.9, 0.54)` | 0.25 |
| 0.86 (19:00) | `twilight.tres` | on the horizon, 0.00 | `(0.3, 0.3, 0.45)` | 0.80 |
| 0.93 (20:00) | `night.tres` | the moon, 38° up, `(0.62, 0.72, 1)`, 0.30 | `(0.1, 0.11, 0.18)` | 1.00 |
| 1.464 (03:30) | `night.tres` | the moon, 10° up in the west, 0.30 | night's | 1.00 |
| 1.536 (04:30) | `night.tres` | the moon on the western horizon, 0.00 | night's | 1.00 |
| 1.607 (05:30) | `twilight.tres` | the sun on the SSE horizon, 0.00 | twilight's | 0.80 |
| 1.661 (06:15) | `dawn.tres` | 7° up in the SSE, `(0.8, 0.86, 1)`, 0.60 | `(0.7, 0.82, 1)` | 0.25 |

- The hours are 特更's clock (`Q162`): a keyframe's `at` is its hour over the shift's 14-hour span.
- By day the angle moves at one speed (`Q222`): the rig slerps the direction to the light, and the
  daylight keyframes sit on two great circles that meet at noon, with angles and `at`s solved so
  every leg runs at 0.216 °/s. `verify_day_cycle.gd` holds the legs within 2% of each other, so
  never move one keyframe's angle or `at` alone; re-solve the leg. This is why the 07:00 sun is in
  the SSE, not the east.
- Colours fade on a smoothstep between keyframes (environments, light colour and energy, both
  globals). The angle alone is linear.
- Noon is the brightest and the highest (2.20, the user's pick), and `verify_day_cycle.gd` holds
  that the two coincide. 80° and not 90°: `looking_at` has no roll for a vertical light, and a
  wall under an overhead sun takes no key light.
- 15:00 and 17:00 reuse the day's environment; only the sun moves there.
- One `DirectionalLight3D` is both sun and moon. The zero-energy keyframes (19:00, 04:30, 05:30)
  exist so it can change hands unseen. `verify_day_cycle.gd` holds that the widest swing between
  two keyframes is on a leg dark at both ends.
- Night dims the key light and never deletes it: `VehicleLamps.read_rig` reads a missing sun as
  "no rig". The moon's 0.30 sits under `vehicle_lamps.tres`'s `night_energy` 0.40; the two move
  together and `verify_day_cycle.gd` holds the pair.
- The rows past 1.0 are the free drive's night and dawn (`Q225`); the last leg blends back to the
  07:00 row across `loop_at`, at the daylight speed. A shift's 21:00 is the same night, 13% of the
  way from the 20:00 moon to the 03:30 one.
- `night_lights` is the dial every lit layer multiplies its own strength by: lanterns and pools
  (`lamps.tres`, `lamp_pools.tres`), floodlights (`city_facade.tres`), road paint
  (`paint_night_glow`), the outline (`cel_outline.tres`). 0.25 at dusk is the lamps coming on
  before the light has gone.
- `exposure_anchor` is not here and must not be: it scales `COLOR_0` alone, so the dark comes from
  the light.
- Every keyframe environment's `Sky` carries `radiance_size = 0` (`Q225`): a loaded `Sky`
  allocates its radiance map undrawn, about 18 MB each at the default. Not `clean_daylight.tres`,
  which is drawn; a moved rig shrinks that sky itself and gives it back on `rest()`.
