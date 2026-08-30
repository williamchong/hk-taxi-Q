class_name ChaseProfile
extends Resource
## Third-person chase camera feel, as data.
##
## CLAUDE.md hard rule 4: tuning values are data, never constants in code. This
## script declares the schema and nothing else — the numbers live only in
## game/tuning/camera.tres.
##
## Deliberately no defaults, following HandlingProfile. ⚠️ **The failure that
## buys is the half-filled .tres, not the unassigned one.** An unassigned
## `@export var profile` is *null*, which `chase_camera.gd` catches outright; a
## hand-authored .tres missing a key reads **0.0** and renders perfectly — a rig
## that never yaws, or a spring arm of zero length with the camera inside the
## car. That is what the asserts in `ChaseCamera._ready` are for, on
## `vehicle_controller.gd`'s precedent.
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

@export_group("Follow")

## Both dials below are first-order response coefficients in 1/s: the rig closes
## `1 - exp(-k * delta)` of the remaining gap each tick, so its rate is
## proportional to how wrong it currently is.
##
## ⚠️ **`hud_style.gd` parameterises the same filter the other way up** —
## `accel_smoothing_s` is a time constant in seconds and `hud.gd` divides by it,
## where these are rates and `chase_camera.gd` multiplies. Deliberate: the pair
## here has to agree with each other before it agrees with another subsystem, and
## a rate is the natural reading of "how hard the camera chases". Check the sign
## of the exponent's argument before porting a number between the two.

## How fast the rig's anchor converges on the car's position.
##
## ⚠️ 13.388613 is not a tuned value — it is the exact `1/s` equivalent of the
## 12.0 this shipped as under the old linear `follow_lag * delta`, chosen so
## `Q98`'s change of law moved the framing by nothing measurable.
@export_range(0.5, 40.0, 0.1, "suffix:1/s") var follow_response: float

## How fast the rig converges on the car's heading.
##
## ⚠️ **Not an angular rate, and that difference is the whole of `Q98`.** This was
## `yaw_lag`, a constant 7.0 rad/s handed to `rotate_toward` — 401°/s, against a
## car whose *steering* can only turn it at 2.245 rad/s (128.6°/s, at 97 kph; the
## kinematic `v·tan(δ)/L` off the ±1.3 m wheel z in taxi.tscn and
## `steer_angle_max_deg`/`_at_top_deg`). At 3.12x the fastest steering alone can
## rotate the car it closed any *steering-induced* error inside a single tick, so
## the rig was rigid through every corner and the dial named "lag" produced none.
## ⚠️ It is **not** a bound on body yaw: `drift_yaw_torque_nm` acts on the chassis
## outside that model, and `Q88` records a 165.0° spin.
##
## Steady-state lag in a sustained turn is `ω · delta / (1 - exp(-k · delta))`,
## which at 60 Hz is 5.1% above the `ω / k` continuous limit: **11.9° at 30 kph
## and 22.4° at 105**. ⚠️ Below about 3.0 the rig should stop being able to show
## the road through a corner — that is a prediction from the same arithmetic, not
## a measurement, and `P2-5`'s "readable at speed" is settled by driving it.
@export_range(0.5, 40.0, 0.1, "suffix:1/s") var yaw_response: float

@export_group("Speed feel")

## Field of view at rest.
@export_range(40.0, 120.0, 1.0, "suffix:°") var fov_base: float

## Added to fov_base at fov_full_kph, ramped linearly from rest.
@export_range(0.0, 50.0, 1.0, "suffix:°") var fov_boost: float

## Speed at which fov_boost is fully applied — **the fallback only.** A
## VehicleController target overrides it from that car's own
## HandlingProfile.max_speed_kph, so retuning top speed cannot desync the ramp,
## and all three shipped scenes take that path. It exists because ChaseCamera
## follows a Node3D and a target without a HandlingProfile still needs a number
## that came from somewhere.
@export_range(10.0, 300.0, 1.0, "suffix:km/h") var fov_full_kph: float
