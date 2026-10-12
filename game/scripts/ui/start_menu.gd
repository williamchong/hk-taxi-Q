class_name StartMenu
extends CanvasLayer
## The start menu (`P6-1`, the user's ask): the two modes, options, credits,
## drawn over the taxi standing on the start line with the camera placed by the page (`Q164`).
##
## **Two ways to play** (`Q162`): 特更 / THE SHIFT, morning to night with the
## total weighed against the best at 交更, and 兜風 / FREE MODE, the drive with
## no end — one PLAY on HOME, the two behind it on PLAY (the user's call), and
## the shift's best on HOME. `Main` opens a fresh one on the REPORT page when a shift ends; its
## AGAIN is a `started` like the first.
##
## Under `GUI` beside the HUD, and it never reaches into the level: `Main` parks
## the level while this is up and resumes it on `started`, the same way it hands
## the HUD its car. Everything drawn is the HUD's head-up glass — `HudStyle`'s
## colours, frame and bare lettering (`Q163`, one display) — and every number is
## `MenuProfile`'s. Every string is `MenuText`'s, in the one language `Locale`
## names, and the credits it shows are the attribution hard rule 6 and
## `LICENSING.md` require; `verify_menu.gd` holds their wording.
##
## ⚠️ **`--menu=off` boots straight into the drive**, and `drive.sh` passes it
## unless a run names the flag, so every scripted drive is what it was.
## `--menu-page=<home|play|guide|options|credits|notices|report>` opens on that
## page, so a frame of any sheet is one `drive.sh` run and never a click; the
## report so opened is an empty shift's.
##
## ⚠️ **The first Controls in this project that take a click.** `InputRouter`
## never marks an event handled, so the buttons see the pointer and the touch;
## while the menu is up the car is parked, so the thumbs the router still reads
## move nothing. `ui_cancel` is read here — a UI action, not a gameplay one —
## for the way back from a page.

## The player picked a mode. `Main` starts the level in it and frees this.
signal started(mode: DayClock.Mode)
## The player picked a language; `Locale.language()` already answers it.
signal language_changed(code: String)
## A page opened; `Main` hands `shot` to the camera round the parked car.
signal page_shown(shot: MenuShot)

## Chooses whether the menu is shown at all. `off` for every scripted run.
const MENU_ARG: String = "--menu="
## The page the menu opens on; absent or unknown, the home page.
const PAGE_ARG: String = "--menu-page="
## Over the HUD (10), under the dev overlay (127).
const LAYER: int = 20
## The blur behind the menu's text (`Q163`).
const BACKDROP: Shader = preload("res://assets/shaders/backdrop_blur.gdshader")
## Where `_sheet` puts a sheet's column, for the page that fills it.
const SHEET_COLUMN: NodePath = ^"Centre/Pad/Column"

## `PAGE_ARG` names one of these, lower-cased; `driver.gd` validates the same
## list by hand, since a `--script` tool cannot preload a `class_name` script.
enum Page { HOME, PLAY, OPTIONS, CREDITS, GUIDE, NOTICES, REPORT }


## What a shift banked, for the REPORT page (`Q162`). Filled by `Main`.
class Report:
	extends RefCounted
	var total_hkd: float = 0.0
	var deliveries: int = 0
	var bails: int = 0
	## The best after this shift, this one included.
	var best_hkd: float = 0.0
	var new_best: bool = false


## The shift to report, set before this enters the tree; null opens on HOME.
var report: Report = null

var _profile: MenuProfile = null
var _style: HudStyle = null
var _text: MenuText = null
var _language: String = Locale.DEFAULT
## The plate's Kai for the Chinese lines, over the theme's own faces for any
## glyph it lacks, so a missing punctuation mark is a different face and never
## a box.
var _font_zh: Font = null
var _root: Control = null
var _page: Page = Page.HOME
var _pages: Dictionary[int, Control] = {}
## Where the focus lands when a page opens, so a pad or the keys can drive it.
var _first: Dictionary[int, Button] = {}
## Each choice's rule (`_button`), for the focus and the current marker.
var _rules: Dictionary[Button, ColorRect] = {}
## The notices' label, filled on the first visit: the text is the engine's and
## costs a build, so neither boot nor a language change pays for a page the
## player may never open.
var _notices_label: RichTextLabel = null


## `--menu=off` turns it off; anything else, including nothing, leaves it on.
func wanted() -> bool:
	return not Cmdline.off(MENU_ARG)


func _ready() -> void:
	layer = LAYER
	# Freed rather than parked, like the HUD; nothing holds a reference to this
	# but `Main`'s export, which checks it is alive.
	if not wanted() or not _load():
		set_process_unhandled_input(false)
		queue_free()
		return
	_language = Locale.language()
	var wanted_page: String = Cmdline.value(PAGE_ARG).to_upper()
	if Page.has(wanted_page):
		_page = Page[wanted_page] as Page
	if report != null:
		_page = Page.REPORT
	elif _page == Page.REPORT:
		report = Report.new()
		report.best_hkd = Settings.best_shift_hkd()
	_build()


## The tables, or false having said why.
func _load() -> bool:
	_profile = load(MenuProfile.PATH) as MenuProfile
	_style = load(HudStyle.PATH) as HudStyle
	_text = MenuText.load_text()
	if _profile == null or _style == null or not _text.loaded:
		push_warning(
			(
				"menu: %s, %s or %s did not load; no menu this run"
				% [MenuProfile.PATH, HudStyle.PATH, MenuText.PATH]
			)
		)
		return false
	_font_zh = StreetPlate.load_font_zh("menu")
	return true


func _build() -> void:
	_root = HudLayout.safe_root(self)
	_pages.clear()
	_first.clear()
	_rules.clear()
	_pages[Page.HOME] = _home()
	_pages[Page.PLAY] = _play()
	_pages[Page.OPTIONS] = _options()
	_pages[Page.CREDITS] = _credits()
	_pages[Page.GUIDE] = _guide()
	_pages[Page.NOTICES] = _notices()
	_pages[Page.REPORT] = _report()
	# The HUD's glass (`Q163`): the drive's brackets, so the menu and the drive
	# are one display. Last, over the pages' backdrops, and unshaded — the
	# backdrops shade the text.
	_root.add_child(HeadUpFrame.styled(_style, false))
	_show(_page)


## Rebuild in the other language, on the same page: every label is set from
## the table at build, so a rebuild is the one switch and nothing is missed.
func _relabel() -> void:
	_root.free()
	_build()


func _show(page: Page) -> void:
	var moved: bool = page != _page
	_page = page
	for key: int in _pages:
		_pages[key].visible = key == page
	if moved:
		page_shown.emit(shot())
	if page == Page.NOTICES and _notices_label.text.is_empty():
		_notices_label.text = EngineNotices.compose()
	if _first.has(page):
		# Deferred: the page has just been shown and focus needs a laid-out
		# control.
		_first[page].grab_focus.call_deferred()


## The camera's place round the parked car for the page up now.
func shot() -> MenuShot:
	match _page:
		Page.PLAY:
			return _profile.shot_play
		Page.OPTIONS:
			return _profile.shot_options
		Page.CREDITS, Page.GUIDE, Page.NOTICES:
			return _profile.shot_sheet
		Page.REPORT:
			return _profile.shot_report
	return _profile.shot_home


func _unhandled_input(event: InputEvent) -> void:
	if _page not in [Page.HOME, Page.REPORT] and event.is_action_pressed(&"ui_cancel"):
		# The notices hang off the credits, so the way back is one step.
		_show(Page.CREDITS if _page == Page.NOTICES else Page.HOME)
		get_viewport().set_input_as_handled()


# ---------------------------------------------------------------- pages ----


## The title and the three choices, a column off the bottom-left corner: the
## car is the picture and the column keeps off it.
func _home() -> Control:
	var column: VBoxContainer = _column("Home")
	# The name is Latin in either language, and stays in the theme's own face.
	var title: Label = _line("Title", str(ProjectSettings.get_setting("application/config/name")))
	title.add_theme_font_size_override(&"font_size", _profile.title_size)
	column.add_child(title)
	var subtitle: Label = _line("Subtitle", _text.say("subtitle", _language))
	_size(subtitle, _profile.subtitle_size_zh, _profile.subtitle_size)
	subtitle.add_theme_color_override(&"font_color", _style.chip_muted)
	column.add_child(subtitle)
	# The shift's high score (`Q162`, the user's ask), always shown — a zero
	# before the first shift says there is one to set.
	var record: Label = _line(
		"Best", _text.say("best", _language) + FareFace.money(Settings.best_shift_hkd())
	)
	_size(record, _profile.body_size_zh, _profile.body_size)
	record.add_theme_color_override(&"font_color", _style.dial_needle)
	column.add_child(record)
	column.add_child(_gap("Gap", _profile.button_gap_px * 2))
	_first[Page.HOME] = _button(column, "Play", "start", _show.bind(Page.PLAY))
	_button(column, "Guide", "guide", _show.bind(Page.GUIDE))
	_button(column, "Options", "options", _show.bind(Page.OPTIONS))
	_button(column, "Credits", "credits", _show.bind(Page.CREDITS))
	return column


## The two ways to play (`Q162`), behind HOME's one PLAY: the shift first,
## then free mode, and the way back.
func _play() -> Control:
	var column: VBoxContainer = _column("Play")
	_heading(column, "Heading", _text.say("start", _language))
	_first[Page.PLAY] = _button(column, "Shift", "shift", _on_start.bind(DayClock.Mode.SHIFT))
	_button(column, "Free", "free", _on_start.bind(DayClock.Mode.FREE))
	column.add_child(_gap("Gap", _profile.button_gap_px))
	_button(column, "Back", "back", _show.bind(Page.HOME))
	return column


## One option, the language: a pair of choices side by side with the current
## one marked, and the way back.
func _options() -> Control:
	var column: VBoxContainer = _column("Options")
	var heading: Label = _line("Heading", _text.say("language", _language))
	_size(heading, _profile.heading_size_zh, _profile.heading_size)
	column.add_child(heading)
	var row := HBoxContainer.new()
	row.name = "Languages"
	row.add_theme_constant_override(&"separation", _profile.button_gap_px)
	column.add_child(row)
	var chinese: Button = _button(row, "Chinese", "language_zh", _pick.bind(Locale.CHINESE))
	var english: Button = _button(row, "English", "language_en", _pick.bind(Locale.ENGLISH))
	# The current language's button is the marker: lit in the accent and not a
	# choice, so there is nothing to press that changes nothing.
	_mark_current(chinese, _language == Locale.CHINESE)
	_mark_current(english, _language == Locale.ENGLISH)
	_first[Page.OPTIONS] = english if _language == Locale.CHINESE else chinese

	# The hour (`Q160`): whether the day runs to night as game time passes —
	# in free mode; a shift always runs it (`Q162`).
	column.add_child(_gap("GapTime", _profile.button_gap_px))
	var time_heading: Label = _line("TimeHeading", _text.say("time", _language))
	_size(time_heading, _profile.heading_size_zh, _profile.heading_size)
	column.add_child(time_heading)
	var times := HBoxContainer.new()
	times.name = "Times"
	times.add_theme_constant_override(&"separation", _profile.button_gap_px)
	column.add_child(times)
	var cycling: bool = Settings.day_cycle()
	var cycle: Button = _button(times, "Cycle", "time_cycle", _pick_time.bind(true))
	var day: Button = _button(times, "Day", "time_day", _pick_time.bind(false))
	_mark_current(cycle, cycling)
	_mark_current(day, not cycling)

	column.add_child(_gap("Gap", _profile.button_gap_px))
	_button(column, "Back", "back", _show.bind(Page.HOME))
	return column


## Save the hour's mode and redraw the page so the marker moves. `DayClock`
## reads the saved option when the car first drives off.
func _pick_time(cycle: bool) -> void:
	if cycle == Settings.day_cycle():
		return
	Settings.set_day_cycle(cycle)
	if not Cmdline.value(DayClock.CYCLE_ARG).is_empty():
		push_warning("menu: --day-cycle= pins the hour this run; the choice is saved for the next")
	_relabel.call_deferred()


## The credits, centred, scrolling: the data's owners, the typeface, the
## engine, and what the code and the hand-made assets are under.
func _credits() -> Control:
	var panel: ChamferPanel = _sheet("Credits", _profile.credits_px)
	var column: VBoxContainer = panel.get_node(SHEET_COLUMN)

	var scroll := ScrollContainer.new()
	scroll.name = "Scroll"
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(scroll)

	var lines := VBoxContainer.new()
	lines.name = "Lines"
	lines.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	lines.add_theme_constant_override(&"separation", _profile.button_gap_px)
	scroll.add_child(lines)
	for index: int in _text.credits.size():
		var entry: Variant = _text.credits[index]
		if not entry is Dictionary:
			continue
		_heading(
			lines,
			"Heading%d" % index,
			MenuText.pick((entry as Dictionary).get("heading"), _language, "")
		)
		var body: Label = _line(
			"Body%d" % index, MenuText.pick((entry as Dictionary).get("body"), _language, "")
		)
		_size(body, _profile.body_size_zh, _profile.body_size)
		lines.add_child(body)

	var foot: HBoxContainer = _foot_row(column)
	_button(foot, "Notices", "notices", _show.bind(Page.NOTICES))
	_first[Page.CREDITS] = _button(foot, "Back", "back", _show.bind(Page.HOME))
	return panel


## The engine's third-party notices, the engine's own words at runtime
## (`EngineNotices` says why they are read and not copied): a heading and a
## lead in the player's language over the English text, which is the only
## text the licences exist in. A `RichTextLabel` for its own scroll and its
## threaded layout — the text runs to some 100 components and 19 licences,
## which a `Label` in a `ScrollContainer` lays out on the main thread at every
## resize.
func _notices() -> Control:
	var panel: ChamferPanel = _sheet("Notices", _profile.credits_px)
	var column: VBoxContainer = panel.get_node(SHEET_COLUMN)
	_heading(column, "Heading", _text.say("notices_title", _language))
	var lead: Label = _line("Lead", _text.say("notices_lead", _language))
	_size(lead, _profile.body_size_zh, _profile.body_size)
	lead.add_theme_color_override(&"font_color", _style.chip_muted)
	column.add_child(lead)

	var text := RichTextLabel.new()
	text.name = "Text"
	text.bbcode_enabled = false
	text.threaded = true
	text.scroll_active = true
	text.selection_enabled = false
	text.focus_mode = Control.FOCUS_NONE
	text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	# English, so the Latin size whatever the language; the theme's face, since
	# the Kai has no Latin of its own.
	text.add_theme_font_size_override(&"normal_font_size", _profile.body_size)
	text.add_theme_color_override(&"default_color", _style.plate_ink)
	column.add_child(text)
	_notices_label = text

	_first[Page.NOTICES] = _foot(column, Page.CREDITS)
	return panel


## How to play, as a row of steps: a drawn picture over a caption each
## (`GuideCard` says why drawn), in reading order from the table.
func _guide() -> Control:
	var panel: ChamferPanel = _sheet("Guide", _profile.guide_px)
	var column: VBoxContainer = panel.get_node(SHEET_COLUMN)
	_heading(column, "Heading", _text.say("guide", _language))

	var row := HBoxContainer.new()
	row.name = "Steps"
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row.add_theme_constant_override(&"separation", _profile.credits_pad_px)
	column.add_child(row)
	for index: int in _text.guide.size():
		var entry: Variant = _text.guide[index]
		if not entry is Dictionary:
			continue
		var step := VBoxContainer.new()
		step.name = "Step%d" % index
		step.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		step.add_theme_constant_override(&"separation", _profile.button_gap_px)
		row.add_child(step)
		var card := GuideCard.new()
		card.name = "Picture"
		card.kind = str((entry as Dictionary).get("picture", ""))
		card.style = _style
		card.custom_minimum_size = _profile.guide_picture_px
		card.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		step.add_child(card)
		var title: Label = _line(
			"Heading",
			(
				"%d. %s"
				% [index + 1, MenuText.pick((entry as Dictionary).get("heading"), _language, "")]
			)
		)
		_size(title, _profile.heading_size_zh, _profile.heading_size)
		step.add_child(title)
		var body: Label = _line(
			"Body", MenuText.pick((entry as Dictionary).get("body"), _language, "")
		)
		_size(body, _profile.body_size_zh, _profile.body_size)
		body.add_theme_color_override(&"font_color", _style.chip_muted)
		step.add_child(body)

	_first[Page.GUIDE] = _foot(column)
	return panel


## 交更 (`Q162`): what the shift banked, over the best, and the way to the
## next — a column off the corner like HOME's, so the car stays the picture.
func _report() -> Control:
	var column: VBoxContainer = _column("Report")
	var shown: Report = report if report != null else Report.new()
	var heading: Label = _line("Heading", _text.say("handover", _language))
	_size(heading, _profile.heading_size_zh, _profile.heading_size)
	heading.add_theme_color_override(&"font_color", _style.dial_needle)
	column.add_child(heading)
	var total: Label = _line("Total", "HK$" + FareFace.money(shown.total_hkd))
	total.add_theme_font_size_override(&"font_size", _profile.title_size)
	column.add_child(total)
	var fares: Label = _line(
		"Fares", _text.say("report_fares", _language) % [shown.deliveries, shown.bails]
	)
	_size(fares, _profile.body_size_zh, _profile.body_size)
	fares.add_theme_color_override(&"font_color", _style.chip_muted)
	column.add_child(fares)
	var best: Label = _line(
		"Best",
		(
			_text.say("new_best", _language)
			if shown.new_best
			else _text.say("best", _language) + FareFace.money(shown.best_hkd)
		)
	)
	_size(best, _profile.body_size_zh, _profile.body_size)
	best.add_theme_color_override(
		&"font_color", _style.accent if shown.new_best else _style.dial_needle
	)
	column.add_child(best)
	column.add_child(_gap("Gap", _profile.button_gap_px))
	_first[Page.REPORT] = _button(column, "Again", "again", _on_start.bind(DayClock.Mode.SHIFT))
	_button(column, "Menu", "menu", _show.bind(Page.HOME))
	return column


# -------------------------------------------------------------- actions ----


func _on_start(mode: DayClock.Mode) -> void:
	# Released first: a `ui_accept` still held would land on whatever took the
	# focus next, and Space is also the drift.
	get_viewport().gui_release_focus()
	set_process_unhandled_input(false)
	visible = false
	started.emit(mode)
	queue_free()


func _pick(code: String) -> void:
	if code == _language:
		return
	Settings.set_language(code)
	# Through `Locale`, not the pick: a `--lang=` flag pins the language for
	# the run, and the menu must show the one the HUD will read.
	var chosen: String = Locale.language()
	if chosen != code:
		push_warning("menu: --lang= pins the language this run; the choice is saved for the next")
	if chosen == _language:
		return
	_language = chosen
	# Deferred: the button asking for this sits under the root being freed, and
	# a node freed inside its own `pressed` is a use-after-free on return.
	_relabel.call_deferred()
	language_changed.emit(chosen)


# -------------------------------------------------------------- widgets ----


## A column of controls off the safe area's bottom-left corner, growing up.
func _column(node_name: String) -> VBoxContainer:
	var column := VBoxContainer.new()
	column.name = node_name
	column.add_theme_constant_override(&"separation", _profile.button_gap_px)
	column.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	column.grow_vertical = Control.GROW_DIRECTION_BEGIN
	column.offset_left = _profile.margin_px.x
	column.offset_right = _profile.margin_px.x + _profile.button_px.x
	column.offset_top = -_profile.margin_px.y
	column.offset_bottom = -_profile.margin_px.y
	# The side panel behind it, fading out toward the car: the root's child,
	# before the column so it draws under it, shown and hidden with it — a
	# child of the column would be laid out by it, and a top-level one drew
	# over it.
	var backdrop: ColorRect = _backdrop(_root, _profile.backdrop_fade_from)
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	backdrop.offset_right = _profile.backdrop_width_px
	column.visibility_changed.connect(_follow.bind(backdrop, column))
	_root.add_child(column)
	return column


func _follow(backdrop: CanvasItem, page: CanvasItem) -> void:
	backdrop.visible = page.visible


## A panel that draws nothing of its own (`Q163`): the HUD's readouts float on
## the glass, and so do the menu's.
func _panel(node_name: String) -> ChamferPanel:
	return ChamferPanel.bare(_style, node_name)


## A sheet for a page with more than a column of buttons on it: the whole
## screen dimmed by the scrim, and a padded column of `size_px` centred on it.
func _sheet(node_name: String, size_px: Vector2) -> ChamferPanel:
	var panel: ChamferPanel = _panel(node_name)
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(panel)
	_backdrop(panel, 1.0).set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var centre := CenterContainer.new()
	centre.name = "Centre"
	centre.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.add_child(centre)

	var pad := MarginContainer.new()
	pad.name = "Pad"
	pad.custom_minimum_size = size_px
	for side: StringName in [&"margin_left", &"margin_top", &"margin_right", &"margin_bottom"]:
		pad.add_theme_constant_override(side, _profile.credits_pad_px)
	centre.add_child(pad)

	var column := VBoxContainer.new()
	column.name = "Column"
	column.add_theme_constant_override(&"separation", _profile.button_gap_px)
	pad.add_child(column)
	return panel


## The blurred, tinted screen behind `parent`'s text (`backdrop_blur.gdshader`),
## fading out from `fade_from` across its width; add it before the text it is for.
func _backdrop(parent: Control, fade_from: float) -> ColorRect:
	var backdrop := ColorRect.new()
	backdrop.name = "Backdrop"
	backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var material := ShaderMaterial.new()
	material.shader = BACKDROP
	material.set_shader_parameter(&"blur_lod", _profile.backdrop_lod)
	material.set_shader_parameter(&"tint", _style.scrim)
	material.set_shader_parameter(&"fade_from", fade_from)
	backdrop.material = material
	parent.add_child(backdrop)
	return backdrop


## A sheet's foot: the way back to `to`, right-aligned. Returned for the focus.
func _foot(column: VBoxContainer, to: Page = Page.HOME) -> Button:
	return _button(_foot_row(column), "Back", "back", _show.bind(to))


## The foot's row, for a sheet with more than the way back in it.
func _foot_row(column: VBoxContainer) -> HBoxContainer:
	var foot := HBoxContainer.new()
	foot.name = "Foot"
	foot.alignment = BoxContainer.ALIGNMENT_END
	foot.add_theme_constant_override(&"separation", _profile.button_gap_px)
	column.add_child(foot)
	return foot


## A choice: bare lettering over a rule down its left side (`Q163`, the
## callout's mark), the rule and the words lit in the accent while the pointer
## or the focus is on it. Returned for the focus and the marker; the panel goes
## under `parent`.
func _button(parent: Control, node_name: String, key: String, pressed: Callable) -> Button:
	var panel: ChamferPanel = _panel(node_name)
	panel.custom_minimum_size = _profile.button_px
	# Its own width in any container: a lone BACK under a row of two would
	# otherwise stretch to the row.
	panel.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	parent.add_child(panel)
	var rule := ColorRect.new()
	rule.name = "Rule"
	rule.color = _style.frame_ink
	rule.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rule.set_anchors_preset(Control.PRESET_LEFT_WIDE)
	rule.offset_right = _style.accent_px
	panel.add_child(rule)

	var button := Button.new()
	button.name = "Button"
	button.flat = true
	button.text = _text.say(key, _language)
	button.set_anchors_preset(Control.PRESET_FULL_RECT)
	button.focus_mode = Control.FOCUS_ALL
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	# The rule is the whole look; the theme's box would draw a second one.
	var empty := StyleBoxEmpty.new()
	empty.content_margin_left = _style.plate_pad.y * 2.0
	for state: StringName in [
		&"normal", &"hover", &"pressed", &"focus", &"hover_pressed", &"disabled"
	]:
		button.add_theme_stylebox_override(state, empty)
	button.add_theme_color_override(&"font_color", _style.plate_ink)
	# An outline, not `HudStyle.shade`'s shadow: a `Button` has no shadow.
	button.add_theme_color_override(&"font_outline_color", _style.float_shadow)
	button.add_theme_constant_override(&"outline_size", _style.float_shadow_px)
	for state: StringName in [
		&"font_hover_color", &"font_focus_color", &"font_pressed_color", &"font_hover_pressed_color"
	]:
		button.add_theme_color_override(state, _style.accent)
	_size(button, _profile.button_size_zh, _profile.button_size)
	button.pressed.connect(pressed)
	# Hover IS focus, so the lit rule follows the pointer and the pad alike
	# and there is one highlighted choice at a time.
	button.mouse_entered.connect(button.grab_focus)
	button.focus_entered.connect(_light.bind(rule, true))
	button.focus_exited.connect(_light.bind(rule, false))
	_rules[button] = rule
	panel.add_child(button)
	return button


func _light(rule: ColorRect, lit: bool) -> void:
	rule.color = _style.accent if lit else _style.frame_ink


## The current option: lit in the dial's amber — not the accent, which is the
## focus's and would make the current choice and the cursor one colour — and
## not a button any more.
func _mark_current(button: Button, current: bool) -> void:
	if not current:
		return
	button.disabled = true
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_color_override(&"font_disabled_color", _style.dial_needle)
	_rules[button].color = _style.dial_needle


## A sheet's heading under `parent`: a line in the dial's amber at the heading
## size.
func _heading(parent: Control, node_name: String, text: String) -> Label:
	var heading: Label = _line(node_name, text)
	_size(heading, _profile.heading_size_zh, _profile.heading_size)
	heading.add_theme_color_override(&"font_color", _style.dial_needle)
	parent.add_child(heading)
	return heading


## A line of menu text in the plate's ink and the HUD's shadow, wrapping inside
## its column.
func _line(node_name: String, text: String) -> Label:
	var label := Label.new()
	label.name = node_name
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.add_theme_color_override(&"font_color", _style.plate_ink)
	return _style.shade(label)


func _gap(node_name: String, px: int) -> Control:
	var gap := Control.new()
	gap.name = node_name
	gap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gap.custom_minimum_size = Vector2(0.0, px)
	return gap


## A size for the language: the Kai face sets larger than the Latin at every
## line, and takes the plate's font.
func _size(control: Control, zh: int, en: int) -> void:
	var chinese: bool = _language == Locale.CHINESE
	control.add_theme_font_size_override(&"font_size", Locale.pick(zh, en, _language))
	if chinese and _font_zh != null:
		control.add_theme_font_override(&"font", _font_zh)
