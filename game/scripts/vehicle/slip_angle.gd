class_name SlipAngle
extends RefCounted
## The car's slip: the angle between where it points and where it is going.
##
## The vehicle's own fact, so it lives with the vehicle: the tyre car's
## stability control and `DriftMode` read it every tick, and the fare loop pays
## on the same number through `FareSystem.slip_deg_of`. It was `FareSystem`'s,
## which made the car depend on the fare loop for a reading of itself.
##
## ⚠️ **A second copy of `skidpad_ablation.gd`'s slip, on purpose** (`Q84`): the
## grader must never call what it grades, so the instrument keeps its own. Same
## flattening, same floor, and the same velocity: the rear axle's
## (`VehicleController.rear_axle_velocity`). A change to either's flattening or
## floor is made twice, by hand, and named.

## Ground speed under which a slip angle is noise rather than a measurement:
## a nearly stationary car has a velocity vector pointing anywhere at all.
## `skidpad_ablation.gd`'s `SLIP_FLOOR_MPS`, restated on purpose (see above).
const FLOOR_MPS: float = 1.0
## The slip past which the car is travelling backwards, not sliding: the
## tyre car's stability control stands aside there, and the drift meter does
## not run (a reverse reads about 180°, and under `Q172`'s 0.5 s bar it paid).
## A geometric fact — 90° is the travel crossing the axle — not a dial.
const REVERSED_DEG: float = 90.0


## The angle between `nose` and `velocity` — the rear axle's, for a slide — in
## degrees, flattened to the ground plane so a ramp or a landing cannot read as
## slip, and 0 under `FLOOR_MPS`. `skidpad_ablation.gd::_slip_deg`, restated.
static func deg_of(velocity: Vector3, nose: Vector3) -> float:
	var travel := Vector3(velocity.x, 0.0, velocity.z)
	if travel.length() < FLOOR_MPS:
		return 0.0
	var heading := Vector3(nose.x, 0.0, nose.z)
	if heading.is_zero_approx():
		return 0.0
	return rad_to_deg(travel.normalized().angle_to(heading.normalized()))
