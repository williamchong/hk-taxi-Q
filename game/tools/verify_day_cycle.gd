## The day that runs to night (`Q160`): the rig's cycle and the clock that
## drives it, held to the promises nothing in a frame can show.
##
## - 🔴 **The day writes nothing.** A rig at `time_of_day` 0 must still hold the
##   authored `Environment` object and the authored sun, untouched — that is
##   what keeps every scripted daylight frame the one it was. A rig that
##   "applied the day" at boot would pass every eye and fail this.
## - 🔴 **Night dims the key light and never loses it.** `VehicleLamps` reads a
##   missing sun as "no rig" and drives dark, so at every keyframe the light is
##   there, above the horizon while it has energy, and at the last one its
##   energy is at or under the car's own `night_energy` bar.
## - `night_lights` only rises, and ends at 1: a lantern that went out again
##   on the way to night is a table authored out of order.
## - The authored `.tres` is never the one written to.
## - The clock reaches the last keyframe in `length_s` game seconds, holds
##   there, and stays at 0 with the option off.
##
## No built region needed: the rig scene and its tables are committed tuning.
extends "res://tools/verify_tool.gd"

const RIG_SCENE := "res://scenes/world/clean_daylight.tscn"
const SettingsScript = preload("res://scripts/core/settings.gd")
const SCRATCH := "user://verify_day_cycle.cfg"
const TICK_S: float = 1.0 / 60.0


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_day_cycle", 30.0)


func _run() -> void:
	var rig: LightingRig = await _stand_rig()
	if rig == null:
		_problem("%s did not load as a LightingRig" % RIG_SCENE)
		_finish("verify_day_cycle")
		return
	if rig.cycle == null:
		_problem("%s carries no cycle" % RIG_SCENE)
		rig.free()
		_finish("verify_day_cycle")
		return
	var cycle: RigCycle = rig.cycle
	_expect(cycle.resource_path == RigCycle.PATH, "table", "the rig runs %s" % RigCycle.PATH)
	_expect(cycle.usable() and rig.moves(), "table", "the cycle is whole and the rig can move")
	if not rig.moves():
		rig.free()
		_finish("verify_day_cycle")
		return

	var world: WorldEnvironment = _child(rig, "WorldEnvironment") as WorldEnvironment
	var sun: DirectionalLight3D = _child(rig, "DirectionalLight3D") as DirectionalLight3D
	var authored: Environment = world.environment
	var authored_energy: float = authored.ambient_light_energy
	var day_facing: Transform3D = sun.transform
	var day_energy: float = sun.light_energy

	var moved: Array[int] = [0]
	rig.changed.connect(func() -> void: moved[0] += 1)

	rig.time_of_day = 0.0
	rig.time_of_day = cycle.day_until
	_expect(
		world.environment == authored and sun.transform == day_facing and moved[0] == 0,
		"day",
		"up to day_until %.2f the rig writes nothing" % cycle.day_until
	)

	var lamps := load(VehicleLampsProfile.PATH) as VehicleLampsProfile
	var lights: float = 0.0
	var rising: bool = true
	var sun_kept: bool = true
	for key: RigKeyframe in cycle.keyframes:
		rig.time_of_day = key.at
		rising = rising and key.night_lights >= lights
		lights = key.night_lights
		var up: float = SunGlint.toward(sun).y
		sun_kept = sun_kept and sun.visible and (sun.light_energy <= 0.0 or up > 0.0)
	_expect(rising and is_equal_approx(lights, 1.0), "lights", "night_lights only rises, to 1.0")
	_expect(sun_kept, "sun", "the key light is kept, and above the horizon while it shines")
	_expect(
		lamps != null and sun.light_energy <= lamps.night_energy,
		"sun",
		(
			"the last keyframe's %.2f is night to the car's %.2f bar"
			% [sun.light_energy, lamps.night_energy if lamps != null else -1.0]
		)
	)
	_expect(moved[0] == cycle.keyframes.size(), "signal", "one `changed` a move")
	_expect(
		world.environment != authored and authored.ambient_light_energy == authored_energy,
		"table",
		"the blend is written to a copy, never to the authored .tres"
	)

	rig.time_of_day = 0.0
	_expect(
		is_equal_approx(sun.light_energy, day_energy) and sun.transform.is_equal_approx(day_facing),
		"day",
		"back at 0 the sun is the authored one"
	)

	await _check_the_clock(rig)
	rig.queue_free()
	_finish("verify_day_cycle")


## The clock with nobody parked over it: on, it reaches 1.0 in `length_s` and
## stops; off, it never moves the rig.
func _check_the_clock(rig: LightingRig) -> void:
	SettingsScript.use_file(SCRATCH)
	for on: bool in [true, false]:
		SettingsScript.set_day_cycle(on)
		rig.time_of_day = 0.0
		var clock := DayClock.new()
		clock.rig = rig
		root.add_child(clock)
		await process_frame
		var ticks: int = ceili(rig.cycle.length_s / TICK_S) + 2
		for tick: int in ticks:
			if clock.is_physics_processing():
				clock._physics_process(TICK_S)
		if on:
			_expect(
				is_equal_approx(rig.time_of_day, 1.0) and not clock.is_physics_processing(),
				"clock",
				(
					"%.0f game seconds reach the last keyframe, and the clock stops"
					% rig.cycle.length_s
				)
			)
		else:
			_expect(rig.time_of_day == 0.0, "clock", "with the option off the day never moves")
		clock.free()
	SettingsScript.use_file(SettingsScript.PATH)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH))


func _stand_rig() -> LightingRig:
	var packed := load(RIG_SCENE) as PackedScene
	if packed == null:
		return null
	var rig := packed.instantiate() as LightingRig
	root.add_child(rig)
	await process_frame
	return rig


func _child(parent: Node, type: String) -> Node:
	var found: Array[Node] = parent.find_children("*", type, false, false)
	return null if found.is_empty() else found[0]
