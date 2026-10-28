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

## What an approach shows. `NONE` for a way no junction controls.
enum Light { NONE, RED, RED_AMBER, GREEN, AMBER }

var plan: SignalPlan
var profile: SignalPlanProfile
## Seconds of physics time since the controller started.
var clock_s: float = 0.0


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


func _physics_process(delta: float) -> void:
	clock_s += delta


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
