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
## **Parked vehicles are cars ahead that never move** (`P3-3f`, the user's drive
## 2026-10-29: cars drove through them). Each region's `ParkedLayer` is read once
## into `Parked` footprints by the road they were published on, and whether one
## stands is asked each tick. A car brakes for one in its lane as for a car, moves
## out a lane to pass it within `pass_look_m`, and where no whole lane is clear
## edges out just past it — across the centre line of a two-way back street only
## while nothing comes the other way, and a car coming stops for one already out.
## Where even that does not fit, it waits: the roster's pinches are its own.
##
## 🚫 **Not here yet**: a car giving way at an unsignalled
## junction, a car near-missed (`P3-2a` reads parked cars alone), the player's
## red light (`P3-3d`), the heads (`P3-3e`). `--traffic=off` takes it away.

const RoadRouterScript = preload("res://scripts/city/road_router.gd")
const ParkedRoster = preload("res://scripts/city/parked_roster.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")
const PlanScript = preload("res://scripts/traffic/signal_plan.gd")
const ParkedLayer = preload("res://scripts/city/parked_layer.gd")

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
## Parked placements read into the index a tick until the roster is in: about
## 0.6 ms, the roster over about a second.
const PARKED_READS_PER_TICK: int = 16
## What an edge with nothing parked on it answers: one shared empty list, not a
## fresh one a call.
const NO_PARKED: Array = []
## `lamp_bits`' `wink` for both indicators at once.
const HAZARDS: int = 2

## The player's car: the ring is round it, and the car ahead may be it.
@export var vehicle: Node3D
## The scene's signals, which the cars stop at; where none is set the system
## runs its own (a verify tool's).
@export var signals: SignalController

## What stopped a car on its last tick, for the verify tool and the overlay.
enum Held { NONE, LIGHT, CAR, PARKED }


## One car.
class Car:
	extends RefCounted

	## Its place in the fleet: the earlier of two cars waiting on each other
	## goes first.
	var id: int = 0
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
	## Whether the car is out of its turn's lane to pass a parked vehicle.
	var passing: bool = false
	## Whether it stands out past its own lanes on a two-way road, toward or
	## over the centre line, so a car coming the other way stops for it.
	var over_centre: bool = false
	## Whether the car has re-picked its move on this edge for want of a gap.
	var replanned: bool = false
	## The sine of the angle the next turn turns through, and which way it turns
	## (`turn_side`: 1 left, -1 right, 0 straight on).
	var turn_sin: float = 0.0
	var turn_side: int = 0
	## The way it is moving across the lanes this tick: 1 toward the nearside
	## (left), -1 toward the offside, 0 not — its indicator.
	var shift: int = 0
	## Whether the road the next move joins has a lane clear of parked
	## vehicles at its mouth.
	var join_clear: bool = true
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


## One parked vehicle on a road a car can drive, read off its `ParkedLayer`
## (`P3-3f`): its footprint along the edge and across each way's lanes.
class Parked:
	extends RefCounted

	var layer: ParkedLayer
	var index: int = 0
	## The footprint's extent along the edge, in metres from its START.
	var s_from: float = 0.0
	var s_to: float = 0.0
	## Across the lanes, in lane widths from lane 0's centre toward the offside,
	## for travel along the edge (`x` the near side of the footprint, `y` the
	## far) and against it — each corner read at its own point on the road, so
	## a taper toward a junction moves the lanes under it.
	var across_along: Vector2 = Vector2.ZERO
	var across_against: Vector2 = Vector2.ZERO
	## One lane's width at its middle, lane centre to lane centre.
	var lane_m: float = 0.0
	## The sine of the most the road turns within a car's length of the
	## footprint: a car's box keeps its own heading while the lanes bend under
	## its corners, so its half-length times this is added to its half-width.
	var bend: float = 0.0
	var source: String = ""

	func standing() -> bool:
		return layer.is_standing(index)

	## Travel metres the footprint spans for a car driving `along` an edge
	## `length_m` long: `x` its near end, `y` its far.
	func span(along: bool, length_m: float) -> Vector2:
		return Vector2(s_from, s_to) if along else Vector2(length_m - s_to, length_m - s_from)

	## Whether a car `half_width` wide in lane position `lane`, driving `along`,
	## comes within `clear_m` of the footprint's flank.
	func in_lane(along: bool, lane: float, half_width: float, clear_m: float) -> bool:
		var across: Vector2 = across_along if along else across_against
		var room: float = (half_width + clear_m) / lane_m
		return lane + room > across.x and lane - room < across.y


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
## The parked vehicles by the merged edge they stand on (`P3-3f`), and whether
## the scene's layers have been read yet.
var _parked: Dictionary[int, Array] = {}
var _parked_read: bool = false
var _parked_layers: Array[Node] = []
## The library's longest half-length: how far past a footprint a car's box can
## reach, for the bend it reads.
var _reach_m: float = 0.0
## The next placement to read: `x` the layer, `y` its entry.
var _parked_next: Vector2i = Vector2i.ZERO
## What `read_parked` found, by source: in lane 0 of a way traffic drives, in a
## lane past it only, clear of every lane, and of those in a lane, how many
## stand on a road with one lane its way — where a car can only wait.
var parked_report: Dictionary[String, Vector4i] = {}


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
		car.id = cars.find(car)
		car.body.name = "car_%d" % car.id
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
		"pass_look_m": table.pass_look_m,
		"side_clear_m": table.side_clear_m,
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
	VehicleLampsProfile.wire_blink(_meshes)
	for extent: AABB in _extents:
		_reach_m = maxf(_reach_m, extent.size.z * 0.5)
	# `instance_count` allocates the buffer and clears it, so it is grown car by
	# car in `setup` before any transform or livery is written.
	return true


## Index every parked vehicle in `layers` by the merged edge it was published
## on, its footprint measured along the edge and across each way's lanes. Read
## once; whether one stands is asked each tick.
func read_parked(layers: Array[Node]) -> void:
	_queue_parked(layers)
	_read_parked_some(1 << 30)


## Start reading `layers` afresh: what `_read_parked_some` works through.
func _queue_parked(layers: Array[Node]) -> void:
	_parked_read = true
	_parked.clear()
	parked_report.clear()
	_parked_layers = layers
	_parked_next = Vector2i.ZERO


## Read up to `budget` more placements: a footprint is a few dozen projections,
## and the whole roster in one tick was a 43 ms hitch at the start of a drive.
func _read_parked_some(budget: int) -> void:
	var read: int = 0
	while _parked_next.x < _parked_layers.size() and read < budget:
		var layer: ParkedLayer = _parked_layers[_parked_next.x]
		if _parked_next.y >= layer.entry_count():
			_parked_next = Vector2i(_parked_next.x + 1, 0)
			continue
		_read_one_parked(layer, _parked_next.y)
		_parked_next.y += 1
		read += 1


func _read_one_parked(layer: ParkedLayer, index: int) -> void:
	var local: int = layer.edge_of(index)
	if local < 0:
		return
	var edge: int = graph.edge_id_in(layer.resolved_region(), local)
	if edge < 0 or not router.admits_way(edge, true) and not router.admits_way(edge, false):
		return
	var parked: Parked = _measure_parked(edge, layer.obstacle_of(index))
	parked.layer = layer
	parked.index = index
	parked.source = layer.source_of(index)
	if not _parked.has(edge):
		_parked[edge] = []
	_parked[edge].append(parked)
	var typical: float = _extents[0].size.x * 0.5
	var row: Vector4i = parked_report.get(parked.source, Vector4i.ZERO)
	var near: bool = false
	var far: bool = false
	var waits: bool = false
	for along: bool in [true, false]:
		if not router.admits_way(edge, along):
			continue
		var lanes: int = graph.lanes_each_way(edge)
		for lane: int in lanes:
			if parked.in_lane(along, lane, typical, profile.side_clear_m):
				near = near or lane == 0
				far = far or lane > 0
				waits = waits or lanes == 1
	if near:
		row.x += 1
	elif far:
		row.y += 1
	else:
		row.z += 1
	if waits:
		row.w += 1
	parked_report[parked.source] = row


## A parked vehicle's footprint, its `obstacle` corners projected on `edge`.
func _measure_parked(edge: int, obstacle: Dictionary) -> Parked:
	var at: Transform3D = obstacle["transform"]
	var extent: AABB = obstacle["extent"]
	var corners: Array[Vector3] = []
	for corner: int in 4:
		var local := Vector3(
			extent.position.x + (extent.size.x if corner & 1 else 0.0),
			0.0,
			extent.position.z + (extent.size.z if corner & 2 else 0.0)
		)
		corners.append(at * local)
	var middle: Vector3 = at * extent.get_center()
	var s: float = graph.distance_along(edge, middle)
	var parked := Parked.new()
	parked.lane_m = _plan_distance(
		graph.lane_at(edge, s, true, 0.0), graph.lane_at(edge, s, true, 1.0)
	)
	parked.s_from = INF
	parked.s_to = -INF
	parked.across_along = Vector2(INF, -INF)
	parked.across_against = Vector2(INF, -INF)
	for corner: Vector3 in corners:
		var here: float = graph.distance_along(edge, corner)
		parked.s_from = minf(parked.s_from, here)
		parked.s_to = maxf(parked.s_to, here)
		for along: bool in [true, false]:
			var lane0: Vector3 = graph.lane_at(edge, here, along, 0.0)
			var across := Vector3(graph.lane_at(edge, here, along, 1.0) - lane0)
			across.y = 0.0
			var off := Vector3(corner.x - lane0.x, 0.0, corner.z - lane0.z)
			var lanes: float = off.dot(across) / across.length_squared()
			if along:
				parked.across_along = Vector2(
					minf(parked.across_along.x, lanes), maxf(parked.across_along.y, lanes)
				)
			else:
				parked.across_against = Vector2(
					minf(parked.across_against.x, lanes), maxf(parked.across_against.y, lanes)
				)
	var length_m: float = graph.plan_length_of(edge)
	var reach_m: float = _reach_m
	var first: Vector3 = _travel_dir(edge, maxf(parked.s_from - reach_m, 0.0), length_m, true)
	var last: Vector3 = _travel_dir(edge, minf(parked.s_to + reach_m, length_m), length_m, true)
	var middle_dir: Vector3 = _travel_dir(edge, s, length_m, true)
	var turned: float = maxf(
		maxf(first.angle_to(last), first.angle_to(middle_dir)), middle_dir.angle_to(last)
	)
	parked.bend = sin(minf(turned, PI * 0.5))
	return parked


## Every parked vehicle published on `edge`, standing or not.
func parked_on(edge: int) -> Array:
	return _parked.get(edge, NO_PARKED)


## The near end, in travel metres, of the nearest parked vehicle standing on
## `edge` in lane position `lane` of `car` driving `along` it, among those whose
## footprint reaches past `from_m` and starts before `to_m`; INF for none. The
## window is tested first and nothing is allocated: every car asks this every
## tick.
func _nearest_parked(
	edge: int, along: bool, length_m: float, lane: float, car: Car, from_m: float, to_m: float
) -> float:
	var nearest: float = INF
	for parked: Parked in _parked.get(edge, NO_PARKED):
		var span: Vector2 = parked.span(along, length_m)
		if span.y <= from_m or span.x >= to_m or span.x >= nearest:
			continue
		var reach: float = car.half_width + car.half_length * parked.bend
		if parked.in_lane(along, lane, reach, profile.side_clear_m) and parked.standing():
			nearest = span.x
	return nearest


func _pick_kind() -> int:
	return _rng.rand_weighted(_weights)


func _physics_process(delta: float) -> void:
	step(delta)


## One tick: spawn into the ring, drive every car, retire what left it.
func step(delta: float) -> void:
	if not _parked_read and is_inside_tree():
		_queue_parked(get_tree().get_nodes_in_group(ParkedLayer.GROUP))
	_read_parked_some(PARKED_READS_PER_TICK)
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
			_write_lamps(car, lamp_bits(true, car.braking, _winking(car)))


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
	var lane: float = float(_rng.randi_range(0, graph.lanes_each_way(edge) - 1))
	var half_length: float = _extents[car.kind].size.z * 0.5
	var room: float = (cruise * 0.5) ** 2 / profile.brake_mps2 + profile.look_m * 0.25
	if (
		_nearest_parked(
			edge,
			along,
			length_m,
			lane,
			car,
			s - half_length - profile.gap_m,
			s + half_length + room
		)
		< INF
	):
		return
	car.live = true
	car.lives += 1
	car.edge = edge
	car.along = along
	car.s = s
	car.turning = false
	car.crossed.clear()
	car.lane = lane
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
	car.passing = false
	car.over_centre = false
	_plan_move(car)


func _cruise_of(edge: int) -> float:
	return graph.speed_limit_of(edge) / 3.6 * profile.cruise_of_limit


## Pick the car's next move, through the junction's inside roads, and where and
## in which lane it leaves for it — another where parked vehicles block every
## lane of the road it would join at the mouth, up to `REPLAN_TRIES`.
func _plan_move(car: Car) -> void:
	for _try: int in REPLAN_TRIES:
		_plan_one_move(car)
		if car.next_edge < 0 or car.join_clear:
			return


func _plan_one_move(car: Car) -> void:
	car.via.clear()
	car.join_clear = true
	car.turn_side = 0
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
	car.turn_sin = absf(into.cross(out).y)
	car.turn_side = side
	if side > 0:
		car.lane_out = 0.0
		car.next_lane = 0.0
	elif side < 0:
		car.lane_out = float(here - 1)
		car.next_lane = float(there - 1)
	else:
		car.lane_out = minf(car.lane, float(here - 1))
		car.next_lane = minf(car.lane_out, float(there - 1))
	var join: float = _join_lane(car, there)
	if join < 0.0 and side == 0:
		# Straight on into a mouth blocked in this lane: across to one that is
		# clear before the junction.
		for lane: int in mini(here, there):
			if not _join_blocked(car, float(lane), float(lane)):
				car.lane_out = float(lane)
				join = float(lane)
				break
	car.join_clear = join >= 0.0
	car.next_lane = join if car.join_clear else car.next_lane


## The lane nearest `car.next_lane` the next road has clear of parked vehicles
## from the turn's lane across to it, for `lane_change_m` past the join, or -1
## where none is.
func _join_lane(car: Car, lanes: int) -> float:
	var best: float = -1.0
	var nearest: float = INF
	for lane: int in lanes:
		var off: float = absf(float(lane) - car.next_lane)
		if off < nearest and not _join_blocked(car, car.lane_out, float(lane)):
			nearest = off
			best = float(lane)
	return best


## Whether a parked vehicle stands within `lane_change_m` past the join
## anywhere between lane positions `from` and `to` of the next road: a turn
## moving across lanes passes every position between, half a lane at a time.
func _join_blocked(car: Car, from: float, to: float) -> bool:
	var steps: int = ceili(absf(to - from) * 2.0)
	for at: int in steps + 1:
		var lane: float = lerpf(from, to, float(at) / maxf(float(steps), 1.0))
		if _nearest_past_join(car, lane, car.join_m + profile.lane_change_m) < INF:
			return true
	return false


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
		car.next_lane,
		car.turn_side,
		car.turn_sin,
		car.join_clear
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
	car.turn_side = kept[7]
	car.turn_sin = kept[8]
	car.join_clear = kept[9]


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
	if car.turning:
		car.shift = 0
		return
	var goal: float = _lane_goal(car)
	car.passing = goal != car.lane_out
	car.shift = 0 if is_equal_approx(car.lane, goal) else (1 if goal < car.lane else -1)
	car.over_centre = (
		not graph.is_one_way(car.edge)
		and car.lane > float(graph.lanes_each_way(car.edge) - 1) + 0.01
	)
	if is_equal_approx(car.lane, goal):
		return
	var toward: float = move_toward(car.lane, goal, metres / profile.lane_change_m)
	if not _lane_blocked(car, toward):
		car.lane = toward
		return
	if goal != car.lane_out:
		return
	var needed: float = absf(car.lane_out - car.lane) * profile.lane_change_m
	if not car.replanned and car.leave_m - car.s < needed:
		car.replanned = true
		_replan_for_lane(car)


## The lane `car` makes for: its turn's, unless a parked vehicle stands in
## that lane within `pass_look_m` ahead — then the clear lane nearest it, to
## pass and come back (`P3-3f`). With no clear lane, the turn's: it waits.
func _lane_goal(car: Car) -> float:
	if not _parked.has(car.edge) or not _parked_ahead(car, car.lane_out):
		return car.lane_out
	var best: float = -1.0
	var nearest: float = INF
	for lane: int in graph.lanes_each_way(car.edge):
		var off: float = absf(float(lane) - car.lane_out)
		if off < nearest and not _parked_ahead(car, float(lane)):
			nearest = off
			best = float(lane)
	if best >= 0.0:
		return best
	var out: float = _edge_out(car)
	return out if out >= 0.0 else car.lane_out


## No whole lane clear: the lane position nearest the turn's lane that keeps
## `side_clear_m` from every parked vehicle in the way and the flank inside the
## kerbs — between two rows, against the near kerb, or across the centre line
## on a two-way road, which a car starts only while nothing comes the other way
## (`parked.py`'s back street, "parked on one side and passed in the lane
## left"). -1 where there is none.
func _edge_out(car: Car) -> float:
	var blocks: Array[Vector2] = []
	var lane_m: float = 0.0
	var until_m: float = car.s
	for parked: Parked in parked_on(car.edge):
		var span: Vector2 = parked.span(car.along, car.length_m)
		if (
			not parked.standing()
			or span.y <= car.s - car.half_length - profile.gap_m
			or span.x >= car.s + car.half_length + profile.pass_look_m
		):
			continue
		var across: Vector2 = parked.across_along if car.along else parked.across_against
		var room: float = (
			(car.half_width + car.half_length * parked.bend + profile.side_clear_m) / parked.lane_m
		)
		blocks.append(Vector2(across.x - room, across.y + room))
		lane_m = parked.lane_m
		until_m = maxf(until_m, span.y)
	if lane_m <= 0.0:
		return -1.0
	# The flank may reach either kerb: the published width runs kerb to kerb,
	# and the room is kept from the parked vehicles, not from a kerb face.
	var low: float = -0.5 + car.half_width / lane_m
	var high: float = float(graph.lane_positions(car.edge)) - 0.5 - car.half_width / lane_m
	var candidates: Array[float] = [low, high]
	for block: Vector2 in blocks:
		# A centimetre past each: exactly on a block's edge reads as inside it.
		candidates.append(block.x - 0.01 / lane_m)
		candidates.append(block.y + 0.01 / lane_m)
	var out: float = -1.0
	var nearest: float = INF
	for at: float in candidates:
		if at < low or at > high or absf(at - car.lane_out) >= nearest:
			continue
		var clear: bool = true
		for block: Vector2 in blocks:
			if block.x < at and at < block.y:
				clear = false
				break
		if clear:
			nearest = absf(at - car.lane_out)
			out = at
	if nearest == INF:
		return -1.0
	var lanes: int = graph.lanes_each_way(car.edge)
	var crosses: bool = not graph.is_one_way(car.edge) and out > float(lanes - 1)
	if crosses and not car.over_centre and not _oncoming_clear(car, until_m):
		return -1.0
	return out


## Whether no car coming the other way on `car`'s road, or turning into it that
## way, is between `car` and `pass_look_m` past `until_m`. Two cars each
## waiting at a parked vehicle for the other: the earlier in the fleet goes.
func _oncoming_clear(car: Car, until_m: float) -> bool:
	for other: Car in cars:
		if other == car or not other.live:
			continue
		var at: float
		if not other.turning and other.edge == car.edge and other.along != car.along:
			at = car.length_m - other.s
		elif other.turning and other.next_edge == car.edge and other.next_along != car.along:
			at = car.length_m - other.join_m
		else:
			continue
		if at < car.s - car.half_length - other.half_length or at > until_m + profile.pass_look_m:
			continue
		if (
			car.held == Held.PARKED
			and other.held == Held.PARKED
			and other.speed < STOPPED_MPS
			and car.id < other.id
		):
			continue
		return false
	return true


## Whether a parked vehicle stands in lane `lane` from `car`'s tail to
## `pass_look_m` past its nose.
func _parked_ahead(car: Car, lane: float) -> bool:
	return (
		_nearest_parked(
			car.edge,
			car.along,
			car.length_m,
			lane,
			car,
			car.s - car.half_length - profile.gap_m,
			car.s + car.half_length + profile.pass_look_m
		)
		< INF
	)


## Whether a car on `car`'s road, its way, stands beside it in the lane
## position `toward`, or a parked vehicle beside it does on the side it moves to.
func _lane_blocked(car: Car, toward: float) -> bool:
	for parked: Parked in _parked.get(car.edge, NO_PARKED):
		var span: Vector2 = parked.span(car.along, car.length_m)
		if span.x >= car.s + car.half_length or span.y <= car.s - car.half_length - profile.gap_m:
			continue
		var reach: float = car.half_width + car.half_length * parked.bend
		if not parked.in_lane(car.along, toward, reach, profile.side_clear_m):
			continue
		if not parked.standing():
			continue
		# Beside it: only a move AWAY from its side is free.
		var across: Vector2 = parked.across_along if car.along else parked.across_against
		var side: float = (across.x + across.y) * 0.5 - car.lane
		if side * (toward - car.lane) > 0.0:
			return true
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
	var to_stop: float = INF
	var light: SignalController.Light = SignalController.Light.GREEN
	if not car.turning:
		var stop: float = stop_travel_m(car)
		if stop >= 0.0:
			to_stop = stop - car.s - car.half_length - STOP_SHORT_M
			light = signals.state_of(car.edge, car.along)
	elif car.next_edge >= 0:
		# Through the curve to the next road's line: a short approach's stands a
		# few metres past the join, too near to stop for once the turn has ended
		# (edge 203, a minibus over it at 3.7 m/s, 2026-10-30).
		var next_length: float = graph.plan_length_of(car.next_edge)
		var next_stop: float = _stop_along_m(car.next_edge, car.next_along, next_length)
		if next_stop >= 0.0:
			to_stop = (
				car.turn_len - car.turn_u + next_stop - car.join_m - car.half_length - STOP_SHORT_M
			)
			light = signals.state_of(car.next_edge, car.next_along)
	# Only a car whose front is not yet over the line: past it, it goes.
	if (
		to_stop < INF
		and to_stop >= -STOP_SHORT_M
		# Judged to the LINE, not the aim short of it: a car crawling at its aim
		# behind a slow leader would read "cannot stop" there, creep on through
		# the amber and meet the red a hair short (seed 4).
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
	var parked_gap: float = _parked_gap(car)
	if parked_gap < INF:
		var limit: float = stopping_speed(parked_gap - profile.gap_m, profile.brake_mps2)
		if limit < target:
			target = limit
			car.held = Held.PARKED
	if car.held == Held.PARKED:
		# Pulling out from behind it at the turning pace, standing or not: a car
		# that changed lane only with the metres it drove would never leave.
		# Topped up to the turning pace: `_advance` moves it by what it drove.
		_change_lane(car, maxf(profile.turn_mps - car.speed, 0.0) * delta)
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
		if _on_path(car, other) or _coming_over(car, other):
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


## Bumper to the nearest parked vehicle standing in `car`'s lane ahead within
## `look_m`, on its edge or the one its turn joins, or INF. On the next edge it
## is measured as if the turn were straight: never longer than the road.
func _parked_gap(car: Car) -> float:
	var best: float = INF
	var front: float = car.s + car.half_length
	if not car.turning:
		var near: float = _nearest_parked(
			car.edge,
			car.along,
			car.length_m,
			car.lane,
			car,
			car.s - car.half_length,
			front + profile.look_m
		)
		if near < INF:
			best = maxf(near - front, 0.0)
	if car.next_edge < 0:
		return best
	var to_join: float = car.turn_len - car.turn_u if car.turning else car.leave_m - front
	if to_join > profile.look_m:
		return best
	var past: float = _nearest_past_join(car, car.next_lane, car.join_m + profile.look_m)
	if past < INF:
		# Negative where it reaches back past the join: the car stops short of
		# the turn rather than turning into it.
		best = minf(best, maxf(to_join + past - car.join_m, 0.0))
	return best


## `_nearest_parked` on the road `car`'s turn joins, past the join, before
## `to_m`. Within two car-lengths of the join the car's box still lies across
## the lanes as it comes out of the turn, so its reach there is its half-length
## times the turn's sine more.
func _nearest_past_join(car: Car, lane: float, to_m: float) -> float:
	var nearest: float = INF
	var next_length: float = graph.plan_length_of(car.next_edge)
	for parked: Parked in _parked.get(car.next_edge, NO_PARKED):
		var span: Vector2 = parked.span(car.next_along, next_length)
		if span.y <= car.join_m or span.x >= to_m or span.x >= nearest:
			continue
		var swing: float = car.turn_sin if span.x < car.join_m + 4.0 * car.half_length else 0.0
		var reach: float = car.half_width + car.half_length * maxf(swing, parked.bend)
		if parked.in_lane(car.next_along, lane, reach, profile.side_clear_m) and parked.standing():
			nearest = span.x
	return nearest


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


## Whether `other` comes the other way down `car`'s road, out over the centre
## line round a parked vehicle, ahead of it: `car` stops short and lets it by.
static func _coming_over(car: Car, other: Car) -> bool:
	return (
		other.over_centre
		and not car.turning
		and not other.turning
		and other.edge == car.edge
		and other.along != car.along
		and car.length_m - other.s > car.s
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
## encoding: 2 for a running car, 4 more while it brakes, 8 for the left
## indicator and 16 for the right — `wink` 1 left, -1 right, `HAZARDS` both,
## the stopping parked car's (`P3-3f`). 0 is a switched-off car.
static func lamp_bits(running: bool, braking: bool, wink: int = 0) -> int:
	var bits: int = (2 if running else 0) + (4 if running and braking else 0)
	if wink == 1 or wink == HAZARDS:
		bits += 8
	if wink == -1 or wink == HAZARDS:
		bits += 16
	return bits


## The indicator `car` shows: its turn's side from `lane_change_m` before the
## mouth until it has joined (left 1, right -1), else the side it is changing
## lane to, else none — never for straight on.
func _winking(car: Car) -> int:
	if car.turning:
		return car.turn_side
	if car.turn_side != 0 and car.next_edge >= 0 and car.leave_m - car.s < profile.lane_change_m:
		return car.turn_side
	return car.shift


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


## The mesh box `car` is drawn and collides as, in its own frame.
func extent_of(car: Car) -> AABB:
	return _extents[car.kind]


static func _plan_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()
