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
