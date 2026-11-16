class_name Settings
extends RefCounted
## The player's saved options (`P6-1`): one `ConfigFile` under `user://`, read
## once and written on every change. The options menu is the only writer.
##
## ⚠️ **A dev flag beats a saved option.** `Locale.language()` reads `--lang=`
## first and this second, so a scripted run's frames never depend on what was
## last picked in the menu on this machine — `drive.sh`'s determinism (`Q27`)
## is the reason, and `Locale` says so beside the read.

const PATH: String = "user://settings.cfg"
const SECTION: String = "options"
const KEY_LANGUAGE: String = "language"
const KEY_DAY_CYCLE: String = "day_cycle"
const KEY_SOUND: String = "sound"
const KEY_VOLUME: String = "volume"
const KEY_STEERING: String = "steering"
const KEY_STEER_ON_RIGHT: String = "steer_on_right"
const KEY_ANCHOR: String = "anchor"
const KEY_FRAME_CAP: String = "frame_cap"
## The frame caps a phone is offered (`Q223`): the project's own 60
## (`application/run/max_fps.mobile`) and half of it, which is a whole number
## of a 60 Hz panel's refreshes and so paces evenly where 40 or 45 would not.
const FRAME_CAPS: PackedInt32Array = [60, 30]
## And the cap a 120 Hz screen is offered above them (`Q223`), a pick and
## never the default: `ControlOptions.frame_caps`.
const FRAME_CAP_FAST: int = 120
## The bus the sound options act on: every other bus sends to it.
const MASTER_BUS: StringName = &"Master"
## What the player has done, beside what they chose: the best shift's total.
const RECORDS: String = "records"
const KEY_SHIFT_BEST: String = "shift_best_hkd"
const KEY_SHIFTS: String = "shifts_finished"
## A skill's two lines in the lifetime books, under its name (`ExamSheet.key_of`).
const COUNT_SUFFIX: String = "_count"
const HKD_SUFFIX: String = "_hkd"
## The most of a skill one style combo held (`Q205`): `drift_combo_best`.
const COMBO_SUFFIX: String = "_combo_best"

## The file read and written: `PATH`, except under `verify_menu`, which round
## trips its own so a check never overwrites the player's choices.
static var _path: String = PATH
static var _file: ConfigFile = null


## The saved language code, or "" where none was ever saved.
static func language() -> String:
	return str(_read().get_value(SECTION, KEY_LANGUAGE, ""))


## Save `code`. Written at once: the file IS the option, and a write deferred
## to quit is one a crash loses.
static func set_language(code: String) -> void:
	_write(KEY_LANGUAGE, code)


## Whether the day runs to night as game time passes in free mode (`Q160`,
## `Q162`). Off where none was ever saved: free mode keeps the daylight (the
## user's ask), and 特更 runs the day whatever this says.
static func day_cycle() -> bool:
	return bool(_read().get_value(SECTION, KEY_DAY_CYCLE, false))


static func set_day_cycle(on: bool) -> void:
	_write(KEY_DAY_CYCLE, on)


## Whether the game sounds at all (the user's ask, 2026-11-16). On where none
## was ever saved.
static func sound_on() -> bool:
	return bool(_read().get_value(SECTION, KEY_SOUND, true))


static func set_sound_on(on: bool) -> void:
	_write(KEY_SOUND, on)


## How loud, 0 to 1 along the slider; full where none was ever saved. Clamped
## on the read, so a file edited by hand cannot boost the bus.
static func volume() -> float:
	return clampf(float(_read().get_value(SECTION, KEY_VOLUME, 1.0)), 0.0, 1.0)


static func set_volume(level: float) -> void:
	_write(KEY_VOLUME, clampf(level, 0.0, 1.0))


## The Master bus set to the saved sound options: `Main` at boot, the options
## menu on a change. Off, or a slider at nothing, mutes the bus — nothing in
## dB says silence.
static func apply_sound() -> void:
	var level: float = volume()
	var bus: int = AudioServer.get_bus_index(MASTER_BUS)
	AudioServer.set_bus_mute(bus, not sound_on() or level <= 0.0)
	if level > 0.0:
		AudioServer.set_bus_volume_db(bus, level_db(level))


## The bus's gain for a slider at `level`: the amplitude is the travel squared,
## since loudness is heard by ratio and a slider straight on the amplitude does
## all its work in its bottom fifth. Half way is -12 dB.
static func level_db(level: float) -> float:
	return linear_to_db(level * level)


## The touch steering's response as saved (`Q223`), or "" where none was:
## `ControlOptions.steering` reads this after its flag and names the default.
static func steering() -> String:
	return str(_read().get_value(SECTION, KEY_STEERING, ""))


static func set_steering(choice: String) -> void:
	_write(KEY_STEERING, choice)


## Where the thumbs' controls stand as saved (`Q239`), or "" where none was:
## `ControlOptions.anchor` reads this after its flag and names the default.
static func anchor() -> String:
	return str(_read().get_value(SECTION, KEY_ANCHOR, ""))


static func set_anchor(choice: String) -> void:
	_write(KEY_ANCHOR, choice)


## Whether the steering thumb is the right one, the pedals under the left
## (`Q223`); `ControlOptions.steer_on_right` reads this after its flag.
static func steer_on_right() -> bool:
	return bool(_read().get_value(SECTION, KEY_STEER_ON_RIGHT, false))


static func set_steer_on_right(on: bool) -> void:
	_write(KEY_STEER_ON_RIGHT, on)


## A phone's frame cap (`Q223`): one of `offered` — what this screen can show,
## `ControlOptions.frame_caps` — or `FRAME_CAPS`' first where none was saved or
## the file names another: a 120 saved on one screen reads 60 on a slower one.
static func frame_cap(offered: PackedInt32Array = FRAME_CAPS) -> int:
	var saved: int = int(_read().get_value(SECTION, KEY_FRAME_CAP, FRAME_CAPS[0]))
	return saved if saved in offered else FRAME_CAPS[0]


static func set_frame_cap(fps: int) -> void:
	_write(KEY_FRAME_CAP, fps)


## The best shift's total in HK$ (`Q162`), 0 before the first.
static func best_shift_hkd() -> float:
	return float(_read().get_value(RECORDS, KEY_SHIFT_BEST, 0.0))


## Weigh a shift's total against the best and keep the larger: true, and
## written, when `hkd` beats it. A tie is not a new best.
static func record_shift(hkd: float) -> bool:
	if hkd <= best_shift_hkd():
		return false
	_write(KEY_SHIFT_BEST, hkd, RECORDS)
	return true


## The driver's lifetime books (`P3-76`, `Q169`), the 成績表's shape. Empty before
## the first run.
static func lifetime() -> SessionTally:
	var file: ConfigFile = _read()
	var tally := SessionTally.new()
	for skill: int in Fare.Skill.values():
		var key: String = ExamSheet.key_of(skill as Fare.Skill)
		tally.counts[skill] = int(file.get_value(RECORDS, key + COUNT_SUFFIX, 0))
		tally.banked[skill] = float(file.get_value(RECORDS, key + HKD_SUFFIX, 0.0))
		tally.combo_best[skill] = int(file.get_value(RECORDS, key + COMBO_SUFFIX, 0))
	for field: String in SessionTally.SUMS + SessionTally.BESTS:
		tally.set(field, file.get_value(RECORDS, field, tally.get(field)))
	return tally


## Shifts run to 交更 (`END SHIFT` is not one: half a shift is not a total).
static func shifts_finished() -> int:
	return int(_read().get_value(RECORDS, KEY_SHIFTS, 0))


## Add what `tally` has done since it was last banked to the lifetime books, one
## write for the lot. Nothing new and no finished shift writes nothing, so a
## pause on a parked car touches no file.
static func bank_tally(tally: SessionTally, shift_finished: bool) -> void:
	var delta: SessionTally = tally.take_unsaved()
	if delta.is_empty() and not shift_finished:
		return
	var sum: SessionTally = lifetime()
	sum.add(delta)
	var file: ConfigFile = _read()
	for skill: int in Fare.Skill.values():
		var key: String = ExamSheet.key_of(skill as Fare.Skill)
		file.set_value(RECORDS, key + COUNT_SUFFIX, sum.counts[skill])
		file.set_value(RECORDS, key + HKD_SUFFIX, sum.banked[skill])
		file.set_value(RECORDS, key + COMBO_SUFFIX, sum.combo_best[skill])
	for field: String in SessionTally.SUMS + SessionTally.BESTS:
		# An untried best is left off the file: a ConfigFile's INF is not worth
		# trusting across a platform, and absent reads as untried.
		if not is_inf(float(sum.get(field))):
			file.set_value(RECORDS, field, sum.get(field))
	if shift_finished:
		file.set_value(RECORDS, KEY_SHIFTS, shifts_finished() + 1)
	_save(file)


## Point every read and write at `path` and forget what was read, as a restart
## would. For `verify_menu`'s round trip; the game never calls it.
static func use_file(path: String) -> void:
	_path = path
	_file = null


static func _write(key: String, value: Variant, section: String = SECTION) -> void:
	var file: ConfigFile = _read()
	file.set_value(section, key, value)
	_save(file)


static func _save(file: ConfigFile) -> void:
	var error: Error = file.save(_path)
	if error != OK:
		push_warning("settings: could not write %s (%s)" % [_path, error_string(error)])


static func _read() -> ConfigFile:
	if _file == null:
		_file = ConfigFile.new()
		# A missing file is the first run, not a fault; anything else is said.
		var error: Error = _file.load(_path)
		if error != OK and error != ERR_FILE_NOT_FOUND:
			push_warning(
				(
					"settings: %s did not load (%s); starting from defaults"
					% [_path, error_string(error)]
				)
			)
	return _file
