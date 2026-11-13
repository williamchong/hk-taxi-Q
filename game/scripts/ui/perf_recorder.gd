extends Node
## A frame-by-frame record of a run, for the handset (`P2-6`).
##
## `drive.sh` prints `prims` / `draws` / `phys` per tick, but its driver is a
## `--script` from outside `res://` and never reaches a PCK, so on a phone the
## only number was `--print-fps`: one average a second, which smooths away the
## single long frame a tile instantiation costs — the hitch `P2-6` is told to
## re-measure. This writes every frame instead, to `user://`, where a launch
## argument can ask for it and `devicectl` can copy it off.
##
## **Inert unless asked.** `DebugHud` builds one only when `--perf-log=<s>` is
## on the command line, in any build, release included: a release build is the
## one a frame time means anything in. Without the flag nothing is built, so the
## shipped game pays nothing.
##
## ⚠️ **Frame time is read off the clock, never off `delta`.** Godot smooths
## `delta` (`application/run/delta_smoothing`, on by default), which is exactly
## the averaging this exists to get past.
##
## ⚠️ **At the vsync cap the frame time cannot show headroom**: a cheaper frame
## only waits longer for the next one, so every run on the Air read 16.7 ms
## whatever it carried. `gpu_ms` and `render_cpu_ms` are the renderer's own
## timings of the frame's work (`viewport_set_measure_render_time`), which do
## move when a GPU dial does. GPU timestamps come back a frame or two late, so a
## row's `gpu_ms` belongs to a frame just before it. ⚠️ **`gpu_ms` reads 0 under
## Metal** — Godot 4.7's Metal driver times nothing, on the Mac and the iPhone
## alike — so on iOS the headroom gauge is the frame rate under `--max-fps 120`
## on the Air's 120 Hz screen instead (`P2-6`). `process_ms` and `physics_ms`
## are Godot's time monitors, which hold a value for about a second, and
## `process_ms` is not the frame's CPU work: the Air read 11.8 ms of it at the
## 60 cap and then ran 120 fps uncapped.

const ARG: String = "--perf-log="
## Seconds at the start left out of the summary — boot, the loading cover and
## the shader warm-up (`Q207`'s first two seconds at 1 fps). The CSV keeps them.
const SKIP_ARG: String = "--perf-skip="
const DEFAULT_SKIP_S: float = 10.0
const DEFAULT_PATH: String = "user://perf.csv"
## A frame over this missed a 60 Hz vsync; over `DOUBLE_MS` it missed two.
const BUDGET_MS: float = 1000.0 / 60.0
const DOUBLE_MS: float = 2000.0 / 60.0
const HEADER: String = "t_s,frame_ms,process_ms,physics_ms,gpu_ms,render_cpu_ms,draws,prims,video_mem_mb,tiles"

## How long to record, in seconds from this node's first frame.
var seconds: float = 0.0
var skip_s: float = DEFAULT_SKIP_S
var path: String = DEFAULT_PATH

var _file: FileAccess = null
var _start_us: int = -1
var _last_us: int = -1
var _tiles_seen: int = 0
var _frames_ms: PackedFloat32Array = PackedFloat32Array()
var _gpu_ms: PackedFloat32Array = PackedFloat32Array()
var _render_cpu_ms: PackedFloat32Array = PackedFloat32Array()
var _viewport_rid: RID = RID()
## Summarised frames over `BUDGET_MS` that also instantiated a tile.
var _hitches_tiled: int = 0
var _done: bool = false
## Read in `_ready`, where the viewport is certain to exist.
var _scale_3d: float = 1.0
var _msaa_3d: int = -1


## The seconds `--perf-log=` asks for, or 0 where it is absent. A value that is
## not a positive number is refused out loud rather than read as "off": a run
## that meant to record and silently did not is a lost drive.
static func armed_seconds() -> float:
	var text: String = Cmdline.value(ARG)
	var seconds_asked: float = parse_seconds(text)
	if seconds_asked < 0.0:
		push_error("%s%s is not a positive number of seconds" % [ARG, text])
		return 0.0
	return seconds_asked


## `--perf-skip=`, or `DEFAULT_SKIP_S` where it is absent. 0 is allowed here,
## unlike `--perf-log=`; a value that is not a number is refused out loud.
static func armed_skip() -> float:
	var text: String = Cmdline.value(SKIP_ARG)
	if text.is_empty():
		return DEFAULT_SKIP_S
	if not text.is_valid_float() or float(text) < 0.0:
		push_error("%s%s is not a number of seconds" % [SKIP_ARG, text])
		return DEFAULT_SKIP_S
	return float(text)


## 0 for an absent value, -1 for one that is not a positive number.
static func parse_seconds(text: String) -> float:
	if text.is_empty():
		return 0.0
	if not text.is_valid_float() or float(text) <= 0.0:
		return -1.0
	return float(text)


## p50 / p95 / p99 / max of `frames_ms`, and how many missed one vsync and two.
## Nearest rank on a sorted copy, so every figure is a frame that happened.
static func summarize(frames_ms: PackedFloat32Array) -> Dictionary:
	var sorted: PackedFloat32Array = frames_ms.duplicate()
	sorted.sort()
	var count: int = sorted.size()
	var over: int = 0
	var over_double: int = 0
	for frame_ms: float in sorted:
		if frame_ms > BUDGET_MS:
			over += 1
		if frame_ms > DOUBLE_MS:
			over_double += 1
	return {
		"frames": count,
		"p50": _rank(sorted, 0.50),
		"p95": _rank(sorted, 0.95),
		"p99": _rank(sorted, 0.99),
		"max": sorted[count - 1] if count > 0 else 0.0,
		"over_budget": over,
		"over_double": over_double,
	}


static func _rank(sorted: PackedFloat32Array, fraction: float) -> float:
	if sorted.is_empty():
		return 0.0
	var index: int = clampi(ceili(fraction * float(sorted.size())) - 1, 0, sorted.size() - 1)
	return sorted[index]


## Set before the node enters the tree; `_ready` opens `path`.
func configure(record_s: float, summary_skip_s: float, csv_path: String = DEFAULT_PATH) -> void:
	seconds = record_s
	skip_s = summary_skip_s
	path = csv_path


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	# Before every other node's `_process`, so a frame's row is the gap between
	# two starts of a frame rather than wherever this sorted in the tree.
	process_priority = -1000
	var viewport: Viewport = get_viewport()
	_scale_3d = viewport.scaling_3d_scale
	_msaa_3d = int(viewport.msaa_3d)
	_viewport_rid = viewport.get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(_viewport_rid, true)
	_file = FileAccess.open(path, FileAccess.WRITE)
	if _file == null:
		push_error("perf: could not open %s (%s)" % [path, FileAccess.get_open_error()])
		set_process(false)
		return
	_file.store_line(HEADER)
	_tiles_seen = CityStreamer.instantiated_total
	print("perf: recording %.0f s to %s, summary skips the first %.0f s" % [seconds, path, skip_s])


func _process(_delta: float) -> void:
	var now_us: int = Time.get_ticks_usec()
	if _start_us < 0:
		_start_us = now_us
		_last_us = now_us
		return
	var t_s: float = float(now_us - _start_us) / 1e6
	var frame_ms: float = float(now_us - _last_us) / 1e3
	_last_us = now_us
	var tiles_total: int = CityStreamer.instantiated_total
	var tiles: int = tiles_total - _tiles_seen
	_tiles_seen = tiles_total
	var gpu_ms: float = RenderingServer.viewport_get_measured_render_time_gpu(_viewport_rid)
	var render_cpu_ms: float = RenderingServer.viewport_get_measured_render_time_cpu(_viewport_rid)
	(
		_file
		. store_line(
			(
				"%.6f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%d,%.1f,%d"
				% [
					t_s,
					frame_ms,
					Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
					Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
					gpu_ms,
					render_cpu_ms,
					int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
					int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)),
					Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0,
					tiles,
				]
			)
		)
	)
	if t_s >= skip_s:
		_frames_ms.append(frame_ms)
		_gpu_ms.append(gpu_ms)
		_render_cpu_ms.append(render_cpu_ms)
		if frame_ms > BUDGET_MS and tiles > 0:
			_hitches_tiled += 1
	if t_s >= seconds:
		_finish()


## The phone may background the app or kill it mid-run; what was written so far
## is kept either way. A run cut short gets no summary — the node may already be
## out of the tree — and the CSV holds every frame it saw.
func _notification(what: int) -> void:
	if _file == null or _done:
		return
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_WM_CLOSE_REQUEST:
		_file.flush()
	elif what == NOTIFICATION_PREDELETE:
		_file.close()


func _finish() -> void:
	if _done or _file == null:
		return
	_done = true
	set_process(false)
	_file.close()
	if _viewport_rid.is_valid():
		RenderingServer.viewport_set_measure_render_time(_viewport_rid, false)
	var lines: PackedStringArray = summary_lines()
	var summary_path: String = path.get_basename() + "_summary.txt"
	var out := FileAccess.open(summary_path, FileAccess.WRITE)
	if out == null:
		push_error("perf: could not open %s (%s)" % [summary_path, FileAccess.get_open_error()])
	for line: String in lines:
		print(line)
		if out != null:
			out.store_line(line)


## The run's summary, as printed and as written beside the CSV.
func summary_lines() -> PackedStringArray:
	var s: Dictionary = summarize(_frames_ms)
	var gpu: Dictionary = summarize(_gpu_ms)
	var render_cpu: Dictionary = summarize(_render_cpu_ms)
	var window: Vector2i = DisplayServer.window_get_size()
	return PackedStringArray(
		[
			"perf: %s, %s" % [OS.get_model_name(), "debug" if OS.is_debug_build() else "release"],
			(
				"perf: window %dx%d, 3D scale %.2f, msaa_3d %d"
				% [window.x, window.y, _scale_3d, _msaa_3d]
			),
			(
				"perf: %d frames after %.0f s: p50 %.2f p95 %.2f p99 %.2f max %.2f ms"
				% [s["frames"], skip_s, s["p50"], s["p95"], s["p99"], s["max"]]
			),
			(
				"perf: over %.1f ms %d (%d with a tile instantiated), over %.1f ms %d"
				% [BUDGET_MS, s["over_budget"], _hitches_tiled, DOUBLE_MS, s["over_double"]]
			),
			(
				"perf: gpu p50 %.2f p95 %.2f p99 %.2f, render cpu p50 %.2f p95 %.2f p99 %.2f ms"
				% [
					gpu["p50"],
					gpu["p95"],
					gpu["p99"],
					render_cpu["p50"],
					render_cpu["p95"],
					render_cpu["p99"]
				]
			),
		]
	)
