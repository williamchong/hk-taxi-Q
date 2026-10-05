class_name CountersteerAssistProfile
extends Resource
## The countersteer assist's numbers (`Q155`): a real car's electric steering
## nudging the wheel into opposite lock while the tail is out (VW's DSR,
## Lexus's VDIM). The player's option (`drift_assist`, `P3-56`), on by
## default in the game and off on the pads. Read by `CountersteerAssist`; why
## each value is what it is lives in `tuning/systems/countersteer_assist.md`.
## No defaults (`Q119`).

## While the car slides, the share of the slip angle past the tyre's peak the
## front wheels are turned towards the travel, on top of the player's own
## steering. 0 is none; 1 points the fronts along the travel. A steering aid,
## not a force: the tyres still decide the slide.
@export_range(0.0, 1.5, 0.05) var gain: float
## The most the front wheels may turn while the assist countersteers, where the
## handling table's lock narrows with speed (16.4° at 63 kph).
@export_range(0.0, 60.0, 1.0, "suffix:°") var max_lock_deg: float
