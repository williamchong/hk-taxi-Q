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

static var _file: ConfigFile = null


## The saved language code, or "" where none was ever saved.
static func language() -> String:
	return str(_read().get_value(SECTION, KEY_LANGUAGE, ""))


## Save `code`. Written at once: the file IS the option, and a write deferred
## to quit is one a crash loses.
static func set_language(code: String) -> void:
	var file: ConfigFile = _read()
	file.set_value(SECTION, KEY_LANGUAGE, code)
	var error: Error = file.save(PATH)
	if error != OK:
		push_warning("settings: could not write %s (%s)" % [PATH, error_string(error)])


static func _read() -> ConfigFile:
	if _file == null:
		_file = ConfigFile.new()
		# A missing file is the first run, not a fault; anything else is said.
		var error: Error = _file.load(PATH)
		if error != OK and error != ERR_FILE_NOT_FOUND:
			push_warning(
				(
					"settings: %s did not load (%s); starting from defaults"
					% [PATH, error_string(error)]
				)
			)
	return _file
