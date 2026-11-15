## The day that runs to night (`Q160`): the rig's cycle and the clock that
## drives it, held to the promises nothing in a frame can show.
##
## - 🔴 **A resting rig writes nothing.** A rig nobody moved must still hold the
##   authored `Environment` object and the authored sun, untouched — that is
##   what keeps every scripted daylight frame the one it was. A rig that
##   "applied the day" at boot would pass every eye and fail this. `rest()`
##   puts a moved rig back on those same objects (`Q222`).
## - By day the key light's angle moves at one speed (`Q222`, the user's ask:
##   "the light angle move linearly"): from the first keyframe to the first
##   one that lights a lamp, every leg — the authored day's two included —
##   covers its arc at the same degrees per game second.
## - The key light is strongest where it stands highest (`Q222`, the user's
##   ask: brightest at noon, from overhead), and that is not the authored day.
## - 🔴 **Night dims the key light and never loses it.** `VehicleLamps` reads a
##   missing sun as "no rig" and drives dark, so at every keyframe the light is
##   there, above the horizon while it has energy, and at the last one its
##   energy is at or under the car's own `night_energy` bar.
## - `night_lights` rises to 1 and only then falls: a lantern that went out
##   and came on again is a table authored out of order.
## - The key light changes hands unseen (`Q160`'s twilight, `Q225`'s dawn): the
##   widest swing between two keyframes in turn is on a leg whose both ends
##   have no energy, so nobody watches the moon cross the sky to the sunrise.
## - The cycle comes round (`Q225`): just short of `loop_at` the rig is on its
##   first keyframe's look again, lamps out, and a free drive's clock runs on
##   through the night into the next morning while a shift's stops at 1.
## - The authored `.tres` is never the one written to.
## - A free drive's clock reaches 1 in `length_s` game seconds and the morning
##   again in `loop_at` of them, and stays at 0 with the option off.
## - 特更 (`Q162`): in a shift the day runs with the option off, the clock reads
##   the opening hour to the closing one over the same `length_s`, `closed`
##   fires once at the end, and `restart` puts the clock and the rig back.
## - The pause (`Q165`): over a paused tree the shift's hour and the sky hold
##   on real physics frames, and run on after it — the clock must stay
##   pausable, or a phone call spends the shift.
## - A phone's sun reaches the rig's `phone_shadow_max_distance_m`, a desk's
##   the authored one (`P2-6`).
##
## No built region needed: the rig scene and its tables are committed tuning.
extends "res://tools/verify_tool.gd"

const RIG_SCENE := "res://scenes/world/clean_daylight.tscn"
const SettingsScript = preload("res://scripts/core/settings.gd")
const SCRATCH := "user://verify_day_cycle.cfg"
const TICK_S: float = 1.0 / 60.0
## Physics frames run each side of the pause.
const PAUSE_FRAMES: int = 10
## How far apart the fastest and slowest daylight legs of the sun's arc may be.
## The keyframes' angles are written to a tenth of a degree.
const ARC_SPREAD: float = 1.02


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

	var lamps := load(VehicleLampsProfile.PATH) as VehicleLampsProfile
	var moved: Array[int] = [0]
	rig.changed.connect(func() -> void: moved[0] += 1)

	_expect(
		rig.resting and world.environment == authored and sun.transform == day_facing,
		"day",
		"a rig nobody moved rests on the authored scene"
	)
	rig.time_of_day = cycle.day_at
	_expect(
		world.environment == authored and sun.transform == day_facing and moved[0] == 0,
		"day",
		"at day_at %.2f the look is the authored one, and nothing is written" % cycle.day_at
	)

	_check_the_arc(rig, sun)
	moved[0] = 0

	var lights: float = 0.0
	var peak: float = 0.0
	var one_hump: bool = true
	var dim_at_night: bool = true
	var sun_kept: bool = true
	var widest_deg: float = 0.0
	var widest_is_dark: bool = false
	var last_toward := Vector3.ZERO
	var last_energy: float = 0.0
	var highest: float = day_facing.basis.z.normalized().y
	var highest_energy: float = day_energy
	var strongest: float = day_energy
	for key: RigKeyframe in cycle.keyframes:
		rig.time_of_day = key.at
		strongest = maxf(strongest, sun.light_energy)
		if SunGlint.toward(sun).y > highest:
			highest = SunGlint.toward(sun).y
			highest_energy = sun.light_energy
		if peak >= 1.0:
			one_hump = one_hump and key.night_lights <= lights
		else:
			one_hump = one_hump and key.night_lights >= lights
		lights = key.night_lights
		peak = maxf(peak, lights)
		if lights >= 1.0 and lamps != null:
			dim_at_night = dim_at_night and sun.light_energy <= lamps.night_energy
		var up: float = SunGlint.toward(sun).y
		var swing_deg: float = rad_to_deg(last_toward.angle_to(SunGlint.toward(sun)))
		if last_toward != Vector3.ZERO and swing_deg > widest_deg:
			widest_deg = swing_deg
			widest_is_dark = last_energy <= 0.0 and sun.light_energy <= 0.0
		last_toward = SunGlint.toward(sun)
		last_energy = sun.light_energy
		sun_kept = sun_kept and sun.visible and (sun.light_energy <= 0.0 or up > 0.0)
	_expect(
		one_hump and is_equal_approx(peak, 1.0),
		"lights",
		"night_lights rises to 1.0 and only then falls"
	)
	_expect(sun_kept, "sun", "the key light is kept, and above the horizon while it shines")
	_expect(
		widest_is_dark,
		"sun",
		"the key light's widest swing, %.0f°, is on a leg dark at both ends" % widest_deg
	)
	_expect(
		highest_energy == strongest and highest_energy > day_energy,
		"sun",
		(
			"the key light is strongest, %.2f, where it stands highest, %.0f° up"
			% [highest_energy, rad_to_deg(asin(highest))]
		)
	)
	_expect(
		lamps != null and dim_at_night,
		"sun",
		(
			"every keyframe at full night is night to the car's %.2f bar"
			% [lamps.night_energy if lamps != null else -1.0]
		)
	)
	_expect(moved[0] == cycle.keyframes.size(), "signal", "one `changed` a move")
	rig.time_of_day = 0.0
	var first: Vector3 = SunGlint.toward(sun)
	rig.time_of_day = cycle.loop_at - 0.0001
	_expect(
		(
			cycle.loop_at > 1.0
			and rad_to_deg(first.angle_to(SunGlint.toward(sun))) < 0.5
			and LightingRig.night_lights_now < 0.01
		),
		"loop",
		"just short of loop_at %.3f the rig is on its first look again, lamps out" % cycle.loop_at
	)
	_expect(
		world.environment != authored and authored.ambient_light_energy == authored_energy,
		"table",
		"the blend is written to a copy, never to the authored .tres"
	)

	rig.time_of_day = 0.0
	_expect(not rig.resting, "day", "at 0 the rig is on its first keyframe, not at rest")
	var before_rest: int = moved[0]
	rig.rest()
	_expect(
		(
			rig.resting
			and rig.time_of_day == 0.0
			and world.environment == authored
			and sun.transform == day_facing
			and sun.light_energy == day_energy
			and moved[0] == before_rest + 1
		),
		"day",
		"rest() puts back the authored environment and sun themselves, and says so once"
	)
	rig.rest()
	_expect(moved[0] == before_rest + 1, "day", "a resting rig asked to rest writes nothing")

	await _check_the_clock(rig)
	await _check_the_shift(rig)
	await _check_the_pause(rig)
	rig.queue_free()
	_check_the_phone()
	_finish("verify_day_cycle")


## The daylight arc: the stops are the keyframes up to the first that lights a
## lamp, with the authored day among them, and the key light's angular speed
## over each leg is within `ARC_SPREAD` of every other's.
func _check_the_arc(rig: LightingRig, sun: DirectionalLight3D) -> void:
	var stops: Array[float] = []
	for key: RigKeyframe in rig.cycle.keyframes:
		if key.at > rig.cycle.day_at and (stops.is_empty() or stops[-1] < rig.cycle.day_at):
			stops.append(rig.cycle.day_at)
		stops.append(key.at)
		if key.night_lights > 0.0:
			break
	var slowest: float = INF
	var fastest: float = 0.0
	for index: int in range(1, stops.size()):
		rig.time_of_day = stops[index - 1]
		var from: Vector3 = SunGlint.toward(sun)
		rig.time_of_day = stops[index]
		var speed: float = rad_to_deg(from.angle_to(SunGlint.toward(sun)))
		speed /= (stops[index] - stops[index - 1]) * rig.cycle.length_s
		slowest = minf(slowest, speed)
		fastest = maxf(fastest, speed)
	_expect(
		stops.size() > 2 and fastest <= slowest * ARC_SPREAD,
		"sun",
		(
			"by day the key light moves at one speed: %.3f to %.3f °/s over %d legs"
			% [slowest, fastest, stops.size() - 1]
		)
	)


## The phone's shadow reach (`P2-6`): the rig on a desk keeps the authored sun,
## and on a phone pulls it in to its own number, cascades untouched.
func _check_the_phone() -> void:
	var packed := load(RIG_SCENE) as PackedScene
	var rig := packed.instantiate() as LightingRig
	var sun: DirectionalLight3D = _child(rig, "DirectionalLight3D") as DirectionalLight3D
	var authored: float = sun.directional_shadow_max_distance
	var mode: DirectionalLight3D.ShadowMode = sun.directional_shadow_mode
	_expect(
		rig.phone_shadow_max_distance_m > 0.0 and rig.phone_shadow_max_distance_m < authored,
		"phone",
		"the rig names a phone reach under the sun's %.0f m" % authored
	)
	rig.fit_shadow(false)
	_expect(
		sun.directional_shadow_max_distance == authored,
		"phone",
		"off a phone the sun reaches its authored %.0f m" % authored
	)
	rig.fit_shadow(true)
	_expect(
		(
			sun.directional_shadow_max_distance == rig.phone_shadow_max_distance_m
			and sun.directional_shadow_mode == mode
		),
		"phone",
		"on a phone it reaches %.0f m, its cascades as authored" % rig.phone_shadow_max_distance_m
	)
	# The 3D scale (`P2-6`): shipped at 1, where no viewport is written; a dial
	# under 1 reaches a phone's viewport and never a desk's.
	var view := SubViewport.new()
	rig.fit_scale(true, view)
	_expect(
		rig.phone_scale_3d == 1.0 and view.scaling_3d_scale == 1.0,
		"phone",
		"the rig ships a 3D scale of 1, and a phone's viewport is left alone"
	)
	rig.phone_scale_3d = 0.75
	rig.fit_scale(false, view)
	var desk: float = view.scaling_3d_scale
	rig.fit_scale(true, view)
	_expect(
		desk == 1.0 and view.scaling_3d_scale == 0.75,
		"phone",
		"a dial of 0.75 draws a phone's scene at 0.75 and a desk's at 1"
	)
	view.free()
	rig.free()


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
		var ticks: int = ceili(rig.cycle.length_s / TICK_S)
		_tick(clock, ticks)
		if on:
			var at_end: float = rig.time_of_day
			# On round the night, to a second past the morning.
			var more: int = ceili(((rig.cycle.loop_at - 1.0) * rig.cycle.length_s + 1.0) / TICK_S)
			_tick(clock, more)
			_expect(
				(
					absf(at_end - 1.0) < 0.001
					and rig.time_of_day < 0.01
					and clock.is_physics_processing()
				),
				"clock",
				(
					"%.0f game seconds reach 1, and %.0f the morning again with the clock running"
					% [rig.cycle.length_s, rig.cycle.loop_at * rig.cycle.length_s]
				)
			)
		else:
			_expect(
				rig.time_of_day == 0.0 and rig.resting,
				"clock",
				"with the option off the rig rests on the authored day"
			)
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
	_tick(clock, to_close)
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
			and not rig.resting
			and clock.is_physics_processing()
		),
		"shift",
		"restart puts the clock and the rig back to the opening hour, on the morning"
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
	_expect(
		is_nan(clock.hour_now()) and rig.resting,
		"shift",
		"free mode has no hour on the clock, and with the option off the rig rests"
	)
	clock.free()
	SettingsScript.use_file(SettingsScript.PATH)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH))


## The tree paused over a running shift (`Q165`): real physics frames, not
## `_physics_process` called by hand, since a hand call ignores the pause.
func _check_the_pause(rig: LightingRig) -> void:
	rig.time_of_day = 0.0
	var clock := DayClock.new()
	clock.rig = rig
	clock.mode = DayClock.Mode.SHIFT
	root.add_child(clock)
	for frame: int in PAUSE_FRAMES:
		await physics_frame
	var running: float = clock.elapsed_s
	var sky: float = rig.time_of_day
	_expect(running > 0.0 and sky > 0.0, "pause", "the shift and its sky run before the pause")
	paused = true
	for frame: int in PAUSE_FRAMES:
		await physics_frame
	var held: bool = clock.elapsed_s == running and rig.time_of_day == sky
	paused = false
	for frame: int in PAUSE_FRAMES:
		await physics_frame
	_expect(
		held and clock.elapsed_s > running and rig.time_of_day > sky,
		"pause",
		"%d paused frames leave the shift at %.3f s, and it runs on after" % [PAUSE_FRAMES, running]
	)
	clock.free()


## `ticks` physics ticks of `clock` by hand, for as long as it still runs.
func _tick(clock: DayClock, ticks: int) -> void:
	for tick: int in ticks:
		if clock.is_physics_processing():
			clock._physics_process(TICK_S)


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
