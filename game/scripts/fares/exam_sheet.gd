class_name ExamSheet
extends RefCounted
## What each `Fare.Skill` is called (`P3-76`, `Q169`, the user's ask): the
## items of the driving test's fault sheet, the 黃紙, read from
## `tuning/exam_sheet.json` — 太接近其他物體 for a near miss, 碰及物體 for a
## crash. Names only: a bonus still pays and a penalty still docks, and TD's
## three-minors-make-a-serious rule is not applied (the user's call).
##
## **The tier is part of the name.** Two events share an item — a near miss
## and a close call are both 太接近其他物體 — and the sheet's own 輕微 / 嚴重
## is what tells them apart on the flash and the receipt, so `name` appends it.
##
## Read once and kept: `FareFace` asks on every award and every receipt line.

const PATH: String = "res://tuning/exam_sheet.json"

static var _loaded: ExamSheet = null

## `Fare.Skill` name, lower-cased → `{ en, zh, tier? }`.
var items: Dictionary = {}
## Tier key → `{ en, zh }`.
var tiers: Dictionary = {}


static func shared() -> ExamSheet:
	if _loaded == null:
		_loaded = ExamSheet.new()
		_loaded._read()
	return _loaded


func _read() -> void:
	var text: String = FileAccess.get_file_as_string(PATH)
	if text.is_empty():
		push_warning("exam sheet: %s did not open, or is empty" % PATH)
		return
	var document: Variant = JSON.parse_string(text)
	if not document is Dictionary:
		push_warning("exam sheet: %s is not a JSON object" % PATH)
		return
	var table: Dictionary = document
	if table.get("items") is Dictionary:
		items = table["items"]
	if table.get("tiers") is Dictionary:
		tiers = table["tiers"]


## The key `skill` is filed under: its enum name, lower-cased.
static func _key_of(skill: Fare.Skill) -> String:
	return str(Fare.Skill.find_key(skill)).to_lower()


## `skill`'s item in `language`, with its tier where it has one —
## "太接近其他物體（輕微）", "too close to other objects (minor)". A skill with
## no row reads as its key in brackets, so a missing name is seen on screen
## rather than flashed as nothing.
func item_name(skill: Fare.Skill, language: String) -> String:
	var key: String = _key_of(skill)
	var row: Variant = items.get(key)
	var item: String = Locale.from_row(row, language, "")
	if item.is_empty():
		return "[%s]" % key
	var tier_key: String = str((row as Dictionary).get("tier", ""))
	if tier_key.is_empty():
		return item
	var tier: String = Locale.from_row(tiers.get(tier_key), language, "[%s]" % tier_key)
	return str(Locale.pick("%s（%s）", "%s (%s)", language)) % [item, tier]
