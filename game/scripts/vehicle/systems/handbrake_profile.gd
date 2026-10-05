class_name HandbrakeProfile
extends Resource
## The handbrake's numbers (`Q155`): the drift button's torque on each rear
## wheel, a real car's handbrake. Read by `TyreVehicleController`; why the
## value is what it is lives in `tuning/systems/handbrake.md`. No defaults
## (`Q119`).

## Torque the drift button puts on each rear wheel. 0 is no handbrake.
@export_range(0.0, 10000.0, 10.0, "suffix:N·m") var torque_nm: float
