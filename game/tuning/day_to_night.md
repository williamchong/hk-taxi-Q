# day_to_night.tres

Rationale for `game/tuning/day_to_night.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The day that runs to night as game time passes (`Q160`, the user's ask, 2026-10-07), read by
`scripts/world/lighting_rig.gd` off `clean_daylight.tscn`'s `cycle` and driven by
`scripts/world/day_clock.gd` in `city_drive.tscn`. It reverses "the sun does not move; night is a
switch between two static rigs" on the user's instruction; `DECISIONS.md` `Q160` has the record.

🔴 **The day is not in this file.** The rig scene as authored — `clean_daylight.tres`, its `Sun` — is
the cycle's first look, read off the scene, so the daylight numbers keep one home and a rig at
`time_of_day` 0 writes nothing at all. `verify_day_cycle.gd` holds that.

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
runs the same table when its option is DAY TO NIGHT, then holds the night.

## `day_until = 0.71`

The authored daylight holds to 17:00 on the shift's clock ((17 − 7) / 14): the look every frame so
far was graded under is most of every run. Was 0.25 when the cycle opened at noon.

## `update_hz = 10.0`

How often the rig is moved. Each move re-renders the sky's radiance, so this is a cost dial. At
10 Hz over a 300 s cycle one step is 1/3000 of the way and no step is visible; a 10 s cycle driven
on `f_045` held 120 fps, 8.3 ms, through the whole blend on the desktop. ⚠️ **The handset is not
measured** — if the radiance update costs there, lower this before touching the looks.

## The keyframes

| `at` | Look | Key light | `sky_light` | `night_lights` |
|---|---|---|---|---|
| 0.79 (18:00) | `dusk.tres` | 8° up in the WSW, `(1, 0.62, 0.36)`, 0.80 | `(1, 0.74, 0.58)` | 0.25 |
| 0.86 (19:00) | `twilight.tres` | on the horizon, 0.00 | `(0.3, 0.3, 0.45)` | 0.80 |
| 0.93 (20:00) | `night.tres` | the moon, 38° up, `(0.62, 0.72, 1)`, 0.30 | `(0.1, 0.11, 0.18)` | 1.00 |

- **The sun sets in the west-south-west** — the engine's −X is west and +Z south — from the rig's
  authored 48° in the south-east, so the slerp carries it across the southern sky.
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
