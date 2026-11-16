extends "res://tools/verify_tool.gd"

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
## asserted to move nothing, and the deferred `handbrake` is asserted *absent* while
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
const TaxiHornScript = preload("res://scripts/vehicle/taxi_horn.gd")
const SettingsScript = preload("res://scripts/core/settings.gd")
const ControlOptionsScript = preload("res://scripts/input/control_options.gd")

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

## The check's own options file: the router reads the player's steering pick
## and thumb sides (`ControlOptions`, `Q223`), and a check must neither read
## this machine's nor overwrite them.
const SETTINGS_PATH: String = "user://verify_input_settings.cfg"

## How long `_run` gets before the watchdog (`verify_tool.gd`) gives up on it.
const WATCHDOG_S: float = 30.0

var _router: Node = null
var _touch: Resource = null
var _layout: Resource = null


func _init() -> void:
	# Deferred, then a frame, before anything is instanced. Autoloads are
	# registered on the first frame and not before, and the router reaches
	# `DebugHud`; `verify_vehicle.gd`'s header records the trap, whose failure
	# mode is a green run over an empty suite.
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_input", WATCHDOG_S)


func _run() -> void:
	await process_frame

	_touch = load(TouchProfileScript.PATH)
	_layout = load(HudLayoutScript.PATH)
	if _touch == null or _layout == null:
		_fail("load", "%s or %s did not load" % [TouchProfileScript.PATH, HudLayoutScript.PATH])
		_finish("verify_input")
		return

	_check_profile()

	_forget_settings_file()
	SettingsScript.use_file(SETTINGS_PATH)
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
	_check_wheel()
	_check_override()
	_check_keyboard_steer()
	_check_deferred()
	_check_mouse()
	_check_horn()
	await _check_pause()
	await _check_options()

	_forget_settings_file()
	SettingsScript.use_file(SettingsScript.PATH)
	_router.queue_free()
	_finish("verify_input")


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
	# A missing key reads 0.0, which `steer_from` drives as linear rather than
	# as a switch; this is what says the key is missing.
	_expect(_touch.steer_curve >= 1.0, "profile", "steer_curve is %.1f" % _touch.steer_curve)
	# The player's three (`Q223`): gentle is the larger power, and a missing
	# key reads 0.0 here too.
	_expect(
		(
			_touch.steer_curve_gentle > _touch.steer_curve
			and _touch.steer_curve > _touch.steer_curve_sharp
			and _touch.steer_curve_sharp >= 1.0
		),
		"profile",
		(
			"the curves run gentle %.1f > normal %.1f > sharp %.1f >= 1"
			% [_touch.steer_curve_gentle, _touch.steer_curve, _touch.steer_curve_sharp]
		)
	)
	# The thumb's slew at speed (`Q230`): 0 is off, and a missing key reads 0.
	_expect(
		_touch.steer_attack_at_top_s > 0.0,
		"profile",
		"steer_attack_at_top_s is %.2f" % _touch.steer_attack_at_top_s
	)
	# The wheel's return (`Q238`): a missing key reads 0, which is a wheel
	# that snaps to centre as it did before.
	_expect(
		_touch.steer_return_at_top_s > 0.0,
		"profile",
		"steer_return_at_top_s is %.3f" % _touch.steer_return_at_top_s
	)
	# The slide must be the larger reading along the wheel's top, or going
	# round would move it: the rim's travel over the slide's (`spin_share`).
	_expect(
		(
			_touch.wheel_radius_px > _touch.wheel_hub_px
			and _touch.wheel_hub_px > 0.0
			and _touch.rim_travel_px() >= _touch.steer_travel_px
		),
		"profile",
		(
			"the wheel is %.0f units round a %.0f hub, its lock %.0f of rim to the slide's %.0f"
			% [
				_touch.wheel_radius_px,
				_touch.wheel_hub_px,
				_touch.rim_travel_px(),
				_touch.steer_travel_px
			]
		)
	)
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
		_layout.steer_zone().encloses(_layout.steer_rest()),
		"zones",
		"the steer zone encloses the steering thumb's rest in design space"
	)
	_expect(
		_layout.drive_zone().encloses(_layout.drive_rest()),
		"zones",
		"the drive zone encloses the pedal thumb's rest in design space"
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

	# Shaped between the dead band and full lock by the table's stated curve
	# (`Q220`), and by nothing else: an unstated one is how a control ends up
	# feeling wrong with every counter reading correctly.
	var half: float = _touch.jitter_deadzone_px + (travel - _touch.jitter_deadzone_px) * 0.5
	var half_lock: float = pow(0.5, _touch.steer_curve)
	_move(FINGER_A, home + Vector2(half, 0.0))
	_expect(
		is_equal_approx(_steer(), half_lock),
		"steer",
		"half the usable travel is 0.5^steer_curve (%.3f) of full lock" % half_lock
	)
	_move(FINGER_A, home + Vector2(-half, 0.0))
	_expect(is_equal_approx(_steer(), -half_lock), "steer", "and the same share to the left")

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

	# The wheel is the car's, not the thumb's (`Q238`): let go on a standing
	# car it stays turned, and it comes back as the car rolls.
	_lift(FINGER_A, home)
	_router.steer_for(0.0, false, 1.0)
	_tick()
	_expect(is_equal_approx(_steer(), 1.0), "steer", "a lifted thumb leaves a standing car's wheel")
	_roll()
	_expect(is_zero_approx(_steer()), "steer", "and a rolling car returns it to centre")

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
	_roll()
	_expect(
		is_zero_approx(_steer()) and is_equal_approx(_accelerate(), 1.0),
		"thumbs",
		"lifting the steering thumb leaves the throttle held"
	)
	_lift(FINGER_B, drive_home)


# ------------------------------------------------------------------ keys ----


## The keyboard's input assist (`Q210`): which method steered last, and a
## key shaped into a linear input before the car sees it. Each case from the
## side that would read wrong — a key that reached the car whole is full lock in
## one tick, the input `Q174`'s lane change spun on.
func _check_keyboard_steer() -> void:
	# The table the router loaded, so the ramp is checked against what it shapes with.
	# Untyped: this tool names no `class_name` global (see the header).
	var keys: Resource = _router.keyboard_profile()
	if keys == null:
		_fail("keys", "the router loaded no keyboard_steer.tres")
		return
	var attack: float = keys.get("attack_s")
	var at_top: float = keys.get("attack_at_top_s")

	_router.steer_from_keys = false
	var key := InputEventKey.new()
	key.physical_keycode = KEY_D
	key.pressed = true
	_router._input(key)
	_expect(_router.steer_from_keys, "keys", "a steering key hands the steering to the keys")
	_router.steer_from_thumb = true
	_router._input(key)
	_expect(not _router.steer_from_thumb, "keys", "and takes it from a thumb")

	var resting := InputEventJoypadMotion.new()
	resting.axis = JOY_AXIS_LEFT_X
	resting.axis_value = 0.1
	_router._input(resting)
	_expect(
		_router.steer_from_keys, "keys", "a stick inside its dead zone leaves the keys steering"
	)
	var stick := InputEventJoypadMotion.new()
	stick.axis = JOY_AXIS_LEFT_X
	stick.axis_value = 1.0
	_router._input(stick)
	_expect(not _router.steer_from_keys, "keys", "a stick past its dead zone takes the steering")

	_router.steer_from_keys = true
	var home: Vector2 = _zone("SteerZone").get_center()
	_press(FINGER_A, home)
	_expect(not _router.steer_from_keys, "keys", "a steering thumb takes the steering")
	_lift(FINGER_A, home)

	# A stick or a thumb passes through as it reads.
	Input.action_press(&"steer_right", 0.6)
	_tick()
	_expect(
		is_equal_approx(_router.steer_for(0.0, false, TICK), _steer()),
		"keys",
		"an analogue input reaches the car as it reads"
	)

	# A key ramps: one tick at rest is one tick of `attack_s`, never full lock.
	Input.action_release(&"steer_right")
	_router.steer_from_keys = true
	_tick()
	_router.steer_for(0.0, false, TICK)
	Input.action_press(&"steer_right")
	_tick()
	_expect(
		is_equal_approx(_router.steer_for(0.0, false, TICK), TICK / attack),
		"keys",
		"a key held one tick at rest is one tick of attack_s"
	)
	# At the limiter the slow ramp, and the quick one when the car asks.
	var at_rest: float = TICK / attack
	_expect(
		is_equal_approx(_router.steer_for(1.0, false, TICK), at_rest + TICK / at_top),
		"keys",
		"at the limiter a key ramps at attack_at_top_s"
	)
	_expect(
		is_equal_approx(
			_router.steer_for(1.0, true, TICK), at_rest + TICK / at_top + TICK / attack
		),
		"keys",
		"the quick ramp is attack_s at any speed"
	)
	for i: int in ceili(attack / TICK) + 1:
		_router.steer_for(0.0, false, TICK)
	_expect(
		is_equal_approx(_router.steer_for(0.0, false, TICK), 1.0), "keys", "a held key reaches full"
	)
	# A curve shapes the slow ramp alone: one tick at rest is that tick's
	# progress to its power, and the quick ramp stays linear.
	var curve: float = keys.get("curve")
	Input.action_release(&"steer_right")
	_tick()
	_router.steer_for(0.0, false, TICK)
	keys.set("curve", 2.0)
	Input.action_press(&"steer_right")
	_tick()
	_expect(
		is_equal_approx(_router.steer_for(0.0, false, TICK), pow(TICK / attack, 2.0)),
		"keys",
		"a curve of 2 makes one tick at rest that tick's progress squared"
	)
	_expect(
		is_equal_approx(
			_router.steer_for(0.0, true, TICK), pow(TICK / attack, 2.0) + TICK / attack
		),
		"keys",
		"the quick ramp stays linear under a curve"
	)
	keys.set("curve", curve)
	for i: int in ceili(attack / TICK) + 1:
		_router.steer_for(0.0, false, TICK)
	# A reversal ramps the whole way; letting go does not ramp (the car's own
	# release returns the wheel).
	Input.action_release(&"steer_right")
	Input.action_press(&"steer_left")
	_tick()
	_expect(
		is_equal_approx(_router.steer_for(0.0, false, TICK), 1.0 - TICK / attack),
		"keys",
		"a reversal ramps from where the key was"
	)
	Input.action_release(&"steer_left")
	_tick()
	_expect(is_zero_approx(_router.steer_for(0.0, false, TICK)), "keys", "letting go is not ramped")

	# A thumb is slewed at speed and never at rest (`Q230`): the same analogue
	# reading, with the router told it is a thumb's.
	var slew: float = _touch.steer_attack_at_top_s
	_router.steer_from_keys = false
	_router.steer_from_thumb = true
	Input.action_press(&"steer_right", 0.6)
	_tick()
	_expect(
		is_equal_approx(_router.steer_for(0.0, false, TICK), _steer()),
		"keys",
		"a thumb at rest reaches the car as it reads"
	)
	Input.action_release(&"steer_right")
	_tick()
	_router.steer_for(1.0, false, TICK)
	Input.action_press(&"steer_right", 0.6)
	_tick()
	_expect(
		is_equal_approx(_router.steer_for(1.0, false, TICK), TICK / slew),
		"keys",
		"at the limiter a thumb adds lock at steer_attack_at_top_s"
	)
	_expect(
		is_equal_approx(_router.steer_for(1.0, true, TICK), _steer()),
		"keys",
		"a thumb's countersteer is not slewed"
	)
	Input.action_release(&"steer_right")
	_tick()
	_expect(
		is_zero_approx(_router.steer_for(1.0, false, TICK)),
		"keys",
		"a thumb letting go is not slewed"
	)
	_router.steer_from_thumb = false
	_router.steer_from_keys = true


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


# ----------------------------------------------------------------- wheel ----


## The wheel between touches, and the thumb that spins it (`Q238`).
func _check_wheel() -> void:
	var home: Vector2 = _zone("SteerZone").get_center()
	var travel: float = _touch.steer_travel_px
	var curve: float = _touch.steer_curve
	var back: float = _touch.steer_return_at_top_s

	# A thumb landing on a turned wheel takes it up from there.
	_press(FINGER_A, home)
	_move(FINGER_A, home + Vector2(travel, 0.0))
	_lift(FINGER_A, home)
	_press(FINGER_A, home)
	_expect(is_equal_approx(_steer(), 1.0), "wheel", "a thumb landing on a turned wheel holds it")
	_move(FINGER_A, home + Vector2(-travel, 0.0))
	_expect(is_zero_approx(_steer()), "wheel", "and a full travel back is centre, not the far lock")
	_move(FINGER_A, home)

	# The return is the car's speed's: half the table's seconds at the limiter
	# is half the wheel, and at half the limiter a quarter.
	_lift(FINGER_A, home)
	_router.steer_for(1.0, false, back * 0.5)
	_expect(
		is_equal_approx(_router.wheel_turn(), pow(0.5, curve)),
		"wheel",
		"half the return's seconds at the limiter leaves %.3f" % _router.wheel_turn()
	)
	_router.steer_for(0.5, false, back * 0.5)
	_tick()
	_expect(
		is_equal_approx(_steer(), pow(0.25, curve)),
		"wheel",
		"and as long again at half the limiter leaves %.3f" % _steer()
	)

	# A key takes the steering, and the wheel a thumb left with it.
	Input.action_press(&"steer_left")
	_tick()
	Input.action_release(&"steer_left")
	_tick()
	_expect(is_zero_approx(_steer()), "wheel", "a key takes a held wheel, and leaves none behind")

	_check_spin(home)


## A thumb that goes round the wheel turns it (`Q238`): the wheel hangs from
## where the thumb landed, so the thumb is on its twelve o'clock, and the turn
## is the thumb's angle round its middle. Nothing tells a spin from a slide.
func _check_spin(home: Vector2) -> void:
	var travel: float = _touch.steer_travel_px
	var curve: float = _touch.steer_curve
	var radius: float = _touch.wheel_radius_px
	var middle: Vector2 = home + Vector2(0.0, radius)

	_press(FINGER_A, home)
	_expect(
		_router.wheel_centre().is_equal_approx(middle) and _router.steer_touch()[0] == home,
		"spin",
		"the wheel's middle is a radius under where the thumb landed"
	)
	# 🔴 Along the top the slide is what steers, at every offset: the reading a
	# slide gave before there was a wheel to go round.
	var same: bool = true
	for i: int in 41:
		var x: float = travel * 1.5 * (i - 20) / 20.0
		_move(FINGER_A, home + Vector2(x, 0.0))
		same = same and is_equal_approx(_steer(), _touch.steer_from(x, curve))
	_expect(same, "spin", "a thumb sliding along the wheel's top steers as a slide alone does")
	_move(FINGER_A, home)

	# Round the rim, clockwise from the top, a twenty-fourth at a time.
	for i: int in 6:
		_move(FINGER_A, _on_circle(middle, radius, i + 1))
	var quarter: float = _touch.shape(_touch.spin_share(90.0), curve)
	_expect(
		is_equal_approx(_steer(), quarter) and quarter > _touch.steer_from(radius, curve),
		"spin",
		"a quarter round to three o'clock is %.3f, more than its sideways offset is worth" % quarter
	)
	for i: int in 6:
		_move(FINGER_A, _on_circle(middle, radius, i + 7))
	_expect(
		is_equal_approx(_steer(), 1.0),
		"spin",
		"at the bottom, with no sideways offset left, the wheel is at its lock"
	)
	for i: int in 6:
		_move(FINGER_A, _on_circle(middle, radius, i + 13))
	_expect(
		is_equal_approx(_steer(), 1.0),
		"spin",
		"on round to nine o'clock the turn steers, not the offset now on the other side"
	)
	# Back the way it came: what was wound is unwound, and no more.
	for i: int in 18:
		_move(FINGER_A, _on_circle(middle, radius, 17 - i))
	_expect(is_zero_approx(_steer()), "spin", "back round to the top is straight ahead")
	for i: int in 12:
		_move(FINGER_A, _on_circle(middle, radius, -(i + 1)))
	_expect(
		is_equal_approx(_steer(), -1.0), "spin", "and anticlockwise to the bottom is the other lock"
	)
	_lift(FINGER_A, home)
	_roll()

	# Straight down through the hub: no bearing is read off a finger on it.
	_press(FINGER_A, home)
	var hub_step: float = _touch.wheel_hub_px * 0.5
	var down: float = 0.0
	while down < radius * 2.0:
		down += hub_step
		_move(FINGER_A, home + Vector2(0.0, down))
	_expect(is_zero_approx(_steer()), "spin", "a thumb drawn down through the hub turns nothing")
	_lift(FINGER_A, home)
	_roll()
	# And in one move, both ends clear of the hub and the line between them
	# through it: read end to end that is half a turn, one way or the other.
	_press(FINGER_A, home)
	_move(FINGER_A, home + Vector2(_touch.jitter_deadzone_px * 0.5, radius * 2.0))
	_expect(is_zero_approx(_steer()), "spin", "a flick across the wheel turns nothing")
	_lift(FINGER_A, home)
	_roll()


## The point `twentyfourths` of the way round a circle, clockwise on the glass
## from its top.
func _on_circle(middle: Vector2, radius: float, twentyfourths: int) -> Vector2:
	return middle + Vector2.from_angle(-PI * 0.5 + TAU * twentyfourths / 24.0) * radius


# -------------------------------------------------------------- deferred ----


## `handbrake` and `look_back` have no touch home, and this is what says so out loud.
##
## ⚠️ **Asserted absent while the axis the handbrake will live on is being driven.**
## `Q83` puts the handbrake on thumb 2's vertical offset past a threshold with
## hysteresis, and `Q97` defers it because the two numbers need a handset. Until
## then that axis is read and discarded — so a change that wires it up without
## the threshold fails here rather than shipping a car that slides whenever the
## player's thumb drifts up the glass.
func _check_deferred() -> void:
	var home: Vector2 = _zone("SteerZone").get_center()
	_press(FINGER_A, home)
	_move(FINGER_A, home + Vector2(0.0, -_zone("SteerZone").size.y * 0.5))
	_expect(
		not bool(_router.handbrake),
		"deferred",
		"a vertical offset on the steering thumb does not pull the handbrake yet"
	)
	_expect(not bool(_router.look_back), "deferred", "no touch gesture looks back yet")
	_expect(not bool(_router.horn), "deferred", "no touch gesture sounds the horn yet")
	_lift(FINGER_A, home)


## The taxi's horn (`Q178`): the action reaches the router, and `TaxiHorn` sounds
## once per press, however long it is held.
func _check_horn() -> void:
	Input.action_press(&"horn")
	_tick()
	_expect(bool(_router.horn), "horn", "the horn action reaches the router")
	Input.action_release(&"horn")
	_tick()
	_expect(not bool(_router.horn), "horn", "and lets go with it")
	var horn: TaxiHorn = TaxiHornScript.new()
	for down: bool in [true, true, true, false, true]:
		horn.hold(down)
	_expect(horn.presses == 2, "horn", "two presses, one held, sound twice (%d)" % horn.presses)
	horn.free()


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
	# The wheel it left turned comes back first (`Q238`): what is asked here is
	# whether the pointer moves it, which full left lock would show.
	_mouse_button(home, false)
	_roll()
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

# ----------------------------------------------------------------- pause ----


## A paused tree sends the router no input (`Q165`), so a finger lifted over
## the pause menu is never released: both thumbs are let go as the pause
## starts, or the car resumes on the last steer and throttle with no finger
## down. The real tree's pause, not the notification called by hand.
func _check_pause() -> void:
	var steer_home: Vector2 = _zone("SteerZone").get_center()
	var drive_home: Vector2 = _zone("DriveZone").get_center()
	_press(FINGER_A, steer_home)
	_press(FINGER_B, drive_home)
	_move(FINGER_A, steer_home + Vector2(_touch.steer_travel_px, 0.0))
	_move(FINGER_B, drive_home + Vector2(0.0, -_touch.drive_travel_px))
	var held: bool = is_equal_approx(_steer(), 1.0) and is_equal_approx(_accelerate(), 1.0)
	paused = true
	await process_frame
	paused = false
	_tick()
	_expect(
		held and is_zero_approx(_steer()) and is_zero_approx(_accelerate()),
		"pause",
		"two thumbs held into a pause are let go by the time it resumes"
	)
	# The lifts the paused tree never delivered, arriving late, release nothing.
	_lift(FINGER_A, steer_home)
	_lift(FINGER_B, drive_home)
	_press(FINGER_A, steer_home)
	_move(FINGER_A, steer_home + Vector2(_touch.steer_travel_px, 0.0))
	_expect(is_equal_approx(_steer(), 1.0), "pause", "a thumb lands afresh after the pause")
	_lift(FINGER_A, steer_home)
	_roll()


# --------------------------------------------------------------- options ----


## The player's picks (`Q223`): a flag beats the saved one, the steering thumb
## answers to the curve picked once the router is told, and the thumbs swap
## sides — zones, rests and the screen's edges together.
func _check_options() -> void:
	_expect(
		(
			ControlOptionsScript.resolve_steering("SHARP", "gentle") == "sharp"
			and ControlOptionsScript.resolve_steering("", "gentle") == "gentle"
			and ControlOptionsScript.resolve_steering("quick", "") == "normal"
		),
		"options",
		"the steering reads the flag, then the saved pick, then normal"
	)
	_expect(
		(
			ControlOptionsScript.resolve_steer_on_right("left", true) == false
			and ControlOptionsScript.resolve_steer_on_right("right", false) == true
			and ControlOptionsScript.resolve_steer_on_right("", true) == true
		),
		"options",
		"the thumbs' sides read the flag, then the saved pick"
	)

	var home: Vector2 = _zone("SteerZone").get_center()
	var half: float = (
		_touch.jitter_deadzone_px + (_touch.steer_travel_px - _touch.jitter_deadzone_px) * 0.5
	)
	var curves: Dictionary[String, float] = {
		"sharp": _touch.steer_curve_sharp,
		"gentle": _touch.steer_curve_gentle,
		"normal": _touch.steer_curve,
	}
	_press(FINGER_A, home)
	for pick: String in curves:
		SettingsScript.set_steering(pick)
		_router.refresh_options()
		_move(FINGER_A, home + Vector2(half, 0.0))
		_expect(
			is_equal_approx(_steer(), pow(0.5, curves[pick])),
			"options",
			"picked %s, half the travel is %.3f of the lock" % [pick, _steer()]
		)
	_lift(FINGER_A, home)

	# The sides. In design space the swap takes the rests with it, so each zone
	# still encloses its own; on the screen each zone holds the other edge.
	SettingsScript.set_steer_on_right(true)
	_expect(
		(
			_layout.steer_zone() == _layout.touch_zone_right
			and _layout.drive_zone() == _layout.touch_zone_left
			and _layout.steer_zone().encloses(_layout.steer_rest())
			and _layout.drive_zone().encloses(_layout.drive_rest())
		),
		"options",
		"steering on the right swaps the zones, and each still encloses its rest"
	)
	_router.rebuild_zones()
	await process_frame
	await process_frame
	var canvas: Vector2 = get_root().get_visible_rect().size
	var steer_zone: Rect2 = _zone("SteerZone")
	_expect(
		(
			is_equal_approx(steer_zone.end.x, canvas.x)
			and is_zero_approx(_zone("DriveZone").position.x)
		),
		"options",
		"rebuilt, the steer zone holds the right edge and the drive zone the left"
	)
	home = steer_zone.get_center()
	_press(FINGER_A, home)
	_move(FINGER_A, home + Vector2(_touch.steer_travel_px, 0.0))
	_expect(
		is_equal_approx(_steer(), 1.0) and is_zero_approx(_accelerate()),
		"options",
		"a thumb on the right steers, and drives nothing"
	)
	_lift(FINGER_A, home)
	SettingsScript.set_steer_on_right(false)
	_router.rebuild_zones()
	await process_frame
	await process_frame
	_expect(
		is_zero_approx(_zone("SteerZone").position.x),
		"options",
		"swapped back, the steer zone holds the left edge again"
	)


func _forget_settings_file() -> void:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_PATH))


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


## A second at the limiter with no thumb down: a wheel left turned is back at
## centre (`Q238`), as the car the router is not under here would have had it.
func _roll() -> void:
	_router.steer_for(1.0, false, 1.0)
	_tick()


func _steer() -> float:
	return _router.steer


func _accelerate() -> float:
	return _router.accelerate


func _brake() -> float:
	return _router.brake_reverse
