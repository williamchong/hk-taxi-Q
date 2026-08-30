extends SceneTree

## The touch scheme, driven by synthetic fingers (`P2-4`).
##
## ⚠️ **Runs without a built region**, like `verify_hud.gd`: the layout and the
## touch profile are committed tuning and the fingers are invented here, so CI
## checks this on every push. That matters more than usual — `P0-3b` has no
## handset, so until it lands **this tool is the only thing that exercises the
## touch path at all** except a human dragging a mouse.
##
## **What this is for, in one line each:**
##
##   * The two zones must land where `hud_layout.tres` reserves them. The router
##     places them with `HudLayout`'s own placer rather than its own arithmetic,
##     and what is asserted here is the *geometric* relationship that would
##     survive either implementation — a zone contains its own thumb rest — so
##     this stays a check rather than a restatement of the code.
##   * A thumb is **relative** (`Q83`): full lock has to be reachable from
##     wherever the finger landed, including by dragging outside the zone.
##   * `brake_reverse` is the negative half of one axis and **centre is coast**,
##     which is what `P0-5b/c/d` requires in order to park the car at all.
##   * Touch **overrides** the action map per axis and does not replace it. Every
##     scripted drive in this repo runs on `Input.action_press`, so this is what
##     stands between a touch scheme and every `--hold=` run going silent.
##
## ⚠️ **The assertions are written so they can fail.** `Q72`'s lesson is that a
## counter reading 0 because 0 is unreachable certifies whichever state the code
## produces — so the override is tested from **both** sides (the keyboard drives
## when no finger is down, and loses when one is), a finger outside every zone is
## asserted to move nothing, and the deferred `drift` is asserted *absent* while
## the axis it will one day live on is being driven.
##
## 🔴 **This tool CAN print `verify_input: ok` having checked nothing**, exactly
## as `verify_hud.gd` can and for the same reason: a `preload`ed script that
## fails to compile aborts the calling function on the spot, every assertion
## after it is skipped, and `_failed` stays 0. `tools/check.sh` greps stderr and
## supplies the exit code Godot will not. **Never run this by hand and read its
## output.**
##
## ⚠️ **Nothing here references a `class_name` global**, for the reason
## `ARCHITECTURE.md` records: a `--script` tool that does fails to parse on a
## fresh clone where the class cache has not been written, and the SceneTree then
## exits **0** having checked nothing. Everything is `preload`ed or `load`ed by
## path. The router itself names two globals and that is fine — it is *loaded*,
## not referenced, and `check.sh` runs `--import` before any tool.

const RouterScript = preload("res://scripts/input/input_router.gd")
const TouchProfileScript = preload("res://scripts/input/touch_profile.gd")
const HudLayoutScript = preload("res://scripts/ui/hud_layout.gd")

## ⚠️ **The paths come from the scripts the game loads, never restated here.** A
## check that names its own path goes green while the game reads a different
## file — the one failure a verify tool cannot be allowed to have.

## A physics step to hand the router. The value is irrelevant — nothing in the
## touch path integrates over time yet — and 0 would be a lie about a tick.
const TICK: float = 1.0 / 60.0

## Finger indices. Real ones, unlike the router's own mouse index, so that
## nothing here is testing the development aid by accident.
const FINGER_A: int = 0
const FINGER_B: int = 1

## Somewhere in the top-middle band, which no zone reaches: `touch_zone_*` both
## start at y 480 and the drawn HUD's own top row is above that.
const NOWHERE := Vector2(960.0, 100.0)

## How long `_run` gets before this tool decides it is never going to finish.
##
## 🔴 **A watchdog and not a nicety.** `verify_hud.gd` records that a `preload`ed
## script failing to compile aborts the calling function on the spot; what it
## does not say is that a `SceneTree` tool which aborts before its `quit()`
## **never exits**. That is worse than the green run it warns about: it wedges
## `check.sh` and CI rather than failing them. This was not hypothetical — it
## happened on this tool's first run, from an autoload identifier that does not
## exist under `--script`. A guard inside `_run` cannot help, because
## `RouterScript.new()` returning null aborts at the guard itself.
const WATCHDOG_S: float = 30.0

var _failed: int = 0
var _finished: bool = false
var _router: Node = null
var _touch: Resource = null
var _layout: Resource = null


func _init() -> void:
	# Deferred, then a frame, before anything is instanced. Autoloads are
	# registered on the first frame and not before, and the router reaches
	# `DebugHud`; `verify_vehicle.gd`'s header records the trap, whose failure
	# mode is a green run over an empty suite.
	_run.call_deferred()
	_watchdog.call_deferred()


## Fails the run if `_run` never reaches `_finish`. A separate coroutine, so an
## abort inside `_run` cannot take it down too.
func _watchdog() -> void:
	await create_timer(WATCHDOG_S).timeout
	if _finished:
		return
	push_error(
		(
			"verify_input: gave up after %.0f s without finishing — a depended script almost certainly failed to compile, which aborts the run mid-function"
			% WATCHDOG_S
		)
	)
	quit(1)


func _run() -> void:
	await process_frame

	_touch = load(TouchProfileScript.PATH)
	_layout = load(HudLayoutScript.PATH)
	if _touch == null or _layout == null:
		_fail("load", "%s or %s did not load" % [TouchProfileScript.PATH, HudLayoutScript.PATH])
		_finish()
		return

	_check_profile()

	_router = RouterScript.new()
	_router.name = "TouchRouterUnderTest"
	get_root().add_child(_router)
	# Two frames: one for `_ready` to build the zones, one for the Controls'
	# anchors to resolve into the global rects the claim test reads. Asking on
	# the same frame returns a zero-size rect, which would make every claim below
	# fail for a reason that has nothing to do with what is being checked.
	await process_frame
	await process_frame

	_check_zones()
	_check_steer()
	_check_drive()
	_check_two_thumbs()
	_check_override()
	_check_deferred()
	_check_mouse()

	_router.queue_free()
	_finish()


func _finish() -> void:
	_finished = true
	if _failed > 0:
		push_error("verify_input: %d check(s) failed" % _failed)
		quit(1)
		return
	print("verify_input: ok")
	quit(0)


# --------------------------------------------------------------- profile ----


## The shipped `touch.tres` has to be usable before anything below means
## anything. `touch_profile.gd` declares no defaults, so a key missing from the
## `.tres` arrives as 0.0 — and a zero travel is full lock the instant a thumb
## lands, which is a car nobody can drive and a number no frame reveals.
func _check_profile() -> void:
	var steer_travel: float = _touch.steer_travel_px
	var drive_travel: float = _touch.drive_travel_px
	var jitter: float = _touch.jitter_deadzone_px
	_expect(steer_travel > 0.0, "profile", "steer_travel_px is %.1f" % steer_travel)
	_expect(drive_travel > 0.0, "profile", "drive_travel_px is %.1f" % drive_travel)
	_expect(jitter >= 0.0, "profile", "jitter_deadzone_px is %.1f" % jitter)
	# The guard in `_axis_from` keeps a bad edit from dividing by zero; this is
	# what says the edit was bad. Below the band there is no usable travel at
	# all and the axis is a switch.
	_expect(
		steer_travel > jitter and drive_travel > jitter,
		"profile",
		"both travels exceed the %.1f dead band" % jitter
	)


# ----------------------------------------------------------------- zones ----


## The zones land where the layout reserves them.
##
## 🔴 **Two assertions in two frames, and neither is an equality against the
## rects the router read.** Comparing a resolved zone to `layout.steer_zone()`
## would pass for any implementation that loads the file — it restates the code.
##
## In **design space**, the check is that a zone encloses its own thumb rest.
## That is a fact about the two tables rather than about either implementation,
## and it is the one `Q80` turns on: a tap zone is where input is detected, a
## thumb rest is the fingertip inside it that the HUD must keep clear.
##
## On the **real screen**, the check is that each zone still holds its own outer
## edge. That is what the anchoring is for and it is viewport-independent, which
## the containment deliberately is not: ⚠️ **the headless viewport is 1920x1920**,
## a dummy-display artifact, and on any canvas taller than the 1080 design the
## rests anchor to the bottom while the zones anchor to the centre, so the two
## genuinely separate. Landscape handsets expand in X and hold 1080 in Y, so this
## does not arise on a device — but re-asserting the containment against resolved
## rects would fail here for a reason that has nothing to do with touch.
func _check_zones() -> void:
	var steer_zone: Rect2 = _zone("SteerZone")
	var drive_zone: Rect2 = _zone("DriveZone")
	var canvas: Vector2 = get_root().get_visible_rect().size

	_expect(
		_layout.steer_zone().encloses(_layout.thumb_rest_left),
		"zones",
		"the steer zone encloses thumb_rest_left in design space"
	)
	_expect(
		_layout.drive_zone().encloses(_layout.thumb_rest_right),
		"zones",
		"the drive zone encloses thumb_rest_right in design space"
	)

	_expect(steer_zone.get_area() > 0.0, "zones", "the steer zone resolved to %s" % steer_zone)
	_expect(drive_zone.get_area() > 0.0, "zones", "the drive zone resolved to %s" % drive_zone)
	# A zone that stopped anchoring would float in from the edge as the canvas
	# widened, and the thumb that reaches furthest — the one in the corner —
	# would fall outside it. Nothing in a frame would show that.
	_expect(
		is_zero_approx(steer_zone.position.x),
		"zones",
		"the steer zone holds the left edge of a %.0f-wide canvas" % canvas.x
	)
	_expect(
		is_equal_approx(drive_zone.end.x, canvas.x),
		"zones",
		"the drive zone holds the right edge of a %.0f-wide canvas" % canvas.x
	)
	# Not a restatement of the `.tres` either: the router offers the steer zone
	# every finger first, so overlapping zones would make which thumb a touch
	# claims depend on that ordering rather than on where the player put it.
	_expect(not steer_zone.intersects(drive_zone), "zones", "the two zones do not overlap")


## The resolved rect of one of the router's zone Controls, by node name.
func _zone(zone_name: String) -> Rect2:
	var control := _router.find_child(zone_name, true, false) as Control
	if control == null:
		_fail("zones", "the router built no %s" % zone_name)
		return Rect2()
	return control.get_global_rect()


# ----------------------------------------------------------------- steer ----


func _check_steer() -> void:
	var home: Vector2 = _zone("SteerZone").get_center()
	var travel: float = _touch.steer_travel_px

	_press(FINGER_A, home)
	_expect(is_zero_approx(_steer()), "steer", "a finger that has not moved steers nothing")

	_move(FINGER_A, home + Vector2(travel, 0.0))
	_expect(is_equal_approx(_steer(), 1.0), "steer", "a full travel right is full right lock")

	_move(FINGER_A, home + Vector2(-travel, 0.0))
	_expect(is_equal_approx(_steer(), -1.0), "steer", "a full travel left is full left lock")

	# Linear between the dead band and full lock. A curve is a legitimate future
	# choice; it is not what ships, and an unstated one is how a control ends up
	# feeling wrong with every counter reading correctly.
	var half: float = _touch.jitter_deadzone_px + (travel - _touch.jitter_deadzone_px) * 0.5
	_move(FINGER_A, home + Vector2(half, 0.0))
	_expect(is_equal_approx(_steer(), 0.5), "steer", "half the usable travel is half lock")

	# Inside the dead band. Reachable — raising `jitter_deadzone_px` past this
	# offset is what would move it — so this is a check and not a tautology.
	_move(FINGER_A, home + Vector2(_touch.jitter_deadzone_px, 0.0))
	_expect(is_zero_approx(_steer()), "steer", "a thumb inside the dead band steers nothing")

	# 🔴 **The arc.** `Q83` refuses a straight drift boundary because a thumb
	# rooted in a corner sweeps an arc; the same fact means a zone cannot be a
	# box the finger is confined to. Dragged far outside its own zone, the axis
	# must still read — clamping to the rect would make full lock unreachable
	# from a thumb that landed near an edge.
	_move(FINGER_A, home + Vector2(_zone("SteerZone").size.x * 2.0, 0.0))
	_expect(
		is_equal_approx(_steer(), 1.0), "steer", "a thumb dragged outside its own zone still steers"
	)

	_lift(FINGER_A, home)
	_expect(is_zero_approx(_steer()), "steer", "lifting the thumb returns the wheel to centre")

	# A finger that never landed in a zone owns nothing, and dragging it moves
	# nothing. The failure this catches is a zone test that accepts every touch.
	_press(FINGER_A, NOWHERE)
	_move(FINGER_A, NOWHERE + Vector2(500.0, 0.0))
	_expect(is_zero_approx(_steer()), "steer", "a finger outside every zone steers nothing")
	_lift(FINGER_A, NOWHERE)


# ----------------------------------------------------------------- drive ----


func _check_drive() -> void:
	var home: Vector2 = _zone("DriveZone").get_center()
	var travel: float = _touch.drive_travel_px

	_press(FINGER_A, home)
	# 🔴 **Centre is coast, and it is the one row here with a citation.**
	# `P0-5b/c/d` made one pedal serve brake and reverse, and lift-off is what
	# parks the car; a longitudinal axis whose centre carried any throttle would
	# make the taxi undriveable in exactly the situation a fare ends in.
	_expect(
		is_zero_approx(_accelerate()) and is_zero_approx(_brake()),
		"drive",
		"a finger that has not moved neither drives nor brakes"
	)

	# Up the screen is negative Y. If this pair is ever transposed the car brakes
	# when asked to accelerate.
	_move(FINGER_A, home + Vector2(0.0, -travel))
	_expect(
		is_equal_approx(_accelerate(), 1.0) and is_zero_approx(_brake()),
		"drive",
		"a full travel up is full throttle and no brake"
	)

	_move(FINGER_A, home + Vector2(0.0, travel))
	_expect(
		is_equal_approx(_brake(), 1.0) and is_zero_approx(_accelerate()),
		"drive",
		"a full travel down is full brake and no throttle"
	)

	# One axis, so the two halves are mutually exclusive by construction — and
	# construction is what this asserts, because the alternative shape (two
	# controls sharing a rest) is the one `Q83` rejected.
	_move(FINGER_A, home)
	_expect(
		is_zero_approx(_accelerate()) and is_zero_approx(_brake()),
		"drive",
		"returning to the origin coasts again"
	)

	# Sideways on the driving thumb does nothing today. `Q83` leaves that axis as
	# the standing candidate for `look_back`, so this is the assertion that has
	# to change when it is placed, rather than a silent second meaning.
	_move(FINGER_A, home + Vector2(travel * 2.0, 0.0))
	_expect(
		is_zero_approx(_accelerate()) and is_zero_approx(_brake()) and is_zero_approx(_steer()),
		"drive",
		"the driving thumb's horizontal axis is unassigned and moves nothing"
	)

	_lift(FINGER_A, home)
	_expect(is_zero_approx(_accelerate()), "drive", "lifting the thumb closes the throttle")


# ------------------------------------------------------------ two thumbs ----


## The pair, which is the half `--touch=mouse` can never reach.
func _check_two_thumbs() -> void:
	var steer_home: Vector2 = _zone("SteerZone").get_center()
	var drive_home: Vector2 = _zone("DriveZone").get_center()

	_press(FINGER_A, steer_home)
	_press(FINGER_B, drive_home)
	_move(FINGER_A, steer_home + Vector2(_touch.steer_travel_px, 0.0))
	_move(FINGER_B, drive_home + Vector2(0.0, -_touch.drive_travel_px))
	_expect(
		is_equal_approx(_steer(), 1.0) and is_equal_approx(_accelerate(), 1.0),
		"thumbs",
		"two thumbs drive their own axes at once"
	)

	# A second finger landing in a zone that is already held must not move the
	# origin out from under the first — which would jerk the wheel to centre
	# mid-corner, from a palm or a stray knuckle.
	_press(FINGER_B + 1, steer_home + Vector2(20.0, 0.0))
	_expect(
		is_equal_approx(_steer(), 1.0),
		"thumbs",
		"a second finger in a held zone does not steal its origin"
	)
	_lift(FINGER_B + 1, steer_home + Vector2(20.0, 0.0))

	# Releasing one thumb leaves the other exactly where it was. The failure this
	# catches is a shared release path, which reads as the throttle dropping
	# every time the player lets go of the wheel.
	_lift(FINGER_A, steer_home)
	_expect(
		is_zero_approx(_steer()) and is_equal_approx(_accelerate(), 1.0),
		"thumbs",
		"lifting the steering thumb leaves the throttle held"
	)
	_lift(FINGER_B, drive_home)


# -------------------------------------------------------------- override ----


## Touch overrides the action map per axis; it does not replace it.
##
## 🔴 **Both directions, and the first one is what protects the repo.** Every
## scripted drive runs on `Input.action_press` — `drive.sh --hold=` — so a router
## that took its axes from touch state unconditionally would read zero through
## every regression run, including `Q81`'s wrong-way route, and each of them
## would still exit `DRIVER OK` having driven nothing.
func _check_override() -> void:
	var home: Vector2 = _zone("SteerZone").get_center()

	Input.action_press(&"steer_right")
	_tick()
	_expect(
		is_equal_approx(_steer(), 1.0), "override", "the action map steers when no finger is down"
	)

	# The same held action, now with a centred thumb on that axis: touch wins,
	# and the answer is the thumb's 0.0 rather than the keyboard's 1.0.
	_press(FINGER_A, home)
	_expect(is_zero_approx(_steer()), "override", "a thumb on the axis overrides the action map")

	# ...and the axis nobody is touching is still the keyboard's. Per axis, not
	# per scheme, which is the whole of the rule.
	Input.action_press(&"accelerate")
	_tick()
	_expect(
		is_equal_approx(_accelerate(), 1.0),
		"override",
		"an axis with no finger on it stays with the action map"
	)

	_lift(FINGER_A, home)
	_expect(is_equal_approx(_steer(), 1.0), "override", "lifting the thumb hands the axis back")
	Input.action_release(&"steer_right")
	Input.action_release(&"accelerate")
	_tick()


# -------------------------------------------------------------- deferred ----


## `drift` and `look_back` have no touch home, and this is what says so out loud.
##
## ⚠️ **Asserted absent while the axis the drift will live on is being driven.**
## `Q83` puts the drift on thumb 2's vertical offset past a threshold with
## hysteresis, and `Q97` defers it because the two numbers need a handset. Until
## then that axis is read and discarded — so a change that wires it up without
## the threshold fails here rather than shipping a car that slides whenever the
## player's thumb drifts up the glass.
func _check_deferred() -> void:
	var home: Vector2 = _zone("SteerZone").get_center()
	_press(FINGER_A, home)
	_move(FINGER_A, home + Vector2(0.0, -_zone("SteerZone").size.y * 0.5))
	_expect(
		not bool(_router.drift),
		"deferred",
		"a vertical offset on the steering thumb does not drift yet"
	)
	_expect(not bool(_router.look_back), "deferred", "no touch gesture looks back yet")
	_lift(FINGER_A, home)


# ----------------------------------------------------------------- mouse ----


## `--touch=mouse`, the development aid, driven without the flag.
##
## 🔴 **Covered here because it cannot be covered anywhere else.** `driver.gd`
## presses the *action map*, so no scripted run can move a mouse — the flag is
## exercised by a person at a window and by nothing else, which means its
## plumbing would otherwise ship unchecked. The flag itself is set directly
## rather than passed on the command line, so `check.sh` does not have to invoke
## this tool differently from every other one.
##
## ⚠️ **One finger, asserted as such.** A second synthetic finger is offered
## while the mouse holds a zone and must be refused — that is what makes "this
## cannot see a two-thumb defect" a property of the aid rather than a hope.
func _check_mouse() -> void:
	var home: Vector2 = _zone("SteerZone").get_center()
	_router._mouse_is_a_finger = true

	_mouse_button(home, true)
	_mouse_move(home + Vector2(_touch.steer_travel_px, 0.0))
	_expect(is_equal_approx(_steer(), 1.0), "mouse", "a dragged mouse steers as one finger")

	# Motion with the button up is not a finger. Without this the pointer would
	# steer the car whenever it crossed the lower-left of the window.
	_mouse_button(home, false)
	_mouse_move(home + Vector2(-_touch.steer_travel_px, 0.0))
	_expect(is_zero_approx(_steer()), "mouse", "a released mouse steers nothing")

	# Off by default is the shipped state, so it is the one worth asserting: with
	# the flag down, the same gesture must do nothing at all.
	_router._mouse_is_a_finger = false
	_mouse_button(home, true)
	_mouse_move(home + Vector2(_touch.steer_travel_px, 0.0))
	_expect(is_zero_approx(_steer()), "mouse", "without --touch=mouse the pointer is not a finger")
	_mouse_button(home, false)


func _mouse_button(at: Vector2, pressed: bool) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	event.position = at
	event.pressed = pressed
	_router._input(event)
	_tick()


func _mouse_move(to: Vector2) -> void:
	var event := InputEventMouseMotion.new()
	event.position = to
	_router._input(event)
	_tick()


# ----------------------------------------------------------------- driving ---
#
# The router's `_input` is called directly rather than through
# `Input.parse_input_event`. That keeps the events this tool invents out of the
# real input queue, where the autoload router — which is also in this tree —
# would see them too, and it is what makes a finger index mean one thing.


func _press(index: int, at: Vector2) -> void:
	_send(index, at, true)


func _lift(index: int, at: Vector2) -> void:
	_send(index, at, false)


func _send(index: int, at: Vector2, pressed: bool) -> void:
	var event := InputEventScreenTouch.new()
	event.index = index
	event.position = at
	event.pressed = pressed
	_router._input(event)
	_tick()


func _move(index: int, to: Vector2) -> void:
	var event := InputEventScreenDrag.new()
	event.index = index
	event.position = to
	_router._input(event)
	_tick()


## One physics step. The router samples in `_physics_process`, so nothing it
## publishes changes until one runs — reading a field straight after an event
## would report the previous tick and pass or fail for the wrong reason.
func _tick() -> void:
	_router._physics_process(TICK)


func _steer() -> float:
	return _router.steer


func _accelerate() -> float:
	return _router.accelerate


func _brake() -> float:
	return _router.brake_reverse


func _expect(condition: bool, area: String, what: String) -> void:
	if condition:
		print("  %s: %s" % [area, what])
		return
	_fail(area, what)


func _fail(area: String, what: String) -> void:
	_failed += 1
	printerr("  FAIL %s: %s" % [area, what])
