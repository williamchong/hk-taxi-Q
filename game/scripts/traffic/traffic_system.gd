class_name TrafficSystem
extends Node3D
## Moving traffic (`P3-3c`, `Q173`): cars on the legal network round the
## player, keeping to the nearside lane, following the car ahead and stopping
## at the signals `SignalController` runs.
##
## 🔴 **A car drives the router's legal arcs and nothing else.** Every move is
## one of `RoadRouter.moves_from` under `Profile.legal()` — one-way, the turn bans,
## the lane bar — so traffic is never on an edge or a way the player's own
## wrong-way monitor would flag. `verify_traffic.gd` holds it.
##
## 🔴 **Kinematic, not simulated.** A car is a position along its edge and a
## speed; its body is an `AnimatableBody3D` moved to where it is each tick, so
## the taxi meets a solid box and the car is never pushed off its lane. Cars
## pass THROUGH each other at a junction without a signal: they follow a car
## ahead within `follow_heading_deg` and see nothing crossing (a car that
## waited for a crossing car could wait for one waiting for it).
##
## **A turn is a curve, not a jump.** The lane centres of two edges meeting at
## a node stand apart, a lane's width on a turn; a car leaves its edge
## `turn_span_m` short of the node (never short of its stop line) and joins the
## next as far in, along a quadratic curve through where the two lanes cross.
##
## **The stop.** Red and red-and-amber stop a car at its approach's stop point;
## amber stops a car that can stop even braking hard (`brake_max_mps2`), and
## lets one that cannot go through — the Highway Code's "so close to the line
## that pulling up might cause an accident". A car stopping for a car ahead or a
## light plans at `brake_mps2` and may brake up to `brake_max_mps2` on a tick.
## ⚠️ The amber judgement is at the HARD rate, never the planned one: a car
## braking at the planned rate rides exactly on that judgement's line, and a
## float's wobble tipped one over it into the red (`verify_traffic`, 2026-10-29).
##
## 🚫 **Not here yet**: a car changing lanes, a car giving way at an unsignalled
## junction, a car near-missed (`P3-2a` reads parked cars alone), the player's
## red light (`P3-3d`), the heads (`P3-3e`). `--traffic=off` takes it away.

const RoadRouterScript = preload("res://scripts/city/road_router.gd")
const ParkedRoster = preload("res://scripts/city/parked_roster.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")
const PlanScript = preload("res://scripts/traffic/signal_plan.gd")

const ARG: String = "--traffic="
## The authored vehicle library the parked layer draws from too.
const LIBRARY_PATH: String = "res://assets/authored/vehicles/parked.glb"
## Spawn attempts a tick; a ring with no room waits for the next.
const SPAWN_TRIES: int = 16
## Samples a turn curve's length is measured over.
const CURVE_SAMPLES: int = 8
## Under this a car is stopped, for the counters.
const STOPPED_MPS: float = 0.1
## A stop point is aimed this far short of, so float slack never carries a car
## a hair over it.
const STOP_SHORT_M: float = 0.3
## A car this far above or below is on another level, not ahead.
const LEVEL_APART_M: float = 3.0
## Edges and turns one tick may carry a car through; a ring of zero-length
## edges would otherwise never end the walk.
const ADVANCE_STEPS: int = 16

## The player's car: the ring is round it, and the car ahead may be it.
@export var vehicle: Node3D
## The scene's signals, which the cars stop at; where none is set the system
## runs its own (a verify tool's).
@export var signals: SignalController

## What stopped a car on its last tick, for the verify tool and the overlay.
enum Held { NONE, LIGHT, CAR }


## One car.
class Car:
	extends RefCounted

	var live: bool = false
	## Spawns this car has had, so a reader can tell a respawn from a move.
	var lives: int = 0
	var kind: int = 0
	## Its index in its kind's `MultiMesh`.
	var slot: int = 0
	var edge: int = -1
	var along: bool = true
	var length_m: float = 0.0
	## Metres travelled from the edge's entry end.
	var s: float = 0.0
	var speed: float = 0.0
	var cruise_mps: float = 0.0
	var next_edge: int = -1
	var next_along: bool = true
	## Where the straight run ends and the turn begins, in travel metres.
	var leave_m: float = 0.0
	## Travel metres into the next edge the turn ends at.
	var join_m: float = 0.0
	var turning: bool = false
	var turn_u: float = 0.0
	var turn_len: float = 0.0
	var p0: Vector3
	var p1: Vector3
	var p2: Vector3
	var pose: Transform3D
	var half_length: float = 0.0
	var half_width: float = 0.0
	var held: Held = Held.NONE
	var body: AnimatableBody3D
	var shape: CollisionShape3D


var profile: TrafficProfile
var graph: RoadGraph
var router: RoadRouter
var cars: Array[Car] = []
## Spawns and retirements since the start, for the verify tool.
var spawned: int = 0
var retired: int = 0

var _rng := RandomNumberGenerator.new()
var _kinds: PackedStringArray = []
var _meshes: Array[Mesh] = []
var _extents: Array[AABB] = []
var _batches: Array[MultiMesh] = []
var _weights: PackedFloat32Array = []
var _admitted: PackedInt32Array = []
## Where the ring is centred when there is no vehicle: the verify tool's.
var centre: Vector3 = Vector3.ZERO


func _ready() -> void:
	# Set up before it entered the tree: the verify tool's own run.
	if profile != null:
		return
	if Cmdline.off(ARG):
		queue_free()
		return
	if not setup(RoadGraph.shared(), load(TrafficProfile.PATH) as TrafficProfile, 1):
		queue_free()


## Everything a run needs, without the scene: false, with a pushed reason,
## where the city or the table cannot carry traffic. `seed` fixes every roll.
func setup(with_graph: RoadGraph, table: TrafficProfile, seed: int) -> bool:
	if with_graph == null or with_graph.is_empty() or table == null or not usable(table):
		return false
	graph = with_graph
	profile = table
	_rng.seed = seed
	router = RoadRouterScript.new(graph, RoadRouterScript.Profile.legal())
	_admitted = router.admitted_edge_ids()
	if _admitted.is_empty():
		push_warning("TrafficSystem: no edge admits traffic; none will run")
		return false
	if not _load_library():
		return false
	if signals != null and signals.plan == null:
		# The scene's controller refused its table and runs nothing.
		signals = null
	elif signals == null:
		var plan_table := load(SignalPlanProfile.PATH) as SignalPlanProfile
		signals = SignalController.create(PlanScript.resident(graph), plan_table)
		if signals != null:
			add_child(signals)
	for index: int in profile.cars:
		var car := Car.new()
		car.kind = _pick_kind()
		car.slot = _batches[car.kind].instance_count
		_batches[car.kind].instance_count += 1
		cars.append(car)
	for kind: int in _kinds.size():
		var drawn := MultiMeshInstance3D.new()
		drawn.name = _kinds[kind]
		drawn.multimesh = _batches[kind]
		add_child(drawn)
	var palettes: Dictionary = {}
	var parked := load(ParkedProfile.PATH) as ParkedProfile
	if parked != null:
		palettes = parked.liveries
	for car: Car in cars:
		var extent: AABB = _extents[car.kind]
		car.half_length = extent.size.z * 0.5
		car.half_width = extent.size.x * 0.5
		car.body = AnimatableBody3D.new()
		car.body.name = "car_%d" % cars.find(car)
		car.shape = CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = extent.size
		car.shape.shape = box
		car.shape.position = extent.get_center()
		car.shape.disabled = true
		car.body.add_child(car.shape)
		add_child(car.body)
		var palette: PackedColorArray = palettes.get(_kinds[car.kind], PackedColorArray())
		_batches[car.kind].set_instance_custom_data(
			car.slot, ParkedRoster.livery(_rng.randi() & 0xFFFF, palette)
		)
		_hide(car)
	return true


## False, with a pushed reason, where a value is zero or negative.
static func usable(table: TrafficProfile) -> bool:
	var required: Dictionary[String, float] = {
		"cars": float(table.cars),
		"spawn_min_m": table.spawn_min_m,
		"spawn_max_m": table.spawn_max_m - table.spawn_min_m,
		"retire_m": table.retire_m - table.spawn_max_m,
		"spawn_clear_m": table.spawn_clear_m,
		"cruise_of_limit": table.cruise_of_limit,
		"turn_mps": table.turn_mps,
		"accel_mps2": table.accel_mps2,
		"brake_mps2": table.brake_mps2,
		"brake_max_mps2": table.brake_max_mps2 - table.brake_mps2,
		"gap_m": table.gap_m,
		"look_m": table.look_m,
		"follow_heading_deg": table.follow_heading_deg,
		"turn_span_m": table.turn_span_m,
		"kinds": float(table.kinds.size()),
	}
	return not TuningTable.any_zero(table, required, "TrafficSystem", "no traffic will run")


func _load_library() -> bool:
	var packed := load(LIBRARY_PATH) as PackedScene
	if packed == null:
		push_error("TrafficSystem: %s did not load as a scene" % LIBRARY_PATH)
		return false
	var library: Node3D = packed.instantiate()
	var found: Dictionary[String, Mesh] = {}
	for node: Node in library.find_children("*", "MeshInstance3D", true, false):
		var mesh_node := node as MeshInstance3D
		if mesh_node.mesh != null:
			found[String(mesh_node.name)] = mesh_node.mesh
	library.free()
	for kind: String in profile.kinds:
		if not found.has(kind) or profile.kinds[kind] <= 0.0:
			push_warning("TrafficSystem: no mesh %s in %s; skipped" % [kind, LIBRARY_PATH])
			continue
		_kinds.append(kind)
		_meshes.append(found[kind])
		_extents.append(found[kind].get_aabb())
		_weights.append(profile.kinds[kind])
		var multi := MultiMesh.new()
		multi.transform_format = MultiMesh.TRANSFORM_3D
		multi.use_custom_data = true
		multi.mesh = found[kind]
		_batches.append(multi)
	if _kinds.is_empty():
		push_error("TrafficSystem: none of %s is in %s" % [profile.kinds.keys(), LIBRARY_PATH])
		return false
	# `instance_count` allocates the buffer and clears it, so it is grown car by
	# car in `setup` before any transform or livery is written.
	return true


func _pick_kind() -> int:
	return _rng.rand_weighted(_weights)


func _physics_process(delta: float) -> void:
	step(delta)


## One tick: spawn into the ring, drive every car, retire what left it.
func step(delta: float) -> void:
	var here: Vector3 = vehicle.global_position if is_instance_valid(vehicle) else centre
	for car: Car in cars:
		if not car.live:
			continue
		if _plan_distance(car.pose.origin, here) > profile.retire_m:
			_retire(car)
			continue
		_drive(car, delta)
	for _try: int in SPAWN_TRIES:
		var idle: Car = _idle_car()
		if idle == null:
			break
		_try_spawn(idle, here)
	for car: Car in cars:
		if car.live:
			car.body.global_transform = car.pose
			_batches[car.kind].set_instance_transform(car.slot, car.pose)


func _idle_car() -> Car:
	for car: Car in cars:
		if not car.live:
			return car
	return null


func _try_spawn(car: Car, here: Vector3) -> void:
	var edge: int = _admitted[_rng.randi_range(0, _admitted.size() - 1)]
	var along: bool = _rng.randf() < 0.5
	if not router.admits_way(edge, along):
		along = not along
	var length_m: float = graph.plan_length_of(edge)
	if length_m < profile.spawn_clear_m:
		return
	var s: float = _rng.randf_range(0.2, 0.6) * length_m
	var at: Vector3 = graph.lane_at(edge, s if along else length_m - s, along)
	var away: float = _plan_distance(at, here)
	if away < profile.spawn_min_m or away > profile.spawn_max_m:
		return
	for other: Car in cars:
		if other.live and _plan_distance(other.pose.origin, at) < profile.spawn_clear_m:
			return
	car.live = true
	car.lives += 1
	car.edge = edge
	car.along = along
	car.s = s
	car.turning = false
	_enter(car)
	car.speed = car.cruise_mps * 0.5
	car.pose = _pose_on_edge(car)
	car.shape.disabled = false
	spawned += 1


## Fill a car's per-edge state on entering `car.edge`: its length, cruise, the
## next move and where the straight run ends.
func _enter(car: Car) -> void:
	car.length_m = graph.plan_length_of(car.edge)
	car.cruise_mps = graph.speed_limit_of(car.edge) / 3.6 * profile.cruise_of_limit
	var moves: Array[Vector2i] = router.moves_from(car.edge, car.along)
	if moves.is_empty():
		car.next_edge = -1
		car.leave_m = car.length_m
		return
	var move: Vector2i = moves[_rng.randi_range(0, moves.size() - 1)]
	car.next_edge = move.x
	car.next_along = move.y == 1
	var back: float = minf(profile.turn_span_m, car.length_m * 0.4)
	var stop: float = stop_travel_m(car)
	if stop >= 0.0:
		back = minf(back, car.length_m - stop)
	car.leave_m = car.length_m - back
	car.join_m = minf(profile.turn_span_m, graph.plan_length_of(car.next_edge) * 0.4)


## Travel metres from the entry to this edge's stop point, or -1 where no
## junction controls the way.
func stop_travel_m(car: Car) -> float:
	if signals == null:
		return -1.0
	var approach: SignalPlan.Approach = signals.plan.approach_on(car.edge, car.along)
	if approach == null:
		return -1.0
	return approach.stop_m if car.along else car.length_m - approach.stop_m


func _drive(car: Car, delta: float) -> void:
	var target: float = minf(car.cruise_mps, profile.turn_mps) if car.turning else car.cruise_mps
	car.held = Held.NONE
	if not car.turning:
		var stop: float = stop_travel_m(car)
		if stop >= 0.0:
			var to_stop: float = stop - car.s - car.half_length - STOP_SHORT_M
			var light: SignalController.Light = signals.state_of(car.edge, car.along)
			# Only a car whose front is not yet over the line: past it, it goes.
			if (
				to_stop >= -STOP_SHORT_M
				# Judged to the LINE, not the aim short of it: a car crawling at its
				# aim behind a slow leader would read "cannot stop" there, creep on
				# through the amber and meet the red a hair short (seed 4).
				and must_stop(light, to_stop + STOP_SHORT_M, car.speed, profile.brake_max_mps2)
			):
				var limit: float = stopping_speed(to_stop, profile.brake_mps2)
				if limit < target:
					target = limit
					car.held = Held.LIGHT
	var gap: float = _gap_ahead(car)
	if gap < INF:
		var limit: float = stopping_speed(gap - profile.gap_m, profile.brake_mps2)
		if limit < target:
			target = limit
			car.held = Held.CAR
	if car.speed < target:
		car.speed = minf(target, car.speed + profile.accel_mps2 * delta)
	else:
		car.speed = maxf(target, car.speed - profile.brake_max_mps2 * delta)
	_advance(car, car.speed * delta)


## The speed a car can still stop from in `distance_m` at `brake_mps2`.
static func stopping_speed(distance_m: float, brake_mps2: float) -> float:
	return sqrt(2.0 * brake_mps2 * maxf(distance_m, 0.0))


## Whether a car `distance_m` short of its stop point at `speed` must stop for
## `light`: red and red-and-amber always; amber only where it can stop at
## `brake_mps2` — one that cannot goes through. The system passes the HARD rate.
static func must_stop(
	light: SignalController.Light, distance_m: float, speed: float, brake_mps2: float
) -> bool:
	match light:
		SignalController.Light.RED, SignalController.Light.RED_AMBER:
			return true
		SignalController.Light.AMBER:
			return distance_m >= speed * speed / (2.0 * brake_mps2)
	return false


## Bumper to bumper to the nearest car ahead, or INF where none is within
## `look_m`. Three readings, the least wins:
##
## - **On the car's own path** — ahead on its edge its way, or anywhere on the
##   edge it turns into — by the straight line between the two, which is never
##   longer than the road between them, so a bend cannot hide the car ahead.
## - **At the mouth**: a car already turning into the same edge holds this one
##   at the end of its straight run until it is through — the merge.
## - **In the plan cone** — another car within `follow_heading_deg` of its
##   heading and its width of its line, or the player whatever its heading.
func _gap_ahead(car: Car) -> float:
	var forward: Vector3 = -car.pose.basis.z
	var origin: Vector3 = car.pose.origin
	var best: float = INF
	var follow_cos: float = cos(deg_to_rad(profile.follow_heading_deg))
	for other: Car in cars:
		if other == car or not other.live:
			continue
		var apart: float = _plan_distance(origin, other.pose.origin)
		if apart > profile.look_m + other.half_length + car.half_length:
			continue
		if _on_path(car, other):
			best = minf(best, apart - car.half_length - other.half_length)
			continue
		if _merging(car, other):
			best = minf(best, car.leave_m - car.s - car.half_length + profile.gap_m)
			continue
		var heading: Vector3 = -other.pose.basis.z
		if forward.x * heading.x + forward.z * heading.z < follow_cos:
			continue
		var gap: float = _gap_to(
			origin, forward, car, other.pose.origin, other.half_length, other.half_width
		)
		best = minf(best, gap)
	if is_instance_valid(vehicle):
		# The taxi measured as the library's first kind: a saloon either way.
		var player: AABB = _extents[0]
		best = minf(
			best,
			_gap_to(
				origin,
				forward,
				car,
				vehicle.global_position,
				player.size.z * 0.5,
				player.size.x * 0.5
			)
		)
	return best


## Whether `other` is ahead of `car` on the road `car` will drive.
static func _on_path(car: Car, other: Car) -> bool:
	if not car.turning and other.edge == car.edge and other.along == car.along:
		return other.turning or other.s > car.s
	if car.next_edge < 0:
		return false
	if other.edge == car.next_edge and other.along == car.next_along and not other.turning:
		return true
	# Both turning off this edge into the next: the one further round leads.
	return (
		car.turning
		and other.turning
		and other.edge == car.edge
		and other.along == car.along
		and other.next_edge == car.next_edge
		and other.turn_u > car.turn_u
	)


## Whether `other`, off another edge, is turning into the edge `car` is about
## to — a merge `car` waits at the mouth for.
static func _merging(car: Car, other: Car) -> bool:
	return (
		not car.turning
		and car.next_edge >= 0
		and other.turning
		and other.next_edge == car.next_edge
		and other.next_along == car.next_along
		and not (other.edge == car.edge and other.along == car.along)
	)


func _gap_to(
	origin: Vector3, forward: Vector3, car: Car, at: Vector3, half_length: float, half_width: float
) -> float:
	if absf(at.y - origin.y) > LEVEL_APART_M:
		return INF
	var dx: float = at.x - origin.x
	var dz: float = at.z - origin.z
	var ahead: float = dx * forward.x + dz * forward.z
	if ahead <= 0.0 or ahead > profile.look_m:
		return INF
	var across: float = absf(dx * forward.z - dz * forward.x)
	if across > car.half_width + half_width:
		return INF
	return ahead - car.half_length - half_length


## Move a car `metres` along its path, through as many turns and edges as that
## takes.
func _advance(car: Car, metres: float) -> void:
	var left: float = metres
	for _step: int in ADVANCE_STEPS:
		if left <= 0.0 or not car.live:
			break
		if car.turning:
			var to_join: float = car.turn_len - car.turn_u
			if left < to_join:
				car.turn_u += left
				left = 0.0
				break
			left -= to_join
			car.edge = car.next_edge
			car.along = car.next_along
			car.s = car.join_m
			car.turning = false
			_enter(car)
			continue
		var room: float = car.leave_m - car.s
		if left < room:
			car.s += left
			left = 0.0
			break
		car.s = car.leave_m
		left -= room
		if car.next_edge < 0:
			_retire(car)
			return
		_start_turn(car)
	if car.live:
		car.pose = _pose_on_turn(car) if car.turning else _pose_on_edge(car)


func _start_turn(car: Car) -> void:
	var next_length: float = graph.plan_length_of(car.next_edge)
	car.p0 = graph.lane_at(car.edge, _edge_m(car.leave_m, car.length_m, car.along), car.along)
	car.p2 = graph.lane_at(
		car.next_edge, _edge_m(car.join_m, next_length, car.next_along), car.next_along
	)
	var into: Vector3 = _travel_dir(car.edge, car.leave_m, car.length_m, car.along)
	var out: Vector3 = _travel_dir(car.next_edge, car.join_m, next_length, car.next_along)
	car.p1 = turn_control(car.p0, into, car.p2, out)
	car.turn_len = curve_length(car.p0, car.p1, car.p2)
	car.turn_u = 0.0
	car.turning = true


## The curve's middle control point: where the line in along `into` meets the
## line out along `out`, in plan, or the chord's middle where they do not meet
## ahead of both (straight on, or a kink the wrong way).
static func turn_control(p0: Vector3, into: Vector3, p2: Vector3, out: Vector3) -> Vector3:
	var chord: Vector3 = p2 - p0
	var middle: Vector3 = p0.lerp(p2, 0.5)
	var denom: float = into.x * out.z - into.z * out.x
	if absf(denom) < 0.05:
		return middle
	var a: float = (chord.x * out.z - chord.z * out.x) / denom
	var b: float = (into.x * chord.z - chord.x * into.z) / denom
	var reach: float = Vector2(chord.x, chord.z).length()
	if a <= 0.0 or b <= 0.0 or a > reach * 2.0 or b > reach * 2.0:
		return middle
	var meet: Vector3 = p0 + into * a
	meet.y = middle.y
	return meet


static func curve_point(p0: Vector3, p1: Vector3, p2: Vector3, u: float) -> Vector3:
	var v: float = 1.0 - u
	return p0 * (v * v) + p1 * (2.0 * v * u) + p2 * (u * u)


static func curve_length(p0: Vector3, p1: Vector3, p2: Vector3) -> float:
	var total: float = 0.0
	var last: Vector3 = p0
	for index: int in range(1, CURVE_SAMPLES + 1):
		var point: Vector3 = curve_point(p0, p1, p2, float(index) / CURVE_SAMPLES)
		total += last.distance_to(point)
		last = point
	return total


static func _edge_m(travel_m: float, length_m: float, along: bool) -> float:
	return travel_m if along else length_m - travel_m


func _travel_dir(edge: int, travel_m: float, length_m: float, along: bool) -> Vector3:
	var a: Vector3 = graph.point_at(
		edge, _edge_m(maxf(travel_m - 0.5, 0.0), length_m, along) / length_m
	)
	var b: Vector3 = graph.point_at(
		edge, _edge_m(minf(travel_m + 0.5, length_m), length_m, along) / length_m
	)
	var dir := Vector3(b.x - a.x, 0.0, b.z - a.z)
	return dir.normalized() if dir.length_squared() > 0.0 else Vector3.FORWARD


func _pose_on_edge(car: Car) -> Transform3D:
	var at: Vector3 = graph.lane_at(car.edge, _edge_m(car.s, car.length_m, car.along), car.along)
	return Transform3D(_facing(_travel_dir(car.edge, car.s, car.length_m, car.along)), at)


func _pose_on_turn(car: Car) -> Transform3D:
	var u: float = clampf(car.turn_u / car.turn_len, 0.0, 1.0) if car.turn_len > 0.0 else 1.0
	var at: Vector3 = curve_point(car.p0, car.p1, car.p2, u)
	var ahead: Vector3 = curve_point(car.p0, car.p1, car.p2, minf(u + 0.05, 1.0))
	var behind: Vector3 = curve_point(car.p0, car.p1, car.p2, maxf(u - 0.05, 0.0))
	var dir := Vector3(ahead.x - behind.x, 0.0, ahead.z - behind.z)
	return Transform3D(
		_facing(dir.normalized() if dir.length_squared() > 0.0 else -car.pose.basis.z), at
	)


## A basis whose -z is `forward` in plan, upright.
static func _facing(forward: Vector3) -> Basis:
	var back := Vector3(-forward.x, 0.0, -forward.z).normalized()
	return Basis(Vector3.UP.cross(back), Vector3.UP, back)


func _retire(car: Car) -> void:
	car.live = false
	retired += 1
	_hide(car)


func _hide(car: Car) -> void:
	car.shape.disabled = true
	_batches[car.kind].set_instance_transform(
		car.slot, Transform3D(Basis().scaled(Vector3.ZERO), Vector3.ZERO)
	)


static func _plan_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()
