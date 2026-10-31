## The trams (`P3-4`, `Q176`), headless: the fleet run for `RUN_S` on every resident
## region's lines, with the plan's lights on, every tick checked.
##
## - 🔴 **The lines join**: every track a route reaches, both ways across the seam
##   where two regions are resident, no stop line on an edge the graph lost.
## - 🔴 **No tram passes a stop line on red or red-and-amber.** Its front's travel past
##   the line is watched tick by tick. Amber may be passed.
## - 🔴 **A tram stops at every stop it reaches**, with its doors open `dwell_s`.
## - 🔴 **No tram runs backwards or jumps**: its body moves forwards, no further each
##   tick than its speed takes it, across every bed's gap and across the seam.
## - **No tram stands inside another** on one route.
## - **The taxi is stopped for, and rung at**, and a tram clear of it runs on.
## - **A car behind a tram waits** and `near_cars` hands the trams to the near miss.
## - **Something happened**: trams moved, some were held by a light and some left.
##
##     godot --headless --path game --script res://tools/verify_trams.gd
extends "res://tools/verify_tool.gd"

const PlanScript = preload("res://scripts/traffic/signal_plan.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

const TICK_S: float = 1.0 / 60.0
const RUN_S: float = 240.0
const SEEDS: Array[int] = [7, 4]
## A heading snap or a float: over this in a tick is a jump.
const JUMP_SLACK_M: float = 0.02
## Beyond a tram's middle, how far to stand the taxi.
const TAXI_AHEAD_M: float = 20.0
const STAGED_S: float = 12.0


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_trams", 240.0)


func _run() -> void:
	var table := load(TramProfile.PATH) as TramProfile
	_expect(table != null and TramSystem.usable(table), "table", "%s runs" % TramProfile.PATH)
	var graph: RoadGraph = RoadGraph.shared()
	if table == null or graph.is_empty():
		_finish("verify_trams")
		return
	var lines: TramLines = TramLines.resident(graph, table)
	if lines.is_empty():
		print("  no tram line resident; nothing to run")
		_finish("verify_trams")
		return
	_check_lines(lines)
	var controller: SignalController = SignalController.create(
		PlanScript.resident(graph), load(SignalPlanProfile.PATH) as SignalPlanProfile
	)
	root.add_child(controller)
	for rolls: int in SEEDS:
		print("  seed %d:" % rolls)
		_drive(lines, table, controller, rolls)
	_check_taxi(lines, table)
	_check_cars_wait(graph, lines, table)
	controller.queue_free()
	_finish("verify_trams")


func _check_lines(lines: TramLines) -> void:
	var longest: float = 0.0
	var regions: Dictionary[String, bool] = {}
	var total_stops: int = 0
	var total_lines: int = 0
	for route: TramLines.Route in lines.routes:
		longest = maxf(longest, route.length_m())
		total_stops += route.stops.size()
		total_lines += route.lines.size()
		for region: String in route.regions:
			regions[region] = true
	print(
		(
			"  lines: %d routes, longest %.0f m, %d stops and %d stop lines on them, %d seam joins"
			% [lines.routes.size(), longest, total_stops, total_lines, lines.seam_joins]
		)
	)
	_expect(lines.unreached == 0, "lines", "every track is on a route (%d not)" % lines.unreached)
	_expect(lines.lines_dropped == 0, "lines", "every stop line's edge is in the graph")
	_expect(total_stops > 0, "lines", "routes carry stops")
	_expect(total_lines > 0, "lines", "routes carry stop lines")
	var resident: int = GeneratedRegions.resident().size()
	if resident > 1:
		_expect(lines.seam_joins >= 2, "seam", "both tracks cross the seam")
		var through: int = 0
		for route: TramLines.Route in lines.routes:
			through += int(route.regions.size() > 1)
		_expect(through > 0, "seam", "%d routes run through both regions" % through)


func _drive(lines: TramLines, table: TramProfile, controller: SignalController, rolls: int) -> void:
	var system: TramSystem = TramSystem.new()
	if not system.setup(lines, table, rolls):
		_fail("setup", "the shipped table and lines carry no tram")
		system.free()
		return
	system.signals = controller
	root.add_child(system)
	var ticks: int = int(RUN_S / TICK_S)
	var moved_m: float = 0.0
	var ran_red: int = 0
	var crossed: int = 0
	var backward: int = 0
	var jumped: int = 0
	var worst_jump: float = 0.0
	var skipped_stop: int = 0
	var dwelled: int = 0
	var inside: int = 0
	var too_fast: int = 0
	var held: Dictionary[int, int] = {}
	var last_s: Array[float] = []
	var last_route: Array[TramLines.Route] = []
	var last_at: Array[Vector3] = []
	var last_stop: Array[int] = []
	var last_dwell: Array[float] = []
	for tram: TramSystem.Tram in system.trams:
		last_s.append(tram.s)
		last_route.append(tram.route)
		last_at.append(tram.pose.origin)
		last_stop.append(tram.next_stop)
		last_dwell.append(tram.dwell_left)
	for _tick: int in ticks:
		var lights: Dictionary[TramSystem.Tram, Array] = {}
		for tram: TramSystem.Tram in system.trams:
			if tram.live:
				lights[tram] = _red_lines(tram, controller)
		controller.clock_s += TICK_S
		system.step(TICK_S)
		for tram: TramSystem.Tram in system.trams:
			var row: int = tram.id
			var same: bool = tram.live and tram.route == last_route[row]
			if same and last_s[row] <= tram.s:
				var step_m: float = tram.s - last_s[row]
				moved_m += step_m
				var plan: float = RoadGraph.plan_distance(last_at[row], tram.pose.origin)
				worst_jump = maxf(worst_jump, plan - step_m)
				if plan > step_m + JUMP_SLACK_M + step_m * 0.5:
					jumped += 1
				for line: TramLines.Line in lights.get(tram, []):
					var front: float = tram.s + system.half_length
					if line.s_m <= front and line.s_m > last_s[row] + system.half_length:
						ran_red += 1
			elif same:
				backward += 1
			if same:
				var passed: int = tram.next_stop - last_stop[row]
				if passed > 0:
					if last_dwell[row] > 0.0:
						dwelled += passed
					else:
						skipped_stop += passed
				if tram.speed > table.cruise_mps + 1e-3:
					too_fast += 1
				for line: TramLines.Line in tram.route.lines:
					if (
						line.s_m > last_s[row] + system.half_length
						and line.s_m <= tram.s + system.half_length
					):
						crossed += 1
			if tram.live:
				held[tram.held] = held.get(tram.held, 0) + 1
				last_s[row] = tram.s
				last_route[row] = tram.route
				last_at[row] = tram.pose.origin
				last_stop[row] = tram.next_stop
				last_dwell[row] = tram.dwell_left
			else:
				last_route[row] = null
		inside += _overlaps(system)
	_expect(
		moved_m > 0.0,
		"run",
		"%.0f m run, %d set out, %d left" % [moved_m, system.set_out, system.left]
	)
	_expect(system.left > 0, "run", "some tram reached the end of its line")
	_expect(
		ran_red == 0,
		"lights",
		"no stop line passed on red: %d passed, %d on red" % [crossed, ran_red]
	)
	_expect(crossed > 0, "lights", "some tram passed a stop line at all")
	_expect(
		held.get(TramSystem.Held.LIGHT, 0) > 0,
		"lights",
		"some tram was held by a light (%d tram-ticks)" % held.get(TramSystem.Held.LIGHT, 0)
	)
	_expect(
		skipped_stop == 0,
		"stops",
		"every stop dwelt at: %d dwelt, %d skipped" % [dwelled, skipped_stop]
	)
	_expect(dwelled > 0, "stops", "some tram stopped at a stop")
	_expect(backward == 0, "path", "no tram ran backwards (%d tram-ticks)" % backward)
	_expect(jumped == 0, "path", "no tram jumped: worst %.3f m over its travel" % worst_jump)
	_expect(too_fast == 0, "speed", "no tram over its cruise (%d tram-ticks)" % too_fast)
	_expect(inside == 0, "queue", "no tram stood inside another (%d tram-ticks)" % inside)
	_expect(
		held.get(TramSystem.Held.TRAM, 0) > 0,
		"queue",
		"some tram was held by the one ahead (%d tram-ticks)" % held.get(TramSystem.Held.TRAM, 0)
	)
	_expect(system.rings > 0, "bell", "the bell rang %d times" % system.rings)
	system.free()


## The tram's next lines that now show red or red-and-amber.
func _red_lines(tram: TramSystem.Tram, controller: SignalController) -> Array[TramLines.Line]:
	var found: Array[TramLines.Line] = []
	for row: int in range(tram.next_line, mini(tram.next_line + 2, tram.route.lines.size())):
		var line: TramLines.Line = tram.route.lines[row]
		var light: SignalController.Light = controller.state_of(line.edge, line.along)
		if light == SignalController.Light.RED or light == SignalController.Light.RED_AMBER:
			found.append(line)
	return found


func _overlaps(system: TramSystem) -> int:
	var found: int = 0
	var trams: Array[TramSystem.Tram] = system.trams
	for a: int in trams.size():
		if not trams[a].live:
			continue
		for b: int in range(a + 1, trams.size()):
			if not trams[b].live or trams[a].route != trams[b].route:
				continue
			if absf(trams[a].s - trams[b].s) < system.half_length * 2.0:
				found += 1
	return found


## A taxi stood on the line ahead of one tram: it stops short, rings, and runs on once
## the taxi is gone.
func _check_taxi(lines: TramLines, table: TramProfile) -> void:
	var system: TramSystem = TramSystem.new()
	system.setup(lines, table, 1)
	var taxi := Node3D.new()
	root.add_child(taxi)
	system.vehicle = taxi
	root.add_child(system)
	var tram: TramSystem.Tram = system.trams[0]
	for other: TramSystem.Tram in system.trams:
		if other != tram:
			other.live = false
	var route: TramLines.Route = _longest(lines)
	tram.route = route
	tram.s = route.length_m() * 0.5
	tram.next_stop = route.stops.size()
	tram.next_line = route.lines.size()
	tram.speed = table.cruise_mps
	var clear_of: float = tram.s + TAXI_AHEAD_M
	taxi.global_position = route.at(clear_of)
	var closest: float = INF
	var rings_before: int = system.rings
	# The rest back off: this is one tram and one taxi.
	system.trams.resize(1)
	for _tick: int in int(STAGED_S * 2.0 / TICK_S):
		system.step(TICK_S)
		closest = minf(closest, clear_of - tram.s)
	_expect(
		closest > system.half_length + table.taxi_half_m,
		"taxi",
		"a tram stops short of the taxi (%.1f m centre to centre)" % closest
	)
	_expect(tram.speed < TramSystem.STOPPED_MPS, "taxi", "and stands")
	_expect(tram.held == TramSystem.Held.TAXI, "taxi", "held by the taxi")
	_expect(
		system.rings > rings_before,
		"bell",
		"it rings at the taxi (%d)" % (system.rings - rings_before)
	)
	var at: float = tram.s
	taxi.global_position = Vector3(0.0, -1000.0, 0.0)
	for _tick: int in int(4.0 / TICK_S):
		system.step(TICK_S)
	_expect(tram.s > at + 1.0, "taxi", "and runs on once the taxi has gone")
	var near: Array[Dictionary] = system.near_cars(tram.pose.origin, 5.0, 1.0)
	_expect(near.size() == 1, "near", "near_cars hands the tram to the near miss")
	_expect(near.size() == 1 and near[0]["extent"].size.z > 8.0, "near", "at the tram's own length")
	var seen: Array[Dictionary] = FareSystem.obstacles_near(self, tram.pose.origin, 5.0, 1.0)
	_expect(not seen.is_empty(), "near", "FareSystem finds it by the group")
	var velocity: Vector3 = Vector3.ZERO if near.is_empty() else near[0]["velocity"]
	_expect(
		is_equal_approx(velocity.length(), tram.speed),
		"near",
		"its velocity at its speed (%.1f m/s)" % velocity.length()
	)
	taxi.free()
	system.free()


## A car stood behind a tram at its stop waits; a tram gone frees it.
func _check_cars_wait(graph: RoadGraph, lines: TramLines, table: TramProfile) -> void:
	var traffic_table := load(TrafficProfile.PATH) as TrafficProfile
	var traffic: TrafficSystem = TrafficSystem.new()
	if not traffic.setup(graph, traffic_table, 1):
		traffic.free()
		_fail("cars", "no traffic to stand behind a tram")
		return
	var system: TramSystem = TramSystem.new()
	system.setup(lines, table, 1)
	root.add_child(traffic)
	root.add_child(system)
	traffic.trams = system
	var tram: TramSystem.Tram = system.trams[0]
	var car: TrafficSystem.Car = traffic.cars[0]
	car.pose = Transform3D(tram.pose.basis, tram.pose.origin + tram.pose.basis.z * 15.0)
	var gap: float = traffic._gap_ahead(car)
	var expected: float = 15.0 - car.half_length - system.half_length
	_expect(
		absf(gap - expected) < 0.01, "cars", "a car behind a tram reads it ahead (%.1f m)" % gap
	)
	var other: bool = tram.live
	tram.live = false
	_expect(other and traffic._gap_ahead(car) > gap, "cars", "and not once it has gone")
	traffic.free()
	system.free()


static func _longest(lines: TramLines) -> TramLines.Route:
	var best: TramLines.Route = lines.routes[0]
	for route: TramLines.Route in lines.routes:
		if route.length_m() > best.length_m():
			best = route
	return best
