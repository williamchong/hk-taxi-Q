class_name ControlOptions
extends RefCounted
## The player's picks that change how a drive handles or runs (`Q223`): the
## touch steering's response, which thumb steers, and a phone's frame cap.
##
## ⚠️ **A dev flag beats a saved option**, as `Locale.language()` reads
## `--lang=` first: a scripted touch run must steer the same on every machine
## whatever was last picked in the menu on it, so `drive.sh` names both flags.
## The frame cap has no flag: it is set on a phone alone, and no scripted run
## is one.

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


## Set the saved cap on a phone: `Main` at boot, the options menu on a change.
static func apply_frame_cap() -> void:
	if caps_frames():
		Engine.max_fps = Settings.frame_cap()
