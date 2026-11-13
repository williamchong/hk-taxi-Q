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
## **The horn** (`Q178`) is for the taxi alone: cut up, or stood behind it with no
## red to wait for (`wants_horn`); and on the loop's awards, the car the taxi
## close-called, and on a docked hit every car that had the taxi ahead or was the
## one struck (`react_to`). A parked taxi hears nothing. Each kind has its own
## horn, and each honk is a pattern of presses drawn by why it honks, growing
## with the car's temper (`P3-79`), off its own RNG so no car moves for it.
##
## 🔴 **Kinematic, not simulated — until the taxi hits it.** A car is a position
## along its edge and a speed; its body is an `AnimatableBody3D` moved to where it
## is each tick. Nothing else pushes it off its lane: not another car, not a tram.
##
## **The taxi knocks a car by its mass** (`Q180`, reversing the line above on the
## user's ask, 2026-11-04). The body is `Pushable`: the taxi's contact hands the
## impulse its mass gives to `take_push`, and the car leaves its lane — sliding on
## its tyres (`_slide`: across them at the road tyre's grip, along them coasting
## for `react_s` and then braking), turning if it was hit off its centre, stopped
## by what it meets, on its hazards. The others stop for it as for a car whatever
## its heading, and pass it once it has settled as a parked vehicle. Then it tries
## to drive on (`_try_recover`): back into its nearside lane on the road it stands
## by, in one curve, if it faces a way it may drive and the way is clear; where it
## cannot it stands until the ring takes it. `--push=off` leaves every car a wall.
##
## **A car gives way at its line** (`_give_way_gap`) to a car in the junction whose
## turn crosses its own, and to one still coming that goes first — straight on
## before left before right, then the earlier in the fleet — with or without a
## light: a right turn on green filters through the oncoming flow.
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
## **Buses and green minibuses keep to their published routes** (`P3-78`, `Q182`).
## `buses` more slots than `cars` spawn only on a `BusRoutes` route, at one of its
## stops, picked by the route's departures in the game hour, and drive from stop to
## stop by `RoadRouter.goal_tree` — a search over the same legal arcs a wandering
## car picks from, toward the way of the edge the stop's kerb flows — standing
## `dwell_s` at each in the nearside lane. Past its run's last stop a vehicle
## wanders; knocked by the taxi it leaves its route and drives on as any car. A
## minibus without a route wears `wander_liveries` (red), one on a route
## `route_liveries` (green): the colour is the licence (`Q167`).
##
## 🚫 **Not here yet**: priority off TD's give-way lines and plates — the order is
## the turn's, not the road's — and giving way to the taxi or a tram crossing.
## `--traffic=off` takes it away.

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
## `lamp_bits`' `wink`: the left indicator, the right, and both at once.
const WINK_LEFT: int = 1
const WINK_RIGHT: int = -1
const HAZARDS: int = 2
## The batched body's lamp and fade bits (`VehicleBodyBatch`, where the shader's
## spelling lives), under the names this system and its verify tools use.
const LAMP_BRAKE: int = VehicleBodyBatch.LAMP_BRAKE
const LAMP_LEFT: int = VehicleBodyBatch.LAMP_LEFT
const LAMP_RIGHT: int = VehicleBodyBatch.LAMP_RIGHT
const ROOF_SIGN: int = VehicleBodyBatch.ROOF_SIGN
const FADE_BIT: int = VehicleBodyBatch.FADE_BIT
const FADE_STEPS: int = VehicleBodyBatch.FADE_STEPS
## A spawn or a car is looked at this high off its road, about its roof (`Q214`).
const SIGHT_HEIGHT_M: float = 1.5
## What the ETL's colliders import as — a building tile's `<tile>_collision`, a
## road chunk's `road_surface_collision` — so the view's ray tells the city from
## a car or a parked vehicle in the way (`Q214`).
const CITY_COLLIDER_SUFFIX: String = "_collision"
## Bodies a sight line may pass through looking for the city: the taxi, cars,
## parked vehicles, trees.
const SIGHT_HITS: int = 6

## What `FareSystem` finds the moving cars by, for the near miss.
const GROUP: StringName = &"traffic_system"
## Centre to centre past touching a car is still the car struck, in plan metres:
## the box is the mesh's bound, and the contact a tick old.
const STRUCK_SLACK_M: float = 0.5
## A knocked car's sweep is tested this far above the road, so the road it
## slides on is not what stops it.
const SWEEP_LIFT_M: float = 0.3
## Under this spin, in rad/s, a knocked car under `STOPPED_MPS` has settled.
const STILL_SPIN: float = 0.05
## Pieces a knocked car's way back to its lane is tested in.
const RECOVER_SAMPLES: int = 6
## Under this many metres to one side of where it stands, a rejoin is straight on
## and winks nothing.
const RECOVER_STRAIGHT_M: float = 0.5

## The trams (`P3-4`): a car follows one as it follows a car, and waits behind one
## at its stop. A car does not pass a tram: on Hennessy Road nothing lawfully does.
var trams: TramSystem

## The routes the routed fleet keeps to (`P3-78`): read at `setup` unless a caller
## set them first.
var bus_routes: BusRoutes = null
## The hour the routed fleet spawns by; NAN reads the lighting rig's.
var hour_override: float = NAN
## For the verify tool: stops a routed vehicle stood at, drove past, could not
## route to, and routed vehicles placed.
var stops_served: int = 0
var stops_missed: int = 0
var stops_unreachable: int = 0
var routed_spawned: int = 0
## For the verify tool: kerbside stops picked, stood at, and driven past.
var kerb_picked: int = 0
var kerb_served: int = 0
var kerb_missed: int = 0
var kerb_unlawful: int = 0

## The player's car: the ring is round it, and the car ahead may be it.
@export var vehicle: Node3D
## The scene's signals, which the cars stop at; where none is set the system
## runs its own (a verify tool's).
@export var signals: SignalController

## What stopped a car on its last tick, for the verify tool and the overlay.
enum Held { NONE, LIGHT, CAR, PARKED, TAXI, GIVE_WAY, DWELL }


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
	## Its index among its kind's drawn instances; -1 while it is hidden.
	var slot: int = -1
	## Whether it is a taxi, and whether its roof sign is lit for hire.
	var taxi: bool = false
	var for_hire: bool = false
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
	## The way it is moving across the lanes: 1 toward the nearside (left), -1
	## toward the offside, 0 not — its indicator. Off the goal, not the move, so
	## a car waiting to pull out shows where it is going.
	var shift: int = 0
	## The side of the turn just finished, still winked until the car is
	## `held_until_m` travel metres into the road it joined (`wink_hold_m`).
	var held_side: int = 0
	var held_until_m: float = 0.0
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
	## Seconds until this car may sound its horn again.
	var horn_wait: float = 0.0
	## How cross it is with the taxi, 0 to `horn_temper_max`, as of `temper_at_s`.
	var temper: float = 0.0
	var temper_at_s: float = 0.0
	## Seconds it has stood behind the taxi with no light to wait for.
	var taxi_stood_s: float = 0.0
	## The livery `ParkedRoster` drew, alpha 1 to apply or 0 for none.
	var livery: Color
	## The lamp bits last written, so a car is written only when they change.
	var written: int = -1
	## How whole it is drawn (`Q214`): 1 opaque, 0 gone. A car placed in view
	## fades in from 0; one leaving in view fades out to 0 and is then retired.
	var fade: float = 1.0
	var leaving: bool = false
	## Seconds it has been out of view past `retire_m`.
	var unseen_s: float = 0.0
	var body: AnimatableBody3D
	var shape: CollisionShape3D
	## What `near_cars` hands the near miss, made once like a parked one's (`Q175`).
	var obstacle: Dictionary
	## Travel metres on the road it joined by until its tail is a length past
	## the join — its path's reach — and out of the junction: until then it is
	## still in it, on its last turn's curve.
	var joined_until_m: float = 0.0
	## Its turn through the junction in plan points, and the tick it was read on.
	var path: PackedVector3Array = []
	var path_tick: int = -1
	## Its kind's kerb mass (`parked.tres` `masses_kg`): 0 is a car the taxi
	## cannot push.
	var mass_kg: float = 0.0
	## Knocked by the taxi (`Q180`): off its lane, moved by `_slide` and not
	## `_drive`, at its own plan velocity and spin (rad/s about up).
	var knocked: bool = false
	var slide: Vector3 = Vector3.ZERO
	var spin: float = 0.0
	## Seconds since the knock, for its driver's reaction; seconds stood still.
	var knocked_s: float = 0.0
	var still_s: float = 0.0
	## The edge its footprint stands on as a parked vehicle once it has settled,
	## or -1.
	var wreck_edge: int = -1
	## A slot of the routed fleet (`P3-78`): it spawns only on a route, as the
	## route's kind, from its slot in each routed kind's `MultiMesh` by kind index.
	var routed: bool = false
	## The route it keeps to and the index of the stop it is bound for or stands
	## at; null once it has left its route, when it wanders.
	var route: BusRoutes.Route = null
	var stop_index: int = -1
	## The search toward that stop; null once it has none left, or when it was
	## placed standing at one.
	var goal: RoadRouter.GoalTree = null
	## Seconds left standing at its stop.
	var dwell_left: float = 0.0
	## A kerbside stop for a passenger (`kerb_stop_kinds`, the user's call
	## 2026-11-06): where on this road its front pulls up, in travel metres, INF
	## for none, and seconds left standing there.
	var kerb_m: float = INF
	var kerb_left: float = 0.0


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
	## A knocked car standing here (`Q180`): it stands while that car is knocked,
	## and `_unwreck` takes it off on a push, a recovery or a retire.
	var wreck: Car = null

	func standing() -> bool:
		if wreck != null:
			return wreck.live and wreck.knocked
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
## Cars the taxi knocked, and knocked cars that drove on again (`Q180`).
var knocks: int = 0
var recovered: int = 0
## The fare loop whose awards the horns answer, found by its group: none under
## `--fares=off`.
var fares: FareSystem = null

## Ticks run, so a car's turn path is read once a tick.
var _tick: int = 0
## The horns (`Q178`, `P3-79`): their voices, patterns and counters.
var horn := TrafficHorns.new(self)
## Where a kerb-stopping car pulls up for a passenger (`P3-78`).
var kerbside := TrafficKerbside.new(self)
## The routed fleet's placement and stops (`P3-78`).
var route_fleet := TrafficRouted.new(self)
## Seconds run, for a car's temper.
var _clock_s: float = 0.0
var _rng := RandomNumberGenerator.new()
## The cars by their body's instance id, for `take_push`.
var _by_body: Dictionary[int, Car] = {}
## What a knocked car's tyres hold across them, in m/s²: the road tyre's `mu`
## times the world's gravity, the pace's (`Q156`) — the taxi's own grip.
var _grip_mps2: float = 0.0
## What a knocked car's sweep met, reused: `test_move` fills it every slide tick.
var _met := KinematicCollision3D.new()
var _kinds: PackedStringArray = []
var _meshes: Array[Mesh] = []
var _extents: Array[AABB] = []
var _batches: Array[MultiMesh] = []
## Every live car's headlamp beam at night (`TrafficBeams`); null where its
## material did not load, and the cars then run with their lenses alone.
var beams: TrafficBeams = null
## The cars each batch draws, by kind index: a batch's first
## `visible_instance_count` instances are these, in this order (`P3-85`). A
## batch has room for every car that may wear its kind — a routed car's in each
## route kind, a wandering car's in every kind the hours draw and every taxi
## licence (`Q183`, `Q186`) — because `instance_count` clears a buffer and
## cannot grow after `setup`; only the cars shown are drawn, where a hidden one
## was an instance of no size that still cost its triangles.
var _shown: Array[Array] = []
## The fleet's kinds by the hour and its taxis' licences (`Q183`, `Q186`).
var fleet_mix := TrafficFleetMix.new()
var _admitted: PackedInt32Array = []
## The kind index of each licence mesh a taxi may wear, the profile's own first.
var _licence_kinds: Dictionary[String, int] = {}
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
## Each route kind's index in `_kinds`.
var _routed_kinds: Dictionary[String, int] = {}
var _parked_profile: ParkedProfile = null
## The lighting rig the hour is read off, found once it is in the tree.
var _rig: LightingRig = null
## What the camera sees this tick (`Q214`): its frustum, eye and `far`. With no
## camera — a verify tool's run — nothing is in view, so a car is placed and
## retired by the ring alone, as the seeded drives were measured.
var _viewing: bool = false
var _planes: Array[Plane] = []
var _eye: Vector3 = Vector3.ZERO
var _far_m: float = 0.0
var _sight := PhysicsRayQueryParameters3D.new()


func _ready() -> void:
	# Set up before it entered the tree: the verify tool's own run.
	if profile != null:
		return
	if Cmdline.off(ARG):
		_stand_down()
		return
	if not setup(RoadGraph.shared(), load(TrafficProfile.PATH) as TrafficProfile, 1):
		_stand_down()


## Leave the tree without one more tick. `queue_free` waits for the frame's end,
## and a long first frame — a phone's — runs physics before it: a tick on a
## system never set up read a null graph and crashed the iOS build under
## `--traffic=off` (`P2-6`). The desktop's first frame ticked none, so it hid.
func _stand_down() -> void:
	set_physics_process(false)
	queue_free()


## Everything a run needs, without the scene: false, with a pushed reason,
## where the city or the table cannot carry traffic. `seed` fixes every roll.
func setup(with_graph: RoadGraph, table: TrafficProfile, seed: int) -> bool:
	if with_graph == null or with_graph.is_empty() or table == null or not usable(table):
		return false
	graph = with_graph
	profile = table
	fleet_mix.profile = table
	_rng.seed = seed
	route_fleet.seed_from(seed)
	horn.seed_from(seed)
	kerbside.seed_from(seed)
	router = RoadRouterScript.new(graph, RoadRouterScript.Profile.legal())
	_admitted = PackedInt32Array()
	for edge: int in router.admitted_edge_ids():
		if not graph.is_stub(edge):
			_admitted.append(edge)
	if _admitted.is_empty():
		push_warning("TrafficSystem: no edge admits traffic; none will run")
		return false
	if fleet_mix.licence_mixes.is_empty():
		for region: String in graph.resident_regions():
			var manifest: CityManifest = CityManifest.shared(region)
			if manifest != null and not manifest.taxi_licences.is_empty():
				fleet_mix.licence_mixes[region] = manifest.taxi_licences
	if bus_routes == null:
		bus_routes = BusRoutes.resident(graph)
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
	_parked_profile = load(ParkedProfile.PATH) as ParkedProfile
	fleet_mix.read_hour(_hour_now())
	var licences: Array[int] = _licence_kinds.values()
	for index: int in profile.cars:
		var car := Car.new()
		car.kind = _pick_kind()
		car.taxi = _kinds[car.kind] == profile.taxi_kind
		for kind: int in _kinds.size():
			if fleet_mix.wanders(kind) or licences.has(kind):
				_batches[kind].instance_count += 1
		cars.append(car)
	if not _routed_kinds.is_empty():
		for _index: int in profile.buses:
			var car := Car.new()
			car.routed = true
			for kind: int in _routed_kinds.values():
				_batches[kind].instance_count += 1
			car.kind = _routed_kinds.values()[0]
			cars.append(car)
	for kind: int in _kinds.size():
		var drawn := MultiMeshInstance3D.new()
		drawn.name = _kinds[kind]
		drawn.multimesh = _batches[kind]
		_batches[kind].visible_instance_count = 0
		add_child(drawn)
	var widest_half_m: float = 0.0
	for extent: AABB in _extents:
		widest_half_m = maxf(widest_half_m, extent.size.x * 0.5)
	beams = TrafficBeams.create(cars.size(), widest_half_m)
	if beams != null:
		add_child(beams)
	var parked: ParkedProfile = _parked_profile
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
		if not car.routed:
			car.livery = ParkedRoster.livery(
				_rng.randi() & 0xFFFF, _palette(profile.wander_liveries, _kinds[car.kind])
			)
		car.obstacle = {
			"transform": Transform3D.IDENTITY,
			"extent": extent,
			"id": hash(Vector2i(int(get_instance_id() & 0x7FFFFFFF), car.id)),
			"velocity": Vector3.ZERO,
		}
		car.mass_kg = parked.masses_kg.get(_kinds[car.kind], 0.0) if parked != null else 0.0
		if car.mass_kg > 0.0:
			Pushable.mark(car.body, self)
			_by_body[car.body.get_instance_id()] = car
		_hide(car)
	_grip_mps2 = grip_mps2()
	var horn_kinds: Array[String] = []
	horn_kinds.assign(profile.kinds.keys())
	horn_kinds.append_array(_routed_kinds.keys())
	horn.load_voices(horn_kinds)
	add_to_group(GROUP)
	return true


## False, with a pushed reason, where a value is zero or negative.
static func usable(table: TrafficProfile) -> bool:
	var required: Dictionary[String, float] = {
		"cars": float(table.cars),
		"spawn_min_m": table.spawn_min_m,
		"spawn_max_m": table.spawn_max_m - table.spawn_min_m,
		"retire_m": table.retire_m - table.spawn_max_m,
		"spawn_clear_m": table.spawn_clear_m,
		"spawn_seen_min_m": table.spawn_seen_min_m - table.spawn_min_m,
		"retire_unseen_s": table.retire_unseen_s,
		"retire_far_margin_m": table.retire_far_margin_m,
		"fade_in_s": table.fade_in_s,
		"fade_out_s": table.fade_out_s,
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
		"give_way_look_m": table.give_way_look_m,
		"horn_voices": float(table.horn_voices),
		"horn_range_m": table.horn_range_m,
		"horn_repeat_s": table.horn_repeat_s,
		"horn_after_s": table.horn_after_s,
		"horn_cut_mps": table.horn_cut_mps,
		"horn_pitch_spread": table.horn_pitch_spread,
		"horn_temper_step": table.horn_temper_step,
		"horn_temper_max": table.horn_temper_max,
		"horn_temper_s": table.horn_temper_s,
		"kinds": float(table.kinds.size()),
		"fleet_by_hour": float(table.fleet_by_hour.size()),
		"taxi_for_hire": table.taxi_for_hire,
		"react_s": table.react_s,
		"recover_after_s": table.recover_after_s,
		"recover_radius_m": table.recover_radius_m,
		"recover_heading_deg": table.recover_heading_deg,
		"recover_ahead_m": table.recover_ahead_m,
		"recover_clear_m": table.recover_clear_m,
		"buses": float(table.buses),
		"dwell_s": table.dwell_s,
		"dwell_reach_m": table.dwell_reach_m,
		"pull_out_m": table.pull_out_m,
		"kerb_stop_every_m": table.kerb_stop_every_m,
		"kerb_dwell_s": table.kerb_dwell_s,
		"kerb_unlawful_share": table.kerb_unlawful_share,
	}
	var hourly: Array[PackedFloat32Array] = [table.fleet_by_hour]
	hourly.append_array(table.kinds.values())
	for table_row: PackedFloat32Array in hourly:
		if table_row.size() != TrafficProfile.HOURS:
			push_error(
				(
					"TrafficSystem: %s has an hourly table of %d entries, not %d"
					% [table.resource_path, table_row.size(), TrafficProfile.HOURS]
				)
			)
			return false
	for hour: int in TrafficProfile.HOURS:
		var drawn: float = 0.0
		for by_hour: PackedFloat32Array in table.kinds.values():
			drawn += by_hour[hour]
		if drawn <= 0.0:
			push_error("TrafficSystem: %s draws no kind at %02d:00" % [table.resource_path, hour])
			return false
	for reason: String in TrafficHorns.HORN_REASONS:
		if not (
			table.horn_count.has(reason)
			and table.horn_press_s.has(reason)
			and table.horn_gap_s.has(reason)
		):
			push_error(
				"TrafficSystem: %s has no horn pattern for %s" % [table.resource_path, reason]
			)
			return false
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
		var by_hour: PackedFloat32Array = profile.kinds[kind]
		if not found.has(kind) or Array(by_hour).max() <= 0.0:
			push_warning("TrafficSystem: no mesh %s in %s; skipped" % [kind, LIBRARY_PATH])
			continue
		_add_kind(kind, found[kind], by_hour)
	if _kinds.is_empty():
		push_error("TrafficSystem: none of %s is in %s" % [profile.kinds.keys(), LIBRARY_PATH])
		return false
	var taxi: int = _kinds.find(profile.taxi_kind)
	if taxi >= 0:
		_licence_kinds[profile.taxi_kind] = taxi
		for region: String in fleet_mix.licence_mixes:
			for mesh: String in fleet_mix.licence_mixes[region]:
				if _licence_kinds.has(mesh):
					continue
				if not found.has(mesh):
					push_warning("TrafficSystem: no licence mesh %s in %s" % [mesh, LIBRARY_PATH])
					continue
				# Never drawn by `_pick_kind`: only a taxi's spawn region wears it.
				_licence_kinds[mesh] = _add_kind(mesh, found[mesh], PackedFloat32Array())
	if bus_routes != null:
		for route: BusRoutes.Route in bus_routes.routes:
			if _routed_kinds.has(route.kind):
				continue
			if not found.has(route.kind):
				push_warning("TrafficSystem: no route mesh %s in %s" % [route.kind, LIBRARY_PATH])
				continue
			var known: int = _kinds.find(route.kind)
			# Weight 0: `_pick_kind` never draws a kind only a route runs.
			_routed_kinds[route.kind] = (
				known
				if known >= 0
				else _add_kind(route.kind, found[route.kind], PackedFloat32Array())
			)
	VehicleLampsProfile.wire_blink(_meshes)
	for extent: AABB in _extents:
		_reach_m = maxf(_reach_m, extent.size.z * 0.5)
	# `instance_count` allocates the buffer and clears it, so it is grown car by
	# car in `setup` before any transform or livery is written.
	return true


## One drawn kind and its batch, at its weight by clock hour — none for a kind
## only a licence or a route wears; its index.
func _add_kind(kind: String, mesh: Mesh, by_hour: PackedFloat32Array) -> int:
	_kinds.append(kind)
	_meshes.append(mesh)
	_extents.append(mesh.get_aabb())
	fleet_mix.add_kind(by_hour)
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.use_custom_data = true
	# Lamps from `INSTANCE_CUSTOM.a`, not the instance uniforms (`VehicleBodyBatch`).
	multi.mesh = VehicleBodyBatch.batched(mesh)
	_batches.append(multi)
	_shown.append([])
	return _kinds.size() - 1


## Light the roof sign or not for this spawn, show the licence `car`'s spawn
## region draws, and hide the one it wore.
func _wear_licence(car: Car) -> void:
	if not car.taxi:
		return
	car.for_hire = fleet_mix.for_hire_of(car.id, car.lives)
	# The sign may have changed with the lamps not: write the datum afresh.
	car.written = -1
	if _licence_kinds.size() < 2:
		return
	var mesh: String = fleet_mix.licence_of(graph.region_of(car.edge), car.id, car.lives)
	var kind: int = _licence_kinds.get(mesh, _licence_kinds[profile.taxi_kind])
	if kind == car.kind:
		return
	_change_kind(car, kind)


## Which licence `car` wears, by mesh name.
func kind_name(car: Car) -> String:
	return _kinds[car.kind]


## The kind a rule reads `car` as: every taxi is `taxi_kind` whatever licence's
## mesh it wears (`_wear_licence` swaps `car.kind` to `taxi_nt` or
## `taxi_lantau`), so a green taxi stops at the kerb and honks as a red one does.
func rules_kind(car: Car) -> String:
	return profile.taxi_kind if car.taxi else _kinds[car.kind]


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
	for car: Car in cars:
		car.wreck_edge = -1  # its footprint went with the rest; it stands again on settling
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
	parked.lane_m = RoadGraph.plan_distance(
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


## Show `car` as `kind`, from that kind's slot, at that kind's size and mass, in
## `livery`.
func _wear_kind(car: Car, kind: int, livery: Color) -> void:
	if kind != car.kind:
		_change_kind(car, kind)
	var extent: AABB = _extents[kind]
	car.half_length = extent.size.z * 0.5
	car.half_width = extent.size.x * 0.5
	(car.shape.shape as BoxShape3D).size = extent.size
	car.shape.position = extent.get_center()
	car.obstacle["extent"] = extent
	if _parked_profile != null:
		car.mass_kg = _parked_profile.masses_kg.get(_kinds[kind], car.mass_kg)
	car.taxi = not car.routed and _kinds[kind] == profile.taxi_kind
	car.livery = livery
	car.written = -1


## The colours `kind` wears: `table`'s own (a wandering or a route livery), else the
## parked roster's palette for it, else none.
func _palette(table: Dictionary[String, PackedColorArray], kind: String) -> PackedColorArray:
	if table.has(kind):
		return table[kind]
	if _parked_profile != null:
		return _parked_profile.liveries.get(kind, PackedColorArray())
	return PackedColorArray()


## Wandering cars alive.
func live_wandering() -> int:
	var live: int = 0
	for car: Car in cars:
		if car.live and not car.routed:
			live += 1
	return live


## The game hour: `hour_override`, else the rig's on the parked roster's clock.
func _hour_now() -> int:
	if not is_nan(hour_override):
		return posmod(int(hour_override), BusRoutes.HOURS)
	var time_of_day: float = 0.0
	if not is_instance_valid(_rig) and is_inside_tree():
		_rig = get_tree().get_first_node_in_group(LightingRig.GROUP) as LightingRig
	if is_instance_valid(_rig):
		time_of_day = _rig.time_of_day
	if _parked_profile == null:
		return 0
	var hour: float = ParkedRoster.hour_of(
		time_of_day, _parked_profile.clock_start_h, _parked_profile.clock_end_h
	)
	return posmod(int(hour), BusRoutes.HOURS)


## Standing at a stop or the kerb for a passenger: brake lamps and the left indicator.
static func standing(car: Car) -> bool:
	return car.dwell_left > 0.0 or car.kerb_left > 0.0


## Pulling away from a stop: the offside indicator until it is `pull_out_m` on.
func _pull_out(car: Car) -> void:
	car.held_side = -1
	car.held_until_m = car.s + profile.pull_out_m


func _pick_kind() -> int:
	return _rng.rand_weighted(fleet_mix.weights)


func _physics_process(delta: float) -> void:
	step(delta)


## One tick: retire what left the ring out of view (`Q214`), drive every car,
## spawn into the ring.
func step(delta: float) -> void:
	_tick += 1
	_clock_s += delta
	horn.step(delta)
	if trams == null and is_inside_tree():
		trams = get_tree().get_first_node_in_group(TramSystem.GROUP) as TramSystem
	if not is_instance_valid(fares) and is_inside_tree():
		_listen(get_tree().get_first_node_in_group(FareSystem.GROUP) as FareSystem)
	if not _parked_read and is_inside_tree():
		_queue_parked(get_tree().get_nodes_in_group(ParkedLayer.GROUP))
	_read_parked_some(PARKED_READS_PER_TICK)
	var here: Vector3 = vehicle.global_position if is_instance_valid(vehicle) else centre
	_read_view()
	for car: Car in cars:
		if not car.live:
			continue
		if _step_view(car, here, delta):
			_retire(car)
			continue
		if car.knocked:
			_slide(car, delta)
		else:
			_drive(car, delta)
	# Once a tick for both readers: the rig is a tree search away.
	var hour: int = _hour_now()
	fleet_mix.read_hour(hour)
	var wandering: int = live_wandering()
	for _try: int in SPAWN_TRIES:
		if wandering >= fleet_mix.fleet_now():
			break
		var idle: Car = _idle_car(false)
		if idle == null:
			break
		_try_spawn(idle, here)
		if idle.live:
			wandering += 1
	route_fleet.refresh_spawn_pool(hour)
	for _try: int in SPAWN_TRIES:
		var idle: Car = _idle_car(true)
		if idle == null:
			break
		route_fleet.try_spawn(idle, here)
	if beams != null:
		beams.begin()
	for car: Car in cars:
		if car.live:
			car.body.global_transform = car.pose
			if car.slot < 0:
				_take_slot(car)
			_batches[car.kind].set_instance_transform(car.slot, car.pose)
			# Standing for a passenger, it shows its brake lamps from the first tick:
			# one placed mid-dwell has not braked yet.
			_write_lamps(
				car,
				lamp_bits(true, car.braking or standing(car), _winking(car)) | fade_bits(car.fade)
			)
			if beams != null:
				beams.add(
					car.pose.translated_local(TrafficBeams.nose_of(_extents[car.kind])),
					car.half_width
				)
	if beams != null:
		beams.end()


## The camera this tick, or none (`Q214`).
func _read_view() -> void:
	var camera: Camera3D = get_viewport().get_camera_3d() if is_inside_tree() else null
	_viewing = camera != null
	if _viewing:
		_planes = camera.get_frustum()
		_eye = camera.global_position
		_far_m = camera.far


## Whether a body `radius_m` round `foot` can be seen (`Q214`): in the camera's
## frustum, its roof in sight past everything the ETL ships — a building, the
## road over a crest or a deck. A car or a parked vehicle between hides nothing:
## either may be gone a moment later, the car driving on, the parked one at its
## hour. Never with no camera.
func seen(foot: Vector3, radius_m: float) -> bool:
	var roof: Vector3 = foot + Vector3.UP * SIGHT_HEIGHT_M
	return _in_frustum(roof, radius_m) and not _behind_city(roof)


## Whether a sphere `radius_m` round `point` reaches into the camera's frustum.
## False with no camera.
func _in_frustum(point: Vector3, radius_m: float) -> bool:
	if not _viewing:
		return false
	# Godot's frustum planes face out: over any one by more than the radius is out.
	for plane: Plane in _planes:
		if plane.distance_to(point) > radius_m:
			return false
	return true


## Whether the sight line from the camera to `target` meets the city first.
func _behind_city(target: Vector3) -> bool:
	if not is_inside_tree():
		return false
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var passed: Array[RID] = []
	_sight.from = _eye
	_sight.to = target
	for _hit: int in SIGHT_HITS:
		_sight.exclude = passed
		var hit: Dictionary = space.intersect_ray(_sight)
		if hit.is_empty():
			return false
		var body := hit["collider"] as Node
		if body != null and String(body.name).ends_with(CITY_COLLIDER_SUFFIX):
			return true
		passed.append(hit["rid"])
	return false


## How whole a car placed at `at` starts (`Q214`): 1 out of view, 0 in view
## past `spawn_seen_min_m` from the camera, where it fades in; -1 in view nearer,
## where it is not placed. Past the bar no ray is cast: a car fading in behind a
## building fades in unseen.
func placed_fade(at: Vector3) -> float:
	var roof: Vector3 = at + Vector3.UP * SIGHT_HEIGHT_M
	if not _in_frustum(roof, _reach_m):
		return 1.0
	if at.distance_to(_eye) >= profile.spawn_seen_min_m:
		return 0.0
	return 1.0 if _behind_city(roof) else -1.0


## Step `car`'s fade, and say whether it is to be retired this tick (`Q214`).
## Inside `retire_m` it stays. Past it, out of view, it goes after
## `retire_unseen_s`; in view it stays — a car the taxi chases is not taken from
## in front of it — until it is within `retire_far_margin_m` of the camera's
## `far`, where it fades out and then goes. With no camera it goes at
## `retire_m` at once, as the seeded drives were measured.
func _step_view(car: Car, here: Vector3, delta: float) -> bool:
	if car.leaving:
		car.fade -= delta / profile.fade_out_s
		return car.fade <= 0.0
	if car.fade < 1.0:
		car.fade = minf(car.fade + delta / profile.fade_in_s, 1.0)
	if RoadGraph.plan_distance(car.pose.origin, here) <= profile.retire_m:
		car.unseen_s = 0.0
		return false
	if not _viewing:
		return true
	# Near the far plane in the frustum it fades out, hidden or not: no ray.
	var near_far: bool = car.pose.origin.distance_to(_eye) > _far_m - profile.retire_far_margin_m
	if near_far and _in_frustum(car.pose.origin + Vector3.UP * SIGHT_HEIGHT_M, car.half_length):
		car.leaving = true
		return false
	if not seen(car.pose.origin, car.half_length):
		car.unseen_s += delta
		return car.unseen_s >= profile.retire_unseen_s
	car.unseen_s = 0.0
	return false


## The fade's bits for a car `fade` whole (`Q214`): 0 whole.
static func fade_bits(fade: float) -> int:
	return FADE_BIT * roundi((1.0 - clampf(fade, 0.0, 1.0)) * FADE_STEPS)


func _idle_car(routed: bool) -> Car:
	for car: Car in cars:
		if not car.live and car.routed == routed:
			return car
	return null


## Whether `at` stands in the spawn ring round `here` and `spawn_clear_m` clear
## of every live car.
func _in_ring_and_clear(at: Vector3, here: Vector3) -> bool:
	var away: float = RoadGraph.plan_distance(at, here)
	if away < profile.spawn_min_m or away > profile.spawn_max_m:
		return false
	for other: Car in cars:
		if other.live and RoadGraph.plan_distance(other.pose.origin, at) < profile.spawn_clear_m:
			return false
	return true


## Whether a vehicle `half_length` long placed on `edge` its `along` way at `s`,
## in `lane`, leaves every live car coming up behind it in that lane — on the
## edge, or turning onto it — room to stop at `brake_mps2` and `gap_m` short.
## Without it a bus placed mid-dwell 12 m ahead of a car at cruise was run into
## at the hardest braking (`Q198`, seed 4 at 40 cars): `_in_ring_and_clear` is a
## point's distance, blind to the placed length and the speed behind.
func _room_behind(edge: int, along: bool, s: float, half_length: float, lane: float) -> bool:
	for other: Car in cars:
		if not other.live:
			continue
		var behind: float = INF
		if other.edge == edge and other.along == along and other.s <= s:
			if same_lane(other.lane, lane):
				behind = s - other.s
		elif other.next_edge == edge and other.next_along == along:
			if same_lane(other.next_lane, lane):
				behind = other.length_m - other.s + s
		if behind == INF:
			continue
		var stopping: float = other.speed * other.speed / (2.0 * profile.brake_mps2)
		if behind - half_length - other.half_length < stopping + profile.gap_m:
			return false
	return true


## Put idle `car` on `edge` its `along` way at `s`, in `lane`, moving at
## `cruise_share` of its cruise. A routed car's route is set before, so that
## `_enter` plans toward its stop.
func _place(car: Car, edge: int, along: bool, s: float, lane: float, cruise_share: float) -> void:
	car.live = true
	car.lives += 1
	car.edge = edge
	car.along = along
	car.s = s
	car.turning = false
	car.joined_until_m = 0.0
	car.crossed.clear()
	car.lane = lane
	car.held_side = 0
	car.fade = 1.0
	car.leaving = false
	car.unseen_s = 0.0
	_enter(car)
	car.speed = car.cruise_mps * cruise_share
	car.pose = _pose_on_edge(car)
	car.shape.disabled = false
	spawned += 1


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
	if not _in_ring_and_clear(at, here):
		return
	# Never where a red ahead could not be stopped for from the spawn speed.
	var stop: float = _stop_along_m(edge, along, length_m)
	var cruise: float = _cruise_of(edge)
	if stop >= 0.0 and stop - s < (cruise * 0.5) ** 2 / profile.brake_mps2 + profile.look_m * 0.25:
		return
	var lane: float = float(_rng.randi_range(0, graph.lanes_each_way(edge) - 1))
	if car.lives > 0:
		_redraw(car, car.lives + 1)
	var half_length: float = car.half_length
	if not _room_behind(edge, along, s, half_length, lane):
		return
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
	# Last, after every cheap refusal: it may cast a ray.
	var fade: float = placed_fade(at)
	if fade < 0.0:
		return
	_place(car, edge, along, s, lane, 0.5)
	car.fade = fade
	_wear_licence(car)


## Draw idle `car` afresh for its `lives`th spawn (`Q186`; `car.lives` is not yet
## counted up) and wear it, before the spawn's checks read its size. Its first
## life keeps the kind `setup` drew; a draw of the kind it wears changes nothing,
## so a spawn that fails its checks and is tried again keeps what it was drawn.
func _redraw(car: Car, lives: int) -> void:
	var kind: int = fleet_mix.kind_for(car.id, lives)
	if kind == car.kind:
		return
	# Off its id and lives, as the kind is: never `_rng`.
	var livery_seed: int = hash(Vector2i(car.id, lives)) & 0xFFFF
	var palette: PackedColorArray = _palette(profile.wander_liveries, _kinds[kind])
	_wear_kind(car, kind, ParkedRoster.livery(livery_seed, palette))


## Fill a car's per-edge state on entering `car.edge`: its length, cruise, the
## next move and where the straight run ends.
func _enter(car: Car) -> void:
	car.length_m = graph.plan_length_of(car.edge)
	car.cruise_mps = _cruise_of(car.edge)
	car.replanned = false
	car.passing = false
	car.shift = 0
	car.over_centre = false
	_plan_move(car)
	kerbside.pick(car)


func _cruise_of(edge: int) -> float:
	return graph.speed_limit_of(edge) / 3.6 * profile.cruise_of_limit


## Pick the car's next move, through the junction's inside roads, and where and
## in which lane it leaves for it — another where parked vehicles block every
## lane of the road it would join at the mouth, up to `REPLAN_TRIES`.
func _plan_move(car: Car) -> void:
	for _try: int in REPLAN_TRIES:
		_plan_one_move(car)
		# A routed vehicle's move is its search's: another try picks the same one.
		if car.next_edge < 0 or car.join_clear or car.route != null:
			return


func _plan_one_move(car: Car) -> void:
	car.via.clear()
	car.join_clear = true
	car.turn_side = 0
	car.lane_out = car.lane
	var move: Vector2i = _pick_move(car, car.edge, car.along)
	# Through the junction's inside roads to the road out, a bounded walk.
	while move.x >= 0 and graph.is_stub(move.x) and car.via.size() < ADVANCE_STEPS:
		car.via.append(move)
		move = _pick_move(car, move.x, move.y == 1)
	if move.x < 0:
		car.next_edge = -1
		car.leave_m = car.length_m
		if car.route != null:
			# Its stop is on this road: in to the kerb's lane for it.
			car.lane_out = 0.0
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


## One of the legal moves off a way at random, or `(-1, 0)` at a dead end. A
## routed vehicle takes its goal's move instead, and `(-1, 0)` on the way its stop
## stands on or while it stands at one; off its route it wanders from here.
func _pick_move(car: Car, edge: int, along: bool) -> Vector2i:
	if car.route != null:
		if car.goal == null:
			return Vector2i(-1, 0)
		var toward: Vector2i = router.next_toward(car.goal, edge, along)
		if toward.x >= 0 or TrafficRouted.is_goal_way(car, edge, along):
			return toward
		stops_unreachable += 1
		TrafficRouted.leave_route(car)
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
		if other == car or not other.live or other.knocked:
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
		if other == car or not other.live or other.knocked:
			continue
		# Coming out of its turn beside this one: it stands at its join in the lane it
		# joins, and a change across it ended up inside it (seed 4).
		if other.turning:
			if (
				other.next_edge == car.edge
				and other.next_along == car.along
				and (
					absf(other.join_m - car.s) < car.half_length + other.half_length + profile.gap_m
				)
				and absf(other.next_lane - toward) < 1.0
			):
				return true
			continue
		if (
			other.edge != car.edge
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
	var for_light: bool = false
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
		for_light = true
		var limit: float = stopping_speed(to_stop, profile.brake_mps2)
		if limit < target:
			target = limit
			car.held = Held.LIGHT
	if car.route != null:
		var at_stop: float = route_fleet.stop_limit(car, delta)
		if at_stop < target:
			target = at_stop
			car.held = Held.DWELL
	if car.kerb_m < INF or car.kerb_left > 0.0:
		var at_kerb: float = kerbside.limit(car, delta)
		if at_kerb < target:
			target = at_kerb
			car.held = Held.DWELL
	var give_way: float = _give_way_gap(car)
	if give_way < INF:
		var limit: float = stopping_speed(give_way - STOP_SHORT_M, profile.brake_mps2)
		if limit < target:
			target = limit
			car.held = Held.GIVE_WAY
	var gap: float = _gap_ahead(car)
	if gap < INF:
		var limit: float = stopping_speed(gap - profile.gap_m, profile.brake_mps2)
		if limit < target:
			target = limit
			car.held = Held.CAR
	var taxi_gap: float = _taxi_gap(car)
	if taxi_gap < INF:
		var limit: float = stopping_speed(taxi_gap - profile.gap_m, profile.brake_mps2)
		if limit < target:
			target = limit
			car.held = Held.TAXI
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
	horn.mind(car, target, for_light, delta)
	car.braking = target < car.speed or car.speed < STOPPED_MPS
	if car.speed < target:
		car.speed = minf(target, car.speed + profile.accel_mps2 * delta)
	else:
		car.speed = maxf(target, car.speed - profile.brake_max_mps2 * delta)
	_advance(car, car.speed * delta)


## Hear `loop`'s awards, paid and practised alike: an empty cab is cut up as rudely.
func _listen(loop: FareSystem) -> void:
	if loop == null:
		return
	fares = loop
	fares.skilled.connect(_on_skilled)
	fares.practised.connect(react_to)


func _on_skilled(_fare: Fare, award: Fare.Award) -> void:
	react_to(award)


## The horns an award draws (`Q178`), whatever the car's own wait: each is one
## event, and the loop already spaces them (`crash_cool_s`, one award a pass).
## A close call: the car passed. A docked hit: every car with the taxi in its
## path, and the car struck. A near miss passes at a distance nobody honks at.
func react_to(award: Fare.Award) -> void:
	match award.skill:
		Fare.Skill.CLOSE_CALL:
			for car: Car in cars:
				if car.live and is_same(car.obstacle, award.passed):
					horn.sound(car, "close_call")
		Fare.Skill.BUMP, Fare.Skill.CRASH:
			for car: Car in cars:
				if car.live and (_struck(car) or _taxi_gap(car) < INF):
					horn.sound(car, "hit")


## Whether `car` is near enough the taxi to be what it hit.
func _struck(car: Car) -> bool:
	if not is_instance_valid(vehicle):
		return false
	var reach: float = car.half_length + _extents[0].size.z * 0.5 + STRUCK_SLACK_M
	return RoadGraph.plan_distance(car.pose.origin, vehicle.global_position) <= reach


## What a knocked car's tyres hold across them, in m/s²: `tyre.tres`' `mu` times
## the world's gravity at `pace.tres`' scale — the taxi's own road and tyre.
static func grip_mps2() -> float:
	var tyre := load(TyreProfile.PATH) as TyreProfile
	var pace := load(PaceProfile.PATH) as PaceProfile
	if tyre == null or pace == null:
		return 0.0
	return (
		tyre.mu * float(ProjectSettings.get_setting("physics/3d/default_gravity")) * pace.pace_scale
	)


## `Pushable`: how readily the car behind `body` gives along `normal` at `at`.
func push_inverse_mass(body: Object, normal: Vector3, at: Vector3) -> float:
	var car: Car = _by_body.get(body.get_instance_id())
	if car == null or not car.live:
		return 0.0
	return Pushable.box_inverse_mass(
		car.mass_kg, car.half_length, car.half_width, _centre_of(car), normal, at
	)


## `Pushable`: the taxi put `impulse` into the car behind `body` at `at`. It is
## knocked off its lane, if it was not already, and takes the impulse as its mass
## and its box answer it.
func take_push(body: Object, impulse: Vector3, at: Vector3) -> void:
	var car: Car = _by_body.get(body.get_instance_id())
	if car == null or not car.live:
		return
	# A wreck pushed again slides on, and is measured afresh where it settles.
	_unwreck(car)
	if not car.knocked:
		_knock(car)
	var push := Vector3(impulse.x, 0.0, impulse.z)
	var middle: Vector3 = _centre_of(car)
	car.slide += push / car.mass_kg
	car.spin += (
		Pushable.yaw_moment(Vector3(at.x - middle.x, 0.0, at.z - middle.z), push)
		/ Pushable.yaw_inertia(car.mass_kg, car.half_length, car.half_width)
	)
	car.knocked_s = 0.0
	car.still_s = 0.0


## Off its lane at the speed it was driving: from here `_slide` moves it.
func _knock(car: Car) -> void:
	car.knocked = true
	var forward: Vector3 = -car.pose.basis.z
	car.slide = Vector3(forward.x, 0.0, forward.z) * car.speed
	car.speed = 0.0
	car.spin = 0.0
	car.turning = false
	car.passing = false
	car.over_centre = false
	car.held = Held.NONE
	car.kerb_m = INF
	car.kerb_left = 0.0
	TrafficRouted.leave_route(car)
	knocks += 1


## The middle of `car`'s box in the world.
func _centre_of(car: Car) -> Vector3:
	return car.pose * _extents[car.kind].get_center()


## One tick of a knocked car: across its tyres it scrubs at `_grip_mps2`, along
## them it coasts for `react_s` and then brakes at `brake_max_mps2`, and its spin
## dies on the same grip over its box — a box on four tyres turning about its
## middle feels about `3 μ g L / (L² + W²)` of angular braking. It stops against
## what it meets. Settled, it stands as a parked vehicle for the others to pass,
## and after `recover_after_s` tries to drive on.
func _slide(car: Car, delta: float) -> void:
	car.knocked_s += delta
	car.braking = true
	var forward: Vector3 = -car.pose.basis.z
	forward = Vector3(forward.x, 0.0, forward.z).normalized()
	var side := Vector3(-forward.z, 0.0, forward.x)
	var along: float = car.slide.dot(forward)
	if car.knocked_s >= profile.react_s:
		along = move_toward(along, 0.0, profile.brake_max_mps2 * delta)
	var across: float = move_toward(car.slide.dot(side), 0.0, _grip_mps2 * delta)
	car.slide = forward * along + side * across
	var length: float = car.half_length * 2.0
	var width: float = car.half_width * 2.0
	var spin_brake: float = 3.0 * _grip_mps2 * length / (length * length + width * width)
	car.spin = move_toward(car.spin, 0.0, spin_brake * delta)
	var motion: Vector3 = car.slide * delta
	if motion.length_squared() > 0.0:
		var from: Transform3D = car.pose
		from.origin.y += SWEEP_LIFT_M
		if car.body.test_move(from, motion, _met):
			motion = _met.get_travel()
			motion.y = 0.0
			var normal: Vector3 = _met.get_normal()
			normal = Vector3(normal.x, 0.0, normal.z)
			if normal.length_squared() > 0.0:
				normal = normal.normalized()
				var into: float = car.slide.dot(normal)
				if into < 0.0:
					car.slide -= normal * into
	var turned: Basis = (Basis(Vector3.UP, car.spin * delta) * car.pose.basis).orthonormalized()
	car.pose = Transform3D(turned, car.pose.origin + motion)
	if car.slide.length() >= STOPPED_MPS or absf(car.spin) >= STILL_SPIN:
		car.still_s = 0.0
		return
	car.slide = Vector3.ZERO
	car.spin = 0.0
	# Once as it settles and once each time it tries to drive on, not every tick:
	# off any road it may drive it has no footprint to stand.
	if car.still_s == 0.0 and car.wreck_edge < 0:
		_stand_wreck(car)
	car.still_s += delta
	if car.still_s >= profile.recover_after_s:
		car.still_s = 0.0
		_try_recover(car)


## A settled knocked car's footprint on the road it stands by, read as a parked
## vehicle's (`_measure_parked`), so the others pass it as they pass one.
func _stand_wreck(car: Car) -> void:
	var hit: RoadGraph.Hit = graph.nearest_edge(
		car.pose.origin, Vector3.ZERO, profile.recover_radius_m
	)
	if hit.edge_id < 0 or graph.is_stub(hit.edge_id):
		return
	if not router.admits_way(hit.edge_id, true) and not router.admits_way(hit.edge_id, false):
		return
	car.obstacle["transform"] = car.pose
	var parked: Parked = _measure_parked(hit.edge_id, car.obstacle)
	parked.wreck = car
	parked.source = "knocked"
	if not _parked.has(hit.edge_id):
		_parked[hit.edge_id] = []
	_parked[hit.edge_id].append(parked)
	car.wreck_edge = hit.edge_id


## Take `car`'s footprint off the road it stood on.
func _unwreck(car: Car) -> void:
	if car.wreck_edge < 0:
		return
	var kept: Array = []
	for parked: Parked in _parked.get(car.wreck_edge, NO_PARKED):
		if parked.wreck != car:
			kept.append(parked)
	if _parked.has(car.wreck_edge):
		_parked[car.wreck_edge] = kept
	car.wreck_edge = -1


## Drive a settled knocked car on, if it can: back into the nearside lane of the
## road it stands by, `recover_ahead_m` down it, in one curve as a turn is driven
## — where that road is within `recover_radius_m`, one traffic drives, a way the
## car faces within `recover_heading_deg` of (it does not reverse), long enough to
## rejoin, with no car under way within `recover_clear_m` of the join or the
## curve's middle, and nothing standing in the curve. False where it stays put.
func _try_recover(car: Car) -> bool:
	var forward: Vector3 = -car.pose.basis.z
	forward = Vector3(forward.x, 0.0, forward.z).normalized()
	var hit: RoadGraph.Hit = graph.nearest_edge(car.pose.origin, forward, profile.recover_radius_m)
	if hit.edge_id < 0 or hit.distance > profile.recover_radius_m:
		return false
	var edge: int = hit.edge_id
	var along: bool = hit.along
	if not _admitted.has(edge) or not router.admits_way(edge, along):
		return false
	if forward.dot(hit.forward) < cos(deg_to_rad(profile.recover_heading_deg)):
		return false
	var length_m: float = graph.plan_length_of(edge)
	var here: float = _edge_m(hit.t * length_m, length_m, along)
	var join: float = here + profile.recover_ahead_m
	if join > length_m - car.half_length:
		return false
	var p0: Vector3 = car.pose.origin
	var p2: Vector3 = graph.lane_at(edge, _edge_m(join, length_m, along), along, 0.0)
	var out: Vector3 = _travel_dir(edge, join, length_m, along)
	var p1: Vector3 = TrafficTurns.turn_control(p0, forward, p2, out)
	var middle: Vector3 = TrafficTurns.curve_point(p0, p1, p2, 0.5)
	for other: Car in cars:
		# A car under way is looked for; one standing — queued behind the wreck for
		# it to move, which a look would wait on for ever — is in the sweep below
		# only if it stands in the way.
		if other == car or not other.live or other.knocked or other.speed < STOPPED_MPS:
			continue
		if (
			RoadGraph.plan_distance(other.pose.origin, p2) < profile.recover_clear_m
			or RoadGraph.plan_distance(other.pose.origin, middle) < profile.recover_clear_m
		):
			return false
	var from: Transform3D = car.pose
	from.origin.y += SWEEP_LIFT_M
	for piece: int in RECOVER_SAMPLES:
		var a: Vector3 = TrafficTurns.curve_point(p0, p1, p2, float(piece) / RECOVER_SAMPLES)
		var b: Vector3 = TrafficTurns.curve_point(p0, p1, p2, float(piece + 1) / RECOVER_SAMPLES)
		from.origin = Vector3(a.x, car.pose.origin.y + SWEEP_LIFT_M, a.z)
		if car.body.test_move(from, Vector3(b.x - a.x, 0.0, b.z - a.z)):
			return false
	_unwreck(car)
	car.knocked = false
	car.slide = Vector3.ZERO
	car.spin = 0.0
	car.edge = edge
	car.along = along
	car.length_m = length_m
	car.s = here
	car.lane = 0.0
	car.lane_out = 0.0
	car.next_edge = edge
	car.next_along = along
	car.next_lane = 0.0
	car.join_m = join
	car.via.clear()
	car.crossed.clear()
	car.held_side = 0
	car.joined_until_m = 0.0
	var aside: float = (p2 - p0).dot(RoadGraph.left_of(forward))
	car.turn_side = 0 if absf(aside) < RECOVER_STRAIGHT_M else (1 if aside > 0.0 else -1)
	car.p0 = p0
	car.p1 = p1
	car.p2 = p2
	car.turn_len = TrafficTurns.curve_length(p0, p1, p2)
	car.turn_u = 0.0
	car.turning = true
	car.speed = 0.0
	car.cruise_mps = _cruise_of(edge)
	recovered += 1
	return true


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
##   heading and its width of its line. The player is `_taxi_gap`'s.
func _gap_ahead(car: Car) -> float:
	var forward: Vector3 = -car.pose.basis.z
	var origin: Vector3 = car.pose.origin
	var best: float = INF
	var follow_cos: float = cos(deg_to_rad(profile.follow_heading_deg))
	for other: Car in cars:
		if other == car or not other.live:
			continue
		var apart: float = RoadGraph.plan_distance(origin, other.pose.origin)
		if apart > profile.look_m + other.half_length + car.half_length:
			continue
		if other.knocked:
			# Off its lane at any heading: in the way wherever it stands across the
			# car's path, as the taxi is.
			best = minf(
				best,
				_gap_to(
					origin, forward, car, other.pose.origin, other.half_length, other.half_width
				)
			)
			continue
		if _on_path(car, other) or _coming_over(car, other):
			best = minf(best, apart - car.half_length - other.half_length)
			continue
		if _merging(car, other):
			best = minf(best, to_give_way_m(car) + profile.gap_m)
			continue
		var heading: Vector3 = -other.pose.basis.z
		if forward.x * heading.x + forward.z * heading.z < follow_cos:
			continue
		var gap: float = _gap_to(
			origin, forward, car, other.pose.origin, other.half_length, other.half_width
		)
		best = minf(best, gap)
	if is_instance_valid(trams):
		for tram: TramSystem.Tram in trams.trams:
			if not tram.live:
				continue
			var heading: Vector3 = -tram.pose.basis.z
			if forward.x * heading.x + forward.z * heading.z < follow_cos:
				continue
			best = minf(
				best,
				_gap_to(origin, forward, car, tram.pose.origin, trams.half_length, trams.half_width)
			)
	return best


## Bumper to the taxi in `car`'s cone, whatever its heading, or INF. Apart from
## `_gap_ahead` only so that the horn knows who is in the way.
func _taxi_gap(car: Car) -> float:
	if not is_instance_valid(vehicle):
		return INF
	# The taxi measured as the library's first kind: a saloon either way.
	var player: AABB = _extents[0]
	return _gap_to(
		car.pose.origin,
		-car.pose.basis.z,
		car,
		vehicle.global_position,
		player.size.z * 0.5,
		player.size.x * 0.5
	)


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


## Travel metres from `car`'s front to the line it gives way at — where its
## turn begins — negative once its front is past it.
static func to_give_way_m(car: Car) -> float:
	return car.leave_m - car.s - car.half_length


## Whether `car` is in the junction as far as giving way goes: turning, its
## tail not yet out of the turn it finished (seeds 4 and 7: a car crossed the
## mouth a car had just joined by), or too near its line to stop for it even
## braking hard (the amber's own judgement).
func committed(car: Car) -> bool:
	return car.turning or car.s < car.joined_until_m or _past_stopping(car)


## Whether `car` is too near its next line to stop for it even braking hard. A
## car still clearing the last junction is not excused its next line by that:
## on a short link a 7 m minibus is clearing the one for nearly the whole road
## (Causeway Bay's back streets: an 8 m link, and it turned into a merge blind).
func _past_stopping(car: Car) -> bool:
	if car.next_edge < 0:
		return false
	return not must_stop(
		SignalController.Light.AMBER, to_give_way_m(car), car.speed, profile.brake_max_mps2
	)


## 0 for straight on, 1 a left turn, 2 a right — the turn across the oncoming
## flow in left-hand traffic.
static func turn_rank(side: int) -> int:
	return 0 if side == 0 else (1 if side > 0 else 2)


## Whether, of two cars each at their line with crossing turns, the first goes:
## straight on before a left turn before a right, then the earlier in the fleet.
## A strict order, so no two cars at their lines can each wait for the other.
static func goes_first(side: int, id: int, other_side: int, other_id: int) -> bool:
	var rank: int = turn_rank(side)
	var other_rank: int = turn_rank(other_side)
	return rank < other_rank or (rank == other_rank and id < other_id)


## Whether `car` must stop for its own light now: such a car is going nowhere,
## and a car crossing on green does not give way to it.
func _stopping_for_light(car: Car) -> bool:
	if car.turning:
		return false
	var stop: float = stop_travel_m(car)
	if stop < 0.0:
		return false
	return must_stop(
		signals.state_of(car.edge, car.along),
		stop - car.s - car.half_length,
		car.speed,
		profile.brake_max_mps2
	)


## Metres `car`'s front may run before it gives way at its line, or INF where
## nothing it must give way to crosses its turn (`Q173`, the user's drive
## 2026-11-04: cars drove through each other at junctions without lights). A
## car within `give_way_look_m` of its line, and still able to stop for it,
## waits for any car whose turn crosses its own that is:
##
## - **in the junction** (`committed`): turning, or past stopping for its line;
## - **or coming, and goes first** (`_coming_first`): running free toward its
##   own line within `give_way_look_m` — held by nothing, not stopping for a light;
## - **or, whatever crosses, the road it joins has no room past the join** (`_queued_past_join`):
##   it would stand in the junction behind the queue, across everyone else's
##   turn — the box junction's rule (the back streets, seed 7: a queue behind a
##   parked vehicle's pinch backed into junctions and held the cross traffic
##   for a minute).
##
## 🔴 **No two cars wait on each other.** A car in the junction never gives
## way, so a wait on one ends when it is through. A wait for room is on a car
## on the road ahead, which waits only down that road. A wait on a car still coming
## is on one held by nothing — not waiting — and among cars at their lines the
## waits run one way down `goes_first`'s strict order. Its own approach is the
## queue's (`_queues_with`, `_gap_ahead`).
func _give_way_gap(car: Car) -> float:
	if car.turning or car.next_edge < 0:
		return INF
	var to_line: float = to_give_way_m(car)
	if to_line > profile.give_way_look_m or _past_stopping(car):
		return INF
	if _queued_past_join(car) != null:
		return maxf(to_line, 0.0)
	var mine: PackedVector3Array = []
	# Two cars each up to `give_way_look_m` short of their lines, the lines a
	# junction's width (at most a `look_m`) apart.
	var near_m: float = profile.give_way_look_m * 2.0 + profile.look_m
	var min_sin: float = sin(deg_to_rad(profile.straight_deg))
	for other: Car in cars:
		if other == car or not other.live or other.knocked:
			continue
		if absf(car.pose.origin.y - other.pose.origin.y) > LEVEL_APART_M:
			continue
		if RoadGraph.plan_distance(car.pose.origin, other.pose.origin) > near_m:
			continue
		if _queues_with(car, other):
			continue
		if not committed(other) and not _coming_first(car, other):
			continue
		if mine.is_empty():
			mine = _turn_path(car)
		var touch_m: float = car.half_width + other.half_width
		if TrafficTurns.paths_cross(
			mine, _turn_path(other), touch_m + profile.side_clear_m, touch_m, min_sin
		):
			return maxf(to_line, 0.0)
	return INF


## Whether `other` is ahead of `car` in its own queue, which `_gap_ahead`
## keeps: on its approach in its lane — a car in the lane beside is passed or
## merged with, not queued behind (Causeway Bay's back streets: two cars side by
## side on a two-lane road went straight on together into a one-lane road and
## stood in each other behind its queue) — and not in the junction on a turn to
## another road (the back streets, seed 7: a car turned into one stopped in its
## turn).
func _queues_with(car: Car, other: Car) -> bool:
	if other.edge != car.edge or other.along != car.along:
		return false
	if not same_lane(other.lane, car.lane):
		return false
	if not committed(other):
		return true
	return other.next_edge == car.next_edge and other.next_along == car.next_along


## Whether `other`, not yet in the junction, is coming and goes first: running
## free toward its own line within `give_way_look_m` — held by nothing, not
## stopping for a light — and first in `goes_first`'s order. The light is read
## last: it is the one check that asks the controller.
func _coming_first(car: Car, other: Car) -> bool:
	return (
		other.held == Held.NONE
		and other.next_edge >= 0
		and goes_first(other.turn_side, other.id, car.turn_side, car.id)
		and to_give_way_m(other) <= profile.give_way_look_m
		and not _stopping_for_light(other)
	)


## The held car on the road `car`'s turn joins, its way and in the lane it
## joins, whose tail stands within the car's length and `gap_m` of the join —
## or held in its own turn into that lane — or null: a car that turned now
## would stop with its tail in the junction (Causeway Bay, seed 4: a car
## followed one stopped part way through its turn and stood in it for 15 s).
func _queued_past_join(car: Car) -> Car:
	var room: float = car.join_m + car.half_length * 2.0 + profile.gap_m
	for other: Car in cars:
		if other == car or not other.live or other.knocked or other.held == Held.NONE:
			continue
		# Where it stands or is turning into: the join's road and lane either way.
		var edge: int = other.next_edge if other.turning else other.edge
		var along: bool = other.next_along if other.turning else other.along
		var lane: float = other.next_lane if other.turning else other.lane
		if edge != car.next_edge or along != car.next_along or not same_lane(lane, car.next_lane):
			continue
		if other.turning or other.s - other.half_length < room:
			return other
	return null


## `car`'s turn through the junction in plan points, read once a tick, out to
## its length past the curve's end, where its nose is when its tail joins (a
## road's mouth can lie inside another turn's sweep, seeds 4 and 7): the curve it
## drives from half its length back, where its body still lies; the end of the
## one it finished while its tail is still in the junction; or for a car not
## yet turning the curve it will drive from its turn's lane. A car still
## clearing the last junction within `give_way_look_m` of its next line carries
## the next turn too (Wan Chai, seed 7: a minibus on a short link pulled off on
## green with its tail in the last junction, read as that turn alone, and
## turned across a car turning left from the other side).
func _turn_path(car: Car) -> PackedVector3Array:
	if car.path_tick == _tick:
		return car.path
	car.path_tick = _tick
	var from_u: float = 0.0
	if car.turning and car.turn_len > 0.0:
		from_u = maxf(car.turn_u - car.half_length, 0.0) / car.turn_len
	elif car.s < car.joined_until_m and car.turn_len > 0.0:
		# Its tail's way back along the curve, from where it joined.
		var joined_m: float = car.joined_until_m - car.half_length * 2.0
		var behind: float = car.half_length - (car.s - joined_m)
		from_u = clampf(1.0 - behind / car.turn_len, 0.0, 1.0)
	var behind_it: bool = car.turning or car.s < car.joined_until_m
	var ahead: bool = (
		not car.turning
		and (not behind_it or car.next_edge >= 0 and to_give_way_m(car) <= profile.give_way_look_m)
	)
	car.path.resize((TrafficTurns.CURVE_SAMPLES + 2) * (int(behind_it) + int(ahead)))
	var at: int = 0
	if behind_it:
		at = _write_curve(car.path, at, [car.p0, car.p1, car.p2], from_u, car.half_length)
	if ahead:
		_write_curve(car.path, at, _turn_points(car, car.lane_out), 0.0, car.half_length)
	return car.path


## The curve through `points` from `from_u` into `path` from `at`, and a point a
## car's length past its end along the way out; where the next curve starts.
static func _write_curve(
	path: PackedVector3Array, at: int, points: PackedVector3Array, from_u: float, half_length: float
) -> int:
	for index: int in TrafficTurns.CURVE_SAMPLES + 1:
		path[at + index] = TrafficTurns.curve_point(
			points[0],
			points[1],
			points[2],
			lerpf(from_u, 1.0, float(index) / TrafficTurns.CURVE_SAMPLES)
		)
	var last: Vector3 = path[at + TrafficTurns.CURVE_SAMPLES - 1]
	var out := Vector3(points[2].x - last.x, 0.0, points[2].z - last.z)
	path[at + TrafficTurns.CURVE_SAMPLES + 1] = (
		points[2] + out.normalized() * half_length * 2.0
		if out.length_squared() > 0.0
		else points[2]
	)
	return at + TrafficTurns.CURVE_SAMPLES + 2


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
			car.held_side = car.turn_side
			car.held_until_m = car.join_m + car.half_length + profile.wink_hold_m
			car.joined_until_m = car.join_m + car.half_length * 2.0
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
			# A dead end — the city's edge. In view it fades out where it stands
			# (`Q214`), and `_step_view` retires it once gone.
			if car.leaving or seen(car.pose.origin, car.half_length):
				car.leaving = true
			else:
				_retire(car)
			return
		_start_turn(car)
	if car.live:
		car.pose = _pose_on_turn(car) if car.turning else _pose_on_edge(car)


func _start_turn(car: Car) -> void:
	var points: PackedVector3Array = _turn_points(car, car.lane)
	car.p0 = points[0]
	car.p1 = points[1]
	car.p2 = points[2]
	car.turn_len = TrafficTurns.curve_length(car.p0, car.p1, car.p2)
	car.turn_u = 0.0
	car.turning = true


## The three points of the curve `car`'s next move drives, leaving its road at
## lane position `lane` — where it is as the turn starts, or the turn's lane
## when read ahead of it — and joining the next in its join lane.
func _turn_points(car: Car, lane: float) -> PackedVector3Array:
	var next_length: float = graph.plan_length_of(car.next_edge)
	var p0: Vector3 = graph.lane_at(
		car.edge, _edge_m(car.leave_m, car.length_m, car.along), car.along, lane
	)
	var p2: Vector3 = graph.lane_at(
		car.next_edge,
		_edge_m(car.join_m, next_length, car.next_along),
		car.next_along,
		car.next_lane
	)
	var into: Vector3 = _travel_dir(car.edge, car.leave_m, car.length_m, car.along)
	var out: Vector3 = _travel_dir(car.next_edge, car.join_m, next_length, car.next_along)
	return [p0, TrafficTurns.turn_control(p0, into, p2, out), p2]


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
	var at: Vector3 = TrafficTurns.curve_point(car.p0, car.p1, car.p2, u)
	var ahead: Vector3 = TrafficTurns.curve_point(car.p0, car.p1, car.p2, minf(u + 0.05, 1.0))
	var behind: Vector3 = TrafficTurns.curve_point(car.p0, car.p1, car.p2, maxf(u - 0.05, 0.0))
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
	TrafficRouted.leave_route(car)
	_unwreck(car)
	car.knocked = false
	retired += 1
	_hide(car)


## `INSTANCE_CUSTOM.a` above the livery's bit, `vehicle_body.gdshader`'s
## encoding: 2 for a running car, 4 more while it brakes, 8 for the left
## indicator and 16 for the right — `wink` 1 left, -1 right, `HAZARDS` both,
## the stopping parked car's (`P3-3f`). 0 is a switched-off car.
static func lamp_bits(running: bool, braking: bool, wink: int = 0) -> int:
	var bits: int = (2 if running else 0) + (LAMP_BRAKE if running and braking else 0)
	if wink == WINK_LEFT or wink == HAZARDS:
		bits += LAMP_LEFT
	if wink == WINK_RIGHT or wink == HAZARDS:
		bits += LAMP_RIGHT
	return bits


## The indicator `car` shows: its turn's side from `lane_change_m` before the
## mouth until its tail is `wink_hold_m` past the mouth it joined by (left 1,
## right -1) — the next turn's approach first — else the side it is changing
## lane to, else none — never for straight on. A routed vehicle winks the kerb
## (left) from `lane_change_m` short of its stop and while it stands there, and
## the offside (right) for `pull_out_m` as it pulls away, as a bus driver does.
func _winking(car: Car) -> int:
	if car.knocked:
		return HAZARDS
	if car.turning:
		return car.turn_side
	if standing(car) or pulling_in(car):
		return WINK_LEFT
	if approaching_turn(car):
		return car.turn_side
	if car.held_side != 0 and car.s < car.held_until_m:
		return car.held_side
	return car.shift


## Whether `car` is within `lane_change_m` of its kerbside stop, or routed and of
## its stop's pole on the stop's own road and way, and not yet past it: it winks
## the kerb.
func pulling_in(car: Car) -> bool:
	if car.kerb_m < INF and not car.turning:
		var to_kerb: float = car.kerb_m - car.s - car.half_length
		if to_kerb > -profile.dwell_reach_m and to_kerb < profile.lane_change_m:
			return true
	if car.goal == null or not TrafficRouted.is_goal_way(car, car.edge, car.along):
		return false
	var to_pole: float = TrafficRouted.to_pole(car, car.route.stops[car.stop_index])
	return to_pole > -profile.dwell_reach_m and to_pole < profile.lane_change_m


## Whether `car` is within `lane_change_m` of a turn's mouth: its indicator is
## that turn's.
func approaching_turn(car: Car) -> bool:
	return car.turn_side != 0 and car.next_edge >= 0 and car.leave_m - car.s < profile.lane_change_m


func _write_lamps(car: Car, bits: int) -> void:
	if car.for_hire:
		bits |= ROOF_SIGN
	if bits == car.written:
		return
	car.written = bits
	if car.slot >= 0:
		_batches[car.kind].set_instance_custom_data(car.slot, _datum(car))


## What `car`'s instance carries: its livery, and its lamp bits above it.
func _datum(car: Car) -> Color:
	var data: Color = car.livery
	data.a = car.livery.a + maxi(car.written, 0)
	return data


func _hide(car: Car) -> void:
	car.shape.disabled = true
	_drop_slot(car)
	_write_lamps(car, lamp_bits(false, false))


## Draw `car`: the next instance of its kind's batch, at its pose and datum.
func _take_slot(car: Car) -> void:
	var shown: Array = _shown[car.kind]
	car.slot = shown.size()
	shown.append(car)
	_write_instance(car)
	_batches[car.kind].visible_instance_count = shown.size()


## Stop drawing `car`: the batch's last drawn car moves into its place, so the
## drawn instances stay the batch's first ones.
func _drop_slot(car: Car) -> void:
	if car.slot < 0:
		return
	var shown: Array = _shown[car.kind]
	var last: Car = shown.back()
	if last != car:
		shown[car.slot] = last
		last.slot = car.slot
		_write_instance(last)
	shown.pop_back()
	_batches[car.kind].visible_instance_count = shown.size()
	car.slot = -1


## Write `car`'s pose and datum into the instance it is drawn from.
func _write_instance(car: Car) -> void:
	var batch: MultiMesh = _batches[car.kind]
	batch.set_instance_transform(car.slot, car.pose)
	batch.set_instance_custom_data(car.slot, _datum(car))


## Whether `car` is drawn, by the system's own record, from the batch of the
## kind it wears and from no other: headless, the dummy renderer keeps no
## buffer to read back.
func draws(car: Car) -> bool:
	for kind: int in _shown.size():
		if kind != car.kind and _shown[kind].has(car):
			return false
	var shown: Array = _shown[car.kind]
	return (
		car.slot >= 0
		and car.slot < shown.size()
		and shown[car.slot] == car
		and _batches[car.kind].visible_instance_count == shown.size()
	)


## Wear another kind: out of the batch it is drawn from and, if it was drawn,
## into the new kind's.
func _change_kind(car: Car, kind: int) -> void:
	var drawn: bool = car.slot >= 0
	_drop_slot(car)
	car.kind = kind
	if drawn:
		_take_slot(car)


## The moving cars the near miss should look at, as `ParkedLayer.near` hands out
## its own with each one's `velocity` added (`Q175`): within `radius_m` of a
## global point, or as much further as the car covers in `look_s`, since the
## disc is sized for a parked car and one may be coming the other way.
func near_cars(point: Vector3, radius_m: float, look_s: float) -> Array[Dictionary]:
	var found: Array[Dictionary] = []
	for car: Car in cars:
		if not car.live:
			continue
		var pose: Transform3D = car.pose
		var far_x: float = pose.origin.x - point.x
		var far_z: float = pose.origin.z - point.z
		var reach_m: float = radius_m + car.speed * look_s
		if far_x * far_x + far_z * far_z > reach_m * reach_m:
			continue
		car.obstacle["transform"] = pose
		car.obstacle["velocity"] = car.slide if car.knocked else -pose.basis.z * car.speed
		found.append(car.obstacle)
	return found


## Seconds run, for a car's temper.
func clock_s() -> float:
	return _clock_s


## The mesh box `car` is drawn and collides as, in its own frame.
func extent_of(car: Car) -> AABB:
	return _extents[car.kind]
