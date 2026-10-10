class_name NearMiss
extends RefCounted
## The near miss and the close call (`P3-2a`, `Q161`): a parked vehicle passed
## inside a band at speed, that the car was HEADING FOR a moment before.
##
## 🔴 **Passing a car in the next lane is not a near miss** (the user's call,
## 2026-10-11: "should not trigger if we are just passing cars in nearby lane
## without real danger"). The band alone cannot tell the two apart — a straight
## run down a lane beside a bay row passes every car in it at the same
## clearance a swerve does. What tells them apart is the PATH: a vehicle the
## car was pointed at — inside the car's own width along its travel, within
## `near_miss_look_s` of reaching it — and then was not hit. A lane pass never
## has the parked car in the path; a swerve round it did, `near_miss_memory_s`
## or less before the pass. Both bars are inclusive and `verify_fares.gd`
## stands on each from both sides.
##
## **What one obstacle is.** Its global transform and the mesh's own extent,
## as `ParkedLayer.near` answers; the detector works in the car's own plan
## frame — along its travel (the velocity, or the nose under the floor) and
## across it — on the obstacle's four plan corners. In the path: some corner
## ahead within the look distance and the corners' across-range overlapping
## the car's half-width. Alongside: the along-range overlapping the car's own
## length; the clearance then is the across-gap between the nearer flank and
## the obstacle's nearer corner, and the least of it over the pass is what is
## graded. Passed: the whole obstacle behind the tail — the tick that decides.
##
## **Pure, so the verify tool can drive it without a car.** `tick` takes the
## car's transform, its velocity, the obstacles near it and whether a wall was
## touched this tick; `FareSystem` is the only caller. A touch forgets every
## threat in flight: a brush is not a miss.
##
## 🚫 No award while airborne, no award on a touch, no chain. The price is a
## flat HK$ per event, as every skill is (`Q145`).


## What the detector remembers of one obstacle between ticks.
class Track:
	extends RefCounted
	## Seconds since the obstacle was last in the car's path; INF for never.
	var threat_age_s: float = INF
	## The least across-clearance seen while alongside, in metres.
	var min_clear_m: float = INF
	## The highest speed seen while alongside, in m/s.
	var speed_mps: float = 0.0
	## Whether the obstacle has been alongside on this approach, and how old
	## the threat was on the tick it came alongside — the swerve is over by
	## then, and the pass itself takes as long as the vehicle is long.
	var alongside: bool = false
	var age_at_alongside_s: float = INF
	## Whether this approach has been judged; cleared once it is ahead again.
	var judged: bool = false
	## The tick the obstacle was last near enough to be handed in.
	var last_seen: int = 0

	## A fresh approach: the obstacle is ahead again after a judged pass.
	func restart() -> void:
		judged = false
		min_clear_m = INF
		speed_mps = 0.0
		alongside = false
		age_at_alongside_s = INF


## Under this the travel direction is the nose, not the velocity.
const SPEED_FLOOR_MPS: float = 1.0
## A track is dropped once it has been out of reach this many ticks.
const FORGET_TICKS: int = 20
## The float slack every inclusive bar carries.
const SLACK: float = 1e-4

var _profile: SkillProfile = null
var _half_width_m: float = 0.0
var _half_length_m: float = 0.0
var _usable: bool = false
var _tracks: Dictionary[int, Track] = {}
var _earned: Array[Fare.Award] = []
## The tick counter, for `Track.last_seen`.
var _tick: int = 0
## The last obstacle's span in the car's frame, written by `_span` into
## members rather than a fresh array a tick.
var _s_min: float = 0.0
var _s_max: float = 0.0
var _t_min: float = 0.0
var _t_max: float = 0.0


## The car's own plan half-extents, and the table. A missing or zeroed bar,
## a close-call band wider than the near-miss band, or a car of no size makes
## an INERT detector, with the reason pushed — never one on a literal (`Q119`).
func _init(profile: SkillProfile, half_width_m: float, half_length_m: float) -> void:
	if profile == null:
		push_error("NearMiss: no SkillProfile handed in; no near miss will pay.")
		return
	var required: Dictionary[String, float] = {
		"near_miss_m": profile.near_miss_m,
		"close_call_m": profile.close_call_m,
		"near_miss_min_kph": profile.near_miss_min_kph,
		"near_miss_look_s": profile.near_miss_look_s,
		"near_miss_memory_s": profile.near_miss_memory_s,
		"near_miss_hkd": profile.near_miss_hkd,
		"close_call_hkd": profile.close_call_hkd,
	}
	if TuningTable.any_zero(profile, required, "NearMiss", "no near miss will pay"):
		return
	if profile.close_call_m >= profile.near_miss_m:
		push_error(
			(
				"NearMiss: %s close_call_m (%.2f) is not under near_miss_m (%.2f); no near miss will pay."
				% [profile.resource_path, profile.close_call_m, profile.near_miss_m]
			)
		)
		return
	if half_width_m <= 0.0 or half_length_m <= 0.0:
		push_error("NearMiss: the car has no plan extent; no near miss will pay.")
		return
	_profile = profile
	_half_width_m = half_width_m
	_half_length_m = half_length_m
	_usable = true


func usable() -> bool:
	return _usable


## The look-ahead, in seconds, and the car's half-length — what `FareSystem`
## sizes its query disc from.
func look_s() -> float:
	return _profile.near_miss_look_s if _usable else 0.0


func car_half_length_m() -> float:
	return _half_length_m


## Forget every approach in flight — at a boarding, as the tracker does.
func reset() -> void:
	_tracks.clear()


## One tick: what it earned, usually nothing. `obstacles` are
## `ParkedLayer.near`'s dictionaries; `touched` is a wall contact this tick;
## `airborne` is every wheel off the ground. ⚠️ The array is reused: read it
## before the next `tick`.
func tick(
	car: Transform3D,
	velocity: Vector3,
	obstacles: Array[Dictionary],
	delta_s: float,
	touched: bool = false,
	airborne: bool = false
) -> Array[Fare.Award]:
	_earned.clear()
	if not _usable:
		return _earned
	var elapsed: float = maxf(delta_s, 0.0)
	var travel := Vector3(velocity.x, 0.0, velocity.z)
	var speed: float = travel.length()
	var nose := Vector3(-car.basis.z.x, 0.0, -car.basis.z.z)
	var along: Vector3 = travel / speed if speed >= SPEED_FLOOR_MPS else nose.normalized()
	if along.is_zero_approx():
		return _earned
	var across := Vector3(-along.z, 0.0, along.x)
	var look_m: float = maxf(speed * _profile.near_miss_look_s, 2.0 * _half_length_m)
	_tick += 1

	for obstacle: Dictionary in obstacles:
		var id: int = int(obstacle["id"])
		var track: Track = _tracks.get(id)
		if track == null:
			track = Track.new()
			_tracks[id] = track
		track.last_seen = _tick
		track.threat_age_s += elapsed
		_span(car, along, across, obstacle)

		if _s_min > _half_length_m:
			# Ahead: a fresh approach once it has been passed and judged.
			if track.judged:
				track.restart()
			if _s_min <= look_m and _t_max >= -_half_width_m and _t_min <= _half_width_m:
				track.threat_age_s = 0.0
		if touched or airborne:
			track.threat_age_s = INF
		var beside: bool = _s_max >= -_half_length_m and _s_min <= _half_length_m
		if beside and not track.judged:
			if not track.alongside:
				track.age_at_alongside_s = track.threat_age_s
			track.alongside = true
			track.min_clear_m = minf(track.min_clear_m, _clear_across())
			track.speed_mps = maxf(track.speed_mps, speed)
		if _s_max < -_half_length_m and track.alongside and not track.judged:
			track.judged = true
			_judge(track)

	for id: int in _tracks.keys():
		if _tick - _tracks[id].last_seen > FORGET_TICKS:
			_tracks.erase(id)
	return _earned


## The across-gap between the nearer flank and the obstacle's nearer corner;
## negative where the two overlap across.
func _clear_across() -> float:
	if _t_min > 0.0:
		return _t_min - _half_width_m
	if _t_max < 0.0:
		return -_t_max - _half_width_m
	return -INF


## The pass as a whole, on the tick the obstacle falls behind the tail.
## Every bar inclusive, with a hair of slack so a clearance built from the
## bar's own number lands on it rather than a bit past it.
func _judge(track: Track) -> void:
	if track.min_clear_m < 0.0 or track.min_clear_m > _profile.near_miss_m + SLACK:
		return
	if track.speed_mps * 3.6 < _profile.near_miss_min_kph - SLACK:
		return
	if track.age_at_alongside_s > _profile.near_miss_memory_s + SLACK:
		return
	if track.min_clear_m <= _profile.close_call_m + SLACK:
		_earned.append(Fare.Award.new(Fare.Skill.CLOSE_CALL, _profile.close_call_hkd))
	else:
		_earned.append(Fare.Award.new(Fare.Skill.NEAR_MISS, _profile.near_miss_hkd))


## The obstacle's four plan corners in the car's frame, into `_s_min`,
## `_s_max`, `_t_min`, `_t_max`: `s` along the travel and `t` across it,
## positive to the car's right.
func _span(car: Transform3D, along: Vector3, across: Vector3, obstacle: Dictionary) -> void:
	var at: Transform3D = obstacle["transform"]
	var extent: AABB = obstacle["extent"]
	_s_min = INF
	_s_max = -INF
	_t_min = INF
	_t_max = -INF
	_corner(car, along, across, at * Vector3(extent.position.x, 0.0, extent.position.z))
	_corner(car, along, across, at * Vector3(extent.end.x, 0.0, extent.position.z))
	_corner(car, along, across, at * Vector3(extent.position.x, 0.0, extent.end.z))
	_corner(car, along, across, at * Vector3(extent.end.x, 0.0, extent.end.z))


func _corner(car: Transform3D, along: Vector3, across: Vector3, point: Vector3) -> void:
	var corner: Vector3 = point - car.origin
	var s: float = corner.x * along.x + corner.z * along.z
	var t: float = corner.x * across.x + corner.z * across.z
	_s_min = minf(_s_min, s)
	_s_max = maxf(_s_max, s)
	_t_min = minf(_t_min, t)
	_t_max = maxf(_t_max, t)
