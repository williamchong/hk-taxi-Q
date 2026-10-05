class_name TractionControlProfile
extends Resource
## Traction control's numbers (`Q155`): a real car's system, which cuts a driven
## wheel's torque when it spins past the tyre's grip. Read by
## `TyreVehicleController`; why each value is what it is lives in
## `tuning/systems/traction_control.md`. No `@export` declares a default
## (`TyreProfile`'s convention, `Q119`): a missing key reads as zero, and zero
## here is the system switched off.

## The wheelspin — forward slip, in multiples of the tyre's peak — at which a
## driven wheel's torque is cut. 0 is no traction control. Drift mode stands it
## down for a slide the player asked for (`DriftModeProfile`).
@export_range(0.0, 5.0, 0.05) var wheelspin_limit: float
