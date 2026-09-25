## Runs a scene from this project, drives it with scripted input, and writes
## screenshots — without a human at the keyboard.
##
## Invoked through `drive.sh`, which supplies the exit code Godot will not. See
## that script before running this one by hand.
##
##     godot --path game --script <this file> -- --scene=res://... --seconds=6
##
## Godot accepts an absolute filesystem path for `--script`, so this lives with
## the skill rather than in `game/tools/`: it is agent tooling, and keeping it
## out of `game/` keeps it out of `tools/check.sh`'s gdformat sweep and out of
## the exported PCK. It does *not* escape the engine's warning settings —
## `project.godot` promotes 21 warnings to errors, and that applies at load time
## wherever the script sits, so a slip here surfaces as `SCRIPT ERROR` and
## `drive.sh` catches it.
##
## `--script` boots this SceneTree in place of the main loop. Autoloads are
## still registered — but on the *first frame*, not before, so `root.has_node`
## in `_init` reports false and `InputRouter` is unreachable until then. That is
## why everything below happens in a deferred coroutine.
extends SceneTree

const Manifest = preload("res://scripts/city/city_manifest.gd")
const Fares = preload("res://scripts/city/generated_fares.gd")
const Regions = preload("res://scripts/city/generated_regions.gd")
const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const Spawn = preload("res://scripts/city/road_spawn.gd")

const DEFAULT_SCENE: String = "res://scenes/main.tscn"

## Sim time between telemetry lines.
const REPORT_EVERY_S: float = 1.0

## Screenshots are sampled on a grid this many points across and checked for
## flatness. A run that renders nothing still writes a valid PNG — of one flat
## colour — and would otherwise be reported as a success with a picture to
## prove it. Cheap: 1024 reads against a 1920x1080 image.
const FLATNESS_SAMPLES: int = 32

## Fewer distinct colours than this in that grid and the frame is called blank.
##
## A weak check by design, and it must not be mistaken for a strong one:
## measured, an empty world with no city built still scores 66 on its sky
## gradient alone. This catches a dead renderer, nothing subtler. `FALL_LIMIT_M`
## is what catches the empty world.
const FLATNESS_MIN_COLOURS: int = 3

## How far below its spawn the car may get before the run is called a failure.
##
## Has to clear the deepest road under the start line before it can be trusted:
## the Central–Wan Chai Bypass Tunnel bottoms out 15.7 m below the HKCEC spawn,
## so anything under about 16 m would fail an honest drive into it.
##
## Above `drive_harness.gd`'s 25 m respawn margin on purpose. In `city_drive`
## the harness catches the car first and this never fires, which is the point:
## it is the backstop for runs where the harness is absent (`city_preview`) or
## has switched itself off — and it switches itself off in exactly the case
## worth catching, a clone with no generated assets, where there is no collider,
## the car drops through the void, and a screenshot of empty sky sails past the
## flatness check.
const FALL_LIMIT_M: float = 30.0

## How long a capture waits for the renderer before giving up, in physics ticks.
##
## Bounded because an unbounded `await` on a signal that never arrives is the
## one failure mode with no exit code at all: no output, no error, nothing for
## `drive.sh` to read. The headless guard below names the one cause we can
## predict; this covers the rest.
const CAPTURE_TIMEOUT_TICKS: int = 600

var _scene_path: String = DEFAULT_SCENE
var _seconds: float = 6.0
var _shot_times: Array[float] = []
var _out_dir: String = ""
## Each entry is [action: StringName, start_s: float, end_s: float].
var _holds: Array[Array] = []
## Non-finite until `--camera` / `--look` say otherwise, so "unset" needs no
## second flag and cannot be confused with the origin.
var _camera_pos: Vector3 = Vector3.INF
var _look_at: Vector3 = Vector3.INF
## `--spawn-fare=<region>/<id>`, split. Empty until given, which leaves the
## scene's own authored `spawn_fare_id` alone — so a run without the flag is the
## run it always was.
var _spawn_region: String = ""
var _spawn_fare_id: String = ""
var _failures: PackedStringArray = []
var _vehicle: Node3D = null
var _spawn_y: float = 0.0
## `--spawn-at=x,y,z` and `--spawn-facing=x,y,z`: put the car at a point in
## engine metres facing another, after the harness has placed it — the one way
## to start a drive on a deck, where no fare node stands (`P3-51`). Unset
## until given; NaN is "not given".
var _spawn_at := Vector3(NAN, NAN, NAN)
var _spawn_facing := Vector3(NAN, NAN, NAN)
## Latched when the run has learned everything it is going to. Stops the loop
## rather than simulating a wrecked physics state to the end of its clock, and
## keeps one cause from printing one failure a second for the whole run.
var _aborted: bool = false
## `--trace=<file>`: one line per physics tick of the car's full-precision state,
## plus one line per collision body entering the tree, each stamped with the tick.
## Built to find the first tick two runs part at, and what arrived just before —
## the 1 s `%.2f` report cannot say either. Empty is off.
var _trace_path: String = ""
## Layer ids `--hide-layers` names, and how many nodes were hidden for them.
var _hidden_layers: PackedStringArray = []
var _hidden_count: int = 0
## Open for the whole run and written a line at a time, so a run that hangs or
## crashes — the one most worth diffing — still leaves its trace behind.
var _trace_file: FileAccess = null
var _trace_lines: int = 0
## Built once; only `from` and `to` move tick to tick.
var _trace_query: PhysicsRayQueryParameters3D = null
## `Engine.get_physics_frames()` when the timeline started; -1 before `_drive`.
## A field because the trace's body handlers stamp ticks during `_boot`.
var _first_tick: int = -1
## Cleared by `_shoot` once the renderer has actually drawn. A field rather than
## a local because the signal handler cannot write to a local — see below.
var _capture_pending: bool = false


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	# One frame for the engine to register autoloads and open the window.
	await process_frame

	var instance: Node = await _boot()
	if instance != null:
		await _drive()
		_release_everything()
	_close_trace()

	# The single exit. `quit()` is reached only through here, so an early return
	# that forgets it would leave the process running for ever with no output —
	# the same silent hang CAPTURE_TIMEOUT_TICKS exists to kill.
	_finish()


## Everything that has to go right before the scene can be driven. Returns the
## scene instance, or null with the reason already recorded.
func _boot() -> Node:
	if not _parse_args():
		return null

	# Measured: under --headless, `RenderingServer.frame_post_draw` never fires,
	# because the dummy driver never draws one. Refusing up front turns a ten
	# second wait and a vague timeout into a one-line message. Telemetry-only
	# runs are still fine headless, and faster for it, so this is not a blanket
	# ban.
	if DisplayServer.get_name() == "headless" and not _shot_times.is_empty():
		_fail("--headless cannot screenshot — it never draws a frame")
		return null

	print("scene:   ", _scene_path)
	print("seconds: %.2f" % _seconds)
	print("out:     ", _out_dir)
	if not _shot_times.is_empty():
		print("shots:   ", _shot_times)

	# `load_manifest` has already pushed the reason and the command that fixes
	# it — and for a stale schema that reason is *not* the missing-file hint, so
	# repeating one here would name the wrong fix half the time. Stronger than
	# testing the file exists: a `city.json` left over from an older build parses
	# and then fails much later, as something unrelated.
	var manifest: Manifest = Manifest.load_manifest()
	if manifest == null:
		_fail("no usable city at %s — see the reason above" % Manifest.path())
		return null
	if not _spawn_fare_id.is_empty() and not _spawn_fare_resolves(manifest):
		return null

	if not ResourceLoader.exists(_scene_path):
		_fail("no such scene: %s" % _scene_path)
		return null

	var packed: PackedScene = load(_scene_path)
	if packed == null:
		_fail("could not load %s" % _scene_path)
		return null

	if not _trace_path.is_empty():
		_trace_file = FileAccess.open(_trace_path, FileAccess.WRITE)
		if _trace_file == null:
			_fail("could not write --trace %s" % _trace_path)
			return null
		# Before `add_child`, so the bodies held under the start line are logged too.
		node_added.connect(_trace_node_added)
		node_removed.connect(_trace_node_removed)

	# Before `add_child`, and by signal: `CityRegions` adds a layer node per
	# resident region from its own `_ready`, so there is no moment to walk for them.
	if not _hidden_layers.is_empty():
		node_added.connect(_hide_layer)
		print("hidden:  ", _hidden_layers)

	var instance: Node = packed.instantiate()
	# Before `add_child`: the harness places the car from its own `_ready`.
	if not _spawn_fare_id.is_empty() and not _set_spawn_fare(instance):
		instance.free()
		return null
	root.add_child(instance)
	await process_frame
	# free_look_camera.gd frames the region from _ready, so placing the camera
	# any earlier than this would be overwritten by it.
	_place_camera(instance)

	_vehicle = _find_vehicle(instance)
	if _vehicle != null and _spawn_at.is_finite():
		var forward: Vector3 = _spawn_facing - _spawn_at
		forward.y = 0.0
		if not _spawn_facing.is_finite() or forward.is_zero_approx():
			_fail("--spawn-at needs a --spawn-facing point that is not above or below it")
			return null
		_vehicle.place_at(Transform3D(Spawn.basis_facing(forward.normalized()), _spawn_at))
		print("spawn:   at ", _spawn_at, " facing ", _spawn_facing)
	if _vehicle != null:
		_spawn_y = _vehicle.global_position.y
		print("vehicle: ", _vehicle.name, " at ", _vehicle.global_position)
	return instance


## Steps the scene on the physics clock, applying the input timeline and
## capturing frames as their times come up.
##
## Time is read from the engine's physics-frame counter rather than accumulated
## per iteration, so it stays true across anything that parks the coroutine for
## more than one tick — a screenshot, a slow render frame, a batch of catch-up
## steps. An accumulator counted those ticks as one and let the timeline drift
## under exactly the load it was supposed to be immune to.
func _drive() -> void:
	var step: float = 1.0 / float(Engine.physics_ticks_per_second)
	_first_tick = Engine.get_physics_frames()
	var shots: Array[float] = _shot_times.duplicate()
	var next_report: float = 0.0
	var t: float = 0.0

	while t < _seconds and not _aborted:
		_trace_tick()
		_apply_holds(t)

		if not shots.is_empty() and t >= shots[0]:
			await _capture_next_frame(shots.pop_front())

		if t >= next_report:
			_report(t)
			while next_report <= t:
				next_report += REPORT_EVERY_S

		await physics_frame
		t = float(Engine.get_physics_frames() - _first_tick) * step

	if _aborted:
		return
	_report(t)

	# A shot due on the last tick falls between the loop's final check and the
	# exit test — the clock steps 5.998 -> 6.016 and never presents 6.000 to the
	# body, so `--shots=...,6` with `--seconds=6` silently wrote nothing. Any
	# shot still queued here is either that boundary case, which the final frame
	# answers, or a time past the end of the run, which is a mistake worth
	# naming rather than a frame worth faking.
	for due: float in shots:
		if due > _seconds:
			# %s, not %g: GDScript's format has no %g, and an unknown specifier
			# is not an error — the string comes out verbatim, so the message
			# read "--shots=%g is past the end of a %g s run".
			_fail("--shots=%s is past the end of a %s s run" % [due, _seconds])
			continue
		await _capture_next_frame(due)


## Waits for the renderer to draw, then captures that frame.
##
## The capture runs inside the signal handler rather than after the await, so
## the image is the frame that was just drawn rather than whatever is current
## whenever this coroutine happens to be resumed. Waiting on `physics_frame`
## keeps the caller's clock advancing while this blocks.
func _capture_next_frame(due: float) -> void:
	var label: String = "t%05.2f" % due
	_capture_pending = true
	# A bound method, not a lambda. GDScript lambdas capture locals *by value*,
	# so a lambda that sets a local `done = true` updates its own copy and the
	# waiting loop below never sees it: measured, the screenshot was written and
	# then reported as a renderer failure. `self` is captured by reference, so a
	# field works where a local cannot.
	var shoot: Callable = _shoot.bind(label)

	RenderingServer.frame_post_draw.connect(shoot, CONNECT_ONE_SHOT)
	var waited: int = 0
	while _capture_pending and waited < CAPTURE_TIMEOUT_TICKS:
		await physics_frame
		waited += 1
	if not _capture_pending:
		return

	RenderingServer.frame_post_draw.disconnect(shoot)
	_abort("no frame drawn in %d ticks at %s — the renderer stopped" % [waited, label])


func _shoot(label: String) -> void:
	_capture(label)
	_capture_pending = false


## Presses and releases actions as their windows open and close.
##
## Driven off `Input.action_press` rather than synthesised `InputEventKey`s
## because `InputRouter` polls `Input.get_action_strength` — the action state,
## not the event queue. Pushing key events would work too and would depend on
## the keyboard bindings in project.godot staying put; this depends only on the
## action names, which are the interface the router actually documents.
##
## An action is wanted while ANY of its holds covers `t`. Deciding per hold let
## a second hold of one action release what the first had pressed on the same
## tick, so `accelerate@0.3+3 … accelerate@5.5+6` never moved until 5.5 s.
func _apply_holds(t: float) -> void:
	var wanted: Dictionary[StringName, bool] = {}
	for hold: Array in _holds:
		var covers: bool = t >= hold[1] and t < hold[2]
		wanted[hold[0]] = covers or wanted.get(hold[0], false)
	for action: StringName in wanted:
		var want: bool = wanted[action]
		if want == Input.is_action_pressed(action):
			continue
		if want:
			Input.action_press(action)
		else:
			Input.action_release(action)


## The tick relative to the timeline's start; negative while booting.
func _trace_tick_index() -> int:
	if _first_tick < 0:
		return -1
	return Engine.get_physics_frames() - _first_tick


func _trace_line(line: String) -> void:
	_trace_file.store_line(line)
	_trace_lines += 1


func _trace_tick() -> void:
	if _trace_file == null or _vehicle == null:
		return
	var tick: int = _trace_tick_index()
	var p: Vector3 = _vehicle.global_position
	var v: Vector3 = _vehicle.get("linear_velocity")
	_trace_line(
		"tick %d pos %.6f %.6f %.6f vel %.6f %.6f %.6f" % [tick, p.x, p.y, p.z, v.x, v.y, v.z]
	)
	# What stands under the car, and whose it is — a streamed body and a held one
	# are indistinguishable from the car's state alone.
	if _trace_query == null:
		_trace_query = PhysicsRayQueryParameters3D.new()
		_trace_query.exclude = [(_vehicle as CollisionObject3D).get_rid()]
	_trace_query.from = p + Vector3.UP * 2.0
	_trace_query.to = p + Vector3.DOWN * 10.0
	var hit: Dictionary = _vehicle.get_world_3d().direct_space_state.intersect_ray(_trace_query)
	if hit.is_empty():
		_trace_line("under %d none" % tick)
	else:
		_trace_line("under %d %.6f %s" % [tick, hit.position.y, (hit.collider as Node).get_path()])


## Hides a `layer_preview.gd` node named by `--hide-layers`, children and all.
## `_hidden_count` is printed at the end so a run that hid nothing says so.
func _hide_layer(node: Node) -> void:
	var spatial := node as Node3D
	if spatial != null and "layer" in spatial and _hidden_layers.has(String(spatial.get("layer"))):
		spatial.visible = false
		_hidden_count += 1


func _trace_node_added(node: Node) -> void:
	if node is CollisionObject3D:
		_trace_line("body %d %s" % [_trace_tick_index(), node.get_path()])


func _trace_node_removed(node: Node) -> void:
	if node is CollisionObject3D:
		var camera: Camera3D = root.get_viewport().get_camera_3d()
		var eye: Vector3 = camera.global_position if camera != null else Vector3.INF
		_trace_line("gone %d %s eye %s" % [_trace_tick_index(), node.get_path(), eye])


func _close_trace() -> void:
	if _trace_file == null:
		return
	# The scene is freed at quit, after this, and every body it frees would
	# otherwise arrive at a closed file.
	node_added.disconnect(_trace_node_added)
	node_removed.disconnect(_trace_node_removed)
	_trace_file.close()
	_trace_file = null
	print("trace:   %s  %d lines" % [_trace_path, _trace_lines])


func _release_everything() -> void:
	for hold: Array in _holds:
		Input.action_release(hold[0])


## What the renderer drew in the last frame it completed, as `  prims=N draws=N`.
##
## Reported every second because every performance number this project has
## written down came from a throwaway probe that was then deleted — so nobody
## could reproduce one without rewriting the probe. A driver run is already the
## reproducible thing.
##
## ⚠️ Both read **0 under `--headless`**: the dummy rasteriser draws nothing.
## Printed anyway rather than hidden, because a zero that is explained is worth
## more than a missing field someone later assumes was non-zero.
##
## ⚠️ `draws` is a budget metric from docs/ARCHITECTURE.md directly. `prims` is
## **not** — that budget is stated in *visible* triangles, and this counts every
## pass including shadows. Measured on this scene the directional shadow adds
## roughly +1x the main pass per two cascades, so treat it as a proxy that moves
## with the budget rather than the budget itself.
##
## The reading is one frame stale and unsynchronised — the project runs the
## multi-threaded render model, so this is whatever the render thread last
## wrote. Fine for a per-second harness line; not a frame-accurate sample.
##
## `phys` is the last physics tick's `_physics_process` time in milliseconds
## (`Performance.TIME_PHYSICS_PROCESS`), added for `P5-12` so a collider change
## has a per-tick cost a run can repeat. One tick, not an average — read the
## whole column.
func _rendering() -> String:
	return (
		"  prims=%d draws=%d phys=%.3fms"
		% [
			RenderingServer.get_rendering_info(
				RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME
			),
			RenderingServer.get_rendering_info(
				RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME
			),
			Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
		]
	)


func _report(t: float) -> void:
	if _vehicle == null:
		print("t=%5.2f%s" % [t, _rendering()])
		return

	var pos: Vector3 = _vehicle.global_position
	var speed: float = float(_vehicle.call("forward_speed_kph"))
	print(
		(
			"t=%5.2f  pos=(%8.2f, %7.2f, %8.2f)  speed=%7.2f kph%s"
			% [t, pos.x, pos.y, pos.z, speed, _rendering()]
		)
	)

	if not pos.is_finite():
		_abort("vehicle position went non-finite at t=%.2f — physics blew up" % t)
		return
	if pos.y < _spawn_y - FALL_LIMIT_M:
		_abort(
			(
				"vehicle fell %.1f m below its spawn by t=%.2f. %s"
				% [_spawn_y - pos.y, t, Manifest.road_missing_hint()]
			)
		)


## Writes the current frame and checks it is not a flat colour.
func _capture(label: String) -> void:
	var image: Image = root.get_texture().get_image()
	if image == null:
		_fail("viewport returned no image at %s" % label)
		return

	var path: String = _out_dir.path_join("%s.png" % label)
	var err: Error = image.save_png(path)
	if err != OK:
		_fail("could not write %s (error %d)" % [path, err])
		return

	var colours: int = _distinct_colours(image)
	print(
		(
			"shot:    %s  %dx%d  %d distinct colours"
			% [path, image.get_width(), image.get_height(), colours]
		)
	)
	if colours < FLATNESS_MIN_COLOURS:
		_fail("%s is flat (%d colours) — the scene rendered nothing" % [path, colours])


func _distinct_colours(image: Image) -> int:
	var seen: Dictionary = {}
	var w: int = image.get_width()
	var h: int = image.get_height()
	for iy: int in range(FLATNESS_SAMPLES):
		for ix: int in range(FLATNESS_SAMPLES):
			var x: int = int(float(ix) / FLATNESS_SAMPLES * w)
			var y: int = int(float(iy) / FLATNESS_SAMPLES * h)
			# Quantised to 5 bits a channel so dithering and a smooth sky
			# gradient do not read as detail.
			var c: Color = image.get_pixel(x, y)
			var key: int = (int(c.r * 31.0) << 10) | (int(c.g * 31.0) << 5) | int(c.b * 31.0)
			seen[key] = true
	return seen.size()


## Teleports the scene's camera, for framing a screenshot at a chosen spot.
##
## A teleport rather than scripted flying because `free_look_camera.gd` reads
## `Input.is_physical_key_pressed` directly rather than the action map, so
## `Input.action_press` — which is how everything else here drives the game —
## moves it not at all. Only useful in the preview scenes: in `city_drive` the
## chase camera rewrites the transform every frame, and this is silently undone.
func _place_camera(instance: Node) -> void:
	if not _camera_pos.is_finite():
		return

	var found: Array[Node] = instance.find_children("*", "Camera3D", true, false)
	if found.is_empty():
		_fail("--camera given but %s has no Camera3D" % _scene_path)
		return

	var camera: Camera3D = found[0] as Camera3D
	camera.global_position = _camera_pos
	if _look_at.is_finite():
		camera.look_at(_look_at)
	print("camera:  ", camera.global_position, " -> ", camera.global_basis.z * -1.0)


## Refuses a `--spawn-fare` naming a region that is not resident or a fare that
## region does not publish. Checked here rather than left to the harness, whose
## own fallback is a `push_warning` and the authored transform — a warning
## `drive.sh` does not fail on, so a typo would drive from the default start
## line and report success.
func _spawn_fare_resolves(manifest: Manifest) -> bool:
	var resident: PackedStringArray = Regions.resident()
	if resident == PackedStringArray([""]):
		resident = PackedStringArray([manifest.region_id])
	if not resident.has(_spawn_region):
		_fail(
			(
				"--spawn-fare names region %s, and the resident regions are %s"
				% [_spawn_region, ", ".join(resident)]
			)
		)
		return false
	if Fares.node_by_id(Fares.load_fares(Fares.path(_spawn_region)), _spawn_fare_id).is_empty():
		_fail("--spawn-fare: %s publishes no fare %s" % [_spawn_region, _spawn_fare_id])
		return false
	print("spawn:   ", _spawn_region, "/", _spawn_fare_id)
	return true


## Hands the fare id to every drive harness in the scene. Duck-typed for the
## reason `_find_vehicle` gives. A scene with none — the preview scenes — is
## refused, because the flag would otherwise do nothing and say nothing.
func _set_spawn_fare(instance: Node) -> bool:
	var set_on: int = 0
	for node: Node in instance.find_children("*", "Node3D", true, false):
		if "spawn_fare_id" in node:
			node.set("spawn_fare_id", _spawn_fare_id)
			# The frame is "" to the harness; naming it keeps one spelling.
			node.set("spawn_region", _spawn_region if _spawn_region != Regions.frame() else "")
			# On the node itself, as before the game's start moved back off its
			# stand: a named spawn is a dev position, and routes are timed from it.
			node.set("spawn_setback_m", 0.0)
			set_on += 1
	if set_on == 0:
		_fail("--spawn-fare given but %s has no drive harness" % _scene_path)
		return false
	return true


## The first VehicleController below `instance`, or null.
##
## Matched by method rather than by type because naming the type is not
## available here: `vehicle_controller.gd` reads the `InputRouter` autoload, and
## autoloads are not registered at script-compile time under `--script`, so a
## typed reference fails to compile with `Identifier not found: InputRouter` —
## the same effect `tools/check.sh` documents for `--check-only`. Duck typing
## also lets a scene with no car report the positions it does not have.
func _find_vehicle(instance: Node) -> Node3D:
	for node: Node in instance.find_children("*", "Node3D", true, false):
		if node.has_method("forward_speed_kph"):
			return node as Node3D
	return null


func _parse_args() -> bool:
	_out_dir = ProjectSettings.globalize_path("res://../build/driver").simplify_path()
	for arg: String in OS.get_cmdline_user_args():
		var bits: PackedStringArray = arg.split("=", true, 1)
		var key: String = bits[0]
		# An empty value is never meaningful and is never harmless: bare `--out`
		# resolved to the repo root and scattered PNGs beside CLAUDE.md.
		if bits.size() < 2 or bits[1].is_empty():
			_fail("%s needs a value, as %s=..." % [key, key])
			return false

		var value: String = bits[1]
		match key:
			"--scene":
				_scene_path = value
			"--seconds":
				_seconds = _to_float(key, value)
				if is_nan(_seconds):
					return false
				if _seconds <= 0.0:
					_fail("--seconds must be positive, got %s" % value)
					return false
			"--out":
				_out_dir = value
			"--shots":
				for piece: String in value.split(",", false):
					var due: float = _to_float(key, piece)
					if is_nan(due):
						return false
					_shot_times.append(due)
			"--camera":
				_camera_pos = _parse_vector(key, value)
				if not _camera_pos.is_finite():
					return false
			"--look":
				_look_at = _parse_vector(key, value)
				if not _look_at.is_finite():
					return false
			"--hold":
				if not _parse_hold(value):
					return false
			"--spawn-fare":
				var parts: PackedStringArray = value.split("/")
				if parts.size() != 2 or parts[0].is_empty() or parts[1].is_empty():
					_fail("bad --spawn-fare '%s' — want region/fare_id" % value)
					return false
				_spawn_region = parts[0]
				_spawn_fare_id = parts[1]
			"--debug-view":
				# *Applied* by the `DebugHud` autoload, which reads the command
				# line itself — it is on screen before the driver has parsed
				# anything. Only validated here, because the autoload's own
				# fallback is a `push_warning` and a full overlay, and a warning
				# is not something `drive.sh` fails on: a typo would otherwise
				# run to completion, report success, and quietly return a
				# different overlay from the one asked for.
				if not ["off", "minimal", "full"].has(value):
					_fail("--debug-view=%s is not off, minimal or full" % value)
					return false
			"--hud":
				# Same shape as `--debug-view` above, and validated here for the
				# same reason: `hud.gd` reads the command line itself and its own
				# fallback is to leave the HUD ON, so a typo would silently
				# return the frame the caller was trying not to take. ⚠️ A clean
				# art-review frame now needs BOTH flags — the player's HUD is not
				# dev chrome and `--debug-view=off` does not touch it.
				if not ["off", "on"].has(value):
					_fail("--hud=%s is not off or on" % value)
					return false
			"--minimap":
				# `hud.gd` reads this one too, and falls back to leaving the map
				# ON — so a typo would hand `P3-9` the aid its test disables.
				if not ["off", "on"].has(value):
					_fail("--minimap=%s is not off or on" % value)
					return false
			"--menu":
				# `start_menu.gd` reads this one itself and falls back to showing
				# the menu, under which the car is parked — so a typo would run a
				# six-second drive that never moved and report success.
				# `drive.sh` appends `--menu=off` unless a run names the flag.
				if not ["off", "on"].has(value):
					_fail("--menu=%s is not off or on" % value)
					return false
			"--touch":
				# `input_router.gd` reads this one itself, so this is validation
				# and nothing else — the same shape as the two above, for the
				# same reason: the router's fallback is to leave touch off, so a
				# typo would run to completion and report success having driven
				# the car with the keyboard the caller was trying not to use.
				#
				# ⚠️ **One finger.** It cannot press two thumbs at once, so it
				# exercises steering or the throttle and never their interaction;
				# `verify_input.gd` covers that, and `P0-3b`'s handset is what
				# actually settles whether the scheme is usable.
				if not ["mouse", "off"].has(value):
					_fail("--touch=%s is not mouse or off" % value)
					return false
			"--spawn-at":
				_spawn_at = _parse_vector(key, value)
				if not _spawn_at.is_finite():
					return false
			"--spawn-facing":
				_spawn_facing = _parse_vector(key, value)
				if not _spawn_facing.is_finite():
					return false
			"--trace":
				_trace_path = value
			"--hide-layers":
				# What a layer COSTS a frame, as a run anyone can repeat: the same
				# drive with and without it, read off `prims` and `draws`. Held
				# against the loader's table because a misspelt layer would hide
				# nothing and report the unhidden frame as the measurement.
				for layer: String in value.split(","):
					if not GeneratedLayer.ids().has(layer):
						_fail(
							(
								"--hide-layers=%s is not one of %s"
								% [layer, ", ".join(GeneratedLayer.ids())]
							)
						)
						return false
					_hidden_layers.append(layer)
			"--asset":
				# `asset_viewer.gd` reads this one itself (`P5-22`); it is named
				# here so the scene's one flag is not refused as unknown.
				pass
			"--fares":
				# `fare_system.gd` reads this one itself (`P3-1a`), and its
				# fallback is to leave the loop ON — a typo would hand `P3-9` a
				# fare it meant to run without.
				if not ["off", "on"].has(value):
					_fail("--fares=%s is not off or on" % value)
					return false
			"--fare-seed":
				# `fare_system.gd` reads this one itself; a seed that is not an
				# int would silently randomise, and two "A/B" drives would draw
				# two destinations.
				if not value.is_valid_int():
					_fail("--fare-seed=%s is not an integer" % value)
					return false
			"--lang":
				# `locale.gd` reads this one itself (`Q142`); anything but the
				# two languages would silently read as the default.
				if not [Locale.ENGLISH, Locale.CHINESE].has(value):
					_fail("--lang=%s is not en or zh" % value)
					return false
			_:
				_fail("unknown argument: %s" % arg)
				return false

	_dedupe_shots()

	_out_dir = _from_repo_root(_out_dir)
	if not _trace_path.is_empty():
		_trace_path = _from_repo_root(_trace_path)
	if DirAccess.make_dir_recursive_absolute(_out_dir) != OK:
		_fail("could not create output directory %s" % _out_dir)
		return false
	return true


## Anchors a relative path to the repo root, not the process's working directory:
## Godot chdirs into `--path`, so a relative `--out` would resolve inside `game/`.
## Every path in this skill's docs is repo-root-relative; this makes the driver
## agree with them.
func _from_repo_root(path: String) -> String:
	if path.is_absolute_path():
		return path
	return ProjectSettings.globalize_path("res://../").simplify_path().path_join(path)


## Sorts the requested shot times and drops any that would collide.
##
## Labels are formatted to two decimals, so two shots closer than that write the
## same filename and the second silently overwrites the first. The survivors are
## printed by the caller, so nothing is dropped without saying so.
func _dedupe_shots() -> void:
	_shot_times.sort()
	var unique: Array[float] = []
	for due: float in _shot_times:
		if unique.is_empty() or due - unique[-1] >= 0.01:
			unique.append(due)
	_shot_times = unique


## Parses a number, or fails. `float("six")` is `0.0` with no error of any kind,
## which turns one typo into a zero-length run that reports success — the false
## green this whole skill is built against.
func _to_float(key: String, value: String) -> float:
	if not value.is_valid_float():
		_fail("%s wants a number, got '%s'" % [key, value])
		return NAN
	return float(value)


func _parse_vector(key: String, value: String) -> Vector3:
	var bits: PackedStringArray = value.split(",", false)
	if bits.size() != 3:
		_fail("bad %s '%s' — want x,y,z" % [key, value])
		return Vector3.INF
	for piece: String in bits:
		if not piece.is_valid_float():
			_fail("bad %s '%s' — '%s' is not a number" % [key, value, piece])
			return Vector3.INF
	return Vector3(float(bits[0]), float(bits[1]), float(bits[2]))


## `--hold=accelerate@0.5+5.0` — press `accelerate` at 0.5 s, hold 5 s.
func _parse_hold(value: String) -> bool:
	var at: PackedStringArray = value.split("@")
	if at.size() != 2:
		_fail("bad --hold '%s' — want action@start+duration" % value)
		return false
	var span: PackedStringArray = at[1].split("+")
	if span.size() != 2:
		_fail("bad --hold '%s' — want action@start+duration" % value)
		return false

	var action := StringName(at[0])
	if not InputMap.has_action(action):
		_fail("no such input action '%s' — see [input] in project.godot" % action)
		return false

	var start: float = _to_float("--hold", span[0])
	var duration: float = _to_float("--hold", span[1])
	if is_nan(start) or is_nan(duration):
		return false

	_holds.append([action, start, start + duration])
	return true


func _fail(message: String) -> void:
	_failures.append(message)


## Records a failure and stops the run — for the ones where every further second
## of simulation only repeats what is already known.
func _abort(message: String) -> void:
	_fail(message)
	_aborted = true


func _finish() -> void:
	if not _hidden_layers.is_empty():
		print("hidden:   %d layer node(s)" % _hidden_count)
		if _hidden_count == 0:
			_fail("--hide-layers hid nothing, so this run measured the unhidden frame")
	if _failures.is_empty():
		print("\nDRIVER OK")
		quit(0)
		return
	for message: String in _failures:
		printerr("  FAIL  ", message)
	printerr("DRIVER FAILED")
	quit(1)
