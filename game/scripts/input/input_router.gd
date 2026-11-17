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
## Whether the steering came last from a thumb, which `steer_for()` slews at
## speed (`TouchProfile.steer_attack_at_top_s`) where a stick passes through as
## it reads. Read only while `steer_from_keys` is false: set while a steering
## thumb is down, which clears that, and cleared by a key or a stick; the
## skidpad's `--steer=touch` sets it.
var steer_from_thumb: bool = false
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
## ⚠️ **`origin` is where the finger LANDED, not the middle of the zone** —
## unless the player asked for controls that stand still (`fixed`, `Q239`). Both
## thumbs are relative (`Q83`) — that is what lets the rests stay fingertip-
## sized instead of needing a slider's travel area, which measured out at 20 px
## of clearance against the HUD.
class Thumb:
	extends RefCounted

	## The invisible Control that resolves this thumb's zone on the real screen.
	var zone: Control = null
	## This thumb's rest, where its control is drawn while it is up; and whether
	## the control stays there (`ControlOptions.FIXED`, `Q239`): the thumb is
	## then read from the rest's middle, wherever in the zone it landed.
	var home: Control = null
	var fixed: bool = false
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
		origin = home.get_global_rect().get_center() if fixed and home != null else at
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
## The steering thumb's curve, the player's pick of `_touch`'s three (`Q223`):
## read when the zones are built and on `refresh_options`, never per tick.
var _steer_curve: float = 1.0
## The touch wheel's position, -1.0 to 1.0, before its curve (`Q238`). Carried
## between touches: a lifted thumb leaves it where it was, `steer_for` returns
## it to centre as the car rolls, and a thumb landing again takes it up from
## there. Zero whenever anything but a thumb steers.
var _wheel: float = 0.0
## Where the wheel was as the sliding thumb landed: its slide adds to this.
var _wheel_at_landing: float = 0.0
## How far round the wheel's middle the steering thumb has gone since it
## landed on its twelve o'clock, in degrees, clockwise positive (`_go_round`).
## Not wrapped: a thumb that has been right round has turned it 360.
var _bearing_deg: float = 0.0
## Whether the steering thumb is going round the wheel (`Q243`): only once it
## is `spin_enter_deg` round, and until it comes back inside that or lifts.
## Until then the slide alone steers.
var _spinning: bool = false
## The wheel and the bearing as the spin began: the spin carries the wheel on
## from there to full lock at `spin_lock_deg`, so taking it up moves nothing.
var _spin_base: float = 0.0
var _spin_from_deg: float = 0.0
## What a spin that ended left the wheel off its slide by, and the sideways
## offset the thumb had then. It shrinks with the thumb's way back to where it
## landed, so the landing point is the wheel at its landing again.
var _slide_bias: float = 0.0
var _bias_reach_px: float = 0.0
## The layer the zones stand on, kept so `rebuild_zones` can retire it.
var _zones: CanvasLayer = null
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
	_wheel = 0.0


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
	refresh_options()

	# First, before any root is inset: the menu, the HUD and these zones all lay
	# out in the frame the table is written in (`Q204`). The desk table's is the
	# project's own, so this is a no-op there.
	layout.apply_scale(get_tree())

	var canvas := CanvasLayer.new()
	canvas.name = "TouchZones"
	add_child(canvas)
	_zones = canvas

	# The same root the HUD builds, from the same function: the zones have to
	# resolve in the frame the rests were reserved in, and that frame is the root
	# as much as it is the inset.
	var root: Control = HudLayout.safe_root(canvas)

	_steer_thumb.zone = _zone(layout, root, "SteerZone", layout.steer_zone())
	_drive_thumb.zone = _zone(layout, root, "DriveZone", layout.drive_zone())
	_steer_thumb.home = _rest(layout, root, "SteerRest", layout.steer_rest())
	_drive_thumb.home = _rest(layout, root, "DriveRest", layout.drive_rest())


## Read the player's steering pick again (`ControlOptions`): the options menu
## changed it, at boot or over a paused drive.
func refresh_options() -> void:
	if _touch != null:
		_steer_curve = _touch.curve_for(ControlOptions.steering())
	# From each thumb's next landing: one that is down keeps the origin it has.
	var fixed: bool = ControlOptions.anchor() == ControlOptions.FIXED
	_steer_thumb.fixed = fixed
	_drive_thumb.fixed = fixed


## Build the zones afresh: the thumbs swapped sides (`Q223`). Both thumbs are
## let go first, since a finger held in a zone that has moved is in neither.
## Freed at once, not queued: the new layer takes the old one's name.
func rebuild_zones() -> void:
	_steer_thumb.release(_steer_thumb.index)
	_drive_thumb.release(_drive_thumb.index)
	_mouse_is_down = false
	if is_instance_valid(_zones):
		_zones.free()
	_zones = null
	_steer_thumb.zone = null
	_drive_thumb.zone = null
	_steer_thumb.home = null
	_drive_thumb.home = null
	_wheel = 0.0
	_build_zones()


func _zone(layout: HudLayout, root: Control, zone_name: String, design: Rect2) -> Control:
	var zone := Control.new()
	zone.name = zone_name
	zone.mouse_filter = Control.MOUSE_FILTER_IGNORE
	# Out to the glass on the edges the zone reaches: a thumb landing in the
	# notch's strip still steers (`Q204`).
	layout.place_to_glass(root, zone, design)
	return zone


## A thumb's rest, placed as the HUD places the hint it draws there, so a fixed
## control reads from the middle of its own drawing.
func _rest(layout: HudLayout, root: Control, rest_name: String, design: Rect2) -> Control:
	var rest := Control.new()
	rest.name = rest_name
	rest.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layout.place(root, rest, design)
	return rest


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


## How far round the drawn wheel is, -1.0 to 1.0 of its lock: the steering the
## touch wheel gives, under a thumb or left by one. It stays where a lifted
## thumb left it and comes back as the car rolls (`Q238`); 0 while anything but
## a thumb steers.
func wheel_turn() -> float:
	if _touch == null:
		return 0.0
	return _touch.shape(_wheel, _steer_curve)


## The middle of the wheel the steering thumb is on, in canvas units, for the
## sticks to draw it at: a radius below where the thumb landed, so the thumb is
## on its twelve o'clock (`Q238`); or, fixed, the rest's own middle (`Q239`).
## Means nothing while no thumb is down: the sticks ask only under one.
func wheel_centre() -> Vector2:
	if _touch == null or _steer_thumb.fixed:
		return _steer_thumb.origin
	return _steer_thumb.origin + Vector2(0.0, _touch.wheel_radius_px)


## The radius the wheel is drawn at, which is the one a thumb is read on.
func wheel_radius_px() -> float:
	return _touch.wheel_radius_px if _touch != null else 0.0


## The degrees the drawn wheel turns at full lock: the angle a thumb goes round
## it for one, so the rim keeps up with the finger.
func wheel_lock_deg() -> float:
	return _touch.spin_lock_deg if _touch != null else 0.0


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
	steer_from_thumb = false
	_wheel = 0.0


## The steering the car drives on (`Q210`): a stick's or a thumb's as it reads,
## and a key's shaped into a linear input — ramped from centre to full over the
## keyboard table's seconds, slower as the car nears its limiter
## (`speed_share`, its share of the limiter), and at `attack_s` when the car
## asks for the quick ramp (`quick`: drift mode, or a countersteer). Letting go,
## or easing to a smaller input on the same side, is not shaped: the car's own
## release ramp returns the wheel. A reversal ramps the whole way, as the car's
## rack did when it carried this ramp. Called once per physics tick, by the
## player's car alone: the ramp's state is the router's.
##
## A thumb is slewed at speed and never shaped (`steer_from_thumb`): it reads
## as it is at rest, and toward the limiter it may add lock no faster than the
## touch table's seconds to full, on the square of `speed_share` as the key's
## ramp is. Easing off and the quick ramp pass through.
##
## And a wheel a thumb let go of comes back here (`_return_wheel`, `Q238`): this
## is the one place the router is told the car's speed.
func steer_for(speed_share: float, quick: bool, delta: float) -> float:
	_return_wheel(speed_share, delta)
	var slewed: bool = steer_from_thumb and not steer_from_keys and _touch != null and not quick
	if not slewed and (not steer_from_keys or _keys == null):
		_key_steer = steer
		return steer
	if absf(steer) <= absf(_key_steer):
		# Easing off is the car's release. Across centre, only down to the new
		# magnitude: the rest of the way is a reversal, and that ramps.
		_key_steer = steer if steer * _key_steer >= 0.0 else signf(_key_steer) * absf(steer)
	if slewed:
		var slew_s: float = _touch.steer_attack_at_top_s * speed_share * speed_share
		# Under a tick to full there is nothing to slew.
		_key_steer = move_toward(_key_steer, steer, delta / slew_s) if slew_s > delta else steer
		return _key_steer
	var seconds: float = (
		_keys.attack_s
		if quick
		else lerpf(_keys.attack_s, _keys.attack_at_top_s, speed_share * speed_share)
	)
	if quick:
		_key_steer = move_toward(_key_steer, steer, delta / seconds)
		return _key_steer
	# The slow ramp moves the progress linearly and the input is its power
	# (`curve`); carried as the input, so a switch to or from the quick ramp
	# never jumps.
	var progress: float = _progress_of(_key_steer)
	progress = move_toward(progress, _progress_of(steer), delta / seconds)
	_key_steer = signf(progress) * pow(absf(progress), _keys.curve)
	return _key_steer


## Bring a wheel no thumb is holding back toward centre (`Q238`): in proportion
## to the car's speed, so it holds at a standstill and is all but at once at
## pace, where lifting the thumb is how a turn or a catch is ended. Linear in
## the wheel's position, so the steering itself falls away on the curve.
func _return_wheel(speed_share: float, delta: float) -> void:
	if _touch == null or _steer_thumb.is_down() or is_zero_approx(_wheel):
		return
	if _touch.steer_return_at_top_s <= 0.0:
		_wheel = 0.0
	else:
		_wheel = move_toward(_wheel, 0.0, delta * speed_share / _touch.steer_return_at_top_s)
	steer = wheel_turn()


## The steering thumb moved from `from` to `to`: keep how far round the
## wheel's middle it is, and whether that is a spin yet (`Q243`). The thumb
## landed on the wheel's twelve o'clock, so a slide stays near the top and a
## spin goes on down the side: `spin_enter_deg` round is where the one becomes
## the other, and back inside it the slide steers again.
##
## Not for a fixed wheel (`Q239`), whose thumb is read from its middle: there a
## thumb landing on the hub would have no bearing to start from.
func _go_round(from: Vector2, to: Vector2) -> void:
	if _steer_thumb.fixed:
		return
	var centre: Vector2 = wheel_centre()
	var now: Vector2 = to - centre
	var reach: float = absf(to.x - _steer_thumb.origin.x)
	if not _spinning:
		if reach < _bias_reach_px:
			_slide_bias *= reach / _bias_reach_px
			_bias_reach_px = reach
		if now.y < 0.0:
			# Above the wheel's middle a sliding thumb is where it is: nothing a
			# move through the hub left behind is carried into the next stroke.
			_bearing_deg = rad_to_deg(Vector2.UP.angle_to(now))
			return
	# The whole move, not its two ends: a flick across the wheel between two
	# events reads as half a turn, either way round. ⚠️ A move the hub
	# swallows is not made up afterwards — a thumb drawn through it has the
	# wheel where it was, and goes round from there.
	var nearest: Vector2 = Geometry2D.get_closest_point_to_segment(centre, from, to)
	if nearest.distance_to(centre) < _touch.wheel_hub_px:
		return
	# Screen Y runs down, so a positive angle here is clockwise on the glass.
	_bearing_deg += rad_to_deg((from - centre).angle_to(now))
	var round_enough: bool = absf(_bearing_deg) >= _touch.spin_enter_deg
	if round_enough == _spinning:
		return
	# Read under the old mode, at the thumb's new place: the wheel the other
	# mode takes up.
	var wheel: float = _thumb_wheel()
	_spinning = round_enough
	_slide_bias = 0.0
	_bias_reach_px = 0.0
	if _spinning:
		_spin_base = wheel
		_spin_from_deg = absf(_bearing_deg)
	elif reach > 0.0:
		# Off the slide before its clamp: a slide past the lock would leave the
		# difference short, and the wheel would jump by the rest.
		_slide_bias = wheel - _wheel_at_landing - _touch.steer_share(_steer_thumb.offset().x)
		_bias_reach_px = reach


## The wheel the thumb that is down has. Sliding: where it was at the landing
## and the thumb's sideways offset, whatever its height (`Q243`). Spinning:
## from the wheel the spin began on to full lock at `spin_lock_deg` round, the
## way the thumb is going; unwound past where it began, the wheel it began on.
func _thumb_wheel() -> float:
	if _spinning:
		var span: float = maxf(_touch.spin_lock_deg - _spin_from_deg, 1.0)
		var over: float = clampf((absf(_bearing_deg) - _spin_from_deg) / span, 0.0, 1.0)
		return lerpf(_spin_base, signf(_bearing_deg), over)
	var slid: float = _touch.steer_share(_steer_thumb.offset().x)
	return clampf(_wheel_at_landing + slid + _slide_bias, -1.0, 1.0)


## The slow ramp's progress that gives `input`, the inverse of its `curve`.
func _progress_of(input: float) -> float:
	return signf(input) * pow(absf(input), 1.0 / _keys.curve)


## The keyboard's input assist, for the skidpad's `--sweep=keyboard_steer.…`.
func keyboard_profile() -> KeyboardSteerProfile:
	return _keys


## The touch table, for the skidpad's `--sweep=touch.…`.
func touch_profile() -> TouchProfile:
	return _touch


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
		# A fixed wheel is where the thumb is on it, whatever it was left at.
		_wheel_at_landing = 0.0 if _steer_thumb.fixed else _wheel
		_bearing_deg = 0.0
		_spinning = false
		_slide_bias = 0.0
		_bias_reach_px = 0.0
		return
	_drive_thumb.claim(index, at)


func _drag(index: int, at: Vector2) -> void:
	var was: Vector2 = _steer_thumb.current
	if _steer_thumb.drag(index, at):
		_go_round(was, at)
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
		# From where the wheel was as the thumb landed (`Q238`): centre,
		# unless it landed on a wheel a standing car was still holding.
		_wheel = _thumb_wheel()
		steer = wheel_turn()
		steer_from_keys = false
		steer_from_thumb = true
	elif not is_zero_approx(_wheel):
		# The thumb lifted and the wheel is where it left it; `steer_for`
		# brings it back as the car rolls. A key or a stick takes the steering
		# and the wheel with it.
		if is_zero_approx(steer) and steer_from_thumb and not steer_from_keys:
			steer = wheel_turn()
		else:
			_wheel = 0.0
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
