extends "res://tools/verify_tool.gd"

## Does the taxi's shading actually reach the shader? (`P3-11c`, `P3-11d`, `P3-11e`)
##
##     godot --headless --path game --script res://tools/verify_vehicle.gd
##
## Everything between the `.glb` on disk and the fragment shader is engine-side,
## and **every failure along it renders nearly right**, which is the one symptom
## nothing else here can see. Two paths in particular:
##
## - **The material name.** `tools/make_vehicle.py` writes the glTF material name
##   `vehicle_body` and `tools/generated_scene_import.gd` maps it to
##   `vehicle_body.tres`. Drop the name, the dictionary entry, the `.tres` or the
##   `[importer_defaults]` wiring and the body falls back to the `BaseMaterial3D`
##   it imported with — a red car with no clearcoat, no sky gradient, and no lamp
##   branch at all.
## - **The switched channels.** `vehicle_lamps.gd` writes `lamp_lit` and
##   `lamp_front` with `set_instance_shader_parameter`. An unmatched name is **not
##   an error**: it is a no-op, the shader keeps its `vec4(0.0)` default, and that
##   default is every lamp out.
##
## ⚠️ **The Python side already holds the generator, and this is not a second copy
## of it.** `TestSurfaceMarkers` and `TestLampCircuits` grade `MeshData` before
## the glTF is written, and `TestShippedAssets` proves the committed `.glb` is
## that generator's output. What no `pytest` can see is the **import** and the
## **scene**, so the payload is read back off the mesh Godot handed the renderer —
## after `ensure_tangents`, surface dedup and LOD generation — rather than off the
## file the ETL wrote.
##
## ⚠️ **It cannot see a frame, and must not be read as if it could.** Headless has
## no rasteriser, and Godot exits `0` on a shader that fails to compile. Whether
## the car *looks* right is still a render and a `grep -i "shader error"` over the
## driver log; this holds the wiring that render depends on.
##
## ⚠️ **Nothing here references a `class_name` global**, for the reason
## `verify_beam_budget.gd` gives: a `--script` tool that does fails to *parse* on a
## fresh clone, where `global_script_class_cache.cfg` has not been written — so
## `_init` never runs, `quit(1)` is never reached, and the SceneTree exits **0**
## having checked nothing. Nodes are identified by the path of the script they
## run, and constants are read out of scripts `load`ed by path.
##
## ⚠️ **The first `await` is still load-bearing, for a narrower reason than it
## was.** Autoloads are registered on the first frame, not before. Until `Q119`
## `vehicle_controller.gd` named `InputRouter` as a global, so loading `taxi.tscn`
## from `_init` compiled it while that name was unresolvable, GDScript cached the
## broken class, and the scene instanced a `RigidBody3D` with a **null script** —
## a run that printed `SCRIPT ERROR` having graded a car that never loaded. The
## car now resolves the router by `NodePath` in `_ready`, so the script compiles
## anywhere; what the frame still buys is that `BeamBudget` and `InputRouter`
## exist when the rig and the car go looking, so this grades the wiring a real
## scene has rather than the "no arbiter" branch. `skidpad_ablation.gd` waits for
## the same reason.
##
## Needs no built region: the taxi is a committed authored asset, so this runs
## outside `check.sh`'s `VERIFY_GENERATED` gate with `verify_beam_budget.gd`.

## The player's car, and the only one: `taxi.tscn` with the per-wheel tyre model
## on it (`Q152`), an inherited scene, so every rig below is `taxi.tscn`'s own. A
## roster car earns its own entry here when it exists; a car carrying no lamp rig
## is supported rather than broken, which `vehicle_lamps.gd` records, so such an
## entry would check less than this.
const SCENE_PATH := "res://scenes/vehicle/taxi_tyre.tscn"
## The scene the game drives, which must instance the car graded here.
const DRIVE_SCENE_PATH := "res://scenes/city_drive.tscn"
const MATERIAL_PATH := "res://tuning/vehicle_body.tres"
const SHADER_PATH := "res://assets/shaders/vehicle_body.gdshader"
const LAMPS_SCRIPT := "res://scripts/vehicle/vehicle_lamps.gd"
const GLINT_SCRIPT := "res://scripts/vehicle/sun_glint.gd"
const CONTROLLER_SCRIPT := "res://scripts/vehicle/vehicle_controller.gd"
const DOOR_SCRIPT := "res://scripts/vehicle/taxi_door.gd"
const EMOTE_SCRIPT := "res://scripts/vehicle/passenger_emote.gd"
const TYRE_SCRIPT := "res://scripts/vehicle/tyre_vehicle_controller.gd"
const MARKS_SCRIPT := "res://scripts/vehicle/skid_marks.gd"
const STRIP_SCRIPT := "res://scripts/vehicle/skid_strip.gd"
const FLICK_SCRIPT := "res://scripts/vehicle/flick_watch.gd"
const SPARKS_SCRIPT := "res://scripts/vehicle/drift_sparks.gd"
const OUTLINE_SCRIPT := "res://scripts/vehicle/car_outline.gd"
## The tuning tables the three rigs read (`Q150`). Restated here rather than read
## off the profile scripts' `PATH`, so the tool cannot be steered by the file it
## grades: what is asserted is that the scene hands each node THIS resource.
const LAMPS_PROFILE_PATH := "res://tuning/vehicle_lamps.tres"
const DOOR_PROFILE_PATH := "res://tuning/taxi_door.tres"
const EMOTE_PROFILE_PATH := "res://tuning/passenger_emote.tres"
const TYRE_PROFILE_PATH := "res://tuning/tyre.tres"
## The car's own table, the game's pace and the car's systems' (`Q155`,
## `Q156`), by the controller's property for each.
const SYSTEM_PATHS: Dictionary[String, String] = {
	"car": "res://tuning/cars/crown_comfort.tres",
	"pace": "res://tuning/pace.tres",
	"traction_control": "res://tuning/systems/traction_control.tres",
	"stability_control": "res://tuning/systems/stability_control.tres",
	"drift_mode": "res://tuning/systems/drift_mode.tres",
	"handbrake": "res://tuning/systems/handbrake.tres",
	"rev_limiter": "res://tuning/systems/rev_limiter.tres",
	"arcade_aids": "res://tuning/systems/arcade_aids.tres",
	"anti_lock_brakes": "res://tuning/systems/anti_lock_brakes.tres",
}
const MARKS_PROFILE_PATH := "res://tuning/skid_marks.tres"
const SPARKS_PROFILE_PATH := "res://tuning/drift_sparks.tres"
const OUTLINE_PROFILE_PATH := "res://tuning/car_outline.tres"


## The rigs' dials are tuning resources, and a zero key makes each rig inert
## (`Q150`, hard rule 4).
##
## Three things per rig, in the order a missing file would fail them: the scene
## assigns a profile at all; it is the shipped resource by path, which is the
## values proof — the node holds the very file, so equality of values is
## identity; and the rig's `usable()` accepts it. Then the mutation: a duplicate
## with the divisor zeroed is swapped in, `usable()` must refuse it, and the rig
## must DO nothing on it — the door does not open, no face goes up. The lamps
## are graded on `usable()` alone: their inertness is `_ready`'s, and nothing
## here enters a tree. The `ERROR:` lines `TuningTable.any_zero` pushes during
## the mutation are the guard speaking, not a failure — `verify_fares.gd` reads
## the same lines for the skills.
func _check_the_dials_are_data(car: Node3D) -> void:
	var before: int = _failed
	var rigs: Array[Array] = [
		[_running(car, LAMPS_SCRIPT), LAMPS_PROFILE_PATH, "lamps", "probe_hz"],
		[_running(car, DOOR_SCRIPT), DOOR_PROFILE_PATH, "door", "swing_s"],
		[_running(car, EMOTE_SCRIPT), EMOTE_PROFILE_PATH, "emote", "life_s"],
		[_running(car, MARKS_SCRIPT), MARKS_PROFILE_PATH, "tyre marks", "mark_width_m"],
		[_running(car, SPARKS_SCRIPT), SPARKS_PROFILE_PATH, "sparks", "lifetime_s"],
		[_running(car, OUTLINE_SCRIPT), OUTLINE_PROFILE_PATH, "outline", "full_speed_kph"],
	]
	for rig: Array in rigs:
		var node := rig[0] as Node3D
		var path: String = rig[1]
		var label: String = rig[2]
		var divisor: String = rig[3]
		if node == null:
			_problem("no node in %s carries the %s rig" % [SCENE_PATH, label])
			continue
		var table := node.get("profile") as Resource
		if table == null:
			_problem("the %s rig has no profile assigned in %s" % [label, SCENE_PATH])
			continue
		if table.resource_path != path:
			_problem("the %s rig reads %s, not the shipped %s" % [label, table.resource_path, path])
		if not node.usable():
			_problem("the shipped %s table has a zero or missing key" % label)
		var zeroed := table.duplicate() as Resource
		zeroed.set(divisor, 0.0)
		node.set("profile", zeroed)
		if node.usable():
			_problem(
				"mutation missed: a zero %s in the %s table still reads usable" % [divisor, label]
			)
		match label:
			"door":
				node.open()
				if node.is_open() or node.is_physics_processing():
					_problem("mutation missed: the door moved on a zero swing_s")
			"emote":
				var live_before: int = node.live()
				node.show_face(0)
				if node.live() != live_before:
					_problem("mutation missed: a face went up on a zero life_s")
		node.set("profile", table)
	if _failed == before:
		print(
			(
				"  ok    the lamp, door, face, tyre-mark, spark and outline dials are tuning resources,"
				+ " and a zero key makes each inert"
			)
		)


## The game's car runs the tyre model, on the shipped table (`Q152`).
##
## A tyre table with a zero key parks the car behind one `ERROR:` line at boot,
## which a drive would show and a headless check would not. So it is refused
## here — the car's script, the table by path, `usable()` on it, and the
## mutation, a duplicate with `mu` zeroed. Last, that
## `city_drive.tscn` instances this scene, read off its dependency list rather
## than by loading it: the drive scene needs a built region and this tool does
## not.
func _check_the_car_runs_its_tyre_model(car: Node3D) -> void:
	var before: int = _failed
	if not _runs(car, TYRE_SCRIPT):
		_problem("%s does not run %s" % [SCENE_PATH, TYRE_SCRIPT])
		return
	var table := car.get("tyre") as Resource
	if table == null:
		_problem("the car has no tyre table assigned in %s" % SCENE_PATH)
		return
	if table.resource_path != TYRE_PROFILE_PATH:
		_problem("the car reads %s, not the shipped %s" % [table.resource_path, TYRE_PROFILE_PATH])
	var controller := car.get_script() as GDScript
	if not controller.call(&"usable", table):
		_problem("the shipped tyre table has a zero or missing key")
	var zeroed := table.duplicate() as Resource
	zeroed.set("mu", 0.0)
	if controller.call(&"usable", zeroed):
		_problem("mutation missed: a zero mu in the tyre table still reads usable")
	# Each system's table by path: an unassigned one parks the car, and a
	# trial table left in the scene would grade a car the game does not ship.
	for system: String in SYSTEM_PATHS:
		var system_table := car.get(system) as Resource
		if system_table == null:
			_problem("the car has no %s table assigned in %s" % [system, SCENE_PATH])
		elif system_table.resource_path != SYSTEM_PATHS[system]:
			_problem(
				(
					"the car's %s reads %s, not %s"
					% [system, system_table.resource_path, SYSTEM_PATHS[system]]
				)
			)
	var listed: Array = Array(ResourceLoader.get_dependencies(DRIVE_SCENE_PATH))
	if not listed.any(func(dependency: String) -> bool: return dependency.ends_with(SCENE_PATH)):
		_problem("%s does not instance %s" % [DRIVE_SCENE_PATH, SCENE_PATH])
	if _failed == before:
		print("  ok    the game's car runs the tyre model on the shipped table")


## The flick (`P3-54`), driven without a car at 60 Hz on the shipped table: a
## lifted or braked feint and the reversal fire on the tick the steering
## arrives, once; a held throttle, a feint under `flick_feint_s`, a pause past
## `flick_window_s`, a speed under `flick_min_kph` and a plain corner never do;
## and a zero `flick_window_s` turns it off. Each from the side that would read
## wrong.
func _check_the_flick_is_read_off_the_inputs() -> void:
	var before: int = _failed
	var table := load(SYSTEM_PATHS["arcade_aids"]) as Resource
	var watch_script := load(FLICK_SCRIPT) as GDScript
	if table == null or watch_script == null:
		_problem("%s or %s did not load" % [SYSTEM_PATHS["arcade_aids"], FLICK_SCRIPT])
		return
	var delta: float = 1.0 / 60.0
	var feint: float = table.get("flick_feint_s") + 0.05
	var window: float = table.get("flick_window_s")
	var slow: float = table.get("flick_min_kph") - 1.0
	var off := table.duplicate() as Resource
	off.set("flick_window_s", 0.0)
	# Each: a list of [steer, throttle, brake, seconds] legs, the speed, the
	# table, how many ticks may fire, and what the case is.
	var cases: Array[Array] = [
		[[[-1.0, 0.0, 0.0, feint], [1.0, 1.0, 0.0, 0.5]], 63.0, table, 1, "a lifted flick"],
		[[[-1.0, 0.0, 1.0, feint], [1.0, 1.0, 0.0, 0.5]], 63.0, table, 1, "a braked flick"],
		[[[-1.0, 1.0, 0.0, feint], [1.0, 1.0, 0.0, 0.5]], 63.0, table, 0, "a held throttle"],
		[[[-1.0, 0.0, 0.0, 0.05], [1.0, 1.0, 0.0, 0.5]], 63.0, table, 0, "a feint too short"],
		[
			[[-1.0, 0.0, 0.0, feint], [0.0, 1.0, 0.0, window + 0.1], [1.0, 1.0, 0.0, 0.5]],
			63.0,
			table,
			0,
			"a pause past the window"
		],
		[[[-1.0, 0.0, 0.0, feint], [1.0, 1.0, 0.0, 0.5]], slow, table, 0, "a flick too slow"],
		[[[1.0, 0.0, 0.0, 3.0]], 63.0, table, 0, "a plain lifted corner"],
		[[[-1.0, 0.0, 0.0, feint], [1.0, 1.0, 0.0, 0.5]], 63.0, off, 0, "a zero window"],
	]
	for case: Array in cases:
		var watch: RefCounted = watch_script.new()
		var fired: int = 0
		for leg: Array in case[0]:
			var ticks: int = roundi(float(leg[3]) / delta)
			for _tick: int in ticks:
				if watch.step(leg[0], leg[1], leg[2], case[1], delta, case[2]):
					fired += 1
		if fired != case[3]:
			_problem("the flick fired %d times on %s, not %d" % [fired, case[4], case[3]])
	if _failed == before:
		print("  ok    the flick fires on a lifted or braked reversal, and on nothing else")


## The tyre marks' strip (`P3-57`), driven without a car: a wheel under the bar
## lays nothing; over it, the first tick only starts the mark and the next lays
## a piece, lifted and as wide as the tread; leaving the ground, falling under
## the bar or jumping further than `max_step_m` in a tick breaks the mark, so
## nothing is drawn across the gap; two wheels keep two marks; and past
## `capacity` the oldest slot is reused. Each from both sides — the tick that
## should lay, lays.
func _check_the_tyre_marks_break_and_wrap() -> void:
	var before: int = _failed
	var table := load(MARKS_PROFILE_PATH) as Resource
	var strip_script := load(STRIP_SCRIPT) as GDScript
	if table == null or strip_script == null:
		_problem("%s or %s did not load" % [MARKS_PROFILE_PATH, STRIP_SCRIPT])
		return
	var bar: float = table.get("mark_from_slip")
	var width: float = table.get("mark_width_m")
	var lift: float = table.get("lift_m")
	var reach: float = table.get("max_step_m")
	var capacity: int = table.get("capacity")
	var strip: RefCounted = strip_script.new(2, table)
	var up := Vector3.UP
	var side := Vector3.RIGHT
	var at := Vector3.ZERO
	var step := Vector3(0.0, 0.0, -0.5)
	# Under the bar, however long: nothing.
	for tick: int in 3:
		if strip.step(0, true, at, up, side, bar - 0.01) != -1:
			_problem("a wheel a hair under mark_from_slip laid a mark")
		at += step
	# On the bar: the first tick starts the mark, the second lays a piece.
	if strip.step(0, true, at, up, side, bar) != -1:
		_problem("the first tick over the bar laid a piece with nothing to join it to")
	at += step
	var slot: int = strip.step(0, true, at, up, side, bar)
	if slot != 0 or strip.get("laid") != 1:
		_problem("the second tick on the bar laid nothing (slot %d)" % slot)
	else:
		var corners: PackedVector3Array = strip.positions()
		var near_edge: float = corners[3].distance_to(corners[2])
		if not is_equal_approx(near_edge, width):
			_problem("a piece is %.3f m wide, not the tread's %.3f m" % [near_edge, width])
		if not is_equal_approx(corners[2].y, lift):
			_problem("a piece sits %.3f m off the road, not lift_m %.3f m" % [corners[2].y, lift])
	# Each break, then the ticks that restart it. A jump lands over the bar,
	# so its landing tick has already started the next mark.
	var breaks: Array[Array] = [
		["off the ground", false, bar, Vector3.ZERO, false],
		["under the bar", true, bar - 0.01, Vector3.ZERO, false],
		["a jump past max_step_m", true, bar, Vector3(0.0, 0.0, -(reach + 0.01)), true],
	]
	for broken: Array in breaks:
		var why: String = broken[0]
		var landed_marking: bool = broken[4]
		at += step + (broken[3] as Vector3)
		var laid_before: int = strip.get("laid")
		if strip.step(0, broken[1], at, up, side, broken[2]) != -1:
			_problem("a mark ran on across %s" % why)
		if strip.get("laid") != laid_before:
			_problem("a piece was drawn across %s" % why)
		at += step
		if not landed_marking and strip.step(0, true, at, up, side, bar) != -1:
			_problem("the first tick back over the bar after %s laid a piece" % why)
		at += step
		if strip.step(0, true, at, up, side, bar) == -1:
			_problem("the mark did not start again after %s" % why)
	# Two wheels, two marks: wheel 1 marking lays nothing for wheel 0.
	var pair: RefCounted = strip_script.new(2, table)
	pair.step(1, true, Vector3.ZERO, up, side, bar)
	if pair.step(0, true, step, up, side, bar) != -1:
		_problem("wheel 0 joined its first tick to wheel 1's mark")
	# The ring: `capacity` + 1 pieces reuse slot 0.
	var ring: RefCounted = strip_script.new(1, table)
	var last: int = -1
	var along := Vector3.ZERO
	for tick: int in capacity + 2:
		last = ring.step(0, true, along, up, side, bar)
		along += step
	if ring.get("laid") != capacity + 1 or last != 0:
		_problem(
			(
				"the ring did not wrap: %d laid, the last in slot %d, at capacity %d"
				% [ring.get("laid"), last, capacity]
			)
		)
	if _failed == before:
		print(
			"  ok    a tyre mark is laid over the bar, breaks at every gap, and wraps at capacity"
		)


## The sparks show `SkillTracker.drift_tier` (`P3-58`): clear at -1, the
## table's colour per tier, the last colour past the end, and a table with no
## colours or a zero key refused. The tier itself is `verify_fares`'
## `sparks:` block, which steps it on the tracker that pays.
func _check_the_sparks_take_the_tier(car: Node3D) -> void:
	var before: int = _failed
	var sparks := _running(car, SPARKS_SCRIPT) as Node3D
	if sparks == null:
		_problem("no node in %s runs %s" % [SCENE_PATH, SPARKS_SCRIPT])
		return
	var table := sparks.get("profile") as Resource
	if table == null:
		return
	var colours: PackedColorArray = table.get("colours")
	if sparks.colour_of(-1).a != 0.0:
		_problem("the sparks are not clear with no slide counting")
	for tier: int in colours.size():
		if sparks.colour_of(tier) != colours[tier]:
			_problem("tier %d does not show colours[%d]" % [tier, tier])
	if sparks.colour_of(colours.size() + 3) != colours[colours.size() - 1]:
		_problem("a tier past the table does not keep its last colour")
	var emptied := table.duplicate() as Resource
	emptied.set("colours", PackedColorArray())
	sparks.set("profile", emptied)
	if sparks.usable():
		_problem("mutation missed: a spark table with no colours still reads usable")
	sparks.set("profile", table)
	if _failed == before:
		print("  ok    the sparks take each tier's colour and are clear when no slide counts")


## The car's outline (`P3-65`): the rim at no width with no slide counting and
## at its one width on every counted tier; its ease never a snap, in either
## direction; the speed share 0 at rest, a half at half of `full_speed_kph`,
## held at 1 above it. A table with no city line to take the colour from is
## refused. The global it writes is `verify_settings.gd`'s.
func _check_the_outline_takes_the_tier_and_speed(car: Node3D) -> void:
	var before: int = _failed
	var outline := _running(car, OUTLINE_SCRIPT) as Node3D
	if outline == null:
		_problem("no node in %s runs %s" % [SCENE_PATH, OUTLINE_SCRIPT])
		return
	var table := outline.get("profile") as Resource
	if table == null:
		_problem("the car outline has no profile assigned in %s" % SCENE_PATH)
		return
	var width: float = table.get("hull_width_m")
	if outline.width_of(-1) != 0.0:
		_problem("the rim has a width with no slide counting")
	for tier: int in 4:
		if outline.width_of(tier) != width:
			_problem("tier %d's rim is not the one hull_width_m" % tier)
	var tick: float = 1.0 / 60.0
	var seeped: float = outline.eased(0.0, width, tick)
	var drained: float = outline.eased(width, 0.0, tick)
	if not (seeped > 0.0 and seeped < width * 0.5):
		_problem("the rim does not seep in: one tick took it to %.4f of %.4f" % [seeped, width])
	if not (drained < width and drained > width * 0.5):
		_problem("the rim does not drain: one tick took it to %.4f of %.4f" % [drained, width])
	var full: float = table.get("full_speed_kph")
	if outline.speed_share(0.0) != 0.0 or outline.speed_share(full * 2.0) != 1.0:
		_problem("the speed share is not 0 at rest and held at 1 past full speed")
	if not is_equal_approx(outline.speed_share(full * 0.5), 0.5):
		_problem("the speed share is not a half at half of full_speed_kph")
	var lineless := table.duplicate() as Resource
	lineless.set("city_line", null)
	outline.set("profile", lineless)
	if outline.usable():
		_problem("mutation missed: an outline table with no city line still reads usable")
	outline.set("profile", table)
	if _failed == before:
		print(
			"  ok    the car's rim seeps in and drains on a counted slide, and the line takes its speed"
		)


## Where `GeometryInstance3D` publishes the instance uniforms its material
## declares. This is the renderer's own list — the same one
## `set_instance_shader_parameter` dispatches against — which is why it is asked
## rather than the shader source: a name that is in the source but not in this
## list would still be a silent no-op, and this list is what decides.
const INSTANCE_PREFIX := "instance_shader_parameters/"

## The prefix `vehicle_lamps.gd` names its channel constants with. Read from the
## script rather than written down here, so a third vector is picked up by adding
## a `PARAMETER_*` constant beside the two that exist.
const CHANNEL_CONSTANT_PREFIX := "PARAMETER"

## `MARKER_*` in `tools/make_vehicle.py` and `vehicle_body.gdshader`. Only the two
## ends are needed: the lens marker, because it is the only one the circuit branch
## reads, and the last legal value, because a marker past it takes the paint
## branch in silence.
const MARKER_LAMP := 2.0
const MARKER_LAST := 3.0
const CIRCUIT_NONE := 0.0


func _init() -> void:
	# Deferred, then a frame, before anything is loaded. See the header.
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_vehicle", 30.0)


func _run() -> void:
	await process_frame

	var packed := load(SCENE_PATH) as PackedScene
	if packed == null:
		_problem("%s did not load as a scene" % SCENE_PATH)
		_finish("verify_vehicle")
		return
	# Instantiated into a `Node` and cast afterwards, so the failure path still has
	# something to free. Casting on the way in discards the reference where the
	# cast fails, and the run then ends in the page of leak errors the `free()`
	# below exists to keep out of a report that is already failing.
	var instanced: Node = packed.instantiate()
	var car := instanced as Node3D
	if car == null:
		_problem("%s did not instantiate as a Node3D" % SCENE_PATH)
		instanced.free()
		_finish("verify_vehicle")
		return

	# Found the way the script finds them, so this grades the wiring rather than
	# the file layout: a lamp rig moved to another node is caught here, not by a
	# path that was written down twice.
	var lamps := _running(car, LAMPS_SCRIPT) as Node3D
	if lamps == null:
		_problem("no node in %s runs %s" % [SCENE_PATH, LAMPS_SCRIPT])
		car.free()
		_finish("verify_vehicle")
		return
	# ⚠️ **The mesh is checked here, not where it is read.** `_body_under` promises
	# a `MeshInstance3D`, never that it carries a mesh — and dereferencing a null
	# one is a run-time error inside a coroutine, which kills the run before
	# `quit()` and exits **0** having reported nothing. That is the failure this
	# whole file is built against, so it is refused at the door.
	var body: MeshInstance3D = _body_under(lamps)
	if body == null or body.mesh == null:
		_problem("the lamp rig has no MeshInstance3D with a mesh below it to switch")
		car.free()
		_finish("verify_vehicle")
		return

	var material: ShaderMaterial = _check_the_body_wears_its_shader(body)
	# Walked once and handed to both checks that read it. See
	# `_declared_instance_uniforms` for why the renderer's list is the authority.
	var declared: Dictionary = _declared_instance_uniforms(body)
	var channels: int = _check_the_switched_channels_reach_the_shader(declared)
	_check_the_payload_survived_the_import(body, channels)
	_check_the_sun_belongs_to_the_material(declared, material)
	_check_the_rig_hangs_where_the_script_looks(car, lamps, material)
	_check_the_beams_point_at_the_road(car)
	_check_the_door_hangs_on_the_flank(car)
	_check_the_passenger_can_make_a_face(car)
	_check_the_car_runs_its_tyre_model(car)
	_check_the_flick_is_read_off_the_inputs()
	_check_the_tyre_marks_break_and_wrap()
	_check_the_sparks_take_the_tier(car)
	_check_the_outline_takes_the_tier_and_speed(car)
	# Last, because it swaps zeroed tables into the rigs and no check above may
	# run against one.
	_check_the_dials_are_data(car)

	# Freed rather than left to the exit: an instantiated scene that never
	# reaches a tree is leaked at exit, and Godot reports that as a page of
	# `ERROR: ... leaked` lines that read like a failure and are not one.
	car.free()
	_finish("verify_vehicle")


## Every surface of the body must render with `vehicle_body.tres`.
##
## The whole material-name path in one assertion: it fails whether the ETL
## dropped the name, `generated_scene_import.gd` dropped the entry, the `.tres`
## moved, or the importer default came unwired — and the fallback it catches is a
## `BaseMaterial3D` that renders very nearly as the shader does.
func _check_the_body_wears_its_shader(body: MeshInstance3D) -> ShaderMaterial:
	var before: int = _failed
	var found: ShaderMaterial = null
	var surfaces: int = body.mesh.get_surface_count()
	# ⚠️ **A mesh with nothing to render passes every loop below without entering
	# one**, and would take the shader and payload checks down with it silently —
	# the shape of quiet pass this tool exists to remove.
	if surfaces == 0:
		_problem("%s carries a mesh with no surfaces to render" % body.name)
	for surface: int in surfaces:
		var material: Material = body.mesh.surface_get_material(surface)
		var shaded := material as ShaderMaterial
		if shaded == null:
			var what: String = "nothing"
			if material != null:
				what = "%s %s" % [material.get_class(), material.resource_path]
			_problem(
				"%s surface %d renders with %s, not the body shader" % [body.name, surface, what]
			)
			continue
		if shaded.resource_path != MATERIAL_PATH:
			_problem(
				(
					"%s surface %d wears %s, not %s"
					% [body.name, surface, shaded.resource_path, MATERIAL_PATH]
				)
			)
			continue
		found = shaded
	# Which shader backs the material is a property of the material, so it is
	# asked once rather than per surface — reported inside the loop it would
	# print the same line, and count the same defect, once per surface.
	if found != null and (found.shader == null or found.shader.resource_path != SHADER_PATH):
		_problem("%s is not backed by %s" % [MATERIAL_PATH, SHADER_PATH])
	# ⚠️ **Against `_failed`, not against `found`.** `found` only says *some*
	# surface passed, so a two-surface body with one fallback would report the
	# failure and then print an `ok` line claiming both surfaces were shaded —
	# and the `ok` is the line a reader believes.
	if _failed == before:
		print("  ok    %s renders %d surface(s) with %s" % [body.name, surfaces, MATERIAL_PATH])
	return found


## The passenger door (`P3-48`) hangs where `taxi_door.gd` can swing it.
##
## A direct child of the car, so its rotation is the swing in the car's frame; off
## the centreline, because the script reads which way is out from the sign of `x`
## and stays shut at zero; authored shut, because the script only ever eases
## *from* where it is; and a leaf that wears the body shader, because it goes
## through the same material door as the body and fails the same silent way. The
## hinge's position against the generator is `test_make_vehicle.py`'s to hold.
func _check_the_door_hangs_on_the_flank(car: Node3D) -> void:
	var before: int = _failed
	var door := _running(car, DOOR_SCRIPT) as Node3D
	if door == null:
		_problem("no node in %s runs %s" % [SCENE_PATH, DOOR_SCRIPT])
		return
	if door.get_parent() != car:
		_problem(
			"%s is not a direct child of the car, so its rotation is not the swing" % door.name
		)
	if is_zero_approx(door.position.x):
		_problem("%s sits on the centreline and cannot tell which way is out" % door.name)
	if not door.transform.basis.is_equal_approx(Basis.IDENTITY):
		_problem("%s is authored turned; the door must start shut" % door.name)
	var leaf: MeshInstance3D = _body_under(door)
	if leaf == null or leaf.mesh == null:
		_problem("%s has no MeshInstance3D with a mesh below it to swing" % door.name)
		return
	_check_the_body_wears_its_shader(leaf)
	if _failed == before:
		print("  ok    the passenger door hangs on the flank, shut")


## The passenger's face (`P3-49`) pops from the seat, and the meshes are built
## the way round the script turns them.
##
## The rig sits on the door's side of the car and behind the hinge — the rear
## kerbside seat — so the face rises out of the back of the cab. Each emote
## scene must instance to a mesh whose features stand proud of -Z, the side
## `look_at` turns to the camera: a face built on +Z renders as a blank coin
## from every angle and no frame check would say why. `show_face` is then
## called and the instance it made is graded — unshaded, vertex-coloured, one
## live face — so a rig that quietly makes nothing fails here rather than in a
## drive where nobody was looking at the back seat.
func _check_the_passenger_can_make_a_face(car: Node3D) -> void:
	var before: int = _failed
	var emote := _running(car, EMOTE_SCRIPT) as Node3D
	if emote == null:
		_problem("no node in %s runs %s" % [SCENE_PATH, EMOTE_SCRIPT])
		return
	var door := _running(car, DOOR_SCRIPT) as Node3D
	if emote.get_parent() != car:
		_problem("%s is not a direct child of the car" % emote.name)
	if door != null:
		if signf(emote.position.x) != signf(door.position.x):
			_problem("%s is not on the passenger door's side of the car" % emote.name)
		if emote.position.z <= door.position.z:
			_problem("%s is ahead of the door hinge, not in the rear seat" % emote.name)
	if emote.position.y <= 0.0:
		_problem("%s sits at or under the floor" % emote.name)
	var scenes: Array[PackedScene] = [emote.grin, emote.angry, emote.hurt]
	var labels: PackedStringArray = ["grin", "angry", "hurt"]
	for face: int in scenes.size():
		var packed: PackedScene = scenes[face]
		var label: String = labels[face]
		if packed == null:
			_problem("%s has no %s scene assigned" % [emote.name, label])
			continue
		var live_before: int = emote.live()
		emote.show_face(face)
		if emote.live() != live_before + 1:
			_problem("show_face(%s) put up %d faces, not one" % [label, emote.live() - live_before])
			continue
		var instance := emote.get_child(emote.get_child_count() - 1) as Node3D
		var mesh: MeshInstance3D = _body_under(instance)
		if mesh == null or mesh.mesh == null:
			_problem("the %s scene has no MeshInstance3D with a mesh" % label)
			continue
		var bounds: AABB = mesh.mesh.get_aabb()
		var behind: float = bounds.end.z
		var proud: float = -bounds.position.z
		if not proud > behind:
			_problem(
				(
					"the %s face is built on +Z (%.3f proud, %.3f behind); look_at shows -Z"
					% [label, proud, behind]
				)
			)
		var material := mesh.material_override as StandardMaterial3D
		if material == null:
			_problem("the %s face has no material override; it would be lit as a surface" % label)
		elif material.shading_mode != BaseMaterial3D.SHADING_MODE_UNSHADED:
			_problem("the %s face is shaded; a glyph is unshaded" % label)
		elif not material.vertex_color_use_as_albedo:
			_problem("the %s face ignores its vertex colours" % label)
	if _failed == before:
		print("  ok    the passenger's face pops from the rear seat, built to face the camera")


## The instance uniforms the renderer will actually dispatch on, by name and
## Variant type.
##
## ⚠️ **Asked of the mesh rather than of the shader source, and the two are not
## the same claim.** `set_instance_shader_parameter` matches against this list; a
## name that is in the text but not in here is still a silent no-op. Instance-
## scope uniforms are also **excluded** from `Shader.get_shader_uniform_list()`,
## so the two lists are complementary and each is the authority for its own
## scope — which is why `sun_toward` is checked against the other one.
func _declared_instance_uniforms(body: MeshInstance3D) -> Dictionary:
	var declared: Dictionary = {}
	for property: Dictionary in body.get_property_list():
		var property_name: String = str(property.get("name", ""))
		if property_name.begins_with(INSTANCE_PREFIX):
			declared[property_name.trim_prefix(INSTANCE_PREFIX)] = int(property.get("type", 0))
	return declared


## Every channel the script writes has to be a channel the renderer knows about.
##
## A name the renderer does not list is the silent failure this whole tool exists
## for: `set_instance_shader_parameter` reports nothing, the default `vec4(0.0)`
## stands, and every lamp on the car stays dark.
##
## Returns how many switched circuits the payload can address — the widths of the
## declared vectors added up, which is what the shader's `CIRCUIT_COUNT` derives
## the same way — or **-1 where a channel is missing outright**. ⚠️ The sentinel
## is not tidiness: a lost name silently narrows the sum, and the mesh check would
## then report the car's own lenses as asking for too much. One defect, one
## message, and the message names the shader rather than the mesh.
func _check_the_switched_channels_reach_the_shader(declared: Dictionary) -> int:
	var before: int = _failed
	var channels: int = 0
	var missing: bool = false
	var written: PackedStringArray = _channel_names()
	if written.is_empty():
		_problem(
			"%s names no %s* channel constant to write" % [LAMPS_SCRIPT, CHANNEL_CONSTANT_PREFIX]
		)
		missing = true
	for channel: String in written:
		if not declared.has(channel):
			_problem(
				(
					"%s writes '%s', which %s does not declare as an instance uniform"
					% [LAMPS_SCRIPT, channel, SHADER_PATH]
				)
			)
			missing = true
			continue
		var width: int = _slots(int(declared[channel]))
		if width == 0:
			_problem(
				(
					"'%s' is declared as %s, which carries no countable circuits"
					% [channel, type_string(int(declared[channel]))]
				)
			)
			missing = true
			continue
		channels += width
	if _failed == before:
		print("  ok    %s reach the shader, %d circuits wide" % [", ".join(written), channels])
	return -1 if missing else channels


## The sun belongs to the material, not to the car.
##
## One sun, and every car agreeing about where it is — so `sun_glint.gd` writes it
## with `set_shader_parameter`. ⚠️ Declared per instance instead, that write would
## be taken in silence and the glint would never move, which is the mirror image
## of the lamp channels' failure and just as invisible.
func _check_the_sun_belongs_to_the_material(declared: Dictionary, material: ShaderMaterial) -> void:
	var sun: String = _constant(GLINT_SCRIPT, "PARAMETER")
	if sun.is_empty():
		_problem("%s names no PARAMETER constant" % GLINT_SCRIPT)
	elif declared.has(sun):
		_problem("'%s' is an instance uniform; %s writes it to the material" % [sun, GLINT_SCRIPT])
	elif material == null:
		# The body check already reported why there is no material to ask.
		pass
	elif not _is_material_uniform(material, sun):
		_problem("%s writes '%s', which %s does not declare" % [GLINT_SCRIPT, sun, SHADER_PATH])
	else:
		print("  ok    '%s' is one uniform on the shared material, not one per car" % sun)


## The `UV` payload the shader reads has to survive the import.
##
## `UV.y` is the surface marker and `UV.x` the switched circuit, both `floor()`ed
## in the vertex stage — so a value the importer moved off an integer selects a
## different branch, and a circuit past the payload is dropped by the shader's
## bounds guard and ships dark.
func _check_the_payload_survived_the_import(body: MeshInstance3D, channels: int) -> void:
	var before: int = _failed
	var circuits: Dictionary = {}
	var fractional: int = 0
	var stray_markers: int = 0
	var unreachable: int = 0
	var switched_bodywork: int = 0
	var vertices: int = 0

	for surface: int in body.mesh.get_surface_count():
		var arrays: Array = body.mesh.surface_get_arrays(surface)
		# Typed through a `Variant`, because a surface with no UVs holds `null`
		# here and assigning that to a typed array is a run-time error — which
		# kills the coroutine where it stands and leaves `quit()` uncalled.
		var payload: Variant = arrays[Mesh.ARRAY_TEX_UV]
		if typeof(payload) != TYPE_PACKED_VECTOR2_ARRAY:
			_problem(
				(
					"%s surface %d carries no UVs, so it carries no shader payload"
					% [body.name, surface]
				)
			)
			continue
		var uvs: PackedVector2Array = payload
		vertices += uvs.size()
		for uv: Vector2 in uvs:
			if uv.x != floorf(uv.x) or uv.y != floorf(uv.y):
				fractional += 1
			if uv.y < 0.0 or uv.y > MARKER_LAST:
				stray_markers += 1
			if uv.x == CIRCUIT_NONE:
				continue
			circuits[uv.x] = true
			# ⚠️ **Bounded at both ends, because the shader's guard is.** It drops
			# `channel < 0` exactly as hard as `channel >= CIRCUIT_COUNT`, so a
			# negative circuit is a permanently dark lens — and it would otherwise
			# sail past an upper-bound test and be reported as `ok`.
			if channels >= 0 and (uv.x < 1.0 or uv.x > float(channels)):
				unreachable += 1
			if uv.y != MARKER_LAMP:
				switched_bodywork += 1

	if fractional > 0:
		_problem(
			"%d vertices carry a fractional marker or circuit; the shader floors both" % fractional
		)
	if stray_markers > 0:
		_problem(
			(
				"%d vertices carry a marker outside 0-%.0f, which takes the paint branch"
				% [stray_markers, MARKER_LAST]
			)
		)
	if unreachable > 0:
		_problem(
			(
				"%d vertices ask for a circuit outside the 1-%d the payload carries"
				% [unreachable, channels]
			)
		)
	if switched_bodywork > 0:
		# The shader reads `UV.x` only inside its `MARKER_LAMP` branch, so a
		# circuit on bodywork is never switched — the same rule `_check_wiring`
		# holds in the generator, asked here of what Godot actually imported.
		_problem(
			"%d switched vertices are not lenses, so nothing ever lights them" % switched_bodywork
		)
	if circuits.is_empty():
		_problem("no vertex carries a circuit at all; every lens on the car is unswitched")
	if _failed == before:
		var found: Array = circuits.keys()
		found.sort()
		print("  ok    %d vertices imported carrying circuits %s, lenses only" % [vertices, found])


## The rig has to hang where the script goes looking for its parts.
##
## Both conditions are `assert`s in `vehicle_lamps.gd`, and asserts are stripped
## from release builds — so a scene that fails these ships a car whose lamps never
## switch rather than a car that refuses to start.
func _check_the_rig_hangs_where_the_script_looks(
	car: Node3D, lamps: Node3D, material: ShaderMaterial
) -> void:
	# ⚠️ **`VehicleController.above` itself, not a walk that looks like it.**
	# `vehicle_lamps.gd` resolves its car with exactly this call, and it matches by
	# *type* where a hand-rolled walk would match by script path — so a roster car
	# on a controller subclass finds its car fine and would fail a copy. Reached
	# through `call()` on a `load`ed script rather than by naming the global, which
	# is `verify_beam_budget.gd`'s idiom and for the same fresh-clone reason.
	var controller := load(CONTROLLER_SCRIPT) as GDScript
	if controller == null:
		_problem("%s did not load" % CONTROLLER_SCRIPT)
	elif controller.call(&"above", lamps) == null:
		_problem("the lamp rig has no %s above it to read the car from" % CONTROLLER_SCRIPT)
	else:
		print("  ok    the lamp rig sits under the controller it reads")

	var glint: Node = _running(car, GLINT_SCRIPT)
	if glint == null:
		_problem("no node in %s runs %s" % [SCENE_PATH, GLINT_SCRIPT])
		return
	# A glint written to a material nobody draws is invisible in every automated
	# check this project has, which is `sun_glint.gd`'s own argument for assigning
	# it in the scene rather than looking it up.
	var fed := glint.get("material") as ShaderMaterial
	if fed == null:
		_problem("%s has no material assigned; the taxi's glint tracks nothing" % glint.name)
	elif material == null:
		# The body wears no shader at all, which is already reported. There is
		# nothing to compare against, and ⚠️ an `ok` here would be a claim about
		# the body that the check above has just refuted.
		pass
	elif fed != material:
		# Against the material the body was *found* wearing, so this cannot pass by
		# agreeing with a constant while the car renders with something else.
		_problem(
			"%s feeds %s, which is not what the body renders with" % [glint.name, fed.resource_path]
		)
	else:
		print("  ok    the glint is fed into the material the body renders with")


## The thrown beams have to be authored dark, and aimed at the road.
##
## ⚠️ **`spot_angle` is Godot's *half* angle, and the cone must not reach above
## horizontal.** `P3-11e` shipped 7° down against an 11° half-angle first, which
## put the top of the beam 4° **up**: it lit a dome climbing the screen and read,
## correctly, as a light shining upward. Today that number is guarded by a comment
## in a `.tscn`, and Godot strips those on any editor resave.
func _check_the_beams_point_at_the_road(car: Node3D) -> void:
	# The same search `vehicle_lamps.gd` runs, so this counts the lights the
	# script would actually drive.
	var spots: Array[Node] = car.find_children("*", "SpotLight3D", true, false)
	if spots.is_empty():
		_problem("the player's taxi throws no beams; %s found no SpotLight3D" % SCENE_PATH)
		return
	var before: int = _failed
	var worst: float = -180.0
	for node: Node in spots:
		var beam := node as SpotLight3D
		if beam.visible:
			# `_apply_beam` puts them out on the first `_ready`, but only a car
			# with a lamp rig runs one — and a roster model authored lit would
			# drive through daylight on main beam until something switched it.
			_problem("%s is authored visible; beams are switched on, never off" % beam.name)
		if beam.light_energy <= 0.0 or beam.spot_range <= 0.0:
			_problem(
				(
					"%s throws nothing: energy %.2f over %.2f m"
					% [beam.name, beam.light_energy, beam.spot_range]
				)
			)
		var facing: Vector3 = (-_basis_in(beam, car).z).normalized()
		var top: float = rad_to_deg(asin(clampf(facing.y, -1.0, 1.0))) + beam.spot_angle
		if top >= 0.0:
			_problem(
				(
					"%s reaches %.2f° above horizontal, so part of it never meets the road"
					% [beam.name, top]
				)
			)
		worst = maxf(worst, top)
	if _failed == before:
		print(
			(
				"  ok    %d beams authored dark, topping out %.2f° below horizontal"
				% [spots.size(), -worst]
			)
		)


## The instance-uniform names `vehicle_lamps.gd` writes, in declaration order.
##
## ⚠️ **Left in declaration order, never sorted.** `vehicle_body.gdshader` states
## that the *ordering* of the circuits is the contract and the split into two
## vectors is not, so a sorted list would print `lamp_front, lamp_lit` and read as
## the reverse of the wiring it is reporting on.
func _channel_names() -> PackedStringArray:
	var names: PackedStringArray = []
	var constants: Dictionary = _constants(LAMPS_SCRIPT)
	for key: Variant in constants:
		if str(key).begins_with(CHANNEL_CONSTANT_PREFIX):
			names.append(str(constants[key]))
	return names


## How many switched circuits a channel of this Variant type carries.
##
## Written as a lookup rather than assumed to be four, because the seam between
## `lamp_lit` and `lamp_front` is where GLSL put it rather than where the car
## divides — `vehicle_body.gdshader` says so — and a widened payload should be
## counted, not re-asserted.
##
## `TYPE_COLOR` is four as well: a `vec4` carrying a `: source_color` hint arrives
## here as a colour, and it is still four channels a circuit can be indexed out of.
func _slots(type: int) -> int:
	match type:
		TYPE_FLOAT:
			return 1
		TYPE_VECTOR2:
			return 2
		TYPE_VECTOR3:
			return 3
		TYPE_VECTOR4, TYPE_COLOR:
			return 4
	return 0


func _is_material_uniform(material: ShaderMaterial, uniform: String) -> bool:
	for property: Dictionary in material.shader.get_shader_uniform_list(false):
		if str(property.get("name", "")) == uniform:
			return true
	return false


## The first node at or below `branch` running the script at `path`.
func _running(branch: Node, path: String) -> Node:
	if _runs(branch, path):
		return branch
	for node: Node in branch.find_children("*", "", true, false):
		if _runs(node, path):
			return node
	return null


func _runs(node: Node, path: String) -> bool:
	var script := node.get_script() as Script
	return script != null and script.resource_path == path


## The mesh `vehicle_lamps.gd` would switch — its own search, first hit and all,
## because grading a different mesh than the script writes to would pass while the
## car stayed dark.
func _body_under(lamps: Node3D) -> MeshInstance3D:
	var found: Array[Node] = lamps.find_children("*", "MeshInstance3D", true, false)
	if found.is_empty():
		return null
	return found[0] as MeshInstance3D


## `node`'s basis in `ancestor`'s space.
##
## Accumulated by hand because `global_transform` returns identity and pushes an
## error outside the tree, and nothing here is ever added to one — the same trap
## `mesh_contract.gd` documents for bounds.
func _basis_in(node: Node3D, ancestor: Node3D) -> Basis:
	var basis: Basis = node.transform.basis
	var walker: Node = node.get_parent()
	while walker != null and walker != ancestor:
		var spatial := walker as Node3D
		if spatial != null:
			basis = spatial.transform.basis * basis
		walker = walker.get_parent()
	return basis
