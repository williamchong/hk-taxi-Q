class_name Cmdline
extends RefCounted
## The command line, read once and the same way by everything that takes a
## flag (`P5-25`). A `class_name` static rather than a method on an autoload:
## a flag reader has no state and no node, and reaching it through `DebugHud`
## gave every flag-taking script — the HUD, the router, the asset viewer — a
## dependency on dev chrome for a string lookup.
##
## ⚠️ **Both argument lists, because the flag arrives through either.** Godot
## splits the command line at `--`: what comes before is the engine's and
## reaches `get_cmdline_args`, what comes after is the caller's and reaches
## `get_cmdline_user_args` alone. `drive.sh` passes everything after the
## dashes, so a reader of the first list alone — which is what `fps_counter.gd`
## once was — misses every flag a scripted run sends. That defect is why there
## is one reader and not one per script.


## Every argument from both halves, in order.
static func arguments() -> PackedStringArray:
	var found: PackedStringArray = OS.get_cmdline_args()
	found.append_array(OS.get_cmdline_user_args())
	return found


## What follows `prefix` on the first argument that starts with it — the value
## of `--flag=value` for a `prefix` of `--flag=` — or "" where no argument does.
static func value(prefix: String) -> String:
	for argument: String in arguments():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""


## Whether `flag` was passed exactly.
static func has(flag: String) -> bool:
	return arguments().has(flag)
