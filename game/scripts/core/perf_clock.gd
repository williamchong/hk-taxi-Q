class_name PerfClock
extends RefCounted
## Where a frame's script time went, by system, for `--perf-log=` (`P2-6`).
##
## `PerfRecorder` logs `process_ms` and `physics_ms` as totals, which say that a
## tick is dear and never which system made it so: the traffic, the trams, the
## fare loop, the signals and the streamer all run inside those two numbers.
## Each brackets its own tick with `begin` / `end`, and the recorder takes the
## sums a frame. The boot is the same question asked once: `boot` keeps how long
## each layer's `_ready` and the JSON parses took (`Q209`: "measured first").
##
## **Inert unless the recorder is built.** `enabled` is false without
## `--perf-log=`, and a bracket is then two reads of a static bool.

enum Slot { TRAFFIC, TRAMS, FARES, SIGNALS, STREAMER }

## A column a slot, in `Slot`'s order.
const NAMES: PackedStringArray = ["traffic", "trams", "fares", "signals", "streamer"]

static var enabled: bool = false
static var _usec: PackedInt64Array = PackedInt64Array([0, 0, 0, 0, 0])
## Milliseconds by what was booted, in the order each first finished.
static var _boot_ms: Dictionary[String, float] = {}


## The clock to hand back to `end` or `boot`; 0 while nothing records.
static func begin() -> int:
	return Time.get_ticks_usec() if enabled else 0


## `slot` ran from `began` to now. Sums over a frame: a frame may hold two
## physics ticks, or none.
static func end(slot: Slot, began: int) -> void:
	if enabled:
		_usec[slot] += Time.get_ticks_usec() - began


## What `slot` has cost since the last `take`, in milliseconds, and clears it.
static func take(slot: Slot) -> float:
	var ms: float = float(_usec[slot]) / 1000.0
	_usec[slot] = 0
	return ms


## `what` took from `began` to now at boot. A name met twice is summed — every
## region's railings layer is one line.
static func boot(what: String, began: int) -> void:
	if enabled:
		_boot_ms[what] = _boot_ms.get(what, 0.0) + float(Time.get_ticks_usec() - began) / 1000.0


## The boot's spans, dearest first, one summary line each.
static func boot_lines() -> PackedStringArray:
	var names: Array[String] = _boot_ms.keys()
	names.sort_custom(func(a: String, b: String) -> bool: return _boot_ms[a] > _boot_ms[b])
	var lines := PackedStringArray()
	for what: String in names:
		lines.append("perf: boot %s %.1f ms" % [what, _boot_ms[what]])
	return lines


## Stop recording and forget everything: the recorder's exit, and a check's.
static func reset() -> void:
	enabled = false
	_usec.fill(0)
	_boot_ms.clear()
