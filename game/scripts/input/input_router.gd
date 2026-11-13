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
## `accelerate` above the touch origin and `brake_reverse` below. `handbrake` and
## `look_back` have no touch home yet, and the note above `TOUCH_ARG` says why;
## nor has `horn` (`Q178`), for the same reason: the handset prices the gesture.

## Steering, -1.0 (full left) to 1.0 (full right), as the device reads it: a key
## is 0 or 1 here. The car asks `steer_for()`, which shapes a key into a linear
## input first (`Q210`); this is the raw reading, for anything that wants it.
var steer: float = 0.0
## Whether the steering came last from a key, which `steer_for()` shapes, rather
## than a stick or a thumb, which it passes through (`Q210`). The input METHOD,
## never the device: a key press sets it, a stick past its dead zone or a
## steering thumb clears it. True until either, so a run driven through
## `Input.action_press` (`driver.gd`, the skidpad) steers as a key does; the
## skidpad's `--steer=analog` clears it.
var steer_from_keys: bool = true
## Throttle, 0.0 to 1.0.
var accelerate: float = 0.0
## Brake / reverse, 0.0 to 1.0.
var brake_reverse: float = 0.0
var handbrake: bool = false
var look_back: bool = false
## The taxi's horn (`Q178`): held, so `TaxiHorn` sounds it on the press.
var horn: bool = false

## Forces full throttle whenever the brake is released. ⚠️ **No longer the touch
## default — `Q83` reversed it.** Touch drives the throttle for real, on the
## positive half of thumb 1's vertical axis, and pays no extra thumb rest for it
## because `brake_reverse` is the negative half of that same axis.
##
## Kept as the accessibility and one-handed option. Nothing sets it, so the
## `false` below is shipped behaviour on every scheme rather than a placeholder.
var auto_accelerate: bool = false

# ⬜ **What touch still does not carry, and why it is a comment rather than a
# broken control.** `handbrake` is settled as a held vertical offset on thumb 2
# past a threshold with hysteresis (`Q83`), and the threshold and hysteresis
# are numbers `Q83` says no desk can pick — `P2-4`'s review is blocked on
# `P0-3b` for the handset. `look_back` has never been placed at all; thumb 1's
# horizontal axis is the standing candidate.
#
# 🔴 **Thumb 2's vertical axis is therefore READ AND DISCARDED, deliberately.**
# The handbrake lives there and nothing else may be put on it — a second control
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
const TOUCH_ARG: String = HudLayout.TOUCH_ARG

## ⚠️ **`Cmdline` is a `class_name`, and that is what makes naming it here safe.**
## The reader this replaced lived on the `DebugHud` autoload, and an autoload
## identifier does not exist for a `--script` tool: naming one here made this
## whole script uncompilable outside a running game, `verify_input.gd` then
## failed to build the router, aborted mid-function and never reached its own
## `quit()` — a hang, not a failure — so it was reached by path. A `class_name`
## resolves out of the class cache the import writes, which every tool has.

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
## The keyboard's input assist (`Q210`), or null when it did not load — then a
## key passes through as it reads, which is a car tuned against a linear input
## driven by a binary one, so it is an error, not a warning.
var _keys: KeyboardSteerProfile = null
## The key's shaped steering, carried between ticks: the ramp's own state.
var _key_steer: float = 0.0
var _steer_thumb: Thumb = Thumb.new()
var _drive_thumb: Thumb = Thumb.new()
var _mouse_is_down: bool = false
## Whether `--touch=mouse` was passed. Resolved once: a command line does not
## change while the game runs.
var _mouse_is_a_finger: bool = false


func _ready() -> void:
	_keys = load(KeyboardSteerProfile.PATH) as KeyboardSteerProfile
	if _keys == null or not _keys.usable():
		push_error("input: %s did not load or has a zero ramp" % KeyboardSteerProfile.PATH)
		_keys = null
	_build_zones()
	_mouse_is_a_finger = Cmdline.value(TOUCH_ARG).to_lower() == "mouse"


## A paused tree sends this no input, so a finger lifted over the pause menu
## would never be released and the thumb would hold its last steer or throttle
## into the resume. Both are let go as the pause starts: the player's thumbs
## land afresh after it.
func _notification(what: int) -> void:
	if what != NOTIFICATION_PAUSED:
		return
	_steer_thumb.release(_steer_thumb.index)
	_drive_thumb.release(_drive_thumb.index)
	_mouse_is_down = false
	# And a held key ramps afresh after it, never from where the pause found it.
	_key_steer = 0.0


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
## staleness. They are `MOUSE_FILTER_IGNORE` and never drawn here, so this
## costs no draw call; the HUD draws the sticks over them (`TouchSticks`, `Q204`).
##
## ⚠️ **A CanvasLayer of its own, not the HUD's.** `--hud=off` frees the HUD
## outright (`hud.gd`), and a touch layer parented to it would take the
## player's steering with it — including on `P3-9`'s no-arrow acceptance drive,
## which is a *driving* test that turns the HUD off.
func _build_zones() -> void:
	var layout: HudLayout = HudLayout.for_device()
	_touch = load(TouchProfile.PATH) as TouchProfile
	if layout == null or _touch == null:
		# Warned rather than fatal: keyboard and gamepad are unaffected and the
		# game is still playable, which is the honest state to leave a desktop
		# run in. On a handset it is fatal in practice, and the warning is what
		# says so.
		push_warning(
			"input: no touch zones this run; the layout or %s did not load" % TouchProfile.PATH
		)
		_touch = null
		return

	# First, before any root is inset: the menu, the HUD and these zones all lay
	# out in the frame the table is written in (`Q204`). The desk table's is the
	# project's own, so this is a no-op there.
	layout.apply_scale(get_tree())

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
	# Out to the glass on the edges the zone reaches: a thumb landing in the
	# notch's strip still steers (`Q204`).
	layout.place_to_glass(root, zone, design)
	return zone


## The steering thumb's landing point and where it is now, in canvas units, or
## an empty array while it is up. For the HUD's sticks, which draw it (`Q204`).
func steer_touch() -> PackedVector2Array:
	return _thumb_points(_steer_thumb)


## The same for the driving thumb.
func drive_touch() -> PackedVector2Array:
	return _thumb_points(_drive_thumb)


static func _thumb_points(thumb: Thumb) -> PackedVector2Array:
	if not thumb.is_down():
		return PackedVector2Array()
	return PackedVector2Array([thumb.origin, thumb.current])


## How far each thumb may travel, for the sticks to draw: steer, then drive.
func travel_px() -> Vector2:
	if _touch == null:
		return Vector2.ZERO
	return Vector2(_touch.steer_travel_px, _touch.drive_travel_px)


## The one place in the project that reads raw input events.
##
## ⚠️ **Not marked handled.** The zones cover most of the lower screen and every
## Control in this project is `MOUSE_FILTER_IGNORE`, so swallowing events here
## would buy nothing and would silently break any UI that later wants a button.
func _input(event: InputEvent) -> void:
	# Before the touch guard: a desk without touch zones still has keys and sticks.
	_note_steer_method(event)
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


## Which input method steered last (`steer_from_keys`). Pressed past the
## action's dead zone only, so a stick resting off centre does not take the
## steering away from a player on the keys.
func _note_steer_method(event: InputEvent) -> void:
	# Pointer motion and touch arrive at hundreds a second and never steer here.
	if not (event is InputEventKey or event is InputEventJoypadMotion):
		return
	if not (event.is_action_pressed(&"steer_left") or event.is_action_pressed(&"steer_right")):
		return
	steer_from_keys = not event is InputEventJoypadMotion


## The steering the car drives on (`Q210`): a stick's or a thumb's as it reads,
## and a key's shaped into a linear input — ramped from centre to full over the
## keyboard table's seconds, slower as the car nears its limiter
## (`speed_share`, its share of the limiter), and at `attack_s` when the car
## asks for the quick ramp (`quick`: drift mode, or a countersteer). Letting go,
## or easing to a smaller input on the same side, is not shaped: the car's own
## release ramp returns the wheel. A reversal ramps the whole way, as the car's
## rack did when it carried this ramp. Called once per physics tick, by the
## player's car alone: the ramp's state is the router's.
func steer_for(speed_share: float, quick: bool, delta: float) -> float:
	if not steer_from_keys or _keys == null:
		_key_steer = steer
		return steer
	var seconds: float = (
		_keys.attack_s
		if quick
		else lerpf(_keys.attack_s, _keys.attack_at_top_s, speed_share * speed_share)
	)
	if absf(steer) <= absf(_key_steer):
		# Easing off is the car's release. Across centre, only down to the new
		# magnitude: the rest of the way is a reversal, and that ramps.
		_key_steer = steer if steer * _key_steer >= 0.0 else signf(_key_steer) * absf(steer)
	_key_steer = move_toward(_key_steer, steer, delta / seconds)
	return _key_steer


## The keyboard's input assist, for the skidpad's `--sweep=keyboard_steer.…`.
func keyboard_profile() -> KeyboardSteerProfile:
	return _keys


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
		steer_from_keys = false
	if _drive_thumb.is_down():
		# One bipolar axis split into the two the vehicle reads (`Q83`), and
		# centre is coast — which is the lift-off `P0-5b/c/d` requires in order
		# to park the car at all.
		var longitudinal: float = _touch.drive_from(_drive_thumb.offset().y)
		accelerate = maxf(longitudinal, 0.0)
		brake_reverse = maxf(-longitudinal, 0.0)

	if auto_accelerate and is_zero_approx(brake_reverse):
		accelerate = 1.0

	# Held state, not `is_action_just_pressed`, which the engine documents as
	# unreliable in `_physics_process`; the controller ramps from the bool (Q83).
	handbrake = Input.is_action_pressed(&"handbrake")
	look_back = Input.is_action_pressed(&"look_back")
	horn = Input.is_action_pressed(&"horn")
