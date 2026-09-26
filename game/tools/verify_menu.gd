extends "res://tools/verify_tool.gd"

## The start menu's two contracts (`P6-1`): its tables load whole, and the
## credits say what the licences require them to say.
##
## ⚠️ **Runs without a built region**, like `verify_hud.gd`: both tables are
## committed tuning, so CI checks them on every push — and a wording edit to a
## licence text is exactly the change that lands on a branch with no city.
##
## **Why the wording is asserted and not read.** Hard rule 6 says attribution
## is stronger than naming a source: the screen must acknowledge the
## Government's and the relevant organisations' OWNERSHIP of the intellectual
## property rights and name BOTH portals, and `LICENSING.md` adds the typeface's
## CC BY credit that must travel with every distributed copy. A credits screen
## that drifted off one of those phrases would still render perfectly, so the
## phrases are the check — in both languages, because the menu shows one.
##
## ⚠️ **Nothing here references a `class_name` global.** A `--script` tool that
## does fails to parse on a fresh clone, where the class cache has not been
## written, and the SceneTree then exits **0** having checked nothing.
## `ARCHITECTURE.md` records the trap; everything is `preload`ed by path.
##
## 🔴 This tool can print `ok` having checked nothing if a preloaded script
## fails to compile — `verify_hud.gd` explains — which is why only
## `check.sh`'s exit code means anything.

const MenuProfileScript = preload("res://scripts/ui/menu_profile.gd")
const MenuTextScript = preload("res://scripts/ui/menu_text.gd")
const GuideCardScript = preload("res://scripts/ui/guide_card.gd")
const EngineNoticesScript = preload("res://scripts/ui/engine_notices.gd")

## Every string the menu asks for, so a row missing from the table is a
## failure here and not a bracketed key on screen.
const KEYS: PackedStringArray = [
	"subtitle",
	"start",
	"guide",
	"options",
	"credits",
	"back",
	"language",
	"language_zh",
	"language_en",
	"notices",
	"notices_title",
	"notices_lead",
]
const LANGUAGES: PackedStringArray = ["en", "zh"]

## The phrases the credits must carry, per language. The English is
## `DATA_SOURCES.md`'s drafted text; the Chinese is its rendering.
const REQUIRED: Dictionary = {
	"en":
	[
		"Government of the Hong Kong Special Administrative Region",
		"DATA.GOV.HK",
		"Common Spatial Data Infrastructure (CSDI) Portal",
		"own the intellectual property rights",
		"does not endorse",
		"Free HK Kai",
		"Creative Commons Attribution 4.0",
		"Godot Engine",
	],
	"zh":
	[
		"香港特別行政區政府",
		"資料一線通",
		"空間數據共享平台",
		"擁有該等數據的知識產權",
		"並不認可",
		"自由香港楷書",
		"署名 4.0 國際",
		"Godot Engine",
	],
}

## The profile's keys that draw something and therefore may not be zero. The
## orbit's start angle and its pitch are left out: 0 and a negative are both
## values there.
const POSITIVE: PackedStringArray = [
	"orbit_distance_m",
	"orbit_height_m",
	"orbit_period_s",
	"orbit_fov_deg",
	"button_gap_px",
	"credits_pad_px",
	"title_size",
	"subtitle_size",
	"subtitle_size_zh",
	"button_size",
	"button_size_zh",
	"heading_size",
	"heading_size_zh",
	"body_size",
	"body_size_zh",
]
const POSITIVE_VECTORS: PackedStringArray = [
	"margin_px", "button_px", "credits_px", "guide_px", "guide_picture_px"
]


func _init() -> void:
	_check_profile()
	_check_text()
	_check_notices()

	_finish("verify_menu")


func _check_profile() -> void:
	var profile: Resource = load(MenuProfileScript.PATH)
	if profile == null or profile.get_script() != MenuProfileScript:
		_fail("profile", "%s did not load as a MenuProfile" % MenuProfileScript.PATH)
		return
	for key: String in POSITIVE:
		var value: Variant = profile.get(key)
		_expect(
			(value is float or value is int) and float(value) > 0.0,
			"profile",
			"%s is %s (> 0)" % [key, value]
		)
	for key: String in POSITIVE_VECTORS:
		var value: Variant = profile.get(key)
		_expect(
			value is Vector2 and (value as Vector2).x > 0.0 and (value as Vector2).y > 0.0,
			"profile",
			"%s is %s (both > 0)" % [key, value]
		)
	# The pitch looks down on the car — a positive would look at the sky.
	var pitch: Variant = profile.get("orbit_pitch_deg")
	_expect(pitch is float and float(pitch) < 0.0, "profile", "orbit_pitch_deg is %s (< 0)" % pitch)


func _check_text() -> void:
	var text: RefCounted = MenuTextScript.load_text()
	if not text.loaded:
		_fail("text", "%s did not load" % MenuTextScript.PATH)
		return
	for key: String in KEYS:
		for language: String in LANGUAGES:
			var said: String = text.say(key, language)
			_expect(not said.begins_with("["), "text", "%s/%s reads %s" % [key, language, said])

	var credits: Array = text.credits
	_expect(
		credits.size() >= 4, "credits", "%d entries (data, typeface, engine, code)" % credits.size()
	)
	for language: String in LANGUAGES:
		var whole: String = ""
		for index: int in credits.size():
			var entry: Variant = credits[index]
			if not entry is Dictionary:
				_fail("credits", "entry %d is not an object" % index)
				continue
			var heading: String = MenuTextScript.pick(
				(entry as Dictionary).get("heading"), language, ""
			)
			var body: String = MenuTextScript.pick((entry as Dictionary).get("body"), language, "")
			_expect(
				not heading.is_empty(), "credits", "entry %d has a %s heading" % [index, language]
			)
			_expect(not body.is_empty(), "credits", "entry %d has a %s body" % [index, language])
			whole += heading + "\n" + body + "\n"
		for phrase: String in REQUIRED[language]:
			_expect(whole.contains(phrase), "credits", '%s says "%s"' % [language, phrase])

	# The guide: every step captioned in both languages and drawn by a
	# picture that exists.
	var guide: Array = text.guide
	_expect(guide.size() >= 4, "guide", "%d steps" % guide.size())
	for index: int in guide.size():
		var entry: Variant = guide[index]
		if not entry is Dictionary:
			_fail("guide", "step %d is not an object" % index)
			continue
		var picture: String = str((entry as Dictionary).get("picture", ""))
		_expect(
			GuideCardScript.KINDS.has(picture),
			"guide",
			'step %d draws "%s" (one of %s)' % [index, picture, GuideCardScript.KINDS]
		)
		for language: String in LANGUAGES:
			var heading: String = MenuTextScript.pick(
				(entry as Dictionary).get("heading"), language, ""
			)
			var body: String = MenuTextScript.pick((entry as Dictionary).get("body"), language, "")
			_expect(not heading.is_empty(), "guide", "step %d has a %s heading" % [index, language])
			_expect(not body.is_empty(), "guide", "step %d has a %s body" % [index, language])


## The engine's third-party notices (`LICENSING.md` item 5): the composed
## text names every component the engine's table lists and carries every
## licence's text whole, so a build ships its notices in full, not the MIT
## screen alone. Read from the running engine, so what is checked is what
## ships from this version.
func _check_notices() -> void:
	var text: String = EngineNoticesScript.compose()
	_expect(
		text.length() > Engine.get_license_text().length(), "notices", "more than the MIT screen"
	)
	var components: Array = Engine.get_copyright_info()
	_expect(
		components.size() >= 50,
		"notices",
		"%d components in the engine's table" % components.size()
	)
	var missing: PackedStringArray = []
	for component: Dictionary in components:
		var name: String = str(component.get("name", ""))
		if not text.contains(name):
			missing.append(name)
	_expect(
		missing.is_empty(), "notices", "every component named (missing %s)" % ", ".join(missing)
	)
	for required: String in ["Godot Engine", "Jolt Physics"]:
		_expect(text.contains(required), "notices", 'names "%s"' % required)
	var licences: Dictionary = Engine.get_license_info()
	_expect(licences.size() >= 10, "notices", "%d licences in the engine's table" % licences.size())
	var unquoted: PackedStringArray = []
	for id: String in licences:
		if not text.contains(str(licences[id]).strip_edges()):
			unquoted.append(id)
	_expect(
		unquoted.is_empty(),
		"notices",
		"every licence text whole (missing %s)" % ", ".join(unquoted)
	)
