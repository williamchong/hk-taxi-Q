class_name DriftModeProfile
extends Resource
## Drift mode's numbers (`Q155`): the switch that stands traction control and
## stability control's understeer cut down for a slide the player asked for —
## the drift button, or a flick (`ArcadeAidsProfile`) — and brings them back
## when it is over, as a real car's drift mode does by the driver's hand. Read
## by `DriftMode`; why each value is what it is lives in
## `tuning/systems/drift_mode.md`. No defaults (`Q119`).

## How long the systems stay off after the drift button comes up, at least;
## after that they re-arm once the car's slip is back under
## `HandlingProfile.drift_slip_threshold_deg`, the bar the game scores a slide
## on. 0 re-arms on the slip alone.
@export_range(0.0, 5.0, 0.05, "suffix:s") var rearm_s: float
## Whether the systems come back as soon as the player lets go of the steering
## after a press — the slide's ending handed to the steering key, where
## `rearm_s` waits on a clock. Letting go only: a countersteer is how a slide
## is HELD, and re-armed on a reversal the countersteered slide died (`hold`
## 2.63 s -> 0.60 s at 63 kph).
@export var rearm_on_steer_release: bool
