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

## `length_s = 240.0`

Four minutes of DRIVING from the start to full night, against `GAME_DESIGN.md`'s three-to-five
minute session: a run that ends on time ends in the dark, and skilled play, which extends the
session, drives on under a night that holds. Game time, not wall time — the clock stops under the
start menu.

## `day_until = 0.25`

The first minute is the authored noon and nothing moves: the look every frame so far was graded
under gets the opening of every run.

## `update_hz = 10.0`

How often the rig is moved. Each move re-renders the sky's radiance, so this is a cost dial. At
10 Hz over a 240 s cycle one step is 1/2400 of the way and no step is visible; a 10 s cycle driven
on `f_045` held 120 fps, 8.3 ms, through the whole blend on the desktop. ⚠️ **The handset is not
measured** — if the radiance update costs there, lower this before touching the looks.

## The keyframes

| `at` | Look | Key light | `sky_light` | `night_lights` |
|---|---|---|---|---|
| 0.55 | `dusk.tres` | 8° up in the WSW, `(1, 0.62, 0.36)`, 0.80 | `(1, 0.74, 0.58)` | 0.25 |
| 0.72 | `twilight.tres` | on the horizon, 0.00 | `(0.3, 0.3, 0.45)` | 0.80 |
| 0.90 | `night.tres` | the moon, 38° up, `(0.62, 0.72, 1)`, 0.30 | `(0.1, 0.11, 0.18)` | 1.00 |

- **The sun sets in the west-south-west** — the engine's −X is west and +Z south — from the rig's
  authored 48° in the south-east, so the slerp carries it across the southern sky.
- 🔴 **The twilight keyframe exists so the key light can change hands unseen.** One
  `DirectionalLight3D` is both sun and moon; at 0.72 its energy is 0.0, and the swing from the
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
