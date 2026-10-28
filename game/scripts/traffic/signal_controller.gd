class_name SignalController
extends Node
## Runs every signalled junction's stages on the physics clock (`P3-3b`,
## `Q173`). `state_of` is the one read: the cars stop at it, and from `P3-3e`
## the heads are lit by it.
##
## 🔴 **The timeline is a pure function of the clock** (`light_at`), so
## `verify_signals.gd` walks every junction's whole cycle without a scene, and a
## state can never depend on what was asked before.
##
## A stage's slot runs red-and-amber, green, amber, all red; every other stage's
## approaches are red throughout it. A crossing (one-axis junction) ends its
## cycle with `crossing_s` of all red. Each junction starts at its own point in
## the cycle (`offset_s`), so the city does not change at once.
##
## **The player's red** (`P3-3d`, the user's call: "keep player detection so
## that we can decide if it would be a bonus or penalty later"). Each approach's
## stop line is the street's width across its stop point; the taxi's middle
## crossing one the approach's way of travel while it shows red or red-and-amber
## is counted in `ran_red_count` and announced on `ran_red` — and NOTHING pays
## or docks it until the user decides which it is. Its middle, not its nose: a
## car that stops with its nose over the line has not run it. One node in
## `city_drive.tscn`, so the count holds under `--traffic=off` too.

## What an approach shows. `NONE` for a way no junction controls.
enum Light { NONE, RED, RED_AMBER, GREEN, AMBER }

## A taxi's middle this far above or below a stop line is on another level.
const LEVEL_APART_M: float = 3.0
## Stop lines further than this from the taxi are not tested on a tick.
const WATCH_M: float = 40.0

## The player's car, watched for a red; none in a verify tool.
@export var vehicle: Node3D

## Announced each time the taxi crosses a stop line on red or red-and-amber.
signal ran_red(edge: int, light: Light)

var plan: SignalPlan
var profile: SignalPlanProfile
## Seconds of physics time since the controller started.
var clock_s: float = 0.0
## Reds the taxi has run since the start.
var ran_red_count: int = 0
## Every approach's stop line, parallel to the plan's approaches in order.
var _lines: Array[StopLine] = []
var _last_at: Vector3 = Vector3.INF


## Where an approach's stop line stands: across `travel` at `centre`, out to
## `half_m` either side.
class StopLine:
	extends RefCounted

	var approach: SignalPlan.Approach
	var centre: Vector3
	var travel: Vector3
	var half_m: float

	## Whether going from `from` to `to` crosses this line its way of travel.
	func crossed_by(from: Vector3, to: Vector3) -> bool:
		if absf(to.y - centre.y) > LEVEL_APART_M:
			return false
		var before: float = (from.x - centre.x) * travel.x + (from.z - centre.z) * travel.z
		var after: float = (to.x - centre.x) * travel.x + (to.z - centre.z) * travel.z
		if before >= 0.0 or after < 0.0:
			return false
		# Where the move meets the line, across it.
		var u: float = -before / (after - before)
		var at: Vector3 = from.lerp(to, u)
		var across: float = absf((at.x - centre.x) * travel.z - (at.z - centre.z) * travel.x)
		return across <= half_m


## The controller over `plan`, or null where the table cannot run (a zero).
static func create(with_plan: SignalPlan, with_profile: SignalPlanProfile) -> SignalController:
	if with_plan == null or with_profile == null or not usable(with_profile):
		return null
	var controller := SignalController.new()
	controller.name = "SignalController"
	controller.plan = with_plan
	controller.profile = with_profile
	return controller


## False, with a pushed reason, where a timing is zero or negative.
static func usable(table: SignalPlanProfile) -> bool:
	var required: Dictionary[String, float] = {
		"red_amber_s": table.red_amber_s,
		"green_s": table.green_s,
		"amber_s": table.amber_s,
		"all_red_s": table.all_red_s,
		"crossing_s": table.crossing_s,
	}
	return not TuningTable.any_zero(table, required, "SignalController", "no signal will run")


func _ready() -> void:
	# Built by `create` (the traffic's own, a verify tool's): already set.
	if plan != null:
		return
	var graph: RoadGraph = RoadGraph.shared()
	var table := load(SignalPlanProfile.PATH) as SignalPlanProfile
	if table == null or not usable(table):
		set_physics_process(false)
		return
	plan = SignalPlan.resident(graph)
	profile = table
	build_lines(graph)


## Each approach's stop line on `graph`: at its stop point, across its heading,
## half the street's published width either side of the centreline.
func build_lines(graph: RoadGraph) -> void:
	_lines.clear()
	for junction: SignalPlan.Junction in plan.junctions:
		for approach: SignalPlan.Approach in junction.approaches:
			var line := StopLine.new()
			line.approach = approach
			var length: float = graph.plan_length_of(approach.edge)
			line.centre = graph.point_at(
				approach.edge, approach.stop_m / length if length > 0.0 else 0.0
			)
			var heading: float = deg_to_rad(approach.heading_deg)
			line.travel = Vector3(sin(heading), 0.0, -cos(heading))
			line.half_m = graph.width_of(approach.edge) * 0.5
			_lines.append(line)


func _physics_process(delta: float) -> void:
	clock_s += delta
	if is_instance_valid(vehicle):
		observe(vehicle.global_position)


## The taxi is at `at` now: count a red for every stop line it crossed since
## the last call. The first call only remembers.
func observe(at: Vector3) -> void:
	var from: Vector3 = _last_at
	_last_at = at
	if from == Vector3.INF:
		return
	for line: StopLine in _lines:
		if absf(line.centre.x - at.x) > WATCH_M or absf(line.centre.z - at.z) > WATCH_M:
			continue
		if not line.crossed_by(from, at):
			continue
		var approach: SignalPlan.Approach = line.approach
		var light: Light = light_at(plan.junctions[approach.junction], approach, clock_s, profile)
		if light == Light.RED or light == Light.RED_AMBER:
			ran_red_count += 1
			ran_red.emit(approach.edge, light)


## Every stop line, for a verify tool.
func lines() -> Array[StopLine]:
	return _lines


## One vehicle stage's slot, in seconds.
static func slot_s(table: SignalPlanProfile) -> float:
	return table.red_amber_s + table.green_s + table.amber_s + table.all_red_s


## A junction's whole cycle, in seconds.
static func cycle_s(junction: SignalPlan.Junction, table: SignalPlanProfile) -> float:
	return junction.stages * slot_s(table) + (table.crossing_s if junction.crossing else 0.0)


## Where in its `cycle` a junction starts: its id's golden-ratio fraction of
## it, so neighbours differ and a rebuild that keeps the id keeps the offset.
static func offset_s(junction: SignalPlan.Junction, cycle: float) -> float:
	return fposmod(junction.id * 0.6180339887, 1.0) * cycle


## What `approach` shows at `clock`.
static func light_at(
	junction: SignalPlan.Junction,
	approach: SignalPlan.Approach,
	clock: float,
	table: SignalPlanProfile
) -> Light:
	var cycle: float = cycle_s(junction, table)
	var into: float = fposmod(clock + offset_s(junction, cycle), cycle)
	var slot: float = slot_s(table)
	var start: float = approach.stage * slot
	if into < start or into >= start + slot:
		return Light.RED
	var t: float = into - start
	if t < table.red_amber_s:
		return Light.RED_AMBER
	t -= table.red_amber_s
	if t < table.green_s:
		return Light.GREEN
	t -= table.green_s
	if t < table.amber_s:
		return Light.AMBER
	return Light.RED


## What a car driving `edge` this way sees at its stop line now; `NONE` where
## no junction controls it.
func state_of(edge: int, along: bool) -> Light:
	var approach: SignalPlan.Approach = plan.approach_on(edge, along)
	if approach == null:
		return Light.NONE
	return light_at(plan.junctions[approach.junction], approach, clock_s, profile)


## Whether a light lets a car past its stop line: green only. Amber and
## red-and-amber stop a car that can stop; that judgement is the car's.
static func is_go(light: Light) -> bool:
	return light == Light.GREEN or light == Light.NONE
