extends Node
## The single source of player intent.
##
## Architectural rule (docs/ARCHITECTURE.md): no gameplay script reads raw
## input events. Everything reads this action set instead. That is what keeps
## touch, gamepad and keyboard from leaking into vehicle and UI code — and it is
## why the raw touch events below are handled *here*, in the one script the rule
## exempts, rather than in an overlay node that pushes values in.
##
## Sampled in _physics_process, not _process: Godot runs every physics step
## before idle processing, so a vehicle polling from _physics_process would
## otherwise read a sample one render frame stale — a guaranteed extra 16.7 ms
## of input latency, doubling whenever the render rate drops below the physics
## tick. Autoloads are the first children of root, so this runs before any
## gameplay node in the same tick.
##
## **Touch is two relative thumbs, and three of five actions** (`Q83`, `Q97`).
## The left zone steers; the right zone is one bipolar longitudinal axis,
## `accelerate` above the touch origin and `brake_reverse` below. `drift` and
## `look_back` have no touch home yet, and the note above `TOUCH_ARG` says why.

## Emitted by keyboard, gamepad, and — for these two — by nothing on touch yet.
signal drift_started
signal drift_ended
signal look_back_started
signal look_back_ended

## Steering, -1.0 (full left) to 1.0 (full right).
var steer: float = 0.0
## Throttle, 0.0 to 1.0.
var accelerate: float = 0.0
## Brake / reverse, 0.0 to 1.0.
var brake_reverse: float = 0.0
var drift: bool = false
var look_back: bool = false

## Forces full throttle whenever the brake is released. ⚠️ **No longer the touch
## default — `Q83` reversed it.** Touch drives the throttle for real, on the
## positive half of thumb 1's vertical axis, and pays no extra thumb rest for it
## because `brake_reverse` is the negative half of that same axis.
##
## Kept as the accessibility and one-handed option. Nothing sets it, so the
## `false` below is shipped behaviour on every scheme rather than a placeholder.
var auto_accelerate: bool = false

# ⬜ **What touch still does not carry, and why it is a comment rather than a
# broken control.** `drift` is settled as a held vertical offset on thumb 2
# past a threshold with hysteresis (`Q83`), and the threshold and hysteresis
# are numbers `Q83` says no desk can pick — `P2-4`'s review is blocked on
# `P0-3b` for the handset. `look_back` has never been placed at all; thumb 1's
# horizontal axis is the standing candidate.
#
# 🔴 **Thumb 2's vertical axis is therefore READ AND DISCARDED, deliberately.**
# The drift lives there and nothing else may be put on it — a second control
# borrowing the axis now is a control that has to be taken away again, in the
# one part of the scheme a player learns by muscle memory.
# (A comment and not a constant: nothing would read it, and an unread array
# naming two unbuilt controls is a scheme that only looks like it exists.)

## Turns the mouse into a single synthetic finger. `--touch=mouse`; anything
## else, including nothing, leaves it off.
##
## ⚠️ **A development aid with a hard limit: one finger.** It can exercise the
## steering thumb or the driving thumb, never both at once, so it cannot see any
## defect that lives in the interaction between them — a zone claiming the wrong
## finger, or one thumb's release zeroing the other's axis. `verify_input.gd`
## covers the two-finger cases because this cannot, and `P0-3b`'s handset is
## still what settles whether the scheme is usable.
##
## Off by default, so shipped behaviour on every platform is unchanged. The
## alternative was `input_devices/pointing/emulate_touch_from_mouse` in
## `project.godot`, which would have changed desktop behaviour for everyone and
## collided with `free_look_camera.gd`'s mouse capture in the preview scenes.
const TOUCH_ARG: String = "--touch="

## Where `DebugHud` lives once the autoloads have registered.
##
## 🔴 **Looked up by path, never named as an identifier and never `preload`ed,
## and both of those were tried.** An autoload identifier does not exist for a
## `--script` tool, so naming `DebugHud` here makes this whole script
## uncompilable outside a running game; `verify_input.gd` then fails to build the
## router, aborts mid-function, and never reaches its own `quit()` — a hang, not
## a failure. `preload`ing `debug_hud.gd` instead only moves the problem: it
## drags in `vehicle_controller.gd`, which names the `InputRouter` autoload, and
## the same error arrives one script further away. A path resolves at runtime and
## has neither dependency.
##
## ⚠️ **Absent is a legitimate answer** — it is what a headless tool gets — and
## it means `--touch=mouse` is simply off, which is the right default for
## everything that is not a person at a desk.
const DEBUG_HUD_PATH: NodePath = ^"/root/DebugHud"

## The index a mouse-as-finger reports as. Negative because real touch indices
## start at 0, so no arrangement of fingers can collide with it.
const _MOUSE_INDEX: int = -2


## One thumb: which zone it may land in, and where it is now.
##
## ⚠️ **`origin` is where the finger LANDED, not the middle of the zone.** Both
## thumbs are relative (`Q83`) — that is what lets the rests stay fingertip-
## sized instead of needing a slider's travel area, which measured out at 20 px
## of clearance against the HUD.
class Thumb:
	extends RefCounted

	## The invisible Control that resolves this thumb's zone on the real screen.
	var zone: Control = null
	## The finger currently claiming this thumb, or -1 for none.
	var index: int = -1
	var origin: Vector2 = Vector2.ZERO
	var current: Vector2 = Vector2.ZERO

	func is_down() -> bool:
		return index != -1

	## Travel from the touch origin, in design units.
	func offset() -> Vector2:
		return current - origin

	## Claims this thumb for `finger` at `at`, and reports whether it took it.
	## Refuses where the thumb is already held: a second finger landing in a zone
	## that is already driving must not move the origin out from under the first.
	func claim(finger: int, at: Vector2) -> bool:
		if is_down() or zone == null or not zone.get_global_rect().has_point(at):
			return false
		index = finger
		origin = at
		current = at
		return true

	## Releases `finger` if it is the one holding this thumb.
	##
	## ⚠️ **`is_down()` first, because the "no finger" sentinel shares an integer
	## space with the finger indices.** Nothing reaches this with -1 today — real
	## indices start at 0 and the synthetic mouse is forced to `_MOUSE_INDEX` for
	## exactly this reason — but without the guard an unheld thumb would report
	## that it had released a finger it never had.
	func release(finger: int) -> bool:
		if not is_down() or index != finger:
			return false
		index = -1
		origin = Vector2.ZERO
		current = Vector2.ZERO
		return true

	## Follows `finger` to `at`. ⚠️ **No bounds check, and that is the point.**
	## A thumb sweeps an arc and may leave the rectangle it was claimed in
	## (`Q83`); the zone says where a finger is *claimed*, not where it is
	## confined. Clamping here would make full lock unreachable from a thumb that
	## landed near its zone's edge.
	func drag(finger: int, at: Vector2) -> bool:
		if index != finger:
			return false
		current = at
		return true


var _touch: TouchProfile = null
var _steer_thumb: Thumb = Thumb.new()
var _drive_thumb: Thumb = Thumb.new()
var _mouse_is_down: bool = false
## Whether `--touch=mouse` was passed. Resolved once: a command line does not
## change while the game runs, and the lookup that answers it needs the autoloads
## to have registered.
var _mouse_is_a_finger: bool = false


func _ready() -> void:
	_build_zones()
	# `DebugHud` registers before this autoload — `project.godot` lists it first —
	# so it is already there. Absent means a headless tool, and mouse-as-finger
	# stays off.
	var debug_hud: Node = get_node_or_null(DEBUG_HUD_PATH)
	if debug_hud != null:
		_mouse_is_a_finger = str(debug_hud.cmdline_value(TOUCH_ARG)).to_lower() == "mouse"


## Resolve the two touch zones onto the real screen, as Controls.
##
## 🔴 **The geometry comes from `hud_layout.tres` and is placed by
## `HudLayout`'s own placer**, never re-derived here. The zones have to land in
## the same frame the layout reserves — same anchor rule, same safe-area inset —
## or a thumb rest that the HUD is keeping clear and the zone it sits inside
## disagree by the width of a notch. That is invisible at a desk and wrong on
## exactly one device.
##
## ⚠️ **Controls rather than arithmetic.** Anchors mean the engine re-resolves
## every zone on a rotation or a window resize, and `get_global_rect()` is then
## the answer; a cached rect would be a second copy of the layout with its own
## staleness. They are `MOUSE_FILTER_IGNORE` and never drawn — `Q97` ships no
## visible touch chrome — so this costs no draw call.
##
## ⚠️ **A CanvasLayer of its own, not the HUD's.** `--hud=off` frees the HUD
## outright (`hud.gd`), and a touch layer parented to it would take the
## player's steering with it — including on `P3-9`'s no-arrow acceptance drive,
## which is a *driving* test that turns the HUD off.
func _build_zones() -> void:
	var layout: HudLayout = load(HudLayout.PATH) as HudLayout
	_touch = load(TouchProfile.PATH) as TouchProfile
	if layout == null or _touch == null:
		# Warned rather than fatal: keyboard and gamepad are unaffected and the
		# game is still playable, which is the honest state to leave a desktop
		# run in. On a handset it is fatal in practice, and the warning is what
		# says so.
		push_warning(
			(
				"input: no touch zones this run; %s or %s did not load"
				% [HudLayout.PATH, TouchProfile.PATH]
			)
		)
		_touch = null
		return

	var canvas := CanvasLayer.new()
	canvas.name = "TouchZones"
	add_child(canvas)

	# The same root the HUD builds, from the same function: the zones have to
	# resolve in the frame the rests were reserved in, and that frame is the root
	# as much as it is the inset.
	var root: Control = HudLayout.safe_root(canvas)

	_steer_thumb.zone = _zone(layout, root, "SteerZone", layout.steer_zone())
	_drive_thumb.zone = _zone(layout, root, "DriveZone", layout.drive_zone())


func _zone(layout: HudLayout, root: Control, zone_name: String, design: Rect2) -> Control:
	var zone := Control.new()
	zone.name = zone_name
	zone.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layout.place(root, zone, design)
	return zone


## The one place in the project that reads raw input events.
##
## ⚠️ **Not marked handled.** The zones cover most of the lower screen and every
## Control in this project is `MOUSE_FILTER_IGNORE`, so swallowing events here
## would buy nothing and would silently break any UI that later wants a button.
func _input(event: InputEvent) -> void:
	if _touch == null:
		return

	var touch := event as InputEventScreenTouch
	if touch != null:
		_finger(touch.index, touch.position, touch.pressed)
		return

	var drag := event as InputEventScreenDrag
	if drag != null:
		_drag(drag.index, drag.position)
		return

	_mouse(event)


## `--touch=mouse` only: one synthetic finger, pressed and dragged by the left
## button.
##
## ⚠️ **The flag is read once in `_ready`, never here.** A command line does not
## change while the game runs, and re-reading it would put a `PackedStringArray`
## copy and a `String` allocation on the mouse-motion path — which fires at the
## pointer's poll rate, several hundred times a second, on the one scheme this
## branch is not even for.
func _mouse(event: InputEvent) -> void:
	if not _mouse_is_a_finger:
		return

	var button := event as InputEventMouseButton
	if button != null and button.button_index == MOUSE_BUTTON_LEFT:
		_mouse_is_down = button.pressed
		_finger(_MOUSE_INDEX, button.position, button.pressed)
		return

	var motion := event as InputEventMouseMotion
	if motion != null and _mouse_is_down:
		_drag(_MOUSE_INDEX, motion.position)


## A finger arriving or leaving.
##
## ⚠️ **The steering zone is offered the finger first and a claim is exclusive**,
## so the two zones cannot both follow one touch even where the rects overlap.
## They do not overlap today — 800 design units apart on opposite edges — and
## the ordering is what keeps that a fact about the `.tres` rather than a fact
## the input code depends on.
func _finger(index: int, at: Vector2, pressed: bool) -> void:
	if not pressed:
		# Both are asked: a finger holds at most one, and which one is not worth
		# tracking separately when the answer is a comparison.
		_steer_thumb.release(index)
		_drive_thumb.release(index)
		return
	if _steer_thumb.claim(index, at):
		return
	_drive_thumb.claim(index, at)


func _drag(index: int, at: Vector2) -> void:
	if _steer_thumb.drag(index, at):
		return
	_drive_thumb.drag(index, at)


func _physics_process(_delta: float) -> void:
	steer = Input.get_axis(&"steer_left", &"steer_right")
	accelerate = Input.get_action_strength(&"accelerate")
	brake_reverse = Input.get_action_strength(&"brake_reverse")

	# 🔴 **Touch OVERRIDES the action map per axis; it does not replace it.**
	# `driver.gd` drives every scripted run through `Input.action_press`
	# (`--hold=accelerate@0.3+12.7`), so a router that computed these from touch
	# state unconditionally would read zero through every regression drive in
	# the repo — including `Q81`'s wrong-way route, which is the only evidence
	# that layer has. Per axis, and only while that axis's own finger is down.
	#
	# ⚠️ **And the touch values are merged HERE rather than fed through
	# `Input.action_press(action, strength)`**, which would have needed no
	# changes below. The action map cannot carry them: `project.godot` gives all
	# four axis actions `"deadzone": 0.2`, and `get_action_strength` returns 0
	# beneath it — so the first fifth of every thumb's travel would vanish, on a
	# control whose whole design is that small travel is available (`Q97`).
	if _steer_thumb.is_down():
		steer = _touch.steer_from(_steer_thumb.offset().x)
	if _drive_thumb.is_down():
		# One bipolar axis split into the two the vehicle reads (`Q83`), and
		# centre is coast — which is the lift-off `P0-5b/c/d` requires in order
		# to park the car at all.
		var longitudinal: float = _touch.drive_from(_drive_thumb.offset().y)
		accelerate = maxf(longitudinal, 0.0)
		brake_reverse = maxf(-longitudinal, 0.0)

	if auto_accelerate and is_zero_approx(brake_reverse):
		accelerate = 1.0

	drift = _track_hold(&"drift", drift, drift_started, drift_ended)
	look_back = _track_hold(&"look_back", look_back, look_back_started, look_back_ended)


## Comparing against the previous value rather than using
## Input.is_action_just_pressed(), which the engine documents as unreliable in
## _physics_process — it can report true across several ticks or none at all.
func _track_hold(action: StringName, was_held: bool, started: Signal, ended: Signal) -> bool:
	var held: bool = Input.is_action_pressed(action)
	if held == was_held:
		return held
	if held:
		started.emit()
	else:
		ended.emit()
	return held
