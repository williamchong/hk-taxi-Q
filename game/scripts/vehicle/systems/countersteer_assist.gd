class_name CountersteerAssist
extends RefCounted
## The countersteer assist (`Q155`): while the car slides past the tyre's peak
## and the player steers INTO the slide, the front wheels are turned towards the
## travel by `CountersteerAssistProfile.gain` of the slip angle beyond the peak,
## up to `max_lock_deg` — a real car's electric steering nudging into opposite
## lock. Built because keyboard and touch steer near on-off; an option, on by
## default, because the user wants the countersteer to be the player's skill
## and a novice's slide to pay (`Q153`).
##
## ⚠️ Not a slip setpoint (`Q72`): the assist aims the fronts along the travel
## and asks for no angle. The throttle and the rear tyres set the slide.

## True from the player's first countersteer in a slide until the slide is
## over: the assist stands aside for it. See `yields`.
var _yielded: bool = false


## Forgets the slide: the car was put somewhere else, or the option went off.
func reset() -> void:
	_yielded = false


## Whether the assist stands aside this tick, given last tick's answer: from
## the player's first countersteer in a slide until the slide is over (the slip
## back under the tyre's peak), the slide is the player's. Re-tested each tick
## instead, the assist stepped back in every time a feathered countersteer
## crossed zero, and the pad's countersteering driver held 0.27 s where it held
## 2.00–3.28 s with the assist off (`P3-56`, `Q153`).
static func yields(yielded: bool, countersteering: bool, sliding: bool) -> bool:
	return sliding and (yielded or countersteering)


## The front wheels' angle with the assist on top of the player's `steering`.
## `toward` is the countersteer's sign in Godot's steering angle, `beyond` the
## slip past the tyre's peak in radians. Only while the player steers INTO the
## slide: letting go or countersteering is how the street's 90° turn is ended,
## and an assist still turning the fronts along the travel then brought it out
## at 58–69° where it settles at 81–91 (`countersteer_assist.md`).
func steer(
	steering: float,
	steer_input: float,
	toward: float,
	beyond: float,
	table: CountersteerAssistProfile
) -> float:
	var countersteer: float = -steer_input * toward
	_yielded = yields(_yielded, countersteer > 0.0, beyond > 0.0)
	if _yielded or countersteer >= 0.0 or beyond <= 0.0:
		return steering
	# Never less lock than the player already has: the assist adds to their
	# angle and is clamped only where it would pass `max_lock_deg`.
	var lock: float = maxf(deg_to_rad(table.max_lock_deg), absf(steering))
	return clampf(steering + toward * beyond * table.gain, -lock, lock)
