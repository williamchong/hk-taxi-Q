# tyre.tres

Rationale for `game/tuning/tyre.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The per-wheel tyre model's table (`P3-52`, `Q152`): built as the spike that asked whether a
drift can be physical on `VehicleBody3D`, and the game's car since 2026-10-03 (`city_drive.tscn`
instances `taxi_tyre.tscn`). Read by `TyreVehicleController` alone. "The shipped car" below is the
car before it — `taxi.tscn` on the engine's tyres, the pad's control until it was dropped on
2026-10-05. Every value was graded on `tools/skidpad.sh --entry-kph=` at 42, 63 and 86 kph (on
`skidpad_tyre.tscn` before that day, the same pad with this car on it), and `Q152` holds the
tables.

⚠️ `substeps`, `mu`, `slide_ratio`, `peak_slip_ratio`, `peak_slip_angle_deg`,
`wheel_inertia_kgm2` and `low_speed_mps` are required: `tyre_profile.gd` declares no
defaults, and a zero parks the car (`TyreVehicleController.usable`). `yaw_assist_scale` (a share
of the engine-tyre car's drift yaw torque) and `handbrake_declutch` went with that car on
2026-10-05: both were 0 / off, the torque not rescuing the low end, the declutch only a harsh brake
(`Q153`).

The car's systems — traction control, stability control, drift mode, the handbrake, the rev
limiter — and the game's own arcade aids have their own tables and notes under
`tuning/systems/` since 2026-10-05 (`Q155`), each moved out of this file with its sections; the
rename map is in `Q155`. This table is the tyre: its grip curve, its wheel, its solve, and where
its sideways force goes in.

## `mu = 1.0`

A road tyre's grip (`Q153`, the user's call 2026-10-05, with the drive and `handbrake_torque_nm`
below). Pillar 2 asks for a car that is easy to drive, not for unrealistic grip: the ease is the
hidden aids'. **A real taxi is the baseline** (the user, the same day): `gravity_scale` 1.0 and a
Toyota Crown Comfort LPG's drive (`HandlingProfile`: 6,000 N off the line, 83 kW above about
42 kph, air drag), so the tyres hold about 1.0 g; a gameplay change is made on top of that, never by bending a physical number.

What a road tyre gives that 2.0 could not: weight transfer moves the rear. At 2.0 a corner left
the tyres about 3.2 g, so a lift or a feint never took the rear under what the turn asked, and no
single dial gave a flick while `corner` gripped (`Q153`'s nine levers). At 1.0 the lifted flick
slides on physics alone, 44 / 48° at 42 / 63 kph (31–34° at 2.0, and those only because the flick
trigger stood traction control down).

⚠️ The dials named in this section are their names before `Q155`'s rename (its map has the new).

⚠️ **1.0 alone spins the car** (2026-10-05, `mu` 1.0 with the rest as at 2.0): the tap and the
lifted flick peak at 168–180° at 42, 63 and 86 kph, the plain `corner` slips 12 / 16 / 23°. Not
answered by any stability dial: `turn_drive_cut` 0.8 / 1.0, `slide_drive_fade_from_deg` 10 / 15 /
20, `traction_limit` 0.5 / 0.75, `drift_side_cut` 0.2 / 0.4, the drift assist and the body's
gravity at 1.0 each left the tap at 164–168°. The spin was the two torques sized for 2.0 —
`drive_scale` and `handbrake_torque_nm` — on a tyre with half the force to answer them. Refused
before at 2.0's drive (`Q153`, 1.0 and 1.25) for the same reason.

## `slide_ratio = 0.9`

The sliding tail. Swept 0.5–0.9 on `hold`: 0.9 was the only value holding past 2 s at both 63 and
86 kph (2.08 / 2.12 s before the roll point moved to 0.8); at 0.6 the 86 kph slide spun (179°).

## `peak_slip_ratio = 0.1`

Where drive and brake force peak, a textbook road tyre. Not swept.

## `peak_slip_angle_deg = 8.0`

A road tyre's cornering peak. Swept 4–8 on `corner`: a stiffer tyre scrubs less and the doubled
drive then accelerates the car even further through the bend, so it moves the failing row the
wrong way.

## `wheel_inertia_kgm2 = 1.2`

A 0.35 m wheel and tyre with a share of the drivetrain. The spin is solved implicitly, so this sets
how fast a wheel spins up, not whether the step is stable.

## `low_speed_mps = 3.0`

The floor under which slip is measured against 3 m/s rather than the wheel's own speed, so a car
at rest does not read an infinite slip.

## `substeps = 8`

The spin solve's steps a tick. At 8 the residual stays monotone (the wheel's inertia term outweighs
the tyre's falling slope); at fewer it may not, and the safeguarded Newton then bisects.

## `side_force_depth = 0.7`

Where the sideways force goes in, 0 at the centre of mass's height, 1 at the contact. The shipped
0.2 (`handling.tres`'s `roll_influence`) takes away the load transfer that rotates the car — at 0.6
and below a player's input does not slide at 63 or 42 kph; at 1.0 the car rolled onto its side at a
kerb on Expo Drive. 0.7 is the least that slides at all three speeds (`ride` 1.85 / 2.55 / 3.15 s),
and on the full-throttle kerb it bounces the body 0.19 m less than 0.8 (peak 6.57 m against 6.76);
both still lift the inside wheels at 72 kph. Its own name, not `roll_influence`: a sweep resolves a
field by name across both tables, and the shared name swept the handling table's copy.
