extends CanvasLayer
## The dev readouts, and the one key that turns them off.
##
## Three things were drawing debug chrome before this existed — `fps_counter.gd`,
## the text block in `road_graph_overlay.gd`, and that same script's 3D chevrons
## — each owning its own visibility, its own font size, and in the label's case a
## screen offset chosen by eye. A fourth readout would have been a fourth offset.
## So this owns the top-left stack, the font treatment and the state, and the
## overlays supply text and ask what to show.
##
## **The position block is the point of it.** Where the car is was only ever on
## stdout — `drive.sh` telemetry and `drive_harness.gd`'s spawn line — which is
## no use when the question is about the *frame*: a screenshot of a car halfway
## through a wall is only actionable if the picture itself says where that is.
## It is sized to survive being downscaled, because what usually reads it is a
## model rather than a person, and it carries the source-CRS grid reference as
## well as game metres so the answer can be checked against the ETL's own data.
##
## **Everything starts off**, in every build, and `F3` cycles it on. What was
## previously always on screen in a debug build — the counter, the road graph's
## text and chevrons — is now asked for. See `View` for why, and `_ready` for the
## three conditions that decide whether the key does anything at all.

## Emitted after the view changes. Deliberately carries no argument: a receiver
## asks `shows_arrows()` or `shows_readouts()` rather than matching on a state,
## so adding a view later does not break every `match` in the project.
signal view_changed

## OFF hides everything; MINIMAL keeps the two compact blocks that answer "where
## am I and is it smooth"; FULL adds the text walls and the 3D debug geometry.
##
## **OFF is the default, in every build.** Debug chrome over the frame is the
## wrong default for a game whose art direction is the deliverable: it was on the
## screen in every screenshot anyone took, including the ones judging how Wan
## Chai looks. Turning it on is a keystroke; noticing that a picture was quietly
## wrong about the city because text covered a third of it is not.
##
## Ordered least to most, but nothing may do arithmetic on that: the `[debug]`
## block promotes `int_as_enum_without_cast` to an error, so `cycle` matches.
enum View { OFF, MINIMAL, FULL }

## Cycles the view. A raw key rather than an action, deliberately: the `[input]`
## map in `project.godot` is the *game's*, and `free_look_camera.gd` already set
## the precedent that dev-only keys stay out of it.
##
## ⚠️ The consequence is that `drive.sh --hold=` cannot press this — it drives
## the action map and nothing else. Scripted runs pick a view with `--debug-view`.
const TOGGLE_KEY: Key = KEY_F3

## Chooses the view a run starts in, and forces the HUD on in a release build:
## `--debug-view=off` is how a screenshot for art review gets a clean frame.
const VIEW_ARG: String = "--debug-view="

## Kept from `fps_counter.gd`, which no longer gates itself. It now means
## `MINIMAL` — the counter plus the position block — rather than the counter
## alone, because the counter is one of this HUD's views and two gates over one
## overlay is what created the mess this file exists to end.
const FPS_ARG: String = "--fps"

## Font sizes, in pixels at the 1920x1080 design resolution.
##
## Constants rather than a `.tres`, and that is a deliberate reading of hard rule
## 4 in `CLAUDE.md`: tuning values are *gameplay* values — handling curves, fare
## timers — which are balanced by someone who should not need a code change.
## Nothing about dev chrome is balanced, and a resource for it would be a file to
## keep in sync for no reader.
##
## `SIZE_POSITION` is set by what a vision model can still read after a 1920-wide
## screenshot is downscaled to fit a context window; the other two by what fits
## beside it without becoming the picture.
const SIZE_POSITION: int = 40
const SIZE_STAT: int = 28
const SIZE_READOUT: int = 22

## `View` spelled for the command line and for stdout, indexed by the enum. One
## table in one direction: a second, inverse one drifts, and its default arm
## silently renames a view it does not know.
const VIEW_NAMES: PackedStringArray = ["off", "minimal", "full"]

const _MARGIN := Vector2(16.0, 12.0)

var view: View = View.OFF

var _stack: VBoxContainer
var _position: Label
## The registered labels, in a box of their own so their shared visibility is one
## property rather than a list this has to keep in step with its own children.
var _readout_box: VBoxContainer
var _subject: Node3D = null
var _manifest: CityManifest = null
var _looked_for_manifest: bool = false


func _ready() -> void:
	layer = 127
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build()

	# Headless overrides everything, including an explicit `--debug-view`: the
	# dummy rasteriser draws nothing, so the only thing an overlay could do there
	# is cost the verify tools a tree walk and a second parse of `city.json`
	# every frame. Every check.sh tool and every telemetry run is headless.
	var requested: String = cmdline_value(VIEW_ARG)
	var counter_asked_for: bool = _cmdline().has(FPS_ARG)
	var forced: bool = not requested.is_empty() or counter_asked_for
	if DisplayServer.get_name() == "headless" or (not OS.is_debug_build() and not forced):
		# Not freed, unlike the counter this replaced the gate of: two scripts
		# hold a reference to this singleton, and a freed autoload turns their
		# every call into a runtime error. Parked instead — no input, no frame
		# cost, nothing drawn. `_set_view` is still needed: `_build` leaves the
		# stack visible.
		set_process_input(false)
		_set_view(View.OFF)
		return

	var wanted: View = View.OFF
	if not requested.is_empty():
		wanted = _parse_view(requested)
	elif counter_asked_for:
		wanted = View.MINIMAL
	_set_view(wanted)


func _build() -> void:
	_stack = VBoxContainer.new()
	_stack.name = "Stack"
	_stack.set_anchors_preset(Control.PRESET_TOP_LEFT)
	_stack.offset_left = _MARGIN.x
	_stack.offset_top = _MARGIN.y
	_stack.add_theme_constant_override(&"separation", 12)
	# A full-width Control over the game would otherwise swallow clicks meant
	# for it. Nothing here is interactive.
	_stack.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_stack)

	_position = Label.new()
	_position.name = "Position"
	style_label(_position, SIZE_POSITION)
	_stack.add_child(_position)

	_readout_box = VBoxContainer.new()
	_readout_box.name = "Readouts"
	_readout_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stack.add_child(_readout_box)


## The house style for debug text: white on a heavy black outline.
##
## The outline is what makes it readable, not the colour. This text is drawn over
## whatever the camera is pointing at — pale carriageway, dark building faces,
## bright sky — and white-on-white is the failure mode a screenshot reports as
## "the overlay is missing". Scaled with the font so a small label is not ringed
## like a large one.
static func style_label(label: Label, size: int) -> void:
	label.add_theme_font_size_override(&"font_size", size)
	label.add_theme_color_override(&"font_color", Color.WHITE)
	label.add_theme_color_override(&"font_outline_color", Color.BLACK)
	label.add_theme_constant_override(&"outline_size", maxi(4, roundi(float(size) * 0.22)))


## Put a caller's label in the top-left stack, under the position block.
##
## The caller keeps ownership of the text and hands over the placement. Pair it
## with `detach_readout` in `_exit_tree`: a label parented here outlives the
## scene that made it, and would otherwise stack up one per scene change.
##
## ⚠️ Reaches `_build`'s nodes, so a caller has to run after this autoload's
## `_ready` — which is every scene node, and any autoload listed below it in
## `project.godot`. `style_label` is static for exactly that reason and this is
## not.
func attach_readout(label: Label) -> void:
	style_label(label, SIZE_READOUT)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_readout_box.add_child(label)


func detach_readout(label: Label) -> void:
	label.queue_free()


## The compact blocks: frame rate, and where the camera or the car is.
func shows_stats() -> bool:
	return view != View.OFF


## The registered text blocks — several lines each, and the first thing in the
## way when the question is what the city looks like.
func shows_readouts() -> bool:
	return view == View.FULL


## Debug geometry drawn in the world rather than on the screen: the road graph
## overlay's centreline, lane cross and travel chevron.
func shows_arrows() -> bool:
	return view == View.FULL


## OFF to MINIMAL to FULL and back to OFF — outwards from the clean frame it
## starts on, so the first press of an unfamiliar key adds the least.
##
## Announced on stdout because a scripted run records that stream, and "the
## overlay was off" is otherwise a silent reason for a screenshot to disagree
## with the last one.
func cycle() -> void:
	match view:
		View.OFF:
			_set_view(View.MINIMAL)
		View.MINIMAL:
			_set_view(View.FULL)
		_:
			_set_view(View.OFF)
	print("debug view: %s" % name_of(view))


static func name_of(which: View) -> String:
	return VIEW_NAMES[which]


func _input(event: InputEvent) -> void:
	var key := event as InputEventKey
	# Presses only, and not the repeats a held key generates — an echo would
	# cycle the view several times per second.
	if key == null or not key.pressed or key.echo or key.keycode != TOGGLE_KEY:
		return
	cycle()
	get_viewport().set_input_as_handled()


func _process(_delta: float) -> void:
	# `is_instance_valid` rather than a null check: on a scene change the node
	# this was following is freed, and the stale reference reads as non-null.
	if not is_instance_valid(_subject):
		_subject = null
	# Re-asked every frame while it is following a camera, so a scene that spawns
	# its car late is picked up rather than reported as a camera for ever. Both
	# lookups are O(1), which is why this needs no throttle.
	if (_subject as VehicleController) == null:
		_subject = _find_subject()

	# Rebuilt every frame, deliberately. The block exists so a screenshot states
	# where it was taken, and a throttled one would be stating where the car was
	# up to a tenth of a second earlier — 1.5 m at 56 kph, which is the width of
	# the lane the whole readout is there to argue about. It costs a TextServer
	# reshape of two lines per frame, on an overlay that is off unless asked for.
	_position.text = _describe(_subject)


## What to report the position of: the car if there is one, else whatever camera
## is rendering.
##
## The fallback is not a consolation prize — it is what makes `--camera=x,y,z`
## in the preview scenes self-documenting, since the frame then states the
## coordinates it was shot from.
func _find_subject() -> Node3D:
	# Not a ternary: `VehicleController` and `Camera3D` are only compatible as
	# `Node3D`, and the engine's checker rejects a ternary whose arms are two
	# unrelated types even where the return type resolves them.
	var car: VehicleController = VehicleController.first_in(get_tree())
	if car != null:
		return car
	return get_viewport().get_camera_3d()


func _describe(subject: Node3D) -> String:
	if subject == null:
		return "no camera and no vehicle to locate"

	var at: Vector3 = subject.global_position
	var car := subject as VehicleController
	# Fixed field widths so the digits do not shuffle sideways every frame. The
	# default theme font is proportional, so this steadies the columns rather
	# than aligning them exactly.
	var line: String = (
		"%s  X %9.2f  Y %8.2f  Z %9.2f" % ["taxi" if car != null else "cam", at.x, at.y, at.z]
	)

	var facts: PackedStringArray = []
	var grid: Vector3 = _grid_of(at)
	if grid != Vector3.INF:
		facts.append("grid %.1fE %.1fN" % [grid.x, grid.y])
	# A compass bearing, not the engine's Y rotation. Taken from the basis rather
	# than from velocity so it still answers at a standstill, which is when
	# someone is most likely to be reading it.
	var forward: Vector3 = -subject.global_transform.basis.z
	facts.append("hdg %03d" % roundi(CityManifest.bearing_deg(forward)))
	if car != null:
		facts.append("%.0f kph" % car.forward_speed_kph())
	return line + "\n" + "   ".join(facts)


## The position in the source CRS, or `Vector3.INF` where there is no city to
## anchor it to — a fresh clone, or a scene running without generated assets.
func _grid_of(at: Vector3) -> Vector3:
	if _manifest == null:
		return Vector3.INF
	return _manifest.to_grid(at)


## Parse `city.json` for the three floats the grid reference needs, once.
##
## Called when the overlay first becomes visible rather than in `_ready` or on
## the first frame it draws. `RoadGraph` and `CityStreamer` each parse the same
## 70 KB document, so this is a third pass of a couple of milliseconds: charging
## it to `_ready` would make a headless tool run pay for an overlay it cannot
## show, and charging it to the first drawn frame would land it inside the window
## `drive.sh --shots=0.5` samples and inside the counter's first average.
##
## The failure is remembered, not retried: on a clone with no city there is
## nothing to wait for, and `load_manifest` has already said so.
func _learn_where_the_city_is() -> void:
	if _looked_for_manifest:
		return
	_looked_for_manifest = true
	_manifest = CityManifest.load_manifest()


func _set_view(next: View) -> void:
	view = next
	_stack.visible = shows_stats()
	_readout_box.visible = shows_readouts()
	# Nothing to compute for a hidden overlay, and this is autoload code: it runs
	# every frame for the life of the process whether or not anyone asked for it.
	set_process(shows_stats())
	if shows_stats():
		_learn_where_the_city_is()
	view_changed.emit()


static func _parse_view(requested: String) -> View:
	var found: int = VIEW_NAMES.find(requested.to_lower())
	if found < 0:
		push_warning("%s%s is not %s; showing everything" % [VIEW_ARG, requested, VIEW_NAMES])
		return View.FULL
	return found as View


## Both argument lists, because the flag arrives through either.
##
## Godot splits the command line at `--`: what comes before is the engine's and
## reaches `get_cmdline_args`, what comes after is the caller's and reaches
## `get_cmdline_user_args` alone. `drive.sh` passes everything after the dashes,
## so reading only the first list — which is what `fps_counter.gd` did — misses
## every flag a scripted run sends.
static func _cmdline() -> PackedStringArray:
	var arguments: PackedStringArray = OS.get_cmdline_args()
	arguments.append_array(OS.get_cmdline_user_args())
	return arguments


## ⚠️ **Public, like `style_label`, and for the same reason**: `hud.gd` needs a
## command-line flag before its own `_ready` has done anything, and a second
## copy of this is how `fps_counter.gd` came to read only `get_cmdline_args()`
## and miss every flag a scripted run sends. That defect is recorded in
## `_cmdline` above; a third copy would be the same one waiting to happen.
static func cmdline_value(prefix: String) -> String:
	for argument: String in _cmdline():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""
