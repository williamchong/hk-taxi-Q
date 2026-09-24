class_name TaxiDoor
extends Node3D
## The passenger door, swung on its hinge while a fare gets in or out (`P3-48`).
##
## The node IS the hinge: `taxi.tscn` places it on the doorway's front edge, at
## `make_vehicle.door_hinge`, and the leaf mesh below it is built in that frame —
## so the swing is this node's own rotation about `y` and nothing else moves.
## Which way is out is read off the node's side of the car, not authored, so a
## door hung on the other flank swings the other way without a second dial.
##
## Only the rear kerbside door has one. Hong Kong drives on the left, and a Hong
## Kong taxi's driver opens that door from the seat with a lever — the passenger
## never touches the front one.
##
## Presentation only, like `VehicleLamps`: nothing here is read by the physics
## and the leaf carries no collider, so an open door cannot clip a lamp post or
## change how the car drives. Whatever owns the fare calls `open`, `close` and
## `open_briefly`; the car itself never does.
##
## Runs on the physics tick for the lamps' reason: the calls that move it are made
## from `FareSystem._physics_process`, and the drive harness's frames are graded
## byte for byte, so the swing must advance on the clock that is fixed.

## How far the door swings, in degrees off shut.
##
## Short of square on purpose. At 90° from the chase camera the leaf is edge-on
## and vanishes into a line; 65° keeps its red face turned towards a camera
## behind the car, which is the only place anyone sees it from.
@export_range(10.0, 90.0, 1.0, "suffix:°") var open_deg: float = 65.0

## How long a full swing takes, either way.
##
## Under `fares.tres`'s `board_s` with room left over, so a hail shows the door
## standing open for most of the boarding rather than still moving when it ends.
@export_range(0.05, 2.0, 0.05, "suffix:s") var swing_s: float = 0.35

## How long `open_briefly` holds the door fully open before shutting it — the
## fare stepping out at the destination, or storming out of a bail.
@export_range(0.0, 5.0, 0.05, "suffix:s") var alight_hold_s: float = 0.8

## -1 or +1: the side of the car the hinge is on, and so which way is out.
var _outward: float = 0.0
## 0 shut, 1 open, and where the leaf is between them.
var _swing: float = 0.0
var _target: float = 0.0
## Counts down while the door is held open by `open_briefly`; negative otherwise.
var _hold_s: float = -1.0


func _ready() -> void:
	_outward = signf(position.x)
	# A hinge on the centreline has no outside. Refused loudly rather than
	# swinging the leaf into the cabin, which is what a zero here would not do —
	# it would not swing at all, and nothing would say so.
	if _outward == 0.0:
		push_warning("TaxiDoor at x = 0 cannot tell which way is out; it stays shut.")
	_apply()
	set_physics_process(false)


## Swing open and stay open.
func open() -> void:
	_hold_s = -1.0
	_move_to(1.0)


## Swing shut.
func close() -> void:
	_hold_s = -1.0
	_move_to(0.0)


## Swing open, hold for `alight_hold_s`, and swing shut again.
func open_briefly() -> void:
	_hold_s = alight_hold_s
	_move_to(1.0)


## Whether the door is anywhere but shut.
func is_open() -> bool:
	return _swing > 0.0


func _move_to(target: float) -> void:
	_target = target
	set_physics_process(_outward != 0.0)


func _physics_process(delta: float) -> void:
	var step: float = delta / swing_s
	_swing = move_toward(_swing, _target, step)
	_apply()
	if _swing != _target:
		return
	# The hold starts once the door is fully open, so a shorter swing never eats
	# into the time the passenger has to step out.
	if _hold_s >= 0.0:
		_hold_s -= delta
		if _hold_s < 0.0:
			_target = 0.0
		return
	# At rest, and nothing is waiting: stop ticking until the next call.
	set_physics_process(false)


func _apply() -> void:
	# Eased at both ends, so the leaf leaves the frame and lands against its stop
	# rather than starting and stopping at full speed.
	rotation.y = _outward * deg_to_rad(open_deg) * smoothstep(0.0, 1.0, _swing)
