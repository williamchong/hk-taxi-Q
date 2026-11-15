# day_to_night.tres

Rationale for `game/tuning/day_to_night.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The day that runs to night as game time passes (`Q160`, the user's ask, 2026-10-07), read by
`scripts/world/lighting_rig.gd` off `clean_daylight.tscn`'s `cycle` and driven by
`scripts/world/day_clock.gd` in `city_drive.tscn`. It reverses "the sun does not move; night is a
switch between two static rigs" on the user's instruction; `DECISIONS.md` `Q160` has the record.

🔴 **The authored day is not in this file.** The rig scene as authored — `clean_daylight.tres`, its
`Sun` — is the look at `day_at`, read off the scene, so the graded daylight numbers keep one home.
Since `Q222` (the user's asks, 2026-11-16: "can the sunlight and shine and sky color changes slowly
according to daytime? e.g. the sun should be brightest and shine directly from up top to street
level", then "can the light angle move linearly and color fades slowly") it is one MOMENT of the
cycle, with a morning before it and noon after, not a look held from the start. A rig nobody moves
is `resting` and writes nothing at all; `DayClock` rests it (`LightingRig.rest()`) for every run
that holds the daylight. `verify_day_cycle.gd` holds that.

The keyframes are picked from rendered frames (`build/driver/q160*/`, gitignored), under three of
the user's calls on the way: not "pitch dark with a neon light-blue outline", which read as
science fiction; "a more realistic night with some light-up touch"; and the buildings floodlit,
not glowing. The first table went to black with a cyan line and was withdrawn the same day.

## `length_s = 300.0`

Five minutes of DRIVING from the start to the end of the cycle, and the length of 特更 (`Q162`,
2026-10-11): `shift.tres` holds the hours, 07:00 to 21:00, and takes its length from here so the sky
and the HUD's clock end on one game second. Was 240 s (`Q160`) against `GAME_DESIGN.md`'s
three-to-five minute session; the shift is that session now, and five minutes is about five to eight
fares at 30–90 s each. Game time, not wall time — the clock stops under the start menu. Free mode
runs the same table when its option is DAY TO NIGHT, and since `Q225` runs on round `loop_at`.

## `day_at = 0.174`

Where the authored scene stands on the cycle: 09:26 on the shift's clock. Not picked — solved. The
authored sun is 48° up in the south-south-east, noon is 80° up at 0.36 and dusk 8° up at 0.79, so
the afternoon's 78.0° of arc over 0.43 sets the speed (0.604 °/game s at 300 s), and the authored
sun's 33.6° before noon puts it here. Move noon, dusk or `length_s`'s keyframes and this moves
with them. Was `day_until` 0.71 (`Q162`): the authored daylight held to 17:00 and nothing moved
before it.

## `loop_at = 1.714`

Where a free drive's day comes round to 07:00 again (`Q225`, the user's ask, 2026-11-16: "Loop the
sky in free mode", "keep at the day's pace, the shift end at 21:00 untouched"): 24 hours on the
scale where 1.0 is the shift's 14, so the night runs at the day's pace — 214 game seconds from
21:00 to 07:00, 514 a lap. 🔴 **A shift never passes 1.0**; `DayClock` caps it there and only a
free drive wraps. 0 would be a cycle that holds its last keyframe.

## `update_hz = 10.0`

How often the rig is moved. Each move re-renders the sky's radiance, so this is a cost dial. At
10 Hz over a 300 s cycle one step is 1/3000 of the way and no step is visible; a 10 s cycle driven
on `f_045` held 120 fps, 8.3 ms, through the whole blend on the desktop. **Measured on the iPhone
Air, 2026-11-16** (release, 2736x1260, `--max-fps 120`, a standing shift's first 60 s, traffic off,
sky moving against `--day-cycle=off`, alternated): 95.4–96.3 fps moving beside 96.8–97.6 held, about
0.13–0.16 ms a frame, under 1% of a 60 fps frame. Left at 10. ⚠️ One handset, the fastest we have;
the floor handset is not measured, and this is still the lever there.

## The keyframes

| `at` | Look | Key light | `sky_light` | `night_lights` |
|---|---|---|---|---|
| 0.00 (07:00) | `morning.tres` | 16.6° up in the SSE, `(1, 0.8, 0.58)`, 0.70 | `(1, 0.88, 0.76)` | 0 |
| 0.174 (09:26) | the rig scene, in no keyframe | 48° up in the SSE, `(1, 0.98, 0.95)`, 0.90 | white | 0 |
| 0.36 (12:00) | `noon.tres` | 80° up, due south, `(1, 1, 0.98)`, 1.15 | white | 0 |
| 0.57 (15:00) | `clean_daylight.tres` | 47.2° up in the WSW, the day's colour, 0.90 | white | 0 |
| 0.71 (17:00) | `clean_daylight.tres` | 22.3° up in the WSW, `(1, 0.9, 0.76)`, 0.88 | `(1, 0.95, 0.88)` | 0 |
| 0.79 (18:00) | `dusk.tres` | 8° up in the WSW, `(1, 0.62, 0.36)`, 0.80 | `(1, 0.74, 0.58)` | 0.25 |
| 0.86 (19:00) | `twilight.tres` | on the horizon, 0.00 | `(0.3, 0.3, 0.45)` | 0.80 |
| 0.93 (20:00) | `night.tres` | the moon, 38° up, `(0.62, 0.72, 1)`, 0.30 | `(0.1, 0.11, 0.18)` | 1.00 |

| 1.464 (03:30) | `night.tres` | the moon, 10° up in the west, 0.30 | night's | 1.00 |
| 1.536 (04:30) | `night.tres` | the moon on the western horizon, 0.00 | night's | 1.00 |
| 1.607 (05:30) | `twilight.tres` | the sun on the SSE horizon, 0.00 | twilight's | 0.80 |
| 1.661 (06:15) | `dusk.tres` | 7° up in the SSE, dusk's colour, 0.60 | dusk's | 0.25 |

- **The rows past 1.0 are the free drive's night and dawn** (`Q225`), and the last leg blends back
  to the 07:00 row across `loop_at`. The moon sets in the west with its energy fading to 0.00 at
  04:30; first light is 0.00 too, so the key light crosses from the western horizon to where the
  sun rises unseen — the 19:00 trick mirrored. The 06:15 sun is on the morning's own arc, 9.7°
  before the 07:00 one, so the wrap leg runs at the daylight speed. Dawn reuses `dusk.tres` and
  first light `twilight.tres`: a first table, with no look of its own yet.
- A shift's 21:00 is 13% of the way from the 20:00 moon to the 03:30 one: the same night, the moon
  a little further west.
- **The sun sets in the west-south-west** — the engine's −X is west and +Z south.
- 🔴 **By day the angle moves at ONE speed** (`Q222`): the rig slerps the DIRECTION to the light
  along the great circle between two keyframes, and the five daylight keyframes sit on two great
  circles that meet at noon — morning → authored day → noon, and noon → dusk — at angles and `at`s
  solved so every leg runs at 0.604 °/s. `verify_day_cycle.gd` holds the legs within 2% of each
  other, so a keyframe's angle or `at` cannot be moved alone: re-solve the leg (to a tenth of a
  degree). ⚠️ So the 07:00 sun is in the south-south-east, not the east: the arc through the
  authored sun and an overhead noon starts there.
- **Colours fade on a smoothstep** between keyframes — the environments, the light's colour and
  energy and both globals — so no look changes pace on the frame a keyframe passes. The angle
  alone is linear.
- **Noon is the brightest and the highest**, 1.15 against the day's 0.90, and `verify_day_cycle`
  holds that the two coincide. 80° and not 90°: `looking_at` has no roll for a vertical light, and
  a wall under an overhead sun takes no key light at all.
- 15:00 and 17:00 reuse the day's environment: only the sun moves there, and 17:00 warms it.
- 🔴 **The twilight keyframe exists so the key light can change hands unseen.** One
  `DirectionalLight3D` is both sun and moon; at 0.86 its energy is 0.0, and the swing from the
  horizon to the moon's 38° happens while it climbs from nothing. Without it the sun's disc rises
  again as it fades.
- 🔴 **Night dims the key light and never deletes it**: `VehicleLamps.read_rig` reads a missing sun
  as "no rig" and drives dark. The moon's 0.30 sits under `vehicle_lamps.tres`'s `night_energy`
  0.40 — the two move together, and `verify_day_cycle.gd` holds the pair.
- **`exposure_anchor` is not here and must not be.** It scales `COLOR_0` alone; lowering it for
  night would darken the walls while paint, fences and glass kept their day values. The dark comes
  from the light.
- `night_lights` is the one dial every lit layer multiplies its own `.tres` strength by: the
  lanterns and their pools (`lamps.tres`, `lamp_pools.tres`), the floodlights
  (`city_facade.tres`), the road paint (`paint_night_glow`) and the outline (`cel_outline.tres`).
  0.25 at dusk is the lamps coming on before the light has gone.
- The hours in brackets are 特更's clock (`Q162`): each keyframe is the shift's hour over its
  14-hour span. Moving a keyframe here moves the hour it lands on, and the hour is what the player
  reads.
