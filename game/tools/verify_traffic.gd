## The traffic (`P3-3c`, `Q173`), headless: the fleet driven for `RUN_S` with
## no player, the ring centred on the signalled junctions, every tick checked —
## three seeds there, then the first again centred on the back streets, where
## the parked vehicles stand in a road's only lane.
##
## - 🔴 **No car crosses its stop point on red or red-and-amber.** The front
##   bumper's travel past the stop is watched tick by tick; a crossing while
##   the light shows either fails by name. Amber may be crossed: a car that
##   could not stop goes through.
## - 🔴 **Every move is a legal arc**: each change of edge is one of
##   `RoadRouter.moves_from` from the edge left, and every way driven is one the
##   legal profile admits. A turn that crossed a road inside the junction
##   (`RoadGraph.is_stub`) is that chain of arcs, each legal.
## - 🔴 **No car drives along a road inside a junction**: a stub is crossed in
##   the turn's curve, never stood on (the user's drive, 2026-10-29).
## - **No car runs into the one ahead in its own lane**: two cars on one edge,
##   one way, in one lane (`TrafficSystem.same_lane`), off the turn, never
##   stand closer than their half-lengths.
## - 🔴 **No car stands inside a parked vehicle** (`P3-3f`, the user's drive
##   2026-10-29: cars drove through them). Each region's `ParkedLayer` is
##   resident at its clock's first hour, and every live car's plan box is
##   tested against every standing vehicle on its road and the road it joins.
##   Some car must have moved out to pass one.
##   The `parked:` table is what the roster puts in the lanes, by source.
## - **No two cars meet head on**: a car edging out over the centre line round a
##   parked vehicle waits for the way to clear, and one coming stops for it, so
##   two cars on one road, opposite ways, off the turn, never overlap in plan.
##   The free drive need not meet that case (Wan Chai's alone never does), so
##   `give way:` stages it: two cars on a back street, the rule held each way.
## - 🔴 **A car winks before every turn and never straight on** (`P3-3f`): at
##   the last tick of a car's straight run its lamp bits carry the turn's side
##   and not the other, and a straight-on move carries neither as it starts;
##   as a turn joins its road the car still winks its side (`wink_hold_m`).
## - 🔴 **A car gives way at its line** (`Q173`, the user's drive 2026-11-04: cars
##   drove through each other at junctions without lights): some car is held
##   by it, and no two cars meet in a signalled junction. The `crossing:` lines
##   count two cars in one another with one at least in its turn, by whether
##   either turns off a signalled approach; the unsignalled line is printed,
##   not gated — seed 4 meets one pair where two roads cross with no node.
## - 🔴 **A knocked car slides, stands and drives on** (`Q180`), staged by hand
##   on a two-lane one-way road with nothing parked: every moving kind carries a
##   mass; a car pushed square across its lane slides into the next one, on its
##   hazards, as far as the road tyre's grip at the pace's gravity takes it
##   (`v² / 2 μ g`), without turning, and settles; a car coming in that lane stops
##   for it there — where its own lane says it is in the other — and never runs
##   into it; then the knocked car rejoins its nearside lane on its road, a way it
##   may drive. One pushed off its middle turns; one turned round stands.
## - 🔴 **A taxi wears the licence its spawn region draws** (`Q183`): each region's
##   `taxi_licences` is printed, every mesh it names is in the library, and a
##   staged fleet of taxis on a mix of red and green in the frame and blue in its
##   neighbour wears, at every spawn, a licence its spawn road's region names, in
##   that licence's slot, with the green and the lit roof signs near their
##   shares, and the lit ones writing the roof sign's bit.
## - 🔴 **The traffic follows the census's hours** (`Q186`): each checked hour
##   runs its share of `cars` and draws each kind near its weight; driven at
##   20:00 and then 04:00, no car is placed into a full fleet, the fleet thins,
##   and a respawn drawn as another kind stands in that kind's slot at its size.
##   The seeds drive at `PEAK_HOUR`, the whole fleet.
## - 🔴 **A bus keeps to its route and stands at its stops** (`P3-78`, `Q182`):
##   the three seeds above drive the wandering fleet alone, as they were measured;
##   a fourth drive adds the routed fleet at 08:00, holds every check above but the
##   signalled meeting — printed, since seeds 1, 2 and 8 of the wandering fleet
##   alone already meet at two merges (e114 / e216 into e333, e618's fork) — and
##   holds that a routed vehicle's planned move is always its stop's search's,
##   that it stands still and at its stop's pole while it dwells, that some
##   stop was served, and that a routed minibus wears green and a wandering one red.
## - No car runs over its cruise.
## - `RoadGraph.lane_at` puts a car where `Hit.lane_centre` would, both ways,
##   at the middle of every edge the query resolves to itself.
## - **Something happened**: cars spawned and moved, and at least one was held
##   by a light and one by a car — a run in which nothing ever stopped would
##   pass every check above.
##
##     godot --headless --path game --script res://tools/verify_traffic.gd
extends "res://tools/verify_tool.gd"

const TrafficScript = preload("res://scripts/traffic/traffic_system.gd")
const PlanScript = preload("res://scripts/traffic/signal_plan.gd")
const FareSystemScript = preload("res://scripts/fares/fare_system.gd")
const ParkedLayerScript = preload("res://scripts/city/parked_layer.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

const TICK_S: float = 1.0 / 60.0
const RUN_S: float = 90.0
const SPEED_SLACK_MPS: float = 1e-3
## Three fleets, each its own rolls. 4 is the seed that found the car creeping
## over the line at amber behind a slow leader (2026-10-29); 7 and 23 two more.
const SEEDS: Array[int] = [7, 4, 23]
## A car this far into a parked vehicle's box is inside it. Not zero: a car's
## heading snaps at a polyline vertex, and on one right-angle corner at a
## junction mouth (Wan Chai's edge 904, Causeway Bay's 110: one road) its box
## swings 0.086 / 0.13 m into a parked car's that the lanes say it clears
## (2026-10-30) — a box that is itself the mesh's bound, not its shape.
const INSIDE_M: float = 0.15
## How long the drive runs on for a car to stage the horn on.
const HORN_SEARCH_S: float = 30.0
## The knock (`Q180`): the road at least this long, the car this far down it and the
## one coming this far behind, and how long it has to slide, stand and drive on.
const KNOCK_ROAD_M: float = 100.0
const KNOCK_AT_M: float = 40.0
const KNOCK_BEHIND_M: float = 25.0
const KNOCK_CLOSE_M: float = 12.0
const KNOCK_AGAIN_MPS: float = 4.0
const KNOCK_RUN_S: float = 40.0
## The hour the routed fleet is driven at: the morning peak, TD's busiest.
const ROUTED_HOUR: float = 8.0
## The hour the wandering seeds are driven at (`Q186`): the census's busiest, at
## which the whole of `cars` is out — the fleet the seeds were measured on.
const PEAK_HOUR: float = 12.0
## The hours the fleet and the mix are checked at (`Q186`): the shift's opening,
## the midday peak, the night's taxis, and a small hour, where few run.
const CHECK_HOURS: Array[int] = [7, 12, 20, 4]
## How far a kind's share over `KIND_DRAWS` draws may sit from its weight.
const KIND_DRAWS: int = 4000
const KIND_SLACK: float = 0.03
## Where the hours drive moves its ring at the switch: past `retire_m` and the
## spawn ring both, so every evening car retires.
const FAR_M: float = 600.0
## The kind whose colour is its licence (`Q167`): green on a route, red off one.
const MINIBUS: String = "minibus"
## A dwelling vehicle's front this much past `dwell_reach_m` from its pole is not
## at its stop: a tick's travel at the turning pace.
const DWELL_SLACK_M: float = 0.15


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_traffic", 360.0)


func _run() -> void:
	_check_rules()
	var table := load(TrafficProfile.PATH) as TrafficProfile
	_expect(table != null, "table", "%s loads" % TrafficProfile.PATH)
	if table == null:
		_finish("verify_traffic")
		return
	var graph: RoadGraph = RoadGraph.shared()
	if graph.is_empty():
		print("  no road graph resident; nothing to drive")
		_finish("verify_traffic")
		return
	_check_lane(graph)
	var layers: Array[Node] = _stand_parked(graph)
	_check_knock(graph, table, layers)
	_check_licences(graph, table)
	_check_hours(graph, table)
	# The three fleets round the signals, then the first again on the back
	# streets, where a car can only pass a parked one over the centre line.
	for run: int in SEEDS.size() + 2:
		var seed: int = SEEDS[run % SEEDS.size()]
		var back_street: bool = run == SEEDS.size()
		var routed: bool = run == SEEDS.size() + 1
		var system: TrafficSystem = TrafficScript.new()
		if routed:
			system.hour_override = ROUTED_HOUR
		else:
			system.hour_override = PEAK_HOUR
			# The wandering fleet alone, what the seeds were measured on: an empty
			# set, since `setup` reads the resident routes only into a null one.
			system.bus_routes = BusRoutes.new()
		if not system.setup(graph, table, seed):
			_fail("setup", "the shipped table and city carry no traffic")
			system.free()
			break
		root.add_child(system)
		if system.signals == null or system.signals.plan.is_empty():
			_fail("setup", "no signal plan resident; the stop check would read nothing")
			system.queue_free()
			break
		if routed and system.bus_routes.is_empty():
			print("  no bus route resident; the routed fleet is not driven")
			system.queue_free()
			break
		print(
			(
				"  seed %d%s:"
				% [
					seed,
					(
						" on the back streets"
						if back_street
						else (" with the routed fleet at %02d:00" % ROUTED_HOUR if routed else "")
					)
				]
			)
		)
		system.read_parked(layers)
		if run == 0:
			_print_parked(system)
		system.centre = (
			_back_street_centre(system) if back_street else _signal_centre(system.signals.plan)
		)
		if back_street:
			_check_give_way(system)
		_drive(system, not back_street, routed)
		system.queue_free()
	_finish("verify_traffic")


## A car knocked by hand (`Q180`) on a long two-lane one-way road with nothing
## parked on it: across into the offside lane, then three more knocks. Two cars:
## the one knocked and one coming in the offside lane.
func _check_knock(graph: RoadGraph, table: TrafficProfile, layers: Array[Node]) -> void:
	var system: TrafficSystem = TrafficScript.new()
	if not system.setup(graph, table, SEEDS[0]):
		_fail("knock", "the shipped table and city carry no traffic")
		system.free()
		return
	root.add_child(system)
	system.read_parked(layers)
	var masses: Dictionary[String, float] = (load(ParkedProfile.PATH) as ParkedProfile).masses_kg
	for kind: String in table.kinds:
		_expect(masses.get(kind, 0.0) > 0.0, "knock", "%s carries a kerb mass" % kind)
	var grip: float = TrafficScript.grip_mps2()
	_expect(grip > 0.0, "knock", "a knocked car has the road tyre's grip (%.1f m/s²)" % grip)
	var found: Vector2i = _knock_road(system)
	_expect(found.x >= 0, "knock", "a long two-lane one-way road with nothing parked")
	if found.x < 0 or grip <= 0.0:
		_drop(system)
		return
	var edge: int = found.x
	var along: bool = found.y == 1
	var struck: TrafficSystem.Car = system.cars[0]
	var coming: TrafficSystem.Car = system.cars[1]
	system.cars.resize(2)
	_stage(system, struck, edge, along, KNOCK_AT_M)
	_stage(system, coming, edge, along, KNOCK_AT_M - KNOCK_BEHIND_M)
	coming.lane = 1.0
	system._enter(coming)
	coming.pose = system._pose_on_edge(coming)
	struck.speed = 0.0
	coming.speed = coming.cruise_mps * 0.5
	system.centre = struck.pose.origin
	_expect(
		struck.body.has_meta(Pushable.OWNER_META), "knock", "a car's body is the taxi's to push"
	)
	# Square across into the offside lane's middle: v² = 2 a d.
	var forward: Vector3 = -struck.pose.basis.z
	var offside: Vector3 = -RoadGraph.left_of(forward)
	var at_m: float = TrafficScript._edge_m(KNOCK_AT_M, struck.length_m, along)
	var lane_m: float = (
		(
			system.graph.lane_at(edge, at_m, along, 1.0)
			- system.graph.lane_at(edge, at_m, along, 0.0)
		)
		. length()
	)
	var across_mps: float = sqrt(2.0 * grip * lane_m)
	var start: Vector3 = struck.pose.origin
	system.take_push(struck.body, offside * struck.mass_kg * across_mps, system._centre_of(struck))
	_expect(struck.knocked and system.knocks == 1, "knock", "a push knocks it off its lane")
	_expect(is_zero_approx(struck.spin), "knock", "pushed through its middle it does not turn")
	_expect(system._winking(struck) == TrafficSystem.HAZARDS, "knock", "it stands on its hazards")
	var deepest: float = 0.0
	var held: bool = false
	var settled_s: float = INF
	var recovered_s: float = INF
	# Where it set out to rejoin, `(edge, along, lane)`, read as it drives on.
	var rejoins := Vector3(-1.0, 0.0, -1.0)
	var t: float = 0.0
	while t < KNOCK_RUN_S and is_inf(recovered_s):
		system.step(TICK_S)
		t += TICK_S
		if struck.knocked and struck.slide == Vector3.ZERO and is_inf(settled_s):
			settled_s = t
			var moved: Vector3 = struck.pose.origin - start
			var expected: float = across_mps * across_mps / (2.0 * grip)
			_expect(
				absf(moved.dot(offside) - expected) < across_mps * TICK_S * 2.0,
				"knock",
				(
					"it slides %.2f m across, as the grip takes it (%.2f m), in %.2f s"
					% [moved.dot(offside), expected, t]
				)
			)
			_expect(absf(moved.dot(forward)) < 0.01, "knock", "and not along")
		held = held or coming.held == TrafficSystem.Held.CAR
		if struck.knocked:
			deepest = maxf(
				deepest,
				_overlap(
					_plan_box(struck.pose, system.extent_of(struck)),
					_plan_box(coming.pose, system.extent_of(coming))
				)
			)
		elif rejoins.x < 0.0:
			rejoins = Vector3(struck.next_edge, 1.0 if struck.next_along else 0.0, struck.next_lane)
		if not struck.knocked and not struck.turning:
			recovered_s = t
	_expect(not is_inf(settled_s), "knock", "it comes to rest")
	_expect(held, "knock", "the car coming in that lane stops for it")
	_expect(deepest <= INSIDE_M, "knock", "and never runs into it (%.2f m)" % deepest)
	_expect(
		not is_inf(recovered_s) and system.recovered == 1,
		"knock",
		"it drives on again (%.1f s after it settled)" % (recovered_s - settled_s)
	)
	_expect(
		rejoins == Vector3(edge, 1.0 if along else 0.0, 0.0),
		"knock",
		"for its nearside lane, on its road, the way it was going"
	)
	_expect(
		struck.edge == edge and TrafficSystem.same_lane(struck.lane, 0.0),
		"knock",
		"and is in it as its way back ends"
	)
	# Knocked across the offside lane and still moving — its own lane still says the
	# nearside, its heading is no queue's and it has not settled to stand as parked —
	# it is in the way of a car coming in that lane.
	_stage(system, struck, edge, along, KNOCK_AT_M)
	_stage(system, coming, edge, along, KNOCK_AT_M - KNOCK_CLOSE_M)
	coming.lane = 1.0
	system._enter(coming)
	coming.pose = system._pose_on_edge(coming)
	var offside_lane: Vector3 = system.graph.lane_at(edge, at_m, along, 1.0)
	struck.pose = Transform3D(
		struck.pose.basis.rotated(Vector3.UP, PI * 0.5),
		Vector3(offside_lane.x, struck.pose.origin.y, offside_lane.z)
	)
	system.take_push(struck.body, -struck.pose.basis.z * struck.mass_kg, system._centre_of(struck))
	_expect(
		system._gap_ahead(coming) < INF,
		"knock",
		"knocked across the lane of a car coming, still moving, it is in that car's way"
	)
	# Pushed square across at its front corner, it turns.
	_stage(system, struck, edge, along, KNOCK_AT_M)
	coming.live = false
	var front: Vector3 = system._centre_of(struck) + forward * struck.half_length
	system.take_push(struck.body, offside * struck.mass_kg * across_mps, front)
	_expect(
		struck.spin * Pushable.yaw_moment(forward, offside) > 0.0,
		"knock",
		"pushed at its front corner it turns, nose first (%.2f rad/s)" % struck.spin
	)
	_step_for(system, KNOCK_RUN_S * 0.25)
	# Turned round on a one-way road it does not reverse: it stands.
	_stage(system, struck, edge, along, KNOCK_AT_M)
	struck.pose.basis = struck.pose.basis.rotated(Vector3.UP, PI)
	system.take_push(struck.body, offside * struck.mass_kg, system._centre_of(struck))
	var before: int = system.recovered
	_step_for(system, table.recover_after_s * 4.0)
	_expect(
		struck.knocked and system.recovered == before,
		"knock",
		"turned round on a one-way road, it stands"
	)
	# Pushed again where it stands, it slides on and stands where it settles.
	var was: Vector2 = _wreck_span(system, struck, edge)
	system.take_push(
		struck.body,
		-struck.pose.basis.z * struck.mass_kg * KNOCK_AGAIN_MPS,
		system._centre_of(struck)
	)
	_step_for(system, table.react_s + KNOCK_RUN_S * 0.25)
	var now: Vector2 = _wreck_span(system, struck, edge)
	_expect(
		(
			was.x >= 0.0
			and now.x >= 0.0
			and absf(now.x - was.x) > KNOCK_AGAIN_MPS * table.react_s * 0.5
		),
		"knock",
		(
			"pushed again, it stands where it settles, not where it stood (%.1f → %.1f m)"
			% [was.x, now.x]
		)
	)
	print(
		(
			"  knock:    %d knocks, %d drove on, settled at %.2f s, on its way %.1f s later"
			% [system.knocks, system.recovered, settled_s, recovered_s - settled_s]
		)
	)
	_drop(system)


## Where `car`'s one footprint stands on `edge`, as its near end and its count, or
## `x` -1 where it has none or more than one.
static func _wreck_span(system: TrafficSystem, car: TrafficSystem.Car, edge: int) -> Vector2:
	var found: Array[float] = []
	for parked: TrafficSystem.Parked in system.parked_on(edge):
		if parked.wreck == car:
			found.append(parked.s_from)
	return Vector2(found[0], 1.0) if found.size() == 1 else Vector2(-1.0, found.size())


## The licences (`Q183`): the shipped mixes, then a fleet of taxis on a staged
## mix, every spawn's licence and roof sign read off its batches.
func _check_licences(graph: RoadGraph, table: TrafficProfile) -> void:
	var shipped: TrafficSystem = TrafficScript.new()
	if not shipped.setup(graph, table, SEEDS[0]):
		_fail("licence", "the shipped table and city carry no traffic")
		shipped.free()
		return
	for region: String in graph.resident_regions():
		var mix: Dictionary = shipped.licence_mixes.get(region, {})
		print("  licence: %s %s" % [region, str(mix) if not mix.is_empty() else "none (red)"])
		for mesh: String in mix:
			_expect(
				shipped._licence_kinds.has(mesh),
				"licence",
				"%s's %s is in the library" % [region, mesh]
			)
	shipped.free()

	var regions: PackedStringArray = graph.resident_regions()
	var staged_table := table.duplicate() as TrafficProfile
	var always := PackedFloat32Array()
	always.resize(TrafficProfile.HOURS)
	always.fill(1.0)
	staged_table.kinds = {table.taxi_kind: always}
	var system: TrafficSystem = TrafficScript.new()
	system.licence_mixes[regions[0]] = {"taxi": 0.5, "taxi_nt": 0.5}
	if regions.size() > 1:
		system.licence_mixes[regions[1]] = {"taxi_lantau": 1.0}
	if not system.setup(graph, staged_table, SEEDS[0]):
		_fail("licence", "a fleet of taxis does not set up")
		system.free()
		return
	root.add_child(system)
	_expect(
		system._licence_kinds.size() == system.licence_mixes.size() + 1,
		"licence",
		"every staged licence is a drawn kind (%d)" % system._licence_kinds.size()
	)
	system.centre = _signal_centre(system.signals.plan)
	var lives: Dictionary[int, int] = {}
	var worn: Dictionary[String, int] = {}
	var spawns: int = 0
	var lit: int = 0
	var wrong: int = 0
	var shown_wrong: int = 0
	var bit_wrong: int = 0
	var in_frame: int = 0
	var green_in_frame: int = 0
	for _tick: int in roundi(RUN_S / TICK_S):
		system.step(TICK_S)
		for car: TrafficSystem.Car in system.cars:
			if not car.live or car.routed or lives.get(car.id, 0) == car.lives:
				continue
			lives[car.id] = car.lives
			spawns += 1
			var region: String = graph.region_of(car.edge)
			var mesh: String = system.kind_name(car)
			worn[mesh] = worn.get(mesh, 0) + 1
			if not (system.licence_mixes.get(region, {}) as Dictionary).has(mesh):
				wrong += 1
			if region == regions[0]:
				in_frame += 1
				if mesh == "taxi_nt":
					green_in_frame += 1
			# Read off the system's own record: headless, the dummy renderer keeps
			# no `MultiMesh` buffer to read a transform or a datum back from.
			if car.kind_slots.get(car.kind, -1) != car.slot:
				shown_wrong += 1
			if ((car.written & TrafficSystem.ROOF_SIGN) != 0) != car.for_hire:
				bit_wrong += 1
			if car.for_hire:
				lit += 1
	print("  licence: %d spawns of a fleet of taxis wore %s, %d lit for hire" % [spawns, worn, lit])
	_expect(spawns >= 24, "licence", "the fleet spawned at least once each (%d)" % spawns)
	_expect(wrong == 0, "licence", "no taxi wears a licence its spawn region does not name")
	_expect(
		in_frame > 0 and absf(float(green_in_frame) / maxf(in_frame, 1) - 0.5) < 0.2,
		"licence",
		"the frame's staged half green wears green (%d of %d)" % [green_in_frame, in_frame]
	)
	_expect(shown_wrong == 0, "licence", "a taxi stands in its own licence's slot")
	_expect(bit_wrong == 0, "licence", "a lit roof sign writes the bit, a dark one not")
	_expect(
		absf(float(lit) / maxf(spawns, 1) - table.taxi_for_hire) < 0.2,
		"licence",
		"the lit roof signs are near their share (%d of %d)" % [lit, spawns]
	)
	# The draw itself, over a thousand ids: near each share.
	var green: int = 0
	for id: int in 1000:
		if system.licence_of(regions[0], id, 1) == "taxi_nt":
			green += 1
	_expect(
		absf(green / 1000.0 - 0.5) < 0.05,
		"licence",
		"the staged half green draws %d of 1000 green" % green
	)
	_expect(
		system.licence_of("nowhere", 3, 1) == table.taxi_kind,
		"licence",
		"a region with no mix wears the red urban taxi"
	)
	_drop(system)


## The census's hours (`Q186`): the fleet each hour stands at, the kinds each
## hour draws, a respawn drawn afresh into its own slot at its own size, and a
## fleet that thins when the hour does — no car placed while the fleet is full.
func _check_hours(graph: RoadGraph, table: TrafficProfile) -> void:
	var peak: int = 0
	for hour: int in TrafficProfile.HOURS:
		if table.fleet_by_hour[hour] > table.fleet_by_hour[peak]:
			peak = hour
	_expect(
		is_equal_approx(table.fleet_by_hour[peak], 1.0) and peak == int(PEAK_HOUR),
		"hours",
		"the fleet is whole at its busiest hour, %02d:00, the seeds' own" % peak
	)
	for hour: int in CHECK_HOURS:
		var system: TrafficSystem = TrafficScript.new()
		system.hour_override = hour
		if not system.setup(graph, table, SEEDS[0]):
			_fail("hours", "the shipped table and city carry no traffic")
			system.free()
			return
		var wanted: int = roundi(table.cars * table.fleet_by_hour[hour])
		_expect(
			system.fleet_now() == wanted,
			"hours",
			"%02d:00 runs %d of %d cars (%d)" % [hour, wanted, table.cars, system.fleet_now()]
		)
		var drawn: Dictionary[String, int] = {}
		for draw: int in KIND_DRAWS:
			var kind: String = system._kinds[system.kind_for(draw % 97, floori(draw / 97.0) + 1)]
			drawn[kind] = drawn.get(kind, 0) + 1
		var total: float = 0.0
		for kind: String in table.kinds:
			total += table.kinds[kind][hour]
		var worst: float = 0.0
		var shares: PackedStringArray = []
		for kind: String in table.kinds:
			var share: float = float(drawn.get(kind, 0)) / KIND_DRAWS
			worst = maxf(worst, absf(share - table.kinds[kind][hour] / total))
			shares.append("%s %.2f" % [kind, share])
		print("  hours: %02d:00 %d cars, %s" % [hour, system.fleet_now(), ", ".join(shares)])
		_expect(
			worst < KIND_SLACK,
			"hours",
			"%02d:00 draws each kind near its weight (worst %.3f)" % [hour, worst]
		)
		system.free()

	# A drive at the evening's hour, then the small hours: every respawn in its
	# own kind's slot at its own size, and no car placed into a full fleet.
	var drive: TrafficSystem = TrafficScript.new()
	drive.hour_override = 20
	drive.bus_routes = BusRoutes.new()
	if not drive.setup(graph, table, SEEDS[1]):
		_fail("hours", "the shipped table and city carry no traffic")
		drive.free()
		return
	root.add_child(drive)
	drive.centre = _signal_centre(drive.signals.plan)
	var lives: Dictionary[int, int] = {}
	var first: Dictionary[int, int] = {}
	var respawns: int = 0
	var redrawn: int = 0
	var misworn: int = 0
	var over: int = 0
	var most: int = 0
	var thinned_to: int = 0
	var ticks: int = roundi(RUN_S / TICK_S)
	for tick: int in ticks * 2:
		if tick == ticks:
			# The small hours, and the ring moved off: the evening's cars retire
			# as they would driving away, and only the hour's few are placed.
			drive.hour_override = 4
			drive.centre = _far_centre(drive)
		var spawned_before: int = drive.spawned
		drive.step(TICK_S)
		var live: int = drive.live_wandering()
		# A car may be placed on the tick another retired: over its hour's size after
		# a placing, it was placed into a full fleet.
		if live > drive.fleet_now() and drive.spawned > spawned_before:
			over += 1
		if tick < ticks:
			most = maxi(most, live)
		else:
			thinned_to = live
		for car: TrafficSystem.Car in drive.cars:
			if not car.live or lives.get(car.id, 0) == car.lives:
				continue
			if not first.has(car.id):
				first[car.id] = car.kind
			elif car.lives > 1:
				respawns += 1
				if car.kind != first[car.id]:
					redrawn += 1
			lives[car.id] = car.lives
			var extent: AABB = drive.extent_of(car)
			if (
				car.kind_slots.get(car.kind, -1) != car.slot
				or not is_equal_approx(car.half_length, extent.size.z * 0.5)
			):
				misworn += 1
	print(
		(
			(
				"  hours: 20:00 drive, at most %d of %d live, %d respawns, %d in another kind;"
				+ " 04:00 thinned it to %d of %d"
			)
			% [
				most,
				roundi(table.cars * table.fleet_by_hour[20]),
				respawns,
				redrawn,
				thinned_to,
				roundi(table.cars * table.fleet_by_hour[4])
			]
		)
	)
	_expect(over == 0, "hours", "no car is placed into a full fleet")
	_expect(
		thinned_to == roundi(table.cars * table.fleet_by_hour[4]),
		"hours",
		"the small hours' fleet stands at its size (%d)" % thinned_to
	)
	_expect(
		most <= roundi(table.cars * table.fleet_by_hour[20]),
		"hours",
		"the evening fleet never runs over its hour's size (%d)" % most
	)
	_expect(
		respawns > 0 and redrawn > 0,
		"hours",
		"a respawn is drawn afresh (%d of %d)" % [redrawn, respawns]
	)
	_expect(misworn == 0, "hours", "every spawn stands in its own kind's slot at its size")
	_drop(drive)

	# Half minibuses: a car redrawn as one wears a wandering minibus's red, and
	# one redrawn as a saloon the saloons' palette, never the red.
	var staged_table := table.duplicate() as TrafficProfile
	var half := PackedFloat32Array()
	half.resize(TrafficProfile.HOURS)
	half.fill(1.0)
	staged_table.kinds = {MINIBUS: half, "car_a": half}
	var staged: TrafficSystem = TrafficScript.new()
	staged.hour_override = PEAK_HOUR
	staged.bus_routes = BusRoutes.new()
	if not staged.setup(graph, staged_table, SEEDS[2]):
		_fail("hours", "a fleet of minibuses and saloons does not set up")
		staged.free()
		return
	root.add_child(staged)
	staged.centre = _signal_centre(staged.signals.plan)
	var red: Color = Color(table.wander_liveries[MINIBUS][0], 1.0)
	var minibus: int = staged._kinds.find(MINIBUS)
	var red_right: int = 0
	var red_wrong: int = 0
	var seen: Dictionary[int, int] = {}
	for tick: int in ticks * 2:
		if tick == ticks:
			staged.centre = _far_centre(staged)
		staged.step(TICK_S)
		for car: TrafficSystem.Car in staged.cars:
			if not car.live or car.lives < 2 or seen.get(car.id, 0) == car.lives:
				continue
			seen[car.id] = car.lives
			if (car.kind == minibus) == car.livery.is_equal_approx(red):
				red_right += 1
			else:
				red_wrong += 1
	print("  hours: a staged half-minibus fleet, %d respawns read" % (red_right + red_wrong))
	_expect(
		red_right > 0 and red_wrong == 0,
		"hours",
		"a respawned wandering minibus wears red, and nothing else does (%d wrong)" % red_wrong
	)
	_drop(staged)


## A point on a road the traffic drives, past `FAR_M` from the system's centre.
func _far_centre(system: TrafficSystem) -> Vector3:
	for edge: int in system._admitted:
		var at: Vector3 = system.graph.lane_at(edge, system.graph.plan_length_of(edge) * 0.5, true)
		if Vector2(at.x - system.centre.x, at.z - system.centre.z).length() > FAR_M:
			return at
	_fail("hours", "no road the traffic drives lies %.0f m from the centre" % FAR_M)
	return system.centre


## A level-0 one-way road with two lanes, `KNOCK_ROAD_M` long and nothing parked
## on it, as `(edge, along)`, or `x` -1.
## Out of the tree at once, not at the frame's end: the drives after it find
## their own system first in `TrafficSystem.GROUP`, and a script runs in one frame.
func _drop(system: TrafficSystem) -> void:
	root.remove_child(system)
	system.free()


static func _knock_road(system: TrafficSystem) -> Vector2i:
	for edge: int in system._admitted:
		var forward: bool = system.router.admits_way(edge, true)
		if forward == system.router.admits_way(edge, false):
			continue
		if (
			system.graph.level_of(edge) != 0
			or system.graph.lanes_each_way(edge) < 2
			or system.graph.plan_length_of(edge) < KNOCK_ROAD_M
			or not system.parked_on(edge).is_empty()
		):
			continue
		return Vector2i(edge, 1 if forward else 0)
	return Vector2i(-1, 0)


## Each resident region's parked roster, stood where the scene stands it.
func _stand_parked(graph: RoadGraph) -> Array[Node]:
	var layers: Array[Node] = []
	for region: String in GeneratedRegions.resident():
		var holder := Node3D.new()
		holder.position = graph.region_offset(region)
		var layer: Node3D = ParkedLayerScript.new()
		layer.region = region
		holder.add_child(layer)
		root.add_child(holder)
		if layer.entry_count() > 0:
			layers.append(layer)
	_expect(not layers.is_empty(), "parked", "a parked roster is resident to drive past")
	return layers


func _print_parked(system: TrafficSystem) -> void:
	print("  parked:   source     lane 0  lane 1+  clear  one-lane")
	for source: String in system.parked_report:
		var row: Vector4i = system.parked_report[source]
		print("            %-9s %7d %8d %6d %9d" % [source, row.x, row.y, row.z, row.w])


## The static rules, off a scene: the amber judgement, the stopping speed and
## the turn's control point.
func _check_rules() -> void:
	# The horn's two bars, each from both sides.
	_expect(TrafficScript.wants_horn(10.0, 7.0, 0.0, 3.0, 2.0), "rules", "cut up at the bar")
	_expect(not TrafficScript.wants_horn(10.0, 7.5, 0.0, 3.0, 2.0), "rules", "just under it, not")
	_expect(TrafficScript.wants_horn(0.0, 0.0, 2.0, 3.0, 2.0), "rules", "stood the wait")
	_expect(not TrafficScript.wants_horn(0.0, 0.0, 1.9, 3.0, 2.0), "rules", "just short of it, not")
	_check_horn_patterns()
	var red := SignalController.Light.RED
	var amber := SignalController.Light.AMBER
	_expect(TrafficScript.must_stop(red, 100.0, 0.0, 3.0), "rules", "red stops a car")
	_expect(
		TrafficScript.must_stop(SignalController.Light.RED_AMBER, 100.0, 0.0, 3.0),
		"rules",
		"red-and-amber stops a car"
	)
	_expect(
		not TrafficScript.must_stop(SignalController.Light.GREEN, 1.0, 10.0, 3.0),
		"rules",
		"green does not"
	)
	# 10 m/s at 3 m/s² needs 16.7 m.
	_expect(TrafficScript.must_stop(amber, 20.0, 10.0, 3.0), "rules", "amber stops one that can")
	_expect(
		not TrafficScript.must_stop(amber, 10.0, 10.0, 3.0),
		"rules",
		"amber lets one that cannot go"
	)
	_expect(
		is_equal_approx(TrafficScript.stopping_speed(16.0 + 2.0 / 3.0, 3.0), 10.0),
		"rules",
		"the stopping speed inverts the stopping distance"
	)
	# A left turn: in heading north (-z) at the origin, out heading west (-x)
	# from (-6, 0, -6); the lines meet at (0, 0, -6).
	var corner: Vector3 = TrafficScript.turn_control(
		Vector3.ZERO, Vector3(0, 0, -1), Vector3(-6, 0, -6), Vector3(-1, 0, 0)
	)
	_expect(corner.is_equal_approx(Vector3(0, 0, -6)), "rules", "a turn bends at the lanes' corner")
	var straight: Vector3 = TrafficScript.turn_control(
		Vector3.ZERO, Vector3(0, 0, -1), Vector3(0, 0, -10), Vector3(0, 0, -1)
	)
	_expect(straight.is_equal_approx(Vector3(0, 0, -5)), "rules", "straight on takes the chord")
	# The give-way's order: straight on, then left, then right, then the fleet.
	_expect(
		(
			TrafficScript.goes_first(0, 5, 1, 1)
			and TrafficScript.goes_first(1, 5, -1, 1)
			and TrafficScript.goes_first(-1, 2, -1, 3)
			and not TrafficScript.goes_first(-1, 3, -1, 2)
		),
		"rules",
		"straight on gives way to nobody turning, a left before a right, then the earlier car"
	)
	# Its path test: an X crosses; two ways a lane apart, head to head, do not;
	# the same two nearer than their width do.
	var east := PackedVector3Array([Vector3(0, 0, 0), Vector3(5, 0, 0), Vector3(10, 0, 0)])
	var cross := PackedVector3Array([Vector3(5, 0, -5), Vector3(5, 0, 5)])
	var lane_over := PackedVector3Array([Vector3(10, 0, 3), Vector3(0, 0, 3)])
	var too_near := PackedVector3Array([Vector3(10, 0, 1.5), Vector3(0, 0, 1.5)])
	_expect(
		(
			TrafficScript.paths_cross(east, cross, 2.3, 2.0, 0.5)
			and not TrafficScript.paths_cross(east, lane_over, 2.3, 2.0, 0.5)
			and TrafficScript.paths_cross(east, too_near, 2.3, 2.0, 0.5)
		),
		"rules",
		"turns that cross meet, a lane apart head to head do not, nearer than a car's width do"
	)
	var north := Vector3(0, 0, -1)
	_expect(
		(
			TrafficScript.turn_side(north, Vector3(-1, 0, 0), 30.0) == 1
			and TrafficScript.turn_side(north, Vector3(1, 0, 0), 30.0) == -1
			and TrafficScript.turn_side(north, Vector3(0.2, 0, -1).normalized(), 30.0) == 0
		),
		"rules",
		"north to west is a left turn, to east a right, a 11° bend straight on"
	)


## The mean of the signalled junctions: where the lights are, so the ring holds
## cars that meet them.
func _signal_centre(plan: SignalPlan) -> Vector3:
	var sum := Vector3.ZERO
	for junction: SignalPlan.Junction in plan.junctions:
		sum += junction.position
	return sum / plan.junctions.size()


## What the tool remembers of a car between ticks.
class Seen:
	extends RefCounted
	var edge: int = -1
	var along: bool = true
	var front_m: float = 0.0
	var live: bool = false
	var lives: int = 0
	var turning: bool = false
	var turn_side: int = 0
	## The lamp bits it showed: a turn is judged by the last tick before it.
	var written: int = 0


## Two-way roads with one lane each way that traffic drives both ways: where a
## car can only pass a parked vehicle over the centre line.
static func _back_streets(system: TrafficSystem) -> Array[int]:
	var found: Array[int] = []
	for edge: int in system.graph.edge_ids():
		if system.graph.is_one_way(edge) or system.graph.lanes_each_way(edge) != 1:
			continue
		if system.router.admits_way(edge, true) and system.router.admits_way(edge, false):
			found.append(edge)
	return found


## The parked vehicle with the most others within `spawn_max_m` that stand in
## the one lane of a two-way road its way: where the ring meets them.
func _back_street_centre(system: TrafficSystem) -> Vector3:
	var blocking: Array[Vector3] = []
	var typical: float = system.extent_of(system.cars[0]).size.x * 0.5
	for edge: int in _back_streets(system):
		for parked: TrafficSystem.Parked in system.parked_on(edge):
			for along: bool in [true, false]:
				if parked.standing() and parked.in_lane(along, 0.0, typical, 0.0):
					blocking.append(parked.layer.obstacle_of(parked.index)["transform"].origin)
					break
	var best: Vector3 = Vector3.ZERO
	var most: int = -1
	for here: Vector3 in blocking:
		var near: int = 0
		for there: Vector3 in blocking:
			if RoadGraph.plan_distance(here, there) < system.profile.spawn_max_m:
				near += 1
		if near > most:
			most = near
			best = here
	print("  centre:   %d blocking parked vehicles within reach" % most)
	return best


## Two cars staged on a back street before the drive: one behind a parked
## vehicle in its only lane, one coming the other way. While the second is in
## reach the first keeps its lane; gone, it makes for the centre line; and once
## the first is out over it, the second stops for it.
func _check_give_way(system: TrafficSystem) -> void:
	var passer: TrafficSystem.Car = system.cars[0]
	var coming: TrafficSystem.Car = system.cars[1]
	var staged: bool = false
	for edge: int in _back_streets(system):
		if staged:
			break
		for parked: TrafficSystem.Parked in system.parked_on(edge):
			var length_m: float = system.graph.plan_length_of(edge)
			var span: Vector2 = parked.span(true, length_m)
			if not parked.standing() or span.x < 15.0 or span.y > length_m - 40.0:
				continue
			_stage(system, passer, edge, true, span.x - passer.half_length - 3.0)
			coming.live = false
			if system._lane_goal(passer) <= 0.0:
				continue
			_stage(system, coming, edge, false, length_m - span.y - 10.0)
			staged = true
			_expect(
				system._lane_goal(passer) == 0.0,
				"give way",
				"a car behind a parked vehicle on edge %d keeps its lane while one comes" % edge
			)
			passer.lane = system._lane_goal(passer)
			passer.over_centre = true
			coming.live = false
			_expect(
				system._lane_goal(passer) > 0.0,
				"give way",
				"and makes for the centre line once the way is clear"
			)
			coming.live = true
			_expect(
				system._gap_ahead(coming) < INF,
				"give way",
				"and the car coming stops for it once it is out"
			)
			break
	_expect(staged, "give way", "a back street with a parked vehicle to stage it on")
	passer.live = false
	coming.live = false


static func _stage(
	system: TrafficSystem, car: TrafficSystem.Car, edge: int, along: bool, s: float
) -> void:
	car.live = true
	car.edge = edge
	car.along = along
	car.s = s
	car.lane = 0.0
	car.turning = false
	car.held = TrafficSystem.Held.NONE
	car.over_centre = false
	car.knocked = false
	car.slide = Vector3.ZERO
	car.spin = 0.0
	system._unwreck(car)
	system._enter(car)
	car.pose = system._pose_on_edge(car)


## Drive `system` for `RUN_S`, every check on every tick; `at_signals` adds the
## checks that the lights were met at all.
func _drive(system: TrafficSystem, at_signals: bool, routed: bool = false) -> void:
	var off_route: int = 0
	var dwelling: int = 0
	var dwell_moving: int = 0
	var dwell_away: int = 0
	# Car-ticks a minibus was looked at for its colour, and wore the wrong one.
	var minibus_looked: int = 0
	var minibus_wrong: int = 0
	var minibus: int = system._kinds.find(MINIBUS)
	var seen: Array[Seen] = []
	for _car: TrafficSystem.Car in system.cars:
		seen.append(Seen.new())
	var ticks: int = roundi(RUN_S / TICK_S)
	var ran_red: int = 0
	var bad_move: int = 0
	var bad_way: int = 0
	var on_stub: int = 0
	var rear_end: int = 0
	var too_fast: int = 0
	var held_light: int = 0
	var held_car: int = 0
	var held_parked: int = 0
	var held_give_way: int = 0
	var give_way_wait: Array[int] = []
	var longest_give_way: int = 0
	var passing: int = 0
	var inside_parked: int = 0
	var head_on: int = 0
	var winked: int = 0
	var bad_wink: int = 0
	var held_wink: int = 0
	var bad_hold: int = 0
	var over_centre: int = 0
	var longest_wait: Array[int] = []
	var waited: Array[int] = []
	longest_wait.resize(system.cars.size())
	longest_wait.fill(0)
	waited.resize(system.cars.size())
	waited.fill(0)
	give_way_wait.resize(system.cars.size())
	give_way_wait.fill(0)
	var crossed: int = 0
	var driven_m: float = 0.0
	# Two cars in one another at a junction, by where: car-ticks then meetings.
	var crossings: Dictionary[String, Vector2i] = {
		"signalled": Vector2i.ZERO, "unsignalled": Vector2i.ZERO
	}
	var overlapping: Dictionary[int, bool] = {}
	for tick: int in ticks:
		system.signals.clock_s += TICK_S
		system.step(TICK_S)
		for index: int in system.cars.size():
			var car: TrafficSystem.Car = system.cars[index]
			var before: Seen = seen[index]
			if not car.live:
				before.live = false
				continue
			driven_m += car.speed * TICK_S
			if car.route != null:
				# Its planned move off this road is the one its goal's tree takes.
				if (
					car.goal != null
					and not car.turning
					and not system._is_goal_way(car, car.edge, car.along)
				):
					var planned: Vector2i = (
						car.via[0]
						if not car.via.is_empty()
						else Vector2i(
							car.next_edge, int(car.next_along) if car.next_edge >= 0 else 0
						)
					)
					if planned != system.router.next_toward(car.goal, car.edge, car.along):
						off_route += 1
				if car.dwell_left > 0.0:
					dwelling += 1
					if car.speed >= TrafficSystem.STOPPED_MPS:
						dwell_moving += 1
					var stop: BusRoutes.Stop = car.route.stops[car.stop_index]
					# A pole nearer the road's start than half the vehicle stands it
					# at the start: placed, not driven to.
					if (
						stop.travel_m >= car.half_length
						and (
							car.edge != stop.edge
							or car.along != stop.along
							or (
								absf(system._to_pole(car, stop))
								> system.profile.dwell_reach_m + DWELL_SLACK_M
							)
						)
					):
						dwell_away += 1
			if routed and car.kind == minibus:
				minibus_looked += 1
				var livery: PackedColorArray = (
					system.profile.route_liveries[MINIBUS]
					if car.routed
					else system.profile.wander_liveries[MINIBUS]
				)
				if not car.livery.is_equal_approx(Color(livery[0], 1.0)):
					minibus_wrong += 1
			if car.speed > car.cruise_mps + SPEED_SLACK_MPS:
				too_fast += 1
			if car.held == TrafficSystem.Held.LIGHT:
				held_light += 1
			elif car.held == TrafficSystem.Held.CAR:
				held_car += 1
			elif car.held == TrafficSystem.Held.PARKED:
				held_parked += 1
			elif car.held == TrafficSystem.Held.GIVE_WAY:
				held_give_way += 1
			give_way_wait[index] = (
				give_way_wait[index] + 1
				if car.held == TrafficSystem.Held.GIVE_WAY and car.speed < TrafficSystem.STOPPED_MPS
				else 0
			)
			longest_give_way = maxi(longest_give_way, give_way_wait[index])
			if car.passing:
				passing += 1
			if car.over_centre:
				over_centre += 1
			waited[index] = (
				waited[index] + 1
				if car.held == TrafficSystem.Held.PARKED and car.speed < TrafficSystem.STOPPED_MPS
				else 0
			)
			longest_wait[index] = maxi(longest_wait[index], waited[index])
			var inside: Node = _inside_parked(system, car)
			if inside != null:
				inside_parked += 1
				_problem(
					(
						"tick %d: car %d stands inside a parked vehicle on edge %d"
						% [tick, index, car.edge]
					)
				)
			if not system.router.admits_way(car.edge, car.along):
				bad_way += 1
				_problem(
					"tick %d: car %d drives edge %d a way it may not" % [tick, index, car.edge]
				)
			if not car.turning and system.graph.is_stub(car.edge):
				on_stub += 1
			var front: float = car.s + car.half_length
			if before.lives != car.lives:
				# Respawned this tick: a new car, nothing to compare.
				before.live = false
				before.lives = car.lives
			if before.live and (before.edge != car.edge or before.along != car.along):
				if not _legal_chain(
					system.router,
					Vector2i(before.edge, 1 if before.along else 0),
					car.crossed,
					Vector2i(car.edge, 1 if car.along else 0)
				):
					bad_move += 1
					_problem(
						(
							"tick %d: car %d moved %d -> %d, no legal arc"
							% [tick, index, before.edge, car.edge]
						)
					)
			elif before.live and not car.turning:
				var stop: float = system.stop_travel_m(car)
				if stop >= 0.0 and before.front_m < stop and front >= stop:
					crossed += 1
					var light: SignalController.Light = system.signals.state_of(car.edge, car.along)
					if (
						light == SignalController.Light.RED
						or light == SignalController.Light.RED_AMBER
					):
						ran_red += 1
						_problem(
							(
								"tick %d: car %d crossed edge %d's stop on %s at %.2f m/s"
								% [
									tick,
									index,
									car.edge,
									SignalController.Light.keys()[light],
									car.speed
								]
							)
						)
			if before.live and car.turning and not before.turning:
				# A turn is judged on its approach's last tick; straight on, as it
				# starts, since the approach may have winked for a lane change.
				var bits: int = before.written if car.turn_side != 0 else car.written
				if _winks_side(car.turn_side, bits):
					winked += absi(car.turn_side)
				else:
					bad_wink += 1
					_problem(
						(
							"tick %d: car %d turns %d with lamp bits %d"
							% [tick, index, car.turn_side, car.written]
						)
					)
			# Still winking the finished turn's side as it joins, unless the next
			# turn's approach already took the indicator over.
			if (
				before.live
				and before.turning
				and not car.turning
				and before.turn_side != 0
				and not system.approaching_turn(car)
			):
				if _winks_side(before.turn_side, car.written):
					held_wink += 1
				else:
					bad_hold += 1
					_problem(
						(
							"tick %d: car %d joined from a %d turn with lamp bits %d"
							% [tick, index, before.turn_side, car.written]
						)
					)
			before.turning = car.turning
			before.turn_side = car.turn_side
			before.written = car.written
			before.live = true
			before.edge = car.edge
			before.along = car.along
			before.front_m = front
		rear_end += _rear_ends(system)
		head_on += _head_ons(system)
		_count_crossings(system, crossings, overlapping)
	_expect(
		system.spawned > 0,
		"drive",
		"%d cars spawned, %d retired" % [system.spawned, system.retired]
	)
	_expect(driven_m > 0.0, "drive", "%.0f m driven in %.0f s" % [driven_m, RUN_S])
	_expect(
		ran_red == 0,
		"lights",
		"no stop crossed on red: %d crossings, %d on red" % [crossed, ran_red]
	)
	if at_signals:
		_expect(crossed > 0, "lights", "some car crossed a stop line at all")
		_expect(
			held_light > 0, "lights", "some car was held by a light (%d car-ticks)" % held_light
		)
	_expect(held_car > 0, "queue", "some car was held by the car ahead (%d car-ticks)" % held_car)
	_expect(
		held_give_way > 0,
		"give way",
		"some car gave way at its line (%d car-ticks)" % held_give_way
	)
	_expect(bad_move == 0 and bad_way == 0, "graph", "every move a legal arc, every way admitted")
	_expect(on_stub == 0, "graph", "no car drove a road inside a junction (%d car-ticks)" % on_stub)
	_expect(rear_end == 0, "queue", "no car stood inside the one ahead (%d car-ticks)" % rear_end)
	_expect(too_fast == 0, "speed", "no car over its cruise (%d car-ticks)" % too_fast)
	_expect(
		inside_parked == 0,
		"parked",
		"no car stood inside a parked vehicle (%d car-ticks)" % inside_parked
	)
	_expect(
		passing > 0,
		"parked",
		(
			"some car moved out to pass a parked vehicle (%d car-ticks; %d held behind one)"
			% [passing, held_parked]
		)
	)
	_expect(
		bad_wink == 0 and winked > 0,
		"wink",
		(
			"every turn winked its own side, none straight on (%d turns winked, %d wrong)"
			% [winked, bad_wink]
		)
	)
	_expect(
		bad_hold == 0 and held_wink > 0,
		"wink",
		(
			"every turn still winked its side as it joined (%d held, %d dropped)"
			% [held_wink, bad_hold]
		)
	)
	_expect(
		head_on == 0,
		"parked",
		(
			"no two cars met head on (%d car-ticks; %d out over the centre line)"
			% [head_on, over_centre]
		)
	)
	print("  parked:   the longest stand behind one %.1f s" % (longest_wait.max() * TICK_S))
	# Gated where the lights and the give-way both hold; without a light one pair
	# in seed 4 meets where two roads cross with no junction between them.
	if not routed:
		_expect(
			crossings["signalled"].x == 0,
			"give way",
			"no two cars met in a signalled junction (%d car-ticks)" % crossings["signalled"].x
		)
	else:
		_check_routed(
			system, off_route, dwelling, dwell_moving, dwell_away, minibus_looked, minibus_wrong
		)
	for where: String in crossings:
		print(
			(
				"  crossing: %-11s %d car-ticks in another car, %d meetings"
				% [where, crossings[where].x, crossings[where].y]
			)
		)
	print(
		(
			"  give way: %d car-ticks held, the longest stand %.1f s"
			% [held_give_way, longest_give_way * TICK_S]
		)
	)
	_check_near(system)
	_check_horn(system)


## A honk's pattern (`P3-79`): every draw inside its reason's ranges, a cross
## car's longer than a calm one's, and the same seed the same pattern.
func _check_horn_patterns() -> void:
	var table := load(TrafficProfile.PATH) as TrafficProfile
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	for reason: String in TrafficScript.HORN_REASONS:
		var count: Vector2i = table.horn_count[reason]
		var press: Vector2 = table.horn_press_s[reason]
		var gap: Vector2 = table.horn_gap_s[reason]
		var inside: bool = true
		var held: Array[float] = [0.0, 0.0]
		var pressed: Array[int] = [0, 0]
		for temper_at: int in 2:
			var temper: float = 0.0 if temper_at == 0 else table.horn_temper_max
			for _draw: int in 200:
				var pattern: PackedFloat32Array = TrafficScript.horn_pattern(
					table, reason, temper, rng
				)
				var presses: int = ceili(pattern.size() / 2.0)
				inside = inside and pattern.size() % 2 == 1
				inside = inside and presses >= count.x and presses <= count.y
				for at: int in pattern.size():
					var span: Vector2 = press if at % 2 == 0 else gap
					inside = (
						inside and pattern[at] >= span.x - 1e-4 and pattern[at] <= span.y + 1e-4
					)
					if at % 2 == 0:
						held[temper_at] += pattern[at]
						pressed[temper_at] += 1
		_expect(inside, "horn", "every %s pattern stays inside its ranges" % reason)
		_expect(
			held[1] / pressed[1] > held[0] / pressed[0],
			"horn",
			"a cross car leans on each press longer (%s)" % reason
		)
		_expect(pressed[1] >= pressed[0], "horn", "and presses no fewer times (%s)" % reason)
	var one := RandomNumberGenerator.new()
	var two := RandomNumberGenerator.new()
	one.seed = 9
	two.seed = 9
	_expect(
		(
			TrafficScript.horn_pattern(table, "hit", 0.3, one)
			== TrafficScript.horn_pattern(table, "hit", 0.3, two)
		),
		"horn",
		"the same seed draws the same pattern"
	)


## The horns the loop's awards draw: the car close-called, and on a docked hit the
## car with the taxi in its path or the car struck; a car's own wait does not hold
## them. `car` stands with `taxi` 6 m ahead of it.
func _check_reactions(system: TrafficSystem, car: TrafficSystem.Car, taxi: Node3D) -> void:
	# The steps before spawned new cars round the taxi, and each would answer too.
	for other: TrafficSystem.Car in system.cars:
		if other != car:
			other.live = false
	var cases: Array[Array] = [
		[Fare.Skill.CLOSE_CALL, car.obstacle, 1, "the car close-called sounds its horn"],
		[Fare.Skill.CLOSE_CALL, {}, 0, "a close call on something else does not"],
		[Fare.Skill.NEAR_MISS, car.obstacle, 0, "nor does a near miss"],
		[Fare.Skill.CRASH, {}, 1, "a crash with the taxi in its path does"],
		[Fare.Skill.BUMP, {}, 1, "and so does a collision"],
		[Fare.Skill.DRIFT, {}, 0, "a drift does not"],
	]
	var rolls: int = system._rng.state
	car.temper = 0.0
	var temper: float = car.temper
	for case: Array in cases:
		var award := Fare.Award.new(case[0], 1.0)
		award.passed = case[1]
		car.horn_wait = 99.0
		var before: int = system.horns
		system.react_to(award)
		_expect(system.horns == before + int(case[2]), "react", case[3])
	# `P3-79`: a pattern rolls on its own RNG, never the traffic's.
	_expect(system._rng.state == rolls, "react", "a honk's pattern moves no car's roll")
	_expect(car.temper > temper, "react", "a honk raises the car's temper")
	var presses: int = system.horn_presses
	for _tick: int in 400:
		system._step_horns(1.0 / 60.0)
	_expect(
		system._horn_calls.all(func(honk: Variant) -> bool: return honk == null),
		"react",
		"every pattern plays out and frees its voice (%d presses)" % (presses)
	)
	var crash := Fare.Award.new(Fare.Skill.CRASH, -5.0)
	var forward: Vector3 = -car.pose.basis.z
	taxi.global_position = car.pose.origin - forward * 20.0
	var horns: int = system.horns
	system.react_to(crash)
	_expect(system.horns == horns, "react", "a crash 20 m behind it does not")
	taxi.global_position = car.pose.origin + car.pose.basis.x * 2.5
	system.react_to(crash)
	_expect(system.horns == horns + 1, "react", "a crash into its flank does")
	# Heard off the loop's own signals, paid and practised alike.
	var loop: FareSystem = FareSystemScript.new()
	system._listen(loop)
	horns = system.horns
	loop.practised.emit(crash)
	loop.skilled.emit(null, crash)
	_expect(system.horns == horns + 2, "react", "the loop's awards reach it, empty or carrying")
	system.fares = null
	loop.free()
	taxi.global_position = car.pose.origin + forward * 6.0


func _step_for(system: TrafficSystem, seconds: float) -> void:
	for _tick: int in int(seconds / TICK_S):
		system.step(TICK_S)


## The horn (`Q178`): a car on no signal's approach, the taxi stood in front of it.
## The drive is run on until one is under way and held by nothing: at its last
## tick every such car may be slowing for a give-way.
func _check_horn(system: TrafficSystem) -> void:
	var car: TrafficSystem.Car = null
	for _searched: int in roundi(HORN_SEARCH_S / TICK_S):
		for candidate: TrafficSystem.Car in system.cars:
			if (
				candidate.live
				and not candidate.turning
				and candidate.held == TrafficSystem.Held.NONE
				and candidate.speed > 2.0
				and system.stop_travel_m(candidate) < 0.0
			):
				car = candidate
				break
		if car != null:
			break
		system.signals.clock_s += TICK_S
		system.step(TICK_S)
	if car == null:
		_expect(false, "horn", "no car under way off a signal's approach to stage the horn on")
		return
	for other: TrafficSystem.Car in system.cars:
		if other != car:
			other.live = false
	var table: TrafficProfile = system.profile
	var taxi := Node3D.new()
	root.add_child(taxi)
	system.vehicle = taxi
	# Pulled out on it at the car's own speed, close enough to be a cut-up.
	car.speed = maxf(car.speed, 10.0)
	car.horn_wait = 0.0
	var horns: int = system.horns
	taxi.global_position = car.pose.origin - car.pose.basis.z * 12.0
	system.step(TICK_S)
	_expect(car.held == TrafficSystem.Held.TAXI, "horn", "the taxi holds the car")
	_expect(system.horns == horns + 1, "horn", "cut up, it sounds its horn on the tick")
	# Stood right up behind it: a car left to brake could run on round a bend, off the
	# taxi's line (seed 23).
	car.speed = 0.0
	taxi.global_position = car.pose.origin - car.pose.basis.z * 6.0
	system.step(TICK_S)
	_expect(car.speed < TrafficSystem.STOPPED_MPS, "horn", "and stands behind the taxi")
	# The wait, from both sides: nothing short of it, the horn on it, then the repeat.
	car.horn_wait = 0.0
	car.taxi_stood_s = 0.0
	horns = system.horns
	_step_for(system, table.horn_after_s - 0.1)
	_expect(system.horns == horns, "horn", "not before horn_after_s")
	_step_for(system, 0.2)
	_expect(system.horns == horns + 1, "horn", "stood horn_after_s, it sounds")
	_step_for(system, table.horn_repeat_s - 0.1)
	_expect(system.horns == horns + 1, "horn", "not again before horn_repeat_s")
	_step_for(system, 0.2)
	_expect(system.horns == horns + 2, "horn", "and again after it")
	# Creeping up behind the taxi is not standing behind it.
	car.horn_wait = 0.0
	car.taxi_stood_s = 0.0
	horns = system.horns
	car.held = TrafficSystem.Held.TAXI
	car.speed = 1.0
	for _tick: int in int(table.horn_after_s * 2.0 / TICK_S):
		system._mind_horn(car, 1.0, false, TICK_S)
	_expect(system.horns == horns, "horn", "a car still creeping has not stood")
	car.speed = 0.0
	# A queue at a red is quiet: the wait starts when the light stops being the reason.
	car.horn_wait = 0.0
	car.taxi_stood_s = 0.0
	horns = system.horns
	car.held = TrafficSystem.Held.TAXI
	for _tick: int in int(table.horn_after_s * 2.0 / TICK_S):
		system._mind_horn(car, 0.0, true, TICK_S)
	_expect(system.horns == horns, "horn", "a car at a red with the taxi ahead stays quiet")
	for _tick: int in int((table.horn_after_s + 0.1) / TICK_S):
		system._mind_horn(car, 0.0, false, TICK_S)
	_expect(system.horns == horns + 1, "horn", "and sounds once the light has gone")
	_check_reactions(system, car, taxi)
	print("  horn: %d sounded" % system.horns)
	system.vehicle = null
	taxi.free()


## What the near miss is handed (`Q175`): a live car on its own pose with the
## velocity it really moves at, reached further by what it covers in the look,
## and no two the same id.
func _check_near(system: TrafficSystem) -> void:
	var car: TrafficSystem.Car = null
	for candidate: TrafficSystem.Car in system.cars:
		if candidate.live and not candidate.turning and candidate.speed > 2.0:
			car = candidate
			break
	if car == null:
		_expect(false, "near", "no car under way to hand the near miss")
		return
	var found: Array[Dictionary] = system.near_cars(car.pose.origin, 1.0, 0.0)
	var mine: Dictionary = {}
	for obstacle: Dictionary in found:
		if obstacle["transform"] == car.pose:
			mine = obstacle
	_expect(not mine.is_empty(), "near", "a live car is handed in on its own pose")
	if mine.is_empty():
		return
	# The earlier runs' fleets stand until the frame ends: the first run's is the
	# one the group answers with.
	if get_first_node_in_group(TrafficSystem.GROUP) == system:
		_expect(
			FareSystem.obstacles_near(self, car.pose.origin, 1.0, 0.0).has(mine),
			"near",
			"FareSystem finds it by the group, beside the parked ones"
		)
	var off := Vector3(car.speed * 2.0 + 4.0, 0.0, 0.0)
	var reached: bool = system.near_cars(car.pose.origin + off, 5.0, 2.0).has(mine)
	var short: bool = system.near_cars(car.pose.origin + off, 5.0, 0.0).has(mine)
	_expect(reached and not short, "near", "the look widens the disc by what the car covers")
	var ids: Dictionary[int, bool] = {}
	for obstacle: Dictionary in system.near_cars(car.pose.origin, 1e6, 0.0):
		ids[int(obstacle["id"])] = true
	_expect(
		ids.size() == system.near_cars(car.pose.origin, 1e6, 0.0).size(),
		"near",
		"no two cars share an id (%d live)" % ids.size()
	)
	var velocity: Vector3 = mine["velocity"]
	var was: Vector3 = car.pose.origin
	var speed: float = car.speed
	system.step(TICK_S)
	var moved: Vector3 = car.pose.origin - was
	_expect(
		moved.dot(velocity) > 0.0 and is_equal_approx(velocity.length(), speed),
		"near",
		"its velocity is the way it moves, at its speed (%.1f m/s)" % speed
	)


## The parked vehicle standing on `car`'s road or the road its turn joins whose
## plan box `car`'s overlaps by more than `INSIDE_M`, or null.
func _inside_parked(system: TrafficSystem, car: TrafficSystem.Car) -> Node:
	var extent: AABB = system.extent_of(car)
	var mine: Array[Vector2] = _plan_box(car.pose, extent)
	for edge: int in [car.edge, car.next_edge]:
		for parked: TrafficSystem.Parked in system.parked_on(edge):
			if not parked.standing():
				continue
			var obstacle: Dictionary = parked.layer.obstacle_of(parked.index)
			var theirs: Array[Vector2] = _plan_box(obstacle["transform"], obstacle["extent"])
			if _overlap(mine, theirs) > INSIDE_M:
				return parked.layer
	return null


## Whether lamp `bits` show a turn's indicator (`side` 1 left, -1 right) and not
## the other — or neither for straight on.
static func _winks_side(side: int, bits: int) -> bool:
	var left: bool = bits & TrafficSystem.LAMP_LEFT != 0
	var right: bool = bits & TrafficSystem.LAMP_RIGHT != 0
	match side:
		1:
			return left and not right
		-1:
			return right and not left
	return not left and not right


## Pairs of cars on one edge, opposite ways, off the turn, whose plan boxes
## overlap.
static func _head_ons(system: TrafficSystem) -> int:
	var found: int = 0
	var live: Array[TrafficSystem.Car] = []
	for car: TrafficSystem.Car in system.cars:
		if car.live and not car.turning:
			live.append(car)
	for a: int in live.size():
		for b: int in range(a + 1, live.size()):
			var one: TrafficSystem.Car = live[a]
			var two: TrafficSystem.Car = live[b]
			if one.edge != two.edge or one.along == two.along:
				continue
			var mine: Array[Vector2] = _plan_box(one.pose, system.extent_of(one))
			var theirs: Array[Vector2] = _plan_box(two.pose, system.extent_of(two))
			if _overlap(mine, theirs) > INSIDE_M:
				found += 1
	return found


## Pairs of live cars on one level, one at least in its turn, whose plan boxes
## overlap — two cars in one another in a junction — into `found` by whether either turns off
## a signalled approach: `x` car-ticks, `y` meetings (a pair's first tick in).
## `overlapping` carries the pairs in one another between ticks.
static func _count_crossings(
	system: TrafficSystem, found: Dictionary[String, Vector2i], overlapping: Dictionary[int, bool]
) -> void:
	var now: Dictionary[int, bool] = {}
	var cars: Array[TrafficSystem.Car] = system.cars
	for a: int in cars.size():
		var one: TrafficSystem.Car = cars[a]
		if not one.live:
			continue
		var mine: Array[Vector2] = _plan_box(one.pose, system.extent_of(one))
		for b: int in range(a + 1, cars.size()):
			var two: TrafficSystem.Car = cars[b]
			if not two.live or not (one.turning or two.turning):
				continue
			# One on a deck over the other is not a meeting (seeds 4 and 7, Wan Chai alone).
			if absf(one.pose.origin.y - two.pose.origin.y) > TrafficSystem.LEVEL_APART_M:
				continue
			var theirs: Array[Vector2] = _plan_box(two.pose, system.extent_of(two))
			if _overlap(mine, theirs) <= INSIDE_M:
				continue
			var signalled: bool = false
			for car: TrafficSystem.Car in [one, two]:
				if car.turning and system.stop_travel_m(car) >= 0.0:
					signalled = true
			var where: String = "signalled" if signalled else "unsignalled"
			var key: int = a * cars.size() + b
			now[key] = true
			found[where] += Vector2i(1, 0 if overlapping.has(key) else 1)
	overlapping.assign(now)


## The routed fleet's own checks, after a drive with it (`P3-78`).
func _check_routed(
	system: TrafficSystem,
	off_route: int,
	dwelling: int,
	dwell_moving: int,
	dwell_away: int,
	minibus_looked: int,
	minibus_wrong: int,
) -> void:
	print(
		(
			"  route: %d routes resident, %d placed; stops %d served, %d driven past, %d unreachable"
			% [
				system.bus_routes.routes.size(),
				system.routed_spawned,
				system.stops_served,
				system.stops_missed,
				system.stops_unreachable,
			]
		)
	)
	_expect(system.routed_spawned > 0, "route", "the routed fleet was placed on its routes")
	_expect(system.stops_served > 0, "route", "some routed vehicle drove to its stop and stood")
	_expect(
		off_route == 0,
		"route",
		"a routed vehicle plans the move its stop's search takes (%d car-ticks off)" % off_route
	)
	_expect(
		dwelling > 0 and dwell_moving == 0,
		"route",
		(
			"a dwelling vehicle stands still (%d car-ticks dwelling, %d moving)"
			% [dwelling, dwell_moving]
		)
	)
	_expect(
		dwell_away == 0,
		"route",
		(
			"a dwelling vehicle stands with its front at its stop's pole (%d car-ticks away)"
			% dwell_away
		)
	)
	# Every tick of the drive, not its last: the census draws a wandering minibus
	# rarely (`Q186`), so one may not be standing when the drive ends.
	_expect(
		minibus_looked > 0 and minibus_wrong == 0,
		"route",
		(
			"a routed minibus wears green and a wandering one red (%d car-ticks, %d wrong)"
			% [minibus_looked, minibus_wrong]
		)
	)


## A box's plan rectangle: its centre, then its two half-axes.
static func _plan_box(at: Transform3D, extent: AABB) -> Array[Vector2]:
	var centre: Vector3 = at * extent.get_center()
	var x: Vector3 = at.basis.x * extent.size.x * 0.5
	var z: Vector3 = at.basis.z * extent.size.z * 0.5
	return [Vector2(centre.x, centre.z), Vector2(x.x, x.z), Vector2(z.x, z.z)]


## How far two plan rectangles interpenetrate along their least-separating
## axis (separating axes), or a negative number where they are apart.
static func _overlap(a: Array[Vector2], b: Array[Vector2]) -> float:
	var least: float = INF
	for axis: Vector2 in [a[1], a[2], b[1], b[2]]:
		var unit: Vector2 = axis.normalized()
		var reach_a: float = absf(a[1].dot(unit)) + absf(a[2].dot(unit))
		var reach_b: float = absf(b[1].dot(unit)) + absf(b[2].dot(unit))
		var apart: float = absf((b[0] - a[0]).dot(unit))
		least = minf(least, reach_a + reach_b - apart)
	return least


## Whether `from`, through each of `via` in turn, to `to` is a chain of legal
## arcs.
static func _legal_chain(
	router: RoadRouter, from: Vector2i, via: Array[Vector2i], to: Vector2i
) -> bool:
	var here: Vector2i = from
	for step: Vector2i in via + [to]:
		if not router.moves_from(here.x, here.y == 1).has(step):
			return false
		here = step
	return true


## Pairs of cars on one edge one way, off the turn, closer than their
## half-lengths.
static func _rear_ends(system: TrafficSystem) -> int:
	var found: int = 0
	var live: Array[TrafficSystem.Car] = []
	for car: TrafficSystem.Car in system.cars:
		if car.live and not car.turning:
			live.append(car)
	for a: int in live.size():
		for b: int in range(a + 1, live.size()):
			var one: TrafficSystem.Car = live[a]
			var two: TrafficSystem.Car = live[b]
			if one.edge != two.edge or one.along != two.along:
				continue
			if not TrafficSystem.same_lane(one.lane, two.lane):
				continue
			if absf(one.s - two.s) < one.half_length + two.half_length:
				found += 1
	return found


## `lane_at` against `nearest_edge`'s lane centre at each edge's middle, both
## ways on a two-way edge. Where the query resolves another edge (a junction's
## stub nearer the point), the edge is skipped and not counted.
func _check_lane(graph: RoadGraph) -> void:
	var compared: int = 0
	var worst: float = 0.0
	for edge: int in graph.edge_ids():
		var length: float = graph.plan_length_of(edge)
		if length <= 0.0 or not graph.is_drivable(edge):
			continue
		var a: Vector3 = graph.point_at(edge, 0.49)
		var b: Vector3 = graph.point_at(edge, 0.51)
		var middle: Vector3 = graph.point_at(edge, 0.5)
		for along: bool in [true, false]:
			if not along and graph.is_one_way(edge):
				continue
			var hit: RoadGraph.Hit = graph.nearest_edge(
				middle, (b - a) * (1.0 if along else -1.0), 5.0
			)
			if hit.edge_id != edge or hit.along != along:
				continue
			var placed: Vector3 = graph.lane_at(edge, length * hit.t, along)
			worst = maxf(worst, RoadGraph.plan_distance(placed, hit.lane_centre))
			compared += 1
	_expect(
		compared > 0 and worst < 0.01,
		"lane",
		"lane_at agrees with Hit.lane_centre on %d ways, worst %.4f m" % [compared, worst]
	)
