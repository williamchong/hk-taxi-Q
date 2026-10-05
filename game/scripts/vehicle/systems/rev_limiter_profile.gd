class_name RevLimiterProfile
extends Resource
## The rev limiter's numbers (`Q155`): a real engine's cut-out, here on the
## driven wheels' rim speed. Read by `TyreVehicleController`; why the value is
## what it is lives in `tuning/systems/rev_limiter.md`. No defaults (`Q119`).

## How far past the car's top speed a driven wheel's rim may spin, as a share
## of it: 0 stops the drive at top speed's rim speed, 0.5 at half as much
## again. A slide is held on wheelspin, and at 86 kph the rim met the limiter
## mid-slide (`Q153`).
@export_range(0.0, 2.0, 0.05) var overspeed_share: float
