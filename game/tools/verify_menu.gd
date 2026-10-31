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
const SessionTallyScript = preload("res://scripts/fares/session_tally.gd")
const ExamSheetScript = preload("res://scripts/fares/exam_sheet.gd")
const FareScript = preload("res://scripts/fares/fare.gd")
const StreetPlateScript = preload("res://scripts/ui/street_plate.gd")

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
	"record",
	"record_runs",
	"sheet_title",
	"sheet_bonus",
	"sheet_penalty",
	"sheet_count",
	"sheet_subtotal",
	"sheet_meter",
	"sheet_time",
	"sheet_floored",
	"sheet_total",
	"sheet_walked",
	"sheet_best_slide",
	"sheet_best_flight",
	"sheet_best_pass",
	"sheet_best_speed",
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
		"Leisure and Cultural Services Department",
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
		"康樂及文化事務署",
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
	"ledger_row_px",
	"ledger_rule_px",
	"ledger_count_px",
	"ledger_money_px",
	"ledger_gutter_px",
	"ledger_gap_px",
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
	"margin_px", "button_px", "credits_px", "guide_px", "guide_picture_px", "ledger_px"
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
	_check_record()
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
	await _check_sheet()
	_finish("verify_menu")


## The 成績表 (`P3-76`): two tables, every row reading the tally's numbers, on
## REPORT, a free drive's PAUSE and RECORD, and none on a shift's PAUSE; every
## word on it in the Kai.
func _check_sheet() -> void:
	var tally: SessionTallyScript = SessionTallyScript.sample()
	var text := MenuTextScript.load_text()

	var report := StartMenuScript.new()
	report.report = StartMenuScript.Report.new()
	report.report.tally = tally
	root.add_child(report)
	await process_frame
	var page: Control = report._pages.get(StartMenuScript.Page.REPORT)
	var ledger: Node = report._root.get_node_or_null("Ledger")
	if ledger == null or page == null or not page.visible:
		_fail("sheet", "REPORT has no ledger beside its column")
		report.queue_free()
		return
	var card: Node = ledger.get_node("Pad/Column/Card")
	for skill: int in SessionTallyScript.BONUSES:
		var row: Node = card.get_node("Tables/Bonus/%s" % ExamSheetScript.key_of(skill))
		_expect(
			(row.get_node("Count") as Label).text == str(tally.counts[skill]),
			"sheet",
			"%s's count reads the tally" % ExamSheetScript.key_of(skill)
		)
		_expect(
			(row.get_node("Money") as Label).text == "+" + "%.1f" % tally.banked[skill],
			"sheet",
			"%s's money reads the tally, signed" % ExamSheetScript.key_of(skill)
		)
	for skill: int in SessionTallyScript.PENALTIES:
		var row: Node = card.get_node("Tables/Penalty/%s" % ExamSheetScript.key_of(skill))
		_expect(
			(row.get_node("Money") as Label).text == "−" + "%.1f" % -tally.banked[skill],
			"sheet",
			"%s docks with a proper minus" % ExamSheetScript.key_of(skill)
		)
	_expect(
		(card.get_node("Books/Sums/Total/Value") as Label).text == "%.1f" % tally.total_hkd(),
		"sheet",
		"the total is the books' sum"
	)
	_expect(
		card.get_node_or_null("Books/Sums/Floored") != null, "sheet", "a floored tip has its line"
	)
	_expect(
		(card.get_node("Books/Bests/Pass/Value") as Label).text == "0.18 m",
		"sheet",
		"the closest pass reads in metres"
	)
	report._show(StartMenuScript.Page.HOME)
	await process_frame
	_expect(not (ledger as CanvasItem).visible, "sheet", "the ledger leaves with its page")
	report._show(StartMenuScript.Page.REPORT)
	await process_frame
	_expect((ledger as CanvasItem).visible, "sheet", "and comes back with it")
	report.queue_free()

	var fresh := StartMenuScript.new()
	fresh.report = StartMenuScript.Report.new()
	root.add_child(fresh)
	await process_frame
	var empty: Node = fresh._root.get_node("Ledger/Pad/Column/Card")
	_expect(
		(
			(empty.get_node("Books/Bests/Slide/Value") as Label).text == "—"
			and empty.get_node_or_null("Books/Sums/Floored") == null
			and empty.get_node_or_null("Books/Sums/Walked") == null
		),
		"sheet",
		"an empty run has no best, no floor line and no loss line"
	)
	_expect(fresh._pages.has(StartMenuScript.Page.RECORD), "sheet", "RECORD is a page off HOME")
	fresh.queue_free()

	for pausing_free: bool in [true, false]:
		var over := StartMenuScript.new()
		over.pausing = true
		over.pausing_shift = not pausing_free
		if pausing_free:
			over.pause_tally = tally
		root.add_child(over)
		await process_frame
		_expect(
			(over._root.get_node_or_null("Ledger") != null) == pausing_free,
			"sheet",
			"a free drive's PAUSE has the sheet; a shift's has not"
		)
		over.queue_free()

	var kai: Font = load(str(StreetPlateScript.load_tuning().get("font_zh", ""))) as Font
	_expect(kai != null, "sheet", "the Kai loads")
	if kai == null:
		return
	for key: String in KEYS:
		if not key.begins_with("sheet_") and not key.begins_with("record"):
			continue
		var said: String = text.say(key, "zh")
		for index: int in said.length():
			if said.unicode_at(index) > 0x2FFF and not kai.has_char(said.unicode_at(index)):
				_fail("sheet", "the Kai has no '%s' for %s" % [said[index], key])


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


## The lifetime record (`P3-76`, `Q169`): saved, restarted and summed; a run saved
## at every pause counts each event once; an older file keeps its best and starts
## its books at nothing; a count is keyed by the skill's name, not its value.
func _check_record() -> void:
	var probe: SessionTallyScript = SessionTallyScript.new()
	for field: String in SessionTallyScript.SUMS + SessionTallyScript.BESTS:
		_expect(probe.get(field) != null, "record", "%s is a field of the tally" % field)
	_forget_settings_file()
	SettingsScript.use_file(SETTINGS_PATH)
	# A file from before the record: the best and nothing else.
	SettingsScript.record_shift(99.0)
	var old: SessionTallyScript = SettingsScript.lifetime()
	_expect(
		old.is_empty() and is_zero_approx(old.total_hkd()),
		"record",
		"an older file reads as empty books"
	)

	var run: SessionTallyScript = SessionTallyScript.new()
	SettingsScript.bank_tally(run, false)
	var disk := ConfigFile.new()
	disk.load(SETTINGS_PATH)
	_expect(
		not disk.has_section_key(SettingsScript.RECORDS, "drift_count"),
		"record",
		"an empty run writes nothing"
	)

	run.counts[FareScript.Skill.DRIFT] = 3
	run.banked[FareScript.Skill.DRIFT] = 6.0
	run.counts[FareScript.Skill.CRASH] = 1
	run.banked[FareScript.Skill.CRASH] = -5.0
	run.meter_hkd = 40.0
	run.deliveries = 1
	run.longest_slide_s = 2.0
	run.closest_pass_m = 0.5
	SettingsScript.bank_tally(run, false)
	SettingsScript.bank_tally(run, false)
	SettingsScript.use_file(SETTINGS_PATH)
	var saved: SessionTallyScript = SettingsScript.lifetime()
	_expect(
		(
			saved.counts[FareScript.Skill.DRIFT] == 3
			and is_equal_approx(saved.banked[FareScript.Skill.CRASH], -5.0)
			and is_equal_approx(saved.meter_hkd, 40.0)
			and saved.deliveries == 1
		),
		"record",
		"mutation caught: saved twice with nothing new, a restart reads each event once"
	)
	_expect(
		is_equal_approx(saved.closest_pass_m, 0.5) and is_equal_approx(saved.longest_slide_s, 2.0),
		"record",
		"the bests survive a restart"
	)

	run.counts[FareScript.Skill.DRIFT] = 5
	run.meter_hkd = 70.0
	run.longest_slide_s = 1.0
	SettingsScript.bank_tally(run, true)
	SettingsScript.use_file(SETTINGS_PATH)
	saved = SettingsScript.lifetime()
	_expect(
		saved.counts[FareScript.Skill.DRIFT] == 5 and is_equal_approx(saved.meter_hkd, 70.0),
		"record",
		"a later save adds only what is new"
	)
	_expect(is_equal_approx(saved.longest_slide_s, 2.0), "record", "a shorter slide keeps the best")
	_expect(SettingsScript.shifts_finished() == 1, "record", "交更 counts a shift")

	# A second run on the same books adds, and a tighter pass is the new best.
	var next: SessionTallyScript = SessionTallyScript.new()
	next.counts[FareScript.Skill.DRIFT] = 2
	next.closest_pass_m = 0.2
	SettingsScript.bank_tally(next, false)
	saved = SettingsScript.lifetime()
	_expect(
		(
			saved.counts[FareScript.Skill.DRIFT] == 7
			and is_equal_approx(saved.closest_pass_m, 0.2)
			and SettingsScript.shifts_finished() == 1
		),
		"record",
		"a new run adds to the lifetime, its pass the tighter, and END SHIFT is no shift"
	)
	_expect(
		is_equal_approx(SettingsScript.best_shift_hkd(), 99.0), "record", "the shift's best is kept"
	)
	disk = ConfigFile.new()
	disk.load(SETTINGS_PATH)
	_expect(
		disk.get_value(SettingsScript.RECORDS, "drift_count", -1) == 7,
		"record",
		"the file keys a count by the skill's name"
	)
	_forget_settings_file()
	SettingsScript.use_file(SettingsScript.PATH)


## A missing file is the state wanted, so the error is not read.
func _forget_settings_file() -> void:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_PATH))
