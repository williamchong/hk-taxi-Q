class_name ControlOptions
extends RefCounted
## The player's picks that change how a drive handles or runs (`Q223`): the
## touch steering's response, whether the thumbs' controls stand still (`Q239`),
## which thumb steers, and a phone's frame cap.
##
## ⚠️ **A dev flag beats a saved option**, as `Locale.language()` reads
## `--lang=` first: a scripted touch run must steer the same on every machine
## whatever was last picked in the menu on it, so `drive.sh` names both flags.
## The frame cap's flag is the engine's own `--max-fps` (`apply_frame_cap`).

## `--touch-steer=gentle|normal|sharp`.
const STEER_ARG: String = "--touch-steer="
## `--touch-side=left|right`: the side of the screen the STEERING thumb is on.
## Left is the scheme as first shipped, the pedals under the right thumb.
const SIDE_ARG: String = "--touch-side="

## `--touch-anchor=relative|fixed`: where the thumbs' controls stand (`Q239`).
const ANCHOR_ARG: String = "--touch-anchor="

const GENTLE: String = "gentle"
const NORMAL: String = "normal"
const SHARP: String = "sharp"
## In the order the menu offers them.
const STEERINGS: PackedStringArray = [GENTLE, NORMAL, SHARP]
## Each control stands where its thumb lands and reads from there (`Q83`), the
## scheme as first shipped; or it stays at its rest and reads from its middle,
## so a thumb put down off-centre is already steering or on a pedal.
const RELATIVE: String = "relative"
const FIXED: String = "fixed"
const ANCHORS: PackedStringArray = [RELATIVE, FIXED]
const SIDE_LEFT: String = "left"
const SIDE_RIGHT: String = "right"
const MAX_FPS_SETTING: String = "application/run/max_fps"

## The cap the engine booted with, read at the first apply; -1 before it.
static var _boot_cap: int = -1
## The cap in force when the pause took the frame rate (`hold_frames`), 0 for
## none; -1 while nothing holds it.
static var _held_cap: int = -1


## The steering response this run drives with: one of `STEERINGS`.
static func steering() -> String:
	return resolve_steering(Cmdline.value(STEER_ARG), Settings.steering())


## Whether the thumbs swap sides this run: steering under the right thumb, the
## pedals under the left.
static func steer_on_right() -> bool:
	return resolve_steer_on_right(Cmdline.value(SIDE_ARG), Settings.steer_on_right())


## Where the thumbs' controls stand this run: one of `ANCHORS`.
static func anchor() -> String:
	return resolve_anchor(Cmdline.value(ANCHOR_ARG), Settings.anchor())


## `flag`, else `saved`, else RELATIVE: the first that names one.
static func resolve_anchor(flag: String, saved: String) -> String:
	for asked: String in [flag.to_lower(), saved]:
		if asked in ANCHORS:
			return asked
	return RELATIVE


## `flag`, else `saved`, else NORMAL: the first that names a response. Apart
## from the readers so a check can ask without a command line.
static func resolve_steering(flag: String, saved: String) -> String:
	for asked: String in [flag.to_lower(), saved]:
		if asked in STEERINGS:
			return asked
	return NORMAL


## `flag` where it names a side, else `saved`.
static func resolve_steer_on_right(flag: String, saved: bool) -> bool:
	match flag.to_lower():
		SIDE_RIGHT:
			return true
		SIDE_LEFT:
			return false
	return saved


## Whether this run takes a frame cap at all: a phone, the app or its browser.
## A desk is uncapped (`ARCHITECTURE.md`, "Project settings") and stays so.
static func caps_frames() -> bool:
	return Handset.is_phone(OS.has_feature)


## The caps a screen refreshing at `refresh_hz` is offered, fastest first:
## `Settings.FRAME_CAPS`, and 120 above them where the screen shows it
## (`Q223`). A screen that does not say (-1, a browser) is not offered it.
## Pure, so a check can ask about a screen it does not have.
static func caps_for(refresh_hz: float) -> PackedInt32Array:
	var caps: PackedInt32Array = Settings.FRAME_CAPS.duplicate()
	# A hertz under: a 120 Hz panel may report 119.88.
	if refresh_hz >= float(Settings.FRAME_CAP_FAST) - 1.0:
		caps.insert(0, Settings.FRAME_CAP_FAST)
	return caps


## The caps this device's screen is offered.
static func frame_caps() -> PackedInt32Array:
	return caps_for(DisplayServer.screen_get_refresh_rate())


## The saved cap as this device's screen can show it.
static func frame_cap() -> int:
	return Settings.frame_cap(frame_caps())


## Set the saved cap on a phone: `Main` at boot, the options menu on a change.
## The engine's own `--max-fps` beats it, like every flag over a saved option:
## `--max-fps 120` is the handset's headroom gauge (`P2-6`, `perf_recorder.gd`).
## ⚠️ The engine consumes that flag, so no argument list holds it: it is read
## off the cap the engine booted with, against the project's — so a flag that
## names the project's own 60 is not seen as one.
static func apply_frame_cap() -> void:
	# A pick made under the pause is saved and lands on `release_frames`.
	if not caps_frames() or _held_cap >= 0:
		return
	if _boot_cap < 0:
		_boot_cap = Engine.max_fps
	if _boot_cap == int(ProjectSettings.get_setting_with_override(MAX_FPS_SETTING)):
		Engine.max_fps = frame_cap()


## The cap a pause draws at (`Q165`): `pause_cap`, never above `running`, the
## cap in force — a pause may only slow the frames. 0 is no cap, on either
## side: a `pause_cap` of 0 holds nothing. Pure, so a check can ask.
static func held_cap(running: int, pause_cap: int) -> int:
	if pause_cap <= 0 or (running > 0 and running <= pause_cap):
		return running
	return pause_cap


## Slow the frames while the pause is up (`Q165`): nothing under it moves but
## the water and a blinker, and a phone left on it never sleeps. Every run, a
## desk's uncapped one most of all.
static func hold_frames(pause_cap: int) -> void:
	if _held_cap >= 0:
		return
	_held_cap = Engine.max_fps
	Engine.max_fps = held_cap(_held_cap, pause_cap)


## The pause is over: the cap it found, then the saved one, which the pause's
## own DISPLAY page may have changed. A desk and a `--max-fps` boot keep the
## first — `apply_frame_cap` leaves both alone.
static func release_frames() -> void:
	if _held_cap < 0:
		return
	Engine.max_fps = _held_cap
	_held_cap = -1
	apply_frame_cap()
