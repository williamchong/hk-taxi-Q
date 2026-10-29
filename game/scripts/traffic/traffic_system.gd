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
## **A turn is a curve, not a jump, mouth to mouth.** A car leaves its edge where
## the drawn ribbon meets the junction (`trim_m`, the stop line's own point;
## `turn_span_m` where a bundle publishes none) and joins the road it leaves by at
## that road's mouth, along a quadratic curve through where the two lanes cross.
## A road INSIDE the junction (`RoadGraph.is_stub`) is crossed in the same curve
## and never driven along — the user watched cars run into a crossroad's middle
## on the stub before turning (2026-10-29) — and is the car's `via`.
##
## **The lane is the turn's.** A car turns left from the nearside lane and right
## from the offside, into the same side of the road it joins, and straight on
## keeps its lane; it moves between lanes over `lane_change_m` before the mouth.
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
## 🚫 **Not here yet**: a car giving way at an unsignalled
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
## Lanes apart under which two cars share one, in lane widths.
const SAME_LANE: float = 0.75
## Moves a car blocked out of its turn's lane tries before it turns from where
## it is.
const REPLAN_TRIES: int = 6

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
	## The junction's inside roads the next turn crosses, `(edge, along)`.
	var via: Array[Vector2i] = []
	## The ones the turn just finished crossed, for the verify tool's arc check.
	var crossed: Array[Vector2i] = []
	## The lane the car stands in, the one it moves to for its turn, and the one
	## it joins the next road in (0 the nearside, fractional mid-change).
	var lane: float = 0.0
	var lane_out: float = 0.0
	var next_lane: float = 0.0
	## Whether the car has re-picked its move on this edge for want of a gap.
	var replanned: bool = false
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
	## Slowing or standing: the brake lamps (`vehicle_body.gdshader`).
	var braking: bool = false
	## The livery `ParkedRoster` drew, alpha 1 to apply or 0 for none.
	var livery: Color
	## The lamp bits last written, so a car is written only when they change.
	var written: int = -1
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
	_admitted = PackedInt32Array()
	for edge: int in router.admitted_edge_ids():
		if not graph.is_stub(edge):
			_admitted.append(edge)
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
		car.livery = ParkedRoster.livery(_rng.randi() & 0xFFFF, palette)
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
		"lane_change_m": table.lane_change_m,
		"straight_deg": table.straight_deg,
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
			_write_lamps(car, lamp_bits(true, car.braking))


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
	# Never where a red ahead could not be stopped for from the spawn speed.
	var stop: float = _stop_along_m(edge, along, length_m)
	var cruise: float = _cruise_of(edge)
	if stop >= 0.0 and stop - s < (cruise * 0.5) ** 2 / profile.brake_mps2 + profile.look_m * 0.25:
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
	car.crossed.clear()
	car.lane = float(_rng.randi_range(0, graph.lanes_each_way(edge) - 1))
	_enter(car)
	car.speed = car.cruise_mps * 0.5
	car.pose = _pose_on_edge(car)
	car.shape.disabled = false
	spawned += 1


## Fill a car's per-edge state on entering `car.edge`: its length, cruise, the
## next move and where the straight run ends.
func _enter(car: Car) -> void:
	car.length_m = graph.plan_length_of(car.edge)
	car.cruise_mps = _cruise_of(car.edge)
	car.replanned = false
	_plan_move(car)


func _cruise_of(edge: int) -> float:
	return graph.speed_limit_of(edge) / 3.6 * profile.cruise_of_limit


## Pick the car's next move, through the junction's inside roads, and where and
## in which lane it leaves for it.
func _plan_move(car: Car) -> void:
	car.via.clear()
	car.lane_out = car.lane
	var move: Vector2i = _pick_move(car.edge, car.along)
	# Through the junction's inside roads to the road out, a bounded walk.
	while move.x >= 0 and graph.is_stub(move.x) and car.via.size() < ADVANCE_STEPS:
		car.via.append(move)
		move = _pick_move(move.x, move.y == 1)
	if move.x < 0:
		car.next_edge = -1
		car.leave_m = car.length_m
		return
	car.next_edge = move.x
	car.next_along = move.y == 1
	var back: float = _mouth_m(car.edge, car.along, false)
	var stop: float = stop_travel_m(car)
	if stop >= 0.0:
		back = minf(back, car.length_m - stop)
	car.leave_m = maxf(car.length_m - back, car.s)
	car.join_m = _mouth_m(car.next_edge, car.next_along, true)
	_pick_lanes(car)


## One of the legal moves off a way at random, or `(-1, 0)` at a dead end.
func _pick_move(edge: int, along: bool) -> Vector2i:
	var moves: Array[Vector2i] = router.moves_from(edge, along)
	if moves.is_empty():
		return Vector2i(-1, 0)
	return moves[_rng.randi_range(0, moves.size() - 1)]


## Travel metres from a way's mouth at its entry end (`entry`) or its exit end
## to that end: the published `trim_m`, or `turn_span_m` where none is, never
## past 40% of the edge.
func _mouth_m(edge: int, along: bool, entry: bool) -> float:
	var trim: Vector2 = graph.trim_of(edge)
	var at_start: bool = along == entry
	var mouth: float = trim.x if at_start else trim.y
	if mouth <= 0.0:
		mouth = profile.turn_span_m
	return minf(mouth, graph.plan_length_of(edge) * 0.4)


## The lane the car must reach by the mouth and the one it joins the next road
## in, by which way the move turns (left-hand traffic: left is nearside).
func _pick_lanes(car: Car) -> void:
	var into: Vector3 = _travel_dir(car.edge, car.leave_m, car.length_m, car.along)
	var next_length: float = graph.plan_length_of(car.next_edge)
	var out: Vector3 = _travel_dir(car.next_edge, car.join_m, next_length, car.next_along)
	var here: int = graph.lanes_each_way(car.edge)
	var there: int = graph.lanes_each_way(car.next_edge)
	var side: int = turn_side(into, out, profile.straight_deg)
	if side > 0:
		car.lane_out = 0.0
		car.next_lane = 0.0
	elif side < 0:
		car.lane_out = float(here - 1)
		car.next_lane = float(there - 1)
	else:
		car.lane_out = minf(car.lane, float(here - 1))
		car.next_lane = minf(car.lane_out, float(there - 1))


## Up to `REPLAN_TRIES` other moves, the first whose lane the car is already in
## kept; where none is, the first plan stands.
func _replan_for_lane(car: Car) -> void:
	var kept: Array = [
		car.next_edge,
		car.next_along,
		car.via.duplicate(),
		car.leave_m,
		car.join_m,
		car.lane_out,
		car.next_lane
	]
	for _try: int in REPLAN_TRIES:
		_plan_move(car)
		if car.next_edge >= 0 and same_lane(car.lane, car.lane_out):
			car.lane_out = car.lane
			return
	car.next_edge = kept[0]
	car.next_along = kept[1]
	car.via.assign(kept[2])
	car.leave_m = kept[3]
	car.join_m = kept[4]
	car.lane_out = kept[5]
	car.next_lane = kept[6]


## 1 for a left turn, -1 for a right, 0 for straight on within `straight_deg`.
static func turn_side(into: Vector3, out: Vector3, straight_deg: float) -> int:
	var angle: float = rad_to_deg(Vector2(into.x, into.z).angle_to(Vector2(out.x, out.z)))
	if absf(angle) < straight_deg:
		return 0
	# Plan x right, z toward the camera: a negative angle turns to the left.
	return 1 if angle < 0.0 else -1


## Move a car `metres` worth of the way toward its turn's lane, one lane per
## `lane_change_m` travelled, and only while no car in the lane it moves into
## stands beside it. A car blocked with too little road left to get across
## re-picks, once, among moves its own lane suits — a missed turn, never a
## turn across the car beside it. A short road with nobody beside is changed
## across as far as it goes, and the turn starts from where the car is.
func _change_lane(car: Car, metres: float) -> void:
	if car.turning or is_equal_approx(car.lane, car.lane_out):
		return
	var toward: float = move_toward(car.lane, car.lane_out, metres / profile.lane_change_m)
	if not _lane_blocked(car, toward):
		car.lane = toward
		return
	var needed: float = absf(car.lane_out - car.lane) * profile.lane_change_m
	if not car.replanned and car.leave_m - car.s < needed:
		car.replanned = true
		_replan_for_lane(car)


## Whether a car on `car`'s road, its way, stands beside it in the lane
## position `toward`.
func _lane_blocked(car: Car, toward: float) -> bool:
	for other: Car in cars:
		if (
			other == car
			or not other.live
			or other.turning
			or other.edge != car.edge
			or other.along != car.along
			or is_equal_approx(other.lane, car.lane)
		):
			continue
		var beside: float = car.half_length + other.half_length + profile.gap_m
		if absf(other.s - car.s) < beside and absf(other.lane - toward) < 1.0:
			return true
	return false


## Travel metres from the entry to this edge's stop point, or -1 where no
## junction controls the way.
func stop_travel_m(car: Car) -> float:
	return _stop_along_m(car.edge, car.along, car.length_m)


func _stop_along_m(edge: int, along: bool, length_m: float) -> float:
	if signals == null:
		return -1.0
	var approach: SignalPlan.Approach = signals.plan.approach_on(edge, along)
	if approach == null:
		return -1.0
	return approach.stop_m if along else length_m - approach.stop_m


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
	car.braking = target < car.speed or car.speed < STOPPED_MPS
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


## Whether `other` is ahead of `car` in the lane `car` will drive: a car in the
## next lane over is passed, not followed.
static func _on_path(car: Car, other: Car) -> bool:
	if not car.turning and other.edge == car.edge and other.along == car.along:
		if other.turning:
			return same_lane(car.lane, other.lane_out)
		return other.s > car.s and same_lane(car.lane, other.lane)
	if car.next_edge < 0:
		return false
	if other.edge == car.next_edge and other.along == car.next_along and not other.turning:
		return same_lane(car.next_lane, other.lane)
	# Both turning into one lane, off this edge or another: the one nearer its
	# join leads — two approaches can run together on one stage.
	return (
		car.turning
		and other.turning
		and other.next_edge == car.next_edge
		and other.next_along == car.next_along
		and same_lane(car.next_lane, other.next_lane)
		and other.turn_len - other.turn_u < car.turn_len - car.turn_u
	)


## Whether `other`, off another edge, is turning into the lane `car` is about
## to join — a merge `car` waits at the mouth for.
static func _merging(car: Car, other: Car) -> bool:
	return (
		not car.turning
		and car.next_edge >= 0
		and other.turning
		and other.next_edge == car.next_edge
		and other.next_along == car.next_along
		and same_lane(car.next_lane, other.next_lane)
		and not (other.edge == car.edge and other.along == car.along)
	)


## Two lane positions close enough that one car is behind the other: under
## `SAME_LANE`, so a car part way through a change is in both.
static func same_lane(one: float, two: float) -> bool:
	return absf(one - two) < SAME_LANE


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
			car.crossed = car.via.duplicate()
			car.lane = car.next_lane
			_enter(car)
			continue
		var room: float = car.leave_m - car.s
		_change_lane(car, minf(left, room))
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
	car.p0 = graph.lane_at(
		car.edge, _edge_m(car.leave_m, car.length_m, car.along), car.along, car.lane
	)
	car.p2 = graph.lane_at(
		car.next_edge,
		_edge_m(car.join_m, next_length, car.next_along),
		car.next_along,
		car.next_lane
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
	var at: Vector3 = graph.lane_at(
		car.edge, _edge_m(car.s, car.length_m, car.along), car.along, car.lane
	)
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


## `INSTANCE_CUSTOM.a` above the livery's bit, `vehicle_body.gdshader`'s
## encoding: 2 for a running car, 4 more while it brakes. 0 is a parked car.
static func lamp_bits(running: bool, braking: bool) -> int:
	return (2 if running else 0) + (4 if running and braking else 0)


func _write_lamps(car: Car, bits: int) -> void:
	if bits == car.written:
		return
	car.written = bits
	var data: Color = car.livery
	data.a = car.livery.a + bits
	_batches[car.kind].set_instance_custom_data(car.slot, data)


func _hide(car: Car) -> void:
	_write_lamps(car, lamp_bits(false, false))
	car.shape.disabled = true
	_batches[car.kind].set_instance_transform(
		car.slot, Transform3D(Basis().scaled(Vector3.ZERO), Vector3.ZERO)
	)


static func _plan_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()
