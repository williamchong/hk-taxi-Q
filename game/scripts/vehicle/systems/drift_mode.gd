class_name DriftMode
extends RefCounted
## Drift mode (`Q155`): traction control and stability control's understeer cut
## stand down for a slide the player asked for, and come back when it is over —
## a real car's drift mode, switched by the driver's hand. Engaged by the drift
## button's press, or by a flick (`FlickWatch`, an arcade aid); released once
## the button has been up for `DriftModeProfile.rearm_s` and the car's slip is
## under the bar the game scores a slide on, or, with `rearm_on_steer_release`,
## the tick the player lets the steering go having steered since the press.
##
## Keyed on the body's slip rather than the tyres': after a handbrake tap the
## rear tyres spin back up to road speed before the throttle can take the slide
## over, and re-armed on that, traction control cut the very torque the slide
## needed (the `hold` row at 63 kph fell from 2.22 s to nothing). The steering
## release is the slide's ending handed to the steering key (`Q153`). A flick
## engages it only while it is off, so a countersteer inside a slide cannot
## stretch the slide.

## True while the systems stand down for the player's slide.
var engaged: bool = false
## Seconds since the drift button came up while engaged.
var _released_s: float = 0.0
## Whether the player has steered since the press, so letting the steering go
## can end the slide whichever of the two was pressed first.
var _slide_steered: bool = false
var _flick: FlickWatch = FlickWatch.new()


## Forgets the slide: the car was put somewhere else.
func reset() -> void:
	engaged = false
	_released_s = 0.0
	_slide_steered = false
	_flick.reset()


## One tick of the player's inputs and the car's travel (`velocity` against
## `nose`, the body slip the game scores a slide on). True on the tick a
## drift press starts a slide — where the rear side cut is latched
## (`ArcadeAidsProfile.drift_side_cut`) — and false on every other.
func step(
	drift_input: bool,
	steer: float,
	throttle: float,
	brake: float,
	kph: float,
	velocity: Vector3,
	nose: Vector3,
	threshold_deg: float,
	delta: float,
	table: DriftModeProfile,
	aids: ArcadeAidsProfile,
) -> bool:
	var flicked: bool = _flick.step(steer, throttle, brake, kph, delta, aids)
	if drift_input:
		var pressed: bool = not engaged or _released_s > 0.0
		if pressed:
			_slide_steered = false
		_slide_steered = _slide_steered or not is_zero_approx(steer)
		engaged = true
		_released_s = 0.0
		return pressed
	if flicked and not engaged:
		engaged = true
		_released_s = 0.0
		_slide_steered = true
		return false
	if not engaged:
		return false
	if not is_zero_approx(steer):
		_slide_steered = true
	elif table.rearm_on_steer_release and _slide_steered:
		engaged = false
		return false
	_released_s += delta
	var slip: float = FareSystem.slip_deg_of(velocity, nose)
	if _released_s >= table.rearm_s and slip < threshold_deg:
		engaged = false
	return false
