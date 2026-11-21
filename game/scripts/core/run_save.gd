class_name RunSave
extends RefCounted
## The run in play, saved so CONTINUE can pick it up after the app was killed
## or the run was left from its PAUSE (`Q253`, the user's ask). One slot: a
## new PLAY replaces it and a shift run to 交更 removes it.
##
## **Its own file, beside `Settings`' and never inside it.** The options and
## the lifetime record are the player's for good; this is one run's, and a new
## run or a finished shift is the file's removal, not a section's surgery.
##
## **What is saved is the run, not the city**: the mode, the clock's seconds,
## where the car stood, and the fare loop's books with the passenger aboard
## (`FareSystem.snapshot`). The traffic, the trams and the waiting customers
## are drawn afresh, as at every start.
##
## ⚠️ **Written only for a player's run** — `Main._save_run` refuses a scripted
## one on `_bank_tally`'s gate — so `drive.sh` never reads a save into a frame
## nor leaves one behind.

const PATH: String = "user://run.cfg"
## Bumped where an older save would be read WRONG, never merely where a field
## is added: `from_dict`-style reads default what they do not find.
const FORMAT: int = 1
const SECTION: String = "run"
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

## The file read and written: `PATH`, except under `verify_menu`, which round
## trips its own so a check never touches the player's run.
static var _path: String = PATH

var mode: DayClock.Mode = DayClock.Mode.FREE
## Game seconds the run's clock had counted (`DayClock.elapsed_s`).
var elapsed_s: float = 0.0
## The game second a free drive's day counts from (`DayClock.day_from_s`);
## 0 in a shift, and in a save from before it was kept.
var day_from_s: float = 0.0
## The shift's clock as it stood, for CONTINUE's caption; NAN in free mode.
var hour_h: float = NAN
## The car's transform where it stood.
var pose: Transform3D = Transform3D.IDENTITY
## `FareSystem.snapshot`'s dictionary.
var books: Dictionary = {}
## The resident regions the run was driven over, in the frame the pose is in.
var regions: PackedStringArray = []


## The HK$ the run had banked, off its books.
func earned_hkd() -> float:
	return float(books.get("earned_hkd", 0.0))


## Game seconds driven, the menu and the pause not counted (`SessionTally`).
func driven_s() -> float:
	var tally: Variant = books.get("tally", {})
	return float((tally as Dictionary).get("driven_s", 0.0)) if tally is Dictionary else 0.0


## Whether a passenger is aboard in the save.
func carrying() -> bool:
	return books.has("fare")


## Write this run as the one saved, at once: the file IS the save, and one
## deferred is one a kill loses. True on success.
func write() -> bool:
	var file := ConfigFile.new()
	file.set_value(SECTION, "format", FORMAT)
	file.set_value(SECTION, "regions", regions)
	file.set_value(SECTION, "mode", mode)
	file.set_value(SECTION, "elapsed_s", elapsed_s)
	file.set_value(SECTION, "day_from_s", day_from_s)
	if not is_nan(hour_h):
		file.set_value(SECTION, "hour_h", hour_h)
	file.set_value(SECTION, "pose", pose)
	file.set_value(SECTION, "books", books)
	var error: Error = file.save(_path)
	if error != OK:
		push_warning("run save: could not write %s (%s)" % [_path, error_string(error)])
	return error == OK


## The saved run over `resident`, or null where there is none or it is not
## one this build can resume — another format, or other regions, which would
## put the car somewhere else in the frame. A save refused is removed and
## the reason said.
static func load_saved(resident: PackedStringArray = GeneratedRegions.resident()) -> RunSave:
	if not exists():
		return null
	var file := ConfigFile.new()
	var error: Error = file.load(_path)
	var refused: String = ""
	if error != OK:
		refused = "did not load (%s)" % error_string(error)
	elif int(file.get_value(SECTION, "format", 0)) != FORMAT:
		refused = "is format %s, not %d" % [file.get_value(SECTION, "format", "none"), FORMAT]
	elif not _same_regions(file.get_value(SECTION, "regions", []), resident):
		refused = "was driven over %s, not %s" % [file.get_value(SECTION, "regions", []), resident]
	if not refused.is_empty():
		push_warning("run save: %s %s; starting fresh" % [_path, refused])
		clear()
		return null
	var run := RunSave.new()
	run.mode = (
		DayClock.Mode.SHIFT
		if int(file.get_value(SECTION, "mode", DayClock.Mode.FREE)) == DayClock.Mode.SHIFT
		else DayClock.Mode.FREE
	)
	run.elapsed_s = float(file.get_value(SECTION, "elapsed_s", 0.0))
	run.day_from_s = float(file.get_value(SECTION, "day_from_s", 0.0))
	run.hour_h = float(file.get_value(SECTION, "hour_h", NAN))
	var saved_pose: Variant = file.get_value(SECTION, "pose", Transform3D.IDENTITY)
	run.pose = saved_pose if saved_pose is Transform3D else Transform3D.IDENTITY
	var saved_books: Variant = file.get_value(SECTION, "books", {})
	run.books = saved_books if saved_books is Dictionary else {}
	run.regions = resident
	return run


## Whether `saved` names `resident`, whatever a hand-edited file put there.
static func _same_regions(saved: Variant, resident: PackedStringArray) -> bool:
	if not (saved is Array or saved is PackedStringArray):
		return false
	return PackedStringArray(saved) == resident


static func exists() -> bool:
	return FileAccess.file_exists(_path)


## No run saved: a new PLAY, or a shift run to 交更. Nothing to remove is not
## a fault.
static func clear() -> void:
	if exists():
		DirAccess.remove_absolute(ProjectSettings.globalize_path(_path))


## A saved run for a frame (`--menu-sample=on`): a shift part-way, a fare
## aboard, the longest caption. Never a player's, and never written.
static func sample() -> RunSave:
	var run := RunSave.new()
	run.mode = DayClock.Mode.SHIFT
	run.hour_h = 15.7
	run.books = {"earned_hkd": 1234.5, "tally": {"driven_s": 1834.0}, "fare": {}}
	return run


## Point every read and write at `path`. For `verify_menu`'s round trip; the
## game never calls it.
static func use_file(path: String) -> void:
	_path = path
