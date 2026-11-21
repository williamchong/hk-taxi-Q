class_name DayClock
extends Node
## Game time for the rig (`Q160`, the user's ask: a mode that runs from day to
## night as game time): the seconds driven since the start, handed to a
## `LightingRig` as its `time_of_day`.
##
## The rig is not its own clock. What "game time" means — driving time, not
## menu time, not wall time — is the level's to say, and the rig is instanced
## by scenes that have no game at all.
##
## **The shift's clock too** (`Q162`): in `Mode.SHIFT` the same seconds are
## 特更's hours (`ShiftProfile`), the day always runs whatever the option says,
## and the last game second emits `closed` — 交更. The rig's `length_s` is the
## shift's length, so the sky and the clock on the dash end together. One
## clock, never a second one beside the rig's (`Q160`).
##
## ⚠️ **On the physics tick, so a scripted drive repeats.** The hour is a
## function of ticks driven and nothing else; a clock on the frame would light
## two runs of one route differently and `drive.sh`'s A/B frames with them.
##
## ⚠️ **The rig is moved `RigCycle.update_hz` times a second, not every tick.**
## Each move re-renders the sky's radiance; a four-minute dusk does not need
## sixty of those a second to read as smooth.

## The shift has reached its closing hour: no new fare, and the one aboard is
## the last.
signal closed

## How a run is played (`Q162`). FREE is the drive as it always was — no end,
## the hour the option's; SHIFT is 特更, morning to night, then the total.
enum Mode { FREE, SHIFT }
## Free mode's hour (the user's ask), picked as the drive begins and changed on
## its pause: the day running to night, the daylight held, the night held.
enum FreeTime { CYCLE, DAY, NIGHT }

## `--day-cycle=off` holds the authored daylight, `on` runs the day, `night`
## holds the night (free mode's alone), and each beats the saved option —
## `drive.sh` appends `off`, so every scripted frame is the daylight one it
## always was unless a run asks for the hour to move.
## In a shift it holds the light alone: the shift still runs and still ends.
const CYCLE_ARG: String = "--day-cycle="
## `--mode=shift` plays a shift with no menu to pick it; anything else, free.
const MODE_ARG: String = "--mode="
## `--shift-s=<seconds>` runs the whole shift in that many game seconds, for a
## frame of the handover without fourteen minutes of driving. Dev only.
const SHIFT_S_ARG: String = "--shift-s="

## The rig this clock moves. Assign in the scene.
@export var rig: LightingRig
## The car whose `parked` holds the clock: under the start menu no game time
## passes. Assign in the scene; without one the clock runs from boot.
@export var vehicle: VehicleController

## The run's mode. Set before the car first drives off; `restart` re-reads it.
var mode: Mode = Mode.FREE
## Game seconds driven.
var elapsed_s: float = 0.0
## The game second a free drive's day counts its hour from: 0 for a day run
## from the start, later where the pause turned it on mid-drive
## (`set_free_time`). Always 0 in a shift.
var day_from_s: float = 0.0

var _due_s: float = 0.0
## Whether the mode has been read. Not at `_ready`: the menu saves the option
## while the car is parked, after this node readied.
var _decided: bool = false
## Whether the rig is moved this run; a shift may count with it held.
var _cycling: bool = false
var _shift: ShiftProfile = null
## The shift's length in game seconds, 0 outside a shift.
var _shift_s: float = 0.0
var _closed: bool = false


## Free mode's hour: the flag, then the saved option.
static func free_time() -> FreeTime:
	if Cmdline.off(CYCLE_ARG):
		return FreeTime.DAY
	match Cmdline.value(CYCLE_ARG).to_lower():
		"on":
			return FreeTime.CYCLE
		"night":
			return FreeTime.NIGHT
	return free_time_of(Settings.free_time())


## The hour `code` in `Settings.FREE_TIMES` names: `FreeTime.CYCLE` for "cycle".
static func free_time_of(code: String) -> FreeTime:
	return FreeTime[code.to_upper()] as FreeTime


## `time`'s name in `Settings.FREE_TIMES`: "cycle" for `FreeTime.CYCLE`.
static func free_time_code(time: FreeTime) -> String:
	return str(FreeTime.find_key(time)).to_lower()


## The mode a run without a menu plays: `--mode=shift`, or free.
static func mode_from_flag() -> Mode:
	return Mode.SHIFT if Cmdline.value(MODE_ARG).to_lower() == "shift" else Mode.FREE


func _ready() -> void:
	restart()


## Back to the first second, in `mode`: the next shift, or a free drive after
## one. The rig is put back to what the run opens on — the morning where the
## day will run, the authored daylight where it is held (`Q222`), the night
## where free mode holds that.
func restart() -> void:
	elapsed_s = 0.0
	day_from_s = 0.0
	_due_s = 0.0
	_decided = false
	_closed = false
	_shift_s = 0.0
	# Read here and not at the drive-off, so a parked shift already reads its
	# opening hour.
	_shift = load(ShiftProfile.PATH) as ShiftProfile if mode == Mode.SHIFT else null
	# Judged once: a broken table is said here, not at every read of the hour.
	if _shift != null and not _shift.usable():
		_shift = null
	if _moves_rig():
		if _runs_day():
			rig.time_of_day = 0.0
		else:
			_hold(_held_time())
	set_physics_process(_moves_rig() or mode == Mode.SHIFT)


## A saved run's clock (`Q253`): `restart`, then `at_s` game seconds on, its
## day counted from `from_s` (`day_from_s`). The
## first tick off the parked car decides the run as for a new one, and the
## rig's next move reads the hour from these seconds, so the sky catches up
## within one `RigCycle.update_hz` step. A shift saved past 交更 closes again
## on that tick, the passenger aboard still the last.
func resume_at(at_s: float, from_s: float = 0.0) -> void:
	restart()
	elapsed_s = maxf(at_s, 0.0)
	day_from_s = from_s


## A free drive's hour switched under its pause (the user's ask). A day turned
## on runs from the look the drive stands in — `RigCycle.day_at`, the authored
## daylight, or `night_at` — so the sky does not jump; a day turned off holds
## the daylight or the night at once, and the clock stops counting. A shift's day is not the
## option's, and a clock not yet decided reads the saved option at the
## drive-off anyway.
func set_free_time(time: FreeTime) -> void:
	if not _free() or not _decided or not _moves_rig():
		return
	if time != FreeTime.CYCLE:
		_cycling = false
		_hold(time)
		set_physics_process(false)
		return
	if _cycling:
		return
	_cycling = true
	# A resting rig reads `time_of_day` 0, not the daylight it shows.
	var held_at: float = rig.cycle.day_at if rig.resting else rig.time_of_day
	day_from_s = elapsed_s - held_at * rig.cycle.length_s
	rig.time_of_day = held_at
	_due_s = 1.0 / rig.cycle.update_hz
	set_physics_process(true)


## Stand the rig at `at` with no game time passing: the boot menu's hour
## (`DriveLevel.light_showroom`). The next `restart` puts the run's own back.
func show_hour(at: float) -> void:
	if _moves_rig():
		rig.time_of_day = at


## Whether a shift is running and has not yet closed.
func on_shift() -> bool:
	return _shift_s > 0.0 and not _closed


## Whether the shift reached its closing hour.
func is_closed() -> bool:
	return _closed


## The hour on the shift's clock, 24-hour; the opening hour before the car
## drives off, NAN outside a shift or on a shift table that is not whole.
func hour_now() -> float:
	if _shift == null or mode != Mode.SHIFT:
		return NAN
	if _shift_s <= 0.0:
		return _shift.opens_h
	return _shift.hour_at(elapsed_s / _shift_s)


## `at_h` on a 24-hour clock face, to the minute begun: 14.999 is "14:59",
## and 24 wraps to "00:00".
static func clock_text(at_h: float) -> String:
	var minutes: int = floori(at_h * 60.0 + 1e-6)
	return "%02d:%02d" % [posmod(floori(minutes / 60.0), 24), minutes % 60]


## The hour the shift closes, NAN outside a shift.
func closes_h() -> float:
	if _shift == null or mode != Mode.SHIFT:
		return NAN
	return _shift.closes_h


func _physics_process(delta: float) -> void:
	if vehicle != null and vehicle.parked:
		return
	if not _decided:
		_decided = true
		_decide()
		if not _cycling and _shift_s <= 0.0:
			set_physics_process(false)
			return
	elapsed_s += delta
	if _shift_s > 0.0 and not _closed and elapsed_s >= _shift_s:
		_closed = true
		closed.emit()
	if not _cycling:
		if _closed:
			set_physics_process(false)
		return
	_due_s -= delta
	if _due_s > 0.0:
		return
	# Added to, not assigned, for `VehicleLamps._settle`'s reason: assigning
	# discards the overshoot and the rate lands under the dial.
	_due_s += 1.0 / rig.cycle.update_hz
	# Through the shift's own length where one runs, so `--shift-s=` speeds the
	# sky with the clock.
	var length_s: float = _shift_s if _shift_s > 0.0 else rig.cycle.length_s
	var at: float = (elapsed_s - day_from_s) / length_s
	if _shift_s <= 0.0 and rig.cycle.loop_at > 0.0:
		# A free drive's day comes round (`Q225`): night, a dawn, the morning.
		rig.time_of_day = fposmod(at, rig.cycle.loop_at)
		return
	rig.time_of_day = minf(at, 1.0)
	if at >= 1.0 and (_shift_s <= 0.0 or _closed):
		# The look at 1.0 holds; there is nothing left to move.
		set_physics_process(false)


## What this run does, read when the car first drives off: a shift always
## runs the day unless the flag holds it; free mode asks the option.
func _decide() -> void:
	_shift_s = 0.0
	if mode == Mode.SHIFT:
		var cycle: RigCycle = rig.cycle if rig != null else null
		if cycle == null:
			cycle = load(RigCycle.PATH) as RigCycle
		if _shift != null and cycle != null and cycle.usable():
			_shift_s = cycle.length_s
			var wanted_s: String = Cmdline.value(SHIFT_S_ARG)
			if wanted_s.is_valid_float() and wanted_s.to_float() > 0.0:
				_shift_s = wanted_s.to_float()
		else:
			push_error("DayClock: no usable shift table; this run plays free.")
			_shift = null
	# Read again here: the option can change under the menu, after `restart`
	# showed its guess.
	_cycling = _moves_rig() and _runs_day()
	if _moves_rig() and not _cycling:
		_hold(_held_time())


## Whether the run plays free: free mode, or a shift with no usable table.
func _free() -> bool:
	return mode != Mode.SHIFT or _shift == null


## What a run that does not move its sky holds: a free drive's pick, or a
## shift's daylight under `--day-cycle=off`.
func _held_time() -> FreeTime:
	return free_time() if _free() else FreeTime.DAY


## Stand the rig at the held `time`: the authored daylight at rest, or the
## cycle's night where it has one.
func _hold(time: FreeTime) -> void:
	if time == FreeTime.NIGHT and rig.cycle.night_at > 0.0:
		rig.time_of_day = rig.cycle.night_at
		return
	rig.rest()


## Whether this run's sky will move, as far as a parked clock can tell: a
## shift's unless the flag holds it, a free drive's by the option.
func _runs_day() -> bool:
	if not _free():
		return not Cmdline.off(CYCLE_ARG)
	return free_time() == FreeTime.CYCLE


## A rig with no usable cycle, or one pinned to an hour for a frame, has
## nothing for a clock to move.
func _moves_rig() -> bool:
	return rig != null and rig.moves() and not rig.pinned
