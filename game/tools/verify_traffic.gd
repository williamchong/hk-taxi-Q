## The traffic (`P3-3c`, `Q173`), headless: the fleet driven for `RUN_S` with
## no player, the ring centred on the signalled junctions, every tick checked.
##
## - 🔴 **No car crosses its stop point on red or red-and-amber.** The front
##   bumper's travel past the stop is watched tick by tick; a crossing while
##   the light shows either fails by name. Amber may be crossed: a car that
##   could not stop goes through.
## - 🔴 **Every move is a legal arc**: each change of edge is one of
##   `RoadRouter.moves_from` from the edge left, and every way driven is one the
##   legal profile admits.
## - **No car runs into the one ahead in its own lane**: two cars on one edge,
##   one way, off the turn, never stand closer than their half-lengths.
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

const TICK_S: float = 1.0 / 60.0
const RUN_S: float = 90.0
const SPEED_SLACK_MPS: float = 1e-3
## Three fleets, each its own rolls. 4 is the seed that found the car creeping
## over the line at amber behind a slow leader (2026-10-29); 7 and 23 two more.
const SEEDS: Array[int] = [7, 4, 23]


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
	for seed: int in SEEDS:
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
		print("  seed %d:" % seed)
		system.centre = _signal_centre(system.signals.plan)
		_drive(system)
		system.queue_free()
	_finish("verify_traffic")


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


func _drive(system: TrafficSystem) -> void:
	var seen: Array[Seen] = []
	for _car: TrafficSystem.Car in system.cars:
		seen.append(Seen.new())
	var ticks: int = roundi(RUN_S / TICK_S)
	var ran_red: int = 0
	var bad_move: int = 0
	var bad_way: int = 0
	var rear_end: int = 0
	var too_fast: int = 0
	var held_light: int = 0
	var held_car: int = 0
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
			if not system.router.admits_way(car.edge, car.along):
				bad_way += 1
				_problem(
					"tick %d: car %d drives edge %d a way it may not" % [tick, index, car.edge]
				)
			var front: float = car.s + car.half_length
			if before.lives != car.lives:
				# Respawned this tick: a new car, nothing to compare.
				before.live = false
				before.lives = car.lives
			if before.live and (before.edge != car.edge or before.along != car.along):
				if not system.router.moves_from(before.edge, before.along).has(
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
			before.live = true
			before.edge = car.edge
			before.along = car.along
			before.front_m = front
		rear_end += _rear_ends(system)
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
	_expect(crossed > 0, "lights", "some car crossed a stop line at all")
	_expect(held_light > 0, "lights", "some car was held by a light (%d car-ticks)" % held_light)
	_expect(held_car > 0, "queue", "some car was held by the car ahead (%d car-ticks)" % held_car)
	_expect(bad_move == 0 and bad_way == 0, "graph", "every move a legal arc, every way admitted")
	_expect(rear_end == 0, "queue", "no car stood inside the one ahead (%d car-ticks)" % rear_end)
	_expect(too_fast == 0, "speed", "no car over its cruise (%d car-ticks)" % too_fast)


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
