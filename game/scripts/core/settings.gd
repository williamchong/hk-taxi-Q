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


## Point every read and write at `path` and forget what was read, as a restart
## would. For `verify_menu`'s round trip; the game never calls it.
static func use_file(path: String) -> void:
	_path = path
	_file = null


static func _write(key: String, value: Variant, section: String = SECTION) -> void:
	var file: ConfigFile = _read()
	file.set_value(section, key, value)
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
