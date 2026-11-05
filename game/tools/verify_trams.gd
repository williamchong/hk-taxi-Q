## The trams (`P3-4`, `Q176`), headless: the fleet run for `RUN_S` on every resident
## region's lines, with the plan's lights on, every tick checked.
##
## - 🔴 **The lines join**: every track a route reaches, both ways across the seam
##   where two regions are resident, no stop line on an edge the graph lost.
## - 🔴 **No tram passes a stop line on red or red-and-amber.** Its front's travel past
##   the line is watched tick by tick. Amber may be passed.
## - 🔴 **A tram stops at every stop it reaches**, with its doors open `dwell_s`,
##   winking left while it stands there (`Q187`).
## - 🔴 **No tram runs backwards or jumps**: its body moves forwards, no further each
##   tick than its speed takes it, across every bed's gap and across the seam.
## - **No tram stands inside another** on one route.
## - **The taxi is stopped for, and rung at**, and a tram clear of it runs on.
## - **A car behind a tram waits** and `near_cars` hands the trams to the near miss; a
##   car knocked across the rails holds a tram whatever its heading (`Q180`).
## - 🔴 **The taxi pushes a tram along its rails, never off them** (`Q180`): it gives
##   along its travel alone, by its mass; a push across the rails moves nothing; pushed
##   on or back it stays on its route, brakes to rest at `brake_max_mps2` and runs on.
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
## A rail bends; a join onto the other track, running the other way, turns this far.
const DOUBLES_BACK_DEG: float = 120.0
const TURN_SPAN_M: float = 5.0
## A knocked car stood across the rails this far down them from a tram's middle.
const KNOCKED_AHEAD_M: float = 20.0


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
	_check_push(lines, table)
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
	var worst_turn: float = 0.0
	for route: TramLines.Route in lines.routes:
		worst_turn = maxf(worst_turn, _worst_turn_deg(route))
	_expect(
		worst_turn < DOUBLES_BACK_DEG,
		"lines",
		"no route doubles back (worst %.0f deg)" % worst_turn
	)
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
	# Tram-ticks at a stop winking left alone, and not.
	var stop_wink: Vector2i = Vector2i.ZERO
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
			if tram.live and tram.dwell_left > 0.0:
				var left: bool = tram.written & TrafficSystem.LAMP_LEFT != 0
				var right: bool = tram.written & TrafficSystem.LAMP_RIGHT != 0
				if left and not right:
					stop_wink.x += 1
				else:
					stop_wink.y += 1
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
	_expect(
		stop_wink.x > 0 and stop_wink.y == 0,
		"stops",
		"a tram at its stop winks left (%d tram-ticks, %d wrong)" % [stop_wink.x, stop_wink.y]
	)
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


## One tram pushed by hand (`Q180`): along its rails, across them, and back.
func _check_push(lines: TramLines, table: TramProfile) -> void:
	var system: TramSystem = TramSystem.new()
	system.setup(lines, table, 1)
	root.add_child(system)
	var tram: TramSystem.Tram = system.trams[0]
	system.trams.resize(1)
	var route: TramLines.Route = _longest(lines)
	tram.route = route
	tram.s = route.length_m() * 0.5
	tram.next_stop = route.stops.size()
	tram.next_line = route.lines.size()
	tram.speed = table.cruise_mps
	tram.dwell_left = 0.0
	tram.live = true
	tram.pose = system._pose_at(route, tram.s)
	system.step(TICK_S)
	_expect(tram.mass_kg > 0.0, "push", "the tram carries a kerb mass (%.0f kg)" % tram.mass_kg)
	_expect(tram.body.has_meta(Pushable.OWNER_META), "push", "and its body is the taxi's to push")
	var rails: Vector3 = -tram.pose.basis.z
	var across := Vector3(-rails.z, 0.0, rails.x)
	_expect(
		is_zero_approx(system.push_inverse_mass(tram.body, across, tram.pose.origin)),
		"push",
		"square across its rails it does not give"
	)
	_expect(
		is_equal_approx(
			system.push_inverse_mass(tram.body, rails, tram.pose.origin), 1.0 / tram.mass_kg
		),
		"push",
		"along them it gives as its mass"
	)
	var origin: Vector3 = tram.pose.origin
	var before: float = tram.speed
	system.take_push(tram.body, across * 20000.0, origin)
	_expect(is_equal_approx(tram.speed, before), "push", "a push across the rails moves nothing")
	# Head on, hard: 3 m/s back past rest.
	var back: float = (before + 3.0) * tram.mass_kg
	system.take_push(tram.body, -rails * back, origin)
	_expect(is_equal_approx(tram.speed, -3.0), "push", "a push down the rails is its speed's")
	var least_s: float = tram.s
	var off_rails: float = 0.0
	var rested: bool = false
	for _tick: int in int(STAGED_S / TICK_S):
		system.step(TICK_S)
		least_s = minf(least_s, tram.s)
		var on: Vector3 = route.at(tram.s)
		off_rails = maxf(
			off_rails, Vector2(on.x - tram.pose.origin.x, on.z - tram.pose.origin.z).length()
		)
		rested = rested or is_zero_approx(tram.speed)
	_expect(least_s < route.length_m() * 0.5, "push", "pushed back, it rolls back")
	_expect(rested, "push", "and brakes to rest")
	_expect(tram.speed > 0.0, "push", "then runs on (%.1f m/s)" % tram.speed)
	_expect(
		off_rails < table.bogie_m,
		"push",
		"never further off its rails than its bogies sit (%.2f m)" % off_rails
	)
	_expect(system.pushes == 2, "push", "both pushes counted (%d)" % system.pushes)
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
	# A car knocked across the rails ahead (`Q180`) is in a tram's way at any heading.
	tram.live = true
	system._traffic = traffic
	car.live = true
	car.knocked = true
	car.pose = Transform3D(
		tram.pose.basis.rotated(Vector3.UP, PI * 0.5),
		tram.pose.origin - tram.pose.basis.z * KNOCKED_AHEAD_M
	)
	tram.held = TramSystem.Held.NONE
	_expect(
		(
			system._follow(tram, table.cruise_mps) < table.cruise_mps
			and tram.held == TramSystem.Held.CAR
		),
		"cars",
		"a car knocked across its rails ahead holds a tram"
	)
	traffic.free()
	system.free()


static func _longest(lines: TramLines) -> TramLines.Route:
	var best: TramLines.Route = lines.routes[0]
	for route: TramLines.Route in lines.routes:
		if route.length_m() > best.length_m():
			best = route
	return best


## The sharpest turn between a route's steps, over `TURN_SPAN_M` so a digitising jitter
## between two close stations does not read as one.
static func _worst_turn_deg(route: TramLines.Route) -> float:
	var worst: float = 0.0
	var s_m: float = TURN_SPAN_M
	while s_m < route.length_m() - TURN_SPAN_M:
		var here: Vector3 = route.at(s_m)
		var before: Vector3 = here - route.at(s_m - TURN_SPAN_M)
		var after: Vector3 = route.at(s_m + TURN_SPAN_M) - here
		var turn: float = Vector2(before.x, before.z).angle_to(Vector2(after.x, after.z))
		worst = maxf(worst, rad_to_deg(absf(turn)))
		s_m += TURN_SPAN_M
	return worst
