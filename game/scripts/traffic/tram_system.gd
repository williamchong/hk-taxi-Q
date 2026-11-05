class_name TramSystem
extends Node3D
## The trams (`P3-4`, `Q176`): walls that move down the published rails, stop at
## the tram stops and obey the signals. `TramLines` says where they go.
##
## 🔴 **Kinematic, as the cars are.** A tram is a number along its route and a speed;
## its body is an `AnimatableBody3D` moved to where it is each tick, and the hit reads
## the closing speed (`Q175`).
##
## 🔴 **The taxi pushes a tram along its rails, never off them** (`Q180`, the user's
## ask, 2026-11-04: "tram should never be derailed"). The body is `Pushable`: it gives
## only along its rails, `(normal · rails)² / m`, so the taxi's push changes its speed
## along the route and nothing else — it has no sideways to be moved in. Pushed on, or
## back, it brakes at `brake_max_mps2` to its own pace; at a stop it rolls to rest
## again before the doors' clock runs on. At 12.5 t it takes about a tenth of a hit.
##
## 🔴 **The whole fleet runs all the time.** Cars spawn in a ring round the player, and
## an 8.9 m tram appearing 60 m up a straight street would be seen doing it. A tram
## sets out past one end of its line and leaves past the other.
##
## **A tram stops for what is ahead and never pushes.** Another tram or a car within
## `follow_heading_deg` of the rails' heading on the rails ahead, and the taxi whatever
## its heading.
## Parked vehicles are the ETL's: none stands in a tram's path (`parked.py`). A car
## crossing is not seen, for `TrafficSystem`'s reason: one that waited for a crossing
## car could wait for one waiting for it.
##
## **The bell** rings as a tram pulls away from a stop and while the taxi stands in
## its way, from a few voices moved to the tram that rings: `bell_range_m`
## keeps a far tram quiet.

const ARG: String = "--trams="
## The kind in the authored library, whose box and lamps it wears.
const KIND: String = "tram"
const BELL_PATH: String = "res://assets/authored/audio/tram_bell.wav"
## What `FareSystem` and `TrafficSystem` find the trams by.
const GROUP: StringName = &"tram_system"
## Under this a tram is stopped.
const STOPPED_MPS: float = 0.1
## A stop point is aimed this far short of, so float slack never carries it over.
const STOP_SHORT_M: float = 0.3
## Above or below this much, another thing is on another level.
const LEVEL_APART_M: float = 3.0
## What `_gap_on_route` takes for "whatever its heading".
const ANY_HEADING: float = -1.0
## Under this a tram short of its stop has arrived and opens its doors.
const ARRIVE_MPS: float = 1.0
## How finely a tram reads the rails ahead for what is on them, in metres: under the
## narrowest thing it stops for, a car's width.
const LOOK_STEP_M: float = 1.5
## Tries for a place on the lines at the start.
const PLACE_TRIES: int = 16

## The player's car, which a tram stops for.
@export var vehicle: Node3D
## The scene's signals; where none is set a tram stops for no light.
@export var signals: SignalController

## What is holding a tram, for the verify tool and the bell.
enum Held { NONE, STOP, LIGHT, TRAM, CAR, TAXI }


## One tram.
class Tram:
	extends RefCounted

	var id: int = 0
	var live: bool = false
	var route: TramLines.Route
	var s: float = 0.0
	var speed: float = 0.0
	## The next stop and stop line along the route.
	var next_stop: int = 0
	var next_line: int = 0
	var dwell_left: float = 0.0
	var held: Held = Held.NONE
	var braking: bool = false
	var bell_wait: float = 0.0
	var pose: Transform3D
	var body: AnimatableBody3D
	var shape: CollisionShape3D
	var obstacle: Dictionary
	## Lamp bits last written, -1 till the first, so a tram is written only when they change.
	var written: int = -1
	## Whether `pose` changed since it was last written: a tram at a stop is not rewritten.
	var moved: bool = false
	## Its kerb mass (`parked.tres` `masses_kg`), 0 for a tram the taxi cannot push.
	var mass_kg: float = 0.0


var profile: TramProfile
## What a tram stops behind; found by its group where the scene has one.
var _traffic: TrafficSystem
var lines: TramLines
var trams: Array[Tram] = []
var half_length: float = 0.0
var half_width: float = 0.0
## Rings since the start, for the verify tool.
var rings: int = 0
## Trams that set out and that left, for the verify tool.
var set_out: int = 0
var left: int = 0
## Pushes the taxi gave a tram (`Q180`), for the verify tool.
var pushes: int = 0
## The trams by their body's instance id, for `take_push`.
var _by_body: Dictionary[int, Tram] = {}

var _rng := RandomNumberGenerator.new()
var _batch: MultiMesh
var _extent: AABB
var _weights: PackedFloat32Array = []
var _voices: Array[AudioStreamPlayer3D] = []
var _next_voice: int = 0


func _ready() -> void:
	# `setup` already ran: the verify tool's own run.
	if profile != null:
		return
	if Cmdline.off(ARG):
		queue_free()
		return
	var table := load(TramProfile.PATH) as TramProfile
	var graph: RoadGraph = RoadGraph.shared()
	if table == null or graph == null or graph.is_empty() or not usable(table):
		queue_free()
		return
	if not setup(TramLines.resident(graph, table), table, 1):
		queue_free()


## Everything a run needs, without the scene: false where the city or the table cannot
## carry a tram. `rolls` seeds every roll.
func setup(with_lines: TramLines, table: TramProfile, rolls: int) -> bool:
	if with_lines == null or with_lines.is_empty() or table == null or not usable(table):
		return false
	lines = with_lines
	profile = table
	_rng.seed = rolls
	if not _load_mesh():
		return false
	for route: TramLines.Route in lines.routes:
		_weights.append(route.length_m())
	_batch.instance_count = table.trams
	var box := BoxShape3D.new()
	box.size = _extent.size
	var parked := load(ParkedProfile.PATH) as ParkedProfile
	var mass_kg: float = parked.masses_kg.get(KIND, 0.0) if parked != null else 0.0
	for index: int in table.trams:
		var tram := Tram.new()
		tram.id = index
		tram.body = AnimatableBody3D.new()
		tram.body.name = "tram_%d" % index
		tram.shape = CollisionShape3D.new()
		tram.shape.shape = box
		tram.shape.position = _extent.get_center()
		tram.shape.disabled = true
		tram.body.add_child(tram.shape)
		add_child(tram.body)
		tram.obstacle = {
			"transform": Transform3D.IDENTITY,
			"extent": _extent,
			"id": hash(Vector2i(int(get_instance_id() & 0x7FFFFFFF), index)),
			"velocity": Vector3.ZERO,
		}
		tram.mass_kg = mass_kg
		if mass_kg > 0.0:
			Pushable.mark(tram.body, self)
			_by_body[tram.body.get_instance_id()] = tram
		trams.append(tram)
		_hide(tram)
	_load_bell()
	for tram: Tram in trams:
		_place_anywhere(tram)
	add_to_group(GROUP)
	return true


## False, with a pushed reason, where a value is zero or negative.
static func usable(table: TramProfile) -> bool:
	var required: Dictionary[String, float] = {
		"trams": float(table.trams),
		"cruise_mps": table.cruise_mps,
		"accel_mps2": table.accel_mps2,
		"brake_mps2": table.brake_mps2,
		"brake_max_mps2": table.brake_max_mps2 - table.brake_mps2,
		"dwell_s": table.dwell_s,
		"gap_m": table.gap_m,
		"look_m": table.look_m,
		"follow_heading_deg": table.follow_heading_deg,
		"start_clear_m": table.start_clear_m,
		"run_off_m": table.run_off_m,
		"bogie_m": table.bogie_m,
		"taxi_half_m": table.taxi_half_m,
		"seam_join_m": table.seam_join_m,
		"seam_heading_deg": table.seam_heading_deg,
		"bell_voices": float(table.bell_voices),
		"bell_range_m": table.bell_range_m,
		"bell_repeat_s": table.bell_repeat_s,
	}
	return not TuningTable.any_zero(table, required, "TramSystem", "no tram will run")


func _load_mesh() -> bool:
	var packed := load(TrafficSystem.LIBRARY_PATH) as PackedScene
	if packed == null:
		push_error("TramSystem: %s did not load as a scene" % TrafficSystem.LIBRARY_PATH)
		return false
	var library: Node3D = packed.instantiate()
	var mesh: Mesh = null
	for node: Node in library.find_children("*", "MeshInstance3D", true, false):
		if String(node.name) == KIND:
			mesh = (node as MeshInstance3D).mesh
	library.free()
	if mesh == null:
		push_error("TramSystem: no mesh %s in %s" % [KIND, TrafficSystem.LIBRARY_PATH])
		return false
	_extent = mesh.get_aabb()
	half_length = _extent.size.z * 0.5
	half_width = _extent.size.x * 0.5
	_batch = MultiMesh.new()
	_batch.transform_format = MultiMesh.TRANSFORM_3D
	_batch.use_custom_data = true
	# Lamps from `INSTANCE_CUSTOM.a`, not the instance uniforms (`VehicleBodyBatch`).
	_batch.mesh = VehicleBodyBatch.batched(mesh)
	var drawn := MultiMeshInstance3D.new()
	drawn.name = KIND
	drawn.multimesh = _batch
	add_child(drawn)
	return true


func _load_bell() -> void:
	var stream := load(BELL_PATH) as AudioStream
	if stream == null:
		push_warning("TramSystem: %s did not load; the trams are silent" % BELL_PATH)
		return
	for _voice: int in profile.bell_voices:
		var voice := AudioStreamPlayer3D.new()
		voice.stream = stream
		voice.max_distance = profile.bell_range_m
		voice.bus = &"SFX"
		add_child(voice)
		_voices.append(voice)


## A tram anywhere along a route, clear of the rest: the city at the start of a drive
## has its trams already out.
func _place_anywhere(tram: Tram) -> void:
	for _try: int in PLACE_TRIES:
		var route: TramLines.Route = _pick_route()
		var s: float = _rng.randf_range(0.0, route.length_m())
		if _clear_at(route.at(s), tram):
			# At rest: at speed, one placed short of a red could not stop for it.
			_set_on(tram, route, s, 0.0)
			return


func _pick_route() -> TramLines.Route:
	return lines.routes[_rng.rand_weighted(_weights)]


## Whether no live tram stands within `start_clear_m` of `at`.
func _clear_at(at: Vector3, except: Tram) -> bool:
	for other: Tram in trams:
		if (
			other != except
			and other.live
			and other.pose.origin.distance_to(at) < profile.start_clear_m
		):
			return false
	return true


func _set_on(tram: Tram, route: TramLines.Route, s: float, speed: float) -> void:
	tram.live = true
	tram.route = route
	tram.s = s
	tram.speed = speed
	tram.dwell_left = 0.0
	tram.moved = true
	tram.next_stop = 0
	tram.next_line = 0
	while tram.next_stop < route.stops.size() and route.stops[tram.next_stop].s_m <= s:
		tram.next_stop += 1
	while (
		tram.next_line < route.lines.size() and route.lines[tram.next_line].s_m <= s + half_length
	):
		tram.next_line += 1
	tram.pose = _pose_at(route, s)
	tram.shape.set_deferred("disabled", false)
	set_out += 1


func _physics_process(delta: float) -> void:
	step(delta)


## One tick: set out what waits, run every tram, write what moved.
func step(delta: float) -> void:
	# Late, and once a tick till found: the traffic joins its group when it is set up.
	if _traffic == null and is_inside_tree():
		_traffic = get_tree().get_first_node_in_group(TrafficSystem.GROUP) as TrafficSystem
	for tram: Tram in trams:
		if tram.live:
			_run(tram, delta)
		else:
			_try_set_out(tram)
	for tram: Tram in trams:
		if tram.live:
			if tram.moved:
				tram.moved = false
				tram.body.global_transform = tram.pose
				_batch.set_instance_transform(tram.id, tram.pose)
			_write_lamps(
				tram, TrafficSystem.lamp_bits(true, tram.braking, 1 if at_stop(tram) else 0)
			)


func _try_set_out(tram: Tram) -> void:
	var route: TramLines.Route = _pick_route()
	if _clear_at(route.at(0.0), tram):
		_set_on(tram, route, 0.0, profile.cruise_mps)


func _run(tram: Tram, delta: float) -> void:
	tram.bell_wait = maxf(tram.bell_wait - delta, 0.0)
	if tram.speed < 0.0 or (tram.dwell_left > 0.0 and tram.speed > 0.0):
		# Pushed back, or on from its stop: it brakes to rest first.
		_roll(tram, move_toward(tram.speed, 0.0, profile.brake_max_mps2 * delta), delta)
		return
	if tram.dwell_left > 0.0:
		tram.dwell_left -= delta
		tram.held = Held.STOP
		tram.braking = true
		if tram.dwell_left <= 0.0:
			tram.next_stop += 1
			_ring(tram)
		return
	var target: float = profile.cruise_mps
	tram.held = Held.NONE
	var route: TramLines.Route = tram.route
	if tram.next_stop < route.stops.size():
		var to_stop: float = route.stops[tram.next_stop].s_m - tram.s
		if to_stop <= STOP_SHORT_M and tram.speed < ARRIVE_MPS:
			tram.speed = 0.0
			tram.dwell_left = profile.dwell_s
			tram.held = Held.STOP
			tram.braking = true
			return
		if to_stop < 0.0:
			# Pushed past it by a late brake: on to the next.
			tram.next_stop += 1
		else:
			target = _limit(tram, target, to_stop - STOP_SHORT_M, Held.STOP)
	while tram.next_line < route.lines.size():
		var line: TramLines.Line = route.lines[tram.next_line]
		var to_line: float = line.s_m - (tram.s + half_length)
		if to_line < -STOP_SHORT_M:
			tram.next_line += 1
			continue
		if (
			signals != null
			and TrafficSystem.must_stop(
				signals.state_of(line.edge, line.along), to_line, tram.speed, profile.brake_max_mps2
			)
		):
			target = _limit(tram, target, to_line - STOP_SHORT_M, Held.LIGHT)
		break
	target = _follow(tram, target)
	tram.braking = target < tram.speed or tram.speed < STOPPED_MPS
	if tram.speed < target:
		tram.speed = minf(target, tram.speed + profile.accel_mps2 * delta)
	else:
		tram.speed = maxf(target, tram.speed - profile.brake_max_mps2 * delta)
	_roll(tram, tram.speed, delta)


## Move `tram` down its rails at `speed` for a tick: past the route's end it leaves.
func _roll(tram: Tram, speed: float, delta: float) -> void:
	tram.speed = speed
	tram.braking = tram.braking or speed < 0.0
	tram.s = maxf(tram.s + speed * delta, 0.0)
	if tram.s >= tram.route.length_m():
		_leave(tram)
		return
	if speed != 0.0:
		tram.pose = _pose_at(tram.route, tram.s)
		tram.moved = true


## `Pushable`: how readily the tram behind `body` gives along `normal` — along its
## rails alone, so a push square across them moves nothing.
func push_inverse_mass(body: Object, normal: Vector3, _at: Vector3) -> float:
	var tram: Tram = _by_body.get(body.get_instance_id())
	if tram == null or not tram.live:
		return 0.0
	return Pushable.rails_inverse_mass(tram.mass_kg, -tram.pose.basis.z, normal)


## `Pushable`: the taxi put `impulse` into the tram behind `body`. Its speed down the
## rails takes the part along them; the rest is the rails'.
func take_push(body: Object, impulse: Vector3, _at: Vector3) -> void:
	var tram: Tram = _by_body.get(body.get_instance_id())
	if tram == null or not tram.live:
		return
	var rails: Vector3 = -tram.pose.basis.z
	tram.speed += (impulse.x * rails.x + impulse.z * rails.z) / tram.mass_kg
	pushes += 1


## `target` or the speed the tram can still stop from in `distance_m`, the lesser, and
## what is holding it if that is what took it.
func _limit(tram: Tram, target: float, distance_m: float, why: Held) -> float:
	var limit: float = TrafficSystem.stopping_speed(distance_m, profile.brake_mps2)
	if limit < target:
		tram.held = why
		return limit
	return target


func _follow(tram: Tram, target: float) -> float:
	var follow_cos: float = cos(deg_to_rad(profile.follow_heading_deg))
	var limited: float = target
	for other: Tram in trams:
		if other != tram and other.live:
			limited = _hold(
				tram,
				limited,
				_gap_on_route(tram, other.pose, follow_cos, half_length, half_width),
				Held.TRAM
			)
	if is_instance_valid(_traffic):
		for car: TrafficSystem.Car in _traffic.cars:
			if car.live:
				# A car knocked across the rails stands in the way at any heading.
				var heading_cos: float = ANY_HEADING if car.knocked else follow_cos
				limited = _hold(
					tram,
					limited,
					_gap_on_route(tram, car.pose, heading_cos, car.half_length, car.half_width),
					Held.CAR
				)
	if is_instance_valid(vehicle):
		var gap: float = _gap_on_route(
			tram, vehicle.global_transform, ANY_HEADING, profile.taxi_half_m, half_width
		)
		limited = _hold(tram, limited, gap, Held.TAXI)
		if tram.held == Held.TAXI and tram.speed < STOPPED_MPS and tram.bell_wait <= 0.0:
			_ring(tram)
	return limited


## `_limit` for something `gap` ahead, its `gap_m` short; nearly every pair reads INF.
func _hold(tram: Tram, target: float, gap: float, why: Held) -> float:
	return target if gap == INF else _limit(tram, target, gap - profile.gap_m, why)


## Bumper to bumper to something at `other`, down the rails: 🔴 a straight cone from the
## tram's nose missed a taxi round a curve until the tram stood on it. INF where it is
## out of `look_m`, off the tram's width of its line, on another level, or crossing.
func _gap_on_route(
	tram: Tram,
	other: Transform3D,
	follow_cos: float,
	other_half_length: float,
	other_half_width: float
) -> float:
	var at: Vector3 = other.origin
	var origin: Vector3 = tram.pose.origin
	if absf(at.y - origin.y) > LEVEL_APART_M:
		return INF
	var look_m: float = profile.look_m + half_length + other_half_length
	if RoadGraph.plan_distance(at, origin) > look_m:
		return INF
	var heading: Vector3 = -other.basis.z
	var reach: float = half_width + other_half_width
	var ahead: float = LOOK_STEP_M
	while ahead <= look_m:
		var here: Vector3 = tram.route.at(tram.s + ahead)
		var off_m: float = RoadGraph.plan_distance(at, here)
		if off_m <= reach:
			var next: Vector3 = tram.route.at(tram.s + ahead + LOOK_STEP_M)
			var along := Vector2(next.x - here.x, next.z - here.z).normalized()
			if along.x * heading.x + along.y * heading.z < follow_cos:
				return INF
			return ahead - half_length - other_half_length
		# A point `d` further along the rails is at most `d` closer: on the same grid,
		# nothing that could hit is stepped over.
		ahead += LOOK_STEP_M * maxi(1, floori((off_m - reach) / LOOK_STEP_M))
	return INF


## The tram's body at `s`: its middle between two bogies each on the line, so it
## swings through a curve and across a chord rather than snapping at each station.
func _pose_at(route: TramLines.Route, s: float) -> Transform3D:
	var front: Vector3 = route.at(s + profile.bogie_m)
	var rear: Vector3 = route.at(s - profile.bogie_m)
	var along := Vector3(front.x - rear.x, 0.0, front.z - rear.z)
	var back: Vector3 = (-along).normalized() if along.length_squared() > 0.0 else Vector3.BACK
	return Transform3D(Basis(Vector3.UP.cross(back), Vector3.UP, back), (front + rear) * 0.5)


func _leave(tram: Tram) -> void:
	tram.live = false
	left += 1
	_hide(tram)


func _hide(tram: Tram) -> void:
	_write_lamps(tram, TrafficSystem.lamp_bits(false, false))
	tram.shape.set_deferred("disabled", true)
	_batch.set_instance_transform(tram.id, Transform3D(Basis().scaled(Vector3.ZERO), Vector3.ZERO))


## Braking into its stop or standing at it for its passengers: it winks left (the
## user's call, 2026-11-06, as a bus does at its stop, `Q187`).
static func at_stop(tram: Tram) -> bool:
	return tram.dwell_left > 0.0 or tram.held == Held.STOP


func _write_lamps(tram: Tram, bits: int) -> void:
	if bits == tram.written:
		return
	tram.written = bits
	_batch.set_instance_custom_data(tram.id, Color(0.0, 0.0, 0.0, float(bits)))


func _ring(tram: Tram) -> void:
	tram.bell_wait = profile.bell_repeat_s
	if (
		is_instance_valid(vehicle)
		and vehicle.global_position.distance_to(tram.pose.origin) > profile.bell_range_m
	):
		return
	rings += 1
	if _voices.is_empty():
		return
	var voice: AudioStreamPlayer3D = _voices[_next_voice]
	_next_voice = (_next_voice + 1) % _voices.size()
	voice.global_position = tram.pose.origin
	if voice.is_inside_tree():
		voice.play()


## The trams the near miss should look at, as `TrafficSystem.near_cars` hands out its
## cars (`Q175`).
func near_cars(point: Vector3, radius_m: float, look_s: float) -> Array[Dictionary]:
	var found: Array[Dictionary] = []
	for tram: Tram in trams:
		if not tram.live:
			continue
		var far_x: float = tram.pose.origin.x - point.x
		var far_z: float = tram.pose.origin.z - point.z
		var reach_m: float = radius_m + tram.speed * look_s
		if far_x * far_x + far_z * far_z > reach_m * reach_m:
			continue
		tram.obstacle["transform"] = tram.pose
		tram.obstacle["velocity"] = -tram.pose.basis.z * tram.speed
		found.append(tram.obstacle)
	return found
