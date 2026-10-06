class_name HandbrakeProfile
extends Resource
## The handbrake's numbers (`Q155`): the drift button's torque on each rear
## wheel, a real car's handbrake. Read by `TyreVehicleController`; why the
## value is what it is lives in `tuning/systems/handbrake.md`. No defaults
## (`Q119`).

## The torque the drift button puts on each rear wheel, in multiples of the
## torque that just locks it at rest (`TyreVehicleController._handbrake_torque_nm`):
## over 1 the button locks the rears, and the same number means the same
## handbrake on a car of another mass, tyre or wheel. 0 is no handbrake.
@export_range(0.0, 5.0, 0.0001) var lock_ratio: float
