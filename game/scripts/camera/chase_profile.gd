class_name ChaseProfile
extends Resource
## Third-person chase camera feel, as data.
##
## CLAUDE.md hard rule 4: tuning values are data, never constants in code. This
## script declares the schema and nothing else — the numbers live only in
## game/tuning/camera.tres.
##
## Deliberately no defaults, following HandlingProfile: a profile that was never
## assigned reads as all-zeroes, which is a zero-length spring arm sitting on the
## car's own origin, and fails loudly rather than quietly framing the game from
## values buried in a script.
##
## ⚠️ **Every number here was an @export default on the camera node until Q98,
## and that was hard rule 4 in name only.** The old docstring argued the exports
## satisfied the rule because they could be dialled in the inspector without a
## code edit — but the camera is instanced in three scenes and *not one of them
## overrode a single value*, so in practice they were constants in a script that
## happened to be reachable from a property panel.

@export_group("Framing")

## How far behind the car the rig sits, as the spring arm's length.
@export_range(1.0, 15.0, 0.1, "suffix:m") var distance: float

## How far above the car's origin the rig's anchor sits.
@export_range(0.0, 5.0, 0.1, "suffix:m") var height: float

## Fixed downward tilt. The rig never pitches with the car — body pitch and roll
## reach the camera through nothing, which is why suspension heave does not tip
## the horizon.
@export_range(-60.0, 0.0, 0.5, "suffix:°") var pitch_deg: float

## Fraction of the remaining positional gap closed per second, not a closing
## speed.
@export_range(1.0, 40.0, 0.5) var follow_lag: float

@export_group("Yaw")

## How fast the rig converges on the car's heading, as a first-order response
## coefficient: it closes `1 - exp(-yaw_response * delta)` of the remaining angle
## each tick, so its turn rate is proportional to how wrong it currently is.
##
## ⚠️ **Not an angular rate, and that difference is the whole of `Q98`.** This was
## `yaw_lag`, a constant 7.0 rad/s handed to `rotate_toward` — 401°/s, against a
## car whose kinematic yaw rate peaks at 2.245 rad/s (128.6°/s, at 97 kph, off a
## 2.6 m wheelbase and a lock tapering 24° to 7°). At 3.12x the fastest the car
## can rotate it closed every reachable heading error inside a single tick, so
## the rig was rigid by construction and the dial named "lag" produced none.
##
## Steady-state lag in a sustained turn is `yaw rate / yaw_response`, so 6.0
## trails by 11.4° at 30 kph and 21.3° at 105. ⚠️ Below about 3.0 the rig stops
## being able to show the road through a corner, which is `P2-5`'s standing
## acceptance criterion — "readable at speed".
@export_range(0.5, 30.0, 0.1, "suffix:1/s") var yaw_response: float

@export_group("Speed feel")

## Field of view at rest.
@export_range(40.0, 120.0, 1.0, "suffix:°") var fov_base: float

## Added to fov_base at max_speed_kph, ramped linearly from rest. The speed it
## ramps against is read from the vehicle's own HandlingProfile rather than
## restated here, so retuning top speed cannot silently desync the FOV.
@export_range(0.0, 50.0, 1.0, "suffix:°") var fov_boost: float
