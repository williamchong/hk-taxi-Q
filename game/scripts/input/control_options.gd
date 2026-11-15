class_name ControlOptions
extends RefCounted
## The player's picks that change how a drive handles or runs (`Q223`): the
## touch steering's response, which thumb steers, and a phone's frame cap.
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

const GENTLE: String = "gentle"
const NORMAL: String = "normal"
const SHARP: String = "sharp"
## In the order the menu offers them.
const STEERINGS: PackedStringArray = [GENTLE, NORMAL, SHARP]
const SIDE_LEFT: String = "left"
const SIDE_RIGHT: String = "right"
const MAX_FPS_SETTING: String = "application/run/max_fps"

## The cap the engine booted with, read at the first apply; -1 before it.
static var _boot_cap: int = -1


## The steering response this run drives with: one of `STEERINGS`.
static func steering() -> String:
	return resolve_steering(Cmdline.value(STEER_ARG), Settings.steering())


## Whether the thumbs swap sides this run: steering under the right thumb, the
## pedals under the left.
static func steer_on_right() -> bool:
	return resolve_steer_on_right(Cmdline.value(SIDE_ARG), Settings.steer_on_right())


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
	if not caps_frames():
		return
	if _boot_cap < 0:
		_boot_cap = Engine.max_fps
	if _boot_cap == int(ProjectSettings.get_setting_with_override(MAX_FPS_SETTING)):
		Engine.max_fps = frame_cap()
