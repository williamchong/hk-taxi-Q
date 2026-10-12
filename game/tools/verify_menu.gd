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
const MenuShotScript = preload("res://scripts/camera/menu_shot.gd")
const MenuTextScript = preload("res://scripts/ui/menu_text.gd")
const GuideCardScript = preload("res://scripts/ui/guide_card.gd")
const EngineNoticesScript = preload("res://scripts/ui/engine_notices.gd")
const SettingsScript = preload("res://scripts/core/settings.gd")
const StartMenuScript = preload("res://scripts/ui/start_menu.gd")

## The file the settings round trip writes, never the player's own.
const SETTINGS_PATH: String = "user://verify_menu_settings.cfg"

## Every string the menu asks for, so a row missing from the table is a
## failure here and not a bracketed key on screen.
const KEYS: PackedStringArray = [
	"subtitle",
	"start",
	"shift",
	"free",
	"best",
	"handover",
	"report_fares",
	"new_best",
	"again",
	"menu",
	"paused",
	"resume",
	"end_shift",
	"guide",
	"options",
	"credits",
	"back",
	"language",
	"language_zh",
	"language_en",
	"time",
	"time_cycle",
	"time_day",
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

## The profile's keys that draw something and therefore may not be zero.
const POSITIVE: PackedStringArray = [
	"shot_response",
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
## A camera shot per page (`MenuShot`), and its keys that may not be zero. The
## yaw is left out: 0 is behind the car, a value.
const SHOTS: PackedStringArray = [
	"shot_home", "shot_play", "shot_options", "shot_sheet", "shot_report"
]
const SHOT_POSITIVE: PackedStringArray = ["distance_m", "height_m", "fov_deg"]


func _init() -> void:
	_check_profile()
	_check_text()
	_check_notices()
	_check_settings()
	# The pause needs a tree, and autoloads register on the first frame.
	_check_pause.call_deferred()
	_start_watchdog.call_deferred("verify_menu", 30.0)


## The menu over a paused drive (`Q165`): it runs alone over the paused tree,
## its END names the run, HOW TO PLAY leads back to it and not HOME, and the
## key that paused resumes — once, the menu leaving.
func _check_pause() -> void:
	await process_frame
	var menu := StartMenuScript.new()
	menu.pausing = true
	menu.pausing_shift = true
	var resumes: Array[int] = [0]
	menu.resumed.connect(func() -> void: resumes[0] += 1)
	paused = true
	root.add_child(menu)
	await process_frame
	var pages: Dictionary = menu._pages
	var page: Control = pages.get(StartMenuScript.Page.PAUSE)
	_expect(
		menu.process_mode == Node.PROCESS_MODE_ALWAYS and page != null and page.visible,
		"pause",
		"the pause opens on its page and runs over the paused tree"
	)
	if page == null:
		paused = false
		_finish("verify_menu")
		return
	var text := MenuTextScript.load_text()
	var end: Button = page.get_node("End/Button")
	_expect(
		end.text in [text.say("end_shift", "en"), text.say("end_shift", "zh")],
		"pause",
		"a shift's way out is END SHIFT"
	)
	(page.get_node("Guide/Button") as Button).pressed.emit()
	var guide: Control = pages.get(StartMenuScript.Page.GUIDE)
	(guide.get_node("Centre/Pad/Column/Foot/Back/Button") as Button).pressed.emit()
	_expect(page.visible and not guide.visible, "pause", "HOW TO PLAY's way back is the pause")
	var cancel := InputEventAction.new()
	cancel.action = &"ui_cancel"
	cancel.pressed = true
	menu._unhandled_input(cancel)
	_expect(
		resumes[0] == 1 and menu.is_queued_for_deletion(),
		"pause",
		"the key that paused resumes, and the menu leaves"
	)
	paused = false
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
	for key: String in SHOTS:
		_check_shot(key, profile.get(key) as Resource)


func _check_shot(key: String, shot: Resource) -> void:
	if shot == null or shot.get_script() != MenuShotScript:
		_fail("profile", "%s is not a MenuShot" % key)
		return
	for field: String in SHOT_POSITIVE:
		var value: float = shot.get(field)
		_expect(value > 0.0, "profile", "%s.%s is %s (> 0)" % [key, field, value])
	# The pitch looks down on the car — a positive would look at the sky.
	var pitch: float = shot.get("pitch_deg")
	_expect(pitch < 0.0, "profile", "%s.pitch_deg is %s (< 0)" % [key, pitch])
	# Never a still frame: a still menu stalls a capture on "no frame drawn".
	var turn: float = shot.get("turn_period_s")
	var sway: float = shot.get("sway_deg")
	var sway_period: float = shot.get("sway_period_s")
	_expect(
		turn > 0.0 or (sway > 0.0 and sway_period > 0.0),
		"profile",
		"%s turns or sways (turn %s s, sway %s deg / %s s)" % [key, turn, sway, sway_period]
	)


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


## No language is saved on a first run, and a choice survives a restart: each
## read after `use_file`, which forgets the cached file as a new run would.
func _check_settings() -> void:
	_forget_settings_file()
	SettingsScript.use_file(SETTINGS_PATH)
	_expect(SettingsScript.language() == "", "settings", "no language with nothing saved")
	for code: String in ["en", "zh"]:
		SettingsScript.set_language(code)
		# The disk read first, apart from `Settings`: a cache kept across
		# `use_file` would answer the restart below from memory.
		var disk := ConfigFile.new()
		_expect(
			(
				disk.load(SETTINGS_PATH) == OK
				and disk.get_value(SettingsScript.SECTION, SettingsScript.KEY_LANGUAGE) == code
			),
			"settings",
			"the language saved %s is on disk" % code
		)
		SettingsScript.use_file(SETTINGS_PATH)
		_expect(
			SettingsScript.language() == code,
			"settings",
			"the language saved %s reads %s after a restart" % [code, code]
		)

	# Free mode keeps the daylight until the option says otherwise (`Q162`).
	_expect(not SettingsScript.day_cycle(), "settings", "free mode's day cycle is off unsaved")
	# 特更's best: only a higher total is a record, and it survives a restart.
	_expect(SettingsScript.best_shift_hkd() == 0.0, "records", "no best with nothing saved")
	_expect(SettingsScript.record_shift(120.5), "records", "a first shift is a record")
	_expect(not SettingsScript.record_shift(120.5), "records", "a tie is not a record")
	_expect(not SettingsScript.record_shift(80.0), "records", "a lower total is not a record")
	SettingsScript.use_file(SETTINGS_PATH)
	_expect(
		SettingsScript.best_shift_hkd() == 120.5 and SettingsScript.language() == "zh",
		"records",
		"the best reads HK$120.5 after a restart, beside the options"
	)
	_expect(SettingsScript.record_shift(200.0), "records", "a higher total is a record")
	_forget_settings_file()
	SettingsScript.use_file(SettingsScript.PATH)


## A missing file is the state wanted, so the error is not read.
func _forget_settings_file() -> void:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_PATH))
