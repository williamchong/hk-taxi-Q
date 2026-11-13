extends "res://tools/verify_tool.gd"

## Does the handset frame recorder (`perf_recorder.gd`, `P2-6`) write what it
## says, summarise it right, and stay off unless asked?
##
## The recorder is the only instrument a phone run has — `drive.sh` cannot reach
## a PCK — so a figure it gets wrong is a figure nobody can re-derive. Three
## things are held: the summary's arithmetic on a known series, the CSV a short
## headless run writes (header, one row a frame, the tile column carrying an
## instantiation), and the gate, `armed_seconds()`, reading 0 on a command line
## without the flag. Headless draws nothing, so the render columns read 0 here;
## what they read on a device is the engine's own monitor.
##
## Everything is `load`ed by path, on `verify_tool.gd`'s rule.

const RECORDER_SCRIPT := "res://scripts/ui/perf_recorder.gd"
const STREAMER_SCRIPT := "res://scripts/city/city_streamer.gd"
const OUT_PATH := "user://verify_perf_recorder.csv"
const RUN_S := 1.0
const COLUMNS := 15
## `traffic_ms`, the first of `PerfClock`'s five columns.
const TRAFFIC_COLUMN := 9
const PerfClockScript = preload("res://scripts/core/perf_clock.gd")


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_perf_recorder", 30.0)


func _run() -> void:
	var recorder_script := load(RECORDER_SCRIPT) as GDScript
	var streamer_script := load(STREAMER_SCRIPT) as GDScript
	if recorder_script == null or streamer_script == null:
		_problem("a script did not load")
		_finish("verify_perf_recorder")
		return

	_check_summary(recorder_script)
	_check_parse(recorder_script)
	await _check_run(recorder_script, streamer_script)
	_finish("verify_perf_recorder")


func _check_summary(recorder_script: GDScript) -> void:
	var series := PackedFloat32Array()
	for ms: int in range(100, 0, -1):
		series.append(float(ms))
	var s: Dictionary = recorder_script.summarize(series)
	_expect(int(s["frames"]) == 100, "summary", "100 frames counted")
	_expect(
		is_equal_approx(s["p50"], 50.0) and is_equal_approx(s["p95"], 95.0),
		"summary",
		"nearest rank: p50 50, p95 95 (got %s, %s)" % [s["p50"], s["p95"]]
	)
	_expect(
		is_equal_approx(s["p99"], 99.0) and is_equal_approx(s["max"], 100.0),
		"summary",
		"p99 99, max 100 (got %s, %s)" % [s["p99"], s["max"]]
	)
	_expect(
		int(s["over_budget"]) == 84 and int(s["over_double"]) == 67,
		"summary",
		"84 frames over 16.7 ms, 67 over 33.3 (got %s, %s)" % [s["over_budget"], s["over_double"]]
	)
	var timed: String = recorder_script.timing_line(series, PackedFloat32Array([0.0, 0.0]))
	_expect(
		timed == "perf: gpu p50 50.00 p95 95.00 p99 99.00 ms, render cpu n/a",
		"summary",
		"a timed series prints its percentiles, an untimed one n/a (got %s)" % timed
	)
	var empty: Dictionary = recorder_script.summarize(PackedFloat32Array())
	_expect(
		int(empty["frames"]) == 0 and float(empty["max"]) == 0.0,
		"summary",
		"an empty run reads zeros"
	)


func _check_parse(recorder_script: GDScript) -> void:
	_expect(recorder_script.parse_seconds("") == 0.0, "gate", "no value is off")
	_expect(recorder_script.parse_seconds("180") == 180.0, "gate", "180 reads 180 s")
	_expect(
		recorder_script.parse_seconds("abc") < 0.0 and recorder_script.parse_seconds("-3") < 0.0,
		"gate",
		"a value that is not a positive number is refused, not read as off"
	)
	_expect(
		recorder_script.armed_seconds() == 0.0,
		"gate",
		"without --perf-log= nothing is armed, so DebugHud builds no recorder"
	)


func _check_run(recorder_script: GDScript, streamer_script: GDScript) -> void:
	var recorder: Variant = recorder_script.new()
	recorder.configure(RUN_S, 0.0, OUT_PATH)
	root.add_child(recorder)

	# One instantiation mid-run, which the tile column must carry exactly once.
	await create_timer(RUN_S * 0.5).timeout
	streamer_script.instantiated_total += 1
	# And one bracketed span, which the traffic's column must carry and no other.
	var began: int = PerfClockScript.begin()
	OS.delay_msec(3)
	PerfClockScript.end(PerfClockScript.Slot.TRAFFIC, began)
	await create_timer(RUN_S * 0.5 + 0.5).timeout

	_expect(not recorder.is_processing(), "run", "the recorder stopped itself after %.1f s" % RUN_S)
	recorder.queue_free()

	var text: String = FileAccess.get_file_as_string(OUT_PATH)
	var lines: PackedStringArray = text.strip_edges().split("\n")
	_expect(
		lines.size() > 0 and lines[0] == recorder_script.HEADER,
		"run",
		"the CSV opens on its header"
	)
	var names: PackedStringArray = str(recorder_script.HEADER).split(",")
	_expect(
		(
			names.size() == COLUMNS
			and names[4] == "gpu_ms"
			and names[5] == "render_cpu_ms"
			and names[COLUMNS - 1] == "tiles"
		),
		"run",
		"the header names %d columns, the render timings at 4 and 5 and tiles last" % COLUMNS
	)
	var rows: int = 0
	var tiles: int = 0
	var traffic_ms: float = 0.0
	var others_ms: float = 0.0
	var monotonic: bool = true
	var widths_ok: bool = true
	var last_t: float = -1.0
	for index: int in range(1, lines.size()):
		var fields: PackedStringArray = lines[index].split(",")
		if fields.size() != COLUMNS:
			widths_ok = false
			continue
		rows += 1
		var t: float = float(fields[0])
		if t <= last_t:
			monotonic = false
		last_t = t
		tiles += int(fields[COLUMNS - 1])
		traffic_ms += float(fields[TRAFFIC_COLUMN])
		for column: int in range(TRAFFIC_COLUMN + 1, COLUMNS - 1):
			others_ms += float(fields[column])
	_expect(rows >= 10, "run", "a row a frame (%d rows in %.1f s)" % [rows, RUN_S])
	_expect(widths_ok, "run", "every row has %d fields" % COLUMNS)
	_expect(monotonic, "run", "time only runs forward")
	_expect(tiles == 1, "run", "the one instantiation is in the tile column once (read %d)" % tiles)
	_expect(
		traffic_ms >= 3.0 and traffic_ms < 50.0 and others_ms == 0.0,
		"run",
		(
			"a 3 ms span bracketed as the traffic's is in its column and no other (%.2f, %.2f)"
			% [traffic_ms, others_ms]
		)
	)
	_expect(
		not PerfClockScript.enabled and PerfClockScript.begin() == 0,
		"run",
		"the clock stops with the recorder, and a bracket then reads no time"
	)

	var summary: String = FileAccess.get_file_as_string(OUT_PATH.get_basename() + "_summary.txt")
	var summary_lines: PackedStringArray = summary.strip_edges().split("\n")
	_expect(
		(
			summary_lines.size() == 6
			and summary_lines[2].contains("p99")
			and summary_lines[4] == "perf: gpu n/a, render cpu n/a"
			and summary_lines[5].begins_with("perf: script ms a frame it ran: traffic p50 ")
		),
		"run",
		"the summary is written beside the CSV, six lines, the headless render timings n/a"
	)
