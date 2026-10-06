class_name LightTrail
extends RefCounted
## The light tail as numbers (`P3-70`): which lamp lays a piece of streak this
## tick and where its corners go, in one ring shared by every lamp. `LightTail`
## owns the mesh and uploads what this writes — `SkidStrip`'s shape, for a lamp
## in the air rather than a tyre on the road.
##
## A lamp lays a piece from where it was last tick to where it is now while it
## is told to, so the streak is unbroken through a slide. It BREAKS — the next
## tick only starts one — when the lamp is told to stop, or moves further than
## `max_step_m` in one tick: a car put somewhere else (`place_at`, the harness's
## reset) or landing from a jump must not draw a streak across the gap. At
## `capacity` pieces the oldest is overwritten.
##
## A piece is two quads in a cross: one spanning the lens across the car, one
## spanning it up, so the streak reads from the chase camera above and from
## level behind without facing either. Each corner carries the time it was laid
## in `UV.x`, and `light_tail.gdshader` fades it against the clock.
##
## Pure, so `verify_vehicle.gd` drives it without a car.

## Corners per piece — two quads — and the triangles that cover them.
const CORNERS: int = 8
const INDICES: Array[int] = [0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7]

## How many pieces have ever been laid; the next one goes in slot `laid % capacity`.
var laid: int = 0

var _capacity: int = 0
var _max_step_m: float = 0.0
var _positions: PackedVector3Array = PackedVector3Array()
var _times: PackedVector2Array = PackedVector2Array()
## Each lamp's last lens — its centre, its half-extent across and up, and when
## it was there — and whether it has one, i.e. whether its streak runs on.
var _centre: PackedVector3Array = PackedVector3Array()
var _across: PackedVector3Array = PackedVector3Array()
var _up: PackedVector3Array = PackedVector3Array()
var _at_s: PackedFloat32Array = PackedFloat32Array()
var _trailing: Array[bool] = []


func _init(lamps: int, capacity: int, max_step_m: float) -> void:
	_capacity = capacity
	_max_step_m = max_step_m
	_positions.resize(_capacity * CORNERS)
	_times.resize(_capacity * CORNERS)
	_centre.resize(lamps)
	_across.resize(lamps)
	_up.resize(lamps)
	_at_s.resize(lamps)
	_trailing.resize(lamps)
	_trailing.fill(false)


## Every corner of every piece, `CORNERS` a piece, slot by slot. A slot never
## laid is eight corners at the origin: two degenerate quads, which draw nothing.
func positions() -> PackedVector3Array:
	return _positions


## When each corner was laid, in `x`, beside `positions()`.
func times() -> PackedVector2Array:
	return _times


## The index buffer for `capacity` pieces.
func indices() -> PackedInt32Array:
	var all := PackedInt32Array()
	all.resize(_capacity * INDICES.size())
	for slot: int in _capacity:
		for k: int in INDICES.size():
			all[slot * INDICES.size() + k] = slot * CORNERS + INDICES[k]
	return all


## One tick of `lamp`: the lens's `centre` now, its half-extents `across` the
## car and `up`, the clock, and whether it is streaking. Returns the slot
## written, or -1 when this tick laid nothing.
func step(
	lamp: int, now_s: float, centre: Vector3, across: Vector3, up: Vector3, laying: bool
) -> int:
	if not laying:
		_trailing[lamp] = false
		return -1
	var slot: int = -1
	if _trailing[lamp] and centre.distance_to(_centre[lamp]) <= _max_step_m:
		slot = laid % _capacity
		var first: int = slot * CORNERS
		var was: Vector3 = _centre[lamp]
		_positions[first] = was - _across[lamp]
		_positions[first + 1] = was + _across[lamp]
		_positions[first + 2] = centre + across
		_positions[first + 3] = centre - across
		_positions[first + 4] = was - _up[lamp]
		_positions[first + 5] = was + _up[lamp]
		_positions[first + 6] = centre + up
		_positions[first + 7] = centre - up
		for k: int in CORNERS:
			var old: bool = k < 2 or (k >= 4 and k < 6)
			_times[first + k] = Vector2(_at_s[lamp] if old else now_s, 0.0)
		laid += 1
	_centre[lamp] = centre
	_across[lamp] = across
	_up[lamp] = up
	_at_s[lamp] = now_s
	_trailing[lamp] = true
	return slot
