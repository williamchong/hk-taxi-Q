class_name SkidStrip
extends RefCounted
## The tyre marks as numbers (`P3-57`): which wheel lays a piece of mark this
## tick, and where its four corners go in one ring of quads shared by every
## wheel. `SkidMarks` owns the mesh and uploads what this writes.
##
## A wheel lays a piece from where its mark ended last tick to where it is now,
## so the mark is unbroken while the tyre stays past `from_slip`. The mark
## BREAKS — the next tick only starts one — when the wheel leaves the ground,
## falls under the bar, or moves further than `max_step_m` in one tick: a car
## put somewhere else (`place_at`, the harness's reset) or landing from a jump
## must not draw a stripe across the gap. At `capacity` pieces the oldest is
## overwritten, so the road keeps the most recent marks and the mesh never grows.
##
## Pure, so `verify_vehicle.gd` drives it without a car.

## Corners per piece, and the triangles that cover them: (0, 1, 2), (0, 2, 3).
const CORNERS: int = 4
const INDICES: Array[int] = [0, 1, 2, 0, 2, 3]

## How many pieces have ever been laid; the next one goes in slot `laid % capacity`.
var laid: int = 0

var _capacity: int = 0
var _from_slip: float = 0.0
var _half_width_m: float = 0.0
var _lift_m: float = 0.0
var _max_step_m: float = 0.0
var _positions: PackedVector3Array = PackedVector3Array()
## Each wheel's last edge — the corner on its left and its right, and the
## contact it was laid at — and whether it has one, i.e. whether its mark runs on.
var _left: PackedVector3Array = PackedVector3Array()
var _right: PackedVector3Array = PackedVector3Array()
var _at: PackedVector3Array = PackedVector3Array()
var _marking: Array[bool] = []


func _init(wheels: int, profile: SkidMarksProfile) -> void:
	_capacity = profile.capacity
	_from_slip = profile.mark_from_slip
	_half_width_m = profile.mark_width_m * 0.5
	_lift_m = profile.lift_m
	_max_step_m = profile.max_step_m
	_positions.resize(_capacity * CORNERS)
	_left.resize(wheels)
	_right.resize(wheels)
	_at.resize(wheels)
	_marking.resize(wheels)
	_marking.fill(false)


## Every corner of every piece, `CORNERS` a piece, slot by slot. A slot never
## laid is four corners at the origin: a degenerate quad, which draws nothing.
func positions() -> PackedVector3Array:
	return _positions


## The index buffer for `capacity` pieces.
func indices() -> PackedInt32Array:
	var all := PackedInt32Array()
	all.resize(_capacity * INDICES.size())
	for slot: int in _capacity:
		for k: int in INDICES.size():
			all[slot * INDICES.size() + k] = slot * CORNERS + INDICES[k]
	return all


## One tick of `wheel`: on the ground or not, its contact `point` and `normal`,
## its axle `side`, and its combined `slip`. Returns the slot written, or -1
## when this tick laid nothing.
func step(
	wheel: int, grounded: bool, point: Vector3, normal: Vector3, side: Vector3, slip: float
) -> int:
	if not grounded or slip < _from_slip:
		_marking[wheel] = false
		return -1
	var across: Vector3 = (side - normal * side.dot(normal)).normalized() * _half_width_m
	var raised: Vector3 = point + normal * _lift_m
	var left: Vector3 = raised - across
	var right: Vector3 = raised + across
	var slot: int = -1
	if _marking[wheel] and point.distance_to(_at[wheel]) <= _max_step_m:
		slot = laid % _capacity
		var first: int = slot * CORNERS
		_positions[first] = _left[wheel]
		_positions[first + 1] = _right[wheel]
		_positions[first + 2] = right
		_positions[first + 3] = left
		laid += 1
	_left[wheel] = left
	_right[wheel] = right
	_at[wheel] = point
	_marking[wheel] = true
	return slot
