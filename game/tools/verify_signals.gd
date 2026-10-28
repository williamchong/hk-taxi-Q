## The signal plan and its controller (`P3-3a`, `P3-3b`, `Q173`), headless.
##
## - 🔴 **No two approaches on crossing axes are ever lit together.** Every
##   junction is walked over its whole cycle at `STEP_S`; two approaches showing
##   anything but red at once must lie within `CONFLICT_DEG` of one axis. The
##   checker itself is graded first, on a junction built to fail it — a check
##   that cannot fail is `Q72`'s tautology.
## - Every approach gets a green each cycle, and its lights run red, red and
##   amber, green, amber, red in that order and no other.
## - A crossing holds every approach red for `crossing_s`.
## - **The player's red** (`P3-3d`): a stop line is crossed only its way of
##   travel, within the street, on its own level; the taxi crossing one at red
##   or red-and-amber is counted once, and at green or backwards not at all.
## - Every approach stands on the graph: its edge is there, its stop point on
##   the edge, and its published heading the edge's own at the mouth — an id
##   mapped wrong in the merge, or a direction flipped, fails here by name.
##
##     godot --headless --path game --script res://tools/verify_signals.gd
extends "res://tools/verify_tool.gd"

const PlanScript = preload("res://scripts/traffic/signal_plan.gd")
const ControllerScript = preload("res://scripts/traffic/signal_controller.gd")

## Seconds between two samples of a cycle: a tenth of the shortest timing a
## table could sensibly carry.
const STEP_S: float = 0.05
## Axes further apart than this cross. Half way between one axis (0) and a
## crossing (90): the ETL's own tolerance is narrower, and this checks its
## result rather than restating its rule.
const CONFLICT_DEG: float = 45.0
## How far a published heading may sit from the edge's own end segment: the
## ETL rounds it to 0.01.
const HEADING_TOLERANCE_DEG: float = 0.1


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_signals", 60.0)


func _run() -> void:
	var table := load(SignalPlanProfile.PATH) as SignalPlanProfile
	_expect(table != null, "table", "%s loads" % SignalPlanProfile.PATH)
	if table == null:
		_finish("verify_signals")
		return
	_expect(ControllerScript.usable(table), "table", "every timing is positive")
	_check_the_checker(table)
	_check_a_line()

	var graph: RoadGraph = RoadGraph.shared()
	var plan: SignalPlan = PlanScript.resident(graph)
	if plan.is_empty():
		print("  no signals_plan.json in any resident region; nothing to check")
		_finish("verify_signals")
		return
	var approaches: int = 0
	for junction: SignalPlan.Junction in plan.junctions:
		approaches += junction.approaches.size()
		_check_on_graph(graph, plan, junction)
		for problem: String in timeline_problems(junction, table):
			_fail("cycle", "junction %s/%d: %s" % [junction.region, junction.id, problem])
	_expect(
		approaches > 0,
		"plan",
		"%d junctions, %d approaches, every cycle walked" % [plan.junctions.size(), approaches]
	)
	_check_the_watch(graph, plan, table)
	_finish("verify_signals")


## The conflict check must fail a junction whose one stage holds two crossing
## axes, and pass the same junction staged apart.
func _check_the_checker(table: SignalPlanProfile) -> void:
	var junction := PlanScript.Junction.new()
	junction.id = 7
	junction.stages = 1
	for heading: float in [0.0, 90.0]:
		var approach := PlanScript.Approach.new()
		approach.heading_deg = heading
		approach.stage = 0
		junction.approaches.append(approach)
	var merged: PackedStringArray = timeline_problems(junction, table)
	_expect(
		merged.size() > 0 and "crossing" in merged[0],
		"checker",
		"a stage holding crossing axes is caught"
	)
	junction.stages = 2
	junction.approaches[1].stage = 1
	_expect(
		timeline_problems(junction, table).is_empty(),
		"checker",
		"the same junction staged apart passes"
	)


## Everything wrong with one junction's cycle, in words; empty where it holds.
static func timeline_problems(
	junction: SignalPlan.Junction, table: SignalPlanProfile
) -> PackedStringArray:
	var problems: PackedStringArray = []
	var cycle: float = ControllerScript.cycle_s(junction, table)
	var steps: int = ceili(cycle / STEP_S)
	var seen_green: Dictionary[int, bool] = {}
	var last: Array[int] = []
	for approach: SignalPlan.Approach in junction.approaches:
		last.append(ControllerScript.light_at(junction, approach, -STEP_S, table))
	var dark_run_s: float = 0.0
	var longest_dark_s: float = 0.0
	# Two laps: one reads every transition (`last` is seeded a step before the
	# start), and the second lets a dark run the walk began inside count whole.
	for step: int in steps * 2:
		var clock: float = step * STEP_S
		var lit: Array[SignalPlan.Approach] = []
		for index: int in junction.approaches.size():
			var approach: SignalPlan.Approach = junction.approaches[index]
			var light: int = ControllerScript.light_at(junction, approach, clock, table)
			if light == ControllerScript.Light.GREEN:
				seen_green[index] = true
			if light != ControllerScript.Light.RED:
				lit.append(approach)
			if light != last[index] and not _follows(last[index], light):
				problems.append(
					(
						"approach %d goes %s -> %s at %.2f s"
						% [index, _name(last[index]), _name(light), clock]
					)
				)
			last[index] = light
		for a: int in lit.size():
			for b: int in range(a + 1, lit.size()):
				var apart: float = _axis_apart(lit[a].heading_deg, lit[b].heading_deg)
				if apart > CONFLICT_DEG:
					problems.append(
						(
							"crossing axes %.0f and %.0f lit together at %.2f s"
							% [lit[a].heading_deg, lit[b].heading_deg, clock]
						)
					)
					return problems
		dark_run_s = dark_run_s + STEP_S if lit.is_empty() else 0.0
		longest_dark_s = maxf(longest_dark_s, dark_run_s)
	for index: int in junction.approaches.size():
		if not seen_green.has(index):
			problems.append("approach %d never sees a green" % index)
	if junction.crossing and longest_dark_s < table.crossing_s - STEP_S:
		problems.append(
			(
				"the crossing holds every approach red %.2f s, under %.2f"
				% [longest_dark_s, table.crossing_s]
			)
		)
	return problems


## Whether `next` may follow `previous`: the British sequence and nothing else.
static func _follows(previous: int, next: int) -> bool:
	match previous:
		ControllerScript.Light.RED:
			return next == ControllerScript.Light.RED_AMBER
		ControllerScript.Light.RED_AMBER:
			return next == ControllerScript.Light.GREEN
		ControllerScript.Light.GREEN:
			return next == ControllerScript.Light.AMBER
		ControllerScript.Light.AMBER:
			return next == ControllerScript.Light.RED
	return false


static func _name(light: int) -> String:
	return ControllerScript.Light.keys()[light]


## Degrees between two headings' axes, folded to [0, 90].
static func _axis_apart(a: float, b: float) -> float:
	var gap: float = fposmod(a - b, 180.0)
	return minf(gap, 180.0 - gap)


## The approach stands on its edge, stops on it, and runs the way it says.
func _check_on_graph(graph: RoadGraph, plan: SignalPlan, junction: SignalPlan.Junction) -> void:
	var where: String = "junction %s/%d" % [junction.region, junction.id]
	for approach: SignalPlan.Approach in junction.approaches:
		var length: float = graph.plan_length_of(approach.edge)
		if length <= 0.0:
			_fail("graph", "%s: edge %d is not in the graph" % [where, approach.edge])
			continue
		if approach.stop_m < 0.0 or approach.stop_m > length:
			_fail(
				"graph",
				(
					"%s: stop %.2f m is off edge %d (%.2f m)"
					% [where, approach.stop_m, approach.edge, length]
				)
			)
			continue
		if plan.approach_on(approach.edge, approach.along) != approach:
			_fail("graph", "%s: edge %d is keyed to another approach" % [where, approach.edge])
		if not approach.along and graph.is_one_way(approach.edge):
			_fail("graph", "%s: edge %d is one-way and entered against it" % [where, approach.edge])
		# The heading of the edge's segment at the end travel enters by — the
		# ETL's own reading, so a bend near the end cannot fail it.
		var points: PackedVector3Array = graph.polyline_of(approach.edge)
		var last: int = points.size() - 1
		var a: Vector3 = points[last - 1] if approach.along else points[1]
		var b: Vector3 = points[last] if approach.along else points[0]
		var heading: float = fposmod(rad_to_deg(atan2(b.x - a.x, -(b.z - a.z))), 360.0)
		var off: float = absf(
			angle_difference(deg_to_rad(heading), deg_to_rad(approach.heading_deg))
		)
		if rad_to_deg(off) > HEADING_TOLERANCE_DEG:
			_fail(
				"graph",
				(
					"%s: edge %d runs %.1f deg at its end, the plan says %.1f"
					% [where, approach.edge, heading, approach.heading_deg]
				)
			)


## One stop line across +x at the origin, travel -z (north): crossed northward
## within the street only.
func _check_a_line() -> void:
	var line := ControllerScript.StopLine.new()
	line.centre = Vector3.ZERO
	line.travel = Vector3(0, 0, -1)
	line.half_m = 4.0
	_expect(
		line.crossed_by(Vector3(1, 0, 1), Vector3(1, 0, -1)), "watch", "crossed its way: counted"
	)
	_expect(
		not line.crossed_by(Vector3(1, 0, -1), Vector3(1, 0, 1)), "watch", "crossed backwards: not"
	)
	_expect(
		not line.crossed_by(Vector3(5, 0, 1), Vector3(5, 0, -1)),
		"watch",
		"crossed off the street: not"
	)
	_expect(
		not line.crossed_by(Vector3(1, 5, 1), Vector3(1, 5, -1)),
		"watch",
		"crossed on a deck above: not"
	)
	_expect(
		not line.crossed_by(Vector3(1, 0, -0.5), Vector3(1, 0, -1)), "watch", "already past: not"
	)


## The shipped plan's first approach driven over at red, red-and-amber and
## green: two counted, one not; and every approach has a line on the street.
func _check_the_watch(graph: RoadGraph, plan: SignalPlan, table: SignalPlanProfile) -> void:
	var controller: SignalController = ControllerScript.create(plan, table)
	controller.build_lines(graph)
	var count: int = 0
	for junction: SignalPlan.Junction in plan.junctions:
		count += junction.approaches.size()
	var flat: int = 0
	for line: ControllerScript.StopLine in controller.lines():
		if line.half_m <= 0.0:
			flat += 1
	_expect(
		controller.lines().size() == count and flat == 0,
		"watch",
		"a stop line for each of %d approaches, none of zero width" % count
	)
	var line: ControllerScript.StopLine = controller.lines()[0]
	var junction: SignalPlan.Junction = plan.junctions[line.approach.junction]
	var cycle: float = ControllerScript.cycle_s(junction, table)
	var counted: Dictionary[int, int] = {}
	for light: int in [
		ControllerScript.Light.RED, ControllerScript.Light.RED_AMBER, ControllerScript.Light.GREEN
	]:
		var clock: float = 0.0
		while (
			clock < cycle
			and ControllerScript.light_at(junction, line.approach, clock, table) != light
		):
			clock += STEP_S
		controller.clock_s = clock
		var before: int = controller.ran_red_count
		controller.observe(line.centre - line.travel)
		controller.observe(line.centre + line.travel)
		controller.observe(Vector3.INF)
		counted[light] = controller.ran_red_count - before
	_expect(
		(
			counted[ControllerScript.Light.RED] == 1
			and counted[ControllerScript.Light.RED_AMBER] == 1
			and counted[ControllerScript.Light.GREEN] == 0
		),
		"watch",
		"over the line at red, red-and-amber, green: counted %s" % [counted.values()]
	)
	controller.free()
