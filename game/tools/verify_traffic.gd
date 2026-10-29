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
##   and not the other, and a straight-on move carries neither as it starts.
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


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_traffic", 240.0)


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
	# The three fleets round the signals, then the first again on the back
	# streets, where a car can only pass a parked one over the centre line.
	for run: int in SEEDS.size() + 1:
		var seed: int = SEEDS[run % SEEDS.size()]
		var back_street: bool = run == SEEDS.size()
		var system: TrafficSystem = TrafficScript.new()
		if not system.setup(graph, table, seed):
			_fail("setup", "the shipped table and city carry no traffic")
			system.free()
			break
		root.add_child(system)
		if system.signals == null or system.signals.plan.is_empty():
			_fail("setup", "no signal plan resident; the stop check would read nothing")
			system.queue_free()
			break
		print("  seed %d%s:" % [seed, " on the back streets" if back_street else ""])
		system.read_parked(layers)
		if run == 0:
			_print_parked(system)
		system.centre = (
			_back_street_centre(system) if back_street else _signal_centre(system.signals.plan)
		)
		if back_street:
			_check_give_way(system)
		_drive(system, not back_street)
		system.queue_free()
	_finish("verify_traffic")


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
	system._enter(car)
	car.pose = system._pose_on_edge(car)


## Drive `system` for `RUN_S`, every check on every tick; `at_signals` adds the
## checks that the lights were met at all.
func _drive(system: TrafficSystem, at_signals: bool) -> void:
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
	var passing: int = 0
	var inside_parked: int = 0
	var head_on: int = 0
	var winked: int = 0
	var bad_wink: int = 0
	var over_centre: int = 0
	var longest_wait: Array[int] = []
	var waited: Array[int] = []
	longest_wait.resize(system.cars.size())
	longest_wait.fill(0)
	waited.resize(system.cars.size())
	waited.fill(0)
	var crossed: int = 0
	var driven_m: float = 0.0
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
			if car.speed > car.cruise_mps + SPEED_SLACK_MPS:
				too_fast += 1
			if car.held == TrafficSystem.Held.LIGHT:
				held_light += 1
			elif car.held == TrafficSystem.Held.CAR:
				held_car += 1
			elif car.held == TrafficSystem.Held.PARKED:
				held_parked += 1
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
			before.turning = car.turning
			before.written = car.written
			before.live = true
			before.edge = car.edge
			before.along = car.along
			before.front_m = front
		rear_end += _rear_ends(system)
		head_on += _head_ons(system)
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
		head_on == 0,
		"parked",
		(
			"no two cars met head on (%d car-ticks; %d out over the centre line)"
			% [head_on, over_centre]
		)
	)
	print("  parked:   the longest stand behind one %.1f s" % (longest_wait.max() * TICK_S))


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
