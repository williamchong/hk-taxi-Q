# tyre.tres

Rationale for `game/tuning/tyre.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The per-wheel tyre model's table (`P3-52`, `Q152`): the spike that asks whether a drift can be
physical on `VehicleBody3D`. Read by `TyreVehicleController` alone, through `taxi_tyre.tscn` and
`drive.sh --tyres=`; the shipped taxi never loads it. Every value was graded on
`tools/skidpad.sh --scene=res://scenes/dev/skidpad_tyre.tscn --entry-kph=` at 42, 63 and 86 kph,
and `Q152` holds the tables.

⚠️ `substeps`, `mu`, `slide_ratio`, `peak_slip_ratio`, `peak_slip_angle_deg`,
`wheel_inertia_kgm2`, `low_speed_mps` and `drive_scale` are required: `tyre_profile.gd` declares no
defaults, and a zero leaves the car on the engine's own tyres (`TyreVehicleController.usable`).
`yaw_assist_scale` is absent because it is 0.0 — Godot's writer drops a value equal to the type's
zero — and 0 is the choice: the model is graded on physics alone.

## `mu = 2.0`

The shipped car corners at 2.7 g on the skidpad's `corner` row (11.2 m radius at 63 kph), and the
car carries `gravity_scale` 1.6, so its tyres need 1.7 × load at the limit. 2.0 leaves a margin.
This is arcade grip — a real tyre is near 1.0 — and it is why the car needs twice the drive to
spin its rear tyres (`drive_scale`).

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

## `handbrake_torque_nm = 3000.0`

Locks the rear wheels at the car's load (capacity ≈ 2 × 4,700 N × 0.35 m ≈ 3,300 N⋅m per wheel with
`mu`). Swept 1,500–4,000 on `hold`: 3,000 was the best at 63 kph; 4,000 killed the slide there and
helped it at 86.

## `low_speed_mps = 3.0`

The floor under which slip is measured against 3 m/s rather than the wheel's own speed, so a car
at rest does not read an infinite slip.

## `substeps = 8`

The spin solve's steps a tick. At 8 the residual stays monotone (the wheel's inertia term outweighs
the tyre's falling slope); at fewer it may not, and the safeguarded Newton then bisects.

## `drive_scale = 2.0`

The finding in one number. At 1.0 — the shipped drive — the rear tyres cannot be spun and no row
holds a slide; at 2.0 `hold` passes at both speeds; at 3.0 the 86 kph slide spins. The cost: the
car runs up to 119 kph in 4 s where it made 63, and the `corner` row accelerates through the bend.

## `traction_limit = 1.0`

Traction control cuts a driven wheel's torque past peak wheelspin, so full throttle at full lock
grips (peak slip 2.5° where it was 82° without it). Forward slip only: keyed on the combined slip
it cut the drive at every cornering limit.

## `traction_rearm_s = 1.0`

The drift button switches traction control off; it re-arms once the button has been up this long
and the body's slip is under the game's 14°. 0 and 0.5 re-armed before the throttle took the slide
over (`hold` at 63 kph 0.00 s); 1.0 and 2.0 read the same.

## `roll_influence = 0.8`

Where the sideways force goes in, 0 at the centre of mass's height, 1 at the contact. The shipped
0.2 (`handling.tres`) takes away the load transfer that rotates the car — nothing slides; at 1.0 the
car rolled onto its side at a kerb on Expo Drive. 0.8 holds the slide and lifts two wheels at the
same kerb at 72 kph, landing upright.
