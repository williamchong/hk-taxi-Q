class_name FlickWatch
extends RefCounted
## The flick as numbers (`P3-54`, `Q153`): which tick a Scandinavian flick
## lands on, read off the player's own inputs. `TyreVehicleController` asks it
## every tick and, on the tick it answers true, stands traction control down
## as the drift button's press does — the lever the pad found holding the rear
## (`Q153`'s step 2), and the one a plain corner never reaches, because a plain
## corner never reverses the steering.
##
## A flick is the steering held to one side for `flick_feint_s` with the
## throttle lifted or the brake touched at some point of it, then over to the
## other side within `flick_window_s` of leaving the first, at
## `flick_min_kph` or more. A held throttle through the whole feint is a
## slalom, not a flick: the lift is what moves the load off the rear, and the
## games that start a slide on an input pattern key it on a lift or a brake
## tap too (`Q153`).
##
## Pure, so `verify_vehicle.gd` drives it without a car.

## The side the steering is held to, -1 left, +1 right, 0 none yet.
var _side: int = 0
## Seconds the steering has been held to `_side`.
var _held_s: float = 0.0
## Whether the throttle was lifted or the brake touched since the steering
## went to `_side`.
var _lifted: bool = false
## Seconds since the steering left `_side`; INF before it ever was anywhere.
var _off_s: float = INF


## Forgets the feint: the car was put somewhere else.
func reset() -> void:
	_side = 0
	_held_s = 0.0
	_lifted = false
	_off_s = INF


## One tick of the player's inputs — `steer` -1 left to +1 right, `throttle`
## and `brake` 0 to 1 — at `kph`. True on the tick the steering arrives on the
## far side of a flick, and never on a table whose `flick_window_s` is 0.
func step(
	steer: float, throttle: float, brake: float, kph: float, delta: float, table: TyreProfile
) -> bool:
	if table.flick_window_s <= 0.0:
		return false
	var share: float = table.flick_input_share
	var side: int = 0
	if steer >= share:
		side = 1
	elif steer <= -share:
		side = -1
	var lifted: bool = throttle < share or brake > 0.0
	if side == 0:
		_off_s += delta
		_lifted = _lifted or lifted
		if _off_s > table.flick_window_s:
			reset()
		return false
	# Back on the same side inside the window resumes the feint: a thumb that
	# wobbles through the centre is still holding it.
	if side == _side:
		_held_s += delta
		_off_s = 0.0
		_lifted = _lifted or lifted
		return false
	# No window test here: a pause past it already reset `_side` to 0.
	var flicked: bool = (
		_side == -side
		and _held_s >= table.flick_feint_s
		and _lifted
		and absf(kph) >= table.flick_min_kph
	)
	# The far side is the next feint's near side: a slalom of flicks reads each.
	# Its first tick counts toward that feint, as every later one does.
	_side = side
	_held_s = delta
	_lifted = lifted
	_off_s = 0.0
	return flicked
