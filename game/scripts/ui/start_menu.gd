class_name StartMenu
extends CanvasLayer
## The start menu (`P6-1`, the user's ask): start, options, credits, drawn over
## the taxi standing on the start line with the camera circling it.
##
## Under `GUI` beside the HUD, and it never reaches into the level: `Main` parks
## the level while this is up and resumes it on `started`, the same way it hands
## the HUD its car. Everything drawn is the cab's housing — `HudStyle`'s
## colours, `ChamferPanel`'s shape (`Q139`, one voice) — and every number is
## `MenuProfile`'s. Every string is `MenuText`'s, in the one language `Locale`
## names, and the credits it shows are the attribution hard rule 6 and
## `LICENSING.md` require; `verify_menu.gd` holds their wording.
##
## ⚠️ **`--menu=off` boots straight into the drive**, and `drive.sh` passes it
## unless a run names the flag, so every scripted drive is what it was.
##
## ⚠️ **The first Controls in this project that take a click.** `InputRouter`
## never marks an event handled, so the buttons see the pointer and the touch;
## while the menu is up the car is parked, so the thumbs the router still reads
## move nothing. `ui_cancel` is read here — a UI action, not a gameplay one —
## for the way back from a page.

## The player pressed start. `Main` resumes the level and frees this.
signal started
## The player picked a language; `Locale.language()` already answers it.
signal language_changed(code: String)

## Chooses whether the menu is shown at all. `off` for every scripted run.
const MENU_ARG: String = "--menu="
## Over the HUD (10), under the dev overlay (127).
const LAYER: int = 20

enum Page { HOME, OPTIONS, CREDITS, GUIDE }

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


## `--menu=off` turns it off; anything else, including nothing, leaves it on.
func wanted() -> bool:
	return Cmdline.value(MENU_ARG).to_lower() != "off"


func _ready() -> void:
	layer = LAYER
	# Freed rather than parked, like the HUD; nothing holds a reference to this
	# but `Main`'s export, which checks it is alive.
	if not wanted() or not _load():
		set_process_unhandled_input(false)
		queue_free()
		return
	_language = Locale.language()
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
	var face_path: String = str(StreetPlate.load_tuning().get("font_zh", ""))
	var face: Font = null
	if not face_path.is_empty() and ResourceLoader.exists(face_path):
		face = load(face_path) as Font
	if face == null:
		# Not fatal, and loud: the Chinese lines fall to the theme's fallback
		# face, which draws them in the wrong hand rather than not at all.
		push_warning("menu: the plate's Chinese font did not load; using the theme's fallback")
		return true
	var kai := FontVariation.new()
	kai.base_font = face
	var fallbacks: Array[Font] = [ThemeDB.fallback_font]
	kai.fallbacks = fallbacks
	_font_zh = kai
	return true


func _build() -> void:
	_root = HudLayout.safe_root(self)
	_pages.clear()
	_first.clear()
	_pages[Page.HOME] = _home()
	_pages[Page.OPTIONS] = _options()
	_pages[Page.CREDITS] = _credits()
	_pages[Page.GUIDE] = _guide()
	_show(_page)


## Rebuild in the other language, on the same page: every label is set from
## the table at build, so a rebuild is the one switch and nothing is missed.
func _relabel() -> void:
	_root.free()
	_build()


func _show(page: Page) -> void:
	_page = page
	for key: int in _pages:
		_pages[key].visible = key == page
	if _first.has(page):
		# Deferred: the page has just been shown and focus needs a laid-out
		# control.
		_first[page].grab_focus.call_deferred()


func _unhandled_input(event: InputEvent) -> void:
	if _page != Page.HOME and event.is_action_pressed(&"ui_cancel"):
		_show(Page.HOME)
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
	column.add_child(_gap("Gap", _profile.button_gap_px * 2))
	_first[Page.HOME] = _button(column, "Start", "start", _on_start)
	_button(column, "Guide", "guide", _show.bind(Page.GUIDE))
	_button(column, "Options", "options", _show.bind(Page.OPTIONS))
	_button(column, "Credits", "credits", _show.bind(Page.CREDITS))
	return column


## One option so far: the language, the two choices side by side with the
## current one marked, and the way back.
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
	column.add_child(_gap("Gap", _profile.button_gap_px))
	_button(column, "Back", "back", _show.bind(Page.HOME))
	return column


## The credits, centred, scrolling: the data's owners, the typeface, the
## engine, and what the code and the hand-made assets are under.
func _credits() -> Control:
	var panel: ChamferPanel = _sheet("Credits", _profile.credits_px)
	var column: VBoxContainer = panel.get_node("Pad/Column")

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
		var heading: Label = _line(
			"Heading%d" % index, MenuText.pick((entry as Dictionary).get("heading"), _language, "")
		)
		_size(heading, _profile.heading_size_zh, _profile.heading_size)
		heading.add_theme_color_override(&"font_color", _style.dial_needle)
		lines.add_child(heading)
		var body: Label = _line(
			"Body%d" % index, MenuText.pick((entry as Dictionary).get("body"), _language, "")
		)
		_size(body, _profile.body_size_zh, _profile.body_size)
		lines.add_child(body)

	_first[Page.CREDITS] = _foot(column)
	return panel


## How to play, as a row of steps: a drawn picture over a caption each
## (`GuideCard` says why drawn), in reading order from the table.
func _guide() -> Control:
	var panel: ChamferPanel = _sheet("Guide", _profile.guide_px)
	var column: VBoxContainer = panel.get_node("Pad/Column")
	var heading: Label = _line("Heading", _text.say("guide", _language))
	_size(heading, _profile.heading_size_zh, _profile.heading_size)
	heading.add_theme_color_override(&"font_color", _style.dial_needle)
	column.add_child(heading)

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


# -------------------------------------------------------------- actions ----


func _on_start() -> void:
	# Released first: a `ui_accept` still held would land on whatever took the
	# focus next, and Space is also the drift.
	get_viewport().gui_release_focus()
	set_process_unhandled_input(false)
	visible = false
	started.emit()
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
	_root.add_child(column)
	return column


## The housing: the HUD's panel, its numbers.
func _panel(node_name: String) -> ChamferPanel:
	var panel := ChamferPanel.new()
	panel.name = node_name
	panel.chamfer_px = _style.chamfer_px
	panel.fill = _style.plate_field
	panel.edge = _style.plate_edge
	panel.edge_px = _style.edge_px
	return panel


## A centred sheet of `size_px`: the housing with a padded column inside it,
## for a page with more than a column of buttons on it.
func _sheet(node_name: String, size_px: Vector2) -> ChamferPanel:
	var panel: ChamferPanel = _panel(node_name)
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.offset_left = -size_px.x * 0.5
	panel.offset_right = size_px.x * 0.5
	panel.offset_top = -size_px.y * 0.5
	panel.offset_bottom = size_px.y * 0.5
	_root.add_child(panel)

	var pad := MarginContainer.new()
	pad.name = "Pad"
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side: StringName in [&"margin_left", &"margin_top", &"margin_right", &"margin_bottom"]:
		pad.add_theme_constant_override(side, _profile.credits_pad_px)
	panel.add_child(pad)

	var column := VBoxContainer.new()
	column.name = "Column"
	column.add_theme_constant_override(&"separation", _profile.button_gap_px)
	pad.add_child(column)
	return panel


## A sheet's foot: the way back, right-aligned. Returned for the focus.
func _foot(column: VBoxContainer) -> Button:
	var foot := HBoxContainer.new()
	foot.name = "Foot"
	foot.alignment = BoxContainer.ALIGNMENT_END
	column.add_child(foot)
	return _button(foot, "Back", "back", _show.bind(Page.HOME))


## A choice: the housing with a flat `Button` filling it, the keyline lit in the
## accent while the pointer or the focus is on it. Returned for the focus and
## the marker; the panel goes under `parent`.
func _button(parent: Control, node_name: String, key: String, pressed: Callable) -> Button:
	var panel: ChamferPanel = _panel(node_name)
	panel.custom_minimum_size = _profile.button_px
	# Its own width in any container: a lone BACK under a row of two would
	# otherwise stretch to the row.
	panel.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	parent.add_child(panel)

	var button := Button.new()
	button.name = "Button"
	button.flat = true
	button.text = _text.say(key, _language)
	button.set_anchors_preset(Control.PRESET_FULL_RECT)
	button.focus_mode = Control.FOCUS_ALL
	# The panel is the whole look; the theme's box would draw a second one.
	var empty := StyleBoxEmpty.new()
	for state: StringName in [
		&"normal", &"hover", &"pressed", &"focus", &"hover_pressed", &"disabled"
	]:
		button.add_theme_stylebox_override(state, empty)
	button.add_theme_color_override(&"font_color", _style.plate_ink)
	for state: StringName in [
		&"font_hover_color", &"font_focus_color", &"font_pressed_color", &"font_hover_pressed_color"
	]:
		button.add_theme_color_override(state, _style.accent)
	_size(button, _profile.button_size_zh, _profile.button_size)
	button.pressed.connect(pressed)
	# Hover IS focus, so the lit keyline follows the pointer and the pad alike
	# and there is one highlighted choice at a time.
	button.mouse_entered.connect(button.grab_focus)
	button.focus_entered.connect(_light.bind(panel, true))
	button.focus_exited.connect(_light.bind(panel, false))
	panel.add_child(button)
	return button


func _light(panel: ChamferPanel, lit: bool) -> void:
	panel.edge = _style.accent if lit else _style.plate_edge


## The current option: lit in the dial's amber — not the accent, which is the
## focus's and would make the current choice and the cursor one colour — and
## not a button any more.
func _mark_current(button: Button, current: bool) -> void:
	if not current:
		return
	button.disabled = true
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_color_override(&"font_disabled_color", _style.dial_needle)
	(button.get_parent() as ChamferPanel).edge = _style.dial_needle


## A line of menu text in the housing's ink, wrapping inside its column.
func _line(node_name: String, text: String) -> Label:
	var label := Label.new()
	label.name = node_name
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.add_theme_color_override(&"font_color", _style.plate_ink)
	return label


func _gap(node_name: String, px: int) -> Control:
	var gap := Control.new()
	gap.name = node_name
	gap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gap.custom_minimum_size = Vector2(0.0, px)
	return gap


## A size for the language, Chinese first like `FareFace._say`: the Kai face
## sets larger than the Latin at every line, and takes the plate's font.
func _size(control: Control, zh: int, en: int) -> void:
	var chinese: bool = _language == Locale.CHINESE
	control.add_theme_font_size_override(&"font_size", zh if chinese else en)
	if chinese and _font_zh != null:
		control.add_theme_font_override(&"font", _font_zh)
