class_name MenuText
extends RefCounted
## The start menu's strings and the credits, in both languages (`P6-1`), read
## from `tuning/menu_text.json`.
##
## JSON rather than a `.tres`, which hard rule 4 permits: the credits are the
## attribution hard rule 6 and `LICENSING.md` require, and a legal text wants
## to be diffable prose in a file anyone can read, not a resource the editor
## rewrites. `verify_menu.gd` holds its wording — the ownership sentence, both
## portals, the typeface — so the screen cannot drift off the terms it exists
## to discharge.

const PATH: String = "res://tuning/menu_text.json"

## `key` → `{ "en": ..., "zh": ... }`.
var strings: Dictionary = {}
## Each `{ "heading": { en, zh }, "body": { en, zh } }`, in reading order.
var credits: Array = []
## Each `{ "picture": <GuideCard kind>, "heading": { en, zh }, "body": { en, zh } }`.
var guide: Array = []
var loaded: bool = false


static func load_text() -> MenuText:
	var text := MenuText.new()
	var file := FileAccess.open(PATH, FileAccess.READ)
	if file == null:
		push_warning("menu: %s did not open" % PATH)
		return text
	var document: Variant = JSON.parse_string(file.get_as_text())
	if not document is Dictionary:
		push_warning("menu: %s is not a JSON object" % PATH)
		return text
	var table: Dictionary = document
	if table.get("strings") is Dictionary:
		text.strings = table["strings"]
	if table.get("credits") is Array:
		text.credits = table["credits"]
	if table.get("guide") is Array:
		text.guide = table["guide"]
	text.loaded = true
	return text


## The string under `key` in `language`, or the key in brackets so a missing
## row is seen on screen rather than read as an empty button.
func say(key: String, language: String) -> String:
	return MenuText.pick(strings.get(key), language, "[%s]" % key)


## `row[language]` where `row` is a `{ en, zh }` table with that string, else
## `fallback`.
static func pick(row: Variant, language: String, fallback: String) -> String:
	if row is Dictionary:
		var value: Variant = (row as Dictionary).get(language)
		if value is String and not (value as String).is_empty():
			return value
	return fallback
