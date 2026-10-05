class_name AntiLockBrakesProfile
extends Resource
## ABS's numbers (`Q155`): a real car's anti-lock brakes, which release a
## wheel's brake as it starts to lock so the tyre stays near its peak and the
## front wheels can still steer. The foot brake only; the drift button's
## handbrake is never released. Read by `TyreVehicleController`; why the value
## is what it is lives in `tuning/systems/anti_lock_brakes.md`. No defaults
## (`Q119`): zero is the system off.

## The lock — backward slip, in multiples of the tyre's peak slip ratio — at
## which a braked wheel's foot brake is released for the substep. 0 is no ABS.
@export_range(0.0, 5.0, 0.05) var slip_limit: float
