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
## - 特更 (`Q162`): in a shift the day runs with the option off, the clock reads
##   the opening hour to the closing one over the same `length_s`, `closed`
##   fires once at the end, and `restart` puts the clock and the rig back.
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
	await _check_the_shift(rig)
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


## 特更 over the rig: the option says ALWAYS DAY and the shift runs the day
## anyway, reads its hours off `ShiftProfile`, closes once, and restarts.
func _check_the_shift(rig: LightingRig) -> void:
	var shift := load(ShiftProfile.PATH) as ShiftProfile
	_expect(shift != null and shift.usable(), "shift", "%s is whole" % ShiftProfile.PATH)
	if shift == null or not shift.usable():
		return
	# One clock (`Q160`): the parked roster reads the rig's dial as the hours
	# the player reads on the dash.
	var parked := load(ParkedProfile.PATH) as ParkedProfile
	_expect(
		(
			parked != null
			and parked.clock_start_h == shift.opens_h
			and parked.clock_end_h == shift.closes_h
		),
		"shift",
		"the parked roster's clock is the shift's, %s to %s" % [shift.opens_h, shift.closes_h]
	)
	SettingsScript.use_file(SCRATCH)
	SettingsScript.set_day_cycle(false)
	rig.time_of_day = 0.0
	var clock := DayClock.new()
	clock.rig = rig
	clock.mode = DayClock.Mode.SHIFT
	var closings: Array[int] = [0]
	clock.closed.connect(func() -> void: closings[0] += 1)
	root.add_child(clock)
	await process_frame
	clock.restart()
	_expect(
		clock.hour_now() == shift.opens_h and clock.closes_h() == shift.closes_h,
		"shift",
		"parked, the clock reads %s, closing at %s" % [shift.opens_h, shift.closes_h]
	)

	var to_close: int = ceili(rig.cycle.length_s / TICK_S)
	for tick: int in floori(to_close / 2.0):
		clock._physics_process(TICK_S)
	var half: float = lerpf(shift.opens_h, shift.closes_h, 0.5)
	_expect(
		(
			closings[0] == 0
			and absf(clock.hour_now() - half) < 0.01
			and clock.on_shift()
			and rig.time_of_day > 0.0
		),
		"shift",
		"halfway it is %.2f h and the day runs with the option off" % clock.hour_now()
	)
	for tick: int in to_close:
		if clock.is_physics_processing():
			clock._physics_process(TICK_S)
	_expect(
		(
			closings[0] == 1
			and clock.is_closed()
			and is_equal_approx(clock.hour_now(), shift.closes_h)
			and is_equal_approx(rig.time_of_day, 1.0)
			and not clock.is_physics_processing()
		),
		"shift",
		(
			"%.0f game seconds reach 交更 at night, `closed` fires once, and the clock stops"
			% rig.cycle.length_s
		)
	)

	clock.restart()
	_expect(
		(
			clock.hour_now() == shift.opens_h
			and not clock.is_closed()
			and rig.time_of_day == 0.0
			and clock.is_physics_processing()
		),
		"shift",
		"restart puts the clock and the rig back to the opening hour"
	)
	_expect(
		(
			DayClock.clock_text(7.0) == "07:00"
			and DayClock.clock_text(14.999) == "14:59"
			and DayClock.clock_text(20.5) == "20:30"
			and DayClock.clock_text(24.0) == "00:00"
		),
		"shift",
		"the face reads the minute begun, on a 24-hour clock"
	)
	clock.mode = DayClock.Mode.FREE
	clock.restart()
	_expect(is_nan(clock.hour_now()), "shift", "free mode has no hour on the clock")
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
