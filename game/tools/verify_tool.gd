## The base every counting verify tool extends: the failure counter, the two
## assertion shapes, the finish line and the watchdog, written once.
##
## Eight tools carried `_expect` / `_fail` / the end-of-run block by hand, four
## of them byte-identical and the rest drifted in their spacing, their summary
## channel and their "ok" line; only one had the watchdog. A tool extends this
## BY PATH — `extends "res://tools/verify_tool.gd"` — because a `--script` tool
## cannot resolve a `class_name` global on a fresh clone (`ARCHITECTURE.md`),
## and the chain still reaches `SceneTree`, which is what `--script` needs.
##
## 🔴 **A tool that aborts before `quit()` never exits.** `verify_hud.gd`
## records that a `preload`ed script failing to compile aborts the calling
## function on the spot; a `SceneTree` tool that aborts before its `quit()`
## then wedges `check.sh` and CI rather than failing them. It happened on
## `verify_input`'s first run, from an autoload identifier that does not exist
## under `--script`, and a guard inside the run cannot help because the abort is
## at the guard itself. `_start_watchdog` is a separate coroutine, so an abort
## inside the run cannot take it down too. The tools that run as a deferred
## coroutine arm it in `_init`; a tool whose whole run is `_init` needs none,
## since an abort there exits the process.
##
## ⚠️ `check.sh` parses none of these lines; it reads the exit code and greps
## stderr for a parse or compile error. The wording here is for a reader.
extends SceneTree

var _failed: int = 0
## Set by `_finish`, read by the watchdog.
var _finished: bool = false


## An assertion by area: printed as it passes, counted as it fails.
func _expect(condition: bool, area: String, what: String) -> void:
	if condition:
		print("  %s: %s" % [area, what])
		return
	_fail(area, what)


func _fail(area: String, what: String) -> void:
	_failed += 1
	printerr("  FAIL %s: %s" % [area, what])


## A failure with no area: the shape the mesh, vehicle and beam tools use,
## whose checks print their own "ok" lines as they go.
func _problem(message: String) -> void:
	_failed += 1
	printerr("  FAIL  %s" % message)


## The end of the run: the count on stderr and exit 1, or the tool's name and
## exit 0. `label` is the tool's name, so the line says which tool spoke.
func _finish(label: String) -> void:
	_finished = true
	if _failed > 0:
		printerr("  FAIL  %s: %d check(s) failed" % [label, _failed])
		quit(1)
		return
	print("  ok    %s" % label)
	quit(0)


## Fail the run if `_finish` is not reached within `seconds`. Armed from
## `_init` by a tool whose run is a deferred coroutine.
func _start_watchdog(label: String, seconds: float) -> void:
	await create_timer(seconds).timeout
	if _finished:
		return
	push_error(
		(
			"%s: gave up after %.0f s without finishing — a depended script almost certainly failed to compile, which aborts the run mid-function"
			% [label, seconds]
		)
	)
	quit(1)
