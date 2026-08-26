extends Node
## The single source of player intent.
##
## Architectural rule (docs/ARCHITECTURE.md): no gameplay script reads raw
## input events. Everything reads this action set instead. That is what keeps
## touch, gamepad and keyboard from leaking into vehicle and UI code.
##
## Sampled in _physics_process, not _process: Godot runs every physics step
## before idle processing, so a vehicle polling from _physics_process would
## otherwise read a sample one render frame stale — a guaranteed extra 16.7 ms
## of input latency, doubling whenever the render rate drops below the physics
## tick. Autoloads are the first children of root, so this runs before any
## gameplay node in the same tick.
##
## STUB — P0-3 scaffold. Keyboard and gamepad work; touch does not. On-screen
## zones, the two relative thumb axes and buffering for taps shorter than one
## physics tick are all P2-4. The touch scheme itself is settled — see `Q83` and
## ARCHITECTURE.md "The three schemes".

signal drift_started
signal drift_ended
signal look_back_started
signal look_back_ended

## Steering, -1.0 (full left) to 1.0 (full right).
var steer: float = 0.0
## Throttle, 0.0 to 1.0.
var accelerate: float = 0.0
## Brake / reverse, 0.0 to 1.0.
var brake_reverse: float = 0.0
var drift: bool = false
var look_back: bool = false

## Forces full throttle whenever the brake is released. ⚠️ **No longer the touch
## default — `Q83` reversed it.** Touch drives the throttle for real, on the
## positive half of thumb 1's vertical axis, and pays no extra thumb rest for it
## because `brake_reverse` is the negative half of that same axis.
##
## Kept as the accessibility and one-handed option. Set by the platform layer in
## P2-4; nothing sets it today, so the `false` below is shipped behaviour on
## every scheme rather than a placeholder.
var auto_accelerate: bool = false


func _physics_process(_delta: float) -> void:
	steer = Input.get_axis(&"steer_left", &"steer_right")
	accelerate = Input.get_action_strength(&"accelerate")
	brake_reverse = Input.get_action_strength(&"brake_reverse")

	if auto_accelerate and is_zero_approx(brake_reverse):
		accelerate = 1.0

	drift = _track_hold(&"drift", drift, drift_started, drift_ended)
	look_back = _track_hold(&"look_back", look_back, look_back_started, look_back_ended)


## Comparing against the previous value rather than using
## Input.is_action_just_pressed(), which the engine documents as unreliable in
## _physics_process — it can report true across several ticks or none at all.
func _track_hold(action: StringName, was_held: bool, started: Signal, ended: Signal) -> bool:
	var held: bool = Input.is_action_pressed(action)
	if held == was_held:
		return held
	if held:
		started.emit()
	else:
		ended.emit()
	return held
