# traffic.tres

Rationale for `game/tuning/traffic.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How the moving traffic drives and where it lives (`P3-3c`, `Q173`). Every value is AUTHORED: no
source publishes Wan Chai's flows, and the cars are a backdrop to the taxi, not a model of the
city's traffic. `traffic_system.gd` says what each rule does; this says why each number.

⚠️ EVERY KEY BELOW IS REQUIRED. `traffic_profile.gd` declares no defaults, so a missing key reads
as zero, and `TrafficSystem` refuses to run on a zero. Three are held as DIFFERENCES — `spawn_max_m`
over `spawn_min_m`, `retire_m` over `spawn_max_m`, `brake_max_mps2` over `brake_mps2` — so a table
that inverts one is refused too. `verify_traffic.gd` drives this file, three seeds × 90 s.

## `cars = 24`

The fleet alive at once. Measured on the throttle route (2026-10-29, desktop): +7 `draws` (one
`MultiMesh` per kind, and their shadows) and about +1 ms of `phys` against `--traffic=off`
(2.8 against 1.8 ms a tick, ±0.5 ms run to run). The mobile tier (`P0-3b`) must re-take it; the
per-car cost is the car-ahead search, which is every pair.

## `spawn_min_m = 60.0`

Far enough that a car rarely appears in the chase camera's near field.

## `spawn_max_m = 220.0`

The ring cars appear in. With 24 cars over the streets inside 220 m, a busy road shows a car or
two at a time, not a jam.

## `retire_m = 260.0`

40 m past the ring, so a car placed at its edge does not vanish on its first tick away.

## `spawn_clear_m = 12.0`

No car is placed nearer another than about two car lengths, and no car is placed on an edge
shorter than this.

## `cruise_of_limit = 0.8`

40 kph on a 50 kph street: a car that keeps to its limit, under it, so the taxi passes traffic.

## `turn_mps = 7.0`

25 kph through a junction's curve.

## `accel_mps2 = 2.0`

A gentle pull-away; 0 to 40 kph in about 5.5 s.

## `brake_mps2 = 3.0`

The planned stop, for a light or a car ahead: comfortable.

## `brake_max_mps2 = 8.0`

The hardest a car brakes on a tick: near a dry tyre's limit, for a car cut up. ⚠️ The AMBER
judgement is made at this rate, not the planned one — see `traffic_system.gd`; at the planned rate
a car rode the line of its own judgement and crossed into the red.

## `gap_m = 2.0`

Bumper to bumper behind a stopped car.

## `look_m = 45.0`

How far a car looks for one to follow: further than its stopping distance from cruise at the planned
rate (40 kph → 21 m).

## `follow_heading_deg = 45.0`

Past this a car ahead is crossing, not queueing, and is not followed in the plan cone. The car's own
path (its edge and the edge it turns into) is read first and has no angle bar.

## `turn_span_m = 6.0`

The fallback only, since city schema 41: a turn runs from the junction mouth the bundle publishes
(`trim_m`, where the stop line stands) to the next road's, and this reaches either side of a node
whose ribbon met no cap. 40% of a short edge, and never short of the stop point.

## `lane_change_m = 25.0`

Travel to move one lane over, a three-second change at 30 kph. A car moves toward its turn's lane
from the moment it joins the road and only while the lane beside it is clear for both cars' lengths
and `gap_m`; one that never got across turns from where it is. Shorter reads as a swerve.

## `straight_deg = 30.0`

Under this between the way in and the way out a move is straight on and keeps its lane; over it a
left turn is taken from the nearside lane into the nearside, a right from the offside into the
offside (the user's drive, 2026-10-29: cars turned right from the left lane). A staggered crossroad's
dog-leg reads straight at 30°.

## `kinds = {car_a 4, car_b 3, minibus 1.5, van 1.5}`

The parked library's road vehicles, weighted toward saloons. No coach (too long for the turn curve
the cars take) and no motorcycle (a box under it would read as a car).
